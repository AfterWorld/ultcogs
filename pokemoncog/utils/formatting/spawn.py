"""Spawn utility functions for the Pokemon cog."""
import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import discord
import aiohttp
from redbot.core import Config
from redbot.core.bot import Red

from ...constants import CATCH_TIMEOUT, MEGA_STONES, Z_CRYSTALS, PRIMAL_ORBS
# Fix the import path to look for api in the parent directory
from ..api import fetch_pokemon, get_random_pokemon_id
from ..formatters import format_pokemon_name, create_spawn_embed

log = logging.getLogger("red.pokemon")

async def spawn_pokemon(
    bot: Red,
    session: aiohttp.ClientSession,
    config: Config,
    guild: discord.Guild,
    spawns_active: Dict[int, Dict[str, Any]],
    pokemon_locks: Dict[int, asyncio.Lock]
) -> bool:
    """Attempt to spawn a Pokemon in the guild.
    
    Args:
        bot: The Red bot instance
        session: The aiohttp ClientSession for API requests
        config: The Red Config instance
        guild: The Discord guild to spawn in
        spawns_active: Dict tracking active spawns
        pokemon_locks: Dict of guild locks to prevent race conditions
        
    Returns:
        True if spawn was successful, False otherwise
    """
    # Get lock for this guild first
    if guild.id not in pokemon_locks:
        pokemon_locks[guild.id] = asyncio.Lock()
        
    async with pokemon_locks[guild.id]:
        # Get current time right away to ensure accurate timing
        now = datetime.now().timestamp()
        
        # Reload the guild config to ensure we have the latest data
        guild_config = await config.guild(guild).all()
        
        # Check if a Pokemon is already active in this guild
        if guild.id in spawns_active:
            log.debug(f"Spawn blocked: Pokemon already active in {guild.name}")
            return False
            
        channel_id = guild_config.get("channel")
        
        if not channel_id:
            log.debug(f"Spawn blocked: No channel set for {guild.name}")
            return False
                
        channel = guild.get_channel(channel_id)
        if not channel:
            log.debug(f"Spawn blocked: Channel {channel_id} no longer exists in {guild.name}")
            return False
        
        # Check cooldown with current time
        if (now - guild_config.get("last_spawn", 0)) < guild_config.get("spawn_cooldown", 60):
            log.debug(f"Spawn blocked: Cooldown not expired in {guild.name}")
            return False
        
        # Determine which Pokemon to spawn
        include_mega = guild_config.get("include_mega", False)
        include_gmax = guild_config.get("include_gmax", False)
        include_forms = guild_config.get("include_forms", False)
        
        pokemon_id, form_type = get_random_pokemon_id(
            include_mega=include_mega,
            include_gmax=include_gmax,
            include_forms=include_forms
        )
        
        # Fetch Pokemon data with form if needed
        pokemon_data = await fetch_pokemon(session, config, pokemon_id, form_type)
        
        if not pokemon_data:
            log.error(f"Failed to fetch data for Pokemon ID {pokemon_id}")
            return False
        
        # Resolve the bot's prefix to a string
        if callable(bot.command_prefix):
            try:
                # If command_prefix is callable, get the actual prefix for this guild
                prefix_list = await bot.command_prefix(bot, None, guild=guild)
                # Use the first prefix if it's a list
                prefix = prefix_list[0] if isinstance(prefix_list, list) else prefix_list
            except:
                # Default fallback prefix if we can't get the actual one
                prefix = "!"
        else:
            # If it's already a string or list
            prefix = bot.command_prefix[0] if isinstance(bot.command_prefix, list) else bot.command_prefix
        
        # Create spawn embed
        embed = create_spawn_embed(prefix, pokemon_data)
        
        # Set expiry time
        expiry = now + CATCH_TIMEOUT
        
        # Store active spawn
        spawns_active[guild.id] = {
            "pokemon": pokemon_data,
            "expiry": expiry
        }
        
        # Update last spawn time
        await config.guild(guild).last_spawn.set(now)
        
        # Send spawn message
        await channel.send(embed=embed)
        
        # Set up expiry task
        bot.loop.create_task(expire_spawn(
            bot, config, guild.id, channel, expiry, spawns_active, pokemon_locks
        ))
        
        return True

