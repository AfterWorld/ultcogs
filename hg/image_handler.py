# image_handler.py - FIXED VERSION WITH CORRECT POSITIONING
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
        
        # Set up paths - use the specific path provided
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to the user's specific path structure
            self.base_path = Path("/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/CogManager/cogs/hg/Images")
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Image settings
        self.template_path = self.base_path / "eventsmockup.png"
        self.font_path = self.base_path / "fonts"
        self.font_path.mkdir(exist_ok=True)
        
        # CORRECTED TEXT POSITIONING based on your image layout
        self.round_position = (350, 210)           # Round number - right after "Round :"
        self.event_area = (60, 300, 940, 380)      # Event text area - in the orange horizontal bar
        self.players_position = (550, 957)         # Remaining players - in the white box at bottom
        
        # Text settings - adjusted for better fit
        self.round_font_size = 42                  # Slightly larger for round number
        self.event_font_size = 18                  # Smaller for event text to fit in bar
        self.players_font_size = 24                # Medium size for player count
        
        # Colors (white text with dark outline for visibility)
        self.round_color = (255, 255, 255)        # White
        self.event_color = (255, 255, 255)        # White  
        self.players_color = (0, 0, 0)             # Black for the white box area
        self.outline_color = (0, 0, 0)             # Black outline
        
        self._setup_fonts()
        
        # Log initialization
        logger.info(f"ImageRoundHandler initialized with template path: {self.template_path}")
    
    def _setup_fonts(self):
        """Set up fonts with fallbacks"""
        try:
            # Try to load custom fonts, fall back to default
            self.round_font = self._load_font(self.round_font_size, bold=True)
            self.event_font = self._load_font(self.event_font_size)
            self.players_font = self._load_font(self.players_font_size, bold=True)
        except Exception as e:
            logger.warning(f"Font setup error: {e}")
            # Use PIL's default font as fallback
            self.round_font = ImageFont.load_default()
            self.event_font = ImageFont.load_default()
            self.players_font = ImageFont.load_default()
    
    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load font with fallbacks"""
        font_options = [
            # Custom fonts in the fonts directory
            self.font_path / "arial-bold.ttf" if bold else self.font_path / "arial.ttf",
            self.font_path / "DejaVuSans-Bold.ttf" if bold else self.font_path / "DejaVuSans.ttf",
            # System fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
        ]
        
        for font_path in font_options:
            try:
                if Path(font_path).exists() or isinstance(font_path, str):
                    return ImageFont.truetype(str(font_path), size)
            except Exception:
                continue
        
        # Final fallback to default font
        logger.warning(f"Could not load custom font, using default for size {size}")
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
                logger.warning(f"Template image not found at {self.template_path}")
                return None
            
            # Load template image
            template = Image.open(self.template_path).convert("RGBA")
            logger.debug(f"Loaded template image: {template.size}")
            
            # Create drawing context
            draw = ImageDraw.Draw(template)
            
            # Draw round number (positioned right after "Round :")
            round_text = str(round_num)
            self._draw_centered_text(
                draw, round_text, self.round_position, 
                self.round_font, self.round_color
            )
            logger.debug(f"Drew round number: {round_text}")
            
            # Draw event text (in the orange horizontal bar)
            clean_event_text = self._clean_event_text(event_text)
            self._draw_wrapped_text(
                draw, clean_event_text, self.event_area, 
                self.event_font, self.event_color
            )
            logger.debug(f"Drew event text: {clean_event_text[:50]}...")
            
            # Draw remaining players (in the white box at bottom)
            players_text = str(remaining_players)
            self._draw_centered_text(
                draw, players_text, self.players_position,
                self.players_font, self.players_color, use_outline=False  # No outline for black text on white
            )
            logger.debug(f"Drew players count: {players_text}")
            
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
                           color: Tuple[int, int, int], use_outline: bool = True):
        """Draw text centered at position"""
        try:
            # Get text dimensions
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate centered position
            x = position[0] - (text_width // 2)
            y = position[1] - (text_height // 2)
            
            # Draw text with or without outline
            if use_outline:
                self._draw_text_with_outline(draw, (x, y), text, font, color)
            else:
                draw.text((x, y), text, font=font, fill=color)
            
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
            
            # Calculate approximate characters per line
            avg_char_width = self._get_average_char_width(font)
            chars_per_line = max(20, int(area_width / avg_char_width))  # Increased minimum
            
            # Wrap text - try to fit in 2-3 lines max
            wrapped_lines = textwrap.fill(text, width=chars_per_line).split('\n')
            
            # If too many lines, try with more characters per line
            if len(wrapped_lines) > 3:
                chars_per_line = int(chars_per_line * 1.5)
                wrapped_lines = textwrap.fill(text, width=chars_per_line).split('\n')
            
            # Limit to 3 lines maximum
            if len(wrapped_lines) > 3:
                wrapped_lines = wrapped_lines[:2]
                if len(wrapped_lines) == 2:
                    wrapped_lines[1] = wrapped_lines[1][:50] + "..."
            
            # Calculate line height
            line_height = self._get_line_height(font)
            total_text_height = len(wrapped_lines) * line_height
            
            # Center text vertically in area
            start_y = y1 + max(0, (area_height - total_text_height) // 2)
            
            # Draw each line
            for i, line in enumerate(wrapped_lines):
                line_y = start_y + (i * line_height)
                
                # Stop if we're running out of space
                if line_y + line_height > y2:
                    break
                
                # Center line horizontally
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                line_x = x1 + (area_width - line_width) // 2
                
                # Draw with outline
                self._draw_text_with_outline(draw, (line_x, line_y), line, font, color)
                    
        except Exception as e:
            logger.error(f"Error drawing wrapped text: {e}")
            # Fallback to simple text
            truncated_text = text[:60] + "..." if len(text) > 60 else text
            # Center the fallback text
            fallback_x = x1 + (area_width - len(truncated_text) * 8) // 2  # Rough estimate
            fallback_y = y1 + (area_height // 2)
            self._draw_text_with_outline(draw, (fallback_x, fallback_y), truncated_text, font, color)
    
    def _draw_text_with_outline(self, draw: ImageDraw.Draw, position: Tuple[int, int],
                               text: str, font: ImageFont.ImageFont, 
                               color: Tuple[int, int, int]):
        """Draw text with outline for better visibility"""
        x, y = position
        
        # Draw outline (offset in 8 directions) - smaller outline for better look
        outline_width = 1
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=self.outline_color)
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=color)
    
    def _clean_event_text(self, text: str) -> str:
        """Clean event text for display"""
        try:
            # Remove markdown formatting
            text = text.replace("**", "").replace("__", "").replace("~~", "")
            
            # Remove emojis at the start and pipe separators
            if "|" in text:
                parts = text.split("|", 1)
                if len(parts) > 1:
                    text = parts[1].strip()
            
            # Remove extra whitespace
            text = " ".join(text.split())
            
            # Limit length for display in the orange bar
            if len(text) > 150:
                text = text[:147] + "..."
            
            return text
        except Exception as e:
            logger.error(f"Error cleaning event text: {e}")
            return text[:80]  # Safe fallback
    
    def _get_average_char_width(self, font: ImageFont.ImageFont) -> float:
        """Get average character width for the font"""
        try:
            # Sample text to measure
            sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
            bbox = font.getbbox(sample)
            width = bbox[2] - bbox[0]
            return max(1, width / len(sample))
        except Exception:
            return 6  # Smaller fallback value for tighter text
    
    def _get_line_height(self, font: ImageFont.ImageFont) -> int:
        """Get line height for the font"""
        try:
            bbox = font.getbbox("Ay")
            return (bbox[3] - bbox[1]) + 2  # Less padding for tighter fit
        except Exception:
            return 18  # Smaller fallback value
    
    def is_available(self) -> bool:
        """Check if the image system is available"""
        return self.template_path.exists()
    
    def get_template_path(self) -> str:
        """Get the template image path for admin commands"""
        return str(self.template_path)
    
    def get_template_info(self) -> dict:
        """Get information about the current template"""
        try:
            if not self.is_available():
                return {"exists": False}
            
            template = Image.open(self.template_path)
            return {
                "exists": True,
                "size": template.size,
                "mode": template.mode,
                "format": template.format,
                "path": str(self.template_path)
            }
        except Exception as e:
            logger.error(f"Error getting template info: {e}")
            return {"exists": False, "error": str(e)}
