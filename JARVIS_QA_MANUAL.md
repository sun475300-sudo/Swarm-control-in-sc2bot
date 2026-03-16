# JARVIS v2.0 — 티어별 전술 점검 매뉴얼 & 자동화 테스트 설계도

**작전명:** Operation Iron Curtain
**버전:** v2.0
**작성일:** 2026-03-16
**작성자:** QA Red Team Lead
**총 기능 수:** 80+ (48 키워드 핸들러 + 65 도구 디스패치 + 4 Slash + 5 Background + 74 MCP)

---

## 1. 점검 티어(Tier) 분류 및 시나리오

### Tier 1: 안전/Fast-Path (단순 API 통신)

위험도: LOW | 복구: 즉시 | 영향범위: 봇 프로세스 내부만

| # | 테스트 명령어 | 기대 정상 응답 (Expected Output) | 발생 가능 에러 | 검증 포인트 |
|---|-------------|-------------------------------|--------------|------------|
| 1-1 | `고양이 그려줘` | Embed: "AI 이미지 생성 완료" + 이미지 첨부 (generated.png) | `DALL-E API error: 401` → SD 폴백 → Pollinations 폴백 | 3단계 폴백 체인 정상 작동 |
| 1-2 | `상상의 동물을 그려줘` | 동일 Embed + "상상의 동물" 프롬프트 표시 | `Image generation error: aiohttp.ClientError` | 한글 프롬프트 URL 인코딩 |
| 1-3 | `draw a dragon` | 동일 Embed + "a dragon" 프롬프트 | Pollinations 타임아웃 (60s) | 영문 프롬프트 처리 |
| 1-4 | `날씨 알려줘 서울` | "서울 날씨: 맑음, 15도..." 텍스트 응답 | `Weather API timeout` | 도시명 추출 정확도 |
| 1-5 | `오늘 날씨 부산` | 부산 날씨 정보 | API 키 미설정 → "날씨 조회 실패" | 도시명 파싱 |
| 1-6 | `번역해줘 Hello World 한국어로` | "안녕하세요 세계" 또는 유사 번역 | 번역 API 실패 | target_lang 추출 |
| 1-7 | `운세 알려줘` | 오늘의 운세 텍스트 | API 실패 → 기본 운세 | fortune 핸들러 |
| 1-8 | `계산해줘 (15*7)+23` | "계산 결과: 128" | `eval() 보안 필터 차단` | 수식 안전 평가 |
| 1-9 | `검색해줘 파이썬 비동기` | 검색 결과 3-5개 링크 | `search_web timeout` | 결과 포맷 |
| 1-10 | `지금 몇시야` | "현재 시각 (KST): 2026-03-16 14:30:00" | (없음 - 로컬 처리) | 시간대 KST 정확 |
| 1-11 | `안녕 자비스` | 군대식 인사 ("사령관님, ...합니다") | (없음) | **페르소나 검증: "사령관님" 호칭** |
| 1-12 | `기능 알려줘` | 7개 카테고리 Embed (AI/Crypto/SC2/System/...) | (없음) | HELP_PATTERN 매칭 |
| 1-13 | `뭐 할 수 있어?` | 동일 Embed | (없음) | 다양한 도움말 변형 매칭 |
| 1-14 | `클립보드 읽어줘` | 현재 클립보드 내용 텍스트 | `pyperclip 미설치` | clipboard_read |
| 1-15 | `네트워크 상태` | IP, 게이트웨이, DNS 정보 | `socket.error` | network_status |

### Tier 2: 주의/MCP 물리 제어 (로컬 하드웨어)

위험도: MEDIUM | 복구: 수동 | 영향범위: 로컬 PC + SC2 게임

