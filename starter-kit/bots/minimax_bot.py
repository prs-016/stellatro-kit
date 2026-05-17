"""
Minimax starter bot.

This bot looks ahead through the draft with alpha-beta minimax and then plays
the highest-scoring 5-card hand from its final cards.

High level flow:
1. Convert the Pydantic-style `GameState` models into the engine objects used
   by `stellatro_game.evaluate_hand`.
2. During the draft, treat joker selection as a two-player zero-sum game:
   "my best future score minus your best future score".
3. Search that draft game tree with minimax and alpha-beta pruning.
4. Once drafting is over, simply brute-force every 5-card hand and play the
   best one.
"""

import math
from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, List, Sequence

from stellatro_common import CardModel, GameState, JokerModel, PlayerTurn
from stellatro_game import Card, JOKER_HAND_SIZE, Joker, PLAYER_CARDS, Suit, evaluate_hand
from stellatro_game.jokers import ALL_JOKER_CLASSES, RegularJoker


Hand = List[Card]
JokerList = List[Joker]
# Map display names back to concrete joker classes so we can rebuild engine
# objects from the serialized models in GameState.
_JOKER_NAME_TO_CLASS = {joker_cls.name: joker_cls for joker_cls in ALL_JOKER_CLASSES}
# During draft search we do not fully re-evaluate every possible play subtree.
# Instead, we precompute only the strongest few 5-card candidate hands for each
# player and reuse those as a cheap approximation deeper in the tree.
DEFAULT_DRAFT_SUBSET_LIMIT = 3


def _card_from_model(card_model: CardModel) -> Card:
    """Convert a serialized card model into the mutable engine Card object."""
    suits = [Suit(suit) for suit in card_model.suits]
    if not suits:
        raise ValueError("CardModel must include at least one suit.")

    card = Card(card_model.rank, suits[0])
    # Some cards can hold multiple suits, so we reconstruct the full suit list.
    for suit in suits[1:]:
        card.add_suit(suit)
    # Preserve runtime scoring state because some jokers interact with these
    # flags/triggers during evaluation.
    card.scored = card_model.scored
    card.num_triggers = card_model.num_triggers
    return card


def _joker_from_model(joker_model: JokerModel) -> Joker:
    """Rebuild a live joker instance from its serialized name."""
    joker_cls = _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)
    return joker_cls()


def _hand_for_player(state: GameState, player_turn: PlayerTurn) -> Hand:
    """Pull the active player's hand out of GameState and convert every card."""
    if player_turn == PlayerTurn.PLAYER1:
        return [_card_from_model(card) for card in state.player1_hand]
    return [_card_from_model(card) for card in state.player2_hand]


def _jokers_for_player(state: GameState, player_turn: PlayerTurn) -> JokerList:
    """Pull the active player's drafted jokers out of GameState."""
    if player_turn == PlayerTurn.PLAYER1:
        return [_joker_from_model(joker) for joker in state.player1_jokers]
    return [_joker_from_model(joker) for joker in state.player2_jokers]


def _normalize_play_indices(indices: Sequence[int], hand_size: int) -> List[int]:
    """
    Clean up a proposed play so it is always a legal list of 5 unique indices.

    The search code should already return good indices, but this keeps the bot
    robust if a future edit produces duplicates or out-of-range values.
    """
    playable_cards = min(PLAYER_CARDS, hand_size)
    unique_in_range: List[int] = []

    for index in indices:
        if 0 <= index < playable_cards and index not in unique_in_range:
            unique_in_range.append(index)
        if len(unique_in_range) == 5:
            return unique_in_range

    for index in range(playable_cards):
        if index not in unique_in_range:
            unique_in_range.append(index)
        if len(unique_in_range) == 5:
            break

    return unique_in_range[:5]


def _all_5_card_subsets(hand: Sequence[Card]) -> Iterable[tuple[int, ...]]:
    """Generate every legal 5-card choice by index."""
    if len(hand) < 5:
        return
    yield from combinations(range(len(hand)), 5)


def _iter_play_values(
    hand: Sequence[Card], jokers: Sequence[Joker]
) -> Iterable[tuple[tuple[int, ...], int]]:
    """
    Yield `(indices, score)` for every possible 5-card hand.

    We deepcopy both cards and jokers before evaluation because scoring can
    mutate state such as trigger counts.
    """
    for indices in _all_5_card_subsets(hand):
        subset = [deepcopy(hand[index]) for index in indices]
        try:
            yield indices, evaluate_hand(subset, deepcopy(list(jokers)))
        except Exception:
            continue


def _play_value_for_indices(
    hand: Sequence[Card], jokers: Sequence[Joker], indices: Sequence[int]
) -> int:
    """Score one specific 5-card choice."""
    subset = [deepcopy(hand[index]) for index in indices]
    try:
        return evaluate_hand(subset, deepcopy(list(jokers)))
    except Exception:
        return 0


