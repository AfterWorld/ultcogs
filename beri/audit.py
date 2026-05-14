"""
Audit log system for the Beri economy cog.
Every balance change is recorded with actor, reason, delta, and timestamp.
"""

import datetime
from typing import Union

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_number


class AuditLog:
    MAX_ENTRIES = 5000

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config

    async def log(self, *, guild, target, actor, delta, new_balance, reason):
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        actor_id = actor.id if isinstance(actor, discord.Member) else 0
        actor_name = actor.display_name if isinstance(actor, discord.Member) else str(actor)

        entry = {
            "ts": now.isoformat(),
            "guild_id": guild.id,
            "target_id": target.id,
            "target_name": target.display_name,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "delta": delta,
            "new_balance": new_balance,
            "reason": reason,
        }

        async with self.config.audit_log() as log:
            log.append(entry)
            if len(log) > self.MAX_ENTRIES:
                del log[: len(log) - self.MAX_ENTRIES]

        audit_ch_id = await self.config.guild(guild).audit_channel()
        if audit_ch_id:
            channel = guild.get_channel(audit_ch_id)
            if channel:
                await self._post_embed(channel, entry)

    async def _post_embed(self, channel, entry):
        icon = await self.config.guild(channel.guild).currency_icon()
        name = await self.config.guild(channel.guild).currency_name()
        sign = "+" if entry["delta"] >= 0 else ""
        color = discord.Color.green() if entry["delta"] >= 0 else discord.Color.red()

        embed = discord.Embed(
            title=f"{icon} {name} Transaction",
            color=color,
            timestamp=datetime.datetime.fromisoformat(entry["ts"]),
        )
        embed.add_field(name="User", value=f"<@{entry['target_id']}> ({entry['target_name']})", inline=True)
        embed.add_field(name="Actor", value=entry["actor_name"], inline=True)
        embed.add_field(name="Change", value=f"`{sign}{humanize_number(entry['delta'])}` {icon}", inline=True)
        embed.add_field(name="New Balance", value=f"{humanize_number(entry['new_balance'])} {icon}", inline=True)
        embed.add_field(name="Reason", value=f"`{entry['reason']}`", inline=True)
        embed.set_footer(text="Beri Audit Log")

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def get_entries(self, *, guild_id=None, user_id=None, limit=20):
        all_entries = await self.config.audit_log()
        results = all_entries
        if guild_id:
            results = [e for e in results if e.get("guild_id") == guild_id]
        if user_id:
            results = [e for e in results if e.get("target_id") == user_id]
        return results[-limit:]
