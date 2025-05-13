import asyncio
import random
import logging
from typing import Dict, List, Optional, Union
import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box, humanize_list
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime

log = logging.getLogger("red.fireforce")

# Ability tiers and their rarity chances
ABILITY_TIERS = {
    "Common": 0.50,     # 50% chance
    "Uncommon": 0.30,   # 30% chance
    "Rare": 0.15,       # 15% chance
    "Epic": 0.04,       # 4% chance
    "Legendary": 0.01,  # 1% chance
    "Secret": 0.001     # 0.1% chance
}

# Squadrons available in the game
SQUADRONS = {
    1: {"name": "Special Fire Force Company 1", "bonus": "defense"},
    2: {"name": "Special Fire Force Company 2", "bonus": "speed"},
    3: {"name": "Special Fire Force Company 3", "bonus": "power"},
    4: {"name": "Special Fire Force Company 4", "bonus": "utility"},
    5: {"name": "Special Fire Force Company 5", "bonus": "resistance"},
    6: {"name": "Special Fire Force Company 6", "bonus": "stealth"},
    7: {"name": "Special Fire Force Company 7", "bonus": "recovery"},
    8: {"name": "Special Fire Force Company 8", "bonus": "balanced"},
}

# Pyrokinesis abilities by tier
ABILITIES = {
    "Common": [
        {"name": "Fire Punch", "damage": 10, "cooldown": 1, "description": "Basic fire-enhanced punch"},
        {"name": "Ember Kick", "damage": 12, "cooldown": 1, "description": "Basic fire-enhanced kick"},
        {"name": "Flame Throw", "damage": 15, "cooldown": 2, "description": "Projects a small flame burst"}
    ],
    "Uncommon": [
        {"name": "Burning Rush", "damage": 18, "cooldown": 2, "description": "Quick series of flame-enhanced strikes"},
        {"name": "Heat Wave", "damage": 22, "cooldown": 3, "description": "Releases a wave of intense heat"},
        {"name": "Blaze Armor", "damage": 5, "defense": 15, "cooldown": 3, "description": "Forms protective fire around the body"}
    ],
    "Rare": [
        {"name": "Inferno Blast", "damage": 30, "cooldown": 3, "description": "Powerful concentrated fire blast"},
        {"name": "Phoenix Rise", "damage": 25, "heal": 10, "cooldown": 4, "description": "Flame attack that also heals the user"},
        {"name": "Firewheel", "damage": 28, "aoe": True, "cooldown": 4, "description": "Spinning wheel of fire that hits multiple targets"}
    ],
    "Epic": [
        {"name": "Hellfire Tornado", "damage": 40, "aoe": True, "cooldown": 5, "description": "Massive spiraling flame that engulfs the area"},
        {"name": "Solar Flare", "damage": 45, "cooldown": 5, "description": "Intensely bright and hot flame burst"},
        {"name": "Dragon's Breath", "damage": 50, "cooldown": 6, "description": "Releases a powerful stream of dragon-like flames"}
    ],
    "Legendary": [
        {"name": "Adolla Link", "damage": 60, "special": "vision", "cooldown": 7, "description": "Taps into the Adolla to glimpse future moves"},
        {"name": "Evangelist's Flame", "damage": 65, "corruption": 10, "cooldown": 7, "description": "Powerful but corrupting flame of the Evangelist"},
        {"name": "Flame of Destruction", "damage": 75, "self_damage": 15, "cooldown": 8, "description": "Devastating flame that also harms the user"}
    ],
    "Secret": [
        {"name": "Adolla Burst", "damage": 100, "transform": True, "cooldown": 10, "description": "Rare ability to ignite with the core flame of the Adolla"},
        {"name": "Grace", "damage": 90, "purify": True, "cooldown": 9, "description": "Holy flame of purification that burns away corruption"},
        {"name": "Crimson Moon", "damage": 120, "ultimate": True, "cooldown": 12, "description": "Legendary flame technique that manifests a crimson moon"}
    ]
}

