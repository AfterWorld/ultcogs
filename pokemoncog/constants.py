"""Constants for the Pokemon cog."""

# Spawn constants
SPAWN_CHANCE = 0.1  # 10% chance of spawn per message
MIN_SPAWN_COOLDOWN = 60  # Minimum 60 seconds between spawns
XP_PER_MESSAGE = 1  # XP gained per message
CATCH_TIMEOUT = 30  # Seconds to catch a Pokemon
SHINY_CHANCE = 1 / 4096  # 1 in 4096 chance for shiny Pokémon

# Special form constants
MEGA_STONE_CHANCE = 0.05  # 5% chance to get a mega stone from daily rewards
Z_CRYSTAL_CHANCE = 0.05   # 5% chance to get a Z-Crystal from daily rewards
DYNAMAX_BAND_CHANCE = 0.05  # 5% chance to get Dynamax Band
PRIMAL_ORB_CHANCE = 0.03  # 3% chance to get a Primal orb (Kyogre/Groudon)

# Special item mapping - Fixed duplicate keys by using tuples for variants
MEGA_STONES = {
    3: "Venusaurite",       # Venusaur
    (6, "X"): "Charizardite X",  # Charizard X
    (6, "Y"): "Charizardite Y",  # Charizard Y
    9: "Blastoisinite",     # Blastoise
    15: "Beedrillite",      # Beedrill
    18: "Pidgeotite",       # Pidgeot
    65: "Alakazite",        # Alakazam
    80: "Slowbronite",      # Slowbro
    94: "Gengarite",        # Gengar
    115: "Kangaskhanite",   # Kangaskhan
    127: "Pinsirite",       # Pinsir
    130: "Gyaradosite",     # Gyarados
    142: "Aerodactylite",   # Aerodactyl
    (150, "X"): "Mewtwoite X",   # Mewtwo X
    (150, "Y"): "Mewtwoite Y",   # Mewtwo Y
    181: "Ampharosite",     # Ampharos
    208: "Steelixite",      # Steelix
    212: "Scizorite",       # Scizor
    214: "Heracronite",     # Heracross
    229: "Houndoominite",   # Houndoom
    248: "Tyranitarite",    # Tyranitar
    254: "Sceptilite",      # Sceptile
    257: "Blazikenite",     # Blaziken
    260: "Swampertite",     # Swampert
    282: "Gardevoirite",    # Gardevoir
    302: "Sablenite",       # Sableye
    303: "Mawilite",        # Mawile
    306: "Aggronite",       # Aggron
    308: "Medichamite",     # Medicham
    310: "Manectite",       # Manectric
    319: "Sharpedonite",    # Sharpedo
    323: "Cameruptite",     # Camerupt
    334: "Altarianite",     # Altaria
    354: "Banettite",       # Banette
    359: "Absolite",        # Absol
    362: "Glalitite",       # Glalie
    373: "Salamencite",     # Salamence
    376: "Metagrossite",    # Metagross
    380: "Latiasite",       # Latias
    381: "Latiosite",       # Latios
    384: "Red Orb",         # Groudon (Primal Reversion)
    382: "Blue Orb",        # Kyogre (Primal Reversion)
    428: "Lopunnite",       # Lopunny
    445: "Garchompite",     # Garchomp
    448: "Lucarionite",     # Lucario
    460: "Abomasite",       # Abomasnow
    475: "Galladite",       # Gallade
    531: "Audinite",        # Audino
    719: "Diancite",        # Diancie
}

