"""Game screen with full interaction handling for Splendor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import pygame

from splendor.game.engine import GameEngine
from splendor.game.actions import (
    Action,
    TakeThreeDifferentAction,
    TakeTwoSameAction,
    ReserveVisibleAction,
    ReserveFromDeckAction,
    PurchaseVisibleAction,
    PurchaseReservedAction,
)
from splendor.models.cards import DevelopmentCard
from splendor.models.gems import GemType
from splendor.gui.constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    CARD_WIDTH,
    CARD_HEIGHT,
    GEM_RADIUS,
    NOBLE_SIZE,
    PLAYER_PANEL_HEIGHT,
    BUTTON_HEIGHT,
    LOG_WIDTH,
)
from splendor.gui.renderer import Renderer


class InteractionMode(Enum):
    """Current interaction mode."""
    IDLE = auto()
    SELECTING_GEMS = auto()
    CARD_SELECTED = auto()
    DECK_SELECTED = auto()
    RESERVED_SELECTED = auto()
    RETURNING_GEMS = auto()


@dataclass
class GameScreen:
    """Main game screen handling rendering and interactions."""

    engine: GameEngine
    renderer: Renderer

    # Selection state
    mode: InteractionMode = InteractionMode.IDLE
    selected_gems: list[GemType] = field(default_factory=list)
    selected_card: Optional[DevelopmentCard] = None
    selected_card_tier: Optional[int] = None
    selected_deck_tier: Optional[int] = None
    selected_reserved_id: Optional[str] = None

    # Return gems state (when over 10 tokens)
    pending_action: Optional[object] = None
    gems_to_return: list[str] = field(default_factory=list)
    return_count_needed: int = 0

    # UI element positions (computed on draw)
    gem_rects: dict[GemType, pygame.Rect] = field(default_factory=dict)
    card_rects: dict[str, pygame.Rect] = field(default_factory=dict)
    deck_rects: dict[int, pygame.Rect] = field(default_factory=dict)
    noble_rects: dict[str, pygame.Rect] = field(default_factory=dict)
    player_clickables: dict[str, pygame.Rect] = field(default_factory=dict)
    button_rects: dict[str, pygame.Rect] = field(default_factory=dict)

    # Action log
    action_log: list[str] = field(default_factory=list)

    # Message to show
    message: str = ""

    def __post_init__(self):
        """Initialize the game screen."""
        self.action_log.append("Game started!")
        self.action_log.append(f"{self.engine.state.num_players} players")
        self.action_log.append("--- Turn 1 ---")

    def reset_selection(self):
        """Clear all selections."""
        self.mode = InteractionMode.IDLE
        self.selected_gems = []
        self.selected_card = None
        self.selected_card_tier = None
        self.selected_deck_tier = None
        self.selected_reserved_id = None
        self.pending_action = None
        self.gems_to_return = []
        self.return_count_needed = 0
        self.message = ""

    def _log_action(self, action: Action, player_id: int):
        """Log an action to the action log."""
        player_name = f"Player {player_id + 1}"
        
        if isinstance(action, TakeThreeDifferentAction):
            gems_str = ", ".join(action.gems)
            self.action_log.append(f"{player_name} took {gems_str}")
        elif isinstance(action, TakeTwoSameAction):
            self.action_log.append(f"{player_name} took 2 {action.gem}")
        elif isinstance(action, ReserveVisibleAction):
            card = self.engine.state.get_visible_card(action.card_id)
            if card:
                self.action_log.append(f"{player_name} reserved {card.bonus.value} card ({card.points}pts)")
            else:
                self.action_log.append(f"{player_name} reserved a card")
        elif isinstance(action, ReserveFromDeckAction):
            self.action_log.append(f"{player_name} reserved from Tier {action.tier} deck")
        elif isinstance(action, PurchaseVisibleAction):
            card = self.engine.state.get_visible_card(action.card_id)
            if card:
                self.action_log.append(f"{player_name} bought {card.bonus.value} card ({card.points}pts)")
            else:
                self.action_log.append(f"{player_name} bought a card")
        elif isinstance(action, PurchaseReservedAction):
            # Find the card in reserved
            for c in self.engine.state.current_player.reserved:
                if c.id == action.card_id:
                    self.action_log.append(f"{player_name} bought reserved {c.bonus.value} ({c.points}pts)")
                    break
            else:
                self.action_log.append(f"{player_name} bought reserved card")

    def _log_noble_visit(self, player_id: int):
        """Log when a noble visits."""
        self.action_log.append(f"Noble visited Player {player_id + 1}!")

    def _log_turn_change(self, turn_number: int):
        """Log turn change."""
        self.action_log.append(f"--- Turn {turn_number + 1} ---")

    def draw(self):
        """Draw the entire game screen."""
        self.renderer.clear()
        state = self.engine.state

        # Clear clickable areas
        self.gem_rects.clear()
        self.card_rects.clear()
        self.deck_rects.clear()
        self.noble_rects.clear()
        self.player_clickables.clear()
        self.button_rects.clear()

        # Main game area (excluding log panel)
        game_width = WINDOW_WIDTH - LOG_WIDTH

        # Layout constants
        left_margin = 40
        top_margin = 25

        # Draw turn info
        turn_text = f"Turn {state.turn_number + 1} - Player {state.current_player_idx + 1}'s turn"
        self.renderer.draw_text(turn_text, (game_width - 280, top_margin), font=self.renderer.font_medium)

        # Draw nobles row
        nobles_y = top_margin
        nobles_x = left_margin
        self.renderer.draw_text("Nobles:", (nobles_x, nobles_y + 5), font=self.renderer.font_small)
        nobles_x += 80
        for noble in state.nobles:
            rect = self.renderer.draw_noble(noble, (nobles_x, nobles_y))
            self.noble_rects[noble.id] = rect
            nobles_x += NOBLE_SIZE + 20

        # Draw card rows (tier 3 at top, tier 1 at bottom)
        cards_start_y = nobles_y + NOBLE_SIZE + 25
        card_row_spacing = CARD_HEIGHT + 15

        for tier in (3, 2, 1):
            row_y = cards_start_y + (3 - tier) * card_row_spacing

            # Tier label
            self.renderer.draw_text(f"Tier {tier}:", (left_margin - 5, row_y + CARD_HEIGHT // 2 - 10), (120, 120, 120), self.renderer.font_tiny)

            # Draw visible cards
            card_x = left_margin + 50
            for card in state.visible_cards[tier]:
                affordable = state.current_player.can_afford(card.cost)
                is_selected = self.selected_card and self.selected_card.id == card.id
                rect = self.renderer.draw_card(card, (card_x, row_y), selected=is_selected, affordable=affordable)
                self.card_rects[card.id] = rect
                card_x += CARD_WIDTH + 20

            # Draw deck
            deck_x = card_x + 40
            deck_count = len(state.card_decks[tier])
            is_deck_selected = self.selected_deck_tier == tier
            rect = self.renderer.draw_card_back(tier, (deck_x, row_y), deck_count, selected=is_deck_selected)
            self.deck_rects[tier] = rect

        # Draw bank tokens
        bank_y = cards_start_y + 3 * card_row_spacing + 15
        bank_x = left_margin
        self.renderer.draw_text("Bank:", (bank_x, bank_y), font=self.renderer.font_small)
        bank_x += 60

        for gem_type in list(GemType):
            count = state.bank.get(gem_type)
            is_selected = gem_type in self.selected_gems
            clickable = count > 0 and gem_type != GemType.GOLD
            rect = self.renderer.draw_gem(
                gem_type,
                (bank_x, bank_y + GEM_RADIUS + 5),
                count=count,
                selected=is_selected,
                clickable=clickable,
            )
            self.gem_rects[gem_type] = rect
            bank_x += GEM_RADIUS * 2 + 25

        # Draw player panels
        player_y = WINDOW_HEIGHT - PLAYER_PANEL_HEIGHT - 75
        num_players = state.num_players
        panel_width = (game_width - 60) // num_players - 15

        for i, player in enumerate(state.players):
            player_x = 30 + i * (panel_width + 15)
            is_current = i == state.current_player_idx
            clickables = self.renderer.draw_player_panel(
                player,
                (player_x, player_y),
                panel_width,
                is_current=is_current,
                selected_reserved_id=self.selected_reserved_id if is_current else None,
            )
            # Only current player's reserved cards are clickable
            if is_current:
                self.player_clickables.update(clickables)

        # Draw action buttons
        self._draw_action_buttons()

        # Draw selection panel
        self.renderer.draw_selection_panel(
            self.selected_gems,
            self.selected_card,
            self.selected_deck_tier,
            self.message,
        )

        # Draw log panel
        self.renderer.draw_log_panel(self.action_log)

        # Draw game over if applicable
        if state.game_over and state.winner is not None:
            self.renderer.draw_game_over(state.winner)

    def _draw_action_buttons(self):
        """Draw the action buttons based on current state."""
        game_width = WINDOW_WIDTH - LOG_WIDTH
        button_y = WINDOW_HEIGHT - 115
        button_x = game_width - 380

        mouse_pos = pygame.mouse.get_pos()

        if self.mode == InteractionMode.RETURNING_GEMS:
            # Show return gems UI
            remaining = self.return_count_needed - len(self.gems_to_return)
            self.message = f"Return {remaining} more gem(s) - click your tokens"

            # Confirm return button
            can_confirm = len(self.gems_to_return) == self.return_count_needed
            rect = self.renderer.draw_button(
                "Confirm Return",
                (button_x, button_y),
                width=130,
                enabled=can_confirm,
                hovered=can_confirm and pygame.Rect(button_x, button_y, 130, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["confirm_return"] = rect

            # Cancel button
            rect = self.renderer.draw_button(
                "Cancel",
                (button_x + 140, button_y),
                width=80,
                hovered=pygame.Rect(button_x + 140, button_y, 80, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["cancel"] = rect
            return

        # Normal action buttons
        if self.selected_gems:
            # Take gems button
            can_take = self._can_take_selected_gems()
            rect = self.renderer.draw_button(
                "Take Gems",
                (button_x, button_y),
                width=100,
                enabled=can_take,
                hovered=can_take and pygame.Rect(button_x, button_y, 100, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["take_gems"] = rect
            button_x += 110

        if self.selected_card or self.selected_reserved_id:
            # Buy button
            card = self.selected_card
            if self.selected_reserved_id:
                for c in self.engine.state.current_player.reserved:
                    if c.id == self.selected_reserved_id:
                        card = c
                        break

            can_buy = card and self.engine.state.current_player.can_afford(card.cost)
            rect = self.renderer.draw_button(
                "Buy",
                (button_x, button_y),
                width=70,
                enabled=can_buy,
                hovered=can_buy and pygame.Rect(button_x, button_y, 70, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["buy"] = rect
            button_x += 80

        if self.selected_card or self.selected_deck_tier:
            # Reserve button
            can_reserve = self.engine.state.current_player.can_reserve
            rect = self.renderer.draw_button(
                "Reserve",
                (button_x, button_y),
                width=90,
                enabled=can_reserve,
                hovered=can_reserve and pygame.Rect(button_x, button_y, 90, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["reserve"] = rect
            button_x += 100

        if self.mode != InteractionMode.IDLE:
            # Cancel button
            rect = self.renderer.draw_button(
                "Cancel",
                (button_x, button_y),
                width=80,
                hovered=pygame.Rect(button_x, button_y, 80, BUTTON_HEIGHT).collidepoint(mouse_pos),
            )
            self.button_rects["cancel"] = rect

    def _can_take_selected_gems(self) -> bool:
        """Check if the currently selected gems can be taken."""
        if not self.selected_gems:
            return False

        bank = self.engine.state.bank

        # Check if all gems are available
        for gem in self.selected_gems:
            if bank.get(gem) <= 0:
                return False

        # Valid take 3 different
        if len(self.selected_gems) <= 3 and len(set(self.selected_gems)) == len(self.selected_gems):
            return True

        # Valid take 2 same
        if len(self.selected_gems) == 2 and self.selected_gems[0] == self.selected_gems[1]:
            gem = self.selected_gems[0]
            return bank.get(gem) >= 4

        return False

    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Handle a mouse click. Returns True if game should return to menu."""
        state = self.engine.state

        # Handle game over
        if state.game_over:
            return True

        # Ignore clicks in log area
        if pos[0] >= WINDOW_WIDTH - LOG_WIDTH:
            return False

        # Handle return gems mode
        if self.mode == InteractionMode.RETURNING_GEMS:
            return self._handle_return_gems_click(pos)

        # Check button clicks
        for btn_name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                self._handle_button_click(btn_name)
                return False

        # Check gem clicks
        for gem_type, rect in self.gem_rects.items():
            if rect.collidepoint(pos) and gem_type != GemType.GOLD:
                self._handle_gem_click(gem_type)
                return False

        # Check card clicks
        for card_id, rect in self.card_rects.items():
            if rect.collidepoint(pos):
                self._handle_card_click(card_id)
                return False

        # Check deck clicks
        for tier, rect in self.deck_rects.items():
            if rect.collidepoint(pos):
                self._handle_deck_click(tier)
                return False

        # Check reserved card clicks
        for key, rect in self.player_clickables.items():
            if rect.collidepoint(pos) and key.startswith("reserved_"):
                card_id = key.replace("reserved_", "")
                self._handle_reserved_click(card_id)
                return False

        return False

    def _handle_gem_click(self, gem_type: GemType):
        """Handle clicking on a gem in the bank."""
        bank = self.engine.state.bank

        if bank.get(gem_type) <= 0:
            return

        # Clear card/deck selection when selecting gems
        self.selected_card = None
        self.selected_card_tier = None
        self.selected_deck_tier = None
        self.selected_reserved_id = None
        self.mode = InteractionMode.SELECTING_GEMS

        if gem_type in self.selected_gems:
            # Check if we can add a second of the same (take 2 same)
            if self.selected_gems.count(gem_type) == 1 and bank.get(gem_type) >= 4:
                # Can only take 2 same if that's our only selection
                if len(self.selected_gems) == 1:
                    self.selected_gems.append(gem_type)
                else:
                    # Deselect
                    self.selected_gems.remove(gem_type)
            else:
                # Deselect
                self.selected_gems.remove(gem_type)
        else:
            # Add new gem
            if len(self.selected_gems) < 3:
                # If we already have 2 of the same, clear and start fresh
                if len(self.selected_gems) == 2 and self.selected_gems[0] == self.selected_gems[1]:
                    self.selected_gems = [gem_type]
                else:
                    self.selected_gems.append(gem_type)

        if not self.selected_gems:
            self.mode = InteractionMode.IDLE

    def _handle_card_click(self, card_id: str):
        """Handle clicking on a visible card."""
        card = self.engine.state.get_visible_card(card_id)
        tier = self.engine.state.get_visible_card_tier(card_id)

        if card is None:
            return

        # Clear other selections
        self.selected_gems = []
        self.selected_deck_tier = None
        self.selected_reserved_id = None

        if self.selected_card and self.selected_card.id == card_id:
            # Deselect
            self.selected_card = None
            self.selected_card_tier = None
            self.mode = InteractionMode.IDLE
        else:
            self.selected_card = card
            self.selected_card_tier = tier
            self.mode = InteractionMode.CARD_SELECTED

    def _handle_deck_click(self, tier: int):
        """Handle clicking on a deck."""
        if not self.engine.state.card_decks[tier]:
            return

        # Clear other selections
        self.selected_gems = []
        self.selected_card = None
        self.selected_card_tier = None
        self.selected_reserved_id = None

        if self.selected_deck_tier == tier:
            self.selected_deck_tier = None
            self.mode = InteractionMode.IDLE
        else:
            self.selected_deck_tier = tier
            self.mode = InteractionMode.DECK_SELECTED

    def _handle_reserved_click(self, card_id: str):
        """Handle clicking on a reserved card."""
        # Clear other selections
        self.selected_gems = []
        self.selected_card = None
        self.selected_card_tier = None
        self.selected_deck_tier = None

        if self.selected_reserved_id == card_id:
            self.selected_reserved_id = None
            self.mode = InteractionMode.IDLE
        else:
            self.selected_reserved_id = card_id
            self.mode = InteractionMode.RESERVED_SELECTED

    def _handle_button_click(self, button: str):
        """Handle button clicks."""
        if button == "cancel":
            self.reset_selection()
            return

        if button == "take_gems":
            self._execute_take_gems()
        elif button == "buy":
            self._execute_buy()
        elif button == "reserve":
            self._execute_reserve()
        elif button == "confirm_return":
            self._execute_pending_with_returns()

    def _execute_action(self, action: Action):
        """Execute an action and log it."""
        player_id = self.engine.state.current_player_idx
        old_nobles = len(self.engine.state.current_player.nobles)
        old_turn = self.engine.state.turn_number
        
        # Log before executing (card info might change)
        self._log_action(action, player_id)
        
        self.engine.step(action)
        
        # Check for noble visit
        new_nobles = len(self.engine.state.get_player(player_id).nobles)
        if new_nobles > old_nobles:
            self._log_noble_visit(player_id)
        
        # Check for turn change
        if self.engine.state.turn_number > old_turn:
            self._log_turn_change(self.engine.state.turn_number)

    def execute_external_action(self, action: Action) -> None:
        """Execute an action originating outside the click UI (e.g. bot turn)."""
        if self.engine.state.game_over:
            return
        try:
            self._execute_action(action)
            self.reset_selection()
        except ValueError as e:
            # Shouldn't happen if caller uses `engine.get_valid_actions()`,
            # but keep the GUI resilient.
            self.message = str(e)

    def _execute_take_gems(self):
        """Execute a take gems action."""
        if not self.selected_gems:
            return

        gems = self.selected_gems[:]
        player = self.engine.state.current_player

        # Check if we need to return gems
        new_token_count = player.token_count + len(gems)
        max_tokens = self.engine.state.config.max_tokens_per_player

        if new_token_count > max_tokens:
            # Need to return gems
            self.return_count_needed = new_token_count - max_tokens

            # Create the pending action
            if len(gems) == 2 and gems[0] == gems[1]:
                self.pending_action = TakeTwoSameAction(gem=gems[0].value)
            else:
                self.pending_action = TakeThreeDifferentAction(gems=tuple(g.value for g in gems))

            self.mode = InteractionMode.RETURNING_GEMS
            self.gems_to_return = []
            return

        # Execute directly
        if len(gems) == 2 and gems[0] == gems[1]:
            action = TakeTwoSameAction(gem=gems[0].value)
        else:
            action = TakeThreeDifferentAction(gems=tuple(g.value for g in gems))

        try:
            self._execute_action(action)
            self.reset_selection()
        except ValueError as e:
            self.message = str(e)

    def _execute_buy(self):
        """Execute a buy action."""
        if self.selected_reserved_id:
            action = PurchaseReservedAction(card_id=self.selected_reserved_id)
        elif self.selected_card:
            action = PurchaseVisibleAction(card_id=self.selected_card.id)
        else:
            return

        try:
            self._execute_action(action)
            self.reset_selection()
        except ValueError as e:
            self.message = str(e)

    def _execute_reserve(self):
        """Execute a reserve action."""
        player = self.engine.state.current_player
        bank = self.engine.state.bank

        # Check if we'll get a gold and need to return gems
        gold_given = bank.gold > 0
        new_token_count = player.token_count + (1 if gold_given else 0)
        max_tokens = self.engine.state.config.max_tokens_per_player

        if new_token_count > max_tokens:
            self.return_count_needed = new_token_count - max_tokens

            if self.selected_deck_tier:
                self.pending_action = ReserveFromDeckAction(tier=self.selected_deck_tier)
            elif self.selected_card:
                self.pending_action = ReserveVisibleAction(card_id=self.selected_card.id)
            else:
                return

            self.mode = InteractionMode.RETURNING_GEMS
            self.gems_to_return = []
            return

        # Execute directly
        if self.selected_deck_tier:
            action = ReserveFromDeckAction(tier=self.selected_deck_tier)
        elif self.selected_card:
            action = ReserveVisibleAction(card_id=self.selected_card.id)
        else:
            return

        try:
            self._execute_action(action)
            self.reset_selection()
        except ValueError as e:
            self.message = str(e)

    def _handle_return_gems_click(self, pos: tuple[int, int]) -> bool:
        """Handle clicks during return gems mode."""
        # Check button clicks
        for btn_name, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                self._handle_button_click(btn_name)
                return False

        # Check player's token clicks (they need to select tokens to return)
        # For simplicity, we'll use the bank gem positions but check player tokens
        player = self.engine.state.current_player

        for gem_type, rect in self.gem_rects.items():
            if rect.collidepoint(pos):
                gem_name = gem_type.value
                player_has = player.tokens.get(gem_type)
                already_returning = self.gems_to_return.count(gem_name)

                if player_has > already_returning and len(self.gems_to_return) < self.return_count_needed:
                    self.gems_to_return.append(gem_name)
                elif gem_name in self.gems_to_return:
                    self.gems_to_return.remove(gem_name)
                return False

        return False

    def _execute_pending_with_returns(self):
        """Execute the pending action with return gems."""
        if not self.pending_action:
            return

        if len(self.gems_to_return) != self.return_count_needed:
            self.message = f"Must return exactly {self.return_count_needed} gems"
            return

        # Add return_gems to the action
        return_tuple = tuple(self.gems_to_return)

        if isinstance(self.pending_action, TakeThreeDifferentAction):
            action = TakeThreeDifferentAction(gems=self.pending_action.gems, return_gems=return_tuple)
        elif isinstance(self.pending_action, TakeTwoSameAction):
            action = TakeTwoSameAction(gem=self.pending_action.gem, return_gems=return_tuple)
        elif isinstance(self.pending_action, ReserveVisibleAction):
            action = ReserveVisibleAction(card_id=self.pending_action.card_id, return_gems=return_tuple)
        elif isinstance(self.pending_action, ReserveFromDeckAction):
            action = ReserveFromDeckAction(tier=self.pending_action.tier, return_gems=return_tuple)
        else:
            self.message = "Unknown action type"
            return

        try:
            self._execute_action(action)
            self.reset_selection()
        except ValueError as e:
            self.message = str(e)
