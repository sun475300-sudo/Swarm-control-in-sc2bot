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

# wicked_zerg_challenger 의 ``from utils.logger import ...`` 같은 상대 import 패턴이
# 작동하려면 패키지 루트가 프로젝트 루트보다 sys.path 앞쪽에 있어야 한다. 그렇지 않으면
# 프로젝트 루트의 다른 ``utils`` 패키지(jarvis_features 용 ``openclaw_helper``)가 먼저
# 캐시되어 blackboard.py 등에서 ``utils.logger`` 를 찾지 못한다.
#
# pytest 가 import-mode=prepend 로 PROJECT_ROOT 를 [0] 에 다시 끼워넣기 때문에 WZC 를
# 단순히 한 번 더 prepend 한 뒤, ``pytest_configure`` 훅에서도 한 번 더 보정한다.
_WZC_PKG = PROJECT_ROOT / "wicked_zerg_challenger"


def _ensure_wzc_first() -> None:
    """``wicked_zerg_challenger`` 디렉토리가 sys.path 최상단에 오도록 강제한다."""
    s = str(_WZC_PKG)
    if not _WZC_PKG.is_dir():
        return
    # 모든 기존 occurrence 제거 후 맨 앞에 삽입
    while s in sys.path:
        sys.path.remove(s)
    sys.path.insert(0, s)


# ``scripts`` 처럼 두 곳에 동일 이름이 존재하는 패키지는 부분 캐시 문제를 일으킨다.
# 한 테스트가 ``local_training/scripts`` (regular package) 를 캐시해 두면 그 다음에 컬렉트되는
# 테스트가 진짜 ``scripts.ladder_tracker`` 를 찾지 못한다. 매 컬렉트 시작 시 namespace
# 패키지 캐시를 비워 다음 import 가 fresh 한 namespace 검색을 하도록 한다.
_AMBIGUOUS_NAMESPACES = ("scripts",)


def _refresh_ambiguous_namespaces() -> None:
    for n in _AMBIGUOUS_NAMESPACES:
        m = sys.modules.get(n)
        if m is None:
            continue
        if getattr(m, "__file__", None) is None:
            sys.modules.pop(n, None)
            for key in list(sys.modules.keys()):
                if key.startswith(n + "."):
                    sys.modules.pop(key, None)


_ensure_wzc_first()


def pytest_configure(config):  # pragma: no cover - 훅
    _ensure_wzc_first()


def pytest_collectstart(collector):  # pragma: no cover - 훅
    _ensure_wzc_first()
    _refresh_ambiguous_namespaces()


# burnysc2 미설치 환경에서도 컬렉션이 통과하도록 공용 stub 주입.
# 실제 sc2 라이브러리가 설치된 경우엔 no-op.
try:
    import sc2  # type: ignore  # noqa: F401
except ImportError:
    from tests._sc2_stub import install_sc2_stub

    install_sc2_stub()


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
