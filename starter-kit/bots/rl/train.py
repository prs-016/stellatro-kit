from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

import chz
import numpy as np
import torch
from tensordict.nn import TensorDictModule, TensorDictSequential
from torch import nn, optim
from torchrl.collectors import SyncDataCollector
from torchrl.data.replay_buffers import ReplayBuffer
from torchrl.data.replay_buffers.samplers import SamplerWithoutReplacement
from torchrl.data.replay_buffers.storages import LazyTensorStorage
from torchrl.envs.utils import check_env_specs
from torchrl.modules import ProbabilisticActor, ValueOperator
from torchrl.modules.distributions import OneHotCategorical
from torchrl.objectives import ClipPPOLoss
from torchrl.objectives.value import GAE

from config import TrainConfig
from env import StellaEnv, _flatten_state
from model import ACTION_DIM, JOKER_DRAFT_OFFSET, build_model, ensure_supported_model_type
from stellatro_game import Game, Phase, PlayerTurn

_RL_DIR = Path(__file__).resolve().parent
_STARTER_ROOT = _RL_DIR.parents[1]
_VALID_OPPONENT_KINDS = {"random", "self", "minimax", "mixed"}


def make_env(
    device: str = "cpu",
    opponent_model: torch.nn.Module | None = None,
    opponent_kind: str = "random",
    mixed_minimax_prob: float = 0.5,
    minimax_depth: int = 1,
    controlled_player: int | None = None,
    seed: int | None = None,
) -> StellaEnv:
    return StellaEnv(
        device=device,
        opponent_model=opponent_model,
        opponent_kind=opponent_kind,
        mixed_minimax_prob=mixed_minimax_prob,
        minimax_depth=minimax_depth,
        controlled_player=controlled_player,
        seed=seed,
    )

def make_policy_and_value(cfg: TrainConfig):
    """Build TorchRL-compatible policy and value modules from our ActorCritic model."""
    ensure_supported_model_type(cfg.model_type)
    model = build_model(
        model_type=cfg.model_type,
        embed_dim=cfg.embed_dim,
        hidden_dim=cfg.hidden_dim,
        num_layers=cfg.num_layers,
    )

    # Actor: observation -> logits (only, no state_value) -> masked logits -> action
    logits_module = TensorDictModule(
        module=_LogitsHead(model),
        in_keys=["observation"],
        out_keys=["logits"],
    )
    mask_module = TensorDictModule(
        module=_LogitsExtractor(),
        in_keys=["logits", "action_mask"],
        out_keys=["logits"],
    )
    policy_module = ProbabilisticActor(
        module=TensorDictSequential(logits_module, mask_module),
        in_keys=["logits"],
        out_keys=["action"],
        distribution_class=OneHotCategorical,
        return_log_prob=True,
    )

    # Value module that independently computes state_value from observation
    # (needed by GAE to evaluate both current and next states)
    value_module = ValueOperator(
        module=_ValueHead(model),
        in_keys=["observation"],
    )

    return model, policy_module, value_module


def _make_model_snapshot(
    cfg: TrainConfig,
    source_model: nn.Module,
    device: torch.device,
) -> nn.Module:
    snapshot = build_model(
        model_type=cfg.model_type,
        embed_dim=cfg.embed_dim,
        hidden_dim=cfg.hidden_dim,
        num_layers=cfg.num_layers,
    )
    snapshot.load_state_dict(source_model.state_dict())
    snapshot.to(device)
    snapshot.eval()
    return snapshot


class _LogitsHead(nn.Module):
    """Extract just the logits output from the shared ActorCritic model."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, observation: torch.Tensor) -> torch.Tensor:
        logits, _ = self.model(observation)
        return logits


class _ValueHead(nn.Module):
    """Extract just the value output from the shared ActorCritic model."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, observation: torch.Tensor) -> torch.Tensor:
        _, value = self.model(observation)
        return value


class _LogitsExtractor(nn.Module):
    """Apply action mask to logits: set invalid actions to -inf."""

    def forward(self, logits: torch.Tensor, action_mask: torch.Tensor) -> torch.Tensor:
        logits = logits.clone()
        # Expand mask to match logits shape (handles unbatched vs batched)
        mask = action_mask.expand_as(logits)
        logits[~mask] = float("-inf")
        return logits


