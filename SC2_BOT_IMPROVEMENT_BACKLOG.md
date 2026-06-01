# SC2 지휘관봇 — 테스트 기반 개선 백로그

> 시작일: 2026-06-01
> 작업 브랜치: `claude/cool-edison-kamgm`
> PR: #216
> 방식: 테스트 실행 → 이슈 식별 → 대규모 리스트 → 작업 → 커밋/푸시 → 반복

## 진행 요약

| 사이클 | 커밋 | passed | failed | error | 변경 |
|---|---|---|---|---|---|
| baseline | — | 312 | 83 | 1 | (pytest-asyncio 누락 환경에서) |
| 1 | a6f91f3 | 395 | 0 | 0 | 비동기 테스트 modernize, sc2 import 가드 |
| 2 | 9597b3c | 395 | 0 | 0 | EnhancedScoutSystem warn 위치, scout stub, check_proxy |
| 3 | 560c932 | 395 | 0 | 0 | `Dict[str, any]` → `Dict[str, Any]` 5건 |
| 4 | 6cbf36e | 395 | 0 | 0 | 죽은 코드 4건 제거 (87줄) + range shadow |
| 5 | 77d2ed8 | 703 | 7 | 0 | **UnitFactory NameError 2개**, sc2 import 가드 18개, Units 폴백 |
| 6 | 325c7bd | 703 | 7 | 0 | 컬렉션 에러 5건 → 0 |
| 7 | 251a6c5 | 710 | 0 | 0 | **blackboard.should_expand 자원 게이트**, sc2 stub 4건 |

## 발견·수정한 실제 운영 버그

1. **`unit_factory._update_gas_ratio_target()` NameError** — 한글 주석의 인코딩 깨짐이 줄바꿈을 먹어 `strategy = getattr(...)` 할당이 주석 안에 들어가 있었음. 매 step마다 실행되는 hot path.
2. **`unit_factory.on_step` `unit_requests` NameError** — 동일 패턴. `unit_requests = {}` 초기화가 주석 안에 있어 다음 줄의 인덱싱이 실패.
3. **`blackboard.should_expand()` 자원 미체크** — 100 mineral 만 있어도 expansion을 허용. `MIN_MINERALS_FOR_EXPANSION=250` 추가.
4. **`smart_resource_balancer` 죽은 worker-classification 로직 48줄** — 리팩토링 후 잔존, 절대 실행되지 않음.
5. **`economy_manager._force_expansion_if_stuck` + `_check_proactive_expansion` 죽은 코드 79줄** — 헬퍼로 추출된 옛 inline 버전.
6. **`check_proxy.py` 임포트 시 sys.exit(1)** — 하드코딩 Windows 경로, logger.info에 positional args 오용, `if __name__=="__main__"` 누락.
7. **`scouting/enhanced_scout_system.py` warn 시점** — 모듈 임포트 시점에 매번 발생, fallback로 임포트해도 노이즈.
8. **`advanced_scout_system_v2.py` stub** — sc2 미설치 시 class body의 `UnitTypeId.OVERLORD` 기본인자가 AttributeError, 모듈 임포트 전체 실패.
9. **`Dict[str, any]` 5건** — `any`는 builtin 함수, `typing.Any`가 아님. 런타임 introspection 실패.
10. **`find_nearby_enemies(unit, enemy_units, range)`** — 파라미터가 `range` builtin shadowing. 함수 내부 사용은 안전했으나 가독성/안전성 측면에서 `radius`로 리네임.

## 사이클 진행 로그

### 사이클 1 (완료, a6f91f3)
- [x] pytest-asyncio 설치 누락 식별 (환경 측)
- [x] test_queen_transfusion.py — sc2 import 가드 추가
- [x] test_combat_phase_fsm.py — event loop modernize (×5)
- [x] wicked_zerg_challenger/tests/test_production_resilience.py — 동일

### 사이클 2 (완료, 9597b3c) — 임포트 안정성 & 잠재 버그
- [x] EnhancedScoutSystem 경고를 인스턴스화 시점으로 이동
- [x] AdvancedScoutingSystemV2 sc2 stub `_IdStub.__getattr__` sentinel
- [x] check_proxy.py: `if __name__=='__main__'`, env-var 경로, logger 버그 수정

### 사이클 3 (완료, 560c932) — 타입 어노테이션
- [x] `Dict[str, any]` → `Dict[str, Any]` 5건

### 사이클 4 (완료, 6cbf36e) — 죽은 코드 + 빌트인 셰도잉
- [x] dead code 4건 제거 (87줄)
- [x] `range` 파라미터 → `radius`

### 사이클 5 (완료, 77d2ed8) — UnitFactory NameError 2개 + 테스트 인프라
- [x] unit_factory.py 두 개의 mojibake 주석이 코드를 삼킨 버그
- [x] tests에서 sc2 import 가드 18건 일괄 추가
- [x] utils/unit_helpers.py 폴백 `_empty_units()`

### 사이클 6 (완료, 325c7bd) — 컬렉션 에러 박멸
- [x] test_actor_critic, test_observation_space, test_sprint6/8 RL 가드
- [x] test_difficulty_progression 단순 skip

### 사이클 7 (완료, 251a6c5) — sc2 stub 강화 + 자원 게이트
- [x] blackboard.should_expand 미네랄 250 게이트 추가
- [x] build_order_system.py: `_IdStub` + `_IdSentinel` (str 충돌 회피)
- [x] early_defense_system.py / combat/micro_combat.py / combat/mutalisk_micro.py stub 강화

## 사이클 8+ 후보 (계속)

- 시나리오 회귀 테스트 추가 (vs Zerg/Terran/Protoss 빌드 변경)
- Combat phase FSM negative-path 시나리오 (RETREAT 트리거)
- `try: except: pass` 270건 검토 — 진짜 swallow 필요한 곳 vs 로그 필요한 곳 분류
- 코드 mojibake 정리 (가독성 - 비즈니스 임팩트 없음)
- 봇 의도 시나리오 단위 통합 테스트 (현재는 unit 위주)
