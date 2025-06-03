"""
Enhanced utility functions for Uno game
Features: Statistics Management, Performance Optimizations, Emoji Card Display
"""
import os
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import discord
from datetime import datetime, timedelta
from .cards import UnoCard, UnoColor, UnoCardType


def get_card_emoji_name(card: UnoCard) -> str:
    """Get the emoji name for a card (matches asset file naming)"""
    if card.color == UnoColor.WILD:
        if card.card_type == UnoCardType.WILD:
            return "Wild_Card"
        elif card.card_type == UnoCardType.WILD_DRAW4:
            return "Wild_draw4"
    else:
        if card.card_type == UnoCardType.NUMBER:
            return f"{card.color.value}_{card.value}"
        elif card.card_type == UnoCardType.SKIP:
            return f"{card.color.value}_skip"
        elif card.card_type == UnoCardType.REVERSE:
            return f"{card.color.value}_reverse"
        elif card.card_type == UnoCardType.DRAW2:
            return f"{card.color.value}_draw2"
    
    return "Unknown_Card"


def get_card_emoji_fallback(card: UnoCard) -> str:
    """Get emoji representation for a card (fallback method)"""
    color_emojis = {
        UnoColor.RED: "🔴",
        UnoColor.GREEN: "🟢",
        UnoColor.YELLOW: "🟡", 
        UnoColor.BLUE: "🔵",
        UnoColor.WILD: "🌈"
    }
    
    type_emojis = {
        UnoCardType.NUMBER: "🔢",
        UnoCardType.SKIP: "⏭️",
        UnoCardType.REVERSE: "🔄",
        UnoCardType.DRAW2: "📥",
        UnoCardType.WILD: "🎨",
        UnoCardType.WILD_DRAW4: "🌈"
    }
    
    return color_emojis.get(card.color, "🎴")


def setup_assets_directory(cog_data_path: Path) -> Path:
    """Setup and return the assets directory path"""
    assets_path = cog_data_path / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)
    
    # Create a comprehensive readme file
    readme_path = assets_path / "README.md"
    if not readme_path.exists():
        readme_content = """# Uno Card Assets & Emojis

## Emoji Setup (Recommended)
The bot now uses Discord emojis for cards instead of images. Upload the card images as custom emojis to your server with these exact names:

### Required Emoji Names:
```
Number Cards (40 total):
Red_0, Red_1, Red_2, ..., Red_9
Green_0, Green_1, Green_2, ..., Green_9
Yellow_0, Yellow_1, Yellow_2, ..., Yellow_9
Blue_0, Blue_1, Blue_2, ..., Blue_9

Action Cards (24 total):
Red_skip, Red_reverse, Red_draw2
Green_skip, Green_reverse, Green_draw2
Yellow_skip, Yellow_reverse, Yellow_draw2
Blue_skip, Blue_reverse, Blue_draw2

Wild Cards (8 total):
Wild_Card
Wild_draw4
```

## Image Assets (Legacy/Fallback)
If you prefer using image files instead of emojis, place your Uno card images in this directory using the following naming convention:

### Naming Convention:
- Number cards: `{Color}_{Number}.png` (e.g., `Red_5.png`, `Blue_0.png`)
- Skip cards: `{Color}_skip.png` (e.g., `Green_skip.png`)
- Reverse cards: `{Color}_reverse.png` (e.g., `Yellow_reverse.png`)
- Draw 2 cards: `{Color}_draw2.png` (e.g., `Red_draw2.png`)
- Wild cards: `Wild_Card.png`
- Wild Draw 4 cards: `Wild_draw4.png`

### Colors:
- Red
- Green  
- Yellow
- Blue
- Wild (for wild cards)

## Setup Instructions:

### Method 1: Discord Emojis (Recommended)
1. Get Uno card images
2. Upload each image as a custom emoji to your Discord server
3. Name each emoji exactly as shown above (case-sensitive)
4. The bot will automatically use these emojis for card display

### Method 2: Image Files (Legacy)
1. Place card image files in this assets directory
2. Use the naming convention above
3. Format: PNG (recommended) or JPG
4. Size: 100x140 pixels (recommended)

## Performance Benefits:
- Emojis load faster than images
- No file storage requirements
- Consistent sizing across all cards
- Better mobile experience
- Instant loading in hands and game displays

## Troubleshooting:
- If emojis don't appear, check that they're uploaded to the same server as the bot
- Emoji names must match exactly (case-sensitive)
- Bot needs access to use external emojis if emojis are from other servers
- Fallback will show colored circles if emojis are missing

Total: 108 emojis needed (matching standard Uno deck)

Note: All names are case-sensitive and use underscores as separators.
"""
        readme_path.write_text(readme_content)
    
    return assets_path


