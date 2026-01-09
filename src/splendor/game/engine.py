"""Game engine for Splendor - handles game setup and turn execution."""

from __future__ import annotations

import random
from itertools import combinations
from typing import Optional

from splendor.data.loader import load_cards_by_tier, load_nobles
from splendor.game.state import (
    GameConfig,
    GameState,
    TOKENS_BY_PLAYER_COUNT,
    GOLD_TOKENS,
    VISIBLE_CARDS_PER_TIER,
)
from splendor.game.actions import (
    Action,
    TakeThreeDifferentAction,
    TakeTwoSameAction,
    ReserveVisibleAction,
    ReserveFromDeckAction,
    PurchaseVisibleAction,
    PurchaseReservedAction,
)
from splendor.models.gems import GemCollection, GemType
from splendor.models.player import Player


class GameEngine:
    """
    Engine for running Splendor games.

    Handles:
    - Game initialization with shuffled decks
    - Action validation
    - Turn execution
    - Win condition checking
    """

    def __init__(self, num_players: int = 2, seed: Optional[int] = None):
        """
        Initialize the game engine.

        Args:
            num_players: Number of players (2-4)
            seed: Random seed for reproducibility
        """
        if num_players < 2 or num_players > 4:
            raise ValueError("Number of players must be between 2 and 4")

        self.config = GameConfig(num_players=num_players)
        self.rng = random.Random(seed)
        self._state: Optional[GameState] = None

    @property
    def state(self) -> GameState:
        """Get current game state."""
        if self._state is None:
            raise RuntimeError("Game not started. Call reset() first.")
        return self._state

    def reset(self) -> GameState:
        """
        Start a new game with shuffled decks.

        Returns:
            Initial game state
        """
        # Create players
        players = tuple(Player(id=i) for i in range(self.config.num_players))

        # Setup bank tokens based on player count
        token_count = TOKENS_BY_PLAYER_COUNT[self.config.num_players]
        bank = GemCollection(
            diamond=token_count,
            sapphire=token_count,
            emerald=token_count,
            ruby=token_count,
            onyx=token_count,
            gold=GOLD_TOKENS,
        )

        # Load and shuffle cards
        cards_by_tier = load_cards_by_tier()
        card_decks = {}
        visible_cards = {}

        for tier in (1, 2, 3):
            deck = list(cards_by_tier[tier])
            self.rng.shuffle(deck)

            # Deal visible cards
            visible = deck[:VISIBLE_CARDS_PER_TIER]
            remaining = deck[VISIBLE_CARDS_PER_TIER:]

            visible_cards[tier] = tuple(visible)
            card_decks[tier] = tuple(remaining)

        # Load and shuffle nobles, take num_players + 1
        all_nobles = load_nobles()
        self.rng.shuffle(all_nobles)
        nobles = tuple(all_nobles[: self.config.num_players + 1])

        self._state = GameState(
            config=self.config,
            players=players,
            current_player_idx=0,
            bank=bank,
            card_decks=card_decks,
            visible_cards=visible_cards,
            nobles=nobles,
            turn_number=0,
        )

        return self._state

    def step(self, action: Action) -> GameState:
        """
        Execute an action and advance the game.

        Args:
            action: The action to execute

        Returns:
            New game state after the action
        """
        if self.state.game_over:
            raise RuntimeError("Game is already over")

        # Execute the action
        if isinstance(action, TakeThreeDifferentAction):
            new_state = self._execute_take_three(action)
        elif isinstance(action, TakeTwoSameAction):
            new_state = self._execute_take_two(action)
        elif isinstance(action, ReserveVisibleAction):
            new_state = self._execute_reserve_visible(action)
        elif isinstance(action, ReserveFromDeckAction):
            new_state = self._execute_reserve_from_deck(action)
        elif isinstance(action, PurchaseVisibleAction):
            new_state = self._execute_purchase_visible(action)
        elif isinstance(action, PurchaseReservedAction):
            new_state = self._execute_purchase_reserved(action)
        else:
            raise ValueError(f"Unknown action type: {type(action)}")

        # Check for noble visits
        new_state = self._check_noble_visits(new_state)

        # Check win condition
        new_state = new_state.check_winner()

        # Advance turn
        new_state = new_state.advance_turn()

        self._state = new_state
        return new_state

    def _execute_take_three(self, action: TakeThreeDifferentAction) -> GameState:
        """Take up to 3 different gem tokens."""
        state = self.state
        player = state.current_player
        bank = state.bank

        # Take gems from bank
        gems_taken = GemCollection()
        for gem_name in action.gems:
            gem_type = GemType(gem_name)
            if gem_type == GemType.GOLD:
                raise ValueError("Cannot take gold tokens with this action")
            if bank.get(gem_type) <= 0:
                raise ValueError(f"No {gem_name} tokens available")
            gems_taken = gems_taken.add_gem(gem_type)

        # Update player and bank
        new_player = player.add_tokens(gems_taken)
        new_bank = bank - gems_taken

        # Handle token return if over limit
        new_player, new_bank = self._handle_token_return(new_player, new_bank, action.return_gems)

        return state.with_current_player(new_player).with_bank(new_bank)

    def _execute_take_two(self, action: TakeTwoSameAction) -> GameState:
        """Take 2 tokens of the same color."""
        state = self.state
        player = state.current_player
        bank = state.bank

        gem_type = GemType(action.gem)
        if gem_type == GemType.GOLD:
            raise ValueError("Cannot take gold tokens with this action")
        if bank.get(gem_type) < 4:
            raise ValueError(f"Need at least 4 {action.gem} tokens to take 2")

        gems_taken = GemCollection.single(gem_type, 2)
        new_player = player.add_tokens(gems_taken)
        new_bank = bank - gems_taken

        # Handle token return if over limit
        new_player, new_bank = self._handle_token_return(new_player, new_bank, action.return_gems)

        return state.with_current_player(new_player).with_bank(new_bank)

    def _execute_reserve_visible(self, action: ReserveVisibleAction) -> GameState:
        """Reserve a visible card."""
        state = self.state
        player = state.current_player

        if not player.can_reserve:
            raise ValueError("Cannot reserve more than 3 cards")

        # Find and remove card from visible
        card = state.get_visible_card(action.card_id)
        if card is None:
            raise ValueError(f"Card {action.card_id} not found")

        tier = state.get_visible_card_tier(action.card_id)
        new_visible = tuple(c for c in state.visible_cards[tier] if c.id != action.card_id)
        state = state.with_visible_cards(tier, new_visible)

        # Refill from deck
        state = state.refill_visible_card(tier)

        # Add card to reserved
        new_player = player.add_reserved(card)

        # Give gold token if available
        bank = state.bank
        if bank.gold > 0:
            new_player = new_player.add_tokens(GemCollection(gold=1))
            bank = bank.remove_gem(GemType.GOLD)

        # Handle token return if over limit
        new_player, bank = self._handle_token_return(new_player, bank, action.return_gems)

        return state.with_current_player(new_player).with_bank(bank)

    def _execute_reserve_from_deck(self, action: ReserveFromDeckAction) -> GameState:
        """Reserve the top card from a deck."""
        state = self.state
        player = state.current_player

        if not player.can_reserve:
            raise ValueError("Cannot reserve more than 3 cards")

        deck = list(state.card_decks[action.tier])
        if not deck:
            raise ValueError(f"Tier {action.tier} deck is empty")

        card = deck.pop(0)
        state = state.with_deck(action.tier, tuple(deck))

        # Add card to reserved
        new_player = player.add_reserved(card)

        # Give gold token if available
        bank = state.bank
        if bank.gold > 0:
            new_player = new_player.add_tokens(GemCollection(gold=1))
            bank = bank.remove_gem(GemType.GOLD)

        # Handle token return if over limit
        new_player, bank = self._handle_token_return(new_player, bank, action.return_gems)

        return state.with_current_player(new_player).with_bank(bank)

    def _execute_purchase_visible(self, action: PurchaseVisibleAction) -> GameState:
        """Purchase a visible card."""
        state = self.state
        player = state.current_player

        card = state.get_visible_card(action.card_id)
        if card is None:
            raise ValueError(f"Card {action.card_id} not found")

        if not player.can_afford(card.cost):
            raise ValueError("Cannot afford this card")

        # Calculate and make payment
        payment = player.payment_for(card.cost)
        new_player = player.remove_tokens(payment)
        new_bank = state.bank + payment

        # Add card to player
        new_player = new_player.add_card(card)

        # Remove from visible and refill
        tier = state.get_visible_card_tier(action.card_id)
        new_visible = tuple(c for c in state.visible_cards[tier] if c.id != action.card_id)
        state = state.with_visible_cards(tier, new_visible)
        state = state.refill_visible_card(tier)

        return state.with_current_player(new_player).with_bank(new_bank)

    def _execute_purchase_reserved(self, action: PurchaseReservedAction) -> GameState:
        """Purchase a reserved card."""
        state = self.state
        player = state.current_player

        # Find card in reserved
        card = None
        for c in player.reserved:
            if c.id == action.card_id:
                card = c
                break

        if card is None:
            raise ValueError(f"Card {action.card_id} not in reserved cards")

        if not player.can_afford(card.cost):
            raise ValueError("Cannot afford this card")

        # Calculate and make payment
        payment = player.payment_for(card.cost)
        new_player = player.remove_tokens(payment)
        new_bank = state.bank + payment

        # Move card from reserved to purchased
        new_player = new_player.remove_reserved(card)
        new_player = new_player.add_card(card)

        return state.with_current_player(new_player).with_bank(new_bank)

    def _handle_token_return(
        self,
        player: Player,
        bank: GemCollection,
        return_gems: tuple,
    ) -> tuple[Player, GemCollection]:
        """Handle returning tokens if player exceeds limit."""
        if player.token_count <= self.config.max_tokens_per_player:
            return player, bank

        # Return specified gems
        for gem_name in return_gems:
            gem_type = GemType(gem_name)
            player = player.remove_tokens(GemCollection.single(gem_type))
            bank = bank.add_gem(gem_type)

        if player.token_count > self.config.max_tokens_per_player:
            raise ValueError(
                f"Player has {player.token_count} tokens, "
                f"must return to {self.config.max_tokens_per_player}"
            )

        return player, bank

    def _check_noble_visits(self, state: GameState) -> GameState:
        """Check if any nobles visit the current player."""
        player = state.current_player
        remaining_nobles = []

        for noble in state.nobles:
            if noble.can_visit(player.bonuses):
                player = player.add_noble(noble)
                # Only one noble visits per turn
                remaining_nobles.extend(n for n in state.nobles if n.id != noble.id)
                return state.with_current_player(player).with_nobles(tuple(remaining_nobles))
            remaining_nobles.append(noble)

        return state.with_current_player(player)

    def get_valid_actions(self) -> list[Action]:
        """
        Get all valid actions for the current player.

        Returns:
            List of valid actions
        """
        actions: list[Action] = []
        state = self.state
        player = state.current_player
        bank = state.bank
        current_tokens = player.token_count
        max_tokens = self.config.max_tokens_per_player

        # Take 3 different gems (only if won't exceed 10, or can take fewer)
        available_gems = [gt for gt in GemType.base_gems() if bank.get(gt) > 0]
        if available_gems:
            # How many can we take without exceeding limit?
            can_take = min(len(available_gems), max_tokens - current_tokens, 3)
            if can_take > 0:
                if can_take >= 3 and len(available_gems) >= 3:
                    for combo in combinations(available_gems, 3):
                        actions.append(TakeThreeDifferentAction(gems=tuple(g.value for g in combo)))
                elif can_take >= 2 and len(available_gems) >= 2:
                    for combo in combinations(available_gems, min(can_take, len(available_gems))):
                        actions.append(TakeThreeDifferentAction(gems=tuple(g.value for g in combo)))
                elif can_take >= 1:
                    for gem in available_gems:
                        actions.append(TakeThreeDifferentAction(gems=(gem.value,)))

        # Take 2 same gems (only if won't exceed 10)
        if current_tokens <= max_tokens - 2:
            for gem_type in GemType.base_gems():
                if bank.get(gem_type) >= 4:
                    actions.append(TakeTwoSameAction(gem=gem_type.value))

        # Reserve visible cards (gold adds 1 token)
        if player.can_reserve:
            gold_will_be_given = bank.gold > 0
            if not gold_will_be_given or current_tokens < max_tokens:
                for tier in (1, 2, 3):
                    for card in state.visible_cards[tier]:
                        actions.append(ReserveVisibleAction(card_id=card.id))
                    # Reserve from deck
                    if state.card_decks[tier]:
                        actions.append(ReserveFromDeckAction(tier=tier))

        # Purchase visible cards
        for tier in (1, 2, 3):
            for card in state.visible_cards[tier]:
                if player.can_afford(card.cost):
                    actions.append(PurchaseVisibleAction(card_id=card.id))

        # Purchase reserved cards
        for card in player.reserved:
            if player.can_afford(card.cost):
                actions.append(PurchaseReservedAction(card_id=card.id))

        return actions
