# game.py
"""Core game logic for Hunger Games"""

import discord
import asyncio
import random
from typing import Dict, List, Optional, Tuple
from redbot.core import bank
from .constants import *


class GameEngine:
    """Handles all game logic and events"""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
    
    def calculate_prize_pool(self, player_count: int, base_reward: int) -> int:
        """Calculate prize based on number of players"""
        if player_count < 5:
            return base_reward
        elif player_count < 10:
            return int(base_reward * 1.5)
        elif player_count < 20:
            return int(base_reward * 2)
        elif player_count < 30:
            return int(base_reward * 2.5)
        else:
            return int(base_reward * 3)
    
    def get_alive_players(self, game: Dict) -> List[str]:
        """Get list of alive player IDs"""
        return [pid for pid, pdata in game["players"].items() if pdata["alive"]]
    
    def get_dead_players(self, game: Dict) -> List[str]:
        """Get list of dead player IDs"""
        return [pid for pid, pdata in game["players"].items() if not pdata["alive"]]
    
    def kill_player(self, game: Dict, player_id: str, killer_id: Optional[str] = None) -> Dict:
        """Kill a player and update stats"""
        if player_id not in game["players"] or not game["players"][player_id]["alive"]:
            return None
            
        game["players"][player_id]["alive"] = False
        game["eliminated"].append({
            "id": player_id,
            "name": game["players"][player_id]["name"],
            "round": game["round"],
            "killer": killer_id
        })
        
        # Update kill count for killer
        if killer_id and killer_id in game["players"]:
            game["players"][killer_id]["kills"] += 1
            
        return game["players"][player_id]
    
    def revive_player(self, game: Dict, player_id: str) -> bool:
        """Attempt to revive a dead player via sponsor"""
        if player_id not in game["players"] or game["players"][player_id]["alive"]:
            return False
            
        if player_id in game["sponsor_used"]:
            return False  # Can only be revived once
            
        game["players"][player_id]["alive"] = True
        game["sponsor_used"].append(player_id)
        
        # Track revive count
        if "revives" not in game["players"][player_id]:
            game["players"][player_id]["revives"] = 0
        game["players"][player_id]["revives"] += 1
        
        # Remove from eliminated list
        game["eliminated"] = [e for e in game["eliminated"] if e["id"] != player_id]
        
        return True
    
    async def execute_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute a death event"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) <= 1:
            return None
            
        # Choose victim
        victim_id = random.choice(alive_players)
        victim_data = game["players"][victim_id]
        victim_name_with_title = f"{victim_data['name']} {victim_data['title']}"
        
        # 60% chance for murder, 40% chance for accident
        if random.random() < 0.6 and len(alive_players) > 2:
            # Murder - choose a killer
            potential_killers = [p for p in alive_players if p != victim_id]
            killer_id = random.choice(potential_killers)
            killer_data = game["players"][killer_id]
            killer_name_with_title = f"{killer_data['name']} {killer_data['title']}"
            
            # Choose murder event
            murder_events = [e for e in DEATH_EVENTS if "{killer}" in e]
            event = random.choice(murder_events)
            message = event.format(player=victim_name_with_title, killer=killer_name_with_title)
            
            self.kill_player(game, victim_id, killer_id)
        else:
            # Accident
            accident_events = [e for e in DEATH_EVENTS if "{killer}" not in e]
            event = random.choice(accident_events)
            message = event.format(player=victim_name_with_title)
            
            self.kill_player(game, victim_id)
        
        # Check for sponsor revival
        sponsor_chance = await self.config.guild(channel.guild).sponsor_chance()
        if random.randint(1, 100) <= sponsor_chance:
            # Try to revive a recently dead player
            dead_players = self.get_dead_players(game)
            eligible_for_revival = [p for p in dead_players if p not in game["sponsor_used"]]
            
            if eligible_for_revival:
                revive_id = random.choice(eligible_for_revival)
                if self.revive_player(game, revive_id):
                    revive_data = game["players"][revive_id]
                    revive_name_with_title = f"{revive_data['name']} {revive_data['title']}"
                    revival_msg = random.choice(REVIVAL_MESSAGES).format(player=revive_name_with_title)
                    message += f"\n\n{revival_msg}"
        
        return message
    
    async def execute_survival_event(self, game: Dict) -> Optional[str]:
        """Execute a survival event"""
        alive_players = self.get_alive_players(game)
        
        if not alive_players:
            return None
            
        player_id = random.choice(alive_players)
        player_data = game["players"][player_id]
        player_name_with_title = f"{player_data['name']} {player_data['title']}"
        
        event = random.choice(SURVIVAL_EVENTS)
        return event.format(player=player_name_with_title)
    
    async def execute_sponsor_event(self, game: Dict) -> Optional[str]:
        """Execute a sponsor gift event"""
        alive_players = self.get_alive_players(game)
        
        if not alive_players:
            return None
            
        player_id = random.choice(alive_players)
        player_data = game["players"][player_id]
        player_name_with_title = f"{player_data['name']} {player_data['title']}"
        
        event = random.choice(SPONSOR_EVENTS)
        return event.format(player=player_name_with_title)
    
    async def execute_alliance_event(self, game: Dict) -> Optional[str]:
        """Execute an alliance event"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) < 2:
            return None
            
        player1_id, player2_id = random.sample(alive_players, 2)
        player1_data = game["players"][player1_id]
        player2_data = game["players"][player2_id]
        player1_name_with_title = f"{player1_data['name']} {player1_data['title']}"
        player2_name_with_title = f"{player2_data['name']} {player2_data['title']}"
        
        event = random.choice(ALLIANCE_EVENTS)
        return event.format(player1=player1_name_with_title, player2=player2_name_with_title)
    
    def create_status_embed(self, game: Dict, guild: discord.Guild) -> discord.Embed:
        """Create status embed showing current game state"""
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
        embed.description = GAME_PHASES[phase_index]
        
        # Players remaining
        embed.add_field(
            name="👥 **Tributes Remaining**",
            value=f"**{alive_count}** survivors",
            inline=True
        )
        
        # Current era/phase
        if alive_count <= 5:
            embed.add_field(
                name="⚔️ **Status**",
                value="**FINAL SHOWDOWN**",
                inline=True
            )
        elif alive_count <= 10:
            embed.add_field(
                name="🔥 **Status**",
                value="**BLOODBATH PHASE**",
                inline=True
            )
        else:
            embed.add_field(
                name="🌿 **Status**",
                value="**SURVIVAL PHASE**",
                inline=True
            )
        
        # Show top killers if any
        killers = [(pid, pdata) for pid, pdata in game["players"].items() 
                  if pdata["kills"] > 0 and pdata["alive"]]
        
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
        
        return embed
    
    async def check_game_end(self, game: Dict, channel: discord.TextChannel) -> bool:
        """Check if game should end and handle victory"""
        alive_players = self.get_alive_players(game)
        
        if len(alive_players) <= 1:
            await self.handle_victory(game, channel)
            return True
        elif len(alive_players) <= 3:
            # Final warning
            count = len(alive_players)
            message = random.choice(FINALE_MESSAGES).format(count=count)
            
            embed = discord.Embed(
                title="⚔️ **FINAL MOMENTS** ⚔️",
                description=message,
                color=0xFF0000
            )
            
            await channel.send(embed=embed)
            
        return False
    
    async def handle_victory(self, game: Dict, channel: discord.TextChannel):
        """Handle end of game and victory with comprehensive results"""
        alive_players = self.get_alive_players(game)
        
        if alive_players:
            winner_id = alive_players[0]
            winner = game["players"][winner_id]
            
            # Calculate prize
            base_reward = await self.config.guild(channel.guild).base_reward()
            total_players = len(game["players"])
            prize = self.calculate_prize_pool(total_players, base_reward)
            
            # Award prize
            try:
                winner_member = channel.guild.get_member(int(winner_id))
                if winner_member:
                    await bank.deposit_credits(winner_member, prize)
            except:
                pass  # User might not be in guild anymore
            
            # Update stats for winner
            async with self.config.member_from_ids(channel.guild.id, int(winner_id)).all() as member_data:
                member_data["wins"] += 1
                member_data["kills"] += winner["kills"]
            
            # Update death stats for all eliminated players
            for eliminated in game["eliminated"]:
                try:
                    async with self.config.member_from_ids(channel.guild.id, int(eliminated["id"])).all() as member_data:
                        member_data["deaths"] += 1
                except:
                    pass
            
            # Update revive stats for all players who were revived
            for player_id, player_data in game["players"].items():
                if player_data.get("revives", 0) > 0:
                    try:
                        async with self.config.member_from_ids(channel.guild.id, int(player_id)).all() as member_data:
                            member_data["revives"] += player_data["revives"]
                    except:
                        pass
            
            # Create comprehensive victory display
            await self.send_victory_display(game, channel, winner_id, winner, prize, total_players)
        else:
            # No survivors (shouldn't happen, but just in case)
            embed = discord.Embed(
                title="💀 **NO SURVIVORS** 💀",
                description="The arena has claimed all tributes...",
                color=0x000000
            )
            await channel.send(embed=embed)
    
    async def send_victory_display(self, game: Dict, channel: discord.TextChannel, 
                                 winner_id: str, winner: Dict, prize: int, total_players: int):
        """Send the comprehensive victory display"""
        
        # Main victory embed with winner
        embed = discord.Embed(color=0xFFD700)
        embed.set_author(name="🏆 WINNER!", icon_url="https://cdn.discordapp.com/emojis/1234567890.png")
        
        # Winner section with yellow sidebar styling
        winner_text = f"👑 **{winner['name']}** the Champion\n"
        winner_text += f"**Reward:** {prize:,} 💰"
        
        embed.add_field(
            name="",
            value=winner_text,
            inline=False
        )
        
        # Stylized game title
        title_art = random.choice(VICTORY_TITLE_ART)
        embed.add_field(
            name="",
            value=title_art,
            inline=False
        )
        
        # Total players with emphasis
        embed.add_field(
            name="",
            value=f"**Total Players:** {total_players}",
            inline=False
        )
        
        # Add a colored strip effect
        embed.set_thumbnail(url="https://i.imgur.com/winner_badge.png")  # Optional winner badge
        
        await channel.send(embed=embed)
        
        # Second embed with detailed rankings
        stats_embed = discord.Embed(color=0x36393F)  # Dark theme like the screenshot
        
        # Calculate rankings
        runner_ups = self.calculate_runner_ups(game)
        kill_leaders = self.calculate_kill_leaders(game)
        revive_leaders = self.calculate_revive_leaders(game)
        
        # Add fields side by side
        fields_added = 0
        
        # Runners-up section
        if runner_ups:
            runner_text = ""
            for i, (player_id, player_data) in enumerate(runner_ups, 2):
                medal = PLACEMENT_MEDALS.get(i, f"{i}.")
                runner_text += f"{medal} {player_data['name']}\n"
            
            stats_embed.add_field(
                name="🥈 **Runners-up**",
                value=runner_text if runner_text else "None",
                inline=True
            )
            fields_added += 1
        
        # Most kills section  
        if kill_leaders:
            kills_text = ""
            for player_id, player_data in kill_leaders:
                kills_text += f"**{player_data['kills']}** {player_data['name']}\n"
            
            stats_embed.add_field(
                name="⚔️ **Most Kills**",
                value=kills_text if kills_text else "None",
                inline=True
            )
            fields_added += 1
        
        # Most revives section
        if revive_leaders:
            revives_text = ""
            for player_id, player_data in revive_leaders:
                revive_count = player_data.get('revives', 0)
                revives_text += f"**{revive_count}** {player_data['name']}\n"
            
            stats_embed.add_field(
                name="✨ **Most Revives**",
                value=revives_text if revives_text else "None", 
                inline=True
            )
            fields_added += 1
        
        # Add empty field if we need to balance the layout
        if fields_added % 3 != 0:
            for _ in range(3 - (fields_added % 3)):
                stats_embed.add_field(name="\u200b", value="\u200b", inline=True)
        
        # Game info footer
        era = random.choice(GAME_ERAS)
        stats_embed.set_footer(
            text=f"🎮 Era: {era} • Battle Royale",
            icon_url="https://i.imgur.com/game_icon.png"
        )
        
        await channel.send(embed=stats_embed)
    
    def calculate_runner_ups(self, game: Dict) -> List[tuple]:
        """Calculate top 5 runner-ups based on elimination order"""
        # Sort eliminated players by round (later rounds = better placement)
        eliminated_sorted = sorted(game["eliminated"], key=lambda x: x["round"], reverse=True)
        
        runner_ups = []
        for eliminated in eliminated_sorted[:4]:  # Top 4 runner-ups (positions 2-5)
            player_id = eliminated["id"]
            if player_id in game["players"]:
                runner_ups.append((player_id, game["players"][player_id]))
        
        return runner_ups
    
    def calculate_kill_leaders(self, game: Dict) -> List[tuple]:
        """Calculate players with most kills"""
        kill_leaders = []
        
        for player_id, player_data in game["players"].items():
            if player_data["kills"] > 0:
                kill_leaders.append((player_id, player_data))
        
        # Sort by kills (descending)
        kill_leaders.sort(key=lambda x: x[1]["kills"], reverse=True)
        
        return kill_leaders[:5]  # Top 5 killers
    
    def calculate_revive_leaders(self, game: Dict) -> List[tuple]:
        """Calculate players with most revives"""
        revive_leaders = []
        
        for player_id, player_data in game["players"].items():
            revive_count = player_data.get("revives", 0)
            if revive_count > 0:
                revive_leaders.append((player_id, player_data))
        
        # Sort by revives (descending)
        revive_leaders.sort(key=lambda x: x[1].get("revives", 0), reverse=True)
        
        return revive_leaders[:5]  # Top 5 most revived
