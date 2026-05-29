"""
chargen/pools.py
─────────────────────────────────────────────────────────────────────────────
All weighted RNG pools used by the character generation engine.

Structure: Every pool is Dict[str | bool, int] where the value is the
relative weight (not percentage). random.choices() handles the math.

Changelog vs v1:
  - Fixed: Sui Sui no Mi removed from Logia list (was a duplicate from Paramecia)
  - Fixed: Zoan list cleaned (Sara Sara no Mi / Axolotl is Zoan, confirmed)
  - Rebalanced: WILL_OF_D, DEVIL_FRUIT_TYPE, HAKI_POTENTIAL weights tuned
    so rare outcomes feel genuinely rare but still hittable
  - Expanded: DEVIL_FRUITS_BY_TYPE — more Paramecia and Zoan entries
  - Expanded: EPITHETS — doubled the pool
  - New: ORIGIN, WEAPON_TYPE, WEAPON_MASTERY, HAKI_MASTERY,
         DEVIL_FRUIT_MASTERY, RIVAL pools added
─────────────────────────────────────────────────────────────────────────────
"""

from typing import Union

Pool = dict[Union[str, bool], int]

# ─── RACE ─────────────────────────────────────────────────────────────────────
RACE: Pool = {
    "Human":        650,
    "Fishman":       90,
    "Mink":          75,
    "Giant":         35,
    "Cyborg":        25,
    "Long Leg":      18,
    "Sky Islander":  14,
    "Tontatta":      12,
    "Lunarian":       6,   # Rebalanced down — near-extinct in lore
    "Snakeneck":      6,
    "Three-Eye":      4,
    "Buccaneer":      2,   # Nika bloodline rarity — extremely rare
}

# ─── WILL OF D ────────────────────────────────────────────────────────────────
WILL_OF_D: Pool = {
    True:   2,   # 2% — rarer than before, matches lore scarcity
    False: 98,
}

# ─── AFFILIATION ──────────────────────────────────────────────────────────────
AFFILIATION: Pool = {
    "Pirate":          55,
    "Marine":          25,
    "Revolutionary":   10,
    "Bounty Hunter":    6,
    "Cipher Pol":       3,
    "World Noble":      1,
}

# ─── ORIGIN ───────────────────────────────────────────────────────────────────
ORIGIN: Pool = {
    "East Blue — Commoner":          18,
    "East Blue — Fisherman's Child":  8,
    "Grand Line — Island Born":      15,
    "New World — Raised in Chaos":   12,
    "Marine Family":                 10,
    "Noble Household":                8,
    "Orphan — Unknown Parentage":    10,
    "Slave — Freed or Escaped":       5,
    "Revolutionary Cell":             5,
    "Pirate Crew — Born at Sea":      5,
    "World Noble Lineage":            2,
    "Ancient Kingdom Descendant":     1,   # Extremely rare — lore-heavy
    "Void Century Bloodline":         1,
}

# ─── DEVIL FRUIT ──────────────────────────────────────────────────────────────
HAS_DEVIL_FRUIT: Pool = {
    True:  30,   # Tuned down slightly — fruit users should feel special
    False: 70,
}

DEVIL_FRUIT_TYPE: Pool = {
    "Paramecia":     60,
    "Zoan":          24,
    "Logia":          9,
    "Ancient Zoan":   5,
    "Mythical Zoan":  2,   # Up from 1 — 1-in-50 fruit users, still rare
}

