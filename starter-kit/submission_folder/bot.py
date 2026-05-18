import math
import time
from itertools import combinations
from typing import Dict, List

from stellatro_common import CardModel, GameState, JokerModel, PlayerTurn
from stellatro_game import Card, JOKER_HAND_SIZE, PLAYER_CARDS, Suit, evaluate_hand
from stellatro_game.jokers import ALL_JOKER_CLASSES, RegularJoker

Hand = List[Card]

_JOKER_NAME_TO_CLASS = {joker_cls.name: joker_cls for joker_cls in ALL_JOKER_CLASSES}


# ── Joker Tier Map ──────────────────────────────────────────────────────────────
_JOKER_TIER: Dict[str, float] = {
    "Supernova": 2.0,
    "Galaxy": 1.8,
    "Sun God": 1.8,
    "Boiling Point": 1.7,
    "The Family": 1.6,
    "Flower Pot": 1.6,
    "The Tribe": 1.6,
    "The Duo": 1.5,
    "The Trio": 1.5,
    "The Order": 1.5,
    "UC Socially Dead": 1.5,
    "PhotoGraph Joker": 1.5,
    "Photograph": 1.5,
    "Starcorn": 1.4,
    "Plasma": 1.4,

    "Stargazing": 1.4,
    "Starjack": 1.3,
    "Fallen Star": 1.3,
    "Star Fish": 1.3,
    "Thrice Twice": 1.2,
    "Binary Star": 1.2,
    "Pips": 1.2,
    "Report Card": 1.2,
    "Wish Upon a Star": 1.1,
    "Branch Out": 1.1,
    "Cache Coherence": 1.1,
    "Star Plasma": 1.1,
    "Constellation": 1.1,
    "Snowball": 1.0,

    "Seltzer": 1.3,
    "Sock and Buskin": 1.2,
    "Last Lecture": 1.2,
    "Encore": 1.1,
    "Jam Session": 1.2,

    "SixSeven": 1.3,
    "Six Seven": 1.3,
    "Blackjack": 1.2,
    "Fibonacci Joker": 1.1,
    "Walkie Talkie": 1.0,
    "Eighth College": 1.0,
    "Half Joker": 0.9,
    "Anya": 1.1,

    "Mirror": 0.9,
    "Spotlight": 0.8,
    "Color Theory": 0.8,
    "Study Group": 0.7,
    "Group Project": 0.7,
    "Lock In": 0.8,
    "LockIn": 0.8,
    "Loss Cut": 0.7,
    "Scary Face Joker": 0.7,
    "Dining Hall Prices": 0.7,
    "Student ID": 0.7,
    "Bit Byte": 0.6,
    "Popcorn": 0.6,
}

_STELLA_GENERATORS = {
    "Fallen Star",
    "Starjack",
    "Branch Out",
    "Cache Coherence",
    "Star Fish",
    "Wish Upon a Star",
    "Binary Star",
    "Pips",
    "Report Card",
    "Thrice Twice",
    "Star Plasma",
}

_STELLA_USERS = {
    "Stargazing",
    "Boiling Point",
    "Galaxy",
    "Starcorn",
    "Supernova",
    "Snowball",
    "Constellation",
}

_MULT_MULTIPLIERS = {
    "Sun God",
    "PhotoGraph Joker",
    "Photograph",
    "Flower Pot",
    "The Duo",
    "The Trio",
    "The Family",
    "The Tribe",
    "The Order",
    "UC Socially Dead",
    "Plasma",
    "Blackjack",
    "Boiling Point",
    "Galaxy",
    "Supernova",
    "Starcorn",
}

_RETRIGGERS = {
    "Seltzer",
    "Last Lecture",
    "Sock and Buskin",
    "Stargazing",
    "Encore",
}

_PER_CARD_TRIGGERS = {
    "Walkie Talkie",
    "Fibonacci Joker",
    "Scary Face Joker",
    "Sun God",
    "Heart Joker",
    "Diamond Joker",
    "Club Joker",
    "Spade Joker",
    "Starcorn",
    "Supernova",
    "Constellation",
}


def _card_from_model(card_model: CardModel) -> Card:
    suits = [Suit(suit) for suit in card_model.suits]
    if not suits:
        raise ValueError("CardModel must include at least one suit.")

    card = Card(card_model.rank, suits[0])

    for suit in suits[1:]:
        card.add_suit(suit)

    card.scored = card_model.scored
    card.num_triggers = card_model.num_triggers

    if hasattr(card_model, "stella"):
        card.stella = card_model.stella

    return card


