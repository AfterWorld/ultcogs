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

# Battle constants
STARTING_HP = 100
MIN_DAMAGE = 5
MAX_DAMAGE = 25
CRIT_CHANCE = 0.15
CRIT_MULTIPLIER = 1.5

# Economy constants
MIN_BERRIS_REWARD = 50
MAX_BERRIS_REWARD = 200
ROBBERY_SUCCESS_RATE = 0.6
MIN_ROBBERY_AMOUNT = 10

# Cooldowns (in seconds)
BATTLE_COOLDOWN = 300  # 5 minutes
BANK_ROBBERY_COOLDOWN = 1800  # 30 minutes
BANK_DEPOSIT_COOLDOWN = 60  # 1 minute

# Battle moves
BATTLE_MOVES = [
    {
        "name": "Punch",
        "description": "A basic punch attack",
        "min_damage": 8,
        "max_damage": 15,
        "crit_chance": 0.1
    },
    {
        "name": "Devil Fruit Strike",
        "description": "A powerful Devil Fruit enhanced attack",
        "min_damage": 12,
        "max_damage": 22,
        "crit_chance": 0.2
    },
    {
        "name": "Haki Blast",
        "description": "An energy-infused attack",
        "min_damage": 10,
        "max_damage": 18,
        "crit_chance": 0.15
    },
    {
        "name": "Special Technique",
        "description": "A unique fighting technique",
        "min_damage": 15,
        "max_damage": 25,
        "crit_chance": 0.25
    }
]

# Bank security levels
BANK_SECURITY_LEVELS = {
    "basic": {"cost": 0, "protection": 0.0},
    "standard": {"cost": 100, "protection": 0.2},
    "advanced": {"cost": 500, "protection": 0.4},
    "maximum": {"cost": 1000, "protection": 0.6}
}