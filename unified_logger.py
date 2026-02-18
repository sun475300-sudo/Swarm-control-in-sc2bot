"""
통합 로깅 시스템 (#169)

모든 JARVIS 모듈(Claude 프록시, 암호화폐, SC2 봇)의 로그를
하나의 일관된 인터페이스로 관리한다.

주요 기능:
  - 모듈별 로거 생성 (get_logger)
  - 로그 로테이션 (TimedRotatingFileHandler - 일 단위)
  - JSON 포맷 로깅 옵션
  - 콘솔 + 파일 동시 출력
  - 로그 레벨 동적 변경

사용 예시:
    from unified_logger import UnifiedLogger

    # 기본 사용
    logger = UnifiedLogger.get_logger("crypto.trader")
    logger.info("매매 시작", extra={"symbol": "KRW-BTC"})

    # JSON 포맷으로 설정
    UnifiedLogger.setup(json_format=True, log_dir="./logs")
"""

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════
# JSON 로그 포매터
# ═══════════════════════════════════════════════════════

class JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON 형태로 직렬화하는 포매터."""

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 문자열로 변환한다."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # extra 필드가 있으면 추가
        # logging 표준 속성이 아닌 것만 포함
        _standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "filename", "module", "pathname", "thread", "threadName",
            "process", "processName", "levelname", "levelno",
            "message", "msecs", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _standard_attrs and not key.startswith("_"):
                try:
                    json.dumps(value)  # 직렬화 가능한지 확인
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        # 예외 정보가 있으면 추가
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# 사람이 읽기 좋은 포매터
# ═══════════════════════════════════════════════════════

class ReadableFormatter(logging.Formatter):
    """색상 없는, 사람이 읽기 좋은 로그 포매터."""

    FORMAT = "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt=self.DATE_FORMAT)


# ═══════════════════════════════════════════════════════
# 콘솔 컬러 포매터
# ═══════════════════════════════════════════════════════

class ColorFormatter(logging.Formatter):
    """터미널에서 로그 레벨별 색상을 적용하는 포매터."""

    # ANSI 색상 코드
    COLORS = {
        "DEBUG": "\033[36m",     # 시안
        "INFO": "\033[32m",      # 녹색
        "WARNING": "\033[33m",   # 노란색
        "ERROR": "\033[31m",     # 빨간색
        "CRITICAL": "\033[35m",  # 보라색
    }
    RESET = "\033[0m"

    FORMAT = "[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        """색상이 적용된 로그 문자열을 반환한다."""
        color = self.COLORS.get(record.levelname, self.RESET)
        formatter = logging.Formatter(
            f"{color}{self.FORMAT}{self.RESET}",
            datefmt=self.DATE_FORMAT,
        )
        return formatter.format(record)


# ═══════════════════════════════════════════════════════
# UnifiedLogger 메인 클래스
# ═══════════════════════════════════════════════════════

class UnifiedLogger:
    """
    JARVIS 프로젝트의 통합 로깅 관리자.

    싱글턴 패턴으로, setup()을 한 번 호출하면
    이후 get_logger()로 생성되는 모든 로거에 설정이 적용된다.
    """

    _initialized: bool = False
    _log_dir: Path = Path("./logs")
    _json_format: bool = False
    _log_level: int = logging.INFO
    _max_bytes: int = 50 * 1024 * 1024  # 50MB (크기 기반 백업용)
    _backup_count: int = 30             # 최대 30일 보관
    _loggers: dict = {}

    @classmethod
    def setup(
        cls,
        log_dir: Optional[str] = None,
        json_format: bool = False,
        log_level: str = "INFO",
        backup_count: int = 30,
        console_output: bool = True,
        color_console: bool = True,
    ) -> None:
        """
        통합 로깅 시스템을 초기화한다.

        Args:
            log_dir: 로그 파일 저장 디렉토리 (기본: ./logs)
            json_format: JSON 포맷 사용 여부
            log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            backup_count: 로그 파일 보관 일수
            console_output: 콘솔 출력 여부
            color_console: 콘솔 색상 출력 여부
        """
        if log_dir:
            cls._log_dir = Path(log_dir)
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        cls._json_format = json_format
        cls._log_level = getattr(logging, log_level.upper(), logging.INFO)
        cls._backup_count = backup_count

        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._log_level)

        # 기존 핸들러 모두 제거 (중복 방지)
        root_logger.handlers.clear()

        # 파일 핸들러 추가 (TimedRotatingFileHandler - 매일 자정 로테이션)
        log_file = cls._log_dir / "jarvis_unified.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=cls._backup_count,
            encoding="utf-8",
        )
        file_handler.suffix = "%Y-%m-%d"
        if cls._json_format:
            file_handler.setFormatter(JsonFormatter())
        else:
            file_handler.setFormatter(ReadableFormatter())
        file_handler.setLevel(cls._log_level)
        root_logger.addHandler(file_handler)

        # 콘솔 핸들러 추가
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            if cls._json_format:
                console_handler.setFormatter(JsonFormatter())
            elif color_console:
                console_handler.setFormatter(ColorFormatter())
            else:
                console_handler.setFormatter(ReadableFormatter())
            console_handler.setLevel(cls._log_level)
            root_logger.addHandler(console_handler)

        cls._initialized = True

        # 이미 생성된 로거들에게도 설정 적용
        for name, logger in cls._loggers.items():
            logger.setLevel(cls._log_level)

        setup_logger = cls.get_logger("unified_logger")
        setup_logger.info(
            "통합 로깅 시스템 초기화 완료 "
            f"(레벨={log_level}, JSON={json_format}, "
            f"디렉토리={cls._log_dir})"
        )

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        이름에 해당하는 로거를 반환한다.
        아직 setup()이 호출되지 않았으면 기본 설정으로 자동 초기화한다.

        Args:
            name: 로거 이름 (예: "crypto.trader", "sc2.bot", "proxy")

        Returns:
            logging.Logger 인스턴스
        """
        if not cls._initialized:
            cls.setup()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(cls._log_level)
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def get_module_logger(
        cls,
        module_name: str,
        separate_file: bool = False,
    ) -> logging.Logger:
        """
        모듈 전용 로거를 생성한다.
        separate_file=True이면 모듈 전용 로그 파일도 추가한다.

        Args:
            module_name: 모듈 이름 (예: "crypto", "sc2", "proxy")
            separate_file: 별도 로그 파일 생성 여부

        Returns:
            logging.Logger 인스턴스
        """
        logger = cls.get_logger(module_name)

        if separate_file:
            module_log_file = cls._log_dir / f"jarvis_{module_name}.log"
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(module_log_file),
                when="midnight",
                interval=1,
                backupCount=cls._backup_count,
                encoding="utf-8",
            )
            handler.suffix = "%Y-%m-%d"
            if cls._json_format:
                handler.setFormatter(JsonFormatter())
            else:
                handler.setFormatter(ReadableFormatter())
            handler.setLevel(cls._log_level)
            logger.addHandler(handler)

        return logger

    @classmethod
    def set_level(cls, level: str) -> None:
        """
        전체 로그 레벨을 동적으로 변경한다.

        Args:
            level: 로그 레벨 문자열 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        new_level = getattr(logging, level.upper(), logging.INFO)
        cls._log_level = new_level

        root_logger = logging.getLogger()
        root_logger.setLevel(new_level)
        for handler in root_logger.handlers:
            handler.setLevel(new_level)

        for name, logger in cls._loggers.items():
            logger.setLevel(new_level)

    @classmethod
    def add_error_file_handler(cls) -> None:
        """ERROR 이상의 로그만 별도 파일에 기록하는 핸들러를 추가한다."""
        error_log = cls._log_dir / "jarvis_errors.log"
        handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(error_log),
            when="midnight",
            interval=1,
            backupCount=cls._backup_count,
            encoding="utf-8",
        )
        handler.suffix = "%Y-%m-%d"
        handler.setLevel(logging.ERROR)
        if cls._json_format:
            handler.setFormatter(JsonFormatter())
        else:
            handler.setFormatter(ReadableFormatter())

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

    @classmethod
    def shutdown(cls) -> None:
        """로깅 시스템을 안전하게 종료한다. 모든 핸들러를 플러시하고 닫는다."""
        logging.shutdown()
        cls._initialized = False
        cls._loggers.clear()


# ═══════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════

def get_logger(name: str) -> logging.Logger:
    """UnifiedLogger.get_logger의 단축 함수."""
    return UnifiedLogger.get_logger(name)


def setup_logging(**kwargs) -> None:
    """UnifiedLogger.setup의 단축 함수."""
    UnifiedLogger.setup(**kwargs)


# ═══════════════════════════════════════════════════════
# 직접 실행 시 테스트
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    # 테스트: 텍스트 포맷
    UnifiedLogger.setup(log_dir="./logs", json_format=False, log_level="DEBUG")
    log = UnifiedLogger.get_logger("test")
    log.debug("디버그 메시지")
    log.info("정보 메시지")
    log.warning("경고 메시지")
    log.error("에러 메시지")

    # 테스트: JSON 포맷
    UnifiedLogger.shutdown()
    UnifiedLogger.setup(
        log_dir="./logs", json_format=True, log_level="DEBUG"
    )
    json_log = UnifiedLogger.get_logger("test.json")
    json_log.info("JSON 포맷 테스트", extra={"key": "value", "count": 42})

    UnifiedLogger.shutdown()
    print("통합 로깅 테스트 완료")
