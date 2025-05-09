from .v2poll import V2Poll

async def setup(bot):
    await bot.add_cog(V2Poll(bot))
