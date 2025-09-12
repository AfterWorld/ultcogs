# enhanced_suggestions.py

import discord
import asyncio
import time
import logging
from datetime import datetime, timedelta
from redbot.core import commands, Config, checks, bank
from redbot.core.utils.chat_formatting import humanize_number, humanize_timedelta
from typing import Optional, Dict, Any, List, Union
from discord.ui import View, Button, Modal, TextInput, Select

log = logging.getLogger("red.cogs.enhanced_suggestions")

DEFAULT_CONFIG = {
    "suggestion_channel": None,
    "cooldown": 300,
    "staff_channel": None,
    "log_channel": None,
    "auto_approve_threshold": 10,
    "auto_deny_threshold": -5,
    "suggestions": {},
    "next_id": 1,
    "voting_roles": [],        # role IDs allowed to vote
    "suggestion_roles": [],     # role IDs allowed to suggest
    "anonymous_suggestions": False,
    "require_reason": True,
    "max_suggestion_length": 1000,
    "reward_credits": 0,
    "categories": {},          # key: category_id, value: category_name
    "blacklisted_words": [],
    "dm_notifications": True,
    "thread_suggestions": False,
    "reaction_voting": False,
    "vote_weight": {},         # role_id: weight
    "suggestion_queue": False,  # if True, suggestions go to staff_channel for approval
}

COLORS = {
    "pending": 0x3498DB,
    "approved": 0x27AE60,
    "denied": 0xE74C3C,
    "implemented": 0x9B59B6,
    "considering": 0xF39C12,
    "duplicate": 0x95A5A6,
    "error": 0xE74C3C,
    "success": 0x2ECC71,
    "warning": 0xE67E22,
    "info": 0x3498DB
}

STATUS_EMOJIS = {
    "pending": "⏳",
    "approved": "✅",
    "denied": "❌",
    "implemented": "🎉",
    "considering": "🤔",
    "duplicate": "🔄"
}