def _candidate_play_subsets(
    hand: Hand, jokers: JokerList, limit: int = DEFAULT_DRAFT_SUBSET_LIMIT
) -> tuple[tuple[int, ...], ...]:
    """
    Keep only the top few promising 5-card choices for draft evaluation.

    Full minimax would be very expensive if every node recomputed every possible
    future hand for both players. This helper trims the play-space down to the
    strongest `limit` subsets seen with the current joker set.
    """
    scored_subsets = sorted(
        _iter_play_values(hand, jokers),
        key=lambda item: item[1],
        reverse=True,
    )
    if limit <= 0:
        return tuple(indices for indices, _ in scored_subsets)
    return tuple(indices for indices, _ in scored_subsets[:limit])


def _approximate_best_play_value(
    hand: Hand,
    jokers: JokerList,
    candidate_subsets: Sequence[tuple[int, ...]],
) -> int:
    """
    Estimate a hand's strength by rescoring only the cached candidate subsets.

    If we have no cached candidates, fall back to the exact best-play search.
    """
    if not candidate_subsets:
        return _best_play_value(hand, jokers)
    return max(_play_value_for_indices(hand, jokers, indices) for indices in candidate_subsets)


def _best_play_indices(hand: Hand, jokers: JokerList) -> List[int]:
    """Find the exact best 5-card play after drafting is complete."""
    best_value = -math.inf
    best_indices: tuple[int, ...] | None = None

    for indices, value in _iter_play_values(hand, jokers):
        if value > best_value:
            best_value = value
            best_indices = indices

    if best_indices is None:
        return []
    return list(best_indices)


def _best_play_value(hand: Hand, jokers: JokerList) -> int:
    """Return the exact score of the best possible 5-card play."""
    best_value = -math.inf
    for _, value in _iter_play_values(hand, jokers):
        if value > best_value:
            best_value = value
    return 0 if best_value == -math.inf else int(best_value)


@dataclass(frozen=True)
class DraftState:
    """Compact immutable node used by minimax during the draft phase."""
    remaining: tuple[Joker, ...]
    my_picks: tuple[Joker, ...]
    opp_picks: tuple[Joker, ...]
    my_turn: bool


