#!/usr/bin/env python3
"""
JARVIS 환경변수 검증 스크립트 (#162)
- .env.jarvis 파일에서 필수 변수들을 체크
- 변수별 형식 검증 (키 길이, 유효 문자)
- 누락된 변수 리스트 출력
- 선택 변수 안내 (DISCORD_TOKEN, CRYPTO_WEBHOOK_URL 등)
"""
import os
import re
import sys

# ═══════════════════════════════════════════════════
#  설정: 필수 변수 및 검증 규칙
# ═══════════════════════════════════════════════════

# 필수 변수 정의
# 형식: (변수명, 설명, 최소길이, 최대길이, 정규식 패턴)
REQUIRED_VARS = [
    {
        "name": "ANTHROPIC_API_KEY",
        "description": "Anthropic Claude API 키",
        "min_len": 10,
        "max_len": 200,
        "pattern": r"^sk-ant-[a-zA-Z0-9_\-]+$",
        "hint": "https://console.anthropic.com/settings/keys 에서 발급",
    },
    {
        "name": "UPBIT_ACCESS_KEY",
        "description": "업비트 API Access Key",
        "min_len": 30,
        "max_len": 100,
        "pattern": r"^[a-zA-Z0-9]+$",
        "hint": "https://upbit.com/mypage/open_api_management 에서 발급",
    },
    {
        "name": "UPBIT_SECRET_KEY",
        "description": "업비트 API Secret Key",
        "min_len": 30,
        "max_len": 100,
        "pattern": r"^[a-zA-Z0-9]+$",
        "hint": "Access Key와 함께 발급됨",
    },
    {
        "name": "DISCORD_BOT_TOKEN",
        "description": "Discord 봇 토큰",
        "min_len": 50,
        "max_len": 200,
        "pattern": r"^[a-zA-Z0-9._\-]+$",
        "hint": "https://discord.com/developers/applications 에서 발급",
    },
]

# 선택 변수 정의
OPTIONAL_VARS = [
    {
        "name": "CRYPTO_WEBHOOK_URL",
        "description": "Discord 암호화폐 알림 Webhook URL",
        "pattern": r"^https://discord\.com/api/webhooks/\d+/.+$",
        "hint": "Discord 채널 설정 > 연동 > 웹후크에서 생성",
    },
    {
        "name": "DISCORD_TOKEN",
        "description": "Discord 봇 토큰 (별칭)",
        "pattern": r"^[a-zA-Z0-9._\-]+$",
        "hint": "DISCORD_BOT_TOKEN과 동일한 값 사용 가능",
    },
    {
        "name": "GOOGLE_API_KEY",
        "description": "Google API 키 (Gemini 등)",
        "pattern": r"^AIza[a-zA-Z0-9_\-]+$",
        "hint": "https://console.cloud.google.com/ 에서 발급",
    },
    {
        "name": "GEMINI_API_KEY",
        "description": "Google Gemini API 키",
        "pattern": r"^AIza[a-zA-Z0-9_\-]+$",
        "hint": "https://aistudio.google.com/apikey 에서 발급",
    },
    {
        "name": "CLAUDE_SESSION_KEY",
        "description": "Claude 웹 세션 키 (폴백용)",
        "pattern": r"^sk-ant-sid[a-zA-Z0-9_\-]+$",
        "hint": "Claude.ai 브라우저 세션에서 추출",
    },
    {
        "name": "GOOGLE_APPLICATION_CREDENTIALS",
        "description": "Google Cloud 서비스 계정 JSON 경로",
        "pattern": r".+\.json$",
        "hint": "Google Cloud Console에서 서비스 계정 키 파일 다운로드",
    },
    {
        "name": "MANUS_API_KEY",
        "description": "Manus AI API 키",
        "pattern": r"^sk-[a-zA-Z0-9_\-]+$",
        "hint": "https://manus.im 대시보드에서 발급",
    },
    {
        "name": "CRYPTO_DRY_RUN",
        "description": "모의매매 모드 (true/false)",
        "pattern": r"^(true|false)$",
        "hint": "true = 모의매매, false = 실전매매",
    },
    {
        "name": "CRYPTO_MAX_TRADE_KRW",
        "description": "1회 최대 거래 금액 (원)",
        "pattern": r"^\d+$",
        "hint": "예: 100000 (10만원)",
    },
    {
        "name": "CRYPTO_DAILY_LIMIT",
        "description": "일일 최대 거래 횟수",
        "pattern": r"^\d+$",
        "hint": "예: 20",
    },
    {
        "name": "BOT_OWNER_ID",
        "description": "Discord 봇 오너 ID",
        "pattern": r"^\d+$",
        "hint": "Discord 사용자 ID (개발자 모드에서 복사)",
    },
    {
        "name": "JARVIS_DEFAULT_MODEL",
        "description": "기본 AI 모델 (haiku/sonnet/opus)",
        "pattern": r"^(haiku|sonnet|opus)$",
        "hint": "haiku = 빠름, sonnet = 균형, opus = 최고성능",
    },
]