async def expire_spawn(
    bot: Red,
    config: Config,
    guild_id: int,
    channel: discord.TextChannel,
    expiry: float,
    spawns_active: Dict[int, Dict[str, Any]],
    pokemon_locks: Dict[int, asyncio.Lock]
):
    """Expire a spawn after the timeout period.
    
    Args:
        bot: The Red bot instance
        config: The Red Config instance
        guild_id: The Discord guild ID
        channel: The Discord text channel
        expiry: The expiry timestamp
        spawns_active: Dict tracking active spawns
        pokemon_locks: Dict of guild locks to prevent race conditions
    """
    now = datetime.now().timestamp()
    wait_time = expiry - now
    
    if wait_time > 0:
        await asyncio.sleep(wait_time)
    
    # Get lock for this guild
    if guild_id not in pokemon_locks:
        pokemon_locks[guild_id] = asyncio.Lock()
        
    async with pokemon_locks[guild_id]:
        # Check if the spawn is still active (it might have been caught)
        if guild_id in spawns_active and spawns_active[guild_id]["expiry"] == expiry:
            pokemon_name = spawns_active[guild_id]["pokemon"]["name"].capitalize()
            
            # Format name for display (handle forms)
            display_name = format_pokemon_name(pokemon_name)
            
            # Remove the spawn
            del spawns_active[guild_id]
            
            # Send expiry message
            await channel.send(f"The wild {display_name} fled!")

async def add_pokemon_to_user(
    session: aiohttp.ClientSession,
    config: Config,
    user: discord.Member, 
    pokemon_data: Dict[str, Any]
):
    """Add a caught Pokemon to a user's collection.
    
    Args:
        session: The aiohttp ClientSession for API requests
        config: The Red Config instance
        user: The Discord member who caught the Pokemon
        pokemon_data: The Pokemon data to add
    """
    async with config.user(user).pokemon() as user_pokemon:
        pokemon_id = str(pokemon_data["id"])
        now = datetime.now().timestamp()
        
        # Check if user already has this Pokemon
        if pokemon_id in user_pokemon:
            # User already has this Pokemon, increment count
            user_pokemon[pokemon_id]["count"] = user_pokemon[pokemon_id].get("count", 1) + 1
        else:
            # New Pokemon
            # Check if this is a form
            form_type = None
            base_pokemon = pokemon_id
            
            if "-" in pokemon_data["name"]:
                base_name, form = pokemon_data["name"].split("-", 1)
                form_type = form
                if "base_pokemon" in pokemon_data:
                    base_pokemon = str(pokemon_data["base_pokemon"])
            
            user_pokemon[pokemon_id] = {
                "name": pokemon_data["name"],
                "level": 1,
                "xp": 0,
                "caught_at": now,
                "count": 1,
                "form_type": form_type,
                "base_pokemon": base_pokemon,
            }
        
        # If user doesn't have an active Pokemon, set this one as active
        active = await config.user(user).active_pokemon()
        if not active:
            await config.user(user).active_pokemon.set(pokemon_id)
            
    # Award money for catching
    catch_reward = random.randint(100, 500)
    current_money = await config.user(user).money()
    await config.user(user).money.set(current_money + catch_reward)
    
    # Random chance for a special item when catching rare Pokemon
    if random.random() < 0.05:  # 5% chance
        # Determine which item to give based on Pokemon
        special_item = None
        
        # Check if this Pokemon has a mega stone
        pokemon_id_int = pokemon_data["id"]
        # Check for simple ID match
        if pokemon_id_int in MEGA_STONES or str(pokemon_id_int) in MEGA_STONES:
            mega_stone = MEGA_STONES.get(pokemon_id_int) or MEGA_STONES.get(str(pokemon_id_int))
            if mega_stone and random.random() < 0.3:  # 30% chance if eligible
                special_item = mega_stone
        # Check for tuple match (X/Y forms)
        elif (pokemon_id_int, "X") in MEGA_STONES:
            special_item = MEGA_STONES[(pokemon_id_int, "X")]
        elif (pokemon_id_int, "Y") in MEGA_STONES:
            special_item = MEGA_STONES[(pokemon_id_int, "Y")]
        
        # Check for Z-Crystal based on type
        if not special_item and "types" in pokemon_data and pokemon_data["types"]:
            primary_type = pokemon_data["types"][0].capitalize()
            if primary_type in Z_CRYSTALS and random.random() < 0.3:
                special_item = Z_CRYSTALS[primary_type]

        # Check for Primal Orb
        if not special_item and (pokemon_id_int in PRIMAL_ORBS or str(pokemon_id_int) in PRIMAL_ORBS):
            orb = PRIMAL_ORBS.get(pokemon_id_int) or PRIMAL_ORBS.get(str(pokemon_id_int))
            if orb:
                special_item = orb

        # Award the special item if one was selected
        if special_item:
            async with config.user(user).items() as items:
                items[special_item] = items.get(special_item, 0) + 1
            
            return {
                "pokemon_id": pokemon_id,
                "money_reward": catch_reward,
                "special_item": special_item
            }
    
    return {
        "pokemon_id": pokemon_id,
        "money_reward": catch_reward
    }

