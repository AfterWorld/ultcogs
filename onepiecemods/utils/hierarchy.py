# onepiecemods/utils/hierarchy.py - Improved Version
import discord
from discord.ext import commands
from typing import Optional, Tuple, Union
import re
import logging

logger = logging.getLogger("red.onepiecemods.hierarchy")

async def check_hierarchy(ctx: commands.Context, member: discord.Member, error_message: Optional[str] = None) -> bool:
    """
    Comprehensive hierarchy checks for moderation actions.
    
    Args:
        ctx: Command context
        member: Target member to check
        error_message: Custom error message for bot hierarchy failures
        
    Returns:
        bool: True if all hierarchy checks pass, False otherwise
        
    Checks performed:
    - Self-moderation prevention
    - Bot moderation prevention  
    - Administrator protection
    - Role hierarchy validation
    - Bot permission validation
    """
    
    # Prevent self-moderation
    if member.id == ctx.author.id:
        await ctx.send("🤔 You can't moderate yourself! That's not how Devil Fruits work!")
        return False
    
    # Prevent moderating bots (unless admin)
    if member.bot and not ctx.author.guild_permissions.administrator:
        await ctx.send("🤖 You cannot moderate bots without administrator permissions!")
        return False
    
    # Prevent moderating the guild owner (unless they are the owner)
    if member.id == ctx.guild.owner_id and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("👑 You cannot moderate the server owner!")
        return False
    
    # Check if target is a moderator/admin and author isn't admin
    if (member.guild_permissions.manage_messages or member.guild_permissions.administrator) and not ctx.author.guild_permissions.administrator:
        await ctx.send("⚔️ You cannot moderate another moderator or administrator!")
        return False
    
    # Check role hierarchy for non-owners
    if ctx.author.id != ctx.guild.owner_id:
        if member.top_role >= ctx.author.top_role:
            await ctx.send("📊 You cannot moderate a member with a higher or equal role!")
            return False
    
    # Check bot's role hierarchy
    if member.top_role >= ctx.guild.me.top_role:
        if error_message:
            await ctx.send(error_message)
        else:
            await ctx.send("🤖 I cannot moderate a member with a higher role than me!")
        return False
    
    # Additional permission check for bot
    required_perms = _get_required_permissions(ctx.command.name if ctx.command else "")
    if required_perms and not _check_bot_permissions(ctx.guild.me, required_perms):
        missing = [perm for perm, value in required_perms.items() if not getattr(ctx.guild.me.guild_permissions, perm, False)]
        await ctx.send(f"❌ I'm missing required permissions: {', '.join(missing)}")
        return False
    
    return True

def _get_required_permissions(command_name: str) -> Optional[dict]:
    """Get required permissions for specific commands"""
    permission_map = {
        "luffykick": {"kick_members": True},
        "shanksban": {"ban_members": True},
        "lawroom": {"manage_roles": True, "moderate_members": True},
        "impeldown": {"manage_roles": True, "moderate_members": True},
        "liberate": {"manage_roles": True, "moderate_members": True}
    }
    
    return permission_map.get(command_name)

def _check_bot_permissions(bot_member: discord.Member, required_perms: dict) -> bool:
    """Check if bot has all required permissions"""
    for perm, required in required_perms.items():
        if required and not getattr(bot_member.guild_permissions, perm, False):
            return False
    return True

def sanitize_reason(reason: Optional[str], max_length: int = 512) -> str:
    """
    Advanced reason sanitization with content filtering.
    
    Args:
        reason: Raw reason string
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized reason string
    """
    if not reason:
        return "No reason provided"
    
    # Strip whitespace
    reason = reason.strip()
    
    # Remove excessive whitespace
    reason = re.sub(r'\s+', ' ', reason)
    
    # Remove potentially problematic characters
    reason = re.sub(r'[^\w\s\-.,!?():;\'\"@#$%&*+=<>/\\|`~]', '', reason)
    
    # Truncate if too long
    if len(reason) > max_length:
        reason = reason[:max_length - 3] + "..."
    
    # Ensure minimum length
    if len(reason.strip()) == 0:
        return "No reason provided"
    
    return reason

def format_time_duration(minutes: int, detailed: bool = False) -> str:
    """
    Enhanced time duration formatting with multiple display options.
    
    Args:
        minutes: Duration in minutes
        detailed: Whether to include detailed breakdown
        
    Returns:
        str: Formatted duration string
        
    Examples:
        30 -> "30 minutes"
        60 -> "1 hour" 
        90 -> "1 hour and 30 minutes"
        1440 -> "1 day"
        10080 -> "1 week"
    """
    if minutes <= 0:
        return "0 minutes"
    
    # Convert to different units
    weeks, remainder = divmod(minutes, 10080)  # 10080 = minutes in a week
    days, remainder = divmod(remainder, 1440)   # 1440 = minutes in a day
    hours, mins = divmod(remainder, 60)
    
    parts = []
    
    if weeks > 0:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if mins > 0:
        parts.append(f"{mins} minute{'s' if mins != 1 else ''}")
    
    if not parts:
        return "0 minutes"
    
    # Return different formats based on detail level
    if detailed or len(parts) <= 2:
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        else:
            return f"{', '.join(parts[:-1])}, and {parts[-1]}"
    else:
        # Simplified format for long durations
        return parts[0]

