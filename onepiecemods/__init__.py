# __init__.py
from .onepiecemods import OnePieceMods

async def setup(bot):
    await bot.add_cog(OnePieceMods(bot))
