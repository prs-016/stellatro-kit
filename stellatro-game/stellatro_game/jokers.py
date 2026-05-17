import random
from .card import Card, Rank, Suit, SUITS, rank_to_score
from typing import List, Tuple
from .checker import HandType, Checker
from itertools import product
import math


# Base class for jokers
class Joker:
    name: str
    description: str

    def pre_card_phase(self, hand: List[Card]) -> Tuple[List[Card]]:
        """Return (hand) after pre-phase application of joker."""
        return hand

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        """Return (chips, mult) after hand evaluation application of joker."""
        return chips, mult

    def post_card_phase(
        self, chips: int, mult: int, hand: List[Card]
    ) -> Tuple[int, int]:
        """Return (chips, mult) after post-phase application of joker."""
        return chips, mult

    def scores_all_cards(self) -> bool:
        """Return True when this joker makes every played card score."""
        return False

    def __str__(self) -> str:
        return self.name + ": " + self.description


class RegularJoker(Joker):
    name = "Regular Joker"
    description = "No special abilities."


def _check_hand_type_preserving_scored(hand: List[Card]) -> HandType:
    scored_status = [card.scored for card in hand]
    hand_type = Checker(hand).check()
    for card, scored in zip(hand, scored_status):
        card.scored = scored
    return hand_type


class PairMultBoost(Joker):
    name = "Jolly Joker"
    description = "+4 Mult if the full played hand includes a Pair."

    def post_card_phase(
        self, chips: int, mult: int, hand: List[Card]
    ) -> Tuple[int, int]:
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.PAIR,
            HandType.TWO_PAIR,
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult + 4
        return chips, mult


class PairChipBoost(Joker):
    name = "Sly Joker"
    description = "+20 Chips if the full played hand includes a Pair."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.PAIR,
            HandType.TWO_PAIR,
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips + 20, mult
        return chips, mult


class TripletMultBoost(Joker):
    name = "Zany Joker"
    description = "+8 Mult if the full played hand includes Three of a Kind."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult + 8
        return chips, mult


class TwoPairMultBoost(Joker):
    name = "Cheeky Joker"
    description = "+6 Mult if the full played hand includes Two Pair."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.TWO_PAIR,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult + 6
        return chips, mult


class StraightMultBoost(Joker):
    name = "Witty Joker"
    description = "+10 Mult if the full played hand includes a Straight."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.STRAIGHT,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips, mult + 10
        return chips, mult


class FlushMultBoost(Joker):
    name = "Daring Joker"
    description = "+10 Mult if the full played hand includes a Flush."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.FLUSH,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips, mult + 10
        return chips, mult


class TripletChipBoost(Joker):
    name = "Merry Joker"
    description = "+20 Chips if the full played hand includes Three of a Kind."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips + 20, mult
        return chips, mult


class TwoPairChipBoost(Joker):
    name = "Jovial Joker"
    description = "+18 Chips if the full played hand includes Two Pair."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.TWO_PAIR,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips + 18, mult
        return chips, mult


class StraightChipBoost(Joker):
    name = "Lively Joker"
    description = "+30 Chips if the full played hand includes a Straight."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.STRAIGHT,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips + 30, mult
        return chips, mult


class FlushChipBoost(Joker):
    name = "Vibrant Joker"
    description = "+30 Chips if the full played hand includes a Flush."

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.FLUSH,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips + 30, mult
        return chips, mult


class DiamondMultBoost(Joker):
    name = "Diamond Joker"
    description = "Scored cards with Diamond suit give +4 Mult."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if suit == Suit.DIAMOND:
            return chips, mult + 4
        return chips, mult


class HeartMultBoost(Joker):
    name = "Heart Joker"
    description = "Scored cards with Heart suit give +4 Mult."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if suit == Suit.HEART:
            return chips, mult + 4
        return chips, mult


class ClubMultBoost(Joker):
    name = "Club Joker"
    description = "Scored cards with Club suit give +4 Mult."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if suit == Suit.CLUB:
            return chips, mult + 4
        return chips, mult


class SpadeMultBoost(Joker):
    name = "Spade Joker"
    description = "Scored cards with Spade suit give +4 Mult."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if suit == Suit.SPADE:
            return chips, mult + 4
        return chips, mult

