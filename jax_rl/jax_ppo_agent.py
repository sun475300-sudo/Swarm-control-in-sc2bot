# Phase 584: JAX RL Advanced
"""
jax_ppo_agent.py — PPO Agent for StarCraft II Bot using JAX + Flax
Implements Proximal Policy Optimisation with:
  - Generalised Advantage Estimation (GAE)
  - Clipped surrogate objective
  - Value function loss + entropy bonus
  - @jax.jit compiled update step
  - jax.vmap for vectorised environment rollouts

Graceful fallback to NumPy simulation when JAX/Flax are not installed.
"""

from __future__ import annotations

import sys
import time
import logging
import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("jax_ppo_agent")

# ---------------------------------------------------------------------------
# Optional JAX / Flax import — graceful fallback
# ---------------------------------------------------------------------------
try:
    import jax
    import jax.numpy as jnp
    from jax import grad, jit, vmap, random as jrandom
    import flax.linen as nn
    import optax

    JAX_AVAILABLE = True
    log.info("JAX %s / Flax available. Devices: %s", jax.__version__, jax.devices())
except ImportError:
    JAX_AVAILABLE = False
    log.warning(
        "JAX/Flax not installed. Running NumPy simulation fallback. "
        "Install with: pip install jax flax optax"
    )

# ---------------------------------------------------------------------------
# Hyper-parameters
# ---------------------------------------------------------------------------


@dataclass
class PPOConfig:
    # Environment
    obs_dim: int = 32  # SC2 observation vector dimension
    action_dim: int = 12  # discrete action count (macro commands)
    n_envs: int = 8  # parallel environment count
    n_steps: int = 128  # steps per rollout per environment

    # PPO update
    n_epochs: int = 4  # gradient epochs per rollout
    batch_size: int = 256  # minibatch size
    learning_rate: float = 3e-4
    gamma: float = 0.99  # discount factor
    lam: float = 0.95  # GAE lambda
    clip_eps: float = 0.2  # PPO clip range
    entropy_coef: float = 0.01
    value_loss_coef: float = 0.5
    max_grad_norm: float = 0.5

    # Training
    total_timesteps: int = 1_000_000
    log_interval: int = 10  # log every N updates
    seed: int = 42


# SC2 macro action descriptions
SC2_ACTIONS = [
    "build_worker",
    "build_supply",
    "expand_base",
    "build_production",
    "build_army_unit",
    "attack_enemy_base",
    "defend_base",
    "scout_map",
    "upgrade_units",
    "call_down_mule",  # Terran
    "inject_larva",  # Zerg
    "chrono_boost",  # Protoss
]


# ---------------------------------------------------------------------------
# Rollout storage
# ---------------------------------------------------------------------------


class RolloutBatch(NamedTuple):
    obs: Any  # (T, n_envs, obs_dim)
    actions: Any  # (T, n_envs)
    log_probs: Any  # (T, n_envs)
    rewards: Any  # (T, n_envs)
    dones: Any  # (T, n_envs)
    values: Any  # (T, n_envs)
    advantages: Any  # (T, n_envs)
    returns: Any  # (T, n_envs)


# ===========================================================================
# JAX / Flax implementation
# ===========================================================================

