from redbot.core import commands, Config
from redbot.core.bot import Red
import discord
import random
import asyncio

ACHIEVEMENTS = {
    "first_blood": {"description": "Win your first match!", "condition": "win", "count": 1},
    "block_master": {"description": "Block 5 attacks in a single match.", "condition": "blocks", "count": 5},
    "big_hitter": {"description": "Deal over 50 damage in one hit!", "condition": "big_hit", "count": 1},
    "iron_wall": {"description": "Block 10 attacks in total.", "condition": "blocks_total", "count": 10},
    "survivor": {"description": "Win a match with less than 10 HP remaining!", "condition": "close_call", "count": 1},
    "devil_fruit_user": {"description": "Use 5 devil fruit-based moves in one match.", "condition": "devil_fruit_moves", "count": 5},
    "perfect_game": {"description": "Win without taking any damage!", "condition": "no_damage", "count": 1},
    "comeback_king": {"description": "Win a match after your HP drops below 20.", "condition": "comeback", "count": 1},
    "combo_master": {"description": "Land 3 big hits in one match.", "condition": "big_hit_streak", "count": 3},
}

MOVES = [
    {"name": "Rubber Rocket", "base_damage": random.randint(10, 30), "description": "Luffy's stretchy punch!"},
    {"name": "Santoryu Onigiri", "base_damage": random.randint(20, 40), "description": "Zoro's powerful sword slash!"},
    {"name": "Diable Jambe", "base_damage": random.randint(15, 35), "description": "Sanji's flaming kick!"},
    {"name": "Clown Bombs", "base_damage": random.randint(10, 25), "description": "Buggy's comical explosive attack!"},
    {"name": "Soul King's Song", "base_damage": random.randint(10, 30), "description": "Brook sings a chilling tune to attack!"},
    {"name": "Pop Green Barrage", "base_damage": random.randint(10, 25), "description": "Usopp's explosive plant attack!"},
    {"name": "Chopper's Heavy Point", "base_damage": random.randint(20, 40), "description": "Chopper transforms into a powerhouse!"},
    {"name": "Franky's Coup de Vent", "base_damage": random.randint(15, 35), "description": "Franky unleashes his iconic air cannon!"},
    {"name": "Robin's Clutch", "base_damage": random.randint(20, 35), "description": "Robin grabs her opponent with extra hands!"},
    {"name": "Thunder Bagua", "base_damage": random.randint(25, 50), "description": "Kaido delivers a devastating blow!"},
]


