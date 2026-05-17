from __future__ import annotations

import math
import random
import sys
from copy import deepcopy
from pathlib import Path
from typing import Optional

import torch
from tensordict import TensorDict, TensorDictBase
from torchrl.data import (
    Binary,
    Categorical,
    Composite,
    Unbounded,
)
from torchrl.envs import EnvBase

from stellatro_game import (
    Game,
    Phase,
    PlayerTurn,
    JOKER_POOL_SIZE,
    NUM_JOKER_TYPES,
    MAX_JOKERS_PER_PLAYER,
    PLAYER_CARDS,
    CARD_DIM,
    ALL_5_CARD_COMBOS,
)
from model import (
    ACTION_DIM,
    JOKER_DRAFT_OFFSET,
)

SCORE_SCALE = 10_000.0
_RL_DIR = Path(__file__).resolve().parent
_STARTER_ROOT = _RL_DIR.parents[1]


def _flatten_state(state_dict: dict[str, torch.Tensor]) -> torch.Tensor:
    """Flatten all encoded state tensors into a single vector."""
    parts = [
        state_dict["my_hand"].flatten(),
        state_dict["opponent_hand"].flatten(),
        state_dict["available_jokers"].flatten(),
        state_dict["my_jokers"].flatten(),
        state_dict["opponent_jokers"].flatten(),
        state_dict["phase"],
        state_dict["jokers_remaining"],
        state_dict["scores"],
    ]
    return torch.cat(parts)


def compute_obs_dim() -> int:
    """Compute the flat observation dimensionality."""
    return (
        PLAYER_CARDS * CARD_DIM          # my_hand
        + PLAYER_CARDS * CARD_DIM        # opponent_hand
        + JOKER_POOL_SIZE * NUM_JOKER_TYPES  # available_jokers
        + MAX_JOKERS_PER_PLAYER * NUM_JOKER_TYPES  # my_jokers
        + MAX_JOKERS_PER_PLAYER * NUM_JOKER_TYPES  # opponent_jokers
        + 2  # phase (one-hot: DRAFT, PLAY_OR_OVER)
        + 1  # jokers_remaining
        + 2  # scores
    )


OBS_DIM = compute_obs_dim()


def _draft_phase() -> Phase:
    """Return the draft phase implemented by the installed game engine."""
    if hasattr(Phase, "DRAFT"):
        return Phase.DRAFT
    return Phase.JOKER_DRAFT


def _is_draft_phase(phase: Phase) -> bool:
    return phase == _draft_phase()


