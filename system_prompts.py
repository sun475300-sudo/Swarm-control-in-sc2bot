# -*- coding: utf-8 -*-
"""
System Prompts Module - JARVIS AI 시스템 프롬프트 모듈화

역할별 프롬프트 구성:
- 기본 (Default): 범용 AI 비서
- 트레이더 (Trader): 암호화폐/금융 전문
- 개발자 (Developer): 코딩/시스템 전문
- 분석가 (Analyst): 데이터/전략 분석

도구 카탈로그 자동 생성 기능 포함
"""

import time as _time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional


# ── 도구 카탈로그 ──

TOOL_CATALOG: Dict[str, Dict[str, str]] = {
    # 검색 & 정보
    "search_web": {"args": "검색어", "desc": "웹 검색", "category": "info"},
    "get_weather": {"args": "지역", "desc": "날씨 조회", "category": "info"},
    "get_fortune": {"args": "none", "desc": "오늘의 운세", "category": "info"},
    "translate": {"args": "텍스트|대상언어|원본언어", "desc": "번역", "category": "info"},
    "calculate": {"args": "수식", "desc": "계산기", "category": "info"},

    # SC2
    "get_sc2_stats": {"args": "none", "desc": "SC2 전적", "category": "sc2"},
    "analyze_replay": {"args": "리플레이파일경로", "desc": "리플레이 분석", "category": "sc2"},
    "list_replays": {"args": "none", "desc": "SC2 리플레이 목록", "category": "sc2"},
    "sc2_coaching": {"args": "none", "desc": "SC2 실시간 코칭", "category": "sc2"},
    "track_ladder": {"args": "플레이어이름|서버", "desc": "래더 추적", "category": "sc2"},

    # 시스템
    "get_system_status": {"args": "none", "desc": "PC 상태", "category": "system"},
    "scan_screen": {"args": "none", "desc": "화면 AI 분석", "category": "system"},
    "run_program": {"args": "프로그램명", "desc": "프로그램 실행", "category": "system"},
    "kill_process": {"args": "PID번호", "desc": "프로세스 종료", "category": "system"},
    "pc_control": {"args": "action|value", "desc": "PC 원격제어", "category": "system"},
    "search_files": {"args": "디렉토리|패턴", "desc": "파일 검색", "category": "system"},
    "ssh_execute": {"args": "user@host|명령어", "desc": "SSH 원격 실행", "category": "system"},

    # 암호화폐
    "get_crypto_price": {"args": "코인심볼", "desc": "코인 시세", "category": "crypto"},
    "portfolio": {"args": "none", "desc": "포트폴리오 요약", "category": "crypto"},
    "recent_trades": {"args": "none", "desc": "최근 거래 내역", "category": "crypto"},
    "trade_stats": {"args": "period", "desc": "매매 통계", "category": "crypto"},
    "analyze_coin": {"args": "KRW-BTC", "desc": "코인 상세 분석", "category": "crypto"},
    "auto_trade": {"args": "start|stop|status", "desc": "자동 매매", "category": "crypto"},
    "pending_orders": {"args": "none", "desc": "대기 주문", "category": "crypto"},
    "price_alert": {"args": "코인|목표가격", "desc": "가격 도달 알림 설정", "category": "crypto"},

    # 메모리 & 비서
    "remember": {"args": "키|값", "desc": "기억 저장", "category": "productivity"},
    "search_memory": {"args": "검색어", "desc": "메모리 검색", "category": "productivity"},
    "check_git": {"args": "옵션", "desc": "Git 상태", "category": "productivity"},
    "bot_status": {"args": "none", "desc": "봇 상태", "category": "productivity"},

    # 캘린더 & 노트
    "get_today_events": {"args": "none", "desc": "오늘 일정", "category": "productivity"},
    "get_upcoming_events": {"args": "일수", "desc": "다가오는 일정", "category": "productivity"},
    "create_event": {"args": "제목|시작|종료", "desc": "일정 생성", "category": "productivity"},
    "save_note": {"args": "제목|내용", "desc": "Notion 메모", "category": "productivity"},
    "search_notes": {"args": "검색어", "desc": "메모 검색", "category": "productivity"},
    "list_notes": {"args": "none", "desc": "최근 메모", "category": "productivity"},

    # Agentic (코드/파일)
    "execute_terminal_command": {"args": "명령어", "desc": "터미널 명령 실행", "category": "agentic"},
    "execute_python_code": {"args": "파이썬코드", "desc": "Python 코드 실행", "category": "agentic"},
    "read_file": {"args": "파일경로", "desc": "파일 읽기", "category": "agentic"},
    "write_file": {"args": "파일경로|내용", "desc": "파일 쓰기", "category": "agentic"},
    "edit_file": {"args": "파일경로|찾을내용|바꿀내용", "desc": "파일 수정", "category": "agentic"},
    "list_dir": {"args": "폴더경로", "desc": "디렉토리 목록", "category": "agentic"},

    # PC 제어
    "pc_mouse_move": {"args": "x|y|duration", "desc": "마우스 이동", "category": "pc_control"},
    "pc_mouse_click": {"args": "button|clicks", "desc": "마우스 클릭", "category": "pc_control"},
    "pc_keyboard_type": {"args": "텍스트", "desc": "키보드 입력", "category": "pc_control"},
    "pc_keyboard_press": {"args": "조합키", "desc": "키 조합", "category": "pc_control"},

    # OpenClaw
    "openclaw_weather": {"args": "지역", "desc": "OpenClaw 날씨 상세", "category": "openclaw"},
    "openclaw_youtube": {"args": "검색어", "desc": "YouTube 검색", "category": "openclaw"},
    "openclaw_summarize": {"args": "URL", "desc": "웹페이지/영상 요약", "category": "openclaw"},
    "openclaw_news": {"args": "주제", "desc": "최신 뉴스", "category": "openclaw"},
    "openclaw_exchange": {"args": "USD|KRW", "desc": "환율 조회", "category": "openclaw"},
    "openclaw_stock": {"args": "종목코드", "desc": "주식 분석", "category": "openclaw"},
    "openclaw_image_gen": {"args": "프롬프트", "desc": "AI 이미지 생성", "category": "openclaw"},
    "openclaw_email": {"args": "수신자|제목|본문", "desc": "이메일 전송", "category": "openclaw"},
    "openclaw_notion": {"args": "제목|내용", "desc": "Notion 페이지", "category": "openclaw"},
    "openclaw_github": {"args": "작업|저장소", "desc": "GitHub 관리", "category": "openclaw"},
    "openclaw_coding": {"args": "작업설명", "desc": "코딩 에이전트", "category": "openclaw"},
    "openclaw_browser": {"args": "URL|작업", "desc": "웹 자동화", "category": "openclaw"},
    "openclaw_cron": {"args": "이름|일정|메시지", "desc": "예약 작업", "category": "openclaw"},
    "openclaw_transcribe": {"args": "오디오경로", "desc": "음성→텍스트", "category": "openclaw"},
    "openclaw_calendar": {"args": "today|create|week", "desc": "일정 관리", "category": "openclaw"},
}


