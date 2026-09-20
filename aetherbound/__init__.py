from .aetherbound import Aetherbound


async def setup(bot):
    await bot.add_cog(Aetherbound(bot))
