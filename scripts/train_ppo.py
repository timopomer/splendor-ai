"""Train a self-play Splendor policy with PPO (Stable-Baselines3).

This script trains a single shared policy that controls *all* players.
We randomize `num_players` per environment instance (2/3/4) to encourage
generalization across player counts.

Outputs:
- Final model: `<out>_<reward>.zip` (reward is always part of the filename)
- Checkpoints: `<checkpoint_dir>/<run_name>/` periodically during training

GPU Support:
- Uses MPS on Apple Silicon, CUDA on NVIDIA, or CPU fallback
- Override with --device flag
- Use --gpu-heavy for larger network that better utilizes GPU
"""

from __future__ import annotations

import argparse
import multiprocessing
import random
import sys
from pathlib import Path

import torch
from rl_progress_callback import ProgressJSONLCallback
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from splendor.rl.env import SplendorEnv

# Policy network architectures
# Note: total rollout size = n_envs * n_steps (collected before each update)
POLICY_CONFIGS = {
    "small": {
        "net_arch": dict(pi=[64, 64], vf=[64, 64]),
        "batch_size": 256,
        "n_steps": 2048,
        "n_envs": 8,
    },
    "medium": {
        "net_arch": dict(pi=[256, 256, 128], vf=[256, 256, 128]),
        "batch_size": 512,
        "n_steps": 2048,
        "n_envs": 16,
    },
    "large": {
        "net_arch": dict(pi=[512, 512, 256, 128], vf=[512, 512, 256, 128]),
        "batch_size": 1024,
        "n_steps": 2048,
        "n_envs": 32,
    },
    "gpu-heavy": {
        # Large network with many parameters for GPU utilization
        # Keep n_envs=8 since env stepping is CPU-bound Python code
        "net_arch": dict(pi=[1024, 1024, 512, 256], vf=[1024, 1024, 512, 256]),
        "batch_size": 4096,
        "n_steps": 2048,
        "n_envs": 8,
    },
}


