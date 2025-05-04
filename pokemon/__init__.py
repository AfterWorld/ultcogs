from .pokemon import PokemonCog

async def setup(bot):
    cog = PokemonCog(bot)
    await bot.add_cog(cog)
    
    # Start background task to check temporary forms
    bot.loop.create_task(cog.check_temporary_forms())
