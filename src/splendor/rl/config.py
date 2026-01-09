"""RL configuration objects (reward weights, env knobs)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RewardType = Literal["baseline", "shaped"]


@dataclass(frozen=True)
class RewardConfig:
    """Reward shaping weights.

    Notes:
    - `compute_reward_baseline()` ignores these weights.
    - We keep weights small/moderate; PPO is sensitive to reward scale.
    """

    # Terminal outcome reward (applied when the game ends after an action).
    win_reward: float = 100.0
    loss_reward: float = -100.0

    # Dense shaping terms.
    points_weight: float = 10.0
    bonus_weight: float = 3.0
    noble_progress_weight: float = 2.0
    purchasing_power_weight: float = 0.5

    # Optional small preferences.
    efficiency_weight: float = 0.1

    # Environment-only: penalty for choosing an invalid action index.
    invalid_action_penalty: float = -1.0


