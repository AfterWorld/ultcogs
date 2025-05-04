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

# Special form constants
MEGA_STONE_CHANCE = 0.05  # 5% chance to get a mega stone from daily rewards
Z_CRYSTAL_CHANCE = 0.05   # 5% chance to get a Z-Crystal from daily rewards
DYNAMAX_BAND_CHANCE = 0.05  # 5% chance to get Dynamax Band
PRIMAL_ORB_CHANCE = 0.03  # 3% chance to get a Primal orb (Kyogre/Groudon)

# Special item mapping - Fixed duplicate keys by using tuples for variants
MEGA_STONES = {
    3: "Venusaurite",       # Venusaur
    (6, "X"): "Charizardite X",  # Charizard X
    (6, "Y"): "Charizardite Y",  # Charizard Y
    9: "Blastoisinite",     # Blastoise
    15: "Beedrillite",      # Beedrill
    18: "Pidgeotite",       # Pidgeot
    65: "Alakazite",        # Alakazam
    80: "Slowbronite",      # Slowbro
    94: "Gengarite",        # Gengar
    115: "Kangaskhanite",   # Kangaskhan
    127: "Pinsirite",       # Pinsir
    130: "Gyaradosite",     # Gyarados
    142: "Aerodactylite",   # Aerodactyl
    (150, "X"): "Mewtwoite X",   # Mewtwo X
    (150, "Y"): "Mewtwoite Y",   # Mewtwo Y
    181: "Ampharosite",     # Ampharos
    208: "Steelixite",      # Steelix
    212: "Scizorite",       # Scizor
    214: "Heracronite",     # Heracross
    229: "Houndoominite",   # Houndoom
    248: "Tyranitarite",    # Tyranitar
    254: "Sceptilite",      # Sceptile
    257: "Blazikenite",     # Blaziken
    260: "Swampertite",     # Swampert
    282: "Gardevoirite",    # Gardevoir
    302: "Sablenite",       # Sableye
    303: "Mawilite",        # Mawile
    306: "Aggronite",       # Aggron
    308: "Medichamite",     # Medicham
    310: "Manectite",       # Manectric
    319: "Sharpedonite",    # Sharpedo
    323: "Cameruptite",     # Camerupt
    334: "Altarianite",     # Altaria
    354: "Banettite",       # Banette
    359: "Absolite",        # Absol
    362: "Glalitite",       # Glalie
    373: "Salamencite",     # Salamence
    376: "Metagrossite",    # Metagross
    380: "Latiasite",       # Latias
    381: "Latiosite",       # Latios
    384: "Red Orb",         # Groudon (Primal Reversion)
    382: "Blue Orb",        # Kyogre (Primal Reversion)
    428: "Lopunnite",       # Lopunny
    445: "Garchompite",     # Garchomp
    448: "Lucarionite",     # Lucario
    460: "Abomasite",       # Abomasnow
    475: "Galladite",       # Gallade
    531: "Audinite",        # Audino
    719: "Diancite",        # Diancie
}

# Z-Crystal mapping
Z_CRYSTALS = {
    # Type-specific Z-Crystals
    "Normal": "Normalium Z",
    "Fire": "Firium Z",
    "Water": "Waterium Z",
    "Grass": "Grassium Z",
    "Electric": "Electrium Z",
    "Ice": "Icium Z",
    "Fighting": "Fightinium Z",
    "Poison": "Poisonium Z",
    "Ground": "Groundium Z",
    "Flying": "Flyinium Z",
    "Psychic": "Psychium Z",
    "Bug": "Buginium Z",
    "Rock": "Rockium Z",
    "Ghost": "Ghostium Z",
    "Dragon": "Dragonium Z",
    "Dark": "Darkinium Z",
    "Steel": "Steelium Z",
    "Fairy": "Fairium Z",
    
    # Special Z-Crystals (Pokémon-specific)
    25: "Pikanium Z",        # Pikachu (Catastropika)
    26: "Aloraichium Z",     # Alolan Raichu (Stoked Sparksurfer)
    38: "Tapunium Z",        # Tapu Koko/Lele/Bulu/Fini (Guardian of Alola)
    53: "Eevium Z",          # Eevee (Extreme Evoboost)
    103: "Decidium Z",       # Decidueye (Sinister Arrow Raid)
    105: "Incinium Z",       # Incineroar (Malicious Moonsault)
    107: "Primarium Z",      # Primarina (Oceanic Operetta)
    150: "Mewnium Z",        # Mewtwo (Genesis Supernova)
    151: "Pikashunium Z",    # Pikachu with cap (10,000,000 Volt Thunderbolt)
    249: "Lunalium Z",       # Lunala (Menacing Moonraze Maelstrom)
    250: "Solganium Z",      # Solgaleo (Searing Sunraze Smash)
    254: "Marshadium Z",     # Marshadow (Soul-Stealing 7-Star Strike)
    302: "Kommonium Z",      # Kommo-o (Clangorous Soulblaze)
    658: "Lycanium Z",       # Lycanroc (Splintered Stormshards)
    791: "Mimikium Z",       # Mimikyu (Let's Snuggle Forever)
    800: "Ultranecrozium Z", # Necrozma (Light That Burns the Sky/Photon Geyser)
}

