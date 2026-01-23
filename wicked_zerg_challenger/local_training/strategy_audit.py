# -*- coding: utf-8 -*-
"""
Strategy Audit - 전략 비교 분석

봇의 빌드 오더와 프로 게이머/학습된 빌드 오더를 비교 분석합니다.

주요 기능:
1. 봇 게임 로그 분석
2. 프로 빌드 오더와 비교
3. 차이점 및 개선점 도출
4. 리포트 생성
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 프로젝트 루트 추가
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class StrategyAudit:
    """전략 감사 및 비교 분석"""

    def __init__(self):
        self.project_root = project_root
        self.learned_builds_path = script_dir / "scripts" / "learned_build_orders.json"
        self.training_stats_path = project_root / "training_stats.json"
        self.report_dir = script_dir / "comparison_reports"

        # 기준 빌드 오더 (프로 게이머 기준)
        self.pro_build_timings = {
            "SpawningPool": 75,      # 서랄 기준: 17 드론 풀
            "Hatchery": 85,          # 자연 확장: 1:25
            "Extractor": 90,         # 가스 타이밍
            "Queen": 105,            # 첫 퀸
            "Zergling": 115,         # 저글링 시작
            "RoachWarren": 180,      # 3분 바퀴굴
            "Lair": 270,             # 4:30 레어
            "third_base": 210,       # 3:30 서드
            "HydraliskDen": 330,     # 5:30 히드라굴
        }

        # 비교 결과
        self.audit_results: Dict[str, Any] = {}

    def load_learned_builds(self) -> Dict[str, Any]:
        """학습된 빌드 오더 로드"""
        try:
            if self.learned_builds_path.exists():
                with open(self.learned_builds_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[AUDIT] Failed to load learned builds: {e}")
        return {}

    def load_training_stats(self) -> Dict[str, Any]:
        """훈련 통계 로드"""
        try:
            if self.training_stats_path.exists():
                with open(self.training_stats_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[AUDIT] Failed to load training stats: {e}")
        return {}

    def compare_build_timings(self, bot_timings: Dict[str, float]) -> Dict[str, Any]:
        """빌드 타이밍 비교"""
        comparison = {}

        for building, pro_time in self.pro_build_timings.items():
            bot_time = bot_timings.get(building, 0)

            if bot_time > 0:
                diff = bot_time - pro_time
                diff_percent = (diff / pro_time) * 100 if pro_time > 0 else 0

                status = "good" if abs(diff) < 15 else ("slow" if diff > 0 else "fast")

                comparison[building] = {
                    "pro_time": pro_time,
                    "bot_time": bot_time,
                    "diff_seconds": diff,
                    "diff_percent": diff_percent,
                    "status": status,
                    "recommendation": self._get_timing_recommendation(building, diff)
                }
            else:
                comparison[building] = {
                    "pro_time": pro_time,
                    "bot_time": 0,
                    "diff_seconds": 0,
                    "diff_percent": 0,
                    "status": "missing",
                    "recommendation": f"Add {building} to build order"
                }

        return comparison

    def _get_timing_recommendation(self, building: str, diff: float) -> str:
        """타이밍 개선 추천"""
        if abs(diff) < 15:
            return "Timing is optimal"

        if diff > 0:
            # 느림
            if building == "SpawningPool":
                return "Consider earlier pool (17 or 16 drone)"
            elif building == "Hatchery":
                return "Expand earlier for better economy"
            elif building == "Queen":
                return "Queen should be first priority after pool"
            elif building == "Lair":
                return "Start Lair earlier for tech advantage"
            else:
                return f"Build {building} {int(diff)}s earlier"
        else:
            # 빠름
            return f"Good aggressive timing, {int(-diff)}s ahead of standard"

    def compare_unit_composition(
        self,
        bot_units: Dict[str, float],
        learned_units: Dict[str, float]
    ) -> Dict[str, Any]:
        """유닛 조합 비교"""
        comparison = {}

        all_units = set(bot_units.keys()) | set(learned_units.keys())

        for unit in all_units:
            bot_ratio = bot_units.get(unit, 0)
            learned_ratio = learned_units.get(unit, 0)

            diff = bot_ratio - learned_ratio

            comparison[unit] = {
                "bot_ratio": bot_ratio,
                "learned_ratio": learned_ratio,
                "diff": diff,
                "recommendation": self._get_unit_recommendation(unit, diff)
            }

        return comparison

    def _get_unit_recommendation(self, unit: str, diff: float) -> str:
        """유닛 조합 추천"""
        if abs(diff) < 0.05:
            return "Balanced"

        if diff > 0:
            return f"Consider fewer {unit}s"
        else:
            return f"Consider more {unit}s"

    def analyze_win_rate(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """승률 분석"""
        total_games = stats.get("total_games", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)

        win_rate = (wins / total_games * 100) if total_games > 0 else 0

        # 종족별 승률
        vs_terran = stats.get("vs_terran", {})
        vs_protoss = stats.get("vs_protoss", {})
        vs_zerg = stats.get("vs_zerg", {})

        analysis = {
            "overall": {
                "total_games": total_games,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate
            },
            "vs_terran": self._analyze_matchup(vs_terran),
            "vs_protoss": self._analyze_matchup(vs_protoss),
            "vs_zerg": self._analyze_matchup(vs_zerg),
            "recommendations": self._get_win_rate_recommendations(win_rate, vs_terran, vs_protoss, vs_zerg)
        }

        return analysis

    def _analyze_matchup(self, matchup_stats: Dict[str, Any]) -> Dict[str, Any]:
        """매치업별 분석"""
        total = matchup_stats.get("total", 0)
        wins = matchup_stats.get("wins", 0)
        win_rate = (wins / total * 100) if total > 0 else 0

        return {
            "total_games": total,
            "wins": wins,
            "win_rate": win_rate,
            "status": "strong" if win_rate >= 50 else "weak"
        }

    def _get_win_rate_recommendations(
        self,
        overall: float,
        vs_t: Dict,
        vs_p: Dict,
        vs_z: Dict
    ) -> List[str]:
        """승률 기반 추천"""
        recommendations = []

        if overall < 30:
            recommendations.append("Focus on macro fundamentals: drone count, injection, creep spread")
            recommendations.append("Practice standard openers against AI before ladder")

        if overall < 50:
            recommendations.append("Review losing replays to identify common mistakes")

        # 종족별 추천
        t_rate = (vs_t.get("wins", 0) / vs_t.get("total", 1)) * 100 if vs_t.get("total", 0) > 0 else 50
        p_rate = (vs_p.get("wins", 0) / vs_p.get("total", 1)) * 100 if vs_p.get("total", 0) > 0 else 50
        z_rate = (vs_z.get("wins", 0) / vs_z.get("total", 1)) * 100 if vs_z.get("total", 0) > 0 else 50

        if t_rate < 40:
            recommendations.append("vs Terran: Focus on Roach/Ravager timing attacks, watch for hellion harass")
        if p_rate < 40:
            recommendations.append("vs Protoss: Scout for DT/Oracle, prepare Spore Crawlers")
        if z_rate < 40:
            recommendations.append("vs Zerg: Control creep spread, prepare for Baneling wars")

        return recommendations if recommendations else ["Keep practicing, win rate is good!"]

    def generate_report(self) -> str:
        """감사 리포트 생성"""
        learned_data = self.load_learned_builds()
        training_stats = self.load_training_stats()

        # 빌드 타이밍 비교
        bot_timings = learned_data.get("build_order_timings", {})
        timing_comparison = self.compare_build_timings(bot_timings)

        # 유닛 조합 비교
        bot_units = learned_data.get("unit_priorities", {})
        unit_comparison = self.compare_unit_composition(bot_units, self.get_pro_unit_composition())

        # 승률 분석
        win_analysis = self.analyze_win_rate(training_stats)

        # 리포트 생성
        report_lines = [
            "=" * 70,
            "STRATEGY AUDIT REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            "",
            "## 1. BUILD ORDER TIMING ANALYSIS",
            "-" * 40,
        ]

        for building, data in timing_comparison.items():
            status_icon = {"good": "+", "slow": "-", "fast": "*", "missing": "!"}.get(data["status"], "?")
            report_lines.append(
                f"[{status_icon}] {building}: Bot={data['bot_time']}s, Pro={data['pro_time']}s "
                f"(diff: {data['diff_seconds']:+.0f}s)"
            )
            if data["status"] != "good":
                report_lines.append(f"    -> {data['recommendation']}")

        report_lines.extend([
            "",
            "## 2. UNIT COMPOSITION ANALYSIS",
            "-" * 40,
        ])

        for unit, data in sorted(unit_comparison.items(), key=lambda x: abs(x[1]["diff"]), reverse=True)[:10]:
            report_lines.append(
                f"  {unit}: Bot={data['bot_ratio']:.1%}, Learned={data['learned_ratio']:.1%}"
            )

        report_lines.extend([
            "",
            "## 3. WIN RATE ANALYSIS",
            "-" * 40,
            f"  Overall: {win_analysis['overall']['win_rate']:.1f}% "
            f"({win_analysis['overall']['wins']}/{win_analysis['overall']['total_games']})",
            f"  vs Terran: {win_analysis['vs_terran']['win_rate']:.1f}%",
            f"  vs Protoss: {win_analysis['vs_protoss']['win_rate']:.1f}%",
            f"  vs Zerg: {win_analysis['vs_zerg']['win_rate']:.1f}%",
            "",
            "## 4. RECOMMENDATIONS",
            "-" * 40,
        ])

        for rec in win_analysis["recommendations"]:
            report_lines.append(f"  * {rec}")

        report_lines.extend([
            "",
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        report = "\n".join(report_lines)

        # 저장
        self.save_report(report)

        return report

    def get_pro_unit_composition(self) -> Dict[str, float]:
        """프로 게이머 유닛 조합 기준"""
        return {
            "Drone": 0.30,
            "Zergling": 0.20,
            "Roach": 0.15,
            "Queen": 0.10,
            "Hydralisk": 0.10,
            "Baneling": 0.05,
            "Ravager": 0.05,
            "Mutalisk": 0.03,
            "Lurker": 0.02,
        }

    def save_report(self, report: str) -> bool:
        """리포트 저장"""
        try:
            self.report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"audit_report_{timestamp}.txt"

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            # JSON 형식도 저장
            json_path = self.report_dir / f"audit_data_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.audit_results, f, indent=2, ensure_ascii=False)

            print(f"[AUDIT] Report saved to {report_path}")
            return True
        except Exception as e:
            print(f"[AUDIT] Failed to save report: {e}")
            return False

    def run(self) -> str:
        """메인 실행"""
        print("=" * 60)
        print("STRATEGY AUDIT")
        print("=" * 60)

        report = self.generate_report()
        print(report)

        return report


def main():
    """메인 함수"""
    audit = StrategyAudit()
    audit.run()


if __name__ == "__main__":
    main()
