#!/usr/bin/env python3
"""
Automated Learning Loop - 리플레이 기반 학습 자동화
Phase 59: 승패 패턴 자동 분석 및 학습 포커스 추천

기능:
1. 리플레이 폴더에서 최신 리플레이 수집
2. 승패 패턴 분석
3. 학습 포커스 추천
4. 파라미터 자동 튜닝 제안
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class LearningLoop:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.replays_dir = project_root / "data" / "replays"
        self.reports_dir = project_root / "data" / "reports"
        self.scoring_dir = project_root / "data" / "scoring"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.scoring_dir.mkdir(parents=True, exist_ok=True)

    def find_replays(self, max_age_days: int = 7) -> List[Path]:
        """최근 리플레이 파일 수집"""
        if not self.replays_dir.exists():
            return []

        cutoff = datetime.now() - timedelta(days=max_age_days)
        replays = []

        for f in self.replays_dir.rglob("*.replay"):
            if f.stat().st_mtime > cutoff.timestamp():
                replays.append(f)

        for f in self.replays_dir.rglob("*.SC2Replay"):
            if f.stat().st_mtime > cutoff.timestamp():
                replays.append(f)

        return sorted(replays, key=lambda x: x.stat().st_mtime, reverse=True)

    def analyze_win_loss_pattern(self, replay_files: List[Path]) -> Dict:
        """승패 패턴 분석"""
        total = len(replay_files)
        if total == 0:
            return {
                "total_games": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "by_enemy_race": {},
                "error": "No replays found",
            }

        wins = losses = 0
        by_race = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0})

        for replay in replay_files[:100]:
            result = self._parse_replay_result(replay)
            if result:
                enemy = result.get("enemy_race", "Unknown")
                won = result.get("won", False)

                if won:
                    wins += 1
                    by_race[enemy]["wins"] += 1
                else:
                    losses += 1
                    by_race[enemy]["losses"] += 1

                by_race[enemy]["total"] += 1

        return {
            "total_games": total,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            "by_enemy_race": dict(by_race),
        }

    def _parse_replay_result(self, replay_path: Path) -> Optional[Dict]:
        """리플레이 결과 파싱 (간단 버전)"""
        try:
            return {
                "enemy_race": "Protoss",
                "won": "Defeat" not in str(replay_path),
                "duration_seconds": 600,
                "map": replay_path.stem,
            }
        except Exception:
            return None

    def generate_learning_focus(self, analysis: Dict) -> List[Dict]:
        """학습 포커스 추천 생성"""
        focuses = []

        win_rate = analysis.get("win_rate", 0)
        by_race = analysis.get("by_enemy_race", {})

        if win_rate < 30:
            focuses.append(
                {
                    "priority": "HIGH",
                    "category": "WIN_RATE",
                    "description": f"전체 승률이 {win_rate:.1f}%로 낮습니다. 기본 전략 복습 필요",
                    "action": "빌드오더 안정화 + 경제 관리 집중 훈련",
                }
            )

        for race, stats in by_race.items():
            if stats["total"] >= 3:
                race_win_rate = (
                    (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0
                )

                if race_win_rate < 25:
                    focuses.append(
                        {
                            "priority": "HIGH",
                            "category": f"VS_{race.upper()}",
                            "description": f"vs {race} 승률이 {race_win_rate:.1f}%로 매우 낮습니다",
                            "action": f"{race} 전 전용 카운터 빌드 훈련 필요",
                        }
                    )
                elif race_win_rate < 50:
                    focuses.append(
                        {
                            "priority": "MEDIUM",
                            "category": f"VS_{race.upper()}",
                            "description": f"vs {race} 승률이 {race_win_rate:.1f}%입니다",
                            "action": f"{race} 전 실전 마이크로 집중 훈련",
                        }
                    )

        if len(focuses) == 0 and analysis.get("total_games", 0) > 0:
            focuses.append(
                {
                    "priority": "LOW",
                    "category": "MAINTENANCE",
                    "description": "현재 승률이 양호합니다. 현재 전략 유지",
                    "action": "안정적인 플레이 유지 + 소폭 개선",
                }
            )

        return sorted(
            focuses,
            key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["priority"], 3),
        )

    def suggest_parameter_adjustments(self, analysis: Dict) -> Dict:
        """파라미터 조정 제안"""
        suggestions = {}

        win_rate = analysis.get("win_rate", 0)
        by_race = analysis.get("by_enemy_race", {})

        for race, stats in by_race.items():
            if stats["total"] >= 5:
                wr = (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0

                if wr < 20:
                    suggestions[f"counter_{race.lower()}"] = {
                        "type": "unit_ratio",
                        "current": "auto",
                        "suggested": "HIGH",
                        "reason": f"vs {race} 승률이 {wr:.1f}%로 낮아 카운터 유닛 비율 상향 필요",
                    }

        return suggestions

    def generate_training_plan(self, focuses: List[Dict]) -> Dict:
        """훈련 계획 생성"""
        plan = {"generated_at": self.timestamp, "focus_areas": [], "daily_routine": []}

        high_priority = [f for f in focuses if f["priority"] == "HIGH"]

        if high_priority:
            plan["daily_routine"] = [
                "1. 카운터 빌드 10게임 반복",
                "2. 마이크로 컨트롤 5게임",
                "3. 경제 관리 5게임",
                "4. 분석 및 리플레이 검토",
            ]

        for focus in focuses:
            plan["focus_areas"].append(
                {
                    "category": focus["category"],
                    "priority": focus["priority"],
                    "recommended_games": 15 if focus["priority"] == "HIGH" else 10,
                    "success_metric": f"{focus['category']} 승률 50% 이상",
                }
            )

        return plan

    def run_analysis(self, max_replays: int = 50) -> Dict:
        """전체 분석 실행"""
        print("=" * 60)
        print("Phase 59: 자동 학습 루프")
        print("=" * 60)

        print("\n[1/5] 리플레이 수집...")
        replays = self.find_replays()
        print(f"  최근 리플레이: {len(replays)}개 발견")

        print("\n[2/5] 승패 패턴 분석...")
        analysis = self.analyze_win_loss_pattern(replays[:max_replays])
        print(f"  총 게임: {analysis['total_games']}")
        print(f"  승리: {analysis['wins']} | 패배: {analysis['losses']}")
        print(f"  승률: {analysis['win_rate']:.1f}%")

        print("\n[3/5] 학습 포커스 생성...")
        focuses = self.generate_learning_focus(analysis)
        for i, f in enumerate(focuses, 1):
            print(f"  {i}. [{f['priority']}] {f['category']}: {f['description']}")

        print("\n[4/5] 파라미터 조정 제안...")
        params = self.suggest_parameter_adjustments(analysis)
        for key, val in params.items():
            print(f"  {key}: {val['reason'][:50]}...")

        print("\n[5/5] 훈련 계획 생성...")
        plan = self.generate_training_plan(focuses)
        print(f"  권장 일일 루틴: {len(plan['daily_routine'])}단계")

        result = {
            "timestamp": self.timestamp,
            "analysis": analysis,
            "learning_focuses": focuses,
            "parameter_suggestions": params,
            "training_plan": plan,
            "replays_analyzed": len(replays[:max_replays]),
        }

        return result

    def save_results(self, result: Dict):
        """결과 저장"""
        filename = f"learning_loop_{self.timestamp}.json"
        filepath = self.reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n결과 저장: {filepath}")

        latest = self.reports_dir / "learning_loop_latest.json"
        with open(latest, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"최신 결과: {latest}")

    def print_summary(self, result: Dict):
        """요약 출력"""
        analysis = result.get("analysis", {})
        focuses = result.get("learning_focuses", [])

        print("\n" + "=" * 60)
        print("학습 루프 요약")
        print("=" * 60)
        print(f"분석된 게임: {analysis.get('total_games', 0)}")
        print(f"승률: {analysis.get('win_rate', 0):.1f}%")
        print(f"학습 포커스: {len(focuses)}개")

        if focuses:
            print("\n상위 학습 포커스:")
            for f in focuses[:3]:
                print(f"  - [{f['priority']}] {f['category']}")

        plan = result.get("training_plan", {})
        if plan.get("daily_routine"):
            print("\n일일 훈련 루틴:")
            for r in plan["daily_routine"]:
                print(f"  {r}")


def main():
    project_root = Path(__file__).parent.parent.resolve()

    loop = LearningLoop(project_root)
    result = loop.run_analysis(max_replays=50)
    loop.save_results(result)
    loop.print_summary(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
