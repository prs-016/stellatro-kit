# include the main logic of the game
from copy import deepcopy
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from .jokers import Joker, generate_jokers, ALL_JOKER_CLASSES
from .card import Card, Deck, Suit, rank_to_score
from .checker import Checker, HandType
from .utils import print_card_list, print_jokers
from stellatro_common import Phase, PlayerTurn, CardModel, JokerModel, GameState

JOKER_POOL_SIZE = 15
JOKER_HAND_SIZE = 5
PLAYER_CARDS = 10
SCORE_SCALE = 10_000.0

HAND_SCORES = {
    HandType.HIGH_CARD: (10, 1),
    HandType.PAIR: (20, 1),
    HandType.TWO_PAIR: (30, 2),
    HandType.THREE_OF_A_KIND: (40, 2),
    HandType.STRAIGHT: (60, 3),
    HandType.FLUSH: (70, 3),
    HandType.FULL_HOUSE: (90, 4),
    HandType.FOUR_OF_A_KIND: (120, 5),
    HandType.STRAIGHT_FLUSH: (160, 6),  # optional, included
}

# Card encoding constants
NUM_RANKS = 13  # 2..14 mapped to 0..12
NUM_SUITS = 4
CARD_DIM = NUM_RANKS + NUM_SUITS  # 17

# Build joker type registry from ALL_JOKER_CLASSES
JOKER_TYPE_TO_IDX: Dict[type, int] = {cls: i for i, cls in enumerate(ALL_JOKER_CLASSES)}
NUM_JOKER_TYPES = len(ALL_JOKER_CLASSES)
MAX_JOKERS_PER_PLAYER = (JOKER_POOL_SIZE + 1) // 2  # 8 for pool of 15

# Precompute all C(10,5) = 252 five-card combinations
ALL_5_CARD_COMBOS = list(combinations(range(PLAYER_CARDS), 5))


class GameSetup:
    """Snapshot of a deal (hands + joker pool) used to seed multiple game variants identically."""

    def __init__(self, p1_hand: List[Card], p2_hand: List[Card], joker_pool: List[Joker]):
        self.p1_hand = p1_hand
        self.p2_hand = p2_hand
        self.joker_pool = joker_pool

    @classmethod
    def generate(cls, rng=None) -> "GameSetup":
        """Generate a random deal by running start_round() on a throwaway game."""
        game = Game(verbose=False, rng=rng)
        game.start_round()
        return cls(
            p1_hand=deepcopy(game.p1hand),
            p2_hand=deepcopy(game.p2hand),
            joker_pool=deepcopy(game.jokers),
        )


