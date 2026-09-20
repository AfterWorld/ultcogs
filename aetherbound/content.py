"""Versioned Phase 1 content. Numbers are provisional, bounded, and testable."""

SLOTS = ("main", "off", "head", "chest", "hands", "legs", "feet", "neck", "ring1", "ring2", "relic")
ATTRS = ("strength", "dexterity", "intelligence", "vitality", "willpower")
CLASSES = {
    "vanguard": {
        "stat": "strength",
        "weapon": "Iron Sword",
        "skills": ("Cleave", "Guard Break", "Iron Guard"),
    },
    "strider": {
        "stat": "dexterity",
        "weapon": "Twin Fang",
        "skills": ("Twin Strike", "Mark Prey", "Evasive Step"),
    },
    "arcanist": {
        "stat": "intelligence",
        "weapon": "Aether Staff",
        "skills": ("Spark Bolt", "Frost Bind", "Aether Ward"),
    },
}
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
TUTORIAL = (
    "Welcome to Hoshifall! Your soul resonates with the shattered sky. Open inventory and equip your starter main-hand weapon: aether equip <item-id>. Gear stays with you between sessions.",
    "Practice combat: aether practice. Use Attack, Guard, and at least one Skill, then win. Read the enemy intent; guarding a charged strike reduces damage. Skills cost energy and have turn cooldowns.",
    "Your training earned an armor kit and forging materials. Equip the chest piece. Profile shows your total stats; item shows individual bonuses. Equip the other pieces too!",
    "Visit the forge: aether forge ring1. Forging consumes materials and gold; recipes show the cost. Salvaging unwanted gear returns materials. Early upgrades cannot destroy gear.",
    "Equip your newly forged ring with aether equip <item-id>. Rings have separate slots. Gear is locked during combat so changing equipment cannot reset your health.",
    "Explore Glimmerwood and win a real hunt: aether explore glimmerwood. Encounters award EXP, gold, materials and loot. Trivial enemies give reduced rewards. Use aether resume after a restart.",
    "Tutorial complete! You earned a Wayfarer relic, 100 gold and two potions. Equip the relic, inspect quests, and tackle the Hollow Trail dungeon at level 6. Notification roles are optional; trade offers belong in the market, discussion in their threads.",
)
QUESTS = {
    "first_hunts": dict(name="Clear the Path", goal=3, field="wins", gold=60, xp=70),
    "guardian": dict(name="Quiet the Hollow Antler", goal=1, field="boss_wins", gold=120, xp=140),
    "trail": dict(name="Walk the Hollow Trail", goal=1, field="dungeons", gold=150, xp=180),
}
