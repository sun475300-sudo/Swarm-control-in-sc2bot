"""
jax_rl/policy_gradient.py
JAX/Flax policy gradient agent for SC2 Zerg strategy selection.

State  : [army_supply, enemy_supply, minerals, gas, tech_level,
          base_count, worker_count, time_norm]  (8 dims)
Actions: [attack, defend, expand, tech, macro]  (5 actions)
"""

from __future__ import annotations

import jax
import jax.numpy as jnp
import flax.linen as nn
import optax
import numpy as np
from flax.training import train_state
from typing import Sequence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_DIM  = 8
NUM_ACTIONS = 5
ACTION_NAMES = ["attack", "defend", "expand", "tech", "macro"]
HIDDEN_SIZES: Sequence[int] = (64, 32)


# ---------------------------------------------------------------------------
# Policy network (2 hidden layers → softmax output)
# ---------------------------------------------------------------------------
class ZergPolicyNet(nn.Module):
    hidden_sizes: Sequence[int] = HIDDEN_SIZES
    num_actions: int = NUM_ACTIONS

    @nn.compact
    def __call__(self, x: jnp.ndarray) -> jnp.ndarray:
        for h in self.hidden_sizes:
            x = nn.Dense(h)(x)
            x = nn.relu(x)
        logits = nn.Dense(self.num_actions)(x)
        return logits   # raw logits; apply softmax externally when needed


# ---------------------------------------------------------------------------
# TrainState factory
# ---------------------------------------------------------------------------
def create_train_state(rng: jax.random.KeyArray, lr: float = 1e-3) -> train_state.TrainState:
    model = ZergPolicyNet()
    dummy_input = jnp.ones((1, STATE_DIM))
    params = model.init(rng, dummy_input)["params"]
    tx = optax.adam(lr)
    return train_state.TrainState.create(apply_fn=model.apply, params=params, tx=tx)


# ---------------------------------------------------------------------------
# JIT-compiled forward pass
# ---------------------------------------------------------------------------
@jax.jit
def forward(params: dict, state: jnp.ndarray) -> jnp.ndarray:
    """Return action probabilities for a batch of SC2 states."""
    logits = ZergPolicyNet().apply({"params": params}, state)
    return jax.nn.softmax(logits, axis=-1)


# ---------------------------------------------------------------------------
# Policy gradient loss (REINFORCE)
# ---------------------------------------------------------------------------
@jax.jit
def pg_loss(params: dict, states: jnp.ndarray, actions: jnp.ndarray, returns: jnp.ndarray) -> jnp.ndarray:
    logits = ZergPolicyNet().apply({"params": params}, states)
    log_probs = jax.nn.log_softmax(logits, axis=-1)
    chosen_log_probs = log_probs[jnp.arange(len(actions)), actions]
    # Normalise returns for stability
    returns_norm = (returns - returns.mean()) / (returns.std() + 1e-8)
    loss = -jnp.mean(chosen_log_probs * returns_norm)
    return loss


# ---------------------------------------------------------------------------
# Single gradient update step
# ---------------------------------------------------------------------------
@jax.jit
def update_step(
    state: train_state.TrainState,
    states: jnp.ndarray,
    actions: jnp.ndarray,
    returns: jnp.ndarray,
) -> tuple[train_state.TrainState, jnp.ndarray]:
    loss, grads = jax.value_and_grad(pg_loss)(state.params, states, actions, returns)
    state = state.apply_gradients(grads=grads)
    return state, loss


# ---------------------------------------------------------------------------
# Dummy SC2 episode generator
# ---------------------------------------------------------------------------
def generate_episode(rng: np.random.Generator, episode_len: int = 20) -> dict:
    """
    Simulate a short SC2 strategy episode with random game states.
    Returns states, actions sampled from a random policy, and discounted returns.
    """
    states  = rng.random((episode_len, STATE_DIM)).astype(np.float32)
    # Inject some structure: tech_level rounds up, time increases
    states[:, 4] = np.clip(np.round(states[:, 4] * 3 + 1), 1, 3)
    states[:, 7] = np.linspace(0.0, 1.0, episode_len)

    actions  = rng.integers(0, NUM_ACTIONS, size=episode_len)
    # Sparse reward: +1 at end if we "won", scattered small rewards
    rewards  = rng.uniform(-0.1, 0.1, size=episode_len)
    rewards[-1] += float(rng.random() > 0.4)   # 60% win probability for demo

    # Compute discounted returns
    gamma = 0.99
    returns = np.zeros(episode_len, dtype=np.float32)
    G = 0.0
    for t in reversed(range(episode_len)):
        G = rewards[t] + gamma * G
        returns[t] = G

    return {
        "states":  jnp.array(states),
        "actions": jnp.array(actions),
        "returns": jnp.array(returns),
    }


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(num_episodes: int = 200, lr: float = 1e-3, seed: int = 42) -> train_state.TrainState:
    rng_jax = jax.random.PRNGKey(seed)
    rng_np  = np.random.default_rng(seed)

    ts = create_train_state(rng_jax, lr)

    print("[PolicyGradient] Starting training …")
    print(f"  State dim={STATE_DIM}  |  Actions={ACTION_NAMES}")
    print(f"  Episodes={num_episodes}  |  LR={lr}\n")

    total_loss = 0.0
    for ep in range(1, num_episodes + 1):
        episode = generate_episode(rng_np)
        ts, loss = update_step(ts, episode["states"], episode["actions"], episode["returns"])
        total_loss += float(loss)

        if ep % 50 == 0:
            avg_loss = total_loss / 50
            total_loss = 0.0
            # Sample greedy action for a typical early-game state
            sample_state = jnp.array([[30, 20, 600, 200, 1, 2, 16, 0.2]])
            probs = forward(ts.params, sample_state)[0]
            best_action = ACTION_NAMES[int(jnp.argmax(probs))]
            print(f"  Episode {ep:4d}  avg_loss={avg_loss:.4f}  "
                  f"greedy_action={best_action}  "
                  f"probs={np.array(probs).round(3).tolist()}")

    print("\n[PolicyGradient] Training complete.")
    return ts


# ---------------------------------------------------------------------------
# Inference helper
# ---------------------------------------------------------------------------
def select_action(ts: train_state.TrainState, game_state: list[float]) -> str:
    """Return the greedy strategy action for a given SC2 game state."""
    x = jnp.array([game_state], dtype=jnp.float32)
    probs = forward(ts.params, x)[0]
    idx = int(jnp.argmax(probs))
    return ACTION_NAMES[idx]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    trained_state = train(num_episodes=200)

    print("\n--- Strategy Selection Examples ---")
    examples = [
        ([10, 5,  800, 200, 1, 1, 16, 0.1], "early pool aggression"),
        ([40, 40, 400, 100, 2, 2, 30, 0.4], "mid-game even fight"),
        ([70, 30, 2000, 900, 3, 4, 60, 0.9], "late game winning"),
        ([30, 70,  200,  50, 1, 1, 14, 0.2], "under pressure"),
    ]
    for state_vec, description in examples:
        action = select_action(trained_state, state_vec)
        print(f"  [{description}]  →  {action}")
