from redbot.core import commands, Config
import discord
import random
import asyncio
from asyncio import Lock
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import logging
import aiohttp
import io  
import json
import os
import difflib
from typing import Optional

BOUNTY_FILE = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/bounties.json"

# Ensure directory exists
os.makedirs(os.path.dirname(BOUNTY_FILE), exist_ok=True)

def load_json(file_path):
    """Safely load JSON data from a file."""
    if not os.path.exists(file_path):
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json(file_path, data):
    """Safely save JSON data to a file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_bounties():
    """Load bounty data safely from file."""
    if not os.path.exists(BOUNTY_FILE):
        return {}  # If file doesn't exist, return empty dict
    
    try:
        with open(BOUNTY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}  # If file is corrupted, return empty dict

def save_bounties(data):
    """Save bounty data safely to file."""
    os.makedirs(os.path.dirname(BOUNTY_FILE), exist_ok=True)
    with open(BOUNTY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Initialize logger
logger = logging.getLogger("red.bounty")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/logs/bountybattle.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

# --- Constants ---
ACHIEVEMENTS = {
    "first_blood": {
        "description": "Claim your first victory in the arena!",
        "condition": "wins",
        "count": 1,
        "title": "Rookie Gladiator",
    },
    "big_hitter": {
        "description": "Deal a colossal 30+ damage in one blow!",
        "condition": "big_hit",
        "count": 1,
        "title": "Heavy Hitter",
    },
    "burn_master": {
        "description": "Inflict burn on your opponent 5 times in a single match!",
        "condition": "burns_applied",
        "count": 5,
        "title": "Master of Flames",
    },
    "comeback_king": {
        "description": "Clinch victory after dropping below 10 HP!",
        "condition": "comeback",
        "count": 1,
        "title": "Comeback King",
    },
    "perfect_game": {
        "description": "Achieve a flawless victory without taking any damage!",
        "condition": "no_damage",
        "count": 1,
        "title": "Flawless Victor",
    },
    "stunning_performance": {
        "description": "Stun your opponent 3 times in a single match!",
        "condition": "stuns",
        "count": 3,
        "title": "Stunning Tactician",
    },
    "overkill": {
        "description": "Deliver an overwhelming 50+ damage in a single hit!",
        "condition": "big_hit",
        "count": 1,
        "title": "Overkill Expert",
    },
    "healing_touch": {
        "description": "Heal yourself for a total of 50 HP in one match!",
        "condition": "healing_done",
        "count": 50,
        "title": "Healing Savior",
    },
    "unstoppable": {
        "description": "Win 10 matches to prove your dominance!",
        "condition": "wins",
        "count": 10,
        "title": "Unstoppable",
    },
    "sea_emperor": {
        "description": "Claim the title of Sea Emperor by winning 25 matches!",
        "condition": "wins",
        "count": 25,
        "title": "Sea Emperor",
    },
    "legendary_warrior": {
        "description": "Win 50 matches to cement your legacy!",
        "condition": "wins",
        "count": 50,
        "title": "Legendary Warrior",
    },
    "iron_wall": {
        "description": "Block 20 attacks across all matches!",
        "condition": "total_blocks",
        "count": 20,
        "title": "Iron Wall",
    },
    "damage_master": {
        "description": "Deal a total of 1000 damage across all matches!",
        "condition": "total_damage_dealt",
        "count": 1000,
        "title": "Damage Master",
    },
    "burning_legacy": {
        "description": "Inflict 100 burns across all matches!",
        "condition": "total_burns_applied",
        "count": 100,
        "title": "Legacy of Fire",
    },
    "guardian_angel": {
        "description": "Prevent 100 damage using blocks across all matches!",
        "condition": "damage_prevented",
        "count": 100,
        "title": "Guardian Angel",
    },
    "swift_finisher": {
        "description": "End a match in under 5 turns!",
        "condition": "turns_taken",
        "count": 5,
        "title": "Swift Finisher",
    },
    "relentless": {
        "description": "Land a critical hit 10 times in one match!",
        "condition": "critical_hits",
        "count": 10,
        "title": "Relentless Attacker",
    },
    "elemental_master": {
        "description": "Use every elemental attack type in a single match!",
        "condition": "elements_used",
        "count": "all",
        "title": "Elemental Master",
    },
    "unstoppable_force": {
        "description": "Win 3 matches in a row without losing!",
        "condition": "win_streak",
        "count": 3,
        "title": "Unstoppable Force",
    },
    "immortal": {
        "description": "Win a match with exactly 1 HP remaining!",
        "condition": "survive_at_1_hp",
        "count": 1,
        "title": "Immortal",
    },
    "devastator": {
        "description": "Deal 500 damage in one match!",
        "condition": "damage_dealt",
        "count": 500,
        "title": "The Devastator",
    },
    "pyromaniac": {
        "description": "Inflict burn 10 times in a single match!",
        "condition": "burns_applied",
        "count": 10,
        "title": "Pyromaniac",
    },
    "titan": {
        "description": "Survive 50 turns in a single match!",
        "condition": "turns_survived",
        "count": 50,
        "title": "The Titan",
    },
}

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
        "Goe Goe no Mi": {"type": "Paramecia", "effect": "sound waves", "bonus": "Launch powerful sound-based attacks"},
        "Ori Ori no Mi": {"type": "Paramecia", "effect": "binding", "bonus": "Can trap enemies in iron restraints"},
        "Shari Shari no Mi": {"type": "Paramecia", "effect": "wheels", "bonus": "Can turn limbs into spinning wheels for attacks"},
        "Awa Awa no Mi": {"type": "Paramecia", "effect": "bubbles", "bonus": "Reduces enemy defense with cleansing bubbles"},
        "Noro Noro no Mi": {"type": "Paramecia", "effect": "slow beam", "bonus": "Temporarily slows down enemies"},
        "Giro Giro no Mi": {"type": "Paramecia", "effect": "x-ray", "bonus": "Can read enemy attacks before they strike"},
        "Tama Tama no Mi": {"type": "Paramecia", "effect": "egg", "bonus": "Can harden body like a shell once per battle"},
        "Ato Ato no Mi": {"type": "Paramecia", "effect": "art", "bonus": "Can slow down an opponent by turning them into a painting"},
        "Nemu Nemu no Mi": {"type": "Paramecia", "effect": "sleep", "bonus": "Chance to put an opponent to sleep for 1 turn"},
        "Hiso Hiso no Mi": {"type": "Paramecia", "effect": "whisper", "bonus": "Can communicate with animals"},
        "Samu Samu no Mi": {"type": "Paramecia", "effect": "cold body", "bonus": "Slight resistance to ice attacks"},
        "Ashi Ashi no Mi": {"type": "Paramecia", "effect": "feet", "bonus": "Movement speed increased by 15%"},
        "Beta Beta no Mi": {"type": "Paramecia", "effect": "sticky", "bonus": "Can slow down enemy movement"},
        "Jiki Jiki no Mi": {"type": "Paramecia", "effect": "magnetism", "bonus": "Can attract and repel small metal objects"},
        "Mitsu Mitsu no Mi": {"type": "Paramecia", "effect": "honey", "bonus": "Can trap opponents in sticky honey"},
        "Taru Taru no Mi": {"type": "Paramecia", "effect": "liquid body", "bonus": "Takes reduced damage from physical attacks"},
        "Chain Chain no Mi": {"type": "Paramecia", "effect": "chains", "bonus": "Can create and control chains"},
        "Clank Clank no Mi": {"type": "Paramecia", "effect": "metallic body", "bonus": "Can transform body parts into metal"},
        "Color Color no Mi": {"type": "Paramecia", "effect": "colors", "bonus": "Can change the color of objects and create illusions"},
        "Cube Cube no Mi": {"type": "Paramecia", "effect": "cubes", "bonus": "Can transform objects into cubes"},
        "Mini Mini no Mi": {"type": "Paramecia", "effect": "shrinking", "bonus": "Can shrink to tiny sizes"},
        "Net Net no Mi": {"type": "Paramecia", "effect": "nets", "bonus": "Can create and control nets"},
        "Roll Roll no Mi": {"type": "Paramecia", "effect": "rolling", "bonus": "Can roll at high speeds"},
        "Scream Scream no Mi": {"type": "Paramecia", "effect": "sonic", "bonus": "Can emit powerful sonic screams"},
        "Sickle Sickle no Mi": {"type": "Paramecia", "effect": "blades", "bonus": "Can create and control sickle blades"},
        "Shroom Shroom no Mi": {"type": "Paramecia", "effect": "mushrooms", "bonus": "Can grow and control mushrooms"},
        "Vision Vision no Mi": {"type": "Paramecia", "effect": "sight", "bonus": "Can see through objects"},
        "Candy Candy no Mi": {"type": "Paramecia", "effect": "candy", "bonus": "Can create and control candy"},
        "Paper Paper no Mi": {"type": "Paramecia", "effect": "paper", "bonus": "Can transform into and control paper"},

        # Regular Zoans
        "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "20% increased speed and agility"},
        "Tori Tori no Mi: Model Falcon": {"type": "Zoan", "effect": "falcon", "bonus": "Enhanced aerial mobility"},
        "Mushi Mushi no Mi: Model Hornet": {"type": "Zoan", "effect": "hornet", "bonus": "Can fly and sting enemies"},
        "Zou Zou no Mi": {"type": "Zoan", "effect": "elephant", "bonus": "Increased strength and durability"},
        "Uma Uma no Mi": {"type": "Zoan", "effect": "horse", "bonus": "Enhanced speed on land"},
        "Kame Kame no Mi": {"type": "Zoan", "effect": "turtle", "bonus": "Enhanced defense and swimming ability"},

        # SMILE Fruits
        "Alpaca SMILE": {"type": "Zoan", "effect": "alpaca features", "bonus": "Gains alpaca traits"},
        "Armadillo SMILE": {"type": "Zoan", "effect": "armadillo features", "bonus": "Can roll into a ball for defense"},
        "Bat SMILE": {"type": "Zoan", "effect": "bat features", "bonus": "Limited flight capability"},
        "Elephant SMILE": {"type": "Zoan", "effect": "elephant features", "bonus": "Trunk-based attacks"},
        "Chicken SMILE": {"type": "Zoan", "effect": "chicken features", "bonus": "Can glide short distances"},
        "Flying Squirrel SMILE": {"type": "Zoan", "effect": "flying squirrel features", "bonus": "Gliding ability"},
        "Gazelle SMILE": {"type": "Zoan", "effect": "gazelle features", "bonus": "Enhanced jumping"},
        "Giraffe SMILE": {"type": "Zoan", "effect": "giraffe features", "bonus": "Extended reach"},
        "Gorilla SMILE": {"type": "Zoan", "effect": "gorilla features", "bonus": "Enhanced strength"},
        "Hippopotamus SMILE": {"type": "Zoan", "effect": "hippo features", "bonus": "Water resistance"},
        "Horse SMILE": {"type": "Zoan", "effect": "horse features", "bonus": "Increased speed"},
        "Lion SMILE": {"type": "Zoan", "effect": "lion features", "bonus": "Predator abilities"},
        "Pug SMILE": {"type": "Zoan", "effect": "pug features", "bonus": "Enhanced smell"},
        "Rattlesnake SMILE": {"type": "Zoan", "effect": "snake features", "bonus": "Poisonous bite"},
        "Scorpion SMILE": {"type": "Zoan", "effect": "scorpion features", "bonus": "Poisonous sting"},
        "Sheep SMILE": {"type": "Zoan", "effect": "sheep features", "bonus": "Wool protection"}
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
        "Mori Mori no Mi": {"type": "Logia", "effect": "forest", "bonus": "Can summon roots to immobilize opponents"},
        "Kaze Kaze no Mi": {"type": "Logia", "effect": "wind", "bonus": "Has a 20% chance to dodge any attack"},
        "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "Lightning attacks have chance to paralyze"},
        "Moku Moku no Mi": {"type": "Logia", "effect": "smoke", "bonus": "Can become intangible at will"},
        "Yuki Yuki no Mi": {"type": "Logia", "effect": "snow", "bonus": "Can freeze and control battlefield"},
        "Numa Numa no Mi": {"type": "Logia", "effect": "swamp", "bonus": "Can create quicksand traps"},

        # Mythical Zoans
        "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Heals 10% HP every 3 turns"},
        "Tori Tori no Mi: Model Thunderbird": {"type": "Mythical Zoan", "effect": "thunderbird", "bonus": "Lightning attacks deal extra damage"},
        "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "azure dragon", "bonus": "30% stronger attacks in battles"},
        "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "sun god", "bonus": "Randomly boosts attack, speed, or defense"},
        "Hito Hito no Mi: Model Daibutsu": {"type": "Mythical Zoan", "effect": "giant buddha", "bonus": "Boosts defense and attack power"},
        "Hito Hito no Mi: Model Onyudo": {"type": "Mythical Zoan", "effect": "monk", "bonus": "Can grow to massive sizes"},
        "Inu Inu no Mi: Model Cerberus": {"type": "Mythical Zoan", "effect": "three-headed dog", "bonus": "Can attack twice per turn"},
        "Inu Inu no Mi: Model Okuchi no Makami": {"type": "Mythical Zoan", "effect": "wolf deity", "bonus": "Healing abilities are doubled"},
        "Hebi Hebi no Mi: Model Yamata no Orochi": {"type": "Mythical Zoan", "effect": "eight-headed snake", "bonus": "Gain 2 extra attacks every 3 turns"},
        "Uma Uma no Mi: Model Pegasus": {"type": "Mythical Zoan", "effect": "pegasus", "bonus": "Flight and enhanced speed"},

        # Ancient Zoans
        "Ryu Ryu no Mi: Model Spinosaurus": {"type": "Ancient Zoan", "effect": "spinosaurus", "bonus": "Increase HP by 20%"},
        "Ryu Ryu no Mi: Model Pteranodon": {"type": "Ancient Zoan", "effect": "pteranodon", "bonus": "Gain a 15% chance to evade attacks"},
        "Ryu Ryu no Mi: Model Allosaurus": {"type": "Ancient Zoan", "effect": "allosaurus", "bonus": "Increase attack damage by 25%"},
        "Ryu Ryu no Mi: Model Brachiosaurus": {"type": "Ancient Zoan", "effect": "brachiosaurus", "bonus": "Massive strength increase"},
        "Ryu Ryu no Mi: Model Pachycephalosaurus": {"type": "Ancient Zoan", "effect": "pachycephalosaurus", "bonus": "Powerful headbutt attacks"},
        "Ryu Ryu no Mi: Model Triceratops": {"type": "Ancient Zoan", "effect": "triceratops", "bonus": "Enhanced charging attacks"},
        "Kumo Kumo no Mi: Model Rosamygale Grauvogeli": {"type": "Ancient Zoan", "effect": "ancient spider", "bonus": "Web attacks slow enemies"},
        
        # Special & Powerful Paramecia
        "Mochi Mochi no Mi": {"type": "Special Paramecia", "effect": "mochi", "bonus": "Can dodge one attack every 4 turns"},
        "Gura Gura no Mi": {"type": "Paramecia", "effect": "quake", "bonus": "Earthquake attack deals massive AoE damage"},
        "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "20% chance to stun an enemy every turn"},
        "Toki Toki no Mi": {"type": "Paramecia", "effect": "time", "bonus": "Can speed up cooldowns for abilities"},
        "Ope Ope no Mi": {"type": "Paramecia", "effect": "operation", "bonus": "Complete control within operation room"},
        "Gold Gold no Mi": {"type": "Paramecia", "effect": "gold", "bonus": "Can create and control gold"},
        "More More no Mi": {"type": "Paramecia", "effect": "multiplication", "bonus": "Can multiply objects and attacks"},
        "Luck Luck no Mi": {"type": "Paramecia", "effect": "fortune", "bonus": "Increases chance of critical hits"},
        "Through Through no Mi": {"type": "Paramecia", "effect": "phasing", "bonus": "Can pass through solid objects"},
        "Return Return no Mi": {"type": "Paramecia", "effect": "reversal", "bonus": "Can return attacks to sender"},
        "Soru Soru no Mi": {"type": "Paramecia", "effect": "soul manipulation", "bonus": "Can steal and manipulate life force"},
        "Bari Bari no Mi": {"type": "Paramecia", "effect": "barrier", "bonus": "Block 40% of incoming melee damage"},
        "Doku Doku no Mi": {"type": "Paramecia", "effect": "poison", "bonus": "Deals poison damage over time"},
        "Hobi Hobi no Mi": {"type": "Paramecia", "effect": "toy conversion", "bonus": "Can erase people from memories"},
        "Kira Kira no Mi": {"type": "Paramecia", "effect": "diamond", "bonus": "Defense increases by 30%"},
        "Ito Ito no Mi": {"type": "Paramecia", "effect": "string control", "bonus": "Can control people and create clones"}
    }
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

# --- Modified Code with One Piece Island Environments ---

ENVIRONMENTS = {
    "Skypiea": {
        "description": "High in the sky, electrical attacks are amplified!",
        "effect": lambda move, stats: move.update({"crit_chance": move.get("crit_chance", 0.2) + 0.1}) if "crit" in move.get("effect", "") else None,
    },
    "Alabasta": {
        "description": "A desert environment where burn effects are more potent!",
        "effect": lambda move, stats: move.update({"burn_chance": move.get("burn_chance", 0.0) + 0.2}) if "burn" in move.get("effect", "") else None,
    },
    "Wano": {
        "description": "The battlefield of samurai sharpens strong attacks!",
        "effect": lambda move, stats: move.update({"damage": stats.get("damage", 0) + 5}) if move.get("type") == "strong" else None,
    },
    "Punk Hazard": {
        "description": "A frozen and fiery wasteland where all elemental effects are enhanced!",
        "effect": lambda move, stats: (
            move.update({"burn_chance": move.get("burn_chance", 0.0) + 0.1}) if "burn" in move.get("effect", "") else None,
            move.update({"stun": True}) if "stun" in move.get("effect", "") else None
        ),
    },
    "Fishman Island": {
        "description": "Underwater battles favor healing moves!",
        "effect": lambda move, stats: move.update({"heal": stats.get("heal", 0) + 10}) if move.get("effect") == "heal" else None,
    },
    "Dressrosa": {
        "description": "A vibrant battleground where critical strikes flourish!",
        "effect": lambda move, stats: move.update({"crit_chance": move.get("crit_chance", 0.2) + 0.1}) if "crit" in move.get("effect", "") else None,
    },
    "Whole Cake Island": {
        "description": "A sweet and strange land where health restoration is increased!",
        "effect": lambda move, stats: move.update({"heal": stats.get("heal", 0) + 15}) if move.get("effect") == "heal" else None,
    },
    "Marineford": {
        "description": "A war-torn battlefield amplifying strong attacks!",
        "effect": lambda move, stats: move.update({"damage": stats.get("damage", 0) + 10}) if move.get("type") == "strong" else None,
    },
    "Enies Lobby": {
        "description": "A place of justice where defensive moves shine!",
        "effect": lambda move, stats: move.update({"block_active": True}) if "block" in move.get("effect", "") else None,
    },
    "Amazon Lily": {
        "description": "A paradise that enhances healing and charm-based moves!",
        "effect": lambda move, stats: move.update({"heal": stats.get("heal", 0) + 10}) if move.get("effect") == "heal" else None,
    },
    "Zou": {
        "description": "The moving island enhances all elemental abilities!",
        "effect": lambda move, stats: (
            move.update({"burn_chance": move.get("burn_chance", 0.0) + 0.1}) if "burn" in move.get("effect", "") else None,
            move.update({"stun": True}) if "stun" in move.get("effect", "") else None
        ),
    },
    "Elbaf": {
        "description": "A giant's battlefield where physical attacks are devastating!",
        "effect": lambda move, stats: move.update({"damage": stats.get("damage", 0) + 15}) if move.get("type") == "strong" else None,
    },
    "Raftel": {
        "description": "The final island where every stat is boosted!",
        "effect": lambda move, stats: (
            move.update({"crit_chance": move.get("crit_chance", 0.2) + 0.1}),
            move.update({"burn_chance": move.get("burn_chance", 0.0) + 0.1}),
            move.update({"heal": stats.get("heal", 0) + 10})
        ),
    },
}

class DevilFruitManager:
    """Manages Devil Fruit effects and their interactions with status effects."""
    
    def __init__(self, status_manager, environment_manager):
        self.status_manager = status_manager
        self.environment_manager = environment_manager
        self.active_transformations = {}
        
        # Effect cooldowns for Devil Fruits
        self.fruit_cooldowns = {
            "Mera Mera no Mi": 3,      # Fire abilities
            "Goro Goro no Mi": 4,      # Lightning abilities
            "Hie Hie no Mi": 3,        # Ice abilities
            "Ope Ope no Mi": 4,        # Room abilities
            "Pika Pika no Mi": 3,      # Light abilities
            "Magu Magu no Mi": 4,      # Magma abilities
            "Gura Gura no Mi": 5,      # Quake abilities
        }
    
    async def process_devil_fruit_effect(self, attacker, defender, move, environment):
        """Process Devil Fruit effects with proper interaction handling."""
        if not attacker.get("fruit"):
            return 0, None
            
        fruit_name = attacker["fruit"]
        bonus_damage = 0
        effect_message = None
        
        # Get fruit data from either Common or Rare categories
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        if not fruit_data:
            return 0, None

        fruit_type = fruit_data["type"]
        effect = fruit_data["effect"]

        # Track fruit usage for achievements
        if "elements_used" not in attacker:
            attacker["elements_used"] = set()
        attacker["elements_used"].add(fruit_type)

        # Process based on fruit type
        if fruit_type == "Logia":
            bonus_damage, effect_message = await self._handle_logia_effects(
                attacker, defender, effect, move, environment
            )
        elif "Zoan" in fruit_type:
            bonus_damage, effect_message = await self._handle_zoan_effects(
                attacker, defender, effect, move, environment
            )
        elif fruit_type in ["Paramecia", "Special Paramecia"]:
            bonus_damage, effect_message = await self._handle_paramecia_effects(
                attacker, defender, effect, move, environment
            )

        return bonus_damage, effect_message

    async def _handle_logia_effects(self, attacker, defender, effect, move, environment):
        """Handle Logia-type Devil Fruit effects with enhanced proc rates and balanced damage."""
        bonus_damage = 0
        effect_message = None  # Initialize at start

        # Get base damage from move
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Mera Mera no Mi (Fire)
        if effect == "fire":
            if random.random() < 0.45:  # 45% proc rate
                await self.status_manager.apply_effect("burn", defender, value=2)
                bonus_damage = int(base_damage * 0.75)
                effect_message = (
                    f"🔥 **FLAME EMPEROR**! 🔥\n"
                    f"**{attacker['name']}** unleashes flames!\n"
                    f"💥 {bonus_damage} fire damage + Burn (2 stacks)"
                )

        # Hie Hie no Mi (Ice)
        elif effect == "ice":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"❄️ **ICE AGE**! ❄️\n"
                    f"**{attacker['name']}** freezes the battlefield!\n"
                    f"🥶 2-turn freeze + {bonus_damage} bonus damage!"
                )

        # Yami Yami no Mi (Darkness)
        elif effect == "darkness":
            if random.random() < 0.50:
                absorb_amount = int(base_damage * 1.5)  
                attacker["hp"] = min(250, attacker["hp"] + absorb_amount)
                bonus_damage = int(base_damage * 1.0)
                effect_message = (
                    f"🌑 **BLACK HOLE**! 🌑\n"
                    f"**{attacker['name']}** commands darkness!\n"
                    f"⚫ Absorbed {absorb_amount} HP + {bonus_damage} bonus damage!"
                )

        # Pika Pika no Mi (Light)
        elif effect == "light":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"✨ **SACRED YASAKANI**! ✨\n"
                    f"**{attacker['name']}** attacks at light speed!\n"
                    f"⚡ {bonus_damage} piercing damage!"
                )

        # Goro Goro no Mi (Lightning)
        elif effect == "lightning":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(base_damage * 1.0)
                effect_message = (
                    f"⚡ **THUNDER GOD**! ⚡\n"
                    f"**{attacker['name']}** channels lightning!\n"
                    f"💫 2-turn stun + {bonus_damage} bonus damage!"
                )

        # Magu Magu no Mi (Magma)
        elif effect == "magma":
            if random.random() < 0.55:
                await self.status_manager.apply_effect("burn", defender, value=4, duration=3)
                bonus_damage = int(base_damage * 0.9)
                effect_message = (
                    f"🌋 **GREAT ERUPTION**! 🌋\n"
                    f"**{attacker['name']}** unleashes magma!\n"
                    f"🔥 4-stack burn + {bonus_damage} bonus damage!"
                )

        # Suna Suna no Mi (Sand)
        elif effect == "sand":
            if random.random() < 0.35:
                drain_amount = int(defender["hp"] * 0.25)
                defender["hp"] -= drain_amount
                attacker["hp"] = min(250, attacker["hp"] + drain_amount)
                bonus_damage = int(base_damage * 0.4)
                effect_message = (
                    f"🏜️ **GROUND DEATH**! 🏜️\n"
                    f"**{attacker['name']}** drains life force!\n"
                    f"💀 Drained {drain_amount} HP + {bonus_damage} bonus damage!"
                )

        # Moku Moku no Mi (Smoke)
        elif effect == "smoke":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"💨 **WHITE LAUNCHER**! 💨\n"
                    f"**{attacker['name']}** becomes smoke!\n"
                    f"✨ 2-turn evasion + {bonus_damage} bonus damage!"
                )

        # Mori Mori no Mi (Forest)
        elif effect == "forest":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("root", defender, duration=2)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"🌳 **FOREST PRISON**! 🌳\n"
                    f"**{attacker['name']}** binds with roots!\n"
                    f"🌿 2-turn root + {bonus_damage} bonus damage!"
                )

        # Kaze Kaze no Mi (Wind)
        elif effect == "wind":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.65)
                effect_message = (
                    f"🌪️ **DIVINE WIND**! 🌪️\n"
                    f"**{attacker['name']}** harnesses the wind!\n"
                    f"💨 2-turn evasion + {bonus_damage} bonus damage!"
                )

        # Gasu Gasu no Mi (Gas)
        elif effect == "gas":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("poison", defender, duration=3)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"☠️ **POISON GAS**! ☠️\n"
                    f"**{attacker['name']}** releases toxic gas!\n"
                    f"💀 3-turn poison + {bonus_damage} bonus damage!"
                )

        # Yuki Yuki no Mi (Snow)
        elif effect == "snow":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"❄️ **WHITE OUT**! ❄️\n"
                    f"**{attacker['name']}** creates a blizzard!\n"
                    f"🌨️ 2-turn slow + {bonus_damage} bonus damage!"
                )

        # Numa Numa no Mi (Swamp)
        elif effect == "swamp":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 0.55)
                effect_message = (
                    f"💀 **SWAMP TRAP**! 💀\n"
                    f"**{attacker['name']}** creates a deadly swamp!\n"
                    f"🌫️ 2-turn bind + {bonus_damage} bonus damage!"
                )

        # Environment interactions with proper scaling
        if environment == "Punk Hazard" and effect in ["fire", "ice", "magma"]:
            bonus_damage = int(bonus_damage * 1.5)
            if effect_message:
                effect_message = f"{effect_message}\n🌋 Power amplified by Punk Hazard's climate!"
        elif environment == "Alabasta" and effect in ["fire", "magma"]:
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n🏜️ Desert environment enhances fire powers!"
        elif environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Sacred battleground amplifies power!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"💫 **LOGIA AWAKENING**! 💫\n"
                f"**{attacker['name']}**'s elemental power provides {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_zoan_effects(self, attacker, defender, effect, move, environment):
        """Handle Zoan-type Devil Fruit effects with proper transformations and hybrid forms."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Model Leopard (Neko Neko no Mi: Model Leopard)
        if effect == "leopard":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 0.9)
                hits = random.randint(2, 3)  # Multi-hit attack
                bonus_damage *= hits
                effect_message = (
                    f"🐆 **PREDATOR'S AGILITY**! 🐆\n"
                    f"**{attacker['name']}** strikes with feline grace!\n"
                    f"⚡ {hits} rapid strikes for {bonus_damage} total damage!"
                )

        # Model Azure Dragon
        elif "Azure Dragon" in effect:
            if random.random() < 0.40:
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                effect_message = (
                    f"🐉 **CELESTIAL DRAGON'S MIGHT**! 🐉\n"
                    f"**{attacker['name']}** channels divine power!\n"
                    f"✨ 2-turn protection + {bonus_damage} divine damage!"
                )

        # Model Phoenix (Tori Tori no Mi: Model Phoenix)
        elif "Phoenix" in effect:
            if random.random() < 0.45:
                heal_amount = int(attacker["max_hp"] * 0.15)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🦅 **FLAMES OF RESTORATION**! 🦅\n"
                    f"**{attacker['name']}** bathes in regenerative flames!\n"
                    f"💚 Healed {heal_amount} HP + {bonus_damage} flame damage!"
                )

        # Model Spinosaurus
        elif "Spinosaurus" in effect:
            if random.random() < 0.40:
                bonus_damage = int(base_damage * 1.3)
                await self.status_manager.apply_effect("protect", attacker, duration=1)
                effect_message = (
                    f"🦕 **ANCIENT WARRIOR'S MIGHT**! 🦕\n"
                    f"**{attacker['name']}** unleashes prehistoric power!\n"
                    f"💥 {bonus_damage} primal damage + 1-turn protection!"
                )

        # Model Pteranodon
        elif "Pteranodon" in effect:
            if random.random() < 0.40:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"🦅 **AERIAL SUPREMACY**! 🦅\n"
                    f"**{attacker['name']}** takes to the skies!\n"
                    f"💨 2-turn dodge + {bonus_damage} aerial damage!"
                )

        # Model Okuchi no Makami
        elif "Okuchi no Makami" in effect:
            if random.random() < 0.40:
                heal_amount = int(base_damage * 0.4)
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🐺 **DIVINE WOLF'S BLESSING**! 🐺\n"
                    f"**{attacker['name']}** channels sacred healing!\n"
                    f"✨ {heal_amount} HP restored + {bonus_damage} divine damage!"
                )

        # Model Rosamygale Grauvogeli
        elif "spider" in effect:
            if random.random() < 0.45:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"🕷️ **ANCIENT WEB**! 🕷️\n"
                    f"**{attacker['name']}** ensnares with prehistoric webbing!\n"
                    f"🕸️ 2-turn slow + {bonus_damage} web damage!"
                )

        # Model Nika (Hito Hito no Mi: Model Nika)
        elif effect == "nika":
            if random.random() < 0.50:  # 50% proc rate for special fruit
                effect_choice = random.choice(["drumbeat", "giant", "freedom"])
                
                if effect_choice == "drumbeat":
                    # Massive damage boost for Drums of Liberation
                    bonus_damage = int(base_damage * 2.0)  # 200% damage boost
                    await self.status_manager.apply_effect("attack_boost", attacker, duration=2)
                    effect_message = (
                        f"💥 **DRUMS OF LIBERATION**! 💥\n"
                        f"**{attacker['name']}** awakens the rhythm of freedom!\n"
                        f"🥁 {bonus_damage} liberation damage + Attack boost for 2 turns!"
                    )
                    
                elif effect_choice == "giant":
                    # Giant form now properly boosts damage and adds defense
                    bonus_damage = int(base_damage * 1.8)  # 180% damage boost
                    await self.status_manager.apply_effect("transform", attacker, duration=3)
                    await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                    effect_message = (
                        f"🌟 **GIANT WARRIOR**! 🌟\n"
                        f"**{attacker['name']}** becomes a giant!\n"
                        f"👊 3-turn transformation with defense boost + {bonus_damage} massive damage!"
                    )
                    
                elif effect_choice == "freedom":
                    # Freedom now boosts damage and provides immunity
                    bonus_damage = int(base_damage * 1.5)  # 150% damage boost
                    # Clear negative status effects
                    for status in ["burn", "stun", "frozen", "slow", "bind", "poison", "defense_down", "attack_down"]:
                        if status in attacker["status"]:
                            attacker["status"][status] = 0
                    # Add immunity
                    await self.status_manager.apply_effect("status_immunity", attacker, duration=2)
                    effect_message = (
                        f"🌈 **WARRIOR OF LIBERATION**! 🌈\n"
                        f"**{attacker['name']}** breaks all limitations!\n"
                        f"✨ Status immunity for 2 turns + {bonus_damage} liberation damage!"
                    )
                
                # Add chance for additional effect using base HP (250)
                if random.random() < 0.25:  # 25% chance for extra joy boy effect
                    heal_amount = int(250 * 0.15)  # 15% of 250 HP = 37 HP heal
                    attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                    effect_message += f"\n💫 **JOY BOY'S BLESSING**! Healed for {heal_amount} HP!"

        # Model Daibutsu
        elif "Daibutsu" in effect:
            if random.random() < 0.45:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                bonus_damage = int(base_damage * 1.1)
                effect_message = (
                    f"🗿 **ENLIGHTENED COMBAT**! 🗿\n"
                    f"**{attacker['name']}** channels Buddha's power!\n"
                    f"🛡️ 2-turn protection + {bonus_damage} enlightened damage!"
                )

        # Model Cerberus
        elif "Cerberus" in effect:
            if random.random() < 0.40:
                hits = 3  # Triple attack
                bonus_damage = int(base_damage * 0.5 * hits)
                effect_message = (
                    f"🐕 **HELLHOUND'S FURY**! 🐕\n"
                    f"**{attacker['name']}** strikes with three heads!\n"
                    f"💥 {hits} coordinated strikes for {bonus_damage} total damage!"
                )

        # Model Seiryu (Uo Uo no Mi: Model Seiryu)
        elif "Seiryu" in effect:
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("elemental_boost", attacker, duration=2)
                effect_message = (
                    f"🐉 **AZURE DRAGON'S BLESSING**! 🐉\n"
                    f"**{attacker['name']}** channels celestial power!\n"
                    f"✨ 2-turn elemental boost + {bonus_damage} divine damage!"
                )

        # Model Allosaurus
        elif "Allosaurus" in effect:
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.4)  # High raw damage
                effect_message = (
                    f"🦖 **JURASSIC HUNTER**! 🦖\n"
                    f"**{attacker['name']}** unleashes prehistoric fury!\n"
                    f"💥 {bonus_damage} primal damage!"
                )

        # Model Yamata no Orochi
        elif "Yamata no Orochi" in effect:
            if random.random() < 0.40:
                hits = random.randint(3, 5)  # Multi-head attack
                bonus_damage = int(base_damage * 0.4 * hits)
                effect_message = (
                    f"🐍 **EIGHT-HEADED ASSAULT**! 🐍\n"
                    f"**{attacker['name']}** strikes with multiple heads!\n"
                    f"💥 {hits} serpent strikes for {bonus_damage} total damage!"
                )

        # Model Bison
        elif "bison" in effect:
            if random.random() < 0.45:
                if "battle_turns" not in attacker:
                    attacker["battle_turns"] = 0
                attacker["battle_turns"] += 1
                
                bonus_damage = int(base_damage * (1.0 + (0.1 * min(5, attacker["battle_turns"]))))
                effect_message = (
                    f"🦬 **STAMPEDING FORCE**! 🦬\n"
                    f"**{attacker['name']}** builds momentum!\n"
                    f"💥 Turn {attacker['battle_turns']} power: {bonus_damage} damage!"
                )
        # Model Thunderbird (Tori Tori no Mi: Model Thunderbird)
        elif "Thunderbird" in effect:
            if random.random() < 0.45:
                await self.status_manager.apply_effect("thunder_charge", attacker, duration=2)
                bonus_damage = int(base_damage * 1.3)
                effect_message = (
                    f"⚡ **STORM MONARCH**! ⚡\n"
                    f"**{attacker['name']}** summons the storm!\n"
                    f"🌩️ Lightning damage boost for 2 turns + {bonus_damage} storm damage!"
                )

        # Model Brachiosaurus (Ryu Ryu no Mi: Model Brachiosaurus)
        elif "Brachiosaurus" in effect:
            if random.random() < 0.40:
                await self.status_manager.apply_effect("strength_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.5)
                effect_message = (
                    f"🦕 **ANCIENT COLOSSUS**! 🦕\n"
                    f"**{attacker['name']}** towers over the battlefield!\n"
                    f"💪 Massive strength boost + {bonus_damage} crushing damage!"
                )

        # Model Pachycephalosaurus (Ryu Ryu no Mi: Model Pachycephalosaurus)
        elif "Pachycephalosaurus" in effect:
            if random.random() < 0.45:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"🦕 **DOME CRUSHER**! 🦕\n"
                    f"**{attacker['name']}** delivers a devastating headbutt!\n"
                    f"💫 1-turn stun + {bonus_damage} impact damage!"
                )

        # Model Triceratops (Ryu Ryu no Mi: Model Triceratops)
        elif "Triceratops" in effect:
            if random.random() < 0.40:
                await self.status_manager.apply_effect("defense_break", defender, duration=2)
                bonus_damage = int(base_damage * 1.3)
                effect_message = (
                    f"🦕 **TRIPLE HORN STRIKE**! 🦕\n"
                    f"**{attacker['name']}** charges with devastating force!\n"
                    f"🛡️ Defense break + {bonus_damage} piercing damage!"
                )

        # Model Uma (Uma Uma no Mi)
        elif effect == "horse":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.1)
                effect_message = (
                    f"🐎 **STAMPEDING CHARGE**! 🐎\n"
                    f"**{attacker['name']}** charges at incredible speed!\n"
                    f"💨 2-turn speed boost + {bonus_damage} trampling damage!"
                )

        # Model Kame (Kame Kame no Mi)
        elif effect == "turtle":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("shell_defense", attacker, duration=3)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"🐢 **SHELL FORTRESS**! 🐢\n"
                    f"**{attacker['name']}** withdraws into an iron-hard shell!\n"
                    f"🛡️ 3-turn enhanced defense + {bonus_damage} shell damage!"
                )

        # Model Hornet (Mushi Mushi no Mi: Model Hornet)
        elif effect == "hornet":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("poison", defender, duration=3)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🐝 **VENOMOUS STRIKE**! 🐝\n"
                    f"**{attacker['name']}** delivers a poisonous sting!\n"
                    f"☠️ 3-turn poison + {bonus_damage} sting damage!"
                )

        # Environment interactions
        if environment == "Wano" and ("Dragon" in effect or "Orochi" in effect):
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Power enhanced by Wano's legendary aura!"
        elif environment == "Zou" and ("elephant" in effect or "mammoth" in effect):
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n🐘 Power amplified by Zou's ancient might!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"✨ **ZOAN TRANSFORMATION**! ✨\n"
                f"**{attacker['name']}**'s beast form grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_paramecia_effects(self, attacker, defender, effect, move, environment):
        """Handle Paramecia-type Devil Fruit effects with consistent activation and balanced damage."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Gomu Gomu no Mi
        if effect == "rubber" and move.get("type") == "strong":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"✨ **RUBBER POWER**! ✨\n"
                    f"**{attacker['name']}** stretches for maximum power!\n"
                    f"💥 {bonus_damage} elastic bonus damage!"
                )

        # Toge Toge no Mi (Fixed counter damage)
        elif effect == "spikes":
            if random.random() < 0.40:
                counter_damage = int(base_damage * 0.75)  # 75% damage reflection
                defender["hp"] -= counter_damage
                defender["stats"]["damage_taken"] += counter_damage
                bonus_damage = int(base_damage * 0.3)  # Additional direct damage
                effect_message = (
                    f"🌵 **SPIKE COUNTER**! 🌵\n"
                    f"**{attacker['name']}** retaliates with spikes!\n"
                    f"💥 Reflected {counter_damage} damage + {bonus_damage} bonus damage!"
                )

        # Ope Ope no Mi
        elif effect == "surgical":
            if random.random() < 0.35:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🏥 **ROOM: SHAMBLES**! 🏥\n"
                    f"**{attacker['name']}** performs surgical precision!\n"
                    f"✨ 2-turn stun + {bonus_damage} bonus damage!"
                )

        # Baku Baku no Mi
        elif effect == "eat anything":
            if random.random() < 0.40:
                bonus_damage = int(base_damage * 0.9)
                heal_amount = int(bonus_damage * 0.3)
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                effect_message = (
                    f"🍽️ **WEAPON DIGESTION**! 🍽️\n"
                    f"**{attacker['name']}** consumes and copies power!\n"
                    f"💥 {bonus_damage} bonus damage + {heal_amount} HP restored!"
                )

        # Bomu Bomu no Mi
        elif effect == "explosion":
            if random.random() < 0.50:
                bonus_damage = int(base_damage * 1.1)  # High damage multiplier
                effect_message = (
                    f"💥 **EXPLOSIVE FORCE**! 💥\n"
                    f"**{attacker['name']}** detonates with power!\n"
                    f"🎯 {bonus_damage} explosive damage!"
                )

        # Kilo Kilo no Mi
        elif effect == "weight":
            if random.random() < 0.45:
                if random.random() < 0.5:  # 50/50 heavy or light form
                    bonus_damage = int(base_damage * 1.3)
                    effect_message = (
                        f"⚖️ **WEIGHT CRUSH**! ⚖️\n"
                        f"**{attacker['name']}** increases mass!\n"
                        f"💥 {bonus_damage} crushing damage!"
                    )
                else:
                    await self.status_manager.apply_effect("dodge", attacker, duration=2)
                    bonus_damage = int(base_damage * 0.4)
                    effect_message = (
                        f"🪶 **WEIGHTLESS DODGE**! 🪶\n"
                        f"**{attacker['name']}** becomes weightless!\n"
                        f"✨ 2-turn dodge + {bonus_damage} bonus damage!"
                    )

        # Bane Bane no Mi
        elif effect == "springs":
            if random.random() < 0.40:
                bonus_damage = int(base_damage * 0.85)
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                effect_message = (
                    f"🔄 **SPRING FORCE**! 🔄\n"
                    f"**{attacker['name']}** compresses and releases!\n"
                    f"💫 Speed boost + {bonus_damage} bonus damage!"
                )

        # Hana Hana no Mi
        elif effect == "multiple limbs":
            if random.random() < 0.45:
                hits = random.randint(2, 4)
                bonus_damage = int(base_damage * 0.4 * hits)
                effect_message = (
                    f"🌸 **FLEUR CASCADE**! 🌸\n"
                    f"**{attacker['name']}** sprouts multiple limbs!\n"
                    f"👊 {hits} hits for {bonus_damage} total damage!"
                )

        # Doru Doru no Mi
        elif effect == "wax":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🕯️ **WAX ARMOR**! 🕯️\n"
                    f"**{attacker['name']}** creates protective wax!\n"
                    f"🛡️ 2-turn protection + {bonus_damage} bonus damage!"
                )

        # Supa Supa no Mi
        elif effect == "blades":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 0.95)
                effect_message = (
                    f"⚔️ **STEEL BODY**! ⚔️\n"
                    f"**{attacker['name']}** turns body to blades!\n"
                    f"🗡️ {bonus_damage} slicing damage!"
                )

        # Mane Mane no Mi
        elif effect == "copy":
            if random.random() < 0.35:
                bonus_damage = int(base_damage * 1.0)
                effect_message = (
                    f"👥 **PERFECT MIMICRY**! 👥\n"
                    f"**{attacker['name']}** copies enemy technique!\n"
                    f"✨ {bonus_damage} mirrored damage!"
                )

        # Goe Goe no Mi
        elif effect == "sound waves":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"🔊 **SONIC BURST**! 🔊\n"
                    f"**{attacker['name']}** releases sound waves!\n"
                    f"💫 1-turn stun + {bonus_damage} sonic damage!"
                )

        # Ori Ori no Mi
        elif effect == "binding":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"⛓️ **BINDING PRISON**! ⛓️\n"
                    f"**{attacker['name']}** restrains the target!\n"
                    f"🔒 2-turn bind + {bonus_damage} bonus damage!"
                )
            
        # Kage Kage no Mi
        elif effect == "shadows":
            if random.random() < 0.40:
                steal_amount = int(base_damage * 0.5)
                defender["hp"] -= steal_amount
                attacker["hp"] = min(250, attacker["hp"] + steal_amount)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"👥 **SHADOW THEFT**! 👥\n"
                    f"**{attacker['name']}** steals enemy's shadow!\n"
                    f"🌑 Drained {steal_amount} HP + {bonus_damage} bonus damage!"
                )

        # Shari Shari no Mi
        elif effect == "wheels":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 0.8)
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                effect_message = (
                    f"🎡 **WHEEL RUSH**! 🎡\n"
                    f"**{attacker['name']}** transforms into deadly wheel!\n"
                    f"💨 Speed boost + {bonus_damage} spinning damage!"
                )

        # Awa Awa no Mi
        elif effect == "bubbles":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("defense_down", defender, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🫧 **CLEANSING BUBBLES**! 🫧\n"
                    f"**{attacker['name']}** weakens target's defense!\n"
                    f"✨ 2-turn defense reduction + {bonus_damage} damage!"
                )

        # Sabi Sabi no Mi
        elif effect == "rust":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("defense_down", defender, duration=3)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"🔨 **RUST DECAY**! 🔨\n"
                    f"**{attacker['name']}** corrodes enemy defenses!\n"
                    f"💫 3-turn defense reduction + {bonus_damage} damage!"
                )

        # Noro Noro no Mi
        elif effect == "slow beam":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"⏳ **SLOW BEAM**! ⏳\n"
                    f"**{attacker['name']}** slows the target!\n"
                    f"🐌 2-turn slow + {bonus_damage} damage!"
                )

        # Doa Doa no Mi
        elif effect == "doors":
            if random.random() < 0.35:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"🚪 **DOOR ESCAPE**! 🚪\n"
                    f"**{attacker['name']}** creates an escape door!\n"
                    f"✨ 2-turn dodge + {bonus_damage} damage!"
                )

        # Beri Beri no Mi
        elif effect == "barrier balls":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🔮 **BERRY BARRIER**! 🔮\n"
                    f"**{attacker['name']}** splits into barrier balls!\n"
                    f"✨ 2-turn dodge + {bonus_damage} damage!"
                )

        # Yomi Yomi no Mi
        elif effect == "revival":
            if attacker["hp"] <= 75 and random.random() < 0.40:
                heal_amount = 100
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"💀 **SOUL KING'S ENCORE**! 💀\n"
                    f"**{attacker['name']}** refuses to fall!\n"
                    f"✨ Recovered {heal_amount} HP + {bonus_damage} damage!"
                )

        # Horo Horo no Mi
        elif effect == "ghosts":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("attack_down", defender, duration=2)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"👻 **NEGATIVE HOLLOW**! 👻\n"
                    f"**{attacker['name']}** summons negative ghosts!\n"
                    f"💔 2-turn attack reduction + {bonus_damage} damage!"
                )

        # Hobi Hobi no Mi
        elif effect == "toy":
            if random.random() < 0.35:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                await self.status_manager.apply_effect("attack_down", defender, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🎎 **TOY TRANSFORMATION**! 🎎\n"
                    f"**{attacker['name']}** temporarily transforms target!\n"
                    f"✨ 1-turn stun + Attack reduction + {bonus_damage} damage!"
                )

        # Gura Gura no Mi
        elif effect == "quake":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.4)  # High damage multiplier
                await self.status_manager.apply_effect("stun", defender, duration=1)
                effect_message = (
                    f"💥 **SEISMIC SHOCK**! 💥\n"
                    f"**{attacker['name']}** shatters the air itself!\n"
                    f"🌋 {bonus_damage} quake damage + 1-turn stun!"
                )
        # Zushi Zushi no Mi (Gravity)
        elif effect == "gravity":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(base_damage * 1.1)
                effect_message = (
                    f"🌍 **GRAVITY CRUSH**! 🌍\n"
                    f"**{attacker['name']}** manipulates gravity!\n"
                    f"💫 1-turn stun + {bonus_damage} crushing damage!"
                )

        # Toki Toki no Mi (Time)
        elif effect == "time":
            if random.random() < 0.35:
                for move in attacker["moves_on_cooldown"]:
                    attacker["moves_on_cooldown"][move] = max(0, attacker["moves_on_cooldown"][move] - 2)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"⏰ **TIME MANIPULATION**! ⏰\n"
                    f"**{attacker['name']}** accelerates time!\n"
                    f"⚡ Cooldowns reduced + {bonus_damage} temporal damage!"
                )

        # Gold Gold no Mi
        elif effect == "gold":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("defense_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"💰 **GOLDEN IMPACT**! 💰\n"
                    f"**{attacker['name']}** creates golden weapons!\n"
                    f"✨ 2-turn defense boost + {bonus_damage} golden damage!"
                )

        # More More no Mi
        elif effect == "multiplication":
            if random.random() < 0.40:
                hits = random.randint(2, 3)
                bonus_damage = int(base_damage * 0.6 * hits)
                effect_message = (
                    f"📋 **DUPLICATE STRIKE**! 📋\n"
                    f"**{attacker['name']}** multiplies their attack!\n"
                    f"💥 {hits} copies deal {bonus_damage} total damage!"
                )

        # Luck Luck no Mi
        elif effect == "fortune":
            if random.random() < 0.40:
                crit_bonus = random.choice([1.5, 2.0, 2.5])  # Random critical multiplier
                bonus_damage = int(base_damage * crit_bonus)
                effect_message = (
                    f"🍀 **FORTUNE'S FAVOR**! 🍀\n"
                    f"**{attacker['name']}** channels their luck!\n"
                    f"✨ {crit_bonus}x critical bonus for {bonus_damage} damage!"
                )

        # Through Through no Mi
        elif effect == "phasing":
            if random.random() < 0.35:
                await self.status_manager.apply_effect("dodge", attacker, duration=3)
                bonus_damage = int(base_damage * 0.6)
                effect_message = (
                    f"👻 **PHASE SHIFT**! 👻\n"
                    f"**{attacker['name']}** becomes intangible!\n"
                    f"💫 3-turn dodge + {bonus_damage} damage!"
                )

        # Return Return no Mi
        elif effect == "reversal":
            if random.random() < 0.35:
                if defender["stats"]["damage_dealt"] > 0:
                    bonus_damage = int(defender["stats"]["damage_dealt"] * 0.3)  # 30% of damage dealt by opponent
                    effect_message = (
                        f"↩️ **DAMAGE REVERSAL**! ↩️\n"
                        f"**{attacker['name']}** returns damage!\n"
                        f"💫 {bonus_damage} reflected damage!"
                    )

        # Soru Soru no Mi
        elif effect == "soul manipulation":
            if random.random() < 0.40:
                steal_amount = int(defender["hp"] * 0.15)  # 15% HP drain
                defender["hp"] -= steal_amount
                attacker["hp"] = min(250, attacker["hp"] + steal_amount)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"👻 **SOUL POCUS**! 👻\n"
                    f"**{attacker['name']}** steals life force!\n"
                    f"💀 Drained {steal_amount} HP + {bonus_damage} damage!"
                )

        # Bari Bari no Mi
        elif effect == "barrier":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🛡️ **BARRIER CRUSH**! 🛡️\n"
                    f"**{attacker['name']}** creates an unbreakable barrier!\n"
                    f"✨ 2-turn protection + {bonus_damage} barrier damage!"
                )

        # Doku Doku no Mi
        elif effect == "poison":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("poison", defender, duration=3)
                bonus_damage = int(base_damage * 0.7)
                effect_message = (
                    f"☠️ **VENOM STRIKE**! ☠️\n"
                    f"**{attacker['name']}** injects deadly poison!\n"
                    f"💀 3-turn poison + {bonus_damage} toxic damage!"
                )

        # Kira Kira no Mi
        elif effect == "diamond":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                bonus_damage = int(base_damage * 1.1)
                effect_message = (
                    f"💎 **DIAMOND BODY**! 💎\n"
                    f"**{attacker['name']}** hardens like diamond!\n"
                    f"✨ 2-turn protection + {bonus_damage} crystalline damage!"
                )

        # Ito Ito no Mi
        elif effect == "string control":
            if random.random() < 0.45:
                hits = random.randint(2, 4)  # Multiple string attacks
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 0.5 * hits)
                effect_message = (
                    f"🕸️ **PARASITE STRING**! 🕸️\n"
                    f"**{attacker['name']}** controls with strings!\n"
                    f"🎯 {hits} hits for {bonus_damage} damage + 2-turn bind!"
                )

        # Environment interactions
        if environment == "Dressrosa" and effect in ["string", "toy"]:
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n🎭 Power amplified by Dressrosa's influence!"
        elif environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Sacred battleground amplifies power!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"✨ **PARAMECIA POWER**! ✨\n"
                f"**{attacker['name']}**'s devil fruit grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    def get_fruit_cooldown(self, fruit_name):
        """Get the cooldown for a Devil Fruit ability."""
        return self.fruit_cooldowns.get(fruit_name, 3)

    def is_fruit_on_cooldown(self, attacker, fruit_name):
        """Check if a Devil Fruit ability is on cooldown."""
        return fruit_name in attacker.get("fruit_cooldowns", {})

class EnvironmentManager:
    """Manages environment effects in battles."""
    
    def __init__(self):
        self.EFFECT_COOLDOWNS = {
            "Skypiea": 3,      # Lightning effects every 3 turns
            "Alabasta": 2,     # Sandstorm effects every 2 turns
            "Punk Hazard": 4,  # Extreme climate every 4 turns
            "Raftel": 5,      # Ancient weapon effects every 5 turns
        }
        
        self.current_cooldowns = {}
        self.active_effects = {}
        
    async def apply_environment_effect(self, environment: str, players: list, turn: int) -> tuple[list[str], dict]:
        """Apply environment effects with proper cooldown management."""
        messages = []
        effect_data = {}
        
        # Check cooldown
        if self.current_cooldowns.get(environment, 0) > 0:
            self.current_cooldowns[environment] -= 1
            return messages, effect_data
            
        # Reset cooldown
        self.current_cooldowns[environment] = self.EFFECT_COOLDOWNS.get(environment, 2)
        
        if environment == "Skypiea":
            if random.random() < 0.3:  # 30% chance
                damage = random.randint(10, 15)
                effect_data = {
                    "type": "lightning",
                    "damage": damage,
                    "duration": 1
                }
                messages.append(f"⚡ Divine lightning strikes for {damage} damage!")
                
        elif environment == "Alabasta":
            if random.random() < 0.3:
                effect_data = {
                    "type": "sandstorm",
                    "accuracy_reduction": 0.2,
                    "duration": 2
                }
                messages.append("🌪️ Sandstorm reduces accuracy by 20% for 2 turns!")
                
        elif environment == "Punk Hazard":
            if random.random() < 0.3:
                damage = random.randint(5, 10)
                effect_data = {
                    "type": "extreme_climate",
                    "damage": damage,
                    "burn_amplification": 1.5,
                    "duration": 2
                }
                messages.append(f"🔥❄️ Extreme climate deals {damage} damage and amplifies burns!")
                
        elif environment == "Raftel":
            if random.random() < 0.2:  # Rare but powerful
                effect_data = {
                    "type": "ancient_weapon",
                    "damage_boost": 1.3,
                    "healing_boost": 1.3,
                    "duration": 1
                }
                messages.append("🏺 Ancient weapon power enhances all abilities!")
                
        return messages, effect_data
        
    async def calculate_environment_modifiers(self, environment: str, move_data: dict) -> tuple[dict, list[str]]:
        """Calculate move modifications based on environment."""
        messages = []
        modified_move = move_data.copy()
        
        # Get active effects
        active_effect = self.active_effects.get(environment, {})
        
        if environment == "Skypiea" and "lightning" in move_data.get("effect", ""):
            modified_move["damage"] = int(modified_move.get("damage", 0) * 1.2)
            messages.append("⚡ Lightning enhanced by Skypiea's atmosphere!")
            
        elif environment == "Alabasta" and "burn" in move_data.get("effect", ""):
            modified_move["burn_chance"] = modified_move.get("burn_chance", 0) + 0.1
            messages.append("🔥 Burn chance increased in the desert heat!")
            
        elif environment == "Punk Hazard":
            if active_effect.get("type") == "extreme_climate":
                if "burn" in move_data.get("effect", ""):
                    modified_move["burn_chance"] = modified_move.get("burn_chance", 0) * 1.5
                    messages.append("🌋 Burn effects amplified by extreme climate!")
                    
        elif environment == "Raftel":
            if active_effect.get("type") == "ancient_weapon":
                modified_move["damage"] = int(modified_move.get("damage", 0) * 1.3)
                if "heal" in move_data.get("effect", ""):
                    modified_move["heal_amount"] = int(modified_move.get("heal_amount", 0) * 1.3)
                messages.append("🏺 Move enhanced by ancient weapon power!")
                
        return modified_move, messages
        
    def clear_environment_effects(self):
        """Clear all active environment effects."""
        self.active_effects = {}
        self.current_cooldowns = {}

class StatusEffectManager:
    """Manages all status effects in battles."""
    
    def __init__(self):
        # Max stacks/durations for effects
        self.MAX_BURN_STACKS = 3
        self.MAX_STUN_DURATION = 2
        self.MAX_FREEZE_DURATION = 2
        self.MAX_POISON_STACKS = 3
        self.MAX_BIND_DURATION = 3
        self.MAX_ROOT_DURATION = 2
        self.MAX_SLOW_DURATION = 2
        
    async def apply_effect(self, effect_type: str, target: dict, value: int = 1, duration: int = 1):
        """Apply a status effect with proper stacking rules."""
        if "status" not in target:
            target["status"] = {}
            
        # Original effects
        if effect_type == "burn":
            current_stacks = target["status"].get("burn", 0)
            target["status"]["burn"] = min(current_stacks + value, self.MAX_BURN_STACKS)
            return f"🔥 Burn stacks: {target['status']['burn']}"
            
        elif effect_type == "stun":
            if not target["status"].get("stun", False):
                target["status"]["stun"] = min(duration, self.MAX_STUN_DURATION)
                return "⚡ Stunned!"
                
        elif effect_type == "freeze":
            current_freeze = target["status"].get("freeze", 0)
            target["status"]["freeze"] = min(current_freeze + duration, self.MAX_FREEZE_DURATION)
            return f"❄️ Frozen for {target['status']['freeze']} turns!"
            
        elif effect_type == "protect":
            target["status"]["protected"] = True
            target["status"]["protect_duration"] = duration
            return "🛡️ Protected!"

        # New effects for updated fruits
        elif effect_type == "poison":
            current_stacks = target["status"].get("poison", 0)
            target["status"]["poison"] = min(current_stacks + value, self.MAX_POISON_STACKS)
            return f"☠️ Poison stacks: {target['status']['poison']}"
            
        elif effect_type == "bind":
            target["status"]["bind"] = min(duration, self.MAX_BIND_DURATION)
            return f"🔒 Bound for {duration} turns!"
            
        elif effect_type == "root":
            target["status"]["root"] = min(duration, self.MAX_ROOT_DURATION)
            return f"🌿 Rooted for {duration} turns!"
            
        elif effect_type == "slow":
            target["status"]["slow"] = min(duration, self.MAX_SLOW_DURATION)
            return f"🐌 Slowed for {duration} turns!"
            
        elif effect_type == "defense_down":
            target["status"]["defense_down"] = duration
            return "🛡️ Defense reduced!"
            
        elif effect_type == "attack_down":
            target["status"]["attack_down"] = duration
            return "⚔️ Attack reduced!"
            
        elif effect_type == "defense_boost":
            target["status"]["defense_boost"] = duration
            return "🛡️ Defense boosted!"
            
        elif effect_type == "attack_boost":
            target["status"]["attack_boost"] = duration
            return "⚔️ Attack boosted!"
            
        elif effect_type == "speed_boost":
            target["status"]["speed_boost"] = duration
            return "💨 Speed boosted!"
            
        elif effect_type == "dodge":
            target["status"]["dodge"] = duration
            return "👻 Dodge active!"
            
        elif effect_type == "elemental_boost":
            target["status"]["elemental_boost"] = duration
            return "✨ Elemental power boosted!"
            
        elif effect_type == "status_immunity":
            target["status"]["status_immunity"] = duration
            return "🌟 Status immunity active!"
            
        elif effect_type == "thunder_charge":
            target["status"]["thunder_charge"] = duration
            return "⚡ Thunder charged!"
            
        elif effect_type == "shell_defense":
            target["status"]["shell_defense"] = duration
            return "🐢 Shell defense active!"

        return None

    async def process_effects(self, player: dict) -> tuple[list[str], int]:
        """Process all status effects on a player's turn."""
        if "status" not in player:
            return [], 0
            
        messages = []
        total_damage = 0
        
        # Process burn
        if player["status"].get("burn", 0) > 0:
            damage = 5 * player["status"]["burn"]
            total_damage += damage
            messages.append(f"🔥 Burn deals {damage} damage!")
            player["status"]["burn"] -= 1

        # Process poison
        if player["status"].get("poison", 0) > 0:
            damage = 8 * player["status"]["poison"]  # Poison does more damage than burn
            total_damage += damage
            messages.append(f"☠️ Poison deals {damage} damage!")
            player["status"]["poison"] -= 1
            
        # Process status effects that prevent actions
        for effect, message in [
            ("stun", "⚡ Stunned - Skip turn!"),
            ("freeze", "❄️ Frozen - Skip turn!"),
            ("bind", "🔒 Bound - Skip turn!"),
            ("root", "🌿 Rooted - Skip turn!")
        ]:
            if player["status"].get(effect, 0) > 0:
                messages.append(message)
                player["status"][effect] -= 1

        # Process buff/debuff durations
        for effect in [
            "protect", "defense_down", "attack_down", "defense_boost",
            "attack_boost", "speed_boost", "dodge", "elemental_boost",
            "status_immunity", "thunder_charge", "shell_defense"
        ]:
            effect_duration = f"{effect}_duration" if effect == "protect" else effect
            if player["status"].get(effect_duration, 0) > 0:
                player["status"][effect_duration] -= 1
                if player["status"][effect_duration] <= 0:
                    player["status"][effect] = False

        return messages, total_damage

    async def calculate_damage_with_effects(self, base_damage: int, attacker: dict, defender: dict) -> tuple[int, list[str]]:
        """Calculate final damage considering all status effects."""
        messages = []
        final_damage = base_damage
        
        # Defender effects
        if defender["status"].get("protected", False):
            final_damage = int(final_damage * 0.5)
            messages.append("🛡️ Damage reduced by protection!")
            
        if defender["status"].get("shell_defense", False):
            final_damage = int(final_damage * 0.6)  # 40% reduction
            messages.append("🐢 Shell defense reduces damage!")
            
        if defender["status"].get("defense_down", False):
            final_damage = int(final_damage * 1.3)  # 30% more damage taken
            messages.append("🛡️ Reduced defense increases damage!")
            
        # Attacker effects
        if attacker["status"].get("attack_boost", False):
            final_damage = int(final_damage * 1.3)
            messages.append("⚔️ Attack boost increases damage!")
            
        if attacker["status"].get("thunder_charge", False):
            final_damage = int(final_damage * 1.25)
            messages.append("⚡ Thunder charge amplifies damage!")
            
        if attacker["status"].get("elemental_boost", False):
            final_damage = int(final_damage * 1.2)
            messages.append("✨ Elemental boost increases damage!")
            
        if attacker["status"].get("attack_down", False):
            final_damage = int(final_damage * 0.7)  # 30% less damage dealt
            messages.append("⚔️ Attack down reduces damage!")
            
        return max(0, final_damage), messages
        
    def clear_all_effects(self, player: dict):
        """Clear all status effects from a player."""
        if "status" in player:
            player["status"] = {}
            
    def get_effect_duration(self, player: dict, effect_type: str) -> int:
        """Get the remaining duration of a specific effect."""
        if "status" not in player:
            return 0
        return player["status"].get(effect_type, 0)

