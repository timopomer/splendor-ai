"""Tests for development cards and nobles."""

import pytest

from splendor.models.cards import DevelopmentCard
from splendor.models.nobles import Noble
from splendor.models.gems import GemCollection, GemType


class TestDevelopmentCard:
    def test_create_card(self):
        card = DevelopmentCard(
            id="test_card",
            tier=1,
            bonus=GemType.DIAMOND,
            points=1,
            cost=GemCollection(sapphire=2, emerald=1),
        )
        assert card.id == "test_card"
        assert card.tier == 1
        assert card.bonus == GemType.DIAMOND
        assert card.points == 1
        assert card.cost.sapphire == 2

    def test_card_default_points(self):
        card = DevelopmentCard(
            id="no_points",
            tier=1,
            bonus=GemType.RUBY,
        )
        assert card.points == 0

    def test_card_equality_by_id(self):
        card1 = DevelopmentCard(id="same", tier=1, bonus=GemType.DIAMOND)
        card2 = DevelopmentCard(id="same", tier=2, bonus=GemType.RUBY)
        card3 = DevelopmentCard(id="different", tier=1, bonus=GemType.DIAMOND)
        assert card1 == card2
        assert card1 != card3

    def test_card_hash(self):
        card1 = DevelopmentCard(id="test", tier=1, bonus=GemType.DIAMOND)
        card2 = DevelopmentCard(id="test", tier=1, bonus=GemType.DIAMOND)
        assert hash(card1) == hash(card2)

    def test_invalid_tier(self):
        with pytest.raises(Exception):
            DevelopmentCard(id="bad", tier=4, bonus=GemType.DIAMOND)

    def test_invalid_points(self):
        with pytest.raises(Exception):
            DevelopmentCard(id="bad", tier=1, bonus=GemType.DIAMOND, points=10)


class TestNoble:
    def test_create_noble(self):
        noble = Noble(
            id="noble_1",
            requirements=GemCollection(diamond=4, sapphire=4),
        )
        assert noble.id == "noble_1"
        assert noble.points == 3
        assert noble.requirements.diamond == 4

    def test_can_visit_with_exact_requirements(self):
        noble = Noble(
            id="test",
            requirements=GemCollection(diamond=3, emerald=3),
        )
        bonuses = GemCollection(diamond=3, emerald=3)
        assert noble.can_visit(bonuses)

    def test_can_visit_with_excess_bonuses(self):
        noble = Noble(
            id="test",
            requirements=GemCollection(ruby=4),
        )
        bonuses = GemCollection(ruby=6, onyx=2)
        assert noble.can_visit(bonuses)

    def test_cannot_visit_insufficient_bonuses(self):
        noble = Noble(
            id="test",
            requirements=GemCollection(diamond=4, sapphire=4),
        )
        bonuses = GemCollection(diamond=4, sapphire=3)
        assert not noble.can_visit(bonuses)

    def test_noble_equality_by_id(self):
        noble1 = Noble(id="same", requirements=GemCollection())
        noble2 = Noble(id="same", requirements=GemCollection(diamond=1))
        assert noble1 == noble2
