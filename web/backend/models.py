"""Model registry for loading and managing bot models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from splendor.rl.policy import Policy, RandomPolicy, SB3PPOPolicy


# Path to models directory
MODELS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "models"

# Bot type determines the icon
BOT_TYPE = Literal["conventional", "neural"]
BOT_ICONS = {
    "conventional": "🤖",
    "neural": "🧠",
}


@dataclass
class NetworkInfo:
    """Neural network architecture info."""
    policy: str
    architecture: list[int]
    observation_dim: int
    action_space: str


@dataclass
class ModelMetadata:
    """Metadata about a bot model."""
    id: str
    name: str
    description: str
    type: BOT_TYPE  # "conventional" or "neural"
    algorithm: Optional[str]
    network: Optional[NetworkInfo]
    training_steps: Optional[int]
    training_games: Optional[int]
    win_rate_vs_random: Optional[float]
    model_path: Optional[Path]  # Path to model file, None for conventional

    @property
    def icon(self) -> str:
        """Icon is determined by type: 🤖 for conventional, 🧠 for neural."""
        return BOT_ICONS.get(self.type, "🤖")

    @classmethod
    def from_json(cls, data: dict, model_path: Optional[Path] = None) -> "ModelMetadata":
        """Create from JSON dict."""
        network_data = data.get("network")
        network = None
        if network_data:
            network = NetworkInfo(
                policy=network_data["policy"],
                architecture=network_data["architecture"],
                observation_dim=network_data["observation_dim"],
                action_space=network_data["action_space"],
            )
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            type=data["type"],
            algorithm=data.get("algorithm"),
            network=network,
            training_steps=data.get("training_steps"),
            training_games=data.get("training_games"),
            win_rate_vs_random=data.get("win_rate_vs_random"),
            model_path=model_path,
        )


# Hardcoded conventional bots (not trained models)
BUILTIN_BOTS: list[ModelMetadata] = [
    ModelMetadata(
        id="random",
        name="Random",
        description="Picks uniformly at random from valid actions.",
        type="conventional",
        algorithm=None,
        network=None,
        training_steps=None,
        training_games=None,
        win_rate_vs_random=None,
        model_path=None,
    ),
]


class ModelRegistry:
    """Registry for discovering and loading bot models."""

    def __init__(self, models_dir: Path = MODELS_DIR):
        self._models_dir = models_dir
        self._models: dict[str, ModelMetadata] = {}
        self._policy_cache: dict[str, Policy] = {}
        
        # Add builtin conventional bots
        for bot in BUILTIN_BOTS:
            self._models[bot.id] = bot
        
        # Scan for trained neural models
        self._scan_models()

    def _scan_models(self) -> None:
        """Scan models directory for available neural models."""
        if not self._models_dir.exists():
            return

        for model_dir in self._models_dir.iterdir():
            if not model_dir.is_dir():
                continue

            metadata_path = model_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                
                # Check for model file
                model_path = model_dir / "model.zip"
                if not model_path.exists():
                    model_path = None

                metadata = ModelMetadata.from_json(data, model_path)
                self._models[metadata.id] = metadata
            except Exception as e:
                print(f"Warning: Failed to load model from {model_dir}: {e}")

    def list_models(self) -> list[ModelMetadata]:
        """List all available models."""
        # Sort: conventional first, then neural by training steps (ascending)
        def sort_key(m: ModelMetadata) -> tuple:
            if m.type == "conventional":
                return (0, 0, m.name)
            return (1, m.training_steps or 0, m.name)
        
        return sorted(self._models.values(), key=sort_key)

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID."""
        return self._models.get(model_id)

    def create_policy(self, model_id: str, seed: Optional[int] = None) -> Policy:
        """Create a policy instance for the given model."""
        metadata = self._models.get(model_id)
        
        # Conventional bots use RandomPolicy
        if metadata is None or metadata.type == "conventional":
            return RandomPolicy(seed=seed)
        
        # Neural models use their trained policy
        if metadata.type == "neural" and metadata.model_path:
            cache_key = str(metadata.model_path)
            if cache_key not in self._policy_cache:
                try:
                    self._policy_cache[cache_key] = SB3PPOPolicy(
                        str(metadata.model_path),
                        deterministic=True,
                    )
                except ImportError:
                    print(f"Warning: stable-baselines3 not available, falling back to random")
                    return RandomPolicy(seed=seed)
            return self._policy_cache[cache_key]
        
        # Fallback to random
        return RandomPolicy(seed=seed)


# Global model registry instance
model_registry = ModelRegistry()
