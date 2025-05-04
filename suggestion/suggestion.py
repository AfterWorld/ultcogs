import discord
import asyncio
import logging
from typing import Dict, Optional, Union
from datetime import datetime

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.i18n import Translator, cog_i18n

log = logging.getLogger("red.suggestion")
_ = Translator("Suggestion", __file__)

UPVOTE_EMOJI = "👍"
DOWNVOTE_EMOJI = "👎"
DEFAULT_THRESHOLD = 5  # Number of upvotes needed for staff review


class Suggestion(commands.Cog):
    """
    A suggestion system for Discord communities.
    
    Users can submit suggestions that will be posted to a designated channel.
    Community members can vote on suggestions with reactions.
    Staff can approve or deny suggestions.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=9258471035622, force_registration=True
        )
        
        default_guild = {
            "suggestion_channel": None,
            "staff_channel": None,
            "upvote_threshold": DEFAULT_THRESHOLD,
            "suggestion_count": 0,
            "suggestions": {},
            "cleanup": True,
        }
        
        self.config.register_guild(**default_guild)
        
    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        pass

    @commands.group(name="suggestionset", aliases=["suggestset"])
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestion_set(self, ctx: commands.Context):
        """Configure the suggestion system."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @suggestion_set.command(name="channel")
    async def set_suggestion_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where suggestions will be posted."""
        # Check if bot has required permissions in the channel
        required_perms = discord.PermissionOverwrite(
            send_messages=True,
            embed_links=True,
            add_reactions=True,
            read_messages=True,
            read_message_history=True
        )
        
        channel_perms = channel.permissions_for(ctx.guild.me)
        if not (channel_perms.send_messages and channel_perms.embed_links and 
                channel_perms.add_reactions and channel_perms.read_message_history):
            await ctx.send(_(
                "I need the following permissions in that channel: "
                "Send Messages, Embed Links, Add Reactions, Read Message History."
            ))
            return
        
        await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
        await ctx.send(_(
            "Suggestion channel set to {channel}."
        ).format(channel=channel.mention))
    
    @suggestion_set.command(name="staffchannel")
    async def set_staff_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where approved suggestions will be sent for staff review."""
        # Check bot permissions in staff channel
        channel_perms = channel.permissions_for(ctx.guild.me)
        if not (channel_perms.send_messages and channel_perms.embed_links):
            await ctx.send(_(
                "I need the following permissions in that channel: "
                "Send Messages, Embed Links."
            ))
            return
        
        await self.config.guild(ctx.guild).staff_channel.set(channel.id)
        await ctx.send(_(
            "Staff review channel set to {channel}."
        ).format(channel=channel.mention))
    
    @suggestion_set.command(name="threshold")
    async def set_threshold(self, ctx: commands.Context, threshold: int):
        """Set the number of upvotes needed for a suggestion to be sent for staff review."""
        if threshold < 1:
            await ctx.send(_("Threshold must be at least 1."))
            return
        
        await self.config.guild(ctx.guild).upvote_threshold.set(threshold)
        await ctx.send(_(
            "Upvote threshold set to {threshold}."
        ).format(threshold=threshold))
    
    @suggestion_set.command(name="cleanup")
    async def set_cleanup(self, ctx: commands.Context, toggle: bool):
        """Toggle whether to remove non-suggestion messages from the suggestion channel.
        
        Set to True to remove messages that aren't suggestions.
        Set to False to allow other messages in the suggestion channel.
        """
        await self.config.guild(ctx.guild).cleanup.set(toggle)
        if toggle:
            await ctx.send(_("I will now remove non-suggestion messages from the suggestion channel."))
        else:
            await ctx.send(_("I will no longer remove non-suggestion messages from the suggestion channel."))
    
    @suggestion_set.command(name="settings")
    async def show_settings(self, ctx: commands.Context):
        """Show the current suggestion system settings."""
        guild_config = await self.config.guild(ctx.guild).all()
        
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
        
        embed = discord.Embed(
            title=_("Suggestion System Settings"),
            color=await ctx.embed_color(),
            description=_(
                "**Suggestion Channel:** {suggestion_channel}\n"
                "**Staff Review Channel:** {staff_channel}\n"
                "**Upvote Threshold:** {threshold}\n"
                "**Cleanup Non-suggestions:** {cleanup}\n"
                "**Total Suggestions:** {count}"
            ).format(
                suggestion_channel=suggestion_channel,
                staff_channel=staff_channel,
                threshold=guild_config["upvote_threshold"],
                cleanup=guild_config["cleanup"],
                count=guild_config["suggestion_count"]
            )
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="suggest", aliases=["idea"])
    @commands.guild_only()
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        """Submit a suggestion.
        
        Your suggestion will be posted in the suggestion channel for others to vote on.
        If it receives enough upvotes, it will be sent for staff review.
        
        Example:
            [p]suggest Add a music channel to the server
        """
        guild_config = await self.config.guild(ctx.guild).all()
        
        # Check if suggestion channel is set
        if not guild_config["suggestion_channel"]:
            await ctx.send(_("The suggestion channel has not been set up yet."))
            return
        
        suggestion_channel = self.bot.get_channel(guild_config["suggestion_channel"])
        if not suggestion_channel:
            await ctx.send(_("The suggestion channel no longer exists. Please ask an admin to set it up again."))
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
        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        )
        embed.set_footer(text=f"ID: {ctx.author.id}")
        
        # Send suggestion to channel
        try:
            suggestion_msg = await suggestion_channel.send(embed=embed)
            
            # Add voting reactions
            await suggestion_msg.add_reaction(UPVOTE_EMOJI)
            await suggestion_msg.add_reaction(DOWNVOTE_EMOJI)
            
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
                }
            
            # Update suggestion count
            await self.config.guild(ctx.guild).suggestion_count.set(suggestion_id)
            
            # Confirm to user
            confirm_msg = await ctx.send(_(
                "Your suggestion has been submitted and can be found in {channel}."
            ).format(channel=suggestion_channel.mention))
            
            # Clean up command message if in suggestion channel
            if ctx.channel.id == suggestion_channel.id and guild_config["cleanup"]:
                try:
                    await ctx.message.delete()
                    # Also remove the confirmation message if in suggestion channel
                    await confirm_msg.delete()
                except (discord.Forbidden, discord.NotFound):
                    pass
                
        except discord.Forbidden:
            await ctx.send(_("I don't have permission to post in the suggestion channel."))
        except discord.HTTPException as e:
            await ctx.send(_("An error occurred while posting your suggestion: {error}").format(error=str(e)))
    
    @commands.command(name="suggesthelp")
    @commands.guild_only()
    async def suggest_help(self, ctx: commands.Context):
        """Shows a helpful guide on how to use the suggestion system."""
        guild_config = await self.config.guild(ctx.guild).all()
        
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
                "Our server uses a community-driven suggestion system! Here's how to use it:"
            )
        )
        
        # How to make suggestions
        embed.add_field(
            name="📌 How to Submit a Suggestion",
            value=(
                f"Use `{prefix}suggest` or `{prefix}idea` followed by your suggestion.\n\n"
                "**Examples:**\n"
                f"`{prefix}suggest Add a music channel to the server`\n"
                f"`{prefix}idea We should have weekly movie nights`\n\n"
                f"Your suggestion will appear in {suggestion_channel} for everyone to vote on."
            ),
            inline=False
        )
        
        # Voting section
        embed.add_field(
            name="🗳️ Voting on Suggestions",
            value=(
                "Each suggestion can be voted on with reactions:\n"
                f"{UPVOTE_EMOJI} - Support this suggestion\n"
                f"{DOWNVOTE_EMOJI} - Don't support this suggestion\n\n"
                f"When a suggestion receives **{guild_config['upvote_threshold']}** upvotes, "
                "it will be sent to the staff for review."
            ),
            inline=False
        )
        
        # Staff review section
        embed.add_field(
            name="👨‍⚖️ Staff Review Process",
            value=(
                "Staff members review popular suggestions and may:\n"
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
                f"• Also try: `{prefix}listsuggestions approved` or `{prefix}listsuggestions denied`"
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
                "• Be patient - staff reviews take time!"
            ),
            inline=False
        )
        
        # Footer
        embed.set_footer(text=f"Use {prefix}help Suggestion for detailed command information")
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitor messages in the suggestion channel."""
        if message.author.bot and message.author.id != self.bot.user.id:
            return
        
        if not message.guild:
            return
        
        guild_config = await self.config.guild(message.guild).all()
        
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
        
        guild_config = await self.config.guild(ctx.guild).all()
        
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
        
        guild_config = await self.config.guild(ctx.guild).all()
        
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
            
            error_msg = await ctx.send(f"An error occurred: {str(error)}")
            await asyncio.sleep(5)
            try:
                await error_msg.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction events for suggestions."""
        if payload.user_id == self.bot.user.id:
            return
        
        # Get guild config
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        guild_config = await self.config.guild(guild).all()
        
        # Check if this is a suggestion message
        suggestions = guild_config["suggestions"]
        suggestion_id = None
        
        for sid, data in suggestions.items():
            if data["message_id"] == payload.message_id:
                suggestion_id = sid
                break
        
        if not suggestion_id:
            return
        
        # Check if this is an upvote and we need to forward to staff
        if (str(payload.emoji) == UPVOTE_EMOJI and 
            guild_config["staff_channel"] and 
            suggestions[suggestion_id]["status"] == "pending"):
            
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return
            
            # Get message to count reactions
            try:
                message = await channel.fetch_message(payload.message_id)
            except (discord.NotFound, discord.Forbidden):
                return
            
            # Count upvotes
            upvotes = 0
            for reaction in message.reactions:
                if str(reaction.emoji) == UPVOTE_EMOJI:
                    upvotes = reaction.count - 1  # Subtract bot's reaction
                    break
            
            # Check if threshold reached
            if upvotes >= guild_config["upvote_threshold"]:
                # Forward to staff channel
                staff_channel = self.bot.get_channel(guild_config["staff_channel"])
                if not staff_channel:
                    return
                
                suggestion_data = suggestions[suggestion_id]
                author = guild.get_member(suggestion_data["author_id"])
                author_name = author.display_name if author else "Unknown User"
                
                # Create staff review embed
                embed = discord.Embed(
                    title=_("Suggestion #{id} for Review").format(id=suggestion_id),
                    description=suggestion_data["content"],
                    color=discord.Color.gold(),
                    timestamp=datetime.fromtimestamp(suggestion_data["timestamp"])
                )
                embed.set_author(
                    name=author_name,
                    icon_url=author.avatar.url if author and author.avatar else discord.Embed.Empty
                )
                embed.add_field(
                    name=_("Votes"),
                    value=_(
                        "{upvotes} upvotes, threshold reached!"
                    ).format(upvotes=upvotes)
                )
                embed.set_footer(text=_("Use [p]approve or [p]deny to handle this suggestion"))
                
                # Send to staff channel
                try:
                    staff_msg = await staff_channel.send(embed=embed)
                    
                    # Update suggestion data
                    async with self.config.guild(guild).suggestions() as suggestions_config:
                        suggestions_config[suggestion_id]["staff_message_id"] = staff_msg.id
                except (discord.Forbidden, discord.HTTPException):
                    pass
        
        # Remove reactions that aren't upvote or downvote
        if str(payload.emoji) not in [UPVOTE_EMOJI, DOWNVOTE_EMOJI]:
            channel = self.bot.get_channel(payload.channel_id)
            if not channel:
                return
                
            try:
                message = await channel.fetch_message(payload.message_id)
                # Remove the non-standard reaction
                await message.remove_reaction(payload.emoji, discord.Object(payload.user_id))
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
    
    @commands.command(name="approve")
    @commands.admin_or_permissions(manage_guild=True)
    async def approve_suggestion(self, ctx: commands.Context, suggestion_id: int, *, reason: str = ""):
        """Approve a suggestion.
        
        The suggestion will be updated with an approved status.
        
        Example:
            [p]approve 5 This is a great idea!
        """
        await self._update_suggestion_status(ctx, suggestion_id, "approved", reason)
    
    @commands.command(name="deny")
    @commands.admin_or_permissions(manage_guild=True)
    async def deny_suggestion(self, ctx: commands.Context, suggestion_id: int, *, reason: str = ""):
        """Deny a suggestion.
        
        The suggestion will be updated with a denied status.
        
        Example:
            [p]deny 5 This doesn't fit our current plans.
        """
        await self._update_suggestion_status(ctx, suggestion_id, "denied", reason)
    
    async def _update_suggestion_status(self, ctx: commands.Context, suggestion_id: int, status: str, reason: str):
        """Update the status of a suggestion."""
        guild_config = await self.config.guild(ctx.guild).all()
        suggestions = guild_config["suggestions"]
        
        # Check if suggestion exists
        if str(suggestion_id) not in suggestions:
            await ctx.send(_("Suggestion #{id} not found.").format(id=suggestion_id))
            return
        
        suggestion_data = suggestions[str(suggestion_id)]
        
        # Get suggestion message
        channel = self.bot.get_channel(suggestion_data["channel_id"])
        if not channel:
            await ctx.send(_("The suggestion channel no longer exists."))
            return
        
        try:
            message = await channel.fetch_message(suggestion_data["message_id"])
        except (discord.NotFound, discord.Forbidden):
            await ctx.send(_("Could not find the suggestion message. It may have been deleted."))
            return
        
        # Update suggestion embed
        embed = message.embeds[0]
        
        if status == "approved":
            embed.color = discord.Color.green()
            status_text = _("APPROVED")
        else:
            embed.color = discord.Color.red()
            status_text = _("DENIED")
        
        # Add status field
        embed.add_field(
            name=status_text,
            value=reason if reason else _("No reason provided."),
            inline=False
        )
        
        # Update message
        try:
            await message.edit(embed=embed)
            
            # Update config
            async with self.config.guild(ctx.guild).suggestions() as suggestions_config:
                suggestions_config[str(suggestion_id)]["status"] = status
            
            await ctx.send(_(
                "Suggestion #{id} has been {status}."
            ).format(id=suggestion_id, status=status))
            
        except (discord.Forbidden, discord.HTTPException) as e:
            await ctx.send(_("An error occurred while updating the suggestion: {error}").format(error=str(e)))
    
    @commands.command(name="showsuggestion")
    async def show_suggestion(self, ctx: commands.Context, suggestion_id: int):
        """Show details about a specific suggestion."""
        guild_config = await self.config.guild(ctx.guild).all()
        suggestions = guild_config["suggestions"]
        
        # Check if suggestion exists
        if str(suggestion_id) not in suggestions:
            await ctx.send(_("Suggestion #{id} not found.").format(id=suggestion_id))
            return
        
        suggestion_data = suggestions[str(suggestion_id)]
        
        # Get author
        author = ctx.guild.get_member(suggestion_data["author_id"])
        author_name = author.display_name if author else _("Unknown User")
        
        # Create embed
        embed = discord.Embed(
            title=_("Suggestion #{id}").format(id=suggestion_id),
            description=suggestion_data["content"],
            color=await ctx.embed_color(),
            timestamp=datetime.fromtimestamp(suggestion_data["timestamp"])
        )
        embed.set_author(
            name=author_name,
            icon_url=author.avatar.url if author and author.avatar else discord.Embed.Empty
        )
        
        # Add status
        status_map = {
            "pending": (_("Pending"), discord.Color.blue()),
            "approved": (_("Approved"), discord.Color.green()),
            "denied": (_("Denied"), discord.Color.red())
        }
        
        status_text, color = status_map.get(suggestion_data["status"], (_("Unknown"), discord.Color.light_gray()))
        embed.add_field(name=_("Status"), value=status_text, inline=True)
        embed.color = color
        
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
    
    @commands.command(name="listsuggestions", aliases=["suggestionlist"])
    async def list_suggestions(self, ctx: commands.Context, status: str = None):
        """List all suggestions, optionally filtered by status.
        
        Status can be: pending, approved, denied
        If no status is provided, all suggestions will be listed.
        
        Example:
            [p]listsuggestions approved
        """
        guild_config = await self.config.guild(ctx.guild).all()
        suggestions = guild_config["suggestions"]
        
        if not suggestions:
            await ctx.send(_("There are no suggestions for this server."))
            return
        
        # Filter by status if provided
        if status:
            status = status.lower()
            valid_statuses = ["pending", "approved", "denied"]
            
            if status not in valid_statuses:
                await ctx.send(_(
                    "Invalid status. Please use one of: {statuses}"
                ).format(statuses=", ".join(valid_statuses)))
                return
            
            filtered_suggestions = {
                k: v for k, v in suggestions.items() if v["status"] == status
            }
        else:
            filtered_suggestions = suggestions
        
        if not filtered_suggestions:
            await ctx.send(_("No suggestions found with that status."))
            return
        
        # Create list output
        entries = []
        
        for suggestion_id, data in sorted(filtered_suggestions.items(), key=lambda x: int(x[0])):
            author = ctx.guild.get_member(data["author_id"])
            author_name = author.display_name if author else _("Unknown User")
            
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "denied": "❌"
            }.get(data["status"], "❓")
            
            # Truncate content if too long
            content = data["content"]
            if len(content) > 60:
                content = content[:57] + "..."
            
            entries.append(
                f"`{suggestion_id}` {status_emoji} {content} - *{author_name}*"
            )
        
        # Send paginated output
        for page in pagify("\n".join(entries), page_length=1000):
            embed = discord.Embed(
                title=_("Suggestions"),
                description=page,
                color=await ctx.embed_color()
            )
            
            if status:
                embed.set_footer(text=_("Filtered by status: {status}").format(status=status))
                
            await ctx.send(embed=embed)
