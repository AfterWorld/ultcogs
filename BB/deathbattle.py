"""
DeathBattle system for 1v1 fights with Devil Fruits and Status Effects.
"""
import discord
from redbot.core import commands
import asyncio
import random
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import requests
from typing import Optional, Tuple, Dict, Any

# Handle imports more robustly
try:
    from .utils import (
        setup_logger, calculate_damage, check_critical_hit, 
        create_battle_embed, get_random_move, safe_send,
        get_random_environment, create_character_data
    )
    from .constants import *
    from .gamedata import MOVES, MOVE_TYPES, ENVIRONMENTS, DEVIL_FRUITS
    from .status_manager import StatusEffectManager
    from .devil_fruit_manager import DevilFruitManager
    from .starter_system import StarterSystem
    from .fruit_manager import FruitManager
except ImportError:
    # Fallback for when the cog is loaded through CogManager
    import sys
    import os
    
    # Get the current directory of this file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Add the BB directory to the Python path temporarily
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        from utils import (
            setup_logger, calculate_damage, check_critical_hit, 
            create_battle_embed, get_random_move, safe_send,
            get_random_environment, create_character_data
        )
        from constants import *
        from gamedata import MOVES, MOVE_TYPES, ENVIRONMENTS, DEVIL_FRUITS
        from status_manager import StatusEffectManager
        from devil_fruit_manager import DevilFruitManager
        from starter_system import StarterSystem
        from fruit_manager import FruitManager
    finally:
        # Clean up the path
        if current_dir in sys.path:
            sys.path.remove(current_dir)

