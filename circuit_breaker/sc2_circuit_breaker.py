# Phase 661: Circuit Breaker Pattern for SC2 Service Resilience
# Protects SC2 bot services from cascading failures with circuit breaker, bulkhead, and retry patterns

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

T = TypeVar("T")


# ============================================================
# Enums and Constants
# ============================================================


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failures exceeded threshold, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class ServiceType(Enum):
    """SC2-specific service types protected by circuit breakers."""

    BOT_API = "bot_api"
    TRAINING_SERVICE = "training_service"
    DASHBOARD = "dashboard"
    REPLAY_ANALYZER = "replay_analyzer"
    MODEL_SERVER = "model_server"
    STRATEGY_DB = "strategy_db"


# ============================================================
# CircuitBreakerError
# ============================================================


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker OPEN for '{service_name}'. "
            f"Retry after {retry_after:.1f}s"
        )


class BulkheadFullError(Exception):
    """Raised when a bulkhead pool has no available capacity."""

    def __init__(self, pool_name: str, max_concurrent: int):
        self.pool_name = pool_name
        self.max_concurrent = max_concurrent
        super().__init__(
            f"Bulkhead '{pool_name}' at capacity ({max_concurrent} concurrent)"
        )


class DeadlineExceededError(Exception):
    """Raised when a deadline is exceeded."""

    pass


# ============================================================
# CircuitBreaker
# ============================================================


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker instance."""

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    monitoring_window_seconds: float = 60.0
    error_rate_threshold: float = 0.5  # 50% error rate triggers open


class CircuitBreaker:
    """
    Circuit breaker implementation with closed -> open -> half-open states.

    - CLOSED: requests flow normally, failures are counted.
    - OPEN: requests are rejected immediately, timer starts.
    - HALF_OPEN: limited requests allowed to test recovery.
    """

    def __init__(
        self, service_name: str, config: Optional[CircuitBreakerConfig] = None
    ):
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = 0.0
        self._opened_at = 0.0
        self._lock = threading.Lock()

        # Sliding window for monitoring
        self._request_log: deque = deque()  # (timestamp, success: bool)
        self._state_change_log: List[Dict[str, Any]] = []

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.config.timeout_seconds:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    def _transition_to(self, new_state: CircuitState) -> None:
        old_state = self._state
        self._state = new_state
        now = time.time()

        if new_state == CircuitState.OPEN:
            self._opened_at = now
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0

        self._state_change_log.append(
            {
                "timestamp": now,
                "from": old_state.value,
                "to": new_state.value,
                "service": self.service_name,
            }
        )

    def _clean_window(self) -> None:
        cutoff = time.time() - self.config.monitoring_window_seconds
        while self._request_log and self._request_log[0][0] < cutoff:
            self._request_log.popleft()

    def _check_error_rate(self) -> bool:
        """Return True if error rate exceeds threshold."""
        self._clean_window()
        if len(self._request_log) < 5:
            return False
        failures = sum(1 for _, success in self._request_log if not success)
        rate = failures / len(self._request_log)
        return rate >= self.config.error_rate_threshold

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function through the circuit breaker."""
        current_state = self.state

        with self._lock:
            if current_state == CircuitState.OPEN:
                retry_after = self.config.timeout_seconds - (
                    time.time() - self._opened_at
                )
                raise CircuitBreakerOpenError(self.service_name, max(retry_after, 0.0))

            if current_state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(self.service_name, 1.0)
                self._half_open_calls += 1

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        with self._lock:
            self._request_log.append((time.time(), True))
            self._success_count += 1
            self._failure_count = 0

            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        with self._lock:
            now = time.time()
            self._request_log.append((now, False))
            self._failure_count += 1
            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                elif self._check_error_rate():
                    self._transition_to(CircuitState.OPEN)

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._request_log.clear()

    def get_status(self) -> Dict[str, Any]:
        current = self.state
        with self._lock:
            self._clean_window()
            total_in_window = len(self._request_log)
            failures_in_window = sum(1 for _, s in self._request_log if not s)

        return {
            "service": self.service_name,
            "state": current.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "requests_in_window": total_in_window,
            "failures_in_window": failures_in_window,
            "error_rate": round(failures_in_window / max(total_in_window, 1), 4),
            "state_changes": len(self._state_change_log),
        }

    def get_state_history(self) -> List[Dict[str, Any]]:
        return list(self._state_change_log)


