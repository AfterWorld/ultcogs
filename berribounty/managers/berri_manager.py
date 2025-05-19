import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from ..models.player import Player

class BerriManager:
    """Manages berri transactions and economy."""
    
    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._transaction_lock = asyncio.Lock()
    
    async def get_player(self, member) -> Player:
        """Get or create a player instance."""
        data = await self.config.member(member).all()
        return Player(member, data)
    
    async def save_player(self, player: Player):
        """Save player data to config."""
        await self.config.member(player.member).set(player.to_dict())
    
    async def transfer_berries(self, from_player: Player, to_player: Player, amount: int) -> bool:
        """Transfer berries between players safely."""
        async with self._transaction_lock:
            if from_player.berries < amount:
                return False
            
            from_player.remove_berries(amount)
            to_player.add_berries(amount)
            
            # Save both players
            await self.save_player(from_player)
            await self.save_player(to_player)
            
            return True
    
    async def daily_reward(self, player: Player) -> Tuple[bool, int, str]:
        """Process daily reward for a player."""
        if not player.last_active:
            # First time player
            reward = random.randint(10000, 50000)
            player.add_berries(reward)
            player.update_last_active()
            await self.save_player(player)
            return True, reward, "Welcome bonus!"
        
        last_active = datetime.fromisoformat(player.last_active)
        now = datetime.utcnow()
        time_since = now - last_active
        
        # Check if 24 hours have passed
        if time_since < timedelta(hours=24):
            time_left = timedelta(hours=24) - time_since
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return False, 0, f"Next reward in {hours}h {minutes}m"
        
        # Calculate reward based on streak
        days_streak = min(7, time_since.days)  # Max 7 day streak
        base_reward = 25000
        streak_bonus = days_streak * 5000
        total_reward = base_reward + streak_bonus
        
        # Add bonus for achievements/titles
        if len(player.achievements) > 10:
            total_reward = int(total_reward * 1.2)
        
        player.add_berries(total_reward)
        player.update_last_active()
        await self.save_player(player)
        
        return True, total_reward, f"Day {days_streak} streak bonus!"
    
    async def berri_gamble(self, player: Player, bet_amount: int) -> Tuple[bool, int, str]:
        """Process a berri gambling game."""
        if player.berries < bet_amount:
            return False, 0, "Insufficient berries!"
        
        # Calculate odds based on bet amount
        if bet_amount <= 10000:
            win_chance = 0.6  # 60% chance
        elif bet_amount <= 100000:
            win_chance = 0.5  # 50% chance
        elif bet_amount <= 1000000:
            win_chance = 0.4  # 40% chance
        else:
            win_chance = 0.3  # 30% chance for high stakes
        
        # Roll the dice
        won = random.random() < win_chance
        
        if won:
            # Calculate winnings with multipliers
            if bet_amount >= 1000000:
                multiplier = 2.5
            elif bet_amount >= 100000:
                multiplier = 2.0
            else:
                multiplier = 1.5
            
            winnings = int(bet_amount * multiplier)
            player.add_berries(winnings)
            player.stats["gambling_wins"] = player.stats.get("gambling_wins", 0) + 1
            await self.save_player(player)
            
            return True, winnings, f"Won {winnings:,} berries! (x{multiplier})"
        else:
            # Lost the bet
            player.remove_berries(bet_amount)
            player.stats["gambling_losses"] = player.stats.get("gambling_losses", 0) + 1
            await self.save_player(player)
            
            return False, bet_amount, f"Lost {bet_amount:,} berries!"
    
    async def berri_heist(self, organizer: Player, targets: list, heist_cost: int) -> Dict[str, Any]:
        """Process a berri heist operation."""
        # Check if organizer can afford the heist
        if organizer.berries < heist_cost:
            return {"success": False, "reason": "Insufficient berries for heist setup!"}
        
        # Remove heist cost
        organizer.remove_berries(heist_cost)
        
        # Calculate success chance
        base_chance = 0.4  # 40% base success
        team_bonus = len(targets) * 0.05  # 5% per additional member
        total_chance = min(0.8, base_chance + team_bonus)  # Max 80% success
        
        # Determine outcome
        success = random.random() < total_chance
        
        if success:
            # Calculate total loot
            total_loot = 0
            for target in targets:
                target_loot = min(target.berries * 0.1, 500000)  # Max 10% or 500k
                total_loot += target_loot
                target.remove_berries(int(target_loot))
            
            # Split loot among crew (organizer gets double share)
            crew_size = len(targets) + 1
            organizer_share = int(total_loot * 0.4)  # 40% for organizer
            member_share = int(total_loot * 0.6 / len(targets))  # 60% split among crew
            
            organizer.add_berries(organizer_share)
            for target in targets:
                target.add_berries(member_share)
            
            # Save all players
            await self.save_player(organizer)
            for target in targets:
                await self.save_player(target)
            
            return {
                "success": True,
                "total_loot": total_loot,
                "organizer_share": organizer_share,
                "member_share": member_share,
                "participants": len(targets) + 1
            }
        else:
            # Heist failed - everyone loses berries
            penalty = heist_cost // 2
            for target in targets:
                lost = target.remove_berries(penalty)
            
            # Save all players
            await self.save_player(organizer)
            for target in targets:
                await self.save_player(target)
            
            return {
                "success": False,
                "reason": "Heist failed!",
                "penalty": penalty,
                "participants": len(targets) + 1
            }
    
    async def get_leaderboard(self, guild, limit: int = 10) -> list:
        """Get berri leaderboard for a guild."""
        all_members = await self.config.all_members(guild)
        
        leaderboard = []
        for member_id, data in all_members.items():
            member = guild.get_member(int(member_id))
            if member and not member.bot:
                player = Player(member, data)
                leaderboard.append(player)
        
        # Sort by total berries (including bank)
        leaderboard.sort(key=lambda p: p.total_berries, reverse=True)
        
        return leaderboard[:limit]