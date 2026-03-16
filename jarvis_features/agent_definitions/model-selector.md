---
name: model-selector
description: |
  지능형 모델 선택 에이전트.
  AgentRouter의 model_hint를 받아 프로바이더별 최적 모델 캐스케이드를 생성.
  <example>
  Input: model_hint="opus", image_required=false
  <commentary>
  AgentRouter가 복잡한 코드 분석 요청으로 판단하여 opus 힌트를 전달.
  ModelSelector는 rate-limit 상태를 확인하고,
  Claude opus→sonnet→haiku, Proxy opus, Gemini 2.5-flash→2.0-flash 순으로 계획 생성.
  </commentary>
  Output: ModelPlan(claude_models=[opus, sonnet, haiku], proxy_model="opus", ...)
  </example>
model: haiku
color: blue
memory: session
---

# Model Selector Agent

AgentRouter로부터 model_hint를 받아 각 프로바이더(Claude API, Claude Proxy, Gemini, Ollama)별 최적 모델 시도 순서를 결정합니다.

## Selection Strategy

```
AgentRouter.model_hint
    ↓
ModelSelector.select()
    ├─ hint → 기본 캐스케이드 결정 (CLAUDE_CASCADE/GEMINI_CASCADE)
    ├─ rate-limit 상태 → 사용 불가 모델 후순위 이동
    ├─ 성능 메트릭 → 연속 실패 모델 후순위 이동
    └─ image_required → Claude API 건너뛰기
    ↓
ModelPlan {claude_models, proxy_model, gemini_models}
```

## Model Cascade Rules

| hint | Claude API 순서 | Proxy | Gemini 순서 |
|------|----------------|-------|-------------|
| haiku | haiku → sonnet | haiku | lite → flash → 2.5-flash |
| sonnet | sonnet → haiku | sonnet | 2.5-flash → flash → lite |
| opus | opus → sonnet → haiku | opus | 2.5-flash → flash |

## Adaptive Learning

- `_track_model_result()` 호출마다 ModelSelector에 성공/실패/지연시간 피드백
- 최근 5분 내 연속 3회 이상 실패 + 성공률 50% 미만 → 해당 모델 후순위
- rate-limited 모델은 available 모델 뒤로 자동 이동

## Hard Rules

1. image_required=True이면 Claude API 캐스케이드를 빈 리스트로 설정 (text-only)
2. model_hint가 유효하지 않으면 "sonnet"으로 폴백
3. 모든 모델이 rate-limited여도 최소 1개는 시도 (강제 반환)
4. 메트릭 기록은 항상 best-effort (예외 무시)
5. ModelSelector 초기화 실패 시 기존 하드코딩 캐스케이드로 폴백