# ═══════════════════════════════════════════════════
#  유틸리티 함수
# ═══════════════════════════════════════════════════

def load_env_file(filepath: str) -> dict:
    """
    .env 파일을 파싱하여 딕셔너리로 반환.
    주석(#)과 빈 줄은 무시.
    """
    env_vars = {}
    if not os.path.exists(filepath):
        return env_vars

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # 빈 줄 또는 주석 무시
            if not line or line.startswith("#"):
                continue
            # KEY=VALUE 파싱
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 따옴표 제거
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            env_vars[key] = value

    return env_vars


def validate_var(name: str, value: str, rule: dict) -> list:
    """
    변수 값의 형식을 검증하고 오류 메시지 리스트를 반환.
    오류가 없으면 빈 리스트 반환.
    """
    errors = []

    # 길이 검증 (필수 변수만)
    min_len = rule.get("min_len", 0)
    max_len = rule.get("max_len", 0)
    if min_len > 0 and len(value) < min_len:
        errors.append(f"  길이 부족: {len(value)}자 (최소 {min_len}자 필요)")
    if max_len > 0 and len(value) > max_len:
        errors.append(f"  길이 초과: {len(value)}자 (최대 {max_len}자)")

    # 정규식 패턴 검증
    pattern = rule.get("pattern", "")
    if pattern and not re.match(pattern, value):
        errors.append(f"  형식 불일치: 기대 패턴 = {pattern}")

    return errors


