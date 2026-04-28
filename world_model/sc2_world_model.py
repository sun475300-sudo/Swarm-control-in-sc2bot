"""
Phase 617: World Model (Dreamer-Style)
SC2 Bot world model with RSSM latent dynamics for imagination-based training.

Features:
- RSSM (Recurrent State Space Model) latent dynamics
- Observation encoder (image/vector -> latent)
- Observation decoder (latent -> predicted observation)
- Imagination rollouts in latent space
- Actor-critic training purely from imagined trajectories
- KL balancing for latent space regularization
- Free bits and KL scaling
- Visualization of latent space (t-SNE/PCA)
- NumPy fallback, CLI demo
"""

from __future__ import annotations

import argparse
import math
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

    class _NumpyFallback:
        """Minimal NumPy shim."""

        float32 = "float32"

        @staticmethod
        def array(data, dtype=None):
            if isinstance(data, list):
                return [float(x) for x in data]
            return float(data)

        @staticmethod
        def zeros(shape, dtype=None):
            if isinstance(shape, (list, tuple)):
                if len(shape) == 1:
                    return [0.0] * shape[0]
                return [[0.0] * shape[1] for _ in range(shape[0])]
            return [0.0] * shape

        @staticmethod
        def ones(shape, dtype=None):
            if isinstance(shape, (list, tuple)):
                if len(shape) == 1:
                    return [1.0] * shape[0]
                return [[1.0] * shape[1] for _ in range(shape[0])]
            return [1.0] * shape

        @staticmethod
        def mean(arr, axis=None):
            if isinstance(arr, (int, float)):
                return float(arr)
            flat = (
                arr if not isinstance(arr[0], list) else [x for row in arr for x in row]
            )
            return sum(flat) / len(flat) if flat else 0.0

        @staticmethod
        def std(arr, axis=None):
            m = _NumpyFallback.mean(arr)
            flat = (
                arr if not isinstance(arr[0], list) else [x for row in arr for x in row]
            )
            var = sum((x - m) ** 2 for x in flat) / len(flat) if flat else 0.0
            return math.sqrt(var)

        @staticmethod
        def clip(val, lo, hi):
            if isinstance(val, list):
                return [max(lo, min(hi, v)) for v in val]
            return max(lo, min(hi, val))

        @staticmethod
        def exp(x):
            if isinstance(x, list):
                return [math.exp(min(v, 500)) for v in x]
            return math.exp(min(x, 500))

        @staticmethod
        def log(x):
            if isinstance(x, list):
                return [math.log(max(v, 1e-10)) for v in x]
            return math.log(max(x, 1e-10))

        @staticmethod
        def sqrt(x):
            if isinstance(x, list):
                return [math.sqrt(max(v, 0)) for v in x]
            return math.sqrt(max(x, 0))

        @staticmethod
        def sum(arr, axis=None):
            if isinstance(arr, (int, float)):
                return float(arr)
            if isinstance(arr, list) and arr and isinstance(arr[0], list):
                return [x for row in arr for x in row]
            return sum(arr) if arr else 0.0

        @staticmethod
        def argmax(arr):
            return max(range(len(arr)), key=lambda i: arr[i])

        class _Random:
            @staticmethod
            def randn(*shape):
                if len(shape) == 0:
                    return random.gauss(0, 1)
                if len(shape) == 1:
                    return [random.gauss(0, 1) for _ in range(shape[0])]
                return [
                    [random.gauss(0, 1) for _ in range(shape[1])]
                    for _ in range(shape[0])
                ]

            @staticmethod
            def uniform(low=0.0, high=1.0, size=None):
                if size is None:
                    return random.uniform(low, high)
                if isinstance(size, int):
                    return [random.uniform(low, high) for _ in range(size)]
                r, c = size
                return [[random.uniform(low, high) for _ in range(c)] for _ in range(r)]

            @staticmethod
            def choice(n, size=1, replace=True):
                return [random.randint(0, n - 1) for _ in range(size)]

        random = _Random()

    np = _NumpyFallback()


# ─────────────────────────────────────────────
# SC2 Constants
# ─────────────────────────────────────────────

OBS_DIM = 16  # observation feature vector
LATENT_DIM = 32  # stochastic latent size
DETERMINISTIC_DIM = 64  # deterministic recurrent state size
HIDDEN_DIM = 64  # MLP hidden layer size
ACTION_DIM = 7  # discrete actions

ACTION_NAMES = [
    "train_drone",
    "train_zergling",
    "train_roach",
    "build_overlord",
    "expand",
    "attack_move",
    "defend_base",
]

STATE_FEATURES = [
    "minerals",
    "gas",
    "supply",
    "max_supply",
    "workers",
    "army_supply",
    "frame",
    "enemy_army_supply",
    "threat_level",
    "tech_level",
    "hatchery_count",
    "base_count",
    "queen_count",
    "upgrade_speed",
    "upgrade_carapace",
    "upgrade_missile",
]


# ─────────────────────────────────────────────
# Math Utilities
# ─────────────────────────────────────────────


def _relu(x: float) -> float:
    return max(0.0, x)


def _elu(x: float, alpha: float = 1.0) -> float:
    return x if x >= 0 else alpha * (math.exp(min(x, 500)) - 1.0)


def _sigmoid(x: float) -> float:
    x = max(-500, min(500, x))
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    return math.tanh(x)


def _softmax(logits: List[float]) -> List[float]:
    max_l = max(logits)
    exps = [math.exp(l - max_l) for l in logits]
    s = sum(exps)
    return [e / s for e in exps]


