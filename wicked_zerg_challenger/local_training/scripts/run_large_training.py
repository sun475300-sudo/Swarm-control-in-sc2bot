#!/usr/bin/env python3
"""
대규모 PPO/RL 훈련 스크립트

PPOAgent 100에피소드 + RLAgent 100에피소드를 SC2ZergEnv 시뮬레이터에서 실행합니다.
SC2 클라이언트 없이 독립 실행 가능합니다.

사용법:
    python run_large_training.py                    # 기본 (PPO 100ep + RL 100ep)
    python run_large_training.py --ppo-episodes 50  # PPO만 50ep
    python run_large_training.py --rl-episodes 200  # RL만 200ep
    python run_large_training.py --skip-rl          # PPO만 실행
"""

import argparse
import logging
import os
import sys
import time

import numpy as np

logger = logging.getLogger("RunLargeTraining")

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "wicked_zerg_challenger"))
sys.path.insert(
    0, os.path.join(PROJECT_ROOT, "wicked_zerg_challenger", "local_training")
)

# SC2ZergEnv 시뮬레이터
from gymnasium_env.sc2_gym_env import SC2ZergEnv


def train_ppo_agent(n_episodes: int, save_dir: str, max_frames: int = 2000):
    """PPOAgent 대규모 훈련."""
    from local_training.ppo_agent import PPOAgent

    agent = PPOAgent(learning_rate=3e-4, gamma=0.99, ppo_epochs=4, batch_size=64)
    env = SC2ZergEnv(max_frames=max_frames)

    logger.info(
        "╔══════════════════════════════════════════════════════════════════════╗"
    )
    logger.info(
        f"║  PPO Agent Training — {n_episodes} Episodes (max_frames={max_frames})"
    )
    logger.info(
        "╠══════════════════════════════════════════════════════════════════════╣"
    )

    wins = 0
    total_rewards = []
    value_losses = []
    t0 = time.time()

    for ep in range(1, n_episodes + 1):
        obs_tuple = env.reset()
        obs = obs_tuple[0] if isinstance(obs_tuple, tuple) else obs_tuple
        if isinstance(obs, (list, tuple)):
            obs = np.array(obs, dtype=np.float32)

        done = False
        ep_reward = 0.0
        steps = 0

        while not done:
            # obs를 15차원으로 변환 (SC2ZergEnv는 16차원)
            state = obs[:15] if len(obs) >= 15 else np.pad(obs, (0, 15 - len(obs)))

            action_idx, _, _ = agent.get_action(state, training=True)

            # SC2ZergEnv step
            result = env.step(action_idx % 7)  # 7 actions in SC2ZergEnv
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result

            if isinstance(obs, (list, tuple)):
                obs = np.array(obs, dtype=np.float32)

            agent.update_reward(reward)
            ep_reward += reward
            steps += 1

        # 에피소드 종료 — 학습
        won = info.get("winner") == "self" if isinstance(info, dict) else False
        final_r = 1.0 if won else -0.5
        metrics = agent.end_episode(final_reward=final_r)
        if won:
            wins += 1

        total_rewards.append(ep_reward)
        vl = metrics.get("value_loss", 0)
        value_losses.append(vl)

        # 출력
        result_str = "[OK] WIN " if won else "[X] LOSS"
        avg_r = np.mean(total_rewards[-10:])
        wr = wins / ep * 100
        logger.info(
            f"║ Ep {ep:4d}/{n_episodes} │ {steps:4d}s │ R={ep_reward:7.1f} │ "
            f"AvgR={avg_r:6.1f} │ VL={vl:7.2f} │ WR={wr:4.1f}% │ {result_str} ║"
        )

        # 10에피소드마다 체크포인트
        if ep % 10 == 0:
            cp_path = os.path.join(save_dir, f"ppo_ep{ep}.npz")
            agent.save_model(cp_path)
            elapsed = time.time() - t0
            eps_per_sec = ep / elapsed
            logger.info(
                f"║ ── Checkpoint: {cp_path} ({elapsed:.0f}s, {eps_per_sec:.1f} ep/s) ──"
            )

    # 최종 저장
    final_path = os.path.join(save_dir, f"ppo_{n_episodes}ep.npz")
    agent.save_model(final_path)

    elapsed = time.time() - t0
    logger.info(
        "╠══════════════════════════════════════════════════════════════════════╣"
    )
    logger.info(
        f"║  PPO 훈련 완료: {n_episodes}ep, 승률 {wins}/{n_episodes} ({wins/n_episodes*100:.1f}%)"
    )
    logger.info(
        f"║  is_trained={agent.is_trained()}, deployment={agent.is_ready_for_deployment()}"
    )
    logger.info(f"║  최종 모델: {final_path} ({elapsed:.1f}s)")
    logger.info(
        "╚══════════════════════════════════════════════════════════════════════╝"
    )

    return {
        "agent": "PPO",
        "episodes": n_episodes,
        "wins": wins,
        "win_rate": wins / n_episodes,
        "avg_reward": float(np.mean(total_rewards)),
        "avg_value_loss": float(np.mean(value_losses)),
        "is_trained": agent.is_trained(),
        "deployment": agent.is_ready_for_deployment(),
        "model_path": final_path,
        "elapsed": elapsed,
    }


