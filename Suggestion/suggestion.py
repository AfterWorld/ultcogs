from __future__ import annotations

import discord
import logging
from redbot.core import commands, Config, checks, bank
from redbot.core.bot import Red
from typing import Optional

from .constants import DEFAULT_CONFIG, COLORS, STATUS_EMOJIS
from .utils import error_embed, success_embed
from .integration import RewardSystem

log = logging.getLogger("red.suggestions")

class Suggestion(commands.Cog):
    """Submit suggestions with voting + rewards."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9494949494, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.rewarder = RewardSystem(self)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context, *, suggestion_text: str):
        """Submit a suggestion (prefix only)."""
        guild = ctx.guild
        author = ctx.author
        settings = await self.config.guild(guild).all()

        suggestion_channel_id = settings.get("suggestion_channel")
        if not suggestion_channel_id:
            return await ctx.send(embed=error_embed("No suggestion channel is set."))

        if any(word.lower() in suggestion_text.lower() for word in settings.get("blacklisted_words", [])):
            return await ctx.send(embed=error_embed("Your suggestion contains a blocked word."))

        next_id = settings.get("next_id", 1)
        suggestion_id = next_id
        await self.config.guild(guild).next_id.set(suggestion_id + 1)

        embed = discord.Embed(
            title=f"{STATUS_EMOJIS['pending']} Suggestion #{suggestion_id}",
            description=suggestion_text[:2048],
            color=COLORS["pending"],
        )
        embed.add_field(name="Status", value="⏳ Pending", inline=True)
        embed.set_footer(text=f"Submitted by {author.display_name}", icon_url=author.display_avatar.url)

        channel = guild.get_channel(suggestion_channel_id)
        if not channel:
            return await ctx.send(embed=error_embed("Suggestion channel not found."))

        try:
            message = await channel.send(embed=embed)
            await message.add_reaction("👍")
            await message.add_reaction("👎")
        except discord.Forbidden:
            return await ctx.send(embed=error_embed("Missing permission to post or react."))

        suggestion_data = {
            "id": suggestion_id,
            "author_id": author.id,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "suggestion": suggestion_text,
            "status": "pending",
            "votes": [],
            "category": None,
            "reason": None,
        }

        await self.config.guild(guild).suggestions.set_raw(str(suggestion_id), value=suggestion_data)
        await ctx.send(embed=success_embed(f"Suggestion #{suggestion_id} submitted!"))

        reward_amt = settings.get("reward_credits", 0)
        if reward_amt > 0:
            await self.rewarder.award(guild=guild, user_id=author.id, amount=reward_amt, suggestion_id=suggestion_id)

    # === Reaction listener ===

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        emoji = str(payload.emoji)
        if emoji not in {"👍", "👎"}:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Match suggestion by message_id
        guild_cfg = self.config.guild(guild)
        all_suggestions = await guild_cfg.suggestions()
        for sid, data in all_suggestions.items():
            if data.get("message_id") == payload.message_id:
                break
        else:
            return

        if data.get("status") != "pending":
            return

        upvotes = 0
        downvotes = 0
        for r in message.reactions:
            if str(r.emoji) == "👍":
                upvotes = r.count
            elif str(r.emoji) == "👎":
                downvotes = r.count

        up_thresh = (await guild_cfg.upvote_threshold()) or 10
        down_thresh = (await guild_cfg.downvote_threshold()) or 5

        if upvotes >= up_thresh:
            await self._handle_approved(guild, message, sid, data)
        elif downvotes >= down_thresh:
            await self._handle_declined(guild, message, sid, data)

    async def _handle_approved(self, guild, message, sid, data):
        author = self.bot.get_user(data["author_id"])
        embed = message.embeds[0]
        embed.set_field_at(0, name="Status", value="✅ Approved", inline=True)
        embed.color = COLORS["approved"]
        embed.set_footer(text=f"Approved — Suggested by {author}", icon_url=author.display_avatar.url)
        await message.edit(embed=embed)

        staff_id = await self.config.guild(guild).staff_channel()
        if staff_id:
            staff_channel = guild.get_channel(staff_id)
            if staff_channel:
                await staff_channel.send(embed=embed)

        data["status"] = "approved"
        await self.config.guild(guild).suggestions.set_raw(str(sid), value=data)

    async def _handle_declined(self, guild, message, sid, data):
        author = self.bot.get_user(data["author_id"])
        embed = message.embeds[0]
        embed.set_field_at(0, name="Status", value="❌ Declined", inline=True)
        embed.color = COLORS["declined"]
        embed.set_footer(text=f"Declined — Suggested by {author}", icon_url=author.display_avatar.url)
        await message.edit(embed=embed)

        data["status"] = "declined"
        await self.config.guild(guild).suggestions.set_raw(str(sid), value=data)

    # === Admin Config ===

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

    @suggestconfig.command(name="setstaffchannel")
    async def suggestconfig_setstaffchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the staff approval output channel."""
        await self.config.guild(ctx.guild).staff_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Staff channel set to {channel.mention}"))

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

    @suggestconfig.command(name="setthresholds")
    async def suggestconfig_setthresholds(self, ctx: commands.Context, upvotes: int = 10, downvotes: int = 5):
        """Set upvote/downvote thresholds (default: 10/5)."""
        await self.config.guild(ctx.guild).upvote_threshold.set(upvotes)
        await self.config.guild(ctx.guild).downvote_threshold.set(downvotes)
        await ctx.send(embed=success_embed(f"Thresholds set: 👍 {upvotes} | 👎 {downvotes}"))
