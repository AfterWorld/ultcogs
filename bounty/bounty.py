from redbot.core import commands, Config
import discord
import random
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os

class BountyCog(commands.Cog):
    """A cog for managing bounties."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        default_member = {"last_daily_claim": None}
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
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Come back in {time_left.seconds // 3600} hours and {(time_left.seconds // 60) % 60} minutes, ye greedy sea dog!")

        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        increase = random.randint(10000, 50000)
        
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            bounties[user_id]["amount"] += increase
            await self.config.guild(ctx.guild).bounties.set(bounties)
            new_bounty = bounties[user_id]["amount"]
            new_title = self.get_bounty_title(new_bounty)
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            await ctx.send(f"💰 Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                           f"Current Title: {new_title}")
        else:
            await ctx.send("Ye decided not to open the chest. The Sea Kings must've scared ye off!")

    @commands.command()
    async def wanted(self, ctx):
        """Display a wanted poster with the user's avatar, username, and bounty."""
        user = ctx.author
        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        bounty_amount = bounties[user_id]["amount"]
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url

        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                if response.status != 200:
                    return await ctx.send("Failed to retrieve avatar.")
                avatar_data = await response.read()

        wanted_poster = await self.create_wanted_poster(user.display_name, bounty_amount, avatar_data)
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
        avatar_image = Image.open(io.BytesIO(avatar_data)).resize((635, 430))

        draw = ImageDraw.Draw(poster_image)
        try:
            font = ImageFont.truetype(font_path, 100)
        except OSError:
            return "Failed to load font. Please ensure the font file exists and is accessible."

        poster_image.paste(avatar_image, (65, 235))

        draw.text((150, 800), username, font=font, fill="black")
        draw.text((150, 850), f"{bounty_amount:,}", font=font, fill="black")

        output = io.BytesIO()
        poster_image.save(output, format="PNG")
        output.seek(0)

        return output

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

async def setup(bot):
    await bot.add_cog(BountyCog(bot))
