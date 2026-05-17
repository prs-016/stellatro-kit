import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from stellatro_common import GameState
from stellatro_game import Game, Phase, PlayerTurn


class ShellInputError(ValueError):
    """Raised when shell input cannot be parsed into a legal move shape."""


def render_joker_list(label: str, jokers: list) -> None:
    print(label)
    if not jokers:
        print("  (none)")
        return

    for i, joker in enumerate(jokers):
        print(f"[{i}] {joker.name}: {joker.description}")


def render_state(state: GameState) -> None:
    """Simple text renderer for the game state."""
    print("\n" + "=" * 30)
    print(f"PHASE: {state.phase.name} | TURN: {state.current_turn}")
    print(f"P1 Score: {state.player1_score} | P2 Score: {state.player2_score}")
    print("-" * 30)

    print("Your current hand:")
    for i, card in enumerate(state.player1_hand):
        print(f"[{i}]: {card}")
    print()

    print("Your opponent's hand:")
    for i, card in enumerate(state.player2_hand):
        print(f"[{i}]: {card}")

    render_joker_list("Player 1 Jokers:", state.player1_jokers)
    render_joker_list("Player 2 Jokers:", state.player2_jokers)

    if state.phase == Phase.DRAFT:
        render_joker_list("Available Jokers to pick:", state.joker_pool)
    elif state.phase == Phase.PLAY:
        print("Your Hand Indices: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]")

    print("=" * 30)


def parse_draft_choice(raw_choice: str, joker_count: int) -> int:
    """Parse a draft input string into a joker index."""
    choice = raw_choice.strip()
    if not choice:
        raise ShellInputError("No joker index entered. Please type one number.")

    try:
        joker_index = int(choice)
    except ValueError as exc:
        raise ShellInputError("Please enter a whole-number joker index.") from exc

    if joker_index < 0 or joker_index >= joker_count:
        raise ShellInputError(f"Joker index must be between 0 and {joker_count - 1}.")

    return joker_index


def parse_play_indices(raw_cards: str, hand_size: int) -> list[int]:
    """Parse a play input string into exactly 5 unique card indices."""
    if not raw_cards.strip():
        raise ShellInputError(
            "No card indices entered. Please provide 5 comma-separated numbers."
        )

    parts = [part.strip() for part in raw_cards.split(",")]
    if any(not part for part in parts):
        raise ShellInputError(
            "Found an empty card slot. Use comma-separated numbers like 0,2,4,6,8."
        )

    try:
        indices = [int(part) for part in parts]
    except ValueError as exc:
        raise ShellInputError("Card indices must all be whole numbers.") from exc

    if len(indices) != 5:
        raise ShellInputError(
            f"You must choose exactly 5 cards; received {len(indices)} selection(s)."
        )

    if len(indices) != len(set(indices)):
        raise ShellInputError("Duplicate card indices are not allowed.")

    invalid_indices = [index for index in indices if index < 0 or index >= hand_size]
    if invalid_indices:
        raise ShellInputError(
            f"Card indices must be between 0 and {hand_size - 1}; got {invalid_indices}."
        )

    return indices


def main() -> None:
    game = Game()
    game.start_round()

    while game.phase != Phase.OVER:
        state = game.get_game_state()
        render_state(state)

        current_p_num = 1 if state.current_turn == PlayerTurn.PLAYER1 else 2

        try:
            if state.phase == Phase.DRAFT:
                choice = input(f"Player {current_p_num}, pick a Joker index: ")
                joker_index = parse_draft_choice(choice, len(state.joker_pool))
                success, _ = game.step(current_p_num, action=joker_index)
            elif state.phase == Phase.PLAY:
                cards = input(
                    f"Player {current_p_num}, enter up to 5 card indices (e.g., 0,2,4): "
                )
                hand_size = (
                    len(state.player1_hand)
                    if state.current_turn == PlayerTurn.PLAYER1
                    else len(state.player2_hand)
                )
                indices = parse_play_indices(cards, hand_size)
                success, _ = game.step(current_p_num, hand_list=indices)
            else:
                success = True

            if not success:
                print(
                    f">>> Move was rejected. It is still Player {current_p_num}'s turn in"
                    f" {state.phase.name.lower()} phase. Please try again."
                )
        except ShellInputError as exc:
            print(f">>> {exc}")
        except Exception as e:
            print(f">>> Error: {e}")

    print("\nGAME OVER")
    final = game.get_game_state()
    print(f"Final Score - P1: {final.player1_score} | P2: {final.player2_score}")


if __name__ == "__main__":
    main()