class SuggestionModal(Modal):
    def __init__(self, cog, category_id: Optional[str] = None, category_name: Optional[str] = None):
        title = f"Submit Suggestion - {category_name}" if category_name else "Submit Suggestion"
        super().__init__(title=title, timeout=300)
        self.cog = cog
        self.category_id = category_id

    suggestion = TextInput(
        label="Your Suggestion",
        placeholder="Describe your suggestion in detail...",
        style=discord.TextStyle.long,
        max_length=DEFAULT_CONFIG["max_suggestion_length"],
        required=True
    )

    reason = TextInput(
        label="Reason/Justification (Optional)",
        placeholder="Why should this be implemented?",
        style=discord.TextStyle.long,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.process_suggestion_submission(
            interaction,
            self.suggestion.value,
            self.reason.value or None,
            self.category_id
        )

class CategorySelect(Select):
    def __init__(self, cog, categories: Dict[str, str]):
        options = [
            discord.SelectOption(
                label="General",
                value="general",
                description="General suggestions",
                emoji="💡"
            )
        ]
        # Limit total to 25
        for cat_id, cat_name in list(categories.items())[:24]:
            options.append(discord.SelectOption(
                label=cat_name[:100],
                value=cat_id,
                description=f"Submit to {cat_name}"[:100]
            ))
        super().__init__(placeholder="Choose a category...", options=options)
        self.cog = cog
        self.categories = categories

    async def callback(self, interaction: discord.Interaction):
        # When user picks a category, show modal
        selected = self.values[0]
        if selected == "general":
            await interaction.response.send_modal(SuggestionModal(self.cog, None, None))
        else:
            name = self.categories.get(selected, None)
            await interaction.response.send_modal(SuggestionModal(self.cog, selected, name))

class CategoryView(View):
    def __init__(self, cog, categories: Dict[str, str]):
        super().__init__(timeout=300)
        self.cog = cog
        self.add_item(CategorySelect(cog, categories))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class EnhancedSuggestionVotingView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        emoji="👍",
        style=discord.ButtonStyle.success,
        custom_id="suggestion_vote:upvote"
    )
    async def upvote(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "upvote")

    @discord.ui.button(
        emoji="👎",
        style=discord.ButtonStyle.danger,
        custom_id="suggestion_vote:downvote"
    )
    async def downvote(self, interaction: discord.Interaction, button: Button):
        await self.handle_vote(interaction, "downvote")

    @discord.ui.button(
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="suggestion_vote:voters",
        label="Voters"
    )
    async def show_voters(self, interaction: discord.Interaction, button: Button):
        await self._show_voters(interaction)

    async def _show_voters(self, interaction: discord.Interaction):
        suggestion_id = await self._extract_suggestion_id(interaction)
        if not suggestion_id:
            return await interaction.response.send_message("❌ Could not find suggestion ID.", ephemeral=True)
        suggestions = await self.cog.config.guild(interaction.guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        if not suggestion:
            return await interaction.response.send_message("❌ Suggestion not found.", ephemeral=True)

        upvoters = suggestion.get("upvotes", [])
        downvoters = suggestion.get("downvotes", [])

        embed = discord.Embed(
            title=f"📊 Voters for Suggestion #{suggestion_id}",
            color=COLORS["info"]
        )
        if upvoters:
            up_list = []
            for uid in upvoters[:15]:
                m = interaction.guild.get_member(uid)
                up_list.append(m.display_name if m else f"Unknown User")
            text = ", ".join(up_list)
            if len(upvoters) > 15:
                text += f"\n... and {len(upvoters) - 15} more"
            embed.add_field(name=f"👍 Upvotes ({len(upvoters)})", value=text, inline=False)
        if downvoters:
            down_list = []
            for uid in downvoters[:15]:
                m = interaction.guild.get_member(uid)
                down_list.append(m.display_name if m else f"Unknown User")
            text = ", ".join(down_list)
            if len(downvoters) > 15:
                text += f"\n... and {len(downvoters) - 15} more"
            embed.add_field(name=f"👎 Downvotes ({len(downvoters)})", value=text, inline=False)
        if not upvoters and not downvoters:
            embed.description = "No votes yet!"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _extract_suggestion_id(self, interaction: discord.Interaction) -> Optional[int]:
        if not interaction.message.embeds:
            return None
        embed = interaction.message.embeds[0]
        if embed.footer and embed.footer.text:
            try:
                txt = embed.footer.text
                if "ID:" in txt:
                    # e.g. "ID: 123 • Submitted by Name"
                    part = txt.split("ID:")[-1].strip()
                    first = part.split()[0]
                    return int(first)
            except (ValueError, IndexError):
                pass
        return None

    async def handle_vote(self, interaction: discord.Interaction, vote_type: str):
        await interaction.response.defer(ephemeral=True)
        suggestion_id = await self._extract_suggestion_id(interaction)
        if not suggestion_id:
            return await interaction.followup.send("❌ Unable to find suggestion ID.", ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        settings = await self.cog.config.guild(guild).all()
        suggestions = settings.get("suggestions", {})
        suggestion = suggestions.get(str(suggestion_id))
        if not suggestion:
            return await interaction.followup.send("❌ Suggestion not found.", ephemeral=True)

        # Voting role check
        voting_roles = settings.get("voting_roles", [])
        if voting_roles and not any(r.id in voting_roles for r in user.roles):
            return await interaction.followup.send("❌ You don't have permission to vote.", ephemeral=True)

        # Self vote prevention if not anonymous
        if not settings.get("anonymous_suggestions", False) and user.id == suggestion.get("author_id"):
            return await interaction.followup.send("❌ You cannot vote on your own suggestion.", ephemeral=True)

        # Only pending suggestions accept votes
        if suggestion.get("status", "pending") != "pending":
            return await interaction.followup.send("❌ This suggestion is no longer accepting votes.", ephemeral=True)

        result = await self._process_vote(suggestion, user.id, vote_type, settings)

        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)

        await self._update_voting_message(interaction, suggestion, suggestion_id, settings, guild)

        await interaction.followup.send(f"✅ You {result['action']} suggestion #{suggestion_id}!", ephemeral=True)

    async def _process_vote(self, suggestion: Dict, user_id: int, vote_type: str, settings: Dict) -> Dict[str, Any]:
        up = set(suggestion.get("upvotes", []))
        down = set(suggestion.get("downvotes", []))

        # role-weighted votes
        vote_weight = 1
        vw: Dict[str, int] = settings.get("vote_weight", {})
        for role in settings.get("vote_weight", {}).keys():
            # role is stored as string or int? assume int role_id
            rid = int(role)
            if any(r.id == rid for r in (suggestion.get("author_roles", []) or [])):
                vote_weight = vw.get(role, 1)
                break

        if vote_type == "upvote":
            if user_id in up:
                up.remove(user_id)
                action = "removed your upvote from"
            else:
                up.add(user_id)
                down.discard(user_id)
                action = "upvoted"
        else:  # downvote
            if user_id in down:
                down.remove(user_id)
                action = "removed your downvote from"
            else:
                down.add(user_id)
                up.discard(user_id)
                action = "downvoted"

        suggestion["upvotes"] = list(up)
        suggestion["downvotes"] = list(down)

        vh = suggestion.get("vote_history", [])
        vh.append({
            "user_id": user_id,
            "action": vote_type if user_id in (up if vote_type == "upvote" else down) else f"remove_{vote_type}",
            "timestamp": int(time.time())
        })
        suggestion["vote_history"] = vh[-50:]

        return {
            "action": action,
            "upvotes": len(up),
            "downvotes": len(down)
        }

    async def _update_voting_message(self, interaction: discord.Interaction,
                                     suggestion: Dict, suggestion_id: int,
                                     settings: Dict, guild: discord.Guild):
        up = len(suggestion.get("upvotes", []))
        down = len(suggestion.get("downvotes", []))
        score = up - down

        embed = interaction.message.embeds[0].copy()
        embed.set_footer(text=f"ID: {suggestion_id} • 👍 {up} | 👎 {down} | Score: {score:+d}")

        auto_ap = settings.get("auto_approve_threshold", 10)
        auto_dn = settings.get("auto_deny_threshold", -5)
        if auto_ap is not None and score >= auto_ap:
            await self._auto_change_status(interaction, suggestion_id, "approved", f"Auto‑approved at score {score:+d}")
            return
        if auto_dn is not None and score <= auto_dn:
            await self._auto_change_status(interaction, suggestion_id, "denied", f"Auto‑denied at score {score:+d}")
            return

        await interaction.edit_original_response(embed=embed, view=self)

    async def _auto_change_status(self, interaction: discord.Interaction,
                                  suggestion_id: int, status: str, reason: str):
        guild = interaction.guild
        suggestions = await self.cog.config.guild(guild).suggestions()
        suggestion = suggestions.get(str(suggestion_id))
        if not suggestion:
            return
        suggestion["status"] = status
        suggestion["approved_by"] = "System"
        suggestion["reason"] = reason
        suggestion["reviewed_at"] = int(time.time())
        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)

        embed = interaction.message.embeds[0].copy()
        embed.color = COLORS.get(status, COLORS["info"])
        embed.title = f"{STATUS_EMOJIS.get(status, '')} {status.title()} Suggestion"
        embed.add_field(name="Status", value=reason, inline=False)

        await interaction.edit_original_response(embed=embed, view=None)

        await self.cog.log_action(guild, suggestion_id, status, "System", reason)
        await self.cog.notify_user(guild, suggestion, status, reason)
        # Optionally update original message record etc.

