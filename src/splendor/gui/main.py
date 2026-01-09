"""Main entry point for Splendor GUI."""

from __future__ import annotations

import sys
from enum import Enum, auto

import pygame

from splendor.game.engine import GameEngine
from splendor.gui import (
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
        self.game_screen: GameScreen | None = None
        
        self.running = True

    def run(self):
        """Main application loop."""
        while self.running:
            self._handle_events()
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
        return pygame.Rect(WINDOW_WIDTH // 2 - 100, 500, 200, 60)

    def _start_game(self):
        """Start a new game with the selected number of players."""
        engine = GameEngine(num_players=self.selected_players)
        engine.reset()
        self.game_screen = GameScreen(engine=engine, renderer=self.renderer)
        self.state = AppState.PLAYING

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
        y_offset = 600
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
    # Start directly with 2 players for testing
    main(skip_menu=True, num_players=2)

