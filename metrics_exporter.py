"""
Prometheus 메트릭 익스포터 (#174)

JARVIS 시스템의 핵심 메트릭을 Prometheus 형식으로 노출한다.
prometheus_client 라이브러리가 있으면 사용하고, 없으면 직접 구현한다.

노출 메트릭:
  - jarvis_trade_total           : 총 거래 횟수 (카운터)
  - jarvis_trade_success_total   : 성공 거래 횟수 (카운터)
  - jarvis_trade_failure_total   : 실패 거래 횟수 (카운터)
  - jarvis_portfolio_value_krw   : 포트폴리오 총 가치 (게이지, KRW)
  - jarvis_api_request_duration  : API 응답 시간 (히스토그램, 초)
  - jarvis_api_request_total     : API 요청 총 횟수 (카운터)
  - jarvis_active_positions      : 활성 포지션 수 (게이지)
  - jarvis_uptime_seconds        : 서비스 가동 시간 (게이지)

사용 예시:
    from metrics_exporter import MetricsExporter

    # 메트릭 서버 시작 (포트 9090)
    exporter = MetricsExporter(port=9090)
    exporter.start()

    # 메트릭 기록
    exporter.record_trade(success=True, symbol="KRW-BTC", amount=50000)
    exporter.update_portfolio_value(15000000)

    with exporter.measure_api_time("upbit", "/v1/ticker"):
        response = call_api()

실행 방법:
    python metrics_exporter.py
    # http://localhost:9090/metrics 에서 확인
"""

import json
import threading
import time
from contextlib import contextmanager
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional

# prometheus_client 라이브러리 사용 시도
try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        start_http_server,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False


# ═══════════════════════════════════════════════════════
# 직접 구현 메트릭 클래스 (prometheus_client 없을 때)
# ═══════════════════════════════════════════════════════

class _SimpleCounter:
    """간단한 카운터 메트릭 (증가만 가능)."""

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self._label_names = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "_SimpleCounter":
        """라벨이 적용된 카운터 뷰를 반환한다."""
        key = tuple(kwargs.get(l, "") for l in self._label_names)
        labeled = _SimpleCounter(self.name, self.description)
        labeled._values = self._values
        labeled._lock = self._lock
        labeled._current_key = key
        return labeled

    def inc(self, amount: float = 1.0) -> None:
        """카운터 값을 증가시킨다."""
        key = getattr(self, "_current_key", ())
        with self._lock:
            self._values[key] = self._values.get(key, 0) + amount

    def _collect(self) -> str:
        """Prometheus 텍스트 형식으로 출력한다."""
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} counter"]
        with self._lock:
            for key, val in self._values.items():
                if key:
                    label_str = ",".join(
                        f'{n}="{v}"' for n, v in zip(self._label_names, key) if v
                    )
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return "\n".join(lines)


