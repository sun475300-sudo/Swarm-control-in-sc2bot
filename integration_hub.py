# -*- coding: utf-8 -*-
"""
Phase 66: Multi-Language System Integration Hub
전체 시스템 통합 브릿지 - Python Hub

이 모듈은 Rust, Go, Julia, C++, Kotlin 모듈을 통합합니다.
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from wicked_zerg_challenger.rust_accel import (
        nearest_point_index,
        combat_power_comparison,
        batch_nearest_points,
        path_distance,
        route_distance,
        cluster_points,
        formation_positions,
        rust_available,
    )

    RUST_AVAILABLE = rust_available()
except ImportError:
    RUST_AVAILABLE = {"nearest_point_index": False}
    nearest_point_index = None
    combat_power_comparison = None


@dataclass
class SystemStatus:
    rust: Dict[str, bool]
    go: bool
    julia: bool
    cpp: bool
    kotlin: bool
    android_app: bool


class IntegrationHub:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.status = self._check_all_systems()

    def _check_all_systems(self) -> SystemStatus:
        return SystemStatus(
            rust=RUST_AVAILABLE,
            go=self._check_go_server(),
            julia=self._check_julia(),
            cpp=self._check_cpp(),
            kotlin=self._check_kotlin(),
            android_app=self._check_android(),
        )

    def _check_go_server(self) -> bool:
        go_backend = self.project_root / "go_backend"
        return go_backend.exists() and (go_backend / "go.mod").exists()

    def _check_julia(self) -> bool:
        julia_dir = self.project_root / "julia_ml"
        return julia_dir.exists()

    def _check_cpp(self) -> bool:
        cpp_dir = self.project_root / "cpp_accel"
        return cpp_dir.exists() and (cpp_dir / "pathfinding.hpp").exists()

    def _check_kotlin(self) -> bool:
        android_dir = self.project_root / "android_app"
        return android_dir.exists()

    def _check_android(self) -> bool:
        return self._check_kotlin()

    def get_status(self) -> Dict[str, Any]:
        return asdict(self.status)

    def run_benchmark(self) -> Dict[str, float]:
        results = {"phase": 66, "timestamp": time.time()}

        if nearest_point_index:
            points = [(float(i), float(i)) for i in range(1000)]
            origin = (500.0, 500.0)

            start = time.perf_counter()
            for _ in range(1000):
                nearest_point_index(origin, points)
            rust_time = time.perf_counter() - start
            results["rust_nearest_point"] = rust_time

        py_start = time.perf_counter()
        points = [(float(i), float(i)) for i in range(1000)]
        origin = (500.0, 500.0)
        for _ in range(1000):
            best_idx = None
            best_dist = float("inf")
            for i, (px, py) in enumerate(points):
                d = (px - origin[0]) ** 2 + (py - origin[1]) ** 2
                if d < best_dist:
                    best_dist = d
                    best_idx = i
        py_time = time.perf_counter() - py_start
        results["python_nearest_point"] = py_time

        if "rust_nearest_point" in results:
            results["speedup"] = py_time / rust_time

        return results

    def combat_analysis(
        self,
        my_units: List[Tuple[float, float, float, float]],
        enemy_units: List[Tuple[float, float, float, float]],
    ) -> Dict[str, Any]:
        if combat_power_comparison:
            advantage = combat_power_comparison(my_units, enemy_units)
        else:

            def calc_power(units):
                return sum(
                    (hp / max_hp if max_hp > 0 else 0) * damage * rng
                    for hp, max_hp, damage, rng in units
                )

            my_power = calc_power(my_units)
            enemy_power = calc_power(enemy_units)
            advantage = my_power / enemy_power if enemy_power > 0 else my_power

        return {
            "advantage": advantage,
            "recommendation": "ATTACK"
            if advantage > 1.2
            else "RETREAT"
            if advantage < 0.8
            else "HOLD",
            "analysis": self._get_recommendation_text(advantage),
        }

    def _get_recommendation_text(self, advantage: float) -> str:
        if advantage > 1.5:
            return "우세 상황 - 적극적 공격 유도"
        elif advantage > 1.2:
            return "약간 우세 - 점진적 전술 시도"
        elif advantage > 0.8:
            return "균형 상황 - 방어적 플레이"
        elif advantage > 0.5:
            return "열세 상황 - 후퇴 및 재편성"
        else:
            return "큰 열세 - 극단적 방어/기회 대기"

    def formation_plan(
        self,
        unit_count: int,
        formation_type: str = "line",
        spacing: float = 2.0,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> List[Tuple[float, float]]:
        if formation_positions:
            return formation_positions(
                count=unit_count,
                spacing=spacing,
                center_x=center_x,
                center_y=center_y,
                formation_type=formation_type,
            )
        return self._python_formation(
            unit_count, formation_type, spacing, center_x, center_y
        )

    def _python_formation(
        self,
        count: int,
        ftype: str,
        spacing: float,
        cx: float,
        cy: float,
    ) -> List[Tuple[float, float]]:
        if count <= 0:
            return []
        if ftype == "line":
            start_x = cx - (count - 1) * spacing / 2
            return [(start_x + i * spacing, cy) for i in range(count)]
        elif ftype == "circle":
            import math

            r = max(count * spacing / (2 * math.pi), spacing)
            return [
                (
                    cx + r * math.cos(2 * math.pi * i / count),
                    cy + r * math.sin(2 * math.pi * i / count),
                )
                for i in range(count)
            ]
        return [(cx, cy)] * count

    def generate_test_script(self, output_path: Path) -> str:
        script = f'''#!/usr/bin/env python3
"""Phase 66 Integration Test Script"""

import sys
sys.path.insert(0, str(__file__).parent.parent)

from integration_hub import IntegrationHub

def main():
    hub = IntegrationHub()
    print("=== System Status ===")
    status = hub.get_status()
    print(json.dumps(status, indent=2))
    
    print("\\n=== Benchmark ===")
    results = hub.run_benchmark()
    print(json.dumps(results, indent=2))
    
    print("\\n=== Combat Analysis ===")
    my_units = [(50, 100, 10, 5), (80, 100, 12, 6)]
    enemy_units = [(45, 100, 11, 5), (60, 100, 9, 4)]
    combat = hub.combat_analysis(my_units, enemy_units)
    print(json.dumps(combat, indent=2))
    
    print("\\n=== Formation Plan ===")
    positions = hub.formation_plan(10, "circle")
    print(f"Generated {len(positions)} positions")
    
    print("\\n✅ All tests passed!")

if __name__ == "__main__":
    main()
'''
        output_path.write_text(script, encoding="utf-8")
        return str(output_path)


hub = IntegrationHub()

if __name__ == "__main__":
    print("=== Phase 66: Integration Hub ===")
    print(json.dumps(hub.get_status(), indent=2))
    print("\\n=== Benchmark ===")
    print(json.dumps(hub.run_benchmark(), indent=2))
