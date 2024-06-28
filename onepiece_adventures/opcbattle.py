import discord
from redbot.core import commands, Config
import random
import asyncio
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class OPCBattle:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        default_user = {
            "character_class": None,
            "hp": 280,
            "stamina": 100,
            "strength": 14,
            "speed": 15,
            "defense": 10,
            "exp": 0,
            "berries": 0,
            "style": "None"
        }
        self.config.register_member(**default_user)
        self.battles: Dict[int, Dict] = {}
        self.battle_emojis = {
            "health": "❤️", "stamina": "⚡", "strength": "💪", "speed": "🏃‍♂️",
            "swordsman": "🗡️", "sniper": "🎯", "navigator": "🧭", "cook": "👨‍🍳", "doctor": "👨‍⚕️"
        }
        self.environmental_effects = ["Stormy Weather", "Calm Waters", "Marine Presence", "Treasure Island"]

    async def battle(self, ctx, player1: discord.Member, player2: discord.Member):
        """Start an automatic battle between two players."""
        if player1 == player2:
            return await ctx.send("A player can't battle themselves!")
        
        if player1.id in self.battles or player2.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        player1_data = await self.config.member(player1).all()
        player2_data = await self.config.member(player2).all()

        if not player1_data["character_class"]:
            return await ctx.send(f"{player1.name}, you need to choose a class first!")
        if not player2_data["character_class"]:
            return await ctx.send(f"{player2.name} needs to choose a class first!")

        self.battles[player1.id] = self.create_battle_data(player1_data, player2.id)
        self.battles[player2.id] = self.create_battle_data(player2_data, player1.id)

        environment = random.choice(self.environmental_effects)
        battle_msg = await ctx.send("Battle started!")
        winner, loser = await self.auto_battle(ctx, player1, player2, battle_msg, environment)

        if winner and loser:
            await self.end_battle(ctx, winner, loser)
        else:
            await ctx.send("The battle ended in a draw.")

        del self.battles[player1.id]
        del self.battles[player2.id]

    def create_battle_data(self, player_data: Dict, opponent_id: int) -> Dict:
        return {
            "hp": player_data["hp"],
            "max_hp": player_data["hp"],
            "stamina": player_data["stamina"],
            "strength": player_data["strength"],
            "speed": player_data["speed"],
            "defense": player_data["defense"],
            "character_class": player_data["character_class"],
            "opponent": opponent_id,
            "style": player_data["style"],
        }

    async def auto_battle(self, ctx, player1: discord.Member, player2: discord.Member, battle_msg: discord.Message, environment: str) -> Tuple[Optional[discord.Member], Optional[discord.Member]]:
        await ctx.send(f"The battle takes place in: **{environment}**!")
        
        while True:
            embed = self.create_battle_embed(player1, player2, environment)
            await battle_msg.edit(embed=embed)

            for current_player in (player1, player2):
                opponent = player2 if current_player == player1 else player1
                damage = self.calculate_damage(current_player, opponent, environment)
                self.battles[opponent.id]["hp"] -= damage
                self.battles[current_player.id]["stamina"] = min(100, self.battles[current_player.id]["stamina"] + 10)

                if self.battles[opponent.id]["hp"] <= 0:
                    final_embed = self.create_battle_embed(player1, player2, environment)
                    await battle_msg.edit(embed=final_embed)
                    return current_player, opponent

            await asyncio.sleep(2)

    def calculate_damage(self, attacker: discord.Member, defender: discord.Member, environment: str) -> int:
        attacker_data = self.battles[attacker.id]
        defender_data = self.battles[defender.id]
        
        base_damage = attacker_data["strength"] * 2 + attacker_data["speed"]
        damage = max(0, base_damage - defender_data["defense"] // 2)

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

        return int(damage)

    def create_battle_embed(self, player1: discord.Member, player2: discord.Member, environment: str) -> discord.Embed:
        embed = discord.Embed(title=f"Battle: {environment}", color=discord.Color.red())
        
        for player in (player1, player2):
            battle_data = self.battles[player.id]
            class_emoji = self.battle_emojis.get(battle_data['character_class'].lower(), "")
            player_info = (
                f"{class_emoji} {player.name} ({battle_data['character_class']})\n"
                f"{self.battle_emojis['health']} HP: {battle_data['hp']}/{battle_data['max_hp']}\n"
                f"{self.battle_emojis['stamina']} Stamina: {battle_data['stamina']}/100\n"
                f"{self.battle_emojis['strength']} STR: {battle_data['strength']} | "
                f"{self.battle_emojis['speed']} SPD: {battle_data['speed']}\n"
                f"Style: {battle_data['style']}"
            )
            embed.add_field(name="\u200b", value=player_info, inline=True)
        
        embed.add_field(name="Environment", value=environment, inline=False)
        
        return embed

    async def end_battle(self, ctx, winner: discord.Member, loser: discord.Member):
        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        async with self.config.member(winner).all() as winner_data:
            winner_data['exp'] += exp_gain
            winner_data['berries'] += berry_gain

        await ctx.send(f"🎉 {winner.name} wins the battle!\n"
                       f"Gained {exp_gain} EXP and {berry_gain} berries!")

    async def statz(self, ctx, member: discord.Member = None):
        """Display your or another member's current stats."""
        target = member or ctx.author
        user_data = await self.config.member(target).all()
        embed = discord.Embed(title=f"{target.name}'s Stats", color=discord.Color.blue())
        class_emoji = self.battle_emojis.get(user_data.get('character_class', '').lower(), '')
        embed.add_field(name="Class", value=f"{class_emoji} {user_data.get('character_class', 'Not set')}", inline=False)
        embed.add_field(name=f"{self.battle_emojis['health']} HP", value=user_data.get('hp', 0), inline=True)
        embed.add_field(name=f"{self.battle_emojis['stamina']} Stamina", value=user_data.get('stamina', 0), inline=True)
        embed.add_field(name=f"{self.battle_emojis['strength']} Strength", value=user_data.get('strength', 0), inline=True)
        embed.add_field(name=f"{self.battle_emojis['speed']} Speed", value=user_data.get('speed', 0), inline=True)
        embed.add_field(name="Defense", value=user_data.get('defense', 0), inline=True)
        embed.add_field(name="EXP", value=user_data.get('exp', 0), inline=True)
        embed.add_field(name="Berries", value=user_data.get('berries', 0), inline=True)
        embed.add_field(name="Style", value=user_data.get('style', 'None'), inline=True)
        await ctx.send(embed=embed)

    async def choose_class(self, ctx, class_name: str):
        """Choose your character class."""
        valid_classes = ['swordsman', 'sniper', 'navigator', 'cook', 'doctor']
        if class_name.lower() not in valid_classes:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(valid_classes)}")

        async with self.config.member(ctx.author).all() as user_data:
            user_data['character_class'] = class_name.capitalize()
            
        class_emoji = self.battle_emojis.get(class_name.lower(), '')
        await ctx.send(f"You are now a {class_emoji} {class_name.capitalize()}!")

    async def reset_player_stats(self, member: discord.Member):
        default_stats = {
            "hp": 280,
            "stamina": 100,
            "strength": 14,
            "speed": 15,
            "defense": 10,
        }
        async with self.config.member(member).all() as user_data:
            user_data.update(default_stats)

    async def level_up(self, ctx, member: discord.Member):
        async with self.config.member(member).all() as user_data:
            exp = user_data.get('exp', 0)
            level = exp // 100  # Simple level calculation, adjust as needed
            
            if level > 0:
                stat_increase = level * 2  # 2 points per level, adjust as needed
                user_data['hp'] += stat_increase
                user_data['strength'] += stat_increase
                user_data['speed'] += stat_increase
                user_data['defense'] += stat_increase
                
                await ctx.send(f"🎉 {member.name} has leveled up! All stats increased by {stat_increase}.")
            else:
                await ctx.send(f"{member.name} hasn't gained enough EXP to level up yet.")
