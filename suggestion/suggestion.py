import discord
import asyncio
import logging
import re
from typing import Dict, Optional, Union, List, Set
from datetime import datetime, timedelta
from collections import defaultdict

from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import box, pagify, escape
from redbot.core.i18n import Translator, cog_i18n

log = logging.getLogger("red.suggestion")
_ = Translator("Suggestion", __file__)

# Constants
DEFAULT_THRESHOLD = 5
DEFAULT_MAX_LENGTH = 2000
DEFAULT_MIN_LENGTH = 10
DEFAULT_COOLDOWN = 300  # 5 minutes
MAX_SUGGESTION_LENGTH = 4000
MIN_SUGGESTION_LENGTH = 5


class SuggestionVotingView(discord.ui.View):
    """View for voting on suggestions with buttons"""
    
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog
        self.suggestion_id = suggestion_id
        # Initialize vote counts by loading from config
        self._load_vote_counts()
    
    async def _load_vote_counts(self):
        """Load current vote counts from the suggestion data"""
        # This should be called after the view is attached to a guild context
        pass
    
    def update_vote_counts(self, upvotes: int, downvotes: int):
        """Update the button labels with current vote counts"""
        # Find the buttons and update their labels
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "upvote":
                    item.label = f"Upvote ({upvotes})"
                elif item.custom_id == "downvote":
                    item.label = f"Downvote ({downvotes})"
    
    @discord.ui.button(label="Upvote (0)", style=discord.ButtonStyle.green, emoji="👍", custom_id="upvote")
    async def upvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle upvote button"""
        await self._handle_vote(interaction, "upvote")
    
    @discord.ui.button(label="Downvote (0)", style=discord.ButtonStyle.red, emoji="👎", custom_id="downvote")
    async def downvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle downvote button"""
        await self._handle_vote(interaction, "downvote")
    
    async def _handle_vote(self, interaction: discord.Interaction, vote_type: str):
        """Handle voting logic"""
        user_id = interaction.user.id
        
        # Get current suggestion data
        guild_config = await self.cog.get_guild_config(interaction.guild)
        suggestions = guild_config.get("suggestions", {})
        
        if str(self.suggestion_id) not in suggestions:
            await interaction.response.send_message("❌ This suggestion no longer exists.", ephemeral=True)
            return
        
        suggestion_data = suggestions[str(self.suggestion_id)]
        
        # Don't allow voting on processed suggestions
        if suggestion_data["status"] != "pending":
            await interaction.response.send_message("❌ This suggestion has already been processed.", ephemeral=True)
            return
        
        # Don't allow author to vote on their own suggestion
        if user_id == suggestion_data["author_id"]:
            await interaction.response.send_message("❌ You cannot vote on your own suggestion.", ephemeral=True)
            return
        
        # Get current votes from suggestion data
        current_votes = suggestion_data.get("votes", {"upvotes": [], "downvotes": []})
        upvoters = set(current_votes.get("upvotes", []))
        downvoters = set(current_votes.get("downvotes", []))
        
        # Handle vote logic
        if vote_type == "upvote":
            if user_id in upvoters:
                # Remove upvote
                upvoters.discard(user_id)
                await interaction.response.send_message("✅ Upvote removed.", ephemeral=True)
            else:
                # Add upvote, remove downvote if exists
                upvoters.add(user_id)
                downvoters.discard(user_id)
                await interaction.response.send_message("✅ Upvoted!", ephemeral=True)
        else:  # downvote
            if user_id in downvoters:
                # Remove downvote
                downvoters.discard(user_id)
                await interaction.response.send_message("✅ Downvote removed.", ephemeral=True)
            else:
                # Add downvote, remove upvote if exists
                downvoters.add(user_id)
                upvoters.discard(user_id)
                await interaction.response.send_message("✅ Downvoted!", ephemeral=True)
        
        # Update vote counts
        upvote_count = len(upvoters)
        downvote_count = len(downvoters)
        
        # Update button labels with new counts
        self.update_vote_counts(upvote_count, downvote_count)
        
        # Update the embed with new vote counts
        embed = interaction.message.embeds[0]
        
        # Find and update the votes field, or add it if it doesn't exist
        vote_field_updated = False
        for i, field in enumerate(embed.fields):
            if field.name == "Votes":
                embed.set_field_at(i, name="Votes", value=f"👍 {upvote_count} | 👎 {downvote_count}", inline=True)
                vote_field_updated = True
                break
        
        if not vote_field_updated:
            embed.add_field(name="Votes", value=f"👍 {upvote_count} | 👎 {downvote_count}", inline=True)
        
        # Update the message with both new embed and updated view
        try:
            await interaction.message.edit(embed=embed, view=self)
        except discord.HTTPException:
            pass
        
        # Save votes to config
        async with self.cog.config.guild(interaction.guild).suggestions() as suggestions_config:
            suggestions_config[str(self.suggestion_id)]["votes"] = {
                "upvotes": list(upvoters),
                "downvotes": list(downvoters)
            }
        
        self.cog.cache.invalidate(interaction.guild.id)
        
        # Check if threshold reached for staff review
        if (upvote_count >= guild_config["upvote_threshold"] and 
            suggestion_data["status"] == "pending" and
            suggestion_data.get("staff_message_id") is None):
            
            await self.cog._forward_to_staff(interaction.guild, str(self.suggestion_id), suggestion_data, upvote_count)

