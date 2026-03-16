# -*- coding: utf-8 -*-
"""
Tool Registry - JARVIS 도구 레지스트리 & 감사 로깅

기능:
1. 도구 사용 통계 (호출 수, 성공률, 평균 응답시간)
2. 감사 로그 (data/audit_log.jsonl)
3. 도구 메타데이터 관리
"""

import json
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger("jarvis.tool_registry")

_AUDIT_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_AUDIT_LOG_PATH = os.path.join(_AUDIT_LOG_DIR, "audit_log.jsonl")
_MAX_AUDIT_LOG_SIZE = 10 * 1024 * 1024  # 10MB


class ToolRegistry:
    """도구 사용 통계 및 감사 로그 관리"""

    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "success": 0, "fail": 0, "total_ms": 0.0}
        )
        self._start_time = time.time()
        os.makedirs(_AUDIT_LOG_DIR, exist_ok=True)

    def record_call(
        self,
        tool_name: str,
        user_id: str,
        success: bool,
        elapsed_ms: float = 0.0,
        error: str = "",
    ) -> None:
        """
        도구 호출 기록.

        Args:
            tool_name: 도구 이름
            user_id: 사용자 ID
            success: 성공 여부
            elapsed_ms: 응답 시간 (ms)
            error: 에러 메시지 (실패 시)
        """
        stats = self._stats[tool_name]
        stats["calls"] += 1
        if success:
            stats["success"] += 1
            stats["total_ms"] += elapsed_ms
        else:
            stats["fail"] += 1

        # 감사 로그 기록
        self._write_audit_log(tool_name, user_id, success, elapsed_ms, error)

    def _write_audit_log(
        self,
        tool_name: str,
        user_id: str,
        success: bool,
        elapsed_ms: float,
        error: str,
    ) -> None:
        """감사 로그를 JSONL 파일에 기록"""
        try:
            # 로그 파일 크기 체크 (10MB 초과 시 rotate)
            if os.path.exists(_AUDIT_LOG_PATH):
                if os.path.getsize(_AUDIT_LOG_PATH) > _MAX_AUDIT_LOG_SIZE:
                    self._rotate_audit_log()

            now_kst = datetime.now(
                timezone(timedelta(hours=9))
            ).strftime("%Y-%m-%d %H:%M:%S")

            entry = {
                "timestamp": now_kst,
                "tool": tool_name,
                "user_id": str(user_id),
                "success": success,
                "elapsed_ms": round(elapsed_ms, 1),
            }
            if error:
                entry["error"] = error[:200]

            with open(_AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        except (IOError, OSError):
            pass  # 로그 실패는 무시

    def _rotate_audit_log(self) -> None:
        """로그 파일 로테이션 (이전 파일을 .old로 이동)"""
        old_path = _AUDIT_LOG_PATH + ".old"
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(_AUDIT_LOG_PATH, old_path)
        except (IOError, OSError):
            pass

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        도구 사용 통계 반환.

        Args:
            tool_name: 특정 도구 (None이면 전체)

        Returns:
            통계 딕셔너리
        """
        if tool_name:
            s = self._stats.get(tool_name, {})
            if not s:
                return {"calls": 0, "success_rate": 0, "avg_ms": 0}
            return {
                "calls": s["calls"],
                "success_rate": (
                    round(s["success"] / s["calls"] * 100, 1) if s["calls"] > 0 else 0
                ),
                "avg_ms": (
                    round(s["total_ms"] / s["success"], 1) if s["success"] > 0 else 0
                ),
            }

        # 전체 통계
        result = {}
        for name, s in self._stats.items():
            result[name] = {
                "calls": s["calls"],
                "success_rate": (
                    round(s["success"] / s["calls"] * 100, 1) if s["calls"] > 0 else 0
                ),
                "avg_ms": (
                    round(s["total_ms"] / s["success"], 1) if s["success"] > 0 else 0
                ),
            }
        return result

    def get_summary(self) -> str:
        """도구 사용 요약 문자열 생성"""
        total_calls = sum(s["calls"] for s in self._stats.values())
        total_success = sum(s["success"] for s in self._stats.values())
        total_fail = sum(s["fail"] for s in self._stats.values())

        uptime = time.time() - self._start_time
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"

        lines = [
            f"도구 레지스트리 요약 (가동시간: {uptime_str})",
            f"총 호출: {total_calls:,} | 성공: {total_success:,} | 실패: {total_fail:,}",
            f"성공률: {total_success / total_calls * 100:.1f}%" if total_calls > 0 else "성공률: N/A",
            "",
        ]

        # Top 5 도구
        sorted_tools = sorted(
            self._stats.items(), key=lambda x: x[1]["calls"], reverse=True
        )[:5]
        if sorted_tools:
            lines.append("인기 도구 Top 5:")
            for name, s in sorted_tools:
                rate = round(s["success"] / s["calls"] * 100) if s["calls"] > 0 else 0
                avg = round(s["total_ms"] / s["success"], 1) if s["success"] > 0 else 0
                lines.append(f"  {name}: {s['calls']}회 ({rate}% 성공, 평균 {avg}ms)")

        return "\n".join(lines)

    def get_recent_audit_entries(self, count: int = 20) -> list:
        """최근 감사 로그 엔트리 반환"""
        entries = []
        try:
            if not os.path.exists(_AUDIT_LOG_PATH):
                return []
            with open(_AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            for line in all_lines[-count:]:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except (IOError, OSError, json.JSONDecodeError):
            pass
        return entries


# 싱글턴 인스턴스
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """ToolRegistry 싱글턴 반환"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
