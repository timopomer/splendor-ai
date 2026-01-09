"""Splendor GUI module - Pygame-based graphical interface."""

from splendor.models.gems import GemType

# Window settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 950
FPS = 60

# Colors for gem types
GEM_COLORS: dict[GemType, tuple[int, int, int]] = {
    GemType.DIAMOND: (255, 255, 255),    # White
    GemType.SAPPHIRE: (30, 100, 200),    # Blue
    GemType.EMERALD: (20, 160, 80),      # Green
    GemType.RUBY: (200, 40, 40),         # Red
    GemType.ONYX: (40, 40, 40),          # Black
    GemType.GOLD: (230, 190, 50),        # Gold/Yellow
}

# UI Colors
BACKGROUND_COLOR = (28, 35, 45)
PANEL_COLOR = (45, 55, 70)
PANEL_LIGHT = (60, 72, 90)
TEXT_COLOR = (240, 240, 240)
TEXT_DARK = (30, 30, 30)
HIGHLIGHT_COLOR = (100, 180, 255)
CURRENT_PLAYER_COLOR = (255, 200, 80)
BUTTON_COLOR = (70, 130, 90)
BUTTON_HOVER = (90, 160, 110)
BUTTON_DISABLED = (80, 80, 80)
CARD_BG = (50, 60, 75)
NOBLE_BG = (80, 60, 80)
SELECTION_BG = (40, 50, 65)
LOG_BG = (35, 42, 52)

# Dimensions
CARD_WIDTH = 100
CARD_HEIGHT = 130
CARD_MINI_WIDTH = 65
CARD_MINI_HEIGHT = 85
GEM_RADIUS = 22
NOBLE_SIZE = 75
BUTTON_HEIGHT = 38
PLAYER_PANEL_HEIGHT = 160
LOG_WIDTH = 260

