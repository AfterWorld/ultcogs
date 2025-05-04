from redbot.core.bot import Red

from .core import BountyBattle


async def setup(bot: Red) -> None:
    """Load the BountyBattle cog."""
    await bot.add_cog(BountyBattle(bot))
