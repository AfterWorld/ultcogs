from __future__ import annotations

import asyncio
import io
import json
import logging
import inspect
import random
import time
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageFilter, ImageOps
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number
from .engine import matches_guess, normalize, safe_wiki_hint

log = logging.getLogger("red.onepieceguess")
WIKI_API = "https://onepiece.fandom.com/api.php"
MODES = {"character": ("characters", "aliases", "hints", "Character"),
         "fruit": ("fruits", "fruit_aliases", "fruit_hints", "Devil Fruit"),
         "ship": ("ships", "ship_aliases", "ship_hints", "Ship")}
DEFAULTS = {
    "migration_v1": False,
    "enabled": False, "channel_id": None, "mode": "character",
    "interval": 1800, "roundtime": 120, "reward": 0,
    "beri_min": 100, "beri_max": 1000,
    "characters": ["Monkey D. Luffy", "Roronoa Zoro", "Nami", "Nico Robin",
                   "Vinsmoke Sanji", "Tony Tony Chopper", "Brook", "Franky",
                   "Jinbe", "Marshall D. Teach", "Gol D. Roger"],
    "aliases": {}, "hints": {}, "fruits": [], "fruit_aliases": {}, "fruit_hints": {},
    "ships": [], "ship_aliases": {}, "ship_hints": {},
    "hint_enabled": True, "blur_mode": "gaussian", "blur_strength": 10,
    "require_image": {"character": True, "fruit": True, "ship": True},
    "team_api": {"enabled": False, "mode": "teamscog", "win_points": 1, "timeout_points": 0},
    "noimage_max_retries": 6,
    "active": {"title": None, "message_id": None, "channel_id": None,
               "started_at": 0, "expired": False},
    "next_post_at": 0,
}


