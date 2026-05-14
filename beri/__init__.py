from .beri import Beri


async def setup(bot):
    cog = Beri(bot)
    cog.__cog_name__ = "BeriCore"
    await bot.add_cog(cog)
