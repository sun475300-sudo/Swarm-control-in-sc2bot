"""
pytest 공통 fixtures (#171)

모든 테스트 파일에서 공유할 수 있는 fixture와 설정을 정의한다.
"""

import os
import sys
import tempfile
import shutil
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# wicked_zerg_challenger도 path에 추가 (sc2 호환 스텁 사용을 위해)
_WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if str(_WZC_ROOT) not in sys.path:
    sys.path.insert(0, str(_WZC_ROOT))


def _install_sc2_stub_modules() -> None:
    """sc2 미설치 환경에서 가짜 sc2 모듈 트리를 sys.modules에 주입.

    tests/test_advanced_scout_system_v2.py 등 5개 파일은 모듈 상단에서
    `from sc2... import ...`를 시도하고 실패하면 ``pytest.skip(...,
    allow_module_level=True)`` 로 모듈 전체를 스킵한다. 본 함수는
    `wicked_zerg_challenger/_sc2_compat.py`의 메타클래스 스텁들을 sys.modules에
    `sc2`/`sc2.ids.*`/`sc2.position`/`sc2.unit` 등으로 주입하여 import를
    성공시킨다. 그러면 해당 테스트 파일들이 collection 단계에서 skip되지
    않고 실제 단위 테스트가 실행된다.

    진짜 burnysc2가 설치되어 있으면 이 함수는 no-op이다.
    """
    try:
        import sc2  # noqa: F401
        return  # 진짜 sc2 사용
    except Exception:
        pass

    try:
        from _sc2_compat import (  # type: ignore
            BotAI,
            UnitTypeId,
            AbilityId,
            UpgradeId,
            Race,
            Difficulty,
            Result,
            Bot,
            Computer,
            Point2,
            Unit,
            Units,
            maps,
            run_game,
        )
    except ImportError:
        # _sc2_compat이 없는 환경 (예: 외부 체크아웃)에서는 조용히 포기.
        return

    def _mod(name: str, **attrs) -> types.ModuleType:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    sc2_pkg = _mod("sc2", maps=maps)
    sc2_pkg.__path__ = []

    sc2_ids = _mod("sc2.ids")
    sc2_ids.__path__ = []

    _mod("sc2.bot_ai", BotAI=BotAI)
    _mod("sc2.ids.unit_typeid", UnitTypeId=UnitTypeId)
    _mod("sc2.ids.ability_id", AbilityId=AbilityId)
    _mod("sc2.ids.upgrade_id", UpgradeId=UpgradeId)
    _mod("sc2.data", Race=Race, Difficulty=Difficulty, Result=Result)
    _mod("sc2.player", Bot=Bot, Computer=Computer)
    _mod("sc2.position", Point2=Point2)
    _mod("sc2.unit", Unit=Unit)
    _mod("sc2.units", Units=Units)
    _mod("sc2.main", run_game=run_game)
    sys.modules["sc2.maps"] = (
        maps if hasattr(maps, "__name__") else types.ModuleType("sc2.maps")
    )
    sys.modules["sc2.maps"].get = maps.get  # type: ignore[attr-defined]


_install_sc2_stub_modules()


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
