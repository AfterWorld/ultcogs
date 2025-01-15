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
    "first_blood": {"description": "Claim your first victory in the arena!", "condition": "win", "count": 1},
    "big_hitter": {"description": "Deal a colossal 30+ damage in one blow!", "condition": "big_hit", "count": 1},
    "burn_master": {"description": "Inflict burn on your opponent 5 times in a single match!", "condition": "burns_applied", "count": 5},
    "comeback_king": {"description": "Clinch victory after dropping below 10 HP!", "condition": "comeback", "count": 1},
    "perfect_game": {"description": "Achieve a flawless victory without taking any damage!", "condition": "no_damage", "count": 1},
    "stunning_performance": {"description": "Stun your opponent 3 times in a single match!", "condition": "stuns", "count": 3},
    "overkill": {"description": "Deliver an overwhelming 50+ damage in a single hit!", "condition": "big_hit", "count": 1},
    "healing_touch": {"description": "Heal yourself for a total of 50 HP in one match!", "condition": "healing_done", "count": 50},
    "unstoppable": {"description": "Win 10 matches to prove your dominance!", "condition": "win", "count": 10},
    "burn_victim": {"description": "Suffer 30 damage from burn effects in a single match!", "condition": "burn_damage_taken", "count": 30},
    "lucky_strike": {"description": "Land 3 critical hits in a single match!", "condition": "crit_hits", "count": 3},
    "combo_master": {"description": "Land 5 consecutive hits without missing!", "condition": "combo_hits", "count": 5},
    "clutch_block": {"description": "Block an attack that would have been your demise!", "condition": "clutch_block", "count": 1},
    "sea_emperor": {"description": "Claim the title of Sea Emperor by winning 25 matches!", "condition": "win", "count": 25},
    "devil_fruit_user": {"description": "Unleash the power of 5 Devil Fruit moves in a single match!", "condition": "devil_fruit_moves", "count": 5},
    "flaming_fury": {"description": "Inflict maximum burn stacks (3) on your opponent!", "condition": "max_burn", "count": 1},
    "critical_king": {"description": "Land a critical hit on every turn of a match!", "condition": "all_crit_hits", "count": 1},
    "ultimate_victory": {"description": "Win a match while keeping your HP at 100!", "condition": "full_health_win", "count": 1},
    "rising_star": {"description": "Win 3 matches in a row!", "condition": "win_streak", "count": 3},
    "berserker_rage": {"description": "Land 10 hits in a single match!", "condition": "hits_landed", "count": 10},
    "tactical_genius": {"description": "Block 5 attacks in a single match!", "condition": "blocks", "count": 5},
    "haki_master": {"description": "Successfully use Haki-based moves 3 times in a single match!", "condition": "haki_moves", "count": 3},
    "death_defier": {"description": "Survive a match with only 1 HP remaining!", "condition": "low_health_survival", "count": 1},
    "fiery_torment": {"description": "Deal 50+ damage solely from burn effects!", "condition": "burn_damage_done", "count": 50},
    "miraculous_recovery": {"description": "Heal yourself for a total of 100 HP across all matches!", "condition": "total_healing_done", "count": 100},
    "strategic_victory": {"description": "Win a match by defeating your opponent using only effects like burn or stun!", "condition": "effect_based_win", "count": 1},
    "one_punch_champion": {"description": "Win a match with a single blow exceeding 50 damage!", "condition": "single_hit_win", "count": 1},
    "team_player": {"description": "Assist an ally by using healing or defensive moves 3 times!", "condition": "team_support", "count": 3},
    "fearless_fighter": {"description": "Never block an attack and still win the match!", "condition": "no_blocks_win", "count": 1},
    "endurance_champion": {"description": "Participate in a match lasting 20+ turns!", "condition": "long_match", "count": 1},
    "flawless_streak": {"description": "Win 5 matches in a row without taking damage!", "condition": "flawless_streak", "count": 5},
    "rookie_of_the_year": {"description": "Win your first 5 matches!", "condition": "early_wins", "count": 5},
    "explosive_finish": {"description": "End a match with an attack that exceeds the opponent's remaining HP by 20 or more!", "condition": "overkill_win", "count": 1},
    "frozen_fury": {"description": "Stun your opponent 5 times in one match!", "condition": "total_stuns", "count": 5},
    "adrenaline_rush": {"description": "Heal for more than 30 HP in a single turn!", "condition": "big_heal", "count": 1},
    "legendary_warrior": {"description": "Win 50 matches to cement your legacy!", "condition": "win", "count": 50},
    "iron_wall": {"description": "Block 20 attacks across all matches!", "condition": "total_blocks", "count": 20},
    "burning_legacy": {"description": "Inflict 100 burns across all matches!", "condition": "total_burns_applied", "count": 100},
    "damage_master": {"description": "Deal a total of 1000 damage across all matches!", "condition": "total_damage_dealt", "count": 1000},
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
    {"name": "Spicy Healing Curry", "type": "regular", "description": "Sanji's gourmet food revitalizes health!", "effect": "heal"},
    {"name": "Berserker Recovery", "type": "strong", "description": "A burst of willpower heals battle fatigue!", "effect": "heal"},
    {"name": "Haki Surge", "type": "critical", "description": "A burst of Conqueror's Haki restores the user's strength!", "effect": "heal"},
    {"name": "Self-Repair", "type": "strong", "description": "Franky repairs himself mid-battle, restoring some health!", "effect": "heal"},
    {"name": "Holy Touch", "type": "strong", "description": "A divine aura envelops the user, healing wounds!", "effect": "heal"},
    {"name": "Refresh", "type": "regular", "description": "A quick breather to regain strength!", "effect": "heal"},
    {"name": "Eternal Youth", "type": "critical", "description": "A mythical technique that restores significant health!", "effect": "heal"},
    {"name": "Battle Bandage", "type": "regular", "description": "Quickly applying first aid recovers some health!", "effect": "heal"},
    {"name": "Healing Bubble", "type": "regular", "description": "A magical bubble that rejuvenates vitality!", "effect": "heal"},
    {"name": "Rejuvenating Stance", "type": "strong", "description": "A calm stance that channels energy to heal!", "effect": "heal"},
    {"name": "Vitality Blossom", "type": "strong", "description": "A rare flower emits healing energy to restore health!", "effect": "heal"},
]

