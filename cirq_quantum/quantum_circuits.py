"""
Phase 529: Cirq Quantum Computing (Google)
SC2 Bot resource routing via quantum annealing simulation
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import math
import cmath
import random

try:
    import cirq
    import numpy as np

    CIRQ_AVAILABLE = True
except ImportError:
    CIRQ_AVAILABLE = False


# ─────────────────────────────────────────────
# Pure-Python complex amplitude simulation
# ─────────────────────────────────────────────


class QuantumState:
    """Minimal statevector simulator for n-qubit systems."""

    def __init__(self, n: int):
        self.n = n
        dim = 1 << n
        self.amplitudes = [complex(0, 0)] * dim
        self.amplitudes[0] = complex(1, 0)  # |000...0>

    def apply_h(self, qubit: int) -> None:
        """Hadamard gate."""
        h = 1.0 / math.sqrt(2)
        dim = len(self.amplitudes)
        new_amp = self.amplitudes[:]
        for i in range(dim):
            if not (i >> qubit & 1):
                j = i | (1 << qubit)
                a0, a1 = self.amplitudes[i], self.amplitudes[j]
                new_amp[i] = h * (a0 + a1)
                new_amp[j] = h * (a0 - a1)
        self.amplitudes = new_amp

    def apply_rz(self, qubit: int, angle: float) -> None:
        """Rz rotation gate."""
        for i in range(len(self.amplitudes)):
            if i >> qubit & 1:
                self.amplitudes[i] *= cmath.exp(complex(0, angle / 2))
            else:
                self.amplitudes[i] *= cmath.exp(complex(0, -angle / 2))

    def apply_cnot(self, control: int, target: int) -> None:
        """CNOT gate."""
        new_amp = self.amplitudes[:]
        for i in range(len(self.amplitudes)):
            if i >> control & 1:
                j = i ^ (1 << target)
                new_amp[i] = self.amplitudes[j]
                new_amp[j] = self.amplitudes[i]
        self.amplitudes = new_amp

    def measure(self, shots: int = 1) -> list[str]:
        """Sample bitstrings from the statevector."""
        probs = [abs(a) ** 2 for a in self.amplitudes]
        results = []
        for _ in range(shots):
            r = random.random()
            cum = 0.0
            for idx, p in enumerate(probs):
                cum += p
                if r <= cum:
                    results.append(format(idx, f"0{self.n}b"))
                    break
        return results

    def expectation_zz(self, i: int, j: int) -> float:
        """<ZZ> for qubits i and j."""
        total = 0.0
        for idx, a in enumerate(self.amplitudes):
            zi = 1 if (idx >> i & 1) == 0 else -1
            zj = 1 if (idx >> j & 1) == 0 else -1
            total += zi * zj * abs(a) ** 2
        return total


# ─────────────────────────────────────────────
# SC2 routing problem on a grid graph
# ─────────────────────────────────────────────


@dataclass
class RoutingProblem:
    """
    Max-cut formulation for army routing.
    Qubits = map nodes; edge weights = strategic value.
    """

    nodes: list[str]  # e.g. ["main_base", "natural", "third", "enemy_main"]
    edges: list[tuple[int, int, float]]  # (i, j, weight)

    def max_cut_value(self, assignment: list[int]) -> float:
        """Count weighted cut edges."""
        total = 0.0
        for i, j, w in self.edges:
            if assignment[i] != assignment[j]:
                total += w
        return total


# ─────────────────────────────────────────────
# QAOA on the routing problem
# ─────────────────────────────────────────────


class CirqQAOA:
    """QAOA for SC2 map routing using Cirq-style circuit."""

    def __init__(self, problem: RoutingProblem, layers: int = 2):
        self.problem = problem
        self.p = layers
        self.n = len(problem.nodes)

    def build_circuit(self, gammas: list[float], betas: list[float]) -> QuantumState:
        """Construct and run QAOA ansatz."""
        state = QuantumState(self.n)

        # Initial superposition
        for q in range(self.n):
            state.apply_h(q)

        for layer in range(self.p):
            # Cost unitary: ZZ interactions
            for i, j, w in self.problem.edges:
                state.apply_cnot(i, j)
                state.apply_rz(j, 2 * gammas[layer] * w)
                state.apply_cnot(i, j)

            # Mixer unitary: X rotations (via H·Rz·H)
            for q in range(self.n):
                state.apply_h(q)
                state.apply_rz(q, 2 * betas[layer])
                state.apply_h(q)

        return state

    def optimize(self, iterations: int = 100) -> dict:
        best_val = 0.0
        best_params = None
        best_cut = []

        for _ in range(iterations):
            gammas = [random.uniform(0, math.pi) for _ in range(self.p)]
            betas = [random.uniform(0, math.pi / 2) for _ in range(self.p)]

            state = self.build_circuit(gammas, betas)
            samples = state.measure(shots=20)

            for s in samples:
                assignment = [int(c) for c in s]
                val = self.problem.max_cut_value(assignment)
                if val > best_val:
                    best_val = val
                    best_params = (gammas, betas)
                    best_cut = assignment

        return {
            "best_cut_value": best_val,
            "assignment": dict(zip(self.problem.nodes, best_cut)),
            "params": best_params,
        }


# ─────────────────────────────────────────────
# Cirq-native implementation (when available)
# ─────────────────────────────────────────────


def build_cirq_circuit(problem: RoutingProblem):
    if not CIRQ_AVAILABLE:
        return None
    import cirq
    import sympy

    n = len(problem.nodes)
    qubits = cirq.LineQubit.range(n)
    gamma = sympy.Symbol("γ")
    beta = sympy.Symbol("β")

    circuit = cirq.Circuit()
    circuit.append(cirq.H.on_each(*qubits))

    # Cost layer
    for i, j, w in problem.edges:
        circuit.append(
            [
                cirq.CNOT(qubits[i], qubits[j]),
                cirq.rz(rads=2 * gamma * w)(qubits[j]),
                cirq.CNOT(qubits[i], qubits[j]),
            ]
        )

    # Mixer layer
    for q in qubits:
        circuit.append(cirq.rx(rads=2 * beta)(q))

    circuit.append(cirq.measure(*qubits, key="result"))
    return circuit


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 529: Cirq Quantum — SC2 Map Routing")
    print(f"Cirq available: {CIRQ_AVAILABLE}")

    problem = RoutingProblem(
        nodes=["main", "natural", "third", "watchtower", "enemy_main"],
        edges=[
            (0, 1, 2.0),  # main ↔ natural
            (1, 2, 1.5),  # natural ↔ third
            (2, 3, 1.0),  # third ↔ watchtower
            (3, 4, 2.5),  # watchtower ↔ enemy_main
            (0, 4, 1.0),  # main ↔ enemy (direct rush)
            (1, 4, 1.8),  # natural ↔ enemy (flank)
        ],
    )

    qaoa = CirqQAOA(problem, layers=2)
    result = qaoa.optimize(iterations=200)

    print(f"\nBest cut value: {result['best_cut_value']:.2f}")
    print("Map partition:")
    for node, side in result["assignment"].items():
        label = "ATTACK" if side else "DEFEND"
        print(f"  {node:12s} → {label}")

    if CIRQ_AVAILABLE:
        circ = build_cirq_circuit(problem)
        print(f"\nCirq circuit:\n{circ}")
