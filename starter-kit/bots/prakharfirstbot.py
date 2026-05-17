import math
import time
from copy import deepcopy
from itertools import combinations
from typing import List

from stellatro_common import CardModel, GameState, JokerModel, PlayerTurn
from stellatro_game import Card, JOKER_HAND_SIZE, Joker, PLAYER_CARDS, Suit, evaluate_hand
from stellatro_game.jokers import ALL_JOKER_CLASSES, RegularJoker

Hand = List[Card]

_JOKER_NAME_TO_CLASS = {joker_cls.name: joker_cls for joker_cls in ALL_JOKER_CLASSES}


def _card_from_model(card_model: CardModel) -> Card:
    suits = [Suit(suit) for suit in card_model.suits]
    if not suits:
        raise ValueError("CardModel must include at least one suit.")
    card = Card(card_model.rank, suits[0])
    for suit in suits[1:]:
        card.add_suit(suit)
    card.scored = card_model.scored
    card.num_triggers = card_model.num_triggers
    card.stella = card_model.stella
    return card


def _joker_cls_from_model(joker_model: JokerModel) -> type:
    return _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)


def _hand_for_player(state: GameState, player_turn: PlayerTurn) -> Hand:
    if player_turn == PlayerTurn.PLAYER1:
        return [_card_from_model(card) for card in state.player1_hand]
    return [_card_from_model(card) for card in state.player2_hand]


def _joker_classes_for_player(state: GameState, player_turn: PlayerTurn) -> List[type]:
    if player_turn == PlayerTurn.PLAYER1:
        return [_joker_cls_from_model(joker) for joker in state.player1_jokers]
    return [_joker_cls_from_model(joker) for joker in state.player2_jokers]


def _get_diverse_candidates(cards: List[Card], count: int = 12, joker_classes: List[type] = None) -> List[List[Card]]:
    """Precompute strategically diverse combinations, scored with current jokers."""
    n = min(PLAYER_CARDS, len(cards))
    if n < 5:
        return []

    joker_classes = joker_classes or []
    scored_combos = []
    for combo in combinations(range(n), 5):
        subset = [cards[i] for i in combo]
        copied_subset = [deepcopy(c) for c in subset]
        fresh_jokers = [cls() for cls in joker_classes]
        try:
            score = evaluate_hand(copied_subset, fresh_jokers)
        except Exception:
            score = 0
        scored_combos.append((score, subset))

    scored_combos.sort(key=lambda x: x[0], reverse=True)

    candidates = []
    seen_indices = set()

    def get_combo_key(subset):
        return tuple(sorted((c.rank, tuple(sorted(s.value for s in c.suits))) for c in subset))

    def is_flush(subset):
        common_suits = set(subset[0].suits)
        for c in subset[1:]:
            common_suits &= set(c.suits)
            if not common_suits:
                return False
        return True

    def is_straight(subset):
        ranks = sorted(c.rank for c in subset)
        if len(set(ranks)) == 5 and ranks[-1] - ranks[0] == 4:
            return True
        if ranks == [2, 3, 4, 5, 14]:
            return True
        return False

    # 1. Add top base score combos (scale based on count)
    base_limit = max(8, int(count * 0.65))
    for score, subset in scored_combos[:base_limit]:
        key = get_combo_key(subset)
        if key not in seen_indices:
            seen_indices.add(key)
            candidates.append(subset)

    # 2. Add Flushes and Straights to cover specific synergies
    flush_limit = max(2, int(count * 0.15))
    straight_limit = max(2, int(count * 0.15))
    flushes_added = 0
    straights_added = 0
    for _, subset in scored_combos:
        key = get_combo_key(subset)
        if key in seen_indices:
            continue

        if is_flush(subset) and flushes_added < flush_limit:
            seen_indices.add(key)
            candidates.append(subset)
            flushes_added += 1

        if is_straight(subset) and straights_added < straight_limit:
            seen_indices.add(key)
            candidates.append(subset)
            straights_added += 1

        if len(candidates) >= count:
            break

    # 3. Fill up to target count
    for _, subset in scored_combos:
        if len(candidates) >= count:
            break
        key = get_combo_key(subset)
        if key not in seen_indices:
            seen_indices.add(key)
            candidates.append(subset)

    return candidates


