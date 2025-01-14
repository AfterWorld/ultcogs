from redbot.core.utils.menus import menu, commands, DEFAULT_CONTROLS
from redbot.core import commands, Config
import discord
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# --- Constants ---
ACHIEVEMENTS = {
    "first_blood": {"description": "Win your first match!", "condition": "win", "count": 1},
    "big_hitter": {"description": "Deal over 30 damage in one hit!", "condition": "big_hit", "count": 1},
    "burn_master": {"description": "Inflict burn 5 times in a match!", "condition": "burns_applied", "count": 5},
    "comeback_king": {"description": "Win a match after dropping below 10 HP!", "condition": "comeback", "count": 1},
    "perfect_game": {"description": "Win without taking any damage!", "condition": "no_damage", "count": 1},
    "stunning_performance": {"description": "Stun your opponent 3 times in a single match!", "condition": "stuns", "count": 3},
    "overkill": {"description": "Deal over 50 damage in one hit!", "condition": "big_hit", "count": 50},
    "healing_touch": {"description": "Heal yourself for 50 HP in a single match!", "condition": "healing_done", "count": 50},
    "unstoppable": {"description": "Win 10 matches!", "condition": "win", "count": 10},
    "burn_victim": {"description": "Take 30 damage from burn in a single match!", "condition": "burn_damage_taken", "count": 30},
    "lucky_strike": {"description": "Land 3 critical hits in a single match!", "condition": "crit_hits", "count": 3},
    "combo_master": {"description": "Land 5 hits in a row without missing!", "condition": "combo_hits", "count": 5},
    "clutch_block": {"description": "Block an attack that would have defeated you!", "condition": "clutch_block", "count": 1},
    "sea_emperor": {"description": "Win 25 matches!", "condition": "win", "count": 25},
    "devil_fruit_user": {"description": "Use 5 Devil Fruit moves in a single match!", "condition": "devil_fruit_moves", "count": 5},
    "flaming_fury": {"description": "Inflict 3 stacks of burn on your opponent!", "condition": "max_burn", "count": 1},
    "critical_king": {"description": "Land a critical hit in every turn of a match!", "condition": "all_crit_hits", "count": 1},
    "ultimate_victory": {"description": "Win a match with your HP at 100!", "condition": "full_health_win", "count": 1},
}

