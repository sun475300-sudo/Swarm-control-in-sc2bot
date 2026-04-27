# -*- coding: utf-8 -*-
"""
GPU Training Runner - GPU 대규모 학습 실행 스크립트

사용법:
    python run_gpu_training.py [--iterations 100] [--batch-size 2048]
"""

import sys
import os
import time
import json
import argparse

# 프로젝트 경로 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "wicked_zerg_challenger"))

from gpu_manager import get_gpu_manager
from gpu_combat_simulator import GPUCombatSimulator
from gpu_spatial_engine import GPUSpatialEngine
from gpu_training_pipeline import GPUTrainingPipeline
from gpu_realtime_inference import GPURealtimeInference
import numpy as np


def run_full_benchmark():
    """전체 GPU 벤치마크 실행"""
    print("\n" + "=" * 70)
    print("  SC2 Zerg AI Bot - GPU Accelerated Training & Benchmark")
    print("=" * 70)

    # 1. GPU 상태 확인
    gpu = get_gpu_manager()
    print(f"\n{gpu.status_report()}\n")

    results = {}

    # 2. 전투 시뮬레이션 벤치마크
    print("\n--- Phase 1: Combat Simulation Benchmark ---")
    combat_sim = GPUCombatSimulator()

    # 저글링 vs 마린 전투
    zerglings = [{"hp": 35, "attack": 5, "type": "zergling"} for _ in range(24)]
    marines = [{"hp": 45, "attack": 6, "type": "marine"} for _ in range(12)]

    start = time.perf_counter()
    combat_result = combat_sim.simulate_battles_gpu(
        zerglings, marines, num_simulations=4096
    )
    combat_time = (time.perf_counter() - start) * 1000

    print(f"  24 Zerglings vs 12 Marines (4096 sims):")
    print(f"    Win rate: {combat_result['win_rate']:.1%}")
    print(f"    Avg survivors: {combat_result.get('avg_survivors_on_win', 0):.1f}")
    print(f"    Avg rounds: {combat_result.get('avg_rounds', 0):.0f}")
    print(f"    Time: {combat_time:.1f}ms")
    print(f"    GPU: {combat_result.get('gpu_accelerated', False)}")
    results["combat_simulation"] = {**combat_result, "time_ms": combat_time}

    # 로치 vs 불멸자 전투
    roaches = [{"hp": 145, "attack": 16, "type": "roach"} for _ in range(15)]
    immortals = [{"hp": 200, "attack": 20, "type": "immortal"} for _ in range(5)]

    start = time.perf_counter()
    combat_result2 = combat_sim.simulate_battles_gpu(
        roaches, immortals, num_simulations=4096
    )
    combat_time2 = (time.perf_counter() - start) * 1000

    print(f"\n  15 Roaches vs 5 Immortals (4096 sims):")
    print(f"    Win rate: {combat_result2['win_rate']:.1%}")
    print(f"    Time: {combat_time2:.1f}ms")
    results["combat_simulation_2"] = {**combat_result2, "time_ms": combat_time2}

    # 유닛 구성 최적화
    print("\n  Composition Optimization:")
    comps = [
        [{"hp": 35, "attack": 5, "type": "zergling"} for _ in range(30)],
        [{"hp": 145, "attack": 16, "type": "roach"} for _ in range(10)],
        [{"hp": 80, "attack": 12, "type": "hydra"} for _ in range(12)],
        [{"hp": 35, "attack": 5, "type": "zergling"} for _ in range(15)]
        + [{"hp": 145, "attack": 16, "type": "roach"} for _ in range(5)],
    ]
    comp_results = combat_sim.evaluate_composition(comps, marines, num_simulations=1024)
    for i, cr in enumerate(comp_results):
        types = cr.get("composition", [])
        type_counts = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1
        comp_str = ", ".join(f"{v}x {k}" for k, v in type_counts.items())
        print(f"    #{i+1}: {comp_str} -> Win: {cr['win_rate']:.1%}")

    # 3. 공간 연산 벤치마크
    print("\n--- Phase 2: Spatial Engine Benchmark ---")
    spatial = GPUSpatialEngine(200, 200)

    # 클러스터링
    positions = np.random.rand(500, 2) * 200
    start = time.perf_counter()
    labels, centroids = spatial.cluster_units_gpu(positions, n_clusters=8)
    cluster_time = (time.perf_counter() - start) * 1000
    print(f"  K-means clustering (500 units, 8 clusters): {cluster_time:.1f}ms")
    results["clustering"] = {"time_ms": cluster_time, "n_units": 500}

    # 최근접 이웃
    queries = np.random.rand(100, 2) * 200
    targets = np.random.rand(300, 2) * 200
    start = time.perf_counter()
    indices, distances = spatial.batch_nearest_neighbors(queries, targets, k=5)
    nn_time = (time.perf_counter() - start) * 1000
    print(f"  Batch k-NN (100 queries, 300 targets, k=5): {nn_time:.1f}ms")
    results["nearest_neighbor"] = {"time_ms": nn_time}

    # 위협 히트맵
    enemy_pos = np.random.rand(50, 2) * 200
    enemy_dps = np.random.rand(50) * 20 + 5
    start = time.perf_counter()
    threat_map = spatial.compute_threat_heatmap(enemy_pos, enemy_dps, resolution=4)
    heatmap_time = (time.perf_counter() - start) * 1000
    print(f"  Threat heatmap (50 enemies, 50x50 grid): {heatmap_time:.1f}ms")
    print(f"    Max threat: {threat_map.max():.2f}, Mean: {threat_map.mean():.4f}")
    results["threat_heatmap"] = {
        "time_ms": heatmap_time,
        "max": float(threat_map.max()),
    }

    # 영향력 맵
    our_pos = np.random.rand(40, 2) * 200
    our_power = np.random.rand(40) * 15 + 5
    start = time.perf_counter()
    influence = spatial.compute_influence_map(
        our_pos, our_power, enemy_pos, enemy_dps, resolution=4
    )
    influence_time = (time.perf_counter() - start) * 1000
    print(f"  Influence map (40 allies vs 50 enemies): {influence_time:.1f}ms")
    results["influence_map"] = {"time_ms": influence_time}

    # 거리 행렬
    units = np.random.rand(200, 2) * 200
    start = time.perf_counter()
    dist_matrix = spatial.compute_distance_matrix(units)
    dist_time = (time.perf_counter() - start) * 1000
    print(f"  Distance matrix (200x200): {dist_time:.1f}ms")
    results["distance_matrix"] = {"time_ms": dist_time}

    # 4. 실시간 추론 벤치마크
    print("\n--- Phase 3: Real-time Inference Benchmark ---")
    inference = GPURealtimeInference()

    # 전략 추론
    game_state = {
        "minerals": 500,
        "vespene": 200,
        "supply_used": 80,
        "supply_cap": 100,
        "worker_count": 40,
        "army_supply": 40,
        "enemy_army_supply": 35,
        "base_count": 3,
        "enemy_base_count": 2,
        "game_time_minutes": 8,
        "upgrade_count": 3,
        "tech_level": 2,
        "threat_level": 1,
        "zergling_count": 20,
        "roach_count": 8,
        "hydra_count": 5,
        "ultra_count": 0,
        "air_count": 0,
        "score": 15000,
        "enemy_score": 12000,
    }

    # 웜업
    for _ in range(10):
        inference.infer_strategy(game_state)

    start = time.perf_counter()
    for _ in range(1000):
        strategy, conf, val = inference.infer_strategy(game_state)
    strategy_time = time.perf_counter() - start
    print(
        f"  Strategy inference (1000 calls): {strategy_time*1000:.1f}ms total, {strategy_time:.3f}ms avg"
    )
    print(f"    Last: {strategy} (confidence: {conf:.3f}, value: {val:.3f})")
    results["strategy_inference"] = {
        "total_ms": strategy_time * 1000,
        "avg_us": strategy_time,
    }

    # 배치 전투 추론
    combat_states = [
        {
            "our_supply": 50,
            "enemy_supply": 45,
            "our_hp_ratio": 0.9,
            "enemy_hp_ratio": 0.8,
            "distance_to_enemy": 8,
        }
        for _ in range(64)
    ]
    start = time.perf_counter()
    combat_decisions = inference.infer_combat_batch(combat_states)
    batch_time = (time.perf_counter() - start) * 1000
    print(f"  Batch combat inference (64 units): {batch_time:.1f}ms")
    results["batch_inference"] = {"time_ms": batch_time, "batch_size": 64}

    # 배치 마이크로 추론
    unit_states = [
        {
            "hp_ratio": 0.7,
            "weapon_cooldown": 0,
            "distance_to_target": 3,
            "nearby_allies": 8,
            "nearby_enemies": 5,
            "on_creep": 1,
        }
        for _ in range(128)
    ]
    start = time.perf_counter()
    micro_decisions = inference.infer_micro_batch(unit_states)
    micro_time = (time.perf_counter() - start) * 1000
    print(f"  Batch micro inference (128 units): {micro_time:.1f}ms")
    results["micro_inference"] = {"time_ms": micro_time, "batch_size": 128}

    print(f"\n  Inference stats: {inference.get_stats()}")

    # 5. GPU 학습 파이프라인
    print("\n--- Phase 4: GPU Training Pipeline ---")
    pipeline = GPUTrainingPipeline(
        {
            "learning_rate": 3e-4,
            "batch_size": 2048,
            "num_epochs": 4,
        }
    )

    training_result = pipeline.run_synthetic_training(
        num_iterations=50, batch_size=2048
    )
    results["training"] = training_result

    # 6. 통합 프레임 처리 벤치마크
    print("\n--- Phase 5: Integrated Frame Processing ---")
    from gpu_integration import GPUIntegration

    integration = GPUIntegration()
    integration.initialize(200, 200)

    our_units_data = [
        {
            "x": np.random.rand() * 200,
            "y": np.random.rand() * 200,
            "hp": 35,
            "attack": 5,
            "dps": 10,
            "supply": 1,
            "hp_ratio": 0.9,
            "type": "zergling",
        }
        for _ in range(40)
    ]
    enemy_units_data = [
        {
            "x": np.random.rand() * 200,
            "y": np.random.rand() * 200,
            "hp": 45,
            "attack": 6,
            "dps": 12,
            "supply": 1,
            "hp_ratio": 1.0,
            "type": "marine",
        }
        for _ in range(20)
    ]

    # 웜업
    for _ in range(5):
        integration.process_frame(game_state, our_units_data, enemy_units_data)

    # 벤치마크 (100 프레임)
    start = time.perf_counter()
    for _ in range(100):
        frame_result = integration.process_frame(
            game_state, our_units_data, enemy_units_data
        )
    frame_total = (time.perf_counter() - start) * 1000

    print(
        f"  100 frames processed: {frame_total:.1f}ms total, {frame_total/100:.2f}ms avg/frame"
    )
    print(f"  Strategy: {frame_result.get('strategy', {}).get('action', 'N/A')}")
    print(f"  Should engage: {frame_result.get('should_engage', 'N/A')}")
    print(f"  Win probability: {frame_result.get('win_probability', 'N/A')}")
    print(f"  Performance: {integration.get_performance_stats()}")
    results["frame_processing"] = {
        "total_ms": frame_total,
        "avg_ms": frame_total / 100,
        "last_frame": {
            k: v for k, v in frame_result.items() if k not in ("threat_map", "clusters")
        },
    }

    # 최종 요약
    print("\n" + "=" * 70)
    print("  FINAL RESULTS SUMMARY")
    print("=" * 70)
    print(f"  GPU Device: {gpu.gpu_name}")
    print(f"  GPU Available: {gpu.gpu_available}")
    print(
        f"  Combat sim (4096 battles): {results['combat_simulation']['time_ms']:.1f}ms"
    )
    print(f"  Clustering (500 units): {results['clustering']['time_ms']:.1f}ms")
    print(f"  Threat heatmap: {results['threat_heatmap']['time_ms']:.1f}ms")
    print(
        f"  Strategy inference: {results['strategy_inference']['avg_us']*1000:.3f}ms avg"
    )
    print(
        f"  Training throughput: {results['training'].get('samples_per_second', 0):,.0f} samples/s"
    )
    print(f"  Frame processing: {results['frame_processing']['avg_ms']:.2f}ms avg")
    print(f"  GPU Memory: {gpu.memory_stats()}")
    print("=" * 70)

    # 결과 저장
    results_path = os.path.join(os.path.dirname(__file__), "data", "training_results")
    os.makedirs(results_path, exist_ok=True)

    # numpy 값을 직렬화 가능하게 변환
    def serialize(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    with open(os.path.join(results_path, "gpu_benchmark_results.json"), "w") as f:
        json.dump(results, f, indent=2, default=serialize)

    print(f"\n  Results saved to: {results_path}/gpu_benchmark_results.json")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SC2 Bot GPU Training")
    parser.add_argument(
        "--iterations", type=int, default=50, help="Training iterations"
    )
    parser.add_argument("--batch-size", type=int, default=2048, help="Batch size")
    args = parser.parse_args()

    run_full_benchmark()