class WalkieTalkie(Joker):
    name = "Walkie Talkie"
    description = "Each scored 10 or 4 gives +10 Chips and +4 Mult when scored."

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        if rank == Rank.TEN or rank == Rank.FOUR:
            return chips + 10, mult + 4
        return chips, mult

class SockAndBuskin(Joker):
    name = "Sock and Buskin"
    description = "Retrigger all scored face cards."

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        for card in hand:
            if card.rank in {Rank.JACK, Rank.QUEEN, Rank.KING}:
                card.add_trigger()
        return hand



class SunGod(Joker):
    name= "Sun God"
    description = "For every heart card scored, get X1.5 Mult"

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        if suit == Suit.HEART:
            return chips, mult * 1.5
        return chips, mult


class EigthCollege(Joker):
    name = "Eigth College"
    description = "Each scored 8 gives +48 chips and +8 Mult when scored"

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        if rank == Rank.EIGHT:
            return chips + 48, mult + 8
        return chips, mult


class PhotoGraphMultBoost(Joker):
    name = "PhotoGraph Joker"
    description = "First scored face card gives X2 Mult when scored"

    def __init__(self):
        self._used_this_hand = False

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        self._used_this_hand = False
        return hand

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if (
            not self._used_this_hand
            and rank in {Rank.JACK, Rank.QUEEN, Rank.KING}
        ):
            self._used_this_hand = True
            return chips, mult * 2
        return chips, mult


class FlowerPot(Joker):
    name = "Flower Pot"
    description = "x3 Mult if the full played hand contains a diamond, heart, spade, and club"

    def post_card_phase(self, chips, mult, hand):
        has_diamond = False
        has_heart = False
        has_club = False
        has_spade = False
        for card in hand:
            if Suit.DIAMOND in card.suits:
                has_diamond = True
            if Suit.HEART in card.suits:
                has_heart = True
            if Suit.CLUB in card.suits:
                has_club = True
            if Suit.SPADE in card.suits:
                has_spade = True
        if has_diamond and has_heart and has_club and has_spade:
            return chips, mult * 3
        return chips, mult