class SuggestionStaffView(discord.ui.View):
    """View for staff approval/denial buttons"""
    
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog
        self.suggestion_id = suggestion_id
    
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅", custom_id="approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve button handler"""
        if not await self._check_permissions(interaction):
            return
        
        modal = ReasonModal(self.cog, self.suggestion_id, "approved", "Approval Reason (Optional)")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌", custom_id="deny")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deny button handler"""
        if not await self._check_permissions(interaction):
            return
        
        modal = ReasonModal(self.cog, self.suggestion_id, "denied", "Denial Reason (Optional)")
        await interaction.response.send_modal(modal)
    
    async def _check_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if user has permission to approve/deny"""
        if not (interaction.user.guild_permissions.manage_guild or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ You don't have permission to manage suggestions.", ephemeral=True)
            return False
        return True


class ReasonModal(discord.ui.Modal):
    """Modal for entering approval/denial reasons"""
    
    def __init__(self, cog, suggestion_id: int, action: str, title: str):
        super().__init__(title=title)
        self.cog = cog
        self.suggestion_id = suggestion_id
        self.action = action
        
        self.reason_input = discord.ui.TextInput(
            label="Reason",
            placeholder="Enter your reason here (optional)...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        self.add_item(self.reason_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value.strip()
        
        # Create a mock context for the update function
        mock_ctx = type('MockContext', (), {
            'guild': interaction.guild,
            'author': interaction.user,
            'send': lambda msg: interaction.followup.send(msg, ephemeral=True)
        })()
        
        await interaction.response.defer(ephemeral=True)
        await self.cog._update_suggestion_status(mock_ctx, self.suggestion_id, self.action, reason, interaction=interaction)


class SuggestionCache:
    """Simple cache for frequently accessed data"""
    def __init__(self):
        self.guild_configs = {}
        self.last_update = {}
        self.cache_duration = 300  # 5 minutes
    
    def get(self, guild_id: int):
        """Get cached config if still valid"""
        if guild_id in self.guild_configs:
            if datetime.now().timestamp() - self.last_update.get(guild_id, 0) < self.cache_duration:
                return self.guild_configs[guild_id]
        return None
    
    def set(self, guild_id: int, config: dict):
        """Cache guild config"""
        self.guild_configs[guild_id] = config
        self.last_update[guild_id] = datetime.now().timestamp()
    
    def invalidate(self, guild_id: int):
        """Invalidate cache for a guild"""
        self.guild_configs.pop(guild_id, None)
        self.last_update.pop(guild_id, None)


class Suggestion(commands.Cog):
    """
    A comprehensive suggestion system for Discord communities.
    
    Features:
    - User suggestion submission with button voting
    - Staff review and approval system with buttons
    - User blacklisting and moderation
    - Configurable length limits and cooldowns
    - Comprehensive logging and analytics
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=9258471035622, force_registration=True
        )
        
        default_guild = {
            "suggestion_channel": None,
            "staff_channel": None,
            "log_channel": None,
            "upvote_threshold": DEFAULT_THRESHOLD,
            "suggestion_count": 0,
            "suggestions": {},
            "cleanup": True,
            "max_length": DEFAULT_MAX_LENGTH,
            "min_length": DEFAULT_MIN_LENGTH,
            "cooldown": DEFAULT_COOLDOWN,
            "blacklisted_users": {},  # user_id: {"reason": str, "timestamp": float, "by": int}
            "auto_delete_denied": False,
            "require_reason": False,
            "dm_notifications": True,
            "anonymous_suggestions": False,
        }
        
        default_user = {
            "suggestions_made": 0,
            "last_suggestion": 0,
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        # Cache and rate limiting
        self.cache = SuggestionCache()
        self.user_cooldowns = defaultdict(float)
        
        # Add persistent views
        self.bot.add_view(SuggestionVotingView(self, 0))  # Template view for persistence
        self.bot.add_view(SuggestionStaffView(self, 0))   # Template view for persistence

    async def cog_load(self):
        """Called when the cog is loaded"""
        # Initialize persistent views for existing suggestions
        await self.initialize_persistent_views()
    
    async def initialize_persistent_views(self):
        """Initialize persistent views for existing suggestions when bot starts"""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                guild_config = await self.get_guild_config(guild)
                suggestions = guild_config.get("suggestions", {})
                
                for suggestion_id, suggestion_data in suggestions.items():
                    if suggestion_data.get("status") == "pending":
                        # Create and register persistent view for each pending suggestion
                        view = SuggestionVotingView(self, int(suggestion_id))
                        
                        # Load current vote counts
                        votes = suggestion_data.get("votes", {"upvotes": [], "downvotes": []})
                        upvote_count = len(votes.get("upvotes", []))
                        downvote_count = len(votes.get("downvotes", []))
                        view.update_vote_counts(upvote_count, downvote_count)
                        
                        # Add the view to the bot's persistent views
                        self.bot.add_view(view)
                        
                        # Optionally, update the message to show current vote counts
                        try:
                            channel = guild.get_channel(suggestion_data["channel_id"])
                            if channel:
                                message = await channel.fetch_message(suggestion_data["message_id"])
                                # Update embed to show current votes
                                embed = message.embeds[0]
                                
                                # Update or add votes field
                                vote_field_updated = False
                                for i, field in enumerate(embed.fields):
                                    if field.name == "Votes":
                                        embed.set_field_at(i, name="Votes", value=f"👍 {upvote_count} | 👎 {downvote_count}", inline=True)
                                        vote_field_updated = True
                                        break
                                
                                if not vote_field_updated:
                                    embed.add_field(name="Votes", value=f"👍 {upvote_count} | 👎 {downvote_count}", inline=True)
                                
                                await message.edit(embed=embed, view=view)
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            # Message might be deleted or bot lacks permissions
                            pass
                    
                    elif suggestion_data.get("staff_message_id"):
                        # Initialize staff views for suggestions in review
                        staff_view = SuggestionStaffView(self, int(suggestion_id))
                        self.bot.add_view(staff_view)
            
            except Exception as e:
                log.error(f"Error initializing persistent views for guild {guild.id}: {e}")
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        # Clean up any persistent views
        pass
        
    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data for GDPR compliance"""
        user_id = kwargs.get("user_id")
        if user_id:
            await self.config.user_from_id(user_id).clear()
            log.info(f"Deleted suggestion data for user {user_id}")
        
    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data for GDPR compliance"""
        user_id = kwargs.get("user_id")
        if user_id:
            await self.config.user_from_id(user_id).clear()
            log.info(f"Deleted suggestion data for user {user_id}")

    async def get_guild_config(self, guild: discord.Guild) -> dict:
        """Get guild config with caching"""
        cached = self.cache.get(guild.id)
        if cached:
            return cached
        
        config = await self.config.guild(guild).all()
        self.cache.set(guild.id, config)
        return config

    async def update_guild_config(self, guild: discord.Guild, **kwargs):
        """Update guild config and invalidate cache"""
        for key, value in kwargs.items():
            await self.config.guild(guild).set_raw(key, value=value)
        self.cache.invalidate(guild.id)

    async def log_action(self, guild: discord.Guild, action: str, user: discord.Member, 
                        suggestion_id: int = None, details: str = "", moderator: discord.Member = None):
        """Log actions to the log channel if configured"""
        guild_config = await self.get_guild_config(guild)
        log_channel_id = guild_config.get("log_channel")
        
        if not log_channel_id:
            return
        
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=f"Suggestion System: {action}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        
        if moderator:
            embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)
        
        if suggestion_id:
            embed.add_field(name="Suggestion ID", value=f"#{suggestion_id}", inline=True)
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        try:
            await log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def is_user_blacklisted(self, guild: discord.Guild, user_id: int) -> tuple[bool, str]:
        """Check if user is blacklisted and return reason"""
        guild_config = await self.get_guild_config(guild)
        blacklisted_users = guild_config.get("blacklisted_users", {})
        
        if str(user_id) in blacklisted_users:
            return True, blacklisted_users[str(user_id)].get("reason", "No reason provided")
        return False, ""

    async def validate_suggestion_content(self, content: str, guild_config: dict) -> tuple[bool, str]:
        """Validate suggestion content against length limits"""
        min_length = guild_config.get("min_length", DEFAULT_MIN_LENGTH)
        max_length = guild_config.get("max_length", DEFAULT_MAX_LENGTH)
        
        if len(content) < min_length:
            return False, f"Suggestion must be at least {min_length} characters long."
        
        if len(content) > max_length:
            return False, f"Suggestion must be no more than {max_length} characters long."
        
        return True, ""

    async def check_user_cooldown(self, user_id: int, guild_config: dict) -> tuple[bool, int]:
        """Check if user is on cooldown"""
        cooldown = guild_config.get("cooldown", DEFAULT_COOLDOWN)
        last_suggestion = self.user_cooldowns.get(user_id, 0)
        current_time = datetime.now().timestamp()
        
        if current_time - last_suggestion < cooldown:
            remaining = int(cooldown - (current_time - last_suggestion))
            return False, remaining
        
        return True, 0

    def set_user_cooldown(self, user_id: int):
        """Set user cooldown"""
        self.user_cooldowns[user_id] = datetime.now().timestamp()

    @commands.group(name="suggestionset", aliases=["suggestset"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestion_set(self, ctx: commands.Context):
        """Configure the suggestion system."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @suggestion_set.command(name="channel")
    async def set_suggestion_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where suggestions will be posted."""
        # Check bot permissions properly
        channel_perms = channel.permissions_for(ctx.guild.me)
        required_perms = ["send_messages", "embed_links", "read_message_history", "use_external_emojis"]
        missing_perms = [perm for perm in required_perms if not getattr(channel_perms, perm)]
        
        if missing_perms:
            await ctx.send(_(
                "I need the following permissions in that channel: {perms}"
            ).format(perms=", ".join(missing_perms)))
            return
        
        await self.update_guild_config(ctx.guild, suggestion_channel=channel.id)
        await ctx.send(_(
            "Suggestion channel set to {channel}. Suggestions will now use buttons for voting!"
        ).format(channel=channel.mention))
        
        await self.log_action(ctx.guild, "Channel Set", ctx.author, 
                             details=f"Suggestion channel set to {channel.mention}")
    
    @suggestion_set.command(name="staffchannel")
    async def set_staff_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where approved suggestions will be sent for staff review."""
        channel_perms = channel.permissions_for(ctx.guild.me)
        if not (channel_perms.send_messages and channel_perms.embed_links):
            await ctx.send(_(
                "I need Send Messages and Embed Links permissions in that channel."
            ))
            return
        
        await self.update_guild_config(ctx.guild, staff_channel=channel.id)
        await ctx.send(_(
            "Staff review channel set to {channel}. Staff can use buttons to approve/deny suggestions!"
        ).format(channel=channel.mention))
    
    @suggestion_set.command(name="logchannel")
    async def set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where suggestion system logs will be posted."""
        channel_perms = channel.permissions_for(ctx.guild.me)
        if not (channel_perms.send_messages and channel_perms.embed_links):
            await ctx.send(_(
                "I need Send Messages and Embed Links permissions in that channel."
            ))
            return
        
        await self.update_guild_config(ctx.guild, log_channel=channel.id)
        await ctx.send(_(
            "Log channel set to {channel}."
        ).format(channel=channel.mention))
    
    @suggestion_set.command(name="threshold")
    async def set_threshold(self, ctx: commands.Context, threshold: int):
        """Set the number of upvotes needed for a suggestion to be sent for staff review."""
        if threshold < 1:
            await ctx.send(_("Threshold must be at least 1."))
            return
        
        if threshold > 50:
            await ctx.send(_("Threshold must be 50 or less to prevent abuse."))
            return
        
        await self.update_guild_config(ctx.guild, upvote_threshold=threshold)
        await ctx.send(_(
            "Upvote threshold set to {threshold}."
        ).format(threshold=threshold))
    
    @suggestion_set.command(name="maxlength")
    async def set_max_length(self, ctx: commands.Context, length: int):
        """Set the maximum length for suggestions."""
        if length < MIN_SUGGESTION_LENGTH:
            await ctx.send(f"Maximum length must be at least {MIN_SUGGESTION_LENGTH} characters.")
            return
        
        if length > MAX_SUGGESTION_LENGTH:
            await ctx.send(f"Maximum length cannot exceed {MAX_SUGGESTION_LENGTH} characters.")
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        min_length = guild_config.get("min_length", DEFAULT_MIN_LENGTH)
        
        if length < min_length:
            await ctx.send(f"Maximum length cannot be less than minimum length ({min_length}).")
            return
        
        await self.update_guild_config(ctx.guild, max_length=length)
        await ctx.send(f"Maximum suggestion length set to {length} characters.")
    
    @suggestion_set.command(name="minlength")
    async def set_min_length(self, ctx: commands.Context, length: int):
        """Set the minimum length for suggestions."""
        if length < MIN_SUGGESTION_LENGTH:
            await ctx.send(f"Minimum length must be at least {MIN_SUGGESTION_LENGTH} characters.")
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        max_length = guild_config.get("max_length", DEFAULT_MAX_LENGTH)
        
        if length > max_length:
            await ctx.send(f"Minimum length cannot be greater than maximum length ({max_length}).")
            return
        
        await self.update_guild_config(ctx.guild, min_length=length)
        await ctx.send(f"Minimum suggestion length set to {length} characters.")
    
    @suggestion_set.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, seconds: int):
        """Set the cooldown between suggestions for users (in seconds)."""
        if seconds < 0:
            await ctx.send("Cooldown cannot be negative.")
            return
        
        if seconds > 86400:  # 24 hours
            await ctx.send("Cooldown cannot exceed 24 hours (86400 seconds).")
            return
        
        await self.update_guild_config(ctx.guild, cooldown=seconds)
        
        if seconds == 0:
            await ctx.send("Suggestion cooldown disabled.")
        else:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            time_str = f"{minutes}m {remaining_seconds}s" if minutes > 0 else f"{seconds}s"
            await ctx.send(f"Suggestion cooldown set to {time_str}.")
    
    @suggestion_set.command(name="cleanup")
    async def set_cleanup(self, ctx: commands.Context, toggle: bool):
        """Toggle whether to remove non-suggestion messages from the suggestion channel."""
        await self.update_guild_config(ctx.guild, cleanup=toggle)
        if toggle:
            await ctx.send(_("I will now remove non-suggestion messages from the suggestion channel."))
        else:
            await ctx.send(_("I will no longer remove non-suggestion messages from the suggestion channel."))
    
    @suggestion_set.command(name="dmnotifications")
    async def set_dm_notifications(self, ctx: commands.Context, toggle: bool):
        """Toggle whether to send DM notifications to users when their suggestions are approved/denied."""
        await self.update_guild_config(ctx.guild, dm_notifications=toggle)
        if toggle:
            await ctx.send("Users will now receive DM notifications for suggestion updates.")
        else:
            await ctx.send("DM notifications for suggestion updates disabled.")
    
    @suggestion_set.command(name="anonymous")
    async def set_anonymous(self, ctx: commands.Context, toggle: bool):
        """Toggle whether suggestions can be submitted anonymously."""
        await self.update_guild_config(ctx.guild, anonymous_suggestions=toggle)
        if toggle:
            await ctx.send("Anonymous suggestions are now enabled.")
        else:
            await ctx.send("Anonymous suggestions are now disabled.")
    
    @suggestion_set.command(name="requirereason")
    async def set_require_reason(self, ctx: commands.Context, toggle: bool):
        """Toggle whether reasons are required for approval/denial."""
        await self.update_guild_config(ctx.guild, require_reason=toggle)
        if toggle:
            await ctx.send("✅ Reasons are now required for approval/denial.")
        else:
            await ctx.send("❌ Reasons are now optional for approval/denial.")
    
    @suggestion_set.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show the current suggestion system settings."""
        guild_config = await self.get_guild_config(ctx.guild)
        
        suggestion_channel = (
            self.bot.get_channel(guild_config["suggestion_channel"]).mention
            if guild_config["suggestion_channel"]
            else _("Not set")
        )
        
        staff_channel = (
            self.bot.get_channel(guild_config["staff_channel"]).mention
            if guild_config["staff_channel"]
            else _("Not set")
        )
        
        log_channel = (
            self.bot.get_channel(guild_config.get("log_channel")).mention
            if guild_config.get("log_channel")
            else _("Not set")
        )
        
        cooldown_text = f"{guild_config['cooldown']}s"
        if guild_config['cooldown'] >= 60:
            minutes = guild_config['cooldown'] // 60
            seconds = guild_config['cooldown'] % 60
            cooldown_text = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        
        embed = discord.Embed(
            title=_("Suggestion System Settings"),
            color=await ctx.embed_color(),
            description=_(
                "**Suggestion Channel:** {suggestion_channel}\n"
                "**Staff Review Channel:** {staff_channel}\n"
                "**Log Channel:** {log_channel}\n"
                "**Upvote Threshold:** {threshold}\n"
                "**Length Limits:** {min_length} - {max_length} characters\n"
                "**Cooldown:** {cooldown}\n"
                "**Cleanup Non-suggestions:** {cleanup}\n"
                "**DM Notifications:** {dm_notifications}\n"
                "**Anonymous Suggestions:** {anonymous}\n"
                "**Require Reason:** {require_reason}\n"
                "**Voting System:** Buttons Only\n"
                "**Total Suggestions:** {count}\n"
                "**Blacklisted Users:** {blacklisted_count}"
            ).format(
                suggestion_channel=suggestion_channel,
                staff_channel=staff_channel,
                log_channel=log_channel,
                threshold=guild_config["upvote_threshold"],
                min_length=guild_config["min_length"],
                max_length=guild_config["max_length"],
                cooldown=cooldown_text,
                cleanup="✅" if guild_config["cleanup"] else "❌",
                dm_notifications="✅" if guild_config["dm_notifications"] else "❌",
                anonymous="✅" if guild_config["anonymous_suggestions"] else "❌",
                require_reason="✅" if guild_config.get("require_reason", False) else "❌",
                count=guild_config["suggestion_count"],
                blacklisted_count=len(guild_config.get("blacklisted_users", {}))
            )
        )
        
        await ctx.send(embed=embed)

    # Blacklist Management Commands (keeping existing implementation)
    @commands.group(name="suggestblacklist", aliases=["sbl"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestion_blacklist(self, ctx: commands.Context):
        """Manage suggestion blacklist."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @suggestion_blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, user: discord.Member, *, reason: str = "No reason provided"):
        """Add a user to the suggestion blacklist."""
        if len(reason) > 500:
            await ctx.send("Blacklist reason must be 500 characters or less.")
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        blacklisted_users = guild_config.get("blacklisted_users", {})
        
        if str(user.id) in blacklisted_users:
            await ctx.send(f"{user.mention} is already blacklisted.")
            return
        
        blacklist_data = {
            "reason": reason,
            "timestamp": datetime.now().timestamp(),
            "by": ctx.author.id
        }
        
        blacklisted_users[str(user.id)] = blacklist_data
        await self.update_guild_config(ctx.guild, blacklisted_users=blacklisted_users)
        
        embed = discord.Embed(
            title="User Blacklisted",
            description=f"{user.mention} has been blacklisted from making suggestions.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        await self.log_action(ctx.guild, "User Blacklisted", user, 
                             details=reason, moderator=ctx.author)
    
    @suggestion_blacklist.command(name="list")
    async def blacklist_list(self, ctx: commands.Context):
        """List all blacklisted users."""
        guild_config = await self.get_guild_config(ctx.guild)
        blacklisted_users = guild_config.get("blacklisted_users", {})
        
        if not blacklisted_users:
            await ctx.send("No users are currently blacklisted.")
            return
        
        entries = []
        for user_id, data in blacklisted_users.items():
            user = ctx.guild.get_member(int(user_id))
            user_name = user.display_name if user else f"Unknown User ({user_id})"
            
            moderator = ctx.guild.get_member(data.get("by", 0))
            moderator_name = moderator.display_name if moderator else "Unknown"
            
            timestamp = datetime.fromtimestamp(data.get("timestamp", 0))
            reason = data.get("reason", "No reason provided")
            
            entries.append(
                f"**{user_name}** - {reason}\n"
                f"*Blacklisted by {moderator_name} on {timestamp.strftime('%Y-%m-%d')}*"
            )
        
        for page in pagify("\n\n".join(entries), page_length=1000):
            embed = discord.Embed(
                title="Blacklisted Users",
                description=page,
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @suggestion_blacklist.command(name="info")
    async def blacklist_info(self, ctx: commands.Context, user: discord.Member):
        """Show blacklist information for a specific user."""
        guild_config = await self.get_guild_config(ctx.guild)
        blacklisted_users = guild_config.get("blacklisted_users", {})
        
        if str(user.id) not in blacklisted_users:
            await ctx.send(f"{user.mention} is not blacklisted.")
            return
        
        data = blacklisted_users[str(user.id)]
        moderator = ctx.guild.get_member(data.get("by", 0))
        moderator_name = moderator.display_name if moderator else "Unknown"
        
        timestamp = datetime.fromtimestamp(data.get("timestamp", 0))
        reason = data.get("reason", "No reason provided")
        
        embed = discord.Embed(
            title="Blacklist Information",
            color=discord.Color.red()
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Blacklisted By", value=moderator_name, inline=True)
        embed.add_field(name="Date", value=timestamp.strftime('%Y-%m-%d %H:%M'), inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name="suggest", aliases=["idea"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)  # Basic spam protection
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        """Submit a suggestion.
        
        Your suggestion will be posted in the suggestion channel for others to vote on using buttons.
        If it receives enough upvotes, it will be sent for staff review.
        
        Example:
            [p]suggest Add a music channel to the server
        """
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Check if suggestion channel is set
        if not guild_config["suggestion_channel"]:
            await ctx.send(_("The suggestion channel has not been set up yet."))
            return
        
        suggestion_channel = self.bot.get_channel(guild_config["suggestion_channel"])
        if not suggestion_channel:
            await ctx.send(_("The suggestion channel no longer exists. Please ask an admin to set it up again."))
            return
        
        # Check if user is blacklisted
        is_blacklisted, blacklist_reason = await self.is_user_blacklisted(ctx.guild, ctx.author.id)
        if is_blacklisted:
            embed = discord.Embed(
                title="❌ Suggestion Blocked",
                description="You are blacklisted from making suggestions.",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=blacklist_reason, inline=False)
            await ctx.send(embed=embed)
            return
        
        # Validate suggestion content
        is_valid, validation_error = await self.validate_suggestion_content(suggestion, guild_config)
        if not is_valid:
            await ctx.send(f"❌ {validation_error}")
            return
        
        # Check cooldown
        can_suggest, remaining = await self.check_user_cooldown(ctx.author.id, guild_config)
        if not can_suggest:
            minutes = remaining // 60
            seconds = remaining % 60
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            await ctx.send(f"❌ You're on cooldown! Please wait {time_str} before suggesting again.")
            return
        
        # Create suggestion ID
        suggestion_id = guild_config["suggestion_count"] + 1
        
        # Create suggestion embed
        embed = discord.Embed(
            title=_("Suggestion #{id}").format(id=suggestion_id),
            description=suggestion,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if not guild_config.get("anonymous_suggestions", False):
            embed.set_author(
                name=f"{ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            embed.set_footer(text=f"ID: {ctx.author.id}")
        else:
            embed.set_footer(text="Anonymous suggestion")
        
        # Add initial vote field
        embed.add_field(name="Votes", value="👍 0 | 👎 0", inline=True)
        
        # Create voting view with proper initialization
        view = SuggestionVotingView(self, suggestion_id)
        # Initialize button labels to show vote counts
        view.update_vote_counts(0, 0)
        
        # Send suggestion to channel
        try:
            suggestion_msg = await suggestion_channel.send(embed=embed, view=view)
            
            # Save suggestion to config
            async with self.config.guild(ctx.guild).suggestions() as suggestions:
                suggestions[str(suggestion_id)] = {
                    "author_id": ctx.author.id,
                    "content": suggestion,
                    "message_id": suggestion_msg.id,
                    "channel_id": suggestion_channel.id,
                    "staff_message_id": None,
                    "status": "pending",
                    "timestamp": datetime.now().timestamp(),
                    "anonymous": guild_config.get("anonymous_suggestions", False),
                    "votes": {"upvotes": [], "downvotes": []},
                }
            
            # Update suggestion count and user stats
            await self.config.guild(ctx.guild).suggestion_count.set(suggestion_id)
            self.cache.invalidate(ctx.guild.id)
            
            # Update user statistics
            user_data = await self.config.user(ctx.author).all()
            user_data["suggestions_made"] += 1
            user_data["last_suggestion"] = datetime.now().timestamp()
            await self.config.user(ctx.author).set(user_data)
            
            # Set cooldown
            self.set_user_cooldown(ctx.author.id)
            
            # Confirm to user with tick emoji
            confirm_msg = await ctx.send(_(
                "✅ Your suggestion has been submitted and can be found in {channel}. Use the buttons to vote!"
            ).format(channel=suggestion_channel.mention))
            
            # Add tick reaction to original command message
            try:
                await ctx.message.add_reaction("✅")
            except (discord.Forbidden, discord.NotFound):
                pass
            
            # Clean up command message if in suggestion channel
            if ctx.channel.id == suggestion_channel.id and guild_config["cleanup"]:
                try:
                    await ctx.message.delete()
                    await confirm_msg.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
            
            # Log the action
            await self.log_action(ctx.guild, "Suggestion Created", ctx.author, 
                                 suggestion_id=suggestion_id, details=f"Content: {suggestion[:100]}...")
                
        except discord.Forbidden:
            await ctx.send(_("❌ I don't have permission to post in the suggestion channel."))
        except discord.HTTPException as e:
            await ctx.send(_("❌ An error occurred while posting your suggestion: {error}").format(error=str(e)))
    
    async def _forward_to_staff(self, guild: discord.Guild, suggestion_id: str, suggestion_data: dict, upvotes: int):
        """Forward suggestion to staff channel"""
        guild_config = await self.get_guild_config(guild)
        staff_channel = self.bot.get_channel(guild_config["staff_channel"])
        if not staff_channel:
            return
        
        author = guild.get_member(suggestion_data["author_id"])
        author_name = author.display_name if author else "Unknown User"
        
        # Create staff review embed
        embed = discord.Embed(
            title=_("Suggestion #{id} for Review").format(id=suggestion_id),
            description=suggestion_data["content"],
            color=discord.Color.gold(),
            timestamp=datetime.fromtimestamp(suggestion_data["timestamp"])
        )
        
        if not suggestion_data.get("anonymous", False):
            embed.set_author(
                name=author_name,
                icon_url=author.display_avatar.url if author else discord.Embed.Empty
            )
        else:
            embed.set_author(name="Anonymous User")
        
        embed.add_field(
            name=_("Votes"),
            value=_(
                "👍 {upvotes} upvotes - threshold reached!"
            ).format(upvotes=upvotes)
        )
        
        embed.set_footer(text=_("Use the buttons below to approve or deny this suggestion"))
        
        # Create staff view
        view = SuggestionStaffView(self, int(suggestion_id))
        
        # Send to staff channel
        try:
            staff_msg = await staff_channel.send(embed=embed, view=view)
            
            # Update suggestion data
            async with self.config.guild(guild).suggestions() as suggestions_config:
                suggestions_config[suggestion_id]["staff_message_id"] = staff_msg.id
            
            self.cache.invalidate(guild.id)
            
            # Log the action
            if author:
                await self.log_action(guild, "Suggestion Forwarded to Staff", author, 
                                     suggestion_id=int(suggestion_id), 
                                     details=f"Reached {upvotes} upvotes")
        except (discord.Forbidden, discord.HTTPException):
            pass
    
    @commands.command(name="approve")
    @commands.admin_or_permissions(manage_guild=True)
    async def approve_suggestion(self, ctx: commands.Context, suggestion_id: int, *, reason: str = ""):
        """Approve a suggestion.
        
        The suggestion will be updated with an approved status.
        Reason is optional unless required by server settings.
        
        Example:
            [p]approve 5 This is a great idea that we'll implement soon!
            [p]approve 5
        """
        await self._update_suggestion_status(ctx, suggestion_id, "approved", reason)
    
    @commands.command(name="deny")
    @commands.admin_or_permissions(manage_guild=True)
    async def deny_suggestion(self, ctx: commands.Context, suggestion_id: int, *, reason: str = ""):
        """Deny a suggestion.
        
        The suggestion will be updated with a denied status.
        Reason is optional unless required by server settings.
        
        Example:
            [p]deny 5 This doesn't fit our current server plans.
            [p]deny 5
        """
        await self._update_suggestion_status(ctx, suggestion_id, "denied", reason)
    
    async def _update_suggestion_status(self, ctx, suggestion_id: int, status: str, reason: str, interaction=None):
        """Update the status of a suggestion."""
        guild_config = await self.get_guild_config(ctx.guild)
        suggestions = guild_config["suggestions"]
        
        # Check if suggestion exists
        if str(suggestion_id) not in suggestions:
            error_msg = _("❌ Suggestion #{id} not found.").format(id=suggestion_id)
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        suggestion_data = suggestions[str(suggestion_id)]
        
        # Check if already processed
        if suggestion_data["status"] != "pending":
            error_msg = f"❌ Suggestion #{suggestion_id} has already been {suggestion_data['status']}."
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        # Validate reason if required
        if guild_config.get("require_reason", False) and not reason:
            error_msg = "❌ A reason is required for this action."
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        if len(reason) > 1000:
            error_msg = "❌ Reason must be 1000 characters or less."
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        # Get suggestion message
        channel = self.bot.get_channel(suggestion_data["channel_id"])
        if not channel:
            error_msg = _("❌ The suggestion channel no longer exists.")
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        try:
            message = await channel.fetch_message(suggestion_data["message_id"])
        except (discord.NotFound, discord.Forbidden):
            error_msg = _("❌ Could not find the suggestion message. It may have been deleted.")
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
            return
        
        # Update suggestion embed
        embed = message.embeds[0]
        
        if status == "approved":
            embed.color = discord.Color.green()
            status_text = _("✅ APPROVED")
            status_emoji = "✅"
        else:
            embed.color = discord.Color.red()
            status_text = _("❌ DENIED")
            status_emoji = "❌"
        
        # Add status field
        embed.add_field(
            name=status_text,
            value=reason if reason else _("No reason provided."),
            inline=False
        )
        embed.add_field(
            name="Reviewed by",
            value=ctx.author.mention,
            inline=True
        )
        
        # Update message and remove buttons
        try:
            await message.edit(embed=embed, view=None)
            
            # Update config
            async with self.config.guild(ctx.guild).suggestions() as suggestions_config:
                suggestions_config[str(suggestion_id)]["status"] = status
                suggestions_config[str(suggestion_id)]["reviewed_by"] = ctx.author.id
                suggestions_config[str(suggestion_id)]["reviewed_at"] = datetime.now().timestamp()
                suggestions_config[str(suggestion_id)]["review_reason"] = reason
            
            self.cache.invalidate(ctx.guild.id)
            
            success_msg = _(
                "{emoji} Suggestion #{id} has been **{status}**."
            ).format(emoji=status_emoji, id=suggestion_id, status=status)
            
            if interaction:
                await interaction.followup.send(success_msg, ephemeral=True)
            else:
                await ctx.send(success_msg)
            
            # Update staff message if it exists
            if suggestion_data.get("staff_message_id"):
                staff_channel = self.bot.get_channel(guild_config.get("staff_channel"))
                if staff_channel:
                    try:
                        staff_message = await staff_channel.fetch_message(suggestion_data["staff_message_id"])
                        staff_embed = staff_message.embeds[0]
                        staff_embed.color = discord.Color.green() if status == "approved" else discord.Color.red()
                        staff_embed.add_field(name=status_text, value=reason if reason else "No reason provided", inline=False)
                        staff_embed.add_field(name="Reviewed by", value=ctx.author.mention, inline=True)
                        await staff_message.edit(embed=staff_embed, view=None)
                    except (discord.NotFound, discord.Forbidden):
                        pass
            
            # Send DM notification if enabled
            if guild_config.get("dm_notifications", True) and not suggestion_data.get("anonymous", False):
                author = ctx.guild.get_member(suggestion_data["author_id"])
                if author:
                    try:
                        dm_embed = discord.Embed(
                            title=f"Suggestion #{suggestion_id} {status_text}",
                            description=suggestion_data["content"],
                            color=discord.Color.green() if status == "approved" else discord.Color.red()
                        )
                        dm_embed.add_field(name="Reason", value=reason if reason else "No reason provided", inline=False)
                        dm_embed.add_field(name="Server", value=ctx.guild.name, inline=True)
                        dm_embed.add_field(name="Reviewed by", value=ctx.author.display_name, inline=True)
                        
                        await author.send(embed=dm_embed)
                    except (discord.Forbidden, discord.HTTPException):
                        pass  # User has DMs disabled or other error
            
            # Log the action
            author = ctx.guild.get_member(suggestion_data["author_id"])
            if author:
                await self.log_action(ctx.guild, f"Suggestion {status.title()}", author, 
                                     suggestion_id=suggestion_id, details=reason, moderator=ctx.author)
            
        except (discord.Forbidden, discord.HTTPException) as e:
            error_msg = _("❌ An error occurred while updating the suggestion: {error}").format(error=str(e))
            if interaction:
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await ctx.send(error_msg)
    
    @commands.command(name="suggesthelp")
    @commands.guild_only()
    async def suggest_help(self, ctx: commands.Context):
        """Shows a helpful guide on how to use the suggestion system."""
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Get channels
        suggestion_channel = (
            self.bot.get_channel(guild_config["suggestion_channel"]).mention
            if guild_config["suggestion_channel"]
            else _("*Not set*")
        )
        
        # Custom prefix
        prefix = ctx.clean_prefix
        
        # Create a Discord-formatted embed with markdown
        embed = discord.Embed(
            title="📝 Suggestion System Guide",
            color=discord.Color.blue(),
            description=(
                "Our server uses a modern button-based suggestion system! Here's how to use it:"
            )
        )
        
        # How to make suggestions
        cooldown_text = f"{guild_config['cooldown']}s"
        if guild_config['cooldown'] >= 60:
            minutes = guild_config['cooldown'] // 60
            seconds = guild_config['cooldown'] % 60
            cooldown_text = f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"
        
        embed.add_field(
            name="📌 How to Submit a Suggestion",
            value=(
                f"Use `{prefix}suggest` or `{prefix}idea` followed by your suggestion.\n\n"
                "**Requirements:**\n"
                f"• Length: {guild_config['min_length']}-{guild_config['max_length']} characters\n"
                f"• Cooldown: {cooldown_text} between suggestions\n"
                f"• Must not be blacklisted\n\n"
                "**Examples:**\n"
                f"`{prefix}suggest Add a music channel to the server`\n"
                f"`{prefix}idea We should have weekly movie nights`\n\n"
                f"Your suggestion will appear in {suggestion_channel} with voting buttons."
            ),
            inline=False
        )
        
        # Voting section
        embed.add_field(
            name="🗳️ Voting on Suggestions",
            value=(
                "Each suggestion has **Upvote** and **Downvote** buttons:\n"
                "• Click **Upvote** 👍 to support the suggestion\n"
                "• Click **Downvote** 👎 if you don't support it\n"
                "• You can change your vote anytime by clicking buttons\n"
                "• You cannot vote on your own suggestions\n\n"
                f"When a suggestion receives **{guild_config['upvote_threshold']}** upvotes, "
                "it will be sent to the staff for review."
            ),
            inline=False
        )
        
        # Staff review section
        embed.add_field(
            name="👨‍⚖️ Staff Review Process",
            value=(
                "Staff members review popular suggestions using buttons:\n"
                "✅ **Approve** - The suggestion will be implemented\n"
                "❌ **Deny** - The suggestion won't be implemented\n\n"
                "The original suggestion will be updated with the staff's decision and reason."
            ),
            inline=False
        )
        
        # Viewing suggestions
        embed.add_field(
            name="🔍 Viewing Suggestions",
            value=(
                f"• View a specific suggestion with `{prefix}showsuggestion <ID>`\n"
                f"• List all suggestions with `{prefix}listsuggestions`\n"
                f"• Filter by status with `{prefix}listsuggestions pending`\n"
                f"• Also try: `{prefix}listsuggestions approved` or `{prefix}listsuggestions denied`\n"
                f"• Check your stats with `{prefix}suggestionstats`"
            ),
            inline=False
        )
        
        # Tips section
        embed.add_field(
            name="💡 Tips for Good Suggestions",
            value=(
                "• Be clear and specific about what you want\n"
                "• Explain why it would benefit the server\n"
                "• Keep suggestions reasonable and achievable\n"
                "• One suggestion per message for better voting\n"
                "• Be patient - staff reviews take time!\n"
                "• Use buttons to vote - no need for emoji reactions!"
            ),
            inline=False
        )
        
        # Footer
        embed.set_footer(text=f"Use {prefix}help Suggestion for detailed command information")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="suggestionstats", aliases=["suggeststats"])
    @commands.guild_only()
    async def suggestion_stats(self, ctx: commands.Context, user: discord.Member = None):
        """View suggestion statistics for yourself or another user."""
        target_user = user or ctx.author
        
        # Get user data
        user_data = await self.config.user(target_user).all()
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Check if user is blacklisted
        is_blacklisted, blacklist_reason = await self.is_user_blacklisted(ctx.guild, target_user.id)
        
        # Count user's suggestions by status
        suggestions = guild_config.get("suggestions", {})
        user_suggestions = {k: v for k, v in suggestions.items() if v["author_id"] == target_user.id}
        
        pending_count = sum(1 for s in user_suggestions.values() if s["status"] == "pending")
        approved_count = sum(1 for s in user_suggestions.values() if s["status"] == "approved")
        denied_count = sum(1 for s in user_suggestions.values() if s["status"] == "denied")
        
        # Calculate approval rate
        total_reviewed = approved_count + denied_count
        approval_rate = (approved_count / total_reviewed * 100) if total_reviewed > 0 else 0
        
        # Last suggestion time
        last_suggestion = user_data.get("last_suggestion", 0)
        if last_suggestion > 0:
            last_suggestion_date = datetime.fromtimestamp(last_suggestion).strftime("%Y-%m-%d %H:%M")
        else:
            last_suggestion_date = "Never"
        
        # Cooldown status
        can_suggest, remaining = await self.check_user_cooldown(target_user.id, guild_config)
        if can_suggest:
            cooldown_status = "Ready to suggest"
        else:
            minutes = remaining // 60
            seconds = remaining % 60
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            cooldown_status = f"On cooldown ({time_str} remaining)"
        
        embed = discord.Embed(
            title=f"Suggestion Statistics",
            color=discord.Color.red() if is_blacklisted else discord.Color.blue()
        )
        embed.set_author(name=target_user.display_name, icon_url=target_user.display_avatar.url)
        
        embed.add_field(name="Total Suggestions", value=str(user_data["suggestions_made"]), inline=True)
        embed.add_field(name="Pending", value=str(pending_count), inline=True)
        embed.add_field(name="Approved", value=str(approved_count), inline=True)
        embed.add_field(name="Denied", value=str(denied_count), inline=True)
        embed.add_field(name="Approval Rate", value=f"{approval_rate:.1f}%", inline=True)
        embed.add_field(name="Last Suggestion", value=last_suggestion_date, inline=True)
        
        if target_user == ctx.author:
            embed.add_field(name="Status", value=cooldown_status, inline=False)
        
        if is_blacklisted:
            embed.add_field(name="⚠️ Blacklisted", value=blacklist_reason, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="showsuggestion", aliases=["suggestion"])
    async def show_suggestion(self, ctx: commands.Context, suggestion_id: int):
        """Show details about a specific suggestion."""
        guild_config = await self.get_guild_config(ctx.guild)
        suggestions = guild_config["suggestions"]
        
        # Check if suggestion exists
        if str(suggestion_id) not in suggestions:
            await ctx.send(_("❌ Suggestion #{id} not found.").format(id=suggestion_id))
            return
        
        suggestion_data = suggestions[str(suggestion_id)]
        
        # Get author
        author = ctx.guild.get_member(suggestion_data["author_id"])
        author_name = author.display_name if author and not suggestion_data.get("anonymous", False) else "Anonymous User"
        
        # Create embed
        embed = discord.Embed(
            title=_("Suggestion #{id}").format(id=suggestion_id),
            description=suggestion_data["content"],
            timestamp=datetime.fromtimestamp(suggestion_data["timestamp"])
        )
        
        if author and not suggestion_data.get("anonymous", False):
            embed.set_author(
                name=author_name,
                icon_url=author.display_avatar.url
            )
        else:
            embed.set_author(name="Anonymous User")
        
        # Add vote counts
        votes = suggestion_data.get("votes", {"upvotes": [], "downvotes": []})
        upvote_count = len(votes.get("upvotes", []))
        downvote_count = len(votes.get("downvotes", []))
        embed.add_field(name="Votes", value=f"👍 {upvote_count} | 👎 {downvote_count}", inline=True)
        
        # Add status
        status_map = {
            "pending": (_("⏳ Pending"), discord.Color.blue()),
            "approved": (_("✅ Approved"), discord.Color.green()),
            "denied": (_("❌ Denied"), discord.Color.red())
        }
        
        status_text, color = status_map.get(suggestion_data["status"], (_("❓ Unknown"), discord.Color.light_gray()))
        embed.add_field(name=_("Status"), value=status_text, inline=True)
        embed.color = color
        
        # Add reviewer info if reviewed
        if suggestion_data["status"] != "pending":
            reviewed_by = ctx.guild.get_member(suggestion_data.get("reviewed_by", 0))
            if reviewed_by:
                embed.add_field(name="Reviewed by", value=reviewed_by.mention, inline=True)
            
            if suggestion_data.get("review_reason"):
                embed.add_field(name="Reason", value=suggestion_data["review_reason"], inline=False)
        
        # Add link to message
        channel = self.bot.get_channel(suggestion_data["channel_id"])
        if channel:
            message_link = f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/{suggestion_data['message_id']}"
            embed.add_field(
                name=_("Link"),
                value=f"[{_('Jump to Suggestion')}]({message_link})",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="listsuggestions", aliases=["suggestionlist", "suggestions"])
    async def list_suggestions(self, ctx: commands.Context, status: str = None):
        """List all suggestions, optionally filtered by status.
        
        Status can be: pending, approved, denied
        If no status is provided, all suggestions will be listed.
        
        Example:
            [p]listsuggestions approved
        """
        guild_config = await self.get_guild_config(ctx.guild)
        suggestions = guild_config["suggestions"]
        
        if not suggestions:
            await ctx.send(_("❌ There are no suggestions for this server."))
            return
        
        # Filter by status if provided
        if status:
            status = status.lower()
            valid_statuses = ["pending", "approved", "denied"]
            
            if status not in valid_statuses:
                await ctx.send(_(
                    "❌ Invalid status. Please use one of: {statuses}"
                ).format(statuses=", ".join(valid_statuses)))
                return
            
            filtered_suggestions = {
                k: v for k, v in suggestions.items() if v["status"] == status
            }
        else:
            filtered_suggestions = suggestions
        
        if not filtered_suggestions:
            await ctx.send(_("❌ No suggestions found with that status."))
            return
        
        # Create list output
        entries = []
        
        for suggestion_id, data in sorted(filtered_suggestions.items(), key=lambda x: int(x[0]), reverse=True):
            author = ctx.guild.get_member(data["author_id"])
            author_name = author.display_name if author and not data.get("anonymous", False) else "Anonymous"
            
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "denied": "❌"
            }.get(data["status"], "❓")
            
            # Get vote counts
            votes = data.get("votes", {"upvotes": [], "downvotes": []})
            upvote_count = len(votes.get("upvotes", []))
            downvote_count = len(votes.get("downvotes", []))
            
            # Truncate content if too long
            content = data["content"]
            if len(content) > 50:
                content = content[:47] + "..."
            
            timestamp = datetime.fromtimestamp(data["timestamp"]).strftime("%m/%d")
            
            entries.append(
                f"`#{suggestion_id}` {status_emoji} {content} - *{author_name}* ({timestamp}) [👍{upvote_count}/👎{downvote_count}]"
            )
        
        # Send paginated output
        for page in pagify("\n".join(entries), page_length=1000):
            embed = discord.Embed(
                title=_("Suggestions List"),
                description=page,
                color=await ctx.embed_color()
            )
            
            if status:
                embed.set_footer(text=_("Filtered by status: {status} • Total: {count}").format(
                    status=status, count=len(filtered_suggestions)))
            else:
                embed.set_footer(text=f"Total suggestions: {len(filtered_suggestions)}")
                
            await ctx.send(embed=embed)
    
    @commands.command(name="deletesuggestion", aliases=["delsuggestion"])
    @commands.admin_or_permissions(manage_guild=True)
    async def delete_suggestion(self, ctx: commands.Context, suggestion_id: int, *, reason: str = "No reason provided"):
        """Delete a suggestion completely.
        
        This will remove the suggestion from the database and attempt to delete the message.
        Use with caution as this action cannot be undone.
        
        Example:
            [p]deletesuggestion 5 Spam/inappropriate content
        """
        guild_config = await self.get_guild_config(ctx.guild)
        suggestions = guild_config["suggestions"]
        
        # Check if suggestion exists
        if str(suggestion_id) not in suggestions:
            await ctx.send(_("❌ Suggestion #{id} not found.").format(id=suggestion_id))
            return
        
        suggestion_data = suggestions[str(suggestion_id)]
        
        # Try to delete the original message
        channel = self.bot.get_channel(suggestion_data["channel_id"])
        if channel:
            try:
                message = await channel.fetch_message(suggestion_data["message_id"])
                await message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass  # Message already deleted or no permission
        
        # Try to delete staff message if it exists
        if suggestion_data.get("staff_message_id"):
            staff_channel = self.bot.get_channel(guild_config.get("staff_channel"))
            if staff_channel:
                try:
                    staff_message = await staff_channel.fetch_message(suggestion_data["staff_message_id"])
                    await staff_message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
        
        # Remove from database
        async with self.config.guild(ctx.guild).suggestions() as suggestions_config:
            del suggestions_config[str(suggestion_id)]
        
        self.cache.invalidate(ctx.guild.id)
        
        # Get author for logging
        author = ctx.guild.get_member(suggestion_data["author_id"])
        
        embed = discord.Embed(
            title="Suggestion Deleted",
            description=f"Suggestion #{suggestion_id} has been permanently deleted.",
            color=discord.Color.red()
        )
        embed.add_field(name="Content", value=suggestion_data["content"][:500] + ("..." if len(suggestion_data["content"]) > 500 else ""), inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Deleted by", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
        # Log the action
        if author:
            await self.log_action(ctx.guild, "Suggestion Deleted", author, 
                                 suggestion_id=suggestion_id, details=reason, moderator=ctx.author)
    
    @commands.command(name="suggestioninfo", aliases=["sinfo"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestion_info(self, ctx: commands.Context):
        """Show detailed information about the suggestion system for this server."""
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Count suggestions by status
        suggestions = guild_config.get("suggestions", {})
        pending_count = sum(1 for s in suggestions.values() if s["status"] == "pending")
        approved_count = sum(1 for s in suggestions.values() if s["status"] == "approved")
        denied_count = sum(1 for s in suggestions.values() if s["status"] == "denied")
        total_count = len(suggestions)
        
        # Calculate approval rate
        total_reviewed = approved_count + denied_count
        approval_rate = (approved_count / total_reviewed * 100) if total_reviewed > 0 else 0
        
        # Get top suggesters
        user_counts = defaultdict(int)
        for suggestion in suggestions.values():
            if not suggestion.get("anonymous", False):
                user_counts[suggestion["author_id"]] += 1
        
        top_suggesters = []
        for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            user = ctx.guild.get_member(user_id)
            if user:
                top_suggesters.append(f"{user.display_name}: {count}")
        
        # Calculate total votes
        total_upvotes = 0
        total_downvotes = 0
        for suggestion in suggestions.values():
            votes = suggestion.get("votes", {"upvotes": [], "downvotes": []})
            total_upvotes += len(votes.get("upvotes", []))
            total_downvotes += len(votes.get("downvotes", []))
        
        embed = discord.Embed(
            title="📊 Suggestion System Analytics",
            color=discord.Color.blue()
        )
        
        # Statistics
        embed.add_field(
            name="📈 Statistics",
            value=(
                f"**Total Suggestions:** {total_count}\n"
                f"**Pending:** {pending_count}\n"
                f"**Approved:** {approved_count}\n"
                f"**Denied:** {denied_count}\n"
                f"**Approval Rate:** {approval_rate:.1f}%\n"
                f"**Total Votes:** 👍{total_upvotes} 👎{total_downvotes}"
            ),
            inline=True
        )
        
        # System health
        suggestion_channel = self.bot.get_channel(guild_config["suggestion_channel"])
        staff_channel = self.bot.get_channel(guild_config["staff_channel"])
        log_channel = self.bot.get_channel(guild_config.get("log_channel"))
        
        health_indicators = []
        if suggestion_channel:
            health_indicators.append("✅ Suggestion Channel")
        else:
            health_indicators.append("❌ Suggestion Channel")
        
        if staff_channel:
            health_indicators.append("✅ Staff Channel")
        else:
            health_indicators.append("❌ Staff Channel")
        
        if log_channel:
            health_indicators.append("✅ Log Channel")
        else:
            health_indicators.append("❌ Log Channel")
        
        health_indicators.append("✅ Button Voting System")
        
        embed.add_field(
            name="🔧 System Health",
            value="\n".join(health_indicators),
            inline=True
        )
        
        # Top suggesters
        if top_suggesters:
            embed.add_field(
                name="🏆 Top Suggesters",
                value="\n".join(top_suggesters),
                inline=False
            )
        
        # Recent activity (last 7 days)
        one_week_ago = (datetime.now() - timedelta(days=7)).timestamp()
        recent_suggestions = [s for s in suggestions.values() if s["timestamp"] > one_week_ago]
        
        embed.add_field(
            name="📅 Recent Activity (7 days)",
            value=f"{len(recent_suggestions)} new suggestions",
            inline=True
        )
        
        # Blacklisted users
        blacklisted_count = len(guild_config.get("blacklisted_users", {}))
        embed.add_field(
            name="🚫 Blacklisted Users",
            value=str(blacklisted_count),
            inline=True
        )
        
        embed.set_footer(text="🔘 Using Modern Button-Based Voting System")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="bulkdeny")
    @commands.admin_or_permissions(manage_guild=True)
    async def bulk_deny(self, ctx: commands.Context, *suggestion_ids: int, reason: str = "Bulk denial"):
        """Deny multiple suggestions at once.
        
        Example:
            [p]bulkdeny 1 2 3 4 5 These suggestions are outdated
        """
        if not suggestion_ids:
            await ctx.send("❌ Please provide at least one suggestion ID.")
            return
        
        if len(suggestion_ids) > 20:
            await ctx.send("❌ You can only bulk deny up to 20 suggestions at once.")
            return
        
        successful = []
        failed = []
        
        for suggestion_id in suggestion_ids:
            try:
                # Use a simplified check since we're doing bulk operations
                guild_config = await self.get_guild_config(ctx.guild)
                suggestions = guild_config["suggestions"]
                
                if str(suggestion_id) in suggestions and suggestions[str(suggestion_id)]["status"] == "pending":
                    await self._update_suggestion_status(ctx, suggestion_id, "denied", reason)
                    successful.append(suggestion_id)
                else:
                    failed.append(f"#{suggestion_id} (not found/already processed)")
            except Exception:
                failed.append(f"#{suggestion_id} (error)")
        
        embed = discord.Embed(
            title="Bulk Denial Results",
            color=discord.Color.orange()
        )
        
        if successful:
            embed.add_field(
                name=f"✅ Successfully Denied ({len(successful)})",
                value=", ".join(f"#{sid}" for sid in successful),
                inline=False
            )
        
        if failed:
            embed.add_field(
                name=f"❌ Failed ({len(failed)})",
                value=", ".join(failed),
                inline=False
            )
        
        embed.add_field(name="Reason Used", value=reason, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="searchsuggestions", aliases=["findsuggestion"])
    async def search_suggestions(self, ctx: commands.Context, *, query: str):
        """Search for suggestions containing specific text.
        
        Example:
            [p]searchsuggestions music channel
        """
        if len(query) < 3:
            await ctx.send("❌ Search query must be at least 3 characters long.")
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        suggestions = guild_config.get("suggestions", {})
        
        if not suggestions:
            await ctx.send("❌ There are no suggestions to search.")
            return
        
        # Search for matching suggestions
        matches = []
        query_lower = query.lower()
        
        for suggestion_id, data in suggestions.items():
            if query_lower in data["content"].lower():
                author = ctx.guild.get_member(data["author_id"])
                author_name = author.display_name if author and not data.get("anonymous", False) else "Anonymous"
                
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅", 
                    "denied": "❌"
                }.get(data["status"], "❓")
                
                # Get vote counts
                votes = data.get("votes", {"upvotes": [], "downvotes": []})
                upvote_count = len(votes.get("upvotes", []))
                downvote_count = len(votes.get("downvotes", []))
                
                # Highlight the matching text
                content = data["content"]
                if len(content) > 100:
                    # Find the query in the content and show surrounding context
                    start_idx = content.lower().find(query_lower)
                    start = max(0, start_idx - 30)
                    end = min(len(content), start_idx + len(query) + 30)
                    content = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
                
                matches.append(f"`#{suggestion_id}` {status_emoji} {content} - *{author_name}* [👍{upvote_count}/👎{downvote_count}]")
        
        if not matches:
            await ctx.send(f"❌ No suggestions found containing '{query}'.")
            return
        
        # Send paginated results
        for page in pagify("\n\n".join(matches), page_length=1000):
            embed = discord.Embed(
                title=f"🔍 Search Results for '{query}'",
                description=page,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Found {len(matches)} matching suggestions")
            await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages in the suggestion channel."""
        if message.author.bot and message.author.id != self.bot.user.id:
            return
        
        if not message.guild:
            return
        
        guild_config = await self.get_guild_config(message.guild)
        
        # Check if message is in suggestion channel and cleanup is enabled
        if (guild_config["cleanup"] and 
            guild_config["suggestion_channel"] and 
            message.channel.id == guild_config["suggestion_channel"]):
            
            # If it's the bot's message but not a suggestion embed, delete it
            if message.author.id == self.bot.user.id:
                # Keep only messages with embeds that have a title starting with "Suggestion #"
                should_keep = False
                for embed in message.embeds:
                    if embed.title and embed.title.startswith(_("Suggestion #")):
                        should_keep = True
                        break
                
                if not should_keep:
                    try:
                        await asyncio.sleep(5)  # Brief delay before deleting
                        await message.delete()
                    except (discord.Forbidden, discord.NotFound):
                        pass
                return
            
            # Check if message is a command
            context = await self.bot.get_context(message)
            if context.valid and context.command:
                # If command is suggest/idea, message will be deleted in the command handler
                if context.command.name not in ["suggest", "idea"]:
                    # For other commands, delete both the command and the response
                    # We'll delete the response in the on_command_completion
                    return
            else:
                # Not a command, delete non-suggestion messages
                try:
                    await asyncio.sleep(3)  # Brief delay before deleting
                    await message.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        """Handle command completion to clean up command messages."""
        if not ctx.guild:
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Check if command was used in suggestion channel and cleanup is enabled
        if (guild_config["cleanup"] and 
            guild_config["suggestion_channel"] and 
            ctx.channel.id == guild_config["suggestion_channel"] and
            ctx.command.name not in ["suggest", "idea"]):
            
            try:
                # Delete the command message
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        """Handle command errors to clean up error messages in suggestion channel."""
        if not ctx.guild:
            return
        
        guild_config = await self.get_guild_config(ctx.guild)
        
        # Check if error occurred in suggestion channel and cleanup is enabled
        if (guild_config["cleanup"] and 
            guild_config["suggestion_channel"] and 
            ctx.channel.id == guild_config["suggestion_channel"]):
            
            # Delete the command message that caused the error
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            
            # Send the error message and then delete it after a short delay
            if isinstance(error, commands.CommandInvokeError):
                error = error.original
            elif isinstance(error, commands.CommandOnCooldown):
                # Handle cooldown errors gracefully
                return
            
            error_msg = await ctx.send(f"❌ An error occurred: {str(error)}")
            await asyncio.sleep(5)
            try:
                await error_msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
