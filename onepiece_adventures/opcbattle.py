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
            "stamina": "⚡",
            "strength": "💪",
            "speed": "🏃",
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
        self.environmental_effects = [
            "Stormy Weather", "Calm Waters", "Marine Presence", "Treasure Island"
        ]
        self.battle_items = {
            "Health Potion": self.use_health_potion,
            "Stamina Boost": self.use_stamina_boost,
            "Smoke Bomb": self.use_smoke_bomb
        }

    async def battle(self, ctx, opponent: discord.Member):
        if ctx.author == opponent:
            return await ctx.send("You can't battle yourself!")
        
        if ctx.author.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        attacker_data = await self.config.member(ctx.author).all()
        defender_data = await self.config.member(opponent).all()

        if not attacker_data.get("character_class"):
            return await ctx.send(f"{ctx.author.mention}, you need to choose a class first! Use the `.choose_class` command.")
        if not defender_data.get("character_class"):
            return await ctx.send(f"{opponent.mention} needs to choose a class first!")

        self.battles[ctx.author.id] = {
            "hp": self.calculate_max_hp(attacker_data),
            "max_hp": self.calculate_max_hp(attacker_data),
            "stamina": 100,
            "opponent": opponent.id,
            "status": []
        }
        self.battles[opponent.id] = {
            "hp": self.calculate_max_hp(defender_data),
            "max_hp": self.calculate_max_hp(defender_data),
            "stamina": 100,
            "opponent": ctx.author.id,
            "status": []
        }

        environment = random.choice(self.environmental_effects)
        embed = self.create_battle_embed(ctx.author, opponent, attacker_data, defender_data, environment)
        battle_msg = await ctx.send(embed=embed)

        await self.battle_loop(ctx, ctx.author, opponent, battle_msg, environment)

    def create_battle_embed(self, player1, player2, player1_data, player2_data, environment):
        embed = discord.Embed(title=f"Battle: {environment}", color=discord.Color.red())
        
        for player, data in [(player1, player1_data), (player2, player2_data)]:
            battle_data = self.battles[player.id]
            class_emoji = self.battle_emojis.get(data["character_class"].lower(), "")
            embed.add_field(
                name=f"{class_emoji} {player.name} ({data['character_class']})",
                value=f"{self.battle_emojis['health']} HP: {battle_data['hp']}/{battle_data['max_hp']}\n"
                      f"{self.battle_emojis['stamina']} Stamina: {battle_data['stamina']}/100\n"
                      f"{self.battle_emojis['strength']} STR: {data['strength']} | "
                      f"{self.battle_emojis['speed']} SPD: {data['speed']}\n"
                      f"Style: {data.get('fighting_style', 'None')}",
                inline=True
            )
        
        embed.add_field(name="Environment", value=environment, inline=False)
        return embed

    async def battle_loop(self, ctx, player1, player2, battle_msg, environment):
        turn = player1
        await ctx.send(f"The battle takes place in: **{environment}**!")

        while self.battles.get(player1.id) and self.battles.get(player2.id):
            action = await self.get_action(ctx, turn)
            await self.execute_action(ctx, turn, action, battle_msg, environment)
            
            if self.battles[player1.id]["hp"] <= 0 or self.battles[player2.id]["hp"] <= 0:
                break
            
            self.battles[turn.id]["stamina"] = min(100, self.battles[turn.id]["stamina"] + 10)
            
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)

        winner = player1 if self.battles.get(player1.id) and self.battles[player1.id]["hp"] > 0 else player2
        loser = player2 if winner == player1 else player1
        
        await self.end_battle(ctx, winner, loser, battle_msg)

    async def get_action(self, ctx, player):
        def check(m):
            return m.author == player and m.channel == ctx.channel and m.content.lower() in ["attack", "defend", "ability", "special", "item"]

        await ctx.send(f"{player.mention}, choose your action: `attack`, `defend`, `ability`, `special`, or `item`")
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            return msg.content.lower()
        except asyncio.TimeoutError:
            return "attack"

    async def execute_action(self, ctx, attacker, action, battle_msg, environment):
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)

        attacker_data = await self.config.member(attacker).all()
        defender_data = await self.config.member(defender).all()

        result = ""

        if action == "attack":
            damage = self.calculate_attack(attacker_data, defender_data, environment)
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
        elif action == "special":
            result = await self.use_special_move(attacker, defender, environment)
        elif action == "item":
            result = await self.use_battle_item(attacker, defender)

        embed = self.create_battle_embed(attacker, defender, attacker_data, defender_data, environment)
        embed.add_field(name="Battle Action", value=result, inline=False)
        await battle_msg.edit(embed=embed)

    def calculate_attack(self, attacker_data, defender_data, environment):
        base_attack = attacker_data["strength"] + random.randint(1, 10)
        class_bonus = 1.2 if attacker_data["character_class"] == "Swordsman" else 1
        style_bonus = 1.1 if attacker_data.get("fighting_style") else 1
        
        crit_chance = 0.05 + (attacker_data["speed"] * 0.01)
        is_crit = random.random() < crit_chance
        crit_multiplier = 2 if is_crit else 1

        dodge_chance = 0.05 + (defender_data["speed"] * 0.01)
        is_dodge = random.random() < dodge_chance

        if is_dodge:
            return 0

        damage = int(base_attack * class_bonus * style_bonus * crit_multiplier)

        if any(status[0] == "defend" for status in self.battles[defender_data["id"]]["status"]):
            damage //= 2

        if environment == "Stormy Weather":
            damage *= random.uniform(0.8, 1.2)
        elif environment == "Calm Waters":
            damage *= 1.1
        elif environment == "Marine Presence":
            if attacker_data["character_class"] == "Marine":
                damage *= 1.2
        elif environment == "Treasure Island":
            if random.random() < 0.1:
                damage *= 2

        return max(0, int(damage - defender_data["defense"]))

    async def use_special_move(self, attacker, defender, environment):
        attacker_data = await self.config.member(attacker).all()
        stamina_cost = 30

        if self.battles[attacker.id]["stamina"] < stamina_cost:
            return f"{attacker.name} doesn't have enough stamina to use a special move!"

        self.battles[attacker.id]["stamina"] -= stamina_cost
        
        if attacker_data["character_class"] == "Swordsman":
            damage = self.calculate_attack(attacker_data, await self.config.member(defender).all(), environment) * 2
            self.battles[defender.id]["hp"] -= damage
            return f"{attacker.name} uses 'Santoryu: Oni Giri', dealing {damage} damage!"
        elif attacker_data["character_class"] == "Sniper":
            damage = self.calculate_attack(attacker_data, await self.config.member(defender).all(), environment) * 2.5
            if random.random() < 0.7:
                self.battles[defender.id]["hp"] -= damage
                return f"{attacker.name} uses 'Fire Bird Star', dealing {damage} damage!"
            else:
                return f"{attacker.name}'s 'Fire Bird Star' misses!"
        # Add special moves for other classes here

    async def use_battle_item(self, user, opponent):
        items = await self.config.member(user).inventory()
        if not items:
            return f"{user.name} has no items to use!"

        item_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items.keys())])
        await user.send(f"Choose an item to use:\n{item_list}\nType the number of the item you want to use.")

        def check(m):
            return m.author == user and m.channel.type == discord.ChannelType.private and m.content.isdigit()

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            item_index = int(msg.content) - 1
            if 0 <= item_index < len(items):
                item = list(items.keys())[item_index]
                if items[item] > 0:
                    items[item] -= 1
                    await self.config.member(user).inventory.set(items)
                    return await self.battle_items[item](user, opponent)
                else:
                    return f"{user.name} doesn't have any {item} left!"
            else:
                return f"{user.name} chose an invalid item number."
        except asyncio.TimeoutError:
            return f"{user.name} took too long to choose an item."

    async def use_health_potion(self, user, opponent):
        heal_amount = 50
        self.battles[user.id]["hp"] = min(self.battles[user.id]["hp"] + heal_amount, self.battles[user.id]["max_hp"])
        return f"{user.name} uses a Health Potion, restoring {heal_amount} HP!"

    async def use_stamina_boost(self, user, opponent):
        boost_amount = 50
        self.battles[user.id]["stamina"] = min(100, self.battles[user.id]["stamina"] + boost_amount)
        return f"{user.name} uses a Stamina Boost, restoring {boost_amount} Stamina!"

    async def use_smoke_bomb(self, user, opponent):
        self.battles[opponent.id]["status"].append(("blinded", 2))
        return f"{user.name} uses a Smoke Bomb, blinding {opponent.name} for 2 turns!"

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

        del self.battles[winner.id]
        del self.battles[loser.id]

    def calculate_max_hp(self, player_data):
        return 100 + (player_data['defense'] * 5)

    # Add any additional helper methods here
