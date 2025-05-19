"""Battle model for the One Piece bot."""

import time
import random
from enum import Enum
from typing import Dict, List, Any, Optional
from .player import Player

class BattleState(Enum):
    """Battle states."""
    PENDING = "pending"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"

class BattlePlayer:
    """Represents a player in battle with battle-specific stats."""
    
    def __init__(self, player: Player):
        self.player = player
        self.max_hp = 100
        self.current_hp = 100
        self.mp = 100
        self.status_effects = {}
        self.move_cooldowns = {}
        self.battle_stats = {
            "damage_dealt": 0,
            "damage_taken": 0,
            "healing_done": 0,
            "critical_hits": 0,
            "moves_used": 0
        }
        self.strategy = None
    
    def take_damage(self, damage: int) -> int:
        """Take damage and return actual damage taken."""
        # Apply defense modifiers from status effects
        defense_modifier = 1.0
        for effect_name, effect_data in self.status_effects.items():
            if "damage_reduction" in effect_data:
                defense_modifier *= (1 - effect_data["damage_reduction"])
        
        actual_damage = int(damage * defense_modifier)
        actual_damage = min(actual_damage, self.current_hp)
        
        self.current_hp -= actual_damage
        self.battle_stats["damage_taken"] += actual_damage
        
        return actual_damage
    
    def heal(self, amount: int) -> int:
        """Heal HP and return actual healing done."""
        healing_modifier = 1.0
        for effect_name, effect_data in self.status_effects.items():
            if "healing_bonus" in effect_data:
                healing_modifier *= effect_data["healing_bonus"]
        
        actual_healing = int(amount * healing_modifier)
        actual_healing = min(actual_healing, self.max_hp - self.current_hp)
        
        self.current_hp += actual_healing
        self.battle_stats["healing_done"] += actual_healing
        
        return actual_healing
    
    def use_mp(self, amount: int) -> bool:
        """Use MP and return if successful."""
        if self.mp >= amount:
            self.mp -= amount
            return True
        return False
    
    def restore_mp(self, amount: int):
        """Restore MP."""
        self.mp = min(100, self.mp + amount)
    
    def apply_status_effect(self, effect_name: str, duration: int, data: Dict[str, Any] = None):
        """Apply a status effect."""
        if data is None:
            data = {}
        
        self.status_effects[effect_name] = {
            "duration": duration,
            **data
        }
    
    def remove_status_effect(self, effect_name: str):
        """Remove a status effect."""
        if effect_name in self.status_effects:
            del self.status_effects[effect_name]
    
    def process_status_effects(self):
        """Process status effects at the start of turn."""
        effects_to_remove = []
        
        for effect_name, effect_data in self.status_effects.items():
            # Process damage-over-time effects
            if effect_name in ["burn", "poison"]:
                damage = effect_data.get("value", 5)
                self.take_damage(damage)
            
            # Process healing-over-time effects
            elif effect_name in ["regen", "heal"]:
                healing = effect_data.get("value", 5)
                self.heal(healing)
            
            # Reduce duration
            effect_data["duration"] -= 1
            if effect_data["duration"] <= 0:
                effects_to_remove.append(effect_name)
        
        # Remove expired effects
        for effect_name in effects_to_remove:
            self.remove_status_effect(effect_name)
    
    def set_move_cooldown(self, move_name: str, cooldown: int):
        """Set cooldown for a move."""
        self.move_cooldowns[move_name] = cooldown
    
    def is_move_on_cooldown(self, move_name: str) -> bool:
        """Check if a move is on cooldown."""
        return self.move_cooldowns.get(move_name, 0) > 0
    
    def reduce_cooldowns(self):
        """Reduce all move cooldowns by 1."""
        for move_name in list(self.move_cooldowns.keys()):
            self.move_cooldowns[move_name] -= 1
            if self.move_cooldowns[move_name] <= 0:
                del self.move_cooldowns[move_name]
    
    @property
    def is_alive(self) -> bool:
        """Check if the player is still alive."""
        return self.current_hp > 0
    
    @property
    def hp_percentage(self) -> float:
        """Get HP as a percentage."""
        return (self.current_hp / self.max_hp * 100) if self.max_hp > 0 else 0

