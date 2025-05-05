"""Formatting utility functions for the Pokemon cog."""
import discord
from typing import Optional, Dict, Any, List
from datetime import datetime

def format_pokemon_name(name: str, form_type: Optional[str] = None) -> str:
    """Format a Pokemon name for display, including special forms.
    
    Args:
        name: The Pokemon name to format
        form_type: The form type, if any
        
    Returns:
        Formatted display name
    """
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

def create_spawn_embed(prefix: str, pokemon_data: Dict[str, Any]) -> discord.Embed:
    """Create an embed for a spawned Pokemon.
    
    Args:
        prefix: The bot's command prefix
        pokemon_data: The Pokemon data dictionary
        
    Returns:
        Discord Embed with spawn information
    """
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
    
    # Create embed for spawn with clear catching instructions
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
    
    return embed

def create_pokemon_info_embed(pokemon_data: Dict[str, Any], user_pokemon_data: Dict[str, Any]) -> discord.Embed:
    """Create an embed with detailed Pokemon information.
    
    Args:
        pokemon_data: Pokemon data from API
        user_pokemon_data: User's Pokemon data from config
        
    Returns:
        Discord Embed with Pokemon information
    """
    # Format name for display
    form_type = user_pokemon_data.get("form_type")
    display_name = format_pokemon_name(pokemon_data["name"], form_type)
    
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
        embed.add_field(
            name="Evolution",
            value=f"Can evolve at level {pokemon_data['evolves_at_level']}",
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
    
    return embed

def create_team_embed(user: discord.Member, team_data: List[Dict]) -> discord.Embed:
    """Create an embed showing a user's Pokemon team.
    
    Args:
        user: The Discord member
        team_data: List of Pokemon data
        
    Returns:
        Discord Embed with team information
    """
    embed = discord.Embed(
        title=f"{user.name}'s Pokemon Team",
        color=0xff5500
    )

    # Add each Pokemon to the embed
    for pokemon in team_data:
        # Format name based on form type
        display_name = format_pokemon_name(pokemon["name"], pokemon.get("form_type"))
        
        name = pokemon.get("nickname") or display_name
        if pokemon.get("nickname"):
            name += f" ({display_name})"

        embed.add_field(
            name=f"#{pokemon['id']}: {name}",
            value=f"Level: {pokemon['level']}\nType: {', '.join(t.capitalize() for t in pokemon['types'])}",
            inline=True
        )
    
    return embed

def create_pokedex_embed(pokemon_data: Dict[str, Any], caught: bool = False) -> discord.Embed:
    """Create a Pokedex entry embed for a Pokemon.
    
    Args:
        pokemon_data: Pokemon data from API
        caught: Whether the user has caught this Pokemon
        
    Returns:
        Discord Embed with Pokedex information
    """
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
        evolution_info = f"Evolves into #{pokemon_data['evolves_to']}"
        
        if pokemon_data.get("evolves_at_level"):
            evolution_info += f" at level {pokemon_data['evolves_at_level']}"
            
        if pokemon_data.get("evolution_condition"):
            evolution_info += f" ({pokemon_data['evolution_condition']})"
            
        embed.add_field(
            name="Evolution",
            value=evolution_info,
            inline=False
        )
    
    # Caught status
    embed.add_field(
        name="Caught Status",
        value="✅ Caught" if caught else "❌ Not caught",
        inline=False
    )
    
    return embed

def create_shop_embed(user_money: int) -> discord.Embed:
    """Create an embed for the Pokemon shop.
    
    Args:
        user_money: The user's current money
        
    Returns:
        Discord Embed with shop information
    """
    from ..constants import SHOP_ITEMS
    
    # Create shop embed
    embed = discord.Embed(
        title="Pokemon Item Shop",
        description=f"Your balance: ${user_money}",
        color=0xffcc00
    )
    
    # Group items by category
    basic_items = [item for key, item in SHOP_ITEMS.items() if item["price"] < 1000]
    mid_items = [item for key, item in SHOP_ITEMS.items() if 1000 <= item["price"] < 10000]
    evolution_items = [item for key, item in SHOP_ITEMS.items() if "stone" in item["name"].lower()]
    special_items = [item for key, item in SHOP_ITEMS.items() if item["price"] >= 30000]
    
    # Add fields for each category
    basic_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in basic_items)
    if basic_str:
        embed.add_field(name="Basic Items", value=basic_str, inline=False)
    
    mid_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in mid_items)
    if mid_str:
        embed.add_field(name="Enhancement Items", value=mid_str, inline=False)
    
    evolution_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in evolution_items)
    if evolution_str:
        embed.add_field(name="Evolution Items", value=evolution_str, inline=False)
    
    special_str = "\n".join(f"{item['name']}: ${item['price']} - {item['description']}" for item in special_items)
    if special_str:
        embed.add_field(name="Special Items", value=special_str, inline=False)
    
    # Add usage instructions
    embed.set_footer(text="Use !pokemon buy <item> to purchase an item.")
    
    return embed

def create_items_embed(user: discord.Member, user_items: Dict[str, int]) -> discord.Embed:
    """Create an embed showing a user's items.
    
    Args:
        user: The Discord member
        user_items: Dict of items and counts
        
    Returns:
        Discord Embed with items information
    """
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
        if "ite" in item_name and "stone" not in item_name.lower():
            mega_stones[item_name] = count
        elif "Z" in item_name and "crystal" in item_name.lower():
            z_crystals[item_name] = count
        elif "Orb" in item_name and ("Blue" in item_name or "Red" in item_name):
            primal_orbs[item_name] = count
        elif "stone" in item_name.lower():
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
        
    return embed

