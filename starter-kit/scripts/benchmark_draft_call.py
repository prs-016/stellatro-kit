import argparse
import importlib
import importlib.util
import inspect
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (
    SCRIPT_DIR,
    STARTER_ROOT,
    REPO_ROOT / "stellatro-common",
    REPO_ROOT / "stellatro-game",
):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import stellatro_game
import stellatro_game.game as game_module
from run_bot_match import BOT_ALIASES
from stellatro_game import Game, Phase


def _set_draft_joker_target(draft_joker_target: int | None) -> None:
    if draft_joker_target is None:
        return
    stellatro_game.JOKER_HAND_SIZE = draft_joker_target
    game_module.JOKER_HAND_SIZE = draft_joker_target


def _current_draft_joker_target() -> int:
    return int(game_module.JOKER_HAND_SIZE)


def _load_bot_class(target: str):
    candidate_path = Path(target)
    if candidate_path.exists():
        module_name = f"benchmark_bot_{candidate_path.stem.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, candidate_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not load module from '{target}'.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        if hasattr(module, "Bot") and inspect.isclass(module.Bot):
            return module.Bot

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj.__module__ == module.__name__
                and hasattr(obj, "pick_joker")
                and callable(getattr(obj, "pick_joker"))
                and hasattr(obj, "pick_hand")
                and callable(getattr(obj, "pick_hand"))
            ):
                return obj

        raise RuntimeError(
            f"No bot class with pick_joker/pick_hand found in '{target}'."
        )

    resolved = BOT_ALIASES.get(target.lower(), target)
    if ":" in resolved:
        module_name, class_name = resolved.split(":", 1)
    else:
        module_name, class_name = resolved, "Bot"

    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def _instantiate_bot(target: str, max_depth: int | None):
    bot_cls = _load_bot_class(target)
    kwargs: dict[str, Any] = {}

    if max_depth is not None:
        signature = inspect.signature(bot_cls)
        if "max_depth" in signature.parameters:
            kwargs["max_depth"] = max_depth

    return bot_cls(**kwargs)


def _random_draft_state(
    seed: int,
    joker_pool_size: int | None,
    draft_steps: int | None,
):
    rng = random.Random(seed)
    game = Game(verbose=False)
    game.start_round(rng=rng)

    if joker_pool_size is not None:
        game.jokers = game.jokers[:joker_pool_size]

    max_steps_before_call = max(0, (2 * _current_draft_joker_target()) - 1)
    steps_to_play = draft_steps
    if steps_to_play is None:
        steps_to_play = rng.randrange(max_steps_before_call + 1)

    for _ in range(min(steps_to_play, max_steps_before_call)):
        if game.phase != Phase.DRAFT or not game.jokers:
            break
        action = rng.randrange(len(game.jokers))
        player = 1 if game.current_turn.name == "PLAYER1" else 2
        ok, _ = game.step(player, action=action)
        if not ok:
            raise RuntimeError("Failed to build a random draft state.")

    if game.phase != Phase.DRAFT:
        raise RuntimeError("Randomized game state is no longer in the draft phase.")

    return game.get_game_state()


