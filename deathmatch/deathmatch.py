from redbot.core import commands, Config
from redbot.core.bot import Red
import discord
import random
import asyncio

ACHIEVEMENTS = {
    "first_blood": {"description": "Win your first match!", "condition": "win", "count": 1},
    "big_hitter": {"description": "Deal over 30 damage in one hit!", "condition": "big_hit", "count": 1},
    "iron_wall": {"description": "Block 10 attacks in total!", "condition": "blocks", "count": 10},
    "burn_master": {"description": "Inflict burn 5 times in a match!", "condition": "burns_applied", "count": 5},
    "comeback_king": {"description": "Win a match after dropping below 10 HP!", "condition": "comeback", "count": 1},
    "perfect_game": {"description": "Win without taking any damage!", "condition": "no_damage", "count": 1},
    "unstoppable": {"description": "Win 10 matches!", "condition": "win", "count": 10},
    "sea_emperor": {"description": "Win 25 matches!", "condition": "win", "count": 25},
    "burn_victim": {"description": "Take 30 damage from burn in a single match!", "condition": "burn_damage_taken", "count": 30},
    "lucky_strike": {"description": "Land 3 critical hits in a single match!", "condition": "crit_hits", "count": 3},
    "haki_master": {"description": "Block 5 attacks in a single match!", "condition": "blocks", "count": 5},
    "combo_master": {"description": "Land 5 hits in a row without missing!", "condition": "combo_hits", "count": 5},
    "clutch_block": {"description": "Block an attack that would have defeated you!", "condition": "clutch_block", "count": 1},
    "devil_fruit_user": {"description": "Use 5 Devil Fruit moves in a single match!", "condition": "devil_fruit_moves", "count": 5},
    "stunning_performance": {"description": "Stun your opponent 3 times in a single match!", "condition": "stuns", "count": 3},
    "overkill": {"description": "Deal over 50 damage in one hit!", "condition": "big_hit", "count": 50},
    "flaming_fury": {"description": "Inflict 3 stacks of burn on your opponent!", "condition": "max_burn", "count": 1},
    "healing_touch": {"description": "Heal yourself for 50 HP in a single match!", "condition": "healing_done", "count": 50},
    "critical_king": {"description": "Land a critical hit in every turn of a match!", "condition": "all_crit_hits", "count": 1},
    "ultimate_victory": {"description": "Win a match with your HP at 100!", "condition": "full_health_win", "count": 1},
}

MOVES = [
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": None},
    {"name": "Santoryu Onigiri", "type": "strong", "description": "Zoro's sword slash!", "effect": None},
    {"name": "Diable Jambe", "type": "regular", "description": "Sanji's fiery kick!", "effect": "burn", "burn_chance": 0.25},
    {"name": "Clown Bombs", "type": "regular", "description": "Buggy's explosive prank!", "effect": None},
    {"name": "Heavy Point", "type": "strong", "description": "Chopper smashes his enemy!", "effect": "heal"},
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "stun"},
    {"name": "Soul Solid", "type": "regular", "description": "Brook plays a chilling tune!", "effect": "burn", "burn_chance": 0.20},
    {"name": "Pop Green", "type": "regular", "description": "Usopp's plant barrage!", "effect": None},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Room Shambles", "type": "critical", "description": "Law's surgical strike!", "effect": "stun"},
    {"name": "Dark Vortex", "type": "strong", "description": "Blackbeard's gravity attack!", "effect": None},
    {"name": "Conqueror's Haki", "type": "critical", "description": "Overwhelms your opponent!", "effect": "stun"},
    {"name": "Red Hawk", "type": "strong", "description": "Luffy's fiery attack!", "effect": "burn", "burn_chance": 0.20},
    {"name": "Ice Age", "type": "regular", "description": "Aokiji freezes the battlefield!", "effect": "stun"},
    {"name": "Magma Fist", "type": "strong", "description": "Akainu's devastating magma punch!", "effect": "burn", "burn_chance": 0.35},
    {"name": "Coup de Vent", "type": "regular", "description": "Franky's air cannon!", "effect": None},
    {"name": "Clutch", "type": "regular", "description": "Robin's multi-hand grab!", "effect": "stun"},
    {"name": "Elephant Gun", "type": "strong", "description": "Luffy's giant fist!", "effect": None},
    {"name": "Enel's Judgement", "type": "critical", "description": "Thunder god's ultimate strike!", "effect": "burn", "burn_chance": 0.15},
    {"name": "Pirate King's Will", "type": "regular", "description": "A legendary strike filled with willpower!", "effect": None},
]

class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with humor, mechanics, and deathboards!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"wins": 0, "damage_dealt": 0, "blocks": 0, "achievements": []}
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
            burn_chance = MOVES[attacker["move_index"]].get("burn_chance", 0)
            if random.random() < burn_chance:
                defender["status"]["burn"] += 1  # Increase burn stacks
                defender["status"]["burn"] = min(defender["status"]["burn"], 3)  # Limit stacks to 3
        elif effect == "heal":
            attacker["hp"] = min(100, attacker["hp"] + 10)
        elif effect == "stun":
            defender["status"]["stun"] = True

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

    @commands.command(name="achievements")
    async def achievements_command(self, ctx: commands.Context, member: discord.Member = None):
        """Command to display achievements."""
        await self.display_achievements(ctx, member)

    @commands.command(name="deathboard")
    async def deathboard(self, ctx: commands.Context):
        """Show the deathboard."""
        # Fetch all members and sort by wins
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)

        embed = discord.Embed(title="🏆 deathboard 🏆", color=0xFFD700)
        for i, (member_id, data) in enumerate(sorted_members[:10], start=1):
            member = ctx.guild.get_member(member_id)
                        if member:
                embed.add_field(
                    name=f"{i}. {member.display_name}",
                    value=f"Wins: {data['wins']}",
                    inline=False,
                )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="deathmatch")
    async def deathmatch(self, ctx: commands.Context, opponent: discord.Member):
        """Start a One Piece deathmatch against another user."""
        challenger = ctx.author

        if challenger == opponent:
            await ctx.send("You can't challenge yourself to a deathmatch!")
            return

        challenger_hp = 100
        opponent_hp = 100

        challenger_status = {"burn": 0, "stun": False}
        opponent_status = {"burn": 0, "stun": False}

        embed = discord.Embed(
            title="🏴‍☠️ One Piece Deathmatch ⚔️",
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
                burn_damage = 5 * defender["status"]["burn"]
                defender["hp"] = max(0, defender["hp"] - burn_damage)
                embed.description = f"🔥 **{defender['name']}** takes {burn_damage} burn damage from fire stacks!"
                defender["status"]["burn"] -= 1
                await message.edit(embed=embed)
                await asyncio.sleep(2)

            # Select a move
            move = random.choice(MOVES)
            damage = self.calculate_damage(move["type"])
            attacker["move_index"] = MOVES.index(move)  # Track move index for effects
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

            await asyncio.sleep(2)
            turn_index = 1 - turn_index  # Switch turns

        # Determine the winner
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

        # Update deathboard stats
        winner_data = winner["member"]
        await self.config.member(winner_data).wins.set(await self.config.member(winner_data).wins() + 1)


def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
