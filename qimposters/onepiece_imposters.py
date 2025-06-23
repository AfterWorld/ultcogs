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

# Import our One Piece questions
from .onepiece_questions import (
    ONE_PIECE_QUESTIONS, 
    CHAOS_QUESTIONS, 
    get_random_question, 
    get_chaos_questions,
    get_available_categories,
    get_questions_by_category
)

class JoinGameView(discord.ui.View):
    """View for joining the game"""
    
    def __init__(self, game_session, bot):
        super().__init__(timeout=300)
        self.game = game_session
        self.bot = bot
    
    @discord.ui.button(label="Join Crew", emoji="⚓", style=discord.ButtonStyle.primary)
    async def join_crew(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.game.add_player(interaction.user)
    
    @discord.ui.button(label="Start Adventure", emoji="🚢", style=discord.ButtonStyle.success)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.game.players) < await self.game.config.guild(self.game.channel.guild).min_players():
            await interaction.response.send_message(
                f"❌ Need at least {await self.game.config.guild(self.game.channel.guild).min_players()} pirates to start!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self.game.start_game()
        self.stop()
    
    async def on_timeout(self):
        """Called when the view times out"""
        embed = discord.Embed(
            title="⏰ Game Timed Out",
            description="Not enough pirates joined the crew in time!",
            color=discord.Color.red()
        )
        try:
            await self.game.channel.send(embed=embed)
        except discord.HTTPException:
            pass
        
        # Clean up the game
        if hasattr(self.bot, 'get_cog'):
            cog = self.bot.get_cog("OnePieceImposters")
            if cog and self.game.channel.guild.id in cog.active_games:
                del cog.active_games[self.game.channel.guild.id]
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        
        try:
            await self.game.join_message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass

class VotingView(discord.ui.View):
    """View for voting on imposters"""
    
    def __init__(self, game_session, answer_items, voting_time):
        super().__init__(timeout=voting_time)
        self.game = game_session
        self.answer_items = answer_items
        
        # Create voting buttons for each player
        for i, (player, answer) in enumerate(answer_items):
            if i < 10:  # Discord limit of 25 buttons per view, but we'll keep it reasonable
                button = discord.ui.Button(
                    label=f"{i+1}. {player.display_name[:15]}",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"vote_{i}"
                )
                button.callback = self.create_vote_callback(i, player)
                self.add_item(button)
    
    def create_vote_callback(self, index, player):
        async def vote_callback(interaction: discord.Interaction):
            if interaction.user not in self.game.players:
                await interaction.response.send_message("❌ You're not part of this game!", ephemeral=True)
                return
            
            self.game.votes[interaction.user] = player
            await interaction.response.send_message(
                f"🗳️ You voted for **{player.display_name}**!",
                ephemeral=True
            )
        
        return vote_callback
    
    async def on_timeout(self):
        """Called when voting time expires"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        if hasattr(self.game, 'voting_message'):
            try:
                await self.game.voting_message.edit(view=self)
            except discord.NotFound:
                pass

class ContinueGameView(discord.ui.View):
    """View for continuing or ending the game"""
    
    def __init__(self, game_session):
        super().__init__(timeout=30)
        self.game = game_session
        self.continue_votes = 0
        self.stop_votes = 0
        self.voters = set()
    
    @discord.ui.button(label="Another Round", emoji="⚓", style=discord.ButtonStyle.primary)
    async def continue_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.game.players:
            await interaction.response.send_message("❌ You're not part of this game!", ephemeral=True)
            return
        
        if interaction.user in self.voters:
            await interaction.response.send_message("❌ You already voted!", ephemeral=True)
            return
        
        self.voters.add(interaction.user)
        self.continue_votes += 1
        
        await interaction.response.send_message("⚓ Voted to continue!", ephemeral=True)
        await self.check_votes()
    
    @discord.ui.button(label="End Game", emoji="🛑", style=discord.ButtonStyle.danger)
    async def end_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.game.players:
            await interaction.response.send_message("❌ You're not part of this game!", ephemeral=True)
            return
        
        if interaction.user in self.voters:
            await interaction.response.send_message("❌ You already voted!", ephemeral=True)
            return
        
        self.voters.add(interaction.user)
        self.stop_votes += 1
        
        await interaction.response.send_message("🛑 Voted to end!", ephemeral=True)
        await self.check_votes()
    
    async def check_votes(self):
        """Check if we should continue or end based on votes"""
        total_players = len(self.game.players)
        
        # If everyone voted or majority wants to continue
        if len(self.voters) >= total_players or self.continue_votes > total_players // 2:
            self.stop()  # Stop the view first
            if self.continue_votes > self.stop_votes:
                await self.game.start_round()
            else:
                await self.game.end_game()
        elif self.stop_votes > total_players // 2:
            # Majority wants to stop
            self.stop()
            await self.game.end_game()
    
    async def on_timeout(self):
        """Called when voting time expires"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        try:
            if hasattr(self.game, 'voting_message') and self.game.voting_message:
                await self.game.voting_message.edit(view=self)
        except (discord.NotFound, discord.HTTPException):
            pass
        
        # Decide based on current votes
        if self.continue_votes > self.stop_votes:
            await self.game.start_round()
        else:
            await self.game.end_game()

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
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        # Stop all active games and their views
        for game in self.active_games.values():
            if hasattr(game, 'join_view') and game.join_view:
                game.join_view.stop()
            if hasattr(game, 'voting_view') and game.voting_view:
                game.voting_view.stop()
        self.active_games.clear()
    
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
        
        # Check bot permissions
        bot_perms = ctx.channel.permissions_for(ctx.guild.me)
        missing_perms = []
        if not bot_perms.send_messages:
            missing_perms.append("Send Messages")
        if not bot_perms.embed_links:
            missing_perms.append("Embed Links")
        if not bot_perms.use_external_emojis:
            missing_perms.append("Use External Emojis")
        
        if missing_perms:
            return await ctx.send(f"❌ I'm missing these permissions: {', '.join(missing_perms)}")

        
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
            
            # Check if category has questions
            questions = get_questions_by_category(category.lower())
            if not questions:
                return await ctx.send(f"❌ No questions found for category: {category}")

        
        game = OnePieceGameSession(ctx.channel, self.config, self.bot, category)
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
            name="👥 Players Needed", 
            value=f"{await self.config.guild(ctx.guild).min_players()}-{await self.config.guild(ctx.guild).max_players()}",
            inline=True
        )
        embed.add_field(
            name="👥 Current Crew",
            value=f"0/{await self.config.guild(ctx.guild).max_players()} pirates",
            inline=True
        )
        embed.add_field(
            name="⏱️ Game Flow",
            value="1️⃣ Answer questions\n2️⃣ Discuss answers\n3️⃣ Vote for imposters\n4️⃣ See results!",
            inline=False
        )
        
        embed.set_footer(text="Click 'Join Crew' to join! Captain can start when ready.")
        
        view = JoinGameView(game, self.bot)
        message = await ctx.send(embed=embed, view=view)
        
        game.join_message = message
        game.join_view = view
    
    @onepiece_game.command(name="stop")
    @checks.admin_or_permissions(manage_guild=True)
    async def stop_game(self, ctx):
        """🛑 Stop the current game (Admin only)"""
        if ctx.guild.id not in self.active_games:
            return await ctx.send("❌ No game is currently running!")
        
        # Stop any active views
        game = self.active_games[ctx.guild.id]
        if hasattr(game, 'join_view'):
            game.join_view.stop()
        
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
            value="• Click 'Join Crew' to join\n"
                  "• Answer questions in DMs\n"
                  "• Some players get different questions (imposters!)\n"
                  "• Vote with buttons to identify imposters\n"
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
    
    def __init__(self, channel: discord.TextChannel, config, bot: Red, category: str = None):
        self.channel = channel
        self.config = config
        self.bot = bot
        self.category = category
        self.players: Set[discord.Member] = set()
        self.answers: Dict[discord.Member, str] = {}
        self.votes: Dict[discord.Member, discord.Member] = {}
        self.scores: Dict[discord.Member, int] = defaultdict(int)
        
        self.current_question: Optional[Dict] = None
        self.impostors: Set[discord.Member] = set()
        self.is_chaos_round = False
        self.chaos_questions: Dict[discord.Member, str] = {}
        
        self.state = "waiting"  # waiting, answering, voting, results
        self.round_number = 0
        self.join_message = None
        self.join_view = None
        self.voting_message = None
        self.voting_view = None
        
    async def add_player(self, user: discord.Member):
        """Add a player to the game"""
        max_players = await self.config.guild(self.channel.guild).max_players()
        
        if user in self.players:
            try:
                await user.send("⚠️ You're already part of this crew!")
            except discord.Forbidden:
                pass
            return
            
        if len(self.players) >= max_players:
            try:
                await user.send(f"❌ The crew is full! ({max_players} max)")
            except discord.Forbidden:
                pass
            return
        
        self.players.add(user)
        try:
            await user.send(f"⚓ Welcome to the crew, {user.display_name}! You've joined the One Piece Imposters adventure!")
        except discord.Forbidden:
            await self.channel.send(f"⚠️ {user.mention}, please enable DMs to receive game questions!")
        
        # Update the join message
        if self.join_message:
            embed = self.join_message.embeds[0]
            embed.set_field_at(
                1,  # Current Crew field
                name="👥 Current Crew",
                value=f"{len(self.players)}/{await self.config.guild(self.channel.guild).max_players()} pirates",
                inline=True
            )
            
            if len(self.players) >= await self.config.guild(self.channel.guild).min_players():
                embed.color = discord.Color.green()
                if len(embed.fields) < 4:  # Add ready field if not already there
                    embed.add_field(
                        name="🚢 Ready to Sail!",
                        value="Captain can now start the adventure!",
                        inline=False
                    )
            
            try:
                await self.join_message.edit(embed=embed)
            except (discord.NotFound, discord.HTTPException):
                # Message was deleted or we don't have permission
                pass
    
    async def start_game(self):
        """Start the actual game"""
        self.state = "starting"
        
        # Stop the join view
        if self.join_view:
            self.join_view.stop()
        
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
        dm_failed_players = []
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
                dm_failed_players.append(player)
        
        if dm_failed_players:
            failed_mentions = ", ".join([p.mention for p in dm_failed_players])
            await self.channel.send(f"❌ Couldn't send DMs to: {failed_mentions}. Please enable DMs!")
        
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
        dm_failed_players = []
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
                dm_failed_players.append(player)
        
        if dm_failed_players:
            failed_mentions = ", ".join([p.mention for p in dm_failed_players])
            await self.channel.send(f"❌ Couldn't send DMs to: {failed_mentions}. Please enable DMs!")
        
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
                value=f"Vote for the {len(self.impostors)} imposter(s)!\nClick the buttons below to vote!",
                inline=False
            )
        else:
            embed.add_field(
                name="🎭 Chaos Voting",
                value="Try to guess what questions others got based on their answers!",
                inline=False
            )
        
        voting_time = await self.config.guild(self.channel.guild).voting_time()
        view = VotingView(self, answer_items, voting_time)
        self.voting_message = await self.channel.send(embed=embed, view=view)
        self.voting_view = view  # Store reference for cleanup
        
        self.state = "voting"
        
        # Wait for voting to complete
        await asyncio.sleep(voting_time)
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
            description="Choose if you want another round or to end the game!",
            color=discord.Color.blue()
        )
        
        view = ContinueGameView(self)
        await self.channel.send(embed=embed, view=view)
    
    async def end_game(self):
        """End the game and show final results"""
        # Stop any active views
        if self.join_view:
            self.join_view.stop()
        if self.voting_view:
            self.voting_view.stop()
        
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
        cog = self.bot.get_cog("OnePieceImposters")
        if cog and self.channel.guild.id in cog.active_games:
            del cog.active_games[self.channel.guild.id]

async def setup(bot):
    await bot.add_cog(OnePieceImposters(bot))
