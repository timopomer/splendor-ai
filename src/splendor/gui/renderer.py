"""Rendering functions for Splendor GUI."""

from __future__ import annotations

from typing import Optional

import pygame

from splendor.models.cards import DevelopmentCard
from splendor.models.gems import GemType
from splendor.models.nobles import Noble
from splendor.models.player import Player
from splendor.gui import (
    GEM_COLORS,
    BACKGROUND_COLOR,
    PANEL_COLOR,
    TEXT_COLOR,
    TEXT_DARK,
    HIGHLIGHT_COLOR,
    CURRENT_PLAYER_COLOR,
    BUTTON_COLOR,
    BUTTON_HOVER,
    BUTTON_DISABLED,
    CARD_BG,
    NOBLE_BG,
    SELECTION_BG,
    LOG_BG,
    CARD_WIDTH,
    CARD_HEIGHT,
    CARD_MINI_WIDTH,
    CARD_MINI_HEIGHT,
    GEM_RADIUS,
    NOBLE_SIZE,
    BUTTON_HEIGHT,
    PLAYER_PANEL_HEIGHT,
    LOG_WIDTH,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)


class Renderer:
    """Handles all drawing operations for the game."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_medium = pygame.font.SysFont("Arial", 20)
        self.font_small = pygame.font.SysFont("Arial", 16)
        self.font_tiny = pygame.font.SysFont("Arial", 12)

    def clear(self):
        """Clear the screen with background color."""
        self.screen.fill(BACKGROUND_COLOR)

    def draw_text(
        self,
        text: str,
        pos: tuple[int, int],
        color: tuple[int, int, int] = TEXT_COLOR,
        font: Optional[pygame.font.Font] = None,
        center: bool = False,
    ):
        """Draw text at the given position."""
        if font is None:
            font = self.font_medium
        surface = font.render(text, True, color)
        rect = surface.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        self.screen.blit(surface, rect)

    def draw_gem(
        self,
        gem_type: GemType,
        pos: tuple[int, int],
        radius: int = GEM_RADIUS,
        count: Optional[int] = None,
        selected: bool = False,
        clickable: bool = True,
    ) -> pygame.Rect:
        """Draw a gem token. Returns the bounding rect for click detection."""
        color = GEM_COLORS[gem_type]
        x, y = pos

        # Draw selection highlight
        if selected:
            pygame.draw.circle(self.screen, HIGHLIGHT_COLOR, (x, y), radius + 5)

        # Draw the gem circle
        pygame.draw.circle(self.screen, color, (x, y), radius)

        # Draw border
        border_color = (200, 200, 200) if gem_type != GemType.DIAMOND else (100, 100, 100)
        pygame.draw.circle(self.screen, border_color, (x, y), radius, 2)

        # Draw count if provided
        if count is not None:
            text_color = TEXT_DARK if gem_type in (GemType.DIAMOND, GemType.GOLD) else TEXT_COLOR
            self.draw_text(str(count), (x, y), text_color, self.font_medium, center=True)

        return pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def draw_small_gem(
        self,
        gem_type: GemType,
        pos: tuple[int, int],
        count: int = 1,
        radius: int = 10,
    ):
        """Draw a small gem icon with count for card costs."""
        x, y = pos
        color = GEM_COLORS[gem_type]

        pygame.draw.circle(self.screen, color, (x, y), radius)
        border_color = (200, 200, 200) if gem_type != GemType.DIAMOND else (100, 100, 100)
        pygame.draw.circle(self.screen, border_color, (x, y), radius, 1)

        if count > 1:
            text_color = TEXT_DARK if gem_type in (GemType.DIAMOND, GemType.GOLD) else TEXT_COLOR
            self.draw_text(str(count), (x, y), text_color, self.font_tiny, center=True)

    def draw_card(
        self,
        card: DevelopmentCard,
        pos: tuple[int, int],
        selected: bool = False,
        affordable: bool = False,
        width: int = CARD_WIDTH,
        height: int = CARD_HEIGHT,
    ) -> pygame.Rect:
        """Draw a development card. Returns bounding rect."""
        x, y = pos
        rect = pygame.Rect(x, y, width, height)
        is_mini = width < CARD_WIDTH

        # Draw card background
        bg_color = CARD_BG
        if selected:
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect.inflate(6, 6), border_radius=8)
        elif affordable:
            pygame.draw.rect(self.screen, (80, 140, 80), rect.inflate(4, 4), border_radius=7)

        pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)

        # Draw bonus gem at top right
        bonus_color = GEM_COLORS[card.bonus]
        gem_size = 20 if is_mini else 25
        bonus_rect = pygame.Rect(x + width - gem_size - 5, y + 5, gem_size, gem_size)
        pygame.draw.rect(self.screen, bonus_color, bonus_rect, border_radius=4)
        border_color = (200, 200, 200) if card.bonus != GemType.DIAMOND else (100, 100, 100)
        pygame.draw.rect(self.screen, border_color, bonus_rect, 1, border_radius=4)

        # Draw points if any
        if card.points > 0:
            font = self.font_medium if is_mini else self.font_large
            self.draw_text(
                str(card.points),
                (x + 8, y + 5),
                TEXT_COLOR,
                font,
            )

        # Draw tier indicator
        tier_text = "•" * card.tier
        self.draw_text(tier_text, (x + 5, y + height - 18), (150, 150, 150), self.font_tiny)

        # Draw costs at bottom
        cost_y = y + height - (35 if is_mini else 45)
        cost_x = x + 8
        gem_spacing = 18 if is_mini else 24
        gem_radius = 8 if is_mini else 10
        for gem_type in GemType.base_gems():
            cost = card.cost.get(gem_type)
            if cost > 0:
                self.draw_small_gem(gem_type, (cost_x + gem_radius, cost_y + gem_radius), cost, radius=gem_radius)
                cost_x += gem_spacing

        return rect

    def draw_card_back(
        self,
        tier: int,
        pos: tuple[int, int],
        count: int,
        selected: bool = False,
    ) -> pygame.Rect:
        """Draw a face-down card deck. Returns bounding rect."""
        x, y = pos
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)

        # Tier colors
        tier_colors = {
            1: (60, 100, 60),
            2: (100, 100, 60),
            3: (60, 60, 100),
        }

        if selected:
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect.inflate(6, 6), border_radius=8)

        pygame.draw.rect(self.screen, tier_colors.get(tier, CARD_BG), rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 2, border_radius=6)

        # Draw tier number and count
        self.draw_text(f"Tier {tier}", (x + CARD_WIDTH // 2, y + 55), TEXT_COLOR, self.font_medium, center=True)
        self.draw_text(f"({count})", (x + CARD_WIDTH // 2, y + 85), (180, 180, 180), self.font_small, center=True)

        return rect

    def draw_noble(
        self,
        noble: Noble,
        pos: tuple[int, int],
        selected: bool = False,
    ) -> pygame.Rect:
        """Draw a noble tile. Returns bounding rect."""
        x, y = pos
        rect = pygame.Rect(x, y, NOBLE_SIZE, NOBLE_SIZE)

        if selected:
            pygame.draw.rect(self.screen, HIGHLIGHT_COLOR, rect.inflate(6, 6), border_radius=6)

        pygame.draw.rect(self.screen, NOBLE_BG, rect, border_radius=4)
        pygame.draw.rect(self.screen, (150, 120, 150), rect, 2, border_radius=4)

        # Draw points
        self.draw_text(str(noble.points), (x + 8, y + 5), TEXT_COLOR, self.font_medium)

        # Draw requirements
        req_y = y + 32
        req_x = x + 8
        for gem_type in GemType.base_gems():
            req = noble.requirements.get(gem_type)
            if req > 0:
                self.draw_small_gem(gem_type, (req_x + 10, req_y + 10), req)
                req_x += 24
                if req_x > x + NOBLE_SIZE - 25:
                    req_x = x + 8
                    req_y += 24

        return rect

    def draw_player_panel(
        self,
        player: Player,
        pos: tuple[int, int],
        width: int,
        is_current: bool = False,
        selected_reserved_id: Optional[str] = None,
    ) -> dict[str, pygame.Rect]:
        """Draw a player's status panel. Returns clickable areas."""
        x, y = pos
        clickable: dict[str, pygame.Rect] = {}

        # Panel background
        panel_rect = pygame.Rect(x, y, width, PLAYER_PANEL_HEIGHT)
        border_color = CURRENT_PLAYER_COLOR if is_current else (80, 80, 80)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, border_color, panel_rect, 3 if is_current else 1, border_radius=8)

        # Player name and points
        name = f"Player {player.id + 1}"
        if is_current:
            name += " ◀"
        self.draw_text(name, (x + 12, y + 10), CURRENT_PLAYER_COLOR if is_current else TEXT_COLOR, self.font_medium)
        self.draw_text(f"{player.points} pts", (x + width - 65, y + 10), TEXT_COLOR, self.font_medium)

        # Draw tokens
        token_y = y + 45
        token_x = x + 15
        self.draw_text("Tokens:", (token_x, token_y - 3), (150, 150, 150), self.font_tiny)
        token_x += 50
        for gem_type in list(GemType):
            count = player.tokens.get(gem_type)
            if count > 0:
                self.draw_small_gem(gem_type, (token_x, token_y + 7), count)
                token_x += 30

        # Draw bonuses
        bonus_y = y + 75
        bonus_x = x + 15
        self.draw_text("Bonuses:", (bonus_x, bonus_y - 3), (150, 150, 150), self.font_tiny)
        bonus_x += 55
        for gem_type in GemType.base_gems():
            count = player.bonuses.get(gem_type)
            if count > 0:
                color = GEM_COLORS[gem_type]
                pygame.draw.rect(self.screen, color, (bonus_x, bonus_y, 20, 20), border_radius=3)
                text_color = TEXT_DARK if gem_type == GemType.DIAMOND else TEXT_COLOR
                self.draw_text(str(count), (bonus_x + 10, bonus_y + 10), text_color, self.font_tiny, center=True)
                bonus_x += 26

        # Draw reserved cards (clickable) - now as mini cards
        reserved_y = y + 105
        reserved_x = x + 10
        self.draw_text("Reserved:", (reserved_x, reserved_y - 3), (150, 150, 150), self.font_tiny)
        reserved_x += 2
        
        if player.reserved:
            for card in player.reserved:
                is_selected = selected_reserved_id == card.id
                affordable = player.can_afford(card.cost) if is_current else False
                card_rect = self.draw_card(
                    card,
                    (reserved_x, reserved_y + 12),
                    selected=is_selected,
                    affordable=affordable,
                    width=CARD_MINI_WIDTH,
                    height=CARD_MINI_HEIGHT - 25,
                )
                clickable[f"reserved_{card.id}"] = card_rect
                reserved_x += CARD_MINI_WIDTH + 8

        # Draw nobles collected
        if player.nobles:
            noble_x = x + width - 35
            noble_y = y + 105
            self.draw_text("Nobles:", (noble_x - 50, noble_y - 3), (150, 150, 150), self.font_tiny)
            for noble in player.nobles:
                pygame.draw.rect(self.screen, NOBLE_BG, (noble_x, noble_y + 12, 28, 28), border_radius=3)
                self.draw_text(str(noble.points), (noble_x + 14, noble_y + 26), TEXT_COLOR, self.font_small, center=True)
                noble_x -= 32

        return clickable

    def draw_button(
        self,
        text: str,
        pos: tuple[int, int],
        width: int = 100,
        enabled: bool = True,
        hovered: bool = False,
    ) -> pygame.Rect:
        """Draw a button. Returns the bounding rect."""
        x, y = pos
        rect = pygame.Rect(x, y, width, BUTTON_HEIGHT)

        if not enabled:
            color = BUTTON_DISABLED
        elif hovered:
            color = BUTTON_HOVER
        else:
            color = BUTTON_COLOR

        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 1, border_radius=6)

        text_color = TEXT_COLOR if enabled else (120, 120, 120)
        self.draw_text(text, (x + width // 2, y + BUTTON_HEIGHT // 2), text_color, self.font_medium, center=True)

        return rect

    def draw_selection_panel(
        self,
        selected_gems: list[GemType],
        selected_card: Optional[DevelopmentCard],
        selected_deck_tier: Optional[int],
        message: str = "",
    ):
        """Draw the selection/action panel at the bottom."""
        panel_rect = pygame.Rect(0, WINDOW_HEIGHT - 70, WINDOW_WIDTH - LOG_WIDTH, 70)
        pygame.draw.rect(self.screen, SELECTION_BG, panel_rect)
        pygame.draw.line(self.screen, (80, 80, 80), (0, WINDOW_HEIGHT - 70), (WINDOW_WIDTH - LOG_WIDTH, WINDOW_HEIGHT - 70), 2)

        # Draw selected items
        sel_x = 20
        sel_y = WINDOW_HEIGHT - 50

        if selected_gems:
            self.draw_text("Selected:", (sel_x, sel_y), (150, 150, 150), self.font_small)
            sel_x += 75
            for gem in selected_gems:
                self.draw_gem(gem, (sel_x, sel_y + 10), radius=15)
                sel_x += 40

        if selected_card:
            self.draw_text(f"Card: {selected_card.bonus.value} ({selected_card.points}pts)", (sel_x, sel_y), TEXT_COLOR, self.font_small)

        if selected_deck_tier:
            self.draw_text(f"Deck Tier {selected_deck_tier}", (sel_x, sel_y), TEXT_COLOR, self.font_small)

        if message:
            self.draw_text(message, ((WINDOW_WIDTH - LOG_WIDTH) // 2, sel_y), HIGHLIGHT_COLOR, self.font_medium, center=True)

    def draw_log_panel(self, log_entries: list[str], scroll_offset: int = 0):
        """Draw the action log panel on the right side."""
        panel_x = WINDOW_WIDTH - LOG_WIDTH
        panel_rect = pygame.Rect(panel_x, 0, LOG_WIDTH, WINDOW_HEIGHT)
        
        pygame.draw.rect(self.screen, LOG_BG, panel_rect)
        pygame.draw.line(self.screen, (60, 70, 85), (panel_x, 0), (panel_x, WINDOW_HEIGHT), 2)
        
        # Header
        header_rect = pygame.Rect(panel_x, 0, LOG_WIDTH, 40)
        pygame.draw.rect(self.screen, PANEL_COLOR, header_rect)
        pygame.draw.line(self.screen, (60, 70, 85), (panel_x, 40), (panel_x + LOG_WIDTH, 40), 1)
        self.draw_text("Action Log", (panel_x + LOG_WIDTH // 2, 20), TEXT_COLOR, self.font_medium, center=True)
        
        # Log entries
        y = 50
        line_height = 22
        max_lines = (WINDOW_HEIGHT - 60) // line_height
        
        # Show most recent entries first
        visible_entries = log_entries[-(max_lines):]
        
        for entry in visible_entries:
            # Wrap long text
            if len(entry) > 32:
                # Split into multiple lines
                words = entry.split()
                lines = []
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    if len(test_line) <= 32:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                for line in lines:
                    color = self._get_log_color(line)
                    self.draw_text(line, (panel_x + 10, y), color, self.font_small)
                    y += line_height
            else:
                color = self._get_log_color(entry)
                self.draw_text(entry, (panel_x + 10, y), color, self.font_small)
                y += line_height
            
            if y > WINDOW_HEIGHT - 20:
                break

    def _get_log_color(self, text: str) -> tuple[int, int, int]:
        """Get color for log entry based on content."""
        text_lower = text.lower()
        if "player 1" in text_lower:
            return (255, 180, 180)
        elif "player 2" in text_lower:
            return (180, 180, 255)
        elif "player 3" in text_lower:
            return (180, 255, 180)
        elif "player 4" in text_lower:
            return (255, 255, 180)
        elif "took" in text_lower or "take" in text_lower:
            return (150, 200, 150)
        elif "bought" in text_lower or "purchase" in text_lower:
            return (200, 180, 150)
        elif "reserved" in text_lower:
            return (180, 150, 200)
        elif "noble" in text_lower:
            return (220, 180, 220)
        elif "---" in text:
            return (80, 90, 100)
        return (180, 180, 180)

    def draw_game_over(self, winner: int):
        """Draw game over overlay."""
        # Semi-transparent overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Winner text
        self.draw_text(
            f"Game Over! Player {winner + 1} Wins!",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 30),
            CURRENT_PLAYER_COLOR,
            self.font_large,
            center=True,
        )
        self.draw_text(
            "Click anywhere to return to menu",
            (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20),
            TEXT_COLOR,
            self.font_medium,
            center=True,
        )
