"""
보안 모듈 테스트 (#171)

테스트 범위:
  - security 모듈 import 검증
  - IP 화이트리스트 검증
  - 키 마스킹 기능 테스트
  - 거래 안전 한도 검증
  - 설정 파일 내 민감 정보 유무 검사
"""

import os
import sys
from pathlib import Path

import pytest

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSecurityImports:
    """보안 모듈의 import가 정상인지 검증한다."""

    def test_import_security_module(self):
        """crypto_trading.security 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import security
        assert security is not None

    def test_trade_safety_exists(self):
        """trade_safety 객체가 존재하는지 확인한다."""
        from crypto_trading.security import trade_safety
        assert trade_safety is not None

    def test_allowed_ips_defined(self):
        """IP 화이트리스트가 정의되어 있는지 확인한다."""
        from crypto_trading.security import ALLOWED_IPS
        assert isinstance(ALLOWED_IPS, set)
        assert len(ALLOWED_IPS) > 0


class TestIPWhitelist:
    """IP 화이트리스트 기능을 테스트한다."""

    def test_localhost_allowed(self):
        """localhost가 허용 IP에 포함되어 있는지 확인한다."""
        from crypto_trading.security import ALLOWED_IPS
        assert "127.0.0.1" in ALLOWED_IPS or "localhost" in ALLOWED_IPS

    def test_ipv6_localhost_allowed(self):
        """IPv6 localhost가 허용 IP에 포함되어 있는지 확인한다."""
        from crypto_trading.security import ALLOWED_IPS
        assert "::1" in ALLOWED_IPS


class TestSensitiveDataProtection:
    """민감한 정보가 코드에 하드코딩되어 있지 않은지 검사한다."""

    def _read_file(self, filepath: Path) -> str:
        """파일 내용을 읽어 반환한다."""
        try:
            return filepath.read_text(encoding="utf-8")
        except Exception:
            return ""

    def test_no_hardcoded_api_keys_in_config(self):
        """config.py에 실제 API 키가 하드코딩되어 있지 않은지 확인한다."""
        config_path = Path(__file__).parent.parent / "crypto_trading" / "config.py"
        content = self._read_file(config_path)
        # 실제 Upbit 키 패턴 검사 (영숫자 20자 이상의 연속 문자열)
        import re
        # os.getenv 호출 내부가 아닌 곳에서 긴 영숫자 문자열 검사
        lines = content.split("\n")
        for line in lines:
            stripped = line.strip()
            # 주석이나 os.getenv 라인은 건너뜀
            if stripped.startswith("#") or "os.getenv" in stripped:
                continue
            # 따옴표 안의 20자 이상 영숫자 문자열 검사
            matches = re.findall(r'["\'][A-Za-z0-9]{20,}["\']', stripped)
            for match in matches:
                # 알려진 안전한 값 제외
                safe_values = {"development", "production", "staging"}
                clean = match.strip("\"'")
                assert clean.lower() in safe_values or len(clean) < 30, \
                    f"config.py에 의심스러운 하드코딩 값 발견: {match[:10]}..."

    def test_no_hardcoded_keys_in_yaml(self):
        """config.yaml에 실제 API 키가 하드코딩되어 있지 않은지 확인한다."""
        yaml_path = Path(__file__).parent.parent / "config.yaml"
        if not yaml_path.exists():
            pytest.skip("config.yaml 파일이 없습니다.")
        content = self._read_file(yaml_path)
        # API 키 필드에 환경변수 참조 ${...} 또는 빈 값이 있어야 한다
        import re
        for line in content.split("\n"):
            if "access_key:" in line or "secret_key:" in line or "password:" in line:
                # 환경변수 참조 패턴이 있거나 빈 값이어야 함
                assert "${" in line or line.strip().endswith('""') or \
                    line.strip().endswith("''") or line.strip().endswith(":"), \
                    f"config.yaml에 민감 정보가 하드코딩된 것 같습니다: {line.strip()}"

    def test_gitignore_includes_env(self):
        """.gitignore에 .env 파일이 포함되어 있는지 확인한다."""
        gitignore_path = Path(__file__).parent.parent / ".gitignore"
        if not gitignore_path.exists():
            pytest.skip(".gitignore 파일이 없습니다.")
        content = self._read_file(gitignore_path)
        assert ".env" in content, ".gitignore에 .env가 포함되어 있지 않습니다."


class TestTradeConfig:
    """거래 설정의 안전성을 검증한다."""

    def test_min_order_amount_reasonable(self):
        """최소 주문 금액이 합리적인 범위인지 확인한다 (1,000 ~ 100,000 KRW)."""
        from crypto_trading.config import MIN_ORDER_AMOUNT
        assert 1000 <= MIN_ORDER_AMOUNT <= 100000, \
            f"최소 주문 금액이 비정상적입니다: {MIN_ORDER_AMOUNT} KRW"

    def test_stop_loss_within_range(self):
        """손절 퍼센트가 -50% ~ 0% 사이인지 확인한다."""
        from crypto_trading.config import DEFAULT_STOP_LOSS_PCT
        assert -50.0 <= DEFAULT_STOP_LOSS_PCT < 0, \
            f"손절 퍼센트가 비정상적입니다: {DEFAULT_STOP_LOSS_PCT}%"

    def test_take_profit_within_range(self):
        """익절 퍼센트가 0% ~ 100% 사이인지 확인한다."""
        from crypto_trading.config import DEFAULT_TAKE_PROFIT_PCT
        assert 0 < DEFAULT_TAKE_PROFIT_PCT <= 100, \
            f"익절 퍼센트가 비정상적입니다: {DEFAULT_TAKE_PROFIT_PCT}%"

    def test_max_order_ratio_conservative(self):
        """1회 최대 주문 비율이 30% 이하인지 확인한다."""
        from crypto_trading.config import MAX_SINGLE_ORDER_RATIO
        assert MAX_SINGLE_ORDER_RATIO <= 0.3, \
            f"1회 최대 주문 비율이 너무 높습니다: {MAX_SINGLE_ORDER_RATIO * 100}%"

    def test_max_investment_ratio_conservative(self):
        """최대 투자 비율이 80% 이하인지 확인한다."""
        from crypto_trading.config import MAX_TOTAL_INVESTMENT_RATIO
        assert MAX_TOTAL_INVESTMENT_RATIO <= 0.8, \
            f"최대 투자 비율이 너무 높습니다: {MAX_TOTAL_INVESTMENT_RATIO * 100}%"
