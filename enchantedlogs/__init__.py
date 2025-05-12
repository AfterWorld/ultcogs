from .enhancedlogs import EnhancedModlog

async def setup(bot):
    await bot.add_cog(EnhancedModlog(bot))
