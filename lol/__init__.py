from .lol import LeagueOfLegends

async def setup(bot):
    await bot.add_cog(LeagueOfLegends(bot))
