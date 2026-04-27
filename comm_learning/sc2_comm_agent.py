"""
Phase 619: Communication Learning for Multi-Agent SC2
CommNet / TarMAC-style learned communication with message gating,
bandwidth constraints, emergent protocol analysis, and ablation support.
"""

from __future__ import annotations

import math
import random
import time
import os
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    import numpy as np


# ============================================================
# Configuration
# ============================================================


@dataclass
class CommConfig:
    """Hyperparameters for the communication learning agent."""

    # Observation / entity
    obs_dim: int = 48  # Per-agent observation dimension
    max_agents: int = 16  # Max agents communicating
    hidden_dim: int = 128  # Internal hidden state dimension

    # Communication
    message_dim: int = 32  # Size of each communicated message
    comm_rounds: int = 2  # Communication rounds per step
    bandwidth_limit: int = 8  # Max messages an agent can send per round
    comm_mode: str = "tarmac"  # "commnet", "tarmac", "broadcast", "hierarchical"

    # Gating
    gate_threshold: float = 0.5  # Message gate activation threshold

    # Action space
    n_actions: int = 10

    # Training
    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_eps: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    batch_size: int = 32

    # Ablation
    communication_enabled: bool = True  # Set False for ablation


# ============================================================
# NumPy Helpers
# ============================================================


def np_softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / (e.sum(axis=axis, keepdims=True) + 1e-12)


def np_sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


