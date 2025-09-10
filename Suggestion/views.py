import discord
from discord.ui import View, Button, Modal, TextInput
from .utils import make_embed
from .constants import EMBED_COLOR_OK

class ReasonModal(Modal, title="Reason"):
    def __init__(self, callback):
        super().__init__()
        self.callback_func = callback
        self.reason = TextInput(label="Reason", required=True)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.reason.value)

class SuggestionVotingView(View):
    def __init__(self, cog, suggestion_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = suggestion_id
        self.upvotes = set()
        self.downvotes = set()

        self.upvote_button = Button(label="👍", style=discord.ButtonStyle.success)
        self.downvote_button = Button(label="👎", style=discord.ButtonStyle.danger)

        self.upvote_button.callback = self.handle_upvote
        self.downvote_button.callback = self.handle_downvote

        self.add_item(self.upvote_button)
        self.add_item(self.downvote_button)

    async def handle_upvote(self, interaction: discord.Interaction):
        user = interaction.user
        self.downvotes.discard(user.id)
        self.upvotes.add(user.id)
        await self.update_message(interaction)

    async def handle_downvote(self, interaction: discord.Interaction):
        user = interaction.user
        self.upvotes.discard(user.id)
        self.downvotes.add(user.id)
        await self.update_message(interaction)

    async def update_message(self, interaction):
        embed = interaction.message.embeds[0]
        embed.set_footer(text=f"👍 {len(self.upvotes)} | 👎 {len(self.downvotes)}")
        await interaction.response.edit_message(embed=embed, view=self)

class SuggestionStaffView(View):
    def __init__(self, cog, suggestion_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.suggestion_id = suggestion_id

        self.approve_button = Button(label="✅ Approve", style=discord.ButtonStyle.green)
        self.deny_button = Button(label="❌ Deny", style=discord.ButtonStyle.red)

        self.approve_button.callback = self.approve
        self.deny_button.callback = self.deny

        self.add_item(self.approve_button)
        self.add_item(self.deny_button)

    async def approve(self, interaction: discord.Interaction):
        await interaction.response.send_message("Suggestion approved!", ephemeral=True)

    async def deny(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ReasonModal(self.send_denied_message))

    async def send_denied_message(self, interaction, reason):
        await interaction.response.send_message(f"Denied with reason: {reason}", ephemeral=True)