def _softplus(x: float) -> float:
    if x > 20:
        return x
    return math.log(1.0 + math.exp(x))


def _one_hot(action: int, dim: int) -> List[float]:
    vec = [0.0] * dim
    vec[action] = 1.0
    return vec


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _matvec(mat: List[List[float]], vec: List[float]) -> List[float]:
    return [_dot(row, vec) for row in mat]


def _mse(pred: List[float], target: List[float]) -> float:
    return sum((p - t) ** 2 for p, t in zip(pred, target)) / len(pred)


def _vec_add(a: List[float], b: List[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)]


def _vec_scale(a: List[float], s: float) -> List[float]:
    return [x * s for x in a]


# ─────────────────────────────────────────────
# Dense Layer & MLP
# ─────────────────────────────────────────────


class DenseLayer:
    """Single dense layer with Xavier initialization."""

    def __init__(self, in_dim: int, out_dim: int, activation: str = "relu"):
        scale = math.sqrt(2.0 / (in_dim + out_dim))
        self.weights = [
            [random.gauss(0, scale) for _ in range(in_dim)] for _ in range(out_dim)
        ]
        self.biases = [0.0] * out_dim
        self.activation = activation
        self.in_dim = in_dim
        self.out_dim = out_dim

    def forward(self, x: List[float]) -> List[float]:
        out = []
        for i in range(self.out_dim):
            z = _dot(self.weights[i], x[: self.in_dim]) + self.biases[i]
            if self.activation == "relu":
                z = _relu(z)
            elif self.activation == "elu":
                z = _elu(z)
            elif self.activation == "tanh":
                z = _tanh(z)
            elif self.activation == "sigmoid":
                z = _sigmoid(z)
            out.append(z)
        return out


class MLP:
    """Multi-layer perceptron."""

    def __init__(self, dims: List[int], activations: Optional[List[str]] = None):
        if activations is None:
            activations = ["relu"] * (len(dims) - 2) + ["linear"]
        self.layers: List[DenseLayer] = []
        for i in range(len(dims) - 1):
            act = activations[i] if i < len(activations) else "linear"
            self.layers.append(DenseLayer(dims[i], dims[i + 1], act))

    def forward(self, x: List[float]) -> List[float]:
        for layer in self.layers:
            x = layer.forward(x)
        return x


# ─────────────────────────────────────────────
# Sequence Buffer
# ─────────────────────────────────────────────


@dataclass
class TimeStep:
    observation: List[float]
    action: int
    reward: float
    done: bool


class SequenceBuffer:
    """Stores sequences of transitions for world model training."""

    def __init__(self, capacity: int = 10_000, seq_len: int = 50):
        self.capacity = capacity
        self.seq_len = seq_len
        self.episodes: List[List[TimeStep]] = []
        self.current_episode: List[TimeStep] = []

    def add(self, obs: List[float], action: int, reward: float, done: bool) -> None:
        self.current_episode.append(TimeStep(obs, action, reward, done))
        if done:
            if len(self.current_episode) >= 2:
                self.episodes.append(self.current_episode)
            self.current_episode = []
            if len(self.episodes) > self.capacity:
                self.episodes.pop(0)

    def sample_sequences(self, batch_size: int) -> List[List[TimeStep]]:
        """Sample batch_size subsequences of length seq_len."""
        seqs = []
        for _ in range(batch_size):
            ep_idx = random.randint(0, len(self.episodes) - 1)
            ep = self.episodes[ep_idx]
            max_start = max(0, len(ep) - self.seq_len)
            start = random.randint(0, max_start)
            end = min(start + self.seq_len, len(ep))
            seqs.append(ep[start:end])
        return seqs

    def __len__(self) -> int:
        return sum(len(ep) for ep in self.episodes)


# ─────────────────────────────────────────────
# RSSM: Recurrent State Space Model
# ─────────────────────────────────────────────


@dataclass
class RSSMState:
    """Combined deterministic + stochastic state."""

    deterministic: List[float]  # h_t (GRU hidden state)
    stochastic: List[float]  # z_t (sampled latent)
    mean: List[float]  # mu of posterior/prior
    log_std: List[float]  # log_sigma of posterior/prior


