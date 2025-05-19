"""Validation utilities for the One Piece bot."""

import re
from typing import Any, Union, List, Dict
from discord.ext import commands
import discord

def validate_berries_amount(amount: int, player_berries: int = None, 
                          min_amount: int = 1, max_amount: int = None) -> tuple:
    """
    Validate berries amount for transactions.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if amount < min_amount:
        return False, f"Amount must be at least {min_amount:,} berries."
    
    if max_amount and amount > max_amount:
        return False, f"Amount cannot exceed {max_amount:,} berries."
    
    if player_berries is not None and amount > player_berries:
        return False, f"You don't have enough berries! You have {player_berries:,} berries."
    
    return True, None

def validate_devil_fruit_name(fruit_name: str, available_fruits: List[str]) -> tuple:
    """
    Validate devil fruit name.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None, closest_match: str or None)
    """
    if not fruit_name:
        return False, "Please provide a fruit name.", None
    
    # Exact match
    if fruit_name.lower() in [f.lower() for f in available_fruits]:
        return True, None, fruit_name
    
    # Partial match
    partial_matches = [f for f in available_fruits if fruit_name.lower() in f.lower()]
    if len(partial_matches) == 1:
        return True, None, partial_matches[0]
    elif len(partial_matches) > 1:
        return False, f"Multiple fruits match '{fruit_name}': {', '.join(partial_matches[:3])}", None
    
    # No match found
    closest = find_closest_match(fruit_name, available_fruits)
    return False, f"Fruit '{fruit_name}' not found.", closest

def validate_battle_challenge(challenger: discord.Member, target: discord.Member,
                            challenger_battles: int = 0, target_battles: int = 0) -> tuple:
    """
    Validate battle challenge conditions.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    # Self-challenge check
    if challenger == target:
        return False, "You cannot challenge yourself to battle!"
    
    # Bot check
    if target.bot:
        return False, "You cannot challenge bots to battle!"
    
    # Already in battle check (would need to be passed from battle manager)
    # This is just a placeholder - actual implementation would check with battle manager
    
    return True, None

def validate_title(title: str, max_length: int = 50) -> tuple:
    """
    Validate custom title.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not title:
        return False, "Title cannot be empty."
    
    if len(title) > max_length:
        return False, f"Title must be {max_length} characters or less."
    
    # Check for inappropriate content (basic check)
    inappropriate_words = ["fuck", "shit", "damn", "hell"]  # Add more as needed
    if any(word in title.lower() for word in inappropriate_words):
        return False, "Title contains inappropriate content."
    
    # Check for Discord markdown abuse
    if title.count('*') > 4 or title.count('_') > 4 or title.count('`') > 2:
        return False, "Title contains too much formatting."
    
    return True, None

def validate_admin_give_amount(item_type: str, amount: int) -> tuple:
    """
    Validate admin give command amounts.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    valid_types = ["berries", "wins", "losses"]
    
    if item_type not in valid_types:
        return False, f"Invalid item type. Valid types: {', '.join(valid_types)}"
    
    if item_type == "berries":
        if amount < -1_000_000_000 or amount > 1_000_000_000:
            return False, "Berries amount must be between -1B and 1B."
    
    elif item_type in ["wins", "losses"]:
        if amount < 0 or amount > 10000:
            return False, f"{item_type.capitalize()} must be between 0 and 10,000."
    
    return True, None

