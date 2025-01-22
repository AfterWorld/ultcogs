from redbot.core import commands, Config
import discord
import random
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps
import aiohttp
import io
import os

class BountyCog(commands.Cog):
    """A cog for managing bounties."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_member = {"last_daily_claim": None, "bounty": 0}
        default_guild = {"bounties": {}}
        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)

    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey with a low-level bounty."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id in bounties:
            return await ctx.send("Ye already have a bounty, ye scallywag!")

        bounties[user_id] = {"amount": random.randint(50, 100)}
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])
        await ctx.send(f"🏴‍☠️ Ahoy, {user.display_name}! Ye have started yer bounty journey with {bounties[user_id]['amount']} Berries!")

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase!"""
        user = ctx.author
        last_claim = await self.config.member(user).last_daily_claim()
        now = datetime.utcnow()

        if last_claim:
            last_claim = datetime.fromisoformat(last_claim)
            if now - last_claim < timedelta(days=1):
                time_left = timedelta(days=1) - (now - last_claim)
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Come back in {hours} hours and {minutes} minutes, ye greedy sea dog!")

        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        increase = random.randint(1000, 5000)
        
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.config.member(user).last_daily_claim.set(None)
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            bounties[user_id]["amount"] += increase
            await self.config.guild(ctx.guild).bounties.set(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            await ctx.send(f"💰 Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                           f"Current Title: {new_title}")

            # Announce if the user reaches a significant rank
            if new_bounty >= 900000000:
                await self.announce_rank(ctx.guild, user, new_title)
        else:
            await self.config.member(user).last_daily_claim.set(None)
            await ctx.send("Ye decided not to open the chest. The Sea Kings must've scared ye off!")

    @commands.command()
    async def wanted(self, ctx):
        """Display a wanted poster with the user's avatar, username, and bounty."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        bounty_amount = await self.config.member(user).bounty()
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status != 200:
                    return await ctx.send("Failed to retrieve avatar.")
                avatar_data = await response.read()

        wanted_poster = await self.create_wanted_poster(user.display_name, bounty_amount, avatar_data)
        if isinstance(wanted_poster, str):
            return await ctx.send(wanted_poster)
        await ctx.send(file=discord.File(wanted_poster, "wanted.png"))

    async def create_wanted_poster(self, username, bounty_amount, avatar_data):
        """Create a wanted poster with the user's avatar, username, and bounty."""
        wanted_poster_url = "https://raw.githubusercontent.com/AfterWorld/ultcogs/refs/heads/main/bounty/wanted.png"
        font_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyCog/fonts/onepiece.ttf"

        async with aiohttp.ClientSession() as session:
            async with session.get(wanted_poster_url) as response:
                if response.status != 200:
                    raise Exception("Failed to retrieve wanted poster template.")
                poster_data = await response.read()

        poster_image = Image.open(io.BytesIO(poster_data))
        avatar_image = Image.open(io.BytesIO(avatar_data)).resize((625, 455))

        # Round the avatar corners
        avatar_image = self.round_image_corners(avatar_image)

        # Ensure avatar image is in RGBA mode
        avatar_image = avatar_image.convert("RGBA")

        draw = ImageDraw.Draw(poster_image)
        try:
            font = ImageFont.truetype(font_path, 100)
        except OSError:
            return "Failed to load font. Please ensure the font file exists and is accessible."

        poster_image.paste(avatar_image, (65, 223), avatar_image)

        draw.text((150, 750), username, font=font, fill="black")
        draw.text((150, 870), f"{bounty_amount:,}", font=font, fill="black")

        output = io.BytesIO()
        poster_image.save(output, format="PNG")
        output.seek(0)

        return output

    def round_image_corners(self, image):
        """Round the corners of an image."""
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0) + image.size, radius=50, fill=255)
        rounded_image = ImageOps.fit(image, mask.size, centering=(0.5, 0.5))
        rounded_image.putalpha(mask)
        return rounded_image

    async def announce_rank(self, guild, user, title):
        """Announce when a user reaches a significant rank."""
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎉 Congratulations to {user.mention} for reaching the rank of **{title}** with a bounty of {user.display_name}'s bounty!")

    def get_bounty_title(self, bounty_amount):
        """Get the bounty title based on the bounty amount."""
        titles = [
            (50000000, "Rookie Pirate"),
            (100000000, "Super Rookie"),
            (200000000, "Notorious Pirate"),
            (300000000, "Supernova"),
            (400000000, "Rising Star"),
            (500000000, "Infamous Pirate"),
            (600000000, "Feared Pirate"),
            (700000000, "Pirate Captain"),
            (800000000, "Pirate Lord"),
            (900000000, "Pirate Emperor"),
            (1000000000, "Yonko"),
            (1500000000, "Pirate King Candidate"),
            (2000000000, "King of the Pirates")
        ]
        for amount, title in reversed(titles):
            if bounty_amount >= amount:
                return title
        return "Unknown Pirate"

    @commands.command()
    @commands.cooldown(1, 3600, commands.BucketType.user)
    async def berryflip(self, ctx, bet: int):
        """Flip a coin to potentially increase your bounty."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        current_bounty = bounties[user_id]["amount"]

        if bet < 500 or bet > 5000:
            return await ctx.send("Ye can only bet between 500 and 5000 Berries, ye scallywag!")

        if bet > current_bounty:
            return await ctx.send("Ye can't bet more than yer current bounty, ye scallywag!")

        flip_result = random.choice(["heads", "tails"])

        if flip_result == "heads":
            bounties[user_id]["amount"] += bet
            await ctx.send(f"🪙 The coin landed on heads! Ye won {bet:,} Berries! Yer new bounty is {bounties[user_id]['amount']:,} Berries!")
        else:
            bounties[user_id]["amount"] -= bet
            await ctx.send(f"🪙 The coin landed on tails! Ye lost {bet:,} Berries! Yer new bounty is {bounties[user_id]['amount']:,} Berries!")

        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])

        new_bounty = bounties[user_id]["amount"]
        new_title = self.get_bounty_title(new_bounty)

        # Announce if the user reaches a significant rank
        if new_bounty >= 900000000:
            await self.announce_rank(ctx.guild, user, new_title)

    @commands.command()
    async def mostwanted(self, ctx):
        """Display the top 10 users with the highest bounties."""
        bounties = await self.config.guild(ctx.guild).bounties()
        sorted_bounties = sorted(bounties.items(), key=lambda x: x[1]["amount"], reverse=True)
        top_bounties = sorted_bounties[:10]

        embed = discord.Embed(title="🏆 Bounty Leaderboard 🏆", color=discord.Color.gold())
        for i, (user_id, bounty) in enumerate(top_bounties, start=1):
            user = self.bot.get_user(int(user_id))
            embed.add_field(name=f"{i}. {user.display_name}", value=f"{bounty['amount']:,} Berries", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def missions(self, ctx):
        """Display available missions."""
        missions = [
            {"description": "Answer a trivia question", "reward": random.randint(500, 2000)},
            {"description": "Share a fun fact", "reward": random.randint(500, 2000)},
            {"description": "Post a meme", "reward": random.randint(500, 2000)},
        ]
        embed = discord.Embed(title="Available Missions", color=discord.Color.green())
        for i, mission in enumerate(missions, start=1):
            embed.add_field(name=f"Mission {i}", value=f"{mission['description']} - Reward: {mission['reward']} Berries", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def completemission(self, ctx, mission_number: int):
        """Complete a mission to earn bounty."""
        missions = [
            {"description": "Answer a trivia question", "reward": random.randint(500, 2000)},
            {"description": "Share a fun fact", "reward": random.randint(500, 2000)},
            {"description": "Post a meme", "reward": random.randint(500, 2000)},
        ]
        if mission_number < 1 or mission_number > len(missions):
            return await ctx.send("Invalid mission number. Please choose a valid mission.")

        mission = missions[mission_number - 1]
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        if mission["description"] == "Answer a trivia question":
            await ctx.send("What is the capital of France?")
            try:
                def check(m):
                    return m.author == user and m.channel == ctx.channel
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                if msg.content.lower() == "paris":
                    await ctx.send("Correct! You have completed the mission.")
                else:
                    return await ctx.send("Incorrect answer. Mission failed.")
            except asyncio.TimeoutError:
                return await ctx.send("You took too long to answer. Mission failed.")
        elif mission["description"] == "Share a fun fact":
            await ctx.send("Please share a fun fact.")
            try:
                def check(m):
                    return m.author == user and m.channel == ctx.channel
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                await ctx.send(f"Fun fact received: {msg.content}")
            except asyncio.TimeoutError:
                return await ctx.send("You took too long to share a fun fact. Mission failed.")
        elif mission["description"] == "Post a meme":
            await ctx.send("Please post a meme.")
            try:
                def check(m):
                    return m.author == user and m.channel == ctx.channel and m.attachments
                msg = await self.bot.wait_for("message", check=check, timeout=30)
                await ctx.send("Meme received.")
            except asyncio.TimeoutError:
                return await ctx.send("You took too long to post a meme. Mission failed.")

        bounties[user_id]["amount"] += mission["reward"]
        await self.config.guild(ctx.guild).bounties.set(bounties)
        await self.config.member(user).bounty.set(bounties[user_id]["amount"])
        new_bounty = bounties[user_id]["amount"]
        new_title = self.get_bounty_title(new_bounty)
        await ctx.send(f"🏆 Mission completed! Ye earned {mission['reward']:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                       f"Current Title: {new_title}")

        # Announce if the user reaches a significant rank
        if bounties[user_id]["amount"] >= 900000000:
            await self.announce_rank(ctx.guild, user, new_title)

    async def check_milestones(self, ctx, user, new_bounty):
        """Check if the user has reached any bounty milestones."""
        milestones = {
            1000000: "First Million!",
            10000000: "Ten Million!",
            50000000: "Fifty Million!",
            100000000: "Hundred Million!",
        }

        for amount, title in milestones.items():
            if new_bounty >= amount:
                await ctx.send(f"🎉 {user.mention} has reached the milestone: **{title}** with a bounty of {new_bounty:,} Berries!")

async def setup(bot):
    await bot.add_cog(BountyCog(bot))
