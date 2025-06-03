"""
Utility functions for Uno game
"""
import os
import asyncio
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw
import discord
from .cards import UnoCard, UnoColor, UnoCardType


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


async def create_hand_image(cards: List[UnoCard], assets_path: Path) -> Optional[str]:
    """
    Create a composite image showing all cards in a hand.
    Returns the path to the generated image file.
    """
    if not cards:
        return None
    
    try:
        # Load all card images
        card_images = []
        card_width = 0
        card_height = 0
        
        for card in cards:
            card_path = assets_path / card.filename
            if card_path.exists():
                img = Image.open(card_path)
                card_images.append(img)
                if card_width == 0:  # Set dimensions from first card
                    card_width, card_height = img.size
            else:
                # Create placeholder image if card file doesn't exist
                placeholder = create_placeholder_card(card, card_width or 100, card_height or 140)
                card_images.append(placeholder)
                if card_width == 0:
                    card_width, card_height = placeholder.size
        
        if not card_images:
            return None
        
        # Calculate final image dimensions
        overlap = max(1, card_width // 4)  # Cards overlap by 25%
        final_width = card_width + (len(card_images) - 1) * overlap
        final_height = card_height
        
        # Create the composite image
        hand_image = Image.new('RGBA', (final_width, final_height), (0, 0, 0, 0))
        
        # Paste each card with overlap
        for i, card_img in enumerate(card_images):
            x_pos = i * overlap
            hand_image.paste(card_img, (x_pos, 0), card_img if card_img.mode == 'RGBA' else None)
        
        # Save the composite image
        output_path = assets_path / "temp_hand.png"
        hand_image.save(output_path, "PNG")
        
        # Clean up loaded images
        for img in card_images:
            img.close()
        
        return str(output_path)
        
    except Exception as e:
        print(f"Error creating hand image: {e}")
        return None


def create_placeholder_card(card: UnoCard, width: int = 100, height: int = 140) -> Image.Image:
    """Create a placeholder image for a missing card file"""
    # Color mapping
    color_map = {
        UnoColor.RED: (220, 50, 50),
        UnoColor.GREEN: (50, 220, 50),
        UnoColor.YELLOW: (220, 220, 50),
        UnoColor.BLUE: (50, 50, 220),
        UnoColor.WILD: (100, 100, 100)
    }
    
    # Create image with colored background
    bg_color = color_map.get(card.color, (150, 150, 150))
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw border
    draw.rectangle([(2, 2), (width-3, height-3)], outline=(0, 0, 0), width=2)
    
    # Add text (simplified)
    text = str(card.value) if card.card_type == UnoCardType.NUMBER else card.card_type.value[:4].upper()
    
    # Calculate text position (center)
    bbox = draw.textbbox((0, 0), text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    draw.text((text_x, text_y), text, fill=(255, 255, 255))
    
    return img


def setup_assets_directory(cog_data_path: Path) -> Path:
    """Setup and return the assets directory path"""
    assets_path = cog_data_path / "assets"
    assets_path.mkdir(parents=True, exist_ok=True)
    
    # Create a readme file explaining the card naming convention
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

## Example Files:
```
Red_0.png, Red_1.png, ..., Red_9.png
Red_skip.png, Red_reverse.png, Red_draw2.png
Green_0.png, Green_1.png, ..., Green_9.png
Green_skip.png, Green_reverse.png, Green_draw2.png
Yellow_0.png, Yellow_1.png, ..., Yellow_9.png
Yellow_skip.png, Yellow_reverse.png, Yellow_draw2.png
Blue_0.png, Blue_1.png, ..., Blue_9.png
Blue_skip.png, Blue_reverse.png, Blue_draw2.png
Wild_Card.png
Wild_draw4.png
```

Note: All names are case-sensitive and use underscores as separators.
"""
        readme_path.write_text(readme_content)
    
    return assets_path


def format_player_list(players: List[int], current_player: Optional[int] = None) -> str:
    """Format a list of players for display"""
    if not players:
        return "No players"
    
    formatted = []
    for player_id in players:
        name = f"<@{player_id}>"
        if current_player and player_id == current_player:
            name = f"**{name}** 🎯"
        formatted.append(name)
    
    return "\n".join(formatted)


def format_card_counts(card_counts: dict, current_player: Optional[int] = None) -> str:
    """Format player card counts for display"""
    if not card_counts:
        return "No players"
    
    formatted = []
    for player_id, count in card_counts.items():
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
        
        formatted.append(line)
    
    return "\n".join(formatted)


def validate_card_files(assets_path: Path) -> tuple[List[str], List[str]]:
    """
    Validate that all required card files exist.
    Returns (missing_files, existing_files)
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


async def cleanup_temp_files(assets_path: Path):
    """Clean up temporary image files"""
    temp_files = list(assets_path.glob("temp_*.png"))
    for temp_file in temp_files:
        try:
            temp_file.unlink()
        except Exception:
            pass  # Ignore errors when cleaning up


class GameManager:
    """Manages multiple game sessions"""
    
    def __init__(self):
        self.games: dict[int, 'UnoGameSession'] = {}  # channel_id -> game_session
    
    def create_game(self, channel_id: int, host_id: int) -> Optional['UnoGameSession']:
        """Create a new game session"""
        if channel_id in self.games:
            # Check if existing game is finished or expired
            existing_game = self.games[channel_id]
            if existing_game.state != 'finished' and not existing_game.is_expired():
                return None  # Game already exists
        
        from .game import UnoGameSession
        game = UnoGameSession(channel_id, host_id)
        self.games[channel_id] = game
        return game
    
    def get_game(self, channel_id: int) -> Optional['UnoGameSession']:
        """Get existing game session"""
        return self.games.get(channel_id)
    
    def remove_game(self, channel_id: int) -> bool:
        """Remove a game session"""
        if channel_id in self.games:
            game = self.games[channel_id]
            game.cleanup()
            del self.games[channel_id]
            return True
        return False
    
    def cleanup_expired_games(self):
        """Remove expired games"""
        expired_channels = []
        for channel_id, game in self.games.items():
            if game.is_expired():
                expired_channels.append(channel_id)
        
        for channel_id in expired_channels:
            self.remove_game(channel_id)
        
        return len(expired_channels)
    
    def get_active_games_count(self) -> int:
        """Get number of active games"""
        return len([g for g in self.games.values() if g.state != 'finished'])
    
    def get_total_players(self) -> int:
        """Get total number of players across all games"""
        return sum(len(g.players) for g in self.games.values())


# Global game manager instance
game_manager = GameManager()