def validate_gamble_amount(amount: int, player_berries: int, 
                         min_bet: int = 100, max_bet: int = 1_000_000) -> tuple:
    """
    Validate gambling amount.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if amount < min_bet:
        return False, f"Minimum bet is {min_bet:,} berries."
    
    if amount > max_bet:
        return False, f"Maximum bet is {max_bet:,} berries."
    
    if amount > player_berries:
        return False, f"You don't have enough berries! You have {player_berries:,} berries."
    
    return True, None

def validate_channel_permissions(channel: discord.TextChannel, required_perms: List[str]) -> tuple:
    """
    Validate bot permissions in a channel.
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None, missing_perms: List[str])
    """
    if not channel:
        return False, "Channel not found.", []
    
    bot_perms = channel.permissions_for(channel.guild.me)
    missing_perms = []
    
    perm_mapping = {
        "send_messages": bot_perms.send_messages,
        "embed_links": bot_perms.embed_links,
        "add_reactions": bot_perms.add_reactions,
        "manage_messages": bot_perms.manage_messages,
        "read_message_history": bot_perms.read_message_history,
        "use_external_emojis": bot_perms.use_external_emojis,
        "read_messages": bot_perms.read_messages
    }
    
    for perm in required_perms:
        if perm in perm_mapping and not perm_mapping[perm]:
            missing_perms.append(perm.replace("_", " ").title())
    
    if missing_perms:
        return False, f"Missing permissions: {', '.join(missing_perms)}", missing_perms
    
    return True, None, []

def validate_cooldown(last_used: float, cooldown_seconds: int) -> tuple:
    """
    Validate command cooldown.
    
    Returns:
        tuple: (is_ready: bool, time_remaining: int)
    """
    import time
    current_time = time.time()
    time_since_use = current_time - last_used
    
    if time_since_use >= cooldown_seconds:
        return True, 0
    
    time_remaining = int(cooldown_seconds - time_since_use)
    return False, time_remaining

def find_closest_match(target: str, options: List[str], max_distance: int = 3) -> str:
    """
    Find the closest string match using Levenshtein distance.
    
    Returns:
        str or None: Closest match if within max_distance, otherwise None
    """
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    target_lower = target.lower()
    best_match = None
    min_distance = float('inf')
    
    for option in options:
        distance = levenshtein_distance(target_lower, option.lower())
        if distance < min_distance:
            min_distance = distance
            best_match = option
    
    return best_match if min_distance <= max_distance else None

def sanitize_input(text: str, max_length: int = 100, 
                  allow_newlines: bool = False) -> str:
    """
    Sanitize user input by removing/escaping dangerous characters.
    
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove/escape Discord markdown
    text = text.replace('`', '\\`')
    text = text.replace('*', '\\*')
    text = text.replace('_', '\\_')
    text = text.replace('~', '\\~')
    text = text.replace('|', '\\|')
    
    # Remove newlines if not allowed
    if not allow_newlines:
        text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text

class ValidationError(commands.BadArgument):
    """Custom validation error for the One Piece bot."""
    
    def __init__(self, message: str, suggestion: str = None):
        super().__init__(message)
        self.suggestion = suggestion

async def validate_and_convert_member(ctx: commands.Context, member_input: str) -> discord.Member:
    """
    Validate and convert member input to Member object.
    
    Raises:
        ValidationError: If member not found or invalid
    """
    try:
        # Try to convert using discord.py's converter
        converter = commands.MemberConverter()
        member = await converter.convert(ctx, member_input)
        return member
    except commands.BadArgument:
       # Try partial name matching
       members = [m for m in ctx.guild.members if member_input.lower() in m.display_name.lower()]
       
       if len(members) == 1:
           return members[0]
       elif len(members) > 1:
           names = [m.display_name for m in members[:5]]
           raise ValidationError(
               f"Multiple members found matching '{member_input}': {', '.join(names)}",
               "Please be more specific with the member name."
           )
       else:
           raise ValidationError(
               f"No member found matching '{member_input}'",
               "Make sure the member is in this server and try using their full name or mention."
           )

def validate_nickname(nickname: str) -> tuple:
   """
   Validate nickname for appropriateness and length.
   
   Returns:
       tuple: (is_valid: bool, error_message: str or None)
   """
   if not nickname:
       return False, "Nickname cannot be empty."
   
   if len(nickname) > 32:
       return False, "Nickname must be 32 characters or less."
   
   # Check for Discord nitro/special characters abuse
   special_chars = ['🏴‍☠️', '⚔️', '💰', '🍎']  # Allowed special chars
   if any(char not in special_chars and ord(char) > 127 for char in nickname):
       return False, "Nickname contains unsupported special characters."
   
   return True, None

def validate_emoji_input(emoji_input: str) -> tuple:
   """
   Validate emoji input for custom reactions.
   
   Returns:
       tuple: (is_valid: bool, error_message: str or None, emoji: str)
   """
   # Check if it's a unicode emoji
   if len(emoji_input) <= 4 and emoji_input.isprintable():
       return True, None, emoji_input
   
   # Check if it's a custom emoji format <:name:id>
   custom_emoji_pattern = r'<a?:\w+:\d+>'
   if re.match(custom_emoji_pattern, emoji_input):
       return True, None, emoji_input
   
   return False, "Invalid emoji format. Use unicode emoji or custom emoji.", None

