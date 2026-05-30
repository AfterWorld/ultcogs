"""
chargen/pools.py
─────────────────────────────────────────────────────────────────────────────
All weighted RNG pools used by the character generation engine.

Changelog vs v2:
  - Added: RIVAL_LORE dict — short flavor blurbs per rival for the
    "View Rival" button ephemeral. Keyed to match RIVAL pool exactly.
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
    "Lunarian":       6,
    "Snakeneck":      6,
    "Three-Eye":      4,
    "Buccaneer":      2,
}

# ─── WILL OF D ────────────────────────────────────────────────────────────────
WILL_OF_D: Pool = {
    True:   2,
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
    "East Blue — Commoner":           18,
    "East Blue — Fisherman's Child":   8,
    "Grand Line — Island Born":       15,
    "New World — Raised in Chaos":    12,
    "Marine Family":                  10,
    "Noble Household":                 8,
    "Orphan — Unknown Parentage":     10,
    "Slave — Freed or Escaped":        5,
    "Revolutionary Cell":              5,
    "Pirate Crew — Born at Sea":       5,
    "World Noble Lineage":             2,
    "Ancient Kingdom Descendant":      1,
    "Void Century Bloodline":          1,
}

# ─── DEVIL FRUIT ──────────────────────────────────────────────────────────────
HAS_DEVIL_FRUIT: Pool = {
    True:  30,
    False: 70,
}

DEVIL_FRUIT_TYPE: Pool = {
    "Paramecia":     60,
    "Zoan":          24,
    "Logia":          9,
    "Ancient Zoan":   5,
    "Mythical Zoan":  2,
}

DEVIL_FRUITS_BY_TYPE: dict[str, list[str]] = {
    "Paramecia": [
        "Bara Bara no Mi", "Sube Sube no Mi", "Bomu Bomu no Mi",
        "Kilo Kilo no Mi", "Doru Doru no Mi", "Bane Bane no Mi",
        "Noro Noro no Mi", "Doa Doa no Mi",   "Awa Awa no Mi",
        "Beri Beri no Mi", "Sabi Sabi no Mi", "Shari Shari no Mi",
        "Horo Horo no Mi", "Yomi Yomi no Mi", "Kage Kage no Mi",
        "Hana Hana no Mi", "Mane Mane no Mi", "Toki Toki no Mi",
        "Ope Ope no Mi",   "Nui Nui no Mi",   "Mochi Mochi no Mi",
        "Poke Poke no Mi", "Soru Soru no Mi", "Memo Memo no Mi",
        "Netsu Netsu no Mi","Buku Buku no Mi", "Shibo Shibo no Mi",
        "Sui Sui no Mi",   "Chiyu Chiyu no Mi","Juku Juku no Mi",
        "Fuku Fuku no Mi", "Woshu Woshu no Mi","Hobi Hobi no Mi",
        "Bari Bari no Mi", "Nagi Nagi no Mi",  "Jake Jake no Mi",
        "Pamu Pamu no Mi", "Guru Guru no Mi",  "Ito Ito no Mi",
        "Giro Giro no Mi", "Oshi Oshi no Mi",  "Fura Fura no Mi",
    ],
    "Zoan": [
        "Ushi Ushi no Mi, Model: Giraffe",
        "Ushi Ushi no Mi, Model: Bison",
        "Ushi Ushi no Mi, Model: Bull",
        "Hito Hito no Mi",
        "Zou Zou no Mi",
        "Neko Neko no Mi, Model: Leopard",
        "Neko Neko no Mi, Model: Tiger",
        "Inu Inu no Mi, Model: Wolf",
        "Inu Inu no Mi, Model: Jackal",
        "Inu Inu no Mi, Model: Dachshund",
        "Inu Inu no Mi, Model: Tanuki",
        "Tori Tori no Mi, Model: Eagle",
        "Tori Tori no Mi, Model: Falcon",
        "Tori Tori no Mi, Model: Hawk",
        "Tori Tori no Mi, Model: Albatross",
        "Hebi Hebi no Mi, Model: Anaconda",
        "Hebi Hebi no Mi, Model: King Cobra",
        "Kame Kame no Mi",
        "Sara Sara no Mi, Model: Axolotl",
        "Mushi Mushi no Mi, Model: Rhinoceros Beetle",
        "Mushi Mushi no Mi, Model: Hornet",
        "Mogu Mogu no Mi",
        "Kumo Kumo no Mi, Model: Rosamygale Grauvogeli",
        "Uma Uma no Mi",
        "Kaba Kaba no Mi",
        "Zou Zou no Mi, Model: Mammoth",
    ],
    "Logia": [
        "Moku Moku no Mi",
        "Mera Mera no Mi",
        "Suna Suna no Mi",
        "Goro Goro no Mi",
        "Hie Hie no Mi",
        "Numa Numa no Mi",
        "Yami Yami no Mi",
        "Pika Pika no Mi",
        "Magu Magu no Mi",
        "Gasu Gasu no Mi",
        "Yuki Yuki no Mi",
        "Kaze Kaze no Mi",
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
DEVIL_FRUIT_MASTERY: Pool = {
    "Awakening — Incomplete":  30,
    "Novice":                  25,
    "Proficient":              22,
    "Advanced":                15,
    "Supreme Mastery":          6,
    "Awakening — Complete":     2,
}

# ─── HAKI ─────────────────────────────────────────────────────────────────────
HAKI_POTENTIAL: Pool = {
    "None":                         28,
    "Armament Only":                25,
    "Observation Only":             20,
    "Armament & Observation":       18,
    "Advanced Armament":             5,
    "Advanced Observation":          3,
    "Conqueror's (All Three)":       1,
}

# ─── HAKI MASTERY ─────────────────────────────────────────────────────────────
HAKI_MASTERY: Pool = {
    "Incomplete — Still Awakening":  30,
    "Rudimentary":                   25,
    "Proficient":                    22,
    "Advanced":                      15,
    "Supreme":                        6,
    "Conqueror's Infusion":           2,
}

# ─── WEAPON TYPE ──────────────────────────────────────────────────────────────
WEAPON_TYPE: Pool = {
    "Sword":                   25,
    "Dual Blades":             12,
    "Three-Sword Style":        3,
    "Spear / Naginata":        12,
    "Staff / Kanabō":           8,
    "Pistol / Flintlock":      10,
    "Rifle / Musket":           8,
    "Trident":                  6,
    "Knuckles / Claws":         8,
    "Scythe":                   4,
    "No Weapon — Bare Hands":   4,
}

# ─── WEAPON MASTERY ───────────────────────────────────────────────────────────
WEAPON_MASTERY: Pool = {
    "Untrained":   15,
    "Novice":      25,
    "Competent":   28,
    "Expert":      20,
    "Master":       9,
    "Legendary":    3,
}

# ─── FIGHTING STYLE ───────────────────────────────────────────────────────────
FIGHTING_STYLE_PIRATE: Pool = {
    "Swordsmanship":             20,
    "Hand-to-Hand Combat":       18,
    "Marksmanship":              15,
    "Devil Fruit Mastery":       12,
    "Electro (Mink)":             5,
    "Fish-Man Karate":            5,
    "Black Leg Style":            8,
    "Rokushiki":                  6,
    "Hasshoken":                  3,
    "Electro & Swordsmanship":    3,
    "Sulong Combat":              3,
    "Gyojin Jujutsu":             2,
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
    "Pirate":         FIGHTING_STYLE_PIRATE,
    "Marine":         FIGHTING_STYLE_MARINE,
    "Revolutionary":  FIGHTING_STYLE_REVOLUTIONARY,
    "Bounty Hunter":  FIGHTING_STYLE_OTHER,
    "Cipher Pol":     FIGHTING_STYLE_MARINE,
    "World Noble":    FIGHTING_STYLE_OTHER,
}

# ─── STAT TIERS ───────────────────────────────────────────────────────────────
STAT_TIER: Pool = {
    "F-Tier":      10,
    "D-Tier":      20,
    "C-Tier":      32,
    "B-Tier":      24,
    "A-Tier":      10,
    "S-Tier":       3,
    "Yonko-Tier":   1,
}

# Numeric value per tier — used for loading bar rendering
STAT_TIER_VALUE: dict[str, int] = {
    "F-Tier":      5,
    "D-Tier":     18,
    "C-Tier":     38,
    "B-Tier":     58,
    "A-Tier":     75,
    "S-Tier":     90,
    "Yonko-Tier": 100,
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

# ─── BOUNTY RANGES ────────────────────────────────────────────────────────────
BOUNTY_RANGE_BY_TIER: dict[str, tuple[int, int, int]] = {
    "F-Tier":      (1,   50,    100_000),
    "D-Tier":      (5,   50,  1_000_000),
    "C-Tier":      (10,  80,  5_000_000),
    "B-Tier":      (20,  80, 10_000_000),
    "A-Tier":      (40,  80, 20_000_000),
    "S-Tier":      (80, 200, 20_000_000),
    "Yonko-Tier": (300, 600, 20_000_000),
}

# ─── RIVAL ────────────────────────────────────────────────────────────────────
RIVAL: Pool = {
    "Coby": 10, "Helmeppo": 9, "Tashigi": 10, "Smoker": 9,
    "Fullbody": 8, "Jango": 7, "Django": 7,
    "Roronoa Zoro": 8, "Trafalgar Law": 8, "Eustass Kid": 8,
    "Killer": 7, "Capone Bege": 7, "Jewelry Bonney": 7,
    "Basil Hawkins": 6, "X Drake": 6, "Scratchmen Apoo": 6, "Urouge": 5,
    "Bartholomew Kuma": 5, "Gecko Moria": 5, "Donquixote Doflamingo": 5,
    "Boa Hancock": 5, "Crocodile": 6, "Buggy": 6,
    "Marco the Phoenix": 4, "Vista": 4,
    "King": 3, "Queen": 3, "Jack": 3,
    "Katakuri": 3, "Smoothie": 3, "Cracker": 3, "Perospero": 4,
    "Sabo": 4, "Koala": 4, "Belo Betty": 3, "Morley": 3,
    "Fujitora": 2, "Ryokugyu": 2, "Kizaru": 2, "Aokiji": 2,
    "Akainu": 1, "Sengoku": 1,
    "Shanks": 1, "Dracule Mihawk": 1, "Silvers Rayleigh": 1,
    "Monkey D. Garp": 1, "Monkey D. Dragon": 1,
    "Whitebeard (Legacy)": 1, "Big Mom": 1, "Kaido (Legend)": 1,
}

# ─── RIVAL LORE ───────────────────────────────────────────────────────────────
# Short flavor blurb per rival. Used by the "View Rival" button ephemeral.
RIVAL_LORE: dict[str, str] = {
    "Coby": (
        "A Marine recruit who dared dream beyond his station. Once a terrified cabin boy "
        "to Alvida, Coby's sheer willpower unlocked Observation Haki mid-battle at Marineford. "
        "The World Government watches his rise with cautious interest."
    ),
    "Helmeppo": (
        "Son of the disgraced Captain Morgan, Helmeppo shed his cowardice under Vice Admiral "
        "Garp's brutal training. What he lacks in raw power he compensates with twin kukri "
        "precision and an unshakable loyalty to Coby."
    ),
    "Tashigi": (
        "A Marine swordsman with encyclopedic knowledge of named blades and zero tolerance "
        "for injustice. Her resemblance to Kuina is a wound Zoro has never fully addressed. "
        "She fights not for the institution, but for what justice should mean."
    ),
    "Smoker": (
        "The White Hunter. A Vice Admiral who operates on principle rather than order, "
        "Smoker's Logia smoke powers and Seastone jutte make him a nightmare for Devil Fruit "
        "users. He chases Luffy not out of duty — but because something about that crew "
        "refuses to let him look away."
    ),
    "Fullbody": "A Marine lieutenant humiliated by Sanji at the Baratie. Has never quite recovered his dignity.",
    "Jango": "Former Black Cat Pirates hypnotist, now a bumbling Marine. His moonwalk is somehow still impressive.",
    "Django": "A hypnotist-for-hire turned Marine. Best known for his chakram and his absolute devotion to Fullbody.",
    "Roronoa Zoro": (
        "The Pirate Hunter. First mate of the Straw Hats and the world's second-greatest swordsman — "
        "for now. Every scar on his body is a debt paid toward the promise he made to a dead girl "
        "on a winter island. He will surpass Mihawk, or die having meant it."
    ),
    "Trafalgar Law": (
        "The Surgeon of Death. Warlord-turned-Revolutionary, Law's Ope Ope no Mi grants him "
        "absolute spatial dominance within his ROOM. Cold, calculating, and driven by a vendetta "
        "against Donquixote Doflamingo that cost him his entire childhood."
    ),
    "Eustass Kid": (
        "Most wanted of the Supernovas at Sabaody. Kid's Jiki Jiki no Mi magnetism and savage "
        "tenacity make him one of the New World's most dangerous rising threats. He doesn't "
        "form alliances — he tolerates them."
    ),
    "Killer": (
        "Kid's right hand and the only Supernova without a Devil Fruit. Twin scythe-bladed "
        "tonfa, Haki, and a fighting style built for carnage. The laugh forced on him by "
        "Kaido's crew left a mark, but didn't break him."
    ),
    "Capone Bege": (
        "Godfather of the sea. Bege's Shiro Shiro no Mi turns him into a walking fortress "
        "and tactical command center. He survived the Charlotte Family's inner circle long "
        "enough to try to assassinate Big Mom herself. Almost worked."
    ),
    "Jewelry Bonney": (
        "The Big Eater. Bonney's age-manipulation Paramecia is more dangerous than it appears — "
        "she carries secrets about the Void Century and a personal connection to Bartholomew Kuma "
        "that the World Government would kill to keep buried."
    ),
    "Basil Hawkins": (
        "The Magician. Hawkins' straw doll powers redirect damage to others, making him nearly "
        "impossible to permanently harm in direct combat. He reads fate without emotion and "
        "accepts its conclusions — even unfavorable ones."
    ),
    "X Drake": (
        "Marine Rear Admiral turned pirate turned SWORD agent. Drake's Ancient Zoan Allosaurus "
        "form is brutally efficient. His true loyalties have shifted so many times even he "
        "seems unsure which version of himself he's currently running."
    ),
    "Scratchmen Apoo": (
        "The Roar of the Sea. Apoo's body is a living instrument — his Oto Oto no Mi turns "
        "sound into ranged physical attacks that hit before the target can react. His opportunism "
        "rivals his rhythm."
    ),
    "Urouge": (
        "The Mad Monk. Urouge's Paramecia converts received damage into raw strength, making "
        "him more dangerous the harder you hit him. He defeated a Sweet Commander and somehow "
        "lived to retire to a Sky Island. The least-understood Supernova."
    ),
    "Bartholomew Kuma": (
        "The Tyrant. A former Revolutionary turned Warlord turned full Pacifista, Kuma's "
        "Nikyu Nikyu no Mi can repel anything — including pain, fatigue, and people. "
        "The man beneath the machine died in pieces, one memory at a time, under Vegapunk's "
        "hands. What remains protects the Thousand Sunny out of a loyalty no one ordered."
    ),
    "Gecko Moria": (
        "The Archipelago Lord. Moria's Kage Kage no Mi army of shadows and zombies made "
        "Thriller Bark a moving graveyard nation. His defeat by Luffy didn't end him — "
        "it just changed his coordinates."
    ),
    "Donquixote Doflamingo": (
        "The Heavenly Demon. Doflamingo's Ito Ito no Mi gives him strings strong enough to "
        "slice stone and puppet anyone, living or dead. A Celestial Dragon by birth who burned "
        "his noble blood and carved a kingdom from fear. The birdcage was just him being honest "
        "about what power always does."
    ),
    "Boa Hancock": (
        "The Pirate Empress. Hancock's Mero Mero no Mi petrifies anyone who feels desire toward "
        "her — which is functionally everyone. She ruled Calm Belt, was a Warlord, and "
        "punched a Pacifista to powder mid-kick. She is also, inconveniently, in love."
    ),
    "Crocodile": (
        "The Desert King. Crocodile's Suna Suna no Mi once made him near-invincible until "
        "Luffy figured out water and blood. His Alabasta scheme collapsed, but he survived "
        "Impel Down, Marineford, and whatever came after — always landing on his feet, "
        "hook gleaming."
    ),
    "Buggy": (
        "The Star Clown. Buggy's Bara Bara no Mi makes him immune to slashing and lets him "
        "detach and fly his parts. His actual power ceiling is modest. His luck and reputation "
        "are not. He has survived every catastrophe through a combination of cowardice, "
        "charisma, and the universe apparently not being done with him yet."
    ),
    "Marco the Phoenix": (
        "Former First Division Commander of the Whitebeard Pirates. Marco's Mythical Zoan "
        "Phoenix fruit grants regenerative blue flames that heal almost any wound. He held "
        "two Admirals at bay at Marineford and kept fighting. He farms pineapples now, "
        "but the fire didn't go out."
    ),
    "Vista": (
        "The Flower Sword. Fifth Division Commander under Whitebeard and one of the world's "
        "elite swordsmen. Even Mihawk acknowledged clashing blades with him at Marineford. "
        "That is not a small thing."
    ),
    "King": (
        "The Wildfire. Kaido's right hand and a Lunarian — a race the World Government "
        "thought they'd erased. King's fire immunity, flight, and mastery of his Ancient "
        "Zoan Pteranodon make him one of the most physically overwhelming fighters alive. "
        "His real name is Alber."
    ),
    "Queen": (
        "The Plague. All-Star of the Beast Pirates and a former MADS scientist. Queen's "
        "Ancient Zoan Brachiosaurus form, cyborg modifications, and biological weapons "
        "development make him as dangerous in a lab as on a battlefield. He is also "
        "inexplicably committed to his musical career."
    ),
    "Jack": (
        "The Drought. A Disaster of the Beast Pirates. Jack's Ancient Zoan Mammoth form "
        "is pure overwhelming force — he laid siege to Zunesha for five days straight "
        "while the rest of his crew was being defeated elsewhere. He does not stop."
    ),
    "Katakuri": (
        "The Oven's Edge. Charlotte Katakuri has never lost a fight and never been made to "
        "lie on his back — until Luffy. His special Paramecia Mochi fruit and advanced "
        "Future Sight Haki made him the strongest Sweet Commander. The scar on his face "
        "is the only honest thing about him."
    ),
    "Smoothie": (
        "The Wring-Wring. Charlotte Smoothie's Shibo Shibo no Mi lets her wring the liquid "
        "from anything — people included. Third-ranked Sweet Commander. She grew to the "
        "size of Whole Cake Island's towers during the escape arc and almost stopped the "
        "Thousand Sunny with a single tidal wave of wrung seawater."
    ),
    "Cracker": (
        "The Thousand Arms. Charlotte Cracker's Bisu Bisu no Mi generates infinite hardened "
        "biscuit soldiers — each one tough enough to stop Gear Fourth Luffy. He fought "
        "for eleven hours. It took Nami's rain and an unfair amount of eating to end it."
    ),
    "Perospero": (
        "The Lick-Lick. Charlotte Perospero's candy constructs are more dangerous than they "
        "sound — he encased an entire fleet in hardened sweets at Marineford-scale events "
        "and survived everything thrown at him with sardonic commentary intact."
    ),
    "Sabo": (
        "The Revolutionary Chief of Staff and Luffy's sworn brother. Sabo inherited Ace's "
        "Mera Mera no Mi at Dressrosa and burns with everything that fruit means. Second "
        "in command to Dragon, first in Luffy's heart after Ace. The world thought he was "
        "dead for a decade. The world was wrong."
    ),
    "Koala": (
        "Fish-Man Karate officer of the Revolutionary Army. Koala's past as a freed slave "
        "shaped her entirely. She fights with precision, trains recruits with Sabo's "
        "intensity, and carries a warmth that survived things that should have killed it."
    ),
    "Belo Betty": (
        "Commander of the East Army, Revolutionary. Betty's Kobu Kobu no Mi flags inspire "
        "ordinary people to fight beyond their limits — she calls it the most powerful "
        "ability in the world and might be right. She prefers watching others rise."
    ),
    "Morley": (
        "Commander of the West Army, Revolutionary. Morley's Oshi Oshi no Mi reshapes "
        "earth like clay. They carved Newkama Land into the bedrock of Impel Down Level 5.5 "
        "with bare hands and existential determination."
    ),
    "Fujitora": (
        "The Blind Swordsman. Admiral Issho chose blindness to avoid seeing the ugliness "
        "of the world he enforces. His Zushi Zushi no Mi controls gravity — he dropped "
        "meteorites, levitated an entire harbor, and dragged a Marine fleet over land. "
        "He spent three years trying to apologize to Dressrosa."
    ),
    "Ryokugyu": (
        "The Green Bull. Admiral Aramaki's Mori Mori no Mi turns him into a walking forest — "
        "he can drain the life force from anyone he ensnares and hasn't eaten in three years "
        "because he doesn't need to. New World ambitions, no patience for mercy."
    ),
    "Kizaru": (
        "The Light Admiral. Borsalino's Pika Pika no Mi makes him the fastest being alive — "
        "he moves, attacks, and thinks at the speed of light. His relaxed demeanor is not "
        "laziness. It is the comfort of someone who knows nothing can outrun him."
    ),
    "Aokiji": (
        "The Ice Admiral. Kuzan's Hie Hie no Mi froze half of Punk Hazard in a duel that "
        "lasted ten days. He resigned rather than serve under Akainu, spent years adrift, "
        "and emerged aligned with Blackbeard for reasons the world doesn't fully understand yet."
    ),
    "Akainu": (
        "The Fleet Admiral. Sakazuki's Magu Magu no Mi — the most offensive Logia in "
        "existence — burns hotter than Ace's fire and holds the moral temperature of "
        "absolute justice. He killed Ace. He almost killed Luffy. He runs the world's "
        "largest military and he is completely certain he is right."
    ),
    "Sengoku": (
        "The Buddha. Former Fleet Admiral and the man who held the Marines together through "
        "the Whitebeard War. His Hito Hito no Mi, Model: Daibutsu and strategic intellect "
        "made him the era's defining naval commander. He retired knowing the next era "
        "would need something he couldn't provide."
    ),
    "Shanks": (
        "The Red-Haired Emperor. Shanks has no Devil Fruit. He doesn't need one. His Haki "
        "alone stopped Whitebeard's tremors from cracking the sky and ended the Summit War "
        "by walking onto the battlefield. He gave Luffy his hat fourteen years ago and "
        "set everything into motion. The bill for that is still coming due."
    ),
    "Dracule Mihawk": (
        "The World's Greatest Swordsman. Mihawk's Yoru is the strongest blade in the world "
        "and he is the man who earned it. He dueled Shanks as an equal for years, held "
        "Marineford by standing still, and is now training the man who wants his title. "
        "He agreed to this because boredom is the only thing that moves him."
    ),
    "Silvers Rayleigh": (
        "The Dark King. First Mate of the Roger Pirates and the man who helped his captain "
        "reach Laugh Tale. Rayleigh's Haki mastery is so complete he used Observation to "
        "see across an ocean. He trained Luffy for two years on Rusukaina and called it "
        "retirement. Roger saw the dawn. Rayleigh made sure someone else would too."
    ),
    "Monkey D. Garp": (
        "The Hero of the Marines. Garp cornered Roger multiple times and is the only man "
        "Roger acknowledged as an equal. He chose the Marines over family, raised Luffy "
        "and Ace with maximally unsafe training, and has spent decades being the institution's "
        "conscience while knowing exactly what it protects."
    ),
    "Monkey D. Dragon": (
        "The World's Most Wanted Man. Leader of the Revolutionary Army and Luffy's father. "
        "Dragon's powers remain deliberately unrevealed in the manga — the World Government's "
        "terror is proportional. He has been dismantling the foundations of the Celestial "
        "Dragon system his entire adult life. Slowly, methodically, and from everywhere at once."
    ),
    "Whitebeard (Legacy)": (
        "Edward Newgate. The World's Strongest Man. His Gura Gura no Mi could crack the "
        "planet and he proved it. He died at Marineford standing, sword in hand, after "
        "267 wounds, 46 swords, 152 bullets, and 72 cannon shots. He died declaring "
        "One Piece is real. The era he anchored ended with him."
    ),
    "Big Mom": (
        "Charlotte Linlin. Emperor of the Sea. Her Soru Soru no Mi steals human souls to "
        "power homies or shorten lives. Her Haki scream alone kills crowds. She has never "
        "been defeated in a fair fight and her hunger rampages are a geopolitical event. "
        "Her love for her family and her willingness to destroy it are the same impulse."
    ),
    "Kaido (Legend)": (
        "The King of the Beasts. The strongest creature alive, by his own accounting and "
        "most others'. Kaido's Azure Dragon Mythical Zoan, Haoshoku Haki, and Boro Breath "
        "make him a force of nature. He survived every execution attempt, every war, "
        "every challenger. Luffy beat him by learning to hit what can't be cut."
    ),
}

# ─── EPITHETS ─────────────────────────────────────────────────────────────────
EPITHETS: list[str] = [
    "the Ironclad", "the Tempest", "Starless", "the Unbroken",
    "Crimson Wake", "the Wanderer", "of the Deep", "the Sovereign",
    "Dawnless", "the Revenant", "Black Tide", "the Phantom",
    "the Unyielding", "Storm Caller", "the Forsaken", "of the Void",
    "the Relentless", "Sea's End", "the Boundless", "the Wraith",
    "Iron Will", "the Undying", "Hollow Crown", "the Ascendant",
    "the Nameless", "World's Edge", "the Cursed", "the Merciless",
    "the Last Storm", "the Dreaded", "of the Scarlet Sea", "the Void Walker",
    "Tidecaller", "the Uncharted", "Bloodless", "the Pale Horizon",
    "of the Ember Coast", "the Ruinous", "Graveless", "the Unclaimed",
    "Ashborn", "the Broken Bell", "of Black Sails", "the Immovable",
    "Sandstorm", "the Colossus", "the Pale King", "Rimefang",
    "the Forgotten", "First Tide", "Last Ember", "the Unmoved",
    "Galeforce", "the Branded", "the Exiled", "Coldwater",
    "the Ravager", "Stormblind", "the Unlit", "the Iron Tide",
]