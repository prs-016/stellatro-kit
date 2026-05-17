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
from stellatro_game import Game, GameSetup, Phase, PlayerTurn, evaluate_hand
from scripts.run_bot_match import resolve_bot_class

for seed in [101, 105]:
    rng = random.Random(seed)
    setup = GameSetup.generate(rng=rng)
    setup.joker_pool = setup.joker_pool[:15]
    
    print(f"\n{'='*60}")
    print(f"SEED {seed}")
    print(f"Pool: {[j.name for j in setup.joker_pool]}")
    
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
        
        # Calculate best hand manually
        best_p1 = 0
        p1_jokers = [deepcopy(j) for j in game.p1jokers]
        for combo in combinations(range(len(game.p1hand)), 5):
            sub = [deepcopy(game.p1hand[i]) for i in combo]
            try:
                s = evaluate_hand(sub, [deepcopy(j) for j in p1_jokers])
                if s > best_p1: best_p1 = s
            except: pass
            
        print(f"  [{bot_name} P1] drafted: {picks_p1} (Score: {best_p1})")
        print(f"  [Opponent P2] drafted: {picks_p2}")
