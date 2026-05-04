"""
pytest 공통 fixtures (#171)

모든 테스트 파일에서 공유할 수 있는 fixture와 설정을 정의한다.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 프로젝트 루트와 wicked_zerg_challenger 디렉토리를 sys.path에 추가.
# wicked_zerg_challenger 내부 모듈은 `from config.x`, `from utils.x`,
# `from local_training.x` 형태로 임포트하므로 봇 디렉토리 자체가 sys.path에
# 있어야 단독 테스트 실행에서도 임포트가 성공한다. 루트의 `utils/`보다
# 우선되도록 봇 경로를 먼저(인덱스 0) 위치시킨다.
PROJECT_ROOT = Path(__file__).parent.parent
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if WZC_ROOT.exists() and str(WZC_ROOT) not in sys.path:
    sys.path.insert(0, str(WZC_ROOT))

# pytest는 conftest 로드 후 PROJECT_ROOT를 sys.path[0]으로 끌어올린다.
# 그러면 PROJECT_ROOT/utils/ 가 wicked_zerg_challenger/utils/ 를 가려
# `from utils.logger import get_logger` 가 ImportError를 일으킨다.
# conftest 시점에 봇의 utils 패키지를 사전 import해 sys.modules에 못 박아
# 이후 모든 `utils.*` 요청이 봇 패키지로 해결되도록 한다.
if WZC_ROOT.exists():
    try:
        import utils as _wzc_utils  # noqa: F401  (wicked_zerg_challenger/utils/__init__.py)
        import utils.logger as _wzc_utils_logger  # noqa: F401
    except Exception:  # noqa: BLE001 — utils 누락 환경에서는 그냥 진행
        pass


# ═══════════════════════════════════════════════════════
# 경로 관련 Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture
def project_root() -> Path:
    """프로젝트 루트 디렉토리 경로를 반환한다."""
    return PROJECT_ROOT


@pytest.fixture
def temp_dir():
    """테스트용 임시 디렉토리를 생성하고, 테스트 후 자동 삭제한다."""
    tmpdir = tempfile.mkdtemp(prefix="jarvis_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


# ═══════════════════════════════════════════════════════
# 환경변수 Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture
def clean_env(monkeypatch):
    """
    테스트 실행 동안 민감한 환경변수를 제거한다.
    테스트 후 원래 값으로 복원된다 (monkeypatch가 자동 처리).
    """
    sensitive_keys = [
        "UPBIT_ACCESS_KEY",
        "UPBIT_SECRET_KEY",
        "ANTHROPIC_API_KEY",
        "DB_PASSWORD",
    ]
    for key in sensitive_keys:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def mock_env(monkeypatch):
    """
    테스트용 가짜 환경변수를 설정한다.
    실제 API 호출을 방지하기 위해 더미 값을 사용한다.
    """
    env_vars = {
        "UPBIT_ACCESS_KEY": "test_access_key_12345",
        "UPBIT_SECRET_KEY": "test_secret_key_67890",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "LOG_LEVEL": "DEBUG",
        "DRY_RUN": "true",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


# ═══════════════════════════════════════════════════════
# 설정 관련 Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture
def sample_config():
    """테스트용 기본 설정 딕셔너리를 반환한다."""
    return {
        "project": {
            "name": "JARVIS Test",
            "version": "0.0.1",
            "environment": "test",
        },
        "proxy": {
            "port": 3456,
            "host": "127.0.0.1",
        },
        "crypto": {
            "trading": {
                "dry_run": True,
                "min_order_amount": 5000,
                "default_fiat": "KRW",
            },
        },
        "logging": {
            "level": "DEBUG",
            "json_format": False,
        },
    }


@pytest.fixture
def sample_config_yaml(temp_dir, sample_config):
    """테스트용 YAML 설정 파일을 임시 디렉토리에 생성하여 경로를 반환한다."""
    try:
        import yaml

        config_path = temp_dir / "config.yaml"
        config_path.write_text(
            yaml.dump(sample_config, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        return config_path
    except ImportError:
        pytest.skip("PyYAML이 설치되어 있지 않아 YAML 테스트를 건너뜁니다.")


# ═══════════════════════════════════════════════════════
# Mock Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture
def mock_upbit_client():
    """UpbitClient의 Mock 객체를 반환한다. 실제 API 호출 없이 테스트할 수 있다."""
    mock = MagicMock()
    mock.get_balances.return_value = [
        {"currency": "KRW", "balance": "1000000", "avg_buy_price": "0"},
        {"currency": "BTC", "balance": "0.01", "avg_buy_price": "50000000"},
    ]
    mock.get_ticker.return_value = {
        "market": "KRW-BTC",
        "trade_price": 55000000,
        "change": "RISE",
        "signed_change_rate": 0.02,
    }
    mock.get_orderbook.return_value = {
        "orderbook_units": [
            {"ask_price": 55100000, "bid_price": 54900000},
        ]
    }
    return mock


@pytest.fixture
def mock_logger():
    """테스트용 Mock 로거를 반환한다."""
    mock = MagicMock()
    mock.debug = MagicMock()
    mock.info = MagicMock()
    mock.warning = MagicMock()
    mock.error = MagicMock()
    mock.critical = MagicMock()
    return mock
