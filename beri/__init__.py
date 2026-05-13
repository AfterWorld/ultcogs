from .beri import Beri


async def setup(bot):
    await bot.add_cog(Beri(bot))
