# image_handler.py - NEW FILE
"""
Custom Image Round Display System for Hunger Games
Overlays round info, events, and player count onto custom background image
"""

import discord
import logging
import asyncio
import textwrap
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)

class ImageRoundHandler:
    """Handles creation of custom round display images"""
    
    def __init__(self, bot, base_path: str = None):
        self.bot = bot
        
        # Set up paths
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path("data") / "hunger_games_images"
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Image settings
        self.template_path = self.base_path / "round_template.png"
        self.font_path = self.base_path / "fonts"
        self.font_path.mkdir(exist_ok=True)
        
        # Text positioning (adjust these based on your image dimensions)
        self.round_position = (400, 80)  # Round number position
        self.event_area = (50, 150, 750, 350)  # Event text area (x1, y1, x2, y2)
        self.players_position = (400, 450)  # Remaining players position
        
        # Text settings
        self.round_font_size = 48
        self.event_font_size = 24
        self.players_font_size = 32
        
        # Colors (adjust to match your design)
        self.round_color = (255, 255, 255)  # White
        self.event_color = (255, 255, 255)  # White
        self.players_color = (255, 255, 255)  # White
        
        self._setup_fonts()
    
    def _setup_fonts(self):
        """Set up fonts with fallbacks"""
        try:
            # Try to load custom fonts, fall back to default
            self.round_font = self._load_font(self.round_font_size)
            self.event_font = self._load_font(self.event_font_size)
            self.players_font = self._load_font(self.players_font_size)
        except Exception as e:
            logger.warning(f"Font setup error: {e}")
            # Use PIL's default font as fallback
            self.round_font = ImageFont.load_default()
            self.event_font = ImageFont.load_default()
            self.players_font = ImageFont.load_default()
    
    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load font with fallbacks"""
        font_options = [
            self.font_path / "arial.ttf",
            self.font_path / "arial-bold.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
        ]
        
        for font_path in font_options:
            try:
                if Path(font_path).exists() or isinstance(font_path, str):
                    return ImageFont.truetype(str(font_path), size)
            except Exception:
                continue
        
        # Final fallback to default font
        return ImageFont.load_default()
    
    def save_template_image(self, image_data: bytes) -> bool:
        """Save the uploaded template image"""
        try:
            with open(self.template_path, 'wb') as f:
                f.write(image_data)
            logger.info(f"Template image saved to {self.template_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving template image: {e}")
            return False
    
    def create_round_image(self, round_num: int, event_text: str, 
                          remaining_players: int) -> Optional[discord.File]:
        """Create round display image with overlaid text"""
        try:
            # Check if template exists
            if not self.template_path.exists():
                logger.warning("Template image not found")
                return None
            
            # Load template image
            template = Image.open(self.template_path).convert("RGBA")
            
            # Create drawing context
            draw = ImageDraw.Draw(template)
            
            # Draw round number
            round_text = str(round_num)
            self._draw_centered_text(
                draw, round_text, self.round_position, 
                self.round_font, self.round_color
            )
            
            # Draw event text (with word wrapping)
            self._draw_wrapped_text(
                draw, event_text, self.event_area, 
                self.event_font, self.event_color
            )
            
            # Draw remaining players
            players_text = str(remaining_players)
            self._draw_centered_text(
                draw, players_text, self.players_position,
                self.players_font, self.players_color
            )
            
            # Convert to Discord file
            img_buffer = io.BytesIO()
            template.save(img_buffer, format='PNG', optimize=True)
            img_buffer.seek(0)
            
            return discord.File(img_buffer, filename="round_display.png")
            
        except Exception as e:
            logger.error(f"Error creating round image: {e}")
            return None
    
    def _draw_centered_text(self, draw: ImageDraw.Draw, text: str, 
                           position: Tuple[int, int], font: ImageFont.ImageFont, 
                           color: Tuple[int, int, int]):
        """Draw text centered at position"""
        try:
            # Get text dimensions
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate centered position
            x = position[0] - (text_width // 2)
            y = position[1] - (text_height // 2)
            
            # Draw text with outline for better visibility
            self._draw_text_with_outline(draw, (x, y), text, font, color)
            
        except Exception as e:
            logger.error(f"Error drawing centered text: {e}")
            # Fallback to simple text
            draw.text(position, text, font=font, fill=color)
    
    def _draw_wrapped_text(self, draw: ImageDraw.Draw, text: str, 
                          area: Tuple[int, int, int, int], font: ImageFont.ImageFont,
                          color: Tuple[int, int, int]):
        """Draw text with word wrapping in specified area"""
        try:
            x1, y1, x2, y2 = area
            area_width = x2 - x1
            area_height = y2 - y1
            
            # Clean and prepare text
            clean_text = self._clean_event_text(text)
            
            # Calculate approximate characters per line
            avg_char_width = self._get_average_char_width(font)
            chars_per_line = int(area_width / avg_char_width)
            
            # Wrap text
            wrapped_lines = textwrap.fill(clean_text, width=chars_per_line).split('\n')
            
            # Calculate line height
            line_height = font.getsize("Ay")[1] + 4  # Add some padding
            total_text_height = len(wrapped_lines) * line_height
            
            # Center text vertically in area
            start_y = y1 + (area_height - total_text_height) // 2
            
            # Draw each line
            for i, line in enumerate(wrapped_lines):
                line_y = start_y + (i * line_height)
                
                # Center line horizontally
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = x1 + (area_width - line_width) // 2
                
                # Draw with outline
                self._draw_text_with_outline(draw, (line_x, line_y), line, font, color)
                
                # Stop if we're running out of space
                if line_y + line_height > y2:
                    break
                    
        except Exception as e:
            logger.error(f"Error drawing wrapped text: {e}")
            # Fallback to simple text
            draw.text((area[0], area[1]), text[:100], font=font, fill=color)
    
    def _draw_text_with_outline(self, draw: ImageDraw.Draw, position: Tuple[int, int],
                               text: str, font: ImageFont.ImageFont, 
                               color: Tuple[int, int, int], outline_color: Tuple[int, int, int] = (0, 0, 0)):
        """Draw text with outline for better visibility"""
        x, y = position
        
        # Draw outline (offset in 8 directions)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=color)
    
    def _clean_event_text(self, text: str) -> str:
        """Clean event text for display"""
        # Remove markdown formatting
        text = text.replace("**", "").replace("__", "").replace("~~", "")
        
        # Remove emojis at the start
        if "|" in text:
            text = text.split("|", 1)[1].strip()
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        return text
    
    def _get_average_char_width(self, font: ImageFont.ImageFont) -> float:
        """Get average character width for the font"""
        try:
            # Sample text to measure
            sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            bbox = font.getbbox(sample)
            width = bbox[2] - bbox[0]
            return width / len(sample)
        except Exception:
            return 10  # Fallback value
    
    def is_available(self) -> bool:
        """Check if the image system is available"""
        return self.template_path.exists()
    
    def get_template_path(self) -> str:
        """Get the template image path for admin commands"""
        return str(self.template_path)
