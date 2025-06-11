"""
Enhanced constants and configuration for the DeathBattle cog with expanded features.
"""
import os
from datetime import timedelta

# File paths - UPDATED with correct paths
BASE_DATA_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/CogManager/cogs/BB/template"
TEMPLATE_PATH = os.path.join(BASE_DATA_PATH, "deathbattle.png")
FONT_PATH = os.path.join(BASE_DATA_PATH, "onepiece.ttf")

# Ensure directory exists
os.makedirs(BASE_DATA_PATH, exist_ok=True)

# Custom emoji IDs for health bars
HEALTH_EMOJIS = {
    "full": "<:full:1379318858279551027>",
    "half": "<:half:1379318888906489897>",
    "gone": "<:gone:1379318910809018408>"
}

# Battle constants - Enhanced system
STARTING_HP = 275  # Increased for longer battles
MAX_HP = 275
MIN_DAMAGE = 5
MAX_DAMAGE = 40  # Increased for critical attacks
CRIT_CHANCE = 0.15
CRIT_MULTIPLIER = 1.5

# Enhanced battle constants
TURN_TIMEOUT = 35  # seconds per turn (slightly increased)
MAX_BATTLE_TURNS = 30  # prevent infinite battles
STATUS_EFFECT_DURATION = 3  # default duration for effects

# Devil Fruit effect chances
DEVIL_FRUIT_ACTIVATION_RATE = 0.45  # Base chance for fruit effects
RARE_FRUIT_BONUS_RATE = 0.15  # Additional chance for rare fruits
ENVIRONMENT_BOOST_MULTIPLIER = 1.25  # Environment effect multiplier

# Economy constants - Enhanced rewards
MIN_BERRIS_REWARD = 150  # Increased base rewards
MAX_BERRIS_REWARD = 750  # Higher max rewards
WIN_STREAK_BONUS = 50   # Bonus per consecutive win
RARE_FRUIT_BONUS = 200  # Extra berris for having rare fruit

# Robbery system
ROBBERY_SUCCESS_RATE = 0.55
MIN_ROBBERY_AMOUNT = 100  # Increased minimum
MAX_ROBBERY_PERCENTAGE = 0.35  # Max 35% can be stolen

# Devil Fruit acquisition chances - Rebalanced
DEVIL_FRUIT_DROP_CHANCE = 0.06  # 6% chance after battle (increased)
RARE_FRUIT_CHANCE = 0.25  # 25% of drops are rare (increased)

# Devil Fruit starter system - Enhanced
STARTER_COMMON_CHANCE = 0.80  # 80% chance for common fruit
STARTER_RARE_CHANCE = 0.20    # 20% chance for rare fruit (increased)
STARTER_BERRIES_BONUS = 1500  # Starting berries bonus (increased)

# Devil Fruit management costs - Adjusted
REMOVE_FRUIT_COST = 4000      # Cost to remove current fruit (reduced)
BUY_FRUIT_COST = 8000         # Cost to buy a random new fruit (reduced)
BUY_RARE_FRUIT_COST = 20000   # Cost to buy specifically a rare fruit

# Fruit purchase chances (when buying) - Enhanced
BUY_COMMON_CHANCE = 0.65      # 65% chance for common when buying
BUY_RARE_CHANCE = 0.35        # 35% chance for rare when buying (increased)

# Rare fruit distribution limits - More generous
MAX_RARE_FRUITS_PER_TYPE = 5  # Increased max per rare fruit type
MYTHICAL_FRUIT_LIMIT = 2      # Special limit for mythical zoans
LEGENDARY_FRUIT_LIMIT = 1     # Limit for truly legendary fruits

# Cooldowns (in seconds) - Adjusted for better gameplay
BATTLE_COOLDOWN = 240  # 4 minutes (reduced)
BANK_ROBBERY_COOLDOWN = 1500  # 25 minutes (reduced)
BANK_DEPOSIT_COOLDOWN = 45  # 45 seconds (reduced)
DEVIL_FRUIT_USE_COOLDOWN = 2700  # 45 minutes for special abilities
FRUIT_REMOVE_COOLDOWN = 72000  # 20 hours (reduced)
FRUIT_BUY_COOLDOWN = 2700     # 45 minutes (reduced)

