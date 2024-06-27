import discord
from redbot.core import commands, Config
from datetime import datetime
import asyncio


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

    @commands.command()
    async def afk(self, ctx, *, reason: str = None):
        """Set your AFK status with an optional reason or image."""
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        else:
            image_url = None

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
