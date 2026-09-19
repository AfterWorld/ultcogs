"""Best-effort, independent owner/channel alerts with bounded deduplication."""

import asyncio
import hashlib
import logging
import time
import traceback
import uuid
from collections import OrderedDict
from pathlib import Path

import discord

from .store import PanelUnavailable

log = logging.getLogger("red.staffapplications")


def diagnostic(error):
    # Never include exception text, source lines, locals, tokens, or application answers.
    # File/function/line and exception class still locate the failing operation.
    frames = traceback.extract_tb(error.__traceback__)
    lines = [type(error).__name__]
    lines.extend(f"{Path(f.filename).name}:{f.lineno} in {f.name}" for f in frames[-12:])
    if isinstance(error, discord.HTTPException):
        lines.append(f"Discord HTTP status={error.status}, code={error.code}")
    if isinstance(error, PanelUnavailable):
        lines.append(PanelUnavailable.REASONS[error.reason])
        lines.append(
            "Automatic panel refresh paused until repair; run staffapp panel after fixing the configuration."
        )
    return "\n".join(lines)


class Alerts:
    def __init__(self, bot, store, clock=time.monotonic):
        self.bot, self.store, self.clock = bot, store, clock
        self.recent = OrderedDict()

    async def report(self, guild_id, operation, error, app_id=None, force=False):
        incident = uuid.uuid4().hex[:12]
        detail = diagnostic(error)
        log.error(
            "Incident %s guild=%s operation=%s application=%s\n%s",
            incident,
            guild_id,
            operation,
            app_id or "-",
            detail,
        )
        key = hashlib.sha256(f"{guild_id}:{operation}:{detail}".encode()).hexdigest()
        now = self.clock()
        previous = self.recent.get(key)
        if not force and previous is not None and now - previous < 300:
            return incident
        self.recent[key] = now
        self.recent.move_to_end(key)
        while len(self.recent) > 256:
            self.recent.popitem(last=False)
        message = (
            f"**Staff applications — incident `{incident}`**\n"
            f"Operation: `{operation}` · Server: `{guild_id or 'startup'}`\n"
            f"Application: `{app_id or 'none'}`\n"
            f"```text\n{detail[:1300]}\n```\n"
            "Repeated copies are suppressed for 5 minutes. No answers or exception payloads included."
        )

        async def owners():
            ids = set(getattr(self.bot, "owner_ids", None) or ())
            if getattr(self.bot, "owner_id", None):
                ids.add(self.bot.owner_id)
            if not ids:
                info = await self.bot.application_info()
                ids.add(info.owner.id)
            for owner_id in ids:
                try:
                    owner = self.bot.get_user(owner_id) or await self.bot.fetch_user(owner_id)
                    await owner.send(message, allowed_mentions=discord.AllowedMentions.none())
                except Exception as exc:
                    log.error("Owner alert failed: %s", type(exc).__name__)

        async def channel(target_guild):
            channel_id = self.store.settings(target_guild)["error_channel"]
            if channel_id:
                destination = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(
                    channel_id
                )
                if getattr(getattr(destination, "guild", None), "id", None) != target_guild:
                    return
                await destination.send(message, allowed_mentions=discord.AllowedMentions.none())

        async def channels():
            # Guild-independent worker failures go to every configured error destination.
            guilds = [guild_id] if guild_id else self.store.guilds()
            outcomes = await asyncio.gather(*(channel(g) for g in guilds), return_exceptions=True)
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    log.error("Channel alert failed: %s", type(outcome).__name__)

        # Neither route can prevent the other route; never recursively report alert failures.
        results = await asyncio.gather(
            asyncio.wait_for(owners(), timeout=20),
            asyncio.wait_for(channels(), timeout=20),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                log.error("Alert delivery failed: %s", type(result).__name__)
        return incident
