from redbot.core.bot import Red  # isort:skip
from redbot.core.utils import get_end_user_data_statement

from .opcsupporters import OPCServerSupporters

# Credits:
# This cog is based on the original ServerSupporters cog by AAA3A
# Original repository: https://github.com/AAA3A-AAA3A/AAA3A-cogs
# Many thanks to AAA3A for the inspiration and original implementation
# Modified to remove AAA3A_utils dependency while maintaining functionality

__red_end_user_data_statement__ = get_end_user_data_statement(file=__file__)


async def setup(bot: Red) -> None:
    """
    Setup function for the OPC Server Supporters cog.
    Based on AAA3A's original setup methodology.
    """
    cog = OPCServerSupporters(bot)
    await bot.add_cog(cog)