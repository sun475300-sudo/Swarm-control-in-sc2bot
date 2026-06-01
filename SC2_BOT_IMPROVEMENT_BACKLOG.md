# SC2 지휘관봇 — 테스트 기반 개선 백로그

> 시작일: 2026-06-01
> 작업 브랜치: `claude/cool-edison-kamgm`
> 방식: 테스트 실행 → 이슈 식별 → 대규모 리스트 → 작업 → 커밋/푸시 → 반복

## 베이스라인 (사이클 1 시작 시점)

```
collected 423 items / 1 error / 5 skipped
83 failed, 312 passed, 33 skipped  (pytest-asyncio 누락 시)
12 failed, 383 passed, 33 skipped  (pytest-asyncio 설치 후)
```

원인 분류:
- 인프라(pytest-asyncio 미설치): 71건 → 환경 측 해결
- 잔존 실패(코드 이슈): 12건 + collect error 1건

---

## 사이클 1 — 즉시 수정 가능한 테스트 결함 (확정)

| # | 분류 | 파일 | 증상 | 조치 |
|---|---|---|---|---|
| 1 | 임포트 | `tests/test_queen_transfusion.py` | `from sc2.ids.unit_typeid import UnitTypeId` 실패 시 collect error | 다른 sc2 테스트처럼 `try/except ImportError → pytest.skip` |
| 2 | 비동기 | `tests/test_combat_phase_fsm.py` ×5 | `asyncio.get_event_loop()` — Py3.10+ 에서 'no current event loop' | `asyncio.new_event_loop()` + `loop.close()` 또는 `asyncio.run()` |
| 3 | 비동기 | `wicked_zerg_challenger/tests/test_production_resilience.py:388` | 동일 deprecated 패턴 | 동일 처리 |

## 사이클 2 — 신뢰성/에러 처리 검토 영역 (조사 필요)

| 영역 | 진단 메서드 |
|---|---|
| `try/except ImportError` 일관성 | sc2/torch import 사용 모듈 전부 확인 |
| `asyncio.get_event_loop()` 전수조사 | 사용 코드/테스트 모두 modernize |
| 코어 매니저 단위 테스트 커버리지 | `intel_manager`, `economy_manager`, `expansion_manager`, `resource_manager`, `combat_manager` |
| skip/xfail 라벨링 | tests/test_p606_modules.py 6건, test_crypto_trading.py 5건 등 사유 분류 |

## 사이클 3 — 정적 분석 (계획)

- 죽은 코드 (unused import, unreachable)
- 중복 정의 (동일 함수 여러 곳)
- 매직 넘버 → 상수화
- 미보호 division by zero / None deref

## 사이클 4+ — 봇 의도 단위 시나리오 (계획)

- 매치업별 빌드 (vs Zerg/Terran/Protoss) 분기 테스트
- Queen transfusion 우선순위/쿨다운 시나리오 확장
- Expansion timing 회귀
- Combat phase FSM 음·양 경로

---

## 사이클 진행 로그

### 사이클 1 (완료, 커밋 a6f91f3)
- [x] pytest-asyncio 설치 누락 식별 (환경 측)
- [x] test_queen_transfusion.py — sc2 import 가드 추가
- [x] test_combat_phase_fsm.py — event loop modernize (×5)
- [x] wicked_zerg_challenger/tests/test_production_resilience.py — 동일
- 결과: `12 failed → 0 failed (395 passed)`, 1 collect error → 0

### 사이클 2 (진행 중) — 임포트 안정성 & 잠재 버그
- [x] EnhancedScoutSystem 경고가 **모듈 임포트 시점**에 매번 발생 (fallback로 import만 해도 노이즈) → 인스턴스화 시점으로 이동
- [x] AdvancedScoutingSystemV2 stub: sc2 미설치 시 `UnitTypeId.OVERLORD` 기본인자가 class body에서 AttributeError → `_IdStub.__getattr__` sentinel로 해결
- [x] check_proxy.py: 임포트만 해도 sys.exit(1) 호출 (Windows 절대경로 하드코딩). `if __name__=='__main__'` 가드 + env-var 경로 + `logger.info` positional-args 버그 수정
- [ ] cycle 2 더 진행: 다른 영역 점검

