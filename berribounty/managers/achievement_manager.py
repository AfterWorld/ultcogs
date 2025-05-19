"""Achievement system manager for the One Piece bot."""

import asyncio
from typing import Dict, List, Any, Optional
from ..constants.achievements import ACHIEVEMENTS

class AchievementManager:
    """Manages player achievements and rewards."""
    
    def __init__(self, config, player_manager):
        self.config = config
        self.player_manager = player_manager
    
    async def check_achievements(self, player, event_type: str, **kwargs):
        """Check if player has unlocked any achievements."""
        unlocked = []
        
        for achievement_id, achievement_data in ACHIEVEMENTS.items():
            if achievement_id in player.achievements:
                continue  # Already unlocked
            
            # Check if achievement conditions are met
            if await self._check_achievement_conditions(player, achievement_data, event_type, **kwargs):
                await self._unlock_achievement(player, achievement_id, achievement_data)
                unlocked.append(achievement_data)
        
        return unlocked
    
    async def _check_achievement_conditions(self, player, achievement_data: Dict[str, Any], 
                                          event_type: str, **kwargs) -> bool:
        """Check if achievement conditions are met."""
        conditions = achievement_data.get("conditions", {})
        
        if conditions.get("event_type") != event_type:
            return False
        
        # Check various condition types
        for condition_type, condition_value in conditions.items():
            if condition_type == "event_type":
                continue
            
            if condition_type == "wins":
                if player.wins < condition_value:
                    return False
            elif condition_type == "berries":
                if player.berries < condition_value:
                    return False
            elif condition_type == "battles":
                total_battles = player.wins + player.losses
                if total_battles < condition_value:
                    return False
            elif condition_type == "devil_fruit":
                if not player.devil_fruit:
                    return False
            elif condition_type == "damage_dealt":
                if player.total_damage_dealt < condition_value:
                    return False
            # Add more condition types as needed
        
        return True
    
    async def _unlock_achievement(self, player, achievement_id: str, achievement_data: Dict[str, Any]):
        """Unlock an achievement for a player."""
        # Add to player's achievements
        player.achievements.append(achievement_id)
        
        # Give rewards
        rewards = achievement_data.get("rewards", {})
        if "berries" in rewards:
            player.add_berries(rewards["berries"])
        
        if "title" in rewards:
            if not hasattr(player, 'titles'):
                player.titles = []
            player.titles.append(rewards["title"])
        
        # Save player data
        await self.player_manager.save_player(player)
    
    async def get_player_achievements(self, player) -> List[Dict[str, Any]]:
        """Get all unlocked achievements for a player."""
        unlocked_achievements = []
        
        for achievement_id in player.achievements:
            if achievement_id in ACHIEVEMENTS:
                achievement_data = ACHIEVEMENTS[achievement_id].copy()
                achievement_data["id"] = achievement_id
                unlocked_achievements.append(achievement_data)
        
        return unlocked_achievements
    
    async def get_available_achievements(self, player) -> List[Dict[str, Any]]:
        """Get achievements that can still be unlocked."""
        available_achievements = []
        
        for achievement_id, achievement_data in ACHIEVEMENTS.items():
            if achievement_id not in player.achievements:
                achievement_copy = achievement_data.copy()
                achievement_copy["id"] = achievement_id
                available_achievements.append(achievement_copy)
        
        return available_achievements