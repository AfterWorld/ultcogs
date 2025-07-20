from .tiktok import TikTokLive

__red_end_user_data_statement__ = (
    "This cog stores TikTok usernames being monitored, notification channel preferences, "
    "mention role settings, and basic statistics about live stream notifications sent. "
    "It connects to TikTok's live streams in real-time using WebSocket connections through "
    "the TikTokLive library. No personal data from TikTok users is stored beyond usernames "
    "and notification counts. All data is stored locally in Red's configuration system."
)

async def setup(bot):
    """Load the TikTok Live cog"""
    cog = TikTokLive(bot)
    await bot.add_cog(cog)
