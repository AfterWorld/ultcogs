"""
Enhanced game data for the DeathBattle system with expanded devil fruits and abilities.
"""

# Define move types with base properties
MOVE_TYPES = {
    "regular": {
        "base_damage_range": (5, 15),
        "crit_chance": 0.15,
        "cooldown": 0
    },
    "strong": {
        "base_damage_range": (15, 25),
        "crit_chance": 0.20,
        "cooldown": 2
    },
    "critical": {
        "base_damage_range": (25, 35),
        "crit_chance": 0.25,
        "cooldown": 4
    }
}

MOVES = [
    # Regular Attacks (No Cooldown)
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": "crit", "crit_chance": 0.20, "cooldown": 0},
    {"name": "Soul Solid", "type": "regular", "description": "Brook plays a chilling tune!", "effect": "stun", "stun_chance": 0.15, "cooldown": 0},
    {"name": "Coup de Vent", "type": "regular", "description": "Franky's air cannon!", "effect": "crit", "crit_chance": 0.20, "cooldown": 0},
    {"name": "Clutch", "type": "regular", "description": "Robin's multi-hand grab!", "effect": "stun", "stun_chance": 0.15, "cooldown": 0},
    {"name": "Black Leg", "type": "regular", "description": "Sanji's blazing kick!", "effect": "burn", "burn_chance": 0.20, "cooldown": 0},
    {"name": "Weather Tempo", "type": "regular", "description": "Nami's weather manipulation!", "effect": "crit", "crit_chance": 0.18, "cooldown": 0},
    {"name": "Usopp Hammer", "type": "regular", "description": "Usopp's massive hammer!", "effect": "stun", "stun_chance": 0.12, "cooldown": 0},
    {"name": "Heavy Point", "type": "regular", "description": "Chopper's powerful form!", "effect": "crit", "crit_chance": 0.15, "cooldown": 0},
    
    # Strong Attacks (2 Turn Cooldown)
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": "crit", "crit_chance": 0.25, "cooldown": 2},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.40, "cooldown": 2},
    {"name": "Dark Vortex", "type": "strong", "description": "Blackbeard's gravity attack!", "effect": "crit", "crit_chance": 0.25, "cooldown": 2},
    {"name": "Elephant Gun", "type": "strong", "description": "Luffy's giant fist!", "effect": "crit", "crit_chance": 0.30, "cooldown": 2},
    {"name": "Diable Jambe", "type": "strong", "description": "Sanji's burning leg!", "effect": "burn", "burn_chance": 0.50, "cooldown": 2},
    {"name": "Thousand Fleur", "type": "strong", "description": "Robin's massive hand barrage!", "effect": "multi_hit", "hits": 3, "cooldown": 2},
    {"name": "Radical Beam", "type": "strong", "description": "Franky's laser cannon!", "effect": "pierce", "pierce_chance": 0.30, "cooldown": 2},
    {"name": "Thunder Bolt Tempo", "type": "strong", "description": "Nami's lightning attack!", "effect": "stun", "stun_chance": 0.35, "cooldown": 2},
    
    # Critical Attacks (4 Turn Cooldown)
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},
    {"name": "King Kong Gun", "type": "critical", "description": "Luffy's massive Gear Fourth punch!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},
    {"name": "Divine Departure", "type": "critical", "description": "Gol D. Roger's legendary strike!", "effect": "stun", "stun_chance": 0.40, "cooldown": 4},
    {"name": "Ashura: Ichibugin", "type": "critical", "description": "Zoro's nine-sword style!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},
    {"name": "Ifrit Jambe", "type": "critical", "description": "Sanji's ultimate burning technique!", "effect": "burn", "burn_chance": 0.60, "cooldown": 4},
    {"name": "Demonio Fleur", "type": "critical", "description": "Robin's demon form attack!", "effect": "fear", "fear_chance": 0.40, "cooldown": 4},
    {"name": "Coup de Burst", "type": "critical", "description": "Franky's ultimate cannon!", "effect": "pierce", "pierce_chance": 0.50, "cooldown": 4},

    # Healing Moves (3 Turn Cooldown)
    {"name": "Phoenix Flames", "type": "strong", "description": "Marco's regenerative flames!", "effect": "heal", "heal_amount": 30, "cooldown": 3},
    {"name": "Healing Rain", "type": "regular", "description": "Soothing rain restores vitality!", "effect": "heal", "heal_amount": 20, "cooldown": 3},
    {"name": "Life Return", "type": "strong", "description": "Energy control to recover health!", "effect": "heal", "heal_amount": 25, "cooldown": 3},
    {"name": "Rumble Ball Recovery", "type": "regular", "description": "Chopper's medical treatment!", "effect": "heal", "heal_amount": 35, "cooldown": 3}
]

DEVIL_FRUITS = {
    "Common": {
        # Paramecia Fruits - Basic
        "Gomu Gomu no Mi": {"type": "Paramecia", "effect": "rubber", "bonus": "Immune to blunt attacks, enhanced stretching power"},
        "Bomu Bomu no Mi": {"type": "Paramecia", "effect": "explosion", "bonus": "Explosive attacks deal 30% extra damage"},
        "Kilo Kilo no Mi": {"type": "Paramecia", "effect": "weight", "bonus": "Can become heavy to crush enemies or light to dodge"},
        "Toge Toge no Mi": {"type": "Paramecia", "effect": "spikes", "bonus": "Counter-attacks deal spike damage to attackers"},
        "Bane Bane no Mi": {"type": "Paramecia", "effect": "springs", "bonus": "Bounce attacks back and enhance mobility"},
        "Hana Hana no Mi": {"type": "Paramecia", "effect": "bloom", "bonus": "Sprout body parts anywhere for surprise attacks"},
        "Doru Doru no Mi": {"type": "Paramecia", "effect": "wax", "bonus": "Create protective barriers and binding attacks"},
        "Supa Supa no Mi": {"type": "Paramecia", "effect": "blades", "bonus": "Turn body parts into blades for cutting attacks"},
        "Baku Baku no Mi": {"type": "Paramecia", "effect": "munch", "bonus": "Devour attacks and incorporate them into your body"},
        "Mane Mane no Mi": {"type": "Paramecia", "effect": "clone", "bonus": "Copy opponent's appearance and one of their abilities"},
        
        # Paramecia Fruits - Enhanced
        "Sube Sube no Mi": {"type": "Paramecia", "effect": "smooth", "bonus": "Slip away from attacks with enhanced evasion"},
        "Kachi Kachi no Mi": {"type": "Paramecia", "effect": "hard", "bonus": "Body becomes harder, reducing incoming damage"},
        "Noro Noro no Mi": {"type": "Paramecia", "effect": "slow", "bonus": "Slow down opponents with photon beams"},
        "Doa Doa no Mi": {"type": "Paramecia", "effect": "door", "bonus": "Create doors to escape or launch surprise attacks"},
        "Awa Awa no Mi": {"type": "Paramecia", "effect": "bubble", "bonus": "Create soap bubbles that weaken opponents"},
        "Sabi Sabi no Mi": {"type": "Paramecia", "effect": "rust", "bonus": "Rust and corrode enemy weapons and armor"},
        "Shiro Shiro no Mi": {"type": "Paramecia", "effect": "castle", "bonus": "Transform into a mobile fortress"},
        "Memo Memo no Mi": {"type": "Paramecia", "effect": "memory", "bonus": "Manipulate memories to confuse opponents"},
        
        # Zoan Fruits - Regular
        "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "Enhanced speed, agility, and predator instincts"},
        "Tori Tori no Mi: Model Falcon": {"type": "Zoan", "effect": "falcon", "bonus": "Superior aerial mobility and keen eyesight"},
        "Mushi Mushi no Mi: Model Hornet": {"type": "Zoan", "effect": "hornet", "bonus": "Flight capability and venomous stinger attacks"},
        "Zou Zou no Mi": {"type": "Zoan", "effect": "elephant", "bonus": "Massive strength and enhanced durability"},
        "Uma Uma no Mi": {"type": "Zoan", "effect": "horse", "bonus": "Incredible speed and stamina on land"},
        "Kame Kame no Mi": {"type": "Zoan", "effect": "turtle", "bonus": "Enhanced defense and aquatic abilities"},
        "Ushi Ushi no Mi: Model Bison": {"type": "Zoan", "effect": "bison", "bonus": "Powerful charge attacks and thick hide"},
        "Ushi Ushi no Mi: Model Giraffe": {"type": "Zoan", "effect": "giraffe", "bonus": "Extended reach and powerful neck attacks"},
        "Inu Inu no Mi: Model Wolf": {"type": "Zoan", "effect": "wolf", "bonus": "Pack hunter instincts and enhanced senses"},
        "Inu Inu no Mi: Model Jackal": {"type": "Zoan", "effect": "jackal", "bonus": "Desert adaptation and cunning tactics"},
        "Neko Neko no Mi: Model Tiger": {"type": "Zoan", "effect": "tiger", "bonus": "Apex predator strength and stealth"},
        "Hebi Hebi no Mi: Model Anaconda": {"type": "Zoan", "effect": "anaconda", "bonus": "Constricting attacks and flexible movement"},
        "Tori Tori no Mi: Model Eagle": {"type": "Zoan", "effect": "eagle", "bonus": "Soaring flight and powerful talons"},
        "Sara Sara no Mi: Model Axolotl": {"type": "Zoan", "effect": "axolotl", "bonus": "Regeneration abilities and aquatic movement"},
    },
    "Rare": {
        # Logia Fruits - Classic
        "Yami Yami no Mi": {"type": "Logia", "effect": "darkness", "bonus": "Absorb attacks and cancel other Devil Fruit powers"},
        "Hie Hie no Mi": {"type": "Logia", "effect": "ice", "bonus": "Freeze opponents and create ice weapons"},
        "Mera Mera no Mi": {"type": "Logia", "effect": "fire", "bonus": "Ignite enemies and become living flame"},
        "Suna Suna no Mi": {"type": "Logia", "effect": "sand", "bonus": "Control sand and drain moisture from enemies"},
        "Gasu Gasu no Mi": {"type": "Logia", "effect": "gas", "bonus": "Create toxic gases and become intangible"},
        "Pika Pika no Mi": {"type": "Logia", "effect": "light", "bonus": "Move at light speed and fire laser beams"},
        "Magu Magu no Mi": {"type": "Logia", "effect": "magma", "bonus": "Superior to fire, melts everything in path"},
        "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "Control electricity and travel through conductors"},
        
        # Logia Fruits - New
        "Moku Moku no Mi": {"type": "Logia", "effect": "smoke", "bonus": "Create smoke screens and become intangible vapor"},
        "Numa Numa no Mi": {"type": "Logia", "effect": "swamp", "bonus": "Create bottomless swamps to trap enemies"},
        "Yuki Yuki no Mi": {"type": "Logia", "effect": "snow", "bonus": "Control snow and create blizzards"},
        
        # Mythical Zoans
        "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Regenerate from blue flames and resurrection power"},
        "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "azure_dragon", "bonus": "Control elements and devastating breath attacks"},
        "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "sun_god", "bonus": "Reality-bending rubber powers and liberation"},
        "Hito Hito no Mi: Model Daibutsu": {"type": "Mythical Zoan", "effect": "buddha", "bonus": "Massive golden form with shockwave attacks"},
        "Inu Inu no Mi: Model Okuchi no Makami": {"type": "Mythical Zoan", "effect": "wolf_god", "bonus": "Divine wolf powers with ice breath"},
        "Hebi Hebi no Mi: Model Yamata no Orochi": {"type": "Mythical Zoan", "effect": "eight_headed_serpent", "bonus": "Eight heads provide multiple attacks and regeneration"},
        "Tori Tori no Mi: Model Nue": {"type": "Mythical Zoan", "effect": "nue", "bonus": "Shapeshifting chimera with illusion powers"},
        
        # Ancient Zoans
        "Ryu Ryu no Mi: Model Spinosaurus": {"type": "Ancient Zoan", "effect": "spinosaurus", "bonus": "Massive size and aquatic hunting abilities"},
        "Ryu Ryu no Mi: Model Pteranodon": {"type": "Ancient Zoan", "effect": "pteranodon", "bonus": "High-speed aerial combat and diving attacks"},
        "Ryu Ryu no Mi: Model Allosaurus": {"type": "Ancient Zoan", "effect": "allosaurus", "bonus": "Powerful jaw and predator instincts"},
        "Ryu Ryu no Mi: Model Triceratops": {"type": "Ancient Zoan", "effect": "triceratops", "bonus": "Armored head and devastating charge attacks"},
        "Ryu Ryu no Mi: Model Brachiosaurus": {"type": "Ancient Zoan", "effect": "brachiosaurus", "bonus": "Enormous size and powerful tail attacks"},
        "Ryu Ryu no Mi: Model Pachycephalosaurus": {"type": "Ancient Zoan", "effect": "pachycephalosaurus", "bonus": "Reinforced skull for headbutt attacks"},
        "Zou Zou no Mi: Model Mammoth": {"type": "Ancient Zoan", "effect": "mammoth", "bonus": "Colossal strength and tusks for piercing"},
        "Neko Neko no Mi: Model Saber Tiger": {"type": "Ancient Zoan", "effect": "saber_tiger", "bonus": "Massive fangs and prehistoric predator power"},
        
        # Special Paramecia & Advanced
        "Mochi Mochi no Mi": {"type": "Special Paramecia", "effect": "mochi", "bonus": "Logia-like properties with sticky trap abilities"},
        "Gura Gura no Mi": {"type": "Paramecia", "effect": "quake", "bonus": "Destroy everything with earthquake power"},
        "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "Control gravitational forces"},
        "Ope Ope no Mi": {"type": "Paramecia", "effect": "operation", "bonus": "Create Room and perform surgical attacks"},
        "Hobi Hobi no Mi": {"type": "Paramecia", "effect": "hobby", "bonus": "Turn enemies into toys under your control"},
        "Bari Bari no Mi": {"type": "Paramecia", "effect": "barrier", "bonus": "Create unbreakable barriers for defense"},
        "Nui Nui no Mi": {"type": "Paramecia", "effect": "stitch", "bonus": "Sew enemies together or to surfaces"},
        "Giro Giro no Mi": {"type": "Paramecia", "effect": "stare", "bonus": "See through lies and read minds"},
        "Ato Ato no Mi": {"type": "Paramecia", "effect": "art", "bonus": "Turn enemies into art and manipulate them"},
        "Jake Jake no Mi": {"type": "Paramecia", "effect": "jacket", "bonus": "Transform into clothing to control others"},
        "Pamu Pamu no Mi": {"type": "Paramecia", "effect": "rupture", "bonus": "Make anything you touch rupture and explode"},
        "Sui Sui no Mi": {"type": "Paramecia", "effect": "swim", "bonus": "Swim through solid surfaces like water"},
        "Ton Ton no Mi": {"type": "Paramecia", "effect": "ton", "bonus": "Increase body weight to massive proportions"},
        "Beta Beta no Mi": {"type": "Paramecia", "effect": "stick", "bonus": "Create sticky substances to trap enemies"},
        "Hira Hira no Mi": {"type": "Paramecia", "effect": "flag", "bonus": "Make anything flat and control like a flag"},
        "Ishi Ishi no Mi": {"type": "Paramecia", "effect": "stone", "bonus": "Merge with and control stone structures"},
    }
}

