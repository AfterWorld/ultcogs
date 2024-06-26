import discord 
from redbot.core import commands, Config
import random
import asyncio

__all__ = ['RaidBossSystem']

class RaidBossSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.active_raid = None  

    async def spawn_raid_boss(self, ctx):
        if self.active_raid:
            await ctx.send("A raid boss is already active!")
            return

        bosses = [
            {"name": "Kaido", "hp": 100000, "attack": 1000},
            {"name": "Big Mom", "hp": 90000, "attack": 900},
            {"name": "Blackbeard", "hp": 80000, "attack": 800},
        ]
        boss = random.choice(bosses)
        self.active_raid = {
            "name": boss["name"],
            "hp": boss["hp"],
            "max_hp": boss["hp"],
            "attack": boss["attack"],
            "participants": {}
        }

        await ctx.send(f"A wild {boss['name']} has appeared! Type `!join_raid` to participate in the raid!")

    async def join_raid(self, ctx):
        if not self.active_raid:
            await ctx.send("There is no active raid boss right now.")
            return

        user_data = await self.config.member(ctx.author).all()
        self.active_raid["participants"][ctx.author.id] = {
            "damage_dealt": 0,
            "strength": user_data["strength"],
            "defense": user_data["defense"]
        }
        await ctx.send(f"{ctx.author.name} has joined the raid against {self.active_raid['name']}!")

    async def attack_raid_boss(self, ctx):
        if not self.active_raid or ctx.author.id not in self.active_raid["participants"]:
            await ctx.send("You're not participating in the current raid.")
            return

        damage = random.randint(100, 500) + self.active_raid["participants"][ctx.author.id]["strength"]
        self.active_raid["hp"] -= damage
        self.active_raid["participants"][ctx.author.id]["damage_dealt"] += damage

        await ctx.send(f"{ctx.author.name} dealt {damage} damage to {self.active_raid['name']}!")

        if self.active_raid["hp"] <= 0:
            await self.end_raid(ctx)

    async def end_raid(self, ctx):
        total_damage = sum(p["damage_dealt"] for p in self.active_raid["participants"].values())
        rewards = {
            "berries": 1000000,
            "exp": 10000,
            "reputation": 1000
        }

        for user_id, data in self.active_raid["participants"].items():
            user = self.bot.get_user(user_id)
            if user:
                share = data["damage_dealt"] / total_damage
                user_rewards = {k: int(v * share) for k, v in rewards.items()}
                
                user_data = await self.config.member(user).all()
                user_data["berries"] += user_rewards["berries"]
                user_data["exp"] += user_rewards["exp"]
                user_data["reputation"]["pirate"] += user_rewards["reputation"]
                await self.config.member(user).set(user_data)

                await ctx.send(f"{user.name} earned {user_rewards['berries']} berries, {user_rewards['exp']} exp, and {user_rewards['reputation']} pirate reputation!")

        self.active_raid = None
        await ctx.send("The raid has ended! Congratulations to all participants!")
        