class TheDuo(Joker):
    name = "The Duo"
    description = "If the full played hand contains a pair, x2 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)
        if hand_type in {
            HandType.PAIR,
            HandType.TWO_PAIR,
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult * 2
        return chips, mult


class TheTrio(Joker):
    name = "The Trio"
    description = "If the full played hand contains a Three of a Kind, x2.5 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)

        # Includes hands that contain at least 3 of a kind
        if hand_type in {
            HandType.THREE_OF_A_KIND,
            HandType.FULL_HOUSE,
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult * 2.5
        return chips, mult


class TheFamily(Joker):
    name = "The Family"
    description = "If the full played hand contains a Four of a Kind, x4 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)

        if hand_type in {
            HandType.FOUR_OF_A_KIND,
        }:
            return chips, mult * 4
        return chips, mult


class TheTribe(Joker):
    name = "The Tribe"
    description = "If the full played hand contains a Flush, x3 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)

        # Includes standard flushes and straight flushes
        if hand_type in {
            HandType.FLUSH,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips, mult * 3
        return chips, mult


class TheOrder(Joker):
    name = "The Order"
    description = "If the full played hand contains a Straight, x3 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)

        # Includes standard straights and straight flushes
        if hand_type in {
            HandType.STRAIGHT,
            HandType.STRAIGHT_FLUSH,
        }:
            return chips, mult * 3
        return chips, mult


class TheSingle(Joker):
    name = "UC Socially Dead"
    description = "If the full played hand contains only a High Card, x8 Mult"

    def post_card_phase(self, chips, mult, hand):
        hand_type = _check_hand_type_preserving_scored(hand)

        if hand_type == HandType.HIGH_CARD:
            return chips, mult * 8
        return chips, mult


class BitByte(Joker):
    name = "Bit Byte"
    description = "Face cards give +4 Mult, number cards give +8 Chips."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if rank in {Rank.JACK, Rank.QUEEN, Rank.KING}:  # Face cards
            return chips, mult + 4
        elif rank in {Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN}:  # Number cards
            return chips + 8, mult
        return chips, mult


class StudentID(Joker):
    name = "Student ID"
    description = "If the full played hand contains a single ace and no face cards, +25 Mult, +25 chips"

    def post_card_phase(self, chips, mult, hand):
        has_single_ace = False
        has_face_card = False
        for card in hand:
            if card.rank == Rank.ACE:  # Ace
                if has_single_ace:  # More than one ace
                    return chips, mult
                has_single_ace = True
            elif card.rank in {Rank.JACK, Rank.QUEEN, Rank.KING}:  # Face cards
                has_face_card = True

        if has_single_ace and not has_face_card:
            return chips + 25, mult + 25
        return chips, mult


class Seltzer(Joker):
    name = "Seltzer"
    description = "Retrigger each played card that has rank <= 8"

    def pre_card_phase(self, hand):
        for card in hand:
            if card.rank in {Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX, Rank.SEVEN, Rank.EIGHT}:  # Cards with rank <= 8
                card.add_trigger()
        return hand


class LastLecture(Joker):
    name = "Last Lecture"
    description = "Final played card gets retriggered 2 extra times"

    def pre_card_phase(self, hand):
        if hand:
            hand[-1].add_trigger()
            hand[-1].add_trigger()
        return hand


class DiningHallPrices(Joker):
    name = "Dining Hall Prices"
    description = "Increases played cards with rank 2,3,4,5 by 5"

    def pre_card_phase(self, hand):
        for card in hand:
            if card.rank in {Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE}:
                card.rank += 5
        return hand


class HalfJoker(Joker):
    name = "Half Joker"
    description = "+15 Mult if scored hand is either all <= 8, or >= 9"

    def post_card_phase(
        self, chips: int, mult: int, hand: List[Card]
    ) -> Tuple[int, int]:
        scored_cards = [card for card in hand if card.scored]
        if scored_cards and (
            all(card.rank <= Rank.EIGHT for card in scored_cards)
            or all(card.rank >= Rank.NINE for card in scored_cards)
        ):
            return chips, mult + 15
        return chips, mult


class Fibonacci(Joker):
    name = "Fibonacci Joker"
    description = "Each played Ace, 2, 3, 5, or 8 gives +5 Mult when scored."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if rank == Rank.ACE or rank == Rank.TWO or rank == Rank.THREE or rank == Rank.FIVE or rank == Rank.EIGHT:
            return chips, mult + 5
        return chips, mult


class ScaryFace(Joker):
    name = "Scary Face Joker"
    description = "Each face card gives +30 chips."

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if rank == Rank.JACK or rank == Rank.QUEEN or rank == Rank.KING:
            return chips+30, mult
        return chips, mult

class Mirror(Joker):
    name = "Mirror"
    description = "Face Cards give +20 mult, but -10 chips"

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if rank == Rank.JACK or rank == Rank.QUEEN or rank == Rank.KING:
            return chips - 10, mult + 20
        return chips, mult
    
class Plasma(Joker):
    name = "Plasma"
    description = "Balance chips and mult, diminished return if chips and mult are far apart"

    def post_card_phase(
        self, chips: int, mult: int, hand: List[Card]
    ) -> Tuple[int, int]:
        # 1. Calculate the base balance
        base_balance = (chips + mult) / 2
        
        # 2. Calculate the Ratio Tax component
        # We use max/min to find how 'lopsided' the build is.
        # Adding 1.0 to the denominator to prevent DivisionByZero on empty hands.
        ratio = max(chips, mult) / (min(chips, mult) + 1.0)
        
        # penalty_strength: 0.5 is a square root tax, 1.0 is a linear tax.
        penalty_strength = 0.2
        tax_multiplier = 1.33 / (ratio ** penalty_strength)
        
        # 3. Apply the tax to the balance
        final_value = base_balance * tax_multiplier
        
        return int(final_value), int(final_value)
class StarPlasma(Joker):
    name = "Star Plasma"
    description="Gain 2x stellas in each played card"
    def pre_card_phase(self, hand):
        for card in hand:
            card.add_stella(card.stella)
        return hand
    
class JamSession(Joker):
    name = "Jam Session"
    description = "+6 mult for each extra trigger on scored cards."

    def post_card_phase(self, chips, mult, hand):
        extra_triggers = sum(max(0, card.num_triggers - 1) for card in hand if card.scored)
        return chips, mult + 6 * extra_triggers


class Spotlight(Joker):
    name = "Spotlight"
    description = "First played face card gains +10 Chips and +4 Mult for each other face card in full played hand."

    def __init__(self):
        self._used_this_hand = False
        self._face_support = 0

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        self._used_this_hand = False
        face_cards = sum(1 for card in hand if card.rank in {Rank.JACK, Rank.QUEEN, Rank.KING})
        self._face_support = max(0, face_cards - 1)
        return hand

    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if self._used_this_hand or rank not in {Rank.JACK, Rank.QUEEN, Rank.KING}:
            return chips, mult

        self._used_this_hand = True
        return chips + 10 * self._face_support, mult + 4 * self._face_support


class ColorTheory(Joker):
    name = "Color Theory"
    description = "x1.25 Mult for each additional suit represented in played hand."

    def post_card_phase(self, chips, mult, hand):
        suit_support = max(0, len({suit for card in hand for suit in card.suits}) - 1)
        return chips, mult * (1.25 ** suit_support)


class StudyGroup(Joker):
    name = "Study Group"
    description = "+12 Chips for each distinct rank among scored cards."

    def post_card_phase(self, chips, mult, hand):
        scored_ranks = {card.rank for card in hand if card.scored}
        return chips + 12 * len(scored_ranks), mult


class GroupProject(Joker):
    name = "Group Project"
    description = "+8 Chips and +2 Mult for each scored card with rank 8 or lower."

    def post_card_phase(self, chips, mult, hand):
        low_cards = sum(1 for card in hand if card.scored and card.rank <= Rank.EIGHT)
        return chips + 8 * low_cards, mult + 2 * low_cards


class Encore(Joker):
    name = "Encore"
    description = "Final card gets retriggered once for each other card sharing its suit."

    def pre_card_phase(self, hand):
        if not hand:
            return hand

        final_card = hand[-1]
        matching_cards = sum(
            1
            for card in hand[:-1]
            if not final_card.suits.isdisjoint(card.suits)
        )
        for _ in range(matching_cards):
            hand[-1].add_trigger()
        return hand


class WishUponAStar(Joker):
    name = "Wish Upon a Star"
    description = "Lowest-ranked played card gains 8 Stella before scoring."

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        if not hand:
            return hand

        lowest_rank = min(card.rank for card in hand)
        for card in hand:
            if card.rank == lowest_rank:
                card.add_stella(8)
                break
        return hand


class BinaryStar(Joker):
    name = "Binary Star"
    description = "Even played cards gain 2 stella"

    def pre_card_phase(self, hand):
        if not hand:
            return hand

        for card in hand:
            if card.rank % 2 == 0:
                card.add_stella(2)
                

        return hand


class Pips(Joker):
    name = "Pips"
    description = "Played cards gain stella equal to their rank, but give base 0 chips when scored."

    def pre_card_phase(self, hand):
        for card in hand:
            card.add_stella(rank_to_score(card.rank))

        return hand

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        return chips - rank_to_score(rank), mult


class ReportCard(Joker):
    name = "Report Card"
    description = "Each ace gives the first card in full played hand 11 stella"

    def pre_card_phase(self, hand):
        for card in hand:
            if card.rank == 14:
                for _ in range(11):
                    hand[0].add_stella()
        return hand


class CacheCoherence(Joker):
    name = "Cache Coherence"
    description = "Played cards of the same suit have the same number of stella (max)"

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        if not hand:
            return hand

        max_stella_by_suit: dict[Suit, int] = {}
        for card in hand:
            for suit in card.suits:
                max_stella_by_suit[suit] = max(
                    max_stella_by_suit.get(suit, 0), card.stella
                )

        for card in hand:
            if not card.suits:
                continue
            card.stella = max(
                max_stella_by_suit.get(suit, 0) for suit in card.suits
            )

        return hand


class Stargazing(Joker):
    name = "Stargazing"
    description = "Each played card's stella gives one retrigger"

    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        for card in hand:
            for _ in range(card.stella):
                card.add_trigger()
        return hand


class BoilingPoint(Joker):
    name = "Boiling Point"
    description = "If total number of stella across played cards is greater than 12, x3 Mult"

    def post_card_phase(self, chips, mult, hand):
        total_stella = sum(card.stella for card in hand)
        if total_stella > 12:
            return chips, mult * 3
        return chips, mult


class Galaxy(Joker):
    name = "Galaxy"
    description = "+0.25x Mult per stella across played cards, base 1x Mult"

    def post_card_phase(self, chips, mult, hand):
        total_stella = 0
        for card in hand:
            total_stella += card.stella
        return chips, mult * (1 + total_stella * 0.25)


class Popcorn(Joker):
    name = "Popcorn"
    description = "+30 Mult, -5 per stella on played cards"

    def post_card_phase(self, chips, mult, hand):
        total_stella = 0
        for card in hand:
            total_stella += card.stella
        m = max(0, 30 - 5*total_stella)
        return chips, mult + m

class Starcorn(Joker):
    name="Starcorn"
    description="Each card gives (rank * stella) mult"
    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        return chips, mult + rank * stella

class Supernova(Joker):
    name = "Supernova"
    description = "Each card with stella gives x(1.1)^stella mult when scored."

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        if stella <= 0:
            return chips, mult
        return chips, mult * (1.1 ** stella)

class Snowball(Joker):
    name="Snowball"
    description="+40 Chips per stella on played cards"
    def post_card_phase(self, chips, mult, hand):
        total_stella = 0
        for card in hand:
            total_stella += card.stella
        return chips+40*total_stella,mult


class Constellation(Joker):
    name = "Constellation"
    description = "Gain +8 chips and +3 mult for each Stella on scored cards."

    def post_card_phase(self, chips, mult, hand):
        total_stella = sum(card.stella for card in hand if card.scored)
        return chips + 8 * total_stella, mult + 3 * total_stella

class Arrowhead(Joker):
    name = "Arrowhead"
    description = "Played cards with Spade suit give +18 Chips."
    def apply_card_phase(
        self, chips: int, mult: int, rank: Rank, suit: Suit, stella: int = 0
    ) -> Tuple[int, int]:
        if suit == Suit.SPADE:
            return chips + 18, mult
        return chips, mult

class LossCut(Joker):
    name="Loss Cut"
    description="For every card that wasn't scored, gain +30 Chips."
    def post_card_phase(self, chips, mult, hand):
        for card in hand:
            if not card.scored:
                chips += 30
        return chips,mult

class LockIn(Joker):
    name = "Lock In"
    description = "All played cards score, no matter what hand is played."

    def scores_all_cards(self) -> bool:
        return True

class Starjack(Joker):
    name="Starjack"
    description="The first face card gains 10 stella."
    def pre_card_phase(self, hand: List[Card]) -> List[Card]:
        if not hand:
            return hand
        for c in hand:
            if c.rank >= 11 and c.rank < 14:
                c.add_stella(10)
                break
        return hand
class Blackjack(Joker):
    name="Blackjack"
    description="x4 Mult if all played cards' score adds up to 21."
    def post_card_phase(self, chips, mult, hand):
        played_total = sum(rank_to_score(card.rank) for card in hand)
        if played_total == 21:
            return chips, mult * 4
        return chips, mult

class SixSeven(Joker):
    name="Six Seven"
    description="If the full played hand contains a 6 and a 7, gain +67 Mult"
    def post_card_phase(self, chips, mult, hand):
        has_6 = any(card.rank == 6 for card in hand)
        has_7 = any(card.rank == 7 for card in hand)
        if has_6 and has_7:
            return chips, mult + 67
        return chips,mult

class ThriceTwice(Joker):
    name="Thrice Twice"
    description="If the full played hand contains a Full House, each card gains 3 stella"
    def pre_card_phase(self, hand):
        checker = Checker(hand)
        hand_type = checker.check()
        if hand_type == HandType.FULL_HOUSE:
            for card in hand:
                card.add_stella(3)
        return hand

class FallenStar(Joker):
    name = "Fallen Star"
    description = "Lowest scored card gains stella equal to the highest scored rank, and highest scored card gains stella equal to the lowest scored rank."

    def pre_card_phase(self, hand):
        checker = Checker(hand)
        checker.check()

        scored_cards = [card for card in hand if card.scored]
        if not scored_cards:
            return hand

        lowest_card = min(scored_cards, key=lambda card: card.rank)
        highest_card = max(scored_cards, key=lambda card: card.rank)

        if lowest_card is highest_card:
            lowest_card.add_stella(lowest_card.rank)
            return hand

        lowest_card.add_stella(highest_card.rank)
        highest_card.add_stella(lowest_card.rank)
        return hand

class StarFish(Joker):
    name = "Star Fish"
    description = "Scored cards in pairs gain +2 stella, triplets gain +4 stella, and quads gain +8 stella."

    def pre_card_phase(self, hand):
        checker = Checker(hand)
        checker.check()

        scored_cards = [card for card in hand if card.scored]
        rank_counts = {}
        for card in scored_cards:
            rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1

        stella_by_count = {
            2: 2,
            3: 4,
            4: 8,
        }
        for card in scored_cards:
            stella = stella_by_count.get(rank_counts[card.rank], 0)
            if stella:
                card.add_stella(stella)

        return hand

class BranchOut(Joker):
    name="Branch Out"
    description="Each played card carries half of the previous played card's stella."
    def pre_card_phase(self, hand):
        previous_card = None
        for card in hand:
            if previous_card is not None:
                card.add_stella(previous_card.stella // 2)
            previous_card = card
        return hand

class Anya(Joker):
    name = "Anya"
    description = "Each scored card gives +4 Mult for every other played card sharing its rank or suit."

    def pre_card_phase(self, hand):
        self.hand = hand
        return hand

    def apply_card_phase(self, chips, mult, rank, suit, stella=0):
        matching_cards = 0
        for card in getattr(self, "hand", []):
            if card.rank == rank or suit in card.suits:
                matching_cards += 1
        return chips, mult + 4 * max(0, matching_cards - 1)

# Straightforward hand/suit condition boosts.
GENERIC_HAND_SUIT_BOOST_JOKER_CLASSES = [
    PairMultBoost,
    PairChipBoost,
    TripletMultBoost,
    TwoPairMultBoost,
    StraightMultBoost,
    FlushMultBoost,
    TripletChipBoost,
    TwoPairChipBoost,
    StraightChipBoost,
    FlushChipBoost,
    DiamondMultBoost,
    HeartMultBoost,
    ClubMultBoost,
    SpadeMultBoost,
    Arrowhead,
]


NON_STELLA_JOKER_CLASSES = [
    RegularJoker,
    WalkieTalkie,
    SockAndBuskin,
    SunGod,
    EigthCollege,
    PhotoGraphMultBoost,
    FlowerPot,
    TheDuo,
    TheTrio,
    TheTribe,
    TheOrder,
    TheSingle,
    BitByte,
    StudentID,
    Seltzer,
    LastLecture,
    DiningHallPrices,
    HalfJoker,
    Fibonacci,
    ScaryFace,
    Mirror,
    Plasma,
    JamSession,
    Spotlight,
    ColorTheory,
    StudyGroup,
    GroupProject,
    Encore,
    LossCut,
    LockIn,
    Blackjack,
    SixSeven,
    Anya,
]


STELLA_GENERATING_JOKER_CLASSES = [
    WishUponAStar,
    BinaryStar,
    Pips,
    ReportCard,
    Starjack,
    ThriceTwice,
    FallenStar,
    StarFish,
]


STELLA_PROPAGATING_JOKER_CLASSES = [
    CacheCoherence,
    StarPlasma,
    BranchOut,
]


STELLA_USING_JOKER_CLASSES = [
    Stargazing,
    BoilingPoint,
    Galaxy,
    Popcorn,
    Constellation,
    Starcorn,
    Supernova,
    Snowball,
]


# currently 67 active jokers
ALL_JOKER_CLASSES = (
    GENERIC_HAND_SUIT_BOOST_JOKER_CLASSES
    + NON_STELLA_JOKER_CLASSES
    + STELLA_GENERATING_JOKER_CLASSES
    + STELLA_PROPAGATING_JOKER_CLASSES
    + STELLA_USING_JOKER_CLASSES
)


def _instantiate_joker(joker_cls, rng=None) -> Joker:
    if rng is not None:
        try:
            return joker_cls(rng=rng)
        except TypeError:
            pass
    return joker_cls()


def generate_jokers(num_jokers: int, rng=None) -> List[Joker]:
    if num_jokers < 2:
        raise ValueError(
            "num_jokers must be at least 2 to guarantee one stella-generating joker and one stella-using joker."
        )

    shuffler = rng or random
    required_classes = [
        shuffler.choice(STELLA_GENERATING_JOKER_CLASSES),
        shuffler.choice(STELLA_USING_JOKER_CLASSES),
    ]

    joker_classes = [
        joker_cls for joker_cls in ALL_JOKER_CLASSES if joker_cls not in required_classes
    ]
    shuffler.shuffle(joker_classes)

    selected_classes = required_classes[:]
    while len(selected_classes) < num_jokers:
        if not joker_classes:
            joker_classes = ALL_JOKER_CLASSES[:]
            shuffler.shuffle(joker_classes)
        selected_classes.append(joker_classes.pop())

    shuffler.shuffle(selected_classes)
    return [
        _instantiate_joker(joker_cls, rng=rng)
        for joker_cls in selected_classes
    ]
