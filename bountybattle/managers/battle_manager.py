import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class BattleStateManager:
    """Manages battle states and related operations."""
    
    def __init__(self):
        self.active_battles = {}
        self.battle_locks = {}
        self._cleanup_threshold = 100  # Maximum number of stored battle states
        self._max_duration = 300  # Maximum battle duration in seconds

    async def create_battle(self, channel_id: int, challenger_data: dict, opponent_data: dict):
        """Create a new battle state."""
        if len(self.active_battles) >= self._cleanup_threshold:
            await self._cleanup_old_battles()
        
        battle_state = {
            "start_time": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "challenger": challenger_data,
            "opponent": opponent_data,
            "turn": 0,
            "current_player": 0,
            "environment": None,
            "battle_log": [],
            "is_finished": False
        }
        
        self.active_battles[channel_id] = battle_state
        self.battle_locks[channel_id] = asyncio.Lock()
        
        return battle_state

    async def end_battle(self, channel_id: int):
        """Clean up battle state after it ends."""
        if channel_id in self.active_battles:
            async with self.battle_locks[channel_id]:
                battle_state = self.active_battles[channel_id]
                battle_state["is_finished"] = True
                
                # Clean up
                del self.active_battles[channel_id]
                del self.battle_locks[channel_id]

    def is_channel_in_battle(self, channel_id: int) -> bool:
        """Check if a channel has an active battle."""
        return channel_id in self.active_battles

    async def _cleanup_old_battles(self):
        """Remove old or inactive battles."""
        current_time = datetime.utcnow()
        channels_to_remove = []

        for channel_id, battle in self.active_battles.items():
            battle_age = (current_time - battle["start_time"]).total_seconds()
            if battle_age > self._max_duration:
                channels_to_remove.append(channel_id)

        for channel_id in channels_to_remove:
            await self.end_battle(channel_id)