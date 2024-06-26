import discord
from redbot.core import commands, Config
import random
import asyncio

class TreasureMapSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.legendary_artifacts = {
            "One Piece": {"rarity": 0.001, "value": 1000000000, "effect": "Grants the title of Pirate King"},
            "Ancient Weapon Pluton": {"rarity": 0.005, "value": 500000000, "effect": "Massively increases fleet power"},
            "Gol D. Roger's Log Pose": {"rarity": 0.01, "value": 100000000, "effect": "Reveals all island locations"},
            "Poneglyph Rubbing": {"rarity": 0.05, "value": 50000000, "effect": "Increases reputation with all factions"},
            "Legendary Sword": {"rarity": 0.1, "value": 10000000, "effect": "Greatly increases strength"},
        }

    async def find_treasure_map(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if random.random() < 0.1:  # 10% chance to find a map
            if "treasure_maps" not in user_data:
                user_data["treasure_maps"] = 0
            user_data["treasure_maps"] += 1
            await self.config.member(ctx.author).set(user_data)
            await ctx.send("You found a treasure map!")
        else:
            await ctx.send("You searched but didn't find any treasure maps this time.")

    async def use_treasure_map(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get("treasure_maps", 0) <= 0:
            return await ctx.send("You don't have any treasure maps to use!")

        user_data["treasure_maps"] -= 1
        await self.config.member(ctx.author).set(user_data)

        await ctx.send("You start following the treasure map...")
        await asyncio.sleep(3)  # Add some suspense

        if random.random() < 0.5:  # 50% chance to find treasure
            treasure = await self.generate_treasure(ctx)
            await ctx.send(f"You found a treasure! {treasure}")
        else:
            await ctx.send("The treasure map led to a dead end. Better luck next time!")

    async def generate_treasure(self, ctx):
        roll = random.random()
        for artifact, data in self.legendary_artifacts.items():
            if roll < data["rarity"]:
                user_data = await self.config.member(ctx.author).all()
                if "artifacts" not in user_data:
                    user_data["artifacts"] = []
                user_data["artifacts"].append(artifact)
                user_data["berries"] += data["value"]
                await self.config.member(ctx.author).set(user_data)
                return f"You found the legendary {artifact}! It's worth {data['value']} berries and {data['effect']}."

        # If no artifact was found, give some berries
        berries = random.randint(10000, 1000000)
        user_data = await self.config.member(ctx.author).all()
        user_data["berries"] += berries
        await self.config.member(ctx.author).set(user_data)
        return f"You found {berries} berries!"

    @commands.command()
    async def treasure_maps(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        maps = user_data.get("treasure_maps", 0)
        await ctx.send(f"You have {maps} treasure map(s).")

    @commands.command()
    async def artifacts(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        artifacts = user_data.get("artifacts", [])
        if not artifacts:
            return await ctx.send("You don't have any legendary artifacts.")

        embed = discord.Embed(title=f"{ctx.author.name}'s Legendary Artifacts", color=discord.Color.gold())
        for artifact in artifacts:
            data = self.legendary_artifacts[artifact]
            embed.add_field(name=artifact, value=f"Value: {data['value']} berries\nEffect: {data['effect']}", inline=False)

        await ctx.send(embed=embed)