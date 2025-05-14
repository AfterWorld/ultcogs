from .consecutivefilter import ConsecutiveFilter

async def setup(bot):
    cog = ConsecutiveFilter(bot)
    await cog.initialize()
    await bot.add_cog(cog)
