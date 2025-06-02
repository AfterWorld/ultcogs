# poll_system.py
"""
Poll system for Hunger Games cog
"""

import discord
import asyncio
import logging
from typing import Set, Optional

logger = logging.getLogger(__name__)

# Try to import advanced poll system
try:
    from .poll_view import PollView
    POLL_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Advanced poll system not available: {e}")
    POLL_SYSTEM_AVAILABLE = False


class PollSystem:
    """Handles poll creation and management for Hunger Games"""
    
    def __init__(self, cog):
        self.cog = cog
        self.bot = cog.bot
        self.config = cog.config
    
    async def create_poll(self, ctx, threshold: int, use_advanced: bool = True) -> bool:
        """Create a poll for starting a Hunger Games
        
        Returns True if poll was created successfully, False otherwise
        """
        try:
            # Validate threshold
            if threshold < 2:
                await ctx.send("❌ Threshold must be at least 2 players!")
                return False
            
            if threshold > 50:
                await ctx.send("❌ Threshold cannot exceed 50 players!")
                return False
            
            # Check if user can start poll
            error_message = await self.cog.validator.validate_poll_starter(ctx.author, self.config)
            if error_message:
                await ctx.send(error_message)
                return False
            
            # Try advanced poll system first if requested and available
            if use_advanced and POLL_SYSTEM_AVAILABLE:
                try:
                    await self._create_advanced_poll(ctx, threshold)
                    return True
                except Exception as e:
                    logger.error(f"Advanced poll failed: {e}")
                    # Fall through to simple poll
            
            # Fallback to simple poll
            await self._create_simple_poll(ctx, threshold)
            return True
            
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
            await ctx.send("❌ Failed to create poll.")
            return False
    
    async def _create_advanced_poll(self, ctx, threshold: int):
        """Create advanced button-based poll with proper role pinging"""
        # Create and start poll with role ping integrated
        poll_view = PollView(self.cog, threshold, timeout=600)
        await poll_view.start(ctx)
        await poll_view.wait()
    
    async def _create_simple_poll(self, ctx, threshold: int):
        """Create simple reaction-based poll with proper role pinging"""
        # Get role to ping
        poll_ping_role_id = await self.config.guild(ctx.guild).poll_ping_role()
        role_mention = ""
        if poll_ping_role_id:
            role = ctx.guild.get_role(poll_ping_role_id)
            if role:
                role_mention = f"{role.mention} "
        
        # Send main poll message with role mention
        poll_message = (
            f"{role_mention}🗳️ **Pirate Royale Poll Started!**\n"
            f"**Target:** {threshold} players\n"
            f"React with 🏹 to join!\n"
            f"Game will start in 60 seconds..."
        )
        
        message = await ctx.send(
            poll_message,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        await message.add_reaction("🏹")
        
        # Wait for reactions and start game when threshold is met
        await self._run_simple_poll(ctx, message, threshold, 60)
    
    async def _run_simple_poll(self, ctx, message: discord.Message, threshold: int, timeout: int):
        """Run a simple poll system that waits for reactions"""
        guild_id = ctx.guild.id
        players = set()
        end_time = asyncio.get_event_loop().time() + timeout
        
        try:
            while asyncio.get_event_loop().time() < end_time:
                # Check reactions
                try:
                    fresh_message = await ctx.channel.fetch_message(message.id)
                    bow_reaction = None
                    
                    for reaction in fresh_message.reactions:
                        if str(reaction.emoji) == "🏹":
                            bow_reaction = reaction
                            break
                    
                    if bow_reaction:
                        current_players = set()
                        async for user in bow_reaction.users():
                            if not user.bot:
                                current_players.add(user.id)
                        
                        # Update players set
                        new_players = current_players - players
                        if new_players:
                            players = current_players
                            
                            # Update message with current count
                            remaining_time = int(end_time - asyncio.get_event_loop().time())
                            
                            embed = discord.Embed(
                                title="🗳️ **HUNGER GAMES POLL** 🗳️",
                                color=0x00FF00 if len(players) >= threshold else 0x4169E1
                            )
                            
                            progress = len(players) / threshold
                            filled_bars = int(progress * 10)
                            empty_bars = 10 - filled_bars
                            progress_bar = "█" * filled_bars + "░" * empty_bars
                            
                            description = (
                                f"**A battle royale is being proposed!**\n\n"
                                f"🎯 **Target:** {threshold} players\n"
                                f"👥 **Current:** {len(players)} players\n"
                                f"📊 **Progress:** `{progress_bar}` {len(players)}/{threshold}\n\n"
                            )
                            
                            if len(players) >= threshold:
                                description += "✅ **Threshold reached! Starting game...**"
                            else:
                                needed = threshold - len(players)
                                description += f"⏳ **Need {needed} more player{'s' if needed != 1 else ''}**\n"
                                description += f"⏰ **Time left:** {remaining_time}s"
                            
                            embed.description = description
                            
                            # Show joined players
                            if players:
                                player_names = []
                                for user_id in list(players)[:8]:
                                    member = ctx.guild.get_member(user_id)
                                    if member:
                                        player_names.append(f"🏹 {member.display_name}")
                                
                                if player_names:
                                    players_text = "\n".join(player_names)
                                    if len(players) > 8:
                                        players_text += f"\n*... and {len(players) - 8} more*"
                                    
                                    embed.add_field(name="**Joined Tributes**", value=players_text, inline=False)
                            
                            await message.edit(embed=embed)
                            
                            # Check if threshold reached
                            if len(players) >= threshold:
                                await asyncio.sleep(2)
                                await self._start_poll_game(ctx, players)
                                return
                
                except discord.NotFound:
                    await ctx.send("❌ Poll message was deleted!")
                    return
                except Exception as e:
                    logger.error(f"Error in simple poll: {e}")
                
                await asyncio.sleep(2)  # Check every 2 seconds
            
            # Timeout - check if we have enough players
            if len(players) >= 2:
                await ctx.send(f"⏰ **Poll timed out** but we have {len(players)} players! Starting game...")
                await self._start_poll_game(ctx, players)
            else:
                embed = discord.Embed(
                    title="⏰ **POLL EXPIRED**",
                    description=f"Only {len(players)} player{'s' if len(players) != 1 else ''} joined. Need at least 2 to start.",
                    color=0xFF0000
                )
                await message.edit(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in simple poll: {e}")
            await ctx.send("❌ Poll system encountered an error.")
    
    async def _start_poll_game(self, ctx, players: Set[int]):
        """Start game with poll participants"""
        try:
            guild_id = ctx.guild.id
            
            # Import utility functions
            from .constants import get_random_player_title, get_random_district
            
            # Create game instance
            self.cog.active_games[guild_id] = {
                "channel": ctx.channel,
                "players": {},
                "status": "active",
                "round": 0,
                "eliminated": [],
                "sponsor_used": [],
                "reactions": set(),
                "milestones_shown": set()
            }
            
            game = self.cog.active_games[guild_id]
            
            # Add poll participants as players
            for user_id in players:
                member = ctx.guild.get_member(user_id)
                if member:
                    game["players"][str(user_id)] = {
                        "name": member.display_name,
                        "title": get_random_player_title(),
                        "alive": True,
                        "kills": 0,
                        "revives": 0,
                        "district": get_random_district()
                    }
            
            player_count = len(game["players"])
            
            # Send game start messages
            await ctx.send(f"🎮 **Game starting with {player_count} tributes!**")
            await asyncio.sleep(2)
            await self.cog._send_game_start_messages(game, player_count)
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.cog.game_loop(guild_id))
            
            logger.info(f"Started Hunger Games via poll with {player_count} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error starting poll game: {e}")
            if guild_id in self.cog.active_games:
                del self.cog.active_games[guild_id]
            await ctx.send("❌ Failed to start the game.")
