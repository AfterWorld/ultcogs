from .enhancedgacha import EnhancedGacha

async def setup(bot):
    await bot.add_cog(EnhancedGacha(bot))