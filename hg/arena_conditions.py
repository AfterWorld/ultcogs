# arena_conditions.py
"""
Grand Line Arena Conditions System for One Piece themed Hunger Games
Adds dynamic weather and environmental effects that change gameplay
"""

import random
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Grand Line Conditions with effects and flavor
GRAND_LINE_CONDITIONS = {
    "calm_belt": {
        "name": "🌊 **Calm Belt**",
        "description": "Eerie stillness falls over the Grand Line - Sea Kings lurk below",
        "effects": {
            "sea_king_events": 0.40,
            "sailing_events": -0.30, 
            "devil_fruit_weakness": 0.20,
            "death_rate_modifier": 0.15
        },
        "flavor_prefix": [
            "In the deadly silence of the Calm Belt,",
            "From the depths where Sea Kings dwell,",
            "Without wind or current to aid them,"
        ],
        "announcement": "🌊 The wind dies completely... the ocean becomes unnaturally still. Sea Kings sense weakness below the surface."
    },
    
    "sea_storm": {
        "name": "⛈️ **Raging Typhoon**", 
        "description": "Massive typhoon rocks the Grand Line with lightning and crushing waves",
        "effects": {
            "drowning_events": 0.50,
            "lightning_deaths": 0.30,
            "ship_destruction": 0.40,
            "death_rate_modifier": 0.25
        },
        "flavor_prefix": [
            "Lightning illuminates the chaos as",
            "Through the raging typhoon,",
            "Amid the crashing waves,"
        ],
        "announcement": "⛈️ Storm clouds gather rapidly! Lightning splits the sky as massive waves begin to form!"
    },
    
    "devil_fruit_aura": {
        "name": "👹 **Devil Fruit Resonance**",
        "description": "Strange energy emanates from ancient Devil Fruit powers",
        "effects": {
            "power_awakening": 0.25,
            "ability_malfunction": 0.20,
            "sponsor_chance_modifier": 0.15,
            "alliance_rate": -0.10
        },
        "flavor_prefix": [
            "As Devil Fruit power surges through the air,",
            "Strange energy warps reality as",
            "With unnatural power flowing freely,"
        ],
        "announcement": "👹 The air shimmers with mysterious Devil Fruit energy! Ancient powers stir and reality bends!"
    },
    
    "marine_blockade": {
        "name": "🚢 **Marine Blockade**",
        "description": "World Government forces patrol the waters with warships",
        "effects": {
            "buster_call_events": 0.35,
            "pacifista_encounters": 0.25,
            "capture_events": 0.30,
            "survival_rate": -0.20
        },
        "flavor_prefix": [
            "Under the watchful eyes of the Marines,",
            "Despite the World Government presence,", 
            "As Marine spotlights sweep the area,"
        ],
        "announcement": "🚢 Marine warships appear on the horizon! The World Government has found this battle!"
    },
    
    "knock_up_stream": {
        "name": "🌪️ **Knock Up Stream**",
        "description": "Powerful ocean currents create chaotic water spouts",
        "effects": {
            "sky_island_events": 0.20,
            "falling_deaths": 0.40,
            "aerial_combat": 0.25,
            "environmental_hazard": 0.35
        },
        "flavor_prefix": [
            "As powerful currents surge upward,",
            "Launched high into the sky,",
            "Caught in the massive water spout,"
        ],
        "announcement": "🌪️ The ocean begins to churn violently! Massive water spouts launch ships skyward!"
    },
    
    "whirlpool_zone": {
        "name": "🌀 **Deadly Whirlpools**",
        "description": "Treacherous whirlpools and underwater currents dominate the area", 
        "effects": {
            "drowning_events": 0.45,
            "ship_collision": 0.30,
            "underwater_events": 0.35,
            "movement_restriction": 0.25
        },
        "flavor_prefix": [
            "Caught in the spinning currents,",
            "As the whirlpool drags them down,",
            "Fighting against the crushing vortex,"
        ],
        "announcement": "🌀 The ocean begins to spin! Massive whirlpools form, threatening to swallow everything!"
    },
    
    "red_line_proximity": {
        "name": "🏔️ **Red Line Cliffs**",
        "description": "The massive Red Line continent looms nearby",
        "effects": {
            "climbing_deaths": 0.40,
            "avalanche_events": 0.30,
            "celestial_dragon_events": 0.15,
            "fall_damage": 0.50
        },
        "flavor_prefix": [
            "Against the towering Red Line,",
            "High above the deadly cliffs,",
            "On the treacherous mountain face,"
        ],
        "announcement": "🏔️ The massive Red Line looms overhead! Its deadly cliffs promise certain death to the fallen!"
    },
    
    "florian_triangle": {
        "name": "👻 **Florian Triangle**",
        "description": "Mysterious fog and supernatural forces cloud the battlefield",
        "effects": {
            "ghost_events": 0.50,
            "shadow_manipulation": 0.30,
            "zombie_encounters": 0.25,
            "visibility_reduced": 0.40
        },
        "flavor_prefix": [
            "Through the supernatural fog,",
            "As ghostly figures watch,",
            "In the realm between life and death,"
        ],
        "announcement": "👻 Thick fog rolls in from the Florian Triangle! Ghostly voices whisper from the shadows!"
    },
    
    "new_world_chaos": {
        "name": "🔥 **New World Storm**",
        "description": "The unpredictable weather of the New World strikes",
        "effects": {
            "yonko_interference": 0.20,
            "haki_storms": 0.35,
            "island_destruction": 0.40,
            "chaos_multiplier": 0.30
        },
        "flavor_prefix": [
            "In the chaotic New World,",
            "As Yonko-level power clashes,",
            "Through the impossible weather,"
        ],
        "announcement": "🔥 The New World shows its fury! Impossible weather and raw Haki energy tear through the area!"
    },
    
    "ancient_weapon_energy": {
        "name": "⚡ **Ancient Power**",
        "description": "Residual energy from Ancient Weapons affects the area",
        "effects": {
            "mass_destruction": 0.60,
            "pluton_cannon": 0.25,
            "poseidon_summon": 0.20,
            "devastation_multiplier": 0.50
        },
        "flavor_prefix": [
            "As ancient power awakens,",
            "With world-ending force,",
            "Through the power of forgotten ages,"
        ],
        "announcement": "⚡ Ancient weapon energy stirs! The very foundations of the world tremble with forgotten power!"
    }
}

