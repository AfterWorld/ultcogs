import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import discord
import yaml
from discord.ext import tasks
from redbot.core import commands, Config, checks, data_manager
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify


class OnePieceMaster(commands.Cog):
    """Master One Piece engagement system with daily challenges and trivia!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1111222233334444)
        
        # Paths for data files
        self.cog_data_path = Path(data_manager.cog_data_path(self))
        self.challenges_path = self.cog_data_path / "challenges"
        self.trivia_path = self.cog_data_path / "trivia"
        self.constants_path = self.cog_data_path / "constants.yaml"
        
        # Create directories if they don't exist
        self.challenges_path.mkdir(parents=True, exist_ok=True)
        self.trivia_path.mkdir(parents=True, exist_ok=True)
        
        # Default guild settings
        default_guild = {
            "challenge_channel": None,
            "trivia_channel": None,
            "daily_challenges": True,
            "auto_trivia": False,
            "challenge_time": "12:00",
            "trivia_interval": 3600,
            "current_daily": None,
            "current_weekly": None,
            "weekly_day": 1,
            "participants": {},
            "trivia_leaderboard": {},
            "challenge_rewards": True,
            "points_per_daily": 10,
            "points_per_trivia": 15,
            "weekly_tournament": False,
            "tournament_day": 6
        }
        
        # Default user settings
        default_user = {
            "total_points": 0,
            "daily_streak": 0,
            "trivia_correct": 0,
            "trivia_attempted": 0,
            "favorite_category": None,
            "achievements": []
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        # Cache for loaded data
        self.constants = {}
        self.daily_challenges = {}
        self.weekly_challenges = {}
        self.trivia_data = {}
        
        # Load all data files
        self.load_all_data()
        
        # Start background tasks
        self.daily_challenge_task.start()
        self.auto_trivia_task.start()

    def cog_unload(self):
        self.daily_challenge_task.cancel()
        self.auto_trivia_task.cancel()

    def load_all_data(self):
        """Load all data files into memory"""
        self.load_constants()
        self.load_challenges()
        self.load_trivia_data()

    def load_constants(self):
        """Load constants from file or create default"""
        if not self.constants_path.exists():
            self.create_default_constants()
        
        try:
            with open(self.constants_path, 'r', encoding='utf-8') as f:
                self.constants = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading constants: {e}")
            self.create_default_constants()

    def create_default_constants(self):
        """Create default constants file"""
        default_constants = {
            "characters": {
                "straw_hats": ["luffy", "zoro", "nami", "usopp", "sanji", "chopper", "robin", "franky", "brook", "jinbe"],
                "emperors": ["shanks", "kaido", "big mom", "blackbeard"],
                "admirals": ["akainu", "kizaru", "aokiji", "fujitora", "ryokugyu"],
                "warlords": ["mihawk", "crocodile", "doflamingo", "hancock", "jinbe", "law", "weevil"]
            },
            "locations": {
                "islands": ["alabasta", "skypiea", "water 7", "thriller bark", "sabaody", "amazon lily", "impel down", "marineford", "fishman island", "punk hazard", "dressrosa", "zou", "whole cake island", "wano"],
                "seas": ["east blue", "west blue", "north blue", "south blue", "grand line", "new world"],
                "special_places": ["reverse mountain", "calm belt", "red line", "marie geoise", "enies lobby"]
            },
            "devil_fruits": {
                "paramecia": ["gomu gomu", "bara bara", "sube sube", "bomu bomu", "kiro kiro"],
                "zoan": ["hito hito", "tori tori", "inu inu", "neko neko", "ushi ushi"],
                "logia": ["moku moku", "mera mera", "suna suna", "goro goro", "hie hie"]
            },
            "emojis": {
                "luffy": "🍖",
                "zoro": "⚔️",
                "nami": "🍊",
                "usopp": "🎯",
                "sanji": "🚬",
                "chopper": "🦌",
                "robin": "📚",
                "franky": "🤖",
                "brook": "💀",
                "jinbe": "🐠",
                "ace": "🔥",
                "law": "⚕️",
                "kidd": "🧲",
                "shanks": "🦾",
                "whitebeard": "⚡",
                "kaido": "🐉"
            },
            "difficulty_colors": {
                "easy": 0x00ff00,
                "medium": 0xff8000,
                "hard": 0xff0000,
                "expert": 0x8b00ff
            },
            "point_values": {
                "easy_trivia": 10,
                "medium_trivia": 20,
                "hard_trivia": 30,
                "expert_trivia": 50,
                "daily_challenge": 15,
                "weekly_challenge": 75,
                "streak_bonus": 5
            }
        }
        
        with open(self.constants_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_constants, f, default_flow_style=False, allow_unicode=True)
        
        self.constants = default_constants

    def load_challenges(self):
        """Load challenge files"""
        # Create default challenge files if they don't exist
        self.create_default_challenges()
        
        # Load daily challenges
        daily_file = self.challenges_path / "daily_challenges.yaml"
        if daily_file.exists():
            with open(daily_file, 'r', encoding='utf-8') as f:
                self.daily_challenges = yaml.safe_load(f)
        
        # Load weekly challenges
        weekly_file = self.challenges_path / "weekly_challenges.yaml"
        if weekly_file.exists():
            with open(weekly_file, 'r', encoding='utf-8') as f:
                self.weekly_challenges = yaml.safe_load(f)

    def create_default_challenges(self):
        """Create default challenge files"""
        daily_challenges = {
            "discussion": [
                {
                    "prompt": "What's your favorite Devil Fruit power and why?",
                    "category": "powers",
                    "difficulty": "easy"
                },
                {
                    "prompt": "If you could join any pirate crew, which would it be?",
                    "category": "crews",
                    "difficulty": "easy"
                },
                {
                    "prompt": "What do you think is the most emotional One Piece moment?",
                    "category": "emotions",
                    "difficulty": "medium"
                }
            ],
            "creative": [
                {
                    "prompt": "Draw or describe your own pirate flag design!",
                    "category": "art",
                    "difficulty": "medium"
                },
                {
                    "prompt": "Create a new Devil Fruit and describe its powers!",
                    "category": "powers",
                    "difficulty": "medium"
                },
                {
                    "prompt": "Design a new island for the Straw Hats to visit!",
                    "category": "worldbuilding",
                    "difficulty": "hard"
                }
            ],
            "trivia": [
                {
                    "prompt": "Name 3 members of the Worst Generation",
                    "answers": ["luffy", "zoro", "law", "kidd", "killer", "hawkins", "drake", "apoo", "bonney", "bege", "urouge"],
                    "min_correct": 3,
                    "difficulty": "medium"
                },
                {
                    "prompt": "List 5 Straw Hat Pirates in order of joining",
                    "answers": ["luffy", "zoro", "nami", "usopp", "sanji", "chopper", "robin", "franky", "brook", "jinbe"],
                    "min_correct": 5,
                    "difficulty": "easy"
                }
            ],
            "scenario": [
                {
                    "prompt": "You're stuck on a deserted island with one Straw Hat member. Who do you choose and why?",
                    "category": "survival",
                    "difficulty": "easy"
                },
                {
                    "prompt": "You have to defend your hometown from pirates. Which 3 One Piece characters do you recruit?",
                    "category": "strategy",
                    "difficulty": "medium"
                }
            ]
        }
        
        weekly_challenges = {
            "contests": [
                {
                    "title": "Best One Piece Fan Art Contest",
                    "description": "Create original One Piece artwork",
                    "theme": "Adventure",
                    "duration": 7,
                    "category": "art"
                },
                {
                    "title": "Ultimate Fight Tournament",
                    "description": "Vote for the best One Piece battles",
                    "theme": "Epic Battles",
                    "duration": 7,
                    "category": "tournament"
                }
            ],
            "analysis": [
                {
                    "title": "Character Deep Dive Week",
                    "description": "Analyze character development and growth",
                    "theme": "Character Analysis",
                    "duration": 7,
                    "category": "analysis"
                }
            ],
            "theory": [
                {
                    "title": "Theory Crafting Week",
                    "description": "Share your wildest One Piece theories",
                    "theme": "Predictions",
                    "duration": 7,
                    "category": "theory"
                }
            ]
        }
        
        # Save files
        with open(self.challenges_path / "daily_challenges.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(daily_challenges, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.challenges_path / "weekly_challenges.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(weekly_challenges, f, default_flow_style=False, allow_unicode=True)

    def load_trivia_data(self):
        """Load trivia data files"""
        # Create default trivia if it doesn't exist
        self.create_default_trivia()
        
        # Load all trivia files
        for trivia_file in self.trivia_path.glob("*.yaml"):
            difficulty = trivia_file.stem
            with open(trivia_file, 'r', encoding='utf-8') as f:
                self.trivia_data[difficulty] = yaml.safe_load(f)

    def create_default_trivia(self):
        """Create default trivia files"""
        easy_trivia = {
            "general": [
                {
                    "question": "What is Luffy's dream?",
                    "answers": ["to become pirate king", "pirate king", "become the pirate king"],
                    "category": "dreams"
                },
                {
                    "question": "Who is the navigator of the Straw Hat Pirates?",
                    "answers": ["nami"],
                    "category": "crew"
                },
                {
                    "question": "What Devil Fruit did Luffy eat?",
                    "answers": ["gomu gomu no mi", "rubber fruit", "gum gum fruit"],
                    "category": "powers"
                }
            ],
            "characters": [
                {
                    "question": "What color is Zoro's hair?",
                    "answers": ["green"],
                    "category": "appearance"
                },
                {
                    "question": "What does Sanji love to cook?",
                    "answers": ["food", "anything", "everything"],
                    "category": "personality"
                }
            ]
        }
        
        medium_trivia = {
            "general": [
                {
                    "question": "What is the name of Law's submarine?",
                    "answers": ["polar tang"],
                    "category": "ships"
                },
                {
                    "question": "Which island is known as the 'Island of Women'?",
                    "answers": ["amazon lily"],
                    "category": "locations"
                }
            ],
            "powers": [
                {
                    "question": "What type of Devil Fruit did Ace eat?",
                    "answers": ["logia", "fire logia", "mera mera no mi"],
                    "category": "devil_fruits"
                }
            ]
        }
        
        hard_trivia = {
            "general": [
                {
                    "question": "What was the first island the Straw Hats visited in the New World?",
                    "answers": ["fishman island", "fish-man island"],
                    "category": "locations"
                },
                {
                    "question": "Who was the first person to call Luffy 'Straw Hat'?",
                    "answers": ["mihawk", "dracule mihawk"],
                    "category": "nicknames"
                }
            ]
        }
        
        # Save trivia files
        with open(self.trivia_path / "easy.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(easy_trivia, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.trivia_path / "medium.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(medium_trivia, f, default_flow_style=False, allow_unicode=True)
        
        with open(self.trivia_path / "hard.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(hard_trivia, f, default_flow_style=False, allow_unicode=True)

    @tasks.loop(minutes=5)
    async def daily_challenge_task(self):
        """Check for daily challenge time"""
        for guild_id in await self.config.all_guilds():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            guild_config = await self.config.guild(guild).all()
            if not guild_config["daily_challenges"]:
                continue
                
            # Check if it's time for daily challenge
            now = datetime.now()
            target_time = datetime.strptime(guild_config["challenge_time"], "%H:%M").time()
            
            if (now.time().hour == target_time.hour and 
                now.time().minute == target_time.minute and
                guild_config["current_daily"] != now.strftime("%Y-%m-%d")):
                
                await self.post_daily_challenge(guild)

    @tasks.loop(minutes=30)
    async def auto_trivia_task(self):
        """Auto trivia posting"""
        for guild_id in await self.config.all_guilds():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            guild_config = await self.config.guild(guild).all()
            if not guild_config["auto_trivia"]:
                continue
                
            # Check if enough time has passed since last trivia
            now = datetime.now()
            last_trivia_key = f"last_auto_trivia_{guild_id}"
            
            # Get last trivia time from config
            last_trivia = await self.config.guild(guild).get_raw("last_auto_trivia", default=None)
            
            if last_trivia is None:
                # First time - post trivia and set timestamp
                await self.post_auto_trivia(guild)
                await self.config.guild(guild).set_raw("last_auto_trivia", value=now.timestamp())
                continue
            
            # Convert timestamp back to datetime
            last_trivia_time = datetime.fromtimestamp(last_trivia)
            time_diff = (now - last_trivia_time).total_seconds()
            
            # Check if enough time has passed (default 1 hour)
            if time_diff >= guild_config["trivia_interval"]:
                await self.post_auto_trivia(guild)
                await self.config.guild(guild).set_raw("last_auto_trivia", value=now.timestamp())

    async def post_daily_challenge(self, guild: discord.Guild):
        """Post today's daily challenge"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["challenge_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
            
        # Select random challenge type and challenge
        challenge_type = random.choice(list(self.daily_challenges.keys()))
        challenge = random.choice(self.daily_challenges[challenge_type])
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create challenge embed
        embed = discord.Embed(
            title="🏴‍☠️ Straw Hat Challenge of the Day!",
            description=challenge["prompt"],
            color=discord.Color(self.constants["difficulty_colors"][challenge.get("difficulty", "easy")]),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📝 Challenge Type",
            value=challenge_type.title(),
            inline=True
        )
        
        embed.add_field(
            name="🏆 Reward",
            value=f"{guild_config['points_per_daily']} Berries",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Deadline",
            value="Before tomorrow's challenge!",
            inline=True
        )
        
        embed.add_field(
            name="📝 How to Participate",
            value="React with ⚓ and share your response!",
            inline=False
        )
        
        embed.set_footer(text=f"Category: {challenge.get('category', 'General').title()}")
        
        try:
            message = await channel.send(embed=embed)
            await message.add_reaction("⚓")
            
            # Update config
            await self.config.guild(guild).current_daily.set(today)
            
        except discord.Forbidden:
            pass

    async def post_auto_trivia(self, guild: discord.Guild):
        """Post automatic trivia question"""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["trivia_channel"]
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return
            
        # Select random difficulty and category
        difficulties = list(self.trivia_data.keys())
        if not difficulties:
            return
            
        difficulty = random.choice(difficulties)
        trivia_set = self.trivia_data[difficulty]
        
        if not trivia_set:
            return
            
        category = random.choice(list(trivia_set.keys()))
        question_data = random.choice(trivia_set[category])
        
        # Create trivia embed
        embed = discord.Embed(
            title="🧠 Auto One Piece Trivia!",
            description=question_data["question"],
            color=discord.Color(self.constants["difficulty_colors"][difficulty])
        )
        embed.add_field(name="⏰ Time Limit", value="45 seconds", inline=True)
        embed.add_field(name="🏆 Points", value=str(self.constants["point_values"][f"{difficulty}_trivia"]), inline=True)
        embed.add_field(name="📂 Category", value=question_data.get("category", "General").title(), inline=True)
        embed.add_field(name="🎯 Difficulty", value=difficulty.title(), inline=True)
        embed.set_footer(text="First to answer correctly wins! 🏴‍☠️")
        
        try:
            message = await channel.send("🚨 **SUDDEN TRIVIA ATTACK!** 🚨", embed=embed)
            
            def check(m):
                return (m.channel == channel and 
                       any(answer.lower() in m.content.lower() 
                           for answer in question_data["answers"]))
            
            try:
                response = await self.bot.wait_for('message', timeout=45.0, check=check)
                
                # Award points
                points = self.constants["point_values"][f"{difficulty}_trivia"]
                await self.add_user_points(response.author, points)
                
                # Update user stats
                user_data = await self.config.user(response.author).all()
                await self.config.user(response.author).trivia_correct.set(user_data["trivia_correct"] + 1)
                await self.config.user(response.author).trivia_attempted.set(user_data["trivia_attempted"] + 1)
                
                # Winner embed
                win_embed = discord.Embed(
                    title="🎉 Lightning Round Winner!",
                    description=f"{response.author.mention} was fastest!",
                    color=discord.Color.green()
                )
                win_embed.add_field(name="✅ Answer", value=question_data["answers"][0].title(), inline=True)
                win_embed.add_field(name="🏆 Points Earned", value=str(points), inline=True)
                win_embed.add_field(name="⚡ Speed Bonus", value="+5 points", inline=True)
                
                # Speed bonus for auto trivia
                await self.add_user_points(response.author, 5)
                
                await channel.send(embed=win_embed)
                
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ No One Got It!",
                    description=f"The answer was: **{question_data['answers'][0].title()}**",
                    color=discord.Color.orange()
                )
                timeout_embed.add_field(name="🤔 Better luck next time!", value="Stay sharp for the next surprise trivia!", inline=False)
                await channel.send(embed=timeout_embed)
                
        except discord.Forbidden:
            pass

    @commands.group(name="onepiece", aliases=["op"])
    async def onepiece(self, ctx):
        """One Piece engagement system commands"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="🏴‍☠️ One Piece Engagement Hub",
                description="Welcome to the ultimate One Piece server experience!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🎯 Daily Challenges",
                value="`[p]op challenge` - Today's challenge\n"
                      "`[p]op challenges` - Challenge commands",
                inline=True
            )
            embed.add_field(
                name="🧠 Trivia Games",
                value="`[p]op trivia` - Start trivia\n"
                      "`[p]op quiz [difficulty]` - Quick quiz",
                inline=True
            )
            embed.add_field(
                name="📊 Stats & Leaderboards",
                value="`[p]op stats` - Your stats\n"
                      "`[p]op leaderboard` - Top players",
                inline=True
            )
            await ctx.send(embed=embed)

    @onepiece.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx, scope: str = "server"):
        """Show the One Piece trivia leaderboard"""
        if scope.lower() not in ["server", "global"]:
            scope = "server"
            
        if scope.lower() == "server":
            # Server leaderboard
            all_users = await self.config.all_users()
            server_members = [member.id for member in ctx.guild.members]
            
            # Filter to only server members
            server_data = {user_id: data for user_id, data in all_users.items() 
                          if user_id in server_members and data.get('total_points', 0) > 0}
        else:
            # Global leaderboard
            server_data = await self.config.all_users()
            server_data = {user_id: data for user_id, data in server_data.items() 
                          if data.get('total_points', 0) > 0}
        
        if not server_data:
            await ctx.send("No one has earned points yet! Start playing trivia! 🏴‍☠️")
            return
        
        # Sort by total points
        sorted_users = sorted(server_data.items(), key=lambda x: x[1]['total_points'], reverse=True)
        
        embed = discord.Embed(
            title=f"🏆 {scope.title()} One Piece Leaderboard",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        for i, (user_id, data) in enumerate(sorted_users[:10], 1):
            user = self.bot.get_user(user_id)
            if user is None:
                continue
                
            points = data['total_points']
            accuracy = 0
            if data.get('trivia_attempted', 0) > 0:
                accuracy = (data.get('trivia_correct', 0) / data['trivia_attempted']) * 100
            
            # Get rank title
            rank_title = self.get_rank_title(points)
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            leaderboard_text += f"{medal} **{user.display_name}**\n"
            leaderboard_text += f"   💰 {points:,} berries | 🎯 {accuracy:.1f}% | {rank_title}\n\n"
        
        embed.description = leaderboard_text
        
        # Add user's position if not in top 10
        user_position = None
        for i, (user_id, _) in enumerate(sorted_users, 1):
            if user_id == ctx.author.id:
                user_position = i
                break
        
        if user_position and user_position > 10:
            user_data = await self.config.user(ctx.author).all()
            user_accuracy = 0
            if user_data['trivia_attempted'] > 0:
                user_accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
            
            embed.add_field(
                name="📍 Your Position",
                value=f"#{user_position} - {user_data['total_points']:,} berries ({user_accuracy:.1f}%)",
                inline=False
            )
        
        await ctx.send(embed=embed)

    def get_rank_title(self, points: int) -> str:
        """Get rank title based on points"""
        rank_thresholds = [
            (20000, "Pirate King Candidate"),
            (10000, "Yonko Level"),
            (5000, "Emperor Commander"),
            (2000, "Warlord Level"),
            (1000, "Supernova"),
            (500, "New World Pirate"),
            (300, "Grand Line Traveler"),
            (100, "East Blue Veteran"),
            (0, "Rookie Pirate")
        ]
        
        for threshold, title in rank_thresholds:
            if points >= threshold:
                return title
        return "Rookie Pirate"

    @onepiece.command(name="daily")
    async def today_challenge(self, ctx):
        """Show today's challenge if there is one"""
        guild_config = await self.config.guild(ctx.guild).all()
        channel_id = guild_config["challenge_channel"]
        
        if not channel_id:
            await ctx.send("❌ No challenge channel set! Ask an admin to set one up.")
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        current_daily = guild_config.get("current_daily")
        
        if current_daily != today:
            await ctx.send("🤔 No challenge posted today yet! Check back later or ask an admin to post one.")
            return
        
        channel = ctx.guild.get_channel(channel_id)
        if channel:
            await ctx.send(f"📍 Today's challenge is in {channel.mention}!")
        else:
            await ctx.send("❌ Challenge channel not found!")

    @onepiece.command(name="profile", aliases=["rank"])
    async def user_profile(self, ctx, user: discord.Member = None):
        """Show detailed user profile and achievements"""
        if user is None:
            user = ctx.author
            
        user_data = await self.config.user(user).all()
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {user.display_name}'s Pirate Profile",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        # Basic stats
        points = user_data['total_points']
        rank_title = self.get_rank_title(points)
        
        embed.add_field(
            name="👑 Pirate Rank",
            value=rank_title,
            inline=True
        )
        
        embed.add_field(
            name="💰 Total Berries",
            value=f"{points:,}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"{user_data['daily_streak']} days",
            inline=True
        )
        
        # Trivia stats
        if user_data['trivia_attempted'] > 0:
            accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
        else:
            accuracy = 0
            
        embed.add_field(
            name="🧠 Trivia Stats",
            value=f"✅ {user_data['trivia_correct']} correct\n"
                  f"❓ {user_data['trivia_attempted']} attempted\n"
                  f"🎯 {accuracy:.1f}% accuracy",
            inline=True
        )
        
        # Achievements
        achievements = user_data.get('achievements', [])
        if achievements:
            embed.add_field(
                name="🏆 Recent Achievements",
                value="\n".join(achievements[-3:]),  # Show last 3
                inline=True
            )
        else:
            embed.add_field(
                name="🏆 Achievements",
                value="None yet - keep playing!",
                inline=True
            )
        
        # Progress to next rank
        current_points = points
        next_rank_points = None
        for threshold, title in [(100, "East Blue Veteran"), (300, "Grand Line Traveler"), 
                                (500, "New World Pirate"), (1000, "Supernova"), 
                                (2000, "Warlord Level"), (5000, "Emperor Commander"),
                                (10000, "Yonko Level"), (20000, "Pirate King Candidate")]:
            if current_points < threshold:
                next_rank_points = threshold
                next_rank_title = title
                break
        
        if next_rank_points:
            progress = current_points / next_rank_points
            progress_bar = "▓" * int(progress * 10) + "░" * (10 - int(progress * 10))
            embed.add_field(
                name="📈 Progress to Next Rank",
                value=f"{progress_bar}\n{current_points}/{next_rank_points} to {next_rank_title}",
                inline=False
            )
        
        embed.set_footer(text=f"Nakama since")
        
        await ctx.send(embed=embed)

    @onepiece.group(name="challenges")
    @checks.admin_or_permissions(manage_guild=True)
    async def challenges_admin(self, ctx):
        """Challenge administration commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @challenges_admin.command(name="channel")
    async def set_challenge_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the challenges channel"""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).challenge_channel.set(channel.id)
        await ctx.send(f"✅ Challenge channel set to {channel.mention}")

    @challenges_admin.command(name="reload")
    async def reload_data(self, ctx):
        """Reload all data files"""
        try:
            self.load_all_data()
            await ctx.send("✅ All data files reloaded successfully!")
        except Exception as e:
            await ctx.send(f"❌ Error reloading data: {str(e)}")

    @onepiece.group(name="trivia_admin", aliases=["tadmin"])
    @checks.admin_or_permissions(manage_guild=True)
    async def trivia_admin(self, ctx):
        """Auto trivia administration commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @trivia_admin.command(name="channel")
    async def set_trivia_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the auto trivia channel"""
        if channel is None:
            channel = ctx.channel
            
        await self.config.guild(ctx.guild).trivia_channel.set(channel.id)
        await ctx.send(f"✅ Auto trivia channel set to {channel.mention}")

    @trivia_admin.command(name="toggle")
    async def toggle_auto_trivia(self, ctx):
        """Toggle auto trivia on/off"""
        current = await self.config.guild(ctx.guild).auto_trivia()
        await self.config.guild(ctx.guild).auto_trivia.set(not current)
        status = "enabled" if not current else "disabled"
        await ctx.send(f"✅ Auto trivia {status}")

    @trivia_admin.command(name="interval")
    async def set_trivia_interval(self, ctx, minutes: int):
        """Set auto trivia interval in minutes (minimum 30)"""
        if minutes < 30:
            await ctx.send("❌ Minimum interval is 30 minutes")
            return
            
        seconds = minutes * 60
        await self.config.guild(ctx.guild).trivia_interval.set(seconds)
        await ctx.send(f"✅ Auto trivia interval set to {minutes} minutes")

    @trivia_admin.command(name="force")
    async def force_auto_trivia(self, ctx):
        """Force post an auto trivia question now"""
        await self.post_auto_trivia(ctx.guild)
        await ctx.send("✅ Auto trivia posted!")

    @trivia_admin.command(name="status")
    async def trivia_status(self, ctx):
        """Show auto trivia settings"""
        config = await self.config.guild(ctx.guild).all()
        
        embed = discord.Embed(
            title="🧠 Auto Trivia Settings",
            color=discord.Color.blue()
        )
        
        trivia_channel = ctx.guild.get_channel(config["trivia_channel"])
        embed.add_field(
            name="📍 Channel",
            value=trivia_channel.mention if trivia_channel else "Not set",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Status",
            value="✅ Enabled" if config["auto_trivia"] else "❌ Disabled",
            inline=True
        )
        
        interval_minutes = config["trivia_interval"] // 60
        embed.add_field(
            name="⏰ Interval",
            value=f"{interval_minutes} minutes",
            inline=True
        )
        
        # Show last trivia time if available
        last_trivia = await self.config.guild(ctx.guild).get_raw("last_auto_trivia", default=None)
        if last_trivia:
            last_time = datetime.fromtimestamp(last_trivia)
            embed.add_field(
                name="📅 Last Trivia",
                value=f"<t:{int(last_trivia)}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @onepiece.command(name="trivia")
    async def trivia_game(self, ctx, difficulty: str = "easy", category: str = "general"):
        """Start a trivia game"""
        if difficulty not in self.trivia_data:
            difficulty = "easy"
            
        trivia_set = self.trivia_data[difficulty]
        if category not in trivia_set:
            category = random.choice(list(trivia_set.keys()))
            
        question_data = random.choice(trivia_set[category])
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {difficulty.title()} One Piece Trivia",
            description=question_data["question"],
            color=discord.Color(self.constants["difficulty_colors"][difficulty])
        )
        embed.add_field(name="⏰ Time Limit", value="30 seconds", inline=True)
        embed.add_field(name="🏆 Points", value=str(self.constants["point_values"][f"{difficulty}_trivia"]), inline=True)
        embed.add_field(name="📂 Category", value=question_data.get("category", "General").title(), inline=True)
        
        message = await ctx.send(embed=embed)
        
        def check(m):
            return (m.channel == ctx.channel and 
                   any(answer.lower() in m.content.lower() 
                       for answer in question_data["answers"]))
        
        try:
            response = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            # Award points
            points = self.constants["point_values"][f"{difficulty}_trivia"]
            await self.add_user_points(response.author, points)
            
            # Update user stats
            user_data = await self.config.user(response.author).all()
            await self.config.user(response.author).trivia_correct.set(user_data["trivia_correct"] + 1)
            await self.config.user(response.author).trivia_attempted.set(user_data["trivia_attempted"] + 1)
            
            # Winner embed
            win_embed = discord.Embed(
                title="🎉 Correct!",
                description=f"{response.author.mention} got it right!",
                color=discord.Color.green()
            )
            win_embed.add_field(name="✅ Answer", value=question_data["answers"][0].title(), inline=True)
            win_embed.add_field(name="🏆 Points Earned", value=str(points), inline=True)
            
            await ctx.send(embed=win_embed)
            
        except asyncio.TimeoutError:
            # Update attempted count
            await self.update_user_trivia_attempts(ctx.author)
            
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"The answer was: **{question_data['answers'][0].title()}**",
                color=discord.Color.orange()
            )
            await ctx.send(embed=timeout_embed)

    async def add_user_points(self, user: discord.User, points: int):
        """Add points to a user"""
        current_points = await self.config.user(user).total_points()
        await self.config.user(user).total_points.set(current_points + points)

    async def update_user_trivia_attempts(self, user: discord.User):
        """Update user's trivia attempt count"""
        attempts = await self.config.user(user).trivia_attempted()
        await self.config.user(user).trivia_attempted.set(attempts + 1)

    @onepiece.command(name="stats")
    async def user_stats(self, ctx, user: discord.Member = None):
        """Show user statistics"""
        if user is None:
            user = ctx.author
            
        user_data = await self.config.user(user).all()
        
        embed = discord.Embed(
            title=f"🏴‍☠️ {user.display_name}'s Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="💰 Total Berries",
            value=f"{user_data['total_points']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"{user_data['daily_streak']} days",
            inline=True
        )
        
        # Calculate trivia accuracy
        if user_data['trivia_attempted'] > 0:
            accuracy = (user_data['trivia_correct'] / user_data['trivia_attempted']) * 100
        else:
            accuracy = 0
            
        embed.add_field(
            name="🧠 Trivia Accuracy",
            value=f"{accuracy:.1f}% ({user_data['trivia_correct']}/{user_data['trivia_attempted']})",
            inline=True
        )
        
        if user_data['achievements']:
            embed.add_field(
                name="🏆 Achievements",
                value="\n".join(user_data['achievements'][:5]),
                inline=False
            )
        
        await ctx.send(embed=embed)
