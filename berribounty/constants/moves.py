"""Battle move definitions for the One Piece bot."""

MOVES = {
    "basic": [
        {
            "name": "Punch",
            "description": "A basic punch attack",
            "damage": 25,
            "mp_cost": 0,
            "cooldown": 0,
            "emoji": "👊",
            "type": "physical"
        },
        {
            "name": "Kick",
            "description": "A basic kick attack",
            "damage": 30,
            "mp_cost": 0,
            "cooldown": 0,
            "emoji": "🦵",
            "type": "physical"
        },
        {
            "name": "Headbutt",
            "description": "A powerful headbutt",
            "damage": 35,
            "mp_cost": 5,
            "cooldown": 1,
            "emoji": "🗣️",
            "type": "physical",
            "effects": [{"type": "stun", "duration": 1, "chance": 0.3}]
        },
        {
            "name": "Uppercut",
            "description": "An upward punch",
            "damage": 40,
            "mp_cost": 10,
            "cooldown": 2,
            "emoji": "👊",
            "type": "physical",
            "crit_chance": 0.2
        },
        {
            "name": "Combo Strike",
            "description": "Multiple quick attacks",
            "damage": 20,
            "mp_cost": 15,
            "cooldown": 3,
            "emoji": "⚡",
            "type": "physical",
            "hit_count": 3
        }
    ],
    "special": [
        {
            "name": "Power Strike",
            "description": "A powerful charged attack",
            "damage": 60,
            "mp_cost": 25,
            "cooldown": 4,
            "emoji": "💥",
            "type": "special"
        },
        {
            "name": "Heal",
            "description": "Restore your health",
            "damage": 0,
            "mp_cost": 30,
            "cooldown": 5,
            "emoji": "💚",
            "type": "healing",
            "effects": [{"type": "heal", "amount": 50}]
        },
        {
            "name": "Focus",
            "description": "Increase critical hit chance",
            "damage": 0,
            "mp_cost": 20,
            "cooldown": 6,
            "emoji": "🎯",
            "type": "buff",
            "effects": [{"type": "focus", "duration": 3, "bonus": 0.3}]
        },
        {
            "name": "Intimidate",
            "description": "Lower opponent's attack",
            "damage": 0,
            "mp_cost": 15,
            "cooldown": 4,
            "emoji": "😤",
            "type": "debuff",
            "effects": [{"type": "intimidate", "duration": 3, "reduction": 0.2}]
        },
        {
            "name": "Berserker Rage",
            "description": "Increase damage but reduce defense",
            "damage": 0,
            "mp_cost": 35,
            "cooldown": 8,
            "emoji": "😡",
            "type": "buff",
            "effects": [
                {"type": "damage_boost", "duration": 4, "bonus": 0.5},
                {"type": "defense_reduction", "duration": 4, "reduction": 0.3}
            ]
        },
        {
            "name": "Lightning Strike",
            "description": "Fast electric attack",
            "damage": 55,
            "mp_cost": 30,
            "cooldown": 4,
            "emoji": "⚡",
            "type": "elemental",
            "effects": [{"type": "paralyze", "duration": 2, "chance": 0.4}]
        },
        {
            "name": "Whirlwind",
            "description": "Spinning attack that hits multiple times",
            "damage": 25,
            "mp_cost": 25,
            "cooldown": 5,
            "emoji": "🌪️",
            "type": "physical",
            "hit_count": 3,
            "effects": [{"type": "dizzy", "duration": 2}]
        },
        {
            "name": "Shield Bash",
            "description": "Defensive attack that can stun",
            "damage": 35,
            "mp_cost": 20,
            "cooldown": 3,
            "emoji": "🛡️",
            "type": "defensive",
            "effects": [
                {"type": "stun", "duration": 1, "chance": 0.5},
                {"type": "defense_boost", "duration": 2, "bonus": 0.2}
            ]
        }
    ],
    "ultimate": [
        {
            "name": "Final Strike",
            "description": "Ultimate finishing move",
            "damage": 100,
            "mp_cost": 50,
            "cooldown": 10,
            "emoji": "💀",
            "type": "ultimate",
            "requirements": {"hp_percent": 0.3}  # Can only use when HP < 30%
        },
        {
            "name": "Phoenix Rebirth",
            "description": "Revive with full health",
            "damage": 0,
            "mp_cost": 80,
            "cooldown": 15,
            "emoji": "🔥",
            "type": "ultimate",
            "effects": [{"type": "revive", "amount": 100}],
            "requirements": {"hp_percent": 0.1}  # Can only use when HP < 10%
        },
        {
            "name": "World Destroyer",
            "description": "Devastating area attack",
            "damage": 150,
            "mp_cost": 100,
            "cooldown": 20,
            "emoji": "🌍",
            "type": "ultimate",
            "effects": [{"type": "devastation", "duration": 3}]
        }
    ],
    "weapon_styles": {
        "sword": [
            {
                "name": "Slash",
                "description": "Basic sword slash",
                "damage": 35,
                "mp_cost": 5,
                "cooldown": 1,
                "emoji": "⚔️",
                "type": "sword"
            },
            {
                "name": "Cross Slash",
                "description": "X-shaped sword attack",
                "damage": 50,
                "mp_cost": 15,
                "cooldown": 3,
                "emoji": "❌",
                "type": "sword"
            },
            {
                "name": "Thousand Cuts",
                "description": "Rapid sword strikes",
                "damage": 30,
                "mp_cost": 25,
                "cooldown": 5,
                "emoji": "🗡️",
                "type": "sword",
                "hit_count": 5
            }
        ],
        "martial_arts": [
            {
                "name": "Iron Fist",
                "description": "Hardened punch attack",
                "damage": 45,
                "mp_cost": 10,
                "cooldown": 2,
                "emoji": "👊",
                "type": "martial_arts"
            },
            {
                "name": "Flying Kick",
                "description": "Leaping kick attack",
                "damage": 40,
                "mp_cost": 12,
                "cooldown": 2,
                "emoji": "🦵",
                "type": "martial_arts"
            },
            {
                "name": "Pressure Point Strike",
                "description": "Target vital points",
                "damage": 35,
                "mp_cost": 20,
                "cooldown": 4,
                "emoji": "👆",
                "type": "martial_arts",
                "effects": [{"type": "disable", "duration": 2}]
            }
        ],
        "gunslinger": [
            {
                "name": "Quick Shot",
                "description": "Fast pistol shot",
                "damage": 30,
                "mp_cost": 8,
                "cooldown": 1,
                "emoji": "🔫",
                "type": "gunslinger"
            },
            {
                "name": "Double Tap",
                "description": "Two quick shots",
                "damage": 25,
                "mp_cost": 15,
                "cooldown": 3,
                "emoji": "🔫🔫",
                "type": "gunslinger",
                "hit_count": 2
            },
            {
                "name": "Explosive Shot",
                "description": "Shot with explosive rounds",
                "damage": 60,
                "mp_cost": 25,
                "cooldown": 5,
                "emoji": "💥",
                "type": "gunslinger",
                "effects": [{"type": "burn", "duration": 2, "damage": 10}]
            }
        ]
    }
}

