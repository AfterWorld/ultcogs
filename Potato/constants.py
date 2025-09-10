import discord

# Embed colors
EMBED_PENDING  = discord.Color.blurple()
EMBED_APPROVED = discord.Color.green()
EMBED_DENIED   = discord.Color.red()
EMBED_INFO     = discord.Color.blue()

# Defaults
DEFAULT_THRESHOLD = 5
DEFAULT_MAX_LENGTH = 2000
DEFAULT_MIN_LENGTH = 10
DEFAULT_COOLDOWN   = 300  # seconds

# Config defaults
GUILD_DEFAULTS = {
    "suggestion_channel": None,
    "staff_channel": None,
    "log_channel": None,
    "upvote_threshold": DEFAULT_THRESHOLD,
    "suggestion_count": 0,
    "suggestions": {},            # id -> data
    "max_length": DEFAULT_MAX_LENGTH,
    "min_length": DEFAULT_MIN_LENGTH,
    "cooldown": DEFAULT_COOLDOWN,
    "dm_notifications": True,
    "anonymous_suggestions": False,
    "auto_delete_denied": False,
    "modrole_ids": []             # role IDs allowed to approve/deny (admins always allowed)
}

USER_DEFAULTS = {
    "last_suggest_ts": 0,
    "suggestions_made": 0
}
