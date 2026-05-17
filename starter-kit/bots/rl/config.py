from __future__ import annotations

import chz


@chz.chz
class TrainConfig:
    """Participant-facing PPO training parameters."""

    total_frames: int = 0
    frames_per_batch: int = 1_000     # agent joker-draft decisions per batch
    num_epochs: int = 5               # PPO epochs per batch
    sub_batch_size: int = 64
    clip_epsilon: float = 0.2
    gamma: float = 1.0
    gae_lambda: float = 0.95
    lr: float = 2e-4
    entropy_coef: float = 0.02
    critic_coef: float = 0.5
    curriculum_warmup_frames: int = 10_000
    opponent_schedule: str = ""       # e.g. "random:10000,minimax:20000,self:30000"
    opponent_kind: str = "mixed"      # "random", "self", "minimax", or "mixed"
    mixed_minimax_prob: float = 0.50
    minimax_depth: int = 1
    bc_teacher_kind: str = "minimax"  # "minimax" or "none"
    bc_pretrain_states: int = 10_000
    bc_pretrain_epochs: int = 10
    bc_batch_size: int = 512
    bc_lr: float = 5e-4
    max_grad_norm: float = 0.5
    device: str = "cpu"
    seed: int = 42
    log_interval: int = 5
    save_every_batches: int = 10
    checkpoint_dir: str = "checkpoints"
    use_trackio: bool = False
    model_type: str = "mlp"
    embed_dim: int = 32
    hidden_dim: int = 256
    num_layers: int = 3


@chz.chz
class EvalConfig:
    """Participant-facing checkpoint evaluation parameters."""

    checkpoint_path: str = "checkpoints/model_final.pt"
    num_games: int = 100
    opponent: str = "random"  # "self", "random", "minimax"
    seed: int = 0
    verbose: bool = False
    use_public_bot: bool = True
    use_minimax_teacher: bool = True
