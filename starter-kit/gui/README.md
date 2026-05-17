# Stellatro GUI

This is the graphical user interface for Stellatro, a Balatro-inspired AI competition game. It allows you to play manually, watch bots play against each other, or test your bot implementation in a visual environment.

## How to Run

### Using the Pre-built Executable (Recommended)

No Python installation or dependencies required.

**macOS**

Double-click `gui-mac/Stellatro.app` to launch with no arguments.

To use flags, open a terminal and run the binary directly:

```bash
./starter-kit/gui-mac/Stellatro --p1 my_bot.py --p2 other_bot.py
```

> If macOS blocks the app ("unidentified developer"), right-click `Stellatro.app` and choose **Open**, then confirm.

**Windows**

Double-click `gui-windows/Stellatro/Stellatro.exe` to launch with no arguments.

To use flags, open Command Prompt or PowerShell and run:

```powershell
.\starter-kit\gui-windows\Stellatro\Stellatro.exe --p1 my_bot.py --p2 other_bot.py
```

---

### Running from Source

**Prerequisites:** Python 3.13

**1. Install dependencies**

From the `starter-kit/` directory, install the project and its local packages:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ../stellatro-common -e ../stellatro-game
pip install -r requirements.txt
```

**2. Run the GUI**

```bash
# From starter-kit/
python gui/gui.py

# Or from inside gui/
python gui.py
```

## Command-Line Flags

You can customize the game setup using various flags:

| Flag               | Description                                                                | Usage Example                          |
| ------------------ | -------------------------------------------------------------------------- | -------------------------------------- |
| `--p1 [PATH]`      | Path to the Python file for **Player 1**. If omitted, Player 1 is a human. | `--p1 starter-kit/bots/random_bot.py`  |
| `--p2 [PATH]`      | Path to the Python file for **Player 2**. If omitted, Player 2 is a human. | `--p2 starter-kit/bots/minimax_bot.py` |
| `--game_speed [N]`| Multiplier for animation and bot decision speed. Default is `1.0`. | `--game_speed 2.0` |
| `--report` | If included, game results will be saved to the `gui/reports/` directory. Each session appends rows to a CSV file named by timestamp (e.g., `reports/session_20260404_123000.csv`). | `--report` |
| `--no_bg` | If included, the dynamic flowing background is disabled (replaced with static Navy Blue). | `--no_bg` |
| `--autorestart` | If included, the game automatically restarts immediately after reaching the game-over screen. | `--autorestart` |

## Examples

### Human vs Human

Play against a friend locally (just launch with no flags):

```bash
# macOS
./starter-kit/gui-mac/Stellatro

# Windows
.\starter-kit\gui-windows\Stellatro\Stellatro.exe

# From source
python starter-kit/gui/gui.py
```

### Human vs Bot

Test your skills against a bot:

```bash
# macOS
./starter-kit/gui-mac/Stellatro --p2 starter-kit/bots/random_bot.py

# Windows
.\starter-kit\gui-windows\Stellatro\Stellatro.exe --p2 starter-kit\bots\random_bot.py

# From source
python starter-kit/gui/gui.py --p2 starter-kit/bots/random_bot.py
```

### Bot vs Bot (Spectator Mode)

Watch two bots compete:

```bash
# macOS
./starter-kit/gui-mac/Stellatro --p1 starter-kit/bots/random_bot.py --p2 starter-kit/bots/minimax_bot.py --game_speed 1.5

# Windows
.\starter-kit\gui-windows\Stellatro\Stellatro.exe --p1 starter-kit\bots\random_bot.py --p2 starter-kit\bots\minimax_bot.py --game_speed 1.5

# From source
python starter-kit/gui/gui.py --p1 starter-kit/bots/random_bot.py --p2 starter-kit/bots/minimax_bot.py --game_speed 1.5
```

### Bot testing with reporting

Run a game and save the final state to a JSON file for analysis:

```bash
# macOS
./starter-kit/gui-mac/Stellatro --p1 starter-kit/bots/minimax_bot.py --p2 starter-kit/bots/random_bot.py --report

# Windows
.\starter-kit\gui-windows\Stellatro\Stellatro.exe --p1 starter-kit\bots\minimax_bot.py --p2 starter-kit\bots\random_bot.py --report

# From source
python starter-kit/gui/gui.py --p1 starter-kit/bots/minimax_bot.py --p2 starter-kit/bots/random_bot.py --report
```

---

## Building the Executable Yourself

If you'd rather produce your own standalone build of the GUI (e.g., to bundle a custom icon, tweak the spec, or ship a fork), you can build it from source using [PyInstaller](https://pyinstaller.org/) and the included `stellatro.spec` file.

**Prerequisites:** Python 3.13 and the source dependencies installed (see [Running from Source](#running-from-source)).

**1. Install PyInstaller**

```bash
pip install pyinstaller
```

**2. Build using the bundled spec**

From inside the `starter-kit/gui/` directory:

```bash
pyinstaller stellatro.spec
```

The spec file (`stellatro.spec`) handles everything PyInstaller needs:

- Entry point: `gui.py`
- Bundles the `../assets` folder so sprites, fonts, and sounds ship with the binary.
- Bundles the local `stellatro_common` and `stellatro_game` packages from the sibling directories.
- Collects all submodules from `pygame`, `stellatro_common`, `stellatro_game`, and `bots` as hidden imports.
- On macOS, wraps the output in a `Stellatro.app` bundle.

**3. Find your build**

PyInstaller writes to two directories next to the spec file:

- `build/` — intermediate build artifacts (safe to delete).
- `dist/` — your finished executable.
  - **macOS:** `dist/Stellatro.app` (double-clickable) and `dist/Stellatro/` (folder build).
  - **Windows:** `dist/Stellatro/Stellatro.exe`.

Run it the same way as the pre-built executables described above.

**Customizing the build**

Common tweaks inside `stellatro.spec`:

- **Custom icon:** replace `icon=None` with `'assets/icon.icns'` (macOS) or `'assets/icon.ico'` (Windows) in both the `EXE(...)` and `BUNDLE(...)` calls.
- **Show a console window** (useful for debugging crashes): set `console=True` in the `EXE(...)` call.
- **Slim down the binary:** uncomment the entries under `excludes=[...]` to drop heavy ML dependencies (`torch`, `torchrl`, `tensordict`) if your bots don't need them at GUI runtime.

> **Note:** PyInstaller produces a build for the OS you run it on. To ship both macOS and Windows binaries, run the build on each platform separately (or use a CI runner per OS).
