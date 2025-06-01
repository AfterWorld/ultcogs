# event_handlers.py
"""
Event handling for Hunger Games cog
"""

import discord
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GameError(Exception):
    """Base exception for game-related errors"""
    pass


class InvalidGameStateError(GameError):
    """Raised when game state is invalid"""
    pass


class EventHandler:
    """Handles event execution with proper error handling"""
    
    def __init__(self, game_engine):
        self.game_engine = game_engine
        self.handlers = {
            "death": self._handle_death_event,
            "survival": self._handle_survival_event,
            "sponsor": self._handle_sponsor_event,
            "alliance": self._handle_alliance_event,
            "crate": self._handle_crate_event
        }
    
    async def execute_event(self, event_type: str, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute event using handler mapping with error handling"""
        try:
            handler = self.handlers.get(event_type)
            if not handler:
                logger.warning(f"Unknown event type: {event_type}")
                return None
            
            return await handler(game, channel)
            
        except GameError as e:
            logger.error(f"Game error in {event_type} event: {e}")
            return self._get_fallback_message(event_type)
        except Exception as e:
            logger.error(f"Unexpected error in {event_type} event: {e}", exc_info=True)
            return None
    
    async def _handle_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Handle death events"""
        return await self.game_engine.execute_death_event(game, channel)
    
    async def _handle_survival_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Handle survival events"""
        return await self.game_engine.execute_survival_event(game)
    
    async def _handle_sponsor_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Handle sponsor events"""
        return await self.game_engine.execute_sponsor_event(game)
    
    async def _handle_alliance_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Handle alliance events"""
        return await self.game_engine.execute_alliance_event(game)
    
    async def _handle_crate_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Handle crate events"""
        return await self.game_engine.execute_crate_event(game)
    
    def _get_fallback_message(self, event_type: str) -> str:
        """Get fallback message for failed events"""
        fallbacks = {
            "death": "💀 | A mysterious death occurred in the arena...",
            "survival": "🌿 | Someone managed to survive another day...",
            "sponsor": "🎁 | A sponsor gift was mysteriously delivered...",
            "alliance": "🤝 | Tributes formed an unexpected alliance...",
            "crate": "📦 | Someone discovered hidden supplies..."
        }
        return fallbacks.get(event_type, "⚡ | Something happened in the arena...")