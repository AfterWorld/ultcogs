import discord
from discord.ui import View, Button, Modal, TextInput, Select
from typing import Optional, Dict
import logging

from .constants import COLORS
from .utils import make_embed

log = logging.getLogger("red.suggestions.views")

# === Suggestion Modal ===

class SuggestionModal(Modal):
    def __init__(self, cog, category_id: Optional[str] = None, category_name: Optional[str] = None):
        title = f"Submit Suggestion - {category_name}" if category_name else "Submit Suggestion"
        super().__init__(title=title, timeout=300)
        self.cog = cog
        self.category_id = category_id

        self.suggestion = TextInput(
            label="Your Suggestion",
            placeholder="Describe your suggestion in detail...",
            style=discord.TextStyle.long,
            max_length=1000,
            required=True,
        )
        self.add_item(self.suggestion)

        self.reason = TextInput(
            label="Reason/Justification (Optional)",
            placeholder="Why should this be implemented?",
            style=discord.TextStyle.long,
            max_length=500,
            required=False,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.cog.process_suggestion_submission(
                interaction,
                self.suggestion.value,
                self.reason.value or None,
                self.category_id
            )
        except Exception as e:
            log.exception("Failed during suggestion submission")
            await interaction.response.send_message(
                "An error occurred while submitting your suggestion.",
                ephemeral=True,
            )


# === Category Selection ===

class CategorySelect(Select):
    def __init__(self, cog, categories: Dict[str, str]):
        options = [
            discord.SelectOption(label="General", value="general", emoji="💡", description="General suggestions")
        ]
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
        selected = self.values[0]
        try:
            if selected == "general":
                await interaction.response.send_modal(SuggestionModal(self.cog, None, None))
            else:
                name = self.categories.get(selected)
                await interaction.response.send_modal(SuggestionModal(self.cog, selected, name))
        except Exception as e:
            log.exception("Failed to show category modal")
            try:
                await interaction.response.send_message(
                    "Failed to open the suggestion form.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                pass


class CategoryView(View):
    def __init__(self, cog, categories: Dict[str, str]):
        super().__init__(timeout=300)
        self.add_item(CategorySelect(cog, categories))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        log.exception("Error in CategoryView")
        try:
            await interaction.response.send_message("An error occurred in the category view.", ephemeral=True)
        except discord.HTTPException:
            pass


# === Simple Modal Launch Button ===

class LaunchModalButton(View):
    def __init__(self, cog):
        super().__init__(timeout=300)
        self.cog = cog

    @discord.ui.button(label="Submit Suggestion", style=discord.ButtonStyle.primary)
    async def launch(self, button: Button, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(SuggestionModal(self.cog))
        except Exception as e:
            log.exception("Failed to launch SuggestionModal")
            try:
                await interaction.response.send_message("Failed to open suggestion form.", ephemeral=True)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        log.exception("Error in LaunchModalButton View")
        try:
            await interaction.response.send_message("An error occurred in the button view.", ephemeral=True)
        except discord.HTTPException:
            pass
