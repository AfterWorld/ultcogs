"""
Advanced League of Legends Cog - Main Integration File (Fixed)

Simplified version with graceful error handling and optional features.
"""

import discord
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict
import logging

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.predicates import ReactionPredicate

# Import enhanced components with error handling
try:
    from .analytics import AdvancedAnalytics
    HAS_ANALYTICS = True
except ImportError as e:
    logging.warning(f"Analytics module not available: {e}")
    HAS_ANALYTICS = False
    AdvancedAnalytics = None

try:
    from .lcu_client import LCUClient
    HAS_LCU = True
except ImportError as e:
    logging.warning(f"LCU client not available: {e}")
    HAS_LCU = False
    LCUClient = None

try:
    from .community import CommunityManager
    HAS_COMMUNITY = True
except ImportError as e:
    logging.warning(f"Community features not available: {e}")
    HAS_COMMUNITY = False
    CommunityManager = None

try:
    from .embeds import EnhancedEmbedBuilder
    HAS_EMBEDS = True
except ImportError as e:
    logging.warning(f"Enhanced embeds not available: {e}")
    HAS_EMBEDS = False
    EnhancedEmbedBuilder = None

# Check for aiohttp
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None

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
    """Enhanced League of Legends integration with optional advanced features"""
    
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78945612370, force_registration=True)
        
        default_global = {
            "riot_api_key": "",
            "default_region": "na1",
            "champion_data": {}
        }
        
        default_guild = {
            "live_game_channel": None,
            "auto_update_interval": 30,
            "achievements_enabled": True,
            "leaderboards_enabled": True,
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
        
        # Basic components
        self.session = None
        self.rate_limiter = RateLimiter()
        self.champion_data = {}
        self.live_game_tasks = {}
        
        # Initialize optional enhanced features
        self.analytics = None
        self.lcu_client = None
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
        """Initialize the cog with available features"""
        try:
            # Initialize HTTP session if aiohttp is available
            if HAS_AIOHTTP:
                self.session = aiohttp.ClientSession()
                await self.load_champion_data()
            else:
                logger.warning("HTTP features disabled - aiohttp not installed")
            
            # Initialize optional enhanced features
            if HAS_ANALYTICS:
                self.analytics = AdvancedAnalytics()
                logger.info("✅ Analytics engine loaded")
            
            if HAS_LCU:
                self.lcu_client = LCUClient()
                asyncio.create_task(self._try_lcu_connection())
                logger.info("✅ LCU client loaded")
            
            if HAS_COMMUNITY:
                db_path = str(self.bot.cog_data_path(self) / "community.db")
                self.community_manager = CommunityManager(db_path)
                logger.info("✅ Community features loaded")
            
            if HAS_EMBEDS:
                theme = await self.config.embed_theme() or "gaming"
                self.embed_builder = EnhancedEmbedBuilder(self.champion_data, theme)
                logger.info("✅ Enhanced embeds loaded")
            
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
        if not self.lcu_client:
            return
            
        try:
            await asyncio.sleep(2)  # Wait for cog to fully load
            if await self.lcu_client.connect():
                logger.info("✅ Connected to League Client!")
            else:
                logger.info("❌ League Client not found or not running")
        except Exception as e:
            logger.error(f"LCU connection attempt failed: {e}")
    
    async def load_champion_data(self):
        """Load champion data for ID to name mapping"""
        if not HAS_AIOHTTP or not self.session:
            return
            
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
        if not HAS_AIOHTTP or not self.session:
            return None
            
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
        """Enhanced League of Legends commands"""
        embed = discord.Embed(
            title="🎮 Advanced League of Legends Bot",
            description="League of Legends integration with analytics and community features",
            color=0x00ff88
        )
        
        # Feature status
        features = []
        if HAS_AIOHTTP:
            features.append("✅ Core API functionality")
        else:
            features.append("❌ Core API (install aiohttp)")
            
        if HAS_ANALYTICS:
            features.append("✅ Advanced analytics")
        else:
            features.append("❌ Analytics (module error)")
            
        if HAS_COMMUNITY:
            features.append("✅ Community features")
        else:
            features.append("❌ Community (module error)")
            
        if HAS_LCU:
            features.append("✅ League Client integration")
        else:
            features.append("❌ LCU integration (module error)")
            
        if HAS_EMBEDS:
            features.append("✅ Enhanced embeds")
        else:
            features.append("❌ Enhanced embeds (module error)")
        
        embed.add_field(
            name="🔧 Feature Status",
            value="\n".join(features),
            inline=False
        )
        
        embed.add_field(
            name="📊 Available Commands",
            value="`profile` - Summoner profiles\n"
                  "`live` - Live game analysis\n"
                  "`matches` - Match history\n"
                  "`status` - Check bot status",
            inline=True
        )
        
        if HAS_COMMUNITY:
            embed.add_field(
                name="🏆 Community",
                value="`community profile` - Your stats\n"
                      "`community leaderboard` - Rankings",
                inline=True
            )
        
        if HAS_LCU:
            embed.add_field(
                name="🔗 League Client",
                value="`lcu connect` - Connect to League\n"
                      "`lcu status` - Connection status",
                inline=True
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
        if HAS_AIOHTTP:
            await self.load_champion_data()
    
    @lol_commands.command(name="status")
    async def bot_status(self, ctx):
        """Check bot status and available features"""
        embed = discord.Embed(
            title="🔧 Bot Status",
            color=0x3498db
        )
        
        # API Key status
        api_key = await self.config.riot_api_key()
        embed.add_field(
            name="🔑 API Configuration",
            value="✅ API key configured" if api_key else "❌ No API key set",
            inline=True
        )
        
        # HTTP status
        embed.add_field(
            name="🌐 HTTP Client",
            value="✅ Active" if (HAS_AIOHTTP and self.session) else "❌ Not available",
            inline=True
        )
        
        # Champion data
        embed.add_field(
            name="🎮 Champion Data",
            value=f"✅ {len(self.champion_data)} champions loaded" if self.champion_data else "❌ Not loaded",
            inline=True
        )
        
        # Enhanced features
        if self.analytics:
            embed.add_field(name="📊 Analytics", value="✅ Active", inline=True)
        if self.community_manager:
            embed.add_field(name="🏆 Community", value="✅ Active", inline=True)
        if self.lcu_client:
            lcu_status = "✅ Connected" if self.lcu_client.connected else "⚠️ Available"
            embed.add_field(name="🔗 LCU", value=lcu_status, inline=True)
        
        await ctx.send(embed=embed)
    
    # =============================================================================
    # PROFILE COMMANDS  
    # =============================================================================
    
    @lol_commands.command(name="profile", aliases=["summoner", "p"])
    async def get_profile(self, ctx, summoner_name: str, region: str = "na"):
        """Get summoner profile"""
        if region not in self.regions:
            await ctx.send(f"❌ Invalid region. Available: {', '.join(self.regions.keys())}")
            return
        
        if not HAS_AIOHTTP:
            await ctx.send("❌ Profile lookup requires aiohttp. Install with: `pip install aiohttp`")
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
            
            # Create embed
            if HAS_EMBEDS and self.embed_builder:
                # Use enhanced embed builder
                embed = await self.embed_builder.create_profile_embed_v2(
                    summoner_data, ranked_data or [], mastery_data or []
                )
            else:
                # Use basic embed
                embed = await self._create_basic_profile_embed(summoner_data, ranked_data, mastery_data)
            
            await ctx.send(embed=embed)
            
            # Community integration if available
            if HAS_COMMUNITY and self.community_manager:
                try:
                    achievements = await self.community_manager.check_achievements(
                        str(ctx.author.id), 
                        "profile_linked" if not await self.config.user(ctx.author).profile_linked() else "profiles_checked"
                    )
                    
                    if not await self.config.user(ctx.author).profile_linked():
                        await self.config.user(ctx.author).profile_linked.set(True)
                    
                    # Award achievements if any
                    for achievement in achievements:
                        achievement_embed = discord.Embed(
                            title="🎉 Achievement Unlocked!",
                            description=f"{ctx.author.mention} earned **{achievement.name}**!\n{achievement.emoji} {achievement.description}",
                            color=0xffd700
                        )
                        await ctx.send(embed=achievement_embed)
                except Exception as e:
                    logger.error(f"Community integration error: {e}")
    
    async def _create_basic_profile_embed(self, summoner_data: Dict, ranked_data: List[Dict], mastery_data: List[Dict]) -> discord.Embed:
        """Create basic profile embed without enhanced features"""
        summoner_name = summoner_data.get('name', 'Unknown')
        summoner_level = summoner_data.get('summonerLevel', 0)
        
        embed = discord.Embed(
            title=f"🎮 {summoner_name}",
            color=0x0596aa
        )
        
        embed.add_field(
            name="📊 Profile Info",
            value=f"**Level:** {summoner_level}\n"
                  f"**Account:** {summoner_data.get('accountId', 'Unknown')[:8]}...",
            inline=True
        )
        
        # Ranked information
        if ranked_data:
            ranked_text = ""
            for queue in ranked_data:
                queue_type = queue.get('queueType', 'RANKED_SOLO_5x5').replace('_', ' ')
                tier = queue.get('tier', 'Unranked')
                rank = queue.get('rank', '')
                lp = queue.get('leaguePoints', 0)
                wins = queue.get('wins', 0)
                losses = queue.get('losses', 0)
                
                total_games = wins + losses
                win_rate = (wins / total_games * 100) if total_games > 0 else 0
                
                ranked_text += f"**{queue_type.replace('RANKED', '').strip()}**\n"
                if tier != "Unranked":
                    ranked_text += f"{tier.title()} {rank} ({lp} LP)\n"
                    ranked_text += f"{wins}W / {losses}L ({win_rate:.1f}%)\n\n"
                else:
                    ranked_text += "Unranked\n\n"
            
            embed.add_field(
                name="🏆 Ranked Status",
                value=ranked_text.strip(),
                inline=True
            )
        
        # Champion mastery
        if mastery_data:
            mastery_text = ""
            for i, mastery in enumerate(mastery_data[:3], 1):
                champion_id = mastery.get('championId', 0)
                champion_name = self.champion_data.get(champion_id, {}).get('name', f'Champion {champion_id}')
                level = mastery.get('championLevel', 0)
                points = mastery.get('championPoints', 0)
                
                mastery_text += f"**{i}. {champion_name}**\n"
                mastery_text += f"Level {level} ({points:,} pts)\n\n"
            
            embed.add_field(
                name="⭐ Top Champions",
                value=mastery_text.strip(),
                inline=False
            )
        
        return embed
    
    # =============================================================================
    # LIVE GAME COMMANDS
    # =============================================================================
    
    @lol_commands.command(name="live", aliases=["current", "spectate", "l"])
    async def get_live_game(self, ctx, summoner_name: str, region: str = "na"):
        """Get live game information"""
        if region not in self.regions:
            await ctx.send(f"❌ Invalid region. Available: {', '.join(self.regions.keys())}")
            return
        
        if not HAS_AIOHTTP:
            await ctx.send("❌ Live game lookup requires aiohttp. Install with: `pip install aiohttp`")
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
            
            # Create embeds
            if HAS_EMBEDS and self.embed_builder and HAS_ANALYTICS and self.analytics:
                # Use enhanced features
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
                
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                # Use basic embed
                embed = await self._create_basic_live_game_embed(live_game)
                await ctx.send(embed=embed)
            
            # Community integration if available
            if HAS_COMMUNITY and self.community_manager:
                try:
                    achievements = await self.community_manager.check_achievements(
                        str(ctx.author.id), 
                        "live_games_checked"
                    )
                    
                    for achievement in achievements:
                        achievement_embed = discord.Embed(
                            title="🎉 Achievement Unlocked!",
                            description=f"{ctx.author.mention} earned **{achievement.name}**!",
                            color=0xffd700
                        )
                        await ctx.send(embed=achievement_embed)
                except Exception as e:
                    logger.error(f"Community integration error: {e}")
    
    async def _create_basic_live_game_embed(self, game_data: Dict) -> discord.Embed:
        """Create basic live game embed"""
        game_mode = game_data.get('gameMode', 'Unknown')
        game_length = game_data.get('gameLength', 0)
        
        embed = discord.Embed(
            title=f"🔴 Live Game - {game_mode}",
            description=f"**Duration:** {game_length // 60}m {game_length % 60}s",
            color=0xff6b6b
        )
        
        # Organize teams
        blue_team = []
        red_team = []
        
        for participant in game_data.get('participants', []):
            if participant.get('teamId') == 100:
                blue_team.append(participant)
            else:
                red_team.append(participant)
        
        # Team displays
        for team_name, team_players, color in [
            ("🔵 Blue Team", blue_team, 0x4ecdc4),
            ("🔴 Red Team", red_team, 0xff6b6b)
        ]:
            if team_players:
                team_text = ""
                for player in team_players:
                    champion_id = player.get('championId', 0)
                    champion_name = self.champion_data.get(champion_id, {}).get('name', f'Champion {champion_id}')
                    summoner_name = player.get('summonerName', 'Unknown')
                    
                    team_text += f"**{champion_name}** - {summoner_name}\n"
                
                embed.add_field(
                    name=team_name,
                    value=team_text.strip(),
                    inline=True
                )
        
        return embed
    
    # =============================================================================
    # COMMUNITY COMMANDS (if available)
    # =============================================================================
    
    @lol_commands.group(name="community", aliases=["comm", "c"], invoke_without_command=True)
    async def community_commands(self, ctx):
        """Community features and leaderboards"""
        if not HAS_COMMUNITY:
            await ctx.send("❌ Community features are not available. Check bot status with `[p]lol status`")
            return
        
        embed = discord.Embed(
            title="🏆 Community Features",
            description="Track your progress and compete with other server members!",
            color=0xffd700
        )
        
        embed.add_field(
            name="📊 Available Commands",
            value="`profile` - View your community profile\n"
                  "`leaderboard` - Server rankings\n"
                  "`achievements` - Achievement progress",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @community_commands.command(name="profile", aliases=["me"])
    async def community_profile(self, ctx, user: discord.Member = None):
        """View your or another user's community profile"""
        if not HAS_COMMUNITY:
            await ctx.send("❌ Community features are not available.")
            return
        
        target_user = user or ctx.author
        
        try:
            profile = await self.community_manager.get_user_profile(str(target_user.id))
            
            if not profile:
                if target_user == ctx.author:
                    profile = await self.community_manager.create_user_profile(str(target_user.id))
                    await ctx.send("🎉 Welcome! Your community profile has been created!")
                else:
                    await ctx.send(f"❌ {target_user.display_name} hasn't used the bot yet!")
                    return
            
            embed = discord.Embed(
                title=f"🎮 {target_user.display_name}'s Community Profile",
                color=target_user.color if target_user.color != discord.Color.default() else 0x00ff88
            )
            
            embed.add_field(
                name="📊 Progress",
                value=f"**Level:** {profile.level}\n"
                      f"**Total Points:** {profile.total_points:,}\n"
                      f"**Achievements:** {profile.achievements_count}",
                inline=True
            )
            
            if profile.summoner_name:
                embed.add_field(
                    name="🎯 League Info",
                    value=f"**Summoner:** {profile.summoner_name}\n"
                          f"**Region:** {profile.region.upper() if profile.region else 'Unknown'}",
                    inline=True
                )
            
            embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else None)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in community profile: {e}")
            await ctx.send("❌ Error retrieving community profile.")
    
    @community_commands.command(name="leaderboard", aliases=["lb"])
    async def server_leaderboard(self, ctx, stat_type: str = "total_points"):
        """View server leaderboards"""
        if not HAS_COMMUNITY:
            await ctx.send("❌ Community features are not available.")
            return
        
        try:
            leaderboard_data = await self.community_manager.get_server_leaderboard(
                str(ctx.guild.id), 
                stat_type,
                limit=10
            )
            
            embed = discord.Embed(
                title=f"🏆 {ctx.guild.name} - {stat_type.replace('_', ' ').title()} Leaderboard",
                color=0xffd700
            )
            
            if not leaderboard_data:
                embed.description = "No data available yet. Start using the bot to appear on the leaderboard!"
                await ctx.send(embed=embed)
                return
            
            leaderboard_text = ""
            for i, entry in enumerate(leaderboard_data, 1):
                discord_id, summoner_name, stat_value = entry[:3]
                user = ctx.guild.get_member(int(discord_id))
                display_name = user.display_name if user else (summoner_name or "Unknown User")
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += f"{medal} **{display_name}** - {stat_value:,.0f}\n"
            
            embed.description = leaderboard_text
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard: {e}")
            await ctx.send("❌ Error retrieving leaderboard.")
    
    # =============================================================================
    # LCU INTEGRATION COMMANDS (if available)
    # =============================================================================
    
    @lol_commands.group(name="lcu", invoke_without_command=True)
    async def lcu_commands(self, ctx):
        """League Client integration commands"""
        if not HAS_LCU:
            await ctx.send("❌ LCU integration is not available. Check bot status with `[p]lol status`")
            return
        
        if not self.lcu_client.connected:
            embed = discord.Embed(
                title="🔗 League Client Integration",
                description="Connect to your local League Client for enhanced features!",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="❌ Not Connected",
                value="Use `[p]lol lcu connect` to connect to League Client",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        await ctx.send_help(ctx.command)
    
    @lcu_commands.command(name="connect")
    async def lcu_connect(self, ctx):
        """Connect to League Client"""
        if not HAS_LCU:
            await ctx.send("❌ LCU integration is not available.")
            return
        
        async with ctx.typing():
            if await self.lcu_client.connect():
                embed = discord.Embed(
                    title="✅ Connected to League Client!",
                    color=0x00ff00
                )
                
                current_summoner = await self.lcu_client.get_current_summoner()
                if current_summoner:
                    embed.add_field(
                        name="👤 Logged in as",
                        value=f"**{current_summoner.display_name}**\nLevel {current_summoner.summoner_level}",
                        inline=True
                    )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to connect to League Client. Make sure League is running!")
    
    @lcu_commands.command(name="status")
    async def lcu_status(self, ctx):
        """Check League Client connection status"""
        if not HAS_LCU:
            await ctx.send("❌ LCU integration is not available.")
            return
        
        status = self.lcu_client.get_connection_status()
        
        embed = discord.Embed(
            title="🔗 League Client Status",
            color=0x00ff00 if status['connected'] else 0xff6b6b
        )
        
        embed.add_field(
            name="Connection",
            value="✅ Connected" if status['connected'] else "❌ Disconnected",
            inline=True
        )
        
        if status['connected']:
            current_summoner = await self.lcu_client.get_current_summoner()
            if current_summoner:
                embed.add_field(
                    name="👤 Summoner",
                    value=f"{current_summoner.display_name}\nLevel {current_summoner.summoner_level}",
                    inline=True
                )
        
        await ctx.send(embed=embed)
