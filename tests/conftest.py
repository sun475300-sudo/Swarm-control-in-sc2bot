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

# Bot 코어는 ``from utils.logger import get_logger`` 같은 top-level 경로를
# 가정한다. wicked_zerg_challenger/ 자체를 sys.path 맨 앞에 추가해 정상 import 되도록.
BOT_DIR = PROJECT_ROOT / "wicked_zerg_challenger"
if BOT_DIR.is_dir() and str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

# 프로젝트 루트에도 동명의 ``utils/`` 디렉터리가 존재한다 (logger.py 없음).
# pytest의 rootdir 자동 추가 때문에 우선순위가 뒤집히면 ``import utils.logger``가
# 실패한다. 여기서 두 경로를 병합한 namespace package로 만든다.
import importlib  # noqa: E402

if "utils" in sys.modules:
    del sys.modules["utils"]
import utils  # noqa: E402

_bot_utils_path = str(BOT_DIR / "utils")
if _bot_utils_path not in utils.__path__:
    utils.__path__.append(_bot_utils_path)


# ═══════════════════════════════════════════════════════
# python-sc2 lightweight stub (only when the real package is missing)
# ═══════════════════════════════════════════════════════
# Several tests `from sc2.position import Point2` / `from sc2.ids.unit_typeid
# import UnitTypeId` only to use them as plain value types. Without
# python-sc2 installed those modules `pytest.skip(...allow_module_level=True)`
# at import time. Provide a minimal stub so the tests collect and run.
def _install_sc2_stub() -> None:
    try:
        import sc2  # noqa: F401  (real package available — do nothing)
        return
    except ImportError:
        pass

    sc2 = types.ModuleType("sc2")
    sc2_position = types.ModuleType("sc2.position")
    sc2_ids = types.ModuleType("sc2.ids")
    sc2_ids_unit = types.ModuleType("sc2.ids.unit_typeid")
    sc2_ids_ability = types.ModuleType("sc2.ids.ability_id")
    sc2_ids_upgrade = types.ModuleType("sc2.ids.upgrade_id")
    sc2_ids_buff = types.ModuleType("sc2.ids.buff_id")
    sc2_bot_ai = types.ModuleType("sc2.bot_ai")
    sc2_unit = types.ModuleType("sc2.unit")
    sc2_units = types.ModuleType("sc2.units")
    sc2_data = types.ModuleType("sc2.data")
    sc2_main = types.ModuleType("sc2.main")
    sc2_player = types.ModuleType("sc2.player")
    sc2_constants = types.ModuleType("sc2.constants")

    class Point2(tuple):
        """Minimal Point2 stub: 2-tuple with .x / .y / basic geometry."""

        def __new__(cls, xy):
            x, y = (xy[0], xy[1]) if hasattr(xy, "__getitem__") else (xy.x, xy.y)
            return super().__new__(cls, (float(x), float(y)))

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        def distance_to(self, other) -> float:
            ox = getattr(other, "x", None)
            oy = getattr(other, "y", None)
            if ox is None and len(other) >= 2:
                ox, oy = other[0], other[1]
            return ((self.x - ox) ** 2 + (self.y - oy) ** 2) ** 0.5

        def towards(self, other, distance: float):
            d = self.distance_to(other) or 1.0
            ox = getattr(other, "x", other[0])
            oy = getattr(other, "y", other[1])
            ratio = distance / d
            return Point2((self.x + (ox - self.x) * ratio,
                           self.y + (oy - self.y) * ratio))

        @property
        def position(self):
            return self

    class _IdEnum:
        """Enum-like container that returns a stable sentinel for any name."""

        def __init__(self, kind: str):
            self._kind = kind
            self._cache: dict[str, object] = {}

        def __getattr__(self, name: str):
            if name.startswith("_"):
                raise AttributeError(name)
            v = self._cache.get(name)
            if v is None:
                v = type(self._kind, (), {"name": name, "value": name,
                                          "__repr__": lambda s, n=name: f"{n}"})()
                self._cache[name] = v
            return v

    sc2_position.Point2 = Point2

    class _StubUnit:  # placeholder
        pass

    class _StubUnits(list):  # behave like a list
        pass

    class _StubBotAI:  # placeholder
        pass

    sc2_ids_unit.UnitTypeId = _IdEnum("UnitTypeId")
    sc2_ids_ability.AbilityId = _IdEnum("AbilityId")
    sc2_ids_upgrade.UpgradeId = _IdEnum("UpgradeId")
    sc2_ids_buff.BuffId = _IdEnum("BuffId")
    sc2_bot_ai.BotAI = _StubBotAI
    sc2_unit.Unit = _StubUnit
    sc2_units.Units = _StubUnits
    sc2_data.Race = _IdEnum("Race")
    sc2_data.Result = _IdEnum("Result")
    sc2_data.Difficulty = _IdEnum("Difficulty")
    sc2_data.AIBuild = _IdEnum("AIBuild")

    # `sc2.maps.get(...)` is used to load map files. Tests don't need the real
    # map; expose a callable that returns the requested name.
    sc2_maps = types.ModuleType("sc2.maps")
    sc2_maps.get = lambda name: name
    sc2.maps = sc2_maps

    # `sc2.player.{Bot,Computer,Human}` are simple value classes.
    sc2_player.Bot = type("Bot", (), {"__init__": lambda self, *a, **k: None})
    sc2_player.Computer = type("Computer", (), {"__init__": lambda self, *a, **k: None})
    sc2_player.Human = type("Human", (), {"__init__": lambda self, *a, **k: None})

    # `sc2.main.run_game(...)` is the engine entry point. Tests stub a no-op.
    sc2_main.run_game = lambda *a, **k: None

    sys.modules.setdefault("sc2", sc2)
    sys.modules.setdefault("sc2.position", sc2_position)
    sys.modules.setdefault("sc2.ids", sc2_ids)
    sys.modules.setdefault("sc2.ids.unit_typeid", sc2_ids_unit)
    sys.modules.setdefault("sc2.ids.ability_id", sc2_ids_ability)
    sys.modules.setdefault("sc2.ids.upgrade_id", sc2_ids_upgrade)
    sys.modules.setdefault("sc2.ids.buff_id", sc2_ids_buff)
    sys.modules.setdefault("sc2.bot_ai", sc2_bot_ai)
    sys.modules.setdefault("sc2.unit", sc2_unit)
    sys.modules.setdefault("sc2.units", sc2_units)
    sys.modules.setdefault("sc2.data", sc2_data)
    sys.modules.setdefault("sc2.main", sc2_main)
    sys.modules.setdefault("sc2.player", sc2_player)
    sys.modules.setdefault("sc2.constants", sc2_constants)
    sys.modules.setdefault("sc2.maps", sc2_maps)


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
