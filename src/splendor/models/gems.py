"""Gem types and token collections for Splendor."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Iterator

from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from typing_extensions import Self


class GemType(str, Enum):
    """The five gem types plus gold (wild/joker)."""

    DIAMOND = "diamond"  # White
    SAPPHIRE = "sapphire"  # Blue
    EMERALD = "emerald"  # Green
    RUBY = "ruby"  # Red
    ONYX = "onyx"  # Black
    GOLD = "gold"  # Wild (joker) - only used for tokens, not bonuses

    @classmethod
    def base_gems(cls) -> list[GemType]:
        """Return all gem types except gold."""
        return [cls.DIAMOND, cls.SAPPHIRE, cls.EMERALD, cls.RUBY, cls.ONYX]


class GemCollection(BaseModel, frozen=True):
    """
    Immutable collection of gems.

    Used for:
    - Token collections (bank and player hands) - includes gold
    - Card costs - no gold
    - Player bonuses (sum of card bonuses) - no gold
    - Noble requirements - no gold
    """

    diamond: int = 0
    sapphire: int = 0
    emerald: int = 0
    ruby: int = 0
    onyx: int = 0
    gold: int = 0  # Only used for token collections

    @model_validator(mode="after")
    def validate_non_negative(self) -> "GemCollection":
        """Ensure all gem counts are non-negative."""
        for gem_type in GemType:
            if self.get(gem_type) < 0:
                raise ValueError(f"Gem count for {gem_type.value} cannot be negative")
        return self

    def get(self, gem_type: GemType) -> int:
        """Get the count for a specific gem type."""
        return getattr(self, gem_type.value)

    def total(self) -> int:
        """Return the total number of gems/tokens."""
        return self.diamond + self.sapphire + self.emerald + self.ruby + self.onyx + self.gold

    def total_without_gold(self) -> int:
        """Return total gems excluding gold."""
        return self.diamond + self.sapphire + self.emerald + self.ruby + self.onyx

    def __add__(self, other: GemCollection) -> GemCollection:
        """Add two gem collections together."""
        return GemCollection(
            diamond=self.diamond + other.diamond,
            sapphire=self.sapphire + other.sapphire,
            emerald=self.emerald + other.emerald,
            ruby=self.ruby + other.ruby,
            onyx=self.onyx + other.onyx,
            gold=self.gold + other.gold,
        )

    def __sub__(self, other: GemCollection) -> GemCollection:
        """Subtract another gem collection from this one."""
        return GemCollection(
            diamond=self.diamond - other.diamond,
            sapphire=self.sapphire - other.sapphire,
            emerald=self.emerald - other.emerald,
            ruby=self.ruby - other.ruby,
            onyx=self.onyx - other.onyx,
            gold=self.gold - other.gold,
        )

    def __ge__(self, other: GemCollection) -> bool:
        """Check if this collection has at least as many of each gem type."""
        return (
            self.diamond >= other.diamond
            and self.sapphire >= other.sapphire
            and self.emerald >= other.emerald
            and self.ruby >= other.ruby
            and self.onyx >= other.onyx
            and self.gold >= other.gold
        )

    def __iter__(self) -> Iterator[tuple[GemType, int]]:
        """Iterate over (gem_type, count) pairs."""
        for gem_type in GemType:
            yield gem_type, self.get(gem_type)

    def with_gem(self, gem_type: GemType, count: int) -> GemCollection:
        """Return a new collection with the specified gem count changed."""
        return GemCollection(
            diamond=count if gem_type == GemType.DIAMOND else self.diamond,
            sapphire=count if gem_type == GemType.SAPPHIRE else self.sapphire,
            emerald=count if gem_type == GemType.EMERALD else self.emerald,
            ruby=count if gem_type == GemType.RUBY else self.ruby,
            onyx=count if gem_type == GemType.ONYX else self.onyx,
            gold=count if gem_type == GemType.GOLD else self.gold,
        )

    def add_gem(self, gem_type: GemType, count: int = 1) -> GemCollection:
        """Return a new collection with gems added."""
        return self.with_gem(gem_type, self.get(gem_type) + count)

    def remove_gem(self, gem_type: GemType, count: int = 1) -> GemCollection:
        """Return a new collection with gems removed."""
        return self.with_gem(gem_type, self.get(gem_type) - count)

    @classmethod
    def single(cls, gem_type: GemType, count: int = 1) -> GemCollection:
        """Create a collection with only one type of gem."""
        return cls().with_gem(gem_type, count)

    @classmethod
    def from_dict(cls, gems: dict[GemType | str, int]) -> GemCollection:
        """Create a collection from a dictionary."""
        normalized = {}
        for key, value in gems.items():
            if isinstance(key, GemType):
                normalized[key.value] = value
            else:
                normalized[key] = value
        return cls(**normalized)
