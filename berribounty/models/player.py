"""Player model for the One Piece bot."""

import time
from typing import Dict, List, Any, Optional

class Player:
    """Represents a player in the One Piece bot."""
    
    def __init__(self, member, data: Dict[str, Any]):
        self.member = member
        self._data = data
        
        # Basic properties
        self.berries = data.get("berries", 0)
        self.bank_berries = data.get("bank_berries", 0)
        self.devil_fruit = data.get("devil_fruit")
        self.devil_fruit_mastery = data.get("devil_fruit_mastery", {})
        
        # Battle stats
        self.wins = data.get("wins", 0)
        self.losses = data.get("losses", 0)
        self.total_damage_dealt = data.get("total_damage_dealt", 0)
        self.total_damage_taken = data.get("total_damage_taken", 0)
        
        # Achievements and titles
        self.achievements = data.get("achievements", [])
        self.titles = data.get("titles", [])
        self.current_title = data.get("current_title")
        
        # Activity tracking
        self.last_active = data.get("last_active", time.time())
        self.last_daily = data.get("last_daily", 0)
        self.last_work = data.get("last_work", 0)
        self.last_gamble = data.get("last_gamble", 0)
        self.daily_streak = data.get("daily_streak", 0)
        
        # Additional stats
        self.stats = data.get("stats", {})
        self.battle_preferences = data.get("battle_preferences", {})
        self.inventory = data.get("inventory", {"items": {}, "consumables": {}})
    
    def add_berries(self, amount: int):
        """Add berries to the player's wallet."""
        self.berries += amount
        self.stats["berries_earned"] = self.stats.get("berries_earned", 0) + amount
    
    def remove_berries(self, amount: int) -> bool:
        """Remove berries from the player's wallet."""
        if self.berries >= amount:
            self.berries -= amount
            self.stats["berries_lost"] = self.stats.get("berries_lost", 0) + amount
            return True
        return False
    
    def add_win(self):
        """Add a win to the player's record."""
        self.wins += 1
        self.stats["battles_fought"] = self.stats.get("battles_fought", 0) + 1
    
    def add_loss(self):
        """Add a loss to the player's record."""
        self.losses += 1
        self.stats["battles_fought"] = self.stats.get("battles_fought", 0) + 1
    
    def add_damage_dealt(self, damage: int):
        """Add damage dealt to stats."""
        self.total_damage_dealt += damage
    
    def add_damage_taken(self, damage: int):
        """Add damage taken to stats."""
        self.total_damage_taken += damage
    
    @property
    def devil_fruit_data(self) -> Optional[Dict[str, Any]]:
        """Get devil fruit data if player has one."""
        if not self.devil_fruit:
            return None
        
        # This would be implemented to look up fruit data
        # from the DEVIL_FRUITS constant
        from ..constants.fruits import DEVIL_FRUITS
        
        for category, fruits in DEVIL_FRUITS.items():
            if self.devil_fruit in fruits:
                return fruits[self.devil_fruit]
        return None
    
    @property
    def total_wealth(self) -> int:
        """Get total wealth (berries + bank)."""
        return self.berries + self.bank_berries
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        total_battles = self.wins + self.losses
        return (self.wins / total_battles * 100) if total_battles > 0 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert player to dictionary for storage."""
        return {
            "berries": self.berries,
            "bank_berries": self.bank_berries,
            "devil_fruit": self.devil_fruit,
            "devil_fruit_mastery": self.devil_fruit_mastery,
            "wins": self.wins,
            "losses": self.losses,
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_taken": self.total_damage_taken,
            "achievements": self.achievements,
            "titles": self.titles,
            "current_title": self.current_title,
            "last_active": self.last_active,
            "last_daily": self.last_daily,
            "last_work": self.last_work,
            "last_gamble": self.last_gamble,
            "daily_streak": self.daily_streak,
            "stats": self.stats,
            "battle_preferences": self.battle_preferences,
            "inventory": self.inventory
       }