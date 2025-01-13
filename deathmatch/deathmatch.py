from redbot.core import commands
from redbot.core.bot import Red
import discord
import random


class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game!"""

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.hybrid_command(name="deathmatch")
    async def deathmatch(self, ctx: commands.Context, user: discord.Member):
        """Challenge another user to a One Piece deathmatch!"""
        challenger = ctx.author
        opponent = user

        if challenger == opponent:
            await ctx.send("You can't challenge yourself to a deathmatch!")
            return

        challenger_hp = 100
        opponent_hp = 100

        moves = [
            ("Haki Punch", 15),
            ("Devil Fruit Strike", 20),
            ("Sword Slash", 25),
            ("Conqueror's Haki Stun", 0),
            ("Dodge", 0),
        ]

        turn = challenger
        battle_log = []

        while challenger_hp > 0 and opponent_hp > 0:
            attacker = turn
            defender = opponent if turn == challenger else challenger
            move = random.choice(moves)

            if move[0] == "Dodge":
                log_entry = f"**{attacker.display_name}** used {move[0]} and avoided the attack!"
            elif move[0] == "Conqueror's Haki Stun":
                log_entry = f"**{attacker.display_name}** stunned **{defender.display_name}** with Conqueror's Haki!"
                turn = attacker  # Keep the turn on the attacker
            else:
                damage = move[1]
                if defender == challenger:
                    challenger_hp -= damage
                else:
                    opponent_hp -= damage

                log_entry = f"**{attacker.display_name}** used {move[0]} and dealt **{damage}** damage to **{defender.display_name}**!"

            battle_log.append(log_entry)
            turn = opponent if turn == challenger else challenger

        # Join the battle log and truncate if necessary
        log_text = "\n".join(battle_log)
        if len(log_text) > 1024:
            log_text = log_text[:1021] + "..."  # Truncate and add ellipsis

        winner = challenger if opponent_hp <= 0 else opponent
        embed = discord.Embed(
            title="⚔️ One Piece Deathmatch!",
            description=f"The battle between **{challenger.display_name}** and **{opponent.display_name}** has ended!",
            color=0x00FF00,
        )
        embed.add_field(name="Battle Log", value=log_text, inline=False)
        embed.add_field(name="Winner", value=f"🏆 **{winner.display_name}** is victorious!", inline=False)
        embed.set_footer(text="May the Haki be with you!")

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle errors for this cog."""
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Error: {error}")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param}")
        else:
            await ctx.send(f"An unexpected error occurred: {str(error)}")


def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
