"""
Phase 369: Multi-Task RL Agent
Combines macro and micro decision-making via a mixture-of-experts architecture
with task-specific heads for Zerg bot control.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math
import random


class TaskModule(Enum):
    MACRO_STRATEGY = "macro_strategy"
    WORKER_PRODUCTION = "worker_production"
    ARMY_PRODUCTION = "army_production"
    ARMY_CONTROL = "army_control"
    SCOUTING = "scouting"


@dataclass
class TaskObservation:
    """Flat feature vector for a specific task module."""
    task: TaskModule
    features: List[float]
    timestamp: float = 0.0


@dataclass
class TaskAction:
    task: TaskModule
    action_id: int
    action_name: str
    confidence: float = 1.0
    parameters: Dict = field(default_factory=dict)

    def __repr__(self):
        return f"Action({self.task.value}/{self.action_name}, conf={self.confidence:.3f})"


@dataclass
class ExpertHead:
    """A task-specific policy head."""
    task: TaskModule
    action_space: List[str]
    weights: List[float] = field(default_factory=list)   # simplified weight vector
    learning_rate: float = 1e-4
    total_updates: int = 0

    def __post_init__(self):
        if not self.weights:
            self.weights = [random.gauss(0, 0.1) for _ in self.action_space]

    def forward(self, features: List[float]) -> List[float]:
        """
        Compute softmax logits for each action given features.
        Simplified dot-product scoring (real impl would use neural network).
        """
        n_actions = len(self.action_space)
        n_feat = len(features)
        logits = []
        for i in range(n_actions):
            idx = i % len(self.weights)
            score = sum(
                features[j % n_feat] * self.weights[(i + j) % len(self.weights)]
                for j in range(min(n_feat, 8))
            )
            logits.append(score + self.weights[idx])
        return _softmax(logits)

    def update(self, action_idx: int, reward: float):
        """Simplified policy gradient weight update."""
        lr = self.learning_rate
        for i, _ in enumerate(self.weights):
            grad = reward * (1.0 if i == action_idx % len(self.weights) else -0.01)
            self.weights[i] += lr * grad
        self.total_updates += 1


def _softmax(x: List[float]) -> List[float]:
    max_x = max(x) if x else 0.0
    exps = [math.exp(v - max_x) for v in x]
    total = sum(exps)
    return [e / total for e in exps]


# ------------------------------------------------------------------
# Action spaces per task
# ------------------------------------------------------------------

MACRO_ACTIONS = [
    "expand_now", "tech_up", "army_push", "drone_build", "wait_macro",
    "third_base", "upgrade_ground", "upgrade_air",
]

WORKER_ACTIONS = [
    "build_drone", "stop_drones", "transfer_workers", "saturate_gas",
]

ARMY_ACTIONS = [
    "build_zergling", "build_roach", "build_hydralisk", "build_mutalisk",
    "build_ravager", "build_baneling", "build_ultralisk", "hold_production",
]

ARMY_CONTROL_ACTIONS = [
    "attack_move", "retreat", "surround", "focus_fire", "split_army",
    "runby", "hold_position", "inject_creep",
]

SCOUTING_ACTIONS = [
    "send_drone_scout", "position_overlord", "cancel_scout",
    "watch_third", "watch_drop_paths",
]

TASK_ACTION_SPACES = {
    TaskModule.MACRO_STRATEGY:   MACRO_ACTIONS,
    TaskModule.WORKER_PRODUCTION: WORKER_ACTIONS,
    TaskModule.ARMY_PRODUCTION:  ARMY_ACTIONS,
    TaskModule.ARMY_CONTROL:     ARMY_CONTROL_ACTIONS,
    TaskModule.SCOUTING:         SCOUTING_ACTIONS,
}


class GatingNetwork:
    """
    Mixture-of-experts gate: distributes importance weights across task modules
    based on global game state features.
    """

    def __init__(self):
        self._task_list = list(TaskModule)
        n = len(self._task_list)
        self._weights = [1.0 / n] * n

    def compute_gates(self, global_features: List[float]) -> Dict[TaskModule, float]:
        """Return normalized importance score per task module."""
        raw = []
        for i, _ in enumerate(self._task_list):
            val = sum(
                global_features[j % len(global_features)] * math.sin(i + j + 1)
                for j in range(min(len(global_features), 6))
            )
            raw.append(abs(val) + self._weights[i])
        scores = _softmax(raw)
        return {task: scores[i] for i, task in enumerate(self._task_list)}

    def update_weight(self, task: TaskModule, delta: float):
        idx = self._task_list.index(task)
        self._weights[idx] = max(0.01, self._weights[idx] + delta)


class MultiTaskAgent:
    """
    Multi-task RL agent for Zerg bot control.
    Uses task-specific expert heads and a gating network for action selection.
    """

    def __init__(self, exploration_rate: float = 0.1):
        self.exploration_rate = exploration_rate
        self.experts: Dict[TaskModule, ExpertHead] = {
            task: ExpertHead(task=task, action_space=actions)
            for task, actions in TASK_ACTION_SPACES.items()
        }
        self.gate = GatingNetwork()
        self._step_count: int = 0
        self._reward_history: List[Tuple[TaskModule, float]] = []

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def select_action(
        self,
        task: TaskModule,
        observation: TaskObservation,
        greedy: bool = False,
    ) -> TaskAction:
        """Sample or greedily select an action for a given task module."""
        expert = self.experts[task]
        probs = expert.forward(observation.features)
        action_space = TASK_ACTION_SPACES[task]

        if not greedy and random.random() < self.exploration_rate:
            idx = random.randint(0, len(action_space) - 1)
        else:
            idx = max(range(len(probs)), key=lambda i: probs[i])

        return TaskAction(
            task=task,
            action_id=idx,
            action_name=action_space[idx],
            confidence=probs[idx],
        )

    def act_all_tasks(
        self,
        observations: Dict[TaskModule, TaskObservation],
        global_features: Optional[List[float]] = None,
    ) -> List[TaskAction]:
        """
        Generate one action per task module.
        Uses gate weights to prioritize which tasks receive greedy inference.
        """
        gates = self.gate.compute_gates(global_features or [0.5] * 8)
        actions = []
        for task, obs in observations.items():
            importance = gates.get(task, 0.2)
            greedy = importance > 0.3
            action = self.select_action(task, obs, greedy=greedy)
            actions.append(action)
        self._step_count += 1
        return actions

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    def update(self, task: TaskModule, action_id: int, reward: float):
        """Update the expert head for the given task with a scalar reward."""
        self.experts[task].update(action_id, reward)
        self._reward_history.append((task, reward))
        # Update gate weights based on reward signal
        self.gate.update_weight(task, reward * 0.01)

    def batch_update(self, experiences: List[Tuple[TaskModule, int, float]]):
        """Process a batch of (task, action_id, reward) tuples."""
        for task, action_id, reward in experiences:
            self.update(task, action_id, reward)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        avg_rewards: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for task, reward in self._reward_history[-200:]:
            key = task.value
            avg_rewards[key] = avg_rewards.get(key, 0.0) + reward
            counts[key] = counts.get(key, 0) + 1
        return {
            "step_count": self._step_count,
            "avg_rewards": {
                k: round(v / counts[k], 4)
                for k, v in avg_rewards.items()
            },
            "expert_updates": {
                task.value: expert.total_updates
                for task, expert in self.experts.items()
            },
            "exploration_rate": self.exploration_rate,
        }

    def decay_exploration(self, factor: float = 0.999):
        self.exploration_rate = max(0.02, self.exploration_rate * factor)
