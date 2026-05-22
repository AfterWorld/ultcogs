"""
DankMemer-style activity commands for the Beri economy cog.
Balance ops go through BeriCoreBridge -> BeriCore API.
"""

import asyncio
import random
from typing import Optional

import discord
from redbot.core import commands

from .fruitbonuses import FRUIT_COMMAND_BONUSES
from redbot.core.utils.chat_formatting import humanize_number

VAULT_SECURITY_LEVELS = {
    "basic": {"label": "Basic", "protection": 0.0, "cost": 0},
    "secure": {"label": "Secure", "protection": 0.25, "cost": 5000},
    "fortified": {"label": "Fortified", "protection": 0.50, "cost": 15000},
    "impenetrable": {"label": "Impenetrable", "protection": 0.75, "cost": 40000},
}

VAULT_ORDER = ["basic", "secure", "fortified", "impenetrable"]

WORK_JOBS = [
    ("🍕 Pizza Delivery", 500, 1200),
    ("🔧 Mechanic", 700, 1500),
    ("🎸 Street Musician", 250, 900),
    ("⚓ Ship Deckhand", 900, 1700),
    ("🏴‍☠️ Bounty Hunter", 1000, 2000),
    ("🐟 Fisherman", 400, 1200),
    ("🗡️ Mercenary", 1400, 2400),
    ("🍜 Ramen Chef", 600, 1300),
    ("📦 Warehouse Worker", 400, 900),
    ("🗺️ Navigator", 900, 1800),
    ("⚔️ Swordsmith Apprentice", 800, 1700),
    ("🌺 Flower Shop Assistant", 300, 900),
]

WORK_SUCCESS = [
    "You pulled a hard watch on deck and pocketed {amount} {icon}.",
    "The crew paid up for your ship duties. Earned {amount} {icon}.",
    "A solid shift on the Grand Line paid off — {amount} {icon} in your pocket.",
    "You finished your share of chores and got {amount} {icon} from the captain.",
    "A salty sailor tipped you nicely. Total: {amount} {icon}.",
]

CRIME_SCENARIOS = [
    ("🎭 Con Artist", 800, 2500, 0.55),
    ("🏦 Bank Heist", 1500, 6000, 0.35),
    ("🎰 Rigged Card Game", 600, 2200, 0.50),
    ("🚢 Smuggling Contraband", 1800, 4200, 0.40),
    ("🎪 Festival Pickpocket", 300, 1500, 0.65),
    ("💣 Explosive Distraction Robbery", 2400, 6000, 0.30),
    ("🌃 Night Market Scam", 500, 2100, 0.60),
]

CRIME_SUCCESS = [
    "Pulled it off without a hitch and escaped with {amount} {icon}.",
    "The crew's plan worked — you made off with {amount} {icon}.",
    "You dodged the Marines and slipped away with {amount} {icon}.",
]
CRIME_FAIL = [
    "The Marines were waiting. You escaped, but paid {fine} {icon} in fines.",
    "A rat in the crew sold you out. You paid {fine} {icon} to stay alive.",
    "Caught with the loot — lost {fine} {icon} while fleeing.",
]

HACK_TARGETS = [
    ("💻 Marine Database", 1200, 3600, 0.50),
    ("🏦 World Government Treasury", 3000, 9000, 0.25),
    ("📡 Enies Lobby Comms", 900, 2700, 0.55),
    ("🛒 Black Market Server", 600, 2100, 0.60),
    ("📱 Celestial Dragon Phone", 1500, 4500, 0.40),
]

HACK_SUCCESS = [
    "You ghosted the Marine firewall and siphoned {amount} {icon} unnoticed.",
    "Cipher Pol never knew what hit them — {amount} {icon} drained cleanly.",
    "A flawless breach. {amount} {icon} slid into your wallet in silence.",
]
HACK_FAIL = [
    "The World Government traced you. Lost {fine} {icon} covering your escape.",
    "Their counter-hack hit hard. Locked out and fined {fine} {icon}.",
    "Cipher Pol caught your signal — {fine} {icon} seized before you could flee.",
]