class BattleStateManager:
    def __init__(self):
        self.active_battles = {}
        self.battle_locks = {}
        self._cleanup_threshold = 100  # Maximum number of stored battle states
        self._max_duration = 300  # Maximum battle duration in seconds

    async def create_battle(self, channel_id: int, challenger_data: dict, opponent_data: dict):
        """Create a new battle state."""
        if len(self.active_battles) >= self._cleanup_threshold:
            await self._cleanup_old_battles()
        
        battle_state = {
            "start_time": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "challenger": challenger_data,
            "opponent": opponent_data,
            "turn": 0,
            "current_player": 0,
            "environment": None,
            "battle_log": [],
            "is_finished": False
        }
        
        self.active_battles[channel_id] = battle_state
        self.battle_locks[channel_id] = asyncio.Lock()
        
        return battle_state

    async def end_battle(self, channel_id: int):
        """Clean up battle state after it ends."""
        if channel_id in self.active_battles:
            async with self.battle_locks[channel_id]:
                battle_state = self.active_battles[channel_id]
                battle_state["is_finished"] = True
                
                # Clean up
                del self.active_battles[channel_id]
                del self.battle_locks[channel_id]

    def is_channel_in_battle(self, channel_id: int) -> bool:
        """Check if a channel has an active battle."""
        return channel_id in self.active_battles

    async def _cleanup_old_battles(self):
        """Remove old or inactive battles."""
        current_time = datetime.utcnow()
        channels_to_remove = []

        for channel_id, battle in self.active_battles.items():
            battle_age = (current_time - battle["start_time"]).total_seconds()
            if battle_age > self._max_duration:
                channels_to_remove.append(channel_id)

        for channel_id in channels_to_remove:
            await self.end_battle(channel_id)

