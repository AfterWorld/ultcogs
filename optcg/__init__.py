from .optcg import OPTCG

async def setup(bot):
    cog = OPTCG(bot)
    await bot.add_cog(cog)
