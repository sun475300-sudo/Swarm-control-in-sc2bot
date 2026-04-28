"""
Phase 537: JAX + Flax RL
SC2 Bot policy network with JAX JIT, Flax, Optax
"""

from __future__ import annotations

import math
import os
import random
import sys
from typing import Any, Callable, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gymnasium_env.sc2_gym_env import ACT_DIM, OBS_DIM, SC2ZergEnv

try:
    import flax.linen as nn
    import jax
    import jax.numpy as jnp
    import optax
    from flax.training import train_state
    from jax import grad, jit, value_and_grad, vmap

    JAX_AVAILABLE = True
except ImportError:
    JAX_AVAILABLE = False


# ─────────────────────────────────────────────
# Flax policy network
# ─────────────────────────────────────────────

if JAX_AVAILABLE:

    class SC2PolicyNet(nn.Module):
        hidden_dim: int = 256
        n_actions: int = ACT_DIM

        @nn.compact
        def __call__(self, x: jnp.ndarray) -> Tuple[jnp.ndarray, jnp.ndarray]:
            # Shared trunk
            h = nn.Dense(self.hidden_dim)(x)
            h = nn.relu(h)
            h = nn.Dense(self.hidden_dim)(h)
            h = nn.relu(h)

            # Actor head (policy logits)
            logits = nn.Dense(self.n_actions)(h)

            # Critic head (value)
            value = nn.Dense(1)(h)

            return logits, value.squeeze(-1)

    class SC2ValueNet(nn.Module):
        hidden_dim: int = 256

        @nn.compact
        def __call__(self, x: jnp.ndarray) -> jnp.ndarray:
            h = nn.Dense(self.hidden_dim)(x)
            h = nn.relu(h)
            h = nn.Dense(self.hidden_dim)(h)
            h = nn.relu(h)
            return nn.Dense(1)(h).squeeze(-1)


# ─────────────────────────────────────────────
# JAX training utilities
# ─────────────────────────────────────────────

if JAX_AVAILABLE:

    def create_train_state(model, rng, obs_dim: int, lr: float = 3e-4):
        """Initialize Flax TrainState."""
        params = model.init(rng, jnp.ones((1, obs_dim)))
        tx = optax.chain(
            optax.clip_by_global_norm(0.5),
            optax.adam(lr),
        )
        return train_state.TrainState.create(
            apply_fn=model.apply,
            params=params,
            tx=tx,
        )

    @jit
    def select_action_jax(state, obs):
        logits, value = state.apply_fn(state.params, obs)
        return logits, value

    @jit
    def compute_loss(params, apply_fn, batch):
        obs, actions, returns, advantages = (
            batch["obs"],
            batch["actions"],
            batch["returns"],
            batch["advantages"],
        )
        logits, values = apply_fn(params, obs)

        # Policy loss (REINFORCE / simplified PPO)
        log_probs = jax.nn.log_softmax(logits)
        log_prob_actions = log_probs[jnp.arange(len(actions)), actions]
        policy_loss = -(log_prob_actions * advantages).mean()

        # Value loss
        value_loss = 0.5 * ((values - returns) ** 2).mean()

        # Entropy bonus
        probs = jax.nn.softmax(logits)
        entropy = -(probs * log_probs).sum(axis=-1).mean()

        total = policy_loss + 0.5 * value_loss - 0.01 * entropy
        return total, {"policy": policy_loss, "value": value_loss, "entropy": entropy}

    @jit
    def train_step(state, batch):
        grad_fn = value_and_grad(compute_loss, has_aux=True)
        (loss, metrics), grads = grad_fn(state.params, state.apply_fn, batch)
        new_state = state.apply_gradients(grads=grads)
        return new_state, loss, metrics


# ─────────────────────────────────────────────
# Training loop (JAX)
# ─────────────────────────────────────────────


