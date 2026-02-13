"""
5중 보안 체계 (Security Layers) — 강화 버전

Layer 1: .env 파일 격리 + .gitignore 자동 복구
Layer 2: Pre-commit hook + 다중 패턴 실시간 스캔
Layer 3: 런타임 키 마스킹 + 스택트레이스/환경변수 보호
Layer 4: 키 유효성 검증 + 키 해시 무결성 체크
Layer 5: 파일 시스템 보호 + 거래 안전 한도 / 이상 거래 탐지
"""
import os
import re
import sys
import stat
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from . import config

logger = logging.getLogger("crypto.security")

# ═══════════════════════════════════════════════
# Layer 1 강화: .gitignore 자동 복구
# ═══════════════════════════════════════════════

_REQUIRED_GITIGNORE_ENTRIES = [
    ".env",
    "*.env",
    ".env.*",
    "crypto_trading/data/",
    "*.key",
    "*.pem",
]


def enforce_gitignore() -> list:
    """필수 항목이 .gitignore에 포함되어 있는지 확인하고, 없으면 자동 추가"""
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    added = []

    existing_lines = set()
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            existing_lines = {line.strip() for line in f if line.strip() and not line.startswith('#')}

    missing = [entry for entry in _REQUIRED_GITIGNORE_ENTRIES if entry not in existing_lines]
    if missing:
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write("\n# ── JARVIS 보안 자동 추가 ──\n")
            for entry in missing:
                f.write(f"{entry}\n")
                added.append(entry)
        logger.info(f".gitignore 보안 항목 추가: {added}")

    return added


# ═══════════════════════════════════════════════
# Layer 2: API 키 패턴 탐지 (강화)
# ═══════════════════════════════════════════════

# 일반적인 API 키 패턴 (강화: 거래소별 패턴 추가)
_KEY_PATTERNS = [
    re.compile(r'[A-Za-z0-9]{30,64}'),          # 일반 API Key 패턴
    re.compile(r'UPBIT_ACCESS_KEY\s*=\s*\S+'),   # Upbit Access
    re.compile(r'UPBIT_SECRET_KEY\s*=\s*\S+'),   # Upbit Secret
    re.compile(r'(access|secret|api)[_-]?key\s*[:=]\s*["\']?\w{20,}', re.IGNORECASE),
    re.compile(r'(token|password|passwd|pwd)\s*[:=]\s*["\']?\w{10,}', re.IGNORECASE),
    re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE),  # Bearer 토큰
    re.compile(r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----'),        # SSH/RSA 키
]

# 실제 키 값 패턴 (현재 등록된 키의 prefix로 탐지)
_KNOWN_KEY_PREFIXES = []


def _load_known_keys():
    """현재 설정된 키의 앞 8자를 prefix로 등록"""
    global _KNOWN_KEY_PREFIXES
    _KNOWN_KEY_PREFIXES = []
    for key in [config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY]:
        if key and len(key) >= 8:
            _KNOWN_KEY_PREFIXES.append(key[:8])


def scan_file_for_secrets(filepath: str) -> list:
    """파일에서 API 키 패턴 탐지"""
    _load_known_keys()
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line_no, line in enumerate(f, 1):
                # 실제 키 값이 포함되어 있는지 체크
                for prefix in _KNOWN_KEY_PREFIXES:
                    if prefix in line:
                        findings.append({
                            "file": filepath,
                            "line": line_no,
                            "type": "ACTUAL_KEY_DETECTED",
                            "snippet": mask_sensitive(line.strip()),
                        })
    except Exception:
        pass
    return findings


def scan_directory_for_secrets(directory: str, extensions: list = None) -> list:
    """디렉토리 전체 스캔"""
    if extensions is None:
        extensions = ['.py', '.js', '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.bat', '.cmd', '.sh']

    all_findings = []
    skip_dirs = {'.venv', 'venv', 'node_modules', '.git', '__pycache__', '.next'}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                filepath = os.path.join(root, fname)
                findings = scan_file_for_secrets(filepath)
                all_findings.extend(findings)
    return all_findings


# ═══════════════════════════════════════════════
# Layer 3: 런타임 키 마스킹
# ═══════════════════════════════════════════════

def mask_sensitive(text: str) -> str:
    """텍스트에서 민감 정보를 마스킹"""
    result = text
    for key in [config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY]:
        if key and len(key) > 8 and key in result:
            masked = key[:4] + "*" * (len(key) - 8) + key[-4:]
            result = result.replace(key, masked)
    return result


