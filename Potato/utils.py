import time
import discord
from datetime import datetime
from redbot.core import commands
from .constants import EMBED_PENDING, EMBED_APPROVED, EMBED_DENIED, EMBED_INFO

def now_ts() -> float:
    return time.time()

def vote_field(up: int, down: int) -> str:
    return f"👍 {up} | 👎 {down}"

def status_color(status: str) -> discord.Color:
    if status == "approved": return EMBED_APPROVED
    if status == "denied":   return EMBED_DENIED
    return EMBED_PENDING

def can_moderate(cog, member: discord.Member) -> bool:
    """Admin OR has any role ID in guild config `modrole_ids`."""
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    try:
        cfg = cog._cache.get(member.guild.id) or {}
    except Exception:
        cfg = {}
    want = set(int(x) for x in (cfg.get("modrole_ids") or []))
    return any(r.id in want for r in member.roles)

def decision_embed(
    sid: int,
    content: str,
    status: str,
    *,
    author: discord.Member = None,
    moderator: discord.Member = None,
    reason: str = None
) -> discord.Embed:
    emb = discord.Embed(
        title=f"Suggestion #{sid}",
        description=content,
        color=status_color(status),
        timestamp=datetime.utcnow()
    )
    if author:
        emb.set_author(name=str(author), icon_url=getattr(author.display_avatar, "url", discord.Embed.Empty))
    emb.add_field(name="Status", value=status.capitalize(), inline=True)
    if moderator:
        emb.add_field(name="Reviewed By", value=moderator.mention, inline=True)
    if reason:
        emb.add_field(name="Reason", value=reason, inline=False)
    return emb

async def log_action(cog, guild: discord.Guild, *, title: str, description: str, color: discord.Color = EMBED_INFO):
    try:
        cfg = await cog.get_guild_config(guild)
        ch_id = cfg.get("log_channel")
        if not ch_id:
            return
        ch = guild.get_channel(int(ch_id))
        if not ch:
            return
        emb = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
        await ch.send(embed=emb)
    except Exception:
        pass
