from .deathbattle import DeathBattle

__red_end_user_data_statement__ = (
    "This cog stores user IDs, battle statistics, and currency data."
)

async def setup(bot):
    """Load the DeathBattle cog."""
    cog = DeathBattle(bot)
    await bot.add_cog(cog)