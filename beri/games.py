"""
Games mixin for the Beri economy cog — coinflip and slots.
Balance ops go through BeriCoreBridge -> BeriCore API.
"""

import random
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎", "💀"]
SLOT_PAYOUTS = {
    ("💀", 3): 0,
    ("🍒", 2): 1.5, ("🍋", 2): 1.5, ("🍊", 2): 1.5,
    ("🍇", 2): 2.0, ("⭐", 2): 2.5, ("💎", 2): 3.0,
    ("🍒", 3): 3.0, ("🍋", 3): 3.5, ("🍊", 3): 4.0,
    ("🍇", 3): 5.0, ("⭐", 3): 7.0, ("💎", 3): 10.0,
}
BET_MIN = 10
BET_MAX = 50_000


class Games(commands.Cog):
    """
    Gambling games mixin. Expects parent to expose:
      - self._get_balance(guild, member)
      - self._safe_modify(ctx, guild, member, delta, reason=, actor=, bypass_cap=, metadata=)
      - self._currency_fmt(guild)
    """

    @commands.command(name="coinflip", aliases=["flip", "cf"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def coinflip(self, ctx: commands.Context, bet: int, choice: str = "heads"):
        """Flip a coin. Win 2x or lose your bet. Usage: `[p]coinflip <amount> [heads|tails]`"""
        name, icon = await self._currency_fmt(ctx.guild)
        choice = choice.lower()
        if choice not in ("heads", "tails", "h", "t"):
            return await ctx.send("❌ Choose `heads` or `tails`.")
        choice_norm = "heads" if choice in ("heads", "h") else "tails"

        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be {humanize_number(BET_MIN)}–{humanize_number(BET_MAX)} {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        result = random.choice(["heads", "tails"])
        won = result == choice_norm
        delta = bet if won else -bet

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, delta,
            reason=f"game:coinflip:{'win' if won else 'loss'}",
            actor=ctx.author, bypass_cap=won,
            metadata={"bet": bet, "choice": choice_norm, "result": result},
        )
        if new_bal is None:
            return

        coin_emoji = "🪙" if result == "heads" else "🌑"
        embed = discord.Embed(title=f"{coin_emoji} Coin Flip — {'**WIN!** 🎉' if won else '**LOSS** 💸'}", color=discord.Color.green() if won else discord.Color.red())
        embed.add_field(name="Your Pick", value=choice_norm.capitalize(), inline=True)
        embed.add_field(name="Result", value=result.capitalize(), inline=True)
        embed.add_field(name="Payout", value=f"{'+' if won else ''}{humanize_number(delta)} {icon}", inline=True)
        embed.add_field(name="New Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    @commands.command(name="slots", aliases=["slot"])
    @commands.guild_only()
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def slots(self, ctx: commands.Context, bet: int):
        """Spin the slot machine! Usage: `[p]slots <amount>`"""
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be {humanize_number(BET_MIN)}–{humanize_number(BET_MAX)} {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        weights = [20, 20, 20, 15, 10, 5, 10]
        reels = random.choices(SLOT_SYMBOLS, weights=weights, k=3)
        multiplier, label = self._evaluate_slots(reels)
        delta = int(bet * multiplier) - bet

        new_bal = await self._safe_modify(
            ctx, ctx.guild, ctx.author, delta,
            reason=f"game:slots:{'win' if delta >= 0 else 'loss'}",
            actor=ctx.author, bypass_cap=(delta > 0),
            metadata={"bet": bet, "reels": reels, "multiplier": multiplier},
        )
        if new_bal is None:
            return

        won = delta > 0
        jackpot = multiplier >= 10
        color = discord.Color.gold() if jackpot else (discord.Color.green() if won else discord.Color.red())
        title = "🎰 JACKPOT!! 🎰" if jackpot else ("🎰 You Win!" if won else "🎰 No Luck")

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Reels", value=f"[ {' | '.join(reels)} ]", inline=False)
        if label:
            embed.add_field(name="Combo", value=label, inline=True)
        embed.add_field(name="Multiplier", value=f"x{multiplier}", inline=True)
        embed.add_field(name="Payout", value=f"{'+' if delta >= 0 else ''}{humanize_number(delta)} {icon}", inline=True)
        embed.add_field(name="New Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    def _evaluate_slots(self, reels):
        if reels.count("💀") >= 2:
            return 0, "💀 Cursed Reels — lose it all!"
        for sym in set(reels):
            count = reels.count(sym)
            key = (sym, count)
            if key in SLOT_PAYOUTS:
                return SLOT_PAYOUTS[key], f"{sym} x{count}"
        return 0.5, "No match — half your bet back"

    @commands.command(name="paytable")
    @commands.guild_only()
    async def paytable(self, ctx: commands.Context):
        """Show the slots paytable and game rules."""
        name, icon = await self._currency_fmt(ctx.guild)
        lines = [
            f"**Bet range:** {humanize_number(BET_MIN)} – {humanize_number(BET_MAX)} {icon}",
            "", "**🎰 Slots Paytable**", "```",
            f"{'Combo':<20} {'Multiplier':>10}", "-" * 32,
        ]
        for (sym, count), mult in sorted(SLOT_PAYOUTS.items(), key=lambda x: x[1]):
            lines.append(f"{sym} × {count:<17} {'x' + str(mult):>10}")
        lines += ["```", "", "**🪙 Coinflip** — Pick heads or tails. Win = **2x**, Lose = **0x**."]
        embed = discord.Embed(title=f"{icon} {name} Games — Paytable", description="\n".join(lines), color=discord.Color.gold())
        await ctx.send(embed=embed)
