# onepiecemods.py - Improved Version
import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import json

from redbot.core import commands, checks, modlog, Config
from redbot.core.utils.chat_formatting import humanize_list, box, pagify
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

# Import message data
from .data.kick_messages import KICK_MESSAGES, KICK_GIFS, KICK_ALIASES
from .data.ban_messages import BAN_MESSAGES, BAN_GIFS, BAN_ALIASES
from .data.mute_messages import MUTE_MESSAGES, MUTE_GIFS, MUTE_ALIASES
from .data.warn_messages import WARN_MESSAGES, WARN_GIFS, WARN_ALIASES, BOUNTY_LEVELS, BOUNTY_DESCRIPTIONS
from .data.impel_down import IMPEL_DOWN_LEVELS, IMPEL_DOWN_MESSAGES, IMPEL_DOWN_GIFS

# Import utilities
from .utils.embed_creator import EmbedCreator
from .utils.hierarchy import check_hierarchy, sanitize_reason, format_time_duration

class DurationConverter(commands.Converter):
    """Convert duration strings like 1h30m to seconds"""
    async def convert(self, ctx, argument: str) -> int:
        # Pattern matches: 1d2h3m, 1h30m, 5m, etc.
        pattern = re.compile(
            r'^(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?$'
        )
        match = pattern.match(argument)
        if not match:
            # Try to convert plain number to seconds (assuming minutes)
            try:
                return int(argument) * 60
            except ValueError:
                raise commands.BadArgument(
                    f"Invalid duration format. Use 1d2h3m, 1h30m, 5m, or plain minutes."
                )
        
        # Extract time units
        days = int(match.group('days') or 0)
        hours = int(match.group('hours') or 0)
        minutes = int(match.group('minutes') or 0)
        
        # Ensure at least one unit was provided
        if days == 0 and hours == 0 and minutes == 0:
            raise commands.BadArgument("Duration must be at least 1 minute.")
            
        # Convert to seconds
        total_seconds = days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60
        
        # Enforce Discord's limits (max 1 week timeout)
        max_seconds = 7 * 24 * 60 * 60  # 7 days in seconds
        if total_seconds > max_seconds:
            total_seconds = max_seconds
            await ctx.send(f"⚠️ Duration capped at 7 days to match Discord limits.")
            
        return total_seconds

