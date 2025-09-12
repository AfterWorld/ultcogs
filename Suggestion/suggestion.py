# suggestion.py
import discord
import asyncio
import time
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import humanize_number
from typing import Optional, Dict, Any
from discord.ui import View, Button, Modal, TextInput

# Constants
DEFAULT_CONFIG = {
    "suggestion_channel": None,
    "cooldown": 300,  # 5 minutes
    "threshold": 3,
    "staff_channel": None,
    "auto_approve_threshold": 10,
    "suggestions": {},  # Store suggestion data
    "next_id": 1
}

EMBED_COLOR_OK = 0x2ECC71
EMBED_COLOR_WARN = 0xE67E22
EMBED_COLOR_ERR = 0xE74C3C
EMBED_COLOR_PENDING = 0x3498DB
EMBED_COLOR_APPROVED = 0x27AE60
EMBED_COLOR_DENIED = 0xE74C3C

class ReasonModal(Modal, title="Provide Reason"):
    def __init__(self, callback_func):
        super().__init__()
        self.callback_func = callback_func
        
    reason = TextInput(
        label="Reason",
        placeholder="Enter reason for this action...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.reason.value)

class SuggestionVotingView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        
    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.success, custom_id="persistent_view:suggestion_upvote")
    async def upvote(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "upvote")
        
    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.danger, custom_id="persistent_view:suggestion_downvote")
    async def downvote(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "downvote")
    
    async def handle_vote(self, interaction: discord.Interaction, vote_type: str):
        # Extract suggestion ID from embed footer or message
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if not embed or not embed.footer:
            return await interaction.response.send_message("❌ Unable to find suggestion ID.", ephemeral=True)
        
        footer_text = embed.footer.text
        try:
            # Extract ID from footer like "👍 5 | 👎 2 | ID: 123"
            suggestion_id = int(footer_text.split("ID: ")[-1])
        except (ValueError, IndexError):
            return await interaction.response.send_message("❌ Invalid suggestion format.", ephemeral=True)
        
        user_id = interaction.user.id
        guild = interaction.guild
        
        # Get suggestion data
        suggestions = await self.cog.config.guild(guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        
        if not suggestion:
            return await interaction.response.send_message("❌ Suggestion not found.", ephemeral=True)
            
        # Prevent author from voting on their own suggestion
        if user_id == suggestion.get("author_id"):
            return await interaction.response.send_message("❌ You cannot vote on your own suggestion.", ephemeral=True)
            
        # Handle vote logic
        upvotes = set(suggestion.get("upvotes", []))
        downvotes = set(suggestion.get("downvotes", []))
        
        if vote_type == "upvote":
            if user_id in upvotes:
                upvotes.remove(user_id)  # Remove upvote
                action = "removed your upvote"
            else:
                upvotes.add(user_id)
                downvotes.discard(user_id)  # Remove downvote if exists
                action = "upvoted"
        else:  # downvote
            if user_id in downvotes:
                downvotes.remove(user_id)  # Remove downvote
                action = "removed your downvote"
            else:
                downvotes.add(user_id)
                upvotes.discard(user_id)  # Remove upvote if exists
                action = "downvoted"
        
        # Update suggestion data
        suggestion["upvotes"] = list(upvotes)
        suggestion["downvotes"] = list(downvotes)
        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)
        
        # Update embed
        embed.set_footer(text=f"👍 {len(upvotes)} | 👎 {len(downvotes)} | ID: {suggestion_id}")
        
        # Check for auto-approval
        settings = await self.cog.config.guild(guild).all()
        threshold = settings.get("auto_approve_threshold", 10)
        
        if len(upvotes) >= threshold and suggestion.get("status") == "pending":
            suggestion["status"] = "approved"
            suggestion["approved_by"] = "Auto-approved"
            suggestions[str(suggestion_id)] = suggestion
            await self.cog.config.guild(guild).suggestions.set(suggestions)
            
            embed.color = EMBED_COLOR_APPROVED
            embed.title = "✅ Approved Suggestion"
            embed.add_field(name="Status", value="Auto-approved due to high votes", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Send ephemeral confirmation
        try:
            await interaction.followup.send(f"You {action} this suggestion!", ephemeral=True)
        except:
            pass

class SuggestionStaffView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        
    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green, custom_id="persistent_view:suggestion_approve")
    async def approve(self, interaction: discord.Interaction, button: Button):
        await self.handle_staff_action(interaction, "approved")
        
    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red, custom_id="persistent_view:suggestion_deny")
    async def deny(self, interaction: discord.Interaction, button: Button):
        modal = ReasonModal(self.handle_deny_with_reason)
        await interaction.response.send_modal(modal)
        
    async def get_suggestion_id(self, interaction: discord.Interaction):
        """Extract suggestion ID from the message"""
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        if not embed:
            return None
        
        # Try to get ID from embed description or fields
        description = embed.description or ""
        for field in embed.fields:
            if "ID:" in field.value or "ID #" in field.value:
                try:
                    return int(''.join(filter(str.isdigit, field.value)))
                except ValueError:
                    continue
        
        # Try to extract from description
        if "ID:" in description:
            try:
                return int(description.split("ID:")[-1].split()[0].strip())
            except ValueError:
                pass
        
        return None
        
    async def handle_staff_action(self, interaction: discord.Interaction, status: str):
        guild = interaction.guild
        user = interaction.user
        
        # Check permissions
        if not (user.guild_permissions.manage_guild or await self.cog.bot.is_owner(user)):
            return await interaction.response.send_message("❌ You don't have permission to use this.", ephemeral=True)
        
        suggestion_id = await self.get_suggestion_id(interaction)
        if not suggestion_id:
            return await interaction.response.send_message("❌ Could not find suggestion ID.", ephemeral=True)
        
        # Update suggestion
        suggestions = await self.cog.config.guild(guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        
        if not suggestion:
            return await interaction.response.send_message("❌ Suggestion not found.", ephemeral=True)
            
        suggestion["status"] = status
        suggestion["approved_by"] = f"{user.display_name} ({user.id})"
        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)
        
        # Update embed
        embed = interaction.message.embeds[0]
        embed.color = EMBED_COLOR_APPROVED if status == "approved" else EMBED_COLOR_DENIED
        embed.title = f"{'✅ Approved' if status == 'approved' else '❌ Denied'} Suggestion"
        
        # Update or add status field
        status_field_found = False
        for i, field in enumerate(embed.fields):
            if field.name.lower() == "status":
                embed.set_field_at(i, name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
                status_field_found = True
                break
        
        if not status_field_found:
            embed.add_field(name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Update original suggestion message if possible
        suggestion_channel_id = suggestion.get("channel_id")
        suggestion_message_id = suggestion.get("message_id")
        if suggestion_channel_id and suggestion_message_id:
            suggestion_channel = guild.get_channel(suggestion_channel_id)
            if suggestion_channel:
                try:
                    suggestion_message = await suggestion_channel.fetch_message(suggestion_message_id)
                    suggestion_embed = suggestion_message.embeds[0]
                    suggestion_embed.color = embed.color
                    suggestion_embed.title = embed.title
                    
                    # Add status field to original message
                    status_field_found = False
                    for i, field in enumerate(suggestion_embed.fields):
                        if field.name.lower() == "status":
                            suggestion_embed.set_field_at(i, name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
                            status_field_found = True
                            break
                    
                    if not status_field_found:
                        suggestion_embed.add_field(name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
                    
                    await suggestion_message.edit(embed=suggestion_embed, view=None)
                except (discord.NotFound, discord.Forbidden):
                    pass
    
    async def handle_deny_with_reason(self, interaction: discord.Interaction, reason: str):
        guild = interaction.guild
        user = interaction.user
        
        # Check permissions
        if not (user.guild_permissions.manage_guild or await self.cog.bot.is_owner(user)):
            return await interaction.followup.send("❌ You don't have permission to use this.", ephemeral=True)
        
        suggestion_id = await self.get_suggestion_id(interaction)
        if not suggestion_id:
            return await interaction.followup.send("❌ Could not find suggestion ID.", ephemeral=True)
        
        # Update suggestion
        suggestions = await self.cog.config.guild(guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        
        if not suggestion:
            return await interaction.followup.send("❌ Suggestion not found.", ephemeral=True)
            
        suggestion["status"] = "denied"
        suggestion["approved_by"] = f"{user.display_name} ({user.id})"
        suggestion["reason"] = reason
        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)
        
        # Update original message
        embed = interaction.message.embeds[0]
        embed.color = EMBED_COLOR_DENIED
        embed.title = "❌ Denied Suggestion"
        
        # Update or add fields
        status_field_found = False
        reason_field_found = False
        
        for i, field in enumerate(embed.fields):
            if field.name.lower() == "status":
                embed.set_field_at(i, name="Status", value=f"Denied by {user.display_name}", inline=False)
                status_field_found = True
            elif field.name.lower() == "reason":
                embed.set_field_at(i, name="Reason", value=reason, inline=False)
                reason_field_found = True
        
        if not status_field_found:
            embed.add_field(name="Status", value=f"Denied by {user.display_name}", inline=False)
        if not reason_field_found:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.edit_original_response(embed=embed, view=None)

class Suggestions(commands.Cog):
    """A comprehensive suggestion system with voting and staff approval."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6969696969, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.user_cooldowns = {}  # Simple in-memory cooldown tracking

    async def cog_load(self):
        # Add persistent views (without specific suggestion IDs)
        self.bot.add_view(SuggestionVotingView(self))
        self.bot.add_view(SuggestionStaffView(self))

    def make_embed(self, title: str = None, description: str = None, color: int = EMBED_COLOR_OK):
        return discord.Embed(title=title, description=description, color=color)

    def error_embed(self, description: str):
        return self.make_embed(title="❌ Error", description=description, color=EMBED_COLOR_ERR)

    @commands.guild_only()
    @commands.command(name="suggest")
    async def suggest(self, ctx: commands.Context, *, text: str):
        """Submit a suggestion to be voted on by the community."""
        if len(text) > 1000:
            return await ctx.send(embed=self.error_embed("Suggestion is too long. Maximum 1000 characters."))
        
        settings = await self.config.guild(ctx.guild).all()
        channel_id = settings.get("suggestion_channel")
        
        if not channel_id:
            return await ctx.send(embed=self.error_embed("No suggestion channel has been configured. Contact an administrator."))

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            return await ctx.send(embed=self.error_embed("The configured suggestion channel was not found."))

        # Check cooldown
        user_key = f"{ctx.guild.id}_{ctx.author.id}"
        cooldown = settings.get("cooldown", 300)
        current_time = time.time()
        
        if user_key in self.user_cooldowns:
            time_left = cooldown - (current_time - self.user_cooldowns[user_key])
            if time_left > 0:
                minutes, seconds = divmod(int(time_left), 60)
                return await ctx.send(embed=self.error_embed(f"Please wait {minutes}m {seconds}s before suggesting again."))

        # Create suggestion
        suggestion_id = settings.get("next_id", 1)
        
        embed = self.make_embed(
            title="💡 New Suggestion",
            description=text,
            color=EMBED_COLOR_PENDING
        )
        embed.set_footer(text=f"👍 0 | 👎 0 | ID: {suggestion_id}")
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        # Create views
        voting_view = SuggestionVotingView(self)
        staff_view = SuggestionStaffView(self)
        
        try:
            # Send to suggestion channel
            suggestion_msg = await channel.send(embed=embed, view=voting_view)
            
            # Store suggestion data
            suggestions = settings.get("suggestions", {})
            suggestions[str(suggestion_id)] = {
                "author_id": ctx.author.id,
                "text": text,
                "upvotes": [],
                "downvotes": [],
                "status": "pending",
                "message_id": suggestion_msg.id,
                "channel_id": channel.id,
                "created_at": current_time
            }
            
            await self.config.guild(ctx.guild).suggestions.set(suggestions)
            await self.config.guild(ctx.guild).next_id.set(suggestion_id + 1)
            
            # Send staff notification if configured
            staff_channel_id = settings.get("staff_channel")
            if staff_channel_id:
                staff_channel = ctx.guild.get_channel(staff_channel_id)
                if staff_channel:
                    staff_embed = self.make_embed(
                        title="📋 New Suggestion Requires Review",
                        description=f"**Author:** {ctx.author.mention}\n**Suggestion:** {text[:500]}{'...' if len(text) > 500 else ''}\n**ID:** {suggestion_id}",
                        color=EMBED_COLOR_PENDING
                    )
                    try:
                        await staff_channel.send(embed=staff_embed, view=staff_view)
                    except discord.Forbidden:
                        pass
            
            # Set cooldown
            self.user_cooldowns[user_key] = current_time
            
            await ctx.send(embed=self.make_embed(
                title="✅ Suggestion Submitted",
                description=f"Your suggestion has been posted in {channel.mention} with ID #{suggestion_id}",
                color=EMBED_COLOR_OK
            ))
            
        except discord.Forbidden:
            await ctx.send(embed=self.error_embed("I don't have permission to send messages in the suggestion channel."))
        except Exception as e:
            await ctx.send(embed=self.error_embed(f"An error occurred while posting your suggestion: {str(e)}"))

    @commands.guild_only()
    @commands.command(name="suggestion")
    async def view_suggestion(self, ctx: commands.Context, suggestion_id: int):
        """View details about a specific suggestion."""
        suggestions = await self.config.guild(ctx.guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        
        if not suggestion:
            return await ctx.send(embed=self.error_embed("Suggestion not found."))
        
        author = ctx.guild.get_member(suggestion["author_id"])
        author_name = author.display_name if author else "Unknown User"
        
        embed = self.make_embed(
            title=f"💡 Suggestion #{suggestion_id}",
            description=suggestion["text"],
            color=EMBED_COLOR_APPROVED if suggestion["status"] == "approved" 
                  else EMBED_COLOR_DENIED if suggestion["status"] == "denied" 
                  else EMBED_COLOR_PENDING
        )
        
        embed.add_field(name="Author", value=author_name, inline=True)
        embed.add_field(name="Status", value=suggestion["status"].title(), inline=True)
        embed.add_field(name="Votes", value=f"👍 {len(suggestion.get('upvotes', []))} | 👎 {len(suggestion.get('downvotes', []))}", inline=True)
        
        if suggestion.get("approved_by"):
            embed.add_field(name="Reviewed By", value=suggestion["approved_by"], inline=False)
            
        if suggestion.get("reason"):
            embed.add_field(name="Reason", value=suggestion["reason"], inline=False)
        
        await ctx.send(embed=embed)

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="suggestionset", aliases=["sugset"])
    async def suggestion_set(self, ctx: commands.Context):
        """Configure the suggestion system."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @suggestion_set.command(name="channel")
    async def set_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set the suggestion channel. Leave blank to disable."""
        if channel:
            await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description=f"Suggestion channel set to {channel.mention}"
            ))
        else:
            await self.config.guild(ctx.guild).suggestion_channel.set(None)
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description="Suggestion channel disabled"
            ))

    @suggestion_set.command(name="staffchannel")
    async def set_staff_channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set the staff notification channel for new suggestions."""
        if channel:
            await self.config.guild(ctx.guild).staff_channel.set(channel.id)
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description=f"Staff notification channel set to {channel.mention}"
            ))
        else:
            await self.config.guild(ctx.guild).staff_channel.set(None)
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description="Staff notification channel disabled"
            ))

    @suggestion_set.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, seconds: int):
        """Set the cooldown between suggestions in seconds."""
        if seconds < 0:
            return await ctx.send(embed=self.error_embed("Cooldown cannot be negative."))
        
        await self.config.guild(ctx.guild).cooldown.set(seconds)
        minutes, secs = divmod(seconds, 60)
        await ctx.send(embed=self.make_embed(
            title="✅ Configuration Updated",
            description=f"Suggestion cooldown set to {minutes}m {secs}s"
        ))

    @suggestion_set.command(name="autoapprove")
    async def set_auto_approve(self, ctx: commands.Context, threshold: int):
        """Set the vote threshold for auto-approval. Set to 0 to disable."""
        if threshold < 0:
            return await ctx.send(embed=self.error_embed("Threshold cannot be negative."))
        
        await self.config.guild(ctx.guild).auto_approve_threshold.set(threshold)
        if threshold == 0:
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description="Auto-approval disabled"
            ))
        else:
            await ctx.send(embed=self.make_embed(
                title="✅ Configuration Updated",
                description=f"Suggestions will be auto-approved at {threshold} upvotes"
            ))

    @suggestion_set.command(name="settings")
    async def view_settings(self, ctx: commands.Context):
        """View current suggestion system settings."""
        settings = await self.config.guild(ctx.guild).all()
        
        suggestion_channel = ctx.guild.get_channel(settings["suggestion_channel"]) if settings["suggestion_channel"] else None
        staff_channel = ctx.guild.get_channel(settings["staff_channel"]) if settings["staff_channel"] else None
        
        embed = self.make_embed(title="📋 Suggestion System Settings", color=EMBED_COLOR_OK)
        embed.add_field(
            name="Suggestion Channel", 
            value=suggestion_channel.mention if suggestion_channel else "Not set", 
            inline=False
        )
        embed.add_field(
            name="Staff Channel", 
            value=staff_channel.mention if staff_channel else "Not set", 
            inline=False
        )
        
        cooldown = settings["cooldown"]
        minutes, seconds = divmod(cooldown, 60)
        embed.add_field(name="Cooldown", value=f"{minutes}m {seconds}s", inline=True)
        embed.add_field(name="Auto-approve Threshold", value=str(settings["auto_approve_threshold"]), inline=True)
        embed.add_field(name="Total Suggestions", value=str(len(settings["suggestions"])), inline=True)
        
        await ctx.send(embed=embed)
