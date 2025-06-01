# validators.py
"""
Input validation for Hunger Games cog
"""

import logging
from typing import Dict, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class InputValidator:
    """Handles all input validation for the game"""
    
    @staticmethod
    def validate_countdown(countdown: int) -> Tuple[bool, str]:
        """Validate countdown parameter"""
        if not isinstance(countdown, int):
            return False, "Countdown must be a number!"
        
        if countdown < 10:
            return False, "Countdown must be at least 10 seconds!"
        
        if countdown > 300:
            return False, "Countdown cannot exceed 5 minutes!"
        
        return True, ""
    
    @staticmethod
    def validate_base_reward(amount: int) -> Tuple[bool, str]:
        """Validate base reward amount"""
        if amount < 100:
            return False, "Base reward must be at least 100 credits!"
        return True, ""
    
    @staticmethod
    def validate_sponsor_chance(chance: int) -> Tuple[bool, str]:
        """Validate sponsor chance"""
        if not 1 <= chance <= 50:
            return False, "Sponsor chance must be between 1-50%!"
        return True, ""
    
    @staticmethod
    def validate_event_interval(seconds: int) -> Tuple[bool, str]:
        """Validate event interval"""
        if not 10 <= seconds <= 120:
            return False, "Event interval must be between 10-120 seconds!"
        return True, ""
    
    @staticmethod
    def validate_poll_threshold(threshold: int) -> Tuple[bool, str]:
        """Validate poll threshold"""
        if threshold < 2:
            return False, "Threshold must be at least 2 players!"
        
        if threshold > 50:
            return False, "Threshold cannot exceed 50 players!"
        
        return True, ""
    
    @staticmethod
    def validate_game_state(game: Dict) -> bool:
        """Validate game state integrity"""
        try:
            required_keys = ["players", "round", "status", "eliminated"]
            if not all(key in game for key in required_keys):
                return False
            
            if game["round"] < 0:
                return False
            
            if not isinstance(game["players"], dict):
                return False
            
            # Validate player data structure
            for player_id, player_data in game["players"].items():
                if not isinstance(player_data, dict):
                    return False
                
                required_player_keys = ["name", "alive", "kills"]
                if not all(key in player_data for key in required_player_keys):
                    return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_temp_ban_duration(duration: str) -> Tuple[bool, str, int]:
        """Validate and parse temporary ban duration
        
        Returns: (is_valid, error_message, total_seconds)
        """
        try:
            import re
            
            if duration.lower() == "remove":
                return True, "", 0
            
            # Parse duration string (e.g., "1h30m", "2d", "45m")
            pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?'
            match = re.match(pattern, duration.lower())
            
            if not match:
                return False, "Invalid duration format! Use examples: 1h, 30m, 1d, 2h30m", 0
            
            days, hours, minutes = match.groups()
            total_seconds = 0
            
            if days:
                total_seconds += int(days) * 86400
            if hours:
                total_seconds += int(hours) * 3600
            if minutes:
                total_seconds += int(minutes) * 60
            
            if total_seconds == 0:
                return False, "Duration must be greater than 0!", 0
            
            if total_seconds > 2592000:  # 30 days max
                return False, "Maximum ban duration is 30 days!", 0
            
            return True, "", total_seconds
            
        except Exception as e:
            logger.error(f"Error parsing duration: {e}")
            return False, "Invalid duration format! Use examples: 1h, 30m, 1d, 2h30m", 0
    
    @staticmethod
    async def validate_poll_starter(user, config) -> str:
        """Validate if user can start a poll
        
        Returns error message if invalid, empty string if valid
        """
        try:
            # Check blacklisted roles
            blacklisted_roles = await config.guild(user.guild).blacklisted_roles()
            if any(user.get_role(role_id) for role_id in blacklisted_roles):
                return "❌ You aren't allowed to start Hunger Games in this server due to your roles!"
            
            # Check temporary ban
            temp_banned_until = await config.member(user).temp_banned_until()
            if temp_banned_until is not None:
                if datetime.now(timezone.utc).timestamp() < temp_banned_until:
                    remaining = temp_banned_until - datetime.now(timezone.utc).timestamp()
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    return f"❌ You are temporarily banned for {hours}h {minutes}m!"
            
            return ""  # All checks passed
            
        except Exception as e:
            logger.error(f"Error validating poll starter {user.id}: {e}")
            return "❌ Error checking your eligibility. Please try again."