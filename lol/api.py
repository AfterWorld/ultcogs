# lol/api.py - API handling and rate limiting
import asyncio
import aiohttp
import time
import json
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import deque, defaultdict
from redbot.core import commands

from .constants import (
    REGION_MAPPING, 
    MATCH_ROUTING, 
    ENDPOINT_RATE_LIMITS,
    DDRAGON_VERSION
)

logger = logging.getLogger(__name__)

class EndpointRateLimiter:
    """Handle rate limiting for specific endpoints"""
    
    def __init__(self, limits: List[Tuple[int, int]]):
        self.limits = limits  # List of (requests, seconds) tuples
        self.request_times = [deque(maxlen=limit[0]) for limit in limits]
        self._lock = asyncio.Lock()
    
    async def wait_for_rate_limit(self):
        """Wait if necessary to respect rate limits for this endpoint"""
        async with self._lock:
            current_time = time.time()
            
            for i, (max_requests, time_window) in enumerate(self.limits):
                request_times = self.request_times[i]
                
                # Remove old requests outside the time window
                while request_times and current_time - request_times[0] >= time_window:
                    request_times.popleft()
                
                # If we're at the limit, wait
                if len(request_times) >= max_requests:
                    oldest_request = request_times[0]
                    wait_time = time_window - (current_time - oldest_request)
                    if wait_time > 0:
                        logger.warning(f"Rate limit hit, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)
                        current_time = time.time()
                
                # Record this request
                request_times.append(current_time)

    def get_status(self) -> Dict[str, str]:
        """Get current rate limit status"""
        current_time = time.time()
        status = {}
        
        for i, (max_requests, time_window) in enumerate(self.limits):
            request_times = self.request_times[i]
            valid_requests = sum(1 for req_time in request_times 
                               if current_time - req_time < time_window)
            status[f"{time_window}s"] = f"{valid_requests}/{max_requests}"
        
        return status

class RiotRateLimiter:
    """Handle Riot API rate limiting with endpoint-specific limits"""
    
    def __init__(self):
        self.endpoint_limiters = {}
        for endpoint, limits in ENDPOINT_RATE_LIMITS.items():
            self.endpoint_limiters[endpoint] = EndpointRateLimiter(limits)
    
    async def wait_for_endpoint(self, endpoint: str):
        """Wait for rate limit clearance for a specific endpoint"""
        if endpoint in self.endpoint_limiters:
            await self.endpoint_limiters[endpoint].wait_for_rate_limit()
    
    def get_endpoint_status(self, endpoint: str) -> Dict[str, str]:
        """Get current status for an endpoint"""
        if endpoint not in self.endpoint_limiters:
            return {}
        return self.endpoint_limiters[endpoint].get_status()

class DataCache:
    """Cache frequently requested data to reduce API calls"""
    def __init__(self, ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                return data
            else:
                # Remove expired data
                del self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, data: Any):
        self.cache[key] = (data, time.time())
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }

