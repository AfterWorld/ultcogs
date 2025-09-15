from .strawhat_sphinx_queue import StrawhatSphinxQueue

async def setup(bot):
    await bot.add_cog(StrawhatSphinxQueue(bot))