class BattleSystem:
    """Handles battle mechanics and state with enhanced devil fruit system."""
    
    def __init__(self, config):
        self.config = config
        self.log = setup_logger("battle")
        self.active_battles = set()  # Track ongoing battles
        
        # Initialize managers for enhanced battle system
        self.status_manager = StatusEffectManager()
        self.devil_fruit_manager = DevilFruitManager(self.status_manager)
    
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
    
    async def get_user_devil_fruit(self, user: discord.Member) -> Optional[str]:
        """Get a user's devil fruit if they have one."""
        member_data = await self.config.member(user).all()
        return member_data.get("devil_fruit", None)
    
    async def award_devil_fruit(self, user: discord.Member) -> Optional[str]:
        """Award a random devil fruit to a user with low probability."""
        if random.random() < DEVIL_FRUIT_DROP_CHANCE:
            # Check if user already has a fruit
            current_fruit = await self.get_user_devil_fruit(user)
            if current_fruit:
                return None  # Can't have multiple fruits
            
            # Determine rarity
            if random.random() < RARE_FRUIT_CHANCE:
                fruit_pool = list(DEVIL_FRUITS["Rare"].keys())
            else:
                fruit_pool = list(DEVIL_FRUITS["Common"].keys())
            
            fruit = random.choice(fruit_pool)
            await self.config.member(user).devil_fruit.set(fruit)
            
            self.log.info(f"Awarded {fruit} to {user.name}")
            return fruit
        
        return None
    
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
        """Main battle loop with enhanced mechanics."""
        # Get devil fruits for both players
        p1_fruit = await self.get_user_devil_fruit(player1)
        p2_fruit = await self.get_user_devil_fruit(player2)
        
        # Create character data
        p1_data = create_character_data(player1, p1_fruit)
        p2_data = create_character_data(player2, p2_fruit)
        
        # Choose random environment
        environment = get_random_environment()
        
        # Determine who goes first (Pika Pika no Mi always goes first)
        if p1_fruit == "Pika Pika no Mi":
            current_player_data = p1_data
            other_player_data = p2_data
            current_member = player1
            other_member = player2
        elif p2_fruit == "Pika Pika no Mi":
            current_player_data = p2_data
            other_player_data = p1_data
            current_member = player2
            other_member = player1
        else:
            # Random first turn
            if random.choice([True, False]):
                current_player_data = p1_data
                other_player_data = p2_data
                current_member = player1
                other_member = player2
            else:
                current_player_data = p2_data
                other_player_data = p1_data
                current_member = player2
                other_member = player1
        
        turn_count = 0
        
        # Initial battle embed with environment
        embed = create_battle_embed(
            player1, player2, p1_data["hp"], p2_data["hp"], 
            f"Battle begins in **{environment}**! Get ready to fight!", 
            environment
        )
        
        # Add devil fruit info if players have them
        if p1_fruit or p2_fruit:
            fruit_info = ""
            if p1_fruit:
                fruit_data = DEVIL_FRUITS["Common"].get(p1_fruit) or DEVIL_FRUITS["Rare"].get(p1_fruit)
                fruit_info += f"**{player1.display_name}**: {p1_fruit} ({fruit_data['type']})\n"
            if p2_fruit:
                fruit_data = DEVIL_FRUITS["Common"].get(p2_fruit) or DEVIL_FRUITS["Rare"].get(p2_fruit)
                fruit_info += f"**{player2.display_name}**: {p2_fruit} ({fruit_data['type']})\n"
            
            embed.add_field(name="🍎 Devil Fruits", value=fruit_info, inline=False)
        
        message = await safe_send(ctx, embed=embed)
        
        if not message:
            return None
        
        while p1_data["hp"] > 0 and p2_data["hp"] > 0 and turn_count < MAX_BATTLE_TURNS:
            turn_count += 1
            
            # Process status effects at start of turn
            current_effects = await self.status_manager.process_status_effects(current_player_data)
            
            # Check if player is stunned
            if self.status_manager.is_stunned(current_player_data):
                turn_info = (
                    f"Turn {turn_count}: **{current_member.display_name}** is stunned and cannot act!\n"
                )
                
                # Show status effects
                if current_effects:
                    effect_text = ", ".join([f"{effect}: {desc}" for effect, desc in current_effects.items()])
                    turn_info += f"Status: {effect_text}"
                
                # Update battle embed
                embed = create_battle_embed(
                    player1, player2, p1_data["hp"], p2_data["hp"], 
                    turn_info, environment
                )
                await message.edit(embed=embed)
                
                # Switch turns and continue
                current_player_data, other_player_data = other_player_data, current_player_data
                current_member, other_member = other_member, current_member
                await asyncio.sleep(2)
                continue
            
            # Get a random move for the current player
            move = get_random_move()
            
            # Check if move is on cooldown
            if current_player_data["moves_on_cooldown"].get(move["name"], 0) > 0:
                # Get a different move that's not on cooldown
                available_moves = [m for m in MOVES if current_player_data["moves_on_cooldown"].get(m["name"], 0) == 0]
                if available_moves:
                    move = random.choice(available_moves)
            
            # Calculate dodge chance
            dodge_chance = self.status_manager.get_dodge_chance(other_player_data)
            
            if random.random() < dodge_chance:
                # Attack was dodged
                turn_info = (
                    f"Turn {turn_count}: **{current_member.display_name}** used **{move['name']}**\n"
                    f"💨 **{other_member.display_name}** dodged the attack!"
                )
            else:
                # Attack hits
                is_crit = check_critical_hit(move, current_player_data)
                
                # Get damage modifiers
                attack_modifier = self.status_manager.get_damage_modifier(current_player_data, is_attack=True)
                defense_modifier = self.status_manager.get_damage_modifier(other_player_data, is_attack=False)
                
                base_damage = calculate_damage(move, is_crit, {
                    "attack": attack_modifier,
                    "defense": defense_modifier
                })
                
                # Apply devil fruit effects
                fruit_damage, fruit_message = await self.devil_fruit_manager.process_devil_fruit_effect(
                    current_player_data, other_player_data, move, environment
                )
                
                total_damage = base_damage + fruit_damage
                
                # Apply environment effects
                total_damage = self._apply_environment_effects(total_damage, move, environment)
                
                # Handle healing moves
                if move.get("effect") == "heal":
                    heal_amount = move.get("heal_amount", 20)
                    # Apply environment healing bonus
                    if environment in ["Fishman Island", "Whole Cake Island"]:
                        heal_amount += ENVIRONMENT_EFFECTS.get("heal_boost", 0)
                    
                    current_player_data["hp"] = min(current_player_data["max_hp"], current_player_data["hp"] + heal_amount)
                    
                    turn_info = (
                        f"Turn {turn_count}: **{current_member.display_name}** used **{move['name']}**\n"
                        f"💚 Healed for {heal_amount} HP!"
                    )
                else:
                    # Apply damage
                    other_player_data["hp"] = max(0, other_player_data["hp"] - total_damage)
                    other_player_data["stats"]["damage_taken"] += total_damage
                    current_player_data["stats"]["damage_dealt"] += total_damage
                    current_player_data["stats"]["moves_used"] += 1
                    
                    if is_crit:
                        current_player_data["stats"]["crits_landed"] += 1
                    
                    # Apply move effects (burn, stun, etc.)
                    await self._apply_move_effects(move, current_player_data, other_player_data)
                    
                    # Create turn description
                    crit_text = " **CRITICAL HIT!**" if is_crit else ""
                    turn_info = (
                        f"Turn {turn_count}: **{current_member.display_name}** used **{move['name']}**{crit_text}\n"
                        f"💥 Dealt {total_damage} damage!"
                    )
                    
                    # Add devil fruit effect message
                    if fruit_message:
                        turn_info += f"\n\n{fruit_message}"
                
                # Set move cooldown
                if move.get("cooldown", 0) > 0:
                    current_player_data["moves_on_cooldown"][move["name"]] = move["cooldown"]
            
            # Show status effects
            if current_effects:
                effect_text = ", ".join([f"{effect}: {desc}" for effect, desc in current_effects.items()])
                turn_info += f"\n📊 Status: {effect_text}"
            
            # Update battle embed
            embed = create_battle_embed(
                player1, player2, p1_data["hp"], p2_data["hp"], 
                turn_info, environment
            )
            await message.edit(embed=embed)
            
            # Check for winner
            if p1_data["hp"] <= 0:
                await asyncio.sleep(2)
                embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{player2.display_name}** wins the battle!",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="📊 Battle Stats",
                    value=self._create_battle_stats(p1_data, p2_data),
                    inline=False
                )
                await message.edit(embed=embed)
                return player2
            elif p2_data["hp"] <= 0:
                await asyncio.sleep(2)
                embed = discord.Embed(
                    title="🏆 Battle Complete!",
                    description=f"**{player1.display_name}** wins the battle!",
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="📊 Battle Stats",
                    value=self._create_battle_stats(p1_data, p2_data),
                    inline=False
                )
                await message.edit(embed=embed)
                return player1
            
            # Reduce cooldowns
            for move_name in list(current_player_data["moves_on_cooldown"].keys()):
                current_player_data["moves_on_cooldown"][move_name] -= 1
                if current_player_data["moves_on_cooldown"][move_name] <= 0:
                    del current_player_data["moves_on_cooldown"][move_name]
            
            # Switch turns
            current_player_data, other_player_data = other_player_data, current_player_data
            current_member, other_member = other_member, current_member
            
            # Small delay between turns
            await asyncio.sleep(3)
        
        # Battle timed out
        if turn_count >= MAX_BATTLE_TURNS:
            embed = discord.Embed(
                title="⏰ Battle Timeout",
                description="The battle lasted too long! It's a draw!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📊 Final Stats",
                value=self._create_battle_stats(p1_data, p2_data),
                inline=False
            )
            await message.edit(embed=embed)
        
        return None
    
    def _apply_environment_effects(self, damage: int, move: Dict[str, Any], environment: str) -> int:
        """Apply environment effects to damage."""
        env_data = ENVIRONMENTS.get(environment, {})
        effect_type = env_data.get("effect")
        
        if effect_type == "strong_boost" and move.get("type") == "strong":
            damage += ENVIRONMENT_EFFECTS.get("strong_boost", 0)
        elif effect_type == "war_boost":
            damage += ENVIRONMENT_EFFECTS.get("war_boost", 0)
        elif effect_type == "ultimate_boost":
            damage = int(damage * (1 + ENVIRONMENT_EFFECTS.get("ultimate_boost", 0)))
        
        return damage
    
    async def _apply_move_effects(self, move: Dict[str, Any], attacker: Dict[str, Any], defender: Dict[str, Any]):
        """Apply move-specific status effects."""
        effect = move.get("effect")
        
        if effect == "burn" and random.random() < move.get("burn_chance", 0):
            await self.status_manager.apply_effect("burn", defender, value=1)
        elif effect == "stun" and random.random() < move.get("stun_chance", 0):
            await self.status_manager.apply_effect("stun", defender, duration=1)
    
    def _create_battle_stats(self, p1_data: Dict[str, Any], p2_data: Dict[str, Any]) -> str:
        """Create battle statistics summary."""
        stats = (
            f"**{p1_data['name']}**: {p1_data['stats']['damage_dealt']} damage dealt, "
            f"{p1_data['stats']['moves_used']} moves used, {p1_data['stats']['crits_landed']} crits\n"
            f"**{p2_data['name']}**: {p2_data['stats']['damage_dealt']} damage dealt, "
            f"{p2_data['stats']['moves_used']} moves used, {p2_data['stats']['crits_landed']} crits"
        )
        return stats
    
    async def _process_battle_rewards(self, ctx, winner: discord.Member, loser: discord.Member):
        """Process rewards after a battle."""
        from .bank import BankSystem
        
        bank = BankSystem(self.config)
        
        # Calculate rewards
        berris_reward = random.randint(MIN_BERRIS_REWARD, MAX_BERRIS_REWARD)
        
        # Award berris to winner
        await bank.add_berris(winner, berris_reward)
        
        # Check for devil fruit drop
        new_fruit = await self.award_devil_fruit(winner)
        
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
            name="Berris Reward",
            value=f"💰 {berris_reward} Berris",
            inline=True
        )
        
        if new_fruit:
            fruit_data = DEVIL_FRUITS["Common"].get(new_fruit) or DEVIL_FRUITS["Rare"].get(new_fruit)
            embed.add_field(
                name="🍎 Devil Fruit Found!",
                value=f"**{new_fruit}**\n*{fruit_data['type']}*\n{fruit_data['bonus']}",
                inline=False
            )
        
        embed.add_field(
            name="Stats Updated",
            value=f"Wins: {winner_wins + 1} | Losses: {loser_losses + 1}",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)
        
        self.log.info(f"Battle complete: {winner.name} beat {loser.name}, earned {berris_reward} berris" + 
                     (f", found {new_fruit}" if new_fruit else ""))