def _get_synergy_multiplier(joker_classes: List[type]) -> float:
    """Project future synergy value for joker combos not yet fully assembled."""
    names = {cls.name if hasattr(cls, 'name') else cls.__name__ for cls in joker_classes}
    multiplier = 1.0

    # 1. Retrigger + Trigger Synergy
    retriggers = {"Seltzer", "Last Lecture", "Sock and Buskin", "Stargazing", "Encore"}
    triggers = {
        "Walkie Talkie", "Fibonacci Joker", "Scary Face Joker", "Sun God", 
        "Heart Joker", "Diamond Joker", "Club Joker", "Spade Joker",
        "Photograph", "Starcorn", "Supernova"
    }
    if any(n in retriggers for n in names) and any(n in triggers for n in names):
        multiplier += 0.35

    # 2. Stella Gainer + Stella Scaler Synergy
    stella_gainers = {
        "Fallen Star", "Starjack", "Branch Out", "Cache Coherence", 
        "Star Fish", "Wish Upon a Star", "Binary Star", "Pips", "Report Card"
    }
    stella_scalers = {
        "Stargazing", "Boiling Point", "Galaxy", "Popcorn", 
        "Starcorn", "Supernova", "Snowball", "Constellation"
    }
    if any(n in stella_gainers for n in names) and any(n in stella_scalers for n in names):
        multiplier += 0.35

    # 3. High Card Synergies
    if "UC Socially Dead" in names:
        flat_boosts = {"Half Joker", "Walkie Talkie", "Fibonacci Joker", "Dining Hall Prices", "Lively Joker"}
        if any(n in flat_boosts for n in names):
            multiplier += 0.25

    # 4. Flush / Suit Synergies
    flush_jokers = {"The Tribe", "Vibrant Joker", "Flush Mult Boost", "Flush Chip Boost", "Color Theory", "Flower Pot"}
    suit_boosters = {"Sun God", "Heart Joker", "Diamond Joker", "Club Joker", "Spade Joker", "Arrowhead"}
    if any(n in flush_jokers for n in names) and any(n in suit_boosters for n in names):
        multiplier += 0.20

    return multiplier


def _best_hand_from_candidates(candidates: List[List[Card]], joker_classes: List[type]) -> int:
    """Return the best score across precomputed candidates, boosted by synergy projection."""
    best_score = 0
    for subset in candidates:
        copied_subset = []
        for c in subset:
            new_c = Card(rank=c.rank, suit=list(c.suits)[0])
            new_c.suits = set(c.suits)
            copied_subset.append(new_c)
        fresh_jokers = [cls() for cls in joker_classes]
        try:
            score = evaluate_hand(copied_subset, fresh_jokers)
        except Exception:
            continue
        if score > best_score:
            best_score = score

    mult = _get_synergy_multiplier(joker_classes)
    return int(best_score * mult)


def _best_hand_exact(cards: List[Card], joker_classes: List[type]) -> tuple[int, List[int]]:
    """Brute force exact card play for play phase (only called once per turn)."""
    best_score = -1
    best_indices = list(range(5))
    n = min(PLAYER_CARDS, len(cards))
    if n < 5:
        return 0, []

    for combo in combinations(range(n), 5):
        copied_subset = []
        for i in combo:
            c = cards[i]
            new_c = Card(rank=c.rank, suit=list(c.suits)[0])
            new_c.suits = set(c.suits)
            copied_subset.append(new_c)
        fresh_jokers = [cls() for cls in joker_classes]
        try:
            score = evaluate_hand(copied_subset, fresh_jokers)
        except Exception:
            continue

        if score > best_score:
            best_score = score
            best_indices = list(combo)

    return max(0, best_score), best_indices


