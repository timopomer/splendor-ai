"""Tests for game data loading."""

from splendor.data import load_cards, load_nobles, load_cards_by_tier
from splendor.models.gems import GemType


class TestDataLoading:
    def test_load_cards_count(self):
        cards = load_cards()
        assert len(cards) == 90

    def test_load_cards_tier_distribution(self):
        cards = load_cards()
        tier_1 = [c for c in cards if c.tier == 1]
        tier_2 = [c for c in cards if c.tier == 2]
        tier_3 = [c for c in cards if c.tier == 3]
        assert len(tier_1) == 40
        assert len(tier_2) == 30
        assert len(tier_3) == 20

    def test_load_cards_by_tier(self):
        by_tier = load_cards_by_tier()
        assert len(by_tier[1]) == 40
        assert len(by_tier[2]) == 30
        assert len(by_tier[3]) == 20

    def test_load_nobles_count(self):
        nobles = load_nobles()
        assert len(nobles) == 10

    def test_nobles_all_worth_3_points(self):
        nobles = load_nobles()
        assert all(n.points == 3 for n in nobles)

    def test_cards_have_valid_bonus(self):
        cards = load_cards()
        valid_bonuses = set(GemType.base_gems())
        for card in cards:
            assert card.bonus in valid_bonuses

    def test_cards_have_unique_ids(self):
        cards = load_cards()
        ids = [c.id for c in cards]
        assert len(ids) == len(set(ids))

    def test_nobles_have_unique_ids(self):
        nobles = load_nobles()
        ids = [n.id for n in nobles]
        assert len(ids) == len(set(ids))

    def test_card_points_in_valid_range(self):
        cards = load_cards()
        for card in cards:
            assert 0 <= card.points <= 5

    def test_card_costs_non_negative(self):
        cards = load_cards()
        for card in cards:
            for gem_type, count in card.cost:
                assert count >= 0
