"""Voyage foundation cog for Red-DiscordBot."""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import discord
from discord.ext import tasks
from redbot.core import Config, checks, commands

from .data import load_json
from .database import CharacterExistsError, VoyageDatabase
from .factions import (
    FACTIONS,
    build_starting_stats,
    format_modifiers,
    format_stats,
    get_faction,
    stat_weights_for_faction,
)

log = logging.getLogger("red.voyage")
COG_DIR = Path(__file__).resolve().parent
DATA_DIR = COG_DIR / "data"
DB_PATH = DATA_DIR / "voyage.sqlite3"
CONFIG_IDENTIFIER = 948_271_603_514
VOYAGE_GOLD = discord.Colour(0xD4AF37)
VOYAGE_RED = discord.Colour(0xB23A48)
VOYAGE_BLUE = discord.Colour(0x2F80ED)
VOYAGE_GREEN = discord.Colour(0x2E8B57)
ACTION_TRAIN = "train"
ACTION_SAIL = "sail"
ACTION_CONTRACT_TARGET = "contract_target"
DEFAULT_CONTRACT_MINIMUM_BERI = 5_000
DEFAULT_CONTRACT_MID_TIER_MIN = 25_000
DEFAULT_CONTRACT_LARGE_TIER_MIN = 100_000
CONTRACT_BIG_WIN_PENALTY_PERCENT = {"Small": 5, "Mid": 10, "Large": 15}
CONTRACT_SMALL_WIN_PENALTY_PERCENT = {"Small": 2, "Mid": 5, "Large": 8}