# ── 도메인별 추가 지시사항 (AgentRouter 연동) ──

DOMAIN_INSTRUCTIONS: Dict[str, str] = {
    "sc2": "SC2 전문. 전략/빌드/저그 코칭.",
    "crypto": "암호화폐. 리스크 경고 필수.",
    "system": "시스템 관리. 위험 작업 사전 확인.",
    "briefing": "간결한 브리핑.",
    "productivity": "일정/메모. KST 기준.",
    "pc_control": "PC 제어. 단계별 확인.",
    "general": "범용 대화.",
}


_tool_list_cache: Dict[str, str] = {}
_tool_cache_ts: float = 0.0
_TOOL_CACHE_TTL: float = 3600.0  # 1시간 TTL

# 카테고리 → 한국어 레이블
_CATEGORY_LABELS: Dict[str, str] = {
    "info": "검색&정보",
    "sc2": "SC2",
    "system": "시스템",
    "crypto": "암호화폐",
    "productivity": "메모리&비서",
    "agentic": "코드&파일",
    "pc_control": "PC제어",
    "openclaw": "OpenClaw",
}


def generate_tool_list(categories: Optional[List[str]] = None) -> str:
    """도구 카탈로그를 카테고리별 그룹으로 생성 (TTL 캐시 적용)."""
    global _tool_cache_ts
    now = _time.monotonic()
    if now - _tool_cache_ts > _TOOL_CACHE_TTL:
        _tool_list_cache.clear()
        _tool_cache_ts = now

    cache_key = ",".join(sorted(categories)) if categories else "__all__"
    if cache_key in _tool_list_cache:
        return _tool_list_cache[cache_key]

    # 카테고리별 그룹핑
    groups: Dict[str, List[str]] = {}
    for name, info in TOOL_CATALOG.items():
        cat = info["category"]
        if categories and cat not in categories:
            continue
        groups.setdefault(cat, []).append(f"{name}({info['args']})")

    lines = []
    for cat, label in _CATEGORY_LABELS.items():
        if cat in groups:
            lines.append(f"[{label}] {', '.join(groups[cat])}")
    result = "\n".join(lines)
    _tool_list_cache[cache_key] = result
    return result


