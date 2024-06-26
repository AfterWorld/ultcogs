import discord # type: ignore
from redbot.core import commands, Config # type: ignore
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
            "bounty": 0,
            "crew": None,
            "devil_fruit": None,
            "last_bounty_update": 0,
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

        self.devil_fruits = [
            "Gomu Gomu no Mi",
            "Mera Mera no Mi",
            "Hito Hito no Mi",
            "Yami Yami no Mi",
            "Gura Gura no Mi",
            "Ope Ope no Mi",
            "Mochi Mochi no Mi",
            "Hana Hana no Mi",
            "Goro Goro no Mi",
            "Suna Suna no Mi",
            "Moku Moku no Mi",
            "Bara Bara no Mi",
        ]

        self.bounty_thresholds = [
            (1000000000, "Yonko"),
            (500000000, "Emperor Commander"),
            (300000000, "Supernova"),
            (100000000, "Super Rookie"),
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

    @commands.command(name="setcrew")
    async def set_crew(self, ctx, *, crew_name: str):
        """Set your pirate crew name."""
        await self.config.member(ctx.author).crew.set(crew_name)
        await ctx.send(
            f"{ctx.author.mention} is now a proud member of the {crew_name}!"
        )

    @commands.command(name="eatdevilfruit")
    async def eat_devil_fruit(self, ctx):
        """Eat a random Devil Fruit."""
        current_fruit = await self.config.member(ctx.author).devil_fruit()
        if current_fruit:
            await ctx.send(
                f"{ctx.author.mention}, you've already eaten the {current_fruit}! You can't eat another Devil Fruit!"
            )
        else:
            new_fruit = random.choice(self.devil_fruits)
            await self.config.member(ctx.author).devil_fruit.set(new_fruit)
            await ctx.send(
                f"{ctx.author.mention} has eaten the {new_fruit}! What new powers will they discover?"
            )

    @commands.command(name="updatebounty")
    async def update_bounty(self, ctx):
        """Request a bounty update from the World Government."""
        last_update = await self.config.member(ctx.author).last_bounty_update()
        current_time = datetime.utcnow().timestamp()

        if current_time - last_update < 86400:
            time_left = 86400 - (current_time - last_update)
            hours, remainder = divmod(int(time_left), 3600)
            minutes, _ = divmod(remainder, 60)
            await ctx.send(
                f"The World Government is still assessing your threat level. Try again in {hours} hours and {minutes} minutes."
            )
            return

        old_bounty = await self.config.member(ctx.author).bounty()

        if old_bounty == 0:
            new_bounty = random.randint(10000000, 99000000)
        else:
            increase = random.uniform(1.1, 2.0)
            new_bounty = int(old_bounty * increase)

        await self.config.member(ctx.author).bounty.set(new_bounty)
        await self.config.member(ctx.author).last_bounty_update.set(current_time)

        embed = discord.Embed(title="Bounty Update", color=discord.Color.red())
        embed.set_thumbnail(url=ctx.author.avatar.url)
        embed.add_field(name="Pirate", value=ctx.author.mention, inline=False)
        embed.add_field(name="New Bounty", value=f"{new_bounty:,} Belly", inline=False)
        if old_bounty > 0:
            embed.add_field(
                name="Previous Bounty", value=f"{old_bounty:,} Belly", inline=False
            )

        for threshold, title in self.bounty_thresholds:
            if new_bounty >= threshold and old_bounty < threshold:
                embed.add_field(name="New Title", value=title, inline=False)
                break

        await ctx.send(embed=embed)

        if new_bounty >= 1000000000:
            most_wanted_embed = discord.Embed(
                title="⚠️ MOST WANTED ALERT ⚠️", color=discord.Color.dark_red()
            )
            most_wanted_embed.set_thumbnail(url=ctx.author.avatar.url)
            most_wanted_embed.add_field(
                name="Dangerous Pirate", value=ctx.author.mention, inline=False
            )
            most_wanted_embed.add_field(
                name="Bounty", value=f"{new_bounty:,} Belly", inline=False
            )
            most_wanted_embed.set_footer(
                text="The World Government has deemed this pirate extremely dangerous!"
            )

            for channel in ctx.guild.text_channels:
                try:
                    await channel.send(embed=most_wanted_embed)
                except discord.Forbidden:
                    pass

    @commands.command(name="wanted")
    async def show_wanted_poster(self, ctx, member: discord.Member = None):
        """Display a wanted poster for yourself or another member."""
        if member is None:
            member = ctx.author

        data = await self.config.member(member).all()
        bounty = data["bounty"]
        crew = data["crew"]
        devil_fruit = data["devil_fruit"]

        embed = discord.Embed(
            title=f"WANTED: {member.name}", color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(name="Bounty", value=f"{bounty:,} Belly")
        if crew:
            embed.add_field(name="Crew", value=crew)
        if devil_fruit:
            embed.add_field(name="Devil Fruit", value=devil_fruit)
        embed.set_footer(text="DEAD OR ALIVE")

        await ctx.send(embed=embed)

    @commands.command(name="topbounties")
    async def show_top_bounties(self, ctx):
        """Display the top 10 bounties in the server."""
        all_members = await self.config.all_members(ctx.guild)
        sorted_bounties = sorted(
            all_members.items(), key=lambda x: x[1]["bounty"], reverse=True
        )[:10]

        embed = discord.Embed(
            title="Top 10 Most Wanted Pirates", color=discord.Color.gold()
        )
        for i, (member_id, data) in enumerate(sorted_bounties, 1):
            member = ctx.guild.get_member(member_id)
            if member and data["bounty"] > 0:
                embed.add_field(
                    name=f"{i}. {member.name}",
                    value=f"{data['bounty']:,} Belly",
                    inline=False,
                )

        await ctx.send(embed=embed)

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

                if data["crew"]:
                    embed.add_field(name="Crew", value=data["crew"])
                if data["bounty"]:
                    embed.add_field(name="Bounty", value=f"{data['bounty']:,} Belly")
                if data["devil_fruit"]:
                    embed.add_field(name="Devil Fruit", value=data["devil_fruit"])

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

        if random.random() < 0.01:
            member = message.author
            data = await self.config.member(member).all()
            if data["bounty"] > 0:
                increase = random.uniform(1.05, 1.2)
                new_bounty = int(data["bounty"] * increase)
                old_bounty = data["bounty"]
                await self.config.member(member).bounty.set(new_bounty)

                embed = discord.Embed(
                    title="Sudden Bounty Increase!", color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar.url)
                embed.add_field(name="Pirate", value=member.mention, inline=False)
                embed.add_field(
                    name="New Bounty", value=f"{new_bounty:,} Belly", inline=False
                )
                embed.add_field(
                    name="Previous Bounty", value=f"{old_bounty:,} Belly", inline=False
                )

                for threshold, title in self.bounty_thresholds:
                    if new_bounty >= threshold and old_bounty < threshold:
                        embed.add_field(name="New Title", value=title, inline=False)
                        break

                await message.channel.send(embed=embed)

                if new_bounty >= 1000000000 and old_bounty < 1000000000:
                    most_wanted_embed = discord.Embed(
                        title="⚠️ MOST WANTED ALERT ⚠️", color=discord.Color.dark_red()
                    )
                    most_wanted_embed.set_thumbnail(url=member.avatar.url)
                    most_wanted_embed.add_field(
                        name="Dangerous Pirate", value=member.mention, inline=False
                    )
                    most_wanted_embed.add_field(
                        name="Bounty", value=f"{new_bounty:,} Belly", inline=False
                    )
                    most_wanted_embed.set_footer(
                        text="The World Government has deemed this pirate extremely dangerous!"
                    )

                    for channel in message.guild.text_channels:
                        try:
                            await channel.send(embed=most_wanted_embed)
                        except discord.Forbidden:
                            pass


async def setup(bot):
    await bot.add_cog(OnePieceAFK(bot))
