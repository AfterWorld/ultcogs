from .onepiecefun import OnePieceFun

async def setup(bot):
    await bot.add_cog(OnePieceFun(bot))
