"""
YAML 설정 로더 (#170)

config.yaml 파일을 파싱하고, 환경변수로 개별 값을 오버라이드할 수 있다.

환경변수 오버라이드 규칙:
  YAML 키 경로를 언더스코어로 연결하고 대문자로 변환한다.
  예: proxy.port       → PROXY_PORT=8080
      crypto.trading.dry_run → CRYPTO_TRADING_DRY_RUN=false

사용 예시:
    from config_loader import load_config, get

    # 전체 설정 로드
    cfg = load_config()

    # 개별 값 접근 (점 표기법)
    port = get("proxy.port")                 # 3456
    dry = get("crypto.trading.dry_run")      # True

    # 기본값 지정
    val = get("nonexistent.key", default=42)  # 42
"""

import os
import re
import copy
from pathlib import Path
from typing import Any, Dict, Optional, Union

# ── YAML 라이브러리 로드 (없으면 간이 파서 사용) ──
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


# 모듈 수준 캐시
_config: Optional[Dict[str, Any]] = None
_config_path: Optional[Path] = None

# 환경변수 참조 패턴: ${ENV_VAR_NAME}
_ENV_REF_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


# ═══════════════════════════════════════════════════════
# 간이 YAML 파서 (yaml 라이브러리가 없을 때 사용)
# ═══════════════════════════════════════════════════════

def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """
    yaml 라이브러리가 없을 때 기본적인 YAML 구문을 파싱하는 간이 파서.
    중첩 딕셔너리와 리스트를 지원한다. 복잡한 YAML 기능은 미지원.
    """
    result: Dict[str, Any] = {}
    stack = [(result, -1)]  # (현재 딕셔너리, 들여쓰기 레벨)
    current_key = None

    for line in text.splitlines():
        # 주석 및 빈 줄 건너뛰기
        stripped = line.split("#")[0].rstrip()
        if not stripped:
            continue

        # 들여쓰기 계산
        indent = len(line) - len(line.lstrip())

        # 스택 정리: 현재 들여쓰기보다 깊은 레벨 제거
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()

        content = stripped.strip()

        # 리스트 항목인 경우
        if content.startswith("- "):
            value = _parse_scalar(content[2:].strip())
            parent_dict = stack[-1][0]
            if current_key and current_key in parent_dict:
                if isinstance(parent_dict[current_key], list):
                    parent_dict[current_key].append(value)
            continue

        # key: value 쌍인 경우
        if ":" in content:
            colon_idx = content.index(":")
            key = content[:colon_idx].strip()
            raw_value = content[colon_idx + 1:].strip()

            parent_dict = stack[-1][0]

            if raw_value == "" or raw_value.startswith("#"):
                # 하위 딕셔너리 또는 리스트 시작
                # 다음 줄의 내용에 따라 결정
                parent_dict[key] = {}
                stack.append((parent_dict[key], indent))
                current_key = key
                # 다음 줄이 리스트면 변환 필요
                _check_and_convert_to_list(parent_dict, key, text, indent)
            else:
                parent_dict[key] = _parse_scalar(raw_value)
                current_key = key

    return result


def _check_and_convert_to_list(
    parent: Dict, key: str, full_text: str, current_indent: int
) -> None:
    """다음 줄이 리스트 항목이면 딕셔너리를 리스트로 변환한다."""
    lines = full_text.splitlines()
    found_key = False
    for line in lines:
        stripped = line.strip()
        if not found_key:
            if stripped.startswith(f"{key}:"):
                found_key = True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            parent[key] = []
        break


def _parse_scalar(value: str) -> Any:
    """문자열 값을 적절한 Python 타입으로 변환한다."""
    # 따옴표 제거
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]

    # 불리언
    if value.lower() in ("true", "yes", "on"):
        return True
    if value.lower() in ("false", "no", "off"):
        return False

    # None
    if value.lower() in ("null", "~", "none"):
        return None

    # 숫자
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


# ═══════════════════════════════════════════════════════
# 환경변수 참조 해석
# ═══════════════════════════════════════════════════════

def _resolve_env_refs(value: Any) -> Any:
    """
    문자열 내의 ${ENV_VAR} 참조를 실제 환경변수 값으로 대체한다.
    환경변수가 없으면 빈 문자열로 대체한다.
    """
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            env_name = match.group(1)
            return os.environ.get(env_name, "")
        return _ENV_REF_PATTERN.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_refs(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_refs(item) for item in value]
    return value


