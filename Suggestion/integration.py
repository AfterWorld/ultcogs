from redbot.core import bank

class RewardSystem:
    def __init__(self, cog):
        self.cog = cog

    async def award(self, guild, user_id: int, amount: int, suggestion_id: int):
        use_beri = await self.cog.config.guild(guild).use_beri_core()
        user = guild.get_member(user_id)
        if not user:
            return

        if use_beri and hasattr(self.cog.bot, "get_cog"):
            beri = self.cog.bot.get_cog("BeriCore")
            if beri:
                await beri.add_beri(user, amount, reason=f"suggestion:{suggestion_id}", actor=None)
                return
