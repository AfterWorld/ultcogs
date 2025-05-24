# onepiecemods/utils/webhook_logger.py
import discord
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
from enum import Enum
import aiohttp

logger = logging.getLogger("red.onepiecemods.webhook")

class LogLevel(Enum):
    """Log levels for webhook logging"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    CRITICAL = "critical"

class WebhookLogger:
    """Advanced webhook logging system for One Piece Mods"""
    
    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        self._webhook_cache = {}  # Cache webhooks to avoid recreating
        self._rate_limits = {}     # Track rate limits per guild
        self._queue = {}          # Message queue per guild
        
        # Color mapping for different log levels
        self.level_colors = {
            LogLevel.INFO: discord.Color.blue(),
            LogLevel.WARNING: discord.Color.orange(),
            LogLevel.ERROR: discord.Color.red(),
            LogLevel.SUCCESS: discord.Color.green(),
            LogLevel.CRITICAL: discord.Color.dark_red()
        }
        
        # Emoji mapping for log levels (using Unicode escape sequences)
        self.level_emojis = {
            LogLevel.INFO: "\u2139\ufe0f",        # ℹ️
            LogLevel.WARNING: "\u26a0\ufe0f",     # ⚠️
            LogLevel.ERROR: "\u274c",             # ❌
            LogLevel.SUCCESS: "\u2705",           # ✅
            LogLevel.CRITICAL: "\U0001f6a8"       # 🚨
        }
    
    async def get_webhook(self, guild: discord.Guild) -> Optional[discord.Webhook]:
        """Get the configured webhook for a guild"""
        webhook_url = await self.config_manager.get_setting(guild, "webhook_url")
        
        if not webhook_url:
            return None
        
        # Check cache first
        if guild.id in self._webhook_cache:
            cached_webhook, cached_url = self._webhook_cache[guild.id]
            if cached_url == webhook_url:
                return cached_webhook
        
        try:
            # Use bot's session if available, otherwise create a new one
            session = getattr(self.bot, 'session', None)
            if session is None:
                # Create a temporary session for this webhook
                webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(aiohttp.ClientSession()))
            else:
                webhook = discord.Webhook.from_url(webhook_url, adapter=discord.AsyncWebhookAdapter(session))
            
            self._webhook_cache[guild.id] = (webhook, webhook_url)
            return webhook
        except Exception as e:
            logger.error(f"Failed to create webhook for guild {guild.id}: {e}")
            return None
    
    async def _check_rate_limit(self, guild: discord.Guild) -> bool:
        """Check if we're rate limited for this guild"""
        now = datetime.now().timestamp()
        
        if guild.id not in self._rate_limits:
            self._rate_limits[guild.id] = {"count": 0, "reset_time": now + 60}
            return False
        
        rate_limit_data = self._rate_limits[guild.id]
        
        # Reset counter if minute has passed
        if now >= rate_limit_data["reset_time"]:
            self._rate_limits[guild.id] = {"count": 0, "reset_time": now + 60}
            return False
        
        # Discord webhook rate limit is 30 requests per minute
        if rate_limit_data["count"] >= 25:  # Leave some buffer
            return True
        
        return False
    
    async def _increment_rate_limit(self, guild: discord.Guild):
        """Increment the rate limit counter"""
        if guild.id in self._rate_limits:
            self._rate_limits[guild.id]["count"] += 1
    
    async def _queue_message(self, guild: discord.Guild, embed: discord.Embed, content: str = None):
        """Queue a message for later sending if rate limited"""
        if guild.id not in self._queue:
            self._queue[guild.id] = []
        
        self._queue[guild.id].append({"embed": embed, "content": content, "timestamp": datetime.now()})
        
        # Limit queue size to prevent memory issues
        if len(self._queue[guild.id]) > 50:
            self._queue[guild.id] = self._queue[guild.id][-50:]
    
    async def _process_queue(self, guild: discord.Guild):
        """Process queued messages for a guild"""
        if guild.id not in self._queue or not self._queue[guild.id]:
            return
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return
        
        # Process up to 5 messages at once
        messages_to_send = self._queue[guild.id][:5]
        self._queue[guild.id] = self._queue[guild.id][5:]
        
        for message_data in messages_to_send:
            if await self._check_rate_limit(guild):
                # Still rate limited, put messages back
                self._queue[guild.id] = messages_to_send[messages_to_send.index(message_data):] + self._queue[guild.id]
                break
            
            try:
                await webhook.send(
                    embed=message_data["embed"],
                    content=message_data["content"],
                    username="One Piece Mods",
                    avatar_url="https://i.imgur.com/Wr8xdJA.png"
                )
                await self._increment_rate_limit(guild)
                await asyncio.sleep(0.5)  # Small delay between messages
            except Exception as e:
                logger.error(f"Failed to send queued webhook message: {e}")
    
    async def log_moderation_action(self, guild: discord.Guild, action_type: str, moderator: discord.Member,
                                  target: discord.Member, reason: str, case_number: Optional[int] = None,
                                  duration: Optional[str] = None, level: Optional[int] = None, **kwargs):
        """Log a moderation action via webhook"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        # Create embed
        embed = discord.Embed(
            title=f"\U0001f6e1\ufe0f Moderation Action: {action_type.title()}",  # 🛡️
            color=self._get_action_color(action_type),
            timestamp=datetime.now()
        )
        
        # Add basic information
        embed.add_field(name="\U0001f464 Target", value=f"{target.mention} ({target.id})", inline=True)  # 👤
        embed.add_field(name="\u2694\ufe0f Moderator", value=f"{moderator.mention} ({moderator.id})", inline=True)  # ⚔️
        
        if case_number:
            embed.add_field(name="\U0001f4cb Case", value=f"#{case_number}", inline=True)  # 📋
        
        if duration:
            embed.add_field(name="\u23f0 Duration", value=duration, inline=True)  # ⏰
        
        if level:
            embed.add_field(name="\U0001f4ca Level", value=f"Level {level}", inline=True)  # 📊
        
        embed.add_field(name="\U0001f4dc Reason", value=reason or "No reason provided", inline=False)  # 📜
        
        # Add extra fields
        for key, value in kwargs.items():
            if value is not None:
                formatted_key = key.replace("_", " ").title()
                embed.add_field(name=formatted_key, value=str(value), inline=True)
        
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def log_system_event(self, guild: discord.Guild, event_type: str, description: str,
                             level: LogLevel = LogLevel.INFO, **kwargs):
        """Log a system event via webhook"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title=f"{self.level_emojis[level]} System Event: {event_type}",
            description=description,
            color=self.level_colors[level],
            timestamp=datetime.now()
        )
        
        # Add extra fields
        for key, value in kwargs.items():
            if value is not None:
                formatted_key = key.replace("_", " ").title()
                embed.add_field(name=formatted_key, value=str(value), inline=True)
        
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def log_configuration_change(self, guild: discord.Guild, setting: str, old_value: Any,
                                     new_value: Any, changed_by: discord.Member):
        """Log a configuration change via webhook"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title="\u2699\ufe0f Configuration Changed",  # ⚙️
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Setting", value=setting.replace("_", " ").title(), inline=True)
        embed.add_field(name="Changed By", value=f"{changed_by.mention} ({changed_by.id})", inline=True)
        embed.add_field(name="Previous Value", value=str(old_value) if old_value is not None else "Not set", inline=False)
        embed.add_field(name="New Value", value=str(new_value) if new_value is not None else "Not set", inline=False)
        
        embed.set_thumbnail(url=changed_by.display_avatar.url)
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def log_punishment_expired(self, guild: discord.Guild, member: discord.Member,
                                   punishment_type: str, original_duration: str, level: Optional[int] = None):
        """Log when a punishment expires automatically"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title="\U0001f513 Punishment Expired",  # 🔓
            description=f"{member.mention} has been automatically released",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="\U0001f464 Member", value=f"{member.mention} ({member.id})", inline=True)  # 👤
        embed.add_field(name="\U0001f4cb Punishment", value=punishment_type.title(), inline=True)  # 📋
        
        if level:
            embed.add_field(name="\U0001f4ca Level", value=f"Level {level}", inline=True)  # 📊
        
        embed.add_field(name="\u23f0 Original Duration", value=original_duration, inline=True)  # ⏰
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def log_escalation(self, guild: discord.Guild, member: discord.Member, warning_level: int,
                           escalation_level: int, escalation_duration: str, moderator: discord.Member):
        """Log automatic escalation events"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title="\u26a1 Automatic Escalation",  # ⚡
            description=f"Warning level {warning_level} triggered automatic escalation",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="\U0001f464 Member", value=f"{member.mention} ({member.id})", inline=True)  # 👤
        embed.add_field(name="\u26a0\ufe0f Warning Level", value=str(warning_level), inline=True)  # ⚠️
        embed.add_field(name="\U0001f3ed Impel Down Level", value=f"Level {escalation_level}", inline=True)  # 🏭
        embed.add_field(name="\u23f0 Duration", value=escalation_duration, inline=True)  # ⏰
        embed.add_field(name="\u2694\ufe0f Triggered By", value=f"{moderator.mention} ({moderator.id})", inline=True)  # ⚔️
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def log_error(self, guild: discord.Guild, error_type: str, error_message: str,
                       command: Optional[str] = None, user: Optional[discord.Member] = None):
        """Log errors and exceptions"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title="\U0001f6a8 Error Occurred",  # 🚨
            description=error_message,
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Error Type", value=error_type, inline=True)
        
        if command:
            embed.add_field(name="Command", value=command, inline=True)
        
        if user:
            embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=True)
        
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def send_bulk_summary(self, guild: discord.Guild, summary_data: Dict[str, Any]):
        """Send a bulk summary of moderation actions"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        embed = discord.Embed(
            title="\U0001f4ca Moderation Summary",  # 📊
            description="Summary of recent moderation activity",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add summary fields
        for category, data in summary_data.items():
            if isinstance(data, dict):
                field_value = "\n".join([f"**{k}:** {v}" for k, v in data.items()])
            else:
                field_value = str(data)
            
            embed.add_field(name=category.replace("_", " ").title(), value=field_value, inline=True)
        
        embed.set_footer(text=f"Guild: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        return await self._send_webhook_message(guild, embed)
    
    async def _send_webhook_message(self, guild: discord.Guild, embed: discord.Embed, content: str = None) -> bool:
        """Send a message via webhook with rate limiting"""
        
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False
        
        # Check rate limit
        if await self._check_rate_limit(guild):
            await self._queue_message(guild, embed, content)
            logger.warning(f"Webhook rate limited for guild {guild.id}, message queued")
            return False
        
        try:
            await webhook.send(
                embed=embed,
                content=content,
                username="One Piece Mods",
                avatar_url="https://i.imgur.com/Wr8xdJA.png"
            )
            await self._increment_rate_limit(guild)
            
            # Try to process any queued messages
            if guild.id in self._queue and self._queue[guild.id]:
                asyncio.create_task(self._process_queue(guild))
            
            return True
            
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                await self._queue_message(guild, embed, content)
                logger.warning(f"Webhook rate limited for guild {guild.id}")
            else:
                logger.error(f"Webhook error for guild {guild.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected webhook error for guild {guild.id}: {e}")
            return False
    
    def _get_action_color(self, action_type: str) -> discord.Color:
        """Get color for different action types"""
        color_map = {
            "ban": discord.Color.dark_red(),
            "kick": discord.Color.orange(),
            "mute": discord.Color.blue(),
            "warn": discord.Color.gold(),
            "timeout": discord.Color.purple(),
            "impeldown": discord.Color.dark_purple(),
            "unmute": discord.Color.green(),
            "unban": discord.Color.green(),
            "release": discord.Color.green(),
            "clear_warnings": discord.Color.green()
        }
        
        return color_map.get(action_type.lower(), discord.Color.light_grey())
    
    async def test_webhook(self, guild: discord.Guild) -> tuple[bool, str]:
        """Test the webhook configuration"""
        webhook = await self.get_webhook(guild)
        if not webhook:
            return False, "No webhook configured or webhook is invalid"
        
        try:
            embed = discord.Embed(
                title="\U0001f9ea Webhook Test",  # 🧪
                description="This is a test message to verify webhook functionality",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Status", value="\u2705 Webhook is working correctly", inline=False)  # ✅
            embed.set_footer(text=f"Guild: {guild.name}")
            
            await webhook.send(
                embed=embed,
                username="One Piece Mods",
                avatar_url="https://i.imgur.com/Wr8xdJA.png"
            )
            
            return True, "Webhook test successful"
            
        except Exception as e:
            return False, f"Webhook test failed: {str(e)}"
    
    async def get_webhook_stats(self, guild: discord.Guild) -> Dict[str, Any]:
        """Get webhook usage statistics"""
        stats = {
            "webhook_configured": bool(await self.get_webhook(guild)),
            "messages_queued": len(self._queue.get(guild.id, [])),
            "rate_limit_active": await self._check_rate_limit(guild)
        }
        
        if guild.id in self._rate_limits:
            rate_data = self._rate_limits[guild.id]
            stats["requests_this_minute"] = rate_data["count"]
            stats["rate_limit_reset"] = rate_data["reset_time"]
        
        return stats
    
    async def cleanup_guild_data(self, guild_id: int):
        """Clean up cached data for a guild (called when bot leaves guild)"""
        self._webhook_cache.pop(guild_id, None)
        self._rate_limits.pop(guild_id, None)
        self._queue.pop(guild_id, None)
        logger.info(f"Cleaned up webhook data for guild {guild_id}")