from redbot.core import commands, Config
import discord
import random
import asyncio

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
}

MOVES = [
    {"name": "Rubber Rocket", "type": "regular", "description": "Luffy's stretchy punch!", "effect": None},
    {"name": "Diable Jambe", "type": "regular", "description": "Sanji's fiery kick!", "effect": "burn", "burn_chance": 0.30},
    {"name": "Hiken", "type": "strong", "description": "Ace's fiery punch!", "effect": "burn", "burn_chance": 0.40},
    {"name": "Thunder Bagua", "type": "critical", "description": "Kaido delivers a devastating blow!", "effect": "crit"},
    {"name": "Room Shambles", "type": "critical", "description": "Law's surgical strike!", "effect": "stun"},
    {"name": "Heavy Point", "type": "strong", "description": "Chopper smashes his enemy!", "effect": "heal"},
]

# --- Cog Class ---
class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with unique effects and achievements."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9876543210, force_registration=True)
        default_member = {"wins": 0, "damage_dealt": 0, "blocks": 0, "achievements": []}
        self.config.register_member(**default_member)

    # --- Helper Functions ---
    def generate_health_bar(self, current_hp: int, max_hp: int = 100, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"

    def calculate_damage(self, move_type: str, crit_chance: float = 0.1) -> int:
        """Determine the damage range based on move type, with a chance to crit."""
        if move_type == "regular":
            damage = random.randint(1, 10)
        elif move_type == "strong":
            damage = random.randint(5, 15)
        elif move_type == "critical":
            damage = random.randint(20, 30)
        if random.random() < crit_chance:
            damage *= 2
        return damage

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

    # --- Main Commands ---
    @commands.hybrid_command(name="deathmatch")
    async def deathmatch(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another user to a One Piece deathmatch."""
        await self.fight(ctx, ctx.author, opponent)

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        """Show the leaderboard."""
        all_members = await self.config.all_members(ctx.guild)
        sorted_members = sorted(all_members.items(), key=lambda x: x[1]["wins"], reverse=True)

        embed = discord.Embed(title="🏆 Leaderboard 🏆", color=0xFFD700)
        for i, (member_id, data) in enumerate(sorted_members[:10], start=1):
            member = ctx.guild.get_member(member_id)
            if member:
                embed.add_field(
                    name=f"{i}. {member.display_name}",
                    value=f"Wins: {data['wins']}",
                    inline=False,
                )
        await ctx.send(embed=embed)

    @commands.command(name="achievements")
    async def achievements(self, ctx: commands.Context, member: discord.Member = None):
        """Show achievements for a user."""
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

    # --- Core Battle Logic ---
    async def fight(self, ctx, challenger, opponent):
        """The main battle logic for the deathmatch."""
        challenger_hp = 100
        opponent_hp = 100
        challenger_status = {"burn": 0, "stun": False}
        opponent_status = {"burn": 0, "stun": False}

        embed = discord.Embed(
            title="🏴‍☠️ One Piece Deathmatch ⚔️",
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

        players = [
            {"name": challenger.display_name, "hp": challenger_hp, "status": challenger_status, "member": challenger},
            {"name": opponent.display_name, "hp": opponent_hp, "status": opponent_status, "member": opponent},
        ]
        turn_index = 0

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
        await ctx.send(embed=embed)

        # Update stats for the winner
        await self.config.member(winner["member"]).wins.set(
            await self.config.member(winner["member"]).wins() + 1
        )

def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