def benchmark_draft_call(
    bot_target: str,
    trials: int = 20,
    seed_base: int = 100,
    joker_pool_size: int | None = None,
    max_depth: int | None = None,
    draft_steps: int | None = None,
    fresh_bot_per_trial: bool = False,
    draft_joker_target: int | None = None,
) -> dict[str, Any]:
    if trials <= 0:
        raise ValueError("trials must be positive.")

    _set_draft_joker_target(draft_joker_target)

    times: list[float] = []
    picks: list[int] = []
    state_summaries: list[str] = []

    shared_bot = None if fresh_bot_per_trial else _instantiate_bot(bot_target, max_depth)

    for offset in range(trials):
        seed = seed_base + offset
        state = _random_draft_state(
            seed=seed,
            joker_pool_size=joker_pool_size,
            draft_steps=draft_steps,
        )
        bot = shared_bot or _instantiate_bot(bot_target, max_depth)

        start = time.perf_counter()
        pick = bot.pick_joker(state)
        elapsed = time.perf_counter() - start

        if not isinstance(pick, int) or isinstance(pick, bool):
            raise RuntimeError(f"Bot returned a non-integer draft action: {pick!r}")
        if pick < 0 or pick >= len(state.joker_pool):
            raise RuntimeError(
                f"Bot returned invalid draft index {pick} for pool size {len(state.joker_pool)}."
            )

        times.append(elapsed)
        picks.append(pick)
        state_summaries.append(
            "seed={seed} turn={turn} pool={pool} p1={p1} p2={p2} pick={pick}".format(
                seed=seed,
                turn=state.current_turn.name if state.current_turn else "NONE",
                pool=len(state.joker_pool),
                p1=len(state.player1_jokers),
                p2=len(state.player2_jokers),
                pick=pick,
            )
        )

    sorted_times = sorted(times)
    average_time = sum(times) / len(times)
    median_time = statistics.median(times)
    p95_index = min(len(sorted_times) - 1, max(0, int(len(sorted_times) * 0.95) - 1))

    return {
        "bot_target": bot_target,
        "trials": trials,
        "seed_base": seed_base,
        "joker_pool_size": joker_pool_size,
        "draft_joker_target": _current_draft_joker_target(),
        "draft_steps": draft_steps,
        "fresh_bot_per_trial": fresh_bot_per_trial,
        "times": times,
        "picks": picks,
        "state_summaries": state_summaries,
        "min_time": min(times),
        "max_time": max(times),
        "average_time": average_time,
        "median_time": median_time,
        "p95_time": sorted_times[p95_index],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a bot's draft move time on random draft-phase GameState values."
    )
    parser.add_argument(
        "bot",
        help=(
            "Bot alias/import path, or a direct .py file path like "
            "starter-kit/bots/greedy_bot.py"
        ),
    )
    parser.add_argument("--trials", type=int, default=20, help="Number of draft calls to time.")
    parser.add_argument("--seed-base", type=int, default=100, help="Starting RNG seed.")
    parser.add_argument(
        "--joker-pool-size",
        type=int,
        default=None,
        help="Optional cap on the generated joker pool before timing.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Optional max_depth passed to bots that accept it.",
    )
    parser.add_argument(
        "--draft-steps",
        type=int,
        default=None,
        help="Optional number of random draft picks to apply before timing the call.",
    )
    parser.add_argument(
        "--draft-joker-target",
        type=int,
        default=None,
        help="Optional override for the number of jokers each player drafts before play.",
    )
    parser.add_argument(
        "--fresh-bot-per-trial",
        action="store_true",
        help="Instantiate a new bot on every trial instead of reusing one instance.",
    )
    args = parser.parse_args()

    summary = benchmark_draft_call(
        bot_target=args.bot,
        trials=args.trials,
        seed_base=args.seed_base,
        joker_pool_size=args.joker_pool_size,
        max_depth=args.max_depth,
        draft_steps=args.draft_steps,
        fresh_bot_per_trial=args.fresh_bot_per_trial,
        draft_joker_target=args.draft_joker_target,
    )

    print(
        f"Draft timing for {summary['bot_target']}: "
        f"trials={summary['trials']} "
        f"draft_target={summary['draft_joker_target']} "
        f"avg={summary['average_time'] * 1000:.3f}ms "
        f"median={summary['median_time'] * 1000:.3f}ms "
        f"p95={summary['p95_time'] * 1000:.3f}ms "
        f"min={summary['min_time'] * 1000:.3f}ms "
        f"max={summary['max_time'] * 1000:.3f}ms"
    )
    print("Sample states:")
    for line in summary["state_summaries"][: min(5, len(summary["state_summaries"]))]:
        print(f"  {line}")


if __name__ == "__main__":
    main()
