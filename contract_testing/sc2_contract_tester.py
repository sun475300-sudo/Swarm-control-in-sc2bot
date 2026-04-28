"""
Phase 656: Contract Testing for SC2 Microservices
==================================================
Consumer-driven contract testing framework for StarCraft II bot services.
Validates API contracts between bot core, dashboard, and training service
using Pact-style consumer expectations and provider verification.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ContractStatus(Enum):
    """Status of a contract verification."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"


class HttpMethod(Enum):
    """Supported HTTP methods for contract interactions."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class SchemaType(Enum):
    """Supported JSON Schema primitive types."""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InteractionRequest:
    """Describes the expected request in a contract interaction."""

    method: HttpMethod
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    query: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None

    def matches(self, actual: "InteractionRequest") -> Tuple[bool, List[str]]:
        """Check whether an actual request matches this expectation."""
        errors: List[str] = []
        if self.method != actual.method:
            errors.append(
                f"Method mismatch: expected {self.method.value}, got {actual.method.value}"
            )
        if self.path != actual.path:
            errors.append(f"Path mismatch: expected {self.path}, got {actual.path}")
        for key, value in self.headers.items():
            actual_val = actual.headers.get(key)
            if actual_val != value:
                errors.append(
                    f"Header '{key}' mismatch: expected '{value}', got '{actual_val}'"
                )
        for key, value in self.query.items():
            actual_val = actual.query.get(key)
            if actual_val != value:
                errors.append(
                    f"Query param '{key}' mismatch: expected '{value}', got '{actual_val}'"
                )
        if self.body is not None and actual.body != self.body:
            errors.append("Request body mismatch")
        return (len(errors) == 0, errors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "path": self.path,
            "headers": self.headers,
            "query": self.query,
            "body": self.body,
        }


@dataclass
class InteractionResponse:
    """Describes the expected response in a contract interaction."""

    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    body_schema: Optional[Dict[str, Any]] = None

    def matches(self, actual: "InteractionResponse") -> Tuple[bool, List[str]]:
        """Validate an actual response against expected response."""
        errors: List[str] = []
        if self.status != actual.status:
            errors.append(
                f"Status mismatch: expected {self.status}, got {actual.status}"
            )
        for key, value in self.headers.items():
            actual_val = actual.headers.get(key)
            if actual_val != value:
                errors.append(
                    f"Response header '{key}' mismatch: expected '{value}', got '{actual_val}'"
                )
        if self.body is not None and actual.body is not None:
            body_ok, body_errors = _deep_match(self.body, actual.body, path="body")
            errors.extend(body_errors)
        if self.body_schema is not None and actual.body is not None:
            schema_ok, schema_errors = validate_schema(actual.body, self.body_schema)
            errors.extend(schema_errors)
        return (len(errors) == 0, errors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "headers": self.headers,
            "body": self.body,
            "body_schema": self.body_schema,
        }


@dataclass
class Interaction:
    """A single request-response pair in a contract."""

    description: str
    request: InteractionRequest
    response: InteractionResponse
    provider_state: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "provider_state": self.provider_state,
            "request": self.request.to_dict(),
            "response": self.response.to_dict(),
        }


# ---------------------------------------------------------------------------
# Schema Validation
# ---------------------------------------------------------------------------


def validate_schema(
    data: Any,
    schema: Dict[str, Any],
    path: str = "$",
) -> Tuple[bool, List[str]]:
    """
    Validate *data* against a simplified JSON Schema definition.
    Supports: type, properties, required, items, enum, minimum, maximum,
    minLength, maxLength, pattern.
    """
    errors: List[str] = []

    # --- type check ---
    schema_type = schema.get("type")
    if schema_type is not None:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected_types = type_map.get(schema_type)
        if expected_types is not None and not isinstance(data, expected_types):
            errors.append(
                f"{path}: expected type '{schema_type}', got '{type(data).__name__}'"
            )
            return (False, errors)

    # --- enum ---
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path}: value {data!r} not in enum {schema['enum']}")

    # --- string constraints ---
    if isinstance(data, str):
        if "minLength" in schema and len(data) < schema["minLength"]:
            errors.append(
                f"{path}: string length {len(data)} < minLength {schema['minLength']}"
            )
        if "maxLength" in schema and len(data) > schema["maxLength"]:
            errors.append(
                f"{path}: string length {len(data)} > maxLength {schema['maxLength']}"
            )
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errors.append(
                f"{path}: string does not match pattern '{schema['pattern']}'"
            )

    # --- numeric constraints ---
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errors.append(f"{path}: value {data} < minimum {schema['minimum']}")
        if "maximum" in schema and data > schema["maximum"]:
            errors.append(f"{path}: value {data} > maximum {schema['maximum']}")

    # --- object constraints ---
    if isinstance(data, dict):
        required_keys = schema.get("required", [])
        for rk in required_keys:
            if rk not in data:
                errors.append(f"{path}: missing required property '{rk}'")
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if prop_name in data:
                _, prop_errors = validate_schema(
                    data[prop_name], prop_schema, path=f"{path}.{prop_name}"
                )
                errors.extend(prop_errors)

    # --- array constraints ---
    if isinstance(data, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            for idx, item in enumerate(data):
                _, item_errors = validate_schema(
                    item, items_schema, path=f"{path}[{idx}]"
                )
                errors.extend(item_errors)

    return (len(errors) == 0, errors)


def _deep_match(
    expected: Any,
    actual: Any,
    path: str = "",
) -> Tuple[bool, List[str]]:
    """Recursively match expected body against actual body (subset match)."""
    errors: List[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            errors.append(f"{path}: expected object, got {type(actual).__name__}")
            return (False, errors)
        for key, val in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing in actual response")
            else:
                _, sub_errors = _deep_match(val, actual[key], path=f"{path}.{key}")
                errors.extend(sub_errors)
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            errors.append(f"{path}: expected array, got {type(actual).__name__}")
            return (False, errors)
        if len(expected) != len(actual):
            errors.append(
                f"{path}: array length mismatch, expected {len(expected)}, got {len(actual)}"
            )
    else:
        if expected != actual:
            errors.append(
                f"{path}: value mismatch, expected {expected!r}, got {actual!r}"
            )
    return (len(errors) == 0, errors)


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


class Contract:
    """
    Represents a Pact-style contract between a consumer and a provider.
    A contract contains one or more interactions (request/response pairs)
    that the consumer expects the provider to honour.
    """

    def __init__(
        self,
        consumer: str,
        provider: str,
        *,
        version: str = "1.0.0",
        description: str = "",
    ) -> None:
        self.contract_id: str = uuid.uuid4().hex[:12]
        self.consumer = consumer
        self.provider = provider
        self.version = version
        self.description = description
        self.interactions: List[Interaction] = []
        self.created_at: str = datetime.utcnow().isoformat()
        self.status: ContractStatus = ContractStatus.PENDING
        self.metadata: Dict[str, Any] = {}

    def add_interaction(self, interaction: Interaction) -> "Contract":
        """Add an interaction to this contract."""
        self.interactions.append(interaction)
        logger.info(
            "Added interaction '%s' to contract %s",
            interaction.description,
            self.contract_id,
        )
        return self

    def fingerprint(self) -> str:
        """Compute a deterministic fingerprint of the contract content."""
        payload = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "consumer": self.consumer,
            "provider": self.provider,
            "version": self.version,
            "description": self.description,
            "interactions": [i.to_dict() for i in self.interactions],
            "created_at": self.created_at,
            "status": self.status.value,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"Contract(id={self.contract_id}, consumer={self.consumer}, "
            f"provider={self.provider}, interactions={len(self.interactions)})"
        )


# ---------------------------------------------------------------------------
# ConsumerExpectation builder
# ---------------------------------------------------------------------------


class ConsumerExpectation:
    """
    Fluent builder for constructing contract interactions from the
    consumer's perspective.

    Usage::

        expectation = (
            ConsumerExpectation("bot_dashboard", "bot_core")
            .given("bot is in a live game")
            .upon_receiving("request for current game state")
            .with_request(HttpMethod.GET, "/api/game/state")
            .will_respond_with(200, body={"game_id": "abc", "supply": 50})
        )
        contract = expectation.build()
    """

    def __init__(self, consumer: str, provider: str) -> None:
        self._consumer = consumer
        self._provider = provider
        self._provider_state: Optional[str] = None
        self._description: str = ""
        self._request: Optional[InteractionRequest] = None
        self._response: Optional[InteractionResponse] = None
        self._interactions: List[Interaction] = []

    def given(self, state: str) -> "ConsumerExpectation":
        """Set the provider state for the next interaction."""
        self._provider_state = state
        return self

    def upon_receiving(self, description: str) -> "ConsumerExpectation":
        """Describe what the consumer expects to receive."""
        self._description = description
        return self

    def with_request(
        self,
        method: HttpMethod,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        query: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> "ConsumerExpectation":
        """Define the expected request."""
        self._request = InteractionRequest(
            method=method,
            path=path,
            headers=headers or {},
            query=query or {},
            body=body,
        )
        return self

    def will_respond_with(
        self,
        status: int,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        body_schema: Optional[Dict[str, Any]] = None,
    ) -> "ConsumerExpectation":
        """Define the expected response, finalizing the current interaction."""
        self._response = InteractionResponse(
            status=status,
            headers=headers or {},
            body=body,
            body_schema=body_schema,
        )
        if self._request is None:
            raise ValueError("Must call with_request before will_respond_with")
        interaction = Interaction(
            description=self._description,
            request=self._request,
            response=self._response,
            provider_state=self._provider_state,
        )
        self._interactions.append(interaction)
        # reset for next interaction
        self._provider_state = None
        self._description = ""
        self._request = None
        self._response = None
        return self

    def build(self) -> Contract:
        """Build the contract containing all defined interactions."""
        contract = Contract(self._consumer, self._provider)
        for interaction in self._interactions:
            contract.add_interaction(interaction)
        return contract


# ---------------------------------------------------------------------------
# ProviderVerifier
# ---------------------------------------------------------------------------


@dataclass
class VerificationResult:
    """Result of a single interaction verification."""

    interaction_desc: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class ProviderVerifier:
    """
    Verifies that a provider honours the contracts defined by consumers.
    Replays each interaction against a provider handler and checks responses.
    """

    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name
        self._state_handlers: Dict[str, Callable[[], None]] = {}
        self._request_handler: Optional[
            Callable[[InteractionRequest], InteractionResponse]
        ] = None
        self._results: List[VerificationResult] = []

    def set_state_handler(self, state: str, handler: Callable[[], None]) -> None:
        """Register a handler that sets up the provider into a given state."""
        self._state_handlers[state] = handler

    def set_request_handler(
        self,
        handler: Callable[[InteractionRequest], InteractionResponse],
    ) -> None:
        """Register the function that processes requests and returns responses."""
        self._request_handler = handler

    def verify(self, contract: Contract) -> Tuple[bool, List[VerificationResult]]:
        """
        Verify all interactions in the given contract.
        Returns (all_passed, list_of_results).
        """
        if self._request_handler is None:
            raise RuntimeError(
                "No request handler registered. Call set_request_handler first."
            )

        self._results = []
        all_passed = True

        for interaction in contract.interactions:
            start = time.time()

            # set up provider state
            if (
                interaction.provider_state
                and interaction.provider_state in self._state_handlers
            ):
                try:
                    self._state_handlers[interaction.provider_state]()
                except Exception as exc:
                    result = VerificationResult(
                        interaction_desc=interaction.description,
                        passed=False,
                        errors=[f"State setup failed: {exc}"],
                        duration_ms=(time.time() - start) * 1000,
                    )
                    self._results.append(result)
                    all_passed = False
                    continue

            # replay request
            try:
                actual_response = self._request_handler(interaction.request)
            except Exception as exc:
                result = VerificationResult(
                    interaction_desc=interaction.description,
                    passed=False,
                    errors=[f"Request handler raised: {exc}"],
                    duration_ms=(time.time() - start) * 1000,
                )
                self._results.append(result)
                all_passed = False
                continue

            # compare responses
            passed, errors = interaction.response.matches(actual_response)
            elapsed = (time.time() - start) * 1000
            result = VerificationResult(
                interaction_desc=interaction.description,
                passed=passed,
                errors=errors,
                duration_ms=elapsed,
            )
            self._results.append(result)
            if not passed:
                all_passed = False

        contract.status = (
            ContractStatus.VERIFIED if all_passed else ContractStatus.FAILED
        )
        logger.info(
            "Verification of contract %s: %s (%d/%d passed)",
            contract.contract_id,
            "PASSED" if all_passed else "FAILED",
            sum(1 for r in self._results if r.passed),
            len(self._results),
        )
        return (all_passed, self._results)

    @property
    def results(self) -> List[VerificationResult]:
        return list(self._results)


# ---------------------------------------------------------------------------
# PactBroker (in-memory registry)
# ---------------------------------------------------------------------------


class PactBroker:
    """
    In-memory Pact broker that stores and retrieves contracts.
    Supports publishing, tagging, and querying contracts between services.
    """

    def __init__(self) -> None:
        self._contracts: Dict[str, Contract] = {}
        self._tags: Dict[str, List[str]] = {}  # contract_id -> tags
        self._verification_log: List[Dict[str, Any]] = []

    def publish(self, contract: Contract, tags: Optional[List[str]] = None) -> str:
        """Publish a contract to the broker. Returns the contract id."""
        self._contracts[contract.contract_id] = contract
        self._tags[contract.contract_id] = tags or []
        logger.info(
            "Published contract %s (%s -> %s) with tags %s",
            contract.contract_id,
            contract.consumer,
            contract.provider,
            tags or [],
        )
        return contract.contract_id

    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """Retrieve a contract by id."""
        return self._contracts.get(contract_id)

    def find_contracts(
        self,
        *,
        consumer: Optional[str] = None,
        provider: Optional[str] = None,
        tag: Optional[str] = None,
        status: Optional[ContractStatus] = None,
    ) -> List[Contract]:
        """Find contracts matching the given filters."""
        results: List[Contract] = []
        for cid, contract in self._contracts.items():
            if consumer is not None and contract.consumer != consumer:
                continue
            if provider is not None and contract.provider != provider:
                continue
            if tag is not None and tag not in self._tags.get(cid, []):
                continue
            if status is not None and contract.status != status:
                continue
            results.append(contract)
        return results

    def record_verification(
        self,
        contract_id: str,
        passed: bool,
        results: List[VerificationResult],
    ) -> None:
        """Log a verification event."""
        self._verification_log.append(
            {
                "contract_id": contract_id,
                "passed": passed,
                "timestamp": datetime.utcnow().isoformat(),
                "results_count": len(results),
                "failures": [r.interaction_desc for r in results if not r.passed],
            }
        )

    def get_verification_history(self, contract_id: str) -> List[Dict[str, Any]]:
        """Get all verification events for a contract."""
        return [v for v in self._verification_log if v["contract_id"] == contract_id]

    @property
    def all_contracts(self) -> List[Contract]:
        return list(self._contracts.values())

    def summary(self) -> Dict[str, Any]:
        """Summary statistics of the broker contents."""
        statuses = {}
        for c in self._contracts.values():
            statuses[c.status.value] = statuses.get(c.status.value, 0) + 1
        return {
            "total_contracts": len(self._contracts),
            "total_verifications": len(self._verification_log),
            "by_status": statuses,
        }


# ---------------------------------------------------------------------------
# ContractTester  (orchestrator)
# ---------------------------------------------------------------------------


class ContractTester:
    """
    High-level orchestrator for SC2 service contract testing.
    Coordinates consumer expectation building, contract publishing,
    provider verification, and result reporting.
    """

    def __init__(self) -> None:
        self.broker = PactBroker()
        self._verifiers: Dict[str, ProviderVerifier] = {}
        self._report: List[Dict[str, Any]] = []

    def register_verifier(self, provider_name: str, verifier: ProviderVerifier) -> None:
        """Register a provider verifier."""
        self._verifiers[provider_name] = verifier

    def publish_contract(
        self, contract: Contract, tags: Optional[List[str]] = None
    ) -> str:
        """Publish a contract to the internal broker."""
        return self.broker.publish(contract, tags=tags)

    def verify_contract(
        self, contract: Contract
    ) -> Tuple[bool, List[VerificationResult]]:
        """Verify a contract using the registered provider verifier."""
        verifier = self._verifiers.get(contract.provider)
        if verifier is None:
            raise ValueError(
                f"No verifier registered for provider '{contract.provider}'"
            )
        passed, results = verifier.verify(contract)
        self.broker.record_verification(contract.contract_id, passed, results)
        self._report.append(
            {
                "contract_id": contract.contract_id,
                "consumer": contract.consumer,
                "provider": contract.provider,
                "passed": passed,
                "total_interactions": len(results),
                "failures": sum(1 for r in results if not r.passed),
            }
        )
        return (passed, results)

    def verify_all(self) -> Dict[str, Any]:
        """Verify every contract in the broker."""
        total = 0
        passed_count = 0
        failed_count = 0
        skipped = 0

        for contract in self.broker.all_contracts:
            if contract.provider not in self._verifiers:
                skipped += 1
                continue
            total += 1
            passed, _ = self.verify_contract(contract)
            if passed:
                passed_count += 1
            else:
                failed_count += 1

        return {
            "total_verified": total,
            "passed": passed_count,
            "failed": failed_count,
            "skipped": skipped,
        }

    def report(self) -> List[Dict[str, Any]]:
        """Return the verification report."""
        return list(self._report)

    def print_report(self) -> None:
        """Print a human-readable verification report."""
        print("\n===== SC2 Contract Test Report =====")
        for entry in self._report:
            status = "PASS" if entry["passed"] else "FAIL"
            print(
                f"  [{status}] {entry['consumer']} -> {entry['provider']} "
                f"({entry['total_interactions']} interactions, "
                f"{entry['failures']} failures)"
            )
        summary = self.broker.summary()
        print(
            f"\nBroker: {summary['total_contracts']} contracts, "
            f"{summary['total_verifications']} verifications"
        )
        print("====================================\n")


# ---------------------------------------------------------------------------
# SC2-Specific contract helpers
# ---------------------------------------------------------------------------


def build_bot_core_game_state_contract() -> Contract:
    """
    Consumer-driven contract: Dashboard expects bot core to return game state.
    """
    return (
        ConsumerExpectation("sc2_dashboard", "sc2_bot_core")
        .given("bot is in an active game")
        .upon_receiving("request for current game state")
        .with_request(HttpMethod.GET, "/api/game/state")
        .will_respond_with(
            200,
            headers={"Content-Type": "application/json"},
            body_schema={
                "type": "object",
                "required": [
                    "game_id",
                    "frame",
                    "minerals",
                    "vespene",
                    "supply_used",
                    "supply_cap",
                ],
                "properties": {
                    "game_id": {"type": "string", "minLength": 1},
                    "frame": {"type": "integer", "minimum": 0},
                    "minerals": {"type": "integer", "minimum": 0},
                    "vespene": {"type": "integer", "minimum": 0},
                    "supply_used": {"type": "integer", "minimum": 0},
                    "supply_cap": {"type": "integer", "minimum": 0, "maximum": 200},
                    "units": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["unit_id", "type_name"],
                            "properties": {
                                "unit_id": {"type": "integer"},
                                "type_name": {"type": "string"},
                            },
                        },
                    },
                },
            },
        )
        .build()
    )


def build_training_service_contract() -> Contract:
    """
    Consumer-driven contract: Bot core expects training service to accept
    replay data and return training metrics.
    """
    return (
        ConsumerExpectation("sc2_bot_core", "sc2_training_service")
        .given("training service is idle")
        .upon_receiving("submit replay for training")
        .with_request(
            HttpMethod.POST,
            "/api/training/submit",
            headers={"Content-Type": "application/json"},
            body={
                "replay_id": "replay_001",
                "replay_path": "/replays/game_001.SC2Replay",
                "race": "Zerg",
                "result": "Victory",
            },
        )
        .will_respond_with(
            202,
            body_schema={
                "type": "object",
                "required": ["job_id", "status"],
                "properties": {
                    "job_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["queued", "processing"]},
                    "estimated_seconds": {"type": "number", "minimum": 0},
                },
            },
        )
        .given("a training job has completed")
        .upon_receiving("request for training results")
        .with_request(
            HttpMethod.GET,
            "/api/training/results",
            query={"job_id": "job_abc123"},
        )
        .will_respond_with(
            200,
            body_schema={
                "type": "object",
                "required": ["job_id", "status", "metrics"],
                "properties": {
                    "job_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["completed"]},
                    "metrics": {
                        "type": "object",
                        "required": ["win_rate", "avg_reward"],
                        "properties": {
                            "win_rate": {"type": "number", "minimum": 0, "maximum": 1},
                            "avg_reward": {"type": "number"},
                            "episodes": {"type": "integer", "minimum": 1},
                        },
                    },
                },
            },
        )
        .build()
    )


def build_dashboard_build_order_contract() -> Contract:
    """
    Consumer-driven contract: Dashboard expects bot core to return
    available build orders.
    """
    return (
        ConsumerExpectation("sc2_dashboard", "sc2_bot_core")
        .given("bot has registered build orders")
        .upon_receiving("request for list of build orders")
        .with_request(HttpMethod.GET, "/api/build-orders", query={"race": "Zerg"})
        .will_respond_with(
            200,
            body_schema={
                "type": "object",
                "required": ["build_orders"],
                "properties": {
                    "build_orders": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "race", "steps"],
                            "properties": {
                                "name": {"type": "string"},
                                "race": {
                                    "type": "string",
                                    "enum": ["Zerg", "Terran", "Protoss"],
                                },
                                "win_rate": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                                "steps": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "required": ["supply", "action"],
                                        "properties": {
                                            "supply": {"type": "integer"},
                                            "action": {"type": "string"},
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        )
        .build()
    )


# ---------------------------------------------------------------------------
# Simulated provider handlers for demo
# ---------------------------------------------------------------------------


def _make_bot_core_handler() -> Callable[[InteractionRequest], InteractionResponse]:
    """Create a simulated bot core provider handler."""

    def handler(req: InteractionRequest) -> InteractionResponse:
        if req.path == "/api/game/state" and req.method == HttpMethod.GET:
            return InteractionResponse(
                status=200,
                headers={"Content-Type": "application/json"},
                body={
                    "game_id": "game_42",
                    "frame": 3500,
                    "minerals": 450,
                    "vespene": 200,
                    "supply_used": 78,
                    "supply_cap": 100,
                    "units": [
                        {"unit_id": 1, "type_name": "Zergling"},
                        {"unit_id": 2, "type_name": "Roach"},
                    ],
                },
            )
        if req.path == "/api/build-orders" and req.method == HttpMethod.GET:
            return InteractionResponse(
                status=200,
                headers={"Content-Type": "application/json"},
                body={
                    "build_orders": [
                        {
                            "name": "ZvP Roach Ravager",
                            "race": "Zerg",
                            "win_rate": 0.62,
                            "steps": [
                                {"supply": 13, "action": "Overlord"},
                                {"supply": 17, "action": "Hatchery"},
                                {"supply": 18, "action": "Extractor"},
                                {"supply": 19, "action": "Spawning Pool"},
                            ],
                        }
                    ],
                },
            )
        return InteractionResponse(status=404, body={"error": "not found"})

    return handler


def _make_training_service_handler() -> (
    Callable[[InteractionRequest], InteractionResponse]
):
    """Create a simulated training service provider handler."""

    def handler(req: InteractionRequest) -> InteractionResponse:
        if req.path == "/api/training/submit" and req.method == HttpMethod.POST:
            return InteractionResponse(
                status=202,
                body={
                    "job_id": "job_abc123",
                    "status": "queued",
                    "estimated_seconds": 120.0,
                },
            )
        if req.path == "/api/training/results" and req.method == HttpMethod.GET:
            return InteractionResponse(
                status=200,
                body={
                    "job_id": "job_abc123",
                    "status": "completed",
                    "metrics": {
                        "win_rate": 0.72,
                        "avg_reward": 15.4,
                        "episodes": 500,
                    },
                },
            )
        return InteractionResponse(status=404, body={"error": "not found"})

    return handler


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate contract testing for SC2 microservices."""
    print("=" * 60)
    print("Phase 656: Contract Testing for SC2 Microservices - Demo")
    print("=" * 60)

    tester = ContractTester()

    # --- Build contracts ---
    print("\n[1] Building consumer-driven contracts...")
    game_state_contract = build_bot_core_game_state_contract()
    training_contract = build_training_service_contract()
    build_order_contract = build_dashboard_build_order_contract()

    print(f"  - Game state contract: {game_state_contract}")
    print(f"  - Training contract:   {training_contract}")
    print(f"  - Build order contract:{build_order_contract}")

    # --- Publish contracts ---
    print("\n[2] Publishing contracts to broker...")
    tester.publish_contract(game_state_contract, tags=["dashboard", "v2"])
    tester.publish_contract(training_contract, tags=["core", "training"])
    tester.publish_contract(build_order_contract, tags=["dashboard", "v2"])

    broker_summary = tester.broker.summary()
    print(f"  Broker summary: {broker_summary}")

    # --- Register provider verifiers ---
    print("\n[3] Registering provider verifiers...")

    bot_core_verifier = ProviderVerifier("sc2_bot_core")
    bot_core_verifier.set_request_handler(_make_bot_core_handler())
    bot_core_verifier.set_state_handler("bot is in an active game", lambda: None)
    bot_core_verifier.set_state_handler("bot has registered build orders", lambda: None)
    tester.register_verifier("sc2_bot_core", bot_core_verifier)

    training_verifier = ProviderVerifier("sc2_training_service")
    training_verifier.set_request_handler(_make_training_service_handler())
    training_verifier.set_state_handler("training service is idle", lambda: None)
    training_verifier.set_state_handler("a training job has completed", lambda: None)
    tester.register_verifier("sc2_training_service", training_verifier)

    # --- Verify all contracts ---
    print("\n[4] Running contract verification...")
    summary = tester.verify_all()
    print(f"  Verification summary: {summary}")

    # --- Schema validation demo ---
    print("\n[5] Standalone schema validation demo...")
    sample_data = {
        "game_id": "game_99",
        "frame": 5000,
        "minerals": 800,
        "vespene": 300,
        "supply_used": 120,
        "supply_cap": 200,
    }
    schema = {
        "type": "object",
        "required": ["game_id", "frame", "minerals"],
        "properties": {
            "game_id": {"type": "string", "minLength": 1},
            "frame": {"type": "integer", "minimum": 0},
            "minerals": {"type": "integer", "minimum": 0},
            "supply_cap": {"type": "integer", "maximum": 200},
        },
    }
    valid, errors = validate_schema(sample_data, schema)
    print(f"  Schema validation: valid={valid}, errors={errors}")

    # Invalid data
    bad_data = {"game_id": "", "frame": -1, "minerals": "not_a_number"}
    valid2, errors2 = validate_schema(bad_data, schema)
    print(f"  Bad data validation: valid={valid2}, errors={errors2}")

    # --- Report ---
    tester.print_report()

    # --- Find contracts by filter ---
    print("[6] Querying contracts from broker...")
    dashboard_contracts = tester.broker.find_contracts(consumer="sc2_dashboard")
    print(f"  Dashboard contracts: {len(dashboard_contracts)}")
    verified = tester.broker.find_contracts(status=ContractStatus.VERIFIED)
    print(f"  Verified contracts:  {len(verified)}")

    print("\nPhase 656 demo complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()

# Phase 656: Contract Testing registered