class Battle:
    """Represents a battle between two players."""
    
    def __init__(self, player1: Player, player2: Player, battle_id: str = None):
        self.id = battle_id or f"battle_{int(time.time())}"
        self.player1 = BattlePlayer(player1)
        self.player2 = BattlePlayer(player2)
        self.current_turn = 0
        self.turn = 0
        self.state = BattleState.PENDING
        self.winner = None
        self.loser = None
        self.surrender_player = None
        self.battle_log = []
        self.start_time = time.time()
        self.end_time = None
        self.environment = None
        self.wager = None
    
    @property
    def current_battle_player(self) -> BattlePlayer:
        """Get the current player's turn."""
        return self.player1 if self.current_turn == 0 else self.player2
    
    @property
    def opponent_battle_player(self) -> BattlePlayer:
        """Get the opponent of the current player."""
        return self.player2 if self.current_turn == 0 else self.player1
    
    def get_battle_player(self, member) -> Optional[BattlePlayer]:
        """Get BattlePlayer by Discord member."""
        if self.player1.player.member == member:
            return self.player1
        elif self.player2.player.member == member:
            return self.player2
        return None
    
    def start_battle(self):
        """Start the battle."""
        self.state = BattleState.ACTIVE
        self.add_log(f"⚔️ Battle begins! {self.player1.player.member.display_name} vs {self.player2.player.member.display_name}")
        
        # Apply environment effects if any
        if self.environment:
            self.apply_environment_effects()
    
    def next_turn(self):
        """Advance to the next turn."""
        # Process status effects for current player
        self.current_battle_player.process_status_effects()
        
        # Reduce cooldowns for both players
        self.player1.reduce_cooldowns()
        self.player2.reduce_cooldowns()
        
        # Restore some MP each turn
        self.player1.restore_mp(10)
        self.player2.restore_mp(10)
        
        # Switch turns
        self.current_turn = 1 - self.current_turn
        self.turn += 1
        
        # Check for battle end conditions
        if not self.player1.is_alive or not self.player2.is_alive:
            self.end_battle()
    
    def end_battle(self):
        """End the battle and determine winner."""
        self.state = BattleState.FINISHED
        self.end_time = time.time()
        
        # Determine winner
        if self.surrender_player:
            # Handle surrender
            if self.surrender_player == self.player1:
                self.winner = self.player2
                self.loser = self.player1
            else:
                self.winner = self.player1
                self.loser = self.player2
            self.add_log(f"🏳️ {self.surrender_player.player.member.display_name} surrendered!")
        else:
            # Determine by HP
            if self.player1.is_alive and not self.player2.is_alive:
                self.winner = self.player1
                self.loser = self.player2
            elif self.player2.is_alive and not self.player1.is_alive:
                self.winner = self.player2
                self.loser = self.player1
            else:
                # Draw or both died - determine by remaining HP
                if self.player1.current_hp > self.player2.current_hp:
                    self.winner = self.player1
                    self.loser = self.player2
                elif self.player2.current_hp > self.player1.current_hp:
                    self.winner = self.player2
                    self.loser = self.player1
                else:
                    # True draw - no winner
                    self.winner = None
                    self.loser = None
        
        if self.winner:
            self.add_log(f"🏆 {self.winner.player.member.display_name} wins the battle!")
        else:
            self.add_log("⚖️ The battle ends in a draw!")
    
    def cancel_battle(self, reason: str = "Battle cancelled"):
        """Cancel the battle."""
        self.state = BattleState.CANCELLED
        self.end_time = time.time()
        self.add_log(f"❌ {reason}")
    
    def add_log(self, message: str):
        """Add an entry to the battle log."""
        self.battle_log.append({
            "turn": self.turn,
            "message": message,
            "timestamp": time.time()
        })
    
    def apply_environment_effects(self):
        """Apply environment effects to the battle."""
        if not self.environment:
            return
        
        effects = self.environment.get("effects", {})
        
        # Apply HP modifications
        if "max_hp" in effects:
            multiplier = effects["max_hp"]
            self.player1.max_hp = int(self.player1.max_hp * multiplier)
            self.player1.current_hp = int(self.player1.current_hp * multiplier)
            self.player2.max_hp = int(self.player2.max_hp * multiplier)
            self.player2.current_hp = int(self.player2.current_hp * multiplier)
        
        # Apply MP modifications
        if "mp_bonus" in effects:
            multiplier = effects["mp_bonus"]
            self.player1.mp = int(self.player1.mp * multiplier)
            self.player2.mp = int(self.player2.mp * multiplier)
        
        self.add_log(f"🌍 Environment: {self.environment['name']} - {self.environment['description']}")
    
    @property
    def duration(self) -> float:
        """Get battle duration in seconds."""
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert battle to dictionary for storage."""
        return {
            "id": self.id,
            "player1_id": self.player1.player.member.id,
            "player2_id": self.player2.player.member.id,
            "state": self.state.value,
            "turn": self.turn,
            "current_turn": self.current_turn,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "winner_id": self.winner.player.member.id if self.winner else None,
            "loser_id": self.loser.player.member.id if self.loser else None,
            "environment": self.environment,
            "wager": self.wager,
            "battle_log": self.battle_log,
            "player1_stats": self.player1.battle_stats,
            "player2_stats": self.player2.battle_stats
        }