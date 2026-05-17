"""
Offline Oracle Bot — NOT for submission if there is a time limit.

Strategy:
1. During draft:
   - Exhaustively search the remaining joker draft using minimax.
   - Assume both players play optimally.
   - Leaf value = my best final hand score - opponent best final hand score.

2. During play:
   - Brute-force all C(10,5)=252 hands and play the best one.

Use this to test what the "best possible" draft decision looks like.
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


def _best_score(cards: List[Card], joker_names: tuple[str, ...]) -> float:
    jokers = [_make_joker_from_name(name) for name in joker_names]
    score, _ = _best_hand(cards, jokers)
    return score


class OracleBot:
    def pick_joker(self, state: GameState) -> int:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        opp_hand = _to_cards(state.player2_hand if is_p1 else state.player1_hand)

        my_jokers = tuple(_joker_name(j) for j in _to_jokers(
            state.player1_jokers if is_p1 else state.player2_jokers
        ))

        opp_jokers = tuple(_joker_name(j) for j in _to_jokers(
            state.player2_jokers if is_p1 else state.player1_jokers
        ))

        pool = tuple(_joker_name(_make_joker(j)) for j in state.joker_pool)

        if not pool:
            return 0

        @lru_cache(maxsize=None)
        def minimax(
            remaining: tuple[str, ...],
            my_picks: tuple[str, ...],
            opp_picks: tuple[str, ...],
            my_turn: bool,
        ) -> float:
            # Terminal: draft is over or nobody can pick more.
            if (
                not remaining
                or (
                    len(my_picks) >= JOKER_HAND_SIZE
                    and len(opp_picks) >= JOKER_HAND_SIZE
                )
            ):
                my_score = _best_score(my_hand, my_picks)
                opp_score = _best_score(opp_hand, opp_picks)
                return my_score - opp_score

            # If one player already has full jokers, skip their turn.
            if my_turn and len(my_picks) >= JOKER_HAND_SIZE:
                return minimax(remaining, my_picks, opp_picks, False)

            if (not my_turn) and len(opp_picks) >= JOKER_HAND_SIZE:
                return minimax(remaining, my_picks, opp_picks, True)

            if my_turn:
                best = -math.inf

                for i, joker_name in enumerate(remaining):
                    new_remaining = remaining[:i] + remaining[i + 1:]
                    value = minimax(
                        new_remaining,
                        my_picks + (joker_name,),
                        opp_picks,
                        False,
                    )
                    best = max(best, value)

                return best

            else:
                best = math.inf

                for i, joker_name in enumerate(remaining):
                    new_remaining = remaining[:i] + remaining[i + 1:]
                    value = minimax(
                        new_remaining,
                        my_picks,
                        opp_picks + (joker_name,),
                        True,
                    )
                    best = min(best, value)

                return best

        best_idx = 0
        best_value = -math.inf

        for i, joker_name in enumerate(pool):
            remaining = pool[:i] + pool[i + 1:]
            value = minimax(
                remaining,
                my_jokers + (joker_name,),
                opp_jokers,
                False,
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


Bot = OracleBot