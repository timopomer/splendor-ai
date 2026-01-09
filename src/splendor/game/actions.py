"""Action types and definitions for Splendor."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, List, Literal, Sequence, Tuple, Union

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """All possible action types in Splendor."""

    TAKE_THREE_DIFFERENT = "take_three_different"
    TAKE_TWO_SAME = "take_two_same"
    RESERVE_VISIBLE = "reserve_visible"
    RESERVE_FROM_DECK = "reserve_from_deck"
    PURCHASE_VISIBLE = "purchase_visible"
    PURCHASE_RESERVED = "purchase_reserved"


class TakeThreeDifferentAction(BaseModel, frozen=True):
    """
    Take 3 tokens of different colors.

    Rules:
    - Must take exactly 3 different colors (or fewer if bank doesn't have enough)
    - Cannot take gold tokens
    - Cannot exceed 10 total tokens (must return excess)
    """

    type: Literal[ActionType.TAKE_THREE_DIFFERENT] = ActionType.TAKE_THREE_DIFFERENT
    gems: tuple[str, ...] = Field(
        description="Gem types to take (1-3 different colors)"
    )
    return_gems: tuple[str, ...] = Field(
        default=(), description="Gems to return if over 10 tokens"
    )


class TakeTwoSameAction(BaseModel, frozen=True):
    """
    Take 2 tokens of the same color.

    Rules:
    - Must have at least 4 tokens of that color in the bank
    - Cannot take gold tokens
    - Cannot exceed 10 total tokens (must return excess)
    """

    type: Literal[ActionType.TAKE_TWO_SAME] = ActionType.TAKE_TWO_SAME
    gem: str = Field(description="Gem type to take 2 of")
    return_gems: tuple[str, ...] = Field(
        default=(), description="Gems to return if over 10 tokens"
    )


class ReserveVisibleAction(BaseModel, frozen=True):
    """
    Reserve a visible card from the table.

    Rules:
    - Can have at most 3 reserved cards
    - Receive 1 gold token (if available)
    - Cannot exceed 10 total tokens (must return excess)
    """

    type: Literal[ActionType.RESERVE_VISIBLE] = ActionType.RESERVE_VISIBLE
    card_id: str = Field(description="ID of the visible card to reserve")
    return_gems: tuple[str, ...] = Field(
        default=(), description="Gems to return if over 10 tokens"
    )


class ReserveFromDeckAction(BaseModel, frozen=True):
    """
    Reserve the top card from a deck (blind reserve).

    Rules:
    - Can have at most 3 reserved cards
    - Receive 1 gold token (if available)
    - Cannot exceed 10 total tokens (must return excess)
    """

    type: Literal[ActionType.RESERVE_FROM_DECK] = ActionType.RESERVE_FROM_DECK
    tier: Literal[1, 2, 3] = Field(description="Tier of deck to reserve from")
    return_gems: tuple[str, ...] = Field(
        default=(), description="Gems to return if over 10 tokens"
    )


class PurchaseVisibleAction(BaseModel, frozen=True):
    """
    Purchase a visible card from the table.

    Rules:
    - Must be able to afford the card (tokens + bonuses + gold)
    - Card provides permanent bonus
    - May attract a noble after purchase
    """

    type: Literal[ActionType.PURCHASE_VISIBLE] = ActionType.PURCHASE_VISIBLE
    card_id: str = Field(description="ID of the visible card to purchase")


class PurchaseReservedAction(BaseModel, frozen=True):
    """
    Purchase a previously reserved card.

    Rules:
    - Must be able to afford the card (tokens + bonuses + gold)
    - Card provides permanent bonus
    - May attract a noble after purchase
    """

    type: Literal[ActionType.PURCHASE_RESERVED] = ActionType.PURCHASE_RESERVED
    card_id: str = Field(description="ID of the reserved card to purchase")


# Discriminated union of all action types
Action = Annotated[
    Union[
        TakeThreeDifferentAction,
        TakeTwoSameAction,
        ReserveVisibleAction,
        ReserveFromDeckAction,
        PurchaseVisibleAction,
        PurchaseReservedAction,
    ],
    Field(discriminator="type"),
]


# Helper functions to create actions
def take_three(
    gems: Sequence[str], return_gems: Sequence[str] = ()
) -> TakeThreeDifferentAction:
    """Create a take-three-different action."""
    return TakeThreeDifferentAction(gems=tuple(gems), return_gems=tuple(return_gems))


def take_two(
    gem: str, return_gems: Sequence[str] = ()
) -> TakeTwoSameAction:
    """Create a take-two-same action."""
    return TakeTwoSameAction(gem=gem, return_gems=tuple(return_gems))


def reserve_visible(
    card_id: str, return_gems: Sequence[str] = ()
) -> ReserveVisibleAction:
    """Create a reserve-visible-card action."""
    return ReserveVisibleAction(card_id=card_id, return_gems=tuple(return_gems))


def reserve_from_deck(
    tier: Literal[1, 2, 3], return_gems: Sequence[str] = ()
) -> ReserveFromDeckAction:
    """Create a reserve-from-deck action."""
    return ReserveFromDeckAction(tier=tier, return_gems=tuple(return_gems))


def purchase_visible(card_id: str) -> PurchaseVisibleAction:
    """Create a purchase-visible-card action."""
    return PurchaseVisibleAction(card_id=card_id)


def purchase_reserved(card_id: str) -> PurchaseReservedAction:
    """Create a purchase-reserved-card action."""
    return PurchaseReservedAction(card_id=card_id)

