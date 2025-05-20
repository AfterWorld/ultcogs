import asyncio
import aiohttp
import discord
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Deque, Tuple
from collections import deque, defaultdict, Counter
from redbot.core import commands, Config, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.predicates import MessagePredicate

_ = Translator("LoL", __file__)

# Mapping of regions to their routing values
REGION_MAPPING = {
    "na": "na1",
    "euw": "euw1", 
    "eune": "eun1",
    "kr": "kr",
    "br": "br1",
    "jp": "jp1",
    "ru": "ru",
    "oc": "oc1",
    "tr": "tr1",
    "lan": "la1",
    "las": "la2",
    "me": "me1",
    "sg": "sg2",
    "tw": "tw2",
    "vn": "vn2"
}

# Regional routing for match API
MATCH_ROUTING = {
    "na1": "americas",
    "br1": "americas", 
    "la1": "americas",
    "la2": "americas",
    "kr": "asia",
    "jp1": "asia",
    "euw1": "europe",
    "eun1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "me1": "europe",
    "oc1": "sea",
    "sg2": "sea",
    "tw2": "sea",
    "vn2": "sea"
}

# Endpoint-specific rate limits
ENDPOINT_RATE_LIMITS = {
    # Champion rotation
    "champion-rotations": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    
    # Summoner endpoints
    "summoner": [(1600, 60)],  # 1600/1m
    
    # League endpoints
    "league-entries": [(100, 60)],  # 100/1m
    "league-challenger": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    "league-master": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    "league-grandmaster": [(30, 10), (500, 600)],  # 30/10s, 500/10m
    
    # Account endpoints
    "account": [(1000, 60), (20000, 10), (1200000, 600)],  # 1000/1m, 20000/10s, 1200000/10m
    
    # Match endpoints
    "match": [(2000, 10)],  # 2000/10s
    
    # Champion mastery
    "champion-mastery": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
    
    # Status
    "status": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
    
    # Clash
    "clash-teams": [(200, 60)],  # 200/1m
    "clash-tournaments": [(10, 60)],  # 10/1m
    "clash-players": [(20000, 10), (1200000, 600)],  # 20000/10s, 1200000/10m
}

class DataCache:
    """Cache frequently requested data to reduce API calls"""
    def __init__(self, ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Tuple[any, float]] = {}
        self.ttl = ttl
    
    def get(self, key: str):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
        return None
    
    def set(self, key: str, data: any):
        self.cache[key] = (data, time.time())
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
    
    def size(self):
        """Get cache size"""
        return len(self.cache)

class CogStatistics:
    """Track cog usage statistics"""
    def __init__(self):
        self.api_calls = defaultdict(int)
        self.commands_used = defaultdict(int)
        self.errors = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()
    
    def record_api_call(self, endpoint: str):
        self.api_calls[endpoint] += 1
    
    def record_command(self, command: str):
        self.commands_used[command] += 1
    
    def record_error(self, error_type: str):
        self.errors[error_type] += 1
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1

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
                        await asyncio.sleep(wait_time)
                        current_time = time.time()
                
                # Record this request
                request_times.append(current_time)

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
    
    def get_endpoint_status(self, endpoint: str) -> Dict:
        """Get current status for an endpoint"""
        if endpoint not in self.endpoint_limiters:
            return {}
        
        limiter = self.endpoint_limiters[endpoint]
        current_time = time.time()
        status = {}
        
        for i, (max_requests, time_window) in enumerate(limiter.limits):
            request_times = limiter.request_times[i]
            # Count requests still within the time window
            valid_requests = sum(1 for req_time in request_times 
                               if current_time - req_time < time_window)
            status[f"{time_window}s"] = f"{valid_requests}/{max_requests}"
        
        return status

