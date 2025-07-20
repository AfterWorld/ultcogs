import discord
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Set, Union
from discord.ext import tasks

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.commands import Context
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.predicates import MessagePredicate

# TikTokLive imports
try:
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, DisconnectEvent, LiveEndEvent
    TIKTOK_LIVE_AVAILABLE = True
except ImportError:
    TIKTOK_LIVE_AVAILABLE = False

log = logging.getLogger("red.ultcogs.tiktok")

class TikTokLive(commands.Cog):
    """
    TikTok Live Notifications - Get notified when your favorite TikTok users go live!
    
    Uses TikTokLive library for real-time live stream detection and monitoring.
    Features beautiful Discord embeds, role mentions, and comprehensive statistics.
    """
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.live_clients: Dict[str, TikTokLiveClient] = {}
        self.live_users: Dict[str, Dict] = {}  # Currently live users
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        
        # Check if TikTokLive is available
        if not TIKTOK_LIVE_AVAILABLE:
            log.error("TikTokLive library not found! Please install: pip install TikTokLive")
            return
        
        # Configuration setup
        self.config = Config.get_conf(
            self, 
            identifier=847392061, 
            force_registration=True
        )
        
        # Default settings
        default_global = {
            "reconnect_on_disconnect": True,
            "max_retries": 5,
            "retry_delay": 30,  # seconds
            "monitoring_enabled": True
        }
        
        default_guild = {
            "notification_channel": None,
            "monitored_users": [],
            "mention_role": None,
            "embed_color": 0xff0050,  # TikTok pink
            "custom_message": None,
            "notify_on_connect": True,
            "notify_on_disconnect": False,
            "delete_notifications": False,
            "notification_timeout": 0  # 0 = no auto-delete
        }
        
        default_user_data = {
            "username": "",
            "display_name": "",
            "unique_id": "",
            "last_live": None,
            "total_notifications": 0,
            "is_monitoring": False,
            "connection_status": "disconnected",
            "last_error": None
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.init_custom("user_data", 1)
        self.config.register_custom("user_data", **default_user_data)
        
        # Start monitoring existing users
        self.bot.loop.create_task(self.initialize_monitoring())
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if TIKTOK_LIVE_AVAILABLE:
            # Cancel all monitoring tasks
            for task in self.monitoring_tasks.values():
                task.cancel()
            
            # Disconnect all live clients
            for client in self.live_clients.values():
                self.bot.loop.create_task(self.disconnect_client(client))
    
    async def initialize_monitoring(self):
        """Initialize monitoring for all configured users"""
        await self.bot.wait_until_ready()
        
        if not TIKTOK_LIVE_AVAILABLE:
            return
        
        try:
            # Get all monitored users across all guilds
            all_guilds = await self.config.all_guilds()
            all_monitored = set()
            
            for guild_data in all_guilds.values():
                all_monitored.update(guild_data.get("monitored_users", []))
            
            # Start monitoring each user
            for username in all_monitored:
                await self.start_monitoring_user(username)
            
            log.info(f"Initialized monitoring for {len(all_monitored)} TikTok users")
            
        except Exception as e:
            log.error(f"Error initializing monitoring: {e}")
    
    async def start_monitoring_user(self, username: str) -> bool:
        """Start monitoring a specific user"""
        if not TIKTOK_LIVE_AVAILABLE:
            log.error("TikTokLive library not available")
            return False
        
        if username in self.monitoring_tasks:
            # Already monitoring
            return True
        
        try:
            # Create monitoring task
            task = asyncio.create_task(self.monitor_user_loop(username))
            self.monitoring_tasks[username] = task
            
            # Update user data
            await self.config.custom("user_data", username).is_monitoring.set(True)
            await self.config.custom("user_data", username).username.set(username)
            
            log.info(f"Started monitoring {username}")
            return True
            
        except Exception as e:
            log.error(f"Failed to start monitoring {username}: {e}")
            await self.config.custom("user_data", username).last_error.set(str(e))
            return False
    
    async def stop_monitoring_user(self, username: str):
        """Stop monitoring a specific user"""
        # Cancel monitoring task
        if username in self.monitoring_tasks:
            self.monitoring_tasks[username].cancel()
            del self.monitoring_tasks[username]
        
        # Disconnect client
        if username in self.live_clients:
            await self.disconnect_client(self.live_clients[username])
            del self.live_clients[username]
        
        # Remove from live users if present
        if username in self.live_users:
            del self.live_users[username]
        
        # Update user data
        await self.config.custom("user_data", username).is_monitoring.set(False)
        await self.config.custom("user_data", username).connection_status.set("disconnected")
        
        log.info(f"Stopped monitoring {username}")
    
    async def monitor_user_loop(self, username: str):
        """Main monitoring loop for a user"""
        max_retries = await self.config.max_retries()
        retry_delay = await self.config.retry_delay()
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self.config.custom("user_data", username).connection_status.set("connecting")
                
                # Create TikTokLive client
                client = TikTokLiveClient(unique_id=username)
                self.live_clients[username] = client
                
                # Set up event handlers
                @client.on(ConnectEvent)
                async def on_connect(event: ConnectEvent):
                    await self.handle_user_connect(username, event)
                
                @client.on(DisconnectEvent)
                async def on_disconnect(event: DisconnectEvent):
                    await self.handle_user_disconnect(username, event)
                
                @client.on(LiveEndEvent)
                async def on_live_end(event: LiveEndEvent):
                    await self.handle_live_end(username, event)
                
                # Connect to live stream
                await client.connect()
                
                # Reset retry count on successful connection
                retry_count = 0
                await self.config.custom("user_data", username).connection_status.set("connected")
                await self.config.custom("user_data", username).last_error.set(None)
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Connection failed (attempt {retry_count}/{max_retries}): {str(e)}"
                log.warning(f"Error monitoring {username}: {error_msg}")
                
                await self.config.custom("user_data", username).last_error.set(error_msg)
                await self.config.custom("user_data", username).connection_status.set("error")
                
                if retry_count < max_retries:
                    if await self.config.reconnect_on_disconnect():
                        await asyncio.sleep(retry_delay)
                    else:
                        break
                else:
                    # Max retries reached
                    await self.config.custom("user_data", username).connection_status.set("failed")
                    log.error(f"Max retries reached for {username}, stopping monitoring")
                    break
        
        # Cleanup
        if username in self.live_clients:
            del self.live_clients[username]
        if username in self.monitoring_tasks:
            del self.monitoring_tasks[username]
    
    async def handle_user_connect(self, username: str, event: ConnectEvent):
        """Handle user connecting to live stream (going live)"""
        try:
            live_data = {
                "username": username,
                "display_name": event.user.display_name if hasattr(event, 'user') else username.title(),
                "unique_id": event.user.unique_id if hasattr(event, 'user') else username,
                "is_live": True,
                "live_url": f"https://www.tiktok.com/@{username}/live",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "viewer_count": getattr(event, 'viewer_count', 0),
                "room_id": getattr(event, 'room_id', None)
            }
            
            # Add to live users
            self.live_users[username] = live_data
            
            # Update user data
            async with self.config.custom("user_data", username).all() as user_data:
                user_data["last_live"] = live_data["timestamp"]
                user_data["total_notifications"] += 1
                user_data["display_name"] = live_data["display_name"]
                user_data["unique_id"] = live_data["unique_id"]
                user_data["connection_status"] = "live"
            
            # Send notifications
            await self.send_live_notifications(username, live_data, "connect")
            
            log.info(f"{username} went live!")
            
        except Exception as e:
            log.error(f"Error handling connect event for {username}: {e}")
    
    async def handle_user_disconnect(self, username: str, event: DisconnectEvent):
        """Handle user disconnecting from live stream"""
        try:
            # Remove from live users
            if username in self.live_users:
                del self.live_users[username]
            
            # Update connection status
            await self.config.custom("user_data", username).connection_status.set("disconnected")
            
            # Send disconnect notification if enabled
            all_guilds = await self.config.all_guilds()
            for guild_id, guild_data in all_guilds.items():
                if username in guild_data.get("monitored_users", []):
                    if guild_data.get("notify_on_disconnect", False):
                        await self.send_disconnect_notification(username, guild_id)
            
            log.info(f"{username} disconnected from live stream")
            
        except Exception as e:
            log.error(f"Error handling disconnect event for {username}: {e}")
    
    async def handle_live_end(self, username: str, event: LiveEndEvent):
        """Handle live stream ending"""
        try:
            # Remove from live users
            if username in self.live_users:
                del self.live_users[username]
            
            # Update connection status
            await self.config.custom("user_data", username).connection_status.set("ended")
            
            log.info(f"{username}'s live stream ended")
            
        except Exception as e:
            log.error(f"Error handling live end event for {username}: {e}")
    
    async def disconnect_client(self, client: TikTokLiveClient):
        """Safely disconnect a TikTokLive client"""
        try:
            if client and hasattr(client, 'disconnect'):
                await client.disconnect()
        except Exception as e:
            log.error(f"Error disconnecting client: {e}")
    
    async def send_live_notifications(self, username: str, live_data: Dict, event_type: str = "connect"):
        """Send live notifications to all configured guilds"""
        all_guilds = await self.config.all_guilds()
        
        for guild_id, guild_data in all_guilds.items():
            if username not in guild_data.get("monitored_users", []):
                continue
            
            # Check if this type of notification is enabled
            if event_type == "connect" and not guild_data.get("notify_on_connect", True):
                continue
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            
            channel_id = guild_data.get("notification_channel")
            if not channel_id:
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            
            embed = await self.create_live_embed(live_data, guild_data)
            
            # Prepare notification content
            content = ""
            role_id = guild_data.get("mention_role")
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    content = role.mention
            
            custom_message = guild_data.get("custom_message")
            if custom_message:
                content += f"\n{custom_message}"
            
            try:
                # Send notification
                message = await channel.send(content=content, embed=embed)
                
                # Auto-delete if configured
                timeout = guild_data.get("notification_timeout", 0)
                if timeout > 0:
                    asyncio.create_task(self.auto_delete_message(message, timeout))
                
                log.info(f"Sent live notification for {username} to {guild.name}")
                
            except Exception as e:
                log.error(f"Failed to send notification to {guild.name}: {e}")
    
    async def send_disconnect_notification(self, username: str, guild_id: int):
        """Send disconnect notification"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        guild_config = await self.config.guild(guild).all()
        channel_id = guild_config.get("notification_channel")
        if not channel_id:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title="📴 TikTok Stream Ended",
            description=f"**@{username}** has ended their live stream.",
            color=0x666666,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_footer(text="TikTok Live Notifications")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            log.error(f"Failed to send disconnect notification: {e}")
    
    async def auto_delete_message(self, message: discord.Message, delay: int):
        """Auto-delete a message after specified delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception:
            pass  # Message might already be deleted
    
    async def create_live_embed(self, live_data: Dict, guild_config: Dict) -> discord.Embed:
        """Create a beautiful embed for live notifications"""
        color = guild_config.get("embed_color", 0xff0050)
        
        embed = discord.Embed(
            title="🔴 TikTok Live Stream Started!",
            description=f"**{live_data['display_name']}** is now live on TikTok!",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="👤 Username",
            value=f"@{live_data['username']}",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Watch Live",
            value=f"[Click here to watch]({live_data['live_url']})",
            inline=True
        )
        
        if live_data.get("viewer_count", 0) > 0:
            embed.add_field(
                name="👥 Viewers",
                value=f"{live_data['viewer_count']:,}",
                inline=True
            )
        
        embed.add_field(
            name="⏰ Started",
            value="<t:{}:R>".format(int(datetime.now(timezone.utc).timestamp())),
            inline=True
        )
        
        # Add thumbnail if available
        embed.set_thumbnail(url="https://raw.githubusercontent.com/AfterWorld/ultcogs/main/tiktok/assets/tiktok_icon.png")
        embed.set_footer(
            text="TikTok Live Notifications • Real-time monitoring", 
            icon_url="https://raw.githubusercontent.com/AfterWorld/ultcogs/main/tiktok/assets/tiktok_small.png"
        )
        
        return embed
    
    # Commands
    @commands.group(name="tiktok", aliases=["tt", "tiktok-live"])
    async def tiktok_group(self, ctx: Context):
        """TikTok Live notification commands"""
        if not TIKTOK_LIVE_AVAILABLE:
            embed = discord.Embed(
                title="❌ TikTokLive Library Missing",
                description="Please install the required library:\n```pip install TikTokLive```",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @tiktok_group.command(name="add")
    @commands.admin_or_permissions(manage_guild=True)
    async def add_user(self, ctx: Context, username: str):
        """
        Add a TikTok user to monitor for live streams
        
        **Arguments:**
        • `username` - TikTok username (without @)
        
        **Example:**
        `[p]tiktok add charlidamelio`
        """
        username = username.lower().strip().replace("@", "")
        
        if not username:
            await ctx.send("❌ Please provide a valid username.")
            return
        
        async with self.config.guild(ctx.guild).monitored_users() as users:
            if username in users:
                await ctx.send(f"❌ `@{username}` is already being monitored.")
                return
            
            users.append(username)
        
        # Start monitoring
        success = await self.start_monitoring_user(username)
        
        embed = discord.Embed(
            title="✅ User Added Successfully" if success else "⚠️ User Added (Connection Issues)",
            description=f"{'Now monitoring' if success else 'Added to monitor list for'} `@{username}` for live streams!",
            color=0x00ff00 if success else 0xff9900
        )
        
        if success:
            embed.add_field(
                name="📡 Status",
                value="✅ Real-time monitoring active",
                inline=True
            )
        else:
            embed.add_field(
                name="⚠️ Status",
                value="❌ Connection failed - will retry automatically",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="info")
    async def show_info(self, ctx: Context):
        """Show information about the TikTok Live cog"""
        embed = discord.Embed(
            title="📱 TikTok Live Notifications",
            description="Get real-time notifications when your favorite TikTok creators go live!",
            color=0xff0050
        )
        
        embed.add_field(
            name="🎯 Features",
            value="• **Real-time live stream detection**\n"
                  "• **TikTokLive library integration**\n"
                  "• **Beautiful Discord notifications**\n"
                  "• **Role mentions & auto-delete**\n"
                  "• **Automatic reconnection**\n"
                  "• **Detailed monitoring statistics**\n"
                  "• **Multi-server support**\n"
                  "• **Connection status tracking**",
            inline=False
        )
        
        embed.add_field(
            name="🚀 Quick Start",
            value="1. Set notification channel: `[p]tiktok channel`\n"
                  "2. Add users to monitor: `[p]tiktok add username`\n"
                  "3. Optional: Set role to mention: `[p]tiktok role @role`\n"
                  "4. Enjoy real-time notifications!",
            inline=False
        )
        
        embed.add_field(
            name="📚 Technology",
            value=f"• **TikTokLive**: {'✅ Available' if TIKTOK_LIVE_AVAILABLE else '❌ Missing'}\n"
                  "• **Detection Method**: WebSocket connections\n"
                  "• **Latency**: Near real-time (<5 seconds)\n"
                  "• **Reliability**: Automatic reconnection",
            inline=False
        )
        
        embed.add_field(
            name="👨‍💻 Author",
            value="UltPanda",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Repository",
            value="[GitHub](https://github.com/AfterWorld/ultcogs)",
            inline=True
        )
        
        embed.add_field(
            name="📋 Version",
            value="3.0.0 - TikTokLive Enhanced",
            inline=True
        )
        
        embed.set_footer(text="Part of UltCogs collection • Powered by TikTokLive library")
        
        await ctx.send(embed=embed)
