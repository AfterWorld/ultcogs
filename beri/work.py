"""
DankMemer-style activity commands for the Beri cog.
All balance ops call BeriCore directly via self._core().
"""

import random
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

WORK_JOBS = [
    ("🍕 Pizza Delivery",          150, 400),
    ("🔧 Mechanic",                200, 500),
    ("🎸 Street Musician",          50, 300),
    ("⚓ Ship Deckhand",           250, 600),
    ("🏴‍☠️ Bounty Hunter",          300, 700),
    ("🐟 Fisherman",               100, 350),
    ("🗡️ Mercenary",               400, 800),
    ("🍜 Ramen Chef",              150, 450),
    ("📦 Warehouse Worker",        100, 300),
    ("🗺️ Navigator",               250, 550),
    ("⚔️ Swordsmith Apprentice",   200, 600),
    ("🌺 Flower Shop Assistant",    80, 250),
]

WORK_SUCCESS = [
    "You clocked in and busted your ass. Earned {amount} {icon}.",
    "Solid shift. The foreman handed you {amount} {icon}.",
    "Long day, but worth it — {amount} {icon} in your pocket.",
    "Finished the job without complaining. You pocketed {amount} {icon}.",
    "Customer left a fat tip. Total: {amount} {icon}.",
]

CRIME_SCENARIOS = [
    ("🎭 Con Artist",                  300,  900, 0.55),
    ("🏦 Bank Heist",                  500, 2000, 0.35),
    ("🎰 Rigged Card Game",            200,  800, 0.50),
    ("🚢 Smuggling Contraband",        600, 1500, 0.40),
    ("🎪 Festival Pickpocket",         100,  500, 0.65),
    ("💣 Explosive Distraction Robbery", 800, 2500, 0.30),
    ("🌃 Night Market Scam",           150,  700, 0.60),
]

CRIME_SUCCESS = [
    "Pulled it off without a hitch. Scored {amount} {icon}.",
    "Daring move. It worked — you walk away with {amount} {icon}.",
    "Chaos everywhere, you slipped out with {amount} {icon}.",
]
CRIME_FAIL = [
    "The marines were waiting. You got away but lost {fine} {icon} in fines.",
    "Someone ratted you out. Paid {fine} {icon} to avoid jail.",
    "Got caught red-handed and fined {fine} {icon}.",
]

HACK_TARGETS = [
    ("💻 Marine Database",          400, 1200, 0.50),
    ("🏦 World Government Treasury", 1000, 3000, 0.25),
    ("📡 Enies Lobby Comms",        300,  900, 0.55),
    ("🛒 Black Market Server",      200,  700, 0.60),
    ("📱 Celestial Dragon Phone",   500, 1500, 0.40),
]

HACK_SUCCESS = [
    "You breached their firewall. Transferred {amount} {icon} before they noticed.",
    "Root access granted. Quietly drained {amount} {icon}.",
    "Flawless intrusion — {amount} {icon} wire-transferred to your wallet.",
]
HACK_FAIL = [
    "They traced your IP. Lost {fine} {icon} covering your tracks.",
    "Honeypot detected! Locked out and fined {fine} {icon}.",
    "Intrusion detected — {fine} {icon} seized by authorities.",
]

SLUT_SCENARIOS = [
    ("💃 Cabaret Performance",  200, 800),
    ("🎤 Suggestive Karaoke",   100, 500),
    ("🃏 Strip Poker Host",     300, 900),
    ("🌹 Companion for Hire",   150, 700),
    ("🎭 Risqué Theater Act",   200, 600),
]
SLUT_SUCCESS = [
    "The crowd went wild. You collected {amount} {icon} in tips.",
    "Sold out the venue. Walked away with {amount} {icon}.",
    "Five-star reviews and {amount} {icon} richer.",
]


