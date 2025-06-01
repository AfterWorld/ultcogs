# __init__.py - UPDATED VERSION WITH IMAGE INTEGRATION
"""
Hunger Games Battle Royale Cog for Red-DiscordBot

A comprehensive battle royale game where players fight to be the last survivor.
Features automatic events, sponsor revivals, dynamic rewards, detailed statistics, 
special arena events, and custom round image displays.
"""

import discord
from redbot.core import commands, Config, bank, data_manager
import asyncio
import random
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

from .constants import (
    DEFAULT_GUILD_CONFIG, DEFAULT_MEMBER_CONFIG, EMOJIS,
    DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS,
    VICTORY_PHRASES, VICTORY_SCENARIOS, TITLE_EMOJIS
)

# Update the default config to include custom images toggle
DEFAULT_GUILD_CONFIG["enable_custom_images"] = True
from .game import GameEngine, GameError, InvalidGameStateError
from .utils import *

# Try to import config, but don't fail if it has issues
try:
    from .config import game_config_manager
except ImportError:
    game_config_manager = None

# Try to import GIF system, but don't fail if it has issues
try:
    from .gif_manager import GifManager
    GIF_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"GIF system not available: {e}")
    GIF_SYSTEM_AVAILABLE = False

# Try to import Image system, but don't fail if it has issues
try:
    from .image_handler import ImageRoundHandler
    IMAGE_SYSTEM_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Image system not available: {e}")
    IMAGE_SYSTEM_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class GameTiming:
    """Centralized timing configuration"""
    MIN_FINAL_DUEL_INTERVAL: int = 8
    MIN_ENDGAME_INTERVAL: int = 15
    MIN_EARLY_GAME_INTERVAL: int = 25
    ENDGAME_THRESHOLD: int = 5
    FINAL_DUEL_THRESHOLD: int = 2
    STATUS_UPDATE_INTERVAL: int = 6


class InputValidator:
    """Handles all input validation for the game"""
    
    @staticmethod
    def validate_countdown(countdown: int) -> tuple[bool, str]:
        """Validate countdown parameter"""
        if not isinstance(countdown, int):
            return False, "Countdown must be a number!"
        
        if countdown < 10:
            return False, "Countdown must be at least 10 seconds!"
        
        if countdown > 300:
            return False, "Countdown cannot exceed 5 minutes!"
        
        return True, ""
    
    @staticmethod
    def validate_base_reward(amount: int) -> tuple[bool, str]:
        """Validate base reward amount"""
        if amount < 100:
            return False, "Base reward must be at least 100 credits!"
        return True, ""
    
    @staticmethod
    def validate_sponsor_chance(chance: int) -> tuple[bool, str]:
        """Validate sponsor chance"""
        if not 1 <= chance <= 50:
            return False, "Sponsor chance must be between 1-50%!"
        return True, ""
    
    @staticmethod
    def validate_event_interval(seconds: int) -> tuple[bool, str]:
        """Validate event interval"""
        if not 10 <= seconds <= 120:
            return False, "Event interval must be between 10-120 seconds!"
        return True, ""
    
    @staticmethod
    def validate_game_state(game: Dict) -> bool:
        """Validate game state integrity"""
        try:
            required_keys = ["players", "round", "status", "eliminated"]
            if not all(key in game for key in required_keys):
                return False
            
            if game["round"] < 0:
                return False
            
            if not isinstance(game["players"], dict):
                return False
            
            # Validate player data structure
            for player_id, player_data in game["players"].items():
                if not isinstance(player_data, dict):
                    return False
                
                required_player_keys = ["name", "alive", "kills"]
                if not all(key in player_data for key in required_player_keys):
                    return False
            
            return True
        except Exception:
            return False


