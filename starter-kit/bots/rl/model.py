from __future__ import annotations

from abc import ABC, abstractmethod

import torch
import torch.nn as nn
from stellatro_game import (
    JOKER_POOL_SIZE,
    NUM_JOKER_TYPES,
    MAX_JOKERS_PER_PLAYER,
    PLAYER_CARDS,
    CARD_DIM,
    NUM_RANKS,
    NUM_SUITS,
)


SUPPORTED_MODEL_TYPES = ("mlp",)

# ---------------------------------------------------------------------------
# Action space constants
# ---------------------------------------------------------------------------
JOKER_DRAFT_OFFSET = 0                         # actions 0..JOKER_POOL_SIZE-1
ACTION_DIM = JOKER_POOL_SIZE
# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class ActorCritic(nn.Module, ABC):
    """Base interface for Stellatro actor-critic models.

    forward() must return a dict with keys:
        "logits"  — (batch, ACTION_DIM) draft action logits
        "value"   — (batch, 1) state value estimate
    """

    @abstractmethod
    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        ...


# ---------------------------------------------------------------------------
# MLP with learned embeddings
# ---------------------------------------------------------------------------

class MLPActorCritic(ActorCritic):
    """Embedding-based MLP actor-critic for joker drafting.

    Discrete card/joker identifiers are projected through learned embedding
    tables, then flattened and processed by a shared MLP backbone.
    """

    def __init__(
        self,
        embed_dim: int = 32,
        hidden_dim: int = 256,
        num_layers: int = 3,
    ):
        super().__init__()

        # --- Embedding tables ---
        # Cards: unique rank/suit pairs, index = rank_idx * NUM_SUITS + suit_idx.
        self.card_embedding = nn.Embedding(NUM_RANKS * NUM_SUITS, embed_dim)
        # Jokers: one embedding per joker type, plus index 0 = padding/empty
        self.joker_embedding = nn.Embedding(NUM_JOKER_TYPES + 1, embed_dim, padding_idx=0)

        # Dimension after embedding all components:
        #   my_hand + opp_hand = PLAYER_CARDS * 2 * embed_dim
        #   available + owned jokers = (JOKER_POOL_SIZE + MAX_JOKERS_PER_PLAYER * 2) * embed_dim
        #   scalar features: phase(2) + jokers_remaining(1) + scores(2) = 5
        embedded_dim = (
            (PLAYER_CARDS * 2) * embed_dim  # cards
            + (JOKER_POOL_SIZE + MAX_JOKERS_PER_PLAYER * 2) * embed_dim  # jokers
            + 5  # scalars
        )

        # --- Shared backbone ---
        layers: list[nn.Module] = []
        in_dim = embedded_dim
        for _ in range(num_layers):
            layers.append(nn.Linear(in_dim, hidden_dim))
            layers.append(nn.ReLU())
            in_dim = hidden_dim
        self.backbone = nn.Sequential(*layers)

        # --- Heads ---
        # The policy scores each available joker slot with the same small MLP.
        # This is more sample-efficient than a flat ACTION_DIM head because a
        # joker's desirability should mostly depend on its identity/context, not
        # the incidental pool index where it appeared after previous picks.
        self.action_scorer = nn.Sequential(
            nn.Linear(hidden_dim + embed_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.value_head = nn.Linear(hidden_dim, 1)

        # Store layout constants for splitting the flat observation
        self._card_section = PLAYER_CARDS * CARD_DIM        # 170 per hand
        self._joker_section_avail = JOKER_POOL_SIZE * NUM_JOKER_TYPES
        self._joker_section_owned = MAX_JOKERS_PER_PLAYER * NUM_JOKER_TYPES

    def _embed_cards(self, one_hot_cards: torch.Tensor) -> torch.Tensor:
        """Convert (batch, 10, 17) one-hot cards to (batch, 10, embed_dim).

        Recovers rank/suit indices from one-hot, computes card_idx = rank*4+suit,
        then looks up embedding. For zero-padded (empty) slots, returns zeros.
        """
        rank_oh = one_hot_cards[..., :NUM_RANKS]  # (batch, 10, 13)
        suit_oh = one_hot_cards[..., NUM_RANKS:]   # (batch, 10, 4)

        # Get indices; empty slots have all zeros → argmax returns 0, but we mask them
        rank_idx = rank_oh.argmax(dim=-1)  # (batch, 10)
        suit_idx = suit_oh.argmax(dim=-1)  # (batch, 10)
        card_idx = rank_idx * NUM_SUITS + suit_idx  # (batch, 10)

        # Mask empty slots (all zeros in one-hot)
        valid = one_hot_cards.sum(dim=-1) > 0  # (batch, 10)

        embedded = self.card_embedding(card_idx)  # (batch, 10, embed_dim)
        embedded = embedded * valid.unsqueeze(-1).float()
        return embedded

    def _embed_jokers(self, one_hot_jokers: torch.Tensor) -> torch.Tensor:
        """Convert (batch, N, NUM_JOKER_TYPES) one-hot jokers to (batch, N, embed_dim).

        Joker index 0 in embedding table is reserved for padding.
        Actual joker types map to indices 1..NUM_JOKER_TYPES.
        """
        valid = one_hot_jokers.sum(dim=-1) > 0  # (batch, N)
        # +1 offset so 0 stays as padding index
        joker_idx = one_hot_jokers.argmax(dim=-1) + 1  # (batch, N)
        joker_idx = joker_idx * valid.long()  # zero out empty slots → padding_idx

        embedded = self.joker_embedding(joker_idx)  # (batch, N, embed_dim)
        return embedded

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if obs.dim() == 1:
            obs = obs.unsqueeze(0)
        batch = obs.shape[0]

        # --- Split flat observation into components ---
        idx = 0
        my_hand_flat = obs[:, idx : idx + self._card_section]
        idx += self._card_section
        opp_hand_flat = obs[:, idx : idx + self._card_section]
        idx += self._card_section

        avail_flat = obs[:, idx : idx + self._joker_section_avail]
        idx += self._joker_section_avail
        my_jk_flat = obs[:, idx : idx + self._joker_section_owned]
        idx += self._joker_section_owned
        opp_jk_flat = obs[:, idx : idx + self._joker_section_owned]
        idx += self._joker_section_owned

        scalars = obs[:, idx:]  # phase(2) + jokers_remaining(1) + scores(2)

        # Reshape
        my_hand = my_hand_flat.view(batch, PLAYER_CARDS, CARD_DIM)
        opp_hand = opp_hand_flat.view(batch, PLAYER_CARDS, CARD_DIM)
        avail_jk = avail_flat.view(batch, JOKER_POOL_SIZE, NUM_JOKER_TYPES)
        my_jk = my_jk_flat.view(batch, MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)
        opp_jk = opp_jk_flat.view(batch, MAX_JOKERS_PER_PLAYER, NUM_JOKER_TYPES)

        # --- Embed ---
        my_hand_emb = self._embed_cards(my_hand).flatten(1)        # (batch, 10*E)
        opp_hand_emb = self._embed_cards(opp_hand).flatten(1)      # (batch, 10*E)
        avail_emb_tokens = self._embed_jokers(avail_jk)            # (batch, 15, E)
        avail_emb = avail_emb_tokens.flatten(1)                    # (batch, 15*E)
        my_jk_emb = self._embed_jokers(my_jk).flatten(1)           # (batch, 8*E)
        opp_jk_emb = self._embed_jokers(opp_jk).flatten(1)         # (batch, 8*E)

        # --- Concatenate everything ---
        x = torch.cat([
            my_hand_emb,
            opp_hand_emb,
            avail_emb,
            my_jk_emb,
            opp_jk_emb,
            scalars,
        ], dim=-1)

        # --- Backbone + heads ---
        features = self.backbone(x)
        action_features = torch.cat(
            [
                features.unsqueeze(1).expand(-1, JOKER_POOL_SIZE, -1),
                avail_emb_tokens,
            ],
            dim=-1,
        )
        logits = self.action_scorer(action_features).squeeze(-1)
        value = self.value_head(features)

        return logits, value


# ---------------------------------------------------------------------------
# Transformer (placeholder for future)
# ---------------------------------------------------------------------------

class TransformerActorCritic(ActorCritic):
    """Transformer-based actor-critic (placeholder).

    Uses the same card/joker embedding tables as the MLP, but treats each
    card and joker as a token and processes them with a Transformer encoder.
    """

    def __init__(
        self,
        embed_dim: int = 64,
        nhead: int = 4,
        num_encoder_layers: int = 4,
        dim_feedforward: int = 256,
    ):
        super().__init__()

        self.card_embedding = nn.Embedding(NUM_RANKS * NUM_SUITS, embed_dim)
        self.joker_embedding = nn.Embedding(NUM_JOKER_TYPES + 1, embed_dim, padding_idx=0)

        # Learnable type tokens to distinguish card groups and joker groups
        # 0=my_card, 1=opp_card, 2=avail_joker, 3=my_joker, 4=opp_joker
        self.type_embedding = nn.Embedding(5, embed_dim)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=nhead,
            dim_feedforward=dim_feedforward, batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)

        self.policy_head = nn.Linear(embed_dim, JOKER_POOL_SIZE)
        self.value_head = nn.Linear(embed_dim, 1)

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        raise NotImplementedError(
            "TransformerActorCritic is a placeholder — implement token "
            "construction and forward pass when ready."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def ensure_supported_model_type(model_type: str) -> None:
    if model_type not in SUPPORTED_MODEL_TYPES:
        supported = ", ".join(SUPPORTED_MODEL_TYPES)
        raise ValueError(
            f"Unsupported model_type {model_type!r}. Supported model types: {supported}."
        )


def build_model(model_type: str = "mlp", **kwargs) -> ActorCritic:
    """Construct an actor-critic model by name."""
    ensure_supported_model_type(model_type)
    return MLPActorCritic(**kwargs)
