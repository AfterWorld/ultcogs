# __init__.py - IMPROVED VERSION
"""
Hunger Games Battle Royale Cog for Red-DiscordBot

A comprehensive battle royale game where players fight to be the last survivor.
Features automatic events, sponsor revivals, dynamic rewards, and detailed statistics.
"""

import discord
from redbot.core import commands, Config, bank
import asyncio
import random
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from .constants import (
    DEFAULT_GUILD_CONFIG, DEFAULT_MEMBER_CONFIG, EMOJIS,
    DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS
)
from .game import GameEngine, GameError, InvalidGameStateError
from .utils import *
from .config import GameConfig

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class GameTiming:
    """Centralized timing configuration"""
    MIN_FINAL_DUEL_INTERVAL: int = 8
    MIN_ENDGAME_INTERVAL: int = 15
    MIN_EARLY_GAME_INTERVAL: int = 25
    ENDGAME_THRESHOLD: int = 5
    FINAL_DUEL_THRESHOLD: int = 2
    STATUS_UPDATE_INTERVAL: int = 6


class InputValidator:
    """Handles all input validation for the game"""
    
    @staticmethod
    def validate_countdown(countdown: int) -> tuple[bool, str]:
        """Validate countdown parameter"""
        if not isinstance(countdown, int):
            return False, "Countdown must be a number!"
        
        if countdown < 10:
            return False, "Countdown must be at least 10 seconds!"
        
        if countdown > 300:
            return False, "Countdown cannot exceed 5 minutes!"
        
        return True, ""
    
    @staticmethod
    def validate_game_state(game: Dict) -> bool:
        """Validate game state integrity"""
        try:
            required_keys = ["players", "round", "status", "eliminated"]
            if not all(key in game for key in required_keys):
                return False
            
            if game["round"] < 0:
                return False
            
            if not isinstance(game["players"], dict):
                return False
            
            # Validate player data structure
            for player_id, player_data in game["players"].items():
                if not isinstance(player_data, dict):
                    return False
                
                required_player_keys = ["name", "alive", "kills"]
                if not all(key in player_data for key in required_player_keys):
                    return False
            
            return True
        except Exception:
            return False