def create_battle_embed(
    user1: discord.Member, 
    user2: discord.Member, 
    pokemon1: Dict[str, Any], 
    pokemon2: Dict[str, Any],
    pokemon1_data: Dict[str, Any],
    pokemon2_data: Dict[str, Any]
) -> discord.Embed:
    """Create an embed for a Pokemon battle.
    
    Args:
        user1: The first user
        user2: The second user
        pokemon1: First user's Pokemon data
        pokemon2: Second user's Pokemon data
        pokemon1_data: API data for first Pokemon
        pokemon2_data: API data for second Pokemon
        
    Returns:
        Discord Embed with battle information
    """
    # Format Pokemon names
    pokemon1_name = format_pokemon_name(pokemon1_data["name"], pokemon1.get("form_type"))
    pokemon2_name = format_pokemon_name(pokemon2_data["name"], pokemon2.get("form_type"))
    
    # Calculate HP bars (10 segments)
    hp1 = 10  # Full HP at start
    hp2 = 10  # Full HP at start
    
    # Create embed
    embed = discord.Embed(
        title="Pokemon Battle",
        description=f"{user1.name} vs. {user2.name}",
        color=0xff0000
    )
    
    embed.add_field(
        name=f"{user1.name}'s Pokemon",
        value=f"{pokemon1_name} (Lv. {pokemon1['level']})\n"
              f"HP: {'█' * hp1}\nType: {', '.join(t.capitalize() for t in pokemon1_data['types'])}",
        inline=True
    )
    
    embed.add_field(
        name=f"{user2.name}'s Pokemon",
        value=f"{pokemon2_name} (Lv. {pokemon2['level']})\n"
              f"HP: {'█' * hp2}\nType: {', '.join(t.capitalize() for t in pokemon2_data['types'])}",
        inline=True
    )
    
    return embed

def create_battle_result_embed(
    winner: discord.Member,
    loser: discord.Member,
    winner_pokemon: str,
    loser_pokemon: str,
    xp_gain: int,
    money_reward: int,
    item_drop: Optional[str] = None
) -> discord.Embed:
    """Create an embed for a battle result.
    
    Args:
        winner: The winning user
        loser: The losing user
        winner_pokemon: Winner's Pokemon name
        loser_pokemon: Loser's Pokemon name
        xp_gain: XP gained by winner
        money_reward: Money reward
        item_drop: Optional item drop
        
    Returns:
        Discord Embed with battle result
    """
    # Create embed
    embed = discord.Embed(
        title="Battle Result",
        description=f"{winner.name}'s {winner_pokemon} defeated {loser.name}'s {loser_pokemon}!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="Rewards",
        value=f"{winner.name}'s {winner_pokemon} gained {xp_gain} XP!",
        inline=False
    )
    
    embed.add_field(
        name="Money",
        value=f"{winner.name} received ${money_reward} for winning!",
        inline=False
    )
    
    if item_drop:
        embed.add_field(
            name="Item Drop",
            value=f"{winner.name} found a {item_drop}!",
            inline=False
        )
    
    return embed

def create_evolution_embed(
    old_pokemon: str,
    new_pokemon: str,
    old_level: int,
    new_level: int
) -> discord.Embed:
    """Create an embed for Pokemon evolution.
    
    Args:
        old_pokemon: Pre-evolution Pokemon name
        new_pokemon: Evolved Pokemon name
        old_level: Pre-evolution level
        new_level: Post-evolution level
        
    Returns:
        Discord Embed with evolution information
    """
    embed = discord.Embed(
        title="Evolution",
        description=f"Congratulations! Your {old_pokemon.capitalize()} evolved into {new_pokemon.capitalize()}!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="Level",
        value=f"Level {old_level} → Level {new_level}",
        inline=False
    )
    
    return embed

def create_daily_reward_embed(
    user: discord.Member,
    money_reward: int,
    xp_bonus: Optional[int] = None,
    pokemon_name: Optional[str] = None,
    level_up: bool = False,
    new_level: Optional[int] = None,
    item_reward: Optional[str] = None
) -> discord.Embed:
    """Create an embed for daily rewards.
    
    Args:
        user: The Discord member
        money_reward: Money reward amount
        xp_bonus: Optional XP bonus for active Pokemon
        pokemon_name: Optional active Pokemon name
        level_up: Whether the Pokemon leveled up
        new_level: New level if leveled up
        item_reward: Optional item reward
        
    Returns:
        Discord Embed with daily reward information
    """
    embed = discord.Embed(
        title="Daily Reward!",
        description=f"Here are your daily rewards, {user.name}!",
        color=0xffcc00
    )
    
    embed.add_field(
        name="Money",
        value=f"You received ${money_reward}!",
        inline=False
    )
    
    if xp_bonus and pokemon_name:
        if level_up and new_level:
            embed.add_field(
                name="Pokemon Training",
                value=f"Your {pokemon_name} gained {xp_bonus} XP and leveled up to level {new_level}!",
                inline=False
            )
        else:
            embed.add_field(
                name="Pokemon Training",
                value=f"Your {pokemon_name} gained {xp_bonus} XP!",
                inline=False
            )
    
    if item_reward:
        embed.add_field(
            name="Item",
            value=f"You received a {item_reward}!",
            inline=False
        )
    
    return embed