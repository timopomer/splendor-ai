"""Gymnasium environment wrapper for Splendor self-play (shared policy).

This is a *single-agent* view over a multi-player game:
- The observation is always from the current player's perspective.
- The action is chosen for the current player.
- The reward returned is for the acting player for that step.

Over an episode, the shared policy is trained across all seat positions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing dependency: gymnasium. Install the RL extras/deps to use SplendorEnv."
    ) from e

from splendor.game.engine import GameEngine
from splendor.rl.config import RewardConfig, RewardType
from splendor.rl.features import feature_vector, feature_vector_size
from splendor.rl.rewards import compute_reward, compute_reward_baseline


@dataclass(frozen=True)
class StepInfo:
    player_idx: int
    valid_action_count: int
    invalid_action: bool
    reward_type: RewardType


class SplendorEnv(gym.Env[np.ndarray, int]):
    metadata = {"render_modes": []}

    def __init__(
        self,
        num_players: int = 2,
        reward_type: RewardType = "shaped",
        reward_config: Optional[RewardConfig] = None,
        seed: Optional[int] = None,
        max_actions: int = 64,
    ):
        if num_players not in (2, 3, 4):
            raise ValueError("num_players must be 2, 3, or 4")
        if reward_type not in ("baseline", "shaped"):
            raise ValueError("reward_type must be 'baseline' or 'shaped'")

        self.num_players = int(num_players)
        self.reward_type: RewardType = reward_type
        self.reward_config = reward_config or RewardConfig()
        self.max_actions = int(max_actions)

        self.engine = GameEngine(num_players=self.num_players, seed=seed)
        self._np_random: np.random.Generator = np.random.default_rng(seed)

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(feature_vector_size(),),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(self.max_actions)

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict[str, Any]] = None):
        super().reset(seed=seed)
        if seed is not None:
            self._np_random = np.random.default_rng(seed)
            # Re-seed engine RNG by recreating it (engine doesn't expose reseed).
            self.engine = GameEngine(num_players=self.num_players, seed=seed)

        state = self.engine.reset()
        obs = feature_vector(state, state.current_player_idx)
        info = {"player_idx": state.current_player_idx}
        return obs, info

    def step(self, action: int):
        # Snapshot before acting.
        old_state = self.engine.state
        acting_player_idx = old_state.current_player_idx

        valid_actions = self.engine.get_valid_actions()
        invalid = False

        if not valid_actions:
            # Should be unreachable in Splendor, but protect training loop.
            terminated = True
            truncated = False
            obs = feature_vector(old_state, acting_player_idx)
            return obs, 0.0, terminated, truncated, {
                "player_idx": acting_player_idx,
                "valid_action_count": 0,
                "invalid_action": False,
                "reward_type": self.reward_type,
            }

        # Map discrete index -> one of the current valid actions. Indices >= len(valid_actions)
        # are treated as invalid; we execute a random valid action with a penalty.
        if int(action) < 0 or int(action) >= len(valid_actions):
            invalid = True
            chosen = valid_actions[int(self._np_random.integers(0, len(valid_actions)))]
        else:
            chosen = valid_actions[int(action)]

        new_state = self.engine.step(chosen)

        # Reward is computed for the acting player (pre-step current player).
        if self.reward_type == "baseline":
            reward = compute_reward_baseline(old_state, new_state, acting_player_idx)
        else:
            reward = compute_reward(old_state, new_state, acting_player_idx, self.reward_config)

        if invalid:
            reward += float(self.reward_config.invalid_action_penalty)

        terminated = bool(new_state.game_over)
        truncated = False

        # Next observation is for the next current player (engine advances turn).
        obs = feature_vector(new_state, new_state.current_player_idx)
        info: dict[str, Any] = {
            "player_idx": acting_player_idx,
            "valid_action_count": len(valid_actions),
            "invalid_action": invalid,
            "reward_type": self.reward_type,
        }
        return obs, float(reward), terminated, truncated, info