def format_player_list(players: List[int], ai_players: List = None, current_player: Optional[int] = None) -> str:
    """Format a list of players for display with enhanced information"""
    if not players:
        return "No players"
    
    ai_players = ai_players or []
    ai_player_ids = [ai.player_id for ai in ai_players]
    
    formatted = []
    for player_id in players:
        if player_id in ai_player_ids:
            # Find AI player info
            ai_player = next((ai for ai in ai_players if ai.player_id == player_id), None)
            if ai_player:
                name = f"🤖 {ai_player.name} ({ai_player.difficulty})"
            else:
                name = f"🤖 AI Player"
        else:
            name = f"<@{player_id}>"
        
        if current_player and player_id == current_player:
            name = f"**{name}** 🎯"
        
        formatted.append(name)
    
    return "\n".join(formatted)


def format_card_counts(card_counts: dict, current_player: Optional[int] = None, game = None) -> str:
    """Format player card counts for display with enhanced information"""
    if not card_counts:
        return "No players"
    
    formatted = []
    for player_id, count in card_counts.items():
        # Check if AI player
        if game and game.is_ai_player(player_id):
            ai_player = game.get_ai_player(player_id)
            name = f"🤖 {ai_player.name}" if ai_player else "🤖 AI"
        else:
            name = f"<@{player_id}>"
        
        cards_text = "card" if count == 1 else "cards"
        
        if current_player and player_id == current_player:
            line = f"**{name}**: {count} {cards_text} 🎯"
        else:
            line = f"{name}: {count} {cards_text}"
        
        # Add special indicators
        if count == 1:
            line += " 🔥"  # UNO!
        elif count == 0:
            line += " 🎉"  # Winner!
        
        # Add UNO status if applicable
        if game and hasattr(game, 'uno_called'):
            if game.uno_called.get(player_id, False) and count == 1:
                line += " (UNO Called)"
            elif game.pending_uno_penalty.get(player_id, False):
                line += " (⚠️ Penalty)"
        
        formatted.append(line)
    
    return "\n".join(formatted)


def validate_card_files(assets_path: Path) -> Tuple[List[str], List[str]]:
    """
    Validate that all required card files exist.
    Returns (missing_files, existing_files)
    Note: This is now mainly for legacy image support
    """
    from .cards import UnoDeck
    
    # Create a deck to get all possible cards
    deck = UnoDeck()
    all_cards = deck.draw_pile.copy()
    
    missing_files = []
    existing_files = []
    
    # Check each card file
    for card in all_cards:
        card_path = assets_path / card.filename
        if card_path.exists():
            existing_files.append(card.filename)
        else:
            missing_files.append(card.filename)
    
    return missing_files, existing_files


def validate_card_emojis(bot: discord.Client) -> Tuple[List[str], List[str]]:
    """
    Validate that all required card emojis exist in the bot's available emojis.
    Returns (missing_emojis, existing_emojis)
    """
    from .cards import UnoDeck
    
    # Create a deck to get all possible cards
    deck = UnoDeck()
    all_cards = deck.draw_pile.copy()
    
    missing_emojis = []
    existing_emojis = []
    
    # Check each card emoji
    for card in all_cards:
        emoji_name = get_card_emoji_name(card)
        emoji = discord.utils.get(bot.emojis, name=emoji_name)
        
        if emoji:
            existing_emojis.append(emoji_name)
        else:
            missing_emojis.append(emoji_name)
    
    return missing_emojis, existing_emojis


