from .cautions import Cautions

async def setup(bot):
    await bot.add_cog(Cautions(bot))