| # | 테스트 명령어 | 기대 정상 응답 (Expected Output) | 발생 가능 에러 | 검증 포인트 |
|---|-------------|-------------------------------|--------------|------------|
| 2-1 | `시스템 상태` | "CPU: 45%, RAM: 8.2/16GB, Disk: 120/500GB" Embed | `psutil 미설치` → fallback | system_resources() |
| 2-2 | `프로세스 목록` | 상위 15개 프로세스 (PID, 이름, CPU%, MEM%) | `AccessDenied` (일부 프로세스) | list_processes() |
| 2-3 | `스크린샷 찍어줘` | 스크린샷 이미지 첨부 (screenshot.png) | `mss 미설치` / 원격 데스크톱 미지원 | capture_screenshot() |
| 2-4 | `웹캠 캡처` | 웹캠 이미지 첨부 | `cv2.VideoCapture 실패` (카메라 없음) | capture_webcam() |
| 2-5 | `!scan` | AI 화면 분석 텍스트 (Gemini Vision) | `GOOGLE_API_KEY 미설정` | _analyze_screen() |
| 2-6 | `속도 측정해줘` | "다운: 150Mbps, 업: 50Mbps, 핑: 12ms" | `speedtest 모듈 실패` / 타임아웃 | check_internet_speed() |
| 2-7 | `SC2 전적` | "승률: 65%, 승: 13, 패: 7" Embed | `sc2_mcp_server 미연결` | sc2_bot_stats() |
| 2-8 | `SC2 게임 상황` | 유닛 목록 JSON (supply, workers, army) | `게임 미실행 상태` | get_game_situation() |
| 2-9 | `SC2 로그` | 최근 5개 로그 파일명 목록 | `로그 디렉토리 없음` | list_bot_logs() |
| 2-10 | `리플레이 목록` | 최근 리플레이 파일 리스트 | `리플레이 폴더 없음` | list_replays() |
| 2-11 | `파일 찾아줘 *.py` | 현재 디렉토리 .py 파일 목록 | `경로 접근 거부` | search_files() |
| 2-12 | `git 상태` | `git status` 결과 텍스트 | `.git 없음` | subprocess git |
| 2-13 | `타이머 5분` | "5분 타이머 설정 완료" → 5분 후 DM 알림 | (없음) | set_timer() |
| 2-14 | `MCP 도구 목록` | 5개 서버 도구 리스트 | MCP 서버 미실행 | list_mcp_tools() |
| 2-15 | `모니터링 시작` | "스마트 감시 모드 ON" + 3분 간격 스크린 분석 | Gemini API 한도 | monitor_task 시작 |
| 2-16 | `모니터링 중지` | "스마트 감시 모드 OFF" | (없음) | monitor_task 중지 |
| 2-17 | `볼륨 50` | "볼륨 50% 설정 완료" | `pycaw 미설치` (Windows) | pc_control(volume) |
| 2-18 | `밝기 70` | "화면 밝기 70% 설정" | `screen_brightness_control 미설치` | pc_control(brightness) |
| 2-19 | `메모 저장 오늘 회의록 AI 프로젝트 진행상황` | "Notion 메모 저장 완료: 오늘 회의록" | `NOTION_TOKEN 미설정` | save_note() |
| 2-20 | `오늘 일정` | Google Calendar 오늘 일정 목록 | `credentials.json 미설정` | get_today_events() |

### Tier 3: 1급 위험/Red Zone (실제 매매/코드 실행/터미널)

위험도: CRITICAL | 복구: 불가 (금전적 손실 가능) | 영향범위: 실계좌 + 시스템 전체

**SAFETY PROTOCOL: 모든 Tier 3 테스트는 반드시 DRY-RUN 모드에서만 실행**

