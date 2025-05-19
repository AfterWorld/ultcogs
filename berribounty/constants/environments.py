"""Battle environment definitions."""

BATTLE_ENVIRONMENTS = {
    "marineford": {
        "name": "Marineford",
        "description": "The great battlefield where legends clash",
        "effects": {
            "all_damage": 1.2,  # 20% more damage
            "critical_rate": 0.15  # +5% crit rate
        },
        "image_url": None,
        "rarity": "legendary"
    },
    "enies_lobby": {
        "name": "Enies Lobby",
        "description": "Judicial island with endless daylight",
        "effects": {
            "speed_bonus": 1.1,  # 10% speed boost
            "mp_regen": 5  # +5 MP per turn
        },
        "image_url": None,
        "rarity": "rare"
    },
    "alabasta_desert": {
        "name": "Alabasta Desert",
        "description": "Scorching sands that drain energy",
        "effects": {
            "mp_drain": 3,  # -3 MP per turn
            "fire_damage": 1.3  # +30% fire damage
        },
        "image_url": None,
        "rarity": "common"
    },
    "water_seven": {
        "name": "Water Seven",
        "description": "City of water and shipwrights",
        "effects": {
            "healing_bonus": 1.5,  # 50% more healing
            "water_damage": 1.2  # 20% more water damage
        },
        "image_url": None,
        "rarity": "common"
    },
    "skypiea": {
        "name": "Skypiea",
        "description": "Island in the sky with thin air",
        "effects": {
            "speed_bonus": 1.15,  # 15% speed boost
            "max_hp": 0.9  # -10% max HP
        },
        "image_url": None,
        "rarity": "rare"
    },
    "impel_down": {
        "name": "Impel Down",
        "description": "The underwater prison",
        "effects": {
            "defense_bonus": 1.2,  # 20% more defense
            "poison_immunity": True
        },
        "image_url": None,
        "rarity": "rare"
    },
    "shabondy": {
        "name": "Sabaody Archipelago",
        "description": "Island of bubbles and mangroves",
        "effects": {
            "bubble_shield": 0.1,  # 10% chance to avoid damage
            "all_stats": 1.05  # 5% boost to all stats
        },
        "image_url": None,
        "rarity": "common"
    },
    "fishman_island": {
        "name": "Fishman Island",
        "description": "Underwater paradise",
        "effects": {
            "water_damage": 1.5,  # 50% more water damage
            "mp_bonus": 1.2  # 20% more max MP
        },
        "image_url": None,
        "rarity": "rare"
    },
    "dressrosa": {
        "name": "Dressrosa",
        "description": "Kingdom of passion and toys",
        "effects": {
            "critical_damage": 1.3,  # 30% more crit damage
            "status_resistance": 0.3  # 30% status effect resistance
        },
        "image_url": None,
        "rarity": "rare"
    },
    "wano": {
        "name": "Wano Country",
        "description": "Land of samurai and honor",
        "effects": {
            "sword_damage": 1.4,  # 40% more sword damage
            "honor_bonus": 1.1  # 10% all stats when health > 50%
        },
        "image_url": None,
        "rarity": "legendary"
    }
}