class FactionSelect(discord.ui.Select):
    """Faction selection menu for character creation."""

    def __init__(self, cog: Voyage, guild_id: int, user_id: int):
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=faction.label,
                value=faction.key,
                emoji=faction.emoji,
                description=f"{format_modifiers(faction)} — {faction.rank_tier}",
            )
            for faction in FACTIONS.values()
        ]
        super().__init__(
            placeholder="Choose your banner on the Grand Line...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        faction_key = self.values[0]
        faction = get_faction(faction_key)
        stats = build_starting_stats(faction_key)

        try:
            character = await self.cog.db.create_character(
                guild_id=self.guild_id,
                user_id=self.user_id,
                faction=faction.key,
                rank_tier=faction.rank_tier,
                stats=stats,
            )
        except CharacterExistsError:
            embed = discord.Embed(
                title="Log Pose Already Set",
                description="You already have a Voyage character in this sea.",
                colour=VOYAGE_RED,
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        embed = self.cog.build_character_embed(
            user=interaction.user,
            character=character,
            title="Wanted Poster Inked",
            description=(
                f"{faction.display_name} colors rise over the mast. "
                "Your first voyage is now recorded."
            ),
        )
        await interaction.response.edit_message(embed=embed, view=None)


class FactionSelectView(discord.ui.View):
    """Owner-locked view for choosing a Voyage faction."""

    def __init__(self, cog: Voyage, guild_id: int, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(FactionSelect(cog, guild_id, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message(
            "This Log Pose is tuned to another sailor.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True


class SailRiskSelect(discord.ui.Select):
    """Risk selection menu for the sail command."""

    def __init__(self, cog: Voyage, guild_id: int, user_id: int):
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label="Safe Waters",
                value="safe",
                emoji="🧭",
                description="Shorter route, modest upside, almost no drama.",
            ),
            discord.SelectOption(
                label="Risky Waters",
                value="risky",
                emoji="🌊",
                description="Longer route, bigger loot, real chance of a loss.",
            ),
        ]
        super().__init__(
            placeholder="Pick a route before the tide turns...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.cog.start_voyage_from_interaction(
            interaction=interaction,
            guild_id=self.guild_id,
            user_id=self.user_id,
            risk_tier=self.values[0],
        )


class SailRiskView(discord.ui.View):
    """Owner-locked view for selecting a sail risk tier."""

    def __init__(self, cog: Voyage, guild_id: int, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(SailRiskSelect(cog, guild_id, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.user_id:
            return True
        await interaction.response.send_message(
            "That ship is waiting on a different captain.",
            ephemeral=True,
        )
        return False

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True


class Voyage(commands.Cog):
    """One Piece-inspired character foundation for Voyage."""

    __author__ = "Roger"
    __version__ = "0.1.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=CONFIG_IDENTIFIER, force_registration=True)
        self.config.register_guild(
            event_channel_id=None,
            train_cooldown_seconds=3 * 60 * 60,
            sail_safe_duration_seconds=5 * 60,
            sail_risky_duration_seconds=10 * 60,
            contract_minimum_beri=DEFAULT_CONTRACT_MINIMUM_BERI,
            contract_mid_tier_min=DEFAULT_CONTRACT_MID_TIER_MIN,
            contract_large_tier_min=DEFAULT_CONTRACT_LARGE_TIER_MIN,
            contract_fee_percent=5,
            contract_expiry_seconds=24 * 60 * 60,
            contract_retarget_cooldown_seconds=24 * 60 * 60,
        )
        self.db = VoyageDatabase(DB_PATH)
        self.train_flavor: dict[str, list[str]] = load_json("train_flavor.json")
        self.sail_events: dict[str, list[dict[str, Any]]] = load_json("sail_events.json")

    async def cog_load(self) -> None:
        await self.db.connect()
        self.warn_if_bericore_missing()
        if not self.voyage_resolution_loop.is_running():
            self.voyage_resolution_loop.start()

    async def cog_unload(self) -> None:
        self.voyage_resolution_loop.cancel()
        await self.db.close()

    @staticmethod
    def format_remaining(expires_at: datetime) -> str:
        remaining = expires_at - datetime.now(UTC)
        seconds = max(0, int(remaining.total_seconds()))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @staticmethod
    def roll_weighted_event(events: list[dict[str, Any]]) -> dict[str, Any]:
        weights = [max(0, int(event.get("weight", 0))) for event in events]
        return random.choices(events, weights=weights, k=1)[0]

    @staticmethod
    def roll_berry_delta(event: dict[str, Any]) -> int:
        minimum = int(event.get("berry_min", 0))
        maximum = int(event.get("berry_max", minimum))
        return random.randint(minimum, maximum)

    def choose_training_stat(self, faction_key: str) -> str:
        weighted = stat_weights_for_faction(faction_key)
        stats = [stat for stat, _weight in weighted]
        weights = [weight for _stat, weight in weighted]
        return random.choices(stats, weights=weights, k=1)[0]

    def get_bericore(self):
        return self.bot.get_cog("BeriCore")

    def warn_if_bericore_missing(self) -> None:
        if self.get_bericore() is None:
            log.warning(
                "Voyage loaded without BeriCore. Economy-backed commands and schedulers "
                "will pause or fail gracefully until BeriCore is loaded."
            )

    async def apply_beri_delta(
        self,
        *,
        member: discord.Member,
        delta: int,
        reason: str,
        action_type: str,
        source: str,
        related_voyage_id: int | None = None,
        related_contract_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[int, int | None]:
        """Apply Beri through BeriCore and log the Voyage-side request."""
        core = self.get_bericore()
        if core is None:
            await self.db.log_transaction(
                guild_id=member.guild.id,
                user_id=member.id,
                source=source,
                action_type=action_type,
                delta_requested=delta,
                delta_applied=0,
                reason=reason,
                balance_after=None,
                related_voyage_id=related_voyage_id,
                related_contract_id=related_contract_id,
                status="failed_bericore_missing",
                metadata=metadata,
            )
            return 0, None

        actual_delta = delta
        if delta < 0:
            current_balance = await core.get_beri(member)
            actual_delta = max(-current_balance, delta)

        if actual_delta:
            balance_after = await core.add_beri(
                member,
                actual_delta,
                reason=reason,
                actor="Voyage",
                metadata=metadata,
            )
        else:
            balance_after = await core.get_beri(member)

        await self.db.log_transaction(
            guild_id=member.guild.id,
            user_id=member.id,
            source=source,
            action_type=action_type,
            delta_requested=delta,
            delta_applied=actual_delta,
            reason=reason,
            balance_after=balance_after,
            related_voyage_id=related_voyage_id,
            related_contract_id=related_contract_id,
            status="applied",
            metadata=metadata,
        )
        return actual_delta, balance_after

    async def require_bericore(self, ctx: commands.Context):
        core = self.get_bericore()
        if core is None:
            await ctx.send(
                "Voyage's economy integration (BeriCore) isn't currently available — "
                "please contact a server admin."
            )
            return None
        return core

    @staticmethod
    def contract_tier_from_thresholds(
        total_pooled: int,
        mid_tier_min: int,
        large_tier_min: int,
    ) -> str:
        if total_pooled >= large_tier_min:
            return "Large"
        if total_pooled >= mid_tier_min:
            return "Mid"
        return "Small"

    async def contract_tier(self, guild: discord.Guild, total_pooled: int) -> str:
        guild_config = self.config.guild(guild)
        mid_tier_min = await guild_config.contract_mid_tier_min()
        large_tier_min = await guild_config.contract_large_tier_min()
        return self.contract_tier_from_thresholds(total_pooled, mid_tier_min, large_tier_min)

    @staticmethod
    def danger_tier(character: dict[str, Any]) -> tuple[str, int]:
        score = (
            character["str"]
            + character["spd"]
            + character["def"]
            + character["will"]
            + max(character["bounty"], character["commendation"], character["infamy"]) // 1_000
        )
        if score >= 65:
            return "Large", 3
        if score >= 50:
            return "Mid", 2
        return "Small", 1

    @staticmethod
    def contract_roll_power(character: dict[str, Any]) -> int:
        faction = get_faction(character["faction"])
        stat_total = character["str"] + character["spd"] + character["def"] + character["will"]
        faction_edge = sum(max(0, value) for value in faction.modifiers.values())
        return stat_total + faction_edge + random.randint(1, 20)

    @staticmethod
    def can_target_contract(actor: dict[str, Any], target: dict[str, Any]) -> tuple[bool, str]:
        actor_faction = actor["faction"]
        target_faction = target["faction"]
        if actor_faction == "marine" and target_faction == "pirate":
            return True, ""
        if actor_faction == "pirate" and target_faction == "pirate":
            return True, ""
        if target_faction == "revolutionary":
            return False, "Revolutionaries require an investigation mechanic that is not in v1."
        return False, "Your faction cannot post or claim that contract in v1."

    def build_contract_embed(
        self,
        *,
        contract: dict[str, Any],
        target: discord.Member,
        tier: str,
        contributor: discord.Member | None = None,
    ) -> discord.Embed:
        expires = int(datetime.fromisoformat(contract["expires_at"]).timestamp())
        embed = discord.Embed(
            title=f"📜 {tier} Contract Posted",
            description=f"A contract is open on {target.mention}.",
            colour=VOYAGE_GOLD,
        )
        embed.add_field(name="Pool", value=f"{contract['total_pooled']:,} Beri", inline=True)
        embed.add_field(
            name="Posting Fees Burned",
            value=f"{contract['posting_fee_collected']:,} Beri",
            inline=True,
        )
        embed.add_field(name="Expires", value=f"<t:{expires}:R>", inline=True)
        if contributor is not None:
            embed.set_footer(text=f"Latest contribution by {contributor.display_name}")
        else:
            embed.set_footer(text=f"Contract #{contract['id']}")
        return embed

    def build_contract_result_embed(
        self,
        *,
        contract: dict[str, Any],
        target: discord.Member,
        claimer: discord.Member,
        outcome: str,
        payout: int,
        rank_field: str,
        rank_delta: int,
        target_penalty: int,
        target_balance_after: int | None,
    ) -> discord.Embed:
        colour = VOYAGE_GREEN if payout > 0 else VOYAGE_RED
        embed = discord.Embed(
            title=f"⚔️ Contract Resolved — {outcome.replace('_', ' ').title()}",
            description=f"{claimer.mention} challenged the contract on {target.mention}.",
            colour=colour,
        )
        embed.add_field(name="Payout", value=f"{payout:,} Beri", inline=True)
        embed.add_field(name="Rank Currency", value=f"+{rank_delta} {rank_field}", inline=True)
        if target_penalty:
            penalty_text = f"{target_penalty:,} Beri lost"
            if target_balance_after is not None:
                penalty_text += f"\nTarget balance: {target_balance_after:,} Beri"
        else:
            penalty_text = "No target-side Beri loss"
        embed.add_field(name="Target Penalty", value=penalty_text, inline=True)
        embed.add_field(
            name="Pool Source",
            value="Rank reward scales from target danger, not pool size.",
            inline=False,
        )
        embed.set_footer(text=f"Contract #{contract['id']}")
        return embed

    def build_character_embed(
        self,
        *,
        user: discord.abc.User,
        character: dict,
        title: str | None = None,
        description: str | None = None,
    ) -> discord.Embed:
        faction = get_faction(character["faction"])
        stats = {
            "str": character["str"],
            "spd": character["spd"],
            "def": character["def"],
            "will": character["will"],
        }
        embed = discord.Embed(
            title=title or f"{user.display_name}'s Voyage Dossier",
            description=description or faction.description,
            colour=VOYAGE_GOLD,
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.add_field(name="Banner", value=faction.display_name, inline=True)
        embed.add_field(name="Rank Tier", value=character["rank_tier"], inline=True)
        embed.add_field(name="Stat Line", value=format_stats(stats), inline=False)
        embed.add_field(name="Bounty", value=f"{character['bounty']:,}", inline=True)
        embed.add_field(name="Commendation", value=f"{character['commendation']:,}", inline=True)
        embed.add_field(name="Infamy", value=f"{character['infamy']:,}", inline=True)
        embed.set_footer(text="Voyage Foundation • Berry balances remain in BeriCore")
        return embed

    def build_voyage_result_embed(
        self,
        *,
        member: discord.Member,
        voyage: dict[str, Any],
        event: dict[str, Any],
        requested_delta: int,
        actual_delta: int,
        balance_after: int | None,
    ) -> discord.Embed:
        if actual_delta > 0:
            colour = VOYAGE_GREEN
            berry_line = f"+{actual_delta:,} Beri"
        elif actual_delta < 0:
            colour = VOYAGE_RED
            berry_line = f"{actual_delta:,} Beri"
        else:
            colour = discord.Colour.dark_grey()
            berry_line = "No Beri moved"

        if requested_delta != actual_delta:
            berry_line += f" (capped from {requested_delta:,})"
        if balance_after is not None:
            berry_line += f"\nBalance: {balance_after:,} Beri"
        else:
            berry_line += "\nBeriCore unavailable; no balance change applied."

        embed = discord.Embed(
            title=f"🧭 Voyage Complete — {event['title']}",
            description=event["description"],
            colour=colour,
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(name="Route", value=voyage["risk_tier"].title(), inline=True)
        embed.add_field(name="Outcome", value=berry_line, inline=True)
        embed.set_footer(text=f"Voyage #{voyage['id']} • {member.guild.name}")
        return embed

    @commands.hybrid_group(name="character", invoke_without_command=True)
    @commands.guild_only()
    async def character_group(self, ctx: commands.Context) -> None:
        """Create and view Voyage characters."""
        prefix = ctx.clean_prefix
        await ctx.send(f"Use `{prefix}character create` or `{prefix}character profile`.")

    @character_group.command(name="create")
    @commands.guild_only()
    async def character_create(self, ctx: commands.Context) -> None:
        """Create your Voyage character."""
        existing = await self.db.get_character(ctx.guild.id, ctx.author.id)
        if existing is not None:
            embed = self.build_character_embed(
                user=ctx.author,
                character=existing,
                title="Log Pose Already Set",
                description="You already have a character in this sea.",
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Choose Your Banner",
            description=(
                "The den-den mushi crackles. A new name is ready for the sea.\n\n"
                "Pick a faction to set your opening stat line and starting rank."
            ),
            colour=VOYAGE_GOLD,
        )
        for faction in FACTIONS.values():
            embed.add_field(
                name=faction.display_name,
                value=f"{faction.description}\n**Opening edge:** {format_modifiers(faction)}",
                inline=False,
            )
        embed.set_footer(text="This choice is permanent unless staff reset your character.")
        view = FactionSelectView(self, ctx.guild.id, ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @character_group.command(name="profile")
    @commands.guild_only()
    async def character_profile(
        self,
        ctx: commands.Context,
        member: discord.Member | None = None,
    ) -> None:
        """Show a Voyage character profile."""
        target = member or ctx.author
        character = await self.db.get_character(ctx.guild.id, target.id)
        if character is None:
            if target.id == ctx.author.id:
                await ctx.send("No Voyage dossier found. Use `/character create` to begin.")
            else:
                await ctx.send(f"No Voyage dossier found for {target.display_name}.")
            return

        await ctx.send(embed=self.build_character_embed(user=target, character=character))

    @commands.hybrid_command(name="train")
    @commands.guild_only()
    async def train(self, ctx: commands.Context) -> None:
        """Train your Voyage character for a small stat gain."""
        if await self.require_bericore(ctx) is None:
            return
        character = await self.db.get_character(ctx.guild.id, ctx.author.id)
        if character is None:
            await ctx.send("No Voyage dossier found. Use `/character create` before training.")
            return

        cooldown = await self.db.get_cooldown(ctx.guild.id, ctx.author.id, ACTION_TRAIN)
        if cooldown and cooldown > datetime.now(UTC):
            await ctx.send(
                "Your training drill is cooling down. "
                f"Try again in {self.format_remaining(cooldown)}."
            )
            return

        stat = self.choose_training_stat(character["faction"])
        updated = await self.db.add_stat(ctx.guild.id, ctx.author.id, stat, 1)
        cooldown_seconds = await self.config.guild(ctx.guild).train_cooldown_seconds()
        await self.db.set_cooldown(
            ctx.guild.id,
            ctx.author.id,
            ACTION_TRAIN,
            datetime.now(UTC) + timedelta(seconds=cooldown_seconds),
        )
        flavor = random.choice(
            self.train_flavor.get(stat, ["You train until the deck feels smaller."])
        )
        stats = {
            "str": updated["str"],
            "spd": updated["spd"],
            "def": updated["def"],
            "will": updated["will"],
        }
        embed = discord.Embed(
            title="🏋️ Deck Training Complete",
            description=flavor,
            colour=VOYAGE_GOLD,
        )
        embed.add_field(name="Gain", value=f"+1 {stat.upper()}", inline=True)
        embed.add_field(name="Current Stat Line", value=format_stats(stats), inline=False)
        next_train = await self.db.get_cooldown(ctx.guild.id, ctx.author.id, ACTION_TRAIN)
        embed.set_footer(text=f"Next drill available in {self.format_remaining(next_train)}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="sail")
    @commands.guild_only()
    async def sail(self, ctx: commands.Context) -> None:
        """Set sail on a timed Voyage route."""
        if await self.require_bericore(ctx) is None:
            return
        character = await self.db.get_character(ctx.guild.id, ctx.author.id)
        if character is None:
            await ctx.send("No Voyage dossier found. Use `/character create` before sailing.")
            return

        cooldown = await self.db.get_cooldown(ctx.guild.id, ctx.author.id, ACTION_SAIL)
        if cooldown and cooldown > datetime.now(UTC):
            remaining = self.format_remaining(cooldown)
            await ctx.send(
                f"Your ship is already at sea. Return expected in {remaining}."
            )
            return

        open_voyage = await self.db.get_open_voyage(ctx.guild.id, ctx.author.id)
        if open_voyage is not None:
            started = datetime.fromisoformat(open_voyage["started_at"])
            expires = started + timedelta(seconds=open_voyage["duration_seconds"])
            remaining = self.format_remaining(expires)
            await ctx.send(f"Your ship is already at sea. Return expected in {remaining}.")
            return

        embed = discord.Embed(
            title="Set Sail",
            description=(
                "The tide is turning. Choose a route and your crew will report back "
                "when the voyage resolves."
            ),
            colour=VOYAGE_BLUE,
        )
        embed.add_field(name="🧭 Safe Waters", value="Short voyage, modest rewards.", inline=False)
        embed.add_field(name="🌊 Risky Waters", value="Longer voyage, higher stakes.", inline=False)
        await ctx.send(embed=embed, view=SailRiskView(self, ctx.guild.id, ctx.author.id))

    async def start_voyage_from_interaction(
        self,
        *,
        interaction: discord.Interaction,
        guild_id: int,
        user_id: int,
        risk_tier: str,
    ) -> None:
        if self.get_bericore() is None:
            embed = discord.Embed(
                title="Economy Unavailable",
                description=(
                    "Voyage's economy integration (BeriCore) isn't currently available — "
                    "please contact a server admin."
                ),
                colour=VOYAGE_RED,
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        cooldown = await self.db.get_cooldown(guild_id, user_id, ACTION_SAIL)
        if cooldown and cooldown > datetime.now(UTC):
            embed = discord.Embed(
                title="Ship Already at Sea",
                description=f"Return expected in {self.format_remaining(cooldown)}.",
                colour=VOYAGE_RED,
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        config = self.config.guild(interaction.guild)
        if risk_tier == "risky":
            duration_seconds = await config.sail_risky_duration_seconds()
        else:
            duration_seconds = await config.sail_safe_duration_seconds()

        started_at = datetime.now(UTC)
        voyage = await self.db.create_voyage(
            guild_id=guild_id,
            user_id=user_id,
            risk_tier=risk_tier,
            duration_seconds=duration_seconds,
            started_at=started_at,
        )
        expires_at = started_at + timedelta(seconds=duration_seconds)
        await self.db.set_cooldown(guild_id, user_id, ACTION_SAIL, expires_at)

        embed = discord.Embed(
            title="🌊 Voyage Underway",
            description=(
                f"You set sail into **{risk_tier.title()} Waters**. "
                f"The den-den mushi should crackle again in {self.format_remaining(expires_at)}."
            ),
            colour=VOYAGE_BLUE,
        )
        embed.add_field(name="Voyage ID", value=str(voyage["id"]), inline=True)
        embed.add_field(
            name="No Reward Yet",
            value="The sea pays only when the route is complete.",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @tasks.loop(seconds=60)
    async def voyage_resolution_loop(self) -> None:
        due_voyages = await self.db.get_due_voyages()
        for voyage in due_voyages:
            try:
                await self.resolve_voyage(voyage)
            except Exception:
                log.exception("Voyage resolution failed for voyage_id=%s", voyage.get("id"))
        due_contracts = await self.db.get_due_contracts()
        for contract in due_contracts:
            try:
                await self.expire_contract(contract)
            except Exception:
                log.exception("Contract expiry failed for contract_id=%s", contract.get("id"))

    @voyage_resolution_loop.before_loop
    async def before_voyage_resolution_loop(self) -> None:
        await self.bot.wait_until_red_ready()

    async def resolve_voyage(self, voyage: dict[str, Any]) -> None:
        if self.get_bericore() is None:
            log.warning(
                "Skipping voyage resolution for voyage_id=%s because BeriCore is not loaded.",
                voyage["id"],
            )
            return

        guild = self.bot.get_guild(voyage["guild_id"])
        if guild is None:
            await self.db.mark_voyage_resolved(
                voyage["id"],
                outcome_key="guild_missing",
                berry_delta=0,
            )
            return

        member = guild.get_member(voyage["user_id"])
        if member is None:
            await self.db.mark_voyage_resolved(
                voyage["id"],
                outcome_key="member_missing",
                berry_delta=0,
            )
            return

        events = self.sail_events[voyage["risk_tier"]]
        event = self.roll_weighted_event(events)
        requested_delta = self.roll_berry_delta(event)
        reason = (
            f"voyage:sail_{voyage['risk_tier']}_reward"
            if requested_delta >= 0
            else f"voyage:sail_{voyage['risk_tier']}_loss"
        )
        actual_delta, balance_after = await self.apply_beri_delta(
            member=member,
            delta=requested_delta,
            reason=reason,
            action_type="sail_resolution",
            source="sail",
            related_voyage_id=voyage["id"],
            metadata={"event_key": event["key"], "risk_tier": voyage["risk_tier"]},
        )
        await self.db.mark_voyage_resolved(
            voyage["id"],
            outcome_key=event["key"],
            berry_delta=actual_delta,
        )

        channel_id = await self.config.guild(guild).event_channel_id()
        channel = guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                embed=self.build_voyage_result_embed(
                    member=member,
                    voyage=voyage,
                    event=event,
                    requested_delta=requested_delta,
                    actual_delta=actual_delta,
                    balance_after=balance_after,
                )
            )

    @commands.hybrid_group(name="contract", invoke_without_command=True)
    @commands.guild_only()
    async def contract_group(self, ctx: commands.Context) -> None:
        """Post and claim Voyage contracts."""
        prefix = ctx.clean_prefix
        await ctx.send(
            f"Use `{prefix}contract post @target amount` or `{prefix}contract claim @target`."
        )

    @contract_group.command(name="post")
    @commands.guild_only()
    async def contract_post(
        self,
        ctx: commands.Context,
        target: discord.Member,
        amount: int,
        anonymous: bool = False,
    ) -> None:
        """Post or add to a bounty contract."""
        core = await self.require_bericore(ctx)
        if core is None:
            return
        if target.bot or target.id == ctx.author.id:
            await ctx.send("You need a real target who is not yourself.")
            return

        poster_char = await self.db.get_character(ctx.guild.id, ctx.author.id)
        target_char = await self.db.get_character(ctx.guild.id, target.id)
        if poster_char is None:
            await ctx.send(
                "No Voyage dossier found. Use `/character create` before posting contracts."
            )
            return
        if target_char is None:
            await ctx.send(f"{target.display_name} has no Voyage dossier.")
            return

        allowed, reason_text = self.can_target_contract(poster_char, target_char)
        if not allowed:
            await ctx.send(reason_text)
            return

        minimum = await self.config.guild(ctx.guild).contract_minimum_beri()
        if amount < minimum:
            await ctx.send(f"Minimum contract contribution is {minimum:,} Beri.")
            return

        cooldown_key = f"{ACTION_CONTRACT_TARGET}:{target.id}"
        cooldown = await self.db.get_cooldown(ctx.guild.id, ctx.author.id, cooldown_key)
        if cooldown and cooldown > datetime.now(UTC):
            await ctx.send(
                f"You recently targeted {target.display_name}. Try again in "
                f"{self.format_remaining(cooldown)}."
            )
            return

        balance = await core.get_beri(ctx.author)
        if balance < amount:
            await ctx.send(f"You only have {balance:,} Beri. Contracts are paid up front.")
            return

        fee_percent = await self.config.guild(ctx.guild).contract_fee_percent()
        fee_amount = max(0, amount * fee_percent // 100)
        net_amount = amount - fee_amount
        expiry_seconds = await self.config.guild(ctx.guild).contract_expiry_seconds()
        expires_at = datetime.now(UTC) + timedelta(seconds=expiry_seconds)
        contract = await self.db.get_open_contract_for_target(ctx.guild.id, target.id)
        if contract is None:
            contract = await self.db.create_contract(
                guild_id=ctx.guild.id,
                target_user_id=target.id,
                net_amount=0,
                fee_amount=0,
                expires_at=expires_at,
            )

        actual_delta, balance_after = await self.apply_beri_delta(
            member=ctx.author,
            delta=-amount,
            reason="voyage:contract_contribution",
            action_type="contract_contribution",
            source="contract",
            related_contract_id=contract["id"],
            metadata={"target_user_id": target.id, "anonymous": anonymous},
        )
        if actual_delta != -amount:
            if contract["total_pooled"] == 0:
                await self.db.mark_contract_expired(contract["id"])
            await ctx.send(
                "Your balance changed before the contract posted. No contract was created."
            )
            return

        await self.db.add_contract_contribution(
            contract_id=contract["id"],
            contributor_user_id=ctx.author.id,
            amount=amount,
            fee_amount=fee_amount,
            anonymous=anonymous,
        )
        contract = await self.db.get_contract(contract["id"])
        await self.db.log_transaction(
            guild_id=ctx.guild.id,
            user_id=ctx.author.id,
            source="contract",
            action_type="contract_fee",
            delta_requested=-fee_amount,
            delta_applied=-fee_amount,
            reason="voyage:contract_posting_fee",
            balance_after=balance_after,
            related_contract_id=contract["id"],
            status="sink_accounting",
            metadata={"gross_amount": amount, "net_pool": net_amount},
        )

        retarget_seconds = await self.config.guild(ctx.guild).contract_retarget_cooldown_seconds()
        await self.db.set_cooldown(
            ctx.guild.id,
            ctx.author.id,
            cooldown_key,
            datetime.now(UTC) + timedelta(seconds=retarget_seconds),
        )

        channel_id = await self.config.guild(ctx.guild).event_channel_id()
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        tier = await self.contract_tier(ctx.guild, contract["total_pooled"])
        embed = self.build_contract_embed(
            contract=contract,
            target=target,
            tier=tier,
            contributor=ctx.author,
        )
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
        await ctx.send(
            f"Contract posted. {net_amount:,} Beri entered the pool; "
            f"{fee_amount:,} Beri was burned as the posting fee.",
            embed=embed,
        )

    @contract_group.command(name="claim")
    @commands.guild_only()
    async def contract_claim(self, ctx: commands.Context, target: discord.Member) -> None:
        """Claim an open contract and resolve it immediately for v1."""
        if await self.require_bericore(ctx) is None:
            return
        contract = await self.db.get_open_contract_for_target(ctx.guild.id, target.id)
        if contract is None:
            await ctx.send(f"No open contract exists for {target.display_name}.")
            return
        if target.id == ctx.author.id:
            await ctx.send("You cannot claim a contract on yourself.")
            return
        if await self.db.user_contributed_to_contract(contract["id"], ctx.author.id):
            await ctx.send("You cannot claim a contract you helped fund.")
            return

        claimer_char = await self.db.get_character(ctx.guild.id, ctx.author.id)
        target_char = await self.db.get_character(ctx.guild.id, target.id)
        if claimer_char is None:
            await ctx.send(
                "No Voyage dossier found. Use `/character create` before claiming contracts."
            )
            return
        if target_char is None:
            await ctx.send(f"{target.display_name} has no Voyage dossier.")
            return

        allowed, reason_text = self.can_target_contract(claimer_char, target_char)
        if not allowed:
            await ctx.send(reason_text)
            return

        claimed = await self.db.claim_contract(contract["id"], ctx.author.id)
        if not claimed:
            await ctx.send("That contract was claimed first by someone else.")
            return

        contract = await self.db.get_contract(contract["id"])
        result = await self.resolve_contract_claim(
            contract=contract,
            claimer=ctx.author,
            target=target,
            claimer_char=claimer_char,
            target_char=target_char,
        )
        await ctx.send(embed=result)

    async def resolve_contract_claim(
        self,
        *,
        contract: dict[str, Any],
        claimer: discord.Member,
        target: discord.Member,
        claimer_char: dict[str, Any],
        target_char: dict[str, Any],
    ) -> discord.Embed:
        claimer_power = self.contract_roll_power(claimer_char)
        target_power = self.contract_roll_power(target_char)
        margin = claimer_power - target_power
        danger_label, danger_reward = self.danger_tier(target_char)

        contract_tier = await self.contract_tier(claimer.guild, contract["total_pooled"])

        if margin >= 10:
            outcome = "claimer_wins_big"
            payout = contract["total_pooled"]
            rank_delta = danger_reward
            penalty_percent = CONTRACT_BIG_WIN_PENALTY_PERCENT[contract_tier]
        elif margin > 0:
            outcome = "claimer_wins_small"
            payout = contract["total_pooled"]
            rank_delta = max(1, danger_reward - 1)
            penalty_percent = CONTRACT_SMALL_WIN_PENALTY_PERCENT[contract_tier]
        elif margin <= -10:
            outcome = "claimer_loses"
            payout = 0
            rank_delta = 0
            penalty_percent = 0
        else:
            outcome = "target_escapes"
            payout = 0
            rank_delta = 0
            penalty_percent = 0

        balance_after = None
        if payout:
            _actual_delta, balance_after = await self.apply_beri_delta(
                member=claimer,
                delta=payout,
                reason="voyage:contract_payout",
                action_type="contract_payout",
                source="contract",
                related_contract_id=contract["id"],
                metadata={
                    "target_user_id": target.id,
                    "outcome": outcome,
                    "danger_tier": danger_label,
                    "claimer_power": claimer_power,
                    "target_power": target_power,
                },
            )

        target_penalty = 0
        target_balance_after = None
        if penalty_percent:
            core = self.get_bericore()
            if core is not None:
                target_balance = await core.get_beri(target)
                nominal_penalty = (
                    max(1, target_balance * penalty_percent // 100) if target_balance else 0
                )
                if nominal_penalty:
                    actual_delta, target_balance_after = await self.apply_beri_delta(
                        member=target,
                        delta=-nominal_penalty,
                        reason="voyage:contract_target_penalty",
                        action_type="contract_target_penalty",
                        source="contract",
                        related_contract_id=contract["id"],
                        metadata={
                            "claimer_user_id": claimer.id,
                            "outcome": outcome,
                            "penalty_percent": penalty_percent,
                            "contract_tier": contract_tier,
                        },
                    )
                    target_penalty = abs(actual_delta)

        rank_field = get_faction(claimer_char["faction"]).renown_field
        if rank_delta:
            await self.db.add_renown(claimer.guild.id, claimer.id, rank_field, rank_delta)

        await self.db.mark_contract_resolved(contract["id"])
        embed = self.build_contract_result_embed(
            contract=contract,
            target=target,
            claimer=claimer,
            outcome=outcome,
            payout=payout,
            rank_field=rank_field,
            rank_delta=rank_delta,
            target_penalty=target_penalty,
            target_balance_after=target_balance_after,
        )
        if balance_after is not None:
            embed.add_field(name="New Balance", value=f"{balance_after:,} Beri", inline=True)
        channel_id = await self.config.guild(claimer.guild).event_channel_id()
        channel = claimer.guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)
        return embed

    async def expire_contract(self, contract: dict[str, Any]) -> None:
        if self.get_bericore() is None:
            log.warning(
                "Skipping contract expiry for contract_id=%s because BeriCore is not loaded.",
                contract["id"],
            )
            return

        guild = self.bot.get_guild(contract["guild_id"])
        if guild is None:
            await self.db.mark_contract_expired(contract["id"])
            return
        contributions = await self.db.get_contract_contributions(contract["id"])
        for contribution in contributions:
            member = guild.get_member(contribution["contributor_user_id"])
            if member is None:
                continue
            refund = max(0, contribution["amount"] - contribution["fee_amount"])
            if refund:
                await self.apply_beri_delta(
                    member=member,
                    delta=refund,
                    reason="voyage:contract_refund",
                    action_type="contract_refund",
                    source="contract",
                    related_contract_id=contract["id"],
                    metadata={"expired_contract_id": contract["id"]},
                )
        await self.db.mark_contract_expired(contract["id"])

        target = guild.get_member(contract["target_user_id"])
        channel_id = await self.config.guild(guild).event_channel_id()
        channel = guild.get_channel(channel_id) if channel_id else None
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                title="📜 Contract Expired",
                description=(
                    f"The contract on {target.mention if target else 'an unknown target'} expired. "
                    "Contributors were refunded minus posting fees."
                ),
                colour=discord.Colour.dark_grey(),
            )
            embed.set_footer(text=f"Contract #{contract['id']}")
            await channel.send(embed=embed)

    @commands.hybrid_group(name="voyageadmin", invoke_without_command=True)
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def voyage_admin_group(self, ctx: commands.Context) -> None:
        """Admin controls for Voyage."""
        prefix = ctx.clean_prefix
        await ctx.send(
            f"Use `{prefix}voyageadmin setchannel` or `{prefix}voyageadmin resetplayer @user`."
        )

    @voyage_admin_group.command(name="setchannel")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def voyageadmin_setchannel(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel | None = None,
    ) -> None:
        """Set the Voyage event channel for this guild."""
        target = channel or ctx.channel
        if not isinstance(target, discord.TextChannel):
            await ctx.send("Voyage needs a text channel for event dispatch.")
            return

        await self.config.guild(ctx.guild).event_channel_id.set(target.id)
        embed = discord.Embed(
            title="Voyage Channel Charted",
            description=f"Future Voyage notices will point toward {target.mention}.",
            colour=VOYAGE_BLUE,
        )
        embed.set_footer(text=f"Guild ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @voyage_admin_group.command(name="resetplayer")
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def voyageadmin_resetplayer(self, ctx: commands.Context, member: discord.Member) -> None:
        """Delete a player's Voyage character and cooldowns."""
        deleted = await self.db.delete_character(ctx.guild.id, member.id)
        if deleted:
            description = f"{member.mention}'s Voyage dossier and cooldowns were cleared."
            colour = VOYAGE_BLUE
        else:
            description = f"No Voyage dossier existed for {member.mention}."
            colour = discord.Colour.dark_grey()

        embed = discord.Embed(
            title="Voyage Reset Complete",
            description=description,
            colour=colour,
        )
        embed.set_footer(text=f"Reset by {ctx.author.display_name}")
        await ctx.send(embed=embed)
