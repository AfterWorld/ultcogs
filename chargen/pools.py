"""
chargen/pools.py
─────────────────────────────────────────────────────────────────────────────
All weighted RNG pools used by the character generation engine.

Structure: Every pool is Dict[str | bool, int] where the value is the
relative weight (not percentage). random.choices() handles the math.

To add/remove outcomes, edit the dicts here — the engine is data-driven
and will pick up changes automatically.
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Union

Pool = dict[Union[str, bool], int]

# ─── RACE ────────────────────────────────────────────────────────────────────
RACE: Pool = {
    "Human":      700,
    "Fishman":    100,
    "Mink":        80,
    "Giant":       40,
    "Cyborg":      30,
    "Long Leg":    20,
    "Lunarian":     8,
    "Sky Islander": 15,
    "Tontatta":    12,
    "Snakeneck":    8,
    "Three-Eye":    5,
    "Buccaneer":    3,  # Nika bloodline rarity — extremely rare
}

# ─── WILL OF D ───────────────────────────────────────────────────────────────
WILL_OF_D: Pool = {
    True:   3,   # 3% to carry the D.
    False: 97,
}

# ─── AFFILIATION ─────────────────────────────────────────────────────────────
AFFILIATION: Pool = {
    "Pirate":          55,
    "Marine":          25,
    "Revolutionary":   10,
    "Bounty Hunter":    6,
    "Cipher Pol":       3,
    "World Noble":      1,  # Extremely rare, purely cosmetic
}

# ─── DEVIL FRUIT ─────────────────────────────────────────────────────────────
HAS_DEVIL_FRUIT: Pool = {
    True:  35,
    False: 65,
}

DEVIL_FRUIT_TYPE: Pool = {
    "Paramecia":     65,
    "Zoan":          22,
    "Logia":          9,
    "Ancient Zoan":   3,
    "Mythical Zoan":  1,
}

# Canonical fruit names per type. Engine picks one from the matching bucket.
# Intentionally excludes Gomu Gomu (Nika) — that's a Legendary-tier event,
# not a roll outcome in a fair RNG pool.
DEVIL_FRUITS_BY_TYPE: dict[str, list[str]] = {
    "Paramecia": [
        "Bara Bara no Mi",     # Chop-Chop
        "Sube Sube no Mi",     # Slip-Slip
        "Bomu Bomu no Mi",     # Bomb-Bomb
        "Kilo Kilo no Mi",     # Kilo-Kilo
        "Doru Doru no Mi",     # Wax-Wax
        "Bane Bane no Mi",     # Spring-Spring
        "Noro Noro no Mi",     # Slow-Slow
        "Doa Doa no Mi",       # Door-Door
        "Awa Awa no Mi",       # Bubble-Bubble
        "Beri Beri no Mi",     # Berry-Berry
        "Sabi Sabi no Mi",     # Rust-Rust
        "Shari Shari no Mi",   # Wheel-Wheel
        "Horo Horo no Mi",     # Hollow-Hollow
        "Yomi Yomi no Mi",     # Revive-Revive
        "Kage Kage no Mi",     # Shadow-Shadow
        "Hana Hana no Mi",     # Flower-Flower
        "Mane Mane no Mi",     # Clone-Clone
        "Toki Toki no Mi",     # Time-Time
        "Ope Ope no Mi",       # Op-Op (rare Paramecia)
        "Nui Nui no Mi",       # Stitch-Stitch
        "Mochi Mochi no Mi",   # Mochi-Mochi (special Paramecia)
        "Poke Poke no Mi",     # Pocket-Pocket
        "Soru Soru no Mi",     # Soul-Soul
        "Memo Memo no Mi",     # Memo-Memo
        "Netsu Netsu no Mi",   # Heat-Heat
        "Buku Buku no Mi",     # Book-Book
        "Shibo Shibo no Mi",   # Wring-Wring
        "Sui Sui no Mi",       # Swim-Swim
        "Chiyu Chiyu no Mi",   # Heal-Heal
        "Juku Juku no Mi",     # Ripe-Ripe
        "Fuku Fuku no Mi",     # Cloth-Cloth
    ],
    "Zoan": [
        "Ushi Ushi no Mi, Model: Giraffe",
        "Ushi Ushi no Mi, Model: Bison",
        "Hito Hito no Mi",
        "Zou Zou no Mi",
        "Neko Neko no Mi, Model: Leopard",
        "Inu Inu no Mi, Model: Wolf",
        "Inu Inu no Mi, Model: Jackal",
        "Inu Inu no Mi, Model: Dachshund",
        "Tori Tori no Mi, Model: Eagle",
        "Tori Tori no Mi, Model: Falcon",
        "Hebi Hebi no Mi, Model: Anaconda",
        "Hebi Hebi no Mi, Model: King Cobra",
        "Kame Kame no Mi",
        "Sara Sara no Mi, Model: Axolotl",
        "Mushi Mushi no Mi, Model: Rhinoceros Beetle",
        "Mushi Mushi no Mi, Model: Hornet",
        "Mogu Mogu no Mi",
        "Kumo Kumo no Mi, Model: Rosamygale Grauvogeli",
    ],
    "Logia": [
        "Moku Moku no Mi",    # Smoke-Smoke
        "Mera Mera no Mi",    # Flame-Flame
        "Suna Suna no Mi",    # Sand-Sand
        "Goro Goro no Mi",    # Rumble-Rumble
        "Hie Hie no Mi",      # Ice-Ice
        "Numa Numa no Mi",    # Swamp-Swamp
        "Yami Yami no Mi",    # Dark-Dark (rare Logia)
        "Pika Pika no Mi",    # Glint-Glint
        "Magu Magu no Mi",    # Magma-Magma
        "Gasu Gasu no Mi",    # Gas-Gas
        "Yuki Yuki no Mi",    # Snow-Snow
        "Sui Sui no Mi",      # Swim-Swim (water type)
    ],
    "Ancient Zoan": [
        "Ryu Ryu no Mi, Model: Allosaurus",
        "Ryu Ryu no Mi, Model: Spinosaurus",
        "Ryu Ryu no Mi, Model: Pteranodon",
        "Ryu Ryu no Mi, Model: Brachiosaurus",
        "Ryu Ryu no Mi, Model: Pachycephalosaurus",
        "Ryu Ryu no Mi, Model: Triceratops",
        "Ryu Ryu no Mi, Model: Ankylosaurus",
        "Ryu Ryu no Mi, Model: Mammoth",
        "Ryu Ryu no Mi, Model: Saber-Toothed Tiger",
    ],
    "Mythical Zoan": [
        "Hito Hito no Mi, Model: Daibutsu",
        "Tori Tori no Mi, Model: Phoenix",
        "Inu Inu no Mi, Model: Okuchi no Makami",
        "Uma Uma no Mi, Model: Pegasus",
        "Hebi Hebi no Mi, Model: Yamata no Orochi",
        "Neko Neko no Mi, Model: Saber-Toothed Tiger",
    ],
}

# ─── HAKI ─────────────────────────────────────────────────────────────────────
HAKI_POTENTIAL: Pool = {
    "None":                          25,
    "Armament Only":                 28,
    "Observation Only":              22,
    "Armament & Observation":        18,
    "Advanced Armament":              4,
    "Advanced Observation":           2,
    "Conqueror's (All Three)":        1,
}

# ─── FIGHTING STYLE ──────────────────────────────────────────────────────────
# Affiliation-aware pools. Engine selects the right pool at generation time.
FIGHTING_STYLE_PIRATE: Pool = {
    "Swordsmanship":         20,
    "Hand-to-Hand Combat":   18,
    "Marksmanship":          15,
    "Devil Fruit Mastery":   12,
    "Electro (Mink)":         5,
    "Fish-Man Karate":        5,
    "Black Leg Style":        8,
    "Rokushiki":              6,
    "Hasshoken":              3,
    "Electro & Swordsmanship":3,
    "Sulong Combat":          3,
    "Gyojin Jujutsu":         2,
}

FIGHTING_STYLE_MARINE: Pool = {
    "Rokushiki":             30,
    "Swordsmanship":         20,
    "Marksmanship":          20,
    "Hand-to-Hand Combat":   15,
    "Seimei Kikan":           5,
    "Buster Call Tactics":    5,
    "Devil Fruit Mastery":    5,
}

FIGHTING_STYLE_REVOLUTIONARY: Pool = {
    "Hand-to-Hand Combat":   25,
    "Ryusoken":              15,
    "Swordsmanship":         20,
    "Marksmanship":          15,
    "Devil Fruit Mastery":   15,
    "Guerrilla Tactics":     10,
}

FIGHTING_STYLE_OTHER: Pool = {
    "Swordsmanship":         25,
    "Marksmanship":          25,
    "Hand-to-Hand Combat":   25,
    "Devil Fruit Mastery":   15,
    "Rokushiki":             10,
}

FIGHTING_STYLES_BY_AFFILIATION: dict[str, Pool] = {
    "Pirate":          FIGHTING_STYLE_PIRATE,
    "Marine":          FIGHTING_STYLE_MARINE,
    "Revolutionary":   FIGHTING_STYLE_REVOLUTIONARY,
    "Bounty Hunter":   FIGHTING_STYLE_OTHER,
    "Cipher Pol":      FIGHTING_STYLE_MARINE,    # Cipher Pol uses Marine-adjacent training
    "World Noble":     FIGHTING_STYLE_OTHER,
}

# ─── STAT TIERS ──────────────────────────────────────────────────────────────
STAT_TIER: Pool = {
    "F-Tier":     12,
    "D-Tier":     22,
    "C-Tier":     30,
    "B-Tier":     22,
    "A-Tier":     10,
    "S-Tier":      3,
    "Yonko-Tier":  1,
}

# ─── MARINE RANK ─────────────────────────────────────────────────────────────
MARINE_RANK: Pool = {
    "Seaman Recruit":   20,
    "Seaman First Class":15,
    "Petty Officer":    15,
    "Lieutenant":       15,
    "Commander":        12,
    "Captain":          10,
    "Commodore":         6,
    "Rear Admiral":      4,
    "Vice Admiral":      2,
    "Admiral":           1,
}

# ─── BOUNTY MULTIPLIERS (keyed by strength tier) ─────────────────────────────
# Bounty = random.randint(low, high) * multiplier  (Beri)
BOUNTY_RANGE_BY_TIER: dict[str, tuple[int, int, int]] = {
    # tier:         (low, high, multiplier)
    "F-Tier":       (1,   50,   100_000),       # 100k – 5M
    "D-Tier":       (5,   50,   1_000_000),     # 5M – 50M
    "C-Tier":       (10,  80,   5_000_000),     # 50M – 400M
    "B-Tier":       (20,  80,   10_000_000),    # 200M – 800M
    "A-Tier":       (40,  80,   20_000_000),    # 800M – 1.6B
    "S-Tier":       (80,  200,  20_000_000),    # 1.6B – 4B
    "Yonko-Tier":   (300, 600,  20_000_000),    # 6B – 12B
}

# ─── EPITHETS (cosmetic flavor, rolled independently) ─────────────────────────
EPITHETS: list[str] = [
    "the Ironclad",       "the Tempest",        "Starless",
    "the Unbroken",       "Crimson Wake",        "the Wanderer",
    "of the Deep",        "the Sovereign",       "Dawnless",
    "the Revenant",       "Black Tide",          "the Phantom",
    "the Unyielding",     "Storm Caller",        "the Forsaken",
    "of the Void",        "the Relentless",      "Sea's End",
    "the Boundless",      "the Wraith",          "Iron Will",
    "the Undying",        "Hollow Crown",        "the Ascendant",
    "the Nameless",       "World's Edge",        "the Cursed",
    "the Merciless",      "the Last Storm",      "the Dreaded",
]
