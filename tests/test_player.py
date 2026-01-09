"""Tests for player state."""

import pytest

from splendor.models.player import Player
from splendor.models.cards import DevelopmentCard
from splendor.models.nobles import Noble
from splendor.models.gems import GemCollection, GemType


class TestPlayer:
    def test_create_player(self):
        player = Player(id=0)
        assert player.id == 0
        assert player.tokens.total() == 0
        assert len(player.cards) == 0
        assert len(player.reserved) == 0
        assert len(player.nobles) == 0

    def test_player_with_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=3, gold=1))
        assert player.token_count == 4
        assert player.tokens.diamond == 3

    def test_computed_bonuses_empty(self):
        player = Player(id=0)
        assert player.bonuses.total() == 0

    def test_computed_bonuses_from_cards(self):
        cards = (
            DevelopmentCard(id="c1", tier=1, bonus=GemType.DIAMOND),
            DevelopmentCard(id="c2", tier=1, bonus=GemType.DIAMOND),
            DevelopmentCard(id="c3", tier=1, bonus=GemType.RUBY),
        )
        player = Player(id=0, cards=cards)
        assert player.bonuses.diamond == 2
        assert player.bonuses.ruby == 1
        assert player.bonuses.sapphire == 0

    def test_computed_points(self):
        cards = (
            DevelopmentCard(id="c1", tier=1, bonus=GemType.DIAMOND, points=1),
            DevelopmentCard(id="c2", tier=2, bonus=GemType.RUBY, points=3),
        )
        nobles = (Noble(id="n1", requirements=GemCollection()),)
        player = Player(id=0, cards=cards, nobles=nobles)
        assert player.points == 1 + 3 + 3  # cards + noble

    def test_can_reserve_initially_true(self):
        player = Player(id=0)
        assert player.can_reserve

    def test_can_reserve_at_limit(self):
        reserved = tuple(
            DevelopmentCard(id=f"r{i}", tier=1, bonus=GemType.DIAMOND)
            for i in range(3)
        )
        player = Player(id=0, reserved=reserved)
        assert not player.can_reserve


class TestPlayerAffordability:
    def test_can_afford_with_exact_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=3, sapphire=2))
        cost = GemCollection(diamond=3, sapphire=2)
        assert player.can_afford(cost)

    def test_can_afford_with_excess_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=5, sapphire=3))
        cost = GemCollection(diamond=3, sapphire=2)
        assert player.can_afford(cost)

    def test_cannot_afford_insufficient_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=2))
        cost = GemCollection(diamond=3)
        assert not player.can_afford(cost)

    def test_can_afford_with_bonuses(self):
        cards = (DevelopmentCard(id="c1", tier=1, bonus=GemType.DIAMOND),)
        player = Player(id=0, cards=cards, tokens=GemCollection(diamond=2))
        cost = GemCollection(diamond=3)
        assert player.can_afford(cost)

    def test_can_afford_with_gold(self):
        player = Player(id=0, tokens=GemCollection(diamond=2, gold=2))
        cost = GemCollection(diamond=3, sapphire=1)
        assert player.can_afford(cost)

    def test_cannot_afford_insufficient_gold(self):
        player = Player(id=0, tokens=GemCollection(diamond=1, gold=1))
        cost = GemCollection(diamond=3)
        assert not player.can_afford(cost)

    def test_payment_calculation_exact(self):
        player = Player(id=0, tokens=GemCollection(diamond=3, sapphire=2))
        cost = GemCollection(diamond=3, sapphire=2)
        payment = player.payment_for(cost)
        assert payment.diamond == 3
        assert payment.sapphire == 2
        assert payment.gold == 0

    def test_payment_with_bonuses(self):
        cards = (
            DevelopmentCard(id="c1", tier=1, bonus=GemType.DIAMOND),
            DevelopmentCard(id="c2", tier=1, bonus=GemType.DIAMOND),
        )
        player = Player(id=0, cards=cards, tokens=GemCollection(diamond=3))
        cost = GemCollection(diamond=4)
        payment = player.payment_for(cost)
        assert payment.diamond == 2  # 4 cost - 2 bonus = 2 tokens needed
        assert payment.gold == 0

    def test_payment_with_gold(self):
        player = Player(id=0, tokens=GemCollection(diamond=1, gold=3))
        cost = GemCollection(diamond=3, sapphire=1)
        payment = player.payment_for(cost)
        assert payment.diamond == 1
        assert payment.sapphire == 0
        assert payment.gold == 3  # 2 for diamond shortfall + 1 for sapphire


class TestPlayerMutations:
    def test_with_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=1))
        new_tokens = GemCollection(sapphire=5)
        updated = player.with_tokens(new_tokens)
        assert updated.tokens.sapphire == 5
        assert updated.tokens.diamond == 0
        assert player.tokens.diamond == 1  # Original unchanged

    def test_add_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=2))
        updated = player.add_tokens(GemCollection(diamond=1, ruby=3))
        assert updated.tokens.diamond == 3
        assert updated.tokens.ruby == 3

    def test_remove_tokens(self):
        player = Player(id=0, tokens=GemCollection(diamond=5))
        updated = player.remove_tokens(GemCollection(diamond=2))
        assert updated.tokens.diamond == 3

    def test_add_card(self):
        player = Player(id=0)
        card = DevelopmentCard(id="new", tier=1, bonus=GemType.EMERALD)
        updated = player.add_card(card)
        assert len(updated.cards) == 1
        assert updated.cards[0].id == "new"

    def test_add_reserved(self):
        player = Player(id=0)
        card = DevelopmentCard(id="reserved", tier=2, bonus=GemType.ONYX)
        updated = player.add_reserved(card)
        assert len(updated.reserved) == 1

    def test_add_reserved_at_limit_raises(self):
        reserved = tuple(
            DevelopmentCard(id=f"r{i}", tier=1, bonus=GemType.DIAMOND)
            for i in range(3)
        )
        player = Player(id=0, reserved=reserved)
        card = DevelopmentCard(id="extra", tier=1, bonus=GemType.RUBY)
        with pytest.raises(ValueError):
            player.add_reserved(card)

    def test_remove_reserved(self):
        card = DevelopmentCard(id="to_remove", tier=1, bonus=GemType.SAPPHIRE)
        player = Player(id=0, reserved=(card,))
        updated = player.remove_reserved(card)
        assert len(updated.reserved) == 0

    def test_remove_reserved_not_found_raises(self):
        player = Player(id=0)
        card = DevelopmentCard(id="not_there", tier=1, bonus=GemType.RUBY)
        with pytest.raises(ValueError):
            player.remove_reserved(card)

    def test_add_noble(self):
        player = Player(id=0)
        noble = Noble(id="visiting", requirements=GemCollection())
        updated = player.add_noble(noble)
        assert len(updated.nobles) == 1
        assert updated.points == 3

