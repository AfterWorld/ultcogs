from .onepieceafk import OnePieceAFK

async def setup(bot):
    await bot.add_cog(OnePieceAFK(bot))