async def cleanup_temp_files(assets_path: Path, max_age_minutes: int = 60):
    """Clean up temporary image files with age-based cleanup"""
    try:
        current_time = time.time()
        max_age_seconds = max_age_minutes * 60
        
        # Look for any temporary files
        temp_files = list(assets_path.glob("temp_*.png"))
        temp_files.extend(list(assets_path.glob("temp_*.jpg")))
        cleaned_count = 0
        
        for temp_file in temp_files:
            try:
                file_age = current_time - temp_file.stat().st_mtime
                if file_age > max_age_seconds:
                    temp_file.unlink()
                    cleaned_count += 1
            except Exception:
                pass  # Ignore errors when cleaning up
        
        if cleaned_count > 0:
            print(f"Cleaned up {cleaned_count} temporary files")
            
    except Exception as e:
        print(f"Error during temp file cleanup: {e}")


class StatisticsManager:
    """Enhanced statistics management system"""
    
    def __init__(self):
        self.session_stats = {}
        self.achievement_definitions = {
            "First Win": {"description": "Win your first game", "check": lambda stats: stats.get("games_won", 0) >= 1},
            "Speed Demon": {"description": "Win a game in under 5 minutes", "check": lambda stats: stats.get("fastest_win", float('inf')) < 300},
            "UNO Master": {"description": "Call UNO 10 times", "check": lambda stats: stats.get("uno_calls", 0) >= 10},
            "Challenge Champion": {"description": "Successfully challenge 5 Draw 4s", "check": lambda stats: stats.get("draw4_successful_challenges", 0) >= 5},
            "Card Counter": {"description": "Play 100 cards", "check": lambda stats: stats.get("cards_played", 0) >= 100},
            "Perfect Game": {"description": "Win without drawing any cards", "check": lambda stats: "perfect_game" in stats.get("special_achievements", [])},
            "AI Crusher": {"description": "Beat 10 AI players", "check": lambda stats: stats.get("ai_wins", 0) >= 10},
            "Comeback King": {"description": "Win from 10+ cards", "check": lambda stats: "comeback_king" in stats.get("special_achievements", [])},
            "Color Master": {"description": "Play all 4 colors in one game", "check": lambda stats: "color_master" in stats.get("special_achievements", [])},
            "Wild Wild West": {"description": "Play 20 wild cards", "check": lambda stats: stats.get("wild_cards_played", 0) >= 20},
            "Marathon Player": {"description": "Play for 2+ hours total", "check": lambda stats: stats.get("total_play_time", 0) >= 7200},
            "Frequent Player": {"description": "Play 50 games", "check": lambda stats: stats.get("games_played", 0) >= 50},
            "Win Streak": {"description": "Win 5 games in a row", "check": lambda stats: stats.get("max_win_streak", 0) >= 5},
            "Draw Master": {"description": "Successfully stack 3 draw cards", "check": lambda stats: "draw_master" in stats.get("special_achievements", [])},
            "Lucky Seven": {"description": "Win with exactly 7 starting cards", "check": lambda stats: "lucky_seven" in stats.get("special_achievements", [])}
        }
    
    def check_achievements(self, player_stats: Dict[str, Any]) -> List[str]:
        """Check which achievements a player has unlocked"""
        current_achievements = set(player_stats.get("achievements", []))
        new_achievements = []
        
        for achievement_name, achievement_data in self.achievement_definitions.items():
            if achievement_name not in current_achievements:
                if achievement_data["check"](player_stats):
                    new_achievements.append(achievement_name)
        
        return new_achievements
    
    def calculate_player_score(self, player_stats: Dict[str, Any]) -> int:
        """Calculate a player's overall score"""
        score = 0
        
        # Base scoring
        score += player_stats.get("games_won", 0) * 100
        score += player_stats.get("games_played", 0) * 10
        score += player_stats.get("cards_played", 0) * 1
        score += player_stats.get("uno_calls", 0) * 20
        score += player_stats.get("draw4_successful_challenges", 0) * 50
        
        # Achievement bonuses
        score += len(player_stats.get("achievements", [])) * 200
        
        # Efficiency bonuses
        win_rate = player_stats.get("games_won", 0) / max(1, player_stats.get("games_played", 1))
        score += int(win_rate * 500)
        
        # Speed bonus
        if player_stats.get("fastest_win"):
            speed_bonus = max(0, 600 - player_stats["fastest_win"]) // 10
            score += speed_bonus
        
        return score
    
    def get_player_rank(self, player_score: int) -> Tuple[str, str]:
        """Get player rank based on score"""
        if player_score >= 10000:
            return "🏆 Grandmaster", "You've mastered the art of Uno!"
        elif player_score >= 5000:
            return "💎 Master", "An exceptional Uno player!"
        elif player_score >= 2500:
            return "🥇 Expert", "You know Uno inside and out!"
        elif player_score >= 1000:
            return "🥈 Advanced", "Getting really good at this!"
        elif player_score >= 500:
            return "🥉 Intermediate", "You're improving quickly!"
        elif player_score >= 100:
            return "📚 Novice", "Still learning the ropes!"
        else:
            return "🆕 Beginner", "Welcome to Uno!"


