"""
Enhanced utility functions for Uno game
Features: Statistics Management, Performance Optimizations, Better Visualization
"""
import os
import asyncio
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import discord
from datetime import datetime, timedelta
from .cards import UnoCard, UnoColor, UnoCardType


# Performance caching
_card_image_cache: Dict[str, Image.Image] = {}
_font_cache: Dict[int, ImageFont.FreeTypeFont] = {}


def get_card_emoji(card: UnoCard) -> str:
    """Get emoji representation for a card"""
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


def _load_cached_image(file_path: Path) -> Optional[Image.Image]:
    """Load and cache card images for performance"""
    cache_key = str(file_path)
    
    if cache_key in _card_image_cache:
        return _card_image_cache[cache_key].copy()
    
    if file_path.exists():
        try:
            img = Image.open(file_path)
            # Cache the image
            _card_image_cache[cache_key] = img.copy()
            return img
        except Exception as e:
            print(f"Error loading image {file_path}: {e}")
    
    return None


def _get_font(size: int) -> Optional[ImageFont.FreeTypeFont]:
    """Get cached font for text rendering"""
    if size in _font_cache:
        return _font_cache[size]
    
    try:
        # Try to load a nice font, fallback to default
        font_paths = [
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "/Windows/Fonts/arial.ttf",         # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                font = ImageFont.truetype(font_path, size)
                break
        
        if not font:
            font = ImageFont.load_default()
        
        _font_cache[size] = font
        return font
        
    except Exception:
        return ImageFont.load_default()


async def create_hand_image(cards: List[UnoCard], assets_path: Path, organize_by_color: bool = True) -> Optional[str]:
    """
    Create an enhanced composite image showing all cards in a hand.
    Returns the path to the generated image file.
    """
    if not cards:
        return None
    
    try:
        start_time = time.time()
        
        # Organize cards by color for better visualization
        if organize_by_color:
            cards = _organize_cards_by_color(cards)
        
        # Load all card images with caching
        card_images = []
        card_width = 0
        card_height = 0
        
        for card in cards:
            card_path = assets_path / card.filename
            img = _load_cached_image(card_path)
            
            if img:
                card_images.append(img)
                if card_width == 0:  # Set dimensions from first card
                    card_width, card_height = img.size
            else:
                # Create placeholder image if card file doesn't exist
                placeholder = create_enhanced_placeholder_card(card, card_width or 100, card_height or 140)
                card_images.append(placeholder)
                if card_width == 0:
                    card_width, card_height = placeholder.size
        
        if not card_images:
            return None
        
        # Calculate final image dimensions with improved spacing
        overlap = max(20, card_width // 5)  # Better overlap ratio
        final_width = card_width + (len(card_images) - 1) * overlap + 20  # Add padding
        final_height = card_height + 40  # Add top/bottom padding
        
        # Create the composite image with background
        hand_image = Image.new('RGBA', (final_width, final_height), (40, 40, 40, 0))
        
        # Add subtle background
        bg = Image.new('RGBA', (final_width, final_height), (20, 20, 20, 180))
        hand_image = Image.alpha_composite(hand_image, bg)
        
        # Paste each card with overlap and slight rotation for visual appeal
        for i, card_img in enumerate(card_images):
            x_pos = 10 + i * overlap
            y_pos = 20
            
            # Add slight rotation for visual interest (optional)
            if len(card_images) > 5:
                rotation = (i - len(card_images) // 2) * 2  # Max 2 degrees rotation
                if rotation != 0:
                    card_img = card_img.rotate(rotation, expand=True, fillcolor=(0, 0, 0, 0))
            
            # Add drop shadow
            shadow = Image.new('RGBA', card_img.size, (0, 0, 0, 100))
            hand_image.paste(shadow, (x_pos + 2, y_pos + 2), shadow)
            
            # Paste the card
            hand_image.paste(card_img, (x_pos, y_pos), card_img if card_img.mode == 'RGBA' else None)
        
        # Add card count overlay
        draw = ImageDraw.Draw(hand_image)
        font = _get_font(16)
        text = f"{len(cards)} cards"
        
        # Get text size for positioning
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw text with outline
        text_x = final_width - text_width - 10
        text_y = 5
        
        # Outline
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=(0, 0, 0, 255))
        
        # Main text
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))
        
        # Save the composite image
        timestamp = int(time.time())
        output_path = assets_path / f"temp_hand_{timestamp}.png"
        hand_image.save(output_path, "PNG", optimize=True)
        
        # Performance logging
        end_time = time.time()
        print(f"Hand image created in {end_time - start_time:.2f}s ({len(cards)} cards)")
        
        return str(output_path)
        
    except Exception as e:
        print(f"Error creating hand image: {e}")
        return None


def _organize_cards_by_color(cards: List[UnoCard]) -> List[UnoCard]:
    """Organize cards by color for better hand visualization"""
    color_order = [UnoColor.RED, UnoColor.GREEN, UnoColor.YELLOW, UnoColor.BLUE, UnoColor.WILD]
    organized = []
    
    for color in color_order:
        color_cards = [card for card in cards if card.color == color]
        # Sort number cards numerically, action cards after
        color_cards.sort(key=lambda c: (
            c.card_type != UnoCardType.NUMBER,  # Numbers first
            c.value if c.card_type == UnoCardType.NUMBER else 100,  # Then by value
            c.card_type.value  # Then by type
        ))
        organized.extend(color_cards)
    
    return organized


