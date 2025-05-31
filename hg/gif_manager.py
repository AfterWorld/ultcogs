# gif_manager.py - FIXED VERSION WITH PROPER DIRECTORY HANDLING
"""
Complete GIF Management System for Hunger Games
Handles GIF selection, loading, and integration with Discord embeds
"""

import os
import random
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import discord
from redbot.core import commands, Config

logger = logging.getLogger(__name__)

class GifManager:
    """Handles all GIF-related functionality for the Hunger Games bot"""
    
    def __init__(self, bot, config, base_path: str = None):
        self.bot = bot
        self.config = config
        
        # Use provided path or default to a safe location
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Default to a subdirectory in the current directory
            self.base_path = Path("data") / "gifs"
        
        self.gif_cache = {}
        self.last_cache_update = 0
        self.cache_timeout = 300  # 5 minutes
        
        # Create directory structure if it doesn't exist (with error handling)
        self._create_directory_structure()
        
        # GIF categories and their subdirectories
        self.gif_structure = {
            "victory": {
                "general": "General victory celebrations",
                "high_kill": "Domination/massacre victories (5+ kills)",
                "medium_kill": "Skilled warrior victories (3-4 kills)", 
                "low_kill": "Strategic victories (1-2 kills)",
                "no_kill": "Peaceful/survival victories (0 kills)",
                "underdog": "Against-all-odds victories",
                "final_duel": "1v1 final showdown victories",
                "bloodbath": "Overwhelming massacre victories"
            },
            "death": {
                "general": "General elimination/death scenes",
                "brutal": "Violent/brutal deaths",
                "accident": "Accidental/environmental deaths",
                "betrayal": "Betrayal/backstab deaths",
                "heroic": "Noble/heroic deaths"
            },
            "sponsor": {
                "gift": "Gift/package deliveries",
                "revival": "Resurrection/revival scenes",
                "equipment": "Weapon/gear deliveries",
                "food": "Food/healing deliveries"
            },
            "alliance": {
                "formation": "Alliance/team formation",
                "betrayal": "Alliance betrayals",
                "cooperation": "Teamwork/cooperation"
            },
            "special": {
                "bloodbath": "Opening Cornucopia bloodbath",
                "finale": "Final showdown scenes",
                "feast": "Arena feast events",
                "environmental": "Arena hazard events"
            }
        }
    
    def _create_directory_structure(self):
        """Create the GIF directory structure with proper error handling"""
        try:
            # Create base directory first
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Create category directories
            for category in ["victory", "death", "sponsor", "alliance", "special"]:
                category_path = self.base_path / category
                category_path.mkdir(exist_ok=True)
                
                # Create subdirectories based on structure
                if category in self.gif_structure:
                    for subcategory in self.gif_structure[category]:
                        subcategory_path = category_path / subcategory
                        subcategory_path.mkdir(exist_ok=True)
            
            logger.info(f"GIF directory structure created at {self.base_path}")
            
            # Create a README file with instructions
            readme_path = self.base_path / "README.md"
            if not readme_path.exists():
                readme_content = """# Hunger Games GIF Directory

This directory contains GIFs that are automatically selected during Hunger Games events.

## Directory Structure

### victory/
- **general/** - General victory celebrations
- **high_kill/** - Domination/massacre victories (5+ kills)
- **medium_kill/** - Skilled warrior victories (3-4 kills)
- **low_kill/** - Strategic victories (1-2 kills)
- **no_kill/** - Peaceful/survival victories (0 kills)
- **underdog/** - Against-all-odds victories
- **final_duel/** - 1v1 final showdown victories
- **bloodbath/** - Overwhelming massacre victories

### death/
- **general/** - General elimination/death scenes
- **brutal/** - Violent/brutal deaths
- **accident/** - Accidental/environmental deaths
- **betrayal/** - Betrayal/backstab deaths
- **heroic/** - Noble/heroic deaths

### sponsor/
- **gift/** - Gift/package deliveries
- **revival/** - Resurrection/revival scenes
- **equipment/** - Weapon/gear deliveries
- **food/** - Food/healing deliveries

### alliance/
- **formation/** - Alliance/team formation
- **betrayal/** - Alliance betrayals
- **cooperation/** - Teamwork/cooperation

### special/
- **bloodbath/** - Opening Cornucopia bloodbath
- **finale/** - Final showdown scenes
- **feast/** - Arena feast events
- **environmental/** - Arena hazard events

## Supported Formats
- `.gif` - Standard GIF files
- `.webp` - WebP animated images
- `.mp4` - MP4 video files
- `.mov` - QuickTime video files

## Usage
1. Place GIF files in the appropriate subdirectories
2. Use `.hungergames gif stats` to verify files are detected
3. Enable GIF integration with `.hungergames gif enable`
4. GIFs are automatically selected based on game context

## Commands
- `.hungergames gif enable` - Enable GIF integration
- `.hungergames gif disable` - Disable GIF integration
- `.hungergames gif stats` - Show GIF collection statistics
- `.hungergames gif structure` - Show this directory structure
- `.hungergames gif test [category] [subcategory]` - Test GIF selection
- `.hungergames gif reload` - Reload GIF cache
"""
                try:
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(readme_content)
                except Exception as e:
                    logger.warning(f"Could not create README file: {e}")
            
        except PermissionError as e:
            logger.error(f"Permission denied creating GIF directory structure: {e}")
            logger.error(f"Please ensure the bot has write permissions to: {self.base_path}")
        except Exception as e:
            logger.error(f"Error creating GIF directory structure: {e}")
    
    def _scan_gifs(self) -> Dict[str, Dict[str, List[str]]]:
        """Scan the GIF directories and return available GIFs"""
        try:
            gif_files = {}
            supported_formats = ['.gif', '.webp', '.mp4', '.mov']
            
            # Check if base directory exists
            if not self.base_path.exists():
                logger.warning(f"GIF base directory does not exist: {self.base_path}")
                return {}
            
            for category_dir in self.base_path.iterdir():
                if category_dir.is_dir() and not category_dir.name.startswith('.'):
                    category = category_dir.name
                    gif_files[category] = {}
                    
                    for subcategory_dir in category_dir.iterdir():
                        if subcategory_dir.is_dir() and not subcategory_dir.name.startswith('.'):
                            subcategory = subcategory_dir.name
                            files = []
                            
                            for file_path in subcategory_dir.iterdir():
                                if (file_path.is_file() and 
                                    file_path.suffix.lower() in supported_formats and
                                    not file_path.name.startswith('.')):
                                    files.append(str(file_path))
                            
                            if files:
                                gif_files[category][subcategory] = files
            
            return gif_files
        except Exception as e:
            logger.error(f"Error scanning GIFs: {e}")
            return {}
    
    def _get_cached_gifs(self) -> Dict[str, Dict[str, List[str]]]:
        """Get GIFs from cache or rescan if cache is stale"""
        current_time = asyncio.get_event_loop().time()
        
        if (not self.gif_cache or 
            current_time - self.last_cache_update > self.cache_timeout):
            self.gif_cache = self._scan_gifs()
            self.last_cache_update = current_time
        
        return self.gif_cache
    
    def get_victory_gif(self, game_data: Dict, winner_data: Dict) -> Optional[str]:
        """Select appropriate victory GIF based on game context"""
        try:
            gifs = self._get_cached_gifs()
            victory_gifs = gifs.get("victory", {})
            
            if not victory_gifs:
                return None
            
            # Determine victory type
            total_players = len(game_data.get("players", {}))
            kills = winner_data.get("kills", 0)
            
            # Priority order for GIF selection
            preferred_categories = []
            
            if total_players == 2:
                preferred_categories.append("final_duel")
            
            if kills >= 7:
                preferred_categories.append("bloodbath")
            elif kills >= 5:
                preferred_categories.append("high_kill")
            elif kills >= 3:
                preferred_categories.append("medium_kill")
            elif kills >= 1:
                preferred_categories.append("low_kill")
            elif kills == 0:
                preferred_categories.append("no_kill")
            
            if total_players <= 5:
                preferred_categories.append("underdog")
            
            # Always add general as fallback
            preferred_categories.append("general")
            
            # Try to find a GIF from preferred categories
            for category in preferred_categories:
                if category in victory_gifs and victory_gifs[category]:
                    selected_gif = random.choice(victory_gifs[category])
                    logger.debug(f"Selected victory GIF from {category}: {selected_gif}")
                    return selected_gif
            
            # Final fallback - any victory GIF
            all_victory_gifs = []
            for category_gifs in victory_gifs.values():
                all_victory_gifs.extend(category_gifs)
            
            if all_victory_gifs:
                selected_gif = random.choice(all_victory_gifs)
                logger.debug(f"Selected fallback victory GIF: {selected_gif}")
                return selected_gif
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting victory GIF: {e}")
            return None
    
    def get_death_gif(self, death_type: str = "general") -> Optional[str]:
        """Get a death/elimination GIF"""
        try:
            gifs = self._get_cached_gifs()
            death_gifs = gifs.get("death", {})
            
            if not death_gifs:
                return None
            
            # Try specific death type first
            if death_type in death_gifs and death_gifs[death_type]:
                selected_gif = random.choice(death_gifs[death_type])
                logger.debug(f"Selected death GIF from {death_type}: {selected_gif}")
                return selected_gif
            
            # Fallback to general death GIFs
            if "general" in death_gifs and death_gifs["general"]:
                selected_gif = random.choice(death_gifs["general"])
                logger.debug(f"Selected general death GIF: {selected_gif}")
                return selected_gif
            
            # Final fallback - any death GIF
            all_death_gifs = []
            for category_gifs in death_gifs.values():
                all_death_gifs.extend(category_gifs)
            
            if all_death_gifs:
                selected_gif = random.choice(all_death_gifs)
                logger.debug(f"Selected fallback death GIF: {selected_gif}")
                return selected_gif
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting death GIF: {e}")
            return None
    
    def get_sponsor_gif(self, sponsor_type: str = "gift") -> Optional[str]:
        """Get a sponsor/gift GIF"""
        try:
            gifs = self._get_cached_gifs()
            sponsor_gifs = gifs.get("sponsor", {})
            
            if not sponsor_gifs:
                return None
            
            # Try specific sponsor type
            if sponsor_type in sponsor_gifs and sponsor_gifs[sponsor_type]:
                selected_gif = random.choice(sponsor_gifs[sponsor_type])
                logger.debug(f"Selected sponsor GIF from {sponsor_type}: {selected_gif}")
                return selected_gif
            
            # Fallback to general gift GIFs
            if "gift" in sponsor_gifs and sponsor_gifs["gift"]:
                selected_gif = random.choice(sponsor_gifs["gift"])
                logger.debug(f"Selected general sponsor GIF: {selected_gif}")
                return selected_gif
            
            # Final fallback - any sponsor GIF
            all_sponsor_gifs = []
            for category_gifs in sponsor_gifs.values():
                all_sponsor_gifs.extend(category_gifs)
            
            if all_sponsor_gifs:
                selected_gif = random.choice(all_sponsor_gifs)
                logger.debug(f"Selected fallback sponsor GIF: {selected_gif}")
                return selected_gif
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting sponsor GIF: {e}")
            return None
    
    def get_special_gif(self, event_type: str) -> Optional[str]:
        """Get a special event GIF (bloodbath, finale, etc.)"""
        try:
            gifs = self._get_cached_gifs()
            special_gifs = gifs.get("special", {})
            
            if not special_gifs:
                return None
            
            if event_type in special_gifs and special_gifs[event_type]:
                selected_gif = random.choice(special_gifs[event_type])
                logger.debug(f"Selected special GIF from {event_type}: {selected_gif}")
                return selected_gif
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting special GIF: {e}")
            return None
    
    def get_gif_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics about available GIFs"""
        try:
            gifs = self._get_cached_gifs()
            stats = {}
            
            for category, subcategories in gifs.items():
                stats[category] = {}
                for subcategory, gif_list in subcategories.items():
                    stats[category][subcategory] = len(gif_list)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting GIF stats: {e}")
            return {}
    
    def clear_cache(self):
        """Clear the GIF cache to force rescan"""
        self.gif_cache = {}
        self.last_cache_update = 0
        logger.debug("GIF cache cleared")
    
    def get_base_path(self) -> str:
        """Get the base path for GIF storage"""
        return str(self.base_path)
    
    def is_available(self) -> bool:
        """Check if the GIF system is properly set up and available"""
        try:
            return self.base_path.exists() and self.base_path.is_dir()
        except Exception:
            return False
    
    async def upload_gif_url(self, url: str, category: str, subcategory: str, filename: str) -> bool:
        """Helper method to download and save a GIF from URL (for admin commands)"""
        try:
            import aiohttp
            
            category_path = self.base_path / category / subcategory
            category_path.mkdir(parents=True, exist_ok=True)
            
            file_path = category_path / filename
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # Clear cache to include new GIF
                        self.clear_cache()
                        logger.info(f"Successfully uploaded GIF: {file_path}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error uploading GIF: {e}")
            return False
