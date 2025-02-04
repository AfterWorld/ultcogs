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
        "Gomu Gomu no Mi": {"type": "Paramecia", "effect": "rubber", "bonus": "Immune to blunt attacks"},
        "Mera Mera no Mi": {"type": "Logia", "effect": "fire", "bonus": "Fire attacks do double damage"},
        "Ope Ope no Mi": {"type": "Paramecia", "effect": "surgical", "bonus": "Can switch places once per battle"},
        "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "20% chance to stun opponent with lightning"},
        "Bomu Bomu no Mi": {"type": "Paramecia", "effect": "explosion", "bonus": "Explosive attacks deal 30% extra damage"},
        "Moku Moku no Mi": {"type": "Logia", "effect": "smoke", "bonus": "15% chance to dodge physical attacks"},
        "Suna Suna no Mi": {"type": "Logia", "effect": "sand", "bonus": "10% chance to drain enemy’s HP"},
        "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "20% increased speed and agility"},
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
        "Kage Kage no Mi": {"type": "Paramecia", "effect": "shadows", "bonus": "Can steal an enemy's shadow to weaken them"},
        "Shari Shari no Mi": {"type": "Paramecia", "effect": "wheels", "bonus": "Can turn limbs into spinning wheels for attacks"},
        "Awa Awa no Mi": {"type": "Paramecia", "effect": "bubbles", "bonus": "Reduces enemy defense with cleansing bubbles"},
        "Sabi Sabi no Mi": {"type": "Paramecia", "effect": "rust", "bonus": "Can corrode enemy weapons and armor"},
        "Noro Noro no Mi": {"type": "Paramecia", "effect": "slow beam", "bonus": "Temporarily slows down enemies"},
        "Doa Doa no Mi": {"type": "Paramecia", "effect": "doors", "bonus": "Can teleport short distances"},
        "Beri Beri no Mi": {"type": "Paramecia", "effect": "barrier balls", "bonus": "Body can split into bouncing balls to evade attacks"},
        "Yomi Yomi no Mi": {"type": "Paramecia", "effect": "revival", "bonus": "Can revive once upon defeat with 30% HP"},
        "Horo Horo no Mi": {"type": "Paramecia", "effect": "ghosts", "bonus": "Summons negative ghosts to weaken enemies"},
        "Jake Jake no Mi": {"type": "Paramecia", "effect": "jacket", "bonus": "Can possess an ally and control their attacks"},
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
	    "Hobi Hobi no Mi": {"type": "Paramecia", "effect": "toy", "bonus": "Temporarily disables an enemy's attack"},
    },
    "Rare": {
        "Yami Yami no Mi": {"type": "Logia", "effect": "darkness", "bonus": "Can absorb 15% of the opponent's attack damage as HP"},
        "Mochi Mochi no Mi": {"type": "Special Paramecia", "effect": "mochi", "bonus": "Can dodge one attack every 4 turns"},
        "Hie Hie no Mi": {"type": "Logia", "effect": "ice", "bonus": "Can freeze an opponent, skipping their next turn"},
        "Tatsu Tatsu no Mi: Model Azure Dragon": {"type": "Mythical Zoan", "effect": "dragon", "bonus": "25% resistance to elemental attacks"},
        "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "20% chance to stun an enemy every turn"},
        "Kami Kami no Mi": {"type": "Mythical Zoan", "effect": "god", "bonus": "Chance to nullify damage once per match"},
        "Ryu Ryu no Mi: Model Spinosaurus": {"type": "Ancient Zoan", "effect": "spinosaurus", "bonus": "Increase HP by 20%"},
        "Ryu Ryu no Mi: Model Pteranodon": {"type": "Ancient Zoan", "effect": "pteranodon", "bonus": "Gain a 15% chance to evade attacks"},
        "Inu Inu no Mi: Model Okuchi no Makami": {"type": "Mythical Zoan", "effect": "wolf deity", "bonus": "Healing abilities are doubled"},
        "Kumo Kumo no Mi: Model Rosamygale Grauvogeli": {"type": "Ancient Zoan", "effect": "spider", "bonus": "Web attacks slow enemies, reducing their speed"},
        "Toki Toki no Mi": {"type": "Paramecia", "effect": "time", "bonus": "Can speed up cooldowns for abilities"},
        "Bari Bari no Mi": {"type": "Paramecia", "effect": "barrier", "bonus": "Block 40% of incoming melee damage"},
        "Doku Doku no Mi": {"type": "Paramecia", "effect": "poison", "bonus": "Deals poison damage over time"},
        "Ushi Ushi no Mi: Model Bison": {"type": "Zoan", "effect": "bison", "bonus": "Attack power increases the longer the battle lasts"},
        "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Heals 10% HP every 3 turns"},
        "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "dragon", "bonus": "30% stronger attacks in battles"},
        "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "nika", "bonus": "Randomly boosts attack, speed, or defense"},
        "Gura Gura no Mi": {"type": "Paramecia", "effect": "quake", "bonus": "Earthquake attack deals massive AoE damage"},
        "Pika Pika no Mi": {"type": "Logia", "effect": "light", "bonus": "Moves first in every battle"},
        "Magu Magu no Mi": {"type": "Logia", "effect": "magma", "bonus": "Deals additional burn damage over time"},
        "Shibo Shibo no Mi": {"type": "Paramecia", "effect": "dehydration", "bonus": "Can drain water from an opponent to weaken them"},
        "Kira Kira no Mi": {"type": "Paramecia", "effect": "diamond", "bonus": "Defense increases by 30%"},
        "Ishi Ishi no Mi": {"type": "Paramecia", "effect": "stone", "bonus": "Can manipulate the battlefield by moving rocks"},
        "Ryu Ryu no Mi: Model Allosaurus": {"type": "Ancient Zoan", "effect": "allosaurus", "bonus": "Increase attack damage by 25%"},
        "Inu Inu no Mi: Model Cerberus": {"type": "Mythical Zoan", "effect": "three-headed dog", "bonus": "Can attack twice per turn"},
        "Mori Mori no Mi": {"type": "Logia", "effect": "forest", "bonus": "Can summon roots to immobilize opponents"},
        "Kaze Kaze no Mi": {"type": "Logia", "effect": "wind", "bonus": "Has a 20% chance to dodge any attack"},
        "Tori Tori no Mi: Model Thunderbird": {"type": "Mythical Zoan", "effect": "thunderbird", "bonus": "Lightning attacks deal extra damage"},
        "Hito Hito no Mi: Model Daibutsu": {"type": "Mythical Zoan", "effect": "giant buddha", "bonus": "Boosts defense and attack power"},
	    "Hito Hito no Mi: Model Human": {"type": "Mythical Zoan", "effect": "Pro Poker Player", "bonus": "Player becomes the worlds best Poker Player"},
        "Hebi Hebi no Mi: Model Yamata no Orochi": {"type": "Mythical Zoan", "effect": "eight-headed snake", "bonus": "Gain 2 extra attacks every 3 turns"},
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
            "Yami Yami no Mi": 5,      # Darkness abilities
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
        """Handle Logia-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None

        # Mera Mera no Mi
        if effect == "fire":
            if random.random() < 0.4:
                await self.status_manager.apply_effect("burn", defender, value=2)
                bonus_damage = int(move.get("damage", 0) * 1.0)  # Double damage
                effect_message = (
                    f"🔥 **FLAME EMPEROR**! 🔥\n"
                    f"**{attacker['name']}** unleashes an inferno!\n"
                    f"💥 Double damage + Intense burn!"
                )

        # Goro Goro no Mi
        elif effect == "lightning":
            if random.random() < 0.2:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.5)
                effect_message = (
                    f"⚡ **THUNDER GOD**! ⚡\n"
                    f"**{attacker['name']}** channels lightning!\n"
                    f"💫 Stun effect + Bonus damage!"
                )

        # Moku Moku no Mi
        elif effect == "smoke":
            if random.random() < 0.15:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                effect_message = (
                    f"💨 **WHITE LAUNCHER**! 💨\n"
                    f"**{attacker['name']}** becomes smoke!\n"
                    f"✨ Gained evasion boost!"
                )

        # Suna Suna no Mi
        elif effect == "sand":
            if random.random() < 0.10:
                drain_amount = int(defender["hp"] * 0.1)
                defender["hp"] -= drain_amount
                attacker["hp"] = min(250, attacker["hp"] + drain_amount)
                effect_message = (
                    f"🏜️ **GROUND DEATH**! 🏜️\n"
                    f"**{attacker['name']}** drains life force!\n"
                    f"💀 Drained {drain_amount} HP!"
                )

        # Hie Hie no Mi
        elif effect == "ice":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.3)
                effect_message = (
                    f"❄️ **ICE AGE**! ❄️\n"
                    f"**{attacker['name']}** freezes the battlefield!\n"
                    f"🥶 Target frozen + Bonus damage!"
                )

        # Yami Yami no Mi
        elif effect == "darkness":
            absorb_amount = int(move.get("damage", 0) * 0.15)
            attacker["hp"] = min(250, attacker["hp"] + absorb_amount)
            bonus_damage = int(move.get("damage", 0) * 0.3)
            effect_message = (
                f"🌑 **BLACK HOLE**! 🌑\n"
                f"**{attacker['name']}** commands darkness!\n"
                f"⚫ Absorbed {absorb_amount} HP + Bonus damage!"
            )

        # Pika Pika no Mi
        elif effect == "light":
            bonus_damage = int(move.get("damage", 0) * 0.4)
            if random.random() < 0.2:
                bonus_damage *= 2
                effect_message = (
                    f"✨ **SACRED YASAKANI**! ✨\n"
                    f"**{attacker['name']}** attacks at light speed!\n"
                    f"⚡ Double damage + Defense pierce!"
                )

        # Magu Magu no Mi
        elif effect == "magma":
            await self.status_manager.apply_effect("burn", defender, value=3)
            bonus_damage = int(move.get("damage", 0) * 0.6)
            effect_message = (
                f"🌋 **GREAT ERUPTION**! 🌋\n"
                f"**{attacker['name']}** unleashes magma!\n"
                f"🔥 Maximum burn + Heavy damage!"
            )

        # Mori Mori no Mi
        elif effect == "forest":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("root", defender, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.2)
                effect_message = (
                    f"🌳 **FOREST PRISON**! 🌳\n"
                    f"**{attacker['name']}** binds with roots!\n"
                    f"🌿 Target rooted + Bonus damage!"
                )

        # Kaze Kaze no Mi
        elif effect == "wind":
            if random.random() < 0.20:
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.3)
                effect_message = (
                    f"🌪️ **DIVINE WIND**! 🌪️\n"
                    f"**{attacker['name']}** harnesses the wind!\n"
                    f"💨 Evasion boost + Bonus damage!"
                )

        # Environment interactions
        if environment == "Punk Hazard" and effect in ["fire", "ice", "magma"]:
            bonus_damage = int(bonus_damage * 1.5)
            effect_message = f"{effect_message}\n🌋 Power amplified by Punk Hazard's climate!"
        elif environment == "Alabasta" and effect == "sand":
            bonus_damage = int(bonus_damage * 1.3)
            effect_message = f"{effect_message}\n🏜️ Desert environment enhances sand powers!"
        elif environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            effect_message = f"{effect_message}\n⚔️ Sacred battleground amplifies power!"

        return bonus_damage, effect_message

    async def _handle_zoan_effects(self, attacker, defender, effect, move, environment):
        """Handle Zoan-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None

        # Leopard Zoan (Neko Neko no Mi: Model Leopard)
        if effect == "leopard":
            if random.random() < 0.2:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.2)
                effect_message = (
                    f"🐆 **PREDATOR'S AGILITY**! 🐆\n"
                    f"**{attacker['name']}** moves with feline grace!\n"
                    f"⚡ Speed increased + Bonus damage!"
                )

        # Azure Dragon Zoan (Tatsu Tatsu no Mi: Model Azure Dragon)
        elif "Azure Dragon" in effect:
            if random.random() < 0.25:
                bonus_damage = int(move.get("damage", 0) * 0.3)
                await self.status_manager.apply_effect("elemental_resist", attacker, duration=2)
                effect_message = (
                    f"🐉 **CELESTIAL DRAGON'S MIGHT**! 🐉\n"
                    f"**{attacker['name']}** channels divine power!\n"
                    f"✨ Elemental resistance + Enhanced damage!"
                )

        # Phoenix Zoan (Tori Tori no Mi: Model Phoenix)
        elif "Phoenix" in effect:
            if random.random() < 0.3:
                heal_amount = int(attacker["hp"] * 0.1)
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                effect_message = (
                    f"🦅 **FLAMES OF RESTORATION**! 🦅\n"
                    f"**{attacker['name']}** bathes in regenerative flames!\n"
                    f"💚 Healed {heal_amount} HP through immortal fire!"
                )

        # Spinosaurus Zoan (Ryu Ryu no Mi: Model Spinosaurus)
        elif "Spinosaurus" in effect:
            attacker["max_hp"] = int(attacker["max_hp"] * 1.2)
            effect_message = (
                f"🦕 **ANCIENT WARRIOR'S ENDURANCE**! 🦕\n"
                f"**{attacker['name']}** taps into prehistoric might!\n"
                f"❤️ Maximum HP increased!"
            )

        # Pteranodon Zoan (Ryu Ryu no Mi: Model Pteranodon)
        elif "Pteranodon" in effect:
            if random.random() < 0.15:
                await self.status_manager.apply_effect("dodge", attacker, duration=1)
                effect_message = (
                    f"🦅 **AERIAL SUPREMACY**! 🦅\n"
                    f"**{attacker['name']}** takes to the skies!\n"
                    f"💨 Attack evaded through aerial maneuver!"
                )

        # Wolf Deity Zoan (Inu Inu no Mi: Model Okuchi no Makami)
        elif "Okuchi no Makami" in effect:
            heal_amount = int(move.get("heal_amount", 0) * 2)
            if heal_amount > 0:
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                effect_message = (
                    f"🐺 **DIVINE WOLF'S BLESSING**! 🐺\n"
                    f"**{attacker['name']}** channels sacred healing!\n"
                    f"✨ Healing doubled to {heal_amount}!"
                )

        # Thunderbird Zoan (Tori Tori no Mi: Model Thunderbird)
        elif "Thunderbird" in effect:
            if "lightning" in move.get("effect", ""):
                bonus_damage = int(move.get("damage", 0) * 0.3)
                effect_message = (
                    f"⚡ **STORM DEITY'S WRATH**! ⚡\n"
                    f"**{attacker['name']}** commands divine lightning!\n"
                    f"💫 Lightning damage amplified!"
                )

        # Buddha Zoan (Hito Hito no Mi: Model Daibutsu)
        elif "Daibutsu" in effect:
            await self.status_manager.apply_effect("protect", attacker, duration=2)
            bonus_damage = int(move.get("damage", 0) * 0.2)
            effect_message = (
                f"🗿 **ENLIGHTENED COMBAT**! 🗿\n"
                f"**{attacker['name']}** channels Buddha's power!\n"
                f"🛡️ Defense and attack enhanced!"
            )

        # Cerberus Zoan (Inu Inu no Mi: Model Cerberus)
        elif "Cerberus" in effect:
            if random.random() < 0.3:
                bonus_damage = int(move.get("damage", 0))  # Double damage
                effect_message = (
                    f"🐕 **HELLHOUND'S FURY**! 🐕\n"
                    f"**{attacker['name']}** strikes with three heads!\n"
                    f"💥 Triple coordinated attack!"
                )

        # Nika Zoan (Hito Hito no Mi: Model Nika)
        elif effect == "nika":
            if random.random() < 0.4:
                effect_choice = random.choice(["drumbeat", "giant", "freedom"])
                if effect_choice == "drumbeat":
                    bonus_damage = int(move.get("damage", 0) * 0.8)
                    effect_message = (
                        f"💥 **DRUMS OF LIBERATION**! 💥\n"
                        f"**{attacker['name']}** awakens the rhythm of freedom!\n"
                        f"🥁 Massive damage boost through joy!"
                    )
                elif effect_choice == "giant":
                    await self.status_manager.apply_effect("transform", attacker, duration=2)
                    effect_message = (
                        f"🌟 **GIANT WARRIOR**! 🌟\n"
                        f"**{attacker['name']}** becomes a giant!\n"
                        f"👊 Size and power dramatically increased!"
                    )
                elif effect_choice == "freedom":
                    # Clear all negative status effects
                    attacker["status"] = {k: v for k, v in attacker["status"].items() 
                                        if not isinstance(v, (bool, int)) or not v}
                    effect_message = (
                        f"🌈 **WARRIOR OF LIBERATION**! 🌈\n"
                        f"**{attacker['name']}** breaks all limitations!\n"
                        f"✨ All negative status effects removed!"
                    )

        # Eight-Headed Snake Zoan (Hebi Hebi no Mi: Model Yamata no Orochi)
        elif "Yamata no Orochi" in effect:
            if random.random() < 0.3:
                multi_strike = random.randint(2, 4)
                bonus_damage = int(move.get("damage", 0) * (multi_strike - 1))
                effect_message = (
                    f"🐍 **EIGHT-HEADED ASSAULT**! 🐍\n"
                    f"**{attacker['name']}** strikes with multiple heads!\n"
                    f"💥 {multi_strike}x strike combo!"
                )

        # Environment interactions
        if environment == "Wano" and ("Dragon" in effect or "Orochi" in effect):
            bonus_damage = int(bonus_damage * 1.3)
            effect_message = f"{effect_message}\n⚔️ Power enhanced by Wano's legendary aura!"

        return bonus_damage, effect_message

    async def _handle_paramecia_effects(self, attacker, defender, effect, move, environment):
        """Handle Paramecia-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None

        # Gomu Gomu no Mi
        if effect == "rubber":
            if move.get("type") == "strong":
                bonus_damage = int(move.get("damage", 0) * 0.5)
                effect_message = (
                    f"💫 **RUBBER ENHANCEMENT**! 💫\n"
                    f"**{attacker['name']}** stretches for maximum power!\n"
                    f"💥 Attack power increased by elasticity!"
                )

        # Ope Ope no Mi
        elif effect == "surgical":
            if random.random() < 0.2:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(move.get("damage", 0) * 0.3)
                effect_message = (
                    f"🏥 **ROOM: SHAMBLES**! 🏥\n"
                    f"**{attacker['name']}** performs surgical precision!\n"
                    f"✨ Target disoriented by spatial manipulation!"
                )

        # Bomu Bomu no Mi
        elif effect == "explosion":
            bonus_damage = int(move.get("damage", 0) * 0.3)
            effect_message = (
                f"💥 **EXPLOSIVE FORCE**! 💥\n"
                f"**{attacker['name']}** detonates with power!\n"
                f"🎯 Blast damage bonus activated!"
            )

        # Kilo Kilo no Mi
        elif effect == "weight":
            if random.random() < 0.35:
                if random.random() < 0.5:
                    bonus_damage = int(move.get("damage", 0) * 1.0)  # Double damage
                    effect_message = (
                        f"⚖️ **WEIGHT CRUSH**! ⚖️\n"
                        f"**{attacker['name']}** increases mass for impact!\n"
                        f"💥 Double damage from weight manipulation!"
                    )
                else:
                    await self.status_manager.apply_effect("dodge", attacker, duration=1)
                    effect_message = (
                        f"🪶 **WEIGHTLESS DODGE**! 🪶\n"
                        f"**{attacker['name']}** becomes weightless!\n"
                        f"✨ Attack evaded through weight control!"
                    )

        # Toge Toge no Mi
        elif effect == "spikes":
            if random.random() < 0.3:
                counter_damage = int(move.get("damage", 0) * 0.4)
                defender["hp"] -= counter_damage
                effect_message = (
                    f"🌵 **SPIKE COUNTER**! 🌵\n"
                    f"**{attacker['name']}** retaliates with spikes!\n"
                    f"💥 Counter damage: {counter_damage}!"
                )

        # Bane Bane no Mi
        elif effect == "springs":
            if random.random() < 0.25:
                bonus_damage = int(move.get("damage", 0) * 0.4)
                effect_message = (
                    f"🔄 **SPRING FORCE**! 🔄\n"
                    f"**{attacker['name']}** compresses and releases!\n"
                    f"💫 Spring-powered attack boost!"
                )

        # Hana Hana no Mi
        elif effect == "multiple limbs":
            if random.random() < 0.3:
                extra_hits = random.randint(1, 3)
                bonus_damage = int(move.get("damage", 0) * (0.5 * extra_hits))
                effect_message = (
                    f"🌸 **FLEUR CASCADE**! 🌸\n"
                    f"**{attacker['name']}** sprouts multiple limbs!\n"
                    f"👊 {extra_hits} extra attacks landed!"
                )

        # Doru Doru no Mi
        elif effect == "wax":
            if random.random() < 0.3:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                effect_message = (
                    f"🕯️ **WAX ARMOR**! 🕯️\n"
                    f"**{attacker['name']}** creates protective wax!\n"
                    f"🛡️ Defense boosted by hardened wax!"
                )

        # Supa Supa no Mi
        elif effect == "blades":
            bonus_damage = int(move.get("damage", 0) * 0.3)
            effect_message = (
                f"⚔️ **STEEL BODY**! ⚔️\n"
                f"**{attacker['name']}** turns body to blades!\n"
                f"🗡️ Melee damage increased!"
            )

        # Baku Baku no Mi
        elif effect == "eat anything":
            if random.random() < 0.25:
                bonus_damage = int(move.get("damage", 0) * 0.5)
                effect_message = (
                    f"🍽️ **WEAPON DIGESTION**! 🍽️\n"
                    f"**{attacker['name']}** consumes and copies power!\n"
                    f"💥 Attack enhanced by absorbed weapons!"
                )

        # Mane Mane no Mi
        elif effect == "copy":
            if random.random() < 0.25:
                bonus_damage = int(move.get("damage", 0))  # Double damage
                effect_message = (
                    f"👥 **PERFECT MIMICRY**! 👥\n"
                    f"**{attacker['name']}** copies enemy technique!\n"
                    f"✨ Double damage through mimicry!"
                )

        # Goe Goe no Mi
        elif effect == "sound waves":
            if random.random() < 0.3:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                effect_message = (
                    f"🔊 **SONIC BURST**! 🔊\n"
                    f"**{attacker['name']}** releases sound waves!\n"
                    f"💫 Target stunned by sound!"
                )

        # Ori Ori no Mi
        elif effect == "binding":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("bind", defender, duration=2)
                effect_message = (
                    f"⛓️ **BINDING PRISON**! ⛓️\n"
                    f"**{attacker['name']}** restrains the target!\n"
                    f"🔒 Target movement restricted!"
                )

        # Kage Kage no Mi
        elif effect == "shadows":
            if random.random() < 0.2:
                steal_amount = int(move.get("damage", 0) * 0.3)
                defender["hp"] -= steal_amount
                attacker["hp"] = min(250, attacker["hp"] + steal_amount)
                effect_message = (
                    f"👥 **SHADOW THEFT**! 👥\n"
                    f"**{attacker['name']}** steals enemy's shadow!\n"
                    f"🌑 Drained {steal_amount} HP through shadow!"
                )

        # Shari Shari no Mi
        elif effect == "wheels":
            if random.random() < 0.3:
                bonus_damage = int(move.get("damage", 0) * 0.4)
                effect_message = (
                    f"🎡 **WHEEL RUSH**! 🎡\n"
                    f"**{attacker['name']}** transforms into deadly wheel!\n"
                    f"💨 Spinning attack boost!"
                )

        # Awa Awa no Mi
        elif effect == "bubbles":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("defense_down", defender, duration=2)
                effect_message = (
                    f"🫧 **CLEANSING BUBBLES**! 🫧\n"
                    f"**{attacker['name']}** weakens target's defense!\n"
                    f"✨ Enemy defense reduced!"
                )

        # Sabi Sabi no Mi
        elif effect == "rust":
            if random.random() < 0.3:
                await self.status_manager.apply_effect("defense_down", defender, duration=2)
                bonus_damage = int(move.get("damage", 0) * 0.3)
                effect_message = (
                    f"🔨 **RUST DECAY**! 🔨\n"
                    f"**{attacker['name']}** corrodes enemy defenses!\n"
                    f"💫 Defense reduced + Bonus damage!"
                )

        # Noro Noro no Mi
        elif effect == "slow beam":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                effect_message = (
                    f"⏳ **SLOW BEAM**! ⏳\n"
                    f"**{attacker['name']}** slows the target!\n"
                    f"🐌 Enemy movement slowed!"
                )

        # Doa Doa no Mi
        elif effect == "doors":
            if random.random() < 0.2:
                await self.status_manager.apply_effect("dodge", attacker, duration=1)
                effect_message = (
                    f"🚪 **DOOR ESCAPE**! 🚪\n"
                    f"**{attacker['name']}** creates an escape door!\n"
                    f"✨ Attack dodged through door power!"
                )

        # Beri Beri no Mi
        elif effect == "barrier balls":
            if random.random() < 0.3:
                await self.status_manager.apply_effect("dodge", attacker, duration=1)
                effect_message = (
                    f"🔮 **BERRY BARRIER**! 🔮\n"
                    f"**{attacker['name']}** splits into barrier balls!\n"
                    f"✨ Attack avoided through splitting!"
                )

        # Yomi Yomi no Mi
        elif effect == "revival":
            if attacker["hp"] <= 50 and random.random() < 0.3:
                heal_amount = 75  # 30% of max HP
                attacker["hp"] = min(250, attacker["hp"] + heal_amount)
                effect_message = (
                    f"💀 **SOUL KING'S ENCORE**! 💀\n"
                    f"**{attacker['name']}** refuses to fall!\n"
                    f"✨ Recovered {heal_amount} HP!"
                )

        # Horo Horo no Mi
        elif effect == "ghosts":
            if random.random() < 0.25:
                await self.status_manager.apply_effect("attack_down", defender, duration=2)
                effect_message = (
                    f"👻 **NEGATIVE HOLLOW**! 👻\n"
                    f"**{attacker['name']}** summons negative ghosts!\n"
                    f"💔 Enemy attack power reduced!"
                )

        # Zushi Zushi no Mi
        elif effect == "gravity":
            if random.random() < 0.2:
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(move.get("damage", 0) * 0.4)
                effect_message = (
                    f"🌌 **GRAVITY CRUSH**! 🌌\n"
                    f"**{attacker['name']}** manipulates gravity!\n"
                    f"💫 Target crushed + Bonus damage!"
                )

        # Gura Gura no Mi
        elif effect == "quake":
            bonus_damage = int(move.get("damage", 0) * 0.6)
            effect_message = (
                f"💥 **SEISMIC SHOCK**! 💥\n"
                f"**{attacker['name']}** shatters the air itself!\n"
                f"🌋 Massive quake damage!"
            )

        # Environment interactions
        if environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message += "\n⚔️ Power enhanced by Marineford's warrior spirit!"
        elif environment == "Dressrosa" and effect in ["string", "toy"]:
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message += "\n🎭 Power amplified by Dressrosa's strings!"

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
        self.MAX_BURN_STACKS = 3
        self.MAX_STUN_DURATION = 2
        self.MAX_FREEZE_DURATION = 2
        
    async def apply_effect(self, effect_type: str, target: dict, value: int = 1, duration: int = 1):
        """Apply a status effect with proper stacking rules."""
        if "status" not in target:
            target["status"] = {}
            
        if effect_type == "burn":
            # Burn stacks up to MAX_BURN_STACKS
            current_stacks = target["status"].get("burn", 0)
            target["status"]["burn"] = min(current_stacks + value, self.MAX_BURN_STACKS)
            return f"🔥 Burn stacks: {target['status']['burn']}"
            
        elif effect_type == "stun":
            # Stun doesn't stack duration but refreshes
            if not target["status"].get("stun", False):
                target["status"]["stun"] = min(duration, self.MAX_STUN_DURATION)
                return "⚡ Stunned!"
            return None
            
        elif effect_type == "freeze":
            # Freeze extends duration up to MAX_FREEZE_DURATION
            current_freeze = target["status"].get("freeze", 0)
            target["status"]["freeze"] = min(current_freeze + duration, self.MAX_FREEZE_DURATION)
            return f"❄️ Frozen for {target['status']['freeze']} turns!"
            
        elif effect_type == "protect":
            # Protection doesn't stack, just refreshes
            target["status"]["protected"] = True
            target["status"]["protect_duration"] = duration
            return "🛡️ Protected!"
            
        return None

    async def process_effects(self, player: dict) -> tuple[list[str], int]:
        """Process all status effects on a player's turn."""
        if "status" not in player:
            return [], 0
            
        messages = []
        total_damage = 0
        
        # Process burn
        if player["status"].get("burn", 0) > 0:
            damage = 5 * player["status"]["burn"]  # 5 damage per burn stack
            total_damage += damage
            messages.append(f"🔥 Burn deals {damage} damage!")
            player["status"]["burn"] -= 1  # Reduce burn stacks
            
        # Process stun
        if player["status"].get("stun", 0) > 0:
            messages.append("⚡ Stunned - Skip turn!")
            player["status"]["stun"] -= 1
            
        # Process freeze
        if player["status"].get("freeze", 0) > 0:
            messages.append("❄️ Frozen - Skip turn!")
            player["status"]["freeze"] -= 1
            
        # Process protection
        if player["status"].get("protected", False):
            if player["status"].get("protect_duration", 0) > 0:
                messages.append("🛡️ Protected from damage!")
                player["status"]["protect_duration"] -= 1
            else:
                player["status"]["protected"] = False
                
        return messages, total_damage

    async def calculate_damage_with_effects(self, base_damage: int, attacker: dict, defender: dict) -> tuple[int, list[str]]:
        """Calculate final damage considering all status effects."""
        messages = []
        final_damage = base_damage
        
        # Check defender's protection
        if defender["status"].get("protected", False):
            final_damage = int(final_damage * 0.5)  # 50% damage reduction
            messages.append("🛡️ Damage reduced by protection!")
            
        # Apply attacker's bonuses
        if attacker["status"].get("empowered", False):
            final_damage = int(final_damage * 1.2)  # 20% damage boost
            messages.append("💪 Damage boosted by empowerment!")
            
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
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1357924680, force_registration=True)
        
        # Comprehensive default member settings
        default_member = {
            # Existing core values
            "bounty": 0,
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
            
            # New tracking stats (will be available but won't break existing code)
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

        # Existing guild settings with new additions
        default_guild = {
            "bounties": {},
            "event": None,
            "tournaments": {},
            "beta_active": True,
            "leaderboard_channel": None,
            "announcement_channel": None,
            "active_events": {},
            "disabled_commands": []
        }

        # Register all defaults
        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)
        
        # Initialize locks
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
        self.log = logging.getLogger("red.deathmatch")
        self.log.setLevel(logging.INFO)

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
            
            # Sync devil fruit
            config_fruit = await self.config.member(member).devil_fruit()
            json_fruit = bounties[user_id].get("fruit")
            
            if config_fruit or json_fruit:
                true_fruit = config_fruit or json_fruit
                bounties[user_id]["fruit"] = true_fruit
                await self.config.member(member).devil_fruit.set(true_fruit)
            
            # Update last active timestamp
            await self.config.member(member).last_active.set(datetime.utcnow().isoformat())
            
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
                    title="🍎 Devil Fruit Cleanup Report",
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

            # Check if it's a rare fruit and if it's already taken
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
        
        # If user has any bounty in either system, sync and return
        if config_bounty > 0 or json_bounty > 0:
            true_bounty = max(config_bounty, json_bounty)
            
            # Sync both systems
            bounties[user_id] = bounties.get(user_id, {})
            bounties[user_id]["amount"] = true_bounty
            save_bounties(bounties)
            await self.config.member(user).bounty.set(true_bounty)
            
            return await ctx.send(f"Ye already have a bounty of `{true_bounty:,}` Berries, ye scallywag!")

        # Set initial bounty for new players
        initial_bounty = random.randint(50, 100)
        
        try:
            # Update both systems
            bounties[user_id] = {
                "amount": initial_bounty,
                "fruit": None
            }
            save_bounties(bounties)
            await self.config.member(user).bounty.set(initial_bounty)
            
            # Initialize other stats
            await self.config.member(user).wins.set(0)
            await self.config.member(user).losses.set(0)
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())
            
            # Create welcome embed
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
        """Clean up Devil Fruits from inactive players (Admin/Owner only)."""
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
            
        await self.cleanup_inactive_fruits(ctx, days)
    
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
                fruit_display = f" • 🍎 {devil_fruit}" if devil_fruit and devil_fruit != "None" else ""
                
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

        # Get all currently taken fruits
        all_taken_fruits = {data.get("fruit") for data in bounties.values() if data.get("fruit")}

        # Get available rare fruits (removing taken ones)
        available_rare_fruits = [
            fruit for fruit in DEVIL_FRUITS["Rare"].keys() 
            if fruit not in all_taken_fruits
        ]

        # Get available common fruits
        available_common_fruits = [
            fruit for fruit in DEVIL_FRUITS["Common"].keys() 
            if fruit not in all_taken_fruits
        ]

        if not available_rare_fruits and not available_common_fruits:
            return await ctx.send("❌ There are no Devil Fruits available right now! Try again later.")

        # 10% chance for rare fruit if available
        if available_rare_fruits and random.random() < 0.10:
            new_fruit = random.choice(available_rare_fruits)
            fruit_data = DEVIL_FRUITS["Rare"][new_fruit]
            is_rare = True
        else:
            if not available_common_fruits:
                return await ctx.send("❌ No common Devil Fruits are available right now! Try again later.")
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
                f"🍎 **{user.display_name}** has eaten the **{new_fruit}**!\n"
                f"Type: {fruit_data['type']}\n"
                f"🔥 Power: {fruit_data['bonus']}\n\n"
                f"⚠️ *You cannot eat another Devil Fruit!*"
            )


    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners and Admins remove for free, others pay 1,000,000 berries."""
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
        config_fruit = await self.config.member(member).devil_fruit()
        bounty_fruit = bounties.get(user_id, {}).get("fruit", None)

        # Check both sources for devil fruit
        if not config_fruit and not bounty_fruit:
            return await ctx.send(f"🍏 **{member.display_name}** has no Devil Fruit to remove!")

        # Get the actual fruit (prefer config over bounties)
        current_fruit = config_fruit or bounty_fruit

        # ✅ Owners and Admins remove the fruit for free
        if is_owner or is_admin:
            # Clear from both sources
            await self.config.member(member).devil_fruit.set(None)
            if user_id in bounties:
                bounties[user_id]["fruit"] = None
                save_bounties(bounties)
            return await ctx.send(f"🛡️ **{user.display_name}** removed `{current_fruit}` from **{member.display_name}** for free!")

        # Normal users must pay
        berries = await self.config.member(user).berries()
        cost = 1_000_000

        if berries < cost:
            return await ctx.send(f"❌ You need **{cost:,}** berries to remove your Devil Fruit.")

        # Deduct cost and remove fruit
        await self.config.member(user).berries.set(berries - cost)
        await self.config.member(member).devil_fruit.set(None)
        
        if user_id in bounties:
            bounties[user_id]["fruit"] = None
            save_bounties(bounties)

        await ctx.send(
            f"💰 **{user.display_name}** paid **{cost:,}** berries to remove `{current_fruit}` from **{member.display_name}**!\n"
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
            title="🍎 Devil Fruit Given!",
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
            f"🍎 **{user.display_name}** has the **{fruit}**! ({fruit_type} Type)\n"
            f"🔥 **Ability:** {effect}"
        )

    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.user)
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
                return await ctx.send(f"💰 **{target.display_name}** is too broke to be worth hunting! (Minimum: {min_bounty:,} Berries)")

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
                    description=f"💰 **{hunter.display_name}** successfully infiltrated **{target.display_name}**'s vault!",
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
                        value=f"`{penalty:,} Berries`",
                        inline=False
                    )
                    failure_embed.add_field(
                        name="🏴‍☠️ Remaining Bounty",
                        value=f"`{bounties[hunter_id]['amount']:,} Berries`",
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
        embed.add_field(name="💰 Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="🎭 Title", value=f"`{current_title}`", inline=False)
        
        await ctx.send(embed=embed)

    
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase."""
        user = ctx.author
        last_claim = await self.config.member(user).last_daily_claim()
        now = datetime.utcnow()

        if last_claim:
            last_claim = datetime.fromisoformat(last_claim)
            time_left = timedelta(days=1) - (now - last_claim)
            
            if time_left.total_seconds() > 0:
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Try again in {hours} hours and {minutes} minutes! ⏳")

        # Sync bounty before processing
        current_bounty = await self.sync_bounty(user)
        
        if not current_bounty and current_bounty != 0:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

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
            bounties = load_bounties()
            user_id = str(user.id)
            
            try:
                bounties[user_id]["amount"] += increase
                save_bounties(bounties)
                await self.config.member(user).bounty.set(bounties[user_id]["amount"])
                await self.config.member(user).last_daily_claim.set(now.isoformat())
            except Exception as e:
                logger.error(f"Failed to save daily bounty data: {e}")
                ctx.command.reset_cooldown(ctx)  # Reset cooldown if save fails
                await ctx.send("⚠️ Failed to claim daily bounty. Please try again.")
                return
            
            # Update both storage systems
            bounties[user_id]["amount"] += increase
            save_bounties(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            
            await ctx.send(f"💰 Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
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
        """Get the bounty title based on the bounty amount."""
        # Define titles and their required bounties
        titles = {
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
        
        # Find the highest title the bounty qualifies for
        current_title = "Unknown Pirate"
        for title, requirements in titles.items():
            if bounty_amount >= requirements["bounty"]:
                current_title = title
                
        return current_title

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
        embed.add_field(name="💰 Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="🍎 Devil Fruit", value=f"`{devil_fruit}`", inline=False)
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

        @berryflip.error
        async def berryflip_error(self, ctx, error):
            """Custom error handler for berryflip command."""
            if isinstance(error, commands.CommandOnCooldown):
                # Only send the cooldown message once
                minutes = int(error.retry_after / 60)
                seconds = int(error.retry_after % 60)
                await ctx.send(f"⏳ Wait **{minutes}m {seconds}s** before gambling again!")
        
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
        """
        TEMPLATE_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/deathbattle.png"
        FONT_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/onepiece.ttf"
    
        # Open the local template image
        template = Image.open(TEMPLATE_PATH)
        draw = ImageDraw.Draw(template)
    
        # Load font
        try:
            username_font = ImageFont.truetype(FONT_PATH, 25)
        except OSError:
            raise FileNotFoundError(f"Font file not found at {FONT_PATH}")
    
        # Avatar dimensions and positions
        avatar_size = (250, 260)  # Adjust as needed
        avatar_positions = [(15, 130), (358, 130)]  # Positions for avatars
        username_positions = [(75, 410), (430, 410)]  # Positions for usernames
    
        # Fetch and paste avatars
        for i, user in enumerate((user1, user2)):
            avatar_response = requests.get(user.display_avatar.url)
            avatar = Image.open(io.BytesIO(avatar_response.content)).convert("RGBA")
            avatar = avatar.resize(avatar_size)
    
            # Paste avatar onto the template
            template.paste(avatar, avatar_positions[i], avatar)
    
            # Draw username
            draw.text(username_positions[i], user.display_name, font=username_font, fill="black")
    
        # Save the image to a BytesIO object
        output = io.BytesIO()
        template.save(output, format="PNG")
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

    @commands.hybrid_command(name="deathbattle")
    async def deathbattle(self, ctx: commands.Context, opponent: discord.Member = None):
        """
        Start a One Piece deathmatch against another user with a bounty.
        """
        try:
            # ✅ Retrieve the bounty list
            bounties = await self.config.guild(ctx.guild).bounties()

            # ✅ If no opponent is provided, choose a random bounty holder
            if opponent is None:
                valid_opponents = [ctx.guild.get_member(int(user_id)) for user_id, data in bounties.items() if data["amount"] > 0]

                if not valid_opponents:
                    return await ctx.send("❌ **There are no users with a bounty to challenge!**")

                opponent = random.choice(valid_opponents)  # ✅ Randomly pick an eligible opponent

            # ✅ Ensure the opponent has a bounty
            elif str(opponent.id) not in bounties or bounties[str(opponent.id)]["amount"] <= 0:
                return await ctx.send(f"❌ **{opponent.display_name} does not have a bounty!**")

            # ✅ Prevent invalid matches
            if ctx.author == opponent:
                return await ctx.send("❌ You cannot challenge yourself to a deathmatch!")
            if opponent.bot:
                return await ctx.send("❌ You cannot challenge a bot to a deathmatch!")
            
            # ✅ Check if a battle is already in progress
            if ctx.channel.id in self.active_channels:
                return await ctx.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")

            # ✅ Mark the channel as active
            self.active_channels.add(ctx.channel.id)

            # ✅ Generate fight card
            fight_card = self.generate_fight_card(ctx.author, opponent)

            # ✅ Send the dynamically generated fight card image
            await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))

            try:
                # ✅ Call the fight function and update bounty only for the initiator
                await self.fight(ctx, ctx.author, opponent)
            except Exception as e:
                await ctx.send(f"❌ An error occurred during the battle: {str(e)}")
                self.log.error(f"Battle error: {str(e)}")
            finally:
                # ✅ Always attempt to remove the channel ID, even if an error occurs
                if ctx.channel.id in self.active_channels:
                    self.active_channels.remove(ctx.channel.id)

        except Exception as e:
            # ✅ Catch any unexpected errors
            await ctx.send(f"❌ An unexpected error occurred: {str(e)}")
            self.log.error(f"Deathbattle command error: {str(e)}")
            
            # ✅ Ensure channel is removed from active channels if an error occurs
            if ctx.channel.id in self.active_channels:
                self.active_channels.remove(ctx.channel.id)

            # ✅ Re-raise the exception for further handling
            raise

        
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
                    fruit_text = f"\n🍎 *{player['fruit']}*" if player['fruit'] else ""
                    
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

                    # Compile turn message
                    turn_message = [f"\nTurn {turn}: **{attacker['name']}** used **{modified_move['name']}**!"]
                    if damage_message:
                        turn_message.append(damage_message)
                    if env_move_messages:
                        turn_message.extend(env_move_messages)
                    if fruit_message:
                        turn_message.append(fruit_message)
                    if effect_messages:
                        turn_message.extend(effect_messages)
                    turn_message.append(f"💥 Dealt **{final_damage}** damage!")

                    # Update battle log
                    await battle_log.edit(content=f"{battle_log.content}\n{''.join(turn_message)}")

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
                        title="💰 Battle Rewards",
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
        
        # Sort by Wins
        sorted_by_wins = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Top 10 Players by Wins 🏆",
            color=0xFFD700,
        )
        for i, (member_id, data) in enumerate(sorted_by_wins[:10], start=1):
            member = ctx.guild.get_member(member_id)
            if member:
                embed.add_field(
                    name=f"{i}. {member.display_name}",
                    value=f"Wins: {data['wins']}\nLosses: {data['losses']}",
                    inline=False,
                )
        
        await ctx.send(embed=embed)

    @deathboard.command(name="kdr")
    async def deathboard_kdr(self, ctx: commands.Context):
        """Show the top 10 players by Kill/Death Ratio (KDR)."""
        all_members = await self.config.all_members(ctx.guild)
    
        # Calculate KDR
        kdr_list = []
        for member_id, data in all_members.items():
            wins = data["wins"]
            losses = data["losses"]
            kdr = wins / losses if losses > 0 else wins  # Avoid division by zero
            member = ctx.guild.get_member(member_id)
            if member:
                kdr_list.append((member, kdr, wins, losses))
        
        # Sort by KDR
        sorted_by_kdr = sorted(kdr_list, key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🏅 Top 10 Players by KDR 🏅",
            color=0x00FF00,
        )
        for i, (member, kdr, wins, losses) in enumerate(sorted_by_kdr[:10], start=1):
            embed.add_field(
                name=f"{i}. {member.display_name}",
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

        # Get all titles based on synced bounty
        unlocked_titles = {t for t, c in TITLES.items() if true_bounty >= c["bounty"]}
        user_titles = await self.config.member(user).titles()
        unlocked_titles.update(user_titles)
        current_title = await self.config.member(user).current_title()

        if action == "equip" and title:
            if title not in unlocked_titles:
                return await ctx.send(f"❌ You haven't unlocked the title `{title}` yet!")
            await self.config.member(user).current_title.set(title)
            return await ctx.send(f"✅ Title equipped: `{title}`")

        embed = discord.Embed(title=f"🏆 {user.display_name}'s Titles", color=discord.Color.gold())
        embed.add_field(name="Unlocked Titles", value="\n".join(unlocked_titles) or "None", inline=False)
        embed.add_field(name="Current Title", value=current_title or "None", inline=False)
        await ctx.send(embed=embed)
        
    @commands.command(name="equiptitle")
    async def equiptitle(self, ctx: commands.Context, *, title: str):
        """Equip a title for yourself."""
        titles = await self.config.member(ctx.author).titles()
        title_lower = title.lower()
        matched_title = next((t for t in titles if t.lower() == title_lower), None)
        
        if not matched_title:
            await ctx.send(f"❌ You have not unlocked the title `{title}`.")
            return

        # ✅ Save the equipped title as `current_title`
        await self.config.member(ctx.author).current_title.set(matched_title)
        await ctx.send(f"✅ You have equipped the title `{matched_title}`!")

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
                    f"💰 Current Bounty: `{true_bounty:,}` Berries\n"
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