class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with achievements and funny abilities!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"achievements": []}
        self.config.register_member(**default_member)

    def generate_health_bar(self, current_hp: int, max_hp: int = 100, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"

    async def check_achievements(self, user, stats):
        """Check and unlock achievements for the user."""
        unlocked = []
        user_achievements = await self.config.member(user).achievements()

        for key, achievement in ACHIEVEMENTS.items():
            if key in user_achievements:
                continue  # Skip already unlocked achievements

            condition = achievement["condition"]
            required_count = achievement["count"]

            # Handle special cases
            if condition == "close_call" and stats.get("win", 0) == 1 and stats.get("remaining_hp", 100) < 10:
                unlocked.append(key)
                user_achievements.append(key)
                await self.notify_achievement(user, achievement["description"])

            elif stats.get(condition, 0) >= required_count:
                unlocked.append(key)
                user_achievements.append(key)
                await self.notify_achievement(user, achievement["description"])

        await self.config.member(user).achievements.set(user_achievements)

    async def notify_achievement(self, user, description):
        """Notify a user of an unlocked achievement."""
        embed = discord.Embed(
            title="🎉 Achievement Unlocked!",
            description=description,
            color=0xFFD700,
        )
        await user.send(embed=embed)

    @commands.guild_only()
    @commands.hybrid_command(name="deathmatch")
    async def deathmatch(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another user to a One Piece deathmatch!"""
        challenger = ctx.author

        if challenger == opponent:
            await ctx.send("You can't challenge yourself to a deathmatch!")
            return

        challenger_hp = 100
        opponent_hp = 100
        stats = {"win": 0, "blocks": 0, "big_hit": 0}

        embed = discord.Embed(
            title="⚔️ One Piece Deathmatch",
            description=f"The battle between **{challenger.display_name}** and **{opponent.display_name}** begins!",
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
        embed.set_footer(text="Actions will happen automatically!")
        message = await ctx.send(embed=embed)

        players = [(challenger, challenger_hp), (opponent, opponent_hp)]
        turn_index = 0

        while players[0][1] > 0 and players[1][1] > 0:
            attacker, attacker_hp = players[turn_index]
            defender, defender_hp = players[1 - turn_index]

            # Randomly select a move
            move = random.choice(MOVES)
            damage = move["base_damage"]
            description = move["description"]

            # Random chance for special effects
            infused_with_haki = random.random() < 0.25  # 25% chance to infuse attack with haki
            blocked_by_haki = random.random() < 0.2  # 20% chance to block the attack

            if infused_with_haki:
                damage += 10
                description += " (Infused with Haki!)"

            if blocked_by_haki:
                damage = 0
                description = f"{defender.display_name} blocked the attack with Haki!"
                stats["blocks"] += 1

            defender_hp = max(0, defender_hp - damage)  # Ensure HP does not go below 0
            players[1 - turn_index] = (defender, defender_hp)

            # Update stats for achievements
            if damage >= 50:
                stats["big_hit"] += 1
            if description.startswith("Devil Fruit"):
                stats["devil_fruit_moves"] = stats.get("devil_fruit_moves", 0) + 1

            # Update the embed
            embed.description = (
                f"**{attacker.display_name}** used **{move['name']}**: {description} and dealt **{damage}** damage to "
                f"**{defender.display_name}**!"
            )
            embed.set_field_at(
                0,
                name="Health Bars",
                value=(
                    f"**{players[0][0].display_name}:** {self.generate_health_bar(players[0][1])} {players[0][1]}/100\n"
                    f"**{players[1][0].display_name}:** {self.generate_health_bar(players[1][1])} {players[1][1]}/100"
                ),
                inline=False,
            )
            await message.edit(embed=embed)

            # Wait before the next turn
            await asyncio.sleep(2)

            # Check if the game is over
            if players[0][1] == 0 or players[1][1] == 0:
                break

            turn_index = 1 - turn_index  # Switch turns

        # Determine winner
        winner = players[0][0] if players[0][1] > 0 else players[1][0]
        stats["win"] += 1
        embed = discord.Embed(
            title="⚔️ One Piece Deathmatch: Game Over!",
            description=f"The battle is over! **{winner.display_name}** is victorious!",
            color=0xFFD700,
        )
        embed.add_field(
            name="Final Health Bars",
            value=(
                f"**{players[0][0].display_name}:** {self.generate_health_bar(players[0][1])} {players[0][1]}/100\n"
                f"**{players[1][0].display_name}:** {self.generate_health_bar(players[1][1])} {players[1][1]}/100"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

        # Check achievements for both players
        await self.check_achievements(challenger, stats)
        await self.check_achievements(opponent, stats)

    @commands.command(name="achievements")
    async def achievements(self, ctx: commands.Context, member: discord.Member = None):
        """View your or another member's unlocked achievements."""
        member = member or ctx.author
        achievements = await self.config.member(member).achievements()

        if not achievements:
            await ctx.send(f"**{member.display_name}** has not unlocked any achievements yet.")
            return

        embed = discord.Embed(
            title=f"{member.display_name}'s Achievements",
            description="Unlocked achievements:",
            color=0x00FF00,
        )

        for key in achievements:
            achievement = ACHIEVEMENTS.get(key)
            if achievement:
                embed.add_field(name=achievement["description"], value=f"🔓 {achievement['description']}", inline=False)

        await ctx.send(embed=embed)


def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
