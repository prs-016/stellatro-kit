import argparse
import csv
import importlib
import importlib.util
import inspect
import random
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from stellatro_game import Game, Phase, PlayerTurn


BOT_ALIASES = {
    "minimax": "bots.minimax_bot:MinimaxBot",
    "random": "bots.random_bot:RandomBot",
    "greedy": "bots.greedy_bot:GreedyBot",
}


RANK_TO_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}


def format_card(card) -> str:
    rank = RANK_TO_STR.get(card.rank, str(card.rank))
    suits = "+".join(card.suits) if card.suits else "?"
    return f"{rank}-{suits}"


_BOT_CLASS_CACHE: dict[str, Any] = {}


def resolve_bot_class(bot_name: str):
    if bot_name in _BOT_CLASS_CACHE:
        return _BOT_CLASS_CACHE[bot_name]

    target = BOT_ALIASES.get(bot_name.lower(), bot_name)
    if ":" in target:
        module_ref, class_name = target.split(":", 1)
    else:
        module_ref, class_name = target, "Bot"

    if module_ref.endswith(".py") or "/" in module_ref or "\\" in module_ref:
        path = Path(module_ref)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"Bot file not found: {path}")
        spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load bot module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(module_ref)

    bot_cls = getattr(module, class_name)
    _BOT_CLASS_CACHE[bot_name] = bot_cls
    return bot_cls


def instantiate_bot(bot_name: str, max_depth: int | None):
    bot_cls = resolve_bot_class(bot_name)
    kwargs: dict[str, Any] = {}

    if max_depth is not None:
        signature = inspect.signature(bot_cls)
        if "max_depth" in signature.parameters:
            kwargs["max_depth"] = max_depth

    return bot_cls(**kwargs)


def play_single_game(
    player1_name: str,
    player2_name: str,
    seed: int,
    joker_pool_size: int,
    player1_max_depth: int | None,
    player2_max_depth: int | None,
) -> dict[str, Any]:
    game = Game(verbose=False)
    game.start_round(rng=random.Random(seed))
    game.jokers = game.jokers[:joker_pool_size]
    initial_pool_snapshot = [j.name for j in game.jokers]

    player1 = instantiate_bot(player1_name, player1_max_depth)
    player2 = instantiate_bot(player2_name, player2_max_depth)

    while game.phase == Phase.DRAFT:
        state = game.get_game_state()
        if state.current_turn == PlayerTurn.PLAYER1:
            action = player1.pick_joker(state)
            ok, _ = game.step(1, action=action)
        else:
            action = player2.pick_joker(state)
            ok, _ = game.step(2, action=action)

        if not ok:
            raise RuntimeError("Draft move was rejected.")

    state = game.get_game_state()
    seat1_hand_snapshot = [format_card(c) for c in state.player1_hand]
    seat2_hand_snapshot = [format_card(c) for c in state.player2_hand]

    p1_hand_list = player1.pick_hand(state)
    p1_played = [state.player1_hand[i] for i in p1_hand_list]
    ok, _ = game.step(1, hand_list=p1_hand_list)
    if not ok:
        raise RuntimeError("Player 1 play move was rejected.")

    state = game.get_game_state()
    p2_hand_list = player2.pick_hand(state)
    p2_played = [state.player2_hand[i] for i in p2_hand_list]
    ok, final_state = game.step(2, hand_list=p2_hand_list)
    if not ok:
        raise RuntimeError("Player 2 play move was rejected.")

    if final_state.phase != Phase.OVER:
        raise RuntimeError("Game did not end after both players played.")

    return {
        "player1_score": final_state.player1_score,
        "player2_score": final_state.player2_score,
        "player1_jokers": final_state.player1_jokers,
        "player2_jokers": final_state.player2_jokers,
        "player1_played": p1_played,
        "player2_played": p2_played,
        "seat1_hand": seat1_hand_snapshot,
        "seat2_hand": seat2_hand_snapshot,
        "initial_pool": initial_pool_snapshot,
    }


