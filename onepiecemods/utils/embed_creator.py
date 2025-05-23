# onepiecemods/utils/embed_creator.py - Improved Version
import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

class EmbedCreator:
    """Utility class for creating stylized embeds for One Piece mod actions"""
    
    @staticmethod
    def _get_base_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
        """Create a base embed with common styling"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now()
        )
        return embed
    
    @staticmethod
    def _add_user_info(embed: discord.Embed, user: discord.Member, mod: discord.Member, reason: Optional[str]):
        """Add common user and moderator information to an embed"""
        embed.add_field(name="🎯 Target", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="⚔️ Executed By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        if reason:
            embed.add_field(name="📜 Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | One Piece Moderation System")
    
    @staticmethod
    def kick_embed(user: discord.Member, mod: discord.Member, reason: Optional[str], message: str, gif: str) -> discord.Embed:
        """Create a kick embed with One Piece styling"""
        embed = EmbedCreator._get_base_embed(
            title="👊 Gomu Gomu no... KICK!",
            description=message,
            color=discord.Color.orange()
        )
        
        EmbedCreator._add_user_info(embed, user, mod, reason)
        
        if gif:
            embed.set_image(url=gif)
        
        return embed
    
    @staticmethod
    def ban_embed(user: discord.Member, mod: discord.Member, reason: Optional[str], message: str, gif: str) -> discord.Embed:
        """Create a ban embed with One Piece styling"""
        embed = EmbedCreator._get_base_embed(
            title="⚔️ Yonko-Level Ban Executed!",
            description=message,
            color=discord.Color.dark_red()
        )
        
        embed.add_field(name="🏴‍☠️ Exiled Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="👑 Executed By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        if reason:
            embed.add_field(name="⚖️ Reason for Exile", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | Banished from the Grand Line")
        
        if gif:
            embed.set_image(url=gif)
        
        return embed
    
    @staticmethod
    def mute_embed(user: discord.Member, mod: discord.Member, duration: int, reason: Optional[str], 
                   message: str, gif: str) -> discord.Embed:
        """Create a mute embed with One Piece styling"""
        embed = EmbedCreator._get_base_embed(
            title="🔇 Sea Prism Stone Applied!",
            description=message,
            color=discord.Color.dark_gray()
        )
        
        embed.add_field(name="🤐 Silenced Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="🔗 Applied By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        # Format duration
        if duration:
            hours, minutes = divmod(duration, 60)
            if hours > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{minutes}m"
        else:
            time_str = "Indefinite"
            
        embed.add_field(name="⏰ Duration", value=time_str, inline=True)
        
        if reason:
            embed.add_field(name="📜 Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | Devil Fruit powers sealed")
        
        if gif:
            embed.set_image(url=gif)
        
        return embed
    
    @staticmethod
    def warn_embed(user: discord.Member, mod: discord.Member, level: int, reason: Optional[str], 
                   message: str, gif: str, bounty_level: str, bounty_description: str) -> discord.Embed:
        """Create a warning embed with One Piece styling"""
        embed = EmbedCreator._get_base_embed(
            title=f"💰 Bounty Increased to {bounty_level}!",
            description=message,
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🏴‍☠️ Pirate", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="🚨 Reported By", value=f"{mod.mention} ({mod.name})", inline=True)
        embed.add_field(name="📊 Current Level", value=f"Level {level}", inline=True)
        
        # Add bounty progression
        embed.add_field(name="⚡ Threat Level", value=bounty_description, inline=False)
        
        # Add escalation warning if approaching dangerous levels
        if level >= 3:
            embed.add_field(name="⚠️ Warning", value="This pirate is becoming dangerous! Watch carefully.", inline=False)
        
        if reason:
            embed.add_field(name="📜 Reason", value=reason, inline=False)
            
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | Marine Database Updated")
        
        if gif:
            embed.set_image(url=gif)
        
        return embed
    
    @staticmethod
    def impel_down_embed(user: discord.Member, mod: discord.Member, level: int, duration: int, 
                        reason: Optional[str], message: str, gif: str, level_data: Dict[str, Any]) -> discord.Embed:
        """Create an Impel Down imprisonment embed with One Piece styling"""
        level_name = level_data.get("name", f"Level {level}")
        level_description = level_data.get("description", "No description available")
        
        # Color gets darker with higher levels
        color_intensity = min(255, 50 + (level * 30))
        embed_color = discord.Color.from_rgb(color_intensity, 0, color_intensity // 2)
        
        embed = EmbedCreator._get_base_embed(
            title=f"⛓️ Impel Down: {level_name}",
            description=message,
            color=embed_color
        )
        
        embed.add_field(name="🔒 Prisoner", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="⚖️ Sentenced By", value=f"{mod.mention} ({mod.name})", inline=True)
        
        # Format duration
        if duration:
            hours, minutes = divmod(duration, 60)
            days, hours = divmod(hours, 24)
            
            duration_parts = []
            if days > 0:
                duration_parts.append(f"{days}d")
            if hours > 0:
                duration_parts.append(f"{hours}h")
            if minutes > 0:
                duration_parts.append(f"{minutes}m")
                
            time_str = " ".join(duration_parts) if duration_parts else "Less than 1m"
        else:
            time_str = "Indefinite"
            
        embed.add_field(name="⏰ Sentence Duration", value=time_str, inline=True)
        
        # Add level description with custom formatting
        embed.add_field(
            name=f"🏭 Level {level} - {level_name}", 
            value=level_description, 
            inline=False
        )
        
        # Add restrictions with emojis
        restrictions = level_data.get("restrictions", [])
        if restrictions:
            restriction_emojis = {
                "send_messages": "💬",
                "add_reactions": "😀",
                "speak": "🔊",
                "view_channel": "👁️"
            }
            
            restriction_text = ""
            for restriction in restrictions:
                emoji = restriction_emojis.get(restriction, "🚫")
                restriction_text += f"{emoji} {restriction.replace('_', ' ').title()}\n"
            
            embed.add_field(
                name="🚫 Restrictions Applied",
                value=restriction_text or "None",
                inline=False
            )
        
        if reason:
            embed.add_field(name="📜 Crime", value=reason, inline=False)
        
        # Add severity indicator
        severity_indicators = ["🟢", "🟡", "🟠", "🔴", "🟣", "⚫"]
        severity = severity_indicators[min(level - 1, len(severity_indicators) - 1)]
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id} | Severity: {severity} | Release in {time_str}")
        
        if gif:
            embed.set_image(url=gif)
        
        return embed
    
    @staticmethod
    def release_embed(user: discord.Member, mod: discord.Member, reason: Optional[str], 
                     previous_level: int) -> discord.Embed:
        """Create a release embed for early liberation"""
        embed = EmbedCreator._get_base_embed(
            title="🔓 Jailbreak! Released from Impel Down!",
            description=f"{user.mention} has been released from Impel Down by {mod.mention}!",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🏭 Previous Level", value=f"Level {previous_level}", inline=True)
        embed.add_field(name="🔑 Released By", value=f"{mod.mention} ({mod.name})", inline=True)
        embed.add_field(name="📜 Reason", value=reason or "No reason provided", inline=True)
        
        embed.add_field(name="✅ Status", value="All restrictions removed\nPrevious roles restored", inline=False)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_image(url="https://media.giphy.com/media/PBAl9H8B5Hali/giphy.gif")  # Prison break gif
        embed.set_footer(text=f"User ID: {user.id} | Freedom restored")
        
        return embed
    
    @staticmethod
    def error_embed(title: str, description: str, error_type: str = "Error") -> discord.Embed:
        """Create a standardized error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_footer(text=f"One Piece Moderation | {error_type}")
        
        return embed
    
    @staticmethod
    def success_embed(title: str, description: str) -> discord.Embed:
        """Create a standardized success embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.set_footer(text="One Piece Moderation | Success")
        
        return embed
    
    @staticmethod
    def info_embed(title: str, description: str) -> discord.Embed:
        """Create a standardized info embed"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_footer(text="One Piece Moderation | Information")
        
        return embed