# Condition-specific death events that replace normal ones
CONDITION_DEATH_EVENTS = {
    "calm_belt": [
        "💀 | **{killer}** pushed ~~**{player}**~~ into the Calm Belt where massive Sea Kings devoured them instantly!",
        "💀 | ~~**{player}**~~ fell overboard in the Calm Belt and sank like a stone with their Devil Fruit powers!",
        "💀 | **{killer}** watched helplessly as a colossal Sea King swallowed ~~**{player}**~~ whole!",
        "💀 | ~~**{player}**~~ was dragged into the depths by something enormous lurking in the still waters!",
    ],
    
    "sea_storm": [
        "💀 | **{killer}** used the lightning storm to electrocute ~~**{player}**~~ with a metal weapon!",
        "💀 | ~~**{player}**~~ was struck by lightning while trying to escape **{killer}**!",
        "💀 | **{killer}** threw ~~**{player}**~~ overboard into the crushing waves during the typhoon!",
        "💀 | ~~**{player}**~~ was swept away by a massive wave while fighting **{killer}**!",
    ],
    
    "marine_blockade": [
        "💀 | **{killer}** alerted the Marines to ~~**{player}**~~'s location and watched them get executed!",
        "💀 | ~~**{player}**~~ was caught in Marine crossfire while fighting **{killer}**!",
        "💀 | **{killer}** used a Marine Pacifista to obliterate ~~**{player}**~~!",
        "💀 | ~~**{player}**~~ was captured by Marines and sent to Impel Down to rot!",
    ],
    
    "knock_up_stream": [
        "💀 | **{killer}** launched ~~**{player}**~~ high into the sky where they fell to their death!",
        "💀 | ~~**{player}**~~ was caught in a massive water spout and slammed into the ocean floor!",
        "💀 | **{killer}** used the chaotic currents to drown ~~**{player}**~~ in the churning water!",
        "💀 | ~~**{player}**~~ was crushed by falling debris launched by the Knock Up Stream!",
    ],
    
    "whirlpool_zone": [
        "💀 | **{killer}** kicked ~~**{player}**~~ into a deadly whirlpool where they were sucked under!",
        "💀 | ~~**{player}**~~ was caught in spinning currents and drowned despite **{killer}**'s attack!",
        "💀 | **{killer}** used the whirlpool's force to slam ~~**{player}**~~ into underwater rocks!",
        "💀 | ~~**{player}**~~ got trapped in a vortex and was pulled down into the abyss!",
    ],
    
    "florian_triangle": [
        "💀 | **{killer}** used the supernatural fog to sneak up and eliminate ~~**{player}**~~!",
        "💀 | ~~**{player}**~~ was consumed by ghostly shadows while **{killer}** watched in horror!",
        "💀 | **{killer}** turned ~~**{player}**~~ into a zombie using the Triangle's dark power!",
        "💀 | ~~**{player}**~~ was lost forever in the supernatural mist of the Florian Triangle!",
    ]
}

