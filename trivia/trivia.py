import discord
from redbot.core import commands, Config
import yaml
import aiohttp
import asyncio
import random
import time
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box
from pathlib import Path
import logging

LOG = logging.getLogger("red.trivia")

class Trivia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.trivia_sessions = {}
        self.questions = {}
        self.bot.loop.create_task(self.initialize_questions())  # Initialize questions on cog load

    async def load_questions_and_print(self):
        await self.initialize_questions()
        print("Questions loaded. Available categories:", list(self.questions.keys()))

    async def initialize_questions(self):
        self.questions = {}
        trivia_path = Path("/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/Trivia/Categories/")
        for file in trivia_path.glob('*_questions.yaml'):
            category = file.stem  # This will be like 'category_questions'
            with file.open('r') as f:
                self.questions[category] = yaml.safe_load(f)

    async def load_questions(self, category):
        try:
            file_path = Path(f"/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/Trivia/Categories/{category}_questions.yaml")
            if file_path.exists():
                with file_path.open('r') as f:
                    questions = yaml.safe_load(f)
                    print(f"Successfully loaded {len(questions)} questions for {category}")
                    return questions
            else:
                print(f"Failed to fetch questions for {category}. File does not exist: {file_path}")
                return None
        except yaml.YAMLError as e:
            print(f"YAML parsing error for {category}: {str(e)}")
            return None
        except Exception as e:
            print(f"An error occurred while loading questions for {category}: {str(e)}")
            return None

    @commands.command()
    async def trivia(self, ctx, category: str = "op"):
        """Start a trivia game for a specific category!"""
        if category.lower() in ["daily", "weekly"]:
            extra_points = 5 if category.lower() == "daily" else 10
            available_categories = list(self.questions.keys())
            if not available_categories:
                await ctx.send("No trivia categories available for the challenge.")
                return
            category = random.choice(available_categories).replace('_questions', '')
            await ctx.send(f"Starting a {category.capitalize()} Trivia game with extra points for the {category.lower()} challenge!")
        else:
            extra_points = 0

        # Check if a trivia game is already active in this channel
        if ctx.channel.id in self.trivia_sessions and self.trivia_sessions[ctx.channel.id]["active"]:
            await ctx.send("There's already a trivia game in progress in this channel. Finish that one first!")
            return

        # Convert the input category to the file name format
        full_category = f"{category.lower()}_questions"

        if full_category not in self.questions:
            available_categories = ", ".join(cat.replace('_questions', '') for cat in self.questions.keys())
            await ctx.send(f"That is an invalid category. Available categories: {available_categories}")
            return

        self.trivia_sessions[ctx.channel.id] = {"active": True, "scores": {}, "category": category, "asked_questions": set()}

        await ctx.send(f"A new {category.capitalize()} Trivia game has begun! First to 25 points wins!")

        try:
            for question in random.sample(self.questions[full_category], min(len(self.questions[full_category]), 50)):
                if ctx.channel.id not in self.trivia_sessions or not self.trivia_sessions[ctx.channel.id]["active"]:
                    await ctx.send("The trivia game has been stopped!")
                    break

                if question['question'] in self.trivia_sessions[ctx.channel.id]["asked_questions"]:
                    continue

                self.trivia_sessions[ctx.channel.id]["asked_questions"].add(question['question'])

                if not await self.ask_question(ctx, question, extra_points):
                    break

                if any(score >= 25 for score in self.trivia_sessions[ctx.channel.id]["scores"].values()):
                    break

                await asyncio.sleep(2)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            LOG.error(f"Error in trivia game: {str(e)}", exc_info=True)
        finally:
            await self.end_game(ctx)

    async def ask_question(self, ctx, question, extra_points=0):
        category = self.trivia_sessions[ctx.channel.id]["category"]
        message = f"**{category.capitalize()} Trivia**\n\n{question['question']}"

        if 'image' in question:
            message += f"\n{question['image']}"

        await ctx.send(message)

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
                if answered or not self.trivia_sessions[ctx.channel.id]["active"]:
                    break
                if hint_index < len(question['hints']):
                    await ctx.send(f"Hint: {question['hints'][hint_index]}")
                hint_index += 1

        hint_task = asyncio.create_task(send_hints())

        try:
            while time.time() - start_time < question_duration and not answered:
                if not self.trivia_sessions[ctx.channel.id]["active"]:
                    break
                try:
                    msg = await asyncio.wait_for(self.bot.wait_for("message", check=check), 
                                                 timeout=question_duration - (time.time() - start_time))

                    if msg.content.lower() in [answer.lower() for answer in question['answers']]:
                        scores = self.trivia_sessions[ctx.channel.id]["scores"]
                        scores[msg.author] = scores.get(msg.author, 0) + 1 + extra_points
                        await ctx.send(f"Correct, {msg.author.display_name}! You know your {category.capitalize()} trivia! (Current score: {scores[msg.author]})")
                        answered = True
                        if scores[msg.author] >= 25:
                            await ctx.send(f"Congratulations, {msg.author.display_name}! You've reached 25 points and won the game!")
                            return False  # End the game

                except asyncio.TimeoutError:
                    # This is expected if no answer is given before the next hint or end of question
                    pass

        finally:
            hint_task.cancel()  # Ensure the hint task is cancelled when the question ends

        if not answered:
            await ctx.send(f"Time's up! The correct answers were: {', '.join(question['answers'])}")

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
                        scores[category][str(player.id)] = {"total_score": 0, "games_played": 0, "weekly_score": 0}
                    scores[category][str(player.id)]["total_score"] += score
                    scores[category][str(player.id)]["games_played"] += 1
                    scores[category][str(player.id)]["weekly_score"] += score

            await ctx.send(f"The {category.capitalize()} trivia game has ended! Thanks for playing!")

    @commands.command()
    async def trivialb(self, ctx):
        """Display the overall leaderboard."""
        async with self.config.guild(ctx.guild).trivia_scores() as scores:
            overall_scores = {}
            for category_scores in scores.values():
                for player_id, data in category_scores.items():
                    if player_id not in overall_scores:
                        overall_scores[player_id] = {"total_score": 0, "games_played": 0, "weekly_score": 0}
                    overall_scores[player_id]["total_score"] += data["total_score"]
                    overall_scores[player_id]["games_played"] += data["games_played"]
                    overall_scores[player_id]["weekly_score"] += data["weekly_score"]

            leaderboard = sorted(overall_scores.items(), key=lambda x: x[1]["total_score"], reverse=True)
            embed = discord.Embed(
                title="🏆 Overall Trivia Leaderboard 🏆",
                color=discord.Color.gold()
            )

            if not leaderboard:
                embed.description = "No players have participated in trivia yet."
            else:
                for player_id, data in leaderboard[:10]:
                    player = self.bot.get_user(int(player_id))
                    if player:
                        embed.add_field(
                            name=player.display_name,
                            value=(f"Total Points: {data['total_score']}\n"
                                   f"Games Played: {data['games_played']}\n"
                                   f"Points This Week: {data['weekly_score']}"),
                            inline=False
                        )

            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()  # Restrict this command to the bot owner
    async def triviaupload(self, ctx):
        """Upload or update custom YAML files for trivia."""
        if not ctx.message.attachments:
            await ctx.send("Arrr! Ye need to attach YAML files with yer trivia questions, ye scurvy dog!")
            return

        for attachment in ctx.message.attachments:
            if not attachment.filename.endswith(('.yaml', '.yml')):
                await ctx.send(f"Blimey! The attached file {attachment.filename} must be a YAML file (with .yaml or .yml extension).")
                continue

            try:
                content = await attachment.read()
                questions = yaml.safe_load(content)

                # Validate the structure of the YAML file
                if not isinstance(questions, list):
                    raise ValueError("Shiver me timbers! The YAML file should contain a list of questions.")

                for question in questions:
                    if not all(key in question for key in ['question', 'answers', 'hints', 'difficulty']):
                        raise ValueError("Avast! Each question must have 'question', 'answers', 'hints', and 'difficulty' fields.")
                    if 'image' in question and not isinstance(question['image'], str):
                        raise ValueError("Avast! The 'image' field must be a string containing a valid URL.")

                # Get the category name from the filename (without .yaml or .yml extension)
                category = attachment.filename.rsplit('.', 1)[0].lower()
                category = category.replace('_questions', '')  # Remove '_questions' if present

                # Save the questions to the bot's data folder
                file_path = Path(f"/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/Trivia/Categories/{category}_questions.yaml")

                # Ensure the directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)

                action = "updated" if file_path.exists() else "uploaded"

                with file_path.open('wb') as f:
                    f.write(content)

                # Load the new questions into memory
                self.questions[f"{category}_questions"] = questions

                await ctx.send(f"Ahoy! Successfully {action} and loaded {len(questions)} questions for the '{category}' category.\n"
                               f"File saved at: {file_path}")

            except yaml.YAMLError as e:
                await ctx.send(f"Blimey! YAML parsing error in file {attachment.filename}: {str(e)}")
            except Exception as e:
                await ctx.send(f"Blimey! An error occurred while processing the file {attachment.filename}: {str(e)}")
                LOG.error(f"Error in triviaupload: {str(e)}", exc_info=True)

        # Reload trivia questions to ensure all categories are up to date
        await self.initialize_questions()

    @triviaupload.error
    async def triviaupload_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("Only the bot owner can upload new trivia questions.")
        else:
            await ctx.send(f"An error occurred: {str(error)}")

    @commands.command()
    async def trivialist(self, ctx):
        """List all available trivia categories."""
        if not self.questions:
            await ctx.send("Shiver me timbers! There be no trivia categories available, ye scurvy dog!")
            return

        categories = [cat.replace('_questions', '') for cat in self.questions.keys()]
        categories.sort()

        category_list = "\n".join([f"• {category}" for category in categories])

        embed = discord.Embed(
            title="🏴‍☠️ Available Trivia Categories 🏴‍☠️",
            description=box(category_list, lang=""),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Use .trivia <category> to start a game!")

        await ctx.send(embed=embed)

    @trivialist.error
    async def trivialist_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            remaining_time = round(error.retry_after)
            await ctx.send(f"Avast ye, {ctx.author.mention}! Ye be askin' too quick! "
                           f"Wait another {remaining_time} seconds before checkin' the categories again, ye eager pirate!")

    @commands.command()
    async def triviastop(self, ctx):
        """Stop the current trivia game."""
        if ctx.channel.id not in self.trivia_sessions:
            await ctx.send("There's no active trivia game in this channel, ye confused sea dog!")
            return

        self.trivia_sessions[ctx.channel.id]["active"] = False
        await ctx.send("The trivia game has been stopped by the captain's orders!")
        await self.end_game(ctx)

    @commands.command()
    @commands.is_owner()
    async def reload_trivia(self, ctx):
        """Manually reload trivia questions."""
        await ctx.send("Reloading trivia questions...")
        await self.initialize_questions()
        categories = ", ".join(self.questions.keys())
        await ctx.send(f"Trivia questions reloaded. Available categories: {categories}")

    @commands.command()
    async def daily_challenge(self, ctx):
        """Start a daily trivia challenge."""
        await self.trivia(ctx, category="daily")

    @commands.command()
    async def weekly_challenge(self, ctx):
        """Start a weekly trivia challenge."""
        await self.trivia(ctx, category="weekly")

    @commands.command()
    async def points(self, ctx):
        """Display the user's current points."""
        user = ctx.author
        if ctx.channel.id not in self.trivia_sessions:
            return await ctx.send("There's no active trivia game in this channel, ye confused sea dog!")

        scores = self.trivia_sessions[ctx.channel.id]["scores"]
        user_score = scores.get(user, 0)
        await ctx.send(f"{user.display_name}, ye have {user_score} points in the current trivia game!")