ENVIRONMENTS = {
    "Skypiea": {
        "description": "High in the sky, electrical attacks are amplified!",
        "effect": "lightning_boost",
        "boost_types": ["lightning", "electric"]
    },
    "Alabasta": {
        "description": "A desert environment where fire and sand powers thrive!",
        "effect": "desert_boost",
        "boost_types": ["fire", "sand", "heat"]
    },
    "Wano": {
        "description": "The battlefield of samurai sharpens blade attacks!",
        "effect": "blade_boost",
        "boost_types": ["sword", "blade", "cutting"]
    },
    "Punk Hazard": {
        "description": "A frozen and fiery wasteland where elemental effects are enhanced!",
        "effect": "elemental_boost",
        "boost_types": ["fire", "ice", "elemental"]
    },
    "Fishman Island": {
        "description": "Underwater battles favor aquatic abilities and healing!",
        "effect": "aquatic_boost",
        "boost_types": ["water", "heal", "fish"]
    },
    "Marineford": {
        "description": "A war-torn battlefield amplifying all combat abilities!",
        "effect": "war_boost",
        "boost_types": ["combat", "war", "strong"]
    },
    "Raftel": {
        "description": "The final island where legendary powers awaken!",
        "effect": "legendary_boost",
        "boost_types": ["all", "legendary"]
    },
    "Impel Down": {
        "description": "The underwater prison where dark powers flourish!",
        "effect": "darkness_boost",
        "boost_types": ["darkness", "poison", "shadow"]
    },
    "Enies Lobby": {
        "description": "The judicial island where justice powers prevail!",
        "effect": "justice_boost",
        "boost_types": ["light", "holy", "justice"]
    },
    "Sabaody Archipelago": {
        "description": "The bubble island where resin and plant powers thrive!",
        "effect": "nature_boost",
        "boost_types": ["bubble", "plant", "resin"]
    },
    "Whole Cake Island": {
        "description": "The sweet paradise where food-based abilities are enhanced!",
        "effect": "food_boost",
        "boost_types": ["food", "sweet", "heal"]
    },
    "Dressrosa": {
        "description": "The toy kingdom where transformation abilities are amplified!",
        "effect": "transformation_boost",
        "boost_types": ["toy", "string", "transformation"]
    }
}

