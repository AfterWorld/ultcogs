from .spriteannouncer import SpriteAnnouncer

async def setup(bot):
    cog = SpriteAnnouncer(bot)
    await cog.initialize()
    await bot.add_cog(cog)
