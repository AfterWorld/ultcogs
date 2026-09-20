import logging

from .aetherbound import Aetherbound


def configure_aliases(bot, cog):
    available = []
    for alias in ("ae", "a"):
        if bot.get_command(alias) is None:
            available.append(alias)
        else:
            logging.getLogger("red.aetherbound").warning(
                "Aetherbound alias %s is owned by another command; keeping it unchanged.", alias
            )
    cog.adventure.aliases = available


async def setup(bot):
    cog = Aetherbound(bot)
    configure_aliases(bot, cog)
    await bot.add_cog(cog)
