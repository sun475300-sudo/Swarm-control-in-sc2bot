"""
Phase 620: Safe RL with Constrained Optimization for SC2
=========================================================
safe_rl/sc2_safe_agent.py

Constrained RL agent that maximizes game reward subject to safety constraints.
Uses Lagrangian relaxation to convert the Constrained MDP (CMDP) into a
tractable unconstrained problem with adaptive dual variables.

Classes:
  - SafetyConstraint     : defines a single safety constraint with threshold
  - LagrangianOptimizer  : dual-variable optimizer for constraint satisfaction
  - SafePPO              : PPO with safety-augmented objective
  - SafetyMonitor        : runtime monitoring and violation tracking

SC2-specific safety constraints enforced:
  1. Minimum worker count  (never drop below economic baseline)
  2. Supply buffer         (maintain headroom to avoid supply-block)
  3. Defense threshold     (keep minimum defense at home)
  4. Army commitment limit (don't over-commit entire army)
  5. Economy baseline      (maintain minimum income rate)

Dependencies: numpy (required).
Python 3.10 compatible.
"""

from __future__ import annotations

import argparse
import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:

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
            if isinstance(shape, int):
                return [0.0] * shape
            return [[0.0] * shape[1] for _ in range(shape[0])]

        @staticmethod
        def ones(shape, dtype=None):
            if isinstance(shape, int):
                return [1.0] * shape
            return [[1.0] * shape[1] for _ in range(shape[0])]

        @staticmethod
        def mean(data):
            d = list(data) if not isinstance(data, list) else data
            return sum(d) / max(len(d), 1)

        @staticmethod
        def clip(val, lo, hi):
            if isinstance(val, list):
                return [max(lo, min(hi, v)) for v in val]
            return max(lo, min(hi, val))

        @staticmethod
        def exp(x):
            if isinstance(x, list):
                return [math.exp(v) for v in x]
            return math.exp(x)

        @staticmethod
        def log(x):
            if isinstance(x, list):
                return [math.log(max(v, 1e-10)) for v in x]
            return math.log(max(x, 1e-10))

        @staticmethod
        def sum(data):
            return sum(data) if isinstance(data, list) else data

        @staticmethod
        def sqrt(x):
            return math.sqrt(x)

        class _Random:
            def randn(self, *shape):
                if len(shape) == 0:
                    return random.gauss(0, 1)
                if len(shape) == 1:
                    return [random.gauss(0, 1) for _ in range(shape[0])]
                return [[random.gauss(0, 1) for _ in range(shape[1])]
                        for _ in range(shape[0])]

            def rand(self, *shape):
                if len(shape) == 0:
                    return random.random()
                if len(shape) == 1:
                    return [random.random() for _ in range(shape[0])]
                return [[random.random() for _ in range(shape[1])]
                        for _ in range(shape[0])]

        random = _Random()

    np = _NumpyFallback()  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SC2 Game State representation
# ---------------------------------------------------------------------------

@dataclass
class SC2GameState:
    """Snapshot of relevant SC2 game state for safety evaluation."""

    minerals: float = 0.0
    vespene: float = 0.0
    supply_used: int = 0
    supply_cap: int = 15
    worker_count: int = 12
    army_supply: int = 0
    army_value: float = 0.0
    army_at_home: float = 0.0
    army_attacking: float = 0.0
    income_rate: float = 0.0
    game_time_seconds: float = 0.0
    enemy_army_visible: float = 0.0
    bases_count: int = 1


# ---------------------------------------------------------------------------
# SafetyConstraint
# ---------------------------------------------------------------------------

class SafetyConstraint:
    """
    Defines a single safety constraint for the Constrained MDP.

    A constraint is of the form:
        E[C_i(s, a)] <= d_i

    where C_i is a cost function and d_i is the threshold.
    """

    def __init__(
        self,
        name: str,
        cost_fn: Callable[[SC2GameState, int], float],
        threshold: float,
        description: str = "",
    ) -> None:
        self.name = name
        self.cost_fn = cost_fn
        self.threshold = threshold
        self.description = description
        self._cumulative_cost: float = 0.0
        self._eval_count: int = 0

    def evaluate(self, state: SC2GameState, action: int) -> float:
        """Compute cost for given state-action pair."""
        cost = self.cost_fn(state, action)
        self._cumulative_cost += cost
        self._eval_count += 1
        return cost

    @property
    def average_cost(self) -> float:
        if self._eval_count == 0:
            return 0.0
        return self._cumulative_cost / self._eval_count

    @property
    def is_satisfied(self) -> bool:
        """Check if constraint is currently satisfied on average."""
        return self.average_cost <= self.threshold

    def reset(self) -> None:
        self._cumulative_cost = 0.0
        self._eval_count = 0

    def __repr__(self) -> str:
        status = "OK" if self.is_satisfied else "VIOLATED"
        return (
            f"SafetyConstraint({self.name}, threshold={self.threshold:.3f}, "
            f"avg_cost={self.average_cost:.3f}, {status})"
        )


