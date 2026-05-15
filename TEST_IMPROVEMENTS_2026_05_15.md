# SC2 Commander Bot - Test-Driven Improvements (2026-05-15)

테스트 결과 기반 개선 사항 대규모 리스트. 이 문서는 반복적인 테스트/점검 사이클에서
발견된 실제 버그를 우선적으로 정리한 것이다.

## 1차 발견 - 10 Test Failures + 21 Collection Errors

### A. SC2 Stub/Fallback 관련 (CRITICAL)
- [x] **A1**: `utils/unit_helpers.py` - `Units([], None)` 호출이 `Units=None` 시 TypeError → 안전한 빈 컬렉션 반환
- [x] **A2**: `early_defense_system.py` - 폴백 `UnitTypeId` 클래스가 비어있어서 `SPINECRAWLER`, `SPAWNINGPOOL`, `LAIR` 등 속성 누락
- [x] **A3**: `build_order_system.py` - 폴백 `UnitTypeId` 가 문자열 값을 가져 `isinstance(x, str)` 체크로 모든 액션이 `upgrade`로 잘못 분류됨
- [x] **A4**: `combat/micro_combat.py:828` - `if not UnitTypeId: return set()` 가드가 테스트 환경에서 lurker positioning을 막음
- [x] **A5**: `combat/mutalisk_micro.py:186` - `if not Point2: return None` 가드가 regen dance를 막음

### B. Test 수집 에러 (21 collection errors)
- [ ] **B1**: `test_aggressive_strategies_expansion_gate.py` - 모듈 임포트 실패
- [ ] **B2**: `test_blackboard.py` - 모듈 임포트 실패
- [ ] **B3**: `test_build_order_*` - 모듈 임포트 실패
- [ ] **B4**: `test_combat_manager.py` - sc2 모듈 임포트 실패
- [ ] **B5**: `test_creep_*` - sc2 모듈 임포트 실패
- [ ] **B6**: `test_defense_coordinator*` - sc2 모듈 임포트 실패
- [ ] **B7**: `test_economy_manager.py` - sc2 모듈 임포트 실패
- [ ] **B8**: `test_opponent_modeling.py` - sc2 모듈 임포트 실패
- [ ] **B9**: `test_production_*` - sc2 모듈 임포트 실패
- [ ] **B10**: `test_proxy_*` - sc2 모듈 임포트 실패
- [ ] **B11**: `test_resource_*` - sc2 모듈 임포트 실패
- [ ] **B12**: `test_smart_*` - sc2 모듈 임포트 실패
- [ ] **B13**: `test_sprint8_qa.py` - sc2 모듈 임포트 실패
- [ ] **B14**: `test_strict_upgrade_priority.py` - sc2 모듈 임포트 실패
- [ ] **B15**: `test_tech_coordinator_expansion.py` - sc2 모듈 임포트 실패
- [ ] **B16**: `test_upgrade_manager_expansion_reserve.py` - sc2 모듈 임포트 실패
- [ ] **B17**: `test_worker_harassment_defense.py` - sc2 모듈 임포트 실패

### C. 향후 개선 (Continuous Improvement)
- [ ] **C1**: `tests/test_unit_helpers.py` - assertion error using `result.units` vs `result` 일관성 검토
- [ ] **C2**: `test_zvt_phase1.py::TestZvTMicroAdjustments::test_banelings_attack_six_marine_clump` - `UnitTypeId.MARINE` 폴백 추가 필요
- [ ] **C3**: `test_zvp_phase2.py::test_zvp_stargate_selects_hydra_lair_macro` - 동일한 LAIR morph 액션 추론 버그
- [ ] **C4**: `test_zvt_phase1.py::test_zvt_safe_expand_selects_fast_lair_macro` - 동일한 morph 액션 추론 버그

## 사이클 정책

각 사이클마다:
1. 테스트 실행 → 실패/에러 항목 식별
2. 가장 영향력 있는 fix 우선 적용
3. 테스트 재실행으로 회귀 검증
4. commit + push
5. 다음 사이클 시작
