from .mrwhite import MrWhite

async def setup(bot):
    await bot.add_cog(MrWhite(bot))
