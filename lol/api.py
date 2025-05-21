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
                            "championId": participant.get("championId", 0),  # Get the champion ID
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
        
        # Champion statistics - include champion IDs 
        champion_stats = defaultdict(lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0, "championId": 0})
        
        for match in matches_data:
            champ = match["champion"]
            champion_id = match.get("championId", 0)
            champion_stats[champ]["games"] += 1
            champion_stats[champ]["kills"] += match["kills"]
            champion_stats[champ]["deaths"] += match["deaths"]
            champion_stats[champ]["assists"] += match["assists"]
            champion_stats[champ]["championId"] = champion_id  # Store champion ID
            if match["win"]:
                champion_stats[champ]["wins"] += 1
        
        # Most played champions with champion IDs
        most_played = sorted(champion_stats.items(), key=lambda x: x[1]["games"], reverse=True)[:3]
        most_played_with_ids = []
        for champ_name, stats in most_played:
            most_played_with_ids.append([champ_name, stats, stats["championId"]])
        
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
            "most_played": most_played_with_ids,
            "recent_wins": recent_wins,
            "recent_games": min(5, total_games)
        }

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
                    # Make sure championId is included 
                    if "championId" not in participant and "championName" in participant:
                        # Try to derive champion ID from champion data
                        champion_data = await self.get_champion_data()
                        for champ_key, champ_info in champion_data.get("data", {}).items():
                            if champ_info["name"] == participant["championName"]:
                                participant["championId"] = int(champ_info["key"])
                                break
                    
                    matches.append({
                        "details": match_details,
                        "participant": participant
                    })
                        
            except Exception as e:
                logger.warning(f"Failed to fetch match {match_id}: {e}")
                continue
        
        return matches

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
            
    async def get_champion_build_data(self, champion_id: str) -> Optional[Dict]:
        """Get champion build data including items and recommendations"""
        # Check cache first
        cache_key = f"build_data:{champion_id}"
        cached_data = self.champion_cache.get(cache_key)
        
        if cached_data is not None:
            return cached_data
        
        try:
            # Get item data
            items_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/en_US/item.json"
            async with self.session.get(items_url) as resp:
                if resp.status == 200:
                    items_data = await resp.json()
                else:
                    logger.warning(f"Failed to fetch items data: {resp.status}")
                    return None
            
            # Get champion-specific recommended items from basic champion data
            champion_url = f"http://ddragon.leagueoflegends.com/cdn/{DDRAGON_VERSION}/data/en_US/champion/{champion_id}.json"
            async with self.session.get(champion_url) as resp:
                if resp.status == 200:
                    champion_details = await resp.json()
                    champion_info = champion_details["data"][champion_id]
                else:
                    # Fallback to basic champion data if detailed data fails
                    logger.warning(f"Failed to fetch champion details: {resp.status}")
                    all_champions = await self.get_champion_data()
                    champion_info = None
                    for champ_data in all_champions.get("data", {}).values():
                        if champ_data["id"] == champion_id:
                            champion_info = champ_data
                            break
                    
                    if not champion_info:
                        return None
            
            # Process build data
            build_data = {
                "items": items_data["data"],
                "champion_recommended": champion_info.get("recommended", []),
                "popular_builds": self._get_popular_builds(champion_id, champion_info.get("tags", [])),
                "starting_items": self._get_starting_items_by_role(champion_info.get("tags", [])),
                "core_items": self._get_core_items_by_role(champion_info.get("tags", [])),
                "boots": self._get_boots_options(),
                "situational": self._get_situational_items_by_role(champion_info.get("tags", []))
            }
            
            # Cache the result for 1 hour
            self.champion_cache.set(cache_key, build_data)
            return build_data
            
        except Exception as e:
            logger.error(f"Error fetching build data for {champion_id}: {e}")
            return None
    
    def _get_popular_builds(self, champion_id: str, tags: List[str]) -> List[Dict]:
        """Get popular builds based on champion role"""
        # Build recommendations based on primary role
        primary_role = tags[0] if tags else "Fighter"
        
        role_builds = {
            "Marksman": [
                {
                    "name": "ADC Core Build", 
                    "description": "Standard crit build for most games",
                    "items": ["1001", "1055", "3031", "3006", "3094", "3033", "3036", "3139"]
                },
                {
                    "name": "On-Hit Build",
                    "description": "Attack speed focused build",
                    "items": ["1001", "1055", "3085", "3006", "3153", "3124", "3091", "3139"]
                }
            ],
            "Mage": [
                {
                    "name": "Burst Build",
                    "description": "High damage burst focused",
                    "items": ["1056", "3020", "3157", "3135", "3116", "3089", "3102"]
                },
                {
                    "name": "Sustain Build", 
                    "description": "Sustained damage with survivability",
                    "items": ["1056", "3020", "4645", "3135", "3157", "3151", "3102"]
                }
            ],
            "Tank": [
                {
                    "name": "Tank Build",
                    "description": "Maximum survivability",
                    "items": ["1054", "3047", "3068", "3065", "3143", "3076", "3110"]
                },
                {
                    "name": "Engage Build",
                    "description": "Initiation focused with utility",
                    "items": ["1054", "3020", "3190", "3068", "3109", "3107", "3110"]
                }
            ],
            "Fighter": [
                {
                    "name": "Bruiser Build",
                    "description": "Balanced damage and survivability", 
                    "items": ["1055", "3047", "3071", "3053", "3026", "3072", "3156"]
                },
                {
                    "name": "Split Push Build",
                    "description": "Dueling and split pushing focused",
                    "items": ["1055", "3047", "3078", "3748", "3053", "3156", "3026"]
                }
            ],
            "Assassin": [
                {
                    "name": "Lethality Build",
                    "description": "High burst damage",
                    "items": ["1055", "3020", "3142", "3147", "3814", "3156", "3026"]
                },
                {
                    "name": "Crit Assassin",
                    "description": "Critical strike based", 
                    "items": ["1055", "3006", "3031", "3094", "3033", "3156", "3139"]
                }
            ],
            "Support": [
                {
                    "name": "Enchanter Build",
                    "description": "Shield and heal focused",
                    "items": ["3850", "3111", "3107", "3222", "3504", "3152"]
                },
                {
                    "name": "Tank Support",
                    "description": "Engage and protection",
                    "items": ["3851", "3047", "3190", "3109", "3143", "3110"]
                }
            ]
        }
        
        return role_builds.get(primary_role, role_builds["Fighter"])
    
    def _get_starting_items_by_role(self, tags: List[str]) -> List[Dict]:
        """Get starting items based on champion role"""
        primary_role = tags[0] if tags else "Fighter"
        
        role_starts = {
            "Marksman": [
                {"id": "1055", "name": "Doran's Blade"},
                {"id": "2003", "name": "Health Potion"},
                {"id": "3340", "name": "Stealth Ward"}
            ],
            "Mage": [
                {"id": "1056", "name": "Doran's Ring"}, 
                {"id": "2003", "name": "Health Potion"},
                {"id": "3340", "name": "Stealth Ward"}
            ],
            "Tank": [
                {"id": "1054", "name": "Doran's Shield"},
                {"id": "2003", "name": "Health Potion"}, 
                {"id": "3340", "name": "Stealth Ward"}
            ],
            "Support": [
                {"id": "3850", "name": "Relic Shield"},
                {"id": "3854", "name": "Steel Shoulderguards"},
                {"id": "2003", "name": "Health Potion"},
                {"id": "3340", "name": "Stealth Ward"}
            ]
        }
        
        return role_starts.get(primary_role, role_starts.get("Fighter", [
            {"id": "1055", "name": "Doran's Blade"},
            {"id": "2003", "name": "Health Potion"},
            {"id": "3340", "name": "Stealth Ward"}
        ]))
    
    def _get_core_items_by_role(self, tags: List[str]) -> List[Dict]:
        """Get core items based on champion role"""
        primary_role = tags[0] if tags else "Fighter"
        
        role_items = {
            "Marksman": [
                {"id": "3031", "name": "Infinity Edge"},
                {"id": "3094", "name": "Rapid Firecannon"},
                {"id": "3033", "name": "Mortal Reminder"},
                {"id": "3036", "name": "Lord Dominik's Regards"}
            ],
            "Mage": [
                {"id": "3157", "name": "Zhonya's Hourglass"},
                {"id": "3135", "name": "Void Staff"},
                {"id": "3116", "name": "Rylai's Crystal Scepter"},
                {"id": "3089", "name": "Rabadon's Deathcap"}
            ],
            "Tank": [
                {"id": "3068", "name": "Sunfire Aegis"},
                {"id": "3065", "name": "Spirit Visage"},
                {"id": "3143", "name": "Randuin's Omen"},
                {"id": "3076", "name": "Bramble Vest"}
            ],
            "Fighter": [
                {"id": "3071", "name": "Black Cleaver"},
                {"id": "3053", "name": "Sterak's Gage"}, 
                {"id": "3078", "name": "Trinity Force"},
                {"id": "3026", "name": "Guardian Angel"}
            ],
            "Assassin": [
                {"id": "3142", "name": "Youmuu's Ghostblade"},
                {"id": "3814", "name": "Edge of Night"},
                {"id": "3147", "name": "Duskblade of Draktharr"},
                {"id": "3156", "name": "Maw of Malmortius"}
            ],
            "Support": [
                {"id": "3107", "name": "Redemption"},
                {"id": "3109", "name": "Knight's Vow"}, 
                {"id": "3190", "name": "Locket of the Iron Solari"},
                {"id": "3222", "name": "Mikael's Blessing"}
            ]
        }
        
        return role_items.get(primary_role, role_items["Fighter"])
    
    def _get_boots_options(self) -> List[Dict]:
        """Get boots options"""
        return [
            {"id": "3006", "name": "Berserker's Greaves"},
            {"id": "3020", "name": "Sorcerer's Shoes"},
            {"id": "3047", "name": "Plated Steelcaps"},
            {"id": "3111", "name": "Mercury's Treads"},
            {"id": "3117", "name": "Mobility Boots"},
            {"id": "3009", "name": "Boots of Swiftness"}
        ]
    
    def _get_situational_items_by_role(self, tags: List[str]) -> List[Dict]:
        """Get situational items based on role"""
        primary_role = tags[0] if tags else "Fighter"
        
        role_situational = {
            "Marksman": [
                {"id": "3139", "name": "Mercurial Scimitar"},
                {"id": "3026", "name": "Guardian Angel"},
                {"id": "3156", "name": "Maw of Malmortius"},
                {"id": "3072", "name": "Bloodthirster"}
            ],
            "Mage": [
                {"id": "3102", "name": "Banshee's Veil"},
                {"id": "3151", "name": "Liandry's Anguish"},  
                {"id": "4645", "name": "Shadowflame"},
                {"id": "3152", "name": "Hextech Rocketbelt"}
            ],
            "Tank": [
                {"id": "3110", "name": "Frozen Heart"},
                {"id": "3193", "name": "Gargoyle Stoneplate"},
                {"id": "3742", "name": "Dead Man's Plate"},
                {"id": "3075", "name": "Thornmail"}
            ],
            "Support": [
                {"id": "3504", "name": "Ardent Censer"},
                {"id": "3152", "name": "Hextech Rocketbelt"},
                {"id": "3110", "name": "Frozen Heart"},
                {"id": "3143", "name": "Randuin's Omen"}
            ]
        }
        
        # Default to Fighter situational items if role not found
        return role_situational.get(primary_role, [
            {"id": "3156", "name": "Maw of Malmortius"},
            {"id": "3026", "name": "Guardian Angel"},
            {"id": "3139", "name": "Mercurial Scimitar"},
            {"id": "3053", "name": "Sterak's Gage"}
        ])