class StaffReasonModal(Modal):
    def __init__(self, callback_func, action: str):
        super().__init__(title=f"Provide Reason - {action.title()}", timeout=300)
        self.callback_func = callback_func

    reason = TextInput(
        label="Public Reason",
        placeholder="Reason shown to the user...",
        style=discord.TextStyle.long,
        required=True,
        max_length=500
    )

    notes = TextInput(
        label="Internal Notes (Optional)",
        placeholder="Staff-only notes...",
        style=discord.TextStyle.long,
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.reason.value, self.notes.value or None)

class EnhancedSuggestionStaffView(View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.select(
        placeholder="Change suggestion status...",
        options=[
            discord.SelectOption(label="✅ Approve", value="approved", emoji="✅"),
            discord.SelectOption(label="❌ Deny", value="denied", emoji="❌"),
            discord.SelectOption(label="🤔 Under Consideration", value="considering", emoji="🤔"),
            discord.SelectOption(label="🎉 Mark as Implemented", value="implemented", emoji="🎉"),
            discord.SelectOption(label="🔄 Mark as Duplicate", value="duplicate", emoji="🔄"),
        ],
        custom_id="suggestion_staff:status_change"
    )
    async def change_status(self, interaction: discord.Interaction, select: Select):
        new_status = select.values[0]
        if not await self.cog.check_staff_permissions(interaction.user, interaction.guild):
            return await interaction.response.send_message("❌ You don't have permission to use this.", ephemeral=True)
        settings = await self.cog.config.guild(interaction.guild).all()
        require = settings.get("require_reason", True)
        if require or new_status in ("denied", "duplicate"):
            modal = StaffReasonModal(lambda i, reason, notes: self._process_status_change(i, new_status, reason, notes), new_status)
            await interaction.response.send_modal(modal)
        else:
            # no reason required
            await self._process_status_change(interaction, new_status, f"Marked as {new_status} by staff", None)

    async def _process_status_change(self, interaction: discord.Interaction,
                                     status: str, reason: str, notes: Optional[str] = None):
        suggestion_id = await self._get_suggestion_id(interaction)
        if not suggestion_id:
            return await interaction.response.send_message("❌ Could not find suggestion ID.", ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        settings = await self.cog.config.guild(guild).all()
        suggestions = settings.get("suggestions", {})
        suggestion = suggestions.get(str(suggestion_id))
        if not suggestion:
            return await interaction.response.send_message("❌ Suggestion not found.", ephemeral=True)

        old_status = suggestion.get("status", "pending")
        suggestion["status"] = status
        suggestion["approved_by"] = f"{user.display_name} ({user.id})"
        suggestion["reason"] = reason
        suggestion["reviewed_at"] = int(time.time())
        if notes:
            suggestion["internal_notes"] = notes

        suggestions[str(suggestion_id)] = suggestion
        await self.cog.config.guild(guild).suggestions.set(suggestions)

        if status == "approved":
            await self.cog.award_credits(guild, suggestion)

        # Edit original message if possible
        await self.cog.update_original_message(guild, suggestion_id, status, user, reason)

        # Respond to interaction
        embed = interaction.message.embeds[0].copy()
        embed.color = COLORS.get(status, COLORS["info"])
        embed.title = f"{STATUS_EMOJIS.get(status, '')} {status.title()} Suggestion"
        self._update_embed_field(embed, "Status", f"{status.title()} by {user.display_name}")
        if reason:
            self._update_embed_field(embed, "Reason", reason)
        await interaction.response.edit_message(embed=embed, view=None)

        await self.cog.log_action(guild, suggestion_id, status, user, reason, old_status, notes)
        await self.cog.notify_user(guild, suggestion, status, reason)

    def _update_embed_field(self, embed: discord.Embed, name: str, value: str):
        for i, field in enumerate(embed.fields):
            if field.name == name:
                embed.set_field_at(i, name=name, value=value, inline=False)
                return
        embed.add_field(name=name, value=value, inline=False)

    async def _get_suggestion_id(self, interaction: discord.Interaction) -> Optional[int]:
        if not interaction.message.embeds:
            return None
        embed = interaction.message.embeds[0]
        if embed.footer and embed.footer.text:
            txt = embed.footer.text
            if "ID:" in txt:
                try:
                    return int(txt.split("ID:")[-1].split()[0])
                except (ValueError, IndexError):
                    pass
        # also check fields if needed
        for f in embed.fields:
            if f.name.lower() == "id" or "id:" in f.value.lower():
                digits = ''.join(filter(str.isdigit, f.value))
                if digits:
                    try:
                        return int(digits)
                    except:
                        pass
        return None

class EnhancedSuggestions(commands.Cog):
    """A comprehensive suggestion system with enhanced admin/config and summary."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=6969694201, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.user_cooldowns: Dict[tuple, int] = {}

    async def cog_load(self):
        self.bot.add_view(EnhancedSuggestionVotingView(self))
        self.bot.add_view(EnhancedSuggestionStaffView(self))
        log.info("EnhancedSuggestions cog loaded, persistent views added.")

    async def cog_unload(self):
        self.user_cooldowns.clear()

    async def red_delete_data_for_user(self, **kwargs):
        user_id = kwargs["user_id"]
        for guild_id, guild_data in (await self.config.all_guilds()).items():
            suggestions = guild_data.get("suggestions", {})
            modified = False
            for sid, sug in suggestions.items():
                if sug.get("author_id") == user_id:
                    sug["author_id"] = None
                    sug["author_name"] = "[Deleted User]"
                    modified = True
                if user_id in sug.get("upvotes", []):
                    sug["upvotes"].remove(user_id)
                    modified = True
                if user_id in sug.get("downvotes", []):
                    sug["downvotes"].remove(user_id)
                    modified = True
                vh = sug.get("vote_history", [])
                new_vh = [v for v in vh if v.get("user_id") != user_id]
                if len(new_vh) != len(vh):
                    sug["vote_history"] = new_vh
                    modified = True
            if modified:
                g = self.bot.get_guild(guild_id)
                if g:
                    await self.config.guild(g).suggestions.set(suggestions)

    # Utilities

    def make_embed(self, title: Optional[str] = None, description: Optional[str] = None,
                   color: str = "info") -> discord.Embed:
        return discord.Embed(
            title=title,
            description=description,
            color=COLORS.get(color, COLORS["info"])
        )

    def error_embed(self, description: str) -> discord.Embed:
        return self.make_embed(title="❌ Error", description=description, color="error")

    def success_embed(self, description: str) -> discord.Embed:
        return self.make_embed(title="✅ Success", description=description, color="success")

    async def check_staff_permissions(self, user: discord.Member, guild: discord.Guild) -> bool:
        if guild is None:
            return False
        return user.guild_permissions.manage_guild or user == guild.owner or await self.bot.is_owner(user)

    async def check_suggestion_permissions(self, user: discord.Member, guild: discord.Guild) -> bool:
        settings = await self.config.guild(guild).all()
        suggestion_roles = settings.get("suggestion_roles", [])
        if not suggestion_roles:
            return True
        return any(r.id in suggestion_roles for r in user.roles)

    async def check_blacklisted_words(self, text: str, guild: discord.Guild) -> List[str]:
        settings = await self.config.guild(guild).all()
        bl = settings.get("blacklisted_words", [])
        tl = text.lower()
        found = [w for w in bl if w.lower() in tl]
        return found

    async def log_action(self, guild: discord.Guild, suggestion_id: int, action: str,
                         user: Union[discord.Member, str], reason: Optional[str] = None,
                         old_status: Optional[str] = None, notes: Optional[str] = None):
        settings = await self.config.guild(guild).all()
        log_ch_id = settings.get("log_channel")
        if not log_ch_id:
            return
        log_ch = guild.get_channel(log_ch_id)
        if not log_ch:
            return

        embed = self.make_embed(title="📋 Suggestion Action Log", color="info")
        embed.add_field(name="Suggestion ID", value=f"#{suggestion_id}", inline=True)
        embed.add_field(name="Action", value=action.title(), inline=True)
        embed.add_field(name="Staff", value=str(user), inline=True)
        if old_status and old_status != action:
            embed.add_field(name="Status Change", value=f"{old_status} → {action}", inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason[:1024], inline=False)
        if notes:
            embed.add_field(name="Internal Notes", value=notes[:1024], inline=False)
        embed.timestamp = datetime.utcnow()
        try:
            await log_ch.send(embed=embed)
        except discord.Forbidden:
            log.warning(f"Cannot send to log channel {log_ch_id} in guild {guild.id}")

    async def notify_user(self, guild: discord.Guild, suggestion: Dict,
                          status: str, reason: Optional[str] = None):
        settings = await self.config.guild(guild).all()
        if not settings.get("dm_notifications", True):
            return
        author_id = suggestion.get("author_id")
        if not author_id:
            return
        user = guild.get_member(author_id) or self.bot.get_user(author_id)
        if not user:
            return
        embed = self.make_embed(
            title=f"📋 Your Suggestion Has Been {status.title()}",
            description=f"Your suggestion in **{guild.name}** has been {status}.",
            color=status if status in COLORS else COLORS["info"]
        )
        stext = suggestion.get("text", "Unknown")
        if len(stext) > 500:
            stext = stext[:497] + "..."
        embed.add_field(name="Your Suggestion", value=stext, inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason[:1024], inline=False)
        try:
            await user.send(embed=embed)
        except discord.Forbidden:
            pass

    async def award_credits(self, guild: discord.Guild, suggestion: Dict):
        settings = await self.config.guild(guild).all()
        reward = settings.get("reward_credits", 0)
        if reward <= 0:
            return
        author_id = suggestion.get("author_id")
        if not author_id:
            return
        author = guild.get_member(author_id)
        if not author:
            return
        try:
            await bank.deposit_credits(author, reward)
        except Exception as e:
            log.error(f"Failed to award credits: {e}")

    async def update_original_message(self, guild: discord.Guild, suggestion_id: int,
                                      status: str, user: discord.Member, reason: Optional[str]):
        settings = await self.config.guild(guild).all()
        suggestions = settings.get("suggestions", {})
        suggestion = suggestions.get(str(suggestion_id))
        if not suggestion:
            return
        msg_id = suggestion.get("message_id")
        ch_id = suggestion.get("channel_id")
        if not msg_id or not ch_id:
            return
        channel = guild.get_channel(ch_id)
        if not channel:
            return
        try:
            msg = await channel.fetch_message(msg_id)
        except discord.NotFound:
            return
        embed = msg.embeds[0].copy()
        embed.color = COLORS.get(status, COLORS["info"])
        embed.title = f"{STATUS_EMOJIS.get(status, '')} {status.title()} Suggestion"
        # update fields
        updated = False
        for i, field in enumerate(embed.fields):
            if field.name == "Status":
                embed.set_field_at(i, name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
                updated = True
                break
        if not updated:
            embed.add_field(name="Status", value=f"{status.title()} by {user.display_name}", inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        try:
            await msg.edit(embed=embed)
        except discord.Forbidden:
            pass

    # === Commands ===

    @commands.group(name="suggestconfig", invoke_without_command=True)
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig(self, ctx: commands.Context):
        """Configuration commands for suggestion system."""
        await ctx.send_help(ctx.command)

    @suggestconfig.command(name="setchannel")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel where suggestions are posted."""
        await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
        await ctx.send(embed=self.success_embed(f"Suggestion channel set to {channel.mention}"))

    @suggestconfig.command(name="setlogchannel")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setlogchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the log channel for actions."""
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(embed=self.success_embed(f"Log channel set to {channel.mention}"))

    @suggestconfig.command(name="setstaffchannel")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setstaffchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the staff channel (for queued suggestions or reviews)."""
        await self.config.guild(ctx.guild).staff_channel.set(channel.id)
        await ctx.send(embed=self.success_embed(f"Staff channel set to {channel.mention}"))

    @suggestconfig.command(name="setthresholds")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setthresholds(self, ctx: commands.Context, auto_approve: int, auto_deny: int):
        """Set auto‑approve and auto‑deny thresholds."""
        await self.config.guild(ctx.guild).auto_approve_threshold.set(auto_approve)
        await self.config.guild(ctx.guild).auto_deny_threshold.set(auto_deny)
        await ctx.send(embed=self.success_embed(f"Thresholds: auto‑approve ≥ {auto_approve}, auto‑deny ≤ {auto_deny}"))

    @suggestconfig.command(name="setcooldown")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setcooldown(self, ctx: commands.Context, seconds: int):
        """Set cooldown (seconds) between suggestions per user."""
        await self.config.guild(ctx.guild).cooldown.set(seconds)
        await ctx.send(embed=self.success_embed(f"Cooldown set to {seconds} seconds"))

    @suggestconfig.command(name="setreward")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setreward(self, ctx: commands.Context, credits: int):
        """Set how many bank credits are awarded for approved suggestions."""
        await self.config.guild(ctx.guild).reward_credits.set(credits)
        await ctx.send(embed=self.success_embed(f"Reward credits set to {credits}"))

    @suggestconfig.command(name="addcategory")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_addcategory(self, ctx: commands.Context, category_id: str, *, category_name: str):
        """Add a suggestion category."""
        cfg = await self.config.guild(ctx.guild).categories()
        if category_id in cfg:
            await ctx.send(embed=self.error_embed(f"Category `{category_id}` already exists."))
            return
        cfg[category_id] = category_name
        await self.config.guild(ctx.guild).categories.set(cfg)
        await ctx.send(embed=self.success_embed(f"Added category `{category_id}` → **{category_name}**"))

    @suggestconfig.command(name="removecategory")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_removecategory(self, ctx: commands.Context, category_id: str):
        """Remove a suggestion category."""
        cfg = await self.config.guild(ctx.guild).categories()
        if category_id not in cfg:
            await ctx.send(embed=self.error_embed(f"Category `{category_id}` does not exist."))
            return
        name = cfg.pop(category_id)
        await self.config.guild(ctx.guild).categories.set(cfg)
        await ctx.send(embed=self.success_embed(f"Removed category `{category_id}` → **{name}**"))

    @suggestconfig.command(name="setanonymous")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setanonymous(self, ctx: commands.Context, yesno: bool):
        """Toggle anonymous suggestions."""
        await self.config.guild(ctx.guild).anonymous_suggestions.set(yesno)
        await ctx.send(embed=self.success_embed(f"Anonymous suggestions: {'enabled' if yesno else 'disabled'}"))

    @suggestconfig.command(name="setreasonrequired")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setreasonrequired(self, ctx: commands.Context, yesno: bool):
        """Toggle whether staff must give a public reason on status change."""
        await self.config.guild(ctx.guild).require_reason.set(yesno)
        await ctx.send(embed=self.success_embed(f"Public reason on status change required: {'enabled' if yesno else 'disabled'}"))

    @suggestconfig.command(name="addblacklist")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_addblacklist(self, ctx: commands.Context, *, word: str):
        """Add a blacklisted word."""
        bl = await self.config.guild(ctx.guild).blacklisted_words()
        if word.lower() in (w.lower() for w in bl):
            await ctx.send(embed=self.error_embed(f"`{word}` is already blacklisted."))
            return
        bl.append(word)
        await self.config.guild(ctx.guild).blacklisted_words.set(bl)
        await ctx.send(embed=self.success_embed(f"Added `{word}` to blacklisted words."))

    @suggestconfig.command(name="removeblacklist")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_removeblacklist(self, ctx: commands.Context, *, word: str):
        """Remove a blacklisted word."""
        bl = await self.config.guild(ctx.guild).blacklisted_words()
        new = [w for w in bl if w.lower() != word.lower()]
        if len(new) == len(bl):
            await ctx.send(embed=self.error_embed(f"`{word}` is not blacklisted."))
            return
        await self.config.guild(ctx.guild).blacklisted_words.set(new)
        await ctx.send(embed=self.success_embed(f"Removed `{word}` from blacklisted words."))

    @suggestconfig.command(name="setsuggestorroles")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setsuggestorroles(self, ctx: commands.Context, *roles: discord.Role):
        """Set roles permitted to submit suggestions."""
        role_ids = [r.id for r in roles]
        await self.config.guild(ctx.guild).suggestion_roles.set(role_ids)
        roles_str = ", ".join(r.name for r in roles) if roles else "None (everyone allowed)"
        await ctx.send(embed=self.success_embed(f"Suggestion submit roles set: {roles_str}"))

    @suggestconfig.command(name="setvoteroles")
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig_setvoteroles(self, ctx: commands.Context, *roles: discord.Role):
        """Set roles permitted to vote."""
        role_ids = [r.id for r in roles]
        await self.config.guild(ctx.guild).voting_roles.set(role_ids)
        roles_str = ", ".join(r.name for r in roles) if roles else "None (everyone allowed)"
        await ctx.send(embed=self.success_embed(f"Voting roles set: {roles_str}"))

    @commands.command(name="suggest")
    @commands.guild_only()
    async def suggest(self, ctx: commands.Context):
        """Submit a suggestion."""
        guild = ctx.guild
        user = ctx.author
        now = int(time.time())
        settings = await self.config.guild(guild).all()

        cd = self.user_cooldowns.get((guild.id, user.id), 0)
        if now < cd:
            left = cd - now
            await ctx.send(embed=self.error_embed(f"You're on cooldown. Try again in {humanize_timedelta(timedelta(seconds=left))}"))
            return

        if not await self.check_suggestion_permissions(user, guild):
            await ctx.send(embed=self.error_embed("You're not allowed to submit suggestions."))
            return

        categories = settings.get("categories", {})
        if categories:
            view = CategoryView(self, categories)
            await ctx.send("Please select a category for your suggestion:", view=view)
        else:
            # Directly open modal
            # We need an interaction to send modal. If ctx is from message, we may not have interaction.
            # Red 3.5 supports Modals via app_commands; to use modal via text command, we need to convert.
            # One workaround: send a button that triggers modal, or fallback to asking text inputs.
            # Here: send a message with a button that, when clicked, opens the modal.

            # create a simple View with a button to launch modal
            class LaunchModalButton(View):
                @discord.ui.button(label="Submit Suggestion", style=discord.ButtonStyle.primary)
                async def launch(self_, button: Button, interaction: discord.Interaction):
                    await interaction.response.send_modal(SuggestionModal(self, None, None))

            await ctx.send("Click the button below to submit your suggestion:", view=LaunchModalButton())

        # set cooldown
        self.user_cooldowns[(guild.id, user.id)] = now + int(settings.get("cooldown", DEFAULT_CONFIG["cooldown"]))

    async def process_suggestion_submission(self, interaction: discord.Interaction, text: str, reason: Optional[str], category_id: Optional[str]):
        guild = interaction.guild
        user = interaction.user
        settings = await self.config.guild(guild).all()

        # max length check
        maxlen = settings.get("max_suggestion_length", DEFAULT_CONFIG["max_suggestion_length"])
        if len(text) > maxlen:
            return await interaction.response.send_message(
                embed=self.error_embed(f"Suggestion is too long (max {maxlen} characters)."),
                ephemeral=True
            )

        # blacklist check
        blacklisted = await self.check_blacklisted_words(text, guild)
        if blacklisted:
            return await interaction.response.send_message(
                embed=self.error_embed(f"Your suggestion contains blacklisted words: {', '.join(blacklisted)}"),
                ephemeral=True
            )

        suggestions = await self.config.guild(guild).suggestions()
        next_id = await self.config.guild(guild).next_id()
        await self.config.guild(guild).next_id.set(next_id + 1)

        author_id = user.id if not settings.get("anonymous_suggestions", False) else None
        author_name = user.display_name if not settings.get("anonymous_suggestions", False) else "Anonymous"

        suggestion_data: Dict[str, Any] = {
            "id": next_id,
            "author_id": author_id,
            "author_name": author_name,
            "text": text,
            "reason": reason,
            "status": "pending",
            "created_at": int(time.time()),
            "category": category_id or "general",
            "upvotes": [],
            "downvotes": [],
            "vote_history": [],
            "message_id": None,
            "channel_id": None
        }

        suggestions[str(next_id)] = suggestion_data
        await self.config.guild(guild).suggestions.set(suggestions)

        # Build embed
        embed = self.make_embed(
            title=f"💡 New Suggestion #{next_id}",
            description=text,
            color="pending"
        )
        embed.set_footer(text=f"ID: {next_id} • Submitted by {author_name}")
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        if category_id:
            cat_map = settings.get("categories", {})
            embed.add_field(name="Category", value=cat_map.get(category_id, category_id), inline=True)

        view = EnhancedSuggestionVotingView(self)
        staff_view = EnhancedSuggestionStaffView(self)

        suggestion_ch_id = settings.get("suggestion_channel")
        if not suggestion_ch_id:
            return await interaction.response.send_message(
                embed=self.error_embed("Suggestion channel not configured. Contact staff."),
                ephemeral=True
            )
        channel = guild.get_channel(suggestion_ch_id)
        if not channel:
            return await interaction.response.send_message(
                embed=self.error_embed("Suggestion channel not found."), ephemeral=True
            )

        msg = await channel.send(embed=embed, view=view)
        # attach staff view if staff should see it on message
        try:
            await msg.edit(view=staff_view)
        except Exception:
            pass

        # store message and channel
        suggestion_data["message_id"] = msg.id
        suggestion_data["channel_id"] = channel.id
        suggestions[str(next_id)] = suggestion_data
        await self.config.guild(guild).suggestions.set(suggestions)

        await interaction.response.send_message(
            embed=self.success_embed(f"Your suggestion has been submitted (ID: {next_id})."),
            ephemeral=True
        )

    @commands.command(name="suggestview")
    @commands.guild_only()
    async def suggestview(self, ctx: commands.Context, suggestion_id: int):
        """View a suggestion's details and current votes."""
        guild = ctx.guild
        settings = await self.config.guild(guild).all()
        suggestions = settings.get("suggestions", {})

        sug = suggestions.get(str(suggestion_id))
        if not sug:
            await ctx.send(embed=self.error_embed(f"Suggestion ID {suggestion_id} not found."))
            return

        up = len(sug.get("upvotes", []))
        down = len(sug.get("downvotes", []))
        score = up - down
        status = sug.get("status", "pending")

        embed = self.make_embed(
            title=f"Suggestion #{suggestion_id} • Status: {status.title()}",
            description=sug.get("text", "No content"),
            color=status
        )
        embed.add_field(name="Author", value=sug.get("author_name", "Unknown"), inline=True)
        embed.add_field(name="Score", value=f"👍 {up} / 👎 {down} = {score}", inline=True)
        if sug.get("reason"):
            embed.add_field(name="Reason", value=sug["reason"], inline=False)
        if sug.get("category"):
            cat = settings.get("categories", {})
            embed.add_field(name="Category", value=cat.get(sug["category"], sug["category"]), inline=True)

        await ctx.send(embed=embed)

