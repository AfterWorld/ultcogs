from .onepiece import OnePiece

async def setup(bot):
    await bot.add_cog(OnePiece(bot))
