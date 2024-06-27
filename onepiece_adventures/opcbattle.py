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
        self.class_abilities = {
            "Swordsman": self.swordsman_ability,
            "Sniper": self.sniper_ability,
            "Navigator": self.navigator_ability,
            "Cook": self.cook_ability,
            "Doctor": self.doctor_ability
        }

    async def battle(self, ctx, opponent: discord.Member):
        if ctx.author == opponent:
            return await ctx.send("You can't battle yourself!")
        
        if ctx.author.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        self.battles[ctx.author.id] = {"hp": self.calculate_max_hp(attacker_data), "opponent": opponent.id, "status": []}
        self.battles[opponent.id] = {"hp": self.calculate_max_hp(defender_data), "opponent": ctx.author.id, "status": []}

        embed = self.create_battle_embed(ctx.author, opponent, attacker_data, defender_data)
        battle_msg = await ctx.send(embed=embed)

        await self.battle_loop(ctx, ctx.author, opponent, battle_msg)

    def calculate_max_hp(self, player_data):
        return 100 + (player_data['defense'] * 5)

    async def battle_loop(self, ctx, player1, player2, battle_msg):
        turn = player1
        while self.battles.get(player1.id) and self.battles.get(player2.id):
            action = await self.get_action(ctx, turn)
            await self.execute_action(ctx, turn, action, battle_msg)
            
            if self.battles[player1.id]["hp"] <= 0 or self.battles[player2.id]["hp"] <= 0:
                break
            
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)

        winner = player1 if self.battles.get(player1.id) and self.battles[player1.id]["hp"] > 0 else player2
        loser = player2 if winner == player1 else player1
        
        await self.end_battle(ctx, winner, loser, battle_msg)

    async def get_action(self, ctx, player):
        def check(m):
            return m.author == player and m.channel == ctx.channel and m.content.lower() in ["attack", "defend", "ability"]

        await ctx.send(f"{player.mention}, choose your action: `attack`, `defend`, or `ability`")
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            return msg.content.lower()
        except asyncio.TimeoutError:
            return "attack"  # Default to attack if no input

    async def execute_action(self, ctx, attacker, action, battle_msg):
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)

        attacker_data = await self.config.member(attacker).all()
        defender_data = await self.config.member(defender).all()

        result = ""

        if action == "attack":
            damage = self.calculate_attack(attacker_data, defender_data)
            self.battles[defender_id]["hp"] -= damage
            result = f"{attacker.name} attacks for {damage} damage!"
        elif action == "defend":
            self.battles[attacker.id]["status"].append(("defend", 1))
            result = f"{attacker.name} takes a defensive stance!"
        elif action == "ability":
            ability_func = self.class_abilities.get(attacker_data["character_class"])
            if ability_func:
                result = await ability_func(attacker, defender)
            else:
                result = f"{attacker.name} tried to use an ability, but their class doesn't have one!"

        embed = self.create_battle_embed(attacker, defender, attacker_data, defender_data)
        embed.add_field(name="Battle Action", value=result, inline=False)
        await battle_msg.edit(embed=embed)

    def calculate_attack(self, attacker_data, defender_data):
        base_attack = attacker_data["strength"] + random.randint(1, 10)
        class_bonus = 1.2 if attacker_data["character_class"] == "Swordsman" else 1
        style_bonus = 1.1 if attacker_data.get("fighting_style") else 1
        
        # Critical hit chance
        crit_chance = 0.05 + (attacker_data["speed"] * 0.01)
        is_crit = random.random() < crit_chance
        crit_multiplier = 2 if is_crit else 1

        # Dodge chance
        dodge_chance = 0.05 + (defender_data["speed"] * 0.01)
        is_dodge = random.random() < dodge_chance

        if is_dodge:
            return 0

        damage = int(base_attack * class_bonus * style_bonus * crit_multiplier)

        # Check for defender's defensive stance
        if any(status[0] == "defend" for status in self.battles[defender_data["id"]]["status"]):
            damage //= 2

        return max(0, damage - defender_data["defense"])

    async def swordsman_ability(self, attacker, defender):
        damage = self.calculate_attack(await self.config.member(attacker).all(), await self.config.member(defender).all()) * 1.5
        self.battles[defender.id]["hp"] -= damage
        return f"{attacker.name} uses Three Sword Style, dealing {damage} damage!"

    async def sniper_ability(self, attacker, defender):
        damage = self.calculate_attack(await self.config.member(attacker).all(), await self.config.member(defender).all()) * 2
        hit_chance = 0.7
        if random.random() < hit_chance:
            self.battles[defender.id]["hp"] -= damage
            return f"{attacker.name} takes a precision shot, dealing {damage} damage!"
        else:
            return f"{attacker.name}'s precision shot misses!"

    async def navigator_ability(self, attacker, defender):
        self.battles[attacker.id]["status"].append(("evasion_boost", 2))
        return f"{attacker.name} uses their navigation skills to boost their evasion for 2 turns!"

    async def cook_ability(self, attacker, defender):
        heal_amount = attacker.strength * 2
        self.battles[attacker.id]["hp"] = min(self.battles[attacker.id]["hp"] + heal_amount, self.calculate_max_hp(await self.config.member(attacker).all()))
        return f"{attacker.name} cooks up a quick meal, restoring {heal_amount} HP!"

    async def doctor_ability(self, attacker, defender):
        heal_amount = attacker.intelligence * 3
        self.battles[attacker.id]["hp"] = min(self.battles[attacker.id]["hp"] + heal_amount, self.calculate_max_hp(await self.config.member(attacker).all()))
        return f"{attacker.name} applies medical knowledge to heal {heal_amount} HP!"

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
