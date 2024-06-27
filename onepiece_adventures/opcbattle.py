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
            "ability": "✨",
            "special": "🌟",
            "item": "🎒",
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
            "status": [],
            **attacker_data
        }
        self.battles[opponent.id] = {
            "hp": self.calculate_max_hp(defender_data),
            "max_hp": self.calculate_max_hp(defender_data),
            "stamina": 100,
            "opponent": ctx.author.id,
            "status": [],
            **defender_data
        }

        environment = random.choice(self.environmental_effects)
        embed = self.create_battle_embed(ctx.author, opponent, environment)
        battle_msg = await ctx.send(embed=embed)

        await self.battle_loop(ctx, ctx.author, opponent, battle_msg, environment)

    async def battle_loop(self, ctx, player1, player2, battle_msg, environment):
        turn = player1
        await ctx.send(f"The battle takes place in: **{environment}**!")
    
        while True:
            if player1.id not in self.battles:
                await ctx.send(f"The battle has ended unexpectedly. {player1.name} is no longer in the battle.")
                break
            if player2.id not in self.battles:
                await ctx.send(f"The battle has ended unexpectedly. {player2.name} is no longer in the battle.")
                break
    
            action = await self.get_action(ctx, turn, battle_msg)
            await self.execute_action(ctx, turn, action, battle_msg, environment)
            
            if player1.id not in self.battles:
                await ctx.send(f"The battle has ended unexpectedly. {player1.name} was removed from the battle after their action.")
                break
            if player2.id not in self.battles:
                await ctx.send(f"The battle has ended unexpectedly. {player2.name} was removed from the battle after their action.")
                break
            
            if self.battles[player1.id]["hp"] <= 0 or self.battles[player2.id]["hp"] <= 0:
                break
            
            self.battles[turn.id]["stamina"] = min(100, self.battles[turn.id]["stamina"] + 10)
            
            turn = player2 if turn == player1 else player1
            await asyncio.sleep(2)
    
        if player1.id in self.battles and player2.id in self.battles:
            winner = player1 if self.battles[player1.id]["hp"] > 0 else player2
            loser = player2 if winner == player1 else player1
        elif player1.id in self.battles:
            winner, loser = player1, player2
        elif player2.id in self.battles:
            winner, loser = player2, player1
        else:
            await ctx.send("The battle ended in a draw as both players were removed.")
            return
    
        await self.end_battle(ctx, winner, loser, battle_msg)

    async def get_action(self, ctx, player, battle_msg):
        action_emojis = [self.battle_emojis[action] for action in ["attack", "defend", "ability", "special", "item"]]
        for emoji in action_emojis:
            await battle_msg.add_reaction(emoji)

        def check(reaction, user):
            return user == player and str(reaction.emoji) in action_emojis and reaction.message.id == battle_msg.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await battle_msg.clear_reactions()
            return list(self.battle_emojis.keys())[list(self.battle_emojis.values()).index(str(reaction.emoji))]
        except asyncio.TimeoutError:
            await battle_msg.clear_reactions()
            return "attack"

   async def execute_action(self, ctx, attacker, action, battle_msg, environment):
        if attacker.id not in self.battles:
            await ctx.send(f"{attacker.name} is no longer in the battle.")
            return
    
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)
    
        if defender_id not in self.battles:
            await ctx.send(f"{defender.name} is no longer in the battle.")
            return
    
        # Handle status effects
        for status in list(self.battles[attacker.id]["status"]):
            if status[0] == "confused":
                if random.random() < 0.3:  # 30% chance to hit self
                    damage = self.calculate_attack(attacker.id, attacker.id, environment)
                    self.battles[attacker.id]["hp"] -= damage
                    await ctx.send(f"{attacker.name} is confused and hits themselves for {damage} damage!")
                    return
            elif status[0] == "burn":
                burn_damage = max(1, int(self.battles[attacker.id]["max_hp"] * 0.05))
                self.battles[attacker.id]["hp"] -= burn_damage
                await ctx.send(f"{attacker.name} takes {burn_damage} burn damage!")
            
            # Reduce status duration
            self.battles[attacker.id]["status"][self.battles[attacker.id]["status"].index(status)] = (status[0], status[1] - 1)
            if status[1] - 1 <= 0:
                self.battles[attacker.id]["status"].remove((status[0], 0))
    
        result = ""
    
        if action == "attack":
            damage = self.calculate_attack(attacker.id, defender_id, environment)
            self.battles[defender_id]["hp"] -= damage
            result = f"{attacker.name} attacks for {damage} damage!"
        elif action == "defend":
            self.battles[attacker.id]["status"].append(("defend", 1))
            result = f"{attacker.name} takes a defensive stance!"
        elif action == "ability":
            ability_func = self.class_abilities.get(self.battles[attacker.id]["character_class"])
            if ability_func:
                result = await ability_func(attacker, defender)
            else:
                result = f"{attacker.name} tried to use an ability, but their class doesn't have one!"
        elif action == "special":
            result = await self.use_special_move(attacker, defender, environment)
        elif action == "item":
            result = await self.use_battle_item(attacker, defender)
    
        # Check if both players are still in the battle after the action
        if attacker.id not in self.battles or defender_id not in self.battles:
            await ctx.send("An unexpected error occurred during the action execution.")
            return
    
        embed = self.create_battle_embed(attacker, defender, environment)
        embed.add_field(name="Battle Action", value=result, inline=False)
        await battle_msg.edit(embed=embed)

    def calculate_attack(self, attacker_id, defender_id, environment):
        attacker_data = self.battles[attacker_id]
        defender_data = self.battles[defender_id]
        
        base_damage = attacker_data["strength"] * 2 + attacker_data["speed"]
        class_bonus = 1.2 if attacker_data["character_class"] == "Swordsman" else 1
        style_bonus = 1.1 if attacker_data.get("fighting_style") else 1
        
        crit_chance = 0.05 + (attacker_data["speed"] * 0.005)
        is_crit = random.random() < crit_chance
        crit_multiplier = 1.5 if is_crit else 1
    
        dodge_chance = 0.05 + (defender_data["speed"] * 0.005)
        is_dodge = random.random() < dodge_chance
    
        if is_dodge:
            return 0
    
        damage = base_damage * class_bonus * style_bonus * crit_multiplier
    
        if any(status[0] == "defend" for status in defender_data["status"]):
            damage *= 0.7
    
        # Apply environmental effects
        if environment == "Stormy Weather":
            damage *= random.uniform(0.8, 1.2)
        elif environment == "Calm Waters":
            damage *= 1.1
        elif environment == "Marine Presence":
            if attacker_data["character_class"] == "Marine":
                damage *= 1.2
        elif environment == "Treasure Island":
            if random.random() < 0.1:
                damage *= 1.5
    
        final_damage = max(1, int(damage - (defender_data["defense"] * 0.5)))
        
        if is_crit:
            return f"{final_damage} (Critical Hit!)"
        else:
            return final_damage
        
    async def use_special_move(self, attacker, defender, environment):
        attacker_data = self.battles[attacker.id]
        defender_data = self.battles[defender.id]
        stamina_cost = 30
    
        if attacker_data["stamina"] < stamina_cost:
            return f"{attacker.name} doesn't have enough stamina to use a special move!"
    
        attacker_data["stamina"] -= stamina_cost
    
        base_damage = (attacker_data["strength"] + attacker_data["speed"]) * 2
        
        if attacker_data["character_class"] == "Swordsman":
            move = random.choice(["Santoryu: Oni Giri", "Ittoryu: Shishi Sonson", "Nitoryu: Sai Kuru"])
            damage = base_damage * 2.5
            self.battles[defender.id]["hp"] -= damage
            return f"{attacker.name} uses '{move}', slashing for {damage:.0f} damage!"
    
        elif attacker_data["character_class"] == "Sniper":
            move = random.choice(["Fire Bird Star", "Exploding Star", "Clima-Tact: Thunderbolt Tempo"])
            damage = base_damage * 2.2
            if random.random() < 0.8:  # 80% accuracy
                self.battles[defender.id]["hp"] -= damage
                return f"{attacker.name} uses '{move}', striking for {damage:.0f} damage!"
            else:
                return f"{attacker.name}'s '{move}' misses!"
    
        elif attacker_data["character_class"] == "Navigator":
            move = random.choice(["Clima-Tact: Cyclone Tempo", "Weather Egg: Rain Tempo", "Mirage Tempo: Fata Morgana"])
            damage = base_damage * 1.8
            self.battles[defender.id]["hp"] -= damage
            self.battles[defender.id]["status"].append(("confused", 2))
            return f"{attacker.name} uses '{move}', dealing {damage:.0f} damage and confusing {defender.name}!"
    
        elif attacker_data["character_class"] == "Cook":
            move = random.choice(["Diable Jambe: Flambage Shot", "Collier Shoot", "Party Table Kick Course"])
            damage = base_damage * 2.3
            self.battles[defender.id]["hp"] -= damage
            heal = damage * 0.3
            attacker_data["hp"] = min(attacker_data["hp"] + heal, attacker_data["max_hp"])
            return f"{attacker.name} uses '{move}', dealing {damage:.0f} damage and healing for {heal:.0f} HP!"
    
        elif attacker_data["character_class"] == "Doctor":
            move = random.choice(["Scope", "Monster Point: Konbie Genjin", "Cherry Blossom Blizzard"])
            damage = base_damage * 2
            self.battles[defender.id]["hp"] -= damage
            for status in attacker_data["status"]:
                if status[0] in ["poison", "burn", "confused"]:
                    attacker_data["status"].remove(status)
            return f"{attacker.name} uses '{move}', dealing {damage:.0f} damage and curing all status effects!"
    
        else:
            return f"{attacker.name} doesn't have any special moves!"
        
    async def use_battle_item(self, user, opponent):
        user_data = self.battles[user.id]
        inventory = user_data.get("inventory", {})
        
        if not inventory:
            return f"{user.name} has no items to use!"

        item_list = "\n".join([f"{i+1}. {item}" for i, item in enumerate(inventory.keys())])
        await user.send(f"Choose an item to use:\n{item_list}\nType the number of the item you want to use.")

        def check(m):
            return m.author == user and m.channel.type == discord.ChannelType.private and m.content.isdigit()

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            item_index = int(msg.content) - 1
            if 0 <= item_index < len(inventory):
                item = list(inventory.keys())[item_index]
                if inventory[item] > 0:
                    inventory[item] -= 1
                    user_data["inventory"] = inventory
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
        damage = self.calculate_attack(attacker.id, defender.id, "Neutral") * 1.5
        self.battles[defender.id]["hp"] -= damage
        return f"{attacker.name} uses Three Sword Style, dealing {damage} damage!"

    async def sniper_ability(self, attacker, defender):
        damage = self.calculate_attack(attacker.id, defender.id, "Neutral") * 2
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
        heal_amount = self.battles[attacker.id]["strength"] * 2
        self.battles[attacker.id]["hp"] = min(self.battles[attacker.id]["hp"] + heal_amount, self.battles[attacker.id]["max_hp"])
        return f"{attacker.name} cooks up a quick meal, restoring {heal_amount} HP!"

    async def doctor_ability(self, attacker, defender):
        heal_amount = self.battles[attacker.id]["intelligence"] * 3
        self.battles[attacker.id]["hp"] = min(self.battles[attacker.id]["hp"] + heal_amount, self.battles[attacker.id]["max_hp"])
        return f"{attacker.name} applies medical knowledge to heal {heal_amount} HP!"

    async def end_battle(self, ctx, winner, loser, battle_msg):
        winner_data = self.battles.get(winner.id, {})
        loser_data = self.battles.get(loser.id, {})
    
        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)
    
        winner_data["exp"] = winner_data.get("exp", 0) + exp_gain
        winner_data["berries"] = winner_data.get("berries", 0) + berry_gain
    
        embed = discord.Embed(title="Battle Over!", color=discord.Color.green())
        embed.add_field(name="Winner", value=f"{winner.mention} ({winner_data.get('character_class', 'Unknown')})", inline=False)
        embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nBerries: {berry_gain}", inline=False)
        embed.set_footer(text=f"{loser.name} has been defeated!")
    
        await battle_msg.edit(embed=embed)
    
        # Update the database with the new values
        await self.config.member(winner).set(winner_data)
        if loser_data:
            await self.config.member(loser).set(loser_data)
    
        self.battles.pop(winner.id, None)
        self.battles.pop(loser.id, None)

    def create_battle_embed(self, player1, player2, environment):
        embed = discord.Embed(title=f"Battle: {environment}", color=discord.Color.red())
        
        for player in [player1, player2]:
            battle_data = self.battles[player.id]
            class_emoji = self.battle_emojis.get(battle_data["character_class"].lower(), "")
            embed.add_field(
                name=f"{class_emoji} {player.name} ({battle_data['character_class']})",
                value=f"{self.battle_emojis['health']} HP: {battle_data['hp']}/{battle_data['max_hp']}\n"
                      f"{self.battle_emojis['stamina']} Stamina: {battle_data['stamina']}/100\n"
                      f"{self.battle_emojis['strength']} STR: {battle_data['strength']} | "
                      f"{self.battle_emojis['speed']} SPD: {battle_data['speed']}\n"
                      f"Style: {battle_data.get('fighting_style', 'None')}",
                inline=True
            )
        
        embed.add_field(name="Environment", value=environment, inline=False)
        return embed


    def calculate_max_hp(self, player_data):
        return 160 + (player_data['defense'] * 10)

    async def battlestatus(self, ctx):
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        embed = self.create_battle_embed(ctx.author, opponent, "Current Battle")
        await ctx.send(embed=embed)
        
    @commands.command()
    async def surrender(self, ctx):
        """Surrender from your current battle."""
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        await self.end_battle(ctx, opponent, ctx.author, await ctx.send("Battle ended due to surrender."))
        await ctx.send(f"{ctx.author.mention} has surrendered the battle to {opponent.mention}!")

    async def clearbattles(self, ctx):
        self.battles.clear()
        await ctx.send("All battles have been cleared.")
        
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"An error occurred: {error.original}")
        else:
            await ctx.send(f"An error occurred: {error}")
