import io
import requests
import logging
from PIL import Image, ImageDraw, ImageFont

class ImageUtils:
    """Utilities for image generation and manipulation."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.TEMPLATE_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/deathbattle.png"
        self.FONT_PATH = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/BountyBattle/onepiece.ttf"
    
    def generate_fight_card(self, user1, user2):
        """
        Generates a dynamic fight card image with avatars and usernames.
        """
        # Open the local template image
        try:
            template = Image.open(self.TEMPLATE_PATH)
            draw = ImageDraw.Draw(template)
        except (FileNotFoundError, IOError):
            self.logger.error(f"Template image not found at {self.TEMPLATE_PATH}")
            # Create a fallback blank image
            template = Image.new('RGBA', (650, 500), color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(template)
            draw.text((50, 200), "Fight Card Template Missing", fill="black")

        # Load font
        try:
            username_font = ImageFont.truetype(self.FONT_PATH, 25)
        except (OSError, IOError):
            self.logger.warning(f"Font file not found at {self.FONT_PATH}, using default")
            username_font = ImageFont.load_default()

        # Avatar dimensions and positions
        avatar_size = (250, 260)  # Adjust as needed
        avatar_positions = [(15, 130), (358, 130)]  # Positions for avatars
        username_positions = [(75, 410), (430, 410)]  # Positions for usernames

        # Fetch and paste avatars
        for i, user in enumerate((user1, user2)):
            try:
                # Use a more efficient, direct approach to fetch avatars
                avatar_url = user.display_avatar.url
                
                # Use requests with a timeout
                avatar_response = requests.get(avatar_url, timeout=2)
                avatar = Image.open(io.BytesIO(avatar_response.content)).convert("RGBA")
                avatar = avatar.resize(avatar_size)
                
                # Paste avatar onto the template
                template.paste(avatar, avatar_positions[i], avatar)
                
                # Draw username
                username = user.display_name[:20]  # Limit username length
                draw.text(username_positions[i], username, font=username_font, fill="black")
            except Exception as e:
                self.logger.error(f"Error processing avatar for {user.display_name}: {e}")
                # Add a placeholder text instead
                draw.rectangle([avatar_positions[i], 
                                (avatar_positions[i][0] + avatar_size[0], 
                                avatar_positions[i][1] + avatar_size[1])], 
                                outline="black", fill="gray")
                draw.text((avatar_positions[i][0] + 50, avatar_positions[i][1] + 130), 
                        "Avatar Error", fill="black")

        # Save the image to a BytesIO object
        output = io.BytesIO()
        template.save(output, format="PNG", optimize=True)
        output.seek(0)

        return output
        
    def generate_health_bar(self, current_hp: int, max_hp: int = 250, length: int = 10) -> str:
        """Generate a health bar using Discord emotes based on current HP."""
        filled_length = int(length * current_hp // max_hp)
        bar = "🥩" * filled_length + "🦴" * (length - filled_length)
        return f"{bar}"