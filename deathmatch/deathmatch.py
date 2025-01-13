from redbot.core import commands, Config
from redbot.core.bot import Red
import discord
import random
import asyncio

ACHIEVEMENTS = {
    "first_blood": {"description": "Win your first match!", "condition": "win", "count": 1},
    "block_master": {"description": "Block 5 attacks in a single match.", "condition": "blocks", "count": 5},
    "big_hitter": {"description": "Deal over 50 damage in one hit!", "condition": "big_hit", "count": 1},
}


class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with achievements!"""

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
            if stats.get(condition, 0) >= required_count:
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

            # Simulate attack with RNG
            is_big_hit = random.random() < 0.1  # 10% chance for a big hit
            infused_with_haki = random.random() < 0.25  # 25% chance to infuse attack with haki
            blocked_by_haki = random.random() < 0.2  # 20% chance to block the attack

            if is_big_hit:
                damage = random.randint(40, 60)
                move = "⚡ Big Haki Strike"
                stats["big_hit"] += 1
            else:
                damage = random.randint(1, 20)
                move = random.choice(["Haki Punch", "Sword Slash", "Devil Fruit Strike"])

            if infused_with_haki:
                damage += 10
                move += " infused with Haki"

            if blocked_by_haki:
                damage = 0
                move = f"{defender.display_name} blocked with Haki!"
                stats["blocks"] += 1

            defender_hp = max(0, defender_hp - damage)  # Ensure HP does not go below 0
            players[1 - turn_index] = (defender, defender_hp)

            # Update the embed
            embed.description = (
                f"**{attacker.display_name}** used **{move}** and dealt **{damage}** damage to "
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

            # Wait before next turn for dramatic effect
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


def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
