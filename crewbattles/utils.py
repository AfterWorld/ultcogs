"""
crewbattles/utils.py
Utility functions and helper classes for crew management
"""

from typing import Dict, List, Optional, Tuple
import discord
import datetime
import hashlib

from .constants import CrewRole, CrewSettings
from .logger import EnhancedCrewLogger


class NicknameManager:
    """Handles nickname operations safely with enhanced error handling"""
    
    def __init__(self, logger: EnhancedCrewLogger):
        self.logger = logger
    
    @staticmethod
    def generate_crew_tag(crew_name: str) -> str:
        """Generate a crew tag from the crew name"""
        if not crew_name:
            return "CREW"
        
        words = crew_name.split()
        tag = "".join(word[0] for word in words if word and word[0].isalpha()).upper()
        
        # Ensure tag is not empty and has reasonable length
        if not tag:
            tag = crew_name[:4].upper()
        
        return tag[:4]  # Limit to 4 characters
    
    @staticmethod
    def truncate_nickname(
        original_name: str, 
        emoji_prefix: str, 
        max_length: Optional[int] = None
    ) -> str:
        """Enhanced nickname truncation with better handling"""
        if max_length is None:
            max_length = CrewSettings.MAX_NICKNAME_LENGTH
        
        # Handle custom emoji length more accurately
        if emoji_prefix.startswith('<:') or emoji_prefix.startswith('<a:'):
            emoji_display_len = 2  # Approximate display length for custom emojis
        else:
            emoji_display_len = len(emoji_prefix)
        
        # Account for space between emoji and name
        available_length = max_length - emoji_display_len - 1
        
        if len(original_name) <= available_length:
            return original_name
        
        # Truncate and add ellipsis if there's room
        if available_length > 3:
            return original_name[:available_length-3] + "..."
        else:
            return original_name[:available_length]
    
    async def set_crew_nickname(
        self, 
        member: discord.Member, 
        crew_emoji: str, 
        crew_tag: Optional[str] = None,
        role: CrewRole = CrewRole.MEMBER
    ) -> Tuple[bool, str]:
        """
        Set crew nickname with enhanced error handling
        Returns: (success, error_message)
        """
        try:
            original_name = member.display_name
            
            # Remove existing crew emoji if present
            clean_name = self._clean_existing_crew_prefix(original_name, crew_emoji)
            
            # Build new nickname based on role
            nickname_base = self._build_nickname_base(clean_name, crew_tag, role)
            
            # Apply emoji and truncate if needed
            final_nickname = self._finalize_nickname(nickname_base, crew_emoji, crew_tag)
            
            # Apply the nickname
            await member.edit(nick=final_nickname)
            
            self.logger.log_user_action(
                "nickname_set", member.id, member.guild.id,
                old_nick=original_name,
                new_nick=final_nickname,
                role=role.value
            )
            
            return True, ""
            
        except discord.Forbidden:
            error_msg = "Insufficient permissions to change nickname"
            self.logger.log_user_action(
                "nickname_failed", member.id, member.guild.id, False,
                error="forbidden", role=role.value
            )
            return False, error_msg
            
        except discord.HTTPException as e:
            error_msg = f"Discord API error: {str(e)}"
            self.logger.log_user_action(
                "nickname_failed", member.id, member.guild.id, False,
                error=str(e), role=role.value
            )
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.logger.log_error_with_context(
                e, "set_crew_nickname", member.guild.id, member.id
            )
            return False, error_msg
    
    def _clean_existing_crew_prefix(self, original_name: str, crew_emoji: str) -> str:
        """Remove existing crew emoji/prefix from nickname"""
        clean_name = original_name
        
        # Remove crew emoji if present
        if clean_name.startswith(crew_emoji):
            clean_name = clean_name[len(crew_emoji):].strip()
        
        # Remove common crew prefixes
        prefixes_to_remove = ['[', '🏴‍☠️', '⚓', '🏆', '⭐']
        for prefix in prefixes_to_remove:
            if clean_name.startswith(prefix):
                # Find the closing bracket or space
                if prefix == '[':
                    end_pos = clean_name.find(']')
                    if end_pos != -1:
                        clean_name = clean_name[end_pos+1:].strip()
                else:
                    clean_name = clean_name[len(prefix):].strip()
        
        return clean_name if clean_name else original_name
    
    def _build_nickname_base(
        self, 
        clean_name: str, 
        crew_tag: Optional[str], 
        role: CrewRole
    ) -> str:
        """Build the base nickname based on role and tag"""
        if role == CrewRole.CAPTAIN:
            if crew_tag:
                return f"[{crew_tag}] Captain"
            else:
                return "Captain"
        elif role == CrewRole.VICE_CAPTAIN:
            if crew_tag:
                return f"[{crew_tag}] Vice"
            else:
                return "Vice Captain"
        else:
            # Regular member - use their name with crew tag
            if crew_tag:
                return f"[{crew_tag}] {clean_name}"
            else:
                return clean_name
    
    def _finalize_nickname(
        self, 
        nickname_base: str, 
        crew_emoji: str, 
        crew_tag: Optional[str]
    ) -> str:
        """Finalize nickname with emoji and handle length constraints"""
        # Truncate if needed
        truncated_name = self.truncate_nickname(nickname_base, crew_emoji)
        final_nickname = f"{crew_emoji} {truncated_name}"
        
        # Handle oversized nicknames with fallback strategies
        if len(final_nickname) > 32:
            fallback_strategies = [
                f"{crew_emoji} [{crew_tag}]" if crew_tag else None,
                f"🏴‍☠️ [{crew_tag}]" if crew_tag else None,
                f"🏴‍☠️ Crew",
                "Crew Member"
            ]
            
            for fallback in fallback_strategies:
                if fallback and len(fallback) <= 32:
                    final_nickname = fallback
                    break
        
        return final_nickname
    
    async def restore_original_nickname(self, member: discord.Member, crew_emoji: str) -> bool:
        """Restore member's original nickname by removing crew prefixes"""
        try:
            current_nick = member.display_name
            clean_name = self._clean_existing_crew_prefix(current_nick, crew_emoji)
            
            # Only change if there's actually a difference
            if clean_name != current_nick:
                await member.edit(nick=clean_name if clean_name else None)
                
                self.logger.log_user_action(
                    "nickname_restored", member.id, member.guild.id,
                    old_nick=current_nick,
                    new_nick=clean_name
                )
            
            return True
        except discord.Forbidden:
            return False
        except Exception as e:
            self.logger.log_error_with_context(
                e, "restore_original_nickname", member.guild.id, member.id
            )
            return False


