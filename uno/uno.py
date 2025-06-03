"""
Uno Game Cog for Red-Discord Bot
"""
import asyncio
import discord
from discord.ext import commands, tasks
from typing import Optional
from redbot.core.data_manager import cog_data_path

from .game import UnoGameSession, GameState
from .views import UnoGameView, LobbyView
from .utils import (
    setup_assets_directory, 
    game_manager, 
    format_player_list, 
    format_card_counts,
    validate_card_files,
    cleanup_temp_files
)
from .cards import UnoColor


class UnoCog(commands.Cog):
    """Uno card game cog with Discord UI integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.assets_path = setup_assets_directory(cog_data_path(self))
        
        # Start background tasks
        self.cleanup_task.start()
        
        # Add persistent views
        self.bot.add_view(UnoGameView(None, self))
        self.bot.add_view(LobbyView(None, self))
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.cleanup_task.cancel()
        
        # Clean up all games
        for game in list(game_manager.games.values()):
            game.cleanup()
        game_manager.games.clear()
    
    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """Periodic cleanup task"""
        # Clean up expired games
        expired_count = game_manager.cleanup_expired_games()
        if expired_count > 0:
            print(f"Cleaned up {expired_count} expired Uno games")
        
        # Clean up temporary image files
        await cleanup_temp_files(self.assets_path)
    
    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        await self.bot.wait_until_ready()
    
    @commands.group(name="uno", invoke_without_command=True)
    async def uno_group(self, ctx):
        """Uno card game commands"""
        await ctx.send_help(ctx.command)
    
    @uno_group.command(name="start")
    async def start_game(self, ctx):
        """Start a new Uno game in this channel"""
        channel_id = ctx.channel.id
        host_id = ctx.author.id
        
        # Check if game already exists
        existing_game = game_manager.get_game(channel_id)
        if existing_game and existing_game.state != GameState.FINISHED:
            await ctx.send("❌ A game is already running in this channel! Use `uno join` to join or `uno stop` to end it.")
            return
        
        # Create new game
        game = game_manager.create_game(channel_id, host_id)
        if not game:
            await ctx.send("❌ Failed to create game. Please try again.")
            return
        
        # Create lobby embed and view
        embed = self.create_lobby_embed(game)
        view = LobbyView(game, self)
        
        message = await ctx.send(embed=embed, view=view)
        game.game_message = message
        
        await ctx.send(f"🎮 **Uno Game Created!**\n{ctx.author.mention} is hosting. Click **Join Game** to participate!")
    
    @uno_group.command(name="join")
    async def join_game(self, ctx):
        """Join the Uno game in this channel"""
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
        else:
            await ctx.send("❌ Cannot join: Game is full or you're already in it!")
    
    @uno_group.command(name="stop", aliases=["end"])
    async def stop_game(self, ctx):
        """Stop the current Uno game (host or admin only)"""
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
        
        # Stop the game
        game_manager.remove_game(ctx.channel.id)
        
        embed = discord.Embed(
            title="🛑 Game Stopped",
            description="The Uno game has been stopped by an administrator.",
            color=discord.Color.red()
        )
        
        if game.game_message:
            try:
                await game.game_message.edit(embed=embed, view=None)
            except discord.NotFound:
                pass
        
        await ctx.send("🛑 **Game stopped!**")
    
    @uno_group.command(name="status")
    async def game_status(self, ctx):
        """Show current game status"""
        game = game_manager.get_game(ctx.channel.id)
        if not game:
            await ctx.send("❌ No game found in this channel.")
            return
        
        status = game.get_game_status()
        embed = discord.Embed(title="📊 Uno Game Status", color=discord.Color.blue())
        
        # Game state
        embed.add_field(name="🎮 State", value=status["state"].title(), inline=True)
        embed.add_field(name="👥 Players", value=status["players"], inline=True)
        
        if status["state"] == "playing":
            # Current game info
            if status["top_card"]:
                embed.add_field(name="🎯 Current Card", value=status["top_card"], inline=True)
            
            if status["current_color"]:
                embed.add_field(name="🎨 Current Color", value=status["current_color"], inline=True)
            
            embed.add_field(name="🔄 Direction", value=status["direction"], inline=True)
            
            if status["current_player"]:
                embed.add_field(name="🎯 Current Turn", value=f"<@{status['current_player']}>", inline=True)
            
            if status["draw_penalty"] > 0:
                embed.add_field(name="📥 Draw Penalty", value=f"{status['draw_penalty']} cards", inline=True)
            
            # Player card counts
            player_counts = format_card_counts(status["card_counts"], status["current_player"])
            embed.add_field(name="🃏 Card Counts", value=player_counts, inline=False)
        
        elif status["state"] == "lobby":
            # Lobby info
            player_list = format_player_list(game.players)
            embed.add_field(name="👥 Players in Lobby", value=player_list, inline=False)
            embed.add_field(
                name="ℹ️ Info", 
                value=f"Waiting for {game.min_players - len(game.players)} more players to start", 
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @uno_group.command(name="stats")
    async def show_stats(self, ctx):
        """Show bot-wide Uno statistics"""
        embed = discord.Embed(title="📈 Uno Bot Statistics", color=discord.Color.gold())
        
        active_games = game_manager.get_active_games_count()
        total_games = len(game_manager.games)
        total_players = game_manager.get_total_players()
        
        embed.add_field(name="🎮 Active Games", value=active_games, inline=True)
        embed.add_field(name="📊 Total Games", value=total_games, inline=True)
        embed.add_field(name="👥 Total Players", value=total_players, inline=True)
        
        # Check card assets
        missing_files, existing_files = validate_card_files(self.assets_path)
        assets_status = f"✅ {len(existing_files)} files" if not missing_files else f"⚠️ {len(missing_files)} missing"
        embed.add_field(name="🖼️ Card Assets", value=assets_status, inline=True)
        
        if missing_files:
            embed.add_field(
                name="❌ Missing Card Files",
                value=f"{len(missing_files)} files missing (check assets folder)",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @uno_group.command(name="download_assets")
    async def download_assets(self, ctx):
        """Download Uno card assets from GitHub repository"""
        try:
            import aiohttp
        except ImportError:
            await ctx.send("❌ `aiohttp` is required for downloading assets. Please install it with `pip install aiohttp`")
            return
        
        base_url = "https://raw.githubusercontent.com/AfterWorld/ultcogs/main/uno/assets/"
        
        # List of all required card files based on Uno deck
        card_files = []
        
        # Number cards for each color
        colors = ["Red", "Green", "Yellow", "Blue"]
        for color in colors:
            for num in range(10):  # 0-9
                card_files.append(f"{color}_{num}.png")
            # Action cards
            card_files.extend([
                f"{color}_skip.png",
                f"{color}_reverse.png", 
                f"{color}_draw2.png"
            ])
        
        # Wild cards
        card_files.extend(["Wild_Card.png", "Wild_draw4.png"])
        
        embed = discord.Embed(
            title="🎴 Downloading Card Assets",
            description=f"Downloading {len(card_files)} card images...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        downloaded = 0
        failed = []
        
        async with aiohttp.ClientSession() as session:
            for filename in card_files:
                try:
                    url = base_url + filename
                    async with session.get(url) as response:
                        if response.status == 200:
                            file_path = self.assets_path / filename
                            with open(file_path, 'wb') as f:
                                f.write(await response.read())
                            downloaded += 1
                        else:
                            failed.append(f"{filename} (Status: {response.status})")
                except Exception as e:
                    failed.append(f"{filename} (Error: {str(e)})")
                
                # Update progress every 10 files
                if downloaded % 10 == 0:
                    embed.description = f"Downloaded {downloaded}/{len(card_files)} files..."
                    try:
                        await message.edit(embed=embed)
                    except:
                        pass
        
        # Final result
        if downloaded == len(card_files):
            embed = discord.Embed(
                title="✅ Assets Downloaded Successfully!",
                description=f"Downloaded all {downloaded} card images to assets folder.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="⚠️ Download Completed with Issues",
                description=f"Downloaded {downloaded}/{len(card_files)} files.",
                color=discord.Color.orange()
            )
            if failed:
                failed_list = "\n".join(failed[:10])  # Show first 10 failures
                if len(failed) > 10:
                    failed_list += f"\n... and {len(failed) - 10} more"
                embed.add_field(name="Failed Downloads", value=failed_list, inline=False)
        
        embed.set_footer(text="You can now use 'uno start' to begin playing!")
        await message.edit(embed=embed)
    
    @uno_group.command(name="rules")
    async def show_rules(self, ctx):
        """Show Uno game rules and how to play"""
        embed = discord.Embed(title="📋 Uno Rules & How to Play", color=discord.Color.purple())
        
        embed.add_field(
            name="🎯 Objective",
            value="Be the first player to play all your cards!",
            inline=False
        )
        
        embed.add_field(
            name="🎮 How to Play",
            value=(
                "• Use `uno start` to create a game\n"
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
                "• Shout **UNO** when you have one card left! (automatic)\n"
                "• If you can't play, you must draw a card\n"
                "• Wild cards can be played on anything\n"
                "• Must declare color when playing wild cards"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Helper methods for updating displays
    
    async def update_lobby_display(self, game: UnoGameSession):
        """Update the lobby display message"""
        if not game.game_message:
            return
        
        embed = self.create_lobby_embed(game)
        view = LobbyView(game, self)
        
        try:
            await game.game_message.edit(embed=embed, view=view)
        except discord.NotFound:
            pass
    
    async def update_game_display(self, game: UnoGameSession):
        """Update the main game display message"""
        if not game.game_message:
            return
        
        embed = self.create_game_embed(game)
        view = UnoGameView(game, self)
        
        try:
            await game.game_message.edit(embed=embed, view=view)
        except discord.NotFound:
            pass
    
    def create_lobby_embed(self, game: UnoGameSession) -> discord.Embed:
        """Create embed for game lobby"""
        embed = discord.Embed(
            title="🎮 Uno Game Lobby",
            description="Waiting for players to join...",
            color=discord.Color.blue()
        )
        
        player_list = format_player_list(game.players)
        embed.add_field(name="👥 Players", value=player_list, inline=True)
        embed.add_field(name="🎯 Host", value=f"<@{game.host_id}>", inline=True)
        embed.add_field(name="📊 Count", value=f"{len(game.players)}/{game.max_players}", inline=True)
        
        if len(game.players) >= game.min_players:
            embed.add_field(
                name="✅ Ready to Start",
                value="Host can start the game!",
                inline=False
            )
        else:
            needed = game.min_players - len(game.players)
            embed.add_field(
                name="⏳ Waiting",
                value=f"Need {needed} more player{'s' if needed != 1 else ''} to start",
                inline=False
            )
        
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
            embed.add_field(name="🎮 Current Turn", value=f"<@{status['current_player']}>", inline=True)
        
        # Draw penalty
        if status["draw_penalty"] > 0:
            embed.add_field(
                name="📥 Draw Penalty",
                value=f"{status['draw_penalty']} cards",
                inline=True
            )
        
        # Player card counts
        player_counts = format_card_counts(status["card_counts"], status["current_player"])
        embed.add_field(name="🃏 Players", value=player_counts, inline=False)
        
        embed.set_footer(text="Use Hand to see your cards • Use Play to make a move • Use Status for details")
        return embed


async def setup(bot):
    """Setup function for Red-Discord bot"""
    cog = UnoCog(bot)
    await bot.add_cog(cog)