class EventHandler:
    """Handles event execution with proper error handling"""
    
    def __init__(self, game_engine):
        self.game_engine = game_engine
        self.handlers = {
            "death": self._handle_death_event,
            "survival": self._handle_survival_event,
            "sponsor": self._handle_sponsor_event,
            "alliance": self._handle_alliance_event,
            "crate": self._handle_crate_event
        }
    
    async def execute_event(self, event_type: str, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute event using handler mapping with error handling"""
        try:
            handler = self.handlers.get(event_type)
            if not handler:
                logger.warning(f"Unknown event type: {event_type}")
                return None
            
            return await handler(game, channel)
            
        except GameError as e:
            logger.error(f"Game error in {event_type} event: {e}")
            return self._get_fallback_message(event_type)
        except Exception as e:
            logger.error(f"Unexpected error in {event_type} event: {e}", exc_info=True)
            return None
    
    async def _handle_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_death_event(game, channel)
    
    async def _handle_survival_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_survival_event(game)
    
    async def _handle_sponsor_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_sponsor_event(game)
    
    async def _handle_alliance_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_alliance_event(game)
    
    async def _handle_crate_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_crate_event(game)
    
    def _get_fallback_message(self, event_type: str) -> str:
        """Get fallback message for failed events"""
        fallbacks = {
            "death": "💀 | A mysterious death occurred in the arena...",
            "survival": "🌿 | Someone managed to survive another day...",
            "sponsor": "🎁 | A sponsor gift was mysteriously delivered...",
            "alliance": "🤝 | Tributes formed an unexpected alliance...",
            "crate": "📦 | Someone discovered hidden supplies..."
        }
        return fallbacks.get(event_type, "⚡ | Something happened in the arena...")


class HungerGames(commands.Cog):
    """A Hunger Games style battle royale game for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)
        self.config.register_member(**DEFAULT_MEMBER_CONFIG)
        
        self.active_games: Dict[int, Dict] = {}
        self.game_engine = GameEngine(bot, self.config)
        self.event_handler = EventHandler(self.game_engine)
        self.validator = InputValidator()
        self.timing = GameTiming()
        
        # Performance optimization - cache alive players
        self._alive_cache = {}
        self._cache_round = {}
    
    def cog_unload(self):
        """Cancel all running games when cog is unloaded"""
        for guild_id in list(self.active_games.keys()):
            if "task" in self.active_games[guild_id]:
                self.active_games[guild_id]["task"].cancel()
        logger.info("Hunger Games cog unloaded, all games cancelled")
    
    @commands.command(name="he")
    async def hunger_games_event(self, ctx, countdown: int = 60):
        """Start a Hunger Games battle royale! React to join!"""
        guild_id = ctx.guild.id
        
        # Enhanced input validation
        valid, error_msg = self.validator.validate_countdown(countdown)
        if not valid:
            return await ctx.send(f"❌ {error_msg}")
        
        if guild_id in self.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        try:
            # Create the game instance with validation
            await self._initialize_new_game(ctx, countdown)
        except Exception as e:
            logger.error(f"Failed to initialize game in guild {guild_id}: {e}", exc_info=True)
            await ctx.send("❌ Failed to start the game. Please try again.")
    
    async def _initialize_new_game(self, ctx, countdown: int):
        """Initialize a new game with proper error handling"""
        guild_id = ctx.guild.id
        
        self.active_games[guild_id] = {
            "channel": ctx.channel,
            "players": {},
            "status": "recruiting",
            "round": 0,
            "eliminated": [],
            "sponsor_used": [],
            "reactions": set(),
            "milestones_shown": set()
        }
        
        # Send recruitment embed
        embed = create_recruitment_embed(countdown)
        message = await ctx.send(embed=embed)
        await message.add_reaction(EMOJIS["bow"])
        
        self.active_games[guild_id]["message"] = message
        
        # Start recruitment countdown
        await self.recruitment_countdown(guild_id, countdown)
    
    async def recruitment_countdown(self, guild_id: int, countdown: int):
        """Handle the recruitment countdown and reaction monitoring"""
        game = self.active_games[guild_id]
        message = game["message"]
        channel = game["channel"]
        
        end_time = asyncio.get_event_loop().time() + countdown
        
        try:
            while asyncio.get_event_loop().time() < end_time:
                remaining = int(end_time - asyncio.get_event_loop().time())
                
                # Update embed every 10 seconds or at key intervals
                if remaining % 10 == 0 or remaining <= 5:
                    await self._update_recruitment_message(game, message, channel, remaining)
                
                await asyncio.sleep(1)
        except discord.NotFound:
            # Message was deleted, cancel game
            logger.info(f"Recruitment message deleted, cancelling game in guild {guild_id}")
            del self.active_games[guild_id]
            return
        except Exception as e:
            logger.error(f"Error during recruitment countdown: {e}")
        
        # Recruitment ended, start the game
        await self.start_battle_royale(guild_id)
    
    async def _update_recruitment_message(self, game: Dict, message: discord.Message, 
                                        channel: discord.TextChannel, remaining: int):
        """Update recruitment message with current player count"""
        try:
            # Get current reactions
            fresh_message = await channel.fetch_message(message.id)
            bow_reaction = None
            
            for reaction in fresh_message.reactions:
                if str(reaction.emoji) == EMOJIS["bow"]:
                    bow_reaction = reaction
                    break
            
            if bow_reaction:
                # Get users who reacted (excluding bot)
                async for user in bow_reaction.users():
                    if not user.bot and user.id not in game["reactions"]:
                        game["reactions"].add(user.id)
                        game["players"][str(user.id)] = {
                            "name": user.display_name,
                            "title": get_random_player_title(),
                            "alive": True,
                            "kills": 0,
                            "revives": 0,
                            "district": get_random_district()
                        }
            
            # Update embed with current player count
            current_players = len(game["players"])
            embed = create_recruitment_embed(remaining, current_players)
            await message.edit(embed=embed)
            
        except discord.Forbidden:
            logger.warning("Missing permissions to edit recruitment message")
        except Exception as e:
            logger.error(f"Error updating recruitment message: {e}")
    
    async def start_battle_royale(self, guild_id: int):
        """Start the actual battle royale game with validation"""
        try:
            game = self.active_games[guild_id]
            channel = game["channel"]
            
            # Validate game state before starting
            if not self.validator.validate_game_state(game):
                raise InvalidGameStateError("Game state is invalid before start")
            
            # Check if we have enough players
            player_count = len(game["players"])
            if player_count < 2:
                embed = discord.Embed(
                    title="❌ **INSUFFICIENT TRIBUTES**",
                    description="Need at least 2 brave souls to enter the arena!",
                    color=0xFF0000
                )
                await channel.send(embed=embed)
                del self.active_games[guild_id]
                return
            
            game["status"] = "active"
            
            # Send game start messages
            await self._send_game_start_messages(game, player_count)
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.game_loop(guild_id))
            logger.info(f"Started Hunger Games with {player_count} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to start battle royale in guild {guild_id}: {e}", exc_info=True)
            await channel.send("❌ Failed to start the battle royale. Game cancelled.")
            if guild_id in self.active_games:
                del self.active_games[guild_id]
    
    async def _send_game_start_messages(self, game: Dict, player_count: int):
        """Send game start and player introduction messages"""
        channel = game["channel"]
        
        # Game start message
        embed = create_game_start_embed(player_count)
        await channel.send(embed=embed)
        
        await asyncio.sleep(3)
        
        # Show initial tributes
        embed = discord.Embed(
            title="👥 **THE TRIBUTES**",
            description="Meet this year's brave competitors:",
            color=0x4169E1
        )
        
        player_list = format_player_list(game["players"], show_status=False)
        embed.add_field(
            name="🏹 **Entered the Arena**",
            value=player_list,
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # Add extra dramatic pause for small games
        if player_count <= 4:
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="⚡ **INTENSE SHOWDOWN INCOMING** ⚡",
                description=f"With only **{player_count} tributes**, this will be a lightning-fast battle!\n"
                           f"Every second counts... every move matters...",
                color=0xFF6B35
            )
            await channel.send(embed=embed)
    
    async def game_loop(self, guild_id: int):
        """Main game loop - IMPROVED AND MODULAR"""
        game = self.active_games[guild_id]
        channel = game["channel"]
        
        try:
            logger.info(f"Starting game loop for guild {guild_id}")
            
            await self._initialize_game_loop(game)
            
            while game["status"] == "active":
                # Process a single round
                await self._process_game_round(game, channel)
                
                # Check if game should end
                if await self.game_engine.check_game_end(game, channel):
                    break
                
                # Calculate and wait for next round
                sleep_time = self._calculate_sleep_time(game)
                logger.debug(f"Guild {guild_id}: Sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.info(f"Game {guild_id} was cancelled")
        except GameError as e:
            logger.error(f"Game error in guild {guild_id}: {e}")
            await self._handle_game_error(game, channel, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in game loop for guild {guild_id}: {e}", exc_info=True)
            await self._handle_game_error(game, channel, "Technical difficulties")
        finally:
            await self._cleanup_game(guild_id)
    
    async def _initialize_game_loop(self, game: Dict):
        """Initialize game loop settings"""
        event_interval = await self.config.guild(game["channel"].guild).event_interval()
        game["event_interval"] = event_interval
        await asyncio.sleep(3)  # Initial pause
    
    async def _process_game_round(self, game: Dict, channel: discord.TextChannel):
        """Process a single game round"""
        game["round"] += 1
        alive_players = self.game_engine.get_alive_players(game)
        
        logger.debug(f"Round {game['round']}: {len(alive_players)} players alive")
        
        # Validate game state
        if not self.validator.validate_game_state(game):
            raise InvalidGameStateError(f"Game state corrupted in round {game['round']}")
        
        # Execute events if players remain
        if len(alive_players) > 1:
            await self._execute_round_events(game, channel)
        
        # Send status update periodically
        await self._maybe_send_status_update(game, channel)
    
    async def _execute_round_events(self, game: Dict, channel: discord.TextChannel):
        """Execute events for the current round"""
        try:
            await self.execute_combined_events(game, channel)
        except Exception as e:
            logger.error(f"Error executing round events: {e}")
            # Send fallback message
            embed = discord.Embed(
                description="⚠️ Something mysterious happened in the arena...",
                color=0xFFFF00
            )
            await channel.send(embed=embed)
    
    async def _maybe_send_status_update(self, game: Dict, channel: discord.TextChannel):
        """Send status update if needed"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        if (game["round"] % self.timing.STATUS_UPDATE_INTERVAL == 0 and 
            alive_count > 8):
            embed = self.game_engine.create_status_embed(game, channel.guild)
            await channel.send(embed=embed)
    
    def _calculate_sleep_time(self, game: Dict) -> int:
        """Calculate appropriate sleep time based on game state"""
        alive_count = len(self.game_engine.get_alive_players(game))
        event_interval = game.get("event_interval", 30)
        
        if alive_count <= self.timing.FINAL_DUEL_THRESHOLD:
            return max(self.timing.MIN_FINAL_DUEL_INTERVAL, event_interval // 3)
        elif alive_count <= 3:
            return max(10, event_interval // 3)
        elif alive_count <= self.timing.ENDGAME_THRESHOLD:
            return max(12, event_interval // 2)
        elif alive_count <= 10:
            return max(self.timing.MIN_ENDGAME_INTERVAL, event_interval // 2)
        else:
            return max(self.timing.MIN_EARLY_GAME_INTERVAL, event_interval)
    
    async def _handle_game_error(self, game: Dict, channel: discord.TextChannel, error_msg: str):
        """Handle game errors gracefully"""
        try:
            embed = discord.Embed(
                title="❌ **ARENA MALFUNCTION**",
                description=f"The arena experienced {error_msg}. Game ended.",
                color=0xFF0000
            )
            await channel.send(embed=embed)
        except Exception:
            logger.error("Failed to send error message to channel")
    
    async def _cleanup_game(self, guild_id: int):
        """Clean up game resources"""
        logger.info(f"Cleaning up game for guild {guild_id}")
        if guild_id in self.active_games:
            del self.active_games[guild_id]
        
        # Clear cache
        self._alive_cache.pop(guild_id, None)
        self._cache_round.pop(guild_id, None)
    
    async def execute_combined_events(self, game: Dict, channel: discord.TextChannel):
        """Execute multiple events in one round - RUMBLE STYLE WITH IMPROVED ERROR HANDLING"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        # Determine number of events
        num_events = self._calculate_event_count(alive_count)
        
        # Get event weights
        weights = get_event_weights()
        weights = self._adjust_weights_for_game_state(weights, alive_count)
        
        # Execute events
        event_messages = []
        
        for i in range(num_events):
            if len(self.game_engine.get_alive_players(game)) <= 1:
                break
            
            # Choose and execute event
            event_type = self._choose_event_type(weights)
            message = await self.event_handler.execute_event(event_type, game, channel)
            
            if message:
                event_messages.append(message)
            
            await asyncio.sleep(0.5)
        
        # Send combined events in Rumble format
        await self._send_rumble_style_events(game, channel, event_messages)
    
    def _calculate_event_count(self, alive_count: int) -> int:
        """Calculate number of events based on alive players"""
        if alive_count <= 3:
            return random.randint(1, 2)
        elif alive_count <= 6:
            return random.randint(2, 3)
        elif alive_count <= 12:
            return random.randint(2, 4)
        else:
            return random.randint(3, 5)
    
    def _adjust_weights_for_game_state(self, weights: Dict[str, int], alive_count: int) -> Dict[str, int]:
        """Adjust event weights based on game state"""
        if alive_count <= 2:
            weights.update({"death": 70, "survival": 10, "sponsor": 10, "alliance": 5, "crate": 5})
        elif alive_count <= 3:
            weights.update({"death": 55, "survival": 15, "sponsor": 15, "alliance": 5, "crate": 10})
        elif alive_count <= 5:
            weights.update({"death": 45, "survival": 20, "sponsor": 15, "alliance": 10, "crate": 10})
        elif alive_count <= 10:
            weights.update({"death": 35, "survival": 25, "sponsor": 15, "alliance": 15, "crate": 10})
        
        return weights
    
    def _choose_event_type(self, weights: Dict[str, int]) -> str:
        """Choose event type based on weights"""
        event_types = list(weights.keys())
        event_weights = list(weights.values())
        return random.choices(event_types, weights=event_weights)[0]
    
    async def _send_rumble_style_events(self, game: Dict, channel: discord.TextChannel, 
                                      event_messages: List[str]):
        """Send events in Rumble style format"""
        if not event_messages:
            logger.warning("No event messages to send")
            return
        
        try:
            alive_after_events = len(self.game_engine.get_alive_players(game))
            
            # Build Rumble format content
            rumble_content = f"**Round {game['round']}**\n"
            rumble_content += "\n".join(event_messages)
            rumble_content += f"\n\n**Players Left: {alive_after_events}**"
            
            # Create embed with Rumble styling
            embed = discord.Embed(
                description=rumble_content,
                color=0x2F3136
            )
            
            await channel.send(embed=embed)
            logger.debug(f"Sent Rumble-style embed with {len(event_messages)} events")
            
        except Exception as e:
            logger.error(f"Failed to send Rumble-style events: {e}")
    
    # [Rest of the command methods stay the same but with better error handling]
    @commands.group(invoke_without_command=True)
    async def hungergames(self, ctx):
        """Hunger Games battle royale commands"""
        await ctx.send_help()
    
    @hungergames.command(name="alive")
    async def hg_alive(self, ctx):
        """Show current alive players in the active game"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        try:
            game = self.active_games[guild_id]
            alive_players = self.game_engine.get_alive_players(game)
            
            if not alive_players:
                return await ctx.send("💀 No survivors remain!")
            
            embed = create_alive_players_embed(game, alive_players)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing alive players: {e}")
            await ctx.send("❌ Error retrieving player information.")
    
    @hungergames.command(name="stats")
    async def hg_stats(self, ctx, member: discord.Member = None):
        """View Hunger Games statistics for yourself or another player"""
        try:
            if member is None:
                member = ctx.author
            
            member_data = await self.config.member(member).all()
            embed = create_player_stats_embed(member_data, member)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            await ctx.send("❌ Error retrieving statistics.")
    
    @hungergames.command(name="stop")
    @commands.has_permissions(manage_guild=True)
    async def hg_stop(self, ctx):
        """Stop the current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active game to stop!")
        
        try:
            game = self.active_games[guild_id]
            
            # Cancel the game task
            if "task" in game:
                game["task"].cancel()
            
            # Clean up
            await self._cleanup_game(guild_id)
            
            embed = discord.Embed(
                title="🛑 **GAME TERMINATED**",
                description="The Hunger Games have been forcibly ended by the Capitol.",
                color=0x000000
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Game manually stopped in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error stopping game: {e}")
            await ctx.send("❌ Error stopping the game.")


async def setup(bot):
    """Required function for loading the cog"""
    await bot.add_cog(HungerGames(bot))
