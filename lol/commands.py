# lol/commands.py - Additional command implementations
import asyncio
import logging
import json
from typing import Optional

import discord
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import humanize_timedelta
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LoLCommands:
    """Mixin class containing additional command implementations"""
    
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(name="mastery", aliases=["masteries"])
    async def mastery(self, ctx, region: str = None, *, summoner_name: str):
        """Show champion mastery for a summoner"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Get champion mastery data
                mastery_data = await self.api_manager.get_champion_mastery(region, summoner_data["puuid"], count=5)
                mastery_score = await self.api_manager.get_mastery_score(region, summoner_data["puuid"])
                
                # Get champion data for names
                champion_data = await self.api_manager.get_champion_data()
                
                embed = discord.Embed(
                    title=f"🏆 Champion Mastery - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0x9932CC,
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="📊 Total Mastery Score", value=f"{mastery_score:,}", inline=True)
                embed.add_field(name="🌍 Region", value=region.upper(), inline=True)
                embed.add_field(name="🏅 Top Champions", value="", inline=False)
                
                for i, mastery in enumerate(mastery_data, 1):
                    champion_name = self._get_champion_name_by_id(mastery["championId"], champion_data)
                    level = mastery["championLevel"]
                    points = mastery["championPoints"]
                    last_play = datetime.fromtimestamp(mastery["lastPlayTime"] / 1000).strftime("%Y-%m-%d")
                    
                    # Add visual indicators for mastery level
                    level_emojis = {7: "💎", 6: "💜", 5: "🔥"}
                    level_emoji = level_emojis.get(level, "⭐")
                    
                    mastery_str = (
                        f"{level_emoji} **{champion_name}**\n"
                        f"Level {level} - {points:,} points\n"
                        f"Last played: {last_play}"
                    )
                    embed.add_field(name=f"#{i}", value=mastery_str, inline=True)
                
                embed.set_footer(
                    text=f"Data from Riot Games",
                    icon_url=self.embed_factory.riot_logo
                )
                
                await ctx.send(embed=embed)
                
                # Save lookup history
                await self.db_manager.save_lookup_history(
                    ctx.author.id, ctx.guild.id if ctx.guild else None, summoner_name, region
                )
                
            except Exception as e:
                logger.error(f"Error getting mastery data: {e}")
                await ctx.send(f"❌ Error getting mastery data: {str(e)}")

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="rotations", aliases=["rotation", "free"])
    async def rotations(self, ctx, region: str = None):
        """Show current champion rotations"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                rotation_data = await self.api_manager.get_champion_rotations(region)
                champion_data = await self.api_manager.get_champion_data()
                
                embed = discord.Embed(
                    title=f"🔄 Champion Rotations ({region.upper()})",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                
                # Free champion IDs
                free_champions = rotation_data.get("freeChampionIds", [])
                if free_champions:
                    champion_names = []
                    for champ_id in free_champions[:10]:  # Limit to 10 to avoid embed limits
                        name = self._get_champion_name_by_id(champ_id, champion_data)
                        champion_names.append(f"• {name}")
                    
                    if len(free_champions) > 10:
                        champion_names.append(f"... and {len(free_champions) - 10} more")
                    
                    embed.add_field(
                        name=f"🆓 Free Champions ({len(free_champions)} total)",
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
                        new_player_names.append(f"• {name}")
                    
                    embed.add_field(
                        name=f"🆕 New Player Champions (Level 1-{max_level})",
                        value="\n".join(new_player_names) or f"{len(new_player_champions)} champions available",
                        inline=False
                    )
                
                embed.set_footer(text=f"Rotations update weekly")
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error getting rotations: {e}")
                await ctx.send(f"❌ Error getting rotations: {str(e)}")

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(name="matches", aliases=["match"])
    async def matches(self, ctx, region: str = None, *, summoner_name: str):
        """Show recent match history for a summoner"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Get recent matches
                matches = await self.api_manager.get_recent_matches(
                    summoner_data, region, count=5
                )
                
                if not matches:
                    await ctx.send("❌ No recent matches found.")
                    return
                
                embed = discord.Embed(
                    title=f"📜 Recent Matches - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=0xFF6B35,
                    timestamp=datetime.now()
                )
                
                for i, match in enumerate(matches, 1):
                    # Create match embed for each match
                    match_embed = self.embed_factory.create_match_embed(
                        summoner_data, match['details'], match['participant']
                    )
                    
                    # Add as a field to the main embed
                    result = "🏆 Victory" if match['participant']['win'] else "❌ Defeat"
                    champion = match['participant']['championName']
                    kda = f"{match['participant']['kills']}/{match['participant']['deaths']}/{match['participant']['assists']}"
                    duration = self.embed_factory._format_duration(match['details']['info']['gameDuration'])
                    
                    match_info = f"{result}\n**{champion}** - {kda}\n{duration}"
                    embed.add_field(name=f"Match {i}", value=match_info, inline=True)
                
                embed.set_footer(text=f"Recent matches in {region.upper()}")
                await ctx.send(embed=embed)
                
                # Save lookup history
                await self.db_manager.save_lookup_history(
                    ctx.author.id, ctx.guild.id if ctx.guild else None, summoner_name, region
                )
                
            except Exception as e:
                logger.error(f"Error getting match history: {e}")
                await ctx.send(f"❌ Error getting match history: {str(e)}")

    @commands.cooldown(1, 20, commands.BucketType.user)
    @commands.command(name="live", aliases=["spectate", "current"])
    async def live_game(self, ctx, region: str = None, *, summoner_name: str):
        """Check if a summoner is currently in a live game"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Check for active game
                game_data = await self.api_manager.get_live_game(region, summoner_data["puuid"])
                
                # Create and send embed
                embed = self.embed_factory.create_live_game_embed(summoner_data, game_data, region)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error checking live game: {e}")
                await ctx.send(f"❌ Error checking live game: {str(e)}")

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.command(name="rank", aliases=["ranks", "tier"])
    async def rank(self, ctx, region: str = None, *, summoner_name: str):
        """Show detailed rank information for a summoner"""
        async with ctx.typing():
            try:
                # Determine region
                region = region or await self.config.guild(ctx.guild).default_region()
                region = self.api_manager.normalize_region(region)
                
                # Get summoner data
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Get rank data
                rank_data = await self.api_manager.get_rank_info(region, summoner_data["id"])
                
                embed = discord.Embed(
                    title=f"🏆 Ranked Info - {summoner_data['gameName']}#{summoner_data['tagLine']}",
                    color=self.embed_factory.get_rank_color(rank_data),
                    timestamp=datetime.now()
                )
                
                if rank_data:
                    for rank in rank_data:
                        queue_type = rank["queueType"].replace("_", " ").title()
                        tier = rank.get("tier", "Unranked").upper()
                        division = rank.get("rank", "")
                        lp = rank.get("leaguePoints", 0)
                        wins = rank.get("wins", 0)
                        losses = rank.get("losses", 0)
                        
                        if tier != "UNRANKED":
                            total_games = wins + losses
                            winrate = round((wins / total_games) * 100, 1) if total_games > 0 else 0
                            
                            # Enhanced rank display
                            rank_emoji = self.embed_factory.get_rank_emoji(tier)
                            
                            rank_info = (
                                f"{rank_emoji} **{tier.title()} {division}** ({lp} LP)\n"
                                f"📊 {wins}W / {losses}L ({winrate}%)\n"
                                f"🎮 Total Games: {total_games}"
                            )
                            
                            # Add additional status indicators
                            status_indicators = []
                            if rank.get("hotStreak"):
                                status_indicators.append("🔥 Hot Streak")
                            if rank.get("veteran"):
                                status_indicators.append("⭐ Veteran")
                            if rank.get("freshBlood"):
                                status_indicators.append("🩸 Fresh Blood")
                            if rank.get("inactive"):
                                status_indicators.append("💤 Inactive")
                            
                            if status_indicators:
                                rank_info += "\n" + " • ".join(status_indicators)
                            
                        else:
                            rank_info = "❓ Unranked"
                        
                        embed.add_field(name=queue_type, value=rank_info, inline=True)
                else:
                    embed.add_field(name="📊 Ranked Status", value="❓ Unranked in all queues", inline=False)
                
                # Add summoner level
                embed.add_field(name="📈 Summoner Level", value=summoner_data.get("summonerLevel", "N/A"), inline=True)
                embed.add_field(name="🌍 Region", value=region.upper(), inline=True)
                
                # Save lookup history
                await self.db_manager.save_lookup_history(
                    ctx.author.id, ctx.guild.id if ctx.guild else None, summoner_name, region
                )
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error getting rank info: {e}")
                await ctx.send(f"❌ Error getting rank info: {str(e)}")

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(name="champion", aliases=["champ"])  # Removed "info" alias
    async def champion_info(self, ctx, *, champion_name: str):
        """Get detailed information about a champion"""
        async with ctx.typing():
            try:
                champion_data = await self.api_manager.get_champion_data_detailed()
                champion = self._find_champion_by_name(champion_name, champion_data)
                
                if not champion:
                    # Try to suggest similar champions
                    suggestions = self._find_similar_champions(champion_name, champion_data)
                    if suggestions:
                        suggestion_text = ", ".join(suggestions[:3])
                        await ctx.send(f"❌ Champion '{champion_name}' not found. Did you mean: {suggestion_text}?")
                    else:
                        await ctx.send(f"❌ Champion '{champion_name}' not found. Please check the spelling.")
                    return
                
                embed = self.embed_factory.create_champion_embed(champion)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error getting champion information: {e}")
                await ctx.send(f"❌ Error getting champion information: {str(e)}")

    @commands.command(name="history")
    async def lookup_history(self, ctx):
        """Show your recent summoner lookups"""
        try:
            history = await self.db_manager.get_user_lookup_history(ctx.author.id, limit=10)
            
            if not history:
                await ctx.send("📭 You haven't looked up any summoners yet.")
                return
            
            embed = discord.Embed(
                title="📜 Your Recent Lookups",
                color=0x9932CC,
                timestamp=datetime.now()
            )
            
            for i, entry in enumerate(history, 1):
                looked_up = datetime.fromisoformat(entry['looked_up_at'])
                time_ago = humanize_timedelta(timedelta=datetime.now() - looked_up)
                
                embed.add_field(
                    name=f"{i}. {entry['summoner_name']}",
                    value=f"🌍 Region: {entry['region'].upper()}\n⏰ {time_ago} ago",
                    inline=True
                )
            
            embed.set_footer(text="Your lookup history")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting lookup history: {e}")
            await ctx.send(f"❌ Error getting lookup history: {str(e)}")

    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.command(name="build", aliases=["builds", "items"])
    async def champion_build(self, ctx, *, champion_name: str):
        """Get recommended builds and items for a champion"""
        async with ctx.typing():
            try:
                # Get champion data first
                champion_data = await self.api_manager.get_champion_data_detailed()
                champion = self._find_champion_by_name(champion_name, champion_data)
                
                if not champion:
                    # Try to suggest similar champions
                    suggestions = self._find_similar_champions(champion_name, champion_data)
                    if suggestions:
                        suggestion_text = ", ".join(suggestions[:3])
                        await ctx.send(f"❌ Champion '{champion_name}' not found. Did you mean: {suggestion_text}?")
                    else:
                        await ctx.send(f"❌ Champion '{champion_name}' not found. Please check the spelling.")
                    return
                
                # Get build recommendations
                build_data = await self.api_manager.get_champion_build_data(champion['id'])
                
                if not build_data:
                    await ctx.send(f"❌ Build data not available for {champion['name']}.")
                    return
                
                embed = self.embed_factory.create_build_embed(champion, build_data)
                await ctx.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error getting champion build: {e}")
                await ctx.send(f"❌ Error getting champion build: {str(e)}")
    
    @commands.command(name="monitored")
    async def list_monitored(self, ctx):
        """List all summoners being monitored in this server"""
        try:
            monitored = await self.notification_manager.get_monitored_summoners_for_guild(ctx.guild.id)
            
            if not monitored:
                await ctx.send("📭 No summoners are currently being monitored in this server.")
                return
            
            embed = discord.Embed(
                title="📋 Monitored Summoners",
                color=0x0099E1,
                timestamp=datetime.now()
            )
            
            monitored_text = []
            for entry in monitored:
                status = entry["status"]
                summoner = entry["summoner"]
                monitored_text.append(
                    f"{status} **{summoner['gameName']}#{summoner['tagLine']}** "
                    f"({summoner['region'].upper()})"
                )
            
            embed.description = "\n".join(monitored_text)
            embed.set_footer(text=f"{len(monitored)} summoners monitored")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing monitored summoners: {e}")
            await ctx.send(f"❌ Error listing monitored summoners: {str(e)}")

    # Linked account commands
    @commands.command(name="me")
    async def my_profile(self, ctx):
        """Show your linked League of Legends profile with a beautiful card"""
        try:
            linked_account = await self.config.user(ctx.author).linked_account()
            
            if not linked_account:
                await ctx.send(
                    "🔗 You haven't linked a League of Legends account yet.\n"
                    f"Use `{ctx.prefix}lol link <region> <summoner#tag>` to link one."
                )
                return
            
            async with ctx.typing():
                # Get summoner data
                region = linked_account["region"]
                summoner_name = linked_account["summoner_name"]
                summoner_data = await self.api_manager.get_summoner_by_name(region, summoner_name)
                
                # Get rank data
                rank_data = await self.api_manager.get_rank_info(region, summoner_data["id"])
                
                # Get champion mastery data
                mastery_data = await self.api_manager.get_champion_mastery(region, summoner_data["puuid"], count=3)
                
                # Get champion data
                champion_data = await self.api_manager.get_champion_data()
                
                # Add champion names and icon IDs to mastery data
                for mastery in mastery_data:
                    champion_id = mastery["championId"]
                    for champ_key, champ_info in champion_data.get("data", {}).items():
                        if int(champ_info["key"]) == champion_id:
                            mastery["championName"] = champ_info["name"]
                            mastery["championIconId"] = champ_info["id"]
                            break
                
                # Get recent match analysis
                match_analysis = await self.api_manager.analyze_recent_matches(summoner_data, region, count=20)
                
                # Find champion IDs for most played champions
                if match_analysis and "most_played" in match_analysis:
                    for i, (champ_name, stats) in enumerate(match_analysis["most_played"]):
                        for champ_key, champ_info in champion_data.get("data", {}).items():
                            if champ_info["name"] == champ_name:
                                match_analysis["most_played"][i] = [champ_name, stats, int(champ_info["key"])]
                                break
                
                # First send fallback embed for platforms that don't support React
                embed = self.embed_factory.create_me_profile_embed(
                    summoner_data, rank_data, mastery_data, match_analysis, region
                )
                
                # Send the embed first as a fallback
                await ctx.send(embed=embed)
                
                # Try to send the React component for enhanced display
                try:
                    # Prepare the React component content with proper indentation
                    react_content = """import { useState, useEffect } from 'react';

export default function LoLProfile() {
    // Load the data from the API response
    const summonerData = %s;
    const rankData = %s;
    const masteryData = %s;
    const matchAnalysis = %s;
    const region = "%s";
    
    const getChampionIconUrl = (championId) => {
        return `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/${championId}.png`;
    };

    const getProfileIconUrl = (iconId) => {
        return `https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/${iconId}.jpg`;
    };

    const getRankEmblemUrl = (tier) => {
        const tierLower = tier.toLowerCase();
        return `https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem-${tierLower}.png`;
    };

    const getMasteryIconUrl = (level) => {
        return `https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-profiles/global/default/images/champion-mastery/mastery-icon-${level}.png`;
    };

    // Determine color for win rates
    const getWinRateColor = (winrate) => {
        if (winrate >= 60) return "text-green-500";
        if (winrate >= 50) return "text-yellow-400";
        return "text-red-500";
    };

    // Format numbers with commas
    const formatNumber = (num) => {
        return num.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, ",");
    };

    return (
        <div className="flex flex-col p-6 bg-gray-900 rounded-lg text-white max-w-md shadow-lg mx-auto">
            {/* Header Section - Profile Info */}
            <div className="flex items-center mb-6">
                <div className="relative mr-4">
                    <img 
                        src={getProfileIconUrl(summonerData.profileIconId)} 
                        alt="Profile Icon" 
                        className="w-16 h-16 rounded-full border-2 border-yellow-500"
                    />
                    <div className="absolute -bottom-1 -right-1 bg-gray-800 text-xs font-bold px-1 rounded-md border border-yellow-500">
                        {summonerData.summonerLevel}
                    </div>
                </div>
                <div>
                    <h2 className="text-xl font-bold text-yellow-400">{summonerData.gameName}<span className="text-gray-400">#{summonerData.tagLine}</span></h2>
                    <p className="text-gray-400">{region.toUpperCase()} Region</p>
                </div>
            </div>

            {/* Ranked Section */}
            <div className="grid grid-cols-2 gap-4 mb-6">
                {rankData.length > 0 ? (
                    rankData.slice(0, 2).map((rank, i) => (
                        <div key={i} className="bg-gray-800 p-3 rounded-lg flex flex-col">
                            <div className="flex items-center mb-2">
                                {rank.tier && rank.tier !== "UNRANKED" ? (
                                    <img 
                                        src={getRankEmblemUrl(rank.tier)} 
                                        alt={rank.tier} 
                                        className="w-10 h-10 mr-2"
                                    />
                                ) : (
                                    <div className="w-10 h-10 mr-2 bg-gray-700 rounded-full flex items-center justify-center">?</div>
                                )}
                                <div>
                                    <p className="text-xs text-gray-400">{rank.queueType.replace('RANKED_', '').replace('_', ' ')}</p>
                                    {rank.tier && rank.tier !== "UNRANKED" ? (
                                        <p className="font-bold">{rank.tier.charAt(0) + rank.tier.slice(1).toLowerCase()} {rank.rank}</p>
                                    ) : (
                                        <p className="font-bold">Unranked</p>
                                    )}
                                </div>
                            </div>
                            
                            {rank.tier && rank.tier !== "UNRANKED" && (
                                <div className="text-sm mt-1">
                                    <div className="flex justify-between mb-1">
                                        <span>LP:</span>
                                        <span className="font-bold text-blue-400">{rank.leaguePoints}</span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                        <span>W/L:</span>
                                        <span>
                                            <span className="text-green-500">{rank.wins}W</span> / <span className="text-red-500">{rank.losses}L</span>
                                        </span>
                                    </div>
                                    
                                    <div className="flex justify-between">
                                        <span>Win Rate:</span>
                                        <span className={getWinRateColor(Math.round((rank.wins / (rank.wins + rank.losses)) * 100))}>
                                            {Math.round((rank.wins / (rank.wins + rank.losses)) * 100)}%
                                        </span>
                                    </div>
                                    
                                    {rank.hotStreak && (
                                        <div className="text-yellow-400 text-xs mt-2 flex items-center">
                                            <span className="mr-1">🔥</span> Hot Streak!
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    <div className="bg-gray-800 p-3 rounded-lg col-span-2">
                        <p className="text-center">No ranked data available</p>
                    </div>
                )}
            </div>

            {/* Champion Mastery Section */}
            <div className="bg-gray-800 p-4 rounded-lg mb-6">
                <h3 className="font-bold mb-3 text-blue-400 flex items-center">
                    <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
                    </svg>
                    Top Champions
                </h3>
                <div className="grid grid-cols-3 gap-4">
                    {masteryData.length > 0 ? (
                        masteryData.map((mastery, i) => (
                            <div key={i} className="flex flex-col items-center">
                                <div className="relative mb-1">
                                    <img 
                                        src={getChampionIconUrl(mastery.championId)} 
                                        alt={mastery.championName || `Champion ${mastery.championId}`}
                                        className="w-14 h-14 rounded-full border-2 border-blue-500"
                                    />
                                    <div className="absolute -bottom-1 -right-1 bg-blue-600 rounded-full w-6 h-6 flex items-center justify-center border border-white">
                                        {mastery.championLevel}
                                    </div>
                                </div>
                                <p className="font-bold text-sm truncate w-full text-center">{mastery.championName || `Champion ${mastery.championId}`}</p>
                                <p className="text-xs text-gray-400">{formatNumber(mastery.championPoints)} pts</p>
                            </div>
                        ))
                    ) : (
                        <div className="col-span-3 text-center">
                            <p>No mastery data available</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Performance Section */}
            {matchAnalysis ? (
                <div className="bg-gray-800 p-4 rounded-lg">
                    <h3 className="font-bold mb-3 text-green-400 flex items-center">
                        <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z" />
                        </svg>
                        Recent Performance
                    </h3>
                    
                    <div className="grid grid-cols-2 gap-4 mb-3">
                        <div className="bg-gray-700 p-2 rounded-lg text-center">
                            <p className="text-xs text-gray-400 mb-1">Win Rate</p>
                            <p className={`text-lg font-bold ${getWinRateColor(matchAnalysis.winrate)}`}>
                                {matchAnalysis.winrate.toFixed(1)}%
                            </p>
                            <p className="text-xs">
                                <span className="text-green-500">{matchAnalysis.wins}W</span> / <span className="text-red-500">{matchAnalysis.losses}L</span>
                            </p>
                        </div>
                        
                        <div className="bg-gray-700 p-2 rounded-lg text-center">
                            <p className="text-xs text-gray-400 mb-1">KDA Ratio</p>
                            <p className="text-lg font-bold text-blue-400">{matchAnalysis.avg_kda.toFixed(2)}</p>
                            <p className="text-xs">{matchAnalysis.avg_kills.toFixed(1)} / {matchAnalysis.avg_deaths.toFixed(1)} / {matchAnalysis.avg_assists.toFixed(1)}</p>
                        </div>
                    </div>
                    
                    {matchAnalysis.most_played && matchAnalysis.most_played.length > 0 && (
                        <div className="text-sm">
                            <p className="mb-2 text-gray-400">Most Played:</p>
                            <div className="grid grid-cols-3 gap-2">
                                {matchAnalysis.most_played.slice(0, 3).map((champData, i) => {
                                    const champName = champData[0];
                                    const stats = champData[1];
                                    const champId = champData[2];
                                    const winRate = Math.round((stats.wins / stats.games) * 100);
                                    
                                    return (
                                        <div key={i} className="bg-gray-700 p-2 rounded-lg flex flex-col items-center">
                                            <img 
                                                src={getChampionIconUrl(champId)} 
                                                alt={champName} 
                                                className="w-8 h-8 rounded-full mb-1"
                                            />
                                            <p className="text-xs font-bold truncate w-full text-center">{champName}</p>
                                            <p className={`text-xs ${getWinRateColor(winRate)}`}>
                                                {winRate}% ({stats.games} games)
                                            </p>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            ) : (
                <div className="bg-gray-800 p-4 rounded-lg text-center">
                    <p>No recent match data available</p>
                </div>
            )}
            
            <div className="mt-4 text-xs text-center text-gray-500">
                {matchAnalysis ? `Data from last ${matchAnalysis.total_games} games` : "No match data available"} • Updated {new Date().toLocaleString()}
            </div>
        </div>
    );
}"""

                    # Format the data for secure insertion into the template
                    formatted_content = react_content % (
                        json.dumps(summoner_data),
                        json.dumps(rank_data),
                        json.dumps(mastery_data),
                        json.dumps(match_analysis),
                        region
                    )
                    
                    # Create the React component
                    await ctx.invoke(self.bot.get_command("artifacts create"), 
                        id="lol-profile",
                        type="application/vnd.ant.react",
                        title=f"{summoner_data['gameName']}#{summoner_data['tagLine']} Profile",
                        content=formatted_content
                    )
                    
                    # Let the user know a more detailed profile view is available
                    await ctx.send("✨ A more detailed profile view has been created with official League icons!")
                    
                except Exception as e:
                    logger.debug(f"Could not create React profile: {str(e)}")
                    # Don't report to user since they already have the embed
                    pass
                
        except Exception as e:
            logger.error(f"Error getting linked profile: {str(e)}")
            await ctx.send(f"❌ Error getting linked profile: {str(e)}")

    @commands.command(name="mymastery", aliases=["mymasteries"])
    async def my_mastery(self, ctx):
        """Show your linked account's champion mastery"""
        try:
            linked_account = await self.config.user(ctx.author).linked_account()
            
            if not linked_account:
                await ctx.send(
                    "🔗 You haven't linked a League of Legends account yet.\n"
                    f"Use `{ctx.prefix}lol link <region> <summoner#tag>` to link one."
                )
                return
            
            # Get mastery data for the linked account
            await self.mastery(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])
            
        except Exception as e:
            logger.error(f"Error getting linked mastery: {e}")
            await ctx.send(f"❌ Error getting linked mastery: {str(e)}")

    @commands.command(name="mymatches", aliases=["myhistory"])
    async def my_matches(self, ctx):
        """Show your linked account's match history"""
        try:
            linked_account = await self.config.user(ctx.author).linked_account()
            
            if not linked_account:
                await ctx.send(
                    "🔗 You haven't linked a League of Legends account yet.\n"
                    f"Use `{ctx.prefix}lol link <region> <summoner#tag>` to link one."
                )
                return
            
            # Get match history for the linked account
            await self.matches(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])
            
        except Exception as e:
            logger.error(f"Error getting linked matches: {e}")
            await ctx.send(f"❌ Error getting linked matches: {str(e)}")

    # Owner-only commands
    @commands.command(name="usage", aliases=["stats"])
    @checks.is_owner()
    async def show_usage_statistics(self, ctx):
        """Show cog usage statistics (Owner only)"""
        try:
            # Get cache statistics
            cache_stats = await self.api_manager.get_cache_stats()
            
            # Get database statistics
            db_stats = await self.db_manager.get_database_stats()
            
            # Get API statistics
            api_stats = await self.db_manager.get_api_statistics(days=7)
            
            embed = discord.Embed(
                title="📊 LoL Cog Statistics",
                color=0x0099E1,
                timestamp=datetime.now()
            )
            
            # Cache performance
            general_cache = cache_stats['general_cache']
            champion_cache = cache_stats['champion_cache']
            
            embed.add_field(
                name="💾 Cache Performance",
                value=f"**General Cache:**\n"
                      f"Size: {general_cache['size']} items\n"
                      f"Hit Rate: {general_cache['hit_rate']}\n"
                      f"**Champion Cache:**\n"
                      f"Size: {champion_cache['size']} items\n"
                      f"Hit Rate: {champion_cache['hit_rate']}",
                inline=True
            )
            
            # Database statistics
            embed.add_field(
                name="🗃️ Database Statistics",
                value=f"**Size:** {db_stats['db_size_mb']} MB\n"
                      f"**Monitored:** {db_stats['monitored_summoners_count']}\n"
                      f"**Lookups:** {db_stats['lookup_history_count']}\n"
                      f"**Cached Matches:** {db_stats['match_cache_count']}",
                inline=True
            )
            
            # Rate limit status
            rate_status = await self.api_manager.get_rate_limit_status()
            if rate_status:
                status_text = "\n".join([f"**{endpoint.title()}:** {usage}" for endpoint, usage in rate_status.items()])
                embed.add_field(
                    name="🚦 Rate Limit Status",
                    value=status_text,
                    inline=False
                )
            
            # Recent API usage
            if api_stats:
                total_calls = sum(stat['total_calls'] for stat in api_stats[:5])
                total_errors = sum(stat['total_errors'] for stat in api_stats[:5])
                embed.add_field(
                    name="📈 Last 7 Days",
                    value=f"**Total API Calls:** {total_calls:,}\n"
                          f"**Total Errors:** {total_errors:,}\n"
                          f"**Success Rate:** {((total_calls - total_errors) / max(total_calls, 1) * 100):.1f}%",
                    inline=True
                )
            
            embed.set_footer(text="Statistics updated")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting usage statistics: {e}")
            await ctx.send(f"❌ Error getting usage statistics: {str(e)}")

    # Helper methods
    def _get_champion_name_by_id(self, champion_id: int, champion_data: dict) -> str:
        """Get champion name by ID"""
        for champ_name, champ_info in champion_data.get("data", {}).items():
            if int(champ_info["key"]) == champion_id:
                return champ_info["name"]
        return f"Champion {champion_id}"

    def _find_champion_by_name(self, champion_name: str, champion_data: dict) -> Optional[dict]:
        """Find champion by name (fuzzy matching)"""
        champion_name = champion_name.lower().replace(" ", "").replace("'", "")
        
        for champ_key, champ_info in champion_data.get("data", {}).items():
            # Check exact match
            if champ_key.lower() == champion_name:
                return champ_info
            
            # Check display name
            if champ_info["name"].lower().replace(" ", "").replace("'", "") == champion_name:
                return champ_info
        
        return None

    def _find_similar_champions(self, champion_name: str, champion_data: dict) -> list:
        """Find champions with similar names for suggestions"""
        import difflib
        
        champion_names = [champ_info["name"] for champ_info in champion_data.get("data", {}).values()]
        # Get close matches using difflib
        close_matches = difflib.get_close_matches(champion_name, champion_names, n=3, cutoff=0.6)
        return close_matches
