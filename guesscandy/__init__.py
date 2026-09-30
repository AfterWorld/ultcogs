from .guesscandy import GuessCandy


async def setup(bot):
    await bot.add_cog(GuessCandy(bot))