# Environmental events that can happen based on conditions
CONDITION_ENVIRONMENTAL_EVENTS = {
    "calm_belt": [
        "🐙 A massive Sea King surfaces briefly, its eyes scanning for prey, before disappearing!",
        "🌊 The unnatural stillness makes every sound echo across the water...",
        "⚓ Ships drift helplessly without wind, making them sitting targets!",
    ],
    
    "sea_storm": [
        "⚡ Lightning strikes the water dangerously close to the remaining pirates!",
        "🌊 A massive wave crashes over the battlefield, scattering supplies!",
        "💨 Hurricane-force winds make sailing and fighting nearly impossible!",
    ],
    
    "marine_blockade": [
        "📢 Marine loudspeakers demand immediate surrender from all pirates!",
        "🚁 Marine surveillance helicopters circle overhead with spotlights!",
        "💣 Warning shots from Marine cannons remind pirates of their presence!",
    ]
}


class ArenaConditionManager:
    """Manages Grand Line conditions and their effects on gameplay"""
    
    def __init__(self):
        self.current_condition = None
        self.condition_duration = 0
        self.condition_effects = {}
    
    def select_condition(self, game_round: int, alive_count: int, force_condition: str = None) -> str:
        """Select appropriate condition based on game state"""
        try:
            if force_condition and force_condition in GRAND_LINE_CONDITIONS:
                self.current_condition = force_condition
                logger.info(f"Forced condition: {force_condition}")
                return force_condition
            
            # Early game conditions (rounds 1-5) - More common/basic
            if game_round <= 5:
                early_conditions = ["sea_storm", "whirlpool_zone", "knock_up_stream", "marine_blockade"]
                weights = [0.3, 0.3, 0.2, 0.2]
            
            # Mid game conditions (rounds 6-15) - Supernatural elements
            elif game_round <= 15:
                mid_conditions = ["devil_fruit_aura", "florian_triangle", "red_line_proximity", "calm_belt"]
                weights = [0.3, 0.25, 0.25, 0.2]
            
            # End game conditions (final 5 players) - Most dramatic
            elif alive_count <= 5:
                end_conditions = ["new_world_chaos", "ancient_weapon_energy", "devil_fruit_aura"]
                weights = [0.4, 0.35, 0.25]
            
            # Default selection for other cases
            else:
                all_conditions = list(GRAND_LINE_CONDITIONS.keys())
                condition = random.choice(all_conditions)
                self.current_condition = condition
                return condition
            
            # Select based on weights for each phase
            if game_round <= 5:
                condition = random.choices(early_conditions, weights=weights)[0]
            elif game_round <= 15:
                condition = random.choices(mid_conditions, weights=weights)[0]
            else:
                condition = random.choices(end_conditions, weights=weights)[0]
            
            self.current_condition = condition
            self.condition_effects = GRAND_LINE_CONDITIONS[condition]["effects"]
            self.condition_duration = random.randint(3, 6)  # Lasts 3-6 rounds
            
            logger.info(f"Selected arena condition: {condition} for {self.condition_duration} rounds")
            return condition
            
        except Exception as e:
            logger.error(f"Error selecting arena condition: {e}")
            # Fallback to a safe default
            self.current_condition = "sea_storm"
            return "sea_storm"
    
    def get_condition_announcement(self, condition: str = None) -> str:
        """Get the dramatic announcement for a condition"""
        try:
            condition = condition or self.current_condition
            if condition and condition in GRAND_LINE_CONDITIONS:
                return GRAND_LINE_CONDITIONS[condition]["announcement"]
            return "🌊 The Grand Line shows its unpredictable nature!"
        except Exception as e:
            logger.error(f"Error getting condition announcement: {e}")
            return "🌊 Strange weather affects the battlefield!"
    
    def apply_condition_to_event_weights(self, base_weights: Dict[str, int]) -> Dict[str, int]:
        """Modify event weights based on current condition"""
        try:
            if not self.current_condition or not self.condition_effects:
                return base_weights
            
            modified_weights = base_weights.copy()
            
            # Apply death rate modifiers
            if "death_rate_modifier" in self.condition_effects:
                death_modifier = self.condition_effects["death_rate_modifier"]
                modified_weights["death"] = int(modified_weights["death"] * (1 + death_modifier))
            
            # Apply sponsor chance modifiers  
            if "sponsor_chance_modifier" in self.condition_effects:
                sponsor_modifier = self.condition_effects["sponsor_chance_modifier"]
                modified_weights["sponsor"] = int(modified_weights["sponsor"] * (1 + sponsor_modifier))
            
            # Apply alliance rate modifiers
            if "alliance_rate" in self.condition_effects:
                alliance_modifier = self.condition_effects["alliance_rate"]
                modified_weights["alliance"] = max(5, int(modified_weights["alliance"] * (1 + alliance_modifier)))
            
            # Normalize weights to ensure they're still reasonable
            total_weight = sum(modified_weights.values())
            if total_weight <= 0:
                return base_weights
            
            logger.debug(f"Applied condition effects to weights: {modified_weights}")
            return modified_weights
            
        except Exception as e:
            logger.error(f"Error applying condition to weights: {e}")
            return base_weights
    
    def get_condition_death_events(self) -> List[str]:
        """Get condition-specific death events"""
        try:
            if self.current_condition and self.current_condition in CONDITION_DEATH_EVENTS:
                return CONDITION_DEATH_EVENTS[self.current_condition]
            return []
        except Exception as e:
            logger.error(f"Error getting condition death events: {e}")
            return []
    
    def apply_flavor_to_message(self, message: str) -> str:
        """Add condition-specific flavor to event messages"""
        try:
            if not self.current_condition:
                return message
            
            condition_data = GRAND_LINE_CONDITIONS.get(self.current_condition, {})
            flavor_prefixes = condition_data.get("flavor_prefix", [])
            
            if flavor_prefixes and random.random() < 0.6:  # 60% chance to apply flavor
                prefix = random.choice(flavor_prefixes)
                # Make the original message lowercase and merge
                return f"{prefix} {message[0].lower() + message[1:]}"
            
            return message
        except Exception as e:
            logger.error(f"Error applying flavor to message: {e}")
            return message
    
    def get_environmental_event(self) -> Optional[str]:
        """Get a random environmental event for current condition"""
        try:
            if (self.current_condition and 
                self.current_condition in CONDITION_ENVIRONMENTAL_EVENTS and
                random.random() < 0.3):  # 30% chance
                
                events = CONDITION_ENVIRONMENTAL_EVENTS[self.current_condition]
                return random.choice(events)
            return None
        except Exception as e:
            logger.error(f"Error getting environmental event: {e}")
            return None
    
    def update_condition_duration(self) -> bool:
        """Update condition duration, return True if condition should change"""
        try:
            if self.condition_duration > 0:
                self.condition_duration -= 1
                if self.condition_duration <= 0:
                    logger.info(f"Condition {self.current_condition} duration ended")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating condition duration: {e}")
            return False
    
    def get_current_condition_info(self) -> Dict:
        """Get current condition information for display"""
        try:
            if not self.current_condition:
                return {}
            
            condition_data = GRAND_LINE_CONDITIONS.get(self.current_condition, {})
            return {
                "name": condition_data.get("name", "Unknown"),
                "description": condition_data.get("description", ""),
                "duration": self.condition_duration,
                "effects": self.condition_effects
            }
        except Exception as e:
            logger.error(f"Error getting condition info: {e}")
            return {}
    
    def clear_condition(self):
        """Clear current condition"""
        self.current_condition = None
        self.condition_duration = 0
        self.condition_effects = {}
        logger.info("Arena condition cleared")


# Global instance for easy importing
arena_condition_manager = ArenaConditionManager()
