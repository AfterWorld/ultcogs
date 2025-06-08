"""
crewbattles/constants.py
Constants, enums, and configuration settings for the crew management system
"""

from enum import Enum


class CrewRole(Enum):
    """Enum for different crew member roles"""
    CAPTAIN = "captain"
    VICE_CAPTAIN = "vice_captain" 
    MEMBER = "member"


class InviteStatus(Enum):
    """Enum for invitation statuses"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class CrewSettings:
    """Centralized configuration settings"""
    MAX_NICKNAME_LENGTH = 30
    INVITE_EXPIRY_MINUTES = 5
    MAX_CREW_SIZE = 50
    DEFAULT_EMOJI = "🏴‍☠️"
    BACKUP_RETENTION_DAYS = 30
    
    # Logging settings
    LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
    LOG_BACKUP_COUNT = 3
    
    # Statistics thresholds
    MIN_BATTLES_FOR_RANKING = 5
    MIN_BATTLES_FOR_LEADERBOARD = 3
    
    # Performance thresholds
    HIGH_ACTIVITY_THRESHOLD = 20
    MEDIUM_ACTIVITY_THRESHOLD = 5
    EXCELLENT_WINRATE_THRESHOLD = 70
    GOOD_WINRATE_THRESHOLD = 50
    POOR_WINRATE_THRESHOLD = 40


# Default crew statistics structure
DEFAULT_CREW_STATS = {
    "wins": 0,
    "losses": 0,
    "tournaments_won": 0,
    "tournaments_participated": 0
}

# Required crew data fields for validation
REQUIRED_CREW_FIELDS = [
    "name", "emoji", "captain_role", 
    "vice_captain_role", "crew_role", "members"
]

# Discord color constants
CREW_COLORS = {
    "captain": 0xFFD700,      # Gold
    "vice_captain": 0xC0C0C0,  # Silver
    "member": 0x0099FF,        # Blue
    "separator": 0x2F3136      # Dark theme
}

# Embed colors for different states
EMBED_COLORS = {
    "success": 0x00FF00,    # Green
    "warning": 0xFF9900,    # Orange
    "error": 0xFF0000,      # Red
    "info": 0x0099FF,       # Blue
    "gold": 0xFFD700        # Gold
}