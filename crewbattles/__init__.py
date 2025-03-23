from .crew import CrewManagement

async def setup(bot):
    cog = CrewManagement(bot)
    await bot.add_cog(cog)
