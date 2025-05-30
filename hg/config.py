# config.py - NEW FILE
"""Configuration management for Hunger Games with centralized settings"""

from dataclasses import dataclass
from typing import Dict, Tuple, Union
import random

@dataclass
class GameConfig:
    """Centralized game configuration to eliminate magic numbers"""
    
    # Timing Configuration
    MIN_COUNTDOWN: int = 10
    MAX_COUNTDOWN: int = 300
    DEFAULT_COUNTDOWN: int = 60
    
    # Game Intervals (seconds)
    MIN_FINAL_DUEL_INTERVAL: int = 8
    MIN_ENDGAME_INTERVAL: int = 15  
    MIN_EARLY_GAME_INTERVAL: int = 25
    DEFAULT_EVENT_INTERVAL: int = 30
    MIN_EVENT_INTERVAL: int = 10
    MAX_EVENT_INTERVAL: int = 120
    
    # Player Thresholds
    MIN_PLAYERS_TO_START: int = 2
    ENDGAME_THRESHOLD: int = 5
    FINAL_DUEL_THRESHOLD: int = 2
    FINAL_THREE_THRESHOLD: int = 3
    
    # Event Configuration
    MAX_EVENTS_SMALL_GAME: Tuple[int, int] = (1, 2)    # ≤3 players
    MAX_EVENTS_MEDIUM_GAME: Tuple[int, int] = (2, 3)   # 4-6 players
    MAX_EVENTS_LARGE_GAME: Tuple[int, int] = (2, 4)    # 7-12 players
    MAX_EVENTS_HUGE_GAME: Tuple[int, int] = (3, 5)     # 13+ players
    
    # Game Progression
    STATUS_UPDATE_INTERVAL: int = 6  # Every 6 rounds
    MILESTONE_MIN_ROUND: int = 2     # Don't show milestones too early
    
    # Event Weights (percentages)
    DEFAULT_EVENT_WEIGHTS: Dict[str, int] = {
        "death": 30,
        "survival": 25,
        "sponsor": 15,
        "alliance": 15,
        "crate": 15
    }
    
    # Endgame Event Weights
    FINAL_DUEL_WEIGHTS: Dict[str, int] = {
        "death": 70,
        "survival": 10,
        "sponsor": 10,
        "alliance": 5,
        "crate": 5
    }
    
    FINAL_THREE_WEIGHTS: Dict[str, int] = {
        "death": 55,
        "survival": 15,
        "sponsor": 15,
        "alliance": 5,
        "crate": 10
    }
    
    ENDGAME_WEIGHTS: Dict[str, int] = {
        "death": 45,
        "survival": 20,
        "sponsor": 15,
        "alliance": 10,
        "crate": 10
    }
    
    # Prize Configuration
    SMALL_GAME_MULTIPLIER: float = 1.0     # < 5 players
    MEDIUM_GAME_MULTIPLIER: float = 1.5    # 5-9 players
    LARGE_GAME_MULTIPLIER: float = 2.0     # 10-19 players
    HUGE_GAME_MULTIPLIER: float = 2.5      # 20-29 players
    MASSIVE_GAME_MULTIPLIER: float = 3.0   # 30+ players
    
    # Sponsor Configuration
    MIN_SPONSOR_CHANCE: int = 1
    MAX_SPONSOR_CHANCE: int = 50
    DEFAULT_SPONSOR_CHANCE: int = 15
    
    # Admin Limits
    MIN_BASE_REWARD: int = 100
    MAX_BASE_REWARD: int = 100000
    
    # Performance Settings
    CACHE_TIMEOUT_SECONDS: int = 30
    MAX_CACHED_GAMES: int = 50