def np_tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def np_relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def np_layer_norm(x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    mu = x.mean(axis=-1, keepdims=True)
    sigma = x.std(axis=-1, keepdims=True)
    return (x - mu) / (sigma + eps)


def np_linear(
    x: np.ndarray, W: np.ndarray, b: Optional[np.ndarray] = None
) -> np.ndarray:
    out = x @ W.T
    if b is not None:
        out = out + b
    return out


# ============================================================
# Protocol Analyzer (NumPy-based, works with both backends)
# ============================================================


class ProtocolAnalyzer:
    """Analyze emergent communication protocols from message logs."""

    def __init__(self, message_dim: int, n_bins: int = 16):
        self.message_dim = message_dim
        self.n_bins = n_bins
        self.message_log: List[np.ndarray] = []
        self.gate_log: List[np.ndarray] = []
        self.action_log: List[int] = []
        self.max_log_size = 5000

    def log_messages(
        self,
        messages: np.ndarray,
        gates: Optional[np.ndarray] = None,
        actions: Optional[np.ndarray] = None,
    ):
        """Log messages for analysis. messages: (N, msg_dim) or (B, N, msg_dim)."""
        flat = messages.reshape(-1, self.message_dim)
        self.message_log.append(flat)
        if gates is not None:
            self.gate_log.append(gates.flatten())
        if actions is not None:
            self.action_log.extend(actions.flatten().tolist())
        # Truncate
        if len(self.message_log) > self.max_log_size:
            self.message_log = self.message_log[-self.max_log_size // 2 :]
            self.gate_log = self.gate_log[-self.max_log_size // 2 :]
            self.action_log = self.action_log[-self.max_log_size // 2 :]

    def message_entropy(self) -> float:
        """Estimate entropy of the message distribution (higher = more diverse)."""
        if len(self.message_log) == 0:
            return 0.0
        all_msgs = np.concatenate(self.message_log, axis=0)
        # Discretize each dimension and compute joint entropy
        entropy_sum = 0.0
        for d in range(min(self.message_dim, 8)):  # sample dims for efficiency
            vals = all_msgs[:, d]
            hist, _ = np.histogram(vals, bins=self.n_bins, density=True)
            hist = hist / (hist.sum() + 1e-12)
            hist = hist[hist > 0]
            entropy_sum += -np.sum(hist * np.log(hist + 1e-12))
        return float(entropy_sum / min(self.message_dim, 8))

    def gate_usage_rate(self) -> float:
        """Fraction of messages that pass the gate (are actually sent)."""
        if len(self.gate_log) == 0:
            return 1.0
        all_gates = np.concatenate(self.gate_log)
        return float((all_gates > 0.5).mean())

    def message_correlation_with_actions(self) -> float:
        """Measure if message content correlates with actions taken."""
        if len(self.message_log) == 0 or len(self.action_log) < 10:
            return 0.0
        all_msgs = np.concatenate(self.message_log, axis=0)
        n = min(len(all_msgs), len(self.action_log))
        msgs = all_msgs[:n]
        acts = np.array(self.action_log[:n])
        # Per-action mean message
        unique_actions = np.unique(acts)
        if len(unique_actions) < 2:
            return 0.0
        between_var = 0.0
        total_var = msgs.var(axis=0).sum()
        for a in unique_actions:
            mask = acts == a
            if mask.sum() > 1:
                between_var += (
                    mask.sum()
                    * ((msgs[mask].mean(axis=0) - msgs.mean(axis=0)) ** 2).sum()
                )
        between_var /= n
        if total_var < 1e-8:
            return 0.0
        return float(min(1.0, between_var / (total_var + 1e-8)))

    def report(self) -> Dict[str, float]:
        return {
            "message_entropy": self.message_entropy(),
            "gate_usage_rate": self.gate_usage_rate(),
            "action_correlation": self.message_correlation_with_actions(),
            "total_messages_logged": sum(m.shape[0] for m in self.message_log),
        }


# ============================================================
# NumPy Fallback Communication Networks
# ============================================================


class NumpyCommNet:
    """CommNet-style continuous communication (NumPy fallback)."""

    def __init__(self, cfg: CommConfig, rng: np.random.RandomState):
        self.cfg = cfg
        d, m = cfg.hidden_dim, cfg.message_dim
        scale_d = 1.0 / math.sqrt(d)
        scale_m = 1.0 / math.sqrt(m)

        # Observation encoder
        self.W_enc = rng.randn(d, cfg.obs_dim).astype(np.float32) * (
            1.0 / math.sqrt(cfg.obs_dim)
        )
        self.b_enc = np.zeros(d, dtype=np.float32)

        # Message encoder / decoder per round
        self.msg_encoders = []
        self.msg_decoders = []
        self.gates = []
        for _ in range(cfg.comm_rounds):
            self.msg_encoders.append(
                {
                    "W": rng.randn(m, d).astype(np.float32) * scale_d,
                    "b": np.zeros(m, dtype=np.float32),
                }
            )
            self.msg_decoders.append(
                {
                    "W": rng.randn(d, m).astype(np.float32) * scale_m,
                    "b": np.zeros(d, dtype=np.float32),
                }
            )
            self.gates.append(
                {
                    "W": rng.randn(1, d + m).astype(np.float32)
                    * (1.0 / math.sqrt(d + m)),
                    "b": np.zeros(1, dtype=np.float32),
                }
            )

        # Action head
        self.W_action = rng.randn(cfg.n_actions, d).astype(np.float32) * scale_d
        self.b_action = np.zeros(cfg.n_actions, dtype=np.float32)

        # Value head
        self.W_val1 = rng.randn(d, d).astype(np.float32) * scale_d
        self.b_val1 = np.zeros(d, dtype=np.float32)
        self.W_val2 = rng.randn(1, d).astype(np.float32) * scale_d
        self.b_val2 = np.zeros(1, dtype=np.float32)

    def forward(
        self, obs: np.ndarray, comm_enabled: bool = True
    ) -> Dict[str, np.ndarray]:
        """obs: (B, N, obs_dim) -> action_logits, values, messages, gate_values."""
        B, N, _ = obs.shape

        # Encode observations
        h = np_relu(np_linear(obs, self.W_enc, self.b_enc))  # (B, N, d)

        all_messages = []
        all_gates = []

        for r in range(self.cfg.comm_rounds):
            enc = self.msg_encoders[r]
            dec = self.msg_decoders[r]
            gate_params = self.gates[r]

            # Generate messages
            messages = np_tanh(np_linear(h, enc["W"], enc["b"]))  # (B, N, m)

            # Compute gate
            gate_input = np.concatenate([h, messages], axis=-1)  # (B, N, d+m)
            gate_val = np_sigmoid(
                np_linear(gate_input, gate_params["W"], gate_params["b"])
            )
            gate_val = gate_val.squeeze(-1)  # (B, N)

            all_messages.append(messages)
            all_gates.append(gate_val)

            if comm_enabled:
                # Apply gate
                gated_msgs = messages * (gate_val > self.cfg.gate_threshold)[
                    ..., None
                ].astype(np.float32)

                # Bandwidth constraint: top-K messages per agent
                if self.cfg.bandwidth_limit < N:
                    msg_norms = np.linalg.norm(gated_msgs, axis=-1)  # (B, N)
                    for b_idx in range(B):
                        top_k = np.argsort(msg_norms[b_idx])[
                            -self.cfg.bandwidth_limit :
                        ]
                        mask = np.zeros(N, dtype=np.float32)
                        mask[top_k] = 1.0
                        gated_msgs[b_idx] *= mask[:, None]

                # CommNet aggregation: mean of other agents' messages
                msg_sum = gated_msgs.sum(axis=1, keepdims=True)  # (B, 1, m)
                # Subtract self-message and divide by (N-1)
                incoming = (msg_sum - gated_msgs) / max(N - 1, 1)  # (B, N, m)

                # Decode and integrate
                comm_signal = np_relu(np_linear(incoming, dec["W"], dec["b"]))
                h = np_layer_norm(h + comm_signal)

        # Action logits per agent
        action_logits = np_linear(h, self.W_action, self.b_action)  # (B, N, n_actions)

        # Value per agent
        v_h = np_relu(np_linear(h, self.W_val1, self.b_val1))
        values = np_linear(v_h, self.W_val2, self.b_val2).squeeze(-1)  # (B, N)

        return {
            "action_logits": action_logits,
            "values": values,
            "messages": all_messages,
            "gate_values": all_gates,
            "hidden": h,
        }


class NumpyTarMAC:
    """TarMAC: Targeted Multi-Agent Communication with attention (NumPy)."""

    def __init__(self, cfg: CommConfig, rng: np.random.RandomState):
        self.cfg = cfg
        d, m = cfg.hidden_dim, cfg.message_dim
        scale_d = 1.0 / math.sqrt(d)

        # Observation encoder
        self.W_enc = rng.randn(d, cfg.obs_dim).astype(np.float32) * (
            1.0 / math.sqrt(cfg.obs_dim)
        )
        self.b_enc = np.zeros(d, dtype=np.float32)

        # Per-round query/key/value for targeted communication
        self.rounds = []
        for _ in range(cfg.comm_rounds):
            self.rounds.append(
                {
                    "W_msg": rng.randn(m, d).astype(np.float32) * scale_d,
                    "b_msg": np.zeros(m, dtype=np.float32),
                    "W_key": rng.randn(m, d).astype(np.float32) * scale_d,
                    "b_key": np.zeros(m, dtype=np.float32),
                    "W_query": rng.randn(m, d).astype(np.float32) * scale_d,
                    "b_query": np.zeros(m, dtype=np.float32),
                    "W_integrate": rng.randn(d, d + m).astype(np.float32)
                    * (1.0 / math.sqrt(d + m)),
                    "b_integrate": np.zeros(d, dtype=np.float32),
                    "W_gate": rng.randn(1, d).astype(np.float32) * scale_d,
                    "b_gate": np.zeros(1, dtype=np.float32),
                }
            )

        # Action / value heads
        self.W_action = rng.randn(cfg.n_actions, d).astype(np.float32) * scale_d
        self.b_action = np.zeros(cfg.n_actions, dtype=np.float32)
        self.W_val1 = rng.randn(d, d).astype(np.float32) * scale_d
        self.b_val1 = np.zeros(d, dtype=np.float32)
        self.W_val2 = rng.randn(1, d).astype(np.float32) * scale_d
        self.b_val2 = np.zeros(1, dtype=np.float32)

    def forward(
        self, obs: np.ndarray, comm_enabled: bool = True
    ) -> Dict[str, np.ndarray]:
        B, N, _ = obs.shape
        h = np_relu(np_linear(obs, self.W_enc, self.b_enc))

        all_messages = []
        all_gates = []

        for r_params in self.rounds:
            # Generate messages, keys, queries
            messages = np_tanh(np_linear(h, r_params["W_msg"], r_params["b_msg"]))
            keys = np_linear(h, r_params["W_key"], r_params["b_key"])
            queries = np_linear(h, r_params["W_query"], r_params["b_query"])

            # Gate
            gate_val = np_sigmoid(np_linear(h, r_params["W_gate"], r_params["b_gate"]))
            gate_val = gate_val.squeeze(-1)  # (B, N)
            all_gates.append(gate_val)
            all_messages.append(messages)

            if comm_enabled:
                # Targeted attention: each agent queries all others
                attn_scores = (queries @ keys.transpose(0, 2, 1)) / math.sqrt(
                    keys.shape[-1]
                )
                # Mask self-attention
                eye_mask = np.eye(N, dtype=np.float32)[None, :, :]
                attn_scores = attn_scores - eye_mask * 1e9

                # Apply gate mask: only attend to agents whose gate is open
                gate_mask = (gate_val > self.cfg.gate_threshold).astype(np.float32)
                attn_scores = attn_scores - (1.0 - gate_mask[:, None, :]) * 1e9

                # Bandwidth: keep top-K attention weights
                if self.cfg.bandwidth_limit < N:
                    for b_idx in range(B):
                        for i in range(N):
                            top_k_idx = np.argsort(attn_scores[b_idx, i])[
                                -self.cfg.bandwidth_limit :
                            ]
                            drop_mask = np.ones(N, dtype=np.float32) * (-1e9)
                            drop_mask[top_k_idx] = 0.0
                            attn_scores[b_idx, i] += drop_mask

                attn_weights = np_softmax(attn_scores, axis=-1)  # (B, N, N)
                incoming = attn_weights @ messages  # (B, N, m)

                combined = np.concatenate([h, incoming], axis=-1)
                h = np_layer_norm(
                    np_relu(
                        np_linear(
                            combined, r_params["W_integrate"], r_params["b_integrate"]
                        )
                    )
                )

        action_logits = np_linear(h, self.W_action, self.b_action)
        v_h = np_relu(np_linear(h, self.W_val1, self.b_val1))
        values = np_linear(v_h, self.W_val2, self.b_val2).squeeze(-1)

        return {
            "action_logits": action_logits,
            "values": values,
            "messages": all_messages,
            "gate_values": all_gates,
            "hidden": h,
        }


# ============================================================
# PyTorch Modules
# ============================================================

if TORCH_AVAILABLE:

    class MessageGate(nn.Module):
        """Learned gate deciding when to communicate."""

        def __init__(self, hidden_dim: int):
            super().__init__()
            self.gate_net = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1),
                nn.Sigmoid(),
            )

        def forward(self, h: torch.Tensor) -> torch.Tensor:
            """h: (B, N, d) -> gate: (B, N, 1) in [0, 1]."""
            return self.gate_net(h)

    class CommNetModule(nn.Module):
        """CommNet: continuous mean-field message passing."""

        def __init__(self, cfg: CommConfig):
            super().__init__()
            self.cfg = cfg
            d, m = cfg.hidden_dim, cfg.message_dim

            self.encoder = nn.Sequential(
                nn.Linear(cfg.obs_dim, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            self.msg_encoders = nn.ModuleList()
            self.msg_decoders = nn.ModuleList()
            self.gates = nn.ModuleList()
            self.norms = nn.ModuleList()

            for _ in range(cfg.comm_rounds):
                self.msg_encoders.append(
                    nn.Sequential(
                        nn.Linear(d, m),
                        nn.Tanh(),
                    )
                )
                self.msg_decoders.append(
                    nn.Sequential(
                        nn.Linear(m, d),
                        nn.ReLU(),
                    )
                )
                self.gates.append(MessageGate(d))
                self.norms.append(nn.LayerNorm(d))

        def forward(
            self, obs: torch.Tensor, comm_enabled: bool = True
        ) -> Dict[str, torch.Tensor]:
            B, N, _ = obs.shape
            h = self.encoder(obs)

            all_messages = []
            all_gates = []

            for r in range(self.cfg.comm_rounds):
                messages = self.msg_encoders[r](h)  # (B, N, m)
                gate_val = self.gates[r](h)  # (B, N, 1)

                all_messages.append(messages.detach())
                all_gates.append(gate_val.squeeze(-1).detach())

                if comm_enabled:
                    # Apply gate with straight-through estimator
                    hard_gate = (gate_val > self.cfg.gate_threshold).float()
                    gate_ste = gate_val + (hard_gate - gate_val).detach()
                    gated_msgs = messages * gate_ste

                    # Bandwidth constraint
                    if self.cfg.bandwidth_limit < N:
                        msg_norms = gated_msgs.norm(dim=-1)  # (B, N)
                        _, top_idx = msg_norms.topk(self.cfg.bandwidth_limit, dim=-1)
                        bw_mask = torch.zeros(B, N, 1, device=obs.device)
                        bw_mask.scatter_(1, top_idx.unsqueeze(-1), 1.0)
                        gated_msgs = gated_msgs * bw_mask

                    # Mean-field: average of others' messages
                    msg_sum = gated_msgs.sum(dim=1, keepdim=True)
                    incoming = (msg_sum - gated_msgs) / max(N - 1, 1)

                    comm_signal = self.msg_decoders[r](incoming)
                    h = self.norms[r](h + comm_signal)

            return {"hidden": h, "messages": all_messages, "gate_values": all_gates}

    class TarMACModule(nn.Module):
        """TarMAC: Targeted Multi-Agent Communication with attention."""

        def __init__(self, cfg: CommConfig):
            super().__init__()
            self.cfg = cfg
            d, m = cfg.hidden_dim, cfg.message_dim

            self.encoder = nn.Sequential(
                nn.Linear(cfg.obs_dim, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            self.rounds = nn.ModuleList()
            for _ in range(cfg.comm_rounds):
                self.rounds.append(
                    nn.ModuleDict(
                        {
                            "msg": nn.Sequential(nn.Linear(d, m), nn.Tanh()),
                            "key": nn.Linear(d, m),
                            "query": nn.Linear(d, m),
                            "integrate": nn.Sequential(
                                nn.Linear(d + m, d),
                                nn.ReLU(),
                                nn.LayerNorm(d),
                            ),
                            "gate": MessageGate(d),
                        }
                    )
                )

        def forward(
            self, obs: torch.Tensor, comm_enabled: bool = True
        ) -> Dict[str, torch.Tensor]:
            B, N, _ = obs.shape
            h = self.encoder(obs)
            device = obs.device

            all_messages = []
            all_gates = []

            for r_mods in self.rounds:
                messages = r_mods["msg"](h)
                keys = r_mods["key"](h)
                queries = r_mods["query"](h)
                gate_val = r_mods["gate"](h)  # (B, N, 1)

                all_messages.append(messages.detach())
                all_gates.append(gate_val.squeeze(-1).detach())

                if comm_enabled:
                    attn_scores = (queries @ keys.transpose(-2, -1)) / math.sqrt(
                        keys.size(-1)
                    )
                    # Mask self
                    self_mask = torch.eye(N, device=device).unsqueeze(0) * (-1e9)
                    attn_scores = attn_scores + self_mask

                    # Gate mask with STE
                    hard_gate = (gate_val > self.cfg.gate_threshold).float()
                    gate_ste = gate_val + (hard_gate - gate_val).detach()
                    gate_broad = gate_ste.transpose(-2, -1)  # (B, 1, N)
                    attn_scores = attn_scores + (1.0 - gate_broad) * (-1e9)

                    # Bandwidth
                    if self.cfg.bandwidth_limit < N:
                        _, top_idx = attn_scores.topk(self.cfg.bandwidth_limit, dim=-1)
                        bw_mask = torch.zeros_like(attn_scores).fill_(float("-inf"))
                        bw_mask.scatter_(-1, top_idx, 0.0)
                        attn_scores = attn_scores + bw_mask

                    attn_weights = F.softmax(attn_scores, dim=-1)
                    incoming = attn_weights @ messages

                    combined = torch.cat([h, incoming], dim=-1)
                    h = r_mods["integrate"](combined)

            return {"hidden": h, "messages": all_messages, "gate_values": all_gates}

    class HierarchicalCommModule(nn.Module):
        """Hierarchical communication: agents grouped into squads with leaders."""

        def __init__(self, cfg: CommConfig, squad_size: int = 4):
            super().__init__()
            self.cfg = cfg
            self.squad_size = squad_size
            d, m = cfg.hidden_dim, cfg.message_dim

            self.encoder = nn.Sequential(
                nn.Linear(cfg.obs_dim, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            # Intra-squad communication
            self.intra_msg = nn.Sequential(nn.Linear(d, m), nn.Tanh())
            self.intra_attn_q = nn.Linear(d, m)
            self.intra_attn_k = nn.Linear(d, m)
            self.intra_integrate = nn.Sequential(
                nn.Linear(d + m, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            # Leader selection
            self.leader_score = nn.Linear(d, 1)

            # Inter-squad (leader-to-leader)
            self.inter_msg = nn.Sequential(nn.Linear(d, m), nn.Tanh())
            self.inter_attn_q = nn.Linear(d, m)
            self.inter_attn_k = nn.Linear(d, m)
            self.inter_integrate = nn.Sequential(
                nn.Linear(d + m, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            # Broadcast from leader to squad
            self.broadcast_proj = nn.Sequential(
                nn.Linear(d + d, d),
                nn.ReLU(),
                nn.LayerNorm(d),
            )

            self.gate = MessageGate(d)

        def forward(
            self, obs: torch.Tensor, comm_enabled: bool = True
        ) -> Dict[str, torch.Tensor]:
            B, N, _ = obs.shape
            h = self.encoder(obs)
            device = obs.device

            gate_val = self.gate(h).squeeze(-1)  # (B, N)
            all_messages = []
            all_gates = [gate_val.detach()]

            if not comm_enabled:
                return {"hidden": h, "messages": [], "gate_values": all_gates}

            n_squads = max(1, N // self.squad_size)
            squad_assignments = torch.arange(N, device=device) % n_squads

            # -- Intra-squad communication --
            msgs = self.intra_msg(h)
            queries = self.intra_attn_q(h)
            keys = self.intra_attn_k(h)
            all_messages.append(msgs.detach())

            attn_scores = (queries @ keys.transpose(-2, -1)) / math.sqrt(msgs.size(-1))
            # Mask agents not in same squad
            squad_mask = (
                squad_assignments.unsqueeze(0) != squad_assignments.unsqueeze(1)
            ).float() * (-1e9)
            # Mask self
            self_mask = torch.eye(N, device=device) * (-1e9)
            attn_scores = attn_scores + squad_mask.unsqueeze(0) + self_mask.unsqueeze(0)

            attn_weights = F.softmax(attn_scores, dim=-1)
            incoming = attn_weights @ msgs
            h = self.intra_integrate(torch.cat([h, incoming], dim=-1))

            # -- Leader selection per squad --
            leader_scores = self.leader_score(h).squeeze(-1)  # (B, N)
            leader_h_list = []
            leader_indices = []
            for s in range(n_squads):
                s_mask = squad_assignments == s
                s_scores = leader_scores[:, s_mask]  # (B, squad_size)
                _, best = s_scores.max(dim=-1)  # (B,)
                s_indices = torch.where(s_mask)[0]
                l_idx = s_indices[best[0]]  # simplified: same leader across batch
                leader_indices.append(l_idx.item())
                leader_h_list.append(h[:, l_idx])  # (B, d)

            if len(leader_h_list) > 1:
                leader_h = torch.stack(leader_h_list, dim=1)  # (B, n_squads, d)

                # Inter-squad communication among leaders
                l_msgs = self.inter_msg(leader_h)
                l_q = self.inter_attn_q(leader_h)
                l_k = self.inter_attn_k(leader_h)
                all_messages.append(l_msgs.detach())

                l_attn = (l_q @ l_k.transpose(-2, -1)) / math.sqrt(l_msgs.size(-1))
                l_attn = l_attn + torch.eye(n_squads, device=device).unsqueeze(0) * (
                    -1e9
                )
                l_weights = F.softmax(l_attn, dim=-1)
                l_incoming = l_weights @ l_msgs
                leader_h = self.inter_integrate(
                    torch.cat([leader_h, l_incoming], dim=-1)
                )

                # Broadcast back to squads
                for s in range(n_squads):
                    s_mask = squad_assignments == s
                    leader_broadcast = leader_h[:, s : s + 1].expand(
                        -1, s_mask.sum(), -1
                    )
                    h_squad = h[:, s_mask]
                    h[:, s_mask] = self.broadcast_proj(
                        torch.cat([h_squad, leader_broadcast], dim=-1)
                    )

            return {"hidden": h, "messages": all_messages, "gate_values": all_gates}

    class CommPolicyNetwork(nn.Module):
        """Complete communication-based policy/value network."""

        def __init__(self, cfg: CommConfig):
            super().__init__()
            self.cfg = cfg

            if cfg.comm_mode == "commnet":
                self.comm = CommNetModule(cfg)
            elif cfg.comm_mode == "tarmac":
                self.comm = TarMACModule(cfg)
            elif cfg.comm_mode == "hierarchical":
                self.comm = HierarchicalCommModule(cfg)
            elif cfg.comm_mode == "broadcast":
                self.comm = CommNetModule(cfg)  # CommNet is broadcast by default
            else:
                raise ValueError(f"Unknown comm_mode: {cfg.comm_mode}")

            self.action_head = nn.Sequential(
                nn.Linear(cfg.hidden_dim, cfg.hidden_dim),
                nn.ReLU(),
                nn.Linear(cfg.hidden_dim, cfg.n_actions),
            )
            self.value_head = nn.Sequential(
                nn.Linear(cfg.hidden_dim, cfg.hidden_dim),
                nn.ReLU(),
                nn.Linear(cfg.hidden_dim, 1),
            )

        def forward(
            self, obs: torch.Tensor, comm_enabled: Optional[bool] = None
        ) -> Dict[str, torch.Tensor]:
            if comm_enabled is None:
                comm_enabled = self.cfg.communication_enabled

            comm_out = self.comm(obs, comm_enabled=comm_enabled)
            h = comm_out["hidden"]

            action_logits = self.action_head(h)  # (B, N, n_actions)
            values = self.value_head(h).squeeze(-1)  # (B, N)

            return {
                "action_logits": action_logits,
                "values": values,
                "messages": comm_out.get("messages", []),
                "gate_values": comm_out.get("gate_values", []),
            }


# ============================================================
# SC2 Communication Agent
# ============================================================


class SC2CommAgent:
    """Multi-agent SC2 bot with learned communication.

    Supports CommNet, TarMAC, hierarchical, and broadcast topologies.
    Includes protocol analysis, ablation mode, and PPO training.
    """

    ACTION_NAMES = [
        "no_op",
        "attack",
        "move",
        "hold",
        "patrol",
        "gather",
        "build",
        "ability",
        "retreat",
        "regroup",
    ]

    def __init__(self, cfg: Optional[CommConfig] = None, seed: int = 42):
        self.cfg = cfg or CommConfig()
        self.seed = seed
        self.step_count = 0
        self.analyzer = ProtocolAnalyzer(self.cfg.message_dim)

        if TORCH_AVAILABLE:
            torch.manual_seed(seed)
            self.network = CommPolicyNetwork(self.cfg)
            self.optimizer = torch.optim.Adam(self.network.parameters(), lr=self.cfg.lr)
            self.use_torch = True
        else:
            rng = np.random.RandomState(seed)
            if self.cfg.comm_mode == "tarmac":
                self.network = NumpyTarMAC(self.cfg, rng)
            else:
                self.network = NumpyCommNet(self.cfg, rng)
            self.use_torch = False

        self._trajectory: List[Dict[str, Any]] = []

    @property
    def param_count(self) -> int:
        if self.use_torch:
            return sum(p.numel() for p in self.network.parameters())
        return 0

    # ---- observation helpers ----

    @staticmethod
    def _dummy_observation(
        batch_size: int, n_agents: int, cfg: CommConfig
    ) -> np.ndarray:
        rng = np.random.RandomState(0)
        return rng.randn(batch_size, n_agents, cfg.obs_dim).astype(np.float32)

    def _preprocess_units(self, units: List[Dict[str, Any]]) -> np.ndarray:
        """Convert unit dicts to observation array. Each unit becomes an agent."""
        cfg = self.cfg
        n = min(len(units), cfg.max_agents)
        obs = np.zeros((1, cfg.max_agents, cfg.obs_dim), dtype=np.float32)

        for i in range(n):
            u = units[i]
            obs[0, i, 0] = u.get("type_id", 0) / 300.0
            obs[0, i, 1] = u.get("health", 0) / 500.0
            obs[0, i, 2] = u.get("shield", 0) / 200.0
            obs[0, i, 3] = u.get("energy", 0) / 200.0
            obs[0, i, 4] = u.get("x", 0) / 200.0
            obs[0, i, 5] = u.get("y", 0) / 200.0
            obs[0, i, 6] = 1.0 if u.get("is_friendly", True) else 0.0
            obs[0, i, 7] = u.get("weapon_cooldown", 0) / 50.0
            obs[0, i, 8] = 1.0 if u.get("is_flying", False) else 0.0
            obs[0, i, 9] = u.get("ground_range", 0) / 15.0
        return obs

    # ---- action selection ----

    def act(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
        comm_enabled: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Select actions for all agents.
        obs: (B, N, obs_dim)
        """
        if comm_enabled is None:
            comm_enabled = self.cfg.communication_enabled

        if self.use_torch:
            self.network.eval()
            with torch.no_grad():
                obs_t = torch.from_numpy(obs)
                out = self.network(obs_t, comm_enabled=comm_enabled)
                action_logits = out["action_logits"]
                probs = F.softmax(action_logits, dim=-1)

                if deterministic:
                    actions = probs.argmax(dim=-1)
                else:
                    B, N, A = probs.shape
                    actions = torch.multinomial(probs.view(-1, A), 1).view(B, N)

                result = {
                    "actions": actions.cpu().numpy(),
                    "action_probs": probs.cpu().numpy(),
                    "values": out["values"].cpu().numpy(),
                }

                # Log messages for analysis
                if out["messages"]:
                    self.analyzer.log_messages(
                        out["messages"][-1].cpu().numpy(),
                        gates=(
                            out["gate_values"][-1].cpu().numpy()
                            if out["gate_values"]
                            else None
                        ),
                        actions=result["actions"],
                    )
        else:
            out = self.network.forward(obs, comm_enabled=comm_enabled)
            action_probs = np_softmax(out["action_logits"], axis=-1)

            if deterministic:
                actions = np.argmax(action_probs, axis=-1)
            else:
                B, N, A = action_probs.shape
                actions = np.zeros((B, N), dtype=np.int64)
                rng = np.random.RandomState(self.step_count)
                for b in range(B):
                    for n in range(N):
                        actions[b, n] = rng.choice(A, p=action_probs[b, n])

            result = {
                "actions": actions,
                "action_probs": action_probs,
                "values": out["values"],
            }

            if out["messages"]:
                self.analyzer.log_messages(
                    out["messages"][-1],
                    gates=out["gate_values"][-1] if out["gate_values"] else None,
                    actions=actions,
                )

        self.step_count += 1
        return result

    def act_on_game_state(
        self, game_state: Dict[str, Any], deterministic: bool = False
    ) -> List[Dict[str, Any]]:
        """Raw game state -> per-unit action decisions."""
        units = game_state.get("units", [])
        friendly = [u for u in units if u.get("is_friendly", True)]
        obs = self._preprocess_units(friendly)
        result = self.act(obs, deterministic=deterministic)

        decisions = []
        n = min(len(friendly), self.cfg.max_agents)
        for i in range(n):
            action_idx = int(result["actions"][0, i])
            decisions.append(
                {
                    "unit_tag": friendly[i].get("tag", i),
                    "action_type": self.ACTION_NAMES[action_idx],
                    "action_idx": action_idx,
                    "value_estimate": float(result["values"][0, i]),
                    "action_probs": {
                        name: float(result["action_probs"][0, i, j])
                        for j, name in enumerate(self.ACTION_NAMES)
                    },
                }
            )
        return decisions

    # ---- ablation ----

    def run_ablation(self, obs: np.ndarray, n_trials: int = 20) -> Dict[str, Any]:
        """Compare performance with and without communication."""
        results_comm = {"values": [], "entropy": []}
        results_no_comm = {"values": [], "entropy": []}

        for _ in range(n_trials):
            # With communication
            res = self.act(obs, deterministic=False, comm_enabled=True)
            results_comm["values"].append(res["values"].mean())
            probs = res["action_probs"]
            ent = -(probs * np.log(probs + 1e-8)).sum(axis=-1).mean()
            results_comm["entropy"].append(ent)

            # Without communication
            res = self.act(obs, deterministic=False, comm_enabled=False)
            results_no_comm["values"].append(res["values"].mean())
            probs = res["action_probs"]
            ent = -(probs * np.log(probs + 1e-8)).sum(axis=-1).mean()
            results_no_comm["entropy"].append(ent)

        return {
            "comm_enabled": {
                "mean_value": float(np.mean(results_comm["values"])),
                "mean_entropy": float(np.mean(results_comm["entropy"])),
            },
            "comm_disabled": {
                "mean_value": float(np.mean(results_no_comm["values"])),
                "mean_entropy": float(np.mean(results_no_comm["entropy"])),
            },
            "value_diff": float(
                np.mean(results_comm["values"]) - np.mean(results_no_comm["values"])
            ),
            "entropy_diff": float(
                np.mean(results_comm["entropy"]) - np.mean(results_no_comm["entropy"])
            ),
        }

    # ---- PPO training ----

    def store_transition(
        self,
        obs: np.ndarray,
        actions: np.ndarray,
        rewards: np.ndarray,
        dones: np.ndarray,
        log_probs: np.ndarray,
        values: np.ndarray,
    ):
        self._trajectory.append(
            {
                "obs": obs.copy(),
                "actions": actions.copy(),
                "rewards": rewards.copy(),
                "dones": dones.copy(),
                "log_probs": log_probs.copy(),
                "values": values.copy(),
            }
        )

    def _compute_gae(
        self,
        rewards: np.ndarray,
        values: np.ndarray,
        dones: np.ndarray,
        last_values: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """GAE computation for multi-agent: rewards/values shape (T, N)."""
        T, N = rewards.shape
        advantages = np.zeros((T, N), dtype=np.float32)
        gae = np.zeros(N, dtype=np.float32)
        gamma, lam = self.cfg.gamma, self.cfg.gae_lambda

        for t in reversed(range(T)):
            next_val = last_values if t == T - 1 else values[t + 1]
            next_non_terminal = 1.0 - dones[t].astype(np.float32)
            delta = rewards[t] + gamma * next_val * next_non_terminal - values[t]
            gae = delta + gamma * lam * next_non_terminal * gae
            advantages[t] = gae

        returns = advantages + values
        return advantages, returns

    def update(self) -> Dict[str, float]:
        if not self.use_torch or len(self._trajectory) == 0:
            self._trajectory.clear()
            return {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0}

        T = len(self._trajectory)
        N = self._trajectory[0]["actions"].shape[-1]

        # Stack trajectory
        obs_all = np.stack([t["obs"] for t in self._trajectory])  # (T, B, N, obs_dim)
        actions_all = np.stack([t["actions"] for t in self._trajectory])  # (T, B, N)
        rewards_all = np.stack([t["rewards"] for t in self._trajectory])  # (T, B, N)
        dones_all = np.stack([t["dones"] for t in self._trajectory])
        old_lp_all = np.stack([t["log_probs"] for t in self._trajectory])
        values_all = np.stack([t["values"] for t in self._trajectory])

        # Use first batch element for simplicity
        b = 0
        rewards = rewards_all[:, b]  # (T, N)
        values = values_all[:, b]
        dones = dones_all[:, b]
        last_values = values[-1]

        advantages, returns = self._compute_gae(rewards, values, dones, last_values)
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        self.network.train()
        adv_t = torch.from_numpy(advantages.flatten())
        ret_t = torch.from_numpy(returns.flatten())
        old_lp_t = torch.from_numpy(old_lp_all[:, b].flatten())

        total_pl, total_vl, total_ent = 0.0, 0.0, 0.0
        n_updates = 0

        for _ in range(4):
            for t_start in range(0, T, max(1, self.cfg.batch_size)):
                t_end = min(t_start + self.cfg.batch_size, T)
                sl = slice(t_start, t_end)
                bs = t_end - t_start

                obs_batch = torch.from_numpy(obs_all[sl, b])  # (bs, N, obs_dim)
                out = self.network(obs_batch)

                action_dist = torch.distributions.Categorical(
                    logits=out["action_logits"]
                )
                acts = torch.from_numpy(actions_all[sl, b])  # (bs, N)
                new_lp = action_dist.log_prob(acts).flatten()

                flat_start = t_start * N
                flat_end = t_end * N
                ratio = torch.exp(new_lp - old_lp_t[flat_start:flat_end])
                adv_slice = adv_t[flat_start:flat_end]

                surr1 = ratio * adv_slice
                surr2 = (
                    torch.clamp(ratio, 1 - self.cfg.clip_eps, 1 + self.cfg.clip_eps)
                    * adv_slice
                )
                policy_loss = -torch.min(surr1, surr2).mean()

                value_loss = F.mse_loss(
                    out["values"].flatten(), ret_t[flat_start:flat_end]
                )
                entropy = action_dist.entropy().mean()

                loss = (
                    policy_loss
                    + self.cfg.value_coef * value_loss
                    - self.cfg.entropy_coef * entropy
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(
                    self.network.parameters(), self.cfg.max_grad_norm
                )
                self.optimizer.step()

                total_pl += policy_loss.item()
                total_vl += value_loss.item()
                total_ent += entropy.item()
                n_updates += 1

        self._trajectory.clear()
        n_updates = max(n_updates, 1)
        return {
            "policy_loss": total_pl / n_updates,
            "value_loss": total_vl / n_updates,
            "entropy": total_ent / n_updates,
        }

    # ---- save / load ----

    def save(self, path: str):
        if self.use_torch:
            torch.save(
                {
                    "network": self.network.state_dict(),
                    "optimizer": self.optimizer.state_dict(),
                    "cfg": self.cfg,
                    "step_count": self.step_count,
                },
                path,
            )

    def load(self, path: str):
        if self.use_torch:
            ckpt = torch.load(path, map_location="cpu", weights_only=False)
            self.network.load_state_dict(ckpt["network"])
            self.optimizer.load_state_dict(ckpt["optimizer"])
            self.step_count = ckpt.get("step_count", 0)

    # ---- diagnostics ----

    def protocol_report(self) -> Dict[str, float]:
        return self.analyzer.report()

    def summary(self) -> str:
        lines = [
            "SC2CommAgent Summary",
            f"  Backend:       {'PyTorch' if self.use_torch else 'NumPy'}",
            f"  comm_mode:     {self.cfg.comm_mode}",
            f"  comm_rounds:   {self.cfg.comm_rounds}",
            f"  message_dim:   {self.cfg.message_dim}",
            f"  hidden_dim:    {self.cfg.hidden_dim}",
            f"  max_agents:    {self.cfg.max_agents}",
            f"  bandwidth:     {self.cfg.bandwidth_limit}",
            f"  gate_threshold:{self.cfg.gate_threshold}",
            f"  n_actions:     {self.cfg.n_actions}",
            f"  comm_enabled:  {self.cfg.communication_enabled}",
            f"  steps_taken:   {self.step_count}",
        ]
        if self.use_torch:
            lines.append(f"  parameters:    {self.param_count:,}")
        return "\n".join(lines)


# ============================================================
# CLI Demo
# ============================================================


def _demo_numpy_commnet():
    print("=" * 60)
    print("NumPy CommNet Demo")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=8,
        hidden_dim=64,
        message_dim=16,
        comm_rounds=2,
        obs_dim=48,
        bandwidth_limit=4,
    )
    rng = np.random.RandomState(42)
    net = NumpyCommNet(cfg, rng)

    B, N = 2, 8
    obs = rng.randn(B, N, cfg.obs_dim).astype(np.float32)

    t0 = time.time()
    out = net.forward(obs, comm_enabled=True)
    dt = time.time() - t0

    print(f"  Batch: {B}, Agents: {N}")
    print(f"  Action logits shape: {out['action_logits'].shape}")
    print(f"  Values shape:        {out['values'].shape}")
    print(f"  Messages per round:  {[m.shape for m in out['messages']]}")
    print(f"  Gate values:         {[g.shape for g in out['gate_values']]}")
    print(f"  Latency:             {dt*1000:.1f} ms")

    # Without communication
    out_no_comm = net.forward(obs, comm_enabled=False)
    val_diff = out["values"].mean() - out_no_comm["values"].mean()
    print(f"  Value diff (comm vs no-comm): {val_diff:.4f}")
    print()


def _demo_numpy_tarmac():
    print("=" * 60)
    print("NumPy TarMAC Demo")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=8,
        hidden_dim=64,
        message_dim=16,
        comm_rounds=2,
        obs_dim=48,
        bandwidth_limit=4,
        comm_mode="tarmac",
    )
    rng = np.random.RandomState(42)
    net = NumpyTarMAC(cfg, rng)

    B, N = 2, 8
    obs = rng.randn(B, N, cfg.obs_dim).astype(np.float32)

    t0 = time.time()
    out = net.forward(obs, comm_enabled=True)
    dt = time.time() - t0

    print(f"  Batch: {B}, Agents: {N}")
    print(f"  Action logits shape: {out['action_logits'].shape}")
    print(f"  Latency:             {dt*1000:.1f} ms")
    print()


def _demo_torch_comm():
    print("=" * 60)
    print("PyTorch Communication Demo")
    print("=" * 60)

    for mode in ["commnet", "tarmac", "hierarchical"]:
        cfg = CommConfig(
            max_agents=12,
            hidden_dim=128,
            message_dim=32,
            comm_rounds=2,
            obs_dim=48,
            comm_mode=mode,
            bandwidth_limit=6,
        )
        agent = SC2CommAgent(cfg, seed=42)
        print(f"\n  --- Mode: {mode} ---")
        print(agent.summary())

        obs = SC2CommAgent._dummy_observation(4, 12, cfg)

        # Warm-up
        _ = agent.act(obs)

        t0 = time.time()
        for _ in range(10):
            result = agent.act(obs)
        dt = (time.time() - t0) / 10

        print(f"  Avg latency:   {dt*1000:.1f} ms")
        print(f"  Actions shape: {result['actions'].shape}")
        print(
            f"  Values range:  [{result['values'].min():.3f}, {result['values'].max():.3f}]"
        )

    print()


def _demo_protocol_analysis():
    print("=" * 60)
    print("Emergent Protocol Analysis Demo")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=8,
        hidden_dim=128,
        message_dim=32,
        comm_rounds=2,
        obs_dim=48,
        comm_mode="tarmac",
    )
    agent = SC2CommAgent(cfg, seed=42)

    # Run many steps to build up message log
    for step in range(100):
        obs = np.random.randn(1, 8, cfg.obs_dim).astype(np.float32)
        agent.act(obs)

    report = agent.protocol_report()
    print(f"  Message entropy:      {report['message_entropy']:.4f}")
    print(f"  Gate usage rate:      {report['gate_usage_rate']:.4f}")
    print(f"  Action correlation:   {report['action_correlation']:.4f}")
    print(f"  Total msgs logged:    {report['total_messages_logged']}")
    print()


def _demo_ablation():
    print("=" * 60)
    print("Communication Ablation Demo")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=8,
        hidden_dim=128,
        message_dim=32,
        comm_rounds=2,
        obs_dim=48,
        comm_mode="tarmac",
    )
    agent = SC2CommAgent(cfg, seed=42)

    obs = SC2CommAgent._dummy_observation(1, 8, cfg)
    ablation = agent.run_ablation(obs, n_trials=30)

    print(
        f"  With comm    - value: {ablation['comm_enabled']['mean_value']:.4f}, "
        f"entropy: {ablation['comm_enabled']['mean_entropy']:.4f}"
    )
    print(
        f"  Without comm - value: {ablation['comm_disabled']['mean_value']:.4f}, "
        f"entropy: {ablation['comm_disabled']['mean_entropy']:.4f}"
    )
    print(f"  Value diff:    {ablation['value_diff']:.4f}")
    print(f"  Entropy diff:  {ablation['entropy_diff']:.4f}")
    print()


def _demo_game_state():
    print("=" * 60)
    print("Game State Integration Demo")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=8,
        hidden_dim=128,
        message_dim=32,
        comm_rounds=2,
        obs_dim=48,
        comm_mode="tarmac",
    )
    agent = SC2CommAgent(cfg, seed=42)

    game_state = {
        "units": [
            {
                "type_id": 84,
                "x": 50,
                "y": 50,
                "health": 45,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "is_visible": True,
                "tag": 1001,
            },
            {
                "type_id": 84,
                "x": 52,
                "y": 48,
                "health": 40,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "is_visible": True,
                "tag": 1002,
            },
            {
                "type_id": 105,
                "x": 55,
                "y": 53,
                "health": 35,
                "shield": 0,
                "energy": 0,
                "is_friendly": True,
                "is_visible": True,
                "tag": 1003,
            },
            {
                "type_id": 48,
                "x": 80,
                "y": 60,
                "health": 150,
                "shield": 50,
                "energy": 0,
                "is_friendly": True,
                "is_visible": True,
                "tag": 1004,
            },
        ],
    }

    decisions = agent.act_on_game_state(game_state)
    for d in decisions:
        print(
            f"  Unit {d['unit_tag']}: {d['action_type']} "
            f"(value={d['value_estimate']:.3f})"
        )
    print()


def _demo_ppo_smoke():
    print("=" * 60)
    print("PPO Training Smoke Test")
    print("=" * 60)

    cfg = CommConfig(
        max_agents=4,
        hidden_dim=64,
        message_dim=16,
        comm_rounds=1,
        obs_dim=48,
        comm_mode="commnet",
    )
    agent = SC2CommAgent(cfg, seed=42)

    for step in range(16):
        obs = SC2CommAgent._dummy_observation(1, 4, cfg)
        result = agent.act(obs)
        log_probs = np.log(
            result["action_probs"][0, np.arange(4), result["actions"][0]] + 1e-8
        )
        rewards = np.random.uniform(-1, 1, (1, 4)).astype(np.float32)
        dones = np.zeros((1, 4), dtype=np.float32)
        if step == 15:
            dones[:] = 1.0
        agent.store_transition(
            obs, result["actions"], rewards, dones, log_probs[None], result["values"]
        )

    metrics = agent.update()
    print(f"  Policy loss: {metrics['policy_loss']:.4f}")
    print(f"  Value loss:  {metrics['value_loss']:.4f}")
    print(f"  Entropy:     {metrics['entropy']:.4f}")
    print()


def main():
    print("Phase 619: Communication Learning for SC2")
    print(f"Backend: {'PyTorch' if TORCH_AVAILABLE else 'NumPy (fallback)'}")
    print()

    _demo_numpy_commnet()
    _demo_numpy_tarmac()

    if TORCH_AVAILABLE:
        _demo_torch_comm()
        _demo_protocol_analysis()
        _demo_ablation()
        _demo_game_state()
        _demo_ppo_smoke()
    else:
        print("PyTorch not available; torch demos skipped.")
        print()
        cfg = CommConfig(
            max_agents=8, hidden_dim=64, message_dim=16, comm_rounds=2, obs_dim=48
        )
        agent = SC2CommAgent(cfg, seed=42)
        obs = SC2CommAgent._dummy_observation(1, 8, cfg)
        result = agent.act(obs)
        print(f"  NumPy agent actions: {result['actions']}")
        print(f"  Protocol report:     {agent.protocol_report()}")

    print()
    print("Phase 619 demo complete.")


if __name__ == "__main__":
    main()
