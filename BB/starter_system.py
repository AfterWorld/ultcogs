"""
Starter system for new users joining the DeathBattle system.
"""
import discord
import random
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

try:
    from .gamedata import DEVIL_FRUITS
    from .constants import STARTER_COMMON_CHANCE, STARTER_RARE_CHANCE, STARTER_BERRIES_BONUS
    from .utils import setup_logger, safe_send
except ImportError:
    from gamedata import DEVIL_FRUITS
    from constants import STARTER_COMMON_CHANCE, STARTER_RARE_CHANCE, STARTER_BERRIES_BONUS
    from utils import setup_logger, safe_send

class StarterSystem:
    """Manages the starter devil fruit system."""
    
    def __init__(self, config):
        self.config = config
        self.log = setup_logger("starter_system")
    
    async def can_start(self, user: discord.Member) -> bool:
        """Check if user can use the start command."""
        has_started = await self.config.member(user).has_started()
        return not has_started
    
    async def get_available_rare_fruits(self, guild: discord.Guild) -> list:
        """Get list of rare fruits that haven't reached the limit."""
        rare_fruits_given = await self.config.guild(guild).rare_fruits_given()
        rare_fruit_limit = await self.config.guild(guild).rare_fruit_limit()
        
        available_rares = []
        
        for fruit_name in DEVIL_FRUITS["Rare"].keys():
            # Count how many of this fruit have been given
            current_count = sum(1 for fruit in rare_fruits_given.values() if fruit == fruit_name)
            
            if current_count < rare_fruit_limit:
                available_rares.append(fruit_name)
        
        return available_rares
    
    async def assign_starter_fruit(self, user: discord.Member, guild: discord.Guild) -> Tuple[str, bool]:
        """
        Assign a starter devil fruit to a user.
        Returns (fruit_name, is_rare)
        """
        # Check if user can start
        if not await self.can_start(user):
            return None, False
        
        # Determine rarity
        is_rare = random.random() < STARTER_RARE_CHANCE
        
        if is_rare:
            # Try to get a rare fruit
            available_rares = await self.get_available_rare_fruits(guild)
            
            if available_rares:
                fruit_name = random.choice(available_rares)
                
                # Track this rare fruit
                rare_fruits_given = await self.config.guild(guild).rare_fruits_given()
                rare_fruits_given[str(user.id)] = fruit_name
                await self.config.guild(guild).rare_fruits_given.set(rare_fruits_given)
                
                self.log.info(f"Assigned rare fruit {fruit_name} to {user.name}")
            else:
                # No rare fruits available, give common instead
                fruit_name = random.choice(list(DEVIL_FRUITS["Common"].keys()))
                is_rare = False
                self.log.info(f"No rare fruits available, gave common {fruit_name} to {user.name}")
        else:
            # Give common fruit
            fruit_name = random.choice(list(DEVIL_FRUITS["Common"].keys()))
        
        # Set the fruit and mark as started
        await self.config.member(user).devil_fruit.set(fruit_name)
        await self.config.member(user).has_started.set(True)
        await self.config.member(user).fruit_acquired_date.set(datetime.now().isoformat())
        
        # Give starting berries
        current_berries = await self.config.member(user).total_berris()
        await self.config.member(user).total_berris.set(current_berries + STARTER_BERRIES_BONUS)
        
        self.log.info(f"User {user.name} started with {fruit_name} ({'rare' if is_rare else 'common'})")
        
        return fruit_name, is_rare
    
    async def create_starter_embed(self, user: discord.Member, fruit_name: str, is_rare: bool) -> discord.Embed:
        """Create an embed for the starter fruit assignment."""
        fruit_data = DEVIL_FRUITS["Rare" if is_rare else "Common"][fruit_name]
        
        # Different colors for different rarities
        color = discord.Color.gold() if is_rare else discord.Color.blue()
        
        embed = discord.Embed(
            title="🏴‍☠️ Welcome to the Grand Line! 🏴‍☠️",
            description=f"**{user.display_name}** has begun their pirate journey!",
            color=color
        )
        
        # Add dramatic flair for rare fruits
        if is_rare:
            embed.add_field(
                name="⭐ LEGENDARY DISCOVERY! ⭐",
                value="You've found an incredibly rare Devil Fruit!",
                inline=False
            )
        
        embed.add_field(
            name="🍎 Your Devil Fruit",
            value=f"**{fruit_name}**",
            inline=True
        )
        
        embed.add_field(
            name="📝 Type",
            value=fruit_data["type"],
            inline=True
        )
        
        embed.add_field(
            name="⚡ Rarity",
            value="⭐ **Rare**" if is_rare else "🔹 **Common**",
            inline=True
        )
        
        embed.add_field(
            name="💫 Power",
            value=fruit_data["bonus"],
            inline=False
        )
        
        embed.add_field(
            name="💰 Starting Bonus",
            value=f"{STARTER_BERRIES_BONUS:,} Berris",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Next Steps",
            value="Use `!db` to start battling and `!bank` to manage your berries!",
            inline=False
        )
        
        # Add special footer for rare fruits
        if is_rare:
            embed.set_footer(text="💎 You are one of the few to possess this legendary power!")
        else:
            embed.set_footer(text="🌊 Your adventure on the Grand Line begins now!")
        
        return embed
    
    async def get_rare_fruit_stats(self, guild: discord.Guild) -> Dict[str, int]:
        """Get statistics on rare fruit distribution."""
        rare_fruits_given = await self.config.guild(guild).rare_fruits_given()
        rare_fruit_limit = await self.config.guild(guild).rare_fruit_limit()
        
        stats = {}
        
        # Count each rare fruit type
        for fruit_name in DEVIL_FRUITS["Rare"].keys():
            count = sum(1 for fruit in rare_fruits_given.values() if fruit == fruit_name)
            stats[fruit_name] = {"current": count, "max": rare_fruit_limit}
        
        return stats