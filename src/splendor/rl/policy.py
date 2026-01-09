"""Policies for choosing actions from a `GameState` (for bots).

These policies are intentionally thin wrappers around:
- `GameEngine.get_valid_actions()` (to enumerate legal actions)
- `feature_vector()` (to build model observations)

They are usable from:
- training (optionally)
- the GUI (bot players)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np  # type: ignore[import-not-found]

from splendor.game.actions import Action
from splendor.game.state import GameState
from splendor.rl.features import feature_vector


class Policy:
    """Base policy API."""

    def select_action_index(
        self, state: GameState, player_idx: int, valid_actions: Sequence[Action]
    ) -> int:
        raise NotImplementedError

    def select_action(
        self, state: GameState, player_idx: int, valid_actions: Sequence[Action]
    ) -> Action:
        if not valid_actions:
            raise ValueError("No valid actions available")
        idx = int(self.select_action_index(state, player_idx, valid_actions))
        if idx < 0 or idx >= len(valid_actions):
            idx = 0
        return valid_actions[idx]


@dataclass
class RandomPolicy(Policy):
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def select_action_index(
        self, state: GameState, player_idx: int, valid_actions: Sequence[Action]
    ) -> int:
        return int(self._rng.integers(0, len(valid_actions)))


class SB3PPOPolicy(Policy):
    """Stable-Baselines3 PPO policy wrapper."""

    def __init__(self, model_path: str, deterministic: bool = True):
        try:
            from stable_baselines3 import PPO  # type: ignore[import-not-found]
        except Exception as e:  # pragma: no cover
            raise ImportError(
                "Missing dependency: stable-baselines3. Install the RL extras/deps."
            ) from e

        self.model = PPO.load(model_path)
        self.deterministic = deterministic

    def select_action_index(
        self, state: GameState, player_idx: int, valid_actions: Sequence[Action]
    ) -> int:
        obs = feature_vector(state, player_idx)
        action_idx, _ = self.model.predict(obs, deterministic=self.deterministic)
        # SB3 sometimes returns numpy scalar/array
        return int(action_idx)


