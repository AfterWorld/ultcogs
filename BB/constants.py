"""
Constants and configuration for the DeathBattle cog.
"""
import os
from datetime import timedelta

# File paths
BASE_DATA_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/DeathBattle"
TEMPLATE_PATH = os.path.join(BASE_DATA_PATH, "deathbattle.png")
FONT_PATH = os.path.join(BASE_DATA_PATH, "onepiece.ttf")

# Ensure directory exists
os.makedirs(BASE_DATA_PATH, exist_ok=True)

# Battle constants - Updated for new system
STARTING_HP = 250  # Increased from 100 for more complex battles
MAX_HP = 250
MIN_DAMAGE = 5
MAX_DAMAGE = 35  # Increased for critical attacks
CRIT_CHANCE = 0.15
CRIT_MULTIPLIER = 1.5

# New battle constants
TURN_TIMEOUT = 30  # seconds per turn
MAX_BATTLE_TURNS = 25  # prevent infinite battles
STATUS_EFFECT_DURATION = 3  # default duration for effects

# Economy constants
MIN_BERRIS_REWARD = 100  # Increased rewards
MAX_BERRIS_REWARD = 500
ROBBERY_SUCCESS_RATE = 0.6
MIN_ROBBERY_AMOUNT = 50  # Increased minimum

# Devil Fruit acquisition chances
DEVIL_FRUIT_DROP_CHANCE = 0.05  # 5% chance after battle
RARE_FRUIT_CHANCE = 0.2  # 20% of drops are rare

# Cooldowns (in seconds)
BATTLE_COOLDOWN = 300  # 5 minutes
BANK_ROBBERY_COOLDOWN = 1800  # 30 minutes
BANK_DEPOSIT_COOLDOWN = 60  # 1 minute
DEVIL_FRUIT_USE_COOLDOWN = 3600  # 1 hour for special abilities

# Bank security levels
BANK_SECURITY_LEVELS = {
    "basic": {"cost": 0, "protection": 0.0},
    "standard": {"cost": 500, "protection": 0.2},
    "advanced": {"cost": 2000, "protection": 0.4},
    "maximum": {"cost": 5000, "protection": 0.6}
}

# Character progression thresholds
TITLE_REQUIREMENTS = {
    "wins": [0, 5, 10, 25, 50, 100, 200, 500, 1000],
    "berris": [0, 10000, 50000, 200000, 1000000, 5000000, 25000000, 100000000, 500000000]
}

# Battle environment effects
ENVIRONMENT_EFFECTS = {
    "crit_boost": 0.1,      # +10% crit chance
    "burn_boost": 0.2,      # +20% burn chance  
    "strong_boost": 5,      # +5 damage to strong attacks
    "elemental_boost": 0.15, # +15% to all elemental effects
    "heal_boost": 10,       # +10 healing
    "war_boost": 10,        # +10 damage in war zones
    "ultimate_boost": 0.2   # +20% to everything
}