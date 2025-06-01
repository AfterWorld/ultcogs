# image_handler.py - CLEAN FIXED VERSION WITHOUT SYNTAX ERRORS
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
    
    def __init__(self, bot, base_path: str = None, enable_emojis: bool = True):
        self.bot = bot
        self.enable_emojis = enable_emojis  # Allow emoji rendering to be toggled
        
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
        self.round_position = (400, 210)           # Round number - right after "Round :"
        self.event_area = (60, 320, 940, 380)      # Event text area - in the orange horizontal bar  
        self.players_position = (680, 957)         # Remaining players - in the white box at bottom
        
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
        logger.info(f"Emoji rendering {'enabled' if self.enable_emojis else 'disabled'}")
    
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
        """Load font with fallbacks including emoji support"""
        font_options = [
            # Try emoji-capable fonts first
            "/System/Library/Fonts/Apple Color Emoji.ttc",  # macOS
            "/usr/share/fonts/truetype/noto-color-emoji/NotoColorEmoji.ttf",  # Linux
            "/Windows/Fonts/seguiemj.ttf",  # Windows emoji font
            # Custom fonts in the fonts directory
            self.font_path / "arial-bold.ttf" if bold else self.font_path / "arial.ttf",
            self.font_path / "DejaVuSans-Bold.ttf" if bold else self.font_path / "DejaVuSans.ttf",
            # System fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Noto fonts (good emoji support)
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/opentype/noto/NotoColorEmoji.ttf",
            # Standard fallbacks
            "arial.ttf",
            "DejaVuSans.ttf",
        ]
        
        for font_path in font_options:
            try:
                if Path(font_path).exists() or isinstance(font_path, str):
                    font = ImageFont.truetype(str(font_path), size)
                    logger.debug(f"Successfully loaded font: {font_path}")
                    return font
            except Exception:
                continue
        
        # Final fallback to default font
        logger.warning(f"Could not load any custom fonts, using default for size {size}")
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
            
            # Clean event text first
            clean_event_text = self._clean_event_text(event_text)
            logger.debug(f"Cleaned event text: {clean_event_text}")
            
            # Draw round number (positioned right after "Round :")
            round_text = str(round_num)
            self._draw_centered_text(
                draw, round_text, self.round_position, 
                self.round_font, self.round_color
            )
            logger.debug(f"Drew round number '{round_text}' at {self.round_position}")
            
            # Draw event text (in the orange horizontal bar)
            self._draw_wrapped_text(
                draw, clean_event_text, self.event_area, 
                self.event_font, self.event_color
            )
            logger.debug(f"Drew event text in area {self.event_area}")
            
            # Draw remaining players (in the white box at bottom)
            players_text = str(remaining_players)
            self._draw_centered_text(
                draw, players_text, self.players_position,
                self.players_font, self.players_color, use_outline=False  # No outline for black text on white
            )
            logger.debug(f"Drew players count '{players_text}' at {self.players_position}")
            
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
        """Draw text with word wrapping in specified area, with emoji support"""
        try:
            x1, y1, x2, y2 = area
            area_width = x2 - x1
            area_height = y2 - y1
            
            # Test if emojis can be rendered with this font
            text_to_render = self._test_emoji_rendering(draw, text, font)
            
            # Calculate approximate characters per line
            avg_char_width = self._get_average_char_width(font)
            chars_per_line = max(20, int(area_width / avg_char_width))  # Increased minimum
            
            # Wrap text - try to fit in 2-3 lines max
            wrapped_lines = textwrap.fill(text_to_render, width=chars_per_line).split('\n')
            
            # If too many lines, try with more characters per line
            if len(wrapped_lines) > 3:
                chars_per_line = int(chars_per_line * 1.5)
                wrapped_lines = textwrap.fill(text_to_render, width=chars_per_line).split('\n')
            
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
            # Fallback to simple text without emojis
            fallback_text = self._strip_emojis(text)
            truncated_text = fallback_text[:60] + "..." if len(fallback_text) > 60 else fallback_text
            # Center the fallback text
            fallback_x = x1 + (area_width - len(truncated_text) * 8) // 2  # Rough estimate
            fallback_y = y1 + (area_height // 2)
            self._draw_text_with_outline(draw, (fallback_x, fallback_y), truncated_text, font, color)
    
    def _test_emoji_rendering(self, draw: ImageDraw.Draw, text: str, font: ImageFont.ImageFont) -> str:
        """Test if emojis can be rendered, fallback to no-emoji version if needed"""
        if not self.enable_emojis:
            return self._strip_emojis(text)
            
        try:
            # Try to get text dimensions with emojis
            bbox = draw.textbbox((0, 0), text, font=font)
            # If this succeeds without error, emojis should render fine
            logger.debug("Emoji rendering test passed")
            return text
        except Exception as e:
            logger.debug(f"Emoji rendering failed, falling back to text only: {e}")
            return self._strip_emojis(text)
    
    def _strip_emojis(self, text: str) -> str:
        """Strip emojis as fallback if rendering fails"""
        try:
            # Remove common emoji patterns and keep just the text
            if "|" in text:
                parts = text.split("|", 1)
                if len(parts) > 1:
                    return parts[1].strip()
            return text
        except Exception:
            return text
    
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
        """Clean event text for display while preserving emojis"""
        try:
            # Remove markdown formatting but keep emojis
            text = text.replace("**", "").replace("__", "").replace("~~", "")
            
            if self.enable_emojis:
                # Keep the emoji but remove just the pipe separator
                if "|" in text:
                    parts = text.split("|", 1)
                    if len(parts) > 1:
                        # Keep the emoji part (before |) and the text part (after |)
                        emoji_part = parts[0].strip()
                        text_part = parts[1].strip()
                        text = f"{emoji_part} {text_part}"
            else:
                # Strip emojis if disabled
                text = self._strip_emojis(text)
            
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
    
    def create_debug_image(self, round_num: int = 5, event_text: str = "💀 Test event text with emoji", 
                          remaining_players: int = 12) -> Optional[discord.File]:
        """Create debug image showing positioning guides"""
        try:
            if not self.template_path.exists():
                logger.warning(f"Template image not found at {self.template_path}")
                return None
            
            template = Image.open(self.template_path).convert("RGBA")
            draw = ImageDraw.Draw(template)
            
            # Draw positioning guides
            # Round position marker (small red circle)
            x, y = self.round_position
            draw.ellipse([x-5, y-5, x+5, y+5], fill=(255, 0, 0, 128))
            
            # Event area marker (red rectangle outline)
            x1, y1, x2, y2 = self.event_area
            draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0, 128), width=2)
            
            # Players position marker (small blue circle)
            x, y = self.players_position
            draw.ellipse([x-5, y-5, x+5, y+5], fill=(0, 0, 255, 128))
            
            # Add coordinate labels
            small_font = self._load_font(12)
            draw.text((self.round_position[0]+10, self.round_position[1]), 
                     f"Round: {self.round_position}", font=small_font, fill=(255, 0, 0))
            draw.text((self.event_area[0], self.event_area[1]-15), 
                     f"Event Area: {self.event_area}", font=small_font, fill=(255, 0, 0))
            draw.text((self.players_position[0]+10, self.players_position[1]), 
                     f"Players: {self.players_position}", font=small_font, fill=(0, 0, 255))
            
            # Now draw the actual text
            clean_event_text = self._clean_event_text(event_text)
            
            # Round number
            self._draw_centered_text(draw, str(round_num), self.round_position, 
                                   self.round_font, self.round_color)
            
            # Event text
            self._draw_wrapped_text(draw, clean_event_text, self.event_area, 
                                  self.event_font, self.event_color)
            
            # Players count
            self._draw_centered_text(draw, str(remaining_players), self.players_position,
                                   self.players_font, self.players_color, use_outline=False)
            
            # Convert to Discord file
            img_buffer = io.BytesIO()
            template.save(img_buffer, format='PNG', optimize=True)
            img_buffer.seek(0)
            
            return discord.File(img_buffer, filename="debug_round_display.png")
            
        except Exception as e:
            logger.error(f"Error creating debug image: {e}")
            return None
    
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
    
    def update_positions(self, round_pos: tuple = None, event_area: tuple = None, 
                        players_pos: tuple = None):
        """Update text positions for fine-tuning"""
        if round_pos:
            self.round_position = round_pos
            logger.info(f"Updated round position to: {round_pos}")
        if event_area:
            self.event_area = event_area
            logger.info(f"Updated event area to: {event_area}")
        if players_pos:
            self.players_position = players_pos
            logger.info(f"Updated players position to: {players_pos}")