# Z-Crystal mapping
Z_CRYSTALS = {
    # Type-specific Z-Crystals
    "Normal": "Normalium Z",
    "Fire": "Firium Z",
    "Water": "Waterium Z",
    "Grass": "Grassium Z",
    "Electric": "Electrium Z",
    "Ice": "Icium Z",
    "Fighting": "Fightinium Z",
    "Poison": "Poisonium Z",
    "Ground": "Groundium Z",
    "Flying": "Flyinium Z",
    "Psychic": "Psychium Z",
    "Bug": "Buginium Z",
    "Rock": "Rockium Z",
    "Ghost": "Ghostium Z",
    "Dragon": "Dragonium Z",
    "Dark": "Darkinium Z",
    "Steel": "Steelium Z",
    "Fairy": "Fairium Z",
    
    # Special Z-Crystals (Pokémon-specific)
    25: "Pikanium Z",        # Pikachu (Catastropika)
    26: "Aloraichium Z",     # Alolan Raichu (Stoked Sparksurfer)
    38: "Tapunium Z",        # Tapu Koko/Lele/Bulu/Fini (Guardian of Alola)
    53: "Eevium Z",          # Eevee (Extreme Evoboost)
    103: "Decidium Z",       # Decidueye (Sinister Arrow Raid)
    105: "Incinium Z",       # Incineroar (Malicious Moonsault)
    107: "Primarium Z",      # Primarina (Oceanic Operetta)
    150: "Mewnium Z",        # Mewtwo (Genesis Supernova)
    151: "Pikashunium Z",    # Pikachu with cap (10,000,000 Volt Thunderbolt)
    249: "Lunalium Z",       # Lunala (Menacing Moonraze Maelstrom)
    250: "Solganium Z",      # Solgaleo (Searing Sunraze Smash)
    254: "Marshadium Z",     # Marshadow (Soul-Stealing 7-Star Strike)
    302: "Kommonium Z",      # Kommo-o (Clangorous Soulblaze)
    658: "Lycanium Z",       # Lycanroc (Splintered Stormshards)
    791: "Mimikium Z",       # Mimikyu (Let's Snuggle Forever)
    800: "Ultranecrozium Z", # Necrozma (Light That Burns the Sky/Photon Geyser)
}

# Primal Orbs
PRIMAL_ORBS = {
    383: "Red Orb",      # Groudon
    382: "Blue Orb",     # Kyogre
}

# Shop items with prices
SHOP_ITEMS = {
    # Basic items
    "potion": {"price": 300, "name": "Potion", "description": "Restores 20 HP"},
    "super potion": {"price": 700, "name": "Super Potion", "description": "Restores 50 HP"},
    "hyper potion": {"price": 1200, "name": "Hyper Potion", "description": "Restores 200 HP"},
    "max potion": {"price": 2500, "name": "Max Potion", "description": "Fully restores HP"},
    "revive": {"price": 1500, "name": "Revive", "description": "Revives a fainted Pokemon with half HP"},
    "max revive": {"price": 4000, "name": "Max Revive", "description": "Revives a fainted Pokemon with full HP"},
    
    # Enhancement items
    "rare candy": {"price": 10000, "name": "Rare Candy", "description": "Instantly raises a Pokemon's level by 1"},
    "exp. candy": {"price": 5000, "name": "Exp. Candy", "description": "Gives a Pokemon 100 XP"},
    "pp up": {"price": 9800, "name": "PP Up", "description": "Increases the PP of a move"},
    
    # Evolution items
    "fire stone": {"price": 20000, "name": "Fire Stone", "description": "Evolves certain Pokemon"},
    "water stone": {"price": 20000, "name": "Water Stone", "description": "Evolves certain Pokemon"},
    "thunder stone": {"price": 20000, "name": "Thunder Stone", "description": "Evolves certain Pokemon"},
    "leaf stone": {"price": 20000, "name": "Leaf Stone", "description": "Evolves certain Pokemon"},
    "moon stone": {"price": 20000, "name": "Moon Stone", "description": "Evolves certain Pokemon"},
    "sun stone": {"price": 20000, "name": "Sun Stone", "description": "Evolves certain Pokemon"},
    "shiny stone": {"price": 25000, "name": "Shiny Stone", "description": "Evolves certain Pokemon"},
    "dusk stone": {"price": 25000, "name": "Dusk Stone", "description": "Evolves certain Pokemon"},
    "dawn stone": {"price": 25000, "name": "Dawn Stone", "description": "Evolves certain Pokemon"},
    
    # Special items
    "lucky egg": {"price": 30000, "name": "Lucky Egg", "description": "Holder earns double XP"},
    "dynamax band": {"price": 50000, "name": "Dynamax Band", "description": "Allows a Pokemon to Dynamax"},
}

