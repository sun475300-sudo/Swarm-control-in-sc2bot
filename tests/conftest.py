"""
pytest 공통 fixtures (#171)

모든 테스트 파일에서 공유할 수 있는 fixture와 설정을 정의한다.
"""

import importlib.util
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 봇 코드 다수가 `from utils.logger import get_logger` 처럼 wicked_zerg_challenger
# 안의 utils 를 top-level 로 가정하고 import 한다. 봇을 정상 실행 환경에서는
# 그 디렉터리가 cwd 라 문제가 없지만, pytest 가 프로젝트 루트에서 실행되면
# `utils` 가 보이지 않아 collection 단계에서 ImportError 가 난다.
# 테스트에 한해 wicked_zerg_challenger 를 sys.path 에 끼워주면 해결된다.
WZC_ROOT = PROJECT_ROOT / "wicked_zerg_challenger"
if WZC_ROOT.exists() and str(WZC_ROOT) not in sys.path:
    sys.path.insert(0, str(WZC_ROOT))


def _install_sc2_stub() -> None:
    """sc2 패키지가 실제로 설치되어 있지 않을 때, 테스트가 import만 하면
    되는 정도의 최소 stub 을 sys.modules 에 등록한다.

    실제 sc2 가 있으면 아무 것도 하지 않는다. 효과:
      - test_queen_transfusion(*).py, test_advanced_scout_system_v2.py,
        test_spatial_query_optimizer.py, test_harassment_coordinator.py 가
        module-level skip 대신 실제로 실행된다.
      - 테스트가 사용하는 심볼만 노출하므로 실제 sc2 와 충돌하지 않는다.
    """
    if importlib.util.find_spec("sc2") is not None:
        return  # 진짜 sc2 가 우선

    class _StringEnumLike(type):
        """무엇을 받아도 새 멤버처럼 동작하는 enum-like 메타."""

        def __getattr__(cls, name):
            value = cls._members.setdefault(name, cls(name))  # type: ignore[attr-defined]
            return value

    class _IdBase(metaclass=_StringEnumLike):
        _members: dict = {}

        def __init__(self, name: str):
            self.name = name
            self.value = name

        def __repr__(self) -> str:  # pragma: no cover
            return f"{type(self).__name__}.{self.name}"

        def __eq__(self, other) -> bool:
            if isinstance(other, type(self)):
                return self.name == other.name
            return NotImplemented

        def __hash__(self) -> int:
            return hash((type(self).__name__, self.name))

    def _make_id_class(class_name: str) -> type:
        # 클래스마다 별도 _members dict 를 갖도록 동적 생성
        return type(class_name, (_IdBase,), {"_members": {}})

    UnitTypeId = _make_id_class("UnitTypeId")
    AbilityId = _make_id_class("AbilityId")
    UpgradeId = _make_id_class("UpgradeId")

    class Point2(tuple):
        def __new__(cls, position):
            if isinstance(position, Point2):
                return position
            try:
                x, y = position
            except (TypeError, ValueError):
                x, y = position, 0
            obj = super().__new__(cls, (float(x), float(y)))
            return obj

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        def distance_to(self, other) -> float:
            ox = getattr(other, "x", other[0] if hasattr(other, "__getitem__") else 0)
            oy = getattr(other, "y", other[1] if hasattr(other, "__getitem__") else 0)
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

    class Point3(Point2):
        def __new__(cls, position):
            if len(position) == 3:
                x, y, _z = position
            else:
                x, y = position
            return Point2.__new__(cls, (x, y))

    class Unit:  # pragma: no cover - test stub
        pass

    class Units(list):  # pragma: no cover - test stub
        def __init__(self, items=None, bot_object=None):
            super().__init__(items or [])

    class BotAI:  # pragma: no cover - test stub
        pass

    sc2 = types.ModuleType("sc2")
    sc2.__path__ = []  # 패키지로 인식

    ids = types.ModuleType("sc2.ids")
    ids.__path__ = []

    unit_typeid = types.ModuleType("sc2.ids.unit_typeid")
    unit_typeid.UnitTypeId = UnitTypeId

    ability_id = types.ModuleType("sc2.ids.ability_id")
    ability_id.AbilityId = AbilityId

    upgrade_id = types.ModuleType("sc2.ids.upgrade_id")
    upgrade_id.UpgradeId = UpgradeId

    position_mod = types.ModuleType("sc2.position")
    position_mod.Point2 = Point2
    position_mod.Point3 = Point3

    unit_mod = types.ModuleType("sc2.unit")
    unit_mod.Unit = Unit

    units_mod = types.ModuleType("sc2.units")
    units_mod.Units = Units

    bot_ai_mod = types.ModuleType("sc2.bot_ai")
    bot_ai_mod.BotAI = BotAI

    for mod in (
        sc2,
        ids,
        unit_typeid,
        ability_id,
        upgrade_id,
        position_mod,
        unit_mod,
        units_mod,
        bot_ai_mod,
    ):
        sys.modules[mod.__name__] = mod


_install_sc2_stub()


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