class EnhancedGameManager:
    """Enhanced game manager with performance optimizations and statistics"""
    
    def __init__(self):
        self.games: Dict[int, 'UnoGameSession'] = {}  # channel_id -> game_session
        self.game_history: List[Dict[str, Any]] = []
        self.performance_stats = {
            "games_created": 0,
            "games_completed": 0,
            "total_players": 0,
            "average_game_duration": 0,
            "peak_concurrent_games": 0
        }
        self.last_cleanup = datetime.now()
    
    def create_game(self, channel_id: int, host_id: int, settings: Dict[str, Any] = None) -> Optional['UnoGameSession']:
        """Create a new game session with enhanced tracking"""
        if channel_id in self.games:
            # Check if existing game is finished or expired
            existing_game = self.games[channel_id]
            from .game import GameState  # Import here to avoid circular import
            if existing_game.state != GameState.FINISHED and not existing_game.is_expired():
                return None  # Game already exists
        
        from .game import UnoGameSession  # Import here to avoid circular import
        game = UnoGameSession(channel_id, host_id, settings)
        self.games[channel_id] = game
        
        # Update performance stats
        self.performance_stats["games_created"] += 1
        self.performance_stats["peak_concurrent_games"] = max(
            self.performance_stats["peak_concurrent_games"],
            len(self.games)
        )
        
        return game
    
    def get_game(self, channel_id: int) -> Optional['UnoGameSession']:
        """Get existing game session"""
        return self.games.get(channel_id)
    
    def remove_game(self, channel_id: int) -> bool:
        """Remove a game session with history tracking"""
        if channel_id in self.games:
            game = self.games[channel_id]
            
            # Save to history if game was completed
            from .game import GameState
            if game.state == GameState.FINISHED:
                self.game_history.append({
                    "channel_id": channel_id,
                    "host_id": game.host_id,
                    "players": len(game.players),
                    "ai_players": len(game.ai_players),
                    "duration": (discord.utils.utcnow() - game.game_start_time).total_seconds() if game.game_start_time else 0,
                    "completed_at": discord.utils.utcnow().isoformat(),
                    "settings": game.settings.copy()
                })
                self.performance_stats["games_completed"] += 1
            
            game.cleanup()
            del self.games[channel_id]
            return True
        return False
    
    def cleanup_expired_games(self) -> int:
        """Remove expired games with enhanced cleanup"""
        current_time = datetime.now()
        
        # Only cleanup every 5 minutes to avoid performance issues
        if (current_time - self.last_cleanup).seconds < 300:
            return 0
        
        self.last_cleanup = current_time
        
        expired_channels = []
        for channel_id, game in self.games.items():
            if game.is_expired():
                expired_channels.append(channel_id)
        
        for channel_id in expired_channels:
            self.remove_game(channel_id)
        
        # Trim game history to prevent memory issues (keep last 1000 games)
        if len(self.game_history) > 1000:
            self.game_history = self.game_history[-1000:]
        
        return len(expired_channels)
    
    def get_active_games_count(self) -> int:
        """Get number of active games"""
        from .game import GameState  # Import here to avoid circular import
        return len([g for g in self.games.values() if g.state != GameState.FINISHED])
    
    def get_total_players(self) -> int:
        """Get total number of players across all games"""
        return sum(len(g.players) for g in self.games.values())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        active_games = self.get_active_games_count()
        total_players = self.get_total_players()
        
        # Calculate average game duration from history
        if self.game_history:
            total_duration = sum(game["duration"] for game in self.game_history)
            avg_duration = total_duration / len(self.game_history)
        else:
            avg_duration = 0
        
        return {
            "active_games": active_games,
            "total_games": len(self.games),
            "total_players": total_players,
            "games_created": self.performance_stats["games_created"],
            "games_completed": self.performance_stats["games_completed"],
            "average_game_duration": avg_duration,
            "peak_concurrent_games": self.performance_stats["peak_concurrent_games"],
            "game_history_size": len(self.game_history)
        }