SLUT_SCENARIOS = [
    ("💃 Cabaret Performance", 600, 2200),
    ("🎤 Suggestive Karaoke", 300, 1500),
    ("🃏 Strip Poker Host", 900, 2600),
    ("🌹 Companion for Hire", 500, 1800),
    ("🎭 Risqué Theater Act", 600, 1600),
]
SLUT_SUCCESS = [
    "The crowd at the tavern went wild. You collected {amount} {icon} in tips.",
    "Sold out the seaside lounge. Walked away with {amount} {icon}.",
    "The performance was a hit. You left {amount} {icon} richer.",
]

PLUNDER_SCENARIOS = [
    ("Merchant Bank Caravan", 800, 2600, 0.55),
    ("Vaulted Treasure Convoy", 1200, 3600, 0.45),
    ("Black Market Caravan", 1000, 3000, 0.50),
    ("Government Escort", 1500, 4200, 0.40),
    ("Imperial Vault Shipment", 2200, 7200, 0.30),
]

PLUNDER_SUCCESS = [
    "You raided the shipment and absconded with {amount} {icon}.",
    "The operation paid off — the hold is lighter and your purse is heavier by {amount} {icon}.",
    "Your crew walked away with {amount} {icon} in loot and valuables.",
]
PLUNDER_FAIL = [
    "The guards fought back. You escaped, but lost {fine} {icon} in damaged cargo.",
    "The convoy broke formation and you had to flee empty-handed.",
    "A failed plunder cost you {fine} {icon} while you made your escape.",
]

DAILY_REWARDS = [1000, 1250, 1500, 1750, 2000, 2250]


