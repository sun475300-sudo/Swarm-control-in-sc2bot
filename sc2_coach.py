"""
#181: SC2 코칭 시스템 (SC2 Coach)

게임 로그를 분석하여 개선 제안을 생성하는 코칭 시스템.
"""
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("sc2_coach")


class SC2Coach:
    """SC2 코칭 시스템 — 게임 로그 분석 기반 개선 조언 생성

    게임 리플레이/로그 데이터를 분석하여 전략, 경제, 유닛 운용 등
    다양한 측면에서 개선 포인트를 제안한다.
    """

    # 분석 카테고리
    CATEGORIES = {
        "economy": "경제 관리",
        "army": "군대 운용",
        "macro": "매크로 (대규모 전략)",
        "micro": "마이크로 (유닛 컨트롤)",
        "timing": "타이밍",
        "scouting": "정찰",
        "defense": "방어",
        "expansion": "확장",
    }

    def __init__(self):
        """초기화"""
        self._project_root = Path(__file__).parent
        self._coaching_history: list = []
        self._known_patterns: list = self._load_patterns()

    def _load_patterns(self) -> list:
        """알려진 게임 패턴/문제 목록 로드"""
        return [
            {
                "pattern": r"supply.?block|supply.?cap|인구.?부족",
                "category": "macro",
                "advice": "인구수(Supply) 차단이 감지되었습니다. 오버로드를 미리 생산하세요. "
                          "50인구 이후에는 2~3마리씩 선행 생산이 필요합니다.",
                "severity": "high",
            },
            {
                "pattern": r"idle.?worker|유휴.?일꾼|일꾼.?대기",
                "category": "economy",
                "advice": "유휴 일꾼이 발견되었습니다. 일꾼은 항상 미네랄/가스 채취에 배정하세요. "
                          "할당키(F1)로 유휴 일꾼을 빠르게 확인할 수 있습니다.",
                "severity": "medium",
            },
            {
                "pattern": r"float.?mineral|미네랄.?과잉|mineral.?bank",
                "category": "economy",
                "advice": "미네랄이 과잉 축적되고 있습니다. 추가 해처리 확장 또는 "
                          "유닛 생산 시설을 늘려 자원을 효율적으로 사용하세요.",
                "severity": "high",
            },
            {
                "pattern": r"late.?expand|확장.?지연|늦은.?확장",
                "category": "expansion",
                "advice": "확장 타이밍이 늦습니다. 저그는 빠른 확장이 생명입니다. "
                          "해처리 퍼스트 또는 풀 후 해처리를 고려하세요.",
                "severity": "high",
            },
            {
                "pattern": r"no.?scout|정찰.?없|정찰.?부족",
                "category": "scouting",
                "advice": "정찰이 부족합니다. 오버로드와 저글링으로 상대 빌드를 반드시 확인하세요. "
                          "정보 없이는 올바른 대응이 불가능합니다.",
                "severity": "high",
            },
            {
                "pattern": r"army.?wipe|전멸|전군.?손실|all.?dead",
                "category": "army",
                "advice": "군대가 전멸했습니다. 전투 전 상대 구성을 확인하고, "
                          "불리한 교전은 피하세요. 소규모 견제 후 후퇴하는 전략을 연습하세요.",
                "severity": "critical",
            },
            {
                "pattern": r"drone.?rush|일꾼.?돌진",
                "category": "defense",
                "advice": "일꾼 러시에 대비하세요. 초반 저글링 2마리로 정찰하고 "
                          "스포닝 풀 완성 시점을 확인하세요.",
                "severity": "low",
            },
            {
                "pattern": r"miss.?inject|인젝트.?빠뜨|주입.?놓침",
                "category": "macro",
                "advice": "퀸 인젝트를 놓치고 있습니다. 라바 인젝트는 저그의 핵심 매크로입니다. "
                          "카메라 핫키 + 인젝트 단축키를 연습하세요.",
                "severity": "high",
            },
            {
                "pattern": r"bad.?engagement|잘못된.?교전|불리.?교전",
                "category": "micro",
                "advice": "불리한 교전이 감지되었습니다. 지형(초크포인트)을 활용하고 "
                          "서라운드가 가능한 위치에서 싸우세요.",
                "severity": "medium",
            },
            {
                "pattern": r"gas.?float|가스.?과잉",
                "category": "economy",
                "advice": "가스가 과잉 축적되고 있습니다. 뮤탈/울트라 같은 "
                          "가스 집약 유닛 테크로 전환하거나, 일꾼을 가스에서 빼세요.",
                "severity": "medium",
            },
        ]

    def get_coaching_advice(self, game_log: str) -> list:
        """게임 로그 분석 후 코칭 조언 생성

        Args:
            game_log: 게임 로그 텍스트 (봇 로그, 리플레이 분석 결과 등)

        Returns:
            list: 조언 딕셔너리 리스트
                [{'category': str, 'advice': str, 'severity': str}, ...]
        """
        if not game_log:
            return [{"category": "general", "advice": "게임 로그가 비어있습니다.", "severity": "info"}]

        advices = []
        log_lower = game_log.lower()

        # 패턴 매칭 기반 조언
        for pattern_info in self._known_patterns:
            if re.search(pattern_info["pattern"], log_lower, re.IGNORECASE):
                advices.append({
                    "category": pattern_info["category"],
                    "category_name": self.CATEGORIES.get(pattern_info["category"], pattern_info["category"]),
                    "advice": pattern_info["advice"],
                    "severity": pattern_info["severity"],
                })

        # 통계 기반 조언 추가
        stat_advices = self._analyze_statistics(game_log)
        advices.extend(stat_advices)

        # 조언이 없으면 기본 조언
        if not advices:
            advices.append({
                "category": "general",
                "category_name": "일반",
                "advice": "특별한 문제 패턴이 감지되지 않았습니다. "
                          "기본기를 꾸준히 연습하세요: 인젝트, 일꾼 생산, 확장 타이밍.",
                "severity": "info",
            })

        # 심각도 순 정렬
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        advices.sort(key=lambda a: severity_order.get(a["severity"], 99))

        # 코칭 기록
        self._coaching_history.append({
            "timestamp": datetime.now().isoformat(),
            "advice_count": len(advices),
            "categories": list(set(a["category"] for a in advices)),
        })

        return advices

    def _analyze_statistics(self, game_log: str) -> list:
        """로그에서 통계 추출 및 분석"""
        advices = []

        # 게임 시간 분석
        time_match = re.search(r"game.?time[:\s]+(\d+)[:\s]*(\d+)?", game_log, re.IGNORECASE)
        if time_match:
            minutes = int(time_match.group(1))
            if minutes < 5:
                advices.append({
                    "category": "timing",
                    "category_name": "타이밍",
                    "advice": f"게임이 {minutes}분 만에 종료되었습니다. "
                              "초반 러시에 취약한 빌드를 사용 중일 수 있습니다. "
                              "안전한 오프닝을 고려하세요.",
                    "severity": "high",
                })

        # 유닛 손실 분석
        lost_match = re.findall(r"lost[:\s]+(\d+)", game_log, re.IGNORECASE)
        if lost_match:
            total_lost = sum(int(x) for x in lost_match)
            if total_lost > 50:
                advices.append({
                    "category": "army",
                    "category_name": "군대 운용",
                    "advice": f"총 {total_lost}유닛이 손실되었습니다. "
                              "무리한 교전을 피하고, 유닛 보존을 우선시하세요.",
                    "severity": "medium",
                })

        return advices

    def analyze_bot_log(self) -> list:
        """프로젝트의 봇 로그 자동 분석

        Returns:
            list: 코칭 조언 리스트
        """
        bot_log_path = self._project_root / "wicked_zerg_challenger" / "logs" / "bot.log"
        if not bot_log_path.exists():
            return [{"category": "general", "advice": "봇 로그를 찾을 수 없습니다.", "severity": "info"}]

        try:
            with open(bot_log_path, "r", encoding="utf-8", errors="replace") as f:
                log_content = f.read()
            return self.get_coaching_advice(log_content)
        except Exception as e:
            return [{"category": "error", "advice": f"봇 로그 분석 실패: {e}", "severity": "high"}]

    def get_coaching_history(self) -> list:
        """코칭 히스토리"""
        return list(self._coaching_history)

    def format_advice(self, advices: list) -> str:
        """조언 리스트를 포맷된 문자열로 변환"""
        if not advices:
            return "코칭 조언 없음"

        lines = []
        lines.append("=" * 50)
        lines.append("  SC2 코칭 리포트")
        lines.append("=" * 50)

        severity_icons = {
            "critical": "[!!!]",
            "high": "[!!]",
            "medium": "[!]",
            "low": "[*]",
            "info": "[i]",
        }

        for i, advice in enumerate(advices, 1):
            icon = severity_icons.get(advice["severity"], "[?]")
            cat = advice.get("category_name", advice["category"])
            lines.append(f"\n{icon} #{i} [{cat}]")
            lines.append(f"    {advice['advice']}")

        lines.append("\n" + "=" * 50)
        return "\n".join(lines)


if __name__ == "__main__":
    coach = SC2Coach()

    # 테스트 로그
    test_log = """
    [12:03] supply blocked at 36/36
    [12:15] idle workers detected: 5
    [12:45] mineral bank: 2500
    [13:00] inject missed on hatchery #2
    """
    advices = coach.get_coaching_advice(test_log)
    print(coach.format_advice(advices))
