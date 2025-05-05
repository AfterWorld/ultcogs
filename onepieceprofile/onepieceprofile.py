import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.data_manager import bundled_data_path, cog_data_path
import asyncio
import aiohttp
import os
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import datetime
import math
import random
from typing import Optional, Union, Dict, List, Tuple, Any

class OnePieceProfile(commands.Cog):
    """
    One Piece themed profile card with integration for Vert's LevelUp cog
    Displays user level, custom staff ranks, sea role, and generates wanted posters
    Inspired by AAA3A's OnePieceBounties cog
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=9271627862453, force_registration=True)
        
        # Default guild settings
        default_guild = {
            "staff_roles": ["Admin", "Moderator", "Helper"],
            "sea_roles": {
                "East Blue": {"color": "#3498db"},
                "West Blue": {"color": "#2ecc71"},
                "North Blue": {"color": "#9b59b6"},
                "South Blue": {"color": "#e74c3c"},
                "Grand Line": {"color": "#f1c40f"},
                "New World": {"color": "#e67e22"}
            },
            "pirate_ranks": {
                "1": ":moneybag: Chore Boy [LVL 1]",
                "5": ":moneybag: Petty Officer [LVL 5]",
                "10": ":moneybag: Chief Petty Officer [LVL 10]",
                "15": ":moneybag: Warrant Officer [LVL 15]",
                "20": ":moneybag: Lieutenant [LVL 20]",
                "25": ":moneybag: Captain [LVL 25]",
                "30": ":moneybag: Commodore [LVL 30]",
                "35": ":moneybag: Rear Admiral [LVL 35]"
                "40": ":moneybag: Vice Admiral [LVL 40]",
                "45": ":moneybag: Buggy's Right-hand [LVL 45]",
                "50": ":moneybag: Kidd's Right-Hand [LVL 50]",
                "55": ":moneybag: Law's Right-Hand [LVL 55]",
                "65": ":moneybag: Shanks's Right-Hand [LVL 65]",
                "70": ":moneybag: Luffy's Right-Hand [LVL 70]",
                "100": ":moneybag: WORLDS WORST CRIMINAL [LVL 100]",
            },
            "use_default_images": True,
            "custom_background": None
        }
        
        self.config.register_guild(**default_guild)
        self.session = None  # Will be initialized in initialize()
        
        # Set up paths
        self.data_path = cog_data_path(self)
        self.font_path = os.path.join(self.data_path, "fonts")
        self.image_path = os.path.join(self.data_path, "images")
        
        # Create directories if they don't exist
        for path in [self.font_path, self.image_path]:
            if not os.path.exists(path):
                os.makedirs(path)
    
    async def initialize(self):
        """Initialize the cog - sets up the ClientSession"""
        self.session = aiohttp.ClientSession()
        
    async def cog_load(self):
        """Called when the cog is loaded"""
        await self.initialize()
    
    def cog_unload(self):
        """Called when the cog is unloaded - closes the ClientSession"""
        if self.session:
            asyncio.create_task(self.session.close())
    
    async def get_levelup_data(self, member: discord.Member) -> Optional[Dict[str, Any]]:
        """Get level data from Vert's LevelUp cog"""
        levelup = self.bot.get_cog("LevelUp")
        if not levelup:
            return None
        
        try:
            # Attempt to use LevelUp API - this may need adjusting based on the actual API
            user_data = await levelup.data.member(member).all()
            if "level" not in user_data:
                return None
                
            # Get rank
            rank = await levelup.get_guild_leaderboard(member.guild)
            user_rank = 0
            for i, user_entry in enumerate(rank):
                if user_entry["user_id"] == member.id:
                    user_rank = i + 1
                    break
                    
            # Calculate XP needed for next level
            next_level_xp = levelup._required_exp(user_data["level"] + 1)
            current_level_xp = levelup._required_exp(user_data["level"])
            xp_needed = next_level_xp - current_level_xp
            
            return {
                "level": user_data["level"],
                "xp": user_data["exp"] - current_level_xp,
                "total_xp": user_data["exp"],
                "xp_needed": xp_needed,
                "rank": user_rank
            }
        except Exception as e:
            print(f"Error getting LevelUp data: {e}")
            return None
    
    async def get_staff_role(self, member: discord.Member) -> Optional[str]:
        """Check if member has a staff role"""
        staff_roles = await self.config.guild(member.guild).staff_roles()
        
        for role in member.roles:
            if role.name in staff_roles:
                return role.name
        return None
    
    async def get_sea_role(self, member: discord.Member) -> Tuple[str, str]:
        """Get member's sea role based on their assigned roles"""
        sea_roles = await self.config.guild(member.guild).sea_roles()
        
        # Default sea role if none is found
        default_sea = "East Blue"
        default_color = sea_roles[default_sea]["color"]
        
        # Check if member has a role that matches a sea role name
        for role in member.roles:
            if role.name in sea_roles:
                return role.name, sea_roles[role.name]["color"]
        
        # Return default if no sea role is found
        return default_sea, default_color
    
    async def get_pirate_rank(self, level: int, guild: discord.Guild) -> str:
        """Get pirate rank based on level"""
        pirate_ranks = await self.config.guild(guild).pirate_ranks()
        
        rank_name = pirate_ranks["0"]  # Default rank
        for req_level, name in sorted(pirate_ranks.items(), key=lambda x: int(x[0])):
            if level >= int(req_level):
                rank_name = name
            else:
                break
                
        return rank_name
    
    async def calculate_bounty(self, member: discord.Member, level: int, xp: int) -> int:
        """Calculate bounty based on level, XP, and time in server"""
        # Fixed multipliers instead of configurable ones
        # These provide a good balance for bounty calculation
        bounty_multiplier = 10000000  # Per level
        xp_multiplier = 10000        # Per XP point
        time_multiplier = 50000      # Per day in server
        
        # Calculate days in server
        days_in_server = 0
        if member.joined_at:
            delta = datetime.datetime.now(datetime.timezone.utc) - member.joined_at
            days_in_server = delta.days
        
        # Calculate base bounty from level and XP
        base_bounty = level * bounty_multiplier + xp * xp_multiplier
        
        # Add time component
        time_component = days_in_server * time_multiplier
        
        # Add random fluctuation (±10%)
        fluctuation = random.uniform(0.9, 1.1)
        
        # Calculate final bounty
        bounty = int((base_bounty + time_component) * fluctuation)
        
        return bounty
    
    async def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Load a font with fallback to default"""
        try:
            if bold:
                return ImageFont.truetype(os.path.join(self.font_path, "arial_bold.ttf"), size)
            else:
                return ImageFont.truetype(os.path.join(self.font_path, "arial.ttf"), size)
        except:
            # Fallback to default
            return ImageFont.load_default()
    
    async def _get_avatar(self, member: discord.Member) -> Optional[BytesIO]:
        """Download and process member's avatar"""
        if self.session is None:
            await self.initialize()
            
        avatar_url = str(member.display_avatar.url)
        if not avatar_url:
            # Create empty avatar if none exists
            img = Image.new("RGBA", (128, 128), (100, 100, 100, 255))
            buffer = BytesIO()
            img.save(buffer, "PNG")
            buffer.seek(0)
            return buffer
            
        try:
            async with self.session.get(avatar_url) as resp:
                if resp.status != 200:
                    return None
                avatar_bytes = await resp.read()
                return BytesIO(avatar_bytes)
        except:
            return None
    
    @commands.group(name="opwanted")
    @commands.guild_only()
    async def _wanted(self, ctx: commands.Context):
        """One Piece wanted poster commands"""
        pass
    
    @_wanted.command(name="poster")
    @commands.guild_only()
    async def wanted_poster(self, ctx: commands.Context, *, member: Optional[discord.Member] = None):
        """
        Display a One Piece themed wanted poster
        
        Shows your bounty based on level, XP, and time in server
        """
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            # Get level data from LevelUp cog
            level_data = await self.get_levelup_data(member)
            
            if not level_data:
                # Default values if no level data is available
                level_data = {
                    "level": 1,
                    "xp": 0,
                    "xp_needed": 100,
                    "rank": 0
                }
                
            # Calculate bounty
            bounty = await self.calculate_bounty(
                member, 
                level_data["level"], 
                level_data.get("xp", 0)
            )
            bounty_formatted = f"{bounty:,} Berries"
            
            # Create wanted poster image
            img_buffer = await self.create_wanted_poster(member, bounty_formatted)
            
            file = discord.File(img_buffer, filename="wanted.png")
            await ctx.send(file=file)
    
    @_wanted.command(name="profile")
    @commands.guild_only()
    async def nakama_profile(self, ctx: commands.Context, *, member: Optional[discord.Member] = None):
        """
        Display a detailed One Piece themed profile card
        
        Shows level, XP, pirate rank, sea, and more
        """
        if member is None:
            member = ctx.author
            
        async with ctx.typing():
            # Get level data from LevelUp cog
            level_data = await self.get_levelup_data(member)
            
            if not level_data:
                # Default values if no level data is available
                level_data = {
                    "level": 1,
                    "xp": 0,
                    "xp_needed": 100,
                    "rank": 0
                }
                
            # Get staff role
            staff_role = await self.get_staff_role(member)
            
            # Get sea role and color
            sea_role, sea_color = await self.get_sea_role(member)
            
            # Get pirate rank
            pirate_rank = await self.get_pirate_rank(level_data["level"], member.guild)
            
            # Calculate bounty
            bounty = await self.calculate_bounty(
                member, 
                level_data["level"], 
                level_data.get("xp", 0)
            )
            bounty_formatted = f"{bounty:,} Berries"
            
            # Create profile image
            img_buffer = await self.create_profile_image(
                member, 
                level_data["level"], 
                level_data.get("xp", 0), 
                level_data.get("xp_needed", 100), 
                level_data.get("rank", 0), 
                staff_role, 
                pirate_rank, 
                sea_role,
                sea_color,
                bounty_formatted
            )
            
            file = discord.File(img_buffer, filename="profile.png")
            await ctx.send(file=file)
    
    @commands.group(name="profileset")
    @commands.guild_only()
    @commands.admin()
    async def profile_settings(self, ctx: commands.Context):
        """Configure the One Piece Profile settings"""
        pass
        
    @profile_settings.command(name="staffrole")
    async def set_staff_role(self, ctx: commands.Context, *, role_name: str):
        """Add a role to the staff roles list"""
        async with self.config.guild(ctx.guild).staff_roles() as staff_roles:
            if role_name in staff_roles:
                await ctx.send(f"`{role_name}` is already in the staff roles list.")
                return
                
            staff_roles.append(role_name)
            await ctx.send(f"Added `{role_name}` to the staff roles list.")
            
    @profile_settings.command(name="removestaffrole")
    async def remove_staff_role(self, ctx: commands.Context, *, role_name: str):
        """Remove a role from the staff roles list"""
        async with self.config.guild(ctx.guild).staff_roles() as staff_roles:
            if role_name not in staff_roles:
                await ctx.send(f"`{role_name}` is not in the staff roles list.")
                return
                
            staff_roles.remove(role_name)
            await ctx.send(f"Removed `{role_name}` from the staff roles list.")
    
    @profile_settings.command(name="searole")
    async def set_sea_role(self, ctx: commands.Context, name: str, color: str):
        """Set a sea role with a custom color"""
        if not color.startswith("#"):
            color = f"#{color}"
        
        # Validate hex color
        try:
            int(color.replace("#", ""), 16)
        except ValueError:
            await ctx.send("Invalid color hex code. Please use a format like #3498db")
            return
            
        async with self.config.guild(ctx.guild).sea_roles() as sea_roles:
            sea_roles[name] = {
                "color": color
            }
            await ctx.send(f"Set `{name}` as a sea role with color {color}")
    
    @profile_settings.command(name="removesearole")
    async def remove_sea_role(self, ctx: commands.Context, *, name: str):
        """Remove a sea role from settings"""
        async with self.config.guild(ctx.guild).sea_roles() as sea_roles:
            if name not in sea_roles:
                await ctx.send(f"`{name}` is not in the sea roles list.")
                return
                
            del sea_roles[name]
            await ctx.send(f"Removed `{name}` from the sea roles list.")
            
    @profile_settings.command(name="piraterank")
    async def set_pirate_rank(self, ctx: commands.Context, level: int, *, rank_name: str):
        """Set a pirate rank for a specific level requirement"""
        async with self.config.guild(ctx.guild).pirate_ranks() as pirate_ranks:
            pirate_ranks[str(level)] = rank_name
            await ctx.send(f"Set `{rank_name}` as the pirate rank for level {level}+")
            
        # Multiplier commands removed as they're now fixed in the config
            
    @profile_settings.command(name="showsettings")
    async def show_settings(self, ctx: commands.Context):
        """Show current One Piece Profile settings"""
        settings = await self.config.guild(ctx.guild).all()
        
        # Format pirate ranks
        pirate_ranks_formatted = "\n".join(
            [f"Level {level}+: {rank}" for level, rank in sorted(
                settings["pirate_ranks"].items(), key=lambda x: int(x[0])
            )]
        )
        
        # Format sea roles
        sea_roles_formatted = "\n".join(
            [f"{sea}: {data['color']}" for sea, data in sorted(
                settings["sea_roles"].items(), key=lambda x: x[0]
            )]
        )
        
        embed = discord.Embed(
            title="One Piece Profile Settings",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Staff Roles", value=", ".join(settings["staff_roles"]) or "None", inline=False)
        embed.add_field(name="Pirate Ranks", value=pirate_ranks_formatted, inline=False)
        embed.add_field(name="Sea Roles", value=sea_roles_formatted, inline=False)
        
        await ctx.send(embed=embed)
    
    async def create_wanted_poster(self, member: discord.Member, bounty: str) -> BytesIO:
        """Create a One Piece wanted poster image"""
        # Base canvas size for wanted poster
        width, height = 600, 800
        
        # Create a new image with a parchment background
        image = Image.new("RGB", (width, height), (222, 184, 135))
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        title_font = await self._get_font(60, bold=True)
        name_font = await self._get_font(40, bold=True)
        bounty_font = await self._get_font(32)
        
        # Create wanted poster effect
        # Top banner with "WANTED" text
        draw.rectangle((0, 0, width, 100), fill=(139, 69, 19))
        draw.text(
            (width // 2, 50),
            "WANTED",
            fill=(255, 223, 0),
            font=title_font,
            anchor="mm"
        )
        
        # Draw border
        border_width = 10
        draw.rectangle(
            (border_width, border_width, width - border_width, height - border_width),
            outline=(139, 69, 19),
            width=border_width
        )
        
        # Draw "DEAD OR ALIVE" text
        draw.text(
            (width // 2, 130),
            "DEAD OR ALIVE",
            fill=(139, 69, 19),
            font=bounty_font,
            anchor="mm"
        )
        
        # Get user avatar
        avatar_bytes = await self._get_avatar(member)
        
        try:
            # Process avatar
            if avatar_bytes:
                avatar_img = Image.open(avatar_bytes)
                avatar_size = 300
                avatar_img = avatar_img.resize((avatar_size, avatar_size))
                
                # Paste avatar onto main image
                image.paste(avatar_img, ((width - avatar_size) // 2, 180))
            else:
                # If avatar can't be loaded, draw a placeholder rectangle
                avatar_size = 300
                draw.rectangle(
                    ((width - avatar_size) // 2, 180, 
                     (width - avatar_size) // 2 + avatar_size, 180 + avatar_size),
                    fill=(200, 200, 200)
                )
        except:
            # If any error occurs, draw a placeholder rectangle
            avatar_size = 300
            draw.rectangle(
                ((width - avatar_size) // 2, 180, 
                 (width - avatar_size) // 2 + avatar_size, 180 + avatar_size),
                fill=(200, 200, 200)
            )
            
        # Draw username
        draw.text(
            (width // 2, 520),
            member.display_name,
            fill=(0, 0, 0),
            font=name_font,
            anchor="mm"
        )
        
        # Draw bounty text
        draw.text(
            (width // 2, 600),
            f"Bounty: {bounty}",
            fill=(0, 0, 0),
            font=bounty_font,
            anchor="mm"
        )
        
        # Add "Issued by the World Government" text
        draw.text(
            (width // 2, 700),
            "Issued by the World Government",
            fill=(0, 0, 0),
            font=bounty_font,
            anchor="mm"
        )
        
        # Draw marine logo watermark
        # This is simplified - just a circle with cross
        watermark_size = 100
        center_x = width // 2
        center_y = height - 150
        
        # Semi-transparent white background
        draw.ellipse(
            (center_x - watermark_size//2, center_y - watermark_size//2,
             center_x + watermark_size//2, center_y + watermark_size//2),
            fill=(255, 255, 255, 128),
            outline=(0, 0, 0, 200)
        )
        
        # Cross
        line_width = 5
        draw.line(
            [(center_x, center_y - watermark_size//2 + 10),
             (center_x, center_y + watermark_size//2 - 10)],
            fill=(0, 0, 0, 200),
            width=line_width
        )
        draw.line(
            [(center_x - watermark_size//2 + 10, center_y),
             (center_x + watermark_size//2 - 10, center_y)],
            fill=(0, 0, 0, 200),
            width=line_width
        )
        
        # Add some weathered texture effect
        for _ in range(100):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            size = random.randint(1, 5)
            color = (
                random.randint(180, 220),
                random.randint(150, 180),
                random.randint(100, 135),
                random.randint(50, 150)
            )
            draw.ellipse(
                (x, y, x+size, y+size),
                fill=color
            )
        
        # Convert image to bytes
        buffer = BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        
        return buffer
        
    async def create_profile_image(
        self,
        member: discord.Member,
        level: int,
        xp: int,
        xp_needed: int,
        rank: int,
        staff_role: Optional[str],
        pirate_rank: str,
        sea_role: str,
        sea_color: str,
        bounty: str
    ) -> BytesIO:
        """Create a One Piece themed profile image"""
        # Base canvas size
        width, height = 800, 400
        
        # Try to parse sea_color
        try:
            sea_color_rgb = tuple(int(sea_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            sea_color_rgb = (sea_color_rgb[0], sea_color_rgb[1], sea_color_rgb[2], 255)
        except:
            # Default to blue if parsing fails
            sea_color_rgb = (52, 152, 219, 255)
        
        # Create a new image with a dark background
        image = Image.new("RGBA", (width, height), (45, 55, 72, 255))
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        title_font = await self._get_font(40, bold=True)
        regular_font = await self._get_font(24)
        small_font = await self._get_font(18)
            
        # Draw banner gradient with sea color influence
        for x in range(width):
            # Create a gradient from sea color to darker version
            r = max(0, min(255, int(sea_color_rgb[0] - (sea_color_rgb[0] * 0.5) * (x / width))))
            g = max(0, min(255, int(sea_color_rgb[1] - (sea_color_rgb[1] * 0.5) * (x / width))))
            b = max(0, min(255, int(sea_color_rgb[2] - (sea_color_rgb[2] * 0.5) * (x / width))))
            draw.line([(x, 0), (x, 120)], fill=(r, g, b, 255))
            
        # Get user avatar
        avatar_bytes = await self._get_avatar(member)
        
        try:
            # Process avatar
            if avatar_bytes:
                avatar_img = Image.open(avatar_bytes)
                avatar_img = avatar_img.resize((120, 120))
                
                # Create circular mask for avatar
                mask = Image.new("L", (120, 120), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 120, 120), fill=255)
                
                # Apply circular mask to avatar
                avatar_circle = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
                avatar_circle.paste(avatar_img, (0, 0), mask)
                
                # Paste avatar onto main image
                image.paste(avatar_circle, (40, 60), avatar_circle)
            else:
                # If avatar can't be loaded, draw a placeholder circle
                draw.ellipse((40, 60, 160, 180), fill=(200, 200, 200, 255))
        except:
            # If any error occurs, draw a placeholder circle
            draw.ellipse((40, 60, 160, 180), fill=(200, 200, 200, 255))
            
        # Draw username
        draw.text((180, 140), member.display_name, fill=(255, 255, 255, 255), font=title_font)
        
        # Draw sea role indicator
        draw.text(
            (180, 190),
            f"Sea: {sea_role}",
            fill=sea_color_rgb,
            font=regular_font
        )
        
        # Draw level badge
        level_badge_x, level_badge_y = 680, 60
        level_badge_size = 80
        draw.ellipse(
            (level_badge_x, level_badge_y, 
             level_badge_x + level_badge_size, level_badge_y + level_badge_size), 
            fill=(66, 153, 225, 255)
        )
        draw.ellipse(
            (level_badge_x + 5, level_badge_y + 5, 
             level_badge_x + level_badge_size - 5, level_badge_y + level_badge_size - 5), 
            outline=(246, 224, 94, 255), width=4
        )
        
        # Draw level text
        level_text = f"LVL {level}"
        text_w = title_font.getsize(level_text)[0] if hasattr(title_font, "getsize") else 0
        draw.text(
            (level_badge_x + (level_badge_size - text_w) // 2, level_badge_y + 30),
            level_text, fill=(255, 255, 255, 255), font=regular_font
        )
        
        # Draw XP bar
        xp_bar_x, xp_bar_y = 180, 230
        xp_bar_width, xp_bar_height = 560, 30
        
        # Background bar
        draw.rectangle(
            (xp_bar_x, xp_bar_y, xp_bar_x + xp_bar_width, xp_bar_y + xp_bar_height),
            fill=(70, 70, 70, 255)
        )
        
        # Progress bar
        if xp_needed > 0:
            progress_width = int((xp / xp_needed) * xp_bar_width)
        else:
            progress_width = xp_bar_width
            
        for px in range(progress_width):
            # Create a gradient from blue to purple
            r = int(66 + (129 - 66) * (px / xp_bar_width))
            g = int(153 + (96 - 153) * (px / xp_bar_width))
            b = int(225 + (225 - 225) * (px / xp_bar_width))
            draw.line(
                [(xp_bar_x + px, xp_bar_y), (xp_bar_x + px, xp_bar_y + xp_bar_height)],
                fill=(r, g, b, 255)
            )
            
        # XP text
        xp_text = f"XP: {xp}/{xp_needed}"
        draw.text(
            (xp_bar_x, xp_bar_y - 25),
            xp_text, fill=(200, 200, 200, 255), font=small_font
        )
        
        # Rank text
        rank_text = f"Rank #{rank}" if rank > 0 else "Unranked"
        rank_text_width = small_font.getsize(rank_text)[0] if hasattr(small_font, "getsize") else 0
        draw.text(
            (xp_bar_x + xp_bar_width - rank_text_width, xp_bar_y - 25),
            rank_text, fill=(200, 200, 200, 255), font=small_font
        )
        
        # Staff role badge (if any)
        if staff_role:
            staff_badge_x, staff_badge_y = 180, 280
            staff_text = staff_role.upper()
            staff_text_width = small_font.getsize(staff_text)[0] if hasattr(small_font, "getsize") else 0
            
            # Draw badge background
            draw.rectangle(
                (staff_badge_x, staff_badge_y,
                 staff_badge_x + staff_text_width + 20, staff_badge_y + 25),
                fill=(229, 62, 62, 255)
            )
            
            # Draw badge text
            draw.text(
                (staff_badge_x + 10, staff_badge_y + 3),
                staff_text, fill=(255, 255, 255, 255), font=small_font
            )
            
        # Pirate rank
        draw.text(
            (xp_bar_x, xp_bar_y + 50),
            f"Pirate Rank: {pirate_rank}", fill=(255, 255, 255, 255), font=regular_font
        )
        
        # Bounty
        bounty_y = xp_bar_y + 90
        draw.rectangle(
            (xp_bar_x, bounty_y, xp_bar_x + xp_bar_width, bounty_y + 40),
            fill=(102, 51, 0, 80), outline=(246, 224, 94, 255), width=2
        )
        
        draw.text(
            (xp_bar_x + 10, bounty_y + 8),
            f"BOUNTY: {bounty}", fill=(246, 224, 94, 255), font=regular_font
        )
        
        # Join date
        join_date = member.joined_at.strftime("%B %d, %Y") if member.joined_at else "Unknown"
        draw.text(
            (xp_bar_x, xp_bar_y + 140),
            f"Joined the crew: {join_date}", fill=(180, 180, 180, 255), font=small_font
        )
        
        # Draw Straw Hat Jolly Roger in the top right
        jolly_roger_size = 60
        jolly_roger_x = width - jolly_roger_size - 20
        jolly_roger_y = 20
        
        # Draw the skull circle
        draw.ellipse(
            (jolly_roger_x, jolly_roger_y, 
             jolly_roger_x + jolly_roger_size, jolly_roger_y + jolly_roger_size),
            fill=(0, 0, 0, 180)
        )
        
        # Draw the crossbones
        draw.line(
            [(jolly_roger_x + 15, jolly_roger_y + jolly_roger_size//2),
             (jolly_roger_x + jolly_roger_size - 15, jolly_roger_y + jolly_roger_size//2)],
            fill=(255, 255, 255, 255), width=5
        )
        draw.line(
            [(jolly_roger_x + jolly_roger_size//2, jolly_roger_y + 15),
             (jolly_roger_x + jolly_roger_size//2, jolly_roger_y + jolly_roger_size - 15)],
            fill=(255, 255, 255, 255), width=5
        )
        
        # Add some One Piece themed decorative elements
        # Devil Fruit swirl pattern in bottom left
        swirl_size = 100
        swirl_x = 30
        swirl_y = height - 120
        
        # Draw simplified devil fruit swirl
        for i in range(0, 361, 30):
            radius = swirl_size / 2 - (i / 360) * 20
            angle = math.radians(i)
            x1 = swirl_x + swirl_size/2 + radius * math.cos(angle)
            y1 = swirl_y + swirl_size/2 + radius * math.sin(angle)
            x2 = swirl_x + swirl_size/2 + radius * math.cos(angle + math.radians(20))
            y2 = swirl_y + swirl_size/2 + radius * math.sin(angle + math.radians(20))
            draw.line([(x1, y1), (x2, y2)], fill=(100, 50, 50, 80), width=3)
        
        # Convert image to bytes
        buffer = BytesIO()
        image.save(buffer, "PNG")
        buffer.seek(0)
        
        return buffer
