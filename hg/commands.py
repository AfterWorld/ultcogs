# commands.py
"""
Command handlers for Hunger Games cog
"""

import discord
import asyncio
import random
import logging
from typing import Optional
from datetime import datetime, timezone

from .constants import EMOJIS, get_random_player_title, get_random_district
from .utils import (
    create_recruitment_embed, create_game_start_embed, create_alive_players_embed,
    create_player_stats_embed, create_leaderboard_embed, format_player_list
)

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handles all command logic for the Hunger Games cog"""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
        self.validator = cog.validator
        self.poll_system = cog.poll_system
    
    # =====================================================
    # MAIN GAME COMMANDS
    # =====================================================
    
    async def handle_hunger_games_event(self, ctx, countdown: int = 60):
        """Handle the main .he command"""
        guild_id = ctx.guild.id
        
        # Enhanced input validation
        valid, error_msg = self.validator.validate_countdown(countdown)
        if not valid:
            return await ctx.send(f"❌ {error_msg}")
        
        if guild_id in self.cog.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        try:
            # Create the game instance with validation
            await self._initialize_new_game(ctx, countdown)
        except Exception as e:
            logger.error(f"Failed to initialize game in guild {guild_id}: {e}", exc_info=True)
            await ctx.send("❌ Failed to start the game. Please try again.")
    
    async def handle_hg_command(self, ctx, args=None):
        """Handle the .hg command (simple poll system)"""
        guild_id = ctx.guild.id
        
        # Check if game already running
        if guild_id in self.cog.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        # Parse arguments
        threshold = 5  # default
        use_poll_system = False
        
        if args:
            if args.lower() == "poll":
                # Use server's configured threshold with poll system
                threshold = await self.config.guild(ctx.guild).poll_threshold()
                if threshold is None:
                    return await ctx.send(
                        "❌ No poll threshold is set for this server! "
                        "Use `.hungergames set pollthreshold <number>` to set one."
                    )
                use_poll_system = True
            else:
                # Try to parse as number
                try:
                    threshold = int(args)
                except ValueError:
                    return await ctx.send(
                        "❌ Invalid argument! Use:\n"
                        "• `.hg` - Default threshold (5) with reactions\n"
                        "• `.hg poll` - Use server threshold with buttons\n"
                        "• `.hg 8` - Specific threshold with reactions"
                    )
        
        # Validate threshold
        valid, error_msg = self.validator.validate_poll_threshold(threshold)
        if not valid:
            return await ctx.send(f"❌ {error_msg}")
        
        # Use poll system if requested and available
        if use_poll_system:
            error_message = await self.validator.validate_poll_starter(ctx.author, self.config)
            if error_message:
                return await ctx.send(error_message)
            
            success = await self.poll_system.create_poll(ctx, threshold, use_advanced=True)
            if success:
                return
        
        # Fallback to regular recruitment system
        poll_ping_role_id = await self.config.guild(ctx.guild).poll_ping_role()
        
        # Send role ping first if configured
        if poll_ping_role_id:
            role = ctx.guild.get_role(poll_ping_role_id)
            if role:
                try:
                    # Send separate ping message
                    ping_msg = await ctx.send(
                        f"{role.mention} 🗳️ **Starting Hunger Games!**",
                        allowed_mentions=discord.AllowedMentions(roles=True)
                    )
                    # Delete after brief moment
                    await asyncio.sleep(1)
                    try:
                        await ping_msg.delete()
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Failed to ping role: {e}")
        
        # Send main poll message (without role mention to avoid double ping)
        poll_message = f"🗳️ **Starting Hunger Games!**\n"
        poll_message += f"Need **{threshold}** players - react with 🏹 to join!\n"
        poll_message += f"Game will start in 60 seconds..."
        
        await ctx.send(poll_message)
    
    async def handle_poll_command(self, ctx, threshold: int = None):
        """Handle the .poll command"""
        guild_id = ctx.guild.id
        
        # Check if game already running
        if guild_id in self.cog.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        # Get threshold
        if threshold is None:
            threshold = await self.config.guild(ctx.guild).poll_threshold()
            if threshold is None:
                return await ctx.send(
                    "❌ No poll threshold is set for this server! "
                    "An admin needs to set it with `.hungergames set pollthreshold <number>`"
                )
        else:
            # Validate provided threshold
            if not ctx.author.guild_permissions.manage_guild:
                return await ctx.send("❌ Only admins can override the poll threshold!")
            
            valid, error_msg = self.validator.validate_poll_threshold(threshold)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
        
        # Create poll
        await self.poll_system.create_poll(ctx, threshold)
    
    async def _initialize_new_game(self, ctx, countdown: int):
        """Initialize a new game with proper error handling"""
        guild_id = ctx.guild.id
        
        self.cog.active_games[guild_id] = {
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
        
        self.cog.active_games[guild_id]["message"] = message
        
        # Start recruitment countdown
        await self._recruitment_countdown(guild_id, countdown)
    
    async def _recruitment_countdown(self, guild_id: int, countdown: int):
        """Handle the recruitment countdown and reaction monitoring"""
        game = self.cog.active_games[guild_id]
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
            del self.cog.active_games[guild_id]
            return
        except Exception as e:
            logger.error(f"Error during recruitment countdown: {e}")
        
        # Recruitment ended, start the game
        await self._start_battle_royale(guild_id)
    
    async def _update_recruitment_message(self, game, message, channel, remaining):
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
    
    async def _start_battle_royale(self, guild_id: int):
        """Start the actual battle royale game"""
        try:
            game = self.cog.active_games[guild_id]
            channel = game["channel"]
            
            # Validate game state before starting
            if not self.validator.validate_game_state(game):
                raise Exception("Game state is invalid before start")
            
            # Check if we have enough players
            player_count = len(game["players"])
            if player_count < 2:
                embed = discord.Embed(
                    title="❌ **INSUFFICIENT TRIBUTES**",
                    description="Need at least 2 brave souls to enter the arena!",
                    color=0xFF0000
                )
                await channel.send(embed=embed)
                del self.cog.active_games[guild_id]
                return
            
            game["status"] = "active"
            
            # Send game start messages
            await self._send_game_start_messages(game, player_count)
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.cog.game_loop(guild_id))
            logger.info(f"Started Hunger Games with {player_count} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to start battle royale in guild {guild_id}: {e}", exc_info=True)
            await channel.send("❌ Failed to start the battle royale. Game cancelled.")
            if guild_id in self.cog.active_games:
                del self.cog.active_games[guild_id]
    
    async def _send_game_start_messages(self, game, player_count):
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
    
    # =====================================================
    # GAME INFO COMMANDS
    # =====================================================
    
    async def handle_alive(self, ctx):
        """Show current alive players in the active game"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        try:
            game = self.cog.active_games[guild_id]
            alive_players = self.cog.game_engine.get_alive_players(game)
            
            if not alive_players:
                return await ctx.send("💀 No survivors remain!")
            
            embed = create_alive_players_embed(game, alive_players)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing alive players: {e}")
            await ctx.send("❌ Error retrieving player information.")
    
    async def handle_stats(self, ctx, member: discord.Member = None):
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
    
    async def handle_status(self, ctx):
        """Check the status of current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        try:
            game = self.cog.active_games[guild_id]
            alive_players = self.cog.game_engine.get_alive_players(game)
            
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
                task_status = "Unknown"
                if "task" in game:
                    if game["task"].done():
                        task_status = "Completed"
                    elif game["task"].cancelled():
                        task_status = "Cancelled"
                    else:
                        task_status = "Running"
                
                embed.add_field(
                    name="⏰ **Task Status**",
                    value=task_status,
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            await ctx.send("❌ Error retrieving game status.")
    
    async def handle_leaderboard(self, ctx, stat: str = "wins"):
        """View the Hunger Games leaderboard"""
        try:
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
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await ctx.send("❌ Error retrieving leaderboard data.")
    
    # =====================================================
    # ADMIN COMMANDS
    # =====================================================
    
    async def handle_stop(self, ctx):
        """Stop the current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active game to stop!")
        
        try:
            game = self.cog.active_games[guild_id]
            
            # Cancel the game task
            if "task" in game:
                game["task"].cancel()
            
            # Clean up
            if guild_id in self.cog.active_games:
                del self.cog.active_games[guild_id]
            
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
    
    async def handle_test(self, ctx):
        """Test game events (Admin only)"""
        try:
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
                "sponsor_used": [],
                "reactions": set(),
                "milestones_shown": set(),
                "channel": ctx.channel
            }
            
            embed = discord.Embed(
                title="🧪 **EVENT TESTING**",
                description="Testing game events...",
                color=0x00CED1
            )
            
            await ctx.send(embed=embed)
            
            # Test each individual event type
            event_types = ["death", "survival", "sponsor", "alliance", "crate"]
            
            await ctx.send("**Testing Individual Events:**")
            
            for event_type in event_types:
                try:
                    message = await self.cog.event_handler.execute_event(event_type, test_game, ctx.channel)
                    
                    if message:
                        # Choose appropriate color
                        colors = {
                            "death": 0xFF4500,
                            "crate": 0x8B4513,
                            "sponsor": 0xFFD700,
                            "alliance": 0x4169E1,
                            "survival": 0x32CD32
                        }
                        
                        color = colors.get(event_type, 0x32CD32)
                        
                        embed = discord.Embed(
                            title=f"✅ **{event_type.upper()} EVENT TEST**",
                            description=message,
                            color=color
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"❌ **{event_type.upper()} EVENT**: No message generated")
                        
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    await ctx.send(f"❌ **{event_type.upper()} EVENT ERROR**: {str(e)}")
            
            await ctx.send("🎉 **Testing Complete!**")
            
        except Exception as e:
            logger.error(f"Error in test command: {e}")
            await ctx.send(f"❌ Error running tests: {str(e)}")
    
    async def handle_debug(self, ctx):
        """Debug current game state (Admin only)"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active game to debug!")
        
        try:
            game = self.cog.active_games[guild_id]
            
            embed = discord.Embed(
                title="🔧 **DEBUG INFO**",
                color=0xFF8C00
            )
            
            embed.add_field(
                name="📊 **Game State**",
                value=f"Status: {game['status']}\nRound: {game['round']}\nTotal Players: {len(game['players'])}",
                inline=True
            )
            
            alive_count = len(self.cog.game_engine.get_alive_players(game))
            embed.add_field(
                name="👥 **Player Counts**",
                value=f"Alive: {alive_count}\nEliminated: {len(game['eliminated'])}\nReactions: {len(game.get('reactions', set()))}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 **Systems**",
                value=(
                    f"Game Engine: {'✅' if hasattr(self.cog, 'game_engine') else '❌'}\n"
                    f"Image System: {'✅' if hasattr(self.cog, 'image_handler') and self.cog.image_handler else '❌'}\n"
                    f"GIF System: {'✅' if hasattr(self.cog, 'gif_manager') and self.cog.gif_manager else '❌'}"
                ),
                inline=True
            )
            
            if "task" in game:
                task_info = "Running" if not game["task"].done() else "Completed"
                if game["task"].cancelled():
                    task_info = "Cancelled"
            else:
                task_info = "No Task"
            
            embed.add_field(
                name="⏰ **Task Info**",
                value=task_info,
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in debug command: {e}")
            await ctx.send(f"❌ Debug error: {str(e)}")
    
    async def handle_config(self, ctx):
        """View current Hunger Games configuration"""
        try:
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
            
            # Poll threshold
            poll_threshold = config_data.get('poll_threshold')
            if poll_threshold is not None:
                embed.add_field(
                    name="🗳️ **Poll Threshold**",
                    value=f"{poll_threshold} players",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🗳️ **Poll Threshold**",
                    value="❌ Not set",
                    inline=True
                )
            
            # Poll ping role
            poll_ping_role_id = config_data.get('poll_ping_role')
            if poll_ping_role_id:
                ping_role = ctx.guild.get_role(poll_ping_role_id)
                if ping_role:
                    embed.add_field(
                        name="📢 **Poll Ping Role**",
                        value=ping_role.mention,
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="📢 **Poll Ping Role**",
                        value="❌ Invalid role",
                        inline=True
                    )
            else:
                embed.add_field(
                    name="📢 **Poll Ping Role**",
                    value="❌ Not set",
                    inline=True
                )
            
            # Add image system status
            images_enabled = config_data.get('enable_custom_images', True)
            image_status = "❌ Disabled"
            if images_enabled:
                if hasattr(self.cog, 'image_handler') and self.cog.image_handler and self.cog.image_handler.is_available():
                    image_status = "✅ Active"
                else:
                    image_status = "⚠️ Enabled (No Template)"
            
            embed.add_field(
                name="🖼️ **Custom Images**",
                value=image_status,
                inline=True
            )
            
            # Blacklisted roles
            blacklisted_roles = config_data.get('blacklisted_roles', [])
            if blacklisted_roles:
                role_mentions = []
                for role_id in blacklisted_roles[:5]:  # Show max 5
                    role = ctx.guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)
                
                if role_mentions:
                    roles_text = "\n".join(role_mentions)
                    if len(blacklisted_roles) > 5:
                        roles_text += f"\n... and {len(blacklisted_roles) - 5} more"
                else:
                    roles_text = "None (invalid role IDs)"
                
                embed.add_field(
                    name="🚫 **Blacklisted Roles**",
                    value=roles_text,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in config command: {e}")
            await ctx.send("❌ Error retrieving configuration.")
    
    # =====================================================
    # HELP COMMAND
    # =====================================================
    
    async def handle_hungergames_help(self, ctx):
        """Show help for hungergames commands"""
        embed = discord.Embed(
            title="🏹 **Hunger Games Commands** 🏹",
            color=0x4169E1
        )
        
        embed.add_field(
            name="🎮 **Game Commands**",
            value=(
                "• `.he [countdown]` - Start a battle royale\n"
                "• `.hg poll [threshold]` - Start a poll to gather players\n"
                "• `.hungergames alive` - Show alive players\n"
                "• `.hungergames status` - Check game status\n"
                "• `.hungergames stop` - Stop current game (Admin)\n"
                "• `.hungergames stats [member]` - View statistics"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ **Configuration (Admin)**",
            value=(
                "• `.hungergames set reward <amount>` - Set base reward\n"
                "• `.hungergames set sponsor <chance>` - Set sponsor chance\n"
                "• `.hungergames set interval <seconds>` - Set event interval\n"
                "• `.hungergames set pollthreshold <number>` - Set poll threshold\n"
                "• `.hungergames set pollpingrole <role>` - Set role to ping for polls\n"
                "• `.hungergames set blacklistrole <role> <add/remove>` - Manage role blacklist\n"
                "• `.hungergames set tempban <member> <duration>` - Temporary ban"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 **Information**",
            value=(
                "• `.hungergames config` - View current settings\n"
                "• `.hungergames leaderboard [stat]` - View leaderboards\n"
                "• `.hungergames test` - Test events (Admin)\n"
                "• `.hungergames debug` - Debug info (Admin)"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use .help <command> for detailed information")
        await ctx.send(embed=embed)
    
    # =====================================================
    # CONFIGURATION COMMANDS
    # =====================================================
    
    async def handle_set_poll_threshold(self, ctx, threshold: int = None):
        """Set the minimum players needed for a poll to start a game"""
        try:
            if threshold is None:
                await self.config.guild(ctx.guild).poll_threshold.set(None)
                await ctx.send("✅ Poll threshold disabled! Polls will not work until a threshold is set.")
            else:
                valid, error_msg = self.validator.validate_poll_threshold(threshold)
                if not valid:
                    return await ctx.send(f"❌ {error_msg}")
                
                await self.config.guild(ctx.guild).poll_threshold.set(threshold)
                await ctx.send(f"✅ Poll threshold set to {threshold} players!")
                
        except Exception as e:
            logger.error(f"Error setting poll threshold: {e}")
            await ctx.send("❌ Error updating poll threshold.")
    
    async def handle_set_poll_ping_role(self, ctx, role: discord.Role = None):
        """Set the role to ping when polls start"""
        try:
            if role is None:
                await self.config.guild(ctx.guild).poll_ping_role.set(None)
                await ctx.send("✅ Poll ping role disabled! No role will be pinged for polls.")
            else:
                # Check if role is mentionable
                if not role.mentionable:
                    embed = discord.Embed(
                        title="⚠️ **Role Setup Warning**",
                        description=(
                            f"Role {role.mention} has been set as the poll ping role, but it's **not mentionable**!\n\n"
                            f"**To make role pings work:**\n"
                            f"1. Go to Server Settings → Roles\n"
                            f"2. Click on the `{role.name}` role\n"
                            f"3. Enable **'Allow anyone to @mention this role'**\n\n"
                            f"**Test the ping:** Use `.hungergames set testping` after enabling mentionable"
                        ),
                        color=0xFF8000
                    )
                    await self.config.guild(ctx.guild).poll_ping_role.set(role.id)
                    await ctx.send(embed=embed)
                else:
                    await self.config.guild(ctx.guild).poll_ping_role.set(role.id)
                    embed = discord.Embed(
                        title="✅ **Poll Ping Role Set**",
                        description=(
                            f"Poll ping role set to {role.mention}!\n\n"
                            f"**What happens now:**\n"
                            f"• Members with this role will be pinged when polls start\n"
                            f"• Use `.hungergames set testping` to test the ping\n"
                            f"• Polls can be started with `.hg poll` or `.poll`"
                        ),
                        color=0x00FF00
                    )
                    await ctx.send(embed=embed)
                    
        except Exception as e:
            logger.error(f"Error setting poll ping role: {e}")
            await ctx.send("❌ Error updating poll ping role.")
    
    async def handle_set_blacklist_role(self, ctx, role: discord.Role, action: str = "add"):
        """Add or remove a role from the blacklist"""
        try:
            action = action.lower()
            if action not in ["add", "remove"]:
                return await ctx.send("❌ Action must be 'add' or 'remove'!")
            
            blacklisted_roles = await self.config.guild(ctx.guild).blacklisted_roles()
            
            if action == "add":
                if role.id in blacklisted_roles:
                    return await ctx.send(f"❌ {role.mention} is already blacklisted!")
                
                blacklisted_roles.append(role.id)
                await self.config.guild(ctx.guild).blacklisted_roles.set(blacklisted_roles)
                await ctx.send(f"✅ Added {role.mention} to the blacklist!")
                
            else:  # remove
                if role.id not in blacklisted_roles:
                    return await ctx.send(f"❌ {role.mention} is not blacklisted!")
                
                blacklisted_roles.remove(role.id)
                await self.config.guild(ctx.guild).blacklisted_roles.set(blacklisted_roles)
                await ctx.send(f"✅ Removed {role.mention} from the blacklist!")
                
        except Exception as e:
            logger.error(f"Error managing blacklist role: {e}")
            await ctx.send("❌ Error updating role blacklist.")
    
    async def handle_set_temp_ban(self, ctx, member: discord.Member, duration: str = None):
        """Temporarily ban a member from Hunger Games"""
        try:
            if duration is None or duration.lower() == "remove":
                await self.config.member(member).temp_banned_until.set(None)
                await ctx.send(f"✅ Removed temporary ban from {member.mention}!")
                return
            
            # Parse duration
            valid, error_msg, total_seconds = self.validator.validate_temp_ban_duration(duration)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            # Set ban
            ban_until = datetime.now(timezone.utc).timestamp() + total_seconds
            await self.config.member(member).temp_banned_until.set(ban_until)
            
            # Format duration for display
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            display_duration = []
            if days:
                display_duration.append(f"{days}d")
            if hours:
                display_duration.append(f"{hours}h")
            if minutes:
                display_duration.append(f"{minutes}m")
            
            await ctx.send(f"✅ Temporarily banned {member.mention} for {' '.join(display_duration)}!")
                
        except Exception as e:
            logger.error(f"Error setting temp ban: {e}")
            await ctx.send("❌ Error setting temporary ban.")
    
    async def handle_set_reward(self, ctx, amount: int):
        """Set the base reward amount"""
        try:
            valid, error_msg = self.validator.validate_base_reward(amount)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).base_reward.set(amount)
            await ctx.send(f"✅ Base reward set to {amount:,} credits!")
            
        except Exception as e:
            logger.error(f"Error setting reward: {e}")
            await ctx.send("❌ Error updating reward amount.")
    
    async def handle_set_sponsor(self, ctx, chance: int):
        """Set the sponsor revival chance (1-50%)"""
        try:
            valid, error_msg = self.validator.validate_sponsor_chance(chance)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).sponsor_chance.set(chance)
            await ctx.send(f"✅ Sponsor revival chance set to {chance}%!")
            
        except Exception as e:
            logger.error(f"Error setting sponsor chance: {e}")
            await ctx.send("❌ Error updating sponsor chance.")
    
    async def handle_set_interval(self, ctx, seconds: int):
        """Set the event interval (10-120 seconds)"""
        try:
            valid, error_msg = self.validator.validate_event_interval(seconds)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).event_interval.set(seconds)
            await ctx.send(f"✅ Event interval set to {seconds} seconds!")
            
        except Exception as e:
            logger.error(f"Error setting interval: {e}")
            await ctx.send("❌ Error updating event interval.")

    # =====================================================
    # Arena handlers
    # =====================================================
    

    async def handle_condition_test(self, ctx, condition_name: str = None):
        """Test arena conditions (Admin only)"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active game to test conditions on!")
        
        try:
            game = self.cog.active_games[guild_id]
            
            if condition_name:
                # Test specific condition
                from .arena_conditions import GRAND_LINE_CONDITIONS
                if condition_name.lower() not in GRAND_LINE_CONDITIONS:
                    available = ", ".join(GRAND_LINE_CONDITIONS.keys())
                    return await ctx.send(f"❌ Invalid condition! Available: {available}")
                
                # Force the condition
                await self.cog.game_engine.condition_manager.select_condition(
                    game["round"], 
                    len(self.cog.game_engine.get_alive_players(game)),
                    force_condition=condition_name.lower()
                )
                
                # Send announcement
                announcement = self.cog.game_engine.condition_manager.get_condition_announcement()
                embed = discord.Embed(
                    title="🧪 **CONDITION TEST** 🧪",
                    description=f"**Testing:** {condition_name}\n\n{announcement}",
                    color=0x00CED1
                )
            else:
                # Test random condition
                await self.cog.game_engine.select_arena_condition(game, ctx.channel)
                embed = discord.Embed(
                    title="🧪 **RANDOM CONDITION TEST** 🧪",
                    description="Random arena condition selected for testing!",
                    color=0x00CED1
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in condition test: {e}")
            await ctx.send(f"❌ Error testing condition: {str(e)}")
    
    async def handle_condition_info(self, ctx):
        """Show current arena condition info"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.cog.active_games:
            return await ctx.send("❌ No active game to check conditions!")
        
        try:
            condition_info = self.cog.game_engine.condition_manager.get_current_condition_info()
            
            if not condition_info:
                return await ctx.send("🌊 No arena condition currently active.")
            
            embed = discord.Embed(
                title="🌊 **CURRENT ARENA CONDITION** 🌊",
                color=0x4169E1
            )
            
            embed.add_field(
                name="📍 **Condition**",
                value=condition_info['name'],
                inline=True
            )
            
            embed.add_field(
                name="⏰ **Duration**",
                value=f"{condition_info['duration']} rounds remaining",
                inline=True
            )
            
            embed.add_field(
                name="📝 **Description**",
                value=condition_info['description'],
                inline=False
            )
            
            # Show effects if any
            if condition_info.get('effects'):
                effects_text = []
                for effect, value in condition_info['effects'].items():
                    if isinstance(value, float):
                        percentage = f"{value*100:+.0f}%"
                        effects_text.append(f"• {effect.replace('_', ' ').title()}: {percentage}")
                
                if effects_text:
                    embed.add_field(
                        name="⚡ **Active Effects**",
                        value="\n".join(effects_text),
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting condition info: {e}")
            await ctx.send("❌ Error retrieving condition information.")
    
    async def handle_condition_list(self, ctx):
        """List all available arena conditions"""
        try:
            from .arena_conditions import GRAND_LINE_CONDITIONS
            
            embed = discord.Embed(
                title="🌊 **GRAND LINE CONDITIONS** 🌊",
                description="All available arena conditions:",
                color=0x4169E1
            )
            
            for condition_key, condition_data in GRAND_LINE_CONDITIONS.items():
                embed.add_field(
                    name=condition_data["name"],
                    value=condition_data["description"],
                    inline=False
                )
            
            embed.set_footer(text="Use .hungergames condition test <name> to test a specific condition")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing conditions: {e}")
            await ctx.send("❌ Error retrieving condition list.")
