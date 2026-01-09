"""Game state for Splendor."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from splendor.models.gems import GemCollection
from splendor.models.cards import DevelopmentCard
from splendor.models.nobles import Noble
from splendor.models.player import Player


# Token counts based on player count
TOKENS_BY_PLAYER_COUNT: dict[int, int] = {
    2: 4,  # 4 tokens of each color
    3: 5,  # 5 tokens of each color
    4: 7,  # 7 tokens of each color
}

# Gold tokens are always 5 regardless of player count
GOLD_TOKENS = 5

# Number of nobles = player count + 1
VISIBLE_CARDS_PER_TIER = 4


class GameConfig(BaseModel, frozen=True):
    """Configuration for a Splendor game."""

    num_players: Literal[2, 3, 4] = Field(default=2, description="Number of players (2-4)")
    winning_points: int = Field(default=15, description="Points needed to trigger end game")
    max_tokens_per_player: int = Field(default=10, description="Maximum tokens a player can hold")
    max_reserved_cards: int = Field(default=3, description="Maximum cards a player can reserve")


class GameState(BaseModel, frozen=True):
    """
    Complete game state - immutable and clonable.

    The game state contains everything needed to:
    - Determine valid actions
    - Execute actions and produce new states
    - Serialize for RL training
    """

    config: GameConfig = Field(default_factory=GameConfig)
    players: tuple[Player, ...] = Field(description="All players in the game")
    current_player_idx: int = Field(default=0, description="Index of player whose turn it is")
    bank: GemCollection = Field(
        default_factory=GemCollection, description="Available tokens in the bank"
    )
    card_decks: dict[int, tuple[DevelopmentCard, ...]] = Field(
        default_factory=lambda: {1: (), 2: (), 3: ()},
        description="Face-down card decks by tier",
    )
    visible_cards: dict[int, tuple[DevelopmentCard, ...]] = Field(
        default_factory=lambda: {1: (), 2: (), 3: ()},
        description="Face-up cards available for purchase (4 per tier)",
    )
    nobles: tuple[Noble, ...] = Field(default=(), description="Available noble tiles")
    turn_number: int = Field(default=0, description="Current turn number")
    is_final_round: bool = Field(
        default=False, description="True if a player has reached winning points"
    )
    first_player_to_win: Optional[int] = Field(
        default=None, description="Index of first player to reach winning points"
    )
    game_over: bool = Field(default=False, description="True if the game has ended")
    winner: Optional[int] = Field(default=None, description="Index of winning player, if game over")

    @model_validator(mode="after")
    def validate_player_count(self) -> "GameState":
        """Validate that player count matches config."""
        if len(self.players) != self.config.num_players:
            raise ValueError(
                f"Expected {self.config.num_players} players, got {len(self.players)}"
            )
        return self

    @property
    def current_player(self) -> Player:
        """Get the current player."""
        return self.players[self.current_player_idx]

    @property
    def num_players(self) -> int:
        """Get the number of players."""
        return len(self.players)

    def get_player(self, player_idx: int) -> Player:
        """Get a player by index."""
        return self.players[player_idx]

    def get_visible_card(self, card_id: str) -> Optional[DevelopmentCard]:
        """Find a visible card by ID."""
        for tier in (1, 2, 3):
            for card in self.visible_cards[tier]:
                if card.id == card_id:
                    return card
        return None

    def get_visible_card_tier(self, card_id: str) -> Optional[int]:
        """Find which tier a visible card belongs to."""
        for tier in (1, 2, 3):
            for card in self.visible_cards[tier]:
                if card.id == card_id:
                    return tier
        return None

    def with_player(self, player_idx: int, player: Player) -> GameState:
        """Return a new state with an updated player."""
        players = list(self.players)
        players[player_idx] = player
        return self.model_copy(update={"players": tuple(players)})

    def with_current_player(self, player: Player) -> GameState:
        """Return a new state with the current player updated."""
        return self.with_player(self.current_player_idx, player)

    def with_bank(self, bank: GemCollection) -> GameState:
        """Return a new state with an updated bank."""
        return self.model_copy(update={"bank": bank})

    def with_visible_cards(
        self, tier: int, cards: tuple[DevelopmentCard, ...]
    ) -> GameState:
        """Return a new state with updated visible cards for a tier."""
        new_visible = dict(self.visible_cards)
        new_visible[tier] = cards
        return self.model_copy(update={"visible_cards": new_visible})

    def with_deck(self, tier: int, deck: tuple[DevelopmentCard, ...]) -> GameState:
        """Return a new state with an updated deck."""
        new_decks = dict(self.card_decks)
        new_decks[tier] = deck
        return self.model_copy(update={"card_decks": new_decks})

    def with_nobles(self, nobles: tuple[Noble, ...]) -> GameState:
        """Return a new state with updated nobles."""
        return self.model_copy(update={"nobles": nobles})

    def advance_turn(self) -> GameState:
        """Advance to the next player's turn."""
        next_idx = (self.current_player_idx + 1) % self.num_players
        new_turn = self.turn_number + 1 if next_idx == 0 else self.turn_number

        return self.model_copy(
            update={
                "current_player_idx": next_idx,
                "turn_number": new_turn,
            }
        )

    def check_winner(self) -> GameState:
        """
        Check for game end conditions and update state accordingly.

        The game ends when:
        1. A player reaches the winning points threshold
        2. The round completes (all players get equal turns)
        3. The player with the most points wins (ties broken by fewer cards)
        """
        state = self

        # Check if current player just reached winning points
        current = self.current_player
        if current.points >= self.config.winning_points and not self.is_final_round:
            state = state.model_copy(
                update={
                    "is_final_round": True,
                    "first_player_to_win": self.current_player_idx,
                }
            )

        # Check if we've completed the final round
        if state.is_final_round:
            # Final round ends when we return to the first player to reach winning points
            # (everyone gets one more turn after someone reaches 15)
            next_idx = (self.current_player_idx + 1) % self.num_players
            if next_idx == state.first_player_to_win:
                # Determine winner
                winner_idx = 0
                winner_points = -1
                winner_cards = float("inf")

                for idx, player in enumerate(state.players):
                    if player.points > winner_points or (
                        player.points == winner_points
                        and len(player.cards) < winner_cards
                    ):
                        winner_idx = idx
                        winner_points = player.points
                        winner_cards = len(player.cards)

                state = state.model_copy(
                    update={
                        "game_over": True,
                        "winner": winner_idx,
                    }
                )

        return state

    def refill_visible_card(self, tier: int) -> GameState:
        """Refill visible cards for a tier from the deck."""
        if len(self.visible_cards[tier]) >= VISIBLE_CARDS_PER_TIER:
            return self

        deck = list(self.card_decks[tier])
        visible = list(self.visible_cards[tier])

        while len(visible) < VISIBLE_CARDS_PER_TIER and deck:
            visible.append(deck.pop(0))

        return self.with_visible_cards(tier, tuple(visible)).with_deck(tier, tuple(deck))

