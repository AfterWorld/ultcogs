from .geoguessr import GeoGuessr


async def setup(bot):
    await bot.add_cog(GeoGuessr(bot))