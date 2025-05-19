"""Devil fruit management for the One Piece bot."""

from typing import List, Dict, Any, Optional
from ..models.player import Player
from ..constants.fruits import DEVIL_FRUITS

class FruitManager:
    """Manages devil fruit operations."""
    
    def __init__(self, config, player_manager):
        self.config = config
        self.player_manager = player_manager
    
    async def give_fruit(self, player: Player, fruit_name: str) -> bool:
        """Give a devil fruit to a player."""
        # Check if player already has a fruit
        if player.devil_fruit:
            return False
        
        # Find the fruit in the constants
        fruit_data = None
        for category, fruits in DEVIL_FRUITS.items():
            if fruit_name in fruits:
                fruit_data = fruits[fruit_name]
                break
        
        if not fruit_data:
            return False
        
        # Give the fruit to the player
        player.devil_fruit = fruit_name
        player.devil_fruit_mastery[fruit_name] = 0
        
        # Save player data
        await self.player_manager.save_player(player)
        
        return True
    
    async def remove_fruit(self, player: Player) -> bool:
        """Remove a devil fruit from a player."""
        if not player.devil_fruit:
            return False
        
        # Remove the fruit
        fruit_name = player.devil_fruit
        player.devil_fruit = None
        
        # Keep mastery for potential future use
        # del player.devil_fruit_mastery[fruit_name]
        
        # Save player data
        await self.player_manager.save_player(player)
        
        return True
    
    def get_available_fruits(self, category: str = None) -> List[str]:
        """Get list of available devil fruits."""
        if category:
            if category in DEVIL_FRUITS:
                return list(DEVIL_FRUITS[category].keys())
            return []
        
        # Return all fruits
        all_fruits = []
        for fruits in DEVIL_FRUITS.values():
            all_fruits.extend(fruits.keys())
        return all_fruits
    
    async def get_fruit_owners(self, guild) -> Dict[str, Player]:
        """Get all players who own devil fruits in a guild."""
        fruit_owners = {}
        all_players = await self.player_manager.get_all_players(guild)
        
        for player in all_players:
            if player.devil_fruit:
                fruit_owners[player.devil_fruit] = player
        
        return fruit_owners
    
    async def increase_mastery(self, player: Player, amount: int = 2):
        """Increase a player's devil fruit mastery."""
        if not player.devil_fruit:
            return
        
        fruit_name = player.devil_fruit
        current_mastery = player.devil_fruit_mastery.get(fruit_name, 0)
        new_mastery = min(100, current_mastery + amount)
        
        player.devil_fruit_mastery[fruit_name] = new_mastery
        
        # Save player data
        await self.player_manager.save_player(player)
        
        return new_mastery
    
    def get_fruit_data(self, fruit_name: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific devil fruit."""
        for category, fruits in DEVIL_FRUITS.items():
            if fruit_name in fruits:
                return fruits[fruit_name]
        return None
    
    def search_fruits(self, query: str) -> List[str]:
        """Search for fruits by name."""
        matches = []
        query_lower = query.lower()
        
        for category, fruits in DEVIL_FRUITS.items():
            for fruit_name in fruits.keys():
                if query_lower in fruit_name.lower():
                    matches.append(fruit_name)
        
        return matches
    
    async def calculate_fruit_bonus(self, fruit_name: str, move: Dict[str, Any]) -> int:
        """Calculate bonus damage for devil fruit users."""
        fruit_data = self.get_fruit_data(fruit_name)
        if not fruit_data:
            return 0
        
        # Basic fruit bonus
        base_bonus = 10
        
        # Type-specific bonuses
        fruit_type = fruit_data.get("type", "")
        move_type = move.get("type", "")
        
        if fruit_type == "Logia":
            base_bonus += 15
        elif fruit_type == "Paramecia":
            base_bonus += 10
        elif fruit_type == "Zoan":
            base_bonus += 5
        
        # Elemental matching bonuses
        if "fire" in fruit_name.lower() and "fire" in move.get("name", "").lower():
            base_bonus += 20
        elif "ice" in fruit_name.lower() and "ice" in move.get("name", "").lower():
            base_bonus += 20
        
        return base_bonus