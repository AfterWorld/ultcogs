from redbot.core import commands, Config
import discord
from discord import app_commands
from typing import List, Optional
import asyncio
import datetime

class Application(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_guild = {
            "application_channel_id": None,
            "log_channel_id": None,
            "questions": [
                "What position in the crew are you applying for? (e.g., Navigator, Cook, Doctor)",
                "What's your pirate name?",
                "What's your age?",
                "What's your favorite One Piece arc and why?",
                "How many hours per week can you dedicate to moderating the server?",
                "Do you have any previous experience as a moderator or in a leadership role?",
                "If you were a Devil Fruit user, what power would you have and how would you use it to help the crew?",
                "Why do you want to join our crew as a staff member?"
            ]
        }
        self.config.register_guild(**default_guild)
        self.applications = {}

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def set_application_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for receiving applications"""
        await self.config.guild(ctx.guild).application_channel_id.set(channel.id)
        await ctx.send(f"Application channel set to {channel.mention}")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for logging application actions"""
        await self.config.guild(ctx.guild).log_channel_id.set(channel.id)
        await ctx.send(f"Log channel set to {channel.mention}")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def add_question(self, ctx, *, question: str):
        """Add a new application question"""
        async with self.config.guild(ctx.guild).questions() as questions:
            questions.append(question)
        await ctx.send(f"Added question: {question}")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def remove_question(self, ctx, index: int):
        """Remove an application question"""
        async with self.config.guild(ctx.guild).questions() as questions:
            if 0 <= index < len(questions):
                removed_question = questions.pop(index)
                await ctx.send(f"Removed question: {removed_question}")
            else:
                await ctx.send("Invalid question index")

    @commands.command()
    async def apply(self, ctx):
        """Apply for a staff position"""
        await ctx.send("Let's start your application! Check your DMs.")
        
        questions = await self.config.guild(ctx.guild).questions()
        answers = []
        for question in questions:
            await ctx.author.send(question)
            try:
                answer = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel),
                    timeout=300.0
                )
                answers.append(answer.content)
            except asyncio.TimeoutError:
                await ctx.author.send("You took too long to answer. Please start the application process again.")
                return

        embed = discord.Embed(
            title="New Crew Application!",
            description=f"Application from {ctx.author.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        for question, answer in zip(questions, answers):
            embed.add_field(name=question, value=answer, inline=False)

        application_channel_id = await self.config.guild(ctx.guild).application_channel_id()
        if application_channel_id:
            application_channel = self.bot.get_channel(application_channel_id)
            if application_channel:
                await application_channel.send(embed=embed)

        if ctx.guild.id not in self.applications:
            self.applications[ctx.guild.id] = []
        self.applications[ctx.guild.id].append({
            "user": ctx.author,
            "embed": embed,
            "timestamp": datetime.datetime.now()
        })

        await ctx.author.send("Your application has been submitted successfully!")
        await self.log_action(ctx.guild, f"New application submitted by {ctx.author}")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def viewapp(self, ctx):
        """View all applications"""
        if ctx.guild.id not in self.applications or not self.applications[ctx.guild.id]:
            await ctx.send("There are no applications to view.")
            return

        current_page = 0

        async def update_embed():
            embed = self.applications[ctx.guild.id][current_page]["embed"]
            embed.set_footer(text=f"Application {current_page + 1}/{len(self.applications[ctx.guild.id])}")
            return embed

        message = await ctx.send(embed=await update_embed())
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️", "✅", "❌"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

                if str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % len(self.applications[ctx.guild.id])
                elif str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % len(self.applications[ctx.guild.id])
                elif str(reaction.emoji) == "✅":
                    await self.accept(ctx, self.applications[ctx.guild.id][current_page]["user"])
                    break
                elif str(reaction.emoji) == "❌":
                    await self.deny(ctx, self.applications[ctx.guild.id][current_page]["user"])
                    break

                await message.edit(embed=await update_embed())
                await message.remove_reaction(reaction, user)

            except asyncio.TimeoutError:
                break

        await message.clear_reactions()

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def accept(self, ctx, user: discord.Member, *, role: discord.Role):
        """Accept an application"""
        if ctx.guild.id not in self.applications:
            await ctx.send("There are no applications for this guild.")
            return

        application = next((app for app in self.applications[ctx.guild.id] if app["user"] == user), None)
        if not application:
            await ctx.send(f"No application found for {user.mention}")
            return

        await user.add_roles(role)
        await user.send(f"Congratulations! Your application has been accepted. You've been given the {role.name} role.")
        await ctx.send(f"Accepted {user.mention}'s application and assigned the {role.name} role.")

        self.applications[ctx.guild.id] = [app for app in self.applications[ctx.guild.id] if app["user"] != user]
        await self.log_action(ctx.guild, f"Application from {user} accepted by {ctx.author}")

    @commands.admin_or_permissions(administrator=True)
    @commands.command()
    async def deny(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Deny an application"""
        if ctx.guild.id not in self.applications:
            await ctx.send("There are no applications for this guild.")
            return

        application = next((app for app in self.applications[ctx.guild.id] if app["user"] == user), None)
        if not application:
            await ctx.send(f"No application found for {user.mention}")
            return

        await user.send(f"We're sorry, but your application has been denied. Reason: {reason}")
        await ctx.send(f"Denied {user.mention}'s application. Reason: {reason}")

        self.applications[ctx.guild.id] = [app for app in self.applications[ctx.guild.id] if app["user"] != user]
        await self.log_action(ctx.guild, f"Application from {user} denied by {ctx.author}. Reason: {reason}")

    async def log_action(self, guild, message: str):
        log_channel_id = await self.config.guild(guild).log_channel_id()
        if log_channel_id:
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(f"[{datetime.datetime.now()}] {message}")

async def setup(bot):
    await bot.add_cog(Application(bot))
