# -*- coding: utf-8 -*-
"""
Advanced GPU Training - V2 전투 시뮬레이션 + MAPPO + 1000 게임 리그

Phase 1: V2 전투 시뮬레이션 (사거리/아머/스플래시) + 최적 카운터 탐색
Phase 2: MAPPO 멀티 에이전트 학습
Phase 3: 1000 게임 리그 학습 (ELO 2000+ 목표)
Phase 4: 최종 리포트
"""

import sys, os, time, json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "wicked_zerg_challenger"))

from gpu_manager import get_gpu_manager, TORCH_AVAILABLE

if TORCH_AVAILABLE:
    import torch
    import torch.optim as optim


def phase1_v2_combat():
    """Phase 1: V2 전투 시뮬레이션"""
    from gpu_combat_simulator_v2 import GPUCombatSimulatorV2

    print("\n" + "=" * 60)
    print("  Phase 1: V2 Combat Simulation (Range/Armor/Splash)")
    print("=" * 60)

    sim = GPUCombatSimulatorV2()
    results = {}

    matchups = [
        (
            "24 Zerglings vs 12 Marines",
            [{"type": "zergling", "count": 24}],
            [{"type": "marine", "count": 12}],
        ),
        (
            "20 Hydras vs 8 Siege Tanks (THE counter test)",
            [{"type": "hydralisk", "count": 20}],
            [{"type": "siegetank", "count": 8}],
        ),
        (
            "20 Hydras vs 8 Siege Tanks (KITE tactics)",
            [{"type": "hydralisk", "count": 20}],
            [{"type": "siegetank", "count": 8}],
        ),
        (
            "15 Roaches vs 5 Immortals",
            [{"type": "roach", "count": 15}],
            [{"type": "immortal", "count": 5}],
        ),
        (
            "30 Lings vs 4 Colossus",
            [{"type": "zergling", "count": 30}],
            [{"type": "colossus", "count": 4}],
        ),
        (
            "10 Mutas vs 8 Marines + 2 Thor",
            [{"type": "mutalisk", "count": 10}],
            [{"type": "marine", "count": 8}, {"type": "thor", "count": 2}],
        ),
        (
            "8 Ultras vs 20 Marines + 5 Marauders",
            [{"type": "ultralisk", "count": 8}],
            [{"type": "marine", "count": 20}, {"type": "marauder", "count": 5}],
        ),
        (
            "Mixed Zerg vs Mixed Terran",
            [
                {"type": "zergling", "count": 12},
                {"type": "roach", "count": 6},
                {"type": "hydralisk", "count": 4},
            ],
            [
                {"type": "marine", "count": 8},
                {"type": "marauder", "count": 4},
                {"type": "siegetank", "count": 2},
            ],
        ),
    ]

    for i, (name, our, enemy) in enumerate(matchups):
        tactics = "kite" if "KITE" in name else "focus_fire"
        start = time.perf_counter()
        result = sim.simulate_v2(our, enemy, num_simulations=4096, tactics=tactics)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"  {name}:")
        print(
            f"    Win: {result['win_rate']:.1%} | Survivors: {result.get('avg_survivors_on_win',0):.1f} | "
            f"Rounds: {result.get('avg_rounds',0):.0f} | Dmg: {result.get('avg_damage_dealt',0):.0f} | "
            f"{elapsed:.0f}ms [{tactics}]"
        )
        results[name] = {
            **{k: v for k, v in result.items() if not isinstance(v, np.ndarray)},
            "time_ms": elapsed,
        }

    # 최적 카운터 탐색
    print(f"\n  --- Optimal Counter Search: vs 8 Siege Tanks ---")
    counters = sim.find_optimal_counter(
        [{"type": "siegetank", "count": 8}],
        budget_supply=40,
        num_simulations=2048,
    )
    for i, c in enumerate(counters[:5]):
        print(f"    #{i+1}: {c['composition']:40s} -> Win: {c['win_rate']:.1%}")

    results["counter_search"] = [
        {"composition": c["composition"], "win_rate": c["win_rate"]}
        for c in counters[:5]
    ]

    return results


def phase2_mappo():
    """Phase 2: MAPPO 멀티 에이전트 학습"""
    from gpu_mappo_agents import MAPPOSystem

    print("\n" + "=" * 60)
    print("  Phase 2: MAPPO Multi-Agent Training")
    print("=" * 60)

    mappo = MAPPOSystem()
    result = mappo.run_training(num_iterations=200, steps_per_iter=100)
    return result