class Work(commands.Cog):
    """Activity commands mixin. Inherits _core() and _currency_fmt() from Beri parent."""

    @commands.command(name="work")
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Work a job and earn Beri. (1 hour cooldown)"""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi = random.choice(WORK_JOBS)
        amount = random.randint(lo, hi)

        new_bal = await core.add_beri(
            ctx.author,
            amount,
            reason="activity:work",
            metadata={"job": job_name},
        )

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
        """Attempt a criminal act. High risk, high reward. (2 hour cooldown)"""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi, success_rate = random.choice(CRIME_SCENARIOS)
        won = random.random() < success_rate

        if won:
            amount = random.randint(lo, hi)
            new_bal = await core.add_beri(
                ctx.author,
                amount,
                reason="activity:crime:success",
                metadata={"crime": job_name, "outcome": "success"},
            )
            msg = random.choice(CRIME_SUCCESS).format(amount=humanize_number(amount), icon=icon)
            embed = discord.Embed(
                title=f"🦹 {job_name} — SUCCESS", description=msg, color=discord.Color.green()
            )
            embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        else:
            balance = await core.get_beri(ctx.author)
            fine = min(random.randint(lo // 3, hi // 3), balance)
            new_bal = await core.add_beri(
                ctx.author,
                -fine,
                reason="activity:crime:caught",
                metadata={"crime": job_name, "outcome": "caught"},
            )
            msg = random.choice(CRIME_FAIL).format(fine=humanize_number(fine), icon=icon)
            embed = discord.Embed(
                title=f"🦹 {job_name} — CAUGHT", description=msg, color=discord.Color.red()
            )
            embed.add_field(name="Fine", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next crime in 2 hours")
        await ctx.send(embed=embed)

    @commands.command(name="hack")
    @commands.guild_only()
    @commands.cooldown(1, 5400, commands.BucketType.user)
    async def hack(self, ctx: commands.Context, target: Optional[discord.Member] = None):
        """Hack a system (or another user) for Beri. (90 min cooldown)"""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)

        if target and target != ctx.author and not target.bot:
            victim_bal = await core.get_beri(target)
            if victim_bal < 50:
                return await ctx.send(f"❌ {target.mention} is too broke to hack.")

            won = random.random() < 0.45
            if won:
                amount = random.randint(50, min(500, victim_bal // 4))
                await core.add_beri(
                    target, -amount,
                    reason=f"hack:victim:{ctx.author.id}",
                    actor=ctx.author,
                )
                new_bal = await core.add_beri(
                    ctx.author, amount,
                    reason=f"hack:attacker:{target.id}",
                    metadata={"victim_id": target.id},
                )
                embed = discord.Embed(
                    title="💻 Hack — SUCCESS",
                    description=f"You cracked {target.mention}'s wallet and siphoned **{humanize_number(amount)}** {icon}.",
                    color=discord.Color.green(),
                )
                embed.add_field(name="Stolen", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
            else:
                balance = await core.get_beri(ctx.author)
                fine = min(random.randint(50, 300), balance)
                new_bal = await core.add_beri(
                    ctx.author, -fine,
                    reason="hack:fail",
                )
                embed = discord.Embed(
                    title="💻 Hack — TRACED",
                    description=f"{target.mention}'s firewall fought back. You lost **{humanize_number(fine)}** {icon}.",
                    color=discord.Color.red(),
                )
                embed.add_field(name="Lost", value=f"**-{humanize_number(fine)}** {icon}", inline=True)
        else:
            sys_name, lo, hi, success_rate = random.choice(HACK_TARGETS)
            won = random.random() < success_rate
            if won:
                amount = random.randint(lo, hi)
                new_bal = await core.add_beri(
                    ctx.author, amount,
                    reason="activity:hack:success",
                    metadata={"target": sys_name},
                )
                msg = random.choice(HACK_SUCCESS).format(amount=humanize_number(amount), icon=icon)
                embed = discord.Embed(
                    title=f"💻 {sys_name} — BREACHED", description=msg, color=discord.Color.green()
                )
                embed.add_field(name="Stolen", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
            else:
                balance = await core.get_beri(ctx.author)
                fine = min(random.randint(lo // 4, hi // 4), balance)
                new_bal = await core.add_beri(
                    ctx.author, -fine,
                    reason="activity:hack:fail",
                )
                msg = random.choice(HACK_FAIL).format(fine=humanize_number(fine), icon=icon)
                embed = discord.Embed(
                    title=f"💻 {sys_name} — TRACED", description=msg, color=discord.Color.red()
                )
                embed.add_field(name="Fine", value=f"**-{humanize_number(fine)}** {icon}", inline=True)

        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next hack in 90 min")
        await ctx.send(embed=embed)

    @commands.command(name="slut", aliases=["sexy", "exotic"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def slut(self, ctx: commands.Context):
        """Use your... assets to earn Beri. (1 hour cooldown)"""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)
        job_name, lo, hi = random.choice(SLUT_SCENARIOS)
        amount = random.randint(lo, hi)

        new_bal = await core.add_beri(
            ctx.author, amount,
            reason="activity:slut",
        )

        msg = random.choice(SLUT_SUCCESS).format(amount=humanize_number(amount), icon=icon)
        embed = discord.Embed(title=f"💋 {job_name}", description=msg, color=discord.Color.magenta())
        embed.add_field(name="Earned", value=f"**+{humanize_number(amount)}** {icon}", inline=True)
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=f"{ctx.author.display_name} • Next in 1 hour")
        await ctx.send(embed=embed)

    @commands.command(name="rob", aliases=["steal"])
    @commands.guild_only()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def rob(self, ctx: commands.Context, target: discord.Member):
        """Attempt to rob another user. (1 hour cooldown)"""
        core = self._core()
        if not core:
            return await ctx.send("❌ BeriCore is not loaded.")

        name, icon = await self._currency_fmt(ctx.guild)

        if target == ctx.author:
            return await ctx.send("❌ You can't rob yourself.")
        if target.bot:
            return await ctx.send("❌ Bots don't carry Beri.")

        victim_bal = await core.get_beri(target)
        robber_bal = await core.get_beri(ctx.author)

        if victim_bal < 100:
            return await ctx.send(
                f"❌ {target.mention} doesn't have enough to be worth robbing."
            )

        ratio = min(robber_bal / max(victim_bal, 1), 2.0)
        success_rate = max(0.25, min(0.65, 0.40 + (ratio - 1) * 0.15))
        won = random.random() < success_rate

        if won:
            stolen = max(50, random.randint(int(victim_bal * 0.05), int(victim_bal * 0.25)))
            await core.add_beri(
                target, -stolen,
                reason=f"rob:victim:{ctx.author.id}",
                actor=ctx.author,
            )
            new_bal = await core.add_beri(
                ctx.author, stolen,
                reason=f"rob:success:{target.id}",
                metadata={"victim_id": target.id, "amount": stolen},
            )
            embed = discord.Embed(
                title="🔫 Robbery — SUCCESS",
                description=f"You cornered {target.mention} and made off with **{humanize_number(stolen)}** {icon}!",
                color=discord.Color.green(),
            )
            embed.add_field(name="Stolen", value=f"**+{humanize_number(stolen)}** {icon}", inline=True)
        else:
            fine = max(50, min(random.randint(int(robber_bal * 0.10), int(robber_bal * 0.30)), robber_bal))
            victim_share = fine // 2
            await core.add_beri(
                target, victim_share,
                reason=f"rob:damages:{ctx.author.id}",
            )
            new_bal = await core.add_beri(
                ctx.author, -fine,
                reason=f"rob:fail:{target.id}",
            )
            embed = discord.Embed(
                title="🔫 Robbery — BUSTED",
                description=(
                    f"{target.mention} fought back! You were fined **{humanize_number(fine)}** {icon}.\n"
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
