from redbot.core import commands, checks, modlog, Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.bot import Red
import discord
import aiohttp
import json
import logging
import os
import random
import time
import asyncio
import yaml
from datetime import datetime, timedelta

LOG = logging.getLogger("red.onepiecefun")

class OnePieceFun(commands.Cog):
    """Fun One Piece-themed commands for entertainment!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        self.trivia_sessions = {}
        default_guild = {
            "custom_devil_fruits": {},
            "bounties": {},
            "pirate_crews": {},
            "gambling_stats": {},
            "double_payout_event": False,
            "double_payout_end_time": None,
            "inspection_active": False,
            "trivia_scores": {},
            "trivia_cooldowns": {},
            "last_berryflip": {}
        }
        default_member = {
            "last_daily_claim": None
        }
        self.config.register_guild(sea_king_alert=False)
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        self.GENERAL_CHANNEL_ID = 425068612542398476
        self.message_count = {}
        self.last_announcement = {}
        self.trivia_lock = asyncio.Lock()
        self.trivia_sessions = {}
        self.questions = []
        self.bot.loop.create_task(self.load_questions_and_print())

    async def load_questions_and_print(self):
        await self.initialize_questions()
        print("Questions loaded. Available categories:", list(self.questions.keys()))
    
    async def initialize_questions(self):
        self.questions = {}
        data_folder = cog_data_path(self)
        yaml_files = list(data_folder.glob("*_questions.yaml"))
        
        if not yaml_files:
            print("No question files found. Loading default One Piece questions.")
            # Load the default One Piece questions from the URL
            one_piece_questions = await self.load_questions("one_piece")
            if one_piece_questions:
                self.questions["one_piece"] = one_piece_questions
        else:
            for file in yaml_files:
                category = file.stem.replace('_questions', '')
                try:
                    with file.open('r') as f:
                        questions = yaml.safe_load(f)
                    self.questions[category] = questions
                    print(f"Loaded {len(questions)} questions for {category}")
                except Exception as e:
                    print(f"Error loading questions for {category}: {str(e)}")
        
        print(f"Loaded categories: {list(self.questions.keys())}")
    
    async def load_questions(self, category):
        try:
            async with aiohttp.ClientSession() as session:
                url = f'https://raw.githubusercontent.com/AfterWorld/ultcogs/main/onepiecefun/categories/{category}_questions.yaml'
                print(f"Attempting to load questions from: {url}")
                async with session.get(url) as resp:
                    print(f"Response status: {resp.status}")
                    print(f"Response headers: {resp.headers}")
                    if resp.status == 200:
                        raw_content = await resp.text()
                        print(f"Raw content (first 500 chars): {raw_content[:500]}")
                        questions = yaml.safe_load(raw_content)
                        print(f"Successfully loaded {len(questions)} questions for {category}")
                        return questions
                    else:
                        print(f"Failed to fetch questions for {category}. Status code: {resp.status}")
                        return None
        except yaml.YAMLError as e:
            print(f"YAML parsing error for {category}: {str(e)}")
            print(f"Problematic content: {raw_content}")
            return None
        except Exception as e:
            print(f"An error occurred while loading questions for {category}: {str(e)}")
            return None
        
    BOUNTY_TITLES = [
        (0, "Cabin Boy"),
        (1000000, "Pirate Apprentice"),
        (10000000, "Rookie Pirate"),
        (50000000, "Super Rookie"),
        (100000000, "Notorious Pirate"),
        (300000000, "Pirate Captain"),
        (500000000, "Supernova"),
        (1000000000, "Yonko Commander"),
        (2000000000, "Yonko Candidate"),
        (10000000000, "Yonko"),
        (1000000000000, "Pirate King")
    ]
    def get_bounty_title(self, bounty):
        for threshold, title in reversed(self.BOUNTY_TITLES):
            if bounty >= threshold:
                return title
        return "Unknown"

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown per user
    async def df(self, ctx):
        """Get a random Devil Fruit fact or a made-up funny one."""
        df_facts = [
            "The Gum-Gum Fruit was the first Devil Fruit introduced in the series.",
            "Blackbeard is the only known person to have eaten two Devil Fruits.",
            "The Calm-Calm Fruit allows the user to create a sphere of silence.",
            "Marco's Phoenix fruit is a Mythical Zoan, one of the rarest types.",
            "Some Devil Fruits, like the Jacket-Jacket Fruit, have seemingly useless powers.",
            "The Ope-Ope Fruit is considered the ultimate Devil Fruit for medical operations.",
            "Chopper's Human-Human Fruit allowed an animal to gain human intelligence and form.",
            "Kaku and Kalifa were given Devil Fruits by Spandam, despite being skilled fighters already.",
            "Brook's Revive-Revive Fruit allowed him to return to life after death... but only once.",
            "The Mochi-Mochi Fruit is a 'special Paramecia' type, blurring the lines between Paramecia and Logia.",
            "The Little-Little Fruit lets the user shrink anything they touch, including themselves.",
            "The Hobby-Hobby Fruit can turn people into toys, erasing memories of their existence.",
            "There's a non-canon Devil Fruit that gives the power to control ramen noodles. Yum!",
            "The Swim-Swim Fruit allows the user to swim through solid objects... but not water!",
            "Legend has it there's a Fruit-Fruit Fruit that turns the user into a walking fruit basket.",
            "The Flame-Flame Fruit doesn't just produce fire, it turns the user's body into flame.",
            "Some say there's a Sleep-Sleep Fruit that puts everyone to sleep... including the user!",
            "The Rumor-Rumor Fruit supposedly lets you spread rumors that become true. Or is that just a rumor?",
            "The Drill-Drill Fruit is perfect for dentists... and pirates who love to make holes in ships!",
            "The Kilo-Kilo Fruit allows the user to change their weight from 1 to 10,000 kilograms. Talk about a yo-yo diet!"
        ]
        fact = random.choice(df_facts)
        await ctx.send(f"🍎 **Devil Fruit Fact:** {fact}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown per user
    async def love(self, ctx, user1: discord.Member, user2: discord.Member):
        """Calculate the One Piece love compatibility between two users with animation!"""
        love_percentage = random.randint(1, 100)
        
        # Create initial embed
        embed = discord.Embed(title=f"Calculating Love Compatibility...", color=discord.Color.blue())
        embed.set_footer(text="Powered by the Grand Line's mystical love calculator!")
        love_message = await ctx.send(embed=embed)
        
        # Simulate loading animation
        for i in range(3):
            await asyncio.sleep(1)
            embed.title = f"Calculating Love Compatibility{'.' * (i + 1)}"
            await love_message.edit(embed=embed)
        
        # Determine final color and emoji based on love percentage
        if love_percentage < 20:
            color = discord.Color.red()
            emoji = "💔"
        elif love_percentage < 40:
            color = discord.Color.orange()
            emoji = "😐"
        elif love_percentage < 60:
            color = discord.Color.gold()
            emoji = "🙂"
        elif love_percentage < 80:
            color = discord.Color.green()
            emoji = "💖"
        else:
            color = discord.Color.dark_magenta()
            emoji = "💞"

        # Create final embed with usernames
        embed = discord.Embed(
            title=f"Love Compatibility: {user1.name} & {user2.name}",
            color=color
        )
        embed.add_field(name="Love Percentage", value=f"{love_percentage}% {emoji}", inline=False)

        if love_percentage < 20:
            verdict = f"Arr! {user1.name} and {user2.name} be as compatible as Luffy and skipping meals!"
            image_url = "https://i.imgur.com/LqX1jSH.jpeg"
        elif love_percentage < 40:
            verdict = f"Yohohoho! The love between {user1.name} and {user2.name} be as empty as Brook's belly!"
            image_url = "https://i.imgur.com/7yAj1avb.jpg"
        elif love_percentage < 60:
            verdict = f"Aye, {user1.name} and {user2.name} be gettin' along like Zoro and a compass!"
            image_url = "https://i.imgur.com/INqnjtYb.jpg"
        elif love_percentage < 80:
            verdict = f"Shiver me timbers! {user1.name} and {user2.name} be as close as Sanji to his kitchen!"
            image_url = "https://static1.cbrimages.com/wordpress/wp-content/uploads/2022/10/0B4E75F9-5053-4BDA-B326-7E32C6E4FBD9.jpeg"
        else:
            verdict = f"By the powers of the sea! {user1.name} and {user2.name} be as perfect as Luffy and meat!"
            image_url = "https://media.tenor.com/l2-mUQdjoScAAAAe/luffy-one-piece.png"

        embed.add_field(name="Pirate's Verdict", value=verdict, inline=False)
        embed.set_image(url=image_url)
        embed.set_footer(text="Powered by the Grand Line's mystical love calculator!")

        await love_message.edit(embed=embed)
        
    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown per user
    async def roast(self, ctx, *, target: discord.Member = None):
        """Deliver a hilarious One Piece-themed roast!"""
        if target is None:
            target = ctx.author
        
        roasts = [
            f"{target.mention}, ye be as useless as a rubber knife at a Logia convention! 🔪😂",
            f"Oi, {target.mention}! Even Buggy the Clown be laughin' at yer skills! 🤡",
            f"Ye know, {target.mention}, if brains were berries, ye couldn't feed Chopper in his smallest form! 🧠🍒",
            f"Arr, {target.mention}! Ye be as lost as Zoro in a straight hallway! 🗺️😵",
            f"Listen here, {target.mention}, ye have the charm of a Sea King with a toothache! 🦈😬",
            f"{target.mention}, yer as slow as Luffy's brain during a math test! 🧮🐌",
            f"Oi, {target.mention}! Ye couldn't find the One Piece if it were hangin' 'round yer neck! 💎🔍",
            f"Ye know what, {target.mention}? Ye be makin' Foxy the Silver Fox look like a genius! 🦊🤓",
            f"Arr, {target.mention}! Ye have the fighting skills of a Den Den Mushi! 🐌👊",
            f"Blimey, {target.mention}! Ye be as useful in a fight as Usopp's rubber band of doom! 🪀💥",
            f"{target.mention}, yer navigation skills make Luffy look like Nami! 🧭😵‍💫",
            f"Oi, {target.mention}! Ye have the charisma of a Celestial Dragon at a commoner's party! 👑🎭",
            f"{target.mention}, ye couldn't beat Spandam in an arm-wrestling match! 💪�weak:",
            f"Arr, {target.mention}! Yer about as intimidating as Chopper's cotton candy loving form! 🦌🍭",
            f"Listen here, {target.mention}, ye have the memory of Gaimon... stuck in a box for 20 years! 📦🧠",
            f"{target.mention}, ye have the ambition of a Marine cleaning Akainu's boots! 👢😴",
            f"Oi, {target.mention}! Yer about as brave as Usopp facing a potato bug! 🥔🐛",
            f"Arrr, {target.mention}! Ye be as smooth as Sanji talkin' to a male okama! 💃😰",
            f"{target.mention}, ye have the luck of Luffy in an all-you-can't-eat buffet! 🍖🚫",
            f"Shiver me timbers, {target.mention}! Ye be as sneaky as Franky in his pre-timeskip speedos! 🩲😱",
            f"Oi, {target.mention}! Ye have the patience of Zoro waitin' for his sense of direction! ⏳🧭",
            f"{target.mention}, ye be as useful as Absalom's invisibility at a blind date! 👻👀",
            f"Blimey, {target.mention}! Ye have the subtlety of Luffy at a stealth mission! 🥷😅",
            f"Arr, {target.mention}! Yer wisdom rivals that of Luffy choosin' between adventure and meat! 🍖🤔",
            f"Listen here, {target.mention}, ye be as reliable as Buggy's flying body parts in a tornado! 🌪️🤡"
        ]

        roast = random.choice(roasts)
        
        # One Piece themed GIFs
        gifs = [
            "https://media1.tenor.com/m/7lRL4QGxcEQAAAAC/one-piece-brooklyn99.gif",  # Brook laughing
            "https://media1.tenor.com/m/_TOUqGiSupAAAAAC/nami-one-piece.gif",  # Nami facepalming
            "https://media1.tenor.com/m/O2PtVljr38kAAAAC/anime-one-piece.gif",  # Usopp laughing
            "https://media1.tenor.com/m/Ig-QyHS3mdQAAAAC/one-piece-one-piece-chopper.gif",  # Chopper shocked
            "https://media1.tenor.com/m/YkSHUSSIBpgAAAAC/sad-sanji.gif",  # Sanji disappointed
            "https://media1.tenor.com/m/bYLysUNam28AAAAC/chopper-angry-chopper.gif",  # Chopper angry
            "https://media1.tenor.com/m/DuHndhgl2FoAAAAC/your-team-sucks-you-guys-suck.gif",  # "You suck"
            "https://media1.tenor.com/m/DhRZ9HA6fbgAAAAC/monkey-d-luffy-luffy.gif",  # Luffy big laugh
            "https://media1.tenor.com/m/rz6rO_YNj3UAAAAC/trafalgar-law.gif",  # Law facepalm
            "https://media1.tenor.com/m/UjQkCTOcuTIAAAAd/buggy-one-piece.gif"   # Buggy angry
        ]
        
        embed = discord.Embed(title="🏴‍☠️ One Piece Roast 🏴‍☠️", description=roast, color=discord.Color.red())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_image(url=random.choice(gifs))
        embed.set_footer(text="Powered by the Grand Line's saltiest pirates!")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown per user
    async def bounty(self, ctx, *, user: discord.Member = None):
        """Check a user's bounty and title."""
        if user is None:
            user = ctx.author

        bounties = await self.config.guild(ctx.guild).bounties()
        user_id = str(user.id)

        if user_id in bounties:
            amount = bounties[user_id]['amount']
            title = self.get_bounty_title(amount)
            await ctx.send(f"💰 **Bounty Alert!** 💰\n"
                           f"{user.display_name}'s bounty is {amount:,} Berries!\n"
                           f"Current Title: {title}")
        else:
            # Generate a new bounty if one doesn't exist
            bounty = random.randint(1000000, 5000000)
            title = self.get_bounty_title(bounty)
            reason = self.generate_bounty_reason()
            async with self.config.guild(ctx.guild).bounties() as bounty_list:
                bounty_list[user_id] = {"amount": bounty}
            
            await ctx.send(f"💰 **New Bounty Alert!** 💰\n"
                           f"The World Government has placed a bounty of {bounty:,} Berries on {user.display_name}'s head "
                           f"{reason}!\nCurrent Title: {title}")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def bountyevent(self, ctx, event_type: str):
        """Trigger a server-wide bounty event."""
        valid_events = ["inflation", "deflation", "random"]
        if event_type not in valid_events:
            return await ctx.send(f"Invalid event type. Choose from: {', '.join(valid_events)}")

        async with self.config.guild(ctx.guild).bounties() as bounties:
            if event_type == "inflation":
                factor = random.uniform(1.1, 1.5)
                description = f"All bounties have increased by {(factor-1)*100:.1f}%!"
            elif event_type == "deflation":
                factor = random.uniform(0.5, 0.9)
                description = f"All bounties have decreased by {(1-factor)*100:.1f}%!"
            else:  # random
                factors = [random.uniform(0.5, 1.5) for _ in range(len(bounties))]
                description = "Bounties have changed unpredictably!"

            for user_id in bounties:
                if event_type == "random":
                    factor = factors.pop()
                bounties[user_id]["amount"] = int(bounties[user_id]["amount"] * factor)

        channel = self.bot.get_channel(self.GENERAL_CHANNEL_ID)
        if channel:
            await channel.send(f"🚨 **Emergency Bounty Update** 🚨\n{description}")
        await ctx.send("Bounty event successfully triggered!")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def resetbounty(self, ctx, user: discord.Member):
        """Reset a user's bounty (Mod only)."""
        async with self.config.guild(ctx.guild).bounties() as bounties:
            if str(user.id) in bounties:
                del bounties[str(user.id)]
                await ctx.send(f"{user.display_name}'s bounty has been reset by the World Government!")
            else:
                await ctx.send(f"{user.display_name} doesn't have a bounty to reset.")

    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def setbounty(self, ctx, user: discord.Member, amount: int):
        """Set a user's bounty to a specific amount (Admin only)."""
        async with self.config.guild(ctx.guild).bounties() as bounties:
            bounties[str(user.id)] = {"amount": amount}
        await ctx.send(f"The World Government has set {user.display_name}'s bounty to {amount:,} Berries!")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)  # 5-minute cooldown per user
    async def bountylist(self, ctx):
        """List the top 10 bounties in the server with rankings."""
        bounties = await self.config.guild(ctx.guild).bounties()
        if not bounties:
            return await ctx.send("🏴‍☠️ Arr! There be no bounties in this server yet, ye scurvy dogs!")
        
        sorted_bounties = sorted(bounties.items(), key=lambda x: x[1]['amount'], reverse=True)[:10]
        
        message = "```md\n"
        message += "💰 Top 10 Most Wanted Pirates 💰\n"
        message += "===================================\n\n"
        for index, (user_id, info) in enumerate(sorted_bounties, start=1):
            user = ctx.guild.get_member(int(user_id))
            if user:
                bounty_amount = f"{info['amount']:,}"
                pirate_rank = self.get_pirate_rank(info['amount'])
                message += f"{index}. {user.display_name}\n"
                message += f"   Bounty: {bounty_amount} Berries\n"
                message += f"   Rank: {pirate_rank}\n\n"
        message += "===================================\n"
        message += "Wanted Dead or Alive by the World Government\n"
        message += "```"
        
        footer = "🌊 These scallywags be the most dangerous pirates in these waters! 🏴‍☠️"
        
        await ctx.send(message)
        await ctx.send(footer)

    def get_pirate_rank(self, bounty):
        ranks = [
            (0, "Cabin Boy"),
            (1000000, "Pirate Apprentice"),
            (10000000, "Rookie Pirate"),
            (50000000, "Super Rookie"),
            (100000000, "Notorious Pirate"),
            (300000000, "Pirate Captain"),
            (500000000, "Supernova"),
            (1000000000, "Yonko Commander"),
            (2000000000, "Yonko Candidate"),
            (10000000000, "Yonko"),
            (1000000000000, "Pirate King")
        ]
        for threshold, rank in reversed(ranks):
            if bounty >= threshold:
                return rank
        return "Unknown"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        
        if message.channel.id == self.GENERAL_CHANNEL_ID:
            user_id = str(message.author.id)
            async with self.config.guild(message.guild).bounties() as bounties:
                if user_id not in bounties:
                    bounties[user_id] = {"amount": 0}
                bounties[user_id]["amount"] += random.randint(10, 50)  # Low amount increase

    async def increase_bounty(self, user, guild):
        async with self.config.guild(guild).bounties() as bounties:
            if str(user.id) not in bounties:
                bounties[str(user.id)] = {"amount": random.randint(1000000, 5000000)}
            
            current_bounty = bounties[str(user.id)]['amount']
            increase = random.randint(1000, 10000)
            new_bounty = current_bounty + increase
            bounties[str(user.id)]['amount'] = new_bounty

            if new_bounty // 1000000 > current_bounty // 1000000:
                await self.announce_bounty_increase(user, new_bounty, guild)

    async def announce_bounty_increase(self, user, new_bounty, guild):
        channel = guild.get_channel(self.GENERAL_CHANNEL_ID)
        if channel:
            last_time = self.last_announcement.get(str(user.id), 0)
            current_time = asyncio.get_event_loop().time()
            if current_time - last_time > 3600:  # 1 hour cooldown
                await channel.send(f"📢 **Bounty Update!** 📢\n"
                                   f"{user.mention}'s bounty has increased to {new_bounty:,} Berries! "
                                   f"The Marines are on high alert!")
                self.last_announcement[str(user.id)] = current_time

    def generate_bounty_reason(self):
        reasons = [
            "for eating too much at the Baratie without paying",
            "for mistaking a Marine base for a restaurant",
            "for trying to sell fake Devil Fruits to Kaido",
            "for asking Big Mom about her diet plan",
            "for using Zoro as a compass",
            "for stealing Doflamingo's sunglasses collection",
            "for trying to give Kaido swimming lessons",
            "for asking Buggy about his nose",
            "for trying to recruit Sea Kings into their crew",
            "for attempting to give Blackbeard a dental plan",
            "for trying to sell meat-scented cologne to Luffy",
            "for starting a 'Save the Sea Kings' campaign",
            "for opening a Monkey D. Luffy School of Strategy",
            "for trying to teach the Revolutionary Army to do the 'Binks' Sake' dance"
        ]
        return random.choice(reasons)

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
            bounties[user_id] = {"amount": 1000000}

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
    @checks.admin_or_permissions(administrator=True)
    async def resetallbounties(self, ctx, default_bounty: int = 1000000):
        """Reset all user bounties to a default value (default is 1,000,000 Berries)."""
        
        # Ask for confirmation
        confirm_msg = await ctx.send(f"Are ye sure ye want to reset ALL bounties to {default_bounty:,} Berries? "
                                     f"This action cannot be undone! React with ✅ to confirm or ❌ to cancel.")
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Reset bounties operation timed out. No bounties were changed.")
            return
        else:
            if str(reaction.emoji) == "❌":
                await ctx.send("Reset bounties operation cancelled. No bounties were changed.")
                return

        async with self.config.guild(ctx.guild).bounties() as bounties:
            # Store the old bounties for the summary
            old_bounties = bounties.copy()
            
            # Reset all bounties
            for user_id in bounties:
                bounties[user_id]["amount"] = default_bounty

        # Prepare a summary embed
        embed = discord.Embed(title="🏴‍☠️ Bounty Reset Summary 🏴‍☠️", color=discord.Color.red())
        embed.description = f"All bounties have been reset to {default_bounty:,} Berries!"
        embed.add_field(name="Total Bounties Reset", value=str(len(old_bounties)), inline=False)
        
        # Calculate and display some statistics
        total_old = sum(b["amount"] for b in old_bounties.values())
        total_new = len(old_bounties) * default_bounty
        embed.add_field(name="Total Berries Before", value=f"{total_old:,}", inline=True)
        embed.add_field(name="Total Berries After", value=f"{total_new:,}", inline=True)
        embed.add_field(name="Difference", value=f"{total_new - total_old:,}", inline=True)

        await ctx.send(embed=embed)
        await ctx.send("Yarr! All bounties have been reset by the World Government's decree!")
                
    @commands.command()
    async def shipname(self, ctx, name1: str, name2: str):
        """Generate a One Piece-style ship name for two characters."""
        ship_prefixes = ["Thousand", "Going", "Oro", "Red", "Big", "Polar", "Moby", "Sexy", "Drunken", "Merry", "Sunny", "Laughing", "Crying", "Flying", "Roaring", "Thundering", "Whispering", "Golden", "Silver", "Burning", "Frozen", "Emerald", "Sapphire", "Ruby", "Diamond"]
        ship_suffixes = ["Sunny", "Merry", "Jackson", "Force", "Top", "Tang", "Dick", "Foxy", "Roger", "Saber", "Dumpling", "Octopus", "Banana", "Cutlass", "Pearl", "Wave", "Storm", "Phoenix", "Dragon", "Serpent", "Titan", "Giant", "Warrior", "Legend", "Myth"]
        
        ship_name = f"{random.choice(ship_prefixes)} {random.choice(ship_suffixes)}"
        ship_type = random.choice(["Galleon", "Caravel", "Frigate", "Schooner", "Sloop", "Brig", "Man-of-War"])
        ship_feature = random.choice(["a figurehead of a roaring lion", "sails made from Sea King skin", "a crow's nest shaped like a pirate hat", "cannons that shoot cola", "a built-in ramen shop", "a secret underwater viewing room", "a mini Thriller Bark amusement park"])

        embed = discord.Embed(title=f"⚓ The {ship_name} ⚓", color=discord.Color.blue())
        embed.add_field(name="Ship Type", value=ship_type, inline=False)
        embed.add_field(name="Special Feature", value=f"This ship has {ship_feature}!", inline=False)
        embed.add_field(name="Owners", value=f"Captained by the fearsome duo of {name1} and {name2}", inline=False)
        embed.set_footer(text="May it sail the Grand Line with pride!")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def piratename(self, ctx, *, name: str):
        """Generate a One Piece-style pirate name."""
        epithets = ["Straw Hat", "Fire Fist", "Pirate Hunter", "Black Leg", "Cat Burglar", "Soul King", "Cyborg", "Devil Child", 
                    "Humming", "Red-Haired", "Hawk-Eye", "Surgeon of Death", "Dark King", "Fire Tank", "Big News", "Red Flag",
                    "Thousand Storm", "Iron Mace", "Massacre Soldier", "Diamond", "Foxfire", "Glutton", "Sky Knight", "First Son of the Sea"]
        
        pirate_name = f"'{random.choice(epithets)}' {name}"
        bounty = f"{random.randint(100, 5000):,}000,000"
        crew_name = f"The {random.choice(['Fearsome', 'Mighty', 'Sneaky', 'Ruthless', 'Jolly', 'Drunken', 'Wild'])} {random.choice(['Skull', 'Fist', 'Storm', 'Wave', 'Sun', 'Moon', 'Star'])} Pirates"
        signature_move = f"{random.choice(['Thunderbolt', 'Hurricane', 'Inferno', 'Tsunami', 'Earthquake', 'Vortex', 'Nebula'])} {random.choice(['Punch', 'Kick', 'Slash', 'Blast', 'Cannon', 'Strike', 'Crush'])}"

        embed = discord.Embed(title=f"🏴‍☠️ {pirate_name} 🏴‍☠️", color=discord.Color.dark_red())
        embed.add_field(name="Bounty", value=f"{bounty} Berries", inline=False)
        embed.add_field(name="Crew", value=crew_name, inline=False)
        embed.add_field(name="Signature Move", value=signature_move, inline=False)
        embed.set_footer(text="Strike fear into the hearts of Marines everywhere!")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def devilfruit(self, ctx):
        """Generate a random, funny Devil Fruit power."""
        prefixes = ["Noodle", "Bubble", "Sneeze", "Hiccup", "Tickle", "Belch", "Giggle", "Blush", "Yawn", "Wink", "Blink", "Wiggle", "Jiggle", "Wobble", "Noogie", "Booger", "Armpit", "Earlobe", "Toenail", "Nostril"]
        suffixes = ["Fruit", "Fruit", "Fruit", "Nut", "Berry", "Melon", "Pineapple", "Mango", "Durian", "Lychee", "Kumquat", "Persimmon", "Fig", "Pomegranate", "Jackfruit"]
        
        fruit_name = f"{random.choice(prefixes)}-{random.choice(prefixes)} {random.choice(suffixes)}"
        powers = [
            f"the power to {fruit_name.split('-')[0].lower()} uncontrollably when nervous",
            f"the ability to make others {fruit_name.split('-')[1].lower()} on command",
            f"the power to turn anything you touch into {fruit_name.split('-')[0].lower()}s",
            f"the ability to shoot {fruit_name.split('-')[1].lower()}s from your fingertips",
            f"the power to summon an army of {fruit_name.split('-')[0].lower()}ing sea creatures",
            f"the ability to create life-size {fruit_name.split('-')[1].lower()} sculptures with your mind",
            f"the power to communicate with {fruit_name.split('-')[0].lower()}s telepathically",
            f"the ability to predict the future, but only while {fruit_name.split('-')[1].lower()}ing",
            f"the power to teleport, but only to places where people are {fruit_name.split('-')[0].lower()}ing",
            f"the ability to change the color of anything to '{fruit_name.split('-')[1].lower()} purple'"
        ]
        
        power = random.choice(powers)
        weaknesses = [
            "you smell like overripe fruit when using your power",
            "you can't stop dancing while using your ability",
            "your power only works on Tuesdays",
            "using your power makes you speak in rhymes for an hour",
            "your hair changes color every time you use your power"
        ]

        embed = discord.Embed(title=f"🍎 The {fruit_name} 🍎", color=discord.Color.green())
        embed.add_field(name="Power", value=power, inline=False)
        embed.add_field(name="Weakness", value=f"However, {random.choice(weaknesses)}.", inline=False)
        embed.set_footer(text="Use it wisely, ye scurvy dog!")
        
        await ctx.send(embed=embed)


    @commands.command()
    async def reaction(self, ctx, *, situation: str = None):
        """Get a One Piece character's reaction to a situation."""
        characters = {
            "Luffy": ["laughs and asks if it's edible", "shouts 'I'm gonna be the Pirate King!'", "picks his nose thoughtfully", "stretches his arms to grab some meat", "grins widely and says 'Sounds like an adventure!'"],
            "Zoro": ["gets lost trying to respond", "mumbles something about training", "takes a nap", "challenges the situation to a duel", "opens another bottle of sake"],
            "Nami": ["demands payment for her opinion", "sighs and facepalms", "starts plotting how to profit from the situation", "checks if the situation affects her tangerines", "draws a map to navigate through the problem"],
            "Usopp": ["tells an outrageous lie about a similar situation", "hides behind Luffy", "invents a new gadget to deal with it", "claims he's allergic to the situation", "dramatically recounts his '8000 followers' facing a similar problem"],
            "Sanji": ["offers to cook something to help", "swoons if it involves a lady", "picks a fight with Zoro", "lights a cigarette and ponders coolly", "kicks the problem away with his 'Diable Jambe'"],
            "Chopper": ["hides the wrong way", "offers medical advice", "gets sparkly-eyed with excitement", "transforms into Guard Point out of surprise", "tries to heal the situation with a Rumble Ball"],
            "Robin": ["chuckles ominously", "shares a morbid historical fact", "calmly sips tea", "uses her Hana Hana no Mi to multitask a solution", "reads a book about similar situations"],
            "Franky": ["strikes a pose and shouts 'SUPER!'", "offers to build a machine to solve the problem", "questions if it's 'SUPER' enough", "shows off a new cyborg feature to handle it", "suggests solving it with a 'COUP DE BURST'"],
            "Brook": ["makes a skull joke", "asks to see ladies' panties", "starts playing a song about the situation", "laughs with a 'Yohohoho!'", "offers to fight the situation with his Soul Solid"]
        }
        
        # Check if the command is used as a reply
        if ctx.message.reference and not situation:
            replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
            situation = replied_message.content
        elif not situation:
            await ctx.send("Yarr! Ye need to provide a situation or reply to a message, ye scurvy dog!")
            return

        character = random.choice(list(characters.keys()))
        reaction = random.choice(characters[character])
        
        character_ascii = self.get_character_ascii(character)
        
        response = f"```\n{character_ascii}\n```\n"
        response += f"📜 Situation: **{situation}**\n\n"
        response += f"💬 **{character}'s Reaction:**\n{reaction}\n\n"
        response += "🌊 One Piece reactions, straight from the Grand Line! 🏴‍☠️"
        
        await ctx.send(response)

    @commands.command()
    async def island(self, ctx):
        """Generate a random One Piece-style island name and description."""
        prefixes = ["Punk", "Whole", "Drum", "Fishman", "Sky", "Water", "Dressrosa", "Shells", "Jaya", "Enies", "Thriller", "Laugh", "Whisper", "Howl", "Ember", "Frost", "Bloom", "Shadow", "Crystal", "Neon"]
        suffixes = ["Island", "Kingdom", "Archipelago", "City", "Town", "Land", "Paradise", "Hell", "World", "Country", "Reef", "Plateau", "Jungle", "Desert", "Tundra", "Volcano", "Labyrinth", "Ruins", "Citadel", "Oasis"]
        
        features = ["giant trees that whisper ancient secrets", "talking animals with philosopher's beards", "extreme weather that changes every 5 minutes", "ancient ruins of a technologically advanced civilization", "futuristic technology powered by Sea King snores", 
                    "perpetual night illuminated by bioluminescent creatures", "eternal summer with occasional snow cone rain", "floating islands connected by rainbow bridges", "underwater caves filled with breathing air bubbles", "living buildings that rearrange themselves daily"]
        
        dangers = ["man-eating plants with a taste for pirate hats", "volcanic eruptions that spew gold instead of lava", "whirlpools that lead to random parts of the Grand Line", "giant sea monsters that tell dad jokes", "unpredictable gravity that turns walking into flying", 
                   "memory-erasing mist that makes you forget your favorite food", "time distortions that age cheese but not people", "reality-bending mirages that make Zoro even more lost", "cursed treasures that turn people into Den Den Mushis", "shape-shifting natives who always impersonate the wrong person"]
        
        island_name = f"{random.choice(prefixes)} {random.choice(suffixes)}"
        feature = random.choice(features)
        danger = random.choice(dangers)
        population = f"{random.randint(100, 1000000):,}"
        
        island_ascii = self.get_island_ascii()
    
        response = f"```\n{island_ascii}\n```\n"
        response += f"🏝️  **{island_name}**  🏝️\n\n"
        response += f"📊 Population: {population}\n\n"
        response += f"✨ Known for: {feature}\n\n"
        response += f"⚠️ Danger: {danger}\n\n"
        response += "🧭 May your Log Pose guide you to this mysterious island! ⛵"
        
        await ctx.send(response)

    @commands.command()
    async def crewrole(self, ctx, *, name: str):
        """Assign a random One Piece crew role to someone."""
        roles = [
            "Captain", "First Mate", "Navigator", "Sniper", "Chef", "Doctor", "Shipwright", "Musician",
            "Archaeologist", "Helmsman", "Lookout", "Strategist", "Cabin Boy/Girl", "Pet", "Quartermaster",
            "Rigger", "Gunner", "Sailing Master", "Boatswain", "Carpenter"
        ]
        
        quirks = [
            "who's always hungry", "with a secret past", "who's afraid of their own shadow",
            "who can't swim (even without a Devil Fruit)", "who tells the worst jokes",
            "who's obsessed with treasure", "who sleeps through every battle",
            "who's in love with the ship", "who thinks they're the captain (but they're not)",
            "who's actually a Marine spy (shh, don't tell anyone)", "who can only speak in rhymes",
            "who believes they're invisible (they're not)", "who collects wanted posters as a hobby",
            "who's allergic to adventure", "who's constantly planning mutiny (but never goes through with it)"
        ]
        
        role = random.choice(roles)
        quirk = random.choice(quirks)
        
        pirate_ascii = self.get_pirate_ascii()
        
        response = f"```\n{pirate_ascii}\n```\n"
        response += f"🏴‍☠️ Ahoy, {name}! Yer new role on the crew be:\n\n"
        response += f"🎭 **{role}**\n\n"
        response += f"👀 Special Quirk: {quirk}\n\n"
        response += "⚓ Welcome aboard, ye scurvy dog! ⚓"
        
        await ctx.send(response)

    def get_character_ascii(self, character):
        characters = {
            "Luffy": """
      _____
     /     \\
    | ^   ^ |
    |   >   |
    |  ___  |
     \\_____/
       | |
      /   \\
    """,
            "Zoro": """
      _____
     |     |
     | >  > |
     |  _|  |
     | ___ |
     |_____|
       /|\\
      / | \\
    """,
            "Nami": """
      _____
     /     \\
    | o   o |
    |   3   |
    |  ___  |
     \\_____/
       | |
      / | \\
    """,
            "Usopp": """
      _____
     |     |
     | O  O |
     |  <>  |
     | ___ |
     |_____|
       | |
      / | \\
    """,
            "Sanji": """
      _____
     |     |
     | )  O |
     |  __  |
     | ___ |
     |_____|
       | |
      / | \\
    """,
            "Chopper": """
      /\\___/\\
     (  o o  )
     /   Y   \\
    ( \\_---_/ )
     \\_______/
       |   |
      /     \\
    """,
            "Robin": """
      _____
     /     \\
    | ^   ^ |
    |   -   |
    |  ___  |
     \\_____/
       | |
      / | \\
    """,
            "Franky": """
     \\=====/ 
      |   |
     [|-O-|]
      |___|
      /   \\
     /     \\
    """,
            "Brook": """
      _____
     /     \\
    | O   O |
    |   _   |
    |  ___  |
     \\_____/
       | |
      / | \\
    """
        }
        return characters.get(character, """
         _____
        |     |
        | O O |
        |  ^  |
        | --- |
        |_____|
         /   \\
        """)
        
    def get_island_ascii(self):
        return r"""
                      |
        _       _    ||\t
       | \     | |    |     _
       |  \    | |   |o|  _| |_        __
     __|   \   | |_  |o|_|     |_    _|  |_
    |  |    \  |   |_|o|     ___  |_|      |
    |  |     \_|      |o|               O  |
    |  |  ()    .---.  o|  ___________   \ |
    |  |       /     \ o|_|  __    __ |__|\|
    |  |      /  ()   \o| | |  |  |  |  |  |
    |__|_____/_________\_|_|__|__|__|__|__| 
        /|\     /|\    /|\
       / | \   / | \  / | \
      /  |  \ /  |  \/  |  \
     /   |   /   |   \  |   \
  __/    |  /    |    \ |    \__
 /       | /     |     \|       \
/_______________________________________\
^^^~^^~^~^^~^~~^~^~^~^~^~~^~^~~^~^~^~^^~^^
~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~^~
        """
        
    def get_pirate_ascii(self):
        return r"""
           _____
          |  _  |
         _| (_) |_
        |   ___   | 
        |  |   |  |
        |  | . |  |   
        |__| _ |__|     
           (o_o)        |==========|
          /  v  \       | ________ |
         /\  ^  /\      ||    |   ||
        /  \/_\/  \     ||____|___||
       |    | |    |    |[■■■]|[■■]|
       |    | |    |    |_____|____|
       |    | |    |      )  (
       |    | |    |     )__(
     __|____| |____|____(_)__)__
    /                            \
        """

    @commands.command()
    @commands.cooldown(1, 240, commands.BucketType.user)  # 4-minute cooldown per user
    async def decode(self, ctx):
        """Decode a 'mysterious' poneglyph message."""
        messages = [
            "The One Piece is real... but it was the friends we made along the way.",
            "Congratulations! You can read poneglyphs. The World Government wants to know your location.",
            "Here's the secret recipe for Sanji's best dish... just kidding, it's blank!",
            "Turn left at the giant whale, right at the sky island, and straight on 'til morning.",
            "This poneglyph intentionally left blank. Please try again in 800 years.",
            "The true power of the Gum-Gum fruit is... [The rest is too weathered to read]",
            "Warning: Reading this poneglyph may cause spontaneous dance parties.",
            "Raftel is just an anagram of... [The rest is covered in Buggy's graffiti]"
        ]
        
        decoded = random.choice(messages)
        await ctx.send(f"🗿 You've decoded the poneglyph! It reads:\n\n*{decoded}*")

    @commands.command()
    async def df_add(self, ctx, name: str, *, description: str):
        """Add a custom Devil Fruit to the server's list."""
        async with self.config.guild(ctx.guild).custom_devil_fruits() as df_list:
            df_list[name] = description
        await ctx.send(f"The {name} has been added to the Devil Fruit encyclopedia!")

    @commands.command()
    async def df_list(self, ctx):
        """List all custom Devil Fruits for this server."""
        df_list = await self.config.guild(ctx.guild).custom_devil_fruits()
        if not df_list:
            return await ctx.send("There are no custom Devil Fruits in this server's encyclopedia yet!")
        
        message = "🍎 **Custom Devil Fruits** 🍎\n\n"
        for name, desc in df_list.items():
            message += f"**{name}**: {desc}\n\n"
        
        pages = list(pagify(message, delims=["\n\n"], page_length=1000))
        await menu(ctx, pages, DEFAULT_CONTROLS)
        
    @commands.command()
    async def strawhat(self, ctx, *, name: str):
        """If the mentioned person joined the Straw Hat crew, what would their role and quirk be?"""
        roles = [
            "the second chef, specializing in desserts",
            "the apprentice shipwright, always carrying a hammer",
            "the assistant doctor, with a fear of blood",
            "the backup musician, who only knows one song",
            "the unofficial storyteller, with tales no one believes",
            "the ship's gardener, growing suspicious plants",
            "the crew's tailor, with a very 'unique' fashion sense",
            "the log keeper, who embellishes every entry",
            "the fishing expert, who's never caught a fish",
            "the treasure appraiser, who overvalues everything"
        ]
        
        quirks = [
            "but they sleep through every meal",
            "and they have a secret collection of Marine wanted posters",
            "though they get seasick easily",
            "but they think every island is Raftel",
            "and they're convinced they're the reincarnation of Gol D. Roger",
            "though they're terrified of Luffy's stretching",
            "but they keep trying to 'improve' Nami's climate baton",
            "and they have a peculiar habit of talking to Sea Kings",
            "though they believe they're the strongest after Luffy (they're not)",
            "but they're on a quest to find the 'One Piece' of perfect clothing"
        ]
        
        role = random.choice(roles)
        quirk = random.choice(quirks)
        
        await ctx.send(f"If {name} joined the Straw Hat crew, they'd be {role}, {quirk}!")

    @commands.command()
    async def move(self, ctx, *, name: str):
        """Generate a random One Piece-style move name."""
        prefixes = ["Gum-Gum", "Flame-Flame", "Rumble-Rumble", "Dragon-Dragon", "Chop-Chop", "Slip-Slip", "Smoke-Smoke", "Sand-Sand"]
        moves = ["Pistol", "Bazooka", "Gatling", "Rifle", "Storm", "Whip", "Hammer", "Cannon", "Tornado", "Blast", "Sword", "Spear"]
        adjectives = ["Flaming", "Thundering", "Colossal", "Rapid-Fire", "Spinning", "Gigantic", "Piercing", "Exploding"]
        
        move_name = f"{random.choice(prefixes)} {random.choice(adjectives)} {random.choice(moves)}"
        description = f"{name} unleashes their secret technique: {move_name}!"
        
        effects = [
            "It's super effective!",
            "The attack misses wildly and hits a nearby building instead.",
            "Somehow, it turns into a dance move mid-attack.",
            "Everyone is impressed, but also slightly confused.",
            "It works perfectly, but {name} forgets how they did it immediately after.",
            "The attack is so powerful, it launches {name} backwards!",
            "It's not very effective... but it looks really cool!",
            "The move is interrupted by the dinner bell. Priorities, right?"
        ]
        
        effect = random.choice(effects).format(name=name)
        
        await ctx.send(f"{description}\n{effect}")

    @commands.command()
    @commands.cooldown(1, 600, commands.BucketType.channel)  # 10-minute cooldown
    async def trivia(self, ctx, category: str = "one_piece"):
        """Start a trivia game for a specific category!"""
        print(f"Trivia command called with category: {category}")  # Debug print
        print(f"Available categories: {list(self.questions.keys())}")  # Debug print
        
        if ctx.channel.id in self.trivia_sessions:
            await ctx.send("A trivia game is already in progress in this channel!")
            return
    
        category = category.lower()
        if category not in self.questions:
            available_categories = ", ".join(self.questions.keys())
            await ctx.send(f"Invalid category. Available categories: {available_categories}")
            return
    
        if not self.questions[category]:
            await ctx.send(f"No questions available for {category}! The trivia game cannot start.")
            return
    
        self.trivia_sessions[ctx.channel.id] = {"active": True, "scores": {}, "category": category}
    
        await ctx.send(f"🏴‍☠️ A new {category.capitalize()} Trivia game has begun! First to 25 points wins! 🏆")  # Changed from 10 to 25
    
        try:
            for question in random.sample(self.questions[category], min(len(self.questions[category]), 50)):  # Increased from 20 to 50
                if not self.trivia_sessions[ctx.channel.id]["active"]:
                    await ctx.send("The trivia game has been stopped!")
                    break
    
                if not await self.ask_question(ctx, question):
                    break
    
                if any(score >= 25 for score in self.trivia_sessions[ctx.channel.id]["scores"].values()):  # Changed from 10 to 25
                    break
    
                await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            LOG.error(f"Error in trivia game: {str(e)}", exc_info=True)
        finally:
            await self.end_game(ctx)

    async def ask_question(self, ctx, question):
        category = self.trivia_sessions[ctx.channel.id]["category"]
        await ctx.send(f"🏴‍☠️ **{category.capitalize()} Trivia** 🏴‍☠️\n\n{question['question']}")
        
        def check(m):
            return m.channel == ctx.channel and m.author != ctx.bot.user
    
        start_time = time.time()
        answered = False
        hint_index = 0
        hint_times = [20, 30, 60]
        question_duration = 120  # 2 minutes
    
        async def send_hints():
            nonlocal hint_index
            for hint_time in hint_times:
                await asyncio.sleep(hint_time - (hint_times[hint_index-1] if hint_index > 0 else 0))
                if answered:
                    break
                if hint_index < len(question['hints']):
                    await ctx.send(f"Hint: {question['hints'][hint_index]}")
                hint_index += 1
    
        hint_task = asyncio.create_task(send_hints())
    
        try:
            while time.time() - start_time < question_duration and not answered:
                try:
                    msg = await asyncio.wait_for(self.bot.wait_for("message", check=check), 
                                                 timeout=question_duration - (time.time() - start_time))
                    
                    if msg.content.lower() in [answer.lower() for answer in question['answers']]:
                        scores = self.trivia_sessions[ctx.channel.id]["scores"]
                        scores[msg.author] = scores.get(msg.author, 0) + 1
                        await ctx.send(f"Aye, that be correct, {msg.author.display_name}! Ye know yer {category.capitalize()} lore!")
                        answered = True
                        if scores[msg.author] >= 25:
                            await ctx.send(f"🎉 Congratulations, {msg.author.display_name}! Ye've reached 25 points and won the game! 🏴‍☠️")
                            return False  # End the game
                
                except asyncio.TimeoutError:
                    # This is expected if no answer is given before the next hint or end of question
                    pass
    
        finally:
            hint_task.cancel()  # Ensure the hint task is cancelled when the question ends
    
        if not answered:
            await ctx.send(f"Time's up, ye slow sea slugs! The correct answers were: {', '.join(question['answers'])}")
    
        await asyncio.sleep(2)  # Add a short pause between questions
        return True  # Continue the game
    
    async def display_scores(self, ctx):
        if ctx.channel.id not in self.trivia_sessions:
            return
        scores = self.trivia_sessions[ctx.channel.id]["scores"]
        if not scores:
            return
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        score_message = "Current scores:\n" + "\n".join(f"{player.display_name}: {score}" for player, score in sorted_scores[:5])
        await ctx.send(f"```{score_message}```")

    async def end_game(self, ctx):
        if ctx.channel.id in self.trivia_sessions:
            category = self.trivia_sessions[ctx.channel.id]["category"]
            final_scores = self.trivia_sessions[ctx.channel.id]["scores"]
            del self.trivia_sessions[ctx.channel.id]
            
            async with self.config.guild(ctx.guild).trivia_scores() as scores:
                if category not in scores:
                    scores[category] = {}
                for player, score in final_scores.items():
                    if str(player.id) not in scores[category]:
                        scores[category][str(player.id)] = {"total_score": 0, "games_played": 0}
                    scores[category][str(player.id)]["total_score"] += score
                    scores[category][str(player.id)]["games_played"] += 1
    
            await ctx.send(f"The {category.capitalize()} trivia game has ended! Thanks for playing, ye scurvy dogs!")
            await self.display_leaderboard(ctx, category)

    @commands.command()
    @commands.is_owner()  # Restrict this command to the bot owner
    async def triviaupload(self, ctx):
        """Upload a custom YAML file for trivia."""
        if not ctx.message.attachments:
            await ctx.send("Please attach a YAML file with your trivia questions.")
            return
    
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(('.yaml', '.yml')):
            await ctx.send("The attached file must be a YAML file (with .yaml or .yml extension).")
            return
    
        try:
            content = await attachment.read()
            questions = yaml.safe_load(content)
    
            # Validate the structure of the YAML file
            if not isinstance(questions, list):
                raise ValueError("The YAML file should contain a list of questions.")
    
            for question in questions:
                if not all(key in question for key in ['question', 'answers', 'hints', 'difficulty']):
                    raise ValueError("Each question must have 'question', 'answers', 'hints', and 'difficulty' fields.")
    
            # Get the category name from the filename (without .yaml or .yml extension)
            category = attachment.filename.rsplit('.', 1)[0].lower()
    
            # Save the questions to the bot's data folder
            file_path = cog_data_path(self) / f"{category}_questions.yaml"
            with file_path.open('wb') as f:
                f.write(content)
    
            # Load the new questions into memory
            self.questions[category] = questions
    
            await ctx.send(f"Successfully uploaded and loaded {len(questions)} questions for the '{category}' category.\n"
                           f"File saved at: {file_path}")
        except Exception as e:
            await ctx.send(f"An error occurred while processing the file: {str(e)}")
            return
    
    @triviaupload.error
    async def triviaupload_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("Only the bot owner can upload new trivia questions.")
        else:
            await ctx.send(f"An error occurred: {str(error)}")

    @commands.command()
    @commands.is_owner()
    async def trivialist(self, ctx):
        """List all uploaded trivia files."""
        data_folder = cog_data_path(self)
        trivia_files = list(data_folder.glob("*_questions.yaml"))
        
        if not trivia_files:
            await ctx.send("No trivia files have been uploaded yet.")
            return
    
        file_list = "\n".join([f"- {file.name}" for file in trivia_files])
        await ctx.send(f"Uploaded trivia files:\n{file_list}")
            
    @commands.command()
    async def triviastop(self, ctx):
        """Stop the current trivia game."""
        if ctx.channel.id not in self.trivia_sessions:
            await ctx.send("There's no active trivia game in this channel, ye confused sea dog!")
            return
        
        self.trivia_sessions[ctx.channel.id]["active"] = False
        await ctx.send("The trivia game has been stopped by the captain's orders!")
        await self.end_game(ctx)

    async def end_game(self, ctx):
        if ctx.channel.id in self.trivia_sessions:
            category = self.trivia_sessions[ctx.channel.id]["category"]
            final_scores = self.trivia_sessions[ctx.channel.id]["scores"]
            del self.trivia_sessions[ctx.channel.id]
            
            async with self.config.guild(ctx.guild).trivia_scores() as scores:
                if category not in scores:
                    scores[category] = {}
                for player, score in final_scores.items():
                    if str(player.id) not in scores[category]:
                        scores[category][str(player.id)] = {"total_score": 0, "games_played": 0}
                    scores[category][str(player.id)]["total_score"] += score
                    scores[category][str(player.id)]["games_played"] += 1
    
            await ctx.send(f"The {category.capitalize()} trivia game has ended! Thanks for playing, ye scurvy dogs!")
            await self.display_leaderboard(ctx, category)
        
    @commands.command()
    async def trivialeaderboard(self, ctx, category: str = "one_piece"):
        """Display the trivia leaderboard for a specific category."""
        await self.display_leaderboard(ctx, category.lower())
    
    async def display_leaderboard(self, ctx, category=None):
        if category is None:
            # If no category is provided, use the category from the active session
            if ctx.channel.id in self.trivia_sessions:
                category = self.trivia_sessions[ctx.channel.id]["category"]
            else:
                # Default to 'one_piece' if there's no active session
                category = "one_piece"
    
        async with self.config.guild(ctx.guild).trivia_scores() as scores:
            if category not in scores:
                await ctx.send(f"No leaderboard available for {category.capitalize()} trivia.")
                return
            
            sorted_scores = sorted(scores[category].items(), key=lambda x: x[1]['total_score'], reverse=True)[:10]
            
            embed = discord.Embed(title=f"🏆 {category.capitalize()} Trivia Leaderboard 🏆", color=discord.Color.gold())
            for i, (player_id, data) in enumerate(sorted_scores, 1):
                player = ctx.guild.get_member(int(player_id))
                if player:
                    embed.add_field(
                        name=f"{i}. {player.display_name}",
                        value=f"Total Score: {data['total_score']}\nGames Played: {data['games_played']}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def reload_trivia(self, ctx):
        """Manually reload trivia questions."""
        await ctx.send("Reloading trivia questions...")
        await self.initialize_questions()
        categories = ", ".join(self.questions.keys())
        await ctx.send(f"Trivia questions reloaded. Available categories: {categories}")

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def transponder(self, ctx):
        """Intercept a random Den Den Mushi conversation."""
        conversations = [
            ("Luffy & Sanji", "Luffy: Meat! Meat! Meat!\nSanji: We just ate, you rubber idiot!", "🍖"),
            ("Nami & Usopp", "Nami: Has anyone seen my treasure?\nUsopp: *sweating* N-no, definitely not!", "💰"),
            ("Zoro & Robin", "Zoro: I think I'm lost...\nRobin: You're in the crow's nest, Zoro.", "🧭"),
            ("Chopper & Random Pirate", "Chopper: I'm not a tanuki!\nRandom Pirate: What a cute raccoon dog!", "🦝"),
            ("Brook & Nami", "Brook: Yohohoho! May I see your pan-\nNami: NO!", "👙"),
            ("Franky & Law", "Franky: SUPER!!!\nLaw: Please stop posing, we're in the middle of a battle.", "🦾"),
            ("Buggy & Shanks", "Buggy: I am the great Captain Buggy!\nShanks: *laughing uncontrollably*", "🤡"),
            ("Garp & Luffy", "Garp: I'm coming to visit, Luffy!\nLuffy: Quick, everyone hide!", "👴"),
            ("Kaido & Big Mom", "Kaido: Why won't anyone let me die?\nBig Mom: WEDDING CAKE!!!", "🍰")
        ]
        convo = random.choice(conversations)
        
        embed = discord.Embed(title="📞 Intercepted Den Den Mushi Conversation 📞", color=discord.Color.purple())
        embed.add_field(name=f"{convo[2]} Participants", value=convo[0], inline=False)
        embed.add_field(name="Conversation", value=convo[1], inline=False)
        embed.set_footer(text="Purupurupuru... Gatcha!")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 180, commands.BucketType.user)
    async def gumgum(self, ctx):
        """Stretch your limbs like Luffy and see what happens!"""
        results = [
            ("Marine's Ice Cream", "You stretched your arm and accidentally knocked over a Marine's ice cream. The Marine is now crying over his lost treat!", "🍦💥"),
            ("Sea King Tickle", "Your elongated nose tickled a Sea King, and now it's chasing the ship! Time for a hasty retreat!", "👃🐉"),
            ("Sky Island Mishap", "You tried to grab a cloud but ended up pulling down a Sky Island resident. They're not amused by your accidental skydiving invitation!", "☁️😱"),
            ("Human Pretzel", "Your rubbery fingers got tangled, and now you're a human pretzel. Sanji's considering adding you to the menu!", "🥨"),
            ("Cooking Pot Faceplant", "You bounced off a wall and landed face-first in Sanji's cooking pot. Congratulations, you're now the secret ingredient!", "🍲😵"),
            ("Nami's Secret", "Your stretched ear overheard Nami's secret treasure map location! But can you keep a secret?", "🗺️🤫"),
            ("Calm Belt Launch", "You accidentally launched yourself into the Calm Belt. Say hi to the Sea Kings for us!", "🌊😅"),
            ("Balloon Pirate", "Your elastic cheeks inflated, and you floated away like a balloon. Enjoy the view from up there!", "🎈"),
            ("Fridge Raider Caught", "You tried to steal food from the fridge, but Sanji caught your extended hand. Prepare for a lecture on patience and portion control!", "🍖🚫")
        ]
        result = random.choice(results)
        
        embed = discord.Embed(title="🖐️ Gum-Gum Stretch! 🖐️", color=discord.Color.red())
        embed.add_field(name=f"{result[2]} {result[0]}", value=result[1], inline=False)
        embed.set_footer(text="Gomu Gomu no... Oops!")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 360, commands.BucketType.user)
    async def oceanforecast(self, ctx):
        """Get a whimsical Grand Line weather forecast."""
        conditions = [
            ("Candy Rain", "It's raining candy! Chopper is in heaven, but everyone's teeth hurt.", "🍬"),
            ("July Snow", "It's snowing in July. Nami's weather predictions are getting weirder by the day.", "❄️"),
            ("Upward Rain", "The rain is falling upwards. Gravity seems to be on vacation today.", "☔↑"),
            ("Sea King Fog", "It's foggy with a chance of Sea Kings. Keep your voices down and hope they don't notice the ship.", "🌫️🐉"),
            ("Buggy Weather", "It's partly cloudy with scattered Buggy parts. Duck to avoid flying noses!", "☁️🤡"),
            ("Whirlpool Sun", "It's sunny with a high chance of random whirlpools. Nami's navigation skills will be put to the test!", "☀️🌀"),
            ("Flying Fish Storm", "A storm is brewing, complete with flying fish. Sanji's excited about the self-delivering ingredients.", "⛈️🐟"),
            ("Suspicious Clear Skies", "The skies are suspiciously clear. Everyone's on edge waiting for the other shoe to drop.", "🌞🕵️"),
            ("Island Migration", "It's mild with roaming islands. Try not to crash into any mobile landmasses!", "🏝️🚶")
        ]
        temperatures = [
            "Hotter than Ace's flames 🔥", "Colder than Aokiji's heart 🧊", 
            "Warm as Luffy's smile 😄", "Cool as Zoro's swords 🗡️", 
            "The temperature is taking a day off 🏖️"
        ]
        warnings = [
            "Watch out for falling ships from Sky Islands! Skypiea spring cleaning is in full swing. ⚠️☁️⚓",
            "Beware of spontaneous Davy Back Fights! Foxy is feeling particularly mischievous today. 🏁🎭",
            "Caution: Roaming bands of singing pirates ahead! Bring earplugs or join the chorus. 🎵🏴‍☠️",
            "Alert: High chance of getting lost (especially if you're Zoro). We've tied a bell around Zoro for easy tracking. 🧭❓",
            "Warning: Increased Marine activity due to donut shortage at HQ. Akainu is hangry and on the warpath. 🍩🚔"
        ]
        
        condition = random.choice(conditions)
        temp = random.choice(temperatures)
        warning = random.choice(warnings)
        
        embed = discord.Embed(title="🌊 Grand Line Weather Forecast 🌊", color=discord.Color.blue())
        embed.add_field(name=f"{condition[2]} Condition", value=condition[1], inline=False)
        embed.add_field(name="🌡️ Temperature", value=temp, inline=False)
        embed.add_field(name="⚠️ Special Warning", value=warning, inline=False)
        embed.set_footer(text="Navigate safely, pirates! 🏴‍☠️")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def rumbleball(self, ctx):
        """Take a Rumble Ball and see what form you turn into!"""
        forms = [
            ("Brain Point 🧠", "Your intellect increases dramatically! You can now solve complex puzzles, but you're so cute that enemies want to pinch your cheeks instead of fight."),
            ("Walk Point 🏃", "You can now run at incredible speeds, but only in one direction. Hope you chose the right way!"),
            ("Heavy Point 💪", "You're super strong now! But be careful, you keep breaking chairs when you sit and doorways are your new arch-nemesis."),
            ("Guard Point 🛡️", "You're practically invincible, but you look like a giant walking hairball. Prepare for lots of petting and the occasional attempt to use you as a mop."),
            ("Horn Point 🦌", "Your antlers are amazing for digging and charging, but good luck fitting through doors or finding a hat that fits."),
            ("Jumping Point 🦘", "You can leap over tall buildings in a single bound! Landing gracefully, however, is a whole other story. Boing!"),
            ("Arm Point 💪", "Your arms are enormous and powerful! Arm wrestling is now your forte, but shirt shopping is a nightmare."),
            ("Monster Point 👹", "Oh no! You're gigantic and out of control! On the bright side, you're really good at remodeling islands now. Sorry about the property damage!"),
            ("Cuddle Point 🤗", "You're irresistibly huggable. Even the toughest enemies just want to snuggle you. This is either really good or really bad for combat."),
            ("Noodle Point 🍜", "You're incredibly flexible now! You can squeeze through any space, but standing upright is a constant struggle. Spaghetti has become your spirit animal.")
        ]
        form = random.choice(forms)
        
        embed = discord.Embed(title="💊 Rumble Ball Transformation 💊", color=discord.Color.green())
        embed.add_field(name=f"You turned into: {form[0]}", value=form[1], inline=False)
        embed.set_footer(text="Remember, you've got 3 minutes before you turn back! Use your new form wisely... or hilariously!")
        
        await ctx.send(embed=embed)

    @commands.command()
    async def createcrew(self, ctx, *, crew_name: str):
        user_id = str(ctx.author.id)
        async with self.config.guild(ctx.guild).all() as guild_data:
            bounties = guild_data['bounties']
            crews = guild_data['pirate_crews']

            if user_id not in bounties or bounties[user_id]['amount'] < 100000000:  # Pirate Captain threshold
                return await ctx.send("Ye need a bounty of at least 100,000,000 Berries to create a crew, ye rookie!")

            if crew_name in crews:
                return await ctx.send("That crew name already exists, ye unoriginal sea dog!")

            crews[crew_name] = {
                "captain": ctx.author.id,
                "members": [ctx.author.id],
                "created_at": datetime.utcnow().isoformat()
            }

        await ctx.send(f"The {crew_name} has been formed with {ctx.author.display_name} as the captain!")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def addtocrew(self, ctx, crew_name: str, member: discord.Member):
        """Add a member to an existing pirate crew."""
        async with self.config.guild(ctx.guild).pirate_crews() as crews:
            if crew_name not in crews:
                return await ctx.send(f"The {crew_name} doesn't exist! Have ye been drinkin' too much rum?")
            
            if member.id in crews[crew_name]["members"]:
                return await ctx.send(f"{member.display_name} is already part of the {crew_name}!")
            
            crews[crew_name]["members"].append(member.id)
        
        # Update the crew's total bounty
        await self.update_crew_bounty(ctx.guild, crew_name)
        
        await ctx.send(f"{member.display_name} has joined the {crew_name}! Welcome aboard, matey!")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def removefromcrew(self, ctx, crew_name: str, member: discord.Member):
        """Remove a member from a pirate crew."""
        async with self.config.guild(ctx.guild).pirate_crews() as crews:
            if crew_name not in crews:
                return await ctx.send(f"The {crew_name} doesn't exist! Are ye seein' ghost ships?")
            
            if member.id not in crews[crew_name]["members"]:
                return await ctx.send(f"{member.display_name} isn't part of the {crew_name}!")
            
            crews[crew_name]["members"].remove(member.id)
            
            if member.id == crews[crew_name]["captain"]:
                if crews[crew_name]["members"]:
                    new_captain_id = random.choice(crews[crew_name]["members"])
                    crews[crew_name]["captain"] = new_captain_id
                    new_captain = ctx.guild.get_member(new_captain_id)
                    await ctx.send(f"{member.display_name} has been removed from the {crew_name}!\n"
                                   f"{new_captain.display_name} is the new captain!")
                else:
                    del crews[crew_name]
                    await ctx.send(f"{member.display_name} has been removed and the {crew_name} has been disbanded!")
            else:
                await ctx.send(f"{member.display_name} has been removed from the {crew_name}!")
        
        # Update the crew's total bounty
        await self.update_crew_bounty(ctx.guild, crew_name)

    @commands.command()
    async def crewinfo(self, ctx, *, crew_name: str):
        """Display information about a pirate crew."""
        async with self.config.guild(ctx.guild).all() as guild_data:
            crews = guild_data["pirate_crews"]
            bounties = guild_data["bounties"]
            
            if crew_name not in crews:
                return await ctx.send(f"The {crew_name} doesn't exist! Are ye hallucinatin' from too much rum?")
            
            crew = crews[crew_name]
            
            # Update total_bounty if it's missing
            if "total_bounty" not in crew:
                crew["total_bounty"] = sum(bounties.get(str(member_id), {}).get("amount", 0) for member_id in crew["members"])
            
            captain = ctx.guild.get_member(crew["captain"])
            members = [ctx.guild.get_member(member_id) for member_id in crew["members"] if ctx.guild.get_member(member_id)]
            
            embed = discord.Embed(title=f"🏴‍☠️ {crew_name} Crew Info 🏴‍☠️", color=discord.Color.dark_red())
            embed.add_field(name="Captain", value=captain.mention if captain else "Unknown", inline=False)
            embed.add_field(name="Total Crew Bounty", value=f"{crew['total_bounty']:,} Berries", inline=False)
            embed.add_field(name="Crew Size", value=str(len(members)), inline=False)
            
            # Add created_at field if it exists, otherwise use "Unknown"
            created_at = crew.get("created_at", "Unknown")
            if created_at != "Unknown":
                created_at = discord.utils.format_dt(datetime.fromisoformat(created_at))
            embed.add_field(name="Founding Date", value=created_at, inline=False)
            
            member_list = "\n".join([member.mention for member in members[:10]])
            if len(members) > 10:
                member_list += f"\n... and {len(members) - 10} more scallywags!"
            embed.add_field(name="Crew Members", value=member_list or "No active members", inline=False)
            
            await ctx.send(embed=embed)

    async def update_crew_bounty(self, guild, crew_name):
        """Update the total bounty for a crew based on its members' individual bounties."""
        async with self.config.guild(guild).all() as guild_data:
            crews = guild_data["pirate_crews"]
            bounties = guild_data["bounties"]
            
            if crew_name in crews:
                total_bounty = sum(bounties.get(str(member_id), {}).get("amount", 0) for member_id in crews[crew_name]["members"])
                crews[crew_name]["total_bounty"] = total_bounty

    async def update_crew_bounty(self, guild, crew_name):
        """Update the total bounty for a crew based on its members' individual bounties."""
        async with self.config.guild(guild).all() as guild_data:
            crews = guild_data["pirate_crews"]
            bounties = guild_data["bounties"]
            
            if crew_name in crews:
                total_bounty = sum(bounties.get(str(member_id), {}).get("amount", 0) for member_id in crews[crew_name]["members"])
                crews[crew_name]["total_bounty"] = total_bounty

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def updateallcrews(self, ctx):
        """Update the total bounty for all crews."""
        async with self.config.guild(ctx.guild).all() as guild_data:
            crews = guild_data["pirate_crews"]
            bounties = guild_data["bounties"]
            
            for crew_name in crews:
                total_bounty = sum(bounties.get(str(member_id), {}).get("amount", 0) for member_id in crews[crew_name]["members"])
                crews[crew_name]["total_bounty"] = total_bounty
                
                if "created_at" not in crews[crew_name]:
                    crews[crew_name]["created_at"] = datetime.utcnow().isoformat()
        
        await ctx.send("All crew bounties and creation dates have been updated!")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def crewbattle(self, ctx, crew1: str, crew2: str):
        """Initiate a battle between two pirate crews."""
        async with self.config.guild(ctx.guild).all() as guild_data:
            crews = guild_data["pirate_crews"]
            bounties = guild_data["bounties"]
            
            if crew1 not in crews or crew2 not in crews:
                return await ctx.send("One or both of these crews don't exist! Check yer sea charts!")
            
            crew1_power = crews[crew1]["total_bounty"] * random.uniform(0.8, 1.2)
            crew2_power = crews[crew2]["total_bounty"] * random.uniform(0.8, 1.2)
            
            winner = crew1 if crew1_power > crew2_power else crew2
            loser = crew2 if winner == crew1 else crew1
            
            # Update bounties
            bounty_increase_percentage = random.uniform(0.05, 0.15)  # 5% to 15% increase
            bounty_decrease_percentage = random.uniform(0.02, 0.08)  # 2% to 8% decrease
            
            for member_id in crews[winner]["members"]:
                member_id_str = str(member_id)
                if member_id_str not in bounties:
                    bounties[member_id_str] = {"amount": 1000000}
                bounties[member_id_str]["amount"] += int(bounties[member_id_str]["amount"] * bounty_increase_percentage)
            
            for member_id in crews[loser]["members"]:
                member_id_str = str(member_id)
                if member_id_str in bounties:
                    bounties[member_id_str]["amount"] = max(0, int(bounties[member_id_str]["amount"] * (1 - bounty_decrease_percentage)))
            
            # Update crew bounties
            await self.update_crew_bounty(ctx.guild, winner)
            await self.update_crew_bounty(ctx.guild, loser)
        
        await ctx.send(f"⚔️ **Epic Crew Battle** ⚔️\n"
                       f"The {winner} have emerged victorious over the {loser}!\n"
                       f"The World Government has increased the bounties of the {winner} by {bounty_increase_percentage:.1%}!\n"
                       f"The {loser} have had their bounties decreased by {bounty_decrease_percentage:.1%}!")

    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def marineraid(self, ctx):
        """Initiate a Marine raid on the server."""
        channel = self.bot.get_channel(self.GENERAL_CHANNEL_ID)
        if not channel:
            return await ctx.send("Error: General channel not found. The Marines couldn't find their way!")
    
        marine_admirals = ["Akainu", "Aokiji", "Kizaru", "Fujitora", "Ryokugyu"]
        admiral = random.choice(marine_admirals)
    
        embed = discord.Embed(
            title="🚨 Marine Raid Alert 🚨",
            description=f"Admiral {admiral} has been spotted nearby! All pirates, prepare for battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="How to Participate", value="React with ⚔️ to join the battle against the Marines!")
        embed.set_footer(text="You have 5 minutes to prepare before the raid begins!")
    
        raid_msg = await channel.send(embed=embed)
        await raid_msg.add_reaction("⚔️")
    
        # Wait for reactions
        await asyncio.sleep(300)  # 5 minutes
    
        # Fetch the updated message to get all reactions
        raid_msg = await channel.fetch_message(raid_msg.id)
        
        # Get only the users who reacted (excluding bots)
        reaction = discord.utils.get(raid_msg.reactions, emoji="⚔️")
        if reaction:
            participants = [user async for user in reaction.users() if not user.bot]
        else:
            participants = []
    
        if not participants:
            await channel.send("No brave pirates stepped up to face the Marines. The raid was called off!")
            return
    
        # Determine outcomes
        num_captured = min(len(participants) // 2, 5)
        captured = random.sample(participants, k=num_captured)
        escaped = [p for p in participants if p not in captured]
    
        # Prepare result messages
        capture_message = "The Marines have captured:\n" + "\n".join([m.mention for m in captured]) if captured else "No pirates were captured this time!"
        escape_message = "These cunning pirates managed to escape:\n" + "\n".join([m.mention for m in escaped]) if escaped else "No pirates managed to escape!"
    
        # Send results
        result_embed = discord.Embed(
            title="Marine Raid Results",
            description=f"The battle against Admiral {admiral} has concluded!",
            color=discord.Color.blue()
        )
        result_embed.add_field(name="Captured Pirates", value=capture_message, inline=False)
        result_embed.add_field(name="Escaped Pirates", value=escape_message, inline=False)
    
        await channel.send(embed=result_embed)
    
        # Update bounties for escaped pirates
        async with self.config.guild(ctx.guild).bounties() as bounties:
            for member in escaped:
                if str(member.id) not in bounties:
                    bounties[str(member.id)] = {"amount": 1000000}
                bounties[str(member.id)]["amount"] += random.randint(1000, 5000)  # Lowered reward
    
        if escaped:
            await channel.send("The bounties of the escaped pirates have been slightly increased!")
            
    @commands.command()
    @checks.mod_or_permissions(manage_messages=True)
    async def islandexpedition(self, ctx):
        """Start a random island expedition event."""
        islands = [
            "Mysterious Fog Island", "Prehistoric Dinosaur Island", "Golden Treasury Island",
            "Perpetual Winter Island", "Sky Island", "Underwater Island Dome"
        ]
        island = random.choice(islands)
        
        treasures = [
            "ancient poneglyph", "cursed sword", "eternal log pose", "chest of gold",
            "mysterious devil fruit", "advanced technology blueprint"
        ]
        treasure = random.choice(treasures)

        channel = self.bot.get_channel(self.GENERAL_CHANNEL_ID)
        if not channel:
            return await ctx.send("Error: General channel not found. The expedition is lost at sea!")

        await channel.send(f"🏝️ **Island Expedition Event** 🏝️\n"
                           f"A {island} has been discovered! Who will be the first to claim its treasures?")

        # Give users time to participate (simulated by waiting)
        await asyncio.sleep(3600)  # 1 hour

        winners = random.sample(ctx.guild.members, k=min(3, len(ctx.guild.members)))
        
        result_message = f"The expedition to {island} has concluded!\n\n"
        result_message += f"The brave pirates {', '.join([w.mention for w in winners])} have discovered a {treasure}!\n"
        result_message += "Their bounties have been increased for this remarkable find!"

        await channel.send(result_message)

        # Update bounties for winners
        async with self.config.guild(ctx.guild).bounties() as bounties:
            for winner in winners:
                if str(winner.id) not in bounties:
                    bounties[str(winner.id)] = {"amount": 1000000}
                bounties[str(winner.id)]["amount"] += random.randint(5000000, 20000000)

    @commands.command()
    async def wanted(self, ctx, member: discord.Member = None):
        """Generate a wanted poster for a user."""
        member = member or ctx.author
        
        # Correctly retrieve the bounty information
        bounties = await self.config.guild(ctx.guild).bounties()
        bounty = bounties.get(str(member.id), {}).get("amount", 0)
        
        poster = f"""
╔══════════════════════╗
║     WANTED ALIVE     ║
║ ╔══════════════════╗ ║
║ ║                  ║ ║
║ ║                  ║ ║
║ ║   {member.name[:14].center(14)} ║ ║
║ ║                  ║ ║
║ ║                  ║ ║
║ ╚══════════════════╝ ║
║                      ║
║  {f'{bounty:,}'.center(20)}║
║        BERRIES       ║
╚══════════════════════╝
"""
        await ctx.send(box(poster))

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def berryflip(self, ctx, bet: int, choice: str = None):
        """
        Flip a Berry coin and test your luck! Bet from your current bounty.
        Usage: .berryflip <amount> [heads/tails]
        If no choice is made, it defaults to heads.
        """
        if bet < 1 or bet > 5000:
            return await ctx.send("Ye can only bet between 1 and 5000 Berries, ye greedy sea dog!")
    
        user_id = str(ctx.author.id)
        
        if choice is None:
            choice = 'heads'
        choice = choice.lower()
        
        if choice not in ['heads', 'tails']:
            return await ctx.send("Ye must choose 'heads' or 'tails', ye indecisive sea dog!")
    
        async with self.config.guild(ctx.guild).all() as guild_data:
            bounties = guild_data['bounties']
            gambling_stats = guild_data.get('gambling_stats', {})
            double_payout = guild_data.get('double_payout_event', False)
            last_flip = guild_data.get('last_berryflip', {}).get(user_id)
    
            if last_flip:
                last_flip_time = datetime.fromisoformat(last_flip)
                if datetime.utcnow() - last_flip_time < timedelta(days=1):
                    time_left = timedelta(days=1) - (datetime.utcnow() - last_flip_time)
                    return await ctx.send(f"Ye must wait {time_left.seconds // 3600} hours and {(time_left.seconds // 60) % 60} minutes before ye can flip again!")
    
            if user_id not in bounties:
                return await ctx.send("Ye don't have a bounty yet, ye rookie! Go cause some trouble first!")
            
            current_bounty = bounties[user_id]['amount']
            
            if bet > current_bounty:
                return await ctx.send(f"Ye can't bet more than yer bounty of {current_bounty:,} Berries, ye greedy landlubber!")
            
            flip = random.choice(["heads", "tails"])
            
            if flip == choice:
                winnings = bet * 2  # Double the bet
                if double_payout:
                    winnings *= 2  # Double again if special event is active
                new_bounty = current_bounty + winnings
                bounties[user_id]['amount'] = new_bounty
                result = f"Ye won {winnings:,} Berries! Yer new bounty is {new_bounty:,} Berries! The Marines will be after ye soon!"
                
                # Update gambling stats
                if user_id not in gambling_stats:
                    gambling_stats[user_id] = {"wins": 0, "losses": 0, "net_gain": 0}
                gambling_stats[user_id]["wins"] += 1
                gambling_stats[user_id]["net_gain"] += winnings
            else:
                new_bounty = max(0, current_bounty - bet)  # Ensure bounty doesn't go negative
                bounties[user_id]['amount'] = new_bounty
                result = f"Ye lost {bet:,} Berries! Yer new bounty is {new_bounty:,} Berries! Better luck next time, ye landlubber!"
                
                # Update gambling stats
                if user_id not in gambling_stats:
                    gambling_stats[user_id] = {"wins": 0, "losses": 0, "net_gain": 0}
                gambling_stats[user_id]["losses"] += 1
                gambling_stats[user_id]["net_gain"] -= bet
    
            guild_data['gambling_stats'] = gambling_stats
            guild_data['last_berryflip'][user_id] = datetime.utcnow().isoformat()
    
        embed = discord.Embed(title="🪙 Berry Flip 🪙", color=discord.Color.gold())
        embed.add_field(name="The Flip", value=f"The Berry coin flips through the air and lands on... {flip}!", inline=False)
        embed.add_field(name="Result", value=result, inline=False)
        if double_payout:
            embed.add_field(name="Special Event", value="Double Payout Event is active! All winnings are doubled!", inline=False)
        embed.set_footer(text=f"Current Bounty: {new_bounty:,} Berries")
        
        await ctx.send(embed=embed)
        
    @commands.command()
    async def gamblelb(self, ctx):
        """Display the gambling leaderboard."""
        async with self.config.guild(ctx.guild).gambling_stats() as gambling_stats:
            sorted_stats = sorted(gambling_stats.items(), key=lambda x: x[1]['net_gain'], reverse=True)[:10]
            
            embed = discord.Embed(title="🏆 Gambling Leaderboard 🏆", color=discord.Color.gold())
            for i, (user_id, stats) in enumerate(sorted_stats, 1):
                user = ctx.guild.get_member(int(user_id))
                if user:
                    embed.add_field(
                        name=f"{i}. {user.display_name}",
                        value=f"Net Gain: {stats['net_gain']:,} Berries\nWins: {stats['wins']}\nLosses: {stats['losses']}",
                        inline=False
                    )
            
            await ctx.send(embed=embed)

    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def startdoublepayout(self, ctx, duration: int):
        """Start a double payout event for a specified number of minutes."""
        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data['double_payout_event'] = True
            guild_data['double_payout_end_time'] = (datetime.utcnow() + timedelta(minutes=duration)).isoformat()

        await ctx.send(f"🎉 Double Payout Event has started! All gambling winnings will be doubled for the next {duration} minutes!")

        # Schedule the event to end
        await self.schedule_double_payout_end(ctx.guild, duration)

    async def schedule_double_payout_end(self, guild, duration):
        await asyncio.sleep(duration * 60)
        async with self.config.guild(guild).all() as guild_data:
            guild_data['double_payout_event'] = False
            guild_data['double_payout_end_time'] = None
        
        # Announce the end of the event in the general channel
        general_channel = self.bot.get_channel(self.GENERAL_CHANNEL_ID)
        if general_channel:
            await general_channel.send("🏁 The Double Payout Event has ended! Gambling winnings have returned to normal.")

    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def worldGovernmentDecree(self, ctx, *, decree: str):
        """Make an official 'World Government' announcement."""
        embed = discord.Embed(
            title="🌐 World Government Official Decree 🌐",
            description=decree,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Issued by Celestial Dragon {ctx.author.display_name}")
        embed.set_thumbnail(url="https://static.wikia.nocookie.net/onepiece/images/a/a1/World_Government_Infobox.png")  # World Government logo
        
        # Send to all channels with 'announcement' in the name
        announcement_channels = [channel for channel in ctx.guild.text_channels if 'announcement' in channel.name.lower()]
        if not announcement_channels:
            await ctx.send("No announcement channels found. Sending decree here.")
            await ctx.send(embed=embed)
        else:
            for channel in announcement_channels:
                await channel.send(embed=embed)
            await ctx.send(f"Decree sent to {len(announcement_channels)} announcement channel(s).")

    @commands.command()
    @checks.mod_or_permissions(manage_channels=True)
    async def seaKingAlert(self, ctx, channel: discord.TextChannel = None):
        """Simulate a Sea King attack on a specific channel or the current channel."""
        if channel is None:
            channel = ctx.channel

        alert_active = await self.config.guild(ctx.guild).sea_king_alert()
        if alert_active:
            await ctx.send("A Sea King is already attacking! Deal with that one first!")
            return

        await self.config.guild(ctx.guild).sea_king_alert.set(True)

        sea_king_images = [
            "https://www.dexerto.com/cdn-cgi/image/width=1080,quality=75,format=auto/https://editors.dexerto.com/wp-content/uploads/2023/06/21/one-piece-sea-king-and-luffy-1024x576.jpeg",
            "https://www.dexerto.com/cdn-cgi/image/width=1080,quality=75,format=auto/https://editors.dexerto.com/wp-content/uploads/2023/06/21/one-piece-poseidon-ancient-weapon-1024x576.jpeg",
            "https://static.wikia.nocookie.net/onepiece/images/e/e2/Sea_King_Infobox.png"
        ]
        sea_king_image = random.choice(sea_king_images)

        embed = discord.Embed(title="🌊🐉 SEA KING ALERT 🐉🌊", color=discord.Color.blue())
        embed.set_image(url=sea_king_image)
        await channel.send(embed=embed)

        messages = [
            "A massive Sea King has appeared!",
            "All conversations in this channel are interrupted!",
            "Quick, someone call for Luffy!",
            "The Sea King is eyeing the ship hungrily!",
            "Prepare for evasive maneuvers!",
            "Where's a Calm Belt when you need one?!"
        ]

        for message in messages:
            await channel.send(message)
            await asyncio.sleep(2)

        # Restrict messaging in the channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await channel.send("The Sea King has temporarily halted all communication in this channel!")

        # Wait for 5 minutes
        await asyncio.sleep(300)

        # Re-enable messaging
        await channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await channel.send("The Sea King has been defeated! Normal communications can resume.")

        await self.config.guild(ctx.guild).sea_king_alert.set(False)
    
    @commands.command()
    @checks.admin_or_permissions(manage_guild=True)
    async def admiralInspection(self, ctx):
        """Trigger a surprise 'Admiral Inspection' of the server."""
        inspection_active = await self.config.guild(ctx.guild).inspection_active()
        if inspection_active:
            await ctx.send("An inspection is already in progress!")
            return

        await self.config.guild(ctx.guild).inspection_active.set(True)

        admirals = {
            "Akainu": "https://static.wikia.nocookie.net/onepiece/images/5/5b/Sakazuki_Pre_Timeskip_Portrait.png",
            "Aokiji": "https://static.wikia.nocookie.net/onepiece/images/5/5a/Kuzan_Pre_Timeskip_Portrait.png",
            "Kizaru": "https://static.wikia.nocookie.net/onepiece/images/9/97/Borsalino_Portrait.png",
            "Fujitora": "https://static.wikia.nocookie.net/onepiece/images/d/db/Issho_Portrait.png",
            "Ryokugyu": "https://static.wikia.nocookie.net/onepiece/images/a/a2/Aramaki_Portrait.png"
        }
        admiral, image_url = random.choice(list(admirals.items()))
        
        embed = discord.Embed(
            title=f"🎖️ Admiral {admiral} Inspection 🎖️",
            description=(
                f"Admiral {admiral} is conducting a surprise inspection of our base!\n"
                "All Marines, stand at attention! Pirates, try to act natural!\n"
                "The Admiral will be checking all channels for the next hour."
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url=image_url)
        
        # Send to all text channels
        for channel in ctx.guild.text_channels:
            await channel.send(embed=embed)

        # Simulated inspection
        inspection_messages = [
            "Admiral {} is checking the weapon stocks...",
            "Admiral {} is reviewing the wanted posters...",
            "Admiral {} is inspecting the ship's log...",
            "Admiral {} is testing the Den Den Mushi network...",
            "Admiral {} is evaluating the base's defenses..."
        ]

        try:
            for _ in range(5):  # Send 5 inspection updates
                await asyncio.sleep(600)  # Wait 10 minutes between updates
                channel = random.choice(ctx.guild.text_channels)
                message = random.choice(inspection_messages).format(admiral)
                await channel.send(message)
        except Exception as e:
            await ctx.send(f"An error occurred during the inspection: {str(e)}")
        finally:
            # End the inspection
            await ctx.send(f"Admiral {admiral} has completed the inspection and left the base.")
            await self.config.guild(ctx.guild).inspection_active.set(False)
            
async def setup(bot):
    await bot.add_cog(OnePieceFun(bot))
