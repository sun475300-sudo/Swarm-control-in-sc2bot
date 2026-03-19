# -*- coding: utf-8 -*-
"""JARVIS 공통 상수 — 매직넘버 중앙 관리."""

# ── 프롬프트 길이 제한 (키워드 매칭 시) ──
MAX_PROMPT_SHORT = 20       # 인사, 로그
MAX_PROMPT_STANDARD = 30    # 시스템, 시간, git, 날씨, 공포지수
MAX_PROMPT_MEDIUM = 40      # 검색
MAX_PROMPT_LONG = 50        # 타이머
MAX_PROMPT_EXTENDED = 100   # 알림

# ── 응답 길이 제한 ──
TRUNCATE_SHORT = 500        # 스크린샷/웹캠 폴백
TRUNCATE_STANDARD = 1500    # git 출력
DISCORD_SAFE_LIMIT = 1900   # Discord 2000자 안전 마진
SEARCH_RESULT_LIMIT = 1800  # 검색 결과/로컬 응답 최대 길이
ATTACHMENT_TEXT_LIMIT = 15000  # 첨부파일 텍스트 최대 길이
DISCORD_MSG_LIMIT = 2000    # Discord 메시지 길이 제한
PROMPT_TRUNCATE_LIMIT = 8000  # 프롬프트 최대 길이

# ── HTTP 타임아웃 (초) ──
HTTP_TIMEOUT_GEMINI = 45
HTTP_TIMEOUT_DEFAULT = 60
HTTP_TIMEOUT_PROXY = 300

# ── 요일 이름 (KST) ──
WEEKDAY_KR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
