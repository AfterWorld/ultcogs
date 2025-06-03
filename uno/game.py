"""
Uno Game Session Management
"""
import asyncio
from typing import Dict, List, Optional, Tuple
from enum import Enum
import discord
from .cards import UnoDeck, PlayerHand, UnoCard, UnoColor, UnoCardType


class GameState(Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    FINISHED = "finished"


class GameDirection(Enum):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = -1


class UnoGameSession:
    """Manages a single Uno game session"""
    
    def __init__(self, channel_id: int, host_id: int):
        self.channel_id = channel_id
        self.host_id = host_id
        self.state = GameState.LOBBY
        self.players: List[int] = [host_id]  # Player IDs in turn order
        self.hands: Dict[int, PlayerHand] = {host_id: PlayerHand(host_id)}
        self.deck = UnoDeck()
        self.current_player_index = 0
        self.direction = GameDirection.CLOCKWISE
        self.draw_count = 0  # For stacking draw cards
        self.last_activity = discord.utils.utcnow()
        self.game_message: Optional[discord.Message] = None
        self.max_players = 10
        self.min_players = 2
        
        # Game settings
        self.starting_cards = 7
        self.timeout_minutes = 30
    
    def add_player(self, player_id: int) -> bool:
        """Add a player to the game. Returns True if successful."""
        if (self.state != GameState.LOBBY or 
            player_id in self.players or 
            len(self.players) >= self.max_players):
            return False
        
        self.players.append(player_id)
        self.hands[player_id] = PlayerHand(player_id)
        self.last_activity = discord.utils.utcnow()
        return True
    
    def remove_player(self, player_id: int) -> bool:
        """Remove a player from the game. Returns True if successful."""
        if player_id not in self.players:
            return False
        
        # If game is in progress, this is more complex
        if self.state == GameState.PLAYING:
            player_index = self.players.index(player_id)
            
            # Adjust current player index if needed
            if player_index < self.current_player_index:
                self.current_player_index -= 1
            elif player_index == self.current_player_index:
                # Current player left, move to next
                if self.current_player_index >= len(self.players) - 1:
                    self.current_player_index = 0
        
        self.players.remove(player_id)
        del self.hands[player_id]
        
        # Check if game should end
        if len(self.players) < self.min_players:
            self.state = GameState.FINISHED
        
        self.last_activity = discord.utils.utcnow()
        return True
    
    def start_game(self) -> bool:
        """Start the game if conditions are met"""
        if (self.state != GameState.LOBBY or 
            len(self.players) < self.min_players):
            return False
        
        self.state = GameState.PLAYING
        
        # Deal starting cards to all players
        for player_id in self.players:
            hand = self.hands[player_id]
            for _ in range(self.starting_cards):
                card = self.deck.draw_card()
                if card:
                    hand.add_card(card)
        
        # Start with first card
        self.deck.start_game()
        
        # Check if first card requires special action
        top_card = self.deck.top_card
        if top_card:
            self._handle_card_effect(top_card, skip_draw=True)
        
        self.last_activity = discord.utils.utcnow()
        return True
    
    def play_card(self, player_id: int, card: UnoCard, declared_color: Optional[UnoColor] = None) -> Tuple[bool, str]:
        """
        Play a card for a player. Returns (success, message).
        """
        if self.state != GameState.PLAYING:
            return False, "Game is not in progress"
        
        if not self.is_current_player(player_id):
            return False, "It's not your turn"
        
        hand = self.hands[player_id]
        if not hand.has_card(card):
            return False, "You don't have that card"
        
        # Check if card can be played
        top_card = self.deck.top_card
        if not card.can_play_on(top_card, self.deck.current_color):
            return False, f"Cannot play {card} on {top_card}"
        
        # Validate wild card color declaration
        if card.color == UnoColor.WILD and not declared_color:
            return False, "Must declare a color for wild cards"
        
        # Play the card
        hand.remove_card(card)
        self.deck.play_card(card, declared_color)
        
        # Handle card effects
        effect_message = self._handle_card_effect(card)
        
        # Check for win condition
        if hand.is_empty:
            self.state = GameState.FINISHED
            return True, f"{effect_message}\n🎉 **Game Over!** <@{player_id}> wins!"
        
        # Check for Uno call (1 card left)
        uno_message = ""
        if hand.card_count == 1:
            uno_message = f"\n🔥 **UNO!** <@{player_id}> has one card left!"
        
        # Move to next player (if not already moved by card effect)
        if card.card_type not in [UnoCardType.SKIP, UnoCardType.REVERSE]:
            self._next_turn()
        
        self.last_activity = discord.utils.utcnow()
        return True, f"{effect_message}{uno_message}"
    
    def draw_card(self, player_id: int, count: int = 1) -> Tuple[bool, str, List[UnoCard]]:
        """
        Player draws cards. Returns (success, message, cards_drawn).
        """
        if self.state != GameState.PLAYING:
            return False, "Game is not in progress", []
        
        if not self.is_current_player(player_id):
            return False, "It's not your turn", []
        
        hand = self.hands[player_id]
        drawn_cards = []
        
        for _ in range(count):
            card = self.deck.draw_card()
            if card:
                hand.add_card(card)
                drawn_cards.append(card)
            else:
                break
        
        # Reset draw count after drawing
        if self.draw_count > 0:
            self.draw_count = 0
        
        # Move to next player
        self._next_turn()
        
        self.last_activity = discord.utils.utcnow()
        card_names = ", ".join(card.display_name for card in drawn_cards)
        return True, f"Drew {len(drawn_cards)} card(s): {card_names}", drawn_cards
    
    def _handle_card_effect(self, card: UnoCard, skip_draw: bool = False) -> str:
        """Handle special card effects"""
        message = f"Played: **{card}**"
        
        if card.card_type == UnoCardType.SKIP:
            self._next_turn()  # Skip next player
            next_player = self.get_current_player()
            message += f"\n⏭️ <@{next_player}> is skipped!"
            self._next_turn()  # Move to player after skipped
            
        elif card.card_type == UnoCardType.REVERSE:
            self.direction = (GameDirection.COUNTERCLOCKWISE 
                            if self.direction == GameDirection.CLOCKWISE 
                            else GameDirection.CLOCKWISE)
            message += "\n🔄 **Direction reversed!**"
            self._next_turn()
            
        elif card.card_type == UnoCardType.DRAW2:
            if not skip_draw:
                self.draw_count += 2
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw 2 cards!"
            
        elif card.card_type == UnoCardType.WILD_DRAW4:
            if not skip_draw:
                self.draw_count += 4
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw 4 cards!"
            
        elif card.card_type == UnoCardType.WILD:
            message += f"\n🌈 Color changed to **{self.deck.current_color.value}**"
            self._next_turn()
        
        elif card.card_type == UnoCardType.NUMBER:
            self._next_turn()
        
        return message
    
    def _next_turn(self):
        """Move to the next player"""
        if self.direction == GameDirection.CLOCKWISE:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
        else:
            self.current_player_index = (self.current_player_index - 1) % len(self.players)
    
    def get_current_player(self) -> int:
        """Get the current player's ID"""
        if self.players:
            return self.players[self.current_player_index]
        return 0
    
    def is_current_player(self, player_id: int) -> bool:
        """Check if it's a specific player's turn"""
        return player_id == self.get_current_player()
    
    def get_player_hand(self, player_id: int) -> Optional[PlayerHand]:
        """Get a player's hand"""
        return self.hands.get(player_id)
    
    def get_playable_cards(self, player_id: int) -> List[UnoCard]:
        """Get cards a player can currently play"""
        hand = self.hands.get(player_id)
        if not hand or not self.deck.top_card:
            return []
        
        return hand.get_playable_cards(self.deck.top_card, self.deck.current_color)
    
    def force_draw_penalty(self, player_id: int) -> bool:
        """Force a player to draw penalty cards"""
        if self.draw_count <= 0:
            return False
        
        hand = self.hands.get(player_id)
        if not hand:
            return False
        
        for _ in range(self.draw_count):
            card = self.deck.draw_card()
            if card:
                hand.add_card(card)
        
        self.draw_count = 0
        self._next_turn()
        self.last_activity = discord.utils.utcnow()
        return True
    
    def get_game_status(self) -> Dict:
        """Get current game status for display"""
        status = {
            "state": self.state.value,
            "players": len(self.players),
            "current_player": self.get_current_player() if self.state == GameState.PLAYING else None,
            "top_card": str(self.deck.top_card) if self.deck.top_card else None,
            "current_color": self.deck.current_color.value if self.deck.current_color else None,
            "direction": "↻" if self.direction == GameDirection.CLOCKWISE else "↺",
            "draw_penalty": self.draw_count,
            "card_counts": {pid: len(hand) for pid, hand in self.hands.items()}
        }
        return status
    
    def is_expired(self) -> bool:
        """Check if game has been inactive too long"""
        if not self.last_activity:
            return False
        
        time_diff = discord.utils.utcnow() - self.last_activity
        return time_diff.total_seconds() > (self.timeout_minutes * 60)
    
    def cleanup(self):
        """Clean up game resources"""
        self.state = GameState.FINISHED
        self.players.clear()
        self.hands.clear()
        self.game_message = None