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
            "hp": 100,
            "strength": 10,
            "speed": 10,
            "defense": 10,
            "exp": 0,
            "berries": 0,
        }
        self.config.register_member(**default_user)
        self.battles: Dict[int, Dict] = {}

    @commands.command()
    async def battle(self, ctx, player1: discord.Member, opponent: discord.Member):
        """Start a battle between two players."""
        if player1 == opponent:
            return await ctx.send("A player can't battle themselves!")
        
        if player1.id in self.battles or opponent.id in self.battles:
            return await ctx.send("One of the players is already in a battle!")

        player1_data = await self.config.member(player1).all()
        player2_data = await self.config.member(opponent).all()

        if not player1_data["character_class"]:
            return await ctx.send(f"{player1.mention}, you need to choose a class first!")
        if not player2_data["character_class"]:
            return await ctx.send(f"{opponent.mention} needs to choose a class first!")

        self.battles[player1.id] = self.create_battle_data(player1_data, opponent.id)
        self.battles[opponent.id] = self.create_battle_data(player2_data, player1.id)

        battle_msg = await ctx.send("Battle started!")
        winner, loser = await self.battle_loop(ctx, player1, opponent, battle_msg)

        if winner and loser:
            await self.end_battle(ctx, winner, loser)
        else:
            await ctx.send("The battle ended in a draw.")

        del self.battles[player1.id]
        del self.battles[opponent.id]
    
    def create_battle_data(self, player_data: Dict, opponent_id: int) -> Dict:
        return {
            "hp": player_data["hp"],
            "max_hp": player_data["hp"],
            "strength": player_data["strength"],
            "speed": player_data["speed"],
            "defense": player_data["defense"],
            "character_class": player_data["character_class"],
            "opponent": opponent_id,
            "ability_cooldown": 0,
            "special_cooldown": 0,
        }

    async def battle_loop(self, ctx, player1: discord.Member, player2: discord.Member, battle_msg: discord.Message) -> Tuple[Optional[discord.Member], Optional[discord.Member]]:
        turn = 0
        while True:
            turn += 1
            for current_player in (player1, player2):
                opponent = player2 if current_player == player1 else player1
                
                embed = self.create_battle_embed(current_player, opponent, turn)
                await battle_msg.edit(embed=embed)

                action = await self.get_action(ctx, current_player)
                damage = await self.execute_action(ctx, current_player, opponent, action)
                
                self.battles[opponent.id]["hp"] -= damage
                if self.battles[opponent.id]["hp"] <= 0:
                    return current_player, opponent

            # Reduce cooldowns
            for player_id in (player1.id, player2.id):
                self.battles[player_id]["ability_cooldown"] = max(0, self.battles[player_id]["ability_cooldown"] - 1)
                self.battles[player_id]["special_cooldown"] = max(0, self.battles[player_id]["special_cooldown"] - 1)

            await asyncio.sleep(2)

    async def get_action(self, ctx, player: discord.Member) -> str:
        valid_actions = ['attack', 'defend', 'ability', 'special']
        await ctx.send(f"{player.mention}, choose your action: {', '.join(valid_actions)}")

        def check(m):
            return m.author == player and m.channel == ctx.channel and m.content.lower() in valid_actions

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            return msg.content.lower()
        except asyncio.TimeoutError:
            return 'attack'  # Default to attack if no input

    async def execute_action(self, ctx, attacker: discord.Member, defender: discord.Member, action: str) -> int:
        attacker_data = self.battles[attacker.id]
        
        if action == 'attack':
            damage = max(0, attacker_data['strength'] - self.battles[defender.id]['defense'] // 2)
            await ctx.send(f"{attacker.mention} attacks for {damage} damage!")
            return damage
        elif action == 'defend':
            attacker_data['defense'] += 5
            await ctx.send(f"{attacker.mention} defends, increasing their defense!")
            return 0
        elif action == 'ability':
            if attacker_data['ability_cooldown'] > 0:
                await ctx.send(f"{attacker.mention}'s ability is on cooldown for {attacker_data['ability_cooldown']} more turns.")
                return 0
            damage = attacker_data['strength'] * 2
            attacker_data['ability_cooldown'] = 3
            await ctx.send(f"{attacker.mention} uses their ability for {damage} damage!")
            return damage
        elif action == 'special':
            if attacker_data['special_cooldown'] > 0:
                await ctx.send(f"{attacker.mention}'s special is on cooldown for {attacker_data['special_cooldown']} more turns.")
                return 0
            damage = attacker_data['strength'] * 3
            attacker_data['special_cooldown'] = 5
            await ctx.send(f"{attacker.mention} uses their special move for {damage} damage!")
            return damage

    def create_battle_embed(self, player1: discord.Member, player2: discord.Member, turn: int) -> discord.Embed:
        embed = discord.Embed(title=f"Battle (Turn {turn})", color=discord.Color.red())
        
        for player in (player1, player2):
            battle_data = self.battles[player.id]
            embed.add_field(
                name=f"{player.name} ({battle_data['character_class']})",
                value=f"HP: {battle_data['hp']}/{battle_data['max_hp']}\n"
                    f"STR: {battle_data['strength']} | "
                    f"SPD: {battle_data['speed']} | "
                    f"DEF: {battle_data['defense']}\n"
                    f"Ability CD: {battle_data['ability_cooldown']} | "
                    f"Special CD: {battle_data['special_cooldown']}",
                inline=False
            )
        
        return embed

    async def end_battle(self, ctx, winner: discord.Member, loser: discord.Member):
        exp_gain = random.randint(10, 20)
        berry_gain = random.randint(100, 200)

        async with self.config.member(winner).all() as winner_data:
            winner_data['exp'] += exp_gain
            winner_data['berries'] += berry_gain

        await ctx.send(f"🎉 {winner.mention} wins the battle!\n"
                       f"Gained {exp_gain} EXP and {berry_gain} berries!")

    @commands.command()
    async def stat(self, ctx):
        """Display your current stats."""
        user_data = await self.config.member(ctx.author).all()
        embed = discord.Embed(title=f"{ctx.author.name}'s Stats", color=discord.Color.blue())
        embed.add_field(name="Class", value=user_data['character_class'] or "Not set", inline=False)
        embed.add_field(name="HP", value=user_data['hp'], inline=True)
        embed.add_field(name="Strength", value=user_data['strength'], inline=True)
        embed.add_field(name="Speed", value=user_data['speed'], inline=True)
        embed.add_field(name="Defense", value=user_data['defense'], inline=True)
        embed.add_field(name="EXP", value=user_data['exp'], inline=True)
        embed.add_field(name="Berries", value=user_data['berries'], inline=True)
        await ctx.send(embed=embed)

    @commands.command()
    async def choose_class(self, ctx, class_name: str):
        """Choose your character class."""
        valid_classes = ['swordsman', 'sniper', 'navigator', 'cook', 'doctor']
        if class_name.lower() not in valid_classes:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(valid_classes)}")

        async with self.config.member(ctx.author).all() as user_data:
            user_data['character_class'] = class_name.capitalize()
            
        await ctx.send(f"You are now a {class_name.capitalize()}!")