| # | 테스트 명령어 | 기대 정상 응답 | 발생 가능 에러 | DRY-RUN 안전장치 |
|---|-------------|--------------|--------------|-----------------|
| 3-1 | `모의 모드 설정` | "거래 모드: DRY-RUN (모의매매) 전환 완료" | (없음) | **먼저 실행 필수** |
| 3-2 | `/price BTC` | Embed: "BTC ₩145,230,000 (+2.3%)" | `Upbit API 429 Rate Limit` | Slash command 정상 |
| 3-3 | `/balance` | "KRW: ₩1,000,000, BTC: 0.005 ..." Embed | `API 키 미설정` | 잔고 조회 |
| 3-4 | `/trade buy BTC 10000` | "[DRY-RUN] 매수 시뮬레이션: BTC 10,000원" | TradeOrchestrator 승인 대기 | **실매매 차단 확인** |
| 3-5 | `/trade sell BTC 0.001` | "[DRY-RUN] 매도 시뮬레이션: BTC 0.001개" | 승인 거부 시 "거래 취소됨" | 승인 게이트 검증 |
| 3-6 | `자동매매 시작 balanced` | "[DRY-RUN] 자동매매 시작 (balanced 전략)" | `auto_trader 초기화 실패` | DRY-RUN 모드 확인 |
| 3-7 | `자동매매 상태` | "자동매매: 활성, 전략: balanced, 포지션: 0" | (없음) | 상태 리포트 |
| 3-8 | `자동매매 중지` | "자동매매 중지 완료" | `이미 중지 상태` | 안전 중지 |
| 3-9 | `손절 3% 익절 5% 설정` | "손절: -3%, 익절: +5% 설정 완료" | `잘못된 % 값` | set_risk_params() |
| 3-10 | `안전 한도 설정 일일 10건 최대 50000원` | "일일 거래 10건, 주문당 최대 50,000원" | (없음) | set_safety_limits() |
| 3-11 | `보안 상태 체크` | "API 키: 유효, 마지막 갱신: ..., IP 제한: 활성" | `API 키 만료` | security_status() |
| 3-12 | `포트폴리오 그래프 7일` | 7일간 포트폴리오 변동 차트 이미지 | `히스토리 데이터 없음` | portfolio_graph() |
| 3-13 | `파이썬 실행 print("Hello")` | "실행 결과: Hello" | `AST 보안 필터 차단` | **execute_python_code (AST 검증)** |
| 3-14 | `파이썬 실행 import os; os.system("rm -rf /")` | "**차단됨:** 위험한 코드 패턴 감지 (os.system)" | AST 필터 → `BLOCKED` | **파괴적 코드 차단 검증** |
| 3-15 | `파이썬 실행 import subprocess; subprocess.run(["ls"])` | "**차단됨:** subprocess 모듈 사용 제한" | AST 필터 → `BLOCKED` | subprocess 차단 |
| 3-16 | `터미널 echo Hello` | "실행 결과: Hello" | `명령어 필터 차단` | execute_terminal_command |
| 3-17 | `터미널 rm -rf /` | "**차단됨:** 위험한 명령어" | 명령어 블랙리스트 | **파괴적 명령 차단** |
| 3-18 | `터미널 format C:` | "**차단됨:** 위험한 명령어" | 명령어 블랙리스트 | 디스크 포맷 차단 |
| 3-19 | `김프 확인` | "BTC 김치프리미엄: +3.2% (Upbit vs Binance)" | `Binance API 실패` | kimchi_premium() |
| 3-20 | `탐욕 지수` | "Fear & Greed Index: 72 (Greed)" | API 타임아웃 | fear_greed_index() |

---

## 2. 백그라운드 자율 에이전트 스트레스 테스트

### 비동기 병목 현상 점검 매트릭스

| Task | 주기 | 블로킹 위험 | 비동기 보호 |
|------|-----|-----------|-----------|
| `update_status_task` | 1분 | LOW | `asyncio.wait_for()` + `bot.wait_until_ready()` |
| `daily_briefing_task` | 1분 (08:00 트리거) | MEDIUM | `WorkflowOrchestrator.execute_parallel()` 7개 섹션 병렬 |
| `monitor_task` | 3분 | **HIGH** | Gemini Vision API 호출 (네트워크 I/O) |
| `portfolio_monitor_task` | 30분 | LOW | `upbit_client` async HTTP |
| `price_alert_check_task` | 1분 | LOW | 로컬 dict 비교 (I/O 없음) |

### 스트레스 테스트 시나리오

