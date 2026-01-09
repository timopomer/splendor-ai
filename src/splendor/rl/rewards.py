"""Reward functions for Splendor RL."""

from __future__ import annotations

from splendor.game.state import GameState
from splendor.rl.config import RewardConfig
from splendor.rl.features import noble_progress, purchasing_power


def compute_reward_baseline(old_state: GameState, new_state: GameState, player_idx: int) -> float:
    """Baseline reward: points gained this turn."""
    return float(new_state.players[player_idx].points - old_state.players[player_idx].points)


def compute_reward(
    old_state: GameState,
    new_state: GameState,
    player_idx: int,
    config: RewardConfig = RewardConfig(),
) -> float:
    """Shaped reward with terminal outcome + dense progress signals."""
    reward = 0.0

    # Terminal outcome (after the action).
    if new_state.game_over:
        reward += config.win_reward if new_state.winner == player_idx else config.loss_reward

    old_p = old_state.players[player_idx]
    new_p = new_state.players[player_idx]

    # Points delta.
    reward += config.points_weight * float(new_p.points - old_p.points)

    # Bonus delta (engine building).
    reward += config.bonus_weight * float(
        new_p.bonuses.total_without_gold() - old_p.bonuses.total_without_gold()
    )

    # Noble progress delta (best noble).
    old_prog = noble_progress(old_state, player_idx)
    new_prog = noble_progress(new_state, player_idx)
    old_best = float(old_prog.max()) if old_prog.size else 0.0
    new_best = float(new_prog.max()) if new_prog.size else 0.0
    reward += config.noble_progress_weight * (new_best - old_best)

    # Purchasing power delta: sum of points of affordable visible cards.
    old_power_sum, _ = purchasing_power(old_state, player_idx)
    new_power_sum, _ = purchasing_power(new_state, player_idx)
    reward += config.purchasing_power_weight * (new_power_sum - old_power_sum)

    # Small efficiency preference (points per owned card), mainly as a tiebreaker hint.
    old_eff = float(old_p.points) / max(1.0, float(len(old_p.cards)))
    new_eff = float(new_p.points) / max(1.0, float(len(new_p.cards)))
    reward += config.efficiency_weight * (new_eff - old_eff)

    return float(reward)


