"""Room management for multiplayer games."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass, field
from typing import Optional

from splendor.game.engine import GameEngine
from splendor.game.state import GameState
from splendor.game.actions import (
    Action,
    TakeThreeDifferentAction,
    TakeTwoSameAction,
    ReserveVisibleAction,
    ReserveFromDeckAction,
    PurchaseVisibleAction,
    PurchaseReservedAction,
)
from splendor.models.gems import GemType
from splendor.rl.policy import Policy, RandomPolicy

from schemas import (
    GameStateSchema,
    GemCollectionSchema,
    CardSchema,
    HiddenCardSchema,
    NobleSchema,
    PlayerSchema,
    SeatInfo,
    ActionSchema,
)


def generate_room_id() -> str:
    """Generate a 6-character room code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(6))


def generate_player_token() -> str:
    """Generate a secure player token."""
    return secrets.token_urlsafe(32)


@dataclass
class Seat:
    """A seat in a room."""
    player_name: Optional[str] = None
    player_token: Optional[str] = None
    is_bot: bool = False
    bot_policy: str = "random"
    is_connected: bool = False


@dataclass
class Room:
    """A game room."""
    room_id: str
    num_players: int
    host_seat: int = 0
    seats: list[Seat] = field(default_factory=list)
    engine: Optional[GameEngine] = None
    game_started: bool = False
    _bot_policies: dict[int, Policy] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize seats."""
        if not self.seats:
            self.seats = [Seat() for _ in range(self.num_players)]

    def get_seat_by_token(self, token: str) -> Optional[int]:
        """Find seat index by player token."""
        for i, seat in enumerate(self.seats):
            if seat.player_token == token:
                return i
        return None

    def add_player(self, name: str) -> tuple[str, int]:
        """Add a player to the next available seat. Returns (token, seat_index)."""
        for i, seat in enumerate(self.seats):
            if seat.player_name is None and not seat.is_bot:
                token = generate_player_token()
                seat.player_name = name
                seat.player_token = token
                seat.is_connected = True
                return token, i
        raise ValueError("No available seats")

    def configure_seat(self, seat: int, is_bot: bool, bot_policy: str = "random"):
        """Configure a seat as bot or human."""
        if seat < 0 or seat >= len(self.seats):
            raise ValueError(f"Invalid seat {seat}")
        if self.game_started:
            raise ValueError("Cannot change seats after game started")
        
        self.seats[seat].is_bot = is_bot
        self.seats[seat].bot_policy = bot_policy
        if is_bot:
            self.seats[seat].player_name = f"Bot {seat + 1}"
            self.seats[seat].player_token = None
            self.seats[seat].is_connected = False

    def can_start(self) -> bool:
        """Check if game can start (all seats filled or bot)."""
        for seat in self.seats:
            if seat.player_name is None and not seat.is_bot:
                return False
        return True

    def start_game(self):
        """Start the game."""
        if not self.can_start():
            raise ValueError("Cannot start: not all seats filled")
        if self.game_started:
            raise ValueError("Game already started")
        
        self.engine = GameEngine(num_players=self.num_players)
        self.engine.reset()
        self.game_started = True
        
        # Initialize bot policies
        for i, seat in enumerate(self.seats):
            if seat.is_bot:
                self._bot_policies[i] = RandomPolicy(seed=i)

    def get_state_for_player(self, seat: int) -> GameStateSchema:
        """Get game state from a player's perspective."""
        if not self.engine:
            raise ValueError("Game not started")
        
        state = self.engine.state
        
        # Rotate players so requesting player is at index 0
        rotated_players = []
        for i in range(self.num_players):
            actual_idx = (seat + i) % self.num_players
            player = state.players[actual_idx]
            player_seat = self.seats[actual_idx]
            
            # Build reserved cards list
            reserved: list[CardSchema | HiddenCardSchema] = []
            for card in player.reserved:
                if i == 0:  # This is the requesting player
                    reserved.append(CardSchema(
                        id=card.id,
                        tier=card.tier,
                        bonus=card.bonus.value,
                        points=card.points,
                        cost=gem_collection_to_schema(card.cost),
                    ))
                else:  # Opponent - hide card details
                    reserved.append(HiddenCardSchema(tier=card.tier))
            
            # Build cards list
            cards = [
                CardSchema(
                    id=card.id,
                    tier=card.tier,
                    bonus=card.bonus.value,
                    points=card.points,
                    cost=gem_collection_to_schema(card.cost),
                )
                for card in player.cards
            ]
            
            # Build nobles list
            nobles = [
                NobleSchema(
                    id=noble.id,
                    points=noble.points,
                    requirements=gem_collection_to_schema(noble.requirements),
                )
                for noble in player.nobles
            ]
            
            rotated_players.append(PlayerSchema(
                id=actual_idx,
                tokens=gem_collection_to_schema(player.tokens),
                bonuses=gem_collection_to_schema(player.bonuses),
                points=player.points,
                card_count=len(player.cards),
                cards=cards,
                reserved=reserved,
                noble_count=len(player.nobles),
                nobles=nobles,
            ))
        
        # Build visible cards
        visible_cards = {}
        for tier in (1, 2, 3):
            visible_cards[str(tier)] = [
                CardSchema(
                    id=card.id,
                    tier=card.tier,
                    bonus=card.bonus.value,
                    points=card.points,
                    cost=gem_collection_to_schema(card.cost),
                )
                for card in state.visible_cards[tier]
            ]
        
        # Build deck counts
        deck_counts = {str(tier): len(state.card_decks[tier]) for tier in (1, 2, 3)}
        
        # Build nobles
        nobles = [
            NobleSchema(
                id=noble.id,
                points=noble.points,
                requirements=gem_collection_to_schema(noble.requirements),
            )
            for noble in state.nobles
        ]
        
        # Calculate current player from rotated perspective
        rotated_current = (state.current_player_idx - seat) % self.num_players
        
        return GameStateSchema(
            room_id=self.room_id,
            your_seat=seat,
            is_your_turn=state.current_player_idx == seat,
            current_player_idx=rotated_current,
            turn_number=state.turn_number,
            is_final_round=state.is_final_round,
            game_over=state.game_over,
            winner=state.winner,
            bank=gem_collection_to_schema(state.bank),
            nobles=nobles,
            visible_cards=visible_cards,
            deck_counts=deck_counts,
            players=rotated_players,
        )

    def submit_action(self, seat: int, action_schema: ActionSchema) -> None:
        """Submit an action for a player."""
        if not self.engine:
            raise ValueError("Game not started")
        
        state = self.engine.state
        if state.game_over:
            raise ValueError("Game is over")
        if state.current_player_idx != seat:
            raise ValueError("Not your turn")
        
        # Convert schema to game action
        action = schema_to_action(action_schema)
        
        # Execute action
        self.engine.step(action)

    def execute_bot_turns(self) -> int:
        """Execute any pending bot turns. Returns number of actions taken."""
        if not self.engine or not self.game_started:
            return 0
        
        actions_taken = 0
        max_iterations = 10  # Safety limit
        
        while not self.engine.state.game_over and actions_taken < max_iterations:
            current = self.engine.state.current_player_idx
            seat = self.seats[current]
            
            if not seat.is_bot:
                break
            
            policy = self._bot_policies.get(current)
            if not policy:
                policy = RandomPolicy(seed=current)
                self._bot_policies[current] = policy
            
            valid_actions = self.engine.get_valid_actions()
            if not valid_actions:
                break
            
            action = policy.select_action(self.engine.state, current, valid_actions)
            self.engine.step(action)
            actions_taken += 1
        
        return actions_taken