# Global instances
game_manager = EnhancedGameManager()
stats_manager = StatisticsManager()


# Emoji setup utility functions
def generate_emoji_upload_guide(assets_path: Path) -> str:
    """Generate a guide for uploading emojis"""
    from .cards import UnoDeck
    
    deck = UnoDeck()
    all_cards = deck.draw_pile.copy()
    
    guide = """# Uno Card Emoji Upload Guide

## Quick Setup Commands (if you have card images):
If you have image files, you can use Discord's Server Settings > Emoji to bulk upload:

"""
    
    # Group by type for easier uploading
    number_cards = []
    action_cards = []
    wild_cards = []
    
    for card in all_cards:
        emoji_name = get_card_emoji_name(card)
        if card.card_type == UnoCardType.NUMBER:
            number_cards.append(emoji_name)
        elif card.color == UnoColor.WILD:
            wild_cards.append(emoji_name)
        else:
            action_cards.append(emoji_name)
    
    guide += "### Number Cards (40 emojis):\n"
    for emoji in sorted(set(number_cards)):
        guide += f"- {emoji}\n"
    
    guide += "\n### Action Cards (24 emojis):\n"
    for emoji in sorted(set(action_cards)):
        guide += f"- {emoji}\n"
    
    guide += "\n### Wild Cards (8 emojis):\n"
    for emoji in sorted(set(wild_cards)):
        guide += f"- {emoji}\n"
    
    guide += f"""
### Total: {len(set([get_card_emoji_name(card) for card in all_cards]))} unique emojis needed

## Upload Instructions:
1. Go to Server Settings > Emoji
2. Click "Upload Emoji" 
3. Select image file
4. Enter exact emoji name from list above
5. Repeat for all cards

## Notes:
- Emoji names are case-sensitive
- Use underscores, not spaces
- Bot needs "Use External Emojis" permission if emojis are from other servers
- Standard Discord servers support 50 static emojis (need Nitro boost for more)
- Consider using multiple servers if you hit the limit
"""
    
    return guide


def check_bot_emoji_permissions(bot: discord.Client, guild: discord.Guild) -> Dict[str, bool]:
    """Check if bot has necessary emoji permissions"""
    bot_member = guild.get_member(bot.user.id)
    if not bot_member:
        return {"in_guild": False}
    
    permissions = bot_member.guild_permissions
    
    return {
        "in_guild": True,
        "use_external_emojis": permissions.use_external_emojis,
        "manage_emojis": permissions.manage_emojis_and_stickers,
        "embed_links": permissions.embed_links,
        "send_messages": permissions.send_messages
    }