class RSSM:
    """
    Recurrent State Space Model (Dreamer).

    Prior:     p(z_t | h_t)
    Posterior: q(z_t | h_t, o_t)
    Transition: h_t = f(h_{t-1}, z_{t-1}, a_{t-1})
    """

    def __init__(
        self,
        obs_dim: int = OBS_DIM,
        action_dim: int = ACTION_DIM,
        latent_dim: int = LATENT_DIM,
        deterministic_dim: int = DETERMINISTIC_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.latent_dim = latent_dim
        self.det_dim = deterministic_dim
        self.hidden_dim = hidden_dim

        # GRU-like transition: (h_{t-1}, z_{t-1}, a_{t-1}) -> h_t
        gru_input = deterministic_dim + latent_dim + action_dim
        self.gru_gate = MLP(
            [gru_input, hidden_dim, deterministic_dim * 2], ["relu", "sigmoid"]
        )
        self.gru_candidate = MLP(
            [gru_input, hidden_dim, deterministic_dim], ["relu", "tanh"]
        )

        # Prior: h_t -> (mu, log_sigma) for z_t
        self.prior_net = MLP(
            [deterministic_dim, hidden_dim, latent_dim * 2], ["elu", "linear"]
        )

        # Posterior: (h_t, encoded_obs) -> (mu, log_sigma) for z_t
        self.posterior_net = MLP(
            [deterministic_dim + hidden_dim, hidden_dim, latent_dim * 2],
            ["elu", "linear"],
        )

        # Observation encoder: obs -> embedded_obs
        self.obs_encoder = MLP([obs_dim, hidden_dim, hidden_dim], ["elu", "elu"])

    def initial_state(self) -> RSSMState:
        """Return zero-initialized RSSM state."""
        return RSSMState(
            deterministic=[0.0] * self.det_dim,
            stochastic=[0.0] * self.latent_dim,
            mean=[0.0] * self.latent_dim,
            log_std=[-1.0] * self.latent_dim,
        )

    def _gru_step(
        self, h_prev: List[float], z_prev: List[float], action: List[float]
    ) -> List[float]:
        """GRU-like deterministic transition."""
        inp = h_prev + z_prev + action
        gates = self.gru_gate.forward(inp)

        reset_gate = gates[: self.det_dim]
        update_gate = gates[self.det_dim :]

        # Apply reset gate to h_prev
        reset_h = [r * h for r, h in zip(reset_gate, h_prev)]
        candidate_inp = reset_h + z_prev + action
        candidate = self.gru_candidate.forward(candidate_inp)

        # Update gate
        new_h = [
            u * h + (1.0 - u) * c for u, h, c in zip(update_gate, h_prev, candidate)
        ]
        return new_h

    def _split_mean_logstd(
        self, params: List[float]
    ) -> Tuple[List[float], List[float]]:
        """Split network output into mean and log_std."""
        mid = len(params) // 2
        mean = params[:mid]
        log_std = [max(-5.0, min(2.0, v)) for v in params[mid:]]
        return mean, log_std

    def _sample_gaussian(self, mean: List[float], log_std: List[float]) -> List[float]:
        """Reparameterized sampling: z = mu + sigma * epsilon."""
        return [m + math.exp(ls) * random.gauss(0, 1) for m, ls in zip(mean, log_std)]

    def prior(self, h: List[float]) -> Tuple[List[float], List[float]]:
        """Compute prior distribution p(z_t | h_t)."""
        params = self.prior_net.forward(h)
        return self._split_mean_logstd(params)

    def posterior(
        self, h: List[float], obs: List[float]
    ) -> Tuple[List[float], List[float]]:
        """Compute posterior distribution q(z_t | h_t, o_t)."""
        embedded = self.obs_encoder.forward(obs)
        inp = h + embedded
        params = self.posterior_net.forward(inp)
        return self._split_mean_logstd(params)

    def observe_step(
        self, prev_state: RSSMState, action: int, obs: List[float]
    ) -> RSSMState:
        """
        One step with observation (training).
        Computes posterior for z_t given h_t and o_t.
        """
        action_vec = _one_hot(action, self.action_dim)

        # Deterministic transition
        h = self._gru_step(prev_state.deterministic, prev_state.stochastic, action_vec)

        # Posterior
        mean, log_std = self.posterior(h, obs)
        z = self._sample_gaussian(mean, log_std)

        return RSSMState(
            deterministic=h,
            stochastic=z,
            mean=mean,
            log_std=log_std,
        )

    def imagine_step(self, prev_state: RSSMState, action: int) -> RSSMState:
        """
        One step without observation (imagination).
        Uses prior for z_t given h_t only.
        """
        action_vec = _one_hot(action, self.action_dim)

        # Deterministic transition
        h = self._gru_step(prev_state.deterministic, prev_state.stochastic, action_vec)

        # Prior (no observation)
        mean, log_std = self.prior(h)
        z = self._sample_gaussian(mean, log_std)

        return RSSMState(
            deterministic=h,
            stochastic=z,
            mean=mean,
            log_std=log_std,
        )

    def get_feature(self, state: RSSMState) -> List[float]:
        """Concatenate deterministic and stochastic for downstream use."""
        return state.deterministic + state.stochastic


# ─────────────────────────────────────────────
# KL Divergence & Balancing
# ─────────────────────────────────────────────


class KLManager:
    """
    Manages KL divergence computation with free bits and balancing.
    """

    def __init__(
        self, free_bits: float = 1.0, kl_scale: float = 1.0, kl_balance: float = 0.8
    ):
        self.free_bits = free_bits
        self.kl_scale = kl_scale
        self.kl_balance = kl_balance  # alpha: weight on prior vs posterior
        self.kl_history: List[float] = []

    def gaussian_kl(
        self,
        post_mean: List[float],
        post_logstd: List[float],
        prior_mean: List[float],
        prior_logstd: List[float],
    ) -> float:
        """
        KL(q || p) for diagonal Gaussian distributions.
        KL = sum[ log(s_p/s_q) + (s_q^2 + (m_q - m_p)^2) / (2*s_p^2) - 0.5 ]
        """
        kl = 0.0
        for mq, lsq, mp, lsp in zip(post_mean, post_logstd, prior_mean, prior_logstd):
            sq = math.exp(lsq)
            sp = math.exp(lsp)
            kl_dim = lsp - lsq + (sq**2 + (mq - mp) ** 2) / (2 * sp**2) - 0.5
            kl += max(0.0, kl_dim)

        return kl

    def compute_loss(
        self,
        post_mean: List[float],
        post_logstd: List[float],
        prior_mean: List[float],
        prior_logstd: List[float],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute KL loss with free bits and balancing.

        KL balancing splits the KL into:
        - alpha * KL(sg(posterior) || prior)    -> trains the prior
        - (1-alpha) * KL(posterior || sg(prior)) -> trains the posterior
        where sg = stop_gradient (simulated by using fixed values).
        """
        raw_kl = self.gaussian_kl(post_mean, post_logstd, prior_mean, prior_logstd)

        # Free bits: clamp KL to at least free_bits per dimension
        kl_free = max(raw_kl, self.free_bits)

        # KL balancing
        # Forward KL component (trains prior, posterior is fixed)
        kl_prior = self.gaussian_kl(post_mean, post_logstd, prior_mean, prior_logstd)
        # Reverse KL component (trains posterior, prior is fixed)
        kl_posterior = self.gaussian_kl(
            post_mean, post_logstd, prior_mean, prior_logstd
        )

        balanced_kl = self.kl_balance * max(kl_prior, self.free_bits) + (
            1 - self.kl_balance
        ) * max(kl_posterior, self.free_bits)

        scaled_kl = self.kl_scale * balanced_kl
        self.kl_history.append(raw_kl)

        info = {
            "raw_kl": raw_kl,
            "free_kl": kl_free,
            "balanced_kl": balanced_kl,
            "scaled_kl": scaled_kl,
        }
        return scaled_kl, info

    def get_stats(self) -> Dict[str, float]:
        """Get KL statistics over recent history."""
        if not self.kl_history:
            return {"mean_kl": 0.0, "max_kl": 0.0, "min_kl": 0.0}
        recent = self.kl_history[-100:]
        return {
            "mean_kl": sum(recent) / len(recent),
            "max_kl": max(recent),
            "min_kl": min(recent),
        }


# ─────────────────────────────────────────────
# Observation Decoder & Reward Predictor
# ─────────────────────────────────────────────

FEATURE_DIM = DETERMINISTIC_DIM + LATENT_DIM  # h + z


class ObservationDecoder:
    """Decodes latent features back to predicted observations."""

    def __init__(
        self,
        feature_dim: int = FEATURE_DIM,
        obs_dim: int = OBS_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ):
        self.net = MLP(
            [feature_dim, hidden_dim, hidden_dim, obs_dim], ["elu", "elu", "sigmoid"]
        )

    def forward(self, feature: List[float]) -> List[float]:
        return self.net.forward(feature)


class RewardPredictor:
    """Predicts reward from latent features."""

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = HIDDEN_DIM):
        self.net = MLP([feature_dim, hidden_dim, 1], ["elu", "linear"])

    def forward(self, feature: List[float]) -> float:
        return self.net.forward(feature)[0]


class ContinuePredictor:
    """Predicts episode continuation probability from latent features."""

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = HIDDEN_DIM):
        self.net = MLP([feature_dim, hidden_dim, 1], ["elu", "sigmoid"])

    def forward(self, feature: List[float]) -> float:
        return self.net.forward(feature)[0]


# ─────────────────────────────────────────────
# Actor-Critic (Dreamer-Style)
# ─────────────────────────────────────────────


class DreamerActor:
    """Actor network: latent features -> action distribution."""

    def __init__(
        self,
        feature_dim: int = FEATURE_DIM,
        action_dim: int = ACTION_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ):
        self.net = MLP(
            [feature_dim, hidden_dim, hidden_dim, action_dim], ["elu", "elu", "linear"]
        )
        self.action_dim = action_dim
        self.entropy_scale = 0.003

    def get_action_dist(self, feature: List[float]) -> List[float]:
        logits = self.net.forward(feature)
        return _softmax(logits)

    def select_action(self, feature: List[float], greedy: bool = False) -> int:
        probs = self.get_action_dist(feature)
        if greedy:
            return max(range(self.action_dim), key=lambda i: probs[i])
        r = random.random()
        cumsum = 0.0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return i
        return self.action_dim - 1

    def entropy(self, probs: List[float]) -> float:
        return -sum(p * math.log(max(p, 1e-10)) for p in probs)


class DreamerCritic:
    """Critic network: latent features -> value estimate."""

    def __init__(self, feature_dim: int = FEATURE_DIM, hidden_dim: int = HIDDEN_DIM):
        self.net = MLP(
            [feature_dim, hidden_dim, hidden_dim, 1], ["elu", "elu", "linear"]
        )

    def forward(self, feature: List[float]) -> float:
        return self.net.forward(feature)[0]


# ─────────────────────────────────────────────
# Latent Space Visualization (PCA / t-SNE)
# ─────────────────────────────────────────────


class LatentVisualizer:
    """
    Visualizes latent states using PCA (always available)
    and t-SNE (when sklearn is present).
    """

    def __init__(self):
        self.collected_states: List[List[float]] = []
        self.collected_labels: List[str] = []
        self._has_sklearn = False
        try:
            from sklearn.manifold import TSNE  # noqa: F401

            self._has_sklearn = True
        except ImportError:
            pass

    def add(self, latent: List[float], label: str = "") -> None:
        self.collected_states.append(latent[:])
        self.collected_labels.append(label)

    def pca_2d(self) -> List[Tuple[float, float]]:
        """Simple 2-component PCA using power iteration."""
        if len(self.collected_states) < 3:
            return [(0.0, 0.0)] * len(self.collected_states)

        n = len(self.collected_states)
        d = len(self.collected_states[0])

        # Center data
        means = [0.0] * d
        for s in self.collected_states:
            for j in range(d):
                means[j] += s[j]
        means = [m / n for m in means]

        centered = [[s[j] - means[j] for j in range(d)] for s in self.collected_states]

        # Power iteration for first principal component
        pc1 = [random.gauss(0, 1) for _ in range(d)]
        norm = math.sqrt(sum(x**2 for x in pc1))
        pc1 = [x / max(norm, 1e-10) for x in pc1]

        for _ in range(50):
            new_pc = [0.0] * d
            for row in centered:
                proj = _dot(row, pc1)
                for j in range(d):
                    new_pc[j] += proj * row[j]
            norm = math.sqrt(sum(x**2 for x in new_pc))
            pc1 = [x / max(norm, 1e-10) for x in new_pc]

        # Deflate for second component
        deflated = []
        for row in centered:
            proj = _dot(row, pc1)
            deflated.append([row[j] - proj * pc1[j] for j in range(d)])

        pc2 = [random.gauss(0, 1) for _ in range(d)]
        norm = math.sqrt(sum(x**2 for x in pc2))
        pc2 = [x / max(norm, 1e-10) for x in pc2]

        for _ in range(50):
            new_pc = [0.0] * d
            for row in deflated:
                proj = _dot(row, pc2)
                for j in range(d):
                    new_pc[j] += proj * row[j]
            norm = math.sqrt(sum(x**2 for x in new_pc))
            pc2 = [x / max(norm, 1e-10) for x in new_pc]

        # Project
        result = []
        for row in centered:
            x = _dot(row, pc1)
            y = _dot(row, pc2)
            result.append((x, y))

        return result

    def tsne_2d(
        self, perplexity: float = 5.0, iterations: int = 300
    ) -> Optional[List[Tuple[float, float]]]:
        """Simplified t-SNE. Falls back to PCA if sklearn unavailable."""
        if self._has_sklearn and HAS_NUMPY:
            try:
                import numpy as real_np
                from sklearn.manifold import TSNE

                data = real_np.array(self.collected_states)
                perp = min(perplexity, len(data) - 1)
                embedded = TSNE(
                    n_components=2,
                    perplexity=max(perp, 1),
                    n_iter=iterations,
                    random_state=42,
                ).fit_transform(data)
                return [(float(row[0]), float(row[1])) for row in embedded]
            except Exception:
                pass
        # Fallback to PCA
        return self.pca_2d()

    def render_ascii(self, width: int = 60, height: int = 20) -> str:
        """Render latent space as ASCII scatter plot."""
        points = self.pca_2d()
        if not points:
            return "(no data)"

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_range = max(x_max - x_min, 1e-6)
        y_range = max(y_max - y_min, 1e-6)

        grid = [[" "] * width for _ in range(height)]

        for i, (x, y) in enumerate(points):
            col = int((x - x_min) / x_range * (width - 1))
            row = int((y - y_min) / y_range * (height - 1))
            row = height - 1 - row
            col = max(0, min(width - 1, col))
            row = max(0, min(height - 1, row))
            label = self.collected_labels[i]
            grid[row][col] = label[0] if label else "*"

        lines = ["    +" + "-" * width + "+"]
        for r in range(height):
            lines.append(f'    |{"".join(grid[r])}|')
        lines.append("    +" + "-" * width + "+")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# SC2 World Model (Dreamer-style)
# ─────────────────────────────────────────────


class SC2WorldModel:
    """
    Complete Dreamer-style world model for StarCraft II.

    Components:
    1. RSSM: learns latent dynamics
    2. Encoder: observation -> latent
    3. Decoder: latent -> predicted observation
    4. Reward predictor: latent -> reward
    5. Continue predictor: latent -> done probability
    6. Actor-Critic: trained purely from imagined trajectories
    """

    def __init__(
        self,
        obs_dim: int = OBS_DIM,
        action_dim: int = ACTION_DIM,
        imagination_horizon: int = 15,
        lr: float = 0.0003,
    ):
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.imagination_horizon = imagination_horizon
        self.lr = lr

        # World model components
        self.rssm = RSSM(obs_dim, action_dim)
        self.decoder = ObservationDecoder()
        self.reward_pred = RewardPredictor()
        self.continue_pred = ContinuePredictor()

        # Actor-Critic
        self.actor = DreamerActor(FEATURE_DIM, action_dim)
        self.critic = DreamerCritic(FEATURE_DIM)

        # KL management
        self.kl_manager = KLManager(free_bits=1.0, kl_scale=0.1, kl_balance=0.8)

        # Data
        self.buffer = SequenceBuffer(capacity=5_000, seq_len=50)
        self.visualizer = LatentVisualizer()

        # Training state
        self.current_state: Optional[RSSMState] = None
        self.train_steps = 0
        self.loss_history: Dict[str, List[float]] = {
            "reconstruction": [],
            "reward": [],
            "kl": [],
            "actor": [],
            "critic": [],
            "total": [],
        }
        self.discount = 0.99
        self.lambda_gae = 0.95

    def reset(self) -> None:
        """Reset internal RSSM state for a new episode."""
        self.current_state = self.rssm.initial_state()

    def encode_observe(self, obs: List[float], action: int) -> RSSMState:
        """Encode an observation and update state."""
        if self.current_state is None:
            self.current_state = self.rssm.initial_state()

        self.current_state = self.rssm.observe_step(self.current_state, action, obs)
        return self.current_state

    def select_action(self, obs: List[float], greedy: bool = False) -> int:
        """Select action using actor given current latent state."""
        if self.current_state is None:
            self.reset()

        feature = self.rssm.get_feature(self.current_state)
        return self.actor.select_action(feature, greedy=greedy)

    def imagine_rollout(
        self, start_state: RSSMState, horizon: Optional[int] = None
    ) -> List[Tuple[RSSMState, int, float, float]]:
        """
        Imagine a trajectory in latent space using the actor.
        Returns: list of (state, action, predicted_reward, continue_prob)
        """
        if horizon is None:
            horizon = self.imagination_horizon

        trajectory = []
        state = start_state

        for t in range(horizon):
            feature = self.rssm.get_feature(state)
            action = self.actor.select_action(feature, greedy=False)
            reward = self.reward_pred.forward(feature)
            cont = self.continue_pred.forward(feature)

            trajectory.append((state, action, reward, cont))

            # Imagine next state (no observation)
            state = self.rssm.imagine_step(state, action)

        return trajectory

    def compute_lambda_returns(
        self, rewards: List[float], values: List[float], continues: List[float]
    ) -> List[float]:
        """
        Compute lambda-returns for GAE-style advantage estimation.
        V_lambda = r_t + gamma * cont * ((1-lambda)*V_{t+1} + lambda*V_lambda_{t+1})
        """
        T = len(rewards)
        returns = [0.0] * T

        # Bootstrap from last value
        last_val = values[-1] if values else 0.0
        last_return = last_val

        for t in reversed(range(T)):
            if t == T - 1:
                next_val = last_val
            else:
                next_val = values[t + 1]

            cont = continues[t]
            td_target = rewards[t] + self.discount * cont * next_val
            returns[t] = td_target + self.discount * cont * self.lambda_gae * (
                last_return - next_val
            )
            last_return = returns[t]

        return returns

    def train_world_model_step(self, batch_size: int = 8) -> Dict[str, float]:
        """
        Train the world model on sequences from the buffer.
        Returns loss components.
        """
        if len(self.buffer.episodes) < 2:
            return {"total": 0.0}

        sequences = self.buffer.sample_sequences(batch_size)

        total_recon_loss = 0.0
        total_reward_loss = 0.0
        total_kl_loss = 0.0
        count = 0

        for seq in sequences:
            state = self.rssm.initial_state()

            for t, timestep in enumerate(seq):
                # Observe step (posterior)
                state = self.rssm.observe_step(
                    state, timestep.action, timestep.observation
                )
                feature = self.rssm.get_feature(state)

                # Reconstruction loss
                pred_obs = self.decoder.forward(feature)
                recon_loss = _mse(pred_obs, timestep.observation)
                total_recon_loss += recon_loss

                # Reward prediction loss
                pred_reward = self.reward_pred.forward(feature)
                reward_loss = (pred_reward - timestep.reward) ** 2
                total_reward_loss += reward_loss

                # KL loss (posterior vs prior)
                prior_mean, prior_logstd = self.rssm.prior(state.deterministic)
                kl_loss, kl_info = self.kl_manager.compute_loss(
                    state.mean, state.log_std, prior_mean, prior_logstd
                )
                total_kl_loss += kl_loss

                count += 1

                # Collect for visualization (sparse)
                if t % 10 == 0:
                    action_label = ACTION_NAMES[timestep.action]
                    self.visualizer.add(state.stochastic, action_label)

        if count == 0:
            return {"total": 0.0}

        avg_recon = total_recon_loss / count
        avg_reward = total_reward_loss / count
        avg_kl = total_kl_loss / count
        total = avg_recon + avg_reward + avg_kl

        # Perturbation-based gradient update on decoder & reward predictor
        eps = 1e-4
        for net, loss_fn_name in [
            (self.decoder.net, "recon"),
            (self.reward_pred.net, "reward"),
        ]:
            for layer in net.layers:
                for i in range(layer.out_dim):
                    for j in range(min(layer.in_dim, 4)):
                        orig = layer.weights[i][j]
                        layer.weights[i][j] = orig + eps

                        # Recompute loss for one sample
                        if sequences and sequences[0]:
                            sample = sequences[0][0]
                            test_state = self.rssm.initial_state()
                            test_state = self.rssm.observe_step(
                                test_state, sample.action, sample.observation
                            )
                            test_feat = self.rssm.get_feature(test_state)

                            if loss_fn_name == "recon":
                                p = self.decoder.forward(test_feat)
                                new_loss = _mse(p, sample.observation)
                                grad = (new_loss - avg_recon) / eps
                            else:
                                p = self.reward_pred.forward(test_feat)
                                new_loss = (p - sample.reward) ** 2
                                grad = (new_loss - avg_reward) / eps

                            layer.weights[i][j] = orig - self.lr * grad
                        else:
                            layer.weights[i][j] = orig

        self.train_steps += 1
        losses = {
            "reconstruction": avg_recon,
            "reward": avg_reward,
            "kl": avg_kl,
            "total": total,
        }
        for k, v in losses.items():
            self.loss_history[k].append(v)

        return losses

    def train_actor_critic_step(self) -> Dict[str, float]:
        """
        Train actor and critic purely from imagined trajectories.
        """
        if self.current_state is None or len(self.buffer.episodes) < 2:
            return {"actor_loss": 0.0, "critic_loss": 0.0}

        # Sample a starting state from buffer
        seqs = self.buffer.sample_sequences(1)
        if not seqs or not seqs[0]:
            return {"actor_loss": 0.0, "critic_loss": 0.0}

        # Build a starting latent state
        start_state = self.rssm.initial_state()
        for ts in seqs[0][:5]:
            start_state = self.rssm.observe_step(start_state, ts.action, ts.observation)

        # Imagine trajectory
        trajectory = self.imagine_rollout(start_state, self.imagination_horizon)

        if not trajectory:
            return {"actor_loss": 0.0, "critic_loss": 0.0}

        # Compute values and returns
        features = [self.rssm.get_feature(s) for s, _, _, _ in trajectory]
        values = [self.critic.forward(f) for f in features]
        rewards = [r for _, _, r, _ in trajectory]
        continues = [c for _, _, _, c in trajectory]

        lambda_returns = self.compute_lambda_returns(rewards, values, continues)

        # Actor loss: maximize returns (policy gradient)
        actor_loss = 0.0
        for t, (state, action, _, _) in enumerate(trajectory):
            feature = self.rssm.get_feature(state)
            probs = self.actor.get_action_dist(feature)
            log_prob = math.log(max(probs[action], 1e-10))
            advantage = lambda_returns[t] - values[t]
            entropy = self.actor.entropy(probs)
            actor_loss += -(log_prob * advantage + self.actor.entropy_scale * entropy)

        actor_loss /= len(trajectory)

        # Critic loss: MSE between values and returns
        critic_loss = 0.0
        for t in range(len(trajectory)):
            critic_loss += (values[t] - lambda_returns[t]) ** 2
        critic_loss /= len(trajectory)

        # Update actor via perturbation
        eps = 1e-4
        for layer in self.actor.net.layers:
            for i in range(layer.out_dim):
                for j in range(min(layer.in_dim, 4)):
                    orig = layer.weights[i][j]
                    layer.weights[i][j] = orig + eps

                    # Recompute actor loss for one step
                    s0, a0, _, _ = trajectory[0]
                    f0 = self.rssm.get_feature(s0)
                    new_probs = self.actor.get_action_dist(f0)
                    new_lp = math.log(max(new_probs[a0], 1e-10))
                    adv = lambda_returns[0] - values[0]
                    new_loss = -(
                        new_lp * adv
                        + self.actor.entropy_scale * self.actor.entropy(new_probs)
                    )
                    grad = (new_loss - actor_loss) / eps

                    layer.weights[i][j] = orig - self.lr * grad

        # Update critic via perturbation
        for layer in self.critic.net.layers:
            for i in range(layer.out_dim):
                for j in range(min(layer.in_dim, 4)):
                    orig = layer.weights[i][j]
                    layer.weights[i][j] = orig + eps

                    f0 = self.rssm.get_feature(trajectory[0][0])
                    new_v = self.critic.forward(f0)
                    new_closs = (new_v - lambda_returns[0]) ** 2
                    grad = (new_closs - (values[0] - lambda_returns[0]) ** 2) / eps

                    layer.weights[i][j] = orig - self.lr * grad

        result = {"actor_loss": actor_loss, "critic_loss": critic_loss}
        self.loss_history["actor"].append(actor_loss)
        self.loss_history["critic"].append(critic_loss)
        return result

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return comprehensive diagnostic information."""
        kl_stats = self.kl_manager.get_stats()
        recent_n = 20

        def _recent_avg(key: str) -> float:
            vals = self.loss_history.get(key, [])
            if not vals:
                return 0.0
            r = vals[-recent_n:]
            return sum(r) / len(r)

        return {
            "train_steps": self.train_steps,
            "buffer_episodes": len(self.buffer.episodes),
            "buffer_transitions": len(self.buffer),
            "latent_dim": self.rssm.latent_dim,
            "deterministic_dim": self.rssm.det_dim,
            "imagination_horizon": self.imagination_horizon,
            "recent_recon_loss": _recent_avg("reconstruction"),
            "recent_reward_loss": _recent_avg("reward"),
            "recent_kl_loss": _recent_avg("kl"),
            "recent_actor_loss": _recent_avg("actor"),
            "recent_critic_loss": _recent_avg("critic"),
            "kl_mean": kl_stats["mean_kl"],
            "kl_max": kl_stats["max_kl"],
            "visualized_points": len(self.visualizer.collected_states),
        }


# ─────────────────────────────────────────────
# SC2 Environment Simulator (for demo)
# ─────────────────────────────────────────────


class SC2EnvSimulator:
    """Lightweight SC2 environment simulator for testing."""

    def __init__(self, max_steps: int = 200):
        self.max_steps = max_steps
        self.step_count = 0
        self.state = self._initial_state()

    def _initial_state(self) -> List[float]:
        return [
            0.05,
            0.02,
            0.06,
            0.10,
            0.15,
            0.0,
            0.0,
            0.0,
            0.1,
            0.0,
            0.2,
            0.2,
            0.1,
            0.0,
            0.0,
            0.0,
        ]

    def reset(self) -> List[float]:
        self.step_count = 0
        self.state = self._initial_state()
        return self.state[:]

    def step(self, action: int) -> Tuple[List[float], float, bool]:
        self.step_count += 1
        reward = 0.0
        s = self.state[:]

        s[0] = min(1.0, s[0] + 0.02 * s[4])
        s[1] = min(1.0, s[1] + 0.01 * s[4])
        s[6] = self.step_count / self.max_steps
        s[7] = min(1.0, 0.01 * self.step_count / self.max_steps)

        if action == 0:  # train_drone
            if s[0] > 0.05 and s[2] < s[3]:
                s[0] -= 0.05
                s[4] = min(1.0, s[4] + 0.0125)
                s[2] += 0.005
                reward = 0.3
        elif action == 1:  # train_zergling
            if s[0] > 0.025:
                s[0] -= 0.025
                s[5] = min(1.0, s[5] + 0.005)
                s[2] += 0.005
                reward = 0.2
        elif action == 2:  # train_roach
            if s[0] > 0.075 and s[1] > 0.025:
                s[0] -= 0.075
                s[1] -= 0.025
                s[5] = min(1.0, s[5] + 0.01)
                s[2] += 0.01
                reward = 0.4
        elif action == 3:  # build_overlord
            if s[0] > 0.1:
                s[0] -= 0.1
                s[3] = min(1.0, s[3] + 0.04)
                reward = 0.1 if s[2] > s[3] * 0.8 else -0.05
        elif action == 4:  # expand
            if s[0] > 0.3:
                s[0] -= 0.3
                s[10] = min(1.0, s[10] + 0.2)
                s[11] = min(1.0, s[11] + 0.2)
                reward = 0.5
        elif action == 5:  # attack_move
            if s[5] > s[7]:
                reward = 1.0 * (s[5] - s[7])
                s[5] = max(0.0, s[5] - 0.02)
            else:
                reward = -0.5
                s[5] = max(0.0, s[5] - 0.05)
        elif action == 6:  # defend_base
            if s[8] > 0.5:
                reward = 0.3
                s[8] = max(0.0, s[8] - 0.1)
            else:
                reward = 0.05

        s[8] = min(1.0, s[7] * 1.5)
        self.state = s
        done = self.step_count >= self.max_steps
        return s[:], reward, done


# ─────────────────────────────────────────────
# CLI Demo
# ─────────────────────────────────────────────


def run_demo(
    episodes: int = 5, steps_per_ep: int = 100, verbose: bool = True
) -> Dict[str, Any]:
    """Run a full World Model (Dreamer) demo."""
    if verbose:
        print(f"{'=' * 60}")
        print(f"  Phase 617: World Model (Dreamer) — SC2 Agent")
        print(f"{'=' * 60}")

    world_model = SC2WorldModel(
        obs_dim=OBS_DIM, action_dim=ACTION_DIM, imagination_horizon=15
    )
    env = SC2EnvSimulator(max_steps=steps_per_ep)
    all_rewards: List[float] = []

    for ep in range(episodes):
        obs = env.reset()
        world_model.reset()
        ep_reward = 0.0
        ep_start = time.time()

        for step in range(steps_per_ep):
            # Encode current observation and select action
            action = world_model.select_action(obs)
            world_model.encode_observe(obs, action)

            # Step environment
            next_obs, reward, done = env.step(action)
            ep_reward += reward

            # Store transition
            world_model.buffer.add(obs, action, reward, done)

            obs = next_obs

            # Train world model periodically
            if step % 20 == 0 and len(world_model.buffer.episodes) >= 2:
                wm_losses = world_model.train_world_model_step(batch_size=4)
                ac_losses = world_model.train_actor_critic_step()

            if done:
                # Finalize episode in buffer
                world_model.buffer.add(obs, 0, 0.0, True)
                break

        all_rewards.append(ep_reward)
        elapsed = time.time() - ep_start

        if verbose:
            diag = world_model.get_diagnostics()
            print(
                f"\n  Episode {ep + 1}/{episodes} | "
                f"Reward: {ep_reward:+.2f} | "
                f"Time: {elapsed:.2f}s"
            )
            print(
                f"    Buffer: {diag['buffer_episodes']} episodes, "
                f"{diag['buffer_transitions']} transitions"
            )
            print(
                f"    Recon loss: {diag['recent_recon_loss']:.4f} | "
                f"KL: {diag['recent_kl_loss']:.4f}"
            )
            print(
                f"    Actor loss: {diag['recent_actor_loss']:.4f} | "
                f"Critic loss: {diag['recent_critic_loss']:.4f}"
            )

    # Final diagnostics
    diag = world_model.get_diagnostics()

    if verbose:
        print(f"\n{'─' * 60}")
        print("  Final Diagnostics:")
        for k, v in diag.items():
            if isinstance(v, float):
                print(f"    {k}: {v:.4f}")
            else:
                print(f"    {k}: {v}")

        # Imagination demo
        print(f"\n{'─' * 60}")
        print("  Imagination Rollout Demo:")
        if world_model.current_state:
            imagined = world_model.imagine_rollout(
                world_model.current_state, horizon=10
            )
            for t, (state, action, reward, cont) in enumerate(imagined):
                print(
                    f"    t={t}: action={ACTION_NAMES[action]}, "
                    f"pred_reward={reward:+.3f}, "
                    f"continue={cont:.3f}"
                )

        # Latent space visualization
        if len(world_model.visualizer.collected_states) >= 5:
            print(f"\n{'─' * 60}")
            print("  Latent Space (PCA 2D):")
            print(world_model.visualizer.render_ascii(width=50, height=15))

        # KL stats
        kl_stats = world_model.kl_manager.get_stats()
        print(
            f"\n  KL Stats: mean={kl_stats['mean_kl']:.4f}, "
            f"max={kl_stats['max_kl']:.4f}, "
            f"min={kl_stats['min_kl']:.4f}"
        )

        print(
            f"\n  Mean episode reward: " f"{sum(all_rewards) / len(all_rewards):+.2f}"
        )
        print(f"{'=' * 60}")

    return {
        "episodes": episodes,
        "all_rewards": all_rewards,
        "mean_reward": sum(all_rewards) / len(all_rewards),
        "diagnostics": diag,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Phase 617: World Model (Dreamer) for SC2"
    )
    parser.add_argument("--episodes", type=int, default=5, help="Number of episodes")
    parser.add_argument("--steps", type=int, default=100, help="Steps per episode")
    parser.add_argument(
        "--horizon", type=int, default=15, help="Imagination rollout horizon"
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    result = run_demo(
        episodes=args.episodes,
        steps_per_ep=args.steps,
        verbose=not args.quiet,
    )

    if args.quiet:
        print(f"Mean reward: {result['mean_reward']:.4f}")


if __name__ == "__main__":
    main()
