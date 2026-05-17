from typing import List
from .card import RANKS, SUITS, Card
from collections import Counter
from enum import Enum


class HandType(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9


class Checker:
    def __init__(self, hand: List[Card]):
        self.hand = hand

    def is_straight(self, ranks: List[int]) -> bool:
        """Return True if ranks form a straight (supports A-2-3-4-5)."""
        uniq = sorted(set(ranks))
        if len(uniq) != 5:
            return False
        # normal straight
        if uniq[-1] - uniq[0] == 4:
            return True

        # wheel: A,2,3,4,5
        return uniq == [2, 3, 4, 5, 14]

    def check(self) -> HandType:
        """
        Given at most 5 cards, return hand name.
        """
        if len(self.hand) != 5:
            raise ValueError("Hand must contain exactly 5 cards to classify.")

        # for now, each card should only have one rank and one suit
        for c in self.hand:
            c.scored = False  # reset scored status
        ranks = [c.rank for c in self.hand]
        suits = [next(iter(c.suits)) for c in self.hand]

        # rank scoring
        rank_counts = Counter(ranks)
        counts = sorted(rank_counts.values(), reverse=True)

        flush = len(set(suits)) == 1
        straight = self.is_straight(ranks)

        hand_type = HandType.HIGH_CARD

        if straight and flush:
            hand_type = HandType.STRAIGHT_FLUSH
            # score all cards
            for c in self.hand:
                c.scored = True
        elif counts == [4, 1]:
            hand_type = HandType.FOUR_OF_A_KIND
            # score four cards
            most_common_rank = rank_counts.most_common(1)[0][0]
            for c in self.hand:
                if c.rank == most_common_rank:
                    c.scored = True
        elif counts == [3, 2]:
            hand_type = HandType.FULL_HOUSE
            # score all cards
            for c in self.hand:
                c.scored = True
        elif flush:
            hand_type = HandType.FLUSH
            # score all cards
            for c in self.hand:
                c.scored = True
        elif straight:
            hand_type = HandType.STRAIGHT
            # score all cards
            for c in self.hand:
                c.scored = True
        elif counts == [3, 1, 1]:
            hand_type = HandType.THREE_OF_A_KIND
            # score three cards
            most_common_rank = rank_counts.most_common(1)[0][0]
            for c in self.hand:
                if c.rank == most_common_rank:
                    c.scored = True
        elif counts == [2, 2, 1]:
            hand_type = HandType.TWO_PAIR
            # score four cards
            pairs = [rank for rank, count in rank_counts.items() if count == 2]
            for c in self.hand:
                if c.rank in pairs:
                    c.scored = True
        elif counts == [2, 1, 1, 1]:
            hand_type = HandType.PAIR
            # score two cards
            pair_rank = rank_counts.most_common(1)[0][0]
            for c in self.hand:
                if c.rank == pair_rank:
                    c.scored = True
        else:
            # HIGH_CARD: score only the highest-ranked card
            highest_rank = max(ranks)
            for c in self.hand:
                if c.rank == highest_rank:
                    c.scored = True
                    break
        return hand_type