def is_correct_catch(pokemon_data: Dict[str, Any], user_input: str) -> bool:
    """Check if the user's catch attempt matches the Pokemon.
    
    Args:
        pokemon_data: The Pokemon data
        user_input: The user's catch attempt input
        
    Returns:
        True if the catch is correct, False otherwise
    """
    # Normalize the input and expected names for more flexible matching
    input_name = user_input.lower().replace(" ", "").replace("-", "").replace("_", "")
    correct_name = pokemon_data["name"].lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Fix common typos and spelling mistakes
    typo_corrections = {
        "charzard": "charizard",
        "charlizard": "charizard",
        "charazard": "charizard",
        "pokeon": "pokemon",
        "pokmon": "pokemon",
        "pikacu": "pikachu",
        "pikchu": "pikachu"
    }
    
    # Apply typo correction if needed
    for typo, correction in typo_corrections.items():
        if typo in input_name:
            input_name = input_name.replace(typo, correction)
    
    # Extracted base name (without form)
    expected_base = correct_name
    if "-" in pokemon_data["name"]:
        expected_base = pokemon_data["name"].split("-")[0].lower()
    
    # Special forms handling
    is_correct = False
    
    # Direct match
    if input_name == correct_name:
        is_correct = True
    
    # Base name match (without any form)
    elif input_name == expected_base:
        is_correct = True
    
    # Try more flexible form matching
    else:
        # Handle mega evolutions with various formats
        if "mega" in pokemon_data["name"].lower():
            if (f"mega{expected_base}" in input_name or 
                f"m{expected_base}" in input_name or
                f"{expected_base}mega" in input_name):
                is_correct = True
                
            # X/Y mega forms
            if "-x" in pokemon_data["name"].lower() and ("megax" in input_name or "mega-x" in input_name or "megaevolutionx" in input_name):
                is_correct = True
            elif "-y" in pokemon_data["name"].lower() and ("megay" in input_name or "mega-y" in input_name or "megaevolutiony" in input_name):
                is_correct = True
        
        # Handle Gigantamax forms
        elif "gmax" in pokemon_data["name"].lower() or "gigantamax" in pokemon_data["name"].lower():
            if (f"gmax{expected_base}" in input_name or 
                f"gigantamax{expected_base}" in input_name or 
                f"g{expected_base}" in input_name):
                is_correct = True
        
        # Handle regional forms
        elif any(form in pokemon_data["name"].lower() for form in ["alola", "galar", "hisui"]):
            regional_forms = ["alola", "galar", "hisui"]
            for form in regional_forms:
                if form in pokemon_data["name"].lower() and (f"{form}{expected_base}" in input_name or f"{expected_base}{form}" in input_name):
                    is_correct = True
                    break
    
    return is_correct

