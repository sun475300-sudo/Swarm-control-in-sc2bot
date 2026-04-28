"""
Phase 616: Model-Based RL with Learned Dynamics for SC2
========================================================

Model-based reinforcement learning agent that learns environment dynamics
(state transitions and rewards) and uses them for planning via Model
Predictive Control (MPC).  An ensemble of dynamics models provides
uncertainty estimation, enabling safe exploration and adaptive rollout
horizons.

SC2-specific capabilities:
  - Predict resource changes (minerals, gas, supply)
  - Predict army combat outcomes
  - Track tech-tree progression
  - Ensemble disagreement as exploration bonus

Key classes:
  - DynamicsModel        -- single learned transition/reward predictor
  - PlanningBuffer       -- experience buffer for model training & planning
  - ModelPredictiveControl -- CEM-based MPC planner over learned model
  - ModelBasedAgent      -- top-level agent orchestrating learning & acting

Python 3.10 compatible.  NumPy optional (pure-Python fallback included).
"""

from __future__ import annotations

import argparse
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional NumPy
# ---------------------------------------------------------------------------
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_DIM = 16
ACTION_DIM = 7
ENSEMBLE_SIZE = 5
ACTION_NAMES = [
    "train_drone",
    "train_zergling",
    "train_roach",
    "build_overlord",
    "expand",
    "attack_move",
    "defend_base",
]


# ===================================================================
# Pure-Python math helpers
# ===================================================================


def _relu(x: float) -> float:
    return max(0.0, x)


def _sigmoid(x: float) -> float:
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    return math.tanh(x)


def _softmax(logits: List[float]) -> List[float]:
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    s = sum(exps)
    return [e / s for e in exps]


def _one_hot(action: int, dim: int) -> List[float]:
    vec = [0.0] * dim
    vec[action] = 1.0
    return vec


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mse(pred: List[float], target: List[float]) -> float:
    return sum((p - t) ** 2 for p, t in zip(pred, target)) / len(pred)


# ===================================================================
# Dense layer
# ===================================================================


class DenseLayer:
    """Single fully-connected layer with optional activation."""

    def __init__(self, in_dim: int, out_dim: int, activation: str = "relu"):
        self.in_dim = in_dim
        self.out_dim = out_dim
        self.activation = activation
        scale = math.sqrt(2.0 / in_dim)
        self.weights: List[List[float]] = [
            [random.gauss(0, scale) for _ in range(in_dim)] for _ in range(out_dim)
        ]
        self.biases: List[float] = [0.0] * out_dim

    def forward(self, x: List[float]) -> List[float]:
        out = [_dot(self.weights[i], x) + self.biases[i] for i in range(self.out_dim)]
        if self.activation == "relu":
            out = [_relu(v) for v in out]
        elif self.activation == "tanh":
            out = [_tanh(v) for v in out]
        elif self.activation == "sigmoid":
            out = [_sigmoid(v) for v in out]
        return out


class MLP:
    """Multi-layer perceptron built from DenseLayer."""

    def __init__(self, dims: List[int], activations: List[str]):
        assert len(dims) - 1 == len(activations)
        self.layers = [
            DenseLayer(dims[i], dims[i + 1], activations[i])
            for i in range(len(activations))
        ]

    def forward(self, x: List[float]) -> List[float]:
        for layer in self.layers:
            x = layer.forward(x)
        return x


# ===================================================================
# PlanningBuffer
# ===================================================================


@dataclass
class Transition:
    """A single (s, a, r, s', done) transition."""

    state: List[float]
    action: int
    reward: float
    next_state: List[float]
    done: bool


class PlanningBuffer:
    """
    Experience buffer for model-based planning.

    Stores real environment transitions for:
      - Training the dynamics model ensemble
      - Providing start states for imagined rollouts
      - Mixing real and imagined data for policy training
    """

    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self.buffer: List[Transition] = []
        self.position: int = 0
        self.total_added: int = 0

    def add(
        self,
        state: List[float],
        action: int,
        reward: float,
        next_state: List[float],
        done: bool,
    ) -> None:
        t = Transition(state[:], action, reward, next_state[:], done)
        if len(self.buffer) < self.capacity:
            self.buffer.append(t)
        else:
            self.buffer[self.position] = t
        self.position = (self.position + 1) % self.capacity
        self.total_added += 1

    def sample(self, batch_size: int) -> List[Transition]:
        return random.choices(self.buffer, k=min(batch_size, len(self.buffer)))

    def sample_states(self, n: int) -> List[List[float]]:
        """Sample n starting states for imagined rollouts."""
        transitions = self.sample(n)
        return [t.state[:] for t in transitions]

    def __len__(self) -> int:
        return len(self.buffer)

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "total_added": self.total_added,
            "utilisation": len(self.buffer) / self.capacity,
        }


