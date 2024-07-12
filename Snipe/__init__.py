from .snipe import SnipeCog

async def setup(bot: Red):
    bot.add_cog(SnipeCog(bot))
