"""Pokemon cog for Red-DiscordBot."""
import random
from redbot.core.bot import Red

from .pokemoncog import PokemonCog

__red_end_user_data_statement__ = (
    "This cog stores data about users' Pokémon collections, including which Pokémon "
    "they have caught, their levels, and other related data. It also tracks items "
    "and currency for the Pokémon economy system. This data can be removed with a "
    "data deletion request."
)

async def setup(bot: Red) -> None:
    """Load the PokemonCog."""
    cog = PokemonCog(bot)
    await bot.add_cog(cog)