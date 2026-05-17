class Bot:
    STELLA_GENERATORS = {
        "Wish Upon a Star",
        "Binary Star",
        "Pips",
        "Report Card",
        "Cache Coherence",
        "Fallen Star",
        "Star Fish",
    }

    STELLA_PAYOFFS = {
        "Stargazing",
        "Boiling Point",
        "Galaxy",
        "Popcorn",
        "Starcorn",
        "Supernova",
        "Snowball",
        "Constellation",
        "Star Plasma",
        "Starjack",
    }

    DRAFT_PRIORITIES = {
        "PhotoGraph Joker": 1200,
        "The Family": 1150,
        "The Tribe": 1050,
        "The Order": 1050,
        "The Trio": 1000,
        "Flower Pot": 950,
        "The Duo": 900,
        "UC Socially Dead": 850,
        "Student ID": 820,
        "Sock and Buskin": 780,
        "Seltzer": 760,
        "Last Lecture": 740,
        "Encore": 725,
        "Sun God": 710,
        "Scary Face Joker": 700,
        "Fibonacci Joker": 690,
        "Walkie Talkie": 680,
        "Eigth College": 670,
        "Bit Byte": 650,
        "Half Joker": 630,
        "Mirror": 620,
        "Plasma": 610,
        "Color Theory": 600,
        "Group Project": 590,
        "Study Group": 580,
        "Jolly Joker": 500,
        "Sly Joker": 490,
        "Zany Joker": 520,
        "Merry Joker": 510,
        "Cheeky Joker": 500,
        "Jovial Joker": 490,
        "Witty Joker": 530,
        "Lively Joker": 520,
        "Daring Joker": 535,
        "Vibrant Joker": 525,
        "Diamond Joker": 450,
        "Heart Joker": 450,
        "Club Joker": 450,
        "Spade Joker": 450,
    }

    HAND_SCORES = {
        "HIGH_CARD": (10, 1),
        "PAIR": (20, 1),
        "TWO_PAIR": (30, 2),
        "THREE_OF_A_KIND": (40, 2),
        "STRAIGHT": (60, 3),
        "FLUSH": (70, 3),
        "FULL_HOUSE": (90, 4),
        "FOUR_OF_A_KIND": (120, 5),
        "STRAIGHT_FLUSH": (160, 6),
    }

    def pick_joker(self, state):
        pool = state.joker_pool
        if not pool:
            return 0

        my_jokers = self._my_jokers(state)
        my_names = {joker.name for joker in my_jokers}

        if not (my_names & self.STELLA_GENERATORS):
            generator_pick = self._best_named_pick(pool, self.STELLA_GENERATORS)
            if generator_pick is not None:
                return generator_pick

        if my_names & self.STELLA_GENERATORS:
            payoff_pick = self._best_named_pick(pool, self.STELLA_PAYOFFS)
            if payoff_pick is not None:
                return payoff_pick

        hand = self._my_hand(state)
        best_index = 0
        best_score = -1
        for index, joker in enumerate(pool):
            trial_jokers = list(my_jokers) + [joker]
            score, _ = self._best_hand(hand, trial_jokers)
            score += self.DRAFT_PRIORITIES.get(joker.name, 0)
            if score > best_score:
                best_score = score
                best_index = index
        return best_index

    def pick_hand(self, state):
        hand = self._my_hand(state)
        jokers = self._my_jokers(state)
        _, indices = self._best_hand(hand, jokers)
        return indices

    def pick_play_hand(self, state):
        return self.pick_hand(state)

    def _best_named_pick(self, pool, names):
        best_index = None
        best_value = -1
        for index, joker in enumerate(pool):
            if joker.name in names:
                value = self.DRAFT_PRIORITIES.get(joker.name, 0)
                if value > best_value:
                    best_value = value
                    best_index = index
        return best_index

    def _my_hand(self, state):
        return state.player1_hand if str(state.current_turn).endswith("PLAYER1") else state.player2_hand

    def _my_jokers(self, state):
        return state.player1_jokers if str(state.current_turn).endswith("PLAYER1") else state.player2_jokers

    def _best_hand(self, cards, jokers):
        n = len(cards)
        if n < 5:
            return 0, list(range(n))

        best_score = -1
        best_indices = [0, 1, 2, 3, 4]
        for a in range(n - 4):
            for b in range(a + 1, n - 3):
                for c in range(b + 1, n - 2):
                    for d in range(c + 1, n - 1):
                        for e in range(d + 1, n):
                            indices = [a, b, c, d, e]
                            hand = [cards[i] for i in indices]
                            score = self._score_hand(hand, jokers)
                            if score > best_score:
                                best_score = score
                                best_indices = indices
        return best_score, best_indices

    def _score_hand(self, hand, jokers):
        hand_type, scored = self._classify(hand)
        chips, mult = self.HAND_SCORES[hand_type]
        triggers = [1, 1, 1, 1, 1]
        stella = [0, 0, 0, 0, 0]
        names = [joker.name for joker in jokers]

        for name in names:
            if name == "Wish Upon a Star":
                low = min(card.rank for card in hand)
                for i, card in enumerate(hand):
                    if card.rank == low:
                        stella[i] += 8
                        break
            elif name == "Binary Star":
                for i, card in enumerate(hand):
                    if card.rank % 2 == 0:
                        stella[i] += 2
            elif name == "Pips":
                for i, card in enumerate(hand):
                    stella[i] += card.rank
            elif name == "Report Card":
                aces = 0
                for card in hand:
                    if card.rank == 14:
                        aces += 1
                stella[0] += aces * 11
            elif name == "Seltzer":
                for i, card in enumerate(hand):
                    if card.rank <= 8:
                        triggers[i] += 1
            elif name == "Last Lecture":
                final_scored = self._final_scored_index(scored)
                if final_scored is not None:
                    triggers[final_scored] += 2
            elif name == "Encore":
                final_scored = self._final_scored_index(scored)
                if final_scored is not None:
                    suit = self._suit(hand[final_scored])
                    for i, card in enumerate(hand):
                        if i != final_scored and self._suit(card) == suit:
                            triggers[final_scored] += 1
            elif name == "Sock and Buskin":
                for i, card in enumerate(hand):
                    if scored[i] and card.rank >= 11:
                        triggers[i] += 1
            elif name == "Stargazing":
                for i in range(5):
                    triggers[i] += stella[i]

        for i, card in enumerate(hand):
            if not scored[i]:
                continue
            for _ in range(triggers[i]):
                add_chips = self._rank_score(card.rank)
                if "Pips" in names:
                    add_chips = 0
                if "Dining Hall Prices" in names and card.rank in (2, 3, 4, 5):
                    add_chips += 5
                if "Scary Face Joker" in names and card.rank >= 11:
                    add_chips += 30
                if "Mirror" in names and card.rank >= 11:
                    add_chips = 0
                    mult += 50
                chips += add_chips

                suit = self._suit(card)
                if "Diamond Joker" in names and suit == "diamond":
                    mult += 2
                if "Heart Joker" in names and suit == "heart":
                    mult += 2
                if "Club Joker" in names and suit == "club":
                    mult += 2
                if "Spade Joker" in names and suit == "spade":
                    mult += 2
                if "Arrowhead" in names and suit == "spade":
                    chips += 18
                if "Walkie Talkie" in names and card.rank in (4, 10):
                    chips += 10
                    mult += 4
                if "Eigth College" in names and card.rank == 8:
                    chips += 80
                    mult += 8
                if "PhotoGraph Joker" in names and card.rank >= 11 and not self._seen_face_before(hand, scored, i):
                    mult *= 2
                if "Fibonacci Joker" in names and card.rank in (2, 3, 5, 8, 14):
                    mult += 5
                if "Bit Byte" in names:
                    if card.rank >= 11:
                        mult += 2
                    else:
                        chips += 8
                if "Group Project" in names and card.rank <= 8:
                    chips += 8
                    mult += 2
                if "Supernova" in names and stella[i] > 0:
                    mult *= 1.1 ** stella[i]
                if "Constellation" in names:
                    chips += 8 * stella[i]
                    mult += 3 * stella[i]

        chips, mult = self._post_score(hand, hand_type, scored, stella, chips, mult, names)
        return int(chips * mult)

    def _post_score(self, hand, hand_type, scored, stella, chips, mult, names):
        if "Jolly Joker" in names and hand_type in ("PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            mult += 3
        if "Sly Joker" in names and hand_type in ("PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            chips += 10
        if "Zany Joker" in names and hand_type in ("THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            mult += 5
        if "Merry Joker" in names and hand_type in ("THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            chips += 15
        if "Cheeky Joker" in names and hand_type in ("TWO_PAIR", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            mult += 4
        if "Jovial Joker" in names and hand_type in ("TWO_PAIR", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            chips += 12
        if "Witty Joker" in names and hand_type in ("STRAIGHT", "STRAIGHT_FLUSH"):
            mult += 6
        if "Lively Joker" in names and hand_type in ("STRAIGHT", "STRAIGHT_FLUSH"):
            chips += 20
        if "Daring Joker" in names and hand_type in ("FLUSH", "STRAIGHT_FLUSH"):
            mult += 7
        if "Vibrant Joker" in names and hand_type in ("FLUSH", "STRAIGHT_FLUSH"):
            chips += 25

        if "The Duo" in names and hand_type in ("PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            mult *= 2
        if "The Trio" in names and hand_type in ("THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND"):
            mult *= 2.5
        if "The Family" in names and hand_type == "FOUR_OF_A_KIND":
            mult *= 4
        if "The Tribe" in names and hand_type in ("FLUSH", "STRAIGHT_FLUSH"):
            mult *= 3
        if "The Order" in names and hand_type in ("STRAIGHT", "STRAIGHT_FLUSH"):
            mult *= 3
        if "UC Socially Dead" in names and hand_type == "HIGH_CARD":
            mult *= 5
        if "Flower Pot" in names and len({self._suit(card) for card in hand}) == 4:
            mult *= 2.5
        if "Student ID" in names and self._student_id(hand):
            mult += 120
        scored_cards = [card for i, card in enumerate(hand) if scored[i]]
        if "Half Joker" in names and scored_cards and (
            all(card.rank <= 8 for card in scored_cards)
            or all(card.rank >= 9 for card in scored_cards)
        ):
            mult += 15
        if "Color Theory" in names:
            mult *= 1 + 0.5 * (len({self._suit(card) for card in hand}) - 1)
        if "Study Group" in names:
            ranks = set()
            for i, card in enumerate(hand):
                if scored[i]:
                    ranks.add(card.rank)
            chips += 12 * len(ranks)

        total_stella = sum(stella)
        if "Snowball" in names:
            chips += 10 * total_stella
        if "Boiling Point" in names and total_stella > 12:
            mult *= 3
        if "Galaxy" in names:
            mult *= 1 + 0.5 * total_stella
        if "Popcorn" in names:
            mult += max(0, 16 - total_stella)
        if "Starcorn" in names:
            mult += 16 + total_stella
        if "Plasma" in names or "Star Plasma" in names:
            average = (chips + mult) / 2
            chips = average
            mult = average
        return chips, mult

    def _classify(self, hand):
        ranks = [card.rank for card in hand]
        suits = [self._suit(card) for card in hand]
        counts = {}
        for rank in ranks:
            counts[rank] = counts.get(rank, 0) + 1
        count_values = sorted(counts.values(), reverse=True)
        flush = len(set(suits)) == 1
        straight = self._is_straight(ranks)
        scored = [False, False, False, False, False]

        if straight and flush:
            return "STRAIGHT_FLUSH", [True, True, True, True, True]
        if count_values == [4, 1]:
            rank = self._rank_with_count(counts, 4)
            return "FOUR_OF_A_KIND", [card.rank == rank for card in hand]
        if count_values == [3, 2]:
            return "FULL_HOUSE", [True, True, True, True, True]
        if flush:
            return "FLUSH", [True, True, True, True, True]
        if straight:
            return "STRAIGHT", [True, True, True, True, True]
        if count_values == [3, 1, 1]:
            rank = self._rank_with_count(counts, 3)
            return "THREE_OF_A_KIND", [card.rank == rank for card in hand]
        if count_values == [2, 2, 1]:
            pair_ranks = {rank for rank, count in counts.items() if count == 2}
            return "TWO_PAIR", [card.rank in pair_ranks for card in hand]
        if count_values == [2, 1, 1, 1]:
            rank = self._rank_with_count(counts, 2)
            return "PAIR", [card.rank == rank for card in hand]

        high = max(ranks)
        for i, card in enumerate(hand):
            if card.rank == high:
                scored[i] = True
                break
        return "HIGH_CARD", scored

    def _is_straight(self, ranks):
        unique = sorted(set(ranks))
        if len(unique) != 5:
            return False
        return unique[-1] - unique[0] == 4 or unique == [2, 3, 4, 5, 14]

    def _rank_with_count(self, counts, target):
        for rank, count in counts.items():
            if count == target:
                return rank
        return 0

    def _rank_score(self, rank):
        if rank <= 10:
            return rank
        if rank <= 13:
            return 10
        return 11

    def _suit(self, card):
        suits = card.suits
        if not suits:
            return ""
        return suits[0]

    def _final_scored_index(self, scored):
        for i in range(len(scored) - 1, -1, -1):
            if scored[i]:
                return i
        return None

    def _seen_face_before(self, hand, scored, index):
        for i in range(index):
            if scored[i] and hand[i].rank >= 11:
                return True
        return False

    def _student_id(self, hand):
        aces = 0
        for card in hand:
            if card.rank == 14:
                aces += 1
            if 11 <= card.rank <= 13:
                return False
        return aces == 1