# ===================================================================
# DynamicsModel
# ===================================================================


class DynamicsModel:
    """
    Learned dynamics model: predicts next state and reward given
    current state and action.

    Architecture:
      input  = concat(state, one_hot(action))
      hidden = MLP(input)
      delta_state = linear(hidden)   (residual prediction)
      reward      = linear(hidden)

    SC2-specific prediction targets:
      - Resource deltas (minerals, gas, supply)
      - Army strength changes
      - Tech-level progression
    """

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        hidden_dim: int = 64,
        lr: float = 0.001,
        model_id: int = 0,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.lr = lr
        self.model_id = model_id

        input_dim = state_dim + action_dim
        # State-delta predictor
        self.state_net = MLP(
            [input_dim, hidden_dim, hidden_dim, state_dim],
            ["relu", "relu", "linear"],
        )
        # Reward predictor
        self.reward_net = MLP(
            [input_dim, hidden_dim, 1],
            ["relu", "linear"],
        )
        self.train_steps: int = 0
        self.total_loss: float = 0.0

    def _encode_input(self, state: List[float], action: int) -> List[float]:
        return state + _one_hot(action, self.action_dim)

    def predict(self, state: List[float], action: int) -> Tuple[List[float], float]:
        """Return (predicted_next_state, predicted_reward)."""
        inp = self._encode_input(state, action)
        delta = self.state_net.forward(inp)
        # Residual: next_state = state + delta
        next_state = [s + d for s, d in zip(state, delta)]
        # Clamp to [0, 1] for normalised SC2 features
        next_state = [max(0.0, min(1.0, v)) for v in next_state]
        reward = self.reward_net.forward(inp)[0]
        return next_state, reward

    def train_on_batch(self, batch: List[Transition]) -> float:
        """One gradient step via finite-difference perturbation."""
        eps = 1e-4
        total_loss = 0.0

        for t in batch:
            pred_ns, pred_r = self.predict(t.state, t.action)
            state_loss = _mse(pred_ns, t.next_state)
            reward_loss = (pred_r - t.reward) ** 2
            loss = state_loss + reward_loss
            total_loss += loss

            # Perturbation-based update on state_net
            for layer in self.state_net.layers:
                for i in range(layer.out_dim):
                    for j in range(min(layer.in_dim, 6)):  # sparse update
                        orig = layer.weights[i][j]
                        layer.weights[i][j] = orig + eps
                        p_ns, _ = self.predict(t.state, t.action)
                        new_loss = _mse(p_ns, t.next_state) + reward_loss
                        grad = (new_loss - loss) / eps
                        layer.weights[i][j] = orig - self.lr * grad

            # Perturbation-based update on reward_net
            for layer in self.reward_net.layers:
                for i in range(layer.out_dim):
                    for j in range(min(layer.in_dim, 6)):
                        orig = layer.weights[i][j]
                        layer.weights[i][j] = orig + eps
                        _, p_r = self.predict(t.state, t.action)
                        new_rl = (p_r - t.reward) ** 2
                        grad = (new_rl - reward_loss) / eps
                        layer.weights[i][j] = orig - self.lr * grad

        avg_loss = total_loss / max(len(batch), 1)
        self.train_steps += 1
        self.total_loss += avg_loss
        return avg_loss


