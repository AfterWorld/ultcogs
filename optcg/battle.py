import discord
import asyncio
import random
import logging
from typing import Dict, List, Optional, Tuple, Union
from redbot.core import Config, commands
from redbot.core.bot import Red
from .utils import get_card_stats

log = logging.getLogger("red.optcg.battle")

class BattleSystem:
    """Battle system for One Piece TCG game."""
    
    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self.active_battles = {}  # {channel_id: BattleSession}
    
    async def initialize(self):
        """Initialize the battle system configuration."""
        # Register defaults for battles
        default_guild = {
            "battle_enabled": True,
            "battle_cooldown": 300,  # 5 minutes cooldown between battles
            "last_battle_time": 0
        }
        
        default_user = {
            "battle_deck": [],      # List of card IDs in the user's battle deck
            "battle_stats": {},     # Dict of card IDs to (attack, defense, health) tuples
            "wins": 0,
            "losses": 0
        }
        
        self.config.register_guild(**default_guild)
        self.config.register_user(**default_user)
    
    async def create_battle(self, ctx: commands.Context, challenger: discord.Member, opponent: discord.Member) -> bool:
        """Create a battle between two users."""
        # Check if there's already a battle in this channel
        if ctx.channel.id in self.active_battles:
            await ctx.send("There's already a battle in progress in this channel!")
            return False
        
        # Check if both users have battle decks
        challenger_data = await self.config.user(challenger).all()
        opponent_data = await self.config.user(opponent).all()
        
        if not challenger_data["battle_deck"]:
            await ctx.send(f"{challenger.display_name} doesn't have a battle deck set up! Use `.optcg deck` to set one up.")
            return False
        
        if not opponent_data["battle_deck"]:
            await ctx.send(f"{opponent.display_name} doesn't have a battle deck set up! Use `.optcg deck` to set one up.")
            return False
        
        # Create the battle session
        battle_session = BattleSession(
            self.bot,
            self.config,
            ctx.channel,
            challenger,
            opponent,
            challenger_data,
            opponent_data
        )
        
        self.active_battles[ctx.channel.id] = battle_session
        
        # Start the battle
        result = await battle_session.start_battle()
        
        # Remove the battle from active battles
        if ctx.channel.id in self.active_battles:
            del self.active_battles[ctx.channel.id]
        
        return result
    
    async def get_user_battle_stats(self, user: discord.Member) -> Tuple[int, int]:
        """Get a user's battle record (wins/losses)."""
        user_data = await self.config.user(user).all()
        return user_data["wins"], user_data["losses"]
    
    async def set_battle_deck(self, user: discord.Member, card_ids: List[str]) -> bool:
        """Set a user's battle deck."""
        user_data = await self.config.user(user).all()
        card_details = user_data.get("card_details", {})
        
        # Verify all cards exist in the user's collection
        for card_id in card_ids:
            if card_id not in card_details:
                return False
        
        # Calculate and store battle stats for each card
        battle_stats = {}
        for card_id in card_ids:
            card = card_details[card_id]
            attack, defense, health = await get_card_stats(card)
            battle_stats[card_id] = (attack, defense, health)
        
        # Update user data
        async with self.config.user(user).all() as user_data:
            user_data["battle_deck"] = card_ids
            user_data["battle_stats"] = battle_stats
        
        return True


