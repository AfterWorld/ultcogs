"""
Fire Force game cog for Red-DiscordBot
"""

from .fireforce import FireForce

__red_end_user_data_statement__ = (
    "This cog stores user data including character information, "
    "battle statistics, and game progression data. "
    "This data can be removed through the Red bot's user data removal functions."
)

async def setup(bot):
    await bot.add_cog(FireForce(bot))
