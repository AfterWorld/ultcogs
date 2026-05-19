"""
currency.py — Unified currency adapter for OnePieceFruit.

Priority chain (first available wins):
  1. BeriCore  (add_beri / get_beri)
  2. BeriCog   (wraps BeriCore itself, exposes _get_balance / _modify_balance)
  3. Red bank  (built-in bank module — fallback)

Import and use CurrencyAdapter everywhere instead of the scattered
_bericog() / _bericore() / bank.* calls spread across core.py.

Usage
-----
    adapter = CurrencyAdapter(bot, guild)
    name    = await adapter.currency_name()
    bal     = await adapter.get_balance(member)
    new_bal = await adapter.withdraw(member, amount, reason="devilfruit:reroll", actor=ctx.author)
    new_bal = await adapter.deposit(member, amount, reason="devilfruit:perk",   actor=ctx.author)
"""

from __future__ import annotations

import discord
from redbot.core import bank
from redbot.core.bot import Red


class InsufficientFunds(ValueError):
    """Raised when a member doesn't have enough currency to cover a withdrawal."""


class CurrencyAdapter:
    """
    Thin adapter that routes balance operations to whichever economy
    cog / module is currently loaded, in priority order.

    Parameters
    ----------
    bot:
        The Red bot instance.
    guild:
        The guild the transaction belongs to. Required for BeriCog calls;
        not used by BeriCore or bank directly but kept for a uniform interface.
    """

    def __init__(self, bot: Red, guild: discord.Guild) -> None:
        self._bot = bot
        self._guild = guild

    # ------------------------------------------------------------------
    # Internal cog resolution
    # ------------------------------------------------------------------

    def _bericore(self):
        return self._bot.get_cog("BeriCore")

    def _bericog(self):
        return self._bot.get_cog("BeriCog")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def currency_name(self) -> str:
        """Return the display name of the currency (e.g. "Beri" or "Credits")."""
        core = self._bericore()
        if core is not None:
            return "Beri"

        beri = self._bericog()
        if beri is not None:
            name, _ = await beri._currency_fmt(self._guild)
            return name

        return await bank.get_currency_name(self._guild)

    async def get_balance(self, member: discord.Member) -> int:
        """Return the member's current balance."""
        core = self._bericore()
        if core is not None:
            return await core.get_beri(member)

        beri = self._bericog()
        if beri is not None:
            return await beri._get_balance(self._guild, member)

        return await bank.get_balance(member)

    async def withdraw(
        self,
        member: discord.Member,
        amount: int,
        *,
        reason: str = "devilfruit",
        actor: discord.Member | str = "System",
    ) -> int:
        """
        Deduct *amount* from *member*.  Returns the new balance.

        Raises
        ------
        InsufficientFunds
            If the member's balance is less than *amount*.
        """
        if amount <= 0:
            raise ValueError(f"Withdrawal amount must be positive, got {amount!r}")

        balance = await self.get_balance(member)
        if balance < amount:
            raise InsufficientFunds(
                f"{member.display_name} needs {amount:,} but only has {balance:,}"
            )

        core = self._bericore()
        if core is not None:
            return await core.add_beri(
                member, -amount, reason=reason, actor=actor
            )

        beri = self._bericog()
        if beri is not None:
            return await beri._modify_balance(
                self._guild, member, -amount, reason=reason, actor=actor
            )

        # Red bank: withdraw_credits returns the new balance only in newer
        # versions; in older versions it returns None.  Handle both.
        result = await bank.withdraw_credits(member, amount)
        return result if result is not None else await bank.get_balance(member)

    async def deposit(
        self,
        member: discord.Member,
        amount: int,
        *,
        reason: str = "devilfruit",
        actor: discord.Member | str = "System",
    ) -> int:
        """
        Add *amount* to *member*.  Returns the new balance.
        """
        if amount <= 0:
            raise ValueError(f"Deposit amount must be positive, got {amount!r}")

        core = self._bericore()
        if core is not None:
            return await core.add_beri(
                member, amount, reason=reason, actor=actor
            )

        beri = self._bericog()
        if beri is not None:
            return await beri._modify_balance(
                self._guild, member, amount, reason=reason, actor=actor
            )

        result = await bank.deposit_credits(member, amount)
        return result if result is not None else await bank.get_balance(member)
