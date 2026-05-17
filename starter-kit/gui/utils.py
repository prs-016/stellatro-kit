import os
import importlib.util
import sys
import inspect
import math
from stellatro_game.checker import HandType
from collections import Counter
from typing import List

def _get_base_path():
    # PyInstaller extracts files to sys._MEIPASS when frozen
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # Normal run: base is the starter-kit/ directory (parent of gui/)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ASSETS_DIR = os.path.join(_get_base_path(), "assets")

def get_assets_path(asset_file_name):
    return os.path.join(ASSETS_DIR,asset_file_name)

def load_bot(file_path):
    """Dynamically loads a Bot class from a given python file path."""
    if not file_path:
        return None # Human player
    
    if not os.path.exists(file_path):
        print(f"Error: Bot file '{file_path}' not found.")
        sys.exit(1)

    module_name = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        print(f"Error: Could not load module from '{file_path}'.")
        sys.exit(1)
        
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Find a class in the module that is a subclass of BotInterface
    for name, obj in inspect.getmembers(module):
        # Duck-typing check: does it have the required methods?
        if (inspect.isclass(obj) and
                obj.__module__ == module.__name__ and # FIXED LINE
                hasattr(obj, 'pick_joker') and
                callable(getattr(obj, 'pick_joker')) and
                hasattr(obj, 'pick_hand') and
                callable(getattr(obj, 'pick_hand'))):
            try:
                return obj()
            except Exception as e:
                print(f"Error: Could not instantiate bot class '{obj.__name__}' from '{file_path}': {e}")
                sys.exit(1)
        
    print(f"Error: The file '{file_path}' must contain a class with 'pick_joker' and 'pick_hand' methods.")
    sys.exit(1)

def is_straight(ranks: List[int]) -> bool:
    """Return True if ranks form a straight (supports A-2-3-4-5)."""
    uniq = sorted(set(ranks))
    if len(uniq) != 5:
        return False
    # normal straight
    if uniq[-1] - uniq[0] == 4:
        return True

    # wheel: A,2,3,4,5
    return uniq == [2, 3, 4, 5, 14]
    

def get_hand_type(hand):
    ranks = [c.rank for c in hand]
    
    unique_suits = set()
    for s_set in [c.suits for c in hand]:
        unique_suits.update(s_set)

    # rank scoring
    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)

    flush = len(unique_suits) == 1 and len(ranks) == 5
    straight = is_straight(ranks)

    hand_type = HandType.HIGH_CARD

    if straight and flush:
        hand_type = HandType.STRAIGHT_FLUSH
    elif counts.count(4) == 1:
        hand_type = HandType.FOUR_OF_A_KIND
    elif counts == [3, 2]:
        hand_type = HandType.FULL_HOUSE
    elif flush:
        hand_type = HandType.FLUSH
    elif straight:
        hand_type = HandType.STRAIGHT
    elif counts.count(3) == 1:
        hand_type = HandType.THREE_OF_A_KIND
    elif counts.count(2) == 2:
        hand_type = HandType.TWO_PAIR
    elif counts.count(2) == 1:
        hand_type = HandType.PAIR
    return hand_type

def format_number(n) -> str:
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    if math.isnan(f):
        return "nan"
    if math.isinf(f):
        return "inf"
    if abs(f) < 100_000_000_000:
        return str(int(f))
    exp = int(math.floor(math.log10(abs(f))))
    mantissa = f / (10 ** exp)
    return f"{mantissa:.2f}e{exp}"

def get_chips_by_rank(rank):
    if rank >= 10 and rank <= 13:
        return 10
    elif rank == 14:
        return 11
    return rank