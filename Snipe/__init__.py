from .demon_slayer import DemonSlayer

async def setup(bot):
    await bot.add_cog(DemonSlayer(bot))