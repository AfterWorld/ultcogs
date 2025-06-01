# game_logic.py
"""
Core game logic and mechanics for Hunger Games cog
"""

import discord
import asyncio
import random
import logging
from typing import Dict, List, Optional, Set
from redbot.core import bank

from .constants import (
    DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS,
    VICTORY_PHRASES, VICTORY_SCENARIOS, EMOJIS
)

logger = logging.getLogger(__name__)


class GameError(Exception):
    """Base exception for game-related errors"""
    pass


class InvalidGameStateError(GameError):
    """Raised when game state is invalid"""
    pass


class GameEngine:
    """Core game engine for Hunger Games logic"""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
    
    def get_alive_players(self, game: Dict) -> List[Dict]:
        """Get list of alive players"""
        return [player for player in game["players"].values() if player["alive"]]
    
    def get_dead_players(self, game: Dict) -> List[Dict]:
        """Get list of dead players"""
        return [player for player in game["players"].values() if not player["alive"]]
    
    async def check_game_end(self, game: Dict, channel: discord.TextChannel) -> bool:
        """Check if game should end and handle victory"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) <= 1:
            await self._handle_game_victory(game, channel, alive_players)
            return True
        
        return False
    
    async def _handle_game_victory(self, game: Dict, channel: discord.TextChannel, alive_players: List[Dict]):
        """Handle game victory and rewards"""
        try:
            if len(alive_players) == 1:
                winner = alive_players[0]
                await self._announce_winner(channel, winner, game)
                await self._award_victory_rewards(channel.guild, winner, game)
            else:
                # No survivors
                embed = discord.Embed(
                    title="💀 **NO SURVIVORS** 💀",
                    description="The arena claimed all tributes... The Capitol is not pleased.",
                    color=0x000000
                )
                await channel.send(embed=embed)
            
            game["status"] = "finished"
            
        except Exception as e:
            logger.error(f"Error handling game victory: {e}")
    
    async def _announce_winner(self, channel: discord.TextChannel, winner: Dict, game: Dict):
        """Announce the winner with dramatic flair"""
        victory_phrase = random.choice(VICTORY_PHRASES)
        
        embed = discord.Embed(
            title="🏆 **VICTOR OF THE HUNGER GAMES** 🏆",
            description=f"**{winner['name']} {winner['title']}** has emerged victorious!",
            color=0xFFD700
        )
        
        embed.add_field(
            name="🎊 **Victory Moment**",
            value=victory_phrase,
            inline=False
        )
        
        stats_text = f"**Eliminations:** {winner['kills']}\n"
        stats_text += f"**Revivals:** {winner.get('revives', 0)}\n"
        stats_text += f"**District:** {winner.get('district', 'Unknown')}\n"
        stats_text += f"**Rounds Survived:** {game['round']}"
        
        embed.add_field(
            name="📊 **Final Stats**",
            value=stats_text,
            inline=True
        )
        
        embed.set_footer(text="🎉 Congratulations to our victor!")
        
        await channel.send(embed=embed)
    
    async def _award_victory_rewards(self, guild: discord.Guild, winner: Dict, game: Dict):
        """Award credits and update stats for winner"""
        try:
            # Get winner member object
            winner_member = None
            for member_id, player_data in game["players"].items():
                if player_data == winner:
                    winner_member = guild.get_member(int(member_id))
                    break
            
            if not winner_member:
                logger.warning("Could not find winner member for rewards")
                return
            
            # Calculate rewards
            base_reward = await self.config.guild(guild).base_reward()
            kill_bonus = winner['kills'] * 50
            survival_bonus = min(game['round'] * 10, 500)
            total_reward = base_reward + kill_bonus + survival_bonus
            
            # Award credits
            try:
                await bank.deposit_credits(winner_member, total_reward)
            except Exception as e:
                logger.error(f"Failed to award credits: {e}")
            
            # Update stats
            await self._update_winner_stats(winner_member, winner, game)
            
            logger.info(f"Awarded {total_reward} credits to winner {winner_member.id} in guild {guild.id}")
            
        except Exception as e:
            logger.error(f"Error awarding victory rewards: {e}")
    
    async def _update_winner_stats(self, member: discord.Member, winner_data: Dict, game: Dict):
        """Update winner's statistics"""
        try:
            current_stats = await self.config.member(member).all()
            
            # Update stats
            current_stats["wins"] += 1
            current_stats["kills"] += winner_data['kills']
            current_stats["revives"] += winner_data.get('revives', 0)
            current_stats["games_played"] += 1
            
            # Save updated stats
            await self.config.member(member).set(current_stats)
            
        except Exception as e:
            logger.error(f"Error updating winner stats: {e}")
    
    async def execute_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute a death event"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) < 2:
            return None
        
        # Choose victim(s)
        if len(alive_players) >= 6 and random.random() < 0.15:
            # Multi-kill event
            num_victims = min(random.randint(2, 3), len(alive_players) - 1)
            victims = random.sample(alive_players, num_victims)
        else:
            # Single kill
            victims = [random.choice(alive_players)]
        
        # Choose killer (can be environment or another player)
        if random.random() < 0.6 and len(alive_players) > len(victims):
            # Player vs player
            potential_killers = [p for p in alive_players if p not in victims]
            killer = random.choice(potential_killers)
            killer_name = f"{killer['name']} {killer['title']}"
            killer['kills'] += len(victims)
        else:
            # Environmental death
            killer = None
            killer_name = None
        
        # Execute the deaths
        for victim in victims:
            victim['alive'] = False
            game['eliminated'].append(victim['name'])
        
        # Choose appropriate death event
        death_event = random.choice(DEATH_EVENTS)
        
        # Format the event message
        if len(victims) == 1:
            victim_names = f"{victims[0]['name']} {victims[0]['title']}"
        else:
            victim_list = [f"{v['name']} {v['title']}" for v in victims]
            if len(victims) == 2:
                victim_names = f"{victim_list[0]} and {victim_list[1]}"
            else:
                victim_names = f"{', '.join(victim_list[:-1])}, and {victim_list[-1]}"
        
        if killer_name:
            message = death_event.format(player=victim_names, killer=killer_name)
        else:
            message = death_event.format(player=victim_names)
        
        # Update stats for eliminated players
        await self._update_death_stats(channel.guild, victims)
        
        return message
    
    async def _update_death_stats(self, guild: discord.Guild, victims: List[Dict]):
        """Update stats for eliminated players"""
        try:
            for victim in victims:
                # Find the member
                victim_member = None
                for member in guild.members:
                    if member.display_name == victim['name']:
                        victim_member = member
                        break
                
                if victim_member:
                    current_stats = await self.config.member(victim_member).all()
                    current_stats["deaths"] += 1
                    current_stats["kills"] += victim['kills']
                    current_stats["revives"] += victim.get('revives', 0)
                    current_stats["games_played"] += 1
                    await self.config.member(victim_member).set(current_stats)
                    
        except Exception as e:
            logger.error(f"Error updating death stats: {e}")
    
    async def execute_survival_event(self, game: Dict) -> Optional[str]:
        """Execute a survival event"""
        alive_players = self.get_alive_players(game)
        
        if not alive_players:
            return None
        
        # Choose 1-3 players for survival event
        num_players = min(random.randint(1, 3), len(alive_players))
        players = random.sample(alive_players, num_players)
        
        survival_event = random.choice(SURVIVAL_EVENTS)
        
        if len(players) == 1:
            player_names = f"{players[0]['name']} {players[0]['title']}"
        else:
            player_list = [f"{p['name']} {p['title']}" for p in players]
            if len(players) == 2:
                player_names = f"{player_list[0]} and {player_list[1]}"
            else:
                player_names = f"{', '.join(player_list[:-1])}, and {player_list[-1]}"
        
        return survival_event.format(player=player_names)
    
    async def execute_sponsor_event(self, game: Dict) -> Optional[str]:
        """Execute a sponsor revival event"""
        dead_players = self.get_dead_players(game)
        
        if not dead_players:
            return None
        
        # Check sponsor chance
        sponsor_chance = await self.config.guild_from_id(game["channel"].guild.id).sponsor_chance()
        
        if random.randint(1, 100) > sponsor_chance:
            return None
        
        # Choose a recently eliminated player
        if len(game['eliminated']) == 0:
            return None
        
        # Find the most recently eliminated player
        last_eliminated_name = game['eliminated'][-1]
        revived_player = None
        
        for player in dead_players:
            if player['name'] == last_eliminated_name and player['name'] not in game.get('sponsor_used', []):
                revived_player = player
                break
        
        if not revived_player:
            return None
        
        # Revive the player
        revived_player['alive'] = True
        revived_player['revives'] = revived_player.get('revives', 0) + 1
        game['sponsor_used'].append(revived_player['name'])
        
        sponsor_event = random.choice(SPONSOR_EVENTS)
        return sponsor_event.format(player=f"{revived_player['name']} {revived_player['title']}")
    
    async def execute_alliance_event(self, game: Dict) -> Optional[str]:
        """Execute an alliance event with proper formatting"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) < 2:
            return None
        
        # Choose 2 players for alliance
        players = random.sample(alive_players, 2)
        
        alliance_event = random.choice(ALLIANCE_EVENTS)
        
        # Format with player1 and player2
        return alliance_event.format(
            player1=f"{players[0]['name']} {players[0]['title']}",
            player2=f"{players[1]['name']} {players[1]['title']}"
        )
    
    async def execute_crate_event(self, game: Dict) -> Optional[str]:
        """Execute a supply crate event"""
        alive_players = self.get_alive_players(game)
        
        if not alive_players:
            return None
        
        # Choose 1-2 players
        num_players = min(random.randint(1, 2), len(alive_players))
        players = random.sample(alive_players, num_players)
        
        crate_event = random.choice(CRATE_EVENTS)
        
        if len(players) == 1:
            player_names = f"{players[0]['name']} {players[0]['title']}"
        else:
            player_names = f"{players[0]['name']} {players[0]['title']} and {players[1]['name']} {players[1]['title']}"
        
        return crate_event.format(player=player_names)
    
    async def check_special_events(self, game: Dict, channel: discord.TextChannel, alive_players: List[Dict]) -> Optional[str]:
        """Check for and generate special arena events"""
        alive_count = len(alive_players)
        round_num = game["round"]
        
        # Final duel event
        if alive_count == 2 and "final_duel" not in game.get("milestones_shown", set()):
            game.setdefault("milestones_shown", set()).add("final_duel")
            return await self._generate_final_duel_event(alive_players)
        
        # Endgame events
        if alive_count <= 3 and "finale_announcement" not in game.get("milestones_shown", set()):
            game.setdefault("milestones_shown", set()).add("finale_announcement")
            return "📢 **ATTENTION TRIBUTES!** Only a few remain... The finale approaches! The arena grows more dangerous by the minute!"
        
        # Midgame events
        if alive_count <= 8 and alive_count > 3 and round_num % 3 == 0:
            return await self._generate_midgame_event(game)
        
        # Early game bloodbath
        if round_num == 1 and alive_count >= 6:
            return "⚔️ **THE BLOODBATH BEGINS!** Tributes scramble for supplies at the Cornucopia as the gong sounds!"
        
        return None
    
    async def _generate_final_duel_event(self, alive_players: List[Dict]) -> str:
        """Generate final duel announcement"""
        player1 = alive_players[0]
        player2 = alive_players[1]
        
        scenarios = [
            f"🔥 **FINAL SHOWDOWN!** {player1['name']} {player1['title']} and {player2['name']} {player2['title']} face off in the ultimate battle for victory!",
            f"⚡ **THE LAST STAND!** Only {player1['name']} {player1['title']} and {player2['name']} {player2['title']} remain... Who will claim the crown?",
            f"🏆 **VICTOR'S DUEL!** {player1['name']} {player1['title']} versus {player2['name']} {player2['title']} - the arena holds its breath!",
            f"💀 **FINAL CONFRONTATION!** The last two tributes, {player1['name']} {player1['title']} and {player2['name']} {player2['title']}, prepare for their destiny!"
        ]
        
        return random.choice(scenarios)
    
    async def _generate_midgame_event(self, game: Dict) -> Optional[str]:
        """Generate midgame arena events"""
        alive_count = len(self.get_alive_players(game))
        
        events = [
            "🌪️ **ARENA EVENT:** A massive tornado tears through the battlefield, forcing tributes to seek shelter!",
            "🔥 **GAMEMAKER INTERVENTION:** Walls of fire begin closing in from the arena's edges!",
            "❄️ **SUDDEN BLIZZARD:** Freezing winds and snow engulf the arena, visibility drops to zero!",
            "🌋 **VOLCANIC ERUPTION:** Lava begins flowing from the arena's center outward!",
            "💨 **TOXIC FOG:** A deadly green mist rolls across the arena floor!",
            "🕷️ **TRACKER JACKER ATTACK:** Genetically modified wasps swarm the arena!",
            "📦 **CORNUCOPIA FEAST:** Fresh supplies appear at the center - but danger lurks for those who dare approach!",
            "🦅 **MUTTATION RELEASE:** The Gamemakers unleash engineered beasts into the arena!",
            "⚡ **ELECTRICAL STORM:** Lightning strikes begin targeting the highest points in the arena!",
            "🌊 **FLASH FLOOD:** Rising waters force tributes to higher ground!"
        ]
        
        # Filter events based on game state
        if alive_count <= 5:
            # More intense events for fewer players
            intense_events = [
                "🔥 **LIGHTNING FINALE:** The arena begins collapsing, forcing the remaining tributes together!",
                "💀 **MUTTATION HUNT:** Engineered beasts are released to hunt down the survivors!",
                "⚡ **FINAL TRAP:** The Gamemakers activate their deadliest arena feature!",
                "🌪️ **ENDGAME CHAOS:** Multiple disasters strike simultaneously!"
            ]
            events.extend(intense_events)
        
        return random.choice(events)
    
    def create_status_embed(self, game: Dict, guild: discord.Guild) -> discord.Embed:
        """Create a status embed for the current game"""
        alive_players = self.get_alive_players(game)
        total_players = len(game["players"])
        
        embed = discord.Embed(
            title="📊 **ARENA STATUS UPDATE**",
            color=0x4169E1
        )
        
        # Basic stats
        embed.add_field(
            name="👥 **Tributes Remaining**",
            value=f"{len(alive_players)}/{total_players}",
            inline=True
        )
        
        embed.add_field(
            name="🔄 **Current Round**",
            value=str(game["round"]),
            inline=True
        )
        
        embed.add_field(
            name="💀 **Eliminated**",
            value=str(len(game["eliminated"])),
            inline=True
        )
        
        # Show alive players if not too many
        if len(alive_players) <= 8:
            alive_names = [f"🏹 {p['name']} {p['title']}" for p in alive_players]
            embed.add_field(
                name="⚔️ **Survivors**",
                value="\n".join(alive_names) if alive_names else "None",
                inline=False
            )
        
        # Show kill leaders if applicable
        top_killers = sorted(alive_players, key=lambda x: x['kills'], reverse=True)[:3]
        if top_killers and top_killers[0]['kills'] > 0:
            killer_text = []
            for i, player in enumerate(top_killers):
                if player['kills'] > 0:
                    emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "🏹"
                    killer_text.append(f"{emoji} {player['name']} ({player['kills']} kills)")
            
            if killer_text:
                embed.add_field(
                    name="🏆 **Top Eliminators**",
                    value="\n".join(killer_text),
                    inline=False
                )
        
        embed.set_footer(text="🎮 Game in progress...")
        return embed
    
    async def execute_combined_events(self, game: Dict, channel: discord.TextChannel, event_count: int = None):
        """Execute multiple events in one round for variety"""
        alive_count = len(self.get_alive_players(game))
        
        # Determine number of events if not specified
        if event_count is None:
            if alive_count <= 3:
                event_count = random.randint(1, 2)
            elif alive_count <= 6:
                event_count = random.randint(2, 3)
            elif alive_count <= 12:
                event_count = random.randint(2, 4)
            else:
                event_count = random.randint(3, 5)
        
        # Execute events
        event_messages = []
        
        from .constants import get_event_weights
        base_weights = get_event_weights()
        
        for i in range(event_count):
            if len(self.get_alive_players(game)) <= 1:
                break
            
            # Adjust weights based on game state
            weights = base_weights.copy()
            if alive_count <= 2:
                weights.update({"death": 70, "survival": 10, "sponsor": 10, "alliance": 5, "crate": 5})
            elif alive_count <= 5:
                weights.update({"death": 45, "survival": 20, "sponsor": 15, "alliance": 10, "crate": 10})
            
            # Choose event type
            event_types = list(weights.keys())
            event_weights = list(weights.values())
            event_type = random.choices(event_types, weights=event_weights)[0]
            
            # Execute event
            message = None
            if event_type == "death":
                message = await self.execute_death_event(game, channel)
            elif event_type == "survival":
                message = await self.execute_survival_event(game)
            elif event_type == "sponsor":
                message = await self.execute_sponsor_event(game)
            elif event_type == "alliance":
                message = await self.execute_alliance_event(game)
            elif event_type == "crate":
                message = await self.execute_crate_event(game)
            
            if message:
                event_messages.append(message)
            
            await asyncio.sleep(0.1)  # Small delay between events
        
        return event_messages
