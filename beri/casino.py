"""
Casino games for the Beri economy cog.

Games:
  - blackjack  — interactive vs dealer (hit/stand via reactions)
  - roulette   — bet on number, color, or column
  - dice       — hi/lo over/under 7 on 2d6
  - horses     — pick a horse, watch the race
  - videopoker — 5-card draw poker vs paytable
"""

import asyncio
import random
from typing import Optional

import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_number

BET_MIN = 10
BET_MAX = 50_000

# ── Card utilities ────────────────────────────────────────────────────────────

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def _new_deck() -> list[tuple[str, str]]:
    deck = [(r, s) for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def _card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)

def _hand_value(hand: list[tuple[str, str]]) -> int:
    total = sum(_card_value(r) for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def _fmt_hand(hand: list[tuple[str, str]]) -> str:
    return "  ".join(f"`{r}{s}`" for r, s in hand)


# ── Poker utilities ───────────────────────────────────────────────────────────

POKER_RANKS_ORDER = "23456789TJQKA"

def _poker_rank(hand: list[tuple[str, str]]) -> tuple[str, int]:
    """Return (hand name, multiplier) for a 5-card hand."""
    ranks = sorted([r if r != "10" else "T" for r, _ in hand],
                   key=lambda r: POKER_RANKS_ORDER.index(r), reverse=True)
    suits = [s for _, s in hand]
    counts = {r: ranks.count(r) for r in set(ranks)}
    freq = sorted(counts.values(), reverse=True)
    flush = len(set(suits)) == 1
    straight = (len(set(ranks)) == 5 and
                POKER_RANKS_ORDER.index(ranks[0]) - POKER_RANKS_ORDER.index(ranks[-1]) == 4)
    # Royal flush special case
    royal = straight and flush and ranks[0] == "A"

    if royal:               return "Royal Flush", 800
    if straight and flush:  return "Straight Flush", 50
    if freq[:2] == [4, 1]:  return "Four of a Kind", 25
    if freq[:2] == [3, 2]:  return "Full House", 9
    if flush:               return "Flush", 6
    if straight:            return "Straight", 4
    if freq[0] == 3:        return "Three of a Kind", 3
    if freq[:2] == [2, 2]:  return "Two Pair", 2
    if freq[0] == 2 and max(POKER_RANKS_ORDER.index(r) for r in counts if counts[r]==2) >= POKER_RANKS_ORDER.index("J"):
                            return "Jacks or Better", 1
    return "No Hand", 0


class Casino(commands.Cog):
    """
    Casino games mixin. Expects parent to expose:
      - self.config
      - self._get_balance(guild, member)
      - self._modify_balance(guild, member, delta, reason=, actor=)
      - self._currency_fmt(guild)
    """

    # ══════════════════════════════════════════════════════════════════════
    # Blackjack
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="blackjack", aliases=["bj", "21"])
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def blackjack(self, ctx: commands.Context, bet: int):
        """
        Play Blackjack against the dealer.

        Hit or stand using the reaction buttons. Blackjack pays 1.5x.
        """
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be between **{humanize_number(BET_MIN)}** and **{humanize_number(BET_MAX)}** {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        deck = _new_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]

        def make_embed(reveal_dealer=False, result_line="") -> discord.Embed:
            pval = _hand_value(player)
            dval = _hand_value(dealer)
            embed = discord.Embed(title="🃏 Blackjack", color=discord.Color.dark_green())
            embed.add_field(
                name=f"Your Hand ({pval})",
                value=_fmt_hand(player),
                inline=False,
            )
            if reveal_dealer:
                embed.add_field(name=f"Dealer's Hand ({dval})", value=_fmt_hand(dealer), inline=False)
            else:
                embed.add_field(
                    name="Dealer's Hand (?)",
                    value=f"`{dealer[0][0]}{dealer[0][1]}`  `??`",
                    inline=False,
                )
            if result_line:
                embed.add_field(name="Result", value=result_line, inline=False)
            embed.set_footer(text=f"Bet: {humanize_number(bet)} {icon} • React ✅ Hit  ❌ Stand")
            return embed

        msg = await ctx.send(embed=make_embed())
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        # ── Player turn ──────────────────────────────────────────────────
        busted = False
        stood = False

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ("✅", "❌")
                and reaction.message.id == msg.id
            )

        while not stood and not busted:
            try:
                reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=45.0, check=check)
            except asyncio.TimeoutError:
                stood = True
                break

            if str(reaction.emoji) == "✅":
                player.append(deck.pop())
                pval = _hand_value(player)
                if pval >= 21:
                    busted = pval > 21
                    stood = True
                else:
                    try:
                        await msg.remove_reaction("✅", ctx.author)
                    except Exception:
                        pass
                    await msg.edit(embed=make_embed())
            else:
                stood = True

        # ── Dealer turn ──────────────────────────────────────────────────
        pval = _hand_value(player)
        dval = _hand_value(dealer)

        if not busted:
            while dval < 17:
                dealer.append(deck.pop())
                dval = _hand_value(dealer)

        # ── Determine outcome ────────────────────────────────────────────
        blackjack_player = (len(player) == 2 and pval == 21)
        blackjack_dealer = (len(dealer) == 2 and dval == 21)

        if busted:
            delta = -bet
            result = f"💥 Bust! Lost **{humanize_number(bet)}** {icon}."
            color = discord.Color.red()
        elif blackjack_player and not blackjack_dealer:
            delta = int(bet * 1.5)
            result = f"🎉 Blackjack! Won **{humanize_number(delta)}** {icon}!"
            color = discord.Color.gold()
        elif blackjack_dealer and not blackjack_player:
            delta = -bet
            result = f"😬 Dealer Blackjack! Lost **{humanize_number(bet)}** {icon}."
            color = discord.Color.red()
        elif dval > 21 or pval > dval:
            delta = bet
            result = f"🏆 Win! Earned **{humanize_number(bet)}** {icon}."
            color = discord.Color.green()
        elif pval == dval:
            delta = 0
            result = "🤝 Push — bet returned."
            color = discord.Color.blurple()
        else:
            delta = -bet
            result = f"💸 Dealer wins! Lost **{humanize_number(bet)}** {icon}."
            color = discord.Color.red()

        new_bal = await self._modify_balance(
            ctx.guild, ctx.author, delta,
            reason=f"game:blackjack:{'win' if delta > 0 else 'push' if delta == 0 else 'loss'}",
            actor=ctx.author,
        )

        final_embed = make_embed(reveal_dealer=True, result_line=result)
        final_embed.color = color
        final_embed.set_footer(text=f"New Balance: {humanize_number(new_bal)} {icon}")
        await msg.clear_reactions()
        await msg.edit(embed=final_embed)

    # ══════════════════════════════════════════════════════════════════════
    # Roulette
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="roulette", aliases=["rl"])
    @commands.guild_only()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def roulette(self, ctx: commands.Context, bet: int, *, choice: str):
        """
        Spin the roulette wheel.

        **Choices:**
        • `red` / `black` — 2x payout
        • `odd` / `even` — 2x payout
        • `1-18` / `19-36` (low/high) — 2x payout
        • `1st12` / `2nd12` / `3rd12` — 3x payout
        • A number `0`–`36` — 36x payout
        """
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be between **{humanize_number(BET_MIN)}** and **{humanize_number(BET_MAX)}** {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        result = random.randint(0, 36)
        RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
        is_red = result in RED_NUMBERS
        is_black = result != 0 and not is_red
        result_color = "🔴 Red" if is_red else ("⚫ Black" if is_black else "🟢 Green")

        choice = choice.lower().strip()
        won = False
        multiplier = 0

        if choice.isdigit():
            n = int(choice)
            if 0 <= n <= 36:
                won = result == n
                multiplier = 36
            else:
                return await ctx.send("❌ Number must be 0–36.")
        elif choice in ("red", "r"):
            won = is_red; multiplier = 2
        elif choice in ("black", "b"):
            won = is_black; multiplier = 2
        elif choice in ("odd",):
            won = result != 0 and result % 2 == 1; multiplier = 2
        elif choice in ("even",):
            won = result != 0 and result % 2 == 0; multiplier = 2
        elif choice in ("low", "1-18"):
            won = 1 <= result <= 18; multiplier = 2
        elif choice in ("high", "19-36"):
            won = 19 <= result <= 36; multiplier = 2
        elif choice == "1st12":
            won = 1 <= result <= 12; multiplier = 3
        elif choice == "2nd12":
            won = 13 <= result <= 24; multiplier = 3
        elif choice == "3rd12":
            won = 25 <= result <= 36; multiplier = 3
        else:
            return await ctx.send("❌ Invalid roulette choice. Try `red`, `black`, `odd`, `even`, `low`, `high`, `1st12`, `2nd12`, `3rd12`, or a number 0–36.")

        delta = bet * (multiplier - 1) if won else -bet
        new_bal = await self._modify_balance(
            ctx.guild, ctx.author, delta,
            reason=f"game:roulette:{'win' if won else 'loss'}",
            actor=ctx.author,
        )

        color = discord.Color.green() if won else discord.Color.red()
        embed = discord.Embed(
            title=f"🎡 Roulette — {'WIN!' if won else 'LOSS'}",
            color=color,
        )
        embed.add_field(name="Result", value=f"**{result}** {result_color}", inline=True)
        embed.add_field(name="Your Bet", value=choice.upper(), inline=True)
        embed.add_field(
            name="Payout",
            value=f"{'+ ' if won else ''}{humanize_number(delta)} {icon}",
            inline=True,
        )
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Dice (hi/lo)
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="dice", aliases=["diceroll", "hilo"])
    @commands.guild_only()
    @commands.cooldown(1, 8, commands.BucketType.user)
    async def dice(self, ctx: commands.Context, bet: int, choice: str = "high"):
        """
        Roll 2d6. Guess high (8+), low (6-), or seven (exact 7).

        • `high` — 8 or more — 2x
        • `low`  — 6 or less — 2x
        • `seven` — exactly 7 — 4x (riskier!)
        """
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be between **{humanize_number(BET_MIN)}** and **{humanize_number(BET_MAX)}** {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        choice = choice.lower()
        if choice not in ("high", "h", "low", "l", "seven", "7"):
            return await ctx.send("❌ Choose `high`, `low`, or `seven`.")
        choice_norm = {"h": "high", "l": "low", "7": "seven"}.get(choice, choice)

        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        total = d1 + d2

        die_emojis = ["", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]

        if choice_norm == "high":
            won = total >= 8; multiplier = 2
        elif choice_norm == "low":
            won = total <= 6; multiplier = 2
        else:
            won = total == 7; multiplier = 4

        delta = bet * (multiplier - 1) if won else -bet
        new_bal = await self._modify_balance(
            ctx.guild, ctx.author, delta,
            reason=f"game:dice:{'win' if won else 'loss'}",
            actor=ctx.author,
        )

        embed = discord.Embed(
            title=f"🎲 Dice — {'WIN!' if won else 'LOSS'}",
            color=discord.Color.green() if won else discord.Color.red(),
        )
        embed.add_field(name="Roll", value=f"{die_emojis[d1]} {die_emojis[d2]} = **{total}**", inline=True)
        embed.add_field(name="Your Call", value=choice_norm.capitalize(), inline=True)
        embed.add_field(
            name="Payout",
            value=f"{'+ ' if won else ''}{humanize_number(delta)} {icon}",
            inline=True,
        )
        embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        embed.set_footer(text=ctx.author.display_name)
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Horse Racing
    # ══════════════════════════════════════════════════════════════════════

    HORSES = [
        ("🐎 Shanks' Pride", 0.30, 3.5),
        ("🦄 Luffy's Dream", 0.25, 4.5),
        ("🐴 Zoro's Nap", 0.20, 5.5),
        ("🏇 Nami's Greed", 0.15, 7.0),
        ("🐇 Robin's Secret", 0.10, 10.0),
    ]

    @commands.command(name="horses", aliases=["horse", "race"])
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def horses(self, ctx: commands.Context, bet: int, *, horse: str):
        """
        Bet on a horse race! Pick a horse by number or name.

        Use `[p]raceboard` to see the horses and odds.
        """
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be between **{humanize_number(BET_MIN)}** and **{humanize_number(BET_MAX)}** {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        # Resolve horse
        chosen = None
        if horse.isdigit():
            idx = int(horse) - 1
            if 0 <= idx < len(self.HORSES):
                chosen = self.HORSES[idx]
        else:
            horse_lower = horse.lower()
            for h in self.HORSES:
                if horse_lower in h[0].lower():
                    chosen = h
                    break

        if not chosen:
            listing = "\n".join(f"`{i+1}.` {h[0]} (odds: {h[2]}x)" for i, h in enumerate(self.HORSES))
            return await ctx.send(f"❌ Unknown horse. Options:\n{listing}")

        # Race!
        weights = [h[1] for h in self.HORSES]
        winner = random.choices(self.HORSES, weights=weights, k=1)[0]

        # Animated race
        embed = discord.Embed(title="🏟️ Race Starting...", color=discord.Color.yellow())
        positions = {h[0]: 0 for h in self.HORSES}
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1)

        for _ in range(3):
            for h in self.HORSES:
                positions[h[0]] += random.randint(1, 5)
            lines = []
            for h in self.HORSES:
                bar = "▓" * positions[h[0]] + "░" * (20 - positions[h[0]])
                lines.append(f"{h[0][:2]} `{bar}` 🏁")
            embed.description = "\n".join(lines)
            embed.title = "🏇 Racing..."
            await msg.edit(embed=embed)
            await asyncio.sleep(1.2)

        won = winner[0] == chosen[0]
        multiplier = chosen[2]
        delta = int(bet * multiplier) - bet if won else -bet

        new_bal = await self._modify_balance(
            ctx.guild, ctx.author, delta,
            reason=f"game:horses:{'win' if won else 'loss'}",
            actor=ctx.author,
        )

        result_embed = discord.Embed(
            title=f"🏆 {winner[0]} wins the race!",
            color=discord.Color.green() if won else discord.Color.red(),
        )
        result_embed.add_field(name="Your Pick", value=chosen[0], inline=True)
        result_embed.add_field(name="Winner", value=winner[0], inline=True)
        result_embed.add_field(
            name="Payout",
            value=f"{'+ ' if won else ''}{humanize_number(delta)} {icon}",
            inline=True,
        )
        result_embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        if won:
            result_embed.description = f"🎉 Your horse won at **{multiplier}x** odds!"
        else:
            result_embed.description = f"Better luck next time. Your horse didn't place."
        result_embed.set_footer(text=ctx.author.display_name)
        await msg.edit(embed=result_embed)

    @commands.command(name="raceboard")
    @commands.guild_only()
    async def raceboard(self, ctx: commands.Context):
        """Show the horse racing odds."""
        name, icon = await self._currency_fmt(ctx.guild)
        lines = [f"`{i+1}.` {h[0]} — **{h[2]}x** odds (~{int(h[1]*100)}% win rate)" for i, h in enumerate(self.HORSES)]
        embed = discord.Embed(
            title="🏇 Race Horses & Odds",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text=f"Use: {ctx.prefix}horses <bet> <horse number or name>")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════════════════════
    # Video Poker
    # ══════════════════════════════════════════════════════════════════════

    @commands.command(name="poker", aliases=["videopoker", "vp"])
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def videopoker(self, ctx: commands.Context, bet: int):
        """
        Play Jacks-or-Better Video Poker.

        React with 1️⃣–5️⃣ to HOLD those cards, then ✅ to draw.
        """
        name, icon = await self._currency_fmt(ctx.guild)
        if bet < BET_MIN or bet > BET_MAX:
            return await ctx.send(f"❌ Bet must be between **{humanize_number(BET_MIN)}** and **{humanize_number(BET_MAX)}** {icon}.")
        balance = await self._get_balance(ctx.guild, ctx.author)
        if bet > balance:
            return await ctx.send(f"❌ You only have **{humanize_number(balance)}** {icon}.")

        deck = _new_deck()
        hand = [deck.pop() for _ in range(5)]
        held = set()

        NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        ALL_REACTS = NUMBER_EMOJIS + ["✅"]

        def make_hand_embed(phase="hold") -> discord.Embed:
            cards = "  ".join(
                f"{'`' + c[0] + c[1] + '`'}{' 🔒' if i in held else ''}"
                for i, c in enumerate(hand)
            )
            embed = discord.Embed(
                title="🃏 Video Poker — Jacks or Better",
                color=discord.Color.dark_teal(),
            )
            embed.add_field(name="Your Hand", value=cards, inline=False)
            if phase == "hold":
                embed.add_field(
                    name="Instructions",
                    value="React 1️⃣–5️⃣ to hold a card, then ✅ to draw replacements.",
                    inline=False,
                )
            else:
                hand_name, mult = _poker_rank(hand)
                embed.add_field(name="Result", value=f"**{hand_name}** — {mult}x", inline=True)
            embed.set_footer(text=f"Bet: {humanize_number(bet)} {icon}")
            return embed

        msg = await ctx.send(embed=make_hand_embed())
        for emoji in ALL_REACTS:
            await msg.add_reaction(emoji)

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) in ALL_REACTS
                and reaction.message.id == msg.id
            )

        deadline = asyncio.get_event_loop().time() + 45
        confirmed = False
        while not confirmed and asyncio.get_event_loop().time() < deadline:
            try:
                remaining = max(1, deadline - asyncio.get_event_loop().time())
                reaction, _ = await ctx.bot.wait_for("reaction_add", timeout=remaining, check=check)
            except asyncio.TimeoutError:
                break

            emoji = str(reaction.emoji)
            if emoji == "✅":
                confirmed = True
            elif emoji in NUMBER_EMOJIS:
                idx = NUMBER_EMOJIS.index(emoji)
                if idx in held:
                    held.discard(idx)
                else:
                    held.add(idx)
                try:
                    await msg.remove_reaction(emoji, ctx.author)
                except Exception:
                    pass
                await msg.edit(embed=make_hand_embed())

        # Draw replacements
        for i in range(5):
            if i not in held:
                hand[i] = deck.pop()

        hand_name, multiplier = _poker_rank(hand)
        delta = int(bet * multiplier) - bet if multiplier > 0 else -bet
        new_bal = await self._modify_balance(
            ctx.guild, ctx.author, delta,
            reason=f"game:poker:{hand_name.lower().replace(' ', '_')}",
            actor=ctx.author,
        )

        final_embed = make_hand_embed(phase="result")
        final_embed.color = discord.Color.green() if delta >= 0 else discord.Color.red()
        final_embed.add_field(
            name="Payout",
            value=f"{'+ ' if delta >= 0 else ''}{humanize_number(delta)} {icon}",
            inline=True,
        )
        final_embed.add_field(name="Balance", value=f"{humanize_number(new_bal)} {icon}", inline=True)
        await msg.clear_reactions()
        await msg.edit(embed=final_embed)

    @commands.command(name="pokerpaytable", aliases=["pokerpay"])
    @commands.guild_only()
    async def pokerpaytable(self, ctx: commands.Context):
        """Show the video poker paytable."""
        name, icon = await self._currency_fmt(ctx.guild)
        hands = [
            ("Royal Flush", 800), ("Straight Flush", 50), ("Four of a Kind", 25),
            ("Full House", 9), ("Flush", 6), ("Straight", 4),
            ("Three of a Kind", 3), ("Two Pair", 2), ("Jacks or Better", 1),
        ]
        lines = ["```", f"{'Hand':<22} {'Payout':>8}", "-" * 32]
        for h, m in hands:
            lines.append(f"{h:<22} {'x' + str(m):>8}")
        lines.append("```")
        embed = discord.Embed(
            title=f"🃏 Video Poker Paytable",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Jacks or Better — 5-card draw")
        await ctx.send(embed=embed)

    # ── Error handlers ────────────────────────────────────────────────────
    @blackjack.error
    @roulette.error
    @dice.error
    @horses.error
    @videopoker.error
    async def _casino_cooldown_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            m, s = divmod(int(error.retry_after), 60)
            await ctx.send(f"⏳ Cooldown! Try again in **{m}m {s}s**.")
        else:
            raise error
