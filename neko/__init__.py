from .nekosinteract import NekoInteractions

__red_end_user_data_statement__ = (
    "This cog stores interaction statistics including the number of times users have "
    "performed specific interactions (hug, kiss, slap, etc.) with other users. "
    "This data includes user IDs, interaction counts, and favorite actions. "
    "No personal information beyond Discord user IDs is collected or stored."
)

async def setup(bot):
    """Load the NekoInteractions cog"""
    cog = NekoInteractions(bot)
    await bot.add_cog(cog)
