from .spriteannouncer import SpriteAnnouncer


async def setup(bot):
    """Set up the SpriteAnnouncer cog."""
    cog = SpriteAnnouncer(bot)
    await bot.add_cog(cog)
    # Note: Initialization is now handled by the cog's background task