# ---------------------------------------------------------------------------
# SC2 Safety Constraint Factories
# ---------------------------------------------------------------------------

def _make_worker_constraint(min_workers: int = 16) -> SafetyConstraint:
    """Workers should not drop below a minimum count."""

    def cost_fn(state: SC2GameState, action: int) -> float:
        if state.worker_count < min_workers:
            return float(min_workers - state.worker_count) / min_workers
        return 0.0

    return SafetyConstraint(
        name="min_workers",
        cost_fn=cost_fn,
        threshold=0.1,
        description=f"Maintain at least {min_workers} workers",
    )


def _make_supply_buffer_constraint(buffer: int = 4) -> SafetyConstraint:
    """Maintain supply headroom to avoid supply-block."""

    def cost_fn(state: SC2GameState, action: int) -> float:
        remaining = state.supply_cap - state.supply_used
        if remaining < buffer:
            return float(buffer - remaining) / buffer
        return 0.0

    return SafetyConstraint(
        name="supply_buffer",
        cost_fn=cost_fn,
        threshold=0.15,
        description=f"Keep at least {buffer} supply headroom",
    )


def _make_defense_threshold_constraint(
    min_home_fraction: float = 0.3,
) -> SafetyConstraint:
    """Keep a minimum fraction of army value at home for defense."""

    def cost_fn(state: SC2GameState, action: int) -> float:
        total = state.army_at_home + state.army_attacking
        if total <= 0:
            return 0.0
        home_frac = state.army_at_home / total
        if home_frac < min_home_fraction:
            return (min_home_fraction - home_frac) / min_home_fraction
        return 0.0

    return SafetyConstraint(
        name="defense_threshold",
        cost_fn=cost_fn,
        threshold=0.1,
        description=f"Keep >= {min_home_fraction*100:.0f}% army at home",
    )


def _make_army_commitment_constraint(
    max_attack_fraction: float = 0.8,
) -> SafetyConstraint:
    """Don't over-commit the entire army to an attack."""

    def cost_fn(state: SC2GameState, action: int) -> float:
        total = state.army_at_home + state.army_attacking
        if total <= 0:
            return 0.0
        attack_frac = state.army_attacking / total
        if attack_frac > max_attack_fraction:
            return (attack_frac - max_attack_fraction) / (1.0 - max_attack_fraction + 1e-8)
        return 0.0

    return SafetyConstraint(
        name="army_commitment",
        cost_fn=cost_fn,
        threshold=0.1,
        description=f"Don't send more than {max_attack_fraction*100:.0f}% army to attack",
    )


def _make_economy_baseline_constraint(
    min_income: float = 40.0,
) -> SafetyConstraint:
    """Maintain a minimum income rate."""

    def cost_fn(state: SC2GameState, action: int) -> float:
        if state.game_time_seconds < 120:
            return 0.0
        if state.income_rate < min_income:
            return (min_income - state.income_rate) / min_income
        return 0.0

    return SafetyConstraint(
        name="economy_baseline",
        cost_fn=cost_fn,
        threshold=0.1,
        description=f"Maintain income rate >= {min_income}",
    )


def create_default_constraints() -> List[SafetyConstraint]:
    """Create the default set of SC2 safety constraints."""
    return [
        _make_worker_constraint(min_workers=16),
        _make_supply_buffer_constraint(buffer=4),
        _make_defense_threshold_constraint(min_home_fraction=0.3),
        _make_army_commitment_constraint(max_attack_fraction=0.8),
        _make_economy_baseline_constraint(min_income=40.0),
    ]


# ---------------------------------------------------------------------------
# LagrangianOptimizer
# ---------------------------------------------------------------------------

