from redbot.core import commands, Config
import discord
import random
import asyncio
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import logging
import aiohttp
import io  
import json
import os

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

MOVES = [
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": "crit"},
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": "crit"},
    {"name": "Diable Jambe", "type": "regular", "description": "Sanji's fiery kick!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Clown Bombs", "type": "regular", "description": "Buggy's explosive prank!", "effect": "burn", "burn_chance": 0.20},
    {"name": "Heavy Point", "type": "strong", "description": "Chopper smashes his enemy!", "effect": "heal"},
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "crit"},
    {"name": "Soul Solid", "type": "regular", "description": "Brook plays a chilling tune!", "effect": "stun"},
    {"name": "Pop Green", "type": "regular", "description": "Usopp's plant barrage!", "effect": "burn", "burn_chance": 0.15},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Room Shambles", "type": "critical", "description": "Law's surgical strike!", "effect": "stun"},
    {"name": "Dark Vortex", "type": "strong", "description": "Blackbeard's gravity attack!", "effect": "crit"},
    {"name": "Conqueror's Haki", "type": "critical", "description": "Overwhelms your opponent!", "effect": "stun"},
    {"name": "Red Hawk", "type": "strong", "description": "Luffy's fiery attack!", "effect": "burn", "burn_chance": 0.25},
    {"name": "Ice Age", "type": "regular", "description": "Aokiji freezes the battlefield!", "effect": "stun"},
    {"name": "Magma Fist", "type": "strong", "description": "Akainu's devastating magma punch!", "effect": "burn", "burn_chance": 0.45},
    {"name": "Coup de Vent", "type": "regular", "description": "Franky's air cannon!", "effect": "crit"},
    {"name": "Clutch", "type": "regular", "description": "Robin's multi-hand grab!", "effect": "stun"},
    {"name": "Elephant Gun", "type": "strong", "description": "Luffy's giant fist!", "effect": "crit"},
    {"name": "Enel's Judgement", "type": "critical", "description": "Thunder god's ultimate strike!", "effect": "burn", "burn_chance": 0.15},
    {"name": "Pirate King's Will", "type": "regular", "description": "A legendary strike filled with willpower!", "effect": "crit"},
    {"name": "Gomu Gomu no Bazooka", "type": "strong", "description": "Luffy's iconic double-handed smash!", "effect": "crit"},
    {"name": "Hiryu Kaen", "type": "critical", "description": "Zoro's flaming dragon slash!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Hell Memories", "type": "critical", "description": "Sanji unleashes a fiery kick fueled by rage!", "effect": "burn", "burn_chance": 0.50},
    {"name": "Takt", "type": "regular", "description": "Law telekinetically slams debris onto the opponent!", "effect": "crit"},
    {"name": "Shigan", "type": "regular", "description": "Lucci's powerful finger pistol technique!", "effect": "crit"},
    {"name": "Yasakani no Magatama", "type": "strong", "description": "Kizaru rains down a flurry of light-based attacks!", "effect": "crit"},
    {"name": "Venom Demon: Hell's Judgement", "type": "critical", "description": "Magellan unleashes a devastating poisonous assault!", "effect": "burn", "burn_chance": 0.45},
    {"name": "King Kong Gun", "type": "critical", "description": "Luffy's massive Gear Fourth punch!", "effect": "crit"},
    {"name": "Black Hole", "type": "strong", "description": "Blackbeard absorbs everything into darkness!", "effect": "crit"},
    {"name": "Raging Tiger", "type": "regular", "description": "Jinbei punches with the force of a tidal wave!", "effect": "crit"},
    {"name": "Rokushiki: Rokuogan", "type": "critical", "description": "Lucci unleashes a devastating shockwave with pure power!", "effect": "crit"},
    {"name": "Raigo", "type": "critical", "description": "Enel calls down a massive thunder strike!", "effect": "burn", "burn_chance": 0.35},
    {"name": "Ashura: Ichibugin", "type": "critical", "description": "Zoro's nine-sword style cuts through everything in its path!", "effect": "crit"},
    {"name": "Divine Departure", "type": "critical", "description": "Gol D. Roger's legendary strike devastates the battlefield!", "effect": "stun"},
    {"name": "Red Roc", "type": "critical", "description": "Luffy launches a fiery Haki-infused punch!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Puncture Wille", "type": "critical", "description": "Law pierces his enemy with a massive Haki-enhanced attack!", "effect": "stun"},
    {"name": "Shin Tenjin", "type": "critical", "description": "Franky's ultimate laser cannon obliterates everything in its path!", "effect": "crit"},
    {"name": "Meteors of Destruction", "type": "critical", "description": "Fujitora summons a rain of meteors to crush his enemies!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Dragon Twister: Gale of Destruction", "type": "critical", "description": "Kaido spins in a tornado of destruction!", "effect": "crit"},
    {"name": "Yoru Strike: Eternal Night", "type": "critical", "description": "Mihawk's ultimate slash creates darkness and devastation!", "effect": "stun"},
    {"name": "Healing Rain", "type": "regular", "description": "A soothing rain that restores vitality!", "effect": "heal"},
    {"name": "Phoenix Flames", "type": "strong", "description": "Marco's regenerative flames heal the wounds of battle!", "effect": "heal"},
    {"name": "Chopper's Doctor Care", "type": "regular", "description": "Chopper's medical expertise rejuvenates health!", "effect": "heal"},
    {"name": "Sunny’s Energy Cola", "type": "regular", "description": "Franky energizes with cola to restore stamina!", "effect": "heal"},
    {"name": "Tactical Recovery", "type": "regular", "description": "Law's ROOM skill restores some health to himself!", "effect": "heal"},
    {"name": "Life Return", "type": "strong", "description": "A technique that uses energy control to recover health!", "effect": "heal"},
    {"name": "Wings of Regeneration", "type": "critical", "description": "Marco's wings glow as they heal him completely!", "effect": "heal"},
    {"name": "Herb Shot", "type": "regular", "description": "Usopp launches a healing plant extract to recover!", "effect": "heal"},
    {"name": "Soul Serenade", "type": "regular", "description": "Brook's music restores vitality to the soul!", "effect": "heal"},
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