MOVES = [
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": None},
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": None},
    {"name": "Diable Jambe", "type": "regular", "description": "Sanji's fiery kick!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Clown Bombs", "type": "regular", "description": "Buggy's explosive prank!", "effect": None},
    {"name": "Heavy Point", "type": "strong", "description": "Chopper smashes his enemy!", "effect": "heal"},
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "crit"},
    {"name": "Soul Solid", "type": "regular", "description": "Brook plays a chilling tune!", "effect": "burn", "burn_chance": 0.20},
    {"name": "Pop Green", "type": "regular", "description": "Usopp's plant barrage!", "effect": None},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Room Shambles", "type": "critical", "description": "Law's surgical strike!", "effect": "stun"},
    {"name": "Dark Vortex", "type": "strong", "description": "Blackbeard's gravity attack!", "effect": None},
    {"name": "Conqueror's Haki", "type": "critical", "description": "Overwhelms your opponent!", "effect": "stun"},
    {"name": "Red Hawk", "type": "strong", "description": "Luffy's fiery attack!", "effect": "burn", "burn_chance": 0.25},
    {"name": "Ice Age", "type": "regular", "description": "Aokiji freezes the battlefield!", "effect": "stun"},
    {"name": "Magma Fist", "type": "strong", "description": "Akainu's devastating magma punch!", "effect": "burn", "burn_chance": 0.45},
    {"name": "Coup de Vent", "type": "regular", "description": "Franky's air cannon!", "effect": "crit"},
    {"name": "Clutch", "type": "regular", "description": "Robin's multi-hand grab!", "effect": "stun"},
    {"name": "Elephant Gun", "type": "strong", "description": "Luffy's giant fist!", "effect": None},
    {"name": "Enel's Judgement", "type": "critical", "description": "Thunder god's ultimate strike!", "effect": "burn", "burn_chance": 0.15},
    {"name": "Pirate King's Will", "type": "regular", "description": "A legendary strike filled with willpower!", "effect": None},
    {"name": "Gomu Gomu no Bazooka", "type": "strong", "description": "Luffy's iconic double-handed smash!", "effect": None},
    {"name": "Hiryu Kaen", "type": "critical", "description": "Zoro's flaming dragon slash!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Hell Memories", "type": "critical", "description": "Sanji unleashes a fiery kick fueled by rage!", "effect": "burn", "burn_chance": 0.50},
    {"name": "Takt", "type": "regular", "description": "Law telekinetically slams debris onto the opponent!", "effect": None},
    {"name": "Shigan", "type": "regular", "description": "Lucci's powerful finger pistol technique!", "effect": "crit"},
    {"name": "Yasakani no Magatama", "type": "strong", "description": "Kizaru rains down a flurry of light-based attacks!", "effect": "crit"},
    {"name": "Venom Demon: Hell's Judgement", "type": "critical", "description": "Magellan unleashes a devastating poisonous assault!", "effect": "burn", "burn_chance": 0.45},
    {"name": "King Kong Gun", "type": "critical", "description": "Luffy's massive Gear Fourth punch!", "effect": None},
    {"name": "Black Hole", "type": "strong", "description": "Blackbeard absorbs everything into darkness!", "effect": None},
    {"name": "Raging Tiger", "type": "regular", "description": "Jinbei punches with the force of a tidal wave!", "effect": None},
    {"name": "Rokushiki: Rokuogan", "type": "critical", "description": "Lucci unleashes a devastating shockwave with pure power!", "effect": None},
    {"name": "Raigo", "type": "critical", "description": "Enel calls down a massive thunder strike!", "effect": "burn", "burn_chance": 0.35},
    {"name": "Ashura: Ichibugin", "type": "critical", "description": "Zoro's nine-sword style cuts through everything in its path!", "effect": None},
    {"name": "Divine Departure", "type": "critical", "description": "Gol D. Roger's legendary strike devastates the battlefield!", "effect": "stun"},
    {"name": "Red Roc", "type": "critical", "description": "Luffy launches a fiery Haki-infused punch!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Puncture Wille", "type": "critical", "description": "Law pierces his enemy with a massive Haki-enhanced attack!", "effect": "stun"},
    {"name": "Shin Tenjin", "type": "critical", "description": "Franky's ultimate laser cannon obliterates everything in its path!", "effect": None},
    {"name": "Meteors of Destruction", "type": "critical", "description": "Fujitora summons a rain of meteors to crush his enemies!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Dragon Twister: Gale of Destruction", "type": "critical", "description": "Kaido spins in a tornado of destruction!", "effect": None},
    {"name": "Yoru Strike: Eternal Night", "type": "critical", "description": "Mihawk's ultimate slash creates darkness and devastation!", "effect": "stun"},
]


