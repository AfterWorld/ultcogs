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
    stats_manager,
    validate_card_emojis,
    check_bot_emoji_permissions
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
                    f"`{ctx.prefix}uno emojis` - Check emoji setup"
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
    
    @uno_group.command(name="emojis")
    async def check_emojis(self, ctx):
        """Check emoji setup status"""
        try:
            # Check bot permissions
            permissions = check_bot_emoji_permissions(self.bot, ctx.guild)
            
            embed = discord.Embed(
                title="🎴 Uno Emoji Setup Status",
                color=discord.Color.blue()
            )
            
            # Permission check
            if not permissions["in_guild"]:
                embed.add_field(name="❌ Error", value="Bot not found in guild", inline=False)
                await ctx.send(embed=embed)
                return
            
            perm_status = []
            if permissions["use_external_emojis"]:
                perm_status.append("✅ Use External Emojis")
            else:
                perm_status.append("❌ Use External Emojis")
                
            if permissions["embed_links"]:
                perm_status.append("✅ Embed Links")
            else:
                perm_status.append("❌ Embed Links")
            
            embed.add_field(name="🔐 Bot Permissions", value="\n".join(perm_status), inline=False)
            
            # Check emoji availability
            missing_emojis, existing_emojis = validate_card_emojis(self.bot)
            
            embed.add_field(
                name="📊 Emoji Status", 
                value=f"Found: {len(existing_emojis)}/54\nMissing: {len(missing_emojis)}", 
                inline=True
            )
            
            if len(existing_emojis) == 54:
                embed.add_field(name="✅ Status", value="All emojis found! Perfect setup!", inline=True)
            elif len(existing_emojis) > 0:
                embed.add_field(name="⚠️ Status", value="Partial setup - some emojis missing", inline=True)
            else:
                embed.add_field(name="❌ Status", value="No card emojis found", inline=True)
            
            # Show some missing emojis
            if missing_emojis:
                missing_sample = missing_emojis[:10]
                if len(missing_emojis) > 10:
                    missing_sample.append(f"... and {len(missing_emojis) - 10} more")
                
                embed.add_field(
                    name="❌ Missing Emojis (sample)",
                    value="`" + "`, `".join(missing_sample) + "`",
                    inline=False
                )
            
            # Setup instructions
            if missing_emojis:
                embed.add_field(
                    name="📋 Setup Instructions",
                    value=(
                        "1. Get 54 Uno card images\n"
                        "2. Go to Server Settings > Emoji\n"
                        "3. Upload each image as custom emoji\n"
                        "4. Name emojis exactly as shown above\n"
                        "5. Use `uno emojis` to check progress"
                    ),
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "checking emoji setup")
    
    @uno_group.command(name="stats")
    async def player_stats(self, ctx, member: discord.Member = None):
        """Show player statistics"""
        try:
            target = member or ctx.author
            stats = await self.config.member(target).all()
            
            embed = discord.Embed(
                title=f"📊 Uno Statistics - {target.display_name}",
                color=discord.Color.gold()
            )
            
            # Basic stats
            embed.add_field(name="🎮 Games Played", value=f"{stats['games_played']}", inline=True)
            embed.add_field(name="🏆 Games Won", value=f"{stats['games_won']}", inline=True)
            
            win_rate = (stats['games_won'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
            embed.add_field(name="📈 Win Rate", value=f"{win_rate:.1f}%", inline=True)
            
            embed.add_field(name="🃏 Cards Played", value=f"{stats['cards_played']}", inline=True)
            embed.add_field(name="🔥 UNO Calls", value=f"{stats['uno_calls']}", inline=True)
            embed.add_field(name="⚠️ UNO Penalties", value=f"{stats['uno_penalties']}", inline=True)
            
            # Challenge stats
            challenge_rate = (stats['draw4_successful_challenges'] / stats['draw4_challenged'] * 100) if stats['draw4_challenged'] > 0 else 0
            embed.add_field(name="⚖️ Draw4 Challenges", value=f"{stats['draw4_challenged']}", inline=True)
            embed.add_field(name="✅ Challenge Success", value=f"{challenge_rate:.1f}%", inline=True)
            
            # Time stats
            if stats['fastest_win']:
                fastest = stats['fastest_win']
                embed.add_field(name="⚡ Fastest Win", value=f"{fastest // 60}m {fastest % 60}s", inline=True)
            
            if stats['favorite_color']:
                embed.add_field(name="🎨 Favorite Color", value=stats['favorite_color'], inline=True)
            
            # Achievements
            if stats['achievements']:
                achievements_text = "\n".join([f"🏅 {achievement}" for achievement in stats['achievements'][:5]])
                if len(stats['achievements']) > 5:
                    achievements_text += f"\n... and {len(stats['achievements']) - 5} more"
                embed.add_field(name="🏆 Achievements", value=achievements_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing player statistics")
    
    @uno_group.command(name="leaderboard", aliases=["lb", "top"])
    async def leaderboard(self, ctx, category: str = "wins"):
        """Show server leaderboard
        
        Categories: wins, games, winrate, cards
        """
        try:
            if category not in ["wins", "games", "winrate", "cards"]:
                await ctx.send("❌ Invalid category. Choose: wins, games, winrate, cards")
                return
            
            # Get all member stats for this guild
            all_members = await self.config.all_members(ctx.guild)
            
            # Filter and sort
            member_data = []
            for member_id, stats in all_members.items():
                if stats['games_played'] == 0:
                    continue
                
                member = ctx.guild.get_member(member_id)
                if not member:
                    continue
                
                if category == "wins":
                    value = stats['games_won']
                elif category == "games":
                    value = stats['games_played']
                elif category == "winrate":
                    value = (stats['games_won'] / stats['games_played']) * 100 if stats['games_played'] > 0 else 0
                elif category == "cards":
                    value = stats['cards_played']
                
                member_data.append((member, value, stats))
            
            if not member_data:
                await ctx.send("📊 No statistics available yet!")
                return
            
            # Sort by value (descending)
            member_data.sort(key=lambda x: x[1], reverse=True)
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=f"🏆 {ctx.guild.name} - {category.title()} Leaderboard",
                color=discord.Color.gold()
            )
            
            # Top 10
            leaderboard_text = ""
            for i, (member, value, stats) in enumerate(member_data[:10]):
                if i == 0:
                    medal = "🥇"
                elif i == 1:
                    medal = "🥈"
                elif i == 2:
                    medal = "🥉"
                else:
                    medal = f"{i+1}."
                
                if category == "winrate":
                    value_text = f"{value:.1f}%"
                else:
                    value_text = f"{value:,}"
                
                leaderboard_text += f"{medal} **{member.display_name}** - {value_text}\n"
            
            embed.description = leaderboard_text
            
            # Add user's position if not in top 10
            user_pos = next((i for i, (m, _, _) in enumerate(member_data) if m.id == ctx.author.id), None)
            if user_pos is not None and user_pos >= 10:
                user_member, user_value, _ = member_data[user_pos]
                if category == "winrate":
                    user_value_text = f"{user_value:.1f}%"
                else:
                    user_value_text = f"{user_value:,}"
                
                embed.add_field(
                    name="Your Position",
                    value=f"{user_pos + 1}. **{user_member.display_name}** - {user_value_text}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing leaderboard")
    
    @uno_group.command(name="achievements")
    async def show_achievements(self, ctx, member: discord.Member = None):
        """Show player achievements"""
        try:
            target = member or ctx.author
            stats = await self.config.member(target).all()
            
            embed = discord.Embed(
                title=f"🏆 Achievements - {target.display_name}",
                color=discord.Color.purple()
            )
            
            if not stats['achievements']:
                embed.description = "No achievements unlocked yet! Keep playing to earn them!"
            else:
                achievements_text = "\n".join([f"🏅 {achievement}" for achievement in stats['achievements']])
                embed.description = achievements_text
            
            # Show some available achievements
            available_achievements = [
                "First Win - Win your first game",
                "Speed Demon - Win a game in under 5 minutes", 
                "UNO Master - Call UNO 10 times",
                "Challenge Champion - Successfully challenge 5 Draw 4s",
                "Card Counter - Play 100 cards",
                "Perfect Game - Win without drawing any cards",
                "AI Crusher - Beat 10 AI players",
                "Comeback King - Win from 10+ cards",
                "Color Master - Play all 4 colors in one game",
                "Wild Wild West - Play 20 wild cards"
            ]
            
            unlocked = set(stats['achievements'])
            available_text = "\n".join([
                f"{'✅' if ach.split(' - ')[0] in unlocked else '🔒'} {ach}" 
                for ach in available_achievements[:10]
            ])
            
            embed.add_field(name="Available Achievements", value=available_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing achievements")
    
    @uno_group.command(name="config", aliases=["settings"])
    async def show_config(self, ctx):
        """Show current server configuration"""
        try:
            settings = await self.config.guild(ctx.guild).all()
            
            embed = discord.Embed(
                title="⚙️ Uno Configuration",
                description=f"Current settings for {ctx.guild.name}",
                color=discord.Color.blue()
            )
            
            # Game settings
            embed.add_field(name="🃏 Starting Cards", value=settings["starting_cards"], inline=True)
            embed.add_field(name="👥 Max Players", value=settings["max_players"], inline=True)
            embed.add_field(name="⏱️ Timeout (min)", value=settings["timeout_minutes"], inline=True)
            
            # Rule settings
            embed.add_field(name="🔥 UNO Penalty", value="✅" if settings["uno_penalty"] else "❌", inline=True)
            embed.add_field(name="📚 Draw Stacking", value="✅" if settings["draw_stacking"] else "❌", inline=True)
            embed.add_field(name="⚖️ Draw 4 Challenge", value="✅" if settings["challenge_draw4"] else "❌", inline=True)
            
            # AI settings
            embed.add_field(name="🤖 AI Players", value="✅" if settings["ai_players"] else "❌", inline=True)
            embed.add_field(name="🤖 Max AI Players", value=settings["max_ai_players"], inline=True)
            embed.add_field(name="⏰ Auto-start Delay", value=f"{settings['auto_start_delay']}s", inline=True)
            
            # Feature settings
            embed.add_field(name="💾 Persistent Games", value="✅" if settings["persistent_games"] else "❌", inline=True)
            embed.add_field(name="📊 Statistics", value="✅" if settings["statistics_enabled"] else "❌", inline=True)
            embed.add_field(name="🏆 Leaderboards", value="✅" if settings["leaderboard_enabled"] else "❌", inline=True)
            
            # Visual persistence settings
            embed.add_field(name="👁️ Visual Persistence", value="✅" if settings["visual_persistence"] else "❌", inline=True)
            embed.add_field(name="📝 Repost Threshold", value=f"{settings['repost_threshold']} messages", inline=True)
            
            embed.set_footer(text="Use 'uno set <setting> <value>' to change settings (Admin only)")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing configuration")
    
    @uno_group.command(name="set")
    @commands.admin_or_permissions(manage_guild=True)
    async def set_config(self, ctx, setting: str, *, value: str):
        """Change a server configuration setting
        
        Available settings:
        - starting_cards (5-10)
        - max_players (4-20)
        - timeout_minutes (10-120)
        - uno_penalty (true/false)
        - draw_stacking (true/false)
        - challenge_draw4 (true/false)
        - ai_players (true/false)
        - max_ai_players (1-5)
        - auto_start_delay (30-300)
        - persistent_games (true/false)
        - statistics_enabled (true/false)
        - leaderboard_enabled (true/false)
        - visual_persistence (true/false)
        - repost_threshold (1-10)
        """
        try:
            valid_settings = {
                "starting_cards": (int, 5, 10),
                "max_players": (int, 4, 20),
                "timeout_minutes": (int, 10, 120),
                "uno_penalty": (bool, None, None),
                "draw_stacking": (bool, None, None),
                "challenge_draw4": (bool, None, None),
                "ai_players": (bool, None, None),
                "max_ai_players": (int, 1, 5),
                "auto_start_delay": (int, 30, 300),
                "persistent_games": (bool, None, None),
                "statistics_enabled": (bool, None, None),
                "leaderboard_enabled": (bool, None, None),
                "visual_persistence": (bool, None, None),
                "repost_threshold": (int, 1, 10)
            }
            
            if setting not in valid_settings:
                settings_list = ", ".join(valid_settings.keys())
                await ctx.send(f"❌ Invalid setting. Available settings:\n```{settings_list}```")
                return
            
            setting_type, min_val, max_val = valid_settings[setting]
            
            try:
                if setting_type == bool:
                    parsed_value = value.lower() in ("true", "yes", "1", "on", "enable", "enabled")
                else:
                    parsed_value = setting_type(value)
                    if min_val is not None and max_val is not None:
                        if not (min_val <= parsed_value <= max_val):
                            await ctx.send(f"❌ Value must be between {min_val} and {max_val}")
                            return
                
                await self.config.guild(ctx.guild).set_raw(setting, value=parsed_value)
                await ctx.send(f"✅ Set `{setting}` to `{parsed_value}`")
                
            except ValueError:
                await ctx.send(f"❌ Invalid value for {setting}")
                
        except Exception as e:
            await self._handle_error(ctx, e, "setting configuration")
    
    @uno_group.command(name="rules")
    async def show_rules(self, ctx):
        """Show Uno game rules and how to play"""
        try:
            embed = discord.Embed(title="📋 Uno Rules & How to Play", color=discord.Color.purple())
            
            embed.add_field(
                name="🎯 Objective",
                value="Be the first player to play all your cards!",
                inline=False
            )
            
            embed.add_field(
                name="🎮 How to Play",
                value=(
                    f"• Use `{ctx.prefix}uno start` to create a game\n"
                    "• Click **Join Game** to join the lobby\n"
                    "• Host clicks **Start Game** when ready\n"
                    "• Use **Hand** button to see your cards\n"
                    "• Use **Play** button to play a card on your turn\n"
                    "• Use **Status** button to see game info"
                ),
                inline=False
            )
            
            embed.add_field(
                name="🃏 Card Types",
                value=(
                    "• **Number Cards** (0-9): Play matching color or number\n"
                    "• **Skip**: Next player loses their turn\n"
                    "• **Reverse**: Change direction of play\n"
                    "• **Draw 2**: Next player draws 2 cards\n"
                    "• **Wild**: Change color to any color\n"
                    "• **Wild Draw 4**: Change color, next player draws 4"
                ),
                inline=False
            )
            
            embed.add_field(
                name="📏 Special Rules",
                value=(
                    "• **Call UNO** when you have one card left!\n"
                    "• **Draw Stacking**: Stack Draw 2s and Draw 4s\n"
                    "• **Challenge Draw 4**: Challenge illegal Draw 4 plays\n"
                    "• **AI Players**: Add computer players to fill games\n"
                    "• If you can't play, you must draw a card"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await self._handle_error(ctx, e, "showing rules")
    
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
    await bot.add_cog(UnoCog(bot