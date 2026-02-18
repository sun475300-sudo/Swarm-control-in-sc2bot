#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manager Factory - 중앙화된 매니저 초기화 시스템

650줄의 중복 초기화 코드를 간결한 factory pattern으로 변경:
- 의존성 그래프 자동 관리
- 명확한 에러 보고
- 초기화 순서 보장
- 실패한 매니저 추적
"""

from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass
from enum import IntEnum
import importlib


class ManagerPriority(IntEnum):
    """매니저 초기화 우선순위"""
    CRITICAL = 0      # 필수 시스템 (실패 시 봇 중단)
    HIGH = 10         # 핵심 시스템
    MEDIUM = 20       # 일반 시스템
    LOW = 30          # 선택적 시스템
    OPTIONAL = 40     # 완전 선택적


@dataclass
class ManagerConfig:
    """매니저 설정"""
    name: str                           # 표시 이름
    module_path: str                    # import 경로
    class_name: str                     # 클래스 이름
    attribute_name: str                 # bot 속성 이름
    priority: ManagerPriority           # 우선순위
    dependencies: List[str] = None      # 의존 매니저 (attribute_name)
    init_args: Dict[str, Any] = None    # 추가 초기화 인자
    post_init: Optional[Callable] = None  # 초기화 후 실행 함수
    enabled: bool = True                # 활성화 여부

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.init_args is None:
            self.init_args = {}


class ManagerFactory:
    """
    매니저 초기화 Factory

    사용법:
        factory = ManagerFactory(bot)
        factory.register_manager(...)
        factory.initialize_all()
    """

    def __init__(self, bot):
        self.bot = bot
        self.managers: Dict[str, ManagerConfig] = {}
        self.initialized: Set[str] = set()
        self.failed: Dict[str, str] = {}  # attribute_name -> error_msg
        self.initialization_order: List[str] = []

    def register_manager(self, config: ManagerConfig) -> None:
        """
        매니저 등록

        Args:
            config: 매니저 설정
        """
        self.managers[config.attribute_name] = config

    def register_managers(self, configs: List[ManagerConfig]) -> None:
        """
        여러 매니저 일괄 등록

        Args:
            configs: 매니저 설정 리스트
        """
        for config in configs:
            self.register_manager(config)

    def initialize_all(self, verbose: bool = True) -> Dict[str, Any]:
        """
        모든 매니저 초기화 (의존성 순서 보장)

        Args:
            verbose: 상세 로그 출력 여부

        Returns:
            초기화 결과 통계
        """
        # 1. 우선순위 정렬
        sorted_managers = sorted(
            self.managers.values(),
            key=lambda m: (m.priority, m.name)
        )

        # 2. 초기화 실행
        for config in sorted_managers:
            if not config.enabled:
                continue

            self._initialize_manager(config, verbose)

        # 3. 결과 보고
        stats = self._get_statistics()

        if verbose:
            self._print_summary(stats)

        return stats

    def _initialize_manager(self, config: ManagerConfig, verbose: bool) -> bool:
        """
        단일 매니저 초기화

        Args:
            config: 매니저 설정
            verbose: 로그 출력 여부

        Returns:
            성공 여부
        """
        attr_name = config.attribute_name

        # 이미 초기화되었으면 스킵
        if attr_name in self.initialized:
            return True

        # 의존성 확인
        for dep in config.dependencies:
            if dep not in self.initialized:
                # 의존성이 실패했으면 현재 매니저도 실패
                if dep in self.failed:
                    self.failed[attr_name] = f"Dependency failed: {dep}"
                    setattr(self.bot, attr_name, None)
                    return False

                # 의존성을 먼저 초기화
                dep_config = self.managers.get(dep)
                if dep_config:
                    self._initialize_manager(dep_config, verbose)

        # 매니저 초기화 시도
        try:
            # 1. 모듈 import
            module = importlib.import_module(config.module_path)
            manager_class = getattr(module, config.class_name)

            # 2. 인스턴스 생성
            init_kwargs = {}

            # 특별한 경우 처리
            if config.attribute_name == "formation_controller":
                # FormationController는 bot 인자를 받지 않음
                pass
            elif config.attribute_name == "opponent_modeling":
                # OpponentModeling은 bot과 intel_manager를 인자로 받음
                init_kwargs["bot"] = self.bot
                intel = getattr(self.bot, "intel", None)
                init_kwargs["intel_manager"] = intel
            else:
                # 일반적인 경우: bot 인자 전달
                init_kwargs["bot"] = self.bot

            # 추가 인자 병합
            init_kwargs.update(config.init_args)

            manager_instance = manager_class(**init_kwargs)

            # 3. bot 속성에 설정
            setattr(self.bot, attr_name, manager_instance)

            # 4. post_init 실행
            if config.post_init:
                config.post_init(self.bot, manager_instance)

            # 5. 성공 기록
            self.initialized.add(attr_name)
            self.initialization_order.append(attr_name)

            # 6. 로그 출력
            if verbose:
                star = "★ " if "NEW" in config.name or "Advanced" in config.name else ""
                print(f"[BOT] {star}{config.name} initialized")

            return True

        except ImportError as e:
            # Import 실패
            self.failed[attr_name] = f"ImportError: {e}"
            setattr(self.bot, attr_name, None)

            if verbose:
                print(f"[BOT_WARN] {config.name} not available: {e}")

            return False

        except Exception as e:
            # 기타 초기화 실패
            self.failed[attr_name] = f"InitError: {e}"
            setattr(self.bot, attr_name, None)

            if verbose:
                print(f"[BOT_ERROR] {config.name} initialization failed: {e}")

            return False

    def _get_statistics(self) -> Dict[str, Any]:
        """초기화 통계 반환"""
        total = len([m for m in self.managers.values() if m.enabled])
        succeeded = len(self.initialized)
        failed = len(self.failed)

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "success_rate": succeeded / total * 100 if total > 0 else 0,
            "failed_managers": list(self.failed.keys()),
            "initialization_order": self.initialization_order
        }

    def _print_summary(self, stats: Dict[str, Any]) -> None:
        """초기화 결과 요약 출력"""
        print("\n" + "="*70)
        print("MANAGER INITIALIZATION SUMMARY")
        print("="*70)
        print(f"Total Managers: {stats['total']}")
        print(f"Succeeded: {stats['succeeded']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")

        if stats['failed_managers']:
            print(f"\nFailed Managers ({len(stats['failed_managers'])}):")
            for attr_name in stats['failed_managers']:
                error = self.failed[attr_name]
                print(f"  - {attr_name}: {error}")

        print("="*70 + "\n")

    def get_manager(self, attribute_name: str) -> Optional[Any]:
        """
        초기화된 매니저 가져오기

        Args:
            attribute_name: 매니저 속성 이름

        Returns:
            매니저 인스턴스 또는 None
        """
        if attribute_name in self.initialized:
            return getattr(self.bot, attribute_name, None)
        return None

    def is_initialized(self, attribute_name: str) -> bool:
        """
        매니저 초기화 여부 확인

        Args:
            attribute_name: 매니저 속성 이름

        Returns:
            초기화 여부
        """
        return attribute_name in self.initialized

    def get_failed_reason(self, attribute_name: str) -> Optional[str]:
        """
        매니저 실패 이유 반환

        Args:
            attribute_name: 매니저 속성 이름

        Returns:
            실패 이유 또는 None
        """
        return self.failed.get(attribute_name)
