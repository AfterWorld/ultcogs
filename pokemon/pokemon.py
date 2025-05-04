import asyncio
import discord
import random
import logging
import aiohttp
import json
import math
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.pokemon")

# Constants
SPAWN_CHANCE = 0.1  # 10% chance of spawn per message
MIN_SPAWN_COOLDOWN = 60  # Minimum 60 seconds between spawns
XP_PER_MESSAGE = 1  # XP gained per message
CATCH_TIMEOUT = 30  # Seconds to catch a Pokemon

class PokemonCog(commands.Cog):
    """Pokemon cog for catching and training Pokemon in your Discord server!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4545484654887, force_registration=True
        )
        default_guild = {
            "channel": None,  # Channel to spawn Pokemon in
            "active_pokemon": None,  # Currently active Pokemon to be caught
            "last_spawn": 0,  # Timestamp of last spawn
            "spawn_chance": SPAWN_CHANCE,
            "spawn_cooldown": MIN_SPAWN_COOLDOWN,
        }
        default_user = {
            "pokemon": {},  # {pokemon_id: {"level": level, "xp": current_xp, "name": name, "caught_at": timestamp}}
            "active_pokemon": None,  # ID of the currently active Pokemon
        }
        default_global = {
            "pokemon_cache": {},  # Cache for Pokemon data from API
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        self.config.register_global(**default_global)
        
        self.session = aiohttp.ClientSession()
        self.spawns_active = {}  # {guild_id: {"pokemon": pokemon_data, "expiry": timestamp}}
        self.pokemon_locks = {}  # {guild_id: asyncio.Lock}
        
        # Start background task
        self.bg_task = self.bot.loop.create_task(self.initialize())
    
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
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.bg_task:
            self.bg_task.cancel()
        asyncio.create_task(self.session.close())
    
    async def fetch_pokemon(self, pokemon_id: int) -> dict:
        """Fetch Pokemon data from PokeAPI."""
        # Check cache first
        pokemon_cache = await self.config.pokemon_cache()
        str_id = str(pokemon_id)
        
        if str_id in pokemon_cache:
            return pokemon_cache[str_id]
        
        # If not in cache, fetch from API
        try:
            async with self.session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Also get species data for evolution details
                    async with self.session.get(data["species"]["url"]) as species_response:
                        if species_response.status == 200:
                            species_data = await species_response.json()
                        else:
                            species_data = {}
                    
                    # Extract only needed info to reduce cache size
                    pokemon_info = {
                        "id": data["id"],
                        "name": data["name"],
                        "types": [t["type"]["name"] for t in data["types"]],
                        "height": data["height"],
                        "weight": data["weight"],
                        "sprite": data["sprites"]["front_default"],
                        "base_experience": data["base_experience"],
                        "stats": {s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
                        "evolution_chain_url": species_data.get("evolution_chain", {}).get("url", None),
                        "evolves_at_level": None,  # Will be populated if this Pokemon evolves
                        "evolves_to": None,  # Will be populated if this Pokemon evolves
                    }
                    
                    # Get evolution data if available
                    if pokemon_info["evolution_chain_url"]:
                        async with self.session.get(pokemon_info["evolution_chain_url"]) as evo_response:
                            if evo_response.status == 200:
                                evo_data = await evo_response.json()
                                
                                # Process evolution chain
                                current = evo_data["chain"]
                                chain = []
                                
                                while current:
                                    species_name = current["species"]["name"]
                                    # Get the numeric ID from the URL
                                    species_url = current["species"]["url"]
                                    species_id = int(species_url.split("/")[-2])
                                    
                                    # Get evolution details
                                    evolves_to = []
                                    for evolution in current["evolves_to"]:
                                        evo_name = evolution["species"]["name"]
                                        evo_url = evolution["species"]["url"]
                                        evo_id = int(evo_url.split("/")[-2])
                                        
                                        # Extract level trigger if it exists
                                        level = None
                                        for detail in evolution["evolution_details"]:
                                            if detail["trigger"]["name"] == "level-up":
                                                level = detail.get("min_level")
                                                break
                                        
                                        evolves_to.append({
                                            "id": evo_id,
                                            "name": evo_name,
                                            "level": level
                                        })
                                    
                                    chain.append({
                                        "id": species_id,
                                        "name": species_name,
                                        "evolves_to": evolves_to
                                    })
                                    
                                    # Move to the next in chain
                                    if current["evolves_to"]:
                                        current = current["evolves_to"][0]
                                    else:
                                        current = None
                                
                                # Find this Pokemon in the chain
                                for i, stage in enumerate(chain):
                                    if stage["id"] == pokemon_id:
                                        if stage["evolves_to"]:
                                            # This Pokemon evolves
                                            for evo in stage["evolves_to"]:
                                                pokemon_info["evolves_to"] = evo["id"]
                                                pokemon_info["evolves_at_level"] = evo["level"]
                                        break
                    
                    # Save to cache
                    pokemon_cache[str_id] = pokemon_info
                    await self.config.pokemon_cache.set(pokemon_cache)
                    
                    return pokemon_info
                else:
                    log.error(f"Error fetching Pokemon {pokemon_id}: HTTP {response.status}")
                    return None
        except Exception as e:
            log.error(f"Error fetching Pokemon {pokemon_id}: {e}")
            return None
    
    async def spawn_pokemon(self, guild: discord.Guild) -> bool:
        """Attempt to spawn a Pokemon in the guild."""
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config["channel"]
        
        if not channel_id:
            return False  # No channel set for this guild
            
        channel = guild.get_channel(channel_id)
        if not channel:
            return False  # Channel no longer exists
        
        # Get current time
        now = datetime.now().timestamp()
        
        # Check cooldown
        if (now - guild_config["last_spawn"]) < guild_config["spawn_cooldown"]:
            return False
        
        # Determine which Pokemon to spawn (1-898 for all National Dex Pokemon)
        pokemon_id = random.randint(1, 898)
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        
        if not pokemon_data:
            return False
        
        # Create embed for spawn
        embed = discord.Embed(
            title="A wild Pokémon appeared!",
            description=f"Type `!catch <pokemon>` to catch it!",
            color=0x00ff00
        )
        
        # Use silhouette for the mystery
        embed.set_image(url=pokemon_data["sprite"])
        
        # Set expiry time
        expiry = now + CATCH_TIMEOUT
        
        # Store active spawn
        self.spawns_active[guild.id] = {
            "pokemon": pokemon_data,
            "expiry": expiry
        }
        
        # Update last spawn time
        await self.config.guild(guild).last_spawn.set(now)
        
        # Send spawn message
        await channel.send(embed=embed)
        
        # Set up expiry task
        self.bot.loop.create_task(self.expire_spawn(guild.id, channel, expiry))
        
        return True
    
    async def expire_spawn(self, guild_id: int, channel: discord.TextChannel, expiry: float):
        """Expire a spawn after the timeout period."""
        now = datetime.now().timestamp()
        wait_time = expiry - now
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        # Check if the spawn is still active (it might have been caught)
        if guild_id in self.spawns_active and self.spawns_active[guild_id]["expiry"] == expiry:
            pokemon_name = self.spawns_active[guild_id]["pokemon"]["name"].capitalize()
            
            # Remove the spawn
            del self.spawns_active[guild_id]
            
            # Send expiry message
            await channel.send(f"The wild {pokemon_name} fled!")
    
    async def add_pokemon_to_user(self, user: discord.Member, pokemon_data: dict):
        """Add a caught Pokemon to a user's collection."""
        async with self.config.user(user).pokemon() as user_pokemon:
            pokemon_id = str(pokemon_data["id"])
            now = datetime.now().timestamp()
            
            # Check if user already has this Pokemon
            if pokemon_id in user_pokemon:
                # User already has this Pokemon, increment count
                user_pokemon[pokemon_id]["count"] = user_pokemon[pokemon_id].get("count", 1) + 1
            else:
                # New Pokemon
                user_pokemon[pokemon_id] = {
                    "name": pokemon_data["name"],
                    "level": 1,
                    "xp": 0,
                    "caught_at": now,
                    "count": 1,
                }
            
            # If user doesn't have an active Pokemon, set this one as active
            active = await self.config.user(user).active_pokemon()
            if not active:
                await self.config.user(user).active_pokemon.set(pokemon_id)
    
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
                pokemon_data = await self.fetch_pokemon(int(active_pokemon_id))
                
                # Check if Pokemon should evolve
                if (pokemon_data and pokemon_data["evolves_to"] and 
                    pokemon_data["evolves_at_level"] and 
                    current_level + 1 >= pokemon_data["evolves_at_level"]):
                    
                    # Pokemon evolves!
                    evolution_id = str(pokemon_data["evolves_to"])
                    evolution_data = await self.fetch_pokemon(int(evolution_id))
                    
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
    
    # Commands
    
    @commands.group(name="pokemon", aliases=["poke", "p"])
    async def pokemon_commands(self, ctx: commands.Context):
        """Pokemon commands for catching and training Pokemon."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @pokemon_commands.command(name="channel")
    @commands.admin_or_permissions(manage_channels=True)
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel where Pokemon will spawn."""
        if not channel:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Pokemon will now spawn in {channel.mention}!")
    
    @pokemon_commands.command(name="catch", aliases=["c"])
    async def catch_pokemon(self, ctx: commands.Context, *, pokemon_name: str):
        """Catch a wild Pokemon that has spawned."""
        # Check if there's an active spawn
        if ctx.guild.id not in self.spawns_active:
            await ctx.send("There's no wild Pokemon to catch right now!")
            return
        
        spawn = self.spawns_active[ctx.guild.id]
        pokemon_data = spawn["pokemon"]
        
        # Check if the name matches
        if pokemon_name.lower() == pokemon_data["name"].lower():
            # Caught!
            del self.spawns_active[ctx.guild.id]
            
            # Add to user's collection
            await self.add_pokemon_to_user(ctx.author, pokemon_data)
            
            # Send success message
            embed = discord.Embed(
                title=f"{ctx.author.name} caught a {pokemon_data['name'].capitalize()}!",
                description=f"The Pokemon has been added to your collection.",
                color=0x00ff00
            )
            embed.set_thumbnail(url=pokemon_data["sprite"])
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("That's not the right Pokemon name! Try again.")
    
    @pokemon_commands.command(name="list", aliases=["l"])
    async def list_pokemon(self, ctx: commands.Context, user: discord.Member = None):
        """List all Pokemon in your collection."""
        if not user:
            user = ctx.author
        
        user_pokemon = await self.config.user(user).pokemon()
        active_pokemon_id = await self.config.user(user).active_pokemon()
        
        if not user_pokemon:
            await ctx.send(f"{user.name} doesn't have any Pokemon yet!")
            return
        
        # Sort Pokemon by ID
        sorted_pokemon = sorted(user_pokemon.items(), key=lambda x: int(x[0]))
        
        # Create embed
        embeds = []
        
        for i in range(0, len(sorted_pokemon), 10):
            chunk = sorted_pokemon[i:i+10]
            
            embed = discord.Embed(
                title=f"{user.name}'s Pokemon",
                description=f"Total: {len(user_pokemon)} Pokemon",
                color=0x3498db
            )
            
            for pokemon_id, pokemon_data in chunk:
                name = pokemon_data["name"].capitalize()
                level = pokemon_data["level"]
                count = pokemon_data.get("count", 1)
                
                # Mark active Pokemon
                if pokemon_id == active_pokemon_id:
                    name = f"**{name} (Active)**"
                
                # Add field
                embed.add_field(
                    name=f"#{pokemon_id}: {name}",
                    value=f"Level: {level}\nCount: {count}",
                    inline=True
                )
            
            embeds.append(embed)
        
        # Send paginated embeds
        if embeds:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(f"{user.name} doesn't have any Pokemon yet!")
    
    @pokemon_commands.command(name="info", aliases=["i"])
    async def pokemon_info(self, ctx: commands.Context, pokemon_id: int = None):
        """Get detailed information about a Pokemon."""
        user = ctx.author
        
        # If no Pokemon ID provided, use active Pokemon
        if pokemon_id is None:
            active_pokemon_id = await self.config.user(user).active_pokemon()
            if not active_pokemon_id:
                await ctx.send("You don't have an active Pokemon! Catch one first or specify a Pokemon ID.")
                return
            pokemon_id = int(active_pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        pokemon_id_str = str(pokemon_id)
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}! Use `!pokemon list` to see your Pokemon.")
            return
        
        # Get Pokemon data
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        user_pokemon_data = user_pokemon[pokemon_id_str]
        
        if not pokemon_data:
            await ctx.send(f"Error fetching Pokemon data for #{pokemon_id}.")
            return
        
        # Calculate XP progress
        current_level = user_pokemon_data["level"]
        current_xp = user_pokemon_data["xp"]
        xp_needed = current_level**3
        xp_percentage = int((current_xp / xp_needed) * 100) if xp_needed > 0 else 100
        
        # Create progress bar
        progress_bar_length = 20
        filled_length = int(progress_bar_length * xp_percentage / 100)
        progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
        
        # Create embed
        embed = discord.Embed(
            title=f"#{pokemon_data['id']}: {pokemon_data['name'].capitalize()}",
            color=0x3498db
        )
        
        embed.set_thumbnail(url=pokemon_data["sprite"])
        
        # Basic info
        embed.add_field(
            name="Basic Info",
            value=f"**Type**: {', '.join(t.capitalize() for t in pokemon_data['types'])}\n"
                  f"**Height**: {pokemon_data['height']/10} m\n"
                  f"**Weight**: {pokemon_data['weight']/10} kg",
            inline=False
        )
        
        # User stats
        embed.add_field(
            name="Training",
            value=f"**Level**: {current_level}\n"
                  f"**XP**: {current_xp}/{xp_needed} ({xp_percentage}%)\n"
                  f"**Progress**: {progress_bar}",
            inline=False
        )
        
        # Pokemon stats
        stats_str = ""
        for stat_name, stat_value in pokemon_data["stats"].items():
            stats_str += f"**{stat_name.capitalize()}**: {stat_value}\n"
        
        embed.add_field(
            name="Stats",
            value=stats_str,
            inline=False
        )
        
        # Evolution info
        if pokemon_data["evolves_to"] and pokemon_data["evolves_at_level"]:
            evolution_data = await self.fetch_pokemon(pokemon_data["evolves_to"])
            if evolution_data:
                embed.add_field(
                    name="Evolution",
                    value=f"Evolves into {evolution_data['name'].capitalize()} at level {pokemon_data['evolves_at_level']}",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @pokemon_commands.command(name="active", aliases=["a"])
    async def set_active(self, ctx: commands.Context, pokemon_id: int):
        """Set a Pokemon as your active Pokemon."""
        user = ctx.author
        user_pokemon = await self.config.user(user).pokemon()
        pokemon_id_str = str(pokemon_id)
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}! Use `!pokemon list` to see your Pokemon.")
            return
        
        # Set as active
        await self.config.user(user).active_pokemon.set(pokemon_id_str)
        
        pokemon_name = user_pokemon[pokemon_id_str]["name"].capitalize()
        await ctx.send(f"{pokemon_name} is now your active Pokemon!")
    
    @pokemon_commands.command(name="dex", aliases=["pokedex", "d"])
    async def pokedex(self, ctx: commands.Context, pokemon_id: int = None):
        """View Pokedex information about a Pokemon."""
        if pokemon_id is None:
            # Show user's Pokedex completion
            user_pokemon = await self.config.user(ctx.author).pokemon()
            total_caught = len(user_pokemon)
            
            embed = discord.Embed(
                title=f"{ctx.author.name}'s Pokedex",
                description=f"You've caught {total_caught}/898 Pokemon ({total_caught/8.98:.1f}%)",
                color=0xff0000
            )
            
            await ctx.send(embed=embed)
            return
        
        # Show specific Pokemon info
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        
        if not pokemon_data:
            await ctx.send(f"Pokemon #{pokemon_id} not found.")
            return
        
        # Check if user has caught this Pokemon
        user_pokemon = await self.config.user(ctx.author).pokemon()
        has_caught = str(pokemon_id) in user_pokemon
        
        # Create embed
        embed = discord.Embed(
            title=f"#{pokemon_data['id']}: {pokemon_data['name'].capitalize()}",
            color=0xff0000
        )
        
        embed.set_thumbnail(url=pokemon_data["sprite"])
        
        # Basic info
        embed.add_field(
            name="Basic Info",
            value=f"**Type**: {', '.join(t.capitalize() for t in pokemon_data['types'])}\n"
                  f"**Height**: {pokemon_data['height']/10} m\n"
                  f"**Weight**: {pokemon_data['weight']/10} kg",
            inline=False
        )
        
        # Pokemon stats
        stats_str = ""
        for stat_name, stat_value in pokemon_data["stats"].items():
            stats_str += f"**{stat_name.capitalize()}**: {stat_value}\n"
        
        embed.add_field(
            name="Stats",
            value=stats_str,
            inline=False
        )
        
        # Caught status
        embed.add_field(
            name="Caught Status",
            value="✅ Caught" if has_caught else "❌ Not caught",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Event listeners
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages for Pokemon spawning and XP."""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        # XP for active Pokemon
        if message.author.id != self.bot.user.id:
            await self.award_xp(message.author)
        
        # Check if this is a Pokemon channel
        guild_config = await self.config.guild(message.guild).all()
        if not guild_config["channel"] or message.channel.id != guild_config["channel"]:
            return
        
        # Get guild lock
        if message.guild.id not in self.pokemon_locks:
            self.pokemon_locks[message.guild.id] = asyncio.Lock()
        
        # Prevent race conditions
        async with self.pokemon_locks[message.guild.id]:
            # Check if a Pokemon is already active
            if message.guild.id in self.spawns_active:
                return
                
            # Random chance to spawn a Pokemon
            if random.random() < guild_config["spawn_chance"]:
                await self.spawn_pokemon(message.guild)
