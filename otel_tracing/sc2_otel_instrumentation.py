"""
Phase 604: OpenTelemetry SDK - SC2 Zerg Bot Distributed Tracing
================================================================
Production-quality OpenTelemetry instrumentation for the SC2 Zerg commander bot.
Provides distributed tracing, custom metrics, and structured logging for all
bot operations including game loop steps, combat decisions, and economy ticks.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from enum import Enum
from typing import Any, Dict, Generator, Optional, Sequence

from opentelemetry import baggage, context, trace
from opentelemetry.baggage import get_baggage, set_baggage
from opentelemetry.context import attach, detach
from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import (
    Counter,
    Histogram,
    Meter,
    UpDownCounter,
    get_meter_provider,
    set_meter_provider,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_ON,
    ParentBasedTraceIdRatio,
    TraceIdRatioBased,
)
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import (
    Span,
    SpanKind,
    StatusCode,
    Tracer,
    get_tracer_provider,
    set_tracer_provider,
)
from opentelemetry.trace.propagation import set_span_in_context


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class SamplingStrategy(Enum):
    """Supported trace sampling strategies."""
    ALWAYS_ON = "always_on"
    TRACE_ID_RATIO = "trace_id_ratio"
    PARENT_BASED = "parent_based"


class SpanName:
    """Canonical span names used across the bot."""
    ON_STEP = "sc2.bot.on_step"
    COMBAT_DECISION = "sc2.bot.combat_decision"
    ECONOMY_TICK = "sc2.bot.economy_tick"
    BUILD_ORDER = "sc2.bot.build_order"
    MICRO_CONTROL = "sc2.bot.micro_control"
    SCOUTING = "sc2.bot.scouting"
    UPGRADE_CHECK = "sc2.bot.upgrade_check"
    INJECTION_CYCLE = "sc2.bot.injection_cycle"
    CREEP_SPREAD = "sc2.bot.creep_spread"


class MetricName:
    """Canonical metric names."""
    STEP_DURATION = "sc2.bot.step_duration"
    STEP_COUNT = "sc2.bot.step_count"
    COMBAT_DECISIONS = "sc2.bot.combat_decisions"
    UNITS_CREATED = "sc2.bot.units_created"
    UNITS_LOST = "sc2.bot.units_lost"
    MINERALS_COLLECTED = "sc2.bot.minerals_collected"
    VESPENE_COLLECTED = "sc2.bot.vespene_collected"
    SUPPLY_USED = "sc2.bot.supply_used"
    SUPPLY_CAP = "sc2.bot.supply_cap"
    ARMY_VALUE = "sc2.bot.army_value"
    ACTIVE_WORKERS = "sc2.bot.active_workers"
    ACTIVE_BASES = "sc2.bot.active_bases"
    APM_ESTIMATE = "sc2.bot.apm_estimate"
    DECISION_LATENCY = "sc2.bot.decision_latency"
    CREEP_COVERAGE = "sc2.bot.creep_coverage"


# ---------------------------------------------------------------------------
# Resource Builder
# ---------------------------------------------------------------------------

def build_resource(
    service_name: str = "sc2-zerg-commander-bot",
    service_version: str = "6.0.4",
    bot_race: str = "Zerg",
    bot_name: str = "WickedZergChallenger",
    environment: str = "production",
    extra_attributes: Optional[Dict[str, str]] = None,
) -> Resource:
    """Create an OpenTelemetry Resource with SC2 bot-specific attributes."""
    attrs: Dict[str, str] = {
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: service_version,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
        "bot.race": bot_race,
        "bot.name": bot_name,
        "bot.framework": "burnysc2",
        "bot.phase": "604",
    }
    if extra_attributes:
        attrs.update(extra_attributes)
    return Resource.create(attrs)


# ---------------------------------------------------------------------------
# Sampler Factory
# ---------------------------------------------------------------------------

def create_sampler(
    strategy: SamplingStrategy = SamplingStrategy.PARENT_BASED,
    ratio: float = 1.0,
):
    """Return an appropriate sampler based on the chosen strategy.

    Parameters
    ----------
    strategy:
        One of ALWAYS_ON, TRACE_ID_RATIO, or PARENT_BASED.
    ratio:
        Sampling ratio in [0.0, 1.0] used for ratio-based strategies.
    """
    if strategy == SamplingStrategy.ALWAYS_ON:
        return ALWAYS_ON
    elif strategy == SamplingStrategy.TRACE_ID_RATIO:
        return TraceIdRatioBased(ratio)
    elif strategy == SamplingStrategy.PARENT_BASED:
        return ParentBasedTraceIdRatio(ratio)
    raise ValueError(f"Unknown sampling strategy: {strategy}")


# ---------------------------------------------------------------------------
# Metric Views
# ---------------------------------------------------------------------------

def _default_metric_views() -> Sequence[View]:
    """Return custom metric views for aggregation tuning."""
    return [
        # Step duration histogram with SC2-relevant bucket boundaries (ms)
        View(
            instrument_name=MetricName.STEP_DURATION,
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=[1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
            ),
        ),
        # Decision latency histogram
        View(
            instrument_name=MetricName.DECISION_LATENCY,
            aggregation=ExplicitBucketHistogramAggregation(
                boundaries=[0.5, 1, 2, 5, 10, 25, 50, 100]
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Core Instrumentation Class
# ---------------------------------------------------------------------------

class SC2OTelInstrumentation:
    """OpenTelemetry instrumentation facade for the SC2 Zerg commander bot.

    Encapsulates TracerProvider, MeterProvider, and LoggerProvider setup with
    OTLP exporters, Prometheus integration, and Jaeger-compatible tracing.

    Usage
    -----
    >>> otel = SC2OTelInstrumentation(otlp_endpoint="localhost:4317")
    >>> otel.setup()
    >>> with otel.trace_on_step(game_time=120.0, supply=44, minerals=350):
    ...     # bot logic
    ...     pass
    >>> otel.shutdown()
    """

    def __init__(
        self,
        otlp_endpoint: str = "localhost:4317",
        service_name: str = "sc2-zerg-commander-bot",
        service_version: str = "6.0.4",
        bot_race: str = "Zerg",
        environment: str = "production",
        sampling_strategy: SamplingStrategy = SamplingStrategy.PARENT_BASED,
        sampling_ratio: float = 1.0,
        enable_prometheus: bool = True,
        prometheus_port: int = 8099,
        enable_console_export: bool = False,
        batch_max_queue_size: int = 2048,
        batch_max_export_batch_size: int = 512,
        batch_schedule_delay_millis: int = 5000,
        metric_export_interval_millis: int = 10000,
        extra_resource_attributes: Optional[Dict[str, str]] = None,
    ) -> None:
        self._otlp_endpoint = otlp_endpoint
        self._service_name = service_name
        self._service_version = service_version
        self._bot_race = bot_race
        self._environment = environment
        self._sampling_strategy = sampling_strategy
        self._sampling_ratio = sampling_ratio
        self._enable_prometheus = enable_prometheus
        self._prometheus_port = prometheus_port
        self._enable_console_export = enable_console_export
        self._batch_max_queue = batch_max_queue_size
        self._batch_max_export = batch_max_export_batch_size
        self._batch_delay = batch_schedule_delay_millis
        self._metric_export_interval = metric_export_interval_millis
        self._extra_attrs = extra_resource_attributes

        # Providers (initialised in setup)
        self._resource: Optional[Resource] = None
        self._tracer_provider: Optional[TracerProvider] = None
        self._meter_provider: Optional[MeterProvider] = None
        self._logger_provider: Optional[LoggerProvider] = None

        # Instruments
        self._tracer: Optional[Tracer] = None
        self._meter: Optional[Meter] = None

        # Metric instruments (lazy-initialised)
        self._step_duration_hist: Optional[Histogram] = None
        self._step_counter: Optional[Counter] = None
        self._combat_decision_counter: Optional[Counter] = None
        self._units_created_counter: Optional[Counter] = None
        self._units_lost_counter: Optional[Counter] = None
        self._minerals_collected_counter: Optional[Counter] = None
        self._vespene_collected_counter: Optional[Counter] = None
        self._supply_used_gauge: Optional[UpDownCounter] = None
        self._supply_cap_gauge: Optional[UpDownCounter] = None
        self._army_value_gauge: Optional[UpDownCounter] = None
        self._active_workers_gauge: Optional[UpDownCounter] = None
        self._active_bases_gauge: Optional[UpDownCounter] = None
        self._apm_estimate_gauge: Optional[UpDownCounter] = None
        self._decision_latency_hist: Optional[Histogram] = None
        self._creep_coverage_gauge: Optional[UpDownCounter] = None

        self._is_setup = False

    # ------------------------------------------------------------------
    # Setup & Teardown
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Initialise all OTel providers, processors, and exporters."""
        if self._is_setup:
            return

        self._resource = build_resource(
            service_name=self._service_name,
            service_version=self._service_version,
            bot_race=self._bot_race,
            environment=self._environment,
            extra_attributes=self._extra_attrs,
        )

        self._setup_tracer_provider()
        self._setup_meter_provider()
        self._setup_logger_provider()
        self._create_metric_instruments()

        self._is_setup = True

    def shutdown(self) -> None:
        """Gracefully flush and shut down all providers."""
        if self._tracer_provider:
            self._tracer_provider.shutdown()
        if self._meter_provider:
            self._meter_provider.shutdown()
        if self._logger_provider:
            self._logger_provider.shutdown()
        self._is_setup = False

    # ------------------------------------------------------------------
    # Provider Setup
    # ------------------------------------------------------------------

    def _setup_tracer_provider(self) -> None:
        """Configure TracerProvider with OTLP exporter and BatchSpanProcessor."""
        sampler = create_sampler(self._sampling_strategy, self._sampling_ratio)

        self._tracer_provider = TracerProvider(
            resource=self._resource,
            sampler=sampler,
        )

        otlp_exporter = OTLPSpanExporter(endpoint=self._otlp_endpoint, insecure=True)
        batch_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=self._batch_max_queue,
            max_export_batch_size=self._batch_max_export,
            schedule_delay_millis=self._batch_delay,
        )
        self._tracer_provider.add_span_processor(batch_processor)

        if self._enable_console_export:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter

            self._tracer_provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )

        set_tracer_provider(self._tracer_provider)
        self._tracer = self._tracer_provider.get_tracer(
            instrumenting_module_name="sc2_otel_instrumentation",
            instrumenting_library_version=self._service_version,
        )

    def _setup_meter_provider(self) -> None:
        """Configure MeterProvider with OTLP + optional Prometheus readers."""
        readers = []

        # OTLP periodic reader
        otlp_metric_exporter = OTLPMetricExporter(
            endpoint=self._otlp_endpoint, insecure=True
        )
        readers.append(
            PeriodicExportingMetricReader(
                otlp_metric_exporter,
                export_interval_millis=self._metric_export_interval,
            )
        )

        # Prometheus reader (exposes /metrics on configured port)
        if self._enable_prometheus:
            prometheus_reader = PrometheusMetricReader()
            readers.append(prometheus_reader)

        self._meter_provider = MeterProvider(
            resource=self._resource,
            metric_readers=readers,
            views=_default_metric_views(),
        )
        set_meter_provider(self._meter_provider)
        self._meter = self._meter_provider.get_meter(
            name="sc2_zerg_bot_metrics",
            version=self._service_version,
        )

    def _setup_logger_provider(self) -> None:
        """Configure LoggerProvider with OTLP exporter for structured logging."""
        otlp_log_exporter = OTLPLogExporter(
            endpoint=self._otlp_endpoint, insecure=True
        )

        self._logger_provider = LoggerProvider(resource=self._resource)
        self._logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(otlp_log_exporter)
        )

        handler = LoggingHandler(
            level=logging.DEBUG,
            logger_provider=self._logger_provider,
        )

        # Attach to root logger so all bot modules emit structured logs
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

    # ------------------------------------------------------------------
    # Metric Instruments
    # ------------------------------------------------------------------

    def _create_metric_instruments(self) -> None:
        """Create all custom metric instruments."""
        m = self._meter

        self._step_counter = m.create_counter(
            name=MetricName.STEP_COUNT,
            description="Total number of on_step iterations executed",
            unit="1",
        )

        self._step_duration_hist = m.create_histogram(
            name=MetricName.STEP_DURATION,
            description="Duration of each on_step call in milliseconds",
            unit="ms",
        )

        self._combat_decision_counter = m.create_counter(
            name=MetricName.COMBAT_DECISIONS,
            description="Total combat decisions made",
            unit="1",
        )

        self._units_created_counter = m.create_counter(
            name=MetricName.UNITS_CREATED,
            description="Total units created by the bot",
            unit="1",
        )

        self._units_lost_counter = m.create_counter(
            name=MetricName.UNITS_LOST,
            description="Total units lost by the bot",
            unit="1",
        )

        self._minerals_collected_counter = m.create_counter(
            name=MetricName.MINERALS_COLLECTED,
            description="Cumulative minerals collected",
            unit="minerals",
        )

        self._vespene_collected_counter = m.create_counter(
            name=MetricName.VESPENE_COLLECTED,
            description="Cumulative vespene gas collected",
            unit="vespene",
        )

        self._supply_used_gauge = m.create_up_down_counter(
            name=MetricName.SUPPLY_USED,
            description="Current supply used",
            unit="1",
        )

        self._supply_cap_gauge = m.create_up_down_counter(
            name=MetricName.SUPPLY_CAP,
            description="Current supply cap",
            unit="1",
        )

        self._army_value_gauge = m.create_up_down_counter(
            name=MetricName.ARMY_VALUE,
            description="Estimated total army mineral+gas value",
            unit="resources",
        )

        self._active_workers_gauge = m.create_up_down_counter(
            name=MetricName.ACTIVE_WORKERS,
            description="Current number of active workers (drones)",
            unit="1",
        )

        self._active_bases_gauge = m.create_up_down_counter(
            name=MetricName.ACTIVE_BASES,
            description="Current number of active hatcheries/lairs/hives",
            unit="1",
        )

        self._apm_estimate_gauge = m.create_up_down_counter(
            name=MetricName.APM_ESTIMATE,
            description="Estimated actions per minute of the bot",
            unit="apm",
        )

        self._decision_latency_hist = m.create_histogram(
            name=MetricName.DECISION_LATENCY,
            description="Latency of combat/economy decision functions in ms",
            unit="ms",
        )

        self._creep_coverage_gauge = m.create_up_down_counter(
            name=MetricName.CREEP_COVERAGE,
            description="Estimated creep coverage percentage",
            unit="%",
        )

    # ------------------------------------------------------------------
    # Public Accessors
    # ------------------------------------------------------------------

    @property
    def tracer(self) -> Tracer:
        assert self._tracer is not None, "Call setup() before accessing tracer"
        return self._tracer

    @property
    def meter(self) -> Meter:
        assert self._meter is not None, "Call setup() before accessing meter"
        return self._meter

    # ------------------------------------------------------------------
    # Context Propagation & Baggage Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def set_baggage_item(key: str, value: str) -> object:
        """Set a baggage item and attach to the current context.

        Returns the context token for later detach.
        """
        ctx = set_baggage(key, value)
        return attach(ctx)

    @staticmethod
    def get_baggage_item(key: str) -> Optional[str]:
        """Retrieve a baggage value from the current context."""
        return get_baggage(key)

    @staticmethod
    def detach_context(token: object) -> None:
        """Detach a previously attached context token."""
        detach(token)

    @contextmanager
    def propagated_context(
        self, baggage_items: Optional[Dict[str, str]] = None
    ) -> Generator[None, None, None]:
        """Context manager that attaches baggage for cross-cutting concerns.

        Parameters
        ----------
        baggage_items:
            Key-value pairs to propagate via OTel baggage (e.g.,
            ``{"matchup": "ZvT", "map_name": "Equilibrium"}``).
        """
        tokens = []
        try:
            if baggage_items:
                for k, v in baggage_items.items():
                    tokens.append(self.set_baggage_item(k, v))
            yield
        finally:
            for tok in reversed(tokens):
                self.detach_context(tok)

    # ------------------------------------------------------------------
    # Span Attribute Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _game_state_attributes(
        game_time: Optional[float] = None,
        supply: Optional[int] = None,
        minerals: Optional[int] = None,
        vespene: Optional[int] = None,
        army_value: Optional[int] = None,
        worker_count: Optional[int] = None,
        base_count: Optional[int] = None,
        iteration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build a dict of span attributes from game state values."""
        attrs: Dict[str, Any] = {}
        if game_time is not None:
            attrs["sc2.game_time"] = game_time
        if supply is not None:
            attrs["sc2.supply"] = supply
        if minerals is not None:
            attrs["sc2.minerals"] = minerals
        if vespene is not None:
            attrs["sc2.vespene"] = vespene
        if army_value is not None:
            attrs["sc2.army_value"] = army_value
        if worker_count is not None:
            attrs["sc2.worker_count"] = worker_count
        if base_count is not None:
            attrs["sc2.base_count"] = base_count
        if iteration is not None:
            attrs["sc2.iteration"] = iteration
        return attrs

    # ------------------------------------------------------------------
    # Traced Operations (context managers)
    # ------------------------------------------------------------------

    @contextmanager
    def trace_on_step(
        self,
        game_time: float = 0.0,
        supply: int = 0,
        minerals: int = 0,
        vespene: int = 0,
        army_value: int = 0,
        worker_count: int = 0,
        base_count: int = 0,
        iteration: int = 0,
    ) -> Generator[Span, None, None]:
        """Trace the bot's main ``on_step`` loop iteration.

        Records duration via histogram and increments step counter.
        """
        attrs = self._game_state_attributes(
            game_time=game_time,
            supply=supply,
            minerals=minerals,
            vespene=vespene,
            army_value=army_value,
            worker_count=worker_count,
            base_count=base_count,
            iteration=iteration,
        )
        start = time.perf_counter_ns()
        with self.tracer.start_as_current_span(
            SpanName.ON_STEP,
            kind=SpanKind.INTERNAL,
            attributes=attrs,
        ) as span:
            try:
                yield span
                span.set_status(StatusCode.OK)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
            finally:
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                self._step_duration_hist.record(elapsed_ms, {"sc2.iteration": iteration})
                self._step_counter.add(1)

    @contextmanager
    def trace_combat_decision(
        self,
        game_time: float = 0.0,
        supply: int = 0,
        army_value: int = 0,
        enemy_army_value: Optional[int] = None,
        decision_type: str = "general",
    ) -> Generator[Span, None, None]:
        """Trace a combat decision evaluation."""
        attrs = self._game_state_attributes(
            game_time=game_time, supply=supply, army_value=army_value
        )
        attrs["sc2.decision_type"] = decision_type
        if enemy_army_value is not None:
            attrs["sc2.enemy_army_value"] = enemy_army_value

        start = time.perf_counter_ns()
        with self.tracer.start_as_current_span(
            SpanName.COMBAT_DECISION,
            kind=SpanKind.INTERNAL,
            attributes=attrs,
        ) as span:
            try:
                yield span
                span.set_status(StatusCode.OK)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
            finally:
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                self._decision_latency_hist.record(
                    elapsed_ms, {"sc2.decision_type": decision_type}
                )
                self._combat_decision_counter.add(
                    1, {"sc2.decision_type": decision_type}
                )

    @contextmanager
    def trace_economy_tick(
        self,
        game_time: float = 0.0,
        minerals: int = 0,
        vespene: int = 0,
        worker_count: int = 0,
        base_count: int = 0,
        income_rate_minerals: Optional[float] = None,
        income_rate_vespene: Optional[float] = None,
    ) -> Generator[Span, None, None]:
        """Trace an economy evaluation tick."""
        attrs = self._game_state_attributes(
            game_time=game_time,
            minerals=minerals,
            vespene=vespene,
            worker_count=worker_count,
            base_count=base_count,
        )
        if income_rate_minerals is not None:
            attrs["sc2.income_rate_minerals"] = income_rate_minerals
        if income_rate_vespene is not None:
            attrs["sc2.income_rate_vespene"] = income_rate_vespene

        start = time.perf_counter_ns()
        with self.tracer.start_as_current_span(
            SpanName.ECONOMY_TICK,
            kind=SpanKind.INTERNAL,
            attributes=attrs,
        ) as span:
            try:
                yield span
                span.set_status(StatusCode.OK)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise
            finally:
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                self._decision_latency_hist.record(
                    elapsed_ms, {"sc2.decision_type": "economy"}
                )

    @contextmanager
    def trace_operation(
        self,
        span_name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Generic traced operation for any bot sub-system."""
        with self.tracer.start_as_current_span(
            span_name, kind=kind, attributes=attributes or {}
        ) as span:
            try:
                yield span
                span.set_status(StatusCode.OK)
            except Exception as exc:
                span.set_status(StatusCode.ERROR, str(exc))
                span.record_exception(exc)
                raise

    # ------------------------------------------------------------------
    # Span Events for Significant Game Events
    # ------------------------------------------------------------------

    @staticmethod
    def record_attack_started(
        span: Span,
        target_position: tuple[float, float],
        army_supply: int,
        army_composition: Optional[Dict[str, int]] = None,
    ) -> None:
        """Record an 'attack_started' span event."""
        event_attrs: Dict[str, Any] = {
            "sc2.target_x": target_position[0],
            "sc2.target_y": target_position[1],
            "sc2.army_supply": army_supply,
        }
        if army_composition:
            for unit_type, count in army_composition.items():
                event_attrs[f"sc2.army.{unit_type}"] = count
        span.add_event("attack_started", attributes=event_attrs)

    @staticmethod
    def record_expansion_built(
        span: Span,
        position: tuple[float, float],
        base_number: int,
        game_time: float,
    ) -> None:
        """Record an 'expansion_built' span event."""
        span.add_event(
            "expansion_built",
            attributes={
                "sc2.expansion_x": position[0],
                "sc2.expansion_y": position[1],
                "sc2.base_number": base_number,
                "sc2.game_time": game_time,
            },
        )

    @staticmethod
    def record_upgrade_started(
        span: Span,
        upgrade_name: str,
        game_time: float,
    ) -> None:
        """Record an 'upgrade_started' span event."""
        span.add_event(
            "upgrade_started",
            attributes={
                "sc2.upgrade_name": upgrade_name,
                "sc2.game_time": game_time,
            },
        )

    @staticmethod
    def record_supply_blocked(span: Span, game_time: float, duration: float) -> None:
        """Record a 'supply_blocked' span event."""
        span.add_event(
            "supply_blocked",
            attributes={
                "sc2.game_time": game_time,
                "sc2.blocked_duration": duration,
            },
        )

    @staticmethod
    def record_enemy_detected(
        span: Span,
        unit_type: str,
        position: tuple[float, float],
        game_time: float,
    ) -> None:
        """Record an 'enemy_detected' span event."""
        span.add_event(
            "enemy_detected",
            attributes={
                "sc2.enemy_unit_type": unit_type,
                "sc2.enemy_x": position[0],
                "sc2.enemy_y": position[1],
                "sc2.game_time": game_time,
            },
        )

    @staticmethod
    def record_tech_transition(
        span: Span,
        from_tech: str,
        to_tech: str,
        game_time: float,
    ) -> None:
        """Record a 'tech_transition' span event (e.g., lair -> hive)."""
        span.add_event(
            "tech_transition",
            attributes={
                "sc2.from_tech": from_tech,
                "sc2.to_tech": to_tech,
                "sc2.game_time": game_time,
            },
        )

    # ------------------------------------------------------------------
    # Metric Recording Helpers
    # ------------------------------------------------------------------

    def record_units_created(self, unit_type: str, count: int = 1) -> None:
        """Increment the units-created counter."""
        self._units_created_counter.add(count, {"sc2.unit_type": unit_type})

    def record_units_lost(self, unit_type: str, count: int = 1) -> None:
        """Increment the units-lost counter."""
        self._units_lost_counter.add(count, {"sc2.unit_type": unit_type})

    def record_minerals_collected(self, amount: int) -> None:
        self._minerals_collected_counter.add(amount)

    def record_vespene_collected(self, amount: int) -> None:
        self._vespene_collected_counter.add(amount)

    def update_supply(self, used_delta: int = 0, cap_delta: int = 0) -> None:
        """Adjust supply gauges by the given deltas."""
        if used_delta:
            self._supply_used_gauge.add(used_delta)
        if cap_delta:
            self._supply_cap_gauge.add(cap_delta)

    def update_army_value(self, delta: int) -> None:
        self._army_value_gauge.add(delta)

    def update_active_workers(self, delta: int) -> None:
        self._active_workers_gauge.add(delta)

    def update_active_bases(self, delta: int) -> None:
        self._active_bases_gauge.add(delta)

    def update_apm_estimate(self, delta: int) -> None:
        self._apm_estimate_gauge.add(delta)

    def update_creep_coverage(self, delta_pct: float) -> None:
        self._creep_coverage_gauge.add(delta_pct)

    # ------------------------------------------------------------------
    # Integration: Bot Module Context Propagation
    # ------------------------------------------------------------------

    def create_linked_span(
        self,
        name: str,
        parent_span: Span,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Create a child span explicitly linked to a parent.

        Useful for propagating context between loosely-coupled bot modules
        (e.g., scouting module feeding into combat decision module).
        """
        parent_ctx = set_span_in_context(parent_span)
        return self.tracer.start_span(
            name, context=parent_ctx, attributes=attributes or {}
        )

    @contextmanager
    def cross_module_trace(
        self,
        span_name: str,
        parent_span: Optional[Span] = None,
        baggage_items: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """Trace an operation across bot modules with full context propagation.

        Combines parent span linking, baggage propagation, and attribute
        attachment in a single convenience context manager.
        """
        tokens = []
        try:
            if baggage_items:
                for k, v in baggage_items.items():
                    tokens.append(self.set_baggage_item(k, v))

            ctx = None
            if parent_span is not None:
                ctx = set_span_in_context(parent_span)

            with self.tracer.start_as_current_span(
                span_name,
                context=ctx,
                kind=SpanKind.INTERNAL,
                attributes=attributes or {},
            ) as span:
                try:
                    yield span
                    span.set_status(StatusCode.OK)
                except Exception as exc:
                    span.set_status(StatusCode.ERROR, str(exc))
                    span.record_exception(exc)
                    raise
        finally:
            for tok in reversed(tokens):
                self.detach_context(tok)


# ---------------------------------------------------------------------------
# Convenience: Module-Level Quick Setup
# ---------------------------------------------------------------------------

_global_instrumentation: Optional[SC2OTelInstrumentation] = None


def get_instrumentation() -> SC2OTelInstrumentation:
    """Return the global SC2OTelInstrumentation singleton."""
    if _global_instrumentation is None:
        raise RuntimeError(
            "SC2 OTel instrumentation has not been initialised. "
            "Call init_instrumentation() first."
        )
    return _global_instrumentation


def init_instrumentation(
    otlp_endpoint: str = "localhost:4317",
    sampling_strategy: SamplingStrategy = SamplingStrategy.PARENT_BASED,
    sampling_ratio: float = 1.0,
    enable_prometheus: bool = True,
    **kwargs: Any,
) -> SC2OTelInstrumentation:
    """Initialise and return the global instrumentation singleton.

    Parameters are forwarded to :class:`SC2OTelInstrumentation`.
    """
    global _global_instrumentation
    _global_instrumentation = SC2OTelInstrumentation(
        otlp_endpoint=otlp_endpoint,
        sampling_strategy=sampling_strategy,
        sampling_ratio=sampling_ratio,
        enable_prometheus=enable_prometheus,
        **kwargs,
    )
    _global_instrumentation.setup()
    return _global_instrumentation


def shutdown_instrumentation() -> None:
    """Shutdown the global instrumentation singleton."""
    global _global_instrumentation
    if _global_instrumentation is not None:
        _global_instrumentation.shutdown()
        _global_instrumentation = None


# ---------------------------------------------------------------------------
# Example Usage (guarded)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("sc2_otel_demo")

    otel = init_instrumentation(
        otlp_endpoint="localhost:4317",
        sampling_strategy=SamplingStrategy.ALWAYS_ON,
        enable_prometheus=True,
        enable_console_export=True,
        environment="development",
    )

    # Simulate a game loop with baggage for cross-cutting match metadata
    with otel.propagated_context(
        baggage_items={"matchup": "ZvT", "map_name": "Equilibrium", "ladder_season": "2026-S1"}
    ):
        for iteration in range(5):
            game_time = iteration * 22.4

            with otel.trace_on_step(
                game_time=game_time,
                supply=44 + iteration * 4,
                minerals=350 - iteration * 20,
                vespene=200 + iteration * 10,
                army_value=1200 + iteration * 300,
                worker_count=16 + iteration * 2,
                base_count=2,
                iteration=iteration,
            ) as step_span:

                # Economy sub-trace
                with otel.trace_economy_tick(
                    game_time=game_time,
                    minerals=350 - iteration * 20,
                    vespene=200 + iteration * 10,
                    worker_count=16 + iteration * 2,
                    base_count=2,
                    income_rate_minerals=800.0,
                    income_rate_vespene=220.0,
                ) as econ_span:
                    otel.record_minerals_collected(50)
                    otel.record_vespene_collected(25)

                    if iteration == 2:
                        otel.record_expansion_built(
                            econ_span,
                            position=(45.0, 60.0),
                            base_number=3,
                            game_time=game_time,
                        )
                        otel.update_active_bases(1)

                # Combat sub-trace
                with otel.trace_combat_decision(
                    game_time=game_time,
                    supply=44 + iteration * 4,
                    army_value=1200 + iteration * 300,
                    enemy_army_value=1000 + iteration * 200,
                    decision_type="aggression_check",
                ) as combat_span:
                    otel.record_units_created("Zergling", count=4)

                    if iteration == 3:
                        otel.record_attack_started(
                            combat_span,
                            target_position=(55.0, 32.0),
                            army_supply=60,
                            army_composition={"Zergling": 24, "Roach": 8, "Ravager": 4},
                        )

                # Cross-module trace example
                with otel.cross_module_trace(
                    SpanName.SCOUTING,
                    parent_span=step_span,
                    baggage_items={"scout_type": "overlord"},
                    attributes={"sc2.game_time": game_time},
                ) as scout_span:
                    if iteration == 1:
                        otel.record_enemy_detected(
                            scout_span,
                            unit_type="Marine",
                            position=(30.0, 25.0),
                            game_time=game_time,
                        )

            logger.info(
                "Completed iteration %d at game_time=%.1f", iteration, game_time
            )

    shutdown_instrumentation()
    logger.info("OpenTelemetry instrumentation demo complete.")