class EventHandler:
    """Handles event execution with proper error handling"""
    
    def __init__(self, game_engine):
        self.game_engine = game_engine
        self.handlers = {
            "death": self._handle_death_event,
            "survival": self._handle_survival_event,
            "sponsor": self._handle_sponsor_event,
            "alliance": self._handle_alliance_event,
            "crate": self._handle_crate_event
        }
    
    async def execute_event(self, event_type: str, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        """Execute event using handler mapping with error handling"""
        try:
            handler = self.handlers.get(event_type)
            if not handler:
                logger.warning(f"Unknown event type: {event_type}")
                return None
            
            return await handler(game, channel)
            
        except GameError as e:
            logger.error(f"Game error in {event_type} event: {e}")
            return self._get_fallback_message(event_type)
        except Exception as e:
            logger.error(f"Unexpected error in {event_type} event: {e}", exc_info=True)
            return None
    
    async def _handle_death_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_death_event(game, channel)
    
    async def _handle_survival_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_survival_event(game)
    
    async def _handle_sponsor_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_sponsor_event(game)
    
    async def _handle_alliance_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_alliance_event(game)
    
    async def _handle_crate_event(self, game: Dict, channel: discord.TextChannel) -> Optional[str]:
        return await self.game_engine.execute_crate_event(game)
    
    def _get_fallback_message(self, event_type: str) -> str:
        """Get fallback message for failed events"""
        fallbacks = {
            "death": "💀 | A mysterious death occurred in the arena...",
            "survival": "🌿 | Someone managed to survive another day...",
            "sponsor": "🎁 | A sponsor gift was mysteriously delivered...",
            "alliance": "🤝 | Tributes formed an unexpected alliance...",
            "crate": "📦 | Someone discovered hidden supplies..."
        }
        return fallbacks.get(event_type, "⚡ | Something happened in the arena...")


class HungerGames(commands.Cog):
    """A Hunger Games style battle royale game for Discord"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        
        self.config.register_guild(**DEFAULT_GUILD_CONFIG)
        self.config.register_member(**DEFAULT_MEMBER_CONFIG)
        
        self.active_games: Dict[int, Dict] = {}
        self.game_engine = GameEngine(bot, self.config)
        self.event_handler = EventHandler(self.game_engine)
        self.validator = InputValidator()
        self.timing = GameTiming()
        
        # Add Image Handler integration
        if IMAGE_SYSTEM_AVAILABLE:
            try:
                # Use the specific path structure provided
                image_base_path = "/home/adam/.local/share/Red-DiscordBot/data/sunny/cogs/CogManager/cogs/hg/Images"
                self.image_handler = ImageRoundHandler(self.bot, image_base_path)
                logger.info("Image handler initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize image handler: {e}")
                self.image_handler = None
        else:
            self.image_handler = None
        
        # Add GIF integration if available
        if GIF_SYSTEM_AVAILABLE:
            try:
                # Create GIF directory in bot's data directory
                cog_data_path = data_manager.cog_data_path(self)
                gif_base_path = cog_data_path / "gifs"
                self.gif_manager = GifManager(bot, self.config, str(gif_base_path))
                logger.info("GIF system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GIF system: {e}")
                self.gif_manager = None
        else:
            self.gif_manager = None
        
        # Performance optimization - cache alive players
        self._alive_cache = {}
        self._cache_round = {}
    
    def cog_unload(self):
        """Cancel all running games when cog is unloaded"""
        for guild_id in list(self.active_games.keys()):
            if "task" in self.active_games[guild_id]:
                self.active_games[guild_id]["task"].cancel()
        logger.info("Hunger Games cog unloaded, all games cancelled")
    
    @commands.command(name="he")
    async def hunger_games_event(self, ctx, countdown: int = 60):
        """Start a Hunger Games battle royale! React to join!"""
        guild_id = ctx.guild.id
        
        # Enhanced input validation
        valid, error_msg = self.validator.validate_countdown(countdown)
        if not valid:
            return await ctx.send(f"❌ {error_msg}")
        
        if guild_id in self.active_games:
            return await ctx.send("❌ A Hunger Games battle is already active!")
        
        try:
            # Create the game instance with validation
            await self._initialize_new_game(ctx, countdown)
        except Exception as e:
            logger.error(f"Failed to initialize game in guild {guild_id}: {e}", exc_info=True)
            await ctx.send("❌ Failed to start the game. Please try again.")
    
    async def _initialize_new_game(self, ctx, countdown: int):
        """Initialize a new game with proper error handling"""
        guild_id = ctx.guild.id
        
        self.active_games[guild_id] = {
            "channel": ctx.channel,
            "players": {},
            "status": "recruiting",
            "round": 0,
            "eliminated": [],
            "sponsor_used": [],
            "reactions": set(),
            "milestones_shown": set()
        }
        
        # Send recruitment embed
        embed = create_recruitment_embed(countdown)
        message = await ctx.send(embed=embed)
        await message.add_reaction(EMOJIS["bow"])
        
        self.active_games[guild_id]["message"] = message
        
        # Start recruitment countdown
        await self.recruitment_countdown(guild_id, countdown)
    
    async def recruitment_countdown(self, guild_id: int, countdown: int):
        """Handle the recruitment countdown and reaction monitoring"""
        game = self.active_games[guild_id]
        message = game["message"]
        channel = game["channel"]
        
        end_time = asyncio.get_event_loop().time() + countdown
        
        try:
            while asyncio.get_event_loop().time() < end_time:
                remaining = int(end_time - asyncio.get_event_loop().time())
                
                # Update embed every 10 seconds or at key intervals
                if remaining % 10 == 0 or remaining <= 5:
                    await self._update_recruitment_message(game, message, channel, remaining)
                
                await asyncio.sleep(1)
        except discord.NotFound:
            # Message was deleted, cancel game
            logger.info(f"Recruitment message deleted, cancelling game in guild {guild_id}")
            del self.active_games[guild_id]
            return
        except Exception as e:
            logger.error(f"Error during recruitment countdown: {e}")
        
        # Recruitment ended, start the game
        await self.start_battle_royale(guild_id)
    
    async def _update_recruitment_message(self, game: Dict, message: discord.Message, 
                                        channel: discord.TextChannel, remaining: int):
        """Update recruitment message with current player count"""
        try:
            # Get current reactions
            fresh_message = await channel.fetch_message(message.id)
            bow_reaction = None
            
            for reaction in fresh_message.reactions:
                if str(reaction.emoji) == EMOJIS["bow"]:
                    bow_reaction = reaction
                    break
            
            if bow_reaction:
                # Get users who reacted (excluding bot)
                async for user in bow_reaction.users():
                    if not user.bot and user.id not in game["reactions"]:
                        game["reactions"].add(user.id)
                        game["players"][str(user.id)] = {
                            "name": user.display_name,
                            "title": get_random_player_title(),
                            "alive": True,
                            "kills": 0,
                            "revives": 0,
                            "district": get_random_district()
                        }
            
            # Update embed with current player count
            current_players = len(game["players"])
            embed = create_recruitment_embed(remaining, current_players)
            await message.edit(embed=embed)
            
        except discord.Forbidden:
            logger.warning("Missing permissions to edit recruitment message")
        except Exception as e:
            logger.error(f"Error updating recruitment message: {e}")
    
    async def start_battle_royale(self, guild_id: int):
        """Start the actual battle royale game with validation"""
        try:
            game = self.active_games[guild_id]
            channel = game["channel"]
            
            # Validate game state before starting
            if not self.validator.validate_game_state(game):
                raise InvalidGameStateError("Game state is invalid before start")
            
            # Check if we have enough players
            player_count = len(game["players"])
            if player_count < 2:
                embed = discord.Embed(
                    title="❌ **INSUFFICIENT TRIBUTES**",
                    description="Need at least 2 brave souls to enter the arena!",
                    color=0xFF0000
                )
                await channel.send(embed=embed)
                del self.active_games[guild_id]
                return
            
            game["status"] = "active"
            
            # Send game start messages
            await self._send_game_start_messages(game, player_count)
            
            # Start the main game loop
            game["task"] = asyncio.create_task(self.game_loop(guild_id))
            logger.info(f"Started Hunger Games with {player_count} players in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to start battle royale in guild {guild_id}: {e}", exc_info=True)
            await channel.send("❌ Failed to start the battle royale. Game cancelled.")
            if guild_id in self.active_games:
                del self.active_games[guild_id]
    
    async def _send_game_start_messages(self, game: Dict, player_count: int):
        """Send game start and player introduction messages"""
        channel = game["channel"]
        
        # Game start message
        embed = create_game_start_embed(player_count)
        await channel.send(embed=embed)
        
        await asyncio.sleep(3)
        
        # Show initial tributes
        embed = discord.Embed(
            title="👥 **THE TRIBUTES**",
            description="Meet this year's brave competitors:",
            color=0x4169E1
        )
        
        player_list = format_player_list(game["players"], show_status=False)
        embed.add_field(
            name="🏹 **Entered the Arena**",
            value=player_list,
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # Add extra dramatic pause for small games
        if player_count <= 4:
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="⚡ **INTENSE SHOWDOWN INCOMING** ⚡",
                description=f"With only **{player_count} tributes**, this will be a lightning-fast battle!\n"
                           f"Every second counts... every move matters...",
                color=0xFF6B35
            )
            await channel.send(embed=embed)
    
    async def game_loop(self, guild_id: int):
        """Main game loop - IMPROVED AND MODULAR"""
        game = self.active_games[guild_id]
        channel = game["channel"]
        
        try:
            logger.info(f"Starting game loop for guild {guild_id}")
            
            await self._initialize_game_loop(game)
            
            while game["status"] == "active":
                # Process a single round
                await self._process_game_round(game, channel)
                
                # Check if game should end
                if await self.game_engine.check_game_end(game, channel):
                    break
                
                # Calculate and wait for next round
                sleep_time = self._calculate_sleep_time(game)
                logger.debug(f"Guild {guild_id}: Sleeping for {sleep_time} seconds")
                await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.info(f"Game {guild_id} was cancelled")
        except GameError as e:
            logger.error(f"Game error in guild {guild_id}: {e}")
            await self._handle_game_error(game, channel, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in game loop for guild {guild_id}: {e}", exc_info=True)
            await self._handle_game_error(game, channel, "Technical difficulties")
        finally:
            await self._cleanup_game(guild_id)
    
    async def _initialize_game_loop(self, game: Dict):
        """Initialize game loop settings"""
        event_interval = await self.config.guild(game["channel"].guild).event_interval()
        game["event_interval"] = event_interval
        await asyncio.sleep(3)  # Initial pause
    
    async def _process_game_round(self, game: Dict, channel: discord.TextChannel):
        """Process a single game round with special events"""
        game["round"] += 1
        alive_players = self.game_engine.get_alive_players(game)
        
        logger.debug(f"Round {game['round']}: {len(alive_players)} players alive")
        
        # Validate game state
        if not self.validator.validate_game_state(game):
            raise InvalidGameStateError(f"Game state corrupted in round {game['round']}")
        
        # Check for special events FIRST
        special_event = await self.game_engine.check_special_events(game, channel, alive_players)
        if special_event:
            await self._send_special_event(special_event, channel)
            await asyncio.sleep(2)  # Dramatic pause
        
        # Execute normal events if players remain
        if len(alive_players) > 1:
            await self._execute_round_events(game, channel)
        
        # Send status update periodically
        await self._maybe_send_status_update(game, channel)
    
    async def _send_special_event(self, event_message: str, channel: discord.TextChannel):
        """Send special event with dramatic formatting"""
        
        # Determine event type for color coding
        if "ATTENTION TRIBUTES" in event_message or "GAMEMAKER" in event_message:
            color = 0xFFD700  # Gold for announcements
            title = "📢 **GAMEMAKER ANNOUNCEMENT**"
        elif any(word in event_message for word in ["finale", "final", "lightning", "lava", "tornado", "blizzard"]):
            color = 0xFF0000  # Red for finale
            title = "🔥 **ARENA EVENT**"
        elif "bloodbath" in event_message.lower() or "Cornucopia" in event_message:
            color = 0x8B0000  # Dark red for bloodbath
            title = "⚔️ **THE BLOODBATH**"
        elif any(word in event_message for word in ["cannon", "fog", "tracker jacker", "trap", "muttation", "earthquake", "test"]):
            color = 0xFF4500  # Orange-red for deadly events
            title = "💀 **DEADLY EVENT**"
        else:
            color = 0xFF6B35  # Orange for general drama
            title = "⚡ **ARENA EVENT**"
        
        embed = discord.Embed(
            title=title,
            description=event_message,
            color=color
        )
        
        # Add footer based on event type
        if "feast" in event_message.lower():
            embed.set_footer(text="⚠️ High risk, high reward...")
        elif any(word in event_message for word in ["final", "finale"]):
            embed.set_footer(text="🏆 The end is near...")
        elif any(word in event_message for word in ["cannon", "fog", "trap", "muttation"]):
            embed.set_footer(text="💀 Danger lurks in every shadow...")
        elif "bloodbath" in event_message.lower():
            embed.set_footer(text="⚔️ Let the Games begin...")
        
        await channel.send(embed=embed)
    
    async def _execute_round_events(self, game: Dict, channel: discord.TextChannel):
        """Execute events for the current round"""
        try:
            await self.execute_combined_events(game, channel)
        except Exception as e:
            logger.error(f"Error executing round events: {e}")
            # Send fallback message
            embed = discord.Embed(
                description="⚠️ Something mysterious happened in the arena...",
                color=0xFFFF00
            )
            await channel.send(embed=embed)
    
    async def _maybe_send_status_update(self, game: Dict, channel: discord.TextChannel):
        """Send status update if needed"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        if (game["round"] % self.timing.STATUS_UPDATE_INTERVAL == 0 and 
            alive_count > 8):
            embed = self.game_engine.create_status_embed(game, channel.guild)
            await channel.send(embed=embed)
    
    def _calculate_sleep_time(self, game: Dict) -> int:
        """Calculate appropriate sleep time based on game state"""
        alive_count = len(self.game_engine.get_alive_players(game))
        event_interval = game.get("event_interval", 30)
        
        if alive_count <= self.timing.FINAL_DUEL_THRESHOLD:
            return max(self.timing.MIN_FINAL_DUEL_INTERVAL, event_interval // 3)
        elif alive_count <= 3:
            return max(10, event_interval // 3)
        elif alive_count <= self.timing.ENDGAME_THRESHOLD:
            return max(12, event_interval // 2)
        elif alive_count <= 10:
            return max(self.timing.MIN_ENDGAME_INTERVAL, event_interval // 2)
        else:
            return max(self.timing.MIN_EARLY_GAME_INTERVAL, event_interval)
    
    async def _handle_game_error(self, game: Dict, channel: discord.TextChannel, error_msg: str):
        """Handle game errors gracefully"""
        try:
            embed = discord.Embed(
                title="❌ **ARENA MALFUNCTION**",
                description=f"The arena experienced {error_msg}. Game ended.",
                color=0xFF0000
            )
            await channel.send(embed=embed)
        except Exception:
            logger.error("Failed to send error message to channel")
    
    async def _cleanup_game(self, guild_id: int):
        """Clean up game resources"""
        logger.info(f"Cleaning up game for guild {guild_id}")
        if guild_id in self.active_games:
            del self.active_games[guild_id]
        
        # Clear cache
        self._alive_cache.pop(guild_id, None)
        self._cache_round.pop(guild_id, None)
    
    async def execute_combined_events(self, game: Dict, channel: discord.TextChannel):
        """Execute multiple events in one round - RUMBLE STYLE WITH IMPROVED ERROR HANDLING"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        # Determine number of events
        num_events = self._calculate_event_count(alive_count)
        
        # Get event weights
        weights = get_event_weights()
        weights = self._adjust_weights_for_game_state(weights, alive_count)
        
        # Execute events
        event_messages = []
        
        for i in range(num_events):
            if len(self.game_engine.get_alive_players(game)) <= 1:
                break
            
            # Choose and execute event
            event_type = self._choose_event_type(weights)
            message = await self.event_handler.execute_event(event_type, game, channel)
            
            if message:
                event_messages.append(message)
            
            await asyncio.sleep(0.5)
        
        # Send combined events in custom image or Rumble format
        await self._send_rumble_style_events(game, channel, event_messages)
    
    def _calculate_event_count(self, alive_count: int) -> int:
        """Calculate number of events based on alive players"""
        if alive_count <= 3:
            return random.randint(1, 2)
        elif alive_count <= 6:
            return random.randint(2, 3)
        elif alive_count <= 12:
            return random.randint(2, 4)
        else:
            return random.randint(3, 5)
    
    def _adjust_weights_for_game_state(self, weights: Dict[str, int], alive_count: int) -> Dict[str, int]:
        """Adjust event weights based on game state"""
        if alive_count <= 2:
            weights.update({"death": 70, "survival": 10, "sponsor": 10, "alliance": 5, "crate": 5})
        elif alive_count <= 3:
            weights.update({"death": 55, "survival": 15, "sponsor": 15, "alliance": 5, "crate": 10})
        elif alive_count <= 5:
            weights.update({"death": 45, "survival": 20, "sponsor": 15, "alliance": 10, "crate": 10})
        elif alive_count <= 10:
            weights.update({"death": 35, "survival": 25, "sponsor": 15, "alliance": 15, "crate": 10})
        
        return weights
    
    def _choose_event_type(self, weights: Dict[str, int]) -> str:
        """Choose event type based on weights"""
        event_types = list(weights.keys())
        event_weights = list(weights.values())
        return random.choices(event_types, weights=event_weights)[0]
    
    async def _send_rumble_style_events(self, game: Dict, channel: discord.TextChannel, 
                                      event_messages: List[str]):
        """Send events using custom round image, embed, or fallback based on settings"""
        if not event_messages:
            logger.warning("No event messages to send")
            return
        
        try:
            alive_after_events = len(self.game_engine.get_alive_players(game))
            
            # Check if custom images are enabled
            images_enabled = await self.config.guild(channel.guild).enable_custom_images()
            
            # Try to use custom image if enabled and available
            if (images_enabled and 
                hasattr(self, 'image_handler') and 
                self.image_handler and 
                self.image_handler.is_available()):
                
                # Combine event messages
                combined_events = "\n".join(event_messages)
                
                # Create custom image
                image_file = self.image_handler.create_round_image(
                    round_num=game['round'],
                    event_text=combined_events,
                    remaining_players=alive_after_events
                )
                
                if image_file:
                    await channel.send(file=image_file)
                    logger.debug(f"Sent custom round image for round {game['round']}")
                    return
                else:
                    logger.warning("Failed to create custom round image, falling back to embed")
            
            # Fallback to embed system (either disabled or failed)
            rumble_content = f"**Round {game['round']}**\n"
            rumble_content += "\n".join(event_messages)
            rumble_content += f"\n\n**Players Left: {alive_after_events}**"
            
            embed = discord.Embed(
                description=rumble_content,
                color=0x2F3136
            )
            
            await channel.send(embed=embed)
            logger.debug(f"Sent {'fallback' if images_enabled else 'standard'} embed for round {game['round']}")
            
        except Exception as e:
            logger.error(f"Failed to send round events: {e}")
            # Ultimate fallback - plain text message
            try:
                fallback_msg = f"**Round {game['round']}** - {len(alive_after_events)} players remaining"
                await channel.send(fallback_msg)
            except Exception:
                pass
    
    async def execute_random_event(self, game: Dict, channel: discord.TextChannel):
        """Execute a random game event (for backwards compatibility)"""
        alive_count = len(self.game_engine.get_alive_players(game))
        
        # Choose random event type
        weights = get_event_weights()
        weights = self._adjust_weights_for_game_state(weights, alive_count)
        
        event_types = list(weights.keys())
        event_weights = list(weights.values())
        event_type = random.choices(event_types, weights=event_weights)[0]
        
        # Execute the chosen event
        message = await self.event_handler.execute_event(event_type, game, channel)
        
        if message:
            # Send as custom image or Rumble-style embed
            await self._send_rumble_style_events(game, channel, [message])
    
    # =====================================================
    # COMMAND DEFINITIONS (hungergames group defined first)
    # =====================================================
    
    @commands.group(invoke_without_command=True)
    async def hungergames(self, ctx):
        """Hunger Games battle royale commands"""
        await ctx.send_help()
    
    @hungergames.command(name="alive")
    async def hg_alive(self, ctx):
        """Show current alive players in the active game"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        try:
            game = self.active_games[guild_id]
            alive_players = self.game_engine.get_alive_players(game)
            
            if not alive_players:
                return await ctx.send("💀 No survivors remain!")
            
            embed = create_alive_players_embed(game, alive_players)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error showing alive players: {e}")
            await ctx.send("❌ Error retrieving player information.")
    
    @hungergames.command(name="stats")
    async def hg_stats(self, ctx, member: discord.Member = None):
        """View Hunger Games statistics for yourself or another player"""
        try:
            if member is None:
                member = ctx.author
            
            member_data = await self.config.member(member).all()
            embed = create_player_stats_embed(member_data, member)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving stats: {e}")
            await ctx.send("❌ Error retrieving statistics.")
    
    @hungergames.command(name="stop")
    @commands.has_permissions(manage_guild=True)
    async def hg_stop(self, ctx):
        """Stop the current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active game to stop!")
        
        try:
            game = self.active_games[guild_id]
            
            # Cancel the game task
            if "task" in game:
                game["task"].cancel()
            
            # Clean up
            await self._cleanup_game(guild_id)
            
            embed = discord.Embed(
                title="🛑 **GAME TERMINATED**",
                description="The Hunger Games have been forcibly ended by the Capitol.",
                color=0x000000
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Game manually stopped in guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error stopping game: {e}")
            await ctx.send("❌ Error stopping the game.")
    
    @hungergames.command(name="status")
    async def hg_status(self, ctx):
        """Check the status of current Hunger Games"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active Hunger Games in this server.")
        
        try:
            game = self.active_games[guild_id]
            alive_players = self.game_engine.get_alive_players(game)
            
            embed = discord.Embed(
                title="📊 **GAME STATUS**",
                color=0x4169E1
            )
            
            embed.add_field(
                name="🎮 **Status**",
                value=game["status"].capitalize(),
                inline=True
            )
            
            embed.add_field(
                name="👥 **Players Alive**",
                value=f"{len(alive_players)}/{len(game['players'])}",
                inline=True
            )
            
            embed.add_field(
                name="🔄 **Current Round**",
                value=str(game["round"]),
                inline=True
            )
            
            if game["status"] == "active":
                task_status = "Unknown"
                if "task" in game:
                    if game["task"].done():
                        task_status = "Completed"
                    elif game["task"].cancelled():
                        task_status = "Cancelled"
                    else:
                        task_status = "Running"
                
                embed.add_field(
                    name="⏰ **Task Status**",
                    value=task_status,
                    inline=True
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            await ctx.send("❌ Error retrieving game status.")
    
    @hungergames.command(name="test")
    @commands.has_permissions(manage_guild=True)
    async def hg_test(self, ctx):
        """Test game events (Admin only)"""
        try:
            # Create a fake game for testing
            test_game = {
                "players": {
                    str(ctx.author.id): {
                        "name": ctx.author.display_name,
                        "title": "the Tester",
                        "alive": True,
                        "kills": 0,
                        "revives": 0,
                        "district": 1
                    },
                    "123456789": {
                        "name": "TestBot",
                        "title": "the Dummy",
                        "alive": True,
                        "kills": 0,
                        "revives": 0,
                        "district": 2
                    },
                    "987654321": {
                        "name": "TestBot2", 
                        "title": "the Mock",
                        "alive": True,
                        "kills": 0,
                        "revives": 0,
                        "district": 3
                    }
                },
                "round": 1,
                "eliminated": [],
                "sponsor_used": [],
                "reactions": set(),
                "milestones_shown": set()
            }
            
            embed = discord.Embed(
                title="🧪 **EVENT TESTING**",
                description="Testing game events...",
                color=0x00CED1
            )
            
            await ctx.send(embed=embed)
            
            # Test each individual event type
            event_types = ["death", "survival", "sponsor", "alliance", "crate"]
            
            await ctx.send("**Testing Individual Events:**")
            
            for event_type in event_types:
                try:
                    message = await self.event_handler.execute_event(event_type, test_game, ctx.channel)
                    
                    if message:
                        # Choose appropriate color
                        colors = {
                            "death": 0xFF4500,
                            "crate": 0x8B4513,
                            "sponsor": 0xFFD700,
                            "alliance": 0x4169E1,
                            "survival": 0x32CD32
                        }
                        
                        color = colors.get(event_type, 0x32CD32)
                        
                        embed = discord.Embed(
                            title=f"✅ **{event_type.upper()} EVENT TEST**",
                            description=message,
                            color=color
                        )
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send(f"❌ **{event_type.upper()} EVENT**: No message generated")
                        
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    await ctx.send(f"❌ **{event_type.upper()} EVENT ERROR**: {str(e)}")
            
            # Test special events
            try:
                await ctx.send("\n**Testing Special Events:**")
                
                # Test midgame event
                special_event = await self.game_engine._generate_midgame_event(test_game)
                if special_event:
                    await self._send_special_event(special_event, ctx.channel)
                    await asyncio.sleep(2)
                
                # Test combined events
                await ctx.send("**Testing Combined Events:**")
                await self.execute_combined_events(test_game, ctx.channel)
                await asyncio.sleep(2)
            except Exception as e:
                await ctx.send(f"❌ **SPECIAL EVENTS ERROR**: {str(e)}")
            
            await ctx.send("🎉 **Testing Complete!**")
            
        except Exception as e:
            logger.error(f"Error in test command: {e}")
            await ctx.send(f"❌ Error running tests: {str(e)}")

    @hungergames.command(name="imagemode")
    @commands.has_permissions(manage_guild=True)
    async def hg_imagemode(self, ctx, mode: str = None):
        """Toggle image display mode: custom, embed, or toggle
        
        Usage:
        .hungergames imagemode toggle   - Switch between modes
        .hungergames imagemode custom   - Use custom images
        .hungergames imagemode embed    - Use classic embeds
        .hungergames imagemode          - Show current mode
        """
        try:
            if not mode:
                # Show current mode
                current_setting = await self.config.guild(ctx.guild).enable_custom_images()
                
                if current_setting:
                    if hasattr(self, 'image_handler') and self.image_handler and self.image_handler.is_available():
                        status = "🖼️ **Custom Images** (Active)"
                    else:
                        status = "🖼️ **Custom Images** (Enabled, No Template)"
                else:
                    status = "📋 **Classic Embeds**"
                
                embed = discord.Embed(
                    title="🎮 **Current Display Mode**",
                    description=status,
                    color=0x00CED1
                )
                
                embed.add_field(
                    name="💡 **Commands**",
                    value=(
                        "`.hungergames imagemode toggle` - Switch modes\n"
                        "`.hungergames imagemode custom` - Use custom images\n"
                        "`.hungergames imagemode embed` - Use classic embeds"
                    ),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            mode = mode.lower()
            
            if mode == "toggle":
                # Toggle current setting
                current_setting = await self.config.guild(ctx.guild).enable_custom_images()
                new_setting = not current_setting
                await self.config.guild(ctx.guild).enable_custom_images.set(new_setting)
                
                if new_setting:
                    embed = discord.Embed(
                        title="🖼️ **Switched to Custom Images**",
                        description="Rounds will now use custom image displays.",
                        color=0x00FF00
                    )
                    
                    # Check if template is available
                    if hasattr(self, 'image_handler') and self.image_handler and self.image_handler.is_available():
                        embed.add_field(
                            name="✅ **Ready**",
                            value="Template found and ready to use!",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="⚠️ **Missing Template**",
                            value="Upload a template with `.hungergames image upload` to use custom images.",
                            inline=False
                        )
                else:
                    embed = discord.Embed(
                        title="📋 **Switched to Classic Embeds**",
                        description="Rounds will now use the classic text embed format.",
                        color=0xFF8C00
                    )
                
            elif mode in ["custom", "image", "images"]:
                # Enable custom images
                await self.config.guild(ctx.guild).enable_custom_images.set(True)
                
                embed = discord.Embed(
                    title="🖼️ **Custom Images Enabled!**",
                    description="Rounds will now use custom images when available.",
                    color=0x00FF00
                )
                
                # Check if template is available
                if hasattr(self, 'image_handler') and self.image_handler and self.image_handler.is_available():
                    embed.add_field(
                        name="✅ **Ready**",
                        value="Template found and ready to use!",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ **Missing Template**",
                        value="Upload a template with `.hungergames image upload` to use custom images.",
                        inline=False
                    )
            
            elif mode in ["embed", "embeds", "classic", "text"]:
                # Enable classic embeds
                await self.config.guild(ctx.guild).enable_custom_images.set(False)
                
                embed = discord.Embed(
                    title="📋 **Classic Embeds Enabled**",
                    description="Rounds will now use the classic text embed format.",
                    color=0xFF8C00
                )
                
                embed.add_field(
                    name="📝 **Note**",
                    value="You can switch back anytime with `.hungergames imagemode custom`",
                    inline=False
                )
            
            else:
                # Invalid mode
                return await ctx.send("❌ Invalid mode! Use: `toggle`, `custom`, or `embed`")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in imagemode command: {e}")
            await ctx.send(f"❌ Error changing display mode: {str(e)}")
    
    # =====================================================
    # IMAGE MANAGEMENT COMMANDS - NEW SECTION
    # =====================================================
    
    @hungergames.group(name="image", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def image_main(self, ctx):
        """Custom round image management"""
        embed = discord.Embed(
            title="🖼️ **Round Image Management**",
            description="Manage custom round display images",
            color=0x00CED1
        )
        
        embed.add_field(
            name="📋 **Available Commands**",
            value=(
                "• `.hungergames image enable` - Enable custom images\n"
                "• `.hungergames image disable` - Use classic embeds\n"
                "• `.hungergames image toggle` - Switch between modes\n"
                "• `.hungergames image upload` - Upload template image\n"
                "• `.hungergames image test` - Test current template\n"
                "• `.hungergames image debug` - Show positioning guides\n"
                "• `.hungergames image position` - Adjust text positions\n"
                "• `.hungergames image status` - Check system status\n"
                "• `.hungergames image info` - Show template information"
            ),
            inline=False
        )
        
        # Show current status
        if hasattr(self, 'image_handler') and self.image_handler:
            images_enabled = await self.config.guild(ctx.guild).enable_custom_images()
            if self.image_handler.is_available() and images_enabled:
                status = "✅ **Custom Images Active**"
            elif self.image_handler.is_available() and not images_enabled:
                status = "🔄 **Custom Images Available (Disabled)**"
            else:
                status = "❌ **No Template Found**"
        else:
            status = "❌ **System Not Available**"
        
        embed.add_field(
            name="🖼️ **Current Status**",
            value=status,
            inline=False
        )
        
        embed.add_field(
            name="💡 **Quick Toggle**",
            value=(
                "• `.hungergames image toggle` - Switch modes instantly\n"
                "• `.hungergames image enable` - Use custom images\n"
                "• `.hungergames image disable` - Use classic embeds"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @image_main.command(name="upload")
    async def image_upload(self, ctx):
        """Upload a new round template image"""
        if not ctx.message.attachments:
            return await ctx.send("❌ Please attach an image file!")
        
        attachment = ctx.message.attachments[0]
        
        # Check file type
        if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return await ctx.send("❌ Please upload a PNG or JPG image!")
        
        try:
            # Check if image handler is available
            if not hasattr(self, 'image_handler') or not self.image_handler:
                return await ctx.send("❌ Image system is not available!")
            
            # Download and save image
            image_data = await attachment.read()
            success = self.image_handler.save_template_image(image_data)
            
            if success:
                embed = discord.Embed(
                    title="✅ **Template Uploaded Successfully!**",
                    description=f"Image saved as template: `{attachment.filename}`",
                    color=0x00FF00
                )
                embed.add_field(
                    name="📝 **Next Steps**",
                    value="Use `.hungergames image test` to test the template!",
                    inline=False
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to save template image!")
                
        except Exception as e:
            logger.error(f"Error uploading template: {e}")
            await ctx.send(f"❌ Error uploading image: {str(e)}")
    
    @image_main.command(name="test")
    async def image_test(self, ctx, round_num: int = 5, remaining: int = 12):
        """Test the current template with sample data"""
        try:
            if not hasattr(self, 'image_handler') or not self.image_handler:
                return await ctx.send("❌ No image handler available!")
            
            if not self.image_handler.is_available():
                return await ctx.send("❌ No template image available. Upload one first!")
            
            # Create test image
            test_event = "Player1 the Brave eliminated Player2 the Swift in epic combat!"
            image_file = self.image_handler.create_round_image(
                round_num=round_num,
                event_text=test_event,
                remaining_players=remaining
            )
            
            if image_file:
                embed = discord.Embed(
                    title="🧪 **Template Test**",
                    description="Here's how your template looks with sample data:",
                    color=0x00CED1
                )
                embed.set_image(url="attachment://round_display.png")
                await ctx.send(embed=embed, file=image_file)
            else:
                await ctx.send("❌ Failed to generate test image!")
                
        except Exception as e:
            logger.error(f"Error testing template: {e}")
            await ctx.send(f"❌ Error testing template: {str(e)}")
    
    @image_main.command(name="status")
    async def image_status(self, ctx):
        """Check image system status"""
        embed = discord.Embed(
            title="🖼️ **Image System Status**",
            color=0x00CED1
        )
        
        try:
            # Check if handler exists
            has_handler = hasattr(self, 'image_handler') and self.image_handler is not None
            embed.add_field(
                name="🔧 **Handler Status**",
                value="✅ Initialized" if has_handler else "❌ Not initialized",
                inline=True
            )
            
            if has_handler:
                # Check settings
                images_enabled = await self.config.guild(ctx.guild).enable_custom_images()
                template_available = self.image_handler.is_available()
                
                embed.add_field(
                    name="⚙️ **Setting**",
                    value="✅ Enabled" if images_enabled else "❌ Disabled",
                    inline=True
                )
                
                embed.add_field(
                    name="🖼️ **Template**",
                    value="✅ Available" if template_available else "❌ Missing",
                    inline=True
                )
                
                # Overall status
                if images_enabled and template_available:
                    overall_status = "🎯 **Active** - Using custom images"
                elif images_enabled and not template_available:
                    overall_status = "⚠️ **Enabled but no template** - Using embeds"
                else:
                    overall_status = "📋 **Disabled** - Using classic embeds"
                
                embed.add_field(
                    name="📊 **Overall Status**",
                    value=overall_status,
                    inline=False
                )
                
                embed.add_field(
                    name="📁 **Template Path**",
                    value=f"`{self.image_handler.get_template_path()}`",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            embed.add_field(
                name="❌ **Error**",
                value=str(e),
                inline=False
            )
            await ctx.send(embed=embed)
    
    @image_main.command(name="debug")
    async def image_debug(self, ctx):
        """Create debug image showing positioning guides"""
        try:
            if not hasattr(self, 'image_handler') or not self.image_handler:
                return await ctx.send("❌ No image handler available!")
            
            if not self.image_handler.is_available():
                return await ctx.send("❌ No template image available. Upload one first!")
            
            # Create debug image with positioning guides
            debug_file = self.image_handler.create_debug_image()
            
            if debug_file:
                embed = discord.Embed(
                    title="🔍 **Debug Positioning**",
                    description=(
                        "**Red circle:** Round number position\n"
                        "**Red rectangle:** Event text area\n"
                        "**Blue circle:** Player count position\n\n"
                        "Current coordinates are shown as labels."
                    ),
                    color=0xFF0000
                )
                embed.set_image(url="attachment://debug_round_display.png")
                await ctx.send(embed=embed, file=debug_file)
            else:
                await ctx.send("❌ Failed to generate debug image!")
                
        except Exception as e:
            logger.error(f"Error creating debug image: {e}")
            await ctx.send(f"❌ Error creating debug image: {str(e)}")
    
    @image_main.command(name="position")
    async def image_position(self, ctx, element: str, x: int = None, y: int = None, x2: int = None, y2: int = None):
        """Adjust text positioning
        
        Usage:
        .hungergames image position round 400 200  (for round number)
        .hungergames image position players 680 950  (for player count)  
        .hungergames image position event 60 320 940 380  (for event area - needs 4 coordinates)
        """
        try:
            if not hasattr(self, 'image_handler') or not self.image_handler:
                return await ctx.send("❌ No image handler available!")
            
            element = element.lower()
            
            if element == "round":
                if x is None or y is None:
                    return await ctx.send("❌ Round position needs X and Y coordinates!\nUsage: `.hungergames image position round 400 200`")
                
                self.image_handler.update_positions(round_pos=(x, y))
                await ctx.send(f"✅ Round position updated to ({x}, {y})")
                
            elif element == "players":
                if x is None or y is None:
                    return await ctx.send("❌ Players position needs X and Y coordinates!\nUsage: `.hungergames image position players 680 950`")
                
                self.image_handler.update_positions(players_pos=(x, y))
                await ctx.send(f"✅ Players position updated to ({x}, {y})")
                
            elif element == "event":
                if None in [x, y, x2, y2]:
                    return await ctx.send("❌ Event area needs X1, Y1, X2, Y2 coordinates!\nUsage: `.hungergames image position event 60 320 940 380`")
                
                self.image_handler.update_positions(event_area=(x, y, x2, y2))
                await ctx.send(f"✅ Event area updated to ({x}, {y}, {x2}, {y2})")
                
            else:
                await ctx.send("❌ Invalid element! Use: `round`, `players`, or `event`")
                
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            await ctx.send(f"❌ Error updating position: {str(e)}")
    
    @image_main.command(name="info")
    async def image_info(self, ctx):
        """Show detailed template information"""
        try:
            if not hasattr(self, 'image_handler') or not self.image_handler:
                return await ctx.send("❌ Image system not available!")
            
            template_info = self.image_handler.get_template_info()
            
            embed = discord.Embed(
                title="📋 **Template Information**",
                color=0x00CED1
            )
            
            if template_info.get("exists"):
                embed.add_field(
                    name="📏 **Dimensions**",
                    value=f"{template_info['size'][0]} x {template_info['size'][1]} pixels",
                    inline=True
                )
                
                embed.add_field(
                    name="🎨 **Format**",
                    value=template_info.get('format', 'Unknown'),
                    inline=True
                )
                
                embed.add_field(
                    name="🔧 **Mode**",
                    value=template_info.get('mode', 'Unknown'),
                    inline=True
                )
                
                embed.add_field(
                    name="📁 **Path**",
                    value=f"`{template_info['path']}`",
                    inline=False
                )
                
                # Add positioning info
                embed.add_field(
                    name="📍 **Text Positions**",
                    value=(
                        f"Round Number: {self.image_handler.round_position}\n"
                        f"Event Area: {self.image_handler.event_area}\n"
                        f"Players Count: {self.image_handler.players_position}"
                    ),
                    inline=False
                )
            else:
                embed.description = "❌ **No template found**"
                if "error" in template_info:
                    embed.add_field(
                        name="❌ **Error**",
                        value=template_info["error"],
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting template info: {e}")
            await ctx.send(f"❌ Error retrieving template information: {str(e)}")
    
    # =====================================================
    # EXISTING COMMANDS CONTINUE...
    # =====================================================
    
    @hungergames.command(name="force")
    @commands.has_permissions(manage_guild=True)
    async def hg_force_event(self, ctx, event_type: str = "random"):
        """Force a single event in active game (Admin only)"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.active_games:
            return await ctx.send("❌ No active game to force event in!")
        
        game = self.active_games[guild_id]
        if game["status"] != "active":
            return await ctx.send("❌ Game is not active!")
        
        valid_types = ["death", "survival", "sponsor", "alliance", "crate", "random", "combined", "special"]
        if event_type.lower() not in valid_types:
            return await ctx.send(f"❌ Invalid event type! Use: {', '.join(valid_types)}")
        
        # Force execute an event
        try:
            if event_type.lower() == "random":
                await self.execute_random_event(game, ctx.channel)
            elif event_type.lower() == "combined":
                await self.execute_combined_events(game, ctx.channel)
            elif event_type.lower() == "special":
                alive_players = self.game_engine.get_alive_players(game)
                special_event = await self.game_engine._generate_midgame_event(game)
                if special_event:
                    await self._send_special_event(special_event, ctx.channel)
                else:
                    await ctx.send("❌ No special event triggered")
            else:
                # Execute specific event type
                message = await self.event_handler.execute_event(event_type, game, ctx.channel)
                
                if message:
                    # Send using custom image or embed
                    await self._send_rumble_style_events(game, ctx.channel, [message])
                else:
                    await ctx.send(f"❌ Failed to generate {event_type} event")
                    
        except Exception as e:
            logger.error(f"Error forcing event: {e}")
            await ctx.send(f"❌ Error forcing event: {str(e)}")
    
    @hungergames.command(name="debug")
    @commands.has_permissions(manage_guild=True)
    async def hg_debug(self, ctx):
        """Debug current game state (Admin only)"""
        guild_id = ctx.guild.id
        
        embed = discord.Embed(
            title="🔍 **DEBUG INFO**",
            color=0x00CED1
        )
        
        # Check if game is active
        if guild_id in self.active_games:
            game = self.active_games[guild_id]
            
            # Game state info
            alive_count = len(self.game_engine.get_alive_players(game))
            total_players = len(game.get("players", {}))
            
            embed.add_field(
                name="🎮 **Game State**",
                value=f"Status: {game.get('status', 'Unknown')}\n"
                      f"Round: {game.get('round', 0)}\n"
                      f"Alive: {alive_count}/{total_players}\n"
                      f"Eliminated: {len(game.get('eliminated', []))}\n"
                      f"Sponsors Used: {len(game.get('sponsor_used', []))}",
                inline=True
            )
            
            # Task status
            task_status = "Unknown"
            if "task" in game:
                if game["task"].done():
                    task_status = "Completed"
                elif game["task"].cancelled():
                    task_status = "Cancelled"
                else:
                    task_status = "Running"
            else:
                task_status = "No Task"
            
            embed.add_field(
                name="⚙️ **Task Status**",
                value=task_status,
                inline=True
            )
            
            # Milestones
            milestones = game.get("milestones_shown", set())
            embed.add_field(
                name="🏁 **Milestones**",
                value=f"Shown: {list(milestones) if milestones else 'None'}",
                inline=True
            )
        else:
            embed.add_field(
                name="🎮 **Game State**",
                value="No active game",
                inline=False
            )
        
        # Check constants
        try:
            from .constants import DEATH_EVENTS, SURVIVAL_EVENTS, SPONSOR_EVENTS, ALLIANCE_EVENTS, CRATE_EVENTS
            embed.add_field(
                name="📊 **Constants Loaded**",
                value=f"Death Events: {len(DEATH_EVENTS)}\n"
                      f"Survival Events: {len(SURVIVAL_EVENTS)}\n"
                      f"Sponsor Events: {len(SPONSOR_EVENTS)}\n"
                      f"Alliance Events: {len(ALLIANCE_EVENTS)}\n"
                      f"Crate Events: {len(CRATE_EVENTS)}",
                inline=True
            )
        except Exception as e:
            embed.add_field(
                name="❌ **Import Error**",
                value=str(e),
                inline=False
            )
        
        # System info
        system_info = f"Active Games: {len(self.active_games)}\n"
        system_info += f"Cache Entries: {len(getattr(self, '_alive_cache', {}))}\n"
        system_info += f"Event Handler: {'✅' if hasattr(self, 'event_handler') else '❌'}\n"
        system_info += f"GIF System: {'✅' if getattr(self, 'gif_manager', None) else '❌'}\n"
        system_info += f"Image System: {'✅' if getattr(self, 'image_handler', None) else '❌'}"
        
        embed.add_field(
            name="🖥️ **System**",
            value=system_info,
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @hungergames.command(name="leaderboard", aliases=["lb", "top"])
    async def hg_leaderboard(self, ctx, stat: str = "wins"):
        """View the Hunger Games leaderboard
        
        Available stats: wins, kills, deaths, revives"""
        
        try:
            if stat.lower() not in ["wins", "kills", "deaths", "revives"]:
                return await ctx.send("❌ Invalid stat! Use: `wins`, `kills`, `deaths`, or `revives`")
            
            stat = stat.lower()
            
            # Get all member data
            all_members = await self.config.all_members(ctx.guild)
            
            # Filter and sort
            filtered_members = []
            for member_id, data in all_members.items():
                stat_value = data.get(stat, 0)
                if stat_value > 0:
                    filtered_members.append((member_id, data))
            
            filtered_members.sort(key=lambda x: x[1].get(stat, 0), reverse=True)
            
            embed = create_leaderboard_embed(ctx.guild, filtered_members, stat)
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await ctx.send("❌ Error retrieving leaderboard data.")
    
    @hungergames.command(name="config")
    @commands.has_permissions(manage_guild=True)
    async def hg_config(self, ctx):
        """View current Hunger Games configuration"""
        try:
            config_data = await self.config.guild(ctx.guild).all()
            
            embed = discord.Embed(
                title="⚙️ **Hunger Games Configuration**",
                color=0x4169E1
            )
            
            embed.add_field(
                name="💰 **Base Reward**",
                value=f"{config_data['base_reward']:,} credits",
                inline=True
            )
            
            embed.add_field(
                name="🎁 **Sponsor Chance**",
                value=f"{config_data['sponsor_chance']}%",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ **Event Interval**",
                value=f"{config_data['event_interval']} seconds",
                inline=True
            )
            
            embed.add_field(
                name="⏰ **Recruitment Time**",
                value=f"{config_data['recruitment_time']} seconds",
                inline=True
            )
            
            embed.add_field(
                name="🎬 **GIFs Enabled**",
                value="✅ Yes" if config_data.get('enable_gifs', False) else "❌ No",
                inline=True
            )
            
            # Add image system status
            images_enabled = config_data.get('enable_custom_images', True)
            image_status = "❌ Disabled"
            if images_enabled:
                if hasattr(self, 'image_handler') and self.image_handler and self.image_handler.is_available():
                    image_status = "✅ Active"
                else:
                    image_status = "⚠️ Enabled (No Template)"
            
            embed.add_field(
                name="🖼️ **Custom Images**",
                value=image_status,
                inline=True
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in config command: {e}")
            await ctx.send("❌ Error retrieving configuration.")
    
    @hungergames.group(name="set", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def hg_set(self, ctx):
        """Configure Hunger Games settings"""
        await ctx.send_help()

    # =====================================================
    # GIF COMMANDS - EXISTING (KEPT FOR COMPATIBILITY)
    # =====================================================
    
    @hungergames.group(name="gif", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def gif_main(self, ctx):
        """GIF management for Hunger Games"""
        if not GIF_SYSTEM_AVAILABLE or not self.gif_manager:
            return await ctx.send("❌ GIF system is not available. Check bot logs for details.")
        
        # Show help for gif commands
        embed = discord.Embed(
            title="🎬 **GIF Management Commands**",
            description="Manage GIF integration for Hunger Games",
            color=0x00CED1
        )
        
        embed.add_field(
            name="📋 **Available Commands**",
            value=(
                "• `.hungergames gif enable` - Enable GIF integration\n"
                "• `.hungergames gif disable` - Disable GIF integration\n"
                "• `.hungergames gif stats` - Show GIF collection statistics\n"
                "• `.hungergames gif structure` - Show directory structure\n"
                "• `.hungergames gif test [category] [subcategory]` - Test GIF selection\n"
                "• `.hungergames gif reload` - Reload GIF cache"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @gif_main.command(name="enable")
    async def gif_enable(self, ctx):
        """Enable GIF integration"""
        if not GIF_SYSTEM_AVAILABLE or not self.gif_manager:
            return await ctx.send("❌ GIF system is not available.")
        
        try:
            await self.config.guild(ctx.guild).enable_gifs.set(True)
            
            embed = discord.Embed(
                title="🎬 **GIF Integration Enabled!**",
                description="GIFs will now be displayed during games when available.",
                color=0x00FF00
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error enabling GIFs: {str(e)}")
    
    @gif_main.command(name="disable") 
    async def gif_disable(self, ctx):
        """Disable GIF integration"""
        if not GIF_SYSTEM_AVAILABLE or not self.gif_manager:
            return await ctx.send("❌ GIF system is not available.")
        
        try:
            await self.config.guild(ctx.guild).enable_gifs.set(False)
            
            embed = discord.Embed(
                title="🚫 **GIF Integration Disabled**",
                description="GIFs will no longer be displayed during games.",
                color=0xFF0000
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error disabling GIFs: {str(e)}")
    
    @gif_main.command(name="stats")
    async def gif_stats(self, ctx):
        """Show GIF collection statistics"""
        if not GIF_SYSTEM_AVAILABLE or not self.gif_manager:
            return await ctx.send("❌ GIF system is not available.")
        
        try:
            stats = self.gif_manager.get_gif_stats()
            
            embed = discord.Embed(
                title="📊 **GIF Collection Statistics**",
                color=0x00CED1
            )
            
            total_gifs = 0
            
            for category, subcategories in stats.items():
                category_total = sum(subcategories.values())
                total_gifs += category_total
                
                if category_total > 0:
                    subcategory_text = "\n".join([
                        f"• {subcat}: {count}" 
                        for subcat, count in subcategories.items() 
                        if count > 0
                    ])
                    
                    embed.add_field(
                        name=f"🎬 **{category.title()}** ({category_total})",
                        value=subcategory_text if subcategory_text else "None",
                        inline=True
                    )
            
            embed.description = f"**Total GIFs:** {total_gifs}"
            
            if total_gifs == 0:
                embed.add_field(
                    name="📁 **No GIFs Found**",
                    value="Add GIF files to the `gifs/` directory to get started!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting GIF stats: {str(e)}")
    
    # =====================================================
    # SETTINGS COMMANDS
    # =====================================================
    
    @hg_set.command(name="reward")
    async def hg_set_reward(self, ctx, amount: int):
        """Set the base reward amount"""
        try:
            valid, error_msg = self.validator.validate_base_reward(amount)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).base_reward.set(amount)
            await ctx.send(f"✅ Base reward set to {amount:,} credits!")
            
        except Exception as e:
            logger.error(f"Error setting reward: {e}")
            await ctx.send("❌ Error updating reward amount.")
    
    @hg_set.command(name="sponsor")
    async def hg_set_sponsor(self, ctx, chance: int):
        """Set the sponsor revival chance (1-50%)"""
        try:
            valid, error_msg = self.validator.validate_sponsor_chance(chance)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).sponsor_chance.set(chance)
            await ctx.send(f"✅ Sponsor revival chance set to {chance}%!")
            
        except Exception as e:
            logger.error(f"Error setting sponsor chance: {e}")
            await ctx.send("❌ Error updating sponsor chance.")
    
    @hg_set.command(name="interval")
    async def hg_set_interval(self, ctx, seconds: int):
        """Set the event interval (10-120 seconds)"""
        try:
            valid, error_msg = self.validator.validate_event_interval(seconds)
            if not valid:
                return await ctx.send(f"❌ {error_msg}")
            
            await self.config.guild(ctx.guild).event_interval.set(seconds)
            await ctx.send(f"✅ Event interval set to {seconds} seconds!")
            
        except Exception as e:
            logger.error(f"Error setting interval: {e}")
            await ctx.send("❌ Error updating event interval.")


async def setup(bot):
    """Required function for loading the cog"""
    await bot.add_cog(HungerGames(bot))
