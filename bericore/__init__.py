from .bericore import BeriCore


async def setup(bot):
    cog = BeriCore(bot)
    await bot.add_cog(cog)
