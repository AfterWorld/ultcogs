# lol/database.py - Database operations
import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the LoL cog"""
    
    def __init__(self, data_path: Path):
        self.db_path = data_path / "lol_data.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the SQLite database with all required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Monitored summoners table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS monitored_summoners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    puuid TEXT NOT NULL,
                    region TEXT NOT NULL,
                    game_name TEXT NOT NULL,
                    tag_line TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, puuid)
                )
            """)
            
            # User preferences table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INTEGER PRIMARY KEY,
                    favorite_region TEXT,
                    notification_settings TEXT,
                    linked_account TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Match history cache table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS match_cache (
                    match_id TEXT PRIMARY KEY,
                    region TEXT NOT NULL,
                    match_data TEXT NOT NULL,
                    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            
            # Summoner lookup history
            await db.execute("""
                CREATE TABLE IF NOT EXISTS lookup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER,
                    summoner_name TEXT NOT NULL,
                    region TEXT NOT NULL,
                    looked_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # API usage statistics
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    calls_count INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date DATE DEFAULT (date('now'))
                )
            """)
            
            await db.commit()
            logger.info("Database initialized successfully")
    
    async def close(self):
        """Close any open connections"""
        # aiosqlite doesn't maintain persistent connections, so nothing to close
        pass
    
    # Monitored summoners methods
    async def save_monitored_summoner(self, guild_id: int, channel_id: int, puuid: str, 
                                    region: str, game_name: str, tag_line: str):
        """Save a monitored summoner to the database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO monitored_summoners 
                (guild_id, channel_id, puuid, region, game_name, tag_line)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (guild_id, channel_id, puuid, region, game_name, tag_line))
            await db.commit()
    
    async def delete_monitored_summoner(self, guild_id: int, puuid: str):
        """Remove a monitored summoner from the database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM monitored_summoners WHERE guild_id = ? AND puuid = ?",
                (guild_id, puuid)
            )
            await db.commit()
    
    async def get_all_monitored_summoners(self) -> List[Tuple]:
        """Get all monitored summoners from the database"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT guild_id, channel_id, puuid, region, game_name, tag_line 
                FROM monitored_summoners
            """) as cursor:
                return await cursor.fetchall()
    
    async def get_monitored_summoners_for_guild(self, guild_id: int) -> List[Tuple]:
        """Get monitored summoners for a specific guild"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT puuid, region, game_name, tag_line 
                FROM monitored_summoners 
                WHERE guild_id = ?
            """, (guild_id,)) as cursor:
                return await cursor.fetchall()
    
    # Lookup history methods
    async def save_lookup_history(self, user_id: int, guild_id: Optional[int], 
                                summoner_name: str, region: str):
        """Save a summoner lookup to history"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO lookup_history (user_id, guild_id, summoner_name, region)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, summoner_name, region))
            await db.commit()
    
    async def get_user_lookup_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent lookup history for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT summoner_name, region, looked_up_at 
                FROM lookup_history 
                WHERE user_id = ? 
                ORDER BY looked_up_at DESC 
                LIMIT ?
            """, (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "summoner_name": row[0],
                        "region": row[1],
                        "looked_up_at": row[2]
                    }
                    for row in rows
                ]
    
    async def cleanup_old_lookups(self, days: int = 30):
        """Clean up lookup history older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM lookup_history WHERE looked_up_at < ?",
                (cutoff_date.isoformat(),)
            )
            await db.commit()
    
    # Match cache methods
    async def cache_match_data(self, match_id: str, region: str, match_data: Dict, ttl_hours: int = 24):
        """Cache match data to database"""
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO match_cache (match_id, region, match_data, expires_at)
                VALUES (?, ?, ?, ?)
            """, (match_id, region, json.dumps(match_data), expires_at.isoformat()))
            await db.commit()
    
    async def get_cached_match_data(self, match_id: str, region: str) -> Optional[Dict]:
        """Get cached match data if not expired"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT match_data FROM match_cache 
                WHERE match_id = ? AND region = ? AND expires_at > datetime('now')
            """, (match_id, region)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None
    
    async def cleanup_expired_cache(self):
        """Remove expired cache entries"""
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute("DELETE FROM match_cache WHERE expires_at <= datetime('now')")
            await db.commit()
            return result.rowcount
    
    # User preferences methods
    async def save_user_preferences(self, user_id: int, preferences: Dict):
        """Save user preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (user_id, favorite_region, notification_settings, linked_account, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (
                user_id, 
                preferences.get('favorite_region'),
                json.dumps(preferences.get('notification_settings', {})),
                json.dumps(preferences.get('linked_account'))
            ))
            await db.commit()
    
    async def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT favorite_region, notification_settings, linked_account 
                FROM user_preferences 
                WHERE user_id = ?
            """, (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'favorite_region': row[0],
                        'notification_settings': json.loads(row[1] or '{}'),
                        'linked_account': json.loads(row[2] or 'null')
                    }
        return None
    
    async def delete_user_data(self, user_id: int):
        """Delete all user data (GDPR compliance)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            await db.execute("DELETE FROM lookup_history WHERE user_id = ?", (user_id,))
            await db.commit()
    
    # Statistics methods
    async def record_api_call(self, endpoint: str, success: bool = True):
        """Record an API call for statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            if success:
                await db.execute("""
                    INSERT INTO api_statistics (endpoint, calls_count, date)
                    VALUES (?, 1, date('now'))
                    ON CONFLICT(endpoint, date) DO UPDATE SET
                    calls_count = calls_count + 1
                """, (endpoint,))
            else:
                await db.execute("""
                    INSERT INTO api_statistics (endpoint, errors_count, date)
                    VALUES (?, 1, date('now'))
                    ON CONFLICT(endpoint, date) DO UPDATE SET
                    errors_count = errors_count + 1
                """, (endpoint,))
            await db.commit()
    
    async def get_api_statistics(self, days: int = 7) -> List[Dict]:
        """Get API statistics for the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT endpoint, SUM(calls_count) as total_calls, SUM(errors_count) as total_errors, date
                FROM api_statistics 
                WHERE date >= date(?)
                GROUP BY endpoint, date
                ORDER BY date DESC, total_calls DESC
            """, (cutoff_date.date().isoformat(),)) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        'endpoint': row[0],
                        'total_calls': row[1] or 0,
                        'total_errors': row[2] or 0,
                        'date': row[3]
                    }
                    for row in rows
                ]
    
    async def cleanup_old_statistics(self, days: int = 30):
        """Clean up statistics older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            result = await db.execute(
                "DELETE FROM api_statistics WHERE date < date(?)",
                (cutoff_date.date().isoformat(),)
            )
            await db.commit()
            return result.rowcount
    
    # Maintenance methods
    async def vacuum_database(self):
        """Optimize database by running VACUUM"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("VACUUM")
            await db.commit()
    
    async def get_database_stats(self) -> Dict:
        """Get general database statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Table row counts
            tables = ['monitored_summoners', 'lookup_history', 'match_cache', 'user_preferences', 'api_statistics']
            for table in tables:
                async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                    count = await cursor.fetchone()
                    stats[f"{table}_count"] = count[0] if count else 0
            
            # Database file size
            stats['db_size_bytes'] = self.db_path.stat().st_size if self.db_path.exists() else 0
            stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
            
            return stats