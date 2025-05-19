"""Configuration settings for the One Piece bot."""

from redbot.core import Config

DEFAULT_GUILD = {
    "players": {},
    "global_bank": 0,
    "maintenance_mode": False,
    "battle_channel": None,
    "announcement_channel": None,
    "log_channel": None,
    "disabled_commands": [],
    "event_data": {},
    "battle_settings": {
        "max_battle_time": 300,  # 5 minutes
        "turn_time_limit": 60,   # 1 minute per turn
        "auto_battle_rewards": True,
        "spectator_betting": True
    },
    "economy_settings": {
        "daily_amount": 5000,
        "work_cooldown": 14400,  # 4 hours
        "gamble_cooldown": 1800,  # 30 minutes
        "max_daily_transfers": 5,
        "transfer_tax": 0.05  # 5% tax on transfers
    },
    "fruit_settings": {
        "search_cost_base": 50000,
        "search_cost_multiplier": 1.5,
        "max_daily_searches": 3,
        "rare_fruit_chance": 0.1,
        "market_refresh_hours": 24
    }
}

DEFAULT_MEMBER = {
    "berries": 0,
    "bank_berries": 0,
    "devil_fruit": None,
    "devil_fruit_mastery": {},
    "wins": 0,
    "losses": 0,
    "total_damage_dealt": 0,
    "total_damage_taken": 0,
    "achievements": [],
    "titles": [],
    "current_title": None,
    "last_active": None,
    "last_daily": 0,
    "last_work": 0,
    "last_gamble": 0,
    "daily_streak": 0,
    "stats": {
        "battles_fought": 0,
        "berries_earned": 0,
        "berries_lost": 0,
        "berries_given": 0,
        "berries_received": 0,
        "berries_gambled": 0,
        "critical_hits": 0,
        "perfect_wins": 0,
        "work_count": 0,
        "daily_claims": 0,
        "gambles_made": 0,
        "battles_with_fruit": 0
    },
    "battle_preferences": {
        "auto_accept_challenges": False,
        "preferred_battle_style": "balanced",
        "show_damage_numbers": True,
        "enable_battle_sounds": True
    },
    "inventory": {
        "items": {},
        "consumables": {}
    }
}

# Bot-wide settings
DEFAULT_GLOBAL = {
    "total_players": 0,
    "total_berries_in_circulation": 0,
    "global_events": {},
    "maintenance_message": "The bot is currently under maintenance. Please try again later.",
    "version": "1.0.0",
    "last_update": None,
    "feature_flags": {
        "enable_devil_fruits": True,
        "enable_battles": True,
        "enable_gambling": True,
        "enable_achievements": True,
        "enable_leaderboards": True,
        "enable_events": True
    }
}

def setup_config(cog_instance):
    """Setup configuration for the cog."""
    config = Config.get_conf(cog_instance, identifier=1357924682, force_registration=True)
    config.register_guild(**DEFAULT_GUILD)
    config.register_member(**DEFAULT_MEMBER)
    config.register_global(**DEFAULT_GLOBAL)
    return config

# Configuration validation
def validate_guild_config(config_data):
    """Validate guild configuration data."""
    required_keys = list(DEFAULT_GUILD.keys())
    for key in required_keys:
        if key not in config_data:
            config_data[key] = DEFAULT_GUILD[key]
    return config_data

def validate_member_config(config_data):
    """Validate member configuration data."""
    required_keys = list(DEFAULT_MEMBER.keys())
    for key in required_keys:
        if key not in config_data:
            config_data[key] = DEFAULT_MEMBER[key]
    return config_data

# Settings for different bot features
BATTLE_SETTINGS = {
    "max_hp": 100,
    "max_mp": 100,
    "base_damage": 25,
    "crit_chance": 0.1,
    "crit_multiplier": 1.5,
    "status_effect_chance": 0.3,
    "mp_regen_per_turn": 10,
    "max_cooldown_turns": 10
}

ECONOMY_SETTINGS = {
    "starting_berries": 1000,
    "daily_base_amount": 5000,
    "work_base_amount": 3000,
    "gamble_min_bet": 100,
    "gamble_max_bet": 1000000,
    "transfer_min_amount": 1,
    "transfer_max_amount": 10000000
}

DEVIL_FRUIT_SETTINGS = {
    "search_base_cost": 50000,
    "search_success_rate": 0.15,
    "rare_fruit_rate": 0.1,
    "mastery_per_battle": 2,
    "max_mastery": 100,
    "market_price_variation": 0.2
}

# Level and progression settings
PROGRESSION_SETTINGS = {
    "title_unlock_requirements": {
        "Rookie Pirate": {"battles": 0},
        "Seasoned Fighter": {"wins": 5},
        "Veteran Warrior": {"wins": 25},
        "Pirate Captain": {"wins": 50},
        "Notorious Pirate": {"wins": 100},
        "Legendary Pirate": {"wins": 250},
        "Pirate King": {"wins": 500}
    },
    "achievement_berry_rewards": {
        "easy": 10000,
        "medium": 25000,
        "hard": 50000,
        "legendary": 100000
    }
}

# Error messages
ERROR_MESSAGES = {
    "maintenance_mode": "⚙️ The bot is currently under maintenance. Please try again later.",
    "insufficient_berries": "💸 You don't have enough berries for this action!",
    "already_in_battle": "⚔️ You are already in a battle!",
    "player_not_found": "❓ Player not found.",
    "fruit_already_owned": "🍎 You already have a devil fruit!",
    "fruit_not_available": "❌ This devil fruit is not available.",
    "command_disabled": "🚫 This command is currently disabled.",
    "cooldown_active": "⏰ This command is on cooldown.",
    "invalid_amount": "💢 Please enter a valid amount.",
    "permission_denied": "🔒 You don't have permission to use this command."
}

# Success messages
SUCCESS_MESSAGES = {
    "berries_transferred": "💸 Berries transferred successfully!",
    "fruit_obtained": "🍎 You have obtained a devil fruit!",
    "battle_won": "🏆 Victory is yours!",
    "achievement_unlocked": "🏆 Achievement unlocked!",
    "daily_claimed": "🌅 Daily berries claimed!",
    "work_completed": "💼 Work completed successfully!",
    "settings_updated": "⚙️ Settings updated successfully!"
}