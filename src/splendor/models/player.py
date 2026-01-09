"""Player state for Splendor."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from splendor.models.gems import GemCollection, GemType
from splendor.models.cards import DevelopmentCard
from splendor.models.nobles import Noble


class Player(BaseModel, frozen=True):
    """
    A player's current state in the game.

    Players have:
    - Tokens (gems) they've collected
    - Cards they've purchased (providing permanent bonuses)
    - Cards they've reserved (max 3)
    - Nobles they've attracted
    """

    id: int = Field(description="Player identifier (0-indexed)")
    tokens: GemCollection = Field(
        default_factory=GemCollection, description="Current gem tokens held"
    )
    cards: tuple[DevelopmentCard, ...] = Field(
        default=(), description="Purchased development cards"
    )
    reserved: tuple[DevelopmentCard, ...] = Field(
        default=(), description="Reserved cards (max 3)"
    )
    nobles: tuple[Noble, ...] = Field(default=(), description="Attracted nobles")

    @computed_field
    @property
    def bonuses(self) -> GemCollection:
        """Calculate total permanent gem bonuses from purchased cards."""
        result = GemCollection()
        for card in self.cards:
            result = result.add_gem(card.bonus)
        return result

    @computed_field
    @property
    def points(self) -> int:
        """Calculate total victory points from cards and nobles."""
        card_points = sum(card.points for card in self.cards)
        noble_points = sum(noble.points for noble in self.nobles)
        return card_points + noble_points

    @property
    def token_count(self) -> int:
        """Total number of tokens held."""
        return self.tokens.total()

    @property
    def can_reserve(self) -> bool:
        """Check if player can reserve another card (max 3)."""
        return len(self.reserved) < 3

    def can_afford(self, cost: GemCollection) -> bool:
        """
        Check if the player can afford a card with given cost.

        The player can use:
        1. Tokens matching the gem type
        2. Permanent bonuses from purchased cards
        3. Gold tokens as wild cards for any remaining cost
        """
        gold_needed = 0

        for gem_type in GemType.base_gems():
            gem_cost = cost.get(gem_type)
            gem_tokens = self.tokens.get(gem_type)
            gem_bonus = self.bonuses.get(gem_type)

            # Effective payment = tokens + bonuses
            available = gem_tokens + gem_bonus
            shortfall = gem_cost - available

            if shortfall > 0:
                gold_needed += shortfall

        return gold_needed <= self.tokens.gold

    def payment_for(self, cost: GemCollection) -> GemCollection:
        """
        Calculate the tokens needed to pay for a card.

        Returns the tokens that should be returned to the bank.
        Bonuses are applied first, then tokens, then gold for any remainder.
        """
        payment = GemCollection()
        gold_needed = 0

        for gem_type in GemType.base_gems():
            gem_cost = cost.get(gem_type)
            gem_bonus = self.bonuses.get(gem_type)

            # Apply bonus first
            remaining_cost = max(0, gem_cost - gem_bonus)

            # Pay with matching tokens
            gem_tokens = self.tokens.get(gem_type)
            tokens_to_pay = min(remaining_cost, gem_tokens)
            payment = payment.add_gem(gem_type, tokens_to_pay)

            # Track gold needed for remainder
            gold_needed += remaining_cost - tokens_to_pay

        # Add gold payment
        payment = payment.with_gem(GemType.GOLD, gold_needed)
        return payment

    def with_tokens(self, tokens: GemCollection) -> Player:
        """Return a new player with updated tokens."""
        return self.model_copy(update={"tokens": tokens})

    def add_tokens(self, gems: GemCollection) -> Player:
        """Return a new player with added tokens."""
        return self.with_tokens(self.tokens + gems)

    def remove_tokens(self, gems: GemCollection) -> Player:
        """Return a new player with removed tokens."""
        return self.with_tokens(self.tokens - gems)

    def add_card(self, card: DevelopmentCard) -> Player:
        """Return a new player with an added purchased card."""
        return self.model_copy(update={"cards": self.cards + (card,)})

    def add_reserved(self, card: DevelopmentCard) -> Player:
        """Return a new player with a reserved card added."""
        if not self.can_reserve:
            raise ValueError("Cannot reserve more than 3 cards")
        return self.model_copy(update={"reserved": self.reserved + (card,)})

    def remove_reserved(self, card: DevelopmentCard) -> Player:
        """Return a new player with a reserved card removed."""
        new_reserved = tuple(c for c in self.reserved if c.id != card.id)
        if len(new_reserved) == len(self.reserved):
            raise ValueError(f"Card {card.id} not in reserved cards")
        return self.model_copy(update={"reserved": new_reserved})

    def add_noble(self, noble: Noble) -> Player:
        """Return a new player with an attracted noble."""
        return self.model_copy(update={"nobles": self.nobles + (noble,)})