def create_enhanced_placeholder_card(card: UnoCard, width: int = 100, height: int = 140) -> Image.Image:
    """Create an enhanced placeholder image for a missing card file"""
    # Color mapping with better colors
    color_map = {
        UnoColor.RED: (220, 20, 20),
        UnoColor.GREEN: (20, 180, 20),
        UnoColor.YELLOW: (255, 200, 20),
        UnoColor.BLUE: (20, 100, 220),
        UnoColor.WILD: (80, 80, 80)
    }
    
    # Create image with colored background
    bg_color = color_map.get(card.color, (150, 150, 150))
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle border
    border_color = tuple(max(0, c - 50) for c in bg_color)
    draw.rounded_rectangle([(2, 2), (width-3, height-3)], radius=8, outline=border_color, width=3)
    
    # Add card text
    if card.card_type == UnoCardType.NUMBER:
        main_text = str(card.value)
        sub_text = card.color.value[:3].upper()
    else:
        main_text = card.card_type.value.replace('_', '\n').upper()
        sub_text = card.color.value[:3].upper()
    
    # Draw main text (large)
    font_large = _get_font(min(width // 3, 24))
    font_small = _get_font(min(width // 6, 12))
    
    # Main text
    bbox = draw.textbbox((0, 0), main_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2 - 10
    
    # Text with shadow
    draw.text((text_x + 1, text_y + 1), main_text, font=font_large, fill=(0, 0, 0, 128))
    draw.text((text_x, text_y), main_text, font=font_large, fill=(255, 255, 255))
    
    # Sub text
    bbox = draw.textbbox((0, 0), sub_text, font=font_small)
    sub_width = bbox[2] - bbox[0]
    sub_x = (width - sub_width) // 2
    sub_y = text_y + text_height + 5
    
    draw.text((sub_x + 1, sub_y + 1), sub_text, font=font_small, fill=(0, 0, 0, 128))
    draw.text((sub_x, sub_y), sub_text, font=font_small, fill=(255, 255, 255))
    
    return img


def setup_assets_directory(cog_data_path: Path) -> Path:
    """Setup and return the assets directory path"""
    assets_path = cog_data_path / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)
    
    # Create a comprehensive readme file
    readme_path = assets_path / "README.md"
    if not readme_path.exists():
        readme_content = """# Uno Card Assets

Place your Uno card images in this directory using the following naming convention:

## Naming Convention:
- Number cards: `{Color}_{Number}.png` (e.g., `Red_5.png`, `Blue_0.png`)
- Skip cards: `{Color}_skip.png` (e.g., `Green_skip.png`)
- Reverse cards: `{Color}_reverse.png` (e.g., `Yellow_reverse.png`)
- Draw 2 cards: `{Color}_draw2.png` (e.g., `Red_draw2.png`)
- Wild cards: `Wild_Card.png`
- Wild Draw 4 cards: `Wild_draw4.png`

## Colors:
- Red
- Green  
- Yellow
- Blue
- Wild (for wild cards)

## Image Requirements:
- Format: PNG (recommended) or JPG
- Size: 100x140 pixels (recommended)
- Transparent background preferred for PNG files
- High quality for best visual results

## Performance Tips:
- Optimize images to reduce file size
- Use consistent dimensions across all cards
- PNG format with transparency works best

## Complete File List:
```
Number Cards (40 total):
Red_0.png, Red_1.png, Red_2.png, ..., Red_9.png
Green_0.png, Green_1.png, Green_2.png, ..., Green_9.png
Yellow_0.png, Yellow_1.png, Yellow_2.png, ..., Yellow_9.png
Blue_0.png, Blue_1.png, Blue_2.png, ..., Blue_9.png

Action Cards (24 total):
Red_skip.png, Red_reverse.png, Red_draw2.png
Green_skip.png, Green_reverse.png, Green_draw2.png
Yellow_skip.png, Yellow_reverse.png, Yellow_draw2.png
Blue_skip.png, Blue_reverse.png, Blue_draw2.png

Wild Cards (8 total):
Wild_Card.png
Wild_draw4.png
```

Total: 108 card files (matching standard Uno deck)

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
    Validate that all required card files exist with enhanced checking.
    Returns (missing_files, existing_files)
    """
    from .cards import UnoDeck
    
    # Create a deck to get all possible cards
    deck = UnoDeck()
    all_cards = deck.draw_pile.copy()
    
    missing_files = []
    existing_files = []
    corrupted_files = []
    
    # Check each card file
    for card in all_cards:
        card_path = assets_path / card.filename
        if card_path.exists():
            # Check if file is valid image
            try:
                with Image.open(card_path) as img:
                    img.verify()  # Verify it's a valid image
                existing_files.append(card.filename)
            except Exception:
                corrupted_files.append(card.filename)
                missing_files.append(f"{card.filename} (corrupted)")
        else:
            missing_files.append(card.filename)
    
    return missing_files, existing_files


async def cleanup_temp_files(assets_path: Path, max_age_minutes: int = 60):
    """Clean up temporary image files with age-based cleanup"""
    try:
        current_time = time.time()
        max_age_seconds = max_age_minutes * 60
        
        temp_files = list(assets_path.glob("temp_*.png"))
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


def clear_image_cache():
    """Clear the image cache to free memory"""
    global _card_image_cache
    _card_image_cache.clear()
    print("Image cache cleared")


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
            "game_history_size": len(self.game_history),
            "memory_usage": {
                "cached_images": len(_card_image_cache),
                "cached_fonts": len(_font_cache)
            }
        }


# Global instances
game_manager = EnhancedGameManager()
stats_manager = StatisticsManager()