def print_header(title: str):
    """섹션 헤더 출력"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, status: str, detail: str = ""):
    """검증 결과 한 줄 출력"""
    # 상태 아이콘
    icons = {
        "OK": "[OK]",
        "WARN": "[경고]",
        "FAIL": "[실패]",
        "SKIP": "[미설정]",
        "INFO": "[정보]",
    }
    icon = icons.get(status, "[??]")
    line = f"  {icon} {name}"
    if detail:
        line += f" - {detail}"
    print(line)


# ═══════════════════════════════════════════════════
#  메인 검증 로직
# ═══════════════════════════════════════════════════

def validate(env_path: str = None) -> int:
    """
    환경변수 검증 메인 함수.
    반환값: 0 = 모든 필수 변수 OK, 1 = 누락/오류 있음
    """
    # .env.jarvis 파일 경로 결정
    if env_path is None:
        # 스크립트가 위치한 디렉토리 기준
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(script_dir, ".env.jarvis")

    print()
    print("JARVIS 환경변수 검증 도구 v1.0")
    print(f"  대상 파일: {env_path}")

    # 파일 존재 확인
    if not os.path.exists(env_path):
        print()
        print(f"[실패] .env.jarvis 파일을 찾을 수 없습니다: {env_path}")
        print()
        print("  해결 방법:")
        print("  1. .env.jarvis.example 파일을 복사하여 .env.jarvis로 이름 변경")
        print("  2. 각 항목에 올바른 API 키 값을 입력")
        return 1

    # .env 파일 로드
    env_vars = load_env_file(env_path)
    print(f"  로드된 변수: {len(env_vars)}개")

    has_errors = False
    missing_required = []
    format_errors = []

    # ── 필수 변수 검증 ──
    print_header("필수 변수 검증")

    for rule in REQUIRED_VARS:
        name = rule["name"]
        value = env_vars.get(name, "")

        if not value:
            # 값이 비어있음 (누락)
            missing_required.append(rule)
            print_result(name, "FAIL", f"누락됨 - {rule['description']}")
            print(f"         발급: {rule['hint']}")
            has_errors = True
        else:
            # 형식 검증
            errors = validate_var(name, value, rule)
            if errors:
                format_errors.append((name, errors))
                print_result(name, "WARN", f"형식 오류 ({rule['description']})")
                for err in errors:
                    print(f"       {err}")
                has_errors = True
            else:
                # 값 마스킹 (처음 4자 + ... + 마지막 4자)
                masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "****"
                print_result(name, "OK", f"{masked} ({rule['description']})")

    # ── 선택 변수 안내 ──
    print_header("선택 변수 상태")

    for rule in OPTIONAL_VARS:
        name = rule["name"]
        value = env_vars.get(name, "")

        if not value:
            print_result(name, "SKIP", rule["description"])
        else:
            # 형식 검증 (선택 변수도 설정되어 있으면 검증)
            errors = validate_var(name, value, rule)
            if errors:
                print_result(name, "WARN", f"형식 주의 ({rule['description']})")
                for err in errors:
                    print(f"       {err}")
            else:
                masked = value[:4] + "..." + value[-4:] if len(value) > 12 else "****"
                print_result(name, "OK", f"{masked} ({rule['description']})")

    # ── 보안 경고: 위험 패턴 체크 ──
    print_header("보안 검사")

    security_ok = True
    # .env.jarvis 가 .gitignore에 포함되어 있는지 확인
    gitignore_path = os.path.join(os.path.dirname(env_path), ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            gitignore_content = f.read()
        if ".env.jarvis" in gitignore_content or ".env*" in gitignore_content:
            print_result(".gitignore", "OK", ".env.jarvis가 .gitignore에 포함됨")
        else:
            print_result(".gitignore", "WARN", ".env.jarvis가 .gitignore에 없음 - 키 유출 위험!")
            security_ok = False
    else:
        print_result(".gitignore", "WARN", ".gitignore 파일이 없음")
        security_ok = False

    # 파일 권한 체크 (Unix 계열)
    if sys.platform != "win32":
        import stat
        file_stat = os.stat(env_path)
        mode = oct(file_stat.st_mode)[-3:]
        if mode not in ("600", "400", "640"):
            print_result("파일 권한", "WARN", f"현재 {mode} - 600 권장 (chmod 600 .env.jarvis)")
            security_ok = False
        else:
            print_result("파일 권한", "OK", f"현재 {mode}")
    else:
        print_result("파일 권한", "INFO", "Windows 환경 - 파일 권한 체크 생략")

    if security_ok:
        print_result("보안 상태", "OK", "문제 없음")

    # ── 요약 ──
    print_header("검증 요약")

    total_required = len(REQUIRED_VARS)
    ok_required = total_required - len(missing_required) - len(format_errors)
    set_optional = sum(1 for r in OPTIONAL_VARS if env_vars.get(r["name"], ""))

    print(f"  필수 변수: {ok_required}/{total_required} 정상")
    if missing_required:
        print(f"  누락 변수: {len(missing_required)}개")
        for r in missing_required:
            print(f"    - {r['name']}: {r['hint']}")
    if format_errors:
        print(f"  형식 오류: {len(format_errors)}개")
        for name, errs in format_errors:
            print(f"    - {name}")
    print(f"  선택 변수: {set_optional}/{len(OPTIONAL_VARS)} 설정됨")

    if has_errors:
        print()
        print("  [결과] 필수 변수에 문제가 있습니다. 위 안내를 참고하여 수정해주세요.")
        return 1
    else:
        print()
        print("  [결과] 모든 필수 변수가 정상입니다. JARVIS를 실행할 수 있습니다.")
        return 0


# ═══════════════════════════════════════════════════
#  엔트리포인트
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    # 인자로 .env 파일 경로를 받을 수 있음
    env_file = sys.argv[1] if len(sys.argv) > 1 else None
    exit_code = validate(env_file)
    sys.exit(exit_code)
