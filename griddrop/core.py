"""
core.py — GridDrop Red-DiscordBot Cog.

Owns:
  - RedBot Config schema (guild and user persistent data)
  - active_sessions: dict[channel_id, GameSession]  (volatile in-memory state)
  - The full game loop: start → broadcast → timer → lock → reveal → write scores
  - All slash/prefix commands

Command surface:
  [p]drop start          — begin a round in the current channel
  [p]drop stop           — admin: abort an active round
  [p]drop leaderboard    — guild scoreboard
  [p]drop setpack <id>   — admin: change the active World Pack
  [p]drop listpacks      — admin: list installed World Packs
  [p]drop reloadpack     — admin: evict and re-cache the active pack
  [p]drop settings       — admin: view current guild config
  [p]drop setdecay <f>   — admin: tune the scoring decay rate
  [p]drop settimer <s>   — admin: change round duration
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Optional

import discord
from redbot.core import Config, commands, checks
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

from .engine.math import rank_guesses, random_target, GRID_SIZE
from .engine.renderer import ImageEngine, shutdown_executor
from .engine.map_loader import MapLoader
from .models.session import GameSession, RoundPhase
from .models.coordinates import GridPoint
from .ui.views import MacroTargetingView
from .ui import embeds


# ---------------------------------------------------------------------------
# Config schema defaults
# ---------------------------------------------------------------------------

GUILD_DEFAULTS = {
    "active":       False,
    "decay_rate":   5.0,       # scoring curve steepness
    "default_pack": "earth",   # World Pack ID
    "max_score":    5000,
    "round_seconds": 60,
    "micro_mode":   True,
}

USER_DEFAULTS = {
    "total_score":      0,
    "games_played":     0,
    "perfect_drops":    0,
    "average_distance": 0.0,
}


class GridDrop(commands.Cog):
    """
    GeoGuessr-style location guessing game built natively for Discord.

    Players target coordinates on a map image using dropdowns.
    Supports pluggable World Packs for custom maps and communities.
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

        self.config = Config.get_conf(
            self,
            identifier=0x4752494444524F50,   # hex for "GRIDDROP"
            force_registration=True,
        )
        self.config.register_guild(**GUILD_DEFAULTS)
        self.config.register_user(**USER_DEFAULTS)

        # Volatile state — never persisted
        self.active_sessions: dict[int, GameSession] = {}

        # Shared engine instances
        self.image_engine = ImageEngine()
        self.map_loader = MapLoader(pack_dir=cog_data_path(self) / "packs")

    def cog_unload(self) -> None:
        """Clean up worker processes and cancel any hanging timers."""
        for session in self.active_sessions.values():
            session.cancel_timer()
        self.active_sessions.clear()
        shutdown_executor()

    # -----------------------------------------------------------------------
    # Command group
    # -----------------------------------------------------------------------

    @commands.group(name="drop", invoke_without_command=True)
    async def drop_group(self, ctx: commands.Context) -> None:
        """GridDrop — location guessing game. Use `[p]drop start` to begin."""
        await ctx.send_help(self.drop_group)

    # -----------------------------------------------------------------------
    # [p]drop start
    # -----------------------------------------------------------------------

    @drop_group.command(name="start")
    @commands.guild_only()
    async def drop_start(self, ctx: commands.Context) -> None:
        """Start a new GridDrop round in this channel."""
        channel_id = ctx.channel.id

        if channel_id in self.active_sessions:
            await ctx.send(embed=embeds.error(
                "Round Already Active",
                "There's already a round running in this channel. "
                "Wait for it to finish or use `[p]drop stop` to abort it."
            ))
            return

        # Load guild config
        cfg = await self.config.guild(ctx.guild).all()
        pack_id      = cfg["default_pack"]
        max_score    = cfg["max_score"]
        decay_rate   = cfg["decay_rate"]
        round_secs   = cfg["round_seconds"]
        micro_mode   = cfg["micro_mode"]

        # Load the World Pack (may be cached)
        try:
            pack = self.map_loader.load(pack_id)
        except FileNotFoundError:
            await ctx.send(embed=embeds.error(
                "Pack Not Found",
                f"World Pack `{pack_id}` could not be loaded. "
                f"Use `[p]drop listpacks` to see installed packs."
            ))
            return

        # Create session
        target  = random_target(pack.grid_size)
        session = GameSession(
            channel_id=channel_id,
            guild_id=ctx.guild.id,
            target=target,
            pack_name=pack.id,
            max_score=max_score,
            decay_rate=decay_rate,
            round_seconds=round_secs,
            micro_mode=micro_mode and pack.micro_mode,
        )
        session.phase = RoundPhase.MACRO
        self.active_sessions[channel_id] = session

        # Render macro grid
        macro_bytes = await self.image_engine.generate_macro_grid(pack.map_image)
        map_file    = discord.File(io.BytesIO(macro_bytes), filename="map.png")
        view        = MacroTargetingView(session, self.image_engine, pack.map_image)

        embed = embeds.round_start(session, pack.name)
        msg   = await ctx.send(embed=embed, file=map_file, view=view)
        session.message_id = msg.id

        # Start the countdown timer
        session.timer_task = asyncio.create_task(
            self._round_timer(ctx, session, view, pack.map_image, pack.name)
        )

    # -----------------------------------------------------------------------
    # [p]drop stop
    # -----------------------------------------------------------------------

    @drop_group.command(name="stop")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_stop(self, ctx: commands.Context) -> None:
        """Abort the active round in this channel (mod only)."""
        session = self.active_sessions.pop(ctx.channel.id, None)
        if session is None:
            await ctx.send("No active round in this channel.")
            return
        session.cancel_timer()
        await ctx.send("🛑 Round aborted.")

    # -----------------------------------------------------------------------
    # [p]drop leaderboard
    # -----------------------------------------------------------------------

    @drop_group.command(name="leaderboard", aliases=["lb"])
    @commands.guild_only()
    async def drop_leaderboard(self, ctx: commands.Context) -> None:
        """Show the guild's all-time GridDrop leaderboard."""
        all_user_data = await self.config.all_users()
        guild_member_ids = {m.id for m in ctx.guild.members}

        entries = [
            {"user_id": uid, **data}
            for uid, data in all_user_data.items()
            if uid in guild_member_ids and data["games_played"] > 0
        ]
        entries.sort(key=lambda e: -e["total_score"])

        await ctx.send(embed=embeds.leaderboard(ctx.guild.name, entries))

    # -----------------------------------------------------------------------
    # Admin commands
    # -----------------------------------------------------------------------

    @drop_group.command(name="setpack")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_setpack(self, ctx: commands.Context, pack_id: str) -> None:
        """Set the active World Pack for this server."""
        try:
            pack = self.map_loader.load(pack_id)
        except FileNotFoundError:
            await ctx.send(embed=embeds.error("Pack Not Found", f"No pack with ID `{pack_id}` found."))
            return
        await self.config.guild(ctx.guild).default_pack.set(pack_id)
        await ctx.send(f"✅ World Pack set to **{pack.name}** (`{pack_id}`).")

    @drop_group.command(name="listpacks")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_listpacks(self, ctx: commands.Context) -> None:
        """List all installed World Packs."""
        packs = self.map_loader.list_available()
        await ctx.send(embed=embeds.pack_list(packs))

    @drop_group.command(name="reloadpack")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_reloadpack(self, ctx: commands.Context) -> None:
        """Force-reload the active World Pack from disk (clears cache)."""
        pack_id = await self.config.guild(ctx.guild).default_pack()
        self.map_loader.evict(pack_id)
        try:
            pack = self.map_loader.load(pack_id)
            await ctx.send(f"✅ Reloaded **{pack.name}** v{pack.version}.")
        except FileNotFoundError:
            await ctx.send(embed=embeds.error("Reload Failed", f"Pack `{pack_id}` no longer found on disk."))

    @drop_group.command(name="setdecay")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_setdecay(self, ctx: commands.Context, value: float) -> None:
        """
        Set the score decay rate k (default 5.0).
        Higher k = harsher curve. Range: 1.0 – 20.0.
        """
        if not (1.0 <= value <= 20.0):
            await ctx.send("Decay rate must be between 1.0 and 20.0.")
            return
        await self.config.guild(ctx.guild).decay_rate.set(value)
        await ctx.send(f"✅ Decay rate set to **{value}**.")

    @drop_group.command(name="settimer")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_settimer(self, ctx: commands.Context, seconds: int) -> None:
        """Set the round duration in seconds (30 – 300)."""
        if not (30 <= seconds <= 300):
            await ctx.send("Timer must be between 30 and 300 seconds.")
            return
        await self.config.guild(ctx.guild).round_seconds.set(seconds)
        await ctx.send(f"✅ Round timer set to **{seconds}s**.")

    @drop_group.command(name="settings")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_guild=True)
    async def drop_settings(self, ctx: commands.Context) -> None:
        """Show current GridDrop settings for this server."""
        cfg = await self.config.guild(ctx.guild).all()
        e = discord.Embed(title="⚙️ GridDrop Settings", colour=0x2B2D31)
        for key, value in cfg.items():
            e.add_field(name=key, value=str(value), inline=True)
        await ctx.send(embed=e)

    # -----------------------------------------------------------------------
    # Game loop (internal)
    # -----------------------------------------------------------------------

    async def _round_timer(
        self,
        ctx: commands.Context,
        session: GameSession,
        view: MacroTargetingView,
        base_image_bytes: bytes,
        pack_name: str,
    ) -> None:
        """
        Async task that drives the round lifecycle:
        sleep → lock → render → reveal → write scores → cleanup.
        """
        try:
            await asyncio.sleep(session.round_seconds)
        except asyncio.CancelledError:
            return   # admin used [p]drop stop

        # --- Lock phase ---
        session.phase = RoundPhase.LOCKED
        view.disable_all()

        try:
            original_msg = await ctx.channel.fetch_message(session.message_id)
            map_file     = discord.File(io.BytesIO(base_image_bytes), filename="map.png")
            await original_msg.edit(embed=embeds.round_locked(session), attachments=[map_file], view=view)
        except (discord.NotFound, discord.HTTPException):
            pass   # message was deleted; continue to reveal anyway

        # --- Reveal phase ---
        session.phase = RoundPhase.RESOLVING

        locked = session.locked_guesses
        if not locked:
            await ctx.send("⏱️ Round ended with **no guesses**. Better luck next time!")
            self.active_sessions.pop(ctx.channel.id, None)
            return

        # Score everyone
        guess_pairs = [(g.user_id, g.resolved_point) for g in locked]
        ranked      = rank_guesses(
            guess_pairs,
            session.target,
            max_score=session.max_score,
            k=session.decay_rate,
        )

        # Update in-session scores for embeds
        for result in ranked:
            g = session.guesses[result["user_id"]]
            g.score    = result["score"]
            g.distance = result["distance"]

        # Render reveal composite
        reveal_bytes = await self.image_engine.generate_reveal(
            base_image_bytes,
            session.target,
            guess_pairs,
        )
        reveal_file = discord.File(io.BytesIO(reveal_bytes), filename="reveal.png")
        reveal_embed = embeds.reveal(session, ranked, session.target, pack_name)
        await ctx.send(embed=reveal_embed, file=reveal_file)

        # --- Persist scores ---
        session.phase = RoundPhase.COMPLETE
        await self._write_scores(ranked, session.target)

        # --- Cleanup ---
        self.active_sessions.pop(ctx.channel.id, None)

    async def _write_scores(
        self,
        ranked: list[dict],
        target: GridPoint,
    ) -> None:
        """Write round results to RedBot Config."""
        for result in ranked:
            uid  = result["user_id"]
            user = self.bot.get_user(uid)
            if user is None:
                continue

            async with self.config.user(user).all() as data:
                data["games_played"]  += 1
                data["total_score"]   += result["score"]

                if result["score"] >= 4999:
                    data["perfect_drops"] += 1

                # Running average of distances
                n = data["games_played"]
                prev_avg = data["average_distance"]
                data["average_distance"] = prev_avg + (result["distance"] - prev_avg) / n


# ---------------------------------------------------------------------------
# Cog setup (RedBot entry point)
# ---------------------------------------------------------------------------

async def setup(bot: Red) -> None:
    await bot.add_cog(GridDrop(bot))