def _copy_card(card: Card) -> Card:
    suits = list(card.suits)
    new_card = Card(card.rank, suits[0])

    for suit in suits[1:]:
        new_card.add_suit(suit)

    new_card.scored = card.scored
    new_card.num_triggers = card.num_triggers

    if hasattr(card, "stella"):
        new_card.stella = card.stella

    return new_card


def _joker_cls_from_model(joker_model: JokerModel) -> type:
    return _JOKER_NAME_TO_CLASS.get(joker_model.name, RegularJoker)


def _joker_name(joker_cls: type) -> str:
    return joker_cls.name if hasattr(joker_cls, "name") else joker_cls.__name__


def _hand_for_player(state: GameState, player_turn: PlayerTurn) -> Hand:
    if player_turn == PlayerTurn.PLAYER1:
        return [_card_from_model(card) for card in state.player1_hand]
    return [_card_from_model(card) for card in state.player2_hand]


def _joker_classes_for_player(state: GameState, player_turn: PlayerTurn) -> List[type]:
    if player_turn == PlayerTurn.PLAYER1:
        return [_joker_cls_from_model(joker) for joker in state.player1_jokers]
    return [_joker_cls_from_model(joker) for joker in state.player2_jokers]


def _is_flush(subset: List[Card]) -> bool:
    common = set(subset[0].suits)

    for card in subset[1:]:
        common &= set(card.suits)
        if not common:
            return False

    return True


def _is_straight(subset: List[Card]) -> bool:
    ranks = sorted(card.rank for card in subset)

    if len(set(ranks)) == 5 and ranks[-1] - ranks[0] == 4:
        return True

    return ranks == [2, 3, 4, 5, 14]


def _combo_key(subset: List[Card]):
    return tuple(
        sorted(
            (card.rank, tuple(sorted(suit.value for suit in card.suits)))
            for card in subset
        )
    )


def _get_diverse_candidates(
    cards: List[Card],
    count: int = 45,
    joker_classes: List[type] | None = None,
) -> List[List[Card]]:
    """
    Candidate hands for minimax approximation.

    Includes:
    - top current-scoring hands
    - flushes
    - straights
    - pairs / trips / quads
    - two-pair/full-house-ish hands
    - high-card style hands
    - face-card-heavy hands
    - low-card hands
    - stella-heavy hands
    """
    n = min(PLAYER_CARDS, len(cards))

    if n < 5:
        return []

    joker_classes = joker_classes or []
    scored_combos = []

    for combo in combinations(range(n), 5):
        subset = [cards[i] for i in combo]

        try:
            score = evaluate_hand(
                [_copy_card(card) for card in subset],
                [cls() for cls in joker_classes],
            )
        except Exception:
            score = 0

        scored_combos.append((score, subset))

    scored_combos.sort(key=lambda x: x[0], reverse=True)

    candidates = []
    seen = set()

    def add_subset(subset):
        if len(candidates) >= count:
            return False

        key = _combo_key(subset)

        if key in seen:
            return False

        seen.add(key)
        candidates.append(subset)
        return True

    def rank_counts(subset):
        counts = {}
        for card in subset:
            counts[card.rank] = counts.get(card.rank, 0) + 1
        return counts

    def max_same_rank(subset):
        counts = rank_counts(subset)
        return max(counts.values()) if counts else 0

    def pair_count(subset):
        counts = rank_counts(subset)
        return sum(1 for value in counts.values() if value >= 2)

    def face_count(subset):
        return sum(1 for card in subset if card.rank >= 11)

    def low_count(subset):
        return sum(1 for card in subset if card.rank <= 8)

    def stella_sum(subset):
        return sum(getattr(card, "stella", 0) for card in subset)

    def high_card_shape(subset):
        counts = rank_counts(subset)
        return (
            max(counts.values()) == 1
            and not _is_flush(subset)
            and not _is_straight(subset)
        )

    # 1. Best raw scored hands.
    for _, subset in scored_combos[: max(12, int(count * 0.35))]:
        add_subset(subset)

    # 2. Flushes.
    added = 0
    for _, subset in scored_combos:
        if added >= 4:
            break
        if _is_flush(subset) and add_subset(subset):
            added += 1

    # 3. Straights.
    added = 0
    for _, subset in scored_combos:
        if added >= 4:
            break
        if _is_straight(subset) and add_subset(subset):
            added += 1

    # 4. Pair / trips / quads coverage.
    for target_same_rank in (4, 3, 2):
        added = 0
        for _, subset in scored_combos:
            if added >= 4:
                break
            if max_same_rank(subset) >= target_same_rank and add_subset(subset):
                added += 1

    # 5. Two-pair/full-house-ish coverage.
    added = 0
    for _, subset in scored_combos:
        if added >= 4:
            break
        if pair_count(subset) >= 2 and add_subset(subset):
            added += 1

    # 6. High-card engine coverage.
    added = 0
    for _, subset in scored_combos:
        if added >= 4:
            break
        if high_card_shape(subset) and add_subset(subset):
            added += 1

    # 7. Face-card-heavy coverage.
    added = 0
    face_sorted = sorted(
        scored_combos,
        key=lambda x: (face_count(x[1]), x[0]),
        reverse=True,
    )

    for _, subset in face_sorted:
        if added >= 4:
            break
        if face_count(subset) >= 2 and add_subset(subset):
            added += 1

    # 8. Low-card coverage.
    added = 0
    low_sorted = sorted(
        scored_combos,
        key=lambda x: (low_count(x[1]), x[0]),
        reverse=True,
    )

    for _, subset in low_sorted:
        if added >= 4:
            break
        if low_count(subset) >= 4 and add_subset(subset):
            added += 1

    # 9. Stella-heavy coverage.
    added = 0
    stella_sorted = sorted(
        scored_combos,
        key=lambda x: (stella_sum(x[1]), x[0]),
        reverse=True,
    )

    for _, subset in stella_sorted:
        if added >= 4:
            break
        if stella_sum(subset) > 0 and add_subset(subset):
            added += 1

    # 10. Fill with best remaining.
    for _, subset in scored_combos:
        if len(candidates) >= count:
            break
        add_subset(subset)

    return candidates


