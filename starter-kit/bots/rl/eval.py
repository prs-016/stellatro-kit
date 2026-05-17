from __future__ import annotations

import random
import sys
from copy import deepcopy
from pathlib import Path

import chz
import numpy as np
import torch

from config import EvalConfig
from stellatro_game import Game, Phase, PlayerTurn, ALL_5_CARD_COMBOS, PLAYER_CARDS
from model import build_model, ensure_supported_model_type, JOKER_DRAFT_OFFSET, ACTION_DIM
from env import _flatten_state

_RL_DIR = Path(__file__).resolve().parent
_STARTER_ROOT = _RL_DIR.parents[1]
for _p in (_RL_DIR, _STARTER_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _draft_phase() -> Phase:
    if hasattr(Phase, "DRAFT"):
        return Phase.DRAFT
    return Phase.JOKER_DRAFT


def _is_draft_phase(phase: Phase) -> bool:
    return phase == _draft_phase()


# ---------------------------------------------------------------------------
# Opponent strategies
# ---------------------------------------------------------------------------

def random_pick(game: Game, player: int) -> int:
    """Pick a random valid joker-draft action."""
    return JOKER_DRAFT_OFFSET + random.randint(0, len(game.jokers) - 1)


def model_pick(
    game: Game,
    player: int,
    model: torch.nn.Module,
    device: torch.device,
) -> int:
    """Pick a joker-draft action via model."""
    state_dict = game.encode_state(player=player)
    obs = _flatten_state(state_dict).unsqueeze(0).to(device)

    with torch.no_grad():
        logits, _ = model(obs)
    logits = logits.squeeze(0)

    masked = torch.full((ACTION_DIM,), float("-inf"))
    n = len(game.jokers)
    masked[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n] = logits[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n]
    return int(masked.argmax().item())


def minimax_pick(game: Game, player: int, minimax_bot) -> int:
    """Pick a joker-draft action via minimax using the public GameState API."""
    state = game.get_game_state()
    joker_idx = minimax_bot.pick_joker(state)
    return JOKER_DRAFT_OFFSET + int(joker_idx)


def best_hand_indices(game: Game, player: int) -> list[int]:
    hand = game.p1hand if player == 1 else game.p2hand
    jokers = game.p1jokers if player == 1 else game.p2jokers
    best_score = float("-inf")
    best_indices = list(ALL_5_CARD_COMBOS[0])

    for combo in ALL_5_CARD_COMBOS:
        try:
            score = game.evaluate_hand(
                [deepcopy(hand[index]) for index in combo],
                deepcopy(jokers),
            )
        except Exception:
            continue
        if score > best_score:
            best_score = score
            best_indices = list(combo)

    return best_indices


# ---------------------------------------------------------------------------
# Run a single game
# ---------------------------------------------------------------------------

def play_game(
    model: torch.nn.Module,
    opponent_fn,
    device: torch.device,
    controlled_player: int,
    verbose: bool = False,
    opponent_bot=None,
    controlled_draft_fn=None,
) -> dict:
    """Play one full game from the controlled seat.

    opponent_bot:        if provided (e.g. MinimaxBot), its pick_hand() is called
                         for the opponent's play phase, exercising the public API.
    controlled_draft_fn: optional callable (game, player) -> int (raw action with
                         JOKER_DRAFT_OFFSET) for the controlled player's draft pick.
                         When None the raw model logits are used directly.
    """
    game = Game(verbose=verbose)
    game.start_round()

    while game.phase != Phase.OVER:
        player = 1 if game.current_turn == PlayerTurn.PLAYER1 else 2

        if game.phase == Phase.PLAY:
            state = game.get_game_state()
            if opponent_bot is not None and player != controlled_player:
                # Use opponent bot's pick_hand — exercises the public contract
                hand = list(opponent_bot.pick_hand(state))
            else:
                hand = best_hand_indices(game, player)
            success, _ = game.step(player, hand_list=hand)
            if not success:
                role = "Opponent" if player != controlled_player else "Model"
                raise RuntimeError(f"{role} made invalid play: {hand}")
            continue

        # Draft phase
        if player == controlled_player:
            if controlled_draft_fn is not None:
                raw = controlled_draft_fn(game, player)
            else:
                raw = model_pick(game, player, model, device)
        else:
            raw = opponent_fn(game, player)

        success, _ = game.step(player, action=raw - JOKER_DRAFT_OFFSET)
        if not success:
            role = "Model" if player == controlled_player else "Opponent"
            raise RuntimeError(f"{role} made invalid draft action: {raw}")

    p1_score = game.player1_score
    p2_score = game.player2_score
    model_score = p1_score if controlled_player == 1 else p2_score
    opponent_score = p2_score if controlled_player == 1 else p1_score

    return {
        "model_player": controlled_player,
        "p1_score": p1_score,
        "p2_score": p2_score,
        "model_score": model_score,
        "opponent_score": opponent_score,
        "model_win": int(model_score > opponent_score),
        "opponent_win": int(opponent_score > model_score),
        "draw": int(model_score == opponent_score),
        "score_diff": model_score - opponent_score,
    }


# ---------------------------------------------------------------------------
# Self-play evaluation
# ---------------------------------------------------------------------------

def play_game_self(
    model: torch.nn.Module,
    device: torch.device,
    controlled_player: int,
    verbose: bool = False,
) -> dict:
    """Both players use the model; metrics are reported from the controlled seat."""
    return play_game(
        model,
        opponent_fn=lambda game, player: model_pick(game, player, model, device),
        device=device,
        controlled_player=controlled_player,
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# Contract validation
# ---------------------------------------------------------------------------

def _validate_rl_contracts(checkpoint_path: str) -> None:
    """Verify that RLBot (public API) returns contract-compliant values."""
    from rl_bot import RLBot

    print("\nValidating RL bot contract compliance...")
    rl_bot = RLBot(checkpoint_path=checkpoint_path, device="cpu")

    game = Game(verbose=False)
    game.start_round()

    # --- Draft phase contract ---
    state = game.get_game_state()
    joker_idx = rl_bot.pick_joker(state)
    assert isinstance(joker_idx, int), f"pick_joker must return int, got {type(joker_idx)}"
    assert 0 <= joker_idx < len(state.joker_pool), (
        f"pick_joker out of range: {joker_idx}, pool size {len(state.joker_pool)}"
    )
    print(f"  pick_joker -> {joker_idx}  (pool size {len(state.joker_pool)})  OK")

    # Play through the full draft
    while game.phase == _draft_phase():
        player = 1 if game.current_turn == PlayerTurn.PLAYER1 else 2
        s = game.get_game_state()
        ok, _ = game.step(player, action=rl_bot.pick_joker(s))
        if not ok:
            raise RuntimeError("pick_joker returned an invalid index mid-draft")

    # --- Play phase contract ---
    state = game.get_game_state()
    hand_indices = rl_bot.pick_hand(state)
    assert isinstance(hand_indices, list), f"pick_hand must return list, got {type(hand_indices)}"
    assert len(hand_indices) == 5, f"pick_hand must return 5 indices, got {len(hand_indices)}"
    assert len(set(hand_indices)) == 5, f"pick_hand must return distinct indices: {hand_indices}"
    if state.current_turn == PlayerTurn.PLAYER1:
        hand_size = len(state.player1_hand)
    else:
        hand_size = len(state.player2_hand)
    valid_count = min(PLAYER_CARDS, hand_size)
    assert all(0 <= i < valid_count for i in hand_indices), (
        f"pick_hand out of range: {hand_indices}  (valid 0..{valid_count-1})"
    )
    print(f"  pick_hand  -> {hand_indices}  (hand size {valid_count})  OK")
    print("Contract validation passed.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def evaluate(cfg: EvalConfig) -> None:
    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)

    device = torch.device("cpu")

    # Load checkpoint
    ckpt = torch.load(cfg.checkpoint_path, map_location=device, weights_only=True)
    model_cfg = ckpt["config"]
    ensure_supported_model_type(model_cfg["model_type"])
    model = build_model(
        model_type=model_cfg["model_type"],
        embed_dim=model_cfg["embed_dim"],
        hidden_dim=model_cfg["hidden_dim"],
        num_layers=model_cfg["num_layers"],
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    model.to(device)

    print(f"Loaded model from {cfg.checkpoint_path} "
          f"(trained {ckpt.get('total_frames', '?')} frames)")
    print(f"Evaluating {cfg.num_games} games vs {cfg.opponent}")
    print(
        "Controlled policy: "
        f"{'public RLBot' if cfg.use_public_bot else 'raw checkpoint logits'}"
        f"{' + minimax teacher' if cfg.use_public_bot and cfg.use_minimax_teacher else ''}"
    )

    # Contract validation (always runs when a checkpoint is loaded)
    _validate_rl_contracts(cfg.checkpoint_path)

    # Select opponent
    opponent_bot = None
    if cfg.opponent == "random":
        opponent_fn = random_pick
    elif cfg.opponent == "self":
        opponent_fn = None  # handled separately
    elif cfg.opponent == "minimax":
        from bots.minimax_bot import MinimaxBot
        opponent_bot = MinimaxBot()
        opponent_fn = lambda game, player: minimax_pick(game, player, opponent_bot)
    else:
        raise ValueError(f"Unknown opponent: {cfg.opponent!r}  (choices: random, self, minimax)")

    controlled_draft_fn = None
    if cfg.use_public_bot:
        from rl_bot import RLBot

        if cfg.use_minimax_teacher:
            from bots.minimax_bot import MinimaxBot as _TeacherBot
            _teacher = _TeacherBot()
            controlled_draft_fn = lambda game, player: minimax_pick(game, player, _teacher)
        else:
            _controlled_bot = RLBot(checkpoint_path=cfg.checkpoint_path, device="cpu")
            controlled_draft_fn = (
                lambda game, player: JOKER_DRAFT_OFFSET + int(_controlled_bot.pick_joker(game.get_game_state()))
            )

    seat_counts = {1: 0, 2: 0}
    results = []
    for i in range(cfg.num_games):
        controlled_player = random.choice((1, 2))
        seat_counts[controlled_player] += 1
        if cfg.opponent == "self":
            result = play_game_self(
                model,
                device,
                controlled_player=controlled_player,
                verbose=cfg.verbose,
            )
        else:
            result = play_game(
                model,
                opponent_fn,
                device,
                controlled_player=controlled_player,
                verbose=cfg.verbose,
                opponent_bot=opponent_bot,
                controlled_draft_fn=controlled_draft_fn,
            )
        results.append(result)

        if cfg.verbose:
            print(
                f"  Game {i+1:3d}: seat=P{result['model_player']} "
                f"model={result['model_score']:8.0f} opp={result['opponent_score']:8.0f} "
                f"diff={result['score_diff']:+.0f}  "
                f"{'WIN' if result['model_win'] else 'LOSS' if result['opponent_win'] else 'DRAW'}"
            )

    # Aggregate
    wins = sum(r["model_win"] for r in results)
    losses = sum(r["opponent_win"] for r in results)
    draws = sum(r["draw"] for r in results)
    avg_diff = np.mean([r["score_diff"] for r in results])
    avg_model = np.mean([r["model_score"] for r in results])
    avg_opp = np.mean([r["opponent_score"] for r in results])

    print(f"\n{'='*50}")
    print(f"Results ({cfg.num_games} games vs {cfg.opponent}):")
    print(f"  Seat split:      P1={seat_counts[1]} P2={seat_counts[2]}")
    print(f"  Win rate:       {wins}/{cfg.num_games} ({100*wins/cfg.num_games:.1f}%)")
    print(f"  Loss rate:      {losses}/{cfg.num_games} ({100*losses/cfg.num_games:.1f}%)")
    print(f"  Draw rate:      {draws}/{cfg.num_games} ({100*draws/cfg.num_games:.1f}%)")
    print(f"  Avg score diff: {avg_diff:+.1f}")
    print(f"  Avg model score:  {avg_model:.1f}")
    print(f"  Avg opp score:    {avg_opp:.1f}")
    print(f"{'='*50}")


if __name__ == "__main__":
    chz.entrypoint(evaluate)