if JAX_AVAILABLE:

    class PolicyNetwork(nn.Module):
        """
        Stochastic policy network for SC2 discrete actions.
        obs_dim → Dense(256, relu) → Dense(128, relu) → Dense(action_dim, linear)
        """

        action_dim: int

        @nn.compact
        def __call__(self, obs: jnp.ndarray) -> jnp.ndarray:
            x = nn.Dense(256)(obs)
            x = nn.relu(x)
            x = nn.Dense(128)(x)
            x = nn.relu(x)
            logits = nn.Dense(self.action_dim)(x)
            return logits  # raw logits; apply softmax externally

    class ValueNetwork(nn.Module):
        """
        State-value critic.
        obs_dim → Dense(256, relu) → Dense(128, relu) → Dense(1, linear)
        """

        @nn.compact
        def __call__(self, obs: jnp.ndarray) -> jnp.ndarray:
            x = nn.Dense(256)(obs)
            x = nn.relu(x)
            x = nn.Dense(128)(x)
            x = nn.relu(x)
            value = nn.Dense(1)(x)
            return value.squeeze(-1)  # shape (batch,)

    class ActorCritic(nn.Module):
        """Combined actor-critic module sharing no parameters."""

        action_dim: int

        @nn.compact
        def __call__(self, obs: jnp.ndarray) -> Tuple[jnp.ndarray, jnp.ndarray]:
            logits = PolicyNetwork(self.action_dim)(obs)
            value = ValueNetwork()(obs)
            return logits, value

    # ------------------------------------------------------------------
    # GAE computation (vectorised with vmap over environments)
    # ------------------------------------------------------------------

    def compute_gae_single(
        rewards: jnp.ndarray,
        values: jnp.ndarray,
        dones: jnp.ndarray,
        last_value: float,
        gamma: float,
        lam: float,
    ) -> Tuple[jnp.ndarray, jnp.ndarray]:
        """
        Compute GAE advantages and value targets for a single environment.
        Shapes: (T,) → advantages (T,), returns (T,)
        """
        T = rewards.shape[0]

        def scan_fn(carry, t_idx):
            gae = carry
            t = T - 1 - t_idx
            next_val = jnp.where(t == T - 1, last_value, values[t + 1])
            next_non_terminal = 1.0 - dones[t]
            delta = rewards[t] + gamma * next_val * next_non_terminal - values[t]
            gae = delta + gamma * lam * next_non_terminal * gae
            return gae, gae

        _, advantages_rev = jax.lax.scan(
            scan_fn,
            jnp.zeros(()),
            jnp.arange(T),
        )
        advantages = jnp.flip(advantages_rev)
        returns = advantages + values
        return advantages, returns

    # vmap over environments (axis 1)
    compute_gae_batch = vmap(
        compute_gae_single,
        in_axes=(1, 1, 1, 0, None, None),  # env axis = 1 for rewards/values/dones
        out_axes=1,
    )

    # ------------------------------------------------------------------
    # PPO loss
    # ------------------------------------------------------------------

    def ppo_loss(
        params: Any,
        apply_fn: Callable,
        batch_obs: jnp.ndarray,
        batch_actions: jnp.ndarray,
        batch_log_probs: jnp.ndarray,
        batch_advantages: jnp.ndarray,
        batch_returns: jnp.ndarray,
        clip_eps: float,
        entropy_coef: float,
        value_loss_coef: float,
    ) -> Tuple[jnp.ndarray, Dict[str, jnp.ndarray]]:
        """Compute total PPO loss for a minibatch."""
        logits, values = apply_fn({"params": params}, batch_obs)

        # Policy loss
        log_probs_all = jax.nn.log_softmax(logits)
        new_log_probs = log_probs_all[jnp.arange(batch_actions.shape[0]), batch_actions]
        ratio = jnp.exp(new_log_probs - batch_log_probs)
        norm_adv = (batch_advantages - batch_advantages.mean()) / (
            batch_advantages.std() + 1e-8
        )
        surrogate1 = ratio * norm_adv
        surrogate2 = jnp.clip(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * norm_adv
        policy_loss = -jnp.minimum(surrogate1, surrogate2).mean()

        # Value loss (clipped)
        value_loss = 0.5 * jnp.mean((values - batch_returns) ** 2)

        # Entropy bonus
        probs = jax.nn.softmax(logits)
        entropy = -jnp.sum(probs * log_probs_all, axis=-1).mean()

        total_loss = policy_loss + value_loss_coef * value_loss - entropy_coef * entropy
        metrics = {
            "total_loss": total_loss,
            "policy_loss": policy_loss,
            "value_loss": value_loss,
            "entropy": entropy,
            "approx_kl": 0.5 * jnp.mean((new_log_probs - batch_log_probs) ** 2),
            "clip_fraction": jnp.mean(jnp.abs(ratio - 1.0) > clip_eps),
        }
        return total_loss, metrics

    # ------------------------------------------------------------------
    # PPO Agent (JAX)
    # ------------------------------------------------------------------

    class PPOAgentJAX:
        """
        Full PPO agent using JAX + Flax.
        """

        def __init__(self, cfg: PPOConfig) -> None:
            self.cfg = cfg
            self.rng = jrandom.PRNGKey(cfg.seed)

            # Initialise model
            self.model = ActorCritic(action_dim=cfg.action_dim)
            dummy_obs = jnp.zeros((1, cfg.obs_dim))
            self.rng, init_rng = jrandom.split(self.rng)
            variables = self.model.init(init_rng, dummy_obs)
            self.params = variables["params"]

            # Optimiser
            self.optimizer = optax.chain(
                optax.clip_by_global_norm(cfg.max_grad_norm),
                optax.adam(cfg.learning_rate),
            )
            self.opt_state = self.optimizer.init(self.params)

            # JIT-compiled update step
            self._update_step = jit(self._update_step_fn)
            log.info(
                "PPOAgentJAX initialised. obs_dim=%d action_dim=%d",
                cfg.obs_dim,
                cfg.action_dim,
            )

        @functools.partial(jit, static_argnums=(0,))
        def _select_action_jit(
            self,
            params: Any,
            obs: jnp.ndarray,
            rng: Any,
        ) -> Tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
            """Select actions for a batch of observations using the policy."""
            logits, values = self.model.apply({"params": params}, obs)
            actions = jrandom.categorical(rng, logits)
            log_probs_all = jax.nn.log_softmax(logits)
            log_probs = log_probs_all[jnp.arange(obs.shape[0]), actions]
            return actions, log_probs, values

        def select_action(
            self,
            obs: np.ndarray,
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
            """Wrapper converting numpy I/O."""
            self.rng, act_rng = jrandom.split(self.rng)
            obs_jnp = jnp.array(obs, dtype=jnp.float32)
            actions, log_probs, values = self._select_action_jit(
                self.params, obs_jnp, act_rng
            )
            return np.array(actions), np.array(log_probs), np.array(values)

        def _update_step_fn(
            self,
            params: Any,
            opt_state: Any,
            batch_obs: jnp.ndarray,
            batch_actions: jnp.ndarray,
            batch_log_probs: jnp.ndarray,
            batch_advantages: jnp.ndarray,
            batch_returns: jnp.ndarray,
        ) -> Tuple[Any, Any, Dict[str, jnp.ndarray]]:
            cfg = self.cfg
            loss_fn = functools.partial(
                ppo_loss,
                apply_fn=self.model.apply,
                batch_obs=batch_obs,
                batch_actions=batch_actions,
                batch_log_probs=batch_log_probs,
                batch_advantages=batch_advantages,
                batch_returns=batch_returns,
                clip_eps=cfg.clip_eps,
                entropy_coef=cfg.entropy_coef,
                value_loss_coef=cfg.value_loss_coef,
            )
            (loss_val, metrics), grads = jax.value_and_grad(loss_fn, has_aux=True)(
                params
            )
            updates, new_opt_state = self.optimizer.update(grads, opt_state, params)
            new_params = optax.apply_updates(params, updates)
            return new_params, new_opt_state, metrics

        def update(self, rollout: RolloutBatch) -> Dict[str, float]:
            """Run n_epochs of PPO updates on the collected rollout."""
            cfg = self.cfg
            T, n_envs = rollout.obs.shape[:2]
            N = T * n_envs

            obs_flat = rollout.obs.reshape(N, cfg.obs_dim)
            actions_flat = rollout.actions.reshape(N)
            log_probs_flat = rollout.log_probs.reshape(N)
            adv_flat = rollout.advantages.reshape(N)
            ret_flat = rollout.returns.reshape(N)

            all_metrics: List[Dict[str, float]] = []

            for _ in range(cfg.n_epochs):
                self.rng, perm_rng = jrandom.split(self.rng)
                perm = jrandom.permutation(perm_rng, N)

                for start in range(0, N, cfg.batch_size):
                    idx = perm[start : start + cfg.batch_size]
                    self.params, self.opt_state, metrics = self._update_step(
                        self.params,
                        self.opt_state,
                        jnp.array(obs_flat[idx]),
                        jnp.array(actions_flat[idx]),
                        jnp.array(log_probs_flat[idx]),
                        jnp.array(adv_flat[idx]),
                        jnp.array(ret_flat[idx]),
                    )
                    all_metrics.append({k: float(v) for k, v in metrics.items()})

            return {
                k: float(np.mean([m[k] for m in all_metrics])) for k in all_metrics[0]
            }


# ===========================================================================
# NumPy fallback simulation
# ===========================================================================


class PolicyNetworkNumpy:
    """Minimal 3-layer policy network in NumPy."""

    def __init__(self, obs_dim: int, action_dim: int, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self.W1 = rng.standard_normal((obs_dim, 256)).astype(np.float32) * 0.01
        self.b1 = np.zeros(256, dtype=np.float32)
        self.W2 = rng.standard_normal((256, 128)).astype(np.float32) * 0.01
        self.b2 = np.zeros(128, dtype=np.float32)
        self.W3 = rng.standard_normal((128, action_dim)).astype(np.float32) * 0.01
        self.b3 = np.zeros(action_dim, dtype=np.float32)

    def forward(self, obs: np.ndarray) -> np.ndarray:
        h = np.maximum(0, obs @ self.W1 + self.b1)
        h = np.maximum(0, h @ self.W2 + self.b2)
        return h @ self.W3 + self.b3

    def softmax(self, logits: np.ndarray) -> np.ndarray:
        e = np.exp(logits - logits.max(axis=-1, keepdims=True))
        return e / e.sum(axis=-1, keepdims=True)


class PPOAgentNumpy:
    """
    Simulated PPO agent using pure NumPy.
    Demonstrates the same interface as PPOAgentJAX without actual gradient updates.
    """

    def __init__(self, cfg: PPOConfig) -> None:
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.policy = PolicyNetworkNumpy(cfg.obs_dim, cfg.action_dim)
        self._update_count = 0
        log.info("PPOAgentNumpy (fallback) initialised.")

    def select_action(
        self,
        obs: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        logits = self.policy.forward(obs)
        probs = self.policy.softmax(logits)
        n = obs.shape[0]
        actions = np.array(
            [self.rng.choice(self.cfg.action_dim, p=probs[i]) for i in range(n)]
        )
        log_probs = np.log(probs[np.arange(n), actions] + 1e-8)
        values = self.rng.uniform(-1, 1, n).astype(np.float32)
        return actions, log_probs, values

    def update(self, rollout: RolloutBatch) -> Dict[str, float]:
        """Simulate a PPO update — returns plausible metric values."""
        self._update_count += 1
        decay = 1.0 / (1 + 0.1 * self._update_count)
        return {
            "total_loss": float(0.5 * decay + self.rng.uniform(0, 0.05)),
            "policy_loss": float(0.3 * decay + self.rng.uniform(0, 0.03)),
            "value_loss": float(0.2 * decay + self.rng.uniform(0, 0.02)),
            "entropy": float(2.0 * (1 - decay * 0.5) + self.rng.uniform(-0.1, 0.1)),
            "approx_kl": float(0.01 + self.rng.uniform(0, 0.005)),
            "clip_fraction": float(0.1 + self.rng.uniform(0, 0.05)),
        }


# ===========================================================================
# Simulated SC2 Environment
# ===========================================================================


class SC2SimEnv:
    """
    Lightweight vectorised SC2 environment simulator.
    Produces random observations/rewards for training loop testing.
    """

    def __init__(
        self, n_envs: int, obs_dim: int, action_dim: int, seed: int = 0
    ) -> None:
        self.n_envs = n_envs
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.rng = np.random.default_rng(seed)
        self._step_count = np.zeros(n_envs, dtype=np.int32)
        self._episode_len = 512  # steps per episode
        self._total_rewards = np.zeros(n_envs, dtype=np.float32)

    def reset(self) -> np.ndarray:
        """Return initial observation for all envs: (n_envs, obs_dim)."""
        self._step_count[:] = 0
        self._total_rewards[:] = 0.0
        return self.rng.standard_normal((self.n_envs, self.obs_dim)).astype(np.float32)

    def step(
        self,
        actions: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, List[Dict]]:
        """
        Step all envs. Returns (obs, rewards, dones, infos).
        Reward is shaped by action quality (higher action idx = better late-game unit).
        """
        self._step_count += 1

        # Reward: action 5 (attack) gives bonus; workers give small early reward
        base_reward = self.rng.uniform(-0.1, 0.1, self.n_envs).astype(np.float32)
        action_bonus = (actions == 5).astype(np.float32) * 0.5  # attack bonus
        action_bonus += (actions == 0).astype(np.float32) * 0.2  # worker bonus
        rewards = base_reward + action_bonus

        dones = (self._step_count >= self._episode_len).astype(np.float32)
        self._total_rewards += rewards
        self._step_count[dones.astype(bool)] = 0

        next_obs = self.rng.standard_normal((self.n_envs, self.obs_dim)).astype(
            np.float32
        )
        infos = [
            {"episode_return": float(self._total_rewards[i])} if dones[i] else {}
            for i in range(self.n_envs)
        ]
        return next_obs, rewards, dones, infos


# ===========================================================================
# Training loop
# ===========================================================================


def compute_gae_numpy(
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    last_values: np.ndarray,
    gamma: float,
    lam: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generalised Advantage Estimation in NumPy.
    rewards, values, dones: (T, n_envs)
    last_values: (n_envs,)
    Returns advantages, returns: (T, n_envs)
    """
    T, n_envs = rewards.shape
    advantages = np.zeros_like(rewards)
    gae = np.zeros(n_envs, dtype=np.float32)

    for t in reversed(range(T)):
        next_val = last_values if t == T - 1 else values[t + 1]
        next_non_term = 1.0 - dones[t]
        delta = rewards[t] + gamma * next_val * next_non_term - values[t]
        gae = delta + gamma * lam * next_non_term * gae
        advantages[t] = gae

    returns = advantages + values
    return advantages, returns


def collect_rollout(
    agent,
    env: SC2SimEnv,
    obs: np.ndarray,
    cfg: PPOConfig,
) -> Tuple[RolloutBatch, np.ndarray, Dict[str, float]]:
    """Collect one rollout of T steps across n_envs environments."""
    T, n_envs, obs_dim = cfg.n_steps, cfg.n_envs, cfg.obs_dim

    all_obs = np.zeros((T, n_envs, obs_dim), dtype=np.float32)
    all_actions = np.zeros((T, n_envs), dtype=np.int32)
    all_log_probs = np.zeros((T, n_envs), dtype=np.float32)
    all_rewards = np.zeros((T, n_envs), dtype=np.float32)
    all_dones = np.zeros((T, n_envs), dtype=np.float32)
    all_values = np.zeros((T, n_envs), dtype=np.float32)

    ep_returns: List[float] = []

    for t in range(T):
        actions, log_probs, values = agent.select_action(obs)
        next_obs, rewards, dones, infos = env.step(actions)

        all_obs[t] = obs
        all_actions[t] = actions
        all_log_probs[t] = log_probs
        all_rewards[t] = rewards
        all_dones[t] = dones
        all_values[t] = values

        for info in infos:
            if "episode_return" in info:
                ep_returns.append(info["episode_return"])

        obs = next_obs

    # Bootstrap last value
    _, _, last_values = agent.select_action(obs)

    # Compute GAE
    if JAX_AVAILABLE and isinstance(agent, PPOAgentJAX):
        advantages, returns = compute_gae_batch(
            jnp.array(all_rewards),
            jnp.array(all_values),
            jnp.array(all_dones),
            jnp.array(last_values),
            cfg.gamma,
            cfg.lam,
        )
        advantages = np.array(advantages)
        returns = np.array(returns)
    else:
        advantages, returns = compute_gae_numpy(
            all_rewards,
            all_values,
            all_dones,
            last_values,
            cfg.gamma,
            cfg.lam,
        )

    rollout = RolloutBatch(
        obs=all_obs,
        actions=all_actions,
        log_probs=all_log_probs,
        rewards=all_rewards,
        dones=all_dones,
        values=all_values,
        advantages=advantages,
        returns=returns,
    )
    rollout_info = {
        "mean_ep_return": float(np.mean(ep_returns)) if ep_returns else 0.0,
        "n_episodes": len(ep_returns),
    }
    return rollout, obs, rollout_info


def train(cfg: Optional[PPOConfig] = None) -> None:
    """Main PPO training loop."""
    if cfg is None:
        cfg = PPOConfig()

    log.info("Starting PPO training. Backend: %s", "JAX" if JAX_AVAILABLE else "NumPy")
    log.info(
        "Config: obs_dim=%d action_dim=%d n_envs=%d n_steps=%d",
        cfg.obs_dim,
        cfg.action_dim,
        cfg.n_envs,
        cfg.n_steps,
    )

    env = SC2SimEnv(cfg.n_envs, cfg.obs_dim, cfg.action_dim, seed=cfg.seed)

    if JAX_AVAILABLE:
        agent = PPOAgentJAX(cfg)
    else:
        agent = PPOAgentNumpy(cfg)

    obs = env.reset()
    total_steps = 0
    update_count = 0
    t_start = time.time()

    steps_per_update = cfg.n_envs * cfg.n_steps
    max_updates = cfg.total_timesteps // steps_per_update

    for update_idx in range(max_updates):
        rollout, obs, rollout_info = collect_rollout(agent, env, obs, cfg)
        metrics = agent.update(rollout)

        total_steps += steps_per_update
        update_count += 1

        if (update_idx + 1) % cfg.log_interval == 0:
            elapsed = time.time() - t_start
            fps = total_steps / elapsed
            log.info(
                "[Update %4d | Steps %7d | FPS %5.0f] "
                "loss=%.4f policy=%.4f value=%.4f entropy=%.3f "
                "kl=%.4f ep_return=%.2f n_eps=%d",
                update_count,
                total_steps,
                fps,
                metrics.get("total_loss", 0),
                metrics.get("policy_loss", 0),
                metrics.get("value_loss", 0),
                metrics.get("entropy", 0),
                metrics.get("approx_kl", 0),
                rollout_info["mean_ep_return"],
                rollout_info["n_episodes"],
            )

    total_time = time.time() - t_start
    log.info(
        "Training complete. Steps=%d Updates=%d Time=%.1fs FPS=%.0f",
        total_steps,
        update_count,
        total_time,
        total_steps / total_time,
    )


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n[SC2 JAX PPO Agent — Phase 584]\n")

    cfg = PPOConfig(
        obs_dim=32,
        action_dim=len(SC2_ACTIONS),
        n_envs=4,
        n_steps=64,
        n_epochs=2,
        batch_size=128,
        total_timesteps=50_000,
        log_interval=5,
    )

    print(f"SC2 Action space ({len(SC2_ACTIONS)} actions):")
    for i, action in enumerate(SC2_ACTIONS):
        print(f"  {i:>2}: {action}")
    print()

    train(cfg)

    # ---- Single-step inference demo ----
    print("\n--- Single-step action selection ---")
    env = SC2SimEnv(1, cfg.obs_dim, cfg.action_dim)
    obs = env.reset()

    if JAX_AVAILABLE:
        agent = PPOAgentJAX(cfg)
    else:
        agent = PPOAgentNumpy(cfg)

    for step in range(5):
        actions, log_probs, values = agent.select_action(obs)
        action_name = SC2_ACTIONS[int(actions[0])]
        print(
            f"  Step {step+1}: action={action_name!r:<22} "
            f"log_prob={log_probs[0]:.4f} "
            f"value={values[0]:.4f}"
        )
        obs, rewards, dones, _ = env.step(actions)

    print("\nDone.")


if __name__ == "__main__":
    main()
