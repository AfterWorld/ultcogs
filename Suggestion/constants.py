DEFAULT_CONFIG = {
    "suggestion_channel": None,
    "staff_channel": None,
    "log_channel": None,
    "archive_channel": None,
    "reward_credits": 1000,
    "use_beri_core": False,
    "next_id": 1,
    "blacklisted_words": [],
    "blacklisted_users": [],
    "cooldown_per_day": 1,
    "upvote_threshold": 10,
    "downvote_threshold": 5,
    "staff_notification_threshold": 5,  # ADD THIS LINE
    "suggestions": {},  # id -> data
    "stats": {},  # user_id -> {"submitted": int, "approved": int}
}

COLORS = {
    "pending": 0x3498db,
    "approved": 0x2ecc71,
    "declined": 0xe74c3c,
}

STATUS_EMOJIS = {
    "pending": "🕐",
    "approved": "✅",
    "declined": "❌",
}
