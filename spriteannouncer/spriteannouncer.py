"""
SpriteAnnouncer Cog for Red-DiscordBot 3.5.x
=============================================
Rewritten for:
  - Red 3.5.22
  - discord.py 2.6.3
  - Python 3.11

Key changes from original:
  - Removed all self.bot.loop references (deprecated). Uses asyncio.create_task().
  - Replaced global on_interaction listener with a proper persistent discord.ui.View subclass.
  - Uses Red's built-in aiohttp session (self.bot.session) instead of a manually managed one.
  - Moved async initialization into cog_load() (Red 3.5+ async cog lifecycle).
  - Sprites are validated BEFORE being written to config (eliminates the rollback race condition).
  - Added a missing `topics add` (single-topic) command.
  - Character traits are now seeded deterministically from the character name so they stay
    consistent across interactions instead of randomizing every click.
  - Embed colors are now deterministic per character name for visual consistency.
  - The "New Topic" button edits the EXISTING message in-place rather than posting a second one.
  - GitHub rate-limit headers (X-RateLimit-Remaining / X-RateLimit-Reset) are now respected.
  - The background announcement loop reschedules itself on unexpected errors instead of silently dying.
  - All configuration mutations are logged.
  - FIXED: Added proper session availability checks to prevent AttributeError
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands as dpy_commands
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify

log = logging.getLogger("red.ultcogs.spriteannouncer")

# ---------------------------------------------------------------------------
# GitHub configuration – centralised so it's easy to swap repos.
# ---------------------------------------------------------------------------
GITHUB_REPO_OWNER = "AfterWorld"
GITHUB_REPO_NAME = "ultcogs"
GITHUB_API_CONTENTS = (
    f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
    "/contents/Character%20Sprite"
)
GITHUB_RAW_BASE = (
    f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
    "/main/Character%20Sprite/"
)

# Fallback sprite filenames used only when the GitHub API is completely unreachable.
DEFAULT_SPRITES: list[str] = [
    "cat_sprite.png",
    "dog_sprite.png",
    "ghost_sprite.png",
    "robot_sprite.png",
    "slime_sprite.png",
]

# ---------------------------------------------------------------------------
# Deterministic helpers – keep character appearance / traits stable across
# interactions so that clicking "Character Info" twice on the same sprite
# doesn't give contradictory answers.
# ---------------------------------------------------------------------------
_PERSONALITIES = [
    "Cheerful", "Thoughtful", "Curious", "Energetic",
    "Calm", "Witty", "Friendly", "Mysterious",
]
_HOBBIES = [
    "Reading", "Gaming", "Hiking", "Art",
    "Music", "Cooking", "Exploring", "Collecting",
]


def _seed_for_name(name: str) -> int:
    """Return a stable integer seed derived from a character name."""
    return int(hashlib.md5(name.encode()).hexdigest(), 16)


def _color_for_name(name: str) -> discord.Color:
    """Deterministic embed color based on character name."""
    seed = _seed_for_name(name)
    # Use lower 24 bits as an RGB value
    return discord.Color(seed & 0xFFFFFF)


def _traits_for_name(name: str) -> tuple[str, str]:
    """Return (personality, hobby) that are stable for a given character name."""
    rng = random.Random(_seed_for_name(name))
    return rng.choice(_PERSONALITIES), rng.choice(_HOBBIES)


def _character_name_from_filename(filename: str) -> str:
    """Extract a display name from a sprite filename, e.g. 'cat_sprite.png' → 'cat_sprite'."""
    return os.path.splitext(os.path.basename(filename))[0]


# ---------------------------------------------------------------------------
# Persistent View – survives bot restarts because Red re-adds it on cog load.
# ---------------------------------------------------------------------------
class AnnouncementView(discord.ui.View):
    """
    Buttons attached to every sprite announcement embed.

    ``persistent=True`` + ``timeout=None`` means Discord keeps these alive
    indefinitely.  The cog registers this view on load via
    ``bot.add_view(AnnouncementView(cog), message_id=...)``.
    Because we cannot know all live message IDs at restart time we register
    *without* a message_id, which makes it a catch-all for any interaction
    whose custom_id prefix matches.
    """

    def __init__(self, cog: SpriteAnnouncer):
        super().__init__(timeout=None)  # persistent views must have timeout=None
        self.cog = cog

    # ------------------------------------------------------------------
    # "New Topic" – admin only, edits message in place
    # ------------------------------------------------------------------
    @discord.ui.button(
        label="New Topic",
        style=discord.ButtonStyle.primary,
        custom_id="sprite_announcer:new_topic",
    )
    async def new_topic(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Permission gate – only guild administrators may regenerate.
        if (
            not interaction.guild
            or not interaction.user.guild_permissions.administrator  # type: ignore[union-attr]
        ):
            await interaction.response.send_message(
                "Only administrators can generate new topics.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        # Build a fresh embed reusing the same view (no new message).
        embed, sprite_name = await self.cog._build_announcement_embed(interaction.guild)
        if embed is None:
            await interaction.followup.send(
                "Could not generate a new topic right now.", ephemeral=True
            )
            return

        # Edit the original message in place.
        await interaction.message.edit(embed=embed, view=self)  # type: ignore[union-attr]
        await interaction.followup.send("Topic refreshed!", ephemeral=True)
        log.info("New topic generated via button by %s in guild %s", interaction.user, interaction.guild.id)

    # ------------------------------------------------------------------
    # "Character Info" – all users, ephemeral
    # ------------------------------------------------------------------
    @discord.ui.button(
        label="Character Info",
        style=discord.ButtonStyle.secondary,
        custom_id="sprite_announcer:character_info",
    )
    async def character_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.message or not interaction.message.embeds:
            await interaction.response.send_message(
                "Unable to find character information.", ephemeral=True
            )
            return

        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""

        # Footer is formatted as "Character: <name>"
        if not footer_text or not footer_text.startswith("Character: "):
            await interaction.response.send_message(
                "Character information not available.", ephemeral=True
            )
            return

        char_name = footer_text[len("Character: "):]
        personality, hobby = _traits_for_name(char_name)

        info_embed = discord.Embed(
            title=f"About {char_name}",
            description=f"{char_name} is one of the sprite characters who helps facilitate discussions!",
            color=_color_for_name(char_name),
        )
        if embed.thumbnail:
            info_embed.set_thumbnail(url=embed.thumbnail.url)

        info_embed.add_field(name="Personality", value=personality, inline=True)
        info_embed.add_field(name="Favourite Activity", value=hobby, inline=True)

        await interaction.response.send_message(embed=info_embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Main Cog
# ---------------------------------------------------------------------------
class SpriteAnnouncer(commands.Cog):
    """
    A topic / announcement cog that uses character sprites to create
    interactive discussions.

    Sprites are fetched from a public GitHub repository.  Topics and
    announcements are stored per-guild via Red's Config system.
    """

    # Config identifier – chosen arbitrarily; must never change after first use
    # or all existing guild data will become inaccessible.
    _CONF_ID = 5626721548

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(self, identifier=self._CONF_ID, force_registration=True)

        self.config.register_guild(
            enabled=False,
            channel_id=None,
            frequency={"min_minutes": 60, "max_minutes": 240},
            sprites_enabled=[],          # user-curated whitelist (empty = use all)
            topics=[],
            announcements=[],
            last_triggered=None,         # float timestamp
            next_trigger=None,           # float timestamp
        )

        # ---- in-memory caches (not persisted) ----
        self._sprite_url_cache: dict[str, str] = {}       # filename → validated raw URL
        self._github_sprites: list[str] = []              # filenames from the GitHub API
        self._github_sprites_fetched_at: float = 0.0      # epoch seconds
        self._github_rate_limit_reset: float = 0.0        # epoch seconds (from response headers)
        self._announcement_tasks: dict[int, asyncio.Task[None]] = {}  # guild_id → running task

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def cog_load(self) -> None:
        """Called by Red once after __init__, with the event loop already running."""
        # Register the persistent view so button interactions survive restarts.
        self.bot.add_view(AnnouncementView(self))

        # Prime the sprite cache from GitHub (only if session is available).
        await self._refresh_github_sprites()

        # Kick off timed tasks for every guild that already has the cog enabled.
        for guild in self.bot.guilds:
            data = await self.config.guild(guild).all()
            if data["enabled"] and data["channel_id"]:
                self._schedule_announcement(guild)

        log.info("SpriteAnnouncer cog loaded successfully.")

    def cog_unload(self) -> None:
        """Cancel every background task when the cog is unloaded."""
        for task in self._announcement_tasks.values():
            task.cancel()
        self._announcement_tasks.clear()

    # ------------------------------------------------------------------
    # GitHub sprite fetching
    # ------------------------------------------------------------------
    async def _refresh_github_sprites(self) -> list[str]:
        """
        Fetch the PNG file list from the GitHub repository.

        Respects the 1-hour local cache *and* GitHub's X-RateLimit-Reset
        header so we never hammer the API.
        """
        now = datetime.now(tz=timezone.utc).timestamp()

        # honour both the local 1-hour TTL and any GitHub-imposed reset time
        earliest_next = max(self._github_sprites_fetched_at + 3600, self._github_rate_limit_reset)
        if now < earliest_next and self._github_sprites:
            return self._github_sprites

        # Check if bot session is available
        if not hasattr(self.bot, 'session') or self.bot.session is None:
            log.warning("Bot session not available yet. Using cached sprites or defaults.")
            return self._github_sprites if self._github_sprites else DEFAULT_SPRITES

        try:
            async with self.bot.session.get(GITHUB_API_CONTENTS) as resp:
                # Always capture rate-limit headers, even on non-200
                reset_header = resp.headers.get("X-RateLimit-Reset")
                if reset_header:
                    self._github_rate_limit_reset = float(reset_header)

                remaining = resp.headers.get("X-RateLimit-Remaining", "60")
                if int(remaining) == 0:
                    log.warning(
                        "GitHub rate limit hit. Will retry after reset at %s",
                        self._github_rate_limit_reset,
                    )
                    return self._github_sprites

                if resp.status == 200:
                    data = await resp.json()
                    sprites = [item["name"] for item in data if item["name"].lower().endswith(".png")]
                    if sprites:
                        self._github_sprites = sprites
                        self._github_sprites_fetched_at = now
                        log.info("Refreshed GitHub sprites: %d files found.", len(sprites))
                    else:
                        log.warning("GitHub sprite directory exists but contains no PNG files.")
                elif resp.status == 403:
                    log.warning("GitHub API returned 403 – likely rate limited.")
                else:
                    log.error("GitHub API returned status %d.", resp.status)
        except Exception:
            log.exception("Error fetching sprites from GitHub.")

        return self._github_sprites if self._github_sprites else DEFAULT_SPRITES

    # ------------------------------------------------------------------
    # Sprite URL resolution
    # ------------------------------------------------------------------
    async def _resolve_sprite_url(self, sprite_name: str) -> Optional[str]:
        """
        Return a verified URL for *sprite_name*, or ``None`` if it cannot be reached.

        Full URLs (http/https) are passed through after a HEAD check.
        Plain filenames are resolved against the GitHub raw-content base URL.
        Results are cached for the lifetime of the cog.
        """
        # Already a full URL – still verify it.
        if sprite_name.startswith(("http://", "https://")):
            cache_key = sprite_name
            raw_url = sprite_name
        else:
            cache_key = sprite_name
            raw_url = f"{GITHUB_RAW_BASE}{sprite_name}"

        if cache_key in self._sprite_url_cache:
            return self._sprite_url_cache[cache_key]

        # Check if bot session is available
        if not hasattr(self.bot, 'session') or self.bot.session is None:
            log.warning("Bot session not available for sprite URL verification.")
            return None

        try:
            async with self.bot.session.head(raw_url) as resp:
                if resp.status == 200:
                    self._sprite_url_cache[cache_key] = raw_url
                    return raw_url
                log.warning("Sprite HEAD check failed for %s (status %d).", raw_url, resp.status)
        except Exception:
            log.exception("Error verifying sprite URL: %s", raw_url)

        return None

    # ------------------------------------------------------------------
    # Sprite list resolution (for a guild)
    # ------------------------------------------------------------------
    def _effective_sprites(self, guild_config: dict) -> list[str]:
        """
        Return the sprite list the guild should use, with fallback chain:
          1. User-enabled whitelist (if non-empty)
          2. All sprites from GitHub cache
          3. Hard-coded defaults
        """
        if guild_config["sprites_enabled"]:
            return list(guild_config["sprites_enabled"])
        if self._github_sprites:
            return list(self._github_sprites)
        return list(DEFAULT_SPRITES)

    # ------------------------------------------------------------------
    # Announcement construction
    # ------------------------------------------------------------------
    async def _build_announcement_embed(
        self, guild: discord.Guild
    ) -> tuple[Optional[discord.Embed], Optional[str]]:
        """
        Build a single announcement embed with a random sprite and topic/announcement.

        Returns ``(embed, sprite_filename)`` or ``(None, None)`` on failure.
        """
        guild_data = await self.config.guild(guild).all()
        sprites = self._effective_sprites(guild_data)
        topics: list[str] = guild_data["topics"]
        announcements: list[str] = guild_data["announcements"]

        # --- pick content ---
        if random.random() < 0.5 and topics:
            title, content = "Let's discuss…", random.choice(topics)
        elif announcements:
            title, content = "Announcement!", random.choice(announcements)
        elif topics:
            title, content = "Let's discuss…", random.choice(topics)
        else:
            title, content = "Let's chat!", "What's on your mind today?"

        # --- pick & validate sprite ---
        # Shuffle so we don't always retry the same broken sprite first.
        candidates = sprites.copy()
        random.shuffle(candidates)

        sprite_url: Optional[str] = None
        chosen_sprite: Optional[str] = None
        for candidate in candidates:
            url = await self._resolve_sprite_url(candidate)
            if url:
                sprite_url = url
                chosen_sprite = candidate
                break

        if sprite_url is None or chosen_sprite is None:
            log.error("No valid sprite URL could be resolved for guild %d.", guild.id)
            return None, None

        char_name = _character_name_from_filename(chosen_sprite)

        embed = discord.Embed(
            title=title,
            description=content,
            color=_color_for_name(char_name),
            timestamp=datetime.now(tz=timezone.utc),
        )
        embed.set_footer(text=f"Character: {char_name}")
        embed.set_thumbnail(url=sprite_url)

        return embed, chosen_sprite

    # ------------------------------------------------------------------
    # Sending announcements
    # ------------------------------------------------------------------
    async def _send_announcement(self, guild: discord.Guild) -> None:
        """Post a new announcement in the guild's configured channel."""
        guild_data = await self.config.guild(guild).all()
        channel = guild.get_channel(guild_data["channel_id"])  # type: ignore[arg-type]
        if not channel or not isinstance(channel, discord.TextChannel):
            log.warning("Announcement channel missing or not a TextChannel in guild %d.", guild.id)
            return

        embed, sprite = await self._build_announcement_embed(guild)
        if embed is None:
            return

        view = AnnouncementView(self)
        try:
            await channel.send(embed=embed, view=view)
            log.info("Sent announcement (sprite=%s) in guild %d.", sprite, guild.id)
        except discord.HTTPException:
            log.exception("Failed to send announcement in guild %d.", guild.id)

    # ------------------------------------------------------------------
    # Background scheduling
    # ------------------------------------------------------------------
    def _schedule_announcement(self, guild: discord.Guild) -> None:
        """Cancel any existing task for *guild* and start a new one."""
        if guild.id in self._announcement_tasks:
            self._announcement_tasks[guild.id].cancel()

        task = asyncio.create_task(self._announcement_loop(guild))
        self._announcement_tasks[guild.id] = task

    async def _announcement_loop(self, guild: discord.Guild) -> None:
        """
        Long-running loop: sleep → post → repeat.

        On unexpected errors it logs and reschedules rather than dying silently.
        """
        try:
            while True:
                guild_data = await self.config.guild(guild).all()

                if not guild_data["enabled"] or not guild_data["channel_id"]:
                    log.info("Announcement loop stopping for guild %d (disabled or no channel).", guild.id)
                    break

                # Verify channel still exists
                channel = guild.get_channel(guild_data["channel_id"])  # type: ignore[arg-type]
                if not channel:
                    log.warning("Channel gone in guild %d – disabling announcer.", guild.id)
                    await self.config.guild(guild).enabled.set(False)
                    break

                # --- determine sleep duration ---
                now = datetime.now(tz=timezone.utc).timestamp()
                next_trigger: Optional[float] = guild_data["next_trigger"]

                if next_trigger is None or now >= next_trigger:
                    # Pick a new random delay and persist it so a restart doesn't
                    # reset the countdown.
                    min_m = guild_data["frequency"]["min_minutes"]
                    max_m = guild_data["frequency"]["max_minutes"]
                    delay_seconds = random.randint(min_m, max_m) * 60
                    next_trigger = now + delay_seconds
                    await self.config.guild(guild).next_trigger.set(next_trigger)
                    wait = delay_seconds
                else:
                    wait = next_trigger - now

                log.debug("Guild %d: sleeping %.0fs until next announcement.", guild.id, wait)
                await asyncio.sleep(wait)

                # --- fire ---
                await self._send_announcement(guild)
                await self.config.guild(guild).next_trigger.set(None)
                await self.config.guild(guild).last_triggered.set(
                    datetime.now(tz=timezone.utc).timestamp()
                )

        except asyncio.CancelledError:
            log.debug("Announcement loop cancelled for guild %d.", guild.id)
        except Exception:
            log.exception("Unexpected error in announcement loop for guild %d – rescheduling.", guild.id)
            # Reschedule after a short back-off so we don't spin on a persistent error.
            await asyncio.sleep(60)
            self._schedule_announcement(guild)

    # ==================================================================
    # Commands
    # ==================================================================
    @commands.group(name="spriteannouncer", aliases=["sa"])
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def spriteannouncer(self, ctx: commands.Context):
        """Configure the Sprite Announcer."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    # ------------------------------------------------------------------
    # toggle
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="toggle")
    async def _toggle(self, ctx: commands.Context, enabled: Optional[bool] = None):
        """Enable or disable the sprite announcer.

        Usage: ``[p]sa toggle`` – show status
               ``[p]sa toggle true/false``
        """
        current = await self.config.guild(ctx.guild).enabled()

        if enabled is None:
            await ctx.send(f"Sprite announcer is currently **{'enabled' if current else 'disabled'}**.")
            return

        if enabled == current:
            await ctx.send(f"Sprite announcer is already **{'enabled' if enabled else 'disabled'}**.")
            return

        await self.config.guild(ctx.guild).enabled.set(enabled)
        log.info("Guild %d: sprite announcer set to %s by %s.", ctx.guild.id, enabled, ctx.author)  # type: ignore[union-attr]

        if enabled:
            channel_id = await self.config.guild(ctx.guild).channel_id()
            if not channel_id:
                await ctx.send(
                    "Sprite announcer **enabled**, but no channel is set.\n"
                    f"Set one with `{ctx.prefix}sa channel #your-channel`."
                )
            else:
                await self.config.guild(ctx.guild).next_trigger.set(None)
                self._schedule_announcement(ctx.guild)  # type: ignore[arg-type]
                await ctx.send("Sprite announcer **enabled**! A topic will appear at a random time.")
        else:
            if ctx.guild.id in self._announcement_tasks:  # type: ignore[union-attr]
                self._announcement_tasks.pop(ctx.guild.id).cancel()  # type: ignore[union-attr]
            await ctx.send("Sprite announcer **disabled**.")

    # ------------------------------------------------------------------
    # channel
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="channel")
    async def _channel(self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None):
        """Set or show the announcement channel.

        Usage: ``[p]sa channel`` – show current
               ``[p]sa channel #general``
        """
        if channel is None:
            cid = await self.config.guild(ctx.guild).channel_id()
            if cid:
                ch = ctx.guild.get_channel(cid)  # type: ignore[union-attr]
                if ch:
                    await ctx.send(f"Announcement channel: {ch.mention}")
                else:
                    await ctx.send("A channel was set but it no longer exists.")
            else:
                await ctx.send("No announcement channel is set.")
            return

        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        log.info("Guild %d: announcement channel set to %d by %s.", ctx.guild.id, channel.id, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Announcement channel set to {channel.mention}.")

        if await self.config.guild(ctx.guild).enabled():
            await self.config.guild(ctx.guild).next_trigger.set(None)
            self._schedule_announcement(ctx.guild)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # frequency
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="frequency")
    async def _frequency(self, ctx: commands.Context, min_minutes: Optional[int] = None, max_minutes: Optional[int] = None):
        """Set or show the announcement frequency range (in minutes).

        Usage: ``[p]sa frequency``         – show current
               ``[p]sa frequency 30 120``  – between 30 and 120 minutes
        """
        current = await self.config.guild(ctx.guild).frequency()

        if min_minutes is None or max_minutes is None:
            await ctx.send(
                f"Announcement frequency: **{current['min_minutes']}–{current['max_minutes']} minutes**."
            )
            return

        if min_minutes < 1:
            await ctx.send("Minimum must be at least **1 minute**.")
            return
        if max_minutes < min_minutes:
            await ctx.send("Maximum must be ≥ minimum.")
            return

        await self.config.guild(ctx.guild).frequency.set(
            {"min_minutes": min_minutes, "max_minutes": max_minutes}
        )
        log.info("Guild %d: frequency set to %d–%d by %s.", ctx.guild.id, min_minutes, max_minutes, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Frequency set to **{min_minutes}–{max_minutes} minutes**.")

        if await self.config.guild(ctx.guild).enabled():
            await self.config.guild(ctx.guild).next_trigger.set(None)
            self._schedule_announcement(ctx.guild)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # sprites sub-group
    # ------------------------------------------------------------------
    @spriteannouncer.group(name="sprites")
    async def _sprites(self, ctx: commands.Context):
        """Manage which sprite characters are used."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_sprites.command(name="list")
    async def _sprites_list(self, ctx: commands.Context):
        """List available and enabled sprites."""
        await self._refresh_github_sprites()
        guild_data = await self.config.guild(ctx.guild).all()
        enabled = set(guild_data["sprites_enabled"])

        lines: list[str] = []

        if self._github_sprites:
            lines.append("**Available sprites (from GitHub):**\n")
            for name in self._github_sprites:
                display = _character_name_from_filename(name)
                tag = " ✅" if name in enabled else ""
                lines.append(f"  • {display}{tag}")
        else:
            lines.append("**Fallback sprites (GitHub unreachable):**\n")
            for name in DEFAULT_SPRITES:
                lines.append(f"  • {_character_name_from_filename(name)}")

        if enabled:
            lines.append(f"\n{len(enabled)} sprite(s) explicitly enabled.")
        else:
            lines.append("\nNo sprites explicitly enabled – using all available.")

        message = "\n".join(lines)
        for page in pagify(message):
            await ctx.send(box(page))

    @_sprites.command(name="add")
    async def _sprites_add(self, ctx: commands.Context, sprite_name: str):
        """Enable a sprite by name (or full URL).

        The sprite is validated before being saved.  If you omit the ``.png``
        extension it will be added automatically when a match is found.
        """
        await self._refresh_github_sprites()

        # --- normalise name ---
        if not sprite_name.startswith(("http://", "https://")):
            if self._github_sprites and sprite_name not in self._github_sprites:
                # Try appending .png
                if f"{sprite_name}.png" in self._github_sprites:
                    sprite_name = f"{sprite_name}.png"
                else:
                    available = ", ".join(
                        _character_name_from_filename(s) for s in self._github_sprites
                    )
                    await ctx.send(
                        f"Sprite **{sprite_name}** not found.\nAvailable: {available}"
                    )
                    return

        # --- validate BEFORE writing to config ---
        url = await self._resolve_sprite_url(sprite_name)
        if url is None:
            await ctx.send(
                f"Could not verify sprite **{sprite_name}**. "
                "Check that it exists in the repository."
            )
            return

        async with self.config.guild(ctx.guild).sprites_enabled() as sprites:
            if sprite_name in sprites:
                await ctx.send(f"Sprite **{_character_name_from_filename(sprite_name)}** is already enabled.")
                return
            sprites.append(sprite_name)

        log.info("Guild %d: sprite '%s' enabled by %s.", ctx.guild.id, sprite_name, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Enabled sprite **{_character_name_from_filename(sprite_name)}**.")

    @_sprites.command(name="remove")
    async def _sprites_remove(self, ctx: commands.Context, sprite_name: str):
        """Disable a previously enabled sprite."""
        # Allow matching without .png for convenience
        async with self.config.guild(ctx.guild).sprites_enabled() as sprites:
            if sprite_name not in sprites:
                if f"{sprite_name}.png" in sprites:
                    sprite_name = f"{sprite_name}.png"
                else:
                    await ctx.send(f"Sprite **{sprite_name}** is not in the enabled list.")
                    return
            sprites.remove(sprite_name)

        log.info("Guild %d: sprite '%s' disabled by %s.", ctx.guild.id, sprite_name, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Removed sprite **{_character_name_from_filename(sprite_name)}**.")

    @_sprites.command(name="reset")
    async def _sprites_reset(self, ctx: commands.Context):
        """Clear the enabled list so all available sprites are used."""
        await self.config.guild(ctx.guild).sprites_enabled.set([])
        await self._refresh_github_sprites()
        count = len(self._github_sprites) or len(DEFAULT_SPRITES)
        source = "GitHub" if self._github_sprites else "defaults"
        log.info("Guild %d: sprite whitelist reset by %s.", ctx.guild.id, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Reset – using all **{count}** sprites from {source}.")

    @_sprites.command(name="refresh")
    async def _sprites_refresh(self, ctx: commands.Context):
        """Force a fresh fetch of the sprite list from GitHub."""
        self._github_sprites_fetched_at = 0.0
        self._github_sprites = []
        await ctx.send("Refreshing…")
        await self._refresh_github_sprites()

        if self._github_sprites:
            names = ", ".join(_character_name_from_filename(s) for s in self._github_sprites)
            await ctx.send(f"Found **{len(self._github_sprites)}** sprites: {names}")
        else:
            await ctx.send("Could not reach GitHub. Using fallback sprites.")

    # ------------------------------------------------------------------
    # topics sub-group
    # ------------------------------------------------------------------
    @spriteannouncer.group(name="topics")
    async def _topics(self, ctx: commands.Context):
        """Manage discussion topics."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_topics.command(name="list")
    async def _topics_list(self, ctx: commands.Context):
        """Show all configured topics."""
        topics: list[str] = await self.config.guild(ctx.guild).topics()
        if not topics:
            await ctx.send("No topics configured yet.")
            return

        lines = [f"{i}. {t}" for i, t in enumerate(topics, 1)]
        message = "**Discussion Topics**\n" + "\n".join(lines)
        for page in pagify(message):
            await ctx.send(box(page))

    @_topics.command(name="add")
    async def _topics_add(self, ctx: commands.Context, *, topic: str):
        """Add a single discussion topic.

        Example: ``[p]sa topics add What's your favourite game?``
        """
        topic = topic.strip()
        if not topic:
            await ctx.send("Please provide a topic.")
            return

        async with self.config.guild(ctx.guild).topics() as topics:
            if topic in topics:
                await ctx.send("That topic already exists.")
                return
            topics.append(topic)

        log.info("Guild %d: topic added by %s – '%s'", ctx.guild.id, ctx.author, topic)  # type: ignore[union-attr]
        await ctx.send(f"Topic added: **{topic}**")

    @_topics.command(name="bulk")
    async def _topics_bulk(self, ctx: commands.Context, *, topics_text: str):
        """Add multiple topics at once (one per line).

        Example::

            [p]sa topics bulk What's your favourite game?
            If you could travel anywhere, where would you go?
            What did you learn recently?
        """
        lines = [line.strip() for line in topics_text.split("\n") if line.strip()]
        if not lines:
            await ctx.send("No valid topics found.")
            return

        added = skipped = 0
        async with self.config.guild(ctx.guild).topics() as topics:
            for line in lines:
                if line in topics:
                    skipped += 1
                else:
                    topics.append(line)
                    added += 1

        log.info("Guild %d: %d topics bulk-added by %s.", ctx.guild.id, added, ctx.author)  # type: ignore[union-attr]
        msg = f"Added **{added}** topic(s)."
        if skipped:
            msg += f" Skipped **{skipped}** duplicate(s)."
        await ctx.send(msg)

    @_topics.command(name="remove")
    async def _topics_remove(self, ctx: commands.Context, index: int):
        """Remove a topic by its list number (from ``[p]sa topics list``)."""
        async with self.config.guild(ctx.guild).topics() as topics:
            if not topics or index < 1 or index > len(topics):
                await ctx.send("Invalid index.")
                return
            removed = topics.pop(index - 1)

        log.info("Guild %d: topic removed by %s – '%s'", ctx.guild.id, ctx.author, removed)  # type: ignore[union-attr]
        await ctx.send(f"Removed topic: **{removed}**")

    # ------------------------------------------------------------------
    # announcements sub-group
    # ------------------------------------------------------------------
    @spriteannouncer.group(name="announcements")
    async def _announcements(self, ctx: commands.Context):
        """Manage announcements."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_announcements.command(name="list")
    async def _announcements_list(self, ctx: commands.Context):
        """Show all configured announcements."""
        announcements: list[str] = await self.config.guild(ctx.guild).announcements()
        if not announcements:
            await ctx.send("No announcements configured yet.")
            return

        lines = [f"{i}. {a}" for i, a in enumerate(announcements, 1)]
        message = "**Announcements**\n" + "\n".join(lines)
        for page in pagify(message):
            await ctx.send(box(page))

    @_announcements.command(name="add")
    async def _announcements_add(self, ctx: commands.Context, *, announcement: str):
        """Add a single announcement."""
        announcement = announcement.strip()
        if not announcement:
            await ctx.send("Please provide an announcement.")
            return

        async with self.config.guild(ctx.guild).announcements() as announcements:
            announcements.append(announcement)

        log.info("Guild %d: announcement added by %s.", ctx.guild.id, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Announcement added: **{announcement}**")

    @_announcements.command(name="bulk")
    async def _announcements_bulk(self, ctx: commands.Context, *, announcements_text: str):
        """Add multiple announcements at once (one per line).

        Example::

            [p]sa announcements bulk Welcome to movie night!
            Don't forget the new server rules.
            Server update this weekend.
        """
        lines = [line.strip() for line in announcements_text.split("\n") if line.strip()]
        if not lines:
            await ctx.send("No valid announcements found.")
            return

        added = skipped = 0
        async with self.config.guild(ctx.guild).announcements() as announcements:
            for line in lines:
                if line in announcements:
                    skipped += 1
                else:
                    announcements.append(line)
                    added += 1

        log.info("Guild %d: %d announcements bulk-added by %s.", ctx.guild.id, added, ctx.author)  # type: ignore[union-attr]
        msg = f"Added **{added}** announcement(s)."
        if skipped:
            msg += f" Skipped **{skipped}** duplicate(s)."
        await ctx.send(msg)

    @_announcements.command(name="remove")
    async def _announcements_remove(self, ctx: commands.Context, index: int):
        """Remove an announcement by its list number."""
        async with self.config.guild(ctx.guild).announcements() as announcements:
            if not announcements or index < 1 or index > len(announcements):
                await ctx.send("Invalid index.")
                return
            removed = announcements.pop(index - 1)

        log.info("Guild %d: announcement removed by %s.", ctx.guild.id, ctx.author)  # type: ignore[union-attr]
        await ctx.send(f"Removed announcement: **{removed}**")

    # ------------------------------------------------------------------
    # trigger (manual)
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="trigger")
    async def _trigger(self, ctx: commands.Context):
        """Manually post a sprite announcement right now."""
        if not await self.config.guild(ctx.guild).enabled():
            await ctx.send("Sprite announcer is currently disabled.")
            return

        await self._send_announcement(ctx.guild)  # type: ignore[arg-type]
        await ctx.send("Announcement triggered manually.")

    # ------------------------------------------------------------------
    # import
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="import")
    async def _import(self, ctx: commands.Context):
        """Import topics and announcements from an attached ``.txt`` file.

        File format::

            [TOPICS]
            Topic one
            Topic two

            [ANNOUNCEMENTS]
            Announcement one
            Announcement two
        """
        if not ctx.message.attachments:
            await ctx.send("Please attach a ``.txt`` file.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".txt"):
            await ctx.send("Only ``.txt`` files are supported.")
            return

        try:
            raw = await attachment.read()
            text = raw.decode("utf-8")
        except Exception:
            await ctx.send("Failed to read the file.")
            return

        mode: Optional[str] = None
        topics: list[str] = []
        announcements: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if upper == "[TOPICS]":
                mode = "topics"
            elif upper == "[ANNOUNCEMENTS]":
                mode = "announcements"
            elif mode == "topics":
                topics.append(stripped)
            elif mode == "announcements":
                announcements.append(stripped)

        topics_added = announcements_added = 0

        if topics:
            async with self.config.guild(ctx.guild).topics() as existing:
                for t in topics:
                    if t not in existing:
                        existing.append(t)
                        topics_added += 1

        if announcements:
            async with self.config.guild(ctx.guild).announcements() as existing:
                for a in announcements:
                    if a not in existing:
                        existing.append(a)
                        announcements_added += 1

        log.info(
            "Guild %d: imported %d topics + %d announcements by %s.",
            ctx.guild.id, topics_added, announcements_added, ctx.author,  # type: ignore[union-attr]
        )
        await ctx.send(f"Imported **{topics_added}** topic(s) and **{announcements_added}** announcement(s).")

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    @spriteannouncer.command(name="status")
    async def _status(self, ctx: commands.Context):
        """Show a summary of the sprite announcer's current state."""
        guild_data = await self.config.guild(ctx.guild).all()

        enabled = guild_data["enabled"]
        channel = (
            ctx.guild.get_channel(guild_data["channel_id"])  # type: ignore[union-attr]
            if guild_data["channel_id"]
            else None
        )
        freq = guild_data["frequency"]
        enabled_sprites = guild_data["sprites_enabled"]

        if enabled_sprites:
            sprite_status = f"{len(enabled_sprites)} enabled"
        elif self._github_sprites:
            sprite_status = f"All {len(self._github_sprites)} from GitHub"
        else:
            sprite_status = f"{len(DEFAULT_SPRITES)} fallback defaults"

        embed = discord.Embed(
            title="Sprite Announcer – Status",
            color=discord.Color.blue() if enabled else discord.Color.red(),
            timestamp=datetime.now(tz=timezone.utc),
        )
        embed.add_field(name="Status",        value="✅ Enabled" if enabled else "❌ Disabled", inline=True)
        embed.add_field(name="Channel",       value=channel.mention if channel else "Not set", inline=True)  # type: ignore[union-attr]
        embed.add_field(name="Frequency",     value=f"{freq['min_minutes']}–{freq['max_minutes']} min", inline=True)
        embed.add_field(name="Sprites",       value=sprite_status, inline=True)
        embed.add_field(name="Topics",        value=str(len(guild_data["topics"])), inline=True)
        embed.add_field(name="Announcements", value=str(len(guild_data["announcements"])), inline=True)

        embed.add_field(
            name="GitHub Repository",
            value=f"[{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}]"
                  f"(https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/tree/main/Character%20Sprite)",
            inline=False,
        )

        last = guild_data["last_triggered"]
        if last:
            embed.add_field(name="Last Triggered", value=f"<t:{int(last)}:R>", inline=True)

        nxt = guild_data["next_trigger"]
        if nxt:
            embed.add_field(name="Next Trigger", value=f"<t:{int(nxt)}:R>", inline=True)

        # Random sprite thumbnail
        if self._github_sprites:
            url = await self._resolve_sprite_url(random.choice(self._github_sprites))
            if url:
                embed.set_thumbnail(url=url)

        await ctx.send(embed=embed)


# ---------------------------------------------------------------------------
# Cog setup – required by Red for loading
# ---------------------------------------------------------------------------
async def setup(bot: Red) -> None:
    await bot.add_cog(SpriteAnnouncer(bot))
