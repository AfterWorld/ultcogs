DEFAULT_CONFIG = {
    "suggestion_channel": None,
    "cooldown": 300,
    "staff_channel": None,
    "log_channel": None,
    "auto_approve_threshold": 10,
    "auto_deny_threshold": -5,
    "suggestions": {},
    "next_id": 1,
    "voting_roles": [],
    "suggestion_roles": [],
    "anonymous_suggestions": False,
    "require_reason": True,
    "max_suggestion_length": 1000,
    "reward_credits": 0,
    "categories": {},
    "blacklisted_words": [],
    "dm_notifications": True,
    "thread_suggestions": False,
    "reaction_voting": False,
    "vote_weight": {},
    "suggestion_queue": False,
    "use_beri_core": False,  # optional integration switch
}

COLORS = {
    "pending": 0x3498DB,
    "approved": 0x27AE60,
    "denied": 0xE74C3C,
    "implemented": 0x9B59B6,
    "considering": 0xF39C12,
    "duplicate": 0x95A5A6,
    "error": 0xE74C3C,
    "success": 0x2ECC71,
    "warning": 0xE67E22,
    "info": 0x3498DB,
}

STATUS_EMOJIS = {
    "pending": "⏳",
    "approved": "✅",
    "denied": "❌",
    "implemented": "🎉",
    "considering": "🤔",
    "duplicate": "🔄",
}