# Primal Orbs
PRIMAL_ORBS = {
    383: "Red Orb",      # Groudon
    382: "Blue Orb",     # Kyogre
}

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
        
        # Start background task
        self.bg_task = self.bot.loop.create_task(self.initialize())
    
    async def initialize(self):
        """Initialize the cog by loading cached data."""
        await self.bot.wait_until_ready()
        try:
            pass  # Add your code logic here
        except Exception as e:
            log.error(f"An error occurred: {e}")
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
    
    async def fetch_pokemon(self, pokemon_id: int, form_key: str = None) -> dict:
        """Fetch Pokemon data from PokeAPI with support for alternate forms.
        
        Args:
            pokemon_id: Base Pokemon ID
            form_key: Optional form identifier (e.g., 'mega', 'mega-x', 'alola', 'galar', 'gmax')
        """
        # Check cache first
        pokemon_cache = await self.config.pokemon_cache()
        form_cache = await self.config.form_cache()
        
        str_id = str(pokemon_id)
        cache_key = f"{str_id}-{form_key}" if form_key else str_id
        
        # Check if form exists in cache
        if cache_key in form_cache:
            return form_cache[cache_key]
        
        # Check if base Pokemon exists in cache
        if str_id in pokemon_cache and not form_key:
            return pokemon_cache[str_id]
        
        # If not in cache, fetch from API
        try:
            # Fetch base Pokemon data first
            async with self.session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}") as response:
                if response.status == 200:
                    base_data = await response.json()
                    
                    # Also get species data for evolution details
                    async with self.session.get(base_data["species"]["url"]) as species_response:
                        if species_response.status == 200:
                            species_data = await species_response.json()
                        else:
                            species_data = {}
                    
                    # Extract only needed info to reduce cache size
                    pokemon_info = {
                        "id": base_data["id"],
                        "name": base_data["name"],
                        "types": [t["type"]["name"] for t in base_data["types"]],
                        "height": base_data["height"],
                        "weight": base_data["weight"],
                        "sprite": base_data["sprites"]["front_default"],
                        "base_experience": base_data["base_experience"],
                        "stats": {s["stat"]["name"]: s["base_stat"] for s in base_data["stats"]},
                        "evolution_chain_url": species_data.get("evolution_chain", {}).get("url", None),
                        "evolves_at_level": None,  # Will be populated if this Pokemon evolves
                        "evolves_to": None,  # Will be populated if this Pokemon evolves
                        "forms": [],  # List of available forms
                        "mega_evolution": False,  # Whether this Pokemon can Mega Evolve
                        "primal_reversion": False,  # Whether this Pokemon has a Primal form
                        "gigantamax": False,  # Whether this Pokemon can Gigantamax
                        "form_details": {},  # Details for alternate forms
                    }
                    
                    # Get forms data if available
                    if base_data.get("forms", []):
                        for form in base_data["forms"]:
                            if form["name"] != base_data["name"]:  # Skip the default form
                                pokemon_info["forms"].append(form["name"])
                    
                    # Check for varieties in species data (mega, regional forms, etc.)
                    if species_data.get("varieties", []):
                        for variety in species_data["varieties"]:
                            if not variety["is_default"]:
                                variety_name = variety["pokemon"]["name"]
                                pokemon_info["forms"].append(variety_name)
                                
                                # Check if this is a mega evolution or other special form
                                if "mega" in variety_name:
                                    pokemon_info["mega_evolution"] = True
                                elif "primal" in variety_name:
                                    pokemon_info["primal_reversion"] = True
                                elif "gmax" in variety_name or "gigantamax" in variety_name:
                                    pokemon_info["gigantamax"] = True
                    
                    # Fetch data for each form if requested
                    if form_key and (form_key in pokemon_info["forms"] or f"{pokemon_info['name']}-{form_key}" in pokemon_info["forms"]):
                        form_name = form_key
                        if not form_key.startswith(pokemon_info["name"]):
                            form_name = f"{pokemon_info['name']}-{form_key}"
                            
                        # Fetch this specific form
                        async with self.session.get(f"https://pokeapi.co/api/v2/pokemon/{form_name}") as form_response:
                            if form_response.status == 200:
                                form_data = await form_response.json()
                                
                                # Create form-specific info
                                form_info = {
                                    "id": form_data["id"],
                                    "name": form_data["name"],
                                    "types": [t["type"]["name"] for t in form_data["types"]],
                                    "height": form_data["height"],
                                    "weight": form_data["weight"],
                                    "sprite": form_data["sprites"]["front_default"],
                                    "base_experience": form_data["base_experience"],
                                    "stats": {s["stat"]["name"]: s["base_stat"] for s in form_data["stats"]},
                                    "base_pokemon": pokemon_id,
                                    "form_type": form_key,
                                }
                                
                                # Add to form cache
                                form_cache[cache_key] = form_info
                                await self.config.form_cache.set(form_cache)
                                
                                return form_info
                    
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
                                        item = None
                                        condition = None
                                        
                                        for detail in evolution["evolution_details"]:
                                            # Check for level-up evolution
                                            if detail["trigger"]["name"] == "level-up":
                                                level = detail.get("min_level")
                                                
                                                # Check for special conditions
                                                if detail.get("time_of_day"):
                                                    condition = f"level-up during {detail['time_of_day']}"
                                                elif detail.get("known_move"):
                                                    condition = f"level-up knowing {detail['known_move']['name']}"
                                                elif detail.get("location"):
                                                    condition = f"level-up at {detail['location']['name']}"
                                                elif detail.get("min_happiness"):
                                                    condition = f"level-up with happiness ≥ {detail['min_happiness']}"
                                                elif detail.get("held_item"):
                                                    condition = f"level-up holding {detail['held_item']['name']}"
                                            
                                            # Check for item-based evolution
                                            elif detail["trigger"]["name"] == "use-item":
                                                item = detail.get("item", {}).get("name")
                                                condition = f"use {item}"
                                            
                                            # Check for trade evolution
                                            elif detail["trigger"]["name"] == "trade":
                                                condition = "trade"
                                                if detail.get("held_item"):
                                                    condition += f" while holding {detail['held_item']['name']}"
                                        
                                        evolves_to.append({
                                            "id": evo_id,
                                            "name": evo_name,
                                            "level": level,
                                            "item": item,
                                            "condition": condition
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
                                                pokemon_info["evolution_item"] = evo["item"]
                                                pokemon_info["evolution_condition"] = evo["condition"]
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
    
    async def fetch_all_forms(self, pokemon_id: int) -> List[dict]:
        """Fetch all available forms for a Pokemon."""
        # Get base Pokemon data
        base_pokemon = await self.fetch_pokemon(pokemon_id)
        if not base_pokemon:
            return []
            
        all_forms = [base_pokemon]  # Start with base form
        
        # Fetch all the additional forms
        for form_name in base_pokemon.get("forms", []):
            # Extract form key (e.g., 'mega', 'alola', etc.)
            if "-" in form_name:
                form_key = form_name.split("-", 1)[1]
                form_data = await self.fetch_pokemon(pokemon_id, form_key)
                if form_data:
                    all_forms.append(form_data)
        
        return all_forms
    
    async def spawn_pokemon(self, guild: discord.Guild) -> bool:
        """Attempt to spawn a Pokemon in the guild."""
        # Get lock for this guild first
        if guild.id not in self.pokemon_locks:
            self.pokemon_locks[guild.id] = asyncio.Lock()
            
        async with self.pokemon_locks[guild.id]:
            # Check if a Pokemon is already active in this guild
            if guild.id in self.spawns_active:
                return False
                
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
            # Randomly decide whether to spawn a special form
            include_mega = guild_config.get("include_mega", False)
            include_gmax = guild_config.get("include_gmax", False)
            include_forms = guild_config.get("include_forms", False)
            
            special_form = False
            form_type = None
            
            # 10% chance for a special form if enabled
            if random.random() < 0.1:
                if include_mega and random.random() < 0.33:
                    special_form = True
                    form_type = "mega"
                    # For Charizard and Mewtwo, pick X or Y
                    if random.random() < 0.5:
                        form_type = "mega-x"
                    else:
                        form_type = "mega-y"
                elif include_gmax and random.random() < 0.33:
                    special_form = True
                    form_type = "gmax"
                elif include_forms and random.random() < 0.33:
                    special_form = True
                    # Pick a regional form
                    form_options = ["alola", "galar", "hisui"]
                    form_type = random.choice(form_options)
            
            pokemon_id = random.randint(1, 898)
            
            # For mega evolutions, only select Pokemon that can mega evolve
            if special_form and form_type in ["mega", "mega-x", "mega-y"]:
                # List of Pokemon that can Mega Evolve
                mega_capable_pokemon = [3, 6, 9, 65, 94, 115, 127, 130, 142, 150, 181, 212, 214, 229, 248, 257, 282, 303, 306, 308, 310, 354, 359, 380, 381, 445, 448, 460]
                pokemon_id = random.choice(mega_capable_pokemon)
            
            # For Gigantamax, only select Pokemon with Gigantamax forms
            if special_form and form_type == "gmax":
                # List of Pokemon with Gigantamax forms
                gmax_capable_pokemon = [3, 6, 9, 12, 25, 52, 68, 94, 99, 131, 143, 569, 809, 812, 815, 818, 823, 826, 834, 839, 841, 844, 849, 851, 858, 861, 869, 879, 884, 892]
                pokemon_id = random.choice(gmax_capable_pokemon)
            
            # For regional forms, only select Pokemon with those forms
            if special_form and form_type in ["alola", "galar", "hisui"]:
                if form_type == "alola":
                    # List of Pokemon with Alolan forms
                    alolan_pokemon = [19, 20, 26, 27, 28, 37, 38, 50, 51, 52, 53, 74, 75, 76, 88, 89, 103, 105]
                    pokemon_id = random.choice(alolan_pokemon)
                elif form_type == "galar":
                    # List of Pokemon with Galarian forms
                    galarian_pokemon = [52, 77, 78, 79, 80, 83, 110, 122, 144, 145, 146, 199, 222, 263, 264, 554, 555, 562, 618]
                    pokemon_id = random.choice(galarian_pokemon)
                elif form_type == "hisui":
                    # List of Pokemon with Hisuian forms
                    hisuian_pokemon = [58, 59, 100, 101, 157, 211, 215, 503, 549, 570, 571, 628, 705, 706, 713]
                    pokemon_id = random.choice(hisuian_pokemon)
            
            # Fetch Pokemon data with form if needed
            pokemon_data = await self.fetch_pokemon(pokemon_id, form_type)
            
            if not pokemon_data:
                return False
            
            # Resolve the bot's prefix to a string
            # Fix the prefix issue
            if callable(self.bot.command_prefix):
                try:
                    # If command_prefix is callable, get the actual prefix for this guild
                    prefix_list = await self.bot.command_prefix(self.bot, None, guild=guild)
                    # Use the first prefix if it's a list
                    prefix = prefix_list[0] if isinstance(prefix_list, list) else prefix_list
                except:
                    # Default fallback prefix if we can't get the actual one
                    prefix = "!"
            else:
                # If it's already a string or list
                prefix = self.bot.command_prefix[0] if isinstance(self.bot.command_prefix, list) else self.bot.command_prefix
            
            # Format display name properly
            display_name = "Pokémon"
            if "-" in pokemon_data["name"]:
                base_name, form = pokemon_data["name"].split("-", 1)
                base_name = base_name.capitalize()
                if form == "mega":
                    display_name = f"Mega {base_name}"
                elif form.startswith("mega-"):
                    form_type = form.split("-")[1].upper()
                    display_name = f"Mega {base_name} {form_type}"
                elif form == "gmax":
                    display_name = f"Gigantamax {base_name}"
                elif form in ["alola", "galar", "hisui"]:
                    display_name = f"{form.capitalize()}n {base_name}"
                else:
                    display_name = pokemon_data["name"].capitalize()
            else:
                display_name = pokemon_data["name"].capitalize()
            
            # Create embed for spawn with clearer catching instructions
            embed = discord.Embed(
                title=f"A wild {display_name} appeared!",
                description=f"Type `{prefix}p catch {pokemon_data['name']}` to catch it!",
                color=0x00ff00
            )
            
            # Center the sprite in the embed and make it larger
            # Instead of setting thumbnail, we'll use the image property for larger display
            embed.set_image(url=pokemon_data["sprite"])
            
            # Add alternative formats for special forms to make it easier to catch
            if "-" in pokemon_data["name"]:
                base_name, form = pokemon_data["name"].split("-", 1)
                base_name = base_name.capitalize()
                
                if form == "mega":
                    embed.add_field(
                        name="Catch Commands",
                        value=f"`{prefix}p catch {pokemon_data['name']}`\n"
                            f"`{prefix}p catch Mega {base_name}`\n"
                            f"`{prefix}p catch {base_name}`",
                        inline=False
                    )
                elif form.startswith("mega-"):
                    form_type = form.split("-")[1].upper()
                    embed.add_field(
                        name="Catch Commands",
                        value=f"`{prefix}p catch {pokemon_data['name']}`\n"
                            f"`{prefix}p catch Mega {base_name} {form_type}`\n"
                            f"`{prefix}p catch {base_name}`",
                        inline=False
                    )
                elif form == "gmax":
                    embed.add_field(
                        name="Catch Commands",
                        value=f"`{prefix}p catch {pokemon_data['name']}`\n"
                            f"`{prefix}p catch Gigantamax {base_name}`\n"
                            f"`{prefix}p catch {base_name}`",
                        inline=False
                    )
            
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
        
        # Get lock for this guild
        if guild_id not in self.pokemon_locks:
            self.pokemon_locks[guild_id] = asyncio.Lock()
            
        async with self.pokemon_locks[guild_id]:
            # Check if the spawn is still active (it might have been caught)
            if guild_id in self.spawns_active and self.spawns_active[guild_id]["expiry"] == expiry:
                pokemon_name = self.spawns_active[guild_id]["pokemon"]["name"].capitalize()
                
                # Format name for display (handle forms)
                display_name = pokemon_name
                if "-" in pokemon_name:
                    base_name, form = pokemon_name.split("-", 1)
                    if form == "mega":
                        display_name = f"Mega {base_name.capitalize()}"
                    elif form in ["mega-x", "mega-y"]:
                        mega_type = form.split("-")[1].upper()
                        display_name = f"Mega {base_name.capitalize()} {mega_type}"
                    elif form == "gmax":
                        display_name = f"Gigantamax {base_name.capitalize()}"
                    elif form in ["alola", "galar", "hisui"]:
                        display_name = f"{form.capitalize()}n {base_name.capitalize()}"
                
                # Remove the spawn
                del self.spawns_active[guild_id]
                
                # Send expiry message
                await channel.send(f"The wild {display_name} fled!")
    
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
        # Check if this is a fully evolved Pokemon (no further evolutions)
        if "evolves_to" not in pokemon_data or not pokemon_data["evolves_to"]:
            # This is a fully evolved Pokemon or has no evolutions
            # Random chance to award special items
            
            # Get user's items
            async with self.config.user(user).items() as user_items:
                # Check Pokemon ID for special items
                pokemon_id = pokemon_data["id"]
                
                # Check for Mega Stone eligibility
                if str(pokemon_id) in MEGA_STONES or pokemon_id in MEGA_STONES:
                    mega_stone = MEGA_STONES.get(str(pokemon_id)) or MEGA_STONES.get(pokemon_id)
                    if mega_stone and random.random() < 0.15:  # 15% chance
                        # Award Mega Stone
                        user_items[mega_stone] = user_items.get(mega_stone, 0) + 1
                        return {"item": mega_stone, "type": "mega_stone"}
                
                # Check for type-based Z-Crystal
                if pokemon_data.get("types"):
                    primary_type = pokemon_data["types"][0].capitalize()
                    if primary_type in Z_CRYSTALS and random.random() < 0.1:  # 10% chance
                        z_crystal = Z_CRYSTALS[primary_type]
                        user_items[z_crystal] = user_items.get(z_crystal, 0) + 1
                        return {"item": z_crystal, "type": "z_crystal"}
                
                # Check for Primal Orbs (Kyogre/Groudon)
                if str(pokemon_id) in PRIMAL_ORBS or pokemon_id in PRIMAL_ORBS:
                    orb = PRIMAL_ORBS.get(str(pokemon_id)) or PRIMAL_ORBS.get(pokemon_id)
                    if orb and random.random() < 0.5:  # 50% chance since these are legendaries
                        user_items[orb] = user_items.get(orb, 0) + 1
                        return {"item": orb, "type": "primal_orb"}
        
        return None
    
    async def activate_form(self, user: discord.Member, pokemon_id: str, form_type: str) -> Optional[dict]:
        """Activate a special form for a Pokemon (Mega, Primal, etc.)"""
        user_pokemon = await self.config.user(user).pokemon()
        user_items = await self.config.user(user).items()
        
        if pokemon_id not in user_pokemon:
            return {"success": False, "reason": "You don't have this Pokemon!"}
        
        pokemon = user_pokemon[pokemon_id]
        base_pokemon_id = pokemon_id
        
        # Check what form is being requested
        required_item = None
        
        if form_type == "mega":
            # Check for mega evolution
            # First, verify if this Pokemon can mega evolve
            pokemon_data = await self.fetch_pokemon(int(pokemon_id))
            if not pokemon_data or not pokemon_data.get("mega_evolution"):
                return {"success": False, "reason": "This Pokemon cannot Mega Evolve!"}
            
            # Check if user has the mega stone
            # Check for both standard and X/Y variants
            if int(pokemon_id) in MEGA_STONES:
                required_item = MEGA_STONES[int(pokemon_id)]
            elif pokemon_id in MEGA_STONES:
                required_item = MEGA_STONES[pokemon_id]
            elif (int(pokemon_id), "X") in MEGA_STONES:
                required_item = MEGA_STONES[(int(pokemon_id), "X")]
            elif (int(pokemon_id), "Y") in MEGA_STONES:
                required_item = MEGA_STONES[(int(pokemon_id), "Y")]
            else:
                return {"success": False, "reason": "No Mega Stone found for this Pokemon!"}
            
            # Check if user has the item
            if required_item not in user_items or user_items[required_item] <= 0:
                return {"success": False, "reason": f"You don't have a {required_item}!"}
            
            # Get mega form
            mega_form = await self.fetch_pokemon(int(pokemon_id), "mega")
            if not mega_form:
                return {"success": False, "reason": "Error fetching Mega Evolution data."}
            
            # Add the mega form to user's collection temporarily
            mega_id = str(mega_form["id"])
            async with self.config.user(user).pokemon() as user_pokemon:
                user_pokemon[mega_id] = {
                    "name": mega_form["name"],
                    "level": pokemon["level"],
                    "xp": pokemon["xp"],
                    "caught_at": datetime.now().timestamp(),
                    "count": 1,
                    "form_type": "mega",
                    "base_pokemon": base_pokemon_id,
                    "temporary": True,  # Mark as temporary
                    "expires_at": datetime.now().timestamp() + 3600  # 1 hour duration
                }
                
                # Set as active Pokemon
                await self.config.user(user).active_pokemon.set(mega_id)
            
            return {
                "success": True, 
                "message": f"Your {pokemon_data['name'].capitalize()} mega evolved with {required_item}!",
                "form": mega_form
            }
            
        elif form_type == "primal":
            # Check for primal reversion
            pokemon_data = await self.fetch_pokemon(int(pokemon_id))
            if not pokemon_data or not pokemon_data.get("primal_reversion"):
                return {"success": False, "reason": "This Pokemon cannot undergo Primal Reversion!"}
            
            # Check if user has the orb
            if int(pokemon_id) in PRIMAL_ORBS:
                required_item = PRIMAL_ORBS[int(pokemon_id)]
            elif pokemon_id in PRIMAL_ORBS:
                required_item = PRIMAL_ORBS[pokemon_id]
            else:
                return {"success": False, "reason": "No Primal Orb found for this Pokemon!"}
            
            # Check if user has the item
            if required_item not in user_items or user_items[required_item] <= 0:
                return {"success": False, "reason": f"You don't have a {required_item}!"}
            
            # Get primal form
            primal_form = await self.fetch_pokemon(int(pokemon_id), "primal")
            if not primal_form:
                return {"success": False, "reason": "Error fetching Primal Reversion data."}
            
            # Add the primal form to user's collection temporarily
            primal_id = str(primal_form["id"])
            async with self.config.user(user).pokemon() as user_pokemon:
                user_pokemon[primal_id] = {
                    "name": primal_form["name"],
                    "level": pokemon["level"],
                    "xp": pokemon["xp"],
                    "caught_at": datetime.now().timestamp(),
                    "count": 1,
                    "form_type": "primal",
                    "base_pokemon": base_pokemon_id,
                    "temporary": True,  # Mark as temporary
                    "expires_at": datetime.now().timestamp() + 3600  # 1 hour duration
                }
                
                # Set as active Pokemon
                await self.config.user(user).active_pokemon.set(primal_id)
            
            return {
                "success": True, 
                "message": f"Your {pokemon_data['name'].capitalize()} reverted to its primal form with {required_item}!",
                "form": primal_form
            }
            
        elif form_type == "dynamax" or form_type == "gigantamax":
            # Check for Gigantamax capability
            pokemon_data = await self.fetch_pokemon(int(pokemon_id))
            is_gmax = False
            
            # Check if this Pokemon can Gigantamax
            if pokemon_data and pokemon_data.get("gigantamax"):
                is_gmax = True
            
            # Check if user has the Dynamax Band
            if "Dynamax Band" not in user_items or user_items["Dynamax Band"] <= 0:
                return {"success": False, "reason": "You don't have a Dynamax Band!"}
            
            # Get form data
            form_key = "gmax" if is_gmax else "dynamax"
            form_data = None
            
            if is_gmax:
                form_data = await self.fetch_pokemon(int(pokemon_id), "gmax")
            
            if not form_data and is_gmax:
                # Fallback to regular Dynamax
                is_gmax = False
            
            # For regular Dynamax, we'll just use the base form with increased stats
            if not is_gmax:
                form_data = pokemon_data
            
            # Create temporary Dynamax/Gigantamax form
            form_id = str(form_data["id"])
            async with self.config.user(user).pokemon() as user_pokemon:
                # For Dynamax, we'll modify the stats
                dynamaxed_stats = {}
                for stat_name, stat_value in form_data.get("stats", {}).items():
                    if stat_name == "hp":
                        dynamaxed_stats[stat_name] = stat_value * 2  # Double HP
                    else:
                        dynamaxed_stats[stat_name] = stat_value
                
                # Create the temporary form
                user_pokemon[f"{form_id}-dmax"] = {
                    "name": f"{form_data['name']}-dynamaxed",
                    "level": pokemon["level"],
                    "xp": pokemon["xp"],
                    "caught_at": datetime.now().timestamp(),
                    "count": 1,
                    "form_type": "gmax" if is_gmax else "dynamax",
                    "base_pokemon": base_pokemon_id,
                    "temporary": True,
                    "expires_at": datetime.now().timestamp() + 1800,  # 30 minutes duration
                    "stats": dynamaxed_stats
                }
                
                # Set as active Pokemon
                await self.config.user(user).active_pokemon.set(f"{form_id}-dmax")
            
            form_name = "Gigantamax" if is_gmax else "Dynamax"
            return {
                "success": True,
                "message": f"Your {pokemon_data['name'].capitalize()} used {form_name}!",
                "form": form_data,
                "is_gmax": is_gmax
            }
            
        elif form_type in ["alola", "galar", "hisui"]:
            # Regional forms are permanent forms caught separately, not transformations
            return {"success": False, "reason": f"{form_type.capitalize()} forms must be caught directly and cannot be transformed."}
        
        return {"success": False, "reason": "Unknown form type!"}
    
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
        
    @pokemon_settings.command(name="forms")
    async def toggle_forms(self, ctx: commands.Context, form_type: str = None, enabled: bool = None):
        """Toggle special forms in spawns (mega, gmax, regional)."""
        valid_forms = ["mega", "gmax", "regional", "all"]
        
        if form_type not in valid_forms and form_type is not None:
            await ctx.send(f"Invalid form type! Choose from: {', '.join(valid_forms)}")
            return
        
        async with self.config.guild(ctx.guild).all() as guild_config:
            if form_type is None or enabled is None:
                # Show current settings
                mega_status = guild_config.get("include_mega", False)
                gmax_status = guild_config.get("include_gmax", False)
                forms_status = guild_config.get("include_forms", False)
                
                embed = discord.Embed(
                    title="Special Form Settings",
                    description="Current settings for special Pokemon forms spawns:",
                    color=0x3498db
                )
                
                embed.add_field(name="Mega Evolutions", value="✅ Enabled" if mega_status else "❌ Disabled", inline=True)
                embed.add_field(name="Gigantamax Forms", value="✅ Enabled" if gmax_status else "❌ Disabled", inline=True)
                embed.add_field(name="Regional Forms", value="✅ Enabled" if forms_status else "❌ Disabled", inline=True)
                
                await ctx.send(embed=embed)
                return
            
            # Update settings
            if form_type == "mega" or form_type == "all":
                guild_config["include_mega"] = enabled
            
            if form_type == "gmax" or form_type == "all":
                guild_config["include_gmax"] = enabled
            
            if form_type == "regional" or form_type == "all":
                guild_config["include_forms"] = enabled
            
            # Confirm changes
            status = "enabled" if enabled else "disabled"
            if form_type == "all":
                await ctx.send(f"All special forms have been {status}!")
            else:
                form_name = "Mega Evolutions" if form_type == "mega" else "Gigantamax Forms" if form_type == "gmax" else "Regional Forms"
                await ctx.send(f"{form_name} have been {status}!")
        
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
        
        # Special forms
        embed.add_field(
            name="Special Forms",
            value=f"Mega Evolutions: {'✅' if guild_config.get('include_mega', False) else '❌'}\n"
                  f"Gigantamax Forms: {'✅' if guild_config.get('include_gmax', False) else '❌'}\n"
                  f"Regional Forms: {'✅' if guild_config.get('include_forms', False) else '❌'}",
            inline=False
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
            await self.config.guild(ctx.guild).include_mega.set(False)
            await self.config.guild(ctx.guild).include_gmax.set(False)
            await self.config.guild(ctx.guild).include_forms.set(False)
            
            await ctx.send("Pokemon settings have been reset to default values.")
        except asyncio.TimeoutError:
            await ctx.send("Reset settings confirmation timed out. No changes were made.")
            
            
    @pokemon_settings.command(name="clear_cache")
    @commands.is_owner()
    async def clear_cache(self, ctx: commands.Context):
        """Clear the Pokemon data cache (bot owner only)."""
        await self.config.pokemon_cache.clear()
        await self.config.form_cache.clear()
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
            
    @pokemon_commands.command(name="forcespawn")
    @commands.admin_or_permissions(manage_guild=True)
    async def force_spawn(self, ctx: commands.Context, pokemon_id: int = None, *, form: str = None):
        """Forcefully spawn a Pokémon in the configured spawn channel."""
        # Get the spawn channel from the guild configuration
        guild_config = await self.config.guild(ctx.guild).all()
        channel_id = guild_config["channel"]

        if not channel_id:
            await ctx.send("No spawn channel is set! Use `!pokemon settings channel` to configure one.")
            return

        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            await ctx.send("The configured spawn channel no longer exists! Please set a new one.")
            return

        # If no Pokémon ID is provided, randomly select one
        if not pokemon_id:
            pokemon_id = random.randint(1, 898)  # National Dex range

        # Fetch Pokémon data
        pokemon_data = await self.fetch_pokemon(pokemon_id, form)
        if not pokemon_data:
            await ctx.send(f"Failed to fetch data for Pokémon ID {pokemon_id}. Please try again.")
            return

        # Get the proper prefix
        if callable(self.bot.command_prefix):
            try:
                prefix_list = await self.bot.command_prefix(self.bot, None, guild=ctx.guild)
                prefix = prefix_list[0] if isinstance(prefix_list, list) else prefix_list
            except:
                prefix = "!"
        else:
            prefix = self.bot.command_prefix[0] if isinstance(self.bot.command_prefix, list) else self.bot.command_prefix

        # Format display name
        display_name = pokemon_data["name"].capitalize()
        if "-" in display_name:
            base_name, form = display_name.split("-", 1)
            base_name = base_name.capitalize()
            if form == "mega":
                display_name = f"Mega {base_name}"
            elif form.startswith("mega-"):
                form_type = form.split("-")[1].upper()
                display_name = f"Mega {base_name} {form_type}"
            elif form == "gmax":
                display_name = f"Gigantamax {base_name}"
            elif form in ["alola", "galar", "hisui"]:
                display_name = f"{form.capitalize()}n {base_name}"

        # Create the embed for the spawned Pokémon
        embed = discord.Embed(
            title=f"A wild {display_name} appeared!",
            description=f"Type `{prefix}p catch {pokemon_data['name']}` to catch it!",
            color=0x00ff00
        )
        
        # Center the sprite in the embed and make it larger
        embed.set_image(url=pokemon_data["sprite"])

        # Set the spawn expiry time
        now = datetime.now().timestamp()
        expiry = now + CATCH_TIMEOUT

        # Store the active spawn
        self.spawns_active[ctx.guild.id] = {
            "pokemon": pokemon_data,
            "expiry": expiry
        }

        # Update the last spawn time
        await self.config.guild(ctx.guild).last_spawn.set(now)

        # Send the spawn message to the configured channel
        await channel.send(embed=embed)

        # Notify the admin in the command channel
        if channel.id != ctx.channel.id:
            await ctx.send(f"A Pokémon has been forcefully spawned in {channel.mention}!")

        # Set up the expiry task
        self.bot.loop.create_task(self.expire_spawn(ctx.guild.id, channel, expiry))
        
    @pokemon_commands.command(name="spawnstatus")
    @commands.admin_or_permissions(manage_guild=True)
    async def spawn_status(self, ctx: commands.Context):
        """Check the current spawn status and settings."""
        guild_config = await self.config.guild(ctx.guild).all()
        
        # Get spawn channel info
        channel_id = guild_config.get("channel")
        channel = ctx.guild.get_channel(channel_id) if channel_id else None
        
        # Check active Pokemon
        active_spawn = self.spawns_active.get(ctx.guild.id)
        
        # Create embed
        embed = discord.Embed(
            title="Pokemon Spawn Status",
            color=0x3498db
        )
        
        # Spawn channel info
        embed.add_field(
            name="Spawn Channel",
            value=f"{channel.mention if channel else 'Not set'}",
            inline=False
        )
        
        # Spawn settings
        embed.add_field(
            name="Spawn Settings",
            value=f"Chance: {guild_config.get('spawn_chance', SPAWN_CHANCE)*100:.1f}%\n"
                f"Cooldown: {guild_config.get('spawn_cooldown', MIN_SPAWN_COOLDOWN)} seconds",
            inline=True
        )
        
        # Last spawn time
        last_spawn = guild_config.get("last_spawn", 0)
        time_since = datetime.now().timestamp() - last_spawn
        embed.add_field(
            name="Last Spawn",
            value=f"{int(time_since)} seconds ago" if last_spawn > 0 else "Never",
            inline=True
        )
        
        # Active spawn info
        if active_spawn:
            pokemon_data = active_spawn.get("pokemon", {})
            expiry = active_spawn.get("expiry", 0)
            time_left = max(0, expiry - datetime.now().timestamp())
            
            embed.add_field(
                name="Active Spawn",
                value=f"Pokemon: {pokemon_data.get('name', 'Unknown').capitalize()}\n"
                    f"Expires in: {int(time_left)} seconds",
                inline=False
            )
        else:
            embed.add_field(
                name="Active Spawn",
                value="No active Pokemon spawn",
                inline=False
            )
        
        # Special forms enabled
        special_forms = []
        if guild_config.get("include_mega", False):
            special_forms.append("Mega Evolutions")
        if guild_config.get("include_gmax", False):
            special_forms.append("Gigantamax Forms")
        if guild_config.get("include_forms", False):
            special_forms.append("Regional Forms")
        
        embed.add_field(
            name="Special Forms",
            value=", ".join(special_forms) if special_forms else "None enabled",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @pokemon_team.command(name="view")
    async def team_view(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's Pokemon team."""
        if user is None:
            user = ctx.author

        # Get user's team - FIXED: directly get the value, don't use get() method
        team = await self.config.user(user).team()

        # If the team is empty, fall back to the user's Pokemon collection
        if not team:
            # FIXED: directly get the value, don't use get() method
            user_pokemon = await self.config.user(user).pokemon()
            if not user_pokemon:
                await ctx.send(f"{user.name} doesn't have a team set up yet and hasn't caught any Pokémon!")
                return

            # Use the Pokémon collection as a fallback
            team = list(user_pokemon.keys())[:6]  # Limit to 6 Pokémon for display

        # Get Pokemon data for each team member
        team_data = []
        for pokemon_id in team:
            # Check if this is a special form
            # FIXED: Get the entire pokemon dictionary first
            user_pokemon_data = await self.config.user(user).pokemon()
            
            # Then access the specific pokemon if it exists
            if pokemon_id in user_pokemon_data:
                pokemon = user_pokemon_data[pokemon_id]
                form_type = pokemon.get("form_type")
                
                pokemon_data = await self.fetch_pokemon(int(pokemon_id), form_type)
                
                if pokemon_data:
                    # Get user's Pokemon level and nickname
                    level = pokemon.get("level", 1)
                    nickname = pokemon.get("nickname", None)

                    team_data.append({
                        "id": pokemon_id,
                        "name": pokemon_data["name"],
                        "sprite": pokemon_data["sprite"],
                        "types": pokemon_data["types"],
                        "level": level,
                        "nickname": nickname,
                        "form_type": form_type
                    })

        # Create embed
        embed = discord.Embed(
            title=f"{user.name}'s Pokemon Team",
            color=0xff5500
        )

        # Add each Pokemon to the embed
        for pokemon in team_data:
            # Format name based on form type
            display_name = pokemon["name"].capitalize()
            if pokemon.get("form_type"):
                # Format special forms for display
                if pokemon["form_type"] == "mega":
                    if "-mega-x" in pokemon["name"]:
                        display_name = f"Mega {pokemon['name'].split('-')[0].capitalize()} X"
                    elif "-mega-y" in pokemon["name"]:
                        display_name = f"Mega {pokemon['name'].split('-')[0].capitalize()} Y"
                    else:
                        display_name = f"Mega {pokemon['name'].split('-')[0].capitalize()}"
                elif pokemon["form_type"] == "gmax":
                    display_name = f"Gigantamax {pokemon['name'].split('-')[0].capitalize()}"
                elif pokemon["form_type"] in ["alola", "galar", "hisui"]:
                    form = pokemon["form_type"].capitalize()
                    display_name = f"{form}n {pokemon['name'].split('-')[0].capitalize()}"
                elif pokemon["form_type"] == "primal":
                    display_name = f"Primal {pokemon['name'].split('-')[0].capitalize()}"
            
            name = pokemon["nickname"] or display_name
            if pokemon["nickname"]:
                name += f" ({display_name})"

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
        
        # Count special forms
        mega_count = sum(1 for p in user_pokemon.values() if p.get("form_type") == "mega")
        gmax_count = sum(1 for p in user_pokemon.values() if p.get("form_type") == "gmax")
        regional_count = sum(1 for p in user_pokemon.values() if p.get("form_type") in ["alola", "galar", "hisui"])
        
        # Get high level Pokemon
        high_level_pokemon = []
        for pokemon_id, pokemon_data in user_pokemon.items():
            if pokemon_data["level"] >= 50:  # Arbitrary threshold
                form_type = pokemon_data.get("form_type")
                pokemon_info = await self.fetch_pokemon(int(pokemon_id), form_type)
                if pokemon_info:
                    high_level_pokemon.append({
                        "id": pokemon_id,
                        "name": pokemon_info["name"],
                        "level": pokemon_data["level"],
                        "form_type": form_type
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
            value=f"Total Pokemon: {total_pokemon}\nUnique Species: {len(set(p['name'].split('-')[0] for p in user_pokemon.values()))}",
            inline=True
        )
        
        embed.add_field(
            name="Training Stats",
            value=f"Total Levels: {total_levels}\nAverage Level: {avg_level:.1f}\nHighest Level: {highest_level}",
            inline=True
        )
        
        # Special forms
        embed.add_field(
            name="Special Forms",
            value=f"Mega Evolutions: {mega_count}\nGigantamax Forms: {gmax_count}\nRegional Variants: {regional_count}",
            inline=False
        )
        
        # Add high level Pokemon
        if high_level_pokemon:
            high_level_str = "\n".join(f"Lv{p['level']} {self.format_pokemon_name(p['name'], p['form_type'])}" for p in high_level_pokemon[:5])
            if len(high_level_pokemon) > 5:
                high_level_str += f"\n...and {len(high_level_pokemon) - 5} more"
            
            embed.add_field(
                name="High Level Pokemon",
                value=high_level_str,
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    def format_pokemon_name(self, name, form_type=None):
        """Format a Pokemon name for display, including special forms."""
        if not form_type or "-" not in name:
            return name.capitalize()
            
        base_name = name.split("-")[0].capitalize()
        
        if form_type == "mega":
            if "mega-x" in name:
                return f"Mega {base_name} X"
            elif "mega-y" in name:
                return f"Mega {base_name} Y"
            else:
                return f"Mega {base_name}"
        elif form_type == "gmax":
            return f"Gigantamax {base_name}"
        elif form_type in ["alola", "galar", "hisui"]:
            return f"{form_type.capitalize()}n {base_name}"
        elif form_type == "primal":
            return f"Primal {base_name}"
        
        return name.capitalize()
   
    @pokemon_commands.command(name="items", aliases=["bag", "inventory"])
    async def view_items(self, ctx: commands.Context, user: discord.Member = None):
        """View your or another user's item inventory."""
        if user is None:
            user = ctx.author
            
        # Get user's items
        user_items = await self.config.user(user).items()
        
        if not user_items:
            await ctx.send(f"{user.name} doesn't have any items!")
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"{user.name}'s Items",
            description=f"Total unique items: {len(user_items)}",
            color=0x00aaff
        )
        
        # Group items by category
        mega_stones = {}
        z_crystals = {}
        primal_orbs = {}
        evo_items = {}
        other_items = {}
        
        for item_name, count in user_items.items():
            if "ite" in item_name and item_name in [stone for stone in MEGA_STONES.values()]:
                mega_stones[item_name] = count
            elif "Z" in item_name and item_name in [crystal for crystal in Z_CRYSTALS.values()]:
                z_crystals[item_name] = count
            elif "Orb" in item_name and item_name in [orb for orb in PRIMAL_ORBS.values()]:
                primal_orbs[item_name] = count
            elif item_name in ["Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", 
                              "Moon Stone", "Sun Stone", "Shiny Stone", "Dusk Stone", "Dawn Stone"]:
                evo_items[item_name] = count
            else:
                other_items[item_name] = count
        
        # Add fields for each category
        if mega_stones:
            mega_str = "\n".join(f"{name}: {count}" for name, count in mega_stones.items())
            embed.add_field(name="Mega Stones", value=mega_str, inline=False)
            
        if z_crystals:
            z_str = "\n".join(f"{name}: {count}" for name, count in z_crystals.items())
            embed.add_field(name="Z-Crystals", value=z_str, inline=False)
            
        if primal_orbs:
            orb_str = "\n".join(f"{name}: {count}" for name, count in primal_orbs.items())
            embed.add_field(name="Primal Orbs", value=orb_str, inline=False)
            
        if evo_items:
            evo_str = "\n".join(f"{name}: {count}" for name, count in evo_items.items())
            embed.add_field(name="Evolution Items", value=evo_str, inline=False)
            
        if other_items:
            other_str = "\n".join(f"{name}: {count}" for name, count in other_items.items())
            embed.add_field(name="Other Items", value=other_str, inline=False)
            
        await ctx.send(embed=embed)
        
    @pokemon_commands.command(name="use")
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
                    pokemon_data = await self.fetch_pokemon(int(active_pokemon_id))
                    pokemon_name = pokemon_data["name"].capitalize() if pokemon_data else f"Pokemon #{active_pokemon_id}"
                    
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
                    pokemon_data = await self.fetch_pokemon(int(active_pokemon_id))
                    pokemon_name = pokemon_data["name"].capitalize() if pokemon_data else f"Pokemon #{active_pokemon_id}"
                    
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
                await ctx.send("You used a Lucky Egg! Your active Pokemon will now earn double XP for the next hour!")
                # Logic for implementing time-based XP boost would go here
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
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Evolution stones
        evolution_stones = {
            "Fire Stone": ["Vulpix", "Growlithe", "Eevee"],
            "Water Stone": ["Poliwhirl", "Shellder", "Eevee", "Lombre", "Panpour"],
            "Thunder Stone": ["Pikachu", "Eevee"],
            "Leaf Stone": ["Gloom", "Weepinbell", "Exeggcute", "Nuzleaf", "Pansage"],
            "Moon Stone": ["Nidorina", "Nidorino", "Clefairy", "Jigglypuff", "Skitty", "Munna"],
            "Sun Stone": ["Gloom", "Sunkern", "Cottonee", "Petilil"],
            "Shiny Stone": ["Togetic", "Roselia", "Minccino", "Floette"],
            "Dusk Stone": ["Murkrow", "Misdreavus", "Lampent", "Doublade"],
            "Dawn Stone": ["Kirlia (male)", "Snorunt (female)"]
        }
        
        if found_item in evolution_stones:
            # Check if this Pokemon can evolve with this stone
            can_evolve = False
            target_evolution = None
            
            # Get the Pokemon's name and check if it can evolve with this stone
            pokemon_name = pokemon_data["name"].lower()
            base_name = pokemon_name.split('-')[0]  # Handle form variants
            
            # Mapping of Pokemon to their stone evolutions
            stone_evolutions = {
                # Fire Stone
                "vulpix": {"stone": "Fire Stone", "evolves_to": 38},     # Vulpix → Ninetales
                "growlithe": {"stone": "Fire Stone", "evolves_to": 59},   # Growlithe → Arcanine
                "eevee": {"stone": "Fire Stone", "evolves_to": 136},     # Eevee → Flareon
                "pansear": {"stone": "Fire Stone", "evolves_to": 514},   # Pansear → Simisear
                
                # Water Stone
                "poliwhirl": {"stone": "Water Stone", "evolves_to": 62},  # Poliwhirl → Poliwrath
                "shellder": {"stone": "Water Stone", "evolves_to": 91},   # Shellder → Cloyster
                "staryu": {"stone": "Water Stone", "evolves_to": 121},    # Staryu → Starmie
                "eevee": {"stone": "Water Stone", "evolves_to": 134},     # Eevee → Vaporeon
                "lombre": {"stone": "Water Stone", "evolves_to": 272},    # Lombre → Ludicolo
                "panpour": {"stone": "Water Stone", "evolves_to": 516},   # Panpour → Simipour
                
                # Thunder Stone
                "pikachu": {"stone": "Thunder Stone", "evolves_to": 26},  # Pikachu → Raichu
                "eevee": {"stone": "Thunder Stone", "evolves_to": 135},   # Eevee → Jolteon
                "eelektrik": {"stone": "Thunder Stone", "evolves_to": 604}, # Eelektrik → Eelektross
                
                # Leaf Stone
                "gloom": {"stone": "Leaf Stone", "evolves_to": 45},       # Gloom → Vileplume
                "weepinbell": {"stone": "Leaf Stone", "evolves_to": 71},  # Weepinbell → Victreebel
                "exeggcute": {"stone": "Leaf Stone", "evolves_to": 103},  # Exeggcute → Exeggutor
                "nuzleaf": {"stone": "Leaf Stone", "evolves_to": 275},    # Nuzleaf → Shiftry
                "pansage": {"stone": "Leaf Stone", "evolves_to": 512},    # Pansage → Simisage
                
                # Moon Stone
                "nidorina": {"stone": "Moon Stone", "evolves_to": 31},    # Nidorina → Nidoqueen
                "nidorino": {"stone": "Moon Stone", "evolves_to": 34},    # Nidorino → Nidoking
                "clefairy": {"stone": "Moon Stone", "evolves_to": 36},    # Clefairy → Clefable
                "jigglypuff": {"stone": "Moon Stone", "evolves_to": 40},  # Jigglypuff → Wigglytuff
                "skitty": {"stone": "Moon Stone", "evolves_to": 301},     # Skitty → Delcatty
                "munna": {"stone": "Moon Stone", "evolves_to": 518},      # Munna → Musharna
                
                # Sun Stone
                "gloom": {"stone": "Sun Stone", "evolves_to": 182},       # Gloom → Bellossom
                "sunkern": {"stone": "Sun Stone", "evolves_to": 192},     # Sunkern → Sunflora
                "cottonee": {"stone": "Sun Stone", "evolves_to": 547},    # Cottonee → Whimsicott
                "petilil": {"stone": "Sun Stone", "evolves_to": 549},     # Petilil → Lilligant
                "helioptile": {"stone": "Sun Stone", "evolves_to": 695},  # Helioptile → Heliolisk
                
                # Shiny Stone
                "togetic": {"stone": "Shiny Stone", "evolves_to": 468},   # Togetic → Togekiss
                "roselia": {"stone": "Shiny Stone", "evolves_to": 407},   # Roselia → Roserade
                "minccino": {"stone": "Shiny Stone", "evolves_to": 573},  # Minccino → Cinccino
                "floette": {"stone": "Shiny Stone", "evolves_to": 670},   # Floette → Florges
                
                # Dusk Stone
                "murkrow": {"stone": "Dusk Stone", "evolves_to": 430},    # Murkrow → Honchkrow
                "misdreavus": {"stone": "Dusk Stone", "evolves_to": 429}, # Misdreavus → Mismagius
                "lampent": {"stone": "Dusk Stone", "evolves_to": 609},    # Lampent → Chandelure
                "doublade": {"stone": "Dusk Stone", "evolves_to": 681},   # Doublade → Aegislash
                
                # Dawn Stone
                "kirlia": {"stone": "Dawn Stone", "evolves_to": 475,      # Male Kirlia → Gallade
                        "condition": "male"},
                "snorunt": {"stone": "Dawn Stone", "evolves_to": 478,     # Female Snorunt → Froslass
                        "condition": "female"}
            }
            
            # Check if this Pokemon can evolve with the found stone
            if base_name in stone_evolutions and stone_evolutions[base_name]["stone"] == found_item:
                # Check if any gender conditions apply (for Dawn Stone)
                if "condition" in stone_evolutions[base_name]:
                    # For gender-specific evolutions, check if we have gender data
                    # In a real implementation, we would store gender with the Pokemon
                    gender_condition = stone_evolutions[base_name]["condition"]
                    
                    # Let's add a simple gender check
                    # We'll randomly assign gender for this example, but ideally it would be stored in user_pokemon_data
                    pokemon_gender = user_pokemon.get(pokemon_id_str, {}).get("gender", None)
                    
                    if pokemon_gender is None:
                        # If no gender is stored, randomly assign one (50/50)
                        pokemon_gender = "male" if random.random() < 0.5 else "female"
                        # Store gender for future reference
                        async with self.config.user(user).pokemon() as user_poke:
                            if pokemon_id_str in user_poke:
                                user_poke[pokemon_id_str]["gender"] = pokemon_gender
                    
                    # Now check if it meets the condition
                    if pokemon_gender == gender_condition:
                        can_evolve = True
                        await ctx.send(f"Your {gender_condition} {pokemon_data['name'].capitalize()} can evolve with {found_item}!")
                    else:
                        can_evolve = False
                        await ctx.send(f"Only {gender_condition} {pokemon_data['name'].capitalize()} can evolve with {found_item}!")
                else:
                    can_evolve = True
                    
                # Set the target evolution ID if can evolve
                if can_evolve:
                    target_evolution = stone_evolutions[base_name]["evolves_to"]
                    
                    # Special case for regional forms
                    # If we're evolving a regional form, we need to get the regional evolved form
                if "-" in pokemon_data["name"]:
                    base_name, form_region = pokemon_data["name"].split("-", 1)
                    if form_region in ["alola", "galar", "hisui"]:
                        # Create a mapping of regional evolutions
                        regional_evolutions = {
                            # Alolan forms
                            "vulpix-alola": {"id": 38, "name": "ninetales-alola"},      # Alolan Vulpix → Alolan Ninetales
                            "sandshrew-alola": {"id": 28, "name": "sandslash-alola"},   # Alolan Sandshrew → Alolan Sandslash
                            "diglett-alola": {"id": 51, "name": "dugtrio-alola"},       # Alolan Diglett → Alolan Dugtrio
                            "meowth-alola": {"id": 53, "name": "persian-alola"},        # Alolan Meowth → Alolan Persian
                            "geodude-alola": {"id": 75, "name": "graveler-alola"},      # Alolan Geodude → Alolan Graveler
                            "graveler-alola": {"id": 76, "name": "golem-alola"},        # Alolan Graveler → Alolan Golem
                            "grimer-alola": {"id": 89, "name": "muk-alola"},            # Alolan Grimer → Alolan Muk
                            "exeggcute-alola": {"id": 103, "name": "exeggutor-alola"},  # Exeggcute → Alolan Exeggutor (with Leaf Stone)
                            
                            # Galarian forms
                            "meowth-galar": {"id": 863, "name": "perrserker"},          # Galarian Meowth → Perrserker
                            "ponyta-galar": {"id": 78, "name": "rapidash-galar"},       # Galarian Ponyta → Galarian Rapidash
                            "slowpoke-galar": {"id": 80, "name": "slowbro-galar"},      # Galarian Slowpoke → Galarian Slowbro (with Galarica Cuff)
                            "slowpoke-galar": {"id": 199, "name": "slowking-galar"},    # Galarian Slowpoke → Galarian Slowking (with Galarica Wreath)
                            "farfetchd-galar": {"id": 865, "name": "sirfetchd"},        # Galarian Farfetch'd → Sirfetch'd
                            "corsola-galar": {"id": 864, "name": "cursola"},            # Galarian Corsola → Cursola
                            "yamask-galar": {"id": 867, "name": "runerigus"},           # Galarian Yamask → Runerigus
                            "linoone-galar": {"id": 862, "name": "obstagoon"},          # Galarian Linoone → Obstagoon
                            
                            # Hisuian forms
                            "growlithe-hisui": {"id": 59, "name": "arcanine-hisui"},    # Hisuian Growlithe → Hisuian Arcanine (with Fire Stone)
                            "voltorb-hisui": {"id": 101, "name": "electrode-hisui"},    # Hisuian Voltorb → Hisuian Electrode (with Leaf Stone)
                            "cyndaquil-hisui": {"id": 157, "name": "quilava-hisui"},    # Hisuian Cyndaquil → Hisuian Quilava
                            "quilava-hisui": {"id": 503, "name": "typhlosion-hisui"},   # Hisuian Quilava → Hisuian Typhlosion
                            "petilil-hisui": {"id": 549, "name": "lilligant-hisui"},    # Hisuian Petilil → Hisuian Lilligant (with Sun Stone)
                            "basculin-hisui": {"id": 902, "name": "basculegion"},       # Hisuian Basculin → Basculegion
                            "sneasel-hisui": {"id": 903, "name": "sneasler"},           # Hisuian Sneasel → Sneasler
                            "zorua-hisui": {"id": 571, "name": "zoroark-hisui"},        # Hisuian Zorua → Hisuian Zoroark
                            "sliggoo-hisui": {"id": 706, "name": "goodra-hisui"},       # Hisuian Sliggoo → Hisuian Goodra
                            "bergmite-hisui": {"id": 713, "name": "avalugg-hisui"}      # Hisuian Bergmite → Hisuian Avalugg
                        }
                        
                        # Check if this specific regional form can evolve with this stone
                        regional_key = f"{base_name}-{form_region}"
                        if regional_key in regional_evolutions:
                            # Get the regional evolution data
                            regional_evo = regional_evolutions[regional_key]
                            
                            # Check if this evolution requires a specific stone
                            # For this example, we'll list the ones that require stones
                            stone_required_evolutions = {
                            # Alolan Forms
                            "exeggcute-alola": "Leaf Stone",      # Evolves into Alolan Exeggutor
                            "pikachu-alola": "Thunder Stone",     # Evolves into Alolan Raichu
                            "vulpix-alola": "Ice Stone",          # Evolves into Alolan Ninetales
                            
                            # Galarian Forms
                            "slowpoke-galar": "Galarica Cuff",    # Evolves into Galarian Slowbro
                            "slowpoke-galar": "Galarica Wreath",  # Evolves into Galarian Slowking
                            "darumaka-galar": "Ice Stone",        # Evolves into Galarian Darmanitan
                            "yamask-galar": "Ancient Relic",      # Evolves into Runerigus (needs to be damaged at Dusty Bowl)
                            
                            # Hisuian Forms
                            "growlithe-hisui": "Fire Stone",      # Evolves into Hisuian Arcanine
                            "voltorb-hisui": "Leaf Stone",        # Evolves into Hisuian Electrode
                            "petilil-hisui": "Sun Stone",         # Evolves into Hisuian Lilligant
                            "qwilfish-hisui": "Barb Barrage",     # Evolves into Overqwil (needs to use Barb Barrage 20 times in strong style)
                            "basculin-hisui": "Recoil Damage",    # Evolves into Basculegion (take 294 recoil damage from attacks)
                            "sneasel-hisui": "Razor Claw",        # Evolves into Sneasler (level up during day with Razor Claw)
                            
                            # Paldean Forms
                            "girafarig-paldea": "Friendship",     # Evolves into Farigiraf (level up with high friendship)
                            "primeape-paldea": "Rage Fist",       # Evolves into Annihilape (use Rage Fist 20 times)
                            "bisharp-paldea": "Leader's Crest",   # Evolves into Kingambit (defeat 3 Bisharp holding Leader's Crest)
                            
                            # DLC Forms
                            "wooper-paldea": "Water Stone",       # Evolves into Clodsire (Paldean form)
                            "rockruff-dusk": "Dusk Stone"         # Evolves into Dusk Form Lycanroc
                        }
                            
                            # If stone is required and matches our stone, update target evolution
                            if regional_key in stone_required_evolutions and stone_required_evolutions[regional_key] == found_item:
                                target_evolution = regional_evo["id"]
                                evolved_name = regional_evo["name"]
                                await ctx.send(f"Your {form_region.capitalize()}n {base_name.capitalize()} is evolving into {evolved_name.split('-')[0].capitalize()}!")
                                
                                # If the evolved form also has a regional variant, mention it
                                if "-" in evolved_name:
                                    evolved_base, evolved_form = evolved_name.split("-")
                                    await ctx.send(f"It will maintain its {evolved_form.capitalize()}n form!")
                            elif regional_key not in stone_required_evolutions:
                                # For non-stone evolutions, we'd need a different evolution mechanism
                                await ctx.send(f"This {form_region.capitalize()}n {base_name.capitalize()} doesn't evolve with stones!")
                                can_evolve = False
                            else:
                                # Requires a different stone
                                await ctx.send(f"Your {form_region.capitalize()}n {base_name.capitalize()} needs a {stone_required_evolutions[regional_key]} to evolve!")
                                can_evolve = False

                # Additional check for Eevee's multiple evolution paths
                if base_name == "eevee":
                    await ctx.send(f"Your Eevee is evolving using {found_item}!")
                    if found_item == "Fire Stone":
                        await ctx.send("It's becoming a Flareon!")
                        target_evolution = 136  # Flareon's Pokedex number
                    elif found_item == "Water Stone":
                        await ctx.send("It's becoming a Vaporeon!")
                        target_evolution = 134  # Vaporeon's Pokedex number
                    elif found_item == "Thunder Stone":
                        await ctx.send("It's becoming a Jolteon!")
                        target_evolution = 135  # Jolteon's Pokedex number

                if not can_evolve:
                    await ctx.send(f"{pokemon_data['name'].capitalize()} can't evolve with a {found_item}!")
                    return
            # Get the evolved form
            evolved_data = await self.fetch_pokemon(target_evolution)
            if not evolved_data:
                await ctx.send("Error fetching evolution data. Please try again.")
                return
                
            # Evolve the Pokemon
            async with self.config.user(user).pokemon() as user_poke:
                pokemon = user_poke[pokemon_id_str]
                
                # Create evolved form
                evolved_id = str(evolved_data["id"])
                user_poke[evolved_id] = {
                    "name": evolved_data["name"],
                    "level": pokemon["level"],
                    "xp": pokemon["xp"],
                    "caught_at": datetime.now().timestamp(),
                    "count": 1,
                    "evolved_from": pokemon_id_str,
                    "evolved_at": datetime.now().timestamp()
                }
                
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
            
            await ctx.send(f"You used a {found_item} on {pokemon_name}! It evolved into {evolved_data['name'].capitalize()}!")
            return
            
        # Mega Stones
        if "ite" in found_item and found_item in [stone for stone in MEGA_STONES.values()]:
            # Check if the stone matches this Pokemon
            correct_stone = False
            # First check simple keys
            for poke_id, stone in MEGA_STONES.items():
                if isinstance(poke_id, int) and stone == found_item and (str(poke_id) == pokemon_id_str or poke_id == pokemon_id):
                    correct_stone = True
                    break
                # Check tuple keys for X/Y variants
                elif isinstance(poke_id, tuple) and stone == found_item and (str(poke_id[0]) == pokemon_id_str or poke_id[0] == pokemon_id):
                    correct_stone = True
                    break
            
            if not correct_stone:
                await ctx.send(f"{found_item} can't be used on {pokemon_data['name'].capitalize()}!")
                return
                
            # Use Mega Stone to transform
            result = await self.activate_form(user, pokemon_id_str, "mega")
            if result["success"]:
                await ctx.send(result["message"])
            else:
                await ctx.send(f"Failed to Mega Evolve: {result['reason']}")
            return
            
        # Primal Orbs
        if found_item in [orb for orb in PRIMAL_ORBS.values()]:
            # Check if the orb matches this Pokemon
            correct_orb = False
            for poke_id, orb in PRIMAL_ORBS.items():
                if orb == found_item and (str(poke_id) == pokemon_id_str or poke_id == pokemon_id):
                    correct_orb = True
                    break
            
            if not correct_orb:
                await ctx.send(f"{found_item} can't be used on {pokemon_data['name'].capitalize()}!")
                return
                
            # Use Primal Orb to transform
            result = await self.activate_form(user, pokemon_id_str, "primal")
            if result["success"]:
                await ctx.send(result["message"])
            else:
                await ctx.send(f"Failed to trigger Primal Reversion: {result['reason']}")
            return
            
        # Dynamax Band
        if found_item == "Dynamax Band":
            # Use Dynamax Band to transform
            form_type = "dynamax"
            # If the Pokemon can Gigantamax, use that instead
            if pokemon_data.get("gigantamax"):
                form_type = "gigantamax"
                
            result = await self.activate_form(user, pokemon_id_str, form_type)
            if result["success"]:
                await ctx.send(result["message"])
            else:
                await ctx.send(f"Failed to Dynamax: {result['reason']}")
            return
            
        # Z-Crystals
        if "Z" in found_item and found_item in [crystal for crystal in Z_CRYSTALS.values()]:
            # Z-Crystals work with any Pokemon of the matching type, or specific Pokemon for special Z-Crystals
            # For simplicity, we'll just show a message
            await ctx.send(f"You held up the {found_item}! {pokemon_data['name'].capitalize()} can now use a Z-Move in battle!")
            return
            
        # If we got here, the item isn't usable on this Pokemon
        await ctx.send(f"{found_item} can't be used on {pokemon_data['name'].capitalize()}!")
    
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
        
        # Get form types if applicable
        user_form_type = user_pokemon_data.get("form_type")
        opponent_form_type = opponent_pokemon_data.get("form_type")
        
        user_pokemon_api = await self.fetch_pokemon(int(user_active_id), user_form_type)
        opponent_pokemon_api = await self.fetch_pokemon(int(opponent_active_id), opponent_form_type)
        
        if not user_pokemon_api or not opponent_pokemon_api:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Format names for display
        user_pokemon_name = self.format_pokemon_name(user_pokemon_api['name'], user_form_type)
        opponent_pokemon_name = self.format_pokemon_name(opponent_pokemon_api['name'], opponent_form_type)
        
        # Create battle request
        battle_msg = await ctx.send(
            f"{opponent.mention}, {ctx.author.name} is challenging you to a Pokemon battle!\n"
            f"{ctx.author.name}'s {user_pokemon_name} (Lv. {user_pokemon_data['level']}) "
            f"vs. your {opponent_pokemon_name} (Lv. {opponent_pokemon_data['level']}).\n"
            f"React with ✅ to accept or ❌ to decline."
        )
        
        await battle_msg.add_reaction("✅")
        await battle_msg.add_reaction("❌")
        
        # Wait for response
        try:
            def check(reaction, reactor):
                return (
                    reactor == opponent
                    and reaction.message.id == battle_msg.id
                    and str(reaction.emoji) in ["✅", "❌"]
                )
                
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            
            if str(reaction.emoji) == "❌":
                await ctx.send(f"{opponent.name} declined the battle challenge.")
                return

            # Battle accepted, let's start!
            await ctx.send(f"Battle between {ctx.author.name} and {opponent.name} is starting!")
            
            # Enhanced battle mechanics with form bonuses
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
            
            # Apply form bonuses
            if user_form_type:
                if user_form_type == "mega":
                    user_power *= 1.5  # 50% boost for Mega Evolution
                elif user_form_type == "primal":
                    user_power *= 1.7  # 70% boost for Primal Reversion
                elif user_form_type == "gmax" or user_form_type == "dynamax":
                    user_power *= 1.6  # 60% boost for Gigantamax/Dynamax
                elif user_form_type in ["alola", "galar", "hisui"]:
                    user_power *= 1.2  # 20% boost for regional forms
            
            if opponent_form_type:
                if opponent_form_type == "mega":
                    opponent_power *= 1.5
                elif opponent_form_type == "primal":
                    opponent_power *= 1.7
                elif opponent_form_type == "gmax" or opponent_form_type == "dynamax":
                    opponent_power *= 1.6
                elif opponent_form_type in ["alola", "galar", "hisui"]:
                    opponent_power *= 1.2
            
            # Add randomness (80-120% of power)
            user_power = int(user_power * random.uniform(0.8, 1.2))
            opponent_power = int(opponent_power * random.uniform(0.8, 1.2))
            
            # Type effectiveness (simplified)
            # This could be expanded with a full type chart
            if user_pokemon_api["types"] and opponent_pokemon_api["types"]:
                user_type = user_pokemon_api["types"][0]
                opponent_type = opponent_pokemon_api["types"][0]
                
                # Complete type matchups chart
                type_chart = {
                    "normal": {
                        "rock": 0.5, "steel": 0.5, "ghost": 0.0
                    },
                    "fire": {
                        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, 
                        "rock": 0.5, "dragon": 0.5, "steel": 2.0
                    },
                    "water": {
                        "fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5
                    },
                    "electric": {
                        "water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5
                    },
                    "grass": {
                        "fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, 
                        "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5
                    },
                    "ice": {
                        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, 
                        "flying": 2.0, "dragon": 2.0, "steel": 0.5
                    },
                    "fighting": {
                        "normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, 
                        "bug": 0.5, "rock": 2.0, "ghost": 0.0, "dark": 2.0, "steel": 2.0, "fairy": 0.5
                    },
                    "poison": {
                        "grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, 
                        "steel": 0.0, "fairy": 2.0
                    },
                    "ground": {
                        "fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, 
                        "bug": 0.5, "rock": 2.0, "steel": 2.0
                    },
                    "flying": {
                        "electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5, "steel": 0.5
                    },
                    "psychic": {
                        "fighting": 2.0, "poison": 2.0, "psychic": 0.5, "dark": 0.0, "steel": 0.5
                    },
                    "bug": {
                        "fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, 
                        "psychic": 2.0, "ghost": 0.5, "dark": 2.0, "steel": 0.5, "fairy": 0.5
                    },
                    "rock": {
                        "fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, 
                        "bug": 2.0, "steel": 0.5
                    },
                    "ghost": {
                        "normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5
                    },
                    "dragon": {
                        "dragon": 2.0, "steel": 0.5, "fairy": 0.0
                    },
                    "dark": {
                        "fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5
                    },
                    "steel": {
                        "fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0, "rock": 2.0, 
                        "steel": 0.5, "fairy": 2.0
                    },
                    "fairy": {
                        "fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0, "dark": 2.0, "steel": 0.5
                    }
                }
                
                # Apply type effectiveness for user attacking opponent
                if user_type in type_chart and opponent_type in type_chart.get(user_type, {}):
                    modifier = type_chart[user_type][opponent_type]
                    user_power = int(user_power * modifier)
                    if modifier > 1:
                        await ctx.send(f"{user_pokemon_name}'s {user_type}-type moves are super effective against {opponent_pokemon_name}!")
                    elif modifier < 1:
                        await ctx.send(f"{user_pokemon_name}'s {user_type}-type moves are not very effective against {opponent_pokemon_name}...")
                    elif modifier == 0:
                        await ctx.send(f"{user_pokemon_name}'s {user_type}-type moves have no effect on {opponent_pokemon_name}!")
                        
                # Apply type effectiveness for opponent attacking user
                if opponent_type in type_chart and user_type in type_chart.get(opponent_type, {}):
                    modifier = type_chart[opponent_type][user_type]
                    opponent_power = int(opponent_power * modifier)
                    if modifier > 1:
                        await ctx.send(f"{opponent_pokemon_name}'s {opponent_type}-type moves are super effective against {user_pokemon_name}!")
                    elif modifier < 1:
                        await ctx.send(f"{opponent_pokemon_name}'s {opponent_type}-type moves are not very effective against {user_pokemon_name}...")
                    elif modifier == 0:
                        await ctx.send(f"{opponent_pokemon_name}'s {opponent_type}-type moves have no effect on {user_pokemon_name}!")
            
            # Create battle embed
            embed = discord.Embed(
                title="Pokemon Battle",
                description=f"{ctx.author.name} vs. {opponent.name}",
                color=0xff0000
            )
            
            embed.add_field(
                name=f"{ctx.author.name}'s Pokemon",
                value=f"{user_pokemon_name} (Lv. {user_pokemon_data['level']})\n"
                    f"HP: {'█' * 10}\nPower: {user_power}",
                inline=True
            )
            
            embed.add_field(
                name=f"{opponent.name}'s Pokemon",
                value=f"{opponent_pokemon_name} (Lv. {opponent_pokemon_data['level']})\n"
                    f"HP: {'█' * 10}\nPower: {opponent_power}",
                inline=True
            )
            
            battle_status = await ctx.send(embed=embed)
            
            # Simulate battle with a delay
            await asyncio.sleep(2)
            
            # Determine winner
            if user_power > opponent_power:
                winner = ctx.author
                winner_pokemon = user_pokemon_name
                loser = opponent
                loser_pokemon = opponent_pokemon_name
                xp_gain = 5 + opponent_pokemon_data["level"] // 2
                winner_id = user_active_id
                
                # Bonus XP for beating higher level Pokemon
                if opponent_pokemon_data["level"] > user_pokemon_data["level"]:
                    level_diff = opponent_pokemon_data["level"] - user_pokemon_data["level"]
                    xp_gain += level_diff * 2
                    await ctx.send(f"Bonus XP for defeating a higher level Pokemon: +{level_diff * 2}!")
            else:
                winner = opponent
                winner_pokemon = opponent_pokemon_name
                loser = ctx.author
                loser_pokemon = user_pokemon_name
                xp_gain = 5 + user_pokemon_data["level"] // 2
                winner_id = opponent_active_id
                
                # Bonus XP for beating higher level Pokemon
                if user_pokemon_data["level"] > opponent_pokemon_data["level"]:
                    level_diff = user_pokemon_data["level"] - opponent_pokemon_data["level"]
                    xp_gain += level_diff * 2
                    await ctx.send(f"Bonus XP for defeating a higher level Pokemon: +{level_diff * 2}!")
                
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
            
            # Add money reward
            money_reward = 10 + random.randint(5, 20)
            async with self.config.user(winner).money() as money:
                money += money_reward
            
            result_embed.add_field(
                name="Money",
                value=f"{winner.name} received ${money_reward} for winning!",
                inline=False
            )
            
            # Random chance for item drop
            if random.random() < 0.3:  # 30% chance
                possible_items = ["Potion", "Super Potion", "Revive", "Rare Candy", "Exp. Candy"]
                
                # Rarer items for higher level battles
                avg_level = (user_pokemon_data["level"] + opponent_pokemon_data["level"]) / 2
                if avg_level > 30:
                    possible_items.extend(["Hyper Potion", "Full Restore", "Max Revive", "PP Up"])
                if avg_level > 50:
                    possible_items.extend(["Max Elixir", "Sacred Ash", "Lucky Egg"])
                    
                    # Small chance for evolution stones
                    if random.random() < 0.1:
                        possible_items.extend(["Fire Stone", "Water Stone", "Thunder Stone", "Leaf Stone", "Moon Stone"])
                
                # Award item to winner
                item = random.choice(possible_items)
                async with self.config.user(winner).items() as items:
                    items[item] = items.get(item, 0) + 1
                
                result_embed.add_field(
                    name="Item Drop",
                    value=f"{winner.name} found a {item}!",
                    inline=False
                )
            
            await battle_status.edit(embed=result_embed)
            
            # Award XP to winner
            async with self.config.user(winner).pokemon() as winner_pokemon_dict:
                if winner_id in winner_pokemon_dict:
                    winner_pokemon_dict[winner_id]["xp"] += xp_gain
                    
                    # Check for level up
                    current_level = winner_pokemon_dict[winner_id]["level"]
                    current_xp = winner_pokemon_dict[winner_id]["xp"]
                    xp_required = current_level**3
                    
                    if current_xp >= xp_required:
                        # Level up!
                        winner_pokemon_dict[winner_id]["level"] += 1
                        winner_pokemon_dict[winner_id]["xp"] = current_xp - xp_required
                        
                        await ctx.send(f"{winner.name}'s {winner_pokemon} leveled up to level {current_level + 1}!")
            
            # Award small consolation XP to loser
            async with self.config.user(loser).pokemon() as loser_pokemon_dict:
                if loser == ctx.author and user_active_id in loser_pokemon_dict:
                    loser_pokemon_dict[user_active_id]["xp"] += 1
                elif loser == opponent and opponent_active_id in loser_pokemon_dict:
                    loser_pokemon_dict[opponent_active_id]["xp"] += 1
        
        except asyncio.TimeoutError:
            await ctx.send(f"{opponent.name} did not respond to the battle challenge.")
    
    @pokemon_commands.command(name="shop")
    async def pokemon_shop(self, ctx: commands.Context):
        """Browse the Pokemon item shop."""
        user = ctx.author
        user_money = await self.config.user(user).money()
        
        # Create shop embed
        embed = discord.Embed(
            title="Pokemon Item Shop",
            description=f"Your balance: ${user_money}",
            color=0xffcc00
        )
        
        # Basic items
        basic_items = [
            {"name": "Potion", "price": 300, "description": "Restores 20 HP"},
            {"name": "Super Potion", "price": 700, "description": "Restores 50 HP"},
            {"name": "Hyper Potion", "price": 1200, "description": "Restores 200 HP"},
            {"name": "Max Potion", "price": 2500, "description": "Fully restores HP"},
            {"name": "Revive", "price": 1500, "description": "Revives a fainted Pokemon with half HP"},
            {"name": "Max Revive", "price": 4000, "description": "Revives a fainted Pokemon with full HP"}
        ]
        
        # Enhancement items
        enhancement_items = [
            {"name": "Rare Candy", "price": 10000, "description": "Instantly raises a Pokemon's level by 1"},
            {"name": "Exp. Candy", "price": 5000, "description": "Gives a Pokemon 100 XP"},
            {"name": "PP Up", "price": 9800, "description": "Increases the PP of a move"}
        ]
        
        # Evolution items
        evolution_items = [
            {"name": "Fire Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Water Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Thunder Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Leaf Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Moon Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Sun Stone", "price": 20000, "description": "Evolves certain Pokemon"},
            {"name": "Shiny Stone", "price": 25000, "description": "Evolves certain Pokemon"},
            {"name": "Dusk Stone", "price": 25000, "description": "Evolves certain Pokemon"},
            {"name": "Dawn Stone", "price": 25000, "description": "Evolves certain Pokemon"}
        ]
        
        # Special items (rare, expensive)
        special_items = [
            {"name": "Lucky Egg", "price": 30000, "description": "Holder earns double XP"},
            {"name": "Dynamax Band", "price": 50000, "description": "Allows a Pokemon to Dynamax"}
        ]
        
        # Add fields for each category
        basic_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in basic_items)
        embed.add_field(name="Basic Items", value=basic_str, inline=False)
        
        enhancement_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in enhancement_items)
        embed.add_field(name="Enhancement Items", value=enhancement_str, inline=False)
        
        evolution_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in evolution_items)
        embed.add_field(name="Evolution Items", value=evolution_str, inline=False)
        
        special_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in special_items)
        embed.add_field(name="Special Items", value=special_str, inline=False)
        
        # Add usage instructions
        embed.set_footer(text="Use !pokemon buy <item> to purchase an item.")
        
        await ctx.send(embed=embed)

    @pokemon_commands.command(name="buy")
    async def buy_item(self, ctx: commands.Context, *, item: str):
        """Buy an item from the Pokemon shop."""
        user = ctx.author
        user_money = await self.config.user(user).money()
        
        # Shop inventory with prices
        shop_inventory = {
            "potion": {"price": 300, "name": "Potion"},
            "super potion": {"price": 700, "name": "Super Potion"},
            "hyper potion": {"price": 1200, "name": "Hyper Potion"},
            "max potion": {"price": 2500, "name": "Max Potion"},
            "revive": {"price": 1500, "name": "Revive"},
            "max revive": {"price": 4000, "name": "Max Revive"},
            "rare candy": {"price": 10000, "name": "Rare Candy"},
            "exp. candy": {"price": 5000, "name": "Exp. Candy"},
            "pp up": {"price": 9800, "name": "PP Up"},
            "fire stone": {"price": 20000, "name": "Fire Stone"},
            "water stone": {"price": 20000, "name": "Water Stone"},
            "thunder stone": {"price": 20000, "name": "Thunder Stone"},
            "leaf stone": {"price": 20000, "name": "Leaf Stone"},
            "moon stone": {"price": 20000, "name": "Moon Stone"},
            "sun stone": {"price": 20000, "name": "Sun Stone"},
            "shiny stone": {"price": 25000, "name": "Shiny Stone"},
            "dusk stone": {"price": 25000, "name": "Dusk Stone"},
            "dawn stone": {"price": 25000, "name": "Dawn Stone"},
            "lucky egg": {"price": 30000, "name": "Lucky Egg"},
            "dynamax band": {"price": 50000, "name": "Dynamax Band"}
        }
        
        # Find the item
        item_key = item.lower()
        item_data = None
        
        for key, data in shop_inventory.items():
            if key == item_key or key in item_key:
                item_data = data
                break
        
        if not item_data:
            await ctx.send(f"Sorry, the item '{item}' is not available in the shop. Use `!pokemon shop` to see available items.")
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

    @pokemon_commands.command(name="money", aliases=["balance", "wallet"])
    async def check_money(self, ctx: commands.Context, user: discord.Member = None):
        """Check your money balance."""
        if user is None:
            user = ctx.author
        
        money = await self.config.user(user).money()
        await ctx.send(f"{user.name}'s balance: ${money}")

    @pokemon_commands.command(name="catch", aliases=["c"])
    async def catch_pokemon(self, ctx: commands.Context, *, pokemon_name: str):
        """Catch a wild Pokemon that has spawned."""
        # Check if there's an active spawn
        if ctx.guild.id not in self.spawns_active:
            await ctx.send("There's no wild Pokemon to catch right now!")
            return

        # Add lock to prevent race conditions
        if ctx.guild.id not in self.pokemon_locks:
            self.pokemon_locks[ctx.guild.id] = asyncio.Lock()

        async with self.pokemon_locks[ctx.guild.id]:
            # Check again inside the lock in case it was caught/fled while waiting
            if ctx.guild.id not in self.spawns_active:
                await ctx.send("There's no wild Pokemon to catch right now!")
                return

            spawn = self.spawns_active[ctx.guild.id]
            pokemon_data = spawn["pokemon"]

            # Normalize the input and expected names for more flexible matching
            input_name = pokemon_name.lower().replace(" ", "").replace("-", "").replace("_", "")
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
            
            # Debug info to help diagnose matching issues
            # print(f"Input: {input_name}, Correct: {correct_name}, Base: {expected_base}, Result: {is_correct}")

            if is_correct:
                # Caught!
                caught_pokemon = self.spawns_active[ctx.guild.id]["pokemon"]
                del self.spawns_active[ctx.guild.id]

                # Add to user's collection
                await self.add_pokemon_to_user(ctx.author, pokemon_data)

                # Award money for catching
                catch_reward = random.randint(100, 500)
                current_money = await self.config.user(ctx.author).money()
                await self.config.user(ctx.author).money.set(current_money + catch_reward)

                # Format display name properly
                display_name = pokemon_data["name"].capitalize()
                if "-" in display_name:
                    base_name, form = display_name.split("-", 1)
                    if form == "mega":
                        display_name = f"Mega {base_name.capitalize()}"
                    elif form in ["mega-x", "mega-y"]:
                        mega_type = form.split("-")[1].upper()
                        display_name = f"Mega {base_name.capitalize()} {mega_type}"
                    elif form == "gmax":
                        display_name = f"Gigantamax {base_name.capitalize()}"
                    elif form in ["alola", "galar", "hisui"]:
                        display_name = f"{form.capitalize()}n {base_name.capitalize()}"

                # Send success message
                embed = discord.Embed(
                    title=f"{ctx.author.name} caught a {display_name}!",
                    description=f"The Pokémon has been added to your collection.\nYou received ${catch_reward} for catching it!",
                    color=0x00ff00
                )
                embed.set_thumbnail(url=pokemon_data["sprite"])
                await ctx.send(embed=embed)
                
                # Random chance for a special item when catching rare Pokemon
                if random.random() < 0.05:  # 5% chance
                    # Determine which item to give based on Pokemon
                    special_item = None
                    
                    # Check if this Pokemon has a mega stone
                    pokemon_id = pokemon_data["id"]
                    # Check for simple ID match
                    if pokemon_id in MEGA_STONES or str(pokemon_id) in MEGA_STONES:
                        mega_stone = MEGA_STONES.get(pokemon_id) or MEGA_STONES.get(str(pokemon_id))
                        if mega_stone and random.random() < 0.3:  # 30% chance if eligible
                            special_item = mega_stone
                    # Check for tuple match (X/Y forms)
                    elif (pokemon_id, "X") in MEGA_STONES:
                        special_item = MEGA_STONES[(pokemon_id, "X")]
                    elif (pokemon_id, "Y") in MEGA_STONES:
                        special_item = MEGA_STONES[(pokemon_id, "Y")]
                    
                    # Check for Z-Crystal based on type
                    if not special_item and "types" in pokemon_data and pokemon_data["types"]:
                        primary_type = pokemon_data["types"][0].capitalize()
                        if primary_type in Z_CRYSTALS and random.random() < 0.3:
                            special_item = Z_CRYSTALS[primary_type]

                    # Check for Primal Orb
                    if not special_item and (pokemon_id in PRIMAL_ORBS or str(pokemon_id) in PRIMAL_ORBS):
                        orb = PRIMAL_ORBS.get(pokemon_id) or PRIMAL_ORBS.get(str(pokemon_id))
                        if orb:
                            special_item = orb

                    # Award the special item if one was selected
                    if special_item:
                        async with self.config.user(ctx.author).items() as items:
                            items[special_item] = items.get(special_item, 0) + 1
                        
                        await ctx.send(f"You found a {special_item} with the Pokemon!")
            else:
                # Helper message for forms
                help_msg = ""
                if "-" in pokemon_data["name"]:
                    base_name, form = pokemon_data["name"].split("-", 1)
                    if form == "mega":
                        help_msg = f"\nHint: Try catching Mega {base_name.capitalize()}"
                    elif form.startswith("mega-"):
                        form_type = form.split("-")[1].upper()
                        help_msg = f"\nHint: Try catching Mega {base_name.capitalize()} {form_type}"
                    elif form == "gmax":
                        help_msg = f"\nHint: Try catching Gigantamax {base_name.capitalize()}"
                
                await ctx.send(f"That's not the right Pokemon name! Try again.{help_msg}")
                
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
                # Format name based on form type
                pokemon_name = pokemon_data["name"].capitalize()
                form_type = pokemon_data.get("form_type")
                
                display_name = self.format_pokemon_name(pokemon_name, form_type)
                level = pokemon_data["level"]
                count = pokemon_data.get("count", 1)
                
                # Mark active Pokemon
                if pokemon_id == active_pokemon_id:
                    display_name = f"**{display_name} (Active)**"
                
                # Add field
                embed.add_field(
                    name=f"#{pokemon_id}: {display_name}",
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
        user_pokemon_data = user_pokemon[pokemon_id_str]
        form_type = user_pokemon_data.get("form_type")
        
        pokemon_data = await self.fetch_pokemon(pokemon_id, form_type)
        
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
        
        # Format name for display
        display_name = self.format_pokemon_name(pokemon_data["name"], form_type)
        
        # Create embed
        embed = discord.Embed(
            title=f"#{pokemon_data['id']}: {display_name}",
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
        
        # Form info if applicable
        if form_type:
            form_descriptions = {
                "mega": "This Pokemon has undergone Mega Evolution, which greatly enhances its power.",
                "mega-x": "This Pokemon has undergone Mega Evolution (X form), which greatly enhances its power.",
                "mega-y": "This Pokemon has undergone Mega Evolution (Y form), which greatly enhances its power.",
                "primal": "This Pokemon has undergone Primal Reversion, returning to its ancient form with immense power.",
                "gmax": "This Pokemon can Gigantamax, growing to enormous size with special G-Max moves.",
                "alola": "This is an Alolan form, adapted to the unique environment of the Alola region.",
                "galar": "This is a Galarian form, adapted to the unique environment of the Galar region.",
                "hisui": "This is a Hisuian form, from ancient times in the Hisui region (now known as Sinnoh)."
            }
            
            if form_type in form_descriptions:
                embed.add_field(
                    name="Special Form",
                    value=form_descriptions[form_type],
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
        if pokemon_data.get("evolves_to") and pokemon_data.get("evolves_at_level"):
            evolution_data = await self.fetch_pokemon(pokemon_data["evolves_to"])
            if evolution_data:
                evo_method = "level"
                if pokemon_data.get("evolution_condition"):
                    evo_method = pokemon_data["evolution_condition"]
                
                embed.add_field(
                    name="Evolution",
                    value=f"Evolves into {evolution_data['name'].capitalize()} at level {pokemon_data['evolves_at_level']} ({evo_method})",
                    inline=False
                )
        
        # Mega evolution info if available
        base_pokemon_id = user_pokemon_data.get("base_pokemon", pokemon_id_str)
        base_pokemon_data = await self.fetch_pokemon(int(base_pokemon_id))
        
        if base_pokemon_data and base_pokemon_data.get("mega_evolution") and not form_type == "mega":
            embed.add_field(
                name="Mega Evolution",
                value=f"This Pokemon can Mega Evolve with a compatible Mega Stone.",
                inline=False
            )
        
        # Show special form availability
        if not form_type:
            available_forms = []
            
            # Check for Mega Evolution
            if pokemon_data.get("mega_evolution"):
                available_forms.append("Mega Evolution")
            
            # Check for Primal Reversion
            if pokemon_data.get("primal_reversion"):
                available_forms.append("Primal Reversion")
            
            # Check for Gigantamax
            if pokemon_data.get("gigantamax"):
                available_forms.append("Gigantamax")
            
            if available_forms:
                embed.add_field(
                    name="Available Forms",
                    value=", ".join(available_forms),
                    inline=False
                )
        
        # Nickname if set
        nickname = user_pokemon_data.get("nickname")
        if nickname:
            embed.add_field(
                name="Nickname",
                value=nickname,
                inline=True
            )
        
        # Caught date
        caught_at = user_pokemon_data.get("caught_at")
        if caught_at:
            caught_date = datetime.fromtimestamp(caught_at).strftime('%Y-%m-%d')
            embed.add_field(
                name="Caught on",
                value=caught_date,
                inline=True
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
        
        # Get proper display name
        form_type = user_pokemon[pokemon_id_str].get("form_type")
        pokemon_data = await self.fetch_pokemon(pokemon_id, form_type)
        
        if pokemon_data:
            display_name = self.format_pokemon_name(pokemon_data["name"], form_type)
        else:
            display_name = user_pokemon[pokemon_id_str]["name"].capitalize()
        
        await ctx.send(f"{display_name} is now your active Pokemon!")

    @pokemon_commands.command(name="dex", aliases=["pokedex", "d"])
    async def pokedex(self, ctx: commands.Context, pokemon_id: int = None):
        """View Pokedex information about a Pokemon."""
        if pokemon_id is None:
            # Show user's Pokedex completion
            user_pokemon = await self.config.user(ctx.author).pokemon()
            
            # Count unique base Pokemon (ignore forms)
            unique_pokemon = set()
            for pokemon_id, pokemon_data in user_pokemon.items():
                # Extract base Pokemon ID
                if "-" in pokemon_data["name"]:
                    # This is a form, get the base Pokemon
                    if "base_pokemon" in pokemon_data:
                        unique_pokemon.add(pokemon_data["base_pokemon"])
                    else:
                        # Try to extract base ID from name
                        unique_pokemon.add(pokemon_id)
                else:
                    unique_pokemon.add(pokemon_id)
            
            total_caught = len(unique_pokemon)
            
            embed = discord.Embed(
                title=f"{ctx.author.name}'s Pokedex",
                description=f"You've caught {total_caught}/898 unique Pokemon ({total_caught/8.98:.1f}%)",
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
        
        # Check both direct ID and any forms
        has_caught = str(pokemon_id) in user_pokemon
        
        # Also check for forms of this Pokemon
        if not has_caught:
            for pid, pdata in user_pokemon.items():
                if pdata.get("base_pokemon") == str(pokemon_id):
                    has_caught = True
                    break
        
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
        
        # Special forms info
        forms = []
        
        if pokemon_data.get("mega_evolution"):
            forms.append("Mega Evolution")
        
        if pokemon_data.get("primal_reversion"):
            forms.append("Primal Reversion")
        
        if pokemon_data.get("gigantamax"):
            forms.append("Gigantamax")
        
        if forms:
            embed.add_field(
                name="Special Forms",
                value=", ".join(forms),
                inline=False
            )
        
        # Evolution info
        if pokemon_data.get("evolves_to"):
            evolution_data = await self.fetch_pokemon(pokemon_data["evolves_to"])
            if evolution_data:
                evo_info = f"Evolves into {evolution_data['name'].capitalize()}"
                
                if pokemon_data.get("evolves_at_level"):
                    evo_info += f" at level {pokemon_data['evolves_at_level']}"
                    
                if pokemon_data.get("evolution_condition"):
                    evo_info += f" ({pokemon_data['evolution_condition']})"
                    
                embed.add_field(
                    name="Evolution",
                    value=evo_info,
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
        your_pokemon_data = your_pokemon[your_pokemon_id_str]
        their_pokemon_data = their_pokemon[their_pokemon_id_str]
        
        # Get form types if applicable
        your_form_type = your_pokemon_data.get("form_type")
        their_form_type = their_pokemon_data.get("form_type")
        
        your_pokemon_api = await self.fetch_pokemon(int(your_pokemon_id), your_form_type)
        their_pokemon_api = await self.fetch_pokemon(int(their_pokemon_id), their_form_type)
        
        if not your_pokemon_api or not their_pokemon_api:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
            
        # Format names for display
        your_pokemon_name = self.format_pokemon_name(your_pokemon_api['name'], your_form_type)
        their_pokemon_name = self.format_pokemon_name(their_pokemon_api['name'], their_form_type)
        
        # Create trade request
        trade_msg = await ctx.send(
            f"{user.mention}, {ctx.author.name} is offering to trade their {your_pokemon_name} (Lv. {your_pokemon_data['level']}) "
            f"for your {their_pokemon_name} (Lv. {their_pokemon_data['level']}).\n"
            f"React with ✅ to accept or ❌ to decline."
        )
        
        await trade_msg.add_reaction("✅")
        await trade_msg.add_reaction("❌")
        
        # Wait for response
        try:
            def check(reaction, reactor):
                return (
                    reactor == user
                    and reaction.message.id == trade_msg.id
                    and str(reaction.emoji) in ["✅", "❌"]
                )
                
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            
            if str(reaction.emoji) == "❌":
                await ctx.send(f"{user.name} declined the trade offer.")
                return
                
            # Trade accepted, let's execute it
            # Check if either Pokemon is active
            your_active = await self.config.user(ctx.author).active_pokemon() == your_pokemon_id_str
            their_active = await self.config.user(user).active_pokemon() == their_pokemon_id_str
            
            # Execute the trade
            async with self.config.user(ctx.author).pokemon() as your_pokemon_dict:
                your_pokemon_temp = your_pokemon_dict[your_pokemon_id_str].copy()
                del your_pokemon_dict[your_pokemon_id_str]
                
            async with self.config.user(user).pokemon() as their_pokemon_dict:
                their_pokemon_temp = their_pokemon_dict[their_pokemon_id_str].copy()
                del their_pokemon_dict[their_pokemon_id_str]
                
            # Add the traded Pokemon
            async with self.config.user(ctx.author).pokemon() as your_pokemon_dict:
                your_pokemon_dict[their_pokemon_id_str] = their_pokemon_temp
                
            async with self.config.user(user).pokemon() as their_pokemon_dict:
                their_pokemon_dict[your_pokemon_id_str] = your_pokemon_temp
                
            # Update active Pokemon if needed
            if your_active:
                await self.config.user(ctx.author).active_pokemon.set(their_pokemon_id_str)
                
            if their_active:
                await self.config.user(user).active_pokemon.set(your_pokemon_id_str)
                
            # Send confirmation
            embed = discord.Embed(
                title="Trade Completed!",
                description=f"{ctx.author.name} traded {your_pokemon_name} for {user.name}'s {their_pokemon_name}!",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
            
        except asyncio.TimeoutError:
            await ctx.send("Trade offer expired.")

    @pokemon_commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context):
        """Show the Pokemon trainer leaderboard."""
        guild = ctx.guild

        # Get all users in the guild
        all_users_data = await self.config.all_users()
        
        all_users = {}

        for user_id, user_data in all_users_data.items():
            member = guild.get_member(user_id)
            if member and "pokemon" in user_data:
                # Count total Pokemon and calculate trainer score
                pokemon_count = len(user_data["pokemon"])

                # Calculate total levels
                total_levels = sum(pokemon["level"] for pokemon in user_data["pokemon"].values())

                # Count special forms
                special_forms = sum(1 for p in user_data["pokemon"].values() if p.get("form_type"))

                # Calculate trainer score (Pokemon count + total levels + special forms)
                trainer_score = pokemon_count + total_levels + (special_forms * 3)  # Special forms worth extra points

                all_users[member] = {
                    "pokemon_count": pokemon_count,
                    "total_levels": total_levels,
                    "special_forms": special_forms,
                    "trainer_score": trainer_score,
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
                      f"Special Forms: {data['special_forms']}\n"
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
            pokemon_data = user_pokemon[pokemon_id_str]
            form_type = pokemon_data.get("form_type")
            
            # Fetch API data for proper name display
            api_data = await self.fetch_pokemon(pokemon_id, form_type)
            if not api_data:
                await ctx.send("Error fetching Pokemon data. Please try again.")
                return
                
            # Format name for display
            pokemon_name = self.format_pokemon_name(api_data["name"], form_type)
            
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
            pokemon_data = your_pokemon[pokemon_id_str]
            form_type = pokemon_data.get("form_type")
            
            # Get API data
            api_data = await self.fetch_pokemon(pokemon_id, form_type)
            if not api_data:
                await ctx.send("Error fetching Pokemon data. Please try again.")
                return
                
            # Format name for display
            pokemon_name = self.format_pokemon_name(api_data["name"], form_type)
            
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
                
            # Get Pokemon data
            pokemon_data = user_pokemon[pokemon_id_str]
            form_type = pokemon_data.get("form_type")
            
            # Get API data for proper name display
            api_data = await self.fetch_pokemon(pokemon_id, form_type)
            
            # Format name for display
            if api_data:
                display_name = self.format_pokemon_name(api_data["name"], form_type)
            else:
                display_name = pokemon_data["name"].capitalize()
                
            # Set nickname
            user_pokemon[pokemon_id_str]["nickname"] = nickname
            
            await ctx.send(f"Your {display_name} is now known as \"{nickname}\"!")
            
    @pokemon_commands.command(name="daily")
    @commands.cooldown(1, 86400, commands.BucketType.user)  # Once per day
    async def daily_reward(self, ctx: commands.Context):
        """Claim your daily reward."""
        user = ctx.author
        
        # Create embed for rewards
        embed = discord.Embed(
            title="Daily Reward!",
            description=f"Here are your daily rewards, {user.name}!",
            color=0xffcc00
        )
        
        # Money reward - FIXED
        money_reward = random.randint(500, 2000)
        current_money = await self.config.user(user).money()
        await self.config.user(user).money.set(current_money + money_reward)
                
        embed.add_field(
            name="Money",
            value=f"You received ${money_reward}!",
            inline=False
        )
        
        # Random XP bonus for active Pokemon
        active_pokemon_id = await self.config.user(user).active_pokemon()
        
        if active_pokemon_id:
            xp_bonus = random.randint(20, 50)
            
            # FIXED: Get Pokemon data first
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
                level_up = False
                
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
                pokemon_data = await self.fetch_pokemon(int(active_pokemon_id), form_type)
                
                if pokemon_data:
                    pokemon_name = self.format_pokemon_name(pokemon_data["name"], form_type)
                else:
                    pokemon_name = active_pokemon["name"].capitalize()
                
                # Add field to embed
                if level_up:
                    embed.add_field(
                        name="Pokemon Training",
                        value=f"Your {active_pokemon.get('nickname', pokemon_name)} gained {xp_bonus} XP and leveled up to level {new_level}!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Pokemon Training",
                        value=f"Your {active_pokemon.get('nickname', pokemon_name)} gained {xp_bonus} XP!",
                        inline=False
                    )
        
        # Random item reward
        if random.random() < 0.7:  # 70% chance
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
            user_pokemon = await self.config.user(user).pokemon()
            highest_level = 0
            
            # FIXED: Check if user_pokemon is not empty
            if user_pokemon:
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
            
            # If user has max evolution Pokemon, add special items
            if highest_level >= 50:
                # Check for possible Mega Evolution candidates
                has_mega_candidate = False
                mega_candidates = []
                
                for pokemon_id in user_pokemon:
                    pokemon_data = await self.fetch_pokemon(int(pokemon_id))
                    if pokemon_data and pokemon_data.get("mega_evolution"):
                        has_mega_candidate = True
                        
                        # Check both direct ID matches and tuple matches for X/Y variants
                        mega_stone = None
                        if int(pokemon_id) in MEGA_STONES:
                            mega_stone = MEGA_STONES[int(pokemon_id)]
                        elif (int(pokemon_id), "X") in MEGA_STONES:
                            mega_stone = MEGA_STONES[(int(pokemon_id), "X")]
                        elif (int(pokemon_id), "Y") in MEGA_STONES:
                            mega_stone = MEGA_STONES[(int(pokemon_id), "Y")]
                            
                        if mega_stone:
                            mega_candidates.append({"name": mega_stone, "weight": 1})
                
                if mega_candidates and random.random() < MEGA_STONE_CHANCE:
                    possible_items.extend(mega_candidates)
            
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
            
            # Award the item - FIXED
            user_items = await self.config.user(user).items()
            if chosen_item in user_items:
                user_items[chosen_item] += 1
            else:
                user_items[chosen_item] = 1
            await self.config.user(user).items.set(user_items)
                
            embed.add_field(
                name="Item",
                value=f"You received a {chosen_item}!",
                inline=False
            )
            
        # Chance to get a random Pokemon (10%)
        if random.random() < 0.1:
            # Generate a random Pokemon (favoring lower numbers for common Pokemon)
            pokemon_id = min(int(random.triangular(1, 898, 150)), 898)  # Triangular distribution favoring lower IDs
            
            # Fetch Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            
            if pokemon_data:
                # Add to user's collection
                await self.add_pokemon_to_user(user, pokemon_data)
                
                embed.add_field(
                    name="Pokemon Encounter",
                    value=f"You found a wild {pokemon_data['name'].capitalize()}!",
                    inline=False
                )
                embed.set_thumbnail(url=pokemon_data["sprite"])
                
        await ctx.send(embed=embed)

    @pokemon_commands.command(name="event")
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
            # List of legendary Pokemon IDs
            legendary_ids = [
                # Gen 1 - Kanto
                144, 145, 146,  # Articuno, Zapdos, Moltres
                150, 151,       # Mewtwo, Mew
                
                # Gen 2 - Johto
                243, 244, 245,  # Raikou, Entei, Suicune
                249, 250, 251,  # Lugia, Ho-Oh, Celebi
                
                # Gen 3 - Hoenn
                377, 378, 379,  # Regirock, Regice, Registeel
                380, 381,       # Latias, Latios
                382, 383, 384,  # Kyogre, Groudon, Rayquaza
                385, 386,       # Jirachi, Deoxys
                
                # Gen 4 - Sinnoh
                480, 481, 482,  # Uxie, Mesprit, Azelf
                483, 484,       # Dialga, Palkia
                485, 486,       # Heatran, Regigigas
                487, 488, 489,  # Giratina, Cresselia, Phione
                490, 491, 492,  # Manaphy, Darkrai, Shaymin
                493,            # Arceus
                
                # Gen 5 - Unova
                494, 495,       # Victini, Cobalion
                638, 639, 640,  # Cobalion, Terrakion, Virizion
                641, 642, 643,  # Tornadus, Thundurus, Reshiram
                644, 645, 646,  # Zekrom, Landorus, Kyurem
                647, 648, 649,  # Keldeo, Meloetta, Genesect
                
                # Gen 6 - Kalos
                716, 717, 718,  # Xerneas, Yveltal, Zygarde
                719, 720, 721,  # Diancie, Hoopa, Volcanion
                
                # Gen 7 - Alola
                772, 773,       # Type: Null, Silvally
                785, 786, 787, 788,  # Tapu Koko, Tapu Lele, Tapu Bulu, Tapu Fini
                789, 790, 791, 792,  # Cosmog, Cosmoem, Solgaleo, Lunala
                793, 794, 795, 796, 797,  # Nihilego, Buzzwole, Pheromosa, Xurkitree, Celesteela
                798, 799, 800,  # Kartana, Guzzlord, Necrozma
                801, 802,       # Magearna, Marshadow
                
                # Gen 8 - Galar
                888, 889, 890,  # Zacian, Zamazenta, Eternatus
                891, 892, 893, 894, 895, 896, 897, 898  # Kubfu, Urshifu, Zarude, Regieleki, Regidrago, Glastrier, Spectrier, Calyrex
            ]
            
            # Choose a random legendary
            pokemon_id = random.choice(legendary_ids)
            
            # Get Pokemon data
            pokemon_data = await self.fetch_pokemon(pokemon_id)
            
            if not pokemon_data:
                await ctx.send("Error fetching legendary Pokemon data. Please try again.")
                return
                
            # Get spawn channel
            guild_config = await self.config.guild(ctx.guild).all()
            channel_id = guild_config["channel"]
            
            if not channel_id:
                await ctx.send("No spawn channel set! Use `!pokemon settings channel` first.")
                return
                
            channel = ctx.guild.get_channel(channel_id)
            if not channel:
                await ctx.send("Spawn channel no longer exists! Please set a new one.")
                return
                
            # Create special announcement
            embed = discord.Embed(
                title="⚡ LEGENDARY POKEMON ALERT ⚡",
                description=f"A wild {pokemon_data['name'].capitalize()} has appeared!\nType `!catch {pokemon_data['name']}` to catch it!",
                color=0xff0000
            )
            
            embed.set_image(url=pokemon_data["sprite"])
            
            # Set longer expiry time for legendary (2 minutes)
            now = datetime.now().timestamp()
            expiry = now + 120  # 2 minutes
            
            # Store active spawn
            self.spawns_active[ctx.guild.id] = {
                "pokemon": pokemon_data,
                "expiry": expiry
            }
            
            # Update last spawn time
            await self.config.guild(ctx.guild).last_spawn.set(now)
            
            # Send spawn message
            await channel.send(embed=embed)
            
            # Announce in the command channel if different
            if channel.id != ctx.channel.id:
                await ctx.send(f"A legendary Pokemon has appeared in {channel.mention}!")
            
            # Set up expiry task
            self.bot.loop.create_task(self.expire_spawn(ctx.guild.id, channel, expiry))
            
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
            
        elif event_type == "megaday":
            # Temporary boost to mega stone drop rates
            # Store original rates for later restoration
            global MEGA_STONE_CHANCE
            original_mega_chance = MEGA_STONE_CHANCE
            
            # Boost rates by 5x (with a maximum of 50%)
            MEGA_STONE_CHANCE = min(MEGA_STONE_CHANCE * 5, 0.5)
            
            # Create scheduled task to reset rates
            async def reset_mega_rates():
                await asyncio.sleep(7200)  # 2 hours
                
                global MEGA_STONE_CHANCE
                MEGA_STONE_CHANCE = original_mega_chance
                
                # Get the channel
                channel = ctx.guild.get_channel(ctx.channel.id)
                if channel:
                    await channel.send("The Mega Evolution Day event has ended. Mega Stone find rates have returned to normal.")
            
            # Start reset task
            self.bot.loop.create_task(reset_mega_rates())
            
            # Give all active users in the guild a guaranteed mega stone
            active_members = [member for member in ctx.guild.members if not member.bot]
            
            for member in active_members:
                # Check if they have Pokemon
                user_pokemon = await self.config.user(member).pokemon()
                if not user_pokemon:
                    continue
                    
                # Find a Pokemon that can mega evolve
                mega_candidates = []
                for pokemon_id in user_pokemon:
                    # Check for regular single mega forms
                    if int(pokemon_id) in MEGA_STONES:
                        mega_stone = MEGA_STONES[int(pokemon_id)]
                        mega_candidates.append(mega_stone)
                    # Check for X/Y variants
                    elif (int(pokemon_id), "X") in MEGA_STONES:
                        mega_stone = MEGA_STONES[(int(pokemon_id), "X")]
                        mega_candidates.append(mega_stone)
                    elif (int(pokemon_id), "Y") in MEGA_STONES:
                        mega_stone = MEGA_STONES[(int(pokemon_id), "Y")]
                        mega_candidates.append(mega_stone)
                
                if mega_candidates:
                    # Award a random mega stone they can use
                    mega_stone = random.choice(mega_candidates)
                    
                    async with self.config.user(member).items() as items:
                        items[mega_stone] = items.get(mega_stone, 0) + 1
                    
                    try:
                        await member.send(f"You received a {mega_stone} as part of the Mega Evolution Day event!")
                    except:
                        pass  # Ignore if DM fails
            
            # Announce the event
            embed = discord.Embed(
                title="🌟 Mega Evolution Day Started! 🌟",
                description="For the next 2 hours, Mega Stone drop rates are significantly increased!",
                color=0xff00ff
            )
            
            embed.add_field(
                name="Event Bonuses",
                value=f"Mega Stone Find Rate: {original_mega_chance*100:.1f}% → {MEGA_STONE_CHANCE*100:.1f}%\nActive trainers received a Mega Stone for one of their Pokemon!",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        elif event_type == "typefocus":
            # Ask which type to focus
            available_types = [
                "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting", "Poison", 
                "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", 
                "Steel", "Fairy"
            ]
            
            embed = discord.Embed(
                title="Type Focus Event",
                description="Which type would you like to focus on? Reply with one of the following types:",
                color=0x3498db
            )
            
            embed.add_field(
                name="Available Types",
                value=", ".join(available_types),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Wait for response
            try:
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel
                    
                response = await self.bot.wait_for("message", check=check, timeout=30)
                
                chosen_type = response.content.capitalize()
                
                if chosen_type not in available_types:
                    await ctx.send(f"Invalid type: {chosen_type}. Event cancelled.")
                    return
                    
                # Store type focus for 2 hours
                # In a real implementation, you'd need a way to track this and modify the spawn logic
                
                # Announce the event
                embed = discord.Embed(
                    title=f"🔍 {chosen_type}-Type Focus Event Started! 🔍",
                    description=f"For the next 2 hours, {chosen_type}-type Pokemon will spawn more frequently!",
                    color=0x3498db
                )
                
                await ctx.send(embed=embed)
                
                # Schedule end of event
                async def end_type_focus():
                    await asyncio.sleep(7200)  # 2 hours
                    
                    # Get the channel
                    channel = ctx.guild.get_channel(ctx.channel.id)
                    if channel:
                        await channel.send(f"The {chosen_type}-Type Focus Event has ended. Pokemon spawns have returned to normal.")
                
                # Start the scheduled task
                self.bot.loop.create_task(end_type_focus())
                
                # Force spawn a Pokemon of the chosen type
                type_pokemon_ids = {}  # Dict to store Pokemon IDs by type
                
                # If we haven't loaded this type's Pokemon before, do it now
                if chosen_type.lower() not in type_pokemon_ids:
                    # Build a list of Pokemon of this type
                    type_pokemon_ids[chosen_type.lower()] = []
                    
                    # This would be more efficient with a pre-built type mapping
                    # For simplicity, we'll check the first 500 Pokemon
                    for pid in range(1, 500):
                        pokemon_data = await self.fetch_pokemon(pid)
                        if pokemon_data and 'types' in pokemon_data:
                            if any(t.lower() == chosen_type.lower() for t in pokemon_data['types']):
                                type_pokemon_ids[chosen_type.lower()].append(pid)
                
                # Force spawn a Pokemon of this type
                if type_pokemon_ids[chosen_type.lower()]:
                    pokemon_id = random.choice(type_pokemon_ids[chosen_type.lower()])
                    pokemon_data = await self.fetch_pokemon(pokemon_id)
                    
                    if pokemon_data:
                        # Get spawn channel
                        guild_config = await self.config.guild(ctx.guild).all()
                        channel_id = guild_config["channel"]
                        
                        if channel_id:
                            channel = ctx.guild.get_channel(channel_id)
                            if channel:
                                # Create spawn embed
                                embed = discord.Embed(
                                    title=f"A wild {chosen_type}-type Pokémon appeared!",
                                    description=f"Type `!catch <pokemon>` to catch it!",
                                    color=0x00ff00
                                )
                                
                                embed.set_image(url=pokemon_data["sprite"])
                                
                                # Set expiry time
                                now = datetime.now().timestamp()
                                expiry = now + CATCH_TIMEOUT
                                
                                # Store active spawn
                                self.spawns_active[ctx.guild.id] = {
                                    "pokemon": pokemon_data,
                                    "expiry": expiry
                                }
                                
                                # Update last spawn time
                                await self.config.guild(ctx.guild).last_spawn.set(now)
                                
                                # Send spawn message
                                await channel.send(embed=embed)
                                
                                # Set up expiry task
                                self.bot.loop.create_task(self.expire_spawn(ctx.guild.id, channel, expiry))
                
            except asyncio.TimeoutError:
                await ctx.send("Type Focus event setup timed out.")
                
        elif event_type == "shinyhunt":
            # Shiny hunt event - this would require implementing shiny Pokemon functionality
            embed = discord.Embed(
                title="✨ Shiny Hunt Event ✨",
                description="This event would enable the chance to catch shiny Pokemon with different coloration!",
                color=0xffd700
            )
            
            embed.add_field(
                name="Feature Not Implemented",
                value="The Shiny Hunt event requires implementation of shiny Pokemon functionality.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        else:
            await ctx.send(f"Unknown event type: {event_type}")

    @pokemon_commands.command(name="forms")
    async def view_forms(self, ctx: commands.Context, pokemon_id: int):
        """View all available forms for a Pokemon."""
        # Fetch the base Pokemon first
        base_pokemon = await self.fetch_pokemon(pokemon_id)
        
        if not base_pokemon:
            await ctx.send(f"Pokemon #{pokemon_id} not found.")
            return
        
        # Check if this Pokemon has forms
        if not base_pokemon.get("forms") and not base_pokemon.get("mega_evolution") and not base_pokemon.get("primal_reversion") and not base_pokemon.get("gigantamax"):
            await ctx.send(f"{base_pokemon['name'].capitalize()} doesn't have any special forms.")
            return
        
        # Fetch all available forms
        all_forms = await self.fetch_all_forms(pokemon_id)
        
        # Create embed
        embed = discord.Embed(
            title=f"Forms of {base_pokemon['name'].capitalize()}",
            description=f"Pokemon #{pokemon_id} has {len(all_forms)} form(s).",
            color=0x9b59b6
        )
        
        # Add each form
        for i, form in enumerate(all_forms):
            form_name = form["name"]
            form_type = None
            
            # Determine form type from name
            if "-" in form_name:
                base_name, form_suffix = form_name.split("-", 1)
                if form_suffix == "mega":
                    form_type = "Mega Evolution"
                elif form_suffix.startswith("mega-"):
                    form_type = f"Mega Evolution ({form_suffix[-1].upper()})"
                elif form_suffix == "gmax":
                    form_type = "Gigantamax"
                elif form_suffix == "primal":
                    form_type = "Primal Reversion"
                elif form_suffix in ["alola", "galar", "hisui"]:
                    form_type = f"{form_suffix.capitalize()}n Form"
                else:
                    form_type = f"{form_suffix.capitalize()} Form"
            else:
                form_type = "Base Form"
            
            # Add stats comparison if this is not the base form
            stats_comparison = ""
            if i > 0:
                base_stats = all_forms[0]["stats"]
                this_stats = form["stats"]
                
                # Compare each stat
                for stat_name, base_val in base_stats.items():
                    if stat_name in this_stats:
                        diff = this_stats[stat_name] - base_val
                        if diff != 0:
                            stats_comparison += f"{stat_name.capitalize()}: {base_val} → {this_stats[stat_name]} ({'+' if diff > 0 else ''}{diff})\n"
            
            embed.add_field(
                name=f"{i+1}. {self.format_pokemon_name(form['name'])}",
                value=f"**Type**: {', '.join(t.capitalize() for t in form['types'])}\n"
                    f"**Form Type**: {form_type}\n"
                    f"{stats_comparison if stats_comparison else ''}",
                inline=False
            )
        
        # Add information about how to obtain forms
        form_info = ""
        if base_pokemon.get("mega_evolution"):
            form_info += "**Mega Evolution**: Requires a Mega Stone\n"
        if base_pokemon.get("primal_reversion"):
            form_info += "**Primal Reversion**: Requires a Primal Orb\n"
        if base_pokemon.get("gigantamax"):
            form_info += "**Gigantamax**: Requires a Dynamax Band\n"
        
        if form_info:
            embed.add_field(
                name="How to Obtain",
                value=form_info,
                inline=False
            )
        
        await ctx.send(embed=embed)

    @pokemon_commands.command(name="evolve")
    async def evolve_pokemon(self, ctx: commands.Context, pokemon_id: int):
        """Attempt to evolve a Pokemon through level-up."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Get user's Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Get Pokemon data
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
        
        # Check if this Pokemon can evolve
        if not pokemon_data.get("evolves_to"):
            await ctx.send(f"{pokemon_data['name'].capitalize()} cannot evolve further.")
            return
        
        # Check evolution conditions
        can_evolve = False
        evolution_message = ""
        
        # Level-up evolution
        if pokemon_data.get("evolves_at_level"):
            required_level = pokemon_data["evolves_at_level"]
            current_level = user_pokemon[pokemon_id_str]["level"]
            
            if current_level >= required_level:
                can_evolve = True
                evolution_message = f"{pokemon_data['name'].capitalize()} meets the level requirement (Level {current_level}/{required_level})."
            else:
                evolution_message = f"{pokemon_data['name'].capitalize()} needs to reach level {required_level} to evolve (current: {current_level})."
        
        # Item-based evolution
        elif pokemon_data.get("evolution_item"):
            required_item = pokemon_data["evolution_item"]
            
            # Check if user has the item
            user_items = await self.config.user(user).items()
            if required_item in user_items and user_items[required_item] > 0:
                can_evolve = True
                evolution_message = f"{pokemon_data['name'].capitalize()} can evolve with {required_item}."
                
                # Use up the item
                async with self.config.user(user).items() as items:
                    items[required_item] -= 1
                    if items[required_item] <= 0:
                        del items[required_item]
            else:
                evolution_message = f"{pokemon_data['name'].capitalize()} needs a {required_item} to evolve, but you don't have one."
        
        # Trade evolution
        elif pokemon_data.get("evolution_condition") and "trade" in pokemon_data["evolution_condition"]:
            evolution_message = f"{pokemon_data['name'].capitalize()} evolves through trading. Use the trade command instead."
        
        # Other conditional evolutions
        elif pokemon_data.get("evolution_condition"):
            evolution_message = f"{pokemon_data['name'].capitalize()} evolves under special conditions: {pokemon_data['evolution_condition']}"
        
        # No known evolution method
        else:
            evolution_message = f"{pokemon_data['name'].capitalize()} has an unknown evolution method."
        
        # If we can evolve, do it
        if can_evolve:
            # Get evolution data
            evolution_id = pokemon_data["evolves_to"]
            evolution_data = await self.fetch_pokemon(evolution_id)
            
            if not evolution_data:
                await ctx.send(f"Error fetching evolution data for {pokemon_data['name'].capitalize()}. Please try again.")
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
                
                # Remove pre-evolution or decrement count
                if pokemon["count"] > 1:
                    pokemon["count"] -= 1
                else:
                    del user_poke[pokemon_id_str]
                    
                # Update active Pokemon if needed
                if await self.config.user(user).active_pokemon() == pokemon_id_str:
                    await self.config.user(user).active_pokemon.set(evolved_id)
            
            # Send evolution message
            embed = discord.Embed(
                title="Evolution",
                description=f"Congratulations! Your {pokemon_data['name'].capitalize()} evolved into {evolution_data['name'].capitalize()}!",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
        else:
            # Send message about why it can't evolve
            await ctx.send(evolution_message)

    @pokemon_commands.command(name="mega")
    async def mega_evolve(self, ctx: commands.Context, pokemon_id: int):
        """Mega evolve a Pokemon using a Mega Stone."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Attempt to activate the mega form
        result = await self.activate_form(user, pokemon_id_str, "mega")
        
        if result["success"]:
            # Get the mega form data
            mega_form = result["form"]
            
            # Create embed
            embed = discord.Embed(
                title="Mega Evolution",
                description=result["message"],
                color=0xff00ff
            )
            
            # Add stat changes
            if "stats" in mega_form:
                # Fetch base form for comparison
                base_form = await self.fetch_pokemon(pokemon_id)
                if base_form and "stats" in base_form:
                    stat_changes = []
                    for stat_name, mega_val in mega_form["stats"].items():
                        if stat_name in base_form["stats"]:
                            base_val = base_form["stats"][stat_name]
                            diff = mega_val - base_val
                            if diff != 0:
                                stat_changes.append(f"{stat_name.capitalize()}: {base_val} → {mega_val} ({'+' if diff > 0 else ''}{diff})")
                    
                    if stat_changes:
                        embed.add_field(
                            name="Stat Changes",
                            value="\n".join(stat_changes),
                            inline=False
                        )
            
            # Add duration info
            embed.add_field(
                name="Duration",
                value="Mega Evolution lasts for 1 hour, or until the Pokemon is switched out.",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Mega Evolution failed: {result['reason']}")

    @pokemon_commands.command(name="dynamax")
    async def dynamax_pokemon(self, ctx: commands.Context, pokemon_id: int):
        """Dynamax or Gigantamax a Pokemon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Get Pokemon data to check if it can Gigantamax
        pokemon_data = await self.fetch_pokemon(pokemon_id)
        if not pokemon_data:
            await ctx.send("Error fetching Pokemon data. Please try again.")
            return
        
        # Determine form type
        form_type = "gigantamax" if pokemon_data.get("gigantamax") else "dynamax"
        
        # Attempt to activate the form
        result = await self.activate_form(user, pokemon_id_str, form_type)
        
        if result["success"]:
            # Create embed
            embed = discord.Embed(
                title="Dynamax",
                description=result["message"],
                color=0xff0000
            )
            
            # Add special info for Gigantamax
            if result.get("is_gmax"):
                embed.add_field(
                    name="Gigantamax",
                    value=f"Your {pokemon_data['name'].capitalize()} can use special G-Max moves in battle!",
                    inline=False
                )
            
            # Add duration info
            embed.add_field(
                name="Duration",
                value="Dynamax lasts for 30 minutes, or until the Pokemon is switched out.",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Dynamax failed: {result['reason']}")

    @pokemon_commands.command(name="primal")
    async def primal_reversion(self, ctx: commands.Context, pokemon_id: int):
        """Trigger Primal Reversion for Kyogre or Groudon."""
        user = ctx.author
        pokemon_id_str = str(pokemon_id)
        
        # Check if user has this Pokemon
        user_pokemon = await self.config.user(user).pokemon()
        if pokemon_id_str not in user_pokemon:
            await ctx.send(f"You don't have Pokemon #{pokemon_id}!")
            return
        
        # Attempt to activate the primal form
        result = await self.activate_form(user, pokemon_id_str, "primal")
        
        if result["success"]:
            # Create embed
            embed = discord.Embed(
                title="Primal Reversion",
                description=result["message"],
                color=0xff0000
            )
            
            # Add duration info
            embed.add_field(
                name="Duration",
                value="Primal Reversion lasts for 1 hour, or until the Pokemon is switched out.",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Primal Reversion failed: {result['reason']}")


    async def spawn_pokemon(self, guild: discord.Guild) -> bool:
        """Attempt to spawn a Pokemon in the guild."""
        # Get lock for this guild first
        if guild.id not in self.pokemon_locks:
            self.pokemon_locks[guild.id] = asyncio.Lock()
            
        async with self.pokemon_locks[guild.id]:
            # Check if a Pokemon is already active in this guild
            if guild.id in self.spawns_active:
                return False
                
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
            # Randomly decide whether to spawn a special form
            include_mega = guild_config.get("include_mega", False)
            include_gmax = guild_config.get("include_gmax", False)
            include_forms = guild_config.get("include_forms", False)
            
            special_form = False
            form_type = None
            
            # 10% chance for a special form if enabled
            if random.random() < 0.1:
                if include_mega and random.random() < 0.33:
                    special_form = True
                    form_type = "mega"
                    # For Charizard and Mewtwo, pick X or Y
                    if random.random() < 0.5:
                        form_type = "mega-x"
                    else:
                        form_type = "mega-y"
                elif include_gmax and random.random() < 0.33:
                    special_form = True
                    form_type = "gmax"
                elif include_forms and random.random() < 0.33:
                    special_form = True
                    # Pick a regional form
                    form_options = ["alola", "galar", "hisui"]
                    form_type = random.choice(form_options)
            
            pokemon_id = random.randint(1, 898)
            
            # For mega evolutions, only select Pokemon that can mega evolve
            if special_form and form_type in ["mega", "mega-x", "mega-y"]:
                # List of Pokemon that can Mega Evolve
                mega_capable_pokemon = [3, 6, 9, 65, 94, 115, 127, 130, 142, 150, 181, 212, 214, 229, 248, 257, 282, 303, 306, 308, 310, 354, 359, 380, 381, 445, 448, 460]
                pokemon_id = random.choice(mega_capable_pokemon)
            
            # For Gigantamax, only select Pokemon with Gigantamax forms
            if special_form and form_type == "gmax":
                # List of Pokemon with Gigantamax forms
                gmax_capable_pokemon = [3, 6, 9, 12, 25, 52, 68, 94, 99, 131, 143, 569, 809, 812, 815, 818, 823, 826, 834, 839, 841, 844, 849, 851, 858, 861, 869, 879, 884, 892]
                pokemon_id = random.choice(gmax_capable_pokemon)
            
            # For regional forms, only select Pokemon with those forms
            if special_form and form_type in ["alola", "galar", "hisui"]:
                if form_type == "alola":
                    # List of Pokemon with Alolan forms
                    alolan_pokemon = [19, 20, 26, 27, 28, 37, 38, 50, 51, 52, 53, 74, 75, 76, 88, 89, 103, 105]
                    pokemon_id = random.choice(alolan_pokemon)
                elif form_type == "galar":
                    # List of Pokemon with Galarian forms
                    galarian_pokemon = [52, 77, 78, 79, 80, 83, 110, 122, 144, 145, 146, 199, 222, 263, 264, 554, 555, 562, 618]
                    pokemon_id = random.choice(galarian_pokemon)
                elif form_type == "hisui":
                    # List of Pokemon with Hisuian forms
                    hisuian_pokemon = [58, 59, 100, 101, 157, 211, 215, 503, 549, 570, 571, 628, 705, 706, 713]
                    pokemon_id = random.choice(hisuian_pokemon)
            
            # Fetch Pokemon data with form if needed
            pokemon_data = await self.fetch_pokemon(pokemon_id, form_type)
            
            if not pokemon_data:
                return False
            
            # Get all possible command prefixes the bot might use
            # This handles both "." and "!" prefixes for multi-prefix bots
            all_prefixes = []
            if callable(self.bot.command_prefix):
                try:
                    # If command_prefix is callable, get the actual prefixes for this guild
                    prefix_list = await self.bot.command_prefix(self.bot, None, guild=guild)
                    if isinstance(prefix_list, list):
                        all_prefixes.extend(prefix_list)
                    else:
                        all_prefixes.append(prefix_list)
                except:
                    # Default fallback prefix if we can't get the actual one
                    all_prefixes = [".", "!"]
            else:
                # If it's already a string or list
                if isinstance(self.bot.command_prefix, list):
                    all_prefixes.extend(self.bot.command_prefix)
                else:
                    all_prefixes.append(self.bot.command_prefix)
            
            # If for some reason we didn't get any prefixes, add default ones
            if not all_prefixes:
                all_prefixes = [".", "!"]
            
            # Format display name properly
            display_name = "Pokémon"
            if "-" in pokemon_data["name"]:
                base_name, form = pokemon_data["name"].split("-", 1)
                base_name = base_name.capitalize()
                if form == "mega":
                    display_name = f"Mega {base_name}"
                elif form.startswith("mega-"):
                    form_type = form.split("-")[1].upper()
                    display_name = f"Mega {base_name} {form_type}"
                elif form == "gmax":
                    display_name = f"Gigantamax {base_name}"
                elif form in ["alola", "galar", "hisui"]:
                    display_name = f"{form.capitalize()}n {base_name}"
                else:
                    display_name = pokemon_data["name"].capitalize()
            else:
                display_name = pokemon_data["name"].capitalize()
            
            # Create embed for spawn with instructions for both prefixes
            embed = discord.Embed(
                title=f"A wild {display_name} appeared!",
                description=f"Type `{all_prefixes[0]}p catch {pokemon_data['name']}` to catch it!",
                color=0x00ff00
            )
            
            # Set image
            embed.set_image(url=pokemon_data["sprite"])
            
            # Add catch commands for all prefixes
            catch_commands = []
            for prefix in all_prefixes:
                catch_commands.append(f"`{prefix}p catch {pokemon_data['name']}`")
            
            embed.add_field(
                name="Catch Commands",
                value="\n".join(catch_commands),
                inline=False
            )
            
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

    # Fix for the on_message listener to ensure spawns happen
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
                    pokemon_name = xp_result.get('pokemon_name', 'Pokemon')
                    await message.channel.send(
                        f"{message.author.mention}'s {pokemon_name.capitalize()} reached level {xp_result['new_level']}!"
                    )
        
        # Check if this is a Pokemon channel
        guild_config = await self.config.guild(message.guild).all()
        if not guild_config["channel"]:
            return  # No spawn channel set
        
        # Get guild lock
        if message.guild.id not in self.pokemon_locks:
            self.pokemon_locks[message.guild.id] = asyncio.Lock()
        
        # Prevent race conditions
        async with self.pokemon_locks[message.guild.id]:
            # Check if a Pokemon is already active
            if message.guild.id in self.spawns_active:
                return
                
            # Random chance to spawn a Pokemon - use the guild's spawn chance setting
            spawn_chance = guild_config.get("spawn_chance", SPAWN_CHANCE)
            if random.random() < spawn_chance:
                # DEBUG: Print to console when spawning is triggered
                print(f"Spawning Pokemon in {message.guild.name}")
                await self.spawn_pokemon(message.guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Initialize guild data when the bot joins a new guild."""
        # Create a lock for this guild
        if guild.id not in self.pokemon_locks:
            self.pokemon_locks[guild.id] = asyncio.Lock()
            
        # Send welcome message to the system channel if available
        if guild.system_channel:
            # Resolve the bot's prefix to a string
            prefix = (self.bot.command_prefix(guild) 
                    if callable(self.bot.command_prefix) 
                    else self.bot.command_prefix)
            
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
                name="Special Forms",
                value=f"Enable Mega Evolutions, Gigantamax forms, and regional variants with `{prefix}pokemon settings forms`!",
                inline=False
            )
            
            embed.add_field(
                name="Help and Commands",
                value=f"Use `{prefix}help pokemon` to see all available commands.",
                inline=False
            )
            
            await guild.system_channel.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot."""
    cog = PokemonCog(bot)
    await bot.add_cog(cog)
    
    # Start background task to check temporary forms
    bot.loop.create_task(cog.check_temporary_forms())
