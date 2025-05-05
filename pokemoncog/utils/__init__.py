"""Utility modules for the Pokemon cog.

This package contains various utility functions used by the Pokemon cog:

- api.py: Functions for interacting with the PokeAPI
- formatters.py: Functions for formatting Pokemon data for display
- spawn.py: Functions for Pokemon spawning mechanics
"""

from .api import fetch_pokemon, fetch_all_forms, get_random_pokemon_id
from .formatters import format_pokemon_name, create_spawn_embed
from .spawn import spawn_pokemon, expire_spawn, add_pokemon_to_user, is_correct_catch

__all__ = [
    # API functions
    'fetch_pokemon',
    'fetch_all_forms',
    'get_random_pokemon_id',
    
    # Formatter functions
    'format_pokemon_name',
    'create_spawn_embed',
    
    # Spawn functions
    'spawn_pokemon',
    'expire_spawn',
    'add_pokemon_to_user',
    'is_correct_catch',
]