# Move effectiveness chart (rock-paper-scissors style)
MOVE_EFFECTIVENESS = {
    "physical": {
        "strong_against": ["special"],
        "weak_against": ["defensive"],
        "neutral": ["physical", "elemental"]
    },
    "special": {
        "strong_against": ["defensive"],
        "weak_against": ["physical"], 
        "neutral": ["special", "elemental"]
    },
    "defensive": {
        "strong_against": ["physical"],
        "weak_against": ["special"],
        "neutral": ["defensive", "elemental"]
    },
    "elemental": {
        "strong_against": ["physical", "special"],
        "weak_against": ["elemental"],
        "neutral": ["defensive"]
    }
}

# Status effects that moves can inflict
STATUS_EFFECTS = {
    "burn": {
        "name": "Burn",
        "description": "Takes damage each turn",
        "emoji": "🔥",
        "damage_per_turn": True
    },
    "poison": {
        "name": "Poison",
        "description": "Takes poison damage each turn", 
        "emoji": "☠️",
        "damage_per_turn": True
    },
    "freeze": {
        "name": "Freeze",
        "description": "Cannot move",
        "emoji": "🧊",
        "skip_turn": True
    },
    "stun": {
        "name": "Stun",
        "description": "Cannot act",
        "emoji": "⚡",
        "skip_turn": True
    },
    "paralyze": {
        "name": "Paralyze",
        "description": "Chance to not act",
        "emoji": "⚡",
        "act_chance": 0.5
    },
    "blind": {
        "name": "Blind",
        "description": "Reduced accuracy",
        "emoji": "🌫️",
        "accuracy_modifier": 0.7
    },
    "heal": {
        "name": "Healing",
        "description": "Restores health each turn",
        "emoji": "💚",
        "heal_per_turn": True
    },
    "regen": {
        "name": "Regeneration",
        "description": "Slowly heals over time",
        "emoji": "💚",
        "heal_per_turn": True
    },
    "focus": {
        "name": "Focus",
        "description": "Increased critical hit chance",
        "emoji": "🎯",
        "crit_bonus": 0.3
    },
    "damage_boost": {
        "name": "Damage Boost",
        "description": "Increased damage output",
        "emoji": "⬆️",
        "damage_modifier": 1.5
    },
    "defense_boost": {
        "name": "Defense Boost", 
        "description": "Reduced damage taken",
        "emoji": "🛡️",
        "defense_modifier": 1.3
    },
    "speed_boost": {
        "name": "Speed Boost",
        "description": "Increased speed and evasion",
        "emoji": "💨",
        "evasion_bonus": 0.2
    }
}