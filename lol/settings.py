# lol/settings.py - Settings and admin commands
import logging
from datetime import datetime

import discord
from redbot.core import commands, checks

logger = logging.getLogger(__name__)

class LoLSettings:
    """Mixin class containing settings and admin commands"""
    
    @commands.command(name="status", aliases=["rate", "limits"])
    async def api_status(self, ctx):
        """Check the current status of rate limiting"""
        embed = discord.Embed(
            title="🚦 Rate Limit Status", 
            color=0x0099E1,
            timestamp=datetime.now()
        )
        
        # Get rate limit status
        status = await self.api_manager.get_rate_limit_status()
        
        if status:
            for endpoint, usage in status.items():
                embed.add_field(
                    name=endpoint.replace("-", " ").title(),
                    value=usage,
                    inline=True
                )
        else:
            embed.description = "No rate limit data available"
        
        # Add cache information
        cache_stats = await self.api_manager.get_cache_stats()
        general_cache = cache_stats['general_cache']
        
        embed.add_field(
            name="💾 Cache Status",
            value=f"Hit Rate: {general_cache['hit_rate']}\nSize: {general_cache['size']} items",
            inline=True
        )
        
        embed.set_footer(text="Usage: current/limit")
        await ctx.send(embed=embed)

    # Settings group
    @commands.group(name="lolset", aliases=["lolsettings"])
    @checks.admin_or_permissions(manage_guild=True)
    async def lol_settings(self, ctx):
        """League of Legends cog settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @lol_settings.command(name="apikey")
    @checks.is_owner()
    async def set_api_key(self, ctx, *, api_key: str):
        """Set the Riot Games API key
        
        Get your API key from: https://developer.riotgames.com/
        """
        await self.config.api_key.set(api_key)
        await ctx.send("✅ API key has been set successfully.")
        
        # Delete the message containing the API key for security
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @lol_settings.command(name="region")
    async def set_default_region(self, ctx, region: str):
        """Set the default region for this server
        
        Valid regions: na, euw, eune, kr, br, jp, ru, oc, tr, lan, las, me, sg, tw, vn
        """
        try:
            region = self.api_manager.normalize_region(region)
            await self.config.guild(ctx.guild).default_region.set(region)
            await ctx.send(f"✅ Default region set to **{region.upper()}**")
        except ValueError as e:
            await ctx.send(f"❌ {str(e)}")

    @lol_settings.command(name="information")
    async def settings_info(self, ctx):
        """Show current settings and status"""
        api_key_set = bool(await self.config.api_key())
        default_region = await self.config.guild(ctx.guild).default_region()
        
        embed = discord.Embed(
            title="⚙️ League of Legends Settings", 
            color=0x0099E1,
            timestamp=datetime.now()
        )
        
        # Basic settings
        embed.add_field(
            name="🔑 API Configuration",
            value=f"API Key: {'✅ Set' if api_key_set else '❌ Not Set'}\nDefault Region: {default_region.upper()}",
            inline=True
        )
        
        # Database info
        try:
            db_stats = await self.db_manager.get_database_stats()
            embed.add_field(
                name="🗃️ Database Status",
                value=f"Size: {db_stats['db_size_mb']} MB\n"
                      f"Monitored: {db_stats['monitored_summoners_count']}\n"
                      f"Cached Matches: {db_stats['match_cache_count']}",
                inline=True
            )
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
        
        # Cache performance
        try:
            cache_stats = await self.api_manager.get_cache_stats()
            general_cache = cache_stats['general_cache']
            embed.add_field(
                name="💾 Cache Performance",
                value=f"Hit Rate: {general_cache['hit_rate']}\n"
                      f"Size: {general_cache['size']} items",
                inline=True
            )
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
        
        # Rate limit status for key endpoints
        try:
            rate_status = await self.api_manager.get_rate_limit_status()
            if rate_status:
                key_endpoints = ['summoner', 'match']
                status_text = []
                for endpoint in key_endpoints:
                    if endpoint in rate_status:
                        status_text.append(f"{endpoint.title()}: {rate_status[endpoint]}")
                
                if status_text:
                    embed.add_field(
                        name="🚦 Key Rate Limits",
                        value="\n".join(status_text),
                        inline=False
                    )
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
        
        await ctx.send(embed=embed)

    @lol_settings.command(name="testapi")
    @checks.is_owner()
    async def test_api(self, ctx):
        """Test the API connection"""
        async with ctx.typing():
            try:
                # Test with a simple status check
                url = "https://na1.api.riotgames.com/lol/status/v4/platform-data"
                status_data = await self.api_manager.make_request(url)
                
                embed = discord.Embed(title="🧪 API Test Results", color=0x00FF00)
                embed.add_field(name="Status", value="✅ Success", inline=True)
                embed.add_field(name="Server", value=status_data.get("name", "NA"), inline=True)
                
                # Test rate limiter status
                rate_status = await self.api_manager.get_rate_limit_status()
                if rate_status and "status" in rate_status:
                    embed.add_field(name="Rate Limit", value=rate_status["status"], inline=True)
                
                embed.add_field(
                    name="Response Time",
                    value="< 1 second",
                    inline=True
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                embed = discord.Embed(title="🧪 API Test Results", color=0xFF0000)
                embed.add_field(name="Status", value="❌ Failed", inline=True)
                embed.add_field(name="Error", value=str(e)[:1000], inline=False)
                await ctx.send(embed=embed)

    @lol_settings.command(name="ratelimits")
    async def show_rate_limits(self, ctx):
        """Show all endpoint rate limits"""
        from .constants import ENDPOINT_RATE_LIMITS
        
        embed = discord.Embed(
            title="📋 Endpoint Rate Limits", 
            color=0x0099E1,
            timestamp=datetime.now()
        )
        
        for endpoint, limits in ENDPOINT_RATE_LIMITS.items():
            limit_strs = []
            for requests, seconds in limits:
                if seconds < 60:
                    limit_strs.append(f"{requests}/{seconds}s")
                elif seconds < 3600:
                    limit_strs.append(f"{requests}/{seconds//60}m")
                else:
                    limit_strs.append(f"{requests}/{seconds//3600}h")
            
            embed.add_field(
                name=endpoint.replace("-", " ").title(),
                value=" | ".join(limit_strs),
                inline=True
            )
        
        embed.set_footer(text="Official Riot API limits")
        await ctx.send(embed=embed)

    @lol_settings.command(name="clearcache")
    @checks.is_owner()
    async def clear_cache(self, ctx):
        """Clear all cached data"""
        try:
            self.api_manager.cache.clear()
            self.api_manager.champion_cache.clear()
            
            # Also clean up database cache
            cleaned_count = await self.db_manager.cleanup_expired_cache()
            
            embed = discord.Embed(
                title="🧹 Cache Cleared",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            embed.add_field(name="Memory Cache", value="✅ Cleared", inline=True)
            embed.add_field(name="Database Cache", value=f"✅ {cleaned_count} entries removed", inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error clearing cache: {str(e)}")

    @lol_settings.command(name="cleanup")
    @checks.is_owner()
    async def cleanup_database(self, ctx, days: int = 30):
        """Clean up old database entries (default: 30 days)"""
        try:
            async with ctx.typing():
                # Cleanup various tables
                lookups_cleaned = await self.db_manager.cleanup_old_lookups(days)
                cache_cleaned = await self.db_manager.cleanup_expired_cache()
                stats_cleaned = await self.db_manager.cleanup_old_statistics(days)
                
                # Vacuum database to reclaim space
                await self.db_manager.vacuum_database()
                
                embed = discord.Embed(
                    title="🧹 Database Cleanup Complete",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                
                embed.add_field(
                    name="Entries Removed",
                    value=f"📜 Lookups: {lookups_cleaned}\n"
                          f"💾 Cache: {cache_cleaned}\n"
                          f"📊 Statistics: {stats_cleaned}",
                    inline=True
                )
                
                # Get new database size
                db_stats = await self.db_manager.get_database_stats()
                embed.add_field(
                    name="Database Size",
                    value=f"{db_stats['db_size_mb']} MB",
                    inline=True
                )
                
                embed.set_footer(text=f"Cleaned entries older than {days} days")
                await ctx.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            await ctx.send(f"❌ Error during cleanup: {str(e)}")

    @lol_settings.command(name="backup")
    @checks.is_owner()
    async def backup_database(self, ctx):
        """Create a backup of the database"""
        try:
            import shutil
            from datetime import datetime
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_manager.db_path.parent / f"lol_backup_{timestamp}.db"
            
            # Copy database file
            shutil.copy2(self.db_manager.db_path, backup_path)
            
            # Get file size
            backup_size = backup_path.stat().st_size / (1024 * 1024)  # MB
            
            embed = discord.Embed(
                title="💾 Database Backup Created",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Backup File", value=backup_path.name, inline=True)
            embed.add_field(name="Size", value=f"{backup_size:.2f} MB", inline=True)
            embed.add_field(name="Location", value=str(backup_path.parent), inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            await ctx.send(f"❌ Error creating backup: {str(e)}")

    @lol_settings.command(name="monitor")
    @checks.is_owner()
    async def monitor_settings(self, ctx):
        """Show monitoring system settings and status"""
        try:
            embed = discord.Embed(
                title="👁️ Monitoring System Status",
                color=0x0099E1,
                timestamp=datetime.now()
            )
            
            # Monitoring statistics
            total_monitored = len(self.notification_manager.monitored_summoners)
            active_channels = sum(len(channels) for channels in self.notification_manager.notification_channels.values())
            
            embed.add_field(
                name="📊 Statistics",
                value=f"Monitored Summoners: {total_monitored}\n"
                      f"Active Channels: {active_channels}\n"
                      f"Check Interval: {self.notification_manager.check_interval}s",
                inline=True
            )
            
            # Task status
            task_status = "🟢 Running" if self.notification_manager.monitor_task and not self.notification_manager.monitor_task.done() else "🔴 Stopped"
            embed.add_field(
                name="⚙️ Task Status",
                value=f"Monitoring Task: {task_status}",
                inline=True
            )
            
            # Recent activity (if any)
            in_game_count = sum(1 for s in self.notification_manager.monitored_summoners.values() if s.get("in_game", False))
            embed.add_field(
                name="🎮 Current Activity",
                value=f"Summoners In Game: {in_game_count}/{total_monitored}",
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting monitor status: {e}")
            await ctx.send(f"❌ Error getting monitor status: {str(e)}")

    @lol_settings.command(name="version")
    async def show_version(self, ctx):
        """Show cog version and information"""
        from .constants import DDRAGON_VERSION, REGION_MAPPING, ENDPOINT_RATE_LIMITS
        
        embed = discord.Embed(
            title="📋 LoL Cog Information",
            color=0x0099E1,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎮 Game Data",
            value=f"Data Dragon Version: {DDRAGON_VERSION}\n"
                  f"Supported Regions: {len(REGION_MAPPING)}\n"
                  f"API Endpoints: {len(ENDPOINT_RATE_LIMITS)}",
            inline=True
        )
        
        # System info
        import sys
        embed.add_field(
            name="🖥️ System",
            value=f"Python: {sys.version.split()[0]}\n"
                  f"Red-DiscordBot: 3.5.0+",
            inline=True
        )
        
        # Features
        features = [
            "✅ Multi-region support",
            "✅ Intelligent rate limiting", 
            "✅ Live game notifications",
            "✅ Account linking",
            "✅ Match analysis",
            "✅ Performance statistics"
        ]
        
        embed.add_field(
            name="⭐ Features",
            value="\n".join(features),
            inline=False
        )
        
        embed.set_footer(text="League of Legends integration for Red-DiscordBot")
        await ctx.send(embed=embed)
