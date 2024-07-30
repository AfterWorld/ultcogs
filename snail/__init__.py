from .dendenmushi import DenDenMushi

async def setup(bot):
    await bot.add_cog(DenDenMushi(bot))
