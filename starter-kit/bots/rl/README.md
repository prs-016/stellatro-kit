# RL Bot

This folder contains a trainable reinforcement learning bot for Stellatro. It
learns which jokers to draft by playing many games and adjusting its strategy
based on outcomes. After the draft, it always plays the best possible 5-card
hand by checking every combination.

If you want to experiment with the RL bot, start with `config.py`. Most useful
training and evaluation settings live there, and you can also override them from
the command line with `cfg.key=value`.

## What The RL Bot Learns

The bot learns to pick jokers during the draft phase. On each turn, it looks at
the current game state and selects a joker from the available pool. Invalid
choices are automatically blocked.

Hand selection is deterministic: after the draft, the bot tries all 252 possible
5-card subsets and plays the highest-scoring one.

By default, the bot trains by distilling the built-in minimax draft policy into
the neural checkpoint. PPO fine-tuning is still available, but it is intentionally
off by default because short PPO runs against minimax/self-play mixtures can
overwrite the distilled policy and regress minimax win rate.

## Files To Start With

- **`config.py`** - Start here. Controls training parameters (`total_frames`, `lr`, `hidden_dim`, `num_layers`, etc.) and evaluation settings (`checkpoint_path`, `opponent`).
- **`model.py`** - The neural network architecture. The default is an MLP; there is also a Transformer placeholder you can implement.
- **`eval.py`** - Run evaluation experiments. Most common options are available via `config.py` overrides instead.
- **`env.py`** - The game environment wrapper. You usually won't need to touch this.
- **`rl_bot.py`** - Loads a checkpoint and exposes the trained policy through the tournament interface. Only edit if you change how checkpoints are loaded.

## Setup

Use the main starter-kit setup first:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows, activate with:

```powershell
.venv\Scripts\Activate.ps1
```

The examples below assume you are running commands from this folder:

```bash
cd starter-kit/bots/rl
```

## Train

Train with the default settings:

```bash
python train.py
```

The default run collects minimax draft demonstrations, behaviorally clones those
choices, and saves `checkpoints/model_final.pt`. If you set
`cfg.total_frames` above zero, the script then runs PPO and saves intermediate
checkpoints named by training frame count, such as `checkpoints/model_30000.pt`.

You can edit defaults in `config.py`, or override them from the command line:

```bash
python train.py \
  cfg.total_frames=200000 \
  cfg.hidden_dim=512 \
  cfg.num_layers=4 \
  cfg.checkpoint_dir=checkpoints_v2
```

You can also specify the PPO opponent curriculum directly from the CLI. For
example, this runs behavioral cloning first, then PPO for `10,000` frames against
random, `20,000` against minimax, and `30,000` against frozen self snapshots:

```bash
python train.py \
  cfg.opponent_schedule=random:10000,minimax:20000,self:30000 \
  cfg.checkpoint_dir=checkpoints_curriculum
```

If `cfg.opponent_schedule` is set and `cfg.total_frames=0`, the PPO frame budget
is the sum of the schedule entries. If `cfg.total_frames` is also set, the run
uses that total budget and keeps using the final schedule phase after the listed
phases are exhausted.

Common training settings:

| Parameter | Default | What it controls |
| --- | ---: | --- |
| `total_frames` | `0` | Number of PPO joker-draft decisions to collect after minimax distillation. Keep at `0` for BC-only training; raise it to experiment with PPO. |
| `frames_per_batch` | `1_000` | How many draft decisions to collect before each PPO update. |
| `num_epochs` | `5` | PPO passes over each collected batch. |
| `sub_batch_size` | `64` | Minibatch size for PPO updates. |
| `lr` | `2e-4` | PPO learning rate. Lower can be more stable; higher can learn faster but is riskier. |
| `entropy_coef` | `0.02` | Exploration pressure. Higher values keep the policy more random for longer. |
| `curriculum_warmup_frames` | `10_000` | Number of PPO frames against a random opponent before the configured stronger opponent curriculum begins. Ignored when `total_frames=0`. |
| `opponent_schedule` | empty | Ordered PPO curriculum, formatted like `random:10000,minimax:20000,self:30000`. Overrides `curriculum_warmup_frames`/`opponent_kind`. |
| `opponent_kind` | `mixed` | PPO opponent after warmup: `random`, `self`, `minimax`, or `mixed`. |
| `mixed_minimax_prob` | `0.50` | In `mixed` PPO phases, probability that an opponent draft move uses minimax instead of the frozen self snapshot. |
| `bc_teacher_kind` | `minimax` | Behavioral-cloning teacher before PPO. Use `none` to skip teacher data even if BC step counts are nonzero. |
| `bc_pretrain_states` | `10_000` | Number of minimax-labeled draft states to collect for behavioral cloning. |
| `bc_pretrain_epochs` | `10` | Number of supervised passes over minimax demonstrations. |
| `hidden_dim` | `256` | Width of each MLP hidden layer. |
| `num_layers` | `3` | Number of MLP hidden layers. |
| `embed_dim` | `32` | Size of learned card and joker embeddings. |
| `checkpoint_dir` | `checkpoints` | Directory for saved model files. |

## Evaluate

Evaluate the default final checkpoint through the public bot entrypoint against
a random opponent:

```bash
python eval.py
```

Try a stronger built-in opponent:

```bash
python eval.py cfg.opponent=minimax cfg.num_games=200
```

By default, evaluation uses the same public RL bot path that tournament-style
code instantiates. To measure the raw neural checkpoint without the minimax
teacher safety policy, set `cfg.use_public_bot=false`.

Evaluate a different checkpoint:

```bash
python eval.py \
  cfg.checkpoint_path=checkpoints_v2/model_final.pt \
  cfg.opponent=minimax \
  cfg.num_games=500
```

Opponent options:

| `cfg.opponent` | Description |
| --- | --- |
| `random` | Picks a random valid joker. Useful as an easy baseline. |
| `minimax` | Uses the built-in minimax bot for joker drafting and hand play. |
| `self` | Uses the RL model for both seats. |

## Track Experiments

Training logs to [trackio](https://github.com/huggingface/trackio) under the
`stellatro-rl` project. To view runs locally:

```bash
trackio show --project stellatro-rl
```

Useful metrics to watch:

- `BC cross_entropy`: should fall during minimax distillation; lower means the checkpoint is matching minimax choices more closely.
- `episode_reward`: in PPO runs, should trend upward if the bot is winning more.
- `loss/entropy`: shows how exploratory the bot still is; if it drops too early,
  the bot may have stopped trying new strategies.
- `loss/critic`: large spikes can mean the learning rate is too high.

## Next Steps

Good first experiments are increasing `total_frames`, trying a smaller `lr`,
changing `hidden_dim` or `num_layers`, and comparing checkpoints against
`minimax`. Give each run a different `checkpoint_dir` so checkpoints and
trackio runs are easy to compare.
