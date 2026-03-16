# -*- coding: utf-8 -*-
"""
Workflow Orchestrator - 다단계 파이프라인 실행 엔진

claude_skills의 instagram-carousel-orchestrator 패턴 적용:
- 파이프라인 정의 (스텝 리스트)
- 순차/병렬 실행
- 스텝별 타임아웃 & 에러 핸들링
- 상태 로깅 (라운드 레이블)
- tool_registry 성공/실패 기록

사용법:
    orchestrator = WorkflowOrchestrator()

    steps = [
        PipelineStep("weather", get_weather_section, timeout=10),
        PipelineStep("calendar", get_calendar_section, timeout=15),
    ]

    # 병렬 실행
    results = await orchestrator.execute_parallel(steps)

    # 결과 조립
    output = orchestrator.format_results(results)
"""

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.orchestrator")


@dataclass
class PipelineStep:
    """파이프라인 단일 스텝 정의"""
    name: str                       # 스텝 이름 (로깅용)
    agent_fn: Callable              # 실행 함수 (sync 또는 async)
    required: bool = False          # True: 실패 시 파이프라인 중단
    timeout: float = 10.0           # 타임아웃 (초)
    retry: int = 0                  # 재시도 횟수 (0 = 재시도 없음)


@dataclass
class StepResult:
    """스텝 실행 결과"""
    step_name: str
    success: bool
    output: str
    elapsed_ms: float
    error: str = ""
    round_label: str = ""           # "[weather - Round 0]" 형태


