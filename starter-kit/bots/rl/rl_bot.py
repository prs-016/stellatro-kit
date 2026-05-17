from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from stellatro_common import GameState, PlayerTurn
from stellatro_game import (
    CARD_DIM,
    JOKER_POOL_SIZE,
    MAX_JOKERS_PER_PLAYER,
    NUM_JOKER_TYPES,
    NUM_RANKS,
    NUM_SUITS,
    PLAYER_CARDS,
    SCORE_SCALE,
    Suit,
)
from stellatro_game.jokers import ALL_JOKER_CLASSES

# Ensure local bots/rl modules are importable when called from other packages
_RL_DIR = Path(__file__).resolve().parent
if str(_RL_DIR) not in sys.path:
    sys.path.insert(0, str(_RL_DIR))
_STARTER_ROOT = _RL_DIR.parents[1]
if str(_STARTER_ROOT) not in sys.path:
    sys.path.insert(0, str(_STARTER_ROOT))

from bots.utils import best_current_hand  # noqa: E402


ACTION_DIM = JOKER_POOL_SIZE
JOKER_DRAFT_OFFSET = 0
_DEFAULT_CHECKPOINT_PATH = _RL_DIR / "checkpoints" / "model_final.pt"


# ---------------------------------------------------------------------------
# Encoding helpers (mirror Game._encode_card / Game._encode_joker)
# ---------------------------------------------------------------------------

_SUIT_ORDER = [Suit.DIAMOND, Suit.HEART, Suit.CLUB, Suit.SPADE]
_JOKER_NAME_TO_IDX = {cls.name: idx for idx, cls in enumerate(ALL_JOKER_CLASSES)}
_DRAFT_PHASE_NAMES = {"DRAFT", "JOKER_DRAFT"}


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "RLBot checkpoint inference requires torch. Install the starter-kit "
            "ML dependencies or submit a non-checkpoint fallback bot."
        ) from exc
    return torch


def _build_model_from_checkpoint_config(cfg: dict):
    from model import build_model, ensure_supported_model_type

    ensure_supported_model_type(cfg["model_type"])
    return build_model(
        model_type=cfg["model_type"],
        embed_dim=cfg["embed_dim"],
        hidden_dim=cfg["hidden_dim"],
        num_layers=cfg.get("num_layers", 3),
    )


def _default_checkpoint_path() -> Path | None:
    env_path = os.getenv("STELLATRO_RL_CHECKPOINT")
    if env_path:
        return Path(env_path)
    if _DEFAULT_CHECKPOINT_PATH.exists():
        return _DEFAULT_CHECKPOINT_PATH
    return None


def _load_checkpoint(checkpoint_path: Path, device):
    torch = _require_torch()
    try:
        return torch.load(checkpoint_path, map_location=device, weights_only=True)
    except TypeError:
        return torch.load(checkpoint_path, map_location=device)


def _encode_card_model(card_model):
    """Encode a CardModel as a 17-dim one-hot vector (13 rank + 4 suit)."""
    torch = _require_torch()
    vec = torch.zeros(CARD_DIM)
    vec[card_model.rank - 2] = 1.0  # rank 2..14 -> index 0..12
    for suit_str in card_model.suits:
        try:
            s = Suit(suit_str)
            vec[NUM_RANKS + _SUIT_ORDER.index(s)] = 1.0
        except (ValueError, IndexError):
            pass
    return vec


def _encode_joker_model(joker_model):
    """Encode a JokerModel as a one-hot vector over all joker types."""
    torch = _require_torch()
    vec = torch.zeros(NUM_JOKER_TYPES)
    idx = _JOKER_NAME_TO_IDX.get(joker_model.name, -1)
    if idx >= 0:
        vec[idx] = 1.0
    return vec


def _flatten_state(state_dict: dict):
    """Flatten a main-branch Game.encode_state-style mapping."""
    torch = _require_torch()
    return torch.cat(
        [
            state_dict["my_hand"].flatten(),
            state_dict["opponent_hand"].flatten(),
            state_dict["available_jokers"].flatten(),
            state_dict["my_jokers"].flatten(),
            state_dict["opponent_jokers"].flatten(),
            state_dict["phase"],
            state_dict["jokers_remaining"],
            state_dict["scores"],
        ]
    )


# ---------------------------------------------------------------------------
# RLBot
# ---------------------------------------------------------------------------

