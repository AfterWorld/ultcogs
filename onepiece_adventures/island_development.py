import discord
from redbot.core import commands, Config
import asyncio
import random

class IslandDevelopment:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.development_options = {
            "Port": {"cost": 50000, "income": 1000, "description": "Increases trade and travel efficiency"},
            "Farm": {"cost": 30000, "income": 500, "description": "Produces food and resources"},
            "Mine": {"cost": 70000, "income": 1500, "description": "Extracts valuable minerals"},
            "Shipyard": {"cost": 100000, "income": 2000, "description": "Allows for ship construction and repair"},
            "Market": {"cost": 40000, "income": 800, "description": "Boosts local economy and trade"},
        }

    async def invest_in_island(self, ctx, island_name: str, development: str):
        user_data = await self.config.member(ctx.author).all()
        islands = await self.config.guild(ctx.guild).islands()

        if island_name not in islands:
            return await ctx.send("That island doesn't exist or hasn't been discovered yet.")

        if development not in self.development_options:
            return await ctx.send("Invalid development option. Choose from: " + ", ".join(self.development_options.keys()))

        cost = self.development_options[development]["cost"]
        if user_data["berries"] < cost:
            return await ctx.send(f"You don't have enough berries. You need {cost} berries to build a {development}.")

        if development in islands[island_name].get("developments", []):
            return await ctx.send(f"This island already has a {development}.")

        user_data["berries"] -= cost
        if "developments" not in islands[island_name]:
            islands[island_name]["developments"] = []
        islands[island_name]["developments"].append(development)

        await self.config.member(ctx.author).set(user_data)
        await self.config.guild(ctx.guild).islands.set(islands)

        await ctx.send(f"You've successfully invested in a {development} on {island_name}!")

    async def collect_island_income(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        islands = await self.config.guild(ctx.guild).islands()

        total_income = 0
        for island_name, island_data in islands.items():
            for development in island_data.get("developments", []):
                total_income += self.development_options[development]["income"]

        user_data["berries"] += total_income
        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"You've collected {total_income} berries from your island developments!")

    @commands.command()
    async def island_info(self, ctx, island_name: str):
        islands = await self.config.guild(ctx.guild).islands()
        if island_name not in islands:
            return await ctx.send("That island doesn't exist or hasn't been discovered yet.")

        island_data = islands[island_name]
        embed = discord.Embed(title=f"Island Info: {island_name}", color=discord.Color.green())
        embed.add_field(name="Developments", value=", ".join(island_data.get("developments", ["None"])), inline=False)
        
        total_income = sum(self.development_options[dev]["income"] for dev in island_data.get("developments", []))
        embed.add_field(name="Total Income", value=f"{total_income} berries per collection", inline=False)

        await ctx.send(embed=embed)