"""
Phase 528: Qiskit Quantum Computing
SC2 Bot strategy optimization using quantum algorithms (QAOA, VQE)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math
import random


# ─────────────────────────────────────────────
# Qiskit availability check
# ─────────────────────────────────────────────

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit import Parameter
    from qiskit_aer import AerSimulator
    from qiskit.primitives import Sampler, Estimator

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


# ─────────────────────────────────────────────
# Problem: SC2 Resource allocation as QUBO
# ─────────────────────────────────────────────


@dataclass
class SC2AllocationProblem:
    """
    Binary quadratic optimization: which units to build?
    x_i ∈ {0,1}: build unit type i (yes/no)
    Objective: maximize combat value subject to resource constraints
    """

    unit_types: list[str]
    mineral_cost: list[int]
    gas_cost: list[int]
    combat_value: list[float]
    max_minerals: int
    max_gas: int
    max_supply: int
    supply_cost: list[int]

    def qubo_matrix(self) -> list[list[float]]:
        """Build QUBO matrix Q for minimize x^T Q x."""
        n = len(self.unit_types)
        Q = [[0.0] * n for _ in range(n)]

        # Penalty for exceeding mineral budget
        penalty_min = 10.0
        penalty_gas = 10.0
        penalty_sup = 10.0

        for i in range(n):
            # Diagonal: maximize combat value (negative = maximize)
            Q[i][i] -= self.combat_value[i]
            # Self-penalty for resource use
            Q[i][i] += penalty_min * self.mineral_cost[i] ** 2 / self.max_minerals**2
            Q[i][i] += penalty_gas * self.gas_cost[i] ** 2 / max(1, self.max_gas) ** 2

        for i in range(n):
            for j in range(i + 1, n):
                # Cross-terms for resource constraint
                Q[i][j] += (
                    2
                    * penalty_min
                    * self.mineral_cost[i]
                    * self.mineral_cost[j]
                    / self.max_minerals**2
                )

        return Q

    def classical_greedy(self) -> list[int]:
        """Classical greedy baseline."""
        m = self.max_minerals
        g = self.max_gas
        s = self.max_supply
        chosen = [0] * len(self.unit_types)

        # Sort by combat value per mineral
        order = sorted(
            range(len(self.unit_types)),
            key=lambda i: self.combat_value[i] / max(1, self.mineral_cost[i]),
            reverse=True,
        )
        for i in order:
            if (
                m >= self.mineral_cost[i]
                and g >= self.gas_cost[i]
                and s >= self.supply_cost[i]
            ):
                chosen[i] = 1
                m -= self.mineral_cost[i]
                g -= self.gas_cost[i]
                s -= self.supply_cost[i]
        return chosen


# ─────────────────────────────────────────────
# QAOA simulator (pure Python approximation)
# ─────────────────────────────────────────────


class QAOASimulator:
    """
    Approximate QAOA using classical simulation.
    For real quantum hardware, use qiskit_aer.AerSimulator.
    """

    def __init__(self, problem: SC2AllocationProblem, layers: int = 3):
        self.problem = problem
        self.p = layers
        self.n_qubits = len(problem.unit_types)
        self.best_solution: Optional[list[int]] = None
        self.best_energy: float = float("inf")

    def _energy(self, bitstring: list[int]) -> float:
        Q = self.problem.qubo_matrix()
        n = len(bitstring)
        energy = 0.0
        for i in range(n):
            energy += Q[i][i] * bitstring[i]
            for j in range(i + 1, n):
                energy += 2 * Q[i][j] * bitstring[i] * bitstring[j]
        return energy

    def optimize(self, shots: int = 1000) -> list[int]:
        """
        Monte Carlo approximation of QAOA sampling.
        Real QAOA would use parameterized quantum circuits.
        """
        n = self.n_qubits
        self.best_solution = [0] * n
        self.best_energy = float("inf")

        for _ in range(shots):
            # Random bit flip perturbation
            candidate = [random.randint(0, 1) for _ in range(n)]
            energy = self._energy(candidate)
            if energy < self.best_energy:
                self.best_energy = energy
                self.best_solution = candidate[:]

        # Local search refinement
        improved = True
        while improved:
            improved = False
            for i in range(n):
                flipped = self.best_solution[:]
                flipped[i] ^= 1
                e = self._energy(flipped)
                if e < self.best_energy:
                    self.best_energy = e
                    self.best_solution = flipped
                    improved = True

        return self.best_solution


# ─────────────────────────────────────────────
# VQE-style variational optimizer
# ─────────────────────────────────────────────


class VariationalOptimizer:
    """Variational Quantum Eigensolver analog for continuous parameters."""

    def __init__(self, n_params: int = 8):
        self.params = [random.uniform(0, math.pi) for _ in range(n_params)]
        self.loss_history: list[float] = []

    def _mock_quantum_expectation(self, params: list[float]) -> float:
        """Simulate quantum circuit expectation value."""
        # Ising-like Hamiltonian: sum(cos(theta_i) * sigma_z^i)
        return sum(math.cos(p) for p in params) + 0.1 * random.gauss(0, 1)

    def gradient_descent_step(self, lr: float = 0.1) -> float:
        """Parameter shift rule gradient estimation."""
        gradients = []
        for i in range(len(self.params)):
            params_plus = self.params[:]
            params_minus = self.params[:]
            params_plus[i] += math.pi / 2
            params_minus[i] -= math.pi / 2
            grad = (
                self._mock_quantum_expectation(params_plus)
                - self._mock_quantum_expectation(params_minus)
            ) / 2.0
            gradients.append(grad)

        for i in range(len(self.params)):
            self.params[i] -= lr * gradients[i]

        loss = self._mock_quantum_expectation(self.params)
        self.loss_history.append(loss)
        return loss

    def optimize(self, steps: int = 100) -> float:
        for _ in range(steps):
            self.gradient_descent_step()
        return min(self.loss_history)


# ─────────────────────────────────────────────
# Qiskit circuit builder (when available)
# ─────────────────────────────────────────────


def build_qaoa_circuit(n_qubits: int, p_layers: int = 1):
    """Build QAOA ansatz circuit."""
    if not QISKIT_AVAILABLE:
        return None

    qc = QuantumCircuit(n_qubits)
    gamma = [Parameter(f"γ_{i}") for i in range(p_layers)]
    beta = [Parameter(f"β_{i}") for i in range(p_layers)]

    # Initial superposition
    qc.h(range(n_qubits))

    for layer in range(p_layers):
        # Cost unitary: Rzz gates
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)
            qc.rz(2 * gamma[layer], i + 1)
            qc.cx(i, i + 1)

        # Mixer unitary: Rx gates
        for i in range(n_qubits):
            qc.rx(2 * beta[layer], i)

    qc.measure_all()
    return qc


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 528: Qiskit Quantum — SC2 Strategy Optimization")
    print(f"Qiskit available: {QISKIT_AVAILABLE}")

    problem = SC2AllocationProblem(
        unit_types=["zergling", "roach", "hydralisk", "mutalisk", "ultralisk"],
        mineral_cost=[25, 75, 100, 100, 300],
        gas_cost=[0, 25, 50, 100, 200],
        combat_value=[8.9, 10.0, 15.6, 9.0, 59.6],
        max_minerals=400,
        max_gas=200,
        max_supply=20,
        supply_cost=[1, 2, 2, 2, 6],
    )

    # Classical baseline
    greedy = problem.classical_greedy()
    print(f"\nClassical greedy: {dict(zip(problem.unit_types, greedy))}")

    # QAOA approximation
    qaoa = QAOASimulator(problem, layers=3)
    quantum_result = qaoa.optimize(shots=500)
    print(f"QAOA result:      {dict(zip(problem.unit_types, quantum_result))}")
    print(f"Energy: {qaoa.best_energy:.3f}")

    # VQE optimization
    vqe = VariationalOptimizer(n_params=8)
    min_energy = vqe.optimize(steps=50)
    print(f"\nVQE min energy: {min_energy:.4f}")

    # Build circuit (if available)
    circuit = build_qaoa_circuit(5, p_layers=2)
    if circuit:
        print(f"\nQAOA circuit: {circuit.num_qubits} qubits, {circuit.depth()} depth")
    else:
        print("\nQAOA circuit: Qiskit not available (simulation only)")
