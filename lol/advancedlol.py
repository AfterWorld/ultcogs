"""
Advanced League of Legends Cog - Main Integration File

Combines all enhanced features into a comprehensive LoL bot experience.
"""

import discord
import aiohttp
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.predicates import ReactionPredicate

# Import our enhanced components
from .analytics import AdvancedAnalytics
from .lcu_client import LCUClient
from .community import CommunityManager
from .embeds import EnhancedEmbedBuilder

import logging
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for Riot API requests"""
    def __init__(self):
        self.requests = defaultdict(list)
        
    def can_make_request(self, endpoint: str, limit: int, window: int) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[endpoint] = [req_time for req_time in self.requests[endpoint] 
                                  if now - req_time < window]
        return len(self.requests[endpoint]) < limit
    
    def add_request(self, endpoint: str):
        self.requests[endpoint].append(time.time())


class AdvancedLoLv2(commands.Cog):
    """Enhanced League of Legends integration with advanced analytics and community features"""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78945612370, force_registration=True)
        
        default_global = {
            "riot_api_key": "",
            "default_region": "na1",
            "champion_data": {},
            "early_adopter_count": 0
        }
        
        default_guild = {
            "live_game_channel": None,
            "auto_update_interval": 30,
            "achievements_enabled": True,
            "leaderboards_enabled": True,
            "auto_accept_enabled": False,
            "embed_theme": "gaming"
        }
        
        default_user = {
            "summoner_name": "",
            "region": "na1",
            "auto_accept": False,
            "notifications": True,
            "profile_linked": False
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        # Enhanced components
        self.session = None
        self.rate_limiter = RateLimiter()
        self.champion_data = {}
        self.live_game_tasks = {}
        
        # Initialize enhanced features
        self.analytics = AdvancedAnalytics()
        self.lcu_client = LCUClient()
        self.community_manager = None
        self.embed_builder = None
        
        # Champion icon base URL
        self.champion_icon_base = "https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons"
        
        # Region mappings
        self.regions = {
            "na": "na1.api.riotgames.com",
            "euw": "euw1.api.riotgames.com", 
            "eune": "eun1.api.riotgames.com",
            "kr": "kr.api.riotgames.com",
            "jp": "jp1.api.riotgames.com",
            "br": "br1.api.riotgames.com",
            "las": "la1.api.riotgames.com",
            "lan": "la2.api.riotgames.com",
            "oce": "oc1.api.riotgames.com",
            "tr": "tr1.api.riotgames.com",
            "ru": "ru.api.riotgames.com"
        }
        
    async def cog_load(self):
        """Initialize the enhanced cog"""
        try:
            self.session = aiohttp.ClientSession()
            await self.load_champion_data()
            
            # Initialize community features
            db_path = str(self.bot.cog_data_path(self) / "community.db")
            self.community_manager = CommunityManager(db_path)
            
            # Initialize embed builder with theme
            theme = await self.config.embed_theme() or "gaming"
            self.embed_builder = EnhancedEmbedBuilder(self.champion_data, theme)
            
            # Try to connect to LCU
            asyncio.create_task(self._try_lcu_connection())
            
            logger.info("Advanced LoL cog loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading Advanced LoL cog: {e}")
    
    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        try:
            if self.session:
                await self.session.close()
            
            # Disconnect LCU client
            if self.lcu_client:
                await self.lcu_client.disconnect()
            
            # Cancel all live game monitoring tasks
            for task in self.live_game_tasks.values():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            logger.info("Advanced LoL cog unloaded successfully")
            
        except Exception as e:
            logger.error(f"Error unloading Advanced LoL cog: {e}")
    
    async def _try_lcu_connection(self):
        """Attempt to connect to League Client"""
        try:
            await asyncio.sleep(2)  # Wait for cog to fully load
            if await self.lcu_client.connect():
                logger.info("✅ Connected to League Client!")
                # Start LCU event monitoring
                asyncio.create_task(self._monitor_lcu_auto_features())
            else:
                logger.info("❌ League Client not found or not running")
        except Exception as e:
            logger.error(f"LCU connection attempt failed: {e}")
    
    async def load_champion_data(self):
        """Load champion data for ID to name mapping"""
        try:
            # Try to load from config first
            cached_data = await self.config.champion_data()
            if cached_data:
                self.champion_data = {int(k): v for k, v in cached_data.items()}
                return
            
            # Load from Data Dragon if not cached
            url = "https://ddragon.leagueoflegends.com/cdn/14.1.1/data/en_US/champion.json"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    champions = {}
                    for champ_name, champ_data in data['data'].items():
                        champions[int(champ_data['key'])] = {
                            'name': champ_data['name'],
                            'id': champ_data['id'],
                            'title': champ_data['title'],
                            'tags': champ_data['tags'],
                            'role': champ_data['tags'][0] if champ_data['tags'] else 'Unknown'
                        }
                    self.champion_data = champions
                    await self.config.champion_data.set({str(k): v for k, v in champions.items()})
                    logger.info(f"Loaded {len(champions)} champions from Data Dragon")
        except Exception as e:
            logger.error(f"Error loading champion data: {e}")
    
    def get_champion_icon_url(self, champion_id: int) -> str:
        """Get champion icon URL from GitHub repo"""
        return f"{self.champion_icon_base}/{champion_id}.png"
    
    async def make_riot_request(self, endpoint: str, region: str = "na1") -> Optional[Dict]:
        """Make a rate-limited request to Riot API"""
        api_key = await self.config.riot_api_key()
        if not api_key:
            return None
        
        # Check rate limits
        if not self.rate_limiter.can_make_request("global", 20, 1):
            await asyncio.sleep(1)
        
        if not self.rate_limiter.can_make_request(endpoint, 100, 120):
            await asyncio.sleep(60)
        
        base_url = self.regions.get(region, "na1.api.riotgames.com")
        url = f"https://{base_url}{endpoint}"
        
        headers = {"X-Riot-Token": api_key}
        
        try:
            async with self.session.get(url, headers=headers) as resp:
                self.rate_limiter.add_request("global")
                self.rate_limiter.add_request(endpoint)
                
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    # Rate limited
                    retry_after = int(resp.headers.get('Retry-After', 60))
                    await asyncio.sleep(retry_after)
                    return await self.make_riot_request(endpoint, region)
                else:
                    logger.warning(f"API request failed: {resp.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"API request error: {e}")
            return None
    
    # =============================================================================
    # COMMAND GROUPS
    # =============================================================================
    
    @commands.group(name="lol", invoke_without_command=True)
    async def lol_commands(self, ctx):
        """Enhanced League of Legends commands with advanced analytics"""
        embed = discord.Embed(
            title="🎮 Advanced League of Legends Bot",
            description="Professional-grade LoL integration with analytics, community features, and LCU support",
            color=0x00ff88
        )
        
        embed.add_field(
            name="📊 Core Commands",
            value="`profile` - Detailed summoner profiles\n"
                  "`live` - Advanced live game analysis\n"
                  "`matches` - Enhanced match history\n"
                  "`rank` - Ranked statistics",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Community",
            value="`community profile` - Your community stats\n"
                  "`community leaderboard` - Server rankings\n"
                  "`community achievements` - Achievement progress",
            inline=True
        )
        
        embed.add_field(
            name="🔗 League Client",
            value="`lcu connect` - Connect to League\n"
                  "`lcu status` - Client status\n"
                  "`lcu autoaccept` - Toggle auto-accept",
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Setup (Mods Only)",
            value="`setup` - Configure live game channel\n"
                  "`monitor` - Auto-monitor summoners\n"
                  "`theme` - Change embed theme",
            inline=False
        )
        
        embed.set_footer(text="Use [p]help lol <command> for detailed information")
        
        await ctx.send(embed=embed)
    
    # =============================================================================
    # ADMIN COMMANDS
    # =============================================================================
    
    @lol_commands.command(name="setkey")
    @checks.is_owner()
    async def set_api_key(self, ctx, api_key: str):
        """Set the Riot API key"""
        await self.config.riot_api_key.set(api_key)
        await ctx.send("✅ Riot API key has been set!")
        await self.load_champion_data()
    
    @lol_commands.command(name="theme")
    @checks.mod_or_permissions(manage_guild=True)
    async def set_theme(self, ctx, theme: str = None):
        """Set the embed theme for this server"""
        available_themes = ["gaming", "dark", "light", "professional", "default"]
        
        if not theme:
            current_theme = await self.config.guild(ctx.guild).embed_theme()
            embed = discord.Embed(
                title="🎨 Embed Themes",
                description=f"**Current theme:** {current_theme}\n\n"
                           f"**Available themes:**\n" + 
                           "\n".join([f"`{t}`" for t in available_themes]),
                color=0x9b59b6
            )
            await ctx.send(embed=embed)
            return
        
        if theme not in available_themes:
            await ctx.send(f"❌ Invalid theme. Available: {', '.join(available_themes)}")
            return
        
        await self.config.guild(ctx.guild).embed_theme.set(theme)
        
        # Reinitialize embed builder with new theme
        self.embed_builder = EnhancedEmbedBuilder(self.champion_data, theme)
        
        await ctx.send(f"✅ Embed theme set to **{theme}**!")
    
    # =============================================================================
    # PROFILE COMMANDS  
    # =============================================================================
    
    @lol_commands.command(name="profile", aliases=["summoner", "p"])
    async def get_profile_v2(self, ctx, summoner_name: str, region: str = "na"):
        """Get detailed summoner profile with enhanced features"""
        if region not in self.regions:
            await ctx.send(f"❌ Invalid region. Available: {', '.join(self.regions.keys())}")
            return
        
        async with ctx.typing():
            # Get account info
            account_data = await self.make_riot_request(
                f"/riot/account/v1/accounts/by-riot-id/{summoner_name.replace('#', '/')}", 
                region
            )
            
            if not account_data:
                await ctx.send("❌ Summoner not found!")
                return
            
            puuid = account_data['puuid']
            
            # Get summoner data
            summoner_data = await self.make_riot_request(
                f"/lol/summoner/v4/summoners/by-puuid/{puuid}", 
                region
            )
            
            if not summoner_data:
                await ctx.send("❌ Could not retrieve summoner data!")
                return
            
            # Get ranked data
            ranked_data = await self.make_riot_request(
                f"/lol/league/v4/entries/by-summoner/{summoner_data['id']}", 
                region
            )
            
            # Get champion mastery
            mastery_data = await self.make_riot_request(
                f"/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3", 
                region
            )
            
            # Community integration
            await self._update_user_profile_data(ctx.author.id, summoner_name, region)
            
            # Check for achievements
            achievements = await self.community_manager.check_achievements(
                str(ctx.author.id), 
                "profile_linked" if not await self.config.user(ctx.author).profile_linked() else "profiles_checked"
            )
            
            # Mark profile as linked
            if not await self.config.user(ctx.author).profile_linked():
                await self.config.user(ctx.author).profile_linked.set(True)
            
            # Update server stats
            await self.community_manager.increment_server_stat(
                str(ctx.guild.id), 
                str(ctx.author.id), 
                "profiles_checked"
            )
            
            # Create enhanced embed
            user_achievements = await self.community_manager.get_user_achievements(str(ctx.author.id))
            recent_achievements = [a for a, _ in user_achievements[:3]]
            
            embed = await self.embed_builder.create_profile_embed_v2(
                summoner_data, ranked_data or [], mastery_data or [], recent_achievements
            )
            
            await ctx.send(embed=embed)
            
            # Award achievements if any
            for achievement in achievements:
                achievement_embed = await self.embed_builder.create_achievement_embed(
                    achievement, 
                    ctx.author.mention
                )
                await ctx.send(embed=achievement_embed)
    
    async def _update_user_profile_data(self, discord_id: str, summoner_name: str, region: str):
        """Update user profile data in community system"""
        profile = await self.community_manager.get_or_create_user_profile(discord_id)
        
        # Update summoner info if changed
        if profile.summoner_name != summoner_name or profile.region != region:
            await self.community_manager.update_user_stat(discord_id, "summoner_name", summoner_name)
            await self.community_manager.update_user_stat(discord_id, "region", region)
    
    # =============================================================================
    # LIVE GAME COMMANDS
    # =============================================================================
    
    @lol_commands.command(name="live", aliases=["current", "spectate", "l"])
    async def get_live_game_v2(self, ctx, summoner_name: str, region: str = "na"):
        """Get enhanced live game information with advanced analytics"""
        if region not in self.regions:
            await ctx.send(f"❌ Invalid region. Available: {', '.join(self.regions.keys())}")
            return
        
        async with ctx.typing():
            # Get account and summoner info
            account_data = await self.make_riot_request(
                f"/riot/account/v1/accounts/by-riot-id/{summoner_name.replace('#', '/')}", 
                region
            )
            
            if not account_data:
                await ctx.send("❌ Summoner not found!")
                return
            
            puuid = account_data['puuid']
            
            # Get live game data
            live_game = await self.make_riot_request(
                f"/lol/spectator/v5/active-games/by-summoner/{puuid}", 
                region
            )
            
            if not live_game:
                await ctx.send("❌ No active game found for this summoner!")
                return
            
            # Enhanced analytics
            win_prob = await self.analytics.calculate_win_probability(live_game)
            win_prob_dict = {
                "100": win_prob.blue_team_prob,
                "200": win_prob.red_team_prob
            }
            
            # Create enhanced embeds with analytics
            embeds = await self.embed_builder.create_live_game_embed_v2(
                live_game, 
                self.analytics, 
                win_prob_dict
            )
            
            # Community integration
            await self.community_manager.increment_server_stat(
                str(ctx.guild.id), 
                str(ctx.author.id), 
                "live_games_checked"
            )
            
            # Check for special achievements
            achievements = await self._check_live_game_achievements(ctx.author.id, live_game)
            
            # Send enhanced embeds with menu navigation
            await menu(ctx, embeds, DEFAULT_CONTROLS)
            
            # Award achievements if any
            for achievement in achievements:
                achievement_embed = await self.embed_builder.create_achievement_embed(
                    achievement, 
                    ctx.author.mention
                )
                await ctx.send(embed=achievement_embed)
    
    async def _check_live_game_achievements(self, discord_id: str, live_game: Dict) -> List:
        """Check for live game specific achievements"""
        achievements = []
        
        # Check for challenger players
        for participant in live_game.get('participants', []):
            # This would check cached rank data
            # For now, simplified logic
            if 'CHALLENGER' in str(participant).upper():
                challenger_achievements = await self.community_manager.check_achievements(
                    str(discord_id), 
                    "challenger_found"
                )
                achievements.extend(challenger_achievements)
                break
        
        # Check game mode specific achievements
        game_mode = live_game.get('gameMode', '')
        if 'ARAM' in game_mode:
            aram_achievements = await self.community_manager.check_achievements(
                str(discord_id), 
                "aram_games_found"
            )
            achievements.extend(aram_achievements)
        
        # Regular live game achievement
        live_achievements = await self.community_manager.check_achievements(
            str(discord_id), 
            "live_games_checked"
        )
        achievements.extend(live_achievements)
        
        return achievements
    
    # =============================================================================
    # COMMUNITY COMMANDS
    # =============================================================================
    
    @lol_commands.group(name="community", aliases=["comm", "c"], invoke_without_command=True)
    async def community_commands(self, ctx):
        """Community features and leaderboards"""
        embed = discord.Embed(
            title="🏆 Community Features",
            description="Track your progress and compete with other server members!",
            color=0xffd700
        )
        
        embed.add_field(
            name="📊 Your Stats",
            value="`profile` - View your community profile\n"
                  "`achievements` - Achievement progress\n"
                  "`stats` - Detailed statistics",
            inline=True
        )
        
        embed.add_field(
            name="🏆 Leaderboards", 
            value="`leaderboard` - Server rankings\n"
                  "`top` - Top performers\n"
                  "`weekly` - Weekly leaders",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Features",
            value="• Achievement system with rarities\n"
                  "• Server-wide competition\n" 
                  "• Progress tracking\n"
                  "• Exclusive rewards",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @community_commands.command(name="profile", aliases=["me"])
    async def community_profile(self, ctx, user: discord.Member = None):
        """View your or another user's community profile"""
        target_user = user or ctx.author
        
        profile = await self.community_manager.get_user_profile(str(target_user.id))
        
        if not profile:
            if target_user == ctx.author:
                # Create profile for first-time user
                profile = await self.community_manager.create_user_profile(str(target_user.id))
                await ctx.send("🎉 Welcome! Your community profile has been created!")
            else:
                await ctx.send(f"❌ {target_user.display_name} hasn't used the bot yet!")
                return
        
        # Get achievements
        user_achievements = await self.community_manager.get_user_achievements(str(target_user.id))
        
        embed = discord.Embed(
            title=f"🎮 {target_user.display_name}'s Community Profile",
            color=target_user.color if target_user.color != discord.Color.default() else 0x00ff88
        )
        
        # Basic stats
        embed.add_field(
            name="📊 Progress",
            value=f"**Level:** {profile.level}\n"
                  f"**Total Points:** {profile.total_points:,}\n"
                  f"**Achievements:** {profile.achievements_count}",
            inline=True
        )
        
        # League info
        league_info = f"**Summoner:** {profile.summoner_name or 'Not linked'}\n"
        if profile.region:
            league_info += f"**Region:** {profile.region.upper()}\n"
        if profile.favorite_champion:
            league_info += f"**Main:** {profile.favorite_champion}"
        
        embed.add_field(
            name="🎯 League Info",
            value=league_info,
            inline=True
        )
        
        # Recent achievements
        if user_achievements:
            achievement_text = ""
            for achievement, earned_at in user_achievements[:5]:
                days_ago = (datetime.utcnow() - earned_at).days
                time_text = f"{days_ago}d ago" if days_ago > 0 else "Today"
                achievement_text += f"{achievement.emoji} {achievement.name} *({time_text})*\n"
            
            embed.add_field(
                name="🏅 Recent Achievements",
                value=achievement_text,
                inline=False
            )
        
        # Activity timeline
        activity_text = f"**Joined:** {profile.created_at.strftime('%b %d, %Y')}\n"
        activity_text += f"**Last Active:** {profile.last_active.strftime('%b %d, %Y')}"
        
        embed.add_field(
            name="📅 Activity",
            value=activity_text,
            inline=True
        )
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else None)
        
        await ctx.send(embed=embed)
    
    @community_commands.command(name="leaderboard", aliases=["lb", "top"])
    async def server_leaderboard(self, ctx, stat_type: str = "total_points"):
        """View server leaderboards for different statistics"""
        available_stats = [
            "total_points", "live_games_checked", "matches_analyzed", 
            "profiles_checked", "achievements_count"
        ]
        
        if stat_type not in available_stats:
            embed = discord.Embed(
                title="📊 Available Leaderboards",
                description="Choose from the following leaderboard types:",
                color=0x3498db
            )
            
            stats_text = ""
            for stat in available_stats:
                display_name = stat.replace('_', ' ').title()
                stats_text += f"`{stat}` - {display_name}\n"
            
            embed.add_field(
                name="📈 Statistics",
                value=stats_text,
                inline=False
            )
            
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}lol community leaderboard <stat_type>`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Get leaderboard data
        leaderboard_data = await self.community_manager.get_server_leaderboard(
            str(ctx.guild.id), 
            stat_type,
            limit=15
        )
        
        # Create enhanced leaderboard embed
        embed = await self.embed_builder.create_leaderboard_embed(
            ctx.guild, 
            leaderboard_data, 
            stat_type
        )
        
        await ctx.send(embed=embed)
    
    @community_commands.command(name="achievements", aliases=["achieve", "progress"])
    async def achievement_progress(self, ctx, user: discord.Member = None):
        """View achievement progress"""
        target_user = user or ctx.author
        
        # Get achievement progress
        progress = await self.community_manager.get_achievement_progress(str(target_user.id))
        
        if not progress:
            await ctx.send(f"❌ No achievement data found for {target_user.display_name}")
            return
        
        # Organize achievements by category and completion
        completed = []
        in_progress = []
        not_started = []
        
        for achievement in self.community_manager.achievement_manager.achievements:
            if achievement.hidden:
                continue
                
            prog_data = progress.get(achievement.id, {})
            
            if prog_data.get('completed', False):
                completed.append((achievement, prog_data))
            elif prog_data.get('current', 0) > 0:
                in_progress.append((achievement, prog_data))
            else:
                not_started.append((achievement, prog_data))
        
        # Create embeds (paginated if needed)
        embeds = []
        
        # Completed achievements embed
        if completed:
            embed = discord.Embed(
                title=f"🏆 {target_user.display_name}'s Achievements - Completed",
                color=0xffd700
            )
            
            completed_text = ""
            for achievement, prog_data in completed[:10]:  # Limit to prevent overflow
                rarity_emoji = self.community_manager.get_rarity_emoji(achievement.rarity)
                completed_text += f"{rarity_emoji} {achievement.emoji} **{achievement.name}**\n"
                completed_text += f"*{achievement.description}*\n\n"
            
            embed.description = completed_text
            embed.set_footer(text=f"Completed {len(completed)} out of {len(self.community_manager.achievement_manager.achievements)} achievements")
            embeds.append(embed)
        
        # In progress achievements embed  
        if in_progress:
            embed = discord.Embed(
                title=f"⚡ {target_user.display_name}'s Achievements - In Progress",
                color=0x3498db
            )
            
            progress_text = ""
            for achievement, prog_data in in_progress[:8]:
                current = prog_data.get('current', 0)
                requirement = prog_data.get('requirement', 1)
                percentage = prog_data.get('progress', 0)
                
                progress_bar = self.embed_builder._create_progress_bar(percentage, 10)
                
                progress_text += f"{achievement.emoji} **{achievement.name}**\n"
                progress_text += f"Progress: {current}/{requirement} {progress_bar}\n\n"
            
            embed.description = progress_text
            embeds.append(embed)
        
        if not embeds:
            embed = discord.Embed(
                title=f"🎯 {target_user.display_name}'s Achievements",
                description="Start using the bot to unlock achievements!",
                color=0x95a5a6
            )
            embeds.append(embed)
        
        # Send with navigation if multiple embeds
        if len(embeds) > 1:
            await menu(ctx, embeds, DEFAULT_CONTROLS)
        else:
            await ctx.send(embed=embeds[0])
    
    # =============================================================================
    # LCU INTEGRATION COMMANDS
    # =============================================================================
    
    @lol_commands.group(name="lcu", invoke_without_command=True)
    async def lcu_commands(self, ctx):
        """League Client integration commands"""
        if not self.lcu_client.connected:
            embed = discord.Embed(
                title="🔗 League Client Integration",
                description="Connect to your local League Client for enhanced features!",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="❌ Not Connected",
                value="League Client not detected or connection failed.\n\n"
                      "**To connect:**\n"
                      "1. Start League of Legends\n"
                      "2. Use `[p]lol lcu connect`\n"
                      "3. Keep League running for features",
                inline=False
            )
            
            embed.add_field(
                name="🚀 Features",
                value="• Auto-accept matchmaking queue\n"
                      "• Real-time game state monitoring\n"
                      "• Champion select integration\n" 
                      "• Automatic notifications",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        await ctx.send_help(ctx.command)
    
    @lcu_commands.command(name="connect")
    async def lcu_connect(self, ctx):
        """Connect to League Client"""
        async with ctx.typing():
            if await self.lcu_client.connect():
                current_summoner = await self.lcu_client.get_current_summoner()
                
                embed = discord.Embed(
                    title="✅ Connected to League Client!",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                
                if current_summoner:
                    embed.add_field(
                        name="👤 Logged in as",
                        value=f"**{current_summoner.display_name}**\nLevel {current_summoner.summoner_level}",
                        inline=True
                    )
                
                # Get game state
                gameflow_phase = await self.lcu_client.get_gameflow_phase()
                if gameflow_phase:
                    embed.add_field(
                        name="🎮 Game State",
                        value=gameflow_phase.replace('"', ''),
                        inline=True
                    )
                
                embed.add_field(
                    name="🎯 Available Features",
                    value="• Auto-accept queue\n• Real-time notifications\n• Champion select info",
                    inline=False
                )
                
                embed.set_footer(text="Use 'lol lcu autoaccept' to enable auto-accept")
                
                await ctx.send(embed=embed)
                
                # Start monitoring task if not already running
                if not hasattr(self, '_lcu_monitoring_task') or self._lcu_monitoring_task.done():
                    self._lcu_monitoring_task = asyncio.create_task(self._monitor_lcu_auto_features())
                    
            else:
                embed = discord.Embed(
                    title="❌ Failed to connect to League Client",
                    description="Make sure League of Legends is running and try again.\n\n"
                               "**Troubleshooting:**\n"
                               "• Restart League of Legends\n"
                               "• Run as administrator (Windows)\n"
                               "• Check firewall settings",
                    color=0xff6b6b
                )
                await ctx.send(embed=embed)
    
    @lcu_commands.command(name="status")
    async def lcu_status(self, ctx):
        """Check League Client connection status"""
        status = self.lcu_client.get_connection_status()
        
        if not status['connected']:
            embed = discord.Embed(
                title="❌ League Client - Disconnected",
                color=0xff6b6b
            )
            embed.add_field(
                name="Connection Status",
                value="Not connected to League Client",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔗 League Client Status",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        
        # Get current summoner info
        current_summoner = await self.lcu_client.get_current_summoner()
        if current_summoner:
            embed.add_field(
                name="👤 Current Summoner",
                value=f"**{current_summoner.display_name}**\nLevel {current_summoner.summoner_level}",
                inline=True
            )
        
        # Get game state
        gameflow_phase = await self.lcu_client.get_gameflow_phase()
        champion_select = await self.lcu_client.get_champion_select_state()
        
        if champion_select:
            embed.add_field(
                name="🎯 Champion Select",
                value="Currently in champion select",
                inline=True
            )
        elif gameflow_phase:
            phase_clean = gameflow_phase.replace('"', '')
            embed.add_field(
                name="🎮 Game State",
                value=phase_clean,
                inline=True
            )
        
        # Auto-accept status
        user_auto_accept = self.lcu_client.is_auto_accept_enabled(str(ctx.author.id))
        embed.add_field(
            name="⚡ Auto-Accept",
            value="Enabled" if user_auto_accept else "Disabled",
            inline=True
        )
        
        # Connection details
        embed.add_field(
            name="🔧 Connection Details",
            value=f"WebSocket: {'✅' if status['has_websocket'] else '❌'}\n"
                  f"Active Users: {status['auto_accept_users']}\n"
                  f"Reconnects: {status['reconnect_attempts']}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @lcu_commands.command(name="autoaccept", aliases=["auto"])
    async def toggle_auto_accept(self, ctx):
        """Toggle automatic queue acceptance"""
        if not self.lcu_client.connected:
            await ctx.send("❌ Not connected to League Client! Use `[p]lol lcu connect` first.")
            return
        
        current = await self.config.user(ctx.author).auto_accept()
        new_value = not current
        await self.config.user(ctx.author).auto_accept.set(new_value)
        
        # Update LCU client
        if new_value:
            self.lcu_client.enable_auto_accept(str(ctx.author.id))
        else:
            self.lcu_client.disable_auto_accept(str(ctx.author.id))
        
        status = "enabled" if new_value else "disabled"
        emoji = "✅" if new_value else "❌"
        
        embed = discord.Embed(
            title=f"{emoji} Auto-Accept {status.title()}",
            description=f"Queue auto-accept has been **{status}** for you.",
            color=0x00ff00 if new_value else 0xff6b6b
        )
        
        if new_value:
            embed.add_field(
                name="ℹ️ How it works",
                value="• Keep League running\n"
                      "• Bot will auto-accept when queue pops\n"
                      "• You'll get a DM notification\n"
                      "• Only works when bot is connected",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def _monitor_lcu_auto_features(self):
        """Monitor LCU events for auto-features"""
        logger.info("Started LCU auto-features monitoring")
        
        while self.lcu_client.connected:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # This is a simplified monitoring loop
                # In a full implementation, you'd use the WebSocket events
                # from the LCU client to trigger auto-accept
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in LCU monitoring: {e}")
                await asyncio.sleep(10)
        
        logger.info("LCU auto-features monitoring stopped")
    
    # =============================================================================
    # SETUP AND MONITORING COMMANDS
    # =============================================================================
    
    @lol_commands.command(name="setup")
    @checks.mod_or_permissions(manage_guild=True)
    async def setup_live_channel(self, ctx, channel: discord.TextChannel = None):
        """Set up automatic live game monitoring for a channel"""
        if not channel:
            channel = ctx.channel
        
        await self.config.guild(ctx.guild).live_game_channel.set(channel.id)
        
        embed = discord.Embed(
            title="✅ Live Game Monitoring Setup",
            description=f"Automatic live game notifications will be posted in {channel.mention}",
            color=0x00ff00
        )
        
        embed.add_field(
            name="📋 Next Steps",
            value=f"Use `{ctx.prefix}lol monitor <summoner> <region>` to start monitoring specific players",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @lol_commands.command(name="monitor")
    @checks.mod_or_permissions(manage_guild=True)
    async def monitor_summoner(self, ctx, summoner_name: str, region: str = "na"):
        """Start monitoring a summoner for live games"""
        if region not in self.regions:
            await ctx.send(f"❌ Invalid region. Available: {', '.join(self.regions.keys())}")
            return
        
        guild_id = ctx.guild.id
        
        # Cancel existing task if any
        if guild_id in self.live_game_tasks:
            self.live_game_tasks[guild_id].cancel()
            try:
                await self.live_game_tasks[guild_id]
            except asyncio.CancelledError:
                pass
        
        # Start new monitoring task
        task = asyncio.create_task(
            self._monitor_live_games(ctx, summoner_name, region)
        )
        self.live_game_tasks[guild_id] = task
        
        embed = discord.Embed(
            title="🔄 Live Game Monitoring Started",
            description=f"Now monitoring **{summoner_name}** ({region.upper()}) for live games!",
            color=0x00ff88
        )
        
        embed.add_field(
            name="ℹ️ Monitoring Details",
            value="• Checks every 30 seconds\n"
                  "• Posts when new games start\n"
                  "• Includes advanced analytics\n"
                  "• Automatic until manually stopped",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _monitor_live_games(self, ctx, summoner_name: str, region: str):
        """Background task to monitor live games"""
        channel_id = await self.config.guild(ctx.guild).live_game_channel()
        if not channel_id:
            return
        
        channel = self.bot.get_channel(channel_id)
        if not channel:
            return
        
        last_game_id = None
        error_count = 0
        
        logger.info(f"Starting live game monitoring for {summoner_name} in {ctx.guild.name}")
        
        while True:
            try:
                # Get account info
                account_data = await self.make_riot_request(
                    f"/riot/account/v1/accounts/by-riot-id/{summoner_name.replace('#', '/')}", 
                    region
                )
                
                if account_data:
                    puuid = account_data['puuid']
                    live_game = await self.make_riot_request(
                        f"/lol/spectator/v5/active-games/by-summoner/{puuid}", 
                        region
                    )
                    
                    if live_game and live_game.get('gameId') != last_game_id:
                        last_game_id = live_game.get('gameId')
                        
                        # Create notification with analytics
                        win_prob = await self.analytics.calculate_win_probability(live_game)
                        win_prob_dict = {
                            "100": win_prob.blue_team_prob,
                            "200": win_prob.red_team_prob
                        }
                        
                        embeds = await self.embed_builder.create_live_game_embed_v2(
                            live_game, 
                            self.analytics, 
                            win_prob_dict
                        )
                        
                        # Send notification
                        await channel.send(f"🔴 **{summoner_name}** just started a live game!")
                        await menu(channel, embeds, DEFAULT_CONTROLS)
                        
                        logger.info(f"Posted live game notification for {summoner_name}")
                
                error_count = 0  # Reset error count on success
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info(f"Live game monitoring cancelled for {summoner_name}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Monitor error for {summoner_name}: {e}")
                
                if error_count >= 5:
                    # Stop monitoring after 5 consecutive errors
                    await channel.send(f"❌ Stopped monitoring {summoner_name} due to repeated errors.")
                    break
                    
                await asyncio.sleep(60)  # Wait longer on error
