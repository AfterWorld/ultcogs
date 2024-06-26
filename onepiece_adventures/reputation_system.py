import discord 
from redbot.core import commands, Config 

class ReputationSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def increase_reputation(self, ctx, faction: str, amount: int):
        user_data = await self.config.member(ctx.author).all()
        if faction not in user_data["reputation"]:
            await ctx.send("Invalid faction.")
            return

        user_data["reputation"][faction] += amount
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"Your reputation with the {faction} faction has increased by {amount}!")

    async def decrease_reputation(self, ctx, faction: str, amount: int):
        user_data = await self.config.member(ctx.author).all()
        if faction not in user_data["reputation"]:
            await ctx.send("Invalid faction.")
            return

        user_data["reputation"][faction] = max(0, user_data["reputation"][faction] - amount)
        await self.config.member(ctx.author).set(user_data)
        await ctx.send(f"Your reputation with the {faction} faction has decreased by {amount}.")

    async def view_reputation(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        embed = discord.Embed(title=f"{ctx.author.name}'s Reputation", color=discord.Color.blue())
        for faction, rep in user_data["reputation"].items():
            embed.add_field(name=faction.capitalize(), value=rep, inline=True)
        await ctx.send(embed=embed)

    async def reputation_rewards(self, ctx):
        user_data = await self.config.member(ctx.author).all()
        rewards = {
            "pirate": {
                100: "Access to advanced pirate quests",
                500: "Ability to recruit more crew members",
                1000: "Chance to find rare Devil Fruits"
            },
            "marine": {
                100: "Access to Marine-only islands",
                500: "Ability to commandeer civilian ships",
                1000: "Chance to receive Seastone weapons"
            },
            "revolutionary": {
                100: "Access to secret Revolutionary Army bases",
                500: "Ability to incite island rebellions",
                1000: "Chance to learn advanced Haki techniques"
            }
        }

        embed = discord.Embed(title="Reputation Rewards", color=discord.Color.gold())
        for faction, rep in user_data["reputation"].items():
            unlocked_rewards = [desc for level, desc in rewards[faction].items() if rep >= level]
            if unlocked_rewards:
                embed.add_field(name=f"{faction.capitalize()} Rewards", value="\n".join(unlocked_rewards), inline=False)
            else:
                embed.add_field(name=f"{faction.capitalize()} Rewards", value="No rewards unlocked yet", inline=False)

        await ctx.send(embed=embed)