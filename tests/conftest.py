"""
pytest 공통 fixtures (#171)

모든 테스트 파일에서 공유할 수 있는 fixture와 설정을 정의한다.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

WZC_PATH = str(PROJECT_ROOT / "wicked_zerg_challenger")


def _ensure_wzc_path_first():
    """wicked_zerg_challenger/utils가 root utils보다 먼저 탐색되도록 path를 재정렬한다."""
    # 기존 WZC_PATH 항목 제거 후 index 0에 재삽입
    while WZC_PATH in sys.path:
        sys.path.remove(WZC_PATH)
    sys.path.insert(0, WZC_PATH)
    # 루트 utils 패키지 캐시 제거
    for _mod in list(sys.modules.keys()):
        if _mod == "utils" or _mod.startswith("utils."):
            del sys.modules[_mod]


def _inject_sc2_stubs():
    """sc2가 설치되지 않은 테스트 환경에서 WZC utils가 임포트 가능하도록 최소 stub을 주입한다."""
    if "sc2" not in sys.modules:
        sc2_stub = MagicMock()

        class _Point2:
            def __init__(self, x=0.0, y=0.0):
                if isinstance(x, (tuple, list)):
                    self.x = float(x[0])
                    self.y = float(x[1])
                else:
                    self.x = float(x)
                    self.y = float(y)
            def __repr__(self):
                return f"Point2({self.x}, {self.y})"

        sc2_stub.position.Point2 = _Point2
        sys.modules["sc2"] = sc2_stub
        sys.modules["sc2.position"] = sc2_stub.position
        sys.modules["sc2.units"] = MagicMock()
        sys.modules["sc2.unit"] = MagicMock()
        sys.modules["sc2.bot_ai"] = MagicMock()
        sys.modules["sc2.ids"] = MagicMock()
        sys.modules["sc2.ids.unit_typeid"] = MagicMock()
        sys.modules["sc2.ids.ability_id"] = MagicMock()
        sys.modules["sc2.ids.upgrade_id"] = MagicMock()


# 모듈 로드 시 즉시 실행 (collection 전)
_inject_sc2_stubs()
_ensure_wzc_path_first()


def pytest_configure(config):
    """pytest 설정 단계에서 경로 및 sc2 stub을 보장한다."""
    _inject_sc2_stubs()
    _ensure_wzc_path_first()


def pytest_sessionstart(session):
    """세션 시작 시점에도 경로를 재보장한다."""
    _ensure_wzc_path_first()


def pytest_runtest_setup(item):
    """각 테스트 실행 직전: pytest가 rootdir를 sys.path[0]에 추가한 후에도 WZC_PATH를 최우선으로 보장한다."""
    _ensure_wzc_path_first()


def pytest_runtest_call(item):
    """테스트 함수 호출 직전 최종 경로 보장 (pytest_runtest_setup 이후에도 경로가 바뀌는 경우 방어)."""
    _ensure_wzc_path_first()


def pytest_collect_file(parent, file_path):
    """각 테스트 파일 수집 직전에도 경로를 보장한다 (collection-time import 보호)."""
    _ensure_wzc_path_first()


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
