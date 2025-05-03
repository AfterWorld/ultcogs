import random
from typing import Dict, Any, Tuple, List, Optional

class DevilFruitManager:
    """Manages Devil Fruit effects and their interactions with status effects."""
    
    def __init__(self, status_manager, environment_manager):
        self.status_manager = status_manager
        self.environment_manager = environment_manager
        self.active_transformations = {}
        
        # Import constants
        from ..constants.devil_fruits import DEVIL_FRUITS
        self.DEVIL_FRUITS = DEVIL_FRUITS
        
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
    
    async def process_devil_fruit_effect(self, attacker, defender, move, environment):
        """Process Devil Fruit effects with proper interaction handling."""
        if not attacker.get("fruit"):
            return 0, None
            
        fruit_name = attacker["fruit"]
        bonus_damage = 0
        effect_message = None
        
        # Get fruit data from either Common or Rare categories
        fruit_data = self.DEVIL_FRUITS["Common"].get(fruit_name) or self.DEVIL_FRUITS["Rare"].get(fruit_name)
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

    async def _handle_logia_effects(self, attacker, defender, effect, move, environment):
        """Handle Logia-type Devil Fruit effects with enhanced proc rates and balanced damage."""
        bonus_damage = 0
        effect_message = None  # Initialize at start

        # Get base damage from move
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in ["regular", "strong", "critical"]:
            base_damage = 15  # Default average damage

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

        # Magu Magu no Mi (Magma)
        elif effect == "magma":
            if random.random() < 0.55:
                await self.status_manager.apply_effect("burn", defender, value=4, duration=3)
                bonus_damage = int(base_damage * 0.9)
                effect_message = (
                    f"🌋 **GREAT ERUPTION**! 🌋\n"
                    f"**{attacker['name']}** unleashes magma!\n"
                    f"🔥 4-stack burn + {bonus_damage} bonus damage!"
                )

        # Suna Suna no Mi (Sand)
        elif effect == "sand":
            if random.random() < 0.35:
                drain_amount = int(defender["hp"] * 0.25)
                defender["hp"] -= drain_amount
                attacker["hp"] = min(250, attacker["hp"] + drain_amount)
                bonus_damage = int(base_damage * 0.4)
                effect_message = (
                    f"🏜️ **GROUND DEATH**! 🏜️\n"
                    f"**{attacker['name']}** drains life force!\n"
                    f"💀 Drained {drain_amount} HP + {bonus_damage} bonus damage!"
                )

        # Environment interactions with proper scaling
        if environment == "Punk Hazard" and effect in ["fire", "ice", "magma"]:
            bonus_damage = int(bonus_damage * 1.5)
            if effect_message:
                effect_message = f"{effect_message}\n🌋 Power amplified by Punk Hazard's climate!"
        elif environment == "Alabasta" and effect in ["fire", "magma"]:
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n🏜️ Desert environment enhances fire powers!"
        elif environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Sacred battleground amplifies power!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"💫 **LOGIA AWAKENING**! 💫\n"
                f"**{attacker['name']}**'s elemental power provides {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_zoan_effects(self, attacker, defender, effect, move, environment):
        """Handle Zoan-type Devil Fruit effects with proper transformations and hybrid forms."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in ["regular", "strong", "critical"]:
            base_damage = 15  # Default average damage

        # Model Leopard (Neko Neko no Mi: Model Leopard)
        if effect == "leopard":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 0.9)
                hits = random.randint(2, 3)  # Multi-hit attack
                bonus_damage *= hits
                effect_message = (
                    f"🐆 **PREDATOR'S AGILITY**! 🐆\n"
                    f"**{attacker['name']}** strikes with feline grace!\n"
                    f"⚡ {hits} rapid strikes for {bonus_damage} total damage!"
                )

        # Model Phoenix (Tori Tori no Mi: Model Phoenix)
        elif "Phoenix" in effect:
            if random.random() < 0.45:
                heal_amount = int(attacker["hp"] * 0.15)
                attacker["hp"] = min(attacker.get("max_hp", 250), attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🦅 **FLAMES OF RESTORATION**! 🦅\n"
                    f"**{attacker['name']}** bathes in regenerative flames!\n"
                    f"💚 Healed {heal_amount} HP + {bonus_damage} flame damage!"
                )

        # Model Nika (Hito Hito no Mi: Model Nika)
        elif effect == "nika":
            if random.random() < 0.50:  # 50% proc rate for special fruit
                effect_choice = random.choice(["drumbeat", "giant", "freedom"])
                
                if effect_choice == "drumbeat":
                    # Massive damage boost for Drums of Liberation
                    bonus_damage = int(base_damage * 2.0)  # 200% damage boost
                    await self.status_manager.apply_effect("attack_boost", attacker, duration=2)
                    effect_message = (
                        f"💥 **DRUMS OF LIBERATION**! 💥\n"
                        f"**{attacker['name']}** awakens the rhythm of freedom!\n"
                        f"🥁 {bonus_damage} liberation damage + Attack boost for 2 turns!"
                    )
                    
                elif effect_choice == "giant":
                    # Giant form now properly boosts damage and adds defense
                    bonus_damage = int(base_damage * 1.8)  # 180% damage boost
                    await self.status_manager.apply_effect("transform", attacker, duration=3)
                    await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                    effect_message = (
                        f"🌟 **GIANT WARRIOR**! 🌟\n"
                        f"**{attacker['name']}** becomes a giant!\n"
                        f"👊 3-turn transformation with defense boost + {bonus_damage} massive damage!"
                    )
                    
                elif effect_choice == "freedom":
                    # Freedom now boosts damage and provides immunity
                    bonus_damage = int(base_damage * 1.5)  # 150% damage boost
                    # Clear negative status effects
                    for status in ["burn", "stun", "frozen", "slow", "bind", "poison", "defense_down", "attack_down"]:
                        if status in attacker["status"]:
                            attacker["status"][status] = 0
                    # Add immunity
                    await self.status_manager.apply_effect("status_immunity", attacker, duration=2)
                    effect_message = (
                        f"🌈 **WARRIOR OF LIBERATION**! 🌈\n"
                        f"**{attacker['name']}** breaks all limitations!\n"
                        f"✨ Status immunity for 2 turns + {bonus_damage} liberation damage!"
                    )
                
                # Add chance for additional effect
                if random.random() < 0.25:  # 25% chance for extra joy boy effect
                    heal_amount = int(250 * 0.15)  # 15% of 250 HP = 37 HP heal
                    attacker["hp"] = min(attacker.get("max_hp", 250), attacker["hp"] + heal_amount)
                    effect_message += f"\n💫 **JOY BOY'S BLESSING**! Healed for {heal_amount} HP!"

        # Environment interactions
        if environment == "Wano" and ("Dragon" in effect or "Orochi" in effect):
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Power enhanced by Wano's legendary aura!"
        elif environment == "Zou" and ("elephant" in effect or "mammoth" in effect):
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n🐘 Power amplified by Zou's ancient might!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"✨ **ZOAN TRANSFORMATION**! ✨\n"
                f"**{attacker['name']}**'s beast form grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    async def _handle_paramecia_effects(self, attacker, defender, effect, move, environment):
        """Handle Paramecia-type Devil Fruit effects with consistent activation and balanced damage."""
        bonus_damage = 0
        effect_message = None
        
        base_damage = move.get("damage", 0)
        if base_damage == 0 and move.get("type") in ["regular", "strong", "critical"]:
            base_damage = 15  # Default average damage

        # Gomu Gomu no Mi
        if effect == "rubber" and move.get("type") == "strong":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.2)
                effect_message = (
                    f"✨ **RUBBER POWER**! ✨\n"
                    f"**{attacker['name']}** stretches for maximum power!\n"
                    f"💥 {bonus_damage} elastic bonus damage!"
                )

        # Ope Ope no Mi
        elif effect == "surgical":
            if random.random() < 0.35:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(base_damage * 0.8)
                effect_message = (
                    f"🏥 **ROOM: SHAMBLES**! 🏥\n"
                    f"**{attacker['name']}** performs surgical precision!\n"
                    f"✨ 2-turn stun + {bonus_damage} bonus damage!"
                )

        # Gura Gura no Mi
        elif effect == "quake":
            if random.random() < 0.45:
                bonus_damage = int(base_damage * 1.4)  # High damage multiplier
                await self.status_manager.apply_effect("stun", defender, duration=1)
                effect_message = (
                    f"💥 **SEISMIC SHOCK**! 💥\n"
                    f"**{attacker['name']}** shatters the air itself!\n"
                    f"🌋 {bonus_damage} quake damage + 1-turn stun!"
                )

        # Bari Bari no Mi
        elif effect == "barrier":
            if random.random() < 0.45:
                await self.status_manager.apply_effect("protect", attacker, duration=2)
                bonus_damage = int(base_damage * 0.5)
                effect_message = (
                    f"🛡️ **BARRIER CRUSH**! 🛡️\n"
                    f"**{attacker['name']}** creates an unbreakable barrier!\n"
                    f"✨ 2-turn protection + {bonus_damage} barrier damage!"
                )

        # Environment interactions
        if environment == "Dressrosa" and effect in ["string", "toy"]:
            bonus_damage = int(bonus_damage * 1.3)
            if effect_message:
                effect_message = f"{effect_message}\n🎭 Power amplified by Dressrosa's influence!"
        elif environment == "Marineford":
            bonus_damage = int(bonus_damage * 1.2)
            if effect_message:
                effect_message = f"{effect_message}\n⚔️ Sacred battleground amplifies power!"

        # If no specific effect triggered, provide minimal default effect
        if effect_message is None:
            bonus_damage = int(base_damage * 0.15)  # Reduced default bonus
            effect_message = (
                f"✨ **PARAMECIA POWER**! ✨\n"
                f"**{attacker['name']}**'s devil fruit grants {bonus_damage} bonus damage!"
            )

        return bonus_damage, effect_message

    def get_fruit_cooldown(self, fruit_name):
        """Get the cooldown for a Devil Fruit ability."""
        return self.fruit_cooldowns.get(fruit_name, 3)

    def is_fruit_on_cooldown(self, attacker, fruit_name):
        """Check if a Devil Fruit ability is on cooldown."""
        return fruit_name in attacker.get("fruit_cooldowns", {})