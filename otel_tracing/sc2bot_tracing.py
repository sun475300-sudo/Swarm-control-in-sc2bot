"""
sc2bot_tracing.py — Phase 347: OpenTelemetry distributed tracing for SC2 bot
Configures a TracerProvider with Jaeger exporter and provides span decorators
for key game-loop subsystems. Supports context propagation across microservices
and custom semantic attributes for race, map, and ladder MMR.
"""

import functools
from typing import Callable, Any

# OpenTelemetry core imports
from opentelemetry import trace, baggage, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

# Jaeger exporter (OTLP/gRPC to Jaeger ≥ 1.35, or legacy Thrift)
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Propagators for distributed context (W3C TraceContext + Baggage)
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry import propagate
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator

# ---------------------------------------------------------------------------
# Resource & Provider Setup
# ---------------------------------------------------------------------------

_RESOURCE = Resource.create(
    {
        SERVICE_NAME: "sc2bot",
        SERVICE_VERSION: "1.0.0",
        "deployment.environment": "production",
        "sc2bot.component": "game-loop",
    }
)

_jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent.monitoring.svc.cluster.local",
    agent_port=6831,          # UDP/Thrift compact protocol
    # udp_split_oversized_batches=True,
)

_provider = TracerProvider(resource=_RESOURCE)
_provider.add_span_processor(BatchSpanProcessor(_jaeger_exporter))
# Also emit spans to console during local development
_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

trace.set_tracer_provider(_provider)

# Configure composite propagator: W3C TraceContext + Baggage + B3
propagate.set_global_textmap(
    CompositePropagator(
        [
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
            B3MultiFormat(),
        ]
    )
)

# Module-level tracer
_tracer = trace.get_tracer(__name__, schema_url="https://opentelemetry.io/schemas/1.21.0")


# ---------------------------------------------------------------------------
# Helper: attach SC2-specific semantic attributes to the current span
# ---------------------------------------------------------------------------

def _attach_game_attributes(span: trace.Span, race: str = "", map_name: str = "", mmr: int = 0) -> None:
    """Enrich a span with SC2 bot domain attributes."""
    if race:
        span.set_attribute("sc2bot.race", race)
    if map_name:
        span.set_attribute("sc2bot.map", map_name)
    if mmr:
        span.set_attribute("sc2bot.ladder_mmr", mmr)
    span.set_attribute("sc2bot.service", "game-loop")


# ---------------------------------------------------------------------------
# Span Decorators
# ---------------------------------------------------------------------------

def game_decision_span(race: str = "", map_name: str = "", mmr: int = 0) -> Callable:
    """
    Decorator that wraps a game-decision function in an OTel span.
    Captures high-level strategic decision calls (build order evaluation,
    macro/micro priority arbiter).
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with _tracer.start_as_current_span(
                f"sc2bot.decision.{func.__name__}",
                kind=trace.SpanKind.INTERNAL,
            ) as span:
                _attach_game_attributes(span, race, map_name, mmr)
                span.set_attribute("sc2bot.decision.function", func.__name__)
                # Propagate baggage values set by the caller
                _race = baggage.get_baggage("sc2bot.race") or race
                _map  = baggage.get_baggage("sc2bot.map")  or map_name
                if _race:
                    span.set_attribute("sc2bot.race", _race)
                if _map:
                    span.set_attribute("sc2bot.map", _map)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(trace.StatusCode.ERROR, str(exc))
                    raise
        return wrapper
    return decorator


def pathfinding_span(func: Callable) -> Callable:
    """
    Decorator for pathfinding calls.
    Records unit_tag, start/end tile coordinates, and path length.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        unit_tag = kwargs.get("unit_tag", args[1] if len(args) > 1 else "unknown")
        with _tracer.start_as_current_span(
            "sc2bot.pathfinding",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("sc2bot.pathfinding.unit_tag", str(unit_tag))
            span.set_attribute("sc2bot.pathfinding.algorithm", "pathing_map_bfs")
            try:
                result = func(*args, **kwargs)
                path_len = len(result) if hasattr(result, "__len__") else -1
                span.set_attribute("sc2bot.pathfinding.path_length", path_len)
                span.set_status(trace.StatusCode.OK)
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise
    return wrapper


def combat_calc_span(func: Callable) -> Callable:
    """
    Decorator for combat calculation functions.
    Records army_supply, enemy_supply, and engagement outcome.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with _tracer.start_as_current_span(
            f"sc2bot.combat.{func.__name__}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("sc2bot.combat.function", func.__name__)
            army_supply   = kwargs.get("army_supply", 0)
            enemy_supply  = kwargs.get("enemy_supply", 0)
            span.set_attribute("sc2bot.combat.army_supply",  army_supply)
            span.set_attribute("sc2bot.combat.enemy_supply", enemy_supply)
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    span.set_attribute("sc2bot.combat.engage", result.get("engage", False))
                span.set_status(trace.StatusCode.OK)
                return result
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR, str(exc))
                raise
    return wrapper


# ---------------------------------------------------------------------------
# Context Propagation between microservices
# ---------------------------------------------------------------------------

def inject_context_headers(headers: dict) -> dict:
    """
    Inject the current OTel trace context and baggage into an outgoing
    HTTP-style headers dict (for gRPC metadata or REST calls to sub-services).
    """
    propagate.inject(headers)
    return headers


def extract_context_from_headers(headers: dict) -> context.Context:
    """
    Extract trace context from incoming request headers and return an
    OTel Context object that can be passed to start_as_current_span().
    """
    return propagate.extract(headers)


def set_game_baggage(race: str, map_name: str, mmr: int) -> context.Context:
    """
    Attach SC2 game metadata as W3C Baggage so all downstream spans
    in the same logical trace automatically inherit these values.
    """
    ctx = baggage.set_baggage("sc2bot.race", race)
    ctx = baggage.set_baggage("sc2bot.map", map_name, context=ctx)
    ctx = baggage.set_baggage("sc2bot.ladder_mmr", str(mmr), context=ctx)
    return ctx
