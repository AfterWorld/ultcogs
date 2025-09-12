from .suggestion import EnhancedSuggestions

async def setup(bot):
    await bot.add_cog(EnhancedSuggestions(bot))
