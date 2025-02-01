from redbot.core import commands, Config
import discord
import random
import asyncio
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import logging
import aiohttp
import io  # Required for handling images

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

    # ------------------ Bounty System ------------------

    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id in bounties:
            return await ctx.send("Ye already have a bounty, ye scallywag!")

        bounties[user_id] = {"amount": random.randint(50, 100)}
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])
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
        bounties = await self.config.guild(ctx.guild).bounties()
        
        if not bounties:  # Check if no bounties exist
            return await ctx.send("🏴‍☠️ No bounties have been claimed yet! Be the first to start your journey with `.startbounty`.")

        sorted_bounties = sorted(bounties.items(), key=lambda x: x[1]["amount"], reverse=True)
        pages = [sorted_bounties[i:i + 10] for i in range(0, len(sorted_bounties), 10)]
        
        current_page = 0
        embed = await self.create_leaderboard_embed(pages[current_page])
        message = await ctx.send(embed=embed)

        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

                if str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % len(pages)
                elif str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % len(pages)

                embed = await self.create_leaderboard_embed(pages[current_page])  # Add await here!
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
        current_fruit = await self.config.member(user).devil_fruit()

        if current_fruit:
            return await ctx.send(f"❌ You already have the `{current_fruit}`! You can only eat one Devil Fruit!")

        # ✅ Get all rare fruits currently taken
        all_taken_fruits = set()
        all_bounties = await self.config.all_members(ctx.guild)

        for user_id, data in all_bounties.items():
            if "devil_fruit" in data and data["devil_fruit"] in DEVIL_FRUITS["Rare"]:
                all_taken_fruits.add(data["devil_fruit"])

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

        # ✅ Save the fruit to the player's profile
        await self.config.member(user).devil_fruit.set(new_fruit)

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

    
        # Assign the fruit to the player
        await self.config.member(user).devil_fruit.set(new_fruit)

    @commands.command()
    async def removefruit(self, ctx, member: discord.Member = None):
        """Remove a user's Devil Fruit. Owners remove for free, others pay 1,000,000 berries."""
        user = ctx.author
        member = member or user  # If no member is provided, remove for the command user
        is_owner = await self.bot.is_owner(user)  # ✅ Check if the user is the bot owner

        fruit = await self.config.member(member).devil_fruit()
        if not fruit:
            return await ctx.send(f"🍏 **{member.display_name}** has no Devil Fruit to remove!")

        # ✅ Owners remove the fruit for free, skipping the cost check
        if is_owner:
            await self.config.member(member).devil_fruit.set(None)
            return await ctx.send(f"🛡️ **{user.display_name}** removed `{fruit}` from **{member.display_name}** for free!")

        # Normal users must pay
        berries = await self.config.member(user).berries()
        cost = 1_000_000

        if berries < cost:
            return await ctx.send(f"❌ You don't have enough berries! You need **{cost:,}** berries to remove your Devil Fruit.")

        # Deduct cost and remove the fruit
        await self.config.member(user).berries.set(berries - cost)
        await self.config.member(member).devil_fruit.set(None)

        await ctx.send(
            f"💰 **{user.display_name}** has paid **{cost:,}** berries to remove `{fruit}` from **{member.display_name}**!\n"
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
        all_fruits = {name.lower(): name for name in {**DEVIL_FRUITS["Common"], **DEVIL_FRUITS["Rare"]}}  # Convert keys to lowercase

        if fruit.lower() not in all_fruits:
            return await ctx.send("❌ That Devil Fruit does not exist in the current list.")

        current_fruit = await self.config.member(member).devil_fruit()
        if current_fruit:
            return await ctx.send(f"❌ **{member.display_name}** already has `{current_fruit}`! They must remove it first.")

        # Assign the correctly formatted fruit name
        fruit_name = all_fruits[fruit.lower()]
        await self.config.member(member).devil_fruit.set(fruit_name)

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
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def bountyhunt(self, ctx, target: discord.Member):
        """Attempt to steal a percentage of another user's bounty."""
        hunter = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        
        hunter_id = str(hunter.id)
        target_id = str(target.id)

        if hunter_id not in bounties or target_id not in bounties:
            return await ctx.send("Both you and your target must have a bounty to participate!")

        if hunter_id == target_id:
            return await ctx.send("Ye can't hunt yer own bounty, ye scallywag!")

        hunter_bounty = bounties[hunter_id]["amount"]
        target_bounty = bounties[target_id]["amount"]

        if target_bounty < 1000:
            return await ctx.send(f"{target.display_name} is too broke to be worth hunting!")

        # 50% chance to win
        success = random.choice([True, False])
        steal_amount = random.randint(5, 20) / 100 * target_bounty  # 5-20% of target bounty

        if success:
            stolen_bounty = int(steal_amount)
        
            # Update winner's bounty
            bounties[hunter_id]["amount"] += stolen_bounty
        
            # Deduct from loser and prevent negative bounty
            bounties[target_id]["amount"] = max(0, bounties[target_id]["amount"] - stolen_bounty)
        
            # Save the updated bounties
            await self.config.guild(ctx.guild).bounties.set(bounties)

            # Track the last active time for both players
            await self.config.member(ctx.author).last_active.set(datetime.utcnow().isoformat())
            await self.config.member(target).last_active.set(datetime.utcnow().isoformat())

            # ✅ Unlock "The Bounty Hunter" (Steal 100,000 Berries)
            current_stolen = await self.config.member(hunter).bounty_hunted() or 0  # ✅ Ensures no NoneType error
            total_stolen = current_stolen + int(steal_amount)
            
            await self.config.member(hunter).bounty_hunted.set(total_stolen)
            
            if total_stolen >= 100_000:
                unlocked_titles = await self.config.member(hunter).titles()
                if "The Bounty Hunter" not in unlocked_titles:
                    unlocked_titles.append("The Bounty Hunter")
                    await self.config.member(hunter).titles.set(unlocked_titles)
                    await ctx.send(f"💰 **{hunter.display_name}** has unlocked the secret title: `The Bounty Hunter`!")


        
            # Notify the results
            await ctx.send(
                f"🏴‍☠️ **{hunter.display_name}** successfully hunted **{target.display_name}** "
                f"and stole `{stolen_bounty:,} Berries`!\n"
                f"💰 **New Winner Bounty:** `{bounties[hunter_id]['amount']:,} Berries`\n"
                f"💀 **New Loser Bounty:** `{bounties[target_id]['amount']:,} Berries`"
            )

        
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

        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(member.id)

        if user_id not in bounties:
            return await ctx.send(f"{member.display_name} needs to start their bounty journey first by typing `.startbounty`!")

        bounties = await self.config.guild(ctx.guild).bounties()
        bounty_amount = bounties.get(str(member.id), {}).get("amount", 0)
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
        
        wanted_poster_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/wanted.png"
        font_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/onepiece.ttf"  # ✅ Define font path
    
        # Open the local wanted poster template
        poster_image = Image.open(wanted_poster_path)
        
        # Open the user's avatar image
        avatar_image = Image.open(io.BytesIO(avatar_data)).resize((625, 455))
        avatar_image = avatar_image.convert("RGBA")
    
        # Paste the avatar onto the wanted poster
        poster_image.paste(avatar_image, (65, 223), avatar_image)
    
        # Draw text (name & bounty)
        draw = ImageDraw.Draw(poster_image)
    
        # ✅ Define font before using it
        try:
            font = ImageFont.truetype(font_path, 100)
        except OSError:
            return "⚠️ Font file not found! Ensure `onepiece.ttf` exists in the fonts folder."
    
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
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def berryflip(self, ctx, bet: int):
        """Flip a coin to potentially increase your bounty."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        current_bounty = bounties[user_id]["amount"]

        if bet < 500 or bet > 5000:
            return await ctx.send("Ye can only bet between 500 and 5000 Berries, ye scallywag!")

        if bet > current_bounty:
            return await ctx.send("Ye can't bet more than yer current bounty, ye scallywag!")

        flip_result = random.choice(["heads", "tails"])

        if flip_result == "heads":
            bounties[user_id]["amount"] += bet
            await ctx.send(f"🪙 The coin landed on heads! Ye won {bet:,} Berries! Yer new bounty is {bounties[user_id]['amount']:,} Berries!")
        else:
            bounties[user_id]["amount"] -= bet
            await ctx.send(f"🪙 The coin landed on tails! Ye lost {bet:,} Berries! Yer new bounty is {bounties[user_id]['amount']:,} Berries!")

        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])

        new_bounty = bounties[user_id]["amount"]
        new_title = self.get_bounty_title(new_bounty)

        # Announce if the user reaches a significant rank
        if new_bounty >= 900000000:
            await self.announce_rank(ctx.guild, user, new_title)

        logger.info(f"{user.display_name} used berryflip and now has a bounty of {new_bounty:,} Berries.")

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
    @commands.cooldown(1, 86400, commands.BucketType.user)
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
        
    async def announce_top_three(self, ctx):
        """Announce the top 3 most wanted pirates."""
        bounties = await self.config.guild(ctx.guild).bounties()
        sorted_bounties = sorted(bounties.items(), key=lambda x: x[1]["amount"], reverse=True)[:3]

        embed = discord.Embed(title="🏆 Most Wanted Pirates", color=discord.Color.red())
        for i, (user_id, bounty) in enumerate(sorted_bounties, start=1):
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(int(user_id))
            if user:
                embed.add_field(name=f"{i}. {user.display_name}", value=f"{bounty['amount']:,} Berries", inline=False)

        top_channel = discord.utils.get(ctx.guild.text_channels, name="bounty-board")
        if top_channel:
            await top_channel.send(embed=embed)


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
    def generate_health_bar(self, current_hp: int, max_hp: int = 100, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"

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
        if ctx.channel.id in self.active_channels:
            return await ctx.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")

        # ✅ Mark the channel as active
        self.active_channels.add(ctx.channel.id)

        # ✅ Generate fight card
        fight_card = self.generate_fight_card(ctx.author, opponent)

        # ✅ Send the dynamically generated fight card image
        await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))

        # ✅ Call the fight function and update bounty only for the initiator
        await self.fight(ctx, ctx.author, opponent)

        # ✅ Mark the channel as inactive
        self.active_channels.remove(ctx.channel.id)

        
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
        """Override the fight method to include environmental hazards."""
        environment = self.choose_environment()
        environment_effect = ENVIRONMENTS[environment]["effect"]

        # Announce the environment
        await ctx.send(f"🌍 The battle takes place in **{environment}**: {ENVIRONMENTS[environment]['description']}")

        # ✅ Get Devil Fruit info for both fighters
        attacker_fruit = await self.config.member(challenger).devil_fruit()
        defender_fruit = await self.config.member(opponent).devil_fruit()

        attacker_bonus = DEVIL_FRUITS["Common"].get(attacker_fruit) or DEVIL_FRUITS["Rare"].get(attacker_fruit)
        defender_bonus = DEVIL_FRUITS["Common"].get(defender_fruit) or DEVIL_FRUITS["Rare"].get(defender_fruit)

        if attacker_bonus:
            await ctx.send(f"🔥 **{challenger.display_name}** is using `{attacker_fruit}`! Bonus: {attacker_bonus['bonus']}")
        if defender_bonus:
            await ctx.send(f"❄️ **{opponent.display_name}** is using `{defender_fruit}`! Bonus: {defender_bonus['bonus']}")

        # Initialize player data
        challenger_hp = 100
        opponent_hp = 100
        challenger_status = {"burn": 0, "stun": False, "block_active": False, "accuracy_reduction": 0, "accuracy_turns": 0}
        opponent_status = {"burn": 0, "stun": False, "block_active": False, "accuracy_reduction": 0, "accuracy_turns": 0}

        # Create the initial embed
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Deathmatch ⚔️",
            description=f"Battle begins between **{challenger.display_name}** and **{opponent.display_name}**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="\u200b",
            value=f"**{challenger.display_name}**\n{self.generate_health_bar(challenger_hp)} {challenger_hp}/100",
            inline=True,
        )
        embed.add_field(
            name="\u200b",
            value=f"**{opponent.display_name}**\n{self.generate_health_bar(opponent_hp)} {opponent_hp}/100",
            inline=True,
        )
        embed.add_field(name="Turn", value=f"It's **{challenger.display_name}**'s turn!", inline=False)
        embed.set_footer(text="Actions are influenced by the environment!")
        message = await ctx.send(embed=embed)

        # Player data structure
        players = [
            {"name": challenger.display_name, "hp": challenger_hp, "status": challenger_status, "member": challenger},
            {"name": opponent.display_name, "hp": opponent_hp, "status": opponent_status, "member": opponent},
        ]
        turn_index = 0

        # Initialize stats
        attacker_stats = await self.config.member(challenger).all()
        defender_stats = await self.config.member(opponent).all()

        # Battle loop
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            if self.battle_stopped:
                embed.title = "⚠️ Battle Stopped!"
                embed.description = "The fight has been forcibly ended! No winner was declared."
                embed.color = discord.Color.red()
                embed.set_footer(text="The battle was interrupted.")
                await message.edit(embed=embed)
                
                self.battle_stopped = False  # Reset for the next battle
                return

            # Apply environmental hazard
            hazard_message = await self.apply_environmental_hazard(environment, players)
            if hazard_message:
                embed.description = f"⚠️ **Environmental Hazard!** {hazard_message}"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Define attacker and defender
            attacker = players[turn_index]
            defender = players[1 - turn_index]  # Now defender is correctly assigned
            
            # Check if the attacker has a Devil Fruit
            attacker_fruit = await self.config.member(attacker["member"]).devil_fruit()
            if attacker_fruit and attacker_fruit in DEVIL_FRUITS:
                fruit_effect = DEVIL_FRUITS[attacker_fruit]["effect"]
            
                if fruit_effect == "fire":
                    burn_chance = random.randint(1, 100)
                    if burn_chance <= 30:  # 30% chance to burn opponent
                        defender["status"]["burn"] += 2
                        await ctx.send(f"🔥 **{attacker['name']}**'s `{attacker_fruit}` burned **{defender['name']}**!")
            
                elif fruit_effect == "rubber":
                    blunt_damage = random.randint(1, 100)
                    if blunt_damage <= 50:  # 50% chance to negate blunt attacks
                        damage = 0
                        await ctx.send(f"💪 **{attacker['name']}**'s `{attacker_fruit}` made them immune to blunt attacks!")
            
                elif fruit_effect == "surgical":
                    swap_chance = random.randint(1, 100)
                    if swap_chance <= 10:  # 10% chance to swap places
                        players[0], players[1] = players[1], players[0]
                        await ctx.send(f"⚡ **{attacker['name']}**'s `{attacker_fruit}` swapped places!")
            
                elif fruit_effect == "darkness":
                    absorb_chance = random.randint(1, 100)
                    if absorb_chance <= 10:  # 10% chance to absorb enemy attack
                        attacker["hp"] += 10
                        await ctx.send(f"🌑 **{attacker['name']}**'s `{attacker_fruit}` absorbed enemy damage!")
            
            # Apply burn damage AFTER defining `defender`
            burn_damage = await self.apply_burn_damage(defender)
            if burn_damage > 0:
                embed.description = f"🔥 **{defender['name']}** takes `{burn_damage}` burn damage from fire stacks!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Skip turn if stunned
            if defender["status"].get("stun"):
                defender["status"]["stun"] = False  # Stun only lasts one turn
                embed.description = f"⚡ **{defender['name']}** is `stunned` and cannot act!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                turn_index = 1 - turn_index
                continue

            # Select move
            move = random.choice(MOVES)

            # Apply environmental effects
            environment_effect(move, attacker)

            # Calculate damage
            damage = self.calculate_damage(move["type"])

            # Apply block logic
            if defender["status"].get("block_active", False):
                damage = max(0, damage - 10)  # Reduce damage by block amount
                await self.config.member(defender["member"]).blocks.set(
                    await self.config.member(defender["member"]).blocks() + 1
                )

            # Apply effects
            await self.apply_effects(move, attacker, defender)

            # Highlighted move effects in message
            effects_highlight = []
            if "burn" in move.get("effect", ""):
                effects_highlight.append("🔥 **Burn!**")
            if "crit" in move.get("effect", ""):
                effects_highlight.append("✨ **Critical Hit!**")
            if "heal" in move.get("effect", ""):
                effects_highlight.append("💚 **Heal!**")
            if "stun" in move.get("effect", ""):
                effects_highlight.append("⚡ **Stun!**")

            effects_display = "\n".join(effects_highlight)

            # Apply damage and update stats
            defender["hp"] = max(0, defender["hp"] - damage)
            embed.description = (
                f"**{attacker['name']}** used **{move['name']}**: {move['description']}\n"
                f"{effects_display}\n"
                f"Dealt **{damage}** damage to **{defender['name']}**!"
            )
            embed.set_field_at(
                0,
                name="\u200b",
                value=f"**{players[0]['name']}**\n{self.generate_health_bar(players[0]['hp'])} {players[0]['hp']}/100",
                inline=True,
            )
            embed.set_field_at(
                1,
                name="\u200b",
                value=f"**{players[1]['name']}**\n{self.generate_health_bar(players[1]['hp'])} {players[1]['hp']}/100",
                inline=True,
            )
            embed.set_field_at(
                2,
                name="Turn",
                value=f"It's **{players[1 - turn_index]['name']}**'s turn!",
                inline=False,
            )
            await message.edit(embed=embed)
            await asyncio.sleep(2)

            # Update damage stats for the attacker
            await self.config.member(attacker["member"]).damage_dealt.set(
                await self.config.member(attacker["member"]).damage_dealt() + damage
            )

            # Update stats for both players
            await self.update_stats(attacker, defender, damage, move, attacker_stats)
            await self.update_stats(defender, attacker, burn_damage, {"effect": "burn"}, defender_stats)

            # Switch turn
            turn_index = 1 - turn_index

        # Determine winner
        winner = players[0] if players[0]["hp"] > 0 else players[1]
        loser = players[1] if players[0]["hp"] > 0 else players[0]

        # Track the last active time for both players
        await self.config.member(challenger).last_active.set(datetime.utcnow().isoformat())
        await self.config.member(opponent).last_active.set(datetime.utcnow().isoformat())

        # Track total wins
        total_wins = await self.config.member(winner["member"]).wins()
        
        # ✅ Unlock "The Unbreakable" (10 wins without losing)
        if total_wins >= 10:
            unlocked_titles = await self.config.member(winner["member"]).titles()
            if "The Unbreakable" not in unlocked_titles:
                unlocked_titles.append("The Unbreakable")
                await self.config.member(winner["member"]).titles.set(unlocked_titles)
                await ctx.send(f"🏆 **{winner['name']}** has unlocked the secret title: `The Unbreakable`!")
        
        # ✅ Unlock "The Underdog" (Defeat an opponent with 5x your bounty)
        loser_bounty = await self.config.member(loser["member"]).bounty()
        winner_bounty = await self.config.member(winner["member"]).bounty()
        
        # ✅ Ensure unlocked_titles is always defined before using it
        unlocked_titles = await self.config.member(winner["member"]).titles() or []
        
        if "The Underdog" not in unlocked_titles:
            unlocked_titles.append("The Underdog")
            await self.config.member(winner["member"]).titles.set(unlocked_titles)
            await ctx.send(f"🏆 **{winner['name']}** has unlocked the secret title: `The Underdog`!")

        # ✅ Unlock "The Ghost" (Evade 3 attacks in a row)
        if defender["status"].get("evade_streak", 0) >= 3:
            unlocked_titles = await self.config.member(defender["member"]).titles()
            if "The Ghost" not in unlocked_titles:
                unlocked_titles.append("The Ghost")
                await self.config.member(defender["member"]).titles.set(unlocked_titles)
                await ctx.send(f"👻 **{defender['name']}** has unlocked the secret title: `The Ghost`!")
        
        # ✅ Unlock "The Berserker" (Deal 100 damage in one attack)
        if damage >= 100:
            unlocked_titles = await self.config.member(attacker["member"]).titles()
            if "The Berserker" not in unlocked_titles:
                unlocked_titles.append("The Berserker")
                await self.config.member(attacker["member"]).titles.set(unlocked_titles)
                await ctx.send(f"🔥 **{attacker['name']}** has unlocked the secret title: `The Berserker`!")
        
                
        # Increase the winner's bounty (random amount between 1,000 and 3,000 Berries)
        bounty_increase = random.randint(1000, 2000)
        winner_id = str(winner["member"].id)
        
        # Get current bounty and update it
        bounties = await self.config.guild(ctx.guild).bounties()
        bounties[winner_id] = bounties.get(winner_id, {"amount": 0})
        bounties[winner_id]["amount"] += bounty_increase
        
        # Save the new bounty
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(winner["member"]).bounty.set(bounties[winner_id]["amount"])

        # Check if the user unlocks a new title
        new_title = self.get_bounty_title(winner_bounty)
        current_title = await self.config.member(winner["member"]).equipped_title()
        
        if new_title != current_title:
            await self.config.member(winner["member"]).equipped_title.set(new_title)
            await ctx.send(f"🏴‍☠️ **{winner['name']}** has earned the new title: `{new_title}`!")
            
        # Update the existing embed to show the final result
        embed.title = "🏆 Victory!"
        embed.description = (
            f"**{winner['name']}** has won the battle!\n\n"
            f"💰 **Bounty Increased:** `{bounty_increase:,} Berries`\n"
            f"🏴‍☠️ **New Bounty:** `{bounties[winner_id]['amount']:,} Berries`"
        )
        embed.color = discord.Color.gold()
        embed.set_field_at(2, name="⚔️ Battle Over", value=f"Winner: **{winner['name']}**", inline=False)
        embed.set_footer(text="The battle has ended.")
        
        await message.edit(embed=embed)  # ✅ Instead of sending a new embed, update the existing one.

        # Update stats for the winner
        await self.check_achievements(winner["member"])
        # Update stats for the loser
        await self.check_achievements(loser["member"])
        # Update stats for the winner and loser
        await self.config.member(winner["member"]).wins.set(
            await self.config.member(winner["member"]).wins() + 1
        )
        await self.config.member(loser["member"]).losses.set(
            await self.config.member(loser["member"]).losses() + 1
        )

        # Decrease the loser's bounty (random amount between 500 and 1500 Berries)
        bounty_decrease = random.randint(500, 1500)
        loser_id = str(loser["member"].id)
        
        # Get current bounty and update it
        bounties[loser_id] = bounties.get(loser_id, {"amount": 0})
        bounties[loser_id]["amount"] = max(0, bounties[loser_id]["amount"] - bounty_decrease)
        
        # Save the new bounty
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(loser["member"]).bounty.set(bounties[loser_id]["amount"])

        # Update the existing embed to show the final result for the loser
        embed.add_field(
            name="💀 Defeat!",
            value=(
                f"**{loser['name']}** has lost the battle!\n\n"
                f"💸 **Bounty Decreased:** `{bounty_decrease:,} Berries`\n"
                f"🏴‍☠️ **New Bounty:** `{bounties[loser_id]['amount']:,} Berries`"
            ),
            inline=False,
        )
        
        await message.edit(embed=embed)
        
    def generate_health_bar(self, current_hp: int, max_hp: int = 100, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🟩" * filled_length + "⬜" * (length - filled_length)
        return f"{bar}"

    async def apply_burn_damage(self, player: dict) -> int:
        """Apply burn damage to a player based on their burn stacks."""
        burn_stacks = player["status"].get("burn", 0)
        if burn_stacks > 0:
            burn_damage = 5 * burn_stacks
            player["hp"] = max(0, player["hp"] - burn_damage)
            player["status"]["burn"] = max(0, burn_stacks - 1)
            return burn_damage
        return 0

    async def update_stats(self, attacker, defender, damage, move, stats):
        """Update the statistics for achievements and overall tracking."""
        if damage >= 30:  # Big hit condition
            stats["big_hit"] = stats.get("big_hit", 0) + 1
        if move.get("effect") == "burn":
            stats["burns_applied"] = stats.get("burns_applied", 0) + 1
        if defender["hp"] <= 0 and stats.get("clutch_block", 0) == 0:  # Clutch block logic
            stats["clutch_block"] = 1
        stats["damage_dealt"] = stats.get("damage_dealt", 0) + damage
        stats["total_damage_dealt"] = stats.get("total_damage_dealt", 0) + damage

    async def reset_player_stats(self, member):
        """Reset a player's statistics for testing or fairness."""
        await self.config.member(member).set({"wins": 0, "losses": 0, "damage_dealt": 0, "blocks": 0, "achievements": []})

    async def reset_all_stats(self, guild):
        """Reset all statistics in the guild."""
        all_members = await self.config.all_members(guild)
        for member_id in all_members:
            member = guild.get_member(member_id)
            if member:
                await self.reset_player_stats(member)
            
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

    async def cog_command_error(self, ctx, error):
        """Handles errors in this cog to prevent duplicate cooldown messages."""
        
        if isinstance(error, commands.CommandOnCooldown):
            remaining = error.retry_after
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
    
            if hours > 0:
                cooldown_message = f"⏳ This command is on cooldown. Try again in {hours} hour(s) {minutes} minute(s)."
            elif minutes > 0:
                cooldown_message = f"⏳ This command is on cooldown. Try again in {minutes} minute(s) {seconds} seconds."
            else:
                cooldown_message = f"⏳ This command is on cooldown. Try again in {seconds} seconds."
    
            return await ctx.send(cooldown_message)  # ✅ Ensures only ONE message is sent
    
        await ctx.send(f"❌ An error occurred: {error}")  # ✅ Generic error handler

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
    await bot.add_cog(BountyBattle(bot))

