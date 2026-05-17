import time
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from copy import deepcopy
from stellatro_common.card import Card, Suit, Rank

c = Card(Suit.SPADES, Rank.ACE)

start = time.perf_counter()
for _ in range(10000):
    a = deepcopy(c)
print("Deepcopy:", time.perf_counter() - start)

start = time.perf_counter()
for _ in range(10000):
    a = Card(suit=c.suit, rank=c.rank)
print("Manual:", time.perf_counter() - start)
