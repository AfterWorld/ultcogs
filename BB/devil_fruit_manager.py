"""
Enhanced Devil Fruit effects manager for the DeathBattle system.
Handles all devil fruit types with detailed, unique effects for each fruit.
"""
import random
from typing import Dict, Any, Tuple, Optional

try:
    from .gamedata import DEVIL_FRUITS, MOVE_TYPES, ENVIRONMENTS
    from .status_manager import StatusEffectManager
    from .utils import setup_logger
except ImportError:
    from gamedata import DEVIL_FRUITS, MOVE_TYPES, ENVIRONMENTS
    from status_manager import StatusEffectManager
    from utils import setup_logger

class EnhancedDevilFruitManager:
    """Enhanced manager for Devil Fruit effects with unique abilities for each fruit."""
    
    def __init__(self, status_manager: StatusEffectManager):
        self.status_manager = status_manager
        self.log = setup_logger("enhanced_devil_fruit_manager")
        self.active_abilities = {}
        
        # Cooldown tracking for special abilities
        self.ability_cooldowns = {}
        
        # Effect multipliers for environments
        self.environment_multipliers = {
            "lightning_boost": 1.5,
            "desert_boost": 1.4,
            "blade_boost": 1.3,
            "elemental_boost": 1.6,
            "aquatic_boost": 1.3,
            "war_boost": 1.4,
            "legendary_boost": 2.0,
            "darkness_boost": 1.5,
            "justice_boost": 1.3,
            "nature_boost": 1.3,
            "food_boost": 1.2,
            "transformation_boost": 1.4
        }
    
    async def process_devil_fruit_effect(self, attacker: Dict[str, Any], defender: Dict[str, Any], 
                                       move: Dict[str, Any], environment: str) -> Tuple[int, Optional[str]]:
        """Process Devil Fruit effects with enhanced individual fruit abilities."""
        if not attacker.get("fruit"):
        # ADDITIONAL MYTHICAL ZOAN EFFECTS
    async def _nue_effect(self, attacker, defender, base_damage):
        """Tori Tori no Mi: Model Nue - Mythical Chimera"""
        if random.random() < 0.50:
            form = random.choice(["monkey", "tiger", "tanuki", "snake"])
            
            if form == "monkey":
                await self.status_manager.apply_effect("speed_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"🐒 **NUE MONKEY FORM!** 🐒\n"
                    f"**{attacker['name']}** shapeshifts into agile monkey!\n"
                    f"💨 {bonus_damage} nimble damage + speed boost!"
                )
            elif form == "tiger":
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("bleed", defender, value=2)
                return bonus_damage, (
                    f"🐅 **NUE TIGER FORM!** 🐅\n"
                    f"**{attacker['name']}** becomes a ferocious tiger!\n"
                    f"🩸 {bonus_damage} savage damage + bleeding!"
                )
            elif form == "tanuki":
                await self.status_manager.apply_effect("confusion", defender, duration=3)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🦝 **NUE TANUKI FORM!** 🦝\n"
                    f"**{attacker['name']}** creates illusions and mischief!\n"
                    f"🌀 {bonus_damage} trickster damage + 3-turn confusion!"
                )
            else:  # snake
                await self.status_manager.apply_effect("poison", defender, value=3)
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"🐍 **NUE SERPENT FORM!** 🐍\n"
                    f"**{attacker['name']}** strikes with venomous fangs!\n"
                    f"☠️ {bonus_damage} toxic damage + 3 Poison stacks!"
                )
        return 0, None

    # MISSING SEIRYU EFFECT
    async def _seiryu_effect(self, attacker, defender, base_damage, environment):
        """Uo Uo no Mi: Model Seiryu - Azure Dragon"""
        if random.random() < 0.55:
            breath_type = random.choice(["fire", "wind", "lightning", "ultimate"])
            
            if breath_type == "fire":
                bonus_damage = int(base_damage * 1.3)
                await self.status_manager.apply_effect("burn", defender, value=3)
                return bonus_damage, (
                    f"🔥 **DRAGON FLAME BREATH!** 🔥\n"
                    f"**{attacker['name']}** breathes scorching dragon fire!\n"
                    f"🐉 {bonus_damage} dragon fire damage + 3 Burn stacks!"
                )
            elif breath_type == "wind":
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"💨 **DRAGON WIND SCYTHES!** 💨\n"
                    f"**{attacker['name']}** creates cutting wind blades!\n"
                    f"🌪️ {bonus_damage} wind blade damage + confusion!"
                )
            elif breath_type == "lightning":
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("stun", defender, duration=2)
                return bonus_damage, (
                    f"⚡ **DRAGON LIGHTNING!** ⚡\n"
                    f"**{attacker['name']}** calls down divine thunder!\n"
                    f"🐲 {bonus_damage} dragon lightning + 2-turn stun!"
                )
            else:  # ultimate
                bonus_damage = int(base_damage * 2.0)
                return bonus_damage, (
                    f"🐉 **AZURE DRAGON SUPREMACY!** 🐉\n"
                    f"**{attacker['name']}** unleashes the full power of the Azure Dragon!\n"
                    f"💥 {bonus_damage} overwhelming dragon damage!"
                )
        return 0, None

    # ADDITIONAL PARAMECIA EFFECTS
    async def _mane_mane_effect(self, attacker, defender, base_damage):
        """Mane Mane no Mi - Clone Paramecia"""
        if random.random() < 0.40:
            # Copy opponent's last move with reduced power
            bonus_damage = int(base_damage * 1.1)
            await self.status_manager.apply_effect("confusion", defender, duration=2)
            return bonus_damage, (
                f"👤 **PERFECT MIMICRY!** 👤\n"
                f"**{attacker['name']}** copies the enemy's appearance and style!\n"
                f"🎭 {bonus_damage} mimic damage + 2-turn confusion!"
            )
        return 0, None

    async def _sube_sube_effect(self, attacker, defender, base_damage):
        """Sube Sube no Mi - Smooth Paramecia"""
        if random.random() < 0.45:
            # Enhanced evasion
            await self.status_manager.apply_effect("dodge", attacker, duration=3)
            bonus_damage = int(base_damage * 0.8)
            return bonus_damage, (
                f"✨ **SMOOTH SLIP!** ✨\n"
                f"**{attacker['name']}** becomes perfectly smooth!\n"
                f"💫 {bonus_damage} slippery damage + 3-turn enhanced evasion!"
            )
        return 0, None

    async def _noro_noro_effect(self, attacker, defender, base_damage):
        """Noro Noro no Mi - Slow Paramecia"""
        if random.random() < 0.50:
            # Slow down opponent significantly
            await self.status_manager.apply_effect("slow", defender, duration=4)
            bonus_damage = int(base_damage * 0.9)
            return bonus_damage, (
                f"🐌 **NORO NORO BEAM!** 🐌\n"
                f"**{attacker['name']}** fires slow-slow photons!\n"
                f"⏰ {bonus_damage} temporal damage + 4-turn extreme slow!"
            )
        return 0, None

    async def _doa_doa_effect(self, attacker, defender, base_damage):
        """Doa Doa no Mi - Door Paramecia"""
        if random.random() < 0.45:
            door_type = random.choice(["escape", "portal", "trap"])
            
            if door_type == "escape":
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"🚪 **DOOR ESCAPE!** 🚪\n"
                    f"**{attacker['name']}** opens doors to safety!\n"
                    f"🎪 {bonus_damage} spatial damage + enhanced dodge!"
                )
            elif door_type == "portal":
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🚪 **PORTAL STRIKE!** 🚪\n"
                    f"**{attacker['name']}** attacks through dimensional doors!\n"
                    f"🌀 {bonus_damage} portal damage from unexpected angles!"
                )
            else:  # trap
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🚪 **DOOR TRAP!** 🚪\n"
                    f"**{attacker['name']}** traps enemy behind closing doors!\n"
                    f"🔒 {bonus_damage} trapping damage + 2-turn binding!"
                )
        return 0, None

    async def _awa_awa_effect(self, attacker, defender, base_damage):
        """Awa Awa no Mi - Bubble Paramecia"""
        if random.random() < 0.45:
            bubble_type = random.choice(["cleanse", "trap", "slip"])
            
            if bubble_type == "cleanse":
                # Remove enemy's beneficial effects
                if "status" in defender:
                    beneficial_effects = ["attack_boost", "defense_boost", "speed_boost", "dodge"]
                    for effect in beneficial_effects:
                        if effect in defender["status"]:
                            del defender["status"][effect]
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🫧 **CLEANSING BUBBLES!** 🫧\n"
                    f"**{attacker['name']}** washes away enemy enhancements!\n"
                    f"🧽 {bonus_damage} cleansing damage + buffs removed!"
                )
            elif bubble_type == "trap":
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🫧 **BUBBLE PRISON!** 🫧\n"
                    f"**{attacker['name']}** traps enemy in soap bubbles!\n"
                    f"💭 {bonus_damage} bubble damage + 2-turn binding!"
                )
            else:  # slip
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🫧 **SLIPPERY BUBBLES!** 🫧\n"
                    f"**{attacker['name']}** makes everything slippery!\n"
                    f"🧼 {bonus_damage} slip damage + 2-turn confusion!"
                )
        return 0, None

    async def _memo_memo_effect(self, attacker, defender, base_damage):
        """Memo Memo no Mi - Memory Paramecia"""
        if random.random() < 0.40:
            memory_type = random.choice(["forget", "confuse", "steal"])
            
            if memory_type == "forget":
                # Enemy forgets their next special move
                defender["next_move_forgotten"] = True
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🧠 **MEMORY WIPE!** 🧠\n"
                    f"**{attacker['name']}** erases combat memories!\n"
                    f"💭 {bonus_damage} mental damage + next special move forgotten!"
                )
            elif memory_type == "confuse":
                await self.status_manager.apply_effect("confusion", defender, duration=3)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🧠 **MEMORY SCRAMBLE!** 🧠\n"
                    f"**{attacker['name']}** scrambles enemy memories!\n"
                    f"🌀 {bonus_damage} psychic damage + 3-turn confusion!"
                )
            else:  # steal
                # Steal a beneficial effect
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🧠 **MEMORY THEFT!** 🧠\n"
                    f"**{attacker['name']}** steals combat knowledge!\n"
                    f"🎯 {bonus_damage} knowledge damage + stolen techniques!"
                )
        return 0, None

    async def _nui_nui_effect(self, attacker, defender, base_damage):
        """Nui Nui no Mi - Stitch Paramecia"""
        if random.random() < 0.50:
            stitch_type = random.choice(["bind", "repair", "pierce"])
            
            if stitch_type == "bind":
                await self.status_manager.apply_effect("bind", defender, duration=3)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🧵 **STITCH BINDING!** 🧵\n"
                    f"**{attacker['name']}** sews the enemy in place!\n"
                    f"🪡 {bonus_damage} binding damage + 3-turn immobilization!"
                )
            elif stitch_type == "repair":
                heal_amount = int(attacker["max_hp"] * 0.12)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amount)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"🧵 **SELF REPAIR!** 🧵\n"
                    f"**{attacker['name']}** stitches their wounds!\n"
                    f"💚 Healed {heal_amount} HP + {bonus_damage} stitch damage!"
                )
            else:  # pierce
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("bleed", defender, value=2)
                return bonus_damage, (
                    f"🧵 **PIERCING NEEDLES!** 🧵\n"
                    f"**{attacker['name']}** attacks with sharp needles!\n"
                    f"🩸 {bonus_damage} piercing damage + bleeding!"
                )
        return 0, None

    async def _giro_giro_effect(self, attacker, defender, base_damage):
        """Giro Giro no Mi - Stare Paramecia"""
        if random.random() < 0.45:
            stare_type = random.choice(["truth", "fear", "weakness"])
            
            if stare_type == "truth":
                # See through enemy defenses
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"👁️ **TRUTH SIGHT!** 👁️\n"
                    f"**{attacker['name']}** sees through all deceptions!\n"
                    f"🎯 {bonus_damage} piercing damage (ignores defense)!"
                )
            elif stare_type == "fear":
                await self.status_manager.apply_effect("fear", defender, duration=3)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"👁️ **TERRIFYING GAZE!** 👁️\n"
                    f"**{attacker['name']}** stares into the enemy's soul!\n"
                    f"😨 {bonus_damage} fear damage + 3-turn terror!"
                )
            else:  # weakness
                # Reveal and exploit weaknesses
                await self.status_manager.apply_effect("defense_down", defender, duration=2)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"👁️ **WEAKNESS EXPOSED!** 👁️\n"
                    f"**{attacker['name']}** finds the enemy's weak points!\n"
                    f"🎯 {bonus_damage} precise damage + defense lowered!"
                )
        return 0, None

    async def _ato_ato_effect(self, attacker, defender, base_damage):
        """Ato Ato no Mi - Art Paramecia"""
        if random.random() < 0.40:
            art_type = random.choice(["painting", "sculpture", "abstract"])
            
            if art_type == "painting":
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🎨 **LIVING PAINTING!** 🎨\n"
                    f"**{attacker['name']}** brings art to life!\n"
                    f"🖼️ {bonus_damage} artistic damage + 2-turn confusion!"
                )
            elif art_type == "sculpture":
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"🎨 **STONE SCULPTURE!** 🎨\n"
                    f"**{attacker['name']}** turns enemy into art!\n"
                    f"🗿 {bonus_damage} petrifying damage + 1-turn stun!"
                )
            else:  # abstract
                # Random chaotic effect
                chaos_damage = random.randint(int(base_damage * 0.5), int(base_damage * 1.8))
                return chaos_damage, (
                    f"🎨 **ABSTRACT CHAOS!** 🎨\n"
                    f"**{attacker['name']}** creates incomprehensible art!\n"
                    f"🌀 {chaos_damage} chaotic damage (unpredictable power)!"
                )
        return 0, None

    async def _pamu_pamu_effect(self, attacker, defender, base_damage):
        """Pamu Pamu no Mi - Rupture Paramecia"""
        if random.random() < 0.50:
            rupture_type = random.choice(["body", "ground", "air"])
            
            if rupture_type == "body":
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("bleed", defender, value=3)
                return bonus_damage, (
                    f"💥 **BODY RUPTURE!** 💥\n"
                    f"**{attacker['name']}** causes internal rupturing!\n"
                    f"🩸 {bonus_damage} rupture damage + severe bleeding!"
                )
            elif rupture_type == "ground":
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"💥 **GROUND RUPTURE!** 💥\n"
                    f"**{attacker['name']}** explodes the battlefield!\n"
                    f"🌋 {bonus_damage} explosive damage + environmental chaos!"
                )
            else:  # air
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"💥 **AIR RUPTURE!** 💥\n"
                    f"**{attacker['name']}** explodes the very air!\n"
                    f"💨 {bonus_damage} atmospheric damage!"
                )
        return 0, None

    async def _sui_sui_effect(self, attacker, defender, base_damage):
        """Sui Sui no Mi - Swim Paramecia"""
        if random.random() < 0.45:
            swim_type = random.choice(["wall", "ground", "surprise"])
            
            if swim_type == "wall":
                await self.status_manager.apply_effect("dodge", attacker, duration=2)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🏊 **WALL SWIMMING!** 🏊\n"
                    f"**{attacker['name']}** swims through solid walls!\n"
                    f"🧱 {bonus_damage} phase damage + enhanced evasion!"
                )
            elif swim_type == "ground":
                bonus_damage = int(base_damage * 1.1)
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"🏊 **UNDERGROUND SWIM!** 🏊\n"
                    f"**{attacker['name']}** attacks from below!\n"
                    f"⬆️ {bonus_damage} surprise damage + confusion!"
                )
            else:  # surprise
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🏊 **SURPRISE EMERGENCE!** 🏊\n"
                    f"**{attacker['name']}** emerges unexpectedly!\n"
                    f"😲 {bonus_damage} surprise attack damage!"
                )
        return 0, None

    async def _ton_ton_effect(self, attacker, defender, base_damage):
        """Ton Ton no Mi - Ton Paramecia"""
        if random.random() < 0.50:
            weight = random.choice(["1000", "5000", "10000"])
            
            if weight == "1000":
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"⚖️ **1000 TON PRESS!** ⚖️\n"
                    f"**{attacker['name']}** becomes incredibly heavy!\n"
                    f"💥 {bonus_damage} crushing weight damage!"
                )
            elif weight == "5000":
                bonus_damage = int(base_damage * 1.5)
                await self.status_manager.apply_effect("stun", defender, duration=1)
                return bonus_damage, (
                    f"⚖️ **5000 TON SLAM!** ⚖️\n"
                    f"**{attacker['name']}** crashes down with massive weight!\n"
                    f"💥 {bonus_damage} devastating weight + stun!"
                )
            else:  # 10000
                bonus_damage = int(base_damage * 2.0)
                # Self damage from extreme weight
                self_damage = int(base_damage * 0.15)
                attacker["hp"] = max(1, attacker["hp"] - self_damage)
                return bonus_damage, (
                    f"⚖️ **10,000 TON METEOR!** ⚖️\n"
                    f"**{attacker['name']}** becomes a living meteor!\n"
                    f"💥 {bonus_damage} catastrophic weight damage!\n"
                    f"⚠️ Strain damage: {self_damage} self-damage!"
                )
        return 0, None

    async def _beta_beta_effect(self, attacker, defender, base_damage):
        """Beta Beta no Mi - Stick Paramecia"""
        if random.random() < 0.50:
            stick_type = random.choice(["trap", "armor", "weapon"])
            
            if stick_type == "trap":
                await self.status_manager.apply_effect("bind", defender, duration=3)
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🍯 **STICKY TRAP!** 🍯\n"
                    f"**{attacker['name']}** creates an inescapable sticky trap!\n"
                    f"🕸️ {bonus_damage} adhesive damage + 3-turn binding!"
                )
            elif stick_type == "armor":
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"🍯 **STICKY ARMOR!** 🍯\n"
                    f"**{attacker['name']}** coats themselves in protective resin!\n"
                    f"🛡️ {bonus_damage} sticky damage + enhanced defense!"
                )
            else:  # weapon
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"🍯 **STICKY WEAPON!** 🍯\n"
                    f"**{attacker['name']}** forms weapons from sticky substances!\n"
                    f"⚔️ {bonus_damage} adhesive weapon damage!"
                )
        return 0, None

    async def _hira_hira_effect(self, attacker, defender, base_damage):
        """Hira Hira no Mi - Flag Paramecia"""
        if random.random() < 0.45:
            flag_type = random.choice(["flatten", "wave", "banner"])
            
            if flag_type == "flatten":
                await self.status_manager.apply_effect("stun", defender, duration=1)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"🏴 **FLATTEN ATTACK!** 🏴\n"
                    f"**{attacker['name']}** flattens everything like a flag!\n"
                    f"📄 {bonus_damage} flattening damage + stun!"
                )
            elif flag_type == "wave":
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🏴 **FLAG WAVE!** 🏴\n"
                    f"**{attacker['name']}** waves like a flag in the wind!\n"
                    f"💨 {bonus_damage} waving damage + 2-turn confusion!"
                )
            else:  # banner
                await self.status_manager.apply_effect("attack_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🏴 **BATTLE BANNER!** 🏴\n"
                    f"**{attacker['name']}** raises their battle flag!\n"
                    f"⚔️ {bonus_damage} inspiring damage + attack boost!"
                )
        return 0, None

    async def _ishi_ishi_effect(self, attacker, defender, base_damage):
        """Ishi Ishi no Mi - Stone Paramecia"""
        if random.random() < 0.50:
            stone_type = random.choice(["merge", "throw", "fortress"])
            
            if stone_type == "merge":
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🪨 **STONE MERGER!** 🪨\n"
                    f"**{attacker['name']}** merges with stone structures!\n"
                    f"🏰 {bonus_damage} stone damage + enhanced defense!"
                )
            elif stone_type == "throw":
                hits = random.randint(3, 6)
                bonus_damage = int(base_damage * 0.7 * hits)
                return bonus_damage, (
                    f"🪨 **STONE BARRAGE!** 🪨\n"
                    f"**{attacker['name']}** hurls {hits} stone projectiles!\n"
                    f"💥 {hits} stones for {bonus_damage} total damage!"
                )
            else:  # fortress
                await self.status_manager.apply_effect("defense_boost", attacker, duration=4)
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🪨 **STONE FORTRESS!** 🪨\n"
                    f"**{attacker['name']}** becomes an impregnable fortress!\n"
                    f"🏰 {bonus_damage} fortress damage + massive defense boost!"
                )
        return 0, None
            
        fruit_name = attacker["fruit"]
        
        # Check if fruit is disabled (by Yami Yami no Mi)
        if attacker.get("fruit_disabled", 0) > 0:
            attacker["fruit_disabled"] -= 1
            return 0, "🚫 Devil Fruit powers are nullified!"
        
        # Get fruit data
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        if not fruit_data:
            return 0, None

        # Track usage for achievements
        if "fruits_used" not in attacker:
            attacker["fruits_used"] = set()
        attacker["fruits_used"].add(fruit_name)

        # Check for fruit vs fruit interactions first
        defender_fruit = defender.get("fruit")
        if defender_fruit:
            interaction_damage, interaction_message = await self._check_fruit_interactions(
                fruit_name, defender_fruit, self._get_base_damage(move)
            )
            if interaction_damage != 0:
                return interaction_damage, interaction_message

        # Check for awakened abilities (high-level players)
        awakened_damage, awakened_message = await self._handle_awakened_abilities(
            fruit_name, attacker, defender, self._get_base_damage(move)
        )
        if awakened_damage > 0:
            return awakened_damage, awakened_message

        # Process specific fruit effects
        bonus_damage, effect_message = await self._process_specific_fruit(
            fruit_name, attacker, defender, move, environment
        )
        
        # Apply mastery bonus
        if bonus_damage > 0:
            mastery_multiplier = self._calculate_fruit_mastery_bonus(attacker, fruit_name)
            bonus_damage = int(bonus_damage * mastery_multiplier)
        
        # Apply environment bonuses
        bonus_damage = self._apply_environment_bonus(bonus_damage, fruit_name, environment)
        
        return bonus_damage, effect_message

    async def _process_specific_fruit(self, fruit_name: str, attacker: Dict[str, Any], 
                                    defender: Dict[str, Any], move: Dict[str, Any], 
                                    environment: str) -> Tuple[int, Optional[str]]:
        """Process effects for specific devil fruits."""
        
        # Get base damage for calculations
        base_damage = self._get_base_damage(move)
        
        # Logia Fruits
        if fruit_name == "Mera Mera no Mi":
            return await self._mera_mera_effect(attacker, defender, base_damage, environment)
        elif fruit_name == "Hie Hie no Mi":
            return await self._hie_hie_effect(attacker, defender, base_damage, environment)
        elif fruit_name == "Yami Yami no Mi":
            return await self._yami_yami_effect(attacker, defender, base_damage)
        elif fruit_name == "Pika Pika no Mi":
            return await self._pika_pika_effect(attacker, defender, base_damage)
        elif fruit_name == "Goro Goro no Mi":
            return await self._goro_goro_effect(attacker, defender, base_damage, environment)
        elif fruit_name == "Magu Magu no Mi":
            return await self._magu_magu_effect(attacker, defender, base_damage)
        elif fruit_name == "Suna Suna no Mi":
            return await self._suna_suna_effect(attacker, defender, base_damage, environment)
        elif fruit_name == "Gasu Gasu no Mi":
            return await self._gasu_gasu_effect(attacker, defender, base_damage)
        elif fruit_name == "Moku Moku no Mi":
            return await self._moku_moku_effect(attacker, defender, base_damage)
        elif fruit_name == "Numa Numa no Mi":
            return await self._numa_numa_effect(attacker, defender, base_damage)
        elif fruit_name == "Yuki Yuki no Mi":
            return await self._yuki_yuki_effect(attacker, defender, base_damage)
        
        # Mythical Zoans
        elif fruit_name == "Tori Tori no Mi: Model Phoenix":
            return await self._phoenix_effect(attacker, defender, base_damage)
        elif fruit_name == "Uo Uo no Mi: Model Seiryu":
            return await self._seiryu_effect(attacker, defender, base_damage, environment)
        elif fruit_name == "Hito Hito no Mi: Model Nika":
            return await self._nika_effect(attacker, defender, base_damage)
        elif fruit_name == "Hito Hito no Mi: Model Daibutsu":
            return await self._daibutsu_effect(attacker, defender, base_damage)
        elif fruit_name == "Inu Inu no Mi: Model Okuchi no Makami":
            return await self._okuchi_no_makami_effect(attacker, defender, base_damage)
        elif fruit_name == "Hebi Hebi no Mi: Model Yamata no Orochi":
            return await self._yamata_no_orochi_effect(attacker, defender, base_damage)
        
        # Ancient Zoans
        elif "Ancient Zoan" in DEVIL_FRUITS["Rare"].get(fruit_name, {}).get("type", ""):
            return await self._ancient_zoan_effect(fruit_name, attacker, defender, base_damage)
        
        # Special Paramecia
        elif fruit_name == "Mochi Mochi no Mi":
            return await self._mochi_effect(attacker, defender, base_damage)
        elif fruit_name == "Gura Gura no Mi":
            return await self._gura_gura_effect(attacker, defender, base_damage)
        elif fruit_name == "Ope Ope no Mi":
            return await self._ope_ope_effect(attacker, defender, base_damage)
        elif fruit_name == "Zushi Zushi no Mi":
            return await self._zushi_zushi_effect(attacker, defender, base_damage)
        elif fruit_name == "Hobi Hobi no Mi":
            return await self._hobi_hobi_effect(attacker, defender, base_damage)
        elif fruit_name == "Bari Bari no Mi":
            return await self._bari_bari_effect(attacker, defender, base_damage)
        
        # Regular Paramecia
        elif fruit_name == "Gomu Gomu no Mi":
            return await self._gomu_gomu_effect(attacker, defender, base_damage, move)
        elif fruit_name == "Bomu Bomu no Mi":
            return await self._bomu_bomu_effect(attacker, defender, base_damage)
        elif fruit_name == "Hana Hana no Mi":
            return await self._hana_hana_effect(attacker, defender, base_damage)
        elif fruit_name == "Supa Supa no Mi":
            return await self._supa_supa_effect(attacker, defender, base_damage)
        elif fruit_name == "Doru Doru no Mi":
            return await self._doru_doru_effect(attacker, defender, base_damage)
        
        # Regular Zoans
        elif "Zoan" in DEVIL_FRUITS["Common"].get(fruit_name, {}).get("type", ""):
            return await self._regular_zoan_effect(fruit_name, attacker, defender, base_damage)
        
        # Default effect for unspecified fruits
        return await self._default_fruit_effect(fruit_name, attacker, defender, base_damage)

    # LOGIA EFFECTS
    async def _mera_mera_effect(self, attacker, defender, base_damage, environment):
        """Mera Mera no Mi - Fire Logia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.0)
            await self.status_manager.apply_effect("burn", defender, value=2)
            
            # Special: Fire Lance
            if random.random() < 0.3:
                bonus_damage = int(base_damage * 1.5)
                return bonus_damage, (
                    f"🔥 **FIRE LANCE!** 🔥\n"
                    f"**{attacker['name']}** launches a concentrated fire spear!\n"
                    f"💥 {bonus_damage} fire damage + 2 Burn stacks!"
                )
            
            return bonus_damage, (
                f"🔥 **FLAME EMPEROR!** 🔥\n"
                f"**{attacker['name']}** unleashes burning flames!\n"
                f"💥 {bonus_damage} fire damage + Burn!"
            )
        return 0, None

    async def _hie_hie_effect(self, attacker, defender, base_damage, environment):
        """Hie Hie no Mi - Ice Logia"""
        if random.random() < 0.45:
            bonus_damage = int(base_damage * 0.9)
            
            # Special: Absolute Zero
            if random.random() < 0.25:
                await self.status_manager.apply_effect("freeze", defender, duration=3)
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"❄️ **ABSOLUTE ZERO!** ❄️\n"
                    f"**{attacker['name']}** freezes everything solid!\n"
                    f"🧊 {bonus_damage} ice damage + 3-turn freeze!"
                )
            else:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                return bonus_damage, (
                    f"❄️ **ICE AGE!** ❄️\n"
                    f"**{attacker['name']}** creates a frozen wasteland!\n"
                    f"🥶 {bonus_damage} ice damage + 2-turn freeze!"
                )
        return 0, None

    async def _yami_yami_effect(self, attacker, defender, base_damage):
        """Yami Yami no Mi - Darkness Logia"""
        if random.random() < 0.55:
            # Absorb power
            absorb = int(base_damage * 1.5)
            attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + absorb)
            bonus_damage = int(base_damage * 1.1)
            
            # Special: Disable Devil Fruit temporarily
            if random.random() < 0.3:
                defender["fruit_disabled"] = 2  # 2 turns
                return bonus_damage, (
                    f"🌑 **DARK VOID!** 🌑\n"
                    f"**{attacker['name']}** nullifies Devil Fruit powers!\n"
                    f"⚫ {bonus_damage} void damage + absorbed {absorb} HP!\n"
                    f"🚫 Enemy's Devil Fruit disabled for 2 turns!"
                )
            
            return bonus_damage, (
                f"🌑 **BLACK HOLE!** 🌑\n"
                f"**{attacker['name']}** commands infinite darkness!\n"
                f"⚫ {bonus_damage} void damage + absorbed {absorb} HP!"
            )
        return 0, None

    async def _pika_pika_effect(self, attacker, defender, base_damage):
        """Pika Pika no Mi - Light Logia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.3)
            
            # Special: Light Speed Barrage
            if random.random() < 0.35:
                hits = random.randint(2, 4)
                bonus_damage *= hits
                return bonus_damage, (
                    f"✨ **LIGHT SPEED ASSAULT!** ✨\n"
                    f"**{attacker['name']}** attacks at the speed of light!\n"
                    f"⚡ {hits} light-speed hits for {bonus_damage} total damage!"
                )
            
            return bonus_damage, (
                f"✨ **SACRED YASAKANI!** ✨\n"
                f"**{attacker['name']}** fires devastating light beams!\n"
                f"⚡ {bonus_damage} piercing light damage!"
            )
        return 0, None

    async def _goro_goro_effect(self, attacker, defender, base_damage, environment):
        """Goro Goro no Mi - Lightning Logia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.1)
            
            # Special: Thunder God Judgment
            if random.random() < 0.4:
                await self.status_manager.apply_effect("stun", defender, duration=3)
                bonus_damage = int(base_damage * 1.4)
                return bonus_damage, (
                    f"⚡ **DIVINE JUDGMENT!** ⚡\n"
                    f"**{attacker['name']}** calls down heavenly lightning!\n"
                    f"💫 {bonus_damage} divine damage + 3-turn paralysis!"
                )
            else:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                return bonus_damage, (
                    f"⚡ **THUNDER GOD!** ⚡\n"
                    f"**{attacker['name']}** channels pure electricity!\n"
                    f"💫 {bonus_damage} lightning damage + 2-turn stun!"
                )
        return 0, None

    # MYTHICAL ZOAN EFFECTS
    async def _phoenix_effect(self, attacker, defender, base_damage):
        """Tori Tori no Mi: Model Phoenix"""
        if random.random() < 0.50:
            heal_amount = int(attacker["max_hp"] * 0.20)
            attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amount)
            bonus_damage = int(base_damage * 0.9)
            
            # Special: Resurrection Flames
            if attacker["hp"] < attacker["max_hp"] * 0.3:
                heal_amount *= 2
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal_amount)
                return bonus_damage, (
                    f"🦅 **RESURRECTION PHOENIX!** 🦅\n"
                    f"**{attacker['name']}** rises from near death!\n"
                    f"💚 Massive heal: {heal_amount} HP + {bonus_damage} blue flame damage!"
                )
            
            return bonus_damage, (
                f"🦅 **PHOENIX REBIRTH!** 🦅\n"
                f"**{attacker['name']}** bathes in regenerative flames!\n"
                f"💚 Healed {heal_amount} HP + {bonus_damage} flame damage!"
            )
        return 0, None

    async def _nika_effect(self, attacker, defender, base_damage):
        """Hito Hito no Mi: Model Nika - Sun God"""
        if random.random() < 0.60:
            # Random reality-bending effect
            effects = ["drums", "giant", "toon", "liberation"]
            chosen_effect = random.choice(effects)
            
            if chosen_effect == "drums":
                bonus_damage = int(base_damage * 2.2)
                await self.status_manager.apply_effect("attack_boost", attacker, duration=3)
                return bonus_damage, (
                    f"🥁 **DRUMS OF LIBERATION!** 🥁\n"
                    f"**{attacker['name']}** awakens the rhythm of freedom!\n"
                    f"💥 {bonus_damage} liberation damage + 3-turn attack boost!"
                )
            elif chosen_effect == "giant":
                bonus_damage = int(base_damage * 2.0)
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                return bonus_damage, (
                    f"🌟 **GIANT TRANSFORMATION!** 🌟\n"
                    f"**{attacker['name']}** becomes a colossal warrior!\n"
                    f"👊 {bonus_damage} giant damage + defense boost!"
                )
            elif chosen_effect == "toon":
                # Toon force - ignore damage and counter
                defender["next_attack_nullified"] = True
                bonus_damage = int(base_damage * 1.8)
                return bonus_damage, (
                    f"😄 **TOON FORCE!** 😄\n"
                    f"**{attacker['name']}** bends reality with cartoon physics!\n"
                    f"🎪 {bonus_damage} toon damage + next enemy attack nullified!"
                )
            else:  # liberation
                bonus_damage = int(base_damage * 1.5)
                # Free ally from all status effects
                if "status" in attacker:
                    attacker["status"] = {}
                return bonus_damage, (
                    f"🗽 **LIBERATION WAVE!** 🗽\n"
                    f"**{attacker['name']}** frees themselves from all constraints!\n"
                    f"✨ {bonus_damage} freedom damage + all status effects removed!"
                )
        return 0, None

    # PARAMECIA EFFECTS
    async def _gomu_gomu_effect(self, attacker, defender, base_damage, move):
        """Gomu Gomu no Mi - Rubber Paramecia"""
        if move.get("type") == "strong" and random.random() < 0.45:
            bonus_damage = int(base_damage * 1.3)
            
            # Special: Gear transformation
            if random.random() < 0.3:
                gear = random.choice(["second", "third", "fourth"])
                if gear == "second":
                    await self.status_manager.apply_effect("speed_boost", attacker, duration=3)
                    bonus_damage = int(base_damage * 1.1)
                    return bonus_damage, (
                        f"💨 **GEAR SECOND!** 💨\n"
                        f"**{attacker['name']}** pumps blood at superhuman speed!\n"
                        f"🚀 {bonus_damage} enhanced damage + speed boost!"
                    )
                elif gear == "third":
                    bonus_damage = int(base_damage * 1.6)
                    return bonus_damage, (
                        f"💪 **GEAR THIRD!** 💪\n"
                        f"**{attacker['name']}** inflates into a giant!\n"
                        f"👊 {bonus_damage} giant bone damage!"
                    )
                elif gear == "fourth":
                    bonus_damage = int(base_damage * 1.8)
                    await self.status_manager.apply_effect("attack_boost", attacker, duration=2)
                    return bonus_damage, (
                        f"🎈 **GEAR FOURTH!** 🎈\n"
                        f"**{attacker['name']}** becomes Boundman!\n"
                        f"💥 {bonus_damage} boundman damage + attack boost!"
                    )
            
            return bonus_damage, (
                f"🔴 **RUBBER POWER!** 🔴\n"
                f"**{attacker['name']}** stretches for maximum impact!\n"
                f"💥 {bonus_damage} elastic damage!"
            )
        return 0, None

    async def _gura_gura_effect(self, attacker, defender, base_damage):
        """Gura Gura no Mi - Quake Paramecia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.6)
            await self.status_manager.apply_effect("stun", defender, duration=2)
            
            # Special: World Destruction
            if random.random() < 0.25:
                bonus_damage = int(base_damage * 2.5)
                # Damage environment (affects both)
                environmental_damage = int(base_damage * 0.3)
                attacker["hp"] = max(1, attacker["hp"] - environmental_damage)
                return bonus_damage, (
                    f"💥 **WORLD DESTRUCTION!** 💥\n"
                    f"**{attacker['name']}** cracks the very world!\n"
                    f"🌋 {bonus_damage} catastrophic damage!\n"
                    f"⚠️ Environmental backlash: {environmental_damage} self-damage!"
                )
            
            return bonus_damage, (
                f"💥 **SEISMIC DEVASTATION!** 💥\n"
                f"**{attacker['name']}** shatters space itself!\n"
                f"🌋 {bonus_damage} earthquake damage + 2-turn stun!"
            )
        return 0, None

    async def _ope_ope_effect(self, attacker, defender, base_damage):
        """Ope Ope no Mi - Operation Paramecia"""
        if random.random() < 0.50:
            operation = random.choice(["shambles", "mes", "injection", "gamma_knife"])
            
            if operation == "shambles":
                # Teleport confusion
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"🔄 **SHAMBLES!** 🔄\n"
                    f"**{attacker['name']}** teleports and confuses!\n"
                    f"💫 {bonus_damage} spatial damage + 2-turn confusion!"
                )
            elif operation == "mes":
                # Heart removal (massive crit chance next turn)
                attacker["next_crit_guaranteed"] = True
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"💗 **MES!** 💗\n"
                    f"**{attacker['name']}** removes the enemy's heart!\n"
                    f"🎯 {bonus_damage} precise damage + next attack guaranteed crit!"
                )
            elif operation == "injection":
                # Healing injection
                heal = int(attacker["max_hp"] * 0.15)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + heal)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"💉 **INJECTION SHOT!** 💉\n"
                    f"**{attacker['name']}** performs surgery mid-battle!\n"
                    f"💚 Healed {heal} HP + {bonus_damage} surgical damage!"
                )
            else:  # gamma_knife
                # Ignore defense
                bonus_damage = int(base_damage * 1.8)
                return bonus_damage, (
                    f"⚡ **GAMMA KNIFE!** ⚡\n"
                    f"**{attacker['name']}** cuts from the inside!\n"
                    f"🔪 {bonus_damage} internal damage (ignores defense)!"
                )
        return 0, None

    # ZOAN EFFECTS
    async def _regular_zoan_effect(self, fruit_name, attacker, defender, base_damage):
        """Regular Zoan transformation effects"""
        if random.random() < 0.40:
            effect = DEVIL_FRUITS["Common"][fruit_name]["effect"]
            
            if "leopard" in effect:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.1)
                hits = random.randint(2, 3)
                bonus_damage *= hits
                return bonus_damage, (
                    f"🐆 **PREDATOR'S HUNT!** 🐆\n"
                    f"**{attacker['name']}** strikes with feline fury!\n"
                    f"⚡ {hits} rapid strikes for {bonus_damage} total damage!"
                )
            elif "elephant" in effect:
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("stun", defender, duration=1)
                return bonus_damage, (
                    f"🐘 **MAMMOTH CHARGE!** 🐘\n"
                    f"**{attacker['name']}** charges with massive force!\n"
                    f"💥 {bonus_damage} trampling damage + stun!"
                )
            elif "wolf" in effect:
                bonus_damage = int(base_damage * 1.2)
                # Pack hunting bonus if ally present
                return bonus_damage, (
                    f"🐺 **ALPHA STRIKE!** 🐺\n"
                    f"**{attacker['name']}** attacks with predator instincts!\n"
                    f"🎯 {bonus_damage} pack hunter damage!"
                )
            else:
                # Generic zoan boost
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"🦁 **BEAST TRANSFORMATION!** 🦁\n"
                    f"**{attacker['name']}** taps into their animal instincts!\n"
                    f"💪 {bonus_damage} enhanced damage!"
                )
        return 0, None

    async def _ancient_zoan_effect(self, fruit_name, attacker, defender, base_damage):
        """Ancient Zoan effects"""
        if random.random() < 0.50:
            effect = DEVIL_FRUITS["Rare"][fruit_name]["effect"]
            
            if "spinosaurus" in effect:
                bonus_damage = int(base_damage * 1.5)
                await self.status_manager.apply_effect("bleed", defender, value=2)
                return bonus_damage, (
                    f"🦖 **ANCIENT PREDATOR!** 🦖\n"
                    f"**{attacker['name']}** unleashes prehistoric fury!\n"
                    f"🩸 {bonus_damage} savage damage + bleeding!"
                )
            elif "pteranodon" in effect:
                bonus_damage = int(base_damage * 1.3)
                await self.status_manager.apply_effect("speed_boost", attacker, duration=3)
                return bonus_damage, (
                    f"🦅 **AERIAL SUPERIORITY!** 🦅\n"
                    f"**{attacker['name']}** dominates from the skies!\n"
                    f"💨 {bonus_damage} dive bomb damage + speed boost!"
                )
            elif "triceratops" in effect:
                bonus_damage = int(base_damage * 1.6)
                await self.status_manager.apply_effect("defense_boost", attacker, duration=2)
                return bonus_damage, (
                    f"🦕 **ARMORED CHARGE!** 🦕\n"
                    f"**{attacker['name']}** charges with triple horns!\n"
                    f"🛡️ {bonus_damage} piercing damage + defense boost!"
                )
            else:
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🦴 **ANCIENT POWER!** 🦴\n"
                    f"**{attacker['name']}** channels prehistoric strength!\n"
                    f"💀 {bonus_damage} ancient damage!"
                )
        return 0, None

    # UTILITY METHODS
    def _get_base_damage(self, move: Dict[str, Any]) -> int:
        """Get base damage from move"""
        move_type = MOVE_TYPES.get(move.get("type", "regular"), MOVE_TYPES["regular"])
        min_damage, max_damage = move_type["base_damage_range"]
        return (min_damage + max_damage) // 2

    def _apply_environment_bonus(self, damage: int, fruit_name: str, environment: str) -> int:
        """Apply environment bonuses to fruit effects"""
        if not damage or not environment:
            return damage
            
        env_data = ENVIRONMENTS.get(environment, {})
        boost_types = env_data.get("boost_types", [])
        multiplier = self.environment_multipliers.get(env_data.get("effect", ""), 1.0)
        
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        if not fruit_data:
            return damage
            
        fruit_effect = fruit_data.get("effect", "")
        
        # Check if fruit effect matches environment boosts
        for boost_type in boost_types:
            if boost_type in fruit_effect or boost_type == "all":
                return int(damage * multiplier)
        
        return damage

    async def _default_fruit_effect(self, fruit_name: str, attacker: Dict[str, Any], 
                                   defender: Dict[str, Any], base_damage: int) -> Tuple[int, Optional[str]]:
        """Default effect for fruits without specific implementations"""
        if random.random() < 0.30:
            bonus_damage = int(base_damage * 0.2)
            return bonus_damage, (
                f"✨ **DEVIL FRUIT POWER!** ✨\n"
                f"**{attacker['name']}** channels their {fruit_name} ability!\n"
                f"💫 {bonus_damage} enhanced damage!"
            )
        return 0, None

    # Additional specific fruit effects can be added here
    async def _magu_magu_effect(self, attacker, defender, base_damage):
        """Magu Magu no Mi - Magma Logia (Superior to fire)"""
        if random.random() < 0.55:
            bonus_damage = int(base_damage * 1.2)
            await self.status_manager.apply_effect("burn", defender, value=3)
            
            # Special: Magma superiority over fire
            if defender.get("fruit") == "Mera Mera no Mi":
                bonus_damage = int(base_damage * 2.0)
                return bonus_damage, (
                    f"🌋 **MAGMA SUPERIORITY!** 🌋\n"
                    f"**{attacker['name']}**'s magma overwhelms fire!\n"
                    f"💥 {bonus_damage} superior magma damage + 3 Burn stacks!"
                )
            
            return bonus_damage, (
                f"🌋 **METEOR VOLCANO!** 🌋\n"
                f"**{attacker['name']}** rains molten destruction!\n"
                f"💥 {bonus_damage} magma damage + intense burning!"
            )
        return 0, None

    # REMAINING LOGIA EFFECTS
    async def _suna_suna_effect(self, attacker, defender, base_damage, environment):
        """Suna Suna no Mi - Sand Logia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.1)
            
            # Special: Dessication (drain moisture)
            if random.random() < 0.35:
                drain_amount = int(defender["max_hp"] * 0.08)
                defender["hp"] = max(1, defender["hp"] - drain_amount)
                attacker["hp"] = min(attacker["max_hp"], attacker["hp"] + (drain_amount // 2))
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🏜️ **DESERT DESSICATION!** 🏜️\n"
                    f"**{attacker['name']}** drains all moisture!\n"
                    f"💧 Drained {drain_amount} HP + {bonus_damage} sand damage!"
                )
            else:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                return bonus_damage, (
                    f"🏜️ **SAND STORM!** 🏜️\n"
                    f"**{attacker['name']}** creates a blinding sandstorm!\n"
                    f"💨 {bonus_damage} sand damage + 2-turn slow!"
                )
        return 0, None

    async def _gasu_gasu_effect(self, attacker, defender, base_damage):
        """Gasu Gasu no Mi - Gas Logia"""
        if random.random() < 0.50:
            gas_type = random.choice(["poison", "explosive", "hallucinogenic"])
            
            if gas_type == "poison":
                bonus_damage = int(base_damage * 0.8)
                await self.status_manager.apply_effect("poison", defender, value=3)
                return bonus_damage, (
                    f"☠️ **TOXIC CLOUD!** ☠️\n"
                    f"**{attacker['name']}** releases deadly poison gas!\n"
                    f"💚 {bonus_damage} gas damage + 3 Poison stacks!"
                )
            elif gas_type == "explosive":
                bonus_damage = int(base_damage * 1.4)
                return bonus_damage, (
                    f"💥 **EXPLOSIVE GAS!** 💥\n"
                    f"**{attacker['name']}** ignites compressed gas!\n"
                    f"🔥 {bonus_damage} explosive damage!"
                )
            else:  # hallucinogenic
                bonus_damage = int(base_damage * 0.9)
                await self.status_manager.apply_effect("confusion", defender, duration=3)
                return bonus_damage, (
                    f"🌀 **HALLUCINOGENIC MIST!** 🌀\n"
                    f"**{attacker['name']}** clouds the enemy's mind!\n"
                    f"😵 {bonus_damage} psychic damage + 3-turn confusion!"
                )
        return 0, None

    async def _moku_moku_effect(self, attacker, defender, base_damage):
        """Moku Moku no Mi - Smoke Logia"""
        if random.random() < 0.45:
            bonus_damage = int(base_damage * 0.9)
            
            # Special: Smoke Screen (enhanced evasion)
            if random.random() < 0.4:
                await self.status_manager.apply_effect("dodge", attacker, duration=3)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"💨 **SMOKE SCREEN!** 💨\n"
                    f"**{attacker['name']}** vanishes in thick smoke!\n"
                    f"👻 {bonus_damage} smoke damage + 3-turn evasion boost!"
                )
            else:
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"💨 **SMOKY HAZE!** 💨\n"
                    f"**{attacker['name']}** blinds with smoke!\n"
                    f"😶‍🌫️ {bonus_damage} smoke damage + 2-turn confusion!"
                )
        return 0, None

    async def _numa_numa_effect(self, attacker, defender, base_damage):
        """Numa Numa no Mi - Swamp Logia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.0)
            
            # Special: Bottomless Swamp
            if random.random() < 0.35:
                await self.status_manager.apply_effect("bind", defender, duration=3)
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"🟫 **BOTTOMLESS SWAMP!** 🟫\n"
                    f"**{attacker['name']}** traps the enemy in endless bog!\n"
                    f"🕳️ {bonus_damage} swamp damage + 3-turn binding!"
                )
            else:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                return bonus_damage, (
                    f"🟫 **SWAMP GRASP!** 🟫\n"
                    f"**{attacker['name']}** drags the enemy down!\n"
                    f"🦶 {bonus_damage} bog damage + 2-turn slow!"
                )
        return 0, None

    async def _yuki_yuki_effect(self, attacker, defender, base_damage):
        """Yuki Yuki no Mi - Snow Logia"""
        if random.random() < 0.45:
            bonus_damage = int(base_damage * 0.9)
            
            # Special: Blizzard
            if random.random() < 0.35:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                await self.status_manager.apply_effect("slow", defender, duration=3)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"❄️ **ENDLESS BLIZZARD!** ❄️\n"
                    f"**{attacker['name']}** summons a devastating snowstorm!\n"
                    f"🌨️ {bonus_damage} frost damage + freeze + slow!"
                )
            else:
                await self.status_manager.apply_effect("slow", defender, duration=2)
                return bonus_damage, (
                    f"❄️ **SNOW DRIFT!** ❄️\n"
                    f"**{attacker['name']}** covers everything in snow!\n"
                    f"⛄ {bonus_damage} snow damage + 2-turn slow!"
                )
        return 0, None

    # REMAINING MYTHICAL ZOAN EFFECTS
    async def _daibutsu_effect(self, attacker, defender, base_damage):
        """Hito Hito no Mi: Model Daibutsu - Buddha"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.3)
            
            # Special: Shockwave Palm
            if random.random() < 0.4:
                await self.status_manager.apply_effect("stun", defender, duration=2)
                bonus_damage = int(base_damage * 1.6)
                return bonus_damage, (
                    f"🌟 **DIVINE SHOCKWAVE!** 🌟\n"
                    f"**{attacker['name']}** strikes with golden Buddha palm!\n"
                    f"✋ {bonus_damage} divine damage + 2-turn stun!"
                )
            else:
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                return bonus_damage, (
                    f"🌟 **BUDDHA'S PROTECTION!** 🌟\n"
                    f"**{attacker['name']}** gains enlightened defense!\n"
                    f"🛡️ {bonus_damage} holy damage + defense boost!"
                )
        return 0, None

    async def _okuchi_no_makami_effect(self, attacker, defender, base_damage):
        """Inu Inu no Mi: Model Okuchi no Makami - Wolf God"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.2)
            
            # Special: Ice Wolf Breath
            if random.random() < 0.4:
                await self.status_manager.apply_effect("freeze", defender, duration=2)
                bonus_damage = int(base_damage * 1.4)
                return bonus_damage, (
                    f"🐺 **DIVINE ICE HOWL!** 🐺\n"
                    f"**{attacker['name']}** breathes freezing wolf spirit!\n"
                    f"🌬️ {bonus_damage} divine ice damage + 2-turn freeze!"
                )
            else:
                await self.status_manager.apply_effect("speed_boost", attacker, duration=3)
                return bonus_damage, (
                    f"🐺 **WOLF GOD HUNT!** 🐺\n"
                    f"**{attacker['name']}** moves with divine predator speed!\n"
                    f"⚡ {bonus_damage} divine damage + speed boost!"
                )
        return 0, None

    async def _yamata_no_orochi_effect(self, attacker, defender, base_damage):
        """Hebi Hebi no Mi: Model Yamata no Orochi - Eight-Headed Serpent"""
        if random.random() < 0.55:
            heads = random.randint(2, 8)
            bonus_damage = int(base_damage * 0.7 * heads)
            
            # Special: All Eight Heads attack
            if random.random() < 0.25:
                bonus_damage = int(base_damage * 1.0 * 8)
                await self.status_manager.apply_effect("fear", defender, duration=3)
                return bonus_damage, (
                    f"🐍 **EIGHT-FOLD DESTRUCTION!** 🐍\n"
                    f"**{attacker['name']}** attacks with all eight serpent heads!\n"
                    f"💀 {bonus_damage} overwhelming damage + 3-turn fear!"
                )
            else:
                return bonus_damage, (
                    f"🐍 **MULTI-HEAD STRIKE!** 🐍\n"
                    f"**{attacker['name']}** attacks with {heads} serpent heads!\n"
                    f"🎯 {bonus_damage} multi-strike damage!"
                )
        return 0, None

    # SPECIAL PARAMECIA EFFECTS
    async def _mochi_effect(self, attacker, defender, base_damage):
        """Mochi Mochi no Mi - Special Paramecia"""
        if random.random() < 0.50:
            bonus_damage = int(base_damage * 1.1)
            
            # Special: Sticky Trap
            if random.random() < 0.4:
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 1.2)
                return bonus_damage, (
                    f"🍡 **MOCHI PRISON!** 🍡\n"
                    f"**{attacker['name']}** traps enemy in sticky mochi!\n"
                    f"🕸️ {bonus_damage} sticky damage + 2-turn binding!"
                )
            else:
                # Logia-like dodge
                attacker["next_dodge_chance"] = 0.6
                return bonus_damage, (
                    f"🍡 **MOCHI TRANSFORMATION!** 🍡\n"
                    f"**{attacker['name']}** becomes flowing mochi!\n"
                    f"💫 {bonus_damage} mochi damage + enhanced dodge next turn!"
                )
        return 0, None

    async def _zushi_zushi_effect(self, attacker, defender, base_damage):
        """Zushi Zushi no Mi - Gravity Paramecia"""
        if random.random() < 0.50:
            gravity_effect = random.choice(["crush", "lift", "meteors"])
            
            if gravity_effect == "crush":
                bonus_damage = int(base_damage * 1.5)
                await self.status_manager.apply_effect("stun", defender, duration=2)
                return bonus_damage, (
                    f"🌌 **GRAVITY CRUSH!** 🌌\n"
                    f"**{attacker['name']}** increases gravity tenfold!\n"
                    f"⬇️ {bonus_damage} crushing damage + 2-turn stun!"
                )
            elif gravity_effect == "lift":
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"🌌 **ZERO GRAVITY!** 🌌\n"
                    f"**{attacker['name']}** removes all gravity!\n"
                    f"⬆️ {bonus_damage} lifting damage + 2-turn confusion!"
                )
            else:  # meteors
                hits = random.randint(3, 6)
                bonus_damage = int(base_damage * 0.8 * hits)
                return bonus_damage, (
                    f"🌌 **GRAVITY METEORS!** 🌌\n"
                    f"**{attacker['name']}** pulls down space debris!\n"
                    f"☄️ {hits} meteors for {bonus_damage} total damage!"
                )
        return 0, None

    async def _hobi_hobi_effect(self, attacker, defender, base_damage):
        """Hobi Hobi no Mi - Hobby Paramecia"""
        if random.random() < 0.40:
            bonus_damage = int(base_damage * 0.8)
            
            # Special: Toy Transformation (temporary)
            if random.random() < 0.3:
                defender["toy_form"] = 3  # 3 turns as toy (reduced stats)
                await self.status_manager.apply_effect("confusion", defender, duration=3)
                bonus_damage = int(base_damage * 1.0)
                return bonus_damage, (
                    f"🧸 **TOY TRANSFORMATION!** 🧸\n"
                    f"**{attacker['name']}** temporarily turns enemy into a toy!\n"
                    f"🎭 {bonus_damage} transformation damage + 3-turn toy curse!"
                )
            else:
                await self.status_manager.apply_effect("fear", defender, duration=2)
                return bonus_damage, (
                    f"🧸 **CREEPY TOY!** 🧸\n"
                    f"**{attacker['name']}** creates unsettling toy magic!\n"
                    f"😨 {bonus_damage} eerie damage + 2-turn fear!"
                )
        return 0, None

    async def _bari_bari_effect(self, attacker, defender, base_damage):
        """Bari Bari no Mi - Barrier Paramecia"""
        if random.random() < 0.45:
            barrier_type = random.choice(["defense", "offense", "reflect"])
            
            if barrier_type == "defense":
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"🛡️ **ABSOLUTE BARRIER!** 🛡️\n"
                    f"**{attacker['name']}** creates an unbreakable shield!\n"
                    f"🔰 {bonus_damage} barrier damage + 3-turn defense boost!"
                )
            elif barrier_type == "offense":
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🛡️ **BARRIER CRASH!** 🛡️\n"
                    f"**{attacker['name']}** attacks with barrier walls!\n"
                    f"💥 {bonus_damage} crushing barrier damage!"
                )
            else:  # reflect
                attacker["reflect_next_attack"] = True
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🛡️ **MIRROR BARRIER!** 🛡️\n"
                    f"**{attacker['name']}** creates a reflecting barrier!\n"
                    f"🪞 {bonus_damage} barrier damage + next attack reflected!"
                )
        return 0, None

    # REGULAR PARAMECIA EFFECTS
    async def _bomu_bomu_effect(self, attacker, defender, base_damage):
        """Bomu Bomu no Mi - Bomb Paramecia"""
        if random.random() < 0.45:
            explosion_type = random.choice(["normal", "chain", "mega"])
            
            if explosion_type == "normal":
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"💣 **EXPLOSIVE PUNCH!** 💣\n"
                    f"**{attacker['name']}** detonates on impact!\n"
                    f"💥 {bonus_damage} explosive damage!"
                )
            elif explosion_type == "chain":
                hits = random.randint(2, 4)
                bonus_damage = int(base_damage * 0.8 * hits)
                return bonus_damage, (
                    f"💣 **CHAIN EXPLOSION!** 💣\n"
                    f"**{attacker['name']}** triggers multiple blasts!\n"
                    f"💥 {hits} explosions for {bonus_damage} total damage!"
                )
            else:  # mega
                bonus_damage = int(base_damage * 2.0)
                # Self damage from mega explosion
                self_damage = int(base_damage * 0.2)
                attacker["hp"] = max(1, attacker["hp"] - self_damage)
                return bonus_damage, (
                    f"💣 **MEGA BOMB!** 💣\n"
                    f"**{attacker['name']}** creates a massive explosion!\n"
                    f"💥 {bonus_damage} mega damage!\n"
                    f"⚠️ Explosion backlash: {self_damage} self-damage!"
                )
        return 0, None

    async def _hana_hana_effect(self, attacker, defender, base_damage):
        """Hana Hana no Mi - Flower Paramecia"""
        if random.random() < 0.50:
            bloom_type = random.choice(["limbs", "giant", "clone"])
            
            if bloom_type == "limbs":
                hits = random.randint(4, 8)
                bonus_damage = int(base_damage * 0.6 * hits)
                return bonus_damage, (
                    f"🌸 **THOUSAND FLEUR!** 🌸\n"
                    f"**{attacker['name']}** sprouts {hits} arms for a barrage!\n"
                    f"👐 {hits} arm strikes for {bonus_damage} total damage!"
                )
            elif bloom_type == "giant":
                bonus_damage = int(base_damage * 1.4)
                await self.status_manager.apply_effect("stun", defender, duration=1)
                return bonus_damage, (
                    f"🌸 **GIGANTESCO MANO!** 🌸\n"
                    f"**{attacker['name']}** blooms a giant arm!\n"
                    f"👊 {bonus_damage} giant arm damage + stun!"
                )
            else:  # clone
                bonus_damage = int(base_damage * 1.1)
                await self.status_manager.apply_effect("confusion", defender, duration=2)
                return bonus_damage, (
                    f"🌸 **DOBLE CLUTCH!** 🌸\n"
                    f"**{attacker['name']}** creates body double confusion!\n"
                    f"👥 {bonus_damage} clone damage + 2-turn confusion!"
                )
        return 0, None

    async def _supa_supa_effect(self, attacker, defender, base_damage):
        """Supa Supa no Mi - Blade Paramecia"""
        if random.random() < 0.50:
            blade_type = random.choice(["slice", "whirlwind", "spiral"])
            
            if blade_type == "slice":
                bonus_damage = int(base_damage * 1.2)
                await self.status_manager.apply_effect("bleed", defender, value=2)
                return bonus_damage, (
                    f"⚔️ **BLADE SLICE!** ⚔️\n"
                    f"**{attacker['name']}** cuts with razor-sharp limbs!\n"
                    f"🩸 {bonus_damage} cutting damage + bleeding!"
                )
            elif blade_type == "whirlwind":
                hits = random.randint(3, 5)
                bonus_damage = int(base_damage * 0.7 * hits)
                return bonus_damage, (
                    f"⚔️ **BLADE WHIRLWIND!** ⚔️\n"
                    f"**{attacker['name']}** spins in a cutting tornado!\n"
                    f"🌪️ {hits} blade strikes for {bonus_damage} total damage!"
                )
            else:  # spiral
                bonus_damage = int(base_damage * 1.5)
                return bonus_damage, (
                    f"⚔️ **SPIRAL BLADE!** ⚔️\n"
                    f"**{attacker['name']}** drills with spinning blade arms!\n"
                    f"🌀 {bonus_damage} drilling damage!"
                )
        return 0, None

    async def _doru_doru_effect(self, attacker, defender, base_damage):
        """Doru Doru no Mi - Wax Paramecia"""
        if random.random() < 0.45:
            wax_type = random.choice(["armor", "weapon", "trap"])
            
            if wax_type == "armor":
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"🕯️ **WAX ARMOR!** 🕯️\n"
                    f"**{attacker['name']}** hardens into protective wax!\n"
                    f"🛡️ {bonus_damage} wax damage + 3-turn defense boost!"
                )
            elif wax_type == "weapon":
                bonus_damage = int(base_damage * 1.3)
                return bonus_damage, (
                    f"🕯️ **WAX WEAPON!** 🕯️\n"
                    f"**{attacker['name']}** forms a hardened wax weapon!\n"
                    f"⚔️ {bonus_damage} enhanced wax damage!"
                )
            else:  # trap
                await self.status_manager.apply_effect("bind", defender, duration=2)
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🕯️ **WAX TRAP!** 🕯️\n"
                    f"**{attacker['name']}** encases enemy in hardening wax!\n"
                    f"🔒 {bonus_damage} trapping damage + 2-turn binding!"
                )
        return 0, None

    # ADDITIONAL PARAMECIA EFFECTS
    async def _kilo_kilo_effect(self, attacker, defender, base_damage):
        """Kilo Kilo no Mi - Weight Paramecia"""
        if random.random() < 0.45:
            weight_change = random.choice(["heavy", "light"])
            
            if weight_change == "heavy":
                bonus_damage = int(base_damage * 1.4)
                return bonus_damage, (
                    f"⚖️ **10,000 KILO PRESS!** ⚖️\n"
                    f"**{attacker['name']}** becomes incredibly heavy!\n"
                    f"💥 {bonus_damage} crushing weight damage!"
                )
            else:  # light
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 0.8)
                return bonus_damage, (
                    f"⚖️ **1 KILO FLOAT!** ⚖️\n"
                    f"**{attacker['name']}** becomes feather-light!\n"
                    f"💨 {bonus_damage} floating damage + speed boost!"
                )
        return 0, None

    async def _toge_toge_effect(self, attacker, defender, base_damage):
        """Toge Toge no Mi - Spike Paramecia"""
        if random.random() < 0.50:
            spike_type = random.choice(["counter", "barrage", "armor"])
            
            if spike_type == "counter":
                attacker["spike_counter"] = 3  # Next 3 attacks are countered
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🌵 **SPIKE ARMOR!** 🌵\n"
                    f"**{attacker['name']}** grows defensive spikes!\n"
                    f"⚡ {bonus_damage} spike damage + counter attacks for 3 turns!"
                )
            elif spike_type == "barrage":
                hits = random.randint(5, 10)
                bonus_damage = int(base_damage * 0.5 * hits)
                return bonus_damage, (
                    f"🌵 **SPIKE BARRAGE!** 🌵\n"
                    f"**{attacker['name']}** fires {hits} spikes!\n"
                    f"📌 {hits} spike hits for {bonus_damage} total damage!"
                )
            else:  # armor
                await self.status_manager.apply_effect("defense_boost", attacker, duration=3)
                bonus_damage = int(base_damage * 0.7)
                return bonus_damage, (
                    f"🌵 **THORN MAIL!** 🌵\n"
                    f"**{attacker['name']}** becomes a walking cactus!\n"
                    f"🛡️ {bonus_damage} thorn damage + enhanced defense!"
                )
        return 0, None

    async def _bane_bane_effect(self, attacker, defender, base_damage):
        """Bane Bane no Mi - Spring Paramecia"""
        if random.random() < 0.45:
            spring_type = random.choice(["bounce", "compress", "leap"])
            
            if spring_type == "bounce":
                # Bounce back enemy's next attack
                attacker["bounce_next_attack"] = True
                bonus_damage = int(base_damage * 0.9)
                return bonus_damage, (
                    f"🌀 **SPRING DEFENSE!** 🌀\n"
                    f"**{attacker['name']}** becomes bouncy and elastic!\n"
                    f"↩️ {bonus_damage} spring damage + next attack bounced back!"
                )
            elif spring_type == "compress":
                bonus_damage = int(base_damage * 1.6)
                return bonus_damage, (
                    f"🌀 **COMPRESSED SPRING!** 🌀\n"
                    f"**{attacker['name']}** compresses and releases with force!\n"
                    f"💥 {bonus_damage} explosive spring damage!"
                )
            else:  # leap
                await self.status_manager.apply_effect("speed_boost", attacker, duration=2)
                bonus_damage = int(base_damage * 1.1)
                return bonus_damage, (
                    f"🌀 **SPRING LEAP!** 🌀\n"
                    f"**{attacker['name']}** bounces around at high speed!\n"
                    f"⚡ {bonus_damage} spring damage + enhanced mobility!"
                )
        return 0, None

    # ADDITIONAL HELPER METHODS
    async def _check_fruit_interactions(self, attacker_fruit: str, defender_fruit: str, 
                                       base_damage: int) -> Tuple[int, Optional[str]]:
        """Check for special fruit vs fruit interactions"""
        interactions = {
            ("Magu Magu no Mi", "Mera Mera no Mi"): {
                "multiplier": 2.5,
                "message": "🌋 Magma overwhelms fire! Superior Logia dominance!"
            },
            ("Hie Hie no Mi", "Mera Mera no Mi"): {
                "multiplier": 0.8,
                "message": "❄️🔥 Ice and fire clash in elemental struggle!"
            },
            ("Yami Yami no Mi", "*"): {  # Darkness affects all fruits
                "multiplier": 1.3,
                "message": "🌑 Darkness nullifies Devil Fruit resistance!"
            },
            ("Goro Goro no Mi", "Gomu Gomu no Mi"): {
                "multiplier": 0.1,
                "message": "⚡🔴 Rubber completely negates lightning!"
            }
        }
        
        # Check specific interactions
        key = (attacker_fruit, defender_fruit)
        if key in interactions:
            interaction = interactions[key]
            bonus = int(base_damage * (interaction["multiplier"] - 1.0))
            return bonus, interaction["message"]
        
        # Check wildcard interactions
        for (attack_fruit, defend_fruit), interaction in interactions.items():
            if attack_fruit == attacker_fruit and defend_fruit == "*":
                bonus = int(base_damage * (interaction["multiplier"] - 1.0))
                return bonus, interaction["message"]
        
        return 0, None

    def _calculate_fruit_mastery_bonus(self, attacker: Dict[str, Any], fruit_name: str) -> float:
        """Calculate mastery bonus based on fruit usage"""
        battles_won = attacker.get("wins", 0)
        fruit_rarity = "Rare" if fruit_name in DEVIL_FRUITS["Rare"] else "Common"
        
        base_mastery = min(battles_won * 0.01, 0.25)  # Max 25% mastery bonus
        
        if fruit_rarity == "Rare":
            base_mastery *= 1.5  # Rare fruits have higher mastery potential
        
        return 1.0 + base_mastery

    async def _handle_awakened_abilities(self, fruit_name: str, attacker: Dict[str, Any], 
                                        defender: Dict[str, Any], base_damage: int) -> Tuple[int, Optional[str]]:
        """Handle awakened Devil Fruit abilities (for high-level players)"""
        wins = attacker.get("wins", 0)
        
        # Awakening requires significant mastery
        if wins < 100:
            return 0, None
        
        if random.random() < 0.15:  # 15% chance for awakened ability
            fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
            fruit_type = fruit_data.get("type", "")
            
            if "Logia" in fruit_type:
                # Environmental transformation
                bonus_damage = int(base_damage * 2.0)
                return bonus_damage, (
                    f"🌟 **AWAKENED LOGIA!** 🌟\n"
                    f"**{attacker['name']}** transforms the entire battlefield!\n"
                    f"🌍 {bonus_damage} environmental devastation!"
                )
            elif "Paramecia" in fruit_type:
                # Affect the opponent directly
                bonus_damage = int(base_damage * 1.8)
                await self.status_manager.apply_effect("confusion", defender, duration=3)
                return bonus_damage, (
                    f"🌟 **AWAKENED PARAMECIA!** 🌟\n"
                    f"**{attacker['name']}** affects the enemy directly!\n"
                    f"🎯 {bonus_damage} reality-altering damage + confusion!"
                )
            elif "Zoan" in fruit_type:
                # Enhanced physical abilities
                bonus_damage = int(base_damage * 1.6)
                await self.status_manager.apply_effect("attack_boost", attacker, duration=4)
                await self.status_manager.apply_effect("defense_boost", attacker, duration=4)
                return bonus_damage, (
                    f"🌟 **AWAKENED ZOAN!** 🌟\n"
                    f"**{attacker['name']}** transcends their beast form!\n"
                    f"💪 {bonus_damage} transcendent damage + enhanced stats!"
                )
        
        return 0, None
