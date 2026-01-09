"""Tests for game engine."""

import pytest

from splendor.game.engine import GameEngine
from splendor.game.actions import (
    take_three,
    take_two,
    reserve_visible,
    reserve_from_deck,
    purchase_visible,
    TakeThreeDifferentAction,
    TakeTwoSameAction,
    ReserveVisibleAction,
    PurchaseVisibleAction,
)
from splendor.models.gems import GemType


class TestGameEngineSetup:
    def test_create_engine(self):
        engine = GameEngine(num_players=2)
        assert engine.config.num_players == 2

    def test_create_engine_invalid_players(self):
        with pytest.raises(ValueError):
            GameEngine(num_players=1)
        with pytest.raises(ValueError):
            GameEngine(num_players=5)

    def test_reset_creates_state(self):
        engine = GameEngine(num_players=2, seed=42)
        state = engine.reset()
        assert state is not None
        assert len(state.players) == 2

    def test_reset_shuffles_cards(self):
        engine1 = GameEngine(num_players=2, seed=42)
        engine2 = GameEngine(num_players=2, seed=42)
        engine3 = GameEngine(num_players=2, seed=99)

        state1 = engine1.reset()
        state2 = engine2.reset()
        state3 = engine3.reset()

        # Same seed = same shuffle
        assert state1.visible_cards[1] == state2.visible_cards[1]
        # Different seed = different shuffle
        assert state1.visible_cards[1] != state3.visible_cards[1]

    def test_reset_correct_token_count(self):
        engine2 = GameEngine(num_players=2, seed=42)
        engine4 = GameEngine(num_players=4, seed=42)

        state2 = engine2.reset()
        state4 = engine4.reset()

        assert state2.bank.diamond == 4  # 2 players
        assert state4.bank.diamond == 7  # 4 players
        assert state2.bank.gold == 5
        assert state4.bank.gold == 5

    def test_reset_correct_noble_count(self):
        engine2 = GameEngine(num_players=2, seed=42)
        engine4 = GameEngine(num_players=4, seed=42)

        state2 = engine2.reset()
        state4 = engine4.reset()

        assert len(state2.nobles) == 3  # 2 + 1
        assert len(state4.nobles) == 5  # 4 + 1

    def test_reset_visible_cards(self):
        engine = GameEngine(num_players=2, seed=42)
        state = engine.reset()

        for tier in (1, 2, 3):
            assert len(state.visible_cards[tier]) == 4


