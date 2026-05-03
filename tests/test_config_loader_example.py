"""
config_loader 스모크 테스트

루트의 ``config.yaml`` 은 gitignored 라서 CI 환경에는 존재하지 않는다.
하지만 ``config.example.yaml`` 은 항상 함께 커밋되므로, 그 템플릿을 직접
로드해서 config_loader 의 핵심 동작 (load_config / get / 환경변수 참조 /
환경변수 오버라이드) 이 회귀 없이 동작하는지를 검증한다.
"""

from pathlib import Path

import config_loader
import pytest

EXAMPLE_PATH = Path(__file__).parent.parent / "config.example.yaml"


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """각 테스트마다 모듈 수준 캐시 초기화."""
    config_loader._config = None
    config_loader._config_path = None
    yield
    config_loader._config = None
    config_loader._config_path = None


@pytest.mark.skipif(not EXAMPLE_PATH.exists(), reason="config.example.yaml not present")
class TestConfigExample:
    def test_loads_as_dict(self):
        cfg = config_loader.load_config(config_path=EXAMPLE_PATH)
        assert isinstance(cfg, dict)
        assert "project" in cfg
        assert "proxy" in cfg

    def test_get_dotted_path(self):
        config_loader.load_config(config_path=EXAMPLE_PATH)
        port = config_loader.get("proxy.port")
        assert isinstance(port, int)
        assert port > 0

    def test_get_nonexistent_returns_default(self):
        config_loader.load_config(config_path=EXAMPLE_PATH)
        assert config_loader.get("no.such.key", default=42) == 42
        assert config_loader.get("also.missing") is None

    def test_env_var_reference_resolved(self, monkeypatch):
        """${UPBIT_ACCESS_KEY} 가 실제 env 값으로 치환된다."""
        monkeypatch.setenv("UPBIT_ACCESS_KEY", "test-access-token")
        config_loader.load_config(config_path=EXAMPLE_PATH)
        assert config_loader.get("crypto.upbit.access_key") == "test-access-token"

    def test_env_override_takes_precedence(self, monkeypatch):
        """PROXY_PORT 환경변수는 yaml 의 proxy.port 를 덮어쓴다."""
        monkeypatch.setenv("PROXY_PORT", "9999")
        config_loader.load_config(config_path=EXAMPLE_PATH)
        assert config_loader.get("proxy.port") == 9999

    def test_no_hardcoded_secrets_in_example(self):
        """example 템플릿에는 실제 비밀이 들어있지 않아야 한다."""
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if any(
                k in stripped
                for k in ("access_key:", "secret_key:", "password:", "api_key:")
            ):
                # 환경변수 참조이거나 빈 값이어야 한다.
                assert (
                    "${" in stripped
                    or stripped.endswith('""')
                    or stripped.endswith("''")
                    or stripped.endswith(":")
                ), f"example 에 secret 가 박혀있는 것 같습니다: {stripped}"
