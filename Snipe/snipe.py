import discord
from redbot.core import commands, Config
from datetime import datetime
import aiohttp

class Snipe(commands.Cog):
    """A cog to snipe deleted messages, including attachments."""
    
    def __init__(self, bot):
        self.bot = bot
        print("Initializing Snipe cog...")  # Debug print statement
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

        attachments = []
        for attachment in message.attachments:
            attachments.append({
                "url": attachment.proxy_url,
                "filename": attachment.filename,
                "content_type": attachment.content_type
            })

        deleted_messages.append({
            "author": message.author.id,
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "attachments": attachments,
            "embeds": [embed.to_dict() for embed in message.embeds]
        })

        await self.config.guild(message.guild).deleted_messages.set(deleted_messages)

    @commands.command()
    async def snipe(self, ctx, index: int = 1):
        """Show recently deleted messages, including attachments."""
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
        embeds = message_data["embeds"]
    
        embed = discord.Embed(
            title="🏴‍☠️ Recovered Sunken Treasure (Deleted Message) 🏴‍☠️",
            description=content,
            color=discord.Color.dark_gold(),
            timestamp=timestamp
        )
        embed.set_author(name=f"Message from {author.name}#{author.discriminator}", icon_url=author.display_avatar.url)
        embed.set_footer(text=f"Message sniped by {ctx.author.name}#{ctx.author.discriminator}")
    
        if attachments:
            attachment_info = []
            for attachment in attachments:
                attachment_info.append(f"[{attachment['filename']}]({attachment['url']})")
            embed.add_field(name="Attachments", value="\n".join(attachment_info), inline=False)
    
        await ctx.send(embed=embed)
        
        # Send attachments separately
        for attachment in attachments:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment['url']) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            file = discord.File(fp=data, filename=attachment['filename'])
                            await ctx.send(file=file)
                        else:
                            await ctx.send(f"Attachment {attachment['filename']} could not be retrieved.")
            except Exception as e:
                await ctx.send(f"Error retrieving attachment {attachment['filename']}: {str(e)}")
    
        # Recreate and send additional embeds
        for embed_data in embeds:
            recreated_embed = discord.Embed.from_dict(embed_data)
            await ctx.send(embed=recreated_embed)

def setup(bot):
    bot.add_cog(Snipe(bot))
    print("Loading Snipe cog...")  # Debug print statement
