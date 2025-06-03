"""
Enhanced Uno Game Session Management with Advanced Features
"""
import asyncio
import random
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import discord
from datetime import datetime, timedelta
from .cards import UnoDeck, PlayerHand, UnoCard, UnoColor, UnoCardType


class GameState(Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    FINISHED = "finished"
    PAUSED = "paused"


class GameDirection(Enum):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = -1


class UnoAction(Enum):
    PLAY_CARD = "play_card"
    DRAW_CARD = "draw_card"
    CALL_UNO = "call_uno"
    CHALLENGE_DRAW4 = "challenge_draw4"
    PASS_TURN = "pass_turn"


class PlayerStats:
    """Track individual player statistics"""
    
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.games_played = 0
        self.games_won = 0
        self.cards_played = 0
        self.draw4_challenged = 0
        self.draw4_successful_challenges = 0
        self.uno_calls = 0
        self.uno_penalties = 0
        self.fastest_win = None  # Time in seconds
        self.total_play_time = 0
        self.favorite_color = None
        self.achievements = set()
    
    @property
    def win_rate(self) -> float:
        return (self.games_won / self.games_played) if self.games_played > 0 else 0.0
    
    @property
    def challenge_success_rate(self) -> float:
        return (self.draw4_successful_challenges / self.draw4_challenged) if self.draw4_challenged > 0 else 0.0


class AIPlayer:
    """AI player for filling games"""
    
    def __init__(self, name: str, difficulty: str = "medium"):
        self.name = name
        self.difficulty = difficulty  # easy, medium, hard
        self.player_id = f"ai_{name.lower()}_{random.randint(1000, 9999)}"
        self.is_ai = True
    
    def choose_card(self, hand: PlayerHand, top_card: UnoCard, current_color: Optional[UnoColor]) -> Optional[UnoCard]:
        """AI logic for choosing a card to play"""
        playable = hand.get_playable_cards(top_card, current_color)
        
        if not playable:
            return None
        
        if self.difficulty == "easy":
            return random.choice(playable)
        
        elif self.difficulty == "medium":
            # Prefer action cards and wilds
            action_cards = [c for c in playable if c.card_type != UnoCardType.NUMBER]
            if action_cards:
                return random.choice(action_cards)
            return random.choice(playable)
        
        elif self.difficulty == "hard":
            # Strategic play: save wilds, play high numbers, prefer matching colors
            # This is a simplified strategy
            
            # If only one card left, play anything
            if len(hand.cards) == 1:
                return playable[0]
            
            # Avoid playing wilds unless necessary
            non_wilds = [c for c in playable if c.color != UnoColor.WILD]
            if non_wilds and len(non_wilds) < len(playable):
                playable = non_wilds
            
            # Prefer action cards to disrupt opponents
            action_cards = [c for c in playable if c.card_type in [UnoCardType.SKIP, UnoCardType.REVERSE, UnoCardType.DRAW2]]
            if action_cards and len(hand.cards) > 3:
                return random.choice(action_cards)
            
            # Play highest number card to reduce hand value
            number_cards = [c for c in playable if c.card_type == UnoCardType.NUMBER]
            if number_cards:
                return max(number_cards, key=lambda c: c.value or 0)
            
            return random.choice(playable)
    
    def choose_wild_color(self, hand: PlayerHand) -> UnoColor:
        """Choose color for wild card"""
        # Count cards by color
        color_counts = {color: 0 for color in [UnoColor.RED, UnoColor.GREEN, UnoColor.YELLOW, UnoColor.BLUE]}
        
        for card in hand.cards:
            if card.color in color_counts:
                color_counts[card.color] += 1
        
        # Choose color with most cards
        return max(color_counts, key=color_counts.get)


class UnoGameSession:
    """Enhanced Uno game session with advanced features"""
    
    def __init__(self, channel_id: int, host_id: int, settings: Dict[str, Any] = None):
        self.channel_id = channel_id
        self.host_id = host_id
        self.state = GameState.LOBBY
        self.players: List[int] = [host_id]  # Player IDs in turn order
        self.ai_players: List[AIPlayer] = []
        self.hands: Dict[int, PlayerHand] = {host_id: PlayerHand(host_id)}
        self.deck = UnoDeck()
        self.current_player_index = 0
        self.direction = GameDirection.CLOCKWISE
        self.draw_count = 0  # For stacking draw cards
        self.last_activity = discord.utils.utcnow()
        self.game_message: Optional[discord.Message] = None
        self.game_start_time: Optional[datetime] = None
        
        # Game history for replays and statistics
        self.action_history: List[Dict[str, Any]] = []
        self.round_number = 0
        
        # UNO callout tracking
        self.uno_called: Dict[int, bool] = {}
        self.pending_uno_penalty: Dict[int, bool] = {}
        
        # Draw 4 challenge system
        self.last_draw4_player: Optional[int] = None
        self.last_draw4_card: Optional[UnoCard] = None
        self.challenge_window_open = False
        
        # Settings with defaults
        self.settings = {
            "starting_cards": 7,
            "max_players": 10,
            "min_players": 2,
            "timeout_minutes": 30,
            "uno_penalty": True,
            "draw_stacking": True,
            "challenge_draw4": True,
            "ai_players": True,
            "max_ai_players": 3,
            "persistent_games": True,
            **( settings or {})
        }
    
    def add_player(self, player_id: int) -> bool:
        """Add a player to the game. Returns True if successful."""
        if (self.state != GameState.LOBBY or 
            player_id in self.players or 
            len(self.players) >= self.settings["max_players"]):
            return False
        
        self.players.append(player_id)
        self.hands[player_id] = PlayerHand(player_id)
        self.uno_called[player_id] = False
        self.pending_uno_penalty[player_id] = False
        self.last_activity = discord.utils.utcnow()
        return True
    
    def add_ai_player(self, difficulty: str = "medium") -> Optional[AIPlayer]:
        """Add an AI player to the game"""
        if (len(self.ai_players) >= self.settings["max_ai_players"] or 
            len(self.players) + len(self.ai_players) >= self.settings["max_players"]):
            return None
        
        ai_names = ["Bot Alice", "Bot Bob", "Bot Charlie", "Bot Diana", "Bot Eve"]
        used_names = [ai.name for ai in self.ai_players]
        available_names = [name for name in ai_names if name not in used_names]
        
        if not available_names:
            return None
        
        ai_player = AIPlayer(random.choice(available_names), difficulty)
        self.ai_players.append(ai_player)
        
        # Add AI to players list and create hand
        self.players.append(ai_player.player_id)
        self.hands[ai_player.player_id] = PlayerHand(ai_player.player_id)
        self.uno_called[ai_player.player_id] = False
        
        return ai_player
    
    def remove_player(self, player_id: int) -> bool:
        """Remove a player from the game. Returns True if successful."""
        if player_id not in self.players:
            return False
        
        # Remove from AI players if applicable
        self.ai_players = [ai for ai in self.ai_players if ai.player_id != player_id]
        
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
        if player_id in self.hands:
            del self.hands[player_id]
        if player_id in self.uno_called:
            del self.uno_called[player_id]
        if player_id in self.pending_uno_penalty:
            del self.pending_uno_penalty[player_id]
        
        # Check if game should end
        if len(self.players) < self.settings["min_players"]:
            self.state = GameState.FINISHED
        
        self.last_activity = discord.utils.utcnow()
        return True
    
    def start_game(self) -> bool:
        """Start the game if conditions are met"""
        total_players = len(self.players) + len(self.ai_players)
        if (self.state != GameState.LOBBY or 
            total_players < self.settings["min_players"]):
            return False
        
        self.state = GameState.PLAYING
        self.game_start_time = discord.utils.utcnow()
        
        # Deal starting cards to all players
        all_player_ids = self.players.copy()
        for player_id in all_player_ids:
            hand = self.hands[player_id]
            for _ in range(self.settings["starting_cards"]):
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
        self._log_action("game_started", {"players": len(self.players), "ai_players": len(self.ai_players)})
        return True
    
    def call_uno(self, player_id: int) -> Tuple[bool, str]:
        """Player calls UNO"""
        if self.state != GameState.PLAYING or player_id not in self.players:
            return False, "Invalid game state or player"
        
        hand = self.hands.get(player_id)
        if not hand:
            return False, "Player not found"
        
        if hand.card_count != 1:
            return False, "Can only call UNO with exactly 1 card"
        
        self.uno_called[player_id] = True
        self.pending_uno_penalty[player_id] = False
        self._log_action("uno_called", {"player": player_id, "cards_left": hand.card_count})
        
        return True, f"<@{player_id}> called **UNO!** 🔥"
    
    def challenge_draw4(self, challenger_id: int) -> Tuple[bool, str]:
        """Challenge the last played Draw 4 card"""
        if not self.settings["challenge_draw4"]:
            return False, "Draw 4 challenges are disabled"
        
        if not self.challenge_window_open or not self.last_draw4_player:
            return False, "No Draw 4 to challenge"
        
        if challenger_id == self.last_draw4_player:
            return False, "Cannot challenge your own card"
        
        if not self.is_current_player(challenger_id):
            return False, "Only the affected player can challenge"
        
        # Check if the Draw 4 was legal
        # Draw 4 is illegal if the player had other playable cards
        draw4_player_hand = self.hands.get(self.last_draw4_player)
        if not draw4_player_hand:
            return False, "Invalid game state"
        
        # Simulate the game state before the Draw 4 was played
        # This is simplified - in a real implementation, you'd want to store more history
        playable_cards = []
        for card in draw4_player_hand.cards:
            if (card != self.last_draw4_card and 
                card.color != UnoColor.WILD and
                card.can_play_on(self.deck.top_card, self.deck.current_color)):
                playable_cards.append(card)
        
        challenge_successful = len(playable_cards) > 0
        
        if challenge_successful:
            # Challenge successful - Draw 4 player draws 4, challenger draws nothing
            for _ in range(4):
                card = self.deck.draw_card()
                if card:
                    draw4_player_hand.add_card(card)
            
            self.draw_count = 0  # Reset draw count
            message = f"🎯 **Challenge successful!** <@{self.last_draw4_player}> draws 4 cards instead!"
        else:
            # Challenge failed - challenger draws 6 (4 + 2 penalty)
            challenger_hand = self.hands.get(challenger_id)
            if challenger_hand:
                for _ in range(6):
                    card = self.deck.draw_card()
                    if card:
                        challenger_hand.add_card(card)
            
            self.draw_count = 0  # Reset draw count
            message = f"❌ **Challenge failed!** <@{challenger_id}> draws 6 cards (4 + 2 penalty)!"
        
        self.challenge_window_open = False
        self.last_draw4_player = None
        self.last_draw4_card = None
        
        # Move to next player
        self._next_turn()
        
        self._log_action("draw4_challenged", {
            "challenger": challenger_id,
            "draw4_player": self.last_draw4_player,
            "successful": challenge_successful
        })
        
        return True, message
    
    def play_card(self, player_id: int, card: UnoCard, declared_color: Optional[UnoColor] = None) -> Tuple[bool, str]:
        """Play a card for a player. Returns (success, message)."""
        if self.state != GameState.PLAYING:
            return False, "Game is not in progress"
        
        if not self.is_current_player(player_id):
            return False, "It's not your turn"
        
        hand = self.hands[player_id]
        if not hand.has_card(card):
            return False, "You don't have that card"
        
        # Check draw stacking rules
        if self.draw_count > 0 and self.settings["draw_stacking"]:
            # Can only play stacking cards or must draw
            if not self._can_stack_card(card):
                return False, f"Must play a stacking card or draw {self.draw_count} cards"
        
        # Check if card can be played
        top_card = self.deck.top_card
        if not card.can_play_on(top_card, self.deck.current_color):
            return False, f"Cannot play {card} on {top_card}"
        
        # Validate wild card color declaration
        if card.color == UnoColor.WILD and not declared_color:
            return False, "Must declare a color for wild cards"
        
        # Check UNO callout requirements
        if hand.card_count == 2 and self.settings["uno_penalty"]:
            # Player will have 1 card after playing, check if UNO was called
            if not self.uno_called.get(player_id, False):
                self.pending_uno_penalty[player_id] = True
        
        # Play the card
        hand.remove_card(card)
        self.deck.play_card(card, declared_color)
        
        # Handle card stacking
        if self.settings["draw_stacking"] and card.card_type in [UnoCardType.DRAW2, UnoCardType.WILD_DRAW4]:
            if card.card_type == UnoCardType.DRAW2:
                self.draw_count += 2
            elif card.card_type == UnoCardType.WILD_DRAW4:
                self.draw_count += 4
                # Set up challenge window
                self.challenge_window_open = True
                self.last_draw4_player = player_id
                self.last_draw4_card = card
        
        # Apply UNO penalty if needed
        uno_penalty_message = ""
        if self.pending_uno_penalty.get(player_id) and hand.card_count == 1:
            penalty_cards = 2
            for _ in range(penalty_cards):
                penalty_card = self.deck.draw_card()
                if penalty_card:
                    hand.add_card(penalty_card)
            uno_penalty_message = f"\n⚠️ <@{player_id}> draws {penalty_cards} cards for not calling UNO!"
            self.pending_uno_penalty[player_id] = False
        
        # Handle card effects
        effect_message = self._handle_card_effect(card)
        
        # Check for win condition
        if hand.is_empty:
            self.state = GameState.FINISHED
            game_duration = (discord.utils.utcnow() - self.game_start_time).total_seconds() if self.game_start_time else 0
            self._log_action("game_won", {"winner": player_id, "duration": game_duration})
            return True, f"{effect_message}\n🎉 **Game Over!** <@{player_id}> wins!{uno_penalty_message}"
        
        # Check for Uno call (1 card left)
        uno_message = ""
        if hand.card_count == 1:
            if self.uno_called.get(player_id, False):
                uno_message = f"\n🔥 **UNO!** <@{player_id}> has one card left!"
            else:
                uno_message = f"\n🔥 <@{player_id}> has one card left! (Remember to call UNO!)"
        
        # Move to next player (if not already moved by card effect)
        if card.card_type not in [UnoCardType.SKIP, UnoCardType.REVERSE]:
            self._next_turn()
        
        self.last_activity = discord.utils.utcnow()
        self._log_action("card_played", {"player": player_id, "card": str(card), "declared_color": declared_color})
        
        return True, f"{effect_message}{uno_message}{uno_penalty_message}"
    
    def _can_stack_card(self, card: UnoCard) -> bool:
        """Check if a card can be stacked on the current draw penalty"""
        if self.draw_count == 0:
            return True
        
        # Can stack Draw 2 on Draw 2, Draw 4 on Draw 4
        last_card = self.deck.top_card
        if not last_card:
            return False
        
        if (last_card.card_type == UnoCardType.DRAW2 and 
            card.card_type == UnoCardType.DRAW2):
            return True
        
        if (last_card.card_type == UnoCardType.WILD_DRAW4 and 
            card.card_type == UnoCardType.WILD_DRAW4):
            return True
        
        return False
    
    def draw_card(self, player_id: int, count: int = None) -> Tuple[bool, str, List[UnoCard]]:
        """Player draws cards. Returns (success, message, cards_drawn)."""
        if self.state != GameState.PLAYING:
            return False, "Game is not in progress", []
        
        if not self.is_current_player(player_id):
            return False, "It's not your turn", []
        
        hand = self.hands[player_id]
        drawn_cards = []
        
        # Determine how many cards to draw
        if count is None:
            count = max(1, self.draw_count)
        
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
        
        # Reset challenge window
        self.challenge_window_open = False
        
        # Move to next player
        self._next_turn()
        
        self.last_activity = discord.utils.utcnow()
        card_names = ", ".join(card.display_name for card in drawn_cards)
        self._log_action("cards_drawn", {"player": player_id, "count": len(drawn_cards)})
        
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
            if not skip_draw and not self.settings["draw_stacking"]:
                self.draw_count += 2
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw 2 cards!"
            elif not skip_draw:
                # Stacking enabled, just move turn
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw {self.draw_count} cards or stack!"
            
        elif card.card_type == UnoCardType.WILD_DRAW4:
            if not skip_draw and not self.settings["draw_stacking"]:
                self.draw_count += 4
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw 4 cards!"
                if self.settings["challenge_draw4"]:
                    message += " (Can challenge!)"
            elif not skip_draw:
                # Stacking enabled, just move turn
                self._next_turn()
                next_player = self.get_current_player()
                message += f"\n📥 <@{next_player}> must draw {self.draw_count} cards or stack!"
            
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
    
    def is_ai_player(self, player_id: int) -> bool:
        """Check if a player is AI"""
        return any(ai.player_id == player_id for ai in self.ai_players)
    
    def get_ai_player(self, player_id: int) -> Optional[AIPlayer]:
        """Get AI player by ID"""
        for ai in self.ai_players:
            if ai.player_id == player_id:
                return ai
        return None
    
    def _log_action(self, action_type: str, data: Dict[str, Any]):
        """Log game action for statistics and replay"""
        self.action_history.append({
            "timestamp": discord.utils.utcnow().isoformat(),
            "round": self.round_number,
            "action": action_type,
            "data": data
        })
    
    def get_game_status(self) -> Dict:
        """Get current game status for display"""
        status = {
            "state": self.state.value,
            "players": len(self.players),
            "ai_players": len(self.ai_players),
            "current_player": self.get_current_player() if self.state == GameState.PLAYING else None,
            "top_card": str(self.deck.top_card) if self.deck.top_card else None,
            "current_color": self.deck.current_color.value if self.deck.current_color else None,
            "direction": "↻" if self.direction == GameDirection.CLOCKWISE else "↺",
            "draw_penalty": self.draw_count,
            "card_counts": {pid: len(hand) for pid, hand in self.hands.items()},
            "uno_called": self.uno_called,
            "challenge_window": self.challenge_window_open,
            "game_duration": (discord.utils.utcnow() - self.game_start_time).total_seconds() if self.game_start_time else 0,
            "settings": self.settings
        }
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize game state for persistence"""
        return {
            "channel_id": self.channel_id,
            "host_id": self.host_id,
            "state": self.state.value,
            "players": self.players,
            "ai_players": [{"name": ai.name, "difficulty": ai.difficulty, "player_id": ai.player_id} for ai in self.ai_players],
            "hands": {pid: [{"color": c.color.value, "type": c.card_type.value, "value": c.value} for c in hand.cards] for pid, hand in self.hands.items()},
            "deck_discard": [{"color": c.color.value, "type": c.card_type.value, "value": c.value} for c in self.deck.discard_pile],
            "current_player_index": self.current_player_index,
            "direction": self.direction.value,
            "draw_count": self.draw_count,
            "current_color": self.deck.current_color.value if self.deck.current_color else None,
            "settings": self.settings,
            "uno_called": self.uno_called,
            "game_start_time": self.game_start_time.isoformat() if self.game_start_time else None,
            "action_history": self.action_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnoGameSession':
        """Deserialize game state from persistence"""
        # This is a complex operation - simplified implementation
        # In production, you'd want more robust serialization
        game = cls(data["channel_id"], data["host_id"], data.get("settings", {}))
        game.state = GameState(data["state"])
        game.players = data["players"]
        # ... additional restoration logic would go here
        return game
    
    def is_expired(self) -> bool:
        """Check if game has been inactive too long"""
        if not self.last_activity:
            return False
        
        time_diff = discord.utils.utcnow() - self.last_activity
        return time_diff.total_seconds() > (self.settings["timeout_minutes"] * 60)
    
    def cleanup(self):
        """Clean up game resources"""
        self.state = GameState.FINISHED
        self.players.clear()
        self.ai_players.clear()
        self.hands.clear()
        self.game_message = None