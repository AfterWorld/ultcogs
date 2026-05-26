"""
chargen/mixin.py
─────────────────────────────────────────────────────────────────────────────
CharGenMixin — drop this into your OnePieceFruit cog's class definition.

Usage in core.py:
    from .chargen.mixin import CharGenMixin

    class OnePieceFruit(CharGenMixin, commands.Cog):
        ...

    # Inside __init__, alongside your existing register_guild call:
    self.config.register_member(character=None)

Config schema (per guild, per user):
    guild_id → user_id → "character" → OnePieceCharacter.to_dict()

Commands exposed:
    [p]rollchar          — Roll your permanent character (one-time per user per guild)
    [p]mychar            — View your own character sheet
    [p]charinfo @user    — View another user's character sheet
    [p]chardelete @user  — Admin: wipe a user's character (allows re-roll)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Optional

import discord
from redbot.core import commands

from .engine import WheelEngine
from .animator import CharacterAnimator
from .models import OnePieceCharacter

log = logging.getLogger("red.OnePieceFruit.chargen")


class CharGenMixin:
    """
    Mixin providing character generation commands for OnePieceFruit.

    Requires self.config to be a Red Config instance. Register the default
    key in the parent cog's __init__:

        self.config.register_member(character=None)

    If you already call register_member() with other keys, add character=None
    as an additional keyword argument — do not call it a second time.
    """

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_character(
        self, member: discord.Member
    ) -> Optional[OnePieceCharacter]:
        """Load a member's character from Config. Returns None if unset."""
        data = await self.config.member(member).character()
        if data is None:
            return None
        try:
            return OnePieceCharacter.from_dict(data)
        except Exception as exc:
            log.warning(
                "Failed to deserialize character for user=%s guild=%s: %s",
                member.id, member.guild.id, exc,
            )
            return None

    async def _save_character(
        self, member: discord.Member, character: OnePieceCharacter
    ) -> None:
        """Persist a character to Red Config."""
        await self.config.member(member).character.set(character.to_dict())

    async def _delete_character(self, member: discord.Member) -> None:
        """Wipe a member's character from Config."""
        await self.config.member(member).character.set(None)

    async def _send_character_sheet(
        self,
        ctx: commands.Context,
        character: OnePieceCharacter,
        target: discord.Member,
    ) -> None:
        """Send a static (non-animated) character sheet embed for [p]mychar / [p]charinfo."""
        embed = CharacterAnimator._build_final_embed(character)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_author(
            name=f"{target.display_name}'s Character Sheet",
            icon_url=target.display_avatar.url,
        )
        await ctx.send(embed=embed)

    # ── Commands ──────────────────────────────────────────────────────────────

    @commands.command(name="rollchar")
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def rollchar(self, ctx: commands.Context) -> None:
        """
        Roll your One Piece character sheet.
        This is a permanent, one-time roll per server. There are no re-rolls.
        """
        # Guard: already has a character in this guild
        existing = await self._get_character(ctx.author)
        if existing is not None:
            await ctx.send(
                f"⚓ **{ctx.author.display_name}**, your fate has already been decided.\n"
                f"Use `{ctx.prefix}mychar` to view your character sheet.",
                delete_after=12,
            )
            return

        # Confirmation gate — permanent action warning
        confirm_msg = await ctx.send(
            f"🏴‍☠️ **{ctx.author.display_name}**, you are about to receive your "
            f"**permanent** One Piece character sheet.\n\n"
            f"> ⚠️ **This cannot be undone.** The Grand Line grants no second chances.\n\n"
            f"React with ✅ to roll your fate, or ❌ to cancel.",
        )
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user.id == ctx.author.id
                and reaction.message.id == confirm_msg.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, _ = await ctx.bot.wait_for(
                "reaction_add", timeout=30.0, check=check
            )
        except asyncio.TimeoutError:
            with suppress(discord.HTTPException):
                await confirm_msg.delete()
            await ctx.send(
                f"⌛ Roll timed out, {ctx.author.mention}. "
                f"Run `{ctx.prefix}rollchar` again when you're ready.",
                delete_after=10,
            )
            return

        with suppress(discord.HTTPException):
            await confirm_msg.delete()

        if str(reaction.emoji) == "❌":
            await ctx.send(
                f"🌊 The sea waits for you, {ctx.author.mention}. "
                f"Come back when you're ready.",
                delete_after=10,
            )
            return

        # Generate instantly in memory — no I/O, no Discord calls yet
        character = WheelEngine.generate_character(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            display_name=ctx.author.display_name,
        )

        # Animate the reveal (~6.5s wall time, rate-limit safe)
        await CharacterAnimator.animate_roll(ctx, character)

        # Persist AFTER animation completes.
        # If the animation crashes mid-way, the user sees nothing and can re-roll.
        # If we saved first, a failed animation would lock them out permanently.
        await self._save_character(ctx.author, character)

        log.info(
            "Character generated — user=%s (%s) guild=%s (%s)",
            ctx.author.display_name, ctx.author.id,
            ctx.guild.name, ctx.guild.id,
        )

    @commands.command(name="mychar")
    @commands.guild_only()
    async def mychar(self, ctx: commands.Context) -> None:
        """View your One Piece character sheet."""
        character = await self._get_character(ctx.author)
        if character is None:
            await ctx.send(
                f"🌊 You haven't rolled your character yet, {ctx.author.mention}.\n"
                f"Use `{ctx.prefix}rollchar` to begin your journey.",
                delete_after=15,
            )
            return
        await self._send_character_sheet(ctx, character, ctx.author)

    @commands.command(name="charinfo")
    @commands.guild_only()
    async def charinfo(
        self, ctx: commands.Context, member: discord.Member
    ) -> None:
        """View another member's One Piece character sheet."""
        character = await self._get_character(member)
        if character is None:
            await ctx.send(
                f"🌊 **{member.display_name}** hasn't rolled their character yet.",
                delete_after=12,
            )
            return
        await self._send_character_sheet(ctx, character, member)

    @commands.command(name="chardelete")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def chardelete(
        self, ctx: commands.Context, member: discord.Member
    ) -> None:
        """
        [Admin] Delete a member's character sheet, allowing them to re-roll.
        Use only for corrections — characters are permanent by design.
        """
        character = await self._get_character(member)
        if character is None:
            await ctx.send(
                f"❌ **{member.display_name}** has no character on record in this server.",
                delete_after=10,
            )
            return

        await self._delete_character(member)
        await ctx.send(
            f"🗑️ Character sheet for **{member.display_name}** (`{member.id}`) "
            f"has been wiped by {ctx.author.mention}.\n"
            f"They may now use `{ctx.prefix}rollchar` again."
        )
        log.warning(
            "Character deleted — user=%s (%s) by admin=%s (%s) guild=%s",
            member.display_name, member.id,
            ctx.author.display_name, ctx.author.id,
            ctx.guild.id,
        )