class DynamicsEnsemble:
    """
    Ensemble of DynamicsModel instances for uncertainty estimation.

    Disagreement among ensemble members indicates epistemic uncertainty,
    which drives exploration and gates model-based rollout length.
    """

    def __init__(
        self,
        n_models: int = ENSEMBLE_SIZE,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
    ):
        self.models = [
            DynamicsModel(state_dim, action_dim, model_id=i) for i in range(n_models)
        ]

    def predict(
        self, state: List[float], action: int
    ) -> Tuple[List[float], float, float]:
        """
        Ensemble prediction.

        Returns:
            (mean_next_state, mean_reward, uncertainty)
        where uncertainty = mean pairwise disagreement across models.
        """
        predictions = [m.predict(state, action) for m in self.models]
        n = len(predictions)
        dim = len(predictions[0][0])

        # Mean next state
        mean_ns = [sum(predictions[k][0][d] for k in range(n)) / n for d in range(dim)]
        # Mean reward
        mean_r = sum(p[1] for p in predictions) / n

        # Uncertainty: average std across state dimensions
        uncertainty = 0.0
        for d in range(dim):
            vals = [predictions[k][0][d] for k in range(n)]
            mu = sum(vals) / n
            var = sum((v - mu) ** 2 for v in vals) / n
            uncertainty += math.sqrt(var)
        uncertainty /= dim

        return mean_ns, mean_r, uncertainty

    def train_step(self, buffer: PlanningBuffer, batch_size: int = 32) -> List[float]:
        """Train each model on an independent sample from the buffer."""
        losses = []
        for model in self.models:
            batch = buffer.sample(batch_size)
            loss = model.train_on_batch(batch)
            losses.append(loss)
        return losses


# ===================================================================
# ModelPredictiveControl
# ===================================================================


class ModelPredictiveControl:
    """
    CEM-based Model Predictive Control using the learned dynamics
    ensemble.

    At each step:
      1. Sample candidate action sequences from a distribution.
      2. Rollout each sequence in the learned model.
      3. Rank by cumulative reward (penalised by uncertainty).
      4. Refit distribution to the elite set.
      5. Execute only the first action; re-plan next step.
    """

    def __init__(
        self,
        ensemble: DynamicsEnsemble,
        horizon: int = 5,
        population: int = 64,
        elite_frac: float = 0.2,
        cem_iterations: int = 5,
        discount: float = 0.99,
        uncertainty_penalty: float = 0.5,
    ):
        self.ensemble = ensemble
        self.horizon = horizon
        self.population = population
        self.num_elite = max(1, int(population * elite_frac))
        self.cem_iterations = cem_iterations
        self.discount = discount
        self.uncertainty_penalty = uncertainty_penalty
        self.last_plan: List[int] = []

    def _evaluate_sequence(self, state: List[float], actions: List[int]) -> float:
        """Rollout action sequence in the learned model."""
        total_reward = 0.0
        gamma = 1.0
        s = state[:]
        for a in actions:
            ns, r, unc = self.ensemble.predict(s, a)
            total_reward += gamma * (r - self.uncertainty_penalty * unc)
            s = ns
            gamma *= self.discount
        return total_reward

    def plan(self, state: List[float]) -> List[int]:
        """Run CEM optimisation and return the best action sequence."""
        action_dim = ACTION_DIM
        # Initialise uniform action distribution per timestep
        probs = [[1.0 / action_dim] * action_dim for _ in range(self.horizon)]

        best_seq: List[int] = []
        best_val = float("-inf")

        for _ in range(self.cem_iterations):
            candidates: List[Tuple[List[int], float]] = []

            for _ in range(self.population):
                seq: List[int] = []
                for t in range(self.horizon):
                    r = random.random()
                    cumsum = 0.0
                    chosen = 0
                    for idx, p in enumerate(probs[t]):
                        cumsum += p
                        if r <= cumsum:
                            chosen = idx
                            break
                    seq.append(chosen)

                val = self._evaluate_sequence(state, seq)
                candidates.append((seq, val))

            candidates.sort(key=lambda x: x[1], reverse=True)
            elites = candidates[: self.num_elite]

            if elites[0][1] > best_val:
                best_val = elites[0][1]
                best_seq = elites[0][0][:]

            # Update distribution from elites
            for t in range(self.horizon):
                counts = [0.0] * action_dim
                for seq, _ in elites:
                    counts[seq[t]] += 1.0
                total = sum(counts)
                probs[t] = [0.9 * (c / total) + 0.1 / action_dim for c in counts]

        self.last_plan = best_seq
        return best_seq

    def select_action(self, state: List[float]) -> int:
        """Plan and return the first action (re-plan each step)."""
        seq = self.plan(state)
        return seq[0] if seq else random.randrange(ACTION_DIM)


# ===================================================================
# SC2-specific prediction helpers
# ===================================================================


