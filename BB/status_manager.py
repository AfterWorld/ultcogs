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
        
        if effect_name in ["burn", "poison"]:
            # Stackable effects
            target["status"][effect_name] = target["status"].get(effect_name, 0) + value
        elif effect_name in ["stun", "freeze", "slow", "bind"]:
            # Duration-based effects
            target["status"][effect_name] = duration
        elif effect_name in ["protect", "dodge", "speed_boost", "attack_boost", "defense_boost"]:
            # Beneficial effects
            target["status"][effect_name] = duration
        else:
            # Other effects
            target["status"][effect_name] = max(target["status"].get(effect_name, 0), duration)
        
        self.log.info(f"Applied {effect_name} to {target.get('name', 'unknown')} - Duration/Value: {duration}/{value}")
    
    async def process_status_effects(self, participant: Dict[str, Any]) -> Dict[str, Any]:
        """Process all status effects on a participant."""
        if "status" not in participant:
            participant["status"] = {}
        
        effects_processed = {}
        effects_to_remove = []
        
        for effect, value in participant["status"].items():
            if effect in ["burn", "poison"]:
                # Damage over time effects
                if value > 0:
                    damage = value * 5  # 5 damage per stack
                    participant["hp"] = max(0, participant["hp"] - damage)
                    effects_processed[effect] = f"Took {damage} {effect} damage"
                    participant["status"][effect] = max(0, value - 1)
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["stun", "freeze"]:
                # Movement preventing effects
                if value > 0:
                    effects_processed[effect] = f"Stunned/Frozen for {value} more turns"
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["slow", "bind"]:
                # Movement impairing effects
                if value > 0:
                    effects_processed[effect] = f"Movement impaired for {value} more turns"
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
            
            elif effect in ["protect", "dodge", "speed_boost", "attack_boost", "defense_boost"]:
                # Beneficial effects
                if value > 0:
                    effects_processed[effect] = f"{effect.title()} active for {value} more turns"
                    participant["status"][effect] = value - 1
                    if participant["status"][effect] == 0:
                        effects_to_remove.append(effect)
        
        # Remove expired effects
        for effect in effects_to_remove:
            del participant["status"][effect]
        
        return effects_processed
    
    def is_stunned(self, participant: Dict[str, Any]) -> bool:
        """Check if participant is stunned."""
        return participant.get("status", {}).get("stun", 0) > 0 or participant.get("status", {}).get("freeze", 0) > 0
    
    def get_dodge_chance(self, participant: Dict[str, Any]) -> float:
        """Get dodge chance based on status effects."""
        base_dodge = 0.0
        
        if participant.get("status", {}).get("dodge", 0) > 0:
            base_dodge += 0.5  # 50% dodge chance
        
        if participant.get("status", {}).get("speed_boost", 0) > 0:
            base_dodge += 0.2  # 20% additional dodge
        
        return min(base_dodge, 0.8)  # Cap at 80%
    
    def get_damage_modifier(self, participant: Dict[str, Any], is_attack: bool = True) -> float:
        """Get damage modifier based on status effects."""
        modifier = 1.0
        
        if is_attack:
            if participant.get("status", {}).get("attack_boost", 0) > 0:
                modifier += 0.3  # 30% attack boost
            if participant.get("status", {}).get("attack_down", 0) > 0:
                modifier -= 0.3  # 30% attack reduction
        else:
            if participant.get("status", {}).get("defense_boost", 0) > 0:
                modifier -= 0.2  # 20% damage reduction
            if participant.get("status", {}).get("defense_down", 0) > 0:
                modifier += 0.2  # 20% more damage taken
        
        return max(modifier, 0.1)  # Minimum 10% of original