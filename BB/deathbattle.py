"""
DeathBattle system for 1v1 fights.
"""
import discord
from redbot.core import commands
import asyncio
import random
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import requests
from typing import Optional, Tuple

from .utils import (
    setup_logger, calculate_damage, check_critical_hit, 
    create_battle_embed, get_random_move, safe_send
)
from .constants import *

class BattleSystem:
    """Handles battle mechanics and state."""
    
    def __init__(self, config):
        self.config = config
        self.log = setup_logger("battle")
        self.active_battles = set()  # Track ongoing battles
    
    def generate_fight_card(self, user1, user2):
        """
        Generates a dynamic fight card image with avatars and usernames.
        Uses asyncio-friendly approach for image processing.
        """
        # Open the local template image
        try:
            template = Image.open(TEMPLATE_PATH)
            draw = ImageDraw.Draw(template)
        except (FileNotFoundError, IOError):
            self.log.error(f"Template image not found at {TEMPLATE_PATH}")
            # Create a fallback blank image
            template = Image.new('RGBA', (650, 500), color=(255, 255, 255, 255))
            draw = ImageDraw.Draw(template)
            draw.text((50, 200), "Fight Card Template Missing", fill="black")

        # Load font
        try:
            username_font = ImageFont.truetype(FONT_PATH, 25)
        except (OSError, IOError):
            self.log.warning(f"Font file not found at {FONT_PATH}, using default")
            username_font = ImageFont.load_default()

        # Avatar dimensions and positions
        avatar_size = (250, 260)  # Adjust as needed
        avatar_positions = [(15, 130), (358, 130)]  # Positions for avatars
        username_positions = [(75, 410), (430, 410)]  # Positions for usernames

        # Fetch and paste avatars
        for i, user in enumerate((user1, user2)):
            try:
                # Use a more efficient, direct approach to fetch avatars
                avatar_url = user.display_avatar.url
                
                # Use requests with a timeout
                avatar_response = requests.get(avatar_url, timeout=2)
                avatar = Image.open(io.BytesIO(avatar_response.content)).convert("RGBA")
                avatar = avatar.resize(avatar_size)
                
                # Paste avatar onto the template
                template.paste(avatar, avatar_positions[i], avatar)
                
                # Draw username
                username = user.display_name[:20]  # Limit username length
                draw.text(username_positions[i], username, font=username_font, fill="black")
            except Exception as e:
                self.log.error(f"Error processing avatar for {user.display_name}: {e}")
                # Add a placeholder text instead
                draw.rectangle([avatar_positions[i], 
                            (avatar_positions[i][0] + avatar_size[0], 
                            avatar_positions[i][1] + avatar_size[1])], 
                            outline="black", fill="gray")
                draw.text((avatar_positions[i][0] + 50, avatar_positions[i][1] + 130), 
                        "Avatar Error", fill="black")

        # Save the image to a BytesIO object
        output = io.BytesIO()
        template.save(output, format="PNG", optimize=True)
        output.seek(0)

        return output
    
    async def start_battle(self, ctx, player1: discord.Member, player2: discord.Member):
        """Start a battle between two players."""
        battle_id = f"{player1.id}_{player2.id}_{ctx.channel.id}"
        
        if battle_id in self.active_battles:
            await safe_send(ctx, "❌ A battle is already in progress between these players!")
            return False
        
        self.active_battles.add(battle_id)
        
        try:
            # Generate fight card
            fight_card = self.generate_fight_card(player1, player2)
            fight_file = discord.File(fp=fight_card, filename="fight_card.png")
            
            # Send fight card
            await safe_send(ctx, file=fight_file)
            
            # Start the actual battle
            winner = await self._battle_loop(ctx, player1, player2)
            
            if winner:
                await self._process_battle_rewards(ctx, winner, player1 if winner != player1 else player2)
            
            return True
            
        except Exception as e:
            self.log.error(f"Battle error: {e}")
            await safe_send(ctx, "❌ An error occurred during the battle!")
            return False
        finally:
            self.active_battles.discard(battle_id)
    
    async def _battle_loop(self, ctx, player1: discord.Member, player2: discord.Member) -> Optional[discord.Member]:
        """Main battle loop."""
        # Initialize HP
        p1_hp = STARTING_HP
        p2_hp = STARTING_HP
        
        # Determine who goes first
        current_player = random.choice([player1, player2])
        other_player = player2 if current_player == player1 else player1
        
        turn_count = 0
        max_turns = 20  # Prevent infinite battles
        
        # Initial battle embed
        embed = create_battle_embed(player1, player2, p1_hp, p2_hp, "Battle begins! Get ready to fight!")
        message = await safe_send(ctx, embed=embed)
        
        if not message:
            return None
        
        while p1_hp > 0 and p2_hp > 0 and turn_count < max_turns:
            turn_count += 1
            
            # Get a random move for the current player
            move = get_random_move()
            is_crit = check_critical_hit(move)
            damage = calculate_damage(move, is_crit)
            
            # Apply damage
            if current_player == player1:
                p2_hp = max(0, p2_hp - damage)
                current_hp = p1_hp
                target_hp = p2_hp
            else:
                p1_hp = max(0, p1_hp - damage)
                current_hp = p2_hp
                target_hp = p1_hp
            
            # Create turn description
            crit_text = " **CRITICAL HIT!**" if is_crit else ""
            turn_info = (
                f"Turn {turn_count}: {current_player.display_name} used **{move['name']}**{crit_text}\n"
                f"Dealt {damage} damage!"
            )
            
            # Update battle embed
            embed = create_battle_embed(player1, player2, p1_hp, p2_hp, turn_info)
            await message.edit(embed=embed)
            
            # Check for winner
            if p1_hp <= 0:
                await asyncio.sleep(2)
                embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{player2.display_name}** wins the battle!",
                    color=discord.Color.gold()
                )
                await message.edit(embed=embed)
                return player2
            elif p2_hp <= 0:
                await asyncio.sleep(2)
                embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{player1.display_name}** wins the battle!",
                    color=discord.Color.gold()
                )
                await message.edit(embed=embed)
                return player1
            
            # Switch turns
            current_player, other_player = other_player, current_player
            
            # Small delay between turns
            await asyncio.sleep(3)
        
        # Battle timed out
        if turn_count >= max_turns:
            embed = discord.Embed(
                title="⏰ Battle Timeout",
                description="The battle lasted too long! It's a draw!",
                color=discord.Color.orange()
            )
            await message.edit(embed=embed)
        
        return None
    
    async def _process_battle_rewards(self, ctx, winner: discord.Member, loser: discord.Member):
        """Process rewards after a battle."""
        from .bank import BankSystem
        
        bank = BankSystem(self.config)
        
        # Calculate rewards
        berris_reward = random.randint(MIN_BERRIS_REWARD, MAX_BERRIS_REWARD)
        
        # Award berris to winner
        await bank.add_berris(winner, berris_reward)
        
        # Update stats
        winner_wins = await self.config.member(winner).wins()
        loser_losses = await self.config.member(loser).losses()
        
        await self.config.member(winner).wins.set(winner_wins + 1)
        await self.config.member(loser).losses.set(loser_losses + 1)
        
        # Create reward embed
        embed = discord.Embed(
            title="🎉 Battle Rewards",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Winner",
            value=f"🏆 {winner.display_name}",
            inline=True
        )
        
        embed.add_field(
            name="Reward",
            value=f"💰 {berris_reward} Berris",
            inline=True
        )
        
        embed.add_field(
            name="Stats Updated",
            value=f"Wins: {winner_wins + 1} | Losses: {loser_losses + 1}",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)
        
        self.log.info(f"Battle complete: {winner.name} beat {loser.name}, earned {berris_reward} berris")

