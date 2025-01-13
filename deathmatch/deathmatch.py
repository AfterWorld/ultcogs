from redbot.core import commands
from redbot.core.bot import Red
import discord
import random
import asyncio


class Deathmatch(commands.Cog):
    """A One Piece-themed deathmatch game with turn-based actions!"""

    def __init__(self, bot: Red):
        self.bot = bot

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

        embed = discord.Embed(
            title="⚔️ One Piece Deathmatch!",
            description=f"The battle between **{challenger.display_name}** and **{opponent.display_name}** begins!",
            color=0x00FF00,
        )
        embed.add_field(name="HP", value=f"**{challenger.display_name}:** {challenger_hp} HP\n**{opponent.display_name}:** {opponent_hp} HP", inline=False)
        embed.set_footer(text="Actions will proceed one at a time!")
        message = await ctx.send(embed=embed)

        players = [challenger, opponent]
        turn_index = 0

        while challenger_hp > 0 and opponent_hp > 0:
            current_player = players[turn_index]
            target_player = players[1 - turn_index]

            # Build the interaction buttons
            view = discord.ui.View()
            for move_name in ["Haki Punch", "Sword Slash", "Devil Fruit Strike"]:
                view.add_item(discord.ui.Button(label=move_name, style=discord.ButtonStyle.primary, custom_id=move_name))

            await message.edit(content=f"**{current_player.display_name}'s** turn! Select your move:", view=view)

            def check(interaction):
                return interaction.user == current_player and interaction.message.id == message.id

            try:
                interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                move = interaction.data["custom_id"]
                damage = random.randint(1, 99)  # RNG-based damage

                if target_player == challenger:
                    challenger_hp -= damage
                else:
                    opponent_hp -= damage

                embed.description = f"**{current_player.display_name}** used **{move}** and dealt **{damage}** damage to **{target_player.display_name}**!"
                embed.set_field_at(0, name="HP", value=f"**{challenger.display_name}:** {max(0, challenger_hp)} HP\n**{opponent.display_name}:** {max(0, opponent_hp)} HP", inline=False)

                await interaction.response.edit_message(embed=embed, view=None)
            except asyncio.TimeoutError:
                await ctx.send(f"{current_player.display_name} took too long to act! Turn skipped.")
                embed.description = f"**{current_player.display_name}** took too long. Skipping their turn!"

            turn_index = 1 - turn_index  # Switch turns

        # Determine the winner
        winner = challenger if opponent_hp <= 0 else opponent
        embed = discord.Embed(
            title="⚔️ One Piece Deathmatch: Game Over!",
            description=f"The battle is over! **{winner.display_name}** is victorious!",
            color=0xFFD700,
        )
        embed.add_field(name="Final HP", value=f"**{challenger.display_name}:** {max(0, challenger_hp)} HP\n**{opponent.display_name}:** {max(0, opponent_hp)} HP", inline=False)
        await ctx.send(embed=embed)


def setup(bot: Red):
    bot.add_cog(Deathmatch(bot))
