import discord
from redbot.core import commands, Config
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import random
import asyncio

class OPCBattle:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.battles = {}

    async def battle(self, ctx, opponent: discord.Member):
        """Initiate a battle between two players."""
        if ctx.author == opponent:
            return await ctx.send("You can't battle yourself!")
        
        if ctx.author.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        attacker_data = await self.config.member(ctx.author).all()
        defender_data = await self.config.member(opponent).all()

        self.battles[ctx.author.id] = {"hp": 100, "opponent": opponent.id}
        self.battles[opponent.id] = {"hp": 100, "opponent": ctx.author.id}

        await ctx.send(f"{ctx.author.mention} has challenged {opponent.mention} to a battle!")
        await self.battle_loop(ctx, ctx.author, opponent)

    async def battle_loop(self, ctx, player1, player2):
        turn = player1
        while self.battles.get(player1.id) and self.battles.get(player2.id):
            await self.battle_turn(ctx, turn)
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)

        winner = player1 if self.battles.get(player1.id) else player2
        loser = player2 if winner == player1 else player1
        
        del self.battles[player1.id]
        del self.battles[player2.id]

        await self.end_battle(ctx, winner, loser)

    async def battle_turn(self, ctx, attacker):
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)

        attacker_data = await self.config.member(attacker).all()
        attack_power = attacker_data["strength"] + random.randint(1, 10)

        self.battles[defender_id]["hp"] -= attack_power

        await ctx.send(f"{attacker.mention} attacks {defender.mention} for {attack_power} damage!")
        await ctx.send(f"{defender.mention} has {max(0, self.battles[defender_id]['hp'])} HP left!")

        if self.battles[defender_id]["hp"] <= 0:
            del self.battles[attacker.id]
            del self.battles[defender_id]

    async def end_battle(self, ctx, winner, loser):
        await ctx.send(f"{winner.mention} has defeated {loser.mention} in battle!")
        
        winner_data = await self.config.member(winner).all()
        loser_data = await self.config.member(loser).all()

        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        await self.config.member(winner).exp.set(winner_data["exp"] + exp_gain)
        await self.config.member(winner).berries.set(winner_data["berries"] + berry_gain)

        await ctx.send(f"{winner.mention} gained {exp_gain} EXP and {berry_gain} Berries!")

    @commands.command()
    async def attack(self, ctx):
        """Attack your opponent in an ongoing battle."""
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        await self.battle_turn(ctx, ctx.author)

    @commands.command()
    async def battlestatus(self, ctx):
        """Check the status of your current battle."""
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        embed = discord.Embed(title="Battle Status", color=discord.Color.red())
        embed.add_field(name=ctx.author.name, value=f"HP: {self.battles[ctx.author.id]['hp']}")
        embed.add_field(name=opponent.name, value=f"HP: {self.battles[opponent_id]['hp']}")

        await ctx.send(embed=embed)
