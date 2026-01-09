"""Allow running the GUI module directly with: python -m splendor.gui"""

from splendor.gui.main import main

if __name__ == "__main__":
    # Start on menu so user can choose player count + human/bot seats.
    main(skip_menu=False, num_players=2)