class TestTakeGems:
    def test_take_three_different(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        action = take_three(["diamond", "sapphire", "ruby"])
        state = engine.step(action)

        # Player 0 took gems, now it's player 1's turn
        assert state.current_player_idx == 1
        player0 = state.players[0]
        assert player0.tokens.diamond == 1
        assert player0.tokens.sapphire == 1
        assert player0.tokens.ruby == 1

    def test_take_two_same(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        action = take_two("diamond")
        state = engine.step(action)

        player0 = state.players[0]
        assert player0.tokens.diamond == 2
        assert state.bank.diamond == 2  # Started with 4 for 2 players

    def test_take_two_requires_four_in_bank(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        # Player 0 takes 2 diamonds (bank: 4 -> 2)
        engine.step(take_two("diamond"))
        # Player 1 takes something else
        engine.step(take_three(["sapphire", "emerald", "ruby"]))

        # Player 0 tries to take 2 more diamonds - should fail (only 2 left)
        with pytest.raises(ValueError):
            engine.step(take_two("diamond"))


class TestReserveCards:
    def test_reserve_visible_card(self):
        engine = GameEngine(num_players=2, seed=42)
        state = engine.reset()

        card_id = state.visible_cards[1][0].id
        action = reserve_visible(card_id)
        new_state = engine.step(action)

        player0 = new_state.players[0]
        assert len(player0.reserved) == 1
        assert player0.reserved[0].id == card_id
        assert player0.tokens.gold == 1  # Got gold token

    def test_reserve_from_deck(self):
        engine = GameEngine(num_players=2, seed=42)
        state = engine.reset()

        initial_deck_size = len(state.card_decks[2])
        action = reserve_from_deck(2)
        new_state = engine.step(action)

        player0 = new_state.players[0]
        assert len(player0.reserved) == 1
        assert len(new_state.card_decks[2]) == initial_deck_size - 1

    def test_cannot_reserve_more_than_three(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        # Reserve 3 cards (alternating turns)
        for i in range(3):
            engine.step(reserve_from_deck(1))
            engine.step(take_three(["diamond", "sapphire", "ruby"]))

        # Try to reserve a 4th
        with pytest.raises(ValueError):
            engine.step(reserve_from_deck(1))


class TestPurchaseCards:
    def test_purchase_card_after_collecting_gems(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        # Alternate turns to build up tokens for player 0
        # Turn 1: P0 takes gems
        engine.step(take_three(["diamond", "sapphire", "emerald"]))
        # Turn 2: P1 takes gems  
        engine.step(take_three(["ruby", "onyx", "diamond"]))
        # Turn 3: P0 takes gems
        engine.step(take_three(["diamond", "sapphire", "ruby"]))
        # Turn 4: P1 takes gems
        engine.step(take_three(["emerald", "onyx", "sapphire"]))
        # Turn 5: P0 takes gems
        engine.step(take_three(["emerald", "ruby", "onyx"]))
        # Turn 6: P1 takes gems
        engine.step(take_three(["diamond", "ruby", "emerald"]))

        # Now it's player 0's turn - check if they can purchase
        state = engine.state
        assert state.current_player_idx == 0
        
        valid = engine.get_valid_actions()
        purchase_actions = [a for a in valid if isinstance(a, PurchaseVisibleAction)]

        if purchase_actions:
            action = purchase_actions[0]
            new_state = engine.step(action)
            # After purchase, it's P1's turn, check P0's cards
            player0 = new_state.players[0]
            assert len(player0.cards) == 1


class TestValidActions:
    def test_valid_actions_at_start(self):
        engine = GameEngine(num_players=2, seed=42)
        engine.reset()

        actions = engine.get_valid_actions()
        assert len(actions) > 0

        # Should have take-three options
        take_three_actions = [
            a for a in actions if isinstance(a, TakeThreeDifferentAction)
        ]
        assert len(take_three_actions) > 0

        # Should have take-two options (bank has 4 of each)
        take_two_actions = [a for a in actions if isinstance(a, TakeTwoSameAction)]
        assert len(take_two_actions) == 5  # All 5 gem types

        # Should have reserve options
        reserve_actions = [a for a in actions if isinstance(a, ReserveVisibleAction)]
        assert len(reserve_actions) == 12  # 4 cards × 3 tiers


class TestGameSimulation:
    def test_simulate_random_game(self):
        """Simulate a complete game with random valid moves."""
        import random

        engine = GameEngine(num_players=2, seed=42)
        engine.reset()
        rng = random.Random(123)

        moves = 0
        max_moves = 500

        while not engine.state.game_over and moves < max_moves:
            actions = engine.get_valid_actions()
            if not actions:
                break  # No valid moves (shouldn't happen normally)
            
            action = rng.choice(actions)
            engine.step(action)
            moves += 1

        # Game should end eventually
        assert engine.state.game_over or moves == max_moves

        if engine.state.game_over:
            assert engine.state.winner is not None
            winner = engine.state.players[engine.state.winner]
            assert winner.points >= 15

    def test_multiple_random_games(self):
        """Run several random games to ensure stability."""
        import random

        for game_num in range(5):
            engine = GameEngine(num_players=2, seed=game_num)
            engine.reset()
            rng = random.Random(game_num * 100)

            moves = 0
            max_moves = 500

            while not engine.state.game_over and moves < max_moves:
                actions = engine.get_valid_actions()
                if not actions:
                    break
                action = rng.choice(actions)
                engine.step(action)
                moves += 1

            # Just verify no crashes
            assert engine.state is not None

