from abc import ABC, abstractmethod
from typing import Any

from stellatro_common import GameState


class BotInterface(ABC):
    """Small interface shared by starter-kit example bots."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def pick_joker(self, game_state: GameState) -> int:
        """Return the index of the joker to draft from the current pool."""

    @abstractmethod
    def pick_hand(self, game_state: GameState) -> list[int]:
        """Return the card indices to play from the active player's hand."""
