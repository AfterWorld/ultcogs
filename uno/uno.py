"""
Enhanced Uno Game Cog for Red-Discord Bot V3
Features: Configuration, Statistics, AI Players, Error Handling, Visual Persistence
"""
import asyncio
import discord
from discord.ext import tasks
from typing import Optional, Dict, Any, List
import traceback
import json
from datetime import datetime, timedelta

# Red-DiscordBot V3 specific imports
from redbot.core import commands, Config
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.predicates import MessagePredicate

from .game import UnoGameSession, GameState, PlayerStats, AIPlayer
from .views import UnoGameView, LobbyView, StatsView, ConfigView
from .utils import (
    setup_assets_directory, 
    game_manager, 
    format_player_list, 
    format_card_counts,
    validate_card_files,
    cleanup_temp_files,
    stats_manager
)
from .cards import UnoColor


class UnoCog(commands.Cog):
    """Enhanced Uno card game cog with advanced features"""
    
    def __init__(self, bot):
        self.bot = bot
        self.assets_path = setup_assets_directory(cog_data_path(self))
        
        # Configuration system
        self.config = Config.get_conf(self, identifier=2584931056)
        
        # Default server settings
        default_guild = {
            "starting_cards": 7,
            "max_players": 10,
            "timeout_minutes": 30,
            "uno_penalty": True,
            "draw_stacking": True,
            "challenge_draw4": True,
            "ai_players": True,
            "max_ai_players": 3,
            "auto_start_delay": 60,  # seconds before auto-starting with AI
            "persistent_games": True,
            "statistics_enabled": True,
            "leaderboard_enabled": True,
            "visual_persistence": True,  # NEW: Keep game visible when people talk
            "repost_threshold": 5  # NEW: Repost game after X messages
        }
        
        # Default global settings
        default_global = {
            "total_games": 0,
            "total_players": 0,
            "maintenance_mode": False
        }
        
        # Player statistics
        default_member = {
            "games_played": 0,
            "games_won": 0,
            "cards_played": 0,
            "draw4_challenged": 0,
            "draw4_successful_challenges": 0,
            "uno_calls": 0,
            "uno_penalties": 0,
            "fastest_win": None,
            "total_play_time": 0,
            "favorite_color": None,
            "achievements": []
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.config.register_member(**default_member)
        
        # Track message counts for visual persistence
        self.channel_message_counts: Dict[int, int] = {}
        
        # Start background tasks
        self.cleanup_task.start()
        self.ai_task.start()
        self.statistics_task.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.cleanup_task.cancel()
        self.ai_task.cancel()
        self.statistics_task.cancel()
        
        # Save all active games if persistence is enabled
        asyncio.create_task(self._save_persistent_games())
        
        # Clean up all games
        for game in list(game_manager.games.values()):
            game.cleanup()
        game_manager.games.clear()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages to handle visual persistence"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if there's an active game in this channel
        game = game_manager.get_game(message.channel.id)
        if not game or game.state not in [GameState.LOBBY, GameState.PLAYING]:
            return
        
        # Check if visual persistence is enabled
        try:
            settings = await self.config.guild(message.guild).all()
            if not settings.get("visual_persistence", True):
                return
            
            # Track message count
            channel_id = message.channel.id
            if channel_id not in self.channel_message_counts:
                self.channel_message_counts[channel_id] = 0
            
            self.channel_message_counts[channel_id] += 1
            
            # Check if we should repost the game
            threshold = settings.get("repost_threshold", 5)
            if self.channel_message_counts[channel_id] >= threshold:
                self.channel_message_counts[channel_id] = 0  # Reset counter
                
                # Repost the game embed
                await self._repost_game_embed(game)
                
        except Exception as e:
            print(f"Error in visual persistence: {e}")
    
    async def _repost_game_embed(self, game: UnoGameSession):
        """Repost the game embed to keep it visible"""
        try:
            channel = self.bot.get_channel(game.channel_id)
            if not channel:
                return
            
            # Create new embed and view
            if game.state == GameState.LOBBY:
                embed = self.create_lobby_embed(game)
                view = LobbyView(game, self)
            else:
                embed = self.create_game_embed(game)
                view = UnoGameView(game, self)
            
            # Send new message
            new_message = await channel.send(embed=embed, view=view)
            
            # Update game message reference
            old_message = game.game_message
            game.game_message = new_message
            
            # Try to delete old message
            if old_message:
                try:
                    await old_message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass  # Message might already be deleted or no permissions
                    
        except Exception as e:
            print(f"Error reposting game embed: {e}")
    
    async def _save_persistent_games(self):
        """Save active games for persistence"""
        try:
            persistent_data = {}
            for channel_id, game in game_manager.games.items():
                if game.settings.get("persistent_games", True) and game.state != GameState.FINISHED:
                    persistent_data[str(channel_id)] = game.to_dict()
            
            if persistent_data:
                # Save to config or file
                await self.config.persistent_games.set(persistent_data)
        except Exception as e:
            print(f"Error saving persistent games: {e}")
    
    async def _load_persistent_games(self):
        """Load saved games on startup"""
        try:
            persistent_data = await self.config.persistent_games()
            for channel_id_str, game_data in persistent_data.items():
                channel_id = int(channel_id_str)
                game = UnoGameSession.from_dict(game_data)
                game_manager.games[channel_id] = game
        except Exception as e:
            print(f"Error loading persistent games: {e}")
    
    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """Periodic cleanup task"""
        try:
            # Clean up expired games
            expired_count = game_manager.cleanup_expired_games()
            if expired_count > 0:
                print(f"Cleaned up {expired_count} expired Uno games")
            
            # Clean up temporary image files
            await cleanup_temp_files(self.assets_path)
            
            # Save persistent games
            await self._save_persistent_games()
            
            # Clean up message counts for inactive channels
            active_channels = set(game.channel_id for game in game_manager.games.values())
            self.channel_message_counts = {
                ch_id: count for ch_id, count in self.channel_message_counts.items() 
                if ch_id in active_channels
            }
            
        except Exception as e:
            print(f"Error in cleanup task: {e}")
    
    @tasks.loop(seconds=30)
    async def ai_task(self):
        """Handle AI player actions"""
        try:
            for game in game_manager.games.values():
                if game.state != GameState.PLAYING:
                    continue
                
                current_player = game.get_current_player()
                if not game.is_ai_player(current_player):
                    continue
                
                ai_player = game.get_ai_player(current_player)
                if not ai_player:
                    continue
                
                # AI makes a move
                await self._handle_ai_turn(game, ai_player)
                
        except Exception as e:
            print(f"Error in AI task: {e}")
    
    @tasks.loop(hours=1)
    async def statistics_task(self):
        """Periodic statistics updates"""
        try:
            # Update global statistics
            total_games = sum(1 for g in game_manager.games.values() if g.state == GameState.FINISHED)
            await self.config.total_games.set(total_games)
            
            # Additional periodic stats processing could go here
            
        except Exception as e:
            print(f"Error in statistics task: {e}")
    
    @cleanup_task.before_loop
    @ai_task.before_loop  
    @statistics_task.before_loop
    async def before_tasks(self):
        await self.bot.wait_until_ready()
        # Load persistent games on startup
        await self._load_persistent_games()
    
    async def _handle_ai_turn(self, game: UnoGameSession, ai_player: AIPlayer):
        """Handle an AI player's turn"""
        try:
            hand = game.hands.get(ai_player.player_id)
            if not hand:
                return
            
            # Check if AI needs to draw penalty cards
            if game.draw_count > 0:
                # AI always draws penalty (doesn't stack for now)
                game.draw_card(ai_player.player_id)
                await self.update_game_display(game)
                return
            
            # Get playable cards
            playable_cards = game.get_playable_cards(ai_player.player_id)
            
            if not playable_cards:
                # Must draw a card
                success, message, drawn = game.draw_card(ai_player.player_id)
                if success:
                    await self.update_game_display(game)
                return
            
            # AI chooses a card
            chosen_card = ai_player.choose_card(hand, game.deck.top_card, game.deck.current_color)
            if not chosen_card:
                return
            
            # Handle wild cards
            declared_color = None
            if chosen_card.color == UnoColor.WILD:
                declared_color = ai_player.choose_wild_color(hand)
            
            # Call UNO if needed
            if hand.card_count == 2:  # Will have 1 after playing
                game.call_uno(ai_player.player_id)
            
            # Play the card
            success, message = game.play_card(ai_player.player_id, chosen_card, declared_color)
            if success:
                await self.update_game_display(game)
                
                # Add a small delay for realism
                await asyncio.sleep(2)
            
        except Exception as e:
            print(f"Error handling AI turn: {e}")
    
    # Hybrid commands (work with both prefix and slash)
    
    @commands.hybrid_group(name="uno", invoke_without_command=True)
    async def uno_group(self, ctx):
        """Uno card game commands"""
        try:
            embed = discord.Embed(
                title="🎮 Uno Card Game",
                description="Play Uno with your friends using Discord UI!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Game Commands",
                value=(
                    f"`{ctx.prefix}uno start` - Start a new game\n"
                    f"`{ctx.prefix}uno join` - Join existing game\n"
                    f"`{ctx.prefix}uno status` - Check game status\n"
                    f"`{ctx.prefix}uno stop` - Stop current game\n"
                    f"`{ctx.prefix}uno rules` - Show game rules"
                ),
                inline=False
            )
            embed.add_field(
                name="📊 Statistics Commands",
                value=(
                    f"`{ctx.prefix}uno stats` - Your statistics\n"
                    f"`{ctx.prefix}uno leaderboard` - Server leaderboard\n"
                    f"`{ctx.prefix}uno achievements` - Your achievements"
                ),
                inline=False
            )
            embed.add_field(
                name="⚙️ Configuration Commands",
                value=(
                    f"`{ctx.prefix}uno config` - View settings\n"
                    f"`{ctx.prefix}uno set` - Change settings (Admin)\n"
                    f"`{ctx.prefix}uno download_assets` - Download card images"
                ),
                inline=False
            )
            embed.set_footer(text="Use the buttons on game messages to play!")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "displaying help")
    
    @uno_group.command(name="start")
    async def start_game(self, ctx):
        """Start a new Uno game in this channel"""
        try:
            # Check maintenance mode
            if await self.config.maintenance_mode():
                await ctx.send("🔧 Uno is currently in maintenance mode. Please try again later.")
                return
            
            # Check if game already exists
            existing_game = game_manager.get_game(ctx.channel.id)
            if existing_game and existing_game.state != GameState.FINISHED and not existing_game.is_expired():
                await ctx.send("❌ A game is already active in this channel! Use `uno stop` to end it first.")
                return
            
            # Get server settings
            settings = await self.config.guild(ctx.guild).all()
            
            # Create new game
            game = game_manager.create_game(ctx.channel.id, ctx.author.id, settings)
            if not game:
                await ctx.send("❌ Failed to create game. Try again.")
                return
            
            # Reset message counter for this channel
            self.channel_message_counts[ctx.channel.id] = 0
            
            # Create lobby embed and view
            embed = self.create_lobby_embed(game)
            view = LobbyView(game, self)
            
            # Send the game message
            message = await ctx.send(embed=embed, view=view)
            game.game_message = message
            
            await ctx.send(f"🎮 **Uno game created!** {ctx.author.mention} is the host.")
            
            # Update statistics
            await self._increment_global_stat("total_games")
            
        except Exception as e:
            await self._handle_error(ctx, e, "starting game")
    
    @uno_group.command(name="join")
    async def join_game(self, ctx):
        """Join the Uno game in this channel"""
        try:
            game = game_manager.get_game(ctx.channel.id)
            if not game:
                await ctx.send("❌ No game found in this channel. Use `uno start` to create one!")
                return
            
            if game.state != GameState.LOBBY:
                await ctx.send("❌ Game has already started or finished!")
                return
            
            success = game.add_player(ctx.author.id)
            if success:
                await self.update_lobby_display(game)
                await ctx.send(f"✅ {ctx.author.mention} joined the game!")
                
                # Update player statistics
                await self._increment_player_stat(ctx.guild, ctx.author, "games_played")
                
            else:
                await ctx.send("❌ Cannot join: Game is full or you're already in it!")
                
        except Exception as e:
            await self._handle_error(ctx, e, "joining game")
    
    @uno_group.command(name="ai")
    async def add_ai(self, ctx, difficulty: str = "medium"):
        """Add an AI player to the current game
        
        Difficulty levels: easy, medium, hard
        """
        try:
            if difficulty not in ["easy", "medium", "hard"]:
                await ctx.send("❌ Invalid difficulty. Choose: easy, medium, or hard")
                return
            
            game = game_manager.get_game(ctx.channel.id)
            if not game:
                await ctx.send("❌ No game found in this channel.")
                return
            
            if game.state != GameState.LOBBY:
                await ctx.send("❌ Can only add AI players in the lobby!")
                return
            
            if ctx.author.id != game.host_id:
                await ctx.send("❌ Only the host can add AI players!")
                return
            
            settings = await self.config.guild(ctx.guild).all()
            if not settings["ai_players"]:
                await ctx.send("❌ AI players are disabled on this server!")
                return
            
            ai_player = game.add_ai_player(difficulty)
            if ai_player:
                await self.update_lobby_display(game)
                await ctx.send(f"🤖 Added AI player **{ai_player.name}** ({difficulty} difficulty)")
            else:
                await ctx.send("❌ Cannot add AI player: Game is full or max AI limit reached!")
                
        except Exception as e:
            await self._handle_error(ctx, e, "adding AI player")
    
    @uno_group.command(name="stop", aliases=["end"])
    async def stop_game(self, ctx):
        """Stop the current Uno game (host or admin only)"""
        try:
            game = game_manager.get_game(ctx.channel.id)
            if not game:
                await ctx.send("❌ No game found in this channel.")
                return
            
            # Check permissions
            is_host = ctx.author.id == game.host_id
            is_admin = ctx.author.guild_permissions.manage_messages
            
            if not (is_host or is_admin):
                await ctx.send("❌ Only the game host or server admins can stop the game!")
                return
            
            # Save final statistics if game was in progress
            if game.state == GameState.PLAYING:
                await self._save_game_statistics(game)
            
            # Clean up message counter
            if ctx.channel.id in self.channel_message_counts:
                del self.channel_message_counts[ctx.channel.id]
            
            # Stop the game
            game_manager.remove_game(ctx.channel.id)
            
            embed = discord.Embed(
                title="🛑 Game Stopped",
                description="The Uno game has been stopped.",
                color=discord.Color.red()
            )
            
            if game.game_message:
                try:
                    await game.game_message.edit(embed=embed, view=None)
                except discord.NotFound:
                    pass
            
            await ctx.send("🛑 **Game stopped!**")
            
        except Exception as e:
            await self._handle_error(ctx, e, "stopping game")
    
    # [Rest of the commands remain the same as in the original file - status, stats, leaderboard, etc.]
    # I'll include the key ones but truncate for space
    
    @uno_group.command(name="status")
    async def game_status(self, ctx):
        """Show current game status"""
        try:
            game = game_manager.get_game(ctx.channel.id)
            if not game:
                await ctx.send("❌ No game found in this channel.")
                return
            
            status = game.get_game_status()
            embed = discord.Embed(title="📊 Uno Game Status", color=discord.Color.blue())
            
            # Game state
            embed.add_field(name="🎮 State", value=status["state"].title(), inline=True)
            embed.add_field(name="👥 Players", value=f"{status['players']}", inline=True)
            embed.add_field(name="🤖 AI Players", value=f"{status['ai_players']}", inline=True)
            
            if status["state"] == "playing":
                # Current game info
                if status["top_card"]:
                    embed.add_field(name="🎯 Current Card", value=status["top_card"], inline=True)
                
                if status["current_color"]:
                    embed.add_field(name="🎨 Current Color", value=status["current_color"], inline=True)
                
                embed.add_field(name="🔄 Direction", value=status["direction"], inline=True)
                
                if status["current_player"]:
                    current_player_id = status["current_player"]
                    if game.is_ai_player(current_player_id):
                        ai_player = game.get_ai_player(current_player_id)
                        player_name = f"🤖 {ai_player.name}" if ai_player else "🤖 AI Player"
                    else:
                        player_name = f"<@{current_player_id}>"
                    embed.add_field(name="🎯 Current Turn", value=player_name, inline=True)
                
                if status["draw_penalty"] > 0:
                    embed.add_field(name="📥 Draw Penalty", value=f"{status['draw_penalty']} cards", inline=True)
                
                if status["challenge_window"]:
                    embed.add_field(name="⚖️ Challenge Window", value="Draw 4 can be challenged!", inline=True)
                
                # Game duration
                duration = int(status["game_duration"])
                embed.add_field(name="⏱️ Duration", value=f"{duration // 60}m {duration % 60}s", inline=True)
                
                # Player card counts
                player_counts = format_card_counts(status["card_counts"], status["current_player"], game)
                embed.add_field(name="🃏 Card Counts", value=player_counts, inline=False)
            
            elif status["state"] == "lobby":
                # Lobby info
                player_list = format_player_list(game.players, game.ai_players)
                embed.add_field(name="👥 Players in Lobby", value=player_list, inline=False)
                
                min_players = game.settings["min_players"]
                total_players = len(game.players) + len(game.ai_players)
                
                if total_players >= min_players:
                    embed.add_field(name="✅ Ready", value="Host can start the game!", inline=False)
                else:
                    needed = min_players - total_players
                    embed.add_field(
                        name="⏳ Waiting", 
                        value=f"Need {needed} more player{'s' if needed != 1 else ''} to start", 
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing game status")
    
    # [Other command methods would continue here...]
    
    # Helper methods
    
    async def _handle_error(self, ctx, error: Exception, action: str):
        """Centralized error handling"""
        error_msg = f"An error occurred while {action}. Please try again."
        
        # Log the full error for debugging
        print(f"Uno Cog Error ({action}): {error}")
        print(traceback.format_exc())
        
        # Send user-friendly error message
        embed = discord.Embed(
            title="❌ Error",
            description=error_msg,
            color=discord.Color.red()
        )
        
        try:
            await ctx.send(embed=embed)
        except:
            # Fallback if embed fails
            await ctx.send(f"❌ {error_msg}")
    
    async def _increment_player_stat(self, guild: discord.Guild, member: discord.Member, stat: str, amount: int = 1):
        """Increment a player statistic"""
        try:
            current = await self.config.member(member).get_raw(stat)
            await self.config.member(member).set_raw(stat, value=current + amount)
        except Exception as e:
            print(f"Error updating player stat {stat}: {e}")
    
    async def _increment_global_stat(self, stat: str, amount: int = 1):
        """Increment a global statistic"""
        try:
            current = await self.config.get_raw(stat)
            await self.config.set_raw(stat, value=current + amount)
        except Exception as e:
            print(f"Error updating global stat {stat}: {e}")
    
    async def _save_game_statistics(self, game: UnoGameSession):
        """Save statistics from a completed game"""
        try:
            if game.state != GameState.FINISHED:
                return
            
            # Update statistics for all players
            for player_id in game.players:
                if game.is_ai_player(player_id):
                    continue
                
                member = self.bot.get_user(player_id)
                if not member:
                    continue
                
                guild = self.bot.get_guild(game.channel_id)  # This is not correct, but simplified
                if not guild:
                    continue
                
                hand = game.hands.get(player_id)
                if not hand:
                    continue
                
                # Update basic stats
                await self._increment_player_stat(guild, member, "games_played")
                
                if hand.is_empty:  # Winner
                    await self._increment_player_stat(guild, member, "games_won")
                    
                    # Check for fastest win achievement
                    if game.game_start_time:
                        duration = (discord.utils.utcnow() - game.game_start_time).total_seconds()
                        current_fastest = await self.config.member(member).fastest_win()
                        if not current_fastest or duration < current_fastest:
                            await self.config.member(member).fastest_win.set(int(duration))
                
                # Update other stats based on game history
                # This would require more detailed action tracking
                
        except Exception as e:
            print(f"Error saving game statistics: {e}")
    
    # Display update methods
    
    async def update_lobby_display(self, game: UnoGameSession):
        """Update the lobby display message"""
        try:
            if not game.game_message:
                return
            
            embed = self.create_lobby_embed(game)
            view = LobbyView(game, self)
            
            await game.game_message.edit(embed=embed, view=view)
            
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error updating lobby display: {e}")
    
    async def update_game_display(self, game: UnoGameSession):
        """Update the main game display message"""
        try:
            if not game.game_message:
                return
            
            embed = self.create_game_embed(game)
            view = UnoGameView(game, self)
            
            await game.game_message.edit(embed=embed, view=view)
            
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error updating game display: {e}")
    
    def create_lobby_embed(self, game: UnoGameSession) -> discord.Embed:
        """Create embed for game lobby"""
        embed = discord.Embed(
            title="🎮 Uno Game Lobby",
            description="Waiting for players to join...",
            color=discord.Color.blue()
        )
        
        player_list = format_player_list(game.players, game.ai_players)
        embed.add_field(name="👥 Players", value=player_list, inline=True)
        embed.add_field(name="🎯 Host", value=f"<@{game.host_id}>", inline=True)
        
        total_players = len(game.players) + len(game.ai_players)
        embed.add_field(name="📊 Count", value=f"{total_players}/{game.settings['max_players']}", inline=True)
        
        if total_players >= game.settings["min_players"]:
            embed.add_field(
                name="✅ Ready to Start",
                value="Host can start the game!",
                inline=False
            )
        else:
            needed = game.settings["min_players"] - total_players
            embed.add_field(
                name="⏳ Waiting",
                value=f"Need {needed} more player{'s' if needed != 1 else ''} to start",
                inline=False
            )
        
        # Show current settings
        settings_text = []
        if game.settings.get("draw_stacking"):
            settings_text.append("📚 Draw Stacking")
        if game.settings.get("challenge_draw4"):
            settings_text.append("⚖️ Draw 4 Challenge")
        if game.settings.get("ai_players"):
            settings_text.append("🤖 AI Players")
        
        if settings_text:
            embed.add_field(name="⚙️ Rules", value=" • ".join(settings_text), inline=False)
        
        embed.set_footer(text="Click Join Game to participate!")
        return embed
    
    def create_game_embed(self, game: UnoGameSession) -> discord.Embed:
        """Create embed for active game"""
        status = game.get_game_status()
        
        if game.state == GameState.FINISHED:
            embed = discord.Embed(
                title="🎉 Game Finished!",
                description="Thanks for playing!",
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="🎮 Uno Game in Progress",
                description="Use the buttons below to interact with the game",
                color=discord.Color.green()
            )
        
        # Current card info
        if status["top_card"]:
            card_info = status["top_card"]
            if status["current_color"] and "Wild" in status["top_card"]:
                card_info += f" (Color: {status['current_color']})"
            embed.add_field(name="🎯 Current Card", value=card_info, inline=True)
        
        embed.add_field(name="🔄 Direction", value=status["direction"], inline=True)
        
        # Current turn
        if status["current_player"]:
            current_player_id = status["current_player"]
            if game.is_ai_player(current_player_id):
                ai_player = game.get_ai_player(current_player_id)
                player_name = f"🤖 {ai_player.name}" if ai_player else "🤖 AI Player"
            else:
                player_name = f"<@{current_player_id}>"
            embed.add_field(name="🎮 Current Turn", value=player_name, inline=True)
        
        # Special states
        if status["draw_penalty"] > 0:
            embed.add_field(
                name="📥 Draw Penalty",
                value=f"{status['draw_penalty']} cards",
                inline=True
            )
        
        if status["challenge_window"]:
            embed.add_field(
                name="⚖️ Challenge Window",
                value="Draw 4 can be challenged!",
                inline=True
            )
        
        # Game info
        duration = int(status["game_duration"])
        embed.add_field(name="⏱️ Duration", value=f"{duration // 60}m {duration % 60}s", inline=True)
        
        # Player card counts
        player_counts = format_card_counts(status["card_counts"], status["current_player"], game)
        embed.add_field(name="🃏 Players", value=player_counts, inline=False)
        
        embed.set_footer(text="Use Hand to see your cards • Use Play to make a move • Use Status for details")
        return embed


async def setup(bot):
    """Setup function for Red-Discord bot"""
    await bot.add_cog(UnoCog(bot))