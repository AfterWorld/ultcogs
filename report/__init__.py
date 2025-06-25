# __init__.py
from .report import Report

async def setup(bot):
    """Setup function called by Red when loading the cog"""
    await bot.add_cog(Report(bot))
