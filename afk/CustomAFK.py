import discord
from redbot.core import commands, Config
from datetime import datetime
import asyncio
import aiohttp
import re

class CustomAFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=1234567890, force_registration=True
        )
        default_member = {
            "afk": False,
            "reason": None,
            "image_url": None,
            "timestamp": None,
        }
        self.config.register_member(**default_member)

    async def is_valid_image_url(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    return content_type.startswith(("image/", "video/gif"))
        return False

    @commands.command()
    async def afk(self, ctx, *, reason: str = None):
        """Set your AFK status with an optional reason, image, or GIF."""
        image_url = None

        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif reason:
            # Check for URLs in the reason
            urls = re.findall(r'(https?://\S+)', reason)
            for url in urls:
                if await self.is_valid_image_url(url):
                    image_url = url
                    reason = reason.replace(url, '').strip()  # Remove the URL from the reason
                    break

        await self.config.member(ctx.author).afk.set(True)
        await self.config.member(ctx.author).reason.set(reason)
        await self.config.member(ctx.author).image_url.set(image_url)
        await self.config.member(ctx.author).timestamp.set(
            datetime.utcnow().timestamp()
        )

        await ctx.send(
            f"{ctx.author.mention} You are now AFK. I'll notify others when they mention you."
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Check if the author of the message is AFK and remove their AFK status
        is_afk = await self.config.member(message.author).afk()
        if is_afk:
            afk_timestamp = await self.config.member(message.author).timestamp()
            # Ensure some time has passed since setting AFK status
            if (datetime.utcnow().timestamp() - afk_timestamp) > 5:  # 5 seconds grace period
                await self.config.member(message.author).afk.set(False)
                await self.config.member(message.author).reason.set(None)
                await self.config.member(message.author).image_url.set(None)
                await self.config.member(message.author).timestamp.set(None)
                await message.channel.send(
                    f"Welcome back, {message.author.mention}! I've removed your AFK status."
                )

        # Notify others if they mention an AFK user
        for mention in message.mentions:
            data = await self.config.member(mention).all()
            if data["afk"]:
                embed = discord.Embed(
                    title=f"{mention.name} is AFK", color=discord.Color.blue()
                )

                if data["reason"]:
                    embed.add_field(name="Reason", value=data["reason"])

                if data["image_url"]:
                    embed.set_image(url=data["image_url"])
                    embed.add_field(name="Image/GIF URL", value=data["image_url"])

                time_elapsed = datetime.utcnow().timestamp() - data["timestamp"]
                hours, remainder = divmod(int(time_elapsed), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_string = f"{hours}h {minutes}m {seconds}s"
                embed.add_field(name="Time Elapsed", value=time_string)

                reply = await message.reply(embed=embed)

                view = discord.ui.View()
                button = discord.ui.Button(
                    style=discord.ButtonStyle.primary, label="Notify User"
                )

                async def button_callback(interaction):
                    if interaction.user == message.author:
                        dm_embed = discord.Embed(
                            title="AFK Notification",
                            description=f"{message.author.mention} pinged you in {message.channel.mention}",
                            color=discord.Color.blue(),
                        )
                        dm_embed.add_field(name="Message", value=message.content)
                        try:
                            await mention.send(embed=dm_embed)
                            await interaction.response.send_message(
                                "User has been notified.", ephemeral=True
                            )
                        except discord.Forbidden:
                            await interaction.response.send_message(
                                "Unable to send DM to the user.", ephemeral=True
                            )
                    else:
                        await interaction.response.send_message(
                            "Only the person who pinged can use this button.",
                            ephemeral=True,
                        )

                button.callback = button_callback
                view.add_item(button)
                await reply.edit(view=view)

async def setup(bot):
    await bot.add_cog(CustomAFK(bot))
