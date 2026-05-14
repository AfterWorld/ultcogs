"""
BeriCore bridge for the Beri cog.

All balance reads/writes go through the BeriCore cog API.
A lightweight per-guild balance cache is maintained locally
so the leaderboard command works without a BeriCore bulk-fetch endpoint.
"""

import discord
from redbot.core import Config
from redbot.core.bot import Red


class BeriCoreBridge:
    """
    Mixin that replaces the old config-based balance helpers with
    BeriCore API calls.  Maintains a local guild leaderboard cache.

    Expects self.bot and self.config to exist on the parent class.
    The cache lives at config.guild(guild).lb_cache:
        {user_id_str: int}
    It is updated on every _modify_balance call so the leaderboard
    never needs to hit BeriCore for bulk data.
    """

    # ── BeriCore accessor ─────────────────────────────────────────────────

    def _core(self):
        """Return the BeriCore cog, or None if not loaded."""
        return self.bot.get_cog("BeriCore")

    def _require_core(self):
        """Return BeriCore or raise RuntimeError."""
        core = self._core()
        if core is None:
            raise RuntimeError(
                "BeriCore is not loaded. Ask an admin to load it first."
            )
        return core

    # ── Balance helpers (drop-in replacements) ────────────────────────────

    async def _get_balance(self, guild: discord.Guild, user: discord.Member) -> int:
        """Fetch the user's balance from BeriCore."""
        core = self._require_core()
        return await core.get_beri(user)

    async def _set_balance(self, guild: discord.Guild, user: discord.Member, amount: int):
        """Set the user's balance via BeriCore and update local cache."""
        core = self._require_core()
        new_bal = await core.set_beri(
            user,
            max(0, amount),
            reason="beri:internal:set",
        )
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
        Add/subtract from a user's balance via BeriCore.
        Returns the new balance and updates the local leaderboard cache.

        Purchases and admin actions should pass bypass_cap=True.
        """
        core = self._require_core()

        kwargs = dict(reason=reason)
        if actor and isinstance(actor, discord.Member):
            kwargs["actor"] = actor
        # Auto-bypass cap for admin/system reason prefixes
        if bypass_cap or reason.startswith(("admin:", "import:", "rollback:", "gift:", "event:")):
            kwargs["bypass_cap"] = True
        if metadata:
            kwargs["metadata"] = metadata

        new_bal = await core.add_beri(user, delta, **kwargs)

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
        """Transfer Beri between two users via BeriCore."""
        core = self._require_core()
        success, msg = await core.transfer_beri(
            from_user,
            to_user,
            amount,
            reason=reason,
            tax_rate=tax_rate,
        )
        if success:
            from_bal = await core.get_beri(from_user)
            to_bal = await core.get_beri(to_user)
            await self._update_cache(guild, from_user, from_bal)
            await self._update_cache(guild, to_user, to_bal)
        return success, msg

    # ── User stats passthrough ────────────────────────────────────────────

    async def _get_user_stats(self, user: discord.Member) -> dict:
        """Return BeriCore user stats dict."""
        core = self._require_core()
        return await core.get_user_stats(user)

    # ── Local leaderboard cache ───────────────────────────────────────────

    async def _update_cache(self, guild: discord.Guild, user: discord.Member, balance: int):
        """Update the per-guild balance cache entry for a single user."""
        async with self.config.guild(guild).lb_cache() as cache:
            cache[str(user.id)] = balance

    async def _get_cache(self, guild: discord.Guild) -> dict:
        """Return the full {uid_str: balance} cache for this guild."""
        return await self.config.guild(guild).lb_cache()

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
        if BeriCore is unavailable, returning None on failure.
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
