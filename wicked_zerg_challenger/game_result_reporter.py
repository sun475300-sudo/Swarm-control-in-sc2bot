# -*- coding: utf-8 -*-
"""
Game Result Reporter - 경기 결과 자동 요약 보고서

Phase 22: 모든 게임 데이터를 종합하여 사후 분석 보고서 생성.

Features:
- 경기 타임라인 요약 (주요 이벤트)
- 확장/테크 타이밍 분석
- 전투 분석 (교전 승패)
- 경제 그래프 요약 (자원 추이)
- 승패 원인 분석
- 개선 제안
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime


class GameResultReporter:
    """경기 결과 자동 요약 보고서 생성"""

    def __init__(self, bot=None):
        self.bot = bot
        self.report_dir = "data/reports"

    def generate_report(self, game_data: Dict, analytics_data: Dict = None) -> str:
        """
        종합 경기 결과 보고서 생성.

        Args:
            game_data: GameDataLogger.game_data (raw) 또는 정규화된 dict
            analytics_data: GameAnalytics의 추가 분석 데이터

        Returns:
            str: 포맷된 보고서 텍스트
        """
        # GameDataLogger.game_data 포맷이면 정규화
        normalized = self._normalize_data(game_data)

        report_lines = []

        # === 헤더 ===
        result = normalized.get("result", "UNKNOWN")
        game_time = normalized.get("game_time", 0)
        opponent_race = normalized.get("opponent_race", "Unknown")
        map_name = normalized.get("map_name", "Unknown")

        result_emoji = "VICTORY" if result.upper() in ("WIN", "VICTORY") else "DEFEAT"

        report_lines.append("=" * 60)
        report_lines.append(f"  GAME RESULT REPORT - {result_emoji}")
        report_lines.append("=" * 60)
        report_lines.append(f"  Map: {map_name}")
        report_lines.append(f"  Opponent: {opponent_race}")
        report_lines.append(f"  Duration: {self._format_time(game_time)}")
        report_lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report_lines.append("")

        # === 1. 타임라인 요약 ===
        report_lines.append("--- TIMELINE ---")
        timeline = self._build_timeline(normalized)
        if timeline:
            for event in timeline:
                report_lines.append(f"  [{self._format_time(event['time'])}] {event['event']}")
        else:
            report_lines.append("  No timeline data available")
        report_lines.append("")

        # === 2. 경제 분석 ===
        report_lines.append("--- ECONOMY ---")
        economy = self._analyze_economy(normalized)
        for line in economy:
            report_lines.append(f"  {line}")
        report_lines.append("")

        # === 3. 확장/테크 타이밍 ===
        report_lines.append("--- TIMINGS ---")
        timings = self._analyze_timings(normalized)
        for line in timings:
            report_lines.append(f"  {line}")
        report_lines.append("")

        # === 4. 전투 분석 ===
        report_lines.append("--- COMBAT ---")
        combat = self._analyze_combat(normalized)
        for line in combat:
            report_lines.append(f"  {line}")
        report_lines.append("")

        # === 5. 유닛 조합 분석 ===
        report_lines.append("--- UNIT COMPOSITION ---")
        comp = self._analyze_composition(normalized)
        for line in comp:
            report_lines.append(f"  {line}")
        report_lines.append("")

        # === 6. 승패 원인 ===
        report_lines.append("--- RESULT ANALYSIS ---")
        if analytics_data:
            defeat_reason = analytics_data.get("defeat_reason", "")
            if defeat_reason:
                report_lines.append(f"  Defeat Reason: {defeat_reason}")
        causes = self._analyze_result_causes(normalized, result)
        for line in causes:
            report_lines.append(f"  {line}")
        report_lines.append("")

        # === 7. 개선 제안 ===
        report_lines.append("--- IMPROVEMENT SUGGESTIONS ---")
        suggestions = self._generate_suggestions(normalized, result)
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"  {i}. {suggestion}")
        report_lines.append("")

        # === 8. 통계 요약 ===
        report_lines.append("--- FINAL STATS ---")
        stats = normalized.get("final_stats", {})
        report_lines.append(f"  Workers: {stats.get('worker_count', '?')}")
        report_lines.append(f"  Army Supply: {stats.get('army_supply', '?')}")
        report_lines.append(f"  Bases: {stats.get('base_count', '?')}")
        report_lines.append(f"  Minerals: {stats.get('minerals', '?')}")
        report_lines.append(f"  Vespene: {stats.get('vespene', '?')}")
        report_lines.append("")

        report_lines.append("=" * 60)

        report_text = "\n".join(report_lines)

        # 파일 저장
        self._save_report(report_text, normalized)

        return report_text

    def _normalize_data(self, game_data: Dict) -> Dict:
        """
        GameDataLogger.game_data 포맷을 리포터 표준 포맷으로 정규화.

        GameDataLogger format:
            meta: {map_name, opponent_race, ...}
            game_result: {result, duration, final_supply, final_minerals, ...}
            build_order: [{time, supply, unit_type, ...}]
            expansions: [{time, expansion_number, ...}]
            engagements: [{time, supply_lost, remaining_army, ...}]
            resource_snapshots: [{time, minerals, vespene, workers, ...}]
            unit_production: [{time, unit_type, supply}]
            tech_upgrades: [{time, building, ...}]
            harassment: [{time, our_units, target_structure, ...}]

        Normalized format (what reporter methods expect):
            result, game_time, opponent_race, map_name
            build_orders, expansions, engagements, resource_snapshots
            unit_production (dict: name -> count), tech_timings, harassment_events
            final_stats: {worker_count, army_supply, base_count, minerals, vespene}
        """
        # Already normalized? (has 'result' at top level)
        if "result" in game_data and "meta" not in game_data:
            return game_data

        normalized = {}

        # --- Header fields ---
        meta = game_data.get("meta", {})
        game_result = game_data.get("game_result", {})

        normalized["result"] = game_result.get("result", "UNKNOWN")
        normalized["game_time"] = game_result.get("duration", 0)
        normalized["opponent_race"] = meta.get("opponent_race", "Unknown").replace("Race.", "")
        normalized["map_name"] = meta.get("map_name", "Unknown")

        # --- Build orders ---
        raw_bo = game_data.get("build_order", [])
        normalized["build_orders"] = [
            {
                "time": bo.get("time", 0),
                "unit": bo.get("unit_type", "Unknown"),
                "supply": bo.get("supply", "?"),
            }
            for bo in raw_bo
        ]

        # --- Expansions ---
        normalized["expansions"] = game_data.get("expansions", [])

        # --- Engagements (supply_lost -> army_lost) ---
        raw_eng = game_data.get("engagements", [])
        normalized["engagements"] = [
            {
                "time": e.get("time", 0),
                "army_lost": e.get("supply_lost", e.get("army_lost", 0)),
                "remaining_army": e.get("remaining_army", 0),
            }
            for e in raw_eng
        ]

        # --- Resource snapshots ---
        normalized["resource_snapshots"] = game_data.get("resource_snapshots", [])

        # --- Unit production (list -> dict of counts) ---
        raw_prod = game_data.get("unit_production", [])
        if isinstance(raw_prod, list):
            prod_counts = {}
            for p in raw_prod:
                unit_type = p.get("unit_type", "Unknown")
                prod_counts[unit_type] = prod_counts.get(unit_type, 0) + 1
            normalized["unit_production"] = prod_counts
        else:
            normalized["unit_production"] = raw_prod

        # --- Tech timings ---
        raw_tech = game_data.get("tech_upgrades", [])
        normalized["tech_timings"] = [
            {
                "name": t.get("building", t.get("name", "?")),
                "time": t.get("time", 0),
            }
            for t in raw_tech
        ]

        # --- Upgrade timings ---
        normalized["upgrade_timings"] = game_data.get("upgrade_sequence", [])

        # --- Harassment events ---
        raw_harass = game_data.get("harassment", [])
        normalized["harassment_events"] = [
            {
                "time": h.get("time", 0),
                "type": h.get("target_structure", "Unknown"),
            }
            for h in raw_harass
        ]

        # --- Final stats ---
        snapshots = normalized["resource_snapshots"]
        last_snapshot = snapshots[-1] if snapshots else {}
        normalized["final_stats"] = {
            "worker_count": last_snapshot.get("workers", game_result.get("final_workers", 0)),
            "army_supply": last_snapshot.get("supply_army", game_result.get("final_supply", 0)),
            "base_count": last_snapshot.get("bases", game_result.get("final_bases", 0)),
            "minerals": game_result.get("final_minerals", last_snapshot.get("minerals", 0)),
            "vespene": game_result.get("final_vespene", last_snapshot.get("vespene", 0)),
        }

        return normalized

    def _build_timeline(self, game_data: Dict) -> List[Dict]:
        """주요 이벤트 타임라인 구성"""
        events = []

        # 빌드 오더 이벤트
        build_orders = game_data.get("build_orders", [])
        for bo in build_orders:
            events.append({
                "time": bo.get("time", 0),
                "event": f"Build: {bo.get('unit', 'Unknown')} (Supply {bo.get('supply', '?')})"
            })

        # 확장 이벤트
        expansions = game_data.get("expansions", [])
        for i, exp in enumerate(expansions):
            events.append({
                "time": exp.get("time", 0),
                "event": f"Expansion #{i+1} started"
            })

        # 교전 이벤트
        engagements = game_data.get("engagements", [])
        for eng in engagements:
            army_lost = eng.get("army_lost", 0)
            events.append({
                "time": eng.get("time", 0),
                "event": f"Engagement: Lost {army_lost} supply"
            })

        # 견제 이벤트
        harassment = game_data.get("harassment_events", [])
        for h in harassment:
            events.append({
                "time": h.get("time", 0),
                "event": f"Harassment: {h.get('type', 'Unknown')}"
            })

        # 시간순 정렬
        events.sort(key=lambda e: e["time"])

        # 최대 20개 이벤트
        return events[:20]

    def _analyze_economy(self, game_data: Dict) -> List[str]:
        """경제 분석"""
        lines = []
        snapshots = game_data.get("resource_snapshots", [])

        if not snapshots:
            lines.append("No resource data available")
            return lines

        # 최대 자원 시점
        max_minerals = max((s.get("minerals", 0) for s in snapshots), default=0)
        max_vespene = max((s.get("vespene", 0) for s in snapshots), default=0)
        max_workers = max((s.get("workers", 0) for s in snapshots), default=0)

        lines.append(f"Peak Minerals: {max_minerals}")
        lines.append(f"Peak Vespene: {max_vespene}")
        lines.append(f"Peak Workers: {max_workers}")

        # 자원 낭비 감지 (미네랄 > 1000 이상인 시간)
        high_mineral_time = sum(
            1 for s in snapshots if s.get("minerals", 0) > 1000
        )
        if high_mineral_time > 0:
            lines.append(f"High mineral periods (>1000): {high_mineral_time} snapshots")
            lines.append("  -> Consider spending faster or adding production")

        return lines

    def _analyze_timings(self, game_data: Dict) -> List[str]:
        """확장/테크 타이밍 분석"""
        lines = []

        # 확장 타이밍
        expansions = game_data.get("expansions", [])
        benchmarks = {
            1: 60,   # 1분 멀티
            2: 240,  # 4분 셋째
            3: 360,  # 6분 넷째
        }

        for i, exp in enumerate(expansions):
            exp_time = exp.get("time", 0)
            target = benchmarks.get(i, None)
            status = ""
            if target:
                diff = exp_time - target
                if diff <= 10:
                    status = "(ON TIME)"
                elif diff <= 30:
                    status = f"(+{int(diff)}s SLIGHTLY LATE)"
                else:
                    status = f"(+{int(diff)}s LATE)"
            lines.append(f"Expansion #{i+1}: {self._format_time(exp_time)} {status}")

        # 테크 타이밍
        tech_timings = game_data.get("tech_timings", [])
        for tech in tech_timings:
            lines.append(f"Tech: {tech.get('name', '?')} at {self._format_time(tech.get('time', 0))}")

        # 업그레이드 타이밍
        upgrade_timings = game_data.get("upgrade_timings", [])
        for up in upgrade_timings:
            lines.append(f"Upgrade: {up.get('name', '?')} at {self._format_time(up.get('time', 0))}")

        if not lines:
            lines.append("No timing data available")

        return lines

    def _analyze_combat(self, game_data: Dict) -> List[str]:
        """전투 분석"""
        lines = []
        engagements = game_data.get("engagements", [])

        if not engagements:
            lines.append("No engagement data recorded")
            return lines

        total_lost = sum(e.get("army_lost", 0) for e in engagements)
        lines.append(f"Total Engagements: {len(engagements)}")
        lines.append(f"Total Army Supply Lost: {total_lost}")

        # 가장 큰 교전
        if engagements:
            worst = max(engagements, key=lambda e: e.get("army_lost", 0))
            lines.append(f"Biggest Loss: {worst.get('army_lost', 0)} supply at {self._format_time(worst.get('time', 0))}")

        return lines

    def _analyze_composition(self, game_data: Dict) -> List[str]:
        """유닛 조합 분석"""
        lines = []
        production = game_data.get("unit_production", {})

        if not production:
            lines.append("No unit production data")
            return lines

        # dict (name -> count)
        if isinstance(production, dict):
            sorted_units = sorted(production.items(), key=lambda x: x[1], reverse=True)
            for unit_name, count in sorted_units[:8]:
                lines.append(f"{unit_name}: {count} produced")
        # list (fallback)
        elif isinstance(production, list):
            from collections import Counter
            counts = Counter(p.get("unit_type", "?") for p in production)
            for unit_name, count in counts.most_common(8):
                lines.append(f"{unit_name}: {count} produced")

        return lines

    def _analyze_result_causes(self, game_data: Dict, result: str) -> List[str]:
        """승패 원인 분석"""
        lines = []
        game_time = game_data.get("game_time", 0)
        final_stats = game_data.get("final_stats", {})

        if result.upper() in ("WIN", "VICTORY"):
            if game_time < 300:
                lines.append("Quick victory (early game dominance)")
            elif game_time < 600:
                lines.append("Mid-game victory")
            else:
                lines.append("Late-game victory (sustained advantage)")

            army = final_stats.get("army_supply", 0)
            if army > 100:
                lines.append("Strong army supply at game end")
        else:
            # 패배 분석
            workers = final_stats.get("worker_count", 0)
            army = final_stats.get("army_supply", 0)
            bases = final_stats.get("base_count", 0)

            if game_time < 180:
                lines.append("EARLY DEFEAT: Possible rush defense failure")
            elif workers < 10:
                lines.append("Economy collapsed - workers lost")
            elif army < 10:
                lines.append("Army wiped out - need better engagements")
            elif bases <= 1:
                lines.append("Contained to one base - expansion denied")

            # 자원 분석
            minerals = final_stats.get("minerals", 0)
            if minerals > 2000:
                lines.append(f"Floating {minerals} minerals at death - spending issue")

        return lines

    def _generate_suggestions(self, game_data: Dict, result: str) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        game_time = game_data.get("game_time", 0)
        final_stats = game_data.get("final_stats", {})
        snapshots = game_data.get("resource_snapshots", [])
        engagements = game_data.get("engagements", [])
        expansions = game_data.get("expansions", [])

        # 1. 확장 타이밍
        if expansions:
            first_exp = expansions[0].get("time", 999)
            if first_exp > 90:
                suggestions.append(f"Natural expansion at {int(first_exp)}s - aim for sub-60s with Hatch First build")

        # 2. 자원 낭비
        high_mineral = any(s.get("minerals", 0) > 1500 for s in snapshots)
        if high_mineral:
            suggestions.append("Mineral bank exceeded 1500 - add more production or expand")

        # 3. 교전 손실
        if engagements:
            big_losses = [e for e in engagements if e.get("army_lost", 0) > 30]
            if len(big_losses) >= 2:
                suggestions.append("Multiple large army losses - consider better engagement timing")

        # 4. 일꾼 수
        workers = final_stats.get("worker_count", 0)
        bases = final_stats.get("base_count", 0)
        if workers < bases * 16 and game_time > 300:
            suggestions.append("Worker count below optimal - prioritize drone production")

        # 5. 빠른 패배
        if result.upper() not in ("WIN", "VICTORY") and game_time < 240:
            suggestions.append("Lost before 4 minutes - review early defense (spine crawlers, queens, zerglings)")

        # 6. 긴 게임 패배
        if result.upper() not in ("WIN", "VICTORY") and game_time > 600:
            suggestions.append("Late game loss - check tech transitions and army composition")

        if not suggestions:
            suggestions.append("Game played well! Continue practicing current build")

        return suggestions

    def _format_time(self, seconds: float) -> str:
        """초를 M:SS 형식으로 변환"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes}:{secs:02d}"

    def _save_report(self, report_text: str, game_data: Dict):
        """보고서 파일 저장"""
        try:
            os.makedirs(self.report_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result = game_data.get("result", "unknown")
            filename = f"report_{timestamp}_{result}.txt"
            filepath = os.path.join(self.report_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_text)

            print(f"[REPORT] Saved to {filepath}")
        except (IOError, OSError) as e:
            print(f"[REPORT] Failed to save: {e}")

    def generate_quick_summary(self, game_data: Dict) -> str:
        """
        간단 한줄 요약 (Discord 전송용)
        """
        normalized = self._normalize_data(game_data)
        result = normalized.get("result", "?")
        game_time = normalized.get("game_time", 0)
        opponent = normalized.get("opponent_race", "?")
        map_name = normalized.get("map_name", "?")
        stats = normalized.get("final_stats", {})

        return (
            f"{'WIN' if result.upper() in ('WIN','VICTORY') else 'LOSS'} "
            f"vs {opponent} on {map_name} "
            f"({self._format_time(game_time)}) "
            f"| Workers:{stats.get('worker_count','?')} "
            f"Army:{stats.get('army_supply','?')} "
            f"Bases:{stats.get('base_count','?')}"
        )
