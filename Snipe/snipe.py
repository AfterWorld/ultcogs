import discord
from discord.ext import commands
from redbot.core import commands as red_commands

class SnipeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.deleted_messages = []

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        if len(self.deleted_messages) >= 10:
            self.deleted_messages.pop(0)

        self.deleted_messages.append(message)

    @red_commands.command()
    async def snipe(self, ctx):
        if not self.deleted_messages:
            await ctx.send("No recently deleted messages found.")
            return

        embed = discord.Embed(title="Recently Deleted Messages", color=discord.Color.blue())

        for i, message in enumerate(self.deleted_messages[::-1], start=1):
            content = message.content
            attachments = [attachment.url for attachment in message.attachments]

            if content:
                embed.add_field(name=f"Message {i}", value=content, inline=False)
            if attachments:
                embed.add_field(name=f"Attachments {i}", value="\n".join(attachments), inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(SnipeCog(bot))
