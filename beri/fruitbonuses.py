"""Fruit-specific bonus definitions for Beri activity and fishing."""

FISHING_FRUIT_BONUSES_BY_TYPE = {
    "Logia": {
        "trash_common_weight_delta": -18,
    },
    "Zoan": {
        "rare_plus_weight": 12,
    },
    "Ancient Zoan": {
        "epic_legendary_weight": 18,
    },
    "Mythical Zoan": {
        "legendary_weight": 28,
        "cooldown_reduce_pct": 0.10,
    },
    "Legendary": {
        "rare_plus_weight": 10,
        "legendary_weight": 20,
        "legendary_only_pool": True,
    },
    "Paramecia": {
        "flat_beri_bonus": 100,
    },
}

LEGENDARY_ONLY_CATCHES = [
    (
        "Sea Emperor Scale",
        "🐉",
        "legendary",
        2,
        35_000,
        65_000,
        "A mythical catch only a Legendary fruit user can tame.",
    ),
    (
        "All Blue Phantom",
        "🌀",
        "legendary",
        1,
        45_000,
        80_000,
        "Only a Legendary Devil Fruit user can lure this beast.",
    ),
    (
        "Mythical Leviathan",
        "🐲",
        "legendary",
        1,
        50_000,
        90_000,
        "A monster from the legends. Your fruit power called it.",
    ),
]

FRUIT_COMMAND_BONUSES = {
    "Magu Magu no Mi": {
        "crime_payout_mul": 1.2,
    },
    "Pika Pika no Mi": {
        "hack_cooldown_reduction_pct": 0.30,
    },
    "Yami Yami no Mi": {
        "hack_fail_no_fine": True,
    },
    "Ope Ope no Mi": {
        "hack_amount_mul": 1.25,
    },
    "Doku Doku no Mi": {
        "crime_success_bonus": 0.15,
    },
    "Suna Suna no Mi": {
        "rob_stolen_mul": 1.20,
    },
    "Kage Kage no Mi": {
        "rob_success_bonus": 0.15,
    },
    "Bara Bara no Mi": {
        "rob_immune_chance": 0.50,
    },
    "Gura Gura no Mi": {
        "plunder_payout_mul": 1.25,
    },
    "Gomu Gomu no Mi": {
        "all_activity_luck": 0.05,
    },
    "Hito Hito no Mi: Model Nika": {
        "all_activity_luck": 0.05,
    },
}
