import argparse
import random
import sys
from pathlib import Path
from typing import Any

# Ensure workspace paths are available
SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from stellatro_game import Game, GameSetup, Phase, PlayerTurn
from scripts.run_bot_match import resolve_bot_class


def instantiate_bot(bot_ref: str) -> Any:
    cls = resolve_bot_class(bot_ref)
    return cls()


def play_variant(bot1, bot2, setup: GameSetup, swap_hands: bool) -> tuple[int, int]:
    """
    Play a single game variant.
    bot1: is Player 1 (drafts first)
    bot2: is Player 2
    """
    game = Game(verbose=False)
    game.load_setup(setup, swap_hands=swap_hands)

    # Draft phase
    while game.phase == Phase.DRAFT:
        state = game.get_game_state()
        if state.current_turn == PlayerTurn.PLAYER1:
            action = bot1.pick_joker(state)
            ok, _ = game.step(1, action=action)
        else:
            action = bot2.pick_joker(state)
            ok, _ = game.step(2, action=action)
        if not ok:
            raise RuntimeError("Draft action rejected")

    # Play phase
    state = game.get_game_state()
    p1_hand_list = bot1.pick_hand(state)
    ok, _ = game.step(1, hand_list=p1_hand_list)
    if not ok:
        raise RuntimeError("Player 1 play rejected")

    state = game.get_game_state()
    p2_hand_list = bot2.pick_hand(state)
    ok, final_state = game.step(2, hand_list=p2_hand_list)
    if not ok:
        raise RuntimeError("Player 2 play rejected")

    return final_state.player1_score, final_state.player2_score


def resolve_bot_path(bot_ref: str) -> str:
    aliases = {
        "greedy": "starter-kit/bots/greedy_bot.py",
        "minimax": "starter-kit/bots/minimax_bot.py",
        "random": "starter-kit/bots/random_bot.py"
    }
    if bot_ref in aliases:
        return str(STARTER_ROOT / aliases[bot_ref].replace("starter-kit/", ""))
    p = Path(bot_ref)
    if p.exists():
        return str(p.resolve())
    p_starter = STARTER_ROOT / bot_ref.replace("starter-kit/", "")
    if p_starter.exists():
        return str(p_starter.resolve())
    return bot_ref


