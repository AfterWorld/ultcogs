import io
import aiohttp
import asyncio
import logging
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageEnhance

log = logging.getLogger("red.optcg.utils")

async def fetch_image(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """Fetch an image from a URL."""
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                log.error(f"Failed to fetch image from {url}: {resp.status}")
                return None
            
            return await resp.read()
    except Exception as e:
        log.error(f"Error fetching image from {url}: {e}")
        return None

async def create_silhouette(session: aiohttp.ClientSession, image_url: str) -> Optional[io.BytesIO]:
    """Create a silhouette version of the card image."""
    image_data = await fetch_image(session, image_url)
    if not image_data:
        return None
    
    # Process the image in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _process_silhouette, image_data)
    except Exception as e:
        log.error(f"Error creating silhouette: {e}")
        return None

def _process_silhouette(image_data: bytes) -> io.BytesIO:
    """Process the image to create a silhouette (runs in a thread pool)."""
    img = Image.open(io.BytesIO(image_data))
    
    # Convert to grayscale
    img = img.convert("L")
    
    # Increase contrast to enhance the silhouette effect
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(3.0)
    
    # Apply threshold to make it truly black and white
    threshold = 100
    img = img.point(lambda p: 0 if p < threshold else 255)
    
    # Convert back to RGB for compatibility
    img = img.convert("RGB")
    
    # Apply a slight blur to smooth edges
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Save to BytesIO
    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    
    return output

async def get_card_stats(card_data: dict) -> Tuple[int, int, int]:
    """Calculate stats for battle system based on card data."""
    # Basic stats calculation based on card properties
    attack = card_data.get("power", 0)
    if isinstance(attack, str) and attack.isdigit():
        attack = int(attack)
    elif not isinstance(attack, int):
        attack = 0
    
    defense = 0
    if card_data.get("counter", "-") != "-":
        try:
            defense = int(card_data["counter"])
        except (ValueError, TypeError):
            defense = attack // 2
    else:
        defense = attack // 2
    
    # Cost as a factor in health calculation
    cost = card_data.get("cost", 1)
    if isinstance(cost, str) and cost.isdigit():
        cost = int(cost)
    elif not isinstance(cost, int):
        cost = 1
    
    health = cost * 1000 + attack // 2
    
    # Rarity bonuses
    rarity_multipliers = {
        "C": 1.0,    # Common
        "U": 1.2,    # Uncommon
        "R": 1.4,    # Rare
        "SR": 1.7,   # Super Rare
        "SEC": 2.0,  # Secret
        "L": 2.2     # Leader
    }
    
    rarity = card_data.get("rarity", "C")
    multiplier = rarity_multipliers.get(rarity, 1.0)
    
    attack = int(attack * multiplier)
    defense = int(defense * multiplier)
    health = int(health * multiplier)
    
    return attack, defense, health