def _get_synergy_multiplier(joker_classes: List[type]) -> float:
    names = {_joker_name(cls) for cls in joker_classes}
    multiplier = 1.0

    if names & _STELLA_GENERATORS and names & _STELLA_USERS:
        multiplier += 0.45

        if names & {"Supernova", "Galaxy", "Boiling Point", "Starcorn"}:
            multiplier += 0.25

    if names & _RETRIGGERS and names & _PER_CARD_TRIGGERS:
        multiplier += 0.30

    mult_count = len(names & _MULT_MULTIPLIERS)
    if mult_count >= 2:
        multiplier += 0.16 * (mult_count - 1)

    if "UC Socially Dead" in names:
        flat_boosts = {
            "Half Joker",
            "Walkie Talkie",
            "Fibonacci Joker",
            "Dining Hall Prices",
            "Lively Joker",
            "Student ID",
        }

        if names & flat_boosts:
            multiplier += 0.28

    flush_jokers = {
        "The Tribe",
        "Vibrant Joker",
        "Daring Joker",
        "Color Theory",
        "Flower Pot",
    }

    suit_boosters = {
        "Sun God",
        "Heart Joker",
        "Diamond Joker",
        "Club Joker",
        "Spade Joker",
        "Arrowhead",
    }

    if names & flush_jokers and names & suit_boosters:
        multiplier += 0.20

    if "Jam Session" in names and names & _RETRIGGERS:
        multiplier += 0.25

    if "Six Seven" in names or "SixSeven" in names:
        multiplier += 0.14

    if "Blackjack" in names:
        multiplier += 0.10

    return multiplier


