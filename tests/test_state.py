"""Tests for game state."""

import pytest

from splendor.game.state import GameConfig, GameState, TOKENS_BY_PLAYER_COUNT
from splendor.models.player import Player
from splendor.models.cards import DevelopmentCard
from splendor.models.nobles import Noble
from splendor.models.gems import GemCollection, GemType


class TestGameConfig:
    def test_default_config(self):
        config = GameConfig()
        assert config.num_players == 2
        assert config.winning_points == 15
        assert config.max_tokens_per_player == 10
        assert config.max_reserved_cards == 3

    def test_custom_config(self):
        config = GameConfig(num_players=4, winning_points=20)
        assert config.num_players == 4
        assert config.winning_points == 20


class TestGameState:
    def test_create_minimal_state(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players)
        assert len(state.players) == 2
        assert state.current_player_idx == 0
        assert state.turn_number == 0
        assert not state.game_over

    def test_player_count_validation(self):
        players = (Player(id=0),)  # Only 1 player
        config = GameConfig(num_players=2)
        with pytest.raises(ValueError):
            GameState(config=config, players=players)

    def test_current_player(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players, current_player_idx=1)
        assert state.current_player.id == 1

    def test_get_player(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players)
        assert state.get_player(0).id == 0
        assert state.get_player(1).id == 1

    def test_num_players(self):
        players = (Player(id=0), Player(id=1), Player(id=2))
        config = GameConfig(num_players=3)
        state = GameState(config=config, players=players)
        assert state.num_players == 3


class TestGameStateCardLookup:
    def test_get_visible_card(self):
        card = DevelopmentCard(id="test_card", tier=1, bonus=GemType.DIAMOND)
        players = (Player(id=0), Player(id=1))
        state = GameState(
            players=players,
            visible_cards={1: (card,), 2: (), 3: ()},
        )
        found = state.get_visible_card("test_card")
        assert found is not None
        assert found.id == "test_card"

    def test_get_visible_card_not_found(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players)
        assert state.get_visible_card("nonexistent") is None

    def test_get_visible_card_tier(self):
        card = DevelopmentCard(id="tier2_card", tier=2, bonus=GemType.RUBY)
        players = (Player(id=0), Player(id=1))
        state = GameState(
            players=players,
            visible_cards={1: (), 2: (card,), 3: ()},
        )
        assert state.get_visible_card_tier("tier2_card") == 2
        assert state.get_visible_card_tier("nonexistent") is None


class TestGameStateMutations:
    def test_with_player(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players)
        updated_player = Player(id=0, tokens=GemCollection(diamond=5))
        new_state = state.with_player(0, updated_player)
        assert new_state.players[0].tokens.diamond == 5
        assert state.players[0].tokens.diamond == 0  # Original unchanged

    def test_with_current_player(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players, current_player_idx=1)
        updated_player = Player(id=1, tokens=GemCollection(ruby=3))
        new_state = state.with_current_player(updated_player)
        assert new_state.players[1].tokens.ruby == 3

    def test_with_bank(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players, bank=GemCollection(diamond=4))
        new_bank = GemCollection(diamond=3)
        new_state = state.with_bank(new_bank)
        assert new_state.bank.diamond == 3
        assert state.bank.diamond == 4

    def test_advance_turn(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players, current_player_idx=0)
        new_state = state.advance_turn()
        assert new_state.current_player_idx == 1
        assert new_state.turn_number == 0  # Still turn 0

    def test_advance_turn_wraps_around(self):
        players = (Player(id=0), Player(id=1))
        state = GameState(players=players, current_player_idx=1, turn_number=0)
        new_state = state.advance_turn()
        assert new_state.current_player_idx == 0
        assert new_state.turn_number == 1  # New turn

    def test_refill_visible_card(self):
        deck_card = DevelopmentCard(id="deck_card", tier=1, bonus=GemType.EMERALD)
        players = (Player(id=0), Player(id=1))
        state = GameState(
            players=players,
            visible_cards={1: (), 2: (), 3: ()},
            card_decks={1: (deck_card,), 2: (), 3: ()},
        )
        new_state = state.refill_visible_card(1)
        assert len(new_state.visible_cards[1]) == 1
        assert len(new_state.card_decks[1]) == 0


class TestWinCondition:
    def test_check_winner_triggers_final_round(self):
        # Create multiple cards totaling 15+ points
        cards = tuple(
            DevelopmentCard(id=f"card_{i}", tier=3, bonus=GemType.DIAMOND, points=5)
            for i in range(3)
        )
        players = (
            Player(id=0, cards=cards),  # 15 points
            Player(id=1),
        )
        state = GameState(players=players, current_player_idx=0)
        new_state = state.check_winner()
        assert new_state.is_final_round
        assert new_state.first_player_to_win == 0
        assert not new_state.game_over

    def test_game_ends_after_final_round(self):
        # Create multiple cards totaling 15+ points
        cards = tuple(
            DevelopmentCard(id=f"card_{i}", tier=3, bonus=GemType.DIAMOND, points=5)
            for i in range(3)
        )
        players = (
            Player(id=0, cards=cards),  # 15 points
            Player(id=1),
        )
        state = GameState(
            players=players,
            current_player_idx=1,  # Player 1's turn (last before returning to 0)
            is_final_round=True,
            first_player_to_win=0,
        )
        new_state = state.check_winner()
        assert new_state.game_over
        assert new_state.winner == 0

