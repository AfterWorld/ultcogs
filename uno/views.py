"""
Discord UI Views and Components for Uno Game
"""
import discord
from typing import List, Optional, Dict, Any
from .game import UnoGameSession, GameState
from .cards import UnoCard, UnoColor, UnoCardType
from .utils import create_hand_image, get_card_emoji


class UnoGameView(discord.ui.View):
    """Main game view with Hand and Play buttons"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=1800)  # 30 minutes
        self.game_session = game_session
        self.cog = cog
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        return interaction.user.id in self.game_session.players
    
    @discord.ui.button(label="🃏 Hand", style=discord.ButtonStyle.primary, row=0)
    async def view_hand(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show player's hand"""
        await interaction.response.defer(ephemeral=True)
        
        player_id = interaction.user.id
        hand = self.game_session.get_player_hand(player_id)
        
        if not hand:
            await interaction.followup.send("❌ You're not in this game!", ephemeral=True)
            return
        
        if len(hand.cards) == 0:
            await interaction.followup.send("🎉 You have no cards! You won!", ephemeral=True)
            return
        
        try:
            # Create hand image
            image_path = await create_hand_image(hand.cards, self.cog.assets_path)
            
            # Create embed
            embed = discord.Embed(
                title="🃏 Your Hand",
                description=f"You have {len(hand.cards)} cards",
                color=discord.Color.blue()
            )
            
            # Add card list as text backup
            card_list = "\n".join([f"{get_card_emoji(card)} {card.display_name}" for card in hand.cards])
            if len(card_list) < 1024:
                embed.add_field(name="Cards", value=card_list, inline=False)
            
            # Check if it's player's turn and what cards they can play
            if self.game_session.is_current_player(player_id):
                playable = self.game_session.get_playable_cards(player_id)
                if playable:
                    embed.add_field(
                        name="🎯 Playable Cards", 
                        value=f"{len(playable)} cards can be played",
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="⚠️ No Playable Cards", 
                        value="You must draw a card",
                        inline=True
                    )
            
            if image_path:
                file = discord.File(image_path, filename="hand.png")
                embed.set_image(url="attachment://hand.png")
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            # Fallback to text-only display
            embed = discord.Embed(
                title="🃏 Your Hand",
                description=f"You have {len(hand.cards)} cards\n\n{card_list}",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🎮 Play", style=discord.ButtonStyle.success, row=0)
    async def play_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open card selection interface"""
        await interaction.response.defer(ephemeral=True)
        
        player_id = interaction.user.id
        
        if not self.game_session.is_current_player(player_id):
            await interaction.followup.send("❌ It's not your turn!", ephemeral=True)
            return
        
        # Check if player must draw penalty cards first
        if self.game_session.draw_count > 0:
            view = DrawPenaltyView(self.game_session, self.cog)
            embed = discord.Embed(
                title="📥 Draw Penalty",
                description=f"You must draw **{self.game_session.draw_count}** cards or play a stacking card!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Get playable cards
        playable_cards = self.game_session.get_playable_cards(player_id)
        
        if not playable_cards:
            # Must draw a card
            view = DrawCardView(self.game_session, self.cog)
            embed = discord.Embed(
                title="📥 Draw Card",
                description="You have no playable cards. You must draw a card.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # Show card selection interface
        if len(playable_cards) <= 25:  # Discord select menu limit
            view = CardSelectionView(self.game_session, playable_cards, self.cog)
            embed = discord.Embed(
                title="🎯 Choose a Card to Play",
                description=f"You can play {len(playable_cards)} cards. Select one below:",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            # Too many cards, use pagination or simplified interface
            await interaction.followup.send(
                "❌ You have too many playable cards! This shouldn't happen in normal Uno.",
                ephemeral=True
            )
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.secondary, row=1)
    async def game_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show game status"""
        await interaction.response.defer(ephemeral=True)
        
        status = self.game_session.get_game_status()
        embed = discord.Embed(title="📊 Game Status", color=discord.Color.blue())
        
        if status["top_card"]:
            embed.add_field(name="🎯 Current Card", value=status["top_card"], inline=True)
        
        if status["current_color"]:
            embed.add_field(name="🎨 Current Color", value=status["current_color"], inline=True)
        
        embed.add_field(name="🔄 Direction", value=status["direction"], inline=True)
        
        if status["current_player"]:
            embed.add_field(
                name="🎮 Current Turn", 
                value=f"<@{status['current_player']}>", 
                inline=True
            )
        
        if status["draw_penalty"] > 0:
            embed.add_field(
                name="📥 Draw Penalty", 
                value=f"{status['draw_penalty']} cards", 
                inline=True
            )
        
        # Player card counts
        player_info = []
        for player_id, card_count in status["card_counts"].items():
            player_info.append(f"<@{player_id}>: {card_count} cards")
        
        embed.add_field(
            name="👥 Players", 
            value="\n".join(player_info), 
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class CardSelectionView(discord.ui.View):
    """View for selecting which card to play"""
    
    def __init__(self, game_session: UnoGameSession, playable_cards: List[UnoCard], cog):
        super().__init__(timeout=300)  # 5 minutes
        self.game_session = game_session
        self.playable_cards = playable_cards
        self.cog = cog
        
        # Add card selection dropdown
        self.add_item(CardSelectDropdown(playable_cards, game_session, cog))


class CardSelectDropdown(discord.ui.Select):
    """Dropdown for selecting cards"""
    
    def __init__(self, playable_cards: List[UnoCard], game_session: UnoGameSession, cog):
        self.game_session = game_session
        self.cog = cog
        
        # Create options for each playable card
        options = []
        for i, card in enumerate(playable_cards):
            emoji = get_card_emoji(card)
            options.append(discord.SelectOption(
                label=card.display_name,
                description=f"Play this {card.color.value.lower()} card",
                emoji=emoji,
                value=str(i)
            ))
        
        super().__init__(
            placeholder="Choose a card to play...",
            options=options,
            max_values=1
        )
        self.playable_cards = playable_cards
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        card_index = int(self.values[0])
        selected_card = self.playable_cards[card_index]
        
        # If it's a wild card, need to select color
        if selected_card.color == UnoColor.WILD:
            view = ColorSelectionView(self.game_session, selected_card, self.cog)
            embed = discord.Embed(
                title="🌈 Choose Color",
                description=f"You're playing **{selected_card.display_name}**. Choose the new color:",
                color=discord.Color.purple()
            )
            await interaction.edit_original_response(embed=embed, view=view)
        else:
            # Play the card directly
            success, message = self.game_session.play_card(interaction.user.id, selected_card)
            
            if success:
                # Update main game view
                await self.cog.update_game_display(self.game_session)
                embed = discord.Embed(
                    title="✅ Card Played!",
                    description=message,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Cannot Play Card",
                    description=message,
                    color=discord.Color.red()
                )
            
            await interaction.edit_original_response(embed=embed, view=None)


class ColorSelectionView(discord.ui.View):
    """View for selecting color after playing wild card"""
    
    def __init__(self, game_session: UnoGameSession, wild_card: UnoCard, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.wild_card = wild_card
        self.cog = cog
        
        # Add color buttons
        colors = [UnoColor.RED, UnoColor.GREEN, UnoColor.YELLOW, UnoColor.BLUE]
        for color in colors:
            button = ColorButton(color, game_session, wild_card, cog)
            self.add_item(button)


class ColorButton(discord.ui.Button):
    """Button for selecting wild card color"""
    
    def __init__(self, color: UnoColor, game_session: UnoGameSession, wild_card: UnoCard, cog):
        self.color = color
        self.game_session = game_session
        self.wild_card = wild_card
        self.cog = cog
        
        # Set button style and emoji based on color
        styles = {
            UnoColor.RED: (discord.ButtonStyle.danger, "🔴"),
            UnoColor.GREEN: (discord.ButtonStyle.success, "🟢"),
            UnoColor.YELLOW: (discord.ButtonStyle.secondary, "🟡"),
            UnoColor.BLUE: (discord.ButtonStyle.primary, "🔵")
        }
        
        style, emoji = styles[color]
        super().__init__(style=style, emoji=emoji, label=color.value)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Play the wild card with selected color
        success, message = self.game_session.play_card(
            interaction.user.id, 
            self.wild_card, 
            self.color
        )
        
        if success:
            # Update main game view
            await self.cog.update_game_display(self.game_session)
            embed = discord.Embed(
                title="✅ Wild Card Played!",
                description=message,
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Cannot Play Card",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)


class DrawCardView(discord.ui.View):
    """View for drawing cards when no playable cards"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.cog = cog
    
    @discord.ui.button(label="📥 Draw Card", style=discord.ButtonStyle.primary)
    async def draw_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        success, message, cards = self.game_session.draw_card(interaction.user.id)
        
        if success:
            await self.cog.update_game_display(self.game_session)
            embed = discord.Embed(
                title="📥 Card Drawn",
                description=message,
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ Cannot Draw",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)


class DrawPenaltyView(discord.ui.View):
    """View for handling draw penalties (Draw 2/4 cards)"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.cog = cog
    
    @discord.ui.button(label="📥 Draw Cards", style=discord.ButtonStyle.danger)
    async def draw_penalty(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        player_id = interaction.user.id
        draw_count = self.game_session.draw_count
        
        success = self.game_session.force_draw_penalty(player_id)
        
        if success:
            await self.cog.update_game_display(self.game_session)
            embed = discord.Embed(
                title="📥 Penalty Cards Drawn",
                description=f"You drew {draw_count} cards as penalty.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to draw penalty cards.",
                color=discord.Color.red()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)


class LobbyView(discord.ui.View):
    """View for game lobby (joining/starting)"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=1800)  # 30 minutes
        self.game_session = game_session
        self.cog = cog
    
    @discord.ui.button(label="🎯 Join Game", style=discord.ButtonStyle.success)
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        success = self.game_session.add_player(interaction.user.id)
        
        if success:
            await self.cog.update_lobby_display(self.game_session)
            await interaction.followup.send(
                f"✅ {interaction.user.mention} joined the game!",
                ephemeral=True
            )
        else:
            reason = "Game is full" if len(self.game_session.players) >= self.game_session.max_players else "Game already started or you're already in it"
            await interaction.followup.send(f"❌ Cannot join: {reason}", ephemeral=True)
    
    @discord.ui.button(label="🚀 Start Game", style=discord.ButtonStyle.primary)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        if interaction.user.id != self.game_session.host_id:
            await interaction.followup.send("❌ Only the host can start the game!", ephemeral=True)
            return
        
        if len(self.game_session.players) < self.game_session.min_players:
            await interaction.followup.send(
                f"❌ Need at least {self.game_session.min_players} players to start!",
                ephemeral=True
            )
            return
        
        success = self.game_session.start_game()
        
        if success:
            await self.cog.update_game_display(self.game_session)
            await interaction.followup.send("🎮 **Game Started!**", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to start game!", ephemeral=True)
    
    @discord.ui.button(label="❌ Leave Game", style=discord.ButtonStyle.danger)
    async def leave_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        success = self.game_session.remove_player(interaction.user.id)
        
        if success:
            await self.cog.update_lobby_display(self.game_session)
            await interaction.followup.send(
                f"👋 {interaction.user.mention} left the game.",
                ephemeral=True
            )
        else:
            await interaction.followup.send("❌ You're not in this game!", ephemeral=True)