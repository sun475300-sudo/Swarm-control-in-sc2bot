"""
Phase 662: Rate Limiter for SC2 API Protection
================================================
Rate limiting algorithms for SC2 bot API protection.

Implements multiple rate limiting strategies:
- Token Bucket: smooth burst handling with refill rate
- Sliding Window Log: precise per-request tracking
- Sliding Window Counter: memory-efficient approximation
- Leaky Bucket: constant output rate queue
- Fixed Window: simple time-window counters

SC2-specific features:
- Bot action rate limiting (APM control)
- API query frequency management
- Replay upload throttling
- Per-client tracking by IP, API key, or user ID
- Distributed rate limiting across bot instances
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class LimitResult(Enum):
    """Result of a rate limit check."""

    ALLOWED = "allowed"
    DENIED = "denied"
    THROTTLED = "throttled"


class ClientIdentifierType(Enum):
    """How to identify a client for rate limiting."""

    IP = "ip"
    API_KEY = "api_key"
    USER_ID = "user_id"
    BOT_ID = "bot_id"
    COMPOSITE = "composite"


@dataclass
class RateLimitConfig:
    """Configuration for a rate limiter."""

    max_requests: int = 100
    window_seconds: float = 60.0
    burst_size: int = 10
    refill_rate: float = 1.0  # tokens per second
    penalty_seconds: float = 0.0
    name: str = "default"


@dataclass
class RateLimitResponse:
    """Response from a rate limit check."""

    result: LimitResult
    remaining: int = 0
    retry_after: float = 0.0
    limit: int = 0
    reset_at: float = 0.0
    client_id: str = ""

    @property
    def allowed(self) -> bool:
        return self.result == LimitResult.ALLOWED

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP rate-limit headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
            "Retry-After": str(int(self.retry_after)) if self.retry_after > 0 else "0",
        }


@dataclass
class ClientRecord:
    """Tracks per-client rate limit state."""

    client_id: str
    identifier_type: ClientIdentifierType = ClientIdentifierType.IP
    total_requests: int = 0
    total_denied: int = 0
    first_seen: float = field(default_factory=time.time)
    last_request: float = 0.0
    penalty_until: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Token Bucket Algorithm
# ---------------------------------------------------------------------------


class TokenBucket:
    """
    Token bucket rate limiter.

    Tokens are added at a fixed refill_rate. Each request consumes one token.
    Bursts up to bucket_size are allowed.
    """

    def __init__(self, bucket_size: int = 10, refill_rate: float = 1.0):
        self._bucket_size = bucket_size
        self._refill_rate = refill_rate
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def _get_tokens(self, client_id: str, now: float) -> float:
        if client_id not in self._buckets:
            self._buckets[client_id] = (float(self._bucket_size), now)
            return float(self._bucket_size)
        tokens, last_refill = self._buckets[client_id]
        elapsed = now - last_refill
        new_tokens = min(self._bucket_size, tokens + elapsed * self._refill_rate)
        return new_tokens

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        """Try to consume tokens from the bucket."""
        now = time.time()
        with self._lock:
            available = self._get_tokens(client_id, now)
            if available >= tokens:
                remaining = available - tokens
                self._buckets[client_id] = (remaining, now)
                return RateLimitResponse(
                    result=LimitResult.ALLOWED,
                    remaining=int(remaining),
                    limit=self._bucket_size,
                    reset_at=now
                    + (self._bucket_size - remaining) / max(self._refill_rate, 0.001),
                    client_id=client_id,
                )
            else:
                wait_time = (tokens - available) / max(self._refill_rate, 0.001)
                self._buckets[client_id] = (available, now)
                return RateLimitResponse(
                    result=LimitResult.DENIED,
                    remaining=0,
                    retry_after=wait_time,
                    limit=self._bucket_size,
                    reset_at=now + wait_time,
                    client_id=client_id,
                )

    def reset(self, client_id: str) -> None:
        with self._lock:
            self._buckets.pop(client_id, None)

    def get_status(self, client_id: str) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            tokens = self._get_tokens(client_id, now)
        return {
            "algorithm": "token_bucket",
            "bucket_size": self._bucket_size,
            "refill_rate": self._refill_rate,
            "available_tokens": round(tokens, 2),
            "client_id": client_id,
        }


# ---------------------------------------------------------------------------
# Sliding Window Log Algorithm
# ---------------------------------------------------------------------------


class SlidingWindowLog:
    """
    Sliding window log rate limiter.

    Stores timestamps of all requests within the window. Precise but
    memory-intensive for high-volume clients.
    """

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self._max_requests = max_requests
        self._window = window_seconds
        self._logs: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup(self, client_id: str, now: float) -> None:
        cutoff = now - self._window
        log = self._logs[client_id]
        while log and log[0] < cutoff:
            log.pop(0)

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        now = time.time()
        with self._lock:
            self._cleanup(client_id, now)
            log = self._logs[client_id]
            current_count = len(log)
            if current_count + tokens <= self._max_requests:
                for _ in range(tokens):
                    log.append(now)
                remaining = self._max_requests - len(log)
                reset_at = log[0] + self._window if log else now + self._window
                return RateLimitResponse(
                    result=LimitResult.ALLOWED,
                    remaining=remaining,
                    limit=self._max_requests,
                    reset_at=reset_at,
                    client_id=client_id,
                )
            else:
                oldest = log[0] if log else now
                retry_after = oldest + self._window - now
                return RateLimitResponse(
                    result=LimitResult.DENIED,
                    remaining=0,
                    retry_after=max(0.0, retry_after),
                    limit=self._max_requests,
                    reset_at=oldest + self._window,
                    client_id=client_id,
                )

    def reset(self, client_id: str) -> None:
        with self._lock:
            self._logs.pop(client_id, None)

    def get_status(self, client_id: str) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            self._cleanup(client_id, now)
            count = len(self._logs.get(client_id, []))
        return {
            "algorithm": "sliding_window_log",
            "max_requests": self._max_requests,
            "window_seconds": self._window,
            "current_count": count,
            "remaining": max(0, self._max_requests - count),
            "client_id": client_id,
        }


# ---------------------------------------------------------------------------
# Sliding Window Counter Algorithm
# ---------------------------------------------------------------------------


class SlidingWindowCounter:
    """
    Sliding window counter rate limiter.

    Approximates the sliding window using weighted counters from the
    current and previous fixed windows. Memory-efficient.
    """

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self._max_requests = max_requests
        self._window = window_seconds
        # {client_id: {window_key: count}}
        self._counters: Dict[str, Dict[int, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._lock = threading.Lock()

    def _window_key(self, timestamp: float) -> int:
        return int(timestamp // self._window)

    def _estimate_count(self, client_id: str, now: float) -> float:
        current_key = self._window_key(now)
        prev_key = current_key - 1
        counters = self._counters[client_id]
        current_count = counters.get(current_key, 0)
        prev_count = counters.get(prev_key, 0)
        elapsed_in_window = now - (current_key * self._window)
        weight = elapsed_in_window / self._window
        return current_count + prev_count * (1.0 - weight)

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        now = time.time()
        with self._lock:
            estimated = self._estimate_count(client_id, now)
            if estimated + tokens <= self._max_requests:
                current_key = self._window_key(now)
                self._counters[client_id][current_key] += tokens
                # Clean old windows
                old_keys = [k for k in self._counters[client_id] if k < current_key - 1]
                for k in old_keys:
                    del self._counters[client_id][k]
                remaining = int(self._max_requests - estimated - tokens)
                reset_at = (current_key + 1) * self._window
                return RateLimitResponse(
                    result=LimitResult.ALLOWED,
                    remaining=max(0, remaining),
                    limit=self._max_requests,
                    reset_at=reset_at,
                    client_id=client_id,
                )
            else:
                current_key = self._window_key(now)
                reset_at = (current_key + 1) * self._window
                retry_after = reset_at - now
                return RateLimitResponse(
                    result=LimitResult.DENIED,
                    remaining=0,
                    retry_after=retry_after,
                    limit=self._max_requests,
                    reset_at=reset_at,
                    client_id=client_id,
                )

    def reset(self, client_id: str) -> None:
        with self._lock:
            self._counters.pop(client_id, None)

    def get_status(self, client_id: str) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            estimated = self._estimate_count(client_id, now)
        return {
            "algorithm": "sliding_window_counter",
            "max_requests": self._max_requests,
            "window_seconds": self._window,
            "estimated_count": round(estimated, 2),
            "remaining": max(0, int(self._max_requests - estimated)),
            "client_id": client_id,
        }


# ---------------------------------------------------------------------------
# Leaky Bucket Algorithm
# ---------------------------------------------------------------------------


class LeakyBucket:
    """
    Leaky bucket rate limiter.

    Requests enter a queue (bucket) and are processed at a constant
    leak_rate. If the bucket is full, requests are rejected.
    """

    def __init__(self, bucket_size: int = 10, leak_rate: float = 1.0):
        self._bucket_size = bucket_size
        self._leak_rate = leak_rate  # requests per second
        # {client_id: (water_level, last_check_time)}
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def _get_level(self, client_id: str, now: float) -> float:
        if client_id not in self._buckets:
            return 0.0
        level, last_check = self._buckets[client_id]
        elapsed = now - last_check
        leaked = elapsed * self._leak_rate
        return max(0.0, level - leaked)

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        now = time.time()
        with self._lock:
            current_level = self._get_level(client_id, now)
            if current_level + tokens <= self._bucket_size:
                new_level = current_level + tokens
                self._buckets[client_id] = (new_level, now)
                remaining = int(self._bucket_size - new_level)
                drain_time = new_level / max(self._leak_rate, 0.001)
                return RateLimitResponse(
                    result=LimitResult.ALLOWED,
                    remaining=remaining,
                    limit=self._bucket_size,
                    reset_at=now + drain_time,
                    client_id=client_id,
                )
            else:
                overflow = current_level + tokens - self._bucket_size
                retry_after = overflow / max(self._leak_rate, 0.001)
                self._buckets[client_id] = (current_level, now)
                return RateLimitResponse(
                    result=LimitResult.DENIED,
                    remaining=0,
                    retry_after=retry_after,
                    limit=self._bucket_size,
                    reset_at=now + retry_after,
                    client_id=client_id,
                )

    def reset(self, client_id: str) -> None:
        with self._lock:
            self._buckets.pop(client_id, None)

    def get_status(self, client_id: str) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            level = self._get_level(client_id, now)
        return {
            "algorithm": "leaky_bucket",
            "bucket_size": self._bucket_size,
            "leak_rate": self._leak_rate,
            "current_level": round(level, 2),
            "remaining_capacity": max(0, int(self._bucket_size - level)),
            "client_id": client_id,
        }


# ---------------------------------------------------------------------------
# Fixed Window Counter
# ---------------------------------------------------------------------------


class FixedWindowCounter:
    """
    Fixed window counter rate limiter.

    Counts requests in non-overlapping fixed time windows.
    Simple but susceptible to boundary bursts.
    """

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self._max_requests = max_requests
        self._window = window_seconds
        self._counters: Dict[str, Tuple[int, int]] = {}  # client -> (window_key, count)
        self._lock = threading.Lock()

    def _window_key(self, now: float) -> int:
        return int(now // self._window)

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        now = time.time()
        current_key = self._window_key(now)
        with self._lock:
            if client_id in self._counters:
                stored_key, count = self._counters[client_id]
                if stored_key != current_key:
                    count = 0
            else:
                count = 0

            if count + tokens <= self._max_requests:
                count += tokens
                self._counters[client_id] = (current_key, count)
                remaining = self._max_requests - count
                reset_at = (current_key + 1) * self._window
                return RateLimitResponse(
                    result=LimitResult.ALLOWED,
                    remaining=remaining,
                    limit=self._max_requests,
                    reset_at=reset_at,
                    client_id=client_id,
                )
            else:
                reset_at = (current_key + 1) * self._window
                return RateLimitResponse(
                    result=LimitResult.DENIED,
                    remaining=0,
                    retry_after=reset_at - now,
                    limit=self._max_requests,
                    reset_at=reset_at,
                    client_id=client_id,
                )

    def reset(self, client_id: str) -> None:
        with self._lock:
            self._counters.pop(client_id, None)

    def get_status(self, client_id: str) -> Dict[str, Any]:
        now = time.time()
        current_key = self._window_key(now)
        with self._lock:
            if client_id in self._counters:
                stored_key, count = self._counters[client_id]
                if stored_key != current_key:
                    count = 0
            else:
                count = 0
        return {
            "algorithm": "fixed_window",
            "max_requests": self._max_requests,
            "window_seconds": self._window,
            "current_count": count,
            "remaining": max(0, self._max_requests - count),
            "client_id": client_id,
        }


# ---------------------------------------------------------------------------
# SC2-Specific Rate Limit Policies
# ---------------------------------------------------------------------------


class SC2ActionLimiter:
    """
    SC2-specific rate limiter for bot actions.

    Controls APM (actions per minute), query frequency, and
    replay upload rates.
    """

    def __init__(self):
        # Bot actions: 300 APM max (5/sec)
        self.action_limiter = TokenBucket(bucket_size=20, refill_rate=5.0)
        # API queries: 60 per minute
        self.query_limiter = SlidingWindowLog(max_requests=60, window_seconds=60.0)
        # Replay uploads: 10 per hour
        self.upload_limiter = FixedWindowCounter(max_requests=10, window_seconds=3600.0)
        # Chat commands: 20 per minute
        self.chat_limiter = LeakyBucket(bucket_size=5, leak_rate=0.33)
        # Observer API: 120 per minute
        self.observer_limiter = SlidingWindowCounter(
            max_requests=120, window_seconds=60.0
        )

    def check_action(self, bot_id: str) -> RateLimitResponse:
        """Check if a bot action is allowed (APM control)."""
        return self.action_limiter.consume(bot_id)

    def check_query(self, bot_id: str) -> RateLimitResponse:
        """Check if an API query is allowed."""
        return self.query_limiter.consume(bot_id)

    def check_upload(self, bot_id: str) -> RateLimitResponse:
        """Check if a replay upload is allowed."""
        return self.upload_limiter.consume(bot_id)

    def check_chat(self, bot_id: str) -> RateLimitResponse:
        """Check if a chat command is allowed."""
        return self.chat_limiter.consume(bot_id)

    def check_observer(self, bot_id: str) -> RateLimitResponse:
        """Check if an observer API call is allowed."""
        return self.observer_limiter.consume(bot_id)

    def get_all_status(self, bot_id: str) -> Dict[str, Any]:
        return {
            "actions": self.action_limiter.get_status(bot_id),
            "queries": self.query_limiter.get_status(bot_id),
            "uploads": self.upload_limiter.get_status(bot_id),
            "chat": self.chat_limiter.get_status(bot_id),
            "observer": self.observer_limiter.get_status(bot_id),
        }


# ---------------------------------------------------------------------------
# Distributed Rate Limiter (Coordination Layer)
# ---------------------------------------------------------------------------


class DistributedRateLimiter:
    """
    Distributed rate limiting across multiple bot instances.

    Uses a shared state store (in-memory for demo, pluggable for Redis/etc.)
    to coordinate rate limits across processes.
    """

    def __init__(self, instance_id: str, total_instances: int = 1):
        self._instance_id = instance_id
        self._total_instances = max(1, total_instances)
        self._shared_state: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._local_limiter: Optional[TokenBucket] = None

    def configure(self, global_limit: int, window_seconds: float = 60.0) -> None:
        """Configure with global limit split across instances."""
        per_instance = max(1, global_limit // self._total_instances)
        self._local_limiter = TokenBucket(
            bucket_size=per_instance,
            refill_rate=per_instance / max(window_seconds, 0.001),
        )
        logger.info(
            "Distributed limiter %s: global=%d, per_instance=%d, instances=%d",
            self._instance_id,
            global_limit,
            per_instance,
            self._total_instances,
        )

    def consume(self, client_id: str, tokens: int = 1) -> RateLimitResponse:
        if self._local_limiter is None:
            self.configure(global_limit=100)
        assert self._local_limiter is not None
        response = self._local_limiter.consume(client_id, tokens)
        with self._lock:
            key = f"{self._instance_id}:{client_id}"
            self._shared_state[key] = {
                "instance": self._instance_id,
                "client": client_id,
                "result": response.result.value,
                "timestamp": time.time(),
            }
        return response

    def get_global_state(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._shared_state)

    def sync_state(self, remote_state: Dict[str, Dict[str, Any]]) -> None:
        """Merge remote instance state for coordination."""
        with self._lock:
            self._shared_state.update(remote_state)


# ---------------------------------------------------------------------------
# Per-Client Tracker
# ---------------------------------------------------------------------------


class ClientTracker:
    """Tracks per-client rate limit metadata."""

    def __init__(self):
        self._clients: Dict[str, ClientRecord] = {}
        self._lock = threading.Lock()

    def identify(
        self,
        raw_id: str,
        id_type: ClientIdentifierType = ClientIdentifierType.IP,
    ) -> str:
        """Normalize and hash a client identifier."""
        normalized = raw_id.strip().lower()
        if id_type == ClientIdentifierType.API_KEY:
            return hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return normalized

    def record_request(self, client_id: str, allowed: bool) -> ClientRecord:
        now = time.time()
        with self._lock:
            if client_id not in self._clients:
                self._clients[client_id] = ClientRecord(
                    client_id=client_id,
                    first_seen=now,
                )
            record = self._clients[client_id]
            record.total_requests += 1
            record.last_request = now
            if not allowed:
                record.total_denied += 1
            return record

    def apply_penalty(self, client_id: str, seconds: float) -> None:
        now = time.time()
        with self._lock:
            if client_id in self._clients:
                self._clients[client_id].penalty_until = now + seconds

    def is_penalized(self, client_id: str) -> bool:
        with self._lock:
            record = self._clients.get(client_id)
            if record is None:
                return False
            return time.time() < record.penalty_until

    def get_top_clients(self, n: int = 10) -> List[ClientRecord]:
        with self._lock:
            sorted_clients = sorted(
                self._clients.values(),
                key=lambda r: r.total_requests,
                reverse=True,
            )
            return sorted_clients[:n]

    def get_abuse_candidates(self, deny_threshold: float = 0.5) -> List[ClientRecord]:
        """Find clients with high denial rates."""
        with self._lock:
            results = []
            for record in self._clients.values():
                if record.total_requests > 10:
                    deny_rate = record.total_denied / record.total_requests
                    if deny_rate >= deny_threshold:
                        results.append(record)
            return results


# ---------------------------------------------------------------------------
# Unified RateLimiter Facade
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Unified rate limiter combining multiple algorithms.

    Provides a single interface for SC2 bot API protection with
    configurable policies per endpoint.
    """

    ALGORITHM_MAP = {
        "token_bucket": TokenBucket,
        "sliding_window_log": SlidingWindowLog,
        "sliding_window_counter": SlidingWindowCounter,
        "leaky_bucket": LeakyBucket,
        "fixed_window": FixedWindowCounter,
    }

    def __init__(self, default_algorithm: str = "token_bucket"):
        self._default_algorithm = default_algorithm
        self._policies: Dict[str, Any] = {}  # endpoint -> limiter instance
        self._tracker = ClientTracker()
        self._sc2_limiter = SC2ActionLimiter()
        self._callbacks: List[Callable] = []
        self._stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"allowed": 0, "denied": 0}
        )
        self._lock = threading.Lock()

    def add_policy(
        self,
        endpoint: str,
        algorithm: str = "token_bucket",
        **kwargs: Any,
    ) -> None:
        """Register a rate limit policy for an endpoint."""
        cls = self.ALGORITHM_MAP.get(algorithm)
        if cls is None:
            raise ValueError(
                f"Unknown algorithm: {algorithm}. Available: {list(self.ALGORITHM_MAP)}"
            )
        self._policies[endpoint] = cls(**kwargs)
        logger.info(
            "Policy added: endpoint=%s, algorithm=%s, params=%s",
            endpoint,
            algorithm,
            kwargs,
        )

    def check(
        self, endpoint: str, client_id: str, tokens: int = 1
    ) -> RateLimitResponse:
        """Check rate limit for an endpoint and client."""
        # Check penalty first
        if self._tracker.is_penalized(client_id):
            response = RateLimitResponse(
                result=LimitResult.DENIED,
                remaining=0,
                retry_after=5.0,
                client_id=client_id,
            )
        elif endpoint in self._policies:
            response = self._policies[endpoint].consume(client_id, tokens)
        else:
            # Auto-create default policy
            self.add_policy(
                endpoint, self._default_algorithm, bucket_size=50, refill_rate=5.0
            )
            response = self._policies[endpoint].consume(client_id, tokens)

        # Track
        self._tracker.record_request(client_id, response.allowed)
        with self._lock:
            key = "allowed" if response.allowed else "denied"
            self._stats[endpoint][key] += 1

        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(endpoint, client_id, response)
            except Exception as e:
                logger.warning("Rate limit callback error: %s", e)

        return response

    def check_sc2_action(self, bot_id: str) -> RateLimitResponse:
        """Check SC2 bot action rate."""
        return self._sc2_limiter.check_action(bot_id)

    def check_sc2_query(self, bot_id: str) -> RateLimitResponse:
        """Check SC2 API query rate."""
        return self._sc2_limiter.check_query(bot_id)

    def check_sc2_upload(self, bot_id: str) -> RateLimitResponse:
        """Check SC2 replay upload rate."""
        return self._sc2_limiter.check_upload(bot_id)

    def on_limit_event(self, callback: Callable) -> None:
        """Register a callback for rate limit events."""
        self._callbacks.append(callback)

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        with self._lock:
            return dict(self._stats)

    def get_client_info(self, client_id: str) -> Optional[ClientRecord]:
        records = self._tracker.get_top_clients(n=1000)
        for r in records:
            if r.client_id == client_id:
                return r
        return None

    def get_abuse_report(self) -> List[Dict[str, Any]]:
        candidates = self._tracker.get_abuse_candidates()
        return [
            {
                "client_id": c.client_id,
                "total_requests": c.total_requests,
                "total_denied": c.total_denied,
                "deny_rate": round(c.total_denied / max(c.total_requests, 1), 3),
            }
            for c in candidates
        ]

    def penalize(self, client_id: str, seconds: float = 60.0) -> None:
        """Apply a temporary ban to a client."""
        self._tracker.apply_penalty(client_id, seconds)
        logger.info("Client %s penalized for %.1f seconds", client_id, seconds)

    def reset_client(self, client_id: str) -> None:
        """Reset all rate limits for a client."""
        for limiter in self._policies.values():
            limiter.reset(client_id)

    def get_sc2_status(self, bot_id: str) -> Dict[str, Any]:
        return self._sc2_limiter.get_all_status(bot_id)

    def summary(self) -> Dict[str, Any]:
        return {
            "policies": list(self._policies.keys()),
            "default_algorithm": self._default_algorithm,
            "stats": self.get_stats(),
            "abuse_candidates": len(self._tracker.get_abuse_candidates()),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate rate limiting algorithms for SC2 API protection."""
    print("=" * 70)
    print("Phase 662: Rate Limiter for SC2 API Protection - Demo")
    print("=" * 70)

    # --- Token Bucket ---
    print("\n[1] Token Bucket (burst-friendly)")
    tb = TokenBucket(bucket_size=5, refill_rate=2.0)
    for i in range(8):
        resp = tb.consume("bot_alpha")
        print(f"  Request {i+1}: {resp.result.value:>8s} | remaining={resp.remaining}")

    # --- Sliding Window Log ---
    print("\n[2] Sliding Window Log (precise tracking)")
    swl = SlidingWindowLog(max_requests=5, window_seconds=10.0)
    for i in range(7):
        resp = swl.consume("player_1")
        status = "PASS" if resp.allowed else "DENY"
        print(f"  Request {i+1}: {status} | remaining={resp.remaining}")

    # --- Sliding Window Counter ---
    print("\n[3] Sliding Window Counter (memory-efficient)")
    swc = SlidingWindowCounter(max_requests=5, window_seconds=10.0)
    for i in range(7):
        resp = swc.consume("player_2")
        status = "PASS" if resp.allowed else "DENY"
        print(f"  Request {i+1}: {status} | remaining={resp.remaining}")

    # --- Leaky Bucket ---
    print("\n[4] Leaky Bucket (constant drain)")
    lb = LeakyBucket(bucket_size=4, leak_rate=1.0)
    for i in range(6):
        resp = lb.consume("bot_beta")
        status = "PASS" if resp.allowed else "DENY"
        print(f"  Request {i+1}: {status} | remaining={resp.remaining}")

    # --- Fixed Window ---
    print("\n[5] Fixed Window Counter (simple)")
    fw = FixedWindowCounter(max_requests=3, window_seconds=60.0)
    for i in range(5):
        resp = fw.consume("bot_gamma")
        status = "PASS" if resp.allowed else "DENY"
        print(f"  Request {i+1}: {status} | remaining={resp.remaining}")

    # --- SC2 Action Limiter ---
    print("\n[6] SC2-Specific Action Limiter")
    sc2 = SC2ActionLimiter()
    for i in range(6):
        action_resp = sc2.check_action("zerg_rush_bot")
        query_resp = sc2.check_query("zerg_rush_bot")
        print(
            f"  Tick {i+1}: action={action_resp.result.value:>7s} "
            f"(rem={action_resp.remaining}) | "
            f"query={query_resp.result.value:>7s} (rem={query_resp.remaining})"
        )
    status = sc2.get_all_status("zerg_rush_bot")
    print(f"  Bot status keys: {list(status.keys())}")

    # --- Unified RateLimiter ---
    print("\n[7] Unified RateLimiter Facade")
    rl = RateLimiter(default_algorithm="token_bucket")
    rl.add_policy(
        "game/action", algorithm="token_bucket", bucket_size=10, refill_rate=3.0
    )
    rl.add_policy(
        "api/query",
        algorithm="sliding_window_log",
        max_requests=20,
        window_seconds=60.0,
    )
    rl.add_policy(
        "replay/upload", algorithm="fixed_window", max_requests=5, window_seconds=3600.0
    )

    events_log: List[str] = []
    rl.on_limit_event(lambda ep, cid, r: events_log.append(f"{ep}:{r.result.value}"))

    for i in range(12):
        resp = rl.check("game/action", "bot_001")
    print(f"  game/action (12 reqs): stats={rl.get_stats().get('game/action', {})}")

    for i in range(3):
        resp = rl.check("replay/upload", "bot_001")
    print(f"  replay/upload (3 reqs): stats={rl.get_stats().get('replay/upload', {})}")

    print(f"  Event log entries: {len(events_log)}")
    print(f"  Summary: {json.dumps(rl.summary(), indent=2)}")

    # --- Distributed ---
    print("\n[8] Distributed Rate Limiting")
    d1 = DistributedRateLimiter("instance_1", total_instances=3)
    d2 = DistributedRateLimiter("instance_2", total_instances=3)
    d1.configure(global_limit=90, window_seconds=60.0)
    d2.configure(global_limit=90, window_seconds=60.0)
    r1 = d1.consume("shared_client")
    r2 = d2.consume("shared_client")
    print(f"  Instance 1: {r1.result.value} (remaining={r1.remaining})")
    print(f"  Instance 2: {r2.result.value} (remaining={r2.remaining})")
    d1.sync_state(d2.get_global_state())
    print(f"  Synced state entries: {len(d1.get_global_state())}")

    # --- Per-Client Tracking ---
    print("\n[9] Per-Client Tracking & Abuse Detection")
    tracker = ClientTracker()
    for i in range(20):
        tracker.record_request("abuser_x", allowed=(i < 5))
    for i in range(10):
        tracker.record_request("normal_user", allowed=True)
    top = tracker.get_top_clients(3)
    print(f"  Top clients: {[(c.client_id, c.total_requests) for c in top]}")
    abusers = tracker.get_abuse_candidates(deny_threshold=0.5)
    print(f"  Abuse candidates: {[c.client_id for c in abusers]}")

    # --- Penalty ---
    print("\n[10] Client Penalty System")
    rl.penalize("bad_bot", seconds=30.0)
    resp = rl.check("game/action", "bad_bot")
    print(f"  Penalized client request: {resp.result.value}")

    print("\n" + "=" * 70)
    print("Phase 662 Demo Complete")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 662: Rate Limiter registered