# Enhanced bank security levels
BANK_SECURITY_LEVELS = {
    "basic": {"cost": 0, "protection": 0.0, "description": "No protection"},
    "standard": {"cost": 400, "protection": 0.25, "description": "Basic security"},
    "advanced": {"cost": 1500, "protection": 0.45, "description": "Advanced protection"},
    "maximum": {"cost": 4000, "protection": 0.65, "description": "Maximum security"},
    "legendary": {"cost": 10000, "protection": 0.80, "description": "Legendary vault security"}
}

# Character progression thresholds - Enhanced
TITLE_REQUIREMENTS = {
    "wins": [0, 3, 7, 15, 25, 50, 75, 125, 200, 300, 500, 750, 1000],
    "berris": [0, 5000, 25000, 100000, 500000, 2500000, 10000000, 50000000, 250000000, 1000000000]
}

# Battle environment effects - Enhanced
ENVIRONMENT_EFFECTS = {
    "lightning_boost": {"multiplier": 1.5, "description": "Lightning attacks amplified"},
    "desert_boost": {"multiplier": 1.4, "description": "Fire and sand powers enhanced"},
    "blade_boost": {"multiplier": 1.3, "description": "Cutting attacks sharpened"},
    "elemental_boost": {"multiplier": 1.6, "description": "All elemental effects enhanced"},
    "aquatic_boost": {"multiplier": 1.3, "description": "Water abilities and healing boosted"},
    "war_boost": {"multiplier": 1.4, "description": "All combat abilities enhanced"},
    "legendary_boost": {"multiplier": 2.0, "description": "All powers dramatically amplified"},
    "darkness_boost": {"multiplier": 1.5, "description": "Dark powers flourish"},
    "justice_boost": {"multiplier": 1.3, "description": "Light and holy powers amplified"},
    "nature_boost": {"multiplier": 1.3, "description": "Plant and nature abilities enhanced"},
    "food_boost": {"multiplier": 1.2, "description": "Food-based abilities and healing boosted"},
    "transformation_boost": {"multiplier": 1.4, "description": "Shape-changing abilities enhanced"}
}

# Status effect configurations
STATUS_EFFECTS = {
    "burn": {
        "damage_per_stack": 5,
        "max_stacks": 5,
        "description": "Takes fire damage each turn"
    },
    "freeze": {
        "duration": 2,
        "dodge_penalty": 0.5,
        "description": "Movement severely restricted"
    },
    "stun": {
        "duration": 1,
        "blocks_action": True,
        "description": "Cannot act for duration"
    },
    "poison": {
        "damage_per_stack": 3,
        "max_stacks": 8,
        "description": "Takes poison damage each turn"
    },
    "bleed": {
        "damage_per_stack": 4,
        "max_stacks": 6,
        "description": "Takes bleeding damage each turn"
    },
    "speed_boost": {
        "duration": 3,
        "dodge_bonus": 0.2,
        "crit_bonus": 0.1,
        "description": "Enhanced speed and reflexes"
    },
    "attack_boost": {
        "duration": 3,
        "damage_multiplier": 1.3,
        "crit_bonus": 0.15,
        "description": "Increased attack power"
    },
    "defense_boost": {
        "duration": 3,
        "damage_reduction": 0.25,
        "description": "Reduced incoming damage"
    },
    "confusion": {
        "duration": 2,
        "accuracy_penalty": 0.3,
        "description": "Attacks may miss target"
    },
    "fear": {
        "duration": 2,
        "damage_penalty": 0.2,
        "accuracy_penalty": 0.15,
        "description": "Reduced combat effectiveness"
    }
}

