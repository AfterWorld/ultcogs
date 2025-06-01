# poll_view.py - Poll system for Hunger Games
"""
Poll system for initiating Hunger Games battles
Similar to mafia cog but adapted for HG mechanics
"""

import discord
import asyncio
import logging
from typing import Dict, List, Optional, Set
from redbot.core import commands
from .constants import POLL_EMOJIS, EMOJIS
from .utils import get_random_player_title, get_random_district

logger = logging.getLogger(__name__)

class PollView(discord.ui.View):
    """Interactive poll view for starting Hunger Games"""
    
    def __init__(self, cog, threshold: int, timeout: int = 600):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.threshold = threshold
        self.players: Set[int] = set()  # Set of user IDs who joined
        self.message: Optional[discord.Message] = None
        self.ctx: Optional[commands.Context] = None
        self.game_started = False
        
    async def start(self, ctx: commands.Context) -> None:
        """Start the poll"""
        self.ctx = ctx
        
        # Get role to ping
        poll_ping_role_id = await self.cog.config.guild(ctx.guild).poll_ping_role()
        role_mention = ""
        if poll_ping_role_id:
            role = ctx.guild.get_role(poll_ping_role_id)
            if role:
                role_mention = f"{role.mention} "
        
        # Send ping message if role is set
        if role_mention:
            await ctx.send(f"{role_mention}🗳️ **Hunger Games Poll Starting!**")
        
        embed = self._create_poll_embed()
        self.message = await ctx.send(embed=embed, view=self)
    
    def _create_poll_embed(self) -> discord.Embed:
        """Create the poll embed"""
        # Determine color based on progress
        if len(self.players) >= self.threshold:
            color = 0x00FF00  # Green when ready
        elif len(self.players) >= self.threshold * 0.7:
            color = 0xFFFF00  # Yellow when close
        else:
            color = 0x4169E1  # Blue when starting
        
        embed = discord.Embed(
            title="🗳️ **HUNGER GAMES POLL** 🗳️", 
            color=color
        )
        
        description = f"**A battle royale is being proposed!**\n\n"
        
        # Progress bar visual
        progress = len(self.players) / self.threshold
        filled_bars = int(progress * 10)
        empty_bars = 10 - filled_bars
        progress_bar = "█" * filled_bars + "░" * empty_bars
        
        description += (
            f"🎯 **Required Players:** {self.threshold}\n"
            f"👥 **Current Players:** {len(self.players)}\n"
            f"📊 **Progress:** `{progress_bar}` {len(self.players)}/{self.threshold}\n\n"
        )
        
        if len(self.players) >= self.threshold:
            description += "✅ **Ready to start!** Click the Start Game button below!\n"
        else:
            needed = self.threshold - len(self.players)
            description += f"⏳ **Need {needed} more player{'s' if needed != 1 else ''} to start**\n"
        
        embed.description = description
        
        # Show current players if any
        if self.players and self.ctx:
            player_names = []
            for user_id in list(self.players)[:8]:  # Show max 8 names
                member = self.ctx.guild.get_member(user_id)
                if member:
                    player_names.append(f"🏹 {member.display_name}")
            
            if player_names:
                players_text = "\n".join(player_names)
                if len(self.players) > 8:
                    players_text += f"\n*... and {len(self.players) - 8} more*"
                
                embed.add_field(
                    name="**Joined Tributes**",
                    value=players_text,
                    inline=False
                )
        
        embed.set_footer(
            text="⏰ Poll expires in 10 minutes • Use buttons below to join/leave"
        )
        return embed
    
    @discord.ui.button(label="Join Poll", emoji="✅", style=discord.ButtonStyle.green, row=0)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle join button press"""
        await interaction.response.defer()
        
        # Validation checks
        error_message = await self._validate_user_can_join(interaction.user)
        if error_message:
            await interaction.followup.send(error_message, ephemeral=True)
            return
        
        # Add player
        if interaction.user.id not in self.players:
            self.players.add(interaction.user.id)
            
            # Update embed
            embed = self._create_poll_embed()
            await self._safe_edit_message(embed=embed, view=self)
            
            await interaction.followup.send(
                f"✅ {interaction.user.mention} joined the Hunger Games poll!", 
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ You're already in the poll!", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Leave Poll", emoji="❌", style=discord.ButtonStyle.red, row=0)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle leave button press"""
        await interaction.response.defer()
        
        if interaction.user.id in self.players:
            self.players.remove(interaction.user.id)
            
            # Update embed
            embed = self._create_poll_embed()
            await self._safe_edit_message(embed=embed, view=self)
            
            await interaction.followup.send(
                f"❌ {interaction.user.mention} left the Hunger Games poll!", 
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ You're not in the poll!", 
                ephemeral=True
            )
    
    @discord.ui.button(label="Start Game", emoji="🎮", style=discord.ButtonStyle.primary, row=1)
    async def start_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle start game button press"""
        await interaction.response.defer()
        
        # Check permissions
        if not (interaction.user.guild_permissions.manage_guild or 
                interaction.user.id in self.players):
            await interaction.followup.send(
                "❌ Only participants or admins can start the game!", 
                ephemeral=True
            )
            return
        
        # Check threshold
        if len(self.players) < self.threshold:
            await interaction.followup.send(
                f"❌ Need at least {self.threshold} players to start! "
                f"Currently have {len(self.players)}.", 
                ephemeral=True
            )
            return
        
        # Check if game already active
        if self.ctx.guild.id in self.cog.active_games:
            await interaction.followup.send(
                "❌ A Hunger Games is already active in this server!", 
                ephemeral=True
            )
            return
        
        # Start the game
        await self._start_hunger_games(interaction)
    
    async def _validate_user_can_join(self, user: discord.Member) -> Optional[str]:
        """Validate if user can join the poll"""
        try:
            # Check blacklisted roles
            blacklisted_roles = await self.cog.config.guild(user.guild).blacklisted_roles()
            if any(user.get_role(role_id) for role_id in blacklisted_roles):
                return "❌ You aren't allowed to join Hunger Games in this server due to your roles!"
            
            # Check temporary ban
            temp_banned_until = await self.cog.config.member(user).temp_banned_until()
            if temp_banned_until is not None:
                from datetime import datetime, timezone
                if datetime.now(timezone.utc).timestamp() < temp_banned_until:
                    remaining = temp_banned_until - datetime.now(timezone.utc).timestamp()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    return f"❌ You are temporarily banned for {hours}h {minutes}m!"
            
            # Check if already in another game
            for guild_id, game in self.cog.active_games.items():
                if str(user.id) in game.get("players", {}):
                    guild_name = self.cog.bot.get_guild(guild_id)
                    guild_name = guild_name.name if guild_name else "another server"
                    return f"❌ You're already in a Hunger Games in {guild_name}!"
            
            return None  # All checks passed
            
        except Exception as e:
            logger.error(f"Error validating user {user.id}: {e}")
            return "❌ Error checking your eligibility. Please try again."
    
    async def _start_hunger_games(self, interaction: discord.Interaction):
        """Start the actual Hunger Games with poll participants"""
        try:
            self.game_started = True
            
            # Create game instance
            guild_id = self.ctx.guild.id
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
            
            # Add all poll participants as players
            for user_id in self.players:
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
            
            # Disable the view
            for item in self.children:
                item.disabled = True
            
            # Update message to show game starting
            embed = discord.Embed(
                title="🎮 **GAME STARTING!** 🎮",
                description=f"✅ **{len(self.players)} tributes** are entering the arena!\n\n"
                           f"The Hunger Games will begin shortly...",
                color=0x00FF00
            )
            
            await self._safe_edit_message(embed=embed, view=self)
            await interaction.followup.send(
                "🎮 **Game starting!** Get ready for battle!", 
                ephemeral=True
            )
            
            # Start the game after a brief pause
            await asyncio.sleep(3)
            await self.cog._send_game_start_messages(game, len(self.players))
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.cog.game_loop(guild_id))
            
            logger.info(f"Started Hunger Games via poll with {len(self.players)} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error starting Hunger Games from poll: {e}")
            
            # Clean up on error
            if guild_id in self.cog.active_games:
                del self.cog.active_games[guild_id]
            
            await interaction.followup.send(
                "❌ Failed to start the game. Please try again.", 
                ephemeral=True
            )
    
    async def _safe_edit_message(self, **kwargs):
        """Safely edit the message with error handling"""
        try:
            if self.message:
                await self.message.edit(**kwargs)
        except discord.HTTPException as e:
            logger.warning(f"Failed to edit poll message: {e}")
    
    async def on_timeout(self):
        """Handle view timeout"""
        if not self.game_started:
            try:
                # Disable all buttons
                for item in self.children:
                    item.disabled = True
                
                embed = discord.Embed(
                    title="⏰ **POLL EXPIRED** ⏰",
                    description="The poll has timed out. Start a new poll to try again!",
                    color=0x808080
                )
                
                await self._safe_edit_message(embed=embed, view=self)
                
            except Exception as e:
                logger.error(f"Error handling poll timeout: {e}")
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        """Handle view errors"""
        logger.error(f"Poll view error: {error}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again.", 
                    ephemeral=True
                )
        except Exception:
            pass
