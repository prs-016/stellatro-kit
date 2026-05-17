import sys, random
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
STARTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = STARTER_ROOT.parent
for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from stellatro_game import Game, GameSetup, Phase, PlayerTurn
from scripts.run_bot_match import resolve_bot_class

seed = 15514
rng = random.Random(seed)
setup = GameSetup.generate(rng=rng)

print(f"\nSEED {seed}")
print(f"Pool: {[j.name for j in setup.joker_pool[:15]]}")

bot_p1 = resolve_bot_class("starter-kit/bots/prakharfirstbot.py")()
bot_p2 = resolve_bot_class("starter-kit/bots/myfirstbot.py")()

game = Game(verbose=False)
game.load_setup(setup, swap_hands=False)

picks_p1, picks_p2 = [], []
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

print(f"[prakhar P1] drafted: {picks_p1}")
print(f"[myfirst P2] drafted: {picks_p2}")
