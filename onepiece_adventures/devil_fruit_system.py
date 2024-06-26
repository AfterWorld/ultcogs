import discord 
from redbot.core import commands, Config 
import random
import asyncio

class DevilFruitSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.devil_fruits = {
            "Gomu Gomu no Mi": {"type": "Paramecia", "ability": "Rubber Body", "awakened_ability": "Environment Rubberization"},
            "Mera Mera no Mi": {"type": "Logia", "ability": "Fire Generation and Control", "awakened_ability": "Flame Emperor"},
            "Hie Hie no Mi": {"type": "Logia", "ability": "Ice Generation and Control", "awakened_ability": "Absolute Zero"},
            "Yami Yami no Mi": {"type": "Logia", "ability": "Darkness Control", "awakened_ability": "Black Hole"},
            "Gura Gura no Mi": {"type": "Paramecia", "ability": "Vibration Generation", "awakened_ability": "Tectonic Manipulation"},
            "Ope Ope no Mi": {"type": "Paramecia", "ability": "Operating Room Creation", "awakened_ability": "Reality Surgeon"},
            "Moku Moku no Mi": {"type": "Logia", "ability": "Smoke Generation and Control", "awakened_ability": "Smoke World"},
            "Hana Hana no Mi": {"type": "Paramecia", "ability": "Body Part Replication", "awakened_ability": "Infinite Bloom"},
        }

    async def eat_devil_fruit(self, ctx, fruit_name: str):
        user_data = await self.config.member(ctx.author).all()
        if user_data.get('devil_fruit'):
            await ctx.send("You've already eaten a Devil Fruit! You can't eat another one.")
            return

        if fruit_name not in self.devil_fruits:
            await ctx.send("That Devil Fruit doesn't exist.")
            return

        user_data['devil_fruit'] = fruit_name
        user_data['devil_fruit_level'] = 1
        user_data['devil_fruit_exp'] = 0
        user_data['devil_fruit_awakened'] = False
        await self.config.member(ctx.author).set(user_data)

        fruit_info = self.devil_fruits[fruit_name]
        await ctx.send(f"You've eaten the {fruit_name} ({fruit_info['type']}-type)! "
                       f"You now have the ability of {fruit_info['ability']}. "
                       f"Remember, you can no longer swim!")

    async def awaken_devil_fruit(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get('devil_fruit'):
            await ctx.send("You haven't eaten a Devil Fruit yet!")
            return

        if user_data.get('devil_fruit_awakened', False):
            await ctx.send("Your Devil Fruit power is already awakened!")
            return

        if user_data['devil_fruit_level'] < 50:  # Requirement for awakening
            await ctx.send("Your Devil Fruit mastery is too low to awaken your power. Keep training!")
            return

        # Awakening chance based on level and haki
        awakening_chance = (user_data['devil_fruit_level'] - 40) * 0.02 + user_data.get('haki_level', 0) * 0.05
        if random.random() < awakening_chance:
            user_data['devil_fruit_awakened'] = True
            await self.config.member(ctx.author).set(user_data)
            fruit_info = self.devil_fruits[user_data['devil_fruit']]
            await ctx.send(f"Congratulations! You've awakened your {user_data['devil_fruit']} power! "
                           f"You now have access to the awakened ability: {fruit_info['awakened_ability']}!")
            await self.apply_awakening_buffs(ctx)
        else:
            await ctx.send("You tried to awaken your Devil Fruit power, but failed. Keep training and try again later!")

    async def apply_awakening_buffs(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        fruit_type = self.devil_fruits[user_data['devil_fruit']]['type']

        if fruit_type == "Paramecia":
            user_data['strength'] = user_data.get('strength', 0) + 20
            user_data['defense'] = user_data.get('defense', 0) + 20
        elif fruit_type == "Logia":
            user_data['defense'] = user_data.get('defense', 0) + 30
            user_data['speed'] = user_data.get('speed', 0) + 10
        elif fruit_type == "Zoan":
            user_data['strength'] = user_data.get('strength', 0) + 15
            user_data['speed'] = user_data.get('speed', 0) + 15
            user_data['defense'] = user_data.get('defense', 0) + 10

        await self.config.member(ctx.author).set(user_data)
        await ctx.send("Your stats have increased due to Devil Fruit awakening!")

    async def devil_fruit_info(self, ctx, fruit_name: str = None):
        if fruit_name:
            if fruit_name in self.devil_fruits:
                fruit_info = self.devil_fruits[fruit_name]
                await ctx.send(f"{fruit_name} ({fruit_info['type']}-type):\n"
                               f"Basic Ability: {fruit_info['ability']}\n"
                               f"Awakened Ability: {fruit_info['awakened_ability']}")
            else:
                await ctx.send("That Devil Fruit doesn't exist.")
        else:
            fruits_list = "\n".join([f"{name} ({info['type']})" for name, info in self.devil_fruits.items()])
            await ctx.send(f"Available Devil Fruits:\n{fruits_list}")

    async def devil_fruit_attack(self, ctx, target: discord.Member):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get('devil_fruit'):
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        fruit = self.devil_fruits[user_data['devil_fruit']]
        damage = random.randint(50, 200) * (1 + user_data.get('haki_level', 0) * 0.1)
        
        if user_data.get('devil_fruit_awakened', False):
            damage *= 1.5  # 50% damage boost for awakened fruits

        target_data = await self.config.member(target).all()
        if target_data.get('devil_fruit') and self.devil_fruits[target_data['devil_fruit']]['type'] == 'Logia':
            if user_data.get('haki_level', 0) > target_data.get('haki_level', 0):
                target_data['hp'] = max(0, target_data.get('hp', 100) - damage)
                await ctx.send(f"Your Haki-infused {fruit['ability']} attack hit {target.name} for {damage} damage!")
            else:
                await ctx.send(f"Your {fruit['ability']} attack passed through {target.name}'s Logia body!")
        else:
            target_data['hp'] = max(0, target_data.get('hp', 100) - damage)
            await ctx.send(f"Your {fruit['ability']} attack hit {target.name} for {damage} damage!")
        
        await self.config.member(target).set(target_data)

    async def train_devil_fruit(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get('devil_fruit'):
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        exp_gain = random.randint(10, 30)
        user_data['devil_fruit_exp'] = user_data.get('devil_fruit_exp', 0) + exp_gain
        
        if user_data['devil_fruit_exp'] >= user_data.get('devil_fruit_level', 1) * 100:
            user_data['devil_fruit_level'] = user_data.get('devil_fruit_level', 1) + 1
            user_data['devil_fruit_exp'] = 0
            await ctx.send(f"Your mastery over the {user_data['devil_fruit']} has increased to level {user_data['devil_fruit_level']}!")
            
            # Chance for awakening through training
            if user_data['devil_fruit_level'] >= 50 and not user_data.get('devil_fruit_awakened', False):
                awakening_chance = (user_data['devil_fruit_level'] - 40) * 0.01
                if random.random() < awakening_chance:
                    await self.awaken_devil_fruit(ctx)
                    return
        else:
            await ctx.send(f"You trained with your {user_data['devil_fruit']} powers and gained {exp_gain} experience!")
        
        await self.config.member(ctx.author).set(user_data)

    async def devil_fruit_ultimate(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get('devil_fruit'):
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        if not user_data.get('devil_fruit_awakened', False):
            return await ctx.send("You need to awaken your Devil Fruit to use its ultimate ability!")
        
        fruit_info = self.devil_fruits[user_data['devil_fruit']]
        cooldown = 3600  # 1 hour cooldown
        last_use = user_data.get('last_ultimate_use', 0)
        
        if (ctx.message.created_at.timestamp() - last_use) < cooldown:
            remaining = cooldown - (ctx.message.created_at.timestamp() - last_use)
            return await ctx.send(f"You can't use your ultimate ability yet. It will be available in {remaining:.0f} seconds.")
        
        await ctx.send(f"You unleash your awakened power: {fruit_info['awakened_ability']}!")
        # Implement the effects of the ultimate ability here
        
        user_data['last_ultimate_use'] = ctx.message.created_at.timestamp()
        await self.config.member(ctx.author).set(user_data)

    async def devil_fruit_mastery(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        if not user_data.get('devil_fruit'):
            return await ctx.send("You haven't eaten a Devil Fruit yet!")
        
        fruit_info = self.devil_fruits[user_data['devil_fruit']]
        embed = discord.Embed(title=f"{ctx.author.name}'s Devil Fruit Mastery", color=discord.Color.purple())
        embed.add_field(name="Devil Fruit", value=user_data['devil_fruit'])
        embed.add_field(name="Type", value=fruit_info['type'])
        embed.add_field(name="Basic Ability", value=fruit_info['ability'])
        embed.add_field(name="Mastery Level", value=user_data.get('devil_fruit_level', 1))
        embed.add_field(name="Experience", value=f"{user_data.get('devil_fruit_exp', 0)}/{user_data.get('devil_fruit_level', 1) * 100}")
        embed.add_field(name="Awakened", value="Yes" if user_data.get('devil_fruit_awakened', False) else "No")
        if user_data.get('devil_fruit_awakened', False):
            embed.add_field(name="Awakened Ability", value=fruit_info['awakened_ability'])
        
        await ctx.send(embed=embed)
