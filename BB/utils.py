"""
Utility functions for the DeathBattle cog.
"""
import logging
import random
import discord
from typing import Optional, Dict, Any

# Handle imports more robustly
try:
    from .constants import *
    from .gamedata import MOVES, MOVE_TYPES, ENVIRONMENTS
except ImportError:
    from constants import *
    from gamedata import MOVES, MOVE_TYPES, ENVIRONMENTS

def setup_logger(name: str) -> logging.Logger:
    """Set up a logger for the cog."""
    logger = logging.getLogger(f"red.deathbattle.{name}")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def calculate_damage(move: Dict[str, Any], is_crit: bool = False, modifiers: Dict[str, float] = None) -> int:
    """Calculate damage for a battle move with new system."""
    move_type = MOVE_TYPES.get(move.get("type", "regular"), MOVE_TYPES["regular"])
    min_damage, max_damage = move_type["base_damage_range"]
    
    base_damage = random.randint(min_damage, max_damage)
    
    if is_crit:
        base_damage = int(base_damage * CRIT_MULTIPLIER)
    
    # Apply modifiers
    if modifiers:
        for modifier_type, value in modifiers.items():
            base_damage = int(base_damage * value)
    
    return max(1, base_damage)  # Minimum 1 damage

def check_critical_hit(move: Dict[str, Any], attacker: Dict[str, Any] = None) -> bool:
    """Check if an attack is a critical hit."""
    base_crit = move.get("crit_chance", CRIT_CHANCE)
    
    # Add bonuses from status effects or devil fruits
    if attacker and attacker.get("status", {}).get("attack_boost", 0) > 0:
        base_crit += 0.1  # 10% bonus crit chance
    
    return random.random() < base_crit

def generate_health_bar(current_hp: int, max_hp: int = STARTING_HP) -> str:
    """Generate a visual health bar."""
    if current_hp <= 0:
        return "💀" * 10
    
    percentage = current_hp / max_hp
    filled_blocks = int(percentage * 10)
    empty_blocks = 10 - filled_blocks
    
    return "❤️" * filled_blocks + "🖤" * empty_blocks

def create_battle_embed(
    player1: discord.Member, 
    player2: discord.Member, 
    p1_hp: int, 
    p2_hp: int,
    turn_info: str = "",
    environment: str = None
) -> discord.Embed:
    """Create a battle status embed."""
    embed = discord.Embed(
        title="⚔️ DeathBattle Arena ⚔️",
        description=turn_info,
        color=discord.Color.red()
    )
    
    if environment:
        env_data = ENVIRONMENTS.get(environment, {})
        embed.add_field(
            name="🌍 Environment",
            value=f"**{environment}**\n{env_data.get('description', '')}",
            inline=False
        )
    
    embed.add_field(
        name=f"🥊 {player1.display_name}",
        value=f"HP: {p1_hp}/{STARTING_HP}\n{generate_health_bar(p1_hp)}",
        inline=True
    )
    
    embed.add_field(
        name="⚡",
        value="VS",
        inline=True
    )
    
    embed.add_field(
        name=f"🥊 {player2.display_name}",
        value=f"HP: {p2_hp}/{STARTING_HP}\n{generate_health_bar(p2_hp)}",
        inline=True
    )
    
    return embed

def format_berris(amount: int) -> str:
    """Format berris amount with proper commas."""
    return f"{amount:,} Berris"

def calculate_robbery_amount(target_balance: int) -> int:
    """Calculate how much can be stolen in a robbery."""
    if target_balance < MIN_ROBBERY_AMOUNT:
        return 0
    
    # Steal 10-30% of their balance
    percentage = random.uniform(0.1, 0.3)
    return int(target_balance * percentage)

def get_random_move() -> Dict[str, Any]:
    """Get a random battle move from the new system."""
    return random.choice(MOVES)

def get_random_environment() -> str:
    """Get a random battle environment."""
    return random.choice(list(ENVIRONMENTS.keys()))

async def safe_send(ctx, content=None, embed=None, file=None) -> Optional[discord.Message]:
    """Safely send a message with error handling."""
    try:
        return await ctx.send(content=content, embed=embed, file=file)
    except discord.HTTPException as e:
        logger = setup_logger("utils")
        logger.error(f"Failed to send message: {e}")
        return None
    except Exception as e:
        logger = setup_logger("utils")
        logger.error(f"Unexpected error sending message: {e}")
        return None

def create_character_data(member: discord.Member, devil_fruit: str = None) -> Dict[str, Any]:
    """Create character data for battle participants."""
    return {
        "name": member.display_name,
        "id": member.id,
        "hp": STARTING_HP,
        "max_hp": STARTING_HP,
        "fruit": devil_fruit,
        "status": {},
        "moves_on_cooldown": {},
        "stats": {
            "damage_dealt": 0,
            "damage_taken": 0,
            "moves_used": 0,
            "crits_landed": 0
        }
    }