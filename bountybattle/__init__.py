from redbot.core.bot import Red
from .bountybattle import OnePieceRPG  # Ensure this matches the class name in bountybattle.py

async def setup(bot: Red):
    """Load the OnePieceRPG cog."""
    cog = OnePieceRPG(bot)  # Instantiate the correct class
    await bot.add_cog(cog)
