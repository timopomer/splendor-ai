"""Development cards for Splendor."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from splendor.models.gems import GemCollection, GemType


class DevelopmentCard(BaseModel, frozen=True):
    """
    A development card that can be purchased or reserved.

    Development cards:
    - Have a tier (1, 2, or 3) indicating their power level
    - Provide a permanent gem bonus when purchased
    - May provide victory points
    - Have a cost in gems to purchase
    """

    id: str = Field(description="Unique identifier for the card")
    tier: Literal[1, 2, 3] = Field(description="Card tier (1=basic, 2=mid, 3=high)")
    bonus: GemType = Field(description="Permanent gem bonus provided")
    points: int = Field(default=0, ge=0, le=5, description="Victory points (0-5)")
    cost: GemCollection = Field(default_factory=GemCollection, description="Gem cost to purchase")

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DevelopmentCard):
            return NotImplemented
        return self.id == other.id