class Game:
    def __init__(self, verbose: bool = True, draft_until_empty: bool = False, rng=None):
        self.verbose = verbose
        self.draft_until_empty = draft_until_empty
        self.rng = rng
        self.player1_score = 0
        self.player2_score = 0
        self.phase = Phase.DRAFT
        self.draft_turn = 0
        self.jokers = []
        self.p1hand = []
        self.p2hand = []
        self.p1jokers = []
        self.p2jokers = []
        self.current_turn = PlayerTurn.PLAYER1

    def evaluate_hand(self, hand: List[Card], jokers: List[Joker]) -> int:

        # before we find out what hand we have, apply the pre-phase jokers
        for c in hand:
            c.scored = False  # reset scored status
            c.stella = 0  # reset per-hand stella state
        # apply each pre-phase joker
        for joker in jokers:
            hand = joker.pre_card_phase(hand)

        # then, check our hand type so we get our base chips and mult
        checker = Checker(hand)
        hand_type = checker.check()
        if any(joker.scores_all_cards() for joker in jokers):
            for card in hand:
                card.scored = True

        # debugging
        if self.verbose:
            print(hand_type)
            print_card_list(hand)
            print_jokers(jokers)

        chips, mult = HAND_SCORES.get(hand_type, (0, 0))
        if self.verbose:
            print(chips, mult)

        # for each card...
        for card in hand:
            # if the card is scored...
            if card.scored:
                # then for each time the card triggers...
                for _ in range(card.num_triggers):
                    # apply each card-phase joker
                    chips += rank_to_score(card.rank)
                    for joker in jokers:
                        chips, mult = joker.apply_card_phase(
                            chips, mult, card.rank, next(iter(card.suits)), card.stella
                        )

        # apply each post-phase joker
        for joker in jokers:
            chips, mult = joker.post_card_phase(chips, mult, hand)
        if self.verbose:
            print(chips, mult)
        return chips * mult

    def load_setup(self, setup: "GameSetup", swap_hands: bool = False):
        """Reset game state and inject a pre-generated deal (no randomness)."""
        self.phase = Phase.DRAFT
        self.draft_turn = 0
        self.player1_score = 0
        self.player2_score = 0
        self.p1jokers = []
        self.p2jokers = []
        self.current_turn = PlayerTurn.PLAYER1
        if swap_hands:
            self.p1hand = deepcopy(setup.p2_hand)
            self.p2hand = deepcopy(setup.p1_hand)
        else:
            self.p1hand = deepcopy(setup.p1_hand)
            self.p2hand = deepcopy(setup.p2_hand)
        self.jokers = deepcopy(setup.joker_pool)

    def start_round(self, rng=None):
        # start the game
        if rng is not None:
            self.rng = rng
        self.phase = Phase.DRAFT
        self.draft_turn = 0
        self.player1_score = 0
        self.player2_score = 0
        self.p1jokers = []
        self.p2jokers = []
        self.current_turn = PlayerTurn.PLAYER1
        if self.verbose:
            print("Game started between Player 1 and Player 2")

        # 1. generate deck for both players
        game_deck = Deck(rng=self.rng)
        self.p1hand = game_deck.draw(PLAYER_CARDS)
        self.p2hand = game_deck.draw(PLAYER_CARDS)

        # 2. generate jokers
        self.jokers = generate_jokers(JOKER_POOL_SIZE, rng=self.rng)

        # 3. set turn
        self.current_turn = PlayerTurn.PLAYER1

    def get_game_state(self) -> GameState:
        def card_to_model(c: Card) -> CardModel:
            return CardModel(
                rank=c.rank,
                suits=sorted([s.value for s in c.suits]),
                scored=c.scored,
                num_triggers=c.num_triggers,
                stella=c.stella,
            )

        def joker_to_model(j: Joker) -> JokerModel:
            return JokerModel(name=j.name, description=j.description)

        return GameState(
            phase=self.phase,
            current_turn=self.current_turn,
            player1_hand=[card_to_model(c) for c in self.p1hand],
            player2_hand=[card_to_model(c) for c in self.p2hand],
            joker_pool=[joker_to_model(j) for j in self.jokers],
            player1_jokers=[joker_to_model(j) for j in self.p1jokers],
            player2_jokers=[joker_to_model(j) for j in self.p2jokers],
            player1_score=self.player1_score,
            player2_score=self.player2_score,
        )

    def step(
        self,
        player: int,
        action: Optional[int] = None,
        hand_list: Optional[List[int]] = None,
    ) -> Tuple:
        if player not in (1, 2):
            print(f"Invalid player id: {player}")
            return (False, self.get_game_state())

        # check if the player is correct in the first place
        if (player == 1 and self.current_turn != PlayerTurn.PLAYER1) or (
            player == 2 and self.current_turn != PlayerTurn.PLAYER2
        ):
            print(f"Player {player} tried to play out of turn!")
            return (False, self.get_game_state())

        # draft phase
        if self.phase == Phase.DRAFT:
            if action is None:
                print(f"Player {player} did not provide an action!")
                return (False, self.get_game_state())

            if not isinstance(action, int) or isinstance(action, bool):
                print(f"Player {player} provided a non-integer draft action!")
                return (False, self.get_game_state())

            if action < 0 or action >= len(self.jokers):
                print(f"Player {player} tried to pick an invalid joker!")
                return (False, self.get_game_state())

            if player == 1:
                picked_joker = self.jokers.pop(action)
                self.p1jokers.append(picked_joker)
                self.current_turn = PlayerTurn.PLAYER2
            else:
                picked_joker = self.jokers.pop(action)
                self.p2jokers.append(picked_joker)
                self.current_turn = PlayerTurn.PLAYER1
                self.draft_turn += 1

            # check if draft phase is over
            draft_done = (
                len(self.jokers) == 0
                if self.draft_until_empty
                else self.draft_turn >= JOKER_HAND_SIZE
            )
            if draft_done:
                self.phase = Phase.PLAY
                self.current_turn = PlayerTurn.PLAYER1
            return (True, self.get_game_state())

        # play phase
        elif self.phase == Phase.PLAY:
            if hand_list is None:
                print(f"Player {player} did not provide a hand to play!")
                return (False, self.get_game_state())

            if not isinstance(hand_list, list):
                print(f"Player {player} provided an invalid hand payload!")
                return (False, self.get_game_state())

            if len(hand_list) != 5:
                print(f"Player {player} provided an invalid number of cards!")
                return (False, self.get_game_state())

            if any(
                (not isinstance(card_index, int)) or isinstance(card_index, bool)
                for card_index in hand_list
            ):
                print(f"Player {player} provided non-integer card indices!")
                return (False, self.get_game_state())

            if len(hand_list) != len(set(hand_list)):
                print(f"Player {player} provided duplicate cards!")
                return (False, self.get_game_state())

            hand_size = len(self.p1hand) if player == 1 else len(self.p2hand)
            for card_index in hand_list:
                if (
                    card_index < 0
                    or card_index >= PLAYER_CARDS
                    or card_index >= hand_size
                ):
                    print(f"Player {player} provided an out-of-range card index!")
                    return (False, self.get_game_state())

            if player == 1:
                played_hand = [self.p1hand[i] for i in hand_list]
                try:
                    round_score = self.evaluate_hand(played_hand, self.p1jokers)
                except Exception as exc:
                    print(f"Player {player} hand evaluation failed: {exc}")
                    return (False, self.get_game_state())
                self.player1_score += round_score
                self.current_turn = PlayerTurn.PLAYER2
                return (True, self.get_game_state())
            else:
                played_hand = [self.p2hand[i] for i in hand_list]
                try:
                    round_score = self.evaluate_hand(played_hand, self.p2jokers)
                except Exception as exc:
                    print(f"Player {player} hand evaluation failed: {exc}")
                    return (False, self.get_game_state())
                self.player2_score += round_score
                self.phase = Phase.OVER
                self.current_turn = None
                return (True, self.get_game_state())

        elif self.phase == Phase.OVER:
            return (False, self.get_game_state())
        else:
            print("Invalid game phase!")
            return (False, self.get_game_state())

    def auto_score(self) -> Tuple[int, int]:
        """Exhaustively evaluate all C(10,5) hands for each player, return best scores."""
        best_p1 = 0
        for combo in ALL_5_CARD_COMBOS:
            hand = [Card(self.p1hand[i].rank, next(iter(self.p1hand[i].suits))) for i in combo]
            try:
                score = self.evaluate_hand(hand, deepcopy(self.p1jokers))
                if score > best_p1:
                    best_p1 = score
            except Exception:
                continue

        best_p2 = 0
        for combo in ALL_5_CARD_COMBOS:
            hand = [Card(self.p2hand[i].rank, next(iter(self.p2hand[i].suits))) for i in combo]
            try:
                score = self.evaluate_hand(hand, deepcopy(self.p2jokers))
                if score > best_p2:
                    best_p2 = score
            except Exception:
                continue

        self.player1_score = best_p1
        self.player2_score = best_p2
        self.phase = Phase.OVER
        self.current_turn = None
        return best_p1, best_p2

    def _encode_card(self, card: Card):
        import torch
        """Encode a single card as a 17-dim one-hot vector (13 rank + 4 suit)."""
        vec = torch.zeros(CARD_DIM)
        vec[card.rank - 2] = 1.0  # rank 2..14 -> index 0..12
        suit_order = [Suit.DIAMOND, Suit.HEART, Suit.CLUB, Suit.SPADE]
        for s in card.suits:
            vec[NUM_RANKS + suit_order.index(s)] = 1.0
        return vec

    def _encode_joker(self, joker: Joker):
        import torch
        """Encode a joker as a one-hot vector over all joker types."""
        vec = torch.zeros(NUM_JOKER_TYPES)
        idx = JOKER_TYPE_TO_IDX.get(type(joker), -1)
        if idx >= 0:
            vec[idx] = 1.0
        return vec

    def encode_state(self, player: int) -> Dict[str, Any]:
        import torch
        """Return numeric encoding of the game state from a given player's perspective."""
        if player not in (1, 2):
            raise ValueError(f"Invalid player: {player}")

        if player == 1:
            my_hand, opp_hand = self.p1hand, self.p2hand
            my_jokers, opp_jokers = self.p1jokers, self.p2jokers
            my_score, opp_score = self.player1_score, self.player2_score
        else:
            my_hand, opp_hand = self.p2hand, self.p1hand
            my_jokers, opp_jokers = self.p2jokers, self.p1jokers
            my_score, opp_score = self.player2_score, self.player1_score

        # Encode hands (padded to PLAYER_CARDS)
        my_hand_enc = torch.zeros(PLAYER_CARDS, CARD_DIM)
        for i, c in enumerate(my_hand):
            my_hand_enc[i] = self._encode_card(c)

        opp_hand_enc = torch.zeros(PLAYER_CARDS, CARD_DIM)
        for i, c in enumerate(opp_hand):
            opp_hand_enc[i] = self._encode_card(c)

        # Encode available jokers (padded to JOKER_POOL_SIZE)
        avail_enc = torch.zeros(JOKER_POOL_SIZE, NUM_JOKER_TYPES)
        for i, j in enumerate(self.jokers):
            avail_enc[i] = self._encode_joker(j)

        # Encode owned jokers (padded to MAX_JOKERS_PER_PLAYER)
        my_jokers_enc = torch.zeros(MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)
        for i, j in enumerate(my_jokers):
            my_jokers_enc[i] = self._encode_joker(j)

        opp_jokers_enc = torch.zeros(MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)
        for i, j in enumerate(opp_jokers):
            opp_jokers_enc[i] = self._encode_joker(j)

        # Scalar features
        phase_enc = torch.zeros(2)
        phase_enc[0 if self.phase == Phase.DRAFT else 1] = 1.0

        jokers_remaining = torch.tensor([len(self.jokers) / JOKER_POOL_SIZE])
        scores = torch.tensor(
            [float(my_score) / SCORE_SCALE, float(opp_score) / SCORE_SCALE]
        )

        return {
            "my_hand": my_hand_enc,
            "opponent_hand": opp_hand_enc,
            "available_jokers": avail_enc,
            "my_jokers": my_jokers_enc,
            "opponent_jokers": opp_jokers_enc,
            "phase": phase_enc,
            "jokers_remaining": jokers_remaining,
            "scores": scores,
        }


def evaluate_hand(hand: List[Card], jokers: List[Joker]) -> int:
    """
    Convenience wrapper to evaluate a hand with jokers without
    needing a full Game instance from the caller's perspective.

    This mirrors the logic in Game.evaluate_hand and is primarily
    used by bots and simulations.
    """
    game = Game(verbose=False)
    return game.evaluate_hand(hand, jokers)