def train_jax_agent(total_steps: int = 20_000) -> dict:
    if not JAX_AVAILABLE:
        return _python_fallback(total_steps)

    rng = jax.random.PRNGKey(42)
    rng, init_rng = jax.random.split(rng)

    model = SC2PolicyNet(hidden_dim=256, n_actions=ACT_DIM)
    state = create_train_state(model, init_rng, OBS_DIM)

    env = SC2ZergEnv(max_frames=500)
    all_rewards = []
    episodes = 0

    steps = 0
    while steps < total_steps:
        obs_list, act_list, rew_list = [], [], []
        obs, _ = env.reset(seed=episodes)
        done = False
        ep_r = 0.0

        while not done and len(obs_list) < 128:
            obs_arr = jnp.array([obs])
            logits, value = select_action_jax(state, obs_arr)
            probs = jax.nn.softmax(logits[0])
            rng, action_rng = jax.random.split(rng)
            action = int(jax.random.categorical(action_rng, logits[0]))

            next_obs, reward, term, trunc, _ = env.step(action)
            obs_list.append(obs)
            act_list.append(action)
            rew_list.append(reward)
            ep_r += reward
            steps += 1
            done = term or trunc
            obs = next_obs

        # Compute returns (simple Monte Carlo)
        returns = []
        r = 0.0
        for rw in reversed(rew_list):
            r = rw + 0.99 * r
            returns.insert(0, r)

        obs_arr = jnp.array(obs_list)
        act_arr = jnp.array(act_list)
        ret_arr = jnp.array(returns)

        # Advantage = returns - baseline (mean)
        adv_arr = ret_arr - ret_arr.mean()

        batch = {
            "obs": obs_arr,
            "actions": act_arr,
            "returns": ret_arr,
            "advantages": adv_arr,
        }

        state, loss, metrics = train_step(state, batch)
        all_rewards.append(ep_r)
        episodes += 1

        if episodes % 20 == 0:
            avg = sum(all_rewards[-20:]) / min(20, len(all_rewards))
            print(
                f"  Ep {episodes:4d} | Steps: {steps:6d} | "
                f"Avg reward: {avg:.2f} | Loss: {float(loss):.4f}"
            )

    return {
        "total_steps": steps,
        "episodes": episodes,
        "mean_reward": sum(all_rewards) / max(1, len(all_rewards)),
    }


def _python_fallback(total_steps: int) -> dict:
    """Numpy-based policy gradient without JAX."""
    import math

    # Simple softmax policy with weight table
    W = [[random.gauss(0, 0.1) for _ in range(ACT_DIM)] for _ in range(OBS_DIM)]

    def forward(obs):
        scores = [sum(W[j][a] * obs[j] for j in range(OBS_DIM)) for a in range(ACT_DIM)]
        max_s = max(scores)
        exp_s = [math.exp(s - max_s) for s in scores]
        total = sum(exp_s)
        return [e / total for e in exp_s]

    def select_action(obs):
        probs = forward(obs)
        r = random.random()
        cum = 0.0
        for i, p in enumerate(probs):
            cum += p
            if r <= cum:
                return i
        return ACT_DIM - 1

    env = SC2ZergEnv(max_frames=500)
    steps = 0
    episodes = 0
    total_r = 0.0

    while steps < total_steps:
        obs, _ = env.reset(seed=episodes)
        done = False
        ep_r = 0.0
        while not done:
            action = select_action(obs)
            obs, r, term, trunc, _ = env.step(action)
            ep_r += r
            steps += 1
            done = term or trunc
        total_r += ep_r
        episodes += 1

    return {
        "total_steps": steps,
        "episodes": episodes,
        "mean_reward": total_r / max(1, episodes),
    }


if __name__ == "__main__":
    print("Phase 537: JAX + Flax — SC2 Policy Network")
    print(f"JAX available: {JAX_AVAILABLE}")
    result = train_jax_agent(total_steps=5000)
    print(f"\nResult: {result}")
