import asyncio
import discord
from .utils import vote_field, can_moderate

class SuggestionVotingView(discord.ui.View):
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = int(suggestion_id)

    def set_counts(self, up: int, down: int):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "upvote":
                    child.label = f"Upvote ({up})"
                elif child.custom_id == "downvote":
                    child.label = f"Downvote ({down})"

    async def _apply_vote(self, interaction: discord.Interaction, vote: str):
        guild = interaction.guild
        if not guild:
            return
        cfg = await self.cog.get_guild_config(guild)
        data = (cfg.get("suggestions") or {}).get(str(self.suggestion_id))
        if not data:
            return await interaction.response.send_message("❌ This suggestion no longer exists.", ephemeral=True)
        if data.get("status") != "pending":
            return await interaction.response.send_message("❌ This suggestion has already been processed.", ephemeral=True)
        if interaction.user.id == int(data.get("author_id", 0)):
            return await interaction.response.send_message("❌ You cannot vote on your own suggestion.", ephemeral=True)

        votes = data.setdefault("votes", {"upvotes": [], "downvotes": []})
        ups = set(int(x) for x in votes.get("upvotes", []))
        dns = set(int(x) for x in votes.get("downvotes", []))
        uid = int(interaction.user.id)

        if vote == "up":
            if uid in ups:
                ups.remove(uid); msg = "✅ Upvote removed."
            else:
                ups.add(uid); dns.discard(uid); msg = "✅ Upvoted!"
        else:
            if uid in dns:
                dns.remove(uid); msg = "✅ Downvote removed."
            else:
                dns.add(uid); ups.discard(uid); msg = "✅ Downvoted!"

        votes["upvotes"] = list(ups)
        votes["downvotes"] = list(dns)

        # persist votes
        async with self.cog.config.guild(guild).suggestions() as s:
            s[str(self.suggestion_id)]["votes"] = votes
        self.cog._cache.invalidate(guild.id)

        # update UI + embed
        upc, dnc = len(ups), len(dns)
        self.set_counts(upc, dnc)
        try:
            emb = interaction.message.embeds[0]
            if emb.fields:
                emb.set_field_at(0, name="Votes", value=vote_field(upc, dnc), inline=True)
            else:
                emb.add_field(name="Votes", value=vote_field(upc, dnc), inline=True)
            await interaction.message.edit(embed=emb, view=self)
        except Exception:
            pass

        await interaction.response.send_message(msg, ephemeral=True)

        # threshold forward
        if upc >= int(cfg.get("upvote_threshold", 5)) and not data.get("staff_message_id") and data.get("status") == "pending":
            await self.cog._forward_to_staff(guild, str(self.suggestion_id))

    @discord.ui.button(label="Upvote (0)", style=discord.ButtonStyle.green, emoji="👍", custom_id="upvote")
    async def _upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_vote(interaction, "up")

    @discord.ui.button(label="Downvote (0)", style=discord.ButtonStyle.red, emoji="👎", custom_id="downvote")
    async def _downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._apply_vote(interaction, "down")


class SuggestionStaffView(discord.ui.View):
    def __init__(self, cog, suggestion_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = int(suggestion_id)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅", custom_id="approve")
    async def _approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_moderate(self.cog, interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to manage suggestions.", ephemeral=True)
        await interaction.response.send_modal(ReasonModal(self.cog, self.suggestion_id, "approved", "Approval Reason"))

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌", custom_id="deny")
    async def _deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_moderate(self.cog, interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to manage suggestions.", ephemeral=True)
        await interaction.response.send_modal(ReasonModal(self.cog, self.suggestion_id, "denied", "Denial Reason"))


class ReasonModal(discord.ui.Modal):
    def __init__(self, cog, suggestion_id: int, action: str, title: str):
        super().__init__(title=title)
        self.cog = cog
        self.suggestion_id = int(suggestion_id)
        self.action = action

        self.reason = discord.ui.TextInput(
            label="Reason (optional)",
            placeholder="Add some context for the decision…",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # tiny shim ctx so we can reuse the cog method
        ctx = type("Shim", (), {"guild": interaction.guild, "author": interaction.user, "send": lambda *_a, **_k: None})()
        await self.cog._set_status(ctx, self.suggestion_id, self.action, self.reason.value or "", interaction=interaction)
