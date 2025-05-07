from .onepiecemods import OnePieceMods

async def setup(bot):
    """Load the OnePieceMods cog."""
    cog = OnePieceMods(bot)
    
    # Start the background task when cog is loaded
    bot.loop.create_task(cog.init_task())
    
    await bot.add_cog(cog)
