# __init__.py
"""
Hunger Games Battle Royale Cog for Red-DiscordBot

A comprehensive battle royale game where players fight to be the last survivor.
Features automatic events, sponsor revivals, dynamic rewards, and detailed statistics.
"""

import discord
from redbot.core import commands, Config, bank
import asyncio
import random
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_GUILD_CONFIG, DEFAULT_MEMBER_CONFIG, EMOJIS,
    DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS
)
from .game import GameEngine
from .utils import *


class HungerGames(commands.Cog):
    """A Hunger Games style battle royale game for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)
        self.config.register_member(**DEFAULT_MEMBER_CONFIG)
        
        self.active_games: Dict[int, Dict] = {}
        self.game_engine = GameEngine(bot, self.config)
        
    def cog_unload(self):
        """Cancel all running games when cog is unloaded"""
        for guild_id in list(self.active_games.keys()):
            if "task" in self.active_games[guild_id]:
                self.active_games[guild_id]["task"].cancel()
    
    @commands.command(name="he")
    async def hunger_games_event(self, ctx, countdown: int = 60):
        """Start a Hunger Games battle royale! React to join!"""
        guild_id = ctx.guild.id
        
        # Validate countdown
        valid, error_msg = validate_countdown(countdown)
        if not valid:
            return await ctx.send(f"❌ {error_msg}")
        
        if guild_id in self.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        # Create the game instance
        self.active_games[guild_id] = {
            "channel": ctx.channel,
            "players": {},
            "status": "recruiting",
            "round": 0,
            "eliminated": [],
            "sponsor_used": [],
            "reactions": set(),
            "milestones_shown": set()  # Track which milestone messages have been shown
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
        
        # Monitor reactions for the countdown period
        end_time = asyncio.get_event_loop().time() + countdown
        
        while asyncio.get_event_loop().time() < end_time:
            remaining = int(end_time - asyncio.get_event_loop().time())
            
            # Update embed every 10 seconds or at key intervals
            if remaining % 10 == 0 or remaining <= 5:
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
                        users = []
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
                    
                except discord.NotFound:
                    # Message was deleted, cancel game
                    del self.active_games[guild_id]
                    return
                except discord.Forbidden:
                    pass  # Can't edit, continue anyway
            
            await asyncio.sleep(1)
        
        # Recruitment ended, start the game
        await self.start_battle_royale(guild_id)
    
    async def start_battle_royale(self, guild_id: int):
        """Start the actual battle royale game"""
        game = self.active_games[guild_id]
        channel = game["channel"]
        
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
        
        # Send game start message
        embed = create_game_start_embed(player_count)
        await channel.send(embed=embed)
        
        # Show initial tributes
        await asyncio.sleep(3)
        
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
        
        # Start the main game loop
        game["task"] = asyncio.create_task(self.game_loop(guild_id))
    
    async def game_loop(self, guild_id: int):
        """Main game loop that handles events and progression - FASTER PACE"""
        game = self.active_games[guild_id]
        channel = game["channel"]
        
        try:
            event_interval = await self.config.guild(channel.guild).event_interval()
            
            # Give shorter pause before starting events
            await asyncio.sleep(3)
            
            # Debug message to confirm loop started
            print(f"Game loop started for guild {guild_id} with {len(game['players'])} players")
            
            while game["status"] == "active":
                game["round"] += 1
                alive_players = self.game_engine.get_alive_players(game)
                
                print(f"Round {game['round']}: {len(alive_players)} players alive")
                
                # Execute MULTIPLE events per round for faster pace
                if len(alive_players) > 1:
                    try:
                        await self.execute_combined_events(game, channel)
                    except Exception as e:
                        print(f"Error executing combined events: {e}")
                        # Send a fallback message so something happens
                        embed = discord.Embed(
                            description="⚠️ Something mysterious happened in the arena...",
                            color=0xFFFF00
                        )
                        await channel.send(embed=embed)
                
                # Shorter delay between event and end check
                await asyncio.sleep(1)
                
                # Re-check alive players after potential events
                alive_players = self.game_engine.get_alive_players(game)
                
                # Check if game should end AFTER events
                if await self.game_engine.check_game_end(game, channel):
                    break
                
                # Send status update less frequently to reduce spam
                if game["round"] % 6 == 0 and len(alive_players) > 8:
                    embed = self.game_engine.create_status_embed(game, channel.guild)
                    await channel.send(embed=embed)
                
                # MUCH faster event intervals
                if len(alive_players) <= 2:
                    sleep_time = max(4, event_interval // 6)   # Super fast final duel
                elif len(alive_players) <= 3:
                    sleep_time = max(5, event_interval // 5)   # Very fast with 2-3 players
                elif len(alive_players) <= 5:
                    sleep_time = max(7, event_interval // 4)   # Fast with 4-5 players
                elif len(alive_players) <= 10:
                    sleep_time = max(10, event_interval // 3)  # Faster mid-game
                else:
                    sleep_time = max(12, event_interval // 2)  # Faster early game
                
                print(f"Sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            print(f"Game {guild_id} was cancelled")
        except Exception as e:
            print(f"Error in game loop for guild {guild_id}: {e}")
            # Send error message to channel
            try:
                embed = discord.Embed(
                    title="❌ **ARENA MALFUNCTION**",
                    description="The arena experienced technical difficulties. Game ended.",
                    color=0xFF0000
                )
                await channel.send(embed=embed)
            except:
                pass
        finally:
            # Clean up
            print(f"Cleaning up game for guild {guild_id}")
            if guild_id in self.active_games:
                del self.active_games[guild_id]
    
    async def execute_random_event(self, game: Dict, channel: discord.TextChannel):
        """Execute a random game event"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        print(f"Executing random event with {alive_count} alive players")
        
        # Get event type weights
        weights = get_event_weights()
        
        # Adjust weights based on game state
        if alive_count <= 2:
            # Final duel - mostly death events with some drama
            weights["death"] = 70
            weights["survival"] = 10  
            weights["sponsor"] = 10
            weights["alliance"] = 5
            weights["crate"] = 5
        elif alive_count <= 3:
            # Final three - more action
            weights["death"] = 55
            weights["survival"] = 15
            weights["sponsor"] = 15
            weights["alliance"] = 5
            weights["crate"] = 10
        elif alive_count <= 5:
            # Top 5 - intense action
            weights["death"] = 45  
            weights["survival"] = 20
            weights["sponsor"] = 15
            weights["alliance"] = 10
            weights["crate"] = 10
        elif alive_count <= 10:
            # Standard late game
            weights["death"] = 35
            weights["survival"] = 25
            weights["sponsor"] = 15
            weights["alliance"] = 15
            weights["crate"] = 10
        
        # Choose event type
        event_types = list(weights.keys())
        event_weights = list(weights.values())
        event_type = random.choices(event_types, weights=event_weights)[0]
        
        print(f"Chosen event type: {event_type}")
        
        message = None
        
        try:
            if event_type == "death":
                message = await self.game_engine.execute_death_event(game, channel)
            elif event_type == "survival":
                message = await self.game_engine.execute_survival_event(game)
            elif event_type == "sponsor":
                message = await self.game_engine.execute_sponsor_event(game)
            elif event_type == "alliance":
                message = await self.game_engine.execute_alliance_event(game)
            elif event_type == "crate":
                message = await self.game_engine.execute_crate_event(game)
        except Exception as e:
            print(f"Error in event execution ({event_type}): {e}")
            # Fallback message if event fails
            message = f"⚠️ | Something unexpected happened in the arena during round {game['round']}!"
        
        print(f"Generated message: {message}")
        
        if message:
            try:
                # Create event embed with appropriate color
                if event_type == "death":
                    color = 0xFF4500  # Red-orange for death
                elif event_type == "crate":
                    color = 0x8B4513  # Brown for crates
                elif event_type == "sponsor":
                    color = 0xFFD700  # Gold for sponsors
                elif event_type == "alliance":
                    color = 0x4169E1  # Blue for alliances
                else:
                    color = 0x32CD32  # Green for survival
                
                embed = discord.Embed(
                    description=message,
                    color=color
                )
                
                # Add round number and phase
                alive_after_event = len(self.game_engine.get_alive_players(game))
                embed.set_footer(text=f"Round {game['round']} • {get_game_phase_description(game['round'], alive_after_event)}")
                
                await channel.send(embed=embed)
                print(f"Event message sent successfully")
            except Exception as e:
                print(f"Error sending event message: {e}")
                # Try sending a plain message as fallback
                try:
                    await channel.send(f"**Round {game['round']}**: {message}")
                except:
                    print("Failed to send even plain message")
        else:
            print("No message generated from event")
    
    async def execute_combined_events(self, game: Dict, channel: discord.TextChannel):
        """Execute multiple events in one round - RUMBLE COMPACT STYLE"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        print(f"Executing combined events with {alive_count} alive players")
        
        # Determine how many events to execute based on player count
        if alive_count <= 3:
            num_events = random.randint(1, 2)
        elif alive_count <= 6:
            num_events = random.randint(2, 3)
        elif alive_count <= 12:
            num_events = random.randint(2, 4)
        else:
            num_events = random.randint(3, 5)
        
        # Get event weights and execute events (same logic as before)
        weights = get_event_weights()
        
        # Adjust weights based on game state
        if alive_count <= 2:
            weights["death"] = 70
            weights["survival"] = 10  
            weights["sponsor"] = 10
            weights["alliance"] = 5
            weights["crate"] = 5
        elif alive_count <= 3:
            weights["death"] = 55
            weights["survival"] = 15
            weights["sponsor"] = 15
            weights["alliance"] = 5
            weights["crate"] = 10
        elif alive_count <= 5:
            weights["death"] = 45  
            weights["survival"] = 20
            weights["sponsor"] = 15
            weights["alliance"] = 10
            weights["crate"] = 10
        elif alive_count <= 10:
            weights["death"] = 35
            weights["survival"] = 25
            weights["sponsor"] = 15
            weights["alliance"] = 15
            weights["crate"] = 10
        
        # Execute multiple events
        event_messages = []
        
        for i in range(num_events):
            if len(self.game_engine.get_alive_players(game)) <= 1:
                break
            
            # Choose event type
            event_types = list(weights.keys())
            event_weights = list(weights.values())
            event_type = random.choices(event_types, weights=event_weights)[0]
            
            message = None
            try:
                if event_type == "death":
                    message = await self.game_engine.execute_death_event(game, channel)
                elif event_type == "survival":
                    message = await self.game_engine.execute_survival_event(game)
                elif event_type == "sponsor":
                    message = await self.game_engine.execute_sponsor_event(game)
                elif event_type == "alliance":
                    message = await self.game_engine.execute_alliance_event(game)
                elif event_type == "crate":
                    message = await self.game_engine.execute_crate_event(game)
                
                if message:
                    # Keep the original message format from your constants
                    event_messages.append(message)
                
            except Exception as e:
                print(f"Error in event {i+1} execution ({event_type}): {e}")
                continue
            
            await asyncio.sleep(0.5)
        
        # Create RUMBLE-STYLE message format
        if event_messages:
            try:
                alive_after_events = len(self.game_engine.get_alive_players(game))
                
                # Build the exact Rumble format
                rumble_message = f"**Round {game['round']}**\n"
                rumble_message += "\n".join(event_messages)
                rumble_message += f"\n\n**Players Left: {alive_after_events}**"
                
                # Send as a simple message (no embed for true Rumble style)
                await channel.send(rumble_message)
                print(f"Rumble-style events message sent with {len(event_messages)} events")
                
            except Exception as e:
                print(f"Error sending rumble-style message: {e}")
        else:
            print("No event messages generated")
    
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
        
        game = self.active_games[guild_id]
        alive_players = self.game_engine.get_alive_players(game)
        
        if not alive_players:
            return await ctx.send("💀 No survivors remain!")
        
        embed = discord.Embed(
            title="❤️ **ALIVE TRIBUTES** ❤️",
            color=0x00FF00
        )
        
        # Create list of alive players with their stats
        alive_list = []
        for player_id in alive_players:
            player_data = game["players"][player_id]
            line = f"**{player_data['name']}** {player_data['title']}"
            
            # Add district info
            district_name = DISTRICTS.get(player_data['district'], f"District {player_data['district']}")
            line += f" - {district_name}"
            
            # Add kill count if any
            if player_data['kills'] > 0:
                line += f" ⚔️ {player_data['kills']} kills"
            
            # Add revive count if any
            if player_data.get('revives', 0) > 0:
                line += f" ✨ {player_data['revives']} revives"
            
            alive_list.append(line)
        
        embed.description = "\n".join(alive_list)
        
        embed.add_field(
            name="📊 **Stats**",
            value=f"**Round:** {game['round']}\n**Survivors:** {len(alive_players)}/{len(game['players'])}",
            inline=True
        )
        
        # Show most dangerous player
        killers = [(pid, pdata) for pid, pdata in game["players"].items() 
                  if pdata["kills"] > 0 and pdata["alive"]]
        
        if killers:
            killers.sort(key=lambda x: x[1]["kills"], reverse=True)
            top_killer = killers[0][1]
            embed.add_field(
                name="⚔️ **Most Dangerous**",
                value=f"**{top_killer['name']}** ({top_killer['kills']} kills)",
                inline=True
            )
        
        embed.set_footer(text=f"Use `.hungergames status` for more details")
        await ctx.send(embed=embed)
    
    @hungergames.command(name="stats")
    async def hg_stats(self, ctx, member: discord.Member = None):
        """View Hunger Games statistics for yourself or another player"""
        if member is None:
            member = ctx.author
        
        member_data = await self.config.member(member).all()
        embed = create_player_stats_embed(member_data, member)
        await ctx.send(embed=embed)
    
    @hungergames.command(name="force")
    @commands.has_permissions(manage_guild=True)
    async def hg_force_event(self, ctx, event_type: str = "random"):
        """Force a single event in active game (Admin only)"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active game to force event in!")
        
        game = self.active_games[guild_id]
        if game["status"] != "active":
            return await ctx.send("❌ Game is not active!")
        
        valid_types = ["death", "survival", "sponsor", "alliance", "crate", "random", "combined"]
        if event_type.lower() not in valid_types:
            return await ctx.send(f"❌ Invalid event type! Use: {', '.join(valid_types)}")
        
        # Force execute an event
        try:
            if event_type.lower() == "random":
                await self.execute_random_event(game, ctx.channel)
            elif event_type.lower() == "combined":
                await self.execute_combined_events(game, ctx.channel)
            else:
                # Execute specific event type
                message = None
                if event_type.lower() == "death":
                    message = await self.game_engine.execute_death_event(game, ctx.channel) 
                elif event_type.lower() == "survival":
                    message = await self.game_engine.execute_survival_event(game)
                elif event_type.lower() == "sponsor":
                    message = await self.game_engine.execute_sponsor_event(game)
                elif event_type.lower() == "alliance":
                    message = await self.game_engine.execute_alliance_event(game)
                elif event_type.lower() == "crate":
                    message = await self.game_engine.execute_crate_event(game)
                
                if message:
                    # Choose appropriate color
                    if event_type.lower() == "death":
                        color = 0xFF4500
                    elif event_type.lower() == "crate":
                        color = 0x8B4513
                    elif event_type.lower() == "sponsor":
                        color = 0xFFD700
                    elif event_type.lower() == "alliance":
                        color = 0x4169E1
                    else:
                        color = 0x32CD32
                    
                    embed = discord.Embed(
                        description=message,
                        color=color
                    )
                    embed.set_footer(text=f"Forced {event_type.title()} Event")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ Failed to generate {event_type} event")
                    
        except Exception as e:
            await ctx.send(f"❌ Error forcing event: {str(e)}")
    
    @hungergames.command(name="debug")
    @commands.has_permissions(manage_guild=True)
    async def hg_debug(self, ctx):
        """Debug constants and imports (Admin only)"""
        embed = discord.Embed(
            title="🔍 **DEBUG INFO**",
            color=0x00CED1
        )
        
        # Check constants
        try:
            from .constants import DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS
            embed.add_field(
                name="📊 **Constants Loaded**",
                value=f"Death Events: {len(DEATH_EVENTS)}\n"
                      f"Survival Events: {len(SURVIVAL_EVENTS)}\n"
                      f"Sponsor Events: {len(SPONSOR_EVENTS)}\n"
                      f"Alliance Events: {len(ALLIANCE_EVENTS)}\n"
                      f"Crate Events: {len(CRATE_EVENTS)}",
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="❌ **Import Error**",
                value=str(e),
                inline=False
            )
        
        # Show sample events
        try:
            from .constants import DEATH_EVENTS, CRATE_EVENTS
            if DEATH_EVENTS:
                sample_death = DEATH_EVENTS[0]
                embed.add_field(
                    name="🎭 **Sample Death Event**",
                    value=f"```{sample_death}```",
                    inline=False
                )
            
            if CRATE_EVENTS:
                sample_crate = CRATE_EVENTS[0]
                embed.add_field(
                    name="📦 **Sample Crate Event**",
                    value=f"```{sample_crate}```",
                    inline=False
                )
        except Exception as e:
            embed.add_field(
                name="❌ **Sample Events Error**",
                value=str(e),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @hungergames.command(name="leaderboard", aliases=["lb", "top"])
    async def hg_leaderboard(self, ctx, stat: str = "wins"):
        """View the Hunger Games leaderboard
        
        Available stats: wins, kills, deaths, revives"""
        
        if stat.lower() not in ["wins", "kills", "deaths", "revives"]:
            return await ctx.send("❌ Invalid stat! Use: `wins`, `kills`, `deaths`, or `revives`")
        
        stat = stat.lower()
        
        # Get all member data
        all_members = await self.config.all_members(ctx.guild)
        
        # Filter and sort
        filtered_members = []
        for member_id, data in all_members.items():
            stat_value = data.get(stat, 0)
            if stat_value > 0:
                filtered_members.append((member_id, data))
        
        filtered_members.sort(key=lambda x: x[1].get(stat, 0), reverse=True)
        
        embed = create_leaderboard_embed(ctx.guild, filtered_members, stat)
        await ctx.send(embed=embed)
    
    @hungergames.command(name="stop")
    @commands.has_permissions(manage_guild=True)
    async def hg_stop(self, ctx):
        """Stop the current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active game to stop!")
        
        game = self.active_games[guild_id]
        
        # Cancel the game task
        if "task" in game:
            game["task"].cancel()
        
        # Clean up
        del self.active_games[guild_id]
        
        embed = discord.Embed(
            title="🛑 **GAME TERMINATED**",
            description="The Hunger Games have been forcibly ended by the Capitol.",
            color=0x000000
        )
        
        await ctx.send(embed=embed)
    
    @hungergames.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def hg_config(self, ctx):
        """View current Hunger Games configuration"""
        config_data = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="⚙️ **Hunger Games Configuration**",
            color=0x4169E1
        )
        
        embed.add_field(
            name="💰 **Base Reward**",
            value=f"{config_data['base_reward']:,} credits",
            inline=True
        )
        
        embed.add_field(
            name="🎁 **Sponsor Chance**",
            value=f"{config_data['sponsor_chance']}%",
            inline=True
        )
        
        embed.add_field(
            name="⏱️ **Event Interval**",
            value=f"{config_data['event_interval']} seconds",
            inline=True
        )
        
        embed.add_field(
            name="⏰ **Recruitment Time**",
            value=f"{config_data['recruitment_time']} seconds",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @hungergames.group(name="set", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def hg_set(self, ctx):
        """Configure Hunger Games settings"""
        await ctx.send_help()
    
    @hg_set.command(name="reward")
    async def hg_set_reward(self, ctx, amount: int):
        """Set the base reward amount"""
        if amount < 100:
            return await ctx.send("❌ Base reward must be at least 100 credits!")
        
        await self.config.guild(ctx.guild).base_reward.set(amount)
        await ctx.send(f"✅ Base reward set to {amount:,} credits!")
    
    @hg_set.command(name="sponsor")
    async def hg_set_sponsor(self, ctx, chance: int):
        """Set the sponsor revival chance (1-50%)"""
        if not 1 <= chance <= 50:
            return await ctx.send("❌ Sponsor chance must be between 1-50%!")
        
        await self.config.guild(ctx.guild).sponsor_chance.set(chance)
        await ctx.send(f"✅ Sponsor revival chance set to {chance}%!")
    
    @hg_set.command(name="interval")
    async def hg_set_interval(self, ctx, seconds: int):
        """Set the event interval (10-120 seconds)"""
        if not 10 <= seconds <= 120:
            return await ctx.send("❌ Event interval must be between 10-120 seconds!")
        
        await self.config.guild(ctx.guild).event_interval.set(seconds)
        await ctx.send(f"✅ Event interval set to {seconds} seconds!")
    
    @hungergames.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def hg_test(self, ctx):
        """Test game events (Admin only)"""
        # Create a fake game for testing
        test_game = {
            "players": {
                str(ctx.author.id): {
                    "name": ctx.author.display_name,
                    "title": "the Tester",
                    "alive": True,
                    "kills": 0,
                    "revives": 0,
                    "district": 1
                },
                "123456789": {
                    "name": "TestBot",
                    "title": "the Dummy",
                    "alive": True,
                    "kills": 0,
                    "revives": 0,
                    "district": 2
                },
                "987654321": {
                    "name": "TestBot2", 
                    "title": "the Mock",
                    "alive": True,
                    "kills": 0,
                    "revives": 0,
                    "district": 3
                }
            },
            "round": 1,
            "eliminated": [],
            "sponsor_used": []
        }
        
        embed = discord.Embed(
            title="🧪 **EVENT TESTING**",
            description="Testing game events...",
            color=0x00CED1
        )
        
        test_msg = await ctx.send(embed=embed)
        
        # Test combined events first
        try:
            await ctx.send("**Testing Combined Events:**")
            await self.execute_combined_events(test_game, ctx.channel)
            await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"❌ **COMBINED EVENTS ERROR**: {str(e)}")
        
        # Test each individual event type
        event_types = ["death", "survival", "sponsor", "alliance", "crate"]
        
        await ctx.send("**Testing Individual Events:**")
        
        for event_type in event_types:
            try:
                if event_type == "death":
                    message = await self.game_engine.execute_death_event(test_game, ctx.channel)
                elif event_type == "survival":
                    message = await self.game_engine.execute_survival_event(test_game)
                elif event_type == "sponsor":
                    message = await self.game_engine.execute_sponsor_event(test_game)
                elif event_type == "alliance":
                    message = await self.game_engine.execute_alliance_event(test_game)
                elif event_type == "crate":
                    message = await self.game_engine.execute_crate_event(test_game)
                
                if message:
                    # Choose appropriate color
                    if event_type == "death":
                        color = 0xFF4500
                    elif event_type == "crate":
                        color = 0x8B4513
                    elif event_type == "sponsor":
                        color = 0xFFD700
                    elif event_type == "alliance":
                        color = 0x4169E1
                    else:
                        color = 0x32CD32
                    
                    embed = discord.Embed(
                        title=f"✅ **{event_type.upper()} EVENT TEST**",
                        description=message,
                        color=color
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"❌ **{event_type.upper()} EVENT**: No message generated")
                    
                await asyncio.sleep(1)  # Brief pause between tests
                
            except Exception as e:
                await ctx.send(f"❌ **{event_type.upper()} EVENT ERROR**: {str(e)}")
        
    @hungergames.command(name="status")
    async def hg_status(self, ctx):
        """Check the status of current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        game = self.active_games[guild_id]
        alive_players = self.game_engine.get_alive_players(game)
        
        embed = discord.Embed(
            title="📊 **GAME STATUS**",
            color=0x4169E1
        )
        
        embed.add_field(
            name="🎮 **Status**",
            value=game["status"].capitalize(),
            inline=True
        )
        
        embed.add_field(
            name="👥 **Players Alive**",
            value=f"{len(alive_players)}/{len(game['players'])}",
            inline=True
        )
        
        embed.add_field(
            name="🔄 **Current Round**",
            value=str(game["round"]),
            inline=True
        )
        
        if game["status"] == "active":
            embed.add_field(
                name="⏰ **Task Status**",
                value="Running" if "task" in game and not game["task"].done() else "Stopped",
                inline=True
            )
        
        await ctx.send(embed=embed)


async def setup(bot):
    """Required function for loading the cog"""
    await bot.add_cog(HungerGames(bot))
