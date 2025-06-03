"""
Enhanced Discord UI Views and Components for Uno Game
Features: Advanced Interactions, Statistics Views, Configuration UI
"""
import discord
from typing import List, Optional, Dict, Any
from .game import UnoGameSession, GameState, AIPlayer
from .cards import UnoCard, UnoColor, UnoCardType
from .utils import create_hand_image, get_card_emoji, stats_manager


class UnoGameView(discord.ui.View):
    """Enhanced main game view with advanced features"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=1800)  # 30 minutes
        self.game_session = game_session
        self.cog = cog
        
        # Add conditional buttons based on game state
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Setup buttons based on current game state"""
        # Always available buttons
        self.add_item(HandButton(self.game_session, self.cog))
        self.add_item(PlayButton(self.game_session, self.cog))
        self.add_item(StatusButton(self.game_session, self.cog))
        
        # Conditional buttons
        if self.game_session.settings.get("challenge_draw4") and self.game_session.challenge_window_open:
            self.add_item(ChallengeButton(self.game_session, self.cog))
        
        if self.game_session.settings.get("uno_penalty"):
            self.add_item(UnoButton(self.game_session, self.cog))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user can interact with this view"""
        return interaction.user.id in self.game_session.players


class HandButton(discord.ui.Button):
    """Enhanced hand viewing button"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(label="🃏 Hand", style=discord.ButtonStyle.primary, row=0)
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
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
            # Create enhanced hand image with organization
            image_path = await create_hand_image(hand.cards, self.cog.assets_path, organize_by_color=True)
            
            # Create enhanced embed
            embed = discord.Embed(
                title="🃏 Your Hand",
                description=f"You have {len(hand.cards)} cards",
                color=discord.Color.blue()
            )
            
            # Organize cards by color for text display
            color_groups = {}
            for card in hand.cards:
                color_name = card.color.value
                if color_name not in color_groups:
                    color_groups[color_name] = []
                color_groups[color_name].append(card)
            
            # Add organized card list
            for color, cards in color_groups.items():
                if len(cards) > 0:
                    card_list = ", ".join([f"{get_card_emoji(card)} {card.display_name}" for card in cards])
                    embed.add_field(name=f"{color} Cards ({len(cards)})", value=card_list, inline=False)
            
            # Check if it's player's turn and what cards they can play
            if self.game_session.is_current_player(player_id):
                playable = self.game_session.get_playable_cards(player_id)
                if playable:
                    embed.add_field(
                        name="🎯 Playable Cards", 
                        value=f"{len(playable)} cards can be played",
                        inline=True
                    )
                    
                    # Show which cards are playable
                    playable_names = [card.display_name for card in playable[:5]]  # Show first 5
                    if len(playable) > 5:
                        playable_names.append(f"... and {len(playable) - 5} more")
                    embed.add_field(
                        name="Playable", 
                        value=", ".join(playable_names),
                        inline=True
                    )
                else:
                    embed.add_field(
                        name="⚠️ No Playable Cards", 
                        value="You must draw a card",
                        inline=True
                    )
                
                # Show draw penalty if applicable
                if self.game_session.draw_count > 0:
                    embed.add_field(
                        name="📥 Draw Penalty",
                        value=f"Must draw {self.game_session.draw_count} cards or stack",
                        inline=True
                    )
            
            # UNO status
            if len(hand.cards) == 1:
                if self.game_session.uno_called.get(player_id, False):
                    embed.add_field(name="🔥 UNO Status", value="✅ UNO Called!", inline=True)
                else:
                    embed.add_field(name="🔥 UNO Status", value="⚠️ Remember to call UNO!", inline=True)
            
            if image_path:
                file = discord.File(image_path, filename="hand.png")
                embed.set_image(url="attachment://hand.png")
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            # Enhanced fallback
            embed = discord.Embed(
                title="❌ Error Loading Hand",
                description="Could not generate hand image. Here's your card list:",
                color=discord.Color.red()
            )
            
            card_list = "\n".join([f"{get_card_emoji(card)} {card.display_name}" for card in hand.cards])
            embed.add_field(name="Your Cards", value=card_list, inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)