class BountyBattle(commands.Cog):
    """A combined One Piece RPG cog with Bounties & Deathmatches."""

    def __init__(self, bot):
        # Initialize Red's Cog class properly
        commands.Cog.__init__(self)
        self.bot = bot
        
        # Initialize config
        self.config = Config.get_conf(self, identifier=1357924680, force_registration=True)
        
        # Initialize all other attributes
        self.bounty_lock = Lock()
        self.battle_lock = Lock()
        self.data_lock = Lock()
        
        # Initialize managers
        self.battle_manager = BattleStateManager()
        self.status_manager = StatusEffectManager()
        self.environment_manager = EnvironmentManager()
        self.devil_fruit_manager = DevilFruitManager(self.status_manager, self.environment_manager)
        
        # Initialize tracking variables
        self.active_channels = set()
        self.tournaments = {}
        self.current_environment = None
        self.battle_stopped = False
        
        # Configure logging
        self.log = logging.getLogger("red.bounty")
        self.log.setLevel(logging.INFO)
        handler = logging.FileHandler(filename="/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/logs/bountybattle.log", encoding="utf-8", mode="w")
        handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        self.log.addHandler(handler)
        
        # Register guild settings
        default_guild = {
            "bounties": {},
            "event": None,
            "global_bank": 0,
            "last_bank_robbery": None,
            "tournaments": {},
            "beta_active": True,
            "leaderboard_channel": None,
            "announcement_channel": None,
            "active_events": {},
            "disabled_commands": [],
            "is_paused": False,
            "restricted_channel": None,
            "maintenance_mode": False
        }
        
        # Register member settings
        default_member = {
            "bounty": 0,
            "bank_balance": 0,
            "berries": 0,
            "last_daily_claim": None,
            "wins": 0,
            "losses": 0,
            "damage_dealt": 0,
            "achievements": [],
            "titles": [],
            "current_title": None,
            "devil_fruit": None,
            "last_active": None,
            "bounty_hunted": 0,
            "last_deposit_time": None,
            "win_streak": 0,
            "damage_taken": 0,
            "critical_hits": 0,
            "healing_done": 0,
            "turns_survived": 0,
            "burns_applied": 0,
            "stuns_applied": 0,
            "blocks_performed": 0,
            "damage_prevented": 0,
            "elements_used": [],
            "total_battles": 0,
            "perfect_victories": 0,
            "comebacks": 0,
            "fastest_victory": None,
            "longest_battle": None,
            "devil_fruit_mastery": 0,
            "successful_hunts": 0,
            "failed_hunts": 0
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # Initialize current_bosses directly in the class
        self.current_bosses = {
            "Marine Fortress": {
                "boss": random.choice(["Vice Admiral Momonga", "Vice Admiral Doberman", "Vice Admiral Onigumo"]),
                "level": "Easy",
                "next_rotation": datetime.utcnow() + timedelta(hours=4)
            },
            "Impel Down": {
                "boss": random.choice(["Magellan", "Hannyabal", "Sadi-chan"]),
                "level": "Medium",
                "next_rotation": datetime.utcnow() + timedelta(hours=6)
            },
            "Enies Lobby": {
                "boss": random.choice(["Rob Lucci", "Kaku", "Jabra"]),
                "level": "Hard",
                "next_rotation": datetime.utcnow() + timedelta(hours=8)
            },
            "Yonko Territory": {
                "boss": random.choice(["Charlotte Linlin (Big Mom)", "Kaido", "Shanks", "Marshall D. Teach"]),
                "level": "Very Hard",
                "next_rotation": datetime.utcnow() + timedelta(hours=12)
            },
            "Mary Geoise": {
                "boss": random.choice(["The Five Elders", "Im-sama", "CP0"]),
                "level": "Extreme",
                "next_rotation": datetime.utcnow() + timedelta(hours=24)
            }
        }

    async def update_hunter_stats(self, hunter, steal_amount):
        """Update hunter's statistics and check for title unlocks."""
        current_stolen = await self.config.member(hunter).bounty_hunted() or 0
        total_stolen = current_stolen + steal_amount
        await self.config.member(hunter).bounty_hunted.set(total_stolen)

        if total_stolen >= 100_000:
            unlocked_titles = await self.config.member(hunter).titles()
            if "The Bounty Hunter" not in unlocked_titles:
                unlocked_titles.append("The Bounty Hunter")
                await self.config.member(hunter).titles.set(unlocked_titles)
                return True
        return False

    async def update_activity(self, hunter, target):
        """Update last active timestamp for both participants."""
        current_time = datetime.utcnow().isoformat()
        await self.config.member(hunter).last_active.set(current_time)
        await self.config.member(target).last_active.set(current_time)
        
    async def sync_bounty(self, user):
        """
        Synchronize bounty data for a user between config and bounties.json.
        
        Returns the synchronized bounty amount.
        """
        # Load current bounty data
        bounties = load_bounties()
        user_id = str(user.id)
        
        # Get bounty from config and bounties.json
        config_bounty = await self.config.member(user).bounty()
        json_bounty = bounties.get(user_id, {}).get("amount", 0)
        
        # Use the higher value as the source of truth
        true_bounty = max(config_bounty, json_bounty)
        
        # Update both systems
        bounties[user_id] = bounties.get(user_id, {})
        bounties[user_id]["amount"] = true_bounty
        
        # Save back to file
        save_bounties(bounties)
        
        # Update config
        await self.config.member(user).bounty.set(true_bounty)
        
        return true_bounty
        
    async def safe_save_bounties(self, bounties, error_message="Failed to save bounty data"):
        """Thread-safe method to save bounties."""
        async with self.bounty_lock:
            try:
                save_bounties(bounties)
                return True
            except Exception as e:
                logger.error(f"{error_message}: {e}")
                return False
        
    async def safe_modify_bounty(self, user, amount, operation="add"):
        """Thread-safe method to modify a user's bounty."""
        async with self.bounty_lock:
            try:
                bounties = load_bounties()
                user_id = str(user.id)
                
                if user_id not in bounties:
                    bounties[user_id] = {"amount": 0, "fruit": None}
                
                if operation == "add":
                    bounties[user_id]["amount"] += amount
                elif operation == "subtract":
                    bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - amount)
                elif operation == "set":
                    bounties[user_id]["amount"] = amount
                
                await self.safe_save_bounties(bounties)
                await self.config.member(user).bounty.set(bounties[user_id]["amount"])
                return bounties[user_id]["amount"]
            except Exception as e:
                logger.error(f"Error modifying bounty: {e}")
                return None

    async def safe_read_bounty(self, user):
        """Thread-safe method to read a user's bounty."""
        async with self.data_lock:
            try:
                bounties = load_bounties()
                user_id = str(user.id)
                return bounties.get(user_id, {}).get("amount", 0)
            except Exception as e:
                logger.error(f"Error reading bounty: {e}")
                return 0
            
    def update_cooldowns(self, player_data: dict):
        """
        Update cooldowns at the start of a player's turn.
        
        Parameters:
        -----------
        player_data : dict
            The player's data dictionary containing their moves_on_cooldown
        """
        # Create a copy of the keys to avoid modifying dict during iteration
        moves = list(player_data["moves_on_cooldown"].keys())
        
        for move in moves:
            player_data["moves_on_cooldown"][move] -= 1
            if player_data["moves_on_cooldown"][move] <= 0:
                del player_data["moves_on_cooldown"][move]

    def is_move_available(self, move_name, player_data):
        """Check if a move is available to use."""
        return move_name not in player_data["moves_on_cooldown"]

    def set_move_cooldown(self, move_name: str, cooldown: int, player_data: dict):
        """
        Set a cooldown for a move on a player.
        
        Parameters:
        -----------
        move_name : str
            The name of the move to put on cooldown
        cooldown : int
            Number of turns the move should be on cooldown
        player_data : dict
            The player's data dictionary containing their moves_on_cooldown
        """
        player_data["moves_on_cooldown"][move_name] = cooldown
        player_data["stats"]["cooldowns_managed"] += 1

    def apply_burn_effect(self, defender_data):
        """Apply burn damage and reduce stacks."""
        if defender_data["status"]["burn"] > 0:
            burn_damage = 5 * defender_data["status"]["burn"]
            defender_data["hp"] -= burn_damage
            defender_data["status"]["burn"] -= 1
            return burn_damage
        return 0

    def apply_stun_effect(self, attacker_data):
        """Check and apply stun effect."""
        if attacker_data["status"]["stun"]:
            attacker_data["status"]["stun"] = False
            return True
        return False

    def apply_healing_effect(self, attacker_data, heal_amount):
        """Apply healing with proper bounds."""
        original_hp = attacker_data["hp"]
        attacker_data["hp"] = min(250, attacker_data["hp"] + heal_amount)
        return attacker_data["hp"] - original_hp
    
    async def _process_victory(self, ctx, winner_data, loser_data):
        """Process victory rewards with simplified logic."""
        try:
            # Get member objects
            winner = winner_data["member"]
            loser = loser_data["member"]
            
            # Simple reward calculations
            bounty_increase = 1000  # Fixed increase for now
            bounty_decrease = 500   # Fixed decrease for now
            
            # Update winner's bounty
            async with self.config.member(winner).all() as winner_data:
                current_bounty = winner_data.get("bounty", 0)
                if not isinstance(current_bounty, int):
                    current_bounty = 0
                new_bounty = current_bounty + bounty_increase
                winner_data["bounty"] = new_bounty
                winner_data["wins"] = winner_data.get("wins", 0) + 1

            # Update loser's bounty
            async with self.config.member(loser).all() as loser_data:
                current_bounty = loser_data.get("bounty", 0)
                if not isinstance(current_bounty, int):
                    current_bounty = 0
                new_bounty = max(0, current_bounty - bounty_decrease)
                loser_data["bounty"] = new_bounty
                loser_data["losses"] = loser_data.get("losses", 0) + 1

            # Create simple victory message
            embed = discord.Embed(
                title="🏆 Battle Results",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name=f"Winner: {winner.display_name}",
                value=f"Gained {bounty_increase:,} Berries\nNew Bounty: {new_bounty:,} Berries",
                inline=False
            )
            
            embed.add_field(
                name=f"Loser: {loser.display_name}",
                value=f"Lost {bounty_decrease:,} Berries\nNew Bounty: {new_bounty:,} Berries",
                inline=False
            )
            
            await ctx.send(embed=embed)

            # Update last active time
            current_time = datetime.utcnow().isoformat()
            await self.config.member(winner).last_active.set(current_time)
            await self.config.member(loser).last_active.set(current_time)

        except Exception as e:
            logger.error(f"Error in _process_victory: {str(e)}")
            await ctx.send("An error occurred while processing rewards.")
            
    async def _initialize_player_data(self, member):
        """Initialize player data with proper memory management."""
        devil_fruit = await self.config.member(member).devil_fruit()
        return {
            "name": member.display_name,
            "hp": 250,
            "member": member,
            "fruit": devil_fruit,
            "moves_on_cooldown": {},
            "status": {
                "burn": 0,
                "stun": False,
                "frozen": 0,
                "transformed": 0,
                "protected": False,
                "block_active": False,
                "accuracy_reduction": 0,
                "accuracy_turns": 0,
                "elements_used": set()
            },
            "stats": {
                "damage": 0,
                "heal": 0,
                "critical_hits": 0,
                "blocks": 0,
                "burns_applied": 0,
                "stuns_applied": 0,
                "damage_dealt": 0,
                "damage_taken": 0,
                "healing_done": 0,
                "turns_survived": 0,
                "cooldowns_managed": 0
            }
        }
    
    async def sync_user_data(self, member):
        """Synchronize all user data between config and JSON."""
        try:
            # Sync bounty
            bounties = load_bounties()
            user_id = str(member.id)
            config_bounty = await self.config.member(member).bounty()
            json_bounty = bounties.get(user_id, {}).get("amount", 0)
            true_bounty = max(config_bounty, json_bounty)
            
            # Update both systems
            bounties[user_id] = bounties.get(user_id, {})
            bounties[user_id]["amount"] = true_bounty
            save_bounties(bounties)
            await self.config.member(member).bounty.set(true_bounty)
            
            # Sync devil fruit with validation
            config_fruit = await self.config.member(member).devil_fruit()
            json_fruit = bounties[user_id].get("fruit")
            
            # Validate fruits
            def is_valid_fruit(fruit):
                return (
                    fruit in DEVIL_FRUITS.get('Common', {}) or 
                    fruit in DEVIL_FRUITS.get('Rare', {})
                )
            
            # Choose a valid fruit, prioritizing config if valid
            valid_fruit = None
            if is_valid_fruit(config_fruit):
                valid_fruit = config_fruit
            elif is_valid_fruit(json_fruit):
                valid_fruit = json_fruit
            
            # Update both systems with valid fruit
            if valid_fruit:
                bounties[user_id]["fruit"] = valid_fruit
                await self.config.member(member).devil_fruit.set(valid_fruit)
            else:
                # Clear invalid fruits
                if user_id in bounties:
                    bounties[user_id]["fruit"] = None
                await self.config.member(member).devil_fruit.set(None)
            
            # Save changes
            save_bounties(bounties)
            
            return true_bounty
            
        except Exception as e:
            logger.error(f"Error in sync_user_data: {str(e)}")
            return None
    
    async def cleanup_inactive_fruits(self, ctx, days_inactive: int = 30):
        """Clean up Devil Fruits from inactive players."""
        try:
            current_time = datetime.utcnow()
            bounties = load_bounties()
            cleaned_fruits = []

            for user_id, data in bounties.items():
                # Skip if no fruit
                if not data.get("fruit"):
                    continue

                try:
                    member = ctx.guild.get_member(int(user_id))
                    if not member:
                        continue

                    last_active = await self.config.member(member).last_active()
                    if not last_active:
                        continue

                    last_active_date = datetime.fromisoformat(last_active)
                    days_since_active = (current_time - last_active_date).days

                    # Remove fruit if inactive for specified period
                    if days_since_active >= days_inactive:
                        fruit_name = data["fruit"]
                        bounties[user_id]["fruit"] = None
                        await self.config.member(member).devil_fruit.set(None)
                        cleaned_fruits.append((member.display_name, fruit_name))

                except (ValueError, AttributeError) as e:
                    logger.error(f"Error processing user {user_id}: {e}")
                    continue

            # Save changes
            save_bounties(bounties)

            # Create report embed
            if cleaned_fruits:
                embed = discord.Embed(
                    title="<:MeraMera:1336888578705330318> Devil Fruit Cleanup Report",
                    description=f"Removed fruits from {len(cleaned_fruits)} inactive players.",
                    color=discord.Color.blue()
                )
                
                for name, fruit in cleaned_fruits:
                    embed.add_field(
                        name=f"Removed from {name}",
                        value=f"Fruit: `{fruit}`",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("✅ No inactive Devil Fruit users found!")

        except Exception as e:
            logger.error(f"Error in cleanup_inactive_fruits: {e}")
            await ctx.send("❌ An error occurred during fruit cleanup.")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle Devil Fruit cleanup when a member leaves the server."""
        try:
            bounties = load_bounties()
            user_id = str(member.id)

            if user_id in bounties and bounties[user_id].get("fruit"):
                fruit_name = bounties[user_id]["fruit"]
                
                # Check if it's a rare fruit
                is_rare = fruit_name in DEVIL_FRUITS["Rare"]
                
                # Remove the fruit
                bounties[user_id]["fruit"] = None
                save_bounties(bounties)
                await self.config.member(member).devil_fruit.set(None)

                # Announce if it was a rare fruit
                if is_rare:
                    for guild in self.bot.guilds:
                        channel = discord.utils.get(guild.text_channels, name="bot-commands")
                        if channel:
                            embed = discord.Embed(
                                title="🌟 Rare Devil Fruit Available!",
                                description=(
                                    f"The `{fruit_name}` has returned to circulation!\n"
                                    f"Previous owner left the server."
                                ),
                                color=discord.Color.gold()
                            )
                            await channel.send(embed=embed)

        except Exception as e:
            logger.error(f"Error handling member remove: {e}")
            
    async def process_raid_reactions(self, message, emoji="⚔️"):
        """Helper function to process raid reactions properly."""
        raiders = []
        try:
            for reaction in message.reactions:
                if str(reaction.emoji) == emoji:
                    # Use proper async iteration pattern
                    async for user in reaction.users():
                        if not user.bot:
                            raiders.append(user)
        except discord.Forbidden:
            logger.error("Missing permissions to fetch reaction users")
        except discord.HTTPException:
            logger.error("Failed to get reaction users")
        except Exception as e:
            logger.error(f"Error processing reactions: {e}")
        return raiders

    async def validate_fruit_transfer(self, ctx, member: discord.Member, fruit_name: str) -> bool:
        """Validate if a fruit can be transferred to a member."""
        try:
            bounties = load_bounties()
            
            # Check if the fruit exists
            fruit_exists = False
            fruit_rarity = None
            
            for rarity, fruits in DEVIL_FRUITS.items():
                if fruit_name in fruits:
                    fruit_exists = True
                    fruit_rarity = rarity
                    break
                    
            if not fruit_exists:
                await ctx.send(f"❌ The fruit `{fruit_name}` does not exist!")
                return False

            # Check if member already has a fruit
            user_id = str(member.id)
            if user_id in bounties and bounties[user_id].get("fruit"):
                await ctx.send(f"❌ {member.display_name} already has the `{bounties[user_id]['fruit']}`!")
                return False

            # Only check for uniqueness if it's a rare fruit
            if fruit_rarity == "Rare":
                for user_data in bounties.values():
                    if user_data.get("fruit") == fruit_name:
                        await ctx.send(f"❌ The rare fruit `{fruit_name}` is already owned by another player!")
                        return False

            return True

        except Exception as e:
            logger.error(f"Error in validate_fruit_transfer: {e}")
            await ctx.send("❌ An error occurred while validating the fruit transfer.")
            return False
        
    async def check_hidden_titles(self, member):
        """Check if a user has earned any hidden titles based on their stats."""
        # Get user stats from config
        stats = await self.config.member(member).all()
        earned_hidden_titles = []
        
        # Check each hidden title condition
        for title, data in HIDDEN_TITLES.items():
            condition = data["condition"]
            
            # Win streak titles
            if "Win 10 battles without losing" in condition and stats.get("win_streak", 0) >= 10:
                earned_hidden_titles.append(title)
                
            # Bounty hunter title
            if "Steal 100,000 Berries" in condition and stats.get("bounty_hunted", 0) >= 100000:
                earned_hidden_titles.append(title)
                
            # Underdog title
            if "bounty 5x higher" in condition and stats.get("underdog_wins", 0) > 0:
                earned_hidden_titles.append(title)
                
            # Kingmaker title
            if "Help an ally win" in condition and stats.get("ally_victories", 0) >= 5:
                earned_hidden_titles.append(title)
                
            # Ghost title
            if "Evade 3 attacks" in condition and stats.get("consecutive_evades", 0) >= 3:
                earned_hidden_titles.append(title)
                
            # Berserker title  
            if "Deal 100 damage" in condition and stats.get("highest_damage", 0) >= 100:
                earned_hidden_titles.append(title)
                
            # Marine Slayer title
            if "Marine-themed titles" in condition and stats.get("marine_defeats", 0) >= 5:
                earned_hidden_titles.append(title)
        
        return earned_hidden_titles

    # ------------------ Bounty System ------------------

    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        user = ctx.author
        
        # Load bounties from both sources
        bounties = load_bounties()
        user_id = str(user.id)
        
        # Check both config and JSON for existing bounty
        config_bounty = await self.config.member(user).bounty()
        json_bounty = bounties.get(user_id, {}).get("amount", 0)
        
        # Preserve existing data, including zero bounties
        if user_id in bounties or config_bounty is not None:
            true_bounty = max(config_bounty, json_bounty)
            
            # Sync both systems
            bounties[user_id] = bounties.get(user_id, {})
            bounties[user_id]["amount"] = true_bounty
            save_bounties(bounties)
            await self.config.member(user).bounty.set(true_bounty)
            
            # If they have any existing data
            if true_bounty > 0:
                return await ctx.send(f"Ye already have a bounty of `{true_bounty:,}` Berries, ye scallywag!")
                
        # For both new players and those with 0 bounty
        try:
            initial_bounty = random.randint(50, 100)
            
            # Update bounty while preserving other data
            if user_id in bounties:
                bounties[user_id]["amount"] = initial_bounty
            else:
                bounties[user_id] = {
                    "amount": initial_bounty,
                    "fruit": None
                }
            save_bounties(bounties)
            await self.config.member(user).bounty.set(initial_bounty)
            
            # Initialize stats only if they don't exist
            if not await self.config.member(user).wins():
                await self.config.member(user).wins.set(0)
            if not await self.config.member(user).losses():
                await self.config.member(user).losses.set(0)
            
            # Always update last active time
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())
            
            # Create appropriate embed
            if user_id in bounties and bounties[user_id].get("fruit"):
                embed = discord.Embed(
                    title="🏴‍☠️ Bounty Renewed!",
                    description=f"**{user.display_name}**'s bounty has been renewed!",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="🏴‍☠️ Welcome to the Grand Line!",
                    description=f"**{user.display_name}** has started their pirate journey!",
                    color=discord.Color.blue()
                )
            
            embed.add_field(
                name="Initial Bounty",
                value=f"`{initial_bounty:,}` Berries",
                inline=False
            )
            
            # Check for beta tester title
            beta_active = await self.config.guild(ctx.guild).beta_active()
            if beta_active:
                unlocked_titles = await self.config.member(user).titles()
                if "BETA TESTER" not in unlocked_titles:
                    unlocked_titles.append("BETA TESTER")
                    await self.config.member(user).titles.set(unlocked_titles)
                    embed.add_field(
                        name="🎖️ Special Title Unlocked",
                        value="`BETA TESTER`",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in startbounty: {str(e)}")
            await ctx.send("⚠️ An error occurred while starting your bounty journey. Please try again.")
            
    @commands.command()
    async def bankstats(self, ctx):
        """View statistics about World Government bank fees and taxes."""
        global_bank = await self.config.guild(ctx.guild).global_bank()
        
        # Create detailed embed
        embed = discord.Embed(
            title="🏦 World Government Bank Statistics",
            description="Detailed breakdown of Marine fees and taxes",
            color=discord.Color.gold()
        )
        
        # Show fee structure
        embed.add_field(
            name="📊 Fee Structure",
            value=(
                "**Deposit Fees:**\n"
                "• Tax: 10% of deposit\n"
                "• Processing Fee: 1-5% of deposit\n\n"
                "**Withdrawal Fees:**\n"
                "• Base Fee: 2-8% of withdrawal\n"
                "• Interest: 1% per hour (compounds)\n"
                "• Surprise Audit: 5% of remaining balance (10% chance)\n\n"
                "**All fees go to the World Government Treasury**"
            ),
            inline=False
        )
        
        # Show current treasury
        embed.add_field(
            name="🏛️ Current Treasury",
            value=f"`{global_bank:,}` Berries",
            inline=False
        )
        
        # Show example calculation
        deposit_amount = 100000
        tax = int(deposit_amount * 0.10)
        proc_fee = int(deposit_amount * 0.03)  # Example 3%
        total_fees = tax + proc_fee
        
        embed.add_field(
            name="💰 Example Transaction (100,000 Berry Deposit)",
            value=(
                f"Base Amount: `{deposit_amount:,}` Berries\n"
                f"Tax (10%): `{tax:,}` Berries\n"
                f"Processing Fee (3%): `{proc_fee:,}` Berries\n"
                f"Total Fees: `{total_fees:,}` Berries\n"
                f"Net Deposit: `{deposit_amount - total_fees:,}` Berries"
            ),
            inline=False
        )
        
        embed.set_footer(text="The Marines thank you for your continued cooperation! 🫡")
        
        await ctx.send(embed=embed)
    
    @commands.group(name="bountybank", aliases=["bbank"], invoke_without_command=True)
    async def bountybank(self, ctx):
        """Check your bank balance and the global bank amount."""
        user = ctx.author
        
        # Get balances
        bank_balance = await self.config.member(user).bank_balance()
        global_bank = await self.config.guild(ctx.guild).global_bank()
        last_deposit = await self.config.member(user).last_deposit_time()
        
        # Calculate interest that will go to global bank (1% per hour)
        current_time = datetime.utcnow()
        interest_pending = 0
        
        if last_deposit and bank_balance > 0:
            last_deposit_time = datetime.fromisoformat(last_deposit)
            hours_passed = (current_time - last_deposit_time).total_seconds() / 3600
            interest_rate = hours_passed * 0.1  # 1% per hour, no cap
            interest_pending = int(bank_balance * interest_rate)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Status",
            description="The World Government charges fees and interest on all stored Berries!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Your Bank Balance",
            value=f"`{bank_balance:,}` Berries",
            inline=False
        )
        
        if interest_pending > 0:
            embed.add_field(
                name="⚠️ Interest Due",
                value=(
                    f"`{interest_pending:,}` Berries\n"
                    "*Interest will be collected on withdrawal or during random Marine audits!*"
                ),
                inline=False
            )
        
        embed.add_field(
            name="World Government Treasury",
            value=f"`{global_bank:,}` Berries",
            inline=False
        )
        
        embed.set_footer(text="💸 Interest Rate: 1% per hour (Compounds continuously)")
        await ctx.send(embed=embed)

    @bountybank.command(name="deposit")
    async def bank_deposit(self, ctx, amount):
        """Deposit bounty into your bank account (10% tax goes to World Government)."""
        user = ctx.author
        
        # Sync bounty data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking your bounty.")
        
        # Handle 'all' case
        if str(amount).lower() == 'all':
            amount = true_bounty
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send("❌ Please provide a valid number or 'all'!")
        
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive!")
            
        if amount > true_bounty:
            return await ctx.send(f"❌ You only have `{true_bounty:,}` Berries to deposit!")
        
        # Calculate tax (10%) plus random "processing fee" (1-5%)
        tax = int(amount * 0.10)
        processing_fee = int(amount * random.uniform(0.01, 0.05))
        total_fees = tax + processing_fee
        deposit_amount = amount - total_fees
        
        # Update bounties
        bounties = load_bounties()
        user_id = str(user.id)
        
        if user_id not in bounties:
            return await ctx.send("🏴‍☠️ Start your bounty journey first with `.startbounty`!")
        
        # Remove from bounty
        bounties[user_id]["amount"] -= amount
        save_bounties(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])
        
        # Add to bank (minus fees)
        current_balance = await self.config.member(user).bank_balance()
        await self.config.member(user).bank_balance.set(current_balance + deposit_amount)
        
        # Update last deposit time for interest calculation
        await self.config.member(user).last_deposit_time.set(datetime.utcnow().isoformat())
        
        # Add fees to global bank
        global_bank = await self.config.guild(ctx.guild).global_bank()
        await self.config.guild(ctx.guild).global_bank.set(global_bank + total_fees)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Deposit",
            description=(
                f"Deposited: `{amount:,}` Berries\n"
                f"Tax (10%): `{tax:,}` Berries\n"
                f"Processing Fee: `{processing_fee:,}` Berries\n"
                f"Net Deposit: `{deposit_amount:,}` Berries\n\n"
                f"⚠️ *Interest of 5% per hour will be collected by the World Government!*"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

    @bountybank.command(name="withdraw")
    async def bank_withdraw(self, ctx, amount):
        """Withdraw bounty from your bank account (subject to fees and interest collection)."""
        user = ctx.author
        
        # Check bank balance
        bank_balance = await self.config.member(user).bank_balance()
        last_deposit = await self.config.member(user).last_deposit_time()
        
        # Calculate accumulated interest
        current_time = datetime.utcnow()
        interest_due = 0
        
        if last_deposit:
            last_deposit_time = datetime.fromisoformat(last_deposit)
            hours_passed = (current_time - last_deposit_time).total_seconds() / 3600
            interest_rate = hours_passed * 0.01  # 1% per hour
            interest_due = int(bank_balance * interest_rate)
        
        # Handle 'all' case
        if str(amount).lower() == 'all':
            amount = bank_balance
        else:
            try:
                amount = int(amount)
            except ValueError:
                return await ctx.send("❌ Please provide a valid number or 'all'!")
        
        if amount <= 0:
            return await ctx.send("❌ Amount must be positive!")
        
        if amount > bank_balance:
            return await ctx.send(f"❌ You only have `{bank_balance:,}` Berries in your bank!")
        
        # Calculate withdrawal fee (2-8% random fee)
        withdrawal_fee = int(amount * random.uniform(0.02, 0.08))
        total_deductions = withdrawal_fee + interest_due
        final_amount = amount - total_deductions
        
        # Ensure they can afford the fees
        if total_deductions > bank_balance:
            return await ctx.send(
                f"❌ Cannot withdraw! Outstanding fees (`{total_deductions:,}` Berries) exceed your balance!"
            )
        
        # Update bank balance
        await self.config.member(user).bank_balance.set(bank_balance - amount)
        await self.config.member(user).last_deposit_time.set(current_time.isoformat())
        
        # Add to bounty
        bounties = load_bounties()
        user_id = str(user.id)
        bounties[user_id]["amount"] += final_amount
        save_bounties(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])
        
        # Add fees and interest to global bank
        global_bank = await self.config.guild(ctx.guild).global_bank()
        await self.config.guild(ctx.guild).global_bank.set(global_bank + total_deductions)
        
        embed = discord.Embed(
            title="🏦 World Government Bank Withdrawal",
            description=(
                f"Withdrawal Amount: `{amount:,}` Berries\n"
                f"Interest Collected: `{interest_due:,}` Berries\n"
                f"Withdrawal Fee: `{withdrawal_fee:,}` Berries\n"
                f"Amount Received: `{final_amount:,}` Berries"
            ),
            color=discord.Color.green()
        )
        
        # Random chance of additional "audit"
        if random.random() < 0.10:  # 10% chance
            audit_fee = int(bank_balance * 0.05)  # 5% of remaining balance
            await self.config.member(user).bank_balance.set(bank_balance - amount - audit_fee)
            await self.config.guild(ctx.guild).global_bank.set(global_bank + total_deductions + audit_fee)
            
            embed.add_field(
                name="🏛️ SURPRISE MARINE AUDIT!",
                value=f"The Marines conducted a random audit and collected `{audit_fee:,}` Berries in fees!",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    @commands.group(name="bbadmin")
    @commands.admin_or_permissions(administrator=True)
    async def bb_admin(self, ctx):
        """Admin controls for BountyBattle (Admin only)"""
        if ctx.invoked_subcommand is None:
            # Show current status
            settings = await self.config.guild(ctx.guild).all()
            
            embed = discord.Embed(
                title="🛠️ BountyBattle Admin Panel",
                color=discord.Color.blue()
            )
            
            # Get status information
            is_paused = settings.get("is_paused", False)
            restricted_channel = settings.get("restricted_channel")
            disabled_commands = settings.get("disabled_commands", [])
            maintenance_mode = settings.get("maintenance_mode", False)
            
            if restricted_channel:
                channel = ctx.guild.get_channel(restricted_channel)
                channel_name = channel.name if channel else "Unknown"
            else:
                channel_name = "None"
            
            embed.add_field(
                name="📊 Current Status",
                value=(
                    f"🔒 System Paused: `{'Yes' if is_paused else 'No'}`\n"
                    f"📍 Restricted Channel: `{channel_name}`\n"
                    f"🛠️ Maintenance Mode: `{'Yes' if maintenance_mode else 'No'}`\n"
                    f"❌ Disabled Commands: `{', '.join(disabled_commands) if disabled_commands else 'None'}`"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Available Commands",
                value=(
                    "`pause` - Temporarily pause all commands\n"
                    "`unpause` - Resume all commands\n"
                    "`restrict` - Restrict commands to one channel\n"
                    "`unrestrict` - Remove channel restriction\n"
                    "`disable` - Disable specific commands\n"
                    "`enable` - Re-enable specific commands\n"
                    "`maintenance` - Toggle maintenance mode\n"
                    "`status` - Show current status"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)

    @bb_admin.command(name="pause")
    async def pause_system(self, ctx, duration: str = None):
        """Temporarily pause all BountyBattle commands.
        
        Duration format: 1h, 30m, etc. Leave blank for indefinite."""
        await self.config.guild(ctx.guild).is_paused.set(True)
        
        if duration:
            try:
                # Parse duration
                time_convert = {"h": 3600, "m": 60, "s": 1}
                time_str = duration[-1].lower()
                time_amount = int(duration[:-1])
                seconds = time_amount * time_convert[time_str]
                
                embed = discord.Embed(
                    title="⏸️ System Paused",
                    description=f"BountyBattle commands paused for {duration}",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                
                # Wait and then unpause
                await asyncio.sleep(seconds)
                await self.config.guild(ctx.guild).is_paused.set(False)
                
                embed = discord.Embed(
                    title="▶️ System Resumed",
                    description="BountyBattle commands have been automatically resumed",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
            except (KeyError, ValueError):
                await ctx.send("❌ Invalid duration format! Use format like: 1h, 30m, 60s")
        else:
            embed = discord.Embed(
                title="⏸️ System Paused",
                description="BountyBattle commands paused indefinitely",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @bb_admin.command(name="unpause")
    async def unpause_system(self, ctx):
        """Resume all BountyBattle commands."""
        await self.config.guild(ctx.guild).is_paused.set(False)
        
        embed = discord.Embed(
            title="▶️ System Resumed",
            description="BountyBattle commands have been resumed",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="restrict")
    async def restrict_channel(self, ctx, channel: discord.TextChannel = None):
        """Restrict BountyBattle commands to a specific channel."""
        channel = channel or ctx.channel
        await self.config.guild(ctx.guild).restricted_channel.set(channel.id)
        
        embed = discord.Embed(
            title="📍 Channel Restricted",
            description=f"BountyBattle commands restricted to {channel.mention}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="unrestrict")
    async def unrestrict_channel(self, ctx):
        """Remove channel restriction for BountyBattle commands."""
        await self.config.guild(ctx.guild).restricted_channel.set(None)
        
        embed = discord.Embed(
            title="🔓 Channel Restriction Removed",
            description="BountyBattle commands can now be used in any channel",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @bb_admin.command(name="disable")
    async def disable_commands(self, ctx, *commands):
        """Disable specific BountyBattle commands."""
        if not commands:
            return await ctx.send("❌ Please specify which commands to disable!")
            
        disabled_commands = await self.config.guild(ctx.guild).disabled_commands()
        newly_disabled = []
        
        for cmd in commands:
            if hasattr(self, cmd) and cmd not in disabled_commands:
                disabled_commands.append(cmd)
                newly_disabled.append(cmd)
        
        await self.config.guild(ctx.guild).disabled_commands.set(disabled_commands)
        
        if newly_disabled:
            embed = discord.Embed(
                title="❌ Commands Disabled",
                description=f"Disabled commands: `{', '.join(newly_disabled)}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No new commands were disabled.")

    @bb_admin.command(name="enable")
    async def enable_commands(self, ctx, *commands):
        """Re-enable specific BountyBattle commands."""
        if not commands:
            return await ctx.send("❌ Please specify which commands to enable!")
            
        disabled_commands = await self.config.guild(ctx.guild).disabled_commands()
        newly_enabled = []
        
        for cmd in commands:
            if cmd in disabled_commands:
                disabled_commands.remove(cmd)
                newly_enabled.append(cmd)
        
        await self.config.guild(ctx.guild).disabled_commands.set(disabled_commands)
        
        if newly_enabled:
            embed = discord.Embed(
                title="✅ Commands Enabled",
                description=f"Re-enabled commands: `{', '.join(newly_enabled)}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No commands were enabled.")

    @bb_admin.command(name="maintenance")
    async def toggle_maintenance(self, ctx, duration: str = None):
        """Toggle maintenance mode for BountyBattle.
        
        Duration format: 1h, 30m, etc. Leave blank for indefinite."""
        current_mode = await self.config.guild(ctx.guild).maintenance_mode()
        
        if current_mode:
            await self.config.guild(ctx.guild).maintenance_mode.set(False)
            embed = discord.Embed(
                title="✅ Maintenance Mode Ended",
                description="BountyBattle is now fully operational",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return
            
        await self.config.guild(ctx.guild).maintenance_mode.set(True)
        
        if duration:
            try:
                # Parse duration
                time_convert = {"h": 3600, "m": 60, "s": 1}
                time_str = duration[-1].lower()
                time_amount = int(duration[:-1])
                seconds = time_amount * time_convert[time_str]
                
                embed = discord.Embed(
                    title="🛠️ Maintenance Mode Active",
                    description=f"BountyBattle entering maintenance mode for {duration}",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                
                # Wait and then end maintenance
                await asyncio.sleep(seconds)
                await self.config.guild(ctx.guild).maintenance_mode.set(False)
                
                embed = discord.Embed(
                    title="✅ Maintenance Complete",
                    description="BountyBattle is now fully operational",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
                
            except (KeyError, ValueError):
                await ctx.send("❌ Invalid duration format! Use format like: 1h, 30m, 60s")
        else:
            embed = discord.Embed(
                title="🛠️ Maintenance Mode Active",
                description="BountyBattle entering maintenance mode indefinitely",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @bb_admin.command(name="status")
    async def show_status(self, ctx):
        """Show current BountyBattle system status."""
        settings = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="📊 BountyBattle System Status",
            color=discord.Color.blue()
        )
        
        # Get status information
        is_paused = settings.get("is_paused", False)
        restricted_channel = settings.get("restricted_channel")
        disabled_commands = settings.get("disabled_commands", [])
        maintenance_mode = settings.get("maintenance_mode", False)
        
        if restricted_channel:
            channel = ctx.guild.get_channel(restricted_channel)
            channel_name = channel.mention if channel else "Unknown"
        else:
            channel_name = "None"
        
        embed.add_field(
            name="System State",
            value=(
                f"🔒 System Paused: `{'Yes' if is_paused else 'No'}`\n"
                f"📍 Restricted Channel: {channel_name}\n"
                f"🛠️ Maintenance Mode: `{'Yes' if maintenance_mode else 'No'}`"
            ),
            inline=False
        )
        
        if disabled_commands:
            embed.add_field(
                name="❌ Disabled Commands",
                value=f"`{', '.join(disabled_commands)}`",
                inline=False
            )
        
        await ctx.send(embed=embed)

    async def check_command_available(self, ctx):
        """Check if a command can be run based on current settings."""
        if not ctx.guild:
            return True  # Allow DMs
            
        if await self.bot.is_owner(ctx.author):
            return True  # Allow bot owner to bypass restrictions
            
        if ctx.author.guild_permissions.administrator:
            return True  # Allow admins to bypass restrictions
            
        settings = await self.config.guild(ctx.guild).all()
        
        # Check if system is paused
        if settings.get("is_paused", False):
            await ctx.send("⏸️ BountyBattle is currently paused!")
            return False
            
        # Check if in maintenance mode
        if settings.get("maintenance_mode", False):
            await ctx.send("🛠️ BountyBattle is currently in maintenance mode!")
            return False
            
        # Check if command is disabled
        if ctx.command.name in settings.get("disabled_commands", []):
            await ctx.send(f"❌ The command `{ctx.command.name}` is currently disabled!")
            return False
            
        # Check channel restriction
        restricted_channel = settings.get("restricted_channel")
        if restricted_channel and ctx.channel.id != restricted_channel:
            channel = ctx.guild.get_channel(restricted_channel)
            if channel:
                await ctx.send(f"📍 BountyBattle commands can only be used in {channel.mention}!")
                return False
                
        return True

    async def cog_before_invoke(self, ctx):
        """Check restrictions before running any command."""
        if not await self.check_command_available(ctx):
            raise commands.CheckFailure("Command not available in this channel")

    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.guild)
    @commands.admin_or_permissions(administrator=True)  # Allow both owner and admins
    async def bankheist(self, ctx):
        """Start a heist on the global bank! First to type the scrambled word gets the loot!"""
        global_bank = await self.config.guild(ctx.guild).global_bank()
        
        if global_bank < 10000:  # Minimum amount for heist
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ The global bank needs at least `10,000` Berries to be worth robbing!")
        
        # Create scrambled word
        words = [
            "ARCHIPELAGO",
            "REVOLUTIONARY",
            "NAVIGATOR",
            "SHICHIBUKAI",
            "ALABASTA",
            "CELESTIAL",
            "MARINEFORD",
            "FISHMAN",
            "LOGUETOWN",
            "PARAMOUNT",
            "THOUSAND",
            "ENIESLOBBY",
            "IMPELDOWN",
            "BAROQUE",
            "SKYPIEA",
            "WARLORD",
            "YONKO",
            "GRANDLINE",
            "REDLINE",
            "THRILLER",
            "SABAODY",
            "DRESSROSA",
            "KARAKURI",
            "MYSTICAL",
            "TRANSPONDER",
            "VIVRE",
            "PONEGLYPH",
            "MARIEJOIS",
            "PARAMOUNT",
            "EPICUREAN"
        ]
        word = random.choice(words)
        scrambled = ''.join(random.sample(word, len(word)))
        
        embed = discord.Embed(
            title="🏦 BANK HEIST ALERT! 🚨",
            description=(
                f"The global bank containing `{global_bank:,}` Berries is being robbed!\n\n"
                f"**Quick!** Unscramble this word to claim the loot:\n"
                f"```\n{scrambled}\n```"
            ),
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.channel == ctx.channel and m.content.upper() == word
        
        try:
            winner = await ctx.bot.wait_for('message', timeout=30.0, check=check)
            
            # Award the loot
            bounties = load_bounties()
            user_id = str(winner.author.id)
            
            if user_id not in bounties:
                bounties[user_id] = {"amount": 0, "fruit": None}
            
            bounties[user_id]["amount"] += global_bank
            save_bounties(bounties)
            await self.config.member(winner.author).bounty.set(bounties[user_id]["amount"])
            
            # Reset global bank
            await self.config.guild(ctx.guild).global_bank.set(0)
            
            await ctx.send(
                f"🎉 **{winner.author.display_name}** unscrambled the word and stole "
                f"`{global_bank:,}` Berries from the global bank!"
            )
            
        except asyncio.TimeoutError:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("❌ No one unscrambled the word in time! The bank remains secure.")
            
    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
    async def bankrob(self, ctx, target: discord.Member):
        """Attempt to rob another player's bank account!"""
        if ctx.author == target:
            return await ctx.send("❌ You can't rob your own bank account!")
            
        robber = ctx.author
        robber_balance = await self.config.member(robber).bank_balance()
        target_balance = await self.config.member(target).bank_balance()
        
        if target_balance < 10000:
            return await ctx.send(f"❌ **{target.display_name}**'s bank account isn't worth robbing! (Minimum: 10,000 Berries)")
            
        # Create scrambled word challenge
        words = [
            # Iconic Locations
            "LAUGHTALE",
            "WHOLECAKEISLAND",
            "ONIGASHIMA",
            "MARINEFORD",
            "ENIESLOBBY",
            "IMPELDOWN",
            "MARIJOIS",
            "WANOKUNI",
            "SKYPIEA",
            "FISHMANISLAND",
            "SABAODY",
            "DRESSROSA",
            "ALABASTA",
            "LOGUETOWN",
            "BALTIGO",
            "THRILLER BARK",
            "WATERSSEVEN",
            
            # Special Terms
            "TENRYUUBITO",
            "SHICHIBUKAI",
            "PONEGLYPH",
            "VIVRECRAFT",
            "DENDENSMUSHI",
            "HAOUSHOKU",
            "SEASTONE",
            "LUMIMETAL",
            
            # Organizations/Groups
            "REVOLUTIONARIES",
            "STRAWHATCREW",
            "REDHAIRPIRATES",
            "WHITEBEARDS",
            "BIGMOMPIRATES",
            "BEASTPIRATES",
            "BLACKBEARDS",
            "CIPHERPOL",
            "BAROQUE WORKS",
            
            # Important Titles
            "YONKOU",
            "GOROSEI",
            "ADMIRALS",
            "FLEETADMIRAL",
            "PIRATEHUNTER",
            "SOULKING",
            "JINBEITAIYOU",
            
            # Significant Ships
            "THOUSANDSUNNY",
            "GOINGMERRY",
            "MOBYDICK",
            "REDFORCE",
            "QUEENMAMA",
            "VICTORIAPUNK",
            "POLARKING",
            
            # Fighting Styles
            "ROKUSHIKI",
            "FISHMANKARATE",
            "BLACKFOOT",
            "SANTORYU",
            "GEPPOU",
            "TEKKAI",
            "ROKUOGAN",
            
            # Important Events
            "VOIDCENTURY",
            "BUSTERSCALL",
            "GODVALLEY",
            "LEVELY",
            "PARAMOUNT WAR",
            "STAMPEDE",
            
            # Devil Fruit Types
            "GOMUGOMU",
            "BARABARA",
            "MERAMERE",
            "GOROGORO",
            "SUNEKKUMAN",
            "HITOHITO",
            "UOUO",
            
            # Key Concepts
            "AWAKENING",
            "REDPONEGLYPH",
            "ROADPONEGLYPH",
            "ANCIENT WEAPON",
            "WILLOFDEEE",
            "JOYBOY",
            "SUNAGOD NIKA",
            "ZUNISHA"
        ]
        word = random.choice(words)
        scrambled = ''.join(random.sample(word, len(word)))
        
        embed = discord.Embed(
            title="🏦 Bank Robbery Attempt! 🚨",
            description=(
                f"**{robber.display_name}** is attempting to rob **{target.display_name}**'s bank!\n\n"
                f"Quick! Unscramble this word to claim the loot:\n"
                f"```\n{scrambled}\n```"
            ),
            color=discord.Color.red()
        )
        
        message = await ctx.send(embed=embed)
        
        def check(m):
            return m.author == robber and m.channel == ctx.channel and m.content.upper() == word
            
        try:
            await self.bot.wait_for('message', timeout=20.0, check=check)
            
            # Calculate stolen amount (10-30% of target's balance)
            steal_percent = random.uniform(0.10, 0.30)
            steal_amount = int(target_balance * steal_percent)
            
            # Update balances
            await self.config.member(target).bank_balance.set(target_balance - steal_amount)
            await self.config.member(robber).bank_balance.set(robber_balance + steal_amount)
            
            success_embed = discord.Embed(
                title="💰 Bank Robbery Successful!",
                description=(
                    f"**{robber.display_name}** successfully robbed "
                    f"**{target.display_name}**'s bank!\n\n"
                    f"Stolen: `{steal_amount:,}` Berries ({steal_percent*100:.1f}% of their balance)"
                ),
                color=discord.Color.green()
            )
            await message.edit(embed=success_embed)
            
        except asyncio.TimeoutError:
            fail_embed = discord.Embed(
                title="❌ Bank Robbery Failed!",
                description=(
                    f"**{robber.display_name}** failed to crack the bank's security!\n"
                    f"**{target.display_name}**'s Berries are safe!"
                ),
                color=discord.Color.red()
            )
            await message.edit(embed=fail_embed)
    @commands.command(name="cd", aliases=["cooldowns"])
    async def check_cooldowns(self, ctx):
        """Check all your current command cooldowns."""
        user = ctx.author

        # Dictionary of commands and their cooldown times (in seconds)
        COMMAND_COOLDOWNS = {
            "dailybounty": 86400,    # 24 hours
            "bankrob": 3600,       # 1 hour
            "bountyhunt": 600,       # 10 minutes
            "berryflip": 1800,       # 30 minutes
            "diceroll": 1800,        # 30 minutes
            "blackjack": 1800,       # 30 minutes
            "marinehunt": 1800,      # 30 minutes
            "raid": 3600,            # 1 hour
        }

        # Get current time
        current_time = datetime.utcnow()
        active_cooldowns = []

        # Check each command's cooldown
        for command_name, cooldown_time in COMMAND_COOLDOWNS.items():
            command = self.bot.get_command(command_name)
            if command is None:
                continue

            # Get cooldown expiry for this command
            bucket = command._buckets.get_bucket(ctx.message)
            if bucket is None:
                continue

            # Get retry_after
            retry_after = bucket.get_retry_after()
            
            if retry_after:
                # Calculate end time and remaining time
                time_remaining = int(retry_after)
                
                # Format time remaining
                if time_remaining >= 86400:  # 24 hours
                    time_str = f"{time_remaining // 86400}d {(time_remaining % 86400) // 3600}h"
                elif time_remaining >= 3600:  # 1 hour
                    time_str = f"{time_remaining // 3600}h {(time_remaining % 3600) // 60}m"
                elif time_remaining >= 60:    # 1 minute
                    time_str = f"{time_remaining // 60}m {time_remaining % 60}s"
                else:
                    time_str = f"{time_remaining}s"
                
                active_cooldowns.append((command_name, time_str))

        if not active_cooldowns:
            return await ctx.send("🕒 You have no active cooldowns!")

        # Create embed
        embed = discord.Embed(
            title="🕒 Active Cooldowns",
            description=f"Command cooldowns for {user.display_name}:",
            color=discord.Color.blue()
        )

        # Add fields for each category
        bounty_cds = []
        gambling_cds = []
        hunting_cds = []

        for cmd, time in active_cooldowns:
            if cmd in ["dailybounty", "bankrob"]:
                bounty_cds.append(f"`{cmd}`: {time}")
            elif cmd in ["berryflip", "diceroll", "blackjack"]:
                gambling_cds.append(f"`{cmd}`: {time}")
            elif cmd in ["bountyhunt", "marinehunt", "raid"]:
                hunting_cds.append(f"`{cmd}`: {time}")

        if bounty_cds:
            embed.add_field(
                name="💰 Bounty Commands",
                value="\n".join(bounty_cds),
                inline=False
            )

        if gambling_cds:
            embed.add_field(
                name="🎲 Gambling Commands",
                value="\n".join(gambling_cds),
                inline=False
            )

        if hunting_cds:
            embed.add_field(
                name="⚔️ Hunting Commands",
                value="\n".join(hunting_cds),
                inline=False
            )

        # Add info about ready commands
        ready_commands = []
        for cmd in COMMAND_COOLDOWNS.keys():
            if cmd not in [cd[0] for cd in active_cooldowns]:
                ready_commands.append(f"`{cmd}`")

        if ready_commands:
            embed.add_field(
                name="✅ Ready to Use",
                value=" ".join(ready_commands),
                inline=False
            )

        # Add footer with default cooldown times
        embed.set_footer(text="Type .help <command> for more information about specific cooldowns")

        await ctx.send(embed=embed)

    def format_cooldown_time(self, seconds):
        """Format cooldown time into a readable string."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
            
    @commands.command(name="globalbank")
    async def global_bank_status(self, ctx):
        """Check how many berries are stored in the World Government's vault."""
        global_bank = await self.config.guild(ctx.guild).global_bank()
        
        embed = discord.Embed(
            title="🏛️ World Government Treasury",
            description=(
                f"💰 Current Vault Contents:\n"
                f"`{global_bank:,}` Berries\n\n"
                f"*Tax collected from all pirate banking transactions.*"
            ),
            color=discord.Color.blue()
        )
        
        # Add info about bank heist if enough berries
        if global_bank >= 10000:
            embed.add_field(
                name="⚠️ Security Notice",
                value=(
                    "The vault contains enough berries to be targeted by pirates!"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="📜 Notice",
                value=(
                    f"Need `{10000 - global_bank:,}` more berries before the vault "
                    "becomes worth targeting."
                ),
                inline=False
            )
        
        embed.set_footer(text="The World Government collects 7% tax on all bank deposits")
        
        await ctx.send(embed=embed)
        
    @commands.group(name="fruits", invoke_without_command=True)
    async def fruits(self, ctx):
        """
        Display Devil Fruit statistics and information.
        Use subcommands 'rare' or 'common' to view specific fruit lists.
        """
        # Load bounties data
        bounties = load_bounties()
        
        # Count fruits by type
        rare_owned = 0
        common_owned = 0
        total_rare = len(DEVIL_FRUITS["Rare"])
        total_common = len(DEVIL_FRUITS["Common"])
        
        # Track fruit ownership
        for data in bounties.values():
            fruit = data.get("fruit")
            if fruit:
                if fruit in DEVIL_FRUITS["Rare"]:
                    rare_owned += 1
                elif fruit in DEVIL_FRUITS["Common"]:
                    common_owned += 1
        
        embed = discord.Embed(
            title="<:MeraMera:1336888578705330318> Devil Fruit Statistics <:MeraMera:1336888578705330318>",
            color=discord.Color.gold()
        )
        
        # Add general statistics
        embed.add_field(
            name="📊 Overall Statistics",
            value=(
                f"**Total Devil Fruits:** `{total_rare + total_common}`\n"
                f"**Currently Owned:** `{rare_owned + common_owned}`\n"
                f"**Available:** `{(total_rare + total_common) - (rare_owned + common_owned)}`"
            ),
            inline=False
        )
        
        # Add rare fruit statistics
        embed.add_field(
            name="🌟 Rare Fruits",
            value=(
                f"**Total:** `{total_rare}`\n"
                f"**Owned:** `{rare_owned}`\n"
                f"**Available:** `{total_rare - rare_owned}`"
            ),
            inline=True
        )
        
        # Add common fruit statistics
        embed.add_field(
            name="🍎 Common Fruits",
            value=(
                f"**Total:** `{total_common}`\n"
                f"**Owned:** `{common_owned}`\n"
                f"**Available:** `{total_common - common_owned}`"
            ),
            inline=True
        )
        
        # Add command help
        embed.add_field(
            name="💡 Available Commands",
            value=(
                "`.fruits rare` - View rare Devil Fruits\n"
                "`.fruits common` - View common Devil Fruits"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    @fruits.command(name="rare")
    async def fruits_rare(self, ctx):
        """Display all rare Devil Fruit users with detailed information."""
        # Load bounties data
        bounties = load_bounties()
        
        # Get rare fruits data
        rare_fruits = DEVIL_FRUITS["Rare"]
        
        # Track ownership
        owned_fruits = {}
        available_fruits = []
        
        # Check ownership
        for user_id, data in bounties.items():
            fruit = data.get("fruit")
            if fruit in rare_fruits:
                try:
                    member = ctx.guild.get_member(int(user_id))
                    if member:
                        fruit_data = rare_fruits[fruit]
                        owned_fruits[fruit] = {
                            "owner": member.display_name,
                            "type": fruit_data["type"],
                            "bonus": fruit_data["bonus"]
                        }
                except:
                    continue
        
        # Get available fruits
        available_fruits = [fruit for fruit in rare_fruits if fruit not in owned_fruits]
        
        # Create pages - separate owners and available fruits
        owned_embeds = []
        available_embeds = []
        
        # Process owned fruits (3 per page)
        owned_chunks = [list(owned_fruits.items())[i:i + 3] for i in range(0, len(owned_fruits), 3)]
        
        for page, chunk in enumerate(owned_chunks):
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits - Owned",
                description=f"Page {page + 1}/{len(owned_chunks) or 1}",
                color=discord.Color.gold()
            )
            
            for fruit, data in chunk:
                embed.add_field(
                    name=f"{fruit} ({data['type']})",
                    value=(
                        f"👤 Owner: {data['owner']}\n"
                        f"✨ Power: {data['bonus']}"
                    ),
                    inline=False
                )
            
            owned_embeds.append(embed)
        
        # Process available fruits (5 per page)
        available_chunks = [available_fruits[i:i + 5] for i in range(0, len(available_fruits), 5)]
        
        for page, chunk in enumerate(available_chunks):
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits - Available",
                description=f"Page {page + 1}/{len(available_chunks) or 1}",
                color=discord.Color.purple()
            )
            
            for fruit in chunk:
                fruit_data = rare_fruits[fruit]
                embed.add_field(
                    name=f"{fruit} ({fruit_data['type']})",
                    value=f"✨ Power: {fruit_data['bonus']}",
                    inline=False
                )
            
            available_embeds.append(embed)
        
        # Add statistics embed
        stats_embed = discord.Embed(
            title="🌟 Rare Devil Fruits - Statistics",
            color=discord.Color.gold()
        )
        
        stats_embed.add_field(
            name="📊 Statistics",
            value=(
                f"Total Rare Fruits: `{len(rare_fruits)}`\n"
                f"Owned Fruits: `{len(owned_fruits)}`\n"
                f"Available Fruits: `{len(available_fruits)}`"
            ),
            inline=False
        )
        
        # Combine all embeds
        all_embeds = owned_embeds + available_embeds + [stats_embed]
        
        if not all_embeds:
            embed = discord.Embed(
                title="🌟 Rare Devil Fruits",
                description="No rare Devil Fruits found!",
                color=discord.Color.gold()
            )
            return await ctx.send(embed=embed)
        
        # Send first embed
        current_page = 0
        message = await ctx.send(embed=all_embeds[current_page])
        
        # Add navigation reactions if multiple pages
        if len(all_embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(all_embeds)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(all_embeds)
                        
                    await message.edit(embed=all_embeds[current_page])
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break
            
            await message.clear_reactions()

    @fruits.command(name="common")
    async def fruits_common(self, ctx):
        """Display all common Devil Fruit users with detailed information."""
        # Load bounties data
        bounties = load_bounties()
        
        # Get common fruits data
        common_fruits = DEVIL_FRUITS["Common"]
        
        # Track ownership
        owned_fruits = {}
        available_fruits = []
        
        # Check ownership
        for user_id, data in bounties.items():
            fruit = data.get("fruit")
            if fruit in common_fruits:
                try:
                    member = ctx.guild.get_member(int(user_id))
                    if member:
                        fruit_data = common_fruits[fruit]
                        owned_fruits[fruit] = {
                            "owner": member.display_name,
                            "type": fruit_data["type"],
                            "bonus": fruit_data["bonus"]
                        }
                except:
                    continue
        
        # Get available fruits
        available_fruits = [fruit for fruit in common_fruits if fruit not in owned_fruits]
        
        # Create pages - separate owners and available fruits across multiple pages
        owned_embeds = []
        available_embeds = []
        
        # Process owned fruits (5 per page to ensure we don't exceed limits)
        owned_chunks = [list(owned_fruits.items())[i:i + 5] for i in range(0, len(owned_fruits), 5)]
        
        for page, chunk in enumerate(owned_chunks):
            embed = discord.Embed(
                title="🍎 Common Devil Fruits - Owned",
                description=f"Page {page + 1}/{len(owned_chunks)}",
                color=discord.Color.blue()
            )
            
            for fruit, data in chunk:
                embed.add_field(
                    name=f"{fruit} ({data['type']})",
                    value=(
                        f"👤 Owner: {data['owner']}\n"
                        f"✨ Power: {data['bonus']}"
                    ),
                    inline=False
                )
            
            owned_embeds.append(embed)
        
        # Process available fruits (10 per page - they're shorter)
        available_chunks = [available_fruits[i:i + 10] for i in range(0, len(available_fruits), 10)]
        
        for page, chunk in enumerate(available_chunks):
            embed = discord.Embed(
                title="🍎 Common Devil Fruits - Available",
                description=f"Page {page + 1}/{len(available_chunks)}",
                color=discord.Color.green()
            )
            
            for fruit in chunk:
                fruit_data = common_fruits[fruit]
                embed.add_field(
                    name=f"{fruit} ({fruit_data['type']})",
                    value=f"✨ Power: {fruit_data['bonus']}",
                    inline=False
                )
            
            available_embeds.append(embed)
        
        # Add statistics embed
        stats_embed = discord.Embed(
            title="🍎 Common Devil Fruits - Statistics",
            color=discord.Color.gold()
        )
        
        stats_embed.add_field(
            name="📊 Statistics",
            value=(
                f"Total Common Fruits: `{len(common_fruits)}`\n"
                f"Owned Fruits: `{len(owned_fruits)}`\n"
                f"Available Fruits: `{len(available_fruits)}`"
            ),
            inline=False
        )
        
        # Combine all embeds
        all_embeds = owned_embeds + available_embeds + [stats_embed]
        
        if not all_embeds:
            embed = discord.Embed(
                title="🍎 Common Devil Fruits",
                description="No Devil Fruits found!",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        # Send first embed
        current_page = 0
        message = await ctx.send(embed=all_embeds[current_page])
        
        # Add navigation reactions if multiple pages
        if len(all_embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(all_embeds)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(all_embeds)
                        
                    await message.edit(embed=all_embeds[current_page])
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break
            
            await message.clear_reactions()
                
    @commands.command()
    @commands.admin_or_permissions(administrator=True)  # Allow both owner and admins
    async def betaover(self, ctx):
        """End the beta test (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")

        beta_active = await self.config.guild(ctx.guild).beta_active()
        
        if not beta_active:
            return await ctx.send("❌ Beta is already over!")
        
        await self.config.guild(ctx.guild).beta_active.set(False)
        await ctx.send("🚨 **The beta test is now officially over!**\nNo new players will receive the `BETA TESTER` title.")
        
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def fruitcleanup(self, ctx, days: int = 30):
        """Clean up Devil Fruits from inactive players and users who left the server (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
                
        try:
            current_time = datetime.utcnow()
            bounties = load_bounties()
            cleaned_fruits = []
            left_server_fruits = []
            
            # Step 1: Process inactive users in the server
            for user_id, data in list(bounties.items()):
                # Skip if no fruit
                if not data.get("fruit"):
                    continue

                try:
                    # Check if user is still in server
                    member = ctx.guild.get_member(int(user_id))
                    if not member:
                        # User left server, clean up their fruit
                        fruit_name = data["fruit"]
                        bounties[user_id]["fruit"] = None
                        left_server_fruits.append((user_id, fruit_name))
                        continue
                        
                    # User is in server, check if inactive
                    last_active = await self.config.member(member).last_active()
                    if not last_active:
                        continue

                    last_active_date = datetime.fromisoformat(last_active)
                    days_since_active = (current_time - last_active_date).days

                    # Remove fruit if inactive for specified period
                    if days_since_active >= days:
                        fruit_name = data["fruit"]
                        bounties[user_id]["fruit"] = None
                        await self.config.member(member).devil_fruit.set(None)
                        cleaned_fruits.append((member.display_name, fruit_name))

                except (ValueError, AttributeError) as e:
                    self.log.error(f"Error processing user {user_id}: {e}")
                    continue

            # Save changes
            save_bounties(bounties)

            # Create report embed
            embed = discord.Embed(
                title="<:MeraMera:1336888578705330318> Devil Fruit Cleanup Report",
                description="Results of the cleanup operation:",
                color=discord.Color.blue()
            )
            
            # Add section for inactive users
            if cleaned_fruits:
                embed.add_field(
                    name=f"🕒 Removed from {len(cleaned_fruits)} inactive players",
                    value="\n".join([f"**{name}**: `{fruit}`" for name, fruit in cleaned_fruits[:10]]) + 
                        (f"\n*...and {len(cleaned_fruits) - 10} more*" if len(cleaned_fruits) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🕒 Inactive Players",
                    value="No inactive Devil Fruit users found!",
                    inline=False
                )
                
            # Add section for users who left the server
            if left_server_fruits:
                embed.add_field(
                    name=f"👋 Removed from {len(left_server_fruits)} users who left the server",
                    value="\n".join([f"**ID {user_id}**: `{fruit}`" for user_id, fruit in left_server_fruits[:10]]) +
                        (f"\n*...and {len(left_server_fruits) - 10} more*" if len(left_server_fruits) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="👋 Left Server Users",
                    value="No Devil Fruit users have left the server!",
                    inline=False
                )
                
            # Add summary
            total_cleaned = len(cleaned_fruits) + len(left_server_fruits)
            if total_cleaned > 0:
                embed.add_field(
                    name="📊 Summary",
                    value=f"**{total_cleaned}** Devil Fruits have been returned to circulation!",
                    inline=False
                )
                
                # Check for rare fruits that were reclaimed
                rare_fruits = [fruit for _, fruit in cleaned_fruits + left_server_fruits 
                            if fruit in DEVIL_FRUITS.get("Rare", {})]
                if rare_fruits:
                    embed.add_field(
                        name="🌟 Rare Fruits Reclaimed",
                        value="\n".join([f"`{fruit}`" for fruit in rare_fruits]),
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
            # Send announcements for rare fruits
            for _, fruit in cleaned_fruits + left_server_fruits:
                if fruit in DEVIL_FRUITS.get("Rare", {}):
                    announcement_embed = discord.Embed(
                        title="🌟 Rare Devil Fruit Available!",
                        description=(
                            f"The `{fruit}` has returned to circulation!\n"
                            f"Previous owner is no longer using it."
                        ),
                        color=discord.Color.gold()
                    )
                    
                    # Try to send to a designated channel if it exists
                    announcement_channel = discord.utils.get(ctx.guild.text_channels, name="fruit-announcements") or \
                                        discord.utils.get(ctx.guild.text_channels, name="announcements") or \
                                        discord.utils.get(ctx.guild.text_channels, name="general")
                    
                    if announcement_channel and announcement_channel != ctx.channel:
                        await announcement_channel.send(embed=announcement_embed)

        except Exception as e:
            self.log.error(f"Error in cleanup_inactive_fruits: {e}")
            await ctx.send("❌ An error occurred during fruit cleanup.")
    
    @commands.command()
    async def mostwanted(self, ctx):
        """Display the top users with the highest bounties."""
        # Load current bounty data from bounties.json
        bounties = load_bounties()
        
        if not bounties:
            return await ctx.send("🏴‍☠️ No bounties have been claimed yet! Be the first to start your journey with `.startbounty`.")

        # Filter out inactive or invalid entries and sort by amount
        valid_bounties = []
        for user_id, data in bounties.items():
            try:
                member = ctx.guild.get_member(int(user_id))
                if member and data.get("amount", 0) > 0:
                    valid_bounties.append((user_id, data))
            except (ValueError, AttributeError):
                continue

        if not valid_bounties:
            return await ctx.send("🏴‍☠️ No active bounties found! Start your journey with `.startbounty`.")

        sorted_bounties = sorted(valid_bounties, key=lambda x: x[1]["amount"], reverse=True)
        pages = [sorted_bounties[i:i + 10] for i in range(0, len(sorted_bounties), 10)]
        
        current_page = 0
        
        async def create_leaderboard_embed(page_data, page_num):
            embed = discord.Embed(
                title="🏆 Most Wanted Pirates 🏆",
                description="The most notorious pirates of the sea!",
                color=discord.Color.gold()
            )
            
            total_pages = len(pages)
            embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total Pirates: {len(sorted_bounties)}")
            
            for i, (user_id, data) in enumerate(page_data, start=1 + (page_num * 10)):
                member = ctx.guild.get_member(int(user_id))
                if not member:
                    continue
                
                # Get user's devil fruit if they have one
                devil_fruit = data.get("fruit", "None")
                fruit_display = f" • <:MeraMera:1336888578705330318> {devil_fruit}" if devil_fruit and devil_fruit != "None" else ""
                
                # Create rank emoji based on position
                rank_emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                # Format the bounty amount with commas
                bounty_amount = "{:,}".format(data["amount"])
                
                embed.add_field(
                    name=f"{rank_emoji} {member.display_name}",
                    value=f"<:Beli:1237118142774247425> `{bounty_amount} Berries`{fruit_display}",
                    inline=False
                )
            
            return embed

        # Send initial embed
        embed = await create_leaderboard_embed(pages[current_page], current_page)
        message = await ctx.send(embed=embed)

        # Add reactions for navigation
        if len(pages) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return (
                    user == ctx.author 
                    and str(reaction.emoji) in ["⬅️", "➡️"] 
                    and reaction.message.id == message.id
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        timeout=60.0,
                        check=check
                    )

                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(pages)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(pages)

                    embed = await create_leaderboard_embed(pages[current_page], current_page)
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break

            await message.clear_reactions()

    async def create_leaderboard_embed(self, bounties):
        embed = discord.Embed(title="🏆 Bounty Leaderboard 🏆", color=discord.Color.gold())
        for i, (user_id, bounty) in enumerate(bounties, start=1):
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            if user is None:
                continue  # Skip if user doesn't exist

            embed.add_field(name=f"{i}. {user.display_name}", 
                            value=f"{bounty['amount']:,} Berries", inline=False)
        return embed

    @commands.command()
    @commands.admin_or_permissions(administrator=True)  # Admin-only command
    async def bountydecay(self, ctx):
        """Reduce inactive players' bounties over time."""
        bounties = await self.config.guild(ctx.guild).bounties()
        decay_rate = 0.05  # 5% per day after 3 days of inactivity
        decay_threshold = 3  # Days before decay starts
    
        updated_bounties = []
        now = datetime.utcnow()
    
        for user_id, data in bounties.items():
            # ✅ Define `member` properly
            member = ctx.guild.get_member(int(user_id))
            if not member:
                continue  # Skip if user is no longer in the server
    
            # ✅ Now `member` is defined before being used
            last_active = await self.config.member(member).last_active()
            if last_active:
                last_active = datetime.fromisoformat(last_active)
                days_inactive = (now - last_active).days
    
                if days_inactive >= decay_threshold:
                    decay_amount = int(data["amount"] * (decay_rate * (days_inactive - decay_threshold)))
                    new_bounty = max(0, data["amount"] - decay_amount)
                    await self.config.member(member).bounty.set(new_bounty)
                    updated_bounties.append(f"⚠️ **{member.display_name}** lost `{decay_amount:,} Berries` due to inactivity!")
    
        if updated_bounties:
            await ctx.send("\n".join(updated_bounties))
        else:
            await ctx.send("✅ No bounties were decayed. Everyone is active!")

    @commands.command()
    async def eatfruit(self, ctx):
        """Consume a random Devil Fruit!"""
        user = ctx.author
        bounties = load_bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        if bounties[user_id].get("fruit"):
            return await ctx.send(f"❌ You already have the `{bounties[user_id]['fruit']}`! You can only eat one Devil Fruit!")

        # Get all currently taken rare fruits
        taken_rare_fruits = {
            data.get("fruit") for data in bounties.values() 
            if data.get("fruit") in DEVIL_FRUITS["Rare"]
        }

        # Get available rare and common fruits
        available_rare_fruits = [
            fruit for fruit in DEVIL_FRUITS["Rare"].keys() 
            if fruit not in taken_rare_fruits
        ]

        available_common_fruits = list(DEVIL_FRUITS["Common"].keys())

        if not available_rare_fruits and not available_common_fruits:
            return await ctx.send("❌ There are no Devil Fruits available right now! Try again later.")

        # 10% chance for rare fruit if available
        if available_rare_fruits and random.random() < 0.10:
            new_fruit = random.choice(available_rare_fruits)
            fruit_data = DEVIL_FRUITS["Rare"][new_fruit]
            is_rare = True
        else:
            new_fruit = random.choice(available_common_fruits)
            fruit_data = DEVIL_FRUITS["Common"][new_fruit]
            is_rare = False

        # Save the fruit to the user
        bounties[user_id]["fruit"] = new_fruit
        save_bounties(bounties)
        await self.config.member(user).devil_fruit.set(new_fruit)
        await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

        # Create announcement
        if is_rare:
            announcement = (
                f"🚨 **Breaking News from the Grand Line!** 🚨\n"
                f"🏴‍☠️ **{user.display_name}** has discovered and consumed the **{new_fruit}**!\n"
                f"Type: {fruit_data['type']}\n"
                f"🔥 Power: {fruit_data['bonus']}\n\n"
                f"⚠️ *This Devil Fruit is now **UNIQUE**! No one else can eat it!*"
            )
            await ctx.send(announcement)
        else:
            await ctx.send(
                f"<:MeraMera:1336888578705330318> **{user.display_name}** has eaten the **{new_fruit}**!\n"
                f"Type: {fruit_data['type']}\n"
                f"🔥 Power: {fruit_data['bonus']}\n\n"
                f"⚠️ *You cannot eat another Devil Fruit!*"
            )

    @commands.group(name="achievementmanager", aliases=["am"])
    @commands.admin_or_permissions(administrator=True)
    async def achievement_manager(self, ctx):
        """Manage custom achievements (Admin only)"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @achievement_manager.command(name="add")
    async def add_achievement(self, ctx, key: str, condition: str, count: int, *, description: str):
        """Add a new achievement
        
        Parameters:
        - key: Unique identifier for the achievement
        - condition: What triggers the achievement (e.g., 'wins', 'total_damage_dealt')
        - count: Number required to complete
        - description: Achievement description
        """
        if key in ACHIEVEMENTS:
            return await ctx.send("❌ This achievement key already exists!")
            
        title = f"Achievement Master: {key.title()}"
        
        ACHIEVEMENTS[key] = {
            "description": description,
            "condition": condition,
            "count": count,
            "title": title
        }
        
        embed = discord.Embed(
            title="✅ New Achievement Added",
            color=discord.Color.green()
        )
        embed.add_field(name="Key", value=key, inline=True)
        embed.add_field(name="Condition", value=f"{condition} >= {count}", inline=True)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Title Reward", value=title, inline=False)
        
        await ctx.send(embed=embed)

    @achievement_manager.command(name="remove")
    async def remove_achievement(self, ctx, key: str):
        """Remove a custom achievement"""
        if key not in ACHIEVEMENTS:
            return await ctx.send("❌ Achievement not found!")
            
        if key in [
            "first_blood",        # First win
            "big_hitter",        # Big damage
            "burn_master",       # Burn effects
            "comeback_king",     # Low HP comeback
            "perfect_game",      # No damage win
            "stunning_performance", # Stun effects
            "overkill",          # Massive damage
            "healing_touch",     # Healing
            "unstoppable",       # Win streak
            "sea_emperor",       # Win milestone
            "legendary_warrior", # Win milestone
            "iron_wall",        # Blocking
            "damage_master",    # Total damage
            "burning_legacy",   # Total burns
            "guardian_angel",   # Damage prevented
            "swift_finisher",   # Quick victory
            "relentless",      # Critical hits
            "elemental_master", # Element variety
            "unstoppable_force", # Win streak
            "immortal",         # 1 HP survival
            "devastator",       # High damage
            "pyromaniac",       # Fire mastery
            "titan"            # Long battle
        ]: 
            return await ctx.send("❌ Cannot remove default achievements!")
            
        achievement_data = ACHIEVEMENTS.pop(key)
        
        embed = discord.Embed(
            title="🗑️ Achievement Removed",
            description=f"Achievement `{key}` has been removed.",
            color=discord.Color.red()
        )
        embed.add_field(name="Description", value=achievement_data["description"], inline=False)
        
        await ctx.send(embed=embed)

    @achievement_manager.command(name="list")
    async def list_achievements(self, ctx):
        """List all achievements"""
        embed = discord.Embed(
            title="📜 Achievement List",
            color=discord.Color.blue()
        )
        
        # Separate default and custom achievements
        default_achievements = []
        custom_achievements = []
        
        for key, data in ACHIEVEMENTS.items():
            achievement_text = f"**{key}**\n{data['description']}\nCondition: {data['condition']} >= {data['count']}"
            if key in ["first_blood", "big_hitter", "burn_master"]:  # Default achievements
                default_achievements.append(achievement_text)
            else:
                custom_achievements.append(achievement_text)
        
        # Split default achievements into chunks if needed
        if default_achievements:
            chunks = []
            current_chunk = []
            current_length = 0
            
            for achievement in default_achievements:
                if current_length + len(achievement) + 2 > 1024:  # +2 for newlines
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [achievement]
                    current_length = len(achievement)
                else:
                    current_chunk.append(achievement)
                    current_length += len(achievement) + 2
            
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
            for i, chunk in enumerate(chunks):
                field_name = "Default Achievements" if i == 0 else "Default Achievements (Continued)"
                embed.add_field(name=field_name, value=chunk, inline=False)
        
        # Split custom achievements into chunks if needed
        if custom_achievements:
            chunks = []
            current_chunk = []
            current_length = 0
            
            for achievement in custom_achievements:
                if current_length + len(achievement) + 2 > 1024:  # +2 for newlines
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = [achievement]
                    current_length = len(achievement)
                else:
                    current_chunk.append(achievement)
                    current_length += len(achievement) + 2
            
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
            for i, chunk in enumerate(chunks):
                field_name = "Custom Achievements" if i == 0 else "Custom Achievements (Continued)"
                embed.add_field(name=field_name, value=chunk, inline=False)
        
        if not (default_achievements or custom_achievements):
            embed.description = "No achievements found."
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners and Admins remove for free, others pay 1,000,000 berries from their bounty."""
        user = ctx.author
        member = member or user  # Defaults to the user running the command
        
        # Check if user is bot owner or has admin permissions
        is_owner = await self.bot.is_owner(user)
        is_admin = ctx.author.guild_permissions.administrator

        # Add permissions message for removing other people's fruits
        if member != user and not (is_owner or is_admin):
            return await ctx.send("❌ You can only remove your own Devil Fruit unless you're an admin!")

        # Load both data sources
        bounties = load_bounties()
        user_id = str(member.id)
        
        # Check if user exists in bounties
        if user_id not in bounties:
            return await ctx.send(f"🍏 **{member.display_name}** has no bounty data!")
            
        # Check if user has a fruit
        if not bounties[user_id].get("fruit"):
            return await ctx.send(f"🍏 **{member.display_name}** has no Devil Fruit to remove!")

        current_fruit = bounties[user_id]["fruit"]

        # Owners and Admins remove the fruit for free
        if is_owner or is_admin:
            # Clear from bounties
            bounties[user_id]["fruit"] = None
            save_bounties(bounties)
            
            # Clear from config
            await self.config.member(member).devil_fruit.set(None)
            
            return await ctx.send(f"🛡️ **{user.display_name}** removed `{current_fruit}` from **{member.display_name}** for free!")

        # Normal users must pay from their bounty
        cost = 1_000_000
        current_bounty = bounties[user_id]["amount"]

        if current_bounty < cost:
            return await ctx.send(f"❌ You need a bounty of at least **{cost:,}** berries to remove your Devil Fruit.")

        # Deduct cost and remove fruit
        bounties[user_id]["amount"] = current_bounty - cost
        bounties[user_id]["fruit"] = None
        save_bounties(bounties)
        
        # Update config
        await self.config.member(member).devil_fruit.set(None)
        await self.config.member(member).bounty.set(bounties[user_id]["amount"])

        await ctx.send(
            f"<:Beli:1237118142774247425> **{user.display_name}** paid **{cost:,}** berries from their bounty to remove `{current_fruit}`!\n"
            f"That fruit can now be found again! 🍏"
        )

        
    @commands.command()
    @commands.admin_or_permissions(administrator=True)  # Allow both admins and owner
    async def setbounty(self, ctx, member: discord.Member, amount: int):
        """Set a user's bounty (Admin/Owner only)."""
        if amount < 0:
            return await ctx.send("❌ Bounty cannot be negative.")
        
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        try:
            bounties = load_bounties()
            user_id = str(member.id)

            if user_id not in bounties:
                bounties[user_id] = {
                    "amount": 0,
                    "fruit": None
                }

            bounties[user_id]["amount"] = amount
            
            try:
                save_bounties(bounties)
                await self.config.member(member).bounty.set(amount)
            except Exception as e:
                logger.error(f"Failed to save bounty data in setbounty: {e}")
                await ctx.send("⚠️ Failed to set bounty. Please try again.")
                return

            # Create embed for response
            embed = discord.Embed(
                title="🏴‍☠️ Bounty Updated",
                description=f"**{member.display_name}**'s bounty has been set to `{amount:,}` Berries!",
                color=discord.Color.green()
            )

            # Add current title if applicable
            new_title = self.get_bounty_title(amount)
            if new_title:
                embed.add_field(
                    name="Current Title",
                    value=f"`{new_title}`",
                    inline=False
                )

            await ctx.send(embed=embed)

            # Check if the new bounty warrants an announcement
            if amount >= 900_000_000:
                await self.announce_rank(ctx.guild, member, new_title)

        except Exception as e:
            logger.error(f"Error in setbounty command: {str(e)}")
            await ctx.send(f"❌ An error occurred while setting the bounty: {str(e)}")
            
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def givefruit(self, ctx, member: discord.Member, *, fruit_name: str):
        """Give a user a Devil Fruit (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")

        # Validate the fruit transfer
        if not await self.validate_fruit_transfer(ctx, member, fruit_name):
            return

        # Assign fruit
        bounties = load_bounties()
        user_id = str(member.id)
        
        if user_id not in bounties:
            bounties[user_id] = {"amount": 0, "fruit": fruit_name}
        else:
            bounties[user_id]["fruit"] = fruit_name
            
        save_bounties(bounties)
        await self.config.member(member).devil_fruit.set(fruit_name)
        await self.config.member(member).last_active.set(datetime.utcnow().isoformat())

        # Get fruit data
        fruit_data = DEVIL_FRUITS["Rare"].get(fruit_name) or DEVIL_FRUITS["Common"].get(fruit_name)
        
        # Create success embed
        embed = discord.Embed(
            title="<:MeraMera:1336888578705330318> Devil Fruit Given!",
            description=f"**{member.display_name}** has been given the `{fruit_name}`!",
            color=discord.Color.green()
        )
        embed.add_field(name="Type", value=fruit_data["type"], inline=True)
        embed.add_field(name="Power", value=fruit_data["bonus"], inline=False)

        await ctx.send(embed=embed)
        
    @commands.command()
    async def myfruit(self, ctx):
        """Check which Devil Fruit you have eaten."""
        user = ctx.author
        fruit = await self.config.member(user).devil_fruit()
    
        if not fruit:
            return await ctx.send("❌ You have not eaten a Devil Fruit!")
    
        # ✅ Search for the fruit in both Common and Rare categories
        fruit_data = DEVIL_FRUITS["Common"].get(fruit) or DEVIL_FRUITS["Rare"].get(fruit)
    
        if not fruit_data:
            return await ctx.send("⚠️ **Error:** Your Devil Fruit could not be found in the database. Please report this!")
    
        fruit_type = fruit_data["type"]
        effect = fruit_data["bonus"]
    
        await ctx.send(
            f"<:MeraMera:1336888578705330318> **{user.display_name}** has the **{fruit}**! ({fruit_type} Type)\n"
            f"🔥 **Ability:** {effect}"
        )

    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def bountyhunt(self, ctx, target: discord.Member):
        """Attempt to steal a percentage of another user's bounty with a lock-picking minigame."""
        try:
            hunter = ctx.author
            
            # Initial validation checks
            if hunter == target:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Ye can't hunt yer own bounty, ye scallywag!")
            
            if target.bot:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Ye can't steal from bots, they're too secure!")

            # Sync data for both hunter and target
            hunter_bounty = await self.sync_user_data(hunter)
            target_bounty = await self.sync_user_data(target)
            
            if hunter_bounty is None or target_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking bounties.")

            # Check minimum bounty requirements
            min_bounty = 1000
            if target_bounty < min_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"<:Beli:1237118142774247425> **{target.display_name}** is too broke to be worth hunting! (Minimum: {min_bounty:,} Berries)")

            # Generate lock-picking challenge
            patterns = {
                "Easy": ["🔒🔑", "🔑🔒"],
                "Medium": ["🔒🔑🔑", "🔑🔒🔑", "🔑🔑🔒"],
                "Hard": ["🔒🔑🔑🔒", "🔑🔒🔒🔑", "🔑🔑🔒🔒"]
            }
            
            # Difficulty scales with target's bounty
            if target_bounty > 1_000_000:
                difficulty = "Hard"
                time_limit = 8
            elif target_bounty > 100_000:
                difficulty = "Medium"
                time_limit = 10
            else:
                difficulty = "Easy"
                time_limit = 12

            lock_code = random.choice(patterns[difficulty])

            # Create challenge embed
            challenge_embed = discord.Embed(
                title="🏴‍☠️ Bounty Hunt Attempt!",
                description=(
                    f"**{hunter.display_name}** is attempting to break into **{target.display_name}**'s safe! 🔐\n\n"
                    f"**Difficulty:** {difficulty}\n"
                    f"**Time Limit:** {time_limit} seconds\n"
                    f"**Pattern to Match:** `{lock_code}`"
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=challenge_embed)

            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == hunter and m.channel == ctx.channel,
                    timeout=time_limit
                )
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⌛ Time's Up!",
                    description=f"**{hunter.display_name}** took too long! {target.display_name} was alerted!",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=timeout_embed)

            # Load bounties for updating
            bounties = load_bounties()
            hunter_id = str(hunter.id)
            target_id = str(target.id)

            if msg.content.strip() != lock_code:
                fail_embed = discord.Embed(
                    title="❌ Lock Pick Failed!",
                    description=f"**{hunter.display_name}** failed to pick the lock! {target.display_name} was alerted!",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=fail_embed)

            # Calculate success chance and critical failure
            success = random.random() < 0.6  # 60% base success rate
            critical_failure = random.random() < 0.05  # 5% critical failure chance

            if success and not critical_failure:
                # Calculate steal amount with minimum guarantee
                base_steal = random.uniform(0.05, 0.20)
                steal_amount = max(int(base_steal * target_bounty), 500)
                
                try:
                    bounties[hunter_id]["amount"] += steal_amount
                    bounties[target_id]["amount"] = max(0, target_bounty - steal_amount)
                    save_bounties(bounties)

                    # Update both users in config
                    await self.config.member(hunter).bounty.set(bounties[hunter_id]["amount"])
                    await self.config.member(target).bounty.set(bounties[target_id]["amount"])
                    
                    # Update activity timestamps
                    current_time = datetime.utcnow().isoformat()
                    await self.config.member(hunter).last_active.set(current_time)
                    await self.config.member(target).last_active.set(current_time)

                except Exception as e:
                    logger.error(f"Failed to save bounty data in bountyhunt: {e}")
                    await ctx.send("⚠️ Failed to process bounty hunt rewards. Please try again.")
                    return

                # Create success embed
                success_embed = discord.Embed(
                    title="🏴‍☠️ Bounty Hunt Success!",
                    description=f"<:Beli:1237118142774247425> **{hunter.display_name}** successfully infiltrated **{target.display_name}**'s vault!",
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="💎 Stolen Amount",
                    value=f"`{steal_amount:,}` Berries",
                    inline=False
                )
                success_embed.add_field(
                    name="🏆 New Hunter Bounty",
                    value=f"`{bounties[hunter_id]['amount']:,}` Berries",
                    inline=True
                )
                success_embed.add_field(
                    name="💀 New Target Bounty",
                    value=f"`{bounties[target_id]['amount']:,}` Berries",
                    inline=True
                )
                await ctx.send(embed=success_embed)

            elif critical_failure:
                # Handle critical failure
                penalty = max(int(hunter_bounty * 0.10), 1000)
                bounties[hunter_id]["amount"] = max(0, hunter_bounty - penalty)
                save_bounties(bounties)
                await self.config.member(hunter).bounty.set(bounties[hunter_id]["amount"])

                failure_embed = discord.Embed(
                    title="💥 Critical Failure!",
                    description=(
                        f"**{hunter.display_name}** got caught in a trap while trying to rob "
                        f"**{target.display_name}**!\n\n"
                        f"*The Marines were alerted and imposed a fine!*"
                    ),
                    color=discord.Color.red()
                )
                failure_embed.add_field(
                    name="💸 Fine Amount",
                    value=f"`{penalty:,}` Berries",
                    inline=False
                )
                failure_embed.add_field(
                    name="🏴‍☠️ Remaining Bounty",
                    value=f"`{bounties[hunter_id]['amount']:,}` Berries",
                    inline=True
                )
                await ctx.send(embed=failure_embed)

            else:
                # Handle normal failure
                await ctx.send(f"💀 **{hunter.display_name}** failed to steal from **{target.display_name}**!")

        except Exception as e:
            logger.error(f"Error in bountyhunt command: {str(e)}")
            await ctx.send("❌ An error occurred during the bounty hunt!")
            self.bot.dispatch("command_error", ctx, e)
            
    @commands.command()
    async def syncbounties(self, ctx):
        """Synchronize all bounties in the system."""
        try:
            # Load bounties from both sources
            bounties = load_bounties()
            guild_bounties = await self.config.guild(ctx.guild).bounties()

            # Synchronize bounties for each user in the guild
            for user_id, guild_bounty_data in guild_bounties.items():
                try:
                    # Get member object
                    member = ctx.guild.get_member(int(user_id))
                    if not member:
                        continue

                    # Get bounty from both sources
                    config_bounty = await self.config.member(member).bounty()
                    json_bounty = bounties.get(user_id, {}).get("amount", 0)

                    # Use the higher bounty as the source of truth
                    true_bounty = max(config_bounty, json_bounty)

                    # Update both systems
                    bounties[user_id] = bounties.get(user_id, {})
                    bounties[user_id]["amount"] = true_bounty
                    
                    # Save to JSON
                    save_bounties(bounties)
                    
                    # Update config
                    await self.config.member(member).bounty.set(true_bounty)

                except Exception as user_sync_error:
                    logger.error(f"Error syncing bounty for user {user_id}: {user_sync_error}")
                    continue

            await ctx.send("✅ Successfully synchronized all bounties!")
        except Exception as e:
            logger.error(f"Error in syncbounties: {str(e)}")
            await ctx.send(f"❌ An error occurred while synchronizing bounties: {str(e)}")

    @commands.command()
    async def mybounty(self, ctx):
        """Check your bounty amount."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking your bounty.")
            
        # Get current title based on synced bounty
        current_title = self.get_bounty_title(true_bounty)
        
        embed = discord.Embed(
            title="🏴‍☠️ Bounty Status",
            description=f"**{user.display_name}**'s current bounty:",
            color=discord.Color.gold()
        )
        embed.add_field(name="<:Beli:1237118142774247425> Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="🎭 Title", value=f"`{current_title}`", inline=False)
        
        await ctx.send(embed=embed)

    
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase."""
        user = ctx.author
        
        # Sync bounty data first, allowing zero bounty
        current_bounty = await self.config.member(user).bounty()
        
        # Check last claim time
        last_claim = await self.config.member(user).last_daily_claim()
        now = datetime.utcnow()

        if last_claim:
            last_claim = datetime.fromisoformat(last_claim)
            time_left = timedelta(days=1) - (now - last_claim)
            
            if time_left.total_seconds() > 0:
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Try again in {hours} hours and {minutes} minutes! ⏳")

        # Prompt for treasure chest
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.config.member(user).last_daily_claim.set(None)
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            increase = random.randint(1000, 5000)
            
            # Ensure user has a bounty record, creating one if not
            bounties = load_bounties()
            user_id = str(user.id)
            
            if user_id not in bounties:
                bounties[user_id] = {"amount": 0, "fruit": None}
            
            # Update bounty
            bounties[user_id]["amount"] += increase
            save_bounties(bounties)
            
            # Update config
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            
            await ctx.send(f"<:Beli:1237118142774247425> Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                        f"Current Title: {new_title}")

            # Announce if the user reaches a significant rank
            if new_bounty >= 900000000:
                await self.announce_rank(ctx.guild, user, new_title)
        else:
            await self.config.member(user).last_daily_claim.set(None)
            await ctx.send("Ye decided not to open the chest. The Sea Kings must've scared ye off!")
            
    @commands.command()
    async def wanted(self, ctx, member: discord.Member = None):
        """Display a wanted poster with the user's avatar, username, and bounty."""
        if member is None:
            member = ctx.author
            
        # Sync data first
        true_bounty = await self.sync_user_data(member)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while creating wanted poster.")

        if true_bounty == 0:
            return await ctx.send(f"{member.display_name} needs to start their bounty journey first by typing `.startbounty`!")

        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status != 200:
                    return await ctx.send("Failed to retrieve avatar.")
                avatar_data = await response.read()

        wanted_poster = await self.create_wanted_poster(member.display_name, true_bounty, avatar_data)
        if isinstance(wanted_poster, str):
            return await ctx.send(wanted_poster)
        await ctx.send(file=discord.File(wanted_poster, "wanted.png"))

    async def create_wanted_poster(self, username, bounty_amount, avatar_data):
        """Create a wanted poster with the user's avatar, username, and bounty."""
        
        # Define dynamic paths (works across different setups)
        base_path = os.path.join("/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/")
        wanted_poster_path = os.path.join(base_path, "wanted.png")
        font_path = os.path.join(base_path, "onepiece.ttf")
    
        # Ensure the template and font exist
        if not os.path.exists(wanted_poster_path):
            return "⚠️ Wanted poster template not found! Ensure `wanted.png` exists in the bountybattle folder."
        if not os.path.exists(font_path):
            return "⚠️ Font file not found! Ensure `onepiece.ttf` exists in the bountybattle folder."
    
        # Load images
        poster_image = Image.open(wanted_poster_path)
        avatar_image = Image.open(io.BytesIO(avatar_data)).resize((625, 455)).convert("RGBA")
    
        # Paste avatar onto the poster
        poster_image.paste(avatar_image, (65, 223), avatar_image)
    
        # Draw text (name & bounty)
        draw = ImageDraw.Draw(poster_image)
        try:
            # Dynamically adjust font size based on name length
            font_size = 100 if len(username) <= 12 else 80
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            return "⚠️ Font loading error! Ensure `onepiece.ttf` is a valid TrueType font."
    
        draw.text((150, 750), username, font=font, fill="black")
        draw.text((150, 870), f"{bounty_amount:,} Berries", font=font, fill="black")
    
        # Save to a BytesIO object
        output = io.BytesIO()
        poster_image.save(output, format="PNG")
        output.seek(0)
    
        return output
    
    async def announce_rank(self, guild, user, title):
        """Announce when a user reaches a significant rank."""
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎉 Congratulations to {user.mention} for reaching the rank of **{title}** with a bounty of {user.display_name}'s bounty!")

    def get_bounty_title(self, bounty_amount):
        """Get the bounty title based on the bounty amount.
        Returns the highest title the user has qualified for."""
        if bounty_amount is None or bounty_amount <= 0:
            return "Unknown Pirate"
            
        # Define titles and their required bounties
        titles_qualified = []
        
        for title, requirements in TITLES.items():
            required_bounty = requirements["bounty"]
            if bounty_amount >= required_bounty:
                titles_qualified.append((title, required_bounty))
        
        # If no titles are qualified
        if not titles_qualified:
            return "Unknown Pirate"
            
        # Sort by required bounty (descending) and return the highest one
        titles_qualified.sort(key=lambda x: x[1], reverse=True)
        return titles_qualified[0][0]

    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def getdata(self, ctx):
        """Retrieve the current guild's bounty data (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        guild = ctx.guild
        all_members = await self.config.all_members(guild)

        if not all_members:
            return await ctx.send("❌ No bounty data found for this guild.")

        # Define the file path
        base_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle"
        file_path = os.path.join(base_path, "bounties.json")

        # Ensure the directory exists
        os.makedirs(base_path, exist_ok=True)

        # Structure the data
        bounties_data = {}

        rare_fruit_owners = set()  # Track users who own rare fruits

        for user_id, data in all_members.items():
            bounty_amount = data.get("bounty", 0)
            devil_fruit = data.get("devil_fruit", None)

            # Ensure only one user can have a rare fruit
            if devil_fruit and devil_fruit in DEVIL_FRUITS["Rare"]:
                if devil_fruit in rare_fruit_owners:
                    devil_fruit = None  # Remove duplicate rare fruit assignment
                else:
                    rare_fruit_owners.add(devil_fruit)

            # Save user data
            bounties_data[user_id] = {
                "amount": bounty_amount,
                "fruit": devil_fruit,
            }

        # Save data to bounties.json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(bounties_data, f, indent=4)

        await ctx.send(f"✅ Bounty and Devil Fruit data has been successfully saved to `{file_path}`!")

    @commands.command()
    async def check(self, ctx, member: discord.Member = None):
        """Check a user's bounty, Devil Fruit, and stats."""
        if member is None:
            member = ctx.author

        # Sync data first
        true_bounty = await self.sync_user_data(member)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking stats.")

        # Get synced data
        bounties = load_bounties()
        user_id = str(member.id)
        devil_fruit = bounties[user_id].get("fruit", "None")
        wins = await self.config.member(member).wins()
        losses = await self.config.member(member).losses()
        titles = await self.config.member(member).titles()
        current_title = await self.config.member(member).current_title()

        # Create embed
        embed = discord.Embed(title=f"🏴‍☠️ {member.display_name}'s Status", color=discord.Color.gold())
        embed.add_field(name="<:Beli:1237118142774247425> Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="<:MeraMera:1336888578705330318> Devil Fruit", value=f"`{devil_fruit}`", inline=False)
        embed.add_field(name="🏆 Wins", value=f"`{wins}`", inline=True)
        embed.add_field(name="💀 Losses", value=f"`{losses}`", inline=True)
        embed.add_field(name="🎖️ Titles", value=", ".join(f"`{t}`" for t in titles) if titles else "`None`", inline=False)
        embed.add_field(name="🎭 Current Title", value=f"`{current_title or 'None'}`", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def topfruits(self, ctx):
        """Show which rare Devil Fruits are still available."""
        bounties = load_bounties()
        
        taken_fruits = {data["fruit"] for data in bounties.values() if "fruit" in data and data["fruit"] in DEVIL_FRUITS["Rare"]}
        available_fruits = [fruit for fruit in DEVIL_FRUITS["Rare"] if fruit not in taken_fruits]

        embed = discord.Embed(title="🌟 Rare Devil Fruits Left", color=discord.Color.orange())
        
        if available_fruits:
            embed.description = "\n".join(f"🍏 `{fruit}`" for fruit in available_fruits)
        else:
            embed.description = "❌ No rare fruits left to claim!"

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def berryflip(self, ctx, bet: Optional[int] = None):
        """Flip a coin to potentially increase your bounty. Higher bets have lower win chances!"""
        try:
            user = ctx.author
            
            # Sync data first
            true_bounty = await self.sync_user_data(user)
            if true_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking your bounty.")

            if true_bounty == 0:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")
                
            # Validate bet amount
            if bet is None:
                bet = min(true_bounty, 10000)  # Default to 10k or max bounty
            elif bet < 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Minimum bet is `100` Berries! Don't be stingy!")
            elif bet > true_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ Ye only have `{true_bounty:,}` Berries to bet!")

            # Create initial embed
            embed = discord.Embed(
                title="🎲 Berry Flip Gamble",
                description=f"**{user.display_name}** is betting `{bet:,}` Berries!",
                color=discord.Color.gold()
            )
            
            # Calculate win probability based on bet size
            if bet <= 1000:
                win_probability = 0.75  # 75% chance
                difficulty = "Easy"
            elif bet <= 10000:
                win_probability = 0.60  # 60% chance
                difficulty = "Medium"
            elif bet <= 50000:
                win_probability = 0.40  # 40% chance
                difficulty = "Hard"
            elif bet <= 100000:
                win_probability = 0.20  # 20% chance
                difficulty = "Very Hard"
            else:
                win_probability = 0.10  # 10% chance
                difficulty = "Extreme"

            embed.add_field(
                name="Difficulty",
                value=f"**{difficulty}**\nWin Chance: `{win_probability*100:.0f}%`",
                inline=False
            )

            message = await ctx.send(embed=embed)
            await asyncio.sleep(2)  # Dramatic pause

            # Determine outcome
            won = random.random() < win_probability
            
            # Load bounties for updating
            bounties = load_bounties()
            user_id = str(user.id)
            
            if won:
                # Calculate bonus multiplier based on risk
                multiplier = 1.0
                if bet > 50000:
                    multiplier = 2.0
                elif bet > 10000:
                    multiplier = 1.5
                
                winnings = int(bet * multiplier)
                bounties[user_id]["amount"] += winnings

                bonus_text = f"💫 BONUS WIN! ({multiplier}x Multiplier)\n" if multiplier > 1 else ""
                
                embed.color = discord.Color.green()
                embed.description = (
                    f"🎉 **{user.display_name}** won `{winnings:,}` Berries!\n"
                    f"{bonus_text}"
                    f"New Bounty: `{bounties[user_id]['amount']:,}` Berries"
                )
            else:
                loss = bet
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - loss)
                
                embed.color = discord.Color.red()
                embed.description = (
                    f"💀 **{user.display_name}** lost `{loss:,}` Berries!\n"
                    f"Remaining Bounty: `{bounties[user_id]['amount']:,}` Berries"
                )

            # Save updated bounties
            save_bounties(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

            # Check for new title
            new_bounty = bounties[user_id]["amount"]
            current_title = await self.config.member(user).current_title()
            new_title = self.get_bounty_title(new_bounty)

            if new_title != current_title:
                await self.config.member(user).current_title.set(new_title)
                embed.add_field(
                    name="🎭 New Title Unlocked!",
                    value=f"`{new_title}`",
                    inline=False
                )

            # Announce if reached significant rank
            if new_bounty >= 900_000_000:
                await self.announce_rank(ctx.guild, user, new_title)

            # Update the embed
            await message.edit(embed=embed)

        except Exception as e:
            ctx.command.reset_cooldown(ctx)
            logger.error(f"Error in berryflip command: {str(e)}")
            await ctx.send("❌ An error occurred during the gamble!")

    async def berryflip_error(self, ctx, error):
        """Custom error handler for berryflip command."""
        if isinstance(error, commands.CommandOnCooldown):
            # Only send the cooldown message once
            minutes, seconds = divmod(int(error.retry_after), 60)
            await ctx.send(f"⏳ Wait **{minutes}m {seconds}s** before gambling again!")
            
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def diceroll(self, ctx, bet: Optional[int] = None):
        """Roll dice against the house. Higher bets have lower win chances!"""
        try:
            user = ctx.author
            
            # Sync data first
            true_bounty = await self.sync_user_data(user)
            if true_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking your bounty.")

            if true_bounty == 0:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")
                
            # Validate bet amount
            if bet is None:
                bet = min(true_bounty, 10000)  # Default to 10k or max bounty
            elif bet < 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Minimum bet is `100` Berries!")
            elif bet > true_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ Ye only have `{true_bounty:,}` Berries to bet!")

            # Calculate win probability based on bet size
            if bet <= 1000:
                win_probability = 0.75  # 75% chance
                difficulty = "Easy"
            elif bet <= 10000:
                win_probability = 0.60  # 60% chance
                difficulty = "Medium"
            elif bet <= 50000:
                win_probability = 0.40  # 40% chance
                difficulty = "Hard"
            elif bet <= 100000:
                win_probability = 0.20  # 20% chance
                difficulty = "Very Hard"
            else:
                win_probability = 0.10  # 10% chance
                difficulty = "Extreme"

            # Create initial embed
            embed = discord.Embed(
                title="🎲 Dice Gambling Den",
                description=f"**{user.display_name}** bets `{bet:,}` Berries!",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="Difficulty",
                value=f"**{difficulty}**\nWin Chance: `{win_probability*100:.0f}%`",
                inline=False
            )
            
            message = await ctx.send(embed=embed)
            await asyncio.sleep(2)

            # Roll dice with weighted probability
            won = random.random() < win_probability
            
            # Load bounties for updating
            bounties = load_bounties()
            user_id = str(user.id)
            
            if won:
                # Calculate bonus multiplier based on risk
                multiplier = 1.0
                if bet > 50000:
                    multiplier = 2.0
                elif bet > 10000:
                    multiplier = 1.5
                
                winnings = int(bet * multiplier)
                bounties[user_id]["amount"] += winnings
                
                bonus_text = f"💫 BONUS WIN! ({multiplier}x Multiplier)\n" if multiplier > 1 else ""
                
                embed.color = discord.Color.green()
                embed.description = (
                    f"🎲 **{user.display_name}** wins!\n"
                    f"{bonus_text}"
                    f"Won `{winnings:,}` Berries!\n"
                    f"New Bounty: `{bounties[user_id]['amount']:,}` Berries"
                )
            else:
                loss = bet
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - loss)
                
                embed.color = discord.Color.red()
                embed.description = (
                    f"🎲 **{user.display_name}** loses!\n"
                    f"Lost `{loss:,}` Berries!\n"
                    f"Remaining Bounty: `{bounties[user_id]['amount']:,}` Berries"
                )

            # Save updated bounties
            save_bounties(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

            # Update the embed
            await message.edit(embed=embed)

        except Exception as e:
            ctx.command.reset_cooldown(ctx)
            logger.error(f"Error in diceroll command: {str(e)}")
            await ctx.send("❌ An error occurred during the gamble!")

    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def blackjack(self, ctx, bet: Optional[int] = None):
        """Play blackjack against the house. Higher bets mean the house plays better!"""
        try:
            user = ctx.author
            
            # Sync data first
            true_bounty = await self.sync_user_data(user)
            if true_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking your bounty.")

            if true_bounty == 0:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")
                
            # Validate bet amount
            if bet is None:
                bet = min(true_bounty, 10000)  # Default to 10k or max bounty
            elif bet < 100:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ Minimum bet is `100` Berries!")
            elif bet > true_bounty:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f"❌ Ye only have `{true_bounty:,}` Berries to bet!")

            # Calculate house skill based on bet size
            if bet <= 1000:
                house_stand_threshold = 15  # House stands on 15 or higher
                difficulty = "Easy"
                win_desc = "House plays conservatively"
            elif bet <= 10000:
                house_stand_threshold = 16
                difficulty = "Medium"
                win_desc = "House plays normally"
            elif bet <= 50000:
                house_stand_threshold = 17
                difficulty = "Hard"
                win_desc = "House plays optimally"
            elif bet <= 100000:
                house_stand_threshold = 18
                difficulty = "Very Hard"
                win_desc = "House has years of experience"
            else:
                house_stand_threshold = 19
                difficulty = "Extreme"
                win_desc = "House never makes mistakes"

            # Create initial embed with difficulty info
            embed = discord.Embed(
                title="♠️ Blackjack Table",
                description=(
                    f"**{user.display_name}** bets `{bet:,}` Berries!\n\n"
                    f"**Difficulty:** {difficulty}\n"
                    f"**House Strategy:** {win_desc}"
                ),
                color=discord.Color.gold()
            )
            
            message = await ctx.send(embed=embed)

            # Initialize deck and hands
            deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
            random.shuffle(deck)
            
            player_hand = [deck.pop(), deck.pop()]
            dealer_hand = [deck.pop(), deck.pop()]

            def calculate_hand(hand):
                total = sum(hand)
                aces = hand.count(11)
                while total > 21 and aces:
                    total -= 10
                    aces -= 1
                return total

            def display_hands(show_dealer=False):
                dealer_total = calculate_hand(dealer_hand) if show_dealer else calculate_hand([dealer_hand[0]])
                player_total = calculate_hand(player_hand)
                
                embed.clear_fields()
                embed.add_field(
                    name="Dealer's Hand",
                    value=f"{dealer_hand[0]}, {'?' if not show_dealer else ', '.join(map(str, dealer_hand[1:]))}\n"
                        f"Total: {dealer_total}",
                    inline=False
                )
                embed.add_field(
                    name="Your Hand",
                    value=f"{', '.join(map(str, player_hand))}\nTotal: {player_total}",
                    inline=False
                )

            # Player's turn
            display_hands()
            while calculate_hand(player_hand) < 21:
                embed.description = "Type `hit` or `stand`"
                await message.edit(embed=embed)
                
                try:
                    def check(m):
                        return m.author == user and m.channel == ctx.channel and \
                            m.content.lower() in ['hit', 'stand']
                    
                    response = await self.bot.wait_for('message', timeout=30.0, check=check)
                    
                    if response.content.lower() == 'hit':
                        player_hand.append(deck.pop())
                        display_hands()
                        await message.edit(embed=embed)
                    else:
                        break
                        
                except asyncio.TimeoutError:
                    embed.description = "Time's up! Standing with current hand."
                    await message.edit(embed=embed)
                    break

            # Dealer's turn - follows optimal strategy based on bet size
            player_total = calculate_hand(player_hand)
            if player_total <= 21:
                while calculate_hand(dealer_hand) < house_stand_threshold:
                    dealer_hand.append(deck.pop())

            # Show final hands
            display_hands(show_dealer=True)
            
            # Load bounties for updating
            bounties = load_bounties()
            user_id = str(user.id)
            
            # Determine winner and calculate rewards
            dealer_total = calculate_hand(dealer_hand)
            
            if player_total > 21:
                result = "Bust! You lose!"
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - bet)
                embed.color = discord.Color.red()
            elif dealer_total > 21:
                result = "Dealer busts! You win!"
                winnings = int(bet * 1.5)  # Blackjack pays 3:2
                bounties[user_id]["amount"] += winnings
                embed.color = discord.Color.green()
            elif player_total > dealer_total:
                result = "You win!"
                winnings = bet
                bounties[user_id]["amount"] += winnings
                embed.color = discord.Color.green()
            elif dealer_total > player_total:
                result = "Dealer wins!"
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - bet)
                embed.color = discord.Color.red()
            else:
                result = "Push! It's a tie!"
                embed.color = discord.Color.blue()

            embed.description = f"{result}\nNew Bounty: `{bounties[user_id]['amount']:,}` Berries"
            
            # Save updated bounties
            save_bounties(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

            await message.edit(embed=embed)

        except Exception as e:
            ctx.command.reset_cooldown(ctx)
            logger.error(f"Error in blackjack command: {str(e)}")
            await ctx.send("❌ An error occurred during the gamble!")
        
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)  # 30 minute cooldown
    async def marinehunt(self, ctx):
        """Hunt Marine ships for bounty rewards. Beware of powerful encounters!"""
        user = ctx.author
        
        # Sync user data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("❌ An error occurred while checking your bounty.")

        if true_bounty == 0:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")

        # Define marine ranks with enhanced rewards and flavor
        MARINE_RANKS = {
            "Marine Recruit": {
                "reward": (500, 2000),
                "risk": 0.9,
                "flavor": [
                    "A small patrol boat manned by fresh recruits.",
                    "The recruits are shaking at the sight of a pirate!",
                    "Their cannons aren't even properly maintained..."
                ]
            },
            "Marine Chore Boy": {
                "reward": (1000, 3000),
                "risk": 0.85,
                "flavor": [
                    "Coby and Helmeppo are leading this patrol!",
                    "They're more focused on cleaning than fighting...",
                    "At least their ship is spotless!"
                ]
            },
            "Marine Soldier": {
                "reward": (2000, 5000),
                "risk": 0.8,
                "flavor": [
                    "A standard Marine vessel on patrol.",
                    "The soldiers look well-trained, but inexperienced.",
                    "They're following textbook formations."
                ]
            },
            "Marine Officer": {
                "reward": (4000, 8000),
                "risk": 0.75,
                "flavor": [
                    "A skilled Marine officer leads this ship.",
                    "They've seen their share of pirate battles.",
                    "Their tactical approach could be troublesome."
                ]
            },
            "Marine Lieutenant": {
                "reward": (6000, 12000),
                "risk": 0.7,
                "flavor": [
                    "A seasoned Lieutenant commands this warship.",
                    "They've already called for reinforcements!",
                    "The crew moves with military precision."
                ]
            },
            "Marine Captain": {
                "reward": (10000, 20000),
                "risk": 0.65,
                "flavor": [
                    "Captain Tashigi spotted! She's after your sword!",
                    "The Captain's reputation precedes them.",
                    "Their ship bears battle scars from previous encounters."
                ]
            },
            "Marine Commodore": {
                "reward": (15000, 30000),
                "risk": 0.6,
                "flavor": [
                    "Commodore Smoker's distinctive vessel approaches!",
                    "The White Hunter himself is on patrol.",
                    "Clouds of smoke are already visible..."
                ]
            },
            "Marine Vice Admiral": {
                "reward": (25000, 50000),
                "risk": 0.5,
                "flavor": [
                    "Vice Admiral Garp's dog mask is visible from here!",
                    "The Hero of the Marines stands ready.",
                    "They're carrying a suspicious amount of cannonballs..."
                ]
            },
            "Marine Admiral": {
                "reward": (50000, 100000),
                "risk": 0.4,
                "flavor": [
                    "Admiral Kizaru's blinding light approaches!",
                    "Admiral Aokiji's ice path freezes the sea!",
                    "Admiral Akainu's magma melts the surrounding ships!"
                ]
            },
            "Fleet Admiral": {
                "reward": (100000, 200000),
                "risk": 0.3,
                "flavor": [
                    "Fleet Admiral Sakazuki himself has arrived!",
                    "The strongest Marine vessel ever built...",
                    "Absolute Justice will be served!"
                ]
            },
            "CP9": {
                "reward": (150000, 250000),
                "risk": 0.25,
                "flavor": [
                    "The World Government's assassins appear!",
                    "Rob Lucci's leopard form is spotted...",
                    "Their mastery of the Six Powers is fearsome!"
                ]
            },
            "CP0": {
                "reward": (200000, 300000),
                "risk": 0.2,
                "flavor": [
                    "The masks of CP0 emerge from the shadows...",
                    "The World Government's strongest agents!",
                    "Even Admiral's fear their approach..."
                ]
            },
            "Gorosei": {
                "reward": (500000, 1000000),
                "risk": 0.1,
                "flavor": [
                    "The Five Elders themselves have taken action!",
                    "The true power of Im-sama's servants...",
                    "The fate of the world hangs in the balance!"
                ]
            },
            "Im-sama": {
                "reward": (1000000, 2000000),
                "risk": 0.05,
                "flavor": [
                    "The empty throne was not so empty after all...",
                    "The true ruler of the World Government appears!",
                    "Few pirates have lived to tell of this encounter!"
                ]
            }
        }

        # Special events that can occur during the hunt
        SPECIAL_EVENTS = [
            "A Celestial Dragon's ship is passing nearby! The Marines are distracted!",
            "A Sea King appears, causing chaos among the Marine ranks!",
            "Revolutionary Army ships are engaging the Marines in the distance!",
            "Mysterious fog rolls in, providing cover for your attack!",
            "A whirlpool forms, affecting ship maneuverability!"
        ]

        # Randomly select rank with weighting based on bounty
        available_ranks = list(MARINE_RANKS.keys())
        weights = []
        for rank in available_ranks:
            if true_bounty < 10000:  # New pirates
                weights.append(5 if rank in ["Marine Recruit", "Marine Chore Boy", "Marine Soldier"] else 1)
            elif true_bounty < 100000:  # Rising pirates
                weights.append(5 if rank in ["Marine Officer", "Marine Lieutenant", "Marine Captain"] else 1)
            elif true_bounty < 1000000:  # Notorious pirates
                weights.append(5 if rank in ["Marine Commodore", "Marine Vice Admiral", "Marine Admiral"] else 1)
            else:  # Legendary pirates
                weights.append(5 if rank in ["Fleet Admiral", "CP9", "CP0", "Gorosei", "Im-sama"] else 1)

        current_rank = random.choices(available_ranks, weights=weights)[0]
        rank_data = MARINE_RANKS[current_rank]

        # Randomly decide if a special event occurs
        special_event = random.random() < 0.2  # 20% chance
        if special_event:
            event_text = random.choice(SPECIAL_EVENTS)
            rank_data["risk"] += 0.1  # Increase success chance during special events

        # Create initial embed
        embed = discord.Embed(
            title="🏴‍☠️ Marine Hunt",
            description=f"**{current_rank}** spotted on the horizon!",
            color=discord.Color.blue()
        )
        
        # Add flavor text
        embed.add_field(
            name="👀 Scout Report",
            value=random.choice(rank_data["flavor"]),
            inline=False
        )

        if special_event:
            embed.add_field(
                name="⚡ Special Event!",
                value=event_text,
                inline=False
            )
        
        # Add engagement option
        embed.add_field(
            name="⚔️ Options",
            value="Type `attack` to engage or `flee` to retreat!",
            inline=False
        )
        
        message = await ctx.send(embed=embed)

        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and \
                    m.content.lower() in ['attack', 'flee']
            
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            if response.content.lower() == 'flee':
                flee_messages = [
                    "You live to fight another day!",
                    "A tactical retreat is sometimes the best option...",
                    "The Marines shout threats as you escape!",
                    "Better to preserve your crew than risk it all!"
                ]
                embed.description = random.choice(flee_messages)
                embed.color = discord.Color.green()
                await message.edit(embed=embed)
                return

            # Calculate success chance
            success_chance = rank_data["risk"]
            if await self.config.member(user).devil_fruit():  # Bonus for Devil Fruit users
                success_chance += 0.1

            # Determine outcome
            success = random.random() < success_chance

            if success:
                # Calculate reward
                min_reward, max_reward = rank_data["reward"]
                reward = random.randint(min_reward, max_reward)
                
                # Add bonus for special events
                if special_event:
                    reward = int(reward * 1.5)
                
                # Update bounty
                bounties = load_bounties()
                user_id = str(user.id)
                bounties[user_id]["amount"] += reward
                save_bounties(bounties)
                await self.config.member(user).bounty.set(bounties[user_id]["amount"])
                
                # Create success embed
                victory_messages = [
                    f"You've defeated the {current_rank}!",
                    "Justice has been evaded once again!",
                    "The Marines retreat in shame!",
                    "Another victory for the pirates!"
                ]
                
                embed = discord.Embed(
                    title="⚔️ Victory!",
                    description=random.choice(victory_messages),
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="<:Beli:1237118142774247425> Reward",
                    value=f"`{reward:,}` Berries",
                    inline=False
                )
                embed.add_field(
                    name="🏴‍☠️ New Bounty",
                    value=f"`{bounties[user_id]['amount']:,}` Berries",
                    inline=False
                )
                
                # Check for rank increase
                new_title = self.get_bounty_title(bounties[user_id]["amount"])
                if new_title != self.get_bounty_title(true_bounty):
                    embed.add_field(
                        name="👑 New Title!",
                        value=f"`{new_title}`",
                        inline=False
                    )
                
            else:
                # Calculate penalty
                penalty = int(true_bounty * 0.05)  # 5% bounty loss
                
                # Update bounty
                bounties = load_bounties()
                user_id = str(user.id)
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - penalty)
                save_bounties(bounties)
                await self.config.member(user).bounty.set(bounties[user_id]["amount"])
                
                # Create failure embed
                defeat_messages = [
                    f"The {current_rank} was too powerful!",
                    "The Marines celebrate their victory!",
                    "Your crew barely escapes with their lives!",
                    "Justice prevails this time..."
                ]
                
                embed = discord.Embed(
                    title="❌ Defeat!",
                    description=random.choice(defeat_messages),
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="💸 Penalty",
                    value=f"`{penalty:,}` Berries",
                    inline=False
                )
                embed.add_field(
                    name="🏴‍☠️ Remaining Bounty",
                    value=f"`{bounties[user_id]['amount']:,}` Berries",
                    inline=False
                )

            await message.edit(embed=embed)

        except asyncio.TimeoutError:
            timeout_messages = [
                "You took too long to decide, and the Marine ship sailed away!",
                "The opportunity slips through your fingers...",
                "The Marines disappear into the fog...",
                "Perhaps hesitation was the better part of valor..."
            ]
            embed.description = random.choice(timeout_messages)
            embed.color = discord.Color.greyple()
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in marinehunt command: {str(e)}")
            await ctx.send("❌ An error occurred during the marine hunt!")
            
    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def raid(self, ctx):
        """Organize raids against powerful enemies like Yonko or Marine fortresses."""
        try:
            user = ctx.author
            
            # Sync user data first
            true_bounty = await self.sync_user_data(user)
            if true_bounty is None:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ An error occurred while checking your bounty.")

            if true_bounty < 100000:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ You need at least `100,000` Berries bounty to attempt raids!")

            # Create raid selection embed
            embed = discord.Embed(
                title="🏴‍☠️ Available Raid Targets",
                description="Choose your target by typing its number:",
                color=discord.Color.dark_red()
            )

            available_targets = []
            for _, (target, data) in enumerate(self.current_bosses.items(), 1):
                if true_bounty >= 100000 and target == "Marine Fortress":
                    available_targets.append(target)
                elif true_bounty >= 500000 and target == "Impel Down":
                    available_targets.append(target)
                elif true_bounty >= 1000000 and target == "Enies Lobby":
                    available_targets.append(target)
                elif true_bounty >= 5000000 and target == "Yonko Territory":
                    available_targets.append(target)
                elif true_bounty >= 10000000 and target == "Mary Geoise":
                    available_targets.append(target)

                if target in available_targets:
                    embed.add_field(
                        name=f"{len(available_targets)}. {target} ({data['level']})",
                        value=(
                            f"Boss: `{data['boss']}`\n"
                            f"Min. Players: `{1 if data['level'] == 'Easy' else 2 if data['level'] == 'Medium' else 3 if data['level'] == 'Hard' else 4}`\n"
                            f"Reward: `{50000 * (2 ** (len(available_targets)-1)):,}` - `{100000 * (2 ** (len(available_targets)-1)):,}` Berries"
                        ),
                        inline=False
                    )

            if not available_targets:
                ctx.command.reset_cooldown(ctx)
                return await ctx.send("❌ No raid targets available at your bounty level!")

            await ctx.send(embed=embed)

            try:
                def check(m):
                    return m.author == user and m.channel == ctx.channel and \
                        m.content.isdigit() and 1 <= int(m.content) <= len(available_targets)

                target_choice = await self.bot.wait_for('message', timeout=30.0, check=check)
                selected_target = available_targets[int(target_choice.content) - 1]
                target_data = self.current_bosses[selected_target]

                # Get required number of players
                required_players = 1 if target_data['level'] == 'Easy' else 2 if target_data['level'] == 'Medium' else 3 if target_data['level'] == 'Hard' else 4

                # Create raid preparation embed
                prep_embed = discord.Embed(
                    title=f"⚔️ Raid on {selected_target}",
                    description=(
                        f"**Target:** {selected_target}\n"
                        f"**Boss:** {target_data['boss']}\n"
                        f"**Required Crew:** {required_players} players\n\n"
                        f"Type `enter` to join the raid! ({required_players} spots available)\n"
                        f"Captain can type `battle` when ready!"
                    ),
                    color=discord.Color.blue()
                )
                prep_msg = await ctx.send(embed=prep_embed)

                # Track raiders
                raiders = [user]  # Include raid starter
                required_remaining = required_players - 1  # Subtract raid starter

                # Wait for raiders
                while len(raiders) < required_players and required_remaining > 0:
                    def raider_check(m):
                        return (m.content.lower() == 'enter' and m.author not in raiders and not m.author.bot) or \
                            (m.content.lower() == 'battle' and m.author == user)

                    try:
                        response = await self.bot.wait_for('message', timeout=60.0, check=raider_check)
                        
                        if response.content.lower() == 'battle':
                            if len(raiders) >= required_players:
                                break
                            else:
                                await ctx.send(f"❌ Need {required_remaining} more raiders before starting!")
                                continue
                                
                        elif response.content.lower() == 'enter' and response.author not in raiders:
                            # Verify raider has enough bounty
                            raider_bounty = await self.sync_user_data(response.author)
                            if raider_bounty is None or raider_bounty < 100000:
                                await ctx.send(f"❌ {response.author.mention} needs at least `100,000` Berries bounty to join!")
                                continue

                            raiders.append(response.author)
                            required_remaining -= 1
                            
                            # Update embed with current raiders
                            prep_embed.description = (
                                f"**Target:** {selected_target}\n"
                                f"**Boss:** {target_data['boss']}\n"
                                f"**Required Crew:** {required_players} players\n\n"
                                f"**Current Raiders:**\n"
                                + "\n".join([f"• {raider.display_name}" for raider in raiders])
                                + f"\n\n{required_remaining} spots remaining!"
                                + "\nCaptain can type `battle` when ready!"
                            )
                            await prep_msg.edit(embed=prep_embed)

                    except asyncio.TimeoutError:
                        return await ctx.send("❌ Not enough raiders joined in time! Raid cancelled.")

                # Calculate success chance based on level and difficulty
                base_chance = 0.0  # Initialize base chance
                if target_data['level'] == "Easy":
                    base_chance = 0.7
                elif target_data['level'] == "Medium":
                    base_chance = 0.5
                elif target_data['level'] == "Hard":
                    base_chance = 0.3
                elif target_data['level'] == "Very Hard":
                    base_chance = 0.2
                elif target_data['level'] == "Extreme":
                    base_chance = 0.1

                # Add bonuses
                player_bonus = min(0.1 * (len(raiders) - required_players), 0.3)

                # Count fruit users correctly
                fruit_users = 0
                for raider in raiders:
                    devil_fruit = await self.config.member(raider).devil_fruit()
                    if devil_fruit:
                        fruit_users += 1

                fruit_bonus = min(0.05 * fruit_users, 0.15)

                # Calculate final chance
                final_chance = min(base_chance + player_bonus + fruit_bonus, 0.9)

                # Calculate base reward based on difficulty
                if target_data['level'] == "Easy":
                    base_reward = random.randint(50000, 100000)
                elif target_data['level'] == "Medium":
                    base_reward = random.randint(100000, 200000)
                elif target_data['level'] == "Hard":
                    base_reward = random.randint(200000, 400000)
                elif target_data['level'] == "Very Hard":
                    base_reward = random.randint(400000, 800000)
                else:  # Extreme
                    base_reward = random.randint(800000, 1600000)

                # Create battle embed
                battle_embed = discord.Embed(
                    title=f"⚔️ Raid Battle Against {target_data['boss']}",
                    description=(
                        f"**Raiders:**\n"
                        + "\n".join([f"• {raider.display_name}" for raider in raiders])
                        + f"\n\nSuccess Chance: `{final_chance*100:.1f}%`"
                    ),
                    color=discord.Color.gold()
                )
                await ctx.send(embed=battle_embed)

                # Add battle animation
                battle_messages = [
                    f"💨 **{target_data['boss']}** prepares for battle...",
                    f"💥 The raiders charge into combat!",
                    "⚔️ **CLASH!** The sound of battle echoes across the seas!"
                ]

                battle_msg = await ctx.send(battle_messages[0])
                await asyncio.sleep(2)

                for message in battle_messages[1:]:
                    await battle_msg.edit(content=message)
                    await asyncio.sleep(2)

                # Add random battle events
                battle_events = [
                    f"🌊 A massive wave crashes into the battlefield!",
                    f"⚡ Lightning strikes illuminate the sky!",
                    f"💫 {random.choice(raiders).display_name} lands a powerful blow!",
                    f"🔥 The air itself seems to burn with fighting spirit!",
                    f"💪 The raiders show their true strength!",
                    f"🌪️ A storm begins to brew from the intensity!",
                    f"🚀 Special techniques are flying everywhere!",
                    f"💥 The ground shakes from the powerful attacks!"
                ]

                # Show 2-3 random battle events
                for _ in range(random.randint(2, 3)):
                    event = random.choice(battle_events)
                    await ctx.send(content=event)
                    await asyncio.sleep(2)

                # Final dramatic pause
                final_messages = [
                    "💭 The dust begins to settle...",
                    "👀 Everyone holds their breath...",
                    "⏳ The outcome will be decided..."
                ]

                final_msg = await ctx.send(final_messages[0])
                for message in final_messages[1:]:
                    await asyncio.sleep(2)
                    await final_msg.edit(content=message)

                await asyncio.sleep(2)

                # Determine outcome
                success = random.random() < final_chance

                if success:
                    # Give rewards to all raiders
                    success_embed = discord.Embed(
                        title="🎉 Raid Successful!",
                        description=f"The raid on {selected_target} was successful!",
                        color=discord.Color.green()
                    )

                    # Process rewards
                    for raider in raiders:
                        bounties = load_bounties()
                        raider_id = str(raider.id)
                        
                        if raider_id in bounties:
                            bounties[raider_id]["amount"] += base_reward
                            save_bounties(bounties)
                            await self.config.member(raider).bounty.set(bounties[raider_id]["amount"])

                    success_embed.add_field(
                        name="<:Beli:1237118142774247425> Rewards",
                        value=f"Each raider earned `{base_reward:,}` Berries!",
                        inline=False
                    )
                    success_embed.add_field(
                        name="⚔️ Raiders",
                        value="\n".join([raider.mention for raider in raiders]),
                        inline=False
                    )
                    
                    await ctx.send(embed=success_embed)

                else:
                    # Calculate penalties
                    penalty = int(base_reward * 0.1)  # 10% of potential reward
                    
                    failure_embed = discord.Embed(
                        title="❌ Raid Failed!",
                        description=f"The raid on {selected_target} was unsuccessful!",
                        color=discord.Color.red()
                    )

                    # Apply penalties
                    for raider in raiders:
                        bounties = load_bounties()
                        raider_id = str(raider.id)
                        
                        if raider_id in bounties:
                            bounties[raider_id]["amount"] = max(0, bounties[raider_id]["amount"] - penalty)
                            save_bounties(bounties)
                            await self.config.member(raider).bounty.set(bounties[raider_id]["amount"])

                    failure_embed.add_field(
                        name="💸 Penalties",
                        value=f"Each raider lost `{penalty:,}` Berries!",
                        inline=False
                    )
                    failure_embed.add_field(
                        name="⚔️ Raiders",
                        value="\n".join([raider.mention for raider in raiders]),
                        inline=False
                    )
                    
                    await ctx.send(embed=failure_embed)

            except asyncio.TimeoutError:
                await ctx.send("Raid planning timed out! Try again later.")
                
        except Exception as e:
            logger.error(f"Error in raid command: {str(e)}")
            await ctx.send(f"An error occurred: {str(e)}")
        
    @commands.command()
    async def missions(self, ctx):
        """Display available missions."""
        missions = [
            {"description": "Answer a trivia question", "reward": random.randint(500, 2000)},
            {"description": "Share a fun fact", "reward": random.randint(500, 2000)},
            {"description": "Post a meme", "reward": random.randint(500, 2000)},
        ]
        embed = discord.Embed(title="Available Missions", color=discord.Color.green())
        for i, mission in enumerate(missions, start=1):
            embed.add_field(name=f"Mission {i}", value=f"{mission['description']} - Reward: {mission['reward']} Berries", inline=False)
        await ctx.send(embed=embed)
        
    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.user)
    async def completemission(self, ctx, mission_number: int):
        """Complete a mission to earn bounty."""
        missions = [
            {"description": "Answer a trivia question", "reward": random.randint(500, 2000)},
            {"description": "Share a fun fact", "reward": random.randint(500, 2000)},
            {"description": "Post a meme", "reward": random.randint(500, 2000)},
        ]
        if mission_number < 1 or mission_number > len(missions):
            return await ctx.send("Invalid mission number. Please choose a valid mission.")

        mission = missions[mission_number - 1]
        user = ctx.author

        # Ensure user has started their bounty journey
        bounties = load_bounties()
        user_id = str(user.id)
        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        # Validate mission completion based on mission type
        if mission["description"] == "Answer a trivia question":
            success = await self.handle_trivia_question(ctx, user)
        elif mission["description"] == "Share a fun fact":
            success = await self.handle_fun_fact(ctx, user)
        elif mission["description"] == "Post a meme":
            success = await self.handle_post_meme(ctx, user)

        if success:
            # Get the reward amount
            reward = mission["reward"]

            # Update bounties in JSON file
            bounties[user_id]["amount"] = bounties[user_id].get("amount", 0) + reward
            save_bounties(bounties)

            # Update bounty in config
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])

            # Get the new title based on the updated bounty
            new_title = self.get_bounty_title(bounties[user_id]["amount"])

            # Send confirmation message
            await ctx.send(f"🏆 Mission completed! Ye earned {reward:,} Berries! Yer new bounty is {bounties[user_id]['amount']:,} Berries!\n"
                        f"Current Title: {new_title}")

            # Announce if the user reaches a significant rank
            if bounties[user_id]["amount"] >= 900000000:
                await self.announce_rank(ctx.guild, user, new_title)

    async def handle_trivia_question(self, ctx, user):
        """Handle the trivia question mission."""
        await ctx.send("What is the capital of France?")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "paris":
                await ctx.send("Correct! You have completed the mission.")
                return True
            else:
                await ctx.send("Incorrect answer. Mission failed.")
                return False
        except asyncio.TimeoutError:
            await ctx.send("You took too long to answer. Mission failed.")
            return False

    async def handle_fun_fact(self, ctx, user):
        """Handle the fun fact mission."""
        await ctx.send("Please share a fun fact.")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            await ctx.send(f"Fun fact received: {msg.content}")
            return True
        except asyncio.TimeoutError:
            await ctx.send("You took too long to share a fun fact. Mission failed.")
            return False

    async def handle_post_meme(self, ctx, user):
        """Handle the post a meme mission."""
        await ctx.send("Please post a meme.")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.attachments
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            await ctx.send("Meme received.")
            return True
        except asyncio.TimeoutError:
            await ctx.send("You took too long to post a meme. Mission failed.")
            return False

    async def check_milestones(self, ctx, user, new_bounty):
        """Check if the user has reached any bounty milestones."""
        milestones = {
            1000000: "First Million!",
            10000000: "Ten Million!",
            50000000: "Fifty Million!",
            100000000: "Hundred Million!",
        }

        for amount, title in milestones.items():
            if new_bounty >= amount:
                await ctx.send(f"🎉 {user.mention} has reached the milestone: **{title}** with a bounty of {new_bounty:,} Berries!")

    # ------------------ Deathmatch System ------------------

    # --- Helper Functions ---
    def generate_health_bar(self, current_hp: int, max_hp: int = 250, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"

    def get_status_icons(self, player_data: dict) -> str:
        """Get status effect icons for display."""
        STATUS_EMOJI = {
            "burn": "🔥",
            "stun": "⚡",
            "frozen": "❄️",
            "protected": "🛡️",
            "transformed": "✨",
            "poison": "☠️"
        }
        
        status_icons = []
        for status, active in player_data["status"].items():
            if active and status in STATUS_EMOJI:
                if isinstance(active, bool) and active:
                    status_icons.append(STATUS_EMOJI[status])
                elif isinstance(active, (int, float)) and active > 0:
                    status_icons.append(f"{STATUS_EMOJI[status]}x{active}")
                    
        return " ".join(status_icons) if status_icons else "✨ None"

    def calculate_damage(self, move, attacker_data, turn_number):
        """Calculate balanced damage considering cooldowns and effects."""
        # Check if move is on cooldown
        if move["name"] in attacker_data["moves_on_cooldown"]:
            if attacker_data["moves_on_cooldown"][move["name"]] > 0:
                return 0, "Move is on cooldown!"

        move_type = MOVE_TYPES[move["type"]]
        base_min, base_max = move_type["base_damage_range"]
        base_damage = random.randint(base_min, base_max)

        # Critical hit calculation
        crit_chance = move.get("crit_chance", move_type["crit_chance"])
        if random.random() < crit_chance:
            base_damage *= 1.5
            message = "Critical hit!"
            attacker_data["stats"]["critical_hits"] += 1
        else:
            message = None

        # Apply scaling with turn number for longer battles
        turn_scaling = 1 + (turn_number * 0.05)  # 5% increase per turn
        final_damage = int(base_damage * turn_scaling)

        # Set cooldown if the move has one
        if move["cooldown"] > 0:
            self.set_move_cooldown(move["name"], move["cooldown"], attacker_data)  # Changed this line to use self

        return final_damage, message

    def generate_fight_card(self, user1, user2):
        """
        Generates a dynamic fight card image with avatars and usernames.
        Uses asyncio-friendly approach for image processing.
        """
        TEMPLATE_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/deathbattle.png"
        FONT_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/onepiece.ttf"

        # Open the local template image
        try:
            template = Image.open(TEMPLATE_PATH)
            draw = ImageDraw.Draw(template)
        except (FileNotFoundError, IOError):
            self.log.error(f"Template image not found at {TEMPLATE_PATH}")
            # Create a fallback blank image
            template = Image.new('RGBA', (650, 500), color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(template)
            draw.text((50, 200), "Fight Card Template Missing", fill="black")

        # Load font
        try:
            username_font = ImageFont.truetype(FONT_PATH, 25)
        except (OSError, IOError):
            self.log.warning(f"Font file not found at {FONT_PATH}, using default")
            username_font = ImageFont.load_default()

        # Avatar dimensions and positions
        avatar_size = (250, 260)  # Adjust as needed
        avatar_positions = [(15, 130), (358, 130)]  # Positions for avatars
        username_positions = [(75, 410), (430, 410)]  # Positions for usernames

        # Fetch and paste avatars
        for i, user in enumerate((user1, user2)):
            try:
                # Use a more efficient, direct approach to fetch avatars
                avatar_url = user.display_avatar.url
                
                # Use requests with a timeout
                avatar_response = requests.get(avatar_url, timeout=2)
                avatar = Image.open(io.BytesIO(avatar_response.content)).convert("RGBA")
                avatar = avatar.resize(avatar_size)
                
                # Paste avatar onto the template
                template.paste(avatar, avatar_positions[i], avatar)
                
                # Draw username
                username = user.display_name[:20]  # Limit username length
                draw.text(username_positions[i], username, font=username_font, fill="black")
            except Exception as e:
                self.log.error(f"Error processing avatar for {user.display_name}: {e}")
                # Add a placeholder text instead
                draw.rectangle([avatar_positions[i], 
                            (avatar_positions[i][0] + avatar_size[0], 
                            avatar_positions[i][1] + avatar_size[1])], 
                            outline="black", fill="gray")
                draw.text((avatar_positions[i][0] + 50, avatar_positions[i][1] + 130), 
                        "Avatar Error", fill="black")

        # Save the image to a BytesIO object
        output = io.BytesIO()
        template.save(output, format="PNG", optimize=True)
        output.seek(0)

        return output

    async def apply_effects(self, move: dict, attacker: dict, defender: dict):
        """Apply special effects like burn, heal, stun, or crit."""
        effect = move.get("effect")
        if effect == "burn":
            if random.random() < move.get("burn_chance", 0):
                defender["status"]["burn"] += 1
                defender["status"]["burn"] = min(defender["status"]["burn"], 3)  # Cap burn stacks at 3
        elif effect == "heal":
            attacker["hp"] = min(100, attacker["hp"] + 10)
        elif effect == "stun":
            defender["status"]["stun"] = True
        elif effect == "crit":
            attacker["crit_hit"] = True  # Add crit tracking for stats

    async def check_achievements(self, member):
        """Check and unlock achievements for the member."""
        stats = await self.config.member(member).all()  # Get stats inside the function
        user_achievements = stats.get("achievements", [])
        unlocked_titles = stats.get("titles", [])
        unlocked = []
    
        for key, data in ACHIEVEMENTS.items():
            if key in user_achievements:
                continue  # Already unlocked
    
            current_stat = stats.get(data["condition"], 0)
            required_count = data["count"]
    
            if isinstance(required_count, str) and required_count == "all":
                required_count = float('inf')  # "all" means infinite
    
            if current_stat >= required_count:
                user_achievements.append(key)
                unlocked.append(data["description"])
    
                if "title" in data and data["title"] not in unlocked_titles:
                    unlocked_titles.append(data["title"])
                    try:
                        await member.send(f"🎉 Congratulations! You've unlocked the title: **{data['title']}**")
                    except discord.Forbidden:
                        self.log.warning(f"Could not send DM to {member.display_name}. They might have DMs disabled.")
    
        await self.config.member(member).achievements.set(user_achievements)
        await self.config.member(member).titles.set(unlocked_titles)
    
        return unlocked

    async def display_achievements(self, ctx: commands.Context, member: discord.Member = None):
        """Show achievements for a user in a stylish embed."""
        member = member or ctx.author
        achievements = await self.config.member(member).achievements()
        if not achievements:
            await ctx.send(f"**{member.display_name}** has not unlocked any achievements yet.")
            return

        embed = discord.Embed(
            title=f"🏴‍☠️ {member.display_name}'s Achievements 🏴‍☠️",
            description="Here are the achievements they've unlocked:",
            color=0x00FF00,
        )
        for key in achievements:
            if key in ACHIEVEMENTS:
                embed.add_field(
                    name=ACHIEVEMENTS[key]["description"],
                    value="🔓 **Unlocked**",
                    inline=False,
                )
        await ctx.send(embed=embed)
        
    def choose_environment(self):
        """Randomly select an environment from One Piece islands."""
        self.current_environment = random.choice(list(ENVIRONMENTS.keys()))
        return self.current_environment
    
    async def apply_environmental_hazard(self, environment, players):
        """Apply random hazards or buffs based on the environment."""
        hazard_message = None

        if environment == "Skypiea" and random.random() < 0.3:  # 30% chance
            hazard_damage = random.randint(10, 15)
            for player in players:
                player["hp"] = max(0, player["hp"] - hazard_damage)
            hazard_message = f"⚡ **DIVINE LIGHTNING!** A bolt strikes from above, dealing `{hazard_damage}` damage to both players!"

        elif environment == "Alabasta" and random.random() < 0.3:
            for player in players:
                player["status"]["accuracy_reduction"] = 0.2
                player["status"]["accuracy_turns"] = 3
            hazard_message = "🌪️ **SANDSTORM RAGES!** A fierce sandstorm reduces accuracy by 20% for 3 turns!"

        elif environment == "Wano" and random.random() < 0.3:
            for player in players:
                player["status"]["strong_damage_boost"] = 5
                player["status"]["boost_turns"] = 3
            hazard_message = "🗡️ **SAMURAI SPIRITS!** The legends of Wano empower strong attacks!"

        elif environment == "Punk Hazard" and random.random() < 0.3:
            hazard_damage = random.randint(5, 10)
            for player in players:
                player["hp"] = max(0, player["hp"] - hazard_damage)
                player["status"]["burn_amplification"] = 0.1
            hazard_message = f"🔥❄️ **EXTREME CLIMATE!** The harsh environment deals `{hazard_damage}` damage and amplifies burn effects!"

        elif environment == "Fishman Island" and random.random() < 0.4:
            heal_amount = random.randint(10, 20)
            for player in players:
                player["hp"] = min(250, player["hp"] + heal_amount)
            hazard_message = f"🌊 **HEALING WATERS!** The sacred waters restore `{heal_amount}` HP to both players!"

        elif environment == "Dressrosa" and random.random() < 0.3:
            for player in players:
                player["status"]["crit_chance_boost"] = 0.1
                player["status"]["boost_turns"] = 3
            hazard_message = "✨ **COLOSSEUM SPIRIT!** The fighting spirit increases critical hit chance!"

        elif environment == "Whole Cake Island" and random.random() < 0.3:
            heal_amount = random.randint(15, 25)
            for player in players:
                player["hp"] = min(250, player["hp"] + heal_amount)
            hazard_message = f"🍰 **SWEET ENERGY!** The sugar rush heals both players for `{heal_amount}` HP!"

        elif environment == "Marineford" and random.random() < 0.3:
            for player in players:
                player["status"]["strong_damage_boost"] = 10
                player["status"]["boost_turns"] = 3
            hazard_message = "⚔️ **BATTLEFIELD FURY!** The historic grounds empower all attacks!"

        elif environment == "Enies Lobby" and random.random() < 0.3:
            for player in players:
                player["status"]["block_amplification"] = True
            hazard_message = "🛡️ **GATES OF JUSTICE!** Defense is enhanced for both players!"

        elif environment == "Amazon Lily" and random.random() < 0.3:
            heal_amount = random.randint(10, 15)
            for player in players:
                player["hp"] = min(250, player["hp"] + heal_amount)
            hazard_message = f"💖 **MAIDEN'S BLESSING!** The island's power heals both players for `{heal_amount}` HP!"

        elif environment == "Zou" and random.random() < 0.3:
            for player in players:
                player["status"]["elemental_boost"] = 0.1
            hazard_message = "🐘 **MINK TRIBE'S POWER!** The ancient power enhances elemental abilities!"

        elif environment == "Elbaf" and random.random() < 0.3:
            for player in players:
                player["status"]["physical_damage_boost"] = 15
                player["status"]["boost_turns"] = 3
            hazard_message = "🔨 **GIANT'S STRENGTH!** Physical attacks are greatly enhanced!"

        elif environment == "Raftel" and random.random() < 0.3:
            for player in players:
                player["status"]["crit_chance_boost"] = 0.1
                player["status"]["burn_amplification"] = 0.1
                player["status"]["heal_boost"] = 10
            hazard_message = "🏝️ **LOST HISTORY!** The power of the ancient weapons enhances all abilities!"

        return hazard_message

    @commands.hybrid_command(name="db")
    async def deathbattle(self, ctx: commands.Context, opponent: discord.Member = None):
        """
        Start a One Piece deathmatch against another user with a bounty.
        """
        try:
            # Quick check if battle is already in progress
            if ctx.channel.id in self.active_channels:
                return await ctx.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")

            # Mark the channel as active immediately
            self.active_channels.add(ctx.channel.id)

            # Send an initial message to provide immediate feedback
            loading_msg = await ctx.send("⚔️ **Preparing for battle...**")

            try:
                # Sync data for the challenger in the background
                user_bounty = await self.sync_user_data(ctx.author)
                
                # If no opponent is provided, choose a random bounty holder
                if opponent is None:
                    await loading_msg.edit(content="🔍 **Finding a worthy opponent...**")
                    
                    # Use more efficient approach to finding opponents
                    valid_opponents = []
                    all_members = await self.config.all_members(ctx.guild)
                    
                    # Limit potential opponents to 20 to avoid checking too many
                    for member_id, data in list(all_members.items())[:20]:
                        try:
                            if int(member_id) == ctx.author.id or data.get("bounty", 0) <= 0:
                                continue
                                
                            member = ctx.guild.get_member(int(member_id))
                            if member and not member.bot:
                                valid_opponents.append(member)
                        except Exception:
                            continue

                    if not valid_opponents:
                        self.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ **There are no valid users with a bounty to challenge!**")
                        return

                    opponent = random.choice(valid_opponents)
                    opponent_bounty = await self.sync_user_data(opponent)
                else:
                    # Verify opponent exists and is valid
                    if opponent.bot:
                        self.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ You cannot challenge a bot to a deathmatch!")
                        return
                        
                    if opponent == ctx.author:
                        self.active_channels.remove(ctx.channel.id)
                        await loading_msg.edit(content="❌ You cannot challenge yourself to a deathmatch!")
                        return
                        
                    # Sync opponent's bounty
                    opponent_bounty = await self.sync_user_data(opponent)
                
                # Ensure both users have a valid bounty (after we have the data)
                if user_bounty <= 0:
                    self.active_channels.remove(ctx.channel.id)
                    await loading_msg.edit(content=f"❌ **{ctx.author.display_name}** needs to start their bounty journey first by typing `.startbounty`!")
                    return

                if opponent_bounty <= 0:
                    self.active_channels.remove(ctx.channel.id)
                    await loading_msg.edit(content=f"❌ **{opponent.display_name}** does not have a bounty to challenge!")
                    return
                
                # Delete the loading message before proceeding
                await loading_msg.delete()
                
                # Generate fight card in the background
                fight_card = await ctx.bot.loop.run_in_executor(
                    None, self.generate_fight_card, ctx.author, opponent
                )
                
                # Send the fight card and start the battle
                await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))
                await self.fight(ctx, ctx.author, opponent)
                
            except Exception as e:
                await ctx.send(f"❌ An error occurred during the battle: {str(e)}")
                self.log.error(f"Battle error: {str(e)}")
            finally:
                # Always clean up
                if ctx.channel.id in self.active_channels:
                    self.active_channels.remove(ctx.channel.id)

        except Exception as e:
            # Catch any unexpected errors
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")
            self.log.error(f"Deathbattle command error: {str(e)}")
            
            # Ensure channel is removed from active channels if an error occurs
            if ctx.channel.id in self.active_channels:
                self.active_channels.remove(ctx.channel.id)
        
    @commands.command(name="stopbattle")
    @commands.admin_or_permissions(administrator=True)
    async def stopbattle(self, ctx: commands.Context):
        """Stop an ongoing battle (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")

        if ctx.channel.id not in self.active_channels:
            return await ctx.send("❌ There is no ongoing battle in this channel.")
    
        # Mark the battle as stopped
        self.battle_stopped = True
        self.active_channels.remove(ctx.channel.id)
    
        # Choose a random reason for stopping the fight
        reasons = [
            "🚢 **The Marines have arrived!** Everyone retreats immediately! ⚓",
            "👁️ **Imu has erased this battle from history!** The fight never happened...",
            "💥 **A Buster Call has been activated!** The battlefield is destroyed! 🔥",
            "🕊️ **The Five Elders have intervened!** All fighters are forced to flee.",
            "🏴‍☠️ **Shanks stepped in!** He declares: *'This fight ends now.'*",
        ]
        reason = random.choice(reasons)
    
        # Send the message inside the async function
        await ctx.send(f"{reason}\n\n🏴‍☠️ **The battle has been forcibly ended.** No winner was declared!")

    async def fight(self, ctx, challenger, opponent):
        """Enhanced fight system with all manager integrations."""
        try:
            channel_id = ctx.channel.id
                
            # Check if channel is already in battle
            if self.battle_manager.is_channel_in_battle(channel_id):
                return await ctx.send("❌ A battle is already in progress in this channel!")

            # Initialize player data
            challenger_data = await self._initialize_player_data(challenger)
            opponent_data = await self._initialize_player_data(opponent)

            # Create battle state
            battle_state = await self.battle_manager.create_battle(
                channel_id,
                challenger_data,
                opponent_data
            )

            # Initialize environment
            environment = self.choose_environment()
            battle_state["environment"] = environment
            environment_data = ENVIRONMENTS[environment]

            # Clear any lingering effects from all managers
            self.status_manager.clear_all_effects(challenger_data)
            self.status_manager.clear_all_effects(opponent_data)
            self.environment_manager.clear_environment_effects()

            # Create initial battle embed
            embed = discord.Embed(
                title="⚔️ EPIC ONE PIECE BATTLE ⚔️",
                description=f"Battle begins in **{environment}**!\n*{environment_data['description']}*",
                color=discord.Color.blue()
            )

            # Initialize display
            def update_player_fields():
                embed.clear_fields()
                for player in [challenger_data, opponent_data]:
                    status = self.get_status_icons(player)
                    health = self.generate_health_bar(player["hp"])
                    fruit_text = f"\n<:MeraMera:1336888578705330318> *{player['fruit']}*" if player['fruit'] else ""
                    
                    embed.add_field(
                        name=f"🏴‍☠️ {player['name']}",
                        value=(
                            f"❤️ HP: {player['hp']}/250\n"
                            f"{health}\n"
                            f"✨ Status: {status}{fruit_text}"
                        ),
                        inline=True
                    )
                    
                    if player == challenger_data:
                        embed.add_field(name="⚔️", value="VS", inline=True)

            # Send initial battle state
            update_player_fields()
            message = await ctx.send(embed=embed)
            battle_log = await ctx.send("📜 **Battle Log:**")

            # Battle loop
            turn = 0
            players = [challenger_data, opponent_data]
            current_player = 0

            while all(p["hp"] > 0 for p in players) and not self.battle_stopped:
                turn += 1
                attacker = players[current_player]
                defender = players[1 - current_player]

                # Process environment effects first
                env_messages, env_effects = await self.environment_manager.apply_environment_effect(
                    environment, players, turn
                )
                
                if env_messages:
                    await battle_log.edit(content=f"{battle_log.content}\n{''.join(env_messages)}")

                # Process status effects
                status_messages, status_damage = await self.status_manager.process_effects(attacker)
                if status_damage > 0:
                    attacker["hp"] = max(0, attacker["hp"] - status_damage)
                    attacker["stats"]["damage_taken"] += status_damage
                
                if status_messages:
                    await battle_log.edit(content=f"{battle_log.content}\n{''.join(status_messages)}")

                # Check if attacker can move (status effects might prevent action)
                if self.status_manager.get_effect_duration(attacker, "stun") > 0 or \
                self.status_manager.get_effect_duration(attacker, "freeze") > 0:
                    await battle_log.edit(content=f"{battle_log.content}\n⚠️ **{attacker['name']}** is unable to move!")
                    
                else:
                    # Update cooldowns and get available moves
                    self.update_cooldowns(attacker)
                    available_moves = [move for move in MOVES if move["name"] not in attacker["moves_on_cooldown"]]
                    if not available_moves:
                        available_moves = [move for move in MOVES if move["type"] == "regular"]

                    # Select move and apply environment modifications
                    selected_move = random.choice(available_moves)
                    modified_move, env_move_messages = await self.environment_manager.calculate_environment_modifiers(
                        environment, selected_move
                    )

                    # Calculate base damage
                    base_damage, damage_message = self.calculate_damage(modified_move, attacker, turn)

                    # Process Devil Fruit effects
                    devil_fruit_bonus, fruit_message = await self.devil_fruit_manager.process_devil_fruit_effect(
                        attacker, defender, modified_move, environment
                    )
                    
                    # Calculate final damage with all effects
                    final_damage, effect_messages = await self.status_manager.calculate_damage_with_effects(
                        base_damage + devil_fruit_bonus, attacker, defender
                    )

                    # Apply final damage
                    if final_damage > 0:
                        defender["hp"] = max(0, defender["hp"] - final_damage)
                        defender["stats"]["damage_taken"] += final_damage
                        attacker["stats"]["damage_dealt"] += final_damage

                    # Apply move effects through status manager
                    if "effect" in modified_move:
                        effect_result = await self.status_manager.apply_effect(
                            modified_move["effect"],
                            defender,
                            value=modified_move.get("effect_value", 1),
                            duration=modified_move.get("effect_duration", 1)
                        )
                        if effect_result:
                            effect_messages.append(effect_result)

                turn_message = [
                    f"\n➤ Turn {turn}: **{attacker['name']}** used **{modified_move['name']}**!"  # Move announcement
                ]

                # Add effects on separate lines
                if damage_message:
                    turn_message.append(f"• {damage_message}")
                if env_move_messages:
                    turn_message.extend(f"• {msg}" for msg in env_move_messages)
                if fruit_message:
                    turn_message.append(f"• {fruit_message}")
                if effect_messages:
                    turn_message.extend(f"• {msg}" for msg in effect_messages)

                # Add final damage as its own line
                turn_message.append(f"💥 Dealt **{final_damage}** damage!")

                # Join with newlines for better readability
                formatted_message = "\n".join(turn_message)

                # Update battle log
                await battle_log.edit(content=f"{battle_log.content}\n{formatted_message}")
                
                # Update display
                update_player_fields()
                await message.edit(embed=embed)

                # Add delay between turns
                await asyncio.sleep(2)

                # Switch turns
                current_player = 1 - current_player

                # Check if anyone is defeated
                if any(p["hp"] <= 0 for p in players):
                    break

            # After battle ends, determine winner
            if not self.battle_stopped:
                winner = next((p for p in players if p["hp"] > 0), players[0])
                loser = players[1] if winner == players[0] else players[0]

                # Create victory embed
                victory_embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{winner['name']}** is victorious!",
                    color=discord.Color.gold()
                )
                await message.edit(embed=victory_embed)

                # Process victory using the simplified processing method
                try:
                    # Get member objects
                    winner_member = winner["member"]
                    loser_member = loser["member"]
                    
                    # Simple reward calculations
                    bounty_increase = random.randint(1000, 3000)
                    bounty_decrease = random.randint(500, 1500)
                    
                    # Update winner
                    async with self.config.member(winner_member).all() as winner_data:
                        winner_current_bounty = int(winner_data.get("bounty", 0))
                        winner_new_bounty = winner_current_bounty + bounty_increase
                        winner_data["bounty"] = winner_new_bounty
                        winner_data["wins"] = winner_data.get("wins", 0) + 1

                    # Update loser
                    async with self.config.member(loser_member).all() as loser_data:
                        loser_current_bounty = int(loser_data.get("bounty", 0))
                        loser_new_bounty = max(0, loser_current_bounty - bounty_decrease)
                        loser_data["bounty"] = loser_new_bounty
                        loser_data["losses"] = loser_data.get("losses", 0) + 1

                    # Create reward embed
                    reward_embed = discord.Embed(
                        title="<:Beli:1237118142774247425> Battle Rewards",
                        color=discord.Color.gold()
                    )
                    
                    reward_embed.add_field(
                        name=f"Winner: {winner['name']}",
                        value=f"Gained {bounty_increase:,} Berries\nNew Bounty: {winner_new_bounty:,} Berries",
                        inline=False
                    )
                    
                    reward_embed.add_field(
                        name=f"Loser: {loser['name']}",
                        value=f"Lost {bounty_decrease:,} Berries\nNew Bounty: {loser_new_bounty:,} Berries",
                        inline=False
                    )
                    
                    await ctx.send(embed=reward_embed)

                    # Update activity timestamps
                    current_time = datetime.utcnow().isoformat()
                    await self.config.member(winner_member).last_active.set(current_time)
                    await self.config.member(loser_member).last_active.set(current_time)

                except Exception as e:
                    logger.error(f"Error processing victory rewards: {str(e)}")
                    await ctx.send("An error occurred while processing rewards.")

        except Exception as e:
            logger.error(f"Error in fight: {str(e)}")
            await ctx.send(f"An error occurred during the battle: {str(e)}")
        finally:
            # Clean up all managers
            await self.battle_manager.end_battle(channel_id)
            if ctx.channel.id in self.active_channels:
                self.active_channels.remove(ctx.channel.id)
            
    async def process_status_effects(self, attacker, defender):
        """Process all status effects and return effect messages."""
        status_messages = []
        
        # Process burn damage
        if attacker["status"]["burn"] > 0:
            burn_damage = 5 * attacker["status"]["burn"]
            attacker["hp"] = max(0, attacker["hp"] - burn_damage)
            attacker["status"]["burn"] = max(0, attacker["status"]["burn"] - 1)
            status_messages.append(f"🔥 **{attacker['name']}** takes `{burn_damage}` burn damage!")

        # Process frozen status
        if attacker["status"]["frozen"] > 0:
            attacker["status"]["frozen"] -= 1
            if attacker["status"]["frozen"] > 0:
                status_messages.append(f"❄️ **{attacker['name']}** is frozen and cannot move!")
                return "\n".join(status_messages)

        # Process stun
        if attacker["status"]["stun"]:
            attacker["status"]["stun"] = False
            status_messages.append(f"⚡ **{attacker['name']}** is stunned and loses their turn!")
            return "\n".join(status_messages)

        # Process transformation
        if attacker["status"]["transformed"] > 0:
            attacker["status"]["transformed"] -= 1
            if attacker["status"]["transformed"] > 0:
                status_messages.append(f"✨ **{attacker['name']}**'s transformation boosts their power!")

        # Process protection
        if attacker["status"]["protected"]:
            attacker["status"]["protected"] = False
            status_messages.append(f"🛡️ **{attacker['name']}**'s barrier fades away.")

        # Process accuracy reduction
        if attacker["status"]["accuracy_turns"] > 0:
            attacker["status"]["accuracy_turns"] -= 1
            if attacker["status"]["accuracy_turns"] == 0:
                attacker["status"]["accuracy_reduction"] = 0
                status_messages.append(f"👁️ **{attacker['name']}**'s accuracy returns to normal!")
            else:
                status_messages.append(f"🌫️ **{attacker['name']}**'s accuracy is still reduced!")

        return "\n".join(status_messages) if status_messages else None

    async def _handle_battle_rewards(self, ctx, winner, loser):
        """Handle post-battle rewards with thread safety."""
        try:
            async with self.battle_lock:
                # Calculate rewards
                bounty_increase = random.randint(1000, 3000)
                bounty_decrease = random.randint(500, 1500)
                
                # Update winner's bounty
                new_winner_bounty = await self.safe_modify_bounty(winner["member"], bounty_increase, "add")
                if new_winner_bounty is None:
                    await ctx.send("⚠️ Failed to update winner's bounty!")
                    return
                
                # Update loser's bounty
                new_loser_bounty = await self.safe_modify_bounty(loser["member"], bounty_decrease, "subtract")
                if new_loser_bounty is None:
                    await ctx.send("⚠️ Failed to update loser's bounty!")
                    return
                
                # Update stats
                async with self.data_lock:
                    await self.config.member(winner["member"]).wins.set(
                        await self.config.member(winner["member"]).wins() + 1
                    )
                    await self.config.member(loser["member"]).losses.set(
                        await self.config.member(loser["member"]).losses() + 1
                    )
                
                # Create and send results embed
                embed = discord.Embed(
                    title="🏆 Battle Results",
                    color=discord.Color.gold()
                )
                
                embed.add_field(
                    name="Winner",
                    value=(
                        f"**{winner['name']}**\n"
                        f"+ `{bounty_increase:,}` Berries\n"
                        f"New Bounty: `{new_winner_bounty:,}` Berries"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="Loser",
                    value=(
                        f"**{loser['name']}**\n"
                        f"- `{bounty_decrease:,}` Berries\n"
                        f"New Bounty: `{new_loser_bounty:,}` Berries"
                    ),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                
                # Update last active time
                current_time = datetime.utcnow().isoformat()
                async with self.data_lock:
                    await self.config.member(winner["member"]).last_active.set(current_time)
                    await self.config.member(loser["member"]).last_active.set(current_time)
                
        except Exception as e:
            logger.error(f"Error in battle rewards: {str(e)}")
            await ctx.send("❌ An error occurred while processing battle rewards.")
            
    async def _unlock_achievement(self, member, achievement_name):
        """Unlock a specific achievement for a member."""
        try:
            if achievement_name not in ACHIEVEMENTS:
                return

            current_achievements = await self.config.member(member).achievements()
            if achievement_name not in current_achievements:
                current_achievements.append(achievement_name)
                await self.config.member(member).achievements.set(current_achievements)
                
                achievement_data = ACHIEVEMENTS[achievement_name]
                await self.config.member(member).titles.set(
                    await self.config.member(member).titles() + [achievement_data["title"]]
                )
                
                # Create achievement unlock announcement
                embed = discord.Embed(
                    title="🎉 Achievement Unlocked!",
                    description=f"**{member.display_name}** has unlocked: `{achievement_data['description']}`",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Title Earned",
                    value=f"`{achievement_data['title']}`",
                    inline=False
                )
                
                # Send to the channel where the achievement was earned
                if member.guild:
                    channel = discord.utils.get(member.guild.text_channels, name="achievements")
                    if channel:
                        await channel.send(embed=embed)
                        
        except Exception as e:
            logger.error(f"Error unlocking achievement: {str(e)}")
    
    async def apply_devil_fruit_effects(self, attacker, defender, damage, move, turn_number=1):
        """Apply Devil Fruit effects using the Devil Fruit manager."""
        try:
            # Ensure attacker has a fruit
            fruit = attacker.get("fruit")
            if not fruit:
                return 0, None

            # Process the effect through our manager
            bonus_damage, effect_message = await self.devil_fruit_manager.process_devil_fruit_effect(
                attacker,
                defender,
                move,
                self.current_environment
            )

            # Track usage for achievements
            if "elements_used" not in attacker:
                attacker["elements_used"] = set()
                
            # Get fruit type from data
            fruit_data = DEVIL_FRUITS["Common"].get(fruit) or DEVIL_FRUITS["Rare"].get(fruit)
            if fruit_data:
                attacker["elements_used"].add(fruit_data["type"])

            return bonus_damage, effect_message

        except Exception as e:
            logger.error(f"Error in apply_devil_fruit_effects: {str(e)}")
            return 0, None
    
    @commands.group(name="deathboard", invoke_without_command=True)
    async def deathboard(self, ctx: commands.Context):
        """
        Show the leaderboard for the deathmatch game.
        Use `.deathboard wins` to view the top players by wins.
        Use `.deathboard kdr` to view the top players by Kill/Death Ratio (KDR).
        """
        embed = discord.Embed(
            title="Deathboard Help",
            description=(
                "Use one of the following subcommands to view rankings:\n"
                "- **`wins`**: Show the top players by wins.\n"
                "- **`kdr`**: Show the top players by Kill/Death Ratio (KDR).\n"
            ),
            color=0x00FF00,
        )
        await ctx.send(embed=embed)

    @deathboard.command(name="wins")
    async def deathboard_wins(self, ctx: commands.Context):
        """Show the top 10 players by wins."""
        all_members = await self.config.all_members(ctx.guild)
        
        # Filter out members with 0 wins and sort by wins
        valid_members = []
        for member_id, data in all_members.items():
            wins = data.get("wins", 0)
            if wins > 0:
                member = ctx.guild.get_member(int(member_id))
                if member:
                    valid_members.append((member, wins, data.get("losses", 0)))
        
        # Sort by wins in descending order
        sorted_by_wins = sorted(valid_members, key=lambda x: x[1], reverse=True)
        
        if not sorted_by_wins:
            return await ctx.send("No players with wins found!")
        
        embed = discord.Embed(
            title="🏆 Top 10 Players by Wins 🏆",
            color=0xFFD700,
        )
        
        # Use explicit loop with proper indexing
        for i in range(min(10, len(sorted_by_wins))):
            member, wins, losses = sorted_by_wins[i]
            # Use i+1 to ensure we start at 1, not 0
            embed.add_field(
                name=f"{i+1}. {member.display_name}",
                value=f"Wins: {wins}\nLosses: {losses}",
                inline=False,
            )
        
        await ctx.send(embed=embed)

    @deathboard.command(name="kdr")
    async def deathboard_kdr(self, ctx: commands.Context):
        """Show the top 10 players by Kill/Death Ratio (KDR)."""
        all_members = await self.config.all_members(ctx.guild)
        
        # Calculate KDR for players with battles
        kdr_list = []
        for member_id, data in all_members.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            
            # Only include players who have participated in battles
            if wins > 0 or losses > 0:
                kdr = wins / losses if losses > 0 else wins  # Avoid division by zero
                member = ctx.guild.get_member(int(member_id))
                if member:
                    kdr_list.append((member, kdr, wins, losses))
        
        # Sort by KDR
        sorted_by_kdr = sorted(kdr_list, key=lambda x: x[1], reverse=True)
        
        if not sorted_by_kdr:
            return await ctx.send("No players with KDR found!")
        
        embed = discord.Embed(
            title="🏅 Top 10 Players by KDR 🏅",
            color=0x00FF00,
        )
        
        # Use explicit loop with proper indexing
        for i in range(min(10, len(sorted_by_kdr))):
            member, kdr, wins, losses = sorted_by_kdr[i]
            # Use i+1 to ensure we start at 1, not 0
            embed.add_field(
                name=f"{i+1}. {member.display_name}",
                value=f"KDR: {kdr:.2f}\nWins: {wins}\nLosses: {losses}",
                inline=False,
            )
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def resetstats(self, ctx, member: discord.Member = None):
        """Reset all users' stats (Admin/Owner only)."""
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
    
        if member is None:  # ✅ Default to full server reset if no user is mentioned
            await ctx.send("⚠️ **Are you sure you want to reset ALL players' stats?** Type `confirm` to proceed.")
    
            def check(m):
                return m.author == ctx.author and m.content.lower() == "confirm"
    
            try:
                await self.bot.wait_for("message", check=check, timeout=15)
            except asyncio.TimeoutError:
                return await ctx.send("❌ **Global reset cancelled.**")
    
            all_members = await self.config.all_members(ctx.guild)
            for user_id in all_members:
                user = ctx.guild.get_member(int(user_id))  # ✅ Get the actual Discord member object
                if user:
                    await self.config.member(user).clear()
    
            # ✅ Reset the server-wide bounty list to 0
            await self.config.guild(ctx.guild).bounties.set({})
            
            await ctx.send("🔄 **All player stats, bounties, and titles have been reset!**")
            return
    
        # ✅ Reset a Single User
        await self.config.member(member).clear()
    
        # ✅ Reset the user's bounty inside the `mostwanted` bounty list
        bounties = await self.config.guild(ctx.guild).bounties()
        if str(member.id) in bounties:
            bounties[str(member.id)]["amount"] = 0  # Set bounty to 0
            await self.config.guild(ctx.guild).bounties.set(bounties)  # Save changes
    
        await ctx.send(f"🔄 **{member.display_name}'s stats, bounty, and titles have been reset!**")
        
    @commands.command()
    async def titles(self, ctx, action: str = None, *, title: str = None):
        """View or equip titles."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking titles.")

        # Get all titles based on bounty level
        bounty_titles = []
        for t, req in TITLES.items():
            if true_bounty >= req["bounty"]:
                bounty_titles.append(t)
                
        # Get achievement/special titles
        custom_titles = await self.config.member(user).titles()
        
        # Check for hidden titles
        hidden_titles = await self.check_hidden_titles(user)
        
        # Combine all titles
        all_titles = sorted(set(bounty_titles + custom_titles + hidden_titles))
        current_title = await self.config.member(user).current_title()

        if action == "equip" and title:
            # Call equiptitle command for consistent behavior
            await ctx.invoke(self.equiptitle, title=title)
            return

        embed = discord.Embed(title=f"🏆 {user.display_name}'s Titles", color=discord.Color.gold())
        
        if all_titles:
            embed.add_field(
                name="Unlocked Titles", 
                value="\n".join(f"• {t}" for t in all_titles) or "None", 
                inline=False
            )
        else:
            embed.add_field(
                name="Unlocked Titles", 
                value="None yet! Increase your bounty to unlock titles.", 
                inline=False
            )
            
        embed.add_field(
            name="Current Title", 
            value=f"`{current_title}`" if current_title else "None equipped", 
            inline=False
        )
        
        # Add instructions
        embed.add_field(
            name="How to Equip", 
            value="Use `.equiptitle \"Title Name\"` to equip a title", 
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    @commands.command(name="equiptitle")
    async def equiptitle(self, ctx: commands.Context, *, title: str):
        """Equip a title for yourself."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking titles.")

        # Get all available titles (bounty-based, achievement-based, and hidden)
        bounty_titles = {t for t, c in TITLES.items() if true_bounty >= c["bounty"]}
        custom_titles = await self.config.member(user).titles()
        hidden_titles = await self.check_hidden_titles(user)
        
        # Combine all available titles
        all_available_titles = list(bounty_titles) + custom_titles + hidden_titles
        
        # Normalize input title and available titles for comparison
        title_lower = title.lower().strip()
        
        # Try exact match first
        exact_match = next((t for t in all_available_titles if t.lower() == title_lower), None)
        if exact_match:
            await self.config.member(user).current_title.set(exact_match)
            return await ctx.send(f"✅ You have equipped the title `{exact_match}`!")
        
        # Try partial match if exact match fails
        partial_matches = [t for t in all_available_titles if title_lower in t.lower()]
        
        if not partial_matches:
            # Try to find the closest match for better feedback
            if all_available_titles:
                closest = difflib.get_close_matches(title, all_available_titles, n=1)
                suggestion = f" Did you mean `{closest[0]}`?" if closest else ""
                await ctx.send(f"❌ You have not unlocked the title `{title}`.{suggestion}")
            else:
                await ctx.send(f"❌ You have not unlocked any titles yet. Increase your bounty to unlock titles!")
            return
        
        if len(partial_matches) == 1:
            # Single partial match found
            matched_title = partial_matches[0]
            await self.config.member(user).current_title.set(matched_title)
            return await ctx.send(f"✅ You have equipped the title `{matched_title}`!")
        else:
            # Multiple matches found - ask user to be more specific
            embed = discord.Embed(
                title="🎖️ Multiple Matching Titles Found",
                description="Please be more specific. Did you mean one of these?",
                color=discord.Color.gold()
            )
            for i, t in enumerate(partial_matches[:10], 1):  # Limit to first 10 to avoid too large embeds
                embed.add_field(name=f"{i}. {t}", value=f"Use `.equiptitle \"{t}\"` to equip", inline=False)
            
            await ctx.send(embed=embed)
            
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def granttitle(self, ctx, member: discord.Member, *, title: str):
        """Grant a title to a user (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        # Ensure the user has a bounty entry
        await self.sync_user_data(member)
        
        # Get current titles
        current_titles = await self.config.member(member).titles()
        
        # Check if they already have this title
        if title in current_titles:
            return await ctx.send(f"⚠️ {member.display_name} already has the title `{title}`!")
        
        # Add the new title
        current_titles.append(title)
        await self.config.member(member).titles.set(current_titles)
        
        # Create response embed
        embed = discord.Embed(
            title="🏆 Title Granted",
            description=f"Granted the title `{title}` to **{member.display_name}**!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="All Titles",
            value="\n".join([f"• {t}" for t in current_titles]),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # DM the user
        try:
            user_embed = discord.Embed(
                title="🎖️ New Title Awarded!",
                description=f"You have been granted the title `{title}`!",
                color=discord.Color.gold()
            )
            user_embed.add_field(
                name="How to Equip",
                value=f"Use `.equiptitle \"{title}\"` to equip your new title!",
                inline=False
            )
            await member.send(embed=user_embed)
        except discord.Forbidden:
            # User might have DMs disabled
            pass

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def debugtitles(self, ctx, member: discord.Member = None):
        """Debug a user's titles (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        member = member or ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(member)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking titles.")
        
        # Get all possible titles from all sources
        bounty_titles = []
        for title, req in TITLES.items():
            if true_bounty >= req["bounty"]:
                bounty_titles.append((title, req["bounty"]))
                
        custom_titles = await self.config.member(member).titles()
        hidden_titles = await self.check_hidden_titles(member)
        current_title = await self.config.member(member).current_title()
        
        # Create detailed debug embed
        embed = discord.Embed(
            title=f"🔍 Title Debug for {member.display_name}",
            description=f"Current Bounty: `{true_bounty:,}` Berries",
            color=discord.Color.blue()
        )
        
        # Show all bounty-based titles with their requirements
        embed.add_field(
            name="Bounty-Based Titles",
            value="\n".join([f"• {title} (Req: {req:,})" for title, req in bounty_titles]) or "None",
            inline=False
        )
        
        # Show achievement/custom titles
        embed.add_field(
            name="Achievement Titles",
            value="\n".join([f"• {title}" for title in custom_titles]) or "None",
            inline=False
        )
        
        # Show hidden titles
        embed.add_field(
            name="Hidden Titles",
            value="\n".join([f"• {title}" for title in hidden_titles]) or "None",
            inline=False
        )
        
        # Show current equipped title
        embed.add_field(
            name="Current Title",
            value=f"`{current_title}`" if current_title else "None equipped",
            inline=False
        )
        
        # Show title from get_bounty_title function
        computed_title = self.get_bounty_title(true_bounty)
        embed.add_field(
            name="Computed Default Title",
            value=f"`{computed_title}`",
            inline=False
        )
        
        # Show all available titles
        all_titles = bounty_titles + [(t, "achievement") for t in custom_titles] + [(t, "hidden") for t in hidden_titles]
        if all_titles:
            embed.add_field(
                name="All Available Titles",
                value="\n".join([f"• {title}" for title, _ in all_titles]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def deathstats(self, ctx, member: discord.Member = None):
        """Check a player's deathmatch stats."""
        member = member or ctx.author
        
        try:
            # Sync data first
            true_bounty = await self.sync_user_data(member)
            if true_bounty is None:
                return await ctx.send("❌ An error occurred while checking stats.")

            # Get comprehensive stats
            stats = await self.config.member(member).all()
            wins = stats.get("wins", 0)
            losses = stats.get("losses", 0)
            kdr = wins / losses if losses > 0 else wins if wins > 0 else 0.0
            damage_dealt = stats.get("damage_dealt", 0)
            damage_taken = stats.get("damage_taken", 0)
            critical_hits = stats.get("critical_hits", 0)
            
            # Get titles and achievements
            titles = stats.get("titles", [])
            current_title = stats.get("current_title") or self.get_bounty_title(true_bounty)
            achievements = stats.get("achievements", [])

            # Create detailed embed
            embed = discord.Embed(
                title=f"⚔️ Battle Statistics for {member.display_name}",
                color=discord.Color.blue()
            )

            # Combat Stats
            embed.add_field(
                name="Combat Record",
                value=(
                    f"🏆 Wins: `{wins}`\n"
                    f"💀 Losses: `{losses}`\n"
                    f"📊 K/D Ratio: `{kdr:.2f}`"
                ),
                inline=False
            )

            # Damage Stats
            embed.add_field(
                name="Damage Statistics",
                value=(
                    f"⚔️ Damage Dealt: `{damage_dealt:,}`\n"
                    f"🛡️ Damage Taken: `{damage_taken:,}`\n"
                    f"💥 Critical Hits: `{critical_hits}`"
                ),
                inline=False
            )

            # Bounty and Titles
            embed.add_field(
                name="Bounty & Titles",
                value=(
                    f"<:Beli:1237118142774247425> Current Bounty: `{true_bounty:,}` Berries\n"
                    f"👑 Current Title: `{current_title}`"
                ),
                inline=False
            )

            # Special Titles
            if titles:
                embed.add_field(
                    name="🎖️ Special Titles Earned",
                    value="\n".join(f"• `{title}`" for title in titles),
                    inline=False
                )

            # Achievements
            if achievements:
                achieved = []
                for ach in achievements:
                    if ach in ACHIEVEMENTS:
                        achieved.append(f"• {ACHIEVEMENTS[ach]['description']}")
                if achieved:
                    embed.add_field(
                        name="🏆 Achievements Unlocked",
                        value="\n".join(achieved),
                        inline=False
                    )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in deathstats command: {str(e)}")
            await ctx.send("❌ An error occurred while retrieving battle statistics!")

    async def update_winner(self, ctx, winner):
        """Update bounty and stats for the winner."""
        bounty_reward = random.randint(1000, 5000)
        winner_id = str(winner.id)

        bounties = await self.config.guild(ctx.guild).bounties()
        bounties[winner_id] = bounties.get(winner_id, {"amount": 0})
        bounties[winner_id]["amount"] += bounty_reward

        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(winner).bounty.set(bounties[winner_id]["amount"])
        await self.config.member(winner).wins.set(await self.config.member(winner).wins() + 1)

        await ctx.send(f"🏆 **{winner.display_name}** won and earned `{bounty_reward}` Berries! Their bounty is now `{bounties[winner_id]['amount']}`!")

    # ------------------ Achievements System ------------------

    @commands.command()
    async def achievements(self, ctx):
        """Show your unlocked achievements."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking achievements.")

        achievements = await self.config.member(user).achievements()
        if not achievements:
            return await ctx.send("Ye have no achievements yet! Win battles and increase yer bounty!")

        embed = discord.Embed(
            title=f"🏆 {user.display_name}'s Achievements",
            color=discord.Color.green()
        )
        for achievement in achievements:
            if achievement in ACHIEVEMENTS:
                embed.add_field(
                    name=ACHIEVEMENTS[achievement]["description"],
                    value=f"🎖️ Title Earned: `{ACHIEVEMENTS[achievement]['title']}`",
                    inline=False
                )

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            retry_seconds = int(error.retry_after)
            time_left = f"{retry_seconds // 3600} hours" if retry_seconds >= 3600 else f"{retry_seconds // 60} minutes"
    
            # ✅ Suppresses default Redbot cooldown message
            error.handled = True  
            await ctx.send(f"⏳ This command is on cooldown. Try again in **{time_left}**.")

# ------------------ Setup Function ------------------
async def setup(bot):
    cog = BountyBattle(bot)
    await bot.add_cog(cog)
