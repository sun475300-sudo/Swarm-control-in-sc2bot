# -*- coding: utf-8 -*-
"""AgentBuilder 단위 테스트 — 빌드, 정규화, YAML frontmatter, 카운터."""

import pytest

from jarvis_features.agent_builder import AgentBuilder, AgentDefinition, VALID_MODELS


class TestBuildValidatesModel:
    def test_invalid_model_falls_back_to_sonnet(self):
        builder = AgentBuilder()
        definition = builder.build(name="test-agent", description="테스트", model="gpt-5")
        assert definition.model == "sonnet"

    def test_valid_model_accepted(self):
        builder = AgentBuilder()
        for model in VALID_MODELS:
            d = builder.build(name="test", description="t", model=model)
            assert d.model == model


class TestNormalizeName:
    def test_spaces_to_kebab(self):
        builder = AgentBuilder()
        d = builder.build(name="My Agent Name", description="test")
        assert d.name == "my-agent-name"

    def test_special_chars_removed(self):
        builder = AgentBuilder()
        d = builder.build(name="agent@v2!", description="test")
        assert "@" not in d.name
        assert "!" not in d.name


class TestToMarkdownFrontmatter:
    def test_contains_yaml_fences(self):
        d = AgentDefinition(name="test-agent", description="테스트 에이전트")
        md = d.to_markdown()
        assert md.startswith("---")
        assert md.count("---") >= 2  # opening + closing

    def test_name_in_frontmatter(self):
        d = AgentDefinition(name="weather-bot", description="날씨 봇")
        md = d.to_markdown()
        assert "name: weather-bot" in md

    def test_tools_section(self):
        d = AgentDefinition(name="t", description="d", tools=["tool_a", "tool_b"])
        md = d.to_markdown()
        assert "- tool_a" in md
        assert "- tool_b" in md


class TestBuildCountIncrements:
    def test_count_increases(self):
        builder = AgentBuilder()
        assert builder._build_count == 0
        builder.build(name="a1", description="d1")
        assert builder._build_count == 1
        builder.build(name="a2", description="d2")
        assert builder._build_count == 2


class TestBuildWithPipeline:
    def test_pipeline_from_dicts(self):
        builder = AgentBuilder()
        d = builder.build(
            name="pipeline-agent",
            description="파이프라인 에이전트",
            pipeline=[
                {"name": "fetch", "source": "mod.fetch", "timeout": 5, "required": True},
                {"name": "analyze"},
            ],
        )
        assert len(d.pipeline) == 2
        assert d.pipeline[0].name == "fetch"
        assert d.pipeline[0].source == "mod.fetch"
        assert d.pipeline[0].required is True
        assert d.pipeline[1].name == "analyze"
        assert d.pipeline[1].timeout == 10  # default

    def test_pipeline_from_strings(self):
        builder = AgentBuilder()
        d = builder.build(
            name="p",
            description="d",
            pipeline=["step-a", "step-b"],
        )
        assert len(d.pipeline) == 2
        assert d.pipeline[0].name == "step-a"
