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
        self.battle_items = ["Health Potion", "Stamina Boost", "Smoke Bomb"]

    async def choose_class(self, ctx, class_name: str):
        if class_name not in self.classes:
            return await ctx.send(f"Invalid class. Choose from: {', '.join(self.classes.keys())}")

        user_data = await self.config.member(ctx.author).all()
        if user_data.get("character_class"):
            return await ctx.send("You've already chosen a class!")

        user_data["character_class"] = class_name
        for stat, bonus in self.classes[class_name].items():
            user_data[stat] += bonus

        # Initialize inventory
        user_data["inventory"] = {item: 3 for item in self.battle_items}

        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You are now a {class_name}! Your stats have been adjusted accordingly, and you've received some starting items.")

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
        
        inventory = user_data.get("inventory", {})
        if inventory:
            inv_list = "\n".join([f"{item}: {quantity}" for item, quantity in inventory.items()])
            embed.add_field(name="Inventory", value=inv_list, inline=False)
        else:
            embed.add_field(name="Inventory", value="Empty", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command()
    async def buy_item(self, ctx, item: str, quantity: int = 1):
        user_data = await self.config.member(ctx.author).all()
        if item not in self.battle_items:
            return await ctx.send(f"Invalid item. Choose from: {', '.join(self.battle_items)}")

        cost = 50 * quantity  # Assuming each item costs 50 berries
        if user_data["berries"] < cost:
            return await ctx.send(f"You don't have enough berries. You need {cost} berries to buy {quantity} {item}(s).")

        user_data["berries"] -= cost
        user_data["inventory"] = user_data.get("inventory", {})
        user_data["inventory"][item] = user_data["inventory"].get(item, 0) + quantity

        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"You've bought {quantity} {item}(s) for {cost} berries.")

    @commands.command()
    async def inventory(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data.get("inventory", {})
        
        if not inventory:
            return await ctx.send("Your inventory is empty.")

        embed = discord.Embed(title=f"{ctx.author.name}'s Inventory", color=discord.Color.green())
        for item, quantity in inventory.items():
            embed.add_field(name=item, value=quantity, inline=True)
        
        embed.set_footer(text=f"Berries: {user_data['berries']}")
        await ctx.send(embed=embed)

    @commands.command()
    async def use_item(self, ctx, item: str):
        user_data = await self.config.member(ctx.author).all()
        inventory = user_data.get("inventory", {})

        if item not in inventory or inventory[item] <= 0:
            return await ctx.send(f"You don't have any {item} in your inventory.")

        # Implement item effects here
        if item == "Health Potion":
            user_data["hp"] = min(user_data["hp"] + 50, user_data["max_hp"])
            await ctx.send(f"You used a Health Potion and restored 50 HP!")
        elif item == "Stamina Boost":
            # Implement stamina boost logic if you have a stamina system
            await ctx.send(f"You used a Stamina Boost!")
        elif item == "Smoke Bomb":
            # Implement smoke bomb logic (perhaps useful in battles or for escaping)
            await ctx.send(f"You used a Smoke Bomb!")

        inventory[item] -= 1
        if inventory[item] == 0:
            del inventory[item]

        user_data["inventory"] = inventory
        await self.config.member(ctx.author).set(user_data)
