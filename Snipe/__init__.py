from .snipe import Snipe

async def setup(bot):
    cog = Snipe(bot)
    await bot.add_cog(cog)

