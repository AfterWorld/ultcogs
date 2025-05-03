import random
from typing import Dict, Any, List, Tuple, Optional

class EnvironmentManager:
    """Manages environment effects in battles."""
    
    def __init__(self):
        from .constants.environments import ENVIRONMENTS
        self.ENVIRONMENTS = ENVIRONMENTS
        
        self.EFFECT_COOLDOWNS = {
            "Skypiea": 3,      # Lightning effects every 3 turns
            "Alabasta": 2,     # Sandstorm effects every 2 turns
            "Punk Hazard": 4,  # Extreme climate every 4 turns
            "Raftel": 5,      # Ancient weapon effects every 5 turns
        }
        
        self.current_cooldowns = {}
        self.active_effects = {}
        
    def choose_environment(self) -> str:
        """Randomly select an environment from One Piece islands."""
        return random.choice(list(self.ENVIRONMENTS.keys()))
    
    def get_environment_data(self, environment: str) -> Dict[str, Any]:
        """Get data for a specific environment."""
        return self.ENVIRONMENTS.get(environment, {})
        
    async def apply_environment_effect(self, environment: str, players: list, turn: int) -> tuple[list[str], dict]:
        """Apply environment effects with proper cooldown management."""
        messages = []
        effect_data = {}
        
        # Check cooldown
        if self.current_cooldowns.get(environment, 0) > 0:
            self.current_cooldowns[environment] -= 1
            return messages, effect_data
            
        # Reset cooldown
        self.current_cooldowns[environment] = self.EFFECT_COOLDOWNS.get(environment, 2)
        
        if environment == "Skypiea":
            if random.random() < 0.3:  # 30% chance
                damage = random.randint(10, 15)
                effect_data = {
                    "type": "lightning",
                    "damage": damage,
                    "duration": 1
                }
                messages.append(f"⚡ Divine lightning strikes for {damage} damage!")
                
        elif environment == "Alabasta":
            if random.random() < 0.3:
                effect_data = {
                    "type": "sandstorm",
                    "accuracy_reduction": 0.2,
                    "duration": 2
                }
                messages.append("🌪️ Sandstorm reduces accuracy by 20% for 2 turns!")
                
        elif environment == "Punk Hazard":
            if random.random() < 0.3:
                damage = random.randint(5, 10)
                effect_data = {
                    "type": "extreme_climate",
                    "damage": damage,
                    "burn_amplification": 1.5,
                    "duration": 2
                }
                messages.append(f"🔥❄️ Extreme climate deals {damage} damage and amplifies burns!")
                
        elif environment == "Raftel":
            if random.random() < 0.2:  # Rare but powerful
                effect_data = {
                    "type": "ancient_weapon",
                    "damage_boost": 1.3,
                    "healing_boost": 1.3,
                    "duration": 1
                }
                messages.append("🏺 Ancient weapon power enhances all abilities!")
                
        return messages, effect_data
        
    async def calculate_environment_modifiers(self, environment: str, move_data: dict) -> tuple[dict, list[str]]:
        """Calculate move modifications based on environment."""
        messages = []
        modified_move = move_data.copy()
        
        # Get active effects
        active_effect = self.active_effects.get(environment, {})
        
        if environment == "Skypiea" and "lightning" in move_data.get("effect", ""):
            modified_move["damage"] = int(modified_move.get("damage", 0) * 1.2)
            messages.append("⚡ Lightning enhanced by Skypiea's atmosphere!")
            
        elif environment == "Alabasta" and "burn" in move_data.get("effect", ""):
            modified_move["burn_chance"] = modified_move.get("burn_chance", 0) + 0.1
            messages.append("🔥 Burn chance increased in the desert heat!")
            
        elif environment == "Punk Hazard":
            if active_effect.get("type") == "extreme_climate":
                if "burn" in move_data.get("effect", ""):
                    modified_move["burn_chance"] = modified_move.get("burn_chance", 0) * 1.5
                    messages.append("🌋 Burn effects amplified by extreme climate!")
                    
        elif environment == "Raftel":
            if active_effect.get("type") == "ancient_weapon":
                modified_move["damage"] = int(modified_move.get("damage", 0) * 1.3)
                if "heal" in move_data.get("effect", ""):
                    modified_move["heal_amount"] = int(modified_move.get("heal_amount", 0) * 1.3)
                messages.append("🏺 Move enhanced by ancient weapon power!")
                
        return modified_move, messages
        
    def clear_environment_effects(self):
        """Clear all active environment effects."""
        self.active_effects = {}
        self.current_cooldowns = {}