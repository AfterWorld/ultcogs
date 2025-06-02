# game_logic.py - Updated with Arena Conditions
"""
Core game logic and mechanics for Hunger Games cog with Grand Line conditions
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
from .arena_conditions import arena_condition_manager, CONDITION_DEATH_EVENTS

logger = logging.getLogger(__name__)


class GameError(Exception):
    """Base exception for game-related errors"""
    pass


class InvalidGameStateError(GameError):
    """Raised when game state is invalid"""
    pass


class GameEngine:
    """Core game engine for Hunger Games logic with Grand Line conditions"""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.condition_manager = arena_condition_manager
    
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
                    description="The Grand Line claimed all pirates... The World Government is pleased.",
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
            title="👑 **PIRATE KING OF THE GRAND LINE** 👑",
            description=f"**{winner['name']} {winner['title']}** has conquered the Grand Line!",
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
        
        # Add condition info if active
        condition_info = self.condition_manager.get_current_condition_info()
        if condition_info:
            embed.add_field(
                name="🌊 **Final Condition**",
                value=condition_info.get("name", "Unknown"),
                inline=True
            )
        
        embed.set_footer(text="🏴‍☠️ A new Pirate King has been crowned!")
        
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
    
    async def select_arena_condition(self, game: Dict, channel: discord.TextChannel) -> bool:
        """Select and announce new arena condition"""
        try:
            # Select condition based on game state
            alive_count = len(self.get_alive_players(game))
            condition = self.condition_manager.select_condition(game["round"], alive_count)
            
            # Get announcement
            announcement = self.condition_manager.get_condition_announcement(condition)
            
            # Send condition announcement
            embed = discord.Embed(
                title="🌊 **GRAND LINE WEATHER CHANGE** 🌊",
                description=announcement,
                color=0x4169E1
            )
            
            condition_info = self.condition_manager.get_current_condition_info()
            if condition_info:
                embed.add_field(
                    name="📍 **Current Condition**",
                    value=f"**{condition_info['name']}**\n{condition_info['description']}",
                    inline=False
                )
            
            await channel.send(embed=embed)
            logger.info(f"Arena condition changed to: {condition}")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting arena condition: {e}")
            return False
    
    async def execute_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute a death event with condition awareness - FIXED"""
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
        killer = None
        killer_name = None
        
        if random.random() < 0.6 and len(alive_players) > len(victims):
            # Player vs player
            potential_killers = [p for p in alive_players if p not in victims]
            if potential_killers:  # Make sure we have potential killers
                killer = random.choice(potential_killers)
                killer_name = f"{killer['name']} {killer['title']}"
                killer['kills'] += len(victims)
        
        # Execute the deaths
        for victim in victims:
            victim['alive'] = False
            game['eliminated'].append(victim['name'])
        
        # Choose death event based on whether we have a killer
        condition_events = self.condition_manager.get_condition_death_events()
        
        if killer_name and condition_events and random.random() < 0.4:
            # Use condition-specific death event (these always have killers)
            death_event = random.choice(condition_events)
        elif killer_name:
            # Use player vs player death event
            from .constants import PLAYER_DEATH_EVENTS
            death_event = random.choice(PLAYER_DEATH_EVENTS)
        else:
            # Use environmental death event (no killer)
            from .constants import ENVIRONMENTAL_DEATH_EVENTS
            death_event = random.choice(ENVIRONMENTAL_DEATH_EVENTS)
        
        # Format victim names
        if len(victims) == 1:
            victim_names = f"{victims[0]['name']} {victims[0]['title']}"
        else:
            victim_list = [f"{v['name']} {v['title']}" for v in victims]
            if len(victims) == 2:
                victim_names = f"{victim_list[0]} and {victim_list[1]}"
            else:
                victim_names = f"{', '.join(victim_list[:-1])}, and {victim_list[-1]}"
        
        # Format the event message
        try:
            if killer_name:
                message = death_event.format(player=victim_names, killer=killer_name)
            else:
                message = death_event.format(player=victim_names)
        except KeyError as e:
            # Fallback if formatting fails
            logger.error(f"Death event formatting error: {e}, event: {death_event}")
            if killer_name:
                message = f"💀 | **{killer_name}** eliminated ~~**{victim_names}**~~ in brutal combat!"
            else:
                message = f"💀 | ~~**{victim_names}**~~ met their end in the Grand Line!"
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
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
        """Execute a survival event with condition awareness"""
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
        
        message = survival_event.format(player=player_names)
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
        return message
    
    async def execute_sponsor_event(self, game: Dict) -> Optional[str]:
        """Execute a sponsor revival event with condition awareness"""
        dead_players = self.get_dead_players(game)
        
        if not dead_players:
            return None
        
        # Check sponsor chance (modified by conditions)
        base_sponsor_chance = await self.config.guild_from_id(game["channel"].guild.id).sponsor_chance()
        
        # Apply condition modifiers
        condition_effects = self.condition_manager.condition_effects
        modifier = condition_effects.get("sponsor_chance_modifier", 0) if condition_effects else 0
        final_chance = int(base_sponsor_chance * (1 + modifier))
        
        if random.randint(1, 100) > final_chance:
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
        message = sponsor_event.format(player=f"{revived_player['name']} {revived_player['title']}")
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
        return message
    
    async def execute_alliance_event(self, game: Dict) -> Optional[str]:
        """Execute an alliance event with proper formatting"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) < 2:
            return None
        
        # Choose 2 players for alliance
        players = random.sample(alive_players, 2)
        
        alliance_event = random.choice(ALLIANCE_EVENTS)
        
        # Format with player1 and player2
        message = alliance_event.format(
            player1=f"{players[0]['name']} {players[0]['title']}",
            player2=f"{players[1]['name']} {players[1]['title']}"
        )
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
        return message
    
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
        
        message = crate_event.format(player=player_names)
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
        return message
    
    async def check_special_events(self, game: Dict, channel: discord.TextChannel, alive_players: List[Dict]) -> Optional[str]:
        """Check for and generate special arena events"""
        alive_count = len(alive_players)
        round_num = game["round"]
        
        # Check for environmental events from current condition
        environmental_event = self.condition_manager.get_environmental_event()
        if environmental_event:
            return environmental_event
        
        # Final duel event
        if alive_count == 2 and "final_duel" not in game.get("milestones_shown", set()):
            game.setdefault("milestones_shown", set()).add("final_duel")
            return await self._generate_final_duel_event(alive_players)
        
        # Endgame events
        if alive_count <= 3 and "finale_announcement" not in game.get("milestones_shown", set()):
            game.setdefault("milestones_shown", set()).add("finale_announcement")
            return "📢 **ATTENTION PIRATES!** Only a few remain... The final battle approaches! The Grand Line grows more dangerous by the minute!"
        
        # Midgame events
        if alive_count <= 8 and alive_count > 3 and round_num % 3 == 0:
            return await self._generate_midgame_event(game)
        
        # Early game bloodbath
        if round_num == 1 and alive_count >= 6:
            return "⚔️ **THE PIRATE BATTLE BEGINS!** Pirates scramble for weapons and Devil Fruits as the chaos erupts!"
        
        return None
    
    async def check_condition_change(self, game: Dict, channel: discord.TextChannel) -> bool:
        """Check if arena condition should change"""
        try:
            # Update condition duration
            should_change = self.condition_manager.update_condition_duration()
            
            # Also chance to change on certain rounds
            if game["round"] % 8 == 0 and random.random() < 0.3:  # 30% chance every 8 rounds
                should_change = True
            
            if should_change:
                await self.select_arena_condition(game, channel)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking condition change: {e}")
            return False
    
    async def _generate_final_duel_event(self, alive_players: List[Dict]) -> str:
        """Generate final duel announcement"""
        player1 = alive_players[0]
        player2 = alive_players[1]
        
        scenarios = [
            f"🔥 **FINAL SHOWDOWN!** {player1['name']} {player1['title']} and {player2['name']} {player2['title']} face off in the ultimate battle for the One Piece!",
            f"⚡ **THE LAST STAND!** Only {player1['name']} {player1['title']} and {player2['name']} {player2['title']} remain... Who will become the Pirate King?",
            f"🏆 **PIRATE KING'S DUEL!** {player1['name']} {player1['title']} versus {player2['name']} {player2['title']} - the Grand Line holds its breath!",
            f"💀 **FINAL CONFRONTATION!** The last two pirates, {player1['name']} {player1['title']} and {player2['name']} {player2['title']}, prepare for their destiny!"
        ]
        
        return random.choice(scenarios)
    
    async def _generate_midgame_event(self, game: Dict) -> Optional[str]:
        """Generate midgame arena events"""
        alive_count = len(self.get_alive_players(game))
        
        events = [
            "🌪️ **GRAND LINE CHAOS:** A massive whirlpool tears through the battlefield, forcing pirates to seek higher ground!",
            "🔥 **DEVIL FRUIT AWAKENING:** Massive power surges as someone's ability goes out of control!",
            "❄️ **ICE AGE:** Freezing winds and ice engulf the ocean, trapping ships in frozen seas!",
            "🌋 **VOLCANIC ERUPTION:** Lava begins flowing from underwater volcanoes!",
            "💨 **STORM KING:** A deadly hurricane with lightning begins devastating the area!",
            "🐙 **SEA KING ATTACK:** Massive sea creatures emerge from the depths to hunt!",
            "📦 **DEVIL FRUIT CACHE:** Fresh Devil Fruits appear at dangerous locations - but who will dare claim them?",
            "🦅 **MARINE INTERVENTION:** The World Government sends their deadliest agents into the fray!",
            "⚡ **CONQUEROR'S HAKI:** Overwhelming willpower clashes shake the very foundations of reality!",
            "🌊 **TSUNAMI WARNING:** Massive tidal waves force pirates to the highest points available!"
        ]
        
        # Filter events based on game state
        if alive_count <= 5:
            # More intense events for fewer players
            intense_events = [
                "🔥 **FINAL TEMPEST:** The Grand Line begins collapsing, forcing the remaining pirates together!",
                "💀 **YONKO'S WRATH:** The power of an Emperor-level pirate rocks the entire area!",
                "⚡ **WORLD'S END:** Ancient Weapons activate their deadliest features!",
                "🌪️ **RAGNAROK:** Multiple disasters strike simultaneously as the world itself seems to end!"
            ]
            events.extend(intense_events)
        
        message = random.choice(events)
        
        # Apply condition flavor
        message = self.condition_manager.apply_flavor_to_message(message)
        
        return message
    
    def create_status_embed(self, game: Dict, guild: discord.Guild) -> discord.Embed:
        """Create a status embed for the current game"""
        alive_players = self.get_alive_players(game)
        total_players = len(game["players"])
        
        embed = discord.Embed(
            title="📊 **GRAND LINE STATUS UPDATE**",
            color=0x4169E1
        )
        
        # Basic stats
        embed.add_field(
            name="🏴‍☠️ **Pirates Remaining**",
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
        
        # Show current arena condition
        condition_info = self.condition_manager.get_current_condition_info()
        if condition_info:
            embed.add_field(
                name="🌊 **Arena Condition**",
                value=f"{condition_info['name']}\n*{condition_info['duration']} rounds remaining*",
                inline=False
            )
        
        # Show alive players if not too many
        if len(alive_players) <= 8:
            alive_names = [f"🏴‍☠️ {p['name']} {p['title']}" for p in alive_players]
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
                    emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else "🏴‍☠️"
                    killer_text.append(f"{emoji} {player['name']} ({player['kills']} eliminations)")
            
            if killer_text:
                embed.add_field(
                    name="🏆 **Most Dangerous Pirates**",
                    value="\n".join(killer_text),
                    inline=False
                )
        
        embed.set_footer(text="🌊 Battle rages across the Grand Line...")
        return embed
    
    async def execute_combined_events(self, game: Dict, channel: discord.TextChannel, event_count: int = None):
        """Execute multiple events in one round with condition awareness and special events"""
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
        
        # Apply condition effects to weights (but don't let them dominate)
        weights = self.condition_manager.apply_condition_to_event_weights(base_weights)
        
        # Ensure minimum chances for non-death events so conditions don't prevent them
        weights["survival"] = max(weights["survival"], 15)
        weights["sponsor"] = max(weights["sponsor"], 10)
        weights["alliance"] = max(weights["alliance"], 10)
        weights["crate"] = max(weights["crate"], 10)
        
        # Check for special midgame events first (these are additional to normal events)
        special_event = await self._check_special_midgame_events(game, channel, alive_count)
        if special_event:
            event_messages.append(special_event)
        
        for i in range(event_count):
            if len(self.get_alive_players(game)) <= 1:
                break
            
            # Adjust weights based on game state
            current_alive = len(self.get_alive_players(game))
            if current_alive <= 2:
                weights.update({"death": 70, "survival": 10, "sponsor": 10, "alliance": 5, "crate": 5})
            elif current_alive <= 5:
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
    
    async def _check_special_midgame_events(self, game: Dict, channel: discord.TextChannel, alive_count: int) -> Optional[str]:
        """Check for and execute special midgame events"""
        try:
            round_num = game["round"]
            
            # Only trigger special events in midgame (not too early, not too late)
            if round_num < 3 or alive_count <= 3:
                return None
            
            # 15% chance for special events in midgame
            if random.random() > 0.15:
                return None
            
            # Choose random special event type
            from .constants import MIDGAME_DEADLY_EVENT_TYPES
            event_type = random.choice(MIDGAME_DEADLY_EVENT_TYPES)
            
            if event_type == "cannon_malfunction":
                return await self._execute_cannon_event(game)
            elif event_type == "toxic_fog":
                return await self._execute_toxic_fog_event(game)
            elif event_type == "tracker_jackers":
                return await self._execute_sea_king_event(game)
            elif event_type == "arena_trap":
                return await self._execute_arena_trap_event(game)
            elif event_type == "muttation_attack":
                return await self._execute_muttation_event(game)
            elif event_type == "environmental_hazard":
                return await self._execute_environmental_hazard_event(game)
            elif event_type == "gamemaker_test":
                return await self._execute_gamemaker_event(game)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in special midgame events: {e}")
            return None
    
    async def _execute_cannon_event(self, game: Dict) -> Optional[str]:
        """Execute cannon malfunction event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import CANNON_DEATH_EVENTS, CANNON_SCARE_EVENTS
            
            if random.random() < 0.3:  # 30% chance for death
                victim = random.choice(alive_players)
                victim['alive'] = False
                game['eliminated'].append(victim['name'])
                
                death_event = random.choice(CANNON_DEATH_EVENTS)
                return death_event.format(player=f"{victim['name']} {victim['title']}")
            else:
                return random.choice(CANNON_SCARE_EVENTS)
                
        except Exception as e:
            logger.error(f"Error in cannon event: {e}")
            return None
    
    async def _execute_toxic_fog_event(self, game: Dict) -> Optional[str]:
        """Execute toxic fog event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import TOXIC_FOG_SINGLE_DEATH, TOXIC_FOG_MULTI_DEATH, TOXIC_FOG_SURVIVAL
            
            if random.random() < 0.4:  # 40% chance for deaths
                if len(alive_players) >= 4 and random.random() < 0.3:
                    # Multi-death
                    num_victims = min(random.randint(2, 3), len(alive_players) - 1)
                    victims = random.sample(alive_players, num_victims)
                    
                    for victim in victims:
                        victim['alive'] = False
                        game['eliminated'].append(victim['name'])
                    
                    victim_names = ", ".join([f"~~**{v['name']} {v['title']}**~~" for v in victims])
                    return TOXIC_FOG_MULTI_DEATH.format(players=victim_names)
                else:
                    # Single death
                    victim = random.choice(alive_players)
                    victim['alive'] = False
                    game['eliminated'].append(victim['name'])
                    
                    death_event = random.choice(TOXIC_FOG_SINGLE_DEATH)
                    return death_event.format(player=f"{victim['name']} {victim['title']}")
            else:
                return TOXIC_FOG_SURVIVAL
                
        except Exception as e:
            logger.error(f"Error in toxic fog event: {e}")
            return None
    
    async def _execute_sea_king_event(self, game: Dict) -> Optional[str]:
        """Execute Sea King attack event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import TRACKER_JACKER_DEATHS, TRACKER_JACKER_HALLUCINATION, TRACKER_JACKER_AVOIDANCE
            
            if random.random() < 0.35:  # 35% chance for death
                victim = random.choice(alive_players)
                victim['alive'] = False
                game['eliminated'].append(victim['name'])
                
                death_event = random.choice(TRACKER_JACKER_DEATHS)
                return death_event.format(player=f"{victim['name']} {victim['title']}")
            elif random.random() < 0.6:
                # Hallucination event
                survivor = random.choice(alive_players)
                return TRACKER_JACKER_HALLUCINATION.format(player=f"{survivor['name']} {survivor['title']}")
            else:
                return TRACKER_JACKER_AVOIDANCE
                
        except Exception as e:
            logger.error(f"Error in sea king event: {e}")
            return None
    
    async def _execute_arena_trap_event(self, game: Dict) -> Optional[str]:
        """Execute arena trap event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import ARENA_TRAP_TYPES, ARENA_TRAP_DEATH, ARENA_TRAP_ESCAPE
            
            trap_name, emoji, description = random.choice(ARENA_TRAP_TYPES)
            player = random.choice(alive_players)
            
            if random.random() < 0.4:  # 40% chance for death
                player['alive'] = False
                game['eliminated'].append(player['name'])
                
                return ARENA_TRAP_DEATH.format(
                    emoji=emoji,
                    player=f"{player['name']} {player['title']}",
                    description=description
                )
            else:
                return ARENA_TRAP_ESCAPE.format(
                    emoji=emoji,
                    player=f"{player['name']} {player['title']}",
                    trap_name=trap_name
                )
                
        except Exception as e:
            logger.error(f"Error in arena trap event: {e}")
            return None
    
    async def _execute_muttation_event(self, game: Dict) -> Optional[str]:
        """Execute muttation/creature attack event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import MUTTATION_TYPES, MUTTATION_DEATH, MUTTATION_ESCAPE
            
            creature_name, emoji, death_verb = random.choice(MUTTATION_TYPES)
            
            if random.random() < 0.3:  # 30% chance for death
                victim = random.choice(alive_players)
                victim['alive'] = False
                game['eliminated'].append(victim['name'])
                
                return MUTTATION_DEATH.format(
                    emoji=emoji,
                    player=f"{victim['name']} {victim['title']}",
                    death_verb=death_verb,
                    creature_name=creature_name
                )
            else:
                return MUTTATION_ESCAPE.format(
                    emoji=emoji,
                    creature_name=creature_name
                )
                
        except Exception as e:
            logger.error(f"Error in muttation event: {e}")
            return None
    
    async def _execute_environmental_hazard_event(self, game: Dict) -> Optional[str]:
        """Execute environmental hazard event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import ENVIRONMENTAL_HAZARDS, ENVIRONMENTAL_SINGLE_DEATH, ENVIRONMENTAL_SURVIVAL
            
            hazard_name, emoji, death_description = random.choice(ENVIRONMENTAL_HAZARDS)
            
            if random.random() < 0.35:  # 35% chance for death
                victim = random.choice(alive_players)
                victim['alive'] = False
                game['eliminated'].append(victim['name'])
                
                return ENVIRONMENTAL_SINGLE_DEATH.format(
                    emoji=emoji,
                    player=f"{victim['name']} {victim['title']}",
                    death_description=death_description,
                    hazard_name=hazard_name
                )
            else:
                return ENVIRONMENTAL_SURVIVAL.format(
                    emoji=emoji,
                    hazard_name=hazard_name
                )
                
        except Exception as e:
            logger.error(f"Error in environmental hazard event: {e}")
            return None
    
    async def _execute_gamemaker_event(self, game: Dict) -> Optional[str]:
        """Execute World Government test event"""
        try:
            alive_players = self.get_alive_players(game)
            if not alive_players:
                return None
            
            from .constants import (GAMEMAKER_COURAGE_DEATH, GAMEMAKER_COURAGE_SURVIVAL, 
                                   GAMEMAKER_TEST_ANNOUNCEMENT, GAMEMAKER_LOYALTY_TEST)
            
            event_type = random.choice(["courage", "announcement", "loyalty"])
            
            if event_type == "courage":
                player = random.choice(alive_players)
                if random.random() < 0.2:  # 20% chance for death
                    player['alive'] = False
                    game['eliminated'].append(player['name'])
                    return GAMEMAKER_COURAGE_DEATH.format(player=f"{player['name']} {player['title']}")
                else:
                    return GAMEMAKER_COURAGE_SURVIVAL.format(player=f"{player['name']} {player['title']}")
            elif event_type == "announcement":
                return GAMEMAKER_TEST_ANNOUNCEMENT
            else:
                return GAMEMAKER_LOYALTY_TEST
                
        except Exception as e:
            logger.error(f"Error in gamemaker event: {e}")
            return None