# ============================================================
# BulkheadIsolation
# ============================================================


class BulkheadIsolation:
    """
    Bulkhead pattern: isolates resource pools to prevent cascading failures.

    Each pool has a maximum number of concurrent executions. When a pool
    is full, new requests are rejected immediately rather than waiting.
    """

    def __init__(self, pool_name: str, max_concurrent: int = 10, queue_size: int = 5):
        self.pool_name = pool_name
        self.max_concurrent = max_concurrent
        self.queue_size = queue_size
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_count = 0
        self._rejected_count = 0
        self._completed_count = 0
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 0.0) -> bool:
        """Try to acquire a slot in the bulkhead."""
        acquired = (
            self._semaphore.acquire(timeout=timeout)
            if timeout > 0
            else self._semaphore.acquire(blocking=False)
        )
        if acquired:
            with self._lock:
                self._active_count += 1
            return True
        else:
            with self._lock:
                self._rejected_count += 1
            return False

    def release(self) -> None:
        """Release a slot back to the bulkhead."""
        self._semaphore.release()
        with self._lock:
            self._active_count = max(0, self._active_count - 1)
            self._completed_count += 1

    def execute(
        self, func: Callable[..., T], *args: Any, timeout: float = 0.0, **kwargs: Any
    ) -> T:
        """Execute a function within the bulkhead."""
        if not self.acquire(timeout=timeout):
            raise BulkheadFullError(self.pool_name, self.max_concurrent)
        try:
            return func(*args, **kwargs)
        finally:
            self.release()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pool_name": self.pool_name,
                "max_concurrent": self.max_concurrent,
                "active": self._active_count,
                "available": self.max_concurrent - self._active_count,
                "completed": self._completed_count,
                "rejected": self._rejected_count,
            }


# ============================================================
# RetryPolicy
# ============================================================


