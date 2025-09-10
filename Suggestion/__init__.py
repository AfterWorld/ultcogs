from redbot.core.bot import Red
from .suggestion import Suggestion

async def setup(bot: Red):
    await bot.add_cog(Suggestion(bot))
