"""
Utility functions for the DeathBattle cog.
"""
import logging
import random
import discord
from typing import Optional, Tuple
from .constants import *

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

def calculate_damage(move: dict, is_crit: bool = False) -> int:
    """Calculate damage for a battle move."""
    base_damage = random.randint(move["min_damage"], move["max_damage"])
    if is_crit:
        base_damage = int(base_damage * CRIT_MULTIPLIER)
    return base_damage

def check_critical_hit(move: dict) -> bool:
    """Check if an attack is a critical hit."""
    return random.random() < move.get("crit_chance", CRIT_CHANCE)

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
    turn_info: str = ""
) -> discord.Embed:
    """Create a battle status embed."""
    embed = discord.Embed(
        title="⚔️ DeathBattle Arena ⚔️",
        description=turn_info,
        color=discord.Color.red()
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

def get_random_move() -> dict:
    """Get a random battle move."""
    return random.choice(BATTLE_MOVES)

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