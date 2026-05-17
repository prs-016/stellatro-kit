# Joker Reference

This document lists the implemented jokers in the canonical game engine at
`stellatro-game/stellatro_game/jokers.py` and shows:

- Joker image
- Joker name
- In-code description
- When the effect is applied

Participants can use this as a quick lookup when building drafting logic or
estimating hand value.

## Phase Meanings

- `pre_card_phase`: changes or retriggers cards before they are scored.
- `apply_card_phase`: applies while each scored card is being processed.
- `post_card_phase`: applies after the hand has been evaluated and card scoring
  is complete.
- `none`: no special phase hook; the joker currently has no custom effect.

Some jokers are lineup-aware: they can inspect the other jokers you own while
scoring. Those effects still run in one of the three phases above.

## Important Note

This file covers all implemented joker classes in the canonical engine. The
current `generate_jokers()` helper samples directly from `ALL_JOKER_CLASSES`,
so every joker listed here can appear in the normal draft pool.

## All Implemented Jokers

| Image | Name | Description | Phase |
| --- | --- | --- | --- |
| <img src="assets/stellatro_jokers/Regular%20Joker.png" width="65" alt="Regular Joker"> | Regular Joker | No special abilities. | `none` |
| <img src="assets/stellatro_jokers/Jolly%20Joker.png" width="65" alt="Jolly Joker"> | Jolly Joker | +4 Mult if the full played hand includes a Pair. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Sly%20Joker.png" width="65" alt="Sly Joker"> | Sly Joker | +20 Chips if the full played hand includes a Pair. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Zany%20Joker.png" width="65" alt="Zany Joker"> | Zany Joker | +8 Mult if the full played hand includes Three of a Kind. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Cheeky%20Joker.png" width="65" alt="Cheeky Joker"> | Cheeky Joker | +6 Mult if the full played hand includes Two Pair. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Witty%20Joker.png" width="65" alt="Witty Joker"> | Witty Joker | +10 Mult if the full played hand includes a Straight. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Daring%20Joker.png" width="65" alt="Daring Joker"> | Daring Joker | +10 Mult if the full played hand includes a Flush. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Merry%20Joker.png" width="65" alt="Merry Joker"> | Merry Joker | +20 Chips if the full played hand includes Three of a Kind. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Jovial%20Joker.png" width="65" alt="Jovial Joker"> | Jovial Joker | +18 Chips if the full played hand includes Two Pair. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Lively%20Joker.png" width="65" alt="Lively Joker"> | Lively Joker | +30 Chips if the full played hand includes a Straight. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Vibrant%20Joker.png" width="65" alt="Vibrant Joker"> | Vibrant Joker | +30 Chips if the full played hand includes a Flush. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Diamond%20Joker.png" width="65" alt="Diamond Joker"> | Diamond Joker | Scored cards with Diamond suit give +4 Mult. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Heart%20Joker.png" width="65" alt="Heart Joker"> | Heart Joker | Scored cards with Heart suit give +4 Mult. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Club%20Joker.png" width="65" alt="Club Joker"> | Club Joker | Scored cards with Club suit give +4 Mult. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Spade%20Joker.png" width="65" alt="Spade Joker"> | Spade Joker | Scored cards with Spade suit give +4 Mult. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Walkie%20Talkie%20Joker.png" width="65" alt="Walkie Talkie"> | Walkie Talkie | Each scored 10 or 4 gives +10 Chips and +4 Mult when scored. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Sock%20and%20Buskin%20Joker.png" width="65" alt="Sock and Buskin"> | Sock and Buskin | Retrigger all scored face cards. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Sun%20God%20Joker.png" width="65" alt="Sun God"> | Sun God | For every heart card scored, get X1.5 Mult | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Eight%20College%20Joker.png" width="65" alt="Eigth College"> | Eigth College | Each scored 8 gives +48 chips and +8 Mult when scored | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Photograph%20Joker.png" width="65" alt="PhotoGraph Joker"> | PhotoGraph Joker | First scored face card gives X2 Mult when scored | `pre_card_phase`, `apply_card_phase` |
| <img src="assets/stellatro_jokers/Flower%20Pot%20Joker.png" width="65" alt="Flower Pot"> | Flower Pot | x3 Mult if the full played hand contains a diamond, heart, spade, and club | `post_card_phase` |
| <img src="assets/stellatro_jokers/The%20Duo%20Joker.png" width="65" alt="The Duo"> | The Duo | If the full played hand contains a pair, x2 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/The%20Trio%20Joker.png" width="65" alt="The Trio"> | The Trio | If the full played hand contains a Three of a Kind, x2.5 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/The%20Tribe%20Joker.png" width="65" alt="The Tribe"> | The Tribe | If the full played hand contains a Flush, x3 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/The%20Order%20Joker.png" width="65" alt="The Order"> | The Order | If the full played hand contains a Straight, x3 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/UC%20Socially%20Dead%20Joker.png" width="65" alt="UC Socially Dead"> | UC Socially Dead | If the full played hand contains only a High Card, x8 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/Bit%20Byte%20Joker.png" width="65" alt="Bit Byte"> | Bit Byte | Face cards give +4 Mult, number cards give +8 Chips. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Student%20ID%20Joker.png" width="65" alt="Student ID"> | Student ID | If the full played hand contains a single ace and no face cards, +25 Mult, +25 chips | `post_card_phase` |
| <img src="assets/stellatro_jokers/Seltzer%20Joker.png" width="65" alt="Seltzer"> | Seltzer | Retrigger each played card that has rank <= 8 | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Last%20Lecture%20Joker.png" width="65" alt="Last Lecture"> | Last Lecture | Final played card gets retriggered 2 extra times | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Dining%20Hall%20Prices%20Joker.png" width="65" alt="Dining Hall Prices"> | Dining Hall Prices | Increases played cards with rank 2,3,4,5 by 5 | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Half%20Joker.png" width="65" alt="Half Joker"> | Half Joker | +15 Mult if scored hand is either all <= 8, or >= 9 | `post_card_phase` |
| <img src="assets/stellatro_jokers/Fibonacci%20Joker.png" width="65" alt="Fibonacci Joker"> | Fibonacci Joker | Each played Ace, 2, 3, 5, or 8 gives +5 Mult when scored. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Scary%20Face%20Joker.png" width="65" alt="Scary Face Joker"> | Scary Face Joker | Each face card gives +30 chips. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/mirror_joker.png" width="65" alt="Mirror"> | Mirror | Face Cards give +20 mult, but -10 chips | `apply_card_phase` |
| <img src="assets/stellatro_jokers/plasma_joker.png" width="65" alt="Plasma"> | Plasma | Balance chips and mult, diminished return if chips and mult are far apart | `post_card_phase` |
| <img src="assets/stellatro_jokers/Star_Plasma.png" width="65" alt="Star Plasma"> | Star Plasma | Gain 2x stellas in each played card | `pre_card_phase` |
| <img src="assets/stellatro_jokers/jam_session_joker.png" width="65" alt="Jam Session"> | Jam Session | +6 mult for each extra trigger on scored cards. | `post_card_phase` |
| <img src="assets/stellatro_jokers/spotlight_joker.png" width="65" alt="Spotlight"> | Spotlight | First played face card gains +10 Chips and +4 Mult for each other face card in full played hand. | `pre_card_phase`, `apply_card_phase` |
| <img src="assets/stellatro_jokers/color_theory_joker.png" width="65" alt="Color Theory"> | Color Theory | x1.25 Mult for each additional suit represented in played hand. | `post_card_phase` |
| <img src="assets/stellatro_jokers/study_group_joker.png" width="65" alt="Study Group"> | Study Group | +12 Chips for each distinct rank among scored cards. | `post_card_phase` |
| <img src="assets/stellatro_jokers/group_project_joker.png" width="65" alt="Group Project"> | Group Project | +8 Chips and +2 Mult for each scored card with rank 8 or lower. | `post_card_phase` |
| <img src="assets/stellatro_jokers/encore_joker.png" width="65" alt="Encore"> | Encore | Final card gets retriggered once for each other card sharing its suit. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/WishUponAStar.png" width="65" alt="Wish Upon a Star"> | Wish Upon a Star | Lowest-ranked played card gains 8 Stella before scoring. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/binary_star_joker.png" width="65" alt="Binary Star"> | Binary Star | Even played cards gain 2 stella | `pre_card_phase` |
| <img src="assets/stellatro_jokers/pips_joker.png" width="65" alt="Pips"> | Pips | Played cards gain stella equal to their rank, but give base 0 chips when scored. | `pre_card_phase`, `apply_card_phase` |
| <img src="assets/stellatro_jokers/report_card_joker.png" width="65" alt="Report Card"> | Report Card | Each ace gives the first card in full played hand 11 stella | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Cache%20Coherence%20Joker.png" width="65" alt="Cache Coherence"> | Cache Coherence | Played cards of the same suit have the same number of stella (max) | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Stargazing%20Joker.png" width="65" alt="Stargazing"> | Stargazing | Each played card's stella gives one retrigger | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Boiling%20Point%20Joker.png" width="65" alt="Boiling Point"> | Boiling Point | If total number of stella across played cards is greater than 12, x3 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/Galaxy%20Joker.png" width="65" alt="Galaxy"> | Galaxy | +0.25x Mult per stella across played cards, base 1x Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/Popcorn%20Joker.png" width="65" alt="Popcorn"> | Popcorn | +30 Mult, -5 per stella on played cards | `post_card_phase` |
| <img src="assets/stellatro_jokers/Starcorn.png" width="65" alt="Starcorn"> | Starcorn | Each card gives (rank * stella) mult | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Supernova.png" width="65" alt="Supernova"> | Supernova | Each card with stella gives x(1.1)^stella mult when scored. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Snowball.png" width="65" alt="Snowball"> | Snowball | +40 Chips per stella on played cards | `post_card_phase` |
| <img src="assets/stellatro_jokers/Constellation%20Joker.png" width="65" alt="Constellation"> | Constellation | Gain +8 chips and +3 mult for each Stella on scored cards. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Arrowhead.png" width="65" alt="Arrowhead"> | Arrowhead | Played cards with Spade suit give +18 Chips. | `apply_card_phase` |
| <img src="assets/stellatro_jokers/Loss_Cut.png" width="65" alt="Loss Cut"> | Loss Cut | For every card that wasn't scored, gain +30 Chips. | `post_card_phase` |
| <img src="assets/stellatro_jokers/Lock%20In.png" width="65" alt="Lock In"> | Lock In | All played cards score, no matter what hand is played. | `scores_all_cards` |
| <img src="assets/stellatro_jokers/Starjack.png" width="65" alt="Starjack"> | Starjack | The first face card gains 10 stella. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Blackjack.png" width="65" alt="Blackjack"> | Blackjack | x4 Mult if all played cards' score adds up to 21. | `post_card_phase` |
| <img src="assets/stellatro_jokers/SixSeven.png" width="65" alt="Six Seven"> | Six Seven | If the full played hand contains a 6 and a 7, gain +67 Mult | `post_card_phase` |
| <img src="assets/stellatro_jokers/ThriceTwice.png" width="65" alt="Thrice Twice"> | Thrice Twice | If the full played hand contains a Full House, each card gains 3 stella | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Fallen%20Star.png" width="65" alt="Fallen Star"> | Fallen Star | Lowest scored card gains stella equal to the highest scored rank, and highest scored card gains stella equal to the lowest scored rank. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Star%20Fish.png" width="65" alt="Star Fish"> | Star Fish | Scored cards in pairs gain +2 stella, triplets gain +4 stella, and quads gain +8 stella. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Branch_Out.png" width="65" alt="Branch Out"> | Branch Out | Each played card carries half of the previous played card's stella. | `pre_card_phase` |
| <img src="assets/stellatro_jokers/Anya.png" width="65" alt="Anya"> | Anya | Each scored card gives +4 Mult for every other played card sharing its rank or suit. | `pre_card_phase`, `apply_card_phase` |

<!-- Generated from jokers.py and joker_sprites.py; 67 jokers. -->
