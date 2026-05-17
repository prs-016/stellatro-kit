from typing import List
import random
from dataclasses import dataclass
from enum import Enum, IntEnum


class Suit(Enum):
    DIAMOND = "diamond"
    HEART = "heart"
    CLUB = "club"
    SPADE = "spade"


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


RANKS = list(range(2, 15))  # 11=J, 12=Q, 13=K, 14=A
SUITS = [Suit.DIAMOND, Suit.HEART, Suit.CLUB, Suit.SPADE]
RANK_TO_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}


def rank_to_score(rank: int) -> int:
    if 2 <= rank <= 10:
        return rank
    if 11 <= rank <= 13:
        return 10
    if rank == 14:
        return 11
    raise ValueError(f"Invalid card rank: {rank}")


class Card:
    rank: int
    suits: set[Suit]
    scored: bool = True
    num_triggers = 1
    stella = 0

    def __init__(self, rank: int, suit: Suit):
        # Initialize as sets using curly braces
        self.rank = rank
        self.suits = {suit}
        self.stella = 0

    def add_suit(self, suit: Suit):
        # Use .add() for sets
        self.suits.add(suit)

    def add_trigger(self):
        self.num_triggers += 1

    def add_stella(self, amount: int = 1):
        self.stella += amount

    def spend_stella(self, amount: int = 1) -> int:
        spent = min(self.stella, amount)
        self.stella -= spent
        return spent

    def clear_stella(self):
        self.stella = 0

    def __str__(self):
        rank_str = RANK_TO_STR.get(self.rank, str(self.rank))
        suits_list = sorted([s.value for s in self.suits])
        suits_str = ", ".join(suits_list)
        stella_suffix = f" [{self.stella} stella]" if self.stella else ""
        return f"{rank_str} of {suits_str}{stella_suffix}"


class Deck:
    def __init__(self, rng=None):
        self._rng = rng or random
        self.cards = [Card(r, s) for s in SUITS for r in RANKS]
        self._rng.shuffle(self.cards)

    def draw(self, n: int) -> List[Card]:
        if len(self.cards) < n:
            # simple reshuffle behavior: rebuild new deck when low
            self.__init__(rng=self._rng)
        out = self.cards[:n]
        self.cards = self.cards[n:]
        return out