def train_rl_agent(n_episodes: int, save_dir: str, max_frames: int = 2000):
    """RLAgent (REINFORCE) 대규모 훈련."""
    from local_training.rl_agent import RLAgent

    agent = RLAgent(learning_rate=0.001)
    env = SC2ZergEnv(max_frames=max_frames)

    logger.info(
        "╔══════════════════════════════════════════════════════════════════════╗"
    )
    logger.info(f"║  RL Agent (REINFORCE) Training — {n_episodes} Episodes")
    logger.info(
        "╠══════════════════════════════════════════════════════════════════════╣"
    )

    wins = 0
    total_rewards = []
    t0 = time.time()

    for ep in range(1, n_episodes + 1):
        obs_tuple = env.reset()
        obs = obs_tuple[0] if isinstance(obs_tuple, tuple) else obs_tuple
        if isinstance(obs, (list, tuple)):
            obs = np.array(obs, dtype=np.float32)

        done = False
        ep_reward = 0.0
        steps = 0

        while not done:
            state = obs[:15] if len(obs) >= 15 else np.pad(obs, (0, 15 - len(obs)))
            action = agent.get_action(state)
            if isinstance(action, tuple):
                action_idx = action[0]
            else:
                action_idx = action

            result = env.step(int(action_idx) % 7)
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result

            if isinstance(obs, (list, tuple)):
                obs = np.array(obs, dtype=np.float32)

            agent.update_reward(reward)
            ep_reward += reward
            steps += 1

        won = info.get("winner") == "self" if isinstance(info, dict) else False
        final_r = 1.0 if won else -0.5
        metrics = agent.end_episode(final_reward=final_r)
        if won:
            wins += 1

        total_rewards.append(ep_reward)
        result_str = "[OK] WIN " if won else "[X] LOSS"
        avg_r = np.mean(total_rewards[-10:])
        wr = wins / ep * 100
        loss = metrics.get("loss", 0) if isinstance(metrics, dict) else 0
        logger.info(
            f"║ Ep {ep:4d}/{n_episodes} │ {steps:4d}s │ R={ep_reward:7.1f} │ "
            f"AvgR={avg_r:6.1f} │ L={loss:7.4f} │ WR={wr:4.1f}% │ {result_str} ║"
        )

        if ep % 10 == 0:
            cp_path = os.path.join(save_dir, f"rl_ep{ep}.npz")
            agent.save_model(cp_path)
            elapsed = time.time() - t0
            logger.info(f"║ ── Checkpoint: {cp_path} ({elapsed:.0f}s) ──")

    final_path = os.path.join(save_dir, f"rl_{n_episodes}ep.npz")
    agent.save_model(final_path)

    elapsed = time.time() - t0
    ready = agent.is_ready_for_deployment()
    logger.info(
        "╠══════════════════════════════════════════════════════════════════════╣"
    )
    logger.info(
        f"║  RL 훈련 완료: {n_episodes}ep, 승률 {wins}/{n_episodes} ({wins/n_episodes*100:.1f}%)"
    )
    logger.info(f"║  is_trained={agent.is_trained()}, deployment={ready}")
    logger.info(f"║  최종 모델: {final_path} ({elapsed:.1f}s)")
    logger.info(
        "╚══════════════════════════════════════════════════════════════════════╝"
    )

    return {
        "agent": "RL",
        "episodes": n_episodes,
        "wins": wins,
        "win_rate": wins / n_episodes,
        "avg_reward": float(np.mean(total_rewards)),
        "is_trained": agent.is_trained(),
        "deployment": ready,
        "model_path": final_path,
        "elapsed": elapsed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="대규모 PPO/RL 훈련")
    parser.add_argument("--ppo-episodes", type=int, default=100)
    parser.add_argument("--rl-episodes", type=int, default=100)
    parser.add_argument("--max-frames", type=int, default=2000)
    parser.add_argument("--skip-ppo", action="store_true")
    parser.add_argument("--skip-rl", action="store_true")
    parser.add_argument(
        "--save-dir",
        type=str,
        default=os.path.join(
            PROJECT_ROOT, "wicked_zerg_challenger", "local_training", "models"
        ),
    )
    args = parser.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)
    results = []

    if not args.skip_ppo:
        r = train_ppo_agent(args.ppo_episodes, args.save_dir, args.max_frames)
        results.append(r)

    if not args.skip_rl:
        r = train_rl_agent(args.rl_episodes, args.save_dir, args.max_frames)
        results.append(r)

    # 최종 요약
    print("\n" + "=" * 72)
    print("  대규모 훈련 최종 요약")
    print("=" * 72)
    for r in results:
        print(
            f"  {r['agent']:4s} │ {r['episodes']}ep │ WR={r['win_rate']*100:.1f}% │ "
            f"AvgR={r['avg_reward']:.1f} │ Trained={r['is_trained']} │ {r['elapsed']:.1f}s"
        )
    print("=" * 72)
