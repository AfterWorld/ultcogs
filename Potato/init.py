import asyncio
import logging
import discord
from datetime import datetime
from redbot.core import commands, Config
from redbot.core.bot import Red
from .constants import GUILD_DEFAULTS, USER_DEFAULTS, EMBED_PENDING
from .utils import now_ts, decision_embed, log_action
from .views import SuggestionVotingView, SuggestionStaffView

log = logging.getLogger("red.suggestion")

class _Cache:
    def __init__(self): self._g = {}
    def get(self, gid): return self._g.get(gid)
    def set(self, gid, v): self._g[gid] = v
    def invalidate(self, gid): self._g.pop(gid, None)

class Suggestion(commands.Cog):
    """Suggestions with button voting, staff review, auto cleanup, and logs."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9258471035622, force_registration=True)
        self.config.register_guild(**GUILD_DEFAULTS)
        self.config.register_user(**USER_DEFAULTS)
        self._cache = _Cache()

        # persistent view templates
        self.bot.add_view(SuggestionVotingView(self, 0))
        self.bot.add_view(SuggestionStaffView(self, 0))

    async def cog_load(self):
        await self._restore_views()

    async def _restore_views(self):
        await self.bot.wait_until_ready()
        for g in list(self.bot.guilds):
            try:
                cfg = await self.get_guild_config(g)
                for sid, data in (cfg.get("suggestions") or {}).items():
                    if data.get("status") == "pending":
                        v = SuggestionVotingView(self, int(sid))
                        votes = data.get("votes", {"upvotes": [], "downvotes": []})
                        v.set_counts(len(votes.get("upvotes", [])), len(votes.get("downvotes", [])))
                        self.bot.add_view(v)
            except Exception:
                pass

    # ---------- helpers ----------
    async def get_guild_config(self, guild: discord.Guild) -> dict:
        cached = self._cache.get(guild.id)
        if cached: return cached
        data = await self.config.guild(guild).all()
        self._cache.set(guild.id, data)
        return data

    async def _save_guild_field(self, guild: discord.Guild, key: str, value):
        await self.config.guild(guild).set_raw(key, value=value)
        self._cache.invalidate(guild.id)

    # ---------- user command ----------
    @commands.command(name="suggest")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context, *, suggestion: str):
        cfg = await self.get_guild_config(ctx.guild)
        ch_id = cfg.get("suggestion_channel")
        if not ch_id:
            return await ctx.send("❌ Suggestion channel not set. Ask an admin to run `[p]suggestset channel #channel`.")
        if len(suggestion) < int(cfg.get("min_length", 10)):
            return await ctx.send(f"❌ Too short. Min length: {cfg.get('min_length')}")
        if len(suggestion) > int(cfg.get("max_length", 2000)):
            return await ctx.send(f"❌ Too long. Max length: {cfg.get('max_length')}")

        # cooldown per user (config seconds)
        cd = int(cfg.get("cooldown", 300))
        last = await self.config.user(ctx.author).last_suggest_ts()
        if last and (now_ts() - last) < cd:
            left = int(cd - (now_ts() - last))
            return await ctx.send(f"⏳ Cooldown active. Please wait **{left}s**.")

        sid = int(cfg.get("suggestion_count", 0)) + 1
        emb = discord.Embed(
            title=f"Suggestion #{sid}",
            description=suggestion,
            color=EMBED_PENDING,
            timestamp=datetime.utcnow()
        )
        if not cfg.get("anonymous_suggestions", False):
            emb.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            emb.set_footer(text=f"ID: {ctx.author.id}")
        emb.add_field(name="Votes", value="👍 0 | 👎 0", inline=True)

        channel = ctx.guild.get_channel(int(ch_id))
        if not channel:
            return await ctx.send("❌ Configured suggestion channel no longer exists.")
        view = SuggestionVotingView(self, sid)
        view.set_counts(0, 0)
        msg = await channel.send(embed=emb, view=view)

        # persist
        data = {
            "id": sid,
            "author_id": int(ctx.author.id),
            "content": suggestion,
            "channel_id": int(channel.id),
            "message_id": int(msg.id),
            "status": "pending",
            "created_at": int(now_ts()),
            "votes": {"upvotes": [], "downvotes": []},
            "staff_message_id": None
        }
        async with self.config.guild(ctx.guild).suggestions() as s:
            s[str(sid)] = data
        await self.config.guild(ctx.guild).suggestion_count.set(sid)
        await self.config.user(ctx.author).last_suggest_ts.set(int(now_ts()))
        await self.config.user(ctx.author).suggestions_made.set((await self.config.user(ctx.author).suggestions_made()) + 1)

        await log_action(self, ctx.guild, title="Suggestion Submitted", description=f"#{sid} by {ctx.author.mention}")
        await ctx.tick()

    # ---------- staff flow ----------
    async def _forward_to_staff(self, guild: discord.Guild, sid: str):
        cfg = await self.get_guild_config(guild)
        sdata = (cfg.get("suggestions") or {}).get(str(sid))
        if not sdata:
            return
        ch_id = cfg.get("staff_channel")
        if not ch_id:
            return
        ch = guild.get_channel(int(ch_id))
        if not ch:
            return
        author = guild.get_member(int(sdata["author_id"]))
        emb = discord.Embed(
            title=f"Staff Review — Suggestion #{sid}",
            description=sdata.get("content", ""),
            color=EMBED_PENDING,
            timestamp=datetime.utcnow()
        )
        if author:
            emb.set_author(name=str(author), icon_url=author.display_avatar.url)
        view = SuggestionStaffView(self, int(sid))
        msg = await ch.send(embed=emb, view=view)

        async with self.config.guild(guild).suggestions() as s:
            s[str(sid)]["staff_message_id"] = int(msg.id)
        await log_action(self, guild, title="Suggestion Forwarded", description=f"#{sid} → staff channel")

    async def _set_status(self, ctx: commands.Context, sid: int, status: str, reason: str = "", *, interaction: discord.Interaction = None):
        guild = ctx.guild
        cfg = await self.get_guild_config(guild)
        s = (cfg.get("suggestions") or {}).get(str(sid))
        if not s:
            return
        s["status"] = status
        s["decided_by"] = int(ctx.author.id)
        s["decided_at"] = int(now_ts())
        if reason:
            s["reason"] = reason
        await self.config.guild(guild).suggestions.set(cfg["suggestions"])
        author = guild.get_member(int(s.get("author_id", 0)))

        # edit original msg
        try:
            ch = guild.get_channel(int(s["channel_id"]))
            msg = await ch.fetch_message(int(s["message_id"]))
            await msg.edit(embed=decision_embed(sid, s["content"], status, author=author, moderator=ctx.author, reason=reason), view=None)
            if status == "denied" and cfg.get("auto_delete_denied", False):
                await asyncio.sleep(10)
                await msg.delete()
        except Exception:
            pass

        await log_action(self, guild, title=f"Suggestion {status.title()}", description=f"#{sid} by <@{s['author_id']}> — by {ctx.author.mention}")

        # DM author
        if author and cfg.get("dm_notifications", True):
            try:
                await author.send(embed=decision_embed(sid, s["content"], status, author=author, moderator=ctx.author, reason=reason))
            except Exception:
                pass

    # ---------- admin config ----------
    @commands.group(name="suggestionset", aliases=["suggestset"], invoke_without_command=True)
    @commands.admin_or_permissions(manage_guild=True)
    async def suggestset(self, ctx: commands.Context):
        await ctx.send_help()

    @suggestset.command(name="channel")
    async def _set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await self._save_guild_field(ctx.guild, "suggestion_channel", int(channel.id))
        await ctx.send(f"✅ Suggestion channel set to {channel.mention}")

    @suggestset.command(name="staffchannel")
    async def _set_staff_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await self._save_guild_field(ctx.guild, "staff_channel", int(channel.id))
        await ctx.send(f"✅ Staff review channel set to {channel.mention}")

    @suggestset.command(name="logchannel")
    async def _set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        await self._save_guild_field(ctx.guild, "log_channel", int(channel.id))
        await ctx.send(f"✅ Log channel set to {channel.mention}")

    @suggestset.command(name="threshold")
    async def _set_threshold(self, ctx: commands.Context, n: int):
        n = max(1, min(50, int(n)))
        await self._save_guild_field(ctx.guild, "upvote_threshold", n)
        await ctx.send(f"✅ Upvote threshold set to **{n}**")

    @suggestset.command(name="cooldown")
    async def _set_cooldown(self, ctx: commands.Context, seconds: int):
        seconds = max(0, int(seconds))
        await self._save_guild_field(ctx.guild, "cooldown", seconds)
        await ctx.send(f"✅ Cooldown set to **{seconds}s**")

    @suggestset.command(name="lengths")
    async def _set_lengths(self, ctx: commands.Context, minlen: int, maxlen: int):
        if minlen < 1 or maxlen < minlen:
            return await ctx.send("❌ Invalid min/max.")
        await self._save_guild_field(ctx.guild, "min_length", int(minlen))
        await self._save_guild_field(ctx.guild, "max_length", int(maxlen))
        await ctx.send(f"✅ Lengths set: **{minlen}–{maxlen}**")

    @suggestset.command(name="anonymous")
    async def _set_anon(self, ctx: commands.Context, toggle: bool):
        await self._save_guild_field(ctx.guild, "anonymous_suggestions", bool(toggle))
        await ctx.send(f"✅ Anonymous suggestions: {'ON' if toggle else 'OFF'}")

    @suggestset.command(name="dmnotify")
    async def _set_dm(self, ctx: commands.Context, toggle: bool):
        await self._save_guild_field(ctx.guild, "dm_notifications", bool(toggle))
        await ctx.send(f"✅ DM notifications: {'ON' if toggle else 'OFF'}")

    @suggestset.command(name="autodelete")
    async def _set_autodel(self, ctx: commands.Context, toggle: bool):
        await self._save_guild_field(ctx.guild, "auto_delete_denied", bool(toggle))
        await ctx.send(f"✅ Auto delete denied suggestions: {'ON' if toggle else 'OFF'}")

    @suggestset.command(name="modrole")
    async def _modrole(self, ctx: commands.Context, role: discord.Role, toggle: bool = True):
        cfg = await self.get_guild_config(ctx.guild)
        ids = set(int(x) for x in (cfg.get("modrole_ids") or []))
        if toggle: ids.add(int(role.id))
        else: ids.discard(int(role.id))
        await self._save_guild_field(ctx.guild, "modrole_ids", list(ids))
        await ctx.send(f"✅ `{role.name}` {'added to' if toggle else 'removed from'} moderator roles.")

    @suggestset.command(name="modroles")
    async def _modroles(self, ctx: commands.Context):
        cfg = await self.get_guild_config(ctx.guild)
        ids = [ctx.guild.get_role(int(i)) for i in (cfg.get("modrole_ids") or [])]
        names = ", ".join(r.mention for r in ids if r) or "*(none)*"
        await ctx.send(f"Moderator roles: {names}")

# red entrypoint
async def setup(bot: Red):
    await bot.add_cog(Suggestion(bot))