class PlayButton(discord.ui.Button):
    """Enhanced play card button"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(label="🎮 Play", style=discord.ButtonStyle.success, row=0)
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        player_id = interaction.user.id
        
        if not self.game_session.is_current_player(player_id):
            await interaction.followup.send("❌ It's not your turn!", ephemeral=True)
            return
        
        # Check if player must draw penalty cards first
        if self.game_session.draw_count > 0:
            if self.game_session.settings.get("draw_stacking"):
                # Show stacking options
                view = DrawStackingView(self.game_session, self.cog)
                embed = discord.Embed(
                    title="📥 Draw Penalty",
                    description=f"You must draw **{self.game_session.draw_count}** cards or play a stacking card!",
                    color=discord.Color.red()
                )
            else:
                # Must draw penalty
                view = DrawPenaltyView(self.game_session, self.cog)
                embed = discord.Embed(
                    title="📥 Draw Penalty",
                    description=f"You must draw **{self.game_session.draw_count}** cards!",
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
        
        # Show enhanced card selection interface
        if len(playable_cards) <= 25:  # Discord select menu limit
            view = EnhancedCardSelectionView(self.game_session, playable_cards, self.cog)
            embed = discord.Embed(
                title="🎯 Choose a Card to Play",
                description=f"You can play {len(playable_cards)} cards. Select one below:",
                color=discord.Color.green()
            )
            
            # Show current game state for context
            if self.game_session.deck.top_card:
                embed.add_field(
                    name="Current Card",
                    value=str(self.game_session.deck.top_card),
                    inline=True
                )
            
            if self.game_session.deck.current_color:
                embed.add_field(
                    name="Current Color",
                    value=self.game_session.deck.current_color.value,
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            # Too many cards, use simplified interface
            await interaction.followup.send(
                "❌ You have too many playable cards! This shouldn't happen in normal Uno.",
                ephemeral=True
            )


class UnoButton(discord.ui.Button):
    """Button for calling UNO"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(label="🔥 UNO", style=discord.ButtonStyle.danger, row=0)
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        success, message = self.game_session.call_uno(interaction.user.id)
        
        if success:
            # Update main game display
            await self.cog.update_game_display(self.game_session)
            embed = discord.Embed(
                title="🔥 UNO Called!",
                description=message,
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ Cannot Call UNO",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class ChallengeButton(discord.ui.Button):
    """Button for challenging Draw 4 cards"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(label="⚖️ Challenge", style=discord.ButtonStyle.secondary, row=1)
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        success, message = self.game_session.challenge_draw4(interaction.user.id)
        
        if success:
            # Update main game display
            await self.cog.update_game_display(self.game_session)
            embed = discord.Embed(
                title="⚖️ Draw 4 Challenge",
                description=message,
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="❌ Cannot Challenge",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class StatusButton(discord.ui.Button):
    """Enhanced status button"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(label="📊 Status", style=discord.ButtonStyle.secondary, row=1)
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        status = self.game_session.get_game_status()
        embed = discord.Embed(title="📊 Detailed Game Status", color=discord.Color.blue())
        
        # Game info
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
                if self.game_session.is_ai_player(current_player_id):
                    ai_player = self.game_session.get_ai_player(current_player_id)
                    player_name = f"🤖 {ai_player.name}" if ai_player else "🤖 AI Player"
                else:
                    player_name = f"<@{current_player_id}>"
                embed.add_field(name="🎮 Current Turn", value=player_name, inline=True)
            
            if status["draw_penalty"] > 0:
                embed.add_field(name="📥 Draw Penalty", value=f"{status['draw_penalty']} cards", inline=True)
            
            if status["challenge_window"]:
                embed.add_field(name="⚖️ Challenge Window", value="Draw 4 can be challenged!", inline=True)
            
            # Game duration
            duration = int(status["game_duration"])
            embed.add_field(name="⏱️ Duration", value=f"{duration // 60}m {duration % 60}s", inline=True)
            
            # Deck info
            remaining_cards = len(self.game_session.deck.draw_pile)
            discard_cards = len(self.game_session.deck.discard_pile)
            embed.add_field(name="🔢 Cards Left", value=f"Draw: {remaining_cards}, Discard: {discard_cards}", inline=True)
            
            # UNO status
            uno_players = [pid for pid, called in status["uno_called"].items() if called]
            if uno_players:
                uno_list = ", ".join([f"<@{pid}>" for pid in uno_players])
                embed.add_field(name="🔥 UNO Called", value=uno_list, inline=False)
            
            # Player detailed info
            player_info = []
            for player_id, card_count in status["card_counts"].items():
                if self.game_session.is_ai_player(player_id):
                    ai_player = self.game_session.get_ai_player(player_id)
                    name = f"🤖 {ai_player.name}" if ai_player else "🤖 AI"
                else:
                    name = f"<@{player_id}>"
                
                line = f"{name}: {card_count} cards"
                
                # Add status indicators
                if status["current_player"] == player_id:
                    line += " 🎯"
                if card_count == 1:
                    line += " 🔥"
                if status["uno_called"].get(player_id, False):
                    line += " (UNO)"
                
                player_info.append(line)
            
            embed.add_field(name="👥 Players", value="\n".join(player_info), inline=False)
            
            # Settings info
            settings = []
            if self.game_session.settings.get("draw_stacking"):
                settings.append("📚 Stacking")
            if self.game_session.settings.get("challenge_draw4"):
                settings.append("⚖️ Challenges")
            if self.game_session.settings.get("uno_penalty"):
                settings.append("🔥 UNO Penalty")
            
            if settings:
                embed.add_field(name="⚙️ Active Rules", value=" • ".join(settings), inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class EnhancedCardSelectionView(discord.ui.View):
    """Enhanced view for selecting which card to play"""
    
    def __init__(self, game_session: UnoGameSession, playable_cards: List[UnoCard], cog):
        super().__init__(timeout=300)  # 5 minutes
        self.game_session = game_session
        self.playable_cards = playable_cards
        self.cog = cog
        
        # Group cards by type for better organization
        self._add_card_selection_components()
    
    def _add_card_selection_components(self):
        """Add organized card selection components"""
        # Group cards by type
        number_cards = [c for c in self.playable_cards if c.card_type == UnoCardType.NUMBER]
        action_cards = [c for c in self.playable_cards if c.card_type in [UnoCardType.SKIP, UnoCardType.REVERSE, UnoCardType.DRAW2]]
        wild_cards = [c for c in self.playable_cards if c.color == UnoColor.WILD]
        
        # Add dropdowns for each category
        if number_cards:
            self.add_item(CardTypeDropdown("Number Cards", number_cards, self.game_session, self.cog))
        
        if action_cards:
            self.add_item(CardTypeDropdown("Action Cards", action_cards, self.game_session, self.cog))
        
        if wild_cards:
            self.add_item(CardTypeDropdown("Wild Cards", wild_cards, self.game_session, self.cog))


class CardTypeDropdown(discord.ui.Select):
    """Dropdown for specific card types"""
    
    def __init__(self, category: str, cards: List[UnoCard], game_session: UnoGameSession, cog):
        self.game_session = game_session
        self.cog = cog
        self.cards = cards
        
        # Create options for each card
        options = []
        for i, card in enumerate(cards):
            emoji = get_card_emoji(card)
            options.append(discord.SelectOption(
                label=card.display_name,
                description=f"Play this {card.color.value.lower()} card",
                emoji=emoji,
                value=str(i)
            ))
        
        super().__init__(
            placeholder=f"Choose from {category} ({len(cards)})...",
            options=options,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        card_index = int(self.values[0])
        selected_card = self.cards[card_index]
        
        # If it's a wild card, need to select color
        if selected_card.color == UnoColor.WILD:
            view = EnhancedColorSelectionView(self.game_session, selected_card, self.cog)
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


class EnhancedColorSelectionView(discord.ui.View):
    """Enhanced view for selecting color after playing wild card"""
    
    def __init__(self, game_session: UnoGameSession, wild_card: UnoCard, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.wild_card = wild_card
        self.cog = cog
        
        # Add color buttons with enhanced styling
        colors = [UnoColor.RED, UnoColor.GREEN, UnoColor.YELLOW, UnoColor.BLUE]
        for color in colors:
            button = EnhancedColorButton(color, game_session, wild_card, cog)
            self.add_item(button)


class EnhancedColorButton(discord.ui.Button):
    """Enhanced button for selecting wild card color"""
    
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
    """Enhanced view for drawing cards when no playable cards"""
    
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
            
            # Show what was drawn
            if cards:
                card_list = "\n".join([f"{get_card_emoji(card)} {card.display_name}" for card in cards])
                embed.add_field(name="Cards Drawn", value=card_list, inline=False)
        else:
            embed = discord.Embed(
                title="❌ Cannot Draw",
                description=message,
                color=discord.Color.red()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)


class DrawStackingView(discord.ui.View):
    """View for handling draw stacking options"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.cog = cog
        
        # Check if player has stacking cards
        player_id = None  # This would need to be passed or determined
        if player_id:
            hand = self.game_session.get_player_hand(player_id)
            if hand:
                stackable_cards = [c for c in hand.cards if self.game_session._can_stack_card(c)]
                if stackable_cards:
                    # Add stacking option
                    self.add_item(StackCardButton(stackable_cards, self.game_session, self.cog))
    
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


class StackCardButton(discord.ui.Button):
    """Button for playing stacking cards"""
    
    def __init__(self, stackable_cards: List[UnoCard], game_session: UnoGameSession, cog):
        super().__init__(label="🔁 Stack Card", style=discord.ButtonStyle.secondary)
        self.stackable_cards = stackable_cards
        self.game_session = game_session
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Show card selection for stacking
        view = EnhancedCardSelectionView(self.game_session, self.stackable_cards, self.cog)
        embed = discord.Embed(
            title="🔁 Stack a Card",
            description="Choose a card to stack:",
            color=discord.Color.orange()
        )
        
        await interaction.edit_original_response(embed=embed, view=view)


class DrawPenaltyView(discord.ui.View):
    """View for handling draw penalties (Draw 2/4 cards) without stacking"""
    
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
    """Enhanced view for game lobby (joining/starting)"""
    
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
            reason = "Game is full" if len(self.game_session.players) >= self.game_session.settings["max_players"] else "Game already started or you're already in it"
            await interaction.followup.send(f"❌ Cannot join: {reason}", ephemeral=True)
    
    @discord.ui.button(label="🚀 Start Game", style=discord.ButtonStyle.primary)
    async def start_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        if interaction.user.id != self.game_session.host_id:
            await interaction.followup.send("❌ Only the host can start the game!", ephemeral=True)
            return
        
        total_players = len(self.game_session.players) + len(self.game_session.ai_players)
        min_players = self.game_session.settings["min_players"]
        
        if total_players < min_players:
            await interaction.followup.send(
                f"❌ Need at least {min_players} players to start! (Current: {total_players})",
                ephemeral=True
            )
            return
        
        success = self.game_session.start_game()
        
        if success:
            await self.cog.update_game_display(self.game_session)
            await interaction.followup.send("🎮 **Game Started!**", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to start game!", ephemeral=True)
    
    @discord.ui.button(label="🤖 Add AI", style=discord.ButtonStyle.secondary)
    async def add_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id != self.game_session.host_id:
            await interaction.followup.send("❌ Only the host can add AI players!", ephemeral=True)
            return
        
        if not self.game_session.settings.get("ai_players", True):
            await interaction.followup.send("❌ AI players are disabled on this server!", ephemeral=True)
            return
        
        # Show AI difficulty selection
        view = AISelectionView(self.game_session, self.cog)
        embed = discord.Embed(
            title="🤖 Add AI Player",
            description="Choose AI difficulty:",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
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


class AISelectionView(discord.ui.View):
    """View for selecting AI difficulty"""
    
    def __init__(self, game_session: UnoGameSession, cog):
        super().__init__(timeout=300)
        self.game_session = game_session
        self.cog = cog
    
    @discord.ui.button(label="🟢 Easy", style=discord.ButtonStyle.success)
    async def add_easy_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_ai(interaction, "easy")
    
    @discord.ui.button(label="🟡 Medium", style=discord.ButtonStyle.primary)
    async def add_medium_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_ai(interaction, "medium")
    
    @discord.ui.button(label="🔴 Hard", style=discord.ButtonStyle.danger)
    async def add_hard_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._add_ai(interaction, "hard")
    
    async def _add_ai(self, interaction: discord.Interaction, difficulty: str):
        await interaction.response.defer()
        
        ai_player = self.game_session.add_ai_player(difficulty)
        if ai_player:
            await self.cog.update_lobby_display(self.game_session)
            embed = discord.Embed(
                title="✅ AI Player Added",
                description=f"Added **{ai_player.name}** ({difficulty} difficulty)",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Cannot Add AI",
                description="Game is full or max AI limit reached!",
                color=discord.Color.red()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)


class StatsView(discord.ui.View):
    """View for displaying statistics and achievements"""
    
    def __init__(self, user_stats: Dict[str, Any], cog):
        super().__init__(timeout=300)
        self.user_stats = user_stats
        self.cog = cog
    
    @discord.ui.button(label="🏆 Achievements", style=discord.ButtonStyle.primary)
    async def show_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🏆 Your Achievements",
            color=discord.Color.gold()
        )
        
        achievements = self.user_stats.get("achievements", [])
        if achievements:
            achievement_text = "\n".join([f"🏅 {ach}" for ach in achievements])
            embed.description = achievement_text
        else:
            embed.description = "No achievements yet! Keep playing to unlock them!"
        
        # Show available achievements
        all_achievements = stats_manager.achievement_definitions
        unlocked = set(achievements)
        
        available = []
        for name, data in all_achievements.items():
            if name not in unlocked:
                available.append(f"🔒 {name} - {data['description']}")
        
        if available:
            embed.add_field(
                name="Available Achievements",
                value="\n".join(available[:10]) + ("..." if len(available) > 10 else ""),
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📊 Detailed Stats", style=discord.ButtonStyle.secondary)
    async def show_detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="📊 Detailed Statistics",
            color=discord.Color.blue()
        )
        
        # Calculate additional stats
        total_score = stats_manager.calculate_player_score(self.user_stats)
        rank_name, rank_desc = stats_manager.get_player_rank(total_score)
        
        embed.add_field(name="🎯 Overall Score", value=f"{total_score:,}", inline=True)
        embed.add_field(name="🏅 Rank", value=rank_name, inline=True)
        embed.add_field(name="📝 Description", value=rank_desc, inline=True)
        
        # Win rate calculation
        games_played = self.user_stats.get("games_played", 0)
        games_won = self.user_stats.get("games_won", 0)
        win_rate = (games_won / games_played * 100) if games_played > 0 else 0
        
        embed.add_field(name="📈 Win Rate", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="🎮 Games Played", value=f"{games_played:,}", inline=True)
        embed.add_field(name="🏆 Games Won", value=f"{games_won:,}", inline=True)
        
        # Challenge stats
        challenges = self.user_stats.get("draw4_challenged", 0)
        successful = self.user_stats.get("draw4_successful_challenges", 0)
        challenge_rate = (successful / challenges * 100) if challenges > 0 else 0
        
        embed.add_field(name="⚖️ Challenge Rate", value=f"{challenge_rate:.1f}%", inline=True)
        embed.add_field(name="🔥 UNO Calls", value=f"{self.user_stats.get('uno_calls', 0):,}", inline=True)
        embed.add_field(name="⚠️ UNO Penalties", value=f"{self.user_stats.get('uno_penalties', 0):,}", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class ConfigView(discord.ui.View):
    """View for server configuration management"""
    
    def __init__(self, current_settings: Dict[str, Any], cog):
        super().__init__(timeout=600)
        self.current_settings = current_settings
        self.cog = cog
    
    @discord.ui.button(label="🎮 Game Settings", style=discord.ButtonStyle.primary)
    async def game_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🎮 Game Settings",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="🃏 Starting Cards", value=self.current_settings["starting_cards"], inline=True)
        embed.add_field(name="👥 Max Players", value=self.current_settings["max_players"], inline=True)
        embed.add_field(name="⏱️ Timeout", value=f"{self.current_settings['timeout_minutes']} min", inline=True)
        
        embed.set_footer(text="Use 'uno set <setting> <value>' to change these settings")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="📏 Rule Settings", style=discord.ButtonStyle.secondary)
    async def rule_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="📏 Rule Settings",
            color=discord.Color.green()
        )
        
        embed.add_field(name="🔥 UNO Penalty", value="✅" if self.current_settings["uno_penalty"] else "❌", inline=True)
        embed.add_field(name="📚 Draw Stacking", value="✅" if self.current_settings["draw_stacking"] else "❌", inline=True)
        embed.add_field(name="⚖️ Draw 4 Challenge", value="✅" if self.current_settings["challenge_draw4"] else "❌", inline=True)
        
        embed.set_footer(text="Use 'uno set <setting> true/false' to change these settings")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🤖 AI Settings", style=discord.ButtonStyle.success)
    async def ai_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🤖 AI Settings",
            color=discord.Color.purple()
        )
        
        embed.add_field(name="🤖 AI Players Enabled", value="✅" if self.current_settings["ai_players"] else "❌", inline=True)
        embed.add_field(name="🎯 Max AI Players", value=self.current_settings["max_ai_players"], inline=True)
        embed.add_field(name="⏰ Auto-start Delay", value=f"{self.current_settings['auto_start_delay']}s", inline=True)
        
        embed.set_footer(text="Use 'uno set <setting> <value>' to change these settings")
        
        await interaction.followup.send(embed=embed, ephemeral=True)