def _context_denial_weight(joker_cls: type, opp_picks: List[type]) -> float:
    opp_names = {_joker_name(cls) for cls in opp_picks}
    jname = _joker_name(joker_cls)

    if opp_names & _STELLA_GENERATORS:
        if jname in {"Supernova", "Galaxy", "Boiling Point", "Starcorn"}:
            return 2.8
        if jname in _STELLA_USERS:
            return 2.0

    if opp_names & _STELLA_USERS and jname in _STELLA_GENERATORS:
        return 2.3

    opp_mult_count = len(opp_names & _MULT_MULTIPLIERS)
    if opp_mult_count >= 1 and jname in _MULT_MULTIPLIERS:
        return 1.7 + 0.35 * opp_mult_count

    if opp_names & _RETRIGGERS and jname in _PER_CARD_TRIGGERS:
        return 1.9

    if opp_names & _PER_CARD_TRIGGERS and jname in _RETRIGGERS:
        return 1.8

    if "UC Socially Dead" in opp_names:
        flat_boosts = {
            "Half Joker",
            "Walkie Talkie",
            "Fibonacci Joker",
            "Dining Hall Prices",
            "Lively Joker",
        }

        if jname in flat_boosts:
            return 2.2

    return 1.12


def _effective_denial_weight(
    joker_cls: type,
    opp_picks: List[type],
    base_weight: float,
    cap: float,
) -> float:
    """
    Hybrid denial:
    preserve context-aware spikes, but cap them so the bot does not over-deny.
    """
    return min(base_weight * _context_denial_weight(joker_cls, opp_picks), cap)


def _best_hand_from_candidates(
    candidates: List[List[Card]],
    joker_classes: List[type],
) -> int:
    best_score = 0

    for subset in candidates:
        try:
            score = evaluate_hand(
                [_copy_card(card) for card in subset],
                [cls() for cls in joker_classes],
            )
        except Exception:
            continue

        if score > best_score:
            best_score = score

    return int(best_score * _get_synergy_multiplier(joker_classes))


def _best_hand_exact(cards: List[Card], joker_classes: List[type]) -> tuple[int, List[int]]:
    best_score = -1
    best_indices = list(range(5))
    n = min(PLAYER_CARDS, len(cards))

    if n < 5:
        return 0, []

    for combo in combinations(range(n), 5):
        try:
            score = evaluate_hand(
                [_copy_card(cards[i]) for i in combo],
                [cls() for cls in joker_classes],
            )
        except Exception:
            continue

        if score > best_score:
            best_score = score
            best_indices = list(combo)

    return max(0, best_score), best_indices


