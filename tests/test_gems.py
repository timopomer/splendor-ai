"""Tests for gem types and collections."""

import pytest

from splendor.models.gems import GemCollection, GemType


class TestGemType:
    def test_base_gems_excludes_gold(self):
        base = GemType.base_gems()
        assert GemType.GOLD not in base
        assert len(base) == 5

    def test_all_gem_types(self):
        assert len(GemType) == 6


class TestGemCollection:
    def test_default_is_empty(self):
        gems = GemCollection()
        assert gems.total() == 0

    def test_create_with_values(self):
        gems = GemCollection(diamond=3, sapphire=2)
        assert gems.diamond == 3
        assert gems.sapphire == 2
        assert gems.emerald == 0

    def test_total(self):
        gems = GemCollection(diamond=2, sapphire=3, gold=1)
        assert gems.total() == 6

    def test_total_without_gold(self):
        gems = GemCollection(diamond=2, sapphire=3, gold=1)
        assert gems.total_without_gold() == 5

    def test_get_by_gem_type(self):
        gems = GemCollection(ruby=5)
        assert gems.get(GemType.RUBY) == 5
        assert gems.get(GemType.DIAMOND) == 0

    def test_add_collections(self):
        a = GemCollection(diamond=2, sapphire=1)
        b = GemCollection(diamond=1, ruby=3)
        result = a + b
        assert result.diamond == 3
        assert result.sapphire == 1
        assert result.ruby == 3

    def test_subtract_collections(self):
        a = GemCollection(diamond=5, sapphire=3)
        b = GemCollection(diamond=2, sapphire=1)
        result = a - b
        assert result.diamond == 3
        assert result.sapphire == 2

    def test_comparison_ge(self):
        a = GemCollection(diamond=3, sapphire=2)
        b = GemCollection(diamond=2, sapphire=2)
        c = GemCollection(diamond=4, sapphire=1)
        assert a >= b
        assert not b >= a
        assert not a >= c  # a has fewer diamonds

    def test_single_gem(self):
        gems = GemCollection.single(GemType.EMERALD, 4)
        assert gems.emerald == 4
        assert gems.total() == 4

    def test_add_gem(self):
        gems = GemCollection(diamond=2)
        result = gems.add_gem(GemType.DIAMOND, 3)
        assert result.diamond == 5
        assert gems.diamond == 2  # Original unchanged (immutable)

    def test_remove_gem(self):
        gems = GemCollection(sapphire=5)
        result = gems.remove_gem(GemType.SAPPHIRE, 2)
        assert result.sapphire == 3

    def test_from_dict(self):
        gems = GemCollection.from_dict({GemType.RUBY: 3, "onyx": 2})
        assert gems.ruby == 3
        assert gems.onyx == 2

    def test_immutable(self):
        gems = GemCollection(diamond=1)
        with pytest.raises(Exception):
            gems.diamond = 5

    def test_negative_validation(self):
        with pytest.raises(ValueError):
            GemCollection(diamond=-1)

    def test_iteration(self):
        gems = GemCollection(diamond=1, sapphire=2)
        items = dict(gems)
        assert items[GemType.DIAMOND] == 1
        assert items[GemType.SAPPHIRE] == 2
