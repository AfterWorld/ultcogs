import discord
from datetime import datetime, timedelta

def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(description=msg, color=0xe74c3c)

def success_embed(msg: str) -> discord.Embed:
    return discord.Embed(description=msg, color=0x2ecc71)

def iso_now() -> str:
    return datetime.utcnow().isoformat()

def iso_to_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)

def cooldown_passed(last_time: str, per_day: int) -> bool:
    if per_day <= 0:
        return True
    try:
        last_dt = iso_to_dt(last_time)
    except Exception:
        return True
    return datetime.utcnow() - last_dt > timedelta(hours=24 / per_day)
