import discord
import aiohttp
import asyncio
import websockets
import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, Counter
import math
import base64
import ssl
from dataclasses import dataclass

from redbot.core import commands, Config, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.predicates import ReactionPredicate

# Advanced Data Classes
@dataclass
class LiveGameState:
    game_id: str
    game_mode: str
    game_length: int
    participants: List[Dict]
    teams: Dict[str, List[Dict]]
    objectives: Dict
    gold_diff: int
    xp_diff: int
    win_probability: Dict[str, float]

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    emoji: str
    rarity: str
    points: int

class AdvancedAnalytics:
    """Advanced game analysis and prediction engine"""
    
    def __init__(self):
        self.win_rate_cache = {}
        self.meta_champions = {}
        
    def calculate_win_probability(self, game_data: Dict, historical_data: List[Dict] = None) -> Dict[str, float]:
        """Calculate real-time win probability based on multiple factors"""
        blue_team = []
        red_team = []
        
        for participant in game_data.get('participants', []):
            if participant['teamId'] == 100:
                blue_team.append(participant)
            else:
                red_team.append(participant)
        
        # Base probability factors
        blue_factors = self._calculate_team_strength(blue_team)
        red_factors = self._calculate_team_strength(red_team)
        
        # Game length factor (some comps are early/late game)
        game_length = game_data.get('gameLength', 0)
        length_modifier = self._get_length_modifier(blue_team, red_team, game_length)
        
        # Calculate final probabilities
        blue_score = blue_factors + length_modifier
        red_score = red_factors - length_modifier
        
        total = blue_score + red_score
        if total <= 0:
            return {"100": 50.0, "200": 50.0}
            
        blue_prob = (blue_score / total) * 100
        red_prob = (red_score / total) * 100
        
        return {"100": max(5.0, min(95.0, blue_prob)), "200": max(5.0, min(95.0, red_prob))}
    
    def _calculate_team_strength(self, team: List[Dict]) -> float:
        """Calculate team strength based on champion synergy and player skill"""
        strength = 0.0
        
        for player in team:
            champion_id = player.get('championId', 0)
            
            # Champion meta strength (would be loaded from data)
            champion_strength = self.meta_champions.get(champion_id, 50.0)
            
            # Player skill factor (based on rank if available)
            player_skill = self._get_player_skill_factor(player)
            
            strength += (champion_strength + player_skill) / 2
        
        return strength / len(team) if team else 0.0
    
    def _get_player_skill_factor(self, player: Dict) -> float:
        """Convert player rank to numerical factor"""
        # This would integrate with cached ranked data
        return 50.0  # Default neutral factor
    
    def _get_length_modifier(self, blue_team: List, red_team: List, game_length: int) -> float:
        """Calculate game length advantage modifier"""
        # Early game champions get advantage in short games
        # Late game champions get advantage in long games
        if game_length < 900:  # < 15 minutes
            return 0.0  # Neutral in early game
        elif game_length > 1800:  # > 30 minutes
            return 2.0  # Late game advantage
        else:
            return game_length / 900  # Gradual scaling
    
    def analyze_team_composition(self, team: List[Dict]) -> Dict:
        """Analyze team composition strengths and weaknesses"""
        analysis = {
            "damage_sources": {"ap": 0, "ad": 0, "true": 0},
            "roles_filled": set(),
            "engage_potential": 0,
            "peel_potential": 0,
            "scaling": "mid",  # early, mid, late
            "synergies": []
        }
        
        for player in team:
            champion_id = player.get('championId', 0)
            # Would analyze based on champion data
            # This is a simplified version
            
        return analysis