# ═══════════════════════════════════════════════════════
# 환경변수 오버라이드
# ═══════════════════════════════════════════════════════

def _apply_env_overrides(config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """
    환경변수를 확인하여 YAML 설정을 오버라이드한다.
    키 경로를 대문자 + 언더스코어로 변환하여 매칭한다.

    예: proxy.port → PROXY_PORT 환경변수 확인
    """
    result = copy.deepcopy(config)

    for key, value in result.items():
        env_key = f"{prefix}_{key}".upper() if prefix else key.upper()

        if isinstance(value, dict):
            result[key] = _apply_env_overrides(value, env_key)
        else:
            env_val = os.environ.get(env_key)
            if env_val is not None:
                # 원래 타입에 맞게 변환
                result[key] = _cast_to_type(env_val, type(value) if value is not None else str)

    return result


def _cast_to_type(value: str, target_type: type) -> Any:
    """환경변수 문자열을 대상 타입으로 변환한다."""
    if target_type == bool:
        return value.lower() in ("true", "1", "yes", "on")
    elif target_type == int:
        try:
            return int(value)
        except ValueError:
            return value
    elif target_type == float:
        try:
            return float(value)
        except ValueError:
            return value
    elif target_type == list:
        # 쉼표 구분 리스트 지원
        return [item.strip() for item in value.split(",")]
    return value


# ═══════════════════════════════════════════════════════
# 공개 API
# ═══════════════════════════════════════════════════════

def load_config(
    config_path: Optional[Union[str, Path]] = None,
    apply_env: bool = True,
    resolve_refs: bool = True,
) -> Dict[str, Any]:
    """
    YAML 설정 파일을 로드한다.

    Args:
        config_path: 설정 파일 경로 (기본: 프로젝트 루트의 config.yaml)
        apply_env: 환경변수 오버라이드 적용 여부
        resolve_refs: ${ENV_VAR} 참조 해석 여부

    Returns:
        설정 딕셔너리

    Raises:
        FileNotFoundError: 설정 파일이 없을 경우
    """
    global _config, _config_path

    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

    _config_path = config_path

    # YAML 파싱
    raw_text = config_path.read_text(encoding="utf-8")
    if _HAS_YAML:
        config = yaml.safe_load(raw_text) or {}
    else:
        config = _simple_yaml_parse(raw_text)

    # 환경변수 참조 해석 (${VAR_NAME})
    if resolve_refs:
        config = _resolve_env_refs(config)

    # 환경변수 오버라이드
    if apply_env:
        config = _apply_env_overrides(config)

    _config = config
    return config


def get(key_path: str, default: Any = None) -> Any:
    """
    점(.) 표기법으로 설정 값을 가져온다.

    Args:
        key_path: 점으로 구분된 키 경로 (예: "proxy.port")
        default: 키가 없을 때 반환할 기본값

    Returns:
        설정 값 또는 기본값

    Examples:
        >>> get("proxy.port")
        3456
        >>> get("crypto.trading.dry_run")
        True
        >>> get("nonexistent", default="없음")
        '없음'
    """
    global _config
    if _config is None:
        load_config()

    keys = key_path.split(".")
    current = _config
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return default
    return current


def reload_config() -> Dict[str, Any]:
    """설정 파일을 다시 로드한다. 런타임 중 설정 변경 시 사용."""
    global _config
    _config = None
    return load_config(config_path=_config_path)


def get_all() -> Dict[str, Any]:
    """전체 설정 딕셔너리를 반환한다."""
    global _config
    if _config is None:
        load_config()
    return copy.deepcopy(_config)


# ═══════════════════════════════════════════════════════
# 직접 실행 시 테스트
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    cfg = load_config()
    print(f"프로젝트: {get('project.name')}")
    print(f"버전: {get('project.version')}")
    print(f"프록시 포트: {get('proxy.port')}")
    print(f"암호화폐 dry_run: {get('crypto.trading.dry_run')}")
    print(f"로그 레벨: {get('logging.level')}")
    print(f"존재하지 않는 키: {get('no.such.key', default='기본값')}")
    print("설정 로드 완료")
