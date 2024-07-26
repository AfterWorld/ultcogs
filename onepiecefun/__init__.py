from .onepiecefun import OnePieceFun

async def setup(bot):
    cog = OnePieceFun(bot)
    await bot.add_cog(cog)
