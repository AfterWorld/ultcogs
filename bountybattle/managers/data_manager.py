import asyncio
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import discord
from redbot.core import Config

class DataManager:
    """Handles data persistence and synchronization."""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.data_lock = asyncio.Lock()
        self.bounty_lock = asyncio.Lock()
        self.bounty_file = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/bounties.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
    
    def load_bounties(self):
        """Load bounty data safely from file."""
        if not os.path.exists(self.bounty_file):
            return {}  # If file doesn't exist, return empty dict
        
        try:
            with open(self.bounty_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}  # If file is corrupted, return empty dict
    
    def save_bounties(self, data):
        """Save bounty data safely to file."""
        os.makedirs(os.path.dirname(self.bounty_file), exist_ok=True)
        with open(self.bounty_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    
    async def sync_user_data(self, user: discord.Member) -> Optional[int]:
        """
        Synchronize bounty data for a user between config and bounties.json.
        
        Returns the synchronized bounty amount.
        """
        async with self.data_lock:
            try:
                # Load current bounty data
                bounties = self.load_bounties()
                user_id = str(user.id)
                
                # Get bounty from config and bounties.json
                config_bounty = await self.config.member(user).bounty()
                json_bounty = bounties.get(user_id, {}).get("amount", 0)
                
                # Use the higher value as the source of truth
                true_bounty = max(config_bounty, json_bounty)
                
                # Update both systems
                if user_id not in bounties:
                    bounties[user_id] = {"amount": true_bounty, "fruit": None}
                else:
                    bounties[user_id]["amount"] = true_bounty
                    
                # Save back to file
                self.save_bounties(bounties)
                
                # Update config
                await self.config.member(user).bounty.set(true_bounty)
                
                return true_bounty
            except Exception as e:
                self.logger.error(f"Error in sync_user_data: {e}")
                return None
    
    async def safe_modify_bounty(self, user: discord.Member, amount: int, operation: str = "add") -> Optional[int]:
        """Thread-safe method to modify a user's bounty."""
        async with self.bounty_lock:
            try:
                bounties = self.load_bounties()
                user_id = str(user.id)
                
                if user_id not in bounties:
                    bounties[user_id] = {"amount": 0, "fruit": None}
                
                if operation == "add":
                    bounties[user_id]["amount"] += amount
                elif operation == "subtract":
                    bounties[user_id]["amount"] = max(0, bounties[user_id]["amount"] - amount)
                elif operation == "set":
                    bounties[user_id]["amount"] = amount
                
                self.save_bounties(bounties)
                await self.config.member(user).bounty.set(bounties[user_id]["amount"])
                return bounties[user_id]["amount"]
            except Exception as e:
                self.logger.error(f"Error modifying bounty: {e}")
                return None
    
    async def get_bounty(self, user: discord.Member) -> int:
        """Get a user's current bounty amount."""
        async with self.data_lock:
            try:
                # Try to get from config first
                config_bounty = await self.config.member(user).bounty()
                
                # If config has valid data, use it
                if isinstance(config_bounty, int) and config_bounty >= 0:
                    return config_bounty
                
                # Otherwise, check JSON file
                bounties = self.load_bounties()
                user_id = str(user.id)
                
                if user_id in bounties:
                    return bounties[user_id].get("amount", 0)
                
                # Default to 0 if user has no bounty data
                return 0
            except Exception as e:
                self.logger.error(f"Error getting bounty: {e}")
                return 0
    
    async def get_devil_fruit(self, user: discord.Member) -> Optional[str]:
        """Get a user's devil fruit."""
        async with self.data_lock:
            try:
                # Try to get from config first
                config_fruit = await self.config.member(user).devil_fruit()
                
                # If config has valid data, use it
                if config_fruit:
                    return config_fruit
                
                # Otherwise, check JSON file
                bounties = self.load_bounties()
                user_id = str(user.id)
                
                if user_id in bounties:
                    return bounties[user_id].get("fruit")
                
                # Default to None if user has no devil fruit
                return None
            except Exception as e:
                self.logger.error(f"Error getting devil fruit: {e}")
                return None
    
    async def set_devil_fruit(self, user: discord.Member, fruit_name: Optional[str]) -> bool:
        """Set a user's devil fruit."""
        async with self.bounty_lock:
            try:
                bounties = self.load_bounties()
                user_id = str(user.id)
                
                if user_id not in bounties:
                    bounties[user_id] = {"amount": 0, "fruit": fruit_name}
                else:
                    bounties[user_id]["fruit"] = fruit_name
                
                self.save_bounties(bounties)
                await self.config.member(user).devil_fruit.set(fruit_name)
                return True
            except Exception as e:
                self.logger.error(f"Error setting devil fruit: {e}")
                return False