def play_variant_gui(bot1_ref: str, bot2_ref: str, seed: int, swap_hands: bool) -> tuple[int, int]:
    """
    Launch the GUI for a single game variant and return final scores.
    """
    import subprocess
    temp_score_file = STARTER_ROOT / "gui" / "temp_score.txt"
    if temp_score_file.exists():
        temp_score_file.unlink()

    bot1_path = resolve_bot_path(bot1_ref)
    bot2_path = resolve_bot_path(bot2_ref)

    cmd = [
        sys.executable,
        str(STARTER_ROOT / "gui" / "gui.py"),
        "--p1", bot1_path,
        "--p2", bot2_path,
        "--seed", str(seed),
        "--score_file", str(temp_score_file)
    ]
    if swap_hands:
        cmd.append("--swap_hands")

    print(f"    🖥️  Launching Pygame GUI... [Seed={seed}, Swap={swap_hands}]")
    print(f"       👉 Close the GUI window after the game is completed to record scores and continue.")

    subprocess.run(cmd)

    p1_score, p2_score = 0, 0
    if temp_score_file.exists():
        try:
            with open(temp_score_file, "r") as f:
                content = f.read().strip()
                if "," in content:
                    p1_str, p2_str = content.split(",")
                    p1_score = float(p1_str)
                    p2_score = float(p2_str)
        except Exception as e:
            print(f"    ⚠️ Warning: Error reading temp score file: {e}")
        finally:
            try:
                temp_score_file.unlink()
            except Exception:
                pass
    else:
        print("    ⚠️ Warning: GUI window closed before the game finished. Score recorded as 0.")

    return p1_score, p2_score


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate an official Stellatro tournament matchup (sets of 4 mirrored games)."
    )
    parser.add_argument("bot_a", help="First bot alias (random, greedy, minimax) or path to bot file")
    parser.add_argument("bot_b", help="Second bot alias or path to bot file")
    parser.add_argument("--rounds", type=int, default=5, help="Number of distinct deals/sets to play")
    parser.add_argument("--seed-base", type=int, default=100, help="Starting RNG seed")
    parser.add_argument("--joker-pool-size", type=int, default=15, help="Official size is 15")
    parser.add_argument("--gui", action="store_true", help="Launch the GUI for each game in the simulation")
    parser.add_argument("--random-seeds", action="store_true", help="Use completely random seeds instead of sequential ones")
    args = parser.parse_args()

    print("=" * 70)
    print(f"🏆 SIMULATING TOURNAMENT MATCHUP: {args.bot_a} vs {args.bot_b}")
    print(f"Rounds (Sets): {args.rounds} (Total Games: {args.rounds * 4})")
    print("=" * 70)

    # Instantiate bots
    bot_a = instantiate_bot(args.bot_a)
    bot_b = instantiate_bot(args.bot_b)

    tournament_points_a = 0
    tournament_points_b = 0

    wins_a = 0
    wins_b = 0
    ties = 0

    sum_scores_a = 0
    sum_scores_b = 0

    for round_idx in range(args.rounds):
        if args.random_seeds:
            seed = random.randint(100000, 999999)
        else:
            seed = args.seed_base + round_idx
        rng = random.Random(seed)

        # Generate a distinct cards deal and joker pool
        setup = GameSetup.generate(rng=rng)
        # Cap the joker pool to the configured size
        setup.joker_pool = setup.joker_pool[:args.joker_pool_size]

        is_last_round = (round_idx == args.rounds - 1)
        use_gui = args.gui and is_last_round

        if use_gui:
            print(f"\n📺 [Set {round_idx + 1}/{args.rounds}] Seed={seed} (SPECTATING IN GUI)...")
        else:
            print(f"\n⚡ [Set {round_idx + 1}/{args.rounds}] Seed={seed} (Simulating headlessly)...")

        # Variant 1: A goes first (P1), Hand 1 = A, Hand 2 = B
        # swap_hands = False
        if use_gui:
            score_p1_v1, score_p2_v1 = play_variant_gui(args.bot_a, args.bot_b, seed, swap_hands=False)
        else:
            score_p1_v1, score_p2_v1 = play_variant(bot_a, bot_b, setup, swap_hands=False)
        score_a_v1, score_b_v1 = score_p1_v1, score_p2_v1

        # Variant 2: B goes first (P1), Hand 1 = B, Hand 2 = A
        # swap_hands = False (B gets P1 hand, which is Hand 1. A gets P2 hand, which is Hand 2)
        if use_gui:
            score_p1_v2, score_p2_v2 = play_variant_gui(args.bot_b, args.bot_a, seed, swap_hands=False)
        else:
            score_p1_v2, score_p2_v2 = play_variant(bot_b, bot_a, setup, swap_hands=False)
        score_b_v2, score_a_v2 = score_p1_v2, score_p2_v2

        # Variant 3: A goes first (P1), Hand 1 = B, Hand 2 = A
        # swap_hands = True (Player 1 hand becomes Hand 2, which is A. Player 2 hand becomes Hand 1, which is B)
        if use_gui:
            score_p1_v3, score_p2_v3 = play_variant_gui(args.bot_a, args.bot_b, seed, swap_hands=True)
        else:
            score_p1_v3, score_p2_v3 = play_variant(bot_a, bot_b, setup, swap_hands=True)
        score_a_v3, score_b_v3 = score_p1_v3, score_p2_v3

        # Variant 4: B goes first (P1), Hand 1 = A, Hand 2 = B
        # swap_hands = True (Player 1 hand becomes Hand 2, which is B. Player 2 hand becomes Hand 1, which is A)
        if use_gui:
            score_p1_v4, score_p2_v4 = play_variant_gui(args.bot_b, args.bot_a, seed, swap_hands=True)
        else:
            score_p1_v4, score_p2_v4 = play_variant(bot_b, bot_a, setup, swap_hands=True)
        score_b_v4, score_a_v4 = score_p1_v4, score_p2_v4

        # Aggregate total score for this seed
        total_a = score_a_v1 + score_a_v2 + score_a_v3 + score_a_v4
        total_b = score_b_v1 + score_b_v2 + score_b_v3 + score_b_v4

        sum_scores_a += total_a
        sum_scores_b += total_b

        # Determine winner of the 4-game set
        if total_a > total_b:
            outcome = f"{args.bot_a} WINS"
            tournament_points_a += 3
            wins_a += 1
        elif total_b > total_a:
            outcome = f"{args.bot_b} WINS"
            tournament_points_b += 3
            wins_b += 1
        else:
            outcome = "TIE"
            tournament_points_a += 1
            tournament_points_b += 1
            ties += 1

        print(f"  └─ Game 1 (A-P1, Hand 1-A): A={score_a_v1:>8} | B={score_b_v1:>8}")
        print(f"  └─ Game 2 (B-P1, Hand 1-B): A={score_a_v2:>8} | B={score_b_v2:>8}")
        print(f"  └─ Game 3 (A-P1, Hand 1-B): A={score_a_v3:>8} | B={score_b_v3:>8}")
        print(f"  └─ Game 4 (B-P1, Hand 1-A): A={score_a_v4:>8} | B={score_b_v4:>8}")
        print(f"  ⭐ Set Sum: {args.bot_a}={total_a:<9} | {args.bot_b}={total_b:<9} -> {outcome}")

    print("\n" + "=" * 70)
    print("🏆 Match Series Summary")
    print("=" * 70)
    print(f"Bot A ({args.bot_a}):")
    print(f"  - Set Wins: {wins_a}")
    print(f"  - Tournament Points: {tournament_points_a}")
    print(f"  - Cumulative Score: {sum_scores_a}")
    print(f"Bot B ({args.bot_b}):")
    print(f"  - Set Wins: {wins_b}")
    print(f"  - Tournament Points: {tournament_points_b}")
    print(f"  - Cumulative Score: {sum_scores_b}")
    print(f"Ties: {ties}")
    print("-" * 70)

    if tournament_points_a > tournament_points_b:
        print(f"👑 Overall Match Winner: {args.bot_a}!")
    elif tournament_points_b > tournament_points_a:
        print(f"👑 Overall Match Winner: {args.bot_b}!")
    else:
        print("🤝 Overall Match ended in a TIE!")
    print("=" * 70)


if __name__ == "__main__":
    main()
