# SC2 지휘관봇 개선 트래커 (Iterative)

테스트/점검 사이클로 발견된 개선사항을 추적합니다. 항목 단위로 수정 → 커밋 → 푸시 → 다음 항목.

## 사이클 1: 정적 import / __init__ / 테스트 인프라

### 인프라 (Infra)
- [x] **A1** pytest-asyncio 누락 — uv tool로 설치 (83건 async 테스트 unblock)
- [x] **A2** numpy 누락 — 설치 후 추가 4건 실패 노출 (다음 항목)

### Phase 6xx 모듈 import 결함
- [ ] **I1** `qmix_marl/sc2_qmix_agent.py`: `class AgentQNetTorch(nn.Module)` 등 3개가 torch import 실패 시 `nn` 미정의로 NameError. `if HAS_TORCH:` 가드 필요
- [ ] **I2** `mappo_marl/sc2_mappo_agent.py`: 동일 결함 (3개 클래스). `HAS_TORCH` 가드 필요
- [ ] **I3** `comm_learning/__init__.py`: 존재하지 않는 심볼 export (`CommChannel/CommNet/TarMAC/CommAgent`). 실제 정의된 이름과 매핑 필요
- [ ] **I4** `attention_policy/__init__.py`: 존재하지 않는 `AttentionPolicy/EntityEncoder/MultiHeadAttention/TransformerBlock`
- [ ] **I5** `world_model/__init__.py`: 존재하지 않는 `RSSM/WorldModel/DreamerAgent/LatentImagination` (실제는 `RSSM`은 있음, `WorldModel→SC2WorldModel`, `DreamerAgent` 없음)

### 검증
- [ ] **I6** 전 패키지 import 청결 검증 — 27개 후보군 sweep
- [ ] **I7** dev 환경 deps (pytest-asyncio, pytest-timeout, numpy) requirements 명시

## 사이클 2 (예정): 정적 분석 (lint/mypy)
- [ ] flake8 critical (E9, F63, F7, F82) 0건 유지
- [ ] mypy import-error 정리

## 사이클 3 (예정): 통합/성능 테스트
- [ ] tests/integration/* 실행
- [ ] 봇 핵심 코드 dead import / TODO 분석

## 진행 로그

| 사이클 | 항목 | 상태 | 커밋 |
|---|---|---|---|
| 1 | A1, A2 | 환경 설정 (커밋 없음) | - |