class Deathmatch(commands.Cog):
    """A One Piece-themed deathbattle game with unique effects and achievements."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"wins": 0, "damage_dealt": 0, "blocks": 0, "achievements": []}
        self.config.register_member(**default_member)
        self.active_channels = set()  # Track active battles by channel ID

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
    
            # Scale by player's wins (optional)
            if stats:
                wins = stats.get("wins", 0)
                base_damage += min(wins // 5, 10)  # Max bonus capped at 10
    
        return base_damage

    def generate_fight_card(self, user1, user2):
        """
        Generates a dynamic fight card image with avatars and usernames.
        :param user1: (discord.Member) First user in the battle.
        :param user2: (discord.Member) Second user in the battle.
        :return: BytesIO object of the generated image.
        """
        TEMPLATE_URL = "https://raw.githubusercontent.com/AfterWorld/ultcogs/refs/heads/main/deathmatch/deathbattle.png"
        FONT_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/Deathmatch/fonts/arial.ttf"
    
        # Download the template
        response = requests.get(TEMPLATE_URL)
        if response.status_code != 200:
            raise FileNotFoundError(f"Could not fetch template from {TEMPLATE_URL}")
    
        # Open the template as an image
        template = Image.open(BytesIO(response.content))
        draw = ImageDraw.Draw(template)
    
        # Load fonts
        try:
            username_font = ImageFont.truetype(FONT_PATH, 25)  # Adjust font size as needed
        except OSError:
            raise FileNotFoundError(f"Font file not found at {FONT_PATH}")
    
        # Avatar dimensions and positions
        avatar_size = (400, 400)  # Adjust size to fully cover the white box
        avatar_positions = [(100, 100), (100, 100)]  # Coordinates for avatar placement
    
        # Username positions (under the avatars in grey boxes)
        username_positions = [(50, 260), (500, 260)]  # Coordinates for username placement
    
        # Fetch, resize, and paste avatars
        for i, user in enumerate((user1, user2)):
            # Fetch avatar
            avatar_response = requests.get(user.display_avatar.url)
            avatar = Image.open(BytesIO(avatar_response.content)).convert("RGBA")
            avatar = avatar.resize(avatar_size)  # Resize to match white box size
    
            # Paste avatar onto the template
            template.paste(avatar, avatar_positions[i], avatar)  # Supports transparency
    
            # Draw username in the grey box below the avatar
            draw.text(username_positions[i], user.display_name, font=username_font, fill="black")
    
        # Save to BytesIO for Discord
        output = BytesIO()
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

    async def check_achievements(self, member, stats):
        """Check and unlock achievements for the member."""
        user_achievements = await self.config.member(member).achievements()
        unlocked = []
        for key, data in ACHIEVEMENTS.items():
            if key in user_achievements:
                continue  # Already unlocked
            if stats.get(data["condition"], 0) >= data["count"]:
                user_achievements.append(key)
                unlocked.append(data["description"])
        await self.config.member(member).achievements.set(user_achievements)
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
        
    # --- Main Commands ---
    @commands.hybrid_command(name="deathbattle")
    async def deathbattle(self, ctx: commands.Context, opponent: discord.Member):
        """
        Start a One Piece deathmatch against another user.
        """
        # Prevent invalid matches
        if ctx.author == opponent:
            await ctx.send("❌ You cannot challenge yourself to a deathmatch!")
            return
        if opponent == ctx.guild.me:
            await ctx.send("❌ You cannot challenge the bot to a deathmatch!")
            return
    
        # Generate fight card
        fight_card = self.generate_fight_card(ctx.author, opponent)
    
        # Send the dynamically generated fight card image
        await ctx.send(file=discord.File(fp=fight_card, filename="fight_card.png"))
    
        # Proceed with fight logic if applicable...
        await self.fight(ctx, ctx.author, opponent)


    @commands.command(name="deathboard")
    async def deathboard(self, ctx: commands.Context):
        """Show the deathboard."""
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)

        embed = discord.Embed(title="🏆 Deathboard 🏆", color=0xFFD700)
        for i, (member_id, data) in enumerate(sorted_members[:10], start=1):
            member = ctx.guild.get_member(member_id)
            if member:
                embed.add_field(
                    name=f"{i}. {member.display_name}",
                    value=f"Wins: {data['wins']}",
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
                
    @commands.command(name="achievements")
    async def achievements(self, ctx: commands.Context, member: discord.Member = None):
        """
        Show all achievements for a user in a paginated format.
        """
        member = member or ctx.author
        unlocked_achievements = await self.config.member(member).achievements()
        stats = await self.config.member(member).all()
    
        # Build the list of achievements
        pages = []
        for key, data in ACHIEVEMENTS.items():
            if key in unlocked_achievements:
                status = f"🔓 **Unlocked!** 🎉"
            else:
                progress = stats.get(data["condition"], 0)
                status = f"🔒 *Locked* (Progress: {progress}/{data['count']})"
    
            achievement_text = (
                f"🎯 **{data['description']}**\n"
                f"- **Status:** {status}\n"
                f"- Use `.achievementinfo {key}` to learn more!\n"
            )
            pages.append(achievement_text)
    
        # Chunk achievements into groups of 5 per page
        chunk_size = 5
        paginated_pages = [pages[i:i + chunk_size] for i in range(0, len(pages), chunk_size)]
    
        embeds = []
        for page_number, chunk in enumerate(paginated_pages, start=1):
            embed = discord.Embed(
                title=f"🏴‍☠️ {member.display_name}'s Achievements 🏴‍☠️",
                description="\n".join(chunk),
                color=0x00FF00,
            )
            embed.set_footer(text=f"Page {page_number}/{len(paginated_pages)}")
            embeds.append(embed)
    
        # Use Redbot's pagination utility
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @commands.command(name="achievementinfo")
    async def achievementinfo(self, ctx: commands.Context, achievement_name: str):
        """Get detailed information about how to unlock a specific achievement."""
        achievement = next(
            (data for key, data in ACHIEVEMENTS.items() if achievement_name.lower() in data["description"].lower()),
            None,
        )

        if not achievement:
            await ctx.send(f"❌ No achievement found matching `{achievement_name}`.")
            return

        embed = discord.Embed(
            title=f"🎯 Achievement Info: {achievement['description']}",
            description=(
                f"**Unlock Requirement:**\n"
                f"- **Condition:** {achievement['condition']}\n"
                f"- **Count Needed:** {achievement['count']}\n\n"
                f"Keep battling to achieve greatness!"
            ),
            color=0x00FF00,
        )
        await ctx.send(embed=embed)


    # --- Core Battle Logic ---
    async def fight(self, ctx, challenger, opponent):
        """The main battle logic for the deathbattle."""
        # Initialize player data
        challenger_hp = 100
        opponent_hp = 100
        challenger_status = {"burn": 0, "stun": False}
        opponent_status = {"burn": 0, "stun": False}

        embed = discord.Embed(
            title="🏴‍☠️ One Piece deathbattle ⚔️",
            description=f"Battle begins between **{challenger.display_name}** and **{opponent.display_name}**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="Health Bars",
            value=(
                f"**{challenger.display_name}:** {self.generate_health_bar(challenger_hp)} {challenger_hp}/100\n"
                f"**{opponent.display_name}:** {self.generate_health_bar(opponent_hp)} {opponent_hp}/100"
            ),
            inline=False,
        )
        embed.set_footer(text="Actions are automatic!")
        message = await ctx.send(embed=embed)

        # Player data structure
        players = [
            {"name": challenger.display_name, "hp": challenger_hp, "status": challenger_status, "member": challenger},
            {"name": opponent.display_name, "hp": opponent_hp, "status": opponent_status, "member": opponent},
        ]
        turn_index = 0

        # Battle loop
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            attacker = players[turn_index]
            defender = players[1 - turn_index]

            # Burn damage
            if defender["status"]["burn"] > 0:
                burn_damage = 5 * defender["status"]["burn"]
                defender["hp"] = max(0, defender["hp"] - burn_damage)
                defender["status"]["burn"] -= 1
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Skip turn if stunned
            if defender["status"]["stun"]:
                defender["status"]["stun"] = False  # Stun only lasts one turn
                embed.description = f"⚡ **{defender['name']}** is stunned and cannot act!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                turn_index = 1 - turn_index
                continue

            # Select move
            move = random.choice(MOVES)
            damage = self.calculate_damage(move["type"])
            await self.apply_effects(move, attacker, defender)

            # Apply damage
            defender["hp"] = max(0, defender["hp"] - damage)
            embed.description = (
                f"**{attacker['name']}** used **{move['name']}**: {move['description']} "
                f"and dealt **{damage}** damage to **{defender['name']}**!"
            )
            embed.set_field_at(
                0,
                name="Health Bars",
                value=(
                    f"**{players[0]['name']}:** {self.generate_health_bar(players[0]['hp'])} {players[0]['hp']}/100\n"
                    f"**{players[1]['name']}:** {self.generate_health_bar(players[1]['hp'])} {players[1]['hp']}/100"
                ),
                inline=False,
            )
            await message.edit(embed=embed)
            await asyncio.sleep(2)
            turn_index = 1 - turn_index

        # Determine winner
        winner = players[0] if players[0]["hp"] > 0 else players[1]
        embed = discord.Embed(
            title="🏆 Victory!",
            description=f"The battle is over! **{winner['name']}** is victorious!",
            color=0xFFD700,
        )
        embed.add_field(
            name="Final Health Bars",
            value=(
                f"**{players[0]['name']}:** {self.generate_health_bar(players[0]['hp'])} {players[0]['hp']}/100\n"
                f"**{players[1]['name']}:** {self.generate_health_bar(players[1]['hp'])} {players[1]['hp']}/100"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

        # Update stats for the winner
        await self.config.member(winner["member"]).wins.set(
            await self.config.member(winner["member"]).wins() + 1
        )

    async def update_stats(self, attacker, defender, damage, move, stats):
        """Update the statistics for achievements and overall tracking."""
        if damage >= 30:  # Big hit condition
            stats["big_hit"] = stats.get("big_hit", 0) + 1
        if move.get("effect") == "burn":
            stats["burns_applied"] = stats.get("burns_applied", 0) + 1
        if defender["hp"] <= 0 and stats.get("clutch_block", 0) == 0:  # Clutch block logic
            stats["clutch_block"] = 1
        stats["damage_dealt"] = stats.get("damage_dealt", 0) + damage

    async def reset_player_stats(self, member):
        """Reset a player's statistics for testing or fairness."""
        await self.config.member(member).set({"wins": 0, "damage_dealt": 0, "blocks": 0, "achievements": []})

    async def reset_all_stats(self, guild):
        """Reset all statistics in the guild."""
        all_members = await self.config.all_members(guild)
        for member_id in all_members:
            member = guild.get_member(member_id)
            if member:
                await self.reset_player_stats(member)