def detect_device() -> str:
    """Auto-detect the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def make_env(seed: int, reward_type: str):
    def _thunk():
        num_players = random.choice([2, 3, 4])
        # Keep env seeds distinct; SB3 may also seed via reset(seed=...).
        return SplendorEnv(num_players=num_players, reward_type=reward_type, seed=seed)

    return _thunk


def with_reward_suffix(out: str, reward: str) -> str:
    """Ensure `reward` is part of the output filename (before optional .zip)."""
    p = Path(out)
    stem = p.stem
    suffix = p.suffix  # may be ".zip" or empty

    token = f"_{reward}"
    if stem.endswith(token):
        return str(p)
    return str(p.with_name(f"{stem}{token}{suffix}"))


def find_latest_checkpoint(checkpoint_dir: Path, run_name: str) -> Path | None:
    """Find the most recent checkpoint in the checkpoint directory."""
    ckpt_path = checkpoint_dir / run_name
    if not ckpt_path.exists():
        return None

    checkpoints = list(ckpt_path.glob("*.zip"))
    if not checkpoints:
        return None

    # Sort by step number extracted from filename (e.g., run_ckpt_200000_steps.zip)
    def extract_steps(p: Path) -> int:
        try:
            parts = p.stem.split("_")
            for i, part in enumerate(parts):
                if part == "steps" and i > 0:
                    return int(parts[i - 1])
            # Fallback: try to find any number
            for part in reversed(parts):
                if part.isdigit():
                    return int(part)
        except (ValueError, IndexError):
            pass
        return 0

    checkpoints.sort(key=extract_steps, reverse=True)
    return checkpoints[0] if checkpoints else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=1_000_000)
    parser.add_argument("--n-envs", type=int, default=None, help="Override env count")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--reward", choices=["baseline", "shaped"], default="shaped")
    parser.add_argument("--out", type=str, default="artifacts/splendor_ppo")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cuda", "mps", "cpu"],
        help="Device to train on (auto detects best available)",
    )
    parser.add_argument(
        "--arch",
        type=str,
        default="small",
        choices=list(POLICY_CONFIGS.keys()),
        help="Network architecture size (small/medium/large/gpu-heavy)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch size (default depends on --arch)",
    )
    parser.add_argument(
        "--n-steps",
        type=int,
        default=None,
        help="Override n_steps (default depends on --arch)",
    )
    parser.add_argument(
        "--checkpoint-freq",
        type=int,
        default=50_000,
        help=(
            "Checkpoint frequency. Note: SB3 counts this in calls to env.step(); "
            "with VecEnv, each call advances n_envs timesteps."
        ),
    )
    parser.add_argument("--checkpoint-dir", type=str, default="artifacts/checkpoints")
    parser.add_argument(
        "--run-name",
        type=str,
        default="",
        help="Optional name for this run (used for checkpoint subdirectory).",
    )
    parser.add_argument(
        "--progress-file",
        type=str,
        default="",
        help="Optional JSONL file to write training progress snapshots to.",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default="",
        help="Path to checkpoint .zip to resume training from, or 'latest' to auto-find.",
    )
    parser.add_argument(
        "--multiprocess",
        action="store_true",
        help="Use SubprocVecEnv instead of DummyVecEnv for parallel envs.",
    )
    args = parser.parse_args()

    # Get config for selected architecture
    arch_config = POLICY_CONFIGS[args.arch]
    batch_size = args.batch_size or arch_config["batch_size"]
    n_steps = args.n_steps or arch_config["n_steps"]
    net_arch = arch_config["net_arch"]

    # Determine n_envs: use CPU count if multiprocess and not explicitly set
    if args.n_envs:
        n_envs = args.n_envs
    elif args.multiprocess:
        n_envs = multiprocessing.cpu_count()
    else:
        n_envs = arch_config["n_envs"]

    print(f"[train_ppo] Architecture: {args.arch}", file=sys.stderr)
    print(f"[train_ppo] Network: pi={net_arch['pi']}, vf={net_arch['vf']}", file=sys.stderr)
    print(
        f"[train_ppo] n_envs={n_envs}, batch_size={batch_size}, n_steps={n_steps}",
        file=sys.stderr,
    )

    # Device selection
    device = args.device if args.device != "auto" else detect_device()
    print(f"[train_ppo] Using device: {device}", file=sys.stderr)

    random.seed(args.seed)

    # Create vectorized environment
    env_fns = [make_env(args.seed + i, args.reward) for i in range(n_envs)]
    if args.multiprocess and n_envs > 1:
        env = SubprocVecEnv(env_fns)
        print(f"[train_ppo] Using SubprocVecEnv with {n_envs} processes", file=sys.stderr)
    else:
        env = DummyVecEnv(env_fns)
        print(f"[train_ppo] Using DummyVecEnv with {n_envs} envs", file=sys.stderr)

    out_path = Path(with_reward_suffix(args.out, args.reward))
    run_name = args.run_name.strip() or out_path.stem
    checkpoint_dir = Path(args.checkpoint_dir)

    # Resume logic
    resume_path: Path | None = None
    initial_timesteps = 0

    if args.resume:
        if args.resume.lower() == "latest":
            resume_path = find_latest_checkpoint(checkpoint_dir, run_name)
            if resume_path:
                print(f"[train_ppo] Resuming from latest: {resume_path}", file=sys.stderr)
            else:
                print("[train_ppo] No checkpoint found, starting fresh", file=sys.stderr)
        else:
            resume_path = Path(args.resume)
            if not resume_path.exists():
                print(f"[train_ppo] Checkpoint not found: {resume_path}", file=sys.stderr)
                resume_path = None
            else:
                print(f"[train_ppo] Resuming from: {resume_path}", file=sys.stderr)

    # Policy kwargs for custom network architecture
    policy_kwargs = dict(net_arch=[net_arch])

    if resume_path and resume_path.exists():
        model = PPO.load(
            str(resume_path),
            env=env,
            device=device,
        )
        # Extract timesteps from checkpoint name
        try:
            parts = resume_path.stem.split("_")
            for i, part in enumerate(parts):
                if part == "steps" and i > 0:
                    initial_timesteps = int(parts[i - 1])
                    break
        except (ValueError, IndexError):
            pass
        print(f"[train_ppo] Loaded checkpoint at {initial_timesteps} timesteps", file=sys.stderr)
    else:
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            seed=args.seed,
            n_steps=n_steps,
            batch_size=batch_size,
            device=device,
            policy_kwargs=policy_kwargs,
        )

    progress_path = (
        Path(args.progress_file)
        if args.progress_file.strip()
        else (Path("artifacts/progress") / f"{run_name}.jsonl")
    )

    callbacks = []
    if args.checkpoint_freq and args.checkpoint_freq > 0:
        ckpt_dir = checkpoint_dir / run_name
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        callbacks.append(
            CheckpointCallback(
                save_freq=args.checkpoint_freq,
                save_path=str(ckpt_dir),
                name_prefix=f"{run_name}_ckpt",
                save_replay_buffer=False,
                save_vecnormalize=False,
            )
        )

    callbacks.append(ProgressJSONLCallback(str(progress_path), initial_timesteps=initial_timesteps))

    remaining_timesteps = max(0, args.timesteps - initial_timesteps)
    if remaining_timesteps == 0:
        print("[train_ppo] Already at or past target timesteps, nothing to train", file=sys.stderr)
        return

    print(
        f"[train_ppo] Training for {remaining_timesteps} more timesteps "
        f"(target: {args.timesteps})",
        file=sys.stderr,
    )

    try:
        model.learn(
            total_timesteps=remaining_timesteps,
            callback=callbacks,
            reset_num_timesteps=False,  # Continue counting from checkpoint
        )
    except KeyboardInterrupt:
        # Allow graceful stop from the CLI monitor. We'll still save the current model.
        print("\n[train_ppo] Interrupted, saving model...", file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(out_path))
    print(f"[train_ppo] Model saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    # Fix macOS multiprocessing issues (fork doesn't work well with debugger/MPS)
    if sys.platform == "darwin":
        try:
            multiprocessing.set_start_method("spawn")
        except RuntimeError:
            pass  # Already set
    main()
