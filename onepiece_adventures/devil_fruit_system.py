import discord # type: ignore
from redbot.core import commands, Config # type: ignore
import random

class DevilFruitSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.devil_fruits = {
            "Gomu Gomu no Mi": {"type": "Paramecia", "ability": "Rubber Body"},
            "Mera Mera no Mi": {"type": "Logia", "ability": "Fire Generation and Control"},
            "Hie Hie no Mi": {"type": "Logia", "ability": "Ice Generation and Control"},
            "Yami Yami no Mi": {"type": "Logia", "ability": "Darkness Control"},
            "Gura Gura no Mi": {"type": "Paramecia", "ability": "Vibration Generation"},
            "Ope Ope no Mi": {"type": "Paramecia", "ability": "Operating Room Creation"},
            "Moku Moku no Mi": {"type": "Logia", "ability": "Smoke Generation and Control"},
            "Hana Hana no Mi": {"type": "Paramecia", "ability": "Body Part Replication"},
        }

    async def eat_devil_fruit(self, ctx, fruit_name: str):
        user_data = await self.config.member(ctx.author).all()
        if user_data['devil_fruit']:
            await ctx.send("You've already eaten a Devil Fruit! You can't eat another one.")
            return

        if fruit_name not in self.devil_fruits:
            await ctx.send("That Devil Fruit doesn't exist.")
            return

        user_data['devil_fruit'] = fruit_name
        user_data['devil_fruit_level'] = 1
        user_data['devil_fruit_exp'] = 0
        await self.config.member(ctx.author).set(user_data)

        fruit_info = self.devil_fruits[fruit_name]
        await ctx.send(f"You've eaten the {fruit_name} ({fruit_info['type']}-type)! "
                       f"You now have the ability of {fruit_info['ability']}. "
                       f"Remember, you can no longer swim!")

    async def awaken_devil_fruit(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data['devil_fruit']:
            await ctx.send("You haven't eaten a Devil Fruit yet!")
            return

        if user_data.get('devil_fruit_awakened', False):
            await ctx.send("Your Devil Fruit power is already awakened!")
            return

        if user_data['level'] < 50:  # Example requirement for awakening
            await ctx.send("Your level is too low to awaken your Devil Fruit power. Keep training!")
            return

        # Awakening chance based on level and haki
        awakening_chance = (user_data['level'] - 40) * 0.02 + user_data['haki_level'] * 0.05
        if random.random() < awakening_chance:
            user_data['devil_fruit_awakened'] = True
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"Congratulations! You've awakened your {user_data['devil_fruit']} power!")
            await self.apply_awakening_buffs(ctx)
        else:
            await ctx.send("You tried to awaken your Devil Fruit power, but failed. Keep training and try again later!")

    async def apply_awakening_buffs(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        fruit_type = self.devil_fruits[user_data['devil_fruit']]['type']

        if fruit_type == "Paramecia":
            user_data['strength'] += 20
            user_data['defense'] += 20
        elif fruit_type == "Logia":
            user_data['defense'] += 30
            user_data['speed'] += 10
        elif fruit_type == "Zoan":
            user_data['strength'] += 15
            user_data['speed'] += 15
            user_data['defense'] += 10

        await self.config.member(ctx.author).set(user_data)
        await ctx.send("Your stats have increased due to Devil Fruit awakening!")

    async def devil_fruit_info(self, ctx, fruit_name: str = None):
        if fruit_name:
            if fruit_name in self.devil_fruits:
                fruit_info = self.devil_fruits[fruit_name]
                await ctx.send(f"{fruit_name} ({fruit_info['type']}-type): {fruit_info['ability']}")
            else:
                await ctx.send("That Devil Fruit doesn't exist.")
        else:
            fruits_list = "\n".join([f"{name} ({info['type']})" for name, info in self.devil_fruits.items()])
            await ctx.send(f"Available Devil Fruits:\n{fruits_list}")

    async def devil_fruit_attack(self, ctx, target: discord.Member):
        user_data = await self.config.member(ctx.author).all()
        if not user_data['devil_fruit']:
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        fruit = self.devil_fruits[user_data['devil_fruit']]
        damage = random.randint(50, 200) * (1 + user_data['haki_level'] * 0.1)
        
        target_data = await self.config.member(target).all()
        if target_data['devil_fruit'] and self.devil_fruits[target_data['devil_fruit']]['type'] == 'Logia':
            if user_data['haki_level'] > target_data['haki_level']:
                target_data['hp'] = max(0, target_data['hp'] - damage)
                await ctx.send(f"Your Haki-infused {fruit['ability']} attack hit {target.name} for {damage} damage!")
            else:
                await ctx.send(f"Your {fruit['ability']} attack passed through {target.name}'s Logia body!")
        else:
            target_data['hp'] = max(0, target_data['hp'] - damage)
            await ctx.send(f"Your {fruit['ability']} attack hit {target.name} for {damage} damage!")
        
        await self.config.member(target).set(target_data)

    async def train_devil_fruit(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data['devil_fruit']:
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        if user_data['devil_fruit_exp'] >= user_data['devil_fruit_level'] * 100:
            user_data['devil_fruit_level'] += 1
            user_data['devil_fruit_exp'] = 0
            await ctx.send(f"Your mastery over the {user_data['devil_fruit']} has increased to level {user_data['devil_fruit_level']}!")
        else:
            exp_gain = random.randint(10, 30)
            user_data['devil_fruit_exp'] += exp_gain
            await ctx.send(f"You trained with your {user_data['devil_fruit']} powers and gained {exp_gain} experience!")
        
        await self.config.member(ctx.author).set(user_data)