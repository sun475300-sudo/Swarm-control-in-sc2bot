# SC2 Bot - OpenTelemetry SDK Custom Spans
# Advanced OpenTelemetry SDK usage with custom processors, exporters, and semantic conventions

from opentelemetry import trace, metrics, baggage, context
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from typing import Sequence
import logging


# --- Custom Span Processor ---
class SC2GameEventSpanProcessor(SpanProcessor):
    """Custom processor that enriches SC2 game event spans."""

    def on_start(self, span, parent_context=None):
        span.set_attribute("sc2.component", "bot_core")
        span.set_attribute("sc2.framework", "python-sc2")

    def on_end(self, span: ReadableSpan):
        if span.status.is_ok and span.duration_ns > 5_000_000:  # > 5ms
            logging.warning(
                f"[SC2 OTEL] Slow span: {span.name} took {span.duration_ns / 1e6:.1f}ms"
            )


# --- Custom Exporter ---
class SC2MetricsLinkingExporter:
    """Exporter that links SC2 trace exemplars to metrics."""

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            exemplar = {
                "trace_id": format(span.context.trace_id, "032x"),
                "span_id": format(span.context.span_id, "016x"),
                "timestamp": span.end_time,
                "value": span.attributes.get("sc2.minerals_collected", 0),
            }
            logging.debug(f"[SC2 Exemplar] {exemplar}")
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


# --- Resource & Provider Setup ---
resource = Resource.create(
    {
        SERVICE_NAME: "sc2-bot",
        SERVICE_VERSION: "2.0.0",
        "sc2.race": "Zerg",
        "deployment.environment": "production",
    }
)

otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
sampler = TraceIdRatioBased(0.1)  # Sample 10% of traces

provider = TracerProvider(
    resource=resource,
    sampler=sampler,
)
provider.add_span_processor(SC2GameEventSpanProcessor())
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("sc2.bot", "2.0.0")

# --- Context Propagation Across Microservices ---
propagator = TraceContextTextMapPropagator()


def inject_trace_context(headers: dict) -> dict:
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict):
    return propagator.extract(headers)


# --- SC2 Semantic Conventions ---
SC2_SPAN_GAME_STEP = "sc2.game.step"
SC2_SPAN_ATTACK = "sc2.unit.attack"
SC2_SPAN_BUILD = "sc2.unit.build"
SC2_SPAN_STRATEGY = "sc2.strategy.decision"


def trace_game_step(step: int, minerals: int, vespene: int, supply: int):
    with tracer.start_as_current_span(SC2_SPAN_GAME_STEP) as span:
        span.set_attribute("sc2.game_loop", step)
        span.set_attribute("sc2.minerals", minerals)
        span.set_attribute("sc2.vespene", vespene)
        span.set_attribute("sc2.supply_used", supply)
        span.set_attribute(SpanAttributes.CODE_FUNCTION, "on_step")
        return span


def trace_attack_wave(unit_count: int, target: str):
    with tracer.start_as_current_span(SC2_SPAN_ATTACK) as span:
        span.set_attribute("sc2.attack.unit_count", unit_count)
        span.set_attribute("sc2.attack.target", target)
        span.add_event("attack_wave_launched", {"units": unit_count})


def trace_strategy_decision(strategy: str, confidence: float):
    with tracer.start_as_current_span(SC2_SPAN_STRATEGY) as span:
        span.set_attribute("sc2.strategy.name", strategy)
        span.set_attribute("sc2.strategy.confidence", confidence)
        span.add_event("strategy_selected")
