"""
Status effects manager for the DeathBattle system.
"""
import asyncio
import random
from typing import Dict, Any

try:
    from .utils import setup_logger
except ImportError:
    from utils import setup_logger

class StatusEffectManager:
    """Manages status effects for battle participants."""
    
    def __init__(self):
        self.log = setup_logger("status_manager")
        
    async def apply_effect(self, effect_name: str, target: Dict[str, Any], duration: int = 1, value: int = 0):
        """Apply a status effect to a target."""
        if "status" not in target:
            target["status"] = {}
        
        if effect_name in ["burn", "poison", "bleed"]:
            # Stackable damage over time effects
            target["status"][effect_name] = target["status"].get(effect_name, 0) + value
        elif effect_name in ["stun", "freeze", "slow", "bind", "confusion", "fear"]:
            # Duration-based negative effects
            target["status"][effect_name] = max(target["status"].get(effect_name, 0), duration)
        elif effect_name in ["dodge", "speed_boost", "attack_boost", "defense_boost", "protect"]:
            # Duration-based beneficial effects
            target["status"][effect_name] = max(target["status"].get(effect_name, 0), duration)
        else:
            # Other effects (default to duration-based)
            target["status"][effect_name] = max(target["status"].get(effect_name, 0), duration)
        
        self.log.info(f"Applied {effect_name} to {target.get('name', 'unknown')} - Duration/Value: {duration}/{value}")
    
    async def process_status_effects(self, participant: Dict[str, Any]) -> Dict[str, Any]:
        """Process all status effects on a participant."""
        if "status" not in participant:
            participant["status"] = {}
        
        effects_processed = {}
        effects_to_remove = []
        
        for effect, value in participant["status"].items():
            if effect in ["burn", "poison", "bleed"]:
                # Damage over time effects
                if value > 0:
                    if effect == "burn":
                        damage = value * 5  # 5 damage per burn stack
                    elif effect == "poison":
                        damage = value * 3  # 3 damage per poison stack
                    elif effect == "bleed":
                        damage = value * 4  # 4 damage per bleed stack
                    else:
                        damage = value * 5  # Default
                    
                    participant["hp"] = max(0, participant["hp"] - damage)
                    effects_processed[effect] = f"Took {damage} {effect} damage"
                    
                    # Reduce stacks over time
                    participant["status"][effect] = max(0, value - 1)
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["stun", "freeze", "confusion", "fear"]:
                # Movement/action preventing effects
                if value > 0:
                    if effect == "stun" or effect == "freeze":
                        effects_processed[effect] = f"Cannot act ({effect}) for {value} more turns"
                    else:
                        effects_processed[effect] = f"Affected by {effect} for {value} more turns"
                    
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["slow", "bind"]:
                # Movement impairing effects
                if value > 0:
                    effects_processed[effect] = f"Movement impaired ({effect}) for {value} more turns"
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["dodge", "speed_boost", "attack_boost", "defense_boost", "protect"]:
                # Beneficial effects
                if value > 0:
                    effects_processed[effect] = f"{effect.replace('_', ' ').title()} active for {value} more turns"
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
        
        # Remove expired effects
        for effect in effects_to_remove:
            del participant["status"][effect]
        
        return effects_processed
    
    def is_stunned(self, participant: Dict[str, Any]) -> bool:
        """Check if participant is stunned or cannot act."""
        status = participant.get("status", {})
        return (status.get("stun", 0) > 0 or 
                status.get("freeze", 0) > 0)
    
    def get_dodge_chance(self, participant: Dict[str, Any]) -> float:
        """Get dodge chance based on status effects."""
        base_dodge = 0.0
        status = participant.get("status", {})
        
        # Positive dodge effects
        if status.get("dodge", 0) > 0:
            base_dodge += 0.5  # 50% dodge chance
        
        if status.get("speed_boost", 0) > 0:
            base_dodge += 0.2  # 20% additional dodge
        
        # Negative effects that reduce dodge
        if status.get("slow", 0) > 0:
            base_dodge -= 0.2  # 20% dodge penalty
        
        if status.get("bind", 0) > 0:
            base_dodge -= 0.3  # 30% dodge penalty
        
        if status.get("freeze", 0) > 0:
            base_dodge -= 0.5  # 50% dodge penalty
        
        if status.get("confusion", 0) > 0:
            base_dodge -= 0.15  # 15% dodge penalty
        
        return max(0.0, min(base_dodge, 0.8))  # Cap between 0% and 80%
    
    def get_damage_modifier(self, participant: Dict[str, Any], is_attack: bool = True) -> float:
        """Get damage modifier based on status effects."""
        modifier = 1.0
        status = participant.get("status", {})
        
        if is_attack:
            # Attack modifiers
            if status.get("attack_boost", 0) > 0:
                modifier += 0.3  # 30% attack boost
            if status.get("fear", 0) > 0:
                modifier -= 0.2  # 20% attack reduction from fear
            if status.get("confusion", 0) > 0:
                modifier -= 0.15  # 15% attack reduction from confusion
        else:
            # Defense modifiers
            if status.get("defense_boost", 0) > 0:
                modifier -= 0.25  # 25% damage reduction
            if status.get("protect", 0) > 0:
                modifier -= 0.15  # 15% damage reduction
        
        return max(modifier, 0.1)  # Minimum 10% of original damage
    
    def has_status_effect(self, participant: Dict[str, Any], effect_name: str) -> bool:
        """Check if participant has a specific status effect."""
        return participant.get("status", {}).get(effect_name, 0) > 0
    
    def get_status_effect_value(self, participant: Dict[str, Any], effect_name: str) -> int:
        """Get the value/duration of a specific status effect."""
        return participant.get("status", {}).get(effect_name, 0)
    
    def remove_status_effect(self, participant: Dict[str, Any], effect_name: str):
        """Remove a specific status effect from a participant."""
        if "status" in participant and effect_name in participant["status"]:
            del participant["status"][effect_name]
            self.log.info(f"Removed {effect_name} from {participant.get('name', 'unknown')}")
    
    def clear_all_status_effects(self, participant: Dict[str, Any]):
        """Clear all status effects from a participant."""
        if "status" in participant:
            participant["status"] = {}
            self.log.info(f"Cleared all status effects from {participant.get('name', 'unknown')}")
    
    def get_status_summary(self, participant: Dict[str, Any]) -> str:
        """Get a summary of all active status effects."""
        status = participant.get("status", {})
        if not status:
            return "No status effects"
        
        effects = []
        for effect, value in status.items():
            if effect in ["burn", "poison", "bleed"]:
                effects.append(f"{effect.title()}: {value} stacks")
            else:
                effects.append(f"{effect.replace('_', ' ').title()}: {value} turns")
        
        return ", ".join(effects)
