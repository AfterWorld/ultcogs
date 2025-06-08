"""
crewbattles/models.py
Data models and classes for the crew management system
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import datetime

from .constants import CrewRole, InviteStatus, DEFAULT_CREW_STATS


@dataclass
class CrewStats:
    """Enhanced crew statistics with calculated properties"""
    wins: int = 0
    losses: int = 0
    tournaments_won: int = 0
    tournaments_participated: int = 0
    
    @property
    def total_battles(self) -> int:
        """Calculate total battles fought"""
        return self.wins + self.losses
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        return (self.wins / self.total_battles * 100) if self.total_battles > 0 else 0.0
    
    @property
    def tournament_win_rate(self) -> float:
        """Calculate tournament win rate percentage"""
        return (self.tournaments_won / self.tournaments_participated * 100) if self.tournaments_participated > 0 else 0.0
    
    @property
    def loss_rate(self) -> float:
        """Calculate loss rate percentage"""
        return (self.losses / self.total_battles * 100) if self.total_battles > 0 else 0.0
    
    def add_win(self) -> None:
        """Add a win to the statistics"""
        self.wins += 1
    
    def add_loss(self) -> None:
        """Add a loss to the statistics"""
        self.losses += 1
    
    def add_tournament_participation(self) -> None:
        """Add tournament participation"""
        self.tournaments_participated += 1
    
    def add_tournament_win(self) -> None:
        """Add a tournament win"""
        self.tournaments_won += 1
        self.add_tournament_participation()
    
    def get_performance_level(self) -> str:
        """Get performance level description"""
        if self.total_battles == 0:
            return "No battles yet"
        elif self.win_rate >= 70:
            return "Excellent"
        elif self.win_rate >= 50:
            return "Good"
        elif self.win_rate >= 30:
            return "Average"
        else:
            return "Needs Improvement"
    
    def get_activity_level(self) -> str:
        """Get activity level description"""
        if self.total_battles >= 20:
            return "High"
        elif self.total_battles >= 5:
            return "Medium"
        else:
            return "Low"
    
    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for JSON serialization"""
        return {
            "wins": self.wins,
            "losses": self.losses,
            "tournaments_won": self.tournaments_won,
            "tournaments_participated": self.tournaments_participated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrewStats':
        """Create from dictionary (backwards compatible)"""
        return cls(
            wins=data.get('wins', 0),
            losses=data.get('losses', 0),
            tournaments_won=data.get('tournaments_won', 0),
            tournaments_participated=data.get('tournaments_participated', 0)
        )


@dataclass
class CrewMember:
    """Enhanced member data with role tracking"""
    user_id: int
    joined_at: str
    role: CrewRole = CrewRole.MEMBER
    battles_participated: int = 0
    last_active: Optional[str] = None
    
    def __post_init__(self):
        """Set default values after initialization"""
        if self.last_active is None:
            self.last_active = datetime.datetime.now().isoformat()
    
    def promote_to_vice_captain(self) -> None:
        """Promote member to vice captain"""
        self.role = CrewRole.VICE_CAPTAIN
    
    def promote_to_captain(self) -> None:
        """Promote member to captain"""
        self.role = CrewRole.CAPTAIN
    
    def demote_to_member(self) -> None:
        """Demote to regular member"""
        self.role = CrewRole.MEMBER
    
    def update_activity(self) -> None:
        """Update last active timestamp"""
        self.last_active = datetime.datetime.now().isoformat()
    
    def add_battle_participation(self) -> None:
        """Increment battle participation count"""
        self.battles_participated += 1
        self.update_activity()
    
    @property
    def days_since_joined(self) -> int:
        """Calculate days since joining"""
        try:
            joined_date = datetime.datetime.fromisoformat(self.joined_at)
            return (datetime.datetime.now() - joined_date).days
        except:
            return 0
    
    @property
    def is_active(self) -> bool:
        """Check if member has been active recently (within 30 days)"""
        if not self.last_active:
            return False
        try:
            last_active_date = datetime.datetime.fromisoformat(self.last_active)
            days_inactive = (datetime.datetime.now() - last_active_date).days
            return days_inactive <= 30
        except:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "joined_at": self.joined_at,
            "role": self.role.value,
            "battles_participated": self.battles_participated,
            "last_active": self.last_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrewMember':
        """Create from dictionary"""
        return cls(
            user_id=data['user_id'],
            joined_at=data['joined_at'],
            role=CrewRole(data.get('role', CrewRole.MEMBER.value)),
            battles_participated=data.get('battles_participated', 0),
            last_active=data.get('last_active')
        )


@dataclass
class InviteData:
    """Data structure for crew invitations"""
    guild_id: str
    crew_name: str
    inviter_id: int
    invitee_id: int
    channel_id: int
    expires_at: datetime.datetime
    status: InviteStatus = InviteStatus.PENDING
    created_at: Optional[datetime.datetime] = None
    
    def __post_init__(self):
        """Set default values after initialization"""
        if self.created_at is None:
            self.created_at = datetime.datetime.now()
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return datetime.datetime.now() > self.expires_at
    
    @property
    def time_remaining(self) -> datetime.timedelta:
        """Get time remaining until expiration"""
        return max(datetime.timedelta(0), self.expires_at - datetime.datetime.now())
    
    def accept(self) -> None:
        """Mark invitation as accepted"""
        self.status = InviteStatus.ACCEPTED
    
    def decline(self) -> None:
        """Mark invitation as declined"""
        self.status = InviteStatus.DECLINED
    
    def expire(self) -> None:
        """Mark invitation as expired"""
        self.status = InviteStatus.EXPIRED


@dataclass
class CrewData:
    """Complete crew data structure"""
    name: str
    emoji: str
    tag: str
    members: List[int]  # Keep for backwards compatibility
    enhanced_members: List[CrewMember]  # New enhanced member tracking
    captain_role: int
    vice_captain_role: int
    crew_role: int
    stats: CrewStats
    created_at: str
    description: str = ""
    color: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default values and ensure data consistency"""
        # Ensure stats is a CrewStats object
        if isinstance(self.stats, dict):
            self.stats = CrewStats.from_dict(self.stats)
        
        # Sync enhanced_members with members list for backwards compatibility
        if not self.enhanced_members and self.members:
            self.enhanced_members = [
                CrewMember(
                    user_id=member_id,
                    joined_at=self.created_at,
                    role=CrewRole.MEMBER
                ) for member_id in self.members
            ]
    
    @property
    def member_count(self) -> int:
        """Get total member count"""
        return len(self.members)
    
    @property
    def captain_count(self) -> int:
        """Get number of captains"""
        return sum(1 for member in self.enhanced_members if member.role == CrewRole.CAPTAIN)
    
    @property
    def vice_captain_count(self) -> int:
        """Get number of vice captains"""
        return sum(1 for member in self.enhanced_members if member.role == CrewRole.VICE_CAPTAIN)
    
    @property
    def regular_member_count(self) -> int:
        """Get number of regular members"""
        return sum(1 for member in self.enhanced_members if member.role == CrewRole.MEMBER)
    
    @property
    def active_member_count(self) -> int:
        """Get number of active members"""
        return sum(1 for member in self.enhanced_members if member.is_active)
    
    @property
    def days_active(self) -> int:
        """Get days since crew creation"""
        try:
            created_date = datetime.datetime.fromisoformat(self.created_at)
            return (datetime.datetime.now() - created_date).days
        except:
            return 0
    
    def get_member_by_id(self, user_id: int) -> Optional[CrewMember]:
        """Get enhanced member data by user ID"""
        return next((member for member in self.enhanced_members if member.user_id == user_id), None)
    
    def add_member(self, user_id: int, role: CrewRole = CrewRole.MEMBER) -> CrewMember:
        """Add a new member to the crew"""
        # Add to legacy members list
        if user_id not in self.members:
            self.members.append(user_id)
        
        # Create enhanced member data
        new_member = CrewMember(
            user_id=user_id,
            joined_at=datetime.datetime.now().isoformat(),
            role=role
        )
        
        # Add to enhanced members if not already present
        existing_member = self.get_member_by_id(user_id)
        if not existing_member:
            self.enhanced_members.append(new_member)
        else:
            existing_member.role = role
            return existing_member
        
        return new_member
    
    def remove_member(self, user_id: int) -> bool:
        """Remove a member from the crew"""
        # Remove from legacy members list
        if user_id in self.members:
            self.members.remove(user_id)
        
        # Remove from enhanced members
        self.enhanced_members = [
            member for member in self.enhanced_members 
            if member.user_id != user_id
        ]
        
        return True
    
    def promote_member(self, user_id: int, new_role: CrewRole) -> bool:
        """Promote a member to a new role"""
        member = self.get_member_by_id(user_id)
        if member:
            member.role = new_role
            return True
        return False
    
    def sync_members_list(self) -> None:
        """Sync the legacy members list with enhanced members"""
        self.members = [member.user_id for member in self.enhanced_members]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "emoji": self.emoji,
            "tag": self.tag,
            "members": self.members,
            "enhanced_members": [member.to_dict() for member in self.enhanced_members],
            "captain_role": self.captain_role,
            "vice_captain_role": self.vice_captain_role,
            "crew_role": self.crew_role,
            "stats": self.stats.to_dict(),
            "created_at": self.created_at,
            "description": self.description,
            "color": self.color
        }
    
    @classmethod
    def from_legacy_dict(cls, data: Dict[str, Any]) -> 'CrewData':
        """Create from legacy crew data (backwards compatible)"""
        # Handle legacy stats format
        stats_data = data.get('stats', DEFAULT_CREW_STATS)
        stats = CrewStats.from_dict(stats_data)
        
        # Convert legacy members to enhanced format
        legacy_members = data.get('members', [])
        enhanced_members = []
        
        # Load enhanced members if available, otherwise convert from legacy
        if 'enhanced_members' in data:
            enhanced_members = [
                CrewMember.from_dict(member_data) 
                for member_data in data['enhanced_members']
            ]
        else:
            # Convert legacy members
            for member_id in legacy_members:
                enhanced_members.append(CrewMember(
                    user_id=member_id,
                    joined_at=data.get('created_at', datetime.datetime.now().isoformat()),
                    role=CrewRole.MEMBER
                ))
        
        # Generate tag if missing
        tag = data.get('tag', '')
        if not tag and data.get('name'):
            words = data['name'].split()
            tag = "".join(word[0] for word in words if word).upper()[:4]
        
        return cls(
            name=data['name'],
            emoji=data.get('emoji', '🏴‍☠️'),
            tag=tag,
            members=legacy_members,
            enhanced_members=enhanced_members,
            captain_role=data['captain_role'],
            vice_captain_role=data['vice_captain_role'],
            crew_role=data['crew_role'],
            stats=stats,
            created_at=data.get('created_at', datetime.datetime.now().isoformat()),
            description=data.get('description', ''),
            color=data.get('color')
        )