class LagrangianOptimizer:
    """
    Dual-variable (Lagrange multiplier) optimizer for constraint satisfaction.

    Maintains one multiplier lambda_i per constraint and updates them via
    dual gradient ascent:
        lambda_i <- max(0, lambda_i + lr * (avg_cost_i - threshold_i))

    The augmented objective becomes:
        L(theta, lambda) = J(theta) - sum_i lambda_i * (J_ci(theta) - d_i)
    """

    def __init__(
        self,
        constraints: List[SafetyConstraint],
        lr: float = 0.01,
        lambda_max: float = 10.0,
        lambda_init: float = 0.0,
    ) -> None:
        self.constraints = constraints
        self.lr = lr
        self.lambda_max = lambda_max
        self._lambdas: List[float] = [lambda_init] * len(constraints)
        self._update_history: List[Dict[str, Any]] = []

    @property
    def lambdas(self) -> List[float]:
        return list(self._lambdas)

    def compute_penalty(
        self,
        costs: List[float],
    ) -> float:
        """Compute total Lagrangian penalty: sum_i lambda_i * cost_i."""
        penalty = 0.0
        for i, cost in enumerate(costs):
            penalty += self._lambdas[i] * cost
        return penalty

    def augmented_reward(
        self,
        reward: float,
        costs: List[float],
    ) -> float:
        """Compute reward - penalty for policy optimization."""
        return reward - self.compute_penalty(costs)

    def update_multipliers(self) -> Dict[str, float]:
        """
        Dual gradient ascent step.

        Updates each lambda based on how much the corresponding constraint
        is violated (positive) or satisfied (negative margin).
        """
        updates: Dict[str, float] = {}
        for i, constraint in enumerate(self.constraints):
            violation = constraint.average_cost - constraint.threshold
            self._lambdas[i] = max(
                0.0,
                min(
                    self.lambda_max,
                    self._lambdas[i] + self.lr * violation,
                ),
            )
            updates[constraint.name] = self._lambdas[i]

        self._update_history.append({
            "lambdas": list(self._lambdas),
            "timestamp": time.time(),
        })
        return updates

    def get_constraint_status(self) -> List[Dict[str, Any]]:
        """Return status of all constraints with current multipliers."""
        statuses = []
        for i, c in enumerate(self.constraints):
            statuses.append({
                "name": c.name,
                "threshold": c.threshold,
                "avg_cost": c.average_cost,
                "lambda": self._lambdas[i],
                "satisfied": c.is_satisfied,
                "description": c.description,
            })
        return statuses

    def reset(self) -> None:
        self._lambdas = [0.0] * len(self.constraints)
        self._update_history.clear()
        for c in self.constraints:
            c.reset()


# ---------------------------------------------------------------------------
# SafePPO
# ---------------------------------------------------------------------------

@dataclass
class PPOConfig:
    """Configuration for Safe PPO."""

    state_dim: int = 12
    action_dim: int = 8
    hidden_dim: int = 64
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    lr_actor: float = 3e-4
    lr_critic: float = 1e-3
    epochs_per_update: int = 4
    batch_size: int = 64
    max_grad_norm: float = 0.5


