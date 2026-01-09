# Agent Instructions

## Running Commands with uv

The project uses `uv` for dependency management. To use `uv` in terminal commands:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

This ensures `uv` is available in the shell. Add this before any `uv` commands.

### Common Commands

```bash
# Sync dependencies (install from uv.lock)
export PATH="$HOME/.local/bin:$PATH" && uv sync

# Run the GUI
export PATH="$HOME/.local/bin:$PATH" && uv run python -m splendor.gui

# Run tests
export PATH="$HOME/.local/bin:$PATH" && uv run pytest

# Add a new dependency
export PATH="$HOME/.local/bin:$PATH" && uv add <package>
```

### Sandbox Permissions

When running `uv sync` or installing packages, use `required_permissions: ["all"]` to avoid cache access issues.

## GUI Testing

The GUI is a Pygame application. To test it visually:

### Kill Previous Instances

Before launching a new instance, kill any existing ones:

```bash
pkill -f "python -m splendor.gui" || pkill -f "splendor.gui" || true
```

### Launch and Screenshot

Run the GUI in background and capture a screenshot:

```bash
export PATH="$HOME/.local/bin:$PATH" && cd /Volumes/code/splendor-ai && uv run python -m splendor.gui &
sleep 3
screencapture -x /tmp/splendor_screenshot.png
```

Then read the screenshot with `read_file` to visually inspect the GUI.

### Skip Menu for Testing

The GUI currently starts directly in game mode with 2 players (skip_menu=True in `__main__.py`). To restore the menu:

```python
# In src/splendor/gui/__main__.py
main(skip_menu=False)  # Show menu
main(skip_menu=True, num_players=2)  # Skip to 2-player game
```

### GUI Layout

The game screen contains:
- **Top**: Nobles row, Turn indicator
- **Middle**: 3 tiers of cards (Tier 3 at top, Tier 1 at bottom) with deck indicators
- **Below cards**: Bank tokens (clickable gems)
- **Bottom**: Player panels showing tokens, bonuses, reserved cards
- **Right sidebar**: Action Log