class Bot:
    def __init__(self, time_limit: float = 0.185) -> None:
        self.time_limit = time_limit
        self.search_start_time = 0.0

        self.my_candidates: List[List[Card]] = []
        self.opp_candidates: List[List[Card]] = []
        self.approx_cache: dict = {}

        # Hybrid settings.
        self.deny_weight = 0.85
        self.denial_cap = 1.75
        self.self_score_tiebreak = 0.024
        self.tier_bonus_weight = 0.005
        self.candidate_count = 36

    def pick_joker(self, state: GameState) -> int:
        start_time = time.perf_counter()
        self.search_start_time = start_time
        self.approx_cache = {}

        player_turn = state.current_turn

        if player_turn not in (PlayerTurn.PLAYER1, PlayerTurn.PLAYER2):
            return 0

        opp_turn = (
            PlayerTurn.PLAYER2
            if player_turn == PlayerTurn.PLAYER1
            else PlayerTurn.PLAYER1
        )

        my_hand = _hand_for_player(state, player_turn)
        opp_hand = _hand_for_player(state, opp_turn)

        my_picks = _joker_classes_for_player(state, player_turn)
        opp_picks = _joker_classes_for_player(state, opp_turn)

        pool = [_joker_cls_from_model(joker) for joker in state.joker_pool]

        if not pool:
            return 0

        if len(pool) == 1:
            return 0

        my_base, _ = _best_hand_exact(my_hand, my_picks)
        opp_base, _ = _best_hand_exact(opp_hand, opp_picks)

        best_index = 0
        best_swing = -math.inf

        for index, joker_cls in enumerate(pool):
            if time.perf_counter() - start_time > self.time_limit:
                break

            my_score, _ = _best_hand_exact(my_hand, my_picks + [joker_cls])
            opp_score, _ = _best_hand_exact(opp_hand, opp_picks + [joker_cls])

            my_gain = max(0, my_score - my_base)
            opp_gain = max(0, opp_score - opp_base)

            denial_w = _effective_denial_weight(
                joker_cls,
                opp_picks,
                self.deny_weight,
                self.denial_cap,
            )
            joker_tier = _JOKER_TIER.get(_joker_name(joker_cls), 0.5)

            swing = (
                my_gain
                + denial_w * opp_gain
                + self.self_score_tiebreak * my_score
                + self.tier_bonus_weight * joker_tier * max(my_score, opp_score)
            )

            if swing > best_swing:
                best_swing = swing
                best_index = index

        if time.perf_counter() - start_time > self.time_limit:
            return best_index

        self.my_candidates = _get_diverse_candidates(
            my_hand,
            count=self.candidate_count,
            joker_classes=my_picks,
        )

        self.opp_candidates = _get_diverse_candidates(
            opp_hand,
            count=self.candidate_count,
            joker_classes=opp_picks,
        )

        if time.perf_counter() - start_time > self.time_limit:
            return best_index

        best_idx_found = best_index

        try:
            for target_depth in (1, 2, 3, 4, 5):
                _, idx = self._minimax(
                    pool=pool,
                    my_picks=my_picks,
                    opp_picks=opp_picks,
                    my_turn=True,
                    depth=0,
                    target_depth=target_depth,
                    alpha=-math.inf,
                    beta=math.inf,
                )

                if idx is not None:
                    best_idx_found = idx

                if time.perf_counter() - start_time > self.time_limit:
                    break

        except TimeoutError:
            pass

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        if elapsed_ms > 200:
            print(f"WARNING: pick_joker too slow: {elapsed_ms:.2f} ms")

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

    def _approx_score(self, player: str, joker_classes: List[type]) -> int:
        key = (player, tuple(_joker_name(cls) for cls in joker_classes))

        if key in self.approx_cache:
            return self.approx_cache[key]

        candidates = self.my_candidates if player == "me" else self.opp_candidates
        value = _best_hand_from_candidates(candidates, joker_classes)

        self.approx_cache[key] = value
        return value

    def _minimax(
        self,
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
            return float(
                self._approx_score("me", my_picks)
                - self._approx_score("opp", opp_picks)
            ), None

        if depth >= target_depth or not pool:
            return float(
                self._approx_score("me", my_picks)
                - self._approx_score("opp", opp_picks)
            ), None

        # Hybrid beam: aggressive root, controlled deeper.
        k = [8, 6, 4, 3, 2][min(depth, 4)]

        my_base = self._approx_score("me", my_picks)
        opp_base = self._approx_score("opp", opp_picks)

        move_scores = []

        for index, joker_cls in enumerate(pool):
            if time.perf_counter() - self.search_start_time > self.time_limit:
                raise TimeoutError()

            joker_tier = _JOKER_TIER.get(_joker_name(joker_cls), 0.5)

            if my_turn:
                my_score = self._approx_score("me", my_picks + [joker_cls])
                opp_score = self._approx_score("opp", opp_picks + [joker_cls])

                my_gain = max(0, my_score - my_base)
                opp_gain = max(0, opp_score - opp_base)

                denial_w = _effective_denial_weight(
                    joker_cls,
                    opp_picks,
                    self.deny_weight,
                    self.denial_cap,
                )

                val = (
                    my_gain
                    + denial_w * opp_gain
                    + self.self_score_tiebreak * my_score
                    + self.tier_bonus_weight * joker_tier * max(my_score, opp_score)
                )

            else:
                opp_score = self._approx_score("opp", opp_picks + [joker_cls])
                my_score = self._approx_score("me", my_picks + [joker_cls])

                opp_gain = max(0, opp_score - opp_base)
                my_gain = max(0, my_score - my_base)

                denial_w = _effective_denial_weight(
                    joker_cls,
                    my_picks,
                    self.deny_weight,
                    self.denial_cap,
                )

                val = (
                    opp_gain
                    + denial_w * my_gain
                    + self.self_score_tiebreak * opp_score
                    + self.tier_bonus_weight * joker_tier * max(my_score, opp_score)
                )

            move_scores.append((index, val, joker_cls))

        move_scores.sort(key=lambda x: x[1], reverse=True)
        top_moves = move_scores[:k]

        best_idx = None

        if my_turn:
            best_val = -math.inf

            for index, _, joker_cls in top_moves:
                val, _ = self._minimax(
                    pool=pool[:index] + pool[index + 1:],
                    my_picks=my_picks + [joker_cls],
                    opp_picks=opp_picks,
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

        best_val = math.inf

        for index, _, joker_cls in top_moves:
            val, _ = self._minimax(
                pool=pool[:index] + pool[index + 1:],
                my_picks=my_picks,
                opp_picks=opp_picks + [joker_cls],
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