DEVIL_FRUITS_BY_TYPE: dict[str, list[str]] = {
    "Paramecia": [
        "Bara Bara no Mi",       # Chop-Chop
        "Sube Sube no Mi",       # Slip-Slip
        "Bomu Bomu no Mi",       # Bomb-Bomb
        "Kilo Kilo no Mi",       # Kilo-Kilo
        "Doru Doru no Mi",       # Wax-Wax
        "Bane Bane no Mi",       # Spring-Spring
        "Noro Noro no Mi",       # Slow-Slow
        "Doa Doa no Mi",         # Door-Door
        "Awa Awa no Mi",         # Bubble-Bubble
        "Beri Beri no Mi",       # Berry-Berry
        "Sabi Sabi no Mi",       # Rust-Rust
        "Shari Shari no Mi",     # Wheel-Wheel
        "Horo Horo no Mi",       # Hollow-Hollow
        "Yomi Yomi no Mi",       # Revive-Revive
        "Kage Kage no Mi",       # Shadow-Shadow
        "Hana Hana no Mi",       # Flower-Flower
        "Mane Mane no Mi",       # Clone-Clone
        "Toki Toki no Mi",       # Time-Time
        "Ope Ope no Mi",         # Op-Op
        "Nui Nui no Mi",         # Stitch-Stitch
        "Mochi Mochi no Mi",     # Mochi-Mochi (special Paramecia)
        "Poke Poke no Mi",       # Pocket-Pocket
        "Soru Soru no Mi",       # Soul-Soul
        "Memo Memo no Mi",       # Memo-Memo
        "Netsu Netsu no Mi",     # Heat-Heat
        "Buku Buku no Mi",       # Book-Book
        "Shibo Shibo no Mi",     # Wring-Wring
        "Sui Sui no Mi",         # Swim-Swim
        "Chiyu Chiyu no Mi",     # Heal-Heal
        "Juku Juku no Mi",       # Ripe-Ripe
        "Fuku Fuku no Mi",       # Cloth-Cloth
        "Woshu Woshu no Mi",     # Wash-Wash
        "Hobi Hobi no Mi",       # Hobby-Hobby
        "Bari Bari no Mi",       # Barrier-Barrier
        "Nagi Nagi no Mi",       # Calm-Calm
        "Jake Jake no Mi",       # Jacket-Jacket
        "Pamu Pamu no Mi",       # Rupture-Rupture
        "Guru Guru no Mi",       # Spin-Spin
        "Ito Ito no Mi",         # String-String
        "Giro Giro no Mi",       # Glare-Glare
        "Oshi Oshi no Mi",       # Push-Push
        "Fura Fura no Mi",       # Waver-Waver
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
        "Tori Tori no Mi, Model: Albatross",
        "Hebi Hebi no Mi, Model: Anaconda",
        "Hebi Hebi no Mi, Model: King Cobra",
        "Kame Kame no Mi",
        "Sara Sara no Mi, Model: Axolotl",
        "Mushi Mushi no Mi, Model: Rhinoceros Beetle",
        "Mushi Mushi no Mi, Model: Hornet",
        "Mogu Mogu no Mi",
        "Kumo Kumo no Mi, Model: Rosamygale Grauvogeli",
        "Tori Tori no Mi, Model: Hawk",
        "Inu Inu no Mi, Model: Tanuki",
        "Neko Neko no Mi, Model: Tiger",
        "Ushi Ushi no Mi, Model: Bull",
        "Uma Uma no Mi",         # Horse
        "Kaba Kaba no Mi",       # Hippo
        "Awa Awa no Mi",         # Bear (non-canon placeholder)
        "Zou Zou no Mi, Model: Mammoth",
    ],
    "Logia": [
        "Moku Moku no Mi",       # Smoke-Smoke
        "Mera Mera no Mi",       # Flame-Flame
        "Suna Suna no Mi",       # Sand-Sand
        "Goro Goro no Mi",       # Rumble-Rumble (Lightning)
        "Hie Hie no Mi",         # Ice-Ice
        "Numa Numa no Mi",       # Swamp-Swamp
        "Yami Yami no Mi",       # Dark-Dark
        "Pika Pika no Mi",       # Glint-Glint (Light)
        "Magu Magu no Mi",       # Magma-Magma
        "Gasu Gasu no Mi",       # Gas-Gas
        "Yuki Yuki no Mi",       # Snow-Snow
        "Kaze Kaze no Mi",       # Wind-Wind (non-canon)
        # NOTE: Sui Sui no Mi removed — it is Paramecia, not Logia
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
        "Ryu Ryu no Mi, Model: Tyrannosaurus",
        "Ryu Ryu no Mi, Model: Archaeopteryx",
    ],
    "Mythical Zoan": [
        "Hito Hito no Mi, Model: Daibutsu",
        "Tori Tori no Mi, Model: Phoenix",
        "Inu Inu no Mi, Model: Okuchi no Makami",
        "Uma Uma no Mi, Model: Pegasus",
        "Hebi Hebi no Mi, Model: Yamata no Orochi",
        "Neko Neko no Mi, Model: Saber-Toothed Tiger",
        "Tori Tori no Mi, Model: Nue",
        "Inu Inu no Mi, Model: Raijuu",
    ],
}

# ─── DEVIL FRUIT MASTERY ──────────────────────────────────────────────────────
# Only rolled if has_devil_fruit == True
DEVIL_FRUIT_MASTERY: Pool = {
    "Awakening — Incomplete":   30,   # Just awakened, unstable
    "Novice":                   25,   # Basic transformation only
    "Proficient":               22,   # Reliable mid-combat use
    "Advanced":                 15,   # Near-mastery, creative usage
    "Supreme Mastery":           6,   # Full awakening, complete control
    "Awakening — Complete":      2,   # Peak — Doffy/Katakuri tier
}