class BattleCommands(commands.Cog):
    """Battle-related commands with enhanced devil fruit system."""
    
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.battle_system = BattleSystem(config)
        self.starter_system = StarterSystem(config)
        self.fruit_manager = FruitManager(config)
        self.log = setup_logger("battle_commands")
    
    @commands.command(name="start")
    async def start_journey(self, ctx):
        """Begin your pirate journey and receive your first Devil Fruit!"""
        user = ctx.author
        
        # Check if user has already started
        if not await self.starter_system.can_start(user):
            current_fruit = await self.config.member(user).devil_fruit()
            embed = discord.Embed(
                title="🏴‍☠️ Journey Already Begun!",
                description=f"You've already started your adventure with the **{current_fruit}**!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🎯 Available Commands",
                value="`.db` - Start a battle\n`.battlestats` - Check your stats\n`.devilfruit` - View your fruit info",
                inline=False
            )
            await safe_send(ctx, embed=embed)
            return
        
        # Assign starter fruit
        fruit_name, is_rare = await self.starter_system.assign_starter_fruit(user, ctx.guild)
        
        if not fruit_name:
            await safe_send(ctx, "❌ An error occurred while starting your journey. Please try again.")
            return
        
        # Create and send the starter embed
        embed = await self.starter_system.create_starter_embed(user, fruit_name, is_rare)
        await safe_send(ctx, embed=embed)
        
        # Send special announcement for rare fruits
        if is_rare:
            announcement = discord.Embed(
                title="🌟 LEGENDARY FRUIT DISCOVERED! 🌟",
                description=f"**{user.display_name}** has discovered the legendary **{fruit_name}**!",
                color=discord.Color.gold()
            )
            announcement.set_thumbnail(url=user.display_avatar.url)
            await safe_send(ctx, embed=announcement)

    @commands.command(name="removefruit")
    @commands.cooldown(1, FRUIT_REMOVE_COOLDOWN, commands.BucketType.user)
    async def remove_fruit(self, ctx):
        """Remove your current Devil Fruit for a cost."""
        user = ctx.author
        
        # Check if user has started
        has_started = await self.config.member(user).has_started()
        if not has_started:
            await safe_send(ctx, "❌ You must start your journey first! Use `.start` to begin.")
            return
        
        # Get current fruit for display
        current_fruit = await self.config.member(user).devil_fruit()
        if not current_fruit:
            await safe_send(ctx, "❌ You don't have a Devil Fruit to remove!")
            return
        
        # Show confirmation
        fruit_data = DEVIL_FRUITS["Common"].get(current_fruit) or DEVIL_FRUITS["Rare"].get(current_fruit)
        is_rare = current_fruit in DEVIL_FRUITS["Rare"]
        
        embed = discord.Embed(
            title="⚠️ Remove Devil Fruit",
            description=f"Are you sure you want to remove **{current_fruit}**?",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="🍎 Current Fruit",
            value=f"**{current_fruit}**\n*{fruit_data['type']}*\n{fruit_data['bonus']}",
            inline=False
        )
        
        embed.add_field(
            name="💰 Cost",
            value=format_berris(REMOVE_FRUIT_COST),
            inline=True
        )
        
        embed.add_field(
            name="⏰ Cooldown",
            value="24 hours before you can remove another",
            inline=True
        )
        
        if is_rare:
            embed.add_field(
                name="⚠️ WARNING",
                value="This is a **RARE** fruit! Once removed, you may not get another rare fruit easily!",
                inline=False
            )
        
        embed.add_field(
            name="🤔 Confirmation",
            value="React with ✅ to confirm or ❌ to cancel",
            inline=False
        )
        
        message = await safe_send(ctx, embed=embed)
        if not message:
            return
        
        # Add reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, reaction_user):
            return (reaction_user == user and 
                    reaction.message.id == message.id and 
                    str(reaction.emoji) in ["✅", "❌"])
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Handle rare fruit tracking
                if is_rare:
                    rare_fruits_given = await self.config.guild(ctx.guild).rare_fruits_given()
                    if str(user.id) in rare_fruits_given:
                        del rare_fruits_given[str(user.id)]
                        await self.config.guild(ctx.guild).rare_fruits_given.set(rare_fruits_given)
                
                # Remove the fruit
                success, msg, removed_fruit = await self.fruit_manager.remove_fruit(user)
                
                if success:
                    embed = discord.Embed(
                        title="🗑️ Devil Fruit Removed",
                        description=msg,
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="💡 Next Steps",
                        value="You can now use `.buyfruit` to purchase a new random Devil Fruit!",
                        inline=False
                    )
                    await message.edit(embed=embed)
                else:
                    await safe_send(ctx, f"❌ {msg}")
            else:
                embed = discord.Embed(
                    title="❌ Removal Cancelled",
                    description="Your Devil Fruit remains intact.",
                    color=discord.Color.blue()
                )
                await message.edit(embed=embed)
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Confirmation Timeout",
                description="Removal cancelled due to no response.",
                color=discord.Color.gray()
            )
            await message.edit(embed=embed)

    @commands.command(name="buyfruit")
    @commands.cooldown(1, FRUIT_BUY_COOLDOWN, commands.BucketType.user)
    async def buy_fruit(self, ctx, fruit_type: str = None):
        """Buy a random Devil Fruit. Use 'rare' to specifically buy a rare fruit."""
        user = ctx.author
        
        # Check if user has started
        has_started = await self.config.member(user).has_started()
        if not has_started:
            await safe_send(ctx, "❌ You must start your journey first! Use `.start` to begin.")
            return
        
        # Check if they already have a fruit
        current_fruit = await self.config.member(user).devil_fruit()
        if current_fruit:
            await safe_send(ctx, f"❌ You already have **{current_fruit}**! Use `.removefruit` first to get a new one.")
            return
        
        # Determine if they want to force a rare fruit
        force_rare = fruit_type and fruit_type.lower() == "rare"
        cost = BUY_RARE_FRUIT_COST if force_rare else BUY_FRUIT_COST
        
        # Check if they have enough berries
        total_berries = await self.config.member(user).total_berris()
        if total_berries < cost:
            embed = discord.Embed(
                title="💰 Insufficient Berris",
                description=f"You need {format_berris(cost)} but only have {format_berris(total_berries)}!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="💡 How to Earn Berris",
                value="• Win battles with `.db`\n• Complete daily activities\n• Bank robberies with `.rob`",
                inline=False
            )
            
            await safe_send(ctx, embed=embed)
            return
        
        # Show available rare fruits if forcing rare
        if force_rare:
            available_rares = await self.fruit_manager._get_available_rare_fruits(ctx.guild)
            if not available_rares:
                await safe_send(ctx, "❌ No rare fruits are currently available for purchase!")
                return
            
            embed = discord.Embed(
                title="⭐ Available Rare Fruits",
                description=f"Available rare fruits: {len(available_rares)}\nCost: {format_berris(cost)}",
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="🍎 Buy Devil Fruit",
                description=f"Purchase a random Devil Fruit for {format_berris(cost)}",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="🎲 Chances",
                value=f"• {int(BUY_COMMON_CHANCE * 100)}% Common Fruit\n• {int(BUY_RARE_CHANCE * 100)}% Rare Fruit",
                inline=True
            )
        
        embed.add_field(
            name="🤔 Confirmation",
            value="React with ✅ to confirm or ❌ to cancel",
            inline=False
        )
        
        message = await safe_send(ctx, embed=embed)
        if not message:
            return
        
        # Add reactions
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        def check(reaction, reaction_user):
            return (reaction_user == user and 
                    reaction.message.id == message.id and 
                    str(reaction.emoji) in ["✅", "❌"])
        
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Buy the fruit
                success, msg, fruit_name, is_rare = await self.fruit_manager.buy_fruit(user, ctx.guild, force_rare)
                
                if success:
                    # Create purchase embed
                    embed = await self.fruit_manager.create_fruit_purchase_embed(user, fruit_name, is_rare, cost)
                    await message.edit(embed=embed)
                    
                    # Send special announcement for rare fruits
                    if is_rare:
                        announcement = discord.Embed(
                            title="🌟 RARE FRUIT PURCHASED! 🌟",
                            description=f"**{user.display_name}** has purchased the legendary **{fruit_name}**!",
                            color=discord.Color.gold()
                        )
                        announcement.set_thumbnail(url=user.display_avatar.url)
                        await safe_send(ctx, embed=announcement)
                else:
                    await safe_send(ctx, f"❌ {msg}")
            else:
                embed = discord.Embed(
                    title="❌ Purchase Cancelled",
                    description="Devil Fruit purchase cancelled.",
                    color=discord.Color.blue()
                )
                await message.edit(embed=embed)
                
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="⏰ Purchase Timeout",
                description="Purchase cancelled due to no response.",
                color=discord.Color.gray()
            )
            await message.edit(embed=embed)

    @commands.command(name="changefruit")
    @commands.admin_or_permissions(manage_guild=True)
    async def change_user_fruit(self, ctx, user: discord.Member, *, fruit_name: str):
        """Change a user's Devil Fruit to a specific one (Admin only)."""
        # Check if fruit exists
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        
        if not fruit_data:
            # Show available fruits
            embed = discord.Embed(
                title="❌ Devil Fruit Not Found",
                description=f"'{fruit_name}' is not a valid Devil Fruit name.",
                color=discord.Color.red()
            )
            
            # Show some examples
            common_examples = list(DEVIL_FRUITS["Common"].keys())[:5]
            rare_examples = list(DEVIL_FRUITS["Rare"].keys())[:5]
            
            embed.add_field(
                name="🔹 Common Examples",
                value="\n".join([f"• {fruit}" for fruit in common_examples]),
                inline=True
            )
            
            embed.add_field(
                name="⭐ Rare Examples", 
                value="\n".join([f"• {fruit}" for fruit in rare_examples]),
                inline=True
            )
            
            await safe_send(ctx, embed=embed)
            return
        
        # Change the fruit
        success, msg = await self.fruit_manager.change_fruit(user, ctx.guild, fruit_name)
        
        if success:
            is_rare = fruit_name in DEVIL_FRUITS["Rare"]
            
            embed = discord.Embed(
                title="🔄 Devil Fruit Changed",
                description=msg,
                color=discord.Color.gold() if is_rare else discord.Color.blue()
            )
            
            embed.add_field(
                name="🍎 New Fruit",
                value=f"**{fruit_name}**",
                inline=True
            )
            
            embed.add_field(
                name="📝 Type",
                value=fruit_data["type"],
                inline=True
            )
            
            embed.add_field(
                name="⚡ Rarity",
                value="⭐ Rare" if is_rare else "🔹 Common",
                inline=True
            )
            
            embed.add_field(
                name="💫 Power",
                value=fruit_data["bonus"],
                inline=False
            )
            
            await safe_send(ctx, embed=embed)
        else:
            await safe_send(ctx, f"❌ {msg}")

    @commands.command(name="fruitshop")
    async def fruit_shop(self, ctx):
        """View the Devil Fruit shop and pricing."""
        embed = discord.Embed(
            title="🍎 Devil Fruit Shop",
            description="Manage your Devil Fruit powers here!",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🗑️ Remove Current Fruit",
            value=f"**Cost:** {format_berris(REMOVE_FRUIT_COST)}\n**Cooldown:** 24 hours\n**Command:** `.removefruit`",
            inline=False
        )
        
        embed.add_field(
            name="🎲 Buy Random Fruit",
            value=f"**Cost:** {format_berris(BUY_FRUIT_COST)}\n**Chances:** {int(BUY_COMMON_CHANCE * 100)}% Common, {int(BUY_RARE_CHANCE * 100)}% Rare\n**Command:** `.buyfruit`",
            inline=False
        )
        
        embed.add_field(
            name="⭐ Buy Rare Fruit",
            value=f"**Cost:** {format_berris(BUY_RARE_FRUIT_COST)}\n**Guaranteed:** Rare fruit (if available)\n**Command:** `.buyfruit rare`",
            inline=False
        )
        
        embed.add_field(
            name="📝 Notes",
            value="• You must remove your current fruit before buying a new one\n• Rare fruits are limited per server\n• All purchases are final!",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)

    @commands.command(name="fruitstats")
    @commands.admin_or_permissions(manage_guild=True)
    async def fruit_distribution_stats(self, ctx):
        """View rare fruit distribution statistics (Admin only)."""
        stats = await self.starter_system.get_rare_fruit_stats(ctx.guild)
        
        embed = discord.Embed(
            title="🍎 Rare Devil Fruit Distribution",
            description="Current distribution of rare fruits in this server:",
            color=discord.Color.purple()
        )
        
        for fruit_name, data in stats.items():
            current = data["current"]
            max_count = data["max"]
            remaining = max_count - current
            
            status = "🔴 FULL" if remaining == 0 else f"🟢 {remaining} left"
            
            embed.add_field(
                name=fruit_name,
                value=f"{current}/{max_count} assigned\n{status}",
                inline=True
            )
        
        # Add summary
        total_given = sum(data["current"] for data in stats.values())
        total_possible = sum(data["max"] for data in stats.values())
        
        embed.add_field(
            name="📊 Summary",
            value=f"**{total_given}/{total_possible}** rare fruits distributed",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)

    @commands.command(name="resetfruit")
    @commands.is_owner()
    async def reset_user_fruit(self, ctx, user: discord.Member):
        """Reset a user's devil fruit and starter status (Owner only)."""
        # Remove from rare fruit tracking if they had a rare fruit
        current_fruit = await self.config.member(user).devil_fruit()
        
        if current_fruit and current_fruit in DEVIL_FRUITS["Rare"]:
            rare_fruits_given = await self.config.guild(ctx.guild).rare_fruits_given()
            if str(user.id) in rare_fruits_given:
                del rare_fruits_given[str(user.id)]
                await self.config.guild(ctx.guild).rare_fruits_given.set(rare_fruits_given)
        
        # Reset user data
        await self.config.member(user).devil_fruit.set(None)
        await self.config.member(user).has_started.set(False)
        await self.config.member(user).fruit_acquired_date.set(None)
        
        embed = discord.Embed(
            title="🔄 User Reset Complete",
            description=f"**{user.display_name}** can now use `.start` again.",
            color=discord.Color.green()
        )
        
        if current_fruit:
            embed.add_field(
                name="Previous Fruit",
                value=current_fruit,
                inline=True
            )
        
        await safe_send(ctx, embed=embed)
    
    @commands.command(name="db", aliases=["deathbattle", "battle"])
    @commands.cooldown(1, BATTLE_COOLDOWN, commands.BucketType.user)
    async def deathbattle(self, ctx, opponent: Optional[discord.Member] = None):
        """Challenge someone to a DeathBattle! If no opponent is specified, a random user will be chosen."""
        challenger = ctx.author
        
        # Check if challenger has started their journey
        has_started = await self.config.member(challenger).has_started()
        if not has_started:
            embed = discord.Embed(
                title="🏴‍☠️ Start Your Journey First!",
                description="You need to begin your pirate adventure before battling!",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🎯 Get Started",
                value="Use `.start` to receive your Devil Fruit and begin your journey!",
                inline=False
            )
            await safe_send(ctx, embed=embed)
            return
        
        if opponent is None:
            # Get all members in the guild (excluding bots and the challenger)
            potential_opponents = [
                member for member in ctx.guild.members 
                if not member.bot and member != challenger and member.status != discord.Status.offline
            ]
            
            # Filter to only include users who have started
            started_opponents = []
            for member in potential_opponents:
                member_started = await self.config.member(member).has_started()
                if member_started:
                    started_opponents.append(member)
            
            if not started_opponents:
                await safe_send(ctx, "❌ No available opponents found! Make sure there are other users who have used `.start`.")
                return
            
            # Pick a random opponent
            opponent = random.choice(started_opponents)
            
            # Send a message showing who was randomly selected
            embed = discord.Embed(
                title="🎲 Random Opponent Selected!",
                description=f"{challenger.display_name} challenges {opponent.display_name} to a battle!",
                color=discord.Color.purple()
            )
            await safe_send(ctx, embed=embed)
            
            # Small delay before starting the battle
            await asyncio.sleep(2)
        
        if opponent == challenger:
            await safe_send(ctx, "❌ You can't battle yourself!")
            return
        
        if opponent.bot:
            await safe_send(ctx, "❌ You can't battle bots!")
            return
        
        # Check if opponent has started
        opponent_started = await self.config.member(opponent).has_started()
        if not opponent_started:
            await safe_send(ctx, f"❌ {opponent.display_name} hasn't started their journey yet! They need to use `.start` first.")
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
        devil_fruit = await self.config.member(user).devil_fruit()
        has_started = await self.config.member(user).has_started()
        total_battles = wins + losses
        
        if not has_started:
            embed = discord.Embed(
                title="🏴‍☠️ No Journey Started",
                description=f"**{user.display_name}** hasn't started their pirate journey yet!",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🎯 Get Started",
                value="Use `.start` to begin your adventure!",
                inline=False
            )
            await safe_send(ctx, embed=embed)
            return
        
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
        
        if devil_fruit:
            fruit_data = DEVIL_FRUITS["Common"].get(devil_fruit) or DEVIL_FRUITS["Rare"].get(devil_fruit)
            if fruit_data:
                rarity = "⭐ Rare" if devil_fruit in DEVIL_FRUITS["Rare"] else "🔹 Common"
                embed.add_field(
                    name="🍎 Devil Fruit",
                    value=f"**{devil_fruit}** ({rarity})\n*{fruit_data['type']}*\n{fruit_data['bonus']}",
                    inline=False
                )
        
        await safe_send(ctx, embed=embed)
    
    @commands.command(name="devilfruit", aliases=["df"])
    async def devil_fruit_info(self, ctx, user: Optional[discord.Member] = None):
        """Check devil fruit information."""
        if user is None:
            user = ctx.author
        
        has_started = await self.config.member(user).has_started()
        if not has_started:
            await safe_send(ctx, f"❌ {user.display_name} hasn't started their journey yet! Use `.start` first.")
            return
        
        devil_fruit = await self.config.member(user).devil_fruit()
        
        if not devil_fruit:
            await safe_send(ctx, f"❌ {user.display_name} doesn't have a Devil Fruit!")
            return
        
        fruit_data = DEVIL_FRUITS["Common"].get(devil_fruit) or DEVIL_FRUITS["Rare"].get(devil_fruit)
        
        if not fruit_data:
            await safe_send(ctx, "❌ Devil Fruit data not found!")
            return
        
        embed = discord.Embed(
            title=f"🍎 {devil_fruit}",
            description=fruit_data["bonus"],
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Type",
            value=fruit_data["type"],
            inline=True
        )
        
        embed.add_field(
            name="Effect",
            value=fruit_data["effect"].title(),
            inline=True
        )
        
        embed.add_field(
            name="Owner",
            value=user.display_name,
            inline=True
        )
        
        # Determine rarity color
        if devil_fruit in DEVIL_FRUITS["Rare"]:
            embed.color = discord.Color.gold()
            embed.add_field(
                name="Rarity",
                value="⭐ Rare",
                inline=False
            )
        else:
            embed.color = discord.Color.blue()
            embed.add_field(
                name="Rarity",
                value="🔹 Common",
                inline=False
            )
        
        await safe_send(ctx, embed=embed)
    
    @commands.command(name="moves")
    async def show_moves(self, ctx):
        """Show all available battle moves."""
        embed = discord.Embed(
            title="⚔️ Battle Moves",
            description="Here are all the moves that can be used in battle!",
            color=discord.Color.red()
        )
        
        # Group moves by type
        regular_moves = [m for m in MOVES if m["type"] == "regular"]
        strong_moves = [m for m in MOVES if m["type"] == "strong"]
        critical_moves = [m for m in MOVES if m["type"] == "critical"]
        
        if regular_moves:
            move_list = "\n".join([f"• **{m['name']}** - {m['description']}" for m in regular_moves[:5]])
            embed.add_field(
                name="🥊 Regular Moves (No Cooldown)",
                value=move_list,
                inline=False
            )
        
        if strong_moves:
            move_list = "\n".join([f"• **{m['name']}** - {m['description']}" for m in strong_moves[:5]])
            embed.add_field(
                name="💪 Strong Moves (2 Turn Cooldown)",
                value=move_list,
                inline=False
            )
        
        if critical_moves:
            move_list = "\n".join([f"• **{m['name']}** - {m['description']}" for m in critical_moves[:4]])
            embed.add_field(
                name="⚡ Critical Moves (4 Turn Cooldown)",
                value=move_list,
                inline=False
            )
        
        embed.add_field(
            name="📝 Note",
            value="Moves are chosen randomly during battle. Some moves have special effects like burn, stun, or healing!",
            inline=False
        )
        
        await safe_send(ctx, embed=embed)
    
    @commands.command(name="environments")
    async def show_environments(self, ctx):
        """Show all battle environments."""
        embed = discord.Embed(
            title="🌍 Battle Environments",
            description="Battles take place in random One Piece locations with special effects!",
            color=discord.Color.green()
        )
        
        for env_name, env_data in ENVIRONMENTS.items():
            embed.add_field(
                name=f"🏝️ {env_name}",
                value=env_data["description"],
                inline=False
            )
        
        await safe_send(ctx, embed=embed)

    @commands.command(name="givedevilfruit", hidden=True)
    @commands.is_owner()
    async def give_devil_fruit(self, ctx, user: discord.Member, *, fruit_name: str):
        """Give a devil fruit to a user (Owner only)."""
        # Check if fruit exists
        fruit_data = DEVIL_FRUITS["Common"].get(fruit_name) or DEVIL_FRUITS["Rare"].get(fruit_name)
        
        if not fruit_data:
            await safe_send(ctx, f"❌ Devil Fruit '{fruit_name}' not found!")
            return
        
        # Check if user already has a fruit
        current_fruit = await self.config.member(user).devil_fruit()
        if current_fruit:
            await safe_send(ctx, f"❌ {user.display_name} already has {current_fruit}!")
            return
        
        # Give the fruit
        await self.config.member(user).devil_fruit.set(fruit_name)
        await self.config.member(user).has_started.set(True)
        
        embed = discord.Embed(
            title="🍎 Devil Fruit Granted!",
            description=f"**{fruit_name}** has been given to {user.display_name}!",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Type",
            value=fruit_data["type"],
            inline=True
        )
        
        embed.add_field(
            name="Effect",
            value=fruit_data["effect"].title(),
            inline=True
        )
        
        embed.add_field(
            name="Bonus",
            value=fruit_data["bonus"],
            inline=False
        )
        
        await safe_send(ctx, embed=embed)