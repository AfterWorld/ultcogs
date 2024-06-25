from .opafk import OPAFK

__red_end_user_data_statement__ = "This cog stores user data including adventure status, bounties, crews, abilities, inventory, and game progress. All data can be removed upon user request."

async def setup(bot):
    await bot.add_cog(OPAFK(bot))