TITLES = {
    "Small-time Pirate": {"bounty": 10_000, "wins_required": 0},
    "Rookie Pirate": {"bounty": 50_000, "wins_required": 3},
    "Super Rookie": {"bounty": 100_000, "wins_required": 5},
    "Notorious Pirate": {"bounty": 200_000, "wins_required": 10},
    "Supernova": {"bounty": 300_000, "wins_required": 15},
    "Rising Star": {"bounty": 400_000, "wins_required": 20},
    "Infamous Pirate": {"bounty": 500_000, "wins_required": 30},
    "Feared Pirate": {"bounty": 600_000, "wins_required": 40},
    "Pirate Captain": {"bounty": 700_000, "wins_required": 50},
    "Pirate Lord": {"bounty": 800_000, "wins_required": 75},
    "Pirate Emperor": {"bounty": 900_000, "wins_required": 100},
    "Yonko Candidate": {"bounty": 1_000_000, "wins_required": 150},
    "Pirate King Candidate": {"bounty": 1_500_000_000, "wins_required": 200},
    "Emperor of the Sea (Yonko)": {"bounty": 2_000_000_000, "wins_required": 300},
    "King of the Pirates": {"bounty": 5_000_000_000, "wins_required": 500},
}

HIDDEN_TITLES = {
    "The Unbreakable": {"condition": "Win 10 battles without losing", "special_effect": "5% damage reduction"},
    "The Underdog": {"condition": "Defeat an opponent with a bounty 5x higher", "special_effect": "10% crit chance vs stronger opponents"},
    "The Bounty Hunter": {"condition": "Steal 100,000 Berries total", "special_effect": "Enhanced robbery success rate"},
    "The Kingmaker": {"condition": "Help an ally win 5 battles", "special_effect": "Team battle bonuses"},
    "The Ghost": {"condition": "Evade 50 attacks total", "special_effect": "5% permanent dodge chance"},
    "The Berserker": {"condition": "Deal 100 damage in a single attack", "special_effect": "Crit attacks deal extra damage"},
    "The Marine Slayer": {"condition": "Defeat 5 different marine-themed players", "special_effect": "Bonus damage vs authority figures"},
    "The Elementalist": {"condition": "Use 5 different elemental fruits", "special_effect": "Environmental bonuses doubled"},
    "The Collector": {"condition": "Own 10 different devil fruits (over time)", "special_effect": "Rare fruit drop rate increased"},
    "The Survivor": {"condition": "Win with less than 10% HP remaining", "special_effect": "Last stand damage bonus"},
}
