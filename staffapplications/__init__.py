from .staffapplications import StaffApplications

__red_end_user_data_statement__ = (
    "Stores applicant/reviewer Discord IDs, answers, positions, timestamps, decisions, "
    "and message IDs in a local SQLite database. Submitted answers are posted in the "
    "configured review channel. Sanitized diagnostics are sent to bot owners and the "
    "configured error channel. Red data deletion is supported."
)


async def setup(bot):
    await bot.add_cog(StaffApplications(bot))