class SC2ResourcePredictor:
    """Wrapper for resource/army/tech predictions using the ensemble."""

    MINERALS_IDX = 0
    GAS_IDX = 1
    SUPPLY_IDX = 2
    ARMY_IDX = 5
    TECH_IDX = 9

    def __init__(self, ensemble: DynamicsEnsemble):
        self.ensemble = ensemble

    def predict_resource_change(
        self, state: List[float], action: int
    ) -> Dict[str, float]:
        ns, _, _ = self.ensemble.predict(state, action)
        return {
            "minerals_delta": ns[self.MINERALS_IDX] - state[self.MINERALS_IDX],
            "gas_delta": ns[self.GAS_IDX] - state[self.GAS_IDX],
            "supply_delta": ns[self.SUPPLY_IDX] - state[self.SUPPLY_IDX],
        }

    def predict_army_outcome(self, state: List[float], action: int) -> Dict[str, float]:
        ns, reward, unc = self.ensemble.predict(state, action)
        return {
            "army_delta": ns[self.ARMY_IDX] - state[self.ARMY_IDX],
            "predicted_reward": reward,
            "uncertainty": unc,
        }

    def predict_tech_progression(self, state: List[float], action: int) -> float:
        ns, _, _ = self.ensemble.predict(state, action)
        return ns[self.TECH_IDX] - state[self.TECH_IDX]


# ===================================================================
# Adaptive Trust Region
# ===================================================================


@dataclass
class ModelAccuracy:
    """Rolling accuracy tracker for model predictions."""

    state_errors: List[float] = field(default_factory=list)
    reward_errors: List[float] = field(default_factory=list)
    uncertainties: List[float] = field(default_factory=list)
    window: int = 200

    def record(
        self,
        pred_state: List[float],
        true_state: List[float],
        pred_reward: float,
        true_reward: float,
        uncertainty: float,
    ) -> None:
        self.state_errors.append(_mse(pred_state, true_state))
        self.reward_errors.append(abs(pred_reward - true_reward))
        self.uncertainties.append(uncertainty)
        if len(self.state_errors) > self.window:
            self.state_errors.pop(0)
            self.reward_errors.pop(0)
            self.uncertainties.pop(0)

    def summary(self) -> Dict[str, float]:
        n = max(len(self.state_errors), 1)
        return {
            "state_mse": sum(self.state_errors) / n,
            "reward_mae": sum(self.reward_errors) / n,
            "mean_uncertainty": sum(self.uncertainties) / n,
            "hallucination_rate": sum(1 for e in self.state_errors if e > 0.1) / n,
        }

    def model_is_reliable(self) -> bool:
        s = self.summary()
        return s["hallucination_rate"] < 0.15 and s["state_mse"] < 0.08


class AdaptiveTrustRegion:
    """Dynamically adjusts rollout horizon based on model accuracy."""

    def __init__(
        self,
        min_horizon: int = 1,
        max_horizon: int = 15,
        initial_horizon: int = 3,
    ):
        self.min_horizon = min_horizon
        self.max_horizon = max_horizon
        self.horizon = initial_horizon
        self.model_ratio = 0.5  # fraction of model data in training

    def update(self, accuracy: ModelAccuracy) -> None:
        s = accuracy.summary()
        if s["hallucination_rate"] < 0.1 and s["state_mse"] < 0.05:
            self.horizon = min(self.max_horizon, int(self.horizon * 1.2))
            self.model_ratio = min(0.95, self.model_ratio + 0.05)
        elif s["hallucination_rate"] > 0.3 or s["state_mse"] > 0.15:
            self.horizon = max(self.min_horizon, int(self.horizon * 0.7))
            self.model_ratio = max(0.1, self.model_ratio - 0.1)


# ===================================================================
# Policy (for MBPO-style training)
# ===================================================================


class SimplePolicy:
    """Lightweight policy network for model-based policy optimisation."""

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        hidden_dim: int = 64,
        lr: float = 0.001,
    ):
        self.net = MLP(
            [state_dim, hidden_dim, hidden_dim, action_dim],
            ["relu", "relu", "linear"],
        )
        self.action_dim = action_dim
        self.lr = lr
        self.entropy_coef = 0.01

    def action_probs(self, state: List[float]) -> List[float]:
        return _softmax(self.net.forward(state))

    def select_action(self, state: List[float], greedy: bool = False) -> int:
        probs = self.action_probs(state)
        if greedy:
            return max(range(self.action_dim), key=lambda i: probs[i])
        r = random.random()
        cumsum = 0.0
        for i, p in enumerate(probs):
            cumsum += p
            if r <= cumsum:
                return i
        return self.action_dim - 1