class RLBot:
    """RL-trained bot implementing the pick_joker / pick_hand interface.

    The checkpointed policy selects jokers during draft. Hand play is solved
    deterministically by exhaustive search over all 5-card subsets.
    """

    def __init__(
        self,
        checkpoint_path: str | None = None,
        device: str = "cpu",
    ):
        self.device_name = device
        self.device = None
        self._model = None
        resolved_checkpoint = Path(checkpoint_path).expanduser() if checkpoint_path is not None else _default_checkpoint_path()
        if resolved_checkpoint is None:
            return

        torch = _require_torch()
        self.device = torch.device(device)
        ckpt = _load_checkpoint(resolved_checkpoint, self.device)
        cfg = ckpt["config"]
        self._model = _build_model_from_checkpoint_config(cfg)
        self._model.load_state_dict(ckpt["model_state_dict"])
        self._model.to(self.device)
        self._model.eval()

    # ------------------------------------------------------------------
    # Internal state encoding
    # ------------------------------------------------------------------

    def _build_obs(self, state: GameState) -> torch.Tensor:
        """Build a flat observation tensor from a GameState.

        Mirrors the main-branch Game.encode_state() structure consumed by
        _flatten_state() in env.py. Main exposes only the joker draft and play
        phases to bots, so the phase vector has two entries.
        """
        torch = _require_torch()
        player_turn = state.current_turn or PlayerTurn.PLAYER1
        if player_turn == PlayerTurn.PLAYER1:
            my_cards = state.player1_hand
            opp_cards = state.player2_hand
            my_jks = state.player1_jokers
            opp_jks = state.player2_jokers
            my_score = state.player1_score
            opp_score = state.player2_score
        else:
            my_cards = state.player2_hand
            opp_cards = state.player1_hand
            my_jks = state.player2_jokers
            opp_jks = state.player1_jokers
            my_score = state.player2_score
            opp_score = state.player1_score

        # Hands
        my_hand_enc = torch.zeros(PLAYER_CARDS, CARD_DIM)
        for i, c in enumerate(my_cards[:PLAYER_CARDS]):
            my_hand_enc[i] = _encode_card_model(c)

        opp_hand_enc = torch.zeros(PLAYER_CARDS, CARD_DIM)
        for i, c in enumerate(opp_cards[:PLAYER_CARDS]):
            opp_hand_enc[i] = _encode_card_model(c)

        # Joker pool (available_jokers)
        avail_enc = torch.zeros(JOKER_POOL_SIZE, NUM_JOKER_TYPES)
        for i, j in enumerate(state.joker_pool[:JOKER_POOL_SIZE]):
            avail_enc[i] = _encode_joker_model(j)

        # Owned jokers
        my_jk_enc = torch.zeros(MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)
        for i, j in enumerate(my_jks[:MAX_JOKERS_PER_PLAYER]):
            my_jk_enc[i] = _encode_joker_model(j)

        opp_jk_enc = torch.zeros(MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)
        for i, j in enumerate(opp_jks[:MAX_JOKERS_PER_PLAYER]):
            opp_jk_enc[i] = _encode_joker_model(j)

        # Phase one-hot
        phase_name = state.phase.name
        phase_enc = torch.zeros(2)
        phase_enc[0 if phase_name in _DRAFT_PHASE_NAMES else 1] = 1.0

        # Scalars
        jokers_remaining = torch.tensor([len(state.joker_pool) / JOKER_POOL_SIZE])
        scores = torch.tensor([float(my_score) / SCORE_SCALE, float(opp_score) / SCORE_SCALE])

        state_dict = {
            "my_hand": my_hand_enc,
            "opponent_hand": opp_hand_enc,
            "available_jokers": avail_enc,
            "my_jokers": my_jk_enc,
            "opponent_jokers": opp_jk_enc,
            "phase": phase_enc,
            "jokers_remaining": jokers_remaining,
            "scores": scores,
        }
        return _flatten_state(state_dict).to(self.device)

    def _run_model(self, obs: torch.Tensor) -> torch.Tensor:
        if self._model is None:
            raise RuntimeError(
                "RLBot requires checkpoint_path to run the policy. "
                "Pass RLBot(checkpoint_path='...') or use a different bot."
            )
        torch = _require_torch()
        with torch.no_grad():
            logits, _ = self._model(obs.unsqueeze(0))
        return logits.squeeze(0)

    # ------------------------------------------------------------------
    # Bot interface
    # ------------------------------------------------------------------

    def pick_joker(self, state: GameState) -> int:
        """Select a joker index from the available pool (0-indexed).

        Args:
            state: Current GameState during the draft phase.

        Returns:
            int: Index into state.joker_pool to pick.
        """
        if self._model is None:
            raise RuntimeError(
                "RLBot has no loaded checkpoint. Pass checkpoint_path, set "
                "STELLATRO_RL_CHECKPOINT, or place model_final.pt under "
                "starter-kit/bots/rl/checkpoints/."
            )

        obs = self._build_obs(state)
        logits = self._run_model(obs)

        torch = _require_torch()
        n_available = len(state.joker_pool)
        masked = torch.full((ACTION_DIM,), float("-inf"), dtype=logits.dtype, device=logits.device)
        masked[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n_available] = (
            logits[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n_available]
        )
        raw = int(masked.argmax().item())
        return raw - JOKER_DRAFT_OFFSET

    def pick_hand(self, state: GameState) -> List[int]:
        """Select the exact best 5-card hand for the active player.

        Args:
            state: Current GameState during PLAY phase.

        Returns:
            List[int]: 5 card indices (0-indexed into the player's hand).
        """
        indices = list(best_current_hand(state).indices)
        if len(indices) == 5:
            return indices
        return [0, 1, 2, 3, 4]

class Bot(RLBot):
    """Tournament-facing bot that loads the trained checkpoint automatically.

    Looks for ``checkpoints/model_final.pt`` next to this file, then falls back
    to ``STELLATRO_RL_CHECKPOINT`` env var. Pass ``checkpoint_path=None`` to
    disable the model and run without a checkpoint.
    """

    def __init__(self):
        super().__init__()
