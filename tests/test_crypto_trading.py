"""
암호화폐 거래 모듈 유닛 테스트 (#171)

테스트 범위:
  - 모듈 import 검증
  - 설정(config) 값 검증
  - config_loader 기능 테스트
  - unified_logger 기본 기능 테스트
"""

import os
import sys
from pathlib import Path

import pytest

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCryptoImports:
    """암호화폐 거래 모듈의 import가 정상인지 검증한다."""

    def test_import_config(self):
        """crypto_trading.config 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import config
        assert hasattr(config, "DEFAULT_FIAT")
        assert hasattr(config, "MIN_ORDER_AMOUNT")

    def test_import_security(self):
        """crypto_trading.security 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import security
        assert hasattr(security, "trade_safety")

    def test_import_upbit_client(self):
        """crypto_trading.upbit_client 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import upbit_client
        assert hasattr(upbit_client, "UpbitClient")

    def test_import_auto_trader(self):
        """crypto_trading.auto_trader 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import auto_trader
        assert hasattr(auto_trader, "AutoTrader")

    def test_import_portfolio_tracker(self):
        """crypto_trading.portfolio_tracker 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import portfolio_tracker
        assert hasattr(portfolio_tracker, "PortfolioTracker")

    def test_import_market_analyzer(self):
        """crypto_trading.market_analyzer 모듈을 import할 수 있는지 확인한다."""
        from crypto_trading import market_analyzer
        assert hasattr(market_analyzer, "MarketAnalyzer")


class TestCryptoConfig:
    """암호화폐 거래 설정 값이 올바른지 검증한다."""

    def test_default_fiat_is_krw(self):
        """기본 법정화폐가 KRW인지 확인한다."""
        from crypto_trading.config import DEFAULT_FIAT
        assert DEFAULT_FIAT == "KRW"

    def test_min_order_amount_positive(self):
        """최소 주문 금액이 양수인지 확인한다."""
        from crypto_trading.config import MIN_ORDER_AMOUNT
        assert MIN_ORDER_AMOUNT > 0

    def test_max_single_order_ratio_range(self):
        """1회 최대 주문 비율이 0~1 사이인지 확인한다."""
        from crypto_trading.config import MAX_SINGLE_ORDER_RATIO
        assert 0 < MAX_SINGLE_ORDER_RATIO <= 1.0

    def test_max_total_investment_ratio_range(self):
        """최대 투자 비율이 0~1 사이인지 확인한다."""
        from crypto_trading.config import MAX_TOTAL_INVESTMENT_RATIO
        assert 0 < MAX_TOTAL_INVESTMENT_RATIO <= 1.0

    def test_stop_loss_is_negative(self):
        """손절 퍼센트가 음수인지 확인한다."""
        from crypto_trading.config import DEFAULT_STOP_LOSS_PCT
        assert DEFAULT_STOP_LOSS_PCT < 0

    def test_take_profit_is_positive(self):
        """익절 퍼센트가 양수인지 확인한다."""
        from crypto_trading.config import DEFAULT_TAKE_PROFIT_PCT
        assert DEFAULT_TAKE_PROFIT_PCT > 0

    def test_watch_list_not_empty(self):
        """관심 코인 목록이 비어있지 않은지 확인한다."""
        from crypto_trading.config import DEFAULT_WATCH_LIST
        assert len(DEFAULT_WATCH_LIST) > 0

    def test_watch_list_format(self):
        """관심 코인 목록의 형식이 'KRW-XXX'인지 확인한다."""
        from crypto_trading.config import DEFAULT_WATCH_LIST
        for coin in DEFAULT_WATCH_LIST:
            assert coin.startswith("KRW-"), f"잘못된 코인 형식: {coin}"

    def test_data_dir_exists(self):
        """데이터 디렉토리가 존재하는지 확인한다."""
        from crypto_trading.config import DATA_DIR
        assert DATA_DIR.exists(), f"데이터 디렉토리가 없습니다: {DATA_DIR}"


class TestConfigLoader:
    """config_loader 모듈의 기능을 테스트한다."""

    def test_import_config_loader(self):
        """config_loader 모듈을 import할 수 있는지 확인한다."""
        import config_loader
        assert hasattr(config_loader, "load_config")
        assert hasattr(config_loader, "get")

    def test_load_config_returns_dict(self):
        """load_config()가 딕셔너리를 반환하는지 확인한다."""
        from config_loader import load_config
        config = load_config()
        assert isinstance(config, dict)

    def test_get_project_name(self):
        """프로젝트 이름을 가져올 수 있는지 확인한다."""
        from config_loader import load_config, get
        load_config()
        name = get("project.name")
        assert name is not None
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_proxy_port(self):
        """프록시 포트 설정을 가져올 수 있는지 확인한다."""
        from config_loader import load_config, get
        load_config()
        port = get("proxy.port")
        assert isinstance(port, int)
        assert port > 0

    def test_get_nonexistent_key_returns_default(self):
        """존재하지 않는 키에 대해 기본값을 반환하는지 확인한다."""
        from config_loader import load_config, get
        load_config()
        result = get("no.such.key", default="테스트기본값")
        assert result == "테스트기본값"

    def test_env_override(self, monkeypatch):
        """환경변수로 설정값을 오버라이드할 수 있는지 확인한다."""
        monkeypatch.setenv("PROXY_PORT", "9999")
        from config_loader import load_config, get
        # 캐시를 무시하고 재로드
        import config_loader
        config_loader._config = None
        cfg = load_config()
        port = get("proxy.port")
        assert port == 9999


class TestUnifiedLogger:
    """unified_logger 모듈의 기본 기능을 테스트한다."""

    def test_import_unified_logger(self):
        """unified_logger 모듈을 import할 수 있는지 확인한다."""
        from unified_logger import UnifiedLogger
        assert hasattr(UnifiedLogger, "setup")
        assert hasattr(UnifiedLogger, "get_logger")

    def test_get_logger_returns_logger(self):
        """get_logger가 Logger 인스턴스를 반환하는지 확인한다."""
        import logging
        from unified_logger import UnifiedLogger
        UnifiedLogger.shutdown()
        logger = UnifiedLogger.get_logger("test.crypto")
        assert isinstance(logger, logging.Logger)
        UnifiedLogger.shutdown()

    def test_setup_with_json_format(self, temp_dir):
        """JSON 포맷 설정이 정상 작동하는지 확인한다."""
        from unified_logger import UnifiedLogger
        UnifiedLogger.shutdown()
        UnifiedLogger.setup(
            log_dir=str(temp_dir),
            json_format=True,
            log_level="DEBUG",
            console_output=False,
        )
        logger = UnifiedLogger.get_logger("test.json")
        # 예외 없이 로깅할 수 있으면 성공
        logger.info("JSON 테스트 메시지")
        UnifiedLogger.shutdown()

    def test_set_level(self, temp_dir):
        """동적 로그 레벨 변경이 작동하는지 확인한다."""
        import logging
        from unified_logger import UnifiedLogger
        UnifiedLogger.shutdown()
        UnifiedLogger.setup(
            log_dir=str(temp_dir),
            log_level="INFO",
            console_output=False,
        )
        UnifiedLogger.set_level("DEBUG")
        assert UnifiedLogger._log_level == logging.DEBUG
        UnifiedLogger.shutdown()
