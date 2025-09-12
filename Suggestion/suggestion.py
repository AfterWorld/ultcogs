from __future__ import annotations
import discord
import logging
from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from typing import Optional

from .constants import DEFAULT_CONFIG, COLORS, STATUS_EMOJIS
from .utils import error_embed, success_embed, iso_now, cooldown_passed
from .integration import RewardSystem

log = logging.getLogger("red.suggestions")

class Suggestion(commands.Cog):
    """Prefix-only suggestion system with rewards, thresholds, and logs."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9999999999, force_registration=True)
        self.config.register_guild(**DEFAULT_CONFIG)
        self.rewarder = RewardSystem(self)

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def suggest(self, ctx: commands.Context, *, text: str):
        """Submit a suggestion. Use '--anon' to hide your name."""
        guild = ctx.guild
        author = ctx.author
        conf = await self.config.guild(guild).all()

        if author.id in conf["blacklisted_users"]:
            return await ctx.send("You are not allowed to submit suggestions.")

        cooldowns = conf.get("cooldown_per_day", 1)
        stats = conf.get("stats", {})
        user_stats = stats.get(str(author.id), {})
        last_time = user_stats.get("last_submit", "1970-01-01T00:00:00")

        if not cooldown_passed(last_time, cooldowns):
            return await ctx.send("You've reached your daily suggestion limit.")

        suggestion_channel = guild.get_channel(conf["suggestion_channel"])
        if not suggestion_channel:
            return await ctx.send("Suggestion channel is not set.")

        next_id = conf["next_id"]
        anon = text.startswith("--anon")
        content = text[7:].strip() if anon else text.strip()

        embed = discord.Embed(
            title=f"{STATUS_EMOJIS['pending']} Suggestion #{next_id}",
            description=content[:2048],
            color=COLORS["pending"]
        )
        embed.add_field(name="Status", value="⏳ Pending", inline=False)
        if not anon:
            embed.set_footer(text=f"Suggested by {author.display_name}", icon_url=author.display_avatar.url)
        else:
            embed.set_footer(text="Anonymous Suggestion")

        msg = await suggestion_channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

        await self.config.guild(guild).suggestions.set_raw(str(next_id), value={
            "id": next_id,
            "author_id": author.id,
            "message_id": msg.id,
            "channel_id": msg.channel.id,
            "suggestion": content,
            "status": "pending",
            "timestamp": iso_now(),
            "anon": anon,
            "votes": []
        })
        await self.config.guild(guild).next_id.set(next_id + 1)

        user_stats["submitted"] = user_stats.get("submitted", 0) + 1
        user_stats["last_submit"] = iso_now()
        stats[str(author.id)] = user_stats
        await self.config.guild(guild).stats.set(stats)

        await ctx.send(embed=success_embed(f"Suggestion #{next_id} submitted!"))

        reward_amt = conf.get("reward_credits", 0)
        if reward_amt > 0:
            await self.rewarder.award(guild, author.id, reward_amt, suggestion_id=next_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) not in {"👍", "👎"}:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        conf = await self.config.guild(guild).all()
        suggestion_data = conf["suggestions"]
        target_id = None
        for sid, entry in suggestion_data.items():
            if entry.get("message_id") == payload.message_id:
                target_id = sid
                break
        if not target_id:
            return

        data = suggestion_data[target_id]
        if data.get("status") != "pending":
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        upvotes = 0
        downvotes = 0
        for r in message.reactions:
            if str(r.emoji) == "👍":
                upvotes = r.count
            elif str(r.emoji) == "👎":
                downvotes = r.count

        if upvotes >= conf["upvote_threshold"]:
            await self._resolve(message, guild, data, approved=True)
        elif downvotes >= conf["downvote_threshold"]:
            await self._resolve(message, guild, data, approved=False)

    async def _resolve(self, msg: discord.Message, guild: discord.Guild, data: dict, approved: bool):
        sid = str(data["id"])
        embed = msg.embeds[0]
        status = "✅ Approved" if approved else "❌ Declined"
        color = COLORS["approved"] if approved else COLORS["declined"]
        emoji = STATUS_EMOJIS["approved"] if approved else STATUS_EMOJIS["declined"]

        author = self.bot.get_user(data["author_id"])
        embed.color = color
        embed.title = f"{emoji} Suggestion #{sid}"
        embed.set_field_at(0, name="Status", value=status)
        embed.set_footer(text=f"{status} — Suggested by {author}", icon_url=author.display_avatar.url)

        await msg.edit(embed=embed)

        archive_id = await self.config.guild(guild).archive_channel()
        if archive_id:
            archive = guild.get_channel(archive_id)
            if archive:
                await archive.send(embed=embed)

        log_id = await self.config.guild(guild).log_channel()
        if log_id:
            log_chan = guild.get_channel(log_id)
            if log_chan:
                await log_chan.send(f"{status} automatically via votes.", embed=embed)

        stats = await self.config.guild(guild).stats()
        stats.setdefault(str(author.id), {})
        stats[str(author.id)]["approved"] = stats[str(author.id)].get("approved", 0) + int(approved)
        await self.config.guild(guild).stats.set(stats)

        data["status"] = "approved" if approved else "declined"
        await self.config.guild(guild).suggestions.set_raw(sid, value=data)

    @commands.group(name="suggestconfig", aliases=["suggestset"])
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def suggestconfig(self, ctx: commands.Context):
        """Configure the suggestion system."""
        pass

    @suggestconfig.command(name="setchannel")
    async def _setchan(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).suggestion_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Suggestion channel set to {channel.mention}"))

    @suggestconfig.command(name="setstaffchannel")
    async def _setstaffchan(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).staff_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Staff channel set to {channel.mention}"))

    @suggestconfig.command(name="setlogchannel")
    async def _setlogchan(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).log_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Log channel set to {channel.mention}"))

    @suggestconfig.command(name="setarchivechannel")
    async def _setarchivechan(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).archive_channel.set(channel.id)
        await ctx.send(embed=success_embed(f"Archive channel set to {channel.mention}"))

    @suggestconfig.command(name="reward")
    async def _setreward(self, ctx, amount: int):
        await self.config.guild(ctx.guild).reward_credits.set(max(0, amount))
        await ctx.send(embed=success_embed(f"Suggestions will reward `{amount}` credits/Beri."))

    @suggestconfig.command(name="usebericore")
    async def _togglebericore(self, ctx, toggle: bool):
        await self.config.guild(ctx.guild).use_beri_core.set(toggle)
        await ctx.send(embed=success_embed(f"BeriCore integration {'enabled' if toggle else 'disabled'}."))

    @suggestconfig.command(name="setthresholds")
    async def _thresholds(self, ctx, upvotes: int = 10, downvotes: int = 5):
        await self.config.guild(ctx.guild).upvote_threshold.set(upvotes)
        await self.config.guild(ctx.guild).downvote_threshold.set(downvotes)
        await ctx.send(embed=success_embed(f"Thresholds set: 👍 {upvotes} | 👎 {downvotes}"))

    @suggestconfig.command(name="cooldown")
    async def _cooldown(self, ctx, per_day: int = 1):
        await self.config.guild(ctx.guild).cooldown_per_day.set(max(0, per_day))
        await ctx.send(embed=success_embed(f"Users may submit up to {per_day} suggestions per day."))

    @suggestconfig.command(name="blacklist")
    async def _blacklist(self, ctx, action: str, user: discord.Member):
        ids = await self.config.guild(ctx.guild).blacklisted_users()
        if action == "add":
            ids.append(user.id)
            await self.config.guild(ctx.guild).blacklisted_users.set(list(set(ids)))
            await ctx.send(embed=success_embed(f"{user} is now blacklisted."))
        elif action == "remove":
            ids = [i for i in ids if i != user.id]
            await self.config.guild(ctx.guild).blacklisted_users.set(ids)
            await ctx.send(embed=success_embed(f"{user} is no longer blacklisted."))
        else:
            await ctx.send("Usage: `[p]suggestconfig blacklist add/remove @user`")

    @suggestconfig.command(name="approve")
    async def _approve(self, ctx, sid: int):
        conf = await self.config.guild(ctx.guild).all()
        data = conf["suggestions"].get(str(sid))
        if not data:
            return await ctx.send("Invalid ID.")
        if data["status"] != "pending":
            return await ctx.send("Already resolved.")

        chan = ctx.guild.get_channel(data["channel_id"])
        msg = await chan.fetch_message(data["message_id"])
        await self._resolve(msg, ctx.guild, data, approved=True)
        await ctx.send(f"Suggestion #{sid} manually approved.")

    @suggestconfig.command(name="decline")
    async def _decline(self, ctx, sid: int):
        conf = await self.config.guild(ctx.guild).all()
        data = conf["suggestions"].get(str(sid))
        if not data:
            return await ctx.send("Invalid ID.")
        if data["status"] != "pending":
            return await ctx.send("Already resolved.")

        chan = ctx.guild.get_channel(data["channel_id"])
        msg = await chan.fetch_message(data["message_id"])
        await self._resolve(msg, ctx.guild, data, approved=False)
        await ctx.send(f"Suggestion #{sid} manually declined.")

    @commands.command()
    @commands.guild_only()
    async def suggesttop(self, ctx):
        """Show top suggesters and approvals."""
        stats = await self.config.guild(ctx.guild).stats()
        if not stats:
            return await ctx.send("No stats yet.")
        sorted_stats = sorted(stats.items(), key=lambda x: x[1].get("approved", 0), reverse=True)
        lines = []
        for uid, s in sorted_stats[:10]:
            user = ctx.guild.get_member(int(uid)) or self.bot.get_user(int(uid))
            name = user.display_name if user else f"User {uid}"
            lines.append(f"**{name}** — ✅ {s.get('approved', 0)} / 📝 {s.get('submitted', 0)}")
        await ctx.send("\n".join(lines))
