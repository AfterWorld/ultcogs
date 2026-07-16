from .voyage import Voyage


async def setup(bot):
    await bot.add_cog(Voyage(bot))
