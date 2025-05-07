from redbot.core.bot import Red
from .schedule1recipes import Schedule1Recipes

async def setup(bot: Red):
    await bot.add_cog(Schedule1Recipes(bot))