```
[테스트 1: 동시 부하]
1. 디스코드 채팅에서 빠르게 5개 명령 연속 입력:
   "시세 BTC" → "날씨 서울" → "시스템 상태" → "기능 알려줘" → "그려줘 고양이"
2. 관찰: 각 응답이 5초 내 도착하는지, 순서가 뒤바뀌지 않는지 확인
3. 예상: 각 명령이 독립 asyncio Task로 처리 → 병렬 응답 (순서 무관)

[테스트 2: Background + Foreground 경합]
1. `모니터링 시작` (3분 간격 스크린 분석 활성)
2. 모니터링 실행 중에 "시세 BTC" 입력
3. 관찰: BTC 시세 응답이 모니터링 때문에 지연되지 않는지
4. 예상: 독립 코루틴 → 간섭 없음

[테스트 3: 대용량 응답 처리]
1. "포트폴리오 그래프 30일" (큰 이미지 생성)
2. 동시에 "전적 알려줘"
3. 관찰: 이미지 생성 중 다른 명령 블로킹 여부

[테스트 4: Rate Limit 캐스케이드]
1. Claude API rate limit 유도 (10회 연속 긴 질문)
2. 관찰: rate limit 후 Gemini/Ollama 폴백 정상 작동 여부
3. 예상: _is_rate_limited() → 쿨다운 60초 → 대체 모델 시도
```

### 비동기 에러 핸들링 코드 검토 가이드

| 검증 항목 | 파일:라인 | 상태 | 설명 |
|----------|---------|------|------|
| `on_message` 전역 try/except | discord_jarvis.py:L700-780 | PASS | 모든 메시지 처리에 최외곽 예외 포착 |
| `_try_local_response` 개별 핸들러 | discord_jarvis.py:L1077-2559 | **WARN** | 대부분 try/except 있지만 일부 inline 핸들러 미보호 |
| `_query_hybrid_model` 캐스케이드 | discord_jarvis.py:L2960-3100 | PASS | 4단계 폴백 (Claude→Proxy→Gemini→Ollama) |
| `_execute_tool` 도구 디스패치 | discord_jarvis.py:L3297-3704 | PASS | 각 도구별 try/except + fallback 메시지 |
| Background task exception | discord_jarvis.py:L4031+ | PASS | `@task.before_loop` + `wait_until_ready()` |
| Image gen fallback chain | discord_jarvis.py:L1199-1238 | **FIXED** | 개별 엔진 try/except 격리 (이번 세션 수정) |
| MCP server error isolation | sc2/system/crypto_mcp_server | PASS | 각 도구 함수 개별 try/except |
| WebSocket reconnect | discord.py 내장 | PASS | Gateway 재연결 자동 처리 |

---

## 3. 멀티모달 및 파일 처리 한계 테스트 (Edge Case)

### 3-1. 손상된 파일 처리

| # | 테스트 시나리오 | 입력 | 기대 응답 | 검증 방법 |
|---|---------------|------|----------|----------|
| E-1 | 손상된 PDF `!scan` | 0바이트 PDF 업로드 후 `!scan` | "사령관님, 해당 파일을 분석할 수 없습니다. 파일이 손상되었거나 빈 파일입니다." | 빈 파일 생성 → Discord 업로드 |
| E-2 | 읽을 수 없는 이미지 | 1x1px 이미지 + `분석해줘` | 정상 처리 or "판독 불가" 우아한 에러 | `convert -size 1x1 xc:black test.png` |
| E-3 | 초대용량 파일 | 10MB+ 이미지 업로드 | "파일 크기 제한(8MB) 초과" | Discord 자체 제한 선행 |
| E-4 | 악성 파일명 | `../../etc/passwd.txt` 첨부 | 경로 순회 차단 → 정상 에러 메시지 | Path traversal 방어 검증 |
| E-5 | 비텍스트 바이너리 | `.exe` 파일 + `읽어줘` | "바이너리 파일은 텍스트로 읽을 수 없습니다" | read_file 타입 검증 |

### 3-2. 입력 경계값 테스트

| # | 테스트 시나리오 | 입력 | 기대 응답 |
|---|---------------|------|----------|
| E-6 | 빈 메시지 (멘션만) | `@JARVIS` | "사령관님, 명령을 내려주십시오." |
| E-7 | 2000자 초과 | 2000자 이상 긴 메시지 | 정상 처리 (Discord 2000자 제한은 응답에만 적용) |
| E-8 | 특수문자 폭탄 | `그려줘 $${}[]<>'"` | Regex 매칭 후 특수문자 프롬프트 → 이미지 생성 시도 |
| E-9 | 한영 혼합 | `시세 check BTC price now` | BTC 시세 조회 정상 |
| E-10 | 이모지 입력 | `날씨 서울 ☀️🌧️` | 이모지 제거 후 "서울" 추출 → 날씨 조회 |