# ===================================================================
# ModelBasedAgent
# ===================================================================


class ModelBasedAgent:
    """
    Top-level model-based RL agent for StarCraft II.

    Supports two planning modes:
      - "mpc"  : Model Predictive Control with CEM
      - "mbpo" : Model-Based Policy Optimisation (Dyna-style)

    Workflow:
      1. Collect real transitions.
      2. Train dynamics ensemble on real data.
      3. (MPC)  Plan via CEM at decision time.
         (MBPO) Generate imagined rollouts, train policy on mixed data.
      4. Adaptively adjust rollout horizon based on model accuracy.
    """

    def __init__(self, mode: str = "mbpo"):
        self.mode = mode
        self.ensemble = DynamicsEnsemble(ENSEMBLE_SIZE, STATE_DIM, ACTION_DIM)
        self.real_buffer = PlanningBuffer(capacity=50_000)
        self.imagined_buffer = PlanningBuffer(capacity=200_000)
        self.policy = SimplePolicy(STATE_DIM, ACTION_DIM)
        self.mpc = ModelPredictiveControl(self.ensemble, horizon=5)
        self.accuracy = ModelAccuracy()
        self.trust = AdaptiveTrustRegion()
        self.sc2_predictor = SC2ResourcePredictor(self.ensemble)

        self.total_steps: int = 0
        self.episodes: int = 0
        self.episode_rewards: List[float] = []
        self.model_train_interval: int = 50
        self.policy_train_interval: int = 10

    # ---- interaction ----

    def observe(
        self,
        state: List[float],
        action: int,
        reward: float,
        next_state: List[float],
        done: bool,
    ) -> None:
        """Record a real transition and update accuracy tracker."""
        self.real_buffer.add(state, action, reward, next_state, done)
        pred_ns, pred_r, unc = self.ensemble.predict(state, action)
        self.accuracy.record(pred_ns, next_state, pred_r, reward, unc)
        self.total_steps += 1

    def select_action(self, state: List[float]) -> int:
        if self.mode == "mpc":
            return self.mpc.select_action(state)
        return self.policy.select_action(state)

    # ---- training ----

    def _train_dynamics(self, batch_size: int = 16) -> List[float]:
        return self.ensemble.train_step(self.real_buffer, batch_size)

    def _generate_imagined(self, num_rollouts: int = 64) -> int:
        if len(self.real_buffer) < 10:
            return 0
        horizon = self.trust.horizon
        generated = 0
        start_states = self.real_buffer.sample_states(num_rollouts)
        for state in start_states:
            s = state[:]
            for t in range(horizon):
                action = self.policy.select_action(s)
                ns, r, unc = self.ensemble.predict(s, action)
                if unc > 0.3:
                    break
                self.imagined_buffer.add(s, action, r, ns, t == horizon - 1)
                s = ns
                generated += 1
        return generated

    def _train_policy(self, batch_size: int = 32) -> float:
        ratio = self.trust.model_ratio
        n_model = int(batch_size * ratio)
        n_real = batch_size - n_model

        transitions: List[Transition] = []
        if n_real > 0 and len(self.real_buffer) >= n_real:
            transitions.extend(self.real_buffer.sample(n_real))
        if n_model > 0 and len(self.imagined_buffer) >= n_model:
            transitions.extend(self.imagined_buffer.sample(n_model))
        if not transitions:
            return 0.0

        eps = 1e-4
        total_loss = 0.0
        for tr in transitions:
            probs = self.policy.action_probs(tr.state)
            log_p = math.log(max(probs[tr.action], 1e-10))
            advantage = tr.reward
            loss = -log_p * advantage
            entropy = -sum(p * math.log(max(p, 1e-10)) for p in probs)
            total_loss += loss - self.policy.entropy_coef * entropy

            for layer in self.policy.net.layers:
                for i in range(layer.out_dim):
                    for j in range(min(layer.in_dim, 4)):
                        orig = layer.weights[i][j]
                        layer.weights[i][j] = orig + eps
                        new_probs = self.policy.action_probs(tr.state)
                        new_log = math.log(max(new_probs[tr.action], 1e-10))
                        new_loss = -new_log * advantage
                        grad = (new_loss - loss) / eps
                        layer.weights[i][j] = orig - self.policy.lr * grad

        return total_loss / len(transitions)

    def train(self) -> Dict[str, Any]:
        """One training iteration (call after each observation)."""
        info: Dict[str, Any] = {}

        if (
            self.total_steps % self.model_train_interval == 0
            and len(self.real_buffer) >= 32
        ):
            losses = self._train_dynamics()
            info["model_losses"] = losses
            info["avg_model_loss"] = sum(losses) / len(losses)
            self.trust.update(self.accuracy)
            info["rollout_horizon"] = self.trust.horizon
            info["model_ratio"] = self.trust.model_ratio

        if self.mode == "mbpo" and self.total_steps % self.policy_train_interval == 0:
            generated = self._generate_imagined(self.trust.horizon * 4)
            info["imagined_transitions"] = generated
            if generated > 0:
                info["policy_loss"] = self._train_policy(batch_size=16)

        info["model_metrics"] = self.accuracy.summary()
        info["model_reliable"] = self.accuracy.model_is_reliable()
        return info

    # ---- diagnostics ----

    def diagnostics(self) -> Dict[str, Any]:
        m = self.accuracy.summary()
        return {
            "mode": self.mode,
            "total_steps": self.total_steps,
            "episodes": self.episodes,
            "real_buffer": len(self.real_buffer),
            "imagined_buffer": len(self.imagined_buffer),
            "rollout_horizon": self.trust.horizon,
            "model_ratio": self.trust.model_ratio,
            "model_reliable": self.accuracy.model_is_reliable(),
            "state_mse": m["state_mse"],
            "reward_mae": m["reward_mae"],
            "hallucination_rate": m["hallucination_rate"],
            "mean_uncertainty": m["mean_uncertainty"],
            "avg_episode_reward": (
                sum(self.episode_rewards[-20:])
                / max(len(self.episode_rewards[-20:]), 1)
            ),
        }