class EmbedBuilder:
    """Helper class for building consistent Discord embeds"""
    
    @staticmethod
    def create_crew_embed(
        title: str, 
        description: str = "",
        color: Optional[int] = None,
        crew_name: Optional[str] = None
    ) -> discord.Embed:
        """Create a standard crew embed with consistent styling"""
        if color is None:
            if crew_name:
                # Generate color based on crew name
                color = int(hashlib.md5(crew_name.encode()).hexdigest()[:6], 16)
            else:
                color = 0x0099FF
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now()
        )
        
        embed.set_footer(text="Enhanced Crew System")
        return embed
    
    @staticmethod
    def create_success_embed(title: str, description: str = "") -> discord.Embed:
        """Create a success embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=0x00FF00,
            timestamp=datetime.datetime.now()
        )
        return embed
    
    @staticmethod
    def create_error_embed(title: str, description: str = "") -> discord.Embed:
        """Create an error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=0xFF0000,
            timestamp=datetime.datetime.now()
        )
        return embed
    
    @staticmethod
    def create_warning_embed(title: str, description: str = "") -> discord.Embed:
        """Create a warning embed"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=0xFF9900,
            timestamp=datetime.datetime.now()
        )
        return embed
    
    @staticmethod
    def create_info_embed(title: str, description: str = "") -> discord.Embed:
        """Create an info embed"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=description,
            color=0x0099FF,
            timestamp=datetime.datetime.now()
        )
        return embed


