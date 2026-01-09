"""Stable-Baselines3 callback to emit training progress to a JSONL file.

We write one JSON object per line (JSONL) so a CLI can tail it robustly.
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Optional

import torch
from stable_baselines3.common.callbacks import BaseCallback


class ProgressJSONLCallback(BaseCallback):
    """Emit progress records (reward, length, timesteps, updates) to JSONL."""

    def __init__(
        self,
        progress_path: str,
        *,
        flush_every: int = 1,
        window: int = 100,
        verbose: int = 0,
        initial_timesteps: int = 0,
        log_interval: int = 500,
    ):
        super().__init__(verbose=verbose)
        self.progress_path = Path(progress_path)
        self.flush_every = int(flush_every)
        self.window = int(window)
        self.initial_timesteps = initial_timesteps
        self.log_interval = log_interval

        self._episode_rewards: list[float] = []
        self._episode_lengths: list[int] = []
        self._cur_rewards: Optional[list[float]] = None
        self._cur_lengths: Optional[list[int]] = None
        self._recent_rewards: Deque[float] = deque(maxlen=self.window)
        self._recent_lengths: Deque[int] = deque(maxlen=self.window)
        self._lines_since_flush = 0
        self._f = None
        self._t0 = time.time()
        self._last_ts = 0
        self._last_log_ts = 0
        self._invalid_actions = 0
        self._total_actions = 0

    def _on_training_start(self) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        # Line-buffered for responsiveness.
        self._f = self.progress_path.open("a", encoding="utf-8", buffering=1)

        # Initialize per-env accumulators once we know n_envs.
        n_envs = int(getattr(self.training_env, "num_envs", 1))
        self._cur_rewards = [0.0 for _ in range(n_envs)]
        self._cur_lengths = [0 for _ in range(n_envs)]

        # Device info
        device = str(getattr(self.model, "device", "unknown"))

        # GPU memory info
        gpu_info = self._get_gpu_info()

        self._write(
            {
                "event": "training_start",
                "ts": time.time(),
                "n_envs": n_envs,
                "device": device,
                "initial_timesteps": self.initial_timesteps,
                **gpu_info,
            }
        )

    def _get_gpu_info(self) -> dict[str, Any]:
        """Get GPU memory and utilization info."""
        info: dict[str, Any] = {}
        try:
            if torch.cuda.is_available():
                info["gpu_name"] = torch.cuda.get_device_name(0)
                info["gpu_memory_allocated_mb"] = torch.cuda.memory_allocated(0) / 1024 / 1024
                info["gpu_memory_reserved_mb"] = torch.cuda.memory_reserved(0) / 1024 / 1024
                total_mem = torch.cuda.get_device_properties(0).total_memory
                info["gpu_memory_total_mb"] = total_mem / 1024 / 1024
            elif torch.backends.mps.is_available():
                info["gpu_name"] = "Apple MPS"
                # MPS doesn't provide detailed memory stats, but we can try
                try:
                    mem = torch.mps.current_allocated_memory()
                    info["gpu_memory_allocated_mb"] = mem / 1024 / 1024
                except AttributeError:
                    pass
        except Exception:
            pass
        return info

    def _on_step(self) -> bool:
        # VecEnv step locals
        rewards = self.locals.get("rewards")
        dones = self.locals.get("dones")
        infos = self.locals.get("infos")

        if (rewards is None or dones is None
                or self._cur_rewards is None or self._cur_lengths is None):
            return True

        # Track invalid actions from info
        if infos is not None:
            for info in infos:
                self._total_actions += 1
                if info.get("invalid_action", False):
                    self._invalid_actions += 1

        # rewards/dones are arrays length n_envs
        for i in range(len(self._cur_rewards)):
            r = float(rewards[i])
            d = bool(dones[i])
            self._cur_rewards[i] += r
            self._cur_lengths[i] += 1
            if d:
                ep_r = float(self._cur_rewards[i])
                ep_l = int(self._cur_lengths[i])
                self._episode_rewards.append(ep_r)
                self._episode_lengths.append(ep_l)
                self._recent_rewards.append(ep_r)
                self._recent_lengths.append(ep_l)
                self._cur_rewards[i] = 0.0
                self._cur_lengths[i] = 0

        # Emit progress update every log_interval steps
        if self.num_timesteps - self._last_log_ts >= self.log_interval:
            self._emit_progress("step")
            self._last_log_ts = self.num_timesteps

        return True

    def _emit_progress(self, event: str = "rollout_end") -> None:
        """Emit a progress snapshot."""
        now = time.time()
        elapsed = max(1e-6, now - self._t0)
        total_ts = self.num_timesteps + self.initial_timesteps

        recent_r = list(self._recent_rewards)
        recent_l = list(self._recent_lengths)
        mean_r = sum(recent_r) / len(recent_r) if recent_r else None
        mean_l = sum(recent_l) / len(recent_l) if recent_l else None
        min_r = min(recent_r) if recent_r else None
        max_r = max(recent_r) if recent_r else None

        # SB3 tracks updates internally as model._n_updates (PPO).
        n_updates = getattr(self.model, "_n_updates", None)

        # Invalid action rate
        invalid_rate = 0.0
        if self._total_actions > 0:
            invalid_rate = self._invalid_actions / self._total_actions * 100

        self._write(
            {
                "event": event,
                "ts": now,
                "timesteps": total_ts,
                "timesteps_this_run": int(self.num_timesteps),
                "updates": int(n_updates) if n_updates is not None else None,
                "episodes_total": len(self._episode_rewards),
                "ep_rew_mean_100": mean_r,
                "ep_rew_min_100": min_r,
                "ep_rew_max_100": max_r,
                "ep_len_mean_100": mean_l,
                "fps_approx": float(self.num_timesteps / elapsed),
                "elapsed_seconds": elapsed,
                "invalid_action_pct": invalid_rate,
            }
        )

    def _on_rollout_end(self) -> None:
        # Emit a full summary at the end of each rollout (includes GPU/policy info).
        self._last_ts = self.num_timesteps
        self._last_log_ts = self.num_timesteps  # Reset so we don't double-log

        now = time.time()
        elapsed = max(1e-6, now - self._t0)
        total_ts = self.num_timesteps + self.initial_timesteps

        recent_r = list(self._recent_rewards)
        recent_l = list(self._recent_lengths)
        mean_r = sum(recent_r) / len(recent_r) if recent_r else None
        mean_l = sum(recent_l) / len(recent_l) if recent_l else None
        min_r = min(recent_r) if recent_r else None
        max_r = max(recent_r) if recent_r else None

        n_updates = getattr(self.model, "_n_updates", None)

        invalid_rate = 0.0
        if self._total_actions > 0:
            invalid_rate = self._invalid_actions / self._total_actions * 100

        # GPU info (only at rollout end to reduce overhead)
        gpu_info = self._get_gpu_info()

        # Get policy loss info if available
        policy_info: dict[str, Any] = {}
        if hasattr(self.model, "logger") and self.model.logger is not None:
            try:
                logger_dict = getattr(self.model.logger, "name_to_value", {})
                keys = [
                    "train/policy_gradient_loss", "train/value_loss",
                    "train/entropy_loss", "train/approx_kl", "train/clip_fraction",
                ]
                for key in keys:
                    if key in logger_dict:
                        policy_info[key.replace("train/", "")] = float(logger_dict[key])
            except Exception:
                pass

        self._write(
            {
                "event": "rollout_end",
                "ts": now,
                "timesteps": total_ts,
                "timesteps_this_run": int(self.num_timesteps),
                "updates": int(n_updates) if n_updates is not None else None,
                "episodes_total": len(self._episode_rewards),
                "ep_rew_mean_100": mean_r,
                "ep_rew_min_100": min_r,
                "ep_rew_max_100": max_r,
                "ep_len_mean_100": mean_l,
                "fps_approx": float(self.num_timesteps / elapsed),
                "elapsed_seconds": elapsed,
                "invalid_action_pct": invalid_rate,
                **gpu_info,
                **policy_info,
            }
        )

    def _on_training_end(self) -> None:
        total_ts = self.num_timesteps + self.initial_timesteps
        self._write({
            "event": "training_end",
            "ts": time.time(),
            "timesteps": total_ts,
            "timesteps_this_run": int(self.num_timesteps),
            "episodes_total": len(self._episode_rewards),
        })
        if self._f:
            self._f.flush()
            self._f.close()
            self._f = None

    def _write(self, obj: dict[str, Any]) -> None:
        if not self._f:
            return
        self._f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._lines_since_flush += 1
        if self.flush_every > 0 and self._lines_since_flush >= self.flush_every:
            self._f.flush()
            self._lines_since_flush = 0
