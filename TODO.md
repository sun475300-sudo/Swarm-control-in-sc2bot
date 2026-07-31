# 내일 작업 목록 (2026-01-26)

## 우선순위 높음 🔴

### 1. 정찰 시스템 강화
**문제점:**
- 정찰을 수시로 하지 않음
- 적의 빌드와 유닛 구성을 파악하지 못함

**해결 방안:**
- `scouting_system.py` 수정
  - 초반: 오버로드로 30초마다 적 본진 정찰
  - 중반: 저글링으로 맵 전체 정찰 (1분마다)
  - 후반: 오버시어로 은폐 유닛 탐지

**파일:** `wicked_zerg_challenger/scouting_system.py`

---

### 2. 견제 시스템 개선
**현재 상태:**
- 1-4분 견제 시스템 구현됨 (strategy_manager.py:228-262)
- 30초마다 견제 신호 전송

**개선 필요:**
- 견제 유닛이 실제로 적 본진으로 이동하는지 확인
- 견제 후 복귀 로직 추가
- 적 일꾼 킬 카운트 추적
- 더 공격적인 견제 (15초마다)

**파일:**
- `wicked_zerg_challenger/strategy_manager.py`
- `wicked_zerg_challenger/combat_manager.py`

---

### 3. 1분 멀티 타이밍 테스트 및 최적화
**현재 상태:**
- expansion 로직 수정 완료 (미네랄 300 즉시 확장)
- 마지막 테스트: 6분에 첫 멀티 성공

**테스트 필요:**
- 실제로 1분 안에 멀티를 가져가는지 확인
- 드론 생산과 expansion 밸런스 최적화
- 풀링 러시 대응 시나리오 테스트

**파일:** `wicked_zerg_challenger/economy_manager.py:882-895`

---

## 우선순위 중간 🟡

### 4. 전투 로직 성능 최적화 (프레임 스킵) — ✅ 2026-07-24 수정 완료
**문제점 (원인 확인됨):**
- `MicroFocusMode.update()`가 상황별 실행 간격(평시 8프레임 / 경계 5 / 전투 3 / 위급 1)을
  올바르게 계산해서 반환하고 있었으나, `bot_step_integration.py`가 그 반환값(`micro_interval`)을
  변수에 저장만 하고 실제로 사용하지 않아 `AdvancedMicroControllerV3.on_step()`이 매 프레임
  실행되고 있었음 (계산은 있었지만 결선이 안 된 dead code).

**해결 완료:**
- `bot_step_integration.py`의 MicroV3 호출부에 `iteration % micro_interval == 0` 가드 추가.
- 회귀 확인: `wicked_zerg_challenger` 테스트 661/661 통과, pyflakes로 dead-code 경고 소거 확인.

**참고 파일:**
- `wicked_zerg_challenger/bot_step_integration.py` (가드 추가 위치)
- `wicked_zerg_challenger/micro_focus_mode.py` (간격 계산 로직, 변경 없음)

---

### 5. 전략 매니저 역할 분담
**문제점:**
- StrategyManager가 건물 건설 위치 찾기, 일꾼 배정 등 너무 많은 역할
- 이는 버그의 원인이 됨

**해결 방안:**
- 건물 건설: BuildingManager로 위임
- 일꾼 배정: EconomyManager로 위임
- StrategyManager는 전략 결정만 담당

**파일:** `wicked_zerg_challenger/strategy_manager.py`

---

## 버그 수정 🐛

### 6. 인코딩 에러 완전 제거
**남은 인코딩 에러:**
- `early_defense_system.py` - "⚪" 문자 사용
- `build_order_executor.py` - "✓" 문자 사용
- 기타 한글 메시지가 있는 모든 파일

**해결 방안:**
- 모든 특수 문자를 ASCII로 변경
- 또는 모든 print/logger에 인코딩 처리 추가

**파일:**
- `wicked_zerg_challenger/early_defense_system.py`
- `wicked_zerg_challenger/build_order_executor.py`
- 기타 인코딩 에러 발생 파일

---

## 테스트 항목 ✅

### 7. 난이도별 승률 테스트
- [ ] Easy 난이도 vs Protoss (목표: 100% 승률)
- [ ] Easy 난이도 vs Terran (목표: 100% 승률)
- [ ] Easy 난이도 vs Zerg (목표: 100% 승률)
- [ ] Medium 난이도 테스트 시작
- [ ] 10게임 연속 테스트 (안정성 확인)

---

## 오늘 완료된 작업 ✅

1. ✅ 인코딩 에러 수정 (combat_manager.py, improved_hierarchical_rl.py)
2. ✅ 로그 스팸 제거 (strategy_manager.py)
3. ✅ 1-4분 견제 시스템 추가
4. ✅ 일꾼 생산 문제 해결 (1베이스 28마리까지)
5. ✅ 점막 종양 제한 해제
6. ✅ Expansion 로직 개선 (6분 → 1분 목표)

---

## 참고사항 📝

### 주요 파일 위치
```
wicked_zerg_challenger/
├── strategy_manager.py          # 전략 관리
├── economy_manager.py           # 경제 및 확장
├── combat_manager.py            # 전투 관리
├── scouting_system.py           # 정찰 시스템
├── early_defense_system.py      # 초반 방어
├── creep_manager.py             # 점막 관리
└── local_training/
    ├── economy_combat_balancer.py  # 경제/전투 밸런스
    └── hierarchical_rl/
        └── improved_hierarchical_rl.py  # 강화학습
```

### 테스트 명령어
```bash
cd wicked_zerg_challenger
python run_single_game.py
```

### 주요 로그 위치
```
wicked_zerg_challenger/logs/bot.log
logs/sensor_network.json
```

---

## 장기 목표 🎯

1. **승률 90%+ 달성** (Medium 난이도)
2. **완벽한 매크로 경제** (분당 80+ 미네랄 수집)
3. **프로게이머급 견제** (상대 경제 지속적 견제)
4. **맵 전체 점막 장악**
5. **AI Arena 대회 참가 준비**

---

**작성일:** 2026-01-25
**다음 업데이트:** 2026-01-26