class FireForce(commands.Cog):
    """Fire Force themed gameplay with pyrokinesis abilities and infernal battles"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=8927348724, force_registration=True)
        
        # Default user settings
        default_user = {
            "character": None,
            "experience": 0,
            "level": 1,
            "battles": 0,
            "wins": 0,
            "losses": 0
        }
        
        # Default guild settings
        default_guild = {
            "active_infernals": [],
            "white_clad_bosses": [],
            "squadron_rankings": {}
        }
        
        # Character schema
        self.character_schema = {
            "name": "",
            "squadron": 0,
            "tier": "",
            "abilities": [],
            "stats": {
                "power": 0,
                "agility": 0,
                "defense": 0,
                "technique": 0,
                "resistance": 0
            },
            "equipped_ability": "",
            "level": 1,
            "experience": 0
        }
        
        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)
        
        # Active battles tracking
        self.active_battles = {}
        
    @commands.group(name="fireforce", aliases=["ff"])
    async def fireforce(self, ctx):
        """Main command group for Fire Force game"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
    
    @fireforce.command(name="create")
    async def create_character(self, ctx, name: str):
        """Create a new Fire Force character with random abilities"""
        # Check if user already has a character
        user_data = await self.config.user(ctx.author).all()
        
        if user_data["character"] is not None:
            return await ctx.send("You already have a character! Use `[p]fireforce info` to see your character.")
        
        # Generate random character
        character = self._generate_character(name)
        
        # Save character to user data
        await self.config.user(ctx.author).character.set(character)
        
        # Create and send character card
        char_image = await self._create_character_card(character)
        file = discord.File(char_image, filename="character.png")
        
        embed = discord.Embed(
            title=f"🔥 Character Created: {character['name']} 🔥",
            description=f"You've joined {SQUADRONS[character['squadron']]['name']}!",
            color=discord.Color.orange()
        )
        embed.add_field(name="Ability Tier", value=character['tier'], inline=True)
        embed.add_field(name="Level", value=character['level'], inline=True)
        
        ability_list = "\n".join([f"• **{a['name']}**: {a['description']}" for a in character['abilities']])
        embed.add_field(name="Abilities", value=ability_list, inline=False)
        
        stats = character['stats']
        stat_text = f"Power: {stats['power']} | Agility: {stats['agility']} | Defense: {stats['defense']} | Technique: {stats['technique']} | Resistance: {stats['resistance']}"
        embed.add_field(name="Stats", value=stat_text, inline=False)
        
        embed.set_image(url="attachment://character.png")
        
        await ctx.send(embed=embed, file=file)

    @fireforce.command(name="info")
    async def character_info(self, ctx, user: discord.Member = None):
        """Display information about your Fire Force character or another user's character"""
        target = user or ctx.author
        
        character = await self.config.user(target).character()
        if character is None:
            if target == ctx.author:
                return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
            else:
                return await ctx.send(f"{target.display_name} doesn't have a character yet.")
        
        # Create and send character card
        char_image = await self._create_character_card(character)
        file = discord.File(char_image, filename="character.png")
        
        embed = discord.Embed(
            title=f"🔥 {character['name']} 🔥",
            description=f"Member of {SQUADRONS[character['squadron']]['name']}",
            color=discord.Color.orange()
        )
        embed.add_field(name="Ability Tier", value=character['tier'], inline=True)
        embed.add_field(name="Level", value=character['level'], inline=True)
        
        ability_list = "\n".join([f"• **{a['name']}**: {a['description']}" for a in character['abilities']])
        embed.add_field(name="Abilities", value=ability_list, inline=False)
        
        stats = character['stats']
        stat_text = f"Power: {stats['power']} | Agility: {stats['agility']} | Defense: {stats['defense']} | Technique: {stats['technique']} | Resistance: {stats['resistance']}"
        embed.add_field(name="Stats", value=stat_text, inline=False)
        
        user_data = await self.config.user(target).all()
        battles = user_data.get("battles", 0)
        wins = user_data.get("wins", 0)
        losses = user_data.get("losses", 0)
        
        win_rate = (wins / battles * 100) if battles > 0 else 0
        
        embed.add_field(name="Battle Record", value=f"Battles: {battles}\nWins: {wins}\nLosses: {losses}\nWin Rate: {win_rate:.1f}%", inline=False)
        embed.set_image(url="attachment://character.png")
        
        await ctx.send(embed=embed, file=file)

    @fireforce.command(name="battle")
    async def battle_infernal(self, ctx):
        """Battle against a randomly generated Infernal"""
        # Check if user has a character
        character = await self.config.user(ctx.author).character()
        if character is None:
            return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
        
        # Check if user is already in a battle
        if ctx.author.id in self.active_battles:
            return await ctx.send("You're already in a battle! Finish that one first.")
        
        # Generate random infernal opponent
        infernal = self._generate_infernal(character['level'])
        
        # Create battle state
        battle_state = {
            "player": character,
            "infernal": infernal,
            "turn": 1,
            "player_hp": 100 + character['stats']['defense'],
            "infernal_hp": 100 + infernal['level'] * 5,
            "player_cooldowns": {},
            "infernal_cooldowns": {},
            "battle_log": [f"A {infernal['name']} appears! Get ready to fight!"]
        }
        
        self.active_battles[ctx.author.id] = battle_state
        
        # Start battle
        await self._run_battle(ctx)

    @fireforce.command(name="pvp")
    async def battle_player(self, ctx, opponent: discord.Member):
        """Challenge another player to a PvP battle"""
        # Check if both users have characters
        player_char = await self.config.user(ctx.author).character()
        opponent_char = await self.config.user(opponent).character()
        
        if player_char is None:
            return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
        
        if opponent_char is None:
            return await ctx.send(f"{opponent.display_name} doesn't have a character yet!")
        
        # Check if either player is already in a battle
        if ctx.author.id in self.active_battles:
            return await ctx.send("You're already in a battle! Finish that one first.")
        
        if opponent.id in self.active_battles:
            return await ctx.send(f"{opponent.display_name} is already in a battle!")
        
        # Ask opponent if they accept the challenge
        await ctx.send(f"{opponent.mention}, {ctx.author.display_name} has challenged you to a battle! Type `accept` to accept or `decline` to decline.")
        
        def check(m):
            return m.author == opponent and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]
        
        try:
            response = await self.bot.wait_for("message", check=check, timeout=60)
            
            if response.content.lower() == "decline":
                return await ctx.send(f"{opponent.display_name} has declined the challenge.")
            
        except asyncio.TimeoutError:
            return await ctx.send("Challenge timed out. Try again later.")
        
        # Set up PvP battle
        battle_state = {
            "player1": {
                "user": ctx.author,
                "character": player_char,
                "hp": 100 + player_char['stats']['defense'],
                "cooldowns": {}
            },
            "player2": {
                "user": opponent,
                "character": opponent_char,
                "hp": 100 + opponent_char['stats']['defense'],
                "cooldowns": {}
            },
            "turn": 1,
            "current_player": 1,  # 1 or 2 to track whose turn it is
            "battle_log": ["PvP battle started!"]
        }
        
        # Store battle state for both players
        self.active_battles[ctx.author.id] = battle_state
        self.active_battles[opponent.id] = battle_state
        
        # Start PvP battle
        await self._run_pvp_battle(ctx, opponent)

    @fireforce.command(name="squadron")
    async def squadron_info(self, ctx, squadron_number: int = None):
        """View information about your squadron or a specific squadron"""
        if squadron_number is not None:
            if squadron_number not in SQUADRONS:
                return await ctx.send(f"Invalid squadron number. Please choose a number between 1 and {len(SQUADRONS)}.")
            
            squadron = SQUADRONS[squadron_number]
            
            embed = discord.Embed(
                title=f"Special Fire Force Company {squadron_number}",
                description=f"Squadron Bonus: {squadron['bonus'].capitalize()}",
                color=discord.Color.orange()
            )
            
            # Get players in this squadron
            squadron_members = []
            
            for member in ctx.guild.members:
                char_data = await self.config.user(member).character()
                if char_data and char_data['squadron'] == squadron_number:
                    squadron_members.append((member.display_name, char_data['name'], char_data['level']))
            
            if squadron_members:
                member_list = "\n".join([f"• {name} ({char_name}) - Level {level}" for name, char_name, level in squadron_members])
                embed.add_field(name="Members", value=member_list, inline=False)
            else:
                embed.add_field(name="Members", value="No members from this guild in this squadron.", inline=False)
            
            await ctx.send(embed=embed)
            
        else:
            # Show user's squadron
            character = await self.config.user(ctx.author).character()
            if character is None:
                return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
            
            squadron_number = character['squadron']
            squadron = SQUADRONS[squadron_number]
            
            embed = discord.Embed(
                title=f"Special Fire Force Company {squadron_number}",
                description=f"Your squadron: {squadron['name']}\nSquadron Bonus: {squadron['bonus'].capitalize()}",
                color=discord.Color.orange()
            )
            
            # Get players in this squadron
            squadron_members = []
            
            for member in ctx.guild.members:
                if member.id == ctx.author.id:
                    continue  # Skip the command user
                    
                char_data = await self.config.user(member).character()
                if char_data and char_data['squadron'] == squadron_number:
                    squadron_members.append((member.display_name, char_data['name'], char_data['level']))
            
            if squadron_members:
                member_list = "\n".join([f"• {name} ({char_name}) - Level {level}" for name, char_name, level in squadron_members])
                embed.add_field(name="Teammates", value=member_list, inline=False)
            else:
                embed.add_field(name="Teammates", value="No other members from this guild in your squadron.", inline=False)
            
            await ctx.send(embed=embed)

    @commands.is_owner()
    @fireforce.command(name="reset")
    async def reset_character(self, ctx, user: discord.Member = None):
        """[Owner Only] Reset a user's character data"""
        target = user or ctx.author
        
        await self.config.user(target).clear()
        await ctx.send(f"{target.display_name}'s character data has been reset.")

    # Helper methods
    def _generate_character(self, name: str) -> Dict:
        """Generate a random character with abilities and stats"""
        # Determine ability tier based on rarity chances
        tier = self._random_tier()
        
        # Random squadron assignment
        squadron = random.randint(1, 8)
        
        # Random abilities (1-3 based on tier)
        abilities_count = min(3, max(1, ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Secret"].index(tier) + 1))
        
        # Get abilities of the given tier and potentially lower tiers
        available_tiers = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Secret"]
        available_tiers = available_tiers[:available_tiers.index(tier) + 1]
        
        abilities = []
        for _ in range(abilities_count):
            chosen_tier = random.choice(available_tiers)
            ability = random.choice(ABILITIES[chosen_tier])
            if ability not in abilities:  # Avoid duplicates
                abilities.append(ability.copy())  # Create a copy to avoid modifying the original
        
        # Generate random stats (influenced by tier and squadron)
        tier_index = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Secret"].index(tier)
        base_stat = 5 + tier_index * 2
        
        stats = {
            "power": base_stat + random.randint(0, 5),
            "agility": base_stat + random.randint(0, 5),
            "defense": base_stat + random.randint(0, 5),
            "technique": base_stat + random.randint(0, 5),
            "resistance": base_stat + random.randint(0, 5)
        }
        
        # Apply squadron bonus
        bonus_type = SQUADRONS[squadron]["bonus"]
        if bonus_type == "power":
            stats["power"] += 3
        elif bonus_type == "speed":
            stats["agility"] += 3
        elif bonus_type == "defense":
            stats["defense"] += 3
        elif bonus_type == "utility":
            stats["technique"] += 3
        elif bonus_type == "resistance":
            stats["resistance"] += 3
        elif bonus_type == "stealth":
            stats["agility"] += 2
            stats["technique"] += 1
        elif bonus_type == "recovery":
            stats["resistance"] += 2
            stats["defense"] += 1
        elif bonus_type == "balanced":
            for stat in stats:
                stats[stat] += 1
        
        # Create character object
        character = {
            "name": name,
            "squadron": squadron,
            "tier": tier,
            "abilities": abilities,
            "stats": stats,
            "equipped_ability": abilities[0]["name"] if abilities else "",
            "level": 1,
            "experience": 0
        }
        
        return character

    def _random_tier(self) -> str:
        """Randomly select an ability tier based on rarity chances"""
        roll = random.random()
        cumulative = 0
        
        for tier, chance in ABILITY_TIERS.items():
            cumulative += chance
            if roll <= cumulative:
                return tier
        
        return "Common"  # Fallback

    def _generate_infernal(self, player_level: int) -> Dict:
        """Generate a random infernal for battles"""
        # Infernal types with increasing difficulty
        infernal_types = [
            {"name": "Flame Human", "difficulty": 1, "abilities": ["Burning Touch", "Fire Breath"]},
            {"name": "Flaming Demon", "difficulty": 2, "abilities": ["Flame Wave", "Explosive Burst"]},
            {"name": "Infernal Beast", "difficulty": 3, "abilities": ["Raging Inferno", "Flame Charge"]},
            {"name": "Demon Infernal", "difficulty": 4, "abilities": ["Soul Fire", "Burning Curse"]},
            {"name": "Adolla Infernal", "difficulty": 5, "abilities": ["Adolla Flame", "Corruption Touch"]}
        ]
        
        # Select infernal type based on player level
        difficulty_index = min(len(infernal_types) - 1, (player_level - 1) // 5)
        infernal_type = infernal_types[difficulty_index]
        
        # Scale the infernal level based on player level
        level = max(1, min(50, player_level + random.randint(-2, 2)))
        
        # Create infernal object
        infernal = {
            "name": infernal_type["name"],
            "level": level,
            "abilities": infernal_type["abilities"],
            "difficulty": infernal_type["difficulty"],
            "stats": {
                "power": 5 + level // 2,
                "agility": 5 + level // 3,
                "defense": 5 + level // 3,
                "technique": 3 + level // 4,
                "resistance": 4 + level // 3
            }
        }
        
        return infernal

    async def _create_character_card(self, character: Dict) -> io.BytesIO:
        """Create a character card image using PIL"""
        # Base card dimensions
        width, height = 600, 400
        
        # Create base image
        image = Image.new("RGB", (width, height), color=(40, 40, 40))
        draw = ImageDraw.Draw(image)
        
        # Add fire-themed border
        border_width = 10
        draw.rectangle(
            [(border_width, border_width), (width - border_width, height - border_width)], 
            outline=(255, 100, 0), 
            width=border_width
        )
        
        # Tier colors
        tier_colors = {
            "Common": (150, 150, 150),
            "Uncommon": (0, 180, 0),
            "Rare": (0, 100, 255),
            "Epic": (180, 0, 180),
            "Legendary": (255, 165, 0),
            "Secret": (255, 0, 0)
        }
        
        # Let's create some basic fonts using PIL's default font
        try:
            # Try to load Arial or a default system font
            title_font = ImageFont.truetype("arial.ttf", 30)
            header_font = ImageFont.truetype("arial.ttf", 20)
            text_font = ImageFont.truetype("arial.ttf", 16)
        except IOError:
            # If font files aren't available, use default bitmap font
            title_font = ImageFont.load_default()
            header_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
        
        # Add character name
        draw.rectangle([(50, 30), (550, 80)], fill=(30, 30, 30))
        draw.text((55, 40), character["name"], fill=(255, 255, 255), font=title_font)
        
        # Add tier
        tier_color = tier_colors.get(character["tier"], (255, 255, 255))
        draw.rectangle([(450, 90), (550, 120)], fill=tier_color)
        text_color = (0, 0, 0) if character["tier"] in ["Common", "Uncommon", "Legendary"] else (255, 255, 255)
        draw.text((455, 95), character["tier"], fill=text_color, font=header_font)
        
        # Add squadron info
        draw.rectangle([(50, 90), (440, 120)], fill=(60, 60, 60))
        squadron_text = f"Special Fire Force Company {character['squadron']}"
        draw.text((55, 95), squadron_text, fill=(255, 255, 255), font=header_font)
        
        # Add abilities section
        draw.rectangle([(50, 130), (550, 230)], fill=(50, 30, 30))
        draw.text((55, 135), "Abilities:", fill=(255, 200, 150), font=header_font)
        
        # List abilities
        abilities_y = 160
        for ability in character["abilities"]:
            ability_text = f"• {ability['name']} - {ability.get('damage', 0)} dmg"
            draw.text((60, abilities_y), ability_text, fill=(255, 255, 255), font=text_font)
            abilities_y += 20
            
            # Add short description if it exists
            if ability.get("description"):
                desc_text = f"  {ability['description']}"
                draw.text((65, abilities_y), desc_text, fill=(200, 200, 200), font=text_font)
                abilities_y += 20
        
        # Add stats section
        draw.rectangle([(50, 240), (550, 320)], fill=(30, 50, 30))
        draw.text((55, 245), "Stats:", fill=(150, 255, 150), font=header_font)
        
        # Draw stats values
        stats = character["stats"]
        stats_y = 270
        
        # Power stat with bar
        power_text = f"Power: {stats['power']}"
        draw.text((60, stats_y), power_text, fill=(255, 255, 255), font=text_font)
        self._draw_stat_bar(draw, 180, stats_y + 8, stats['power'], (255, 100, 100))
        stats_y += 20
        
        # Agility stat with bar
        agility_text = f"Agility: {stats['agility']}"
        draw.text((60, stats_y), agility_text, fill=(255, 255, 255), font=text_font)
        self._draw_stat_bar(draw, 180, stats_y + 8, stats['agility'], (100, 255, 100))
        stats_y += 20
        
        # Defense stat with bar
        defense_text = f"Defense: {stats['defense']}"
        draw.text((60, stats_y), defense_text, fill=(255, 255, 255), font=text_font)
        self._draw_stat_bar(draw, 180, stats_y + 8, stats['defense'], (100, 100, 255))
        stats_y += 20
        
        # Add level and experience
        level_text = f"Level: {character['level']} - XP: {character['experience']}"
        draw.text((300, 330), level_text, fill=(255, 255, 150), font=header_font)
        
        # Add fire effects (simpler version that works with RGB mode)
        for _ in range(30):
            x = random.randint(20, width - 20)
            y = random.randint(20, height - 20)
            size = random.randint(2, 6)
            
            # Create orange/red particle
            draw.ellipse(
                [(x - size, y - size), (x + size, y + size)],
                fill=(255, random.randint(50, 150), 0)
            )
        
        # Convert to bytes for Discord
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        
        return buffer
    
    def _draw_stat_bar(self, draw, x, y, value, color, max_width=300, height=10):
        """Draw a stat bar for character cards"""
        # Base stat is around 5, max reasonable stat would be around 30-40
        percentage = min(1.0, value / 40.0)
        width = int(max_width * percentage)
        
        # Draw background bar
        draw.rectangle([(x, y), (x + max_width, y + height)], fill=(50, 50, 50), outline=(100, 100, 100))
        
        # Draw filled part
        draw.rectangle([(x, y), (x + width, y + height)], fill=color)

    async def _run_battle(self, ctx):
        """Run a battle against an infernal"""
        battle_state = self.active_battles[ctx.author.id]
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Create initial battle embed
        embed = self._create_battle_embed(battle_state)
        battle_msg = await ctx.send(embed=embed)
        
        # Add reaction controls
        for i in range(min(3, len(player["abilities"]))):
            await battle_msg.add_reaction(f"{i+1}\u20e3")  # Number emoji
        
        # Battle loop
        while True:
            # Check if battle is over
            if battle_state["player_hp"] <= 0:
                await self._end_battle(ctx, False)  # Player lost
                break
                
            if battle_state["infernal_hp"] <= 0:
                await self._end_battle(ctx, True)  # Player won
                break
            
            # Wait for player's move selection
            def check(reaction, user):
                return (
                    user == ctx.author
                    and reaction.message.id == battle_msg.id
                    and str(reaction.emoji)[0] in "123"
                    and int(str(reaction.emoji)[0]) <= len(player["abilities"])
                )
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
                ability_index = int(str(reaction.emoji)[0]) - 1
                
                # Execute player's move
                await self._execute_player_move(ctx, battle_state, ability_index)
                
                # Update battle embed
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Check if battle is over after player's move
                if battle_state["infernal_hp"] <= 0:
                    await self._end_battle(ctx, True)  # Player won
                    break
                
                # Execute infernal's move
                await asyncio.sleep(1)  # Brief pause for effect
                await self._execute_infernal_move(ctx, battle_state)
                
                # Update battle embed again
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Increment turn counter
                battle_state["turn"] += 1
                
                # Update cooldowns
                for ability, cd in list(battle_state["player_cooldowns"].items()):
                    if cd > 0:
                        battle_state["player_cooldowns"][ability] -= 1
                    else:
                        del battle_state["player_cooldowns"][ability]
                
                for ability, cd in list(battle_state["infernal_cooldowns"].items()):
                    if cd > 0:
                        battle_state["infernal_cooldowns"][ability] -= 1
                    else:
                        del battle_state["infernal_cooldowns"][ability]
                
            except asyncio.TimeoutError:
                # Player took too long
                battle_state["battle_log"].append(f"{ctx.author.display_name} hesitated!")
                
                # Infernal attacks automatically
                await self._execute_infernal_move(ctx, battle_state)
                
                # Update battle embed
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Check if battle is over
                if battle_state["player_hp"] <= 0:
                    await self._end_battle(ctx, False)  # Player lost
                    break
                
                # Increment turn counter
                battle_state["turn"] += 1

    def _create_battle_embed(self, battle_state):
        """Create an embed for the current battle state"""
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Create progress bars for HP
        player_max_hp = 100 + player["stats"]["defense"]
        infernal_max_hp = 100 + infernal["level"] * 5
        
        player_hp_percent = max(0, min(1, battle_state["player_hp"] / player_max_hp))
        infernal_hp_percent = max(0, min(1, battle_state["infernal_hp"] / infernal_max_hp))
        
        player_bar = self._create_hp_bar(player_hp_percent)
        infernal_bar = self._create_hp_bar(infernal_hp_percent)
        
        # Create battle embed
        embed = discord.Embed(
            title=f"🔥 Battle: {player['name']} vs {infernal['name']} 🔥",
            description=f"Turn {battle_state['turn']}",
            color=discord.Color.red()
        )
        
        # Add HP bars
        embed.add_field(
            name=f"{player['name']} [Lvl {player['level']}]",
            value=f"HP: {battle_state['player_hp']}/{player_max_hp}\n{player_bar}",
            inline=False
        )
        
        embed.add_field(
            name=f"{infernal['name']} [Lvl {infernal['level']}]",
            value=f"HP: {battle_state['infernal_hp']}/{infernal_max_hp}\n{infernal_bar}",
            inline=False
        )
        
        # List player abilities with cooldowns
        ability_list = []
        for i, ability in enumerate(player["abilities"]):
            cooldown = battle_state["player_cooldowns"].get(ability["name"], 0)
            status = f"[ON COOLDOWN: {cooldown}]" if cooldown > 0 else "[READY]"
            ability_list.append(f"{i+1}. **{ability['name']}** {status}")
        
        embed.add_field(
            name="Your Abilities",
            value="\n".join(ability_list) or "No abilities available",
            inline=False
        )
        
        # Battle log (last 5 entries)
        log_entries = battle_state["battle_log"][-5:]
        embed.add_field(
            name="Battle Log",
            value="\n".join(log_entries) or "Battle started!",
            inline=False
        )
        
        return embed

    def _create_hp_bar(self, percent, length=20):
        """Create a text-based HP bar"""
        filled = int(percent * length)
        bar = "█" * filled + "░" * (length - filled)
        return bar

    async def _execute_player_move(self, ctx, battle_state, ability_index):
        """Execute the player's selected move"""
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Get selected ability
        ability = player["abilities"][ability_index]
        
        # Check if ability is on cooldown
        if battle_state["player_cooldowns"].get(ability["name"], 0) > 0:
            battle_state["battle_log"].append(f"{player['name']} tried to use {ability['name']} but it's still on cooldown!")
            return
        
        # Set ability cooldown
        battle_state["player_cooldowns"][ability["name"]] = ability.get("cooldown", 1)
        
        # Calculate damage
        base_damage = ability.get("damage", 10)
        power_bonus = player["stats"]["power"] * 0.5
        technique_bonus = player["stats"]["technique"] * 0.2
        
        total_damage = int(base_damage + power_bonus + technique_bonus)
        
        # Apply damage reduction based on infernal's defense
        defense_reduction = infernal["stats"]["defense"] * 0.3
        final_damage = max(1, total_damage - defense_reduction)
        final_damage = int(final_damage)  # Ensure it's an integer
        
        # Apply damage
        battle_state["infernal_hp"] -= final_damage
        
        # Special ability effects
        if ability.get("heal"):
            heal_amount = ability["heal"]
            player_max_hp = 100 + player["stats"]["defense"]
            battle_state["player_hp"] = min(player_max_hp, battle_state["player_hp"] + heal_amount)
            battle_state["battle_log"].append(f"{player['name']} uses {ability['name']} for {final_damage} damage and heals for {heal_amount} HP!")
        elif ability.get("aoe"):
            # AOE does additional damage
            aoe_damage = int(final_damage * 0.5)
            battle_state["infernal_hp"] -= aoe_damage
            battle_state["battle_log"].append(f"{player['name']} uses area attack {ability['name']} for {final_damage} + {aoe_damage} damage!")
        elif ability.get("self_damage"):
            # Ability hurts the player too
            self_damage = ability["self_damage"]
            battle_state["player_hp"] -= self_damage
            battle_state["battle_log"].append(f"{player['name']} uses {ability['name']} for {final_damage} damage but takes {self_damage} self-damage!")
        else:
            # Standard attack
            battle_state["battle_log"].append(f"{player['name']} uses {ability['name']} for {final_damage} damage!")

    async def _execute_infernal_move(self, ctx, battle_state):
        """Execute the infernal's move"""
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Select a random ability that's not on cooldown
        available_abilities = [
            ability for ability in infernal["abilities"] 
            if ability not in battle_state["infernal_cooldowns"] or battle_state["infernal_cooldowns"][ability] <= 0
        ]
        
        if not available_abilities:
            # Use a basic attack if all abilities are on cooldown
            battle_state["battle_log"].append(f"{infernal['name']} uses a basic attack!")
            
            base_damage = 5 + infernal["level"] // 2
            defense_reduction = player["stats"]["defense"] * 0.3
            final_damage = max(1, int(base_damage - defense_reduction))
            
            battle_state["player_hp"] -= final_damage
            battle_state["battle_log"].append(f"{infernal['name']} deals {final_damage} damage!")
            return
        
        # Select random ability
        ability = random.choice(available_abilities)
        
        # Set cooldown (random between 1-3 turns)
        battle_state["infernal_cooldowns"][ability] = random.randint(1, 3)
        
        # Calculate damage
        base_damage = 8 + infernal["level"] // 2
        if ability == "Burning Touch":
            base_damage += 2
        elif ability == "Fire Breath":
            base_damage += 4
        elif ability == "Flame Wave":
            base_damage += 6
        elif ability == "Explosive Burst":
            base_damage += 8
        elif ability == "Raging Inferno":
            base_damage += 10
        elif ability == "Flame Charge":
            base_damage += 12
        elif ability == "Soul Fire":
            base_damage += 14
        elif ability == "Burning Curse":
            base_damage += 16
        elif ability == "Adolla Flame":
            base_damage += 18
        elif ability == "Corruption Touch":
            base_damage += 20
        
        # Apply player's defense
        defense_reduction = player["stats"]["defense"] * 0.3
        final_damage = max(1, int(base_damage - defense_reduction))
        
        # Apply damage
        battle_state["player_hp"] -= final_damage
        
        # Log the action
        battle_state["battle_log"].append(f"{infernal['name']} uses {ability} for {final_damage} damage!")

    async def _end_battle(self, ctx, victory: bool):
        """Handle end of battle"""
        battle_state = self.active_battles[ctx.author.id]
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Remove from active battles
        del self.active_battles[ctx.author.id]
        
        if victory:
            # Calculate rewards
            exp_gain = 10 + infernal["level"] * 2 + infernal["difficulty"] * 5
            
            # Update player stats
            await self._award_experience(ctx.author, exp_gain)
            await self.config.user(ctx.author).battles.set(
                await self.config.user(ctx.author).battles() + 1
            )
            await self.config.user(ctx.author).wins.set(
                await self.config.user(ctx.author).wins() + 1
            )
            
            # Create victory embed
            embed = discord.Embed(
                title="🔥 Victory! 🔥",
                description=f"You defeated the {infernal['name']}!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Experience Gained", value=f"+{exp_gain} EXP", inline=False)
            
            # Check for level up
            character = await self.config.user(ctx.author).character()
            if character["level"] > player["level"]:
                embed.add_field(
                    name="Level Up!",
                    value=f"You reached level {character['level']}!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        else:
            # Update player stats
            await self.config.user(ctx.author).battles.set(
                await self.config.user(ctx.author).battles() + 1
            )
            await self.config.user(ctx.author).losses.set(
                await self.config.user(ctx.author).losses() + 1
            )
            
            # Create defeat embed
            embed = discord.Embed(
                title="💀 Defeat 💀",
                description=f"You were defeated by the {infernal['name']}!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Try Again",
                value="Don't give up! Train and become stronger to defeat your enemies.",
                inline=False
            )
            
            await ctx.send(embed=embed)

    async def _award_experience(self, user: discord.Member, exp_amount: int):
        """Award experience to a player and handle level ups"""
        # Get character data
        character = await self.config.user(user).character()
        if not character:
            return
        
        # Update experience
        current_exp = character["experience"] + exp_amount
        current_level = character["level"]
        
        # Calculate exp needed for next level (exponential scaling)
        exp_needed = 100 * (current_level ** 1.5)
        
        # Check for level up
        while current_exp >= exp_needed:
            # Level up!
            current_exp -= exp_needed
            current_level += 1
            
            # Recalculate exp needed for next level
            exp_needed = 100 * (current_level ** 1.5)
            
            # Improve stats on level up
            for stat in character["stats"]:
                # Increase each stat by 1-2 points
                character["stats"][stat] += random.randint(1, 2)
        
        # Update character data
        character["experience"] = current_exp
        character["level"] = current_level
        
        # Save updated character
        await self.config.user(user).character.set(character)

    async def _run_pvp_battle(self, ctx, opponent: discord.Member):
        """Run a PvP battle between two players"""
        battle_state = self.active_battles[ctx.author.id]
        
        # Create initial battle embed
        embed = self._create_pvp_battle_embed(battle_state)
        battle_msg = await ctx.send(embed=embed)
        
        # Battle loop
        while True:
            # Get current player
            current_player_num = battle_state["current_player"]
            current_player = battle_state["player1"] if current_player_num == 1 else battle_state["player2"]
            
            # Check if battle is over
            if battle_state["player1"]["hp"] <= 0:
                await self._end_pvp_battle(ctx, opponent, 2)  # Player 2 won
                break
                
            if battle_state["player2"]["hp"] <= 0:
                await self._end_pvp_battle(ctx, opponent, 1)  # Player 1 won
                break
            
            # Add reaction controls
            await battle_msg.clear_reactions()
            for i in range(min(3, len(current_player["character"]["abilities"]))):
                await battle_msg.add_reaction(f"{i+1}\u20e3")  # Number emoji
            
            # Notify current player
            await ctx.send(f"{current_player['user'].mention}, it's your turn! Select an ability by reacting.", delete_after=5)
            
            # Wait for player's move selection
            def check(reaction, user):
                return (
                    user == current_player["user"]
                    and reaction.message.id == battle_msg.id
                    and str(reaction.emoji)[0] in "123"
                    and int(str(reaction.emoji)[0]) <= len(current_player["character"]["abilities"])
                )
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
                ability_index = int(str(reaction.emoji)[0]) - 1
                
                # Execute player's move
                await self._execute_pvp_move(ctx, battle_state, ability_index)
                
                # Update battle embed
                embed = self._create_pvp_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Check if battle is over
                if battle_state["player1"]["hp"] <= 0 or battle_state["player2"]["hp"] <= 0:
                    winner = 2 if battle_state["player1"]["hp"] <= 0 else 1
                    await self._end_pvp_battle(ctx, opponent, winner)
                    break
                
                # Switch to other player
                battle_state["current_player"] = 2 if current_player_num == 1 else 1
                
                # Increment turn counter
                battle_state["turn"] += 1
                
                # Update cooldowns
                for ability, cd in list(battle_state["player1"]["cooldowns"].items()):
                    if cd > 0:
                        battle_state["player1"]["cooldowns"][ability] -= 1
                    else:
                        del battle_state["player1"]["cooldowns"][ability]
                
                for ability, cd in list(battle_state["player2"]["cooldowns"].items()):
                    if cd > 0:
                        battle_state["player2"]["cooldowns"][ability] -= 1
                    else:
                        del battle_state["player2"]["cooldowns"][ability]
                
            except asyncio.TimeoutError:
                # Player took too long
                battle_state["battle_log"].append(f"{current_player['user'].display_name} hesitated and lost their turn!")
                
                # Switch to other player
                battle_state["current_player"] = 2 if current_player_num == 1 else 1
                
                # Update battle embed
                embed = self._create_pvp_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Increment turn counter
                battle_state["turn"] += 1

    def _create_pvp_battle_embed(self, battle_state):
        """Create an embed for the current PvP battle state"""
        player1 = battle_state["player1"]
        player2 = battle_state["player2"]
        
        # Create progress bars for HP
        player1_max_hp = 100 + player1["character"]["stats"]["defense"]
        player2_max_hp = 100 + player2["character"]["stats"]["defense"]
        
        player1_hp_percent = max(0, min(1, player1["hp"] / player1_max_hp))
        player2_hp_percent = max(0, min(1, player2["hp"] / player2_max_hp))
        
        player1_bar = self._create_hp_bar(player1_hp_percent)
        player2_bar = self._create_hp_bar(player2_hp_percent)
        
        # Create battle embed
        embed = discord.Embed(
            title=f"⚔️ PvP Battle: {player1['character']['name']} vs {player2['character']['name']} ⚔️",
            description=f"Turn {battle_state['turn']} | Current Player: {'Player 1' if battle_state['current_player'] == 1 else 'Player 2'}",
            color=discord.Color.gold()
        )
        
        # Add HP bars
        embed.add_field(
            name=f"Player 1: {player1['character']['name']} [Lvl {player1['character']['level']}]",
            value=f"HP: {player1['hp']}/{player1_max_hp}\n{player1_bar}",
            inline=False
        )
        
        embed.add_field(
            name=f"Player 2: {player2['character']['name']} [Lvl {player2['character']['level']}]",
            value=f"HP: {player2['hp']}/{player2_max_hp}\n{player2_bar}",
            inline=False
        )
        
        # List current player's abilities with cooldowns
        current_player = player1 if battle_state["current_player"] == 1 else player2
        ability_list = []
        for i, ability in enumerate(current_player["character"]["abilities"]):
            cooldown = current_player["cooldowns"].get(ability["name"], 0)
            status = f"[ON COOLDOWN: {cooldown}]" if cooldown > 0 else "[READY]"
            ability_list.append(f"{i+1}. **{ability['name']}** {status}")
        
        embed.add_field(
            name=f"Current Player's Abilities",
            value="\n".join(ability_list) or "No abilities available",
            inline=False
        )
        
        # Battle log (last 5 entries)
        log_entries = battle_state["battle_log"][-5:]
        embed.add_field(
            name="Battle Log",
            value="\n".join(log_entries) or "Battle started!",
            inline=False
        )
        
        return embed

    async def _execute_pvp_move(self, ctx, battle_state, ability_index):
        """Execute a player's move in PvP"""
        current_player_num = battle_state["current_player"]
        attacker = battle_state["player1"] if current_player_num == 1 else battle_state["player2"]
        defender = battle_state["player2"] if current_player_num == 1 else battle_state["player1"]
        
        # Get selected ability
        ability = attacker["character"]["abilities"][ability_index]
        
        # Check if ability is on cooldown
        if attacker["cooldowns"].get(ability["name"], 0) > 0:
            battle_state["battle_log"].append(f"{attacker['character']['name']} tried to use {ability['name']} but it's still on cooldown!")
            return
        
        # Set ability cooldown
        attacker["cooldowns"][ability["name"]] = ability.get("cooldown", 1)
        
        # Calculate damage
        base_damage = ability.get("damage", 10)
        power_bonus = attacker["character"]["stats"]["power"] * 0.5
        technique_bonus = attacker["character"]["stats"]["technique"] * 0.2
        
        total_damage = int(base_damage + power_bonus + technique_bonus)
        
        # Apply damage reduction based on defender's defense
        defense_reduction = defender["character"]["stats"]["defense"] * 0.3
        final_damage = max(1, total_damage - defense_reduction)
        final_damage = int(final_damage)  # Ensure it's an integer
        
        # Apply damage
        defender["hp"] -= final_damage
        
        # Special ability effects
        if ability.get("heal"):
            heal_amount = ability["heal"]
            attacker_max_hp = 100 + attacker["character"]["stats"]["defense"]
            attacker["hp"] = min(attacker_max_hp, attacker["hp"] + heal_amount)
            battle_state["battle_log"].append(f"{attacker['character']['name']} uses {ability['name']} for {final_damage} damage and heals for {heal_amount} HP!")
        elif ability.get("aoe"):
            # AOE does reduced damage in PvP
            aoe_damage = int(final_damage * 0.3)
            defender["hp"] -= aoe_damage
            battle_state["battle_log"].append(f"{attacker['character']['name']} uses area attack {ability['name']} for {final_damage} + {aoe_damage} damage!")
        elif ability.get("self_damage"):
            # Ability hurts the attacker too
            self_damage = ability["self_damage"]
            attacker["hp"] -= self_damage
            battle_state["battle_log"].append(f"{attacker['character']['name']} uses {ability['name']} for {final_damage} damage but takes {self_damage} self-damage!")
        else:
            # Standard attack
            battle_state["battle_log"].append(f"{attacker['character']['name']} uses {ability['name']} for {final_damage} damage!")

    async def _end_pvp_battle(self, ctx, opponent: discord.Member, winner: int):
        """Handle end of PvP battle"""
        battle_state = self.active_battles[ctx.author.id]
        
        # Get player objects
        player1 = battle_state["player1"]["user"]
        player2 = battle_state["player2"]["user"]
        
        # Get character data
        player1_char = battle_state["player1"]["character"]
        player2_char = battle_state["player2"]["character"]
        
        # Remove from active battles
        if ctx.author.id in self.active_battles:
            del self.active_battles[ctx.author.id]
        if opponent.id in self.active_battles:
            del self.active_battles[opponent.id]
        
        # Determine winner and loser
        winner_user = player1 if winner == 1 else player2
        winner_char = player1_char if winner == 1 else player2_char
        loser_user = player2 if winner == 1 else player1
        loser_char = player2_char if winner == 1 else player1_char
        
        # Calculate experience reward (based on level difference)
        level_diff = abs(winner_char["level"] - loser_char["level"])
        base_exp = 20
        
        if winner_char["level"] < loser_char["level"]:
            # Bonus for defeating higher level opponent
            exp_gain = base_exp + (level_diff * 5)
        else:
            # Less experience for defeating lower level opponent
            exp_gain = max(5, base_exp - (level_diff * 3))
        
        # Award experience to winner
        await self._award_experience(winner_user, exp_gain)
        
        # Update battle stats
        await self.config.user(winner_user).battles.set(
            await self.config.user(winner_user).battles() + 1
        )
        await self.config.user(winner_user).wins.set(
            await self.config.user(winner_user).wins() + 1
        )
        
        await self.config.user(loser_user).battles.set(
            await self.config.user(loser_user).battles() + 1
        )
        await self.config.user(loser_user).losses.set(
            await self.config.user(loser_user).losses() + 1
        )
        
        # Create victory embed
        embed = discord.Embed(
            title="⚔️ PvP Battle Results ⚔️",
            description=f"{winner_user.mention} ({winner_char['name']}) has defeated {loser_user.mention} ({loser_char['name']})!",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Experience Gained",
            value=f"{winner_user.display_name} gained +{exp_gain} EXP",
            inline=False
        )
        
        # Check for level up
        updated_char = await self.config.user(winner_user).character()
        if updated_char["level"] > winner_char["level"]:
            embed.add_field(
                name="Level Up!",
                value=f"{winner_user.display_name} reached level {updated_char['level']}!",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @fireforce.command(name="tutorial")
    async def tutorial(self, ctx):
        """Learn how to play the Fire Force game"""
        # Tutorial embed 1: Introduction
        embed1 = discord.Embed(
            title="🔥 Fire Force Game Tutorial 🔥",
            description="Welcome to the Fire Force game! This tutorial will help you get started.",
            color=discord.Color.orange()
        )
        
        embed1.add_field(
            name="Creating Your Character",
            value="First, create your character using `[p]fireforce create <name>`. "
                 "You'll be assigned to one of 8 Special Fire Force Companies and receive "
                 "random pyrokinetic abilities based on rarity.",
            inline=False
        )
        
        embed1.add_field(
            name="Character Stats",
            value="Your character has five main stats:\n"
                 "• **Power**: Increases damage output\n"
                 "• **Agility**: Affects turn order and evasion\n"
                 "• **Defense**: Reduces damage taken\n"
                 "• **Technique**: Improves ability effectiveness\n"
                 "• **Resistance**: Resists special effects",
            inline=False
        )
        
        # Tutorial embed 2: Battles
        embed2 = discord.Embed(
            title="🔥 Fire Force Game Tutorial: Battles 🔥",
            description="Battle against Infernals or other players to gain experience and level up!",
            color=discord.Color.orange()
        )
        
        embed2.add_field(
            name="Battle Commands",
            value="• `[p]fireforce battle` - Battle against an Infernal\n"
                 "• `[p]fireforce pvp @user` - Challenge another player\n"
                 "When in battle, select abilities by clicking reaction numbers.",
            inline=False
        )
        
        embed2.add_field(
            name="Abilities",
            value="Abilities have different effects:\n"
                 "• **Damage**: Standard attack abilities\n"
                 "• **Healing**: Restore HP while attacking\n"
                 "• **AoE**: Deal damage to multiple targets\n"
                 "• **Special**: Unique effects based on ability type",
            inline=False
        )
        
        embed2.add_field(
            name="Cooldowns",
            value="Each ability has a cooldown period (in turns) before it can be used again. "
                 "Stronger abilities generally have longer cooldowns.",
            inline=False
        )
        
        # Tutorial embed 3: Progression
        embed3 = discord.Embed(
            title="🔥 Fire Force Game Tutorial: Progression 🔥",
            description="Level up your character to become stronger!",
            color=discord.Color.orange()
        )
        
        embed3.add_field(
            name="Experience and Leveling",
            value="Win battles to gain experience points (EXP). "
                 "When you gain enough EXP, you'll level up automatically. "
                 "Each level up increases your stats.",
            inline=False
        )
        
        embed3.add_field(
            name="Rare Abilities",
            value="The ability tiers from common to rare are:\n"
                 "• **Common** (50% chance)\n"
                 "• **Uncommon** (30% chance)\n"
                 "• **Rare** (15% chance)\n"
                 "• **Epic** (4% chance)\n"
                 "• **Legendary** (1% chance)\n"
                 "• **Secret** (0.1% chance)",
            inline=False
        )
        
        embed3.add_field(
            name="Commands to Check Progress",
            value="• `[p]fireforce info` - View your character info\n"
                 "• `[p]fireforce squadron` - View your squadron info",
            inline=False
        )
        
        # Create and send pages
        embeds = [embed1, embed2, embed3]
        await menu(ctx, embeds, DEFAULT_CONTROLS)
    
    @fireforce.command(name="leaderboard", aliases=["top"])
    async def leaderboard(self, ctx):
        """View the Fire Force players leaderboard"""
        # Get all users with characters
        all_users = await self.config.all_users()
        
        # Filter users who have characters and are in this guild
        guild_member_ids = [member.id for member in ctx.guild.members]
        valid_users = []
        
        for user_id, user_data in all_users.items():
            if user_id in guild_member_ids and user_data.get("character") is not None:
                member = ctx.guild.get_member(user_id)
                if member:
                    valid_users.append((
                        member,
                        user_data["character"]["level"],
                        user_data["character"]["name"],
                        user_data.get("wins", 0),
                        user_data.get("battles", 0)
                    ))
        
        if not valid_users:
            return await ctx.send("No Fire Force characters found in this server.")
        
        # Sort by level, then by wins
        valid_users.sort(key=lambda x: (x[1], x[3]), reverse=True)
        
        # Create leaderboard embed
        embed = discord.Embed(
            title="🔥 Fire Force Leaderboard 🔥",
            description="Top Fire Force players in this server",
            color=discord.Color.gold()
        )
        
        # Add top players
        for i, (member, level, char_name, wins, battles) in enumerate(valid_users[:10], 1):
            win_rate = (wins / battles * 100) if battles > 0 else 0
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"**Character**: {char_name}\n"
                      f"**Level**: {level}\n"
                      f"**Wins**: {wins}/{battles} ({win_rate:.1f}%)",
                inline=(i % 2 == 0)  # Alternate inline
            )
        
        await ctx.send(embed=embed)

    # Helper function to generate battle images
    async def _create_battle_image(self, battle_state):
        """Create a battle scene image using PIL"""
        # Base image dimensions
        width, height = 800, 400
        
        # Create base image (dark background)
        image = Image.new("RGB", (width, height), color=(40, 40, 40))
        draw = ImageDraw.Draw(image)
        
        # Draw battle arena
        draw.rectangle([(50, 50), (width - 50, height - 50)], outline=(255, 100, 0), width=3)
        
        # Add fire effects (simplified)
        for _ in range(20):
            fire_x = random.randint(60, width - 60)
            fire_y = random.randint(60, height - 60)
            fire_size = random.randint(5, 20)
            draw.ellipse(
                [(fire_x - fire_size, fire_y - fire_size), 
                 (fire_x + fire_size, fire_y + fire_size)], 
                fill=(255, random.randint(50, 150), 0)
            )
        
        # Player character (left side)
        player_x, player_y = 150, 200
        draw.rectangle(
            [(player_x - 40, player_y - 80), (player_x + 40, player_y + 80)],
            fill=(60, 60, 100)
        )
        
        # Enemy character (right side)
        enemy_x, enemy_y = width - 150, 200
        draw.rectangle(
            [(enemy_x - 40, enemy_y - 80), (enemy_x + 40, enemy_y + 80)],
            fill=(100, 60, 60)
        )
        
        # Add health bars
        # Player health bar
        player_hp_percent = max(0, min(1, battle_state["player_hp"] / (100 + battle_state["player"]["stats"]["defense"])))
        bar_width = 100
        player_hp_width = int(bar_width * player_hp_percent)
        
        draw.rectangle(
            [(player_x - 50, player_y - 100), (player_x + 50, player_y - 90)],
            outline=(255, 255, 255),
            width=1
        )
        draw.rectangle(
            [(player_x - 50, player_y - 100), (player_x - 50 + player_hp_width, player_y - 90)],
            fill=(0, 255, 0)
        )
        
        # Enemy health bar
        enemy_hp_percent = max(0, min(1, battle_state["infernal_hp"] / (100 + battle_state["infernal"]["level"] * 5)))
        enemy_hp_width = int(bar_width * enemy_hp_percent)
        
        draw.rectangle(
            [(enemy_x - 50, enemy_y - 100), (enemy_x + 50, enemy_y - 90)],
            outline=(255, 255, 255),
            width=1
        )
        draw.rectangle(
            [(enemy_x - 50, enemy_y - 100), (enemy_x - 50 + enemy_hp_width, enemy_y - 90)],
            fill=(255, 0, 0)
        )
        
        # Add battle effect if there was a recent action
        if len(battle_state["battle_log"]) > 0:
            effect_x = (player_x + enemy_x) // 2
            effect_y = (player_y + enemy_y) // 2
            
            # Draw a "burst" effect
            for i in range(10):
                radius = i * 5
                draw.arc(
                    [(effect_x - radius, effect_y - radius), 
                     (effect_x + radius, effect_y + radius)],
                    0, 360, fill=(255, 255, 0), width=2
                )
        
        # Convert to bytes for Discord
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        
        return buffer
        
    @fireforce.command(name="summon")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # Once per hour per user
    async def summon_infernal(self, ctx):
        """Summon a powerful Infernal for everyone to fight (server-wide event)"""
        # Check if user has a character
        character = await self.config.user(ctx.author).character()
        if character is None:
            return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
        
        # Check for any active infernals in the guild
        active_infernals = await self.config.guild(ctx.guild).active_infernals()
        if active_infernals:
            # Get most recent infernal
            recent_infernal = active_infernals[-1]
            spawn_time = recent_infernal.get("spawn_time", 0)
            current_time = int(datetime.now().timestamp())
            
            # If less than 30 minutes have passed, don't allow a new one
            if current_time - spawn_time < 1800:  # 30 minutes in seconds
                remaining = 1800 - (current_time - spawn_time)
                minutes = remaining // 60
                seconds = remaining % 60
                return await ctx.send(f"An Infernal was recently summoned! Please wait {minutes}m {seconds}s before summoning another.")
        
        # Generate a powerful infernal (3-5 levels higher than the summoner)
        level_boost = random.randint(3, 5)
        infernal = self._generate_infernal(character["level"] + level_boost)
        
        # Make it more powerful for a server event
        infernal["level"] += 2
        for stat in infernal["stats"]:
            infernal["stats"][stat] += random.randint(2, 5)
        
        # Add it to the active infernals list with timestamp
        infernal_data = {
            "infernal": infernal,
            "spawn_time": int(datetime.now().timestamp()),
            "summoner_id": ctx.author.id,
            "defeated_by": None,
            "participants": []
        }
        
        async with self.config.guild(ctx.guild).active_infernals() as active_infernals:
            active_infernals.append(infernal_data)
        
        # Create and send an announcement embed
        embed = discord.Embed(
            title="🔥 INFERNAL ALERT! 🔥",
            description=f"A powerful {infernal['name']} (Level {infernal['level']}) has appeared!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="Summoned By",
            value=ctx.author.mention,
            inline=True
        )
        
        embed.add_field(
            name="Challenge",
            value=f"Use `{ctx.prefix}fireforce engage` to battle this Infernal!\n"
                  f"The Infernal will remain for 30 minutes or until defeated.",
            inline=False
        )
        
        embed.set_footer(text="Server-wide event | Rewards for participation")
        
        await ctx.send(embed=embed)
        
        # Schedule automatic removal after 30 minutes
        self.bot.loop.create_task(self._schedule_infernal_removal(ctx.guild, len(active_infernals) - 1))

    async def _schedule_infernal_removal(self, guild, infernal_index):
        """Remove an infernal after 30 minutes if not defeated"""
        await asyncio.sleep(1800)  # 30 minutes
        
        # Check if infernal still exists and wasn't defeated
        active_infernals = await self.config.guild(guild).active_infernals()
        if len(active_infernals) > infernal_index:
            infernal_data = active_infernals[infernal_index]
            if infernal_data.get("defeated_by") is None:
                # Infernal wasn't defeated, remove it
                async with self.config.guild(guild).active_infernals() as infernals:
                    if len(infernals) > infernal_index:
                        infernals.pop(infernal_index)
                
                # Find a channel to send the notification
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send(f"The {infernal_data['infernal']['name']} has disappeared without being defeated!")
                        break

    @fireforce.command(name="engage")
    async def engage_infernal(self, ctx):
        """Battle against a server-wide Infernal event"""
        # Check if user has a character
        character = await self.config.user(ctx.author).character()
        if character is None:
            return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
        
        # Check if user is already in a battle
        if ctx.author.id in self.active_battles:
            return await ctx.send("You're already in a battle! Finish that one first.")
        
        # Check for active infernals
        active_infernals = await self.config.guild(ctx.guild).active_infernals()
        if not active_infernals:
            return await ctx.send("There are no active Infernals in this server. Use `[p]fireforce summon` to summon one.")
        
        # Get the most recent infernal
        infernal_data = active_infernals[-1]
        infernal = infernal_data["infernal"]
        
        # Check if this infernal has already been defeated
        if infernal_data.get("defeated_by") is not None:
            return await ctx.send(f"This {infernal['name']} has already been defeated by {ctx.guild.get_member(infernal_data['defeated_by']).display_name}!")
        
        # Check if user is already a participant
        if ctx.author.id in infernal_data.get("participants", []):
            return await ctx.send("You've already participated in battling this Infernal!")
        
        # Create battle state (with boosted HP for server event)
        battle_state = {
            "player": character,
            "infernal": infernal,
            "turn": 1,
            "player_hp": 100 + character['stats']['defense'],
            "infernal_hp": int((100 + infernal['level'] * 5) * 0.3),  # Reduced to 30% for server event battles
            "player_cooldowns": {},
            "infernal_cooldowns": {},
            "battle_log": [f"You engage the {infernal['name']}!"]
        }
        
        self.active_battles[ctx.author.id] = battle_state
        
        # Add user to participants
        async with self.config.guild(ctx.guild).active_infernals() as active_infernals:
            if "participants" not in active_infernals[-1]:
                active_infernals[-1]["participants"] = []
            active_infernals[-1]["participants"].append(ctx.author.id)
        
        # Start battle
        await self._run_infernal_event_battle(ctx, infernal_data)

    async def _run_infernal_event_battle(self, ctx, infernal_data):
        """Run a battle against a server event infernal"""
        battle_state = self.active_battles[ctx.author.id]
        
        # Create initial battle embed
        embed = self._create_battle_embed(battle_state)
        battle_msg = await ctx.send(embed=embed)
        
        # Add reaction controls
        for i in range(min(3, len(battle_state["player"]["abilities"]))):
            await battle_msg.add_reaction(f"{i+1}\u20e3")  # Number emoji
        
        # Battle loop
        while True:
            # Check if battle is over
            if battle_state["player_hp"] <= 0:
                await self._end_event_battle(ctx, False, infernal_data)  # Player lost
                break
                
            if battle_state["infernal_hp"] <= 0:
                await self._end_event_battle(ctx, True, infernal_data)  # Player won
                break
            
            # Wait for player's move selection
            def check(reaction, user):
                return (
                    user == ctx.author
                    and reaction.message.id == battle_msg.id
                    and str(reaction.emoji)[0] in "123"
                    and int(str(reaction.emoji)[0]) <= len(battle_state["player"]["abilities"])
                )
            
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=30.0)
                ability_index = int(str(reaction.emoji)[0]) - 1
                
                # Execute player's move
                await self._execute_player_move(ctx, battle_state, ability_index)
                
                # Update battle embed
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Check if battle is over after player's move
                if battle_state["infernal_hp"] <= 0:
                    await self._end_event_battle(ctx, True, infernal_data)  # Player won
                    break
                
                # Execute infernal's move
                await asyncio.sleep(1)  # Brief pause for effect
                await self._execute_infernal_move(ctx, battle_state)
                
                # Update battle embed again
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Increment turn counter
                battle_state["turn"] += 1
                
                # Update cooldowns
                for ability, cd in list(battle_state["player_cooldowns"].items()):
                    if cd > 0:
                        battle_state["player_cooldowns"][ability] -= 1
                    else:
                        del battle_state["player_cooldowns"][ability]
                
                for ability, cd in list(battle_state["infernal_cooldowns"].items()):
                    if cd > 0:
                        battle_state["infernal_cooldowns"][ability] -= 1
                    else:
                        del battle_state["infernal_cooldowns"][ability]
                
            except asyncio.TimeoutError:
                # Player took too long
                battle_state["battle_log"].append(f"{ctx.author.display_name} hesitated!")
                
                # Infernal attacks automatically
                await self._execute_infernal_move(ctx, battle_state)
                
                # Update battle embed
                embed = self._create_battle_embed(battle_state)
                await battle_msg.edit(embed=embed)
                
                # Check if battle is over
                if battle_state["player_hp"] <= 0:
                    await self._end_event_battle(ctx, False, infernal_data)  # Player lost
                    break
                
                # Increment turn counter
                battle_state["turn"] += 1

    async def _end_event_battle(self, ctx, victory: bool, infernal_data):
        """Handle end of event battle"""
        battle_state = self.active_battles[ctx.author.id]
        player = battle_state["player"]
        infernal = battle_state["infernal"]
        
        # Remove from active battles
        del self.active_battles[ctx.author.id]
        
        if victory:
            # Player defeated the infernal - mark as defeated in server data
            async with self.config.guild(ctx.guild).active_infernals() as active_infernals:
                for i, inf_data in enumerate(active_infernals):
                    if inf_data.get("spawn_time") == infernal_data.get("spawn_time"):
                        active_infernals[i]["defeated_by"] = ctx.author.id
                        break
            
            # Calculate increased rewards for defeating a server event
            exp_gain = 20 + infernal["level"] * 3 + infernal["difficulty"] * 8
            
            # Update player stats
            await self._award_experience(ctx.author, exp_gain)
            await self.config.user(ctx.author).battles.set(
                await self.config.user(ctx.author).battles() + 1
            )
            await self.config.user(ctx.author).wins.set(
                await self.config.user(ctx.author).wins() + 1
            )
            
            # Create victory embed
            embed = discord.Embed(
                title="🏆 Server Event Victory! 🏆",
                description=f"You defeated the {infernal['name']}!",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Experience Gained", value=f"+{exp_gain} EXP", inline=False)
            
            # Check for level up
            character = await self.config.user(ctx.author).character()
            if character["level"] > player["level"]:
                embed.add_field(
                    name="Level Up!",
                    value=f"You reached level {character['level']}!",
                    inline=False
                )
            
            # Server-wide announcement
            announcement = f"🔥 **EVENT CONCLUDED** 🔥\n{ctx.author.mention} has defeated the {infernal['name']}!"
            await ctx.send(announcement)
            
            await ctx.send(embed=embed)
            
        else:
            # Update player stats
            await self.config.user(ctx.author).battles.set(
                await self.config.user(ctx.author).battles() + 1
            )
            await self.config.user(ctx.author).losses.set(
                await self.config.user(ctx.author).losses() + 1
            )
            
            # Create defeat embed
            embed = discord.Embed(
                title="💀 Defeat 💀",
                description=f"You were defeated by the {infernal['name']}!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Event Continues",
                value="The Infernal is still active! Other members can continue to battle it.",
                inline=False
            )
            
            await ctx.send(embed=embed)

    @fireforce.command(name="status")
    async def server_status(self, ctx):
        """Check the status of active Infernals and server events"""
        # Get active infernals
        active_infernals = await self.config.guild(ctx.guild).active_infernals()
        
        if not active_infernals:
            return await ctx.send("There are no active Infernals or events in this server.")
        
        # Create embed
        embed = discord.Embed(
            title="🔥 Server Status 🔥",
            description=f"Active events in {ctx.guild.name}",
            color=discord.Color.orange()
        )
        
        # Add each active infernal to the embed
        for i, infernal_data in enumerate(active_infernals):
            infernal = infernal_data["infernal"]
            spawn_time = infernal_data.get("spawn_time", 0)
            spawn_time_str = f"<t:{spawn_time}:R>" if spawn_time else "Unknown"
            
            summoner_id = infernal_data.get("summoner_id")
            summoner = ctx.guild.get_member(summoner_id) if summoner_id else None
            summoner_str = summoner.mention if summoner else "Unknown"
            
            defeated_by_id = infernal_data.get("defeated_by")
            status = "Active" if defeated_by_id is None else "Defeated"
            
            participants = infernal_data.get("participants", [])
            participant_count = len(participants)
            
            description = (
                f"**Status**: {status}\n"
                f"**Summoned**: {spawn_time_str}\n"
                f"**Summoned By**: {summoner_str}\n"
                f"**Participants**: {participant_count}\n"
            )
            
            if defeated_by_id is not None:
                defeated_by = ctx.guild.get_member(defeated_by_id)
                defeated_by_str = defeated_by.mention if defeated_by else "Unknown"
                description += f"**Defeated By**: {defeated_by_str}\n"
            
            embed.add_field(
                name=f"{i+1}. {infernal['name']} (Level {infernal['level']})",
                value=description,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @fireforce.command(name="squad")
    @commands.cooldown(1, 86400, commands.BucketType.guild)  # Once per day per guild
    async def squadron_mission(self, ctx):
        """Start a Fire Force Squadron mission for all members"""
        # Check if user has a character
        character = await self.config.user(ctx.author).character()
        if character is None:
            return await ctx.send("You don't have a character yet! Create one with `[p]fireforce create <name>`.")
        
        # Start the mission
        embed = discord.Embed(
            title="🔥 Squadron Mission Alert 🔥",
            description="A squadron mission has been initiated! All Fire Force members can participate.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Mission",
            value="A large outbreak of Infernals has been reported downtown. The Special Fire Force has been dispatched to contain the situation.",
            inline=False
        )
        
        embed.add_field(
            name="How to Participate",
            value=f"React with 🔥 to this message to join the mission. You have 1 minute to join.",
            inline=False
        )
        
        # Post the announcement and collect participants
        mission_msg = await ctx.send(embed=embed)
        await mission_msg.add_reaction("🔥")
        
        try:
            # Wait for reactions for 1 minute
            await asyncio.sleep(60)
            
            # Get the message with reactions
            mission_msg = await ctx.channel.fetch_message(mission_msg.id)
            
            # Get users who reacted (except the bot)
            participants = []
            for reaction in mission_msg.reactions:
                if str(reaction.emoji) == "🔥":
                    users = await reaction.users().flatten()
                    participants = [user for user in users if not user.bot]
                    break
            
            if not participants:
                return await ctx.send("No one joined the mission. It has been cancelled.")
            
            # Run the squadron mission with all participants
            await self._run_squadron_mission(ctx, participants)
            
        except Exception as e:
            log.error(f"Error in squadron mission: {e}")
            await ctx.send("There was an error running the squadron mission. Please try again later.")

    async def _run_squadron_mission(self, ctx, participants):
        """Run a squadron mission with multiple participants"""
        # Check which participants have characters
        valid_participants = []
        for user in participants:
            character = await self.config.user(user).character()
            if character is not None:
                valid_participants.append((user, character))
        
        if not valid_participants:
            return await ctx.send("None of the participants have Fire Force characters. Mission cancelled.")
        
        # Generate mission difficulty based on average level
        avg_level = sum(char["level"] for _, char in valid_participants) // len(valid_participants)
        
        # Create progress messages
        mission_messages = [
            "The squadron arrives at the scene...",
            "Multiple Infernals detected in the area!",
            "The members split up to cover more ground...",
            "The battle against the Infernals intensifies!",
            "Squad members combine their attacks to push back the Infernals!",
        ]
        
        # Send mission progress with a delay
        progress_msg = await ctx.send(mission_messages[0])
        
        for i in range(1, len(mission_messages)):
            await asyncio.sleep(3)
            await progress_msg.edit(content=mission_messages[i])
        
        # Calculate mission results
        success_chance = min(95, 40 + (len(valid_participants) * 5) + (avg_level * 2))
        mission_success = random.randint(1, 100) <= success_chance
        
        # Award experience based on mission success
        base_exp = 15 + (avg_level * 2)
        if mission_success:
            exp_gain = base_exp * 2
            # Add a small chance for bonus rewards
            bonus_rewards = random.random() < 0.2
        else:
            exp_gain = base_exp // 2
            bonus_rewards = False
        
        # Final report embed
        embed = discord.Embed(
            title="🔥 Squadron Mission Report 🔥",
            description="Mission " + ("Successful! ✅" if mission_success else "Failed! ❌"),
            color=discord.Color.green() if mission_success else discord.Color.red()
        )
        
        # Add mission details
        if mission_success:
            embed.add_field(
                name="Mission Outcome",
                value="The squadron successfully contained the Infernal outbreak! The area has been secured.",
                inline=False
            )
        else:
            embed.add_field(
                name="Mission Outcome",
                value="The squadron struggled to contain all the Infernals. Additional forces had to be called in.",
                inline=False
            )
        
        # Participant contributions
        participants_text = ""
        for user, character in valid_participants:
            # Award experience
            await self._award_experience(user, exp_gain)
            
            # Update battle count
            await self.config.user(user).battles.set(
                await self.config.user(user).battles() + 1
            )
            
            # Add to the report
            participants_text += f"• {user.mention} ({character['name']}) - Earned {exp_gain} EXP\n"
        
        embed.add_field(
            name=f"Participants ({len(valid_participants)})",
            value=participants_text,
            inline=False
        )
        
        # Bonus rewards section
        if bonus_rewards:
            bonus_exp = exp_gain // 2
            lucky_user, lucky_char = random.choice(valid_participants)
            await self._award_experience(lucky_user, bonus_exp)
            
            embed.add_field(
                name="⭐ Bonus Reward ⭐",
                value=f"{lucky_user.mention} displayed exceptional skill and earned an additional {bonus_exp} EXP!",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        # Check for level ups
        for user, old_character in valid_participants:
            new_character = await self.config.user(user).character()
            if new_character["level"] > old_character["level"]:
                await ctx.send(f"🎉 {user.mention} leveled up to level {new_character['level']}!")

async def setup(bot):
    await bot.add_cog(FireForce(bot))
