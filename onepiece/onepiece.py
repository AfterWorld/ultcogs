"""
One Piece Discord Bot Cog for Red Discord Bot
Compatible with discord.py 2.0+

This file contains the main OnePiece cog implementation with all features:
1. "Who Am I?" character guessing game
2. Episode Quote Challenge
3. Weekly Watch/Read Along scheduler
4. One Piece API Dashboard
5. Character Birthday Celebrations
6. Devil Fruit Encyclopedia
"""

import discord
import asyncio
import aiohttp
import json
import random
import os
import datetime
from typing import Dict, List, Optional, Union, Literal
from redbot.core import commands, Config, checks
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import box, pagify, humanize_list

# Base URL for the One Piece API
BASE_URL = "https://api.api-onepiece.com/v2"

class OnePieceQuotes:
    """Quote handler for One Piece cog"""
    
    def __init__(self, bot):
        self.bot = bot
        self.quotes_file = cog_data_path(self) / "quotes.json"
        self.quotes_data = self.load_quotes()
        
    def load_quotes(self) -> dict:
        """Load quotes from JSON file, creating default if not exists"""
        if not os.path.exists(self.quotes_file):
            # Create default quotes file with sample quotes
            default_quotes = {
                "episodes": {
                    "1": {
                        "title": "I'm Luffy! The Man Who Will Become the Pirate King!",
                        "quotes": [
                            {"character": "Monkey D. Luffy", "text": "I'm going to be King of the Pirates!"},
                            {"character": "Monkey D. Luffy", "text": "I ate the Gum-Gum Fruit and became a rubber person!"},
                            {"character": "Koby", "text": "That's impossible! Impossible, impossible! Absolutely impossible!"}
                        ]
                    },
                    "2": {
                        "title": "Enter the Great Swordsman! Pirate Hunter Roronoa Zoro!",
                        "quotes": [
                            {"character": "Roronoa Zoro", "text": "I'm going to be the world's greatest swordsman! All I have left is my destiny! My name may be infamous, but it's gonna shake the world!"},
                            {"character": "Monkey D. Luffy", "text": "If you fight with me now, either way, you'd be going against your code! So how about it? Son of the devil."}
                        ]
                    },
                    "3": {
                        "title": "Morgan versus Luffy! Who's the Mysterious Pretty Girl?",
                        "quotes": [
                            {"character": "Nami", "text": "I love money and tangerines!"},
                            {"character": "Monkey D. Luffy", "text": "I've decided that you're going to join my crew!"}
                        ]
                    },
                    "19": {
                        "title": "Past the Limits! Luffy's Rapid-Fire Fists Explode!",
                        "quotes": [
                            {"character": "Monkey D. Luffy", "text": "I don't care if you're a good person! I don't care if you're a gangster! It has nothing to do with me! But a friend who feeds someone who's hungry is a friend of mine!"},
                            {"character": "Sanji", "text": "Food should never be wasted. No matter what happens."}
                        ]
                    },
                    "24": {
                        "title": "Hawk-Eye Mihawk! Swordsman Zoro Falls into the Sea!",
                        "quotes": [
                            {"character": "Dracule Mihawk", "text": "It's been a while since I've seen such strong will. As a swordsman courtesy demands I send you to your death with my black blade, the finest in the world."},
                            {"character": "Roronoa Zoro", "text": "I promise I will never lose again! Until I defeat him and become the greatest swordsman, I'll never be defeated again! Got a problem with that, King of the Pirates?"},
                            {"character": "Monkey D. Luffy", "text": "Nope!"}
                        ]
                    },
                    "37": {
                        "title": "Luffy Stands Up! End of the Fishman Empire!",
                        "quotes": [
                            {"character": "Monkey D. Luffy", "text": "Of course I don't know how to use a sword, you idiot! I don't know how to navigate either! I can't cook! I can't even lie! I know I need friends to help me if I want to keep sailing!"}
                        ]
                    },
                    "45": {
                        "title": "Bounty! Wanted Luffy and the Straw Hat Pirates!",
                        "quotes": [
                            {"character": "Monkey D. Luffy", "text": "Thirty million berries? That's great!"},
                            {"character": "Sanji", "text": "Why am I not on a wanted poster? Why just these three?!"}
                        ]
                    },
                    "483": {
                        "title": "Looking for the Answer! Fire Fist Ace Dies on the Battlefield!",
                        "quotes": [
                            {"character": "Portgas D. Ace", "text": "Thank you... for loving me!"}
                        ]
                    },
                    "517": {
                        "title": "Gathering of the Straw Hat Crew! Luffy's Earnest Wish!",
                        "quotes": [
                            {"character": "Monkey D. Luffy", "text": "I still want to see them! I've gotten stronger these past two years... and they have too! I'm sure of it!"}
                        ]
                    },
                    "877": {
                        "title": "A Hard Battle Starts! Luffy vs. Katakuri!",
                        "quotes": [
                            {"character": "Charlotte Katakuri", "text": "If you've come this far just to be overwhelmed, then your journey is over."},
                            {"character": "Monkey D. Luffy", "text": "I get stronger as I fight!"}
                        ]
                    }
                },
                "characters": [
                    "Monkey D. Luffy",
                    "Roronoa Zoro",
                    "Nami",
                    "Usopp",
                    "Sanji",
                    "Tony Tony Chopper",
                    "Nico Robin",
                    "Franky",
                    "Brook",
                    "Jinbe",
                    "Portgas D. Ace",
                    "Dracule Mihawk",
                    "Charlotte Katakuri",
                    "Koby"
                ]
            }
            
            # Save default quotes
            with open(self.quotes_file, 'w', encoding='utf-8') as f:
                json.dump(default_quotes, f, indent=4)
            
            return default_quotes
        else:
            # Load existing quotes
            try:
                with open(self.quotes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, create a new one
                os.remove(self.quotes_file)
                return self.load_quotes()

    def save_quotes(self):
        """Save quotes to JSON file"""
        with open(self.quotes_file, 'w', encoding='utf-8') as f:
            json.dump(self.quotes_data, f, indent=4)

    async def get_random_quote(self) -> dict:
        """Get a random quote from the quotes database"""
        # Get a list of episodes that have quotes
        episodes = list(self.quotes_data["episodes"].keys())
        
        if not episodes:
            return {"error": "No quotes available"}
        
        # Select a random episode
        random_episode_id = random.choice(episodes)
        episode_data = self.quotes_data["episodes"][random_episode_id]
        
        # Check if the episode has quotes
        if not episode_data.get("quotes", []):
            return {"error": f"No quotes found for episode {random_episode_id}"}
        
        # Select a random quote
        random_quote = random.choice(episode_data["quotes"])
        
        return {
            "quote": random_quote["text"],
            "character": random_quote["character"],
            "episode": random_episode_id,
            "title": episode_data.get("title", f"Episode {random_episode_id}")
        }
        
    async def add_quote(self, episode_id: str, character: str, quote_text: str, episode_title: str = None) -> bool:
        """Add a new quote to the database"""
        # Ensure character exists
        if character not in self.quotes_data["characters"]:
            self.quotes_data["characters"].append(character)
        
        # Ensure episode exists
        if episode_id not in self.quotes_data["episodes"]:
            self.quotes_data["episodes"][episode_id] = {
                "title": episode_title or f"Episode {episode_id}",
                "quotes": []
            }
        
        # Add the quote
        self.quotes_data["episodes"][episode_id]["quotes"].append({
            "character": character,
            "text": quote_text
        })
        
        # Save changes
        self.save_quotes()
        
        return True
        
    async def get_quote_by_character(self, character: str) -> dict:
        """Get a random quote from a specific character"""
        # Find all quotes by this character
        character_quotes = []
        
        for episode_id, episode_data in self.quotes_data["episodes"].items():
            for quote in episode_data.get("quotes", []):
                if quote["character"].lower() == character.lower():
                    character_quotes.append({
                        "quote": quote["text"],
                        "character": quote["character"],
                        "episode": episode_id,
                        "title": episode_data.get("title", f"Episode {episode_id}")
                    })
        
        if not character_quotes:
            return {"error": f"No quotes found for character {character}"}
        
        # Select a random quote
        return random.choice(character_quotes)
        
    async def get_quote_by_episode(self, episode_id: str) -> dict:
        """Get a random quote from a specific episode"""
        # Check if episode exists
        if episode_id not in self.quotes_data["episodes"]:
            return {"error": f"Episode {episode_id} not found"}
        
        # Check if episode has quotes
        episode_data = self.quotes_data["episodes"][episode_id]
        if not episode_data.get("quotes", []):
            return {"error": f"No quotes found for episode {episode_id}"}
        
        # Select a random quote
        random_quote = random.choice(episode_data["quotes"])
        
        return {
            "quote": random_quote["text"],
            "character": random_quote["character"],
            "episode": episode_id,
            "title": episode_data.get("title", f"Episode {episode_id}")
        }

class OnePiece(commands.Cog):
    """One Piece themed features using the One Piece API"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1073977086, force_registration=True)
        
        # Default settings
        default_guild = {
            "whoami_channel": None,
            "whoami_active": False,
            "whoami_scores": {},
            "quote_channel": None,
            "quote_active": False,
            "quote_scores": {},
            "dashboard_channel": None,
            "daily_fact_time": "12:00",  # Noon by default
            "weekly_watchalong_channel": None, 
            "current_watchalong": None,
            "watchalong_day": 6,  # Saturday by default
            "watchalong_time": "18:00",  # 6 PM by default
            "last_birthday_check": None
        }
        
        self.config.register_guild(**default_guild)
        
        # Cache for active games
        self.active_whoami = {}  # guild_id: {"character": data, "clues": [], "current_clue": 0}
        self.active_quotes = {}  # guild_id: {"quote": text, "character": name, "episode": num}
        
        # Set up quotes handler
        self.quotes_handler = OnePieceQuotes(bot)
        
        # Start background tasks when cog is loaded
        self.bg_tasks = []
        self.start_background_tasks()
        
    def start_background_tasks(self):
        """Start all background tasks"""
        self.bg_tasks.append(self.bot.loop.create_task(self.birthday_announcer()))
        self.bg_tasks.append(self.bot.loop.create_task(self.daily_fact_poster()))
        self.bg_tasks.append(self.bot.loop.create_task(self.watchalong_reminder()))
        
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        for task in self.bg_tasks:
            task.cancel()

    # API Helper Methods
    async def api_request(self, endpoint: str, language: str = "en") -> dict:
        """Make a request to the One Piece API"""
        url = f"{BASE_URL}/{endpoint}/{language}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API request failed with status {response.status}"}

    async def get_random_character(self) -> dict:
        """Get a random character from the API"""
        characters = await self.api_request("characters")
        if "error" in characters:
            return {"error": "Failed to get characters"}
        
        random_char = random.choice(characters)
        char_id = random_char.get("_id", "")
        
        # Get detailed character info
        character_details = await self.api_request(f"characters/{char_id}")
        return character_details

    async def get_character_clues(self, character: dict) -> List[str]:
        """Generate clues for a character"""
        clues = []
        
        # Obscure clues first
        if character.get("affiliations"):
            clues.append(f"This character is affiliated with {random.choice(character['affiliations'])}")
        
        if character.get("occupations"):
            clues.append(f"This character's occupation is {random.choice(character['occupations'])}")
        
        if character.get("status"):
            clues.append(f"This character's status is {character['status']}")
        
        if character.get("devil_fruit"):
            clues.append(f"This character has eaten a Devil Fruit")
        
        # More specific clues
        if character.get("epithet"):
            clues.append(f"This character is known as '{character['epithet']}'")
        
        if character.get("bounty"):
            clues.append(f"This character has a bounty of {character['bounty']}")
        
        if character.get("crew"):
            clues.append(f"This character is a member of the {character['crew']} crew")
        
        # Shuffle to make it more interesting
        random.shuffle(clues)
        
        # Always add these clues last
        if character.get("origin"):
            clues.append(f"This character comes from {character['origin']}")
        
        if character.get("first_appearance"):
            clues.append(f"This character first appeared in {character['first_appearance']}")
        
        return clues

    #################################################
    # 1. "WHO AM I?" GAME IMPLEMENTATION
    #################################################
    
    @commands.group(name="whoami")
    @commands.guild_only()
    async def _whoami(self, ctx):
        """Commands for the One Piece 'Who Am I?' game"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @_whoami.command(name="setup")
    @commands.admin_or_permissions(manage_guild=True)
    async def whoami_setup(self, ctx, channel: discord.TextChannel = None):
        """Set up the Who Am I game channel"""
        channel = channel or ctx.channel
        
        await self.config.guild(ctx.guild).whoami_channel.set(channel.id)
        await ctx.send(f"Who Am I game has been set up in {channel.mention}!")
    
    @_whoami.command(name="start")
    @commands.admin_or_permissions(manage_guild=True)
    async def whoami_start(self, ctx):
        """Start the Who Am I game"""
        channel_id = await self.config.guild(ctx.guild).whoami_channel()
        if not channel_id:
            return await ctx.send("Please set up the game channel first with `!whoami setup`")
        
        await self.config.guild(ctx.guild).whoami_active.set(True)
        await ctx.send("Who Am I game has been activated! A new character will appear shortly.")
        
        # Start the first round
        await self.new_whoami_round(ctx.guild.id)
    
    @_whoami.command(name="stop")
    @commands.admin_or_permissions(manage_guild=True)
    async def whoami_stop(self, ctx):
        """Stop the Who Am I game"""
        await self.config.guild(ctx.guild).whoami_active.set(False)
        
        # Clear active game
        if ctx.guild.id in self.active_whoami:
            del self.active_whoami[ctx.guild.id]
            
        await ctx.send("Who Am I game has been deactivated.")
    
    @_whoami.command(name="scores")
    async def whoami_scores(self, ctx):
        """Show the Who Am I game leaderboard"""
        scores = await self.config.guild(ctx.guild).whoami_scores()
        
        if not scores:
            return await ctx.send("No scores recorded yet!")
        
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create leaderboard
        leaderboard = ["**Who Am I Game Leaderboard**\n"]
        
        for i, (user_id, score) in enumerate(sorted_scores, 1):
            user = ctx.guild.get_member(int(user_id))
            username = user.display_name if user else f"User {user_id}"
            leaderboard.append(f"{i}. {username}: {score} points")
        
        await ctx.send("\n".join(leaderboard))
    
    @_whoami.command(name="clue")
    async def whoami_clue(self, ctx):
        """Get the next clue for the current Who Am I game"""
        if ctx.guild.id not in self.active_whoami:
            return await ctx.send("There's no active Who Am I game!")
        
        channel_id = await self.config.guild(ctx.guild).whoami_channel()
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            return await ctx.send("Game channel not found!")
        
        game_data = self.active_whoami[ctx.guild.id]
        
        if game_data["current_clue"] >= len(game_data["clues"]):
            await channel.send("All clues have been revealed! Make your guesses now!")
        else:
            clue = game_data["clues"][game_data["current_clue"]]
            game_data["current_clue"] += 1
            
            await channel.send(f"**Clue #{game_data['current_clue']}**: {clue}")
    
    async def new_whoami_round(self, guild_id: int):
        """Start a new round of Who Am I"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel_id = await self.config.guild(guild).whoami_channel()
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            return
        
        # Check if the game is active
        if not await self.config.guild(guild).whoami_active():
            return
        
        # Get a random character
        character = await self.get_random_character()
        if "error" in character:
            await channel.send("Error getting a character! Try again later.")
            return
        
        # Generate clues
        clues = await self.get_character_clues(character)
        
        # Store the game data
        self.active_whoami[guild_id] = {
            "character": character,
            "clues": clues,
            "current_clue": 0
        }
        
        # Send the first message
        await channel.send("**New 'Who Am I?' round!**\n\nI'm thinking of a One Piece character. Use `!whoami clue` to get clues and make your guesses in this channel!")
        
        # Send the first clue
        ctx = commands.Context(bot=self.bot, guild=guild, channel=channel)
        await self.whoami_clue(ctx)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for guesses in the Who Am I game"""
        if message.author.bot:
            return
        
        # Check if it's in a guild
        if not message.guild:
            return
            
        # Check if there's an active game
        if message.guild.id not in self.active_whoami and message.guild.id not in self.active_quotes:
            return
            
        # Process Who Am I guesses
        if message.guild.id in self.active_whoami:
            # Check if it's in the right channel
            channel_id = await self.config.guild(message.guild).whoami_channel()
            if message.channel.id == channel_id:
                # Get the game data
                game_data = self.active_whoami[message.guild.id]
                character_name = game_data["character"].get("name", "").lower()
                romanized_name = game_data["character"].get("romanized_name", "").lower()
                
                # Check if the message is a guess
                content = message.content.lower()
                
                # Skip commands
                prefixes = await self.bot.get_prefix(message)
                if isinstance(prefixes, str):
                    prefixes = [prefixes]
                
                if any(content.startswith(prefix) for prefix in prefixes):
                    return
                    
                # Check if the guess is correct
                if content == character_name or content == romanized_name:
                    # Update scores
                    async with self.config.guild(message.guild).whoami_scores() as scores:
                        user_id = str(message.author.id)
                        scores[user_id] = scores.get(user_id, 0) + 1
                    
                    # Announce winner
                    await message.channel.send(f"🎉 **{message.author.display_name}** got it right! The character is **{game_data['character']['name']}**!")
                    
                    # Show character info
                    embed = discord.Embed(title=game_data["character"]["name"], color=discord.Color.blue())
                    
                    if "romanized_name" in game_data["character"]:
                        embed.add_field(name="Romanized Name", value=game_data["character"]["romanized_name"], inline=True)
                        
                    if "epithet" in game_data["character"]:
                        embed.add_field(name="Epithet", value=game_data["character"]["epithet"], inline=True)
                        
                    if "occupations" in game_data["character"]:
                        embed.add_field(name="Occupations", value=", ".join(game_data["character"]["occupations"]), inline=True)
                        
                    if "crew" in game_data["character"]:
                        embed.add_field(name="Crew", value=game_data["character"]["crew"], inline=True)
                        
                    await message.channel.send(embed=embed)
                    
                    # Clean up
                    del self.active_whoami[message.guild.id]
                    
                    # Wait before starting a new round
                    await asyncio.sleep(60)
                    
                    # Start a new round
                    await self.new_whoami_round(message.guild.id)
                    
        # Process Quote Challenge guesses
        if message.guild.id in self.active_quotes:
            # Check if it's in the right channel
            channel_id = await self.config.guild(message.guild).quote_channel()
            if message.channel.id == channel_id:
                # Get the game data
                quote_data = self.active_quotes[message.guild.id]
                correct_character = quote_data["character"].lower()
                correct_episode = str(quote_data["episode"])
                
                # Check if the message is a guess
                content = message.content.lower()
                
                # Skip commands
                prefixes = await self.bot.get_prefix(message)
                if isinstance(prefixes, str):
                    prefixes = [prefixes]
                
                if any(content.startswith(prefix) for prefix in prefixes):
                    return
                    
                # Parse the guess (format: "Character, Episode")
                parts = content.split(",")
                
                if len(parts) >= 2:
                    character_guess = parts[0].strip()
                    episode_guess = parts[1].strip()
                    
                    # Check if the guess is correct
                    if character_guess == correct_character and episode_guess == correct_episode:
                        # Full correct
                        points = 2
                        result = "Both character and episode correct!"
                    elif character_guess == correct_character:
                        # Only character correct
                        points = 1
                        result = f"Character correct, but the episode was {correct_episode}!"
                    elif episode_guess == correct_episode:
                        # Only episode correct
                        points = 1
                        result = f"Episode correct, but the character was {quote_data['character']}!"
                    else:
                        # Both wrong
                        return
                        
                    # Update scores
                    async with self.config.guild(message.guild).quote_scores() as scores:
                        user_id = str(message.author.id)
                        scores[user_id] = scores.get(user_id, 0) + points
                    
                    # Announce winner
                    await message.channel.send(f"🎉 **{message.author.display_name}** gets {points} point(s)! {result}")
                    
                    # Show quote info
                    embed = discord.Embed(
                        title=f"Quote from Episode {quote_data['episode']}",
                        description=f"*\"{quote_data['quote']}\"*",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Character", value=quote_data["character"], inline=True)
                    embed.add_field(name="Episode", value=f"{quote_data['episode']} - {quote_data['title']}", inline=True)
                    
                    await message.channel.send(embed=embed)
                    
                    # Clean up
                    del self.active_quotes[message.guild.id]
                    
                    # Wait before starting a new round
                    await asyncio.sleep(60)
                    
                    # Start a new round
                    await self.new_quote_round(message.guild.id)

    #################################################
    # 2. EPISODE QUOTE CHALLENGE
    #################################################
    
    @commands.group(name="quote")
    @commands.guild_only()
    async def _quote(self, ctx):
        """Commands for the One Piece Quote Challenge"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @_quote.command(name="setup")
    @commands.admin_or_permissions(manage_guild=True)
    async def quote_setup(self, ctx, channel: discord.TextChannel = None):
        """Set up the Quote Challenge channel"""
        channel = channel or ctx.channel
        
        await self.config.guild(ctx.guild).quote_channel.set(channel.id)
        await ctx.send(f"Quote Challenge has been set up in {channel.mention}!")
    
    @_quote.command(name="start")
    @commands.admin_or_permissions(manage_guild=True)
    async def quote_start(self, ctx):
        """Start the Quote Challenge"""
        channel_id = await self.config.guild(ctx.guild).quote_channel()
        if not channel_id:
            return await ctx.send("Please set up the game channel first with `!quote setup`")
        
        await self.config.guild(ctx.guild).quote_active.set(True)
        await ctx.send("Quote Challenge has been activated! A new quote will appear shortly.")
        
        # Start the first round
        await self.new_quote_round(ctx.guild.id)
    
    @_quote.command(name="stop")
    @commands.admin_or_permissions(manage_guild=True)
    async def quote_stop(self, ctx):
        """Stop the Quote Challenge"""
        await self.config.guild(ctx.guild).quote_active.set(False)
        
        # Clear active game
        if ctx.guild.id in self.active_quotes:
            del self.active_quotes[ctx.guild.id]
            
        await ctx.send("Quote Challenge has been deactivated.")
    
    @_quote.command(name="scores")
    async def quote_scores(self, ctx):
        """Show the Quote Challenge leaderboard"""
        scores = await self.config.guild(ctx.guild).quote_scores()
        
        if not scores:
            return await ctx.send("No scores recorded yet!")
        
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create leaderboard
        leaderboard = ["**Quote Challenge Leaderboard**\n"]
        
        for i, (user_id, score) in enumerate(sorted_scores, 1):
            user = ctx.guild.get_member(int(user_id))
            username = user.display_name if user else f"User {user_id}"
            leaderboard.append(f"{i}. {username}: {score} points")
        
        await ctx.send("\n".join(leaderboard))
    
    @_quote.command(name="add")
    @commands.admin_or_permissions(manage_guild=True)
    async def quote_add(self, ctx, episode_id: str, character: str, *, quote_text: str):
        """Add a new quote to the database"""
        await self.quotes_handler.add_quote(episode_id, character, quote_text)
        await ctx.send(f"Quote added for {character} in episode {episode_id}!")
    
    async def new_quote_round(self, guild_id: int):
        """Start a new round of Quote Challenge"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel_id = await self.config.guild(guild).quote_channel()
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            return
        
        # Check if the game is active
        if not await self.config.guild(guild).quote_active():
            return
        
        # Get a random quote using the quotes handler
        quote_data = await self.quotes_handler.get_random_quote()
        if "error" in quote_data:
            await channel.send("Error getting a quote! Try adding more quotes with `!quote add`.")
            return
        
        # Store the game data
        self.active_quotes[guild_id] = quote_data
        
        # Send the quote
        embed = discord.Embed(
            title="📜 Quote Challenge",
            description=f"**Who said this and in which episode?**\n\n*\"{quote_data['quote']}\"*",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Type your guess in this channel! Format: 'Character Name, Episode Number'")
        
        await channel.send(embed=embed)

    #################################################
    # 3. WEEKLY WATCH/READ ALONG
    #################################################
    
    @commands.group(name="watchalong")
    @commands.guild_only()
    async def _watchalong(self, ctx):
        """Commands for the One Piece Watch/Read Along"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @_watchalong.command(name="setup")
    @commands.admin_or_permissions(manage_guild=True)
    async def watchalong_setup(self, ctx, channel: discord.TextChannel = None):
        """Set up the Watch/Read Along channel"""
        channel = channel or ctx.channel
        
        await self.config.guild(ctx.guild).weekly_watchalong_channel.set(channel.id)
        await ctx.send(f"Watch/Read Along has been set up in {channel.mention}!")
    
    @_watchalong.command(name="schedule")
    @commands.admin_or_permissions(manage_guild=True)
    async def watchalong_schedule(self, ctx, day: int, time: str):
        """
        Schedule the weekly watchalong
        
        Day should be a number from 0-6 (0 is Monday, 6 is Sunday)
        Time should be in 24-hour format like "18:00"
        """
        if day < 0 or day > 6:
            return await ctx.send("Day must be between 0 (Monday) and 6 (Sunday)")
        
        # Validate time format
        try:
            datetime.datetime.strptime(time, "%H:%M")
        except ValueError:
            return await ctx.send("Time must be in 24-hour format like '18:00'")
        
        await self.config.guild(ctx.guild).watchalong_day.set(day)
        await self.config.guild(ctx.guild).watchalong_time.set(time)
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        await ctx.send(f"Watch/Read Along scheduled for every {days[day]} at {time}!")
    
    @_watchalong.command(name="set")
    @commands.admin_or_permissions(manage_guild=True)
    async def watchalong_set(self, ctx, content_type: str, number: str):
        """
        Set the current episode or chapter to watch/read
        
        Content type should be either "episode" or "chapter"
        Number should be the episode or chapter number
        """
        if content_type.lower() not in ["episode", "chapter"]:
            return await ctx.send("Content type must be either 'episode' or 'chapter'")
        
        content = {
            "type": content_type.lower(),
            "number": number
        }
        
        await self.config.guild(ctx.guild).current_watchalong.set(content)
        await ctx.send(f"Next watch/read along set to {content_type} {number}!")
    
    @_watchalong.command(name="info")
    async def watchalong_info(self, ctx):
        """Show information about the current watch/read along"""
        watchalong = await self.config.guild(ctx.guild).current_watchalong()
        if not watchalong:
            return await ctx.send("No watch/read along currently scheduled!")
        
        day = await self.config.guild(ctx.guild).watchalong_day()
        time = await self.config.guild(ctx.guild).watchalong_time()
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        embed = discord.Embed(
            title="📺 Weekly Watch/Read Along",
            description=f"Join us every {days[day]} at {time} for our community One Piece watch/read along!",
            color=discord.Color.purple()
        )
        
        content_type = watchalong["type"]
        content_number = watchalong["number"]
        
        if content_type == "episode":
            # Get episode info from API
            episode_data = await self.api_request(f"episodes/{content_number}")
            
            if "error" not in episode_data:
                embed.add_field(name="Next Episode", value=f"Episode {content_number}: {episode_data.get('title', 'Unknown')}", inline=False)
                
                if "release" in episode_data:
                    embed.add_field(name="Release Date", value=episode_data["release"], inline=True)
                    
                if "characters" in episode_data:
                    embed.add_field(name="Featured Characters", value=", ".join(episode_data["characters"][:5]) + ("..." if len(episode_data["characters"]) > 5 else ""), inline=True)
            else:
                embed.add_field(name="Next Episode", value=f"Episode {content_number}", inline=False)
        else:
            # Get chapter info from API
            chapter_data = await self.api_request(f"chapters/{content_number}")
            
            if "error" not in chapter_data:
                embed.add_field(name="Next Chapter", value=f"Chapter {content_number}: {chapter_data.get('title', 'Unknown')}", inline=False)
                
                if "release" in chapter_data:
                    embed.add_field(name="Release Date", value=chapter_data["release"], inline=True)
                    
                if "volume" in chapter_data:
                    embed.add_field(name="Volume", value=chapter_data["volume"], inline=True)
            else:
                embed.add_field(name="Next Chapter", value=f"Chapter {content_number}", inline=False)
        
        channel_id = await self.config.guild(ctx.guild).weekly_watchalong_channel()
        channel = self.bot.get_channel(channel_id)
        
        if channel:
            embed.add_field(name="Where", value=channel.mention, inline=False)
        
        await ctx.send(embed=embed)
    
    async def watchalong_reminder(self):
        """Background task to send watchalong reminders"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            # Check each guild
            for guild in self.bot.guilds:
                # Get settings
                watchalong = await self.config.guild(guild).current_watchalong()
                
                if not watchalong:
                    continue
                    
                channel_id = await self.config.guild(guild).weekly_watchalong_channel()
                if not channel_id:
                    continue
                    
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                    
                day = await self.config.guild(guild).watchalong_day()
                time_str = await self.config.guild(guild).watchalong_time()
                
                # Check if it's time for a reminder
                now = datetime.datetime.now()
                
                if now.weekday() == day:
                    # Check time (30 minutes before)
                    hour, minute = map(int, time_str.split(":"))
                    reminder_time = now.replace(hour=hour, minute=minute, second=0) - datetime.timedelta(minutes=30)
                    
                    # If we're within a minute of the reminder time
                    if abs((now - reminder_time).total_seconds()) < 60:
                        # Send reminder
                        content_type = watchalong["type"]
                        content_number = watchalong["number"]
                        
                        embed = discord.Embed(
                            title="📢 Watch/Read Along Reminder",
                            description=f"Our One Piece {content_type} watch/read along will start in 30 minutes!",
                            color=discord.Color.red()
                        )
                        
                        if content_type == "episode":
                            episode_data = await self.api_request(f"episodes/{content_number}")
                            
                            if "error" not in episode_data:
                                embed.add_field(name="Episode", value=f"Episode {content_number}: {episode_data.get('title', 'Unknown')}", inline=False)
                            else:
                                embed.add_field(name="Episode", value=f"Episode {content_number}", inline=False)
                        else:
                            chapter_data = await self.api_request(f"chapters/{content_number}")
                            
                            if "error" not in chapter_data:
                                embed.add_field(name="Chapter", value=f"Chapter {content_number}: {chapter_data.get('title', 'Unknown')}", inline=False)
                            else:
                                embed.add_field(name="Chapter", value=f"Chapter {content_number}", inline=False)
                        
                        await channel.send("@everyone", embed=embed)
                    
                    # If we're within a minute of the actual event time
                    event_time = now.replace(hour=hour, minute=minute, second=0)
                    if abs((now - event_time).total_seconds()) < 60:
                        # Send start message
                        content_type = watchalong["type"]
                        content_number = watchalong["number"]
                        
                        embed = discord.Embed(
                            title="🎬 Watch/Read Along Starting Now!",
                            description=f"Our One Piece {content_type} watch/read along is starting now! Join in!",
                            color=discord.Color.green()
                        )
                        
                        if content_type == "episode":
                            episode_data = await self.api_request(f"episodes/{content_number}")
                            
                            if "error" not in episode_data:
                                embed.add_field(name="Episode", value=f"Episode {content_number}: {episode_data.get('title', 'Unknown')}", inline=False)
                                
                                if "characters" in episode_data:
                                    chars = ", ".join(episode_data["characters"][:5])
                                    if len(episode_data["characters"]) > 5:
                                        chars += "..."
                                    embed.add_field(name="Featured Characters", value=chars, inline=True)
                            else:
                                embed.add_field(name="Episode", value=f"Episode {content_number}", inline=False)
                        else:
                            chapter_data = await self.api_request(f"chapters/{content_number}")
                            
                            if "error" not in chapter_data:
                                embed.add_field(name="Chapter", value=f"Chapter {content_number}: {chapter_data.get('title', 'Unknown')}", inline=False)
                                
                                if "volume" in chapter_data:
                                    embed.add_field(name="Volume", value=chapter_data["volume"], inline=True)
                            else:
                                embed.add_field(name="Chapter", value=f"Chapter {content_number}", inline=False)
                        
                        # Add discussion questions
                        embed.add_field(
                            name="Discussion Questions",
                            value="1. What did you think of this episode/chapter?\n2. What was your favorite moment?\n3. Any predictions for what happens next?",
                            inline=False
                        )
                        
                        await channel.send("@everyone", embed=embed)
                        
                        # Increment to next episode/chapter for next week
                        next_number = str(int(content_number) + 1)
                        
                        content = {
                            "type": content_type,
                            "number": next_number
                        }
                        
                        await self.config.guild(guild).current_watchalong.set(content)
            
            # Check every minute
            await asyncio.sleep(60)

    #################################################
    # 4. ONE PIECE API DASHBOARD
    #################################################
    
    @commands.group(name="dashboard")
    @commands.guild_only()
    async def _dashboard(self, ctx):
        """Commands for the One Piece API Dashboard"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @_dashboard.command(name="setup")
    @commands.admin_or_permissions(manage_guild=True)
    async def dashboard_setup(self, ctx, channel: discord.TextChannel = None):
        """Set up the One Piece Dashboard channel"""
        channel = channel or ctx.channel
        
        await self.config.guild(ctx.guild).dashboard_channel.set(channel.id)
        await ctx.send(f"One Piece Dashboard has been set up in {channel.mention}! Daily facts will be posted here.")
    
    @_dashboard.command(name="time")
    @commands.admin_or_permissions(manage_guild=True)
    async def dashboard_time(self, ctx, time: str):
        """
        Set the daily fact posting time
        
        Time should be in 24-hour format like "12:00"
        """
        # Validate time format
        try:
            datetime.datetime.strptime(time, "%H:%M")
        except ValueError:
            return await ctx.send("Time must be in 24-hour format like '12:00'")
        
        await self.config.guild(ctx.guild).daily_fact_time.set(time)
        await ctx.send(f"Daily One Piece fact will be posted at {time}!")
    
    @_dashboard.command(name="post")
    @commands.admin_or_permissions(manage_guild=True)
    async def dashboard_post(self, ctx):
        """Manually post a One Piece fact"""
        await self.post_one_piece_fact(ctx.guild.id)
        await ctx.send("One Piece fact posted!")
    
    async def get_random_fact(self) -> dict:
        """Get a random One Piece fact"""
        # Choose a random category
        categories = ["characters", "devil_fruits", "crews", "locations", "sagas"]
        category = random.choice(categories)
        
        # Get data from the API
        data = await self.api_request(category)
        
        if "error" in data:
            return {"error": f"Failed to get {category}"}
        
        # Get a random item
        item = random.choice(data)
        item_id = item.get("_id", "")
        
        # Get detailed info
        details = await self.api_request(f"{category}/{item_id}")
        
        if "error" in details:
            return {"error": f"Failed to get {category} details"}
        
        # Create a fact based on the category
        if category == "characters":
            # Possible character facts
            fact_options = [
                f"{details.get('name', 'This character')} has a bounty of {details.get('bounty', 'unknown')}.",
                f"{details.get('name', 'This character')} first appeared in {details.get('first_appearance', 'an unknown chapter/episode')}.",
                f"{details.get('name', 'This character')} is from {details.get('origin', 'an unknown location')}.",
                f"{details.get('name', 'This character')} is a member of the {details.get('crew', 'unknown')} crew.",
                f"{details.get('name', 'This character')} is known as '{details.get('epithet', 'unknown')}'."
            ]
            
            # Filter out facts with "unknown" values
            valid_facts = [f for f in fact_options if "unknown" not in f.lower()]
            
            fact = random.choice(valid_facts) if valid_facts else fact_options[0]
            return {"fact": fact, "category": "Character", "name": details.get('name', 'Unknown')}
            
        elif category == "devil_fruits":
            fact = f"The {details.get('name', 'Unknown')} Devil Fruit is a {details.get('type', 'Unknown')} type fruit that {details.get('description', 'grants an unknown power')}."
            return {"fact": fact, "category": "Devil Fruit", "name": details.get('name', 'Unknown')}
            
        elif category == "crews":
            fact = f"The {details.get('name', 'Unknown')} crew is captained by {details.get('captain', 'an unknown pirate')} and has a total bounty of {details.get('total_bounty', 'unknown')}."
            return {"fact": fact, "category": "Pirate Crew", "name": details.get('name', 'Unknown')}
            
        elif category == "locations":
            fact = f"{details.get('name', 'This location')} is located in {details.get('region', 'an unknown region')} and is known for {details.get('description', 'something interesting')}."
            return {"fact": fact, "category": "Location", "name": details.get('name', 'Unknown')}
            
        elif category == "sagas":
            fact = f"The {details.get('name', 'Unknown')} saga consists of {len(details.get('arcs', []))} arcs and features {details.get('main_antagonist', 'various antagonists')} as the main antagonist."
            return {"fact": fact, "category": "Saga", "name": details.get('name', 'Unknown')}
            
        return {"error": "Failed to generate fact"}
    
    async def post_one_piece_fact(self, guild_id: int):
        """Post a random One Piece fact to the dashboard channel"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel_id = await self.config.guild(guild).dashboard_channel()
        if not channel_id:
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        # Get a random fact
        fact_data = await self.get_random_fact()
        
        if "error" in fact_data:
            return
        
        # Create an embed
        embed = discord.Embed(
            title=f"📊 Daily One Piece Fact: {fact_data['category']}",
            description=fact_data["fact"],
            color=discord.Color.blue()
        )
        
        embed.set_footer(text=f"Use .devilfruit, .character, or other commands to learn more about {fact_data['name']}!")
        
        # Add timestamp
        embed.timestamp = datetime.datetime.now()
        
        await channel.send(embed=embed)
    
    async def daily_fact_poster(self):
        """Background task to post daily One Piece facts"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            # Check each guild
            for guild in self.bot.guilds:
                channel_id = await self.config.guild(guild).dashboard_channel()
                if not channel_id:
                    continue
                    
                time_str = await self.config.guild(guild).daily_fact_time()
                
                # Check if it's time to post
                now = datetime.datetime.now()
                hour, minute = map(int, time_str.split(":"))
                post_time = now.replace(hour=hour, minute=minute, second=0)
                
                # If we're within a minute of the post time
                if abs((now - post_time).total_seconds()) < 60:
                    await self.post_one_piece_fact(guild.id)
            
            # Check every minute
            await asyncio.sleep(60)

    #################################################
    # 5. CHARACTER BIRTHDAY CELEBRATIONS
    #################################################
    
    async def get_todays_birthdays(self) -> List[dict]:
        """Get characters with birthdays today"""
        today = datetime.datetime.now()
        month = today.month
        day = today.day
        
        # Get all characters
        characters = await self.api_request("characters")
        
        if "error" in characters:
            return []
        
        birthday_chars = []
        
        for char in characters:
            char_id = char.get("_id", "")
            
            # Get detailed character info
            character_details = await self.api_request(f"characters/{char_id}")
            
            if "error" in character_details:
                continue
            
            # Check if birthday matches today
            if "birthday" in character_details:
                birthday = character_details["birthday"]
                
                # Parse the birthday (assuming format like "May 5th")
                try:
                    birthday_date = datetime.datetime.strptime(birthday, "%B %d")
                    if birthday_date.month == month and birthday_date.day == day:
                        birthday_chars.append(character_details)
                except ValueError:
                    # Try alternative format (e.g., "May 5")
                    try:
                        birthday_date = datetime.datetime.strptime(birthday, "%B %d")
                        if birthday_date.month == month and birthday_date.day == day:
                            birthday_chars.append(character_details)
                    except ValueError:
                        continue
        
        return birthday_chars
    
    async def birthday_announcer(self):
        """Background task to announce character birthdays"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            today = datetime.datetime.now().date()
            
            # Check each guild
            for guild in self.bot.guilds:
                # Get last check date
                last_check = await self.config.guild(guild).last_birthday_check()
                
                if last_check:
                    last_check_date = datetime.datetime.strptime(last_check, "%Y-%m-%d").date()
                    
                    # Skip if we already checked today
                    if last_check_date == today:
                        continue
                
                # Get dashboard channel
                channel_id = await self.config.guild(guild).dashboard_channel()
                if not channel_id:
                    continue
                    
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                
                # Get characters with birthdays today
                birthday_chars = await self.get_todays_birthdays()
                
                if birthday_chars:
                    # Create a birthday announcement
                    embed = discord.Embed(
                        title="🎂 One Piece Character Birthdays Today!",
                        description=f"Today is the birthday of {len(birthday_chars)} One Piece character(s)!",
                        color=discord.Color.gold()
                    )
                    
                    for char in birthday_chars:
                        name = char.get("name", "Unknown")
                        epithet = char.get("epithet", "")
                        name_display = f"{name} '{epithet}'" if epithet else name
                        
                        field_value = []
                        
                        if "crew" in char:
                            field_value.append(f"Crew: {char['crew']}")
                            
                        if "bounty" in char:
                            field_value.append(f"Bounty: {char['bounty']}")
                        
                        if "birthday" in char:
                            field_value.append(f"Birthday: {char['birthday']}")
                        
                        embed.add_field(
                            name=name_display,
                            value="\n".join(field_value) or "Happy Birthday!",
                            inline=False
                        )
                    
                    await channel.send("🎉 **Character Birthday Alert!** 🎉", embed=embed)
                
                # Update last check date
                await self.config.guild(guild).last_birthday_check.set(today.strftime("%Y-%m-%d"))
            
            # Check once a day (at midnight)
            now = datetime.datetime.now()
            tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0)
            seconds_until_midnight = (tomorrow - now).total_seconds()
            
            await asyncio.sleep(seconds_until_midnight)

    #################################################
    # 6. DEVIL FRUIT ENCYCLOPEDIA
    #################################################
    
    @commands.group(name="devilfruit")
    @commands.guild_only()
    async def _devilfruit(self, ctx):
        """Commands for looking up Devil Fruit information"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @_devilfruit.command(name="search")
    async def devilfruit_search(self, ctx, *, name: str):
        """Search for a Devil Fruit by name"""
        # Get all devil fruits
        devil_fruits = await self.api_request("devil_fruits")
        
        if "error" in devil_fruits:
            return await ctx.send("Failed to retrieve Devil Fruit data. Try again later.")
        
        # Find matching fruits
        name_lower = name.lower()
        matches = []
        
        for fruit in devil_fruits:
            fruit_name = fruit.get("name", "").lower()
            fruit_id = fruit.get("_id", "")
            
            if name_lower in fruit_name:
                matches.append(fruit_id)
        
        if not matches:
            return await ctx.send(f"No Devil Fruits found matching '{name}'.")
        
        if len(matches) == 1:
            # Get detailed info for the single match
            return await self.show_devil_fruit(ctx, matches[0])
        else:
            # Show multiple matches
            embed = discord.Embed(
                title="Multiple Devil Fruits Found",
                description=f"Found {len(matches)} Devil Fruits matching '{name}'.",
                color=discord.Color.purple()
            )
            
            for i, fruit_id in enumerate(matches[:10], 1):
                # Get fruit details
                fruit = await self.api_request(f"devil_fruits/{fruit_id}")
                
                if "error" not in fruit:
                    embed.add_field(
                        name=f"{i}. {fruit.get('name', 'Unknown')}",
                        value=f"Type: {fruit.get('type', 'Unknown')}\nUse `.devilfruit info {fruit_id}` for details",
                        inline=True
                    )
            
            if len(matches) > 10:
                embed.set_footer(text=f"Showing 10 of {len(matches)} matches. Please refine your search.")
            
            await ctx.send(embed=embed)
    
    @_devilfruit.command(name="info")
    async def devilfruit_info(self, ctx, fruit_id: str):
        """Get detailed information about a Devil Fruit by ID"""
        await self.show_devil_fruit(ctx, fruit_id)
    
    @_devilfruit.command(name="random")
    async def devilfruit_random(self, ctx):
        """Get information about a random Devil Fruit"""
        # Get all devil fruits
        devil_fruits = await self.api_request("devil_fruits")
        
        if "error" in devil_fruits:
            return await ctx.send("Failed to retrieve Devil Fruit data. Try again later.")
        
        # Get a random fruit
        random_fruit = random.choice(devil_fruits)
        fruit_id = random_fruit.get("_id", "")
        
        await self.show_devil_fruit(ctx, fruit_id)
    
    async def show_devil_fruit(self, ctx, fruit_id: str):
        """Display detailed information about a Devil Fruit"""
        # Get detailed fruit info
        fruit = await self.api_request(f"devil_fruits/{fruit_id}")
        
        if "error" in fruit:
            return await ctx.send(f"Failed to retrieve Devil Fruit with ID '{fruit_id}'.")
        
        # Create an embed
        embed = discord.Embed(
            title=f"🍎 {fruit.get('name', 'Unknown Devil Fruit')}",
            description=fruit.get('description', 'No description available.'),
            color=discord.Color.orange()
        )
        
        # Add fields
        if "type" in fruit:
            embed.add_field(name="Type", value=fruit["type"], inline=True)
        
        if "japanese_name" in fruit:
            embed.add_field(name="Japanese Name", value=fruit["japanese_name"], inline=True)
        
        if "meaning" in fruit:
            embed.add_field(name="Meaning", value=fruit["meaning"], inline=True)
        
        if "current_user" in fruit:
            embed.add_field(name="Current User", value=fruit["current_user"], inline=True)
        
        if "previous_users" in fruit and fruit["previous_users"]:
            embed.add_field(name="Previous Users", value=", ".join(fruit["previous_users"]), inline=True)
        
        if "abilities" in fruit and fruit["abilities"]:
            abilities = "\n".join([f"• {ability}" for ability in fruit["abilities"][:5]])
            if len(fruit["abilities"]) > 5:
                abilities += f"\n...and {len(fruit['abilities']) - 5} more"
            embed.add_field(name="Abilities", value=abilities, inline=False)
        
        if "strengths" in fruit and fruit["strengths"]:
            strengths = "\n".join([f"• {strength}" for strength in fruit["strengths"][:3]])
            if len(fruit["strengths"]) > 3:
                strengths += f"\n...and {len(fruit['strengths']) - 3} more"
            embed.add_field(name="Strengths", value=strengths, inline=True)
        
        if "weaknesses" in fruit and fruit["weaknesses"]:
            weaknesses = "\n".join([f"• {weakness}" for weakness in fruit["weaknesses"][:3]])
            if len(fruit["weaknesses"]) > 3:
                weaknesses += f"\n...and {len(fruit['weaknesses']) - 3} more"
            embed.add_field(name="Weaknesses", value=weaknesses, inline=True)
        
        if "first_appearance" in fruit:
            embed.add_field(name="First Appearance", value=fruit["first_appearance"], inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="character")
    @commands.guild_only()
    async def character_info(self, ctx, *, name: str):
        """Get information about a One Piece character"""
        # Get all characters
        characters = await self.api_request("characters")
        
        if "error" in characters:
            return await ctx.send("Failed to retrieve character data. Try again later.")
        
        # Find matching characters
        name_lower = name.lower()
        matches = []
        
        for char in characters:
            char_name = char.get("name", "").lower()
            char_id = char.get("_id", "")
            
            if name_lower in char_name:
                matches.append(char_id)
        
        if not matches:
            return await ctx.send(f"No characters found matching '{name}'.")
        
        if len(matches) == 1:
            # Get detailed info for the single match
            char_id = matches[0]
            char = await self.api_request(f"characters/{char_id}")
            
            if "error" in char:
                return await ctx.send(f"Failed to retrieve character with ID '{char_id}'.")
            
            # Create an embed
            embed = discord.Embed(
                title=char.get("name", "Unknown Character"),
                description=char.get("description", "No description available."),
                color=discord.Color.blue()
            )
            
            # Add fields
            if "epithet" in char:
                embed.add_field(name="Epithet", value=char["epithet"], inline=True)
            
            if "bounty" in char:
                embed.add_field(name="Bounty", value=char["bounty"], inline=True)
            
            if "crew" in char:
                embed.add_field(name="Crew", value=char["crew"], inline=True)
            
            if "occupations" in char and char["occupations"]:
                embed.add_field(name="Occupations", value=", ".join(char["occupations"]), inline=True)
            
            if "origin" in char:
                embed.add_field(name="Origin", value=char["origin"], inline=True)
            
            if "devil_fruit" in char:
                embed.add_field(name="Devil Fruit", value=char["devil_fruit"], inline=True)
            
            if "affiliations" in char and char["affiliations"]:
                embed.add_field(name="Affiliations", value=", ".join(char["affiliations"]), inline=True)
            
            if "first_appearance" in char:
                embed.add_field(name="First Appearance", value=char["first_appearance"], inline=True)
            
            await ctx.send(embed=embed)
        else:
            # Show multiple matches
            embed = discord.Embed(
                title="Multiple Characters Found",
                description=f"Found {len(matches)} characters matching '{name}'.",
                color=discord.Color.purple()
            )
            
            for i, char_id in enumerate(matches[:10], 1):
                # Get character details
                char = await self.api_request(f"characters/{char_id}")
                
                if "error" not in char:
                    desc_parts = []
                    
                    if "epithet" in char:
                        desc_parts.append(f"'{char['epithet']}'")
                        
                    if "crew" in char:
                        desc_parts.append(f"Crew: {char['crew']}")
                    
                    desc = " | ".join(desc_parts) if desc_parts else "Use `.character {char['name']}` for details"
                    
                    embed.add_field(
                        name=f"{i}. {char.get('name', 'Unknown')}",
                        value=desc,
                        inline=True
                    )
            
            if len(matches) > 10:
                embed.set_footer(text=f"Showing 10 of {len(matches)} matches. Please refine your search.")
            
            await ctx.send(embed=embed)