# Achievement system - New feature
ACHIEVEMENTS = {
    "first_blood": {
        "condition": "Win your first battle",
        "reward": 500,
        "title": "First Victory"
    },
    "fruit_collector": {
        "condition": "Obtain 5 different Devil Fruits (over time)",
        "reward": 2000,
        "title": "Devil Fruit Collector"
    },
    "berris_millionaire": {
        "condition": "Accumulate 1,000,000 total berris",
        "reward": 10000,
        "title": "Millionaire Pirate"
    },
    "win_streak_5": {
        "condition": "Win 5 battles in a row",
        "reward": 1000,
        "title": "Unstoppable"
    },
    "environmental_master": {
        "condition": "Win battles in 10 different environments",
        "reward": 1500,
        "title": "World Traveler"
    },
    "rare_fruit_master": {
        "condition": "Win 10 battles with a rare Devil Fruit",
        "reward": 3000,
        "title": "Legendary Power"
    },
    "bank_robber": {
        "condition": "Successfully rob 1,000,000 berris total",
        "reward": 5000,
        "title": "Master Thief"
    },
    "elemental_fury": {
        "condition": "Use all elemental devil fruit effects in battles",
        "reward": 2500,
        "title": "Elemental Master"
    }
}

# Seasonal events configuration
SEASONAL_EVENTS = {
    "devil_fruit_festival": {
        "drop_rate_multiplier": 2.0,
        "duration_days": 7,
        "description": "Double Devil Fruit drop rates!"
    },
    "berris_bonanza": {
        "reward_multiplier": 1.5,
        "duration_days": 5,
        "description": "50% more berris from battles!"
    },
    "legendary_awakening": {
        "rare_fruit_chance": 0.5,
        "duration_days": 3,
        "description": "Rare fruits much more common!"
    }
}

# Combat mechanics - Enhanced
COMBO_SYSTEM = {
    "enabled": True,
    "max_combo": 5,
    "damage_bonus_per_combo": 0.1,  # 10% per combo level
    "combo_timeout": 2  # turns before combo resets
}

CRITICAL_HIT_TYPES = {
    "normal": {"multiplier": 1.5, "chance": 0.15},
    "super": {"multiplier": 2.0, "chance": 0.05},
    "devastating": {"multiplier": 2.5, "chance": 0.01}
}

# Balancing constants
BATTLE_BALANCE = {
    "max_damage_per_turn": 150,  # Prevent one-shot kills
    "min_battle_length": 3,      # Minimum turns for a battle
    "comeback_mechanic": True,   # Low health bonus
    "comeback_threshold": 0.2,   # Activate at 20% health
    "comeback_bonus": 0.25       # 25% damage bonus when low
}

# Daily/Weekly bonuses
DAILY_BONUSES = {
    "first_battle_win": 300,     # Bonus for first win of the day
    "login_bonus": 100,          # Daily login bonus
    "weekly_streak": 1000        # Weekly activity bonus
}

# PvP Rankings
RANKING_SYSTEM = {
    "tiers": {
        "rookie": {"min_wins": 0, "max_wins": 9, "berris_bonus": 1.0},
        "veteran": {"min_wins": 10, "max_wins": 29, "berris_bonus": 1.1},
        "elite": {"min_wins": 30, "max_wins": 59, "berris_bonus": 1.25},
        "master": {"min_wins": 60, "max_wins": 99, "berris_bonus": 1.4},
        "grandmaster": {"min_wins": 100, "max_wins": 199, "berris_bonus": 1.6},
        "legend": {"min_wins": 200, "max_wins": 499, "berris_bonus": 1.8},
        "mythic": {"min_wins": 500, "max_wins": float('inf'), "berris_bonus": 2.0}
    }
}

# Special battle modes
BATTLE_MODES = {
    "classic": {
        "description": "Standard 1v1 battle",
        "hp_multiplier": 1.0,
        "reward_multiplier": 1.0
    },
    "endurance": {
        "description": "Battle with increased HP",
        "hp_multiplier": 1.5,
        "reward_multiplier": 1.3
    },
    "blitz": {
        "description": "Fast-paced battle with reduced HP",
        "hp_multiplier": 0.7,
        "reward_multiplier": 0.9
    },
    "elemental": {
        "description": "Enhanced elemental effects",
        "hp_multiplier": 1.0,
        "reward_multiplier": 1.2,
        "elemental_bonus": 2.0
    }
}
