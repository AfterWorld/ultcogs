# lol/commands.py - Additional command implementations
import asyncio
import logging
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
        """Show your linked League of Legends profile"""
        try:
            linked_account = await self.config.user(ctx.author).linked_account()
            
            if not linked_account:
                await ctx.send(
                    "🔗 You haven't linked a League of Legends account yet.\n"
                    f"Use `{ctx.prefix}lol link <region> <summoner#tag>` to link one."
                )
                return
            
            # Get current data for the linked account
            await self.summoner(ctx, linked_account["region"], summoner_name=linked_account["summoner_name"])
            
        except Exception as e:
            logger.error(f"Error getting linked profile: {e}")
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