SEAS = ["West Blue", "East Blue", "North Blue", "Grand Line", "South Blue"]

class JoinButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Join Tournament", style=discord.ButtonStyle.primary)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        tournament = self.cog.tournaments[self.tournament_name]
        if interaction.user.id in tournament["participants"]:
            await interaction.response.send_message("❌ You are already in the tournament.", ephemeral=True)
            return

        tournament["participants"].append(interaction.user.id)
        await interaction.response.send_message(f"✅ You have joined the tournament `{self.tournament_name}`!", ephemeral=True)
        await self.cog.update_tournament_message(interaction.message, self.tournament_name)

class StartButton(discord.ui.Button):
    def __init__(self, tournament_name, cog):
        super().__init__(label="Start Tournament", style=discord.ButtonStyle.success)
        self.tournament_name = tournament_name
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        tournament = self.cog.tournaments[self.tournament_name]
        if tournament["creator"] != interaction.user.id:
            await interaction.response.send_message("❌ Only the creator of the tournament can start it.", ephemeral=True)
            return

        if len(tournament["participants"]) < 2:
            await interaction.response.send_message("❌ Tournament needs at least 2 participants to start.", ephemeral=True)
            return

        tournament["started"] = True
        await interaction.response.send_message(f"✅ Tournament `{self.tournament_name}` has started!", ephemeral=True)
        await self.cog.run_tournament(interaction.message.channel, self.tournament_name)

class TournamentView(discord.ui.View):
    def __init__(self, tournament_name, cog):
        super().__init__(timeout=None)
        self.add_item(JoinButton(tournament_name, cog))
        self.add_item(StartButton(tournament_name, cog))

