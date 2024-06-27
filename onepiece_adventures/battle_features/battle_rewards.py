import random
import discord
from redbot.core import commands


async def end_battle(self, ctx, winner, loser, battle_msg):
    winner_data = self.battles[winner.id]
    loser_data = self.battles[loser.id]

    exp_gain = random.randint(20, 50)
    berry_gain = random.randint(200, 500)
    item_chance = random.random()

    winner_data["exp"] += exp_gain
    winner_data["berries"] += berry_gain
    winner_data["wins"] = winner_data.get("wins", 0) + 1

    embed = discord.Embed(title="Battle Over!", color=discord.Color.green())
    embed.add_field(name="Winner", value=f"{winner.mention} ({winner_data['character_class']})", inline=False)
    embed.add_field(name="Rewards", value=f"EXP: {exp_gain}\nBerries: {berry_gain}", inline=False)

    if item_chance < 0.1:  # 10% chance to get an item
        item = random.choice(["Health Potion", "Stamina Boost", "Smoke Bomb"])
        winner_data["inventory"] = winner_data.get("inventory", {})
        winner_data["inventory"][item] = winner_data["inventory"].get(item, 0) + 1
        embed.add_field(name="Item Reward", value=f"You found a {item}!", inline=False)

    embed.set_footer(text=f"{loser.name} has been defeated!")

    await battle_msg.edit(embed=embed)

    # Update the database with the new values
    await self.config.member(winner).set(winner_data)
    await self.config.member(loser).set(loser_data)

    del self.battles[winner.id]
    del self.battles[loser.id]

    # Check for level up
    if winner_data["exp"] >= winner_data["level"] * 100:
        winner_data["level"] += 1
        winner_data["exp"] -= winner_data["level"] * 100
        await ctx.send(f"🎉 Congratulations {winner.mention}! You've leveled up to level {winner_data['level']}!")
        
        # Stat increase on level up
        stat_increase = random.randint(1, 3)
        stat_to_increase = random.choice(["strength", "defense", "speed"])
        winner_data[stat_to_increase] += stat_increase
        await ctx.send(f"Your {stat_to_increase} has increased by {stat_increase}!")

    await self.config.member(winner).set(winner_data)