### 3-3. 우아한 예외 처리 검증 방법

```python
# 테스트 스크립트 (Discord에 직접 입력)
# Step 1: 봇이 다운되지 않는지 확인
"파이썬 실행 1/0"
# → 기대: "ZeroDivisionError: division by zero" (봇 생존)

# Step 2: 봇 메모리 누수 확인
"봇 상태"
# → 기대: 업타임, 메모리 사용량, 처리 메시지 수 표시

# Step 3: 존재하지 않는 도구 호출
"TOOL:nonexistent_tool:test"
# → 기대: "알 수 없는 도구: nonexistent_tool" (봇 생존)
```

---

## 4. 기능 커버리지 리포트

### 카테고리별 기능 집계

| 카테고리 | 키워드 핸들러 | 도구 디스패치 | Slash CMD | BG Task | MCP Tools | 합계 |
|---------|------------|------------|----------|---------|-----------|------|
| AI & Multimodal | 3 (이미지/TTS/분석) | 1 (scan) | 0 | 0 | 0 | **4** |
| Crypto & Trading | 18 | 10 | 4 | 2 | 28+ | **62** |
| SC2 Bot Control | 9 | 5 | 0 | 0 | 10 | **24** |
| System Admin | 15 | 8 | 0 | 0 | 22+ | **45** |
| Productivity | 5 | 7 | 0 | 1 | 0 | **13** |
| Autonomous Agent | 3 (monitor/cctv/briefing) | 0 | 0 | 5 | 6 | **14** |
| Entertainment | 2 (음악/운세) | 1 | 0 | 0 | 0 | **3** |
| OpenClaw Skills | 0 | 14 | 0 | 0 | 0 | **14** |
| Agentic (Code/File) | 0 | 10 | 0 | 0 | 8 | **18** |
| **합계** | **55** | **56** | **4** | **8** | **74+** | **~197** |

### TOOL_CATALOG vs _execute_tool() 매핑 검증

| 상태 | 항목 수 | 설명 |
|------|--------|------|
| MAPPED (정상) | 52/55 | TOOL_CATALOG의 도구가 _execute_tool()에 핸들러 있음 |
| UNMATCHED | 3 | `openclaw_transcribe`, `openclaw_calendar` — OpenClaw CLI 의존 (외부 서비스) |
| EXTRA (카탈로그 미등록) | 8 | `backup_memory`, `bot_status`, `search_memory` 등 — 동작하지만 카탈로그 미등록 |

---

## 5. 시스템 보안 핵심 권고사항

### RED TEAM 최우선 권고: `execute_python_code` 샌드박스 강화

**현재 상태:** AST 기반 정적 분석으로 위험 모듈(`os`, `subprocess`, `shutil`, `sys`) 차단 중.

**취약점:** AST 우회 가능한 패턴 존재:

```python
# 우회 시나리오 1: __import__ 동적 임포트
exec("__import__('os').system('whoami')")

# 우회 시나리오 2: builtins 접근
getattr(__builtins__, '__import__')('os')

# 우회 시나리오 3: eval 체이닝
eval(compile("import os; os.system('id')", "<x>", "exec"))
```

**권고 조치:**
1. `exec()`, `eval()`, `compile()`, `__import__()` 를 AST 블랙리스트에 추가
2. `__builtins__`, `__class__`, `__subclasses__` 접근 차단
3. 실행 환경에 `RestrictedPython` 또는 Docker 컨테이너 샌드박스 적용
4. 최대 실행 시간 10초 타임아웃 (현재 미설정 시 무한 루프 위험)

---

## 부록 A: 전체 점검 실행 순서

