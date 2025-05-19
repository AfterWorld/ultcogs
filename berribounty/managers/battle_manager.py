# berribounty/managers/battle_manager.py
"""Battle management for the One Piece bot."""

import asyncio
import random  # Add this missing import
from typing import Dict, List, Optional
import discord
from ..models.battle import Battle, BattleState
from ..models.player import Player
from ..constants.environments import BATTLE_ENVIRONMENTS

class BattleManager:
    """Manages battles and battle-related operations."""
    
    def __init__(self, config, player_manager):
        self.config = config
        self.player_manager = player_manager
        self.active_battles: Dict[str, Battle] = {}
        self.pending_challenges: Dict[int, Dict] = {}
    
    async def create_challenge(self, challenger: discord.Member, opponent: discord.Member, 
                             wager: int = 0, message: str = "") -> bool:
        """Create a battle challenge."""
        challenge_data = {
            "challenger": challenger,
            "opponent": opponent,
            "wager": wager,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        self.pending_challenges[opponent.id] = challenge_data
        
        # Auto-remove challenge after 60 seconds
        asyncio.create_task(self._remove_challenge_after_timeout(opponent.id, 60))
        
        return True
    
    async def _remove_challenge_after_timeout(self, opponent_id: int, timeout: int):
        """Remove a challenge after timeout."""
        await asyncio.sleep(timeout)
        if opponent_id in self.pending_challenges:
            del self.pending_challenges[opponent_id]
    
    async def accept_challenge(self, opponent: discord.Member) -> Optional[Battle]:
        """Accept a pending challenge."""
        if opponent.id not in self.pending_challenges:
            return None
        
        challenge = self.pending_challenges[opponent.id]
        challenger = challenge["challenger"]
        
        # Remove the challenge
        del self.pending_challenges[opponent.id]
        
        # Create the battle
        return await self.create_battle(challenger, opponent, challenge.get("wager", 0))
    
    async def create_battle(self, player1: discord.Member, player2: discord.Member, 
                          wager: int = 0) -> Optional[Battle]:
        """Create a new battle between two players."""
        # Get player objects
        player1_obj = await self.player_manager.get_or_create_player(player1)
        player2_obj = await self.player_manager.get_or_create_player(player2)
        
        # Check if either player is already in battle
        if await self.is_in_battle(player1_obj) or await self.is_in_battle(player2_obj):
            return None
        
        # Create battle
        battle = Battle(player1_obj, player2_obj)
        battle.wager = wager
        
        # Select random environment
        environment_names = list(BATTLE_ENVIRONMENTS.keys())
        if environment_names:
            env_name = random.choice(environment_names)
            battle.environment = BATTLE_ENVIRONMENTS[env_name]
        
        # Start the battle
        battle.start_battle()
        
        # Store in active battles
        self.active_battles[battle.id] = battle
        
        return battle
    
    async def is_in_battle(self, player: Player) -> bool:
        """Check if a player is currently in a battle."""
        for battle in self.active_battles.values():
            if (battle.player1.player.member == player.member or 
                battle.player2.player.member == player.member):
                if battle.state == BattleState.ACTIVE:
                    return True
        return False
    
    async def get_player_battle(self, player: Player) -> Optional[Battle]:
        """Get the battle a player is currently in."""
        for battle in self.active_battles.values():
            if (battle.player1.player.member == player.member or 
                battle.player2.player.member == player.member):
                if battle.state == BattleState.ACTIVE:
                    return battle
        return None
    
    async def has_pending_challenge(self, player: Player) -> bool:
        """Check if a player has a pending challenge."""
        return player.member.id in self.pending_challenges
    
    async def cancel_challenge(self, player: Player):
        """Cancel a pending challenge."""
        if player.member.id in self.pending_challenges:
            del self.pending_challenges[player.member.id]
    
    async def end_battle(self, battle: Battle):
        """End a battle and process results."""
        if battle.state != BattleState.FINISHED:
            return
        
        # Update player records
        if battle.winner and battle.loser:
            battle.winner.player.add_win()
            battle.loser.player.add_loss()
            
            # Add damage stats
            battle.winner.player.add_damage_dealt(battle.winner.battle_stats["damage_dealt"])
            battle.winner.player.add_damage_taken(battle.winner.battle_stats["damage_taken"])
            battle.loser.player.add_damage_dealt(battle.loser.battle_stats["damage_dealt"])
            battle.loser.player.add_damage_taken(battle.loser.battle_stats["damage_taken"])
            
            # Process wager if any
            if battle.wager and battle.wager > 0:
                battle.loser.player.remove_berries(battle.wager)
                battle.winner.player.add_berries(battle.wager)
            
            # Increase devil fruit mastery if applicable
            if battle.winner.player.devil_fruit:
                # This would be handled by the fruit manager
                pass
            
            # Save player data
            await self.player_manager.save_player(battle.winner.player)
            await self.player_manager.save_player(battle.loser.player)
        
        # Remove from active battles
        if battle.id in self.active_battles:
            del self.active_battles[battle.id]
    
    async def process_battle_rewards(self, battle: Battle):
        """Process battle rewards (berries, achievements, etc.)."""
        if not battle.winner:
            return
        
        # Base berries reward
        base_reward = 1000
        
        # Bonus for difficulty (based on opponent's stats)
        opponent = battle.loser
        difficulty_bonus = min(1000, opponent.player.wins * 10)
        
        # Bonus for perfect victory (no damage taken)
        perfect_bonus = 500 if battle.winner.battle_stats["damage_taken"] == 0 else 0
        
        total_reward = base_reward + difficulty_bonus + perfect_bonus
        
        # Give berries to winner
        battle.winner.player.add_berries(total_reward)
        
        # Process achievements (this would be handled by achievement manager)
        
        # Save player data
        await self.player_manager.save_player(battle.winner.player)
        
        return total_reward
    
    async def cleanup_all_battles(self):
        """Clean up all active battles (called on cog unload)."""
        for battle in list(self.active_battles.values()):
            battle.cancel_battle("Bot shutting down")
            if battle.id in self.active_battles:
                del self.active_battles[battle.id]
        
        # Clear pending challenges
        self.pending_challenges.clear()
    
    def get_battle_by_id(self, battle_id: str) -> Optional[Battle]:
        """Get a battle by its ID."""
        return self.active_battles.get(battle_id)
    
    async def get_recent_battles(self, guild: discord.Guild, limit: int = 10) -> List[Dict]:
        """Get recent finished battles (this would require a database implementation)."""
        # This is a placeholder - in a real implementation, you'd store
        # battle history in a database or config
        return []
    
    def get_active_battle_count(self) -> int:
        """Get the number of currently active battles."""
        return len([b for b in self.active_battles.values() if b.state == BattleState.ACTIVE])
