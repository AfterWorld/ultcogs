import discord # type: ignore
from redbot.core import commands, Config 
import random
import asyncio

class CrewBattleSystem:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    async def create_crew(self, ctx, name: str):
        crews = await self.config.guild(ctx.guild).crews()
        if name in crews:
            await ctx.send("A crew with that name already exists.")
            return

        crews[name] = {
            "captain": ctx.author.id,
            "members": [ctx.author.id],
            "ships": [],
            "reputation": 0
        }
        await self.config.guild(ctx.guild).crews.set(crews)
        await self.config.member(ctx.author).crew.set(name)
        await ctx.send(f"Crew '{name}' has been created with {ctx.author.name} as the captain!")

    async def join_crew(self, ctx, crew_name: str):
        crews = await self.config.guild(ctx.guild).crews()
        if crew_name not in crews:
            await ctx.send("That crew doesn't exist.")
            return

        if await self.config.member(ctx.author).crew():
            await ctx.send("You're already in a crew. Leave your current crew first.")
            return

        crews[crew_name]["members"].append(ctx.author.id)
        await self.config.guild(ctx.guild).crews.set(crews)
        await self.config.member(ctx.author).crew.set(crew_name)
        await ctx.send(f"You have joined the '{crew_name}' crew!")

    async def initiate_crew_battle(self, ctx, opponent_crew: str):
        user_crew = await self.config.member(ctx.author).crew()
        if not user_crew:
            await ctx.send("You're not in a crew.")
            return

        crews = await self.config.guild(ctx.guild).crews()
        if opponent_crew not in crews:
            await ctx.send("The opponent crew doesn't exist.")
            return

        if user_crew == opponent_crew:
            await ctx.send("You can't battle your own crew.")
            return

        # Calculate crew strengths
        user_crew_strength = await self.calculate_crew_strength(ctx.guild, user_crew)
        opponent_crew_strength = await self.calculate_crew_strength(ctx.guild, opponent_crew)

        # Battle logic
        total_strength = user_crew_strength + opponent_crew_strength
        user_crew_chance = user_crew_strength / total_strength

        if random.random() < user_crew_chance:
            winner = user_crew
            loser = opponent_crew
        else:
            winner = opponent_crew
            loser = user_crew

        # Update reputations
        crews[winner]["reputation"] += 10
        crews[loser]["reputation"] = max(0, crews[loser]["reputation"] - 5)

        await self.config.guild(ctx.guild).crews.set(crews)

        await ctx.send(f"The {winner} crew has defeated the {loser} crew in an epic battle!")

    async def calculate_crew_strength(self, guild, crew_name):
        crews = await self.config.guild(guild).crews()
        crew = crews[crew_name]
        
        total_strength = 0
        for member_id in crew["members"]:
            member_data = await self.config.member_from_ids(guild.id, member_id).all()
            total_strength += (member_data["strength"] + member_data["defense"] + member_data["speed"]) * (1 + member_data["haki_level"] * 0.1)

        # Factor in ships and other bonuses
        ship_bonus = len(crew["ships"]) * 50
        total_strength += ship_bonus

        return total_strength

    async def recruit_crew_member(self, ctx, member: discord.Member):
        user_data = await self.config.member(ctx.author).all()
        if not user_data['crew']:
            return await ctx.send("You need to be in a crew to recruit members.")
        
        crews = await self.config.guild(ctx.guild).crews()
        if len(crews[user_data['crew']]['members']) >= 10:
            return await ctx.send("Your crew is already at maximum capacity (10 members).")
        
        await ctx.send(f"{member.mention}, {ctx.author.name} is inviting you to join their crew. Do you accept? (yes/no)")
        
        def check(m):
            return m.author == member and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            return await ctx.send("The invitation has timed out.")
        
        if msg.content.lower() == 'yes':
            crews[user_data['crew']]['members'].append(member.id)
            await self.config.guild(ctx.guild).crews.set(crews)
            await self.config.member(member).crew.set(user_data['crew'])
            await ctx.send(f"{member.name} has joined {user_data['crew']}!")
        else:
            await ctx.send("The invitation was declined.")

    async def crew_info(self, ctx, crew_name: str = None):
        if crew_name is None:
            user_data = await self.config.member(ctx.author).all()
            crew_name = user_data['crew']
            if not crew_name:
                return await ctx.send("You're not in a crew. Specify a crew name or join one first.")
        
        crews = await self.config.guild(ctx.guild).crews()
        if crew_name not in crews:
            return await ctx.send("That crew doesn't exist.")
        
        crew = crews[crew_name]
        embed = discord.Embed(title=f"Crew Info: {crew_name}", color=discord.Color.gold())
        captain = self.bot.get_user(crew['captain'])
        embed.add_field(name="Captain", value=captain.name if captain else "Unknown")
        embed.add_field(name="Members", value=len(crew['members']))
        embed.add_field(name="Ships", value=len(crew['ships']))
        embed.add_field(name="Reputation", value=crew['reputation'])
        
        await ctx.send(embed=embed)