async def spawn_legendary(
    bot: Red,
    session: aiohttp.ClientSession,
    config: Config,
    guild: discord.Guild,
    spawns_active: Dict[int, Dict[str, Any]],
    pokemon_locks: Dict[int, asyncio.Lock],
    pokemon_id: Optional[int] = None
) -> bool:
    """Spawn a legendary Pokemon in the guild.
    
    Args:
        bot: The Red bot instance
        session: The aiohttp ClientSession for API requests
        config: The Red Config instance
        guild: The Discord guild to spawn in
        spawns_active: Dict tracking active spawns
        pokemon_locks: Dict of guild locks to prevent race conditions
        pokemon_id: Optional specific legendary Pokemon ID
        
    Returns:
        True if spawn was successful, False otherwise
    """
    from ...constants import LEGENDARY_IDS
    
    # Get lock for this guild first
    if guild.id not in pokemon_locks:
        pokemon_locks[guild.id] = asyncio.Lock()
        
    async with pokemon_locks[guild.id]:
        # Get current time right away to ensure accurate timing
        now = datetime.now().timestamp()
        
        # Check if a Pokemon is already active in this guild
        if guild.id in spawns_active:
            log.debug(f"Spawn blocked: Pokemon already active in {guild.name}")
            return False
            
        guild_config = await config.guild(guild).all()
        channel_id = guild_config.get("channel")
        
        if not channel_id:
            log.debug(f"Spawn blocked: No channel set for {guild.name}")
            return False
                
        channel = guild.get_channel(channel_id)
        if not channel:
            log.debug(f"Spawn blocked: Channel {channel_id} no longer exists in {guild.name}")
            return False
        
        # Choose a random legendary if none provided
        if not pokemon_id:
            pokemon_id = random.choice(LEGENDARY_IDS)
        
        # Fetch Pokemon data
        pokemon_data = await fetch_pokemon(session, config, pokemon_id)
        
        if not pokemon_data:
            log.error(f"Failed to fetch data for legendary Pokemon ID {pokemon_id}")
            return False
        
        # Resolve the bot's prefix to a string
        if callable(bot.command_prefix):
            try:
                # If command_prefix is callable, get the actual prefix for this guild
                prefix_list = await bot.command_prefix(bot, None, guild=guild)
                # Use the first prefix if it's a list
                prefix = prefix_list[0] if isinstance(prefix_list, list) else prefix_list
            except:
                # Default fallback prefix if we can't get the actual one
                prefix = "!"
        else:
            # If it's already a string or list
            prefix = bot.command_prefix[0] if isinstance(bot.command_prefix, list) else bot.command_prefix
        
        # Create special announcement embed
        embed = discord.Embed(
            title="⚡ LEGENDARY POKEMON ALERT ⚡",
            description=f"A wild {pokemon_data['name'].capitalize()} has appeared!\nType `{prefix}p catch {pokemon_data['name']}` to catch it!",
            color=0xff0000
        )
        
        embed.set_image(url=pokemon_data["sprite"])
        
        # Set longer expiry time for legendary (2 minutes)
        expiry = now + 120  # 2 minutes
        
        # Store active spawn
        spawns_active[guild.id] = {
            "pokemon": pokemon_data,
            "expiry": expiry
        }
        
        # Update last spawn time
        await config.guild(guild).last_spawn.set(now)
        
        # Send spawn message
        await channel.send(embed=embed)
        
        # Set up expiry task
        bot.loop.create_task(expire_spawn(
            bot, config, guild.id, channel, expiry, spawns_active, pokemon_locks
        ))
        
        return True
