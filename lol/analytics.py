"""
Advanced League of Legends Analytics Engine - Minimal Version

Simplified analytics with basic win probability calculations.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WinProbability:
    """Win probability calculation results"""
    blue_team_prob: float
    red_team_prob: float
    confidence: float = 50.0
    factors: Dict[str, float] = None
    game_phase_modifier: float = 0.0
    
    def __post_init__(self):
        if self.factors is None:
            self.factors = {}


@dataclass
class TeamComposition:
    """Team composition analysis results"""
    damage_distribution: Dict[str, float]
    roles_filled: List[str]
    engage_score: int
    peel_score: int
    scaling_phase: str  # "Early", "Mid", "Late"
    synergies: List[str]
    weaknesses: List[str]
    objective_control: int  # 1-10 scale
    
    def __post_init__(self):
        if not self.damage_distribution:
            self.damage_distribution = {"AD": 50, "AP": 50, "Tank": 0}
        if not self.roles_filled:
            self.roles_filled = []
        if not self.synergies:
            self.synergies = []
        if not self.weaknesses:
            self.weaknesses = []


class AdvancedAnalytics:
    """Simplified analytics engine for League of Legends data analysis"""
    
    def __init__(self):
        self.champion_data = {}
        self.meta_cache = {}
        self.win_rate_cache = {}
        
        # Basic champion data for calculations
        self._initialize_basic_data()
    
    def _initialize_basic_data(self):
        """Initialize basic champion data for analysis"""
        # Simplified champion metadata
        self.champion_meta = {
            # Format: champion_id: {"scaling": "Early/Mid/Late", "damage_type": "AD/AP/Tank", "role": "ADC/Support/etc"}
            1: {"scaling": "Mid", "damage_type": "AP", "role": "Mid"},
            22: {"scaling": "Late", "damage_type": "AD", "role": "ADC"},
            51: {"scaling": "Late", "damage_type": "AD", "role": "ADC"},
            222: {"scaling": "Late", "damage_type": "AD", "role": "ADC"},
            12: {"scaling": "Early", "damage_type": "Tank", "role": "Support"},
            40: {"scaling": "Late", "damage_type": "AP", "role": "Support"},
            412: {"scaling": "Mid", "damage_type": "Tank", "role": "Support"},
            103: {"scaling": "Mid", "damage_type": "AP", "role": "Mid"},
            157: {"scaling": "Late", "damage_type": "AD", "role": "Mid"},
            238: {"scaling": "Mid", "damage_type": "AD", "role": "Mid"},
            121: {"scaling": "Mid", "damage_type": "AD", "role": "Jungle"},
            64: {"scaling": "Early", "damage_type": "AD", "role": "Jungle"},
            54: {"scaling": "Late", "damage_type": "Tank", "role": "Top"},
            86: {"scaling": "Mid", "damage_type": "AD", "role": "Top"},
        }
    
    async def calculate_win_probability(self, game_data: Dict, historical_data: Optional[List[Dict]] = None) -> WinProbability:
        """
        Calculate simplified win probability
        
        Args:
            game_data: Live game data from Riot API
            historical_data: Optional historical match data
            
        Returns:
            WinProbability object with basic analysis
        """
        try:
            blue_team = []
            red_team = []
            
            # Organize teams
            for participant in game_data.get('participants', []):
                if participant.get('teamId') == 100:
                    blue_team.append(participant)
                else:
                    red_team.append(participant)
            
            # Basic team strength calculation
            blue_strength = self._calculate_basic_team_strength(blue_team)
            red_strength = self._calculate_basic_team_strength(red_team)
            
            # Game length modifier
            game_length = game_data.get('gameLength', 0)
            length_modifier = self._get_basic_length_modifier(blue_team, red_team, game_length)
            
            # Apply modifiers
            blue_final = blue_strength + length_modifier
            red_final = red_strength - length_modifier
            
            # Normalize to percentages
            total = blue_final + red_final
            if total <= 0:
                blue_prob = red_prob = 50.0
            else:
                blue_prob = max(15.0, min(85.0, (blue_final / total) * 100))
                red_prob = 100.0 - blue_prob
            
            return WinProbability(
                blue_team_prob=blue_prob,
                red_team_prob=red_prob,
                confidence=60.0,  # Basic confidence
                factors={
                    'blue_strength': blue_strength,
                    'red_strength': red_strength,
                    'game_phase': length_modifier
                },
                game_phase_modifier=length_modifier
            )
            
        except Exception as e:
            logger.error(f"Error calculating win probability: {e}")
            return WinProbability(
                blue_team_prob=50.0,
                red_team_prob=50.0,
                confidence=30.0
            )
    
    def _calculate_basic_team_strength(self, team: List[Dict]) -> float:
        """Calculate basic team strength"""
        if not team:
            return 50.0
        
        strength = 0.0
        for player in team:
            champion_id = player.get('championId', 0)
            
            # Basic champion strength (simplified)
            if champion_id in self.champion_meta:
                strength += 55.0  # Known champion
            else:
                strength += 50.0  # Unknown champion
        
        return strength / len(team)
    
    def _get_basic_length_modifier(self, blue_team: List[Dict], red_team: List[Dict], game_length: int) -> float:
        """Basic game length modifier"""
        if game_length == 0:
            return 0.0
        
        blue_scaling = self._get_team_scaling(blue_team)
        red_scaling = self._get_team_scaling(red_team)
        
        # Simple scaling advantage
        if game_length > 1800:  # Late game (30+ min)
            if blue_scaling == "Late" and red_scaling != "Late":
                return 5.0
            elif red_scaling == "Late" and blue_scaling != "Late":
                return -5.0
        elif game_length < 900:  # Early game (< 15 min)
            if blue_scaling == "Early" and red_scaling != "Early":
                return 3.0
            elif red_scaling == "Early" and blue_scaling != "Early":
                return -3.0
        
        return 0.0
    
    def _get_team_scaling(self, team: List[Dict]) -> str:
        """Determine team scaling preference"""
        scaling_votes = defaultdict(int)
        
        for player in team:
            champion_id = player.get('championId', 0)
            champion_meta = self.champion_meta.get(champion_id, {"scaling": "Mid"})
            scaling_votes[champion_meta["scaling"]] += 1
        
        return max(scaling_votes, key=scaling_votes.get) if scaling_votes else "Mid"
    
    async def analyze_team_composition(self, team: List[Dict]) -> TeamComposition:
        """Basic team composition analysis"""
        if not team:
            return TeamComposition(
                damage_distribution={"AD": 50, "AP": 50, "Tank": 0},
                roles_filled=[],
                engage_score=5,
                peel_score=5,
                scaling_phase="Mid",
                synergies=[],
                weaknesses=[],
                objective_control=5
            )
        
        try:
            damage_dist = {"AD": 0, "AP": 0, "Tank": 0}
            roles = []
            
            for player in team:
                champion_id = player.get('championId', 0)
                champion_meta = self.champion_meta.get(champion_id, {
                    "damage_type": "AD", 
                    "role": "Unknown"
                })
                
                # Count damage types
                damage_type = champion_meta.get("damage_type", "AD")
                damage_dist[damage_type] += 20  # Each player contributes 20%
                
                # Collect roles
                role = champion_meta.get("role", "Unknown")
                roles.append(role)
            
            # Normalize damage distribution
            total_damage = sum(damage_dist.values())
            if total_damage > 0:
                damage_dist = {k: (v / total_damage) * 100 for k, v in damage_dist.items()}
            
            # Basic analysis
            scaling_phase = self._get_team_scaling(team)
            
            # Simple scoring
            engage_score = min(10, len([r for r in roles if r in ["Support", "Jungle"]]) * 3)
            peel_score = min(10, len([r for r in roles if r in ["Support", "ADC"]]) * 2)
            objective_control = min(10, max(3, len(set(roles))))
            
            # Basic weaknesses
            weaknesses = []
            if damage_dist.get("AD", 0) > 80:
                weaknesses.append("Heavy AD team")
            if damage_dist.get("AP", 0) > 80:
                weaknesses.append("Heavy AP team")
            if engage_score < 3:
                weaknesses.append("Low engage")
            
            return TeamComposition(
                damage_distribution=damage_dist,
                roles_filled=list(set(roles)),
                engage_score=engage_score,
                peel_score=peel_score,
                scaling_phase=scaling_phase,
                synergies=[],  # Simplified - no synergy detection
                weaknesses=weaknesses,
                objective_control=objective_control
            )
            
        except Exception as e:
            logger.error(f"Error analyzing team composition: {e}")
            return TeamComposition(
                damage_distribution={"AD": 50, "AP": 50, "Tank": 0},
                roles_filled=[],
                engage_score=5,
                peel_score=5,
                scaling_phase="Mid",
                synergies=[],
                weaknesses=[],
                objective_control=5
            )
    
    def get_game_phase(self, game_length: int) -> str:
        """Determine current game phase based on length"""
        if game_length < 900:  # < 15 minutes
            return "Early Game"
        elif game_length < 1800:  # < 30 minutes
            return "Mid Game"
        else:
            return "Late Game"
    
    def get_phase_description(self, phase: str) -> str:
        """Get detailed description of game phase"""
        descriptions = {
            "Early Game": "Laning phase focus - CS and early objectives",
            "Mid Game": "Team fighting begins - objective control key",
            "Late Game": "High-stakes fights - one mistake can end the game"
        }
        return descriptions.get(phase, "Unknown phase")
    
    async def predict_objective_outcomes(self, game_data: Dict) -> Dict[str, float]:
        """Simple objective control prediction"""
        try:
            blue_team = [p for p in game_data.get('participants', []) if p.get('teamId') == 100]
            red_team = [p for p in game_data.get('participants', []) if p.get('teamId') == 200]
            
            blue_comp = await self.analyze_team_composition(blue_team)
            red_comp = await self.analyze_team_composition(red_team)
            
            # Simple calculation based on objective control scores
            blue_control = blue_comp.objective_control
            red_control = red_comp.objective_control
            
            total_control = blue_control + red_control
            if total_control == 0:
                return {"dragon": 50.0, "baron": 50.0, "elder": 50.0}
            
            blue_obj_prob = (blue_control / total_control) * 100
            
            return {
                "dragon": blue_obj_prob,
                "baron": blue_obj_prob,
                "elder": blue_obj_prob,
                "herald": blue_obj_prob
            }
            
        except Exception as e:
            logger.error(f"Error predicting objectives: {e}")
            return {"dragon": 50.0, "baron": 50.0, "elder": 50.0, "herald": 50.0}
