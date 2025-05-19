"""Player management for the One Piece bot."""

import time
from typing import Dict, List, Optional
import discord
from ..models.player import Player

class PlayerManager:
    """Manages player data and operations."""
    
    def __init__(self, config):
        self.config = config
        self._player_cache = {}
    
    async def get_or_create_player(self, member: discord.Member) -> Player:
        """Get or create a player from a Discord member."""
        # Check cache first
        if member.id in self._player_cache:
            return self._player_cache[member.id]
        
        # Get data from config
        player_data = await self.config.member(member).all()
        
        # Create player object
        player = Player(member, player_data)
        
        # Cache the player
        self._player_cache[member.id] = player
        
        return player
    
    async def save_player(self, player: Player):
        """Save player data to config."""
        # Update the cache
        self._player_cache[player.member.id] = player
        
        # Save to config
        await self.config.member(player.member).set(player.to_dict())
    
    async def update_last_active(self, player: Player):
        """Update player's last active time."""
        player.last_active = time.time()
        await self.save_player(player)
    
    async def get_all_players(self, guild: discord.Guild) -> List[Player]:
        """Get all players in a guild."""
        players = []
        async for member_data in self.config.all_members(guild):
            member_id, data = member_data
            member = guild.get_member(int(member_id))
            if member:
                player = Player(member, data)
                players.append(player)
        return players
    
    async def reset_player(self, member: discord.Member):
        """Reset a player's data to defaults."""
        await self.config.member(member).clear()
        
        # Remove from cache
        if member.id in self._player_cache:
            del self._player_cache[member.id]
    
    async def transfer_berries(self, from_player: Player, to_player: Player, amount: int) -> bool:
        """Transfer berries between players."""
        if from_player.berries < amount:
            return False
        
        from_player.remove_berries(amount)
        to_player.add_berries(amount)
        
        await self.save_player(from_player)
        await self.save_player(to_player)
        
        return True
    
    async def get_top_players(self, guild: discord.Guild, stat: str, limit: int = 10) -> List[Player]:
        """Get top players by a specific stat."""
        all_players = await self.get_all_players(guild)
        
        # Sort by the specified stat
        if stat == "berries":
            all_players.sort(key=lambda p: p.berries, reverse=True)
        elif stat == "wins":
            all_players.sort(key=lambda p: p.wins, reverse=True)
        elif stat == "win_rate":
            all_players.sort(key=lambda p: p.win_rate, reverse=True)
        elif stat == "total_wealth":
            all_players.sort(key=lambda p: p.total_wealth, reverse=True)
        elif stat == "damage_dealt":
            all_players.sort(key=lambda p: p.total_damage_dealt, reverse=True)
        
        return all_players[:limit]
    
    def clear_cache(self):
        """Clear the player cache."""
        self._player_cache.clear()
    
    def get_cached_player(self, member_id: int) -> Optional[Player]:
        """Get a player from cache without loading from config."""
        return self._player_cache.get(member_id)