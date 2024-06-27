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
            "health": "❤️",
            "strength": "💪",
            "speed": "⚡",
            "swordsman": "🗡️",
            "sniper": "🎯",
            "navigator": "🧭",
            "cook": "👨‍🍳",
            "doctor": "👨‍⚕️"
        }

    async def battle(self, ctx, opponent: discord.Member):
        if ctx.author == opponent:
            return await ctx.send("You can't battle yourself!")
        
        if ctx.author.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        attacker_data = await self.config.member(ctx.author).all()
        defender_data = await self.config.member(opponent).all()

        # Check if players have chosen a class
        if not attacker_data.get("character_class"):
            return await ctx.send(f"{ctx.author.mention}, you need to choose a class first! Use the `.choose_class` command.")
        if not defender_data.get("character_class"):
            return await ctx.send(f"{opponent.mention} needs to choose a class first!")

        self.battles[ctx.author.id] = {"hp": 100, "opponent": opponent.id}
        self.battles[opponent.id] = {"hp": 100, "opponent": ctx.author.id}

        embed = self.create_battle_embed(ctx.author, opponent, attacker_data, defender_data)
        battle_msg = await ctx.send(embed=embed)

        await self.battle_loop(ctx, ctx.author, opponent, battle_msg)

    def create_battle_embed(self, player1, player2, player1_data, player2_data):
        embed = discord.Embed(title="Battle Start!", color=discord.Color.red())
        
        for player, data in [(player1, player1_data), (player2, player2_data)]:
            class_emoji = self.battle_emojis.get(data["character_class"].lower(), "")
            embed.add_field(
                name=f"{class_emoji} {player.name} ({data['character_class']})",
                value=f"{self.battle_emojis['health']} 100 HP\n"
                      f"{self.battle_emojis['strength']} {data['strength']} STR | "
                      f"{self.battle_emojis['speed']} {data['speed']} SPD\n"
                      f"Style: {data.get('fighting_style', 'None')}",
                inline=True
            )
        
        return embed

    async def battle_loop(self, ctx, player1, player2, battle_msg):
        turn = player1
        while self.battles.get(player1.id) and self.battles.get(player2.id):
            await self.battle_turn(ctx, turn, battle_msg)
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)

        winner = player1 if self.battles.get(player1.id) else player2
        loser = player2 if winner == player1 else player1
        
        if player1.id in self.battles:
            del self.battles[player1.id]
        if player2.id in self.battles:
            del self.battles[player2.id]

        await self.end_battle(ctx, winner, loser, battle_msg)

    async def battle_turn(self, ctx, attacker, battle_msg):
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)

        attacker_data = await self.config.member(attacker).all()
        defender_data = await self.config.member(defender).all()

        attack_power = self.calculate_attack(attacker_data)
        defense = self.calculate_defense(defender_data)

        damage = max(0, attack_power - defense)
        self.battles[defender_id]["hp"] -= damage
        self.battles[defender_id]["hp"] = max(0, self.battles[defender_id]["hp"])

        embed = self.create_battle_embed(attacker, defender, attacker_data, defender_data)
        embed.add_field(name="Battle Action", value=f"{attacker.name} attacks for {damage} damage!", inline=False)

        await battle_msg.edit(embed=embed)

        if self.battles[defender_id]["hp"] <= 0:
            if attacker.id in self.battles:
                del self.battles[attacker.id]
            if defender_id in self.battles:
                del self.battles[defender_id]

    def calculate_attack(self, attacker_data):
        base_attack = attacker_data["strength"] + random.randint(1, 10)
        class_bonus = 1.2 if attacker_data["character_class"] == "Swordsman" else 1
        style_bonus = 1.1 if attacker_data.get("fighting_style") else 1
        return int(base_attack * class_bonus * style_bonus)

    def calculate_defense(self, defender_data):
        base_defense = defender_data["defense"] + random.randint(1, 5)
        class_bonus = 1.2 if defender_data["character_class"] == "Cook" else 1
        return int(base_defense * class_bonus)

    async def end_battle(self, ctx, winner, loser, battle_msg):
        winner_data = await self.config.member(winner).all()
        loser_data = await self.config.member(loser).all()

        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        await self.config.member(winner).exp.set(winner_data["exp"] + exp_gain)
        await self.config.member(winner).berries.set(winner_data["berries"] + berry_gain)

        embed = discord.Embed(title="Battle Over!", color=discord.Color.green())
        embed.add_field(name="Winner", value=f"{winner.mention} ({winner_data['character_class']})", inline=False)
        embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nBerries: {berry_gain}", inline=False)
        embed.set_footer(text=f"{loser.name} has been defeated!")

        await battle_msg.edit(embed=embed)

    async def battlestatus(self, ctx):
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        attacker_data = await self.config.member(ctx.author).all()
        defender_data = await self.config.member(opponent).all()

        embed = self.create_battle_embed(ctx.author, opponent, attacker_data, defender_data)
        embed.title = "Battle Status"

        await ctx.send(embed=embed)
