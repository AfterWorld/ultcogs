"""
Card and Deck management for Uno game
"""
import random
from enum import Enum
from typing import List, Optional


class UnoColor(Enum):
    RED = "Red"
    GREEN = "Green"
    YELLOW = "Yellow"
    BLUE = "Blue"
    WILD = "Wild"


class UnoCardType(Enum):
    NUMBER = "number"
    SKIP = "skip"
    REVERSE = "reverse"
    DRAW2 = "draw2"
    WILD = "Wild_Card"
    WILD_DRAW4 = "draw4"


class UnoCard:
    """Represents a single Uno card"""
    
    def __init__(self, color: UnoColor, card_type: UnoCardType, value: Optional[int] = None):
        self.color = color
        self.card_type = card_type
        self.value = value
        
        if self.card_type == UnoCardType.NUMBER and self.value is None:
            raise ValueError("Number cards must have a value")
    
    @property
    def filename(self) -> str:
        """Returns the filename for this card's image"""
        if self.color == UnoColor.WILD:
            if self.card_type == UnoCardType.WILD:
                return "Wild_Card.png"
            elif self.card_type == UnoCardType.WILD_DRAW4:
                return "Wild_draw4.png"
        else:
            if self.card_type == UnoCardType.NUMBER:
                return f"{self.color.value}_{self.value}.png"
            elif self.card_type == UnoCardType.SKIP:
                return f"{self.color.value}_skip.png"
            elif self.card_type == UnoCardType.REVERSE:
                return f"{self.color.value}_reverse.png"
            elif self.card_type == UnoCardType.DRAW2:
                return f"{self.color.value}_draw2.png"
        
        raise ValueError(f"Invalid card combination: {self.color}, {self.card_type}")
    
    @property
    def display_name(self) -> str:
        """Human-readable card name"""
        if self.color == UnoColor.WILD:
            return f"Wild {self.card_type.value.replace('_', ' ').title()}"
        elif self.card_type == UnoCardType.NUMBER:
            return f"{self.color.value} {self.value}"
        else:
            return f"{self.color.value} {self.card_type.value.replace('_', ' ').title()}"
    
    def can_play_on(self, other: 'UnoCard', declared_color: Optional[UnoColor] = None) -> bool:
        """Check if this card can be played on another card"""
        # Wild cards can always be played
        if self.color == UnoColor.WILD:
            return True
        
        # If the top card is wild, check against declared color
        if other.color == UnoColor.WILD and declared_color:
            return self.color == declared_color
        
        # Same color or same type/value
        if self.color == other.color:
            return True
        
        if self.card_type == other.card_type and self.card_type != UnoCardType.NUMBER:
            return True
        
        if (self.card_type == UnoCardType.NUMBER and 
            other.card_type == UnoCardType.NUMBER and 
            self.value == other.value):
            return True
        
        return False
    
    def __str__(self):
        return self.display_name
    
    def __repr__(self):
        return f"UnoCard({self.color}, {self.card_type}, {self.value})"


class UnoDeck:
    """Manages the Uno deck and discard pile"""
    
    def __init__(self):
        self.draw_pile: List[UnoCard] = []
        self.discard_pile: List[UnoCard] = []
        self.current_color: Optional[UnoColor] = None  # For wild cards
        self._create_deck()
        self.shuffle()
    
    def _create_deck(self):
        """Create a standard Uno deck"""
        self.draw_pile = []
        
        # Regular colored cards
        for color in [UnoColor.RED, UnoColor.GREEN, UnoColor.YELLOW, UnoColor.BLUE]:
            # Number cards: 0 (1 copy), 1-9 (2 copies each)
            self.draw_pile.append(UnoCard(color, UnoCardType.NUMBER, 0))
            for value in range(1, 10):
                self.draw_pile.append(UnoCard(color, UnoCardType.NUMBER, value))
                self.draw_pile.append(UnoCard(color, UnoCardType.NUMBER, value))
            
            # Action cards (2 copies each)
            for _ in range(2):
                self.draw_pile.append(UnoCard(color, UnoCardType.SKIP))
                self.draw_pile.append(UnoCard(color, UnoCardType.REVERSE))
                self.draw_pile.append(UnoCard(color, UnoCardType.DRAW2))
        
        # Wild cards (4 copies each)
        for _ in range(4):
            self.draw_pile.append(UnoCard(UnoColor.WILD, UnoCardType.WILD))
            self.draw_pile.append(UnoCard(UnoColor.WILD, UnoCardType.WILD_DRAW4))
    
    def shuffle(self):
        """Shuffle the draw pile"""
        random.shuffle(self.draw_pile)
    
    def draw_card(self) -> Optional[UnoCard]:
        """Draw a card from the deck"""
        if not self.draw_pile:
            self._reshuffle_discard_pile()
        
        if self.draw_pile:
            return self.draw_pile.pop()
        return None
    
    def _reshuffle_discard_pile(self):
        """Move discard pile back to draw pile (except top card)"""
        if len(self.discard_pile) <= 1:
            return
        
        # Keep the top card in discard pile
        top_card = self.discard_pile[-1]
        self.draw_pile = self.discard_pile[:-1]
        self.discard_pile = [top_card]
        self.shuffle()
    
    def play_card(self, card: UnoCard, declared_color: Optional[UnoColor] = None):
        """Play a card to the discard pile"""
        self.discard_pile.append(card)
        
        # Set current color for wild cards
        if card.color == UnoColor.WILD:
            self.current_color = declared_color
        else:
            self.current_color = card.color
    
    @property
    def top_card(self) -> Optional[UnoCard]:
        """Get the top card of the discard pile"""
        return self.discard_pile[-1] if self.discard_pile else None
    
    def start_game(self) -> UnoCard:
        """Deal the first card to start the game"""
        # Make sure first card isn't a wild or action card
        while True:
            card = self.draw_card()
            if (card and card.color != UnoColor.WILD and 
                card.card_type == UnoCardType.NUMBER):
                self.play_card(card)
                return card
            elif card:
                # Put it back and shuffle
                self.draw_pile.append(card)
                self.shuffle()


class PlayerHand:
    """Manages a player's hand of cards"""
    
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.cards: List[UnoCard] = []
    
    def add_card(self, card: UnoCard):
        """Add a card to the hand"""
        self.cards.append(card)
    
    def remove_card(self, card: UnoCard) -> bool:
        """Remove a card from the hand"""
        if card in self.cards:
            self.cards.remove(card)
            return True
        return False
    
    def get_playable_cards(self, top_card: UnoCard, current_color: Optional[UnoColor] = None) -> List[UnoCard]:
        """Get all cards that can be played on the current top card"""
        return [card for card in self.cards if card.can_play_on(top_card, current_color)]
    
    def has_card(self, card: UnoCard) -> bool:
        """Check if the hand contains a specific card"""
        return card in self.cards
    
    @property
    def card_count(self) -> int:
        """Number of cards in hand"""
        return len(self.cards)
    
    @property
    def is_empty(self) -> bool:
        """Check if hand is empty (game won)"""
        return len(self.cards) == 0
    
    def __len__(self):
        return len(self.cards)
    
    def __iter__(self):
        return iter(self.cards)