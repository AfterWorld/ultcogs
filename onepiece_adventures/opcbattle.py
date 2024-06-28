import discord
from discord.ui import Button, View
from redbot.core import commands, Config
import random
import asyncio
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class BattleView(View):
    def __init__(self, battle):
        super().__init__(timeout=30)
        self.battle = battle
        self.action = None

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: Button):
        self.action = "attack"
        self.stop()

    @discord.ui.button(label="Defend", style=discord.ButtonStyle.primary)
    async def defend(self, interaction: discord.Interaction, button: Button):
        self.action = "defend"
        self.stop()

    @discord.ui.button(label="Ability", style=discord.ButtonStyle.success)
    async def ability(self, interaction: discord.Interaction, button: Button):
        self.action = "ability"
        self.stop()

    @discord.ui.button(label="Special", style=discord.ButtonStyle.secondary)
    async def special(self, interaction: discord.Interaction, button: Button):
        self.action = "special"
        self.stop()

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
            "status": [],
        }

    async def battle_loop(self, ctx, player1: discord.Member, player2: discord.Member, battle_msg: discord.Message) -> Tuple[Optional[discord.Member], Optional[discord.Member]]:
        turn = 0
        while True:
            turn += 1
            for current_player in (player1, player2):
                opponent = player2 if current_player == player1 else player1
                
                embed = self.create_battle_embed(current_player, opponent, turn)
                view = BattleView(self)
                await battle_msg.edit(embed=embed, view=view)

                await view.wait()
                action = view.action or "attack"  # Default to attack if no button is pressed

                damage = await self.execute_action(ctx, current_player, opponent, action)
                
                self.battles[opponent.id]["hp"] -= damage
                if self.battles[opponent.id]["hp"] <= 0:
                    return current_player, opponent

            # Reduce cooldowns and handle status effects
            for player_id in (player1.id, player2.id):
                self.battles[player_id]["ability_cooldown"] = max(0, self.battles[player_id]["ability_cooldown"] - 1)
                self.battles[player_id]["special_cooldown"] = max(0, self.battles[player_id]["special_cooldown"] - 1)
                self.handle_status_effects(player_id)

            await asyncio.sleep(2)

    def handle_status_effects(self, player_id):
        player_data = self.battles[player_id]
        new_status = []
        for status, duration in player_data["status"]:
            if duration > 1:
                new_status.append((status, duration - 1))
            elif status == "confused":
                if random.random() < 0.5:
                    player_data["hp"] -= player_data["strength"] // 2
        player_data["status"] = new_status

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
            return await self.use_class_ability(ctx, attacker, defender)
        elif action == 'special':
            if attacker_data['special_cooldown'] > 0:
                await ctx.send(f"{attacker.mention}'s special is on cooldown for {attacker_data['special_cooldown']} more turns.")
                return 0
            return await self.use_special_move(ctx, attacker, defender)

    async def use_class_ability(self, ctx, attacker: discord.Member, defender: discord.Member) -> int:
        attacker_data = self.battles[attacker.id]
        class_name = attacker_data["character_class"]
        
        if class_name == "Swordsman":
            damage = attacker_data['strength'] * 2
            await ctx.send(f"{attacker.mention} uses Three Sword Style, dealing {damage} damage!")
        elif class_name == "Sniper":
            damage = attacker_data['strength'] * 2
            if random.random() < 0.8:
                await ctx.send(f"{attacker.mention} takes a precision shot, dealing {damage} damage!")
            else:
                await ctx.send(f"{attacker.mention}'s precision shot misses!")
                damage = 0
        elif class_name == "Navigator":
            attacker_data['speed'] += 5
            await ctx.send(f"{attacker.mention} uses their navigation skills to boost their speed!")
            damage = 0
        elif class_name == "Cook":
            heal = attacker_data['strength']
            attacker_data['hp'] = min(attacker_data['hp'] + heal, attacker_data['max_hp'])
            await ctx.send(f"{attacker.mention} cooks up a quick meal, restoring {heal} HP!")
            damage = 0
        elif class_name == "Doctor":
            heal = attacker_data['strength'] * 2
            attacker_data['hp'] = min(attacker_data['hp'] + heal, attacker_data['max_hp'])
            await ctx.send(f"{attacker.mention} applies medical knowledge to heal {heal} HP!")
            damage = 0
        else:
            await ctx.send(f"{attacker.mention} doesn't have a class ability!")
            damage = 0

        attacker_data['ability_cooldown'] = 3
        return damage

    async def use_special_move(self, ctx, attacker: discord.Member, defender: discord.Member) -> int:
        attacker_data = self.battles[attacker.id]
        defender_data = self.battles[defender.id]
        class_name = attacker_data["character_class"]
        base_damage = attacker_data['strength'] * 3

        if class_name == "Swordsman":
            move = random.choice(["**Santoryu: Oni Giri**", "**Ittoryu: Shishi Sonson**", "**Nitoryu: Sai Kuru**"])
            damage = int(base_damage * 2.5)
            await ctx.send(f"{attacker.mention} uses '{move}', slashing for {damage} damage!")
        elif class_name == "Sniper":
            move = random.choice(["**Fire Bird Star**", "**Exploding Star**", "**Clima-Tact: Thunderbolt Tempo**"])
            damage = int(base_damage * 2.2)
            if random.random() < 0.8:  # 80% accuracy
                await ctx.send(f"{attacker.mention} uses '{move}', striking for {damage} damage!")
            else:
                await ctx.send(f"{attacker.mention}'s '{move}' misses!")
                damage = 0
        elif class_name == "Navigator":
            move = random.choice(["**Clima-Tact: Cyclone Tempo**", "**Weather Egg: Rain Tempo**", "**Mirage Tempo: Fata Morgana**"])
            damage = int(base_damage * 1.8)
            defender_data["status"].append(("confused", 2))
            await ctx.send(f"{attacker.mention} uses '{move}', dealing {damage} damage and confusing {defender.mention}!")
        elif class_name == "Cook":
            move = random.choice(["**Diable Jambe: Flambage Shot**", "**Collier Shoot**", "**Party Table Kick Course**"])
            damage = int(base_damage * 2.3)
            heal = int(damage * 0.3)
            attacker_data["hp"] = min(attacker_data["hp"] + heal, attacker_data["max_hp"])
            await ctx.send(f"{attacker.mention} uses '{move}', dealing {damage} damage and healing for {heal} HP!")
        elif class_name == "Doctor":
            move = random.choice(["Scope", "**Monster Point: Konbie Genjin**", "**Cherry Blossom Blizzard**"])
            damage = int(base_damage * 2)
            attacker_data["status"] = [status for status in attacker_data["status"] if status[0] not in ["poison", "burn", "confused"]]
            await ctx.send(f"{attacker.mention} uses '{move}', dealing {damage} damage and curing all status effects!")
        else:
            await ctx.send(f"{attacker.mention} doesn't have any special moves!")
            damage = 0

        attacker_data['special_cooldown'] = 5
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
                    f"Special CD: {battle_data['special_cooldown']}\n"
                    f"Status: {', '.join(status for status, _ in battle_data['status']) or 'None'}",
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

    async def stats(self, ctx, member: discord.Member = None):
        """Display your or another member's current stats."""
        target = member or ctx.author
        user_data = await self.config.member(target).all()
        embed = discord.Embed(title=f"{target.name}'s Stats", color=discord.Color.blue())
        embed.add_field(name="Class", value=user_data['character_class'] or "Not set", inline=False)
        embed.add_field(name="HP", value=user_data['hp'], inline=True)
        embed.add_field(name="Strength", value=user_data['strength'], inline=True)
        embed.add_field(name="Speed", value=user_data['speed'], inline=True)
        embed.add_field(name="Defense", value=user_data['defense'], inline=True)
        embed.add_field(name="EXP", value=user_data['exp'], inline=True)
        embed.add_field(name="Berries", value=user_data['berries'], inline=True)
        await ctx.send(embed=embed)

    async def choose_class(self, ctx, class_name: str):
        """Choose your character class."""
        valid_classes = ['swordsman', 'sniper', 'navigator', 'cook', 'doctor']
        if class_name.lower() not in valid_classes:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(valid_classes)}")

        async with self.config.member(ctx.author).all() as user_data:
            user_data['character_class'] = class_name.capitalize()
            
        await ctx.send(f"You are now a {class_name.capitalize()}!")
