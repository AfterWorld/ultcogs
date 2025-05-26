"""
League Client API (LCU) Integration

Provides direct integration with the local League of Legends client
for real-time monitoring, auto-accept, and champion select features.
"""

import asyncio
import aiohttp
import websockets
import json
import ssl
import base64
import time
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
import psutil
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class LCUCredentials:
    """LCU connection credentials"""
    port: str
    password: str
    protocol: str = "https"
    host: str = "127.0.0.1"


@dataclass
class CurrentSummoner:
    """Current logged-in summoner information"""
    account_id: str
    display_name: str
    internal_name: str
    profile_icon_id: int
    puuid: str
    summoner_id: str
    summoner_level: int
    xp_since_last_level: int
    xp_until_next_level: int


@dataclass
class ChampionSelectState:
    """Champion select session state"""
    actions: List[Dict]
    allow_battle_boost: bool
    allow_duplicate_picks: bool
    allow_locked_events: bool
    allow_rerolling: bool
    allow_skin_selection: bool
    bans: List[Dict]
    bench_champions: List[Dict]
    bench_enabled: bool
    boosts_available: bool
    chat_details: Dict
    counter: int
    entry_type: str
    game_id: int
    has_simultaneous_bans: bool
    has_simultaneous_picks: bool
    is_custom_game: bool
    is_spectating: bool
    local_player_cell_id: int
    locked_event_index: int
    my_team: List[Dict]
    phase_time_remaining: int
    pick_order_swaps: List[Dict]
    recovery_counter: int
    reroll_points: Dict
    skip_champion_select: bool
    their_team: List[Dict]
    timer: Dict
    trades: List[Dict]


class LCUEventHandler:
    """Handles LCU WebSocket events"""
    
    def __init__(self):
        self.event_handlers = {}
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler for specific event types"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def handle_event(self, event_data: Dict):
        """Process incoming LCU events"""
        try:
            if len(event_data) >= 3 and event_data[2]:
                event_type = event_data[2].get('eventType')
                uri = event_data[2].get('uri', '')
                data = event_data[2].get('data')
                
                # Determine specific event category
                if 'ready-check' in uri:
                    await self._handle_ready_check_event(event_type, data)
                elif 'champ-select' in uri:
                    await self._handle_champion_select_event(event_type, data, uri)
                elif 'matchmaking' in uri:
                    await self._handle_matchmaking_event(event_type, data, uri)
                elif 'gameflow' in uri:
                    await self._handle_gameflow_event(event_type, data)
                
                # Call registered handlers
                for handler in self.event_handlers.get(event_type, []):
                    await handler(event_data)
                    
        except Exception as e:
            logger.error(f"Error handling LCU event: {e}")
    
    async def _handle_ready_check_event(self, event_type: str, data: Any):
        """Handle ready check events"""
        if event_type == 'Create' and data:
            logger.info("Ready check detected")
            # Trigger auto-accept if enabled
    
    async def _handle_champion_select_event(self, event_type: str, data: Any, uri: str):
        """Handle champion select events"""
        if '/session' in uri:
            logger.info(f"Champion select state changed: {event_type}")
    
    async def _handle_matchmaking_event(self, event_type: str, data: Any, uri: str):
        """Handle matchmaking events"""
        logger.info(f"Matchmaking event: {event_type} - {uri}")
    
    async def _handle_gameflow_event(self, event_type: str, data: Any):
        """Handle game flow events"""
        if data and 'phase' in str(data):
            logger.info(f"Game flow phase changed: {data}")