def _current_player_num(game: Game) -> int:
    return 1 if game.current_turn == PlayerTurn.PLAYER1 else 2


def _load_minimax_bot(max_depth: int):
    if str(_STARTER_ROOT) not in sys.path:
        sys.path.insert(0, str(_STARTER_ROOT))
    from bots.minimax_bot import MinimaxBot

    return MinimaxBot(max_depth=max_depth)


def _collect_minimax_demonstrations(
    cfg: TrainConfig,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Generate active-player draft states labeled by MinimaxBot choices."""
    minimax_bot = _load_minimax_bot(cfg.minimax_depth)
    py_rng = random.Random(cfg.seed + 10_000)
    observations: list[torch.Tensor] = []
    actions: list[int] = []
    masks: list[torch.Tensor] = []

    while len(observations) < cfg.bc_pretrain_states:
        game = Game(verbose=False, rng=py_rng)
        game.start_round(rng=py_rng)
        while game.phase == Phase.DRAFT and len(observations) < cfg.bc_pretrain_states:
            player = _current_player_num(game)
            n_valid = len(game.jokers)
            obs = _flatten_state(game.encode_state(player))
            mask = torch.zeros(ACTION_DIM, dtype=torch.bool)
            mask[JOKER_DRAFT_OFFSET : JOKER_DRAFT_OFFSET + n_valid] = True
            action = JOKER_DRAFT_OFFSET + int(minimax_bot.pick_joker(game.get_game_state()))

            observations.append(obs)
            actions.append(action)
            masks.append(mask)

            success, _ = game.step(player, action=action - JOKER_DRAFT_OFFSET)
            if not success:
                raise RuntimeError(f"Minimax demonstration produced invalid action {action}.")

    return (
        torch.stack(observations).to(device),
        torch.tensor(actions, dtype=torch.long, device=device),
        torch.stack(masks).to(device),
    )


def _pretrain_with_minimax(
    cfg: TrainConfig,
    model: nn.Module,
    device: torch.device,
) -> None:
    """Behaviorally clone MinimaxBot before PPO fine-tuning."""
    if cfg.bc_teacher_kind == "none":
        return
    if cfg.bc_teacher_kind != "minimax":
        raise ValueError("cfg.bc_teacher_kind must be 'minimax' or 'none'.")
    if cfg.bc_pretrain_states <= 0 or cfg.bc_pretrain_epochs <= 0:
        return

    print(
        f"Collecting {cfg.bc_pretrain_states} minimax demonstration states "
        f"(depth={cfg.minimax_depth})..."
    )
    observations, actions, masks = _collect_minimax_demonstrations(cfg, device)
    optimizer = optim.Adam(model.parameters(), lr=cfg.bc_lr)
    model.train()

    for epoch in range(cfg.bc_pretrain_epochs):
        perm = torch.randperm(observations.shape[0], device=device)
        total_loss = 0.0
        n_updates = 0
        for start in range(0, observations.shape[0], cfg.bc_batch_size):
            batch_idx = perm[start : start + cfg.bc_batch_size]
            logits, _ = model(observations[batch_idx])
            masked_logits = logits.masked_fill(~masks[batch_idx], float("-inf"))
            loss = nn.functional.cross_entropy(masked_logits, actions[batch_idx])

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), cfg.max_grad_norm)
            optimizer.step()

            total_loss += loss.item()
            n_updates += 1

        print(
            f"[BC {epoch + 1}/{cfg.bc_pretrain_epochs}] "
            f"cross_entropy={total_loss / max(n_updates, 1):.4f}"
        )


def _parse_opponent_schedule(schedule: str) -> list[tuple[str, int]]:
    """Parse 'random:1000,minimax:2000,self:3000' into ordered phases."""
    phases: list[tuple[str, int]] = []
    if not schedule.strip():
        return phases

    for raw_phase in schedule.split(","):
        raw_phase = raw_phase.strip()
        if not raw_phase:
            continue
        try:
            kind, frames_text = raw_phase.split(":", maxsplit=1)
        except ValueError as exc:
            raise ValueError(
                "cfg.opponent_schedule entries must look like 'kind:frames', "
                "for example 'random:10000,minimax:20000,self:30000'."
            ) from exc
        kind = kind.strip()
        if kind not in _VALID_OPPONENT_KINDS:
            raise ValueError(
                f"Unknown opponent kind {kind!r}; expected one of "
                f"{', '.join(sorted(_VALID_OPPONENT_KINDS))}."
            )
        frames = int(frames_text.replace("_", "").strip())
        if frames <= 0:
            raise ValueError("Opponent schedule frame counts must be positive.")
        phases.append((kind, frames))

    return phases


def _scheduled_total_frames(cfg: TrainConfig, phases: list[tuple[str, int]]) -> int:
    if phases and cfg.total_frames <= 0:
        return sum(frames for _, frames in phases)
    return cfg.total_frames


def _opponent_kind_for_frame(
    cfg: TrainConfig,
    phases: list[tuple[str, int]],
    total_collected: int,
) -> str:
    if phases:
        cursor = 0
        for kind, frames in phases:
            cursor += frames
            if total_collected < cursor:
                return kind
        return phases[-1][0]

    if total_collected < cfg.curriculum_warmup_frames:
        return "random"
    if cfg.opponent_kind not in _VALID_OPPONENT_KINDS:
        raise ValueError(
            f"Unknown cfg.opponent_kind {cfg.opponent_kind!r}; expected one of "
            f"{', '.join(sorted(_VALID_OPPONENT_KINDS))}."
        )
    return cfg.opponent_kind

def train(cfg: TrainConfig) -> None:
    # Seed
    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)

    device = torch.device(cfg.device)

    # Environment
    env = make_env(device=cfg.device, seed=cfg.seed)
    check_env_specs(env)
    env.close()

    # Model
    model, actor, value_module = make_policy_and_value(cfg)
    model.to(device)
    _pretrain_with_minimax(cfg, model, device)

    # Loss
    loss_module = ClipPPOLoss(
        actor_network=actor,
        critic_network=value_module,
        clip_epsilon=cfg.clip_epsilon,
        entropy_bonus=True,
        entropy_coeff=cfg.entropy_coef,
        critic_coeff=cfg.critic_coef,
        loss_critic_type="smooth_l1",
    )

    # GAE advantage estimation
    advantage_module = GAE(
        gamma=cfg.gamma,
        lmbda=cfg.gae_lambda,
        value_network=value_module,
        average_gae=True,
    )

    # Optimizer
    optimizer = optim.Adam(loss_module.parameters(), lr=cfg.lr)

    # Replay buffer for minibatch sampling
    replay_buffer = ReplayBuffer(
        storage=LazyTensorStorage(cfg.frames_per_batch),
        sampler=SamplerWithoutReplacement(),
        batch_size=cfg.sub_batch_size,
    )

    # Checkpoint directory
    ckpt_dir = Path(cfg.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Training
    logs: dict[str, list[float]] = defaultdict(list)
    total_collected = 0
    opponent_schedule = _parse_opponent_schedule(cfg.opponent_schedule)
    total_frames = _scheduled_total_frames(cfg, opponent_schedule)

    trackio_run = None
    if cfg.use_trackio:
        import trackio

        trackio_run = trackio
        trackio_run.init(project="stellatro-rl", name=cfg.checkpoint_dir)

    if opponent_schedule:
        schedule_text = ", ".join(f"{kind}:{frames}" for kind, frames in opponent_schedule)
        print(f"Opponent schedule: {schedule_text}")
    print(f"Starting PPO training: {total_frames} total frames, "
          f"{cfg.frames_per_batch} per batch, {cfg.num_epochs} epochs")
    print(f"Model type: {cfg.model_type}, device: {cfg.device}")
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    if total_frames <= 0:
        print("Skipping PPO updates because no PPO frames were requested.")

    batch_idx = 0
    while total_collected < total_frames:
        batch_frames = min(cfg.frames_per_batch, total_frames - total_collected)
        batch_seed = cfg.seed + batch_idx
        opponent_kind = _opponent_kind_for_frame(cfg, opponent_schedule, total_collected)
        opponent_model = (
            _make_model_snapshot(cfg, model, device)
            if opponent_kind in {"self", "mixed"}
            else None
        )
        collector = SyncDataCollector(
            create_env_fn=lambda opponent_model=opponent_model, batch_seed=batch_seed: make_env(
                device=cfg.device,
                opponent_model=opponent_model,
                opponent_kind=opponent_kind,
                mixed_minimax_prob=cfg.mixed_minimax_prob,
                minimax_depth=cfg.minimax_depth,
                seed=batch_seed,
            ),
            policy=actor,
            frames_per_batch=batch_frames,
            total_frames=batch_frames,
            device=device,
            storing_device=device,
        )
        try:
            batch_data = next(iter(collector))
        finally:
            collector.shutdown()

        total_collected += batch_data.numel()

        # Compute advantage
        with torch.no_grad():
            advantage_module(batch_data)

        # Load into replay buffer
        replay_buffer.empty()
        replay_buffer.extend(batch_data.reshape(-1))

        # PPO update epochs
        epoch_losses = defaultdict(float)
        n_updates = 0
        for _ in range(cfg.num_epochs):
            for minibatch in replay_buffer:
                loss_td = loss_module(minibatch)
                loss = (
                    loss_td["loss_objective"]
                    + loss_td["loss_critic"]
                    + loss_td["loss_entropy"]
                )

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(loss_module.parameters(), cfg.max_grad_norm)
                optimizer.step()

                for key in ("loss_objective", "loss_critic", "loss_entropy"):
                    epoch_losses[key] += loss_td[key].item()
                n_updates += 1

        # Log
        for key, val in epoch_losses.items():
            logs[key].append(val / max(n_updates, 1))

        # Episode reward from batch
        done_mask = batch_data["next", "done"].squeeze(-1)
        if done_mask.any():
            ep_rewards = batch_data["next", "reward"][done_mask].mean().item()
        else:
            ep_rewards = 0.0
        logs["episode_reward"].append(ep_rewards)

        if (batch_idx + 1) % cfg.log_interval == 0:
            print(
                f"[Batch {batch_idx + 1}] "
                f"frames={total_collected} "
                f"opponent={opponent_kind} "
                f"reward={logs['episode_reward'][-1]:.1f} "
                f"loss_obj={logs['loss_objective'][-1]:.4f} "
                f"loss_crit={logs['loss_critic'][-1]:.4f} "
                f"loss_ent={logs['loss_entropy'][-1]:.4f}"
            )
            if trackio_run is not None:
                trackio_run.log({
                    "episode_reward": logs["episode_reward"][-1],
                    "loss/objective": logs["loss_objective"][-1],
                    "loss/critic":    logs["loss_critic"][-1],
                    "loss/entropy":   logs["loss_entropy"][-1],
                }, step=total_collected)

        # Save checkpoint
        if (batch_idx + 1) % cfg.save_every_batches == 0 or total_collected >= total_frames:
            ckpt_path = ckpt_dir / f"model_{total_collected}.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "config": {
                    "model_type": cfg.model_type,
                    "embed_dim": cfg.embed_dim,
                    "hidden_dim": cfg.hidden_dim,
                    "num_layers": cfg.num_layers,
                },
                "total_frames": total_collected,
            }, ckpt_path)
            print(f"Saved checkpoint: {ckpt_path}")

        batch_idx += 1

    # Save final checkpoint
    final_path = ckpt_dir / "model_final.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "config": {
            "model_type": cfg.model_type,
            "embed_dim": cfg.embed_dim,
            "hidden_dim": cfg.hidden_dim,
            "num_layers": cfg.num_layers,
        },
        "total_frames": total_collected,
    }, final_path)
    print(f"Training complete. Final checkpoint: {final_path}")
    if trackio_run is not None:
        trackio_run.finish()


if __name__ == "__main__":
    chz.entrypoint(train)
