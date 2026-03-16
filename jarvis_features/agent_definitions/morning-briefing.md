---
name: morning-briefing
description: |
  모닝 브리핑 파이프라인 오케스트레이터.
  7개 섹션을 병렬 수집 → 포맷팅 → 디스코드 전송.
  <example>
  Trigger: 매일 오전 7:30 자동 실행 또는 "브리핑 해줘" 명령
  <commentary>
  weather/fortune/calendar/news/portfolio/sc2/system 7개 에이전트를
  동시에 실행하여 최대 15초(가장 느린 calendar) 내에 전체 브리핑 생성.
  기존 순차 실행 대비 ~60% 시간 절약.
  </commentary>
  </example>
model: haiku
color: green
memory: project
pipeline:
  - name: weather-agent
    source: morning_briefing_helper.get_weather
    timeout: 10
    required: false
  - name: fortune-agent
    source: morning_briefing_helper.get_fortune
    timeout: 5
    required: false
  - name: calendar-agent
    source: calendar_integration.CalendarIntegration.get_today_events
    timeout: 15
    required: false
  - name: news-agent
    source: morning_briefing_helper.get_google_news
    timeout: 10
    required: false
  - name: crypto-agent
    source: daily_briefing._get_portfolio_section
    timeout: 10
    required: false
  - name: sc2-agent
    source: daily_briefing._get_sc2_section
    timeout: 5
    required: false
  - name: system-agent
    source: daily_briefing._get_system_section
    timeout: 5
    required: false
---

# Morning Briefing Orchestrator

매일 아침 JARVIS가 자동으로 생성하는 종합 브리핑 파이프라인입니다.

## Pipeline Overview

```
[weather] ─┐
[fortune] ─┤
[calendar]─┤
[news]   ─┤──→ [briefing-formatter] ──→ Discord Channel
[crypto] ─┤
[sc2]    ─┤
[system] ─┘
```

모든 스텝이 **병렬**로 실행됩니다 (asyncio.gather).
각 스텝은 독립적이며, 하나가 실패해도 나머지는 정상 출력됩니다.

## Execution Rules

1. 각 스텝은 개별 타임아웃을 가짐 (calendar=15s, 기본=10s)
2. 실패한 스텝은 "정보를 가져올 수 없습니다" 메시지로 대체
3. 모든 스텝 완료 후 포맷터가 헤더/푸터 추가
4. 실행 보고서를 로그에 기록 (성공/실패/소요시간)

## Hard Rules

1. required=false: 어떤 섹션이든 실패해도 브리핑은 생성
2. 타임아웃 초과 시 해당 섹션만 스킵
3. 전체 브리핑 생성 시간은 20초를 초과하지 않아야 함
4. 포트폴리오 섹션에 민감한 키 정보를 포함하지 않음
5. 브리핑 채널 ID는 환경변수 BRIEFING_CHANNEL_ID에서 읽음
