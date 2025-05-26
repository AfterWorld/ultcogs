"""
League Client API (LCU) Integration - Fixed Version

Provides direct integration with the local League of Legends client
with graceful handling of missing dependencies.
"""

import asyncio
import json
import ssl
import base64
import time
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass
import logging

# Optional dependencies with graceful fallbacks
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    websockets = None

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

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
    account_id: str = ""
    display_name: str = ""
    internal_name: str = ""
    profile_icon_id: int = 0
    puuid: str = ""
    summoner_id: str = ""
    summoner_level: int = 0
    xp_since_last_level: int = 0
    xp_until_next_level: int = 0


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
    """Main LCU client for League of Legends integration with graceful degradation"""
    
    def __init__(self):
        self.connected = False
        self.credentials: Optional[LCUCredentials] = None
        self.session: Optional[Any] = None  # Will be aiohttp.ClientSession if available
        self.websocket: Optional[Any] = None  # Will be websockets object if available
        self.event_handler = LCUEventHandler()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Auto-features state
        self.auto_accept_enabled = False
        self.auto_accept_users = set()
        
        # Check dependencies on init
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check which dependencies are available"""
        missing_deps = []
        if not HAS_AIOHTTP:
            missing_deps.append("aiohttp")
        if not HAS_WEBSOCKETS:
            missing_deps.append("websockets")
        if not HAS_PSUTIL:
            missing_deps.append("psutil")
        
        if missing_deps:
            logger.warning(f"LCU features limited - missing dependencies: {', '.join(missing_deps)}")
            logger.info("Install with: pip install " + " ".join(missing_deps))
    
    async def connect(self) -> bool:
        """
        Connect to the local League Client
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not HAS_AIOHTTP:
            logger.error("Cannot connect to LCU - aiohttp not installed")
            return False
        
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
                
                # Start WebSocket connection if websockets is available
                if HAS_WEBSOCKETS:
                    await self._connect_websocket()
                    
                    # Start monitoring task
                    self.monitoring_task = asyncio.create_task(self._monitor_events())
                else:
                    logger.warning("WebSocket features disabled - websockets not installed")
                
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
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        
        await self._cleanup_session()
        logger.info("Disconnected from League Client")
    
    async def _discover_lcu_credentials(self) -> Optional[LCUCredentials]:
        """
        Discover LCU credentials from running League Client process
        
        Returns:
            LCUCredentials or None if not found
        """
        if not HAS_PSUTIL:
            logger.warning("Cannot discover LCU credentials - psutil not installed")
            return await self._read_lockfile()
        
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
            
            # Fallback to lockfile method
            return await self._read_lockfile()
            
        except Exception as e:
            logger.error(f"Error discovering LCU credentials: {e}")
            return None
    
    async def _read_lockfile(self) -> Optional[LCUCredentials]:
        """Read credentials from League Client lockfile"""
        import os
        
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
        if not self.session or not self.credentials:
            return False
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-summoner/v1/current-summoner"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def _connect_websocket(self):
        """Connect to LCU WebSocket for real-time events"""
        if not HAS_WEBSOCKETS or not self.credentials:
            return
        
        try:
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
        if not HAS_WEBSOCKETS:
            return
        
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
                    try:
                        await self.websocket.ping()
                    except:
                        break
                    
            except Exception as e:
                if "websockets.exceptions.ConnectionClosed" in str(type(e)):
                    logger.warning("WebSocket connection closed")
                    break
                else:
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
            try:
                await self.session.close()
            except:
                pass
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
                    return CurrentSummoner(
                        account_id=data.get('accountId', ''),
                        display_name=data.get('displayName', ''),
                        internal_name=data.get('internalName', ''),
                        profile_icon_id=data.get('profileIconId', 0),
                        puuid=data.get('puuid', ''),
                        summoner_id=data.get('summonerId', ''),
                        summoner_level=data.get('summonerLevel', 0),
                        xp_since_last_level=data.get('xpSinceLastLevel', 0),
                        xp_until_next_level=data.get('xpUntilNextLevel', 0)
                    )
                else:
                    logger.error(f"Failed to get current summoner: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error getting current summoner: {e}")
        
        return None
    
    async def get_champion_select_state(self) -> Optional[Dict]:
        """Get current champion select state"""
        if not self.connected or not self.session:
            return None
        
        try:
            url = f"https://{self.credentials.host}:{self.credentials.port}/lol-champ-select/v1/session"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
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
                    text = await response.text()
                    return text.strip('"')  # Remove quotes from JSON string
                    
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
    
    # Simplified API methods for basic functionality
    
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
            "reconnect_attempts": self.reconnect_attempts,
            "dependencies": {
                "aiohttp": HAS_AIOHTTP,
                "websockets": HAS_WEBSOCKETS,
                "psutil": HAS_PSUTIL
            }
        }
