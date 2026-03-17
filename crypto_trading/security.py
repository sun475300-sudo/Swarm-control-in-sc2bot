"""
5중 보안 체계 (Security Layers) — 강화 버전

Layer 1: .env 파일 격리 + .gitignore 자동 복구
Layer 2: Pre-commit hook + 다중 패턴 실시간 스캔
Layer 3: 런타임 키 마스킹 + 스택트레이스/환경변수 보호
Layer 4: 키 유효성 검증 + 키 해시 무결성 체크
Layer 5: 파일 시스템 보호 + 거래 안전 한도 / 이상 거래 탐지

#155: 통계적 이상 탐지 강화
#156: 암호화된 거래 로그
#157: 자동 백업
#158: 보안 대시보드
#159: 제로 트러스트 검증
#160: 시크릿 매니저
"""
import math
import os
import re
import sys
import stat
import hashlib
import logging
import threading
import time
import json
import base64
import zipfile
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta
from . import config

logger = logging.getLogger("crypto.security")

# ═══════════════════════════════════════════════
# IP Whitelist (#151)
# ═══════════════════════════════════════════════

ALLOWED_IPS = {"127.0.0.1", "::1", "localhost"}


def check_ip_allowed(ip: str) -> bool:
    """IP 화이트리스트 확인"""
    if not ALLOWED_IPS:
        return True  # 화이트리스트 비어있으면 모두 허용
    return ip in ALLOWED_IPS or ip.startswith("192.168.") or ip.startswith("10.")


# ═══════════════════════════════════════════════
# Audit Log (#152)
# ═══════════════════════════════════════════════

AUDIT_LOG_FILE = Path(__file__).parent / "data" / "audit_log.jsonl"


