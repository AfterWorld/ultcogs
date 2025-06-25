from .advancedreport import AdvancedReport

async def setup(bot):
    """Entry point for loading the cog"""
    cog = AdvancedReport(bot)
    await bot.add_cog(cog)
