import discord
from redbot.core import commands, Config
import random
import asyncio

class DavyBackFight:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def start_davy_back_fight(self, ctx, opponent: discord.Member):
        if opponent.bot:
            await ctx.send("You can't challenge a bot to a Davy Back Fight!")
            return

        await ctx.send(f"{opponent.mention}, {ctx.author.mention} has challenged you to a Davy Back Fight! Do you accept? (yes/no)")

        def check(m):
            return m.author == opponent and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("The challenge has timed out.")
            return

        if msg.content.lower() == 'no':
            await ctx.send("The challenge was declined.")
            return

        await ctx.send("The Davy Back Fight begins! There will be three rounds: Donut Race, Groggy Ring, and Combat.")

        challenger_wins = 0
        opponent_wins = 0

        # Donut Race
        await ctx.send("Round 1: Donut Race!")
        if await self.donut_race(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Groggy Ring
        await ctx.send("Round 2: Groggy Ring!")
        if await self.groggy_ring(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Combat
        await ctx.send("Final Round: Combat!")
        if await self.combat(ctx, ctx.author, opponent):
            challenger_wins += 1
        else:
            opponent_wins += 1

        # Determine overall winner
        if challenger_wins > opponent_wins:
            winner = ctx.author
            loser = opponent
        else:
            winner = opponent
            loser = ctx.author

        await ctx.send(f"{winner.mention} has won the Davy Back Fight!")
        await self.award_prize(ctx, winner, loser)

    async def donut_race(self, ctx, player1, player2):
        await ctx.send("The Donut Race is a test of speed and navigation!")
        p1_speed = (await self.config.member(player1).speed()) * random.uniform(0.8, 1.2)
        p2_speed = (await self.config.member(player2).speed()) * random.uniform(0.8, 1.2)
        
        progress1 = 0
        progress2 = 0
        
        while progress1 < 100 and progress2 < 100:
            progress1 += p1_speed * random.uniform(0.5, 1.5)
            progress2 += p2_speed * random.uniform(0.5, 1.5)
            
            await ctx.send(f"{player1.name}: {'🛥' * int(progress1/10)}{'  ' * (10-int(progress1/10))} {progress1:.1f}%\n"
                           f"{player2.name}: {'🛥' * int(progress2/10)}{'  ' * (10-int(progress2/10))} {progress2:.1f}%")
            await asyncio.sleep(1)
        
        winner = player1 if progress1 >= 100 else player2
        await ctx.send(f"{winner.mention} wins the Donut Race!")
        return winner == player1

    async def groggy_ring(self, ctx, player1, player2):
        await ctx.send("The Groggy Ring is a test of strength and teamwork!")
        p1_strength = (await self.config.member(player1).strength()) * random.uniform(0.8, 1.2)
        p2_strength = (await self.config.member(player2).strength()) * random.uniform(0.8, 1.2)
        
        p1_score = 0
        p2_score = 0
        
        for round in range(1, 4):
            await ctx.send(f"Round {round}!")
            p1_roll = random.randint(1, 6)
            p2_roll = random.randint(1, 6)
            
            p1_total = p1_strength * p1_roll
            p2_total = p2_strength * p2_roll
            
            if p1_total > p2_total:
                p1_score += 1
                await ctx.send(f"{player1.name} wins round {round}!")
            elif p2_total > p1_total:
                p2_score += 1
                await ctx.send(f"{player2.name} wins round {round}!")
            else:
                await ctx.send("It's a tie!")
            
            await ctx.send(f"Current score: {player1.name} {p1_score} - {p2_score} {player2.name}")
            await asyncio.sleep(2)
        
        winner = player1 if p1_score > p2_score else player2
        await ctx.send(f"{winner.mention} wins the Groggy Ring!")
        return winner == player1

    async def combat(self, ctx, player1, player2):
        await ctx.send("The Combat round is a direct battle between the two players!")
        p1_hp = 100
        p2_hp = 100
        
        p1_attack = (await self.config.member(player1).strength()) * random.uniform(0.8, 1.2)
        p2_attack = (await self.config.member(player2).strength()) * random.uniform(0.8, 1.2)
        p1_defense = (await self.config.member(player1).defense()) * random.uniform(0.8, 1.2)
        p2_defense = (await self.config.member(player2).defense()) * random.uniform(0.8, 1.2)
        
        while p1_hp > 0 and p2_hp > 0:
            p1_damage = max(0, p1_attack - p2_defense/2) * random.uniform(0.8, 1.2)
            p2_damage = max(0, p2_attack - p1_defense/2) * random.uniform(0.8, 1.2)
            
            p2_hp -= p1_damage
            p1_hp -= p2_damage
            
            p1_hp_bar = '█' * int(p1_hp/10) + '░' * (10 - int(p1_hp/10))
            p2_hp_bar = '█' * int(p2_hp/10) + '░' * (10 - int(p2_hp/10))
            
            await ctx.send(f"{player1.name}: {p1_hp_bar} {max(0, p1_hp):.1f} HP\n"
                           f"{player2.name}: {p2_hp_bar} {max(0, p2_hp):.1f} HP")
            await asyncio.sleep(2)
        
        winner = player1 if p1_hp > p2_hp else player2
        await ctx.send(f"{winner.mention} wins the Combat round!")
        return winner == player1

    async def award_prize(self, ctx, winner, loser):
        prize_options = [
            {"name": "Rare Treasure Map", "type": "item"},
            {"name": "Mysterious Devil Fruit", "type": "item"},
            {"name": "Ancient Weapon Blueprint", "type": "item"},
            {"name": "Substantial Berries", "type": "currency", "amount": random.randint(10000, 100000)},
            {"name": "Powerful Ally", "type": "temp_buff", "duration": 24}  # Duration in hours
        ]
    
        prize = random.choice(prize_options)
        await ctx.send(f"{winner.mention} has won {prize['name']} from {loser.mention}!")
    
        winner_data = await self.config.member(winner).all()
    
        if prize['type'] == "item":
            if 'inventory' not in winner_data:
                winner_data['inventory'] = {}
            winner_data['inventory'][prize['name']] = winner_data['inventory'].get(prize['name'], 0) + 1
            await ctx.send(f"{winner.mention} has added {prize['name']} to their inventory!")
    
        elif prize['type'] == "currency":
            winner_data['berries'] = winner_data.get('berries', 0) + prize['amount']
            await ctx.send(f"{winner.mention} has gained {prize['amount']} Berries!")
    
        elif prize['type'] == "temp_buff":
            if 'temp_buffs' not in winner_data:
                winner_data['temp_buffs'] = {}
            expiry_time = ctx.message.created_at.timestamp() + (prize['duration'] * 3600)
            winner_data['temp_buffs'][prize['name']] = expiry_time
            await ctx.send(f"{winner.mention} has gained the {prize['name']} buff for {prize['duration']} hours!")
    
        winner_data['davy_back_wins'] = winner_data.get('davy_back_wins', 0) + 1
        await self.config.member(winner).set(winner_data)
    
        loser_data = await self.config.member(loser).all()
        loser_data['davy_back_losses'] = loser_data.get('davy_back_losses', 0) + 1
        await self.config.member(loser).set(loser_data)
