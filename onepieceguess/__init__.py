__red_end_user_data_statement__ = (
    "Stores per-server round settings and entry pools, plus Discord user IDs and win counts. "
    "User win data is removed when Red processes a data deletion request."
)


async def setup(bot):
    from .onepieceguess import OnePieceGuess

    await bot.add_cog(OnePieceGuess(bot))
