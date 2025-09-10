import discord
from datetime import datetime
from .utils import get_vote_field, get_embed_color, can_moderate_suggestions


class SuggestionVotingView(discord.ui.View):
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = suggestion_id

    def update_vote_counts(self, upvotes: int, downvotes: int):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "upvote":
                    item.label = f"Upvote ({upvotes})"
                elif item.custom_id == "downvote":
                    item.label = f"Downvote ({downvotes})"

    @discord.ui.button(label="Upvote (0)", style=discord.ButtonStyle.green, emoji="👍", custom_id="upvote")
    async def upvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "upvote")

    @discord.ui.button(label="Downvote (0)", style=discord.ButtonStyle.red, emoji="👎", custom_id="downvote")
    async def downvote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, "downvote")

    async def _handle_vote(self, interaction: discord.Interaction, vote_type: str):
        user_id = interaction.user.id
        guild = interaction.guild
        if not guild:
            return

        guild_config = await self.cog.get_guild_config(guild)
        suggestions = guild_config.get("suggestions", {})
        suggestion_data = suggestions.get(str(self.suggestion_id))

        if not suggestion_data:
            return await interaction.response.send_message("❌ This suggestion no longer exists.", ephemeral=True)

        if suggestion_data["status"] != "pending":
            return await interaction.response.send_message("❌ This suggestion has already been processed.", ephemeral=True)

        if user_id == suggestion_data["author_id"]:
            return await interaction.response.send_message("❌ You cannot vote on your own suggestion.", ephemeral=True)

        votes = suggestion_data.setdefault("votes", {"upvotes": [], "downvotes": []})
        upvoters = set(votes.get("upvotes", []))
        downvoters = set(votes.get("downvotes", []))

        if vote_type == "upvote":
            if user_id in upvoters:
                upvoters.remove(user_id)
                msg = "✅ Upvote removed."
            else:
                upvoters.add(user_id)
                downvoters.discard(user_id)
                msg = "✅ Upvoted!"
        else:
            if user_id in downvoters:
                downvoters.remove(user_id)
                msg = "✅ Downvote removed."
            else:
                downvoters.add(user_id)
                upvoters.discard(user_id)
                msg = "✅ Downvoted!"

        votes["upvotes"] = list(upvoters)
        votes["downvotes"] = list(downvoters)
        suggestion_data["votes"] = votes

        self.update_vote_counts(len(upvoters), len(downvoters))

        try:
            embed = interaction.message.embeds[0]
        except IndexError:
            return await interaction.response.send_message("Suggestion embed missing.", ephemeral=True)

        embed.set_field_at(0, name="Votes", value=get_vote_field(len(upvoters), len(downvoters)))
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(msg, ephemeral=True)

        async with self.cog.config.guild(guild).suggestions() as suggestions_config:
            suggestions_config[str(self.suggestion_id)]["votes"] = votes

        self.cog.cache.invalidate(guild.id)

        if (
            len(upvoters) >= guild_config["upvote_threshold"]
            and suggestion_data["status"] == "pending"
            and suggestion_data.get("staff_message_id") is None
        ):
            await self.cog._forward_to_staff(guild, str(self.suggestion_id), suggestion_data, len(upvoters))


class SuggestionStaffView(discord.ui.View):
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = suggestion_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅", custom_id="approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_moderate_suggestions(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to approve suggestions.", ephemeral=True)

        modal = ReasonModal(self.cog, self.suggestion_id, "approved", "Approval Reason")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌", custom_id="deny")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_moderate_suggestions(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to deny suggestions.", ephemeral=True)

        modal = ReasonModal(self.cog, self.suggestion_id, "denied", "Denial Reason")
        await interaction.response.send_modal(modal)


class ReasonModal(discord.ui.Modal):
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
        await interaction.response.defer(ephemeral=True)

        mock_ctx = type("MockContext", (), {
            "guild": interaction.guild,
            "author": interaction.user,
            "send": lambda msg=None, *, embed=None: interaction.followup.send(msg, embed=embed, ephemeral=True)
        })()
        await self.cog._update_suggestion_status(mock_ctx, self.suggestion_id, self.action, reason, interaction=interaction)