# Legendary Pokemon IDs for events
LEGENDARY_IDS = [
    # Gen 1 - Kanto
    144, 145, 146,  # Articuno, Zapdos, Moltres
    150, 151,       # Mewtwo, Mew
    
    # Gen 2 - Johto
    243, 244, 245,  # Raikou, Entei, Suicune
    249, 250, 251,  # Lugia, Ho-Oh, Celebi
    
    # Gen 3 - Hoenn
    377, 378, 379,  # Regirock, Regice, Registeel
    380, 381,       # Latias, Latios
    382, 383, 384,  # Kyogre, Groudon, Rayquaza
    385, 386,       # Jirachi, Deoxys
    
    # Gen 4 - Sinnoh
    480, 481, 482,  # Uxie, Mesprit, Azelf
    483, 484,       # Dialga, Palkia
    485, 486,       # Heatran, Regigigas
    487, 488, 489,  # Giratina, Cresselia, Phione
    490, 491, 492,  # Manaphy, Darkrai, Shaymin
    493,            # Arceus
    
    # Gen 5 - Unova
    494, 495,       # Victini, Cobalion
    638, 639, 640,  # Cobalion, Terrakion, Virizion
    641, 642, 643,  # Tornadus, Thundurus, Reshiram
    644, 645, 646,  # Zekrom, Landorus, Kyurem
    647, 648, 649,  # Keldeo, Meloetta, Genesect
    
    # Gen 6 - Kalos
    716, 717, 718,  # Xerneas, Yveltal, Zygarde
    719, 720, 721,  # Diancie, Hoopa, Volcanion
    
    # Gen 7 - Alola
    772, 773,       # Type: Null, Silvally
    785, 786, 787, 788,  # Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini
    789, 790, 791, 792,  # Cosmog, Cosmoem, Solgaleo, Lunala
    793, 794, 795, 796, 797,  # Nihilego, Buzzwole, Pheromosa, Xurkitree, Celesteela
    798, 799, 800,  # Kartana, Guzzlord, Necrozma
    801, 802,       # Magearna, Marshadow
    
    # Gen 8 - Galar
    888, 889, 890,  # Zacian, Zamazenta, Eternatus
    891, 892, 893, 894, 895, 896, 897, 898  # Kubfu, Urshifu, Zarude, Regieleki, Regidrago, Glastrier, Spectrier, Calyrex
]

