from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Phase(str, Enum):
    DRAFT = "DRAFT"
    PLAY = "PLAY"
    OVER = "OVER"


class PlayerTurn(str, Enum):
    PLAYER1 = "PLAYER1"
    PLAYER2 = "PLAYER2"


class CardModel(BaseModel):
    rank: int
    suits: List[str]
    scored: bool
    num_triggers: int
    stella: int = 0


class JokerModel(BaseModel):
    name: str
    description: str


class GameState(BaseModel):
    phase: Phase
    current_turn: Optional[PlayerTurn]
    player1_hand: List[CardModel]
    player2_hand: List[CardModel]
    joker_pool: List[JokerModel]
    player1_jokers: List[JokerModel]
    player2_jokers: List[JokerModel]
    player1_score: float
    player2_score: float
