from redbot.core import bank
import logging
import discord

log = logging.getLogger("red.suggestions.integration")

class RewardSystem:
    def __init__(self, cog):
        self.cog = cog

    async def award(self, guild: discord.Guild, user_id: int, amount: int):
        settings = await self.cog.config.guild(guild).all()
        use_beri = settings.get("use_beri_core", False)

        if not amount or amount <= 0:
            return

        member = guild.get_member(user_id)
        if not member:
            return

        try:
            if use_beri:
                # Assume beri_core.py exists and provides `award_currency`
                await self.cog.beri.award_currency(member, amount)
            else:
                await bank.deposit_credits(member, amount)
        except Exception as e:
            log.warning(f"Reward failed for user {user_id}: {e}")
