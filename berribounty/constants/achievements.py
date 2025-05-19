"""Achievement definitions for the One Piece bot."""

ACHIEVEMENTS = {
    "first_battle": {
        "name": "First Steps",
        "description": "Fight your first battle",
        "emoji": "⚔️",
        "conditions": {
            "event_type": "battle_complete",
            "battles": 1
        },
        "rewards": {
            "berries": 5000,
            "title": "Rookie Fighter"
        }
    },
    "first_win": {
        "name": "Taste of Victory",
        "description": "Win your first battle",
        "emoji": "🏆",
        "conditions": {
            "event_type": "battle_win",
            "wins": 1
        },
        "rewards": {
            "berries": 10000,
            "title": "Victor"
        }
    },
    "berries_millionaire": {
        "name": "Wealthy Pirate",
        "description": "Accumulate 1,000,000 berries",
        "emoji": "💰",
        "conditions": {
            "event_type": "berries_gained",
            "berries": 1000000
        },
        "rewards": {
            "berries": 50000,
            "title": "Millionaire"
        }
    },
    "devil_fruit_owner": {
        "name": "Cursed Power",
        "description": "Obtain your first devil fruit",
        "emoji": "🍎",
        "conditions": {
            "event_type": "fruit_obtained",
            "devil_fruit": True
        },
        "rewards": {
            "berries": 100000,
            "title": "Devil Fruit User"
        }
    },
    "ten_wins": {
        "name": "Rising Fighter",
        "description": "Win 10 battles",
        "emoji": "🥊",
        "conditions": {
            "event_type": "battle_win",
            "wins": 10
        },
        "rewards": {
            "berries": 25000,
            "title": "Skilled Fighter"
        }
    },
    "hundred_battles": {
        "name": "Veteran Warrior",
        "description": "Fight 100 battles",
        "emoji": "🗡️",
        "conditions": {
            "event_type": "battle_complete",
            "battles": 100
        },
        "rewards": {
            "berries": 100000,
            "title": "Battle Veteran"
        }
    },
    "daily_dedication": {
        "name": "Daily Dedication",
        "description": "Claim daily rewards 30 days in a row",
        "emoji": "📅",
        "conditions": {
            "event_type": "daily_claimed",
            "daily_streak": 30
        },
        "rewards": {
            "berries": 200000,
            "title": "Dedicated Pirate"
        }
    },
    "big_spender": {
        "name": "Big Spender",
        "description": "Spend 10,000,000 berries total",
        "emoji": "💸",
        "conditions": {
            "event_type": "berries_spent",
            "berries_spent": 10000000
        },
        "rewards": {
            "berries": 500000,
            "title": "High Roller"
        }
    },
    "perfect_fighter": {
        "name": "Perfect Fighter",
        "description": "Win a battle without taking damage",
        "emoji": "🥇",
        "conditions": {
            "event_type": "perfect_win"
        },
        "rewards": {
            "berries": 50000,
            "title": "Flawless"
        }
    },
    "damage_dealer": {
        "name": "Destroyer",
        "description": "Deal 1,000,000 total damage",
        "emoji": "💥",
        "conditions": {
            "event_type": "damage_dealt",
            "damage_dealt": 1000000
        },
        "rewards": {
            "berries": 75000,
            "title": "Destroyer"
        }
    }
}