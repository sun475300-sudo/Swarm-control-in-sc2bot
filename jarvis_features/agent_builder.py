# -*- coding: utf-8 -*-
"""
Agent Builder - 에이전트 정의 생성 팩토리

claude_skills의 meta-prompting 패턴 적용:
- 대화를 통해 새 에이전트 정의(.md)를 자동 생성
- 기존 에이전트 정의를 참조하여 일관된 포맷 유지
- 파이프라인 스텝, 키워드, 도구 매핑을 자동 구성

사용법:
    builder = AgentBuilder()

    # 에이전트 정의 생성
    definition = builder.build(
        name="stock-analyzer",
        description="주식 분석 에이전트",
        domain="finance",
        tools=["stock_price", "chart_analysis"],
        pipeline=["data-fetch", "analysis", "report"],
    )

    # .md 파일로 저장
    builder.save(definition, "jarvis_features/agent_definitions/")
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("jarvis.agent_builder")

# 기본 에이전트 정의 디렉토리
AGENT_DEFINITIONS_DIR = os.path.join(
    os.path.dirname(__file__), "agent_definitions"
)

# 모델 옵션
VALID_MODELS = ["haiku", "sonnet", "opus"]

# 컬러 옵션
VALID_COLORS = [
    "red", "green", "blue", "orange", "purple", "yellow", "cyan", "grey",
]


@dataclass
class PipelineStepDef:
    """파이프라인 스텝 정의"""
    name: str
    source: str = ""        # Python 모듈.함수 경로
    timeout: int = 10
    required: bool = False


@dataclass
class AgentDefinition:
    """에이전트 정의 구조체"""
    name: str
    description: str
    model: str = "sonnet"
    color: str = "blue"
    memory: str = "session"  # "session" | "project" | "none"
    domain: str = ""         # AgentRouter 도메인 매핑
    tools: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    pipeline: List[PipelineStepDef] = field(default_factory=list)
    hard_rules: List[str] = field(default_factory=list)
    body_markdown: str = ""  # 추가 마크다운 본문

    def to_markdown(self) -> str:
        """에이전트 정의를 .md 파일 형식으로 변환"""
        lines = ["---"]
        lines.append(f"name: {self.name}")
        lines.append(f"description: |")
        for desc_line in self.description.strip().split("\n"):
            lines.append(f"  {desc_line}")
        lines.append(f"model: {self.model}")
        lines.append(f"color: {self.color}")
        lines.append(f"memory: {self.memory}")

        if self.domain:
            lines.append(f"domain: {self.domain}")

        if self.tools:
            lines.append("tools:")
            for tool in self.tools:
                lines.append(f"  - {tool}")

        if self.keywords:
            lines.append("keywords:")
            for kw in self.keywords:
                lines.append(f"  - {kw}")

        if self.pipeline:
            lines.append("pipeline:")
            for step in self.pipeline:
                lines.append(f"  - name: {step.name}")
                if step.source:
                    lines.append(f"    source: {step.source}")
                lines.append(f"    timeout: {step.timeout}")
                lines.append(f"    required: {'true' if step.required else 'false'}")

        lines.append("---")
        lines.append("")

        # 본문
        lines.append(f"# {self.name.replace('-', ' ').title()}")
        lines.append("")

        if self.body_markdown:
            lines.append(self.body_markdown)
        else:
            lines.append(self.description.strip())

        # 도구 섹션
        if self.tools:
            lines.append("")
            lines.append("## Available Tools")
            lines.append("")
            for tool in self.tools:
                lines.append(f"- `{tool}`")

        # 파이프라인 섹션
        if self.pipeline:
            lines.append("")
            lines.append("## Pipeline")
            lines.append("")
            lines.append("```")
            for i, step in enumerate(self.pipeline):
                prefix = "[" if i == 0 else " "
                suffix = "]" if i == len(self.pipeline) - 1 else ""
                arrow = " ──→ " if i < len(self.pipeline) - 1 else ""
                lines.append(f"[{step.name}]{arrow}")
            lines.append("```")

        # Hard Rules 섹션
        if self.hard_rules:
            lines.append("")
            lines.append("## Hard Rules")
            lines.append("")
            for i, rule in enumerate(self.hard_rules, 1):
                lines.append(f"{i}. {rule}")

        lines.append("")
        return "\n".join(lines)


class AgentBuilder:
    """
    에이전트 정의 팩토리

    meta-prompting 패턴:
    - build(): 파라미터에서 AgentDefinition 생성
    - from_template(): 기존 정의를 템플릿으로 사용
    - save(): .md 파일로 저장
    - list_definitions(): 기존 정의 목록 반환
    - generate_router_entry(): AgentRouter 키워드 엔트리 생성
    """

    def __init__(self, definitions_dir: str = ""):
        self._definitions_dir = definitions_dir or AGENT_DEFINITIONS_DIR
        self._build_count = 0

    def build(
        self,
        name: str,
        description: str,
        model: str = "sonnet",
        color: str = "blue",
        memory: str = "session",
        domain: str = "",
        tools: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        pipeline: Optional[List[dict]] = None,
        hard_rules: Optional[List[str]] = None,
        body_markdown: str = "",
    ) -> AgentDefinition:
        """
        에이전트 정의 생성.

        Args:
            name: 에이전트 이름 (케밥-케이스)
            description: 에이전트 설명
            model: LLM 모델 ("haiku", "sonnet", "opus")
            color: UI 컬러
            memory: 메모리 스코프
            domain: AgentRouter 도메인 매핑
            tools: 사용 가능 도구 목록
            keywords: 라우팅 키워드 목록
            pipeline: 파이프라인 스텝 목록 [{name, source, timeout, required}]
            hard_rules: 하드 룰 목록
            body_markdown: 추가 마크다운 본문

        Returns:
            AgentDefinition
        """
        self._build_count += 1

        # 이름 정규화 (케밥-케이스)
        name = self._normalize_name(name)

        # 모델 검증
        if model not in VALID_MODELS:
            logger.warning(f"[AGENT_BUILDER] Invalid model '{model}', defaulting to 'sonnet'")
            model = "sonnet"

        # 컬러 검증
        if color not in VALID_COLORS:
            color = "blue"

        # 파이프라인 스텝 변환
        pipeline_steps = []
        if pipeline:
            for step_data in pipeline:
                if isinstance(step_data, dict):
                    pipeline_steps.append(PipelineStepDef(
                        name=step_data.get("name", "unnamed"),
                        source=step_data.get("source", ""),
                        timeout=step_data.get("timeout", 10),
                        required=step_data.get("required", False),
                    ))
                elif isinstance(step_data, str):
                    pipeline_steps.append(PipelineStepDef(name=step_data))

        definition = AgentDefinition(
            name=name,
            description=description,
            model=model,
            color=color,
            memory=memory,
            domain=domain,
            tools=tools or [],
            keywords=keywords or [],
            pipeline=pipeline_steps,
            hard_rules=hard_rules or [],
            body_markdown=body_markdown,
        )

        logger.info(
            f"[AGENT_BUILDER] Built '{name}' (model={model}, "
            f"tools={len(definition.tools)}, pipeline={len(pipeline_steps)})"
        )

        return definition

    def from_template(
        self,
        template_name: str,
        new_name: str,
        overrides: Optional[Dict] = None,
    ) -> Optional[AgentDefinition]:
        """
        기존 에이전트 정의를 템플릿으로 새 정의 생성.

        Args:
            template_name: 템플릿 에이전트 파일명 (확장자 제외)
            new_name: 새 에이전트 이름
            overrides: 덮어쓸 필드 dict

        Returns:
            AgentDefinition 또는 None (템플릿 없음)
        """
        template_path = os.path.join(self._definitions_dir, f"{template_name}.md")
        if not os.path.exists(template_path):
            logger.warning(f"[AGENT_BUILDER] Template not found: {template_path}")
            return None

        # 템플릿 파싱
        parsed = self._parse_definition_file(template_path)
        if not parsed:
            return None

        # 오버라이드 적용
        if overrides:
            parsed.update(overrides)

        parsed["name"] = self._normalize_name(new_name)

        # build()에 허용된 키만 전달
        valid_keys = {
            "name", "description", "model", "color", "memory", "domain",
            "tools", "keywords", "pipeline", "hard_rules", "body_markdown",
        }
        filtered = {k: v for k, v in parsed.items() if k in valid_keys}

        return self.build(**filtered)

    def save(self, definition: AgentDefinition, directory: str = "") -> str:
        """
        에이전트 정의를 .md 파일로 저장.

        Args:
            definition: 저장할 에이전트 정의
            directory: 저장 디렉토리 (빈 문자열이면 기본 디렉토리)

        Returns:
            저장된 파일 경로
        """
        save_dir = directory or self._definitions_dir
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{definition.name}.md"
        filepath = os.path.join(save_dir, filename)

        content = definition.to_markdown()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[AGENT_BUILDER] Saved '{definition.name}' → {filepath}")
        return filepath

    def list_definitions(self) -> List[Dict[str, str]]:
        """기존 에이전트 정의 목록 반환"""
        if not os.path.isdir(self._definitions_dir):
            return []

        definitions = []
        for filename in sorted(os.listdir(self._definitions_dir)):
            if filename.endswith(".md"):
                filepath = os.path.join(self._definitions_dir, filename)
                parsed = self._parse_definition_file(filepath)
                if parsed:
                    definitions.append({
                        "name": parsed.get("name", filename[:-3]),
                        "description": parsed.get("description", "")[:100],
                        "model": parsed.get("model", "unknown"),
                        "file": filename,
                    })

        return definitions

    def generate_router_entry(self, definition: AgentDefinition) -> str:
        """
        AgentRouter에 추가할 키워드 엔트리 Python 코드 생성.

        Returns:
            DOMAIN_KEYWORDS 엔트리 코드 문자열
        """
        if not definition.keywords:
            return f"# {definition.name}: 키워드 없음"

        keywords_str = ", ".join(f'"{kw}"' for kw in definition.keywords)
        return (
            f'# {definition.name}\n'
            f'AgentDomain.{definition.domain.upper() if definition.domain else "GENERAL_CHAT"}: [\n'
            f'    {keywords_str},\n'
            f'],'
        )

    def _normalize_name(self, name: str) -> str:
        """이름을 케밥-케이스로 정규화"""
        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9가-힣\s-]", "", name)
        name = re.sub(r"[\s_]+", "-", name)
        name = re.sub(r"-+", "-", name).strip("-")
        return name

    def _parse_definition_file(self, filepath: str) -> Optional[Dict]:
        """에이전트 정의 .md 파일 파싱 (YAML frontmatter 추출)"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # YAML frontmatter 추출
            match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not match:
                return None

            frontmatter = match.group(1)
            result = {}

            # 간단 YAML 파싱 (PyYAML 의존성 없이)
            current_key = None
            current_list = None
            multiline_key = None  # description: | 등 멀티라인 값 수집
            multiline_lines = []

            for line in frontmatter.split("\n"):
                raw_indent = len(line) - len(line.lstrip())
                stripped = line.strip()

                # 멀티라인 값 수집 중 (들여쓰기된 줄)
                if multiline_key and raw_indent >= 2 and stripped:
                    multiline_lines.append(stripped)
                    continue
                elif multiline_key and (raw_indent < 2 or not stripped):
                    # 멀티라인 끝 → 값 저장
                    if multiline_lines:
                        result[multiline_key] = "\n".join(multiline_lines)
                    multiline_key = None
                    multiline_lines = []
                    if not stripped:
                        continue

                if not stripped or stripped.startswith("#"):
                    continue

                # 리스트 아이템 (최상위 키 아래 또는 pipeline 내부 등)
                if stripped.startswith("- ") and current_key:
                    if current_list is None:
                        current_list = []
                        result[current_key] = current_list
                    current_list.append(stripped[2:].strip())
                    continue

                # 키-값 쌍 (최상위만: 들여쓰기 없는 줄)
                if ":" in stripped and raw_indent == 0:
                    key, _, value = stripped.partition(":")
                    key = key.strip()
                    value = value.strip()

                    current_key = key
                    current_list = None

                    if value == "|":
                        # 멀티라인 시작
                        multiline_key = key
                        multiline_lines = []
                        continue

                    if value:
                        # boolean 변환
                        if value.lower() in ("true", "yes"):
                            value = True
                        elif value.lower() in ("false", "no"):
                            value = False
                        # 숫자 변환
                        elif value.isdigit():
                            value = int(value)

                        result[key] = value

            # 마지막 멀티라인 값 처리
            if multiline_key and multiline_lines:
                result[multiline_key] = "\n".join(multiline_lines)

            return result if result else None

        except Exception as e:
            logger.warning(f"[AGENT_BUILDER] Parse error {filepath}: {e}")
            return None