class StellaEnv(EnvBase):
    """
    TorchRL environment wrapping the Stellatro game engine.

    Single-seat self-play: each episode controls one player, chosen randomly
    unless fixed via ``controlled_player``. Opponent turns are rolled internally.

    Episode = joker draft -> deterministic best-hand scoring -> game over.
    Actions are joker-pool indices in a fixed JOKER_POOL_SIZE-way categorical
    space. Invalid entries are masked when fewer jokers remain.
    An action_mask gates which slice is valid each step.

    Reward: 0 for all non-terminal steps; (my_score - opp_score) at terminal
    from the controlled seat's perspective.
    """

    def __init__(
        self,
        device: torch.device | str = "cpu",
        opponent_model: Optional[torch.nn.Module] = None,
        opponent_kind: str = "random",
        mixed_minimax_prob: float = 0.5,
        minimax_depth: int = 1,
        controlled_player: Optional[int] = None,
        invalid_action_reward: float = -1.0,
        seed: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(device=device, batch_size=torch.Size([]), **kwargs)

        # Specs
        self.observation_spec = Composite(
            observation=Unbounded(
                shape=(OBS_DIM,), device=self.device
            ),
            action_mask=Binary(
                n=ACTION_DIM, dtype=torch.bool, device=self.device
            ),
        )
        self.action_spec = Categorical(
            n=ACTION_DIM, device=self.device
        )
        self.reward_spec = Unbounded(
            shape=(1,), device=self.device
        )

        self._game: Optional[Game] = None
        self._fixed_controlled_player: Optional[int] = controlled_player
        self._controlled_player: Optional[int] = controlled_player
        self._invalid_action_reward = invalid_action_reward
        self._opponent_model: Optional[torch.nn.Module] = None
        self._opponent_kind = opponent_kind
        self._mixed_minimax_prob = mixed_minimax_prob
        self._minimax_depth = minimax_depth
        self._minimax_bot = None
        self._py_rng = random.Random()
        self._torch_rng = torch.Generator(device="cpu")
        self._seed: Optional[int] = None
        if opponent_model is not None:
            self.set_opponent_model(opponent_model)
        if seed is not None:
            self._set_seed(seed)

    def _current_player_num(self) -> int:
        if self._game.current_turn == PlayerTurn.PLAYER1:
            return 1
        return 2

    def set_opponent_model(self, opponent_model: Optional[torch.nn.Module]) -> None:
        if opponent_model is None:
            self._opponent_model = None
            return
        self._opponent_model = opponent_model.to(self.device)
        self._opponent_model.eval()

    def _obs_data(self) -> dict:
        """Return obs + action_mask entries for a TensorDict."""
        if self._controlled_player is None:
            raise RuntimeError("Controlled player is not set.")

        state_dict = self._game.encode_state(self._controlled_player)
        obs = _flatten_state(state_dict).to(self.device)
        mask = torch.zeros(ACTION_DIM, dtype=torch.bool, device=self.device)
        if _is_draft_phase(self._game.phase):
            n_remaining = len(self._game.jokers)
            mask[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n_remaining] = True
        return {"observation": obs, "action_mask": mask}

    def _reset(self, tensordict: TensorDictBase | None = None) -> TensorDict:
        if self._fixed_controlled_player is None:
            self._controlled_player = self._py_rng.choice((1, 2))
        else:
            self._controlled_player = self._fixed_controlled_player

        self._game = Game(verbose=False, rng=self._py_rng)
        self._game.start_round(rng=self._py_rng)
        self._roll_opponent_turns()
        return TensorDict(
            self._obs_data(),
            batch_size=self.batch_size,
            device=self.device,
        )

    def _make_step_td(self, reward: float, done: bool) -> TensorDict:
        """Build the TensorDict returned by _step (populates the 'next' sub-td)."""
        data = self._obs_data()
        data["reward"] = torch.tensor([reward], dtype=torch.float32, device=self.device)
        data["done"] = torch.tensor([done], dtype=torch.bool, device=self.device)
        data["terminated"] = torch.tensor([done], dtype=torch.bool, device=self.device)
        return TensorDict(data, batch_size=self.batch_size, device=self.device)

    def _opponent_action(self, player: int) -> int:
        """Return a unified action index (0..ACTION_DIM-1) for the opponent."""
        if _is_draft_phase(self._game.phase):
            n_valid = len(self._game.jokers)
            if n_valid == 0:
                raise RuntimeError("Opponent action requested with no jokers remaining.")
            offset = JOKER_DRAFT_OFFSET
        else:
            raise RuntimeError(f"Opponent action requested in unexpected phase: {self._game.phase}")

        kind = self._opponent_kind
        if kind == "mixed":
            kind = "minimax" if self._py_rng.random() < self._mixed_minimax_prob else "self"

        if kind == "minimax":
            return offset + self._minimax_pick()

        if kind == "random" or self._opponent_model is None:
            return offset + self._py_rng.randrange(n_valid)

        if kind != "self":
            raise ValueError(
                f"Unknown opponent_kind {self._opponent_kind!r}; expected random, self, minimax, or mixed."
            )

        state_dict = self._game.encode_state(player)
        obs = _flatten_state(state_dict).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits, _ = self._opponent_model(obs)
        logits = logits.squeeze(0).detach().float().cpu()
        masked = torch.full((ACTION_DIM,), float("-inf"))
        masked[offset : offset + n_valid] = logits[offset : offset + n_valid]
        return int(masked.argmax().item())

    def _minimax_pick(self) -> int:
        """Pick a draft joker using the same public MinimaxBot used in eval."""
        if self._minimax_bot is None:
            if str(_STARTER_ROOT) not in sys.path:
                sys.path.insert(0, str(_STARTER_ROOT))
            from bots.minimax_bot import MinimaxBot

            self._minimax_bot = MinimaxBot(max_depth=self._minimax_depth)
        return int(self._minimax_bot.pick_joker(self._game.get_game_state()))

    def _roll_opponent_turns(self) -> None:
        while (
            _is_draft_phase(self._game.phase)
            and self._game.current_turn is not None
            and self._current_player_num() != self._controlled_player
        ):
            player = self._current_player_num()
            raw = self._opponent_action(player)
            joker_idx = raw - JOKER_DRAFT_OFFSET
            success, _ = self._game.step(player, action=joker_idx)
            if not success:
                raise RuntimeError(f"Opponent made invalid action: {raw}")

    def _best_hand_score(self, player: int) -> float:
        hand = self._game.p1hand if player == 1 else self._game.p2hand
        jokers = self._game.p1jokers if player == 1 else self._game.p2jokers
        best = 0.0
        for combo in ALL_5_CARD_COMBOS:
            try:
                score = self._game.evaluate_hand(
                    [deepcopy(hand[index]) for index in combo],
                    deepcopy(jokers),
                )
                if score > best:
                    best = score
            except Exception:
                continue
        return best

    def _best_hand_indices(self, player: int) -> list[int]:
        hand = self._game.p1hand if player == 1 else self._game.p2hand
        jokers = self._game.p1jokers if player == 1 else self._game.p2jokers
        best_score = float("-inf")
        best_indices = list(ALL_5_CARD_COMBOS[0])

        for combo in ALL_5_CARD_COMBOS:
            try:
                score = self._game.evaluate_hand(
                    [deepcopy(hand[index]) for index in combo],
                    deepcopy(jokers),
                )
            except Exception:
                continue
            if score > best_score:
                best_score = score
                best_indices = list(combo)

        return best_indices

    def _play_deterministic_hands(self) -> None:
        while self._game.phase == Phase.PLAY and self._game.current_turn is not None:
            player = self._current_player_num()
            success, _ = self._game.step(
                player,
                hand_list=self._best_hand_indices(player),
            )
            if not success:
                raise RuntimeError(f"Deterministic play failed for player {player}.")

    def _terminal_reward(self) -> float:
        p1_score = self._game.player1_score
        p2_score = self._game.player2_score
        if self._controlled_player == 1:
            return math.tanh(float(p1_score - p2_score) / SCORE_SCALE)
        return math.tanh(float(p2_score - p1_score) / SCORE_SCALE)

    def _step(self, tensordict: TensorDictBase) -> TensorDict:
        raw_action = tensordict["action"]
        # Support both scalar (Categorical) and one-hot (OneHotCategorical) actions
        if raw_action.dim() > 0 and raw_action.shape[-1] > 1:
            action = int(raw_action.argmax(-1).item())
        else:
            action = int(raw_action.item())
        player = self._controlled_player

        if _is_draft_phase(self._game.phase):
            joker_idx = action - JOKER_DRAFT_OFFSET
            success, _ = self._game.step(player, action=joker_idx)
        else:
            success = False

        if not success:
            return self._make_step_td(reward=self._invalid_action_reward, done=True)

        if self._game.phase == Phase.PLAY:
            self._play_deterministic_hands()

        self._roll_opponent_turns()
        if self._game.phase == Phase.PLAY:
            self._play_deterministic_hands()

        if self._game.phase == Phase.OVER:
            return self._make_step_td(reward=self._terminal_reward(), done=True)

        return self._make_step_td(reward=0.0, done=False)

    def _set_seed(self, seed: Optional[int]) -> None:
        if seed is not None:
            self._seed = seed
            self._py_rng.seed(seed)
            self._torch_rng.manual_seed(seed)
            random.seed(seed)
            torch.manual_seed(seed)
