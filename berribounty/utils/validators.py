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

class ValidationError(commands.BadArgument):
    """Custom validation error for the One Piece bot."""
    
    def __init__(self, message: str, suggestion: str = None):
        super().__init__(message)
        self.suggestion = suggestion