# Evolution mapping
EVOLUTION_MAPPING = {
    # Stone evolutions
    "fire stone": {
        "vulpix": 38,     # Vulpix → Ninetales
        "growlithe": 59,   # Growlithe → Arcanine
        "eevee": 136,     # Eevee → Flareon
        "pansear": 514,   # Pansear → Simisear
    },
    "water stone": {
        "poliwhirl": 62,  # Poliwhirl → Poliwrath
        "shellder": 91,   # Shellder → Cloyster
        "staryu": 121,    # Staryu → Starmie
        "eevee": 134,     # Eevee → Vaporeon
        "lombre": 272,    # Lombre → Ludicolo
        "panpour": 516,   # Panpour → Simipour
    },
    "thunder stone": {
        "pikachu": 26,    # Pikachu → Raichu
        "eevee": 135,     # Eevee → Jolteon
        "eelektrik": 604, # Eelektrik → Eelektross
    },
    "leaf stone": {
        "gloom": 45,      # Gloom → Vileplume
        "weepinbell": 71, # Weepinbell → Victreebel
        "exeggcute": 103, # Exeggcute → Exeggutor
        "nuzleaf": 275,   # Nuzleaf → Shiftry
        "pansage": 512,   # Pansage → Simisage
    },
    "moon stone": {
        "nidorina": 31,   # Nidorina → Nidoqueen
        "nidorino": 34,   # Nidorino → Nidoking
        "clefairy": 36,   # Clefairy → Clefable
        "jigglypuff": 40, # Jigglypuff → Wigglytuff
        "skitty": 301,    # Skitty → Delcatty
        "munna": 518,     # Munna → Musharna
    },
    "sun stone": {
        "gloom": 182,     # Gloom → Bellossom
        "sunkern": 192,   # Sunkern → Sunflora
        "cottonee": 547,  # Cottonee → Whimsicott
        "petilil": 549,   # Petilil → Lilligant
        "helioptile": 695,# Helioptile → Heliolisk
    },
    "shiny stone": {
        "togetic": 468,   # Togetic → Togekiss
        "roselia": 407,   # Roselia → Roserade
        "minccino": 573,  # Minccino → Cinccino
        "floette": 670,   # Floette → Florges
    },
    "dusk stone": {
        "murkrow": 430,   # Murkrow → Honchkrow
        "misdreavus": 429,# Misdreavus → Mismagius
        "lampent": 609,   # Lampent → Chandelure
        "doublade": 681,  # Doublade → Aegislash
    },
    "dawn stone": {
        "kirlia": {"id": 475, "condition": "male"},      # Male Kirlia → Gallade
        "snorunt": {"id": 478, "condition": "female"},   # Female Snorunt → Froslass
    },
}

# Regional form evolution mapping
REGIONAL_EVOLUTIONS = {
    # Alolan forms
    "vulpix-alola": {"id": 38, "name": "ninetales-alola"},      # Alolan Vulpix → Alolan Ninetales
    "sandshrew-alola": {"id": 28, "name": "sandslash-alola"},   # Alolan Sandshrew → Alolan Sandslash
    "diglett-alola": {"id": 51, "name": "dugtrio-alola"},       # Alolan Diglett → Alolan Dugtrio
    "meowth-alola": {"id": 53, "name": "persian-alola"},        # Alolan Meowth → Alolan Persian
    "geodude-alola": {"id": 75, "name": "graveler-alola"},      # Alolan Geodude → Alolan Graveler
    "graveler-alola": {"id": 76, "name": "golem-alola"},        # Alolan Graveler → Alolan Golem
    "grimer-alola": {"id": 89, "name": "muk-alola"},            # Alolan Grimer → Alolan Muk
    "exeggcute-alola": {"id": 103, "name": "exeggutor-alola"},  # Exeggcute → Alolan Exeggutor (with Leaf Stone)
    
    # Galarian forms
    "meowth-galar": {"id": 863, "name": "perrserker"},          # Galarian Meowth → Perrserker
    "ponyta-galar": {"id": 78, "name": "rapidash-galar"},       # Galarian Ponyta → Galarian Rapidash
    "slowpoke-galar": {"id": 80, "name": "slowbro-galar"},      # Galarian Slowpoke → Galarian Slowbro (with Galarica Cuff)
    "slowpoke-galar": {"id": 199, "name": "slowking-galar"},    # Galarian Slowpoke → Galarian Slowking (with Galarica Wreath)
    "farfetchd-galar": {"id": 865, "name": "sirfetchd"},        # Galarian Farfetch'd → Sirfetch'd
    "corsola-galar": {"id": 864, "name": "cursola"},            # Galarian Corsola → Cursola
    "yamask-galar": {"id": 867, "name": "runerigus"},           # Galarian Yamask → Runerigus
    "linoone-galar": {"id": 862, "name": "obstagoon"},          # Galarian Linoone → Obstagoon
    
    # Hisuian forms
    "growlithe-hisui": {"id": 59, "name": "arcanine-hisui"},    # Hisuian Growlithe → Hisuian Arcanine (with Fire Stone)
    "voltorb-hisui": {"id": 101, "name": "electrode-hisui"},    # Hisuian Voltorb → Hisuian Electrode (with Leaf Stone)
    "cyndaquil-hisui": {"id": 157, "name": "quilava-hisui"},    # Hisuian Cyndaquil → Hisuian Quilava
    "quilava-hisui": {"id": 503, "name": "typhlosion-hisui"},   # Hisuian Quilava → Hisuian Typhlosion
    "petilil-hisui": {"id": 549, "name": "lilligant-hisui"},    # Hisuian Petilil → Hisuian Lilligant (with Sun Stone)
    "basculin-hisui": {"id": 902, "name": "basculegion"},       # Hisuian Basculin → Basculegion
    "sneasel-hisui": {"id": 903, "name": "sneasler"},           # Hisuian Sneasel → Sneasler
    "zorua-hisui": {"id": 571, "name": "zoroark-hisui"},        # Hisuian Zorua → Hisuian Zoroark
    "sliggoo-hisui": {"id": 706, "name": "goodra-hisui"},       # Hisuian Sliggoo → Hisuian Goodra
    "bergmite-hisui": {"id": 713, "name": "avalugg-hisui"}      # Hisuian Bergmite → Hisuian Avalugg
}

