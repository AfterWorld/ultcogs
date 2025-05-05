"""API utility functions for the Pokemon cog."""
import logging
import random
from typing import Dict, Optional, List, Union, Any

import aiohttp
from redbot.core import Config

from ..constants import MEGA_CAPABLE_POKEMON, GMAX_CAPABLE_POKEMON, REGIONAL_FORM_POKEMON

log = logging.getLogger("red.pokemon")

async def fetch_pokemon(
    session: aiohttp.ClientSession, 
    config: Config, 
    pokemon_id: int, 
    form_key: str = None
) -> Optional[Dict[str, Any]]:
    """Fetch Pokemon data from PokeAPI with support for alternate forms.
    
    Args:
        session: The aiohttp ClientSession to use for requests
        config: The Red Config object for caching
        pokemon_id: Base Pokemon ID
        form_key: Optional form identifier (e.g., 'mega', 'mega-x', 'alola', 'galar', 'gmax')
        
    Returns:
        Dict containing Pokemon data or None if not found
    """
    # Check cache first
    pokemon_cache = await config.pokemon_cache()
    form_cache = await config.form_cache()
    
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
        async with session.get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}") as response:
            if response.status == 200:
                base_data = await response.json()
                
                # Also get species data for evolution details
                async with session.get(base_data["species"]["url"]) as species_response:
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
                    async with session.get(f"https://pokeapi.co/api/v2/pokemon/{form_name}") as form_response:
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
                            await config.form_cache.set(form_cache)
                            
                            return form_info
                
                # Get evolution data if available
                if pokemon_info["evolution_chain_url"]:
                    async with session.get(pokemon_info["evolution_chain_url"]) as evo_response:
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
                await config.pokemon_cache.set(pokemon_cache)
                
                return pokemon_info
            else:
                log.error(f"Error fetching Pokemon {pokemon_id}: HTTP {response.status}")
                return None
    except Exception as e:
        log.error(f"Error fetching Pokemon {pokemon_id}: {e}")
        return None

async def fetch_all_forms(session: aiohttp.ClientSession, config: Config, pokemon_id: int) -> List[Dict[str, Any]]:
    """Fetch all available forms for a Pokemon.
    
    Args:
        session: The aiohttp ClientSession to use for requests
        config: The Red Config object for caching
        pokemon_id: The Pokemon ID to fetch forms for
        
    Returns:
        List of dictionaries containing Pokemon form data
    """
    # Get base Pokemon data
    base_pokemon = await fetch_pokemon(session, config, pokemon_id)
    if not base_pokemon:
        return []
        
    all_forms = [base_pokemon]  # Start with base form
    
    # Fetch all the additional forms
    for form_name in base_pokemon.get("forms", []):
        # Extract form key (e.g., 'mega', 'alola', etc.)
        if "-" in form_name:
            form_key = form_name.split("-", 1)[1]
            form_data = await fetch_pokemon(session, config, pokemon_id, form_key)
            if form_data:
                all_forms.append(form_data)
    
    return all_forms

def get_random_pokemon_id(
    include_mega: bool = False, 
    include_gmax: bool = False, 
    include_forms: bool = False,
    form_type: str = None,
    type_filter: str = None
) -> tuple:
    """Get a random Pokemon ID, potentially with a special form.
    
    Args:
        include_mega: Whether to include Mega Evolutions
        include_gmax: Whether to include Gigantamax forms
        include_forms: Whether to include regional forms
        form_type: A specific form type to use, if any
        type_filter: A Pokemon type to filter by, if any
        
    Returns:
        Tuple of (pokemon_id, form_type)
    """
    pokemon_id = random.randint(1, 898)  # National Dex range
    selected_form = None
    
    # Handle specific form type request
    if form_type:
        if form_type == "mega":
            pokemon_id = random.choice(MEGA_CAPABLE_POKEMON)
            # For Charizard and Mewtwo, pick X or Y
            if pokemon_id in [6, 150] and random.random() < 0.5:
                selected_form = "mega-x"
            else:
                selected_form = "mega"
        elif form_type == "gmax":
            pokemon_id = random.choice(GMAX_CAPABLE_POKEMON)
            selected_form = "gmax"
        elif form_type in ["alola", "galar", "hisui"]:
            pokemon_id = random.choice(REGIONAL_FORM_POKEMON[form_type])
            selected_form = form_type
        return pokemon_id, selected_form
    
    # Random chance for special form if enabled
    if random.random() < 0.1:  # 10% chance for a special form
        if include_mega and random.random() < 0.33:
            pokemon_id = random.choice(MEGA_CAPABLE_POKEMON)
            # For Charizard and Mewtwo, pick X or Y
            if pokemon_id in [6, 150] and random.random() < 0.5:
                selected_form = "mega-x"
            else:
                selected_form = "mega"
        elif include_gmax and random.random() < 0.33:
            pokemon_id = random.choice(GMAX_CAPABLE_POKEMON)
            selected_form = "gmax"
        elif include_forms and random.random() < 0.33:
            # Pick a regional form
            form_options = ["alola", "galar", "hisui"]
            selected_form = random.choice(form_options)
            pokemon_id = random.choice(REGIONAL_FORM_POKEMON[selected_form])
    
    return pokemon_id, selected_form