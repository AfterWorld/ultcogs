# lol/notifications.py - Notification management
import asyncio
import time
import logging
from typing import Dict, Set
from collections import defaultdict
from datetime import datetime

import discord

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manage live game notifications"""
    
    def __init__(self, cog):
        self.cog = cog
        self.monitored_summoners: Dict[str, Dict] = {}
        self.notification_channels: Dict[int, Set[int]] = defaultdict(set)
        self.check_interval = 300  # 5 minutes
        self.monitor_task = None
        
    def start_monitoring(self):
        """Start the background monitoring task"""
        if self.monitor_task is None or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Started live game monitoring")
    
    def stop_monitoring(self):
        """Stop the background monitoring task"""
        if self.monitor_task:
            self.monitor_task.cancel()
            logger.info("Stopped live game monitoring")
    
    async def add_summoner(self, guild_id: int, channel_id: int, summoner_data: Dict):
        """Add a summoner to monitoring list"""
        key = f"{summoner_data['region']}:{summoner_data['puuid']}"
        
        self.monitored_summoners[key] = {
            **summoner_data,
            "in_game": False,
            "last_checked": time.time(),
            "current_game_id": None
        }
        
        self.notification_channels[guild_id].add(channel_id)
        
        # Save to database
        await self._save_monitored_summoner(guild_id, channel_id, summoner_data)
        logger.info(f"Added {summoner_data['gameName']}#{summoner_data['tagLine']} to monitoring")
    
    async def remove_summoner(self, guild_id: int, summoner_data: Dict):
        """Remove a summoner from monitoring"""
        key = f"{summoner_data['region']}:{summoner_data['puuid']}"
        
        if key in self.monitored_summoners:
            del self.monitored_summoners[key]
        
        # Remove from database
        await self._delete_monitored_summoner(guild_id, summoner_data['puuid'])
        logger.info(f"Removed {summoner_data['gameName']}#{summoner_data['tagLine']} from monitoring")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._check_all_summoners()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _check_all_summoners(self):
        """Check all monitored summoners for game status changes"""
        if not self.monitored_summoners:
            return
            
        logger.debug(f"Checking {len(self.monitored_summoners)} monitored summoners")
        
        for key, summoner_data in list(self.monitored_summoners.items()):
            try:
                await self._check_summoner_status(key, summoner_data)
                await asyncio.sleep(1)  # Small delay between checks
            except Exception as e:
                logger.error(f"Error checking summoner {key}: {e}")
    
    async def _check_summoner_status(self, key: str, summoner_data: Dict):
        """Check if a specific summoner's game status has changed"""
        try:
            game_data = await self._fetch_active_game(summoner_data)
            
            if game_data:
                await self._handle_game_start(summoner_data, game_data)
            else:
                await self._handle_game_end(summoner_data)
                
        except Exception as e:
            logger.error(f"Error checking {summoner_data['gameName']}: {e}")
    
    async def _fetch_active_game(self, summoner_data: Dict) -> Dict:
        """Fetch active game data for a summoner"""
        region = summoner_data['region']
        puuid = summoner_data['puuid']
        
        url = f"https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
        
        try:
            game_data = await self.cog.api_manager.make_request(url)
            return game_data
        except Exception:
            # Summoner is not in game (404 error is expected)
            return None
    
    async def _handle_game_start(self, summoner_data: Dict, game_data: Dict):
        """Handle when a summoner starts a game"""
        current_game_id = game_data.get("gameId")
        
        if not summoner_data["in_game"] or summoner_data["current_game_id"] != current_game_id:
            # Game started or changed
            summoner_data["in_game"] = True
            summoner_data["current_game_id"] = current_game_id
            summoner_data["last_checked"] = time.time()
            
            embed = self.cog.embed_factory.create_notification_embed(
                summoner_data, game_data, game_started=True
            )
            await self._send_to_notification_channels(embed, game_data, summoner_data)
            logger.info(f"{summoner_data['gameName']} started a game")
    
    async def _handle_game_end(self, summoner_data: Dict):
        """Handle when a summoner ends a game"""
        if summoner_data["in_game"]:
            # Game ended
            summoner_data["in_game"] = False
            summoner_data["current_game_id"] = None
            summoner_data["last_checked"] = time.time()
            
            embed = self.cog.embed_factory.create_notification_embed(
                summoner_data, None, game_started=False
            )
            await self._send_to_notification_channels(embed)
            logger.info(f"{summoner_data['gameName']} ended their game")
    
    async def _send_to_notification_channels(self, embed: discord.Embed, game_data=None, summoner_data=None):
        """Send notification with Components V2 where possible"""
        for guild_id, channel_ids in self.notification_channels.items():
            guild = self.cog.bot.get_guild(guild_id)
            if not guild:
                continue
                
            for channel_id in list(channel_ids):
                channel = guild.get_channel(channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        # If we have game data and summoner data and it's a game start notification
                        if game_data and summoner_data and summoner_data.get("in_game", False):
                            # Try Components V2 first
                            success = False
                            try:
                                # Create a Components V2 notification
                                notification_container = {
                                    "type": 17,  # Container type
                                    "components": [
                                        {
                                            "type": 10,  # TextDisplay type
                                            "content": f"# 🎮 Game Started!\n**{summoner_data['gameName']}#{summoner_data['tagLine']}** started a game"
                                        }
                                    ]
                                }
                                
                                # Add game info
                                game_mode = game_data.get("gameMode", "Unknown")
                                queue_id = game_data.get("gameQueueConfigId", 0)
                                queue_type = QUEUE_TYPES.get(queue_id, f"Queue {queue_id}")
                                
                                notification_container["components"].append({
                                    "type": 10,  # TextDisplay type
                                    "content": f"**🎮 Game Mode:** {game_mode}\n**🏆 Queue:** {queue_type}\n**🌍 Region:** {summoner_data['region'].upper()}"
                                })
                                
                                # Find champion being played
                                for participant in game_data.get("participants", []):
                                    if participant.get("puuid") == summoner_data.get("puuid"):
                                        champion_id = participant.get("championId", 0)
                                        champion_name = participant.get("championName", f"Champion {champion_id}")
                                        
                                        # Add champion section
                                        notification_container["components"].append({
                                            "type": 9,  # Section type
                                            "components": [
                                                {
                                                    "type": 10,  # TextDisplay type
                                                    "content": f"**Playing:** {champion_name}"
                                                }
                                            ]
                                        })
                                        
                                        # Add champion icon
                                        icon_url = self.cog.embed_factory.get_custom_champion_icon_url(champion_id)
                                        notification_container["components"].append({
                                            "type": 12,  # Media gallery type
                                            "items": [
                                                {
                                                    "media": {
                                                        "url": icon_url
                                                    }
                                                }
                                            ]
                                        })
                                        
                                        break
                                
                                # Send the Components V2 message
                                payload = {
                                    "flags": 32768,  # IS_COMPONENTS_V2 flag
                                    "components": [notification_container]
                                }
                                
                                await channel.bot.http.request(
                                    discord.http.Route('POST', '/channels/{channel_id}/messages', 
                                                    channel_id=channel.id),
                                    json=payload
                                )
                                success = True
                            except Exception as e:
                                logger.warning(f"Failed to send Components V2 notification: {e}")
                                success = False
                            
                            # If Components V2 failed, fall back to standard embed
                            if not success:
                                await channel.send(embed=embed)
                        else:
                            # For game end notifications or if we don't have enough data, just use the standard embed
                            await channel.send(embed=embed)
                            
                    except (discord.Forbidden, discord.HTTPException) as e:
                        logger.warning(f"Failed to send notification to {channel_id}: {e}")
                        # Remove invalid channels
                        channel_ids.discard(channel_id)
                else:
                    # Remove invalid channels
                    channel_ids.discard(channel_id)
    
    async def get_monitored_summoners_for_guild(self, guild_id: int) -> list:
        """Get all monitored summoners for a specific guild"""
        monitored = []
        
        if guild_id not in self.notification_channels:
            return monitored
        
        for key, summoner_data in self.monitored_summoners.items():
            # Check if this summoner is monitored in this guild
            if guild_id in self.notification_channels:
                status = "🟢 In Game" if summoner_data["in_game"] else "⚫ Offline"
                monitored.append({
                    "status": status,
                    "summoner": summoner_data,
                    "key": key
                })
        
        return monitored
    
    # Database methods for persistence
    async def _save_monitored_summoner(self, guild_id: int, channel_id: int, summoner_data: Dict):
        """Save monitored summoner to database"""
        await self.cog.db_manager.save_monitored_summoner(
            guild_id, channel_id, summoner_data['puuid'], 
            summoner_data['region'], summoner_data['gameName'], 
            summoner_data['tagLine']
        )
    
    async def _delete_monitored_summoner(self, guild_id: int, puuid: str):
        """Remove monitored summoner from database"""
        await self.cog.db_manager.delete_monitored_summoner(guild_id, puuid)
    
    async def load_from_database(self):
        """Load monitored summoners from database on startup"""
        monitored_data = await self.cog.db_manager.get_all_monitored_summoners()
        
        for row in monitored_data:
            guild_id, channel_id, puuid, region, game_name, tag_line = row
            key = f"{region}:{puuid}"
            
            self.monitored_summoners[key] = {
                "puuid": puuid,
                "region": region,
                "gameName": game_name,
                "tagLine": tag_line,
                "in_game": False,
                "last_checked": time.time(),
                "current_game_id": None
            }
            
            self.notification_channels[guild_id].add(channel_id)
        
        logger.info(f"Loaded {len(self.monitored_summoners)} monitored summoners from database")
