from redbot.core.bot import Red

from .pokemon import PokemonCog


async def setup(bot: Red) -> None:
    """Set up the Pokemon cog."""
    cog = PokemonCog(bot)
    await bot.add_cog(cog)
    
