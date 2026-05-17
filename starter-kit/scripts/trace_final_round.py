import random
import sys
from pathlib import Path
from typing import Any, List

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


def card_to_str(card) -> str:
    rank_str = {11: "J", 12: "Q", 13: "K", 14: "A"}.get(card.rank, str(card.rank))
    suits_str = "+".join(s.value for s in card.suits) if card.suits else "?"
    return f"{rank_str}-{suits_str}"


def play_game_with_detailed_trace(
    bot_a_ref: str,
    bot_b_ref: str,
    setup: GameSetup,
    swap_hands: bool,
    game_num: int,
    variant_desc: str,
) -> None:
    # Instantiate bots
    bot_p1 = instantiate_bot(bot_a_ref)
    bot_p2 = instantiate_bot(bot_b_ref)

    game = Game(verbose=False)
    game.load_setup(setup, swap_hands=swap_hands)

    p1_name = "Adversarial Bot (P1)"
    p2_name = "Greedy Bot (P2)"

    print("\n" + "=" * 80)
    print(f"🎬 GAME {game_num}: {variant_desc}")
    print("=" * 80)

    # Print starting hands
    print(f"\n♠️ Playable Hands Deal:")
    print(f"  - Player 1 Hand ({p1_name}): {[card_to_str(c) for c in game.p1hand]}")
    print(f"  - Player 2 Hand ({p2_name}): {[card_to_str(c) for c in game.p2hand]}")

    print(f"\n🃏 Starting Joker Pool:")
    for idx, joker in enumerate(game.jokers):
        print(f"  [{idx:>2}] {joker.name}: {joker.description}")

    # Draft Phase
    print(f"\n⛏️ DRAFT PHASE BEGINS:")
    draft_turn = 0
    while game.phase == Phase.DRAFT:
        state = game.get_game_state()
        pool_str = [f"[{i}] {j.name}" for i, j in enumerate(game.jokers)]
        print(f"\n  [Draft Turn {draft_turn + 1}]")
        print(f"    Available Pool: {', '.join(pool_str)}")

        if state.current_turn == PlayerTurn.PLAYER1:
            action = bot_p1.pick_joker(state)
            picked_joker = game.jokers[action].name
            print(f"    👉 {p1_name} drafts: {picked_joker} (index {action})")
            ok, _ = game.step(1, action=action)
        else:
            action = bot_p2.pick_joker(state)
            picked_joker = game.jokers[action].name
            print(f"    👉 {p2_name} drafts: {picked_joker} (index {action})")
            ok, _ = game.step(2, action=action)

        if not ok:
            raise RuntimeError("Draft action rejected")
        draft_turn += 1

    # End of draft
    print(f"\n🔒 DRAFT PHASE COMPLETE:")
    print(f"  - {p1_name} drafted Jokers: {[j.name for j in game.p1jokers]}")
    print(f"  - {p2_name} drafted Jokers: {[j.name for j in game.p2jokers]}")

    # Play Phase
    print(f"\n🎰 PLAY PHASE:")
    state = game.get_game_state()

    # Player 1 Plays
    p1_hand_indices = bot_p1.pick_hand(state)
    played_cards_p1 = [game.p1hand[i] for i in p1_hand_indices]
    ok, _ = game.step(1, hand_list=p1_hand_indices)
    if not ok:
        raise RuntimeError("Player 1 play rejected")

    # Player 2 Plays
    state = game.get_game_state()
    p2_hand_indices = bot_p2.pick_hand(state)
    played_cards_p2 = [game.p2hand[i] for i in p2_hand_indices]
    ok, final_state = game.step(2, hand_list=p2_hand_indices)
    if not ok:
        raise RuntimeError("Player 2 play rejected")

    # Evaluate hand types visually using engine
    from stellatro_game.checker import Checker
    p1_hand_type = Checker(played_cards_p1).check()
    p2_hand_type = Checker(played_cards_p2).check()

    print(f"  - {p1_name}:")
    print(f"    - Hand Held: {[card_to_str(c) for c in game.p1hand]}")
    print(f"    - Cards Played: {[card_to_str(c) for c in played_cards_p1]}")
    print(f"    - Classified Hand: {p1_hand_type}")
    print(f"    - Final Score: {final_state.player1_score}")

    print(f"  - {p2_name}:")
    print(f"    - Hand Held: {[card_to_str(c) for c in game.p2hand]}")
    print(f"    - Cards Played: {[card_to_str(c) for c in played_cards_p2]}")
    print(f"    - Classified Hand: {p2_hand_type}")
    print(f"    - Final Score: {final_state.player2_score}")


def main() -> None:
    seed = 104  # Seed for the final round (Set 5)
    rng = random.Random(seed)

    bot_a = "starter-kit/submission_folder/bot.py"
    bot_b = "greedy"

    setup = GameSetup.generate(rng=rng)
    setup.joker_pool = setup.joker_pool[:15]  # Cap pool to 15

    # Run the 4 mirrored games
    # Game 1: P1=BotA, P2=BotB, swap_hands=False (A gets Hand 1, B gets Hand 2)
    play_game_with_detailed_trace(
        bot_a, bot_b, setup, swap_hands=False, game_num=1,
        variant_desc="Adversarial Bot drafts first (P1) | Hand 1 goes to Adversarial, Hand 2 to Greedy"
    )

    # Game 2: P1=BotB, P2=BotA, swap_hands=False (B gets Hand 1, A gets Hand 2)
    play_game_with_detailed_trace(
        bot_b, bot_a, setup, swap_hands=False, game_num=2,
        variant_desc="Greedy Bot drafts first (P1) | Hand 1 goes to Greedy, Hand 2 to Adversarial"
    )

    # Game 3: P1=BotA, P2=BotB, swap_hands=True (A gets Hand 2, B gets Hand 1)
    play_game_with_detailed_trace(
        bot_a, bot_b, setup, swap_hands=True, game_num=3,
        variant_desc="Adversarial Bot drafts first (P1) | Hand 1 goes to Greedy, Hand 2 to Adversarial"
    )

    # Game 4: P1=BotB, P2=BotA, swap_hands=True (B gets Hand 2, A gets Hand 1)
    play_game_with_detailed_trace(
        bot_b, bot_a, setup, swap_hands=True, game_num=4,
        variant_desc="Greedy Bot drafts first (P1) | Hand 1 goes to Adversarial, Hand 2 to Greedy"
    )


if __name__ == "__main__":
    main()