class OnePieceGuess(commands.Cog):
    """Timed One Piece image guessing game with command answers and team scoring."""

    def __init__(self, bot: Red):
        self.bot = bot
        # Keep the original identifier so existing pool/settings data can be reused.
        self.config = Config.get_conf(self, identifier=2025111801, force_registration=True)
        self.config.register_guild(**DEFAULTS)
        self.config.register_member(wins=0)
        self._locks: dict[int, asyncio.Lock] = {}
        self._task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None

    def lock(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    async def cog_load(self) -> None:
        self._task = asyncio.create_task(self.event_loop(), name="onepieceguess-ticker")

    def cog_unload(self) -> None:
        if self._task:
            self._task.cancel()
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    async def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(timeout=timeout,
                headers={"User-Agent": "OnePieceGuess Redbot cog (wiki image trivia)"})
        return self._session

    async def event_loop(self) -> None:
        await self.bot.wait_until_red_ready()
        await self.migrate_legacy_data()
        while True:
            try:
                for guild in list(self.bot.guilds):
                    try:
                        await self.tick_guild(guild)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        log.exception("Round processing failed in guild %s", guild.id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("OnePieceGuess scheduler failed")
            await asyncio.sleep(5)

    async def migrate_legacy_data(self) -> None:
        """Keep settings and an in-progress round from the earlier cog version."""
        for guild in self.bot.guilds:
            conf = self.config.guild(guild)
            values = await conf.all()
            if values.get("migration_v1"):
                continue
            old_blur = values.get("blur") or {}
            if old_blur.get("mode"):
                await conf.blur_mode.set(old_blur["mode"])
            if old_blur.get("strength"):
                await conf.blur_strength.set(old_blur["strength"])
            active = values.get("active") or {}
            if active.get("title"):
                active.setdefault("message_id", active.get("posted_message_id"))
                active.setdefault("channel_id", active.get("posted_channel_id"))
                active.setdefault("expired", False)
                active.setdefault("mode", values.get("mode", "character"))
                await conf.active.set(active)
            await conf.migration_v1.set(True)

    async def tick_guild(self, guild: discord.Guild) -> None:
        async with self.lock(guild.id):
            settings = await self.config.guild(guild).all()
            active = settings["active"] or {}
            now = int(time.time())
            if active.get("title") and not active.get("expired"):
                if now >= int(active.get("started_at") or 0) + int(settings["roundtime"]):
                    await self.finish_round(guild, settings, timed_out=True)
                    settings = await self.config.guild(guild).all()
                    active = settings["active"]
            if not settings["enabled"]:
                return
            if (not active.get("title") or active.get("expired")) and now >= int(settings.get("next_post_at") or 0):
                await self.post_round(guild, settings)

    async def wiki_page(self, title: str) -> tuple[str, Optional[str], str]:
        session = await self.session()
        # Match the original cog's Fandom query: intro text plus the original
        # image, with a large thumbnail as fallback for pages lacking originals.
        params = {"action": "query", "prop": "extracts|pageimages",
                  "exintro": "1", "explaintext": "1", "piprop": "original|thumbnail",
                  "pithumbsize": "1600", "redirects": "1", "format": "json", "titles": title}
        async with session.get(WIKI_API, params=params) as response:
            response.raise_for_status()
            data = await response.json()
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        image_url = (page.get("original") or {}).get("source") or (page.get("thumbnail") or {}).get("source")
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url
        return page.get("title", title), image_url, page.get("extract", "")

    async def blurred_image(self, url: str, settings: dict) -> Optional[discord.File]:
        try:
            session = await self.session()
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                raw = await response.read()
            image = Image.open(io.BytesIO(raw))
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            strength = max(1, min(250, int(settings.get("blur_strength", 10))))
            if settings.get("blur_mode") == "pixelate":
                width, height = image.size
                image = image.resize((max(1, width // strength), max(1, height // strength)), Image.Resampling.NEAREST)
                image = image.resize((width, height), Image.Resampling.NEAREST)
            else:
                image = image.filter(ImageFilter.GaussianBlur(radius=strength))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=86, optimize=True)
            output.seek(0)
            return discord.File(output, filename="onepieceguess.jpg")
        except (aiohttp.ClientError, OSError, ValueError, Image.DecompressionBombError):
            log.info("Could not fetch or blur wiki image %s", url, exc_info=True)
            return None

    async def post_round(self, guild: discord.Guild, settings: dict, title: Optional[str] = None) -> bool:
        channel_id = int(settings.get("channel_id") or 0)
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
            log.warning("No valid game channel is configured in guild %s", guild.id)
            return False
        mode = settings.get("mode", "character")
        pool_key, _, hints_key, label = MODES.get(mode, MODES["character"])
        pool = list(settings.get(pool_key) or [])
        if title:
            candidates = [title]
        else:
            random.shuffle(pool)
            candidates = pool[:max(1, min(20, int(settings.get("noimage_max_retries") or 6)))]
        selected = None
        canonical = None
        image_url = None
        extract = ""
        selected_file = None
        for candidate in candidates:
            if candidate not in pool:
                continue
            try:
                canonical, image_url, extract = await self.wiki_page(candidate)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                log.info("Wiki lookup failed for %s", candidate, exc_info=True)
                continue
            if not image_url:
                continue
            image_file = await self.blurred_image(image_url, settings)
            if image_file is None:
                continue
            selected, selected_file = candidate, image_file
            break
        if not selected:
            if not title:
                await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
                await self.safe_send(channel, "⚠️ I couldn't find a usable image for this round. I'll try again after the configured interval.")
            return False

        file = selected_file
        hint = (settings.get(hints_key) or {}).get(selected) if settings.get("hint_enabled") else None
        if not hint and settings.get("hint_enabled"):
            hint = safe_wiki_hint(extract, canonical or selected,
                (settings.get(MODES[mode][1]) or {}).get(selected, []))
        embed = discord.Embed(title=f"🗺️ Guess the One Piece {label}!",
            description="Answer with `/guess <name>` or your bot prefix followed by `guess <name>`.\n"
                        f"You have **{int(settings['roundtime'])} seconds**.",
            color=discord.Color.from_rgb(38, 91, 153))
        if hint:
            embed.add_field(name="Hint", value=str(hint)[:500], inline=False)
        embed.set_footer(text="OnePieceGuess • first correct answer wins")
        if file:
            embed.set_image(url="attachment://onepieceguess.jpg")
        permissions = channel.permissions_for(guild.me)
        if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links:
            await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
            log.warning("Bot lacks permission to post a game round in guild %s", guild.id)
            return False
        if not permissions.attach_files:
            await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
            log.warning("Bot lacks attach-files permission in guild %s", guild.id)
            return False
        try:
            message = await channel.send(embed=embed, file=file,
                allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
            log.exception("Could not post a round in guild %s", guild.id)
            return False
        await self.config.guild(guild).active.set({
            "title": selected, "message_id": message.id, "channel_id": channel.id,
            "started_at": int(time.time()), "expired": False, "mode": mode,
        })
        return True

    async def finish_round(self, guild: discord.Guild, settings: dict, *, timed_out: bool,
                           winner: Optional[discord.Member] = None) -> None:
        active = settings.get("active") or {}
        title = active.get("title")
        if not title or active.get("expired"):
            return
        # Mark closed before network work so only one user can claim the round.
        active["expired"] = True
        await self.config.guild(guild).active.set(active)
        await self.config.guild(guild).next_post_at.set(int(time.time()) + int(settings["interval"]))
        channel = guild.get_channel(int(active.get("channel_id") or active.get("posted_channel_id") or 0))
        if not isinstance(channel, discord.TextChannel):
            return
        round_mode = active.get("mode", settings.get("mode"))
        label = MODES.get(round_mode, MODES["character"])[3]
        if timed_out:
            text = f"⏰ Time! The answer was **{discord.utils.escape_markdown(title)}**."
        else:
            text = f"✅ {winner.mention if winner else 'A player'} got it: **{discord.utils.escape_markdown(title)}**!"
            if winner:
                member_conf = self.config.member(winner)
                await member_conf.wins.set((await member_conf.wins()) + 1)
                reward = int(settings.get("reward") or 0)
                actual_reward = reward
                if reward == 0:
                    actual_reward = random.randint(int(settings.get("beri_min") or 100),
                                                   max(int(settings.get("beri_min") or 100), int(settings.get("beri_max") or 1000)))
                beri = self.bot.get_cog("BeriCore")
                if beri and actual_reward > 0:
                    try:
                        await beri.add_beri(winner, actual_reward, reason=f"opguess:{label}:{title}", actor=winner)
                        text += f"\n💰 +{humanize_number(actual_reward)} Beri"
                    except Exception:
                        log.exception("BeriCore reward failed")
                team_note = await self.award_team_points(guild, winner, settings)
                if team_note:
                    text += f"\n{team_note}"
        try:
            canonical, image_url, _ = await self.wiki_page(title)
            if image_url:
                session = await self.session()
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image = discord.File(io.BytesIO(await response.read()), filename="onepieceguess-answer.png")
                        await channel.send(text, file=image, allowed_mentions=discord.AllowedMentions.none())
                        return
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            log.info("Could not fetch answer image for %s", title, exc_info=True)
        await self.safe_send(channel, text)

    async def award_team_points(self, guild: discord.Guild, winner: discord.Member,
                                settings: dict) -> Optional[str]:
        """Award the winner's team through the original Teams cog integration."""
        team_settings = settings.get("team_api") or {}
        if not team_settings.get("enabled") or team_settings.get("mode") != "teamscog":
            return None
        points = max(0, int(team_settings.get("win_points") or 0))
        if points <= 0:
            return None
        teams_cog = self.bot.get_cog("Teams")
        if teams_cog is None:
            return "⚠️ Team scoring is enabled, but the `Teams` cog is not loaded."
        guild_teams = getattr(teams_cog, "teams", {}).get(guild.id, {})
        team = next((candidate for candidate in guild_teams.values()
                     if winner in getattr(candidate, "members", ())), None)
        if team is None:
            return "🏴‍☠️ No team points awarded (winner is not on a team)."
        team_name = discord.utils.escape_markdown(str(
            getattr(team, "display_name", getattr(team, "name", "your team"))
        ))
        amplifier = self.bot.get_cog("BeriAmplifier")
        if amplifier and hasattr(amplifier, "add_amplified_points"):
            try:
                total = amplifier.add_amplified_points(
                    winner, points, "guessing_game_win", notification_channel=None
                )
                if inspect.isawaitable(total):
                    total = await total
                total = int(total) if total is not None else points
                return f"🏴‍☠️ **{team_name}** earned **{humanize_number(total)}** team point(s)!"
            except Exception:
                log.exception("BeriAmplifier failed; falling back to base team points")
        try:
            result = team.add_points(points, winner, guild.me)
            if inspect.isawaitable(result):
                await result
            return f"🏴‍☠️ **{team_name}** earned **{humanize_number(points)}** team point(s)!"
        except Exception:
            log.exception("Team points award failed for guild %s", guild.id)
            return "⚠️ Team points could not be awarded; check the Teams cog configuration."

    async def process_guess(self, guild: discord.Guild, channel: discord.abc.Messageable,
                            member: discord.abc.User, guess: str) -> str:
        async with self.lock(guild.id):
            settings = await self.config.guild(guild).all()
            target_channel = int(settings.get("channel_id") or 0)
            if getattr(channel, "id", None) != target_channel:
                return "Guesses are accepted in the configured game channel."
            active = settings.get("active") or {}
            title = active.get("title")
            if not title or active.get("expired"):
                return "There isn't an active round right now."
            _, alias_key, _, _ = MODES.get(active.get("mode", settings.get("mode")), MODES["character"])
            aliases = (settings.get(alias_key) or {}).get(title, [])
            if not matches_guess(guess, title, aliases):
                return "❌ Not quite. Try again!"
            if not isinstance(member, discord.Member):
                return "I couldn't verify your server membership."
            await self.finish_round(guild, settings, timed_out=False, winner=member)
            return "✅ Correct! The answer has been revealed in the game channel."

    async def safe_send(self, channel, content: str) -> None:
        try:
            await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            log.exception("Could not send OnePieceGuess message")

    @commands.hybrid_group(name="opguess", invoke_without_command=True)
    @commands.guild_only()
    async def opguess(self, ctx: commands.Context) -> None:
        """Show game status and configuration."""
        settings = await self.config.guild(ctx.guild).all()
        active = settings.get("active") or {}
        channel = ctx.guild.get_channel(int(settings.get("channel_id") or 0))
        text = (f"**OnePieceGuess** — {'ON' if settings['enabled'] else 'OFF'}\n"
                f"Mode: **{settings['mode']}** • Channel: {channel.mention if channel else 'not set'}\n"
                f"Post interval: **{settings['interval']}s** • Round: **{settings['roundtime']}s**\n"
                f"Pool size: **{len(settings.get(MODES[settings['mode']][0]) or [])}**\n"
                f"Active round: **{active.get('title') if active.get('title') and not active.get('expired') else 'none'}**")
        await ctx.reply(embed=discord.Embed(description=text, color=discord.Color.blurple()))

    @opguess.command(name="toggle")
    @commands.admin()
    async def toggle(self, ctx: commands.Context, enabled: Optional[bool] = None) -> None:
        current = await self.config.guild(ctx.guild).enabled()
        enabled = not current if enabled is None else enabled
        await self.config.guild(ctx.guild).enabled.set(enabled)
        await ctx.reply(f"New rounds **{'enabled' if enabled else 'paused'}**.")

    @opguess.command(name="setchannel")
    @commands.admin()
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        await self.config.guild(ctx.guild).channel_id.set(channel.id)
        await ctx.reply(f"Game channel set to {channel.mention}.")

    @opguess.command(name="mode")
    @commands.admin()
    async def set_mode(self, ctx: commands.Context, mode: str) -> None:
        mode = mode.casefold()
        if mode not in MODES:
            return await ctx.reply("Choose `character`, `fruit`, or `ship`.")
        await self.config.guild(ctx.guild).mode.set(mode)
        await ctx.reply(f"Mode set to **{mode}**.")

    @opguess.command(name="setinterval")
    @commands.admin()
    async def set_interval(self, ctx: commands.Context, seconds: int) -> None:
        seconds = max(30, min(86400, seconds))
        await self.config.guild(ctx.guild).interval.set(seconds)
        await ctx.reply(f"Next-round delay set to **{seconds} seconds**.")

    @opguess.command(name="setroundtime")
    @commands.admin()
    async def set_roundtime(self, ctx: commands.Context, seconds: int) -> None:
        seconds = max(15, min(3600, seconds))
        await self.config.guild(ctx.guild).roundtime.set(seconds)
        await ctx.reply(f"Round duration set to **{seconds} seconds**.")

    @opguess.command(name="setreward")
    @commands.admin()
    async def set_reward(self, ctx: commands.Context, amount: int) -> None:
        amount = max(0, amount)
        await self.config.guild(ctx.guild).reward.set(amount)
        await ctx.reply("Reward set to a random Beri amount." if amount == 0 else f"Reward set to **{amount} Beri**.")

    @opguess.command(name="setberirange")
    @commands.admin()
    async def set_beri_range(self, ctx: commands.Context, minimum: int, maximum: int) -> None:
        minimum = max(0, minimum)
        maximum = max(minimum, maximum)
        conf = self.config.guild(ctx.guild)
        await conf.beri_min.set(minimum)
        await conf.beri_max.set(maximum)
        await ctx.reply(f"Random Beri range set to **{minimum}–{maximum}**.")

    @opguess.command(name="blur")
    @commands.admin()
    async def set_blur(self, ctx: commands.Context, mode: str, strength: int = 10) -> None:
        mode = mode.casefold()
        if mode not in {"gaussian", "pixelate"}:
            return await ctx.reply("Blur mode must be `gaussian` or `pixelate`.")
        conf = self.config.guild(ctx.guild)
        await conf.blur_mode.set(mode)
        await conf.blur_strength.set(max(1, min(250, strength)))
        await ctx.reply(f"Image effect set to **{mode}**, strength **{max(1, min(250, strength))}**.")

    @opguess.command(name="requireimage")
    @commands.admin()
    async def require_image(self, ctx: commands.Context) -> None:
        """Images are required for every round so empty embeds are never posted."""
        conf = self.config.guild(ctx.guild)
        await conf.require_image.set({"character": True, "fruit": True, "ship": True})
        await ctx.reply("Images are required for all modes to prevent image-less rounds.")

    @opguess.command(name="hints")
    @commands.admin()
    async def toggle_hints(self, ctx: commands.Context, enabled: Optional[bool] = None) -> None:
        conf = self.config.guild(ctx.guild)
        value = not await conf.hint_enabled() if enabled is None else enabled
        await conf.hint_enabled.set(value)
        await ctx.reply(f"Custom clues are **{'enabled' if value else 'disabled'}**.")

    @opguess.group(name="teamapi", invoke_without_command=True)
    @commands.admin()
    async def team_api(self, ctx: commands.Context) -> None:
        """Configure points awarded through the Teams cog."""
        settings = await self.config.guild(ctx.guild).team_api()
        await ctx.reply(
            f"Team scoring: **{'on' if settings.get('enabled') else 'off'}**\n"
            f"Integration: **Teams cog** • points per win: **{settings.get('win_points', 1)}**"
        )

    @team_api.command(name="toggle")
    @commands.admin()
    async def team_api_toggle(self, ctx: commands.Context, enabled: Optional[bool] = None) -> None:
        conf = self.config.guild(ctx.guild).team_api
        settings = await conf()
        settings["enabled"] = not settings.get("enabled", False) if enabled is None else enabled
        settings["mode"] = "teamscog"
        await conf.set(settings)
        await ctx.reply(f"Team scoring **{'enabled' if settings['enabled'] else 'disabled'}**.")

    @team_api.command(name="setpoints")
    @commands.admin()
    async def team_api_setpoints(self, ctx: commands.Context, points: int,
                                 timeout_points: int = 0) -> None:
        conf = self.config.guild(ctx.guild).team_api
        settings = await conf()
        settings["win_points"] = max(0, points)
        settings["timeout_points"] = max(0, timeout_points)
        settings["mode"] = "teamscog"
        await conf.set(settings)
        await ctx.reply(f"Points set — win: **{settings['win_points']}**, timeout: **{settings['timeout_points']}**.")

    @opguess.group(name="char", invoke_without_command=True)
    @commands.admin()
    async def pool(self, ctx: commands.Context) -> None:
        settings = await self.config.guild(ctx.guild).all()
        pool_key = MODES[settings["mode"]][0]
        entries = settings.get(pool_key) or []
        preview = ", ".join(entries[:12]) or "empty"
        await ctx.reply(f"**{settings['mode'].title()} pool: {len(entries)}**\n{preview}")

    @pool.command(name="add")
    @commands.admin()
    async def add_entry(self, ctx: commands.Context, *, title: str) -> None:
        conf = self.config.guild(ctx.guild)
        mode = await conf.mode()
        pool_key = MODES[mode][0]
        async with getattr(conf, pool_key)() as pool:
            if any(normalize(entry) == normalize(title) for entry in pool):
                return await ctx.reply("That entry is already in the pool.")
            pool.append(title.strip())
        await ctx.reply(f"Added **{discord.utils.escape_markdown(title.strip())}**.")

    @pool.command(name="remove")
    @commands.admin()
    async def remove_entry(self, ctx: commands.Context, *, title: str) -> None:
        conf = self.config.guild(ctx.guild)
        mode = await conf.mode()
        pool_key, alias_key, hints_key, _ = MODES[mode]
        entries = await getattr(conf, pool_key)()
        found = next((entry for entry in entries if normalize(entry) == normalize(title)), None)
        if not found:
            return await ctx.reply("I couldn't find that entry.")
        entries.remove(found)
        await getattr(conf, pool_key).set(entries)
        async with getattr(conf, alias_key)() as aliases:
            aliases.pop(found, None)
        async with getattr(conf, hints_key)() as hints:
            hints.pop(found, None)
        await ctx.reply(f"Removed **{discord.utils.escape_markdown(found)}**.")

    @pool.command(name="aliases")
    @commands.admin()
    async def set_aliases(self, ctx: commands.Context, title: str, *, aliases: str) -> None:
        conf = self.config.guild(ctx.guild)
        mode = await conf.mode()
        pool_key, alias_key, _, _ = MODES[mode]
        entries = await getattr(conf, pool_key)()
        entry = next((item for item in entries if normalize(item) == normalize(title)), None)
        if not entry:
            return await ctx.reply("Add the entry to the pool first.")
        values = list(dict.fromkeys(part.strip() for part in aliases.split(",") if part.strip()))
        async with getattr(conf, alias_key)() as mapping:
            mapping[entry] = values
        await ctx.reply(f"Saved {len(values)} alias(es) for **{entry}**.")

    @opguess.command(name="clue")
    @commands.admin()
    async def set_clue(self, ctx: commands.Context, title: str, *, clue: str) -> None:
        conf = self.config.guild(ctx.guild)
        mode = await conf.mode()
        pool_key, _, hints_key, _ = MODES[mode]
        entries = await getattr(conf, pool_key)()
        entry = next((item for item in entries if normalize(item) == normalize(title)), None)
        if not entry:
            return await ctx.reply("Add the entry to the current pool first.")
        async with getattr(conf, hints_key)() as hints:
            hints[entry] = clue[:1000]
        await ctx.reply(f"Saved a clue for **{entry}**.")

    @opguess.command(name="import")
    @commands.admin()
    async def import_pool(self, ctx: commands.Context) -> None:
        if not ctx.message.attachments:
            return await ctx.reply("Attach a JSON file to import the current mode's pool.")
        attachment = ctx.message.attachments[0]
        if attachment.size > 1_000_000:
            return await ctx.reply("The JSON file must be smaller than 1 MB.")
        try:
            payload = json.loads((await attachment.read()).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return await ctx.reply("That attachment isn't valid UTF-8 JSON.")
        if isinstance(payload, list):
            entries, aliases, hints = payload, {}, {}
        elif isinstance(payload, dict):
            entries = payload.get("entries", payload.get("characters", []))
            aliases, hints = payload.get("aliases", {}), payload.get("hints", {})
        else:
            return await ctx.reply("JSON must be a list or an object with entries, aliases, and hints.")
        if not isinstance(entries, list) or not isinstance(aliases, dict) or not isinstance(hints, dict):
            return await ctx.reply("Invalid pool format: entries must be a list; aliases and hints must be objects.")
        entries = list(dict.fromkeys(str(item).strip() for item in entries if str(item).strip()))
        conf = self.config.guild(ctx.guild)
        mode = await conf.mode()
        pool_key, alias_key, hints_key, _ = MODES[mode]
        await getattr(conf, pool_key).set(entries)
        await getattr(conf, alias_key).set({str(k): [str(v) for v in values]
            for k, values in aliases.items() if isinstance(values, list)})
        await getattr(conf, hints_key).set({str(k): str(v)[:1000] for k, v in hints.items()})
        await ctx.reply(f"Imported **{len(entries)}** entries for **{mode}**.")

    @opguess.command(name="export")
    @commands.admin()
    async def export_pool(self, ctx: commands.Context) -> None:
        settings = await self.config.guild(ctx.guild).all()
        mode = settings["mode"]
        pool_key, alias_key, hints_key, _ = MODES[mode]
        payload = {"mode": mode, "entries": settings.get(pool_key, []),
                   "aliases": settings.get(alias_key, {}), "hints": settings.get(hints_key, {})}
        data = io.BytesIO(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
        await ctx.reply(file=discord.File(data, filename=f"onepieceguess-{mode}.json"))

    @opguess.command(name="forcepost")
    @commands.admin()
    async def force_post(self, ctx: commands.Context, *, title: Optional[str] = None) -> None:
        async with self.lock(ctx.guild.id):
            settings = await self.config.guild(ctx.guild).all()
            active = settings.get("active") or {}
            if active.get("title") and not active.get("expired"):
                await self.finish_round(ctx.guild, settings, timed_out=True)
                settings = await self.config.guild(ctx.guild).all()
            if title:
                pool_key = MODES[settings["mode"]][0]
                entries = settings.get(pool_key) or []
                match = next((entry for entry in entries if normalize(entry) == normalize(title)), None)
                if not match:
                    return await ctx.reply("That entry isn't in the current mode's pool.")
                posted = await self.post_round(ctx.guild, settings, match)
            else:
                posted = await self.post_round(ctx.guild, settings)
            await ctx.reply("Round posted." if posted else "I couldn't post a round. Check the channel, pool, and wiki image.")

    @opguess.command(name="end")
    @commands.admin()
    async def end_round(self, ctx: commands.Context) -> None:
        async with self.lock(ctx.guild.id):
            settings = await self.config.guild(ctx.guild).all()
            active = settings.get("active") or {}
            if not active.get("title") or active.get("expired"):
                return await ctx.reply("There is no active round.")
            await self.finish_round(ctx.guild, settings, timed_out=True)
        await ctx.reply("Round ended and answer revealed.")

    @opguess.command(name="stats")
    @commands.guild_only()
    async def stats(self, ctx: commands.Context, member: Optional[discord.Member] = None) -> None:
        member = member or ctx.author
        wins = await self.config.member(member).wins()
        await ctx.reply(embed=discord.Embed(description=f"🏴‍☠️ **{member.display_name}** has **{wins}** correct guess(es).",
                                            color=discord.Color.blurple()))

    @opguess.command(name="top")
    @commands.guild_only()
    async def leaderboard(self, ctx: commands.Context) -> None:
        rows = await self.config.all_members(ctx.guild)
        winners = sorted(((int(uid), int(data.get("wins", 0))) for uid, data in rows.items()),
                         key=lambda row: (-row[1], row[0]))
        lines = []
        for rank, (user_id, wins) in enumerate([row for row in winners if row[1] > 0][:10], 1):
            member = ctx.guild.get_member(user_id)
            name = discord.utils.escape_markdown(member.display_name) if member else f"User {user_id}"
            lines.append(f"**{rank}.** {name} — **{wins}**")
        await ctx.reply(embed=discord.Embed(title="🏆 OnePieceGuess leaderboard",
            description="\n".join(lines) if lines else "No wins yet.", color=discord.Color.gold()))

    @commands.hybrid_command(name="guess")
    @commands.guild_only()
    async def guess(self, ctx: commands.Context, *, answer: str) -> None:
        if getattr(ctx, "interaction", None):
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.defer(ephemeral=True, thinking=True)
            result = await self.process_guess(ctx.guild, ctx.channel, ctx.author, answer)
            await ctx.interaction.followup.send(result, ephemeral=True)
        else:
            result = await self.process_guess(ctx.guild, ctx.channel, ctx.author, answer)
            await ctx.reply(result, delete_after=8 if result.startswith("❌") else None)

    async def red_delete_data_for_user(self, *, requester, user_id: int) -> None:
        for guild_id in await self.config.all_guilds():
            await self.config.member_from_ids(guild_id, user_id).clear()


async def setup(bot: Red) -> None:
    await bot.add_cog(OnePieceGuess(bot))
