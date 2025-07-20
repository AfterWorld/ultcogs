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
    
    @tiktok_group.command(name="remove", aliases=["delete", "rm"])
    @commands.admin_or_permissions(manage_guild=True)
    async def remove_user(self, ctx: Context, username: str):
        """
        Remove a TikTok user from monitoring
        
        **Arguments:**
        • `username` - TikTok username to remove
        """
        username = username.lower().strip().replace("@", "")
        
        async with self.config.guild(ctx.guild).monitored_users() as users:
            if username not in users:
                await ctx.send(f"❌ `@{username}` is not being monitored.")
                return
            
            users.remove(username)
        
        # Stop monitoring if no other guilds are monitoring this user
        all_guilds = await self.config.all_guilds()
        still_monitored = False
        for guild_data in all_guilds.values():
            if username in guild_data.get("monitored_users", []):
                still_monitored = True
                break
        
        if not still_monitored:
            await self.stop_monitoring_user(username)
        
        embed = discord.Embed(
            title="✅ User Removed",
            description=f"No longer monitoring `@{username}` for live streams.",
            color=0xff9900
        )
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="list", aliases=["show"])
    async def list_users(self, ctx: Context):
        """Show all monitored TikTok users in this server"""
        users = await self.config.guild(ctx.guild).monitored_users()
        
        if not users:
            embed = discord.Embed(
                title="📋 Monitored Users",
                description="No TikTok users are currently being monitored.",
                color=0x666666
            )
            await ctx.send(embed=embed)
            return
        
        # Get user data and format list
        user_list = []
        for username in users:
            user_data = await self.config.custom("user_data", username).all()
            notifications = user_data.get("total_notifications", 0)
            last_live = user_data.get("last_live")
            connection_status = user_data.get("connection_status", "unknown")
            
            # Status indicators
            if username in self.live_users:
                status = "🔴 LIVE"
            elif connection_status == "connected":
                status = "🟢 Connected"
            elif connection_status == "connecting":
                status = "🟡 Connecting"
            elif connection_status == "error":
                status = "🔄 Retrying"
            elif connection_status == "failed":
                status = "❌ Failed"
            else:
                status = "⚫ Offline"
            
            user_info = f"`@{username}` {status}\n"
            user_info += f"  • Notifications sent: {notifications}"
            
            if last_live:
                try:
                    last_time = datetime.fromisoformat(last_live.replace('Z', '+00:00'))
                    timestamp = int(last_time.timestamp())
                    user_info += f"\n  • Last live: <t:{timestamp}:R>"
                except:
                    user_info += f"\n  • Last live: Unknown"
            
            # Add error info if present
            last_error = user_data.get("last_error")
            if last_error and connection_status in ["error", "failed"]:
                error_short = last_error[:50] + "..." if len(last_error) > 50 else last_error
                user_info += f"\n  • Error: {error_short}"
            
            user_list.append(user_info)
        
        embed = discord.Embed(
            title="📋 Monitored TikTok Users",
            description="\n\n".join(user_list),
            color=0xff0050
        )
        embed.set_footer(text=f"Monitoring {len(users)} user(s) • Real-time detection active")
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="status")
    async def status_command(self, ctx: Context, username: str = None):
        """
        Show detailed status for a specific user or all users
        
        **Arguments:**
        • `username` - Specific user to check (optional)
        """
        if username:
            username = username.lower().strip().replace("@", "")
            users = await self.config.guild(ctx.guild).monitored_users()
            
            if username not in users:
                await ctx.send(f"❌ `@{username}` is not being monitored in this server.")
                return
            
            await self.show_user_status(ctx, username)
        else:
            await self.show_system_status(ctx)
    
    async def show_user_status(self, ctx: Context, username: str):
        """Show detailed status for a specific user"""
        user_data = await self.config.custom("user_data", username).all()
        
        embed = discord.Embed(
            title=f"📊 Status: @{username}",
            color=0xff0050
        )
        
        # Basic info
        display_name = user_data.get("display_name", username.title())
        embed.add_field(
            name="👤 Display Name",
            value=display_name,
            inline=True
        )
        
        # Live status
        is_live = username in self.live_users
        live_status = "🔴 LIVE" if is_live else "⚫ Offline"
        embed.add_field(
            name="📺 Live Status",
            value=live_status,
            inline=True
        )
        
        # Connection status
        connection_status = user_data.get("connection_status", "unknown")
        status_emoji = {
            "connected": "🟢",
            "connecting": "🟡", 
            "disconnected": "⚫",
            "error": "🔄",
            "failed": "❌",
            "live": "🔴"
        }
        
        embed.add_field(
            name="🔗 Connection",
            value=f"{status_emoji.get(connection_status, '❓')} {connection_status.title()}",
            inline=True
        )
        
        # Statistics
        notifications = user_data.get("total_notifications", 0)
        embed.add_field(
            name="📊 Notifications Sent",
            value=str(notifications),
            inline=True
        )
        
        # Monitoring status
        is_monitoring = user_data.get("is_monitoring", False)
        monitoring_status = "✅ Active" if is_monitoring else "❌ Inactive"
        embed.add_field(
            name="📡 Monitoring",
            value=monitoring_status,
            inline=True
        )
        
        # Last live
        last_live = user_data.get("last_live")
        if last_live:
            try:
                last_time = datetime.fromisoformat(last_live.replace('Z', '+00:00'))
                timestamp = int(last_time.timestamp())
                embed.add_field(
                    name="⏰ Last Live",
                    value=f"<t:{timestamp}:R>",
                    inline=True
                )
            except:
                embed.add_field(
                    name="⏰ Last Live",
                    value="Unknown",
                    inline=True
                )
        
        # Error info
        last_error = user_data.get("last_error")
        if last_error:
            embed.add_field(
                name="⚠️ Last Error",
                value=f"```{last_error[:100]}{'...' if len(last_error) > 100 else ''}```",
                inline=False
            )
        
        # Live stream info if currently live
        if is_live and username in self.live_users:
            live_data = self.live_users[username]
            viewer_count = live_data.get("viewer_count", 0)
            if viewer_count > 0:
                embed.add_field(
                    name="👥 Current Viewers",
                    value=f"{viewer_count:,}",
                    inline=True
                )
        
        await ctx.send(embed=embed)
    
    async def show_system_status(self, ctx: Context):
        """Show overall system status"""
        global_config = await self.config.all()
        guild_users = await self.config.guild(ctx.guild).monitored_users()
        
        embed = discord.Embed(
            title="🖥️ TikTok Live System Status",
            color=0xff0050
        )
        
        # Basic stats
        total_monitoring = len(self.monitoring_tasks)
        total_live = len(self.live_users)
        total_clients = len(self.live_clients)
        
        embed.add_field(
            name="📊 Statistics",
            value=f"• Users monitoring: {total_monitoring}\n"
                  f"• Currently live: {total_live}\n"
                  f"• Active connections: {total_clients}\n"
                  f"• This server: {len(guild_users)} users",
            inline=False
        )
        
        # System settings
        embed.add_field(
            name="⚙️ Settings",
            value=f"• Auto-reconnect: {'✅' if global_config['reconnect_on_disconnect'] else '❌'}\n"
                  f"• Max retries: {global_config['max_retries']}\n"
                  f"• Retry delay: {global_config['retry_delay']}s\n"
                  f"• Monitoring: {'✅' if global_config['monitoring_enabled'] else '❌'}",
            inline=False
        )
        
        # Library info
        embed.add_field(
            name="📚 Library",
            value=f"• TikTokLive: {'✅ Available' if TIKTOK_LIVE_AVAILABLE else '❌ Missing'}\n"
                  f"• Real-time detection: ✅ Active\n"
                  f"• Connection method: WebSocket",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="channel")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_channel(self, ctx: Context, channel: Optional[discord.TextChannel] = None):
        """
        Set the channel for live notifications
        
        **Arguments:**
        • `channel` - Channel to send notifications (optional, defaults to current)
        """
        if channel is None:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).notification_channel.set(channel.id)
        
        embed = discord.Embed(
            title="✅ Notification Channel Set",
            description=f"Live notifications will be sent to {channel.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="role")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_role(self, ctx: Context, role: Optional[discord.Role] = None):
        """
        Set a role to mention when users go live
        
        **Arguments:**
        • `role` - Role to mention (optional, use 'none' to disable)
        """
        if role is None:
            await self.config.guild(ctx.guild).mention_role.set(None)
            embed = discord.Embed(
                title="✅ Mention Role Cleared",
                description="No role will be mentioned for live notifications.",
                color=0xff9900
            )
        else:
            await self.config.guild(ctx.guild).mention_role.set(role.id)
            embed = discord.Embed(
                title="✅ Mention Role Set",
                description=f"{role.mention} will be mentioned for live notifications.",
                color=0x00ff00
            )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="config", aliases=["settings"])
    @commands.admin_or_permissions(manage_guild=True)
    async def show_config(self, ctx: Context):
        """Show current TikTok Live configuration for this server"""
        guild_config = await self.config.guild(ctx.guild).all()
        global_config = await self.config.all()
        
        # Get channel info
        channel_id = guild_config.get("notification_channel")
        channel_info = "Not set"
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            channel_info = channel.mention if channel else "Invalid channel"
        
        # Get role info
        role_id = guild_config.get("mention_role")
        role_info = "None"
        if role_id:
            role = ctx.guild.get_role(role_id)
            role_info = role.mention if role else "Invalid role"
        
        # Get monitored users count
        users_count = len(guild_config.get("monitored_users", []))
        live_count = len([u for u in guild_config.get("monitored_users", []) if u in self.live_users])
        
        embed = discord.Embed(
            title="⚙️ TikTok Live Configuration",
            color=0xff0050
        )
        
        embed.add_field(
            name="📺 Notification Channel",
            value=channel_info,
            inline=False
        )
        
        embed.add_field(
            name="👥 Mention Role",
            value=role_info,
            inline=True
        )
        
        embed.add_field(
            name="👤 Monitored Users",
            value=f"{users_count} users",
            inline=True
        )
        
        embed.add_field(
            name="🔴 Currently Live",
            value=f"{live_count} users",
            inline=True
        )
        
        embed.add_field(
            name="🔔 Connect Notifications",
            value="✅ Enabled" if guild_config.get("notify_on_connect", True) else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="📴 Disconnect Notifications",
            value="✅ Enabled" if guild_config.get("notify_on_disconnect", False) else "❌ Disabled",
            inline=True
        )
        
        embed.add_field(
            name="🎨 Embed Color",
            value=f"#{guild_config.get('embed_color', 0xff0050):06x}",
            inline=True
        )
        
        timeout = guild_config.get("notification_timeout", 0)
        timeout_text = f"{timeout}s" if timeout > 0 else "Disabled"
        embed.add_field(
            name="⏰ Auto-delete",
            value=timeout_text,
            inline=True
        )
        
        embed.add_field(
            name="📚 Library Status",
            value="✅ TikTokLive Available" if TIKTOK_LIVE_AVAILABLE else "❌ TikTokLive Missing",
            inline=True
        )
        
        embed.add_field(
            name="🔄 Auto-reconnect",
            value="✅ Enabled" if global_config["reconnect_on_disconnect"] else "❌ Disabled",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="reconnect")
    @commands.admin_or_permissions(manage_guild=True)
    async def reconnect_user(self, ctx: Context, username: str):
        """
        Force reconnect monitoring for a specific user
        
        **Arguments:**
        • `username` - TikTok username to reconnect
        """
        username = username.lower().strip().replace("@", "")
        
        users = await self.config.guild(ctx.guild).monitored_users()
        if username not in users:
            await ctx.send(f"❌ `@{username}` is not being monitored in this server.")
            return
        
        await ctx.typing()
        
        # Stop current monitoring
        await self.stop_monitoring_user(username)
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Restart monitoring
        success = await self.start_monitoring_user(username)
        
        if success:
            embed = discord.Embed(
                title="✅ Reconnection Successful",
                description=f"Successfully reconnected monitoring for `@{username}`",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Reconnection Failed",
                description=f"Failed to reconnect monitoring for `@{username}`. Check logs for details.",
                color=0xff0000
            )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="notifications")
    @commands.admin_or_permissions(manage_guild=True)
    async def notification_settings(self, ctx: Context, setting: str, value: bool):
        """
        Configure notification settings
        
        **Arguments:**
        • `setting` - Setting to change (connect, disconnect, timeout)
        • `value` - True/False for connect/disconnect, seconds for timeout
        
        **Examples:**
        `[p]tiktok notifications connect true`
        `[p]tiktok notifications disconnect false`
        """
        setting = setting.lower()
        
        if setting == "connect":
            await self.config.guild(ctx.guild).notify_on_connect.set(value)
            embed = discord.Embed(
                title="✅ Setting Updated",
                description=f"Connect notifications: {'✅ Enabled' if value else '❌ Disabled'}",
                color=0x00ff00
            )
        elif setting == "disconnect":
            await self.config.guild(ctx.guild).notify_on_disconnect.set(value)
            embed = discord.Embed(
                title="✅ Setting Updated",
                description=f"Disconnect notifications: {'✅ Enabled' if value else '❌ Disabled'}",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Invalid Setting",
                description="Valid settings: `connect`, `disconnect`",
                color=0xff0000
            )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="timeout")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_timeout(self, ctx: Context, seconds: int):
        """
        Set auto-delete timeout for notifications
        
        **Arguments:**
        • `seconds` - Seconds after which to delete notifications (0 to disable)
        
        **Example:**
        `[p]tiktok timeout 300` - Delete after 5 minutes
        `[p]tiktok timeout 0` - Disable auto-delete
        """
        if seconds < 0:
            await ctx.send("❌ Timeout cannot be negative.")
            return
        
        await self.config.guild(ctx.guild).notification_timeout.set(seconds)
        
        if seconds > 0:
            embed = discord.Embed(
                title="✅ Auto-delete Timeout Set",
                description=f"Notifications will be deleted after {seconds} seconds.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="✅ Auto-delete Disabled",
                description="Notifications will not be automatically deleted.",
                color=0xff9900
            )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="test")
    @commands.admin_or_permissions(manage_guild=True)
    async def test_notification(self, ctx: Context):
        """Send a test live notification to see how it looks"""
        guild_config = await self.config.guild(ctx.guild).all()
        
        channel_id = guild_config.get("notification_channel")
        if not channel_id:
            await ctx.send("❌ No notification channel set. Use `[p]tiktok channel` first.")
            return
        
        channel = ctx.guild.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Notification channel not found.")
            return
        
        # Create test live data
        test_data = {
            "username": "testuser",
            "display_name": "Test User",
            "unique_id": "testuser",
            "is_live": True,
            "live_url": "https://www.tiktok.com/@testuser/live",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "viewer_count": 1337,
            "room_id": "test_room_123"
        }
        
        embed = await self.create_live_embed(test_data, guild_config)
        embed.title = "🧪 Test Notification - TikTok Live"
        embed.description = "This is a test notification to show how live alerts will look."
        
        # Test role mention if configured
        content = "🧪 **Test Notification**"
        role_id = guild_config.get("mention_role")
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                content += f"\n{role.mention}"
        
        try:
            message = await channel.send(content=content, embed=embed)
            
            # Test auto-delete if configured
            timeout = guild_config.get("notification_timeout", 0)
            if timeout > 0:
                asyncio.create_task(self.auto_delete_message(message, timeout))
                await ctx.send(f"✅ Test notification sent to {channel.mention} (will auto-delete in {timeout}s)")
            else:
                await ctx.send(f"✅ Test notification sent to {channel.mention}")
                
        except Exception as e:
            await ctx.send(f"❌ Failed to send test notification: {e}")
    
    @tiktok_group.command(name="restart")
    @checks.is_owner()
    async def restart_monitoring(self, ctx: Context):
        """Restart all monitoring connections (Bot owner only)"""
        await ctx.typing()
        
        # Stop all monitoring
        for username in list(self.monitoring_tasks.keys()):
            await self.stop_monitoring_user(username)
        
        # Wait a moment
        await asyncio.sleep(3)
        
        # Restart monitoring
        await self.initialize_monitoring()
        
        embed = discord.Embed(
            title="✅ Monitoring Restarted",
            description="All TikTok Live monitoring connections have been restarted.",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📊 Status",
            value=f"• Active connections: {len(self.live_clients)}\n"
                  f"• Monitoring tasks: {len(self.monitoring_tasks)}\n"
                  f"• Currently live: {len(self.live_users)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="global")
    @checks.is_owner()
    async def global_settings(self, ctx: Context, setting: str, value: Union[int, bool]):
        """
        Configure global settings (Bot owner only)
        
        **Arguments:**
        • `setting` - Setting to change (retries, delay, reconnect, monitoring)
        • `value` - New value for the setting
        
        **Examples:**
        `[p]tiktok global retries 3`
        `[p]tiktok global delay 60`
        `[p]tiktok global reconnect true`
        """
        setting = setting.lower()
        
        if setting == "retries":
            if not isinstance(value, int) or value < 1:
                await ctx.send("❌ Max retries must be a positive integer.")
                return
            await self.config.max_retries.set(value)
            message = f"Max retries set to {value}"
            
        elif setting == "delay":
            if not isinstance(value, int) or value < 10:
                await ctx.send("❌ Retry delay must be at least 10 seconds.")
                return
            await self.config.retry_delay.set(value)
            message = f"Retry delay set to {value} seconds"
            
        elif setting == "reconnect":
            if not isinstance(value, bool):
                await ctx.send("❌ Reconnect must be true or false.")
                return
            await self.config.reconnect_on_disconnect.set(value)
            message = f"Auto-reconnect {'enabled' if value else 'disabled'}"
            
        elif setting == "monitoring":
            if not isinstance(value, bool):
                await ctx.send("❌ Monitoring must be true or false.")
                return
            await self.config.monitoring_enabled.set(value)
            message = f"Global monitoring {'enabled' if value else 'disabled'}"
            
        else:
            await ctx.send("❌ Valid settings: `retries`, `delay`, `reconnect`, `monitoring`")
            return
        
        embed = discord.Embed(
            title="✅ Global Setting Updated",
            description=message,
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="color")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_embed_color(self, ctx: Context, color: str):
        """
        Set the embed color for notifications
        
        **Arguments:**
        • `color` - Hex color code (e.g., #ff0050, ff0050, or tiktok)
        
        **Examples:**
        `[p]tiktok color #ff0050` - TikTok pink
        `[p]tiktok color tiktok` - Default TikTok color
        `[p]tiktok color #00ff00` - Green
        """
        color = color.lower().strip()
        
        # Handle special color names
        if color == "tiktok":
            color_value = 0xff0050
        elif color == "red":
            color_value = 0xff0000
        elif color == "green":
            color_value = 0x00ff00
        elif color == "blue":
            color_value = 0x0000ff
        elif color == "purple":
            color_value = 0x800080
        else:
            # Parse hex color
            color = color.replace("#", "")
            try:
                color_value = int(color, 16)
                if color_value > 0xffffff:
                    raise ValueError("Color value too large")
            except ValueError:
                await ctx.send("❌ Invalid color format. Use hex format like `#ff0050` or color names like `tiktok`.")
                return
        
        await self.config.guild(ctx.guild).embed_color.set(color_value)
        
        embed = discord.Embed(
            title="✅ Embed Color Updated",
            description=f"Notification embeds will now use this color.",
            color=color_value
        )
        embed.add_field(
            name="🎨 Color Code",
            value=f"#{color_value:06x}",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="message")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_custom_message(self, ctx: Context, *, message: str = None):
        """
        Set a custom message to include with notifications
        
        **Arguments:**
        • `message` - Custom message text (use 'none' to disable)
        
        **Example:**
        `[p]tiktok message 🎉 Someone is live! Come watch!`
        `[p]tiktok message none` - Disable custom message
        """
        if message and message.lower() == "none":
            await self.config.guild(ctx.guild).custom_message.set(None)
            embed = discord.Embed(
                title="✅ Custom Message Cleared",
                description="No custom message will be included with notifications.",
                color=0xff9900
            )
        elif message:
            # Limit message length
            if len(message) > 200:
                await ctx.send("❌ Custom message must be 200 characters or less.")
                return
            
            await self.config.guild(ctx.guild).custom_message.set(message)
            embed = discord.Embed(
                title="✅ Custom Message Set",
                description=f"This message will be included with notifications:\n\n> {message}",
                color=0x00ff00
            )
        else:
            # Show current message
            current_message = await self.config.guild(ctx.guild).custom_message()
            if current_message:
                embed = discord.Embed(
                    title="📝 Current Custom Message",
                    description=f"> {current_message}",
                    color=0xff0050
                )
            else:
                embed = discord.Embed(
                    title="📝 Custom Message",
                    description="No custom message is currently set.",
                    color=0x666666
                )
        
        await ctx.send(embed=embed)
    
    @tiktok_group.command(name="info")
    async def cog_info(self, ctx: Context):
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
            name="🔧 Advanced Features",
            value="• Force reconnect users: `[p]tiktok reconnect username`\n"
                  "• Monitor connection status: `[p]tiktok status`\n"
                  "• Configure notifications: `[p]tiktok notifications`\n"
                  "• Auto-delete messages: `[p]tiktok timeout`\n"
                  "• Custom colors: `[p]tiktok color #ff0050`\n"
                  "• Custom messages: `[p]tiktok message text`",
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
            name="📊 Current Status",
            value=f"• **Active Connections**: {len(self.live_clients)}\n"
                  f"• **Monitoring Tasks**: {len(self.monitoring_tasks)}\n"
                  f"• **Currently Live**: {len(self.live_users)}\n"
                  f"• **Library Status**: {'✅ Ready' if TIKTOK_LIVE_AVAILABLE else '❌ Missing'}",
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
