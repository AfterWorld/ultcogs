from .ultprivates import UltPrivates

async def setup(bot):
    await bot.add_cog(UltPrivates(bot))