@cog_i18n(_)
class LeagueOfLegends(commands.Cog):
    """League of Legends integration with Riot Games API"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
        
        # Default settings
        default_guild = {
            "default_region": "na1"
        }
        
        default_global = {
            "api_key": None
        }
        
        default_user = {
            "linked_account": None,
            "preferred_region": None
        }
        
        self.session = aiohttp.ClientSession()
        self.rate_limiter = RiotRateLimiter()
        self.cache = DataCache(ttl=300)  # 5 minute cache
        self.champion_cache = DataCache(ttl=3600)  # 1 hour for champion data
        self.stats = CogStatistics()
        
    def cog_unload(self):
        if self.session:
            asyncio.create_task(self.session.close())
            
    async def _handle_api_error(self, error_code: int, context: str = "API request") -> str:
        """Handle API errors with specific user-friendly messages"""
        error_messages = {
            403: "❌ Invalid API key. Please contact the bot owner.",
            404: "❌ Summoner not found. Check the spelling and region.",
            429: "⏳ Rate limit hit. Please try again in a moment.",
            500: "🔧 Riot servers are having issues. Try again later.",
            503: "🚧 Riot API is temporarily unavailable.",
            400: "❌ Bad request. Please check your input.",
            401: "🔑 Unauthorized. API key may be expired.",
            415: "❌ Unsupported media type.",
        }
        self.stats.record_error(str(error_code))
        return error_messages.get(error_code, f"❌ Error during {context}: HTTP {error_code}")

    async def red_delete_data_for_user(self, **kwargs):
        """Delete user data for GDPR compliance"""
        requester = kwargs.get("requester")
        user_id = kwargs.get("user_id")
        
        if requester == "discord_deleted_user":
            await self.config.user_from_id(user_id).clear()

    async def _get_api_key(self):
        """Get the Riot API key from config"""
        api_key = await self.config.api_key()
        if not api_key:
            raise commands.UserFeedbackCheckFailure(
                _("No Riot API key set. Please set one using `{prefix}lolset apikey <key>`")
            )
        return api_key

    def _get_endpoint_key(self, url: str) -> str:
        """Determine the endpoint key for rate limiting"""
        if "/champion-rotations" in url:
            return "champion-rotations"
        elif "/summoner/v4/summoners/" in url:
            return "summoner"
        elif "/league/v4/entries/by-summoner/" in url:
            return "league-entries"
        elif "/league/v4/challengerleagues/" in url:
            return "league-challenger"
        elif "/league/v4/masterleagues/" in url:
            return "league-master"
        elif "/league/v4/grandmasterleagues/" in url:
            return "league-grandmaster"
        elif "/riot/account/v1/" in url:
            return "account"
        elif "/match/v5/" in url:
            return "match"
        elif "/champion-mastery/v4/" in url:
            return "champion-mastery"
        elif "/status/v4/" in url:
            return "status"
        elif "/clash/v1/teams/" in url or "/clash/v1/tournaments/by-team/" in url:
            return "clash-teams"
        elif "/clash/v1/tournaments" in url:
            return "clash-tournaments"
        elif "/clash/v1/players/" in url:
            return "clash-players"
        else:
            return "default"

    async def _make_request(self, url: str, headers: Dict = None, params: Dict = None) -> Dict:
        """Enhanced API request with caching and error handling"""
        # Check cache first
        cache_key = f"{url}:{json.dumps(params, sort_keys=True) if params else ''}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data is not None:
            self.stats.record_cache_hit()
            return cached_data
        
        self.stats.record_cache_miss()
        
        # Determine endpoint for rate limiting
        endpoint_key = self._get_endpoint_key(url)
        
        # Wait for rate limit clearance
        await self.rate_limiter.wait_for_endpoint(endpoint_key)
        
        # Record API call
        self.stats.record_api_call(endpoint_key)
        
        api_key = await self._get_api_key()
        
        if headers is None:
            headers = {}
        headers["X-Riot-Token"] = api_key
        
        try:
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Cache successful responses
                    self.cache.set(cache_key, data)
                    return data
                else:
                    error_msg = await self._handle_api_error(resp.status, "API request")
                    raise commands.UserFeedbackCheckFailure(error_msg)
        except aiohttp.ClientError as e:
            raise commands.UserFeedbackCheckFailure(f"Network error: {str(e)}")
    
    async def _get_champion_data_detailed(self) -> Dict:
        """Get detailed champion data from Data Dragon with caching"""
        cached_data = self.champion_cache.get("champion_detailed")
        
        if cached_data is not None:
            return cached_data
        
        url = "http://ddragon.leagueoflegends.com/cdn/13.24.1/data/en_US/champion.json"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.champion_cache.set("champion_detailed", data)
                    return data
                else:
                    return {}
        except:
            return {}
    
    def _find_champion_by_name(self, champion_name: str, champion_data: Dict) -> Dict:
        """Find champion by name (fuzzy matching)"""
        champion_name = champion_name.lower().replace(" ", "").replace("'", "")
        
        for champ_key, champ_info in champion_data.get("data", {}).items():
            # Check exact match
            if champ_key.lower() == champion_name:
                return champ_info
            
            # Check display name
            if champ_info["name"].lower().replace(" ", "").replace("'", "") == champion_name:
                return champ_info
            
            # Check aliases
            for alias in champ_info.get("aliases", []):
                if alias.lower().replace(" ", "").replace("'", "") == champion_name:
                    return champ_info
        
        return None

    def _normalize_region(self, region: str) -> str:
        """Normalize region input to proper format"""
        region = region.lower()
        if region in REGION_MAPPING:
            return REGION_MAPPING[region]
        elif region in REGION_MAPPING.values():
            return region
        else:
            raise commands.BadArgument(f"Invalid region: {region}. Valid regions: {', '.join(REGION_MAPPING.keys())}")

    async def _get_summoner_by_name(self, region: str, summoner_name: str) -> Dict:
        """Get summoner by name using Account API then Summoner API"""
        # First get account info using Riot ID
        if "#" not in summoner_name:
            summoner_name += "#NA1"  # Default tag if not provided
        
        game_name, tag_line = summoner_name.split("#", 1)
        
        # Get routing value for account API
        if region in ["na1", "br1", "la1", "la2"]:
            routing = "americas"
        elif region in ["kr", "jp1"]:
            routing = "asia"
        elif region in ["euw1", "eun1", "tr1", "ru", "me1"]:
            routing = "europe"
        else:
            routing = "sea"
        
        # Get account by Riot ID
        account_url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        account_data = await self._make_request(account_url)
        
        # Get summoner by PUUID
        summoner_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{account_data['puuid']}"
        summoner_data = await self._make_request(summoner_url)
        
        # Combine data
        summoner_data.update(account_data)
        return summoner_data

    async def _get_rank_info(self, region: str, summoner_id: str) -> List[Dict]:
        """Get ranked information for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        return await self._make_request(url)

    async def _get_champion_rotations(self, region: str) -> Dict:
        """Get current champion rotations"""
        url = f"https://{region}.api.riotgames.com/lol/platform/v3/champion-rotations"
        return await self._make_request(url)

    async def _get_champion_mastery(self, region: str, puuid: str, count: int = 10) -> List[Dict]:
        """Get champion mastery for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top"
        params = {"count": count}
        return await self._make_request(url, params=params)

    async def _get_mastery_score(self, region: str, puuid: str) -> int:
        """Get total mastery score for a summoner"""
        url = f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/scores/by-puuid/{puuid}"
        return await self._make_request(url)

    async def _get_match_history(self, routing: str, puuid: str, count: int = 5, start: int = 0) -> List[str]:
        """Get match history for a player"""
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": min(count, 20), "start": start}  # Limit to 20 per request
        
        return await self._make_request(url, params=params)

    async def _get_match_details(self, routing: str, match_id: str) -> Dict:
        """Get detailed information about a match"""
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._make_request(url)

    async def _get_champion_data(self) -> Dict:
        """Get champion data from Data Dragon (doesn't count against rate limit)"""
        url = "http://ddragon.leagueoflegends.com/cdn/13.24.1/data/en_US/champion.json"
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {}
        except:
            return {}

    def _get_champion_name_by_id(self, champion_id: int, champion_data: Dict) -> str:
        """Get champion name by ID"""
        for champ_name, champ_info in champion_data.get("data", {}).items():
            if int(champ_info["key"]) == champion_id:
                return champ_info["name"]
        return f"Champion {champion_id}"

    def _create_summoner_embed(self, summoner_data: Dict, rank_data: List[Dict]) -> discord.Embed:
        """Create an embed for summoner information"""
        embed = discord.Embed(
            title=f"{summoner_data['gameName']}#{summoner_data['tagLine']}",
            color=0x1E90FF
        )
        
        # Profile icon
        if "profileIconId" in summoner_data:
            icon_url = f"http://ddragon.leagueoflegends.com/cdn/13.24.1/img/profileicon/{summoner_data['profileIconId']}.png"
            embed.set_thumbnail(url=icon_url)
        
        # Basic info
        embed.add_field(name="Level", value=summoner_data.get("summonerLevel", "N/A"), inline=True)
        
        # Ranked information
        if rank_data:
            for rank in rank_data:
                queue_type = rank["queueType"].replace("_", " ").title()
                tier = rank.get("tier", "Unranked").title()
                division = rank.get("rank", "")
                lp = rank.get("leaguePoints", 0)
                wins = rank.get("wins", 0)
                losses = rank.get("losses", 0)
                
                if tier != "Unranked":
                    rank_str = f"{tier} {division} ({lp} LP)\n{wins}W / {losses}L"
                    winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
                    rank_str += f"\n{winrate}% WR"
                else:
                    rank_str = "Unranked"
                
                embed.add_field(name=queue_type, value=rank_str, inline=True)
        else:
            embed.add_field(name="Ranked", value="Unranked", inline=True)
        
        # Add region info
        embed.set_footer(text=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return embed
    
    async def _calculate_tier_score(self, rank_data: List[Dict]) -> int:
        """Calculate a numerical score for ranking comparison"""
        tier_scores = {
            "IRON": 0,
            "BRONZE": 400,
            "SILVER": 800,
            "GOLD": 1200,
            "PLATINUM": 1600,
            "EMERALD": 2000,
            "DIAMOND": 2400,
            "MASTER": 2800,
            "GRANDMASTER": 3200,
            "CHALLENGER": 3600
        }
        
        division_scores = {"IV": 0, "III": 100, "II": 200, "I": 300}
        
        for rank in rank_data:
            if rank["queueType"] == "RANKED_SOLO_5x5":
                tier = rank.get("tier", "UNRANKED")
                division = rank.get("rank", "IV")
                lp = rank.get("leaguePoints", 0)
                
                if tier in tier_scores:
                    return tier_scores[tier] + division_scores.get(division, 0) + lp
        
        return 0  # Unranked

    def _format_duration(self, seconds: int) -> str:
        """Format game duration into readable format"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}m {seconds}s"

    def _get_rank_emoji(self, tier: str) -> str:
        """Get emoji representation for rank tiers"""
        rank_emojis = {
            "IRON": "🥉",
            "BRONZE": "🥉",
            "SILVER": "🥈",
            "GOLD": "🥇",
            "PLATINUM": "💎",
            "EMERALD": "💚",
            "DIAMOND": "💎",
            "MASTER": "👑",
            "GRANDMASTER": "👑",
            "CHALLENGER": "🏆"
        }
        return rank_emojis.get(tier, "❓")

    # Commands
    @commands.group(name="lol", aliases=["league"])
    async def lol(self, ctx):
        """League of Legends commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @lol.command(name="summoner", aliases=["player", "profile"])
    async def summoner(self, ctx, region: str = None, *, summoner_name: str):
        """Look up a summoner's profile
        
        Examples:
        - `[p]lol summoner na Faker#KR1`
        - `[p]lol summoner Doublelift#NA1` (uses default region)
        """
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Get rank data
                rank_data = await self._get_rank_info(region, summoner_data["id"])
                
                # Create and send embed
                embed = self._create_summoner_embed(summoner_data, rank_data)
                embed.add_field(name="Region", value=region.upper(), inline=True)
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error looking up summoner: {str(e)}")

    @lol.command(name="mastery", aliases=["masteries"])
    async def mastery(self, ctx, region: str = None, *, summoner_name: str):
        """Show champion mastery for a summoner
        
        Examples:
        - `[p]lol mastery na Faker#KR1`
        - `[p]lol mastery Doublelift#NA1` (uses default region)
        """
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Get champion mastery data
                mastery_data = await self._get_champion_mastery(region, summoner_data["puuid"], count=5)
                mastery_score = await self._get_mastery_score(region, summoner_data["puuid"])
                
                # Get champion data for names
                champion_data = await self._get_champion_data()
                
                embed = discord.Embed(
                    title=f"Champion Mastery - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0x9932CC
                )
                
                embed.add_field(name="Total Mastery Score", value=f"{mastery_score:,}", inline=True)
                embed.add_field(name="Region", value=region.upper(), inline=True)
                embed.add_field(name="Top Champions", value="", inline=False)
                
                for i, mastery in enumerate(mastery_data, 1):
                    champion_name = self._get_champion_name_by_id(mastery["championId"], champion_data)
                    level = mastery["championLevel"]
                    points = mastery["championPoints"]
                    last_play = datetime.fromtimestamp(mastery["lastPlayTime"] / 1000).strftime("%Y-%m-%d")
                    
                    mastery_str = f"**{champion_name}**\nLevel {level} - {points:,} points\nLast played: {last_play}"
                    embed.add_field(name=f"#{i}", value=mastery_str, inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error getting mastery data: {str(e)}")

    @lol.command(name="rotations", aliases=["rotation", "free"])
    async def rotations(self, ctx, region: str = None):
        """Show current champion rotations"""
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                rotation_data = await self._get_champion_rotations(region)
                champion_data = await self._get_champion_data()
                
                embed = discord.Embed(
                    title=f"Champion Rotations ({region.upper()})",
                    color=0x00FF00
                )
                
                # Free champion IDs
                free_champions = rotation_data.get("freeChampionIds", [])
                if free_champions:
                    champion_names = []
                    for champ_id in free_champions[:10]:  # Limit to 10 to avoid embed limits
                        name = self._get_champion_name_by_id(champ_id, champion_data)
                        champion_names.append(name)
                    
                    if len(free_champions) > 10:
                        champion_names.append(f"... and {len(free_champions) - 10} more")
                    
                    embed.add_field(
                        name=f"Free Champions ({len(free_champions)} total)",
                        value="\n".join(champion_names) or f"{len(free_champions)} champions available",
                        inline=False
                    )
                
                # New player rotations
                new_player_champions = rotation_data.get("freeChampionIdsForNewPlayers", [])
                if new_player_champions:
                    max_level = rotation_data.get("maxNewPlayerLevel", 10)
                    new_player_names = []
                    for champ_id in new_player_champions:
                        name = self._get_champion_name_by_id(champ_id, champion_data)
                        new_player_names.append(name)
                    
                    embed.add_field(
                        name=f"New Player Champions (Level 1-{max_level})",
                        value="\n".join(new_player_names) or f"{len(new_player_champions)} champions available",
                        inline=False
                    )
                
                embed.set_footer(text=f"Data from Riot Games API • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error getting rotations: {str(e)}")

    @lol.command(name="matches", aliases=["match", "history"])
    async def matches(self, ctx, region: str = None, *, summoner_name: str):
        """Show recent match history for a summoner
        
        Examples:
        - `[p]lol matches na Faker#KR1`
        - `[p]lol matches Doublelift#NA1` (uses default region)
        """
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Get match routing
                routing = MATCH_ROUTING.get(region, "americas")
                
                # Get match history (limit to 5 to avoid overwhelming the embed)
                match_ids = await self._get_match_history(routing, summoner_data["puuid"], count=5)
                
                if not match_ids:
                    await ctx.send("No recent matches found.")
                    return
                
                embed = discord.Embed(
                    title=f"Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0xFF6B35
                )
                
                # Get details for each match
                match_details_list = []
                for match_id in match_ids[:3]:  # Only process first 3 matches
                    try:
                        match_details = await self._get_match_details(routing, match_id)
                        match_details_list.append(match_details)
                    except Exception as e:
                        # Skip this match if there's an error
                        continue
                
                for i, match_details in enumerate(match_details_list):
                    # Find the player in the match
                    participant = None
                    for p in match_details["info"]["participants"]:
                        if p["puuid"] == summoner_data["puuid"]:
                            participant = p
                            break
                    
                    if participant:
                        # Format match info
                        game_mode = match_details["info"]["gameMode"]
                        game_duration = match_details["info"]["gameDuration"]
                        champion = participant["championName"]
                        kills = participant["kills"]
                        deaths = participant["deaths"]
                        assists = participant["assists"]
                        win = participant["win"]
                        
                        # Game duration in minutes
                        duration_minutes = game_duration // 60
                        duration_seconds = game_duration % 60
                        
                        result = "🏆 Victory" if win else "❌ Defeat"
                        kda = f"{kills}/{deaths}/{assists}"
                        
                        # Calculate KDA ratio
                        kda_ratio = (kills + assists) / max(deaths, 1)
                        
                        match_info = (
                            f"{result}\n"
                            f"**{champion}** - {kda} ({kda_ratio:.1f} KDA)\n"
                            f"{game_mode} - {duration_minutes}m {duration_seconds}s"
                        )
                        
                        embed.add_field(
                            name=f"Match {i+1}",
                            value=match_info,
                            inline=True
                        )
                
                if len(match_ids) > len(match_details_list):
                    embed.set_footer(text=f"Showing {len(match_details_list)} of {len(match_ids)} recent matches")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error getting match history: {str(e)}")

    @lol.command(name="link")
    async def link_account(self, ctx, region: str, *, summoner_name: str):
        """Link your Discord account to a League of Legends summoner
        
        Example:
        - `[p]lol link na Faker#KR1`
        """
        region = self._normalize_region(region)
        
        try:
            # Verify the summoner exists
            summoner_data = await self._get_summoner_by_name(region, summoner_name)
            
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

    @lol.command(name="unlink")
    async def unlink_account(self, ctx):
        """Unlink your League of Legends account"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You don't have a linked League of Legends account.")
            return
        
        await self.config.user(ctx.author).linked_account.clear()
        await ctx.send("✅ Successfully unlinked your League of Legends account.")

    @lol.command(name="me", aliases=["myprofile"])
    async def my_profile(self, ctx):
        """Show your linked League of Legends profile"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link <region> <summoner#tag>` to link one.")
            return
        
        # Get current data for the linked account using the correct method call
        await self.summoner(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])

    @lol.command(name="mymastery", aliases=["mymasteries"])
    async def my_mastery(self, ctx):
        """Show your linked account's champion mastery"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link <region> <summoner#tag>` to link one.")
            return
        
        # Get mastery data for the linked account
        await self.mastery(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])

    @lol.command(name="mymatches", aliases=["myhistory"])
    async def my_matches(self, ctx):
        """Show your linked account's match history"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link <region> <summoner#tag>` to link one.")
            return
        
        # Get match history for the linked account
        await self.matches(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])

    @lol.command(name="status")
    async def api_status(self, ctx):
        """Check the current status of rate limiting"""
        embed = discord.Embed(title="Rate Limit Status", color=0x0099E1)
        
        # Show status for key endpoints
        key_endpoints = ["summoner", "account", "match", "champion-rotations", "league-entries"]
        
        for endpoint in key_endpoints:
            status = self.rate_limiter.get_endpoint_status(endpoint)
            if status:
                status_str = " | ".join([f"{period}: {usage}" for period, usage in status.items()])
                embed.add_field(
                    name=endpoint.replace("-", " ").title(),
                    value=status_str,
                    inline=True
                )
        
        embed.set_footer(text="Usage: current/limit")
        await ctx.send(embed=embed)

    @lol.command(name="live", aliases=["spectate"])
    async def live_game(self, ctx, region: str = None, *, summoner_name: str):
        """Check if a summoner is currently in a live game
        
        Examples:
        - `[p]lol live na Faker#KR1`
        - `[p]lol live Doublelift#NA1` (uses default region)
        """
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Check for active game
                url = f"https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{summoner_data['puuid']}"
                
                try:
                    game_data = await self._make_request(url)
                    
                    embed = discord.Embed(
                        title=f"Live Game - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                        color=0xFF0000
                    )
                    
                    # Game info
                    game_mode = game_data["gameMode"]
                    game_length = game_data["gameLength"]
                    game_minutes = game_length // 60
                    game_seconds = game_length % 60
                    
                    embed.add_field(name="Game Mode", value=game_mode, inline=True)
                    embed.add_field(name="Game Length", value=f"{game_minutes}m {game_seconds}s", inline=True)
                    embed.add_field(name="Region", value=region.upper(), inline=True)
                    
                    # Find the player and their team
                    for participant in game_data["participants"]:
                        if participant["puuid"] == summoner_data["puuid"]:
                            champion_name = participant["championId"]  # This is actually champion ID
                            embed.add_field(name="Champion", value=f"Champion ID: {champion_name}", inline=True)
                            break
                    
                    embed.set_footer(text="🔴 Currently in game")
                    
                except commands.UserFeedbackCheckFailure as e:
                    if "not found" in str(e).lower():
                        embed = discord.Embed(
                            title=f"{summoner_data['gameName']}#{summoner_data['tagLine']}",
                            description="Not currently in a game",
                            color=0x808080
                        )
                    else:
                        raise e
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error checking live game: {str(e)}")

    @lol.command(name="rank", aliases=["ranks"])
    async def rank(self, ctx, region: str = None, *, summoner_name: str):
        """Show detailed rank information for a summoner
        
        Examples:
        - `[p]lol rank na Faker#KR1`
        - `[p]lol rank Doublelift#NA1` (uses default region)
        """
        async with ctx.typing():
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Get rank data
                rank_data = await self._get_rank_info(region, summoner_data["id"])
                
                embed = discord.Embed(
                    title=f"Ranked Info - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0xFFD700
                )
                
                if rank_data:
                    for rank in rank_data:
                        queue_type = rank["queueType"].replace("_", " ").title()
                        tier = rank.get("tier", "Unranked").title()
                        division = rank.get("rank", "")
                        lp = rank.get("leaguePoints", 0)
                        wins = rank.get("wins", 0)
                        losses = rank.get("losses", 0)
                        
                        if tier != "Unranked":
                            total_games = wins + losses
                            winrate = round((wins / total_games) * 100, 1) if total_games > 0 else 0
                            
                            rank_info = (
                                f"**{tier} {division}** ({lp} LP)\n"
                                f"Wins: {wins} | Losses: {losses}\n"
                                f"Win Rate: {winrate}%\n"
                                f"Total Games: {total_games}"
                            )
                            
                            # Add hot streak and veteran status if available
                            if rank.get("hotStreak"):
                                rank_info += "\n🔥 Hot Streak!"
                            if rank.get("veteran"):
                                rank_info += "\n⭐ Veteran"
                            
                        else:
                            rank_info = "Unranked"
                        
                        embed.add_field(name=queue_type, value=rank_info, inline=True)
                else:
                    embed.add_field(name="Ranked Status", value="Unranked in all queues", inline=False)
                
                embed.add_field(name="Region", value=region.upper(), inline=True)
                embed.add_field(name="Level", value=summoner_data.get("summonerLevel", "N/A"), inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error getting rank info: {str(e)}")
        
    @lol.command(name="champion", aliases=["champ"])
    async def champion_info(self, ctx, *, champion_name: str):
        """Get detailed information about a champion
        
        Examples:
        - `[p]lol champion Yasuo`
        - `[p]lol champ Kai'Sa`
        """
        async with ctx.typing():
            self.stats.record_command("champion")
            
            try:
                champion_data = await self._get_champion_data_detailed()
                champion = self._find_champion_by_name(champion_name, champion_data)
                
                if not champion:
                    await ctx.send(f"❌ Champion '{champion_name}' not found. Please check the spelling.")
                    return
                
                embed = discord.Embed(
                    title=champion["name"],
                    description=champion["title"],
                    color=0x0596AA
                )
                
                # Champion splash art
                splash_url = f"http://ddragon.leagueoflegends.com/cdn/img/champion/splash/{champion['id']}_0.jpg"
                embed.set_image(url=splash_url)
                
                # Champion square icon
                square_url = f"http://ddragon.leagueoflegends.com/cdn/13.24.1/img/champion/{champion['id']}.png"
                embed.set_thumbnail(url=square_url)
                
                # Basic info
                embed.add_field(name="Tags", value=" • ".join(champion["tags"]), inline=True)
                embed.add_field(name="Difficulty", value=f"{champion['info']['difficulty']}/10", inline=True)
                
                # Stats
                stats = champion["stats"]
                embed.add_field(
                    name="Base Stats",
                    value=f"**HP:** {stats['hp']} (+{stats['hpperlevel']}/lvl)\n"
                          f"**Mana:** {stats['mp']} (+{stats['mpperlevel']}/lvl)\n"
                          f"**AD:** {stats['attackdamage']} (+{stats['attackdamageperlevel']}/lvl)\n"
                          f"**Armor:** {stats['armor']} (+{stats['armorperlevel']}/lvl)\n"
                          f"**MR:** {stats['spellblock']} (+{stats['spellblockperlevel']}/lvl)",
                    inline=False
                )
                
                # Abilities (basic info)
                embed.add_field(
                    name="Champion Info",
                    value=f"**Attack Range:** {stats['attackrange']}\n"
                          f"**Move Speed:** {stats['movespeed']}\n"
                          f"**Attack Speed:** {stats['attackspeed']:.3f} (+{stats['attackspeedperlevel']:.3f}%/lvl)",
                    inline=False
                )
                
                # Lore snippet
                lore = champion.get("lore", "")
                if len(lore) > 200:
                    lore = lore[:200] + "..."
                embed.add_field(name="Lore", value=lore, inline=False)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error getting champion information: {str(e)}")

    @lol.command(name="coginfo", aliases=["usage"])
    @checks.is_owner()
    async def cog_statistics(self, ctx):
        """Show cog usage statistics"""
        
        async with ctx.typing():
            self.stats.record_command("analyze")
            
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get summoner data
                summoner_data = await self._get_summoner_by_name(region, summoner_name)
                
                # Get match routing
                routing = MATCH_ROUTING.get(region, "americas")
                
                # Get last 20 matches
                match_ids = await self._get_match_history(routing, summoner_data["puuid"], count=20)
                
                if not match_ids:
                    await ctx.send("No recent matches found for analysis.")
                    return
                
                # Analyze matches
                matches_data = []
                champion_stats = defaultdict(lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0})
                
                for match_id in match_ids[:15]:  # Limit to 15 to avoid too many API calls
                    try:
                        match_details = await self._get_match_details(routing, match_id)
                        
                        # Find the player in the match
                        participant = None
                        for p in match_details["info"]["participants"]:
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
                                "gameMode": match_details["info"]["gameMode"],
                                "gameDuration": match_details["info"]["gameDuration"]
                            })
                            
                            # Update champion stats
                            champ = participant["championName"]
                            champion_stats[champ]["games"] += 1
                            champion_stats[champ]["kills"] += participant["kills"]
                            champion_stats[champ]["deaths"] += participant["deaths"]
                            champion_stats[champ]["assists"] += participant["assists"]
                            if participant["win"]:
                                champion_stats[champ]["wins"] += 1
                        
                    except Exception:
                        continue
                
                if not matches_data:
                    await ctx.send("Could not analyze any matches.")
                    return
                
                # Calculate statistics
                total_games = len(matches_data)
                wins = sum(1 for m in matches_data if m["win"])
                winrate = (wins / total_games) * 100
                
                avg_kills = statistics.mean([m["kills"] for m in matches_data])
                avg_deaths = statistics.mean([m["deaths"] for m in matches_data])
                avg_assists = statistics.mean([m["assists"] for m in matches_data])
                avg_kda = (avg_kills + avg_assists) / max(avg_deaths, 1)
                
                # Most played champions
                most_played = sorted(champion_stats.items(), key=lambda x: x[1]["games"], reverse=True)[:3]
                
                # Create analysis embed
                embed = discord.Embed(
                    title=f"Performance Analysis - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0x00FF7F if winrate >= 50 else 0xFF6B6B
                )
                
                # Overall stats
                embed.add_field(
                    name="📊 Overall Performance",
                    value=f"**Games Analyzed:** {total_games}\n"
                          f"**Win Rate:** {winrate:.1f}% ({wins}W / {total_games - wins}L)\n"
                          f"**Average KDA:** {avg_kda:.2f}\n"
                          f"**K/D/A:** {avg_kills:.1f} / {avg_deaths:.1f} / {avg_assists:.1f}",
                    inline=False
                )
                
                # Most played champions
                if most_played:
                    champ_text = ""
                    for champ, stats in most_played:
                        champ_winrate = (stats["wins"] / stats["games"]) * 100
                        champ_kda = (stats["kills"] + stats["assists"]) / max(stats["deaths"], 1)
                        champ_text += f"**{champ}** ({stats['games']} games)\n"
                        champ_text += f"  {champ_winrate:.1f}% WR • {champ_kda:.2f} KDA\n"
                    
                    embed.add_field(
                        name="🏆 Most Played Champions",
                        value=champ_text,
                        inline=False
                    )
                
                # Recent trend (last 5 games)
                recent_matches = matches_data[:5]
                recent_wins = sum(1 for m in recent_matches if m["win"])
                recent_trend = "📈 Winning streak!" if recent_wins >= 4 else "📉 Losing streak" if recent_wins <= 1 else "📊 Mixed results"
                
                embed.add_field(
                    name="🔄 Recent Trend (Last 5 Games)",
                    value=f"{recent_trend}\n{recent_wins}W / {5 - recent_wins}L",
                    inline=True
                )
                
                embed.add_field(name="Region", value=region.upper(), inline=True)
                embed.set_footer(text=f"Analysis based on {total_games} recent games")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error analyzing summoner: {str(e)}")

    @lol.command(name="compare", aliases=["vs"])
    async def compare_summoners(self, ctx, summoner1: str, summoner2: str, region: str = None):
        """Compare two summoners' stats and performance
        
        Examples:
        - `[p]lol compare Faker#KR1 Showmaker#KR1 kr`
        - `[p]lol vs Doublelift#NA1 Bjergsen#NA1` (uses default region)
        """
        async with ctx.typing():
            self.stats.record_command("compare")
            
            # Determine region
            if region is None:
                region = await self.config.guild(ctx.guild).default_region()
            else:
                region = self._normalize_region(region)
            
            try:
                # Get both summoners' data
                summoner1_data = await self._get_summoner_by_name(region, summoner1)
                summoner2_data = await self._get_summoner_by_name(region, summoner2)
                
                # Get rank data for both
                rank1_data = await self._get_rank_info(region, summoner1_data["id"])
                rank2_data = await self._get_rank_info(region, summoner2_data["id"])
                
                # Get mastery scores
                routing = MATCH_ROUTING.get(region, "americas")
                mastery1_score = await self._get_mastery_score(region, summoner1_data["puuid"])
                mastery2_score = await self._get_mastery_score(region, summoner2_data["puuid"])
                
                # Create comparison embed
                embed = discord.Embed(
                    title="⚔️ Summoner Comparison",
                    color=0x9932CC
                )
                
                # Basic info comparison
                embed.add_field(
                    name=f"👤 {summoner1_data['gameName']}#{summoner1_data['tagLine']}",
                    value=f"**Level:** {summoner1_data.get('summonerLevel', 'N/A')}\n"
                          f"**Mastery Score:** {mastery1_score:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="🆚",
                    value="**VS**",
                    inline=True
                )
                
                embed.add_field(
                    name=f"👤 {summoner2_data['gameName']}#{summoner2_data['tagLine']}",
                    value=f"**Level:** {summoner2_data.get('summonerLevel', 'N/A')}\n"
                          f"**Mastery Score:** {mastery2_score:,}",
                    inline=True
                )
                
                # Rank comparison
                def get_rank_string(rank_data):
                    for rank in rank_data:
                        if rank["queueType"] == "RANKED_SOLO_5x5":
                            tier = rank.get("tier", "Unranked").title()
                            division = rank.get("rank", "")
                            lp = rank.get("leaguePoints", 0)
                            wins = rank.get("wins", 0)
                            losses = rank.get("losses", 0)
                            if tier != "Unranked":
                                winrate = round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0
                                return f"{tier} {division} ({lp} LP)\n{wins}W / {losses}L • {winrate}% WR"
                            else:
                                return "Unranked"
                    return "Unranked"
                
                rank1_str = get_rank_string(rank1_data)
                rank2_str = get_rank_string(rank2_data)
                
                embed.add_field(
                    name="🏆 Ranked Solo/Duo",
                    value=f"**{summoner1_data['gameName']}:**\n{rank1_str}\n\n"
                          f"**{summoner2_data['gameName']}:**\n{rank2_str}",
                    inline=False
                )
                
                embed.add_field(name="Region", value=region.upper(), inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error comparing summoners: {str(e)}")

    @lol.command(name="stats", aliases=["statistics"])  # Changed from "cogstats"
    @checks.is_owner()
    async def cog_statistics(self, ctx):
        """Show cog usage statistics"""
        uptime = time.time() - self.stats.start_time
        uptime_hours = uptime / 3600
        
        embed = discord.Embed(title="📊 LoL Cog Statistics", color=0x0099E1)
        
        # API calls
        total_calls = sum(self.stats.api_calls.values())
        calls_per_hour = total_calls / max(uptime_hours, 1)
        
        embed.add_field(
            name="🔗 API Usage",
            value=f"**Total Calls:** {total_calls}\n"
                f"**Calls/Hour:** {calls_per_hour:.1f}\n"
                f"**Cache Hits:** {self.stats.cache_hits}\n"
                f"**Cache Misses:** {self.stats.cache_misses}",
            inline=True
        )
        
        # Cache efficiency
        total_requests = self.stats.cache_hits + self.stats.cache_misses
        cache_rate = (self.stats.cache_hits / max(total_requests, 1)) * 100
        
        embed.add_field(
            name="💾 Cache Performance",
            value=f"**Hit Rate:** {cache_rate:.1f}%\n"
                f"**Cache Size:** {self.cache.size()}\n"
                f"**Champion Cache:** {self.champion_cache.size()}",
            inline=True
        )
        
        # Most used commands
        top_commands = sorted(self.stats.commands_used.items(), key=lambda x: x[1], reverse=True)[:5]
        commands_text = "\n".join([f"{cmd}: {count}" for cmd, count in top_commands])
        
        embed.add_field(
            name="🎯 Top Commands",
            value=commands_text or "No commands used yet",
            inline=True
        )
        
        # Most used endpoints
        top_endpoints = sorted(self.stats.api_calls.items(), key=lambda x: x[1], reverse=True)[:5]
        endpoints_text = "\n".join([f"{endpoint}: {count}" for endpoint, count in top_endpoints])
        
        embed.add_field(
            name="🔄 Top API Endpoints",
            value=endpoints_text or "No API calls yet",
            inline=True
        )
        
        # Error statistics
        total_errors = sum(self.stats.errors.values())
        embed.add_field(
            name="⚠️ Errors",
            value=f"**Total:** {total_errors}\n"
                f"**Error Rate:** {(total_errors / max(total_calls, 1) * 100):.2f}%",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Uptime",
            value=f"{uptime_hours:.1f} hours",
            inline=True
        )
        
        await ctx.send(embed=embed)

    # Settings commands
    @commands.group(name="lolset")
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
        except:
            pass

    @lol_settings.command(name="region")
    async def set_default_region(self, ctx, region: str):
        """Set the default region for this server
        
        Valid regions: na, euw, eune, kr, br, jp, ru, oc, tr, lan, las, me, sg, tw, vn
        """
        region = self._normalize_region(region)
        await self.config.guild(ctx.guild).default_region.set(region)
        await ctx.send(f"✅ Default region set to **{region.upper()}**")

    @lol_settings.command(name="info")
    async def settings_info(self, ctx):
        """Show current settings"""
        api_key_set = bool(await self.config.api_key())
        default_region = await self.config.guild(ctx.guild).default_region()
        
        embed = discord.Embed(title="League of Legends Settings", color=0x0099E1)
        embed.add_field(name="API Key", value="✅ Set" if api_key_set else "❌ Not Set", inline=True)
        embed.add_field(name="Default Region", value=default_region.upper(), inline=True)
        
        # Show some rate limit info for key endpoints
        summoner_status = self.rate_limiter.get_endpoint_status("summoner")
        match_status = self.rate_limiter.get_endpoint_status("match")
        
        if summoner_status:
            summoner_usage = list(summoner_status.values())[0]
            embed.add_field(name="Summoner API Usage", value=summoner_usage, inline=True)
        
        if match_status:
            match_usage = list(match_status.values())[0]
            embed.add_field(name="Match API Usage", value=match_usage, inline=True)
        
        await ctx.send(embed=embed)

    @lol_settings.command(name="testapi")
    @checks.is_owner()
    async def test_api(self, ctx):
        """Test the API connection"""
        try:
            # Test with a simple status check
            api_key = await self._get_api_key()
            
            # Try to get NA server status (usually works without issues)
            url = "https://na1.api.riotgames.com/lol/status/v4/platform-data"
            status_data = await self._make_request(url)
            
            embed = discord.Embed(title="API Test Results", color=0x00FF00)
            embed.add_field(name="Status", value="✅ Success", inline=True)
            embed.add_field(name="Server", value=status_data.get("name", "NA"), inline=True)
            
            # Test rate limiter status
            status = self.rate_limiter.get_endpoint_status("status")
            if status:
                usage = list(status.values())[0]
                embed.add_field(name="Rate Limit", value=usage, inline=True)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(title="API Test Results", color=0xFF0000)
            embed.add_field(name="Status", value="❌ Failed", inline=True)
            embed.add_field(name="Error", value=str(e), inline=False)
            await ctx.send(embed=embed)

    @lol_settings.command(name="ratelimits")
    async def show_rate_limits(self, ctx):
        """Show all endpoint rate limits"""
        embed = discord.Embed(title="Endpoint Rate Limits", color=0x0099E1)
        
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
        
        await ctx.send(embed=embed)
        
    @lol_settings.command(name="clearcache")
    @checks.is_owner()
    async def clear_cache(self, ctx):
        """Clear all cached data"""
        self.cache.clear()
        self.champion_cache.clear()
        await ctx.send("✅ All cached data has been cleared.")

    @lol_settings.command(name="resetstats")
    @checks.is_owner()
    async def reset_statistics(self, ctx):
        """Reset cog usage statistics"""
        self.stats = CogStatistics()
        await ctx.send("✅ Cog statistics have been reset.")