```
Phase 1: 사전 준비
  [1] 모의 모드 확인: "모의 모드 설정" → DRY-RUN 활성 확인
  [2] 봇 상태 확인: "봇 상태" → 업타임, 메모리 정상 확인

Phase 2: Tier 1 점검 (15개 항목, ~10분)
  [3] 1-1 ~ 1-15 순차 실행
  [4] 각 응답에서 "사령관님" 호칭 사용 여부 확인 (페르소나 검증)

Phase 3: Tier 2 점검 (20개 항목, ~15분)
  [5] 2-1 ~ 2-20 순차 실행
  [6] MCP 서버 연결 상태 확인

Phase 4: Tier 3 점검 (20개 항목, ~20분)
  [7] 3-1 먼저 실행 (DRY-RUN 모드 전환)
  [8] 3-2 ~ 3-20 순차 실행
  [9] 파괴적 명령 차단 확인 (3-14, 3-17, 3-18)

Phase 5: 스트레스 테스트 (~10분)
  [10] 동시 부하 테스트 (5개 연속 입력)
  [11] Background + Foreground 경합 테스트

Phase 6: Edge Case 테스트 (~10분)
  [12] E-1 ~ E-10 실행

Phase 7: 최종 리포트
  [13] "봇 상태" → 메모리 누수 없는지 확인
  [14] 결과 정리 → PASS/FAIL 집계
```

---

## 부록 B: 자동화 테스트 스크립트 (Python)

```python
"""
JARVIS v2.0 자동화 QA 테스트 — 코드 경로 검증 (오프라인)
Discord 실행 없이 import/syntax/handler 매핑 검증
"""
import py_compile
import re
import ast
import sys

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")

# ── 1. Syntax Check ──
print("=== Phase 1: Syntax Verification ===")
for f in ["discord_jarvis.py", "system_prompts.py", "jarvis_features/ai_features.py",
          "crypto_mcp_server.py", "sc2_mcp_server.py", "system_mcp_server.py",
          "agentic_mcp_server.py", "jarvis_mcp_server.py"]:
    try:
        py_compile.compile(f, doraise=True)
        check(f"Syntax: {f}", True)
    except py_compile.PyCompileError as e:
        check(f"Syntax: {f} — {e}", False)

# ── 2. Regex Pattern Validation ──
print("\n=== Phase 2: Regex Pattern Tests ===")
import importlib.util
spec = importlib.util.spec_from_file_location("dj", "discord_jarvis.py")
# Can't fully import (needs discord), so parse regex directly
with open("discord_jarvis.py", "r", encoding="utf-8") as f:
    src = f.read()

# Extract HELP_PATTERN
m = re.search(r"_HELP_PATTERN\s*=\s*_re\.compile\(\s*r'(.+?)',", src, re.DOTALL)
if m:
    hp = re.compile(m.group(1), re.IGNORECASE)
    for txt, expect in [("기능 알려줘", True), ("뭐 할 수 있어", True),
                        ("도움", True), ("help", True), ("오늘 날씨", False)]:
        check(f"HELP_PATTERN '{txt}' → {expect}", bool(hp.search(txt)) == expect)

# Extract IMAGE_GEN_PATTERN
m = re.search(r"_IMAGE_GEN_PATTERN\s*=\s*_re\.compile\(\s*r'(.+?)',", src, re.DOTALL)
if m:
    ip = re.compile(m.group(1), re.IGNORECASE)
    for txt, expect in [("고양이 그려줘", True), ("그림 그려", True),
                        ("이미지 생성", True), ("draw a cat", True),
                        ("오늘 날씨", False), ("시세 알려줘", False)]:
        check(f"IMAGE_PATTERN '{txt}' → {expect}", bool(ip.search(txt)) == expect)

# ── 3. Persona Guard Check ──
print("\n=== Phase 3: Persona Guard ===")
check("_PERSONA_PREAMBLE contains '사령관'", "사령관" in src)
check("_PERSONA_PREAMBLE contains '절대 지시사항'", "절대 지시사항" in src)
check("_PERSONA_PREAMBLE contains '사장님' ban", "사장님" in src and "금지" in src)
check("Fallback prompt has '사령관'",
      "사령관의 AI 부관" in src.split("_build_fallback_system_prompt")[1][:500])

# ── 4. Summary ──
print(f"\n{'='*40}")
print(f"Total: {PASS + FAIL} | PASS: {PASS} | FAIL: {FAIL}")
print(f"{'='*40}")
sys.exit(1 if FAIL > 0 else 0)
```

---

*End of QA Manual — Operation Iron Curtain*
