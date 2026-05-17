import sys
from pathlib import Path


STARTER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = STARTER_ROOT.parent

for path in (STARTER_ROOT, REPO_ROOT / "stellatro-common", REPO_ROOT / "stellatro-game"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
