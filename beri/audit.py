"""
Audit log helper for the Beri cog.
Posts formatted embed to the configured audit channel whenever
the main cog calls AuditLog.log(). Does NOT store data itself —
storage lives in BeriCore's guild audit list.
"""

import datetime
from typing import Union

import discord
from redbot.core.utils.chat_formatting import humanize_number


class AuditLog:
    """Thin wrapper that formats and posts audit embeds to the audit channel."""

    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def log(
        self,
        *,
        guild: discord.Guild,
        target: discord.Member,
        actor: Union[discord.Member, str],
        delta: int,
        new_balance: int,
        reason: str,
    ):
        """Post a transaction to the guild's audit channel (if configured)."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        actor_name = actor.display_name if isinstance(actor, discord.Member) else str(actor)

        entry = {
            "ts": now.isoformat(),
            "target_id": target.id,
            "target_name": target.display_name,
            "actor_name": actor_name,
            "delta": delta,
            "new_balance": new_balance,
            "reason": reason,
        }

        audit_ch_id = await self.config.guild(guild).audit_channel()
        if audit_ch_id:
            channel = guild.get_channel(audit_ch_id)
            if channel:
                await self._post_embed(channel, entry)

    async def _post_embed(self, channel: discord.TextChannel, entry: dict):
        icon = await self.config.guild(channel.guild).currency_icon()
        name = await self.config.guild(channel.guild).currency_name()

        sign = "+" if entry["delta"] >= 0 else ""
        color = discord.Color.green() if entry["delta"] >= 0 else discord.Color.red()

        embed = discord.Embed(
            title=f"{icon} {name} Transaction",
            color=color,
            timestamp=datetime.datetime.fromisoformat(entry["ts"]),
        )
        embed.add_field(
            name="User",
            value=f"<@{entry['target_id']}> ({entry['target_name']})",
            inline=True,
        )
        embed.add_field(name="Actor", value=entry["actor_name"], inline=True)
        embed.add_field(
            name="Change",
            value=f"`{sign}{humanize_number(entry['delta'])}` {icon}",
            inline=True,
        )
        embed.add_field(
            name="New Balance",
            value=f"{humanize_number(entry['new_balance'])} {icon}",
            inline=True,
        )
        embed.add_field(name="Reason", value=f"`{entry['reason']}`", inline=True)
        embed.set_footer(text="Beri Audit Log")

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass
