import discord # type: ignore
from redbot.core import commands, Config # type: ignore
import asyncio
from datetime import datetime, timedelta
import random  # Add this import

class TrainingSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.training_cooldown = 3600  # 1 hour cooldown
        self.max_daily_trainings = 15

    async def train_attribute(self, ctx, attribute: str):
        valid_attributes = ["strength", "defense", "speed"]
        if attribute.lower() not in valid_attributes:
            await ctx.send(f"Invalid attribute. Choose from: {', '.join(valid_attributes)}")
            return

        user_data = await self.config.member(ctx.author).all()
        current_time = datetime.utcnow().timestamp()

        # Check cooldown
        if current_time - user_data.get(f"last_{attribute}_training", 0) < self.training_cooldown:
            cooldown_remaining = self.training_cooldown - (current_time - user_data.get(f"last_{attribute}_training", 0))
            await ctx.send(f"You need to wait {cooldown_remaining:.0f} seconds before training {attribute} again.")
            return

        # Check daily limit
        if user_data["training_counts"][attribute] >= self.max_daily_trainings:
            await ctx.send(f"You've reached the daily limit for training {attribute}. Try again tomorrow!")
            return

        # Perform training
        attribute_increase = random.randint(1, 3)
        user_data[attribute] += attribute_increase
        user_data["exp"] += 10
        user_data["training_counts"][attribute] += 1
        user_data[f"last_{attribute}_training"] = current_time

        await self.config.member(ctx.author).set(user_data)

        await ctx.send(f"You've trained your {attribute}! It increased by {attribute_increase} points. You gained 10 exp.")

        # Check for level up
        await self.check_level_up(ctx, user_data)

    async def check_level_up(self, ctx, user_data):
        required_exp = user_data["level"] * 100
        if user_data["exp"] >= required_exp:
            user_data["level"] += 1
            user_data["exp"] -= required_exp
            await self.config.member(ctx.author).set(user_data)
            await ctx.send(f"Congratulations! You've leveled up to level {user_data['level']}!")

    async def reset_daily_training_counts(self):
        all_members = await self.config.all_members()
        for guild_id, guild_data in all_members.items():
            for user_id, user_data in guild_data.items():
                user_data["training_counts"] = {"strength": 0, "defense": 0, "speed": 0}
                await self.config.member_from_ids(guild_id, user_id).set(user_data)