from .grill import Grilled

async def setup(bot):
    """Load the Grilled cog."""
    await bot.add_cog(Grilled(bot))
