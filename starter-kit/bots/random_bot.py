from typing import List
from stellatro_common import GameState


class RandomBot:
    def pick_joker(self, state: GameState) -> int:
        # Return the index into state.joker_pool of the joker to pick.
        return 0

    def pick_hand(self, state: GameState) -> List[int]:
        # Return a list of 5 card indices to play.
        return [0, 1, 2, 3, 4]


Bot = RandomBot
