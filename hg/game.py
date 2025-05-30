# game.py - IMPROVED VERSION
"""Core game logic for Hunger Games with enhanced error handling and performance"""

import discord
import asyncio
import random
import logging
from typing import Dict, List, Optional, Tuple, Union, TypedDict
from redbot.core import bank
from dataclasses import dataclass

from .constants import (
    DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS,
    REVIVAL_MESSAGES, GAME_PHASES, FINALE_MESSAGES, VICTORY_TITLE_ART,
    PLACEMENT_MEDALS
)

# Set up logging
logger = logging.getLogger(__name__)

# Type definitions for better type safety
class PlayerData(TypedDict):
    name: str
    title: str
    alive: bool
    kills: int
    revives: int
    district: int

class GameState(TypedDict):
    players: Dict[str, PlayerData]
    round: int
    status: str
    eliminated: List[Dict[str, Union[str, int]]]
    sponsor_used: List[str]
    reactions: set
    milestones_shown: set

class EliminatedPlayer(TypedDict):
    id: str
    name: str
    round: int
    killer: Optional[str]

@dataclass
class PrizeConfig:
    """Configuration for prize calculations"""
    BASE_MULTIPLIER_SMALL: float = 1.0    # < 5 players
    BASE_MULTIPLIER_MEDIUM: float = 1.5   # 5-9 players  
    BASE_MULTIPLIER_LARGE: float = 2.0    # 10-19 players
    BASE_MULTIPLIER_HUGE: float = 2.5     # 20-29 players
    BASE_MULTIPLIER_MASSIVE: float = 3.0  # 30+ players

# Custom exceptions for better error handling
class GameError(Exception):
    """Base exception for game-related errors"""
    pass

class InvalidGameStateError(GameError):
    """Game state is invalid or corrupted"""
    pass

class PlayerNotFoundError(GameError):
    """Player not found in game"""
    pass

class EventExecutionError(GameError):
    """Error during event execution"""
    pass