class LCUClient:
    """League Client API integration for local features"""
    
    def __init__(self):
        self.connected = False
        self.websocket = None
        self.credentials = None
        self.session = None
        
    async def connect(self) -> bool:
        """Connect to local League Client"""
        try:
            # Get LCU credentials from lockfile
            credentials = await self._get_lcu_credentials()
            if not credentials:
                return False
                
            self.credentials = credentials
            
            # Create SSL context that ignores self-signed certs
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create authenticated session
            auth = base64.b64encode(f"riot:{credentials['password']}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector
            )
            
            # Test connection
            url = f"https://127.0.0.1:{credentials['port']}/lol-summoner/v1/current-summoner"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    self.connected = True
                    # Start WebSocket connection for events
                    await self._connect_websocket()
                    return True
                    
        except Exception as e:
            print(f"LCU connection error: {e}")
            
        return False
    
    async def _get_lcu_credentials(self) -> Optional[Dict]:
        """Get LCU credentials from lockfile"""
        import os
        import psutil
        
        try:
            # Find League Client process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['name'] in ['LeagueClient.exe', 'LeagueClient']:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    # Extract port and auth token from command line
                    port = None
                    auth_token = None
                    
                    for arg in cmdline:
                        if '--app-port=' in arg:
                            port = arg.split('=')[1]
                        elif '--remoting-auth-token=' in arg:
                            auth_token = arg.split('=')[1]
                    
                    if port and auth_token:
                        return {
                            'port': port,
                            'password': auth_token
                        }
                        
        except Exception as e:
            print(f"Error getting LCU credentials: {e}")
            
        return None
    
    async def _connect_websocket(self):
        """Connect to LCU WebSocket for real-time events"""
        try:
            if not self.credentials:
                return
                
            uri = f"wss://127.0.0.1:{self.credentials['port']}/"
            
            # WebSocket with authentication
            auth = base64.b64encode(f"riot:{self.credentials['password']}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.websocket = await websockets.connect(
                uri, 
                extra_headers=headers,
                ssl=ssl_context
            )
            
            # Subscribe to relevant events
            await self.websocket.send(json.dumps([5, "OnJsonApiEvent"]))
            
        except Exception as e:
            print(f"WebSocket connection error: {e}")
    
    async def get_current_summoner(self) -> Optional[Dict]:
        """Get current logged-in summoner"""
        if not self.connected or not self.session:
            return None
            
        try:
            url = f"https://127.0.0.1:{self.credentials['port']}/lol-summoner/v1/current-summoner"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            print(f"Error getting current summoner: {e}")
            
        return None
    
    async def get_champion_select_state(self) -> Optional[Dict]:
        """Get current champion select state"""
        if not self.connected or not self.session:
            return None
            
        try:
            url = f"https://127.0.0.1:{self.credentials['port']}/lol-champ-select/v1/session"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 404:
                    return None  # Not in champion select
        except Exception as e:
            print(f"Error getting champion select: {e}")
            
        return None
    
    async def auto_accept_queue(self) -> bool:
        """Automatically accept matchmaking queue"""
        if not self.connected or not self.session:
            return False
            
        try:
            url = f"https://127.0.0.1:{self.credentials['port']}/lol-matchmaking/v1/ready-check/accept"
            async with self.session.post(url) as resp:
                return resp.status == 204
        except Exception as e:
            print(f"Error auto-accepting queue: {e}")
            
        return False

