"""Tests for action types."""

from splendor.game.actions import (
    ActionType,
    TakeThreeDifferentAction,
    TakeTwoSameAction,
    ReserveVisibleAction,
    ReserveFromDeckAction,
    PurchaseVisibleAction,
    PurchaseReservedAction,
    take_three,
    take_two,
    reserve_visible,
    reserve_from_deck,
    purchase_visible,
    purchase_reserved,
)


class TestActionTypes:
    def test_all_action_types(self):
        assert len(ActionType) == 6

    def test_take_three_different(self):
        action = TakeThreeDifferentAction(gems=("diamond", "sapphire", "ruby"))
        assert action.type == ActionType.TAKE_THREE_DIFFERENT
        assert len(action.gems) == 3
        assert action.return_gems == ()

    def test_take_three_with_return(self):
        action = TakeThreeDifferentAction(
            gems=("diamond", "sapphire", "ruby"),
            return_gems=("emerald",),
        )
        assert action.return_gems == ("emerald",)

    def test_take_two_same(self):
        action = TakeTwoSameAction(gem="emerald")
        assert action.type == ActionType.TAKE_TWO_SAME
        assert action.gem == "emerald"

    def test_reserve_visible(self):
        action = ReserveVisibleAction(card_id="t1_d01")
        assert action.type == ActionType.RESERVE_VISIBLE
        assert action.card_id == "t1_d01"

    def test_reserve_from_deck(self):
        action = ReserveFromDeckAction(tier=2)
        assert action.type == ActionType.RESERVE_FROM_DECK
        assert action.tier == 2

    def test_purchase_visible(self):
        action = PurchaseVisibleAction(card_id="t2_s03")
        assert action.type == ActionType.PURCHASE_VISIBLE
        assert action.card_id == "t2_s03"

    def test_purchase_reserved(self):
        action = PurchaseReservedAction(card_id="reserved_card")
        assert action.type == ActionType.PURCHASE_RESERVED


class TestActionHelpers:
    def test_take_three_helper(self):
        action = take_three(["diamond", "sapphire", "ruby"])
        assert action.type == ActionType.TAKE_THREE_DIFFERENT
        assert action.gems == ("diamond", "sapphire", "ruby")

    def test_take_three_with_return_helper(self):
        action = take_three(["diamond"], return_gems=["gold"])
        assert action.return_gems == ("gold",)

    def test_take_two_helper(self):
        action = take_two("onyx")
        assert action.type == ActionType.TAKE_TWO_SAME
        assert action.gem == "onyx"

    def test_reserve_visible_helper(self):
        action = reserve_visible("card_123")
        assert action.type == ActionType.RESERVE_VISIBLE
        assert action.card_id == "card_123"

    def test_reserve_from_deck_helper(self):
        action = reserve_from_deck(3)
        assert action.type == ActionType.RESERVE_FROM_DECK
        assert action.tier == 3

    def test_purchase_visible_helper(self):
        action = purchase_visible("buy_this")
        assert action.type == ActionType.PURCHASE_VISIBLE

    def test_purchase_reserved_helper(self):
        action = purchase_reserved("my_reserved")
        assert action.type == ActionType.PURCHASE_RESERVED


class TestActionImmutability:
    def test_action_is_frozen(self):
        action = take_three(["diamond", "sapphire", "ruby"])
        try:
            action.gems = ("changed",)
            assert False, "Should have raised"
        except Exception:
            pass  # Expected

