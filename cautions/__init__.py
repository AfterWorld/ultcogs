async def setup(bot):
    """Load the Cautions cog."""
    await bot.add_cog(Cautions(bot))