def validate_time_input(time_input: str) -> tuple:
   """
   Validate and parse time input (e.g., "1h", "30m", "2d").
   
   Returns:
       tuple: (is_valid: bool, error_message: str or None, seconds: int)
   """
   if not time_input:
       return False, "Time input cannot be empty.", 0
   
   # Pattern for time input: number followed by unit
   pattern = r'^(\d+)([smhd])$'
   match = re.match(pattern, time_input.lower())
   
   if not match:
       return False, "Invalid time format. Use format like '1h', '30m', '2d'.", 0
   
   amount, unit = match.groups()
   amount = int(amount)
   
   # Convert to seconds
   multipliers = {
       's': 1,
       'm': 60,
       'h': 3600,
       'd': 86400
   }
   
   seconds = amount * multipliers[unit]
   
   # Reasonable limits
   if seconds < 60:  # Minimum 1 minute
       return False, "Minimum time is 1 minute.", 0
   
   if seconds > 86400 * 7:  # Maximum 1 week
       return False, "Maximum time is 7 days.", 0
   
   return True, None, seconds

def is_valid_hex_color(color_string: str) -> bool:
   """Check if string is a valid hex color."""
   hex_pattern = r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
   return bool(re.match(hex_pattern, color_string))

def validate_search_query(query: str, min_length: int = 2, max_length: int = 50) -> tuple:
   """
   Validate search query.
   
   Returns:
       tuple: (is_valid: bool, error_message: str or None)
   """
   if not query:
       return False, "Search query cannot be empty."
   
   if len(query) < min_length:
       return False, f"Search query must be at least {min_length} characters."
   
   if len(query) > max_length:
       return False, f"Search query must be {max_length} characters or less."
   
   # Remove excessive whitespace
   query = re.sub(r'\s+', ' ', query.strip())
   
   if not query:
       return False, "Search query cannot be only whitespace."
   
   return True, None

class InputValidator:
   """Class for handling multiple validation checks."""
   
   def __init__(self):
       self.errors = []
       self.warnings = []
   
   def add_check(self, condition: bool, error_message: str, is_warning: bool = False):
       """Add a validation check."""
       if not condition:
           if is_warning:
               self.warnings.append(error_message)
           else:
               self.errors.append(error_message)
       return self
   
   def is_valid(self) -> bool:
       """Check if all validations passed."""
       return len(self.errors) == 0
   
   def get_error_message(self) -> str:
       """Get formatted error message."""
       if not self.errors:
           return ""
       return "❌ " + "\n❌ ".join(self.errors)
   
   def get_warning_message(self) -> str:
       """Get formatted warning message."""
       if not self.warnings:
           return ""
       return "⚠️ " + "\n⚠️ ".join(self.warnings)
   
   def reset(self):
       """Reset validator for reuse."""
       self.errors.clear()
       self.warnings.clear()

# Decorators for validation
def require_berries(min_amount: int = 0):
   """Decorator to require minimum berries before command execution."""
   def decorator(func):
       async def wrapper(self, ctx, *args, **kwargs):
           # This would integrate with player manager
           # Implementation depends on how player data is accessed
           return await func(self, ctx, *args, **kwargs)
       return wrapper
   return decorator

def validate_target_member(allow_self: bool = False, allow_bots: bool = False):
   """Decorator to validate target member in commands."""
   def decorator(func):
       async def wrapper(self, ctx, target: discord.Member = None, *args, **kwargs):
           if target is None:
               target = ctx.author
           
           validator = InputValidator()
           validator.add_check(allow_self or target != ctx.author, 
                            "You cannot target yourself for this action.")
           validator.add_check(allow_bots or not target.bot,
                            "You cannot target bots for this action.")
           
           if not validator.is_valid():
               await ctx.send(validator.get_error_message())
               return
           
           return await func(self, ctx, target, *args, **kwargs)
       return wrapper
   return decorator

# Constants for validation
class ValidationConstants:
   """Constants used in validation."""
   
   # Berries limits
   MIN_BERRIES_TRANSFER = 1
   MAX_BERRIES_TRANSFER = 1_000_000_000
   MAX_BERRIES_GAMBLE = 10_000_000
   MIN_BERRIES_GAMBLE = 100
   
   # Text limits
   MAX_TITLE_LENGTH = 50
   MAX_NICKNAME_LENGTH = 32
   MAX_DESCRIPTION_LENGTH = 500
   
   # Time limits
   MIN_COOLDOWN_SECONDS = 60
   MAX_COOLDOWN_SECONDS = 86400 * 7  # 1 week
   
   # Battle limits
   MAX_CONCURRENT_BATTLES = 1
   BATTLE_TIMEOUT_SECONDS = 300  # 5 minutes
   
   # Rate limits
   COMMANDS_PER_MINUTE = 10
   BERRIES_TRANSFERS_PER_HOUR = 5
   BATTLES_PER_DAY = 10