# ─── HAKI ─────────────────────────────────────────────────────────────────────
HAKI_POTENTIAL: Pool = {
    "None":                          28,
    "Armament Only":                 25,
    "Observation Only":              20,
    "Armament & Observation":        18,
    "Advanced Armament":              5,
    "Advanced Observation":           3,
    "Conqueror's (All Three)":        1,
}

# ─── HAKI MASTERY ─────────────────────────────────────────────────────────────
# Only rolled if haki != "None"
HAKI_MASTERY: Pool = {
    "Incomplete — Still Awakening":  30,
    "Rudimentary":                   25,
    "Proficient":                    22,
    "Advanced":                      15,
    "Supreme":                        6,   # Yonko-adjacent
    "Conqueror's Infusion":           2,   # Pinnacle — Luffy/Zoro/Shanks tier
}

# ─── WEAPON TYPE ──────────────────────────────────────────────────────────────
WEAPON_TYPE: Pool = {
    "Sword":              25,
    "Dual Blades":        12,
    "Three-Sword Style":   3,   # Rare — Zoro-style
    "Spear / Naginata":   12,
    "Staff / Kanabō":      8,
    "Pistol / Flintlock": 10,
    "Rifle / Musket":      8,
    "Trident":             6,
    "Knuckles / Claws":    8,
    "Scythe":              4,
    "No Weapon — Bare Hands": 4,
}

# ─── WEAPON MASTERY ───────────────────────────────────────────────────────────
WEAPON_MASTERY: Pool = {
    "Untrained":    15,
    "Novice":       25,
    "Competent":    28,
    "Expert":       20,
    "Master":        9,
    "Legendary":     3,   # Mihawk / Vista tier
}

# ─── FIGHTING STYLE ───────────────────────────────────────────────────────────
FIGHTING_STYLE_PIRATE: Pool = {
    "Swordsmanship":              20,
    "Hand-to-Hand Combat":        18,
    "Marksmanship":               15,
    "Devil Fruit Mastery":        12,
    "Electro (Mink)":              5,
    "Fish-Man Karate":             5,
    "Black Leg Style":             8,
    "Rokushiki":                   6,
    "Hasshoken":                   3,
    "Electro & Swordsmanship":     3,
    "Sulong Combat":               3,
    "Gyojin Jujutsu":              2,
}

FIGHTING_STYLE_MARINE: Pool = {
    "Rokushiki":              30,
    "Swordsmanship":          20,
    "Marksmanship":           20,
    "Hand-to-Hand Combat":    15,
    "Seimei Kikan":            5,
    "Buster Call Tactics":     5,
    "Devil Fruit Mastery":     5,
}

FIGHTING_STYLE_REVOLUTIONARY: Pool = {
    "Hand-to-Hand Combat":    25,
    "Ryusoken":               15,
    "Swordsmanship":          20,
    "Marksmanship":           15,
    "Devil Fruit Mastery":    15,
    "Guerrilla Tactics":      10,
}

FIGHTING_STYLE_OTHER: Pool = {
    "Swordsmanship":          25,
    "Marksmanship":           25,
    "Hand-to-Hand Combat":    25,
    "Devil Fruit Mastery":    15,
    "Rokushiki":              10,
}

FIGHTING_STYLES_BY_AFFILIATION: dict[str, Pool] = {
    "Pirate":         FIGHTING_STYLE_PIRATE,
    "Marine":         FIGHTING_STYLE_MARINE,
    "Revolutionary":  FIGHTING_STYLE_REVOLUTIONARY,
    "Bounty Hunter":  FIGHTING_STYLE_OTHER,
    "Cipher Pol":     FIGHTING_STYLE_MARINE,
    "World Noble":    FIGHTING_STYLE_OTHER,
}

# ─── STAT TIERS ───────────────────────────────────────────────────────────────
# Used for: strength, speed, battle_iq, endurance, willpower
STAT_TIER: Pool = {
    "F-Tier":      10,
    "D-Tier":      20,
    "C-Tier":      32,
    "B-Tier":      24,
    "A-Tier":      10,
    "S-Tier":       3,
    "Yonko-Tier":   1,
}

# ─── MARINE RANK ──────────────────────────────────────────────────────────────
MARINE_RANK: Pool = {
    "Seaman Recruit":      20,
    "Seaman First Class":  15,
    "Petty Officer":       15,
    "Lieutenant":          15,
    "Commander":           12,
    "Captain":             10,
    "Commodore":            6,
    "Rear Admiral":         4,
    "Vice Admiral":         2,
    "Admiral":              1,
}

