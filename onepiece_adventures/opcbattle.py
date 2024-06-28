import discord
from redbot.core import commands, Config
import random
import asyncio
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class OPCBattle:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.battles: Dict[int, Dict] = {}
        self.battle_emojis = {
            "attack": "⚔️", "defend": "🛡️", "ability": "✨", "special": "🌟",
            "health": "❤️", "stamina": "⚡", "strength": "💪", "speed": "🏃",
            "swordsman": "🗡️", "sniper": "🎯", "navigator": "🧭", "cook": "👨‍🍳", "doctor": "👨‍⚕️"
        }
        self.class_abilities = {
            "Swordsman": self.swordsman_ability,
            "Sniper": self.sniper_ability,
            "Navigator": self.navigator_ability,
            "Cook": self.cook_ability,
            "Doctor": self.doctor_ability
        }
        self.environmental_effects = ["Stormy Weather", "Calm Waters", "Marine Presence", "Treasure Island"]

    async def battle(self, ctx, player1: discord.Member, player2: discord.Member):
        logger.info(f"Starting battle between {player1.name} and {player2.name}")
        if player1 == player2:
            return await ctx.send("A player can't battle themselves!")
        
        if player1.id in self.battles or player2.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")
    
        player1_data = await self.config.member(player1).all()
        player2_data = await self.config.member(player2).all()
    
        if not player1_data.get("character_class"):
            return await ctx.send(f"{player1.mention}, you need to choose a class first! Use the `.choose_class` command.")
        if not player2_data.get("character_class"):
            return await ctx.send(f"{player2.mention} needs to choose a class first!")
    
        player1_max_hp = self.calculate_max_hp(player1_data)
        player2_max_hp = self.calculate_max_hp(player2_data)
    
        self.battles[player1.id] = self.create_battle_data(player1_data, player2.id, player1_max_hp)
        self.battles[player2.id] = self.create_battle_data(player2_data, player1.id, player2_max_hp)
    
        environment = random.choice(self.environmental_effects)
        embed = self.create_battle_embed(player1, player2, environment)
        battle_msg = await ctx.send(embed=embed)
    
        result = await self.battle_loop(ctx, player1, player2, battle_msg, environment)
        
        logger.info(f"Battle loop result: {result}")
        
        if isinstance(result, tuple) and len(result) == 2:
            winner, loser = result
            logger.info(f"Battle ended. Winner: {winner.name if winner else 'None'}, Loser: {loser.name if loser else 'None'}")
            return winner, loser
        elif isinstance(result, discord.Message):
            logger.error(f"battle_loop returned a Message object: {result.content}")
            await ctx.send("An error occurred during the battle. It has been ended.")
            return None, None
        else:
            logger.error(f"Unexpected result from battle_loop: {result}")
            await ctx.send("An unexpected error occurred during the battle. It has been ended.")
            return None, None

    def create_battle_data(self, player_data, opponent_id, max_hp):
        return {
            "hp": max_hp,
            "max_hp": max_hp,
            "stamina": 100,
            "opponent": opponent_id,
            "status": [],
            "ability_cooldown": 0,
            "special_cooldown": 0,
            **player_data
        }

    async def battle_loop(self, ctx, player1, player2, battle_msg, environment) -> Tuple[discord.Member, discord.Member]:
        await ctx.send(f"The battle takes place in: **{environment}**!")
    
        while True:
            if player1.id not in self.battles or player2.id not in self.battles:
                logger.error(f"A player was removed from the battle unexpectedly. Player1: {player1.id in self.battles}, Player2: {player2.id in self.battles}")
                await ctx.send("An error occurred during the battle. It has been ended.")
                break
    
            embed = self.create_battle_embed(player1, player2, environment)
            await battle_msg.edit(embed=embed)
    
            for current_player in [player1, player2]:
                action = await self.get_action(ctx, current_player, battle_msg)
                if action != "skip":
                    await self.execute_action(ctx, current_player, action, battle_msg, environment)
                
                if current_player.id not in self.battles:
                    logger.error(f"{current_player.name} was removed from the battle after action execution.")
                    await ctx.send(f"An error occurred during {current_player.name}'s turn. The battle has been ended.")
                    break
                
                if self.battles[player1.id]["hp"] <= 0 or self.battles[player2.id]["hp"] <= 0:
                    break
            
            if self.battles[player1.id]["hp"] <= 0 or self.battles[player2.id]["hp"] <= 0:
                break
            
            # Reduce cooldowns
            for player in [player1, player2]:
                self.battles[player.id]["ability_cooldown"] = max(0, self.battles[player.id]["ability_cooldown"] - 1)
                self.battles[player.id]["special_cooldown"] = max(0, self.battles[player.id]["special_cooldown"] - 1)
            
            await asyncio.sleep(2)

        # Determine the winner
        if player1.id in self.battles and player2.id in self.battles:
            winner = player1 if self.battles[player1.id]["hp"] > 0 else player2
            loser = player2 if winner == player1 else player1
        elif player1.id in self.battles:
            winner, loser = player1, player2
        elif player2.id in self.battles:
            winner, loser = player2, player1
        else:
            await ctx.send("The battle ended in a draw as both players were removed.")
            return None, None

    await self.end_battle(ctx, winner, loser, battle_msg)
    return winner, loser
    
        await self.end_battle(ctx, winner, loser, battle_msg)
        return winner, loser
    
    async def get_action(self, ctx, current_player, battle_msg):
        action_emojis = [self.battle_emojis[action] for action in ["attack", "defend", "ability", "special"]]
        for emoji in action_emojis:
            await battle_msg.add_reaction(emoji)
    
        def check(reaction, user):
            return user.id == current_player.id and str(reaction.emoji) in action_emojis and reaction.message.id == battle_msg.id
    
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await battle_msg.clear_reactions()
            return list(self.battle_emojis.keys())[list(self.battle_emojis.values()).index(str(reaction.emoji))]
        except asyncio.TimeoutError:
            await battle_msg.clear_reactions()
            return "skip"

    def apply_damage(self, defender_id, damage_info):
        damage_value, is_crit = damage_info
        
        current_hp = self.battles[defender_id]["hp"]
        new_hp = max(0, current_hp - damage_value)
        self.battles[defender_id]["hp"] = new_hp
        logger.debug(f"Player {defender_id} HP: {current_hp} -> {new_hp} (Damage: {damage_value}, Critical: {is_crit})")
        return is_crit

    async def execute_action(self, ctx, attacker, action, battle_msg, environment):
        logger.info(f"Executing action for {attacker.name}: {action}")
        if attacker.id not in self.battles:
            logger.error(f"{attacker.name} (ID: {attacker.id}) not found in battles dict. Current battles: {self.battles.keys()}")
            await ctx.send(f"{attacker.name} was not found in the battle. This may be an error.")
            return
    
        defender_id = self.battles[attacker.id]["opponent"]
        defender = ctx.guild.get_member(defender_id)
    
        if defender_id not in self.battles:
            logger.error(f"Defender (ID: {defender_id}) not found in battles dict. Current battles: {self.battles.keys()}")
            await ctx.send(f"Opponent was not found in the battle. This may be an error.")
            return
    
        result = ""
    
        if action == "attack":
            damage, is_crit = self.calculate_attack(attacker.id, defender_id, environment)
            is_crit = self.apply_damage(defender_id, (damage, is_crit))
            crit_text = " (Critical Hit!)" if is_crit else ""
            result = f"{attacker.name} attacks for {damage} damage{crit_text}!"
        elif action == "defend":
            self.battles[attacker.id]["status"].append(("defend", 1))
            result = f"{attacker.name} takes a defensive stance!"
        elif action == "ability":
            if self.battles[attacker.id]["ability_cooldown"] > 0:
                result = f"{attacker.name}'s ability is on cooldown for {self.battles[attacker.id]['ability_cooldown']} more turns!"
            else:
                ability_func = self.class_abilities.get(self.battles[attacker.id]["character_class"])
                if ability_func:
                    result = await ability_func(attacker, defender)
                    self.battles[attacker.id]["ability_cooldown"] = 3  # Set cooldown to 3 turns
                else:
                    result = f"{attacker.name} tried to use an ability, but their class doesn't have one!"
        elif action == "special":
            if self.battles[attacker.id]["special_cooldown"] > 0:
                result = f"{attacker.name}'s special move is on cooldown for {self.battles[attacker.id]['special_cooldown']} more turns!"
            else:
                result = await self.use_special_move(attacker, defender, environment)
                self.battles[attacker.id]["special_cooldown"] = 5  # Set cooldown to 5 turns
    
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
            return 0, False
    
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
        
        return final_damage, is_crit
        
    async def use_special_move(self, attacker, defender, environment):
        attacker_data = self.battles[attacker.id]
        defender_data = self.battles[defender.id]
        stamina_cost = 30
    
        if attacker_data["stamina"] < stamina_cost:
            return f"{attacker.name} doesn't have enough stamina to use a special move!"
    
        attacker_data["stamina"] -= stamina_cost
    
        base_damage, _ = self.calculate_attack(attacker.id, defender.id, environment)
        base_damage = int(base_damage * 2)  # Double the base damage for special moves
        
        if attacker_data["character_class"] == "Swordsman":
            move = random.choice(["**Santoryu: Oni Giri**", "**Ittoryu: Shishi Sonson**", "**Nitoryu: Sai Kuru**"])
            damage = int(base_damage * 2.5)
            self.apply_damage(defender.id, (damage, False))  # Assume no crit for special moves
            return f"{attacker.name} uses '{move}', slashing for {damage} damage!"
    
        elif attacker_data["character_class"] == "Sniper":
            move = random.choice(["**Fire Bird Star**", "**Exploding Star**", "**Clima-Tact: Thunderbolt Tempo**"])
            damage = int(base_damage * 2.2)
            if random.random() < 0.8:  # 80% accuracy
                self.apply_damage(defender.id, (damage, False))
                return f"{attacker.name} uses '{move}', striking for {damage} damage!"
            else:
                return f"{attacker.name}'s '{move}' misses!"
    
        elif attacker_data["character_class"] == "Navigator":
            move = random.choice(["**Clima-Tact: Cyclone Tempo**", "**Weather Egg: Rain Tempo**", "**Mirage Tempo: Fata Morgana**"])
            damage = int(base_damage * 1.8)
            self.apply_damage(defender.id, (damage, False))
            self.battles[defender.id]["status"].append(("confused", 2))
            return f"{attacker.name} uses '{move}', dealing {damage} damage and confusing {defender.name}!"
    
        elif attacker_data["character_class"] == "Cook":
            move = random.choice(["**Diable Jambe: Flambage Shot**", "**Collier Shoot**", "**Party Table Kick Course**"])
            damage = int(base_damage * 2.3)
            self.apply_damage(defender.id, (damage, False))
            heal = int(damage * 0.3)
            attacker_data["hp"] = min(attacker_data["hp"] + heal, attacker_data["max_hp"])
            return f"{attacker.name} uses '{move}', dealing {damage} damage and healing for {heal} HP!"
    
        elif attacker_data["character_class"] == "Doctor":
            move = random.choice(["Scope", "**Monster Point: Konbie Genjin**", "**Cherry Blossom Blizzard**"])
            damage = int(base_damage * 2)
            self.apply_damage(defender.id, (damage, False))
            for status in attacker_data["status"]:
                if status[0] in ["poison", "burn", "confused"]:
                    attacker_data["status"].remove(status)
            return f"{attacker.name} uses '{move}', dealing {damage} damage and curing all status effects!"
    
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
        damage, is_crit = self.calculate_attack(attacker.id, defender.id, "Neutral")
        damage = int(damage * 1.5)  # Increase damage by 50%
        self.apply_damage(defender.id, (damage, is_crit))
        crit_text = " (Critical Hit!)" if is_crit else ""
        return f"{attacker.name} uses Three Sword Style, dealing {damage} damage{crit_text}!"
    
    async def sniper_ability(self, attacker, defender):
        damage, is_crit = self.calculate_attack(attacker.id, defender.id, "Neutral")
        damage = int(damage * 2)  # Double the damage
        hit_chance = 0.7
        if random.random() < hit_chance:
            self.apply_damage(defender.id, (damage, is_crit))
            crit_text = " (Critical Hit!)" if is_crit else ""
            return f"{attacker.name} takes a precision shot, dealing {damage} damage{crit_text}!"
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
        heal_amount = self.battles[attacker.id].get("intelligence", 10) * 3
        self.battles[attacker.id]["hp"] = min(self.battles[attacker.id]["hp"] + heal_amount, self.battles[attacker.id]["max_hp"])
        return f"{attacker.name} applies medical knowledge to heal {heal_amount} HP!"

    async def end_battle(self, ctx, winner, loser, battle_msg):
        logger.info(f"Ending battle. Winner: {winner.name}, Loser: {loser.name}")
        winner_data = self.battles.get(winner.id, {})
        loser_data = self.battles.get(loser.id, {})

        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        winner_data["exp"] = winner_data.get("exp", 0) + exp_gain
        winner_data["berries"] = winner_data.get("berries", 0) + berry_gain

        # Reset HP to max for both players in the config
        winner_data["hp"] = winner_data["max_hp"]
        loser_data["hp"] = loser_data["max_hp"]

        embed = discord.Embed(title="Battle Over!", color=discord.Color.green())
        embed.add_field(name="Winner", value=f"{winner.mention} ({winner_data.get('character_class', 'Unknown')})", inline=False)
        embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nBerries: {berry_gain}", inline=False)
        embed.set_footer(text=f"{loser.name} has been defeated!")

        await battle_msg.edit(embed=embed)

        # Update the database with the new values
        await self.config.member(winner).set(winner_data)
        await self.config.member(loser).set(loser_data)

        self.battles.pop(winner.id, None)
        self.battles.pop(loser.id, None)
        logger.info(f"Removed {winner.name} and {loser.name} from battles dict. Remaining battles: {self.battles.keys()}")

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
                    f"Style: {battle_data.get('fighting_style', 'None')}\n"
                    f"Ability CD: {battle_data['ability_cooldown']} | Special CD: {battle_data['special_cooldown']}",
                inline=True
            )
        
        embed.add_field(name="Environment", value=environment, inline=False)
        return embed

    def calculate_max_hp(self, player_data):
        return 100 + (player_data['defense'] * 10)

    async def battlestatus(self, ctx):
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")
    
        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)
    
        embed = self.create_battle_embed(ctx.author, opponent, "Current Battle")
        await ctx.send(embed=embed)
        
    async def surrender(self, ctx):
        if ctx.author.id not in self.battles:
            return await ctx.send("You're not in a battle!")

        opponent_id = self.battles[ctx.author.id]["opponent"]
        opponent = ctx.guild.get_member(opponent_id)

        await self.end_battle(ctx, opponent, ctx.author, await ctx.send("Battle ended due to surrender."))
        await ctx.send(f"{ctx.author.mention} has surrendered the battle to {opponent.mention}!")

    async def clearbattles(self, ctx):
        self.battles.clear()
        await ctx.send("All battles have been cleared.")
        logger.info("All battles have been cleared.")

    async def reset_player_stats(self, member):
        user_data = await self.config.member(member).all()
        max_hp = self.calculate_max_hp(user_data)
        user_data["hp"] = max_hp
        await self.config.member(member).set(user_data)

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"An error occurred: {error.original}")
        else:
            await ctx.send(f"An error occurred: {error}")
        logger.error(f"Error in OPCBattle: {error}", exc_info=True)