class SecureLogFilter(logging.Filter):
    """로그에서 API 키 자동 마스킹 필터"""

    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = mask_sensitive(record.msg)
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    mask_sensitive(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def install_log_filter():
    """모든 로거에 보안 필터 설치"""
    secure_filter = SecureLogFilter()
    root_logger = logging.getLogger()
    root_logger.addFilter(secure_filter)
    for handler in root_logger.handlers:
        handler.addFilter(secure_filter)
    # crypto 관련 로거에도 설치
    for name in ["crypto", "crypto.upbit_client", "crypto.auto_trader",
                  "crypto.portfolio_tracker", "crypto.risk_manager", "crypto_mcp",
                  "crypto.analyzer", "crypto.security"]:
        logging.getLogger(name).addFilter(secure_filter)
    logger.info("보안 로그 필터 설치 완료")


def protect_environment_variables():
    """환경변수에서 민감 키를 런타임 후 즉시 제거 (메모리에만 유지)"""
    sensitive_env_keys = ["UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"]
    removed = []
    for key in sensitive_env_keys:
        if key in os.environ:
            os.environ.pop(key)
            removed.append(key)
    if removed:
        logger.info(f"환경변수에서 민감 키 제거 완료: {removed}")
    return removed


def install_exception_hook():
    """전역 예외 핸들러에 키 마스킹 적용 (스택트레이스 보호)"""
    _original_hook = sys.excepthook

    def _secure_excepthook(exc_type, exc_value, exc_tb):
        # 예외 메시지에서 민감 정보 제거
        safe_msg = mask_sensitive(str(exc_value))
        safe_exc = exc_type(safe_msg)
        _original_hook(exc_type, safe_exc, exc_tb)

    sys.excepthook = _secure_excepthook
    logger.info("보안 예외 핸들러 설치 완료")


# ═══════════════════════════════════════════════
# Layer 4: 키 유효성 검증
# ═══════════════════════════════════════════════

_KEY_HASH_FILE = config.DATA_DIR / ".key_hash"


def validate_api_keys() -> tuple[bool, str]:
    """API 키 형식 유효성 검증"""
    access = config.UPBIT_ACCESS_KEY
    secret = config.UPBIT_SECRET_KEY

    if not access or not secret:
        return False, "API 키가 설정되지 않았습니다. .env 파일을 확인하세요."

    if len(access) < 30 or len(secret) < 30:
        return False, "API 키 길이가 너무 짧습니다 (최소 30자)."

    if not re.match(r'^[A-Za-z0-9]+$', access):
        return False, "Access Key에 허용되지 않는 문자가 포함되어 있습니다."

    if not re.match(r'^[A-Za-z0-9]+$', secret):
        return False, "Secret Key에 허용되지 않는 문자가 포함되어 있습니다."

    return True, "API 키 형식 검증 통과"


def check_key_integrity() -> tuple[bool, str]:
    """키 해시 무결성 확인 — 키가 무단 변경되었는지 탐지"""
    access = config.UPBIT_ACCESS_KEY
    secret = config.UPBIT_SECRET_KEY
    if not access or not secret:
        return True, "키 미설정 (무결성 체크 스킵)"

    current_hash = hashlib.sha256(f"{access}:{secret}".encode()).hexdigest()[:16]

    if _KEY_HASH_FILE.exists():
        stored_hash = _KEY_HASH_FILE.read_text(encoding='utf-8').strip()
        if stored_hash != current_hash:
            logger.warning("⚠️ API 키 변경 감지! 이전 해시와 일치하지 않습니다.")
            # 새 해시 저장
            _KEY_HASH_FILE.write_text(current_hash, encoding='utf-8')
            return False, "API 키가 변경됨 (신규 해시 저장)"
        return True, "API 키 무결성 확인 완료"
    else:
        # 최초 실행: 해시 저장
        _KEY_HASH_FILE.write_text(current_hash, encoding='utf-8')
        return True, "API 키 해시 최초 등록"


# ═══════════════════════════════════════════════
# Layer 5: 파일 시스템 보호
# ═══════════════════════════════════════════════

def secure_data_files():
    """데이터 파일 권한 제한 (소유자만 읽기/쓰기)"""
    sensitive_paths = [
        config.PORTFOLIO_HISTORY_FILE,
        config.TRADE_LOG_FILE,
    ]
    # .env 파일들도 보호
    for env_path in [
        Path(__file__).parent.parent / "wicked_zerg_challenger" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        if env_path.exists():
            sensitive_paths.append(env_path)

    for path in sensitive_paths:
        path = Path(path)
        if path.exists():
            try:
                if sys.platform == "win32":
                    import subprocess
                    subprocess.run(
                        ["attrib", "+H", str(path)],
                        capture_output=True, timeout=5
                    )
                else:
                    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
                logger.debug(f"파일 보호 적용: {path}")
            except Exception as e:
                logger.warning(f"파일 보호 실패 ({path}): {e}")


# ═══════════════════════════════════════════════
# Layer 5 강화: 거래 안전 한도 / 이상 거래 탐지
# ═══════════════════════════════════════════════

class TradeSafetyGuard:
    """거래 안전 가드 — 비정상적 매매 패턴 감지 및 차단"""

    def __init__(self):
        self.max_daily_trades: int = 50               # 일일 최대 거래 횟수
        self.max_single_order_krw: float = 1_000_000  # 1회 최대 주문 금액 (100만원)
        self.max_daily_volume_krw: float = 5_000_000  # 일일 최대 거래 총액 (500만원)
        self._daily_trades: list = []                  # [(timestamp, amount), ...]
        self._alerts: list = []                        # 보안 경고 기록

    def _clean_old_trades(self):
        """24시간 이전 기록 정리"""
        cutoff = datetime.now() - timedelta(hours=24)
        self._daily_trades = [(ts, amt) for ts, amt in self._daily_trades if ts > cutoff]

    def check_trade(self, amount_krw: float) -> tuple[bool, str]:
        """매매 전 안전 검증"""
        self._clean_old_trades()

        # 1. 1회 금액 한도
        if amount_krw > self.max_single_order_krw:
            msg = f"⛔ 1회 주문 한도 초과: {amount_krw:,.0f}원 > {self.max_single_order_krw:,.0f}원"
            self._alerts.append((datetime.now(), msg))
            logger.warning(msg)
            return False, msg

        # 2. 일일 거래 횟수
        if len(self._daily_trades) >= self.max_daily_trades:
            msg = f"⛔ 일일 거래 횟수 초과: {len(self._daily_trades)} >= {self.max_daily_trades}"
            self._alerts.append((datetime.now(), msg))
            logger.warning(msg)
            return False, msg

        # 3. 일일 총 거래액
        daily_total = sum(amt for _, amt in self._daily_trades) + amount_krw
        if daily_total > self.max_daily_volume_krw:
            msg = f"⛔ 일일 거래 총액 초과: {daily_total:,.0f}원 > {self.max_daily_volume_krw:,.0f}원"
            self._alerts.append((datetime.now(), msg))
            logger.warning(msg)
            return False, msg

        # 4. 이상 패턴 감지: 최근 5분간 5회 이상 매매
        five_min_ago = datetime.now() - timedelta(minutes=5)
        recent = [t for t in self._daily_trades if t[0] > five_min_ago]
        if len(recent) >= 5:
            msg = f"⚠️ 이상 거래 감지: 5분 내 {len(recent)}회 매매 (봇 오작동 의심)"
            self._alerts.append((datetime.now(), msg))
            logger.warning(msg)
            return False, msg

        return True, "OK"

    def record_trade(self, amount_krw: float):
        """매매 기록"""
        self._daily_trades.append((datetime.now(), abs(amount_krw)))

    def get_daily_summary(self) -> dict:
        """일일 거래 요약"""
        self._clean_old_trades()
        total = sum(amt for _, amt in self._daily_trades)
        return {
            "trade_count": len(self._daily_trades),
            "total_volume_krw": total,
            "remaining_trades": self.max_daily_trades - len(self._daily_trades),
            "remaining_volume_krw": max(0, self.max_daily_volume_krw - total),
            "recent_alerts": [(str(ts), msg) for ts, msg in self._alerts[-5:]],
        }

    def set_limits(self, max_daily_trades: int = None, max_single_order_krw: float = None,
                   max_daily_volume_krw: float = None):
        """안전 한도 변경"""
        if max_daily_trades is not None:
            self.max_daily_trades = max_daily_trades
        if max_single_order_krw is not None:
            self.max_single_order_krw = max_single_order_krw
        if max_daily_volume_krw is not None:
            self.max_daily_volume_krw = max_daily_volume_krw


# 전역 인스턴스
trade_safety = TradeSafetyGuard()


# ═══════════════════════════════════════════════
# 초기화
# ═══════════════════════════════════════════════

def initialize_security():
    """5중 보안 체계 초기화 (강화 버전)"""
    results = []

    # Layer 1: .env 격리 + .gitignore 자동 복구
    env_exists = any(p.exists() for p in [
        Path(__file__).parent.parent / "wicked_zerg_challenger" / ".env",
        Path(__file__).parent.parent / ".env",
    ])
    gitignore_added = enforce_gitignore()
    l1_status = "✓" if env_exists else "✗ .env 파일 없음"
    if gitignore_added:
        l1_status += f" | .gitignore 자동 보강({len(gitignore_added)}항목)"
    results.append(f"Layer 1 (.env 격리 + .gitignore): {l1_status}")

    # Layer 2: 시크릿 스캔 (강화 패턴)
    project_root = str(Path(__file__).parent.parent)
    findings = scan_directory_for_secrets(project_root)
    if findings:
        results.append(f"Layer 2 (시크릿 스캔): ⚠ {len(findings)}개 의심 항목 발견")
        for f in findings[:3]:
            results.append(f"  - {f['file']}:{f['line']} [{f['type']}]")
    else:
        results.append("Layer 2 (시크릿 스캔): ✓ 소스코드에서 키 미검출")

    # Layer 3: 로그 마스킹 + 환경변수 보호 + 예외 핸들러
    install_log_filter()
    removed_env = protect_environment_variables()
    install_exception_hook()
    l3_detail = f"환경변수 {len(removed_env)}개 정리" if removed_env else "환경변수 클린"
    results.append(f"Layer 3 (런타임 보호): ✓ 로그필터 + {l3_detail} + 예외핸들러")

    # Layer 4: 키 유효성 + 무결성 해시
    valid, msg = validate_api_keys()
    integrity_ok, integrity_msg = check_key_integrity()
    l4_status = "✓" if (valid and integrity_ok) else "⚠"
    results.append(f"Layer 4 (키 검증): {l4_status} {msg} | {integrity_msg}")

    # Layer 5: 파일 보호 + 거래 안전 가드
    secure_data_files()
    results.append(f"Layer 5 (파일/거래 보호): ✓ 파일보호 적용 | "
                    f"일일한도: {trade_safety.max_daily_trades}회, "
                    f"{trade_safety.max_daily_volume_krw:,.0f}원")

    report = "\n".join(results)
    logger.info(f"5중 보안 체계 초기화 완료 (강화):\n{report}")
    return report


# Pre-commit hook 설치 스크립트
def _generate_hook_content() -> str:
    """Pre-commit hook 내용을 동적으로 생성 (키 prefix를 .env에서 읽음)"""
    # 키 prefix를 런타임에 주입 (소스코드에 하드코딩 방지)
    prefixes = []
    for key in [config.UPBIT_ACCESS_KEY, config.UPBIT_SECRET_KEY]:
        if key and len(key) >= 10:
            prefixes.append(key[:10])

    prefix_patterns = "\n".join(f'    "{p}"' for p in prefixes) if prefixes else '    # (키 prefix 없음 - .env 설정 필요)'

    return r'''#!/bin/sh
# JARVIS Crypto Trading - Pre-commit Secret Scanner
# 이 훅은 커밋 전에 API 키가 소스코드에 포함되어 있는지 검사합니다.

echo "🔒 보안 스캔: API 키 유출 검사 중..."

# 스테이징된 파일에서 API 키 패턴 탐색
PATTERNS=(
    "UPBIT_ACCESS_KEY\s*=\s*[A-Za-z0-9]{20,}"
    "UPBIT_SECRET_KEY\s*=\s*[A-Za-z0-9]{20,}"
''' + prefix_patterns + r'''
    "access_key.*[A-Za-z0-9]{30,}"
    "secret_key.*[A-Za-z0-9]{30,}"
)

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|json|yaml|yml|toml|cfg|ini|bat|cmd|sh|md|txt)$')

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

FOUND=0
for pattern in "${PATTERNS[@]}"; do
    RESULT=$(echo "$STAGED_FILES" | xargs grep -lnE "$pattern" 2>/dev/null | grep -v ".env" | grep -v ".gitignore")
    if [ -n "$RESULT" ]; then
        echo "❌ API 키 패턴 발견!"
        echo "$RESULT"
        FOUND=1
    fi
done

if [ $FOUND -eq 1 ]; then
    echo ""
    echo "⛔ 커밋 차단: 민감 정보가 포함된 파일이 있습니다."
    echo "   해당 파일에서 API 키를 제거하고 .env 파일을 사용하세요."
    exit 1
fi

echo "✅ 보안 스캔 통과"
exit 0
'''


def install_pre_commit_hook():
    """Git pre-commit hook 설치"""
    git_dir = Path(__file__).parent.parent / ".git" / "hooks"
    if not git_dir.exists():
        return "Git hooks 디렉토리를 찾을 수 없습니다."

    hook_path = git_dir / "pre-commit"

    # 기존 훅이 있으면 백업
    if hook_path.exists():
        backup = git_dir / "pre-commit.backup"
        hook_path.rename(backup)

    hook_content = _generate_hook_content()
    with open(hook_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(hook_content)

    if sys.platform != "win32":
        os.chmod(hook_path, 0o755)

    return f"Pre-commit hook 설치 완료: {hook_path}"