class Bot:
    """
    Draft with minimax, then play the exact best 5-card hand.

    `max_depth` controls how far the draft search explores before switching to
    the heuristic evaluation. `draft_subset_limit` controls how many promising
    play subsets are cached for that heuristic.
    """

    def __init__(
        self,
        max_depth: int | None = 1,
        draft_subset_limit: int = DEFAULT_DRAFT_SUBSET_LIMIT,
    ) -> None:
        self.max_depth = max_depth
        self.draft_subset_limit = draft_subset_limit

    def pick_joker(self, state: GameState) -> int:
        """
        Choose the joker that maximizes our future advantage.

        For each available joker:
        - assume we take it now,
        - let minimax simulate the rest of the alternating draft,
        - score the resulting position as `my best hand - opponent best hand`.
        """
        player_turn = state.current_turn
        if player_turn not in (PlayerTurn.PLAYER1, PlayerTurn.PLAYER2):
            return 0

        # Build local engine objects for both players so the search can score
        # future positions without touching the original GameState.
        my_hand = _hand_for_player(state, player_turn)
        opp_turn = (
            PlayerTurn.PLAYER2
            if player_turn == PlayerTurn.PLAYER1
            else PlayerTurn.PLAYER1
        )
        opp_hand = _hand_for_player(state, opp_turn)
        my_picks = tuple(_jokers_for_player(state, player_turn))
        opp_picks = tuple(_jokers_for_player(state, opp_turn))
        pool = tuple(_joker_from_model(joker) for joker in state.joker_pool)
        # Precompute the most promising future hand shapes once up front and
        # reuse them all through the draft search.
        my_candidate_subsets = _candidate_play_subsets(
            my_hand, list(my_picks), self.draft_subset_limit
        )
        opp_candidate_subsets = _candidate_play_subsets(
            opp_hand, list(opp_picks), self.draft_subset_limit
        )

        best_index = 0
        best_value = -math.inf
        for index, joker in enumerate(pool):
            # Simulate "what if I draft this joker right now?"
            next_state = DraftState(
                remaining=pool[:index] + pool[index + 1 :],
                my_picks=my_picks + (joker,),
                opp_picks=opp_picks,
                my_turn=False,
            )
            value = self._minimax(
                my_hand,
                opp_hand,
                next_state,
                -math.inf,
                math.inf,
                depth=1,
                my_candidate_subsets=my_candidate_subsets,
                opp_candidate_subsets=opp_candidate_subsets,
            )
            # Choose the move with the highest minimax value.
            if value > best_value:
                best_value = value
                best_index = index
        return best_index

    def pick_hand(self, state: GameState) -> List[int]:
        """
        Once draft is over, do an exact brute-force search over every 5-card hand.
        """
        player_turn = state.current_turn or PlayerTurn.PLAYER1
        hand = _hand_for_player(state, player_turn)
        jokers = _jokers_for_player(state, player_turn)
        return _normalize_play_indices(_best_play_indices(hand, jokers), len(hand))

    def _leaf_value(
        self,
        my_hand: Hand,
        opp_hand: Hand,
        state: DraftState,
        my_candidate_subsets: Sequence[tuple[int, ...]],
        opp_candidate_subsets: Sequence[tuple[int, ...]],
    ) -> float:
        """
        Exact-ish terminal evaluation once both players have full joker hands.

        The score is zero-sum: positive means the position favors us, negative
        means it favors the opponent.
        """
        my_best = _approximate_best_play_value(
            my_hand, list(state.my_picks), my_candidate_subsets
        )
        opp_best = _approximate_best_play_value(
            opp_hand, list(state.opp_picks), opp_candidate_subsets
        )
        return float(my_best - opp_best)

    def _heuristic_value(
        self,
        my_hand: Hand,
        opp_hand: Hand,
        state: DraftState,
        my_candidate_subsets: Sequence[tuple[int, ...]],
        opp_candidate_subsets: Sequence[tuple[int, ...]],
    ) -> float:
        """
        Heuristic used when we cut search off before the draft fully ends.

        This uses the current joker collections and asks: "if the draft stopped
        here, how much better would my best hand be than yours?"
        """
        my_now = _approximate_best_play_value(
            my_hand, list(state.my_picks), my_candidate_subsets
        )
        opp_now = _approximate_best_play_value(
            opp_hand, list(state.opp_picks), opp_candidate_subsets
        )
        return float(my_now - opp_now)

    def _minimax(
        self,
        my_hand: Hand,
        opp_hand: Hand,
        state: DraftState,
        alpha: float,
        beta: float,
        depth: int,
        my_candidate_subsets: Sequence[tuple[int, ...]],
        opp_candidate_subsets: Sequence[tuple[int, ...]],
    ) -> float:
        """
        Standard alpha-beta minimax over the remaining joker draft.

        - Maximizing nodes are "my turn": choose the joker that helps us most.
        - Minimizing nodes are "opponent turn": assume they choose the joker
          that hurts us most.
        - `alpha` is the best guaranteed value seen for the maximizing player.
        - `beta` is the best guaranteed value seen for the minimizing player.
        - When `alpha >= beta`, the rest of that branch cannot affect the final
          decision, so we prune it.
        """
        # Terminal node: both players have drafted a full joker hand.
        if (
            len(state.my_picks) == JOKER_HAND_SIZE
            and len(state.opp_picks) == JOKER_HAND_SIZE
        ):
            return self._leaf_value(
                my_hand,
                opp_hand,
                state,
                my_candidate_subsets,
                opp_candidate_subsets,
            )

        # Depth limit reached: stop expanding the tree and estimate the
        # position with the heuristic instead.
        if self.max_depth is not None and depth >= self.max_depth:
            return self._heuristic_value(
                my_hand,
                opp_hand,
                state,
                my_candidate_subsets,
                opp_candidate_subsets,
            )

        # Maximizing layer: we choose the move that makes the position best for us.
        if state.my_turn:
            best_value = -math.inf
            for index, joker in enumerate(state.remaining):
                next_state = DraftState(
                    remaining=state.remaining[:index] + state.remaining[index + 1 :],
                    my_picks=state.my_picks + (joker,),
                    opp_picks=state.opp_picks,
                    my_turn=False,
                )
                value = self._minimax(
                    my_hand,
                    opp_hand,
                    next_state,
                    alpha,
                    beta,
                    depth + 1,
                    my_candidate_subsets,
                    opp_candidate_subsets,
                )
                if value > best_value:
                    best_value = value
                # Tighten alpha with the best maximizing result seen so far.
                if best_value > alpha:
                    alpha = best_value
                # No need to search more children if the minimizing player would
                # already avoid this branch.
                if alpha >= beta:
                    break
            return best_value

        # Minimizing layer: assume the opponent chooses the move worst for us.
        best_value = math.inf
        for index, joker in enumerate(state.remaining):
            next_state = DraftState(
                remaining=state.remaining[:index] + state.remaining[index + 1 :],
                my_picks=state.my_picks,
                opp_picks=state.opp_picks + (joker,),
                my_turn=True,
            )
            value = self._minimax(
                my_hand,
                opp_hand,
                next_state,
                alpha,
                beta,
                depth + 1,
                my_candidate_subsets,
                opp_candidate_subsets,
            )
            if value < best_value:
                best_value = value
            # Tighten beta with the best minimizing result seen so far.
            if best_value < beta:
                beta = best_value
            # Symmetric alpha-beta prune for minimizing nodes.
            if alpha >= beta:
                break
        return best_value


# Friendly alias so other code can import either `Bot` or `MinimaxBot`.
MinimaxBot = Bot
