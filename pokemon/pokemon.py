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
            "team": [],  # List of Pokemon IDs in the user's team
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
    
    @pokemon_commands.group(name="settings", aliases=["set"])
    @commands.admin_or_permissions(manage_channels=True)
    async def pokemon_settings(self, ctx: commands.Context):
        """Configure Pokemon cog settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            
    @pokemon_settings.command(name="channel")
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Set the channel where Pokemon will spawn."""
        if not channel:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(f"Pokemon will now spawn in {channel.mention}!")
        
    @pokemon_settings.command(name="spawnrate")
    async def set_spawn_rate(self, ctx: commands.Context, rate: float):
        """Set the spawn rate (0.01 to 0.5, default is 0.1)."""
        if rate < 0.01 or rate > 0.5:
            await ctx.send("Spawn rate must be between 0.01 (1%) and 0.5 (50%).")
            return
            
        await self.config.guild(ctx.guild).spawn_chance.set(rate)
        percentage = rate * 100
        await ctx.send(f"Pokemon spawn rate set to {percentage:.1f}%.")
        
    @pokemon_settings.command(name="cooldown")
    async def set_cooldown(self, ctx: commands.Context, seconds: int):
        """Set the spawn cooldown in seconds (10 to 300, default is 60)."""
        if seconds < 10 or seconds > 300:
            await ctx.send("Cooldown must be between 10 and 300 seconds.")
            return
            
        await self.config.guild(ctx.guild).spawn_cooldown.set(seconds)
        await ctx.send(f"Pokemon spawn cooldown set to {seconds} seconds.")
        
    @pokemon_settings.command(name="show")
    async def show_settings(self, ctx: commands.Context):
        """Show current Pokemon settings."""
        guild_config = await self.config.guild(ctx.guild).all()
        
        # Get channel mention if it exists
        channel_id = guild_config["channel"]
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        channel_mention = channel.mention if channel else "Not set"
        
        # Create embed
        embed = discord.Embed(
            title=f"Pokemon Settings for {ctx.guild.name}",
            color=0x3498db
        )
        
        embed.add_field(
            name="Spawn Channel",
            value=channel_mention,
            inline=False
        )
        
        embed.add_field(
            name="Spawn Rate",
            value=f"{guild_config['spawn_chance'] * 100:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Spawn Cooldown",
            value=f"{guild_config['spawn_cooldown']} seconds",
            inline=True
        )
        
        await ctx.send(embed=embed)
        
    @pokemon_settings.command(name="reset")
    async def reset_settings(self, ctx: commands.Context):
        """Reset all Pokemon settings to default."""
        # Ask for confirmation
        confirm_msg = await ctx.send("Are you sure you want to reset all Pokemon settings to default? React with ✅ to confirm.")
        await confirm_msg.add_reaction("✅")
        
        try:
            def check(reaction, reactor):
                return (
                    reaction.message.id == confirm_msg.id
                    and reactor == ctx.author
                    and str(reaction.emoji) == "✅"
                )
                
            # Wait for confirmation (15 second timeout)
            await self.bot.wait_for("reaction_add", check=check, timeout=15)
            
            # Reset settings
            await self.config.guild(ctx.guild).channel.set(None)
            await self.config.guild(ctx.guild).spawn_chance.set(SPAWN_CHANCE)
            await self.config.guild(ctx.guild).spawn_cooldown.set(MIN_SPAWN_COOLDOWN)
            
            await ctx.send("Pokemon settings have been reset to default values.")
        except asyncio.TimeoutError:
            await ctx.send("Reset settings confirmation timed out. No changes were made.")
            
            
    @pokemon_settings.command(name="clear_cache")
    @commands.is_owner()
    async def clear_cache(self, ctx: commands.Context):
        """Clear the Pokemon data cache (bot owner only)."""
        await self.config.pokemon_cache.clear()
        await ctx.send("Pokemon data cache has been cleared.")
        
    @pokemon_commands.group(name="team")
    async def pokemon_team(self, ctx: commands.Context):
        """Manage your Pokemon team."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            
    @pokemon_team.command(name="add")
    async def team_add(self, ctx: commands.Context, pokemon_id: int):
        """Add a Pokemon to your team."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
            
        # Get user's team
        async with self.config.user(user).team() as team:
            # Initialize team if not already
            if team is None:
                team = []
                
            # Check if team is full
            if len(team) >= 6:
                await ctx.send("Your team is already full! Remove a Pokemon first.")
                return
                
            # Check if Pokemon is already in team
            if pokemon_id_str in team:
                await ctx.send(f"Pokemon #{pokemon_id} is already in your team!")
                return
                
            # Add to team
            team.append(pokemon_id_str)
            
            # Get Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            pokemon_name = pokemon_data["name"].capitalize() if pokemon_data else f"Pokemon #{pokemon_id}"
            
            await ctx.send(f"{pokemon_name} has been added to your team!")
            
    @pokemon_team.command(name="remove")
    async def team_remove(self, ctx: commands.Context, pokemon_id: int):
        """Remove a Pokemon from your team."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Get user's team
        async with self.config.user(user).team() as team:
            # Initialize team if not already
            if team is None:
                team = []
                await ctx.send("You don't have a team set up yet!")
                return
                
            # Check if Pokemon is in team
            if pokemon_id_str not in team:
                await ctx.send(f"Pokemon #{pokemon_id} is not in your team!")
                return
                
            # Remove from team
            team.remove(pokemon_id_str)
            
            # Get Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            pokemon_name = pokemon_data["name"].capitalize() if pokemon_data else f"Pokemon #{pokemon_id}"
            
            await ctx.send(f"{pokemon_name} has been removed from your team!")
            
    @pokemon_team.command(name="view")
    async def team_view(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's Pokemon team."""
        if user is None:
            user = ctx.author
            
        # Get user's team
        team = await self.config.user(user).team()
        
        if not team:
            await ctx.send(f"{user.name} doesn't have a team set up yet!")
            return
            
        # Get Pokemon data for each team member
        team_data = []
        for pokemon_id in team:
            pokemon_data = await self.fetch_pokemon(int(pokemon_id))
            if pokemon_data:
                # Get user's Pokemon level and nickname
                user_pokemon = await self.config.user(user).pokemon()
                level = user_pokemon.get(pokemon_id, {}).get("level", 1)
                nickname = user_pokemon.get(pokemon_id, {}).get("nickname", None)
                
                team_data.append({
                    "id": pokemon_id,
                    "name": pokemon_data["name"],
                    "sprite": pokemon_data["sprite"],
                    "types": pokemon_data["types"],
                    "level": level,
                    "nickname": nickname
                })
                
        # Create embed
        embed = discord.Embed(
            title=f"{user.name}'s Pokemon Team",
            color=0xff5500
        )
        
        # Add each Pokemon to the embed
        for pokemon in team_data:
            name = pokemon["nickname"] or pokemon["name"].capitalize()
            if pokemon["nickname"]:
                name += f" ({pokemon['name'].capitalize()})"
                
            embed.add_field(
                name=f"#{pokemon['id']}: {name}",
                value=f"Level: {pokemon['level']}\nType: {', '.join(t.capitalize() for t in pokemon['types'])}",
                inline=True
            )
            
        await ctx.send(embed=embed)
        
    @pokemon_commands.command(name="stats")
    async def pokemon_stats(self, ctx: commands.Context, user: discord.Member = None):
        """View Pokemon trainer statistics."""
        if user is None:
            user = ctx.author
            
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        
        if not user_pokemon:
            await ctx.send(f"{user.name} hasn't caught any Pokemon yet!")
            return
            
        # Calculate stats
        total_pokemon = len(user_pokemon)
        total_levels = sum(p["level"] for p in user_pokemon.values())
        avg_level = total_levels / total_pokemon if total_pokemon > 0 else 0
        highest_level = max((p["level"] for p in user_pokemon.values()), default=0)
        
        # Get high level Pokemon
        high_level_pokemon = []
        for pokemon_id, pokemon_data in user_pokemon.items():
            if pokemon_data["level"] >= 50:  # Arbitrary threshold
                pokemon_info = await self.fetch_pokemon(int(pokemon_id))
                if pokemon_info:
                    high_level_pokemon.append({
                        "id": pokemon_id,
                        "name": pokemon_info["name"],
                        "level": pokemon_data["level"]
                    })
                    
        # Sort by level
        high_level_pokemon.sort(key=lambda p: p["level"], reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title=f"{user.name}'s Trainer Stats",
            color=0xffcc00
        )
        
        embed.add_field(
            name="Pokemon Collection",
            value=f"Total Pokemon: {total_pokemon}\nUnique Species: {len(set(p['name'] for p in user_pokemon.values()))}",
            inline=True
        )
        
        embed.add_field(
            name="Training Stats",
            value=f"Total Levels: {total_levels}\nAverage Level: {avg_level:.1f}\nHighest Level: {highest_level}",
            inline=True
        )
        
        # Add high level Pokemon
        if high_level_pokemon:
            high_level_str = "\n".join(f"Lv{p['level']} {p['name'].capitalize()}" for p in high_level_pokemon[:5])
            if len(high_level_pokemon) > 5:
                high_level_str += f"\n...and {len(high_level_pokemon) - 5} more"
                
            embed.add_field(
                name="High Level Pokemon",
                value=high_level_str,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @pokemon_commands.command(name="battle")
    async def pokemon_battle(self, ctx: commands.Context, opponent: discord.Member):
        """Challenge another trainer to a Pokemon battle."""
        if opponent.bot:
            await ctx.send("You can't battle against bots!")
            return
            
        if opponent == ctx.author:
            await ctx.send("You can't battle against yourself!")
            return
            
        # Check if both users have active Pokemon
        user_active_id = await self.config.user(ctx.author).active_pokemon()
        opponent_active_id = await self.config.user(opponent).active_pokemon()
        
        if not user_active_id:
            await ctx.send("You don't have an active Pokemon! Set one with `!pokemon active <id>`.")
            return
            
        if not opponent_active_id:
            await ctx.send(f"{opponent.name} doesn't have an active Pokemon!")
            return
            
        # Get Pokemon data
        user_pokemon = await self.config.user(ctx.author).pokemon()
        opponent_pokemon = await self.config.user(opponent).pokemon()
        
        if user_active_id not in user_pokemon:
            await ctx.send("Error: Your active Pokemon data is missing.")
            return
            
        if opponent_active_id not in opponent_pokemon:
            await ctx.send(f"Error: {opponent.name}'s active Pokemon data is missing.")
            return
            
        # Get Pokemon info
        user_pokemon_data = user_pokemon[user_active_id]
        opponent_pokemon_data = opponent_pokemon[opponent_active_id]
        
        user_pokemon_api = await self.fetch_pokemon(int(user_active_id))
        opponent_pokemon_api = await self.fetch_pokemon(int(opponent_active_id))
        
        if not user_pokemon_api or not opponent_pokemon_api:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Create battle request
        battle_msg = await ctx.send(
            f"{opponent.mention}, {ctx.author.name} is challenging you to a Pokemon battle!\n"
            f"{ctx.author.name}'s {user_pokemon_api['name'].capitalize()} (Lv. {user_pokemon_data['level']}) "
            f"vs. your {opponent_pokemon_api['name'].capitalize()} (Lv. {opponent_pokemon_data['level']}).\n"
            f"React with ✅ to accept or ❌ to decline."
        )
        
        await battle_msg.add_reaction("✅")
        await battle_msg.add_reaction("❌")
        
        # Wait for response
        try:
            def check(reaction, user):
                return (
                    user == opponent
                    and reaction.message.id == battle_msg.id
                    and str(reaction.emoji) in ["✅", "❌"]
                )
                
            reaction, user = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            
            if str(reaction.emoji) == "❌":
                await ctx.send(f"{opponent.name} declined the battle challenge.")
                return
                
            # Battle accepted, let's start!
            await ctx.send(f"Battle between {ctx.author.name} and {opponent.name} is starting!")
            
            # Simplified battle mechanics
            # Calculate battle power
            user_power = (
                user_pokemon_data["level"] * 10 +
                user_pokemon_api["stats"].get("attack", 50) +
                user_pokemon_api["stats"].get("defense", 50) +
                user_pokemon_api["stats"].get("speed", 50)
            )
            
            opponent_power = (
                opponent_pokemon_data["level"] * 10 +
                opponent_pokemon_api["stats"].get("attack", 50) +
                opponent_pokemon_api["stats"].get("defense", 50) +
                opponent_pokemon_api["stats"].get("speed", 50)
            )
            
            # Add randomness (80-120% of power)
            user_power = int(user_power * random.uniform(0.8, 1.2))
            opponent_power = int(opponent_power * random.uniform(0.8, 1.2))
            
            # Create battle embed
            embed = discord.Embed(
                title="Pokemon Battle",
                description=f"{ctx.author.name} vs. {opponent.name}",
                color=0xff0000
            )
            
            embed.add_field(
                name=f"{ctx.author.name}'s Pokemon",
                value=f"{user_pokemon_api['name'].capitalize()} (Lv. {user_pokemon_data['level']})\n"
                      f"HP: {'█' * 10}\nPower: {user_power}",
                inline=True
            )
            
            embed.add_field(
                name=f"{opponent.name}'s Pokemon",
                value=f"{opponent_pokemon_api['name'].capitalize()} (Lv. {opponent_pokemon_data['level']})\n"
                      f"HP: {'█' * 10}\nPower: {opponent_power}",
                inline=True
            )
            
            battle_status = await ctx.send(embed=embed)
            
            # Simulate battle with a delay
            await asyncio.sleep(2)
            
            # Determine winner
            if user_power > opponent_power:
                winner = ctx.author
                winner_pokemon = user_pokemon_api['name'].capitalize()
                loser = opponent
                loser_pokemon = opponent_pokemon_api['name'].capitalize()
                xp_gain = 5 + opponent_pokemon_data["level"] // 2
                winner_id = user_active_id
            else:
                winner = opponent
                winner_pokemon = opponent_pokemon_api['name'].capitalize()
                loser = ctx.author
                loser_pokemon = user_pokemon_api['name'].capitalize()
                xp_gain = 5 + user_pokemon_data["level"] // 2
                winner_id = opponent_active_id
                
            # Update battle result embed
            result_embed = discord.Embed(
                title="Battle Result",
                description=f"{winner.name}'s {winner_pokemon} defeated {loser.name}'s {loser_pokemon}!",
                color=0x00ff00
            )
            
            result_embed.add_field(
                name="Rewards",
                value=f"{winner.name}'s {winner_pokemon} gained {xp_gain} XP!",
                inline=False
            )
            
            await battle_status.edit(embed=result_embed)
            
            # Award XP to winner
            async with self.config.user(winner).pokemon() as winner_pokemon_dict:
                if winner_id in winner_pokemon_dict:
                    winner_pokemon_dict[winner_id]["xp"] += xp_gain
                    
            # Award small consolation XP to loser
            async with self.config.user(loser).pokemon() as loser_pokemon_dict:
                if loser == ctx.author and user_active_id in loser_pokemon_dict:
                    loser_pokemon_dict[user_active_id]["xp"] += 1
                elif loser == opponent and opponent_active_id in loser_pokemon_dict:
                    loser_pokemon_dict[opponent_active_id]["xp"] += 1
                    
        except asyncio.TimeoutError:
            await ctx.send(f"{opponent.name} did not respond to the battle challenge.")
            
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize guild data when the bot joins a new guild."""
        # Create a lock for this guild
        if guild.id not in self.pokemon_locks:
            self.pokemon_locks[guild.id] = asyncio.Lock()
            
        # Send welcome message to the system channel if available
        if guild.system_channel:
            embed = discord.Embed(
                title="Pokemon Bot has joined the server!",
                description="Thanks for adding the Pokemon bot to your server! Here's how to get started:",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Set up a spawn channel",
                value="Use `!pokemon settings channel #channel-name` to set where Pokemon will spawn.",
                inline=False
            )
            
            embed.add_field(
                name="Catch Pokemon",
                value="When a Pokemon appears, use `!catch <pokemon-name>` to catch it!",
                inline=False
            )
            
            embed.add_field(
                name="Help and Commands",
                value="Use `!help pokemon` to see all available commands.",
                inline=False
            )
            
            await guild.system_channel.send(embed=embed)
            
    @pokemon_settings.command(name="force_spawn")
    @commands.admin_or_permissions(administrator=True)
    async def force_spawn(self, ctx: commands.Context, pokemon_id: int = None):
        """Force a Pokemon to spawn (admin only)."""
        guild = ctx.guild
        guild_config = await self.config.guild(guild).all()
        
        # Check if channel is set
        if not guild_config["channel"]:
            await ctx.send("No spawn channel set! Use `!pokemon settings channel` first.")
            return
            
        channel = guild.get_channel(guild_config["channel"])
        if not channel:
            await ctx.send("Spawn channel no longer exists! Please set a new one.")
            return
            
        # Check if a Pokemon is already active
        if guild.id in self.spawns_active:
            await ctx.send("A Pokemon is already active! Wait for it to be caught or flee.")
            return
            
        # Generate Pokemon data
        if pokemon_id is None:
            # Random Pokemon
            pokemon_id = random.randint(1, 898)
            
        # Fetch Pokemon data
        pokemon_data = await self.fetch
    
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
    
    @pokemon_commands.command(name="trade")
    async def trade_pokemon(self, ctx: commands.Context, user: discord.Member, your_pokemon_id: int, their_pokemon_id: int):
        """Trade Pokemon with another user."""
        if user.bot:
            await ctx.send("You can't trade with bots!")
            return
            
        if user == ctx.author:
            await ctx.send("You can't trade with yourself!")
            return
            
        # Check if you have the Pokemon
        your_pokemon = await self.config.user(ctx.author).pokemon()
        your_pokemon_id_str = str(your_pokemon_id)
        
        if your_pokemon_id_str not in your_pokemon:
            await ctx.send(f"You don't have Pokemon #{your_pokemon_id}!")
            return
            
        # Check if they have the Pokemon
        their_pokemon = await self.config.user(user).pokemon()
        their_pokemon_id_str = str(their_pokemon_id)
        
        if their_pokemon_id_str not in their_pokemon:
            await ctx.send(f"{user.name} doesn't have Pokemon #{their_pokemon_id}!")
            return
            
        # Get Pokemon data
        your_pokemon_data = await self.fetch_pokemon(your_pokemon_id)
        their_pokemon_data = await self.fetch_pokemon(their_pokemon_id)
        
        if not your_pokemon_data or not their_pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Ask for confirmation from both users
        your_confirm_msg = await ctx.send(
            f"{ctx.author.mention}, do you confirm trading your {your_pokemon_data['name'].capitalize()} "
            f"for {user.name}'s {their_pokemon_data['name'].capitalize()}? React with ✅ to confirm."
        )
        await your_confirm_msg.add_reaction("✅")
        
        their_confirm_msg = await ctx.send(
            f"{user.mention}, do you confirm trading your {their_pokemon_data['name'].capitalize()} "
            f"for {ctx.author.name}'s {your_pokemon_data['name'].capitalize()}? React with ✅ to confirm."
        )
        await their_confirm_msg.add_reaction("✅")
        
        # Check reactions
        try:
            def check_your_reaction(reaction, reactor):
                return (
                    reaction.message.id == your_confirm_msg.id
                    and reactor == ctx.author
                    and str(reaction.emoji) == "✅"
                )
                
            def check_their_reaction(reaction, reactor):
                return (
                    reaction.message.id == their_confirm_msg.id
                    and reactor == user
                    and str(reaction.emoji) == "✅"
                )
                
            # Wait for both reactions (30 second timeout)
            tasks = [
                asyncio.create_task(self.bot.wait_for("reaction_add", check=check_your_reaction, timeout=30)),
                asyncio.create_task(self.bot.wait_for("reaction_add", check=check_their_reaction, timeout=30))
            ]
            
            # Wait for both reactions
            done, pending = await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                
            # Check if both reactions were received
            if len(done) < 2:
                await ctx.send("Trade cancelled due to timeout.")
                return
                
            # Execute the trade
            async with self.config.user(ctx.author).pokemon() as your_pokemon_dict:
                your_pokemon_data = your_pokemon_dict[your_pokemon_id_str]
                del your_pokemon_dict[your_pokemon_id_str]
                
            async with self.config.user(user).pokemon() as their_pokemon_dict:
                their_pokemon_data = their_pokemon_dict[their_pokemon_id_str]
                del their_pokemon_dict[their_pokemon_id_str]
                
            # Add the traded Pokemon
            async with self.config.user(ctx.author).pokemon() as your_pokemon_dict:
                your_pokemon_dict[their_pokemon_id_str] = their_pokemon_data
                
            async with self.config.user(user).pokemon() as their_pokemon_dict:
                their_pokemon_dict[your_pokemon_id_str] = your_pokemon_data
                
            # Check if active Pokemon was traded
            if await self.config.user(ctx.author).active_pokemon() == your_pokemon_id_str:
                await self.config.user(ctx.author).active_pokemon.set(their_pokemon_id_str)
                
            if await self.config.user(user).active_pokemon() == their_pokemon_id_str:
                await self.config.user(user).active_pokemon.set(your_pokemon_id_str)
                
            # Send confirmation
            embed = discord.Embed(
                title="Trade Completed!",
                description=f"{ctx.author.name} traded {your_pokemon_data['name'].capitalize()} for {user.name}'s {their_pokemon_data['name'].capitalize()}!",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("Trade cancelled due to timeout.")
            
    @pokemon_commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context):
        """Show the Pokemon trainer leaderboard."""
        guild = ctx.guild
        
        # Get all users in the guild
        all_users = {}
        async for user_id, user_data in self.config.all_users():
            member = guild.get_member(user_id)
            if member and "pokemon" in user_data:
                # Count total Pokemon and calculate trainer score
                pokemon_count = len(user_data["pokemon"])
                
                # Calculate total levels
                total_levels = 0
                for pokemon_data in user_data["pokemon"].values():
                    total_levels += pokemon_data["level"]
                    
                # Calculate trainer score (Pokemon count + total levels)
                trainer_score = pokemon_count + total_levels
                
                all_users[member] = {
                    "pokemon_count": pokemon_count,
                    "total_levels": total_levels,
                    "trainer_score": trainer_score
                }
                
        # Sort by trainer score
        sorted_users = sorted(all_users.items(), key=lambda x: x[1]["trainer_score"], reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title=f"Pokemon Trainer Leaderboard - {guild.name}",
            color=0xffcc00
        )
        
        # Add fields for top 10 users
        for i, (user, data) in enumerate(sorted_users[:10], 1):
            embed.add_field(
                name=f"{i}. {user.name}",
                value=f"Pokemon: {data['pokemon_count']}\n"
                      f"Total Levels: {data['total_levels']}\n"
                      f"Trainer Score: {data['trainer_score']}",
                inline=(i % 2 != 0)  # Alternate inline
            )
            
        await ctx.send(embed=embed)
        
    @pokemon_commands.command(name="release")
    async def release_pokemon(self, ctx: commands.Context, pokemon_id: int):
        """Release a Pokemon from your collection."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        async with self.config.user(user).pokemon() as user_pokemon:
            if pokemon_id_str not in user_pokemon:
                await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
                return
                
            # Get Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            if not pokemon_data:
                await ctx.send("Error fetching Pokemon data. Please try again.")
                return
                
            pokemon_name = pokemon_data["name"].capitalize()
            
            # Check if it's the active Pokemon
            active_pokemon = await self.config.user(user).active_pokemon()
            if active_pokemon == pokemon_id_str:
                await ctx.send(f"You can't release your active Pokemon! Set another Pokemon as active first.")
                return
                
            # Ask for confirmation
            confirm_msg = await ctx.send(f"Are you sure you want to release your {pokemon_name}? This action cannot be undone. React with ✅ to confirm.")
            await confirm_msg.add_reaction("✅")
            
            try:
                def check(reaction, reactor):
                    return reaction.message.id == confirm_msg.id and reactor == user and str(reaction.emoji) == "✅"
                    
                # Wait for confirmation (15 second timeout)
                await self.bot.wait_for("reaction_add", check=check, timeout=15)
                
                # If user has multiple of this Pokemon, reduce count
                if user_pokemon[pokemon_id_str].get("count", 1) > 1:
                    user_pokemon[pokemon_id_str]["count"] -= 1
                    await ctx.send(f"You released one of your {pokemon_name}s. You still have {user_pokemon[pokemon_id_str]['count']} remaining.")
                else:
                    # Remove the Pokemon
                    del user_pokemon[pokemon_id_str]
                    await ctx.send(f"You released your {pokemon_name}. Farewell, {pokemon_name}!")
                    
            except asyncio.TimeoutError:
                await ctx.send("Release cancelled.")
        
    @pokemon_commands.command(name="gift")
    async def gift_pokemon(self, ctx: commands.Context, user: discord.Member, pokemon_id: int):
        """Gift a Pokemon to another user."""
        if user.bot:
            await ctx.send("You can't gift Pokemon to bots!")
            return
            
        if user == ctx.author:
            await ctx.send("You can't gift Pokemon to yourself!")
            return
            
        # Check if you have the Pokemon
        async with self.config.user(ctx.author).pokemon() as your_pokemon:
            pokemon_id_str = str(pokemon_id)
            
            if pokemon_id_str not in your_pokemon:
                await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
                return
                
            # Get Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            if not pokemon_data:
                await ctx.send("Error fetching Pokemon data. Please try again.")
                return
                
            pokemon_name = pokemon_data["name"].capitalize()
            
            # Check if it's the active Pokemon
            active_pokemon = await self.config.user(ctx.author).active_pokemon()
            if active_pokemon == pokemon_id_str:
                await ctx.send(f"You can't gift your active Pokemon! Set another Pokemon as active first.")
                return
                
            # Ask for confirmation
            confirm_msg = await ctx.send(f"Are you sure you want to gift your {pokemon_name} to {user.name}? This action cannot be undone. React with ✅ to confirm.")
            await confirm_msg.add_reaction("✅")
            
            try:
                def check(reaction, reactor):
                    return reaction.message.id == confirm_msg.id and reactor == ctx.author and str(reaction.emoji) == "✅"
                    
                # Wait for confirmation (15 second timeout)
                await self.bot.wait_for("reaction_add", check=check, timeout=15)
                
                # If user has multiple of this Pokemon, reduce count
                if your_pokemon[pokemon_id_str].get("count", 1) > 1:
                    your_pokemon[pokemon_id_str]["count"] -= 1
                    pokemon_to_gift = dict(your_pokemon[pokemon_id_str])
                    pokemon_to_gift["count"] = 1
                else:
                    # Remove the Pokemon
                    pokemon_to_gift = your_pokemon[pokemon_id_str]
                    del your_pokemon[pokemon_id_str]
                    
                # Add the Pokemon to the recipient
                async with self.config.user(user).pokemon() as their_pokemon:
                    if pokemon_id_str in their_pokemon:
                        their_pokemon[pokemon_id_str]["count"] = their_pokemon[pokemon_id_str].get("count", 1) + 1
                    else:
                        their_pokemon[pokemon_id_str] = pokemon_to_gift
                        # If they don't have an active Pokemon, set this one
                        if not await self.config.user(user).active_pokemon():
                            await self.config.user(user).active_pokemon.set(pokemon_id_str)
                            
                await ctx.send(f"You gifted your {pokemon_name} to {user.name}!")
                
            except asyncio.TimeoutError:
                await ctx.send("Gift cancelled.")
    
    @pokemon_commands.command(name="rename")
    async def rename_pokemon(self, ctx: commands.Context, pokemon_id: int, *, nickname: str):
        """Give a nickname to your Pokemon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if nickname is too long
        if len(nickname) > 20:
            await ctx.send("Nickname must be 20 characters or less.")
            return
            
        async with self.config.user(user).pokemon() as user_pokemon:
            if pokemon_id_str not in user_pokemon:
                await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
                return
                
            # Get original name
            original_name = user_pokemon[pokemon_id_str]["name"]
            
            # Set nickname
            user_pokemon[pokemon_id_str]["nickname"] = nickname
            
            await ctx.send(f"Your {original_name.capitalize()} is now known as \"{nickname}\"!")
            
    @pokemon_commands.command(name="daily")
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def daily_reward(self, ctx: commands.Context):
        """Claim your daily reward."""
        user = ctx.author
        
        # Random XP bonus for active Pokemon
        xp_bonus = random.randint(10, 30)
        
        # Check if user has an active Pokemon
        active_pokemon_id = await self.config.user(user).active_pokemon()
        
        if not active_pokemon_id:
            # No active Pokemon, spawn a random one
            pokemon_id = random.randint(1, 151)  # Gen 1 Pokemon
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            
            if pokemon_data:
                await self.add_pokemon_to_user(user, pokemon_data)
                
                embed = discord.Embed(
                    title="Daily Reward!",
                    description=f"You received a {pokemon_data['name'].capitalize()}!",
                    color=0xffcc00
                )
                embed.set_thumbnail(url=pokemon_data["sprite"])
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Error fetching Pokemon data. Please try again.")
                ctx.command.reset_cooldown(ctx)
        else:
            # Give XP to active Pokemon
            async with self.config.user(user).pokemon() as user_pokemon:
                if active_pokemon_id in user_pokemon:
                    # Get Pokemon data
                    active_pokemon = user_pokemon[active_pokemon_id]
                    active_pokemon["xp"] += xp_bonus
                    
                    # Check for level up
                    current_level = active_pokemon["level"]
                    current_xp = active_pokemon["xp"]
                    xp_required = current_level**3
                    
                    if current_xp >= xp_required:
                        # Level up!
                        active_pokemon["level"] = current_level + 1
                        active_pokemon["xp"] = current_xp - xp_required
                        
                        embed = discord.Embed(
                            title="Daily Reward!",
                            description=f"Your {active_pokemon.get('nickname', active_pokemon['name'].capitalize())} gained {xp_bonus} XP and leveled up to level {current_level + 1}!",
                            color=0xffcc00
                        )
                    else:
                        embed = discord.Embed(
                            title="Daily Reward!",
                            description=f"Your {active_pokemon.get('nickname', active_pokemon['name'].capitalize())} gained {xp_bonus} XP!",
                            color=0xffcc00
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
            xp_result = await self.award_xp(message.author)
            
            # If Pokemon leveled up or evolved, notify
            if xp_result and xp_result.get("leveled_up"):
                if xp_result.get("evolved"):
                    # Pokemon evolved
                    embed = discord.Embed(
                        title="Pokemon Evolution!",
                        description=f"{message.author.mention}'s {xp_result['old_pokemon'].capitalize()} evolved into {xp_result['new_pokemon'].capitalize()}!",
                        color=0xff00ff
                    )
                    await message.channel.send(embed=embed)
                elif random.random() < 0.1:  # 10% chance to notify level ups to avoid spam
                    # Pokemon leveled up
                    await message.channel.send(
                        f"{message.author.mention}'s {xp_result['pokemon_name'].capitalize()} reached level {xp_result['new_level']}!"
                    )
        
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
