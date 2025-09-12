from __future__ import annotations

import discord
import logging

from redbot.core import commands, Config, checks, bank
from redbot.core.bot import Red
from typing import Optional, Dict, Any

from .constants import DEFAULT_CONFIG, COLORS, STATUS_EMOJIS
from .utils import make_embed, success_embed, error_embed
from .views import SuggestionModal, CategoryView, LaunchModalButton
from .integration import RewardSystem

log = logging.getLogger("red.suggestions")

class Suggestion(commands.Cog):
    """Submit and manage community suggestions with optional rewards."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9494949494, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.rewarder = RewardSystem(self)

    async def cog_load(self):
        log.info("Suggestion cog loaded.")

    # ========== Main Command ==========

    @commands.hybrid_command(name="suggest")
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context):
        """Submit a suggestion."""
        guild = ctx.guild
        settings = await self.config.guild(guild).all()
        categories = settings.get("categories", {})

        if categories:
            view = CategoryView(self, categories)
            await ctx.reply("Choose a category to submit your suggestion:", view=view)
        else:
            view = LaunchModalButton(self)
            await ctx.reply("Click below to open the suggestion form.", view=view)

    # ========== Processing Logic ==========

    async def process_suggestion_submission(
        self,
        interaction: discord.Interaction,
        suggestion_text: str,
        reason_text: Optional[str] = None,
        category_id: Optional[str] = None,
    ):
        guild = interaction.guild
        author = interaction.user
        settings = await self.config.guild(guild).all()
        suggestion_channel_id = settings.get("suggestion_channel")
        if not suggestion_channel_id:
            await interaction.response.send_message(
                embed=error_embed("No suggestion channel is set up. Ask an admin to run `[p]suggestconfig setchannel`."),
                ephemeral=True,
            )
            return

        # Basic validation
        if any(word.lower() in suggestion_text.lower() for word in settings.get("blacklisted_words", [])):
            await interaction.response.send_message(
                embed=error_embed("Your suggestion contains a blocked word. Please revise."),
                ephemeral=True,
            )
            return

        next_id = settings.get("next_id", 1)
        suggestion_id = next_id
        await self.config.guild(guild).next_id.set(suggestion_id + 1)

        embed = discord.Embed(
            title=f"{STATUS_EMOJIS['pending']} Suggestion #{suggestion_id}",
            description=suggestion_text[:2048],
            color=COLORS["pending"],
        )
        embed.add_field(name="Status", value="⏳ Pending", inline=True)
        if reason_text:
            embed.add_field(name="Reason", value=reason_text[:1024], inline=False)
        embed.set_footer(text=f"Submitted by {author.display_name}", icon_url=author.display_avatar.url)

        channel = guild.get_channel(suggestion_channel_id)
        if not channel:
            await interaction.response.send_message(
                embed=error_embed("Suggestion channel not found."),
                ephemeral=True,
            )
            return

        try:
            message = await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Missing permission to post in suggestion channel."),
                ephemeral=True,
            )
            return

        # Save to config
        suggestion_data = {
            "id": suggestion_id,
            "author_id": author.id,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "suggestion": suggestion_text,
            "reason": reason_text,
            "category": category_id,
            "status": "pending",
            "votes": [],
        }
        async with self.config.guild(guild).suggestions() as all_suggestions:
            all_suggestions[str(suggestion_id)] = suggestion_data

        await self.config.guild(guild).suggestions.set_raw(str(suggestion_id), value=suggestion_data)

        await interaction.response.send_message(
            embed=success_embed(f"Suggestion #{suggestion_id} submitted!"),
            ephemeral=True,
        )

        # Award credits if configured
        reward_amt = settings.get("reward_credits", 0)
        if reward_amt > 0:
            await self.rewarder.award(
                guild=guild,
                user_id=author.id,
                amount=reward_amt,
                suggestion_id=suggestion_id,
            )

    # ========== Admin Setup ==========

    @commands.group(name="suggestconfig", aliases=["suggestset"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def suggestconfig(self, ctx: commands.Context):
        """Configure the suggestion system."""
        pass

    @suggestconfig.command(name="setchannel")
    async def suggestconfig_setchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the suggestion output channel."""
        await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Suggestion channel set to {channel.mention}"))

    @suggestconfig.command(name="reward")
    async def suggestconfig_reward(self, ctx: commands.Context, credits: int):
        """Set the credit reward per suggestion."""
        await self.config.guild(ctx.guild).reward_credits.set(max(0, credits))
        await ctx.send(embed=success_embed(f"Suggestions will now reward `{credits}` credits/Beri."))

    @suggestconfig.command(name="usebericore")
    async def suggestconfig_usebericore(self, ctx: commands.Context, toggle: bool):
        """Enable or disable BeriCore integration for rewards."""
        await self.config.guild(ctx.guild).use_beri_core.set(toggle)
        await ctx.send(embed=success_embed(f"BeriCore integration {'enabled' if toggle else 'disabled'}."))

    # ========== Deletion Compliance ==========

    async def red_delete_data_for_user(self, **kwargs) -> dict[str, list[str]]:
        """Compliance for Red's `[p]gdpr`"""
        return {
            "guild": ["suggestions"],
            "user": ["author_id"]
        }