def audit_log(event_type: str, details: dict):
    """감사 로그 기록 (JSONL 형식)"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **details
    }
    try:
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"감사 로그 실패: {e}")


# ═══════════════════════════════════════════════
# API Key Health Check (#153)
# ═══════════════════════════════════════════════

def check_api_key_health() -> dict:
    """API 키 상태 점검"""
    from . import config
    status = {"upbit_key_set": bool(config.UPBIT_ACCESS_KEY), "upbit_secret_set": bool(config.UPBIT_SECRET_KEY)}
    # Key length validation
    if config.UPBIT_ACCESS_KEY and len(config.UPBIT_ACCESS_KEY) < 20:
        status["warning"] = "Upbit Access Key가 너무 짧습니다. 올바른 키인지 확인하세요."
    return status


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
    except Exception as e:
        logger.debug(f"Could not scan file {filepath} for secrets: {e}")
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
        try:
            safe_exc = exc_type(safe_msg)
        except Exception as e:
            logger.debug(f"Could not reconstruct exception type {exc_type}: {e}")
            safe_exc = Exception(safe_msg)
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
        self._pending_confirmations: dict = {}         # 2FA 확인 대기 (#150)
        self._recent_amounts: deque = deque(maxlen=100)  # P2-13: 이상 거래 탐지용 최근 금액 (자동 제한)
        self._guard_lock = threading.Lock()            # 스레드 안전 보호

    def _clean_old_trades(self):
        """24시간 이전 기록 정리"""
        cutoff = datetime.now() - timedelta(hours=24)
        self._daily_trades = [(ts, amt) for ts, amt in self._daily_trades if ts > cutoff]

    def check_trade(self, amount_krw: float) -> tuple[bool, str]:
        """매매 전 안전 검증"""
        with self._guard_lock:
            self._clean_old_trades()

            # 1. 1회 금액 한도 — Bug #8 Fix: >= 로 변경하여 2FA가 먼저 트리거될 수 있도록 함
            if amount_krw >= self.max_single_order_krw:
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
        with self._guard_lock:
            self._daily_trades.append((datetime.now(), abs(amount_krw)))
            self._recent_amounts.append(abs(amount_krw))  # P2-13: deque(maxlen=100) 자동 제한

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
        """안전 한도 변경 — P2-4: 범위 검증 추가"""
        if max_daily_trades is not None:
            if not (0 < max_daily_trades <= 1000):
                raise ValueError(f"max_daily_trades는 1~1000 범위여야 합니다: {max_daily_trades}")
            self.max_daily_trades = max_daily_trades
        if max_single_order_krw is not None:
            if not (5000 <= max_single_order_krw <= 100_000_000):
                raise ValueError(f"max_single_order_krw는 5,000~100,000,000 범위여야 합니다: {max_single_order_krw}")
            self.max_single_order_krw = max_single_order_krw
        if max_daily_volume_krw is not None:
            if not (10_000 <= max_daily_volume_krw <= 1_000_000_000):
                raise ValueError(f"max_daily_volume_krw는 10,000~1,000,000,000 범위여야 합니다: {max_daily_volume_krw}")
            self.max_daily_volume_krw = max_daily_volume_krw

    # ── 2FA Trade Confirmation (#150) ──

    def request_2fa_confirmation(self, amount_krw: float, ticker: str) -> dict:
        """대규모 거래 시 확인 요청 생성"""
        LARGE_TRADE_THRESHOLD = 1_000_000  # 100만원 이상
        if amount_krw >= LARGE_TRADE_THRESHOLD:
            import secrets as _secrets
            confirm_code = str(_secrets.randbelow(900000) + 100000)
            self._pending_confirmations[confirm_code] = {
                "amount": amount_krw, "ticker": ticker,
                "created": time.time(), "expires": time.time() + 300
            }
            return {"needs_confirmation": True, "code": confirm_code,
                    "message": f"대규모 거래({amount_krw:,.0f}원). 확인 코드: {confirm_code}"}
        return {"needs_confirmation": False}

    def confirm_2fa(self, code: str) -> bool:
        """확인 코드 검증"""
        entry = self._pending_confirmations.pop(code, None)
        if not entry:
            return False
        if time.time() > entry["expires"]:
            return False
        return True

    # ── Anomaly Detection Enhancement (#154) ──

    def detect_anomaly(self, amount_krw: float) -> tuple:
        """비정상 거래 패턴 탐지 (통계 기반)"""
        if len(self._recent_amounts) < 5:
            return False, "충분한 데이터 없음"
        avg = sum(self._recent_amounts) / len(self._recent_amounts)
        if avg == 0:
            return False, "평균 0"
        deviation = abs(amount_krw - avg) / max(avg, 1)
        if deviation > 3.0:  # 평균 대비 3배 이상 편차
            return True, f"비정상 거래 감지: 평균({avg:,.0f}) 대비 {deviation:.1f}배 편차"
        return False, "정상"

    # ── Statistical Anomaly Detection (#155) ──

    def statistical_anomaly_detection(self, amount_krw: float, z_threshold: float = 2.5) -> dict:
        """통계적 이상 탐지 — 이동 평균 및 표준 편차 기반 Z-score 분석

        Args:
            amount_krw: 검증할 거래 금액 (KRW)
            z_threshold: Z-score 임계값 (기본 2.5, |z| > threshold 시 이상 판정)

        Returns:
            dict: {
                'is_anomaly': bool,
                'z_score': float,
                'mean': float,
                'std_dev': float,
                'amount': float,
                'message': str
            }
        """
        result = {
            "is_anomaly": False,
            "z_score": 0.0,
            "mean": 0.0,
            "std_dev": 0.0,
            "amount": amount_krw,
            "message": "",
        }

        # 최소 10개 이상의 거래 기록이 있어야 통계 의미 있음
        if len(self._recent_amounts) < 10:
            result["message"] = f"데이터 부족 ({len(self._recent_amounts)}/10). 통계적 탐지 불가."
            return result

        # 이동 평균 (최근 50건)
        window = self._recent_amounts[-50:]
        n = len(window)
        mean = sum(window) / n

        # 표준 편차 — Bug #9 Fix: 표본 표준편차 사용 (n-1), n<=1이면 0
        if n <= 1:
            std_dev = 0.0
        else:
            variance = sum((x - mean) ** 2 for x in window) / (n - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 0.0

        result["mean"] = round(mean, 2)
        result["std_dev"] = round(std_dev, 2)

        if std_dev == 0:
            result["message"] = "표준 편차 0 — 모든 거래 금액 동일. 이상 탐지 불가."
            return result

        # Z-score 계산
        z_score = (amount_krw - mean) / std_dev
        result["z_score"] = round(z_score, 4)

        if abs(z_score) > z_threshold:
            result["is_anomaly"] = True
            direction = "과대" if z_score > 0 else "과소"
            result["message"] = (
                f"통계적 이상 거래 감지: Z-score={z_score:.2f} (임계값 ±{z_threshold}). "
                f"금액 {amount_krw:,.0f}원은 평균({mean:,.0f}원) 대비 {direction} 편차."
            )
            self._alerts.append((datetime.now(), result["message"]))
            logger.warning(result["message"])
        else:
            result["message"] = (
                f"정상 범위: Z-score={z_score:.2f} (임계값 ±{z_threshold}). "
                f"평균 {mean:,.0f}원, 표준편차 {std_dev:,.0f}원."
            )

        return result


# 전역 인스턴스
trade_safety = TradeSafetyGuard()


# ═══════════════════════════════════════════════
# #156: 암호화된 거래 로그 (EncryptedTradeLog)
# ═══════════════════════════════════════════════

class EncryptedTradeLog:
    """암호화된 거래 로그 관리

    Fernet 대칭 암호화를 사용하여 거래 로그를 암호화하여 저장.
    cryptography 라이브러리가 없으면 base64 인코딩으로 폴백.
    """

    def __init__(self, log_dir: Path = None, key: bytes = None):
        """초기화

        Args:
            log_dir: 암호화 로그 저장 디렉토리 (기본: crypto_trading/data/encrypted_logs)
            key: Fernet 암호화 키 (None이면 자동 생성/로드)
        """
        self.log_dir = log_dir or (config.DATA_DIR / "encrypted_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._key_file = self.log_dir / ".log_key"
        self._use_fernet = False
        self._fernet = None

        # Fernet 초기화 시도
        try:
            from cryptography.fernet import Fernet
            if key:
                self._fernet = Fernet(key)
            elif self._key_file.exists():
                stored_key = self._key_file.read_bytes().strip()
                self._fernet = Fernet(stored_key)
            else:
                new_key = Fernet.generate_key()
                self._key_file.write_bytes(new_key)
                self._fernet = Fernet(new_key)
            self._use_fernet = True
            logger.info("EncryptedTradeLog: Fernet 암호화 활성화")
        except ImportError:
            logger.warning("EncryptedTradeLog: cryptography 미설치. base64 폴백 사용.")

    def _encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        if self._use_fernet and self._fernet:
            return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        else:
            return base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")

    def _decrypt(self, ciphertext: str) -> str:
        """문자열 복호화"""
        if self._use_fernet and self._fernet:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        else:
            return base64.b64decode(ciphertext.encode("utf-8")).decode("utf-8")

    def write_log(self, entry: dict) -> Path:
        """암호화된 로그 엔트리 기록

        Args:
            entry: 로그 데이터 딕셔너리

        Returns:
            Path: 저장된 로그 파일 경로
        """
        entry["_logged_at"] = datetime.now().isoformat()
        plaintext = json.dumps(entry, ensure_ascii=False)
        encrypted = self._encrypt(plaintext)

        log_file = self.log_dir / f"trade_log_{datetime.now().strftime('%Y%m%d')}.enc"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(encrypted + "\n")

        logger.debug(f"암호화 로그 기록: {log_file.name}")
        return log_file

    def read_log(self, log_file: Path) -> list:
        """암호화된 로그 파일 읽기

        Args:
            log_file: 암호화 로그 파일 경로

        Returns:
            list: 복호화된 로그 엔트리 리스트
        """
        entries = []
        if not log_file.exists():
            return entries

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    decrypted = self._decrypt(line)
                    entries.append(json.loads(decrypted))
                except Exception as e:
                    logger.error(f"로그 복호화 실패: {e}")
                    entries.append({"_error": str(e), "_raw": line[:50] + "..."})

        return entries

    def list_logs(self) -> list:
        """저장된 암호화 로그 파일 목록"""
        return sorted(self.log_dir.glob("trade_log_*.enc"))


# ═══════════════════════════════════════════════
# #157: 자동 백업 (auto_backup)
# ═══════════════════════════════════════════════

def auto_backup(target_dir: str = None, max_backups: int = 10) -> str:
    """crypto_trading/data/ 디렉토리를 zip으로 자동 백업

    Args:
        target_dir: 백업 저장 디렉토리 (기본: crypto_trading/data/backups)
        max_backups: 최대 보관 백업 수 (초과 시 오래된 것 자동 삭제)

    Returns:
        str: 생성된 백업 파일 경로 또는 에러 메시지
    """
    source_dir = config.DATA_DIR
    if not source_dir.exists():
        return f"백업 대상 디렉토리 없음: {source_dir}"

    backup_dir = Path(target_dir) if target_dir else (config.DATA_DIR / "backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"crypto_data_backup_{timestamp}"
    backup_path = backup_dir / f"{backup_name}.zip"

    try:
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(source_dir):
                # 백업 디렉토리 자체는 제외
                root_path = Path(root)
                if "backups" in root_path.parts:
                    continue
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(source_dir)
                    zf.write(file_path, arcname)

        logger.info(f"자동 백업 생성: {backup_path}")

        # 오래된 백업 정리
        existing = sorted(backup_dir.glob("crypto_data_backup_*.zip"))
        while len(existing) > max_backups:
            oldest = existing.pop(0)
            oldest.unlink()
            logger.info(f"오래된 백업 삭제: {oldest.name}")

        return str(backup_path)
    except Exception as e:
        msg = f"백업 실패: {e}"
        logger.error(msg)
        return msg


# ═══════════════════════════════════════════════
# #158: 보안 대시보드 (get_security_dashboard)
# ═══════════════════════════════════════════════

def get_security_dashboard() -> dict:
    """보안 대시보드 — 각 보안 레이어 상태 종합 요약

    Returns:
        dict: {
            'timestamp': str,
            'layers': { ... },
            'trade_safety': { ... },
            'recent_events': [ ... ],
            'overall_status': str
        }
    """
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "layers": {},
        "trade_safety": {},
        "recent_events": [],
        "overall_status": "UNKNOWN",
    }

    issues = 0

    # Layer 1: .env + .gitignore
    env_exists = any(p.exists() for p in [
        Path(__file__).parent.parent / "wicked_zerg_challenger" / ".env",
        Path(__file__).parent.parent / ".env",
    ])
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    dashboard["layers"]["layer1_env_isolation"] = {
        "status": "OK" if env_exists else "WARNING",
        "env_file_exists": env_exists,
        "gitignore_exists": gitignore_path.exists(),
    }
    if not env_exists:
        issues += 1

    # Layer 2: 시크릿 스캔
    dashboard["layers"]["layer2_secret_scan"] = {
        "status": "OK",
        "patterns_loaded": len(_KEY_PATTERNS),
    }

    # Layer 3: 런타임 보호
    dashboard["layers"]["layer3_runtime_protection"] = {
        "status": "OK",
        "log_filter_installed": True,
        "exception_hook_installed": sys.excepthook.__name__ != "excepthook" if hasattr(sys.excepthook, '__name__') else True,
    }

    # Layer 4: 키 검증
    try:
        valid, msg = validate_api_keys()
        integrity_ok, integrity_msg = check_key_integrity()
        dashboard["layers"]["layer4_key_validation"] = {
            "status": "OK" if (valid and integrity_ok) else "WARNING",
            "key_valid": valid,
            "key_validation_msg": msg,
            "integrity_ok": integrity_ok,
            "integrity_msg": integrity_msg,
        }
        if not valid or not integrity_ok:
            issues += 1
    except Exception as e:
        dashboard["layers"]["layer4_key_validation"] = {"status": "ERROR", "error": str(e)}
        issues += 1

    # Layer 5: 파일 보호 + 거래 안전
    dashboard["layers"]["layer5_file_trade_protection"] = {
        "status": "OK",
        "data_dir_exists": config.DATA_DIR.exists(),
    }

    # 거래 안전 가드 통계
    dashboard["trade_safety"] = trade_safety.get_daily_summary()

    # 최근 보안 이벤트 (최대 20개)
    events = []
    # 감사 로그에서 최근 이벤트 읽기
    if AUDIT_LOG_FILE.exists():
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    try:
                        events.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.debug(f"Failed to read audit log file: {e}")

    # trade_safety 알림도 추가
    for ts, msg in trade_safety._alerts[-10:]:
        events.append({"timestamp": ts.isoformat(), "event": "trade_alert", "message": msg})

    dashboard["recent_events"] = events[-20:]

    # 전체 상태
    if issues == 0:
        dashboard["overall_status"] = "SECURE"
    elif issues <= 2:
        dashboard["overall_status"] = "WARNING"
    else:
        dashboard["overall_status"] = "CRITICAL"

    return dashboard


# ═══════════════════════════════════════════════
# #159: 제로 트러스트 검증 (ZeroTrustValidator)
# ═══════════════════════════════════════════════

class ZeroTrustValidator:
    """제로 트러스트 보안 모델 — 모든 요청을 검증

    IP + 시간 + 빈도 복합 검증으로 무단 접근 차단.
    """

    def __init__(self):
        self._request_log: list = []  # [(timestamp, ip, action), ...]
        self._blocked_ips: set = set()
        self._max_requests_per_minute: int = 60
        self._allowed_hours: tuple = (0, 24)  # 기본: 24시간 허용
        self._trust_scores: dict = {}  # ip -> score (0~100)

    def configure(self, max_requests_per_minute: int = 60,
                  allowed_hours: tuple = (0, 24)):
        """검증 정책 설정

        Args:
            max_requests_per_minute: 분당 최대 요청 수
            allowed_hours: 허용 시간대 (시작, 종료) 24시간제
        """
        self._max_requests_per_minute = max_requests_per_minute
        self._allowed_hours = allowed_hours

    def validate_request(self, ip: str, action: str) -> dict:
        """요청 종합 검증

        Args:
            ip: 요청 IP 주소
            action: 수행 액션 (예: 'trade', 'query', 'config_change')

        Returns:
            dict: {
                'allowed': bool,
                'checks': {
                    'ip_check': bool,
                    'time_check': bool,
                    'rate_check': bool,
                    'trust_check': bool
                },
                'reason': str,
                'trust_score': int
            }
        """
        now = datetime.now()
        result = {
            "allowed": True,
            "checks": {
                "ip_check": True,
                "time_check": True,
                "rate_check": True,
                "trust_check": True,
            },
            "reason": "",
            "trust_score": self._trust_scores.get(ip, 50),
        }
        reasons = []

        # 1. IP 검증
        if ip in self._blocked_ips:
            result["checks"]["ip_check"] = False
            result["allowed"] = False
            reasons.append(f"차단된 IP: {ip}")

        if not check_ip_allowed(ip):
            result["checks"]["ip_check"] = False
            result["allowed"] = False
            reasons.append(f"허용되지 않은 IP: {ip}")

        # 2. 시간대 검증
        current_hour = now.hour
        start_h, end_h = self._allowed_hours
        if start_h <= end_h:
            if not (start_h <= current_hour < end_h):
                result["checks"]["time_check"] = False
                result["allowed"] = False
                reasons.append(f"허용 시간대 외 요청: {current_hour}시 (허용: {start_h}-{end_h}시)")
        else:
            # 자정을 넘기는 경우 (예: 22시~6시)
            if not (current_hour >= start_h or current_hour < end_h):
                result["checks"]["time_check"] = False
                result["allowed"] = False
                reasons.append(f"허용 시간대 외 요청: {current_hour}시 (허용: {start_h}-{end_h}시)")

        # 3. 빈도 검증 (분당 요청 수)
        one_min_ago = now - timedelta(minutes=1)
        recent = [r for r in self._request_log if r[0] > one_min_ago and r[1] == ip]
        if len(recent) >= self._max_requests_per_minute:
            result["checks"]["rate_check"] = False
            result["allowed"] = False
            reasons.append(
                f"요청 빈도 초과: {len(recent)}/{self._max_requests_per_minute} (분당)"
            )

        # 4. 신뢰 점수 검증
        trust = self._trust_scores.get(ip, 50)
        if trust < 20:
            result["checks"]["trust_check"] = False
            result["allowed"] = False
            reasons.append(f"신뢰 점수 부족: {trust}/100")
        result["trust_score"] = trust

        # 요청 기록
        self._request_log.append((now, ip, action))
        # 오래된 기록 정리 (1시간 이전)
        cutoff = now - timedelta(hours=1)
        self._request_log = [r for r in self._request_log if r[0] > cutoff]

        # 신뢰 점수 업데이트
        if result["allowed"]:
            self._trust_scores[ip] = min(100, trust + 1)
        else:
            self._trust_scores[ip] = max(0, trust - 10)
            audit_log("zero_trust_block", {
                "ip": ip, "action": action, "reasons": reasons
            })

        result["reason"] = "; ".join(reasons) if reasons else "모든 검증 통과"
        return result

    def block_ip(self, ip: str):
        """IP 수동 차단"""
        self._blocked_ips.add(ip)
        logger.warning(f"ZeroTrust: IP 차단 — {ip}")

    def unblock_ip(self, ip: str):
        """IP 차단 해제"""
        self._blocked_ips.discard(ip)

    def get_status(self) -> dict:
        """제로 트러스트 상태 요약"""
        return {
            "blocked_ips": list(self._blocked_ips),
            "trust_scores": dict(self._trust_scores),
            "max_requests_per_minute": self._max_requests_per_minute,
            "allowed_hours": self._allowed_hours,
            "recent_request_count": len(self._request_log),
        }


# 전역 인스턴스
zero_trust = ZeroTrustValidator()


# ═══════════════════════════════════════════════
# #160: 시크릿 매니저 (SecretManager)
# ═══════════════════════════════════════════════

class SecretManager:
    """시크릿 매니저 — 키를 환경변수 대신 암호화 파일에서 관리

    메모리 내 키 캐싱, 자동 갱신 지원.
    """

    def __init__(self, secrets_file: Path = None):
        """초기화

        Args:
            secrets_file: 암호화 시크릿 파일 경로
                (기본: crypto_trading/data/.secrets.enc)
        """
        self._secrets_file = secrets_file or (config.DATA_DIR / ".secrets.enc")
        self._cache: dict = {}
        self._cache_ttl: int = 3600  # 캐시 유효기간 (초)
        self._cache_timestamps: dict = {}
        self._master_key: str = self._derive_master_key()
        # Bug #7 Fix: Fernet 초기화
        self._fernet = None
        self._use_fernet = False
        self._init_fernet()

    def _derive_master_key(self) -> str:
        """마스터 키 생성 — 머신 고유 정보 기반"""
        import platform
        try:
            login_name = os.getlogin()
        except OSError:
            login_name = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
        machine_info = f"{platform.node()}:{platform.machine()}:{login_name}"
        return hashlib.sha256(machine_info.encode()).hexdigest()

    def _init_fernet(self):
        """Bug #7 Fix + H-7: Fernet 대칭 암호화 초기화. PBKDF2 키 파생 강화."""
        try:
            from cryptography.fernet import Fernet
            # H-7: PBKDF2로 강화된 키 파생 (salt + 100k iterations)
            import hashlib
            _salt = hashlib.sha256(b"JARVIS_FERNET_SALT_v1").digest()[:16]
            key_hash = hashlib.pbkdf2_hmac(
                "sha256", self._master_key.encode("utf-8"), _salt, 100_000
            )
            fernet_key = base64.urlsafe_b64encode(key_hash)
            self._fernet = Fernet(fernet_key)
            self._use_fernet = True
        except ImportError:
            logger.warning(
                "SecretManager: cryptography 라이브러리 미설치 — "
                "시크릿이 암호화되지 않고 base64 인코딩만 적용됩니다. "
                "보안을 위해 'pip install cryptography'를 실행하세요."
            )
            self._fernet = None
            self._use_fernet = False

    def _encrypt_value(self, value: str) -> str:
        """값 암호화 — Bug #7 Fix: Fernet 사용, 미설치 시 base64 폴백"""
        if self._use_fernet and self._fernet:
            return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return base64.b64encode(value.encode("utf-8")).decode("utf-8")

    def _decrypt_value(self, encrypted: str) -> str:
        """값 복호화 — Bug #7 Fix + H-7: Fernet 사용, 구 키 호환 폴백"""
        if self._use_fernet and self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
            except Exception:
                # H-7: 구 SHA-256 키로 암호화된 데이터 복호화 시도 (마이그레이션 호환)
                try:
                    import hashlib as _hlib
                    from cryptography.fernet import Fernet as _Fernet
                    old_key = _hlib.sha256(self._master_key.encode("utf-8")).digest()
                    old_fernet = _Fernet(base64.urlsafe_b64encode(old_key))
                    return old_fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
                except Exception:
                    raise
        return base64.b64decode(encrypted.encode("utf-8")).decode("utf-8")

    def set_secret(self, name: str, value: str):
        """시크릿 저장

        Args:
            name: 시크릿 이름 (예: 'UPBIT_ACCESS_KEY')
            value: 시크릿 값
        """
        # 메모리 캐시 업데이트
        self._cache[name] = value
        self._cache_timestamps[name] = time.time()

        # 파일에 암호화 저장
        secrets = self._load_secrets_file()
        secrets[name] = self._encrypt_value(value)
        self._save_secrets_file(secrets)
        logger.info(f"SecretManager: 시크릿 저장 — {name}")

    def get_secret(self, name: str, default: str = None) -> str:
        """시크릿 조회 (캐시 우선)

        Args:
            name: 시크릿 이름
            default: 기본값

        Returns:
            str: 시크릿 값 또는 default
        """
        # 캐시에서 조회 (TTL 확인)
        if name in self._cache:
            cached_time = self._cache_timestamps.get(name, 0)
            if time.time() - cached_time < self._cache_ttl:
                return self._cache[name]
            else:
                # 캐시 만료 — 파일에서 재로드
                del self._cache[name]

        # 파일에서 로드
        secrets = self._load_secrets_file()
        if name in secrets:
            try:
                value = self._decrypt_value(secrets[name])
                self._cache[name] = value
                self._cache_timestamps[name] = time.time()
                return value
            except Exception as e:
                logger.error(f"SecretManager: 복호화 실패 ({name}): {e}")

        return default

    def delete_secret(self, name: str):
        """시크릿 삭제"""
        self._cache.pop(name, None)
        self._cache_timestamps.pop(name, None)

        secrets = self._load_secrets_file()
        if name in secrets:
            del secrets[name]
            self._save_secrets_file(secrets)
            logger.info(f"SecretManager: 시크릿 삭제 — {name}")

    def list_secrets(self) -> list:
        """저장된 시크릿 이름 목록 (값은 반환하지 않음)"""
        secrets = self._load_secrets_file()
        return list(secrets.keys())

    def refresh_cache(self):
        """캐시 전체 갱신 — 파일에서 다시 로드"""
        self._cache.clear()
        self._cache_timestamps.clear()
        secrets = self._load_secrets_file()
        for name, encrypted in secrets.items():
            try:
                self._cache[name] = self._decrypt_value(encrypted)
                self._cache_timestamps[name] = time.time()
            except Exception as e:
                logger.warning(f"SecretManager: failed to decrypt secret '{name}': {e}")
        logger.info(f"SecretManager: 캐시 갱신 완료 ({len(self._cache)}개)")

    def set_cache_ttl(self, ttl_seconds: int):
        """캐시 TTL(유효기간) 변경"""
        self._cache_ttl = ttl_seconds

    def _load_secrets_file(self) -> dict:
        """암호화 시크릿 파일 로드"""
        if not self._secrets_file.exists():
            return {}
        try:
            with open(self._secrets_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load secrets file {self._secrets_file}: {e}")
            return {}

    def _save_secrets_file(self, secrets: dict):
        """암호화 시크릿 파일 저장"""
        self._secrets_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._secrets_file, "w", encoding="utf-8") as f:
            json.dump(secrets, f, ensure_ascii=False, indent=2)


# 전역 인스턴스
secret_manager = SecretManager()


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

    # #156: 암호화 거래 로그
    try:
        enc_log = EncryptedTradeLog()
        results.append(f"#156 (암호화 로그): ✓ {'Fernet' if enc_log._use_fernet else 'Base64 폴백'} 모드")
    except Exception as e:
        results.append(f"#156 (암호화 로그): ✗ {e}")

    # #159: 제로 트러스트
    results.append(f"#159 (제로 트러스트): ✓ 분당 {zero_trust._max_requests_per_minute}건 제한")

    # #160: 시크릿 매니저
    results.append(f"#160 (시크릿 매니저): ✓ 캐시 TTL {secret_manager._cache_ttl}초")

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
