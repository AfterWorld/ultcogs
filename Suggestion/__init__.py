# Suggestion/__init__.py
from .suggestion import Suggestions

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
