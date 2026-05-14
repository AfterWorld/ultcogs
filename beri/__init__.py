from .beri import Beri


async def setup(bot):
    cog = Beri(bot)
    await bot.add_cog(cog)
