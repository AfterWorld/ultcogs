import asyncio
import copy
import logging
import random
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import discord
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify

from .content import CANDIES
from .engine import matches, season, tally

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
            enabled=False, channel=None, october_only=True, utc_offset=-300,
            messages=12, users=3, cooldown=600, timeout=120,
            milestones={}, next_reward=1, values={}, seasons={},
        )
        self.locks = {}
        self.activity = {}
        self.rounds = {}
        self.tasks = set()

    def lock(self, guild_id):
        return self.locks.setdefault(guild_id, asyncio.Lock())

    def cog_unload(self):
        for task in self.tasks:
            task.cancel()
        self.rounds.clear()

    def current_season(self, settings):
        return season(datetime.now(timezone.utc), settings["utc_offset"], settings["october_only"])

    async def red_delete_data_for_user(self, *, requester, user_id):
        for guild_id in await self.config.all_guilds():
            async with self.lock(guild_id):
                async with self.config.guild_from_id(guild_id).seasons() as seasons:
                    for records in seasons.values():
                        records.pop(str(user_id), None)
                activity = self.activity.get(guild_id)
                if activity:
                    activity["speakers"].discard(user_id)
                    activity["last"].pop(user_id, None)

    async def send(self, channel, text=None, **kwargs):
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
            await self.send(round_["channel"], text)
            try:
                await round_["message"].edit(embed=discord.Embed(
                    title="🍬 Candy round finished", description=text, color=0xED8936,
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
        candy_id = random.choices(list(CANDIES), weights=[c["weight"] for c in CANDIES.values()])[0]
        candy = CANDIES[candy_id]
        points = settings["values"].get(candy_id, candy["points"])
        photo = PHOTOS / candy["file"]
        if not photo.is_file():
            log.error("Missing bundled candy photo: %s", photo)
            return False
        embed = discord.Embed(
            title="🎃 A candy appeared!", color=0xED8936,
            description=f"Type its name in this channel to catch it!\nFirst correct guess wins **{points} points**.\n"
                        f"You have **{settings['timeout']} seconds**. Use the candy hint command for a clue.",
        )
        embed.set_image(url="attachment://mystery.jpg")
        embed.set_footer(text=f"Photo: {candy['author']} • {candy['license']} • Source revealed after the round")
        with closing(discord.File(photo, filename="mystery.jpg")) as file:
            posted = await self.send(channel, embed=embed, file=file)
        if not posted:
            return False
        round_ = dict(candy=candy, candy_id=candy_id, points=points, channel=channel,
                      message=posted, season=self.current_season(settings),
                      deadline=time.monotonic() + settings["timeout"], timeout=settings["timeout"])
        self.rounds[channel.guild.id] = round_
        self.activity[channel.guild.id] = dict(count=0, speakers=set(), last={}, started=time.monotonic())
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
            year = self.current_season(settings)
            if not year:
                await self.finish(guild_id, "The October candy hunt has closed. Thanks for playing!")
                self.activity.pop(guild_id, None)
                return
            now = time.monotonic()
            round_ = self.rounds.get(guild_id)
            if round_:
                if now >= round_["deadline"] or year != round_["season"]:
                    await self.finish(guild_id, f"The candy escaped! It was **{round_['candy']['name']}**.")
                    return
                if message.id <= round_["message"].id or not matches(message.content, round_["candy"]):
                    return
                # The guild lock covers claiming AND persisting so simultaneous guesses cannot both win.
                async with self.config.guild(message.guild).seasons() as seasons:
                    records = seasons.setdefault(year, {})
                    record = records.setdefault(str(message.author.id), copy.deepcopy(EMPTY))
                    earned = tally(record, round_["candy_id"], round_["points"], settings["milestones"])
                    total = record["points"]
                reward_text = "".join(f"\n🏆 {r['label']} (+{r['bonus']} bonus points)" for r in earned)
                candy = round_["candy"]
                await self.finish(guild_id,
                    f"{message.author.mention} caught **{candy['name']}**! +{round_['points']} points • Total: **{total}**"
                    f"{reward_text}")
                return
            # Commands and repeated messages from one person do not accelerate spawns.
            if (await self.bot.get_context(message)).valid:
                return
            activity = self.activity.setdefault(guild_id, dict(count=0, speakers=set(), last={}, started=now))
            if now - activity["last"].get(message.author.id, float("-inf")) < 20:
                return
            activity["last"] = {uid: stamp for uid, stamp in activity["last"].items() if now - stamp < 20}
            activity["last"][message.author.id] = now
            activity["count"] += 1
            activity["speakers"].add(message.author.id)
            if (activity["count"] >= settings["messages"] and len(activity["speakers"]) >= settings["users"]
                    and now - activity["started"] >= settings["cooldown"]):
                if not await self.spawn(message.channel, settings):
                    activity["started"] = now  # Back off when uploads/permissions fail.

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def candy(self, ctx):
        """Candy hunt rules and player commands."""
        await ctx.send("🎃 Chat in the hunt channel. When a photo appears, type the candy's name! "
                       "First correct guess collects it. Bigger/rare candies give more points.\n"
                       "Commands: `candy bag`, `candy top`, `candy rewards`, `candy hint`, `candy catalog`.")

    @candy.command()
    async def bag(self, ctx, member: discord.Member = None, year: int = None):
        """Show a collection for this year or a specified year."""
        member = member or ctx.author
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(datetime.now(timezone.utc), settings["utc_offset"], False)
        record = settings["seasons"].get(year, {}).get(str(member.id), EMPTY)
        lines = [f"**{discord.utils.escape_markdown(member.display_name)} — {year}**",
                 f"{record['points']} points • {record['caught']} candies"]
        lines.extend(f"{c['name']}: {record['bag'].get(key, 0)}" for key, c in CANDIES.items())
        lines.append("Earned milestone IDs: " + (", ".join(record["earned"]) or "None"))
        await ctx.send("\n".join(lines), allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    async def top(self, ctx, year: int = None):
        """Top 10 collectors by points (then candy count)."""
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(datetime.now(timezone.utc), settings["utc_offset"], False)
        records = settings["seasons"].get(year, {})
        leaders = sorted(records.items(), key=lambda item: (-item[1]["points"], -item[1]["caught"], int(item[0])))[:10]
        lines = [f"🎃 **Candy leaderboard — {year}**"]
        for rank, (uid, record) in enumerate(leaders, 1):
            member = ctx.guild.get_member(int(uid))
            name = discord.utils.escape_markdown(member.display_name) if member else f"User {uid}"
            lines.append(f"{rank}. {name} — **{record['points']}** points ({record['caught']} candies)")
        await ctx.send("\n".join(lines) if leaders else "No candies collected yet.", allowed_mentions=discord.AllowedMentions.none())

    @candy.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def hint(self, ctx):
        """Show the current candy's clue."""
        async with self.lock(ctx.guild.id):
            round_ = self.rounds.get(ctx.guild.id)
            if not round_ or ctx.channel.id != round_["channel"].id or time.monotonic() >= round_["deadline"]:
                return await ctx.send("No active candy here.")
            await ctx.send(f"🔎 {round_['candy']['hint']}")

    @candy.command()
    async def catalog(self, ctx):
        """Candy IDs, values, rarity, aliases, and photo credits."""
        values = await self.config.guild(ctx.guild).values()
        text = "\n".join(f"**{key}** — {c['name']}: {values.get(key, c['points'])} points, {c['weight']}% chance\n"
                         f"Aliases: {', '.join(c['aliases'])}\nPhoto: {c['author']}, {c['license']} — "
                         f"https://commons.wikimedia.org/wiki/File:{quote(c['source'])}"
                         + (f" • {c['license_url']}" if c.get('license_url') else '')
                         for key, c in CANDIES.items())
        for page in pagify(text):
            await ctx.send(page)

    @candy.command()
    async def rewards(self, ctx):
        """View custom collection milestones. Physical/custom prizes are delivered by staff."""
        rewards = await self.config.guild(ctx.guild).milestones()
        text = "\n".join(f"#{key}: Collect {r['count']} × {r['candy']} → {r['label']} (+{r['bonus']} points)"
                         for key, r in rewards.items()) or "No milestones configured yet. Each catch still earns points!"
        for page in pagify(text):
            await ctx.send(page, allowed_mentions=discord.AllowedMentions.none())

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def candyset(self, ctx):
        """Configure the candy hunt."""
        s = await self.config.guild(ctx.guild).all()
        await ctx.send(f"Enabled: {s['enabled']} • Channel: {s['channel']} • October only: {s['october_only']}\n"
                       f"UTC offset: {s['utc_offset']} minutes • Spawn after {s['messages']} messages from {s['users']} users\n"
                       f"Cooldown: {s['cooldown']}s • Guess window: {s['timeout']}s\nUse help candyset for commands.")

    async def setting(self, ctx, key, value):
        async with self.lock(ctx.guild.id):
            await self.config.guild(ctx.guild).get_attr(key).set(value)
            if key in ("enabled", "channel", "october_only", "utc_offset"):
                await self.finish(ctx.guild.id, "Round closed because the hunt settings changed.")
                self.activity.pop(ctx.guild.id, None)
        await ctx.tick()

    @candyset.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        """Choose the channel (e.g. #general)."""
        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links and perms.attach_files):
            return await ctx.send("I need View Channel, Send Messages, Embed Links and Attach Files there.")
        await self.setting(ctx, "channel", channel.id)

    @candyset.command()
    async def enabled(self, ctx, enabled: bool):
        """Enable or pause spawns and guessing."""
        if enabled and not await self.config.guild(ctx.guild).channel():
            return await ctx.send("Set a hunt channel first.")
        await self.setting(ctx, "enabled", enabled)

    @candyset.command(name="october")
    async def october(self, ctx, enabled: bool):
        """Restrict play to October (true by default). False allows off-season tests."""
        await self.setting(ctx, "october_only", enabled)

    @candyset.command()
    async def offset(self, ctx, minutes: int):
        """Local UTC offset in minutes. Chicago in October: -300."""
        if not -720 <= minutes <= 840:
            return await ctx.send("Use an offset from -720 to 840 minutes.")
        await self.setting(ctx, "utc_offset", minutes)

    @candyset.command()
    async def pace(self, ctx, messages: int, users: int, cooldown: int, timeout: int):
        """Set message threshold, distinct users, cooldown seconds, guess seconds."""
        if not (1 <= users <= messages <= 1000 and 30 <= cooldown <= 86400 and 15 <= timeout <= 600):
            return await ctx.send("Require 1 ≤ users ≤ messages ≤ 1000, cooldown 30–86400s, timeout 15–600s.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).all() as settings:
                settings.update(messages=messages, users=users, cooldown=cooldown, timeout=timeout)
            self.activity.pop(ctx.guild.id, None)
        await ctx.tick()

    @candyset.command()
    async def value(self, ctx, candy_id: str, points: int):
        """Change one candy's points for future spawns. See candy catalog for IDs."""
        if candy_id not in CANDIES or not 1 <= points <= 100000:
            return await ctx.send("Use a catalog candy ID and 1–100000 points.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).values() as values:
                values[candy_id] = points
        await ctx.tick()

    @candyset.command()
    async def reward(self, ctx, candy_id: str, count: int, bonus: int, *, label: str):
        """Add milestone: reward corn 10 100 Candy Corn Champion. Use any for total catches."""
        if candy_id not in CANDIES and candy_id != "any":
            return await ctx.send("Use a catalog ID or any.")
        if not (1 <= count <= 100000 and 0 <= bonus <= 100000 and 1 <= len(label) <= 150):
            return await ctx.send("Count 1–100000, bonus 0–100000, label 1–150 characters.")
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).all() as settings:
                if len(settings["milestones"]) >= 50:
                    return await ctx.send("Maximum 50 milestones. Remove one first.")
                key = str(settings["next_reward"])
                settings["next_reward"] += 1
                settings["milestones"][key] = dict(candy=candy_id, count=count, bonus=bonus, label=label)
        await ctx.send(f"Added milestone #{key}. Bonus awarded once per player per year, on their next qualifying catch.")

    @candyset.command()
    async def unreward(self, ctx, reward_id: str):
        """Remove a milestone. Previously earned points remain."""
        async with self.lock(ctx.guild.id):
            async with self.config.guild(ctx.guild).milestones() as rewards:
                removed = rewards.pop(reward_id, None)
        await ctx.send("Milestone removed." if removed else "Unknown milestone ID.")

    @candyset.command()
    async def winners(self, ctx, reward_id: str, year: int = None):
        """List players who earned a milestone, for staff to deliver custom prizes."""
        settings = await self.config.guild(ctx.guild).all()
        year = str(year) if year else season(datetime.now(timezone.utc), settings["utc_offset"], False)
        lines = [f"**Milestone #{reward_id} winners — {year}**"]
        for uid, record in settings["seasons"].get(year, {}).items():
            if reward_id in record["earned"]:
                member = ctx.guild.get_member(int(uid))
                name = discord.utils.escape_markdown(member.display_name) if member else "Former member"
                lines.append(f"{name} — ID {uid}")
        if len(lines) == 1:
            lines.append("No winners yet.")
        for page in pagify("\n".join(lines)):
            await ctx.send(page, allowed_mentions=discord.AllowedMentions.none())

    @candyset.command(name="spawn")
    async def manual_spawn(self, ctx):
        """Spawn in the configured channel immediately, bypassing activity/cooldown."""
        async with self.lock(ctx.guild.id):
            settings = await self.config.guild(ctx.guild).all()
            if not settings["enabled"] or not self.current_season(settings):
                return await ctx.send("Enable the hunt during October, or turn off October restriction for testing.")
            channel = ctx.guild.get_channel(settings["channel"])
            if not channel or ctx.guild.id in self.rounds:
                return await ctx.send("Missing hunt channel or a candy is already active.")
            success = await self.spawn(channel, settings)
        await ctx.send("Candy spawned!" if success else "Spawn failed. Check channel permissions and bundled photos.")