class WorkflowOrchestrator:
    """
    워크플로우 오케스트레이터

    orchestrator 패턴:
    - execute_pipeline(): 순차 실행 (의존성 있는 스텝)
    - execute_parallel(): 병렬 실행 (독립 스텝)
    - format_results(): 결과를 포맷팅된 문자열로 조립
    """

    def __init__(self, tool_registry=None):
        self.tool_registry = tool_registry
        self._execution_count = 0

    async def execute_pipeline(
        self,
        pipeline: List[PipelineStep],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[StepResult]:
        """
        파이프라인 순차 실행.

        각 스텝의 출력이 다음 스텝의 context에 추가됩니다.
        required=True 스텝이 실패하면 파이프라인이 중단됩니다.

        Args:
            pipeline: 실행할 스텝 리스트
            context: 초기 컨텍스트 (스텝 간 공유)

        Returns:
            각 스텝의 실행 결과 리스트
        """
        if context is None:
            context = {}

        results = []
        self._execution_count += 1
        run_id = self._execution_count

        logger.info(f"[ORCHESTRATOR] Pipeline start (run #{run_id}, {len(pipeline)} steps)")

        for i, step in enumerate(pipeline):
            result = await self._execute_step(step, context, round_num=0)
            results.append(result)

            # 상태 로깅
            status = "OK" if result.success else "FAIL"
            logger.info(
                f"[ORCHESTRATOR] Step {i+1}/{len(pipeline)} [{step.name}] "
                f"{status} ({result.elapsed_ms:.0f}ms)"
            )

            # 성공 시 context에 출력 추가
            if result.success:
                context[step.name] = result.output

            # required 스텝 실패 시 중단
            if not result.success and step.required:
                logger.error(
                    f"[ORCHESTRATOR] Required step '{step.name}' failed. "
                    f"Pipeline aborted. Error: {result.error}"
                )
                break

        logger.info(
            f"[ORCHESTRATOR] Pipeline complete (run #{run_id}, "
            f"{sum(1 for r in results if r.success)}/{len(results)} succeeded)"
        )
        return results

    async def execute_parallel(
        self,
        steps: List[PipelineStep],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[StepResult]:
        """
        독립 스텝 병렬 실행 (asyncio.gather).

        모든 스텝이 동시에 시작되므로, 가장 느린 스텝이 전체 시간을 결정합니다.

        Args:
            steps: 실행할 스텝 리스트 (순서 무관)
            context: 공유 컨텍스트

        Returns:
            각 스텝의 실행 결과 리스트 (입력 순서 유지)
        """
        if context is None:
            context = {}

        self._execution_count += 1
        run_id = self._execution_count

        logger.info(f"[ORCHESTRATOR] Parallel start (run #{run_id}, {len(steps)} steps)")

        start_all = time.perf_counter()

        # 모든 스텝을 동시 실행
        tasks = [self._execute_step(step, context, round_num=0) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        total_ms = (time.perf_counter() - start_all) * 1000
        succeeded = sum(1 for r in results if r.success)

        logger.info(
            f"[ORCHESTRATOR] Parallel complete (run #{run_id}, "
            f"{succeeded}/{len(results)} succeeded, {total_ms:.0f}ms total)"
        )

        # tool_registry에 전체 파이프라인 기록
        if self.tool_registry:
            try:
                self.tool_registry.record_call(
                    "orchestrator_parallel", "", succeeded == len(results),
                    total_ms, "" if succeeded == len(results) else "partial_failure",
                )
            except Exception:
                pass

        return list(results)

    async def _execute_step(
        self, step: PipelineStep, context: Dict, round_num: int = 0,
    ) -> StepResult:
        """단일 스텝 실행 (타임아웃 + 재시도)"""
        attempts = 1 + step.retry
        last_error = ""

        for attempt in range(attempts):
            start = time.perf_counter()
            try:
                output = await self._run_with_timeout(step.agent_fn, step.timeout)
                elapsed_ms = (time.perf_counter() - start) * 1000

                result = StepResult(
                    step_name=step.name,
                    success=True,
                    output=str(output) if output else "",
                    elapsed_ms=elapsed_ms,
                    round_label=f"[{step.name.upper()} - Round {round_num}]",
                )

                # tool_registry 기록
                if self.tool_registry:
                    try:
                        self.tool_registry.record_call(
                            f"orchestrator.{step.name}", "", True, elapsed_ms, "",
                        )
                    except Exception:
                        pass

                return result

            except asyncio.TimeoutError:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = f"Timeout ({step.timeout}s)"
                logger.warning(
                    f"[ORCHESTRATOR] Step '{step.name}' timeout "
                    f"(attempt {attempt+1}/{attempts})"
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = str(e)
                logger.warning(
                    f"[ORCHESTRATOR] Step '{step.name}' error: {e} "
                    f"(attempt {attempt+1}/{attempts})"
                )

            # 재시도 간 짧은 대기
            if attempt < attempts - 1:
                await asyncio.sleep(0.5)

        # 모든 시도 실패
        elapsed_ms = (time.perf_counter() - start) * 1000

        # tool_registry 실패 기록
        if self.tool_registry:
            try:
                self.tool_registry.record_call(
                    f"orchestrator.{step.name}", "", False, elapsed_ms, last_error,
                )
            except Exception:
                pass

        return StepResult(
            step_name=step.name,
            success=False,
            output="",
            elapsed_ms=elapsed_ms,
            error=last_error,
            round_label=f"[{step.name.upper()} - Round {round_num} FAILED]",
        )

    async def _run_with_timeout(self, fn: Callable, timeout: float) -> Any:
        """함수 실행 (sync/async 자동 판별 + 타임아웃)"""
        if inspect.iscoroutinefunction(fn):
            return await asyncio.wait_for(fn(), timeout=timeout)
        else:
            # sync 함수를 executor에서 실행
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, fn), timeout=timeout,
            )

    def format_results(
        self,
        results: List[StepResult],
        template: str = "",
        separator: str = "\n\n",
        include_failed: bool = True,
    ) -> str:
        """
        결과를 포맷팅된 문자열로 조립.

        Args:
            results: 스텝 결과 리스트
            template: 헤더/푸터 포함 템플릿 (빈 문자열이면 기본)
            separator: 섹션 구분자
            include_failed: 실패 섹션도 포함할지

        Returns:
            조립된 문자열
        """
        sections = []
        for r in results:
            if r.success and r.output:
                sections.append(r.output)
            elif include_failed and r.error:
                sections.append(f"[{r.step_name}] 정보를 가져올 수 없습니다: {r.error}")

        body = separator.join(sections)

        if template:
            return template.replace("{body}", body)

        return body

    def get_execution_report(self, results: List[StepResult]) -> str:
        """실행 보고서 생성 (디버깅/로깅용)"""
        lines = ["[Orchestrator Report]"]
        total_ms = sum(r.elapsed_ms for r in results)

        for r in results:
            status = "OK" if r.success else "FAIL"
            lines.append(
                f"  {r.step_name}: {status} ({r.elapsed_ms:.0f}ms)"
                + (f" - {r.error}" if r.error else "")
            )

        succeeded = sum(1 for r in results if r.success)
        lines.append(f"  Total: {succeeded}/{len(results)} succeeded ({total_ms:.0f}ms)")
        return "\n".join(lines)
