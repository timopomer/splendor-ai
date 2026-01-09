"""Terminal UI to start/stop PPO training and view progress.

Controls:
- s: start training (fresh)
- r: resume from latest checkpoint
- x: stop training gracefully (SIGINT)
- c: list checkpoints
- q: quit (stops training if running)
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import termios
import time
import tty
from datetime import timedelta
from pathlib import Path
from typing import Optional


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


def c(text: str, *styles: str) -> str:
    return "".join(styles) + text + Ansi.RESET


def progress_bar(
    value: float,
    max_value: float,
    width: int = 30,
    fill_char: str = "█",
    empty_char: str = "░",
) -> str:
    """Create a progress bar."""
    if max_value <= 0:
        pct = 0.0
    else:
        pct = min(1.0, max(0.0, value / max_value))
    filled = int(pct * width)
    empty = width - filled
    bar = c(fill_char * filled, Ansi.GREEN) + c(empty_char * empty, Ansi.DIM)
    return f"[{bar}] {pct * 100:5.1f}%"


def sparkline(values: list[float], width: int = 20) -> str:
    """Create a sparkline from values."""
    if not values:
        return ""
    chars = "▁▂▃▄▅▆▇█"
    min_v = min(values)
    max_v = max(values)
    if max_v - min_v < 1e-6:
        return chars[4] * min(len(values), width)
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values[-width:]
    result = ""
    for v in sampled:
        idx = int((v - min_v) / (max_v - min_v) * (len(chars) - 1))
        result += chars[idx]
    return result


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 0:
        return "--:--"
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    elif minutes > 0:
        return f"{minutes}m {secs:02d}s"
    else:
        return f"{secs}s"


def format_number(n: float) -> str:
    """Format number with K/M suffixes."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    else:
        return f"{n:.0f}"


def check_rl_deps() -> tuple[bool, list[str]]:
    """Return (ok, missing_modules)."""
    missing: list[str] = []
    for mod in ("numpy", "gymnasium", "stable_baselines3", "torch"):
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)
    return (len(missing) == 0), missing


def get_gpu_info() -> dict:
    """Get current GPU info from PyTorch."""
    try:
        import torch

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return {
                "type": "CUDA",
                "name": torch.cuda.get_device_name(0),
                "memory_used": torch.cuda.memory_allocated(0) / 1024 / 1024,
                "memory_total": props.total_memory / 1024 / 1024,
            }
        elif torch.backends.mps.is_available():
            try:
                mem = torch.mps.current_allocated_memory() / 1024 / 1024
            except AttributeError:
                mem = 0
            return {
                "type": "MPS",
                "name": "Apple Silicon GPU",
                "memory_used": mem,
                "memory_total": 0,
            }
    except Exception:
        pass
    return {"type": "CPU", "name": "CPU", "memory_used": 0, "memory_total": 0}


def tail_last_n_json(path: Path, n: int = 50) -> list[dict]:
    """Read last n JSON lines from file."""
    if not path.exists():
        return []
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 256 * 1024), os.SEEK_SET)
            data = f.read().decode("utf-8", errors="ignore")
        lines = [ln for ln in data.splitlines() if ln.strip()]
        results = []
        for line in lines[-n:]:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return results
    except Exception:
        return []


def tail_last_json(path: Path) -> Optional[dict]:
    """Read last JSON line from file."""
    results = tail_last_n_json(path, 1)
    return results[0] if results else None


def get_reward_history(path: Path, limit: int = 100) -> list[float]:
    """Extract reward history from progress file."""
    entries = tail_last_n_json(path, limit * 2)
    rewards = []
    for entry in entries:
        mean = entry.get("ep_rew_mean_100")
        if entry.get("event") == "rollout_end" and mean is not None:
            rewards.append(float(mean))
    return rewards[-limit:]