class CommunityManager:
    """Manages community features, achievements, and leaderboards"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.achievements = self._load_achievements()
        self._init_database()
    
    def _init_database(self):
        """Initialize community database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                discord_id TEXT PRIMARY KEY,
                summoner_name TEXT,
                region TEXT,
                total_points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT,
                achievement_id TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (discord_id) REFERENCES user_profiles (discord_id)
            )
        ''')
        
        # Server leaderboards
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_stats (
                guild_id TEXT,
                discord_id TEXT,
                stat_type TEXT,
                stat_value REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, discord_id, stat_type)
            )
        ''')
        
        # Community challenges
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT,
                name TEXT,
                description TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                reward_points INTEGER,
                active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_achievements(self) -> List[Achievement]:
        """Load all available achievements"""
        return [
            Achievement("first_profile", "First Steps", "Link your first League profile", "🎮", "common", 10),
            Achievement("live_game_hunter", "Live Game Hunter", "Check 10 live games", "🔴", "common", 25),
            Achievement("match_analyst", "Match Analyst", "View 50 match histories", "📊", "uncommon", 50),
            Achievement("challenger_spotter", "Challenger Spotter", "Find a Challenger player", "💎", "rare", 100),
            Achievement("pentakill_witness", "Pentakill Witness", "Discover a pentakill in match history", "⭐", "epic", 200),
            Achievement("dedication", "Dedicated Fan", "Use the bot for 30 days", "💪", "legendary", 500),
            Achievement("community_leader", "Community Leader", "Help 10 other users", "👑", "mythic", 1000),
        ]
    
    async def check_achievements(self, discord_id: str, action: str, data: Dict = None) -> List[Achievement]:
        """Check and award achievements for user actions"""
        earned = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user's current achievements
        cursor.execute(
            "SELECT achievement_id FROM user_achievements WHERE discord_id = ?",
            (discord_id,)
        )
        current_achievements = {row[0] for row in cursor.fetchall()}
        
        for achievement in self.achievements:
            if achievement.id in current_achievements:
                continue
                
            should_award = False
            
            # Check achievement conditions
            if achievement.id == "first_profile" and action == "profile_linked":
                should_award = True
            elif achievement.id == "live_game_hunter" and action == "live_game_checked":
                cursor.execute(
                    "SELECT COUNT(*) FROM server_stats WHERE discord_id = ? AND stat_type = 'live_games_checked'",
                    (discord_id,)
                )
                count = cursor.fetchone()[0] or 0
                if count >= 10:
                    should_award = True
            elif achievement.id == "challenger_spotter" and action == "challenger_found":
                should_award = True
            # Add more achievement logic here
            
            if should_award:
                # Award achievement
                cursor.execute(
                    "INSERT INTO user_achievements (discord_id, achievement_id) VALUES (?, ?)",
                    (discord_id, achievement.id)
                )
                
                # Add points to user
                cursor.execute(
                    "UPDATE user_profiles SET total_points = total_points + ? WHERE discord_id = ?",
                    (achievement.points, discord_id)
                )
                
                earned.append(achievement)
        
        conn.commit()
        conn.close()
        
        return earned
    
    async def get_server_leaderboard(self, guild_id: str, stat_type: str, limit: int = 10) -> List[Tuple]:
        """Get server leaderboard for specific stat"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ss.discord_id, up.summoner_name, ss.stat_value, up.total_points
            FROM server_stats ss
            JOIN user_profiles up ON ss.discord_id = up.discord_id
            WHERE ss.guild_id = ? AND ss.stat_type = ?
            ORDER BY ss.stat_value DESC
            LIMIT ?
        ''', (guild_id, stat_type, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return results

class EnhancedEmbedBuilder:
    """Creates sophisticated Discord embeds with interactive elements"""
    
    def __init__(self, champion_data: Dict):
        self.champion_data = champion_data
        self.champion_icon_base = "https://raw.githubusercontent.com/AfterWorld/ultcogs/main/lol/championicons"
    
    async def create_live_game_embed_v2(self, game_data: Dict, analytics: AdvancedAnalytics) -> List[discord.Embed]:
        """Create enhanced live game embeds with analytics"""
        embeds = []
        
        # Main game embed with win probability
        win_prob = analytics.calculate_win_probability(game_data)
        game_mode = game_data.get('gameMode', 'Unknown')
        game_length = game_data.get('gameLength', 0)
        
        main_embed = discord.Embed(
            title=f"🔴 Live Game Analysis - {game_mode}",
            description=f"⏱️ **Duration:** {game_length // 60}m {game_length % 60}s\n"
                       f"📊 **Win Probability**\n"
                       f"🔵 Blue Team: **{win_prob['100']:.1f}%**\n"
                       f"🔴 Red Team: **{win_prob['200']:.1f}%**",
            color=0x00ff88,
            timestamp=datetime.utcnow()
        )
        
        # Add game analysis
        if game_length > 0:
            phase = self._get_game_phase(game_length)
            main_embed.add_field(
                name="📈 Game Phase",
                value=f"**{phase}**\n{self._get_phase_description(phase)}",
                inline=True
            )
        
        embeds.append(main_embed)
        
        # Enhanced team embeds
        teams = {"100": [], "200": []}
        for participant in game_data.get('participants', []):
            teams[str(participant['teamId'])].append(participant)
        
        team_colors = {"100": 0x4ecdc4, "200": 0xff6b6b}
        team_names = {"100": "🔵 Blue Team", "200": "🔴 Red Team"}
        
        for team_id, players in teams.items():
            if not players:
                continue
                
            embed = discord.Embed(
                title=f"{team_names[team_id]} - {win_prob[team_id]:.1f}% Win Rate",
                color=team_colors[team_id]
            )
            
            # Team composition analysis
            comp_analysis = analytics.analyze_team_composition(players)
            embed.description = f"**Team Composition Analysis**\n" \
                              f"Scaling: {comp_analysis['scaling'].title()} Game\n" \
                              f"Engage: {'High' if comp_analysis['engage_potential'] > 7 else 'Medium' if comp_analysis['engage_potential'] > 4 else 'Low'}"
            
            for i, player in enumerate(players, 1):
                champ_id = player.get('championId', 0)
                champ_data = self.champion_data.get(champ_id, {})
                champ_name = champ_data.get('name', f'Champion {champ_id}')
                summoner_name = player.get('summonerName', 'Unknown')
                
                # Enhanced player info with rank and performance indicators
                rank_info = self._get_rank_display(player)
                performance_emoji = self._get_performance_emoji(player, champ_id)
                
                embed.add_field(
                    name=f"{performance_emoji} {champ_name}",
                    value=f"**{summoner_name}**\n{rank_info}",
                    inline=True
                )
            
            embeds.append(embed)
        
        return embeds
    
    def _get_game_phase(self, game_length: int) -> str:
        """Determine current game phase"""
        if game_length < 900:  # < 15 min
            return "Early Game"
        elif game_length < 1800:  # < 30 min
            return "Mid Game"
        else:
            return "Late Game"
    
    def _get_phase_description(self, phase: str) -> str:
        """Get description for game phase"""
        descriptions = {
            "Early Game": "Laning phase, focus on CS and objectives",
            "Mid Game": "Team fights and objective control",
            "Late Game": "High-stakes team fights, one mistake can end the game"
        }
        return descriptions.get(phase, "")
    
    def _get_rank_display(self, player: Dict) -> str:
        """Get formatted rank display"""
        # This would integrate with cached rank data
        return "Unranked"
    
    def _get_performance_emoji(self, player: Dict, champ_id: int) -> str:
        """Get performance indicator emoji"""
        # This would analyze player's performance on this champion
        return "⚔️"
    
    async def create_achievement_embed(self, achievement: Achievement, user_mention: str) -> discord.Embed:
        """Create achievement unlock embed"""
        rarity_colors = {
            "common": 0x95a5a6,
            "uncommon": 0x2ecc71,
            "rare": 0x3498db,
            "epic": 0x9b59b6,
            "legendary": 0xf39c12,
            "mythic": 0xe74c3c
        }
        
        embed = discord.Embed(
            title=f"🎉 Achievement Unlocked!",
            description=f"{user_mention} earned **{achievement.name}**!\n\n"
                       f"{achievement.emoji} {achievement.description}\n"
                       f"**+{achievement.points} points**",
            color=rarity_colors.get(achievement.rarity, 0x95a5a6)
        )
        
        embed.add_field(
            name="Rarity",
            value=achievement.rarity.title(),
            inline=True
        )
        
        embed.set_footer(text=f"Achievement Points: {achievement.points}")
        
        return embed
    
    async def create_leaderboard_embed(self, guild: discord.Guild, leaderboard_data: List[Tuple], stat_type: str) -> discord.Embed:
        """Create server leaderboard embed"""
        embed = discord.Embed(
            title=f"🏆 {guild.name} - {stat_type.replace('_', ' ').title()} Leaderboard",
            color=0xffd700
        )
        
        if not leaderboard_data:
            embed.description = "No data available yet. Start using the bot to appear on the leaderboard!"
            return embed
        
        leaderboard_text = ""
        for i, (discord_id, summoner_name, stat_value, total_points) in enumerate(leaderboard_data, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            user = guild.get_member(int(discord_id))
            display_name = user.display_name if user else summoner_name
            
            leaderboard_text += f"{medal} **{display_name}** - {stat_value:,.0f}\n"
        
        embed.description = leaderboard_text
        embed.set_footer(text="Use the bot more to climb the leaderboard!")
        
        return embed

# Enhanced main cog class with new features
class AdvancedLoLv2(commands.Cog):
    """Enhanced League of Legends integration with advanced analytics and community features"""
    
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
            "auto_accept_enabled": False
        }
        
        default_user = {
            "summoner_name": "",
            "region": "na1",
            "auto_accept": False,
            "notifications": True
        }
        
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
        
        # Enhanced components
        self.session = None
        self.rate_limiter = RateLimiter()
        self.champion_data = {}
        self.live_game_tasks = {}
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
        self.session = aiohttp.ClientSession()
        await self.load_champion_data()
        
        # Initialize community features
        db_path = str(self.bot.get_cog_path(self) / "community.db")
        self.community_manager = CommunityManager(db_path)
        self.embed_builder = EnhancedEmbedBuilder(self.champion_data)
        
        # Try to connect to LCU
        asyncio.create_task(self._try_lcu_connection())
        
    async def _try_lcu_connection(self):
        """Attempt to connect to League Client"""
        try:
            if await self.lcu_client.connect():
                print("✅ Connected to League Client!")
            else:
                print("❌ League Client not found or not running")
        except Exception as e:
            print(f"LCU connection attempt failed: {e}")
    
    # ... (keeping existing basic methods from original cog)
    
    @commands.group(name="lol", invoke_without_command=True)
    async def lol_commands(self, ctx):
        """Enhanced League of Legends commands"""
        await ctx.send_help(ctx.command)
    
    @lol_commands.command(name="live", aliases=["current", "spectate"])
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
            
            # Create enhanced embeds with analytics
            embeds = await self.embed_builder.create_live_game_embed_v2(live_game, self.analytics)
            await menu(ctx, embeds, DEFAULT_CONTROLS)
            
            # Track achievement
            achievements = await self.community_manager.check_achievements(
                str(ctx.author.id), 
                "live_game_checked"
            )
            
            # Award achievements if any
            for achievement in achievements:
                embed = await self.embed_builder.create_achievement_embed(achievement, ctx.author.mention)
                await ctx.send(embed=embed)
    
    @lol_commands.group(name="community", invoke_without_command=True)
    async def community_commands(self, ctx):
        """Community features and leaderboards"""
        await ctx.send_help(ctx.command)
    
    @community_commands.command(name="profile")
    async def community_profile(self, ctx, user: discord.Member = None):
        """View your or another user's community profile"""
        target_user = user or ctx.author
        
        conn = sqlite3.connect(self.community_manager.db_path)
        cursor = conn.cursor()
        
        # Get user profile
        cursor.execute(
            "SELECT * FROM user_profiles WHERE discord_id = ?",
            (str(target_user.id),)
        )
        profile = cursor.fetchone()
        
        if not profile:
            await ctx.send(f"❌ {target_user.display_name} hasn't linked their League profile yet!")
            conn.close()
            return
        
        # Get achievements
        cursor.execute('''
            SELECT a.achievement_id, a.earned_at 
            FROM user_achievements a 
            WHERE a.discord_id = ? 
            ORDER BY a.earned_at DESC
        ''', (str(target_user.id),))
        user_achievements = cursor.fetchall()
        
        conn.close()
        
        embed = discord.Embed(
            title=f"🎮 {target_user.display_name}'s Profile",
            color=target_user.color
        )
        
        embed.add_field(
            name="📊 Stats",
            value=f"**Level:** {profile[4]}\n"
                  f"**Total Points:** {profile[3]:,}\n"
                  f"**Summoner:** {profile[1]} ({profile[2].upper()})",
            inline=True
        )
        
        if user_achievements:
            achievement_text = ""
            for achievement_id, earned_at in user_achievements[:5]:  # Show latest 5
                achievement = next((a for a in self.community_manager.achievements if a.id == achievement_id), None)
                if achievement:
                    achievement_text += f"{achievement.emoji} {achievement.name}\n"
            
            embed.add_field(
                name=f"🏆 Achievements ({len(user_achievements)})",
                value=achievement_text or "No achievements yet",
                inline=True
            )
        
        embed.set_thumbnail(url=target_user.avatar.url if target_user.avatar else None)
        
        await ctx.send(embed=embed)
    
    @community_commands.command(name="leaderboard", aliases=["lb"])
    async def server_leaderboard(self, ctx, stat_type: str = "total_points"):
        """View server leaderboards"""
        available_stats = ["total_points", "live_games_checked", "matches_analyzed"]
        
        if stat_type not in available_stats:
            await ctx.send(f"❌ Invalid stat type. Available: {', '.join(available_stats)}")
            return
        
        leaderboard_data = await self.community_manager.get_server_leaderboard(
            str(ctx.guild.id), 
            stat_type
        )
        
        embed = await self.embed_builder.create_leaderboard_embed(
            ctx.guild, 
            leaderboard_data, 
            stat_type
        )
        
        await ctx.send(embed=embed)
    
    @lol_commands.group(name="lcu", invoke_without_command=True)
    async def lcu_commands(self, ctx):
        """League Client integration commands"""
        if not self.lcu_client.connected:
            await ctx.send("❌ Not connected to League Client. Make sure League is running and try `[p]lol lcu connect`")
            return
        
        await ctx.send_help(ctx.command)
    
    @lcu_commands.command(name="connect")
    async def lcu_connect(self, ctx):
        """Connect to League Client"""
        async with ctx.typing():
            if await self.lcu_client.connect():
                current_summoner = await self.lcu_client.get_current_summoner()
                if current_summoner:
                    embed = discord.Embed(
                        title="✅ Connected to League Client!",
                        description=f"**Logged in as:** {current_summoner['displayName']}\n"
                                   f"**Level:** {current_summoner['summonerLevel']}",
                        color=0x00ff00
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("✅ Connected to League Client!")
            else:
                await ctx.send("❌ Failed to connect to League Client. Make sure League is running!")
    
    @lcu_commands.command(name="status")
    async def lcu_status(self, ctx):
        """Check League Client connection status"""
        if not self.lcu_client.connected:
            await ctx.send("❌ Not connected to League Client")
            return
        
        current_summoner = await self.lcu_client.get_current_summoner()
        champion_select = await self.lcu_client.get_champion_select_state()
        
        embed = discord.Embed(
            title="🔗 League Client Status",
            color=0x00ff00
        )
        
        if current_summoner:
            embed.add_field(
                name="👤 Current Summoner",
                value=f"**{current_summoner['displayName']}**\nLevel {current_summoner['summonerLevel']}",
                inline=True
            )
        
        if champion_select:
            embed.add_field(
                name="🎯 Champion Select",
                value="Currently in champion select",
                inline=True
            )
        else:
            embed.add_field(
                name="🎯 Champion Select",
                value="Not in champion select",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @lcu_commands.command(name="autoaccept")
    async def toggle_auto_accept(self, ctx):
        """Toggle automatic queue acceptance"""
        current = await self.config.user(ctx.author).auto_accept()
        new_value = not current
        await self.config.user(ctx.author).auto_accept.set(new_value)
        
        status = "enabled" if new_value else "disabled"
        await ctx.send(f"✅ Auto-accept {status} for you!")
    
    # Background task for LCU monitoring
    async def _monitor_lcu_events(self):
        """Monitor LCU events for auto-features"""
        while True:
            try:
                if self.lcu_client.connected and self.lcu_client.websocket:
                    message = await self.lcu_client.websocket.recv()
                    data = json.loads(message)
                    
                    # Handle different event types
                    if len(data) > 2 and data[2] and 'eventType' in data[2]:
                        event_type = data[2]['eventType']
                        event_data = data[2].get('data', {})
                        
                        # Auto-accept queue
                        if event_type == 'Create' and 'lol-matchmaking/v1/ready-check' in data[2].get('uri', ''):
                            await self._handle_ready_check(event_data)
                
                await asyncio.sleep(0.1)  # Small delay to prevent high CPU usage
                
            except Exception as e:
                print(f"LCU monitoring error: {e}")
                await asyncio.sleep(1)
    
    async def _handle_ready_check(self, data: Dict):
        """Handle ready check event for auto-accept"""
        # Check which users have auto-accept enabled
        all_users = await self.config.all_users()
        
        for user_id, user_config in all_users.items():
            if user_config.get('auto_accept', False):
                # Auto-accept for this user
                success = await self.lcu_client.auto_accept_queue()
                if success:
                    user = self.bot.get_user(int(user_id))
                    if user:
                        try:
                            await user.send("✅ Automatically accepted queue for you!")
                        except:
                            pass  # User might have DMs disabled
