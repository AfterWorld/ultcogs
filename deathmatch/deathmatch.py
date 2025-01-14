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
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": None},
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": None},
    {"name": "Diable Jambe", "type": "regular", "description": "Sanji's fiery kick!", "effect": "burn"},
    {"name": "Clown Bombs", "type": "regular", "description": "Buggy's explosive prank!", "effect": None},
    {"name": "Heavy Point", "type": "strong", "description": "Chopper smashes his enemy!", "effect": "heal"},
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "stun"},
]


class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with humor, mechanics, and leaderboards!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"wins": 0, "damage_dealt": 0, "blocks": 0}
        self.config.register_member(**default_member)

    def generate_health_bar(self, current_hp: int, max_hp: int = 100, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"

    def calculate_damage(self, move_type: str) -> int:
        """Determine the damage range based on move type."""
        if move_type == "regular":
            return random.randint(1, 10)
        elif move_type == "strong":
            return random.randint(5, 15)
        elif move_type == "critical":
            return random.randint(20, 30)

    async def apply_effects(self, effect: str, attacker: dict, defender: dict):
        """Apply special effects like burn, heal, or stun."""
        if effect == "burn":
            defender["status"]["burn"] = 3  # Burn lasts 3 turns
        elif effect == "heal":
            attacker["hp"] = min(100, attacker["hp"] + 10)
        elif effect == "stun":
            defender["status"]["stun"] = True

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

        challenger_status = {"burn": 0, "stun": False}
        opponent_status = {"burn": 0, "stun": False}

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

        players = [
            {"name": challenger.display_name, "hp": challenger_hp, "status": challenger_status, "member": challenger},
            {"name": opponent.display_name, "hp": opponent_hp, "status": opponent_status, "member": opponent},
        ]
        turn_index = 0

        while players[0]["hp"] > 0 and players[1]["hp"] > 0:
            attacker = players[turn_index]
            defender = players[1 - turn_index]

            if defender["status"]["stun"]:
                defender["status"]["stun"] = False  # Stun only lasts 1 turn
                embed.description = f"**{defender['name']}** is stunned and cannot move!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)
                turn_index = 1 - turn_index
                continue

            # Apply burn damage
            if defender["status"]["burn"] > 0:
                burn_damage = 5
                defender["hp"] = max(0, defender["hp"] - burn_damage)
                defender["status"]["burn"] -= 1
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage!"
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Select move
            move = random.choice(MOVES)
            damage = self.calculate_damage(move["type"])
            await self.apply_effects(move["effect"], attacker, defender)

            defender["hp"] = max(0, defender["hp"] - damage)

            # Update embed
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

            # Wait for next turn
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

        # Update leaderboard stats
        winner_data = winner["member"]
        await self.config.member(winner_data).wins.set(await self.config.member(winner_data).wins() + 1)

    @commands.command(name="leaderboard")
    async def deathboard(self, ctx: commands.Context):
        """Show the top players based on wins."""
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(
            all_members.items(), key=lambda x: x[1]["wins"], reverse=True
        )

        embed = discord.Embed(title="🏆 Leaderboard", color=0x00FF00)
        for i, (member_id, data) in enumerate(sorted_members[:10], start=1):
            member = ctx.guild.get_member(member_id)
            if member:
                embed.add_field(
                    name=f"{i}. {member.display_name}",
                    value=f"Wins: {data['wins']}",
                    inline=False,
                )

        await ctx.send(embed=embed)

def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