class Bot:
    def __init__(self, time_limit: float = 0.180) -> None:
        self.time_limit = time_limit
        self.search_start_time = 0.0

    def pick_joker(self, state: GameState) -> int:
        start_time = time.perf_counter()
        self.search_start_time = start_time
        player_turn = state.current_turn
        if player_turn not in (PlayerTurn.PLAYER1, PlayerTurn.PLAYER2):
            return 0

        my_hand = _hand_for_player(state, player_turn)
        opp_turn = (
            PlayerTurn.PLAYER2
            if player_turn == PlayerTurn.PLAYER1
            else PlayerTurn.PLAYER1
        )
        opp_hand = _hand_for_player(state, opp_turn)

        my_picks = _joker_classes_for_player(state, player_turn)
        opp_picks = _joker_classes_for_player(state, opp_turn)
        pool = [_joker_cls_from_model(joker) for joker in state.joker_pool]

        if not pool:
            return 0
        if len(pool) == 1:
            return 0

        # Precompute high-resolution (45) diverse candidates for minimax
        my_candidates_high = _get_diverse_candidates(my_hand, count=45, joker_classes=my_picks)
        opp_candidates_high = _get_diverse_candidates(opp_hand, count=45, joker_classes=opp_picks)

        # 1. Exact Greedy Search — brute-force all 252 combos for perfect accuracy
        my_base, _ = _best_hand_exact(my_hand, my_picks)
        opp_base, _ = _best_hand_exact(opp_hand, opp_picks)

        best_index = 0
        best_swing = -1.0

        for index, joker_cls in enumerate(pool):
            my_score, _ = _best_hand_exact(my_hand, my_picks + [joker_cls])
            opp_score, _ = _best_hand_exact(opp_hand, opp_picks + [joker_cls])
            
            my_gain = max(0, my_score - my_base)
            opp_gain = max(0, opp_score - opp_base)

            # Total swing: offense + denial (zero-sum optimal)
            swing = my_gain + opp_gain

            if swing > best_swing:
                best_swing = swing
                best_index = index

        # If time is tight, return greedy choice immediately
        if time.perf_counter() - start_time > self.time_limit:
            return best_index

        # 2. Pruned Minimax Search with Iterative Deepening
        # For minimax lookahead, slice the top 18 candidates to utilize remaining 30ms safely
        my_candidates_fast = my_candidates_high[:18]
        opp_candidates_fast = opp_candidates_high[:18]

        best_idx_found = best_index
        try:
            for target_depth in (1, 2, 3, 4):
                val, idx = self._minimax(
                    my_candidates_fast,
                    opp_candidates_fast,
                    pool,
                    my_picks,
                    opp_picks,
                    my_turn=True,
                    depth=0,
                    target_depth=target_depth,
                    alpha=-math.inf,
                    beta=math.inf,
                )
                if idx is not None:
                    best_idx_found = idx
        except TimeoutError:
            pass

        return best_idx_found

    def pick_hand(self, state: GameState) -> List[int]:
        player_turn = state.current_turn or PlayerTurn.PLAYER1
        hand = _hand_for_player(state, player_turn)
        joker_classes = _joker_classes_for_player(state, player_turn)
        _, indices = _best_hand_exact(hand, joker_classes)
        playable_cards = min(PLAYER_CARDS, len(hand))
        unique_in_range = []
        for idx in indices:
            if 0 <= idx < playable_cards and idx not in unique_in_range:
                unique_in_range.append(idx)
        for idx in range(playable_cards):
            if len(unique_in_range) == 5:
                break
            if idx not in unique_in_range:
                unique_in_range.append(idx)
        return unique_in_range[:5]

    def _minimax(
        self,
        my_candidates: List[List[Card]],
        opp_candidates: List[List[Card]],
        pool: List[type],
        my_picks: List[type],
        opp_picks: List[type],
        my_turn: bool,
        depth: int,
        target_depth: int,
        alpha: float,
        beta: float,
    ) -> tuple[float, int | None]:
        if time.perf_counter() - self.search_start_time > self.time_limit:
            raise TimeoutError()

        if len(my_picks) == JOKER_HAND_SIZE and len(opp_picks) == JOKER_HAND_SIZE:
            my_score = _best_hand_from_candidates(my_candidates, my_picks)
            opp_score = _best_hand_from_candidates(opp_candidates, opp_picks)
            return float(my_score - opp_score), None

        if depth >= target_depth or not pool:
            my_score = _best_hand_from_candidates(my_candidates, my_picks)
            opp_score = _best_hand_from_candidates(opp_candidates, opp_picks)
            return float(my_score - opp_score), None

        if depth == 0:
            K = 4
        elif depth <= 2:
            K = 3
        else:
            K = 2

        my_base = _best_hand_from_candidates(my_candidates, my_picks)
        opp_base = _best_hand_from_candidates(opp_candidates, opp_picks)
        candidates = []
        for index, joker_cls in enumerate(pool):
            if time.perf_counter() - self.search_start_time > self.time_limit:
                raise TimeoutError()
            
            if my_turn:
                score = _best_hand_from_candidates(my_candidates, my_picks + [joker_cls])
                opp_score = _best_hand_from_candidates(opp_candidates, opp_picks + [joker_cls])
                
                my_gain = max(0, score - my_base)
                opp_gain = max(0, opp_score - opp_base)
                val = my_gain + opp_gain
                candidates.append((index, val, joker_cls))
            else:
                score = _best_hand_from_candidates(opp_candidates, opp_picks + [joker_cls])
                my_score = _best_hand_from_candidates(my_candidates, my_picks + [joker_cls])
                
                opp_gain = max(0, score - opp_base)
                my_gain = max(0, my_score - my_base)
                val = opp_gain + my_gain
                candidates.append((index, val, joker_cls))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:K]

        best_idx = None
        if my_turn:
            best_val = -math.inf
            for index, _, joker_cls in top_candidates:
                next_pool = pool[:index] + pool[index + 1 :]
                val, _ = self._minimax(
                    my_candidates,
                    opp_candidates,
                    next_pool,
                    my_picks + [joker_cls],
                    opp_picks,
                    my_turn=False,
                    depth=depth + 1,
                    target_depth=target_depth,
                    alpha=alpha,
                    beta=beta,
                )
                if val > best_val:
                    best_val = val
                    best_idx = index
                alpha = max(alpha, best_val)
                if alpha >= beta:
                    break
            return best_val, best_idx
        else:
            best_val = math.inf
            for index, _, joker_cls in top_candidates:
                next_pool = pool[:index] + pool[index + 1 :]
                val, _ = self._minimax(
                    my_candidates,
                    opp_candidates,
                    next_pool,
                    my_picks,
                    opp_picks + [joker_cls],
                    my_turn=True,
                    depth=depth + 1,
                    target_depth=target_depth,
                    alpha=alpha,
                    beta=beta,
                )
                if val < best_val:
                    best_val = val
                    best_idx = index
                beta = min(beta, best_val)
                if alpha >= beta:
                    break
            return best_val, best_idx