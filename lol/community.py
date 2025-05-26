"""
Community Features Manager for Advanced LoL Cog

Handles achievements, leaderboards, user progression, challenges,
and community engagement features.
"""

import sqlite3
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Achievement:
    """Achievement definition"""
    id: str
    name: str
    description: str
    emoji: str
    rarity: str  # "common", "uncommon", "rare", "epic", "legendary", "mythic"
    points: int
    category: str  # "profile", "games", "community", "special"
    requirements: Dict[str, Any]
    hidden: bool = False


@dataclass
class UserProfile:
    """User community profile"""
    discord_id: str
    summoner_name: str
    region: str
    total_points: int
    level: int
    xp: int
    created_at: datetime
    last_active: datetime
    achievements_count: int
    favorite_champion: Optional[str] = None


@dataclass
class Challenge:
    """Community challenge definition"""
    id: str
    guild_id: str
    name: str
    description: str
    challenge_type: str  # "daily", "weekly", "monthly", "seasonal"
    start_date: datetime
    end_date: datetime
    requirements: Dict[str, Any]
    rewards: Dict[str, int]
    participants: List[str]
    active: bool = True


@dataclass
class UserAchievement:
    """User achievement record"""
    user_id: str
    achievement_id: str
    earned_at: datetime
    progress: int = 100


