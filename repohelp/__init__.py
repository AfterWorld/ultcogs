from .repohelp import RepoHelp

__red_end_user_data_statement__ = "This cog does not persistently store end-user data."


async def setup(bot):
    await bot.add_cog(RepoHelp(bot))
