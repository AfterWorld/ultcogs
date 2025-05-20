import asyncio
import aiohttp
import discord
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Deque, Tuple
from collections import deque, defaultdict
from redbot.core import commands, Config, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu

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
        
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        
        self.session = aiohttp.ClientSession()
        self.rate_limiter = RiotRateLimiter()
        
    def cog_unload(self):
        if self.session:
            asyncio.create_task(self.session.close())

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
        """Make an API request to Riot Games API with endpoint-specific rate limiting"""
        # Determine endpoint for rate limiting
        endpoint_key = self._get_endpoint_key(url)
        
        # Wait for rate limit clearance
        await self.rate_limiter.wait_for_endpoint(endpoint_key)
        
        api_key = await self._get_api_key()
        
        if headers is None:
            headers = {}
        headers["X-Riot-Token"] = api_key
        
        try:
            async with self.session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 403:
                    raise commands.UserFeedbackCheckFailure(_("Invalid API key or insufficient permissions"))
                elif resp.status == 404:
                    raise commands.UserFeedbackCheckFailure(_("Summoner not found"))
                elif resp.status == 429:
                    # Rate limit hit - extract retry-after header if available
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                        await asyncio.sleep(wait_time)
                        # Retry the request once
                        return await self._make_request(url, headers, params)
                    else:
                        raise commands.UserFeedbackCheckFailure(_("Rate limit exceeded. Please try again later"))
                elif resp.status == 500:
                    raise commands.UserFeedbackCheckFailure(_("Riot API is currently unavailable"))
                elif resp.status == 503:
                    raise commands.UserFeedbackCheckFailure(_("Riot API service is temporarily unavailable"))
                else:
                    raise commands.UserFeedbackCheckFailure(f"API request failed with status {resp.status}")
        except aiohttp.ClientError as e:
            raise commands.UserFeedbackCheckFailure(f"Network error: {str(e)}")

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
        
        # Get current data for the linked account
        await self.summoner(ctx, linked_account["region"], linked_account["summoner_name"])

    @lol.command(name="mymastery", aliases=["mymasteries"])
    async def my_mastery(self, ctx):
        """Show your linked account's champion mastery"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link <region> <summoner#tag>` to link one.")
            return
        
        # Get mastery data for the linked account
        await self.mastery(ctx, linked_account["region"], linked_account["summoner_name"])

    @lol.command(name="mymatches", aliases=["myhistory"])
    async def my_matches(self, ctx):
        """Show your linked account's match history"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link <region> <summoner#tag>` to link one.")
            return
        
        # Get match history for the linked account
        await self.matches(ctx, linked_account["region"], linked_account["summoner_name"])

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
