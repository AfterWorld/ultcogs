"""Original bounded item tiers, names and encounter-specific loot tables."""

import hashlib
import random

RARITIES = {
    "common": dict(rank=1, level=1, color=0xAAB2BD, icon="⚪"),
    "uncommon": dict(rank=2, level=1, color=0x48C774, icon="🟢"),
    "rare": dict(rank=3, level=3, color=0x4D9FFF, icon="🔵"),
    "epic": dict(rank=4, level=6, color=0xB66DFF, icon="🟣"),
    "legendary": dict(rank=5, level=10, color=0xFFAA33, icon="🟠"),
    "mythic": dict(rank=6, level=16, color=0xF05B78, icon="🔴"),
    "unique": dict(rank=4, level=1, color=0xE8C66A, icon="🌟"),
}
BASE_NAMES = {
    "main": ("Dawnsteel Blade", "Moonpiercer", "Stormglass Staff"),
    "off": ("Lantern Aegis", "Jade Ward", "Spiritglass Focus"),
    "head": ("Starwoven Hood", "Duskguard Helm", "Moonveil Circlet"),
    "chest": ("Dawnwarden Coat", "Mistweave Robe", "Skyforged Cuirass"),
    "hands": ("Embergrip Gloves", "Cloudstep Wraps", "Starsteel Gauntlets"),
    "legs": ("Duskwalker Leggings", "Moonthread Greaves", "Riftguard Tassets"),
    "feet": ("Windchaser Boots", "Silentstep Sandals", "Ashwalker Sabatons"),
    "neck": ("Lanternkeeper Pendant", "Azure Oath", "Stardrop Amulet"),
    "ring1": ("Moonlit Signet", "Dawnfire Band", "Whispering Halo"),
    "ring2": ("Moonlit Signet", "Dawnfire Band", "Whispering Halo"),
    "relic": ("Echo of Hoshifall", "Lanternheart Charm", "Skyshard Compass"),
}
EPITHETS = ("Resolve", "the Wandering Star", "Still Waters", "First Light", "the Silent Sky")
BOSS_DROPS = {
    "tsukara": (
        ("neck", "Hollow Antler Pendant"),
        ("off", "Rootsong Aegis"),
        ("chest", "Moonbark Mantle"),
    ),
    "raizen": (
        ("main", "Furnace Warden's Edge"),
        ("hands", "Cinderlord Grasp"),
        ("feet", "Crucible Striders"),
    ),
}
UNIQUES = {
    "slime": dict(slot="relic", name="Lantern Slime's Heart", effect="wayfarer"),
    "wolf": dict(slot="feet", name="Mossfang's Silent Step", effect="spiritward"),
    "mask": dict(slot="head", name="Face of the Lost Moon", effect="spiritward"),
    "ronin": dict(slot="main", name="Last Oath of the Rift", effect="emberblade"),
    "tsukara": dict(slot="relic", name="Tsukara's Living Antler", effect="spiritward"),
    "raizen": dict(slot="main", name="Raizen's Final Ember", effect="emberblade"),
}


def item_name(slot, rarity, seed):
    # Naming never consumes combat/item RNG or changes a saved item's stats.
    rng = random.Random(hashlib.sha256(str(seed).encode()).digest())
    base = rng.choice(BASE_NAMES[slot])
    return base if rarity in ("common", "uncommon") else f"{base} of {rng.choice(EPITHETS)}"


def migrate_names(p):
    for i in p["inventory"].values():
        if i["name"] == f"{i['rarity'].title()} {i['slot'].title()} of Hoshifall":
            i["name"] = item_name(i["slot"], i["rarity"], i["id"])
        for boss in BOSS_DROPS:
            if i["name"] == f"{boss.title()} {i['slot'].title()}":
                i["name"] = f"{boss.title()}'s {BASE_NAMES[i['slot']][0]}"


def rarity_label(rarity):
    return RARITIES[rarity]["icon"]


def roll_rarity(level, boss, rng):
    tiers = list(RARITIES)[:-1]
    weights = [500, 2000, 4000, 2500, 850, 150] if boss else [6000, 2600, 1000, 320, 70, 10]
    for n, tier in enumerate(tiers):
        if level < RARITIES[tier]["level"]:
            weights[0] += weights[n]
            weights[n] = 0
    return rng.choices(tiers, weights=weights)[0]
