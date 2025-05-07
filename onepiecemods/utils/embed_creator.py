import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

class EmbedCreator:
    """Utility class for creating stylized embeds for One Piece mod actions"""
    
    @staticmethod
    def kick_embed(user: discord.Member, mod: discord.Member, reason: Optional[str], message: str, gif: str) -> discord.Embed:
        """Create a kick embed with One Piece styling"""
        embed = discord.Embed(
            title="👊 Gomu Gomu no... KICK!",
            description=message,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Target", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Executed By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=gif)
        embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    @staticmethod
    def ban_embed(user: discord.Member, mod: discord.Member, reason: Optional[str], message: str, gif: str) -> discord.Embed:
        """Create a ban embed with One Piece styling"""
        embed = discord.Embed(
            title="⚔️ Yonko-Level Ban Executed!",
            description=message,
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Exiled Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Executed By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        if reason:
            embed.add_field(name="Reason for Exile", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=gif)
        embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    @staticmethod
    def mute_embed(user: discord.Member, mod: discord.Member, duration: int, reason: Optional[str], message: str, gif: str) -> discord.Embed:
        """Create a mute embed with One Piece styling"""
        embed = discord.Embed(
            title="🔇 Sea Prism Stone Applied!",
            description=message,
            color=discord.Color.dark_gray(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Silenced Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Applied By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        # Format duration
        time_str = f"{duration} minutes" if duration else "Indefinite"
        embed.add_field(name="Duration", value=time_str, inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=gif)
        embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    @staticmethod
    def warn_embed(user: discord.Member, mod: discord.Member, level: int, reason: Optional[str], 
                   message: str, gif: str, bounty_level: str, bounty_description: str) -> discord.Embed:
        """Create a warning embed with One Piece styling"""
        embed = discord.Embed(
            title=f"💰 Bounty Increased to {bounty_level}!",
            description=message,
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Reported By", value=f"{mod.mention} ({mod.name})", inline=True)
        embed.add_field(name="Current Level", value=f"Level {level}", inline=True)
        
        embed.add_field(name="Threat Level", value=bounty_description, inline=False)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=gif)
        embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    @staticmethod
    def impel_down_embed(user: discord.Member, mod: discord.Member, level: int, duration: int, 
                        reason: Optional[str], message: str, gif: str, level_data: Dict[str, Any]) -> discord.Embed:
        """Create an Impel Down imprisonment embed with One Piece styling"""
        level_name = level_data.get("name", f"Level {level}")
        level_description = level_data.get("description", "No description available")
        
        embed = discord.Embed(
            title=f"⛓️ Impel Down: {level_name}",
            description=message,
            color=discord.Color.dark_purple(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Prisoner", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Sentenced By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        # Format duration
        time_str = f"{duration} minutes" if duration else "Indefinite"
        embed.add_field(name="Sentence Duration", value=time_str, inline=True)
        
        # Add level description
        embed.add_field(name=f"Level {level} - {level_name}", value=level_description, inline=False)
        
        # Add restrictions
        restrictions = level_data.get("restrictions", [])
        if restrictions:
            embed.add_field(
                name="Restrictions",
                value=", ".join(restrictions) or "None",
                inline=False
            )
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url=gif)
        embed.set_footer(text=f"User ID: {user.id} • Release scheduled in {duration} minutes")
        
        return embed
