import discord
from redbot.core import commands
import asyncio

class UltPrivates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        content = message.content.lower()

        if "skadoosh" in content:
            await self.skadoosh(message)
        elif "i have arrived" in content:
            await self.grand_entrance(message)

    async def skadoosh(self, message):
        """Delete recent messages and play a gif."""
        # Delete the triggering message
        await message.delete()

        # Delete the last 5 messages from the user
        def is_user(m):
            return m.author == message.author

        await message.channel.purge(limit=5, check=is_user)

        # Send the GIF
        gif_url = "https://media.giphy.com/media/S36fZu0PmDqMSVxXxH/giphy.gif"  # Replace with your chosen GIF
        await message.channel.send(gif_url)

    async def grand_entrance(self, message):
        """Make a grand entrance as a top Gorosei."""
        # Delete the triggering message
        await message.delete()

        entrance_messages = [
            "🌟 Silence, mortals! A Top Gorosei has graced this chat with their presence! 🌟",
            "⚡️ Tremble, for the wisdom of the ages has entered the server! ⚡️",
            "🌪 The winds of change blow as a Top Gorosei steps into our midst! 🌪",
            "🔥 Behold! The very foundation of the World Government now walks among us! 🔥",
            "🌊 As the tides are governed by the moon, so too is this server now under the watchful eye of a Top Gorosei! 🌊"
        ]

        embed = discord.Embed(
            title="👑 A Top Gorosei Has Arrived! 👑",
            description=entrance_messages[0],
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="All hail the wisdom of the ages!")

        entrance_msg = await message.channel.send(embed=embed)

        # Cycle through entrance messages
        for msg in entrance_messages[1:]:
            await asyncio.sleep(2)
            embed.description = msg
            await entrance_msg.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(UltPrivates(bot))
