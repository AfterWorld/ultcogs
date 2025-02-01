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
    "Gomu Gomu no Mi": {"type": "Paramecia", "effect": "rubber", "bonus": "Immune to blunt attacks"},
    "Mera Mera no Mi": {"type": "Logia", "effect": "fire", "bonus": "Fire attacks do double damage"},
    "Ope Ope no Mi": {"type": "Paramecia", "effect": "surgical", "bonus": "Can switch places once per battle"},
    "Yami Yami no Mi": {"type": "Logia", "effect": "darkness", "bonus": "Absorbs enemy attacks 10% of the time"},
    "Hie Hie no Mi": {"type": "Logia", "effect": "ice", "bonus": "Freezes opponent, reducing their speed"},
    "Goro Goro no Mi": {"type": "Logia", "effect": "lightning", "bonus": "20% chance to stun opponent with lightning"},
    "Bari Bari no Mi": {"type": "Paramecia", "effect": "barrier", "bonus": "Blocks 50% of damage every 3 turns"},
    "Bomu Bomu no Mi": {"type": "Paramecia", "effect": "explosion", "bonus": "Explosive attacks deal 30% extra damage"},
    "Moku Moku no Mi": {"type": "Logia", "effect": "smoke", "bonus": "15% chance to dodge physical attacks"},
    "Suna Suna no Mi": {"type": "Logia", "effect": "sand", "bonus": "10% chance to drain enemy’s HP"},
    "Tori Tori no Mi: Model Phoenix": {"type": "Mythical Zoan", "effect": "phoenix", "bonus": "Heals 10% HP every 3 turns"},
    "Uo Uo no Mi: Model Seiryu": {"type": "Mythical Zoan", "effect": "dragon", "bonus": "30% stronger attacks in battles"},
    "Zushi Zushi no Mi": {"type": "Paramecia", "effect": "gravity", "bonus": "Can stun enemy with gravity 20% of the time"},
    "Neko Neko no Mi: Model Leopard": {"type": "Zoan", "effect": "leopard", "bonus": "20% increased speed and agility"},
    "Hito Hito no Mi: Model Nika": {"type": "Mythical Zoan", "effect": "nika", "bonus": "Randomly boosts attack, speed, or defense"},
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

        # Store both bounty and deathmatch stats
        default_member = {
            "bounty": 0,
            "last_daily_claim": None,
            "wins": 0,
            "losses": 0,
            "damage_dealt": 0,
            "achievements": [],
            "titles": [],
            "titles": [],  # List of unlocked titles
            "current_title": None,  # Equipped title
            "devil_fruit": None,
            "last_active": None,
        }
        self.config.register_member(**default_member)

        default_guild = {
            "bounties": {},
            "event": None,
            "tournaments": {},
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.active_channels = set()  # Track active battles by channel ID
        self.tournaments = {}  # Track active tournaments
        self.log = logging.getLogger("red.deathmatch")  # Log under the cog name
        self.log.setLevel(logging.INFO)  # Set the log level
        self.current_environment = None  # Track the current environment
        self.battle_stopped = False  # Track if a battle was stopped

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
        """Consume a random Devil Fruit for unique battle powers!"""
        user = ctx.author
        current_fruit = await self.config.member(user).devil_fruit()
    
        if current_fruit:
            return await ctx.send(f"❌ You already have the `{current_fruit}`! You can only eat one Devil Fruit!")
    
        # Select a random fruit
        new_fruit = random.choice(list(DEVIL_FRUITS.keys()))
        fruit_type = DEVIL_FRUITS[new_fruit]["type"]
        effect = DEVIL_FRUITS[new_fruit]["bonus"]
    
        await self.config.member(user).devil_fruit.set(new_fruit)
    
        await ctx.send(
            f"🍎 **{user.display_name}** has eaten the **{new_fruit}**! ({fruit_type} Type)\n"
            f"🔥 **New Power:** {effect}\n\n"
            f"⚠️ *You cannot eat another Devil Fruit!*"
        )

    @commands.command()
    async def myfruit(self, ctx):
        """Check which Devil Fruit you have eaten."""
        user = ctx.author
        fruit = await self.config.member(user).devil_fruit()
    
        if not fruit:
            return await ctx.send("🍏 You have not eaten a Devil Fruit yet!")
    
        effect = DEVIL_FRUITS[fruit]["bonus"]
        await ctx.send(f"🍎 **{user.display_name}**, you have the `{fruit}`! **Effect:** {effect}")

    
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
        titles = [
            (50000000, "Rookie Pirate"),
            (100000000, "Super Rookie"),
            (200000000, "Notorious Pirate"),
            (300000000, "Supernova"),
            (400000000, "Rising Star"),
            (500000000, "Infamous Pirate"),
            (600000000, "Feared Pirate"),
            (700000000, "Pirate Captain"),
            (800000000, "Pirate Lord"),
            (900000000, "Pirate Emperor"),
            (1000000000, "Yonko"),
            (1500000000, "Pirate King Candidate"),
            (2000000000, "King of the Pirates")
        ]
        for amount, title in reversed(titles):
            if bounty_amount >= amount:
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
    async def deathbattle(self, ctx: commands.Context, opponent: discord.Member):
        """
        Start a One Piece deathmatch against another user.
        """
        # Prevent invalid matches
        if ctx.author == opponent:
            await ctx.send("❌ You cannot challenge yourself to a deathmatch!")
            return
        if opponent.bot:
            await ctx.send("❌ You cannot challenge a bot to a deathmatch!")
            return
        if ctx.channel.id in self.active_channels:
            await ctx.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")
            return

        # Mark the channel as active
        self.active_channels.add(ctx.channel.id)

        # Generate fight card
        fight_card = self.generate_fight_card(ctx.author, opponent)

        # Send the dynamically generated fight card image
        await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))

        # Proceed with fight logic if applicable...
        await self.fight(ctx, ctx.author, opponent)

        # Mark the channel as inactive
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
        
        # Increase the winner's bounty (random amount between 1,000 and 3,000 Berries)
        bounty_increase = random.randint(1000, 3000)
        winner_id = str(winner["member"].id)
        
        # Get current bounty and update it
        bounties = await self.config.guild(ctx.guild).bounties()
        bounties[winner_id] = bounties.get(winner_id, {"amount": 0})
        bounties[winner_id]["amount"] += bounty_increase
        
        # Save the new bounty
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(winner["member"]).bounty.set(bounties[winner_id]["amount"])
        
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

    @commands.admin_or_permissions(administrator=True)
    @commands.command(name="resetstats")
    async def resetstats(self, ctx: commands.Context, member: discord.Member = None):
        """
        Reset the stats of a specific user, or everyone in the guild if no member is specified.
        This command can only be used by admins.
        """
        if member:
            # Reset stats for a specific user
            await self.reset_player_stats(member)
            await ctx.send(f"✅ Stats for **{member.display_name}** have been reset.")
        else:
            # Reset stats for all members in the guild
            confirmation_msg = await ctx.send(
                "⚠️ Are you sure you want to reset stats for **everyone in this guild**? Reply with `yes` to confirm."
            )

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == "yes"

            try:
                await self.bot.wait_for("message", check=check, timeout=30)
                await self.reset_all_stats(ctx.guild)
                await ctx.send("✅ Stats for **all members in this guild** have been reset.")
            except asyncio.TimeoutError:
                await ctx.send("❌ Reset operation timed out. No stats were reset.")
    
    @commands.command(name="titles")
    async def titles(self, ctx: commands.Context, member: discord.Member = None):
        """Display a list of unlocked titles for a user."""
        member = member or ctx.author
        titles = await self.config.member(member).titles()
        current_title = await self.config.member(member).current_title()
    
        embed = discord.Embed(
            title=f"🏅 {member.display_name}'s Titles",
            description=(
                f"**Current Title:** {current_title if current_title else 'None'}\n\n"
                f"**Unlocked Titles:**\n" + "\n".join(titles) if titles else "None"
            ),
            color=0x00FF00,
        )
        await ctx.send(embed=embed)
        
    @commands.command(name="equiptitle")
    async def equiptitle(self, ctx: commands.Context, title: str):
        """Equip a title for yourself."""
        titles = await self.config.member(ctx.author).titles()
        title_lower = title.lower()
        matched_title = next((t for t in titles if t.lower() == title_lower), None)
            
        if not matched_title:
            await ctx.send(f"❌ You have not unlocked the title `{title}`.")
            return

        await self.config.member(ctx.author).current_title.set(matched_title)
        await ctx.send(f"✅ You have equipped the title `{matched_title}`!")

    @commands.command(name="deathstats")
    async def deathstats(self, ctx: commands.Context, member: discord.Member = None):
        """Display the stats, titles, and rank of a user."""
        member = member or ctx.author
        stats = await self.config.member(member).all()
        all_members = await self.config.all_members(ctx.guild)
    
        # Sort members by wins for ranking
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)
        rank = next((i for i, (m_id, _) in enumerate(sorted_members, start=1) if m_id == member.id), None)
    
        wins = stats["wins"]
        losses = stats["losses"]
        kdr = (wins / losses) if losses > 0 else wins  # Avoid division by zero
        current_title = stats["current_title"]
    
        embed = discord.Embed(
            title=f"🏴‍☠️ {member.display_name}'s Stats 🏴‍☠️",
            color=0x00FF00,
        )
        embed.add_field(name="Wins", value=wins, inline=True)
        embed.add_field(name="Losses", value=losses, inline=True)
        embed.add_field(name="KDR", value=f"{kdr:.2f}", inline=True)
        embed.add_field(name="Rank", value=f"#{rank}" if rank else "Unranked", inline=True)
        embed.add_field(name="Current Title", value=current_title if current_title else "None", inline=False)
    
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
    await bot.add_cog(BountyBattle(bot))