class LCUClient:
    """Main LCU client for League of Legends integration"""
    
    def __init__(self):
        self.connected = False
        self.credentials: Optional[LCUCredentials] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.event_handler = LCUEventHandler()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Auto-features state
        self.auto_accept_enabled = False
        self.auto_accept_users = set()
        
    async def connect(self) -> bool:
        """
        Connect to the local League Client
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Get LCU credentials
            self.credentials = await self._discover_lcu_credentials()
            if not self.credentials:
                logger.warning("League Client not found or not running")
                return False
            
            # Create SSL context for self-signed certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create authenticated session
            auth_string = f"riot:{self.credentials.password}"
            auth_header = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {auth_header}"}
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=10)
            )
            
            # Test connection with current summoner endpoint
            success = await self._test_connection()
            if success:
                self.connected = True
                logger.info("Successfully connected to League Client")
                
                # Start WebSocket connection
                await self._connect_websocket()
                
                # Start monitoring task
                self.monitoring_task = asyncio.create_task(self._monitor_events())
                
                self.reconnect_attempts = 0
                return True
            else:
                await self._cleanup_session()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to LCU: {e}")
            await self._cleanup_session()
            return False
    
    async def disconnect(self):
        """Disconnect from League Client"""
        self.connected = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        await self._cleanup_session()
        logger.info("Disconnected from League Client")
    
    async def _discover_lcu_credentials(self) -> Optional[LCUCredentials]:
        """
        Discover LCU credentials from running League Client process
        
        Returns:
            LCUCredentials or None if not found
        """
        try:
            # Look for League Client processes
            target_processes = [
                'LeagueClient.exe',
                'LeagueClient',
                'LeagueClientUx.exe',
                'LeagueClientUx'
            ]
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if not proc.info['name']:
                        continue
                        
                    if any(target in proc.info['name'] for target in target_processes):
                        cmdline = proc.info.get('cmdline', [])
                        if not cmdline:
                            continue
                        
                        # Extract credentials from command line arguments
                        port = None
                        auth_token = None
                        
                        for arg in cmdline:
                            if '--app-port=' in str(arg):
                                port = str(arg).split('=')[1]
                            elif '--remoting-auth-token=' in str(arg):
                                auth_token = str(arg).split('=')[1]
                        
                        if port and auth_token:
                            return LCUCredentials(port=port, password=auth_token)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Alternative method: check lockfile
            return await self._read_lockfile()
            
        except Exception as e:
            logger.error(f"Error discovering LCU credentials: {e}")
            return None
    
    async def _read_lockfile(self) -> Optional[LCUCredentials]:
        """Read credentials from League Client lockfile"""
        try:
            # Common lockfile locations
            possible_paths = [
                os.path.expanduser("~/Riot Games/League of Legends/lockfile"),
                "C:/Riot Games/League of Legends/lockfile",
                "/Applications/League of Legends.app/Contents/LoL/lockfile"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read().strip()
                        parts = content.split(':')
                        if len(parts) >= 5:
                            return LCUCredentials(
                                port=parts[2],
                                password=parts[3]
                            )
        except Exception as e:
            logger.error(f"Error reading lockfile: {e}")
        
        return None
    
    async def _test_connection(self) -> bool:
        """Test LCU connection"""
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-summoner/v1/current-summoner"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def _connect_websocket(self):
        """Connect to LCU WebSocket for real-time events"""
        try:
            if not self.credentials:
                return
            
            uri = f"wss://{self.credentials.host}:{self.credentials.port}/"
            
            # WebSocket headers
            auth_string = f"riot:{self.credentials.password}"
            auth_header = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {auth_header}"}
            
            # SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            self.websocket = await websockets.connect(
                uri,
                extra_headers=headers,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Subscribe to all events
            await self.websocket.send(json.dumps([5, "OnJsonApiEvent"]))
            
            logger.info("WebSocket connected successfully")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.websocket = None
    
    async def _monitor_events(self):
        """Monitor WebSocket events from LCU"""
        while self.connected and self.websocket:
            try:
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=30.0
                )
                
                if message:
                    data = json.loads(message)
                    await self.event_handler.handle_event(data)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                if self.websocket:
                    await self.websocket.ping()
                    
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
                
            except Exception as e:
                logger.error(f"Error in event monitoring: {e}")
                await asyncio.sleep(1)
        
        # Attempt reconnection
        if self.connected and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
            await asyncio.sleep(5)
            await self._connect_websocket()
    
    async def _cleanup_session(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    # API Methods
    
    async def get_current_summoner(self) -> Optional[CurrentSummoner]:
        """Get current logged-in summoner information"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-summoner/v1/current-summoner"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return CurrentSummoner(**data)
                else:
                    logger.error(f"Failed to get current summoner: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting current summoner: {e}")
        
        return None
    
    async def get_champion_select_state(self) -> Optional[ChampionSelectState]:
        """Get current champion select state"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-champ-select/v1/session"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return ChampionSelectState(**data)
                elif response.status == 404:
                    return None  # Not in champion select
                else:
                    logger.error(f"Failed to get champion select state: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting champion select state: {e}")
        
        return None
    
    async def get_gameflow_phase(self) -> Optional[str]:
        """Get current game flow phase"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-gameflow/v1/gameflow-phase"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                    
        except Exception as e:
            logger.error(f"Error getting gameflow phase: {e}")
        
        return None
    
    async def auto_accept_queue(self) -> bool:
        """Automatically accept matchmaking queue"""
        if not self.connected or not self.session:
            return False
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-matchmaking/v1/ready-check/accept"
            async with self.session.post(url) as response:
                success = response.status == 204
                if success:
                    logger.info("Queue auto-accepted successfully")
                else:
                    logger.warning(f"Failed to auto-accept queue: {response.status}")
                return success
                
        except Exception as e:
            logger.error(f"Error auto-accepting queue: {e}")
            return False
    
    async def get_lobby_state(self) -> Optional[Dict]:
        """Get current lobby state"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-lobby/v2/lobby"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None  # Not in lobby
                    
        except Exception as e:
            logger.error(f"Error getting lobby state: {e}")
        
        return None
    
    async def get_friends_list(self) -> Optional[List[Dict]]:
        """Get friends list"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-chat/v1/friends"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error getting friends list: {e}")
        
        return None
    
    async def send_chat_message(self, room_id: str, message: str) -> bool:
        """Send a chat message to specified room"""
        if not self.connected or not self.session:
            return False
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-chat/v1/conversations/{room_id}/messages"
            payload = {
                "body": message,
                "type": "chat"
            }
            async with self.session.post(url, json=payload) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            return False
    
    async def pick_champion(self, action_id: int, champion_id: int) -> bool:
        """Pick a champion in champion select"""
        if not self.connected or not self.session:
            return False
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-champ-select/v1/session/actions/{action_id}"
            payload = {
                "championId": champion_id,
                "completed": True,
                "type": "pick"
            }
            async with self.session.patch(url, json=payload) as response:
                return response.status == 204
                
        except Exception as e:
            logger.error(f"Error picking champion: {e}")
            return False
    
    async def ban_champion(self, action_id: int, champion_id: int) -> bool:
        """Ban a champion in champion select"""
        if not self.connected or not self.session:
            return False
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-champ-select/v1/session/actions/{action_id}"
            payload = {
                "championId": champion_id,
                "completed": True,
                "type": "ban"
            }
            async with self.session.patch(url, json=payload) as response:
                return response.status == 204
                
        except Exception as e:
            logger.error(f"Error banning champion: {e}")
            return False
    
    async def get_owned_champions(self) -> Optional[List[Dict]]:
        """Get list of owned champions"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-champions/v1/owned-champions-minimal"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error getting owned champions: {e}")
        
        return None
    
    async def get_match_history(self, start: int = 0, count: int = 20) -> Optional[Dict]:
        """Get match history for current summoner"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-match-history/v1/products/lol/current-summoner/matches"
            params = {"begIndex": start, "endIndex": start + count}
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error getting match history: {e}")
        
        return None
    
    # Auto-feature management
    
    def enable_auto_accept(self, user_id: str = None):
        """Enable auto-accept feature"""
        self.auto_accept_enabled = True
        if user_id:
            self.auto_accept_users.add(user_id)
        logger.info("Auto-accept enabled")
    
    def disable_auto_accept(self, user_id: str = None):
        """Disable auto-accept feature"""
        if user_id:
            self.auto_accept_users.discard(user_id)
        if not self.auto_accept_users:
            self.auto_accept_enabled = False
        logger.info("Auto-accept disabled")
    
    def is_auto_accept_enabled(self, user_id: str = None) -> bool:
        """Check if auto-accept is enabled"""
        if user_id:
            return user_id in self.auto_accept_users
        return self.auto_accept_enabled
    
    # Utility methods
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        return {
            "connected": self.connected,
            "has_credentials": self.credentials is not None,
            "has_session": self.session is not None,
            "has_websocket": self.websocket is not None,
            "auto_accept_enabled": self.auto_accept_enabled,
            "auto_accept_users": len(self.auto_accept_users),
            "reconnect_attempts": self.reconnect_attempts
        }
