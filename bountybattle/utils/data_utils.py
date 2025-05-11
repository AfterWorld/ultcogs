import random
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
import discord
from redbot.core import Config

class DataUtils:
    """Utilities for data manipulation and calculation."""
    
    def __init__(self, config: Config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # Import constants
        from ..constants.moves import MOVE_TYPES
        from ..constants.achievements import ACHIEVEMENTS
        from ..constants.titles import TITLES
        
        self.MOVE_TYPES = MOVE_TYPES
        self.ACHIEVEMENTS = ACHIEVEMENTS
        self.TITLES = TITLES
        
    def update_cooldowns(self, player_data: dict):
        """
        Update cooldowns at the start of a player's turn.
        
        Parameters:
        -----------
        player_data : dict
            The player's data dictionary containing their moves_on_cooldown
        """
        # Create a copy of the keys to avoid modifying dict during iteration
        if "moves_on_cooldown" not in player_data:
            player_data["moves_on_cooldown"] = {}
            return
            
        moves = list(player_data["moves_on_cooldown"].keys())
        
        for move in moves:
            player_data["moves_on_cooldown"][move] -= 1
            if player_data["moves_on_cooldown"][move] <= 0:
                del player_data["moves_on_cooldown"][move]

    def is_move_available(self, move_name: str, player_data: dict) -> bool:
        """Check if a move is available to use."""
        if "moves_on_cooldown" not in player_data:
            player_data["moves_on_cooldown"] = {}
        return move_name not in player_data["moves_on_cooldown"]

    def set_move_cooldown(self, move_name: str, cooldown: int, player_data: dict):
        """
        Set a cooldown for a move on a player.
        
        Parameters:
        -----------
        move_name : str
            The name of the move to put on cooldown
        cooldown : int
            Number of turns the move should be on cooldown
        player_data : dict
            The player's data dictionary containing their moves_on_cooldown
        """
        if "moves_on_cooldown" not in player_data:
            player_data["moves_on_cooldown"] = {}
            
        player_data["moves_on_cooldown"][move_name] = cooldown
        
        if "stats" in player_data:
            if "cooldowns_managed" not in player_data["stats"]:
                player_data["stats"]["cooldowns_managed"] = 0
            player_data["stats"]["cooldowns_managed"] += 1

    def calculate_damage(self, move: dict, attacker_data: dict, turn_number: int) -> Tuple[int, Optional[str]]:
        """Calculate damage considering cooldowns and effects."""
        # Check if move is on cooldown
        if move["name"] in attacker_data.get("moves_on_cooldown", {}):
            if attacker_data["moves_on_cooldown"][move["name"]] > 0:
                return 0, "Move is on cooldown!"
    
        # Handle move_type properly - ensure we're getting correct type info
        move_type_name = move.get("type", "regular")
        if move_type_name not in self.MOVE_TYPES:
            move_type_name = "regular"  # Fallback to regular if type not found
            
        move_type = self.MOVE_TYPES[move_type_name]
        
        # Ensure base_damage_range is a tuple of two integers
        if isinstance(move_type["base_damage_range"], tuple) and len(move_type["base_damage_range"]) == 2:
            base_min, base_max = move_type["base_damage_range"]
            base_damage = random.randint(base_min, base_max)
        else:
            # Fallback values if the range is not properly defined
            base_damage = random.randint(5, 15)
    
        # Critical hit calculation
        crit_chance = move.get("crit_chance", move_type.get("crit_chance", 0.15))
        crit_message = None
        
        if random.random() < crit_chance:
            base_damage = int(base_damage * 1.5)
            crit_message = "Critical hit!"
            
            # Update stats if available
            if "stats" in attacker_data:
                if "critical_hits" not in attacker_data["stats"]:
                    attacker_data["stats"]["critical_hits"] = 0
                attacker_data["stats"]["critical_hits"] += 1
    
        # Apply scaling with turn number for longer battles (cap at reasonable value)
        max_turn_bonus = 2.0  # Maximum scaling factor
        turn_scaling = min(1 + (turn_number * 0.05), max_turn_bonus)  # 5% increase per turn, capped
        final_damage = int(base_damage * turn_scaling)
    
        # Set cooldown if the move has one
        cooldown = move.get("cooldown", 0)
        if cooldown > 0:
            self.set_move_cooldown(move["name"], cooldown, attacker_data)
            
        # Update damage stats
        if "stats" in attacker_data:
            if "damage" not in attacker_data["stats"]:
                attacker_data["stats"]["damage"] = 0
            attacker_data["stats"]["damage"] += final_damage
    
        return final_damage, crit_message
    
    def get_bounty_title(self, bounty_amount: int) -> str:
        """Get the bounty title based on the bounty amount.
        Returns the highest title the user has qualified for."""
        if bounty_amount is None or bounty_amount <= 0:
            return "Unknown Pirate"
            
        # Define titles and their required bounties
        titles_qualified = []
        
        for title, requirements in self.TITLES.items():
            required_bounty = requirements["bounty"]
            if bounty_amount >= required_bounty:
                titles_qualified.append((title, required_bounty))
        
        # If no titles are qualified
        if not titles_qualified:
            return "Unknown Pirate"
            
        # Sort by required bounty (descending) and return the highest one
        titles_qualified.sort(key=lambda x: x[1], reverse=True)
        return titles_qualified[0][0]
    
    async def check_achievements(self, member: discord.Member) -> List[str]:
        """Check and unlock achievements for the member."""
        stats = await self.config.member(member).all()  # Get stats inside the function
        user_achievements = stats.get("achievements", [])
        unlocked_titles = stats.get("titles", [])
        unlocked = []
    
        for key, data in self.ACHIEVEMENTS.items():
            if key in user_achievements:
                continue  # Already unlocked
    
            current_stat = stats.get(data["condition"], 0)
            required_count = data["count"]
    
            if isinstance(required_count, str) and required_count == "all":
                required_count = float('inf')  # "all" means infinite
    
            if current_stat >= required_count:
                user_achievements.append(key)
                unlocked.append(data["description"])
    
                if "title" in data and data["title"] not in unlocked_titles:
                    unlocked_titles.append(data["title"])
                    try:
                        await member.send(f"🎉 Congratulations! You've unlocked the title: **{data['title']}**")
                    except discord.Forbidden:
                        self.logger.warning(f"Could not send DM to {member.display_name}. They might have DMs disabled.")
    
        await self.config.member(member).achievements.set(user_achievements)
        await self.config.member(member).titles.set(unlocked_titles)
    
        return unlocked