class RetryPolicy:
    """
    Retry policy with exponential backoff and jitter.

    Supports configurable max attempts, base delay, max delay,
    backoff multiplier, and jitter range.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        backoff_multiplier: float = 2.0,
        jitter_range: Tuple[float, float] = (0.0, 0.5),
        retryable_exceptions: Optional[Tuple[type, ...]] = None,
    ):
        self.max_attempts = max(max_attempts, 1)
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.jitter_range = jitter_range
        self.retryable_exceptions = retryable_exceptions or (Exception,)
        self._attempt_log: List[Dict[str, Any]] = []

    def _compute_delay(self, attempt: int) -> float:
        """Compute delay with exponential backoff and jitter."""
        delay = self.base_delay_seconds * (self.backoff_multiplier**attempt)
        delay = min(delay, self.max_delay_seconds)
        jitter = random.uniform(*self.jitter_range)
        return delay + jitter

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute with retry logic."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_attempts):
            try:
                result = func(*args, **kwargs)
                self._attempt_log.append(
                    {
                        "attempt": attempt + 1,
                        "success": True,
                        "timestamp": time.time(),
                    }
                )
                return result
            except self.retryable_exceptions as exc:
                last_exception = exc
                self._attempt_log.append(
                    {
                        "attempt": attempt + 1,
                        "success": False,
                        "error": str(exc),
                        "timestamp": time.time(),
                    }
                )
                if attempt < self.max_attempts - 1:
                    delay = self._compute_delay(attempt)
                    time.sleep(delay * 0.01)  # Scaled for demo

        assert last_exception is not None
        raise last_exception

    def get_attempt_history(self) -> List[Dict[str, Any]]:
        return list(self._attempt_log)

    def reset(self) -> None:
        self._attempt_log.clear()


# ============================================================
# DeadlinePropagation
# ============================================================


class DeadlinePropagation:
    """
    Deadline propagation across service calls.

    Tracks remaining time budget and propagates deadlines to
    downstream service calls to prevent unbounded waits.
    """

    def __init__(self, deadline_seconds: float):
        self.deadline_seconds = deadline_seconds
        self._start_time = time.time()
        self._checkpoints: List[Dict[str, Any]] = []

    @property
    def remaining(self) -> float:
        elapsed = time.time() - self._start_time
        return max(self.deadline_seconds - elapsed, 0.0)

    @property
    def is_expired(self) -> bool:
        return self.remaining <= 0.0

    def checkpoint(self, label: str) -> float:
        """Record a checkpoint and return remaining time."""
        remaining = self.remaining
        self._checkpoints.append(
            {
                "label": label,
                "elapsed": time.time() - self._start_time,
                "remaining": remaining,
            }
        )
        return remaining

    def execute_with_deadline(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """Execute a function, raising DeadlineExceededError if time runs out."""
        if self.is_expired:
            raise DeadlineExceededError(
                f"Deadline already expired ({self.deadline_seconds}s budget)"
            )
        result = func(*args, **kwargs)
        if self.is_expired:
            raise DeadlineExceededError(
                f"Deadline exceeded during execution ({self.deadline_seconds}s budget)"
            )
        return result

    def create_child(
        self, label: str, budget_fraction: float = 1.0
    ) -> "DeadlinePropagation":
        """Create a child deadline with a fraction of remaining budget."""
        remaining = self.remaining
        child_budget = remaining * min(max(budget_fraction, 0.0), 1.0)
        self.checkpoint(f"child:{label}")
        return DeadlinePropagation(child_budget)

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        return list(self._checkpoints)


# ============================================================
# ServiceHealthMonitor
# ============================================================


class ServiceHealthMonitor:
    """Monitors health metrics for protected services."""

    def __init__(self):
        self._service_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def record_call(self, service: str, success: bool, latency_ms: float) -> None:
        with self._lock:
            if service not in self._service_stats:
                self._service_stats[service] = {
                    "total_calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "latencies": [],
                    "last_failure_time": None,
                }
            stats = self._service_stats[service]
            stats["total_calls"] += 1
            if success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
                stats["last_failure_time"] = time.time()
            stats["latencies"].append(latency_ms)
            # Keep only last 1000 latency samples
            if len(stats["latencies"]) > 1000:
                stats["latencies"] = stats["latencies"][-500:]

    def get_health(self, service: str) -> Dict[str, Any]:
        with self._lock:
            stats = self._service_stats.get(service)
            if not stats:
                return {"service": service, "status": "unknown"}
            total = stats["total_calls"]
            failures = stats["failures"]
            error_rate = failures / max(total, 1)
            lats = stats["latencies"]
            return {
                "service": service,
                "total_calls": total,
                "error_rate": round(error_rate, 4),
                "avg_latency_ms": round(sum(lats) / max(len(lats), 1), 2),
                "status": (
                    "healthy"
                    if error_rate < 0.1
                    else ("degraded" if error_rate < 0.5 else "unhealthy")
                ),
            }

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for svc in list(self._service_stats.keys()):
            result[svc] = self.get_health(svc)
        return result


# ============================================================
# ResilienceManager
# ============================================================


class ResilienceManager:
    """
    Central manager combining circuit breakers, bulkheads, retries,
    and deadline propagation for SC2 service resilience.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._bulkheads: Dict[str, BulkheadIsolation] = {}
        self._retry_policies: Dict[str, RetryPolicy] = {}
        self._health_monitor = ServiceHealthMonitor()
        self._lock = threading.Lock()

    def register_service(
        self,
        service_name: str,
        breaker_config: Optional[CircuitBreakerConfig] = None,
        bulkhead_max_concurrent: int = 10,
        retry_max_attempts: int = 3,
        retry_base_delay: float = 0.5,
    ) -> None:
        """Register a service with all resilience patterns."""
        with self._lock:
            self._breakers[service_name] = CircuitBreaker(
                service_name, breaker_config or CircuitBreakerConfig()
            )
            self._bulkheads[service_name] = BulkheadIsolation(
                service_name, max_concurrent=bulkhead_max_concurrent
            )
            self._retry_policies[service_name] = RetryPolicy(
                max_attempts=retry_max_attempts,
                base_delay_seconds=retry_base_delay,
            )

    def call(
        self,
        service_name: str,
        func: Callable[..., T],
        *args: Any,
        deadline_seconds: Optional[float] = None,
        **kwargs: Any,
    ) -> T:
        """
        Execute a function with full resilience stack:
        deadline -> bulkhead -> circuit breaker -> retry -> function
        """
        breaker = self._breakers.get(service_name)
        bulkhead = self._bulkheads.get(service_name)
        retry = self._retry_policies.get(service_name)

        if not breaker:
            raise ValueError(f"Service '{service_name}' not registered")

        # Wrap with deadline if specified
        deadline: Optional[DeadlinePropagation] = None
        if deadline_seconds is not None:
            deadline = DeadlinePropagation(deadline_seconds)

        start_time = time.time()
        try:
            # Bulkhead gate
            if bulkhead and not bulkhead.acquire(timeout=0.0):
                raise BulkheadFullError(service_name, bulkhead.max_concurrent)

            try:
                # Circuit breaker + retry
                def _protected_call() -> T:
                    return breaker.call(func, *args, **kwargs)

                if retry:
                    result = retry.execute(_protected_call)
                else:
                    result = _protected_call()

                # Check deadline
                if deadline and deadline.is_expired:
                    raise DeadlineExceededError(f"Deadline exceeded for {service_name}")

                latency = (time.time() - start_time) * 1000
                self._health_monitor.record_call(service_name, True, latency)
                return result

            finally:
                if bulkhead:
                    bulkhead.release()

        except (CircuitBreakerOpenError, BulkheadFullError, DeadlineExceededError):
            latency = (time.time() - start_time) * 1000
            self._health_monitor.record_call(service_name, False, latency)
            raise
        except Exception:
            latency = (time.time() - start_time) * 1000
            self._health_monitor.record_call(service_name, False, latency)
            raise

    def get_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        return self._breakers.get(service_name)

    def get_bulkhead(self, service_name: str) -> Optional[BulkheadIsolation]:
        return self._bulkheads.get(service_name)

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {"service": service_name}
        breaker = self._breakers.get(service_name)
        if breaker:
            result["circuit_breaker"] = breaker.get_status()
        bulkhead = self._bulkheads.get(service_name)
        if bulkhead:
            result["bulkhead"] = bulkhead.get_status()
        result["health"] = self._health_monitor.get_health(service_name)
        return result

    def get_all_status(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {}
        for svc_name in self._breakers:
            status[svc_name] = self.get_service_status(svc_name)
        return status

    def reset_service(self, service_name: str) -> None:
        breaker = self._breakers.get(service_name)
        if breaker:
            breaker.reset()
        retry = self._retry_policies.get(service_name)
        if retry:
            retry.reset()

    def reset_all(self) -> None:
        for svc_name in list(self._breakers.keys()):
            self.reset_service(svc_name)


# ============================================================
# SC2 Service Simulators
# ============================================================


class SC2ServiceSimulator:
    """Simulates SC2 backend services with configurable failure rates."""

    def __init__(
        self,
        service_name: str,
        base_latency_ms: float = 10.0,
        failure_rate: float = 0.0,
    ):
        self.service_name = service_name
        self.base_latency_ms = base_latency_ms
        self.failure_rate = failure_rate
        self._call_count = 0

    def call(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        self._call_count += 1
        # Simulate processing time
        latency = self.base_latency_ms * random.uniform(0.5, 2.0)
        time.sleep(latency / 10000.0)  # Scaled down

        if random.random() < self.failure_rate:
            raise ConnectionError(
                f"Service '{self.service_name}' unavailable (simulated)"
            )

        return {
            "service": self.service_name,
            "call_number": self._call_count,
            "latency_ms": latency,
            "status": "ok",
        }

    def set_failure_rate(self, rate: float) -> None:
        self.failure_rate = max(0.0, min(rate, 1.0))


# ============================================================
# FallbackHandler
# ============================================================


class FallbackHandler:
    """Provides fallback responses when primary services are unavailable."""

    def __init__(self):
        self._fallback_cache: Dict[str, Any] = {}
        self._fallback_count = 0

    def cache_response(self, service_name: str, response: Any) -> None:
        self._fallback_cache[service_name] = {
            "response": response,
            "cached_at": time.time(),
        }

    def get_fallback(self, service_name: str) -> Optional[Any]:
        cached = self._fallback_cache.get(service_name)
        if cached:
            self._fallback_count += 1
            return cached["response"]
        return None

    def call_with_fallback(
        self,
        manager: ResilienceManager,
        service_name: str,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Try the primary call; on failure, return cached fallback."""
        try:
            result = manager.call(service_name, func, *args, **kwargs)
            self.cache_response(service_name, result)
            return result
        except Exception:
            fallback = self.get_fallback(service_name)
            if fallback is not None:
                return fallback
            return {"error": f"Service {service_name} unavailable, no fallback cached"}

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cached_services": list(self._fallback_cache.keys()),
            "fallback_invocations": self._fallback_count,
        }


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate SC2 Circuit Breaker and Resilience capabilities."""
    print("=" * 70)
    print("  Phase 661: Circuit Breaker Pattern for SC2 Service Resilience")
    print("=" * 70)

    # --- 1. Basic Circuit Breaker ---
    print("\n[1] Basic Circuit Breaker")
    cb = CircuitBreaker(
        "bot_api",
        CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1.0,
        ),
    )
    print(f"    Initial state: {cb.state.value}")

    # Simulate failures to trip the breaker
    fail_count = 0
    for i in range(5):
        try:

            def _failing_call() -> str:
                raise ConnectionError("Service down")

            cb.call(_failing_call)
        except ConnectionError:
            fail_count += 1
        except CircuitBreakerOpenError as e:
            print(f"    Call {i+1}: REJECTED - {e}")
            break

    print(f"    State after {fail_count} failures: {cb.state.value}")
    status = cb.get_status()
    print(
        f"    Status: failures={status['failure_count']}, "
        f"error_rate={status['error_rate']}"
    )

    # Wait for timeout and test half-open
    print("    Waiting for circuit timeout...")
    time.sleep(1.1)
    print(f"    State after timeout: {cb.state.value}")

    # Recover with successes
    for _ in range(3):
        try:
            cb.call(lambda: "ok")
        except CircuitBreakerOpenError:
            pass
    print(f"    State after recovery: {cb.state.value}")

    # --- 2. Bulkhead Isolation ---
    print("\n[2] Bulkhead Isolation")
    bulkhead = BulkheadIsolation("training_pool", max_concurrent=3)

    results = []
    for i in range(5):
        try:
            result = bulkhead.execute(lambda idx=i: f"task-{idx} done")
            results.append(result)
        except BulkheadFullError as e:
            results.append(f"REJECTED: {e}")

    bh_status = bulkhead.get_status()
    print(
        f"    Pool: {bh_status['pool_name']}, "
        f"completed={bh_status['completed']}, "
        f"rejected={bh_status['rejected']}"
    )

    # --- 3. Retry with Exponential Backoff ---
    print("\n[3] Retry Policy (Exponential Backoff)")
    retry = RetryPolicy(
        max_attempts=4,
        base_delay_seconds=0.1,
        backoff_multiplier=2.0,
        jitter_range=(0.0, 0.05),
    )

    call_counter = {"count": 0}

    def _flaky_service() -> str:
        call_counter["count"] += 1
        if call_counter["count"] < 3:
            raise ConnectionError(f"Attempt {call_counter['count']} failed")
        return "Success on attempt 3"

    try:
        result = retry.execute(_flaky_service)
        print(f"    Result: {result}")
    except Exception as e:
        print(f"    Final failure: {e}")

    history = retry.get_attempt_history()
    for entry in history:
        status_str = "OK" if entry["success"] else f"FAIL: {entry.get('error', '')}"
        print(f"    Attempt {entry['attempt']}: {status_str}")

    # --- 4. Deadline Propagation ---
    print("\n[4] Deadline Propagation")
    deadline = DeadlinePropagation(deadline_seconds=2.0)
    remaining = deadline.checkpoint("start")
    print(f"    Budget: 2.0s, Remaining at start: {remaining:.2f}s")

    child = deadline.create_child("sub_service", budget_fraction=0.5)
    print(f"    Child budget (50%): {child.deadline_seconds:.2f}s")

    try:
        result = deadline.execute_with_deadline(lambda: "fast response")
        print(f"    Result: {result}")
    except DeadlineExceededError as e:
        print(f"    Deadline exceeded: {e}")

    checkpoints = deadline.get_checkpoints()
    print(f"    Checkpoints: {len(checkpoints)}")

    # --- 5. ResilienceManager (Full Stack) ---
    print("\n[5] ResilienceManager - Full Resilience Stack")
    manager = ResilienceManager()

    # Register SC2 services
    for svc in ServiceType:
        manager.register_service(
            svc.value,
            breaker_config=CircuitBreakerConfig(
                failure_threshold=3, timeout_seconds=1.0
            ),
            bulkhead_max_concurrent=5,
            retry_max_attempts=2,
        )

    # Normal calls
    sim_api = SC2ServiceSimulator("bot_api", base_latency_ms=10.0, failure_rate=0.0)
    for _ in range(5):
        try:
            result = manager.call(ServiceType.BOT_API.value, sim_api.call)
        except Exception as e:
            print(f"    Error: {e}")
    api_status = manager.get_service_status(ServiceType.BOT_API.value)
    print(
        f"    Bot API - state: {api_status['circuit_breaker']['state']}, "
        f"health: {api_status['health']['status']}"
    )

    # Degrade a service
    sim_training = SC2ServiceSimulator(
        "training", base_latency_ms=50.0, failure_rate=0.8
    )
    for _ in range(10):
        try:
            manager.call(ServiceType.TRAINING_SERVICE.value, sim_training.call)
        except Exception:
            pass
    training_status = manager.get_service_status(ServiceType.TRAINING_SERVICE.value)
    print(
        f"    Training - state: {training_status['circuit_breaker']['state']}, "
        f"health: {training_status['health']['status']}"
    )

    # --- 6. Fallback Handler ---
    print("\n[6] Fallback Handler")
    fallback = FallbackHandler()

    # Cache a good response first
    sim_dashboard = SC2ServiceSimulator(
        "dashboard", base_latency_ms=15.0, failure_rate=0.0
    )
    result = fallback.call_with_fallback(
        manager, ServiceType.DASHBOARD.value, sim_dashboard.call
    )
    print(f"    Dashboard normal: status={result.get('status', 'N/A')}")

    # Now make dashboard fail
    sim_dashboard.set_failure_rate(1.0)
    for _ in range(5):
        result = fallback.call_with_fallback(
            manager, ServiceType.DASHBOARD.value, sim_dashboard.call
        )
    fb_stats = fallback.get_stats()
    print(f"    Fallback invocations: {fb_stats['fallback_invocations']}")
    print(f"    Cached services: {fb_stats['cached_services']}")

    # --- 7. Full System Status ---
    print("\n[7] Full System Status")
    all_status = manager.get_all_status()
    for svc_name, svc_status in all_status.items():
        cb_state = svc_status.get("circuit_breaker", {}).get("state", "N/A")
        health = svc_status.get("health", {}).get("status", "unknown")
        bh = svc_status.get("bulkhead", {})
        print(
            f"    {svc_name:20s} | CB: {cb_state:10s} | "
            f"Health: {health:10s} | BH completed: {bh.get('completed', 0)}"
        )

    # --- 8. State History ---
    print("\n[8] Circuit Breaker State History")
    breaker = manager.get_breaker(ServiceType.TRAINING_SERVICE.value)
    if breaker:
        for change in breaker.get_state_history():
            print(
                f"    {change['from']:10s} -> {change['to']:10s} "
                f"({change['service']})"
            )

    print("\n" + "=" * 70)
    print("Phase 661 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 661: Circuit Breaker registered
