"""
Phase 530: PennyLane Quantum ML
SC2 Bot Quantum Policy Network — hybrid quantum-classical RL
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

try:
    import numpy as np
    import pennylane as qml

    PENNYLANE_AVAILABLE = True
except ImportError:
    PENNYLANE_AVAILABLE = False
    import math as np_fallback


# ─────────────────────────────────────────────
# Quantum circuit parameters
# ─────────────────────────────────────────────

N_QUBITS = 6  # Encode game state into 6 qubits
N_LAYERS = 4  # Variational layers
N_ACTIONS = 5  # train_drone, train_army, build, expand, attack


# ─────────────────────────────────────────────
# PennyLane device setup
# ─────────────────────────────────────────────

if PENNYLANE_AVAILABLE:
    dev = qml.device("default.qubit", wires=N_QUBITS)

    @qml.qnode(dev)
    def quantum_policy_circuit(inputs, weights):
        """
        Variational quantum circuit for SC2 policy.
        inputs: encoded game state (N_QUBITS angles)
        weights: trainable parameters (N_LAYERS x N_QUBITS x 3)
        """
        # Encode state
        for i in range(N_QUBITS):
            qml.RY(inputs[i], wires=i)

        # Variational layers
        for layer in range(N_LAYERS):
            # Entanglement
            for i in range(N_QUBITS - 1):
                qml.CNOT(wires=[i, i + 1])
            qml.CNOT(wires=[N_QUBITS - 1, 0])

            # Rotation layer
            for i in range(N_QUBITS):
                qml.RX(weights[layer, i, 0], wires=i)
                qml.RY(weights[layer, i, 1], wires=i)
                qml.RZ(weights[layer, i, 2], wires=i)

        # Measure expectation values
        return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]


# ─────────────────────────────────────────────
# State encoder / action decoder
# ─────────────────────────────────────────────


def encode_state(
    minerals: int, gas: int, supply: int, workers: int, army: int, threat: float
) -> list[float]:
    """Map game state to qubit angles [0, π]."""

    def clip_angle(v: float) -> float:
        return max(0.0, min(math.pi, v))

    return [
        clip_angle(math.pi * min(minerals, 500) / 500),
        clip_angle(math.pi * min(gas, 300) / 300),
        clip_angle(math.pi * min(supply, 200) / 200),
        clip_angle(math.pi * min(workers, 66) / 66),
        clip_angle(math.pi * min(army, 100) / 100),
        clip_angle(math.pi * threat),
    ]


def decode_action(measurements: list[float]) -> int:
    """Map quantum measurements [-1, 1] → action index."""
    # Map 6 Z-measurements to 5 actions via softmax-like weighting
    logits = measurements[:N_ACTIONS]
    # softmax
    exp_l = [math.exp(l) for l in logits]
    s = sum(exp_l)
    probs = [e / s for e in exp_l]
    # sample
    r = random.random()
    cum = 0.0
    for i, p in enumerate(probs):
        cum += p
        if r <= cum:
            return i
    return N_ACTIONS - 1


# ─────────────────────────────────────────────
# Quantum Policy Network
# ─────────────────────────────────────────────


class QuantumPolicyNetwork:
    """Hybrid quantum-classical policy network for SC2 RL."""

    ACTIONS = ["train_drone", "train_army", "build_supply", "expand", "attack"]

    def __init__(self, use_quantum: bool = True):
        self.use_quantum = use_quantum and PENNYLANE_AVAILABLE
        self._init_weights()
        self.episode_rewards: list[float] = []

    def _init_weights(self) -> None:
        if self.use_quantum:
            import numpy as np

            self.weights = np.random.uniform(
                -math.pi, math.pi, size=(N_LAYERS, N_QUBITS, 3)
            )
        else:
            # Classical fallback: simple linear policy
            self.weights = [
                [random.uniform(-1, 1) for _ in range(N_QUBITS)]
                for _ in range(N_ACTIONS)
            ]

    def select_action(self, state_vec: list[float]) -> tuple[int, float]:
        """Returns (action_idx, log_prob)."""
        if self.use_quantum:
            import numpy as np

            measurements = quantum_policy_circuit(np.array(state_vec), self.weights)
            action = decode_action(list(measurements))
            log_prob = math.log(1.0 / N_ACTIONS)  # uniform approximation
        else:
            # Classical: dot product scoring
            scores = []
            for row in self.weights:
                score = sum(w * s for w, s in zip(row, state_vec))
                scores.append(score)
            max_score = max(scores)
            exp_s = [math.exp(s - max_score) for s in scores]
            total = sum(exp_s)
            probs = [e / total for e in exp_s]
            r = random.random()
            cum = 0.0
            action = 0
            for i, p in enumerate(probs):
                cum += p
                if r <= cum:
                    action = i
                    break
            log_prob = math.log(max(1e-10, probs[action]))

        return action, log_prob

    def update(
        self, states: list, actions: list, rewards: list, lr: float = 0.01
    ) -> float:
        """REINFORCE policy gradient update (simplified)."""
        total_reward = sum(rewards)
        self.episode_rewards.append(total_reward)
        # In full implementation: compute gradients via parameter shift
        # and update self.weights
        return total_reward

    def get_action_name(self, idx: int) -> str:
        return self.ACTIONS[idx] if idx < len(self.ACTIONS) else "unknown"


# ─────────────────────────────────────────────
# Training loop
# ─────────────────────────────────────────────


@dataclass
class SC2Env:
    """Minimal SC2 environment for quantum RL testing."""

    minerals: int = 50
    gas: int = 0
    supply: int = 12
    workers: int = 12
    army: int = 0
    frame: int = 0
    threat: float = 0.0

    def step(self, action: int) -> tuple[list[float], float, bool]:
        # Economy tick
        self.minerals += self.workers * 8 // 10
        self.frame += 1
        self.threat = min(1.0, self.frame / 3000)

        reward = 0.0
        if action == 0:  # drone
            if self.minerals >= 50:
                self.minerals -= 50
                self.workers += 1
                reward = 0.5
        elif action == 1:  # army
            if self.minerals >= 25:
                self.minerals -= 25
                self.army += 1
                reward = 0.3
        elif action == 2:  # supply
            if self.minerals >= 100:
                self.minerals -= 100
                self.supply += 8
                reward = 0.2
        elif action == 3:  # expand
            if self.minerals >= 300:
                self.minerals -= 300
                self.workers += 4
                reward = 1.0
        elif action == 4:  # attack
            reward = self.army * 0.1

        done = self.frame >= 500
        state = encode_state(
            self.minerals, self.gas, self.supply, self.workers, self.army, self.threat
        )
        return state, reward, done


def train_quantum_agent(episodes: int = 20) -> QuantumPolicyNetwork:
    policy = QuantumPolicyNetwork(use_quantum=PENNYLANE_AVAILABLE)
    print(f"Using {'quantum' if policy.use_quantum else 'classical'} policy")

    for ep in range(episodes):
        env = SC2Env()
        state = encode_state(
            env.minerals, env.gas, env.supply, env.workers, env.army, env.threat
        )
        states, actions_taken, rewards = [], [], []
        done = False

        while not done:
            action, log_prob = policy.select_action(state)
            next_state, reward, done = env.step(action)
            states.append(state)
            actions_taken.append(action)
            rewards.append(reward)
            state = next_state

        total = policy.update(states, actions_taken, rewards)
        if (ep + 1) % 5 == 0:
            print(
                f"  Episode {ep+1:3d} | Reward: {total:.1f} | "
                f"Army: {env.army} | Workers: {env.workers}"
            )

    return policy


if __name__ == "__main__":
    print("Phase 530: PennyLane QML — Quantum Policy Network")
    print(f"PennyLane available: {PENNYLANE_AVAILABLE}")
    agent = train_quantum_agent(episodes=20)
    print(f"\nTraining complete. Episodes: {len(agent.episode_rewards)}")
    print(f"Best reward: {max(agent.episode_rewards):.1f}")
