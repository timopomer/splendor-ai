"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from typing import List, Dict, Literal, Optional, Union
from pydantic import BaseModel, Field


# --- Gem Types ---
GemTypeLiteral = Literal["diamond", "sapphire", "emerald", "ruby", "onyx", "gold"]


class GemCollectionSchema(BaseModel):
    """Gem counts for tokens, costs, bonuses."""
    diamond: int = 0
    sapphire: int = 0
    emerald: int = 0
    ruby: int = 0
    onyx: int = 0
    gold: int = 0


# --- Card Schemas ---
class CardSchema(BaseModel):
    """A development card (visible or reserved)."""
    id: str
    tier: Literal[1, 2, 3]
    bonus: GemTypeLiteral
    points: int
    cost: GemCollectionSchema


class HiddenCardSchema(BaseModel):
    """A hidden reserved card (opponent's view)."""
    hidden: Literal[True] = True
    tier: Literal[1, 2, 3]


# --- Noble Schema ---
class NobleSchema(BaseModel):
    """A noble tile."""
    id: str
    points: int
    requirements: GemCollectionSchema


# --- Player Schema ---
class PlayerSchema(BaseModel):
    """Player state as seen from a perspective."""
    id: int
    name: str  # Player display name
    emoji: str  # Player's emoji
    is_bot: bool  # Whether this is a bot player
    tokens: GemCollectionSchema
    bonuses: GemCollectionSchema
    points: int
    card_count: int
    cards: List[CardSchema]  # Full card details for display
    reserved: List[Union[CardSchema, HiddenCardSchema]]  # Hidden for opponents
    noble_count: int
    nobles: List[NobleSchema]


# --- Game State Schema ---
class GameStateSchema(BaseModel):
    """Complete game state from a player's perspective."""
    room_id: str
    your_seat: int
    is_your_turn: bool
    current_player_idx: int
    turn_number: int
    is_final_round: bool
    game_over: bool
    winner: Optional[int] = None
    
    # Board state
    bank: GemCollectionSchema
    nobles: List[NobleSchema]
    visible_cards: Dict[str, List[CardSchema]]  # tier -> cards
    deck_counts: Dict[str, int]  # tier -> count
    
    # Players (rotated so you are index 0)
    players: List[PlayerSchema]


# --- Room Management ---
class CreateRoomRequest(BaseModel):
    """Request to create a new room."""
    num_players: Literal[2, 3, 4] = 2
    player_name: str = Field(default="Player 1", max_length=20)
    player_emoji: str = Field(default="👤", max_length=8)


class CreateRoomResponse(BaseModel):
    """Response after creating a room."""
    room_id: str
    player_token: str
    seat: int


class JoinRoomRequest(BaseModel):
    """Request to join a room."""
    player_name: str = Field(default="Player", max_length=20)
    player_emoji: str = Field(default="👤", max_length=8)


class JoinRoomResponse(BaseModel):
    """Response after joining a room."""
    player_token: str
    seat: int


class ConfigureSeatRequest(BaseModel):
    """Request to configure a seat as bot or human."""
    seat: int
    is_bot: bool
    model_id: str = "random"  # ID of model from /models endpoint


class StartGameRequest(BaseModel):
    """Request to start the game."""
    pass


class SeatInfo(BaseModel):
    """Info about a seat in a room."""
    seat: int
    player_name: Optional[str] = None
    player_emoji: Optional[str] = None  # Player's chosen emoji
    is_bot: bool = False
    model_id: Optional[str] = None  # Model ID if bot
    model_icon: Optional[str] = None  # Icon for display
    is_connected: bool = False


class RoomInfoSchema(BaseModel):
    """Room info for lobby display."""
    room_id: str
    num_players: int
    seats: List[SeatInfo]
    game_started: bool
    host_seat: int


# --- Actions ---
class TakeThreeDifferentActionSchema(BaseModel):
    """Take up to 3 different gem tokens."""
    type: Literal["take_three_different"] = "take_three_different"
    gems: List[GemTypeLiteral]
    return_gems: List[GemTypeLiteral] = []


class TakeTwoSameActionSchema(BaseModel):
    """Take 2 tokens of the same color."""
    type: Literal["take_two_same"] = "take_two_same"
    gem: GemTypeLiteral
    return_gems: List[GemTypeLiteral] = []


class ReserveVisibleActionSchema(BaseModel):
    """Reserve a visible card."""
    type: Literal["reserve_visible"] = "reserve_visible"
    card_id: str
    return_gems: List[GemTypeLiteral] = []


class ReserveFromDeckActionSchema(BaseModel):
    """Reserve from deck."""
    type: Literal["reserve_from_deck"] = "reserve_from_deck"
    tier: Literal[1, 2, 3]
    return_gems: List[GemTypeLiteral] = []


class PurchaseVisibleActionSchema(BaseModel):
    """Purchase a visible card."""
    type: Literal["purchase_visible"] = "purchase_visible"
    card_id: str


class PurchaseReservedActionSchema(BaseModel):
    """Purchase a reserved card."""
    type: Literal["purchase_reserved"] = "purchase_reserved"
    card_id: str


ActionSchema = Union[
    TakeThreeDifferentActionSchema,
    TakeTwoSameActionSchema,
    ReserveVisibleActionSchema,
    ReserveFromDeckActionSchema,
    PurchaseVisibleActionSchema,
    PurchaseReservedActionSchema,
]


class SubmitActionRequest(BaseModel):
    """Request to submit an action."""
    action: ActionSchema


class SubmitActionResponse(BaseModel):
    """Response after submitting an action."""
    success: bool
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    detail: str


# --- Model Metadata ---
class NetworkInfoSchema(BaseModel):
    """Neural network architecture info."""
    policy: str
    architecture: List[int]
    observation_dim: int
    action_space: str


class ModelMetadataSchema(BaseModel):
    """Metadata about a bot model."""
    id: str
    name: str
    description: str
    type: Literal["conventional", "neural"]
    algorithm: Optional[str] = None
    network: Optional[NetworkInfoSchema] = None
    training_steps: Optional[int] = None
    training_games: Optional[int] = None
    win_rate_vs_random: Optional[float] = None
    icon: str  # 🤖 for conventional, 🧠 for neural


class ModelsListResponse(BaseModel):
    """Response containing list of available models."""
    models: List[ModelMetadataSchema]