# Mega Evolution capable Pokemon IDs
MEGA_CAPABLE_POKEMON = [
    3, 6, 9, 65, 94, 115, 127, 130, 142, 150, 181, 212, 214, 229, 
    248, 257, 282, 303, 306, 308, 310, 354, 359, 380, 381, 445, 448, 460
]

# Gigantamax capable Pokemon IDs
GMAX_CAPABLE_POKEMON = [
    3, 6, 9, 12, 25, 52, 68, 94, 99, 131, 143, 569, 809, 812, 
    815, 818, 823, 826, 834, 839, 841, 844, 849, 851, 858, 861, 
    869, 879, 884, 892
]

# Pokemon IDs with regional forms
REGIONAL_FORM_POKEMON = {
    "alola": [19, 20, 26, 27, 28, 37, 38, 50, 51, 52, 53, 74, 75, 76, 88, 89, 103, 105],
    "galar": [52, 77, 78, 79, 80, 83, 110, 122, 144, 145, 146, 199, 222, 263, 264, 554, 555, 562, 618],
    "hisui": [58, 59, 100, 101, 157, 211, 215, 503, 549, 570, 571, 628, 705, 706, 713]
}

# Type effectiveness chart for battles
TYPE_CHART = {
    "normal": {
        "rock": 0.5, "steel": 0.5, "ghost": 0.0
    },
    "fire": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, 
        "rock": 0.5, "dragon": 0.5, "steel": 2.0
    },
    "water": {
        "fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5
    },
    "electric": {
        "water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5
    },
    "grass": {
        "fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, 
        "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5
    },
    "ice": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, 
        "flying": 2.0, "dragon": 2.0, "steel": 0.5
    },
    "fighting": {
        "normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, 
        "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5
    },
    "poison": {
        "grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, 
        "steel": 0.0, "fairy": 2.0
    },
    "ground": {
        "fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, 
        "bug": 0.5, "rock": 2.0, "steel": 2.0
    },
    "flying": {
        "electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5
    },
    "psychic": {
        "fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5
    },
    "bug": {
        "fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, 
        "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5
    },
    "rock": {
        "fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, 
        "bug": 2.0, "steel": 0.5
    },
    "ghost": {
        "normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5
    },
    "dragon": {
        "dragon": 2.0, "steel": 0.5, "fairy": 0.0
    },
    "dark": {
        "fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5
    },
    "steel": {
        "fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, 
        "steel": 0.5, "fairy": 2.0
    },
    "fairy": {
        "fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5
    }
}