# ─── BOUNTY RANGES (keyed by strength tier) ───────────────────────────────────
# bounty = random.randint(low, high) * multiplier  (Beri)
BOUNTY_RANGE_BY_TIER: dict[str, tuple[int, int, int]] = {
    "F-Tier":       (1,   50,    100_000),    # 100k – 5M
    "D-Tier":       (5,   50,  1_000_000),    # 5M – 50M
    "C-Tier":       (10,  80,  5_000_000),    # 50M – 400M
    "B-Tier":       (20,  80, 10_000_000),    # 200M – 800M
    "A-Tier":       (40,  80, 20_000_000),    # 800M – 1.6B
    "S-Tier":       (80, 200, 20_000_000),    # 1.6B – 4B
    "Yonko-Tier":  (300, 600, 20_000_000),    # 6B – 12B
}

# ─── RIVAL (canon manga characters) ───────────────────────────────────────────
# Weighted so encountering a top-tier rival is rare but possible.
# Grouped loosely by power tier — higher weight = more common rival.
RIVAL: Pool = {
    # ── Approachable / East Blue tier ──────────────────────────────────────
    "Coby":                  10,
    "Helmeppo":               9,
    "Tashigi":               10,
    "Smoker":                 9,
    "Fullbody":               8,
    "Jango":                  7,
    "Django":                 7,

    # ── Supernovas / Rising threats ────────────────────────────────────────
    "Roronoa Zoro":           8,
    "Trafalgar Law":          8,
    "Eustass Kid":            8,
    "Killer":                 7,
    "Capone Bege":            7,
    "Jewelry Bonney":         7,
    "Basil Hawkins":          6,
    "X Drake":                6,
    "Scratchmen Apoo":        6,
    "Urouge":                 5,

    # ── Warlord / Warlord-Adjacent ─────────────────────────────────────────
    "Bartholomew Kuma":       5,
    "Gecko Moria":            5,
    "Donquixote Doflamingo":  5,
    "Boa Hancock":            5,
    "Crocodile":              6,
    "Buggy":                  6,

    # ── New World commanders ───────────────────────────────────────────────
    "Marco the Phoenix":      4,
    "Vista":                  4,
    "King":                   3,
    "Queen":                  3,
    "Jack":                   3,
    "Katakuri":               3,
    "Smoothie":               3,
    "Cracker":                3,
    "Perospero":              4,

    # ── Revolutionary Army ─────────────────────────────────────────────────
    "Sabo":                   4,
    "Koala":                  4,
    "Belo Betty":             3,
    "Morley":                 3,

    # ── Admirals / Fleet Admiral ───────────────────────────────────────────
    "Fujitora":               2,
    "Ryokugyu":               2,
    "Kizaru":                 2,
    "Aokiji":                 2,
    "Akainu":                 1,
    "Sengoku":                1,

    # ── Yonko tier — rarest rivals ────────────────────────────────────────
    "Shanks":                 1,
    "Dracule Mihawk":         1,
    "Silvers Rayleigh":       1,
    "Monkey D. Garp":         1,
    "Monkey D. Dragon":       1,
    "Whitebeard (Legacy)":    1,
    "Big Mom":                1,
    "Kaido (Legend)":         1,
}

# ─── EPITHETS ─────────────────────────────────────────────────────────────────
EPITHETS: list[str] = [
    # Original set
    "the Ironclad",       "the Tempest",          "Starless",
    "the Unbroken",       "Crimson Wake",          "the Wanderer",
    "of the Deep",        "the Sovereign",         "Dawnless",
    "the Revenant",       "Black Tide",            "the Phantom",
    "the Unyielding",     "Storm Caller",          "the Forsaken",
    "of the Void",        "the Relentless",        "Sea's End",
    "the Boundless",      "the Wraith",            "Iron Will",
    "the Undying",        "Hollow Crown",          "the Ascendant",
    "the Nameless",       "World's Edge",          "the Cursed",
    "the Merciless",      "the Last Storm",        "the Dreaded",
    # Expanded set
    "of the Scarlet Sea",  "the Void Walker",      "Tidecaller",
    "the Uncharted",       "Bloodless",            "the Pale Horizon",
    "of the Ember Coast",  "the Ruinous",          "Graveless",
    "the Unclaimed",       "Ashborn",              "the Broken Bell",
    "of Black Sails",      "the Immovable",        "Sandstorm",
    "the Colossus",        "the Pale King",        "Rimefang",
    "the Forgotten",       "First Tide",           "Last Ember",
    "the Unmoved",         "Galeforce",            "the Branded",
    "the Exiled",          "Coldwater",            "the Ravager",
    "Stormblind",          "the Unlit",            "the Iron Tide",
]