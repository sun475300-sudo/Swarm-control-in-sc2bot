"""
pytest 공통 fixtures (#171)

모든 테스트 파일에서 공유할 수 있는 fixture와 설정을 정의한다.
"""

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


# ─────────────────────────────────────────────
# Minimal sc2 stub injection (for tests only)
# ─────────────────────────────────────────────
#
# python-sc2 / burnysc2 cannot be `pip install`ed in many CI / dev
# environments because mpyq fails to build a wheel. We don't actually
# need the live SC2 client to unit-test pure-logic helpers — we only
# need the IDs module to expose `UnitTypeId.<NAME>` and
# `AbilityId.<NAME>` as typed-enough placeholders. Inject these into
# `sys.modules` BEFORE any test/wicked_zerg_challenger module imports
# `from sc2...`.
#
# Real sc2 always wins: we only inject if the real package is missing.
def _install_sc2_stubs() -> None:
    try:  # real sc2 present — leave it alone
        import sc2  # noqa: F401

        return
    except ImportError:
        pass

    class _Member:
        """Hashable stand-in for an sc2 enum member (e.g. UnitTypeId.QUEEN)."""

        __slots__ = ("name", "value", "_kind")

        def __init__(self, kind: str, name: str) -> None:
            self._kind = kind
            self.name = name
            self.value = name

        def __repr__(self) -> str:  # pragma: no cover - cosmetic
            return f"{self._kind}.{self.name}"

        def __eq__(self, other) -> bool:
            return (
                isinstance(other, _Member)
                and self._kind == other._kind
                and self.name == other.name
            )

        def __hash__(self) -> int:
            return hash((self._kind, self.name))

    class _Identifier:
        """Stand-in for sc2 ID enums (UnitTypeId / AbilityId / UpgradeId).

        Attribute access returns a hashable `_Member` with `.name == "<ATTR>"`,
        so production code that does `UnitTypeId.ULTRALISK` and uses it as
        a dict key keeps working.
        """

        def __init__(self, kind: str) -> None:
            self._kind = kind
            self._cache: dict = {}

        def __getattr__(self, name: str):
            cached = self._cache.get(name)
            if cached is None:
                cached = _Member(self._kind, name)
                self._cache[name] = cached
            return cached

    class _Point2(tuple):
        def __new__(cls, xy):
            return tuple.__new__(cls, (float(xy[0]), float(xy[1])))

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        def distance_to(self, other) -> float:
            ox, oy = other[0], other[1]
            return ((self[0] - ox) ** 2 + (self[1] - oy) ** 2) ** 0.5

    class _Unit:  # pragma: no cover - placeholder type
        pass

    class _Units(list):  # pragma: no cover - placeholder type
        pass

    class _BotAI:  # pragma: no cover - placeholder type
        pass

    sc2 = types.ModuleType("sc2")
    sc2_ids = types.ModuleType("sc2.ids")
    sc2_ids_unit = types.ModuleType("sc2.ids.unit_typeid")
    sc2_ids_ability = types.ModuleType("sc2.ids.ability_id")
    sc2_ids_upgrade = types.ModuleType("sc2.ids.upgrade_id")
    sc2_position = types.ModuleType("sc2.position")
    sc2_unit = types.ModuleType("sc2.unit")
    sc2_units = types.ModuleType("sc2.units")
    sc2_bot_ai = types.ModuleType("sc2.bot_ai")

    sc2_ids_unit.UnitTypeId = _Identifier("UnitTypeId")
    sc2_ids_ability.AbilityId = _Identifier("AbilityId")
    sc2_ids_upgrade.UpgradeId = _Identifier("UpgradeId")
    sc2_position.Point2 = _Point2
    sc2_unit.Unit = _Unit
    sc2_units.Units = _Units
    sc2_bot_ai.BotAI = _BotAI

    for mod in (
        sc2,
        sc2_ids,
        sc2_ids_unit,
        sc2_ids_ability,
        sc2_ids_upgrade,
        sc2_position,
        sc2_unit,
        sc2_units,
        sc2_bot_ai,
    ):
        sys.modules[mod.__name__] = mod


_install_sc2_stubs()


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