class AchievementManager:
    """Manages achievement definitions and checking logic"""
    
    def __init__(self):
        self.achievements = self._load_achievements()
        self.achievement_checkers = self._setup_achievement_checkers()
    
    def _load_achievements(self) -> List[Achievement]:
        """Load all achievement definitions"""
        achievements = [
            # Profile & Setup Achievements
            Achievement(
                id="first_steps",
                name="First Steps",
                description="Link your first League of Legends profile",
                emoji="🎮",
                rarity="common",
                points=10,
                category="profile",
                requirements={"action": "profile_linked"}
            ),
            Achievement(
                id="region_explorer",
                name="Region Explorer", 
                description="Check profiles from 3 different regions",
                emoji="🌍",
                rarity="uncommon",
                points=30,
                category="profile",
                requirements={"action": "regions_explored", "count": 3}
            ),
            Achievement(
                id="summoner_sleuth",
                name="Summoner Sleuth",
                description="Look up 25 different summoners",
                emoji="🔍",
                rarity="uncommon",
                points=50,
                category="profile",
                requirements={"action": "summoners_checked", "count": 25}
            ),
            
            # Live Game Achievements
            Achievement(
                id="live_game_hunter",
                name="Live Game Hunter",
                description="Check 10 live games",
                emoji="🔴",
                rarity="common",
                points=25,
                category="games",
                requirements={"action": "live_games_checked", "count": 10}
            ),
            Achievement(
                id="spectator_supreme",
                name="Spectator Supreme",
                description="Watch 50 live games",
                emoji="👁️",
                rarity="rare",
                points=100,
                category="games",
                requirements={"action": "live_games_checked", "count": 50}
            ),
            Achievement(
                id="aram_enthusiast",
                name="ARAM Enthusiast",
                description="Find 20 ARAM games",
                emoji="🏰",
                rarity="uncommon",
                points=40,
                category="games",
                requirements={"action": "aram_games_found", "count": 20}
            ),
            
            # Rank & Skill Achievements
            Achievement(
                id="challenger_spotter",
                name="Challenger Spotter",
                description="Find a Challenger-ranked player in live games",
                emoji="💎",
                rarity="rare",
                points=100,
                category="games",
                requirements={"action": "challenger_found"}
            ),
            Achievement(
                id="master_tracker",
                name="Master Tracker",
                description="Find 5 Master+ players",
                emoji="👑",
                rarity="epic",
                points=150,
                category="games",
                requirements={"action": "masters_found", "count": 5}
            ),
            Achievement(
                id="rank_diversity",
                name="Rank Diversity",
                description="Find players from all rank tiers",
                emoji="🏆",
                rarity="legendary",
                points=300,
                category="games",
                requirements={"action": "all_ranks_found"}
            ),
            
            # Match History Achievements
            Achievement(
                id="match_analyst",
                name="Match Analyst",
                description="View 50 match histories",
                emoji="📊",
                rarity="uncommon",
                points=50,
                category="games",
                requirements={"action": "matches_analyzed", "count": 50}
            ),
            Achievement(
                id="pentakill_witness",
                name="Pentakill Witness",
                description="Discover a pentakill in match history",
                emoji="⭐",
                rarity="epic",
                points=200,
                category="games",
                requirements={"action": "pentakill_found"}
            ),
            Achievement(
                id="perfect_game_finder",
                name="Perfect Game Finder",
                description="Find a match with 0 deaths",
                emoji="👼",
                rarity="rare",
                points=75,
                category="games",
                requirements={"action": "perfect_game_found"}
            ),
            
            # Community Achievements
            Achievement(
                id="helpful_member",
                name="Helpful Member",
                description="Help 5 other users with commands",
                emoji="🤝",
                rarity="uncommon",
                points=60,
                category="community",
                requirements={"action": "users_helped", "count": 5}
            ),
            Achievement(
                id="community_leader",
                name="Community Leader",
                description="Help 25 other users and be active for 30 days",
                emoji="👑",
                rarity="mythic",
                points=1000,
                category="community",
                requirements={"action": "leadership_milestone"}
            ),
            Achievement(
                id="knowledge_sharer",
                name="Knowledge Sharer",
                description="Share bot features with others 10 times",
                emoji="📚",
                rarity="rare",
                points=80,
                category="community",
                requirements={"action": "features_shared", "count": 10}
            ),
            
            # Special & Time-based Achievements
            Achievement(
                id="early_adopter",
                name="Early Adopter",
                description="One of the first 100 users of the bot",
                emoji="⚡",
                rarity="legendary",
                points=500,
                category="special",
                requirements={"action": "early_adoption"},
                hidden=True
            ),
            Achievement(
                id="dedication",
                name="Dedicated Fan",
                description="Use the bot for 30 consecutive days",
                emoji="💪",
                rarity="legendary",
                points=500,
                category="special",
                requirements={"action": "consecutive_days", "count": 30}
            ),
            Achievement(
                id="night_owl",
                name="Night Owl",
                description="Use the bot after midnight 10 times",
                emoji="🦉",
                rarity="uncommon",
                points=35,
                category="special",
                requirements={"action": "night_usage", "count": 10}
            ),
            Achievement(
                id="weekend_warrior",
                name="Weekend Warrior",
                description="Very active on weekends",
                emoji="⚔️",
                rarity="rare",
                points=65,
                category="special",
                requirements={"action": "weekend_activity"}
            ),
            
            # Meta & Advanced Achievements
            Achievement(
                id="meta_observer",
                name="Meta Observer",
                description="Track win rates across 100 different champions",
                emoji="🎯",
                rarity="epic",
                points=250,
                category="games",
                requirements={"action": "champions_tracked", "count": 100}
            ),
            Achievement(
                id="trend_setter",
                name="Trend Setter",
                description="Find an uncommon pick before it becomes popular",
                emoji="🚀",
                rarity="mythic",
                points=750,
                category="special",
                requirements={"action": "trend_prediction"},
                hidden=True
            ),
            Achievement(
                id="data_enthusiast",
                name="Data Enthusiast",
                description="Use advanced analytics features 100 times",
                emoji="📈",
                rarity="epic",
                points=200,
                category="games",
                requirements={"action": "analytics_used", "count": 100}
            ),
        ]
        
        return achievements
    
    def _setup_achievement_checkers(self) -> Dict[str, callable]:
        """Setup functions to check achievement progress"""
        return {
            "profile_linked": self._check_profile_linked,
            "live_games_checked": self._check_count_achievement,
            "matches_analyzed": self._check_count_achievement,
            "challenger_found": self._check_instant_achievement,
            "pentakill_found": self._check_instant_achievement,
            "summoners_checked": self._check_count_achievement,
            "regions_explored": self._check_regions_explored,
            "consecutive_days": self._check_consecutive_days,
            "users_helped": self._check_count_achievement,
            "masters_found": self._check_count_achievement,
            "all_ranks_found": self._check_all_ranks_found,
            "perfect_game_found": self._check_instant_achievement,
            "aram_games_found": self._check_count_achievement,
            "features_shared": self._check_count_achievement,
            "night_usage": self._check_count_achievement,
            "weekend_activity": self._check_weekend_activity,
            "champions_tracked": self._check_count_achievement,
            "analytics_used": self._check_count_achievement,
        }
    
    def get_achievement_by_id(self, achievement_id: str) -> Optional[Achievement]:
        """Get achievement by ID"""
        return next((a for a in self.achievements if a.id == achievement_id), None)
    
    def get_achievements_by_category(self, category: str) -> List[Achievement]:
        """Get achievements by category"""
        return [a for a in self.achievements if a.category == category]
    
    def get_achievements_by_rarity(self, rarity: str) -> List[Achievement]:
        """Get achievements by rarity"""
        return [a for a in self.achievements if a.rarity == rarity]
    
    def _check_profile_linked(self, user_stats: Dict, requirement: Any) -> bool:
        """Check if user has linked a profile"""
        return user_stats.get('profiles_linked', 0) >= 1
    
    def _check_count_achievement(self, user_stats: Dict, requirement: int) -> bool:
        """Check count-based achievements"""
        action = requirement.get('action')
        required_count = requirement.get('count', 1)
        return user_stats.get(action, 0) >= required_count
    
    def _check_instant_achievement(self, user_stats: Dict, requirement: Any) -> bool:
        """Check instant achievements (triggered by specific events)"""
        # These are handled by direct triggers in the main logic
        return False
    
    def _check_regions_explored(self, user_stats: Dict, requirement: Dict) -> bool:
        """Check if user has explored different regions"""
        regions_used = user_stats.get('regions_used', set())
        if isinstance(regions_used, str):
            try:
                regions_used = json.loads(regions_used)
            except:
                regions_used = set()
        return len(regions_used) >= requirement.get('count', 3)
    
    def _check_consecutive_days(self, user_stats: Dict, requirement: Dict) -> bool:
        """Check consecutive days usage"""
        return user_stats.get('consecutive_days', 0) >= requirement.get('count', 30)
    
    def _check_all_ranks_found(self, user_stats: Dict, requirement: Dict) -> bool:
        """Check if all rank tiers have been found"""
        ranks_found = user_stats.get('ranks_found', set())
        if isinstance(ranks_found, str):
            try:
                ranks_found = json.loads(ranks_found)
            except:
                ranks_found = set()
        
        all_ranks = {'IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 
                    'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'}
        return len(ranks_found.intersection(all_ranks)) >= len(all_ranks)
    
    def _check_weekend_activity(self, user_stats: Dict, requirement: Dict) -> bool:
        """Check weekend activity pattern"""
        weekend_commands = user_stats.get('weekend_commands', 0)
        total_commands = user_stats.get('total_commands', 1)
        weekend_ratio = weekend_commands / total_commands
        return weekend_ratio >= 0.3 and weekend_commands >= 20


