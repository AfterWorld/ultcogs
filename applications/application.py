import discord
from discord.ext import commands
from discord import app_commands
from typing import List, Optional
import asyncio
import datetime
import json
import os

class Application(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.applications = []
        self.config_file = 'one_piece_config.json'
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'application_channel_id': None,
                'log_channel_id': None,
                'questions': [
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
            self.save_config()

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    @app_commands.command(name="set_application_channel", description="Set the channel for receiving applications")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_application_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.config['application_channel_id'] = channel.id
        self.save_config()
        await interaction.response.send_message(f"Application channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="set_log_channel", description="Set the channel for logging application actions")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        self.config['log_channel_id'] = channel.id
        self.save_config()
        await interaction.response.send_message(f"Log channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="add_question", description="Add a new application question")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_question(self, interaction: discord.Interaction, question: str):
        self.config['questions'].append(question)
        self.save_config()
        await interaction.response.send_message(f"Added question: {question}", ephemeral=True)

    @app_commands.command(name="remove_question", description="Remove an application question")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_question(self, interaction: discord.Interaction, index: int):
        if 0 <= index < len(self.config['questions']):
            removed_question = self.config['questions'].pop(index)
            self.save_config()
            await interaction.response.send_message(f"Removed question: {removed_question}", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid question index", ephemeral=True)

    @app_commands.command(name="apply", description="Apply for a staff position")
    async def apply(self, interaction: discord.Interaction):
        await interaction.response.send_message("Let's start your application! Check your DMs.", ephemeral=True)
        
        answers = []
        for question in self.config['questions']:
            await interaction.user.send(question)
            try:
                answer = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == interaction.user and isinstance(m.channel, discord.DMChannel),
                    timeout=300.0
                )
                answers.append(answer.content)
            except asyncio.TimeoutError:
                await interaction.user.send("You took too long to answer. Please start the application process again.")
                return

        embed = discord.Embed(
            title="New Crew Application!",
            description=f"Application from {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        for question, answer in zip(self.config['questions'], answers):
            embed.add_field(name=question, value=answer, inline=False)

        application_channel = self.bot.get_channel(self.config['application_channel_id'])
        if application_channel:
            await application_channel.send(embed=embed)

        self.applications.append({
            "user": interaction.user,
            "embed": embed,
            "timestamp": datetime.datetime.now()
        })

        await interaction.user.send("Your application has been submitted successfully!")
        await self.log_action(f"New application submitted by {interaction.user}")

    @app_commands.command(name="viewapp", description="View all applications")
    @app_commands.checks.has_permissions(administrator=True)
    async def viewapp(self, interaction: discord.Interaction):
        if not self.applications:
            await interaction.response.send_message("There are no applications to view.", ephemeral=True)
            return

        current_page = 0

        async def update_embed():
            embed = self.applications[current_page]["embed"]
            embed.set_footer(text=f"Application {current_page + 1}/{len(self.applications)}")
            return embed

        class ApplicationView(discord.ui.View):
            def __init__(self, parent):
                super().__init__(timeout=300)
                self.parent = parent

            @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
            async def previous_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal current_page
                current_page = (current_page - 1) % len(self.applications)
                await button_interaction.response.edit_message(embed=await update_embed())

            @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
            async def next_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal current_page
                current_page = (current_page + 1) % len(self.applications)
                await button_interaction.response.edit_message(embed=await update_embed())

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
            async def accept_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await self.parent.accept(button_interaction, self.applications[current_page]["user"])

            @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
            async def deny_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await self.parent.deny(button_interaction, self.applications[current_page]["user"])

        view = ApplicationView(self)
        await interaction.response.send_message(embed=await update_embed(), view=view)

    @app_commands.command(name="accept", description="Accept an application")
    @app_commands.checks.has_permissions(administrator=True)
    async def accept(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        application = next((app for app in self.applications if app["user"] == user), None)
        if not application:
            await interaction.response.send_message(f"No application found for {user.mention}", ephemeral=True)
            return

        await user.add_roles(role)
        await user.send(f"Congratulations! Your application has been accepted. You've been given the {role.name} role.")
        await interaction.response.send_message(f"Accepted {user.mention}'s application and assigned the {role.name} role.", ephemeral=True)

        self.applications = [app for app in self.applications if app["user"] != user]
        await self.log_action(f"Application from {user} accepted by {interaction.user}")

    @app_commands.command(name="deny", description="Deny an application")
    @app_commands.checks.has_permissions(administrator=True)
    async def deny(self, interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = "No reason provided"):
        application = next((app for app in self.applications if app["user"] == user), None)
        if not application:
            await interaction.response.send_message(f"No application found for {user.mention}", ephemeral=True)
            return

        await user.send(f"We're sorry, but your application has been denied. Reason: {reason}")
        await interaction.response.send_message(f"Denied {user.mention}'s application. Reason: {reason}", ephemeral=True)

        self.applications = [app for app in self.applications if app["user"] != user]
        await self.log_action(f"Application from {user} denied by {interaction.user}. Reason: {reason}")

    async def log_action(self, message: str):
        if self.config['log_channel_id']:
            log_channel = self.bot.get_channel(self.config['log_channel_id'])
            if log_channel:
                await log_channel.send(f"[{datetime.datetime.now()}] {message}")

async def setup(bot):
    await bot.add_cog(Application(bot))