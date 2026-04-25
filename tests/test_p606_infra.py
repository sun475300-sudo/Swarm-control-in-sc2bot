# -*- coding: utf-8 -*-
"""
P606+ 인프라/보안/성능 모듈 테스트

각 모듈에서 실제로 export 되는 핵심 클래스를 검증한다.
이전 버전에서는 존재하지 않는 클래스 이름을 찾아 silent skip 처리되어
실제 회귀를 잡지 못했다 (#fix-p606-infra-skip).
"""

import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _import_attrs(module_path: str, *names: str):
    """Import a module and return the requested attributes as a tuple.

    Raises ImportError so pytest reports the real failure instead of
    silently skipping (which used to mask renamed/removed symbols).
    """
    mod = importlib.import_module(module_path)
    missing = [n for n in names if not hasattr(mod, n)]
    if missing:
        raise AttributeError(
            f"{module_path} is missing expected names: {missing}. "
            f"Available: {sorted(n for n in dir(mod) if not n.startswith('_'))[:20]}"
        )
    return tuple(getattr(mod, n) for n in names)


class TestLoadTesting:
    def test_import(self):
        (cls,) = _import_attrs("load_testing.sc2_load_tester", "LoadProfileType")
        assert cls is not None

    def test_request_type(self):
        (cls,) = _import_attrs("load_testing.sc2_load_tester", "RequestType")
        assert cls is not None


class TestFuzzTesting:
    def test_import(self):
        # Real exports: FuzzInput, Mutator, SC2Fuzzer, CrashReport
        fuzz_input, mutator, fuzzer = _import_attrs(
            "fuzz_testing.sc2_fuzzer", "FuzzInput", "Mutator", "SC2Fuzzer"
        )
        assert fuzz_input is not None
        assert mutator is not None
        assert fuzzer is not None


class TestContractTesting:
    def test_import(self):
        # Real exports: Contract, ContractStatus, ContractTester
        contract, status, tester = _import_attrs(
            "contract_testing.sc2_contract_tester",
            "Contract",
            "ContractStatus",
            "ContractTester",
        )
        assert contract is not None
        assert status is not None
        assert tester is not None


class TestEBPFObservability:
    def test_import(self):
        probe_type, monitor = _import_attrs(
            "ebpf_observability.sc2_ebpf_monitor", "ProbeType", "eBPFMonitor"
        )
        assert probe_type is not None
        assert monitor is not None


class TestMTLSSecurity:
    def test_import(self):
        tls_config, ca = _import_attrs(
            "mtls_security.sc2_mtls_gateway", "TLSConfig", "CertificateAuthority"
        )
        assert tls_config is not None
        assert ca is not None


class TestSBOMManager:
    def test_import(self):
        # Real exports: Package, SBOMDocument, SBOMGenerator, Vulnerability
        package, doc, generator = _import_attrs(
            "sbom_manager.sc2_sbom_generator",
            "Package",
            "SBOMDocument",
            "SBOMGenerator",
        )
        assert package is not None
        assert doc is not None
        assert generator is not None


class TestChaosEngineering:
    def test_import(self):
        experiment, monkey = _import_attrs(
            "chaos_engineering.sc2_chaos_monkey", "ChaosExperiment", "ChaosMonkey"
        )
        assert experiment is not None
        assert monkey is not None


class TestRateLimiter:
    def test_import(self):
        config, limiter = _import_attrs(
            "rate_limiter.sc2_rate_limiter", "RateLimitConfig", "RateLimiter"
        )
        assert config is not None
        assert limiter is not None


class TestEventSourcing:
    def test_import(self):
        event_type, event, store = _import_attrs(
            "event_sourcing.sc2_event_store", "EventType", "Event", "EventStore"
        )
        assert event_type is not None
        assert event is not None
        assert store is not None


class TestCQRSPattern:
    def test_import(self):
        cmd_type, query_type, bus = _import_attrs(
            "cqrs_pattern.sc2_cqrs", "CommandType", "QueryType", "CQRSBus"
        )
        assert cmd_type is not None
        assert query_type is not None
        assert bus is not None


class TestPerformanceProfiler:
    def test_import(self):
        # Real exports: Timer, CPUProfiler, SC2Profiler, MemoryTracker
        timer, cpu, profiler = _import_attrs(
            "performance_profiler.sc2_profiler",
            "Timer",
            "CPUProfiler",
            "SC2Profiler",
        )
        assert timer is not None
        assert cpu is not None
        assert profiler is not None


class TestGraphQLAPI:
    def test_import(self):
        schema, server = _import_attrs(
            "graphql_api.sc2_graphql_server", "SC2Schema", "GraphQLServer"
        )
        assert schema is not None
        assert server is not None
