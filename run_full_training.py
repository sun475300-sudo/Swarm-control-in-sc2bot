# -*- coding: utf-8 -*-
"""
Full GPU Training Pipeline - 대규모 통합 학습 실행

Phase 1: 벡터화 전투 시뮬레이션 벤치마크
Phase 2: Transformer 모델 대규모 PPO 학습 (100만+ 샘플)
Phase 3: Self-Play 리그 학습 + Curriculum Learning
Phase 4: 최종 결과 분석 및 리포트
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "wicked_zerg_challenger"))

from gpu_manager import TORCH_AVAILABLE, get_gpu_manager

if TORCH_AVAILABLE:
    import torch
    import torch.nn.functional as F
    import torch.optim as optim


def phase1_combat_benchmark():
    """Phase 1: 벡터화 전투 시뮬레이션 벤치마크"""
    from gpu_combat_simulator import GPUCombatSimulator

    print("\n" + "=" * 60)
    print("  Phase 1: Vectorized Combat Simulation")
    print("=" * 60)

    sim = GPUCombatSimulator()

    matchups = [
        (
            "24 Zerglings vs 12 Marines",
            [{"hp": 35, "attack": 5} for _ in range(24)],
            [{"hp": 45, "attack": 6} for _ in range(12)],
        ),
        (
            "15 Roaches vs 5 Immortals",
            [{"hp": 145, "attack": 16} for _ in range(15)],
            [{"hp": 200, "attack": 20} for _ in range(5)],
        ),
        (
            "20 Hydras vs 8 Siege Tanks",
            [{"hp": 80, "attack": 12} for _ in range(20)],
            [{"hp": 175, "attack": 40} for _ in range(8)],
        ),
        (
            "10 Mutas vs 6 Marines + 4 Medivacs",
            [{"hp": 120, "attack": 9} for _ in range(10)],
            [{"hp": 45, "attack": 6} for _ in range(6)]
            + [{"hp": 150, "attack": 0} for _ in range(4)],
        ),
        (
            "30 Lings + 5 Banes vs 15 Marines",
            [{"hp": 35, "attack": 5} for _ in range(30)]
            + [{"hp": 30, "attack": 20} for _ in range(2)],
            [{"hp": 45, "attack": 6} for _ in range(15)],
        ),
    ]

    results = {}
    for name, our, enemy in matchups:
        start = time.perf_counter()
        result = sim.simulate_battles_gpu(our, enemy, num_simulations=8192)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  {name}:")
        print(
            f"    Win: {result['win_rate']:.1%} | Survivors: {result.get('avg_survivors_on_win', 0):.1f} | Rounds: {result.get('avg_rounds', 0):.0f} | {elapsed:.0f}ms"
        )
        results[name] = {**result, "time_ms": elapsed}

    return results


def phase2_large_scale_training():
    """Phase 2: 대규모 PPO 학습"""
    from gpu_training_pipeline import GPUTrainingPipeline

    print("\n" + "=" * 60)
    print("  Phase 2: Large-Scale PPO Training")
    print("=" * 60)

    pipeline = GPUTrainingPipeline(
        {
            "learning_rate": 3e-4,
            "batch_size": 4096,
            "minibatch_size": 512,
            "num_epochs": 4,
            "lr_schedule": "cosine",
            "total_timesteps": 1_000_000,
        }
    )

    # 200 iterations × 4096 batch = 819,200 samples
    result = pipeline.run_synthetic_training(
        num_iterations=200,
        batch_size=4096,
    )

    return result


def phase3_selfplay_league():
    """Phase 3: Self-Play 리그 + Curriculum Learning"""
    from gpu_selfplay_league import GPUSelfPlayLeague
    from gpu_training_pipeline import PPOActorCritic

    print("\n" + "=" * 60)
    print("  Phase 3: Self-Play League Training")
    print("=" * 60)

    gpu = get_gpu_manager()
    device = gpu.get_device()

    # 모델 초기화
    model = PPOActorCritic(state_dim=20, action_dim=8, hidden=256).to(device)

    # 저장된 가중치 로딩
    model_path = "data/models/ppo_latest.pt"
    if os.path.exists(model_path):
        try:
            checkpoint = torch.load(model_path, map_location=device, weights_only=False)
            model.load_state_dict(checkpoint["model"])
            print("[LEAGUE] Loaded pre-trained weights")
        except Exception as e:
            print(f"[LEAGUE] Starting from scratch: {e}")

    optimizer = optim.Adam(model.parameters(), lr=1e-4, eps=1e-5)

    # 리그 학습
    league = GPUSelfPlayLeague(state_dim=20, action_dim=8)

    result = league.run_league_training(
        model=model,
        optimizer=optimizer,
        num_games=300,
        train_every=10,
        config={"clip_epsilon": 0.2, "value_coeff": 0.5, "entropy_coeff": 0.01},
    )

    # 학습된 모델 저장
    models_dir = "data/models"
    os.makedirs(models_dir, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "elo": result["final_elo"],
            "win_rate": result["win_rate"],
        },
        os.path.join(models_dir, "league_champion.pt"),
    )

    # 전략/전투/마이크로 네트워크에도 저장
    torch.save(model.state_dict(), os.path.join(models_dir, "strategy_net.pt"))

    return result


def phase4_transformer_training():
    """Phase 4: Transformer 모델 학습"""
    from gpu_advanced_models import TransformerStrategyNet, encode_extended_state

    print("\n" + "=" * 60)
    print("  Phase 4: Transformer Strategy Network Training")
    print("=" * 60)

    gpu = get_gpu_manager()
    device = gpu.get_device()

    model = TransformerStrategyNet(
        state_dim=32, action_dim=8, hidden=512, n_heads=8, n_layers=3
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Transformer params: {total_params:,}")

    optimizer = optim.Adam(model.parameters(), lr=1e-4, eps=1e-5)

    start_time = time.time()
    best_reward = float("-inf")
    history = []

    for epoch in range(100):
        model.train()
        batch_size = 2048

        # 합성 데이터
        states = torch.randn(batch_size, 32, device=device) * 0.3
        game_times = torch.randint(0, 25, (batch_size,), device=device)

        # 전문가 행동 레이블 (시간대에 따른 전략)
        expert_actions = torch.where(
            game_times < 5,
            torch.zeros(batch_size, dtype=torch.long, device=device),  # Early: ECONOMY
            torch.where(
                game_times < 12,
                torch.ones(
                    batch_size, dtype=torch.long, device=device
                ),  # Mid: AGGRESSIVE
                torch.full(
                    (batch_size,), 4, dtype=torch.long, device=device
                ),  # Late: ALL_IN
            ),
        )
        # 노이즈 추가 (10% 확률로 다른 행동)
        noise_mask = torch.rand(batch_size, device=device) < 0.1
        noise_actions = torch.randint(0, 8, (batch_size,), device=device)
        expert_actions = torch.where(noise_mask, noise_actions, expert_actions)

        rewards = torch.randn(batch_size, device=device) * 0.3

        # Forward
        actions, log_probs, entropy, values = model.get_action_and_value(
            states, game_time_min=game_times
        )

        # Imitation + RL Loss
        imitation_loss = F.cross_entropy(model(states, game_times)[0], expert_actions)

        # PPO-style loss
        advantages = rewards - values.detach()
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        policy_loss = -(log_probs * advantages).mean()

        value_loss = F.mse_loss(values, rewards)
        entropy_loss = entropy.mean()

        # Combined loss (imitation 비중을 점진적으로 줄임)
        imitation_weight = max(0.5 * (1 - epoch / 100), 0.05)
        loss = (
            imitation_weight * imitation_loss
            + (1 - imitation_weight) * policy_loss
            + 0.5 * value_loss
            - 0.01 * entropy_loss
        )

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
        optimizer.step()

        avg_reward = rewards.mean().item()
        if avg_reward > best_reward:
            best_reward = avg_reward

        history.append(
            {
                "epoch": epoch,
                "imitation_loss": imitation_loss.item(),
                "policy_loss": policy_loss.item(),
                "value_loss": value_loss.item(),
                "entropy": entropy_loss.item(),
            }
        )

        if (epoch + 1) % 20 == 0:
            elapsed = time.time() - start_time
            # 전략 정확도 측정
            with torch.no_grad():
                pred_logits, _ = model(states, game_times)
                pred_actions = pred_logits.argmax(dim=-1)
                accuracy = (pred_actions == expert_actions).float().mean().item()

            print(
                f"  Epoch {epoch+1:3d}/100 | "
                f"IL: {imitation_loss.item():.4f} | "
                f"PL: {policy_loss.item():.4f} | "
                f"VL: {value_loss.item():.4f} | "
                f"Acc: {accuracy:.1%} | "
                f"{elapsed:.1f}s"
            )

    total_time = time.time() - start_time

    # 모델 저장
    torch.save(model.state_dict(), "data/models/transformer_strategy.pt")

    summary = {
        "total_params": total_params,
        "total_time": round(total_time, 2),
        "epochs": 100,
        "final_imitation_loss": history[-1]["imitation_loss"],
        "final_policy_loss": history[-1]["policy_loss"],
        "best_reward": best_reward,
    }
    print(f"  Transformer training done: {total_time:.1f}s, {total_params:,} params")

    return summary


def final_report(combat_results, ppo_results, league_results, transformer_results):
    """최종 통합 리포트"""
    gpu = get_gpu_manager()

    print("\n" + "=" * 70)
    print("  FINAL COMPREHENSIVE REPORT")
    print("=" * 70)

    print(f"\n  GPU: {gpu.gpu_name}")
    print(
        f"  VRAM Used: {gpu.memory_stats()['allocated_mb']:.1f} MB / {gpu.memory_stats()['total_mb']:.0f} MB"
    )

    print(f"\n  --- Combat Simulation ---")
    for name, res in combat_results.items():
        print(
            f"  {name}: {res['win_rate']:.0%} win ({res['time_ms']:.0f}ms for 8192 sims)"
        )

    print(f"\n  --- PPO Training ---")
    print(f"  Samples: {ppo_results.get('total_samples', 0):,}")
    print(f"  Throughput: {ppo_results.get('samples_per_second', 0):,.0f} samples/s")
    print(f"  Best reward: {ppo_results.get('best_reward', 0):+.4f}")
    print(f"  Time: {ppo_results.get('total_time_seconds', 0):.1f}s")

    print(f"\n  --- Self-Play League ---")
    print(f"  Games: {league_results.get('total_games', 0)}")
    print(f"  Win rate: {league_results.get('win_rate', 0):.1%}")
    print(f"  Final ELO: {league_results.get('final_elo', 0):.0f}")
    print(
        f"  Curriculum: {league_results.get('curriculum', {}).get('current_level', 'N/A')}"
    )
    print(f"  Time: {league_results.get('total_time_seconds', 0):.1f}s")

    print(f"\n  --- Transformer Model ---")
    print(f"  Parameters: {transformer_results.get('total_params', 0):,}")
    print(f"  Final IL: {transformer_results.get('final_imitation_loss', 0):.4f}")
    print(f"  Time: {transformer_results.get('total_time', 0):.1f}s")

    leaderboard = league_results.get("leaderboard", [])
    if leaderboard:
        print(f"\n  --- ELO Leaderboard ---")
        for name, rating in leaderboard[:5]:
            marker = " <<<" if name == "current" else ""
            print(f"  {name:20s} {rating:.0f}{marker}")

    print(f"\n  --- Curriculum Progression ---")
    curriculum = league_results.get("curriculum", {})
    print(f"  Final Level: {curriculum.get('current_level', 'N/A')}")
    print(f"  Promotions: {curriculum.get('promotions', 0)}")
    print(f"  Demotions: {curriculum.get('demotions', 0)}")

    print("=" * 70)

    # JSON 리포트 저장
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gpu": gpu.gpu_name,
        "combat_simulation": {
            k: {kk: vv for kk, vv in v.items() if not isinstance(vv, np.ndarray)}
            for k, v in combat_results.items()
        },
        "ppo_training": ppo_results,
        "selfplay_league": {
            k: v for k, v in league_results.items() if k != "elo_history"
        },
        "transformer": transformer_results,
    }

    def serialize(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, deque):
            return list(obj)
        return str(obj)

    from collections import deque

    os.makedirs("data/training_results", exist_ok=True)
    with open("data/training_results/full_training_report.json", "w") as f:
        json.dump(report, f, indent=2, default=serialize)

    print(f"\n  Full report saved: data/training_results/full_training_report.json")


if __name__ == "__main__":
    print("=" * 70)
    print("  SC2 Zerg AI - Full GPU Training Pipeline")
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    total_start = time.time()

    combat_results = phase1_combat_benchmark()
    ppo_results = phase2_large_scale_training()
    league_results = phase3_selfplay_league()
    transformer_results = phase4_transformer_training()

    final_report(combat_results, ppo_results, league_results, transformer_results)

    total_time = time.time() - total_start
    print(f"\n  Total pipeline time: {total_time:.1f}s ({total_time/60:.1f}m)")
