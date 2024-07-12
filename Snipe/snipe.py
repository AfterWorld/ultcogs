import discord
from redbot.core import commands, Config
from datetime import datetime

class Snipe(commands.Cog):
    """A cog to snipe deleted messages."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        default_guild = {
            "deleted_messages": []
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        deleted_messages = await self.config.guild(message.guild).deleted_messages()
        if len(deleted_messages) >= 10:
            deleted_messages.pop(0)

        deleted_messages.append({
            "author": message.author.id,
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "attachments": [attachment.url for attachment in message.attachments]
        })

        await self.config.guild(message.guild).deleted_messages.set(deleted_messages)

    @commands.command()
    async def snipe(self, ctx, index: int = 1):
        """Show recently deleted messages."""
        deleted_messages = await self.config.guild(ctx.guild).deleted_messages()

        if not deleted_messages:
            return await ctx.send("No recently deleted messages found, ye scurvy dog!")

        if index < 1 or index > len(deleted_messages):
            return await ctx.send(f"Invalid index. Must be between 1 and {len(deleted_messages)}, ye landlubber!")

        message_data = deleted_messages[-index]
        author = ctx.guild.get_member(message_data["author"])
        content = message_data["content"]
        timestamp = datetime.fromisoformat(message_data["timestamp"])
        attachments = message_data["attachments"]

        embed = discord.Embed(
            title="🏴‍☠️ Recovered Sunken Treasure (Deleted Message) 🏴‍☠️",
            description=content,
            color=discord.Color.dark_gold(),
            timestamp=timestamp
        )
        embed.set_author(name=f"Message from {author.name}#{author.discriminator}", icon_url=author.avatar_url)
        embed.set_footer(text=f"Message sniped by {ctx.author.name}#{ctx.author.discriminator}")

        if attachments:
            embed.add_field(name="Attachments", value="\n".join(attachments), inline=False)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Snipe(bot))