class BountyBattle(commands.Cog):
    """A combined One Piece RPG cog with Bounties & Deathmatches."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1357924680, force_registration=True)
        self.config.register_member(berries=0)


        # Store both bounty and deathmatch stats
        default_member = {
            "bounty": 0,
            "last_daily_claim": None,
            "wins": 0,
            "losses": 0,
            "damage_dealt": 0,
            "achievements": [],
            "titles": [],  # List of unlocked titles
            "current_title": None,  # Equipped title
            "devil_fruit": None,
            "last_active": None,
            "equipped_title": "Unknown Pirate",  # ✅ Now registered!
        }
        self.config.register_member(**default_member)

        default_guild = {
            "bounties": {},
            "event": None,
            "tournaments": {},
            "beta_active": True,  # ✅ Stores whether beta is still running
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.active_channels = set()  # Track active battles by channel ID
        self.tournaments = {}  # Track active tournaments
        self.log = logging.getLogger("red.deathmatch")  # Log under the cog name
        self.log.setLevel(logging.INFO)  # Set the log level
        self.current_environment = None  # Track the current environment
        self.battle_stopped = False  # Track if a battle was stopped
        self.config.register_member(bounty_hunted=0)

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
        
    # ------------------ Bounty System ------------------

    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        user = ctx.author
        bounties = load_bounties()  # ✅ Use load_bounties() instead
        user_id = str(user.id)
    
        if user_id in bounties:
            return await ctx.send("Ye already have a bounty, ye scallywag!")
    
        bounties[user_id] = {"amount": random.randint(50, 100), "fruit": None}
        save_bounties(bounties)  # ✅ Use save_bounties() instead
        
        await ctx.send(f"🏴‍☠️ Ahoy, {user.display_name}! Ye have started yer bounty journey with {bounties[user_id]['amount']} Berries!")
        
        # ✅ If beta is active, give "BETA TESTER" title
        beta_active = await self.config.guild(ctx.guild).beta_active()
        if beta_active:
            unlocked_titles = await self.config.member(ctx.author).titles()
            if "BETA TESTER" not in unlocked_titles:
                unlocked_titles.append("BETA TESTER")
                await self.config.member(ctx.author).titles.set(unlocked_titles)
                await ctx.send(f"🎖️ **{ctx.author.display_name}** has received the exclusive title: `BETA TESTER`!")

    @commands.command()
    @commands.is_owner()  # ✅ Only the bot owner can use this
    async def betaover(self, ctx):
        """End the beta test, preventing new players from getting the 'BETA TESTER' title."""
        beta_active = await self.config.guild(ctx.guild).beta_active()
    
        if not beta_active:
            return await ctx.send("❌ Beta is already over!")
    
        await self.config.guild(ctx.guild).beta_active.set(False)
        await ctx.send("🚨 **The beta test is now officially over!**\nNo new players will receive the `BETA TESTER` title.")
    
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
        """Consume a random Devil Fruit! Some rare fruits are unique and globally announced."""
        user = ctx.author
        bounties = load_bounties()  # ✅ Use load_bounties() instead
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        if bounties[user_id].get("fruit"):
            return await ctx.send(f"❌ You already have the `{bounties[user_id]['fruit']}`! You can only eat one Devil Fruit!")

        # ✅ Get all rare fruits currently taken
        all_taken_fruits = {data["fruit"] for data in bounties.values() if "fruit" in data and data["fruit"] in DEVIL_FRUITS["Rare"]}

        # ✅ Remove taken rare fruits from available list
        available_rare_fruits = [fruit for fruit in DEVIL_FRUITS["Rare"] if fruit not in all_taken_fruits]

        # ✅ Determine fruit type (90% Common, 10% Rare if available)
        is_rare = available_rare_fruits and random.randint(1, 100) <= 10

        if is_rare:
            new_fruit = random.choice(available_rare_fruits)
            fruit_data = DEVIL_FRUITS["Rare"][new_fruit]
        else:
            new_fruit = random.choice(list(DEVIL_FRUITS["Common"].keys()))
            fruit_data = DEVIL_FRUITS["Common"][new_fruit]

        fruit_type = fruit_data["type"]
        effect = fruit_data["bonus"]

        # ✅ Save the fruit to bounties.json
        bounties[user_id]["fruit"] = new_fruit
        save_bounties(bounties)  # ✅ Use save_bounties() instead

        # ✅ ANNOUNCE IF RARE FRUIT
        if is_rare:
            announcement = (
                f"🚨 **Breaking News from the Grand Line!** 🚨\n"
                f"🏴‍☠️ **{user.display_name}** has discovered and consumed the **{new_fruit}**! ({fruit_type} Type)\n"
                f"🔥 **New Power:** {effect}\n\n"
                f"⚠️ *This Devil Fruit is now **UNIQUE**! No one else can eat it unless they remove it!*"
            )
            await ctx.send(announcement)
        else:
            await ctx.send(
                f"🍎 **{user.display_name}** has eaten the **{new_fruit}**! ({fruit_type} Type)\n"
                f"🔥 **New Power:** {effect}\n\n"
                f"⚠️ *You cannot eat another Devil Fruit!*"
            )

        # Assign the fruit to the player in Redbot's Config
        await self.config.member(user).devil_fruit.set(new_fruit)


    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners and Admins remove for free, others pay 1,000,000 berries."""
        user = ctx.author
        member = member or user  # Defaults to the user running the command
        
        # Check if user is bot owner or has admin permissions
        is_owner = await self.bot.is_owner(user)
        is_admin = ctx.author.guild_permissions.administrator

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
    @commands.is_owner()
    async def setbounty(self, ctx, member: discord.Member, amount: int):
        """Set a user's bounty (Admin only)."""
        if amount < 0:
            return await ctx.send("❌ Bounty cannot be negative.")

        await self.config.guild(ctx.guild).bounties.set_raw(str(member.id), value={"amount": amount})
        
        await ctx.send(f"🏴‍☠️ **{member.display_name}** now has a bounty of **{amount:,}** berries!")

    @commands.command()
    @commands.is_owner()
    async def givefruit(self, ctx, member: discord.Member, *, fruit: str):
        """Give a user a Devil Fruit (Admin only)."""
        fruit = fruit.strip().title()  # Normalize case & remove spaces
        all_fruits = {**DEVIL_FRUITS["Common"], **DEVIL_FRUITS["Rare"]}
        fruit_names = {name.lower(): name for name in all_fruits}  # Convert keys to lowercase

        if fruit.lower() not in fruit_names:
            return await ctx.send("❌ That Devil Fruit does not exist in the current list.")

        # Check both sources for existing fruit
        bounties = load_bounties()
        user_id = str(member.id)
        config_fruit = await self.config.member(member).devil_fruit()
        bounty_fruit = bounties.get(user_id, {}).get("fruit", None)

        # If either source has a fruit, prevent giving new fruit
        if config_fruit or bounty_fruit:
            existing_fruit = config_fruit or bounty_fruit
            return await ctx.send(f"❌ **{member.display_name}** already has `{existing_fruit}`! They must remove it first.")

        # Assign the correctly formatted fruit name to both sources
        fruit_name = fruit_names[fruit.lower()]
        await self.config.member(member).devil_fruit.set(fruit_name)
        
        # Initialize or update bounties entry
        if user_id not in bounties:
            bounties[user_id] = {"amount": 0, "fruit": fruit_name}
        else:
            bounties[user_id]["fruit"] = fruit_name
        save_bounties(bounties)

        await ctx.send(f"🍏 **{member.display_name}** has been given the `{fruit_name}`!")
        
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
        hunter = ctx.author
        
        # Initial validation checks
        if hunter == target:
            return await ctx.send("❌ Ye can't hunt yer own bounty, ye scallywag!")
        
        if target.bot:
            return await ctx.send("❌ Ye can't steal from bots, they're too secure!")

        try:
            # Load bounty data
            bounties = load_bounties()
            hunter_id = str(hunter.id)
            target_id = str(target.id)

            # Validate participants
            if not all(uid in bounties for uid in [hunter_id, target_id]):
                return await ctx.send("🏴‍☠️ Both you and your target must have a bounty to participate!")

            target_bounty = bounties[target_id].get("amount", 0)
            hunter_bounty = bounties[hunter_id].get("amount", 0)

            # Check minimum bounty requirements
            min_bounty = 1000
            if target_bounty < min_bounty:
                return await ctx.send(f"💰 **{target.display_name}** is too broke to be worth hunting! (Minimum: {min_bounty:,} Berries)")

            # Generate dynamic lock-picking challenge
            patterns = {
                "Easy": ["🔒🔑", "🔑🔒"],
                "Medium": ["🔒🔑🔑", "🔑🔒🔑", "🔑🔑🔒"],
                "Hard": ["🔒🔑🔑🔒", "🔑🔒🔒🔑", "🔑🔑🔒🔒"]
            }
            
            # Difficulty scales with target's bounty
            if target_bounty > 1_000_000:
                difficulty = "Hard"
            elif target_bounty > 100_000:
                difficulty = "Medium"
            else:
                difficulty = "Easy"

            lock_code = random.choice(patterns[difficulty])
            time_limit = {"Easy": 12, "Medium": 10, "Hard": 8}[difficulty]

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

            # Wait for response
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

            # Check response and handle outcomes
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

            # Calculate steal amount with minimum guarantee
            base_steal = random.uniform(0.05, 0.20)
            steal_amount = max(int(base_steal * target_bounty), 500)

            if success and not critical_failure:
                # Handle successful theft
                bounties[hunter_id]["amount"] += steal_amount
                bounties[target_id]["amount"] = max(0, target_bounty - steal_amount)
                save_bounties(bounties)

                # Update stats and activity
                await self.update_hunter_stats(hunter, steal_amount)
                await self.update_activity(hunter, target)

                # Create success embed
                success_embed = discord.Embed(
                    title="🏴‍☠️ Bounty Hunt Success!",
                    description=f"💰 **{hunter.display_name}** successfully infiltrated **{target.display_name}**'s vault!",
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="💎 Stolen Amount",
                    value=f"`{steal_amount:,} Berries`",
                    inline=False
                )
                success_embed.add_field(
                    name="🏆 New Hunter Bounty",
                    value=f"`{bounties[hunter_id]['amount']:,} Berries`",
                    inline=True
                )
                success_embed.add_field(
                    name="💀 New Target Bounty",
                    value=f"`{bounties[target_id]['amount']:,} Berries`",
                    inline=True
                )
                await ctx.send(embed=success_embed)

            elif critical_failure:
                # Handle critical failure
                penalty = max(int(hunter_bounty * 0.10), 1000)
                bounties[hunter_id]["amount"] = max(0, hunter_bounty - penalty)
                save_bounties(bounties)

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
    async def mybounty(self, ctx):
        """Check your bounty amount."""
        user_id = str(ctx.author.id)
        bounties = load_bounties()

        if user_id not in bounties:
            await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Use `.startbounty`.")
            return

        bounty_amount = bounties[user_id].get("amount", 0)
        await ctx.send(f"🏴‍☠️ {ctx.author.display_name}, yer bounty is `{bounty_amount:,}` Berries!")

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

        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`! and `.eatfruit`!")

        increase = random.randint(1000, 5000)
        
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.config.member(user).last_daily_claim.set(None)
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            bounties[user_id]["amount"] += increase
            await self.config.guild(ctx.guild).bounties.set(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            await self.config.member(user).last_daily_claim.set(now.isoformat())
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
    
        bounties = load_bounties()  # ✅ Use load_bounties() instead
        user_id = str(member.id)
    
        if user_id not in bounties:
            return await ctx.send(f"{member.display_name} needs to start their bounty journey first by typing `.startbounty`!")
    
        bounty_amount = bounties[user_id].get("amount", 0)
        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status != 200:
                    return await ctx.send("Failed to retrieve avatar.")
                avatar_data = await response.read()
    
        wanted_poster = await self.create_wanted_poster(member.display_name, bounty_amount, avatar_data)
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
        
        def get_bounty_title(self, bounty_amount):
            """Get the highest earned bounty title based on the bounty amount."""
            for title, condition in reversed(TITLES.items()):
                if bounty_amount >= condition["bounty"]:
                    return title
            return "Unknown Pirate"

    

    @commands.command()
    @commands.admin_or_permissions(administrator=True)  # Restrict to admins
    async def getdata(self, ctx):
        """Retrieve the current guild's bounty and devil fruit data and save it to bounties.json."""
        
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

        bounties = load_bounties()
        user_id = str(member.id)

        if user_id not in bounties:
            return await ctx.send(f"🏴‍☠️ {member.display_name} has no bounty record! Use `.startbounty`.")

        # Fetch bounty data
        bounty_amount = bounties[user_id].get("amount", 0)
        devil_fruit = bounties[user_id].get("fruit", "None")

        # Fetch user stats from config
        wins = await self.config.member(member).wins()
        losses = await self.config.member(member).losses()
        titles = await self.config.member(member).titles()
        equipped_title = await self.config.member(member).equipped_title() or "None"

        # Count remaining rare fruits
        taken_rare_fruits = {data["fruit"] for data in bounties.values() if "fruit" in data and data["fruit"] in DEVIL_FRUITS["Rare"]}
        remaining_rare_fruits = len(DEVIL_FRUITS["Rare"]) - len(taken_rare_fruits)

        # Build embed
        embed = discord.Embed(title=f"🏴‍☠️ {member.display_name}'s Status", color=discord.Color.gold())
        embed.add_field(name="💰 Bounty", value=f"`{bounty_amount:,} Berries`", inline=False)
        embed.add_field(name="🍎 Devil Fruit", value=f"`{devil_fruit}`" if devil_fruit else "`None`", inline=False)
        embed.add_field(name="🏆 Wins", value=f"`{wins}`", inline=True)
        embed.add_field(name="💀 Losses", value=f"`{losses}`", inline=True)
        embed.add_field(name="🌟 Rare Fruits Left", value=f"`{remaining_rare_fruits}`", inline=False)
        embed.add_field(name="🎖️ Titles", value=", ".join(titles) if titles else "`None`", inline=False)
        embed.add_field(name="🎭 Equipped Title", value=f"`{equipped_title}`", inline=False)

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
    async def berryflip(self, ctx, bet: int = None):
        """Flip a coin to potentially increase your bounty. Higher bets have lower win chances!"""
        try:
            user = ctx.author
            bounties = load_bounties()
            user_id = str(user.id)

            if user_id not in bounties:
                return await ctx.send("🏴‍☠️ Ye need to start yer bounty journey first! Type `.startbounty`")

            current_bounty = bounties[user_id]["amount"]
            
            # Validate bet amount
            if bet is None:
                bet = min(current_bounty, 10000)  # Default to 10k or max bounty
            elif bet < 100:
                return await ctx.send("❌ Minimum bet is `100` Berries! Don't be stingy!")
            elif bet > current_bounty:
                return await ctx.send(f"❌ Ye only have `{current_bounty:,}` Berries to bet!")

            # Create initial embed
            embed = discord.Embed(
                title="🎲 Berry Flip Gamble",
                description=f"**{user.display_name}** is betting `{bet:,}` Berries!",
                color=discord.Color.gold()
            )
            
            # Calculate and show win probability
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

            # Update Config as well for compatibility
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

            # Log the gamble
            logger.info(
                f"Berryflip: {user.display_name} bet {bet:,} Berries - "
                f"{'Won' if won else 'Lost'} - New bounty: {new_bounty:,}"
            )

            # Update the embed
            await message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error in berryflip command: {str(e)}")
            await ctx.send("❌ An error occurred during the gamble!")

    @berryflip.error
    async def berryflip_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
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
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        if mission["description"] == "Answer a trivia question":
            success = await self.handle_trivia_question(ctx, user)
        elif mission["description"] == "Share a fun fact":
            success = await self.handle_fun_fact(ctx, user)
        elif mission["description"] == "Post a meme":
            success = await self.handle_post_meme(ctx, user)

        if success:
            bounties[user_id]["amount"] += mission["reward"]
            await self.config.guild(ctx.guild).bounties.set(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            await ctx.send(f"🏆 Mission completed! Ye earned {mission['reward']:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
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
    def generate_health_bar(self, current_hp: int, max_hp: int = 300, length: int = 10) -> str:
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

    def calculate_damage(self, move_type: str, crit_chance: float = 0.2, turn_number: int = 1, stats=None) -> int:
        """Calculate balanced damage for each move type."""
        base_damage = 0

        if move_type == "regular":
            base_damage = random.randint(5, 10)
        elif move_type == "strong":
            base_damage = random.randint(10, 20)
        elif move_type == "critical":
            base_damage = random.randint(15, 25)

            # Apply critical hit chance
            if random.random() < crit_chance:
                base_damage *= 2

            # Scale critical damage by turn number
            base_damage += turn_number * 2

        return base_damage

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
            hazard_message = "⚡ A lightning bolt strikes, dealing 15 damage to both players!"
            for player in players:
                player["hp"] = max(0, player["hp"] - 15)
        elif environment == "Alabasta" and random.random() < 0.3:  # 30% chance
            hazard_message = "🌪️ A sandstorm reduces accuracy by 20% for 3 turns!"
            for player in players:
                player["status"]["accuracy_reduction"] = 0.2
                player["status"]["accuracy_turns"] = 3
        elif environment == "Wano" and random.random() < 0.3:  # 30% chance
            hazard_message = "🗡️ A samurai's spirit empowers strong attacks, increasing their damage temporarily!"
            for player in players:
                player["status"]["strong_damage_boost"] = 5
                player["status"]["boost_turns"] = 3
        elif environment == "Punk Hazard" and random.random() < 0.3:  # 30% chance
            hazard_message = "🔥❄️ The extreme elements amplify burn and stun effects!"
            for player in players:
                player["status"]["burn_amplification"] = 0.1
                player["status"]["stun_chance_boost"] = True
        elif environment == "Fishman Island" and random.random() < 0.4:  # 40% chance
            hazard_message = "🌊 A soothing wave heals both players for 10 HP!"
            for player in players:
                player["hp"] = min(100, player["hp"] + 10)
        elif environment == "Dressrosa" and random.random() < 0.3:  # 30% chance
            hazard_message = "✨ A dazzling aura increases crit chance for both players!"
            for player in players:
                player["status"]["crit_chance_boost"] = 0.1
                player["status"]["boost_turns"] = 3
        elif environment == "Whole Cake Island" and random.random() < 0.3:  # 30% chance
            hazard_message = "🍰 The sweetness restores 15 HP for both players!"
            for player in players:
                player["hp"] = min(100, player["hp"] + 15)
        elif environment == "Marineford" and random.random() < 0.3:  # 30% chance
            hazard_message = "⚔️ The battlefield empowers strong attacks, increasing their damage!"
            for player in players:
                player["status"]["strong_damage_boost"] = 10
                player["status"]["boost_turns"] = 3
        elif environment == "Enies Lobby" and random.random() < 0.3:  # 30% chance
            hazard_message = "🛡️ Justice prevails, enhancing block effects for both players!"
            for player in players:
                player["status"]["block_amplification"] = True
        elif environment == "Amazon Lily" and random.random() < 0.3:  # 30% chance
            hazard_message = "💖 The charm of the island enhances healing moves!"
            for player in players:
                player["status"]["heal_boost"] = 10
        elif environment == "Zou" and random.random() < 0.3:  # 30% chance
            hazard_message = "🐘 The island enhances all elemental abilities!"
            for player in players:
                player["status"]["elemental_boost"] = 0.1
        elif environment == "Elbaf" and random.random() < 0.3:  # 30% chance
            hazard_message = "🔨 The land of giants amplifies physical attack damage!"
            for player in players:
                player["status"]["physical_damage_boost"] = 15
                player["status"]["boost_turns"] = 3
        elif environment == "Raftel" and random.random() < 0.3:  # 30% chance
            hazard_message = "🏝️ The legendary island boosts all stats for both players!"
            for player in players:
                player["status"]["crit_chance_boost"] = 0.1
                player["status"]["burn_amplification"] = 0.1
                player["status"]["heal_boost"] = 10

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
        """
        Stop an ongoing battle in the current channel with a One Piece joke.
        """
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
        """Enhanced fight system with improved visual display."""
        # Initialize environment
        environment = self.choose_environment()
        environment_data = ENVIRONMENTS[environment]
        
        # Get Devil Fruit info
        challenger_fruit = await self.config.member(challenger).devil_fruit()
        opponent_fruit = await self.config.member(opponent).devil_fruit()
        
        # Initialize player data with 300 HP
        challenger_data = {
            "name": challenger.display_name,
            "hp": 300,
            "member": challenger,
            "fruit": challenger_fruit,
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
                "stuns_applied": 0
            }
        }

        opponent_data = {
            "name": opponent.display_name,
            "hp": 300,
            "member": opponent,
            "fruit": opponent_fruit,
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
                "stuns_applied": 0
            }
        }

        # Create initial battle embed
        embed = discord.Embed(
            title="⚔️ EPIC ONE PIECE BATTLE ⚔️",
            description=f"Battle begins in **{environment}**!\n*{environment_data['description']}*",
            color=discord.Color.blue()
        )

        # Add player info fields
        def update_player_fields():
            # Challenger field
            challenger_status = self.get_status_icons(challenger_data)
            challenger_health = self.generate_health_bar(challenger_data["hp"])
            challenger_fruit_text = f"\n🍎 *{challenger_fruit}*" if challenger_fruit else ""
            
            embed.add_field(
                name=f"🏴‍☠️ {challenger_data['name']}",
                value=(
                    f"❤️ HP: {challenger_data['hp']}/300\n"
                    f"{challenger_health}\n"
                    f"✨ Status: {challenger_status}{challenger_fruit_text}"
                ),
                inline=True
            )

            # VS Separator
            embed.add_field(name="⚔️", value="VS", inline=True)

            # Opponent field
            opponent_status = self.get_status_icons(opponent_data)
            opponent_health = self.generate_health_bar(opponent_data["hp"])
            opponent_fruit_text = f"\n🍎 *{opponent_fruit}*" if opponent_fruit else ""
            
            embed.add_field(
                name=f"🏴‍☠️ {opponent_data['name']}",
                value=(
                    f"❤️ HP: {opponent_data['hp']}/300\n"
                    f"{opponent_health}\n"
                    f"✨ Status: {opponent_status}{opponent_fruit_text}"
                ),
                inline=True
            )

        update_player_fields()
        message = await ctx.send(embed=embed)

        # Battle log message
        battle_log = await ctx.send("📜 **Battle Log:**")
        
        # Battle loop
        turn = 0
        players = [challenger_data, opponent_data]
        current_player = 0
        
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            turn += 1
            attacker = players[current_player]
            defender = players[1 - current_player]
            
            # Check for battle stop
            if self.battle_stopped:
                embed.title = "⚠️ Battle Stopped!"
                embed.description = "The fight has been forcibly ended!"
                await message.edit(embed=embed)
                return

            # Process status effects
            status_message = await self.process_status_effects(attacker, defender)
            if status_message:
                await battle_log.edit(content=f"{battle_log.content}\n{status_message}")
                await asyncio.sleep(2)

            # Select and modify move
            move = random.choice(MOVES)
            move_copy = move.copy()
            if environment_data['effect']:
                environment_data['effect'](move_copy, attacker["stats"])

            # Calculate base damage
            base_damage = self.calculate_damage(move_copy["type"], turn_number=turn)
            final_damage = base_damage
            
            # Apply Devil Fruit effects
            if attacker["fruit"]:
                fruit_data = DEVIL_FRUITS["Common"].get(attacker["fruit"]) or DEVIL_FRUITS["Rare"].get(attacker["fruit"])
                if fruit_data:
                    final_damage, fruit_effect = await self.apply_devil_fruit_effects(
                        attacker, 
                        defender, 
                        base_damage, 
                        move_copy,
                        turn
                    )
                    if fruit_effect:
                        # Create dramatic Devil Fruit activation message
                        fruit_embed = discord.Embed(
                            title="🌟 DEVIL FRUIT POWER ACTIVATED 🌟",
                            description=fruit_effect,
                            color=discord.Color.purple()
                        )
                        activation_msg = await ctx.send(embed=fruit_embed)
                        await asyncio.sleep(2)
                        await activation_msg.delete()

            # Update HP and create action description
            defender["hp"] = max(0, defender["hp"] - final_damage)
            action_description = (
                f"**{attacker['name']}** used **{move_copy['name']}**!\n"
                f"{move_copy['description']}\n"
                f"💥 Dealt **{final_damage}** damage!"
            )
            
            # Update battle log
            await battle_log.edit(content=f"{battle_log.content}\n{action_description}")
            
            # Update main embed
            embed.clear_fields()
            update_player_fields()
            await message.edit(embed=embed)
            await asyncio.sleep(3)
            
            # Switch turns
            current_player = 1 - current_player

        # Determine winner
        winner = players[0] if players[0]["hp"] > 0 else players[1]
        loser = players[1] if players[0]["hp"] > 0 else players[0]

        # Update stats and handle rewards
        await self._handle_battle_rewards(ctx, winner, loser)
        
        # Final embed update - Clean victory message
        victory_embed = discord.Embed(
            title="🏆 Battle Complete!",
            description=f"**{winner['name']}** is victorious!",
            color=discord.Color.gold()
        )
        await message.edit(embed=victory_embed)

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
        """Handle post-battle rewards and updates."""
        try:
            # Update bounties
            bounties = load_bounties()
            winner_id = str(winner["member"].id)
            loser_id = str(loser["member"].id)
            
            # Calculate bounty changes
            bounty_increase = random.randint(1000, 3000)
            bounty_decrease = random.randint(500, 1500)
            
            # Update winner's bounty
            if winner_id in bounties:
                bounties[winner_id]["amount"] += bounty_increase
                
            # Update loser's bounty
            if loser_id in bounties:
                current_bounty = bounties[loser_id].get("amount", 0)
                bounties[loser_id]["amount"] = max(0, current_bounty - bounty_decrease)
            
            # Save bounty changes
            save_bounties(bounties)
            
            # Update stats
            await self.config.member(winner["member"]).wins.set(
                await self.config.member(winner["member"]).wins() + 1
            )
            await self.config.member(loser["member"]).losses.set(
                await self.config.member(loser["member"]).losses() + 1
            )
            
            # Update last active time
            current_time = datetime.utcnow().isoformat()
            await self.config.member(winner["member"]).last_active.set(current_time)
            await self.config.member(loser["member"]).last_active.set(current_time)
            
            # Announce results
            embed = discord.Embed(
                title="🏆 Battle Results",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="Winner",
                value=(
                    f"**{winner['name']}**\n"
                    f"+ `{bounty_increase:,}` Berries\n"
                    f"New Bounty: `{bounties[winner_id]['amount']:,}` Berries"
                ),
                inline=False
            )
            
            embed.add_field(
                name="Loser",
                value=(
                    f"**{loser['name']}**\n"
                    f"- `{bounty_decrease:,}` Berries\n"
                    f"New Bounty: `{bounties[loser_id]['amount']:,}` Berries"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Check achievements
            await self.check_achievements(winner["member"])
            await self.check_achievements(loser["member"])
            
        except Exception as e:
            logger.error(f"Error in battle rewards: {str(e)}")
            await ctx.send("❌ An error occurred while processing battle rewards!")

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
    
    async def apply_devil_fruit_effects(self, attacker, defender, damage, move_copy, turn_number=1):
        """Apply Devil Fruit effects to combat."""
        fruit_effect = None  # Initialize fruit_effect to None
        fruit = await self.config.member(attacker["member"]).devil_fruit()
        if not fruit:
            return damage, fruit_effect

        # Get fruit data from either Common or Rare categories
        fruit_data = DEVIL_FRUITS["Common"].get(fruit) or DEVIL_FRUITS["Rare"].get(fruit)
        if not fruit_data:
            return damage, fruit_effect

        effect_message = None
        fruit_type = fruit_data["type"]
        
        # Track fruit usage for achievements
        if "elements_used" not in attacker:
            attacker["elements_used"] = set()
        attacker["elements_used"].add(fruit_type)

        # Apply type-specific effects - Making sure move_copy is passed to all handlers
        if fruit_type == "Logia":
            damage, effect_message = await self._handle_logia_combat(attacker, defender, damage, fruit_data, turn_number, move_copy)
        elif "Zoan" in fruit_type:
            damage, effect_message = await self._handle_zoan_combat(attacker, defender, damage, fruit_data, turn_number, move_copy)
        elif fruit_type in ["Paramecia", "Special Paramecia"]:
            damage, effect_message = await self._handle_paramecia_combat(attacker, defender, damage, fruit_data, turn_number, move_copy)

        return damage, effect_message

    async def _create_devil_fruit_announcement(self, attacker, fruit_data, effect_message):
        """Create a dramatic Devil Fruit ability announcement."""
        fruit_type = fruit_data["type"]
        fruit_name = attacker["fruit"]

        # Create type-specific emoji and formatting
        type_formatting = {
            "Logia": "🌀",
            "Paramecia": "✨",
            "Special Paramecia": "💫",
            "Mythical Zoan": "🐉",
            "Ancient Zoan": "🦕",
            "Zoan": "🐾"
        }

        emoji = type_formatting.get(fruit_type, "⚔️")
        
        announcement = (
            f"{emoji} **DEVIL FRUIT ABILITY!** {emoji}\n"
            f"**{fruit_name}** Activated!\n"
            f"{effect_message}"
        )
        
        return announcement
    
    async def _handle_logia_combat(self, attacker, defender, damage, fruit_data, turn, move_copy):
        """Handle Logia-type combat effects."""
        effect = fruit_data["effect"]
        effect_message = None

        # Fire/Magma Logia
        if effect in ["fire", "magma"]:
            if random.random() < 0.4:  # 40% chance
                defender["status"]["burn"] += 2
                damage *= 2
                effect_message = (
                    f"🔥 **FLAME EMPEROR'S WRATH**! 🔥\n"
                    f"**{attacker['name']}**'s flames burn with devastating power using {move_copy['name']}!\n"
                    f"💥 Double Damage + Intense Burn!"
                )

        # Lightning Logia
        elif effect == "lightning":
            if random.random() < 0.2:
                defender["status"]["stun"] = True
                effect_message = (
                    f"⚡ **THUNDER GOD'S JUDGEMENT**! ⚡\n"
                    f"**{attacker['name']}** channels divine lightning!\n"
                    f"💫 Enemy Paralyzed!"
                )

        # Ice Logia
        elif effect == "ice":
            if random.random() < 0.25:
                defender["status"]["frozen"] = 2
                effect_message = (
                    f"❄️ **ABSOLUTE ZERO**! ❄️\n"
                    f"**{attacker['name']}** unleashes freezing power!\n"
                    f"🥶 Enemy Frozen Solid!"
                )

        # Light Logia
        elif effect == "light":
            if random.random() < 0.2:
                damage *= 2
                effect_message = (
                    f"✨ **SACRED YASAKANI**! ✨\n"
                    f"**{attacker['name']}** moves at light speed!\n"
                    f"⚡ Double Strike!"
                )

        # Darkness Logia
        elif effect == "darkness":
            absorbed = int(damage * 0.15)
            attacker["hp"] = min(100, attacker["hp"] + absorbed)
            effect_message = (
                f"🌑 **BLACK HOLE**! 🌑\n"
                f"**{attacker['name']}** commands darkness itself!\n"
                f"⚫ Absorbed {absorbed} HP!"
            )

        # Sand Logia
        elif effect == "sand":
            if random.random() < 0.1:
                drain = int(defender["hp"] * 0.1)
                defender["hp"] -= drain
                attacker["hp"] = min(100, attacker["hp"] + drain)
                effect_message = (
                    f"🏖️ **DESERT COFFIN**! 🏖️\n"
                    f"**{attacker['name']}** drains life through desert sands!\n"
                    f"💀 Absorbed {drain} HP!"
                )
                
        # Ice Logia
        elif effect == "ice":
            if random.random() < 0.25:
                defender["status"]["frozen"] = 2
                effect_message = (
                    f"❄️ **ABSOLUTE ZERO**! ❄️\n"
                    f"**{attacker['name']}** unleashes freezing power!\n"
                    f"🥶 Enemy Frozen Solid!"
                )

        # Light Logia
        elif effect == "light":
            damage *= 1.2
            if random.random() < 0.2:
                damage *= 2
                effect_message = (
                    f"✨ **SACRED YASAKANI**! ✨\n"
                    f"**{attacker['name']}** moves at light speed!\n"
                    f"⚡ Double Strike at Light Speed!"
                )

        # Darkness Logia
        elif effect == "darkness":
            absorbed = int(damage * 0.15)
            attacker["hp"] = min(100, attacker["hp"] + absorbed)
            effect_message = (
                f"🌑 **BLACK HOLE**! 🌑\n"
                f"**{attacker['name']}** commands darkness itself!\n"
                f"⚫ Absorbed {absorbed} HP Through Void!"
            )

        # Magma Logia
        elif effect == "magma":
            defender["status"]["burn"] += 3
            effect_message = (
                f"🌋 **GREAT ERUPTION**! 🌋\n"
                f"**{attacker['name']}** unleashes molten destruction!\n"
                f"🔥 Inflicts Devastating Burns!"
            )

        # Forest Logia
        elif effect == "forest":
            if random.random() < 0.3:
                defender["status"]["movement_restricted"] = 2
                effect_message = (
                    f"🌳 **FOREST PRISON**! 🌳\n"
                    f"**{attacker['name']}** binds with ancient roots!\n"
                    f"🌿 Enemy Movement Restricted!"
                )

        # Wind Logia
        elif effect == "wind":
            if random.random() < 0.2:
                damage = 0
                effect_message = (
                    f"🌪️ **DIVINE WIND**! 🌪️\n"
                    f"**{attacker['name']}** becomes one with the wind!\n"
                    f"💨 Attack Completely Evaded!"
                )

        return damage, effect_message

    async def _handle_zoan_combat(self, attacker, defender, damage, fruit_data, turn, move_copy):
        """Handle Zoan-type combat effects."""
        effect = fruit_data["effect"]
        effect_message = None

        # Mythical Zoan Types
        if "Model Phoenix" in effect:
            if turn % 3 == 0:
                heal = int(attacker["hp"] * 0.1)
                attacker["hp"] = min(100, attacker["hp"] + heal)
                effect_message = (
                    f"🦅 **FLAMES OF RESTORATION**! 🦅\n"
                    f"**{attacker['name']}** rises from the ashes!\n"
                    f"💚 Regenerated {heal} HP!"
                )

        elif "Model Azure Dragon" in effect:
            damage *= 1.3
            effect_message = (
                f"🐉 **AZURE DRAGON'S MIGHT**! 🐉\n"
                f"**{attacker['name']}** channels celestial power!\n"
                f"💥 Damage Enhanced!"
            )

        elif "Model Nika" in effect:
            boost_type = random.choice(["attack", "speed", "defense"])
            if boost_type == "attack":
                damage *= 1.5
                effect_message = (
                    f"🔥 **NIKA'S AWAKENING**! 🔥\n"
                    f"**{attacker['name']}** unleashes freedom's power!\n"
                    f"💥 Attack Enhanced!"
                )
            elif boost_type == "defense":
                attacker["status"]["protected"] = True
                effect_message = (
                    f"✨ **NIKA'S LIBERATION**! ✨\n"
                    f"**{attacker['name']}** moves with complete freedom!\n"
                    f"🛡️ Defense Boosted!"
                )

        # Ancient Zoan Types
        elif "Model Spinosaurus" in effect:
            if turn % 2 == 0:
                damage *= 1.4
                effect_message = (
                    f"🦕 **ANCIENT PREDATOR**! 🦕\n"
                    f"**{attacker['name']}** channels prehistoric might!\n"
                    f"💥 Damage Amplified!"
                )

        return damage, effect_message

    async def _handle_paramecia_combat(self, attacker, defender, damage, fruit_data, turn, move_copy):
        """Handle Paramecia-type combat effects."""
        effect = fruit_data["effect"]
        effect_message = None

        # Rubber Paramecia
        if effect == "rubber":
            if move_copy.get("type") == "strong":
                damage *= 1.5
                effect_message = (
                    f"💫 **RUBBER ENHANCEMENT**! 💫\n"
                    f"**{attacker['name']}** stretches for extra power!\n"
                    f"💥 Attack Amplified!"
                )

        # Surgical Paramecia
        elif effect == "surgical":
            if random.random() < 0.2:
                defender["status"]["stun"] = True
                effect_message = (
                    f"🏥 **ROOM: SHAMBLES**! 🏥\n"
                    f"**{attacker['name']}** performs surgical precision!\n"
                    f"✨ Enemy Disoriented!"
                )

        # Quake Paramecia
        elif effect == "quake":
            damage *= 1.8
            effect_message = (
                f"🌋 **SEISMIC FORCE**! 🌋\n"
                f"**{attacker['name']}** shatters reality!\n"
                f"💥 Massive Damage Boost!"
            )

        # Barrier Paramecia
        elif effect == "barrier":
            if random.random() < 0.4:
                attacker["status"]["protected"] = True
                effect_message = (
                    f"🛡️ **BARRIER FORTRESS**! 🛡️\n"
                    f"**{attacker['name']}** creates an impenetrable wall!\n"
                    f"✨ Defense Activated!"
                )

        # String Paramecia
        elif effect == "string":
            if random.random() < 0.3:
                defender["status"]["movement_restricted"] = 2
                effect_message = (
                    f"🕸️ **STRING BIND**! 🕸️\n"
                    f"**{attacker['name']}** restricts the enemy's movement!\n"
                    f"⛓️ Enemy Movement Limited!"
                )

        # Mochi Paramecia
        elif effect == "mochi":
            if turn % 4 == 0:
                damage *= 1.5
                effect_message = (
                    f"🍡 **MOCHI STRIKE**! 🍡\n"
                    f"**{attacker['name']}** launches a powerful mochi attack!\n"
                    f"💥 Special Turn Damage Boost!"
                )

        return damage, effect_message

    
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
    @commands.admin_or_permissions(administrator=True)  # ✅ Admin-only command
    async def resetstats(self, ctx, member: discord.Member = None):
        """Reset all users' stats (default) or reset a specific user with `[p]resetstats @user`."""
    
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
        """View or equip a previously unlocked title, including exclusive ones."""
        user = ctx.author
        bounty = (await self.config.guild(ctx.guild).bounties()).get(str(user.id), {}).get("amount", 0)

        # Get all normal unlocked titles based on bounty
        unlocked_titles = {t for t, c in TITLES.items() if bounty >= c["bounty"]}

        # ✅ Add hidden & exclusive titles that have been unlocked, avoiding duplicates
        user_titles = await self.config.member(user).titles()
        unlocked_titles.update(user_titles)  # ✅ Ensures no duplicate titles

        # ✅ Fetch `current_title` (NOT `equipped_title`)
        equipped_title = await self.config.member(user).current_title()

        # ✅ Convert all titles to lowercase for case-insensitive comparison
        unlocked_titles_lower = {t.lower(): t for t in unlocked_titles}

        # ✅ Ensure the equipped title is still valid
        if equipped_title and equipped_title.lower() in unlocked_titles_lower:
            equipped_title = unlocked_titles_lower[equipped_title.lower()]
        else:
            equipped_title = None  # Reset if the title isn't in the unlocked list
            await self.config.member(user).current_title.set(None)  # ✅ Fix stored title

        if not unlocked_titles:
            return await ctx.send("🏴‍☠️ You haven't unlocked any titles yet!")

        if action == "equip" and title:
            if title.lower() not in unlocked_titles_lower:
                return await ctx.send(f"❌ You haven't unlocked the title `{title}` yet!")

            await self.config.member(user).current_title.set(unlocked_titles_lower[title.lower()])
            return await ctx.send(f"✅ **{user.display_name}** has equipped the title `{unlocked_titles_lower[title.lower()]}`!")

        # Show available titles
        embed = discord.Embed(title=f"🏆 {user.display_name}'s Titles", color=discord.Color.gold())
        embed.add_field(name="Unlocked Titles", value="\n".join(unlocked_titles) or "None", inline=False)
        embed.add_field(name="Currently Equipped", value=equipped_title or "None Equipped", inline=False)
        embed.set_footer(text='Use [p]equiptitle "<title>" to set a title!')

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
        """Check a player's deathmatch stats, including exclusive titles."""
        member = member or ctx.author
    
        # Retrieve stats from config
        stats = await self.config.member(member).all()
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
    
        # ✅ Retrieve bounty from the same source as `mostwanted`
        bounties = await self.config.guild(ctx.guild).bounties()
        bounty = bounties.get(str(member.id), {}).get("amount", 0)
    
        # ✅ Get the correct title based on bounty
        title = self.get_bounty_title(bounty) or "Unknown Pirate"
    
        # ✅ Check for hidden/exclusive titles and prevent NoneType errors
        hidden_titles = await self.config.member(member).titles() or []
        if hidden_titles:
            title += f" / {', '.join(hidden_titles)}"
    
        # Create embed
        embed = discord.Embed(
            title=f"⚔️ Deathmatch Stats for {member.display_name}",
            color=discord.Color.red()
        )
        embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
        embed.add_field(name="💀 Losses", value=str(losses), inline=True)
        embed.add_field(name="💰 Bounty", value=f"{bounty:,} Berries", inline=True)
        embed.add_field(name="🎖️ Titles", value=title, inline=False)
    
        await ctx.send(embed=embed)

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
        achievements = await self.config.member(user).achievements()

        if not achievements:
            return await ctx.send("Ye have no achievements yet! Win battles and increase yer bounty!")

        embed = discord.Embed(title=f"🏆 {user.display_name}'s Achievements", color=discord.Color.green())

        for achievement in achievements:
            embed.add_field(name=achievement, value="✅ Unlocked!", inline=False)

        await ctx.send(embed=embed)

    async def check_achievements(self, member):
        """Check and unlock achievements for the member."""
        stats = await self.config.member(member).all()  # Get stats inside the function
        user_achievements = stats.get("achievements", [])
        unlocked_titles = stats.get("titles", [])
        unlocked = []
    
        for key, data in ACHIEVEMENTS.items():
            if key in user_achievements:
                continue  # Already unlocked
    
            current_stat = stats.get(data["condition"], 0)  # Use .get() to avoid KeyError
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
