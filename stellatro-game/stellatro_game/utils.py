from .card import Card
from typing import List


def print_card_list(cards: List[Card]) -> None:
    for card in cards:
        print(card, end=" ")
    print()  # newline at the end


def print_jokers(jokers: List) -> None:
    for joker in jokers:
        print(joker, end=" ")
    print()  # newline at the end
