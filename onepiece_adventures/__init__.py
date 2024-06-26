from .main import OnePieceAdventures
from .raid_boss_system import RaidBossSystem

async def setup(bot):
    cog = OnePieceAdventures(bot)
    cog.raid_boss_system = RaidBossSystem(bot, cog.config)
    await bot.add_cog(cog)