import discord
from discord.ext import commands
from typing import Optional

async def check_hierarchy(ctx: commands.Context, member: discord.Member, error_message: Optional[str] = None) -> bool:
    """
    Checks if the bot and command author can perform an action on the specified member.
    
    Returns True if the hierarchy check passes, False otherwise.
    """
    # Check if author is trying to moderate a mod/admin
    if member.guild_permissions.manage_messages or member.guild_permissions.administrator:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ You cannot moderate another moderator or administrator!")
            return False
            
    # Check if author has sufficient permissions
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot moderate a member with a higher or equal role!")
        return False
        
    # Check if bot has sufficient permissions
    if member.top_role >= ctx.guild.me.top_role:
        if error_message:
            await ctx.send(error_message)
        else:
            await ctx.send("❌ I cannot moderate a member with a higher role than me!")
        return False
        
    return True

def sanitize_reason(reason: Optional[str]) -> str:
    """
    Sanitizes and formats reason strings.
    
    Returns a default reason if none provided.
    """
    if not reason:
        return "No reason provided"
        
    # Strip whitespace and ensure reasonable length
    reason = reason.strip()
    
    # Truncate if too long
    if len(reason) > 512:
        reason = reason[:509] + "..."
        
    return reason

def format_time_duration(minutes: int) -> str:
    """
    Formats a duration in minutes into a human-readable string.
    
    Examples:
    30 -> "30 minutes"
    60 -> "1 hour"
    90 -> "1 hour and 30 minutes"
    1440 -> "1 day"
    """
    if minutes <= 0:
        return "0 minutes"
        
    days, remainder = divmod(minutes, 1440)  # 1440 = minutes in a day
    hours, minutes = divmod(remainder, 60)
    
    parts = []
    
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
    if not parts:
        return "0 minutes"
        
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    else:
        return f"{parts[0]}, {parts[1]}, and {parts[2]}"