class ValidationUtils:
    """Utility functions for data validation"""
    
    @staticmethod
    def validate_crew_name(name: str) -> Tuple[bool, str]:
        """Validate crew name format"""
        if not name or not name.strip():
            return False, "Crew name cannot be empty"
        
        name = name.strip()
        
        if len(name) > 50:
            return False, "Crew name must be 50 characters or less"
        
        if len(name) < 2:
            return False, "Crew name must be at least 2 characters"
        
        # Check for invalid characters
        if name.startswith('<@') or '@everyone' in name or '@here' in name:
            return False, "Crew name cannot contain mentions"
        
        # Check for Discord markdown that might break things
        invalid_chars = ['`', '*', '_', '~', '|']
        if any(char in name for char in invalid_chars):
            return False, "Crew name cannot contain markdown characters"
        
        return True, ""
    
    @staticmethod
    def validate_emoji(emoji: str) -> Tuple[bool, str]:
        """Validate emoji format"""
        if not emoji:
            return False, "Emoji cannot be empty"
        
        # Check if it's a custom Discord emoji
        if emoji.startswith('<:') or emoji.startswith('<a:'):
            if not emoji.endswith('>'):
                return False, "Invalid custom emoji format"
            
            parts = emoji.split(':')
            if len(parts) < 3:
                return False, "Invalid custom emoji format"
            
            try:
                int(parts[2][:-1])  # Check if ID is valid
            except ValueError:
                return False, "Invalid emoji ID"
        
        return True, ""
    
    @staticmethod
    def validate_tag(tag: str) -> Tuple[bool, str]:
        """Validate crew tag format"""
        if not tag:
            return False, "Tag cannot be empty"
        
        tag = tag.upper().strip()
        
        if len(tag) > 4:
            return False, "Tag must be 4 characters or less"
        
        if not tag.isalnum():
            return False, "Tag must contain only letters and numbers"
        
        return True, ""


class PermissionUtils:
    """Utility functions for permission checking"""
    
    @staticmethod
    def can_manage_crews(member: discord.Member) -> bool:
        """Check if member can manage crews (admin or specific permission)"""
        return (
            member.guild_permissions.administrator or
            member.guild_permissions.manage_roles or
            member.guild_permissions.manage_guild
        )
    
    @staticmethod
    def can_invite_members(member: discord.Member, crew_roles: Dict[str, int]) -> bool:
        """Check if member can invite others to crew"""
        captain_role_id = crew_roles.get('captain_role')
        vice_captain_role_id = crew_roles.get('vice_captain_role')
        
        if captain_role_id and any(role.id == captain_role_id for role in member.roles):
            return True
        
        if vice_captain_role_id and any(role.id == vice_captain_role_id for role in member.roles):
            return True
        
        return PermissionUtils.can_manage_crews(member)
    
    @staticmethod
    def can_kick_members(member: discord.Member, crew_roles: Dict[str, int]) -> bool:
        """Check if member can kick others from crew"""
        return PermissionUtils.can_invite_members(member, crew_roles)
    
    @staticmethod
    def can_promote_members(member: discord.Member, crew_roles: Dict[str, int]) -> bool:
        """Check if member can promote others in crew"""
        captain_role_id = crew_roles.get('captain_role')
        
        if captain_role_id and any(role.id == captain_role_id for role in member.roles):
            return True
        
        return PermissionUtils.can_manage_crews(member)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:.0f}m {secs:.0f}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:.0f}h {minutes:.0f}m"


def safe_get_member(guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
    """Safely get a member from guild, handling errors"""
    try:
        return guild.get_member(user_id)
    except:
        return None


def safe_get_role(guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
    """Safely get a role from guild, handling errors"""
    try:
        return guild.get_role(role_id)
    except:
        return None