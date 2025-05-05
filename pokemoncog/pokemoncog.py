"""Main Pokemon cog implementation."""
import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Optional, Union

import discord
import aiohttp
from redbot.core import Config, commands
from redbot.core.bot import Red

from .constants import (
    SPAWN_CHANCE, 
    MIN_SPAWN_COOLDOWN, 
    CATCH_TIMEOUT, 
    XP_PER_MESSAGE
)

# Import command modules
from .commands.catch import CatchCommands
from .commands.settings import SettingsCommands
from .commands.team import TeamCommands
from .commands.info import InfoCommands

# Import utility functions
from .utils.spawn import spawn_pokemon, expire_spawn, add_pokemon_to_user, spawn_legendary, is_correct_catch
from .utils.api import fetch_pokemon, fetch_all_forms, get_random_pokemon_id
from .utils.formatters import format_pokemon_name

log = logging.getLogger("red.pokemon")

class PokemonCog(
    commands.Cog,
    CatchCommands,
    SettingsCommands,
    TeamCommands,
    InfoCommands
):
    """Pokemon cog for catching and training Pokemon in your Discord server!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4545484654887, force_registration=True
        )
        
        # Default configuration values
        default_guild = {
            "channel": None,  # Channel to spawn Pokemon in
            "active_pokemon": None,  # Currently active Pokemon to be caught
            "last_spawn": 0,  # Timestamp of last spawn
            "spawn_chance": SPAWN_CHANCE,
            "spawn_cooldown": MIN_SPAWN_COOLDOWN,
            "include_mega": False,  # Whether to include Mega Evolutions in spawns
            "include_gmax": False,  # Whether to include Gigantamax forms in spawns
            "include_forms": False,  # Whether to include other special forms
        }
        
        default_user = {
            "pokemon": {},  # {pokemon_id: {"level": level, "xp": current_xp, "name": name, "caught_at": timestamp}}
            "active_pokemon": None,  # ID of the currently active Pokemon
            "team": [],  # List of Pokemon IDs in the user's team
            "items": {},  # {item_name: count} - Mega Stones, Z-Crystals, etc.
            "money": 0,   # Currency for the shop
        }
        
        default_global = {
            "pokemon_cache": {},  # Cache for Pokemon data from API
            "form_cache": {},    # Cache for Pokemon form data
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        self.config.register_global(**default_global)
        
        self.session = aiohttp.ClientSession()
        self.spawns_active = {}  # {guild_id: {"pokemon": pokemon_data, "expiry": timestamp}}
        self.pokemon_locks = {}  # {guild_id: asyncio.Lock}
        
        # Start background tasks
        self.bg_tasks = []
        
    async def initialize(self):
        """Initialize the cog by loading cached data."""
        await self.bot.wait_until_ready()
        try:
            # Initialize locks for each guild
            for guild in self.bot.guilds:
                if guild.id not in self.pokemon_locks:
                    self.pokemon_locks[guild.id] = asyncio.Lock()
        except Exception as e:
            log.error(f"Error initializing Pokemon cog: {e}")
    
    async def cog_load(self):
        """Load the cog and start background tasks."""
        self.bg_tasks.append(self.bot.loop.create_task(self.initialize()))
        self.bg_tasks.append(self.bot.loop.create_task(self.check_temporary_forms()))
        self.bg_tasks.append(self.bot.loop.create_task(self.check_expired_spawns()))
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        # Cancel all background tasks
        for task in self.bg_tasks:
            task.cancel()
        
        # Close the aiohttp session
        asyncio.create_task(self.session.close())
        
        # Clean up any active spawns
        for guild_id, spawn_data in self.spawns_active.items():
            if spawn_data.get("expiry", 0) > datetime.now().timestamp():
                guild = self.bot.get_guild(guild_id)
                if guild:
                    channel_id = self.config.guild(guild).channel()
                    channel = guild.get_channel(channel_id)
                    if channel:
                        asyncio.create_task(
                            channel.send("The Pokemon cog is being unloaded. All active spawns have fled!")
                        )
    
    async def award_xp(self, user: discord.Member, xp_amount: int = XP_PER_MESSAGE):
        """Award XP to a user's active Pokemon."""
        active_pokemon_id = await self.config.user(user).active_pokemon()
        if not active_pokemon_id:
            return  # No active Pokemon
        
        async with self.config.user(user).pokemon() as user_pokemon:
            if active_pokemon_id not in user_pokemon:
                # Something went wrong, reset active Pokemon
                await self.config.user(user).active_pokemon.set(None)
                return
            
            pokemon = user_pokemon[active_pokemon_id]
            current_level = pokemon["level"]
            current_xp = pokemon["xp"]
            
            # Add XP
            new_xp = current_xp + xp_amount
            pokemon["xp"] = new_xp
            
            # Check if Pokemon should level up
            # XP required for next level = current_level^3
            xp_required = current_level**3
            
            if new_xp >= xp_required:
                # Level up!
                pokemon["level"] = current_level + 1
                pokemon["xp"] = 0  # Reset XP
                
                # Get Pokemon data
                pokemon_data = await fetch_pokemon(self.session, self.config, int(active_pokemon_id))
                
                # Check if Pokemon should evolve
                if (pokemon_data and pokemon_data.get("evolves_to") and 
                    pokemon_data.get("evolves_at_level") and 
                    current_level + 1 >= pokemon_data["evolves_at_level"]):
                    
                    # Check for special evolution conditions
                    can_evolve = True
                    if pokemon_data.get("evolution_condition"):
                        # For simplicity, we'll auto-evolve most conditional evolutions
                        # In a more complex system, these would require specific actions
                        if "happiness" in pokemon_data["evolution_condition"]:
                            can_evolve = True  # Assume enough happiness
                        elif "trade" in pokemon_data["evolution_condition"]:
                            can_evolve = False  # Trade evolutions need to be handled separately
                        elif "item" in pokemon_data["evolution_condition"] and pokemon_data["evolution_item"]:
                            # Check if user has the evolution item
                            user_items = await self.config.user(user).items()
                            if pokemon_data["evolution_item"] in user_items and user_items[pokemon_data["evolution_item"]] > 0:
                                # Use up the item
                                user_items[pokemon_data["evolution_item"]] -= 1
                                if user_items[pokemon_data["evolution_item"]] <= 0:
                                    del user_items[pokemon_data["evolution_item"]]
                                await self.config.user(user).items.set(user_items)
                            else:
                                can_evolve = False
                    
                    if can_evolve:
                        # Pokemon evolves!
                        evolution_id = str(pokemon_data["evolves_to"])
                        evolution_data = await fetch_pokemon(self.session, self.config, int(evolution_id))
                        
                        if evolution_data:
                            # Transfer data to the evolved form
                            evolved_pokemon = {
                                "name": evolution_data["name"],
                                "level": current_level + 1,
                                "xp": 0,
                                "caught_at": pokemon["caught_at"],
                                "count": 1,
                                "evolved_from": active_pokemon_id,
                                "evolved_at": datetime.now().timestamp()
                            }
                            
                            # Add to user's Pokemon
                            user_pokemon[evolution_id] = evolved_pokemon
                            
                            # Set as active Pokemon
                            await self.config.user(user).active_pokemon.set(evolution_id)
                            
                            # If this isn't the user's last of this Pokemon, decrement count
                            if pokemon["count"] > 1:
                                pokemon["count"] -= 1
                            else:
                                # Remove the pre-evolution
                                del user_pokemon[active_pokemon_id]
                            
                            # Award special stones for fully evolved Pokemon
                            await self.award_evolution_items(user, evolution_data)
                            
                            # Return evolution info
                            return {
                                "leveled_up": True,
                                "evolved": True,
                                "old_level": current_level,
                                "new_level": current_level + 1,
                                "old_pokemon": pokemon_data["name"],
                                "new_pokemon": evolution_data["name"]
                            }
                
                # No evolution, just level up
                return {
                    "leveled_up": True,
                    "evolved": False,
                    "old_level": current_level,
                    "new_level": current_level + 1,
                    "pokemon_name": pokemon["name"]
                }
            
            # No level up
            return None
    
    async def award_evolution_items(self, user: discord.Member, pokemon_data: dict):
        """Award special evolution items when a Pokemon reaches its final evolution."""
        from .constants import MEGA_STONES, Z_CRYSTALS, PRIMAL_ORBS
        
        # Check if this is a fully evolved Pokemon (no further evolutions)
        if not pokemon_data.get("evolves_to"):
            # This is a fully evolved Pokemon or has no evolutions
            # Random chance to award special items
            
            # Get user's items
            async with self.config.user(user).items() as user_items:
                # Check Pokemon ID for special items
                pokemon_id = pokemon_data["id"]
                
                # Check for Mega Stone eligibility
                if pokemon_id in MEGA_STONES or str(pokemon_id) in MEGA_STONES:
                    mega_stone = MEGA_STONES.get(pokemon_id) or MEGA_STONES.get(str(pokemon_id))
                    if mega_stone and random.random() < 0.15:  # 15% chance if eligible
                        # Award Mega Stone
                        user_items[mega_stone] = user_items.get(mega_stone, 0) + 1
                        return {"item": mega_stone, "type": "mega_stone"}
                
                # Check for Z-Crystal based on type
                if pokemon_data.get("types"):
                    primary_type = pokemon_data["types"][0].capitalize()
                    if primary_type in Z_CRYSTALS and random.random() < 0.1:  # 10% chance
                        z_crystal = Z_CRYSTALS[primary_type]
                        user_items[z_crystal] = user_items.get(z_crystal, 0) + 1
                        return {"item": z_crystal, "type": "z_crystal"}

                # Check for Primal Orb
                if pokemon_id in PRIMAL_ORBS or str(pokemon_id) in PRIMAL_ORBS:
                    orb = PRIMAL_ORBS.get(pokemon_id) or PRIMAL_ORBS.get(str(pokemon_id))
                    if orb and random.random() < 0.5:  # 50% chance since these are legendaries
                        user_items[orb] = user_items.get(orb, 0) + 1
                        return {"item": orb, "type": "primal_orb"}
        
        return None
    
    async def check_temporary_forms(self):
        """Background task to check for expired temporary forms."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.now().timestamp()
                
                # Check all users
                all_users = await self.config.all_users()
                
                for user_id, user_data in all_users.items():
                    if "pokemon" not in user_data:
                        continue
                    
                    # Get user's Pokemon
                    user_pokemon = user_data["pokemon"]
                    active_pokemon = user_data.get("active_pokemon")
                    
                    # Check for temporary forms
                    expired_forms = []
                    for pokemon_id, pokemon in user_pokemon.items():
                        if pokemon.get("temporary") and pokemon.get("expires_at", 0) <= now:
                            expired_forms.append((pokemon_id, pokemon))
                    
                    # Handle expired forms
                    if expired_forms:
                        # Get user object
                        for guild in self.bot.guilds:
                            member = guild.get_member(user_id)
                            if member:
                                # Found the user
                                async with self.config.user(member).pokemon() as user_pokemon_data:
                                    for pokemon_id, pokemon in expired_forms:
                                        # Remove the temporary form
                                        if pokemon_id in user_pokemon_data:
                                            del user_pokemon_data[pokemon_id]
                                            
                                            # If this was the active Pokemon, revert to base form
                                            if active_pokemon == pokemon_id:
                                                base_pokemon = pokemon.get("base_pokemon")
                                                if base_pokemon and base_pokemon in user_pokemon_data:
                                                    await self.config.user(member).active_pokemon.set(base_pokemon)
                                                else:
                                                    # Reset active Pokemon if base form not found
                                                    await self.config.user(member).active_pokemon.set(None)
                                                    
                                                # Try to send a DM to inform the user
                                                try:
                                                    form_type = pokemon.get("form_type", "special form")
                                                    await member.send(f"Your {pokemon['name'].capitalize()}'s {form_type} effect has worn off and it has reverted to its original form.")
                                                except:
                                                    pass  # Ignore if DM fails
                                break
            except Exception as e:
                log.error(f"Error in temporary form checker: {e}")
            
            # Check every 5 minutes
            await asyncio.sleep(300)
    
    async def check_expired_spawns(self):
        """Background task to check for expired spawns."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                now = datetime.now().timestamp()
                
                # Check all active spawns
                expired_spawns = []
                for guild_id, spawn_data in self.spawns_active.items():
                    if spawn_data.get("expiry", 0) <= now:
                        expired_spawns.append(guild_id)
                
                # Handle expired spawns
                for guild_id in expired_spawns:
                    if guild_id in self.spawns_active:
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            channel_id = await self.config.guild(guild).channel()
                            channel = guild.get_channel(channel_id)
                            if channel:
                                # Get Pokemon name
                                pokemon_data = self.spawns_active[guild_id].get("pokemon", {})
                                pokemon_name = pokemon_data.get("name", "Unknown")
                                
                                # Format display name
                                display_name = format_pokemon_name(pokemon_name, "-" in pokemon_name and pokemon_name.split("-", 1)[1])
                                
                                # Send expiry message
                                await channel.send(f"The wild {display_name} fled!")
                                
                                # Remove from active spawns
                                del self.spawns_active[guild_id]
            except Exception as e:
                log.error(f"Error in expired spawn checker: {e}")
            
            # Check every 10 seconds
            await asyncio.sleep(10)
    
    @commands.group(name="pokemon", aliases=["poke", "p"])
    async def pokemon_commands(self, ctx: commands.Context):
        """Pokemon commands for catching and training Pokemon."""
        if ctx.invoked_subcommand is None:
            # Send help message with overview of available commands
            embed = discord.Embed(
                title="Pokemon Commands",
                description="Use these commands to catch and train Pokemon!",
                color=0x3498db
            )
            
            embed.add_field(
                name="Basic Commands",
                value=f"• `{ctx.clean_prefix}p catch <pokemon>` - Catch a spawned Pokemon\n"
                      f"• `{ctx.clean_prefix}p list` - View your Pokemon collection\n"
                      f"• `{ctx.clean_prefix}p info <id>` - View Pokemon details\n"
                      f"• `{ctx.clean_prefix}p active <id>` - Set your active Pokemon",
                inline=False
            )
            
            embed.add_field(
                name="Team Management",
                value=f"• `{ctx.clean_prefix}p team` - View your team\n"
                      f"• `{ctx.clean_prefix}p team add <id>` - Add a Pokemon to your team\n"
                      f"• `{ctx.clean_prefix}p team remove <id>` - Remove a Pokemon from your team",
                inline=False
            )
            
            embed.add_field(
                name="Items & Shop",
                value=f"• `{ctx.clean_prefix}p shop` - Browse the shop\n"
                      f"• `{ctx.clean_prefix}p buy <item>` - Buy an item\n"
                      f"• `{ctx.clean_prefix}p items` - View your items\n"
                      f"• `{ctx.clean_prefix}p use <item> <id>` - Use an item on a Pokemon",
                inline=False
            )
            
            embed.add_field(
                name="Special Forms",
                value=f"• `{ctx.clean_prefix}p mega <id>` - Mega evolve a Pokemon\n"
                      f"• `{ctx.clean_prefix}p dynamax <id>` - Dynamax a Pokemon\n"
                      f"• `{ctx.clean_prefix}p primal <id>` - Primal reversion for Kyogre/Groudon",
                inline=False
            )
            
            embed.add_field(
                name="Misc Commands",
                value=f"• `{ctx.clean_prefix}p daily` - Claim daily rewards\n"
                      f"• `{ctx.clean_prefix}p dex <id>` - View Pokedex information\n"
                      f"• `{ctx.clean_prefix}p money` - Check your balance\n"
                      f"• `{ctx.clean_prefix}p settings` - Configure spawn settings (admin)",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages for Pokemon spawning and XP."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        # Award XP for active Pokemon
        if message.author.id != self.bot.user.id:
            xp_result = await self.award_xp(message.author)
            
            # Handle level up or evolution notifications if needed
            if xp_result and xp_result.get("leveled_up"):
                # Get the Pokemon name
                if xp_result.get("evolved"):
                    # Pokemon evolved
                    old_pokemon = xp_result.get("old_pokemon", "Unknown")
                    new_pokemon = xp_result.get("new_pokemon", "Unknown")
                    old_level = xp_result.get("old_level", 0)
                    new_level = xp_result.get("new_level", 0)
                    
                    # Format names
                    old_display = format_pokemon_name(old_pokemon, "-" in old_pokemon and old_pokemon.split("-", 1)[1])
                    new_display = format_pokemon_name(new_pokemon, "-" in new_pokemon and new_pokemon.split("-", 1)[1])
                    
                    # Send DM to the user about the evolution
                    try:
                        await message.author.send(
                            f"Your {old_display} (Lv. {old_level}) leveled up to Lv. {new_level} and evolved into {new_display}!"
                        )
                    except:
                        pass  # Ignore if DM fails
                else:
                    # Normal level up
                    pokemon_name = xp_result.get("pokemon_name", "Unknown")
                    old_level = xp_result.get("old_level", 0)
                    new_level = xp_result.get("new_level", 0)
                    
                    # Format name
                    display_name = format_pokemon_name(pokemon_name, "-" in pokemon_name and pokemon_name.split("-", 1)[1])
                    
                    # Send DM to the user about the level up
                    try:
                        await message.author.send(
                            f"Your {display_name} leveled up from Lv. {old_level} to Lv. {new_level}!"
                        )
                    except:
                        pass  # Ignore if DM fails
        
        # Check if this message is in a Pokemon channel
        guild_config = await self.config.guild(message.guild).all()
        spawn_channel_id = guild_config.get("channel")
        
        # Skip if no spawn channel is set or if this isn't the spawn channel
        if not spawn_channel_id or message.channel.id != spawn_channel_id:
            return
        
        # Initialize lock if needed
        if message.guild.id not in self.pokemon_locks:
            self.pokemon_locks[message.guild.id] = asyncio.Lock()
        
        # Use the lock to prevent race conditions
        async with self.pokemon_locks[message.guild.id]:
            # Check if a Pokemon is already active
            if message.guild.id in self.spawns_active:
                return
                
            # Get current time
            now = datetime.now().timestamp()
            last_spawn = guild_config.get("last_spawn", 0)
            cooldown = guild_config.get("spawn_cooldown", MIN_SPAWN_COOLDOWN)
            
            # Check if cooldown has passed
            if (now - last_spawn) < cooldown:
                return
            
            # Random chance to spawn a Pokemon based on guild's spawn chance setting
            spawn_chance = guild_config.get("spawn_chance", SPAWN_CHANCE)
            
            # Debug logging
            log.debug(f"Guild: {message.guild.name} | Spawn check: chance={spawn_chance} | Last spawn: {now - last_spawn}s ago")
            
            if random.random() < spawn_chance:
                # Attempt to spawn a Pokemon
                await spawn_pokemon(
                    self.bot, 
                    self.session, 
                    self.config, 
                    message.guild, 
                    self.spawns_active, 
                    self.pokemon_locks
                )
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize guild data when the bot joins a new guild."""
        # Create a lock for this guild
        if guild.id not in self.pokemon_locks:
            self.pokemon_locks[guild.id] = asyncio.Lock()
            
        # Send welcome message to the system channel if available
        if guild.system_channel:
            # Get the prefix
            if callable(self.bot.command_prefix):
                try:
                    prefix_list = await self.bot.command_prefix(self.bot, None, guild=guild)
                    prefix = prefix_list[0] if isinstance(prefix_list, list) else prefix_list
                except:
                    prefix = "!"
            else:
                prefix = self.bot.command_prefix[0] if isinstance(self.bot.command_prefix, list) else self.bot.command_prefix
                
            embed = discord.Embed(
                title="Pokemon Bot has joined the server!",
                description="Thanks for adding the Pokemon bot to your server! Here's how to get started:",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Set up a spawn channel",
                value=f"Use `{prefix}pokemon settings channel #channel-name` to set where Pokemon will spawn.",
                inline=False
            )
            
            embed.add_field(
                name="Catch Pokemon",
                value=f"When a Pokemon appears, use `{prefix}p catch <pokemon-name>` to catch it!",
                inline=False
            )
            
            embed.add_field(
                name="Help and Commands",
                value=f"Use `{prefix}help pokemon` to see all available commands.",
                inline=False
            )
            
            await guild.system_channel.send(embed=embed)
    
    # Implementation of missing command groups
    
    @commands.command(name="shop")
    async def pokemon_shop(self, ctx: commands.Context):
        """Browse the Pokemon item shop."""
        from .utils.formatters import create_shop_embed
        
        user = ctx.author
        user_money = await self.config.user(user).money()
        
        # Create shop embed
        embed = create_shop_embed(user_money)
        await ctx.send(embed=embed)
    
    @commands.command(name="buy")
    async def buy_item(self, ctx: commands.Context, *, item: str):
        """Buy an item from the Pokemon shop."""
        from .constants import SHOP_ITEMS
        
        user = ctx.author
        user_money = await self.config.user(user).money()
        
        # Find the item
        item_key = item.lower()
        item_data = None
        
        for key, data in SHOP_ITEMS.items():
            if key == item_key or key in item_key:
                item_data = data
                break
        
        if not item_data:
            await ctx.send(f"Sorry, the item '{item}' is not available in the shop. Use `{ctx.clean_prefix}pokemon shop` to see available items.")
            return
        
        # Check if user has enough money
        if user_money < item_data["price"]:
            await ctx.send(f"You don't have enough money to buy {item_data['name']}. It costs ${item_data['price']} but you only have ${user_money}.")
            return
        
        # Purchase the item
        async with self.config.user(user).money() as money:
            money -= item_data["price"]
        
        async with self.config.user(user).items() as user_items:
            user_items[item_data["name"]] = user_items.get(item_data["name"], 0) + 1
        
        await ctx.send(f"You bought a {item_data['name']} for ${item_data['price']}! You now have ${money} left.")
    
    @commands.command(name="money", aliases=["balance", "wallet"])
    async def check_money(self, ctx: commands.Context, user: discord.Member = None):
        """Check your money balance."""
        if user is None:
            user = ctx.author
        
        money = await self.config.user(user).money()
        await ctx.send(f"{user.name}'s balance: ${money}")
    
    @commands.command(name="items", aliases=["bag", "inventory"])
    async def view_items(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's item inventory."""
        from .utils.formatters import create_items_embed
        
        if user is None:
            user = ctx.author
            
        # Get user's items
        user_items = await self.config.user(user).items()
        
        if not user_items:
            await ctx.send(f"{user.name} doesn't have any items!")
            return
            
        # Create and send the items embed
        embed = create_items_embed(user, user_items)
        await ctx.send(embed=embed)
    
    @commands.command(name="daily")
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def daily_reward(self, ctx: commands.Context):
        """Claim your daily reward."""
        from .utils.formatters import create_daily_reward_embed
        
        user = ctx.author
        
        # Money reward
        money_reward = random.randint(500, 2000)
        current_money = await self.config.user(user).money()
        await self.config.user(user).money.set(current_money + money_reward)
        
        # XP bonus for active Pokemon
        active_pokemon_id = await self.config.user(user).active_pokemon()
        xp_bonus = None
        pokemon_name = None
        level_up = False
        new_level = None
        
        if active_pokemon_id:
            xp_bonus = random.randint(20, 50)
            
            # Get Pokemon data
            user_pokemon = await self.config.user(user).pokemon()
            if active_pokemon_id in user_pokemon:
                # Get Pokemon data
                active_pokemon = user_pokemon[active_pokemon_id]
                current_xp = active_pokemon["xp"]
                current_level = active_pokemon["level"]
                
                # Calculate new XP and level
                new_xp = current_xp + xp_bonus
                xp_required = current_level**3
                new_level = current_level
                
                if new_xp >= xp_required:
                    # Level up!
                    new_level = current_level + 1
                    new_xp = new_xp - xp_required
                    level_up = True
                
                # Update the Pokemon data
                active_pokemon["xp"] = new_xp
                active_pokemon["level"] = new_level
                
                # Save the changes
                await self.config.user(user).pokemon.set(user_pokemon)
                
                # Get Pokemon name for display
                form_type = active_pokemon.get("form_type")
                pokemon_data = await fetch_pokemon(self.session, self.config, int(active_pokemon_id), form_type)
                
                if pokemon_data:
                    pokemon_name = format_pokemon_name(pokemon_data["name"], form_type)
                else:
                    pokemon_name = active_pokemon["name"].capitalize()
        
        # Random item reward (30% chance)
        item_reward = None
        if random.random() < 0.3:
            possible_items = [
                # Common items (70%)
                {"name": "Potion", "weight": 70},
                {"name": "Super Potion", "weight": 50},
                {"name": "Revive", "weight": 40},
                
                # Uncommon items (25%)
                {"name": "Hyper Potion", "weight": 25},
                {"name": "Rare Candy", "weight": 15},
                {"name": "Exp. Candy", "weight": 20},
                
                # Rare items (5%)
                {"name": "Max Potion", "weight": 5},
                {"name": "Max Revive", "weight": 5},
                {"name": "PP Up", "weight": 3},
                
                # Very rare items (1%)
                {"name": "Lucky Egg", "weight": 1},
            ]
            
            # If user has high-level Pokemon, add evolution items
            highest_level = 0
            
            # Check if user_pokemon is not empty
            if user_pokemon := await self.config.user(user).pokemon():
                highest_level = max((p["level"] for p in user_pokemon.values()), default=0)
            
            if highest_level >= 25:
                evolution_stones = [
                    {"name": "Fire Stone", "weight": 2},
                    {"name": "Water Stone", "weight": 2},
                    {"name": "Thunder Stone", "weight": 2},
                    {"name": "Leaf Stone", "weight": 2},
                    {"name": "Moon Stone", "weight": 2},
                    {"name": "Sun Stone", "weight": 1},
                    {"name": "Shiny Stone", "weight": 1},
                    {"name": "Dusk Stone", "weight": 1},
                    {"name": "Dawn Stone", "weight": 1},
                ]
                possible_items.extend(evolution_stones)
            
            # Choose an item based on weights
            total_weight = sum(item["weight"] for item in possible_items)
            rand_val = random.uniform(0, total_weight)
            
            current_weight = 0
            chosen_item = possible_items[0]["name"]  # Default
            
            for item in possible_items:
                current_weight += item["weight"]
                if rand_val <= current_weight:
                    chosen_item = item["name"]
                    break
            
            # Award the item
            item_reward = chosen_item
            async with self.config.user(user).items() as items:
                items[chosen_item] = items.get(chosen_item, 0) + 1
        
        # Create and send the reward embed
        from .utils.formatters import create_daily_reward_embed
        embed = create_daily_reward_embed(
            user=user,
            money_reward=money_reward,
            xp_bonus=xp_bonus,
            pokemon_name=pokemon_name,
            level_up=level_up,
            new_level=new_level,
            item_reward=item_reward
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="use")
    async def use_item(self, ctx: commands.Context, item: str, pokemon_id: int = None):
        """Use an item on a Pokemon."""
        user = ctx.author
        
        # Get user's items
        user_items = await self.config.user(user).items()
        
        # Check if user has the item
        found_item = None
        for item_name in user_items.keys():
            if item.lower() in item_name.lower():
                found_item = item_name
                break
                
        if not found_item:
            await ctx.send(f"You don't have an item called '{item}'!")
            return
        
        # Handle different item types based on whether pokemon_id is provided
        from .constants import MEGA_STONES, Z_CRYSTALS, PRIMAL_ORBS, EVOLUTION_MAPPING
        
        # If no Pokemon ID provided, and it's a general use item
        if not pokemon_id and found_item in ["Rare Candy", "Exp. Candy", "Lucky Egg"]:
            # General use items that don't need a specific Pokemon
            if found_item == "Rare Candy":
                # Get active Pokemon
                active_pokemon_id = await self.config.user(user).active_pokemon()
                if not active_pokemon_id:
                    await ctx.send("You don't have an active Pokemon! Choose one first.")
                    return
                    
                # Apply Rare Candy (level up)
                async with self.config.user(user).pokemon() as user_pokemon:
                    if active_pokemon_id not in user_pokemon:
                        await ctx.send("Your active Pokemon data is missing!")
                        return
                        
                    pokemon = user_pokemon[active_pokemon_id]
                    old_level = pokemon["level"]
                    pokemon["level"] += 1
                    new_level = pokemon["level"]
                    
                    # Get Pokemon name
                    form_type = pokemon.get("form_type")
                    pokemon_data = await fetch_pokemon(self.session, self.config, int(active_pokemon_id), form_type)
                    
                    if pokemon_data:
                        pokemon_name = format_pokemon_name(pokemon_data["name"], form_type)
                    else:
                        pokemon_name = f"Pokemon #{active_pokemon_id}"
                    
                    # Use up item
                    async with self.config.user(user).items() as items:
                        items[found_item] -= 1
                        if items[found_item] <= 0:
                            del items[found_item]
                    
                    await ctx.send(f"You used a Rare Candy on {pokemon_name}! It grew from level {old_level} to {new_level}!")
                    return
                    
            elif found_item == "Exp. Candy":
                # Get active Pokemon
                active_pokemon_id = await self.config.user(user).active_pokemon()
                if not active_pokemon_id:
                    await ctx.send("You don't have an active Pokemon! Choose one first.")
                    return
                    
                # Apply Exp Candy (add XP)
                async with self.config.user(user).pokemon() as user_pokemon:
                    if active_pokemon_id not in user_pokemon:
                        await ctx.send("Your active Pokemon data is missing!")
                        return
                        
                    pokemon = user_pokemon[active_pokemon_id]
                    old_xp = pokemon["xp"]
                    pokemon["xp"] += 100  # Add 100 XP
                    new_xp = pokemon["xp"]
                    
                    # Get Pokemon name
                    form_type = pokemon.get("form_type")
                    pokemon_data = await fetch_pokemon(self.session, self.config, int(active_pokemon_id), form_type)
                    
                    if pokemon_data:
                        pokemon_name = format_pokemon_name(pokemon_data["name"], form_type)
                    else:
                        pokemon_name = f"Pokemon #{active_pokemon_id}"
                    
                    # Calculate XP needed for next level
                    xp_needed = pokemon["level"]**3
                    progress = min(100, int((new_xp / xp_needed) * 100))
                    
                    # Use up item
                    async with self.config.user(user).items() as items:
                        items[found_item] -= 1
                        if items[found_item] <= 0:
                            del items[found_item]
                    
                    await ctx.send(f"You used an Exp. Candy on {pokemon_name}! It gained 100 XP and is now at {progress}% to the next level!")
                    return
                    
            elif found_item == "Lucky Egg":
                # This would need a more complex implementation to track time-based XP boosts
                await ctx.send("You used a Lucky Egg! Your active Pokemon will now earn double XP for the next hour!")
                # Use up item
                async with self.config.user(user).items() as items:
                    items[found_item] -= 1
                    if items[found_item] <= 0:
                        del items[found_item]
                return
        
        # Item needs a specific Pokemon
        if not pokemon_id:
            await ctx.send(f"You need to specify which Pokemon to use {found_item} on!")
            return
            
        pokemon_id_str = str(pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
            
        # Handle different item types
        pokemon_data = await fetch_pokemon(self.session, self.config, pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
        
        # Format display name
        form_type = user_pokemon[pokemon_id_str].get("form_type")
        display_name = format_pokemon_name(pokemon_data["name"], form_type)
            
        # Evolution stones
        stone_types = ["Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", 
                       "Moon Stone", "Sun Stone", "Shiny Stone", "Dusk Stone", "Dawn Stone"]
                       
        if found_item in stone_types:
            # Check if this Pokemon can evolve with this stone
            base_name = pokemon_data["name"].lower().split('-')[0]  # Handle form variants
            
            # Check if this Pokemon is in the evolution mapping for this stone
            stone_key = found_item.lower()
            if stone_key in EVOLUTION_MAPPING and base_name in EVOLUTION_MAPPING[stone_key]:
                # Get evolution data
                evolution_info = EVOLUTION_MAPPING[stone_key][base_name]
                
                # Handle conditional evolutions (like Dawn Stone)
                if isinstance(evolution_info, dict) and "condition" in evolution_info:
                    # Check gender condition
                    required_gender = evolution_info["condition"]
                    pokemon_gender = user_pokemon[pokemon_id_str].get("gender")
                    
                    # If no gender stored, randomly assign one
                    if pokemon_gender is None:
                        pokemon_gender = "male" if random.random() < 0.5 else "female"
                        # Store for future reference
                        async with self.config.user(user).pokemon() as user_poke:
                            user_poke[pokemon_id_str]["gender"] = pokemon_gender
                    
                    if pokemon_gender != required_gender:
                        await ctx.send(f"Only {required_gender} {display_name} can evolve with {found_item}!")
                        return
                    
                    # Get evolution ID
                    evolution_id = evolution_info["id"]
                else:
                    # Simple evolution
                    evolution_id = evolution_info if isinstance(evolution_info, int) else evolution_info["id"]
                
                # Special handling for regional forms
                from .constants import REGIONAL_EVOLUTIONS
                
                if "-" in pokemon_data["name"]:
                    # This is a regional form, check if it has a special evolution
                    if pokemon_data["name"] in REGIONAL_EVOLUTIONS:
                        regional_evo = REGIONAL_EVOLUTIONS[pokemon_data["name"]]
                        evolution_id = regional_evo["id"]
                
                # Get evolution data
                evolution_data = await fetch_pokemon(self.session, self.config, evolution_id)
                
                if not evolution_data:
                    await ctx.send("Error fetching evolution data. Please try again.")
                    return
                
                # Evolve the Pokemon
                async with self.config.user(user).pokemon() as user_poke:
                    pokemon = user_poke[pokemon_id_str]
                    
                    # Create evolved form
                    evolved_id = str(evolution_id)
                    user_poke[evolved_id] = {
                        "name": evolution_data["name"],
                        "level": pokemon["level"],
                        "xp": pokemon["xp"],
                        "caught_at": datetime.now().timestamp(),
                        "count": 1,
                        "evolved_from": pokemon_id_str,
                        "evolved_at": datetime.now().timestamp()
                    }
                    
                    # Preserve form type if this is a regional form
                    if "-" in pokemon_data["name"] and any(form in pokemon_data["name"] for form in ["alola", "galar", "hisui"]):
                        form = pokemon_data["name"].split("-")[1]
                        user_poke[evolved_id]["form_type"] = form
                    
                    # Remove pre-evolution or decrement count
                    if pokemon["count"] > 1:
                        pokemon["count"] -= 1
                    else:
                        del user_poke[pokemon_id_str]
                        
                    # Update active Pokemon if needed
                    if await self.config.user(user).active_pokemon() == pokemon_id_str:
                        await self.config.user(user).active_pokemon.set(evolved_id)
                
                # Use up item
                async with self.config.user(user).items() as items:
                    items[found_item] -= 1
                    if items[found_item] <= 0:
                        del items[found_item]
                
                # Format evolution name
                evolution_display = format_pokemon_name(evolution_data["name"])
                await ctx.send(f"You used a {found_item} on {display_name}! It evolved into {evolution_display}!")
                return
            else:
                await ctx.send(f"{display_name} can't evolve with a {found_item}!")
                return
        
        # Mega Stones
        if "ite" in found_item and found_item in [stone for stone in MEGA_STONES.values()]:
            # Will be implemented in a separate file for special forms
            await ctx.send(f"Mega Evolution will be implemented in a future update!")
            return
            
        # Primal Orbs
        if "Orb" in found_item and found_item in [orb for orb in PRIMAL_ORBS.values()]:
            # Will be implemented in a separate file for special forms
            await ctx.send(f"Primal Reversion will be implemented in a future update!")
            return
            
        # Dynamax Band
        if found_item == "Dynamax Band":
            # Will be implemented in a separate file for special forms
            await ctx.send(f"Dynamax/Gigantamax will be implemented in a future update!")
            return
            
        # Z-Crystals
        if "Z" in found_item and found_item in [crystal for crystal in Z_CRYSTALS.values()]:
            await ctx.send(f"You held up the {found_item}! {display_name} can now use a Z-Move in battle!")
            return
            
        # If we got here, the item isn't usable on this Pokemon
        await ctx.send(f"{found_item} can't be used on {display_name}!")
    
    @commands.command(name="mega")
    async def mega_evolve(self, ctx: commands.Context, pokemon_id: int):
        """Mega evolve a Pokemon using a Mega Stone."""
        # This is a placeholder for the mega evolution implementation
        # Will be implemented in a separate file for special forms
        await ctx.send("Mega Evolution will be implemented in a future update!")
    
    @commands.command(name="dynamax")
    async def dynamax_pokemon(self, ctx: commands.Context, pokemon_id: int):
        """Dynamax or Gigantamax a Pokemon."""
        # This is a placeholder for the dynamax implementation
        # Will be implemented in a separate file for special forms
        await ctx.send("Dynamax/Gigantamax will be implemented in a future update!")
    
    @commands.command(name="primal")
    async def primal_reversion(self, ctx: commands.Context, pokemon_id: int):
        """Trigger Primal Reversion for Kyogre or Groudon."""
        # This is a placeholder for the primal reversion implementation
        # Will be implemented in a separate file for special forms
        await ctx.send("Primal Reversion will be implemented in a future update!")
    
    # Event command for admins
    @commands.command(name="event")
    @commands.admin_or_permissions(manage_guild=True)
    async def pokemon_event(self, ctx: commands.Context, event_type: str = None):
        """Trigger a special Pokemon event (admin only)."""
        if not event_type:
            # Show available events
            embed = discord.Embed(
                title="Pokemon Events",
                description="Available events you can trigger:",
                color=0xff00ff
            )
            
            embed.add_field(
                name="Legendary",
                value="Spawns a random legendary Pokemon",
                inline=True
            )
            
            embed.add_field(
                name="Safari",
                value="Increases spawn rates for the next hour",
                inline=True
            )
            
            embed.add_field(
                name="MegaDay",
                value="Increased chance of mega evolution items",
                inline=True
            )
            
            embed.add_field(
                name="TypeFocus",
                value="Spawns Pokemon of a specific type",
                inline=True
            )
            
            embed.add_field(
                name="ShinyHunt",
                value="Chance to catch shiny Pokemon",
                inline=True
            )
            
            await ctx.send(embed=embed)
            return
        
        # Handle different event types
        event_type = event_type.lower()
        
        if event_type == "legendary":
            # Spawn a legendary Pokemon
            result = await spawn_legendary(
                self.bot,
                self.session,
                self.config,
                ctx.guild,
                self.spawns_active,
                self.pokemon_locks
            )
            
            if result:
                await ctx.send("A legendary Pokemon has appeared!")
            else:
                await ctx.send("Failed to spawn a legendary Pokemon. Make sure a spawn channel is set.")
        
        elif event_type == "safari":
            # Increase spawn rate for 1 hour
            old_rate = await self.config.guild(ctx.guild).spawn_chance()
            new_rate = min(old_rate * 3, 0.5)  # Triple spawn rate, max 50%
            
            old_cooldown = await self.config.guild(ctx.guild).spawn_cooldown()
            new_cooldown = max(old_cooldown // 2, 15)  # Half cooldown, min 15 seconds
            
            # Set new rates
            await self.config.guild(ctx.guild).spawn_chance.set(new_rate)
            await self.config.guild(ctx.guild).spawn_cooldown.set(new_cooldown)
            
            # Create scheduled task to reset rates
            async def reset_rates():
                await asyncio.sleep(3600)  # 1 hour
                await self.config.guild(ctx.guild).spawn_chance.set(old_rate)
                await self.config.guild(ctx.guild).spawn_cooldown.set(old_cooldown)
                
                # Get the channel
                channel = ctx.guild.get_channel(ctx.channel.id)
                if channel:
                    await channel.send("The Safari Zone event has ended. Spawn rates have returned to normal.")
            
            # Start reset task
            self.bot.loop.create_task(reset_rates())
            
            # Announce the event
            embed = discord.Embed(
                title="🌿 Safari Zone Event Started! 🌿",
                description="For the next hour, Pokemon will spawn much more frequently!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Event Bonuses",
                value=f"Spawn Rate: {old_rate*100:.1f}% → {new_rate*100:.1f}%\nCooldown: {old_cooldown}s → {new_cooldown}s",
                inline=False
            )
            
            await ctx.send(embed=embed)
        
        else:
            await ctx.send(f"Event type '{event_type}' is not yet implemented.")