# ===================================================================
# SC2 Environment Simulator (for demo)
# ===================================================================


class SC2EnvSim:
    """Lightweight SC2 environment simulator for testing."""

    def __init__(self, max_steps: int = 200):
        self.max_steps = max_steps
        self.step_count = 0
        self.state = self._init_state()

    def _init_state(self) -> List[float]:
        return [
            0.05,
            0.02,
            0.06,
            0.10,
            0.15,  # minerals, gas, supply, max_supply, workers
            0.0,
            0.0,
            0.0,  # army, frame, enemy_army
            0.1,
            0.0,  # threat, tech
            0.2,
            0.2,
            0.1,  # hatch, bases, queens
            0.0,
            0.0,
            0.0,  # upgrades (speed, carapace, missile)
        ]

    def reset(self) -> List[float]:
        self.step_count = 0
        self.state = self._init_state()
        return self.state[:]

    def step(self, action: int) -> Tuple[List[float], float, bool]:
        self.step_count += 1
        s = self.state[:]
        reward = 0.0

        s[0] = min(1.0, s[0] + 0.02 * s[4])
        s[1] = min(1.0, s[1] + 0.01 * s[4])
        s[6] = self.step_count / self.max_steps
        s[7] = min(1.0, 0.01 * self.step_count / self.max_steps)

        if action == 0 and s[0] > 0.05 and s[2] < s[3]:
            s[0] -= 0.05
            s[4] = min(1.0, s[4] + 0.0125)
            s[2] += 0.005
            reward = 0.3
        elif action == 1 and s[0] > 0.025:
            s[0] -= 0.025
            s[5] = min(1.0, s[5] + 0.005)
            s[2] += 0.005
            reward = 0.2
        elif action == 2 and s[0] > 0.075 and s[1] > 0.025:
            s[0] -= 0.075
            s[1] -= 0.025
            s[5] = min(1.0, s[5] + 0.01)
            s[2] += 0.01
            reward = 0.4
        elif action == 3 and s[0] > 0.1:
            s[0] -= 0.1
            s[3] = min(1.0, s[3] + 0.04)
            reward = 0.1 if s[2] > s[3] * 0.8 else -0.05
        elif action == 4 and s[0] > 0.3:
            s[0] -= 0.3
            s[10] = min(1.0, s[10] + 0.2)
            s[11] = min(1.0, s[11] + 0.2)
            reward = 0.5
        elif action == 5:
            if s[5] > s[7]:
                reward = 1.0 * (s[5] - s[7])
                s[5] = max(0.0, s[5] - 0.02)
            else:
                reward = -0.5
                s[5] = max(0.0, s[5] - 0.05)
        elif action == 6:
            reward = 0.3 if s[8] > 0.5 else 0.05
            s[8] = max(0.0, s[8] - 0.1) if s[8] > 0.5 else s[8]

        s[8] = min(1.0, s[7] * 1.5)
        self.state = s
        return s[:], reward, self.step_count >= self.max_steps