@dataclass
class ValidationConfig:
    """Validation rules and error messages"""
    
    ERROR_MESSAGES: Dict[str, str] = {
        "countdown_too_short": "Countdown must be at least {min} seconds!",
        "countdown_too_long": "Countdown cannot exceed {max} seconds!",
        "countdown_not_number": "Countdown must be a number!",
        "insufficient_players": "Need at least {min} brave souls to enter the arena!",
        "game_already_active": "A Hunger Games battle is already active!",
        "no_active_game": "No active Hunger Games in this server.",
        "invalid_event_type": "Invalid event type! Use: {types}",
        "sponsor_chance_invalid": "Sponsor chance must be between {min}-{max}%!",
        "interval_invalid": "Event interval must be between {min}-{max} seconds!",
        "reward_invalid": "Base reward must be at least {min} credits!",
        "permission_denied": "You need Manage Guild permissions to use this command!",
        "game_error": "The arena experienced technical difficulties. Game ended.",
        "player_not_found": "Player not found in the current game.",
        "invalid_game_state": "Game state is corrupted. Please restart the game."
    }
    
    VALID_EVENT_TYPES: list = ["death", "survival", "sponsor", "alliance", "crate", "random", "combined"]
    
    REQUIRED_GAME_KEYS: list = ["players", "round", "status", "eliminated", "sponsor_used"]
    REQUIRED_PLAYER_KEYS: list = ["name", "alive", "kills", "title", "district"]