def count_checkpoints(checkpoint_dir: Path) -> list[Path]:
    """List checkpoint files sorted by step count."""
    if not checkpoint_dir.exists():
        return []
    checkpoints = list(checkpoint_dir.glob("*.zip"))

    def extract_steps(p: Path) -> int:
        try:
            parts = p.stem.split("_")
            for i, part in enumerate(parts):
                if part == "steps" and i > 0:
                    return int(parts[i - 1])
            for part in reversed(parts):
                if part.isdigit():
                    return int(part)
        except (ValueError, IndexError):
            pass
        return 0

    checkpoints.sort(key=extract_steps)
    return checkpoints


def spawn_training(cmd: list[str]) -> subprocess.Popen:
    """Start training subprocess."""
    return subprocess.Popen(
        cmd,
        cwd=str(Path.cwd()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def try_sigint(p: subprocess.Popen) -> None:
    """Send SIGINT to gracefully stop training."""
    if p.poll() is not None:
        return
    try:
        p.send_signal(signal.SIGINT)
    except Exception:
        try:
            p.terminate()
        except Exception:
            pass


def get_terminal_size() -> tuple[int, int]:
    """Get terminal width and height."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


class RLTrainingTUI:
    def __init__(self, args):
        self.args = args
        self.run_name = Path(args.out).stem + f"_{args.reward}"
        self.progress_path = (
            Path(args.progress_file)
            if args.progress_file
            else Path("artifacts/progress") / f"{self.run_name}.jsonl"
        )
        self.ckpt_dir = Path(args.checkpoint_dir) / self.run_name

        self.process: Optional[subprocess.Popen] = None
        self.last_render = ""
        self.show_checkpoints = False
        self.message = ""
        self.message_time = 0.0

        # Build command
        self.train_cmd = [
            sys.executable,
            "scripts/train_ppo.py",
            "--reward",
            args.reward,
            "--timesteps",
            str(args.timesteps),
            "--seed",
            str(args.seed),
            "--out",
            args.out,
            "--checkpoint-dir",
            args.checkpoint_dir,
            "--checkpoint-freq",
            str(args.checkpoint_freq),
            "--run-name",
            self.run_name,
            "--progress-file",
            str(self.progress_path),
            "--device",
            args.device,
            "--arch",
            args.arch,
        ]
        if args.multiprocess:
            self.train_cmd.append("--multiprocess")

    def start_training(self, resume: bool = False):
        """Start or resume training."""
        if self.process is not None and self.process.poll() is None:
            self.set_message("Training already running!", Ansi.YELLOW)
            return

        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)

        cmd = self.train_cmd.copy()
        if resume:
            cmd.extend(["--resume", "latest"])
            self.set_message("Resuming from latest checkpoint...", Ansi.CYAN)
        else:
            self.set_message("Starting fresh training...", Ansi.GREEN)

        self.process = spawn_training(cmd)

    def stop_training(self):
        """Stop training gracefully."""
        if self.process is not None:
            try_sigint(self.process)
            self.set_message("Stopping (saving checkpoint)...", Ansi.YELLOW)

    def set_message(self, msg: str, color: str = Ansi.RESET):
        """Set a temporary message to display."""
        self.message = c(msg, color, Ansi.BOLD)
        self.message_time = time.time()

    def render(self) -> str:
        """Render the TUI."""
        width, _ = get_terminal_size()
        lines: list[str] = []

        # Header
        lines.append(c("═" * width, Ansi.CYAN))
        lines.append(c(" 🎮 Splendor RL Training", Ansi.BOLD, Ansi.CYAN))
        lines.append(c("═" * width, Ansi.CYAN))

        # Status
        running = self.process is not None and self.process.poll() is None
        status_icon = "🟢" if running else "🔴"
        if running:
            status_text = c("TRAINING", Ansi.GREEN, Ansi.BOLD)
        else:
            status_text = c("STOPPED", Ansi.RED, Ansi.BOLD)

        # GPU info
        gpu = get_gpu_info()
        gpu_text = f"{gpu['type']}: {gpu['name']}"
        if gpu["memory_total"] > 0:
            mem_pct = gpu["memory_used"] / gpu["memory_total"] * 100
            gpu_text += f" ({mem_pct:.0f}% used)"

        lines.append("")
        lines.append(f"Status: {status_icon} {status_text}")
        lines.append(f"Device: {c(gpu_text, Ansi.YELLOW)}")
        lines.append(f"Architecture: {c(self.args.arch, Ansi.MAGENTA, Ansi.BOLD)}")

        # Get latest progress
        last = tail_last_json(self.progress_path)
        checkpoints = count_checkpoints(self.ckpt_dir)
        lines.append(f"Checkpoints: {c(str(len(checkpoints)), Ansi.MAGENTA)}")

        # Progress section
        if last:
            timesteps = last.get("timesteps", 0)
            target = self.args.timesteps

            lines.append("")
            lines.append(c("─── Progress ───", Ansi.BOLD, Ansi.MAGENTA))

            # Progress bar
            pbar = progress_bar(timesteps, target, width=min(40, width - 30))
            ts_text = f"{format_number(timesteps)} / {format_number(target)}"
            lines.append(f"{pbar}  {ts_text}")

            # Stats
            elapsed = last.get("elapsed_seconds", 0)
            fps = last.get("fps_approx", 0)
            if fps > 0:
                remaining = (target - timesteps) / fps
                eta_text = format_duration(remaining)
            else:
                eta_text = "--"

            elapsed_text = format_duration(elapsed)
            lines.append(
                f"Elapsed: {c(elapsed_text, Ansi.CYAN)}  "
                f"ETA: {c(eta_text, Ansi.YELLOW)}  "
                f"FPS: {c(f'{fps:.0f}', Ansi.GREEN)}"
            )

            # Training metrics
            lines.append("")
            lines.append(c("─── Training Metrics ───", Ansi.BOLD, Ansi.MAGENTA))

            ep_rew = last.get("ep_rew_mean_100")
            ep_len = last.get("ep_len_mean_100")
            ep_rew_min = last.get("ep_rew_min_100")
            ep_rew_max = last.get("ep_rew_max_100")
            updates = last.get("updates", 0)
            episodes = last.get("episodes_total", 0)
            invalid_pct = last.get("invalid_action_pct", 0)

            if ep_rew is not None:
                rew_color = Ansi.GREEN if ep_rew > 0 else Ansi.RED
                rew_text = f"Reward (mean): {c(f'{ep_rew:+.2f}', rew_color)}"
                if ep_rew_min is not None and ep_rew_max is not None:
                    rew_text += f"  (min: {ep_rew_min:+.1f}, max: {ep_rew_max:+.1f})"
                lines.append(rew_text)

            if ep_len is not None:
                lines.append(f"Episode Length: {c(f'{ep_len:.1f}', Ansi.CYAN)}")

            inv_color = Ansi.RED if invalid_pct > 10 else Ansi.GREEN
            lines.append(
                f"Updates: {c(str(updates), Ansi.YELLOW)}  "
                f"Episodes: {c(str(episodes), Ansi.YELLOW)}  "
                f"Invalid: {c(f'{invalid_pct:.1f}%', inv_color)}"
            )

            # Reward sparkline
            rewards = get_reward_history(self.progress_path, limit=min(50, width - 20))
            if rewards:
                spark = sparkline(rewards, width=min(50, width - 20))
                lines.append(f"Reward trend: {c(spark, Ansi.GREEN)}")

            # Policy metrics if available
            policy_loss = last.get("policy_gradient_loss")
            value_loss = last.get("value_loss")
            entropy = last.get("entropy_loss")

            if policy_loss is not None or value_loss is not None:
                policy_parts = []
                if policy_loss is not None:
                    policy_parts.append(f"P.Loss: {policy_loss:.4f}")
                if value_loss is not None:
                    policy_parts.append(f"V.Loss: {value_loss:.4f}")
                if entropy is not None:
                    policy_parts.append(f"Entropy: {entropy:.4f}")
                lines.append(c("  ".join(policy_parts), Ansi.DIM))

        else:
            lines.append("")
            lines.append(c("No training data yet.", Ansi.DIM))
            lines.append(c("Press 's' to start or 'r' to resume.", Ansi.DIM))

        # Checkpoints section (if toggled)
        if self.show_checkpoints and checkpoints:
            lines.append("")
            lines.append(c("─── Checkpoints ───", Ansi.BOLD, Ansi.MAGENTA))
            for ckpt in checkpoints[-5:]:
                lines.append(c(f"  • {ckpt.name}", Ansi.DIM))

        # Message
        if self.message and time.time() - self.message_time < 3.0:
            lines.append("")
            lines.append(self.message)

        # Footer with controls
        lines.append("")
        lines.append(c("─" * width, Ansi.CYAN))
        lines.append(
            f"{c('s', Ansi.GREEN, Ansi.BOLD)}=start  "
            f"{c('r', Ansi.CYAN, Ansi.BOLD)}=resume  "
            f"{c('x', Ansi.RED, Ansi.BOLD)}=stop  "
            f"{c('c', Ansi.MAGENTA, Ansi.BOLD)}=checkpoints  "
            f"{c('q', Ansi.YELLOW, Ansi.BOLD)}=quit"
        )

        return "\n".join(lines)

    def handle_key(self, key: str) -> bool:
        """Handle keypress. Return False to quit."""
        if key == "s":
            self.start_training(resume=False)
        elif key == "r":
            self.start_training(resume=True)
        elif key == "x":
            self.stop_training()
        elif key == "c":
            self.show_checkpoints = not self.show_checkpoints
        elif key == "q":
            if self.process is not None:
                self.stop_training()
            return False
        return True

    def run(self) -> int:
        """Main loop."""
        # Check dependencies
        ok, missing = check_rl_deps()
        if not ok:
            clear_screen()
            print(c("Splendor RL TUI", Ansi.BOLD, Ansi.CYAN))
            print("")
            print(c("RL dependencies missing.", Ansi.RED, Ansi.BOLD))
            print("")
            print("Missing modules:")
            for m in missing:
                print(f"  - {m}")
            print("")
            print("Fix by running:")
            print(c("  uv sync --extra rl --extra dev", Ansi.BOLD))
            print("")
            return 2

        # Set up terminal for raw input
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())

            while True:
                # Non-blocking key read
                if sys.stdin in select_readable(0.2):
                    ch = sys.stdin.read(1)
                    if not self.handle_key(ch):
                        break

                # Render
                screen = self.render()
                if screen != self.last_render:
                    clear_screen()
                    print(screen)
                    self.last_render = screen

        except KeyboardInterrupt:
            if self.process is not None:
                self.stop_training()
            return 130

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        return 0


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def select_readable(timeout: float):
    """Check if stdin has input ready (Unix only)."""
    import select

    r, _, _ = select.select([sys.stdin], [], [], timeout)
    return r


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive TUI for Splendor RL")
    parser.add_argument(
        "--reward",
        choices=["baseline", "shaped"],
        default="shaped",
        help="Reward function type",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=1_000_000,
        help="Total training timesteps",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument(
        "--out",
        type=str,
        default="artifacts/splendor_ppo",
        help="Output model path",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="artifacts/checkpoints",
        help="Checkpoint directory",
    )
    parser.add_argument(
        "--checkpoint-freq",
        type=int,
        default=50_000,
        help="Checkpoint frequency (timesteps)",
    )
    parser.add_argument(
        "--progress-file",
        type=str,
        default="",
        help="Progress JSONL file path",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "mps", "cpu"],
        default="auto",
        help="Training device",
    )
    parser.add_argument(
        "--arch",
        choices=["small", "medium", "large", "gpu-heavy"],
        default="small",
        help="Network size (gpu-heavy = max GPU utilization)",
    )
    parser.add_argument(
        "--multiprocess",
        action="store_true",
        help="Use SubprocVecEnv for parallel envs",
    )
    args = parser.parse_args()

    tui = RLTrainingTUI(args)
    return tui.run()


if __name__ == "__main__":
    raise SystemExit(main())