def phase3_league_1000():
    """Phase 3: 1000 게임 리그"""
    from gpu_selfplay_league import GPUSelfPlayLeague
    from gpu_training_pipeline import PPOActorCritic

    print("\n" + "=" * 60)
    print("  Phase 3: 1000-Game League Training (ELO 2000+ Target)")
    print("=" * 60)

    gpu = get_gpu_manager()
    device = gpu.get_device()

    model = PPOActorCritic(state_dim=20, action_dim=8, hidden=256).to(device)

    # 기존 챔피언 모델 로딩
    for path in ["data/models/league_champion.pt", "data/models/ppo_latest.pt"]:
        if os.path.exists(path):
            try:
                ckpt = torch.load(path, map_location=device, weights_only=False)
                model.load_state_dict(ckpt["model"])
                print(f"[LEAGUE] Loaded: {path}")
                break
            except Exception:
                pass

    optimizer = optim.Adam(model.parameters(), lr=5e-5, eps=1e-5)

    league = GPUSelfPlayLeague(
        state_dim=20,
        action_dim=8,
        config={
            "pool_size": 15,
            "snapshot_interval": 100,
        },
    )

    result = league.run_league_training(
        model=model,
        optimizer=optimizer,
        num_games=1000,
        train_every=10,
        config={"clip_epsilon": 0.15, "value_coeff": 0.5, "entropy_coeff": 0.005},
    )

    # 저장
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "elo": result["final_elo"],
            "win_rate": result["win_rate"],
        },
        "data/models/league_champion_v2.pt",
    )
    torch.save(model.state_dict(), "data/models/strategy_net.pt")

    return result


def final_report(combat, mappo, league):
    """최종 리포트"""
    gpu = get_gpu_manager()

    print("\n" + "=" * 70)
    print("  ADVANCED TRAINING - FINAL REPORT")
    print("=" * 70)

    print(
        f"\n  GPU: {gpu.gpu_name} | VRAM: {gpu.memory_stats()['allocated_mb']:.1f}MB used"
    )

    print(f"\n  === V2 Combat Simulation ===")
    for name, r in combat.items():
        if name == "counter_search":
            continue
        print(f"  {name}: {r.get('win_rate',0):.0%} win ({r.get('time_ms',0):.0f}ms)")

    if "counter_search" in combat:
        print(f"\n  === Best Counters vs Siege Tanks ===")
        for c in combat["counter_search"][:3]:
            print(f"  {c['composition']}: {c['win_rate']:.0%}")

    print(f"\n  === MAPPO Multi-Agent ===")
    print(
        f"  Time: {mappo.get('total_time', 0):.1f}s | Steps: {mappo.get('total_steps', 0):,}"
    )
    for agent, info in mappo.get("agents", {}).items():
        print(f"    {agent:12s}: reward={info['avg_reward']:+.4f}")

    print(f"\n  === League Training ===")
    print(f"  Games: {league.get('total_games', 0)}")
    print(f"  Win rate: {league.get('win_rate', 0):.1%}")
    print(f"  Final ELO: {league.get('final_elo', 0):.0f}")
    print(f"  Curriculum: {league.get('curriculum', {}).get('current_level', 'N/A')}")

    lb = league.get("leaderboard", [])
    if lb:
        print(f"\n  === ELO Leaderboard (Top 5) ===")
        for name, rating in lb[:5]:
            print(f"    {name:20s} {rating:.0f}")

    print("=" * 70)

    # JSON 저장
    def ser(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)

    os.makedirs("data/training_results", exist_ok=True)
    with open("data/training_results/advanced_training_report.json", "w") as f:
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gpu": gpu.gpu_name,
            "combat_v2": {k: v for k, v in combat.items()},
            "mappo": mappo,
            "league": {k: v for k, v in league.items() if k != "elo_history"},
        }
        json.dump(report, f, indent=2, default=ser)
    print(f"\n  Report: data/training_results/advanced_training_report.json")


if __name__ == "__main__":
    print("=" * 70)
    print("  SC2 Zerg AI - Advanced GPU Training Pipeline")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    total_start = time.time()

    combat = phase1_v2_combat()
    mappo = phase2_mappo()
    league = phase3_league_1000()

    final_report(combat, mappo, league)

    total = time.time() - total_start
    print(f"\n  Total: {total:.1f}s ({total/60:.1f}m)")
