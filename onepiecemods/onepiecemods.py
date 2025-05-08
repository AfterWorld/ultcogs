# onepiecemods.py
import discord
from discord.ext import commands
import asyncio
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
import logging

from redbot.core import commands, checks, modlog, Config
from redbot.core.utils.chat_formatting import humanize_list, box
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
    
    default_guild_settings = {
        "mute_role": None,
        "log_channel": None,
        "warnings": {},
        "active_punishments": {},
        "mod_history": {}
    }
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("red.onepiecemods")
        self.config = Config.get_conf(self, identifier=502050299, force_registration=True)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_member(roles=[])
        
        # We'll use an asyncio task to check for expired punishments
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
    
    async def check_expired_punishments(self):
        """Background task to check for expired punishments"""
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
                    for user_id, punishment in active_punishments.items():
                        # Skip if no end time
                        if "end_time" not in punishment:
                            continue
                            
                        # Check if punishment should end
                        end_time = punishment["end_time"]
                        if datetime.now().timestamp() >= end_time:
                            # Get the member
                            member = guild.get_member(int(user_id))
                            if not member:
                                # Remove punishment if member left
                                async with self.config.guild(guild).active_punishments() as punishments:
                                    if user_id in punishments:
                                        del punishments[user_id]
                                continue
                                
                            # Release the punishment
                            await self.release_punishment(guild, member, "Automatic release after sentence completion")
                            
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
    
    async def release_punishment(self, guild, member, reason):
        """Release a member from punishment with role restoration"""
        try:
            # End timeout if active
            await member.timeout(None, reason=f"Released: {reason}")
            
            # Get guild config
            mute_role_id = await self.config.guild(guild).mute_role()
            
            # Remove mute role if available
            if mute_role_id:
                mute_role = guild.get_role(mute_role_id)
                if mute_role and mute_role in member.roles:
                    await member.remove_roles(mute_role, reason=f"Released: {reason}")
            
            # Get the punishment data to check level
            punishment = await self.get_active_punishment(guild, member)
            if punishment and punishment.get("level", 0) >= 3:
                # For level 3+ punishments, reset channel permissions
                for channel in guild.channels:
                    try:
                        if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                            perms = channel.overwrites_for(member)
                            if perms.view_channel is False:  # Only modify if explicit override exists
                                await channel.set_permissions(member, overwrite=None, 
                                                          reason=f"Released from Impel Down: {reason}")
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
                                                      reason=f"Impel Down Level {level}")
                except discord.HTTPException:
                    success = False
        
        return success
    
    async def delayed_escalation(self, ctx, member, level, duration, reason, delay=2):
        """Apply escalation after a short delay"""
        await asyncio.sleep(delay)  # Short delay to ensure warning shows first
        await self.impel_down(ctx, member, level, duration, reason)
        
    
    
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
    
    @opm_group.command(name="setmuterole", aliases=["seaprismrole"])
    async def set_mute_role(self, ctx, role: discord.Role = None):
        """Set the mute role or create a new one
        
        If no role is specified, a new role will be created with appropriate permissions.
        """
        if role is None:
            # Create a new mute role
            role = await ctx.guild.create_role(
                name="Sea Prism Stone",
                color=discord.Color.dark_gray(),
                reason="Automatic creation of mute role"
            )
            
            # Set permissions for each channel
            for channel in ctx.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(role, send_messages=False, add_reactions=False)
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(role, speak=False, connect=True)
        
        # Update guild config
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        
        embed = discord.Embed(
            title="Sea Prism Stone Role Set",
            description=f"The Sea Prism Stone role has been set to {role.mention}!",
            color=discord.Color.green()
        )
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
            title="Marine HQ Set",
            description=f"Marine HQ reports will now be sent to {channel.mention}!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @opm_group.command(name="help")
    async def opm_help(self, ctx):
        """Show help for One Piece themed moderation commands"""
        embed = discord.Embed(
            title="One Piece Moderation - Command Manual",
            description="Here are all the commands you can use in this cog!",
            color=discord.Color.blue()
        )
        
        # Setup Commands
        embed.add_field(
            name="🛠️ Setup Commands",
            value=(
                f"`{ctx.clean_prefix}onepiecemod setmuterole [role]` - Set the Sea Prism Stone role\n"
                f"`{ctx.clean_prefix}onepiecemod setlogchannel [channel]` - Set the Marine HQ report channel"
            ),
            inline=False
        )
        
        # Kick Commands
        embed.add_field(
            name="👊 Kick Commands",
            value=(
                f"`{ctx.clean_prefix}luffykick @user [reason]` - Kick a user from the server\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in KICK_ALIASES])}"
            ),
            inline=False
        )
        
        # Ban Commands
        embed.add_field(
            name="⚔️ Ban Commands",
            value=(
                f"`{ctx.clean_prefix}shanksban @user [reason]` - Ban a user from the server\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in BAN_ALIASES])}"
            ),
            inline=False
        )
        
        # Mute Commands
        embed.add_field(
            name="🔇 Mute Commands",
            value=(
                f"`{ctx.clean_prefix}lawroom @user [duration] [reason]` - Mute a user for specified duration\n"
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in MUTE_ALIASES])}"
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
                f"Aliases: {', '.join([ctx.clean_prefix + alias for alias in WARN_ALIASES])}"
            ),
            inline=False
        )
        
        # Impel Down Commands
        embed.add_field(
            name="🏢 Impel Down Commands",
            value=(
                f"`{ctx.clean_prefix}impeldown @user [level] [duration] [reason]` - Send a user to Impel Down\n"
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
                f"`{ctx.clean_prefix}piratehelp` - Display this help message\n"
                f"Aliases: `{ctx.clean_prefix}crewinfo`, `{ctx.clean_prefix}shipinfo`, `{ctx.clean_prefix}history`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Moderation Commands - These wrap around Red's existing commands
    
    @commands.command(name="luffykick", aliases=KICK_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
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
            return await ctx.send("You can't kick yourself, that's not how Devil Fruits work!")
            
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
            await member.kick(reason=f"{ctx.author}: {reason}")
            
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
                embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Kick",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at
                )
                await log_channel.send(embed=embed)
            
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
        except Exception as e:
            self.logger.error(f"Error in luffykick: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)[:100]}")
    
    @commands.command(name="shanksban", aliases=BAN_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
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
            await member.ban(reason=f"{ctx.author}: {reason}")
            
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
                embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Ban",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at
                )
                await log_channel.send(embed=embed)
            
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
        except Exception as e:
            self.logger.error(f"Error in shanksban: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)[:100]}")
    
    @commands.command(name="lawroom", aliases=MUTE_ALIASES)
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
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
            return await ctx.send(f"❌ No Sea Prism Stone role set! Use `{ctx.clean_prefix}onepiecemod setmuterole` first.")
            
        # Get the mute role
        mute_role = ctx.guild.get_role(mute_role_id)
        if not mute_role:
            return await ctx.send("❌ The Sea Prism Stone role has been deleted. Please set it again.")
            
        # Check if already muted
        if mute_role in member.roles:
            return await ctx.send(f"{member.mention} is already affected by Sea Prism Stone!")
            
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
            await member.add_roles(mute_role, reason=f"Muted by {ctx.author}: {reason}")
            
            # Apply timeout if available (Discord feature)
            if ctx.guild.me.guild_permissions.moderate_members:
                until = datetime.now(timezone.utc) + timedelta(seconds=duration)
                await member.timeout(until, reason=f"Muted by {ctx.author}: {reason}")
            
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
                # Add duration info for mutes
                embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="Mute",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Duration=format_time_duration(duration//60)  # Add duration as extra field
                )
                await log_channel.send(embed=embed)
            
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
        except Exception as e:
            self.logger.error(f"Error in lawroom: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)[:100]}")
    
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
        # Rate limit to prevent warning spam
        if not hasattr(self, "_warning_cooldown"):
            self._warning_cooldown = {}
            
        cooldown_key = f"{ctx.guild.id}:{ctx.author.id}:{member.id}"
        current_time = datetime.now().timestamp()
        
        if cooldown_key in self._warning_cooldown:
            if current_time - self._warning_cooldown[cooldown_key] < 30:
                return await ctx.send(f"⚠️ Please wait before setting another bounty on {member.mention}.")
                
        self._warning_cooldown[cooldown_key] = current_time
        
        # Check hierarchy
        if not await check_hierarchy(ctx, member, "My Haki isn't strong enough to warn this user!"):
            return
        
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
        level = min(warning_count, 6)
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
        escalation_level = 0
        escalation_duration = 0
        escalation_message = None
        
        if warning_count == 3:
            escalation_level = 1
            escalation_duration = 30 * 60  # 30 mins in seconds
            escalation_message = f"⚠️ This pirate has reached bounty level 3! {member.mention} will be sent to Impel Down Level 1!"
                    
        elif warning_count == 5:
            escalation_level = 3
            escalation_duration = 60 * 60  # 60 mins in seconds
            escalation_message = f"⚠️⚠️ This pirate has reached bounty level 5! {member.mention} will be sent to Impel Down Level 3!"
                    
        elif warning_count >= 7:
            escalation_level = 5
            escalation_duration = 120 * 60  # 120 mins in seconds
            escalation_message = f"⚠️⚠️⚠️ ALERT! This pirate has reached bounty level {warning_count}! {member.mention} will be sent to Impel Down Level 5!"
        
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
            await log_channel.send(embed=log_embed)
        
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
        if escalation_level > 0:
            # Create a task to handle escalation
            self.bot.loop.create_task(
                self.delayed_escalation(
                    ctx, member, escalation_level, escalation_duration // 60,  # Convert to minutes
                    f"Automatic after warning level {warning_count}: {reason}"
                )
            )
    
    @commands.command(name="impeldown", aliases=["imprison"])
    @commands.guild_only()
    @commands.mod_or_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, moderate_members=True)
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
        """Internal method to handle Impel Down imprisonment"""
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
        required_perms = discord.Permissions(manage_roles=True, moderate_members=True)
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
            await member.timeout(timeout_until, reason=f"Impel Down Level {level}: {reason}")
            
            # Get mute role ID
            mute_role_id = await self.config.guild(ctx.guild).mute_role()
            
            # Apply mute role if available
            if mute_role_id:
                mute_role = ctx.guild.get_role(mute_role_id)
                if mute_role:
                    await member.add_roles(mute_role, reason=f"Impel Down Level {level}: {reason}")
            
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
                embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelDown",
                    user=member,
                    moderator=ctx.author,
                    reason=f"Level {level}: {reason}",
                    timestamp=ctx.message.created_at,
                    Duration=f"{duration} minutes",
                    Level=f"Level {level}"
                )
                await log_channel.send(embed=embed)
            
            # Send the embed
            await ctx.send(embed=embed)
            
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to apply Impel Down restrictions!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ An error occurred while applying restrictions: {e}")
        except Exception as e:
            self.logger.error(f"Error in impel_down: {e}")
            await ctx.send(f"❌ An unexpected error occurred: {str(e)[:100]}")
    
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
                title="Jailbreak! Released from Impel Down!",
                description=f"{member.mention} has been released from Impel Down by {ctx.author.mention}!",
                color=discord.Color.gold()
            )
            
            # Get the active punishment to know which level they were at
            punishment = await self.get_active_punishment(ctx.guild, member)
            
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
                embed = self.create_modlog_embed(
                    case_num=case.case_number,
                    action_type="ImpelRelease",
                    user=member,
                    moderator=ctx.author,
                    reason=reason,
                    timestamp=ctx.message.created_at,
                    Previous_Level=f"Level {punishment.get('level', 'Unknown')}"
                )
                await log_channel.send(embed=embed)
            
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
            self.logger.error(f"Error in release_command: {e}")
            await ctx.send(f"❌ An error occurred: {str(e)[:100]}")
    
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
            return await ctx.send(f"{member.mention} doesn't have a bounty to clear!")
            
        # Get current warning count
        previous_level = len(warnings)
        
        # Clear warnings
        await self.clear_warnings(ctx.guild, member)
        
        # Create embed
        embed = discord.Embed(
            title="Bounty Cleared!",
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
        await modlog.create_case(
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
            title = "Bounty Poster"
            color = discord.Color.gold()
            
            # Get bounty level based on warning count
            level = min(warning_count, 6)
            bounty_level = BOUNTY_LEVELS[level]
            bounty_description = BOUNTY_DESCRIPTIONS[level]
            
            description = f"{member.mention} has a bounty of {bounty_level}!"
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
        """View a member's moderation history
        
        Examples:
        [p]crewhistory @User
        [p]history @User
        [p]modlogs @User
        """
        
        # Get moderation history
        history = await self.get_user_mod_history(ctx.guild, member)
        
        if not history:
            return await ctx.send(f"{member.mention} has no moderation history!")
            
        # Count actions by type
        action_counts = {}
        for entry in history:
            action_type = entry.get("action_type", "unknown")
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
            
        # Create embed
        embed = discord.Embed(
            title=f"Pirate History: {member.name}",
            description=f"Moderation history for {member.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add action counts
        action_field = ""
        for action, count in action_counts.items():
            action_name = action.replace("_", " ").title()
            action_field += f"{action_name}: **{count}**\n"
            
        embed.add_field(name="Action Summary", value=action_field or "None", inline=False)
        
        # Add recent actions (up to 10)
        recent_actions = history[-10:] if len(history) > 10 else history
        recent_field = ""
        
        for i, action in enumerate(reversed(recent_actions), 1):
            action_type = action.get("action_type", "unknown").replace("_", " ").title()
            mod_id = action.get("mod_id", 0)
            mod = ctx.guild.get_member(int(mod_id))
            mod_name = mod.name if mod else "Unknown"
            
            timestamp = action.get("timestamp", "Unknown")
            if timestamp != "Unknown":
                try:
                    # Parse the ISO timestamp
                    dt = datetime.fromisoformat(timestamp)
                    # Format as a more readable timestamp
                    timestamp = dt.strftime("%Y-%m-%d")
                except:
                    pass  # Keep original if parsing fails
                    
            reason = action.get("reason", "No reason provided")
            reason = (reason[:40] + "...") if len(reason) > 40 else reason
            
            recent_field += f"**{i}. {action_type}** - {timestamp}\n"
            recent_field += f"By: {mod_name} • Reason: {reason}\n\n"
            
        embed.add_field(name="Recent Actions", value=recent_field or "None", inline=False)
        
        # Add note if history is truncated
        if len(history) > 10:
            embed.set_footer(text=f"Showing 10 most recent actions. Total actions: {len(history)}")
            
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
            title=f"The {guild.name} Pirate Crew",
            description=guild.description or "A crew sailing the Grand Line!",
            color=discord.Color.blue()
        )
        
        # Set server icon as thumbnail
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            
        # Basic info
        embed.add_field(name="Captain", value=guild.owner.mention, inline=True)
        embed.add_field(name="Voyage Began", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        
        # Member info
        embed.add_field(name="Crew Size", value=f"{guild.member_count} members", inline=True)
        embed.add_field(name="Human Nakama", value=f"{humans} pirates", inline=True)
        embed.add_field(name="Den Den Mushi", value=f"{bots} snails", inline=True)
        
        # Channel info
        embed.add_field(name="Ship Areas", value=f"{len(guild.categories)} sections", inline=True)
        embed.add_field(name="Meeting Rooms", value=f"{text_channels} text channels", inline=True)
        embed.add_field(name="Voice Spots", value=f"{voice_channels} voice channels", inline=True)
        
        # Server features
        if guild.premium_subscription_count > 0:
            embed.add_field(
                name="Ship Upgrades", 
                value=f"Level {guild.premium_tier} (Boosted by {guild.premium_subscription_count} nakama)",
                inline=False
            )
            
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
                title=f"Command: {ctx.clean_prefix}{command.name}",
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
                
            await ctx.send(embed=embed)
            return
        
        # Otherwise, display the opm_help command's output
        await ctx.invoke(self.opm_help)

    # Error Handling
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle common errors for this cog"""
        # Ignore errors that have already been handled
        if getattr(ctx, "handled", False):
            return
            
        # Only handle errors for commands from this cog
        if not ctx.command or ctx.command.cog != self:
            return
            
        ctx.handled = True
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Your Haki isn't strong enough to use this command!")
            
        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await ctx.send(f"❌ I need more power! Missing permissions: {perms}")
            
        elif isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after)
            await ctx.send(f"⚖️ Justice is swift but not that swift! Try again in {remaining} seconds.")
            
        elif isinstance(error, commands.UserInputError):
            await ctx.send(f"❌ Invalid input: {str(error)}")
            
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, discord.Forbidden):
                await ctx.send("❌ I don't have permission to do that!")
            else:
                self.logger.error(f"Error in {ctx.command.name}: {error}")
                await ctx.send(f"❌ An error occurred: {str(error)[:100]}")
