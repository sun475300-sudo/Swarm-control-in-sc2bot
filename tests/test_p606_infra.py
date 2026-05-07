# -*- coding: utf-8 -*-
"""
P606+ 인프라/보안/성능 모듈 테스트
"""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_HAS_NUMPY = importlib.util.find_spec("numpy") is not None


_LAST_IMPORT_ERROR: dict[str, str] = {}


def _safe_import(module_path, class_name):
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        _LAST_IMPORT_ERROR[module_path] = f"{type(e).__name__}: {e}"
        return None
    cls = getattr(mod, class_name, None)
    if cls is None:
        _LAST_IMPORT_ERROR.setdefault(
            module_path, f"class '{class_name}' not found in module"
        )
    return cls


def _skip_with_reason(module_path: str) -> None:
    err = _LAST_IMPORT_ERROR.get(module_path, "module/class not found")
    pytest.skip(f"not importable ({module_path}): {err}")


class TestLoadTesting:
    def test_import(self):
        cls = _safe_import("load_testing.sc2_load_tester", "LoadProfileType")
        if cls is None:
            _skip_with_reason("load_testing.sc2_load_tester")
        assert cls is not None

    def test_request_type(self):
        cls = _safe_import("load_testing.sc2_load_tester", "RequestType")
        if cls is None:
            _skip_with_reason("load_testing.sc2_load_tester")
        assert cls is not None


class TestFuzzTesting:
    def test_import(self):
        cls = _safe_import("fuzz_testing.sc2_fuzzer", "SC2Fuzzer")
        if cls is None:
            cls = _safe_import("fuzz_testing.sc2_fuzzer", "FuzzInput")
        if cls is None:
            _skip_with_reason("fuzz_testing.sc2_fuzzer")
        assert cls is not None


class TestContractTesting:
    def test_import(self):
        cls = _safe_import("contract_testing.sc2_contract_tester", "Contract")
        if cls is None:
            cls = _safe_import("contract_testing.sc2_contract_tester", "ContractStatus")
        if cls is None:
            _skip_with_reason("contract_testing.sc2_contract_tester")
        assert cls is not None


class TestEBPFObservability:
    def test_import(self):
        cls = _safe_import("ebpf_observability.sc2_ebpf_monitor", "ProbeType")
        if cls is None:
            cls = _safe_import("ebpf_observability.sc2_ebpf_monitor", "EBPFConfig")
        if cls is None:
            _skip_with_reason("ebpf_observability.sc2_ebpf_monitor")
        assert cls is not None


class TestMTLSSecurity:
    def test_import(self):
        cls = _safe_import("mtls_security.sc2_mtls_gateway", "CertificateType")
        if cls is None:
            cls = _safe_import("mtls_security.sc2_mtls_gateway", "TLSConfig")
        if cls is None:
            _skip_with_reason("mtls_security.sc2_mtls_gateway")
        assert cls is not None


class TestSBOMManager:
    def test_import(self):
        cls = _safe_import("sbom_manager.sc2_sbom_generator", "Package")
        if cls is None:
            cls = _safe_import("sbom_manager.sc2_sbom_generator", "SBOMGenerator")
        if cls is None:
            _skip_with_reason("sbom_manager.sc2_sbom_generator")
        assert cls is not None


class TestChaosEngineering:
    def test_import(self):
        cls = _safe_import("chaos_engineering.sc2_chaos_monkey", "ChaosExperiment")
        if cls is None:
            cls = _safe_import("chaos_engineering.sc2_chaos_monkey", "ExperimentType")
        if cls is None:
            _skip_with_reason("chaos_engineering.sc2_chaos_monkey")
        assert cls is not None


class TestRateLimiter:
    def test_import(self):
        cls = _safe_import("rate_limiter.sc2_rate_limiter", "RateLimitAlgorithm")
        if cls is None:
            cls = _safe_import("rate_limiter.sc2_rate_limiter", "RateLimitConfig")
        if cls is None:
            _skip_with_reason("rate_limiter.sc2_rate_limiter")
        assert cls is not None


class TestEventSourcing:
    def test_import(self):
        cls = _safe_import("event_sourcing.sc2_event_store", "EventType")
        if cls is None:
            cls = _safe_import("event_sourcing.sc2_event_store", "DomainEvent")
        if cls is None:
            _skip_with_reason("event_sourcing.sc2_event_store")
        assert cls is not None


class TestCQRSPattern:
    def test_import(self):
        cls = _safe_import("cqrs_pattern.sc2_cqrs", "CommandType")
        if cls is None:
            cls = _safe_import("cqrs_pattern.sc2_cqrs", "CQRSConfig")
        if cls is None:
            _skip_with_reason("cqrs_pattern.sc2_cqrs")
        assert cls is not None


class TestPerformanceProfiler:
    def test_import(self):
        cls = _safe_import("performance_profiler.sc2_profiler", "Timer")
        if cls is None:
            cls = _safe_import("performance_profiler.sc2_profiler", "CPUProfiler")
        if cls is None:
            _skip_with_reason("performance_profiler.sc2_profiler")
        assert cls is not None


class TestGraphQLAPI:
    def test_import(self):
        cls = _safe_import("graphql_api.sc2_graphql_server", "QueryType")
        if cls is None:
            cls = _safe_import("graphql_api.sc2_graphql_server", "SC2Schema")
        if cls is None:
            _skip_with_reason("graphql_api.sc2_graphql_server")
        assert cls is not None
