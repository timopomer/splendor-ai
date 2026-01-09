"""Main entry point for Splendor GUI."""

from __future__ import annotations

import sys
from enum import Enum, auto
from pathlib import Path

import pygame

from splendor.game.engine import GameEngine
from splendor.gui.constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    BACKGROUND_COLOR,
    PANEL_COLOR,
    TEXT_COLOR,
    HIGHLIGHT_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER,
    CURRENT_PLAYER_COLOR,
)
from splendor.gui.renderer import Renderer
from splendor.gui.game_screen import GameScreen


class AppState(Enum):
    """Application state."""
    MENU = auto()
    PLAYING = auto()


class SplendorApp:
    """Main application class."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Splendor")
        
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)
        
        self.state = AppState.MENU
        self.selected_players = 2
        # Per-seat player type for seats 0..3 (only first `selected_players` are used).
        self.seat_is_bot: list[bool] = [False, False, False, False]
        # Bot policy settings (PPO model is optional).
        self.bot_policy_name: str = "random"  # "random" | "ppo"
        self.bot_model_path: str = "artifacts/splendor_ppo.zip"
        self._bot_policy = None
        self._last_bot_move_ms: int = 0
        self.game_screen: GameScreen | None = None
        
        self.running = True

    def run(self):
        """Main application loop."""
        while self.running:
            self._handle_events()
            self._maybe_play_bot_turn()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def _handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self._handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == AppState.PLAYING:
                        self.state = AppState.MENU
                    else:
                        self.running = False

    def _handle_click(self, pos: tuple[int, int]):
        """Handle mouse click based on current state."""
        if self.state == AppState.MENU:
            self._handle_menu_click(pos)
        elif self.state == AppState.PLAYING and self.game_screen:
            if self.game_screen.handle_click(pos):
                # Return to menu
                self.state = AppState.MENU

    def _handle_menu_click(self, pos: tuple[int, int]):
        """Handle clicks on the menu screen."""
        # Check player count buttons
        for i, num_players in enumerate([2, 3, 4]):
            btn_rect = self._get_player_button_rect(i)
            if btn_rect.collidepoint(pos):
                self.selected_players = num_players
                # Ensure seats outside selected range are reset to human.
                for j in range(self.selected_players, 4):
                    self.seat_is_bot[j] = False

        # Check per-seat human/bot toggle buttons
        for seat in range(self.selected_players):
            rect = self._get_seat_type_button_rect(seat)
            if rect.collidepoint(pos):
                self.seat_is_bot[seat] = not self.seat_is_bot[seat]

        # Check bot policy toggle button
        policy_rect = self._get_policy_button_rect()
        if policy_rect.collidepoint(pos):
            self.bot_policy_name = "ppo" if self.bot_policy_name == "random" else "random"

        # Check start button
        start_rect = self._get_start_button_rect()
        if start_rect.collidepoint(pos):
            self._start_game()

    def _get_player_button_rect(self, index: int) -> pygame.Rect:
        """Get the rect for a player count button."""
        center_x = WINDOW_WIDTH // 2
        btn_width = 80
        btn_height = 50
        total_width = 3 * btn_width + 2 * 20  # 3 buttons + 2 gaps
        start_x = center_x - total_width // 2
        return pygame.Rect(start_x + index * (btn_width + 20), 380, btn_width, btn_height)

    def _get_start_button_rect(self) -> pygame.Rect:
        """Get the rect for the start button."""
        return pygame.Rect(WINDOW_WIDTH // 2 - 110, 575, 220, 60)

    def _get_seat_type_button_rect(self, seat_idx: int) -> pygame.Rect:
        """Button rect to toggle a seat between Human/Bot."""
        center_x = WINDOW_WIDTH // 2
        btn_width = 170
        btn_height = 48
        gap = 18
        total = self.selected_players * btn_width + (self.selected_players - 1) * gap
        start_x = center_x - total // 2
        x = start_x + seat_idx * (btn_width + gap)
        return pygame.Rect(x, 455, btn_width, btn_height)

    def _get_policy_button_rect(self) -> pygame.Rect:
        """Button rect to toggle bot policy (Random/PPO)."""
        return pygame.Rect(WINDOW_WIDTH // 2 - 170, 520, 340, 44)

    def _start_game(self):
        """Start a new game with the selected number of players."""
        engine = GameEngine(num_players=self.selected_players)
        engine.reset()
        self.game_screen = GameScreen(engine=engine, renderer=self.renderer)
        self._bot_policy = None
        self._last_bot_move_ms = pygame.time.get_ticks()
        self.state = AppState.PLAYING

    def _maybe_play_bot_turn(self) -> None:
        """If it's a bot's turn, auto-play one action with a small delay."""
        if self.state != AppState.PLAYING or not self.game_screen:
            return
        state = self.game_screen.engine.state
        if state.game_over:
            return

        cur = state.current_player_idx
        if cur >= len(self.seat_is_bot) or not self.seat_is_bot[cur]:
            return

        # Throttle bot moves so humans can follow.
        now = pygame.time.get_ticks()
        if now - self._last_bot_move_ms < 250:
            return
        self._last_bot_move_ms = now

        valid_actions = self.game_screen.engine.get_valid_actions()
        if not valid_actions:
            return

        # Lazy-load the policy.
        if self._bot_policy is None:
            if self.bot_policy_name == "ppo":
                try:
                    from splendor.rl.policy import SB3PPOPolicy

                    model_path = str(Path(self.bot_model_path))
                    self._bot_policy = SB3PPOPolicy(model_path=model_path, deterministic=True)
                except Exception:
                    # Fall back to random if PPO isn't available.
                    from splendor.rl.policy import RandomPolicy

                    self._bot_policy = RandomPolicy(seed=0)
            else:
                from splendor.rl.policy import RandomPolicy

                self._bot_policy = RandomPolicy(seed=0)

        try:
            action = self._bot_policy.select_action(state, cur, valid_actions)
        except Exception:
            action = valid_actions[0]

        self.game_screen.execute_external_action(action)

    def _draw(self):
        """Draw based on current state."""
        if self.state == AppState.MENU:
            self._draw_menu()
        elif self.state == AppState.PLAYING and self.game_screen:
            self.game_screen.draw()

    def _draw_menu(self):
        """Draw the main menu."""
        self.renderer.clear()
        
        # Title
        title_font = pygame.font.SysFont("Arial", 64, bold=True)
        title = title_font.render("SPLENDOR", True, CURRENT_PLAYER_COLOR)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)

        # Subtitle
        subtitle_font = pygame.font.SysFont("Arial", 24)
        subtitle = subtitle_font.render("A game of gem collection and prestige", True, TEXT_COLOR)
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 220))
        self.screen.blit(subtitle, subtitle_rect)

        # Player count selection
        label_font = pygame.font.SysFont("Arial", 28)
        label = label_font.render("Number of Players:", True, TEXT_COLOR)
        label_rect = label.get_rect(center=(WINDOW_WIDTH // 2, 330))
        self.screen.blit(label, label_rect)

        mouse_pos = pygame.mouse.get_pos()
        btn_font = pygame.font.SysFont("Arial", 32, bold=True)

        for i, num_players in enumerate([2, 3, 4]):
            rect = self._get_player_button_rect(i)
            is_selected = self.selected_players == num_players
            is_hovered = rect.collidepoint(mouse_pos)

            if is_selected:
                color = HIGHLIGHT_COLOR
            elif is_hovered:
                color = BUTTON_HOVER
            else:
                color = PANEL_COLOR

            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            pygame.draw.rect(
                self.screen,
                HIGHLIGHT_COLOR if is_selected else (100, 100, 100),
                rect,
                3 if is_selected else 1,
                border_radius=10,
            )

            text = btn_font.render(str(num_players), True, TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        # Seat type selection (Human/Bot)
        label2 = label_font.render("Human vs Bot:", True, TEXT_COLOR)
        label2_rect = label2.get_rect(center=(WINDOW_WIDTH // 2, 425))
        self.screen.blit(label2, label2_rect)

        for seat in range(self.selected_players):
            rect = self._get_seat_type_button_rect(seat)
            is_hovered = rect.collidepoint(mouse_pos)
            is_bot = self.seat_is_bot[seat]
            color = BUTTON_HOVER if is_hovered else PANEL_COLOR
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            pygame.draw.rect(
                self.screen,
                HIGHLIGHT_COLOR if is_bot else (100, 100, 100),
                rect,
                3 if is_bot else 1,
                border_radius=10,
            )
            seat_label = f"P{seat+1}: {'BOT' if is_bot else 'HUMAN'}"
            text = self.renderer.font_small.render(seat_label, True, TEXT_COLOR)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)

        # Bot policy toggle
        policy_rect = self._get_policy_button_rect()
        is_policy_hovered = policy_rect.collidepoint(mouse_pos)
        pygame.draw.rect(
            self.screen,
            BUTTON_HOVER if is_policy_hovered else PANEL_COLOR,
            policy_rect,
            border_radius=10,
        )
        pygame.draw.rect(self.screen, (100, 100, 100), policy_rect, 1, border_radius=10)
        policy_text = (
            f"Bot policy: {'PPO (artifacts/splendor_ppo.zip)' if self.bot_policy_name == 'ppo' else 'Random'}"
        )
        t = self.renderer.font_small.render(policy_text, True, TEXT_COLOR)
        self.screen.blit(t, t.get_rect(center=policy_rect.center))

        # Start button
        start_rect = self._get_start_button_rect()
        is_start_hovered = start_rect.collidepoint(mouse_pos)
        start_color = BUTTON_HOVER if is_start_hovered else BUTTON_COLOR

        pygame.draw.rect(self.screen, start_color, start_rect, border_radius=12)
        pygame.draw.rect(self.screen, (100, 150, 100), start_rect, 2, border_radius=12)

        start_text = btn_font.render("Start Game", True, TEXT_COLOR)
        start_text_rect = start_text.get_rect(center=start_rect.center)
        self.screen.blit(start_text, start_text_rect)

        # Instructions
        instructions = [
            "How to Play:",
            "• Click gems in the bank to select them, then click 'Take Gems'",
            "• Click a card to select it, then 'Buy' or 'Reserve'",
            "• Click a deck to reserve blindly from that tier",
            "• Click reserved cards to buy them later",
            "• First to 15 points triggers the final round!",
            "",
            "Press ESC to return to menu during game",
        ]

        inst_font = pygame.font.SysFont("Arial", 18)
        y_offset = 665
        for line in instructions:
            color = HIGHLIGHT_COLOR if line.startswith("How") else (180, 180, 180)
            text = inst_font.render(line, True, color)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, y_offset))
            self.screen.blit(text, text_rect)
            y_offset += 28


def main(skip_menu: bool = False, num_players: int = 2):
    """Entry point for the Splendor GUI."""
    app = SplendorApp()
    if skip_menu:
        app.selected_players = num_players
        app._start_game()
    app.run()


if __name__ == "__main__":
    main(skip_menu=False, num_players=2)