def gem_collection_to_schema(gc) -> GemCollectionSchema:
    """Convert GemCollection to schema."""
    return GemCollectionSchema(
        diamond=gc.diamond,
        sapphire=gc.sapphire,
        emerald=gc.emerald,
        ruby=gc.ruby,
        onyx=gc.onyx,
        gold=gc.gold,
    )


def schema_to_action(schema: ActionSchema) -> Action:
    """Convert action schema to game action."""
    if schema.type == "take_three_different":
        return TakeThreeDifferentAction(
            gems=tuple(schema.gems),
            return_gems=tuple(schema.return_gems),
        )
    elif schema.type == "take_two_same":
        return TakeTwoSameAction(
            gem=schema.gem,
            return_gems=tuple(schema.return_gems),
        )
    elif schema.type == "reserve_visible":
        return ReserveVisibleAction(
            card_id=schema.card_id,
            return_gems=tuple(schema.return_gems),
        )
    elif schema.type == "reserve_from_deck":
        return ReserveFromDeckAction(
            tier=schema.tier,
            return_gems=tuple(schema.return_gems),
        )
    elif schema.type == "purchase_visible":
        return PurchaseVisibleAction(card_id=schema.card_id)
    elif schema.type == "purchase_reserved":
        return PurchaseReservedAction(card_id=schema.card_id)
    else:
        raise ValueError(f"Unknown action type: {schema.type}")


class RoomManager:
    """Manages all active rooms."""

    def __init__(self):
        self._rooms: dict[str, Room] = {}

    def create_room(self, num_players: int, player_name: str) -> tuple[Room, str, int]:
        """Create a new room and add the creator. Returns (room, token, seat)."""
        room_id = generate_room_id()
        while room_id in self._rooms:
            room_id = generate_room_id()
        
        room = Room(room_id=room_id, num_players=num_players)
        token, seat = room.add_player(player_name)
        room.host_seat = seat
        
        self._rooms[room_id] = room
        return room, token, seat

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get a room by ID."""
        return self._rooms.get(room_id.upper())

    def delete_room(self, room_id: str):
        """Delete a room."""
        self._rooms.pop(room_id, None)


# Global room manager instance
room_manager = RoomManager()

