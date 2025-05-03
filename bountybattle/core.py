import discord
import random
import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from redbot.core import commands, Config
from redbot.core.bot import Red

class BountyBattle(commands.Cog):
    """One Piece themed RPG system with bounties, devil fruits, and deathmatches."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.logger = logging.getLogger("red.BountyBattle")
        
        # Initialize Config
        self.config = Config.get_conf(self, identifier=1357924680, force_registration=True)
        
        # Register default guild settings
        default_guild = {
            "bounties": {},
            "event": None,
            "global_bank": 0,
            "last_bank_robbery": None,
            "tournaments": {},
            "beta_active": True,
            "leaderboard_channel": None,
            "announcement_channel": None,
            "active_events": {},
            "disabled_commands": [],
            "is_paused": False,
            "restricted_channel": None,
            "maintenance_mode": False
        }
        
        # Register default member settings
        default_member = {
            "bounty": 0,
            "bank_balance": 0,
            "berries": 0,
            "last_daily_claim": None,
            "wins": 0,
            "losses": 0,
            "damage_dealt": 0,
            "achievements": [],
            "titles": [],
            "current_title": None,
            "devil_fruit": None,
            "last_active": None,
            "bounty_hunted": 0,
            "last_deposit_time": None,
            "win_streak": 0,
            "damage_taken": 0,
            "critical_hits": 0,
            "healing_done": 0,
            "turns_survived": 0,
            "burns_applied": 0,
            "stuns_applied": 0,
            "blocks_performed": 0,
            "damage_prevented": 0,
            "elements_used": [],
            "total_battles": 0,
            "perfect_victories": 0,
            "comebacks": 0,
            "fastest_victory": None,
            "longest_battle": None,
            "devil_fruit_mastery": 0,
            "successful_hunts": 0,
            "failed_hunts": 0
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # File path for external data
        self.bounty_file = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/bounties.json"
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
        
        # Initialize tracking variables
        self.active_channels = set()
        self.battle_stopped = False
        
        # Import necessary constants
        from .constants.devil_fruits import DEVIL_FRUITS
        from .constants.titles import TITLES, HIDDEN_TITLES
        from .constants.achievements import ACHIEVEMENTS
        
        self.DEVIL_FRUITS = DEVIL_FRUITS
        self.TITLES = TITLES
        self.HIDDEN_TITLES = HIDDEN_TITLES
        self.ACHIEVEMENTS = ACHIEVEMENTS
        
        # Initialize boss rotation
        self._initialize_bosses()
        
    def _initialize_bosses(self):
        """Initialize the boss rotation system."""
        now = datetime.utcnow()
        self.current_bosses = {
            "Marine Fortress": {
                "boss": "Vice Admiral Momonga",  # Will be randomized later
                "level": "Easy",
                "next_rotation": now + timedelta(hours=4)
            },
            "Impel Down": {
                "boss": "Magellan",  # Will be randomized later
                "level": "Medium",
                "next_rotation": now + timedelta(hours=6)
            },
            "Enies Lobby": {
                "boss": "Rob Lucci",  # Will be randomized later
                "level": "Hard",
                "next_rotation": now + timedelta(hours=8)
            },
            "Yonko Territory": {
                "boss": "Kaido",  # Will be randomized later
                "level": "Very Hard",
                "next_rotation": now + timedelta(hours=12)
            },
            "Mary Geoise": {
                "boss": "The Five Elders",  # Will be randomized later
                "level": "Extreme",
                "next_rotation": now + timedelta(hours=24)
            }
        }
    
    # --- Data Management Functions ---
    
    def load_bounties(self):
        """Load bounty data safely from file."""
        if not os.path.exists(self.bounty_file):
            return {}  # If file doesn't exist, return empty dict
        
        try:
            with open(self.bounty_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}  # If file is corrupted, return empty dict
    
    def save_bounties(self, data):
        """Save bounty data safely to file."""
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
        with open(self.bounty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    async def sync_user_data(self, user):
        """
        Synchronize bounty data for a user between config and bounties.json.
        
        Returns the synchronized bounty amount.
        """
        try:
            # Load current bounty data
            bounties = self.load_bounties()
            user_id = str(user.id)
            
            # Get bounty from config and bounties.json
            config_bounty = await self.config.member(user).bounty()
            json_bounty = bounties.get(user_id, {}).get("amount", 0)
            
            # Use the higher value as the source of truth
            true_bounty = max(config_bounty, json_bounty)
            
            # Update both systems
            if user_id not in bounties:
                bounties[user_id] = {"amount": true_bounty, "fruit": None}
            else:
                bounties[user_id]["amount"] = true_bounty
                
            # Save back to file
            self.save_bounties(bounties)
            
            # Update config
            await self.config.member(user).bounty.set(true_bounty)
            
            return true_bounty
        except Exception as e:
            self.logger.error(f"Error in sync_user_data: {e}")
            return None
    
    async def safe_modify_bounty(self, user, amount, operation="add"):
        """Thread-safe method to modify a user's bounty."""
        try:
            bounties = self.load_bounties()
            user_id = str(user.id)
            
            if user_id not in bounties:
                bounties[user_id] = {"amount": 0, "fruit": None}
            
            if operation == "add":
                bounties[user_id]["amount"] += amount
            elif operation == "subtract":
                bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - amount)
            elif operation == "set":
                bounties[user_id]["amount"] = amount
            
            self.save_bounties(bounties)
            await self.config.member(user).bounty.set(bounties[user_id]["amount"])
            return bounties[user_id]["amount"]
        except Exception as e:
            self.logger.error(f"Error modifying bounty: {e}")
            return None
    
    def get_bounty_title(self, bounty_amount):
        """Get the bounty title based on the bounty amount."""
        if bounty_amount is None or bounty_amount <= 0:
            return "Unknown Pirate"
            
        # Get all titles the user qualifies for
        titles_qualified = []
        
        for title, requirements in self.TITLES.items():
            required_bounty = requirements["bounty"]
            if bounty_amount >= required_bounty:
                titles_qualified.append((title, required_bounty))
        
        # If no titles are qualified
        if not titles_qualified:
            return "Unknown Pirate"
            
        # Sort by required bounty (descending) and return the highest one
        titles_qualified.sort(key=lambda x: x[1], reverse=True)
        return titles_qualified[0][0]
    
    # --- Bounty Commands ---
    
    @commands.command()
    async def startbounty(self, ctx):
        """Start your bounty journey."""
        user = ctx.author
        
        # Use data manager to sync bounties
        true_bounty = await self.sync_user_data(user)
        
        # If they have any existing data
        if true_bounty is not None and true_bounty > 0:
            return await ctx.send(f"Ye already have a bounty of `{true_bounty:,}` Berries, ye scallywag!")
            
        # For both new players and those with 0 bounty
        try:
            initial_bounty = random.randint(50, 100)
            
            # Update bounty
            new_bounty = await self.safe_modify_bounty(user, initial_bounty, "set")
            if new_bounty is None:
                return await ctx.send("❌ Failed to set your bounty. Please try again.")
            
            # Initialize stats only if they don't exist
            if not await self.config.member(user).wins():
                await self.config.member(user).wins.set(0)
            if not await self.config.member(user).losses():
                await self.config.member(user).losses.set(0)
            
            # Always update last active time
            await self.config.member(user).last_active.set(datetime.utcnow().isoformat())
            
            # Create appropriate embed
            bounties = self.load_bounties()
            if str(user.id) in bounties and bounties[str(user.id)].get("fruit"):
                embed = discord.Embed(
                    title="🏴‍☠️ Bounty Renewed!",
                    description=f"**{user.display_name}**'s bounty has been renewed!",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title="🏴‍☠️ Welcome to the Grand Line!",
                    description=f"**{user.display_name}** has started their pirate journey!",
                    color=discord.Color.blue()
                )
            
            embed.add_field(
                name="Initial Bounty",
                value=f"`{initial_bounty:,}` Berries",
                inline=False
            )
            
            # Check for beta tester title
            beta_active = await self.config.guild(ctx.guild).beta_active()
            if beta_active:
                unlocked_titles = await self.config.member(user).titles()
                if "BETA TESTER" not in unlocked_titles:
                    unlocked_titles.append("BETA TESTER")
                    await self.config.member(user).titles.set(unlocked_titles)
                    embed.add_field(
                        name="🎖️ Special Title Unlocked",
                        value="`BETA TESTER`",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in startbounty: {str(e)}")
            await ctx.send("⚠️ An error occurred while starting your bounty journey. Please try again.")
    
    @commands.command()
    async def mybounty(self, ctx):
        """Check your bounty amount."""
        user = ctx.author
        
        # Sync data first
        true_bounty = await self.sync_user_data(user)
        if true_bounty is None:
            return await ctx.send("❌ An error occurred while checking your bounty.")
            
        # Get current title based on synced bounty
        current_title = self.get_bounty_title(true_bounty)
        
        embed = discord.Embed(
            title="🏴‍☠️ Bounty Status",
            description=f"**{user.display_name}**'s current bounty:",
            color=discord.Color.gold()
        )
        embed.add_field(name="<:Beli:1237118142774247425> Bounty", value=f"`{true_bounty:,}` Berries", inline=False)
        embed.add_field(name="🎭 Title", value=f"`{current_title}`", inline=False)
        
        await ctx.send(embed=embed)
        
    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user)
    async def dailybounty(self, ctx):
        """Claim your daily bounty increase."""
        user = ctx.author
        
        # Sync bounty data first
        current_bounty = await self.config.member(user).bounty()
        
        # Check last claim time
        last_claim = await self.config.member(user).last_daily_claim()
        now = datetime.utcnow()

        if last_claim:
            last_claim = datetime.fromisoformat(last_claim)
            time_left = timedelta(days=1) - (now - last_claim)
            
            if time_left.total_seconds() > 0:
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return await ctx.send(f"Ye can't claim yer daily bounty yet! Try again in {hours} hours and {minutes} minutes! ⏳")

        # Prompt for treasure chest
        await ctx.send(f"Ahoy, {user.display_name}! Ye found a treasure chest! Do ye want to open it? (yes/no)")
        try:
            def check(m):
                return m.author == user and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]
            msg = await self.bot.wait_for("message", check=check, timeout=30)
        except asyncio.TimeoutError:
            await self.config.member(user).last_daily_claim.set(None)
            return await ctx.send("Ye let the treasure slip through yer fingers! Try again tomorrow, ye landlubber!")

        if msg.content.lower() == "yes":
            increase = random.randint(1000, 5000)
            
            # Update bounty
            new_bounty = await self.safe_modify_bounty(user, increase, "add")
            if new_bounty is None:
                return await ctx.send("❌ Failed to update your bounty. Please try again.")
            
            # Update last claim time
            await self.config.member(user).last_daily_claim.set(now.isoformat())
            
            # Get new title
            new_title = self.get_bounty_title(new_bounty)
            
            await ctx.send(f"<:Beli:1237118142774247425> Ye claimed {increase:,} Berries! Yer new bounty is {new_bounty:,} Berries!\n"
                        f"Current Title: {new_title}")

            # Announce if the user reaches a significant rank
            if new_bounty >= 900000000:
                await self.announce_rank(ctx.guild, user, new_title)
        else:
            await self.config.member(user).last_daily_claim.set(None)
            await ctx.send("Ye decided not to open the chest. The Sea Kings must've scared ye off!")
    
    @commands.command()
    async def mostwanted(self, ctx):
        """Display the top users with the highest bounties."""
        # Load current bounty data from bounties.json
        bounties = self.load_bounties()
        
        if not bounties:
            return await ctx.send("🏴‍☠️ No bounties have been claimed yet! Be the first to start your journey with `.startbounty`.")

        # Filter out inactive or invalid entries and sort by amount
        valid_bounties = []
        for user_id, data in bounties.items():
            try:
                member = ctx.guild.get_member(int(user_id))
                if member and data.get("amount", 0) > 0:
                    valid_bounties.append((user_id, data))
            except (ValueError, AttributeError):
                continue

        if not valid_bounties:
            return await ctx.send("🏴‍☠️ No active bounties found! Start your journey with `.startbounty`.")

        sorted_bounties = sorted(valid_bounties, key=lambda x: x[1]["amount"], reverse=True)
        pages = [sorted_bounties[i:i + 10] for i in range(0, len(sorted_bounties), 10)]
        
        current_page = 0
        
        async def create_leaderboard_embed(page_data, page_num):
            embed = discord.Embed(
                title="🏆 Most Wanted Pirates 🏆",
                description="The most notorious pirates of the sea!",
                color=discord.Color.gold()
            )
            
            total_pages = len(pages)
            embed.set_footer(text=f"Page {page_num + 1}/{total_pages} | Total Pirates: {len(sorted_bounties)}")
            
            for i, (user_id, data) in enumerate(page_data, start=1 + (page_num * 10)):
                member = ctx.guild.get_member(int(user_id))
                if not member:
                    continue
                
                # Get user's devil fruit if they have one
                devil_fruit = data.get("fruit", "None")
                fruit_display = f" • <:MeraMera:1336888578705330318> {devil_fruit}" if devil_fruit and devil_fruit != "None" else ""
                
                # Create rank emoji based on position
                rank_emoji = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                # Format the bounty amount with commas
                bounty_amount = "{:,}".format(data["amount"])
                
                embed.add_field(
                    name=f"{rank_emoji} {member.display_name}",
                    value=f"<:Beli:1237118142774247425> `{bounty_amount} Berries`{fruit_display}",
                    inline=False
                )
            
            return embed

        # Send initial embed
        embed = await create_leaderboard_embed(pages[current_page], current_page)
        message = await ctx.send(embed=embed)

        # Add reactions for navigation
        if len(pages) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return (
                    user == ctx.author 
                    and str(reaction.emoji) in ["⬅️", "➡️"] 
                    and reaction.message.id == message.id
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        timeout=60.0,
                        check=check
                    )

                    if str(reaction.emoji) == "➡️":
                        current_page = (current_page + 1) % len(pages)
                    elif str(reaction.emoji) == "⬅️":
                        current_page = (current_page - 1) % len(pages)

                    embed = await create_leaderboard_embed(pages[current_page], current_page)
                    await message.edit(embed=embed)
                    await message.remove_reaction(reaction, user)
                    
                except asyncio.TimeoutError:
                    break

            await message.clear_reactions()
            
    # --- Devil Fruit Commands ---
    
    @commands.command()
    async def eatfruit(self, ctx):
        """Consume a random Devil Fruit!"""
        user = ctx.author
        bounties = self.load_bounties()
        user_id = str(user.id)

        if user_id not in bounties:
            return await ctx.send("Ye need to start yer bounty journey first by typing `.startbounty`!")

        if bounties[user_id].get("fruit"):
            return await ctx.send(f"❌ You already have the `{bounties[user_id]['fruit']}`! You can only eat one Devil Fruit!")

        # Get all currently taken rare fruits
        taken_rare_fruits = {
            data.get("fruit") for data in bounties.values() 
            if data.get("fruit") in self.DEVIL_FRUITS["Rare"]
        }

        # Get available rare and common fruits
        available_rare_fruits = [
            fruit for fruit in self.DEVIL_FRUITS["Rare"].keys() 
            if fruit not in taken_rare_fruits
        ]

        available_common_fruits = list(self.DEVIL_FRUITS["Common"].keys())

        if not available_rare_fruits and not available_common_fruits:
            return await ctx.send("❌ There are no Devil Fruits available right now! Try again later.")

        # 10% chance for rare fruit if available
        if available_rare_fruits and random.random() < 0.10:
            new_fruit = random.choice(available_rare_fruits)
            fruit_data = self.DEVIL_FRUITS["Rare"][new_fruit]
            is_rare = True
        else:
            new_fruit = random.choice(available_common_fruits)
            fruit_data = self.DEVIL_FRUITS["Common"][new_fruit]
            is_rare = False

        # Save the fruit to the user
        bounties[user_id]["fruit"] = new_fruit
        self.save_bounties(bounties)
        await self.config.member(user).devil_fruit.set(new_fruit)
        await self.config.member(user).last_active.set(datetime.utcnow().isoformat())

        # Create announcement
        if is_rare:
            announcement = (
                f"🚨 **Breaking News from the Grand Line!** 🚨\n"
                f"🏴‍☠️ **{user.display_name}** has discovered and consumed the **{new_fruit}**!\n"
                f"Type: {fruit_data['type']}\n"
                f"🔥 Power: {fruit_data['bonus']}\n\n"
                f"⚠️ *This Devil Fruit is now **UNIQUE**! No one else can eat it!*"
            )
            await ctx.send(announcement)
        else:
            await ctx.send(
                f"<:MeraMera:1336888578705330318> **{user.display_name}** has eaten the **{new_fruit}**!\n"
                f"Type: {fruit_data['type']}\n"
                f"🔥 Power: {fruit_data['bonus']}\n\n"
                f"⚠️ *You cannot eat another Devil Fruit!*"
            )
    
    @commands.command()
    async def myfruit(self, ctx):
        """Check which Devil Fruit you have eaten."""
        user = ctx.author
        bounties = self.load_bounties()
        user_id = str(user.id)
        
        if user_id not in bounties or not bounties[user_id].get("fruit"):
            return await ctx.send("❌ You have not eaten a Devil Fruit!")
    
        fruit = bounties[user_id]["fruit"]
        
        # Search for the fruit in both Common and Rare categories
        fruit_data = self.DEVIL_FRUITS["Common"].get(fruit) or self.DEVIL_FRUITS["Rare"].get(fruit)
    
        if not fruit_data:
            return await ctx.send("⚠️ **Error:** Your Devil Fruit could not be found in the database. Please report this!")
    
        fruit_type = fruit_data["type"]
        effect = fruit_data["bonus"]
    
        await ctx.send(
            f"<:MeraMera:1336888578705330318> **{user.display_name}** has the **{fruit}**! ({fruit_type} Type)\n"
            f"🔥 **Ability:** {effect}"
        )
    
    # --- Admin Commands ---
    
    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def setbounty(self, ctx, member: discord.Member, amount: int):
        """Set a user's bounty (Admin/Owner only)."""
        if amount < 0:
            return await ctx.send("❌ Bounty cannot be negative.")
        
        # Add permission check message
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.administrator:
            return await ctx.send("❌ You need administrator permissions to use this command!")
        
        try:
            # Set the bounty
            new_bounty = await self.safe_modify_bounty(member, amount, "set")
            if new_bounty is None:
                return await ctx.send("⚠️ Failed to set bounty. Please try again.")

            # Create embed for response
            embed = discord.Embed(
                title="🏴‍☠️ Bounty Updated",
                description=f"**{member.display_name}**'s bounty has been set to `{amount:,}` Berries!",
                color=discord.Color.green()
            )

            # Add current title if applicable
            new_title = self.get_bounty_title(amount)
            if new_title:
                embed.add_field(
                    name="Current Title",
                    value=f"`{new_title}`",
                    inline=False
                )

            await ctx.send(embed=embed)

            # Check if the new bounty warrants an announcement
            if amount >= 900_000_000:
                await self.announce_rank(ctx.guild, member, new_title)

        except Exception as e:
            self.logger.error(f"Error in setbounty command: {str(e)}")
            await ctx.send(f"❌ An error occurred while setting the bounty: {str(e)}")
            
    async def announce_rank(self, guild, user, title):
        """Announce when a user reaches a significant rank."""
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎉 Congratulations to {user.mention} for reaching the rank of **{title}** with a bounty of {user.display_name}'s bounty!")
