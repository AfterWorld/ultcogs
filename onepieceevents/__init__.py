# onepiece_events/__init__.py
from .onepieceevents import OnePieceEvents

async def setup(bot):
    await bot.add_cog(OnePieceEvents(bot))
