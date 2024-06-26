import discord # type: ignore
from redbot.core import commands, Config # type: ignore
import random

class MarineCareerSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.marine_ranks = [
            "Chore Boy", "Seaman Recruit", "Seaman First Class", "Petty Officer",
            "Lieutenant Junior Grade", "Lieutenant", "Lieutenant Commander",
            "Commander", "Captain", "Commodore", "Rear Admiral", "Vice Admiral", "Admiral"
        ]

    async def join_marines(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data['crew']:
            await ctx.send("You can't join the Marines while you're in a pirate crew!")
            return

        user_data['marine_rank'] = 0  # Chore Boy
        user_data['faction'] = 'Marine'
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"Welcome to the Marines, {ctx.author.mention}! You start as a {self.marine_ranks[0]}.")

    async def marine_promotion(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('faction') != 'Marine':
            await ctx.send("You're not a Marine!")
            return

        current_rank = user_data['marine_rank']
        if current_rank >= len(self.marine_ranks) - 1:
            await ctx.send("You've already reached the highest Marine rank!")
            return

        promotion_chance = 0.5 - (current_rank * 0.05)  # Gets harder to promote at higher ranks
        if random.random() < promotion_chance:
            user_data['marine_rank'] += 1
            await self.config.member(ctx.author).set(user_data)
            new_rank = self.marine_ranks[user_data['marine_rank']]
            await ctx.send(f"Congratulations, {ctx.author.mention}! You've been promoted to {new_rank}!")
        else:
            await ctx.send("You weren't promoted this time. Keep working hard!")

    async def marine_mission(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('faction') != 'Marine':
            await ctx.send("Only Marines can take on Marine missions!")
            return

        missions = [
            "Patrol the seas",
            "Investigate pirate activity",
            "Protect a merchant ship",
            "Capture a notorious pirate",
            "Defend a Marine base"
        ]

        mission = random.choice(missions)
        await ctx.send(f"Your mission: {mission}")

        # Simulate mission success based on marine rank and random chance
        success_chance = 0.5 + (user_data['marine_rank'] * 0.05)
        if random.random() < success_chance:
            reward = random.randint(1000, 5000) * (user_data['marine_rank'] + 1)
            user_data['berries'] += reward
            user_data['exp'] += 50 * (user_data['marine_rank'] + 1)
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"Mission successful! You earned {reward} berries and some experience.")
        else:
            await ctx.send("Mission failed. Better luck next time!")

    async def marine_info(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('faction') != 'Marine':
            await ctx.send("You're not a Marine!")
            return

        rank = self.marine_ranks[user_data['marine_rank']]
        embed = discord.Embed(title=f"Marine Info: {ctx.author.name}", color=discord.Color.blue())
        embed.add_field(name="Rank", value=rank, inline=False)
        embed.add_field(name="Berries", value=user_data['berries'], inline=True)
        embed.add_field(name="Experience", value=user_data['exp'], inline=True)
        await ctx.send(embed=embed)

    async def marine_patrol(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('faction') != 'Marine':
            return await ctx.send("Only Marines can go on patrol!")
        
        encounters = [
            "You caught a group of petty thieves.",
            "You assisted in evacuating civilians from a dangerous area.",
            "You successfully broke up a pirate gathering.",
            "You discovered and confiscated illegal weapons.",
            "You helped resolve a dispute between local merchants."
        ]
        
        encounter = random.choice(encounters)
        reward = random.randint(500, 2000)
        exp_gain = random.randint(20, 50)
        
        user_data['berries'] += reward
        user_data['exp'] += exp_gain
        await self.config.member(ctx.author).set(user_data)
        
        await ctx.send(f"Patrol Report: {encounter}\nYou earned {reward} berries and {exp_gain} exp.")

    async def request_promotion(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('faction') != 'Marine':
            return await ctx.send("Only Marines can request promotions!")
        
        current_rank = user_data['marine_rank']
        if current_rank >= len(self.marine_ranks) - 1:
            return await ctx.send("You've already reached the highest Marine rank!")
        
        required_exp = (current_rank + 1) * 1000
        if user_data['exp'] < required_exp:
            return await ctx.send(f"You need {required_exp} total exp to be eligible for promotion. Keep training!")
        
        promotion_chance = 0.5 - (current_rank * 0.05)
        if random.random() < promotion_chance:
            user_data['marine_rank'] += 1
            new_rank = self.marine_ranks[user_data['marine_rank']]
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"Congratulations! You've been promoted to {new_rank}!")
        else:
            await ctx.send("Your promotion request was denied. Keep up the good work and try again later!")