class Work(commands.Cog):
    """
    Activity commands mixin. Expects parent to expose:
      - self._get_balance(guild, member)
      - self._safe_modify(ctx, guild, member, delta, reason=, actor=, bypass_cap=)
      - self._modify_balance(guild, member, delta, reason=, actor=, bypass_cap=)
      - self._currency_fmt(guild)
    """

    async def _fruit_effects(self, member: discord.Member) -> dict:
        fruit_data = await self._get_fruit_data(member)
        return FRUIT_COMMAND_BONUSES.get(fruit_data.get("fruit_name", ""), {})

    def _apply_activity_amount_bonus(self, amount: int, effects: dict) -> int:
        return int(amount * (1.0 + effects.get("all_activity_luck", 0.0)))

    def _apply_activity_success_bonus(self, rate: float, effects: dict) -> float:
        return min(0.95, rate + effects.get("all_activity_luck", 0.0))

    def _reduce_command_cooldown(self, ctx: commands.Context, reduction_pct: float):
        bucket = ctx.command._buckets.get_bucket(ctx.message)
        if bucket is None:
            return
        current = ctx.message.created_at.timestamp()
        remaining = bucket.get_retry_after(current)
        if remaining <= 0:
            return
        new_remaining = max(0.0, remaining * (1.0 - reduction_pct))
        bucket._window = current - (bucket.per - new_remaining)
        bucket._tokens = 0

    @commands.command(name="work")
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Take on a One Piece-themed job and earn Beri. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi = random.choice(WORK_JOBS)
        amount = random.randint(lo, hi)
        effects = await self._fruit_effects(ctx.author)
        amount = self._apply_activity_amount_bonus(amount, effects)

        # Apply weather multipliers and Yonko tribute
        weather_mult = await self.get_weather_modifier(ctx.guild, "work_multiplier")
        amount = int(amount * weather_mult)

        tribute = await self.collect_yonko_tribute(ctx.guild, ctx.author, amount)
        amount -= tribute

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, amount,
            reason="activity:work", actor="System",
            metadata={"job": job_name},
        )
        if new_bal is None:
            return

        msg = random.choice(WORK_SUCCESS).format(amount=humanize_number(amount), icon=icon)
        embed = discord.Embed(title=f"👷 {job_name}", description=msg, color=discord.Color.green())
        embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next work in 1 hour")
        await ctx.send(embed=embed)

    @commands.command(name="crime")
    @commands.guild_only()
    @commands.cooldown(1, 7200, commands.BucketType.user)
    async def crime(self, ctx: commands.Context):
        """Attempt a shady One Piece caper for Beri. (2 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        job_name, lo, hi, success_rate = random.choice(CRIME_SCENARIOS)
        success_rate = self._apply_activity_success_bonus(success_rate, effects) + effects.get("crime_success_bonus", 0.0)
        # Apply weather crime delta
        weather_crime_delta = await self.get_weather_modifier(ctx.guild, "crime_success_delta", default=0.0)
        success_rate += weather_crime_delta
        won = random.random() < success_rate

        if won:
            amount = random.randint(lo, hi)
            amount = int(amount * effects.get("crime_payout_mul", 1.0))
            amount = self._apply_activity_amount_bonus(amount, effects)
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, amount,
                reason="activity:crime:success", actor="System",
                metadata={"crime": job_name, "outcome": "success"},
            )
            if new_bal is None:
                return
            msg = random.choice(CRIME_SUCCESS).format(amount=humanize_number(amount), icon=icon)
            embed = discord.Embed(title=f"🦹 {job_name} — SUCCESS", description=msg, color=discord.Color.green())
            embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        else:
            balance = await self._get_balance(ctx.guild, ctx.author)
            fine = min(random.randint(lo // 3, hi // 3), balance)
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, -fine,
                reason="activity:crime:caught", actor="System", bypass_cap=True,
                metadata={"crime": job_name, "outcome": "caught"},
            )
            if new_bal is None:
                return
            msg = random.choice(CRIME_FAIL).format(fine=humanize_number(fine), icon=icon)
            embed = discord.Embed(title=f"🦹 {job_name} — CAUGHT", description=msg, color=discord.Color.red())
            embed.add_field(name="Fine", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next crime in 2 hours")
        await ctx.send(embed=embed)

    @commands.command(name="hack")
    @commands.guild_only()
    @commands.cooldown(1, 5400, commands.BucketType.user)
    async def hack(self, ctx: commands.Context, target: Optional[discord.Member] = None, *, mode: str = "wallet"):
        """Hack World Government systems or siphon another pirate's wallet or vault. (90 min cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        mode = mode.lower() if mode else "wallet"

        if target and target != ctx.author and not target.bot:
            if mode in ("vault", "bank"):
                vault = await self.config.member(target).vault()
                vault_balance = vault.get("balance", 0)
                if vault_balance < 50:
                    return await ctx.send(f"❌ {target.mention}'s vault doesn't have enough Beri to hack.")

                security = vault.get("security", "basic")
                protection = VAULT_SECURITY_LEVELS.get(security, VAULT_SECURITY_LEVELS["basic"])["protection"]
                success_rate = max(0.10, 0.50 - protection * 0.35)
                won = random.random() < success_rate
                if won:
                    amount = random.randint(50, min(500, vault_balance // 4))
                    amount = int(amount * effects.get("hack_amount_mul", 1.0))
                    amount = self._apply_activity_amount_bonus(amount, effects)
                    amount = min(amount, vault_balance)
                    vault["balance"] = vault_balance - amount
                    await self.config.member(target).vault.set(vault)
                    try:
                        new_bal = await self._modify_balance(ctx.guild, ctx.author, amount, reason=f"hack:vault:success", actor="System", metadata={"target_id": target.id, "target_type": "vault"})
                    except RuntimeError as e:
                        return await ctx.send(f"❌ {e}")
                    embed = discord.Embed(title="💻 Vault Hack — SUCCESS", description=f"You cracked {target.mention}'s vault and siphoned **{humanize_number(amount)}** {icon}.", color=discord.Color.green())
                    embed.add_field(name="Stolen", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
                else:
                    balance = await self._get_balance(ctx.guild, ctx.author)
                    fine = min(random.randint(75, 450), balance)
                    if effects.get("hack_fail_no_fine"):
                        fine = 0
                    new_bal = await self._safe_modify(ctx, ctx.guild, ctx.author, -fine, reason="hack:vault:fail", actor="System", bypass_cap=True)
                    if new_bal is None:
                        return
                    embed = discord.Embed(title="💻 Vault Hack — TRACED", description=f"{target.mention}'s vault security blocked your attempt. You lost **{humanize_number(fine)}** {icon}.", color=discord.Color.red())
                    embed.add_field(name="Lost", value=f"**-{humanize_number(fine)}** {icon}", inline=True)
            else:
                victim_bal = await self._get_balance(ctx.guild, target)
                if victim_bal < 50:
                    return await ctx.send(f"❌ {target.mention} is too broke to hack.")
                success_rate = self._apply_activity_success_bonus(0.45, effects)
                won = random.random() < success_rate
                if won:
                    amount = random.randint(50, min(500, victim_bal // 4))
                    amount = int(amount * effects.get("hack_amount_mul", 1.0))
                    amount = self._apply_activity_amount_bonus(amount, effects)
                    try:
                        await self._modify_balance(ctx.guild, target, -amount, reason=f"hack:victim:{ctx.author.id}", actor=ctx.author)
                        new_bal = await self._modify_balance(ctx.guild, ctx.author, amount, reason=f"hack:attacker:{target.id}", actor="System", metadata={"victim_id": target.id})
                    except RuntimeError as e:
                        return await ctx.send(f"❌ {e}")
                    embed = discord.Embed(title="💻 Hack — SUCCESS", description=f"You cracked {target.mention}'s wallet and siphoned **{humanize_number(amount)}** {icon}.", color=discord.Color.green())
                    embed.add_field(name="Stolen", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
                else:
                    balance = await self._get_balance(ctx.guild, ctx.author)
                    fine = min(random.randint(50, 300), balance)
                    if effects.get("hack_fail_no_fine"):
                        fine = 0
                    new_bal = await self._safe_modify(ctx, ctx.guild, ctx.author, -fine, reason="hack:fail", actor="System", bypass_cap=True)
                    if new_bal is None:
                        return
                    description = f"{target.mention}'s firewall fought back. You lost **{humanize_number(fine)}** {icon}."
                    if fine == 0 and effects.get("hack_fail_no_fine"):
                        description = f"Your Yami fruit warped the penalty away. No Beri was lost."
                    embed = discord.Embed(title="💻 Hack — TRACED", description=description, color=discord.Color.red())
                    embed.add_field(name="Lost", value=f"**-{humanize_number(fine)}** {icon}", inline=True)
        else:
            sys_name, lo, hi, success_rate = random.choice(HACK_TARGETS)
            won = random.random() < success_rate
            if won:
                amount = random.randint(lo, hi)
                new_bal = await self._safe_modify(ctx, ctx.guild, ctx.author, amount, reason="activity:hack:success", actor="System", metadata={"target": sys_name})
                if new_bal is None:
                    return
                msg = random.choice(HACK_SUCCESS).format(amount=humanize_number(amount), icon=icon)
                embed = discord.Embed(title=f"💻 {sys_name} — BREACHED", description=msg, color=discord.Color.green())
                embed.add_field(name="Stolen", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
            else:
                balance = await self._get_balance(ctx.guild, ctx.author)
                fine = min(random.randint(lo // 4, hi // 4), balance)
                new_bal = await self._safe_modify(ctx, ctx.guild, ctx.author, -fine, reason="activity:hack:fail", actor="System", bypass_cap=True)
                if new_bal is None:
                    return
                msg = random.choice(HACK_FAIL).format(fine=humanize_number(fine), icon=icon)
                embed = discord.Embed(title=f"💻 {sys_name} — TRACED", description=msg, color=discord.Color.red())
                embed.add_field(name="Fine", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next hack in 90 min")
        if effects.get("hack_cooldown_reduction_pct"):
            self._reduce_command_cooldown(ctx, effects["hack_cooldown_reduction_pct"])
        await ctx.send(embed=embed)

    @commands.command(name="slut", aliases=["sexy", "exotic"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def slut(self, ctx: commands.Context):
        """Use your charm and earn Beri in a Grand Line venue. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        job_name, lo, hi = random.choice(SLUT_SCENARIOS)
        amount = random.randint(lo, hi)
        amount = self._apply_activity_amount_bonus(amount, effects)

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, amount,
            reason="activity:slut", actor="System",
        )
        if new_bal is None:
            return

        msg = random.choice(SLUT_SUCCESS).format(amount=humanize_number(amount), icon=icon)
        embed = discord.Embed(title=f"💋 {job_name}", description=msg, color=discord.Color.magenta())
        embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next in 1 hour")
        await ctx.send(embed=embed)

    @commands.command(name="beg")
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def beg(self, ctx: commands.Context):
        """Plead your case and scrounge up some Beri from the crew. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        outcomes = [
            ("A passing pirate dropped some coins in your hat.", random.randint(100, 400)),
            ("A shipmate felt sorry for you and tossed you some Beri.", random.randint(150, 500)),
            ("You sang a sorrowful shanty and earned a few generous tips.", random.randint(120, 450)),
        ]
        success = random.random() < self._apply_activity_success_bonus(0.75, effects)
        if success:
            message, amount = random.choice(outcomes)
            amount = self._apply_activity_amount_bonus(amount, effects)
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, amount,
                reason="activity:beg", actor="System",
            )
            if new_bal is None:
                return
            embed = discord.Embed(
                title="🪖 Begging — SUCCESS",
                description=message,
                color=discord.Color.green(),
            )
            embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        else:
            new_bal = await self._get_balance(ctx.guild, ctx.author)
            embed = discord.Embed(
                title="🪖 Begging — NO LUCK",
                description="The crew is too stingy today. No Beri came your way.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Earned", value=f"**+0** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next beg in 1 hour")
        await ctx.send(embed=embed)

    @commands.command(name="plunder")
    @commands.guild_only()
    @commands.cooldown(1, 10800, commands.BucketType.user)
    async def plunder(self, ctx: commands.Context):
        """Raid a ship or convoy and claim loot for your crew. (3 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        target_name, lo, hi, success_rate = random.choice(PLUNDER_SCENARIOS)
        success_rate = self._apply_activity_success_bonus(success_rate, effects)
        won = random.random() < success_rate

        if won:
            amount = random.randint(lo, hi)
            amount = int(amount * effects.get("plunder_payout_mul", 1.0))
            amount = self._apply_activity_amount_bonus(amount, effects)
            # Apply weather plunder multiplier
            weather_plunder = await self.get_weather_modifier(ctx.guild, "plunder_multiplier")
            amount = int(amount * weather_plunder)
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, amount,
                reason="activity:plunder:success", actor="System",
                metadata={"target": target_name, "outcome": "success"},
            )
            if new_bal is None:
                return
            msg = random.choice(PLUNDER_SUCCESS).format(amount=humanize_number(amount), icon=icon)
            embed = discord.Embed(
                title=f"🏴‍☠️ Plunder — {target_name}",
                description=msg,
                color=discord.Color.gold(),
            )
            embed.add_field(name="Loot", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        else:
            fine = min(random.randint(50, 200), await self._get_balance(ctx.guild, ctx.author))
            new_bal = await self._safe_modify(
                ctx, ctx.guild, ctx.author, -fine,
                reason="activity:plunder:fail", actor="System", bypass_cap=True,
                metadata={"target": target_name, "outcome": "fail"},
            )
            if new_bal is None:
                return
            msg = random.choice(PLUNDER_FAIL).format(fine=humanize_number(fine), icon=icon)
            embed = discord.Embed(
                title=f"🏴‍☠️ Plunder — {target_name} Failed",
                description=msg,
                color=discord.Color.red(),
            )
            embed.add_field(name="Loss", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next plunder in 3 hours")
        await ctx.send(embed=embed)

    @commands.command(name="daily")
    @commands.guild_only()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def daily(self, ctx: commands.Context):
        """Claim your daily Beri ration. (24 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        effects = await self._fruit_effects(ctx.author)
        amount = random.choice(DAILY_REWARDS)
        amount = self._apply_activity_amount_bonus(amount, effects)
        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, amount,
            reason="activity:daily", actor="System",
        )
        if new_bal is None:
            return

        embed = discord.Embed(
            title="🌅 Daily Rations",
            description=f"You claimed your daily Beri ration and gained **{humanize_number(amount)}** {icon}.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next daily in 24 hours")
        await ctx.send(embed=embed)

    @commands.command(name="rob", aliases=["steal"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, target: discord.Member):
        """Attempt to rob another user. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        attacker_effects = await self._fruit_effects(ctx.author)

        if target == ctx.author:
            return await ctx.send("❌ You can't rob yourself.")
        if target.bot:
            return await ctx.send("❌ Bots don't carry Beri.")

        victim_bal = await self._get_balance(ctx.guild, target)
        robber_bal = await self._get_balance(ctx.guild, ctx.author)
        target_fruit = await self._get_fruit_data(target)
        if target_fruit.get("fruit_name") == "Bara Bara no Mi" and random.random() < 0.5:
            return await ctx.send(f"❌ {target.mention}'s Bara Bara no Mi made them untouchable this time.")

        if victim_bal < 100:
            return await ctx.send(f"❌ {target.mention} doesn't have enough to be worth robbing.")

        ratio = min(robber_bal / max(victim_bal, 1), 2.0)
        success_rate = max(0.25, min(0.65, 0.40 + (ratio - 1) * 0.15))
        success_rate += attacker_effects.get("rob_success_bonus", 0.0)
        success_rate = self._apply_activity_success_bonus(success_rate, attacker_effects)
        # Apply weather rob delta
        weather_rob_delta = await self.get_weather_modifier(ctx.guild, "rob_success_delta", default=0.0)
        success_rate += weather_rob_delta
        won = random.random() < success_rate

        if won:
            stolen = max(50, random.randint(int(victim_bal * 0.05), int(victim_bal * 0.25)))
            stolen = int(stolen * attacker_effects.get("rob_stolen_mul", 1.0))
            stolen = self._apply_activity_amount_bonus(stolen, attacker_effects)
            try:
                await self._modify_balance(ctx.guild, target, -stolen, reason=f"rob:victim:{ctx.author.id}", actor=ctx.author)
                new_bal = await self._modify_balance(ctx.guild, ctx.author, stolen, reason=f"rob:success:{target.id}", actor="System", metadata={"victim_id": target.id, "amount": stolen})
            except RuntimeError as e:
                return await ctx.send(f"❌ {e}")
            embed = discord.Embed(
                title="🔫 Robbery — SUCCESS",
                description=f"You cornered {target.mention} in a dark alley and made off with **{humanize_number(stolen)}** {icon}!",
                color=discord.Color.green(),
            )
            embed.add_field(name="Stolen", value=f"**+{humanize_number(stolen)}** {icon}", inline=True)
        else:
            fine = max(50, min(random.randint(int(robber_bal * 0.10), int(robber_bal * 0.30)), robber_bal))
            victim_share = fine // 2
            try:
                await self._modify_balance(ctx.guild, target, victim_share, reason=f"rob:damages:{ctx.author.id}", actor="System")
                new_bal = await self._modify_balance(ctx.guild, ctx.author, -fine, reason=f"rob:fail:{target.id}", actor="System")
            except RuntimeError as e:
                return await ctx.send(f"❌ {e}")
            embed = discord.Embed(
                title="🔫 Robbery — BUSTED",
                description=(
                    f"{target.mention} fought back and called the marines! "
                    f"You were fined **{humanize_number(fine)}** {icon}.\n"
                    f"{target.mention} received **{humanize_number(victim_share)}** {icon} in damages."
                ),
                color=discord.Color.red(),
            )
            embed.add_field(name="Fine", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next rob in 1 hour")
        await ctx.send(embed=embed)

    @commands.command(name="cooldowns", aliases=["cd", "activitycd", "cooldown"])
    @commands.guild_only()
    async def cooldowns(self, ctx: commands.Context):
        """Show remaining cooldowns for Beri activity commands."""
        command_names = ["work", "crime", "hack", "slut", "beg", "plunder", "daily", "rob"]
        lines = []
        current = ctx.message.created_at.timestamp()
        for name in command_names:
            command = ctx.bot.get_command(name)
            if command is None:
                continue
            bucket = command._buckets.get_bucket(ctx.message)
            retry = bucket.get_retry_after(current) if bucket else 0.0
            if retry and retry > 0:
                seconds = int(retry)
                mins, secs = divmod(seconds, 60)
                hours, mins = divmod(mins, 60)
                if hours:
                    remaining = f"{hours}h {mins}m {secs}s"
                elif mins:
                    remaining = f"{mins}m {secs}s"
                else:
                    remaining = f"{secs}s"
                lines.append(f"**.{name}** — {remaining}")
            else:
                lines.append(f"**.{name}** — Ready")

        embed = discord.Embed(
            title="🕒 Activity Cooldowns",
            description="\n".join(lines) if lines else "No activity commands found.",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Check back when the sea calls you again.")
        await ctx.send(embed=embed)

    @work.error
    @crime.error
    @hack.error
    @slut.error
    @beg.error
    @plunder.error
    @daily.error
    @rob.error
    async def _activity_cooldown_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            m, s = divmod(int(error.retry_after), 60)
            h, m = divmod(m, 60)
            time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
            await ctx.send(f"⏳ You're on cooldown! Try again in **{time_str}**.")
        else:
            raise error
