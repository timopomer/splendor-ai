"""Train a self-play Splendor policy with PPO (Stable-Baselines3).

This script trains a single shared policy that controls *all* players.
We randomize `num_players` per environment instance (2/3/4) to encourage
generalization across player counts.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from splendor.rl.env import SplendorEnv


def make_env(seed: int, reward_type: str):
    def _thunk():
        num_players = random.choice([2, 3, 4])
        # Keep env seeds distinct; SB3 may also seed via reset(seed=...).
        return SplendorEnv(num_players=num_players, reward_type=reward_type, seed=seed)

    return _thunk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=1_000_000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--reward", choices=["baseline", "shaped"], default="shaped")
    parser.add_argument("--out", type=str, default="artifacts/splendor_ppo")
    args = parser.parse_args()

    random.seed(args.seed)

    env = DummyVecEnv([make_env(args.seed + i, args.reward) for i in range(args.n_envs)])

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        seed=args.seed,
        n_steps=2048,
        batch_size=256,
    )
    model.learn(total_timesteps=args.timesteps)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out))


if __name__ == "__main__":
    main()


