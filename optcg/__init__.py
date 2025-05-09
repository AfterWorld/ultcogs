from .optcg import OPTCG

async def setup(bot):
    await bot.add_cog(OPTCG(bot))
