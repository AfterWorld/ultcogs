import discord

# ---------- Colors ----------
EMBED_COLOR_PENDING = discord.Color.blurple()
EMBED_COLOR_APPROVED = discord.Color.green()
EMBED_COLOR_DENIED = discord.Color.red()

# ---------- Config Defaults ----------
DEFAULT_THRESHOLD = 5
DEFAULT_MAX_LENGTH = 2000
DEFAULT_MIN_LENGTH = 10
DEFAULT_COOLDOWN = 300  # 5 minutes
MAX_SUGGESTION_LENGTH = 4000
MIN_SUGGESTION_LENGTH = 5

DEFAULT_GUILD_CONFIG = {
    "suggestion_channel": None,
    "staff_channel": None,
    "log_channel": None,
    "upvote_threshold": DEFAULT_THRESHOLD,
    "suggestion_count": 0,
    "suggestions": {},
    "cleanup": True,
    "max_length": DEFAULT_MAX_LENGTH,
    "min_length": DEFAULT_MIN_LENGTH,
    "cooldown": DEFAULT_COOLDOWN,
    "blacklisted_users": {},  # user_id: {"reason": str, "timestamp": float, "by": int}
    "auto_delete_denied": False,
    "require_reason": False,
    "dm_notifications": True,
    "anonymous_suggestions": False,
}

DEFAULT_USER_CONFIG = {
    "suggestions_made": 0,
    "last_suggestion": 0,
}
