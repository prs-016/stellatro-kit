"""Quick trace: compare draft choices between prakharfirstbot and myfirstbot on lost seeds."""
import sys, random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from copy import deepcopy
from itertools import combinations
from stellatro_game import Game, GameSetup, Phase, PlayerTurn
from stellatro_game import Card, Suit, evaluate_hand, PLAYER_CARDS
from scripts.run_bot_match import resolve_bot_class

def card_str(c):
    r = {11:"J",12:"Q",13:"K",14:"A"}.get(c.rank, str(c.rank))
    return f"{r}-{'+'.join(s.value for s in c.suits)}"

def best_brute_force(cards, jokers):
    n = min(PLAYER_CARDS, len(cards))
    best = 0
    best_combo = []
    for combo in combinations(range(n), 5):
        sub = [deepcopy(cards[i]) for i in combo]
        j = [deepcopy(j) for j in jokers]
        try:
            s = evaluate_hand(sub, j)
        except:
            s = 0
        if s > best:
            best = s
            best_combo = [cards[i] for i in combo]
    return best, best_combo

for seed in [101, 103, 105, 107, 109]:
    rng = random.Random(seed)
    setup = GameSetup.generate(rng=rng)
    setup.joker_pool = setup.joker_pool[:15]
    
    print(f"\n{'='*60}")
    print(f"SEED {seed}")
    print(f"{'='*60}")
    print(f"P1 Hand: {[card_str(c) for c in setup.p1_hand]}")
    print(f"P2 Hand: {[card_str(c) for c in setup.p2_hand]}")
    print(f"Pool: {[j.name for j in setup.joker_pool]}")
    
    # Run game 1 with each bot as P1
    for bot_name, bot_path in [("prakhar", "starter-kit/bots/prakharfirstbot.py"), ("myfirst", "starter-kit/bots/myfirstbot.py")]:
        bot_p1 = resolve_bot_class(bot_path)()
        bot_p2 = resolve_bot_class("starter-kit/bots/myfirstbot.py" if bot_name == "prakhar" else "starter-kit/bots/prakharfirstbot.py")()
        
        game = Game(verbose=False)
        game.load_setup(setup, swap_hands=False)
        
        picks_p1 = []
        picks_p2 = []
        while game.phase == Phase.DRAFT:
            state = game.get_game_state()
            if state.current_turn == PlayerTurn.PLAYER1:
                action = bot_p1.pick_joker(state)
                picks_p1.append(game.jokers[action].name)
                game.step(1, action=action)
            else:
                action = bot_p2.pick_joker(state)
                picks_p2.append(game.jokers[action].name)
                game.step(2, action=action)
        
        print(f"\n  [{bot_name} as P1] drafted: {picks_p1}")
        print(f"  [opponent as P2] drafted: {picks_p2}")
        
        # Show best possible hand for P1 with their jokers
        p1_jokers = [deepcopy(j) for j in game.p1jokers]
        score, combo = best_brute_force(game.p1hand, p1_jokers)
        print(f"  P1 best hand: {[card_str(c) for c in combo]} = {score}")
