from .snipe import SnipeCog

async def setup(bot):
    bot.add_cog(SnipeCog(bot))
