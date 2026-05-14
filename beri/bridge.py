"""
Bridge mixin for the Beri cog.

Internal balance helpers used by commands and features.
"""

import discord
from redbot.core import Config


class BeriCoreBridge:
    """
    Mixin providing balance helpers for the Beri cog.

    Expects self.bot, self.config, and self.audit to exist on the parent class.
    The cache lives at config.guild(guild).lb_cache:
        {user_id_str: int}
    It is updated on every _modify_balance call so the leaderboard
    never needs to hit the API for bulk data.
    """

    # ── Local leaderboard cache ───────────────────────────────────────────

    async def _update_cache(self, guild: discord.Guild, user: discord.Member, balance: int):
        """Update the per-guild balance cache entry for a single user."""
        async with self.config.guild(guild).lb_cache() as cache:
            cache[str(user.id)] = balance

    async def _get_cache(self, guild: discord.Guild) -> dict:
        """Return the full {uid_str: balance} cache for this guild."""
        return await self.config.guild(guild).lb_cache()

    # ── Balance helpers ────────────────────────────────────────────────────

    async def _get_balance(self, guild: discord.Guild, user: discord.Member) -> int:
        """Fetch the user's balance from the public API."""
        return await self.get_beri(user)

    async def _set_balance(self, guild: discord.Guild, user: discord.Member, amount: int):
        """Set the user's balance via the public API and update local cache."""
        new_bal = await self.set_beri(user, max(0, amount), reason="beri:internal:set")
        await self._update_cache(guild, user, new_bal)

    async def _modify_balance(
        self,
        guild: discord.Guild,
        user: discord.Member,
        delta: int,
        *,
        reason: str,
        actor,
        bypass_cap: bool = False,
        metadata: dict = None,
    ) -> int:
        """
        Add/subtract from a user's balance via the public API.
        Returns the new balance and updates the local leaderboard cache.
        """
        new_bal = await self.add_beri(
            user,
            delta,
            reason=reason,
            actor=actor,
            bypass_cap=bypass_cap,
            metadata=metadata,
        )

        # Mirror into local cache for leaderboard
        await self._update_cache(guild, user, new_bal)

        # Fire our own audit log (keeps the audit-channel feed alive)
        await self.audit.log(
            guild=guild,
            target=user,
            actor=actor,
            delta=delta,
            new_balance=new_bal,
            reason=reason,
        )

        return new_bal

    # ── Transfer helper ───────────────────────────────────────────────────

    async def _transfer_balance(
        self,
        guild: discord.Guild,
        from_user: discord.Member,
        to_user: discord.Member,
        amount: int,
        *,
        reason: str,
        tax_rate: float = 0.0,
    ) -> tuple[bool, str]:
        """Transfer Beri between two users via the public API."""
        success, msg = await self.transfer_beri(
            from_user,
            to_user,
            amount,
            reason=reason,
            tax_rate=tax_rate,
        )
        if success:
            from_bal = await self.get_beri(from_user)
            to_bal = await self.get_beri(to_user)
            await self._update_cache(guild, from_user, from_bal)
            await self._update_cache(guild, to_user, to_bal)
        return success, msg

    # ── User stats passthrough ────────────────────────────────────────────

    async def _get_user_stats(self, user: discord.Member) -> dict:
        """Return user stats dict from the public API."""
        return await self.get_user_stats(user)

    # ── Error-safe wrapper used by commands ───────────────────────────────

    async def _safe_modify(
        self,
        ctx,
        guild: discord.Guild,
        user: discord.Member,
        delta: int,
        *,
        reason: str,
        actor,
        bypass_cap: bool = False,
        metadata: dict = None,
    ):
        """
        Wrapper around _modify_balance that sends a user-facing error
        if the balance operation fails, returning None on failure.
        """
        try:
            return await self._modify_balance(
                guild, user, delta,
                reason=reason,
                actor=actor,
                bypass_cap=bypass_cap,
                metadata=metadata,
            )
        except RuntimeError as e:
            await ctx.send(f"❌ {e}")
            return None
        except Exception as e:
            await ctx.send(f"❌ Economy error: {e}")
            return None
