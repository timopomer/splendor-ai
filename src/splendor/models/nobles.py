"""Noble tiles for Splendor."""

from __future__ import annotations

from pydantic import BaseModel, Field

from splendor.models.gems import GemCollection


class Noble(BaseModel, frozen=True):
    """
    A noble tile that visits players who meet their requirements.

    Nobles:
    - Are always worth 3 victory points
    - Automatically visit a player who has the required bonuses
    - Can only visit one player (removed from play after visiting)
    - Requirements are in card bonuses, NOT tokens
    """

    id: str = Field(description="Unique identifier for the noble")
    points: int = Field(default=3, description="Victory points (always 3)")
    requirements: GemCollection = Field(description="Required card bonuses to attract this noble")

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Noble):
            return NotImplemented
        return self.id == other.id

    def can_visit(self, player_bonuses: GemCollection) -> bool:
        """Check if a player's bonuses satisfy this noble's requirements."""
        # Check each non-gold gem type (nobles don't require gold)
        return (
            player_bonuses.diamond >= self.requirements.diamond
            and player_bonuses.sapphire >= self.requirements.sapphire
            and player_bonuses.emerald >= self.requirements.emerald
            and player_bonuses.ruby >= self.requirements.ruby
            and player_bonuses.onyx >= self.requirements.onyx
        )
