"""
Phase 500: gRPC Auth Interceptor for SC2 Bot — 500 Phases Milestone!
Server-side interceptor: JWT validation, metadata extraction, rate limiting
"""

import logging
import os
import time
from collections import defaultdict
from typing import Any, Callable

import grpc
import jwt

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
PUBLIC_METHODS = {"/sc2.advanced.v1.SC2BotAdvancedService/WatchLeaderboard"}
RATE_LIMIT_RPS = 100
RATE_WINDOW_SEC = 1


class SC2AuthInterceptor(grpc.ServerInterceptor):
    """JWT authentication and rate-limiting interceptor for SC2 gRPC server."""

    def __init__(self):
        self._rate_counters: dict = defaultdict(list)

    # ── Rate limiting ───────────────────────────────────────────────────────

    def _is_rate_limited(self, client_id: str) -> bool:
        now = time.monotonic()
        window_start = now - RATE_WINDOW_SEC
        calls = self._rate_counters[client_id]
        # Evict old timestamps
        self._rate_counters[client_id] = [t for t in calls if t > window_start]
        if len(self._rate_counters[client_id]) >= RATE_LIMIT_RPS:
            return True
        self._rate_counters[client_id].append(now)
        return False

    # ── Token extraction ────────────────────────────────────────────────────

    @staticmethod
    def _extract_token(metadata) -> str | None:
        for key, value in metadata:
            if key == "authorization" and value.startswith("Bearer "):
                return value[7:]
        return None

    # ── JWT validation ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise grpc.RpcError(grpc.StatusCode.UNAUTHENTICATED, "Token expired")
        except jwt.InvalidTokenError as e:
            raise grpc.RpcError(grpc.StatusCode.UNAUTHENTICATED, f"Invalid token: {e}")

    # ── Main intercept logic ────────────────────────────────────────────────

    def intercept_service(self, continuation: Callable, handler_call_details):
        method = handler_call_details.method
        metadata = dict(handler_call_details.invocation_metadata)

        # Extract request-id for tracing
        request_id = metadata.get("x-sc2bot-request-id", "unknown")
        logger.debug(f"[{request_id}] Intercepting {method}")

        # Allow public methods without auth
        if method in PUBLIC_METHODS:
            return continuation(handler_call_details)

        # Extract and validate JWT
        token = self._extract_token(handler_call_details.invocation_metadata)
        if not token:

            def abort(request, context):
                context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "Missing authorization token"
                )

            return grpc.unary_unary_rpc_method_handler(abort)

        try:
            payload = self._validate_token(token)
        except grpc.RpcError as e:

            def abort(request, context):
                context.abort(e.code(), e.details())

            return grpc.unary_unary_rpc_method_handler(abort)

        # Rate limiting per user
        user_id = payload.get("sub", "anonymous")
        if self._is_rate_limited(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")

            def abort(request, context):
                context.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "Rate limit exceeded")

            return grpc.unary_unary_rpc_method_handler(abort)

        logger.info(f"[{request_id}] Authenticated user={user_id} method={method}")
        return continuation(handler_call_details)


def create_server_with_interceptor(port: int = 50051) -> grpc.Server:
    """Create gRPC server with auth interceptor."""
    interceptor = SC2AuthInterceptor()
    server = grpc.server(
        grpc.experimental.gevent_executor(),
        interceptors=[interceptor],
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
        ],
    )
    server.add_insecure_port(f"[::]:{port}")
    return server
