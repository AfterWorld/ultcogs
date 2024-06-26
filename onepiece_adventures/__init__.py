from .main import OnePieceAdventures

async def setup(bot):
    await bot.add_cog(OnePieceAdventures(bot))