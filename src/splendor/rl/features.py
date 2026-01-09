"""Feature extraction from `GameState` for RL.

Design goals:
- Fixed-size observation vector for 2/3/4 player games
- Computed strictly from `GameState` (no engine internals)
- Cheap to compute (called every step)
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    import numpy as np  # type: ignore[import-not-found]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Missing dependency: numpy. Install the RL extras/deps to use splendor.rl.features."
    ) from e

from splendor.game.state import GameState
from splendor.models.gems import GemType


@dataclass(frozen=True)
class PlayerFeatures:
    points: float
    token_count: float
    gold_tokens: float
    cards_owned: float
    reserved_count: float
    nobles_owned: float
    bonuses_total: float
    bonuses_diamond: float
    bonuses_sapphire: float
    bonuses_emerald: float
    bonuses_ruby: float
    bonuses_onyx: float


@dataclass(frozen=True)
class StateFeatures:
    """Structured features (mostly for debugging)."""

    num_players: float
    turn_number: float
    bank_diamond: float
    bank_sapphire: float
    bank_emerald: float
    bank_ruby: float
    bank_onyx: float
    bank_gold: float
    current_player: PlayerFeatures
    opponents_mean: PlayerFeatures
    opponents_max: PlayerFeatures
    best_noble_progress: float
    mean_noble_progress: float
    purchasing_power: float
    best_affordable_card_points: float


def _player_features(state: GameState, player_idx: int) -> PlayerFeatures:
    p = state.players[player_idx]
    b = p.bonuses
    return PlayerFeatures(
        points=float(p.points),
        token_count=float(p.token_count),
        gold_tokens=float(p.tokens.gold),
        cards_owned=float(len(p.cards)),
        reserved_count=float(len(p.reserved)),
        nobles_owned=float(len(p.nobles)),
        bonuses_total=float(b.total_without_gold()),
        bonuses_diamond=float(b.diamond),
        bonuses_sapphire=float(b.sapphire),
        bonuses_emerald=float(b.emerald),
        bonuses_ruby=float(b.ruby),
        bonuses_onyx=float(b.onyx),
    )


def _as_vec(pf: PlayerFeatures) -> np.ndarray:
    return np.array(
        [
            pf.points,
            pf.token_count,
            pf.gold_tokens,
            pf.cards_owned,
            pf.reserved_count,
            pf.nobles_owned,
            pf.bonuses_total,
            pf.bonuses_diamond,
            pf.bonuses_sapphire,
            pf.bonuses_emerald,
            pf.bonuses_ruby,
            pf.bonuses_onyx,
        ],
        dtype=np.float32,
    )


def noble_progress(state: GameState, player_idx: int) -> np.ndarray:
    """Per-noble progress in [0,1] based on how many required bonuses are met."""
    bonuses = state.players[player_idx].bonuses
    progresses: list[float] = []
    for noble in state.nobles:
        req = noble.requirements
        required = 0
        satisfied = 0
        for gt in GemType.base_gems():
            need = req.get(gt)
            required += need
            satisfied += min(bonuses.get(gt), need)
        progresses.append((satisfied / required) if required > 0 else 1.0)
    return np.asarray(progresses, dtype=np.float32)


def purchasing_power(state: GameState, player_idx: int) -> tuple[float, float]:
    """Returns (sum_points_affordable, best_points_affordable) over visible cards."""
    player = state.players[player_idx]
    cards = []
    for tier in (1, 2, 3):
        cards.extend(state.visible_cards[tier])

    affordable_points = [float(c.points) for c in cards if player.can_afford(c.cost)]
    if not affordable_points:
        return 0.0, 0.0
    return float(sum(affordable_points)), float(max(affordable_points))


def extract_features(state: GameState, player_idx: int) -> StateFeatures:
    """Extract structured features from a `GameState` for `player_idx`."""
    cur = _player_features(state, player_idx)

    opp_idxs = [i for i in range(len(state.players)) if i != player_idx]
    if opp_idxs:
        opp_vecs = np.stack([_as_vec(_player_features(state, i)) for i in opp_idxs], axis=0)
        opp_mean = opp_vecs.mean(axis=0)
        opp_max = opp_vecs.max(axis=0)
        opp_mean_pf = _vec_to_player_features(opp_mean)
        opp_max_pf = _vec_to_player_features(opp_max)
    else:
        zeros = np.zeros((12,), dtype=np.float32)
        opp_mean_pf = _vec_to_player_features(zeros)
        opp_max_pf = _vec_to_player_features(zeros)

    np_prog = noble_progress(state, player_idx)
    best_prog = float(np.max(np_prog)) if np_prog.size else 0.0
    mean_prog = float(np.mean(np_prog)) if np_prog.size else 0.0

    power_sum, power_best = purchasing_power(state, player_idx)

    bank = state.bank
    return StateFeatures(
        num_players=float(state.num_players),
        turn_number=float(state.turn_number),
        bank_diamond=float(bank.diamond),
        bank_sapphire=float(bank.sapphire),
        bank_emerald=float(bank.emerald),
        bank_ruby=float(bank.ruby),
        bank_onyx=float(bank.onyx),
        bank_gold=float(bank.gold),
        current_player=cur,
        opponents_mean=opp_mean_pf,
        opponents_max=opp_max_pf,
        best_noble_progress=best_prog,
        mean_noble_progress=mean_prog,
        purchasing_power=float(power_sum),
        best_affordable_card_points=float(power_best),
    )


def feature_vector(state: GameState, player_idx: int) -> np.ndarray:
    """Fixed-size float32 observation vector for Gymnasium."""
    f = extract_features(state, player_idx)
    return np.concatenate(
        [
            np.array(
                [
                    f.num_players,
                    f.turn_number,
                    f.bank_diamond,
                    f.bank_sapphire,
                    f.bank_emerald,
                    f.bank_ruby,
                    f.bank_onyx,
                    f.bank_gold,
                    f.best_noble_progress,
                    f.mean_noble_progress,
                    f.purchasing_power,
                    f.best_affordable_card_points,
                ],
                dtype=np.float32,
            ),
            _as_vec(f.current_player),
            _as_vec(f.opponents_mean),
            _as_vec(f.opponents_max),
        ],
    ).astype(np.float32, copy=False)


def feature_vector_size() -> int:
    # global(12) + self(12) + opp_mean(12) + opp_max(12) = 48
    return 48


def _vec_to_player_features(vec: np.ndarray) -> PlayerFeatures:
    # vec layout matches _as_vec
    return PlayerFeatures(
        points=float(vec[0]),
        token_count=float(vec[1]),
        gold_tokens=float(vec[2]),
        cards_owned=float(vec[3]),
        reserved_count=float(vec[4]),
        nobles_owned=float(vec[5]),
        bonuses_total=float(vec[6]),
        bonuses_diamond=float(vec[7]),
        bonuses_sapphire=float(vec[8]),
        bonuses_emerald=float(vec[9]),
        bonuses_ruby=float(vec[10]),
        bonuses_onyx=float(vec[11]),
    )