class RiotAPIManager:
    """Manages all Riot API interactions"""
    
    def __init__(self, config):
        self.config = config
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        self.rate_limiter = RiotRateLimiter()
        self.cache = DataCache(ttl=300)  # 5 minute cache
        self.champion_cache = DataCache(ttl=3600)  # 1 hour for champion data
        
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "general_cache": self.cache.get_stats(),
            "champion_cache": self.champion_cache.get_stats()
        }
    
    async def get_api_key(self) -> str:
        """Get the Riot API key from config or environment"""
        api_key = await self.config.api_key()
        if not api_key:
            api_key = os.getenv("RIOT_API_KEY")
        if not api_key:
            raise commands.UserFeedbackCheckFailure(
                "No Riot API key set. Please set one using `[p]lolset apikey <key>` "
                "or set the RIOT_API_KEY environment variable."
            )
        return api_key
    
    def set_database_manager(self, db_manager):
        """Set reference to database manager for caching"""
        self.db_manager = db_manager

    def normalize_region(self, region: str) -> str:
        """Normalize region input to proper format"""
        region = region.lower()
        if region in REGION_MAPPING:
            return REGION_MAPPING[region]
        elif region in REGION_MAPPING.values():
            return region
        else:
            valid_regions = ", ".join(REGION_MAPPING.keys())
            raise ValueError(f"Invalid region: {region}. Valid regions: {valid_regions}")

    def get_endpoint_key(self, url: str) -> str:
        """Determine the endpoint key for rate limiting"""
        endpoint_map = {
            "/champion-rotations": "champion-rotations",
            "/summoner/v4/summoners/": "summoner",
            "/league/v4/entries/by-summoner/": "league-entries",
            "/league/v4/challengerleagues/": "league-challenger",
            "/league/v4/masterleagues/": "league-master",
            "/league/v4/grandmasterleagues/": "league-grandmaster",
            "/riot/account/v1/": "account",
            "/match/v5/": "match",
            "/champion-mastery/v4/": "champion-mastery",
            "/status/v4/": "status",
            "/clash/v1/teams/": "clash-teams",
            "/clash/v1/tournaments": "clash-tournaments",
            "/clash/v1/players/": "clash-players"
        }
        
        for path, endpoint in endpoint_map.items():
            if path in url:
                return endpoint
        return "default"

    async def handle_api_error(self, status_code: int, context: str = "API request") -> str:
        """Handle API errors with specific user-friendly messages"""
        error_messages = {
            400: "❌ Bad request. Please check your input.",
            401: "🔑 Unauthorized. API key may be expired.",
            403: "❌ Forbidden. Invalid API key or insufficient permissions.",
            404: "❌ Not found. Check the spelling and region.",
            415: "❌ Unsupported media type.",
            429: "⏳ Rate limit exceeded. Please try again in a moment.",
            500: "🔧 Riot servers are having issues. Try again later.",
            502: "🔧 Riot API gateway error. Try again later.",
            503: "🚧 Riot API is temporarily unavailable.",
            504: "⏰ Request timeout. Riot servers may be slow."
        }
        error_msg = error_messages.get(status_code, f"❌ Error during {context}: HTTP {status_code}")
        logger.error(f"API Error {status_code}: {context}")
        return error_msg

    async def make_request(self, url: str, headers: Dict = None, params: Dict = None) -> Dict:
        """Enhanced API request with caching and error handling"""
        # Check cache first
        cache_key = f"{url}:{json.dumps(params, sort_keys=True) if params else ''}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        # Determine endpoint for rate limiting
        endpoint_key = self.get_endpoint_key(url)
        
        # Wait for rate limit clearance
        await self.rate_limiter.wait_for_endpoint(endpoint_key)
        
        # Get API key
        api_key = await self.get_api_key()
        
        if headers is None:
            headers = {}
        headers["X-Riot-Token"] = api_key
        
        try:
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Cache successful responses
                    self.cache.set(cache_key, data)
                    logger.info(f"API request successful: {endpoint_key}")
                    return data
                else:
                    error_msg = await self.handle_api_error(resp.status, f"{endpoint_key} request")
                    raise commands.UserFeedbackCheckFailure(error_msg)
                    
        except asyncio.TimeoutError:
            raise commands.UserFeedbackCheckFailure("⏰ Request timed out. Please try again.")
        except aiohttp.ClientError as e:
            raise commands.UserFeedbackCheckFailure(f"🌐 Network error: {str(e)}")

    async def get_summoner_by_name(self, region: str, summoner_name: str) -> Dict:
        """Get summoner by name using Account API then Summoner API"""
        # Parse Riot ID
        if "#" not in summoner_name:
            summoner_name += "#NA1"  # Default tag if not provided
        
        game_name, tag_line = summoner_name.split("#", 1)
        
        # Get routing for account API
        routing = MATCH_ROUTING.get(region, "americas")
        
        # Get account by Riot ID
        account_url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_data = await self.make_request(account_url)
        
        # Get summoner by PUUID
        summoner_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{account_data['puuid']}"
        summoner_data = await self.make_request(summoner_url)
        
        # Combine data
        summoner_data.update(account_data)
        return summoner_data

    async def get_rank_info(self, region: str, summoner_id: str) -> List[Dict]:
        """Get ranked information for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        return await self.make_request(url)

    async def get_champion_data(self) -> Dict:
        """Get champion data from Data Dragon (cached)"""
        cached_data = self.champion_cache.get("champion_data")
        if cached_data is not None:
            return cached_data
        
        url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/en_US/champion.json"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.champion_cache.set("champion_data", data)
                    return data
                else:
                    logger.warning(f"Failed to fetch champion data: {resp.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching champion data: {e}")
            return {}

    async def analyze_recent_matches(self, summoner_data: Dict, region: str, count: int = 20) -> Optional[Dict]:
        """Analyze recent matches for a summoner with parallel processing"""
        routing = MATCH_ROUTING.get(region, "americas")
        
        # Get match IDs
        match_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner_data['puuid']}/ids"
        match_ids = await self.make_request(match_url, params={"count": min(count, 20)})
        
        if not match_ids:
            return None
        
        # Process matches in parallel batches to respect rate limits
        matches_data = []
        batch_size = 5
        
        for i in range(0, len(match_ids), batch_size):
            batch_ids = match_ids[i:i+batch_size]
            
            # Create tasks for parallel processing
            tasks = []
            for match_id in batch_ids:
                match_detail_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
                tasks.append(self.make_request(match_detail_url))
            
            # Execute batch and process results
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Failed to fetch match: {result}")
                        continue
                    
                    # Find participant data
                    participant = None
                    for p in result["info"]["participants"]:
                        if p["puuid"] == summoner_data["puuid"]:
                            participant = p
                            break
                    
                    if participant:
                        matches_data.append({
                            "champion": participant["championName"],
                            "kills": participant["kills"],
                            "deaths": participant["deaths"],
                            "assists": participant["assists"],
                            "win": participant["win"],
                            "gameMode": result["info"]["gameMode"],
                            "gameDuration": result["info"]["gameDuration"],
                            "damage": participant.get("totalDamageDealtToChampions", 0),
                            "vision": participant.get("visionScore", 0)
                        })
                        
            except Exception as e:
                logger.error(f"Error processing match batch: {e}")
                continue
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        if not matches_data:
            return None
        
        # Analyze the data
        analysis = self._analyze_match_data(matches_data)
        return analysis

    def _analyze_match_data(self, matches_data: List[Dict]) -> Dict:
        """Analyze match data and return statistics"""
        from statistics import mean
        
        total_games = len(matches_data)
        wins = sum(1 for m in matches_data if m["win"])
        winrate = (wins / total_games) * 100
        
        # KDA statistics
        avg_kills = mean([m["kills"] for m in matches_data])
        avg_deaths = mean([m["deaths"] for m in matches_data])
        avg_assists = mean([m["assists"] for m in matches_data])
        avg_kda = (avg_kills + avg_assists) / max(avg_deaths, 1)
        
        # Champion statistics
        champion_stats = defaultdict(lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0})
        
        for match in matches_data:
            champ = match["champion"]
            champion_stats[champ]["games"] += 1
            champion_stats[champ]["kills"] += match["kills"]
            champion_stats[champ]["deaths"] += match["deaths"]
            champion_stats[champ]["assists"] += match["assists"]
            if match["win"]:
                champion_stats[champ]["wins"] += 1
        
        # Most played champions
        most_played = sorted(champion_stats.items(), key=lambda x: x[1]["games"], reverse=True)[:3]
        
        # Recent trend (last 5 games)
        recent_matches = matches_data[:5]
        recent_wins = sum(1 for m in recent_matches if m["win"])
        
        return {
            "total_games": total_games,
            "wins": wins,
            "losses": total_games - wins,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "avg_kills": avg_kills,
            "avg_deaths": avg_deaths,
            "avg_assists": avg_assists,
            "most_played": most_played,
            "recent_wins": recent_wins,
            "recent_games": min(5, total_games)
        }

    async def get_rate_limit_status(self) -> Dict[str, str]:
        """Get current rate limit status for key endpoints"""
        key_endpoints = ["summoner", "account", "match", "champion-rotations"]
        status = {}
        
        for endpoint in key_endpoints:
            endpoint_status = self.rate_limiter.get_endpoint_status(endpoint)
            if endpoint_status:
                # Get the most restrictive limit
                status_parts = []
                for period, usage in endpoint_status.items():
                    status_parts.append(f"{period}: {usage}")
                status[endpoint] = " | ".join(status_parts)
        
        return status

    async def get_champion_mastery(self, region: str, puuid: str, count: int = 10) -> List[Dict]:
        """Get champion mastery for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top"
        params = {"count": count}
        return await self.make_request(url, params=params)

    async def get_mastery_score(self, region: str, puuid: str) -> int:
        """Get total mastery score for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/scores/by-puuid/{puuid}"
        return await self.make_request(url)

    async def get_champion_rotations(self, region: str) -> Dict:
        """Get current champion rotations"""
        url = f"https://{region}.api.riotgames.com/lol/platform/v3/champion-rotations"
        return await self.make_request(url)

    async def get_live_game(self, region: str, puuid: str) -> Optional[Dict]:
        """Check if a summoner is currently in a live game"""
        url = f"https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        
        try:
            game_data = await self.make_request(url)
            return game_data
        except commands.UserFeedbackCheckFailure as e:
            if "not found" in str(e).lower() or "404" in str(e):
                return None
            raise e

    async def get_recent_matches(self, summoner_data: Dict, region: str, count: int = 5) -> List[Dict]:
        """Get recent matches with detailed information using caching"""
        routing = MATCH_ROUTING.get(region, "americas")
        
        # Get match IDs
        match_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{summoner_data['puuid']}/ids"
        match_ids = await self.make_request(match_url, params={"count": min(count, 20)})
        
        if not match_ids:
            return []
        
        # Get match details with caching
        matches = []
        for match_id in match_ids[:count]:
            try:
                # Check cache first
                match_details = await self._get_cached_match(match_id, region)
                
                if not match_details:
                    # Fetch from API if not cached
                    match_detail_url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
                    match_details = await self.make_request(match_detail_url)
                    # Cache the result
                    await self._cache_match(match_id, region, match_details)
                
                # Find participant data
                participant = None
                for p in match_details["info"]["participants"]:
                    if p["puuid"] == summoner_data["puuid"]:
                        participant = p
                        break
                
                if participant:
                    matches.append({
                        "details": match_details,
                        "participant": participant
                    })
                        
            except Exception as e:
                logger.warning(f"Failed to fetch match {match_id}: {e}")
                continue
        
        return matches

    async def get_champion_data_detailed(self) -> Dict:
        """Get detailed champion data from Data Dragon with caching"""
        cached_data = self.champion_cache.get("champion_detailed")
        
        if cached_data is not None:
            return cached_data
        
        url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/en_US/champion.json"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.champion_cache.set("champion_detailed", data)
                    return data
                else:
                    logger.warning(f"Failed to fetch detailed champion data: {resp.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching detailed champion data: {e}")
            return {}

    async def _get_cached_match(self, match_id: str, region: str) -> Optional[Dict]:
        """Get cached match data from database"""
        try:
            # First check memory cache
            cache_key = f"match:{match_id}:{region}"
            cached_data = self.cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Then check database cache if db_manager is available
            if hasattr(self, 'db_manager') and self.db_manager:
                db_cached = await self.db_manager.get_cached_match_data(match_id, region)
                if db_cached:
                    # Store in memory cache for faster future access
                    self.cache.set(cache_key, db_cached)
                    return db_cached
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached match {match_id}: {e}")
            return None

    async def _cache_match(self, match_id: str, region: str, match_data: Dict):
        """Cache match data to both memory and database"""
        try:
            # Cache in memory
            cache_key = f"match:{match_id}:{region}"
            self.cache.set(cache_key, match_data)
            
            # Cache in database if db_manager is available
            if hasattr(self, 'db_manager') and self.db_manager:
                await self.db_manager.cache_match_data(match_id, region, match_data)
                logger.debug(f"Cached match {match_id} in both memory and database")
            else:
                logger.debug(f"Cached match {match_id} in memory only")
                
        except Exception as e:
            logger.error(f"Error caching match {match_id}: {e}")