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


def _make_joker(joker_model):
    return _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)()


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


class SmartGreedyBot:
    def pick_joker(self, state: GameState) -> int:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)

        opp_hand = _to_cards(state.player2_hand if is_p1 else state.player1_hand)
        opp_jokers = _to_jokers(state.player2_jokers if is_p1 else state.player1_jokers)

        best_value = -1
        best_idx = 0

        # How much we care about blocking opponent's good jokers.
        deny_weight = 0.35

        opp_base_score, _ = _best_hand(opp_hand, opp_jokers)

        for i, joker_model in enumerate(state.joker_pool):
            candidate = _make_joker(joker_model)

            # Score if I take this joker.
            my_score, _ = _best_hand(my_hand, my_jokers + [candidate])

            # Score if opponent had gotten this joker.
            opp_score_with_candidate, _ = _best_hand(opp_hand, opp_jokers + [candidate])
            opponent_gain = max(0, opp_score_with_candidate - opp_base_score)

            # Main idea:
            # prioritize helping myself, but also steal jokers that help opponent a lot.
            value = my_score + deny_weight * opponent_gain

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


Bot = SmartGreedyBot