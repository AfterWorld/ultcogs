"""
Game data for the DeathBattle system including moves, devil fruits, environments, and titles.
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
    
    # Strong Attacks (2 Turn Cooldown)
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": "crit", "crit_chance": 0.25, "cooldown": 2},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.40, "cooldown": 2},
    {"name": "Dark Vortex", "type": "strong", "description": "Blackbeard's gravity attack!", "effect": "crit", "crit_chance": 0.25, "cooldown": 2},
    {"name": "Elephant Gun", "type": "strong", "description": "Luffy's giant fist!", "effect": "crit", "crit_chance": 0.30, "cooldown": 2},
    
    # Critical Attacks (4 Turn Cooldown)
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},
    {"name": "King Kong Gun", "type": "critical", "description": "Luffy's massive Gear Fourth punch!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},
    {"name": "Divine Departure", "type": "critical", "description": "Gol D. Roger's legendary strike devastates the battlefield!", "effect": "stun", "stun_chance": 0.40, "cooldown": 4},
    {"name": "Ashura: Ichibugin", "type": "critical", "description": "Zoro's nine-sword style cuts through everything in its path!", "effect": "crit", "crit_chance": 0.35, "cooldown": 4},

    # Healing Moves (3 Turn Cooldown)
    {"name": "Phoenix Flames", "type": "strong", "description": "Marco's regenerative flames heal wounds!", "effect": "heal", "heal_amount": 30, "cooldown": 3},
    {"name": "Healing Rain", "type": "regular", "description": "A soothing rain that restores vitality!", "effect": "heal", "heal_amount": 20, "cooldown": 3},
    {"name": "Life Return", "type": "strong", "description": "A technique that uses energy control to recover health!", "effect": "heal", "heal_amount": 25, "cooldown": 3}
]

DEVIL_FRUITS = {
    "Common": {
        # Paramecia Fruits
        "Gomu Gomu no Mi": {"type": "Paramecia", "effect": "rubber", "bonus": "Immune to blunt attacks"},
        "Bomu Bomu no Mi": {"type": "Paramecia", "effect": "explosion", "bonus": "Explosive attacks deal 30% extra damage"},
        "Kilo Kilo no Mi": {"type": "Paramecia", "effect": "weight", "bonus": "Increase or decrease weight to avoid attacks"},
        "Toge Toge no Mi": {"type": "Paramecia", "effect": "spikes", "bonus": "Counter melee attacks with spike damage"},
        "Bane Bane no Mi": {"type": "Paramecia", "effect": "springs", "bonus": "Jump twice as far and attack with spring force"},
        "Hana Hana no Mi": {"type": "Paramecia", "effect": "multiple limbs", "bonus": "Can attack or defend from any direction"},
        "Doru Doru no Mi": {"type": "Paramecia", "effect": "wax", "bonus": "Create shields and weapons from hard wax"},
        "Supa Supa no Mi": {"type": "Paramecia", "effect": "blades", "bonus": "Body turns into blades, increasing melee damage"},
        "Baku Baku no Mi": {"type": "Paramecia", "effect": "eat anything", "bonus": "Can consume and copy enemy weapons"},
        "Mane Mane no Mi": {"type": "Paramecia", "effect": "copy", "bonus": "Can mimic an enemy's attack once per battle"},
        
        # Regular Zoans
        "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "20% increased speed and agility"},
        "Tori Tori no Mi: Model Falcon": {"type": "Zoan", "effect": "falcon", "bonus": "Enhanced aerial mobility"},
        "Mushi Mushi no Mi: Model Hornet": {"type": "Zoan", "effect": "hornet", "bonus": "Can fly and sting enemies"},
        "Zou Zou no Mi": {"type": "Zoan", "effect": "elephant", "bonus": "Increased strength and durability"},
        "Uma Uma no Mi": {"type": "Zoan", "effect": "horse", "bonus": "Enhanced speed on land"},
        "Kame Kame no Mi": {"type": "Zoan", "effect": "turtle", "bonus": "Enhanced defense and swimming ability"},
    },
    "Rare": {
        # Logia Fruits
        "Yami Yami no Mi": {"type": "Logia", "effect": "darkness", "bonus": "Can absorb 15% of the opponent's attack damage as HP"},
        "Hie Hie no Mi": {"type": "Logia", "effect": "ice", "bonus": "Can freeze an opponent, skipping their next turn"},
        "Mera Mera no Mi": {"type": "Logia", "effect": "fire", "bonus": "Fire attacks do double damage"},
        "Suna Suna no Mi": {"type": "Logia", "effect": "sand", "bonus": "10% chance to drain enemy's HP"},
        "Gasu Gasu no Mi": {"type": "Logia", "effect": "gas", "bonus": "Can poison enemies with toxic gas"},
        "Pika Pika no Mi": {"type": "Logia", "effect": "light", "bonus": "Moves first in every battle"},
        "Magu Magu no Mi": {"type": "Logia", "effect": "magma", "bonus": "Deals additional burn damage over time"},
        "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "Lightning attacks have chance to paralyze"},
        
        # Mythical Zoans
        "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Heals 10% HP every 3 turns"},
        "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "azure dragon", "bonus": "30% stronger attacks in battles"},
        "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "sun god", "bonus": "Randomly boosts attack, speed, or defense"},
        "Hito Hito no Mi: Model Daibutsu": {"type": "Mythical Zoan", "effect": "giant buddha", "bonus": "Boosts defense and attack power"},
        
        # Ancient Zoans
        "Ryu Ryu no Mi: Model Spinosaurus": {"type": "Ancient Zoan", "effect": "spinosaurus", "bonus": "Increase HP by 20%"},
        "Ryu Ryu no Mi: Model Pteranodon": {"type": "Ancient Zoan", "effect": "pteranodon", "bonus": "Gain a 15% chance to evade attacks"},
        "Ryu Ryu no Mi: Model Allosaurus": {"type": "Ancient Zoan", "effect": "allosaurus", "bonus": "Increase attack damage by 25%"},
        
        # Special Paramecia
        "Mochi Mochi no Mi": {"type": "Special Paramecia", "effect": "mochi", "bonus": "Can dodge one attack every 4 turns"},
        "Gura Gura no Mi": {"type": "Paramecia", "effect": "quake", "bonus": "Earthquake attack deals massive AoE damage"},
        "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "20% chance to stun an enemy every turn"},
        "Ope Ope no Mi": {"type": "Paramecia", "effect": "operation", "bonus": "Complete control within operation room"},
    }
}

ENVIRONMENTS = {
    "Skypiea": {
        "description": "High in the sky, electrical attacks are amplified!",
        "effect": "crit_boost",
    },
    "Alabasta": {
        "description": "A desert environment where burn effects are more potent!",
        "effect": "burn_boost",
    },
    "Wano": {
        "description": "The battlefield of samurai sharpens strong attacks!",
        "effect": "strong_boost",
    },
    "Punk Hazard": {
        "description": "A frozen and fiery wasteland where all elemental effects are enhanced!",
        "effect": "elemental_boost",
    },
    "Fishman Island": {
        "description": "Underwater battles favor healing moves!",
        "effect": "heal_boost",
    },
    "Marineford": {
        "description": "A war-torn battlefield amplifying strong attacks!",
        "effect": "war_boost",
    },
    "Raftel": {
        "description": "The final island where every stat is boosted!",
        "effect": "ultimate_boost",
    },
}

TITLES = {
    "Small-time Pirate": {"bounty": 10_000},
    "Rookie Pirate": {"bounty": 50_000},
    "Super Rookie": {"bounty": 100_000},
    "Notorious Pirate": {"bounty": 200_000},
    "Supernova": {"bounty": 300_000},
    "Rising Star": {"bounty": 400_000},
    "Infamous Pirate": {"bounty": 500_000},
    "Feared Pirate": {"bounty": 600_000},
    "Pirate Captain": {"bounty": 700_000},
    "Pirate Lord": {"bounty": 800_000},
    "Pirate Emperor": {"bounty": 900_000},
    "Yonko Candidate": {"bounty": 1_000_000},
    "Pirate King Candidate": {"bounty": 1_500_000_000},
    "Emperor of the Sea (Yonko)": {"bounty": 2_000_000_000},
    "King of the Pirates": {"bounty": 5_000_000_000},
}

HIDDEN_TITLES = {
    "The Unbreakable": {"condition": "Win 10 battles without losing"},
    "The Underdog": {"condition": "Defeat an opponent with a bounty 5x higher than yours"},
    "The Bounty Hunter": {"condition": "Steal 100,000 Berries from bounty hunting"},
    "The Kingmaker": {"condition": "Help an ally win 5 battles by teaming up"},
    "The Ghost": {"condition": "Evade 3 attacks in a row"},
    "The Berserker": {"condition": "Deal 100 damage in a single attack"},
    "The Marine Slayer": {"condition": "Defeat 5 different players with Marine-themed titles"},
}