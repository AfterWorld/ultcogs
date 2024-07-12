from .snipe import Snipe

async def setup(bot):
    bot.add_cog(Snipe(bot))
