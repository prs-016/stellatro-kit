"""
Fast future-aware smart greedy bot.

Strategy:
1. First pass: score every joker using the proven formula:
      my_score + 0.35 * opponent_gain

2. Second pass: only for the top few candidates, add future potential:
      best score if I later get one more joker

This keeps most of the strength of future lookahead while staying much faster.
"""

from copy import deepcopy
from itertools import combinations
from typing import List
import time

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


def _joker_key(joker) -> str:
    return getattr(joker, "name", joker.__class__.__name__)


def _best_hand(cards: List[Card], jokers) -> tuple[float, List[int]]:
    """Return (best_score, best_indices) across all C(n,5) combos."""
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


def _best_score(cards: List[Card], jokers) -> float:
    score, _ = _best_hand(cards, jokers)
    return score


class SmartGreedyBot:
    def pick_joker(self, state: GameState) -> int:
        start = time.perf_counter()
        TIME_LIMIT = 0.18  # stay under 200 ms

        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)

        opp_hand = _to_cards(state.player2_hand if is_p1 else state.player1_hand)
        opp_jokers = _to_jokers(state.player2_jokers if is_p1 else state.player1_jokers)

        pool = [_make_joker(j) for j in state.joker_pool]

        if not pool:
            return 0

        deny_weight = 0.35
        future_weight = 0.10

        # IMPORTANT: only do future lookahead for top candidates.
        TOP_K_FUTURE = 3

        score_cache = {}

        def cached_score(player: str, jokers) -> float:
            key = (player, tuple(_joker_key(j) for j in jokers))

            if key in score_cache:
                return score_cache[key]

            if player == "me":
                score = _best_score(my_hand, list(jokers))
            else:
                score = _best_score(opp_hand, list(jokers))

            score_cache[key] = score
            return score

        opp_base_score = cached_score("opp", opp_jokers)

        candidates = []

        # Pass 1: original fast greedy scoring for every joker.
        for i, candidate in enumerate(pool):
            my_after = my_jokers + [candidate]
            my_score = cached_score("me", my_after)

            opp_score_with_candidate = cached_score("opp", opp_jokers + [candidate])
            opponent_gain = max(0.0, opp_score_with_candidate - opp_base_score)

            base_value = my_score + deny_weight * opponent_gain

            candidates.append(
                {
                    "idx": i,
                    "joker": candidate,
                    "my_score": my_score,
                    "base_value": base_value,
                }
            )

        # Sort by original strong formula.
        candidates.sort(key=lambda x: x["base_value"], reverse=True)

        # Default answer = original greedy best.
        best_idx = candidates[0]["idx"]
        best_value = candidates[0]["base_value"]

        # Pass 2: future lookahead only for top K candidates.
        for item in candidates[:TOP_K_FUTURE]:
            if time.perf_counter() - start > TIME_LIMIT:
                break

            i = item["idx"]
            candidate = item["joker"]
            my_after = my_jokers + [candidate]
            my_score = item["my_score"]

            remaining = pool[:i] + pool[i + 1:]
            best_next_score = my_score

            # Check possible next jokers, but stop if close to time limit.
            for next_joker in remaining:
                if time.perf_counter() - start > TIME_LIMIT:
                    break

                next_score = cached_score("me", my_after + [next_joker])

                if next_score > best_next_score:
                    best_next_score = next_score

            future_gain = max(0.0, best_next_score - my_score)

            final_value = item["base_value"] + future_weight * future_gain

            if final_value > best_value:
                best_value = final_value
                best_idx = i

        elapsed_ms = (time.perf_counter() - start) * 1000

        if elapsed_ms > 200:
            print(f"WARNING: stronger pick_joker too slow: {elapsed_ms:.2f} ms")

        return best_idx

    def pick_hand(self, state: GameState) -> List[int]:
        is_p1 = state.current_turn == PlayerTurn.PLAYER1

        my_hand = _to_cards(state.player1_hand if is_p1 else state.player2_hand)
        my_jokers = _to_jokers(state.player1_jokers if is_p1 else state.player2_jokers)

        _, indices = _best_hand(my_hand, my_jokers)
        return indices


Bot = SmartGreedyBot