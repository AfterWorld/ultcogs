# buckshot.py
import discord
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import box, humanize_list
from redbot.core.utils.predicates import MessagePredicate
import random
import asyncio
from typing import Dict, List, Optional, Tuple
import logging
from enum import Enum
from datetime import datetime, timedelta

log = logging.getLogger("red.ultcogs.buckshot")

class BulletType(Enum):
    LIVE = "🔴"
    BLANK = "⚫"

class ItemType(Enum):
    SKIP = "🥫"      # Skip bullet
    MAGNIFIER = "🔍"  # See bullet type
    GLOVES = "🧤"     # Skip opponent's turn
    SAW = "🪚"        # Double damage
    BEER = "🍾"       # Heal one heart

class GameState(Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"

class BuckshotGame:
    """Represents a single Buckshot game instance"""
    
    def __init__(self, channel_id: int, player1: discord.Member, player2: discord.Member):
        self.channel_id = channel_id
        self.players = {player1.id: player1, player2.id: player2}
        self.player_ids = [player1.id, player2.id]
        self.current_player_index = 0
        
        # Game state
        self.state = GameState.ACTIVE
        self.lives = {player1.id: 5, player2.id: 5}
        self.items = {
            player1.id: [ItemType.SKIP, ItemType.MAGNIFIER, ItemType.GLOVES, ItemType.SAW, ItemType.BEER],
            player2.id: [ItemType.SKIP, ItemType.MAGNIFIER, ItemType.GLOVES, ItemType.SAW, ItemType.BEER]
        }
        
        # Shotgun state
        self.chamber = []
        self.chamber_position = 0
        self.saw_active = False
        self.current_bullet_known = False
        self.known_bullet_type = None
        
        # Game tracking
        self.start_time = datetime.utcnow()
        self.last_action_time = datetime.utcnow()
        self.turn_count = 0
        
        self._generate_chamber()
    
    def _generate_chamber(self):
        """Generate a new chamber with random bullets"""
        chamber_size = random.randint(4, 8)
        live_bullets = random.randint(1, chamber_size - 1)
        blank_bullets = chamber_size - live_bullets
        
        self.chamber = ([BulletType.LIVE] * live_bullets + 
                       [BulletType.BLANK] * blank_bullets)
        random.shuffle(self.chamber)
        self.chamber_position = 0
        self.current_bullet_known = False
        self.known_bullet_type = None
        
        log.info(f"Generated chamber: {len(self.chamber)} bullets, {live_bullets} live, {blank_bullets} blank")
    
    @property
    def current_player_id(self) -> int:
        """Get the current player's ID"""
        return self.player_ids[self.current_player_index]
    
    @property
    def current_player(self) -> discord.Member:
        """Get the current player"""
        return self.players[self.current_player_id]
    
    @property
    def opponent_id(self) -> int:
        """Get the opponent's ID"""
        return self.player_ids[1 - self.current_player_index]
    
    @property
    def opponent(self) -> discord.Member:
        """Get the opponent"""
        return self.players[self.opponent_id]
    
    def next_turn(self):
        """Switch to the next player's turn"""
        self.current_player_index = 1 - self.current_player_index
        self.turn_count += 1
        self.last_action_time = datetime.utcnow()
    
    def use_item(self, player_id: int, item: ItemType) -> bool:
        """Use an item if the player has it"""
        if item in self.items[player_id]:
            self.items[player_id].remove(item)
            return True
        return False
    
    def get_current_bullet(self) -> Optional[BulletType]:
        """Get the current bullet if chamber isn't empty"""
        if self.chamber_position < len(self.chamber):
            return self.chamber[self.chamber_position]
        return None
    
    def fire_bullet(self) -> Optional[BulletType]:
        """Fire the current bullet and advance chamber"""
        if self.chamber_position < len(self.chamber):
            bullet = self.chamber[self.chamber_position]
            self.chamber_position += 1
            self.current_bullet_known = False
            self.known_bullet_type = None
            return bullet
        return None
    
    def is_chamber_empty(self) -> bool:
        """Check if chamber is empty"""
        return self.chamber_position >= len(self.chamber)
    
    def get_winner(self) -> Optional[discord.Member]:
        """Get the winner if game is finished"""
        for player_id, lives in self.lives.items():
            if lives <= 0:
                # Return the other player as winner
                winner_id = self.opponent_id if player_id == self.current_player_id else self.current_player_id
                return self.players[winner_id]
        return None
    
    def get_game_status_embed(self) -> discord.Embed:
        """Generate game status embed"""
        embed = discord.Embed(
            title="🎯 Buckshot Game",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Player status
        p1_id, p2_id = self.player_ids
        p1_lives = "❤️" * self.lives[p1_id]
        p2_lives = "❤️" * self.lives[p2_id]
        
        p1_items = "".join([item.value for item in self.items[p1_id]])
        p2_items = "".join([item.value for item in self.items[p2_id]])
        
        embed.add_field(
            name=f"👤 {self.players[p1_id].display_name}",
            value=f"**Lives:** {p1_lives}\n**Items:** {p1_items}",
            inline=True
        )
        embed.add_field(
            name=f"👤 {self.players[p2_id].display_name}",
            value=f"**Lives:** {p2_lives}\n**Items:** {p2_items}",
            inline=True
        )
        
        # Current turn indicator
        current_player_emoji = "🎯" if self.current_player_id == p1_id else "👤"
        opponent_emoji = "👤" if self.current_player_id == p1_id else "🎯"
        
        embed.add_field(
            name="🎮 Current Turn",
            value=f"{current_player_emoji} **{self.current_player.display_name}**",
            inline=False
        )
        
        # Chamber info
        remaining_bullets = len(self.chamber) - self.chamber_position
        if remaining_bullets > 0:
            bullet_display = "🔫 " + "●" * remaining_bullets
            if self.current_bullet_known and self.known_bullet_type:
                bullet_display += f"\n**Next bullet:** {self.known_bullet_type.value}"
        else:
            bullet_display = "🔫 *Chamber empty - reloading...*"
        
        embed.add_field(
            name="🔫 Chamber",
            value=bullet_display,
            inline=False
        )
        
        # Special effects
        effects = []
        if self.saw_active:
            effects.append("🪚 **Saw Active** - Next live bullet deals 2 damage")
        
        if effects:
            embed.add_field(
                name="⚡ Active Effects",
                value="\n".join(effects),
                inline=False
            )
        
        return embed

class Buckshot(commands.Cog):
    """
    Buckshot - A strategic Russian Roulette game with items and multiplayer support.
    
    Play intense 1v1 matches with items that can change the game's outcome!
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890987654321, force_registration=True)
        
        # Default settings
        self.config.register_global(
            max_games_per_channel=2,
            game_timeout_minutes=30,
            allow_spectators=True
        )
        
        self.config.register_guild(
            enabled=True,
            allowed_channels=[],
            banned_users=[]
        )
        
        self.config.register_user(
            games_played=0,
            games_won=0,
            total_shots_fired=0,
            items_used=0,
            favorite_item=None
        )
        
        # Active games storage
        self.active_games: Dict[int, BuckshotGame] = {}
        self.pending_challenges: Dict[int, Tuple[discord.Member, datetime]] = {}
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_games())
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()
    
    async def _cleanup_expired_games(self):
        """Background task to clean up expired games"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                timeout_minutes = await self.config.game_timeout_minutes()
                timeout_delta = timedelta(minutes=timeout_minutes)
                current_time = datetime.utcnow()
                
                # Clean up expired games
                expired_games = []
                for channel_id, game in self.active_games.items():
                    if current_time - game.last_action_time > timeout_delta:
                        expired_games.append(channel_id)
                
                for channel_id in expired_games:
                    game = self.active_games.pop(channel_id)
                    try:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            embed = discord.Embed(
                                title="⏰ Game Timeout",
                                description="The Buckshot game has been automatically ended due to inactivity.",
                                color=discord.Color.orange()
                            )
                            await channel.send(embed=embed)
                    except Exception:
                        pass
                
                # Clean up expired challenges
                expired_challenges = []
                for channel_id, (challenger, challenge_time) in self.pending_challenges.items():
                    if current_time - challenge_time > timedelta(minutes=5):
                        expired_challenges.append(channel_id)
                
                for channel_id in expired_challenges:
                    self.pending_challenges.pop(channel_id)
                
            except Exception as e:
                log.error(f"Error in cleanup task: {e}")
    
    async def _is_channel_allowed(self, channel: discord.TextChannel) -> bool:
        """Check if Buckshot is allowed in this channel"""
        if not await self.config.guild(channel.guild).enabled():
            return False
        
        allowed_channels = await self.config.guild(channel.guild).allowed_channels()
        if allowed_channels and channel.id not in allowed_channels:
            return False
        
        return True
    
    async def _is_user_banned(self, user: discord.Member) -> bool:
        """Check if user is banned from playing"""
        banned_users = await self.config.guild(user.guild).banned_users()
        return user.id in banned_users
    
    @commands.group(name="buckshot", aliases=["bs"])
    async def buckshot(self, ctx):
        """Buckshot game commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @buckshot.command(name="challenge")
    async def challenge(self, ctx, opponent: discord.Member):
        """Challenge another player to a Buckshot game"""
        if not await self._is_channel_allowed(ctx.channel):
            return await ctx.send("❌ Buckshot is not enabled in this channel.")
        
        if await self._is_user_banned(ctx.author):
            return await ctx.send("❌ You are banned from playing Buckshot.")
        
        if await self._is_user_banned(opponent):
            return await ctx.send("❌ That user is banned from playing Buckshot.")
        
        if opponent.bot:
            return await ctx.send("❌ You cannot challenge a bot.")
        
        if opponent == ctx.author:
            return await ctx.send("❌ You cannot challenge yourself.")
        
        if ctx.channel.id in self.active_games:
            return await ctx.send("❌ There's already an active game in this channel.")
        
        # Check max games per channel
        max_games = await self.config.max_games_per_channel()
        channel_games = sum(1 for game in self.active_games.values() 
                          if game.channel_id == ctx.channel.id)
        
        if channel_games >= max_games:
            return await ctx.send(f"❌ Maximum number of games ({max_games}) reached in this channel.")
        
        # Create challenge
        self.pending_challenges[ctx.channel.id] = (ctx.author, datetime.utcnow())
        
        embed = discord.Embed(
            title="🎯 Buckshot Challenge",
            description=f"{ctx.author.mention} challenges {opponent.mention} to a game of Buckshot!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🎮 How to Play",
            value="React with ✅ to accept or ❌ to decline\n"
                  "Use items strategically to survive!",
            inline=False
        )
        embed.add_field(
            name="📋 Items",
            value="🥫 Skip bullet\n🔍 See bullet type\n🧤 Skip opponent's turn\n🪚 Double damage\n🍾 Heal one heart",
            inline=False
        )
        embed.set_footer(text="Challenge expires in 5 minutes")
        
        challenge_msg = await ctx.send(embed=embed)
        await challenge_msg.add_reaction("✅")
        await challenge_msg.add_reaction("❌")
        
        # Wait for response
        def check(reaction, user):
            return (user == opponent and 
                   reaction.message.id == challenge_msg.id and 
                   str(reaction.emoji) in ["✅", "❌"])
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=300.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Accept challenge
                if ctx.channel.id in self.pending_challenges:
                    del self.pending_challenges[ctx.channel.id]
                
                # Create game
                game = BuckshotGame(ctx.channel.id, ctx.author, opponent)
                self.active_games[ctx.channel.id] = game
                
                embed = discord.Embed(
                    title="🎯 Buckshot Game Started!",
                    description=f"**{ctx.author.display_name}** vs **{opponent.display_name}**",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="🎮 Commands",
                    value="`!buckshot shoot` - Fire the gun\n"
                          "`!buckshot item <item>` - Use an item\n"
                          "`!buckshot status` - Show game status\n"
                          "`!buckshot surrender` - Give up",
                    inline=False
                )
                await ctx.send(embed=embed)
                
                # Show initial game status
                await ctx.send(embed=game.get_game_status_embed())
                
            else:
                # Decline challenge
                if ctx.channel.id in self.pending_challenges:
                    del self.pending_challenges[ctx.channel.id]
                
                embed = discord.Embed(
                    title="❌ Challenge Declined",
                    description=f"{opponent.mention} declined the challenge.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                
        except asyncio.TimeoutError:
            # Challenge expired
            if ctx.channel.id in self.pending_challenges:
                del self.pending_challenges[ctx.channel.id]
            
            embed = discord.Embed(
                title="⏰ Challenge Expired",
                description="The challenge was not accepted in time.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
    
    @buckshot.command(name="shoot")
    async def shoot(self, ctx):
        """Fire the gun at yourself or your opponent"""
        if ctx.channel.id not in self.active_games:
            return await ctx.send("❌ No active game in this channel.")
        
        game = self.active_games[ctx.channel.id]
        
        if ctx.author.id != game.current_player_id:
            return await ctx.send("❌ It's not your turn!")
        
        # Check if chamber is empty
        if game.is_chamber_empty():
            game._generate_chamber()
            await ctx.send("🔫 *Chamber was empty. Reloading...*")
        
        # Ask who to shoot
        embed = discord.Embed(
            title="🎯 Choose Your Target",
            description="Who do you want to shoot?",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Targets",
            value="🔫 **Self** - If blank, keep your turn\n👤 **Opponent** - If live, they take damage",
            inline=False
        )
        
        target_msg = await ctx.send(embed=embed)
        await target_msg.add_reaction("🔫")  # Self
        await target_msg.add_reaction("👤")  # Opponent
        
        def check(reaction, user):
            return (user == ctx.author and 
                   reaction.message.id == target_msg.id and 
                   str(reaction.emoji) in ["🔫", "👤"])
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            target_self = str(reaction.emoji) == "🔫"
            target_name = "yourself" if target_self else game.opponent.display_name
            
            # Fire the bullet
            bullet = game.fire_bullet()
            if bullet is None:
                return await ctx.send("❌ Something went wrong with the gun.")
            
            damage = 2 if game.saw_active and bullet == BulletType.LIVE else 1
            game.saw_active = False  # Reset saw effect
            
            embed = discord.Embed(
                title="💥 BANG!",
                color=discord.Color.red() if bullet == BulletType.LIVE else discord.Color.green()
            )
            
            if bullet == BulletType.LIVE:
                # Live bullet
                if target_self:
                    game.lives[ctx.author.id] -= damage
                    embed.description = f"{ctx.author.mention} shot themselves with a **LIVE** bullet! 💀"
                    if damage > 1:
                        embed.description += f"\n🪚 **Saw effect:** {damage} damage dealt!"
                else:
                    game.lives[game.opponent_id] -= damage
                    embed.description = f"{ctx.author.mention} shot {game.opponent.mention} with a **LIVE** bullet! 💀"
                    if damage > 1:
                        embed.description += f"\n🪚 **Saw effect:** {damage} damage dealt!"
                
                embed.add_field(
                    name="Result",
                    value=f"{bullet.value} **LIVE BULLET** - {damage} damage!",
                    inline=False
                )
            else:
                # Blank bullet
                embed.description = f"{ctx.author.mention} shot {target_name} with a **BLANK** bullet! 😮‍💨"
                embed.add_field(
                    name="Result",
                    value=f"{bullet.value} **BLANK** - No damage!",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
            # Check for winner
            winner = game.get_winner()
            if winner:
                await self._end_game(ctx, game, winner)
                return
            
            # Handle turn logic
            if bullet == BulletType.BLANK and target_self:
                # Shot self with blank - keep turn
                await ctx.send(f"🎯 {ctx.author.mention} keeps their turn!")
            else:
                # Switch turns
                game.next_turn()
                await ctx.send(f"🔄 It's now {game.current_player.mention}'s turn!")
            
            # Show updated status
            await ctx.send(embed=game.get_game_status_embed())
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ You took too long to choose a target.")
    
    @buckshot.command(name="item")
    async def use_item(self, ctx, item: str):
        """Use an item"""
        if ctx.channel.id not in self.active_games:
            return await ctx.send("❌ No active game in this channel.")
        
        game = self.active_games[ctx.channel.id]
        
        if ctx.author.id != game.current_player_id:
            return await ctx.send("❌ It's not your turn!")
        
        # Parse item
        item_mapping = {
            "skip": ItemType.SKIP,
            "can": ItemType.SKIP,
            "🥫": ItemType.SKIP,
            "magnifier": ItemType.MAGNIFIER,
            "glass": ItemType.MAGNIFIER,
            "🔍": ItemType.MAGNIFIER,
            "gloves": ItemType.GLOVES,
            "🧤": ItemType.GLOVES,
            "saw": ItemType.SAW,
            "🪚": ItemType.SAW,
            "beer": ItemType.BEER,
            "heal": ItemType.BEER,
            "🍾": ItemType.BEER
        }
        
        item_type = item_mapping.get(item.lower())
        if not item_type:
            return await ctx.send("❌ Invalid item. Use: skip, magnifier, gloves, saw, or beer")
        
        # Check if player has the item
        if not game.use_item(ctx.author.id, item_type):
            return await ctx.send(f"❌ You don't have a {item_type.value} to use!")
        
        # Update user stats
        async with self.config.user(ctx.author).items_used() as items_used:
            items_used += 1
        
        embed = discord.Embed(
            title="⚡ Item Used",
            color=discord.Color.blue()
        )
        
        # Execute item effect
        if item_type == ItemType.SKIP:
            # Skip bullet
            if game.is_chamber_empty():
                game._generate_chamber()
                await ctx.send("🔫 *Chamber was empty. Reloading...*")
            
            skipped_bullet = game.fire_bullet()
            embed.description = f"{ctx.author.mention} used 🥫 **Skip**!"
            embed.add_field(
                name="Effect",
                value=f"Skipped a {skipped_bullet.value} bullet!",
                inline=False
            )
            
        elif item_type == ItemType.MAGNIFIER:
            # See bullet type
            if game.is_chamber_empty():
                game._generate_chamber()
                await ctx.send("🔫 *Chamber was empty. Reloading...*")
            
            current_bullet = game.get_current_bullet()
            game.current_bullet_known = True
            game.known_bullet_type = current_bullet
            
            embed.description = f"{ctx.author.mention} used 🔍 **Magnifier**!"
            embed.add_field(
                name="Effect",
                value=f"Next bullet is: {current_bullet.value}",
                inline=False
            )
            
        elif item_type == ItemType.GLOVES:
            # Skip opponent's turn
            embed.description = f"{ctx.author.mention} used 🧤 **Gloves**!"
            embed.add_field(
                name="Effect",
                value=f"{game.opponent.mention} will skip their next turn!",
                inline=False
            )
            # Keep current turn
            
        elif item_type == ItemType.SAW:
            # Double damage on next live bullet
            game.saw_active = True
            embed.description = f"{ctx.author.mention} used 🪚 **Saw**!"
            embed.add_field(
                name="Effect",
                value="Next live bullet will deal **2 damage**!",
                inline=False
            )
            
        elif item_type == ItemType.BEER:
            # Heal one heart
            if game.lives[ctx.author.id] < 5:
                game.lives[ctx.author.id] += 1
                embed.description = f"{ctx.author.mention} used 🍾 **Beer**!"
                embed.add_field(
                    name="Effect",
                    value="Healed **1 heart**! ❤️",
                    inline=False
                )
            else:
                embed.description = f"{ctx.author.mention} used 🍾 **Beer**!"
                embed.add_field(
                    name="Effect",
                    value="Already at full health!",
                    inline=False
                )
        
        await ctx.send(embed=embed)
        
        # Show updated status
        await ctx.send(embed=game.get_game_status_embed())
    
    @buckshot.command(name="status")
    async def status(self, ctx):
        """Show current game status"""
        if ctx.channel.id not in self.active_games:
            return await ctx.send("❌ No active game in this channel.")
        
        game = self.active_games[ctx.channel.id]
        await ctx.send(embed=game.get_game_status_embed())
    
    @buckshot.command(name="surrender")
    async def surrender(self, ctx):
        """Surrender the current game"""
        if ctx.channel.id not in self.active_games:
            return await ctx.send("❌ No active game in this channel.")
        
        game = self.active_games[ctx.channel.id]
        
        if ctx.author.id not in game.players:
            return await ctx.send("❌ You're not playing in this game.")
        
        # Determine winner (the other player)
        winner = game.opponent if ctx.author.id == game.current_player_id else game.current_player
        
        embed = discord.Embed(
            title="🏳️ Surrender",
            description=f"{ctx.author.mention} surrendered the game!",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        await self._end_game(ctx, game, winner)
    
    async def _end_game(self, ctx, game: BuckshotGame, winner: discord.Member):
        """End a game and update statistics"""
        # Remove game from active games
        del self.active_games[ctx.channel.id]
        
        # Update statistics
        for player_id in game.players:
            player = game.players[player_id]
            async with self.config.user(player).all() as user_data:
                user_data["games_played"] += 1
                if player == winner:
                    user_data["games_won"] += 1
        
        # Create victory embed
        embed = discord.Embed(
            title="🏆 Game Over!",
            description=f"**{winner.display_name}** wins the Buckshot game!",
            color=discord.Color.gold()
        )
        
        # Add game statistics
        game_duration = datetime.utcnow() - game.start_time
        embed.add_field(
            name="📊 Game Stats",
            value=f"**Duration:** {game_duration.seconds // 60}m {game_duration.seconds % 60}s\n"
                  f"**Turns:** {game.turn_count}\n"
                  f"**Bullets Fired:** {game.chamber_position}",
            inline=False
        )
        
        # Final lives
        p1_id, p2_id = game.player_ids
        p1_lives = "❤️" * max(0, game.lives[p1_id])
        p2_lives = "❤️" * max(0, game.lives[p2_id])
        
        embed.add_field(
            name="💀 Final Lives",
            value=f"**{game.players[p1_id].display_name}:** {p1_lives}\n"
                  f"**{game.players[p2_id].display_name}:** {p2_lives}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @buckshot.command(name="stats")
    async def stats(self, ctx, user: discord.Member = None):
        """Show Buckshot statistics"""
        if user is None:
            user = ctx.author
        
        user_data = await self.config.user(user).all()
        
        embed = discord.Embed(
            title=f"📊 Buckshot Stats - {user.display_name}",
            color=discord.Color.blue()
        )
        
        games_played = user_data["games_played"]
        games_won = user_data["games_won"]
        win_rate = (games_won / games_played * 100) if games_played > 0 else 0
        
        embed.add_field(
            name="🎮 Games",
            value=f"**Played:** {games_played}\n"
                  f"**Won:** {games_won}\n"
                  f"**Win Rate:** {win_rate:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="📈 Actions",
            value=f"**Items Used:** {user_data['items_used']}\n"
                  f"**Shots Fired:** {user_data['total_shots_fired']}",
            inline=True
        )
        
        if user_data['favorite_item']:
            embed.add_field(
                name="⭐ Favorite Item",
                value=user_data['favorite_item'],
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @buckshot.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx):
        """Show the Buckshot leaderboard"""
        if not ctx.guild:
            return await ctx.send("❌ This command can only be used in a server.")
        
        # Get all user data for this guild
        user_stats = []
        for member in ctx.guild.members:
            if member.bot:
                continue
            
            user_data = await self.config.user(member).all()
            if user_data["games_played"] > 0:
                win_rate = (user_data["games_won"] / user_data["games_played"]) * 100
                user_stats.append({
                    "member": member,
                    "games_played": user_data["games_played"],
                    "games_won": user_data["games_won"],
                    "win_rate": win_rate
                })
        
        if not user_stats:
            return await ctx.send("📊 No games have been played in this server yet!")
        
        # Sort by games won, then by win rate
        user_stats.sort(key=lambda x: (x["games_won"], x["win_rate"]), reverse=True)
        
        embed = discord.Embed(
            title="🏆 Buckshot Leaderboard",
            color=discord.Color.gold()
        )
        
        leaderboard_text = ""
        for i, stats in enumerate(user_stats[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += (
                f"{medal} **{stats['member'].display_name}**\n"
                f"   Wins: {stats['games_won']} | "
                f"Games: {stats['games_played']} | "
                f"Rate: {stats['win_rate']:.1f}%\n\n"
            )
        
        embed.description = leaderboard_text
        await ctx.send(embed=embed)
    
    @buckshot.command(name="rules")
    async def rules(self, ctx):
        """Show Buckshot game rules"""
        embed = discord.Embed(
            title="📋 Buckshot Rules",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Objective",
            value="Survive by strategically using items and making smart shooting decisions. Last player alive wins!",
            inline=False
        )
        
        embed.add_field(
            name="🔫 Gun Mechanics",
            value="• Each round has 4-8 bullets (mix of live and blank)\n"
                  "• Shooting yourself with a blank lets you keep your turn\n"
                  "• Live bullets deal 1 damage (2 with saw)\n"
                  "• Chamber reloads when empty",
            inline=False
        )
        
        embed.add_field(
            name="🎒 Items (Each player starts with 1 of each)",
            value="🥫 **Skip** - Discard the current bullet\n"
                  "🔍 **Magnifier** - See what the next bullet is\n"
                  "🧤 **Gloves** - Skip opponent's next turn\n"
                  "🪚 **Saw** - Next live bullet deals 2 damage\n"
                  "🍾 **Beer** - Heal 1 heart (max 5 hearts)",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Commands",
            value="`!buckshot challenge @user` - Start a game\n"
                  "`!buckshot shoot` - Fire the gun\n"
                  "`!buckshot item <item>` - Use an item\n"
                  "`!buckshot status` - Show game state\n"
                  "`!buckshot surrender` - Give up",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    # Admin commands
    @buckshot.group(name="admin")
    @checks.admin_or_permissions(administrator=True)
    async def buckshot_admin(self, ctx):
        """Buckshot admin commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @buckshot_admin.command(name="enable")
    async def admin_enable(self, ctx):
        """Enable Buckshot in this server"""
        await self.config.guild(ctx.guild).enabled.set(True)
        await ctx.send("✅ Buckshot has been enabled in this server.")
    
    @buckshot_admin.command(name="disable")
    async def admin_disable(self, ctx):
        """Disable Buckshot in this server"""
        await self.config.guild(ctx.guild).enabled.set(False)
        
        # End all active games in this guild
        guild_games = [channel_id for channel_id, game in self.active_games.items() 
                      if ctx.guild.get_channel(channel_id)]
        
        for channel_id in guild_games:
            del self.active_games[channel_id]
        
        await ctx.send(f"❌ Buckshot has been disabled in this server. {len(guild_games)} active games ended.")
    
    @buckshot_admin.command(name="setchannel")
    async def admin_set_channel(self, ctx, channel: discord.TextChannel):
        """Add a channel to the allowed channels list"""
        async with self.config.guild(ctx.guild).allowed_channels() as channels:
            if channel.id not in channels:
                channels.append(channel.id)
                await ctx.send(f"✅ {channel.mention} added to allowed channels.")
            else:
                await ctx.send(f"❌ {channel.mention} is already in the allowed channels list.")
    
    @buckshot_admin.command(name="removechannel")
    async def admin_remove_channel(self, ctx, channel: discord.TextChannel):
        """Remove a channel from the allowed channels list"""
        async with self.config.guild(ctx.guild).allowed_channels() as channels:
            if channel.id in channels:
                channels.remove(channel.id)
                await ctx.send(f"✅ {channel.mention} removed from allowed channels.")
            else:
                await ctx.send(f"❌ {channel.mention} is not in the allowed channels list.")
    
    @buckshot_admin.command(name="ban")
    async def admin_ban_user(self, ctx, user: discord.Member, *, reason: str = "No reason provided"):
        """Ban a user from playing Buckshot"""
        async with self.config.guild(ctx.guild).banned_users() as banned:
            if user.id not in banned:
                banned.append(user.id)
                await ctx.send(f"🔨 {user.mention} has been banned from Buckshot. Reason: {reason}")
            else:
                await ctx.send(f"❌ {user.mention} is already banned from Buckshot.")
    
    @buckshot_admin.command(name="unban")
    async def admin_unban_user(self, ctx, user: discord.Member):
        """Unban a user from playing Buckshot"""
        async with self.config.guild(ctx.guild).banned_users() as banned:
            if user.id in banned:
                banned.remove(user.id)
                await ctx.send(f"✅ {user.mention} has been unbanned from Buckshot.")
            else:
                await ctx.send(f"❌ {user.mention} is not banned from Buckshot.")
    
    @buckshot_admin.command(name="endgame")
    async def admin_end_game(self, ctx, channel: discord.TextChannel = None):
        """Force end a game in the specified channel"""
        target_channel = channel or ctx.channel
        
        if target_channel.id not in self.active_games:
            return await ctx.send(f"❌ No active game in {target_channel.mention}.")
        
        game = self.active_games[target_channel.id]
        del self.active_games[target_channel.id]
        
        embed = discord.Embed(
            title="⚠️ Game Terminated",
            description=f"The Buckshot game in {target_channel.mention} was ended by an administrator.",
            color=discord.Color.orange()
        )
        
        await target_channel.send(embed=embed)
        await ctx.send(f"✅ Game in {target_channel.mention} has been terminated.")
    
    @buckshot_admin.command(name="config")
    async def admin_config(self, ctx):
        """Show current Buckshot configuration"""
        guild_config = await self.config.guild(ctx.guild).all()
        global_config = await self.config.all()
        
        embed = discord.Embed(
            title="⚙️ Buckshot Configuration",
            color=discord.Color.blue()
        )
        
        # Guild settings
        enabled = "✅ Enabled" if guild_config["enabled"] else "❌ Disabled"
        allowed_channels = guild_config["allowed_channels"]
        banned_users = guild_config["banned_users"]
        
        channel_list = "All channels" if not allowed_channels else ", ".join(
            f"#{ctx.guild.get_channel(ch).name}" for ch in allowed_channels 
            if ctx.guild.get_channel(ch)
        )
        
        embed.add_field(
            name="🏛️ Server Settings",
            value=f"**Status:** {enabled}\n"
                  f"**Allowed Channels:** {channel_list}\n"
                  f"**Banned Users:** {len(banned_users)}",
            inline=False
        )
        
        # Global settings
        embed.add_field(
            name="🌐 Global Settings",
            value=f"**Max Games/Channel:** {global_config['max_games_per_channel']}\n"
                  f"**Game Timeout:** {global_config['game_timeout_minutes']} minutes\n"
                  f"**Allow Spectators:** {'Yes' if global_config['allow_spectators'] else 'No'}",
            inline=False
        )
        
        # Active games
        active_count = sum(1 for game in self.active_games.values() 
                          if ctx.guild.get_channel(game.channel_id))
        
        embed.add_field(
            name="📊 Current Status",
            value=f"**Active Games:** {active_count}\n"
                  f"**Pending Challenges:** {len(self.pending_challenges)}",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @buckshot_admin.command(name="resetstats")
    async def admin_reset_stats(self, ctx, user: discord.Member):
        """Reset a user's Buckshot statistics"""
        await self.config.user(user).clear()
        await ctx.send(f"✅ Reset {user.mention}'s Buckshot statistics.")
    
    # Global admin commands (bot owner only)
    @buckshot.group(name="global")
    @checks.is_owner()
    async def buckshot_global(self, ctx):
        """Global Buckshot configuration (Bot Owner Only)"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
    
    @buckshot_global.command(name="settimeout")
    async def global_set_timeout(self, ctx, minutes: int):
        """Set the global game timeout in minutes"""
        if minutes < 5:
            return await ctx.send("❌ Timeout must be at least 5 minutes.")
        
        await self.config.game_timeout_minutes.set(minutes)
        await ctx.send(f"✅ Global game timeout set to {minutes} minutes.")
    
    @buckshot_global.command(name="setmaxgames")
    async def global_set_max_games(self, ctx, count: int):
        """Set the maximum number of games per channel"""
        if count < 1:
            return await ctx.send("❌ Max games must be at least 1.")
        
        await self.config.max_games_per_channel.set(count)
        await ctx.send(f"✅ Maximum games per channel set to {count}.")
    
    @buckshot_global.command(name="stats")
    async def global_stats(self, ctx):
        """Show global Buckshot statistics"""
        total_games = 0
        total_users = 0
        
        # This is expensive but provides accurate global stats
        all_users = await self.config.all_users()
        for user_data in all_users.values():
            if user_data.get("games_played", 0) > 0:
                total_users += 1
                total_games += user_data["games_played"]
        
        embed = discord.Embed(
            title="🌐 Global Buckshot Statistics",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📊 Overall Stats",
            value=f"**Total Games Played:** {total_games:,}\n"
                  f"**Active Players:** {total_users:,}\n"
                  f"**Currently Active Games:** {len(self.active_games)}\n"
                  f"**Pending Challenges:** {len(self.pending_challenges)}",
            inline=False
        )
        
        # Server count with Buckshot enabled
        enabled_servers = 0
        all_guilds = await self.config.all_guilds()
        for guild_data in all_guilds.values():
            if guild_data.get("enabled", True):  # Default is enabled
                enabled_servers += 1
        
        embed.add_field(
            name="🏛️ Server Stats",
            value=f"**Servers with Buckshot:** {enabled_servers}\n"
                  f"**Total Bot Servers:** {len(self.bot.guilds)}",
            inline=False
        )
        
        await ctx.send(embed=embed)

# Additional utility functions for the cog
async def setup(bot):
    """Setup function for Red-DiscordBot"""
    cog = Buckshot(bot)
    await bot.add_cog(cog)