# ===================================================================
# Demo
# ===================================================================


def demo(
    mode: str = "mbpo",
    episodes: int = 5,
    steps_per_episode: int = 100,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run a full Model-Based RL demonstration.

    Args:
        mode: "mbpo" (policy optimisation) or "mpc" (planning).
        episodes: number of training episodes.
        steps_per_episode: environment steps per episode.
        verbose: print progress to stdout.

    Returns:
        Dictionary with episode rewards and final diagnostics.
    """
    if verbose:
        print("=" * 60)
        print("  Phase 616: Model-Based RL with Learned Dynamics for SC2")
        print(f"  Mode: {mode.upper()}  |  Episodes: {episodes}")
        print("=" * 60)

    agent = ModelBasedAgent(mode=mode)
    env = SC2EnvSim(max_steps=steps_per_episode)
    all_rewards: List[float] = []

    for ep in range(episodes):
        state = env.reset()
        ep_reward = 0.0
        t0 = time.time()

        for step in range(steps_per_episode):
            action = agent.select_action(state)
            next_state, reward, done = env.step(action)
            agent.observe(state, action, reward, next_state, done)
            agent.train()
            ep_reward += reward
            state = next_state
            if done:
                break

        agent.episodes += 1
        agent.episode_rewards.append(ep_reward)
        all_rewards.append(ep_reward)
        elapsed = time.time() - t0

        if verbose:
            m = agent.accuracy.summary()
            print(
                f"\n  Episode {ep + 1}/{episodes}  |  "
                f"Reward: {ep_reward:+.2f}  |  {elapsed:.2f}s"
            )
            print(
                f"    Buffers: {len(agent.real_buffer)} real, "
                f"{len(agent.imagined_buffer)} imagined"
            )
            print(
                f"    Model MSE: {m['state_mse']:.4f}  |  "
                f"Halluc: {m['hallucination_rate']:.2%}"
            )
            print(
                f"    Horizon: {agent.trust.horizon}  |  "
                f"Ratio: {agent.trust.model_ratio:.2f}"
            )

    diag = agent.diagnostics()

    if verbose:
        print(f"\n{'─' * 60}")
        print("  Final Diagnostics:")
        for k, v in diag.items():
            print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")

        if mode == "mbpo":
            print("\n  [MPC comparison with shared model]")
            mpc_agent = ModelBasedAgent(mode="mpc")
            mpc_agent.ensemble = agent.ensemble
            mpc_env = SC2EnvSim(max_steps=steps_per_episode)
            s = mpc_env.reset()
            mpc_r = 0.0
            for _ in range(steps_per_episode):
                a = mpc_agent.select_action(s)
                s, r, d = mpc_env.step(a)
                mpc_r += r
                if d:
                    break
            print(f"  MPC reward:  {mpc_r:+.2f}")
            print(f"  MBPO mean:   {sum(all_rewards) / len(all_rewards):+.2f}")

        print(f"{'─' * 60}")

    return {
        "mode": mode,
        "episodes": episodes,
        "rewards": all_rewards,
        "mean_reward": sum(all_rewards) / max(len(all_rewards), 1),
        "diagnostics": diag,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 616: Model-Based RL with Learned Dynamics for SC2",
    )
    parser.add_argument("--mode", choices=["mbpo", "mpc"], default="mbpo")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    result = demo(
        mode=args.mode,
        episodes=args.episodes,
        steps_per_episode=args.steps,
        verbose=not args.quiet,
    )
    if args.quiet:
        print(f"Mean reward: {result['mean_reward']:.4f}")


if __name__ == "__main__":
    main()

# Phase 616: Model-Based RL registered
