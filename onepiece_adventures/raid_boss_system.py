import discord 
from redbot.core import commands, Config
import random
import asyncio

class RaidBossSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.active_raid = None
        self.raid_timer = None

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
        
        # Start the raid timer
        self.raid_timer = asyncio.create_task(self.end_raid_timer(ctx))
        self.last_raid_time = datetime.now().timestamp()

    async def join_raid(self, ctx):
        if not self.active_raid:
            await ctx.send("There is no active raid boss right now.")
            return

        user_data = await self.config.member(ctx.author).all()
        self.active_raid["participants"][ctx.author.id] = {
            "damage_dealt": 0,
            "strength": user_data["strength"],
            "defense": user_data["defense"],
            "attacks_left": 3
        }
        await ctx.send(f"{ctx.author.name} has joined the raid against {self.active_raid['name']}!")

    async def attack_raid_boss(self, ctx):
        if not self.active_raid or ctx.author.id not in self.active_raid["participants"]:
            await ctx.send("You're not participating in the current raid.")
            return

        participant = self.active_raid["participants"][ctx.author.id]
        if participant["attacks_left"] <= 0:
            await ctx.send(f"{ctx.author.name}, you have no attacks left in this raid!")
            return

        damage = random.randint(100, 500) + participant["strength"]
        self.active_raid["hp"] -= damage
        participant["damage_dealt"] += damage
        participant["attacks_left"] -= 1

        await ctx.send(f"{ctx.author.name} dealt {damage} damage to {self.active_raid['name']}! Attacks left: {participant['attacks_left']}")

        if self.active_raid["hp"] <= 0:
            self.raid_timer.cancel()
            await self.end_raid(ctx)

    async def end_raid_timer(self, ctx):
        await asyncio.sleep(300)  # 5 minutes
        if self.active_raid:
            await self.end_raid(ctx, timeout=True)

    async def end_raid(self, ctx, timeout=False):
        if timeout:
            await ctx.send("Time's up! The raid boss has escaped.")
        else:
            await ctx.send(f"{self.active_raid['name']} has been defeated!")

        participants = sorted(
            self.active_raid["participants"].items(),
            key=lambda x: x[1]["damage_dealt"],
            reverse=True
        )

        total_damage = sum(p["damage_dealt"] for p in self.active_raid["participants"].values())
        
        await ctx.send("Raid Participants:")
        for i, (user_id, data) in enumerate(participants, 1):
            user = self.bot.get_user(user_id)
            if user:
                await ctx.send(f"{i}. {user.name}: {data['damage_dealt']} damage")

        # Reward top 3 participants
        for i, (user_id, data) in enumerate(participants[:3], 1):
            user = self.bot.get_user(user_id)
            if user:
                exp_reward = 10000 if i == 1 else 7500 if i == 2 else 5000
                berry_reward = int(1000000 * (data["damage_dealt"] / total_damage))
                reputation_reward = 1000 if i == 1 else 750 if i == 2 else 500

                user_data = await self.config.member(user).all()
                user_data["exp"] += exp_reward
                user_data["berries"] += berry_reward
                user_data["reputation"]["pirate"] += reputation_reward
                await self.config.member(user).set(user_data)

                await ctx.send(f"{user.name} earned {exp_reward} exp, {berry_reward} berries, and {reputation_reward} pirate reputation!")

        self.active_raid = None
        self.raid_timer = None

    async def raid_status(self, ctx):
        if not self.active_raid:
            await ctx.send("There is no active raid boss right now.")
            return

        boss_hp_percentage = (self.active_raid["hp"] / self.active_raid["max_hp"]) * 100
        participants = sorted(
            self.active_raid["participants"].items(),
            key=lambda x: x[1]["damage_dealt"],
            reverse=True
        )

        status_message = f"**Raid Boss: {self.active_raid['name']}**\n"
        status_message += f"HP: {self.active_raid['hp']}/{self.active_raid['max_hp']} ({boss_hp_percentage:.2f}%)\n\n"
        status_message += "**Top Participants:**\n"

        for i, (user_id, data) in enumerate(participants[:5], 1):
            user = self.bot.get_user(user_id)
            if user:
                status_message += f"{i}. {user.name}: {data['damage_dealt']} damage\n"

        await ctx.send(status_message)
