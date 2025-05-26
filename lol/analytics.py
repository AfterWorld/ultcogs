"""
Advanced League of Legends Analytics Engine

Provides real-time game analysis, win probability calculations,
team composition analysis, and performance predictions.
"""

import asyncio
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter


@dataclass
class ChampionData:
    """Champion information and meta statistics"""
    id: int
    name: str
    role: str
    win_rate: float
    pick_rate: float
    ban_rate: float
    difficulty: int
    damage_type: str  # "AD", "AP", "Mixed"
    scaling: str      # "Early", "Mid", "Late"
    engage_potential: int  # 1-10 scale
    peel_potential: int    # 1-10 scale


@dataclass
class TeamComposition:
    """Team composition analysis results"""
    damage_distribution: Dict[str, float]  # AD, AP, True damage %
    roles_filled: List[str]
    engage_score: int
    peel_score: int
    scaling_phase: str  # "Early", "Mid", "Late"
    synergies: List[str]
    weaknesses: List[str]
    objective_control: int  # 1-10 scale


@dataclass
class WinProbability:
    """Win probability calculation results"""
    blue_team_prob: float
    red_team_prob: float
    confidence: float
    factors: Dict[str, float]
    game_phase_modifier: float


class AdvancedAnalytics:
    """Main analytics engine for League of Legends data analysis"""
    
    def __init__(self):
        self.champion_data = {}
        self.meta_cache = {}
        self.win_rate_cache = {}
        self.synergy_matrix = {}
        self.counter_matrix = {}
        
        # Initialize champion meta data
        self._initialize_champion_data()
        self._initialize_synergy_data()
    
    def _initialize_champion_data(self):
        """Initialize champion metadata for analysis"""
        # This would typically be loaded from data files or API
        # Simplified version with key champions
        self.champion_data = {
            # ADC Champions
            1: ChampionData(1, "Annie", "Mid", 52.1, 3.2, 5.1, 6, "AP", "Mid", 7, 4),
            22: ChampionData(22, "Ashe", "ADC", 51.8, 12.5, 8.2, 4, "AD", "Late", 6, 5),
            51: ChampionData(51, "Caitlyn", "ADC", 50.2, 15.8, 12.1, 6, "AD", "Late", 4, 3),
            119: ChampionData(119, "Draven", "ADC", 49.8, 8.1, 15.5, 9, "AD", "Early", 5, 2),
            222: ChampionData(222, "Jinx", "ADC", 52.7, 18.2, 22.3, 6, "AD", "Late", 3, 2),
            
            # Support Champions
            12: ChampionData(12, "Alistar", "Support", 51.2, 8.5, 12.1, 7, "Tank", "Early", 9, 8),
            40: ChampionData(40, "Janna", "Support", 52.8, 7.2, 6.8, 5, "AP", "Late", 3, 9),
            412: ChampionData(412, "Thresh", "Support", 48.9, 15.2, 35.1, 8, "Tank", "Mid", 8, 7),
            267: ChampionData(267, "Nami", "Support", 53.1, 12.8, 8.5, 6, "AP", "Mid", 5, 8),
            
            # Mid Champions
            103: ChampionData(103, "Ahri", "Mid", 51.5, 8.9, 12.2, 5, "AP", "Mid", 6, 5),
            7: ChampionData(7, "LeBlanc", "Mid", 47.8, 5.2, 18.5, 9, "AP", "Early", 8, 3),
            157: ChampionData(157, "Yasuo", "Mid", 49.2, 12.5, 45.8, 8, "AD", "Late", 7, 4),
            238: ChampionData(238, "Zed", "Mid", 48.5, 9.8, 32.1, 8, "AD", "Mid", 8, 2),
            
            # Jungle Champions
            121: ChampionData(121, "Kha'Zix", "Jungle", 51.2, 8.5, 15.2, 6, "AD", "Mid", 7, 3),
            64: ChampionData(64, "Lee Sin", "Jungle", 47.8, 12.1, 25.8, 9, "AD", "Early", 9, 4),
            104: ChampionData(104, "Graves", "Jungle", 52.1, 15.2, 18.5, 6, "AD", "Mid", 6, 4),
            
            # Top Champions
            54: ChampionData(54, "Malphite", "Top", 53.2, 8.5, 12.1, 2, "Tank", "Late", 9, 6),
            86: ChampionData(86, "Garen", "Top", 52.8, 12.5, 8.2, 3, "AD", "Mid", 6, 5),
            17: ChampionData(17, "Teemo", "Top", 51.2, 6.8, 25.1, 4, "AP", "Late", 2, 3),
        }
    
    def _initialize_synergy_data(self):
        """Initialize champion synergy and counter matrices"""
        # Simplified synergy matrix (champion_id: [synergistic_champions])
        self.synergy_matrix = {
            157: [54],  # Yasuo + Malphite (The Wombo Combo)
            222: [412], # Jinx + Thresh
            22: [267],  # Ashe + Nami
            103: [121], # Ahri + Kha'Zix
        }
        
        # Counter matrix (champion_id: [countered_by])
        self.counter_matrix = {
            157: [54, 12],  # Yasuo countered by Malphite, Alistar
            222: [121, 7], # Jinx countered by Kha'Zix, LeBlanc
            238: [54, 12], # Zed countered by Malphite, Alistar
        }
    
    async def calculate_win_probability(self, game_data: Dict, historical_data: Optional[List[Dict]] = None) -> WinProbability:
        """
        Calculate real-time win probability based on multiple factors
        
        Args:
            game_data: Live game data from Riot API
            historical_data: Optional historical match data for players
            
        Returns:
            WinProbability object with detailed analysis
        """
        blue_team = []
        red_team = []
        
        # Organize teams
        for participant in game_data.get('participants', []):
            if participant.get('teamId') == 100:
                blue_team.append(participant)
            else:
                red_team.append(participant)
        
        # Calculate team strengths
        blue_factors = await self._calculate_team_strength(blue_team, historical_data)
        red_factors = await self._calculate_team_strength(red_team, historical_data)
        
        # Game length modifier
        game_length = game_data.get('gameLength', 0)
        length_modifier = self._calculate_length_modifier(blue_team, red_team, game_length)
        
        # Champion synergy/counter analysis
        blue_synergy = self._calculate_team_synergy(blue_team)
        red_synergy = self._calculate_team_synergy(red_team)
        
        # Meta strength analysis
        blue_meta = self._calculate_meta_strength(blue_team)
        red_meta = self._calculate_meta_strength(red_team)
        
        # Final calculations
        blue_score = (blue_factors['skill'] * 0.4 + 
                     blue_factors['champion'] * 0.3 + 
                     blue_synergy * 0.15 + 
                     blue_meta * 0.15 + 
                     length_modifier)
        
        red_score = (red_factors['skill'] * 0.4 + 
                    red_factors['champion'] * 0.3 + 
                    red_synergy * 0.15 + 
                    red_meta * 0.15 - 
                    length_modifier)
        
        # Normalize to percentages
        total_score = blue_score + red_score
        if total_score <= 0:
            blue_prob = red_prob = 50.0
        else:
            blue_prob = max(5.0, min(95.0, (blue_score / total_score) * 100))
            red_prob = 100.0 - blue_prob
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(blue_team, red_team, historical_data)
        
        return WinProbability(
            blue_team_prob=blue_prob,
            red_team_prob=red_prob,
            confidence=confidence,
            factors={
                'blue_skill': blue_factors['skill'],
                'red_skill': red_factors['skill'],
                'blue_champions': blue_factors['champion'],
                'red_champions': red_factors['champion'],
                'blue_synergy': blue_synergy,
                'red_synergy': red_synergy,
                'game_phase': length_modifier
            },
            game_phase_modifier=length_modifier
        )
    
    async def _calculate_team_strength(self, team: List[Dict], historical_data: Optional[List[Dict]] = None) -> Dict[str, float]:
        """Calculate overall team strength from multiple factors"""
        if not team:
            return {'skill': 0.0, 'champion': 0.0}
        
        skill_total = 0.0
        champion_total = 0.0
        
        for player in team:
            # Player skill factor (from rank or historical performance)
            skill_factor = await self._get_player_skill_factor(player, historical_data)
            skill_total += skill_factor
            
            # Champion strength factor
            champion_id = player.get('championId', 0)
            champion_factor = self._get_champion_strength_factor(champion_id)
            champion_total += champion_factor
        
        return {
            'skill': skill_total / len(team),
            'champion': champion_total / len(team)
        }
    
    async def _get_player_skill_factor(self, player: Dict, historical_data: Optional[List[Dict]] = None) -> float:
        """Convert player skill metrics to numerical factor (0-100)"""
        # Base factor
        factor = 50.0
        
        # If we have rank information
        if 'tier' in player and 'rank' in player:
            tier_values = {
                'IRON': 10, 'BRONZE': 20, 'SILVER': 30, 'GOLD': 40,
                'PLATINUM': 50, 'EMERALD': 60, 'DIAMOND': 70,
                'MASTER': 80, 'GRANDMASTER': 85, 'CHALLENGER': 95
            }
            rank_values = {'IV': 0, 'III': 2, 'II': 4, 'I': 6}
            
            tier = player.get('tier', 'GOLD')
            rank = player.get('rank', 'II')
            
            factor = tier_values.get(tier, 40) + rank_values.get(rank, 2)
        
        # If we have historical performance data
        if historical_data:
            # Analyze recent performance, KDA, win rate, etc.
            recent_performance = self._analyze_recent_performance(player, historical_data)
            factor = (factor + recent_performance) / 2
        
        return max(10.0, min(100.0, factor))
    
    def _get_champion_strength_factor(self, champion_id: int) -> float:
        """Get champion meta strength factor"""
        champion = self.champion_data.get(champion_id)
        if not champion:
            return 50.0  # Default neutral strength
        
        # Base on win rate and pick rate
        base_strength = champion.win_rate
        
        # Adjust for pick rate (popular champions are often strong)
        if champion.pick_rate > 15:  # High pick rate
            base_strength += 2
        elif champion.pick_rate < 5:  # Low pick rate might indicate weakness
            base_strength -= 1
        
        # Adjust for ban rate (heavily banned champions are usually strong)
        if champion.ban_rate > 30:  # Highly banned
            base_strength += 3
        elif champion.ban_rate > 15:  # Moderately banned
            base_strength += 1
        
        return max(30.0, min(70.0, base_strength))
    
    def _calculate_length_modifier(self, blue_team: List[Dict], red_team: List[Dict], game_length: int) -> float:
        """Calculate game length advantage modifier"""
        if game_length == 0:
            return 0.0
        
        blue_scaling = self._get_team_scaling(blue_team)
        red_scaling = self._get_team_scaling(red_team)
        
        # Early game (0-15 min): favor early game champions
        if game_length < 900:
            if blue_scaling == "Early" and red_scaling != "Early":
                return 5.0
            elif red_scaling == "Early" and blue_scaling != "Early":
                return -5.0
        
        # Mid game (15-25 min): neutral
        elif game_length < 1500:
            if blue_scaling == "Mid" and red_scaling != "Mid":
                return 2.0
            elif red_scaling == "Mid" and blue_scaling != "Mid":
                return -2.0
        
        # Late game (25+ min): favor late game champions
        else:
            if blue_scaling == "Late" and red_scaling != "Late":
                return 7.0
            elif red_scaling == "Late" and blue_scaling != "Late":
                return -7.0
        
        return 0.0
    
    def _get_team_scaling(self, team: List[Dict]) -> str:
        """Determine team's overall scaling preference"""
        scaling_votes = defaultdict(int)
        
        for player in team:
            champion_id = player.get('championId', 0)
            champion = self.champion_data.get(champion_id)
            if champion:
                scaling_votes[champion.scaling] += 1
        
        return max(scaling_votes, key=scaling_votes.get) if scaling_votes else "Mid"
    
    def _calculate_team_synergy(self, team: List[Dict]) -> float:
        """Calculate team synergy score based on champion combinations"""
        synergy_score = 0.0
        champion_ids = [p.get('championId', 0) for p in team]
        
        # Check for known synergies
        for champ_id in champion_ids:
            synergistic_champions = self.synergy_matrix.get(champ_id, [])
            for synergy_partner in synergistic_champions:
                if synergy_partner in champion_ids:
                    synergy_score += 10.0  # Strong synergy bonus
        
        # Check for role balance
        roles = []
        for player in team:
            champion_id = player.get('championId', 0)
            champion = self.champion_data.get(champion_id)
            if champion:
                roles.append(champion.role)
        
        role_balance = len(set(roles))
        if role_balance >= 4:  # Good role diversity
            synergy_score += 5.0
        elif role_balance <= 2:  # Poor role diversity
            synergy_score -= 5.0
        
        return max(0.0, min(20.0, synergy_score))
    
    def _calculate_meta_strength(self, team: List[Dict]) -> float:
        """Calculate team's current meta strength"""
        meta_score = 0.0
        
        for player in team:
            champion_id = player.get('championId', 0)
            champion = self.champion_data.get(champion_id)
            if champion:
                # High win rate and pick rate = meta champion
                if champion.win_rate > 52 and champion.pick_rate > 10:
                    meta_score += 2.0
                elif champion.win_rate < 48 or champion.ban_rate > 40:
                    meta_score -= 1.0
        
        return max(-10.0, min(10.0, meta_score))
    
    def _calculate_confidence(self, blue_team: List[Dict], red_team: List[Dict], historical_data: Optional[List[Dict]]) -> float:
        """Calculate prediction confidence based on available data"""
        confidence = 50.0  # Base confidence
        
        # More data = higher confidence
        if historical_data:
            confidence += 20.0
        
        # Known champions = higher confidence
        known_champions = sum(1 for p in blue_team + red_team 
                            if p.get('championId', 0) in self.champion_data)
        confidence += (known_champions / len(blue_team + red_team)) * 20.0
        
        # Rank information = higher confidence
        ranked_players = sum(1 for p in blue_team + red_team 
                           if 'tier' in p and 'rank' in p)
        if ranked_players > 0:
            confidence += (ranked_players / len(blue_team + red_team)) * 10.0
        
        return max(30.0, min(95.0, confidence))
    
    async def analyze_team_composition(self, team: List[Dict]) -> TeamComposition:
        """Perform comprehensive team composition analysis"""
        if not team:
            return TeamComposition({}, [], 0, 0, "Mid", [], [], 0)
        
        damage_dist = {"AD": 0, "AP": 0, "Tank": 0}
        roles = []
        engage_total = 0
        peel_total = 0
        scaling_votes = defaultdict(int)
        synergies = []
        weaknesses = []
        
        champion_ids = [p.get('championId', 0) for p in team]
        
        for player in team:
            champion_id = player.get('championId', 0)
            champion = self.champion_data.get(champion_id)
            
            if champion:
                # Damage distribution
                if champion.damage_type == "AD":
                    damage_dist["AD"] += 20
                elif champion.damage_type == "AP":
                    damage_dist["AP"] += 20
                else:  # Tank/Mixed
                    damage_dist["Tank"] += 20
                
                roles.append(champion.role)
                engage_total += champion.engage_potential
                peel_total += champion.peel_potential
                scaling_votes[champion.scaling] += 1
        
        # Normalize damage distribution
        total_damage = sum(damage_dist.values())
        if total_damage > 0:
            damage_dist = {k: (v / total_damage) * 100 for k, v in damage_dist.items()}
        
        # Determine overall scaling
        scaling_phase = max(scaling_votes, key=scaling_votes.get) if scaling_votes else "Mid"
        
        # Identify synergies
        for champ_id in champion_ids:
            synergistic_champions = self.synergy_matrix.get(champ_id, [])
            for partner in synergistic_champions:
                if partner in champion_ids:
                    partner_name = self.champion_data.get(partner, {}).get('name', f'Champion {partner}')
                    champ_name = self.champion_data.get(champ_id, {}).get('name', f'Champion {champ_id}')
                    synergies.append(f"{champ_name} + {partner_name}")
        
        # Identify weaknesses
        if damage_dist["AD"] > 80:
            weaknesses.append("Heavy AD team - vulnerable to armor")
        if damage_dist["AP"] > 80:
            weaknesses.append("Heavy AP team - vulnerable to magic resist")
        if engage_total < 15:
            weaknesses.append("Low engage potential")
        if peel_total < 15:
            weaknesses.append("Poor protection for carries")
        
        # Calculate objective control
        tank_count = sum(1 for role in roles if role in ["Support", "Jungle"] 
                        and any(self.champion_data.get(p.get('championId', 0), {}).get('damage_type') == "Tank" 
                               for p in team))
        objective_control = min(10, max(1, tank_count * 3 + engage_total // 5))
        
        return TeamComposition(
            damage_distribution=damage_dist,
            roles_filled=list(set(roles)),
            engage_score=min(10, engage_total // len(team)) if team else 0,
            peel_score=min(10, peel_total // len(team)) if team else 0,
            scaling_phase=scaling_phase,
            synergies=synergies,
            weaknesses=weaknesses,
            objective_control=objective_control
        )
    
    def _analyze_recent_performance(self, player: Dict, historical_data: List[Dict]) -> float:
        """Analyze player's recent performance from historical data"""
        # This would analyze KDA, win rate, damage dealt, etc.
        # Simplified implementation returns neutral value
        return 50.0
    
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
            "Early Game": "Laning phase focus - CS advantage and first objectives are crucial",
            "Mid Game": "Team fighting begins - objective control and positioning key",
            "Late Game": "High-stakes engagements - one team fight can decide the game"
        }
        return descriptions.get(phase, "Unknown phase")
    
    async def predict_objective_outcomes(self, game_data: Dict) -> Dict[str, float]:
        """Predict likelihood of objective captures"""
        # Analyze team compositions for objective control
        blue_team = [p for p in game_data.get('participants', []) if p.get('teamId') == 100]
        red_team = [p for p in game_data.get('participants', []) if p.get('teamId') == 200]
        
        blue_comp = await self.analyze_team_composition(blue_team)
        red_comp = await self.analyze_team_composition(red_team)
        
        # Calculate objective control differential
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
