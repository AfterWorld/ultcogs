from typing import Tuple, List, Dict, Any

class StatusEffectManager:
    """Manages all status effects in battles."""
    
    def __init__(self):
        # Max stacks/durations for effects
        self.MAX_BURN_STACKS = 3
        self.MAX_STUN_DURATION = 2
        self.MAX_FREEZE_DURATION = 2
        self.MAX_POISON_STACKS = 3
        self.MAX_BIND_DURATION = 3
        self.MAX_ROOT_DURATION = 2
        self.MAX_SLOW_DURATION = 2
        
    async def apply_effect(self, effect_type: str, target: dict, value: int = 1, duration: int = 1):
        """Apply a status effect with proper stacking rules."""
        if "status" not in target:
            target["status"] = {}
            
        # Original effects
        if effect_type == "burn":
            current_stacks = target["status"].get("burn", 0)
            target["status"]["burn"] = min(current_stacks + value, self.MAX_BURN_STACKS)
            return f"🔥 Burn stacks: {target['status']['burn']}"
            
        elif effect_type == "stun":
            if not target["status"].get("stun", False):
                target["status"]["stun"] = min(duration, self.MAX_STUN_DURATION)
                return "⚡ Stunned!"
                
        elif effect_type == "freeze":
            current_freeze = target["status"].get("freeze", 0)
            target["status"]["freeze"] = min(current_freeze + duration, self.MAX_FREEZE_DURATION)
            return f"❄️ Frozen for {target['status']['freeze']} turns!"
            
        elif effect_type == "protect":
            target["status"]["protected"] = True
            target["status"]["protect_duration"] = duration
            return "🛡️ Protected!"

        # New effects for updated fruits
        elif effect_type == "poison":
            current_stacks = target["status"].get("poison", 0)
            target["status"]["poison"] = min(current_stacks + value, self.MAX_POISON_STACKS)
            return f"☠️ Poison stacks: {target['status']['poison']}"
            
        elif effect_type == "bind":
            target["status"]["bind"] = min(duration, self.MAX_BIND_DURATION)
            return f"🔒 Bound for {duration} turns!"
            
        elif effect_type == "root":
            target["status"]["root"] = min(duration, self.MAX_ROOT_DURATION)
            return f"🌿 Rooted for {duration} turns!"
            
        elif effect_type == "slow":
            target["status"]["slow"] = min(duration, self.MAX_SLOW_DURATION)
            return f"🐌 Slowed for {duration} turns!"
            
        elif effect_type == "defense_down":
            target["status"]["defense_down"] = duration
            return "🛡️ Defense reduced!"
            
        elif effect_type == "attack_down":
            target["status"]["attack_down"] = duration
            return "⚔️ Attack reduced!"
            
        elif effect_type == "defense_boost":
            target["status"]["defense_boost"] = duration
            return "🛡️ Defense boosted!"
            
        elif effect_type == "attack_boost":
            target["status"]["attack_boost"] = duration
            return "⚔️ Attack boosted!"
            
        elif effect_type == "speed_boost":
            target["status"]["speed_boost"] = duration
            return "💨 Speed boosted!"
            
        elif effect_type == "dodge":
            target["status"]["dodge"] = duration
            return "👻 Dodge active!"
            
        elif effect_type == "elemental_boost":
            target["status"]["elemental_boost"] = duration
            return "✨ Elemental power boosted!"
            
        elif effect_type == "status_immunity":
            target["status"]["status_immunity"] = duration
            return "🌟 Status immunity active!"
            
        elif effect_type == "thunder_charge":
            target["status"]["thunder_charge"] = duration
            return "⚡ Thunder charged!"
            
        elif effect_type == "shell_defense":
            target["status"]["shell_defense"] = duration
            return "🐢 Shell defense active!"

        return None

    async def process_effects(self, player: dict) -> tuple[list[str], int]:
        """Process all status effects on a player's turn."""
        if "status" not in player:
            return [], 0
            
        messages = []
        total_damage = 0
        
        # Process burn
        if player["status"].get("burn", 0) > 0:
            damage = 5 * player["status"]["burn"]
            total_damage += damage
            messages.append(f"🔥 Burn deals {damage} damage!")
            player["status"]["burn"] -= 1

        # Process poison
        if player["status"].get("poison", 0) > 0:
            damage = 8 * player["status"]["poison"]  # Poison does more damage than burn
            total_damage += damage
            messages.append(f"☠️ Poison deals {damage} damage!")
            player["status"]["poison"] -= 1
            
        # Process status effects that prevent actions
        for effect, message in [
            ("stun", "⚡ Stunned - Skip turn!"),
            ("freeze", "❄️ Frozen - Skip turn!"),
            ("bind", "🔒 Bound - Skip turn!"),
            ("root", "🌿 Rooted - Skip turn!")
        ]:
            if player["status"].get(effect, 0) > 0:
                messages.append(message)
                player["status"][effect] -= 1

        # Process buff/debuff durations
        for effect in [
            "protect", "defense_down", "attack_down", "defense_boost",
            "attack_boost", "speed_boost", "dodge", "elemental_boost",
            "status_immunity", "thunder_charge", "shell_defense"
        ]:
            effect_duration = f"{effect}_duration" if effect == "protect" else effect
            if player["status"].get(effect_duration, 0) > 0:
                player["status"][effect_duration] -= 1
                if player["status"][effect_duration] <= 0:
                    player["status"][effect] = False

        return messages, total_damage

    async def calculate_damage_with_effects(self, base_damage: int, attacker: dict, defender: dict) -> tuple[int, list[str]]:
        """Calculate final damage considering all status effects."""
        if not isinstance(base_damage, (int, float)):
            # If base_damage is not a number, log error and provide default
            base_damage = 0
        
        messages = []
        final_damage = base_damage
        
        # Ensure status dictionaries exist
        if "status" not in defender:
            defender["status"] = {}
        if "status" not in attacker:
            attacker["status"] = {}
        
        # Defender effects
        if defender["status"].get("protected", False):
            final_damage = int(final_damage * 0.5)
            messages.append("🛡️ Damage reduced by protection!")
            
        if defender["status"].get("shell_defense", 0):
            final_damage = int(final_damage * 0.6)  # 40% reduction
            messages.append("🐢 Shell defense reduces damage!")
            
        if defender["status"].get("defense_down", 0):
            final_damage = int(final_damage * 1.3)  # 30% more damage taken
            messages.append("🛡️ Reduced defense increases damage!")
            
        # Attacker effects
        if attacker["status"].get("attack_boost", 0):
            final_damage = int(final_damage * 1.3)
            messages.append("⚔️ Attack boost increases damage!")
            
        if attacker["status"].get("thunder_charge", 0):
            final_damage = int(final_damage * 1.25)
            messages.append("⚡ Thunder charge amplifies damage!")
            
        if attacker["status"].get("elemental_boost", 0):
            final_damage = int(final_damage * 1.2)
            messages.append("✨ Elemental boost increases damage!")
            
        if attacker["status"].get("attack_down", 0):
            final_damage = int(final_damage * 0.7)  # 30% less damage dealt
            messages.append("⚔️ Attack down reduces damage!")
            
        # Ensure damage is non-negative
        return max(0, final_damage), messages
        
    def clear_all_effects(self, player: dict):
        """Clear all status effects from a player."""
        if "status" in player:
            player["status"] = {}
            
    def get_effect_duration(self, player: dict, effect_type: str) -> int:
        """Get the remaining duration of a specific effect."""
        if "status" not in player:
            return 0
        return player["status"].get(effect_type, 0)
