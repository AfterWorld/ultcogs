"""
Devil Fruit effects manager for the DeathBattle system.
"""
import random
from typing import Dict, Any, Tuple, Optional

try:
    from .gamedata import DEVIL_FRUITS, MOVE_TYPES
    from .status_manager import StatusEffectManager
    from .utils import setup_logger
except ImportError:
    from gamedata import DEVIL_FRUITS, MOVE_TYPES
    from status_manager import StatusEffectManager
    from utils import setup_logger

class DevilFruitManager:
    """Manages Devil Fruit effects and their interactions with status effects."""
    
    def __init__(self, status_manager: StatusEffectManager):
        self.status_manager = status_manager
        self.log = setup_logger("devil_fruit_manager")
        self.active_transformations = {}
        
        # Effect cooldowns for Devil Fruits
        self.fruit_cooldowns = {
            "Mera Mera no Mi": 3,      # Fire abilities
            "Goro Goro no Mi": 4,      # Lightning abilities
            "Hie Hie no Mi": 3,        # Ice abilities
            "Ope Ope no Mi": 4,        # Room abilities
            "Pika Pika no Mi": 3,      # Light abilities
            "Magu Magu no Mi": 4,      # Magma abilities
            "Gura Gura no Mi": 5,      # Quake abilities
        }
    
    async def process_devil_fruit_effect(self, attacker: Dict[str, Any], defender: Dict[str, Any], 
                                       move: Dict[str, Any], environment: str) -> Tuple[int, Optional[str]]:
        """Process Devil Fruit effects with proper interaction handling."""
        if not attacker.get("fruit"):
            return 0, None
            
        fruit_name = attacker["fruit"]
        bonus_damage = 0
        effect_message = None
        
        # Get fruit data from either Common or Rare categories
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        if not fruit_data:
            return 0, None

        fruit_type = fruit_data["type"]
        effect = fruit_data["effect"]

        # Track fruit usage for achievements
        if "elements_used" not in attacker:
            attacker["elements_used"] = set()
        attacker["elements_used"].add(fruit_type)

        # Process based on fruit type
        if fruit_type == "Logia":
            bonus_damage, effect_message = await self._handle_logia_effects(
                attacker, defender, effect, move, environment
            )
        elif "Zoan" in fruit_type:
            bonus_damage, effect_message = await self._handle_zoan_effects(
                attacker, defender, effect, move, environment
            )
        elif fruit_type in ["Paramecia", "Special Paramecia"]:
            bonus_damage, effect_message = await self._handle_paramecia_effects(
                attacker, defender, effect, move, environment
            )

        return bonus_damage, effect_message

    async def _handle_logia_effects(self, attacker: Dict[str, Any], defender: Dict[str, Any], 
                                  effect: str, move: Dict[str, Any], environment: str) -> Tuple[int, Optional[str]]:
        """Handle Logia-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None
        
        # Get base damage from move
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Mera Mera no Mi (Fire)
        if effect == "fire":
            if random.random() < 0.45:  # 45% proc rate
                await self.status_manager.apply_effect("burn", defender, value=2)
                bonus_damage = int(base_damage * 0.75)
                effect_message = (
                    f"🔥 **FLAME EMPEROR**! 🔥\n"
                    f"**{attacker['name']}** unleashes flames!\n"
                    f"💥 {bonus_damage} fire damage + Burn (2 stacks)"
                )

        # Hie Hie no Mi (Ice)
        elif effect == "ice":
            if random.random() < 0.40:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"❄️ **ICE AGE**! ❄️\n"
                    f"**{attacker['name']}** freezes the battlefield!\n"
                    f"🥶 2-turn freeze + {bonus_damage} bonus damage!"
                )

        # Yami Yami no Mi (Darkness)
        elif effect == "darkness":
            if random.random() < 0.50:
                absorb_amount = int(base_damage * 1.5)  
                attacker["hp"] = min(250, attacker["hp"] + absorb_amount)
                bonus_damage = int(base_damage * 1.0)
                effect_message = (
                    f"🌑 **BLACK HOLE**! 🌑\n"
                    f"**{attacker['name']}** commands darkness!\n"
                    f"⚫ Absorbed {absorb_amount} HP + {bonus_damage} bonus damage!"
                )

        # Pika Pika no Mi (Light)
        elif effect == "light":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"✨ **SACRED YASAKANI**! ✨\n"
                    f"**{attacker['name']}** attacks at light speed!\n"
                    f"⚡ {bonus_damage} piercing damage!"
                )

        # Goro Goro no Mi (Lightning)
        elif effect == "lightning":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(base_damage * 1.0)
                effect_message = (
                    f"⚡ **THUNDER GOD**! ⚡\n"
                    f"**{attacker['name']}** channels lightning!\n"
                    f"💫 2-turn stun + {bonus_damage} bonus damage!"
                )

        # Environment interactions
        if environment == "Punk Hazard" and effect in ["fire", "ice"]:
            bonus_damage = int(bonus_damage * 1.5)
            if effect_message:
                effect_message = f"{effect_message}\n🌋 Power amplified by Punk Hazard's climate!"
        elif environment == "Alabasta" and effect == "fire":
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n🏜️ Desert environment enhances fire powers!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)
            effect_message = (
                f"💫 **LOGIA AWAKENING**! 💫\n"
                f"**{attacker['name']}**'s elemental power provides {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_zoan_effects(self, attacker: Dict[str, Any], defender: Dict[str, Any], 
                                 effect: str, move: Dict[str, Any], environment: str) -> Tuple[int, Optional[str]]:
        """Handle Zoan-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Model Leopard
        if effect == "leopard":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 0.9)
                hits = random.randint(2, 3)
                bonus_damage *= hits
                effect_message = (
                    f"🐆 **PREDATOR'S AGILITY**! 🐆\n"
                    f"**{attacker['name']}** strikes with feline grace!\n"
                    f"⚡ {hits} rapid strikes for {bonus_damage} total damage!"
                )

        # Model Phoenix
        elif "phoenix" in effect:
            if random.random() < 0.45:
                heal_amount = int(attacker["max_hp"] * 0.15)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🦅 **FLAMES OF RESTORATION**! 🦅\n"
                    f"**{attacker['name']}** bathes in regenerative flames!\n"
                    f"💚 Healed {heal_amount} HP + {bonus_damage} flame damage!"
                )

        # Model Nika (Special case)
        elif effect == "sun god":
            if random.random() < 0.50:
                effect_choice = random.choice(["drumbeat", "giant", "freedom"])
                
                if effect_choice == "drumbeat":
                    bonus_damage = int(base_damage * 2.0)
                    await self.status_manager.apply_effect("attack_boost", attacker, duration=2)
                    effect_message = (
                        f"💥 **DRUMS OF LIBERATION**! 💥\n"
                        f"**{attacker['name']}** awakens the rhythm of freedom!\n"
                        f"🥁 {bonus_damage} liberation damage + Attack boost!"
                    )
                elif effect_choice == "giant":
                    bonus_damage = int(base_damage * 1.8)
                    await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                    effect_message = (
                        f"🌟 **GIANT WARRIOR**! 🌟\n"
                        f"**{attacker['name']}** becomes a giant!\n"
                        f"👊 {bonus_damage} massive damage + Defense boost!"
                    )

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)
            effect_message = (
                f"✨ **ZOAN TRANSFORMATION**! ✨\n"
                f"**{attacker['name']}**'s beast form grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_paramecia_effects(self, attacker: Dict[str, Any], defender: Dict[str, Any], 
                                      effect: str, move: Dict[str, Any], environment: str) -> Tuple[int, Optional[str]]:
        """Handle Paramecia-type Devil Fruit effects."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in MOVE_TYPES:
            move_type = MOVE_TYPES[move["type"]]
            min_damage, max_damage = move_type["base_damage_range"]
            base_damage = (min_damage + max_damage) // 2

        # Gomu Gomu no Mi
        if effect == "rubber" and move.get("type") == "strong":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"✨ **RUBBER POWER**! ✨\n"
                    f"**{attacker['name']}** stretches for maximum power!\n"
                    f"💥 {bonus_damage} elastic bonus damage!"
                )

        # Gura Gura no Mi
        elif effect == "quake":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("stun", defender, duration=1)
                effect_message = (
                    f"💥 **SEISMIC SHOCK**! 💥\n"
                    f"**{attacker['name']}** shatters the air itself!\n"
                    f"🌋 {bonus_damage} quake damage + 1-turn stun!"
                )

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)
            effect_message = (
                f"✨ **PARAMECIA POWER**! ✨\n"
                f"**{attacker['name']}**'s devil fruit grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message