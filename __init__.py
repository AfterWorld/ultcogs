from .beri_cautions import BeriCautions

async def setup(bot):
    await bot.add_cog(BeriCautions(bot))
