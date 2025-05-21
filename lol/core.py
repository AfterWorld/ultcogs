# lol/core.py - Main cog class
import asyncio
import aiohttp
import discord
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from collections import deque, defaultdict, Counter
from redbot.core import commands, Config, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import humanize_timedelta
from redbot.core import data_manager

from .api import RiotAPIManager
from .embeds import EmbedFactory
from .notifications import NotificationManager
from .database import DatabaseManager
from .constants import REGION_MAPPING
from .commands import LoLCommands
from .settings import LoLSettings
from .errors import LoLErrorHandler
from .v2_components import V2ComponentsHelper

_ = Translator("LoL", __file__)

@cog_i18n(_)
class LeagueOfLegends(LoLCommands, LoLSettings, LoLErrorHandler, commands.Cog):
    """League of Legends integration with Riot Games API"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Initialize managers
        self.api_manager = RiotAPIManager(self.config)
        self.embed_factory = EmbedFactory()
        self.notification_manager = NotificationManager(self)
        self.db_manager = DatabaseManager(data_manager.cog_data_path(self))
        
        # Initialize V2 Components Helper
        self.v2_helper = V2ComponentsHelper(bot)
        
        # Default settings
        default_guild = {"default_region": "na1"}
        default_global = {"api_key": None}
        default_user = {"linked_account": None, "preferred_region": None}
        
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        
        self.api_manager.set_database_manager(self.db_manager)
        
    async def cog_load(self):
        """Initialize database and start monitoring"""
        await self.db_manager.initialize()
        await self.notification_manager.load_from_database()
        self.notification_manager.start_monitoring()
    
    async def cog_unload(self):
        """Clean shutdown"""
        self.notification_manager.stop_monitoring()
        await self.api_manager.close()
        await self.db_manager.close()

    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data for GDPR compliance"""
        requester = kwargs.get("requester")
        user_id = kwargs.get("user_id")
        
        if requester == "discord_deleted_user":
            await self.config.user_from_id(user_id).clear()
            await self.db_manager.delete_user_data(user_id)

    # Command methods will be added here
    @commands.group(name="lol", aliases=["league"])
    async def lol(self, ctx):
        """League of Legends commands"""
        pass

    @commands.cooldown(1, 10, commands.BucketType.user)
    @lol.command(name="summoner", aliases=["player", "profile"])
    async def summoner(self, ctx, region: str = None, *, summoner_name: str):
        """Look up a summoner's profile with champion icons"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                rank_data = await self.api_manager.get_rank_info(region, summoner_data["id"])
                
                # Get champion mastery data for icons
                mastery_data = await self.api_manager.get_champion_mastery(region, summoner_data["puuid"], count=5)
                
                # Save lookup history
                await self.db_manager.save_lookup_history(ctx.author.id, ctx.guild.id if ctx.guild else None, summoner_name, region)
                
                # Send profile with champion icons - ONLY ONCE
                await self.v2_helper.send_summoner_profile_with_champions(
                    ctx, summoner_data, rank_data, mastery_data, region
                )
                
            except Exception as e:
                import logging
                logging.error(f"Error in summoner command: {e}", exc_info=True)
                await ctx.send(f"Error looking up summoner: {str(e)}")

    @commands.cooldown(1, 30, commands.BucketType.user)
    @lol.command(name="analyze", aliases=["stats"])
    async def analyze_summoner(self, ctx, region: str = None, *, summoner_name: str):
        """Deep analysis of summoner performance over last 20 games"""
        async with ctx.typing():
            try:
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Get match analysis
                analysis = await self.api_manager.analyze_recent_matches(summoner_data, region, count=20)
                
                if not analysis:
                    await ctx.send("No recent matches found for analysis.")
                    return
                
                # Create analysis embed
                embed = self.embed_factory.create_analysis_embed(summoner_data, analysis, region)
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error analyzing summoner: {str(e)}")

    @lol.command(name="link")
    async def link_account(self, ctx, region: str, *, summoner_name: str):
        """Link your Discord account to a League of Legends summoner"""
        try:
            region = self.api_manager.normalize_region(region)
            summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
            
            # Save to user config
            await self.config.user(ctx.author).linked_account.set({
                "summoner_name": f"{summoner_data['gameName']}#{summoner_data['tagLine']}",
                "region": region,
                "puuid": summoner_data["puuid"],
                "summoner_id": summoner_data["id"]
            })
            
            await ctx.send(f"✅ Successfully linked your account to **{summoner_data['gameName']}#{summoner_data['tagLine']}** ({region.upper()})")
            
        except Exception as e:
            await ctx.send(f"❌ Error linking account: {str(e)}")

    @commands.has_permissions(manage_guild=True)
    @lol.command(name="notify")
    async def setup_notifications(self, ctx, region: str = None, *, summoner_name: str):
        """Get notified when a summoner starts/ends a game"""
        try:
            region = region or await self.config.guild(ctx.guild).default_region()
            region = self.api_manager.normalize_region(region)
            
            summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
            summoner_data['region'] = region
            
            await self.notification_manager.add_summoner(ctx.guild.id, ctx.channel.id, summoner_data)
            
            await ctx.send(
                f"✅ Now monitoring **{summoner_data['gameName']}#{summoner_data['tagLine']}** "
                f"({region.upper()}) for live games in this channel."
            )
            
        except Exception as e:
            await ctx.send(f"❌ Error setting up notifications: {str(e)}")

    @commands.command(name="unlink")
    async def unlink_account(self, ctx):
        """Unlink your League of Legends account"""
        try:
            linked_account = await self.config.user(ctx.author).linked_account()
            
            if not linked_account:
                await ctx.send("🔗 You don't have a linked League of Legends account.")
                return
            
            await self.config.user(ctx.author).linked_account.clear()
            await ctx.send("✅ Successfully unlinked your League of Legends account.")
            
        except Exception as e:
            await ctx.send(f"❌ Error unlinking account: {str(e)}")

    @commands.has_permissions(manage_guild=True)
    @commands.command(name="unnotify")
    async def remove_notifications(self, ctx, region: str = None, *, summoner_name: str):
        """Stop notifications for a summoner"""
        try:
            region = region or await self.config.guild(ctx.guild).default_region()
            region = self.api_manager.normalize_region(region)
            
            summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
            summoner_data['region'] = region
            
            await self.notification_manager.remove_summoner(ctx.guild.id, summoner_data)
            
            await ctx.send(
                f"✅ Stopped monitoring **{summoner_data['gameName']}#{summoner_data['tagLine']}** "
                f"({region.upper()}) in this server."
            )
            
        except Exception as e:
            await ctx.send(f"❌ Error removing notifications: {str(e)}")

    @commands.cooldown(1, 15, commands.BucketType.user)
    @lol.command(name="build", aliases=["builds", "items"])
    async def build(self, ctx, *, champion_name: str):
        """Get recommended builds and items for a champion"""
        await self.champion_build(ctx, champion_name=champion_name)

    # Maintenance and utility methods
    async def _periodic_cleanup(self):
        """Perform periodic cleanup tasks"""
        try:
            # Clean up expired cache entries
            await self.db_manager.cleanup_expired_cache()
            
            # Clean up old lookup history (older than 30 days)
            await self.db_manager.cleanup_old_lookups(30)
            
            # Clean up old statistics (older than 60 days)
            await self.db_manager.cleanup_old_statistics(60)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during periodic cleanup: {e}")

    # Red-DiscordBot integration methods
    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Format help text for this cog"""
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        text = [
            f"{pre_processed}{n}",
            f"Cog Version: 2.0.0",
            f"API Integration: Riot Games API v5",
            f"Features: Enhanced visuals, live notifications, performance analysis",
        ]
        return "\n".join(text)

async def setup(bot):
    cog = LeagueOfLegends(bot)
    await bot.add_cog(cog)