def _winner_label(p1_score: float, p2_score: float) -> str:
    if p1_score > p2_score:
        return "player1"
    if p2_score > p1_score:
        return "player2"
    return "tie"


def _log_completion(
    game_result: dict[str, Any],
    completed_count: int,
    total: int,
    results: dict[str, int],
) -> None:
    p1_score = game_result["player1_score"]
    p2_score = game_result["player2_score"]
    winner = _winner_label(p1_score, p2_score)
    if winner == "player1":
        results["player1_wins"] += 1
    elif winner == "player2":
        results["player2_wins"] += 1
    else:
        results["ties"] += 1
    print(
        f"[{completed_count}/{total}] round={game_result['round_number']} "
        f"seed={game_result['seed']} p1={p1_score} p2={p2_score} winner={winner}"
    )


def _run_game_job(job: dict[str, Any]) -> dict[str, Any]:
    result = play_single_game(
        job["player1"],
        job["player2"],
        job["seed"],
        job["joker_pool_size"],
        job["player1_max_depth"],
        job["player2_max_depth"],
    )
    result["round_number"] = job["round_number"]
    result["seed"] = job["seed"]
    result["player1"] = job["player1"]
    result["player2"] = job["player2"]
    result["mirror"] = job["mirror"]
    result["player1_jokers"] = [j.name for j in result["player1_jokers"]]
    result["player2_jokers"] = [j.name for j in result["player2_jokers"]]
    result["player1_played"] = [format_card(c) for c in result["player1_played"]]
    result["player2_played"] = [format_card(c) for c in result["player2_played"]]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local bot-vs-bot Stellatro match.")
    parser.add_argument("player1", nargs="?", help="Player 1 bot alias or import path like bots.minimax_bot:MinimaxBot")
    parser.add_argument("player2", nargs="?", help="Player 2 bot alias or import path like bots.random_bot:RandomBot")
    parser.add_argument("--rounds", type=int, default=10, help="Number of games to run")
    parser.add_argument("--seed-base", type=int, default=100, help="Starting seed for the match series")
    parser.add_argument("--joker-pool-size", type=int, default=10, help="Number of jokers to keep in the draft pool")
    parser.add_argument("--player1-max-depth", type=int, default=None, help="Optional max_depth for player 1 if supported")
    parser.add_argument("--player2-max-depth", type=int, default=None, help="Optional max_depth for player 2 if supported")
    parser.add_argument("--list-bots", action="store_true", help="Print built-in bot aliases and exit")
    parser.add_argument("--csv", type=Path, default=None, help="Optional path to write per-game results as CSV")
    parser.add_argument(
        "--csv-append",
        action="store_true",
        help="Append to the CSV file if it exists instead of overwriting it. The header is only written when the file is new or empty.",
    )
    parser.add_argument("--jobs", type=int, default=5, help="Number of parallel worker processes (set 1 to run serially)")
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Replay each seed with seats swapped to neutralise first-pick bias; results aggregated by bot identity.",
    )
    args = parser.parse_args()

    if args.list_bots:
        for alias, target in sorted(BOT_ALIASES.items()):
            print(f"{alias}: {target}")
        return
    if args.player1 is None or args.player2 is None:
        parser.error("player1 and player2 are required unless --list-bots is used")

    player1 = args.player1 or args.p1_pos
    player2 = args.player2 or args.p2_pos

    if not player1 or not player2:
        parser.error("Both player1 and player2 must be specified (either as positional arguments or via --player1/--player2).")

    results = {"player1_wins": 0, "player2_wins": 0, "ties": 0}

    jobs: list[dict[str, Any]] = []
    round_number = 0
    for seed in range(args.seed_base, args.seed_base + args.rounds):
        round_number += 1
        jobs.append({
            "round_number": round_number,
            "seed": seed,
            "player1": player1,
            "player2": player2,
            "joker_pool_size": args.joker_pool_size,
            "player1_max_depth": args.player1_max_depth,
            "player2_max_depth": args.player2_max_depth,
            "mirror": False,
        })
        if args.mirror:
            round_number += 1
            jobs.append({
                "round_number": round_number,
                "seed": seed,
                "player1": player2,
                "player2": player1,
                "joker_pool_size": args.joker_pool_size,
                "player1_max_depth": args.player2_max_depth,
                "player2_max_depth": args.player1_max_depth,
                "mirror": True,
            })

    completed: list[dict[str, Any]] = []
    workers = max(1, min(args.jobs, len(jobs)))

    if workers == 1:
        for job in jobs:
            completed.append(_run_game_job(job))
            _log_completion(completed[-1], len(completed), len(jobs), results)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_run_game_job, job): job for job in jobs}
            for future in as_completed(futures):
                game_result = future.result()
                completed.append(game_result)
                _log_completion(game_result, len(completed), len(jobs), results)

    completed.sort(key=lambda r: r["round_number"])

    if args.mirror:
        _verify_mirror_pairs(completed)

    if args.csv is not None:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        append_mode = args.csv_append and args.csv.exists() and args.csv.stat().st_size > 0
        open_mode = "a" if append_mode else "w"
        with args.csv.open(open_mode, newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            if not append_mode:
                csv_writer.writerow(
                    [
                        "round",
                        "seed",
                        "player1",
                        "player2",
                        "player1_score",
                        "player2_score",
                        "winner",
                        "player1_jokers",
                        "player2_jokers",
                        "player1_played_hand",
                        "player2_played_hand",
                        "mirror",
                    ]
                )
            for r in completed:
                csv_writer.writerow(
                    [
                        r["round_number"],
                        r["seed"],
                        r["player1"],
                        r["player2"],
                        r["player1_score"],
                        r["player2_score"],
                        _winner_label(r["player1_score"], r["player2_score"]),
                        "; ".join(r["player1_jokers"]),
                        "; ".join(r["player2_jokers"]),
                        "; ".join(r["player1_played"]),
                        "; ".join(r["player2_played"]),
                        int(r["mirror"]),
                    ]
                )

    print(
        "By seat: "
        f"player1={results['player1_wins']} "
        f"player2={results['player2_wins']} "
        f"ties={results['ties']}"
    )

    if args.mirror:
        bot_wins: dict[str, int] = defaultdict(int)
        bot_ties = 0
        for r in completed:
            winner = _winner_label(r["player1_score"], r["player2_score"])
            if winner == "player1":
                bot_wins[r["player1"]] += 1
            elif winner == "player2":
                bot_wins[r["player2"]] += 1
            else:
                bot_ties += 1
        a, b = args.player1, args.player2
        total = bot_wins[a] + bot_wins[b] + bot_ties
        print(
            f"By bot:  {a}={bot_wins[a]} ({bot_wins[a]/total:.1%})  "
            f"{b}={bot_wins[b]} ({bot_wins[b]/total:.1%})  ties={bot_ties}"
        )

    if args.csv is not None:
        action = "appended to" if args.csv_append else "written to"
        print(f"Per-game results {action} {args.csv}")


def _verify_mirror_pairs(completed: list[dict[str, Any]]) -> None:
    by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in completed:
        by_seed[r["seed"]].append(r)
    for seed, pair in by_seed.items():
        if len(pair) != 2:
            continue
        try:
            orig = next(p for p in pair if not p["mirror"])
            mirror = next(p for p in pair if p["mirror"])
        except StopIteration:
            continue
        if orig["initial_pool"] != mirror["initial_pool"]:
            print(f"WARNING seed={seed}: joker pool diverged between original and mirror")
        if orig["seat1_hand"] != mirror["seat1_hand"]:
            print(f"WARNING seed={seed}: seat-1 hand diverged between original and mirror")
        if orig["seat2_hand"] != mirror["seat2_hand"]:
            print(f"WARNING seed={seed}: seat-2 hand diverged between original and mirror")


if __name__ == "__main__":
    main()
