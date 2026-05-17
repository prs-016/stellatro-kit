"""
Fast Oracle Bot — for testing, not necessarily for final submission.

Set MAX_DEPTH = None for full exhaustive search.
Set MAX_DEPTH = 4 or 5 for a much faster approximate oracle.
"""

import math
from copy import deepcopy
from functools import lru_cache
from itertools import combinations
from typing import List

from stellatro_common import GameState, PlayerTurn
from stellatro_game import Card, Suit, evaluate_hand, PLAYER_CARDS, JOKER_HAND_SIZE
from stellatro_game.jokers import ALL_JOKER_CLASSES, RegularJoker

_JOKER_NAME_TO_CLASS = {cls.name: cls for cls in ALL_JOKER_CLASSES}

# None = true exhaustive oracle, but slow.
# 4 or 5 = much faster and still useful for testing.
MAX_DEPTH = 5


def _to_cards(card_models) -> List[Card]:
    cards = []
    for c in card_models:
        card = Card(c.rank, Suit(c.suits[0]))
        for s in c.suits[1:]:
            card.add_suit(Suit(s))
        card.scored = c.scored
        card.num_triggers = c.num_triggers
        cards.append(card)
    return cards


def _to_jokers(joker_models):
    return [_JOKER_NAME_TO_CLASS.get(j.name, RegularJoker)() for j in joker_models]


def _make_joker(joker_model):
    return _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)()


def _make_joker_from_name(name: str):
    return _JOKER_NAME_TO_CLASS.get(name, RegularJoker)()


def _joker_name(joker) -> str:
    return getattr(joker, "name", joker.__class__.__name__)


def _canonical_names(joker_names):
    """
    Treat joker sets as unordered for caching.
    This makes the oracle MUCH faster.
    """
    return tuple(sorted(joker_names))


def _best_hand(cards: List[Card], jokers) -> tuple[float, List[int]]:
    best_score = -1.0
    best_indices = list(range(5))
    n = min(PLAYER_CARDS, len(cards))

    for combo in combinations(range(n), 5):
        try:
            score = evaluate_hand(
                [deepcopy(cards[i]) for i in combo],
                deepcopy(jokers),
            )
        except Exception:
            continue

        if score > best_score:
            best_score = score
            best_indices = list(combo)

    return best_score, best_indices


class FastOracleBot:
    def pick_joker(self, state: GameState) -> int:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        opp_hand = _to_cards(state.player2_hand if is_p1 else state.player1_hand)

        my_jokers = tuple(
            _joker_name(j)
            for j in _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)
        )

        opp_jokers = tuple(
            _joker_name(j)
            for j in _to_jokers(state.player2_jokers if is_p1 else state.player1_jokers)
        )

        pool = tuple(_joker_name(_make_joker(j)) for j in state.joker_pool)

        if not pool:
            return 0

        @lru_cache(maxsize=None)
        def best_score(player: str, joker_names: tuple[str, ...]) -> float:
            joker_names = _canonical_names(joker_names)
            jokers = [_make_joker_from_name(name) for name in joker_names]

            if player == "me":
                score, _ = _best_hand(my_hand, jokers)
            else:
                score, _ = _best_hand(opp_hand, jokers)

            return score

        def evaluate(my_picks, opp_picks) -> float:
            return (
                best_score("me", _canonical_names(my_picks))
                - best_score("opp", _canonical_names(opp_picks))
            )

        def ordered_moves(remaining, my_picks, opp_picks, my_turn):
            """
            Search promising moves first so alpha-beta prunes more.
            """
            scored = []

            for i, joker_name in enumerate(remaining):
                new_remaining = remaining[:i] + remaining[i + 1:]

                if my_turn:
                    new_my = my_picks + (joker_name,)
                    new_opp = opp_picks
                else:
                    new_my = my_picks
                    new_opp = opp_picks + (joker_name,)

                val = evaluate(new_my, new_opp)
                scored.append((val, i, joker_name, new_remaining))

            # My turn: high values first.
            # Opp turn: low values first.
            scored.sort(reverse=my_turn, key=lambda x: x[0])
            return scored

        @lru_cache(maxsize=None)
        def minimax(
            remaining: tuple[str, ...],
            my_picks: tuple[str, ...],
            opp_picks: tuple[str, ...],
            my_turn: bool,
            depth: int,
            alpha: float,
            beta: float,
        ) -> float:
            my_picks = _canonical_names(my_picks)
            opp_picks = _canonical_names(opp_picks)

            draft_done = (
                len(my_picks) >= JOKER_HAND_SIZE
                and len(opp_picks) >= JOKER_HAND_SIZE
            )

            if not remaining or draft_done:
                return evaluate(my_picks, opp_picks)

            if MAX_DEPTH is not None and depth >= MAX_DEPTH:
                return evaluate(my_picks, opp_picks)

            if my_turn and len(my_picks) >= JOKER_HAND_SIZE:
                return minimax(remaining, my_picks, opp_picks, False, depth, alpha, beta)

            if (not my_turn) and len(opp_picks) >= JOKER_HAND_SIZE:
                return minimax(remaining, my_picks, opp_picks, True, depth, alpha, beta)

            if my_turn:
                best = -math.inf

                for _, _, joker_name, new_remaining in ordered_moves(
                    remaining, my_picks, opp_picks, my_turn=True
                ):
                    value = minimax(
                        new_remaining,
                        my_picks + (joker_name,),
                        opp_picks,
                        False,
                        depth + 1,
                        alpha,
                        beta,
                    )

                    best = max(best, value)
                    alpha = max(alpha, best)

                    if alpha >= beta:
                        break

                return best

            else:
                best = math.inf

                for _, _, joker_name, new_remaining in ordered_moves(
                    remaining, my_picks, opp_picks, my_turn=False
                ):
                    value = minimax(
                        new_remaining,
                        my_picks,
                        opp_picks + (joker_name,),
                        True,
                        depth + 1,
                        alpha,
                        beta,
                    )

                    best = min(best, value)
                    beta = min(beta, best)

                    if alpha >= beta:
                        break

                return best

        best_idx = 0
        best_value = -math.inf

        # Root search.
        root_moves = ordered_moves(pool, my_jokers, opp_jokers, my_turn=True)

        for _, i, joker_name, remaining in root_moves:
            value = minimax(
                remaining,
                my_jokers + (joker_name,),
                opp_jokers,
                False,
                1,
                -math.inf,
                math.inf,
            )

            if value > best_value:
                best_value = value
                best_idx = i

        return best_idx

    def pick_hand(self, state: GameState) -> List[int]:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)

        _, indices = _best_hand(my_hand, my_jokers)
        return indices


Bot = FastOracleBot