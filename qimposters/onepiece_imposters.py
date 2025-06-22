import discord
import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, Counter

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

# Import our One Piece questions
from .onepiece_questions import (
    ONE_PIECE_QUESTIONS, 
    CHAOS_QUESTIONS, 
    get_random_question, 
    get_chaos_questions,
    get_available_categories,
    get_questions_by_category
)

class OnePieceImposters(commands.Cog):
    """
    🏴‍☠️ One Piece Question Imposters Game! 🏴‍☠️
    
    A social deduction game where pirates answer questions about the Grand Line,
    but some crew members might have received different orders from their captain!
    Figure out who the imposters are based on their suspicious answers.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567891234, force_registration=True)
        
        # Default configuration
        default_guild = {
            "game_channel": None,
            "min_players": 4,
            "max_players": 20,
            "answer_time": 90,  # Longer for One Piece questions
            "voting_time": 60,
            "chaos_chance": 0.08,  # 8% chance for chaos round
            "points_correct_guess": 10,
            "points_successful_impostor": 15,
            "points_fooled_players": 5,
            "allow_categories": True
        }
        
        self.config.register_guild(**default_guild)
        
        # Active games storage
        self.active_games: Dict[int, OnePieceGameSession] = {}
    
    @commands.group(name="onepiece", aliases=["op"])
    async def onepiece_game(self, ctx):
        """🏴‍☠️ One Piece Question Imposters commands"""
        if ctx.invoked_subcommand is None:
            await self.show_help(ctx)
    
    @onepiece_game.command(name="start")
    async def start_game(self, ctx, category: str = None):
        """🚢 Start a new One Piece Question Imposters game!
        
        Optional: Specify a category (devil_fruits, straw_hats, locations, etc.)
        Use `[p]onepiece categories` to see available categories.
        """
        if ctx.guild.id in self.active_games:
            return await ctx.send("⚠️ There's already a game running in this server!")
        
        # Validate category if provided
        if category:
            available_categories = get_available_categories()
            if category.lower() not in available_categories:
                embed = discord.Embed(
                    title="❌ Invalid Category",
                    description=f"Available categories: {', '.join(available_categories)}",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
        
        game = OnePieceGameSession(ctx.channel, self.config, category)
        self.active_games[ctx.guild.id] = game
        
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Question Imposters",
            description="⚓ **A new adventure begins!** ⚓\n\nPirates will receive questions about the Grand Line, but some crew members might be working for the enemy! Can you identify the imposters?",
            color=discord.Color.from_rgb(255, 165, 0)  # Orange like Luffy's vest
        )
        
        if category:
            embed.add_field(
                name="📚 Category Focus", 
                value=f"Questions will focus on: **{category.replace('_', ' ').title()}**",
                inline=False
            )
        
        embed.add_field(
            name="⚡ How to Join", 
            value="React with ⚓ to join the crew!",
            inline=True
        )
        embed.add_field(
            name="👥 Players Needed", 
            value=f"{await self.config.guild(ctx.guild).min_players()}-{await self.config.guild(ctx.guild).max_players()}",
            inline=True
        )
        embed.add_field(
            name="⏱️ Game Flow",
            value="1️⃣ Answer questions\n2️⃣ Discuss answers\n3️⃣ Vote for imposters\n4️⃣ See results!",
            inline=False
        )
        
        embed.set_footer(text="React with ⚓ to join! Captain will start when ready with 🚢")
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("⚓")
        await message.add_reaction("🚢")
        
        game.join_message = message
        
        # Start listening for reactions
        await self.handle_join_reactions(game)
    
    async def handle_join_reactions(self, game: 'OnePieceGameSession'):
        """Handle join reactions for the game"""
        def check(reaction, user):
            return (reaction.message.id == game.join_message.id and 
                   not user.bot and 
                   str(reaction.emoji) in ["⚓", "🚢"])
        
        while game.state == "waiting":
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
                
                if str(reaction.emoji) == "⚓":
                    await game.add_player(user)
                elif str(reaction.emoji) == "🚢" and len(game.players) >= await game.config.guild(game.channel.guild).min_players():
                    await game.start_game()
                    break
                    
            except asyncio.TimeoutError:
                embed = discord.Embed(
                    title="⏰ Game Timed Out",
                    description="Not enough pirates joined the crew in time!",
                    color=discord.Color.red()
                )
                await game.channel.send(embed=embed)
                del self.active_games[game.channel.guild.id]
                break
    
    @onepiece_game.command(name="stop")
    @checks.admin_or_permissions(manage_guild=True)
    async def stop_game(self, ctx):
        """🛑 Stop the current game (Admin only)"""
        if ctx.guild.id not in self.active_games:
            return await ctx.send("❌ No game is currently running!")
        
        del self.active_games[ctx.guild.id]
        
        embed = discord.Embed(
            title="🛑 Game Stopped",
            description="The adventure has ended by admin command!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @onepiece_game.command(name="categories")
    async def show_categories(self, ctx):
        """📚 Show all available question categories"""
        categories = get_available_categories()
        
        embed = discord.Embed(
            title="📚 One Piece Question Categories",
            description="You can start a game focused on any of these categories:",
            color=discord.Color.blue()
        )
        
        category_list = "\n".join([f"🔹 **{cat.replace('_', ' ').title()}**" for cat in categories])
        embed.add_field(name="Available Categories", value=category_list, inline=False)
        embed.add_field(
            name="Usage", 
            value=f"`{ctx.prefix}onepiece start <category>`\nExample: `{ctx.prefix}onepiece start devil_fruits`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @onepiece_game.command(name="config")
    @checks.admin_or_permissions(manage_guild=True)
    async def configure_game(self, ctx):
        """⚙️ Configure game settings (Admin only)"""
        embed = discord.Embed(
            title="⚙️ One Piece Imposters Configuration",
            description="Current server settings:",
            color=discord.Color.blue()
        )
        
        config = self.config.guild(ctx.guild)
        
        embed.add_field(name="Min Players", value=await config.min_players(), inline=True)
        embed.add_field(name="Max Players", value=await config.max_players(), inline=True)
        embed.add_field(name="Answer Time", value=f"{await config.answer_time()}s", inline=True)
        embed.add_field(name="Voting Time", value=f"{await config.voting_time()}s", inline=True)
        embed.add_field(name="Chaos Round Chance", value=f"{await config.chaos_chance()*100:.1f}%", inline=True)
        
        await ctx.send(embed=embed)
    
    async def show_help(self, ctx):
        """Show help information"""
        embed = discord.Embed(
            title="🏴‍☠️ One Piece Question Imposters Help",
            description="Set sail on an adventure of deduction and One Piece knowledge!",
            color=discord.Color.from_rgb(255, 165, 0)
        )
        
        embed.add_field(
            name="🚢 Basic Commands",
            value=f"`{ctx.prefix}onepiece start` - Start a new game\n"
                  f"`{ctx.prefix}onepiece categories` - View question categories\n"
                  f"`{ctx.prefix}onepiece stop` - Stop current game (Admin)",
            inline=False
        )
        
        embed.add_field(
            name="🎯 How to Play",
            value="• Join with ⚓ reaction\n"
                  "• Answer questions in DMs\n"
                  "• Some players get different questions (imposters!)\n"
                  "• Vote to identify imposters\n"
                  "• Earn points for correct guesses!",
            inline=False
        )
        
        embed.add_field(
            name="🌟 Special Rounds",
            value="• **Normal**: 1-3 imposters with different questions\n"
                  "• **Chaos**: Everyone gets different questions! (rare)",
            inline=False
        )
        
        await ctx.send(embed=embed)

class OnePieceGameSession:
    """Manages a single One Piece game session"""
    
    def __init__(self, channel: discord.TextChannel, config, category: str = None):
        self.channel = channel
        self.config = config
        self.category = category
        self.players: Set[discord.Member] = set()
        self.answers: Dict[discord.Member, str] = {}
        self.votes: Dict[discord.Member, int] = {}
        self.scores: Dict[discord.Member, int] = defaultdict(int)
        
        self.current_question: Optional[Dict] = None
        self.impostors: Set[discord.Member] = set()
        self.is_chaos_round = False
        self.chaos_questions: Dict[discord.Member, str] = {}
        
        self.state = "waiting"  # waiting, answering, voting, results
        self.round_number = 0
        self.join_message = None
        
    async def add_player(self, user: discord.Member):
        """Add a player to the game"""
        max_players = await self.config.guild(self.channel.guild).max_players()
        
        if user in self.players:
            await user.send("⚠️ You're already part of this crew!")
            return
            
        if len(self.players) >= max_players:
            await user.send(f"❌ The crew is full! ({max_players} max)")
            return
        
        self.players.add(user)
        await user.send(f"⚓ Welcome to the crew, {user.display_name}! You've joined the One Piece Imposters adventure!")
        
        # Update the join message
        if self.join_message:
            embed = self.join_message.embeds[0]
            embed.set_field_at(
                1,  # Players field
                name="👥 Current Crew",
                value=f"{len(self.players)}/{await self.config.guild(self.channel.guild).max_players()} pirates",
                inline=True
            )
            
            if len(self.players) >= await self.config.guild(self.channel.guild).min_players():
                embed.color = discord.Color.green()
                embed.add_field(
                    name="🚢 Ready to Sail!",
                    value="Captain can now start the adventure!",
                    inline=False
                )
            
            await self.join_message.edit(embed=embed)
    
    async def start_game(self):
        """Start the actual game"""
        self.state = "starting"
        
        embed = discord.Embed(
            title="🚢 Adventure Begins!",
            description=f"**{len(self.players)} brave pirates** have joined the crew!\n\nPreparing for the first challenge...",
            color=discord.Color.green()
        )
        
        crew_list = "\n".join([f"⚓ {player.display_name}" for player in self.players])
        embed.add_field(name="👥 Crew Manifest", value=crew_list, inline=False)
        
        await self.channel.send(embed=embed)
        await asyncio.sleep(3)
        
        await self.start_round()
    
    async def start_round(self):
        """Start a new round of the game"""
        self.round_number += 1
        self.answers.clear()
        self.votes.clear()
        self.impostors.clear()
        self.chaos_questions.clear()
        
        # Get questions based on category if specified
        if self.category:
            questions = get_questions_by_category(self.category)
        else:
            questions = ONE_PIECE_QUESTIONS
        
        # Determine if this is a chaos round
        chaos_chance = await self.config.guild(self.channel.guild).chaos_chance()
        self.is_chaos_round = random.random() < chaos_chance and len(self.players) >= 6
        
        if self.is_chaos_round:
            await self._setup_chaos_round()
        else:
            await self._setup_normal_round(questions)
    
    async def _setup_normal_round(self, questions: List[Dict]):
        """Setup a normal round with 1-3 impostors"""
        self.current_question = random.choice(questions)
        
        # Determine number of impostors (weighted towards 1)
        num_players = len(self.players)
        max_impostors = min(3, num_players // 2)
        
        if max_impostors == 1:
            num_impostors = 1
        else:
            # Weighted selection: 70% chance for 1, 25% for 2, 5% for 3
            weights = [70, 25, 5][:max_impostors]
            num_impostors = random.choices(range(1, max_impostors + 1), weights=weights)[0]
        
        self.impostors = set(random.sample(list(self.players), num_impostors))
        
        # Send round announcement
        embed = discord.Embed(
            title=f"⚔️ Round {self.round_number} - Grand Line Challenge!",
            description="📮 Check your DMs for your mission briefing!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="⏱️ Time Limit", 
            value=f"{await self.config.guild(self.channel.guild).answer_time()} seconds",
            inline=True
        )
        embed.add_field(
            name="🕵️ Imposters", 
            value=f"{len(self.impostors)} crew member(s) have different orders...",
            inline=True
        )
        
        await self.channel.send(embed=embed)
        
        # DM questions to players
        for player in self.players:
            try:
                if player in self.impostors:
                    question_text = f"🕵️‍♂️ **UNDERCOVER MISSION:**\n{self.current_question['impostor']}"
                    embed = discord.Embed(
                        title="🔥 Secret Orders",
                        description=question_text,
                        color=discord.Color.red()
                    )
                    embed.add_field(
                        name="Your Mission",
                        value="Answer this question, but try to blend in with the crew!",
                        inline=False
                    )
                else:
                    question_text = f"🏴‍☠️ **CREW QUESTION:**\n{self.current_question['main']}"
                    embed = discord.Embed(
                        title="⚓ Crew Mission",
                        description=question_text,
                        color=discord.Color.blue()
                    )
                
                embed.set_footer(text=f"Respond here with your answer! Time limit: {await self.config.guild(self.channel.guild).answer_time()}s")
                await player.send(embed=embed)
                
            except discord.Forbidden:
                await self.channel.send(f"❌ Couldn't send DM to {player.mention}. Please enable DMs!")
        
        self.state = "answering"
        await self.collect_answers()
    
    async def _setup_chaos_round(self):
        """Setup chaos round where everyone gets different questions"""
        chaos_questions = get_chaos_questions(len(self.players))
        
        # Assign unique questions to each player
        for player, question in zip(self.players, chaos_questions):
            self.chaos_questions[player] = question
        
        # Announce chaos round
        embed = discord.Embed(
            title="🌪️ CHAOS ROUND! 🌪️",
            description="🎭 **EVERYONE** has received different questions!\n📮 Check your DMs for your unique challenge!",
            color=discord.Color.from_rgb(255, 0, 255)  # Purple for chaos
        )
        embed.add_field(
            name="⚡ Special Rules",
            value="Try to figure out who got what question based on their answers!",
            inline=False
        )
        
        await self.channel.send(embed=embed)
        
        # DM unique questions
        for player in self.players:
            try:
                question_text = f"🎭 **YOUR UNIQUE QUESTION:**\n{self.chaos_questions[player]}"
                embed = discord.Embed(
                    title="🌪️ Chaos Mission",
                    description=question_text,
                    color=discord.Color.from_rgb(255, 0, 255)
                )
                embed.set_footer(text="Everyone has a different question! Good luck!")
                
                await player.send(embed=embed)
                
            except discord.Forbidden:
                await self.channel.send(f"❌ Couldn't send DM to {player.mention}. Please enable DMs!")
        
        self.state = "answering"
        await self.collect_answers()
    
    async def collect_answers(self):
        """Collect answers from all players"""
        answer_time = await self.config.guild(self.channel.guild).answer_time()
        
        def check(message):
            return (message.author in self.players and 
                   isinstance(message.channel, discord.DMChannel) and
                   message.author not in self.answers)
        
        start_time = asyncio.get_event_loop().time()
        
        while len(self.answers) < len(self.players):
            remaining_time = answer_time - (asyncio.get_event_loop().time() - start_time)
            if remaining_time <= 0:
                break
                
            try:
                message = await self.bot.wait_for('message', timeout=remaining_time, check=check)
                self.answers[message.author] = message.content[:200]  # Limit answer length
                
                await message.add_reaction("✅")
                await message.author.send(f"📝 Answer recorded: {message.content}")
                
            except asyncio.TimeoutError:
                break
        
        await self.show_answers()
    
    async def show_answers(self):
        """Display all answers and start voting"""
        if not self.answers:
            embed = discord.Embed(
                title="😴 No Answers Received",
                description="All pirates fell asleep! Starting a new round...",
                color=discord.Color.red()
            )
            await self.channel.send(embed=embed)
            await asyncio.sleep(3)
            await self.start_round()
            return
        
        # Create answers display
        if self.is_chaos_round:
            embed = discord.Embed(
                title="🌪️ Chaos Round - All Answers",
                description="Everyone had different questions!",
                color=discord.Color.from_rgb(255, 0, 255)
            )
        else:
            embed = discord.Embed(
                title=f"📊 Round {self.round_number} - Crew Answers",
                description=f"**Question:** {self.current_question['main']}",
                color=discord.Color.green()
            )
        
        # Shuffle answers for anonymous display
        answer_items = list(self.answers.items())
        random.shuffle(answer_items)
        
        answer_text = ""
        for i, (player, answer) in enumerate(answer_items, 1):
            answer_text += f"**{i}.** {player.display_name}: {answer}\n"
        
        embed.add_field(name="🗣️ Answers", value=answer_text or "No answers received", inline=False)
        
        if not self.is_chaos_round:
            embed.add_field(
                name="🕵️ Your Mission",
                value=f"Vote for the {len(self.impostors)} imposter(s)!\nReact with numbers to vote!",
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Chaos Voting",
                value="Try to guess what questions others got based on their answers!",
                inline=False
            )
        
        message = await self.channel.send(embed=embed)
        
        # Add number reactions for voting
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(len(self.answers)):
            if i < len(number_emojis):
                await message.add_reaction(number_emojis[i])
        
        self.state = "voting"
        await self.collect_votes(message, answer_items)
    
    async def collect_votes(self, message, answer_items):
        """Collect votes for imposters"""
        voting_time = await self.config.guild(self.channel.guild).voting_time()
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        def check(reaction, user):
            return (user in self.players and 
                   reaction.message.id == message.id and
                   str(reaction.emoji) in number_emojis[:len(answer_items)])
        
        # Collect votes for the specified time
        end_time = asyncio.get_event_loop().time() + voting_time
        
        while asyncio.get_event_loop().time() < end_time:
            try:
                remaining = end_time - asyncio.get_event_loop().time()
                reaction, user = await self.bot.wait_for('reaction_add', timeout=remaining, check=check)
                
                # Record vote
                emoji_index = number_emojis.index(str(reaction.emoji))
                voted_player = answer_items[emoji_index][0]
                self.votes[user] = voted_player
                
            except asyncio.TimeoutError:
                break
        
        await self.show_results()
    
    async def show_results(self):
        """Show round results and update scores"""
        if self.is_chaos_round:
            await self.show_chaos_results()
        else:
            await self.show_normal_results()
        
        # Show updated scores
        await self.show_scores()
        
        # Ask if players want another round
        await self.ask_next_round()
    
    async def show_normal_results(self):
        """Show results for normal round"""
        # Count votes for each player
        vote_counts = Counter(self.votes.values())
        
        embed = discord.Embed(
            title="🏆 Round Results",
            color=discord.Color.gold()
        )
        
        # Show the questions
        embed.add_field(
            name="📋 The Questions Were:",
            value=f"**Crew:** {self.current_question['main']}\n**Imposters:** {self.current_question['impostor']}",
            inline=False
        )
        
        # Show who the imposters were
        impostor_names = [imp.display_name for imp in self.impostors]
        embed.add_field(
            name="🕵️ The Imposters Were:",
            value=", ".join(impostor_names),
            inline=False
        )
        
        # Show voting results
        vote_text = ""
        for player, count in vote_counts.most_common():
            vote_text += f"**{player.display_name}:** {count} votes\n"
        
        if vote_text:
            embed.add_field(name="🗳️ Vote Results", value=vote_text, inline=False)
        
        # Calculate points
        points_config = self.config.guild(self.channel.guild)
        correct_guess_points = await points_config.points_correct_guess()
        impostor_success_points = await points_config.points_successful_impostor()
        
        # Points for correct guesses
        for voter, voted_for in self.votes.items():
            if voted_for in self.impostors:
                self.scores[voter] += correct_guess_points
        
        # Points for imposters who weren't caught
        total_votes = len(self.votes)
        for impostor in self.impostors:
            votes_against = vote_counts.get(impostor, 0)
            if votes_against < total_votes / 2:  # Less than majority
                self.scores[impostor] += impostor_success_points
        
        await self.channel.send(embed=embed)
    
    async def show_chaos_results(self):
        """Show results for chaos round"""
        embed = discord.Embed(
            title="🌪️ Chaos Round Complete!",
            description="Everyone had different questions - pure chaos!",
            color=discord.Color.from_rgb(255, 0, 255)
        )
        
        # Show what questions each player had
        question_text = ""
        for player, question in self.chaos_questions.items():
            answer = self.answers.get(player, "No answer")
            question_text += f"**{player.display_name}:** {question}\n*Answer: {answer}*\n\n"
        
        embed.add_field(name="🎭 Questions & Answers", value=question_text[:1024], inline=False)
        
        # Everyone gets participation points in chaos rounds
        for player in self.players:
            if player in self.answers:
                self.scores[player] += 5
        
        await self.channel.send(embed=embed)
    
    async def show_scores(self):
        """Display current scores"""
        if not any(self.scores.values()):
            return
        
        embed = discord.Embed(
            title="🏆 Current Leaderboard",
            color=discord.Color.gold()
        )
        
        # Sort players by score
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        
        score_text = ""
        for i, (player, score) in enumerate(sorted_scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏴‍☠️"
            score_text += f"{medal} **{player.display_name}:** {score} points\n"
        
        embed.add_field(name="Scores", value=score_text, inline=False)
        
        await self.channel.send(embed=embed)
    
    async def ask_next_round(self):
        """Ask if players want another round"""
        embed = discord.Embed(
            title="🚢 Continue the Adventure?",
            description="React with ⚓ for another round or 🛑 to end the game!",
            color=discord.Color.blue()
        )
        
        message = await self.channel.send(embed=embed)
        await message.add_reaction("⚓")
        await message.add_reaction("🛑")
        
        def check(reaction, user):
            return (user in self.players and 
                   reaction.message.id == message.id and
                   str(reaction.emoji) in ["⚓", "🛑"])
        
        continue_votes = 0
        stop_votes = 0
        voters = set()
        
        # Collect votes for 30 seconds
        timeout = 30
        end_time = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < end_time and len(voters) < len(self.players):
            try:
                remaining = end_time - asyncio.get_event_loop().time()
                reaction, user = await self.bot.wait_for('reaction_add', timeout=remaining, check=check)
                
                if user not in voters:
                    voters.add(user)
                    if str(reaction.emoji) == "⚓":
                        continue_votes += 1
                    elif str(reaction.emoji) == "🛑":
                        stop_votes += 1
                        
            except asyncio.TimeoutError:
                break
        
        # Decide based on votes
        if continue_votes > stop_votes:
            await asyncio.sleep(2)
            await self.start_round()
        else:
            await self.end_game()
    
    async def end_game(self):
        """End the game and show final results"""
        embed = discord.Embed(
            title="🏁 Adventure Complete!",
            description="Thank you for playing One Piece Question Imposters!",
            color=discord.Color.gold()
        )
        
        if self.scores:
            # Show final leaderboard
            sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
            
            final_scores = ""
            for i, (player, score) in enumerate(sorted_scores, 1):
                medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏴‍☠️"
                final_scores += f"{medal} **{player.display_name}:** {score} points\n"
            
            embed.add_field(name="🏆 Final Leaderboard", value=final_scores, inline=False)
            
            # Congratulate winner
            if sorted_scores:
                winner = sorted_scores[0][0]
                embed.add_field(
                    name="🎉 Pirate King/Queen",
                    value=f"Congratulations {winner.mention}! You've proven yourself worthy of the Grand Line!",
                    inline=False
                )
        
        embed.set_footer(text="Thanks for playing! Use the command again to start a new adventure!")
        
        await self.channel.send(embed=embed)
        
        # Clean up the game
        if self.channel.guild.id in self.channel.guild.get_cog("OnePieceImposters").active_games:
            del self.channel.guild.get_cog("OnePieceImposters").active_games[self.channel.guild.id]

async def setup(bot):
    await bot.add_cog(OnePieceImposters(bot))
