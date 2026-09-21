"""Versioned Phase 1 content. Numbers are provisional, bounded, and testable."""

SLOTS = ("main", "off", "head", "chest", "hands", "legs", "feet", "neck", "ring1", "ring2", "relic")
ATTRS = ("strength", "dexterity", "intelligence", "vitality", "willpower")
CLASSES = {
    "vanguard": {
        "stat": "strength",
        "weapon": "Iron Sword",
    },
    "strider": {
        "stat": "dexterity",
        "weapon": "Twin Fang",
    },
    "arcanist": {
        "stat": "intelligence",
        "weapon": "Aether Staff",
    },
}
# Cooldown is set before the end-of-turn decrement: 3 means two intervening turns.
# Effects are applied before damage, preserving the original Phase 1 timing.
SKILLS = {
    "vanguard": {
        "skill1": dict(name="Cleave", cost=14, cooldown=3, multiplier=1.65, effects={}),
        "skill2": dict(
            name="Guard Break",
            cost=10,
            cooldown=3,
            multiplier=1.05,
            interrupt=True,
            effects={"exposed": 2},
        ),
        "skill3": dict(
            name="Iron Guard",
            cost=16,
            cooldown=4,
            multiplier=0.45,
            guard=True,
            shield_hp=0.35,
            effects={},
        ),
    },
    "strider": {
        "skill1": dict(
            name="Twin Strike", cost=10, cooldown=2, multiplier=1.35, effects={"enemy_bleed": 2}
        ),
        "skill2": dict(
            name="Mark Prey",
            cost=12,
            cooldown=3,
            multiplier=1.05,
            interrupt=True,
            effects={"exposed": 3},
        ),
        "skill3": dict(
            name="Evasive Step",
            cost=14,
            cooldown=4,
            multiplier=0.45,
            guard=True,
            shield_hp=0.20,
            effects={"riposte": True},
        ),
    },
    "arcanist": {
        "skill1": dict(name="Spark Bolt", cost=16, cooldown=3, multiplier=1.85, effects={}),
        "skill2": dict(
            name="Frost Bind",
            cost=12,
            cooldown=3,
            multiplier=0.8,
            interrupt=True,
            effects={"exposed": 2, "chill": 2},
        ),
        "skill3": dict(
            name="Aether Ward",
            cost=16,
            cooldown=4,
            multiplier=0.45,
            guard=True,
            shield_hp=0.30,
            effects={},
        ),
    },
}
# Energy remains the common action budget; each class adds its own bounded mechanic.
MECHANICS = {
    "vanguard": dict(
        name="Resolve",
        cap=3,
        gain_actions=("guard", "skill3"),
        spend_action="skill1",
        damage_per_stack=0.12,
        discount_per_stack=0,
        incoming=0.95,
        crit=0,
        guard_energy=10,
        description="Guard or Iron Guard builds 1 Resolve (max 3). Cleave spends it for +12% damage per stack. Passive: take 5% less direct damage.",
    ),
    "strider": dict(
        name="Momentum",
        cap=3,
        gain_actions=(),
        spend_action=None,
        damage_per_stack=0.04,
        discount_per_stack=0,
        alternating=True,
        incoming=1,
        crit=0.03,
        guard_energy=10,
        description="Alternate damaging actions to build Momentum (max 3), gaining +4% damage per stack. Repeating an action, Guard or Potion resets it. Passive: +3 percentage points critical chance (subject to the crit cap).",
    ),
    "arcanist": dict(
        name="Aether charges",
        cap=3,
        gain_actions=("attack", "skill3"),
        spend_action="skill1",
        damage_per_stack=0.08,
        discount_per_stack=2,
        incoming=1,
        crit=0,
        guard_energy=12,
        description="Attack or Aether Ward builds 1 charge (max 3). Spark Bolt spends charges for +8% damage and 2 less energy per charge. Passive: Guard restores 12 energy instead of 10.",
    ),
}
for _cls, _skills in SKILLS.items():
    CLASSES[_cls]["skills"] = tuple(skill["name"] for skill in _skills.values())

# key, name, fixed level, region, behavior, material
_ROWS = [
    ("slime", "Lantern Slime", 1, "glimmerwood", "burst", "essence"),
    ("thornkit", "Thornkit", 2, "glimmerwood", "bleed", "fang"),
    ("wolf", "Mossfang Wolf", 3, "glimmerwood", "lunge", "fang"),
    ("moth", "Glasswing Moth", 4, "glimmerwood", "dust", "essence"),
    ("sentinel", "Rootbound Sentinel", 6, "glimmerwood", "armor", "wood"),
    ("wisp", "Wisp-Eater", 8, "glimmerwood", "absorb", "essence"),
    ("mask", "Hollow Mask", 10, "glimmerwood", "alternate", "essence"),
    ("imp", "Cinder Imp", 10, "embervein", "burn", "ember"),
    ("beetle", "Ironback Beetle", 11, "embervein", "armor", "iron"),
    ("raptor", "Ashclaw Raptor", 13, "embervein", "lunge", "fang"),
    ("leech", "Crystal Leech", 15, "embervein", "drain", "crystal"),
    ("revenant", "Forge Revenant", 17, "embervein", "heat", "iron"),
    ("ronin", "Riftbound Ronin", 19, "embervein", "counter", "crystal"),
    ("tsukara", "Tsukara, the Hollow Antler", 10, "glimmerwood", "roots", "spirit_core"),
    ("raizen", "Raizen, the Furnace Warden", 20, "embervein", "overheat", "ember_core"),
]
MONSTERS = {
    k: dict(name=n, level=level, region=r, behavior=b, material=m, boss=k in ("tsukara", "raizen"))
    for k, n, level, r, b, m in _ROWS
}
INTENTS = {
    "burst": "Charging an aether burst: guard or interrupt.",
    "bleed": "Sharpening thorns: the next strike causes bleeding.",
    "lunge": "Crouching for a heavy lunge: guard or interrupt.",
    "dust": "Gathering blinding dust: your next attack may miss.",
    "armor": "Bracing armor, then charging: interrupt or guard the charge.",
    "absorb": "Preparing to consume your barrier.",
    "alternate": "Preparing a magical strike (alternates with physical).",
    "burn": "Gathering flame: the next strike burns.",
    "drain": "Channeling a life-draining bite: interrupt it.",
    "heat": "Heating its blade: a heavy strike is coming.",
    "counter": "Watching your stance: repeating your last attack invites a counter.",
    "roots": "Gathering roots: interrupt to expose its spirit core.",
    "overheat": "Heating the furnace: guard; overheating exposes its armor.",
}
QUESTS = {
    "first_hunts": dict(name="Clear the Path", goal=3, field="wins", gold=60, xp=70),
    "guardian": dict(name="Quiet the Hollow Antler", goal=1, field="boss_wins", gold=120, xp=140),
    "trail": dict(name="Walk the Hollow Trail", goal=1, field="dungeons", gold=150, xp=180),
}


# Fixed, craftable armor collections; any class may mix sets.
GEAR_SETS = {
    "dawnward": dict(name="Dawnward Oath", bonuses={2: {"vitality": 3}, 4: {"strength": 4}}),
    "moonstep": dict(name="Moonstep Veil", bonuses={2: {"dexterity": 3}, 4: {"vitality": 4}}),
    "starweave": dict(
        name="Starweave Covenant", bonuses={2: {"intelligence": 3}, 4: {"willpower": 4}}
    ),
}
RUNES = {
    "ember": "strength",
    "gale": "dexterity",
    "aether": "intelligence",
    "stone": "vitality",
    "spirit": "willpower",
}