class _SimpleGauge:
    """간단한 게이지 메트릭 (증가/감소/설정 가능)."""

    def __init__(self, name: str, description: str, labels: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self._label_names = labels or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "_SimpleGauge":
        """라벨이 적용된 게이지 뷰를 반환한다."""
        key = tuple(kwargs.get(l, "") for l in self._label_names)
        labeled = _SimpleGauge(self.name, self.description)
        labeled._values = self._values
        labeled._lock = self._lock
        labeled._current_key = key
        return labeled

    def set(self, value: float) -> None:
        """게이지 값을 설정한다."""
        key = getattr(self, "_current_key", ())
        with self._lock:
            self._values[key] = value

    def inc(self, amount: float = 1.0) -> None:
        """게이지 값을 증가시킨다."""
        key = getattr(self, "_current_key", ())
        with self._lock:
            self._values[key] = self._values.get(key, 0) + amount

    def dec(self, amount: float = 1.0) -> None:
        """게이지 값을 감소시킨다."""
        key = getattr(self, "_current_key", ())
        with self._lock:
            self._values[key] = self._values.get(key, 0) - amount

    def _collect(self) -> str:
        """Prometheus 텍스트 형식으로 출력한다."""
        lines = [f"# HELP {self.name} {self.description}", f"# TYPE {self.name} gauge"]
        with self._lock:
            for key, val in self._values.items():
                if key:
                    label_str = ",".join(
                        f'{n}="{v}"' for n, v in zip(self._label_names, key) if v
                    )
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return "\n".join(lines)


class _SimpleHistogram:
    """간단한 히스토그램 메트릭 (분포 측정)."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[List[str]] = None,
        buckets: Optional[tuple] = None,
    ):
        self.name = name
        self.description = description
        self._label_names = labels or []
        self._buckets = buckets or self.DEFAULT_BUCKETS
        self._observations: Dict[tuple, list] = {}
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "_SimpleHistogram":
        """라벨이 적용된 히스토그램 뷰를 반환한다."""
        key = tuple(kwargs.get(l, "") for l in self._label_names)
        labeled = _SimpleHistogram(self.name, self.description, buckets=self._buckets)
        labeled._observations = self._observations
        labeled._lock = self._lock
        labeled._current_key = key
        return labeled

    def observe(self, value: float) -> None:
        """관측값을 기록한다."""
        key = getattr(self, "_current_key", ())
        with self._lock:
            if key not in self._observations:
                self._observations[key] = []
            self._observations[key].append(value)

    def _collect(self) -> str:
        """Prometheus 텍스트 형식으로 출력한다."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key, obs in self._observations.items():
                label_prefix = ""
                if key:
                    label_prefix = ",".join(
                        f'{n}="{v}"' for n, v in zip(self._label_names, key) if v
                    )
                    label_prefix += ","

                total = sum(obs)
                count = len(obs)
                for bucket in self._buckets:
                    bucket_count = sum(1 for o in obs if o <= bucket)
                    lines.append(
                        f'{self.name}_bucket{{{label_prefix}le="{bucket}"}} {bucket_count}'
                    )
                lines.append(
                    f'{self.name}_bucket{{{label_prefix}le="+Inf"}} {count}'
                )
                lines.append(f"{self.name}_sum{{{label_prefix.rstrip(',')}}} {total}")
                lines.append(f"{self.name}_count{{{label_prefix.rstrip(',')}}} {count}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# 메트릭 익스포터 메인 클래스
# ═══════════════════════════════════════════════════════

class MetricsExporter:
    """
    JARVIS 시스템 메트릭을 Prometheus 형식으로 노출하는 익스포터.

    prometheus_client 라이브러리가 설치되어 있으면 활용하고,
    없으면 자체 구현으로 폴백한다.
    """

    def __init__(self, port: int = 9090, host: str = "0.0.0.0"):
        """
        메트릭 익스포터를 초기화한다.

        Args:
            port: 메트릭 HTTP 서버 포트
            host: 바인드 주소
        """
        self.port = port
        self.host = host
        self._start_time = time.time()
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

        if _HAS_PROMETHEUS:
            self._init_prometheus_metrics()
        else:
            self._init_simple_metrics()

    def _init_prometheus_metrics(self) -> None:
        """prometheus_client 라이브러리로 메트릭을 초기화한다."""
        self.trade_total = Counter(
            "jarvis_trade_total",
            "총 거래 횟수",
            ["symbol", "side"],
        )
        self.trade_success = Counter(
            "jarvis_trade_success_total",
            "성공한 거래 횟수",
            ["symbol"],
        )
        self.trade_failure = Counter(
            "jarvis_trade_failure_total",
            "실패한 거래 횟수",
            ["symbol", "reason"],
        )
        self.portfolio_value = Gauge(
            "jarvis_portfolio_value_krw",
            "포트폴리오 총 가치 (KRW)",
        )
        self.api_request_duration = Histogram(
            "jarvis_api_request_duration_seconds",
            "API 요청 응답 시간 (초)",
            ["service", "endpoint"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self.api_request_total = Counter(
            "jarvis_api_request_total",
            "API 요청 총 횟수",
            ["service", "endpoint", "status"],
        )
        self.active_positions = Gauge(
            "jarvis_active_positions",
            "현재 활성 포지션 수",
        )
        self.uptime = Gauge(
            "jarvis_uptime_seconds",
            "서비스 가동 시간 (초)",
        )

    def _init_simple_metrics(self) -> None:
        """자체 구현 메트릭을 초기화한다."""
        self.trade_total = _SimpleCounter(
            "jarvis_trade_total", "총 거래 횟수", ["symbol", "side"],
        )
        self.trade_success = _SimpleCounter(
            "jarvis_trade_success_total", "성공한 거래 횟수", ["symbol"],
        )
        self.trade_failure = _SimpleCounter(
            "jarvis_trade_failure_total", "실패한 거래 횟수", ["symbol", "reason"],
        )
        self.portfolio_value = _SimpleGauge(
            "jarvis_portfolio_value_krw", "포트폴리오 총 가치 (KRW)",
        )
        self.api_request_duration = _SimpleHistogram(
            "jarvis_api_request_duration_seconds",
            "API 요청 응답 시간 (초)",
            ["service", "endpoint"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
        self.api_request_total = _SimpleCounter(
            "jarvis_api_request_total", "API 요청 총 횟수",
            ["service", "endpoint", "status"],
        )
        self.active_positions = _SimpleGauge(
            "jarvis_active_positions", "현재 활성 포지션 수",
        )
        self.uptime = _SimpleGauge(
            "jarvis_uptime_seconds", "서비스 가동 시간 (초)",
        )
        self._simple_metrics = [
            self.trade_total, self.trade_success, self.trade_failure,
            self.portfolio_value, self.api_request_duration,
            self.api_request_total, self.active_positions, self.uptime,
        ]

    # ── 메트릭 기록 메서드 ──

    def record_trade(
        self,
        success: bool,
        symbol: str = "unknown",
        side: str = "buy",
        amount: float = 0,
        reason: str = "",
    ) -> None:
        """
        거래를 기록한다.

        Args:
            success: 거래 성공 여부
            symbol: 거래 심볼 (예: KRW-BTC)
            side: 매매 방향 (buy/sell)
            amount: 거래 금액
            reason: 실패 사유 (실패 시)
        """
        self.trade_total.labels(symbol=symbol, side=side).inc()
        if success:
            self.trade_success.labels(symbol=symbol).inc()
        else:
            self.trade_failure.labels(symbol=symbol, reason=reason).inc()

    def update_portfolio_value(self, value_krw: float) -> None:
        """포트폴리오 총 가치를 업데이트한다 (KRW)."""
        self.portfolio_value.set(value_krw)

    def update_active_positions(self, count: int) -> None:
        """활성 포지션 수를 업데이트한다."""
        self.active_positions.set(count)

    def record_api_request(
        self, service: str, endpoint: str, status: str, duration: float
    ) -> None:
        """
        API 요청을 기록한다.

        Args:
            service: 서비스 이름 (예: upbit, anthropic)
            endpoint: API 엔드포인트
            status: 응답 상태 (success/error)
            duration: 응답 시간 (초)
        """
        self.api_request_total.labels(
            service=service, endpoint=endpoint, status=status,
        ).inc()
        self.api_request_duration.labels(
            service=service, endpoint=endpoint,
        ).observe(duration)

    @contextmanager
    def measure_api_time(self, service: str, endpoint: str):
        """
        API 응답 시간을 자동 측정하는 컨텍스트 매니저.

        사용 예:
            with exporter.measure_api_time("upbit", "/v1/ticker"):
                response = call_api()
        """
        start = time.time()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start
            self.record_api_request(service, endpoint, status, duration)

    def _update_uptime(self) -> None:
        """가동 시간 메트릭을 업데이트한다."""
        self.uptime.set(time.time() - self._start_time)

    # ── 메트릭 서버 ──

    def _generate_metrics_text(self) -> str:
        """모든 메트릭을 Prometheus 텍스트 형식으로 생성한다."""
        self._update_uptime()
        if _HAS_PROMETHEUS:
            return generate_latest().decode("utf-8")
        else:
            parts = []
            for metric in self._simple_metrics:
                parts.append(metric._collect())
            return "\n\n".join(parts) + "\n"

    def start(self) -> None:
        """메트릭 HTTP 서버를 백그라운드에서 시작한다."""
        if _HAS_PROMETHEUS:
            start_http_server(self.port, addr=self.host)
            print(f"Prometheus 메트릭 서버 시작 (prometheus_client): "
                  f"http://{self.host}:{self.port}/metrics")
        else:
            exporter = self

            class MetricsHandler(BaseHTTPRequestHandler):
                """메트릭 HTTP 요청 핸들러."""

                def do_GET(self):
                    if self.path == "/metrics":
                        body = exporter._generate_metrics_text()
                        self.send_response(200)
                        self.send_header(
                            "Content-Type",
                            "text/plain; version=0.0.4; charset=utf-8",
                        )
                        self.end_headers()
                        self.wfile.write(body.encode("utf-8"))
                    elif self.path == "/health":
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            json.dumps({"status": "ok"}).encode("utf-8")
                        )
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    """기본 로깅 억제."""
                    pass

            self._server = HTTPServer((self.host, self.port), MetricsHandler)
            self._server_thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
            )
            self._server_thread.start()
            print(f"Prometheus 메트릭 서버 시작 (자체 구현): "
                  f"http://{self.host}:{self.port}/metrics")

    def stop(self) -> None:
        """메트릭 HTTP 서버를 중지한다."""
        if self._server:
            self._server.shutdown()
            print("메트릭 서버 중지")


# ═══════════════════════════════════════════════════════
# 싱글턴 인스턴스
# ═══════════════════════════════════════════════════════

_default_exporter: Optional[MetricsExporter] = None


def get_exporter(port: int = 9090) -> MetricsExporter:
    """기본 메트릭 익스포터 인스턴스를 반환한다."""
    global _default_exporter
    if _default_exporter is None:
        _default_exporter = MetricsExporter(port=port)
    return _default_exporter


# ═══════════════════════════════════════════════════════
# 직접 실행 시 데모
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import random

    exporter = MetricsExporter(port=9090)
    exporter.start()
    print("메트릭 서버가 http://localhost:9090/metrics 에서 실행 중입니다.")
    print("Ctrl+C로 종료합니다.\n")

    try:
        while True:
            # 데모 데이터 생성
            symbol = random.choice(["KRW-BTC", "KRW-ETH", "KRW-XRP"])
            success = random.random() > 0.1
            exporter.record_trade(
                success=success,
                symbol=symbol,
                side=random.choice(["buy", "sell"]),
                reason="" if success else "insufficient_balance",
            )
            exporter.update_portfolio_value(
                random.uniform(10_000_000, 20_000_000)
            )
            exporter.update_active_positions(random.randint(0, 5))
            exporter.record_api_request(
                service="upbit",
                endpoint="/v1/ticker",
                status="success",
                duration=random.uniform(0.01, 0.5),
            )

            print(f"메트릭 업데이트: {symbol} ({'성공' if success else '실패'})")
            time.sleep(3)
    except KeyboardInterrupt:
        exporter.stop()
        print("\n데모 종료")
