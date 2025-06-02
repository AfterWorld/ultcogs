# poll_view.py - BUTTON-BASED POLL SYSTEM
"""
Advanced button-based poll system for Hunger Games
"""

import discord
import asyncio
import logging
from typing import Set, Optional

from .constants import get_random_player_title, get_random_district

logger = logging.getLogger(__name__)


class PollView(discord.ui.View):
    """Advanced button-based poll for Hunger Games recruitment"""
    
    def __init__(self, cog, threshold: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.threshold = threshold
        self.participants: Set[int] = set()
        self.message: Optional[discord.Message] = None
        self.ctx = None
        self.game_started = False
    
    async def start(self, ctx):
        """Start the poll with proper role pinging"""
        self.ctx = ctx
        
        # Get role to ping
        poll_ping_role_id = await self.cog.config.guild(ctx.guild).poll_ping_role()
        role_mention = ""
        if poll_ping_role_id:
            role = ctx.guild.get_role(poll_ping_role_id)
            if role:
                role_mention = f"{role.mention} "
        
        # Create initial embed
        embed = self._create_poll_embed()
        
        # Send poll message with role mention if configured
        content = f"{role_mention}🗳️ **Pirate Royale Poll Started!**" if role_mention else None
        self.message = await ctx.send(
            content=content, 
            embed=embed, 
            view=self,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
    
    def _create_poll_embed(self) -> discord.Embed:
        """Create the poll embed"""
        current_count = len(self.participants)
        progress = min(current_count / self.threshold, 1.0)
        
        # Progress bar
        filled_bars = int(progress * 10)
        empty_bars = 10 - filled_bars
        progress_bar = "█" * filled_bars + "░" * empty_bars
        
        # Color based on progress
        if current_count >= self.threshold:
            color = 0x00FF00  # Green - ready
        elif current_count >= self.threshold * 0.75:
            color = 0xFFFF00  # Yellow - close
        else:
            color = 0x4169E1  # Blue - need more
        
        embed = discord.Embed(
            title="🗳️ **HUNGER GAMES POLL** 🗳️",
            color=color
        )
        
        description = (
            f"**A battle royale is being proposed!**\n\n"
            f"🎯 **Target:** {self.threshold} players\n"
            f"👥 **Current:** {current_count} players\n"
            f"📊 **Progress:** `{progress_bar}` {current_count}/{self.threshold}\n\n"
        )
        
        if current_count >= self.threshold:
            description += "✅ **Threshold reached! Ready to start!**"
        else:
            needed = self.threshold - current_count
            description += f"⏳ **Need {needed} more player{'s' if needed != 1 else ''}**"
        
        embed.description = description
        
        # Show joined players (up to 8)
        if self.participants:
            player_names = []
            for user_id in list(self.participants)[:8]:
                member = self.ctx.guild.get_member(user_id)
                if member:
                    player_names.append(f"🏹 {member.display_name}")
            
            if player_names:
                players_text = "\n".join(player_names)
                if len(self.participants) > 8:
                    players_text += f"\n*... and {len(self.participants) - 8} more*"
                
                embed.add_field(
                    name="**Joined Tributes**",
                    value=players_text,
                    inline=False
                )
        
        return embed
    
    @discord.ui.button(label="Join Game", style=discord.ButtonStyle.green, emoji="🏹")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle join button press"""
        try:
            # Check if user can join
            error_message = await self.cog.validator.validate_poll_starter(interaction.user, self.cog.config)
            if error_message:
                return await interaction.response.send_message(error_message, ephemeral=True)
            
            # Add user to participants
            if interaction.user.id in self.participants:
                return await interaction.response.send_message("❌ You're already in the poll!", ephemeral=True)
            
            self.participants.add(interaction.user.id)
            
            # Update embed
            embed = self._create_poll_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Check if we can start
            if len(self.participants) >= self.threshold and not self.game_started:
                self.game_started = True
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                
                # Start game after short delay
                await asyncio.sleep(3)
                await self._start_game()
                
        except Exception as e:
            logger.error(f"Error in join button: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
    
    @discord.ui.button(label="Leave Game", style=discord.ButtonStyle.red, emoji="❌")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle leave button press"""
        try:
            if interaction.user.id not in self.participants:
                return await interaction.response.send_message("❌ You're not in the poll!", ephemeral=True)
            
            self.participants.remove(interaction.user.id)
            
            # Update embed
            embed = self._create_poll_embed()
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Error in leave button: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
    
    @discord.ui.button(label="Start Now", style=discord.ButtonStyle.blurple, emoji="🎮")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle force start button press (for admins)"""
        try:
            # Check permissions
            if not interaction.user.guild_permissions.manage_guild:
                return await interaction.response.send_message("❌ Only admins can force start!", ephemeral=True)
            
            # Need at least 2 players
            if len(self.participants) < 2:
                return await interaction.response.send_message("❌ Need at least 2 players to start!", ephemeral=True)
            
            if self.game_started:
                return await interaction.response.send_message("❌ Game is already starting!", ephemeral=True)
            
            self.game_started = True
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            
            await interaction.response.edit_message(view=self)
            
            # Start game
            await self._start_game()
            
        except Exception as e:
            logger.error(f"Error in start button: {e}")
            await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
    
    async def _start_game(self):
        """Start the Hunger Games with poll participants"""
        try:
            guild_id = self.ctx.guild.id
            
            # Create game instance
            self.cog.active_games[guild_id] = {
                "channel": self.ctx.channel,
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
            for user_id in self.participants:
                member = self.ctx.guild.get_member(user_id)
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
            
            # Send game start message
            await self.ctx.send(f"🎮 **Game starting with {player_count} tributes!**")
            await asyncio.sleep(2)
            
            # Use the cog's method to send game start messages
            if hasattr(self.cog, '_send_game_start_messages'):
                await self.cog._send_game_start_messages(game, player_count)
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.cog.game_loop(guild_id))
            
            logger.info(f"Started Hunger Games via poll with {player_count} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error starting poll game: {e}")
            if guild_id in self.cog.active_games:
                del self.cog.active_games[guild_id]
            await self.ctx.send("❌ Failed to start the game.")
    
    async def on_timeout(self):
        """Handle poll timeout"""
        try:
            if self.game_started:
                return
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            if self.message:
                # Check if we have enough players to start anyway
                if len(self.participants) >= 2:
                    embed = discord.Embed(
                        title="⏰ **POLL TIMED OUT**",
                        description=f"Poll expired but we have {len(self.participants)} players! Starting game...",
                        color=0xFFFF00
                    )
                    await self.message.edit(embed=embed, view=self)
                    await self._start_game()
                else:
                    embed = discord.Embed(
                        title="⏰ **POLL EXPIRED**",
                        description=f"Only {len(self.participants)} player{'s' if len(self.participants) != 1 else ''} joined. Need at least 2 to start.",
                        color=0xFF0000
                    )
                    await self.message.edit(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error handling poll timeout: {e}")
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        """Handle view errors"""
        logger.error(f"Poll view error: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
        except Exception:
            pass