class GameConfigManager:
    """Manages game configuration with validation and helper methods"""
    
    def __init__(self):
        self.game_config = GameConfig()
        self.validation_config = ValidationConfig()
    
    def get_event_count_range(self, alive_count: int) -> Tuple[int, int]:
        """Get event count range based on alive players"""
        if alive_count <= 3:
            return self.game_config.MAX_EVENTS_SMALL_GAME
        elif alive_count <= 6:
            return self.game_config.MAX_EVENTS_MEDIUM_GAME
        elif alive_count <= 12:
            return self.game_config.MAX_EVENTS_LARGE_GAME
        else:
            return self.game_config.MAX_EVENTS_HUGE_GAME
    
    def get_event_weights(self, alive_count: int) -> Dict[str, int]:
        """Get event weights based on game state"""
        if alive_count <= self.game_config.FINAL_DUEL_THRESHOLD:
            return self.game_config.FINAL_DUEL_WEIGHTS.copy()
        elif alive_count <= self.game_config.FINAL_THREE_THRESHOLD:
            return self.game_config.FINAL_THREE_WEIGHTS.copy()
        elif alive_count <= self.game_config.ENDGAME_THRESHOLD:
            return self.game_config.ENDGAME_WEIGHTS.copy()
        else:
            return self.game_config.DEFAULT_EVENT_WEIGHTS.copy()
    
    def calculate_sleep_time(self, alive_count: int, base_interval: int) -> int:
        """Calculate sleep time based on game state"""
        if alive_count <= self.game_config.FINAL_DUEL_THRESHOLD:
            return max(self.game_config.MIN_FINAL_DUEL_INTERVAL, base_interval // 3)
        elif alive_count <= 3:
            return max(10, base_interval // 3)
        elif alive_count <= self.game_config.ENDGAME_THRESHOLD:
            return max(12, base_interval // 2)
        elif alive_count <= 10:
            return max(self.game_config.MIN_ENDGAME_INTERVAL, base_interval // 2)
        else:
            return max(self.game_config.MIN_EARLY_GAME_INTERVAL, base_interval)
    
    def get_prize_multiplier(self, player_count: int) -> float:
        """Get prize multiplier based on player count"""
        if player_count < 5:
            return self.game_config.SMALL_GAME_MULTIPLIER
        elif player_count < 10:
            return self.game_config.MEDIUM_GAME_MULTIPLIER
        elif player_count < 20:
            return self.game_config.LARGE_GAME_MULTIPLIER
        elif player_count < 30:
            return self.game_config.HUGE_GAME_MULTIPLIER
        else:
            return self.game_config.MASSIVE_GAME_MULTIPLIER
    
    def validate_countdown(self, countdown: int) -> Tuple[bool, str]:
        """Validate countdown parameter"""
        if not isinstance(countdown, int):
            return False, self.validation_config.ERROR_MESSAGES["countdown_not_number"]
        
        if countdown < self.game_config.MIN_COUNTDOWN:
            return False, self.validation_config.ERROR_MESSAGES["countdown_too_short"].format(
                min=self.game_config.MIN_COUNTDOWN
            )
        
        if countdown > self.game_config.MAX_COUNTDOWN:
            return False, self.validation_config.ERROR_MESSAGES["countdown_too_long"].format(
                max=self.game_config.MAX_COUNTDOWN
            )
        
        return True, ""
    
    def validate_sponsor_chance(self, chance: int) -> Tuple[bool, str]:
        """Validate sponsor chance parameter"""
        if not (self.game_config.MIN_SPONSOR_CHANCE <= chance <= self.game_config.MAX_SPONSOR_CHANCE):
            return False, self.validation_config.ERROR_MESSAGES["sponsor_chance_invalid"].format(
                min=self.game_config.MIN_SPONSOR_CHANCE,
                max=self.game_config.MAX_SPONSOR_CHANCE
            )
        return True, ""
    
    def validate_event_interval(self, interval: int) -> Tuple[bool, str]:
        """Validate event interval parameter"""
        if not (self.game_config.MIN_EVENT_INTERVAL <= interval <= self.game_config.MAX_EVENT_INTERVAL):
            return False, self.validation_config.ERROR_MESSAGES["interval_invalid"].format(
                min=self.game_config.MIN_EVENT_INTERVAL,
                max=self.game_config.MAX_EVENT_INTERVAL
            )
        return True, ""
    
    def validate_base_reward(self, reward: int) -> Tuple[bool, str]:
        """Validate base reward parameter"""
        if reward < self.game_config.MIN_BASE_REWARD:
            return False, self.validation_config.ERROR_MESSAGES["reward_invalid"].format(
                min=self.game_config.MIN_BASE_REWARD
            )
        return True, ""
    
    def validate_event_type(self, event_type: str) -> Tuple[bool, str]:
        """Validate event type parameter"""
        if event_type.lower() not in self.validation_config.VALID_EVENT_TYPES:
            return False, self.validation_config.ERROR_MESSAGES["invalid_event_type"].format(
                types=", ".join(self.validation_config.VALID_EVENT_TYPES)
            )
        return True, ""
    
    def validate_game_state(self, game: Dict) -> bool:
        """Validate complete game state"""
        if not isinstance(game, dict):
            return False
        
        # Check required keys
        for key in self.validation_config.REQUIRED_GAME_KEYS:
            if key not in game:
                return False
        
        # Validate round number
        if not isinstance(game.get("round"), int) or game["round"] < 0:
            return False
        
        # Validate players structure
        players = game.get("players", {})
        if not isinstance(players, dict):
            return False
        
        # Validate each player
        for player_id, player_data in players.items():
            if not self.validate_player_data(player_data):
                return False
        
        return True
    
    def validate_player_data(self, player_data: Dict) -> bool:
        """Validate individual player data structure"""
        if not isinstance(player_data, dict):
            return False
        
        # Check required keys
        for key in self.validation_config.REQUIRED_PLAYER_KEYS:
            if key not in player_data:
                return False
        
        # Validate data types
        if not isinstance(player_data.get("alive"), bool):
            return False
        
        if not isinstance(player_data.get("kills"), int) or player_data["kills"] < 0:
            return False
        
        if not isinstance(player_data.get("name"), str):
            return False
        
        return True
    
    def get_random_event_count(self, alive_count: int) -> int:
        """Get random event count for the given player count"""
        min_events, max_events = self.get_event_count_range(alive_count)
        return random.randint(min_events, max_events)
    
    def should_show_milestone(self, game: Dict, milestone_type: str) -> bool:
        """Determine if milestone should be shown"""
        if game["round"] < self.game_config.MILESTONE_MIN_ROUND:
            return False
        
        milestones_shown = game.get("milestones_shown", set())
        return milestone_type not in milestones_shown
    
    def should_send_status_update(self, round_num: int, alive_count: int) -> bool:
        """Determine if status update should be sent"""
        return (round_num % self.game_config.STATUS_UPDATE_INTERVAL == 0 and 
                alive_count > 8)


# Global instance for easy importing
game_config_manager = GameConfigManager()
