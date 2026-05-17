"""
Greedy bot — picks the joker that maximises the best possible hand score
given the current hand, then plays the highest-scoring 5-card combo.

Strategy: for each candidate joker, brute-force all C(10,5)=252 hand combos
and keep the joker that yields the highest score. Fast enough to run in <1ms.
"""

from copy import deepcopy
from itertools import combinations
from typing import List

from stellatro_common import GameState, PlayerTurn
from stellatro_game import Card, Suit, evaluate_hand, PLAYER_CARDS
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


def _best_hand(cards: List[Card], jokers) -> tuple[int, List[int]]:
    """Return (best_score, best_indices) across all C(n,5) combos."""
    best_score = -1
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


class GreedyBot:
    def pick_joker(self, state: GameState) -> int:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1
        my_hand   = _to_cards(state.player1_hand   if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)

        best_score = -1
        best_idx = 0
        for i, joker_model in enumerate(state.joker_pool):
            candidate = _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)()
            score, _ = _best_hand(my_hand, my_jokers + [candidate])
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def pick_hand(self, state: GameState) -> List[int]:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1
        my_hand   = _to_cards(state.player1_hand   if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)
        _, indices = _best_hand(my_hand, my_jokers)
        return indices


Bot = GreedyBot
