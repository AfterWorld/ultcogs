import discord
from redbot.core import commands, Config
import random
import asyncio

class OPCBattle:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.battles = {}
        self.battle_emojis = {
            "attack": "⚔️",
            "defend": "🛡️",
            "health": "❤️"
        }

    async def battle(self, ctx, opponent: discord.Member):
        if ctx.author == opponent:
            return await ctx.send("You can't battle yourself!")
        
        if ctx.author.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        attacker_data = await self.config.member(ctx.author).all()
        defender_data = await self.config.member(opponent).all()

        self.battles[ctx.author.id] = {"hp": 100, "opponent": opponent.id}
        self.battles[opponent.id] = {"hp": 100, "opponent": ctx.author.id}

        embed = discord.Embed(title="Battle Start!", color=discord.Color.red())
        embed.add_field(name=ctx.author.name, value=f"{self.battle_emojis['health']} 100 HP", inline=True)
        embed.add_field(name=opponent.name, value=f"{self.battle_emojis['health']} 100 HP", inline=True)
        battle_msg = await ctx.send(embed=embed)

        await self.battle_loop(ctx, ctx.author, opponent, battle_msg)

    async def battle_loop(self, ctx, player1, player2, battle_msg):
        turn = player1
        while self.battles.get(player1.id) and self.battles.get(player2.id):
            await self.battle_turn(ctx, turn, battle_msg)
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)

        winner = player1 if self.battles.get(player1.id) else player2
        loser = player2 if winner == player1 else player1
        
        del self.battles[player1.id]
        del self.battles[player2.id]

        await self.end_battle(ctx, winner, loser, battle_msg)

    async def battle_turn(self, ctx, attacker, battle_msg):
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)

        attacker_data = await self.config.member(attacker).all()
        attack_power = attacker_data["strength"] + random.randint(1, 10)

        self.battles[defender_id]["hp"] -= attack_power
        self.battles[defender_id]["hp"] = max(0, self.battles[defender_id]["hp"])

        embed = discord.Embed(title="Battle in Progress!", color=discord.Color.blue())
        embed.add_field(name=attacker.name, value=f"{self.battle_emojis['attack']} Attacks for {attack_power} damage!", inline=False)
        embed.add_field(name=attacker.name, value=f"{self.battle_emojis['health']} {self.battles[attacker.id]['hp']} HP", inline=True)
        embed.add_field(name=defender.name, value=f"{self.battle_emojis['health']} {self.battles[defender_id]['hp']} HP", inline=True)

        await battle_msg.edit(embed=embed)

        if self.battles[defender_id]["hp"] <= 0:
            del self.battles[attacker.id]
            del self.battles[defender_id]

    async def end_battle(self, ctx, winner, loser, battle_msg):
        winner_data = await self.config.member(winner).all()
        loser_data = await self.config.member(loser).all()

        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        await self.config.member(winner).exp.set(winner_data["exp"] + exp_gain)
        await self.config.member(winner).berries.set(winner_data["berries"] + berry_gain)

        embed = discord.Embed(title="Battle Over!", color=discord.Color.green())
        embed.add_field(name="Winner", value=f"{winner.mention} {self.battle_emojis['health']} {self.battles[winner.id]['hp']} HP", inline=False)
        embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nBerries: {berry_gain}", inline=False)
        embed.set_footer(text=f"{loser.name} has been defeated!")

        await battle_msg.edit(embed=embed)

    @commands.command()
    async def battlestatus(self, ctx):
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        embed = discord.Embed(title="Battle Status", color=discord.Color.blue())
        embed.add_field(name=ctx.author.name, value=f"{self.battle_emojis['health']} {self.battles[ctx.author.id]['hp']} HP", inline=True)
        embed.add_field(name=opponent.name, value=f"{self.battle_emojis['health']} {self.battles[opponent_id]['hp']} HP", inline=True)

        await ctx.send(embed=embed)