class BattleCommands(commands.Cog):
    """Battle-related commands."""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.battle_system = BattleSystem(config)
        self.log = setup_logger("battle_commands")
    
    @commands.command(name="db", aliases=["deathbattle", "battle"])
    @commands.cooldown(1, BATTLE_COOLDOWN, commands.BucketType.user)
    async def deathbattle(self, ctx, opponent: Optional[discord.Member] = None):
        """Challenge someone to a DeathBattle!"""
        challenger = ctx.author
        
        if opponent is None:
            await safe_send(ctx, "❌ You need to mention someone to challenge them to a battle!")
            return
        
        if opponent == challenger:
            await safe_send(ctx, "❌ You can't battle yourself!")
            return
        
        if opponent.bot:
            await safe_send(ctx, "❌ You can't battle bots!")
            return
        
        # Start the battle
        success = await self.battle_system.start_battle(ctx, challenger, opponent)
        
        if not success:
            # Reset cooldown if battle failed to start
            ctx.command.reset_cooldown(ctx)
    
    @commands.command(name="battlestats", aliases=["bs"])
    async def battle_stats(self, ctx, user: Optional[discord.Member] = None):
        """Check battle statistics."""
        if user is None:
            user = ctx.author
        
        wins = await self.config.member(user).wins()
        losses = await self.config.member(user).losses()
        total_battles = wins + losses
        
        if total_battles == 0:
            win_rate = 0
        else:
            win_rate = (wins / total_battles) * 100
        
        embed = discord.Embed(
            title=f"⚔️ {user.display_name}'s Battle Stats",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏆 Wins",
            value=str(wins),
            inline=True
        )
        
        embed.add_field(
            name="💀 Losses",
            value=str(losses),
            inline=True
        )
        
        embed.add_field(
            name="📊 Win Rate",
            value=f"{win_rate:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Total Battles",
            value=str(total_battles),
            inline=False
        )
        
        await safe_send(ctx, embed=embed)