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

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# wicked_zerg_challenger/ 도 sys.path 에 추가.
#
# 봇 코드는 `from config.unit_configs import ...`, `from utils.logger import
# get_logger` 처럼 패키지 내부 모듈을 절대 import 한다. 봇 자체는 자기
# 디렉토리를 cwd 로 실행해서 동작하지만 pytest 가
# wicked_zerg_challenger.economy_manager 를 import 하면 `config` 와
# `utils` 가 sys.path 에 없어서 ModuleNotFoundError 가 난다. 그 결과
# EconomyManager / StrategyManager 를 사용하는 약 30 개 테스트가 조용히 SKIP 된다.
#
# 추가로 PROJECT_ROOT 에는 logger.py 가 없는 stub `utils/` 패키지가 있어서
# `wicked_zerg_challenger/` 보다 먼저 검색되면 import 가 stub 을 만나
# 실패한다. pytest 는 자기가 알아서 PROJECT_ROOT 를 sys.path 에 prepend 하므로
# pytest_configure 에서 BOT_PACKAGE_ROOT 를 다시 0번 인덱스로 강제 고정한다.
BOT_PACKAGE_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if BOT_PACKAGE_ROOT.is_dir() and str(BOT_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PACKAGE_ROOT))


def pytest_configure(config):  # noqa: D401 - pytest hook
    """`pytest` 가 자체적으로 PROJECT_ROOT 를 sys.path 에 prepend 한 뒤
    실행되는 훅. BOT_PACKAGE_ROOT 를 다시 0번 인덱스로 강제 고정해서
    PROJECT_ROOT/utils stub 이 wicked_zerg_challenger/utils 를 가리지 않도록 한다.
    """
    bot_root = str(BOT_PACKAGE_ROOT)
    if bot_root in sys.path:
        sys.path.remove(bot_root)
    sys.path.insert(0, bot_root)

    # 단일 파일/단일 테스트 실행 모드에서 pytest 의 자동 rootdir prepend 가
    # BOT_PACKAGE_ROOT 보다 늦게 일어나는 케이스를 대비해, `utils` /
    # `config` 가 pytest 실행 시점에 stub 패키지로 해석되어 있으면 강제로
    # 제거한다. 이후 `from utils.logger import ...` 가 import 될 때
    # sys.path 의 BOT_PACKAGE_ROOT (wicked_zerg_challenger/) 에서 다시
    # 찾도록 한다.
    for _shadowed in ("utils", "config"):
        mod = sys.modules.get(_shadowed)
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", "") or ""
        # bot 패키지의 utils 가 이미 import 됐다면 유지; 그렇지 않고
        # PROJECT_ROOT 직속 stub 만 import 돼 있다면 제거.
        if str(BOT_PACKAGE_ROOT) not in mod_file:
            sys.modules.pop(_shadowed, None)


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
