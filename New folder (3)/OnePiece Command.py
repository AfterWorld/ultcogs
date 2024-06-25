import discord
from redbot.core import commands, Config
from datetime import datetime
import asyncio
import random


class OnePieceAFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=1234567890, force_registration=True
        )
        default_member = {
            "on_adventure": False,
            "log_pose": None,
            "jolly_roger": None,
            "departure_time": None,
        }
        self.config.register_member(**default_member)

        self.quotes = [
            "I'm going to be King of the Pirates! - Monkey D. Luffy",
            "When do you think people die? When they are shot through the heart? No. When they are ravaged by an incurable disease? No. When they drink a soup made from a poisonous mushroom? No! It's when... they are forgotten. - Dr. Hiluluk",
            "Only I can call my dream stupid! - Roronoa Zoro",
            "Fools who don't respect the past are likely to repeat it. - Nico Robin",
            "When the world shoves you around, you just gotta stand up and shove back. It's not like somebody's gonna save you if you start babbling excuses. - Sanji",
            "There comes a time when a man has to stand and fight! - Usopp",
            "If you don't take risks, you can't create a future! - Monkey D. Luffy",
            "Justice will prevail, you say? But of course it will! Whoever wins this war becomes justice! - Donquixote Doflamingo",
            "Inherited Will, The Destiny of the Age, and The Dreams of the People. As long as people continue to pursue the meaning of Freedom, these things will never cease to be! - Gol D. Roger",
            "The world's too big to stay in one place. - Nami",
        ]

    @commands.command(name="setadventure", aliases=["sa"])
    async def set_adventure(self, ctx, *, log_pose: str = "Unknown seas"):
        """Set your adventure status with an optional destination."""
        if ctx.message.attachments:
            jolly_roger = ctx.message.attachments[0].url
        else:
            jolly_roger = None

        await self.config.member(ctx.author).on_adventure.set(True)
        await self.config.member(ctx.author).log_pose.set(log_pose)
        await self.config.member(ctx.author).jolly_roger.set(jolly_roger)
        await self.config.member(ctx.author).departure_time.set(
            datetime.utcnow().timestamp()
        )

        await ctx.send(
            f"{ctx.author.mention} has set sail on a grand adventure! Their log pose is set to: {log_pose}"
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        for mention in message.mentions:
            data = await self.config.member(mention).all()
            if data["on_adventure"]:
                embed = discord.Embed(
                    title=f"{mention.name} is on a Grand Adventure!",
                    color=discord.Color.blue(),
                )

                if data["log_pose"]:
                    embed.add_field(name="Log Pose Set To", value=data["log_pose"])

                if data["jolly_roger"]:
                    embed.set_thumbnail(url=data["jolly_roger"])

                time_elapsed = datetime.utcnow().timestamp() - data["departure_time"]
                days, remainder = divmod(int(time_elapsed), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_string = f"{days}d {hours}h {minutes}m {seconds}s"
                embed.add_field(name="Time at Sea", value=time_string)

                embed.set_footer(text=random.choice(self.quotes))

                reply = await message.reply(embed=embed)

                view = discord.ui.View()
                button = discord.ui.Button(
                    style=discord.ButtonStyle.primary, label="Send News Coo"
                )

                async def button_callback(interaction):
                    if interaction.user == message.author:
                        dm_embed = discord.Embed(
                            title="News Coo Special Delivery!",
                            description=f"{message.author.mention} sent a message via News Coo in {message.channel.mention}",
                            color=discord.Color.blue(),
                        )
                        dm_embed.add_field(name="Message", value=message.content)
                        dm_embed.set_footer(text="The News Coo always delivers!")
                        try:
                            await mention.send(embed=dm_embed)
                            await interaction.response.send_message(
                                "News Coo has delivered your message!", ephemeral=True
                            )
                        except discord.Forbidden:
                            await interaction.response.send_message(
                                "The News Coo couldn't reach the pirate.",
                                ephemeral=True,
                            )
                    else:
                        await interaction.response.send_message(
                            "Only the person who called out can send a News Coo.",
                            ephemeral=True,
                        )

                button.callback = button_callback
                view.add_item(button)
                await reply.edit(view=view)

        if message.author.id in [member.id for member in message.mentions]:
            data = await self.config.member(message.author).all()
            if data["on_adventure"]:
                await self.config.member(message.author).on_adventure.set(False)
                await self.config.member(message.author).log_pose.set(None)
                await self.config.member(message.author).jolly_roger.set(None)
                await self.config.member(message.author).departure_time.set(None)
                await message.channel.send(
                    f"Welcome back to port, {message.author.mention}! How was your adventure?"
                )


async def setup(bot):
    await bot.add_cog(OPAFK(bot))
