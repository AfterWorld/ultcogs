"""
weather.py — Grand Line Weather System for BeriCog.

A server-wide dynamic weather state that modifies all economy outputs.
Weather transitions automatically every few hours using a weighted
Markov chain. Announced to a configurable channel on each transition.

Mixin for BeriCog. Expects parent to expose:
    self.config
    self._currency_fmt(guild)
    self._safe_modify(ctx, guild, member, delta, *, reason, actor)
    self._modify_balance(guild, member, delta, *, reason, actor)
    self._get_balance(guild, member)
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

log = logging.getLogger("red.bericog.weather")

# ---------------------------------------------------------------------------
# Weather state definitions
# ---------------------------------------------------------------------------

WEATHER_STATES: dict[str, dict] = {
    "calm_seas": {
        "label": "🌊 Calm Seas",
        "short": "calm",
        "duration_range": (2, 4),
        "weight": 30,
        "colour": 0x3498DB,
        "modifiers": {
            "fishing_multiplier":       1.0,
            "work_multiplier":          1.0,
            "crime_success_delta":      0.0,
            "plunder_multiplier":       1.0,
            "rob_success_delta":        0.0,
            "duel_payout_multiplier":   1.0,
            "heat_decay_rate":          1.5,
            "heat_threshold_modifier":  0,
            "legendary_catch_weight":   0,
            "beri_drop_bonus":          0.0,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas":         40,
            "storm":             20,
            "marine_blockade":   15,
            "new_world_current": 10,
            "fog_of_war":        15,
        },
        "announce": {
            "start": [
                "The Grand Line has gone quiet. Seas are calm.",
                "Unusually peaceful waters today. Enjoy it while it lasts.",
                "The Den Den Mushi network reports clear skies across all seas.",
            ],
            "end": [
                "The calm is ending. Something is stirring on the horizon.",
            ],
        },
    },

    "storm": {
        "label": "⛈️ Grand Line Storm",
        "short": "storm",
        "duration_range": (1, 3),
        "weight": 20,
        "colour": 0x2C3E50,
        "modifiers": {
            "fishing_multiplier":       0.5,
            "work_multiplier":          0.75,
            "crime_success_delta":      0.15,
            "plunder_multiplier":       1.3,
            "rob_success_delta":        0.10,
            "duel_payout_multiplier":   1.5,
            "heat_decay_rate":          2.0,
            "heat_threshold_modifier":  -20,
            "legendary_catch_weight":   8,
            "beri_drop_bonus":          0.0,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas":       40,
            "marine_blockade": 20,
            "fog_of_war":      25,
            "storm":           15,
        },
        "announce": {
            "start": [
                (
                    "⛈️ **STORM WARNING** — A violent storm is forming across the Grand Line.\n"
                    "Marine patrols have pulled back. Criminal activity is spiking.\n"
                    "**Fishing yields halved. Crime and plunder success rates rising.**"
                ),
                "The sky has turned black. Whatever you were planning — now's the time.",
            ],
            "end": [
                "The storm is passing. Marine vessels are resuming patrol routes.",
                "Skies clearing. The Marines are already moving back in.",
            ],
        },
    },

    "marine_blockade": {
        "label": "⚓ Marine Blockade",
        "short": "blockade",
        "duration_range": (2, 4),
        "weight": 15,
        "colour": 0xF1C40F,
        "modifiers": {
            "fishing_multiplier":       1.0,
            "work_multiplier":          1.4,
            "crime_success_delta":      -0.25,
            "plunder_multiplier":       0.4,
            "rob_success_delta":        -0.20,
            "duel_payout_multiplier":   1.0,
            "heat_decay_rate":          0.3,
            "heat_threshold_modifier":  30,
            "legendary_catch_weight":   0,
            "beri_drop_bonus":          0.0,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas":  50,
            "storm":      20,
            "fog_of_war": 30,
        },
        "announce": {
            "start": [
                (
                    "⚓ **MARINE BROADCAST** — Fleet Admiral has ordered a full blockade.\n"
                    "All vessels subject to inspection. Legitimate workers compensated.\n"
                    "**Criminal success rates significantly reduced. Heat decay suspended.**"
                ),
                "The Marines have mobilized. Every port is being watched.",
            ],
            "end": [
                "The Marine blockade is lifting. Ships are free to move.",
                "Fleet Admiral's office has recalled the inspection units.",
            ],
        },
    },

    "new_world_current": {
        "label": "🌀 New World Current",
        "short": "current",
        "duration_range": (1, 2),
        "weight": 10,
        "colour": 0x9B59B6,
        "modifiers": {
            "fishing_multiplier":       2.5,
            "work_multiplier":          1.2,
            "crime_success_delta":      0.0,
            "plunder_multiplier":       1.0,
            "rob_success_delta":        0.0,
            "duel_payout_multiplier":   1.0,
            "heat_decay_rate":          1.0,
            "heat_threshold_modifier":  0,
            "legendary_catch_weight":   25,
            "beri_drop_bonus":          0.10,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas":       60,
            "storm":           30,
            "marine_blockade": 10,
        },
        "announce": {
            "start": [
                (
                    "🌀 **NEW WORLD CURRENT DETECTED** — Rare creatures are surfacing.\n"
                    "Fishing yields massively boosted. Legendary catches possible from any rod.\n"
                    "**This window won't last long.**"
                ),
            ],
            "end": [
                "The current has passed. The deep sea returns to silence.",
            ],
        },
    },

    "fog_of_war": {
        "label": "🌫️ Fog of War",
        "short": "fog",
        "duration_range": (1, 3),
        "weight": 15,
        "colour": 0x95A5A6,
        "modifiers": {
            "fishing_multiplier":       1.2,
            "work_multiplier":          0.9,
            "crime_success_delta":      0.10,
            "plunder_multiplier":       1.1,
            "rob_success_delta":        0.05,
            "duel_payout_multiplier":   1.0,
            "duel_outcome_randomness":  0.15,
            "heat_decay_rate":          1.2,
            "heat_threshold_modifier":  -10,
            "legendary_catch_weight":   0,
            "beri_drop_bonus":          0.0,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas":         45,
            "storm":             25,
            "marine_blockade":   15,
            "new_world_current": 15,
        },
        "announce": {
            "start": [
                (
                    "🌫️ A thick fog has settled over the Grand Line.\n"
                    "Navigation is difficult. Duel outcomes are less predictable.\n"
                    "**Criminals move easier unseen. Work yields slightly reduced.**"
                ),
            ],
            "end": [
                "The fog is clearing. Visibility returning to normal.",
            ],
        },
    },

    "red_line_eclipse": {
        "label": "🔴 Red Line Eclipse",
        "short": "eclipse",
        "duration_range": (1, 1),
        "weight": 3,
        "colour": 0xE74C3C,
        "modifiers": {
            "fishing_multiplier":       3.0,
            "work_multiplier":          2.0,
            "crime_success_delta":      0.20,
            "plunder_multiplier":       2.0,
            "rob_success_delta":        0.15,
            "duel_payout_multiplier":   2.0,
            "heat_decay_rate":          3.0,
            "heat_threshold_modifier":  -40,
            "legendary_catch_weight":   50,
            "beri_drop_bonus":          0.20,
            "all_multiplier":           2.0,
            "tribute_active":           False,
        },
        "transitions": {
            "calm_seas": 70,
            "storm":     30,
        },
        "announce": {
            "start": [
                (
                    "🔴 **RED LINE ECLIPSE — ONCE IN A GENERATION EVENT**\n\n"
                    "The sky has turned deep red. All activity yields are doubled.\n"
                    "Legendary catches are possible from any rod.\n"
                    "**This lasts one hour. Do not waste it.**"
                ),
            ],
            "end": [
                "The eclipse has ended. The sky returns to normal.",
                "The red fades. Whatever you did in that hour — it counted.",
            ],
        },
    },

    "yonko_territory": {
        "label": "👑 Yonko Territory",
        "short": "yonko",
        "duration_range": (2, 3),
        "weight": 7,
        "colour": 0xE67E22,
        "modifiers": {
            "fishing_multiplier":       1.0,
            "work_multiplier":          1.5,
            "crime_success_delta":      -0.10,
            "plunder_multiplier":       0.7,
            "rob_success_delta":        -0.05,
            "duel_payout_multiplier":   2.0,
            "heat_decay_rate":          0.7,
            "heat_threshold_modifier":  15,
            "legendary_catch_weight":   0,
            "beri_drop_bonus":          0.0,
            "tribute_active":           True,
            "tribute_rate":             0.02,
        },
        "transitions": {
            "calm_seas":       40,
            "storm":           25,
            "marine_blockade": 20,
            "fog_of_war":      15,
        },
        "announce": {
            "start": [
                (
                    "👑 **YONKO TERRITORY** — You've drifted into Emperor's waters.\n"
                    "Duels pay double. Work is rewarded generously.\n"
                    "**2% tribute is automatically collected from all Beri earned.**"
                ),
            ],
            "end": [
                "You've left Yonko territory. The Emperor's influence fades.",
            ],
        },
    },
}

# ---------------------------------------------------------------------------
# Modifier display map — used in embeds to show human-readable modifiers
# ---------------------------------------------------------------------------

MODIFIER_DISPLAY: dict[str, tuple[str, str]] = {
    "fishing_multiplier":       ("🎣 Fishing",   "x{:.1f}"),
    "work_multiplier":          ("👷 Work",      "x{:.1f}"),
    "crime_success_delta":      ("🦹 Crime",     "{:+.0%}"),
    "plunder_multiplier":       ("🏴‍☠️ Plunder",  "x{:.1f}"),
    "rob_success_delta":        ("🔫 Rob",       "{:+.0%}"),
    "duel_payout_multiplier":   ("⚔️ Duels",    "x{:.1f}"),
    "heat_decay_rate":          ("🌡️ Heat Decay","x{:.1f}"),
    "beri_drop_bonus":          ("💰 All Income","{:+.0%}"),
    "all_multiplier":           ("✨ Everything", "x{:.1f}"),
    "tribute_active":           ("👑 Tribute",   "2% collected"),
}

# ---------------------------------------------------------------------------
# Pure functions — no self needed
# ---------------------------------------------------------------------------

def _next_weather(current: str) -> str:
    """
    Pick next weather using the current state's transition weights.
    Uses a Markov chain so weather flows naturally rather than
    jumping randomly between unrelated states.
    """
    state = WEATHER_STATES.get(current)
    if state is None:
        return random.choices(
            list(WEATHER_STATES.keys()),
            weights=[s["weight"] for s in WEATHER_STATES.values()],
            k=1,
        )[0]

    transitions = state["transitions"]
    options = list(transitions.keys())
    weights = [transitions[o] for o in options]
    return random.choices(options, weights=weights, k=1)[0]


def _fmt_duration(seconds: int) -> str:
    """Format seconds into a human-readable duration string."""
    if seconds <= 0:
        return "expired"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _build_modifier_lines(modifiers: dict) -> list[str]:
    """Build human-readable modifier lines for embed display."""
    lines = []
    for key, (label, fmt) in MODIFIER_DISPLAY.items():
        val = modifiers.get(key)
        if val is None or val is False:
            continue
        if val is True:
            lines.append(f"{label}: **active**")
            continue
        if isinstance(val, float) and (val == 1.0 or val == 0.0):
            continue
        try:
            lines.append(f"{label}: **{fmt.format(val)}**")
        except (ValueError, KeyError):
            continue
    return lines


# ---------------------------------------------------------------------------
# Weather mixin
# ---------------------------------------------------------------------------

class Weather(commands.Cog):
    """
    Grand Line Weather System mixin for BeriCog.

    Add to BeriCog's inheritance chain:
        class BeriCog(Casino, Games, Work, Income, XKCD, Treasure, Fishing, Weather, commands.Cog):

    Register config in BeriCog.DEFAULT_GUILD:
        "weather": {
            "current_state":      "calm_seas",
            "started_at":         None,
            "expires_at":         None,
            "channel_id":         None,
            "last_state":         None,
            "yonko_treasury":     0,
            "crackdown_active":   False,
            "crackdown_expires":  None,
            "crackdown_threshold": 500,
        }

    Start/stop the background task in BeriCog.cog_load / cog_unload.
    """

    # -----------------------------------------------------------------------
    # Primary interface — called by every economy command
    # -----------------------------------------------------------------------

    async def get_weather_modifier(
        self,
        guild: discord.Guild,
        modifier_key: str,
        default: float = 1.0,
    ) -> float:
        """
        Primary interface for all economy commands.
        Returns the float modifier for a given key under current weather.

        Examples:
            multiplier = await self.get_weather_modifier(ctx.guild, "work_multiplier")
            amount = int(amount * multiplier)

            crime_delta = await self.get_weather_modifier(ctx.guild, "crime_success_delta", default=0.0)
            success_rate += crime_delta
        """
        weather_cfg = await self.config.guild(guild).weather()

        # Lazy expiry check — transition now if expired
        expires_at_str = weather_cfg.get("expires_at")
        if expires_at_str:
            expires_dt = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) >= expires_dt:
                await self._transition_weather(guild)
                weather_cfg = await self.config.guild(guild).weather()

        current = weather_cfg.get("current_state", "calm_seas")
        state = WEATHER_STATES.get(current, {})
        modifiers = state.get("modifiers", {})

        # Check all_multiplier — applies on top of specific modifier
        base = modifiers.get(modifier_key, default)
        all_mult = modifiers.get("all_multiplier", 1.0)

        # all_multiplier only applies to income-type multipliers, not deltas
        if modifier_key.endswith("_multiplier") and all_mult != 1.0:
            base = base * all_mult

        # Crackdown stacks onto crime/rob modifiers
        if modifier_key in ("crime_success_delta", "rob_success_delta"):
            crackdown = weather_cfg.get("crackdown_active", False)
            crackdown_expires_str = weather_cfg.get("crackdown_expires")
            if crackdown and crackdown_expires_str:
                if datetime.fromisoformat(crackdown_expires_str) > datetime.now(timezone.utc):
                    base = base - 0.30
                else:
                    # Crackdown expired — clean it up
                    async with self.config.guild(guild).weather() as w:
                        w["crackdown_active"] = False
                        w["crackdown_expires"] = None

        return base

    async def get_current_weather(self, guild: discord.Guild) -> dict:
        """
        Return the full current weather state including time remaining.
        Safe to call from any command — triggers lazy transition if needed.
        """
        weather_cfg = await self.config.guild(guild).weather()
        current = weather_cfg.get("current_state", "calm_seas")
        expires_at_str = weather_cfg.get("expires_at")

        remaining_seconds = 0
        if expires_at_str:
            delta = datetime.fromisoformat(expires_at_str) - datetime.now(timezone.utc)
            remaining_seconds = max(0, int(delta.total_seconds()))

        state = WEATHER_STATES.get(current, WEATHER_STATES["calm_seas"])
        return {
            **state,
            "current_state":    current,
            "remaining_seconds": remaining_seconds,
            "expires_at":       expires_at_str,
            "started_at":       weather_cfg.get("started_at"),
            "yonko_treasury":   weather_cfg.get("yonko_treasury", 0),
        }

    # -----------------------------------------------------------------------
    # Transition engine
    # -----------------------------------------------------------------------

    async def _transition_weather(
        self,
        guild: discord.Guild,
        force_state: Optional[str] = None,
    ) -> dict:
        """
        Transition to the next weather state.
        Called by the background task or lazily from get_weather_modifier.
        Returns the new state dict.
        """
        weather_cfg = await self.config.guild(guild).weather()
        current = weather_cfg.get("current_state", "calm_seas")

        # Announce end of current weather
        await self._announce_weather(guild, current, "end")

        new_state_key = force_state or _next_weather(current)
        new_state = WEATHER_STATES[new_state_key]

        duration_min, duration_max = new_state["duration_range"]
        duration_hours = random.uniform(duration_min, duration_max)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration_hours)

        async with self.config.guild(guild).weather() as w:
            w["last_state"]   = current
            w["current_state"] = new_state_key
            w["started_at"]   = now.isoformat()
            w["expires_at"]   = expires_at.isoformat()

        # Announce start of new weather
        await self._announce_weather(guild, new_state_key, "start", expires_at)

        log.info(
            "Weather transition guild=%s: %s -> %s (expires %s)",
            guild.id, current, new_state_key, expires_at.isoformat(),
        )

        return new_state

    # -----------------------------------------------------------------------
    # Announcement engine
    # -----------------------------------------------------------------------

    async def _announce_weather(
        self,
        guild: discord.Guild,
        state_key: str,
        phase: str,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Post weather announcement to the configured world state channel.
        phase: "start" or "end"
        """
        weather_cfg = await self.config.guild(guild).weather()
        channel_id = weather_cfg.get("channel_id")

        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        state = WEATHER_STATES.get(state_key)
        if not state:
            return

        messages = state["announce"].get(phase, [])
        if not messages:
            return

        description = random.choice(messages)
        colour = discord.Colour(state["colour"])

        embed = discord.Embed(
            title=state["label"],
            description=description,
            colour=colour,
            timestamp=datetime.now(timezone.utc),
        )

        if phase == "start":
            if expires_at:
                remaining = expires_at - datetime.now(timezone.utc)
                embed.add_field(
                    name="⏱️ Duration",
                    value=f"Approximately **{_fmt_duration(int(remaining.total_seconds()))}**",
                    inline=True,
                )

            modifier_lines = _build_modifier_lines(state.get("modifiers", {}))
            if modifier_lines:
                embed.add_field(
                    name="📊 Active Modifiers",
                    value="\n".join(modifier_lines),
                    inline=False,
                )

        embed.set_footer(text="Use [p]weather to check current conditions at any time.")

        with suppress(discord.HTTPException):
            await channel.send(embed=embed)

    # -----------------------------------------------------------------------
    # Aggregate heat check — triggers server-wide crackdown
    # -----------------------------------------------------------------------

    async def _check_aggregate_heat(self, guild: discord.Guild) -> None:
        """
        Check total server heat. If over threshold, trigger a crackdown.
        Called from the weather loop every cycle.
        """
        weather_cfg = await self.config.guild(guild).weather()

        # Don't stack crackdowns
        if weather_cfg.get("crackdown_active"):
            return

        threshold = weather_cfg.get("crackdown_threshold", 500)

        try:
            all_members = await self.config.all_members(guild)
        except Exception:
            return

        total_heat = sum(
            data.get("heat", {}).get("heat_level", 0)
            for data in all_members.values()
        )

        if total_heat < threshold:
            return

        now = datetime.now(timezone.utc)
        crackdown_expires = now + timedelta(hours=2)

        async with self.config.guild(guild).weather() as w:
            w["crackdown_active"]  = True
            w["crackdown_expires"] = crackdown_expires.isoformat()

        channel_id = weather_cfg.get("channel_id")
        if not channel_id:
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="🔴 CRACKDOWN — Criminal Activity Has Drawn Attention",
            description=(
                f"Aggregate criminal heat on this server has reached **{total_heat}**.\n"
                f"A fleet-wide crackdown has been triggered.\n\n"
                f"**All crime, rob, and hack success rates reduced by 30%**\n"
                f"**for the next 2 hours.**\n\n"
                f"Someone — or several people — pushed it too far."
            ),
            colour=discord.Colour.dark_red(),
            timestamp=now,
        )
        embed.add_field(
            name="Expires",
            value=f"<t:{int(crackdown_expires.timestamp())}:R>",
            inline=True,
        )
        embed.set_footer(text="Lay low. Or don't. Your choice.")

        with suppress(discord.HTTPException):
            await channel.send(embed=embed)

    # -----------------------------------------------------------------------
    # Yonko tribute collection
    # -----------------------------------------------------------------------

    async def collect_yonko_tribute(
        self,
        guild: discord.Guild,
        member: discord.Member,
        amount_earned: int,
    ) -> int:
        """
        If Yonko Territory is active, deduct tribute from earnings.
        Returns the tribute amount taken (0 if not active).
        Call this AFTER calculating final payout, BEFORE crediting member.

        Usage in work.py:
            tribute = await self.collect_yonko_tribute(ctx.guild, ctx.author, amount)
            amount -= tribute
        """
        tribute_active = await self.get_weather_modifier(
            guild, "tribute_active", default=False
        )
        if not tribute_active:
            return 0

        weather_cfg = await self.config.guild(guild).weather()
        state = WEATHER_STATES.get(weather_cfg.get("current_state", "calm_seas"), {})
        rate = state.get("modifiers", {}).get("tribute_rate", 0.02)

        tribute = max(1, int(amount_earned * rate))

        async with self.config.guild(guild).weather() as w:
            w["yonko_treasury"] = w.get("yonko_treasury", 0) + tribute

        return tribute

    # -----------------------------------------------------------------------
    # Background task
    # -----------------------------------------------------------------------

    @tasks.loop(minutes=10)
    async def _weather_loop(self) -> None:
        """
        Every 10 minutes check all guilds for expired weather.
        Also checks aggregate heat for crackdown trigger.
        The lazy check in get_weather_modifier is the primary mechanism —
        this loop is the safety net for inactive servers.
        """
        now = datetime.now(timezone.utc)
        for guild in self.bot.guilds:
            try:
                weather_cfg = await self.config.guild(guild).weather()

                # Initialize weather if never set
                if weather_cfg.get("expires_at") is None:
                    await self._transition_weather(guild, force_state="calm_seas")
                    continue

                expires_at = datetime.fromisoformat(weather_cfg["expires_at"])
                if now >= expires_at:
                    await self._transition_weather(guild)

                # Check aggregate heat for crackdown
                await self._check_aggregate_heat(guild)

            except Exception as exc:
                log.error(
                    "Weather loop error for guild %s",
                    guild.id,
                    exc_info=exc,
                )

    @_weather_loop.before_loop
    async def _before_weather_loop(self) -> None:
        await self.bot.wait_until_ready()

    # -----------------------------------------------------------------------
    # Player commands
    # -----------------------------------------------------------------------

    @commands.command(name="weather", aliases=["forecast", "seas", "conditions"])
    @commands.guild_only()
    async def weather_check(self, ctx: commands.Context) -> None:
        """Check current Grand Line weather conditions and active modifiers."""
        current = await self.get_current_weather(ctx.guild)
        weather_cfg = await self.config.guild(ctx.guild).weather()

        embed = discord.Embed(
            title=f"🌍 Grand Line Conditions — {current['label']}",
            colour=discord.Colour(current["colour"]),
            timestamp=datetime.now(timezone.utc),
        )

        remaining = current["remaining_seconds"]
        embed.add_field(
            name="⏱️ Time Remaining",
            value=f"**{_fmt_duration(remaining)}**",
            inline=True,
        )

        last_state = weather_cfg.get("last_state")
        if last_state and last_state in WEATHER_STATES:
            embed.add_field(
                name="📜 Previous",
                value=WEATHER_STATES[last_state]["label"],
                inline=True,
            )

        modifier_lines = _build_modifier_lines(current.get("modifiers", {}))
        if modifier_lines:
            embed.add_field(
                name="📊 Active Modifiers",
                value="\n".join(modifier_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="📊 Active Modifiers",
                value="All activity rates are normal.",
                inline=False,
            )

        # Show crackdown if active
        crackdown = weather_cfg.get("crackdown_active", False)
        crackdown_expires_str = weather_cfg.get("crackdown_expires")
        if crackdown and crackdown_expires_str:
            crackdown_expires = datetime.fromisoformat(crackdown_expires_str)
            if crackdown_expires > datetime.now(timezone.utc):
                embed.add_field(
                    name="🔴 CRACKDOWN ACTIVE",
                    value=(
                        f"Crime/rob/hack success −30%\n"
                        f"Expires: <t:{int(crackdown_expires.timestamp())}:R>"
                    ),
                    inline=False,
                )

        # Show Yonko treasury if in Yonko territory
        if current.get("modifiers", {}).get("tribute_active"):
            treasury = current.get("yonko_treasury", 0)
            name, icon = await self._currency_fmt(ctx.guild)
            embed.add_field(
                name="👑 Yonko Treasury",
                value=f"**{humanize_number(treasury)}** {icon} collected",
                inline=True,
            )

        embed.set_footer(text="Weather changes automatically every few hours.")
        await ctx.send(embed=embed)

    @commands.command(name="worldstate", aliases=["ws", "globalstate"])
    @commands.guild_only()
    async def world_state(self, ctx: commands.Context) -> None:
        """
        Full world state overview — weather, crackdown status,
        and aggregate server heat level.
        """
        weather_cfg = await self.config.guild(ctx.guild).weather()
        current = await self.get_current_weather(ctx.guild)
        name, icon = await self._currency_fmt(ctx.guild)

        embed = discord.Embed(
            title="🌍 Grand Line World State",
            colour=discord.Colour(current["colour"]),
            timestamp=datetime.now(timezone.utc),
        )

        # Weather block
        remaining = current["remaining_seconds"]
        embed.add_field(
            name="🌊 Current Weather",
            value=(
                f"**{current['label']}**\n"
                f"Expires in: {_fmt_duration(remaining)}"
            ),
            inline=False,
        )

        # Aggregate heat
        try:
            all_members = await self.config.all_members(ctx.guild)
            total_heat = sum(
                data.get("heat", {}).get("heat_level", 0)
                for data in all_members.values()
            )
        except Exception:
            total_heat = 0

        threshold = weather_cfg.get("crackdown_threshold", 500)
        heat_pct = min(1.0, total_heat / threshold)
        bar_filled = int(heat_pct * 20)
        bar_empty = 20 - bar_filled
        heat_bar = f"{'█' * bar_filled}{'░' * bar_empty}"

        embed.add_field(
            name="🌡️ Server Heat Level",
            value=(
                f"`{heat_bar}` {int(heat_pct * 100)}%\n"
                f"**{total_heat}** / {threshold} (crackdown threshold)"
            ),
            inline=False,
        )

        # Crackdown status
        crackdown = weather_cfg.get("crackdown_active", False)
        crackdown_expires_str = weather_cfg.get("crackdown_expires")
        if crackdown and crackdown_expires_str:
            crackdown_dt = datetime.fromisoformat(crackdown_expires_str)
            if crackdown_dt > datetime.now(timezone.utc):
                embed.add_field(
                    name="🔴 Crackdown",
                    value=f"ACTIVE — expires <t:{int(crackdown_dt.timestamp())}:R>",
                    inline=True,
                )
        else:
            embed.add_field(
                name="🔴 Crackdown",
                value="Inactive",
                inline=True,
            )

        # Yonko treasury
        if current.get("modifiers", {}).get("tribute_active"):
            treasury = current.get("yonko_treasury", 0)
            embed.add_field(
                name="👑 Yonko Treasury",
                value=f"**{humanize_number(treasury)}** {icon}",
                inline=True,
            )

        embed.set_footer(text="[p]weather for detailed modifier breakdown.")
        await ctx.send(embed=embed)

    # -----------------------------------------------------------------------
    # Admin commands
    # -----------------------------------------------------------------------

    @commands.group(name="weatherset")
    @commands.admin_or_permissions(administrator=True)
    @commands.guild_only()
    async def weatherset(self, ctx: commands.Context) -> None:
        """Configure the Grand Line weather system."""

    @weatherset.command(name="channel")
    async def weatherset_channel(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel] = None,
    ) -> None:
        """Set the channel for weather and world state announcements."""
        async with self.config.guild(ctx.guild).weather() as w:
            w["channel_id"] = channel.id if channel else None
        if channel:
            await ctx.send(f"✅ Weather announcements will post in {channel.mention}.")
        else:
            await ctx.send("✅ Weather announcement channel cleared.")

    @weatherset.command(name="force")
    async def weatherset_force(
        self,
        ctx: commands.Context,
        state: str,
    ) -> None:
        """Force a specific weather state immediately."""
        if state not in WEATHER_STATES:
            valid = ", ".join(f"`{k}`" for k in WEATHER_STATES)
            return await ctx.send(f"❌ Unknown state. Valid options: {valid}")
        await self._transition_weather(ctx.guild, force_state=state)
        await ctx.send(
            f"✅ Weather forced to **{WEATHER_STATES[state]['label']}**."
        )

    @weatherset.command(name="crackdownthreshold")
    async def weatherset_crackdown_threshold(
        self,
        ctx: commands.Context,
        threshold: int,
    ) -> None:
        """Set the aggregate heat threshold that triggers a server crackdown."""
        if threshold < 50:
            return await ctx.send("❌ Threshold must be at least 50.")
        async with self.config.guild(ctx.guild).weather() as w:
            w["crackdown_threshold"] = threshold
        await ctx.send(
            f"✅ Crackdown threshold set to **{threshold}** aggregate heat."
        )

    @weatherset.command(name="clearcrackdown")
    async def weatherset_clear_crackdown(self, ctx: commands.Context) -> None:
        """Manually clear an active crackdown."""
        async with self.config.guild(ctx.guild).weather() as w:
            w["crackdown_active"]  = False
            w["crackdown_expires"] = None
        await ctx.send("✅ Crackdown cleared.")

    @weatherset.command(name="list")
    async def weatherset_list(self, ctx: commands.Context) -> None:
        """List all possible weather states with durations and weights."""
        lines = []
        for key, state in WEATHER_STATES.items():
            dur_min, dur_max = state["duration_range"]
            lines.append(
                f"**{state['label']}** — `{key}`\n"
                f"  Weight: {state['weight']} | "
                f"Duration: {dur_min}–{dur_max}h"
            )
        embed = discord.Embed(
            title="🌍 Available Weather States",
            description="\n\n".join(lines),
            colour=discord.Colour.blurple(),
        )
        await ctx.send(embed=embed)

    @weatherset.command(name="info")
    async def weatherset_info(self, ctx: commands.Context) -> None:
        """Show current weather configuration for this server."""
        weather_cfg = await self.config.guild(ctx.guild).weather()
        channel_id = weather_cfg.get("channel_id")
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        threshold = weather_cfg.get("crackdown_threshold", 500)

        embed = discord.Embed(
            title="⚙️ Weather System Config",
            colour=discord.Colour.blurple(),
        )
        embed.add_field(
            name="Announcement Channel",
            value=channel.mention if channel else "Not set",
            inline=True,
        )
        embed.add_field(
            name="Crackdown Threshold",
            value=str(threshold),
            inline=True,
        )
        embed.add_field(
            name="Current State",
            value=weather_cfg.get("current_state", "calm_seas"),
            inline=True,
        )
        await ctx.send(embed=embed)
