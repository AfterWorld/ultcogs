import discord
from redbot.core import commands, Config
import random

class CharacterCustomization:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.classes = {
            "Swordsman": {"strength": 3, "defense": 2, "speed": 1},
            "Sniper": {"strength": 1, "defense": 1, "speed": 4},
            "Navigator": {"strength": 1, "defense": 2, "speed": 3},
            "Cook": {"strength": 2, "defense": 2, "speed": 2},
            "Doctor": {"strength": 1, "defense": 3, "speed": 2},
        }
        self.fighting_styles = {
            "Swordsman": ["One Sword Style", "Two Sword Style", "Three Sword Style"],
            "Sniper": ["Long Range", "Trick Shots", "Explosive Ammunition"],
            "Navigator": ["Weather Control", "Terrain Manipulation", "Cartography Mastery"],
            "Cook": ["Leg Techniques", "Flame Cooking", "Food-based Buffs"],
            "Doctor": ["Medical Knowledge", "Chemical Warfare", "Regeneration"],
        }

    async def choose_class(self, ctx, class_name: str):
        if class_name not in self.classes:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(self.classes.keys())}")

        user_data = await self.config.member(ctx.author).all()
        if user_data.get("character_class"):
            return await ctx.send("You've already chosen a class!")

        user_data["character_class"] = class_name
        for stat, bonus in self.classes[class_name].items():
            user_data[stat] += bonus

        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You are now a {class_name}! Your stats have been adjusted accordingly.")

    async def choose_fighting_style(self, ctx, style: str):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get("character_class"):
            return await ctx.send("You need to choose a class first!")

        class_name = user_data["character_class"]
        if style not in self.fighting_styles[class_name]:
            return await ctx.send(f"Invalid fighting style for {class_name}. Choose from: {', '.join(self.fighting_styles[class_name])}")

        user_data["fighting_style"] = style
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You have adopted the {style} fighting style!")

    async def customize_appearance(self, ctx, *, description: str):
        await self.config.member(ctx.author).appearance.set(description)
        await ctx.send("Your character's appearance has been updated!")

    @commands.command()
    async def character_info(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        embed = discord.Embed(title=f"{ctx.author.name}'s Character", color=discord.Color.blue())
        embed.add_field(name="Class", value=user_data.get("character_class", "Not chosen"), inline=False)
        embed.add_field(name="Fighting Style", value=user_data.get("fighting_style", "Not chosen"), inline=False)
        embed.add_field(name="Appearance", value=user_data.get("appearance", "Not set"), inline=False)
        embed.add_field(name="Strength", value=user_data["strength"], inline=True)
        embed.add_field(name="Defense", value=user_data["defense"], inline=True)
        embed.add_field(name="Speed", value=user_data["speed"], inline=True)
        await ctx.send(embed=embed)