class SafePPO:
    """
    Proximal Policy Optimization with safety-augmented objective.

    Maximizes:
        L_safe(theta) = L_ppo(theta) - sum_i lambda_i * J_ci(theta)

    where lambda_i are updated by the LagrangianOptimizer.
    """

    def __init__(
        self,
        config: PPOConfig,
        lagrangian: LagrangianOptimizer,
    ) -> None:
        self.config = config
        self.lagrangian = lagrangian
        self._step_count: int = 0
        self._episode_count: int = 0

        # Simple linear policy weights (numpy-based)
        self._policy_weights = np.zeros(
            (config.state_dim, config.action_dim)
        )
        self._value_weights = np.zeros(config.state_dim)

        # Trajectory buffer
        self._buffer: List[Dict[str, Any]] = []
        self._episode_rewards: List[float] = []
        self._episode_costs: List[List[float]] = []

        logger.info(
            "SafePPO initialized: state_dim=%d, action_dim=%d, constraints=%d",
            config.state_dim,
            config.action_dim,
            len(lagrangian.constraints),
        )

    def _state_to_features(self, state: SC2GameState) -> List[float]:
        """Convert SC2 game state to feature vector."""
        return [
            state.minerals / 1000.0,
            state.vespene / 500.0,
            state.supply_used / 200.0,
            state.supply_cap / 200.0,
            state.worker_count / 80.0,
            state.army_supply / 200.0,
            state.army_value / 5000.0,
            state.army_at_home / 5000.0,
            state.army_attacking / 5000.0,
            state.income_rate / 100.0,
            state.game_time_seconds / 1200.0,
            state.bases_count / 5.0,
        ]

    def _softmax(self, logits: List[float]) -> List[float]:
        """Compute softmax probabilities from logits."""
        max_l = max(logits)
        exps = [math.exp(l - max_l) for l in logits]
        total = sum(exps)
        return [e / total for e in exps]

    def select_action(
        self,
        state: SC2GameState,
        deterministic: bool = False,
    ) -> Tuple[int, float]:
        """
        Select action using current policy.

        Returns (action_index, log_probability).
        """
        features = self._state_to_features(state)

        # Linear policy: logits = features @ weights
        logits = []
        for a in range(self.config.action_dim):
            logit = 0.0
            for j, f in enumerate(features):
                w = (
                    self._policy_weights[j][a]
                    if isinstance(self._policy_weights[j], list)
                    else self._policy_weights[j, a]
                )
                logit += f * w
            logits.append(logit)

        probs = self._softmax(logits)

        if deterministic:
            action = probs.index(max(probs))
        else:
            r = random.random()
            cumsum = 0.0
            action = len(probs) - 1
            for i, p in enumerate(probs):
                cumsum += p
                if r <= cumsum:
                    action = i
                    break

        log_prob = math.log(max(probs[action], 1e-10))
        return action, log_prob

    def estimate_value(self, state: SC2GameState) -> float:
        """Estimate state value using value function."""
        features = self._state_to_features(state)
        value = 0.0
        for j, f in enumerate(features):
            w = (
                self._value_weights[j]
                if isinstance(self._value_weights, list)
                else float(self._value_weights[j])
            )
            value += f * w
        return value

    def store_transition(
        self,
        state: SC2GameState,
        action: int,
        reward: float,
        costs: List[float],
        next_state: SC2GameState,
        done: bool,
        log_prob: float,
    ) -> None:
        """Store a transition in the replay buffer."""
        # Compute safety-augmented reward
        safe_reward = self.lagrangian.augmented_reward(reward, costs)

        self._buffer.append({
            "state": state,
            "action": action,
            "reward": reward,
            "safe_reward": safe_reward,
            "costs": costs,
            "next_state": next_state,
            "done": done,
            "log_prob": log_prob,
        })
        self._step_count += 1

    def update(self) -> Dict[str, float]:
        """
        Run a PPO update using collected transitions.

        Updates both policy and Lagrange multipliers.
        """
        if len(self._buffer) == 0:
            return {"policy_loss": 0.0, "value_loss": 0.0}

        # Compute advantages using GAE
        advantages = []
        returns = []
        gae = 0.0

        for i in reversed(range(len(self._buffer))):
            t = self._buffer[i]
            if t["done"] or i == len(self._buffer) - 1:
                next_val = 0.0
            else:
                next_val = self.estimate_value(t["next_state"])
            current_val = self.estimate_value(t["state"])
            delta = t["safe_reward"] + self.config.gamma * next_val - current_val
            gae = delta + self.config.gamma * self.config.gae_lambda * gae
            advantages.insert(0, gae)
            returns.insert(0, gae + current_val)

        # Normalize advantages
        if len(advantages) > 1:
            mean_a = sum(advantages) / len(advantages)
            var_a = sum((a - mean_a) ** 2 for a in advantages) / len(advantages)
            std_a = math.sqrt(var_a + 1e-8)
            advantages = [(a - mean_a) / std_a for a in advantages]

        # Simplified policy gradient update
        total_policy_loss = 0.0
        total_value_loss = 0.0

        for epoch in range(self.config.epochs_per_update):
            for i, t in enumerate(self._buffer):
                features = self._state_to_features(t["state"])
                adv = advantages[i]
                old_log_prob = t["log_prob"]

                _, new_log_prob = self.select_action(t["state"])
                ratio = math.exp(new_log_prob - old_log_prob)
                clipped = max(
                    1 - self.config.clip_epsilon,
                    min(1 + self.config.clip_epsilon, ratio),
                )
                policy_loss = -min(ratio * adv, clipped * adv)

                # Value loss
                pred_val = self.estimate_value(t["state"])
                value_loss = (pred_val - returns[i]) ** 2

                # Simple gradient step on weights
                lr = self.config.lr_actor
                for j, f in enumerate(features):
                    if isinstance(self._policy_weights[j], list):
                        self._policy_weights[j][t["action"]] -= (
                            lr * policy_loss * f * 0.01
                        )
                    else:
                        self._policy_weights[j, t["action"]] -= (
                            lr * policy_loss * f * 0.01
                        )

                    if isinstance(self._value_weights, list):
                        self._value_weights[j] -= (
                            self.config.lr_critic * value_loss * f * 0.01
                        )
                    else:
                        self._value_weights[j] -= (
                            self.config.lr_critic * value_loss * f * 0.01
                        )

                total_policy_loss += policy_loss
                total_value_loss += value_loss

        n = max(len(self._buffer) * self.config.epochs_per_update, 1)

        # Update Lagrange multipliers
        lambda_updates = self.lagrangian.update_multipliers()
        logger.debug("Lambda updates: %s", lambda_updates)

        # Clear buffer
        self._buffer.clear()
        self._episode_count += 1

        return {
            "policy_loss": total_policy_loss / n,
            "value_loss": total_value_loss / n,
            "episodes": self._episode_count,
            "steps": self._step_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return training statistics."""
        return {
            "step_count": self._step_count,
            "episode_count": self._episode_count,
            "buffer_size": len(self._buffer),
            "constraint_status": self.lagrangian.get_constraint_status(),
            "lambdas": self.lagrangian.lambdas,
        }


# ---------------------------------------------------------------------------
# SafetyMonitor
# ---------------------------------------------------------------------------

@dataclass
class ViolationRecord:
    """Record of a single constraint violation."""

    constraint_name: str
    cost: float
    threshold: float
    game_time: float
    state_snapshot: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class SafetyMonitor:
    """
    Runtime safety monitoring and violation tracking.

    Monitors all constraints in real-time, logs violations, computes
    aggregate safety metrics, and can trigger emergency interventions.
    """

    def __init__(
        self,
        constraints: List[SafetyConstraint],
        violation_budget: int = 50,
        emergency_threshold: int = 10,
    ) -> None:
        self.constraints = constraints
        self.violation_budget = violation_budget
        self.emergency_threshold = emergency_threshold
        self._violations: List[ViolationRecord] = []
        self._total_checks: int = 0
        self._consecutive_violations: Dict[str, int] = {
            c.name: 0 for c in constraints
        }

    def check_safety(
        self,
        state: SC2GameState,
        action: int,
    ) -> Tuple[bool, List[ViolationRecord]]:
        """
        Check all constraints for the given state-action pair.

        Returns (all_safe, list_of_violations).
        """
        self._total_checks += 1
        violations: List[ViolationRecord] = []

        for constraint in self.constraints:
            cost = constraint.evaluate(state, action)
            if cost > constraint.threshold:
                record = ViolationRecord(
                    constraint_name=constraint.name,
                    cost=cost,
                    threshold=constraint.threshold,
                    game_time=state.game_time_seconds,
                    state_snapshot={
                        "minerals": state.minerals,
                        "workers": state.worker_count,
                        "supply": f"{state.supply_used}/{state.supply_cap}",
                        "army_home": state.army_at_home,
                        "army_attack": state.army_attacking,
                        "income": state.income_rate,
                    },
                )
                violations.append(record)
                self._violations.append(record)
                self._consecutive_violations[constraint.name] += 1
                logger.warning(
                    "Safety violation: %s (cost=%.3f > threshold=%.3f) at t=%.1f",
                    constraint.name,
                    cost,
                    constraint.threshold,
                    state.game_time_seconds,
                )
            else:
                self._consecutive_violations[constraint.name] = 0

        all_safe = len(violations) == 0
        return all_safe, violations

    def is_emergency(self) -> bool:
        """Check if any constraint has too many consecutive violations."""
        return any(
            count >= self.emergency_threshold
            for count in self._consecutive_violations.values()
        )

    def get_emergency_constraints(self) -> List[str]:
        """Return names of constraints in emergency state."""
        return [
            name
            for name, count in self._consecutive_violations.items()
            if count >= self.emergency_threshold
        ]

    @property
    def violation_rate(self) -> float:
        if self._total_checks == 0:
            return 0.0
        return len(self._violations) / self._total_checks

    @property
    def budget_remaining(self) -> int:
        return max(0, self.violation_budget - len(self._violations))

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of safety monitoring status."""
        per_constraint: Dict[str, int] = {}
        for v in self._violations:
            per_constraint[v.constraint_name] = (
                per_constraint.get(v.constraint_name, 0) + 1
            )

        return {
            "total_checks": self._total_checks,
            "total_violations": len(self._violations),
            "violation_rate": round(self.violation_rate, 4),
            "budget_remaining": self.budget_remaining,
            "is_emergency": self.is_emergency(),
            "per_constraint": per_constraint,
            "consecutive": dict(self._consecutive_violations),
        }

    def reset(self) -> None:
        self._violations.clear()
        self._total_checks = 0
        self._consecutive_violations = {c.name: 0 for c in self.constraints}


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def _simulate_game_state(step: int) -> SC2GameState:
    """Generate a simulated SC2 game state for demo purposes."""
    t = float(step * 10)
    return SC2GameState(
        minerals=200 + random.gauss(0, 50),
        vespene=100 + random.gauss(0, 30),
        supply_used=min(20 + step * 2, 190),
        supply_cap=min(23 + step * 2 + random.randint(0, 3), 200),
        worker_count=max(12 + step, min(70 + random.randint(-5, 5), 80)),
        army_supply=min(step * 3, 120),
        army_value=float(min(step * 150, 6000)),
        army_at_home=float(min(step * 100, 4000)) * random.uniform(0.3, 0.9),
        army_attacking=float(min(step * 50, 2000)) * random.uniform(0.0, 0.7),
        income_rate=30.0 + step * 2 + random.gauss(0, 5),
        game_time_seconds=t,
        enemy_army_visible=random.uniform(0, 3000),
        bases_count=min(1 + step // 10, 5),
    )


def demo() -> None:
    """Run Phase 620 Safe RL demonstration."""
    print("=" * 70)
    print("Phase 620: Safe RL with Constrained Optimization for SC2")
    print("=" * 70)
    print()

    # 1. Create constraints
    constraints = create_default_constraints()
    print(f"[1] Created {len(constraints)} safety constraints:")
    for c in constraints:
        print(f"    - {c.name}: {c.description} (threshold={c.threshold})")
    print()

    # 2. Lagrangian optimizer
    lagrangian = LagrangianOptimizer(constraints, lr=0.05, lambda_max=5.0)
    print("[2] LagrangianOptimizer initialized")
    print(f"    Initial lambdas: {lagrangian.lambdas}")
    print()

    # 3. Safe PPO agent
    config = PPOConfig(state_dim=12, action_dim=8)
    agent = SafePPO(config, lagrangian)
    print("[3] SafePPO agent created")
    print(f"    State dim: {config.state_dim}, Action dim: {config.action_dim}")
    print()

    # 4. Safety monitor
    monitor = SafetyMonitor(constraints, violation_budget=100)
    print("[4] SafetyMonitor active")
    print()

    # 5. Simulate training loop
    print("[5] Simulating 30 training steps...")
    print("-" * 60)

    for step in range(30):
        state = _simulate_game_state(step)
        action, log_prob = agent.select_action(state)

        # Check safety
        safe, violations = monitor.check_safety(state, action)

        # Compute per-constraint costs
        costs = [c.evaluate(state, action) for c in constraints]

        # Reward from environment
        reward = random.uniform(0.5, 2.0) + state.income_rate * 0.01

        # Next state
        next_state = _simulate_game_state(step + 1)

        # Store transition
        agent.store_transition(state, action, reward, costs, next_state, False, log_prob)

        if (step + 1) % 10 == 0:
            # PPO update every 10 steps
            metrics = agent.update()
            print(
                f"  Step {step + 1:3d}: action={action}, reward={reward:.2f}, "
                f"safe={safe}, policy_loss={metrics['policy_loss']:.4f}"
            )
            status = lagrangian.get_constraint_status()
            for s in status:
                flag = "OK" if s["satisfied"] else "VIOLATED"
                print(
                    f"    {s['name']:20s} lambda={s['lambda']:.3f} "
                    f"avg_cost={s['avg_cost']:.3f} [{flag}]"
                )

    print("-" * 60)
    print()

    # 6. Final report
    print("[6] Safety Monitor Summary:")
    summary = monitor.get_summary()
    for key, val in summary.items():
        print(f"    {key}: {val}")
    print()

    print("[7] Agent Stats:")
    stats = agent.get_stats()
    print(f"    Steps: {stats['step_count']}")
    print(f"    Episodes: {stats['episode_count']}")
    print(f"    Final lambdas: {stats['lambdas']}")
    print()

    print("=" * 70)
    print("Phase 620 demo complete.")
    print("=" * 70)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Phase 620: Safe RL with Constrained Optimization for SC2",
    )
    parser.add_argument(
        "--demo", action="store_true", default=True, help="Run demo"
    )
    parser.parse_args()
    demo()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    main()

# Phase 620: Safe RL registered