class CommunityManager:
    """Main community features manager"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.achievement_manager = AchievementManager()
        self.active_challenges = {}
        self._init_database()
    
    def _init_database(self):
        """Initialize community database with all necessary tables"""
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
                xp INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                achievements_count INTEGER DEFAULT 0,
                favorite_champion TEXT
            )
        ''')
        
        # User achievements table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT,
                achievement_id TEXT,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 100,
                FOREIGN KEY (discord_id) REFERENCES user_profiles (discord_id),
                UNIQUE(discord_id, achievement_id)
            )
        ''')
        
        # User statistics tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                discord_id TEXT,
                stat_name TEXT,
                stat_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (discord_id, stat_name),
                FOREIGN KEY (discord_id) REFERENCES user_profiles (discord_id)
            )
        ''')
        
        # Server leaderboards and statistics
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
                id TEXT PRIMARY KEY,
                guild_id TEXT,
                name TEXT,
                description TEXT,
                challenge_type TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                requirements TEXT,
                rewards TEXT,
                participants TEXT,
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Challenge participation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS challenge_progress (
                challenge_id TEXT,
                discord_id TEXT,
                progress INTEGER DEFAULT 0,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                PRIMARY KEY (challenge_id, discord_id),
                FOREIGN KEY (challenge_id) REFERENCES challenges (id)
            )
        ''')
        
        # Daily activity tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_activity (
                discord_id TEXT,
                date DATE,
                commands_used INTEGER DEFAULT 0,
                PRIMARY KEY (discord_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Community database initialized successfully")
    
    async def get_user_profile(self, discord_id: str) -> Optional[UserProfile]:
        """Get user community profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM user_profiles WHERE discord_id = ?",
            (discord_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return UserProfile(
                discord_id=result[0],
                summoner_name=result[1] or "",
                region=result[2] or "",
                total_points=result[3],
                level=result[4],
                xp=result[5],
                created_at=datetime.fromisoformat(result[6]) if result[6] else datetime.now(),
                last_active=datetime.fromisoformat(result[7]) if result[7] else datetime.now(),
                achievements_count=result[8],
                favorite_champion=result[9]
            )
        
        return None
    
    async def create_user_profile(self, discord_id: str, summoner_name: str = "", region: str = "") -> UserProfile:
        """Create new user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO user_profiles 
            (discord_id, summoner_name, region, total_points, level, xp, created_at, last_active, achievements_count)
            VALUES (?, ?, ?, 0, 1, 0, ?, ?, 0)
        ''', (discord_id, summoner_name, region, now, now))
        
        conn.commit()
        conn.close()
        
        return await self.get_user_profile(discord_id)
    
    async def update_user_activity(self, discord_id: str):
        """Update user's last activity timestamp"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        cursor.execute(
            "UPDATE user_profiles SET last_active = ? WHERE discord_id = ?",
            (now.isoformat(), discord_id)
        )
        
        # Track daily activity
        today = now.date()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_activity (discord_id, date, commands_used)
            VALUES (?, ?, COALESCE((SELECT commands_used FROM daily_activity WHERE discord_id = ? AND date = ?), 0) + 1)
        ''', (discord_id, today, discord_id, today))
        
        conn.commit()
        conn.close()
    
    async def update_user_stat(self, discord_id: str, stat_name: str, value: Any):
        """Update user statistic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Ensure user profile exists
        await self.get_or_create_user_profile(discord_id)
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_stats (discord_id, stat_name, stat_value, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (discord_id, stat_name, str(value), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    async def increment_user_stat(self, discord_id: str, stat_name: str, increment: int = 1):
        """Increment a user statistic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current value
        cursor.execute(
            "SELECT stat_value FROM user_stats WHERE discord_id = ? AND stat_name = ?",
            (discord_id, stat_name)
        )
        result = cursor.fetchone()
        current_value = int(result[0]) if result else 0
        
        # Update with incremented value
        new_value = current_value + increment
        await self.update_user_stat(discord_id, stat_name, new_value)
        
        conn.close()
        return new_value
    
    async def get_user_stats(self, discord_id: str) -> Dict[str, Any]:
        """Get all user statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT stat_name, stat_value FROM user_stats WHERE discord_id = ?",
            (discord_id,)
        )
        results = cursor.fetchall()
        conn.close()
        
        stats = {}
        for stat_name, stat_value in results:
            try:
                # Try to convert to appropriate type
                if stat_value.isdigit():
                    stats[stat_name] = int(stat_value)
                elif stat_value.replace('.', '').isdigit():
                    stats[stat_name] = float(stat_value)
                elif stat_value.startswith('{') or stat_value.startswith('['):
                    stats[stat_name] = json.loads(stat_value)
                else:
                    stats[stat_name] = stat_value
            except:
                stats[stat_name] = stat_value
        
        return stats
    
    async def get_or_create_user_profile(self, discord_id: str) -> UserProfile:
        """Get existing user profile or create new one"""
        profile = await self.get_user_profile(discord_id)
        if not profile:
            profile = await self.create_user_profile(discord_id)
        return profile
    
    async def check_achievements(self, discord_id: str, action: str, data: Dict = None) -> List[Achievement]:
        """Check and award achievements for user actions"""
        earned_achievements = []
        
        # Ensure user profile exists
        await self.get_or_create_user_profile(discord_id)
        await self.update_user_activity(discord_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user's current achievements
        cursor.execute(
            "SELECT achievement_id FROM user_achievements WHERE discord_id = ?",
            (discord_id,)
        )
        current_achievements = {row[0] for row in cursor.fetchall()}
        
        # Get user statistics for checking
        user_stats = await self.get_user_stats(discord_id)
        
        # Update the specific action stat
        if action:
            new_count = await self.increment_user_stat(discord_id, action, 1)
            user_stats[action] = new_count
        
        # Check each achievement
        for achievement in self.achievement_manager.achievements:
            if achievement.id in current_achievements:
                continue
            
            should_award = False
            
            # Handle different achievement types
            req_action = achievement.requirements.get('action')
            if req_action == action:
                # Check if this action triggers the achievement
                if 'count' in achievement.requirements:
                    should_award = user_stats.get(action, 0) >= achievement.requirements['count']
                else:
                    should_award = True
            elif req_action in self.achievement_manager.achievement_checkers:
                # Use custom checker
                checker = self.achievement_manager.achievement_checkers[req_action]
                should_award = checker(user_stats, achievement.requirements)
            
            # Special handling for specific achievements
            if achievement.id == "challenger_found" and action == "challenger_found":
                should_award = True
            elif achievement.id == "pentakill_found" and action == "pentakill_found":
                should_award = True
            elif achievement.id == "perfect_game_found" and action == "perfect_game_found":
                should_award = True
            
            if should_award:
                # Award the achievement
                cursor.execute('''
                    INSERT INTO user_achievements (discord_id, achievement_id, earned_at)
                    VALUES (?, ?, ?)
                ''', (discord_id, achievement.id, datetime.now().isoformat()))
                
                # Update user points and achievement count
                cursor.execute('''
                    UPDATE user_profiles 
                    SET total_points = total_points + ?, achievements_count = achievements_count + 1
                    WHERE discord_id = ?
                ''', (achievement.points, discord_id))
                
                # Check for level up
                await self._check_level_up(discord_id, cursor)
                
                earned_achievements.append(achievement)
                logger.info(f"User {discord_id} earned achievement: {achievement.name}")
        
        conn.commit()
        conn.close()
        
        return earned_achievements
    
    async def _check_level_up(self, discord_id: str, cursor):
        """Check if user should level up based on points"""
        cursor.execute(
            "SELECT total_points, level FROM user_profiles WHERE discord_id = ?",
            (discord_id,)
        )
        result = cursor.fetchone()
        if not result:
            return
        
        total_points, current_level = result
        
        # Calculate required XP for next level (exponential curve)
        required_xp = self._calculate_required_xp(current_level)
        
        if total_points >= required_xp:
            new_level = current_level + 1
            cursor.execute(
                "UPDATE user_profiles SET level = ? WHERE discord_id = ?",
                (new_level, discord_id)
            )
            logger.info(f"User {discord_id} leveled up to level {new_level}")
    
    def _calculate_required_xp(self, level: int) -> int:
        """Calculate XP required for a given level"""
        # Exponential curve: level 1=0, level 2=100, level 3=250, etc.
        return int(50 * (level ** 1.5))
    
    async def get_user_achievements(self, discord_id: str) -> List[Tuple[Achievement, datetime]]:
        """Get user's earned achievements with timestamps"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT achievement_id, earned_at FROM user_achievements 
            WHERE discord_id = ? ORDER BY earned_at DESC
        ''', (discord_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        achievements = []
        for achievement_id, earned_at in results:
            achievement = self.achievement_manager.get_achievement_by_id(achievement_id)
            if achievement:
                earned_datetime = datetime.fromisoformat(earned_at)
                achievements.append((achievement, earned_datetime))
        
        return achievements
    
    async def get_server_leaderboard(self, guild_id: str, stat_type: str, limit: int = 10) -> List[Tuple]:
        """Get server leaderboard for specific stat"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if stat_type == "total_points":
            # Special handling for total points
            cursor.execute('''
                SELECT up.discord_id, up.summoner_name, up.total_points, up.level, up.achievements_count
                FROM user_profiles up
                WHERE up.discord_id IN (
                    SELECT DISTINCT discord_id FROM server_stats WHERE guild_id = ?
                )
                ORDER BY up.total_points DESC, up.level DESC
                LIMIT ?
            ''', (guild_id, limit))
        else:
            # Regular server stats
            cursor.execute('''
                SELECT ss.discord_id, up.summoner_name, ss.stat_value, up.total_points, up.level
                FROM server_stats ss
                JOIN user_profiles up ON ss.discord_id = up.discord_id
                WHERE ss.guild_id = ? AND ss.stat_type = ?
                ORDER BY ss.stat_value DESC
                LIMIT ?
            ''', (guild_id, stat_type, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    async def update_server_stat(self, guild_id: str, discord_id: str, stat_type: str, value: float):
        """Update server-specific user statistic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO server_stats (guild_id, discord_id, stat_type, stat_value, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (guild_id, discord_id, stat_type, value, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    async def increment_server_stat(self, guild_id: str, discord_id: str, stat_type: str, increment: float = 1.0):
        """Increment server-specific statistic"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current value
        cursor.execute(
            "SELECT stat_value FROM server_stats WHERE guild_id = ? AND discord_id = ? AND stat_type = ?",
            (guild_id, discord_id, stat_type)
        )
        result = cursor.fetchone()
        current_value = result[0] if result else 0.0
        
        # Update with incremented value
        new_value = current_value + increment
        await self.update_server_stat(guild_id, discord_id, stat_type, new_value)
        
        conn.close()
        return new_value
    
    async def get_achievement_progress(self, discord_id: str) -> Dict[str, Dict]:
        """Get achievement progress for user"""
        user_stats = await self.get_user_stats(discord_id)
        current_achievements = {a.id for a, _ in await self.get_user_achievements(discord_id)}
        
        progress = {}
        
        for achievement in self.achievement_manager.achievements:
            if achievement.id in current_achievements:
                progress[achievement.id] = {
                    "completed": True,
                    "progress": 100,
                    "requirement": achievement.requirements.get('count', 1)
                }
            else:
                req_action = achievement.requirements.get('action')
                req_count = achievement.requirements.get('count', 1)
                current_count = user_stats.get(req_action, 0)
                
                progress[achievement.id] = {
                    "completed": False,
                    "progress": min(100, (current_count / req_count) * 100) if req_count > 0 else 0,
                    "current": current_count,
                    "requirement": req_count
                }
        
        return progress
    
    def get_rarity_color(self, rarity: str) -> int:
        """Get Discord color for achievement rarity"""
        colors = {
            "common": 0x95a5a6,     # Gray
            "uncommon": 0x2ecc71,   # Green
            "rare": 0x3498db,       # Blue
            "epic": 0x9b59b6,       # Purple
            "legendary": 0xf39c12,  # Orange
            "mythic": 0xe74c3c      # Red
        }
        return colors.get(rarity, 0x95a5a6)
    
    def get_rarity_emoji(self, rarity: str) -> str:
        """Get emoji for achievement rarity"""
        emojis = {
            "common": "⚪",
            "uncommon": "🟢", 
            "rare": "🔵",
            "epic": "🟣",
            "legendary": "🟠",
            "mythic": "🔴"
        }
        return emojis.get(rarity, "⚪")
