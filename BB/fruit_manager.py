"""
Fruit management system for removing, buying, and changing devil fruits.
"""
import discord
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

try:
    from .gamedata import DEVIL_FRUITS
    from .constants import *
    from .utils import setup_logger, safe_send, format_berris
except ImportError:
    from gamedata import DEVIL_FRUITS
    from constants import *
    from utils import setup_logger, safe_send, format_berris

class FruitManager:
    """Manages devil fruit removal, purchasing, and admin changes."""
    
    def __init__(self, config):
        self.config = config
        self.log = setup_logger("fruit_manager")
    
    async def can_remove_fruit(self, user: discord.Member) -> Tuple[bool, str]:
        """Check if user can remove their fruit."""
        # Check if user has a fruit
        current_fruit = await self.config.member(user).devil_fruit()
        if not current_fruit:
            return False, "You don't have a Devil Fruit to remove!"
        
        # Check cooldown
        last_remove = await self.config.member(user).last_fruit_remove()
        if last_remove:
            last_remove_time = datetime.fromisoformat(last_remove)
            cooldown_end = last_remove_time + timedelta(seconds=FRUIT_REMOVE_COOLDOWN)
            
            if datetime.now() < cooldown_end:
                remaining = cooldown_end - datetime.now()
                hours = int(remaining.total_seconds() // 3600)
                return False, f"You must wait {hours} more hours before removing another fruit!"
        
        return True, ""
    
    async def can_buy_fruit(self, user: discord.Member) -> Tuple[bool, str]:
        """Check if user can buy a fruit."""
        # Check if user already has a fruit
        current_fruit = await self.config.member(user).devil_fruit()
        if current_fruit:
            return False, "You already have a Devil Fruit! Remove it first to buy a new one."
        
        # Check if user has started
        has_started = await self.config.member(user).has_started()
        if not has_started:
            return False, "You must start your journey first! Use `!start` to begin."
        
        # Check cooldown
        last_buy = await self.config.member(user).last_fruit_buy()
        if last_buy:
            last_buy_time = datetime.fromisoformat(last_buy)
            cooldown_end = last_buy_time + timedelta(seconds=FRUIT_BUY_COOLDOWN)
            
            if datetime.now() < cooldown_end:
                remaining = cooldown_end - datetime.now()
                minutes = int(remaining.total_seconds() // 60)
                return False, f"You must wait {minutes} more minutes before buying another fruit!"
        
        return True, ""
    
    async def remove_fruit(self, user: discord.Member) -> Tuple[bool, str, str]:
        """
        Remove a user's devil fruit.
        Returns (success, message, removed_fruit_name)
        """
        can_remove, error_msg = await self.can_remove_fruit(user)
        if not can_remove:
            return False, error_msg, ""
        
        # Check if user has enough berries
        total_berries = await self.config.member(user).total_berris()
        if total_berries < REMOVE_FRUIT_COST:
            return False, f"You need {format_berris(REMOVE_FRUIT_COST)} to remove your fruit! You only have {format_berris(total_berries)}.", ""
        
        # Get current fruit
        current_fruit = await self.config.member(user).devil_fruit()
        
        # Remove from rare fruit tracking if it's a rare fruit
        if current_fruit in DEVIL_FRUITS["Rare"]:
            # This requires guild context, so we'll handle it in the command
            pass
        
        # Deduct cost
        await self.config.member(user).total_berris.set(total_berries - REMOVE_FRUIT_COST)
        
        # Remove fruit and update tracking
        await self.config.member(user).devil_fruit.set(None)
        await self.config.member(user).last_fruit_remove.set(datetime.now().isoformat())
        
        # Increment remove count
        remove_count = await self.config.member(user).fruits_removed_count()
        await self.config.member(user).fruits_removed_count.set(remove_count + 1)
        
        self.log.info(f"User {user.name} removed fruit {current_fruit} for {REMOVE_FRUIT_COST} berries")
        
        return True, f"Successfully removed **{current_fruit}** for {format_berris(REMOVE_FRUIT_COST)}!", current_fruit
    
    async def buy_fruit(self, user: discord.Member, guild: discord.Guild, force_rare: bool = False) -> Tuple[bool, str, Optional[str], bool]:
        """
        Buy a random devil fruit for a user.
        Returns (success, message, fruit_name, is_rare)
        """
        can_buy, error_msg = await self.can_buy_fruit(user)
        if not can_buy:
            return False, error_msg, None, False
        
        # Determine cost
        cost = BUY_RARE_FRUIT_COST if force_rare else BUY_FRUIT_COST
        
        # Check if user has enough berries
        total_berries = await self.config.member(user).total_berris()
        if total_berries < cost:
            return False, f"You need {format_berris(cost)} to buy a fruit! You only have {format_berris(total_berries)}.", None, False
        
        # Determine rarity
        if force_rare:
            is_rare = True
        else:
            is_rare = random.random() < BUY_RARE_CHANCE
        
        fruit_name = None
        
        if is_rare:
            # Try to get a rare fruit
            available_rares = await self._get_available_rare_fruits(guild)
            
            if available_rares:
                fruit_name = random.choice(available_rares)
                
                # Track this rare fruit
                rare_fruits_given = await self.config.guild(guild).rare_fruits_given()
                rare_fruits_given[str(user.id)] = fruit_name
                await self.config.guild(guild).rare_fruits_given.set(rare_fruits_given)
            else:
                if force_rare:
                    return False, "No rare fruits are available for purchase!", None, False
                # Fall back to common
                fruit_name = random.choice(list(DEVIL_FRUITS["Common"].keys()))
                is_rare = False
        else:
            # Give common fruit
            fruit_name = random.choice(list(DEVIL_FRUITS["Common"].keys()))
        
        # Deduct cost and assign fruit
        await self.config.member(user).total_berris.set(total_berries - cost)
        await self.config.member(user).devil_fruit.set(fruit_name)
        await self.config.member(user).last_fruit_buy.set(datetime.now().isoformat())
        await self.config.member(user).fruit_acquired_date.set(datetime.now().isoformat())
        
        self.log.info(f"User {user.name} bought {fruit_name} ({'rare' if is_rare else 'common'}) for {cost} berries")
        
        return True, f"Successfully purchased **{fruit_name}** for {format_berris(cost)}!", fruit_name, is_rare
    
    async def change_fruit(self, user: discord.Member, guild: discord.Guild, new_fruit: str) -> Tuple[bool, str]:
        """
        Admin command to change a user's fruit.
        Returns (success, message)
        """
        # Check if fruit exists
        fruit_data = DEVIL_FRUITS["Common"].get(new_fruit) or DEVIL_FRUITS["Rare"].get(new_fruit)
        if not fruit_data:
            return False, f"Devil Fruit '{new_fruit}' not found!"
        
        # Get current fruit
        current_fruit = await self.config.member(user).devil_fruit()
        
        # Handle rare fruit tracking
        rare_fruits_given = await self.config.guild(guild).rare_fruits_given()
        
        # Remove old rare fruit from tracking if applicable
        if current_fruit and current_fruit in DEVIL_FRUITS["Rare"]:
            if str(user.id) in rare_fruits_given and rare_fruits_given[str(user.id)] == current_fruit:
                del rare_fruits_given[str(user.id)]
        
        # Add new rare fruit to tracking if applicable
        if new_fruit in DEVIL_FRUITS["Rare"]:
            rare_fruits_given[str(user.id)] = new_fruit
        
        # Update tracking
        await self.config.guild(guild).rare_fruits_given.set(rare_fruits_given)
        
        # Set new fruit
        await self.config.member(user).devil_fruit.set(new_fruit)
        await self.config.member(user).fruit_acquired_date.set(datetime.now().isoformat())
        
        # Mark as started if not already
        await self.config.member(user).has_started.set(True)
        
        old_fruit_text = f" (was {current_fruit})" if current_fruit else ""
        self.log.info(f"Admin changed {user.name}'s fruit to {new_fruit}{old_fruit_text}")
        
        return True, f"Successfully changed **{user.display_name}**'s fruit to **{new_fruit}**{old_fruit_text}!"
    
    async def _get_available_rare_fruits(self, guild: discord.Guild) -> list:
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
    
    async def create_fruit_purchase_embed(self, user: discord.Member, fruit_name: str, is_rare: bool, cost: int) -> discord.Embed:
        """Create an embed for fruit purchase confirmation."""
        fruit_data = DEVIL_FRUITS["Rare" if is_rare else "Common"][fruit_name]
        
        color = discord.Color.gold() if is_rare else discord.Color.blue()
        
        embed = discord.Embed(
            title="🍎 Devil Fruit Purchased!",
            description=f"**{user.display_name}** has acquired a new power!",
            color=color
        )
        
        if is_rare:
            embed.add_field(
                name="⭐ RARE ACQUISITION! ⭐",
                value="You've purchased an incredibly rare Devil Fruit!",
                inline=False
            )
        
        embed.add_field(
            name="🍎 Your New Devil Fruit",
            value=f"**{fruit_name}**",
            inline=True
        )
        
        embed.add_field(
            name="📝 Type",
            value=fruit_data["type"],
            inline=True
        )
        
        embed.add_field(
            name="💰 Cost",
            value=format_berris(cost),
            inline=True
        )
        
        embed.add_field(
            name="💫 Power",
            value=fruit_data["bonus"],
            inline=False
        )
        
        if is_rare:
            embed.set_footer(text="💎 A legendary power now flows through you!")
        else:
            embed.set_footer(text="🌊 Your power has been renewed!")
        
        return embed