class GameEngine:
    """Handles all game logic and events with improved error handling"""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.prize_config = PrizeConfig()
        
        # Performance optimization - cache frequently accessed data
        self._alive_players_cache = {}
        self._cache_timestamps = {}
        
    def _validate_game_state(self, game: GameState) -> bool:
        """Validate game state integrity"""
        try:
            required_keys = ["players", "round", "status"]
            return all(key in game for key in required_keys)
        except Exception:
            return False
    
    def _validate_player_exists(self, game: GameState, player_id: str) -> bool:
        """Validate that player exists in game"""
        return player_id in game.get("players", {})
    
    def calculate_prize_pool(self, player_count: int, base_reward: int) -> int:
        """Calculate prize based on number of players with clear thresholds"""
        if player_count < 5:
            multiplier = self.prize_config.BASE_MULTIPLIER_SMALL
        elif player_count < 10:
            multiplier = self.prize_config.BASE_MULTIPLIER_MEDIUM
        elif player_count < 20:
            multiplier = self.prize_config.BASE_MULTIPLIER_LARGE
        elif player_count < 30:
            multiplier = self.prize_config.BASE_MULTIPLIER_HUGE
        else:
            multiplier = self.prize_config.BASE_MULTIPLIER_MASSIVE
        
        return int(base_reward * multiplier)
    
    def get_alive_players(self, game: GameState) -> List[str]:
        """Get list of alive player IDs with caching for performance"""
        try:
            game_id = id(game)
            current_round = game.get("round", 0)
            
            # Check cache validity
            if (game_id in self._cache_timestamps and 
                self._cache_timestamps[game_id] == current_round and
                game_id in self._alive_players_cache):
                return self._alive_players_cache[game_id]
            
            # Recalculate and cache
            alive_players = [
                pid for pid, pdata in game["players"].items() 
                if pdata.get("alive", False)
            ]
            
            self._alive_players_cache[game_id] = alive_players
            self._cache_timestamps[game_id] = current_round
            
            return alive_players
            
        except Exception as e:
            logger.error(f"Error getting alive players: {e}")
            # Fallback without cache
            return [
                pid for pid, pdata in game.get("players", {}).items() 
                if pdata.get("alive", False)
            ]
    
    def get_dead_players(self, game: GameState) -> List[str]:
        """Get list of dead player IDs"""
        try:
            return [
                pid for pid, pdata in game.get("players", {}).items() 
                if not pdata.get("alive", True)
            ]
        except Exception as e:
            logger.error(f"Error getting dead players: {e}")
            return []
    
    def invalidate_cache(self, game: GameState):
        """Invalidate alive players cache when game state changes"""
        game_id = id(game)
        self._alive_players_cache.pop(game_id, None)
        self._cache_timestamps.pop(game_id, None)
    
    def kill_player(self, game: GameState, player_id: str, killer_id: Optional[str] = None) -> Optional[PlayerData]:
        """Kill a player and update stats with validation"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state")
            
            if not self._validate_player_exists(game, player_id):
                raise PlayerNotFoundError(f"Player {player_id} not found")
            
            player_data = game["players"][player_id]
            
            if not player_data.get("alive", False):
                logger.warning(f"Attempted to kill already dead player: {player_id}")
                return None
            
            # Kill the player
            player_data["alive"] = False
            
            # Add to eliminated list
            eliminated_data: EliminatedPlayer = {
                "id": player_id,
                "name": player_data["name"],
                "round": game["round"],
                "killer": killer_id
            }
            
            if "eliminated" not in game:
                game["eliminated"] = []
            game["eliminated"].append(eliminated_data)
            
            # Update kill count for killer
            if killer_id and self._validate_player_exists(game, killer_id):
                game["players"][killer_id]["kills"] += 1
            
            # Invalidate cache
            self.invalidate_cache(game)
            
            logger.debug(f"Player {player_id} killed by {killer_id or 'environment'}")
            return player_data
            
        except Exception as e:
            logger.error(f"Error killing player {player_id}: {e}")
            raise EventExecutionError(f"Failed to eliminate player: {e}")
    
    def revive_player(self, game: GameState, player_id: str) -> bool:
        """Attempt to revive a dead player via sponsor with validation"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state")
            
            if not self._validate_player_exists(game, player_id):
                raise PlayerNotFoundError(f"Player {player_id} not found")
            
            player_data = game["players"][player_id]
            
            if player_data.get("alive", False):
                logger.warning(f"Attempted to revive living player: {player_id}")
                return False
            
            # Check if already used sponsor
            if "sponsor_used" not in game:
                game["sponsor_used"] = []
            
            if player_id in game["sponsor_used"]:
                logger.debug(f"Player {player_id} already used sponsor revival")
                return False
            
            # Revive the player
            player_data["alive"] = True
            game["sponsor_used"].append(player_id)
            
            # Track revive count
            player_data["revives"] = player_data.get("revives", 0) + 1
            
            # Remove from eliminated list
            if "eliminated" in game:
                game["eliminated"] = [
                    e for e in game["eliminated"] 
                    if e.get("id") != player_id
                ]
            
            # Invalidate cache
            self.invalidate_cache(game)
            
            logger.info(f"Player {player_id} successfully revived")
            return True
            
        except Exception as e:
            logger.error(f"Error reviving player {player_id}: {e}")
            return False
    
    async def execute_death_event(self, game: GameState, channel: discord.TextChannel) -> Optional[str]:
        """Execute a death event with comprehensive error handling"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state for death event")
            
            alive_players = self.get_alive_players(game)
            logger.debug(f"Death event: {len(alive_players)} alive players")
            
            if len(alive_players) <= 1:
                logger.debug("Not enough players for death event")
                return None
            
            # Choose victim
            victim_id = random.choice(alive_players)
            victim_data = game["players"][victim_id]
            victim_name_with_title = f"{victim_data['name']} {victim_data['title']}"
            
            # Generate event message
            message = await self._generate_death_event_message(
                game, victim_id, victim_name_with_title, alive_players
            )
            
            # Check for sponsor revival
            sponsor_message = await self._check_sponsor_revival(game, channel)
            if sponsor_message:
                message += f"\n\n{sponsor_message}"
            
            return message
            
        except GameError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in death event: {e}", exc_info=True)
            raise EventExecutionError(f"Death event failed: {e}")
    
    async def _generate_death_event_message(self, game: GameState, victim_id: str, 
                                          victim_name_with_title: str, alive_players: List[str]) -> str:
        """Generate death event message (murder vs accident)"""
        # Enhanced fallback events for reliability
        fallback_murder_events = [
            "💀 | **{killer}** eliminated ~~**{player}**~~ in brutal combat!",
            "💀 | **{killer}** outmaneuvered ~~**{player}**~~ in a fierce duel!",
            "💀 | **{killer}** overwhelmed ~~**{player}**~~ with superior tactics!",
            "💀 | **{killer}** ambushed ~~**{player}**~~ from the shadows!",
            "💀 | **{killer}** trapped ~~**{player}**~~ with a clever ruse!"
        ]
        
        fallback_accident_events = [
            "💀 | ~~**{player}**~~ met their demise in the treacherous arena.",
            "💀 | ~~**{player}**~~ made a fatal mistake while exploring.",
            "💀 | ~~**{player}**~~ was eliminated by the arena's deadly traps.",
            "💀 | ~~**{player}**~~ fell victim to the harsh environment.",
            "💀 | ~~**{player}**~~ pushed their luck too far."
        ]
        
        # 70% chance for murder, 30% chance for accident
        if random.random() < 0.7 and len(alive_players) > 2:
            # Murder - choose a killer
            potential_killers = [p for p in alive_players if p != victim_id]
            killer_id = random.choice(potential_killers)
            killer_data = game["players"][killer_id]
            killer_name_with_title = f"{killer_data['name']} {killer_data['title']}"
            
            # Choose murder event
            try:
                murder_events = [e for e in DEATH_EVENTS if "{killer}" in e]
                if not murder_events:
                    murder_events = fallback_murder_events
            except (NameError, AttributeError):
                murder_events = fallback_murder_events
            
            event = random.choice(murder_events)
            message = event.format(player=victim_name_with_title, killer=killer_name_with_title)
            
            self.kill_player(game, victim_id, killer_id)
        else:
            # Accident
            try:
                accident_events = [e for e in DEATH_EVENTS if "{killer}" not in e]
                if not accident_events:
                    accident_events = fallback_accident_events
            except (NameError, AttributeError):
                accident_events = fallback_accident_events
            
            event = random.choice(accident_events)
            message = event.format(player=victim_name_with_title)
            
            self.kill_player(game, victim_id)
        
        return message
    
    async def _check_sponsor_revival(self, game: GameState, channel: discord.TextChannel) -> Optional[str]:
        """Check and execute sponsor revival"""
        try:
            sponsor_chance = await self.config.guild(channel.guild).sponsor_chance()
            
            if random.randint(1, 100) <= sponsor_chance:
                dead_players = self.get_dead_players(game)
                eligible_for_revival = [
                    p for p in dead_players 
                    if p not in game.get("sponsor_used", [])
                ]
                
                if eligible_for_revival:
                    revive_id = random.choice(eligible_for_revival)
                    if self.revive_player(game, revive_id):
                        revive_data = game["players"][revive_id]
                        revive_name_with_title = f"{revive_data['name']} {revive_data['title']}"
                        
                        try:
                            revival_msg = random.choice(REVIVAL_MESSAGES).format(
                                player=revive_name_with_title
                            )
                        except (NameError, AttributeError):
                            revival_msg = f"✨ | **MIRACLE!** ~~**{revive_name_with_title}**~~ was __*revived by a generous sponsor*__!"
                        
                        return revival_msg
            
            return None
            
        except Exception as e:
            logger.error(f"Error in sponsor revival check: {e}")
            return None
    
    async def execute_survival_event(self, game: GameState) -> Optional[str]:
        """Execute a survival event with error handling"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state for survival event")
            
            alive_players = self.get_alive_players(game)
            
            if not alive_players:
                return None
            
            player_id = random.choice(alive_players)
            player_data = game["players"][player_id]
            player_name_with_title = f"{player_data['name']} {player_data['title']}"
            
            try:
                if not SURVIVAL_EVENTS:
                    raise AttributeError("No survival events available")
                
                event = random.choice(SURVIVAL_EVENTS)
                message = event.format(player=player_name_with_title)
            except (NameError, AttributeError):
                message = f"🌿 | **{player_name_with_title}** survived another day in the arena."
            
            return message
            
        except GameError:
            raise
        except Exception as e:
            logger.error(f"Error in survival event: {e}")
            raise EventExecutionError(f"Survival event failed: {e}")
    
    async def execute_crate_event(self, game: GameState) -> Optional[str]:
        """Execute a crate discovery event with error handling"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state for crate event")
            
            alive_players = self.get_alive_players(game)
            
            if not alive_players:
                return None
            
            player_id = random.choice(alive_players)
            player_data = game["players"][player_id]
            player_name_with_title = f"{player_data['name']} {player_data['title']}"
            
            # Fallback crate events
            fallback_crate_events = [
                "📦 | **{player}** discovered a weapon cache hidden in the ruins!",
                "📦 | **{player}** found survival gear in an abandoned supply crate!",
                "📦 | **{player}** uncovered medical supplies in a hidden stash!",
                "📦 | **{player}** located a food cache buried underground!",
                "📦 | **{player}** cracked open a mystery crate with useful tools!"
            ]
            
            try:
                if not CRATE_EVENTS:
                    crate_events = fallback_crate_events
                else:
                    crate_events = CRATE_EVENTS
            except (NameError, AttributeError):
                crate_events = fallback_crate_events
            
            event = random.choice(crate_events)
            message = event.format(player=player_name_with_title)
            
            return message
            
        except GameError:
            raise
        except Exception as e:
            logger.error(f"Error in crate event: {e}")
            raise EventExecutionError(f"Crate event failed: {e}")
    
    async def execute_sponsor_event(self, game: GameState) -> Optional[str]:
        """Execute a sponsor gift event with error handling"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state for sponsor event")
            
            alive_players = self.get_alive_players(game)
            
            if not alive_players:
                return None
            
            player_id = random.choice(alive_players)
            player_data = game["players"][player_id]
            player_name_with_title = f"{player_data['name']} {player_data['title']}"
            
            try:
                if not SPONSOR_EVENTS:
                    raise AttributeError("No sponsor events available")
                
                event = random.choice(SPONSOR_EVENTS)
                message = event.format(player=player_name_with_title)
            except (NameError, AttributeError):
                message = f"🎁 | **SPONSOR GIFT!** **{player_name_with_title}** received a mysterious package."
            
            return message
            
        except GameError:
            raise
        except Exception as e:
            logger.error(f"Error in sponsor event: {e}")
            raise EventExecutionError(f"Sponsor event failed: {e}")
    
    async def execute_alliance_event(self, game: GameState) -> Optional[str]:
        """Execute an alliance event with error handling"""
        try:
            if not self._validate_game_state(game):
                raise InvalidGameStateError("Invalid game state for alliance event")
            
            alive_players = self.get_alive_players(game)
            
            if len(alive_players) < 2:
                return None
            
            player1_id, player2_id = random.sample(alive_players, 2)
            player1_data = game["players"][player1_id]
            player2_data = game["players"][player2_id]
            
            player1_name_with_title = f"{player1_data['name']} {player1_data.get('title', 'the Nameless')}"
            player2_name_with_title = f"{player2_data['name']} {player2_data.get('title', 'the Nameless')}"
            
            # Enhanced fallback alliance events
            fallback_alliance_events = [
                "🤝 | **{player1}** and **{player2}** formed an alliance!",
                "💔 | **{player1}** betrayed **{player2}** for supplies!",
                "🛡️ | **{player1}** protected **{player2}** from danger!",
                "🔥 | **{player1}** and **{player2}** shared resources!",
                "⚔️ | **{player1}** and **{player2}** teamed up for battle!",
                "🗣️ | **{player1}** and **{player2}** planned their strategy!",
                "🏥 | **{player1}** treated **{player2}**'s wounds!"
            ]
            
            try:
                if not ALLIANCE_EVENTS:
                    alliance_events = fallback_alliance_events
                else:
                    alliance_events = ALLIANCE_EVENTS
            except (NameError, AttributeError):
                alliance_events = fallback_alliance_events
            
            event = random.choice(alliance_events)
            message = event.format(player1=player1_name_with_title, player2=player2_name_with_title)
            
            return message
            
        except GameError:
            raise
        except Exception as e:
            logger.error(f"Error in alliance event: {e}")
            raise EventExecutionError(f"Alliance event failed: {e}")
    
    def create_status_embed(self, game: GameState, guild: discord.Guild) -> discord.Embed:
        """Create status embed showing current game state with error handling"""
        try:
            alive_players = self.get_alive_players(game)
            alive_count = len(alive_players)
            
            # Determine embed color based on players remaining
            if alive_count > 15:
                color = 0x00FF00  # Green
            elif alive_count > 10:
                color = 0xFFFF00  # Yellow
            elif alive_count > 5:
                color = 0xFF8C00  # Orange
            else:
                color = 0xFF0000  # Red
            
            embed = discord.Embed(
                title=f"🏹 **HUNGER GAMES - ROUND {game['round']}** 🏹",
                color=color
            )
            
            # Phase indicator
            phase_index = min(game["round"] // 3, len(GAME_PHASES) - 1)
            try:
                embed.description = GAME_PHASES[phase_index]
            except (NameError, AttributeError, IndexError):
                embed.description = f"Round {game['round']} - {alive_count} tributes remaining"
            
            # Players remaining
            embed.add_field(
                name="👥 **Tributes Remaining**",
                value=f"**{alive_count}** survivors",
                inline=True
            )
            
            # Current phase
            if alive_count <= 5:
                status_text = "**FINAL SHOWDOWN**"
            elif alive_count <= 10:
                status_text = "**BLOODBATH PHASE**"
            else:
                status_text = "**SURVIVAL PHASE**"
            
            embed.add_field(
                name="⚔️ **Status**",
                value=status_text,
                inline=True
            )
            
            # Show top killers if any
            self._add_killer_leaderboard(embed, game)
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating status embed: {e}")
            # Return minimal embed
            return discord.Embed(
                title="📊 **Game Status**",
                description="Status information unavailable",
                color=0x808080
            )
    
    def _add_killer_leaderboard(self, embed: discord.Embed, game: GameState):
        """Add killer leaderboard to status embed"""
        try:
            killers = [
                (pid, pdata) for pid, pdata in game["players"].items() 
                if pdata.get("kills", 0) > 0 and pdata.get("alive", False)
            ]
            
            if killers:
                killers.sort(key=lambda x: x[1]["kills"], reverse=True)
                top_killers = killers[:3]
                killer_text = "\n".join([
                    f"🗡️ **{pdata['name']}**: {pdata['kills']} kills" 
                    for _, pdata in top_killers
                ])
                embed.add_field(
                    name="💀 **Most Dangerous**",
                    value=killer_text,
                    inline=False
                )
        except Exception as e:
            logger.error(f"Error adding killer leaderboard: {e}")
    
    async def check_game_end(self, game: GameState, channel: discord.TextChannel) -> bool:
        """Check if game should end and handle victory with spam prevention"""
        try:
            if not self._validate_game_state(game):
                logger.error("Invalid game state during end check")
                return True  # End the game if state is corrupted
            
            alive_players = self.get_alive_players(game)
            alive_count = len(alive_players)
            
            # Initialize milestone tracking if not present
            if "milestones_shown" not in game:
                game["milestones_shown"] = set()
            
            if alive_count <= 1:
                await self.handle_victory(game, channel)
                return True
            elif (alive_count == 3 and "final_three" not in game["milestones_shown"] and 
                  game["round"] > 2):
                await self._send_milestone_message(game, channel, "final_three", 3)
            elif (alive_count == 2 and "final_duel" not in game["milestones_shown"] and 
                  game["round"] > 3):
                await self._send_milestone_message(game, channel, "final_duel", 2)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking game end: {e}")
            return True  # End game on error to prevent infinite loops
    
    async def _send_milestone_message(self, game: GameState, channel: discord.TextChannel, 
                                    milestone: str, count: int):
        """Send milestone message for game progression"""
        try:
            if milestone == "final_three":
                embed = discord.Embed(
                    title="⚔️ **FINAL THREE** ⚔️",
                    description="🔥 **THE END APPROACHES!** Only 3 tributes remain!",
                    color=0xFF0000
                )
            elif milestone == "final_duel":
                embed = discord.Embed(
                    title="💀 **FINAL DUEL** 💀", 
                    description="🔥 **THE END APPROACHES!** Only 2 tributes remain in the ultimate showdown!",
                    color=0xFF0000
                )
            else:
                return
            
            await channel.send(embed=embed)
            game["milestones_shown"].add(milestone)
            
        except Exception as e:
            logger.error(f"Error sending milestone message: {e}")
    
    async def handle_victory(self, game: GameState, channel: discord.TextChannel):
        """Handle end of game and victory with comprehensive results"""
        try:
            alive_players = self.get_alive_players(game)
            
            if alive_players:
                winner_id = alive_players[0]
                winner = game["players"][winner_id]
                
                # Calculate and award prize
                prize = await self._calculate_and_award_prize(game, channel, winner_id)
                
                # Update all player statistics
                await self._update_all_player_stats(game, channel.guild)
                
                # Create comprehensive victory display
                await self._send_victory_display(game, channel, winner_id, winner, prize)
            else:
                # No survivors (shouldn't happen, but just in case)
                embed = discord.Embed(
                    title="💀 **NO SURVIVORS** 💀",
                    description="The arena has claimed all tributes...",
                    color=0x000000
                )
                await channel.send(embed=embed)
            
            logger.info(f"Game completed in guild {channel.guild.id}")
            
        except Exception as e:
            logger.error(f"Error handling victory: {e}", exc_info=True)
            # Send basic completion message on error
            try:
                await channel.send("🏆 **The Hunger Games have concluded!**")
            except Exception:
                pass
    
    async def _calculate_and_award_prize(self, game: GameState, channel: discord.TextChannel, 
                                       winner_id: str) -> int:
        """Calculate and award prize to winner"""
        try:
            base_reward = await self.config.guild(channel.guild).base_reward()
            total_players = len(game["players"])
            prize = self.calculate_prize_pool(total_players, base_reward)
            
            # Award prize
            winner_member = channel.guild.get_member(int(winner_id))
            if winner_member:
                await bank.deposit_credits(winner_member, prize)
                logger.info(f"Awarded {prize} credits to winner {winner_id}")
            
            return prize
            
        except Exception as e:
            logger.error(f"Error calculating/awarding prize: {e}")
            return 0
    
    async def _update_all_player_stats(self, game: GameState, guild: discord.Guild):
        """Update statistics for all players"""
        try:
            # Update stats for winner
            alive_players = self.get_alive_players(game)
            if alive_players:
                winner_id = alive_players[0]
                winner = game["players"][winner_id]
                
                async with self.config.member_from_ids(guild.id, int(winner_id)).all() as member_data:
                    member_data["wins"] += 1
                    member_data["kills"] += winner["kills"]
            
            # Update death stats for all eliminated players
            for eliminated in game.get("eliminated", []):
                try:
                    async with self.config.member_from_ids(guild.id, int(eliminated["id"])).all() as member_data:
                        member_data["deaths"] += 1
                except Exception as e:
                    logger.warning(f"Failed to update death stats for {eliminated['id']}: {e}")
            
            # Update revive stats for all players who were revived
            for player_id, player_data in game["players"].items():
                revive_count = player_data.get("revives", 0)
                if revive_count > 0:
                    try:
                        async with self.config.member_from_ids(guild.id, int(player_id)).all() as member_data:
                            member_data["revives"] += revive_count
                    except Exception as e:
                        logger.warning(f"Failed to update revive stats for {player_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error updating player stats: {e}")
    
    async def _send_victory_display(self, game: GameState, channel: discord.TextChannel, 
                                  winner_id: str, winner: PlayerData, prize: int):
        """Send the comprehensive victory display"""
        try:
            total_players = len(game["players"])
            
            # Main victory embed
            embed = discord.Embed(color=0xFFD700)
            embed.set_author(name="🏆 WINNER!")
            
            # Winner section
            winner_text = f"👑 **{winner['name']}** the Champion\n"
            winner_text += f"**Reward:** {prize:,} 💰"
            
            embed.add_field(name="", value=winner_text, inline=False)
            
            # Stylized game title
            try:
                title_art = random.choice(VICTORY_TITLE_ART)
                embed.add_field(name="", value=title_art, inline=False)
            except (NameError, AttributeError):
                embed.add_field(
                    name="🏹 **THE HUNGER GAMES** 🏹",
                    value="```\n╔═══════════════════════════╗\n║     BATTLE ROYALE         ║\n╚═══════════════════════════╝\n```",
                    inline=False
                )
            
            embed.add_field(name="", value=f"**Total Players:** {total_players}", inline=False)
            
            await channel.send(embed=embed)
            
            # Second embed with detailed rankings
            await self._send_rankings_embed(game, channel)
            
        except Exception as e:
            logger.error(f"Error sending victory display: {e}")
    
    async def _send_rankings_embed(self, game: GameState, channel: discord.TextChannel):
        """Send detailed rankings embed"""
        try:
            stats_embed = discord.Embed(color=0x36393F)
            
            # Calculate rankings
            runner_ups = self._calculate_runner_ups(game)
            kill_leaders = self._calculate_kill_leaders(game)
            revive_leaders = self._calculate_revive_leaders(game)
            
            # Add ranking fields
            self._add_ranking_fields(stats_embed, runner_ups, kill_leaders, revive_leaders)
            
            # Footer
            stats_embed.set_footer(
                text="🏹 The Hunger Games • Battle Royale Complete"
            )
            
            await channel.send(embed=stats_embed)
            
        except Exception as e:
            logger.error(f"Error sending rankings embed: {e}")
    
    def _add_ranking_fields(self, embed: discord.Embed, runner_ups: List[tuple], 
                          kill_leaders: List[tuple], revive_leaders: List[tuple]):
        """Add ranking fields to embed"""
        try:
            # Runners-up
            if runner_ups:
                runner_text = ""
                for i, (player_id, player_data) in enumerate(runner_ups, 2):
                    try:
                        medal = PLACEMENT_MEDALS.get(i, f"{i}.")
                    except (NameError, AttributeError):
                        medal = f"{i}."
                    runner_text += f"{medal} {player_data['name']}\n"
                
                embed.add_field(
                    name="🥈 **Runners-up**",
                    value=runner_text if runner_text else "None",
                    inline=True
                )
            
            # Kill leaders
            if kill_leaders:
                kills_text = ""
                for player_id, player_data in kill_leaders:
                    kills_text += f"**{player_data['kills']}** {player_data['name']}\n"
                
                embed.add_field(
                    name="⚔️ **Most Kills**",
                    value=kills_text if kills_text else "None",
                    inline=True
                )
            
            # Revive leaders
            if revive_leaders:
                revives_text = ""
                for player_id, player_data in revive_leaders:
                    revive_count = player_data.get('revives', 0)
                    revives_text += f"**{revive_count}** {player_data['name']}\n"
                
                embed.add_field(
                    name="✨ **Most Revives**",
                    value=revives_text if revives_text else "None", 
                    inline=True
                )
        except Exception as e:
            logger.error(f"Error adding ranking fields: {e}")
    
    def _calculate_runner_ups(self, game: GameState) -> List[tuple]:
        """Calculate top 4 runner-ups based on elimination order"""
        try:
            eliminated_sorted = sorted(
                game.get("eliminated", []), 
                key=lambda x: x.get("round", 0), 
                reverse=True
            )
            
            runner_ups = []
            for eliminated in eliminated_sorted[:4]:
                player_id = eliminated.get("id")
                if player_id and player_id in game.get("players", {}):
                    runner_ups.append((player_id, game["players"][player_id]))
            
            return runner_ups
        except Exception as e:
            logger.error(f"Error calculating runner-ups: {e}")
            return []
    
    def _calculate_kill_leaders(self, game: GameState) -> List[tuple]:
        """Calculate players with most kills"""
        try:
            kill_leaders = []
            
            for player_id, player_data in game.get("players", {}).items():
                if player_data.get("kills", 0) > 0:
                    kill_leaders.append((player_id, player_data))
            
            kill_leaders.sort(key=lambda x: x[1].get("kills", 0), reverse=True)
            return kill_leaders[:5]
        except Exception as e:
            logger.error(f"Error calculating kill leaders: {e}")
            return []
    
    def _calculate_revive_leaders(self, game: GameState) -> List[tuple]:
        """Calculate players with most revives"""
        try:
            revive_leaders = []
            
            for player_id, player_data in game.get("players", {}).items():
                revive_count = player_data.get("revives", 0)
                if revive_count > 0:
                    revive_leaders.append((player_id, player_data))
            
            revive_leaders.sort(key=lambda x: x[1].get("revives", 0), reverse=True)
            return revive_leaders[:5]
        except Exception as e:
            logger.error(f"Error calculating revive leaders: {e}")
            return []
