"""Allow running the GUI module directly with: python -m splendor.gui"""

from splendor.gui.main import main

if __name__ == "__main__":
    # Start directly with 2 players for testing (skip menu)
    main(skip_menu=True, num_players=2)

