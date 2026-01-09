"""Game data loading utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from splendor.models.cards import DevelopmentCard
    from splendor.models.nobles import Noble

_DATA_DIR = Path(__file__).parent


def load_cards() -> list[DevelopmentCard]:
    """Load all development cards from the data file."""
    from splendor.models.cards import DevelopmentCard
    from splendor.models.gems import GemCollection

    with open(_DATA_DIR / "cards.json") as f:
        data = json.load(f)

    cards = []
    for card_data in data["cards"]:
        cost = GemCollection(**card_data.get("cost", {}))
        card = DevelopmentCard(
            id=card_data["id"],
            tier=card_data["tier"],
            bonus=card_data["bonus"],
            points=card_data.get("points", 0),
            cost=cost,
        )
        cards.append(card)

    return cards


def load_nobles() -> list[Noble]:
    """Load all noble tiles from the data file."""
    from splendor.models.nobles import Noble
    from splendor.models.gems import GemCollection

    with open(_DATA_DIR / "cards.json") as f:
        data = json.load(f)

    nobles = []
    for noble_data in data["nobles"]:
        requirements = GemCollection(**noble_data.get("requirements", {}))
        noble = Noble(
            id=noble_data["id"],
            points=noble_data.get("points", 3),
            requirements=requirements,
        )
        nobles.append(noble)

    return nobles


def load_cards_by_tier() -> dict[int, list[DevelopmentCard]]:
    """Load cards organized by tier."""
    cards = load_cards()
    by_tier: dict[int, list[DevelopmentCard]] = {1: [], 2: [], 3: []}
    for card in cards:
        by_tier[card.tier].append(card)
    return by_tier


__all__ = ["load_cards", "load_nobles", "load_cards_by_tier"]
