import asyncio
import aiohttp
import discord
from datetime import datetime
from typing import Optional, Dict, List
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

    async def _make_request(self, url: str, headers: Dict = None) -> Dict:
        """Make an API request to Riot Games API"""
        api_key = await self._get_api_key()
        
        if headers is None:
            headers = {}
        headers["X-Riot-Token"] = api_key
        
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 403:
                raise commands.UserFeedbackCheckFailure(_("Invalid API key or insufficient permissions"))
            elif resp.status == 404:
                raise commands.UserFeedbackCheckFailure(_("Summoner not found"))
            elif resp.status == 429:
                raise commands.UserFeedbackCheckFailure(_("Rate limit exceeded. Please try again later"))
            else:
                raise commands.UserFeedbackCheckFailure(f"API request failed with status {resp.status}")

    def _normalize_region(self, region: str) -> str:
        """Normalize region input to proper format"""
        region = region.lower()
        if region in REGION_MAPPING:
            return REGION_MAPPING[region]
        elif region in REGION_MAPPING.values():
            return region
        else:
            raise commands.BadArgument(f"Invalid region: {region}")

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

    async def _get_match_history(self, routing: str, puuid: str, count: int = 5) -> List[str]:
        """Get match history for a player"""
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count}
        
        async with self.session.get(url, headers={"X-Riot-Token": await self._get_api_key()}, params=params) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise commands.UserFeedbackCheckFailure(f"Failed to get match history: {resp.status}")

    async def _get_match_details(self, routing: str, match_id: str) -> Dict:
        """Get detailed information about a match"""
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return await self._make_request(url)

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
                else:
                    rank_str = "Unranked"
                
                embed.add_field(name=queue_type, value=rank_str, inline=True)
        else:
            embed.add_field(name="Ranked", value="Unranked", inline=True)
        
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
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"Error looking up summoner: {str(e)}")

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
                
                embed = discord.Embed(
                    title="Champion Rotations",
                    color=0x00FF00
                )
                
                # Free champion IDs
                free_champions = rotation_data.get("freeChampionIds", [])
                if free_champions:
                    embed.add_field(
                        name="Free Champions",
                        value=f"{len(free_champions)} champions available",
                        inline=False
                    )
                
                # New player rotations
                new_player_champions = rotation_data.get("freeChampionIdsForNewPlayers", [])
                if new_player_champions:
                    max_level = rotation_data.get("maxNewPlayerLevel", 10)
                    embed.add_field(
                        name=f"New Player Champions (Level 1-{max_level})",
                        value=f"{len(new_player_champions)} champions available",
                        inline=False
                    )
                
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
                
                # Get match history
                match_ids = await self._get_match_history(routing, summoner_data["puuid"], count=5)
                
                if not match_ids:
                    await ctx.send("No recent matches found.")
                    return
                
                embed = discord.Embed(
                    title=f"Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0xFF6B35
                )
                
                # Get details for each match (limited to prevent rate limiting)
                for i, match_id in enumerate(match_ids[:3]):  # Only show first 3 for brevity
                    try:
                        match_details = await self._get_match_details(routing, match_id)
                        
                        # Find the player in the match
                        participant = None
                        for p in match_details["info"]["participants"]:
                            if p["puuid"] == summoner_data["puuid"]:
                                participant = p
                                break
                        
                        if participant:
                            # Format match info
                            game_mode = match_details["info"]["gameMode"]
                            champion = participant["championName"]
                            kills = participant["kills"]
                            deaths = participant["deaths"]
                            assists = participant["assists"]
                            win = participant["win"]
                            
                            result = "🏆 Victory" if win else "❌ Defeat"
                            kda = f"{kills}/{deaths}/{assists}"
                            
                            match_info = f"{result}\n{champion} - {kda}\n{game_mode}"
                            embed.add_field(
                                name=f"Match {i+1}",
                                value=match_info,
                                inline=True
                            )
                    except Exception as e:
                        # Skip this match if there's an error
                        continue
                
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
                "puuid": summoner_data["puuid"]
            })
            
            await ctx.send(f"Successfully linked your account to {summoner_data['gameName']}#{summoner_data['tagLine']} ({region.upper()})")
            
        except Exception as e:
            await ctx.send(f"Error linking account: {str(e)}")

    @lol.command(name="me", aliases=["myprofile"])
    async def my_profile(self, ctx):
        """Show your linked League of Legends profile"""
        linked_account = await self.config.user(ctx.author).linked_account()
        
        if not linked_account:
            await ctx.send("You haven't linked a League of Legends account. Use `[p]lol link` to link one.")
            return
        
        # Get current data for the linked account
        await self.summoner(ctx, linked_account["region"], linked_account["summoner_name"])

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
        await ctx.send("API key has been set successfully.")
        
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
        await ctx.send(f"Default region set to {region.upper()}")

    @lol_settings.command(name="info")
    async def settings_info(self, ctx):
        """Show current settings"""
        api_key_set = bool(await self.config.api_key())
        default_region = await self.config.guild(ctx.guild).default_region()
        
        embed = discord.Embed(title="League of Legends Settings", color=0x0099E1)
        embed.add_field(name="API Key", value="✅ Set" if api_key_set else "❌ Not Set", inline=True)
        embed.add_field(name="Default Region", value=default_region.upper(), inline=True)
        
        await ctx.send(embed=embed)
