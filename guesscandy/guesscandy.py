import asyncio
import copy
import logging
import random
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.parse import quote

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify

from .content import CANDIES, SETS, SIZES
from .engine import (catch_points, cooldown_delay, daily_goals, eligible_candies,
                     goal_progress, is_finale, local_time, matches, season, standings, tally)

log = logging.getLogger("red.guesscandy")
PHOTOS = Path(__file__).parent / "photos"
EMPTY = {"points": 0, "caught": 0, "bag": {}, "earned": []}


class GuessCandy(commands.Cog):
    """Talk, spot a candy, and type its name to collect it!"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=92463020261001, force_registration=True)
        # ponytail: yearly guild tallies suit community events; use per-member storage for very large servers.
        self.config.register_guild(
            enabled=False, channel=None, october_only=True, utc_offset="America/New_York", clock_version=0,
            messages=12, users=3, cooldown=600, timeout=120,
            milestones={}, next_reward=1, values={}, seasons={},
            jitter=30, finale=True, announcements={}, final_standings={}, set_rewards={},
        )
        self.locks = {}
        self.activity = {}
        self.rounds = {}
        self.tasks = set()

    async def cog_load(self):
        for guild_id, stored in (await self.config.all_guilds()).items():
            if stored.get("clock_version", 0) < 1:
                group = self.config.guild_from_id(guild_id)
                if stored.get("utc_offset", -300) == -300:
                    await group.utc_offset.set("America/New_York")
                await group.clock_version.set(1)
        task = asyncio.create_task(self.event_loop())
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def now(self):
        return datetime.now(timezone.utc)

    def fresh_activity(self, settings):
        now = time.monotonic()
        return dict(count=0, speakers=set(), last={}, started=now,
                    ready=now + cooldown_delay(settings["cooldown"], settings["jitter"]))

    def collection_rewards(self, settings):
        return {key: dict(reward, **settings["set_rewards"].get(key, {})) for key, reward in SETS.items()}

    async def event_loop(self):
        await self.bot.wait_until_red_ready()
        while True:
            try:
                await self.event_tick(self.now())
            except Exception:
                log.exception("Candy calendar check failed")
            await asyncio.sleep(60)

    async def event_tick(self, now):
        for guild_id in await self.config.all_guilds():
            guild = self.bot.get_guild(guild_id)
            if not guild or await self.bot.cog_disabled_in_guild(self, guild):
                continue
            async with self.lock(guild_id):
                settings = await self.config.guild(guild).all()
                if settings["enabled"]:
                    await self.process_events(guild, settings, now)

    def leaderboard_text(self, guild, rows, title):
        lines = [f"🎃 **{title}**"]
        for rank, row in enumerate(rows[:10], 1):
            member = guild.get_member(int(row["user"]))
            name = discord.utils.escape_markdown(member.display_name) if member else f"User {row['user']}"
            lines.append(f"{['🥇', '🥈', '🥉'][rank-1] if rank <= 3 else str(rank) + '.'} {name} — **{row['points']:,}** points ({row['caught']} candies)")
        return "\n".join(lines) if rows else "No candies collected yet."

    async def process_events(self, guild, settings, now):
        """Caller holds guild lock; announcements retry after failures and survive reloads."""
        if not settings["finale"]:
            return
        channel = guild.get_channel(settings["channel"])
        if not channel:
            return
        local = local_time(now, settings["utc_offset"])
        year = str(local.year)
        if is_finale(now, settings["utc_offset"]):
            if not settings["announcements"].get(year, {}).get("finale"):
                sent = await self.send(channel, "🎃 **Halloween Finale!** Today all candy catches earn **double points**, "
                                       "and Reese's Big Cup + Chocolate Gold Coins can appear! "
                                       "Collection and daily bonuses keep their normal values.")
                if sent:
                    async with self.config.guild(guild).announcements() as announcements:
                        announcements.setdefault(year, {})["finale"] = True
        # Recover missed final announcements after downtime, including across New Year.
        for closed_year, records in settings["seasons"].items():
            if local < datetime(int(closed_year), 11, 1, tzinfo=local.tzinfo) or not records:
                continue
            if settings["announcements"].get(closed_year, {}).get("final"):
                continue
            rows = settings["final_standings"].get(closed_year)
            if rows is None:
                rows = standings(records)
                async with self.config.guild(guild).final_standings() as saved:
                    saved[closed_year] = rows
            await self.finish(guild.id, "The October candy hunt has closed. Thanks for playing!")
            sent = await self.send(channel, self.leaderboard_text(guild, rows, f"Final candy standings — {closed_year}"))
            if sent:
                async with self.config.guild(guild).announcements() as announcements:
                    announcements.setdefault(closed_year, {})["final"] = True

    def lock(self, guild_id):
        return self.locks.setdefault(guild_id, asyncio.Lock())

    def cog_unload(self):
        for task in self.tasks:
            task.cancel()
        self.rounds.clear()

    def current_season(self, settings):
        return season(self.now(), settings["utc_offset"], settings["october_only"])

    async def red_delete_data_for_user(self, *, requester, user_id):
        for guild_id in await self.config.all_guilds():
            async with self.lock(guild_id):
                async with self.config.guild_from_id(guild_id).seasons() as seasons:
                    for records in seasons.values():
                        records.pop(str(user_id), None)
                async with self.config.guild_from_id(guild_id).final_standings() as saved:
                    for year, rows in saved.items():
                        saved[year] = [row for row in rows if row["user"] != str(user_id)]
                activity = self.activity.get(guild_id)
                if activity:
                    activity["speakers"].discard(user_id)
                    activity["last"].pop(user_id, None)

    def card(self, text, title="🎃 Guess the Candy"):
        embed = discord.Embed(title=title[:256], description=text, color=0xF59E0B)
        embed.set_footer(text="🍬 October Candy Hunt • Collect • Complete • Climb")
        return embed

    async def reply(self, ctx, text, *, title="🎃 Guess the Candy", **kwargs):
        kwargs.pop("allowed_mentions", None)
        if title == "🎃 Guess the Candy" and getattr(ctx, "command", None):
            title = "🍬 " + ctx.command.qualified_name.replace("candyset", "Hunt Settings").replace("candy", "Candy").title()
        for page in pagify(text):
            await self.send(ctx, embed=self.card(page, title), **kwargs)

    async def send(self, channel, text=None, **kwargs):
        if text is not None:
            kwargs["embed"] = self.card(text)
            text = None
        try:
            return await channel.send(text, allowed_mentions=discord.AllowedMentions.none(), **kwargs)
        except discord.HTTPException:
            log.warning("Could not send candy message in channel %s", channel.id, exc_info=True)
            return None

    async def finish(self, guild_id, text):
        round_ = self.rounds.pop(guild_id, None)
        if round_:
            candy = round_["candy"]
            source = "https://commons.wikimedia.org/wiki/File:" + quote(candy["source"])
            text += f"\n[Photo source]({source}) • {candy['author']} • {candy['license']}"
            if candy.get("license_url"):
                text += f" • [License]({candy['license_url']})"
            if candy["changes"] != "None":
                text += f" • {candy['changes']}"
            for page in pagify(text):
                await self.send(round_["channel"], page)
            try:
                await round_["message"].edit(embed=discord.Embed(
                    title="🍬 Candy round finished", description=text[:4000], color=0xED8936,
                ))
            except discord.HTTPException:
                pass

    async def expire(self, guild_id, round_):
        try:
            await asyncio.sleep(round_["timeout"])
            async with self.lock(guild_id):
                if self.rounds.get(guild_id) is round_:
                    await self.finish(guild_id, f"The candy escaped! It was **{round_['candy']['name']}**.")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Candy expiry failed for guild %s", guild_id)

    async def spawn(self, channel, settings):
        """Caller holds the guild lock."""
        permissions = channel.permissions_for(channel.guild.me)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links and permissions.attach_files):
            return False
        now = self.now()
        local = local_time(now, settings["utc_offset"])
        finale = is_finale(now, settings["utc_offset"], settings["finale"])
        pool = eligible_candies(finale)
        candy_id = random.choices(list(pool), weights=[c["weight"] for c in pool.values()])[0]
        candy = CANDIES[candy_id]
        size = random.choices(list(SIZES), weights=[s["weight"] for s in SIZES.values()])[0]
        points = catch_points(settings["values"].get(candy_id, candy["points"]), size, finale)
        photo = PHOTOS / candy["file"]
        if not photo.is_file():
            log.error("Missing bundled candy photo: %s", photo)
            return False
        midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        remaining = max(0, min(settings["timeout"], (midnight.astimezone(timezone.utc) - now).total_seconds()))
        closes = int(now.timestamp() + remaining)
        cutoff_note = "\n🌙 Ends at midnight when daily goals reset." if remaining < settings["timeout"] else ""
        event_note = "🎉 Halloween double points are included!\n" if finale else ""
        embed = discord.Embed(
            title=f"🎃 A {SIZES[size]['label'].lower()} candy appeared!", color=0xED8936,
            description=f"Type its name in this channel to catch it!\nFirst correct guess wins **{points} points**.\n"
                        f"{event_note}Ends <t:{closes}:R> • <t:{closes}:t>. Use `candy hint` for a clue.{cutoff_note}",
        )
        embed.set_image(url="attachment://mystery.jpg")
        embed.set_footer(text=f"Photo: {candy['author']} • {candy['license']} • "
                              + ("Resized preview • " if candy["changes"] != "None" else "")
                              + "Source revealed after the round")
        with closing(discord.File(photo, filename="mystery.jpg")) as file:
            posted = await self.send(channel, embed=embed, file=file)
        if not posted:
            return False
        round_ = dict(candy=candy, candy_id=candy_id, points=points, channel=channel,
                      message=posted, season=self.current_season(settings),
                      size=size, day=local.date().isoformat(),
                      deadline=time.monotonic() + settings["timeout"], timeout=settings["timeout"])
        # End at local midnight, so a previous day's size/event value cannot cross into the new day.
        remaining = max(0, min(settings["timeout"], (midnight.astimezone(timezone.utc) - self.now()).total_seconds()))
        round_.update(deadline=time.monotonic() + remaining, timeout=remaining)
        self.rounds[channel.guild.id] = round_
        self.activity[channel.guild.id] = self.fresh_activity(settings)
        task = asyncio.create_task(self.expire(channel.guild.id, round_))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot or message.webhook_id or not message.content:
            return
        if await self.bot.cog_disabled_in_guild(self, message.guild):
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        guild_id = message.guild.id
        async with self.lock(guild_id):
            settings = await self.config.guild(message.guild).all()
            if not settings["enabled"] or message.channel.id != settings["channel"]:
                return
            await self.process_events(message.guild, settings, self.now())
            year = self.current_season(settings)
            if not year:
                await self.finish(guild_id, "The October candy hunt has closed. Thanks for playing!")
                self.activity.pop(guild_id, None)
                return
            now = time.monotonic()
            round_ = self.rounds.get(guild_id)
            if round_:
                day = local_time(self.now(), settings["utc_offset"]).date().isoformat()
                if now >= round_["deadline"] or year != round_["season"] or day != round_["day"]:
                    await self.finish(guild_id, f"The candy escaped! It was **{round_['candy']['name']}**.")
                    return
                if message.id <= round_["message"].id or not matches(message.content, round_["candy"]):
                    return
                # The guild lock covers claiming AND persisting so simultaneous guesses cannot both win.
                async with self.config.guild(message.guild).seasons() as seasons:
                    records = seasons.setdefault(year, {})
                    record = records.setdefault(str(message.author.id), copy.deepcopy(EMPTY))
                    earned = tally(record, round_["candy_id"], round_["points"], settings["milestones"],
                                   day=day, size=round_["size"], sets=self.collection_rewards(settings))
                    total = record["points"]
                reward_text = "".join(f"\n🏆 {r['label']} (+{r['bonus']} bonus points)" for r in earned)
                candy = round_["candy"]
                await self.finish(guild_id,
                    f"{message.author.mention} caught **{SIZES[round_['size']]['label']} {candy['name']}**! "
                    f"+{round_['points']} points • Total: **{total}**"
                    f"{reward_text}")
                return
            # Commands and repeated messages from one person do not accelerate spawns.
            if (await self.bot.get_context(message)).valid:
                return
            activity = self.activity.get(guild_id)
            if activity is None:
                activity = self.activity[guild_id] = self.fresh_activity(settings)
            if now - activity["last"].get(message.author.id, float("-inf")) < 20:
                return
            activity["last"] = {uid: stamp for uid, stamp in activity["last"].items() if now - stamp < 20}
            activity["last"][message.author.id] = now
            activity["count"] += 1
            activity["speakers"].add(message.author.id)
            if (activity["count"] >= settings["messages"] and len(activity["speakers"]) >= settings["users"]
                    and now >= activity["ready"]):
                if not await self.spawn(message.channel, settings):
                    activity["ready"] = now + cooldown_delay(settings["cooldown"], settings["jitter"])

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def candy(self, ctx):
        """Candy hunt rules and player commands."""
        settings = await self.config.guild(ctx.guild).all()
        local = local_time(self.now(), settings["utc_offset"])
        opens = int(datetime(local.year, 10, 1, tzinfo=local.tzinfo).timestamp())
        closes = int(datetime(local.year, 11, 1, tzinfo=local.tzinfo).timestamp())
        await self.reply(ctx, "🎃 Chat in the hunt channel. When a photo appears, type the candy's name! "
                       "First correct guess collects it. Bigger/rare candies give more points.\n"
                       "Commands: `candy bag`, `candy top`, `candy daily`, `candy sets`, `candy finals`, "
                       "`candy rewards`, `candy hint`, `candy catalog`.\n\n"
                       f"🗓️ Season opens <t:{opens}:F> and closes <t:{closes}:F>.\n"
                       f"Clock: **{local.tzname()}**. Daily goals reset at midnight; season points stay.\n"
                       + ("October restriction is off for testing." if not settings["october_only"] else ""),
                       title="🎃 Welcome to the Candy Hunt")

    @candy.command()
    async def bag(self, ctx, member: discord.Member = None, year: int = None):
        """Show a collection for this year or a specified year."""
        member = member or ctx.author
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(self.now(), settings["utc_offset"], False)
        record = settings["seasons"].get(year, {}).get(str(member.id), EMPTY)
        lines = [f"**{discord.utils.escape_markdown(member.display_name)} — {year}**",
                 f"{record['points']} points • {record['caught']} candies"]
        lines.extend(f"{c['name']}: {record['bag'].get(key, 0)}" for key, c in CANDIES.items())
        lines.append("Earned milestone IDs: " + (", ".join(record["earned"]) or "None"))
        lines.append("Sizes: " + ", ".join(f"{s['label']}: {record.get('sizes', {}).get(key, 0)}" for key, s in SIZES.items()))
        lines.append("Completed sets: " + (", ".join(SETS[key]["label"] for key in record.get("sets", []) if key in SETS) or "None"))
        for page in pagify("\n".join(lines)):
            await self.reply(ctx, page, allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    async def top(self, ctx, year: int = None):
        """Top 10 collectors by points (then candy count)."""
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(self.now(), settings["utc_offset"], False)
        records = settings["seasons"].get(year, {})
        await self.reply(ctx, self.leaderboard_text(ctx.guild, standings(records), f"Candy leaderboard — {year}"),
                       allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    async def daily(self, ctx):
        """Today's rotating goals and your progress. Bonuses are automatic."""
        settings = await self.config.guild(ctx.guild).all()
        local = local_time(self.now(), settings["utc_offset"])
        record = settings["seasons"].get(str(local.year), {}).get(str(ctx.author.id), {})
        daily = record.get("daily", {})
        if daily.get("date") != local.date().isoformat():
            daily = {}
        lines = [f"🎯 **Daily goals — {local.date()}**"]
        for goal in daily_goals(local.date().isoformat()):
            progress = min(goal["target"], goal_progress(goal, daily))
            status = "✅" if goal["id"] in daily.get("earned", []) else "⬜"
            filled = int(8 * progress / goal["target"])
            bar = "▰" * filled + "▱" * (8 - filled)
            lines.append(f"{status} **{goal['label']}**\n{bar} {progress}/{goal['target']} • **+{goal['bonus']} points**")
        await self.reply(ctx, "\n\n".join(lines) + f"\n\n🌙 Daily reset: midnight {local.tzname()}. Your season tally stays.")

    @candy.command(name="sets")
    async def collection_sets(self, ctx):
        """Collection sets, missing candies, and automatic bonus points."""
        settings = await self.config.guild(ctx.guild).all()
        year = season(self.now(), settings["utc_offset"], False)
        record = settings["seasons"].get(year, {}).get(str(ctx.author.id), {})
        lines = ["🏆 **Collection sets**"]
        for key, reward in self.collection_rewards(settings).items():
            missing = [CANDIES[c]["name"] for c in reward["candies"] if not record.get("bag", {}).get(c)]
            status = "✅" if key in record.get("sets", []) else "⬜"
            lines.append(f"{status} **{reward['label']}** (+{reward['bonus']} points)\n"
                         + ("Missing: " + ", ".join(missing) if missing else "Collection complete"))
            if reward.get("prize"):
                lines.append(f"Custom reward: {reward['prize']} (staff-delivered)")
        for page in pagify("\n".join(lines)):
            await self.reply(ctx, page, allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    async def finals(self, ctx, year: int = None):
        """Saved standings from the end of October."""
        async with self.lock(ctx.guild.id):
            settings = await self.config.guild(ctx.guild).all()
            if settings["enabled"]:
                await self.process_events(ctx.guild, settings, self.now())
            saved = await self.config.guild(ctx.guild).final_standings()
        if year is None:
            year = max(saved, key=int) if saved else None
        rows = saved.get(str(year))
        await self.reply(ctx, self.leaderboard_text(ctx.guild, rows, f"Final candy standings — {year}")
                       if rows is not None else "No final standings saved yet. October closes on November 1.",
                       allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def hint(self, ctx):
        """Show the current candy's clue."""
        async with self.lock(ctx.guild.id):
            round_ = self.rounds.get(ctx.guild.id)
            if not round_ or ctx.channel.id != round_["channel"].id or time.monotonic() >= round_["deadline"]:
                return await self.reply(ctx, "No active candy here.")
            await self.reply(ctx, f"🔎 {round_['candy']['hint']}")

    @candy.command()
    async def catalog(self, ctx):
        """Candy IDs, values, rarity, aliases, and photo credits."""
        values = await self.config.guild(ctx.guild).values()
        total_weight = sum(c["weight"] for c in eligible_candies(False).values())
        text = "\n".join(f"**{key}** — {c['name']}: {values.get(key, c['points'])} base points, "
                         + ("Halloween finale only" if c["finale_only"] else f"{100*c['weight']/total_weight:.1f}% normal spawn chance") + "\n"
                         f"Aliases: {', '.join(c['aliases'])}\nPhoto: {c['author']}, {c['license']} — "
                         f"https://commons.wikimedia.org/wiki/File:{quote(c['source'])}"
                         + (f" • {c['license_url']}" if c.get('license_url') else '')
                         + (f" • {c['changes']}" if c['changes'] != "None" else '')
                         for key, c in CANDIES.items())
        for page in pagify(text):
            await self.reply(ctx, page)

    @candy.command()
    async def rewards(self, ctx):
        """View custom collection milestones. Physical/custom prizes are delivered by staff."""
        rewards = await self.config.guild(ctx.guild).milestones()
        text = "\n".join(f"#{key}: Collect {r['count']} × {r['candy']} → {r['label']} (+{r['bonus']} points)"
                         for key, r in rewards.items()) or "No milestones configured yet. Each catch still earns points!"
        for page in pagify(text):
            await self.reply(ctx, page, allowed_mentions=discord.AllowedMentions.none())

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def candyset(self, ctx):
        """Configure the candy hunt."""
        s = await self.config.guild(ctx.guild).all()
        await self.reply(ctx, f"Enabled: {s['enabled']} • Channel: {s['channel']} • October only: {s['october_only']}\n"
                       f"Clock: {local_time(self.now(), s['utc_offset']).tzname()} ({s['utc_offset']}) • Spawn after {s['messages']} messages from {s['users']} users\n"
                       f"Cooldown: {s['cooldown']}s ±{s['jitter']}% • Guess window: {s['timeout']}s\n"
                       f"Halloween finale: {s['finale']} • Use help candyset for commands.")

    async def setting(self, ctx, key, value):
        async with self.lock(ctx.guild.id):
            await self.config.guild(ctx.guild).get_attr(key).set(value)
            if key in ("enabled", "channel", "october_only", "utc_offset", "finale"):
                await self.finish(ctx.guild.id, "Round closed because the hunt settings changed.")
                self.activity.pop(ctx.guild.id, None)
            if key == "jitter":
                self.activity.pop(ctx.guild.id, None)
        await self.reply(ctx, "Your hunt settings have been saved.", title="✅ Settings updated")

    @candyset.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Choose the channel (e.g. #general)."""
        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links and perms.attach_files):
            return await self.reply(ctx, "I need View Channel, Send Messages, Embed Links and Attach Files there.")
        await self.setting(ctx, "channel", channel.id)

    @candyset.command()
    async def enabled(self, ctx, enabled: bool):
        """Enable or pause spawns and guessing."""
        if enabled and not await self.config.guild(ctx.guild).channel():
            return await self.reply(ctx, "Set a hunt channel first.")
        await self.setting(ctx, "enabled", enabled)

    @candyset.command(name="october")
    async def october(self, ctx, enabled: bool):
        """Restrict play to October (true by default). False allows off-season tests."""
        await self.setting(ctx, "october_only", enabled)

    @candyset.command()
    async def offset(self, ctx, minutes: int):
        """Fixed UTC offset in minutes. EST: -300; EDT: -240. Prefer timezone Eastern."""
        if not -720 <= minutes <= 840:
            return await self.reply(ctx, "Use an offset from -720 to 840 minutes.")
        await self.setting(ctx, "utc_offset", minutes)

    @candyset.command(name="timezone")
    async def set_timezone(self, ctx, *, name: str = "Eastern"):
        """Use Eastern/New York time, fixed EST, UTC, or an IANA zone."""
        zone = {"eastern": "America/New_York", "est": -300, "edt": -240, "utc": "UTC"}.get(name.casefold(), name)
        try:
            if isinstance(zone, str):
                ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            return await self.reply(ctx, "Use Eastern, EST, UTC, or an IANA name such as America/New_York.")
        await self.setting(ctx, "utc_offset", zone)

    @candyset.command()
    async def pace(self, ctx, messages: int, users: int, cooldown: int, timeout: int):
        """Set message threshold, distinct users, cooldown seconds, guess seconds."""
        if not (1 <= users <= messages <= 1000 and 30 <= cooldown <= 86400 and 15 <= timeout <= 600):
            return await self.reply(ctx, "Require 1 ≤ users ≤ messages ≤ 1000, cooldown 30–86400s, timeout 15–600s.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).all() as settings:
                settings.update(messages=messages, users=users, cooldown=cooldown, timeout=timeout)
            self.activity.pop(ctx.guild.id, None)
        await self.reply(ctx, "Your hunt settings have been saved.", title="✅ Settings updated")

    @candyset.command()
    async def jitter(self, ctx, percent: int):
        """Randomize cooldown by this percentage (0–80, default 30)."""
        if not 0 <= percent <= 80:
            return await self.reply(ctx, "Use 0–80 percent. Zero makes the cooldown fixed.")
        await self.setting(ctx, "jitter", percent)

    @candyset.command()
    async def finale(self, ctx, enabled: bool):
        """Enable October 31 double catch points, special candies, and final announcements."""
        await self.setting(ctx, "finale", enabled)

    @candyset.command()
    async def value(self, ctx, candy_id: str, points: int):
        """Change one candy's points for future spawns. See candy catalog for IDs."""
        if candy_id not in CANDIES or not 1 <= points <= 100000:
            return await self.reply(ctx, "Use a catalog candy ID and 1–100000 points.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).values() as values:
                values[candy_id] = points
        await self.reply(ctx, "Your hunt settings have been saved.", title="✅ Settings updated")

    @candyset.command()
    async def reward(self, ctx, candy_id: str, count: int, bonus: int, *, label: str):
        """Add milestone: reward corn 10 100 Candy Corn Champion. Use any for total catches."""
        if candy_id not in CANDIES and candy_id != "any":
            return await self.reply(ctx, "Use a catalog ID or any.")
        if not (1 <= count <= 100000 and 0 <= bonus <= 100000 and 1 <= len(label) <= 150):
            return await self.reply(ctx, "Count 1–100000, bonus 0–100000, label 1–150 characters.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).all() as settings:
                if len(settings["milestones"]) >= 50:
                    return await self.reply(ctx, "Maximum 50 milestones. Remove one first.")
                key = str(settings["next_reward"])
                settings["next_reward"] += 1
                settings["milestones"][key] = dict(candy=candy_id, count=count, bonus=bonus, label=label)
        await self.reply(ctx, f"Added milestone #{key}. Bonus awarded once per player per year, on their next qualifying catch.")

    @candyset.command()
    async def setreward(self, ctx, set_id: str, bonus: int, *, prize: str):
        """Set bonus/custom prize for a collection set. Sets: chocolate fruity halloween retro bigbars."""
        if set_id not in SETS or not 0 <= bonus <= 100000 or not 1 <= len(prize) <= 150:
            return await self.reply(ctx, "Use a valid set ID, bonus 0–100000, and a prize description of 1–150 characters.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).set_rewards() as rewards:
                rewards[set_id] = dict(bonus=bonus, prize=prize)
        await self.reply(ctx, "Set reward updated for future completions. Use candyset winners set:" + set_id + " for staff delivery.")

    @candyset.command()
    async def unreward(self, ctx, reward_id: str):
        """Remove a milestone. Previously earned points remain."""
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).milestones() as rewards:
                removed = rewards.pop(reward_id, None)
        await self.reply(ctx, "Milestone removed." if removed else "Unknown milestone ID.")

    @candyset.command()
    async def winners(self, ctx, reward_id: str, year: int = None):
        """List milestone winners, or use set:chocolate etc. for collection-set prizes."""
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(self.now(), settings["utc_offset"], False)
        set_id = reward_id[4:] if reward_id.startswith("set:") else None
        if set_id is not None and set_id not in SETS:
            return await self.reply(ctx, "Unknown collection set ID.")
        title = SETS[set_id]["label"] if set_id else f"Milestone #{reward_id}"
        lines = [f"**{title} winners — {year}**"]
        for uid, record in settings["seasons"].get(year, {}).items():
            earned = set_id in record.get("sets", []) if set_id else reward_id in record["earned"]
            if earned:
                member = ctx.guild.get_member(int(uid))
                name = discord.utils.escape_markdown(member.display_name) if member else "Former member"
                lines.append(f"{name} — ID {uid}")
        if len(lines) == 1:
            lines.append("No winners yet.")
        for page in pagify("\n".join(lines)):
            await self.reply(ctx, page, allowed_mentions=discord.AllowedMentions.none())

    @candyset.command(name="spawn")
    async def manual_spawn(self, ctx):
        """Spawn in the configured channel immediately, bypassing activity/cooldown."""
        async with self.lock(ctx.guild.id):
            settings = await self.config.guild(ctx.guild).all()
            if not settings["enabled"] or not self.current_season(settings):
                return await self.reply(ctx, "Enable the hunt during October, or turn off October restriction for testing.")
            channel = ctx.guild.get_channel(settings["channel"])
            if not channel or ctx.guild.id in self.rounds:
                return await self.reply(ctx, "Missing hunt channel or a candy is already active.")
            success = await self.spawn(channel, settings)
        await self.reply(ctx, "Candy spawned!" if success else "Spawn failed. Check channel permissions and bundled photos.")
