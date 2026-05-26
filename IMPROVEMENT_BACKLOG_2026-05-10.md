# SC2 지휘관봇 — 개선 백로그 (2026-05-10)

테스트 → 점검 → 개선 → 커밋/푸시 루프를 반복적으로 실행하기 위한 대규모 작업 리스트.
각 라운드 종료 시 본 문서를 갱신하고, 새 항목을 발견하면 백로그 끝에 추가한다.

## 현재 테스트 베이스라인 (Round 1 종료 시점)

| 영역 | 통과 | 스킵 | 실패 |
|---|---:|---:|---:|
| `tests/` (루트) | **392** | 34 | 0 |
| `wicked_zerg_challenger/tests/` | **651** | 3 | 0 |
| **합계** | **1043** | 37 | **0** |

## 라운드 1 — 테스트 인프라 복구 ✅ (DONE)

- [x] `pytest-asyncio` 미설치로 인한 83개 async 테스트 실패 → `uv tool install --with pytest-asyncio` 로 해결
- [x] `tests/test_queen_transfusion.py`: `from sc2.ids ...` 무조건 임포트로 collection 실패 → `try/except` + `pytest.skip` 패턴 적용
- [x] `wicked_zerg_challenger/blackboard.py`: `Blackboard` 별칭 누락 → `Blackboard = GameStateBlackboard` 추가, `__all__` 정의
- [x] `should_expand()` 의 오타 `is_supply_block` → `is_supply_blocked` 수정
- [x] `should_expand()` 가 미네랄 잔량을 검사하지 않아 100미네랄에서 확장 트리거 → 해처리 비용(300) 가드 추가
- [x] `wicked_zerg_challenger/tests/conftest.py`: 23개 collection error → `sc2`/`sc2.ids.*`/`sc2.bot_ai`/`sc2.unit`/`sc2.units`/`sc2.data`/`sc2.maps`/`sc2.main`/`sc2.player`/`sc2.client`/`sc2.protocol`/`sc2.portconfig` 의 in-memory 스텁 추가
- [x] `numpy` 의존 테스트 3종 (`test_actor_critic`, `test_observation_space`, `test_sprint6_rl_pipeline`) → `pytest.importorskip("numpy")` 패턴 적용

---

## 라운드 2 — 우선 적용 후보 (NEXT)

### 2A. 코드 품질 / 안전성

- [ ] `wicked_zerg_challenger/blackboard.py`: `is_supply_blocked` 상수 캐시 (매 호출 시 재계산)
- [ ] `should_expand()` 에 가스 잔량/식량 한도(40+) 체크 추가
- [ ] `Blackboard.update_resources(...)` 에 음수 입력 가드
- [ ] `GameStateBlackboard.__init__` 의 `logger` 가 매 인스턴스마다 생성됨 → 클래스 레벨 캐시
- [ ] `tests/test_queen_transfusion.py` 와 `tests/test_queen_transfusion_manager.py` 중복 → 한쪽으로 통합
- [ ] 에러 로그 일관성 (`logger.error(..., exc_info=True)`) 감사

### 2B. 테스트 커버리지

- [ ] `wicked_zerg_challenger/tests/test_meta_adapter.py` collection-순서 충돌 (root/scripts vs wicked/scripts) 방지: 로컬 패키지 임포트로 변경
- [ ] `wicked_zerg_challenger/tests/test_ladder_tracker.py` 동일
- [ ] 성능 벤치마크 테스트 별도 마커로 분리 (slow, requires-sc2)
- [ ] `test_blackboard.py` 의 `should_expand` 케이스에 미네랄 부족·가스 부족·식량 블록 분리 테스트 추가
- [ ] `pytest-cov` 도입 + 커버리지 리포트 추가

### 2C. 빌드 / CI

- [ ] `pyproject.toml` 또는 `requirements-dev.txt` 에 `pytest-asyncio`, `pytest-timeout` 명시
- [ ] `.github/workflows/` 에 nightly test 작업 (matrix: with/without sc2) 추가
- [ ] `pytest.ini` 의 `testpaths = tests` 를 양쪽 디렉터리 모두 포함하도록 확장하거나 멀티프로젝트화
- [ ] pre-commit hook: `python -m compileall` + `ruff check`

### 2D. SC2 봇 로직

- [ ] `wicked_zerg_challenger/queen_transfusion_manager.py` — 큐 dedup 키가 `tag` 이지만 죽은 후 재사용 시 충돌 가능 → `(tag, spawn_iteration)` 합성
- [ ] `aggressive_strategies.py` — 11풀/12풀 빌드 분기 시 워커 손실 보정 누락
- [ ] `creep_expansion_system.py` — BFS 그리드 메모리 누수 (재진입 시 cache 미해제)
- [ ] `combat_manager.py` — `health_percentage` 0인 죽은 유닛이 후방 풀에 잔존
- [ ] `economy_manager.py` — 과도한 가스 채집 시 미네랄 라인 부족 보정 안 함
- [ ] `expansion_manager.py` — 4번째 해처리 이후 거리 기반 우선순위 부재
- [ ] `production_resilience.py` — 락커 모프 실패 시 회복 경로 부재
- [ ] `queen_manager` — 인젝션 큐 우선순위 (위험 영역 해처리 우선)

### 2E. 관측 / 운영

- [ ] `metrics_exporter.py` — 큐 길이 메트릭 추가 (Prometheus)
- [ ] `web_dashboard.py` — WebSocket reconnect 백오프 부재
- [ ] `monitor_services.py` — health check 타임아웃 5s 너무 김

---

## 라운드 N — 점검 사이클

매 라운드 종료마다 `pytest tests/ wicked_zerg_challenger/tests/ -q --tb=no` 실행 후 본 문서의 베이스라인 표를 갱신한다.

작업 분류 기준:
1. **인프라/테스트** (즉시 반영 가능, 머지 위험 낮음)
2. **버그 수정** (정상 동작 위반, 회귀 테스트 동반)
3. **로직 개선** (전략 변경, A/B 테스트 권장)
4. **관측/운영** (런타임 메트릭, 알림)
