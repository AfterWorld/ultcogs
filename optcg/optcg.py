import asyncio
import json
import random
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

import aiohttp
import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, humanize_list
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

log = logging.getLogger("red.optcg")

# Default rarity weights
RARITY_WEIGHTS = {
    "Leader": 0.5,      # 0.5%
    "Secret Rare": 2,   # 2%
    "Super Rare": 7.5,  # 7.5%
    "Rare": 20,         # 20%
    "Uncommon": 30,     # 30%
    "Common": 40        # 40%
}

# Rarity emojis
RARITY_EMOJIS = {
    "Leader": "👑",
    "Secret Rare": "✨",
    "Super Rare": "🌟",
    "Rare": "💎",
    "Uncommon": "🔷",
    "Common": "⚪"
}

# Card spawn cooldown defaults (in minutes)
DEFAULT_MIN_COOLDOWN = 30
DEFAULT_MAX_COOLDOWN = 90

class OPTCG(commands.Cog):
    """
    One Piece Trading Card Game collection system
    
    Spawn, claim, and collect One Piece TCG cards in your server.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=82726151897, force_registration=True
        )
        
        # Path to store cached card data
        self.data_path = cog_data_path(self) / "card_cache.json"
        
        # API endpoint
        self.api_url = "https://api.optcgapi.com/cards"
        
        # Default settings
        default_global = {
            "last_api_call": 0,
            "card_cache_timestamp": 0
        }
        
        default_guild = {
            "enabled": False,
            "spawn_channel": None,
            "min_cooldown": DEFAULT_MIN_COOLDOWN,
            "max_cooldown": DEFAULT_MAX_COOLDOWN,
            "custom_weights": {},
            "use_default_weights": True,
            "active_card": None,
            "next_spawn_time": 0
        }
        
        default_member = {
            "cards": [],
            "stats": {
                "Leader": 0,
                "Secret Rare": 0,
                "Super Rare": 0,
                "Rare": 0,
                "Uncommon": 0,
                "Common": 0
            }
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
        
        # Cache for cards
        self.cards_cache = {}
        
        # Active spawn tasks
        self.spawn_tasks = {}
        
        # Session for API requests
        self.session = None
        
        # Lock for API calls to respect rate limits
        self.api_lock = asyncio.Lock()
    
    async def cog_load(self):
        """Initialize the cog when loaded"""
        self.session = aiohttp.ClientSession()
        await self._load_card_cache()
        self._start_spawn_tasks()
    
    async def cog_unload(self):
        """Clean up when the cog is unloaded"""
        if self.session:
            await self.session.close()
        
        # Cancel all spawn tasks
        for task in self.spawn_tasks.values():
            if not task.done():
                task.cancel()
    
    async def red_delete_data_for_user(self, *, requester, user_id):
        """Delete user data"""
        # Delete all member data for this user across all guilds
        all_guilds = await self.config.all_guilds()
        for guild_id in all_guilds:
            await self.config.member_from_ids(guild_id, user_id).clear()
    
    async def _load_card_cache(self):
        """Load card data from cache file or API"""
        try:
            if os.path.exists(self.data_path):
                async with self.config.card_cache_timestamp() as timestamp:
                    # If cache is older than 24 hours, refresh it
                    if time.time() - timestamp > 86400:  # 24 hours
                        await self._fetch_and_cache_cards()
                    else:
                        # Load from cache file
                        with open(self.data_path, "r", encoding="utf-8") as f:
                            self.cards_cache = json.load(f)
                        log.info(f"Loaded {len(self.cards_cache)} cards from cache")
            else:
                # No cache exists, fetch from API
                await self._fetch_and_cache_cards()
        except Exception as e:
            log.error(f"Error loading card cache: {e}")
            self.cards_cache = {}
    
    async def _fetch_and_cache_cards(self):
        """Fetch cards from the API and cache them"""
        async with self.api_lock:
            # Respect rate limits (minimum 5 seconds between API calls)
            last_call = await self.config.last_api_call()
            if time.time() - last_call < 5:
                await asyncio.sleep(5 - (time.time() - last_call))
            
            try:
                log.info("Fetching cards from OPTCG API...")
                # First check if we can get all cards
                async with self.session.get(self.api_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Process and cache the cards
                        self.cards_cache = {str(card["card_id"]): card for card in data}
                        
                        # Save to file
                        with open(self.data_path, "w", encoding="utf-8") as f:
                            json.dump(self.cards_cache, f, indent=4)
                        
                        # Update timestamps
                        await self.config.last_api_call.set(time.time())
                        await self.config.card_cache_timestamp.set(time.time())
                        
                        log.info(f"Fetched and cached {len(self.cards_cache)} cards from API")
                    else:
                        # If we can't get all cards, try with a more specific endpoint
                        log.warning(f"API returned status code {resp.status}, trying alternative endpoints")
                        
                        # Try alternative API endpoints that might help if the main one fails
                        alt_endpoints = [
                            "https://api.optcgapi.com/v1/cards",
                            "https://api.optcgapi.com/cards/search"
                        ]
                        
                        for endpoint in alt_endpoints:
                            log.info(f"Trying alternative endpoint: {endpoint}")
                            async with self.session.get(endpoint) as alt_resp:
                                if alt_resp.status == 200:
                                    data = await alt_resp.json()
                                    
                                    # Process and cache the cards
                                    self.cards_cache = {str(card["card_id"]): card for card in data}
                                    
                                    # Save to file
                                    with open(self.data_path, "w", encoding="utf-8") as f:
                                        json.dump(self.cards_cache, f, indent=4)
                                    
                                    # Update timestamps
                                    await self.config.last_api_call.set(time.time())
                                    await self.config.card_cache_timestamp.set(time.time())
                                    
                                    log.info(f"Fetched and cached {len(self.cards_cache)} cards from API")
                                    break
                        else:
                            log.error("All API endpoints failed, using sample data as fallback")
                            # Use a sample set of cards as fallback
                            self._load_sample_cards()
            except Exception as e:
                log.error(f"Error fetching cards from API: {e}")
                # Use a sample set of cards as fallback
                self._load_sample_cards()
                
    def _load_sample_cards(self):
        """Load a sample set of cards as fallback"""
        log.warning("Loading sample card data as fallback")
        
        # Sample One Piece TCG cards as fallback
        sample_cards = [
            {
                "card_id": "OP01-001",
                "name": "Monkey D. Luffy",
                "rarity": "Leader",
                "card_type": "Leader",
                "power": "5000",
                "effect": "When this card attacks, draw 1 card.",
                "image": "https://i.imgur.com/sample1.png"
            },
            {
                "card_id": "OP01-002",
                "name": "Roronoa Zoro",
                "rarity": "Super Rare",
                "card_type": "Character",
                "power": "8000",
                "effect": "When this card is played, you may rest 1 of your opponent's characters.",
                "image": "https://i.imgur.com/sample2.png"
            },
            {
                "card_id": "OP01-003",
                "name": "Nami",
                "rarity": "Rare",
                "card_type": "Character",
                "power": "6000",
                "effect": "When this card is played, draw 1 card.",
                "image": "https://i.imgur.com/sample3.png"
            },
            {
                "card_id": "OP01-004",
                "name": "Usopp",
                "rarity": "Uncommon",
                "card_type": "Character",
                "power": "5000",
                "effect": "When this card is played, you may rest 1 of your opponent's characters with 5000 power or less.",
                "image": "https://i.imgur.com/sample4.png"
            },
            {
                "card_id": "OP01-005",
                "name": "Sanji",
                "rarity": "Rare",
                "card_type": "Character",
                "power": "7000",
                "effect": "When this card attacks, it gets +2000 power until end of turn.",
                "image": "https://i.imgur.com/sample5.png"
            },
            {
                "card_id": "OP01-006",
                "name": "Tony Tony Chopper",
                "rarity": "Common",
                "card_type": "Character",
                "power": "4000",
                "effect": "When this card is played, heal 1 damage from your Leader.",
                "image": "https://i.imgur.com/sample6.png"
            },
            {
                "card_id": "OP01-007",
                "name": "Nico Robin",
                "rarity": "Rare",
                "card_type": "Character",
                "power": "6000",
                "effect": "When this card is played, look at the top 3 cards of your deck. Add 1 to your hand and put the rest at the bottom of your deck in any order.",
                "image": "https://i.imgur.com/sample7.png"
            },
            {
                "card_id": "OP01-008",
                "name": "Franky",
                "rarity": "Uncommon",
                "card_type": "Character",
                "power": "7000",
                "effect": "When this card is played, you may trash 1 card from your hand. If you do, draw 1 card.",
                "image": "https://i.imgur.com/sample8.png"
            },
            {
                "card_id": "OP01-009",
                "name": "Brook",
                "rarity": "Uncommon",
                "card_type": "Character",
                "power": "5000",
                "effect": "When this card is played, you may put 1 card from your trash on the bottom of your deck.",
                "image": "https://i.imgur.com/sample9.png"
            },
            {
                "card_id": "OP01-010",
                "name": "Jinbe",
                "rarity": "Super Rare",
                "card_type": "Character",
                "power": "8000",
                "effect": "When this card attacks, it gets +1000 power for each other character you control until end of turn.",
                "image": "https://i.imgur.com/sample10.png"
            },
            {
                "card_id": "OP01-011",
                "name": "Monkey D. Luffy, Gear 4",
                "rarity": "Secret Rare",
                "card_type": "Character",
                "power": "10000",
                "effect": "When this card is played, you may KO 1 of your opponent's characters with 8000 power or less.",
                "image": "https://i.imgur.com/sample11.png"
            },
            {
                "card_id": "OP01-012",
                "name": "Going Merry",
                "rarity": "Rare",
                "card_type": "Event",
                "effect": "Draw 2 cards, then discard 1 card.",
                "image": "https://i.imgur.com/sample12.png"
            },
            {
                "card_id": "OP01-013",
                "name": "Straw Hat Crew",
                "rarity": "Super Rare",
                "card_type": "Event",
                "effect": "All of your characters get +2000 power until end of turn.",
                "image": "https://i.imgur.com/sample13.png"
            },
            {
                "card_id": "OP01-014",
                "name": "Thousand Sunny",
                "rarity": "Common",
                "card_type": "Event",
                "effect": "Draw 1 card.",
                "image": "https://i.imgur.com/sample14.png"
            },
            {
                "card_id": "OP01-015",
                "name": "Gum-Gum Pistol",
                "rarity": "Common",
                "card_type": "Event",
                "effect": "Your Leader gets +3000 power until end of turn.",
                "image": "https://i.imgur.com/sample15.png"
            }
        ]
        
        # Cache the sample cards
        self.cards_cache = {card["card_id"]: card for card in sample_cards}
        
        # Save to file
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.cards_cache, f, indent=4)
        
        log.info(f"Loaded {len(self.cards_cache)} sample cards as fallback")
    
    def _start_spawn_tasks(self):
        """Start card spawn tasks for all enabled guilds"""
        asyncio.create_task(self._initialize_spawn_tasks())
    
    async def _initialize_spawn_tasks(self):
        """Initialize spawn tasks for all enabled guilds"""
        all_guilds = await self.config.all_guilds()
        for guild_id, guild_data in all_guilds.items():
            if guild_data["enabled"] and guild_data["spawn_channel"]:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    self._create_spawn_task(guild)
    
    def _create_spawn_task(self, guild: discord.Guild):
        """Create a spawn task for a guild"""
        if guild.id in self.spawn_tasks and not self.spawn_tasks[guild.id].done():
            self.spawn_tasks[guild.id].cancel()
        
        self.spawn_tasks[guild.id] = asyncio.create_task(self._card_spawn_loop(guild))
        log.info(f"Created spawn task for guild {guild.id}")
    
    async def _card_spawn_loop(self, guild: discord.Guild):
        """Main loop for spawning cards"""
        try:
            while True:
                # Check if spawning is enabled
                guild_data = await self.config.guild(guild).all()
                if not guild_data["enabled"] or not guild_data["spawn_channel"]:
                    # Spawning disabled, check again in 5 minutes
                    await asyncio.sleep(300)
                    continue
                
                # Get the spawn channel
                channel_id = guild_data["spawn_channel"]
                channel = guild.get_channel(channel_id)
                if not channel:
                    log.error(f"Spawn channel {channel_id} not found in guild {guild.id}")
                    await asyncio.sleep(300)
                    continue
                
                # Check if there's an active card
                if guild_data["active_card"]:
                    # There's already an active card, wait until next check
                    await asyncio.sleep(60)
                    continue
                
                # Check if it's time to spawn a new card
                now = time.time()
                next_spawn = guild_data["next_spawn_time"]
                
                if now >= next_spawn:
                    # Time to spawn a new card
                    await self._spawn_card(guild, channel)
                    
                    # Wait a minute before checking again
                    await asyncio.sleep(60)
                else:
                    # Not time yet, sleep until next spawn or for 60 seconds, whichever is shorter
                    sleep_time = min(next_spawn - now, 60)
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            log.info(f"Spawn task cancelled for guild {guild.id}")
        except Exception as e:
            log.error(f"Error in spawn loop for guild {guild.id}: {e}")
            # Restart the task after a delay
            await asyncio.sleep(60)
            self._create_spawn_task(guild)
    
    async def _spawn_card(self, guild: discord.Guild, channel: discord.TextChannel):
        """Spawn a card in the specified channel"""
        if len(self.cards_cache) == 0:
            log.error("No cards available in cache")
            return
        
        # Select a random card based on rarity weights
        card = await self._select_random_card(guild)
        if not card:
            log.error("Failed to select a random card")
            return
        
        # Create the spawn message with buttons
        embed = await self._create_mystery_embed(card)
        view = CardClaimView(self, guild.id, card)
        
        try:
            message = await channel.send(embed=embed, view=view)
            
            # Store the active card
            active_card_data = {
                "card_id": card["card_id"],
                "message_id": message.id,
                "timestamp": time.time()
            }
            await self.config.guild(guild).active_card.set(active_card_data)
            
            # Set the next spawn time
            guild_data = await self.config.guild(guild).all()
            min_cooldown = guild_data["min_cooldown"] * 60  # Convert to seconds
            max_cooldown = guild_data["max_cooldown"] * 60  # Convert to seconds
            next_spawn = time.time() + random.randint(min_cooldown, max_cooldown)
            await self.config.guild(guild).next_spawn_time.set(next_spawn)
            
            log.info(f"Spawned card {card['card_id']} in guild {guild.id}")
        except Exception as e:
            log.error(f"Error spawning card in guild {guild.id}: {e}")
    
    async def _select_random_card(self, guild: discord.Guild) -> Dict:
        """Select a random card based on rarity weights"""
        guild_data = await self.config.guild(guild).all()
        
        # Determine which weights to use
        if guild_data["use_default_weights"]:
            weights = RARITY_WEIGHTS
        else:
            weights = guild_data["custom_weights"]
            if not weights:
                weights = RARITY_WEIGHTS
        
        # Group cards by rarity
        cards_by_rarity = {}
        for card_id, card in self.cards_cache.items():
            rarity = card.get("rarity", "Common")
            if rarity not in cards_by_rarity:
                cards_by_rarity[rarity] = []
            cards_by_rarity[rarity].append(card)
        
        # Calculate total weight
        total_weight = sum(weights.get(rarity, 1) for rarity in cards_by_rarity.keys())
        
        # Select a rarity based on weights
        rand_val = random.uniform(0, total_weight)
        cumulative_weight = 0
        selected_rarity = None
        
        for rarity, weight in weights.items():
            if rarity in cards_by_rarity:
                cumulative_weight += weight
                if rand_val <= cumulative_weight:
                    selected_rarity = rarity
                    break
        
        # If no rarity was selected, pick one that has cards
        if not selected_rarity:
            rarities_with_cards = [r for r in cards_by_rarity.keys()]
            if rarities_with_cards:
                selected_rarity = random.choice(rarities_with_cards)
            else:
                # Fallback - just pick any card
                return random.choice(list(self.cards_cache.values()))
        
        # Return a random card of the selected rarity
        return random.choice(cards_by_rarity[selected_rarity])
    
    async def _create_mystery_embed(self, card: Dict) -> discord.Embed:
        """Create an embed for a mystery card (silhouette)"""
        embed = discord.Embed(
            title="A Wild Card Appears!",
            description="Quick! Claim this card before someone else does!",
            color=discord.Color.dark_blue()
        )
        
        # Use a black card image instead of the actual card
        embed.set_image(url="https://i.imgur.com/JLFGGyr.png")
        embed.set_footer(text="Click the button below to claim this card!")
        
        return embed
    
    async def _create_card_embed(self, card: Dict, claimer: Optional[discord.Member] = None) -> discord.Embed:
        """Create an embed for a revealed card"""
        rarity = card.get("rarity", "Common")
        rarity_emoji = RARITY_EMOJIS.get(rarity, "⚪")
        
        embed = discord.Embed(
            title=f"{rarity_emoji} {card.get('name', 'Unknown Card')}",
            description=f"**Card ID**: {card.get('card_id', 'Unknown')}\n**Rarity**: {rarity}",
            color=discord.Color.gold()
        )
        
        # Add card image
        image_url = card.get("image", None)
        if image_url:
            embed.set_image(url=image_url)
        
        # Add card details
        card_type = card.get("card_type", "Unknown")
        power = card.get("power", "N/A")
        
        embed.add_field(name="Type", value=card_type, inline=True)
        
        if card_type != "Event" and power != "N/A":
            embed.add_field(name="Power", value=power, inline=True)
        
        if "effect" in card and card["effect"]:
            embed.add_field(name="Effect", value=card["effect"], inline=False)
        
        # Add claimer information if provided
        if claimer:
            embed.set_footer(text=f"Claimed by {claimer.display_name}", 
                            icon_url=claimer.display_avatar.url)
        
        return embed
    
    async def claim_card(self, guild_id: int, user_id: int, card: Dict) -> bool:
        """Claim a card for a user"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return False
        
        # Clear the active card
        await self.config.guild(guild).active_card.clear()
        
        # Add the card to the user's collection
        async with self.config.member_from_ids(guild_id, user_id).cards() as cards:
            cards.append({
                "card_id": card["card_id"],
                "claimed_at": datetime.now().isoformat()
            })
        
        # Update user stats
        rarity = card.get("rarity", "Common")
        async with self.config.member_from_ids(guild_id, user_id).stats() as stats:
            if rarity in stats:
                stats[rarity] += 1
            else:
                stats[rarity] = 1
        
        return True

    @commands.group(name="optcg", aliases=["tcg"])
    async def optcg(self, ctx: commands.Context):
        """One Piece TCG collection commands"""
        pass
    
    @optcg.command(name="setup")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_setup(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set up the OPTCG card system in your server
        
        Specify a channel where cards will spawn, or leave blank to use the current channel
        """
        if channel is None:
            channel = ctx.channel
        
        # Check if the bot has permissions in the channel
        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.attach_files):
            return await ctx.send(f"I need permissions to send messages, embed links, and attach files in {channel.mention}.")
        
        # Enable the system and set the channel
        await self.config.guild(ctx.guild).enabled.set(True)
        await self.config.guild(ctx.guild).spawn_channel.set(channel.id)
        
        # Set initial next spawn time
        guild_data = await self.config.guild(ctx.guild).all()
        min_cooldown = guild_data["min_cooldown"] * 60  # Convert to seconds
        max_cooldown = guild_data["max_cooldown"] * 60  # Convert to seconds
        next_spawn = time.time() + random.randint(min_cooldown, max_cooldown)
        await self.config.guild(ctx.guild).next_spawn_time.set(next_spawn)
        
        # Create the spawn task if it doesn't exist
        if ctx.guild.id not in self.spawn_tasks or self.spawn_tasks[ctx.guild.id].done():
            self._create_spawn_task(ctx.guild)
        
        # Calculate when the next card will spawn
        next_time = datetime.fromtimestamp(next_spawn)
        time_until = next_time - datetime.now()
        hours, remainder = divmod(time_until.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours} hours, "
        time_str += f"{minutes} minutes"
        
        await ctx.send(
            f"OPTCG card system has been set up in {channel.mention}!\n"
            f"Cards will spawn randomly. Next card will appear in approximately {time_str}."
        )
    
    @optcg.command(name="disable")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_disable(self, ctx: commands.Context):
        """Disable the OPTCG card system in your server"""
        await self.config.guild(ctx.guild).enabled.set(False)
        
        # Cancel the spawn task if it exists
        if ctx.guild.id in self.spawn_tasks and not self.spawn_tasks[ctx.guild.id].done():
            self.spawn_tasks[ctx.guild.id].cancel()
            del self.spawn_tasks[ctx.guild.id]
        
        await ctx.send("OPTCG card system has been disabled in this server.")
    
    @optcg.command(name="cooldown")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_cooldown(self, ctx: commands.Context, min_cooldown: int, max_cooldown: int):
        """Set the cooldown range between card spawns (in minutes)
        
        This sets the minimum and maximum time between card spawns.
        
        Example: 
        - `[p]optcg cooldown 30 90` - Cards will spawn between 30 and 90 minutes apart
        """
        if min_cooldown < 5:
            return await ctx.send("Minimum cooldown must be at least 5 minutes.")
        
        if max_cooldown < min_cooldown:
            return await ctx.send("Maximum cooldown must be greater than or equal to minimum cooldown.")
        
        await self.config.guild(ctx.guild).min_cooldown.set(min_cooldown)
        await self.config.guild(ctx.guild).max_cooldown.set(max_cooldown)
        
        await ctx.send(f"Card spawn cooldown has been set to {min_cooldown}-{max_cooldown} minutes.")
    
    @optcg.command(name="weights")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_weights(self, ctx: commands.Context):
        """View current rarity spawn weights"""
        guild_data = await self.config.guild(ctx.guild).all()
        
        # Determine which weights to use
        if guild_data["use_default_weights"]:
            weights = RARITY_WEIGHTS
            weights_type = "Default"
        else:
            weights = guild_data["custom_weights"]
            if not weights:
                weights = RARITY_WEIGHTS
            weights_type = "Custom"
        
        # Create the embed
        embed = discord.Embed(
            title="Card Rarity Spawn Weights",
            description=f"**{weights_type} weights currently in use**",
            color=discord.Color.blue()
        )
        
        # Calculate total weight for percentage
        total_weight = sum(weights.values())
        
        # Add each rarity and its weight
        for rarity, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            emoji = RARITY_EMOJIS.get(rarity, "⚪")
            percentage = (weight / total_weight) * 100
            embed.add_field(
                name=f"{emoji} {rarity}",
                value=f"{weight} ({percentage:.1f}%)",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="setweights")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_setweights(self, ctx: commands.Context, rarity: str, weight: float):
        """Set custom spawn weight for a specific rarity
        
        Available rarities: Leader, Secret Rare, Super Rare, Rare, Uncommon, Common
        
        Example:
        - `[p]optcg setweights "Secret Rare" 5` - Set Secret Rare cards to have a 5% weight
        """
        valid_rarities = list(RARITY_WEIGHTS.keys())
        
        if rarity not in valid_rarities:
            return await ctx.send(
                f"Invalid rarity. Valid options are: {humanize_list(valid_rarities)}"
            )
        
        if weight < 0:
            return await ctx.send("Weight cannot be negative.")
        
        # Enable custom weights
        await self.config.guild(ctx.guild).use_default_weights.set(False)
        
        # Set the custom weight
        async with self.config.guild(ctx.guild).custom_weights() as weights:
            weights[rarity] = weight
        
        await ctx.send(f"Spawn weight for {rarity} has been set to {weight}.")
        await self.optcg_weights(ctx)
    
    @optcg.command(name="resetweights")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_resetweights(self, ctx: commands.Context):
        """Reset to default rarity spawn weights"""
        await self.config.guild(ctx.guild).use_default_weights.set(True)
        await self.config.guild(ctx.guild).custom_weights.clear()
        
        await ctx.send("Rarity spawn weights have been reset to default values.")
        await self.optcg_weights(ctx)
    
    @optcg.command(name="status")
    @commands.guild_only()
    async def optcg_status(self, ctx: commands.Context):
        """Check the status of the OPTCG card system"""
        guild_data = await self.config.guild(ctx.guild).all()
        
        if not guild_data["enabled"]:
            return await ctx.send("OPTCG card system is currently disabled in this server.")
        
        # Get the spawn channel
        channel_id = guild_data["spawn_channel"]
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            return await ctx.send(
                "OPTCG card system is enabled, but the configured spawn channel no longer exists."
            )
        
        # Check if there's an active card
        active_card = guild_data["active_card"]
        
        if active_card:
            try:
                card = self.cards_cache[str(active_card["card_id"])]
                return await ctx.send(
                    f"There is currently an active card waiting to be claimed in {channel.mention}!"
                )
            except KeyError:
                # Invalid card ID in active card, clear it
                await self.config.guild(ctx.guild).active_card.clear()
                active_card = None
        
        # Calculate time until next spawn
        next_spawn = guild_data["next_spawn_time"]
        if next_spawn:
            now = time.time()
            if now >= next_spawn:
                time_str = "soon"
            else:
                time_until = datetime.fromtimestamp(next_spawn) - datetime.now()
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = ""
                if hours > 0:
                    time_str += f"{hours} hours, "
                time_str += f"{minutes} minutes"
        else:
            time_str = "unknown time"
        
        await ctx.send(
            f"OPTCG card system is enabled in {channel.mention}.\n"
            f"Next card will spawn in approximately {time_str}."
        )
    
    @optcg.command(name="cards", aliases=["collection", "inventory"])
    @commands.guild_only()
    async def optcg_cards(self, ctx: commands.Context, member: discord.Member = None, 
                        rarity: str = None, sort: str = "newest"):
        """View your card collection
        
        You can filter by rarity and sort by oldest/newest
        
        Examples:
        - `[p]optcg cards` - View your own collection
        - `[p]optcg cards @User` - View someone else's collection
        - `[p]optcg cards @User "Secret Rare"` - View someone's Secret Rare cards
        - `[p]optcg cards @User "Super Rare" oldest` - View oldest Super Rare cards first
        """
        member = member or ctx.author
        
        # Get the member's card collection
        user_data = await self.config.member(member).all()
        cards = user_data["cards"]
        
        if not cards:
            return await ctx.send(f"{member.display_name} doesn't have any cards yet.")
        
        # Filter by rarity if specified
        valid_rarities = list(RARITY_WEIGHTS.keys())
        if rarity:
            if rarity not in valid_rarities:
                return await ctx.send(
                    f"Invalid rarity. Valid options are: {humanize_list(valid_rarities)}"
                )
            
            filtered_cards = []
            for card_entry in cards:
                card_id = str(card_entry["card_id"])
                if card_id in self.cards_cache:
                    card = self.cards_cache[card_id]
                    if card.get("rarity", "Common") == rarity:
                        filtered_cards.append(card_entry)
            
            cards = filtered_cards
            
            if not cards:
                return await ctx.send(f"{member.display_name} doesn't have any {rarity} cards.")
        
        # Sort the cards
        if sort.lower() in ["oldest", "old", "first"]:
            # Sort by claimed_at (oldest first)
            cards.sort(key=lambda x: x.get("claimed_at", ""))
        else:
            # Sort by claimed_at (newest first) - default
            cards.sort(key=lambda x: x.get("claimed_at", ""), reverse=True)
        
        # Create embeds for each card
        embeds = []
        for card_entry in cards:
            card_id = str(card_entry["card_id"])
            if card_id in self.cards_cache:
                card = self.cards_cache[card_id]
                embed = await self._create_card_embed(card)
                
                # Add claim timestamp
                claimed_at = card_entry.get("claimed_at")
                if claimed_at:
                    try:
                        claimed_datetime = datetime.fromisoformat(claimed_at)
                        embed.set_footer(text=f"Claimed: {claimed_datetime.strftime('%Y-%m-%d %H:%M')}")
                    except (ValueError, TypeError):
                        embed.set_footer(text="Claimed at unknown time")
                
                embeds.append(embed)
        
        if not embeds:
            return await ctx.send(f"No valid cards found in {member.display_name}'s collection.")
        
        # Show the collection
        title = f"{member.display_name}'s Card Collection"
        if rarity:
            title += f" - {rarity} Cards"
        
        await menu(
            ctx, 
            embeds, 
            DEFAULT_CONTROLS,
            page_start=0,
            timeout=60.0,
            message=await ctx.send(f"**{title}** (Page 1/{len(embeds)})")
        )
    
    @optcg.command(name="stats")
    @commands.guild_only()
    async def optcg_stats(self, ctx: commands.Context, member: discord.Member = None):
        """View card collection statistics"""
        member = member or ctx.author
        
        # Get the member's stats
        user_data = await self.config.member(member).all()
        stats = user_data["stats"]
        total_cards = len(user_data["cards"])
        
        if total_cards == 0:
            return await ctx.send(f"{member.display_name} hasn't collected any cards yet.")
        
        # Create stats embed
        embed = discord.Embed(
            title=f"{member.display_name}'s Card Collection Stats",
            description=f"Total Cards Collected: **{total_cards}**",
            color=member.color or discord.Color.blue()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add stats for each rarity
        for rarity in ["Leader", "Secret Rare", "Super Rare", "Rare", "Uncommon", "Common"]:
            emoji = RARITY_EMOJIS.get(rarity, "⚪")
            count = stats.get(rarity, 0)
            percentage = (count / total_cards * 100) if total_cards > 0 else 0
            
            embed.add_field(
                name=f"{emoji} {rarity}",
                value=f"{count} ({percentage:.1f}%)",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="force")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def optcg_force(self, ctx: commands.Context):
        """Force a card to spawn immediately"""
        guild_data = await self.config.guild(ctx.guild).all()
        
        if not guild_data["enabled"]:
            return await ctx.send("OPTCG card system is currently disabled in this server.")
        
        # Check if there's already an active card
        if guild_data["active_card"]:
            return await ctx.send("There's already an active card waiting to be claimed.")
        
        # Get the spawn channel
        channel_id = guild_data["spawn_channel"]
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            return await ctx.send("The configured spawn channel no longer exists.")
        
        # Force spawn a card
        await ctx.send("Forcing a card to spawn...")
        await self._spawn_card(ctx.guild, channel)
        
    @optcg.command(name="refresh")
    @commands.is_owner()
    async def optcg_refresh(self, ctx: commands.Context):
        """Refresh the card cache from the API (owner only)"""
        await ctx.send("Refreshing card cache from API...")
        
        try:
            await self._fetch_and_cache_cards()
            await ctx.send(f"✅ Successfully refreshed card cache. {len(self.cards_cache)} cards loaded.")
        except Exception as e:
            await ctx.send(f"❌ Error refreshing card cache: {e}")
    
    @optcg.command(name="leaderboard", aliases=["top"])
    @commands.guild_only()
    async def optcg_leaderboard(self, ctx: commands.Context, rarity: str = None):
        """View the top card collectors in the server
        
        You can specify a rarity to see the top collectors for that rarity.
        
        Example:
        - `[p]optcg leaderboard` - View overall leaderboard
        - `[p]optcg leaderboard "Secret Rare"` - View leaderboard for Secret Rare cards
        """
        all_members = await self.config.all_members(ctx.guild)
        
        if not all_members:
            return await ctx.send("No one has collected any cards yet.")
        
        # Build leaderboard data
        leaderboard_data = []
        
        if rarity:
            valid_rarities = list(RARITY_WEIGHTS.keys())
            if rarity not in valid_rarities:
                return await ctx.send(
                    f"Invalid rarity. Valid options are: {humanize_list(valid_rarities)}"
                )
                
            # Rarity-specific leaderboard
            for member_id, member_data in all_members.items():
                member = ctx.guild.get_member(member_id)
                if member:
                    count = member_data["stats"].get(rarity, 0)
                    if count > 0:
                        leaderboard_data.append((member, count))
            
            # Sort by count (descending)
            leaderboard_data.sort(key=lambda x: x[1], reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title=f"Top {rarity} Card Collectors",
                description=f"Leaderboard for {RARITY_EMOJIS.get(rarity, '⚪')} {rarity} cards",
                color=discord.Color.gold()
            )
        else:
            # Overall leaderboard
            for member_id, member_data in all_members.items():
                member = ctx.guild.get_member(member_id)
                if member:
                    total_cards = len(member_data["cards"])
                    if total_cards > 0:
                        leaderboard_data.append((member, total_cards))
            
            # Sort by count (descending)
            leaderboard_data.sort(key=lambda x: x[1], reverse=True)
            
            # Create embed
            embed = discord.Embed(
                title="Top Card Collectors",
                description="Overall card collection leaderboard",
                color=discord.Color.gold()
            )
        
        # Limit to top 10
        leaderboard_data = leaderboard_data[:10]
        
        if not leaderboard_data:
            return await ctx.send(f"No one has collected any{' ' + rarity if rarity else ''} cards yet.")
        
        # Add leaderboard entries to embed
        for i, (member, count) in enumerate(leaderboard_data, 1):
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
                
            embed.add_field(
                name=f"{medal}#{i} - {member.display_name}",
                value=f"{count} cards",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    @optcg.command(name="search")
    @commands.guild_only()
    async def optcg_search(self, ctx: commands.Context, *, search_term: str):
        """Search for cards by name
        
        Example:
        - `[p]optcg search Luffy` - Search for cards with "Luffy" in the name
        """
        search_term = search_term.lower()
        
        if len(self.cards_cache) == 0:
            await ctx.send("No cards available in cache. Attempting to refresh...")
            await self._fetch_and_cache_cards()
            if len(self.cards_cache) == 0:
                return await ctx.send("Failed to load any cards. Please try again later.")
        
        # Search for matching cards
        matching_cards = []
        for card_id, card in self.cards_cache.items():
            card_name = card.get("name", "").lower()
            
            # Check for exact matches or substring matches
            if search_term in card_name or search_term == card_name:
                matching_cards.append(card)
        
        # If no direct matches, try more lenient matching
        if not matching_cards:
            # Try matching individual words
            search_words = search_term.split()
            for card_id, card in self.cards_cache.items():
                card_name = card.get("name", "").lower()
                
                # Check if any of the search words match
                if any(word in card_name for word in search_words):
                    matching_cards.append(card)
        
        # If still no matches, check for partial word matches
        if not matching_cards:
            for card_id, card in self.cards_cache.items():
                card_name = card.get("name", "").lower()
                
                # Check for partial word matches
                for word in search_term.split():
                    if len(word) >= 3 and any(word in name_part for name_part in card_name.split()):
                        matching_cards.append(card)
                        break
        
        if not matching_cards:
            return await ctx.send(f"No cards found matching '{search_term}'")
        
        # Sort by name
        matching_cards.sort(key=lambda x: x.get("name", ""))
        
        # Create embeds for each matching card
        embeds = []
        for card in matching_cards:
            embed = await self._create_card_embed(card)
            embeds.append(embed)
        
        # Show the matching cards using menu
        # Different versions of Red have different menu parameters
        try:
            # Try the newer version with page_start
            await menu(
                ctx, 
                embeds, 
                DEFAULT_CONTROLS,
                page_start=0,
                timeout=60.0,
                message=await ctx.send(f"**Search Results for '{search_term}'** (Page 1/{len(embeds)})")
            )
        except TypeError:
            try:
                # Try without page_start (older Red versions)
                await menu(
                    ctx, 
                    embeds, 
                    DEFAULT_CONTROLS,
                    timeout=60.0,
                    message=await ctx.send(f"**Search Results for '{search_term}'** (Page 1/{len(embeds)})")
                )
            except TypeError:
                # Fall back to the most basic form if needed
                await menu(
                    ctx, 
                    pages=embeds,
                    controls=DEFAULT_CONTROLS
                )
        
    @optcg.command(name="view")
    @commands.guild_only()
    async def optcg_view(self, ctx: commands.Context, card_id: str):
        """View a specific card by ID
        
        Example:
        - `[p]optcg view OP01-001` - View card with ID OP01-001
        """
        if card_id not in self.cards_cache:
            return await ctx.send(f"No card found with ID '{card_id}'")
        
        card = self.cards_cache[card_id]
        embed = await self._create_card_embed(card)
        
        await ctx.send(embed=embed)
    
    @optcg.command(name="wipe")
    @commands.guild_only()
    @commands.admin_or_permissions(administrator=True)
    async def optcg_wipe(self, ctx: commands.Context, member: discord.Member = None):
        """Wipe a user's card collection (Admin only)
        
        Example:
        - `[p]optcg wipe @User` - Wipe the card collection of the specified user
        """
        if not member:
            return await ctx.send("You must specify a user to wipe their collection.")
        
        # Ask for confirmation
        confirm_msg = await ctx.send(
            f"⚠️ Are you sure you want to wipe {member.mention}'s entire card collection? "
            f"This action cannot be undone.\n\nReact with ✅ to confirm or ❌ to cancel."
        )
        
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == confirm_msg.id
                and str(reaction.emoji) in ["✅", "❌"]
            )
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            return await ctx.send("Wipe canceled - you didn't respond in time.")
        
        if str(reaction.emoji) == "❌":
            await confirm_msg.delete()
            return await ctx.send("Wipe canceled.")
        
        # Wipe the collection
        await self.config.member(member).clear()
        
        # Reinitialize the stats structure
        default_stats = {
            "Leader": 0,
            "Secret Rare": 0,
            "Super Rare": 0,
            "Rare": 0,
            "Uncommon": 0,
            "Common": 0
        }
        await self.config.member(member).stats.set(default_stats)
        
        await confirm_msg.delete()
        await ctx.send(f"✅ {member.mention}'s card collection has been wiped.")
    
    @optcg.command(name="trade")
    @commands.guild_only()
    async def optcg_trade(self, ctx: commands.Context, target: discord.Member, your_card_id: str, their_card_id: str):
        """Propose a card trade with another user
        
        Example:
        - `[p]optcg trade @User OP01-001 OP01-002` - Propose trading your OP01-001 for their OP01-002
        """
        if target.bot:
            return await ctx.send("You can't trade with bots.")
        
        if target == ctx.author:
            return await ctx.send("You can't trade with yourself.")
        
        # Check if both cards exist
        if your_card_id not in self.cards_cache:
            return await ctx.send(f"No card found with ID '{your_card_id}'")
        
        if their_card_id not in self.cards_cache:
            return await ctx.send(f"No card found with ID '{their_card_id}'")
        
        # Check if you have the card
        async with self.config.member(ctx.author).cards() as cards:
            your_cards = [card["card_id"] for card in cards]
            if your_card_id not in your_cards:
                return await ctx.send(f"You don't have the card with ID '{your_card_id}'")
        
        # Check if the target has the card
        async with self.config.member(target).cards() as cards:
            their_cards = [card["card_id"] for card in cards]
            if their_card_id not in their_cards:
                return await ctx.send(f"{target.display_name} doesn't have the card with ID '{their_card_id}'")
        
        # Get the card information
        your_card = self.cards_cache[your_card_id]
        their_card = self.cards_cache[their_card_id]
        
        # Create the trade proposal embed
        embed = discord.Embed(
            title="Card Trade Proposal",
            description=f"{ctx.author.mention} wants to trade with {target.mention}",
            color=discord.Color.blue()
        )
        
        # Add your card
        your_rarity = your_card.get("rarity", "Common")
        your_emoji = RARITY_EMOJIS.get(your_rarity, "⚪")
        embed.add_field(
            name=f"{ctx.author.display_name} offers:",
            value=f"{your_emoji} **{your_card.get('name')}** ({your_card_id})",
            inline=False
        )
        
        # Add their card
        their_rarity = their_card.get("rarity", "Common")
        their_emoji = RARITY_EMOJIS.get(their_rarity, "⚪")
        embed.add_field(
            name=f"{target.display_name} offers:",
            value=f"{their_emoji} **{their_card.get('name')}** ({their_card_id})",
            inline=False
        )
        
        embed.set_footer(text=f"{target.display_name}, react with ✅ to accept or ❌ to decline.")
        
        # Send the trade proposal
        trade_msg = await ctx.send(embed=embed)
        
        await trade_msg.add_reaction("✅")
        await trade_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == target
                and reaction.message.id == trade_msg.id
                and str(reaction.emoji) in ["✅", "❌"]
            )
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await trade_msg.edit(content="⏱️ Trade offer has expired.", embed=embed)
            return
        
        if str(reaction.emoji) == "❌":
            await trade_msg.edit(content="❌ Trade declined.", embed=embed)
            return
        
        # Trade accepted - perform the trade
        try:
            # Remove your card
            async with self.config.member(ctx.author).cards() as your_card_list:
                for i, card in enumerate(your_card_list):
                    if card["card_id"] == your_card_id:
                        your_card_obj = your_card_list.pop(i)
                        break
            
            # Remove their card
            async with self.config.member(target).cards() as their_card_list:
                for i, card in enumerate(their_card_list):
                    if card["card_id"] == their_card_id:
                        their_card_obj = their_card_list.pop(i)
                        break
            
            # Add their card to your collection
            async with self.config.member(ctx.author).cards() as your_card_list:
                your_card_list.append({
                    "card_id": their_card_id,
                    "claimed_at": datetime.now().isoformat(),
                    "obtained_via": "trade"
                })
            
            # Add your card to their collection
            async with self.config.member(target).cards() as their_card_list:
                their_card_list.append({
                    "card_id": your_card_id,
                    "claimed_at": datetime.now().isoformat(),
                    "obtained_via": "trade"
                })
            
            # Update stats
            # Remove from your stats
            async with self.config.member(ctx.author).stats() as stats:
                if your_rarity in stats:
                    stats[your_rarity] = max(0, stats[your_rarity] - 1)
            
            # Remove from their stats
            async with self.config.member(target).stats() as stats:
                if their_rarity in stats:
                    stats[their_rarity] = max(0, stats[their_rarity] - 1)
            
            # Add to your stats
            async with self.config.member(ctx.author).stats() as stats:
                if their_rarity in stats:
                    stats[their_rarity] += 1
                else:
                    stats[their_rarity] = 1
            
            # Add to their stats
            async with self.config.member(target).stats() as stats:
                if your_rarity in stats:
                    stats[your_rarity] += 1
                else:
                    stats[your_rarity] = 1
            
            await trade_msg.edit(content="✅ Trade completed successfully!", embed=embed)
        except Exception as e:
            log.error(f"Error during trade: {e}")
            await trade_msg.edit(content="❌ Error occurred during the trade. No cards were exchanged.", embed=embed)
            
    @optcg.command(name="debug")
    @commands.is_owner()
    async def optcg_debug(self, ctx: commands.Context):
        """Debug the OPTCG cog (owner only)"""
        
        debug_info = [
            f"Card cache size: {len(self.cards_cache)} cards",
            f"Card cache file exists: {os.path.exists(self.data_path)}",
            f"Sample card names: {', '.join([card.get('name', 'Unknown') for card_id, card in list(self.cards_cache.items())[:5]])}",
            f"Has 'Luffy' cards: {any('luffy' in card.get('name', '').lower() for card in self.cards_cache.values())}"
        ]
        
        await ctx.send("```\n" + "\n".join(debug_info) + "\n```")
        
        # Force a refresh and try again
        await ctx.send("Refreshing card cache...")
        await self._fetch_and_cache_cards()
        
        debug_info = [
            f"Card cache size after refresh: {len(self.cards_cache)} cards",
            f"Sample card names after refresh: {', '.join([card.get('name', 'Unknown') for card_id, card in list(self.cards_cache.items())[:5]])}",
            f"Has 'Luffy' cards after refresh: {any('luffy' in card.get('name', '').lower() for card in self.cards_cache.values())}"
        ]
        
        await ctx.send("```\n" + "\n".join(debug_info) + "\n```")
    
    @optcg.command(name="gift")
    @commands.guild_only()
    async def optcg_gift(self, ctx: commands.Context, target: discord.Member, card_id: str):
        """Gift a card to another user
        
        Example:
        - `[p]optcg gift @User OP01-001` - Gift your OP01-001 card to the specified user
        """
        if target.bot:
            return await ctx.send("You can't gift cards to bots.")
        
        if target == ctx.author:
            return await ctx.send("You can't gift cards to yourself.")
        
        # Check if the card exists
        if card_id not in self.cards_cache:
            return await ctx.send(f"No card found with ID '{card_id}'")
        
        # Check if you have the card
        async with self.config.member(ctx.author).cards() as cards:
            your_cards = [card["card_id"] for card in cards]
            if card_id not in your_cards:
                return await ctx.send(f"You don't have the card with ID '{card_id}'")
        
        # Get the card information
        card = self.cards_cache[card_id]
        rarity = card.get("rarity", "Common")
        emoji = RARITY_EMOJIS.get(rarity, "⚪")
        
        # Ask for confirmation
        confirm_msg = await ctx.send(
            f"Are you sure you want to gift your {emoji} **{card.get('name')}** ({card_id}) to {target.mention}?\n"
            f"React with ✅ to confirm or ❌ to cancel."
        )
        
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == confirm_msg.id
                and str(reaction.emoji) in ["✅", "❌"]
            )
        
        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await confirm_msg.delete()
            return await ctx.send("Gift canceled - you didn't respond in time.")
        
        if str(reaction.emoji) == "❌":
            await confirm_msg.delete()
            return await ctx.send("Gift canceled.")
        
        # Gift the card
        try:
            # Remove the card from your collection
            async with self.config.member(ctx.author).cards() as your_card_list:
                for i, card_obj in enumerate(your_card_list):
                    if card_obj["card_id"] == card_id:
                        your_card_obj = your_card_list.pop(i)
                        break
            
            # Add the card to their collection
            async with self.config.member(target).cards() as their_card_list:
                their_card_list.append({
                    "card_id": card_id,
                    "claimed_at": datetime.now().isoformat(),
                    "obtained_via": "gift"
                })
            
            # Update stats
            # Remove from your stats
            async with self.config.member(ctx.author).stats() as stats:
                if rarity in stats:
                    stats[rarity] = max(0, stats[rarity] - 1)
            
            # Add to their stats
            async with self.config.member(target).stats() as stats:
                if rarity in stats:
                    stats[rarity] += 1
                else:
                    stats[rarity] = 1
            
            await confirm_msg.delete()
            await ctx.send(
                f"✅ You have gifted your {emoji} **{card.get('name')}** to {target.mention}!"
            )
        except Exception as e:
            log.error(f"Error during gift: {e}")
            await confirm_msg.delete()
            await ctx.send("❌ An error occurred while gifting the card. Please try again later.")
    
    @optcg.command(name="nextspawn")
    @commands.guild_only()
    @commands.mod_or_permissions(manage_messages=True)
    async def optcg_nextspawn(self, ctx: commands.Context):
        """Check when the next card will spawn (Mod only)"""
        guild_data = await self.config.guild(ctx.guild).all()
        
        if not guild_data["enabled"]:
            return await ctx.send("OPTCG card system is currently disabled in this server.")
        
        # Check if there's an active card
        active_card = guild_data["active_card"]
        if active_card:
            channel_id = guild_data["spawn_channel"]
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                return await ctx.send(
                    f"There is currently an active card waiting to be claimed in {channel.mention}."
                )
        
        # Calculate time until next spawn
        next_spawn = guild_data["next_spawn_time"]
        if next_spawn:
            now = time.time()
            if now >= next_spawn:
                time_str = "very soon"
            else:
                time_until = datetime.fromtimestamp(next_spawn) - datetime.now()
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                time_str = ""
                if hours > 0:
                    time_str += f"{hours} hours, "
                time_str += f"{minutes} minutes, and {seconds} seconds"
                
                # Also include actual timestamp
                spawn_time = datetime.fromtimestamp(next_spawn)
                time_str += f" (at {spawn_time.strftime('%I:%M %p')})"
        else:
            time_str = "unknown time"
        
        await ctx.send(f"The next card will spawn in {time_str}.")

# This class needs to be imported at the top of the file
class CardClaimView(discord.ui.View):
    """View with a button to claim a card"""
    
    def __init__(self, cog, guild_id, card):
        super().__init__(timeout=1800)  # 30 minute timeout
        self.cog = cog
        self.guild_id = guild_id
        self.card = card
        self.claimed = False
        self.claimer = None
    
    @discord.ui.button(label="Claim Card!", style=discord.ButtonStyle.primary, emoji="🎴")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to claim a card"""
        # Stop if already claimed
        if self.claimed:
            return await interaction.response.send_message(
                "This card has already been claimed!", ephemeral=True
            )
        
        # Mark as claimed to prevent race conditions
        self.claimed = True
        self.claimer = interaction.user
        
        # Disable the button
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        button.style = discord.ButtonStyle.success
        
        # Add the card to the user's collection
        success = await self.cog.claim_card(self.guild_id, interaction.user.id, self.card)
        
        if not success:
            # Something went wrong
            await interaction.response.send_message(
                "There was an error claiming this card. Please try again later.", ephemeral=True
            )
            return
        
        # Create the reveal embed
        embed = await self.cog._create_card_embed(self.card, interaction.user)
        
        # Update the message with the revealed card
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Get user's current stats
        user_data = await self.cog.config.member_from_ids(
            self.guild_id, interaction.user.id
        ).all()
        
        stats = user_data["stats"]
        rarity = self.card.get("rarity", "Common")
        
        # Send confirmation to the user
        rarity_emoji = RARITY_EMOJIS.get(rarity, "⚪")
        
        stats_msg = (
            f"You claimed a {rarity_emoji} **{rarity}** card: **{self.card.get('name')}**!\n\n"
            f"Your collection stats:\n"
        )
        
        for r, emoji in RARITY_EMOJIS.items():
            count = stats.get(r, 0)
            stats_msg += f"{emoji} **{r}**: {count}\n"
        
        await interaction.followup.send(stats_msg, ephemeral=True)
    
    async def on_timeout(self):
        """Handle timeout - disable the button"""
        if not self.claimed:
            for child in self.children:
                child.disabled = True
            
            # Try to update the message
            guild = self.cog.bot.get_guild(self.guild_id)
            if guild:
                # Clear the active card
                await self.cog.config.guild(guild).active_card.clear()
                
                # Try to find the message
                guild_data = await self.cog.config.guild(guild).all()
                if guild_data["active_card"]:
                    channel_id = guild_data["spawn_channel"]
                    channel = guild.get_channel(channel_id)
                    if channel:
                        try:
                            message_id = guild_data["active_card"]["message_id"]
                            message = await channel.fetch_message(message_id)
                            await message.edit(view=self)
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            pass