class BattleSession:
    """Represents an active battle between two users."""
    
    def __init__(
        self,
        bot: Red,
        config: Config,
        channel: discord.TextChannel,
        challenger: discord.Member,
        opponent: discord.Member,
        challenger_data: Dict,
        opponent_data: Dict
    ):
        self.bot = bot
        self.config = config
        self.channel = channel
        self.challenger = challenger
        self.opponent = opponent
        self.challenger_data = challenger_data
        self.opponent_data = opponent_data
        self.challenger_deck = challenger_data["battle_deck"]
        self.opponent_deck = opponent_data["battle_deck"]
        self.challenger_stats = challenger_data["battle_stats"]
        self.opponent_stats = opponent_data["battle_stats"]
        self.turn = 0
        self.message = None
        self.winner = None
        
    async def start_battle(self) -> bool:
        """Start the battle sequence."""
        try:
            # Send initial battle message
            embed = discord.Embed(
                title="One Piece TCG Battle!",
                description=f"**{self.challenger.display_name}** vs **{self.opponent.display_name}**",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name=f"{self.challenger.display_name}'s Deck",
                value=f"{len(self.challenger_deck)} cards",
                inline=True
            )
            
            embed.add_field(
                name=f"{self.opponent.display_name}'s Deck",
                value=f"{len(self.opponent_deck)} cards",
                inline=True
            )
            
            self.message = await self.channel.send(embed=embed)
            
            # Wait for confirmation from opponent
            confirm_embed = discord.Embed(
                title="Battle Challenge",
                description=f"{self.opponent.mention}, do you accept the battle challenge from {self.challenger.display_name}?",
                color=discord.Color.blue()
            )
            
            accept_button = discord.ui.Button(label="Accept", style=discord.ButtonStyle.success)
            decline_button = discord.ui.Button(label="Decline", style=discord.ButtonStyle.danger)
            
            async def accept_callback(interaction: discord.Interaction):
                if interaction.user != self.opponent:
                    await interaction.response.send_message("You're not the opponent in this battle!", ephemeral=True)
                    return
                
                await interaction.response.defer()
                await confirmation_message.edit(content="Battle accepted! Starting the battle...", embed=None, view=None)
                await self.run_battle()
            
            async def decline_callback(interaction: discord.Interaction):
                if interaction.user != self.opponent:
                    await interaction.response.send_message("You're not the opponent in this battle!", ephemeral=True)
                    return
                
                await interaction.response.defer()
                await confirmation_message.edit(content=f"{self.opponent.display_name} declined the battle challenge!", embed=None, view=None)
                return
            
            accept_button.callback = accept_callback
            decline_button.callback = decline_callback
            
            view = discord.ui.View()
            view.add_item(accept_button)
            view.add_item(decline_button)
            
            confirmation_message = await self.channel.send(embed=confirm_embed, view=view)
            
            # Wait for 60 seconds for a response
            try:
                await asyncio.sleep(60)
                # If we reach here, no response was given
                if view.is_finished():
                    # A button was pressed and handled
                    return True
                else:
                    await confirmation_message.edit(content=f"{self.opponent.display_name} did not respond to the battle challenge!", embed=None, view=None)
                    return False
            except Exception as e:
                log.error(f"Error in battle confirmation: {e}")
                return False
            
            return True
            
        except Exception as e:
            log.error(f"Error starting battle: {e}")
            return False
    
    async def run_battle(self) -> bool:
        """Run the battle simulation."""
        # Shuffle decks
        random.shuffle(self.challenger_deck)
        random.shuffle(self.opponent_deck)
        
        # Create copies to avoid modifying the original decks
        challenger_active_deck = self.challenger_deck.copy()
        opponent_active_deck = self.opponent_deck.copy()
        
        # Initial battle embed
        battle_embed = discord.Embed(
            title="One Piece TCG Battle",
            description=f"**{self.challenger.display_name}** vs **{self.opponent.display_name}**",
            color=discord.Color.gold()
        )
        
        battle_message = await self.channel.send(embed=battle_embed)
        
        # Main battle loop
        battle_rounds = min(5, min(len(challenger_active_deck), len(opponent_active_deck)))
        challenger_points = 0
        opponent_points = 0
        
        for round_num in range(1, battle_rounds + 1):
            # Draw cards for this round
            challenger_card_id = challenger_active_deck.pop(0)
            opponent_card_id = opponent_active_deck.pop(0)
            
            # Get card details
            challenger_card = self.challenger_data["card_details"][challenger_card_id]
            opponent_card = self.opponent_data["card_details"][opponent_card_id]
            
            # Get battle stats
            challenger_stats = self.challenger_stats[challenger_card_id]
            opponent_stats = self.opponent_stats[opponent_card_id]
            
            # Battle round embed
            round_embed = discord.Embed(
                title=f"Round {round_num}",
                description=f"**{self.challenger.display_name}** draws **{challenger_card['name']}**\n"
                           f"**{self.opponent.display_name}** draws **{opponent_card['name']}**",
                color=discord.Color.blue()
            )
            
            # Add card images
            round_embed.set_thumbnail(url=challenger_card["images"]["large"])
            round_embed.set_image(url=opponent_card["images"]["large"])
            
            # Add card stats
            round_embed.add_field(
                name=f"{challenger_card['name']} ({challenger_card['rarity']})",
                value=f"Attack: {challenger_stats[0]}\nDefense: {challenger_stats[1]}\nHealth: {challenger_stats[2]}",
                inline=True
            )
            
            round_embed.add_field(
                name=f"{opponent_card['name']} ({opponent_card['rarity']})",
                value=f"Attack: {opponent_stats[0]}\nDefense: {opponent_stats[1]}\nHealth: {opponent_stats[2]}",
                inline=True
            )
            
            # Simulate card battle
            challenger_remaining_health = challenger_stats[2]
            opponent_remaining_health = opponent_stats[2]
            
            # Simple battle simulation - each card attacks the other
            # Challenger attacks first
            damage_to_opponent = max(0, challenger_stats[0] - opponent_stats[1])
            opponent_remaining_health -= damage_to_opponent
            
            # Opponent attacks next
            damage_to_challenger = max(0, opponent_stats[0] - challenger_stats[1])
            challenger_remaining_health -= damage_to_challenger
            
            # Determine round winner
            round_result = ""
            if challenger_remaining_health > opponent_remaining_health:
                round_result = f"**{self.challenger.display_name}** wins round {round_num}!"
                challenger_points += 1
            elif opponent_remaining_health > challenger_remaining_health:
                round_result = f"**{self.opponent.display_name}** wins round {round_num}!"
                opponent_points += 1
            else:
                round_result = f"Round {round_num} is a tie!"
            
            round_embed.add_field(
                name="Battle Result",
                value=f"{challenger_card['name']} deals {damage_to_opponent} damage!\n"
                     f"{opponent_card['name']} deals {damage_to_challenger} damage!\n\n"
                     f"{round_result}",
                inline=False
            )
            
            # Update score
            round_embed.set_footer(text=f"Score: {self.challenger.display_name} {challenger_points} - {opponent_points} {self.opponent.display_name}")
            
            await battle_message.edit(embed=round_embed)
            await asyncio.sleep(3)  # Pause between rounds
        
        # Determine overall winner
        final_embed = discord.Embed(
            title="Battle Finished!",
            color=discord.Color.green()
        )
        
        if challenger_points > opponent_points:
            final_embed.description = f"**{self.challenger.display_name}** wins the battle!"
            self.winner = self.challenger
        elif opponent_points > challenger_points:
            final_embed.description = f"**{self.opponent.display_name}** wins the battle!"
            self.winner = self.opponent
        else:
            final_embed.description = "The battle ends in a tie!"
        
        final_embed.add_field(
            name="Final Score",
            value=f"**{self.challenger.display_name}**: {challenger_points}\n"
                 f"**{self.opponent.display_name}**: {opponent_points}",
            inline=False
        )
        
        await battle_message.edit(embed=final_embed)
        
        # Update win/loss records
        if self.winner:
            if self.winner == self.challenger:
                await self.update_battle_record(self.challenger, self.opponent)
            else:
                await self.update_battle_record(self.opponent, self.challenger)
        
        return True
    
    async def update_battle_record(self, winner: discord.Member, loser: discord.Member):
        """Update the battle records for winner and loser."""
        async with self.config.user(winner).all() as winner_data:
            winner_data["wins"] = winner_data.get("wins", 0) + 1
        
        async with self.config.user(loser).all() as loser_data:
            loser_data["losses"] = loser_data.get("losses", 0) + 1
