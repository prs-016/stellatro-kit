import subprocess
import random
import time
from pathlib import Path

def main():
    rounds = 5
    bot1 = "starter-kit/bots/prakharfirstbot.py"
    bot2 = "starter-kit/bots/myfirstbot.py"
    
    print(f"======================================================================")
    print(f"🏆 SIMULATING RANDOM TOURNAMENT MATCHUP: {bot1} vs {bot2}")
    print(f"Rounds (Sets): {rounds} (Total Games: {rounds * 4})")
    print(f"======================================================================")

    series_start = time.perf_counter()
    bot1_wins, bot2_wins, ties = 0, 0, 0

    for i in range(rounds):
        # Generate completely random seed between 100000 and 999999
        seed = random.randint(100000, 999999)
        print(f"\n>>> RUNNING SET {i+1}/{rounds} WITH TRUE RANDOM SEED {seed} <<<")
        
        # We call the official simulate_competition_match script via subprocess to avoid import errors
        cmd = [
            ".venv/bin/python",
            "starter-kit/scripts/simulate_competition_match.py",
            bot1,
            bot2,
            "--rounds", "1",
            "--seed-base", str(seed)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        
        # Quick parsing to keep track of wins
        if "Overall Match Winner: starter-kit/bots/prakharfirstbot.py!" in result.stdout:
            bot1_wins += 1
        elif "Overall Match Winner: starter-kit/bots/myfirstbot.py!" in result.stdout:
            bot2_wins += 1
        else:
            ties += 1

    elapsed = time.perf_counter() - series_start

    print("\n======================================================================")
    print(f"🏆 Random Match Series Summary (took {elapsed:.1f}s)")
    print(f"======================================================================")
    print(f"Bot A ({bot1}):")
    print(f"  - Set Wins: {bot1_wins}")
    print(f"Bot B ({bot2}):")
    print(f"  - Set Wins: {bot2_wins}")
    print(f"Ties: {ties}")
    print(f"----------------------------------------------------------------------")
    if bot1_wins > bot2_wins:
        print(f"👑 OVERALL TOURNAMENT WINNER: {bot1}!")
    elif bot2_wins > bot1_wins:
        print(f"👑 OVERALL TOURNAMENT WINNER: {bot2}!")
    else:
        print(f"🤝 OVERALL TOURNAMENT ENDED IN A TIE!")
    print(f"======================================================================")

if __name__ == "__main__":
    main()
