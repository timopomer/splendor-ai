# Splendor AI

A Python implementation of the board game Splendor, designed for reinforcement learning experiments.

## Game Overview

Splendor is a gem-collecting and card development game where players:

- Collect gem tokens (5 colors + gold wild tokens)
- Purchase development cards using gems
- Attract nobles for bonus points
- First to 15 points triggers the final round

## Game Components

### Gem Types

- Diamond (white)
- Sapphire (blue)
- Emerald (green)
- Ruby (red)
- Onyx (black)
- Gold (wild - only for tokens)

### Development Cards

- **Tier 1**: 40 cards (basic, cheaper)
- **Tier 2**: 30 cards (mid-tier)
- **Tier 3**: 20 cards (powerful, expensive)

Each card provides a permanent gem bonus and optional victory points (0-5).

### Nobles

- 10 noble tiles in the game
- Worth 3 victory points each
- Automatically visit when bonus requirements are met

## Player Actions

On each turn, a player performs one action:

1. **Take 3 different gems** - Take 1 token each of 3 different colors
2. **Take 2 same gems** - Take 2 tokens of one color (requires 4+ in bank)
3. **Reserve a card** - Reserve a visible card or top of deck, gain 1 gold
4. **Purchase a card** - Buy a visible or reserved card using tokens and bonuses

## Installation

```bash
pip install -e .
```

## License

MIT
