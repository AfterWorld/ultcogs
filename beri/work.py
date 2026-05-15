"""
DankMemer-style activity commands for the Beri economy cog.
Balance ops go through BeriCoreBridge -> BeriCore API.
"""

import asyncio
import random
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

WORK_JOBS = [
    ("🍕 Pizza Delivery", 150, 400),
    ("🔧 Mechanic", 200, 500),
    ("🎸 Street Musician", 50, 300),
    ("⚓ Ship Deckhand", 250, 600),
    ("🏴‍☠️ Bounty Hunter", 300, 700),
    ("🐟 Fisherman", 100, 350),
    ("🗡️ Mercenary", 400, 800),
    ("🍜 Ramen Chef", 150, 450),
    ("📦 Warehouse Worker", 100, 300),
    ("🗺️ Navigator", 250, 550),
    ("⚔️ Swordsmith Apprentice", 200, 600),
    ("🌺 Flower Shop Assistant", 80, 250),
]

WORK_SUCCESS = [
    "You pulled a hard watch on deck and pocketed {amount} {icon}.",
    "The crew paid up for your ship duties. Earned {amount} {icon}.",
    "A solid shift on the Grand Line paid off — {amount} {icon} in your pocket.",
    "You finished your share of chores and got {amount} {icon} from the captain.",
    "A salty sailor tipped you nicely. Total: {amount} {icon}.",
]

CRIME_SCENARIOS = [
    ("🎭 Con Artist", 300, 900, 0.55),
    ("🏦 Bank Heist", 500, 2000, 0.35),
    ("🎰 Rigged Card Game", 200, 800, 0.50),
    ("🚢 Smuggling Contraband", 600, 1500, 0.40),
    ("🎪 Festival Pickpocket", 100, 500, 0.65),
    ("💣 Explosive Distraction Robbery", 800, 2500, 0.30),
    ("🌃 Night Market Scam", 150, 700, 0.60),
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
    ("💻 Marine Database", 400, 1200, 0.50),
    ("🏦 World Government Treasury", 1000, 3000, 0.25),
    ("📡 Enies Lobby Comms", 300, 900, 0.55),
    ("🛒 Black Market Server", 200, 700, 0.60),
    ("📱 Celestial Dragon Phone", 500, 1500, 0.40),
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
    ("💃 Cabaret Performance", 200, 800),
    ("🎤 Suggestive Karaoke", 100, 500),
    ("🃏 Strip Poker Host", 300, 900),
    ("🌹 Companion for Hire", 150, 700),
    ("🎭 Risqué Theater Act", 200, 600),
]
SLUT_SUCCESS = [
    "The crowd at the tavern went wild. You collected {amount} {icon} in tips.",
    "Sold out the seaside lounge. Walked away with {amount} {icon}.",
    "The performance was a hit. You left {amount} {icon} richer.",
]


class Work(commands.Cog):
    """
    Activity commands mixin. Expects parent to expose:
      - self._get_balance(guild, member)
      - self._safe_modify(ctx, guild, member, delta, reason=, actor=, bypass_cap=)
      - self._modify_balance(guild, member, delta, reason=, actor=, bypass_cap=)
      - self._currency_fmt(guild)
    """

    @commands.command(name="work")
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Take on a One Piece-themed job and earn Beri. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi = random.choice(WORK_JOBS)
        amount = random.randint(lo, hi)

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
        job_name, lo, hi, success_rate = random.choice(CRIME_SCENARIOS)
        won = random.random() < success_rate

        if won:
            amount = random.randint(lo, hi)
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
    async def hack(self, ctx: commands.Context, target: Optional[discord.Member] = None):
        """Hack World Government systems or siphon another pirate's Beri. (90 min cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)

        if target and target != ctx.author and not target.bot:
            victim_bal = await self._get_balance(ctx.guild, target)
            if victim_bal < 50:
                return await ctx.send(f"❌ {target.mention} is too broke to hack.")
            won = random.random() < 0.45
            if won:
                amount = random.randint(50, min(500, victim_bal // 4))
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
                new_bal = await self._safe_modify(ctx, ctx.guild, ctx.author, -fine, reason="hack:fail", actor="System", bypass_cap=True)
                if new_bal is None:
                    return
                embed = discord.Embed(title="💻 Hack — TRACED", description=f"{target.mention}'s firewall fought back. You lost **{humanize_number(fine)}** {icon}.", color=discord.Color.red())
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
        await ctx.send(embed=embed)

    @commands.command(name="slut", aliases=["sexy", "exotic"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def slut(self, ctx: commands.Context):
        """Use your charm and earn Beri in a Grand Line venue. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi = random.choice(SLUT_SCENARIOS)
        amount = random.randint(lo, hi)

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

        success = random.random() < 0.75
        if success:
            outcomes = [
                ("A passing pirate dropped some coins in your hat.", random.randint(25, 100)),
                ("A shipmate felt sorry for you and tossed you some Beri.", random.randint(40, 120)),
                ("You sang a sorrowful shanty and earned a few generous tips.", random.randint(30, 110)),
            ]
            message, amount = random.choice(outcomes)
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

    @commands.command(name="rob", aliases=["steal"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, target: discord.Member):
        """Attempt to rob another user. (1 hour cooldown)"""
        name, icon = await self._currency_fmt(ctx.guild)

        if target == ctx.author:
            return await ctx.send("❌ You can't rob yourself.")
        if target.bot:
            return await ctx.send("❌ Bots don't carry Beri.")

        victim_bal = await self._get_balance(ctx.guild, target)
        robber_bal = await self._get_balance(ctx.guild, ctx.author)

        if victim_bal < 100:
            return await ctx.send(f"❌ {target.mention} doesn't have enough to be worth robbing.")

        ratio = min(robber_bal / max(victim_bal, 1), 2.0)
        success_rate = max(0.25, min(0.65, 0.40 + (ratio - 1) * 0.15))
        won = random.random() < success_rate

        if won:
            stolen = max(50, random.randint(int(victim_bal * 0.05), int(victim_bal * 0.25)))
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

    @work.error
    @crime.error
    @hack.error
    @slut.error
    @rob.error
    async def _activity_cooldown_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            m, s = divmod(int(error.retry_after), 60)
            h, m = divmod(m, 60)
            time_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
            await ctx.send(f"⏳ You're on cooldown! Try again in **{time_str}**.")
        else:
            raise error
