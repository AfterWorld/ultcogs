from .ultimatenekos import UltimateNekoInteractions

__red_end_user_data_statement__ = (
    "This cog stores comprehensive interaction statistics including the number of times users have "
    "performed specific interactions (both regular and extreme) with other users. "
    "This data includes user IDs, interaction counts, favorite actions, API usage statistics, "
    "extreme interaction acknowledgments, and performance monitoring data. "
    "No personal information beyond Discord user IDs is collected or stored. "
    "The cog supports multiple APIs with fallback mechanisms and includes safety features "
    "for extreme content including warnings, role restrictions, and user blacklists."
)

async def setup(bot):
    """Load the UltimateNekoInteractions cog"""
    cog = UltimateNekoInteractions(bot)
    await bot.add_cog(cog)