class Deathmatch(commands.Cog):
    """A One Piece-themed deathbattle game with unique effects and achievements."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"wins": 0, "losses": 0, "damage_dealt": 0, "blocks": 0, "achievements": [], "sea": None}
        self.config.register_member(**default_member)
        self.active_channels = set()  # Track active battles by channel ID
        self.tournaments = {}  # Track active tournaments

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
        FONT_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/Deathmatch/fonts/onepiece.ttf"
    
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
        avatar_size = (250, 260)  # Adjust size to fully cover the white box
        avatar_positions = [(15, 130), (358, 130)]  # Coordinates for avatar placement
    
        # Username positions (under the avatars in grey boxes)
        username_positions = [(75, 410), (430, 410)]  # Coordinates for username placement
    
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


    @commands.command(name="deathstats")
    async def deathstat(self, ctx: commands.Context, member: discord.Member = None):
        """
        Display the stats and rank of a user.
        """
        member = member or ctx.author
        stats = await self.config.member(member).all()
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)
        rank = next((i for i, (m_id, _) in enumerate(sorted_members, start=1) if m_id == member.id), None)

        wins = stats["wins"]
        losses = stats["losses"]
        kdr = (wins / losses) if losses > 0 else wins

        embed = discord.Embed(
            title=f"🏴‍☠️ {member.display_name}'s Stats 🏴‍☠️",
            color=0x00FF00,
        )
        embed.add_field(name="Wins", value=wins, inline=True)
        embed.add_field(name="Losses", value=losses, inline=True)
        embed.add_field(name="KDR", value=f"{kdr:.2f}", inline=True)
        embed.add_field(name="Damage Dealt", value=stats["damage_dealt"], inline=True)
        embed.add_field(name="Blocks", value=stats["blocks"], inline=True)
        embed.add_field(name="Rank", value=f"#{rank}" if rank else "Unranked", inline=True)

        await ctx.send(embed=embed)

    # --- Core Battle Logic ---
    async def fight(self, ctx, challenger, opponent):
        """The main battle logic for the deathmatch."""
        # Initialize player data
        challenger_hp = 100
        opponent_hp = 100
        challenger_status = {"burn": 0, "stun": False}
        opponent_status = {"burn": 0, "stun": False}
    
        # Create the initial embed
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
    
        # Initialize stats
        attacker_stats = await self.config.member(challenger).all()
        defender_stats = await self.config.member(opponent).all()
    
        # Battle loop
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            attacker = players[turn_index]
            defender = players[1 - turn_index]
    
            # Apply burn damage
            burn_damage = await self.apply_burn_damage(defender)
            if burn_damage > 0:
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
    
            # Update stats for the attacker
            await self.update_stats(attacker, defender, damage, move, attacker_stats)
            await self.update_stats(defender, attacker, burn_damage, {"effect": "burn"}, defender_stats)
    
        # Determine winner
        winner = players[0] if players[0]["hp"] > 0 else players[1]
        loser = players[1] if players[0]["hp"] > 0 else players[0]
    
        # Update the embed for victory
        embed.title = "🏆 Victory!"
        embed.description = f"The battle is over! **{winner['name']}** is victorious!"
        embed.color = 0xFFD700  # Change to gold for victory
        embed.set_field_at(
            0,
            name="Final Health Bars",
            value=(
                f"**{players[0]['name']}:** {self.generate_health_bar(players[0]['hp'])} {players[0]['hp']}/100\n"
                f"**{players[1]['name']}:** {self.generate_health_bar(players[1]['hp'])} {players[1]['hp']}/100"
            ),
            inline=False,
        )
        await message.edit(embed=embed)
    
        # Update stats for the winner and loser
        await self.config.member(winner["member"]).wins.set(
            await self.config.member(winner["member"]).wins() + 1
        )
        await self.config.member(loser["member"]).losses.set(
            await self.config.member(loser["member"]).losses() + 1
        )
        await self.config.member(winner["member"]).damage_dealt.set(
            await self.config.member(winner["member"]).damage_dealt() + damage
        )
        await self.config.member(loser["member"]).blocks.set(
            await self.config.member(loser["member"]).blocks() + 1
        )

    async def apply_burn_damage(self, player):
        """Apply burn damage to a player if they have burn stacks."""
        if player["status"]["burn"] > 0:
            burn_damage = 5 * player["status"]["burn"]
            player["hp"] = max(0, player["hp"] - burn_damage)
            player["status"]["burn"] -= 1
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

    @commands.group(name="tournament", invoke_without_command=True)
    async def tournament(self, ctx: commands.Context):
        """Manage tournaments."""
        await ctx.send_help(ctx.command)

    def get_sea(self, member: discord.Member) -> str:
        """Get the sea of a member based on their roles."""
        for role in member.roles:
            if role.name in SEAS:
                return role.name
        return None

    @tournament.command(name="create")
    async def tournament_create(self, ctx: commands.Context, name: str, team_size: int = 1, double_elimination: bool = False):
        """Create a new tournament."""
        if name in self.tournaments:
            await ctx.send(f"❌ A tournament with the name `{name}` already exists.")
            return

        self.tournaments[name] = {
            "creator": ctx.author.id,
            "participants": [],
            "started": False,
            "team_size": team_size,
            "double_elimination": double_elimination,
            "bracket": [],
            "losers_bracket": [],
            "statistics": {
                "total_matches": 0,
                "average_match_duration": 0,
                "most_used_moves": {},
            },
        }
        await self.send_tournament_message(ctx, name)

    async def send_tournament_message(self, ctx: commands.Context, name: str):
        """Send a message with buttons to join and start the tournament."""
        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {ctx.author.display_name}\nParticipants: 0/0",
            color=0x00FF00,
        )
        view = TournamentView(name, self)
        await ctx.send(embed=embed, view=view)

    async def update_tournament_message(self, message: discord.Message, name: str):
        """Update the tournament message with the current number of participants."""
        tournament = self.tournaments[name]
        creator = message.guild.get_member(tournament["creator"])
        participants = [message.guild.get_member(pid) for pid in tournament["participants"]]

        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.display_name if creator else 'Unknown'}\nParticipants: {len(participants)}/{len(participants)}",
            color=0x00FF00,
        )
        embed.add_field(name="Participants", value="\n".join([p.display_name for p in participants if p]), inline=False)
        await message.edit(embed=embed)

    @tournament.command(name="view")
    async def tournament_view(self, ctx: commands.Context, name: str):
        """View the details of a tournament."""
        if name not in self.tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return

        tournament = self.tournaments[name]
        creator = ctx.guild.get_member(tournament["creator"])
        participants = [ctx.guild.get_member(pid) for pid in tournament["participants"]]

        embed = discord.Embed(
            title=f"Tournament: {name}",
            description=f"Creator: {creator.display_name if creator else 'Unknown'}\nParticipants: {len(participants)}/{len(participants)}",
            color=0x00FF00,
        )
        embed.add_field(name="Participants", value="\n".join([p.display_name for p in participants if p]), inline=False)
        view = TournamentView(name, self)
        await ctx.send(embed=embed, view=view)

    @tournament.command(name="bracket")
    async def tournament_bracket(self, ctx: commands.Context, name: str):
        """View the tournament bracket."""
        if name not in self.tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return

        tournament = self.tournaments[name]
        bracket = tournament["bracket"]
        losers_bracket = tournament["losers_bracket"]

        embed = discord.Embed(
            title=f"Tournament Bracket: {name}",
            color=0x00FF00,
        )
        for round_num, matches in enumerate(bracket, start=1):
            match_list = "\n".join([f"{match[0]} vs {match[1]}" for match in matches])
            embed.add_field(name=f"Round {round_num}", value=match_list, inline=False)

        if tournament["double_elimination"]:
            for round_num, matches in enumerate(losers_bracket, start=1):
                match_list = "\n".join([f"{match[0]} vs {match[1]}" for match in matches])
                embed.add_field(name=f"Losers Round {round_num}", value=match_list, inline=False)

        await ctx.send(embed=embed)

    @tournament.command(name="stats")
    async def tournament_stats(self, ctx: commands.Context, name: str):
        """View the tournament statistics."""
        if name not in self.tournaments:
            await ctx.send(f"❌ No tournament found with the name `{name}`.")
            return

        tournament = self.tournaments[name]
        stats = tournament["statistics"]

        embed = discord.Embed(
            title=f"Tournament Statistics: {name}",
            color=0x00FF00,
        )
        embed.add_field(name="Total Matches", value=stats["total_matches"], inline=True)
        embed.add_field(name="Average Match Duration", value=f"{stats['average_match_duration']:.2f} seconds", inline=True)
        most_used_moves = "\n".join([f"{move}: {count}" for move, count in stats["most_used_moves"].items()])
        embed.add_field(name="Most Used Moves", value=most_used_moves if most_used_moves else "None", inline=False)

        await ctx.send(embed=embed)

    async def run_tournament(self, channel: discord.TextChannel, name: str):
        """Run the tournament matches."""
        if channel.id in self.active_channels:
            await channel.send("❌ A battle is already in progress in this channel. Please wait for it to finish.")
            return

        # Mark the channel as active
        self.active_channels.add(channel.id)

        tournament = self.tournaments[name]
        participants = tournament["participants"]
        team_size = tournament["team_size"]
        double_elimination = tournament["double_elimination"]

        sea_groups = {sea: [] for sea in SEAS}
        for pid in participants:
            member = channel.guild.get_member(pid)
            sea = self.get_sea(member)
            if sea:
                sea_groups[sea].append(member)

        # Create initial bracket
        bracket = self.create_bracket(participants, team_size)
        tournament["bracket"] = bracket

        if double_elimination:
            losers_bracket = []
            tournament["losers_bracket"] = losers_bracket

        while len(participants) > 1:
            for round_num, matches in enumerate(bracket):
                for match in matches:
                    player1 = channel.guild.get_member(match[0])
                    player2 = channel.guild.get_member(match[1])
                    sea1 = self.get_sea(player1)
                    sea2 = self.get_sea(player2)

                    if sea1 == sea2:
                        await channel.send(f"⚔️ Match: **{player1.display_name}** vs **AI Opponent**")
                        winner = await self.run_ai_match(channel, player1)
                    else:
                        await channel.send(f"⚔️ Match: **{player1.display_name}** vs **{player2.display_name}**")
                        winner = await self.run_match(channel, player1, player2)

                    await channel.send(f"🏆 Winner: **{winner.display_name}**")
                    participants.remove(player1.id if winner == player2 else player2.id)

                    if double_elimination:
                        losers_bracket.append((player1.id if winner == player2 else player2.id,))

        winner = channel.guild.get_member(participants[0])
        await channel.send(f"🎉 The winner of the tournament `{name}` is **{winner.display_name}**!")
        del self.tournaments[name]

        # Mark the channel as inactive
        self.active_channels.remove(channel.id)

    def create_bracket(self, participants, team_size):
        """Create the initial tournament bracket."""
        random.shuffle(participants)
        bracket = []
        for i in range(0, len(participants), team_size * 2):
            match = participants[i:i + team_size * 2]
            if len(match) == team_size * 2:
                bracket.append((match[:team_size], match[team_size:]))
        return bracket

    async def run_match(self, channel: discord.TextChannel, player1: discord.Member, player2: discord.Member):
        """Run a single match between two players or a player and an AI opponent."""
        # Initialize player data
        player1_hp = 100
        player2_hp = 100 if player2 else 50  # AI opponent has less HP
        player1_status = {"burn": 0, "stun": False}
        player2_status = {"burn": 0, "stun": False} if player2 else {}

        # Create the initial embed
        embed = discord.Embed(
            title="🏴‍☠️ One Piece deathbattle ⚔️",
            description=f"Battle begins between **{player1.display_name}** and **{player2.display_name if player2 else 'AI Opponent'}**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="Health Bars",
            value=(
                f"**{player1.display_name}:** {self.generate_health_bar(player1_hp)} {player1_hp}/100\n"
                f"**{player2.display_name if player2 else 'AI Opponent'}:** {self.generate_health_bar(player2_hp)} {player2_hp}/100"
            ),
            inline=False,
        )
        embed.set_footer(text="Actions are automatic!")
        message = await channel.send(embed=embed)

        # Player data structure
        players = [
            {"name": player1.display_name, "hp": player1_hp, "status": player1_status, "member": player1},
            {"name": player2.display_name if player2 else "AI Opponent", "hp": player2_hp, "status": player2_status, "member": player2},
        ]
        turn_index = 0

        # Battle loop
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            attacker = players[turn_index]
            defender = players[1 - turn_index]

            # Apply burn damage
            burn_damage = await self.apply_burn_damage(defender)
            if burn_damage > 0:
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Skip turn if stunned
            if defender["status"].get("stun"):
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
        return winner["member"]

    async def run_ai_match(self, channel: discord.TextChannel, player: discord.Member):
        """Run a single match between a player and an AI opponent."""
        # Initialize player data
        player_hp = 100
        ai_hp = 50  # AI opponent has less HP
        player_status = {"burn": 0, "stun": False}
        ai_status = {"burn": 0, "stun": False}

        # Create the initial embed
        embed = discord.Embed(
            title="🏴‍☠️ One Piece deathbattle ⚔️",
            description=f"Battle begins between **{player.display_name}** and **AI Opponent**!",
            color=0x00FF00,
        )
        embed.add_field(
            name="Health Bars",
            value=(
                f"**{player.display_name}:** {self.generate_health_bar(player_hp)} {player_hp}/100\n"
                f"**AI Opponent:** {self.generate_health_bar(ai_hp)} {ai_hp}/50"
            ),
            inline=False,
        )
        embed.set_footer(text="Actions are automatic!")
        message = await channel.send(embed=embed)

        # Player data structure
        players = [
            {"name": player.display_name, "hp": player_hp, "status": player_status, "member": player},
            {"name": "AI Opponent", "hp": ai_hp, "status": ai_status, "member": None},
        ]
        turn_index = 0

        # Battle loop
        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            attacker = players[turn_index]
            defender = players[1 - turn_index]

            # Apply burn damage
            burn_damage = await self.apply_burn_damage(defender)
            if burn_damage > 0:
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Skip turn if stunned
            if defender["status"].get("stun"):
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
                    f"**{players[1]['name']}:** {self.generate_health_bar(players[1]['hp'])} {players[1]['hp']}/50"
                ),
                inline=False,
            )
            await message.edit(embed=embed)
            await asyncio.sleep(2)
            turn_index = 1 - turn_index

        # Determine winner
        winner = players[0] if players[0]["hp"] > 0 else players[1]
        return winner["member"]