class OnePieceMods(commands.Cog):
    """One Piece themed moderation commands 🏴‍☠️

    Adds fun One Piece styling to standard moderation actions.
    """
    
    # Updated default settings with new configuration options
    default_guild_settings = {
        "mute_role": None,
        "log_channel": None,
        "warnings": {},
        "active_punishments": {},
        "mod_history": {},
        "warning_cooldown": 30,  # Configurable cooldown in seconds
        "auto_escalation": True,  # Enable/disable automatic escalation
        "max_warning_level": 6,  # Maximum warning level
        "escalation_levels": {  # Configurable escalation thresholds
            3: {"level": 1, "duration": 30},
            5: {"level": 3, "duration": 60},
            7: {"level": 5, "duration": 120}
        },
        "audit_log_format": "One Piece Mods: {moderator} ({moderator_id}) | {reason}",
        "backup_enabled": True,
        "webhook_url": None  # Optional webhook for advanced logging
    }
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("red.onepiecemods")
        self.config = Config.get_conf(self, identifier=502050299, force_registration=True)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_member(roles=[])
        
        # Background task
        self.bg_task = None
        
        # Register the casetypes
        self.init_casetypes_task = asyncio.create_task(self.register_casetypes())
        
    def create_modlog_embed(self, case_num, action_type, user, moderator, reason, timestamp, **kwargs):
        """Create a moderation log embed that mimics Red's style but with One Piece flair"""
        embed = discord.Embed(color=self.get_action_color(action_type))
        
        # Main case information
        embed.title = f"Case #{case_num}"
        
        # Action with color-coded field
        embed.add_field(name="Action:", value=action_type, inline=False)
        
        # User field with mention and ID
        user_text = f"{user.mention} ({user.id})"
        embed.add_field(name="User:", value=user_text, inline=False)
        
        # Moderator field
        embed.add_field(name="Moderator:", value=f"{moderator.mention} ({moderator.id})", inline=False)
        
        # Reason field
        embed.add_field(name="Reason:", value=reason or "No reason provided", inline=False)
        
        # Date field with relative time
        relative_time = f"({self.get_relative_time(timestamp)})"
        date_value = f"{timestamp.strftime('%B %d, %Y %I:%M %p')} {relative_time}"
        embed.add_field(name="Date:", value=date_value, inline=False)
        
        # Add any extra fields from kwargs
        for name, value in kwargs.items():
            if name.lower() not in ["case_num", "action_type", "user", "moderator", "reason", "timestamp"]:
                embed.add_field(name=f"{name}:", value=value, inline=False)
        
        # Set the author with moderator details
        embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        
        # Set footer with One Piece theme
        embed.set_footer(text="One Piece Moderation System", 
                        icon_url="https://i.imgur.com/Wr8xdJA.png")  # One Piece logo
        
        return embed

    def get_action_color(self, action_type):
        """Return color based on action type with One Piece theme colors"""
        colors = {
            "ban": discord.Color.from_rgb(204, 0, 0),         # Shanks red
            "kick": discord.Color.from_rgb(255, 128, 0),      # Luffy orange
            "mute": discord.Color.from_rgb(0, 102, 204),      # Law blue
            "warn": discord.Color.from_rgb(255, 215, 0),      # Bounty gold
            "timeout": discord.Color.from_rgb(102, 0, 153),   # Purple
            "impeldown": discord.Color.from_rgb(51, 51, 51),  # Dark gray
            "unmute": discord.Color.from_rgb(0, 204, 102),    # Green
            "unban": discord.Color.from_rgb(46, 204, 113),    # Green
            "release": discord.Color.from_rgb(46, 204, 113),  # Green
            "impelrelease": discord.Color.from_rgb(46, 204, 113),  # Green
            "bounty": discord.Color.from_rgb(255, 215, 0),    # Gold
        }
        action_type = action_type.lower()
        return colors.get(action_type, discord.Color.light_grey())

    def get_relative_time(self, timestamp):
        """Calculate relative time from timestamp to now"""
        now = datetime.now(timezone.utc)
        delta = now - timestamp
        
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours == 0:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "yesterday"
        else:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
    
    async def format_audit_reason(self, guild, moderator, reason):
        """Format audit log reason according to guild settings"""
        format_template = await self.config.guild(guild).audit_log_format()
        return format_template.format(
            moderator=moderator.display_name,
            moderator_id=moderator.id,
            reason=reason or "No reason provided"
        )
        
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.bg_task:
            self.bg_task.cancel()
        if self.init_casetypes_task:
            self.init_casetypes_task.cancel()
    
    async def register_casetypes(self):
        """Register the custom casetypes for the cog"""
        await modlog.register_casetypes([
            {
                "name": "impeldown",
                "default_setting": True,
                "image": "⛓️",
                "case_str": "Impel Down Imprisonment"
            },
            {
                "name": "impelrelease",
                "default_setting": True,
                "image": "🔓",
                "case_str": "Impel Down Release"
            },
            {
                "name": "bounty",
                "default_setting": True,
                "image": "💰",
                "case_str": "Bounty Increase"
            }
        ])
    
    async def init_task(self):
        """Start background tasks once the bot is ready"""
        await self.bot.wait_until_ready()
        self.bg_task = self.bot.loop.create_task(self.check_expired_punishments())
    
    async def batch_update_punishments(self, guild, updates):
        """Batch update multiple punishments to reduce database calls"""
        async with self.config.guild(guild).active_punishments() as punishments:
            for user_id, update_data in updates.items():
                if update_data is None:
                    punishments.pop(str(user_id), None)
                else:
                    punishments[str(user_id)] = update_data
    
    async def check_expired_punishments(self):
        """Background task to check for expired punishments with improved efficiency"""
        await self.bot.wait_until_ready()
        while True:
            try:
                # Check each guild for expired punishments
                all_guilds = await self.config.all_guilds()
                
                for guild_id, guild_data in all_guilds.items():
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    
                    # Get active punishments
                    active_punishments = guild_data.get("active_punishments", {})
                    expired_punishments = {}
                    
                    current_time = datetime.now().timestamp()
                    
                    for user_id, punishment in active_punishments.items():
                        # Skip if no end time
                        if "end_time" not in punishment:
                            continue
                            
                        # Check if punishment should end
                        end_time = punishment["end_time"]
                        if current_time >= end_time:
                            # Get the member
                            member = guild.get_member(int(user_id))
                            if not member:
                                # Mark for removal if member left
                                expired_punishments[user_id] = None
                                continue
                                
                            # Release the punishment
                            try:
                                await self.release_punishment(guild, member, "Automatic release after sentence completion")
                                expired_punishments[user_id] = None
                            except Exception as e:
                                self.logger.error(f"Error releasing punishment for {user_id}: {e}")
                    
                    # Batch update expired punishments
                    if expired_punishments:
                        await self.batch_update_punishments(guild, expired_punishments)
                        
                # Check every 30 seconds
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in punishment check task: {e}")
                await asyncio.sleep(60)  # Wait longer if error
    
    async def save_roles(self, member):
        """Save member's roles for later restoration"""
        role_ids = [r.id for r in member.roles if not r.is_default()]
        await self.config.member(member).roles.set(role_ids)
    
    async def restore_roles(self, guild, member):
        """Restore member's saved roles"""
        saved_roles = await self.config.member(member).roles()
        if not saved_roles:
            return False
            
        # Get the actual role objects
        to_add = []
        for role_id in saved_roles:
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                to_add.append(role)
                
        if to_add:
            try:
                await member.add_roles(*to_add, reason="Restoring previous roles")
                return True
            except discord.HTTPException:
                return False
        
        return False
    
    async def add_warning(self, guild, user, mod, reason):
        """Add a warning to a user"""
        async with self.config.guild(guild).warnings() as warnings:
            user_id = str(user.id)
            if user_id not in warnings:
                warnings[user_id] = []
                
            warnings[user_id].append({
                "mod_id": mod.id,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })
            
            return len(warnings[user_id])
    
    async def get_warnings(self, guild, user):
        """Get all warnings for a user"""
        warnings = await self.config.guild(guild).warnings()
        user_id = str(user.id)
        return warnings.get(user_id, [])
    
    async def clear_warnings(self, guild, user):
        """Clear all warnings for a user"""
        async with self.config.guild(guild).warnings() as warnings:
            user_id = str(user.id)
            if user_id in warnings:
                warnings[user_id] = []
                return True
        return False
    
    async def add_punishment(self, guild, user, level, duration, mod, reason):
        """Add an active punishment"""
        now = datetime.now().timestamp()
        end_time = now + duration
        
        async with self.config.guild(guild).active_punishments() as punishments:
            punishments[str(user.id)] = {
                "level": level,
                "mod_id": mod.id,
                "reason": reason,
                "start_time": now,
                "end_time": end_time,
                "active": True
            }
    
    async def end_punishment(self, guild, user):
        """End an active punishment"""
        async with self.config.guild(guild).active_punishments() as punishments:
            user_id = str(user.id)
            if user_id in punishments:
                punishment = punishments[user_id]
                del punishments[user_id]
                return punishment
        return None
    
    async def get_active_punishment(self, guild, user):
        """Get active punishment for a user"""
        punishments = await self.config.guild(guild).active_punishments()
        return punishments.get(str(user.id))
    
    async def add_mod_action(self, guild, action_type, mod, user, reason, **kwargs):
        """Add an action to the mod history"""
        async with self.config.guild(guild).mod_history() as history:
            user_id = str(user.id)
            if user_id not in history:
                history[user_id] = []
                
            history[user_id].append({
                "action_type": action_type,
                "mod_id": mod.id,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            })
    
    async def get_user_mod_history(self, guild, user):
        """Get moderation history for a user"""
        history = await self.config.guild(guild).mod_history()
        user_id = str(user.id)
        return history.get(user_id, [])
    
    async def backup_guild_data(self, guild):
        """Create a backup of all guild moderation data"""
        if not await self.config.guild(guild).backup_enabled():
            return None
            
        data = {
            "guild_id": guild.id,
            "timestamp": datetime.now().isoformat(),
            "warnings": await self.config.guild(guild).warnings(),
            "active_punishments": await self.config.guild(guild).active_punishments(),
            "mod_history": await self.config.guild(guild).mod_history()
        }
        
        return data
    
    async def release_punishment(self, guild, member, reason):
        """Release a member from punishment with role restoration"""
        try:
            # Get the punishment data first to avoid race conditions
            punishment = await self.get_active_punishment(guild, member)
            
            if not punishment:
                return False
                
            # End timeout if active
            try:
                await member.timeout(None, reason=await self.format_audit_reason(guild, guild.me, f"Released: {reason}"))
            except discord.HTTPException as e:
                if e.status != 403:  # Ignore permission errors, continue with other steps
                    self.logger.warning(f"Could not remove timeout for {member}: {e}")
            
            # Get guild config
            mute_role_id = await self.config.guild(guild).mute_role()
            
            # Remove mute role if available
            if mute_role_id:
                mute_role = guild.get_role(mute_role_id)
                if mute_role and mute_role in member.roles:
                    try:
                        await member.remove_roles(mute_role, reason=await self.format_audit_reason(guild, guild.me, f"Released: {reason}"))
                    except discord.HTTPException as e:
                        self.logger.warning(f"Could not remove mute role from {member}: {e}")
            
            # For level 3+ punishments, reset channel permissions
            if punishment.get("level", 0) >= 3:
                for channel in guild.channels:
                    try:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            perms = channel.overwrites_for(member)
                            if perms.view_channel is False:
                                await channel.set_permissions(member, overwrite=None, 
                                                          reason=await self.format_audit_reason(guild, guild.me, f"Released from Impel Down: {reason}"))
                    except discord.HTTPException:
                        pass  # Continue with other channels even if one fails
            
            # Restore roles
            await self.restore_roles(guild, member)
            
            # End punishment in Config
            await self.end_punishment(guild, member)
            
            return True
        except Exception as e:
            self.logger.error(f"Error releasing punishment: {e}")
            return False
    
    async def apply_level_restrictions(self, guild, member, level, reason):
        """Apply level-specific restrictions based on Impel Down level"""
        level_data = IMPEL_DOWN_LEVELS.get(level, {})
        restrictions = level_data.get("restrictions", [])
        
        success = True
        
        # Apply channel-specific overrides for higher levels (3+)
        if level >= 3:
            for channel in guild.channels:
                try:
                    if "view_channel" in restrictions:
                        # For text and voice channels: hide them
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            await channel.set_permissions(member, view_channel=False, 
                                                      reason=await self.format_audit_reason(guild, guild.me, f"Impel Down Level {level}"))
                except discord.HTTPException:
                    success = False
        
        return success
    
    async def should_escalate(self, guild, warning_count):
        """Check if a warning should trigger escalation based on guild settings"""
        auto_escalation = await self.config.guild(guild).auto_escalation()
        if not auto_escalation:
            return None, None
            
        escalation_levels = await self.config.guild(guild).escalation_levels()
        
        if str(warning_count) in escalation_levels:
            escalation_data = escalation_levels[str(warning_count)]
            return escalation_data.get("level", 0), escalation_data.get("duration", 0)
            
        return None, None
    
    async def delayed_escalation(self, ctx, member, level, duration, reason, delay=2):
        """Apply escalation after a short delay"""
        await asyncio.sleep(delay)  # Short delay to ensure warning shows first
        await self.impel_down(ctx, member, level, duration, reason)
    
    async def create_history_pages(self, member, history):
        """Create paginated embeds for moderation history"""
        pages = []
        chunk_size = 5
        
        # Count actions by type
        action_counts = {}
        for entry in history:
            action_type = entry.get("action_type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        for i in range(0, len(history), chunk_size):
            chunk = history[i:i + chunk_size]
            
            embed = discord.Embed(
                title=f"Pirate History: {member.name}",
                description=f"Moderation history for {member.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Add action counts on first page only
            if i == 0:
                action_field = ""
                for action, count in action_counts.items():
                    action_name = action.replace("_", " ").title()
                    action_field += f"{action_name}: **{count}**\n"
                    
                embed.add_field(name="Action Summary", value=action_field or "None", inline=False)
            
            # Add chunk of actions
            for j, action in enumerate(chunk, 1):
                action_type = action.get("action_type", "unknown").replace("_", " ").title()
                mod_id = action.get("mod_id", 0)
                mod = member.guild.get_member(int(mod_id))
                mod_name = mod.name if mod else "Unknown"
                
                timestamp = action.get("timestamp", "Unknown")
                if timestamp != "Unknown":
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        timestamp = dt.strftime("%Y-%m-%d")
                    except:
                        pass
                        
                reason = action.get("reason", "No reason provided")
                reason = (reason[:40] + "...") if len(reason) > 40 else reason
                
                embed.add_field(
                    name=f"{i + j}. {action_type} - {timestamp}",
                    value=f"By: {mod_name} • Reason: {reason}",
                    inline=False
                )
            
            # Add page footer
            total_pages = (len(history) + chunk_size - 1) // chunk_size
            current_page = (i // chunk_size) + 1
            embed.set_footer(text=f"Page {current_page}/{total_pages} • Total actions: {len(history)}")
            
            pages.append(embed)
        
        return pages
    
    # Setup Commands
    
    @commands.group(name="onepiecemod", aliases=["opm", "piratemod"])
    @commands.admin_or_permissions(administrator=True)
    async def opm_group(self, ctx):
        """One Piece moderation commands and settings"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="One Piece Moderation",
                description="Use `[p]onepiecemod help` to see all commands and settings.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
    
    @opm_group.command(name="setup")
    async def setup_wizard(self, ctx):
        """Interactive setup wizard for One Piece Mods"""
        embed = discord.Embed(
            title="⚙️ One Piece Mods Setup Wizard",
            description="Let's configure your server for One Piece moderation!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="What we'll set up:",
            value="• Sea Prism Stone (mute) role\n• Marine HQ (log) channel\n• Warning escalation settings\n• Other preferences",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Step 1: Mute Role
        embed = discord.Embed(
            title="Step 1: Sea Prism Stone Role",
            description="Would you like me to create a mute role or use an existing one?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Options:", value="• Type `create` to create a new role\n• Mention an existing role\n• Type `skip` to skip this step", inline=False)
        
        msg = await ctx.send(embed=embed)
        
        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60.0
            )
            
            if response.content.lower() == "create":
                await ctx.invoke(self.set_mute_role)
            elif response.content.lower() != "skip":
                # Try to find mentioned role
                if response.role_mentions:
                    await ctx.invoke(self.set_mute_role, response.role_mentions[0])
                    
        except asyncio.TimeoutError:
            await ctx.send("⏰ Setup wizard timed out. You can run it again anytime!")
            return
        
        # Step 2: Log Channel
        embed = discord.Embed(
            title="Step 2: Marine HQ (Log Channel)",
            description="Where should moderation logs be sent?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Options:", value="• Mention a channel\n• Type `here` for current channel\n• Type `skip` to skip this step", inline=False)
        
        await ctx.send(embed=embed)
        
        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60.0
            )
            
            if response.content.lower() == "here":
                await ctx.invoke(self.set_log_channel)
            elif response.content.lower() != "skip":
                if response.channel_mentions:
                    await ctx.invoke(self.set_log_channel, response.channel_mentions[0])
                    
        except asyncio.TimeoutError:
            await ctx.send("⏰ Setup wizard timed out. Configuration saved so far!")
            return
        
        # Step 3: Auto-escalation
        embed = discord.Embed(
            title="Step 3: Warning Escalation",
            description="Should warnings automatically escalate to Impel Down punishments?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Options:", value="• Type `yes` to enable auto-escalation\n• Type `no` to disable it", inline=False)
        
        await ctx.send(embed=embed)
        
        try:
            response = await self.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                timeout=60.0
            )
            
            if response.content.lower() in ["yes", "y", "enable", "true"]:
                await self.config.guild(ctx.guild).auto_escalation.set(True)
                await ctx.send("✅ Auto-escalation enabled!")
            elif response.content.lower() in ["no", "n", "disable", "false"]:
                await self.config.guild(ctx.guild).auto_escalation.set(False)
                await ctx.send("✅ Auto-escalation disabled!")
                
        except asyncio.TimeoutError:
            pass
        
        # Completion
        embed = discord.Embed(
            title="🎉 Setup Complete!",
            description="One Piece Mods is now configured for your server!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Next steps:",
            value=f"• Use `{ctx.clean_prefix}piratehelp` to see all commands\n• Test the commands with appropriate permissions\n• Customize settings with `{ctx.clean_prefix}opm config`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @opm_group.command(name="config")
    async def config_menu(self, ctx):
        """View and modify configuration settings"""
        guild_config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="⚙️ One Piece Mods Configuration",
            description=f"Settings for {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        # Mute role
        mute_role_id = guild_config.get("mute_role")
        mute_role = ctx.guild.get_role(mute_role_id) if mute_role_id else None
        embed.add_field(
            name="Sea Prism Stone Role",
            value=mute_role.mention if mute_role else "Not set",
            inline=True
        )
        
        # Log channel
        log_channel_id = guild_config.get("log_channel")
        log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
        embed.add_field(
            name="Marine HQ Channel",
            value=log_channel.mention if log_channel else "Not set",
            inline=True
        )
        
        # Auto-escalation
        auto_escalation = guild_config.get("auto_escalation", True)
        embed.add_field(
            name="Auto-Escalation",
            value="✅ Enabled" if auto_escalation else "❌ Disabled",
            inline=True
        )
        
        # Warning cooldown
        warning_cooldown = guild_config.get("warning_cooldown", 30)
        embed.add_field(
            name="Warning Cooldown",
            value=f"{warning_cooldown} seconds",
            inline=True
        )
        
        # Max warning level
        max_warning_level = guild_config.get("max_warning_level", 6)
        embed.add_field(
            name="Max Warning Level",
            value=str(max_warning_level),
            inline=True
        )
        
        # Backup status
        backup_enabled = guild_config.get("backup_enabled", True)
        embed.add_field(
            name="Backup System",
            value="✅ Enabled" if backup_enabled else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="Modify Settings",
            value=f"Use `{ctx.clean_prefix}opm set <setting> <value>` to change settings",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @opm_group.command(name="set")
    async def set_config(self, ctx, setting: str, *, value: str):
        """Set a configuration option
        
        Available settings:
        - warning_cooldown: Time between warnings (seconds)
        - auto_escalation: Enable/disable automatic escalation (true/false)
        - max_warning_level: Maximum warning level (number)
        - backup_enabled: Enable/disable backups (true/false)
        """
        setting = setting.lower()
        
        try:
            if setting == "warning_cooldown":
                cooldown = int(value)
                if cooldown < 5 or cooldown > 3600:
                    return await ctx.send("❌ Warning cooldown must be between 5 and 3600 seconds!")
                await self.config.guild(ctx.guild).warning_cooldown.set(cooldown)
                await ctx.send(f"✅ Warning cooldown set to {cooldown} seconds!")
                
            elif setting == "auto_escalation":
                enabled = value.lower() in ["true", "yes", "1", "enable", "on"]
                await self.config.guild(ctx.guild).auto_escalation.set(enabled)
                status = "enabled" if enabled else "disabled"
                await ctx.send(f"✅ Auto-escalation {status}!")
                
            elif setting == "max_warning_level":
                level = int(value)
                if level < 1 or level > 10:
                    return await ctx.send("❌ Max warning level must be between 1 and 10!")
                await self.config.guild(ctx.guild).max_warning_level.set(level)
                await ctx.send(f"✅ Max warning level set to {level}!")
                
            elif setting == "backup_enabled":
                enabled = value.lower() in ["true", "yes", "1", "enable", "on"]
                await self.config.guild(ctx.guild).backup_enabled.set(enabled)
                status = "enabled" if enabled else "disabled"
                await ctx.send(f"✅ Backup system {status}!")
                
            else:
                await ctx.send(f"❌ Unknown setting: {setting}")
                
        except ValueError:
            await ctx.send("❌ Invalid value for that setting!")
    
    @opm_group.command(name="backup")
    async def backup_data(self, ctx):
        """Create a backup of all moderation data"""
        try:
            backup_data = await self.backup_guild_data(ctx.guild)
            if not backup_data:
                return await ctx.send("❌ Backups are disabled for this server!")
            
            # Convert to JSON and create file
            backup_json = json.dumps(backup_data, indent=2)
            
            # Create file object
            file_content = backup_json.encode('utf-8')
            filename = f"onepiece_backup_{ctx.guild.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            file = discord.File(
                fp=discord.utils._BytesIOLike(file_content),
                filename=filename
            )
            
            embed = discord.Embed(
                title="📦 Backup Created",
                description="Your moderation data has been backed up!",
                color=discord.Color.green()
            )
            embed.add_field(name="Filename", value=filename, inline=False)
            embed.add_field(name="Contains", value="• All warnings\n• Active punishments\n• Moderation history", inline=False)
            
            await ctx.send(embed=embed, file=file)
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            await ctx.send("❌ Failed to create backup!")
    
    @opm_group.command(name="setmuterole", aliases=["seaprismrole"])
    async def set_mute_role(self, ctx, role: discord.Role = None):
        """Set the mute role or create a new one
        
        If no role is specified, a new role will be created with appropriate permissions.
        """
        if role is None:
            # Create a new mute role
            try:
                role = await ctx.guild.create_role(
                    name="Sea Prism Stone",
                    color=discord.Color.dark_gray(),
                    reason="Automatic creation of mute role by One Piece Mods"
                )
                
                # Set permissions for each channel
                success_count = 0
                total_channels = len(ctx.guild.channels)
                
                for channel in ctx.guild.channels:
                    try:
                        if isinstance(channel, discord.TextChannel):
                            await channel.set_permissions(role, send_messages=False, add_reactions=False)
                            success_count += 1
                        elif isinstance(channel, discord.VoiceChannel):
                            await channel.set_permissions(role, speak=False, connect=True)
                            success_count += 1
                    except discord.HTTPException:
                        pass  # Continue with other channels
                
                if success_count < total_channels:
                    await ctx.send(f"⚠️ Warning: Could only set permissions for {success_count}/{total_channels} channels.")
                    
            except discord.HTTPException as e:
                return await ctx.send(f"❌ Failed to create mute role: {e}")
        
        # Update guild config
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        
        embed = discord.Embed(
            title="🔗 Sea Prism Stone Role Set",
            description=f"The Sea Prism Stone role has been set to {role.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Role ID", value=str(role.id), inline=True)
        embed.add_field(name="Members with role", value=str(len(role.members)), inline=True)
        
        await ctx.send(embed=embed)
    
    @opm_group.command(name="setlogchannel", aliases=["marinehq"])
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for moderation logs
        
        If no channel is specified, the current channel will be used.
        """
        if channel is None:
            channel = ctx.channel
            
        # Update guild config
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        
        embed = discord.Embed(
            title="🏛️ Marine HQ Set",
            description=f"Marine HQ reports will now be sent to {channel.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Channel ID", value=str(channel.id), inline=True)
        
        await ctx.send(embed=embed)
    
    @opm_group.command(name="help")
    async def opm_help(self, ctx):
        """Show help for One Piece themed moderation commands"""
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Moderation - Command Manual",
            description="Here are all the commands you can use in this cog!",
            color=discord.Color.blue()
        )
        
        # Setup Commands
        embed.add_field(
            name="🛠️ Setup Commands",
            value=(
                f"`{ctx.clean_prefix}opm setup` - Interactive setup wizard\n"
                f"`{ctx.clean_prefix}opm config` - View current settings\n"
                f"`{ctx.clean_prefix}opm set <setting> <value>` - Change settings\n"
                f"`{ctx.clean_prefix}opm setmuterole [role]` - Set the Sea Prism Stone role\n"
                f"`{ctx.clean_prefix}opm setlogchannel [channel]` - Set the Marine HQ report channel\n"
                f"`{ctx.clean_prefix}opm backup` - Create data backup"
            ),
            inline=False
        )
        
        # Kick Commands
        embed.add_field(
            name="👊 Kick Commands",
            value=(
                f"`{ctx.clean_prefix}luffykick @user [reason]` - Kick a user from the server\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in KICK_ALIASES[:3]])}"
            ),
            inline=False
        )
        
        # Ban Commands
        embed.add_field(
            name="⚔️ Ban Commands",
            value=(
                f"`{ctx.clean_prefix}shanksban @user [reason]` - Ban a user from the server\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in BAN_ALIASES[:3]])}"
            ),
            inline=False
        )
        
        # Mute Commands
        embed.add_field(
            name="🔇 Mute Commands",
            value=(
                f"`{ctx.clean_prefix}lawroom @user <duration> [reason]` - Mute a user for specified duration\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in MUTE_ALIASES[:3]])}"
            ),
            inline=False
        )
        
        # Warning Commands
        embed.add_field(
            name="⚠️ Warning Commands",
            value=(
                f"`{ctx.clean_prefix}bountyset @user [reason]` - Warn a user and increase their bounty\n"
                f"`{ctx.clean_prefix}bountycheck @user` - Check a user's current bounty\n"
                f"`{ctx.clean_prefix}clearbounty @user [reason]` - Clear a user's bounty\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in WARN_ALIASES[:3]])}"
            ),
            inline=False
        )
        
        # Impel Down Commands
        embed.add_field(
            name="🏢 Impel Down Commands",
            value=(
                f"`{ctx.clean_prefix}impeldown @user <level> <duration> [reason]` - Send a user to Impel Down\n"
                f"`{ctx.clean_prefix}liberate @user [reason]` - Release a user from Impel Down\n"
                f"Aliases: `{ctx.clean_prefix}imprison`, `{ctx.clean_prefix}free`, `{ctx.clean_prefix}breakout`"
            ),
            inline=False
        )
        
        # Utility Commands
        embed.add_field(
            name="🔍 Utility Commands",
            value=(
                f"`{ctx.clean_prefix}nakama` - Display server information\n"
                f"`{ctx.clean_prefix}crewhistory @user` - View a user's moderation history\n"
                f"`{ctx.clean_prefix}modstats [days]` - View moderation statistics\n"
                f"`{ctx.clean_prefix}piratehelp` - Display this help message"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Moderation Commands - These wrap around Red's existing commands
    
    @commands.command(name="luffykick", aliases=KICK_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def luffykick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kicks a member from the server with One Piece style!
        
        Examples:
        [p]luffykick @User Disrespecting the captain
        [p]zoroshove @User Breaking server rules
        """
        # Sanitize input
        reason = sanitize_reason(reason)
        
        # Check if person can be kicked
        if member.id == ctx.author.id:
            return await ctx.send("🤔 You can't kick yourself, that's not how Devil Fruits work!")
            
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to kick that user!"):
            return
            
        # Format the kick message
        kick_message = random.choice(KICK_MESSAGES).format(
            user=member.mention, 
            mod=ctx.author.mention
        )
        
        # Get a random GIF
        kick_gif = random.choice(KICK_GIFS)
        
        # Create embed
        embed = EmbedCreator.kick_embed(
            user=member,
            mod=ctx.author,
            reason=reason,
            message=kick_message,
            gif=kick_gif
        )
        
        try:
            # Kick the member using Red's behavior
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, reason)
            await member.kick(reason=audit_reason)
            
            # Get the log channel
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            
            # Create the case in modlog
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="kick",
                user=member,
                moderator=ctx.author,
                reason=reason
            )
            
            # If we have a log channel, send our custom embed
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Kick",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
            
            # Add to mod history
            await self.add_mod_action(
                guild=ctx.guild, 
                action_type="kick", 
                mod=ctx.author, 
                user=member, 
                reason=reason
            )
            
            # Send the fun embed
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick that member!")
        except discord.HTTPException as e:
            if e.status == 400:
                await ctx.send("❌ Cannot kick this user (likely a bot or webhook)!")
            else:
                await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in luffykick: {e}")
            await ctx.send("❌ An unexpected error occurred!")
    
    @commands.command(name="shanksban", aliases=BAN_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def shanksban(self, ctx, member: discord.Member, *, reason: str = None):
        """Bans a member from the server with the power of a Yonko!
        
        Examples:
        [p]shanksban @User Posting inappropriate content
        [p]garpfist @User Raid advertising
        """
        # Sanitize input
        reason = sanitize_reason(reason)
        
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to ban this user!"):
            return
            
        # Format ban message
        ban_message = random.choice(BAN_MESSAGES).format(
            user=member.mention,
            mod=ctx.author.mention
        )
        
        # Get random GIF
        ban_gif = random.choice(BAN_GIFS)
        
        # Create embed
        embed = EmbedCreator.ban_embed(
            user=member,
            mod=ctx.author,
            reason=reason,
            message=ban_message,
            gif=ban_gif
        )
        
        try:
            # Ban the member using Red's behavior
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, reason)
            await member.ban(reason=audit_reason, delete_message_days=0)
            
            # Get the log channel
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            
            # Create the case in modlog
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="ban",
                user=member,
                moderator=ctx.author,
                reason=reason
            )
            
            # If we have a log channel, send our custom embed
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Ban",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
            
            # Add to mod history
            await self.add_mod_action(
                guild=ctx.guild, 
                action_type="ban", 
                mod=ctx.author, 
                user=member, 
                reason=reason
            )
            
            # Send the fun embed
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban that member!")
        except discord.HTTPException as e:
            if e.status == 400:
                await ctx.send("❌ Cannot ban this user!")
            else:
                await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in shanksban: {e}")
            await ctx.send("❌ An unexpected error occurred!")
    
    @commands.command(name="lawroom", aliases=MUTE_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lawroom(self, ctx, member: discord.Member, duration: DurationConverter, *, reason: str = None):
        """Mutes a member for a specified duration
        
        Duration can be specified as:
        - Plain minutes: 30
        - Time format: 1h30m or 2h or 45m or 1d12h
        
        Examples:
        [p]lawroom @User 30 Excessive spam
        [p]lawroom @User 2h30m Arguing with moderators
        [p]seaprism @User 1d Bad behavior
        """
        # Sanitize input
        reason = sanitize_reason(reason)
        
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to mute this user!"):
            return
            
        # Get mute role
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        
        # If no mute role is set, inform the user
        if not mute_role_id:
            return await ctx.send(f"❌ No Sea Prism Stone role set! Use `{ctx.clean_prefix}opm setmuterole` first.")
            
        # Get the mute role
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            return await ctx.send("❌ The Sea Prism Stone role has been deleted. Please set it again.")
            
        # Check if already muted
        if mute_role in member.roles:
            return await ctx.send(f"🔗 {member.mention} is already affected by Sea Prism Stone!")
            
        # Format mute message
        mute_message = random.choice(MUTE_MESSAGES).format(
            user=member.mention,
            mod=ctx.author.mention,
            time=format_time_duration(duration//60)  # Convert seconds to minutes for display
        )
        
        # Get random GIF
        mute_gif = random.choice(MUTE_GIFS)
        
        # Save member's roles for restoring later
        await self.save_roles(member)
        
        # Create embed
        embed = EmbedCreator.mute_embed(
            user=member,
            mod=ctx.author,
            duration=duration//60,  # Convert seconds to minutes for display
            reason=reason,
            message=mute_message,
            gif=mute_gif
        )
        
        try:
            # Add the mute role
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, f"Muted: {reason}")
            await member.add_roles(mute_role, reason=audit_reason)
            
            # Apply timeout if available (Discord feature)
            if ctx.guild.me.guild_permissions.moderate_members:
                until = datetime.now(timezone.utc) + timedelta(seconds=duration)
                try:
                    await member.timeout(until, reason=audit_reason)
                except discord.HTTPException as e:
                    if e.status == 403:
                        await ctx.send("⚠️ Could not apply Discord timeout, but mute role was applied.")
                    elif e.status == 400:
                        await ctx.send("⚠️ Invalid timeout duration, but mute role was applied.")
            
            # Get the log channel
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            
            # Create the case in modlog
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="mute",
                user=member,
                moderator=ctx.author,
                reason=reason
            )
            
            # If we have a log channel, send our custom embed
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Mute",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Duration=format_time_duration(duration//60)
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
            
            # Add to mod history
            await self.add_mod_action(
                guild=ctx.guild, 
                action_type="mute", 
                mod=ctx.author, 
                user=member, 
                reason=reason,
                duration=duration//60  # Convert seconds to minutes
            )
            
            # Add active punishment so it can be automatically ended
            await self.add_punishment(
                guild=ctx.guild,
                user=member,
                level=1,  # Basic mute is level 1
                duration=duration,
                mod=ctx.author,
                reason=reason
            )
            
            # Send the fun embed
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage that member's roles!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Discord API error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in lawroom: {e}")
            await ctx.send("❌ An unexpected error occurred!")
    
    @commands.command(name="bountyset", aliases=WARN_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def bountyset(self, ctx, member: discord.Member, *, reason: str = None):
        """Warn a member, increasing their bounty
        
        Examples:
        [p]bountyset @User Spamming in chat
        [p]bountyraise @User Excessive emoji usage
        [p]marinealert @User Minor rule violation
        """
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to warn this user!"):
            return
        
        # Apply cooldown check based on guild settings
        warning_cooldown = await self.config.guild(ctx.guild).warning_cooldown()
        
        # Create a cooldown key
        cooldown_key = f"warn_{ctx.guild.id}_{ctx.author.id}_{member.id}"
        
        # Check if user is on cooldown
        try:
            bucket = commands.Cooldown(1, warning_cooldown)
            bucket_key = bucket.get_key(ctx)
            
            retry_after = bucket.update_rate_limit(ctx.message.created_at.timestamp())
            if retry_after:
                return await ctx.send(f"⚠️ Please wait {retry_after:.1f} seconds before setting another bounty on {member.mention}.")
        except:
            # Fallback if cooldown system fails
            pass
        
        # Sanitize input
        reason = sanitize_reason(reason)
        
        # Add warning to config
        warning_count = await self.add_warning(
            guild=ctx.guild,
            user=member,
            mod=ctx.author,
            reason=reason
        )
        
        # Get bounty information
        max_level = await self.config.guild(ctx.guild).max_warning_level()
        level = min(warning_count, max_level)
        bounty_level = BOUNTY_LEVELS.get(level, BOUNTY_LEVELS[6])
        bounty_description = BOUNTY_DESCRIPTIONS.get(level, BOUNTY_DESCRIPTIONS[6])
        
        # Format warning message
        warn_message = random.choice(WARN_MESSAGES).format(
            user=member.mention,
            mod=ctx.author.mention,
            level=warning_count
        )
        
        # Get random GIF
        warn_gif = random.choice(WARN_GIFS)
        
        # Create embed
        embed = EmbedCreator.warn_embed(
            user=member,
            mod=ctx.author,
            level=warning_count,
            reason=reason,
            message=warn_message,
            gif=warn_gif,
            bounty_level=bounty_level,
            bounty_description=bounty_description
        )
        
        # Check for escalation
        escalation_level, escalation_duration = await self.should_escalate(ctx.guild, warning_count)
        escalation_message = None
        
        if escalation_level and escalation_duration:
            if warning_count == 3:
                escalation_message = f"⚠️ This pirate has reached bounty level 3! {member.mention} will be sent to Impel Down Level {escalation_level}!"
            elif warning_count == 5:
                escalation_message = f"⚠️⚠️ This pirate has reached bounty level 5! {member.mention} will be sent to Impel Down Level {escalation_level}!"
            elif warning_count >= 7:
                escalation_message = f"⚠️⚠️⚠️ ALERT! This pirate has reached bounty level {warning_count}! {member.mention} will be sent to Impel Down Level {escalation_level}!"
        
        if escalation_message:
            embed.add_field(name="Escalation", value=escalation_message, inline=False)
        
        # Get the log channel
        log_channel_id = await self.config.guild(ctx.guild).log_channel()
        log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
        
        # Create modlog case
        case = await modlog.create_case(
            bot=self.bot,
            guild=ctx.guild,
            created_at=ctx.message.created_at,
            action_type="bounty",
            user=member,
            moderator=ctx.author,
            reason=f"Bounty Level {warning_count}: {reason}"
        )
        
        # If we have a log channel, send our custom embed
        if log_channel:
            log_embed = self.create_modlog_embed(
                case_num=case.case_number,
                action_type="Bounty",
                user=member,
                moderator=ctx.author,
                reason=reason,
                timestamp=ctx.message.created_at,
                **{"Bounty Level": f"Level {warning_count}", "Bounty Amount": bounty_level}
            )
            try:
                await log_channel.send(embed=log_embed)
            except discord.HTTPException as e:
                self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
        
        # Add to mod history
        await self.add_mod_action(
            guild=ctx.guild, 
            action_type="warn", 
            mod=ctx.author, 
            user=member, 
            reason=reason,
            level=warning_count
        )
        
        # Send the warning first
        await ctx.send(embed=embed)
        
        # Apply escalation if needed - with a small delay so warning is shown first
        if escalation_level and escalation_duration:
            # Create a task to handle escalation
            self.bot.loop.create_task(
                self.delayed_escalation(
                    ctx, member, escalation_level, escalation_duration,
                    f"Automatic after warning level {warning_count}: {reason}"
                )
            )
    
    @commands.command(name="impeldown", aliases=["imprison"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def impel_down_cmd(self, ctx, member: discord.Member, level: int, duration: DurationConverter, *, reason: str = None):
        """Send a member to Impel Down prison for a specified level and duration
        
        Level 1-6 determines severity of restrictions:
        1: Crimson Hell - Minor restrictions (10min default)
        2: Wild Beast Hell - Message restrictions (30min default)
        3: Starvation Hell - Channel visibility restricted (1h default)
        4: Burning Hell - Voice chat restricted (2h default)
        5: Freezing Hell - Severe isolation (4h default)
        6: Eternal Hell - Maximum restrictions (12h default)
        
        Duration can be specified as:
        - Plain minutes: 30
        - Time format: 1h30m or 2h or 45m or 1d12h
        
        Examples:
        [p]impeldown @User 1 30 First offense
        [p]impeldown @User 3 1h30m Repeated violations
        [p]impeldown @User 6 5h Severe rule breaking
        """
        await self.impel_down(ctx, member, level, duration // 60, reason)  # Convert seconds to minutes
    
    async def impel_down(self, ctx, member, level, duration, reason=None):
        """Internal method to handle Impel Down imprisonment
        
        Args:
            ctx: Command context
            member: Discord member to imprison
            level: Impel Down level (1-6)
            duration: Duration in minutes
            reason: Optional reason for imprisonment
            
        Raises:
            ValueError: If level is not 1-6
            discord.Forbidden: If bot lacks permissions
            
        Note:
            This method handles role saving, permission changes,
            and automatic release scheduling.
        """
        # Validate level
        if not isinstance(level, int) or level < 1 or level > 6:
            return await ctx.send("❌ Impel Down levels must be a number from 1 to 6!")
            
        # Validate duration
        if not isinstance(duration, int) or duration < 1:
            return await ctx.send("❌ Duration must be a positive number of minutes!")
        
        # Cap duration at 10080 minutes (7 days) to match Discord's limit
        if duration > 10080:
            duration = 10080
            await ctx.send("⚠️ Duration capped at 7 days (10080 minutes) to match Discord limits.")
                
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to imprison this user!"):
            return
            
        # Get level data
        level_data = IMPEL_DOWN_LEVELS.get(level)
        if not level_data:
            return await ctx.send("❌ Invalid Impel Down level!")
            
        # Check for active punishment
        active_punishment = await self.get_active_punishment(ctx.guild, member)
        if active_punishment and active_punishment.get("active", False):
            return await ctx.send(f"❌ {member.mention} is already imprisoned in Impel Down! Use `{ctx.clean_prefix}liberate` to end the current sentence first.")
            
        # Check permissions before proceeding
        if not ctx.me.guild_permissions.manage_roles or not ctx.me.guild_permissions.moderate_members:
            missing = []
            if not ctx.me.guild_permissions.manage_roles:
                missing.append("Manage Roles")
            if not ctx.me.guild_permissions.moderate_members:
                missing.append("Moderate Members")
            return await ctx.send(f"❌ I need the following permissions to use Impel Down: {', '.join(missing)}")
        
        # Sanitize reason
        reason = sanitize_reason(reason)
        
        # Format message
        impel_message = random.choice(IMPEL_DOWN_MESSAGES.get(level, IMPEL_DOWN_MESSAGES[1])).format(
            user=member.mention,
            mod=ctx.author.mention,
            time=duration
        )
        
        # Get random GIF
        impel_gif = random.choice(IMPEL_DOWN_GIFS.get(level, IMPEL_DOWN_GIFS[1]))
        
        # Save member's roles for restoring later
        await self.save_roles(member)
        
        # Create embed
        embed = EmbedCreator.impel_down_embed(
            user=member,
            mod=ctx.author,
            level=level,
            duration=duration,
            reason=reason,
            message=impel_message,
            gif=impel_gif,
            level_data=level_data
        )
        
        # Add to config
        await self.add_punishment(
            guild=ctx.guild,
            user=member,
            level=level,
            duration=duration * 60,  # Convert minutes to seconds
            mod=ctx.author,
            reason=reason
        )
        
        # Add to mod history
        await self.add_mod_action(
            guild=ctx.guild, 
            action_type="impeldown", 
            mod=ctx.author, 
            user=member, 
            reason=reason,
            duration=duration,
            level=level
        )
        
        try:
            # Apply timeout if available (Discord feature)
            timeout_until = datetime.now(timezone.utc) + timedelta(minutes=min(duration, 10080))
            audit_reason = await self.format_audit_reason(ctx.guild, ctx.author, f"Impel Down Level {level}: {reason}")
            
            try:
                await member.timeout(timeout_until, reason=audit_reason)
            except discord.HTTPException as e:
                if e.status == 403:
                    await ctx.send("⚠️ I don't have permission to timeout this member!")
                elif e.status == 400:
                    await ctx.send("⚠️ Invalid timeout duration!")
                else:
                    await ctx.send(f"⚠️ Could not apply Discord timeout: {e}")
            
            # Get mute role ID
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            
            # Apply mute role if available
            if mute_role_id:
                mute_role = ctx.guild.get_role(mute_role_id)
                if mute_role:
                    try:
                        await member.add_roles(mute_role, reason=audit_reason)
                    except discord.HTTPException as e:
                        await ctx.send(f"⚠️ Could not apply mute role: {e}")
            
            # Apply additional level-specific restrictions
            success = await self.apply_level_restrictions(ctx.guild, member, level, reason)
            
            if not success:
                await ctx.send("⚠️ Warning: Could not apply all restrictions. The punishment may not be fully effective.")
            
            # Get the log channel
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            
            # Create modlog case
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="impeldown",
                user=member,
                moderator=ctx.author,
                reason=f"Impel Down Level {level}: {reason}"
            )
            
            # If we have a log channel, send our custom embed
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelDown",
                    user=member,
                    moderator=ctx.author,
                    reason=f"Level {level}: {reason}",
                    timestamp=ctx.message.created_at,
                    Duration=f"{duration} minutes",
                    Level=f"Level {level}"
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
            
            # Send the embed
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to apply Impel Down restrictions!")
        except Exception as e:
            self.logger.error(f"Unexpected error in impel_down: {e}")
            await ctx.send("❌ An unexpected error occurred!")
    
    @commands.command(name="liberate", aliases=["free", "breakout"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
    async def release_command(self, ctx, member: discord.Member, *, reason: str = None):
        """Release a member from Impel Down before their sentence is complete
        
        Examples:
        [p]liberate @User Good behavior
        [p]free @User Sentence reduced
        [p]breakout @User Impel Down jailbreak
        """
        # Sanitize reason
        reason = sanitize_reason(reason)
        
        # Check for active punishment
        punishment = await self.get_active_punishment(ctx.guild, member)
        if not punishment or not punishment.get("active", False):
            return await ctx.send(f"❌ {member.mention} is not currently imprisoned in Impel Down!")
            
        try:
            # Release the punishment
            success = await self.release_punishment(ctx.guild, member, f"Released by {ctx.author}: {reason}")
            
            if not success:
                return await ctx.send("❌ Failed to release the prisoner. The Sea Prism Stone is too strong!")
            
            # Create release embed
            embed = discord.Embed(
                title="🔓 Jailbreak! Released from Impel Down!",
                description=f"{member.mention} has been released from Impel Down by {ctx.author.mention}!",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Prison Level", value=f"Level {punishment.get('level', 'Unknown')}", inline=True)
            embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
            embed.add_field(name="Roles", value="Previous roles have been restored.", inline=False)
            embed.set_image(url="https://media.giphy.com/media/PBAl9H8B5Hali/giphy.gif")  # Prison break gif
            embed.set_footer(text="One Piece Moderation - Early Release")
            
            # Get the log channel
            log_channel_id = await self.config.guild(ctx.guild).log_channel()
            log_channel = ctx.guild.get_channel(log_channel_id) if log_channel_id else None
            
            # Create modlog case
            case = await modlog.create_case(
                bot=self.bot,
                guild=ctx.guild,
                created_at=ctx.message.created_at,
                action_type="impelrelease",
                user=member,
                moderator=ctx.author,
                reason=reason
            )
            
            # If we have a log channel, send our custom embed
            if log_channel:
                log_embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelRelease",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Previous_Level=f"Level {punishment.get('level', 'Unknown')}"
                )
                try:
                    await log_channel.send(embed=log_embed)
                except discord.HTTPException as e:
                    self.logger.warning(f"Could not send log to channel {log_channel.id}: {e}")
            
            # Add to mod history
            await self.add_mod_action(
                guild=ctx.guild, 
                action_type="impeldown_release", 
                mod=ctx.author, 
                user=member, 
                reason=reason
            )
            
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to release this member!")
        except Exception as e:
            self.logger.error(f"Unexpected error in release_command: {e}")
            await ctx.send("❌ An unexpected error occurred!")
    
    @commands.command(name="clearbounty", aliases=["forgive", "pardon"])
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def clearbounty(self, ctx, member: discord.Member, *, reason: str = None):
        """Clear a member's bounty/warnings
        
        Examples:
        [p]clearbounty @User Redemption
        [p]forgive @User Has shown improvement
        [p]pardon @User Marine agreement
        """
        # Sanitize reason
        reason = sanitize_reason(reason)
        
        # Get warnings
        warnings = await self.get_warnings(ctx.guild, member)
        
        if not warnings:
            return await ctx.send(f"💰 {member.mention} doesn't have a bounty to clear!")
            
        # Get current warning count
        previous_level = len(warnings)
        
        # Clear warnings
        await self.clear_warnings(ctx.guild, member)
        
        # Create embed
        embed = discord.Embed(
            title="💚 Bounty Cleared!",
            description=f"Fleet Admiral {ctx.author.mention} has pardoned {member.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Previous Bounty Level", value=f"Level {previous_level}", inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=True)
        
        # Set a thumbnail
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Set a pardon image
        embed.set_image(url="https://media.giphy.com/media/xT5LMHxhOfscxPfIfm/giphy.gif")  # Pardon gif
        
        # Create modlog case
        case = await modlog.create_case(
            bot=self.bot,
            guild=ctx.guild,
            created_at=ctx.message.created_at,
            action_type="bounty",
            user=member,
            moderator=ctx.author,
            reason=f"Bounty Cleared: {reason}"
        )
        
        # Add to mod history
        await self.add_mod_action(
            guild=ctx.guild, 
            action_type="clear_warnings", 
            mod=ctx.author, 
            user=member, 
            reason=reason
        )
        
        await ctx.send(embed=embed)
    
    # Utility Commands
    
    @commands.command(name="bountycheck", aliases=["checkbounty", "bountyc"])
    @commands.guild_only()
    async def bountycheck(self, ctx, member: discord.Member = None):
        """Check a member's current bounty/warning level
        
        Examples:
        [p]bountycheck @User
        [p]bounty @User
        [p]checkbounty
        """
        if member is None:
            member = ctx.author
        
        # Get warnings
        warnings = await self.get_warnings(ctx.guild, member)
        
        # Get warning count
        warning_count = len(warnings)
        
        # Create bounty embed with One Piece styling
        if warning_count == 0:
            title = "No Bounty Found"
            color = discord.Color.green()
            description = f"{member.mention} doesn't have a bounty yet. They're not on the World Government's radar."
            image_url = "https://i.imgur.com/7lCkYHj.png"  # Image of a blank wanted poster
        else:
            title = "💰 Bounty Poster"
            color = discord.Color.gold()
            
            # Get bounty level based on warning count
            max_level = await self.config.guild(ctx.guild).max_warning_level()
            level = min(warning_count, max_level)
            bounty_level = BOUNTY_LEVELS.get(level, BOUNTY_LEVELS[6])
            bounty_description = BOUNTY_DESCRIPTIONS.get(level, BOUNTY_DESCRIPTIONS[6])
            
            description = f"{member.mention} has a bounty of **{bounty_level}**!"
            description += f"\nThreat Level: **{bounty_description}**"
            
            image_url = "https://i.imgur.com/9tZpqR6.jpg"  # Image of a wanted poster
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        # Add warning details if there are any
        if warning_count > 0:
            # Show only the 5 most recent warnings
            recent_warnings = warnings[-5:] if len(warnings) > 5 else warnings
            
            for i, warning in enumerate(recent_warnings, 1):
                mod_id = warning.get("mod_id", "0")
                mod = ctx.guild.get_member(int(mod_id)) if mod_id else None
                mod_name = mod.name if mod else "Unknown Moderator"
                
                timestamp = warning.get("timestamp", "Unknown")
                if timestamp != "Unknown":
                    try:
                        # Parse the ISO timestamp
                        dt = datetime.fromisoformat(timestamp)
                        # Format as a more readable timestamp
                        timestamp = dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        pass  # Keep original if parsing fails
                
                embed.add_field(
                    name=f"Warning #{warning_count - len(recent_warnings) + i}",
                    value=f"**Reported by:** {mod_name}\n**Reason:** {warning.get('reason', 'No reason provided')}\n**Date:** {timestamp}",
                    inline=False
                )
            
            if warning_count > 5:
                embed.add_field(
                    name="Note",
                    value=f"Showing 5 most recent warnings. Total warnings: {warning_count}",
                    inline=False
                )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=image_url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="crewhistory", aliases=["history", "mlogs"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    async def crewhistory(self, ctx, member: discord.Member):
        """View a member's moderation history with pagination
        
        Examples:
        [p]crewhistory @User
        [p]history @User
        [p]modlogs @User
        """
        
        # Get moderation history
        history = await self.get_user_mod_history(ctx.guild, member)
        
        if not history:
            return await ctx.send(f"📜 {member.mention} has no moderation history!")
        
        # Create paginated history
        pages = await self.create_history_pages(member, history)
        
        if len(pages) > 1:
            await menu(ctx, pages, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=pages[0])
    
    @commands.command(name="modstats", aliases=["stats"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    async def modstats(self, ctx, days: int = 30):
        """View moderation statistics for the server
        
        Examples:
        [p]modstats
        [p]modstats 7
        [p]stats 14
        """
        if days < 1 or days > 365:
            return await ctx.send("❌ Days must be between 1 and 365!")
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all mod history
        all_history = await self.config.guild(ctx.guild).mod_history()
        
        # Count actions within the time period
        action_counts = {}
        moderator_counts = {}
        recent_actions = 0
        
        for user_id, user_history in all_history.items():
            for action in user_history:
                try:
                    action_date = datetime.fromisoformat(action.get("timestamp", ""))
                    if action_date >= cutoff_date:
                        action_type = action.get("action_type", "unknown")
                        mod_id = action.get("mod_id", 0)
                        
                        action_counts[action_type] = action_counts.get(action_type, 0) + 1
                        moderator_counts[mod_id] = moderator_counts.get(mod_id, 0) + 1
                        recent_actions += 1
                except (ValueError, TypeError):
                    continue
        
        # Get active punishments
        active_punishments = await self.config.guild(ctx.guild).active_punishments()
        active_count = len(active_punishments)
        
        # Create stats embed
        embed = discord.Embed(
            title=f"📊 Moderation Statistics ({days} days)",
            description=f"Statistics for {ctx.guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Total actions
        embed.add_field(name="Total Actions", value=str(recent_actions), inline=True)
        embed.add_field(name="Active Punishments", value=str(active_count), inline=True)
        embed.add_field(name="Average per Day", value=f"{recent_actions/days:.1f}", inline=True)
        
        # Action breakdown
        if action_counts:
            action_text = ""
            for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
                action_name = action.replace("_", " ").title()
                action_text += f"**{action_name}:** {count}\n"
            embed.add_field(name="Action Breakdown", value=action_text or "None", inline=False)
        
        # Top moderators
        if moderator_counts:
            mod_text = ""
            sorted_mods = sorted(moderator_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for mod_id, count in sorted_mods:
                mod = ctx.guild.get_member(int(mod_id))
                mod_name = mod.name if mod else "Unknown"
                mod_text += f"**{mod_name}:** {count}\n"
            embed.add_field(name="Top Moderators", value=mod_text or "None", inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="nakama", aliases=["crewinfo", "shipinfo"])
    @commands.guild_only()
    async def nakama(self, ctx):
        """Display information about the server in One Piece style
        
        Examples:
        [p]nakama
        [p]crewinfo
        [p]shipinfo
        """
        guild = ctx.guild
        
        # Count bot and human members
        humans = len([m for m in guild.members if not m.bot])
        bots = len([m for m in guild.members if m.bot])
        
        # Get channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        
        # Create embed
        embed = discord.Embed(
            title=f"🏴‍☠️ The {guild.name} Pirate Crew",
            description=guild.description or "A crew sailing the Grand Line!",
            color=discord.Color.blue()
        )
        
        # Set server icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        # Basic info
        embed.add_field(name="👑 Captain", value=guild.owner.mention, inline=True)
        embed.add_field(name="🗓️ Voyage Began", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        
        # Member info
        embed.add_field(name="👥 Crew Size", value=f"{guild.member_count} members", inline=True)
        embed.add_field(name="🏴‍☠️ Human Nakama", value=f"{humans} pirates", inline=True)
        embed.add_field(name="🐌 Den Den Mushi", value=f"{bots} snails", inline=True)
        
        # Channel info
        embed.add_field(name="🏛️ Ship Areas", value=f"{len(guild.categories)} sections", inline=True)
        embed.add_field(name="💬 Meeting Rooms", value=f"{text_channels} text channels", inline=True)
        embed.add_field(name="🔊 Voice Spots", value=f"{voice_channels} voice channels", inline=True)
        
        # Server features
        if guild.premium_subscription_count > 0:
            embed.add_field(
                name="⭐ Ship Upgrades", 
                value=f"Level {guild.premium_tier} (Boosted by {guild.premium_subscription_count} nakama)",
                inline=False
            )
        
        # Moderation info
        mute_role_id = await self.config.guild(guild).mute_role()
        log_channel_id = await self.config.guild(guild).log_channel()
        
        mod_info = ""
        if mute_role_id:
            mute_role = guild.get_role(mute_role_id)
            mod_info += f"🔗 Sea Prism Stone: {mute_role.mention if mute_role else 'Deleted'}\n"
        if log_channel_id:
            log_channel = guild.get_channel(log_channel_id)
            mod_info += f"🏛️ Marine HQ: {log_channel.mention if log_channel else 'Deleted'}\n"
            
        if mod_info:
            embed.add_field(name="🛡️ Moderation Setup", value=mod_info, inline=False)
            
        # Set footer
        embed.set_footer(text=f"Ship ID: {guild.id} • Requested by {ctx.author}")
        
        await ctx.send(embed=embed)
            
    @commands.command(name="piratehelp", aliases=["crewhelp", "shiphelp", "opmhelp"])
    async def piratehelp(self, ctx, command_name: str = None):
        """Display help for One Piece moderation commands
        
        Use [p]piratehelp <command> for details on a specific command
        Example: [p]piratehelp luffykick
        """
        if command_name:
            # Get the specific command
            command = None
            for cmd in self.bot.commands:
                if cmd.name == command_name or command_name in getattr(cmd, 'aliases', []):
                    if cmd.cog and cmd.cog == self:
                        command = cmd
                        break
                    
            if not command:
                return await ctx.send(f"❌ Command `{command_name}` not found in the One Piece moderation cog.")
                
            # Create detailed help for the specific command
            embed = discord.Embed(
                title=f"🏴‍☠️ Command: {ctx.clean_prefix}{command.name}",
                description=command.help or "No description available",
                color=discord.Color.blue()
            )
            
            # Add signature
            params = command.clean_params
            if params:
                signature = f"{ctx.clean_prefix}{command.name} "
                for name, param in params.items():
                    if param.default != param.empty:
                        signature += f"[{name}] "
                    else:
                        signature += f"<{name}> "
                embed.add_field(name="Usage", value=f"`{signature.strip()}`", inline=False)
            
            # Add aliases
            if command.aliases:
                embed.add_field(
                    name="Aliases", 
                    value=", ".join([f"`{ctx.clean_prefix}{alias}`" for alias in command.aliases]),
                    inline=False
                )
            
            # Add cooldown info
            if hasattr(command, '_buckets') and command._buckets:
                bucket = command._buckets._cooldown
                embed.add_field(
                    name="Cooldown",
                    value=f"{bucket.rate} use{'s' if bucket.rate != 1 else ''} per {bucket.per} second{'s' if bucket.per != 1 else ''}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
            return
        
        # Otherwise, display the opm_help command's output
        await ctx.invoke(self.opm_help)

    # Error Handling with improved specificity
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle common errors for this cog with improved error messages"""
        # Ignore errors that have already been handled
        if getattr(ctx, "handled", False):
            return
            
        # Only handle errors for commands from this cog
        if not ctx.command or ctx.command.cog != self:
            return
            
        ctx.handled = True
            
        if isinstance(error, commands.MissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(f"⚔️ Your Haki isn't strong enough! You need: **{missing_perms}**")
            
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await ctx.send(f"❌ I need more power! Missing permissions: **{missing_perms}**")
            
        elif isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after)
            await ctx.send(f"⏰ Justice is swift but not that swift! Try again in **{remaining}** seconds.")
            
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid input: {str(error)}")
            
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ That pirate couldn't be found on this ship!")
            
        elif isinstance(error, commands.UserInputError):
            await ctx.send(f"❌ Invalid input: {str(error)}")
            
        elif isinstance(error, commands.CommandInvokeError):
            original_error = error.original
            
            if isinstance(original_error, discord.Forbidden):
                await ctx.send("❌ I don't have permission to do that!")
            elif isinstance(original_error, discord.HTTPException):
                if original_error.status == 400:
                    await ctx.send("❌ Invalid request to Discord!")
                elif original_error.status == 429:
                    await ctx.send("❌ Rate limited! Please try again later.")
                else:
                    await ctx.send(f"❌ Discord API error: {original_error}")
            else:
                self.logger.error(f"Unexpected error in {ctx.command.name}: {original_error}")
                await ctx.send("❌ An unexpected error occurred! Check the logs.")
        
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command!")
            
        else:
            self.logger.error(f"Unhandled error in {ctx.command.name if ctx.command else 'unknown'}: {error}")
            await ctx.send("❌ Something went wrong! Please contact an administrator.")
