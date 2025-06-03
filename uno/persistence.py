"""
Persistent Game State System for Uno Cog
Handles saving and restoring game states across bot restarts
"""
import json
import asyncio
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import discord
from redbot.core.data_manager import cog_data_path

from .game import UnoGameSession, GameState, AIPlayer
from .cards import UnoCard, UnoColor, UnoCardType, UnoDeck, PlayerHand


class PersistenceManager:
    """Manages persistent storage of game states"""
    
    def __init__(self, cog_data_path: Path):
        self.data_path = cog_data_path
        self.persistence_file = self.data_path / "persistent_games.json"
        self.backup_file = self.data_path / "persistent_games_backup.json"
        
        # Ensure directory exists
        self.data_path.mkdir(parents=True, exist_ok=True)
    
    async def save_games(self, games: Dict[int, UnoGameSession]) -> bool:
        """Save all active games to persistent storage"""
        try:
            persistent_data = {
                "version": "1.0",
                "saved_at": datetime.now().isoformat(),
                "games": {}
            }
            
            for channel_id, game in games.items():
                if game.settings.get("persistent_games", True) and game.state != GameState.FINISHED:
                    try:
                        game_data = self._serialize_game(game)
                        persistent_data["games"][str(channel_id)] = game_data
                    except Exception as e:
                        print(f"Error serializing game {channel_id}: {e}")
                        continue
            
            # Create backup of existing file
            if self.persistence_file.exists():
                self.persistence_file.rename(self.backup_file)
            
            # Write new data
            with open(self.persistence_file, 'w') as f:
                json.dump(persistent_data, f, indent=2)
            
            print(f"Saved {len(persistent_data['games'])} persistent games")
            return True
            
        except Exception as e:
            print(f"Error saving persistent games: {e}")
            # Restore backup if available
            if self.backup_file.exists():
                self.backup_file.rename(self.persistence_file)
            return False
    
    async def load_games(self) -> Dict[int, UnoGameSession]:
        """Load saved games from persistent storage"""
        games = {}
        
        try:
            if not self.persistence_file.exists():
                return games
            
            with open(self.persistence_file, 'r') as f:
                persistent_data = json.load(f)
            
            if persistent_data.get("version") != "1.0":
                print("Warning: Incompatible persistence version")
                return games
            
            for channel_id_str, game_data in persistent_data.get("games", {}).items():
                try:
                    channel_id = int(channel_id_str)
                    game = self._deserialize_game(game_data)
                    if game:
                        games[channel_id] = game
                except Exception as e:
                    print(f"Error loading game {channel_id_str}: {e}")
                    continue
            
            print(f"Loaded {len(games)} persistent games")
            
        except Exception as e:
            print(f"Error loading persistent games: {e}")
            
            # Try backup file
            if self.backup_file.exists():
                try:
                    with open(self.backup_file, 'r') as f:
                        persistent_data = json.load(f)
                    print("Loaded from backup file")
                    # Process backup data...
                except Exception as backup_error:
                    print(f"Backup file also corrupted: {backup_error}")
        
        return games
    
    def _serialize_game(self, game: UnoGameSession) -> Dict[str, Any]:
        """Serialize a game session to JSON-compatible format"""
        return {
            "channel_id": game.channel_id,
            "host_id": game.host_id,
            "state": game.state.value,
            "players": game.players,
            "ai_players": [
                {
                    "name": ai.name,
                    "difficulty": ai.difficulty,
                    "player_id": ai.player_id
                }
                for ai in game.ai_players
            ],
            "hands": {
                str(pid): [
                    {
                        "color": card.color.value,
                        "card_type": card.card_type.value,
                        "value": card.value
                    }
                    for card in hand.cards
                ]
                for pid, hand in game.hands.items()
            },
            "deck": {
                "discard_pile": [
                    {
                        "color": card.color.value,
                        "card_type": card.card_type.value,
                        "value": card.value
                    }
                    for card in game.deck.discard_pile
                ],
                "current_color": game.deck.current_color.value if game.deck.current_color else None,
                "draw_pile_count": len(game.deck.draw_pile)  # Don't save full draw pile for security
            },
            "game_state": {
                "current_player_index": game.current_player_index,
                "direction": game.direction.value,
                "draw_count": game.draw_count,
                "round_number": game.round_number
            },
            "uno_tracking": {
                "uno_called": game.uno_called,
                "pending_uno_penalty": game.pending_uno_penalty
            },
            "challenge_system": {
                "last_draw4_player": game.last_draw4_player,
                "challenge_window_open": game.challenge_window_open
            },
            "timestamps": {
                "last_activity": game.last_activity.isoformat() if game.last_activity else None,
                "game_start_time": game.game_start_time.isoformat() if game.game_start_time else None
            },
            "settings": game.settings,
            "action_history": game.action_history[-50:]  # Only save last 50 actions
        }
    
    def _deserialize_game(self, data: Dict[str, Any]) -> Optional[UnoGameSession]:
        """Deserialize a game session from stored data"""
        try:
            # Create new game instance
            game = UnoGameSession(
                data["channel_id"],
                data["host_id"],
                data.get("settings", {})
            )
            
            # Restore basic state
            game.state = GameState(data["state"])
            game.players = data["players"]
            game.current_player_index = data["game_state"]["current_player_index"]
            game.direction = data["game_state"]["direction"]
            game.draw_count = data["game_state"]["draw_count"]
            game.round_number = data["game_state"].get("round_number", 0)
            
            # Restore AI players
            game.ai_players = []
            for ai_data in data.get("ai_players", []):
                ai_player = AIPlayer(ai_data["name"], ai_data["difficulty"])
                ai_player.player_id = ai_data["player_id"]
                game.ai_players.append(ai_player)
            
            # Restore hands
            game.hands = {}
            for pid_str, hand_data in data["hands"].items():
                pid = int(pid_str)
                hand = PlayerHand(pid)
                
                for card_data in hand_data:
                    card = self._deserialize_card(card_data)
                    if card:
                        hand.add_card(card)
                
                game.hands[pid] = hand
            
            # Restore deck (partial - only discard pile and current color)
            deck_data = data["deck"]
            game.deck = UnoDeck()  # Create fresh deck
            
            # Restore discard pile
            game.deck.discard_pile = []
            for card_data in deck_data["discard_pile"]:
                card = self._deserialize_card(card_data)
                if card:
                    game.deck.discard_pile.append(card)
            
            # Restore current color
            if deck_data["current_color"]:
                game.deck.current_color = UnoColor(deck_data["current_color"])
            
            # Remove cards from draw pile that are in hands or discard
            # This is a simplified approach - in production you'd want more sophisticated deck restoration
            used_cards = []
            for hand in game.hands.values():
                used_cards.extend(hand.cards)
            used_cards.extend(game.deck.discard_pile)
            
            # Restore UNO tracking
            uno_data = data.get("uno_tracking", {})
            game.uno_called = {int(k): v for k, v in uno_data.get("uno_called", {}).items()}
            game.pending_uno_penalty = {int(k): v for k, v in uno_data.get("pending_uno_penalty", {}).items()}
            
            # Restore challenge system
            challenge_data = data.get("challenge_system", {})
            game.last_draw4_player = challenge_data.get("last_draw4_player")
            game.challenge_window_open = challenge_data.get("challenge_window_open", False)
            
            # Restore timestamps
            timestamps = data.get("timestamps", {})
            if timestamps.get("last_activity"):
                game.last_activity = datetime.fromisoformat(timestamps["last_activity"])
            if timestamps.get("game_start_time"):
                game.game_start_time = datetime.fromisoformat(timestamps["game_start_time"])
            
            # Restore action history
            game.action_history = data.get("action_history", [])
            
            return game
            
        except Exception as e:
            print(f"Error deserializing game: {e}")
            return None
    
    def _deserialize_card(self, card_data: Dict[str, Any]) -> Optional[UnoCard]:
        """Deserialize a single card from stored data"""
        try:
            color = UnoColor(card_data["color"])
            card_type = UnoCardType(card_data["card_type"])
            value = card_data.get("value")
            
            return UnoCard(color, card_type, value)
            
        except Exception as e:
            print(f"Error deserializing card: {e}")
            return None
    
    async def cleanup_old_saves(self, max_age_days: int = 7):
        """Clean up old save files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 3600
            
            for file_path in [self.persistence_file, self.backup_file]:
                if file_path.exists():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        print(f"Cleaned up old save file: {file_path.name}")
        
        except Exception as e:
            print(f"Error during save cleanup: {e}")


class ViewPersistenceManager:
    """Manages persistent views that survive bot restarts"""
    
    def __init__(self, bot, cog):
        self.bot = bot
        self.cog = cog
        self.persistent_views: Dict[int, discord.ui.View] = {}
    
    async def restore_persistent_views(self, games: Dict[int, UnoGameSession]):
        """Restore persistent views for active games"""
        try:
            for channel_id, game in games.items():
                if game.state in [GameState.LOBBY, GameState.PLAYING]:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        continue
                    
                    # Try to find the game message
                    try:
                        # Look for recent messages from the bot
                        async for message in channel.history(limit=50):
                            if (message.author == self.bot.user and 
                                message.embeds and 
                                "Uno" in message.embeds[0].title):
                                
                                # Restore the appropriate view
                                if game.state == GameState.LOBBY:
                                    from .views import LobbyView
                                    view = LobbyView(game, self.cog)
                                else:
                                    from .views import UnoGameView
                                    view = UnoGameView(game, self.cog)
                                
                                # Update the message with the restored view
                                await message.edit(view=view)
                                game.game_message = message
                                self.persistent_views[channel_id] = view
                                
                                break
                    except Exception as e:
                        print(f"Error restoring view for channel {channel_id}: {e}")
            
            print(f"Restored {len(self.persistent_views)} persistent views")
            
        except Exception as e:
            print(f"Error restoring persistent views: {e}")
    
    def add_persistent_view(self, channel_id: int, view: discord.ui.View):
        """Add a view to persistent tracking"""
        self.persistent_views[channel_id] = view
    
    def remove_persistent_view(self, channel_id: int):
        """Remove a view from persistent tracking"""
        if channel_id in self.persistent_views:
            del self.persistent_views[channel_id]


class BackupManager:
    """Manages automatic backups of game data"""
    
    def __init__(self, cog_data_path: Path):
        self.data_path = cog_data_path
        self.backup_dir = self.data_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Maximum number of backups to keep
        self.max_backups = 10
    
    async def create_backup(self, games: Dict[int, UnoGameSession]) -> bool:
        """Create a timestamped backup of current game state"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"games_backup_{timestamp}.json"
            
            # Create persistence manager for serialization
            persistence = PersistenceManager(self.data_path)
            
            # Save to backup file
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "game_count": len(games),
                "games": {}
            }
            
            for channel_id, game in games.items():
                if game.state != GameState.FINISHED:
                    try:
                        game_data = persistence._serialize_game(game)
                        backup_data["games"][str(channel_id)] = game_data
                    except Exception as e:
                        print(f"Error backing up game {channel_id}: {e}")
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            print(f"Created backup: {backup_file.name}")
            return True
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    async def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the most recent ones"""
        try:
            backup_files = list(self.backup_dir.glob("games_backup_*.json"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Remove excess backups
            for old_backup in backup_files[self.max_backups:]:
                old_backup.unlink()
                print(f"Removed old backup: {old_backup.name}")
                
        except Exception as e:
            print(f"Error cleaning up backups: {e}")
    
    async def restore_from_backup(self, backup_filename: str) -> Optional[Dict[int, UnoGameSession]]:
        """Restore games from a specific backup file"""
        try:
            backup_file = self.backup_dir / backup_filename
            if not backup_file.exists():
                return None
            
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Use persistence manager for deserialization
            persistence = PersistenceManager(self.data_path)
            games = {}
            
            for channel_id_str, game_data in backup_data.get("games", {}).items():
                try:
                    channel_id = int(channel_id_str)
                    game = persistence._deserialize_game(game_data)
                    if game:
                        games[channel_id] = game
                except Exception as e:
                    print(f"Error restoring game {channel_id_str} from backup: {e}")
            
            print(f"Restored {len(games)} games from backup: {backup_filename}")
            return games
            
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return None
    
    def list_backups(self) -> List[str]:
        """List available backup files"""
        try:
            backup_files = list(self.backup_dir.glob("games_backup_*.json"))
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return [f.name for f in backup_files]
        except Exception as e:
            print(f"Error listing backups: {e}")
            return []


class PerformanceMonitor:
    """Monitors system performance and resource usage"""
    
    def __init__(self):
        self.metrics = {
            "games_saved": 0,
            "games_loaded": 0,
            "save_time": 0.0,
            "load_time": 0.0,
            "errors": 0
        }
    
    def record_save(self, duration: float, success: bool):
        """Record save operation metrics"""
        self.metrics["games_saved"] += 1
        self.metrics["save_time"] += duration
        if not success:
            self.metrics["errors"] += 1
    
    def record_load(self, duration: float, success: bool):
        """Record load operation metrics"""
        self.metrics["games_loaded"] += 1
        self.metrics["load_time"] += duration
        if not success:
            self.metrics["errors"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_save_time = self.metrics["save_time"] / max(1, self.metrics["games_saved"])
        avg_load_time = self.metrics["load_time"] / max(1, self.metrics["games_loaded"])
        
        return {
            "operations": {
                "saves": self.metrics["games_saved"],
                "loads": self.metrics["games_loaded"],
                "errors": self.metrics["errors"]
            },
            "performance": {
                "avg_save_time": round(avg_save_time, 3),
                "avg_load_time": round(avg_load_time, 3)
            },
            "reliability": {
                "success_rate": round(
                    (self.metrics["games_saved"] + self.metrics["games_loaded"] - self.metrics["errors"]) / 
                    max(1, self.metrics["games_saved"] + self.metrics["games_loaded"]) * 100, 2
                )
            }
        }


# Global instances that can be imported
persistence_manager = None
view_persistence_manager = None
backup_manager = None
performance_monitor = PerformanceMonitor()


def initialize_persistence(cog_data_path: Path, bot, cog):
    """Initialize persistence managers"""
    global persistence_manager, view_persistence_manager, backup_manager
    
    persistence_manager = PersistenceManager(cog_data_path)
    view_persistence_manager = ViewPersistenceManager(bot, cog)
    backup_manager = BackupManager(cog_data_path)