def clear_tool_cache():
    """도구 캐시를 강제 무효화."""
    global _tool_cache_ts
    _tool_list_cache.clear()
    _tool_cache_ts = 0.0


# ── 역할별 시스템 프롬프트 ──

# SOUL.md 기반 JARVIS 정체성 (SOUL.md 내용 통합)
_JARVIS_IDENTITY = (
    "[절대 지시사항]\n"
    "당신은 J.A.R.V.I.S., 장선우 사령관의 AI 부관입니다.\n"
    "사령관: 육군 제53보병사단 통신병 출신, 드론기계학 전공.\n"
    "말투: 합쇼체, 군대식, 통신 프로토콜 준수. 호칭: 사령관님.\n"
    "★ 민간 호칭(사장님, 고객님, 선생님 등) 절대 금지. 이모지 사용 금지. ★\n"
    "전문: Swarm-Net 드론, SC2 저그봇 RL, 시스템 운용, 암호화폐.\n"
    "응답규칙: 간결. 상세 요청 시에만 길게.\n"
    "기능 설명 요청 시: MCP 도구를 작전 브리핑 형식으로 카테고리별 상세 보고.\n"
    "금지: 파괴적 명령·금융거래는 사령관 승인 없이 불가. 비밀정보 노출 금지.\n"
)

_TOOL_FORMAT_INSTRUCTIONS = (
    "\n[도구 호출 형식]\n"
    "도구가 필요하면 응답의 **마지막 줄에만** 아래 형식으로 출력하세요:\n"
    "TOOL:도구명:인자\n"
    "인자가 여러 개면 `|`로 구분: TOOL:도구명:인자1|인자2\n"
    "예시:\n"
    "  TOOL:get_crypto_price:BTC\n"
    "  TOOL:search_web:비트코인 전망 2026\n"
    "  TOOL:ssh_execute:visionfive|df -h\n"
    "직접 답변 가능하면 도구를 사용하지 마세요.\n"
)

ROLE_PROMPTS = {
    "default": _JARVIS_IDENTITY + _TOOL_FORMAT_INSTRUCTIONS,
    "trader": _JARVIS_IDENTITY + "트레이딩 특화. 차트/매매/리스크 분석.\n" + _TOOL_FORMAT_INSTRUCTIONS,
    "developer": _JARVIS_IDENTITY + "개발 특화. 코드/디버깅/시스템.\n" + _TOOL_FORMAT_INSTRUCTIONS,
    "analyst": _JARVIS_IDENTITY + "분석 특화. 전략/통계/데이터.\n" + _TOOL_FORMAT_INSTRUCTIONS,
}


def build_system_prompt(
    role: str = "default",
    context: str = "",
    history_str: str = "",
    categories: Optional[List[str]] = None,
    domain: Optional[str] = None,
) -> str:
    """
    역할 기반 시스템 프롬프트를 빌드합니다.

    Args:
        role: 역할 ("default", "trader", "developer", "analyst")
        context: 사용자 컨텍스트 문자열
        history_str: 대화 내역 문자열
        categories: 포함할 도구 카테고리
        domain: 에이전트 도메인 ("sc2", "crypto", "system" 등)

    Returns:
        완성된 시스템 프롬프트
    """
    now_kst = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S (KST)")

    base = ROLE_PROMPTS.get(role, ROLE_PROMPTS["default"])
    tool_list = generate_tool_list(categories)

    # 도메인별 추가 지시사항
    domain_inst = ""
    if domain and domain in DOMAIN_INSTRUCTIONS:
        domain_inst = f"\n[도메인 지시사항]\n{DOMAIN_INSTRUCTIONS[domain]}\n"

    return (
        f"{base}\n"
        f"현재 시간(KST): {now_kst}\n\n"
        f"{domain_inst}"
        f"사용자 컨텍스트: {context}\n"
        f"{history_str}\n"
        f"사용 가능한 도구:\n{tool_list}\n"
    )