def format_relative_time(timestamp, now=None) -> str:
    """
    Format a timestamp as relative time (e.g., '2 hours ago').
    
    Args:
        timestamp: datetime object or timestamp
        now: Current time (defaults to datetime.now())
        
    Returns:
        str: Relative time string
    """
    from datetime import datetime, timezone
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Handle different timestamp formats
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    elif not hasattr(timestamp, 'timestamp'):
        return "Unknown time"
    
    delta = now - timestamp
    
    if delta.days > 0:
        if delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    minutes = delta.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    return "just now"

def validate_duration(duration_str: str) -> Tuple[bool, Union[int, str]]:
    """
    Validate and parse duration strings.
    
    Args:
        duration_str: Duration string to validate
        
    Returns:
        Tuple[bool, Union[int, str]]: (is_valid, parsed_seconds_or_error_message)
    """
    try:
        # Try parsing as plain number (minutes)
        if duration_str.isdigit():
            minutes = int(duration_str)
            if minutes < 1:
                return False, "Duration must be at least 1 minute"
            if minutes > 10080:  # 1 week
                return False, "Duration cannot exceed 1 week (10080 minutes)"
            return True, minutes * 60
        
        # Parse complex duration strings
        pattern = re.compile(
            r'^(?:(?P<weeks>\d+)w)?(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?$'
        )
        match = pattern.match(duration_str.lower())
        
        if not match:
            return False, "Invalid duration format. Use formats like: 30, 1h30m, 2d, 1w"
        
        weeks = int(match.group('weeks') or 0)
        days = int(match.group('days') or 0)
        hours = int(match.group('hours') or 0)
        minutes = int(match.group('minutes') or 0)
        
        if weeks == 0 and days == 0 and hours == 0 and minutes == 0:
            return False, "Duration must be at least 1 minute"
        
        # Convert to total seconds
        total_seconds = (
            weeks * 7 * 24 * 60 * 60 +
            days * 24 * 60 * 60 + 
            hours * 60 * 60 + 
            minutes * 60
        )
        
        # Check Discord limits (max 1 week)
        max_seconds = 7 * 24 * 60 * 60
        if total_seconds > max_seconds:
            return False, f"Duration exceeds Discord's maximum of 1 week"
        
        return True, total_seconds
        
    except (ValueError, AttributeError) as e:
        return False, f"Invalid duration format: {str(e)}"

def create_progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """
    Create a text-based progress bar.
    
    Args:
        current: Current value
        maximum: Maximum value
        length: Length of the progress bar
        
    Returns:
        str: Progress bar string
    """
    if maximum <= 0:
        return "▱" * length
    
    filled = min(length, int(length * current / maximum))
    empty = length - filled
    
    return "▰" * filled + "▱" * empty

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Intelligently truncate text at word boundaries when possible.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    max_content_length = max_length - len(suffix)
    
    if max_content_length <= 0:
        return suffix[:max_length]
    
    # Find last space before the limit
    truncate_at = text.rfind(' ', 0, max_content_length)
    
    if truncate_at == -1 or truncate_at < max_content_length * 0.7:
        # No good word boundary found, hard truncate
        return text[:max_content_length] + suffix
    else:
        # Truncate at word boundary
        return text[:truncate_at] + suffix

def format_user_mention(user: Union[discord.Member, discord.User], include_id: bool = False) -> str:
    """
    Format a user mention with optional ID.
    
    Args:
        user: User to format
        include_id: Whether to include user ID
        
    Returns:
        str: Formatted user string
    """
    if include_id:
        return f"{user.mention} ({user.id})"
    return user.mention

def log_mod_action(action: str, moderator: discord.Member, target: discord.Member, 
                  reason: str, **kwargs) -> None:
    """
    Log moderation actions with consistent formatting.
    
    Args:
        action: Type of moderation action
        moderator: Member who performed the action
        target: Member who was targeted
        reason: Reason for the action
        **kwargs: Additional data to log
    """
    extra_info = " | ".join([f"{k}: {v}" for k, v in kwargs.items()])
    log_message = f"[{action.upper()}] {moderator} ({moderator.id}) -> {target} ({target.id}) | Reason: {reason}"
    
    if extra_info:
        log_message += f" | {extra_info}"
    
    logger.info(log_message)
