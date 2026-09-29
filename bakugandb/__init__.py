from .bakugandb import BakuganDB


async def setup(bot):
    await bot.add_cog(BakuganDB(bot))
