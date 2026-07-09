# WickedZergBot 대규모 수정 계획서

**기준 데이터**: 88게임 로그 분석 (17W/71L, 승률 19.3%)  
**분석일**: 2026-05-10  
**목표**: 승률 50%+ 달성 (Easy AI 기준 80%+)

---

## ⚠️ 2026-07-09 현황 재확인 (중요 — 재작업 방지용)

이 문서는 2026-05-10 이후 갱신되지 않았지만, **아래 항목들은 이미 코드에 구현되어 있음**을
`grep -rn "FIX P0"` / `grep -rn "FIX P1"` 및 관련 함수 존재 여부로 직접 확인했다 (커밋 메시지가
`1`, `12` 같은 무의미한 문자열이라 git log 검색으로는 안 잡히니 주의 — 반드시 코드에서 직접 확인할 것).

**P0 (Sprint 1+2) — 8개 전부 구현 완료:**
- P0-1 가스 부유 해결 — `local_training/production_resilience.py:389,2809`
- P0-2 EMERGENCY 타임아웃 — `blackboard.py:359` (30초)
- P0-3 EMERGENCY 중 최소 드론 유지 — `strategy_manager_v2.py:1258` (0.0→0.1)
- P0-4 REMAX 시스템 — `local_training/production_resilience.py:2432` (`_check_remax_needed`)
- P0-5 3기지 강제 확장 — `local_training/production_resilience.py:408`
- P0-6 서플라이 블록 예방 강화 — `local_training/production_resilience.py:1331`
- P0-7 가스 워커 자동 조절 — `resource_manager.py:223`, `economy_manager.py:1159`, `smart_resource_balancer.py:404`
- P0-8 1기지 미네랄 오버플로 — `local_training/production_resilience.py:437`

**P1 — 8개 중 6개는 이미 사실상 구현됨, 2개는 진짜 미구현:**
- P1-1 HP가중 전투력 — `combat_manager.py:3070 _combat_power()` 구현됨 (단, shield 항 없음 — Protoss 상대 시 과소평가 가능성 있으니 개선 여지는 있음)
- P1-2 무한루프 위험 — 현재 `strategy_manager_v2.py:1296`는 `while`이 아니라 `if`문이라 애초에 무한루프 아님 (moot)
- **P1-3 매치업별 초기 빌드오더 분리 — 미구현 확인.** `enemy_race == Race.*` 분기가 strategy_manager_v2.py/early_defense_system.py에 없음. 진짜 남은 작업.
- P1-4 공격 타이밍(서플80+) — `combat_manager.py:1980`에 구현됨
- **P1-5 방어 병력 50% 분할 — 미구현 확인.** `defense_coordinator.py`의 `_emergency_defense`/`_request_emergency_units`는 신규 유닛 생산 요청만 하고, 기존 공격 부대를 방어로 회수하는 로직 자체가 없음 (그래서 "100% 회수" 버그도 없지만, 계획된 50/50 분할 기능도 없음). 진짜 남은 작업이지만 실전 검증 없이 만지면 위험도 있음.
- P1-6 퀸 인젝트 최적화 — `economy/queen_inject_optimizer.py` (29초 쿨다운, 우선순위, role 관리) 이미 계획보다 정교하게 구현됨
- P1-7 테크 타이밍 — 레어 타이밍 체크(`upgrade_manager.py:676`)는 있음, 하이브 9:00~10:00 타이밍은 미확인
- P1-8 유닛 컴포지션 자동 조정 — `unit_factory.py` 가스비율/`_check_protoss_threat_boost` 등 이미 구현됨

**결론**: 이 계획서가 암시하는 "19.3% 승률" 데이터 시점(2026-05-10) 이후 P0 전체 + P1 대부분이
이미 고쳐졌다. 문서만 안 갱신된 것 — **실제 승률이 얼마인지는 현재 재검증 필요** (§ 검증 계획의
20게임 자동 대전을 아직 아무도 실행/기록하지 않은 것으로 보임). 다음 작업자는:
1. P0/P1 재작업 금지 (위 목록 참고)
2. P1-3(매치업별 빌드오더), P1-5(방어 분할), P1-7(하이브 타이밍 확인) 가 진짜 남은 작업
3. P2/P3는 이 문서 작성 이후 grep으로 재확인 안 됨 — 착수 전 반드시 먼저 확인할 것
4. 20게임 벤치마크를 실제로 돌려서 현재 진짜 승률을 재측정하는 것이 최우선 — 감이 아니라 데이터로 판단해야 함

---

## 핵심 패턴 분석

### 패배 원인 통계
- **71패 중 61경기 (86%)**: 최종 서플라이 0~9 → 군대가 전멸하고 회복 불가
- **가스 낭비**: 패배 시 평균 잔여 가스 1,700+ (ZvP: 2,238, ZvZ: 1,994)
- **확장 부족**: 승리 시 평균 2.1 확장 vs 패배 시 2.0 → 3기지 전환 실패
- **매치업 불균형**: ZvP 8%, ZvT 18%, ZvZ 67%

### 근본 원인 5가지
1. **가스 부유**: 가스 소비 로직이 미네랄 초과 소비만 처리, 가스 초과는 방치
2. **EMERGENCY 모드 무한루프**: 위협 감지 → 드론 생산 중단 → 경제 붕괴 → 군대 복구 불가
3. **확장 타이밍 지연**: 3기지가 계획(240초)보다 크게 늦어짐
4. **군대 맥스아웃 실패**: 최대 서플라이 89에 그침, 200 도달 불가
5. **패배 후 회복 메커니즘 부재**: 군대 전멸 시 재건 로직 없음

---

## 수정 항목 (총 32개)

### P0 — CRITICAL (즉시 수정, 승률 직접 영향) [8개]

#### P0-1. 가스 부유 해결: _spend_excess_minerals()에 가스 체크 추가
- **파일**: `production_resilience.py` lines 2622-2630
- **현재**: 미네랄 > 200이면 저글링(가스 0) 무조건 생산 → 가스 계속 축적
- **수정**: 가스 > 300이면 저글링 대신 히드라/뮤탈/바퀴 생산 우선
- **코드**:
```python
# 기존: 무조건 저글링
if self.bot.minerals > 200:
    train zergling

# 수정: 가스 잔고에 따라 분기
if self.bot.vespene > 300 and can_afford(HYDRALISK):
    train hydralisk  # 가스 50 소비
elif self.bot.vespene > 200 and can_afford(ROACH):
    train roach  # 가스 25 소비
else:
    train zergling  # 가스 0, 미네랄만 소비
```
- **예상 효과**: 가스 부유 2,238 → 500 이하

#### P0-2. EMERGENCY 모드 타임아웃 추가
- **파일**: `blackboard.py` (authority mode 관리)
- **파일**: `defense_coordinator.py` lines 600-605
- **현재**: CRITICAL 위협 → EMERGENCY 진입, 해제 조건 불명확 → 무한 지속
- **수정**: EMERGENCY 진입 시 타임스탬프 기록, 30초 후 자동 BALANCED 복귀
- **코드**:
```python
def set_authority_mode(self, mode, reason):
    self._authority_mode = mode
    self._authority_set_time = self.bot.time
    
def get_authority_mode(self):
    # 30초 타임아웃
    if (self._authority_mode == AuthorityMode.EMERGENCY 
        and self.bot.time - self._authority_set_time > 30):
        self._authority_mode = AuthorityMode.BALANCED
    return self._authority_mode
```
- **예상 효과**: EMERGENCY 스팸 제거, 경제 복구 가능

#### P0-3. EMERGENCY 중에도 드론 최소 생산 보장
- **파일**: `strategy_manager_v2.py` lines 1164-1261 (resource priority)
- **현재**: EMERGENCY → economy=0.0 → 드론 완전 중단
- **수정**: EMERGENCY에서도 economy=0.15 유지 (최소 드론 교체)
- **코드**:
```python
# 기존
if emergency: priorities = {"army": 0.7, "economy": 0.0, ...}
# 수정
if emergency: priorities = {"army": 0.6, "economy": 0.15, "defense": 0.2, "tech": 0.05}
```

#### P0-4. 군대 전멸 후 리맥스(재건) 시스템
- **파일**: `production_resilience.py` (새 메서드 추가)
- **현재**: 군대 전멸 → 아무 조치 없음 → 서플라이 0~4로 패배
- **수정**: 군대 서플라이 < 20이면 REMAX 모드 진입
  - 모든 라바를 전투 유닛 생산에 투입
  - 잔여 가스로 고급 유닛(히드라/뮤탈) 우선
  - 저글링으로 시간 벌기
- **코드**:
```python
async def check_remax_needed(self):
    army_supply = sum(u.supply for u in self.bot.units if u.can_attack and not u.is_worker)
    if army_supply < 20 and self.bot.supply_workers > 30:
        # REMAX: 모든 라바를 군대로
        for larva in self.bot.larva:
            if self.bot.vespene >= 50 and can_afford(HYDRALISK):
                larva.train(HYDRALISK)
            elif can_afford(ZERGLING):
                larva.train(ZERGLING)
```
- **예상 효과**: 86% 패배 패턴(서플 0~9) 직접 해결

#### P0-5. 3기지 확장 타이밍 강제 실행
- **파일**: `strategy_manager_v2.py` lines 670-775 (expansion planning)
- **파일**: `production_controller.py` lines 284-310 (expansion reserve)
- **현재**: 240초에 3기지 "계획"하지만 reserve 로직이 블로킹 → 실제 건설 지연
- **수정**: 
  - 240초(4분) 도달 시 reserve 무관하게 3기지 강제 건설
  - expansion reserve 타임아웃 60초 추가
- **코드**:
```python
async def force_third_base(self):
    if (self.bot.time >= 240 
        and self.bot.townhalls.ready.amount < 3
        and not self.bot.already_pending(HATCHERY)):
        if self.bot.can_afford(HATCHERY):
            await self.bot.expand_now()
```

#### P0-6. 서플라이 블록 예방 강화
- **파일**: `wicked_zerg_bot_pro_impl.py` 또는 `production_resilience.py`
- **현재**: 서플라이 여유 < 4일 때 오버로드 생산, 하지만 로그에서 14/12 블록 발생
- **수정**: 서플라이 여유 < 6으로 상향, 2개 동시 생산 허용
- **코드**:
```python
if (self.supply_left < 6 and self.supply_cap < 200
    and self.already_pending(OVERLORD) < 2):
    if self.can_afford(OVERLORD) and self.larva:
        self.larva.random.train(OVERLORD)
```

#### P0-7. 가스 워커 자동 조절 개선
- **파일**: resource_manager.py (gas worker assignment)
- **현재**: 가스가 미네랄의 3배 이상일 때만 워커 이동 → 너무 느림
- **수정**: 가스 > 500이면 즉시 가스 워커 감소, 가스 < 100이면 즉시 증가
- **코드**:
```python
def _should_prioritize_minerals_over_gas(self):
    # 기존: gas > max(300, minerals * 3)  ← 너무 느슨
    # 수정:
    if self.bot.vespene > 500 and self.bot.minerals < 300:
        return True  # 가스 과잉, 미네랄 부족
    if self.bot.vespene > self.bot.minerals * 2:
        return True  # 가스가 미네랄의 2배
    return False
```

#### P0-8. 미네랄 오버플로 1기지 처리 추가
- **파일**: `production_resilience.py` lines 416-424
- **현재**: bases >= 2 조건 → 1기지에서 미네랄 넘쳐도 처리 안 됨
- **수정**: 1기지에서도 미네랄 > 400이면 오버플로 처리 활성화
- **코드**:
```python
# 기존: if bases >= 2 and minerals > 600
# 수정: if minerals > 400 (1기지) or (bases >= 2 and minerals > 600)
if self.bot.minerals > 400:
    await self._spend_excess_minerals()
```

---

### P1 — HIGH (핵심 전투력 향상) [8개]

#### P1-1. 전투력 비교 로직 개선 (HP-가중치)
- **파일**: `combat_manager.py`
- **현재**: 단순 유닛 수 비교로 전투 결정
- **수정**: HP + Shield + DPS 가중치 비교
```python
def calculate_combat_power(self, units):
    return sum(
        (u.health + u.shield) * (1 + u.ground_dps / 10)
        for u in units
    )
```

#### P1-2. 무한 루프 위험 제거: strategy_manager_v2
- **파일**: `strategy_manager_v2.py` ~line 1588
- **현재**: `while len(active_strategies) < limit` → 전략 추가 실패 시 무한루프
- **수정**: max_iterations 카운터 추가
```python
max_attempts = 5
for _ in range(max_attempts):
    if len(self.active_strategies) >= self.concurrent_strategy_limit:
        break
    if not self._queue_pending_strategies(game_time):
        break
```

#### P1-3. 매치업별 초기 빌드오더 분리
- **파일**: `strategy_manager_v2.py`, `early_defense_system.py`
- **현재**: 모든 매치업 동일 오프닝
- **수정**:
  - ZvP: 14풀 → 빠른 바퀴 + 로치 워런 (보이드레이/아다 대응)
  - ZvT: 16해치 → 저글링 속도 → 바퀴 (헬리온/리퍼 대응)
  - ZvZ: 12풀 → 저글링 속도 → 바퀴 (거울전)

#### P1-4. 공격 타이밍 최적화
- **파일**: `combat_manager.py`
- **현재**: 군대 가치 기반 공격 판단
- **수정**: 
  - 서플라이 80+ 달성 시 첫 공격 (2~3기지 포화 기준)
  - 서플라이 150+에서 메인 푸시
  - 공격 후 후퇴 판단: 아군 전투력 30% 이하 시 철수

#### P1-5. 방어 유닛 위치 최적화
- **파일**: `defense_coordinator.py`
- **현재**: 적 위협 시 모든 군대를 해당 기지로 이동
- **수정**: 
  - 전체 군대의 50%만 방어 투입
  - 나머지는 다음 공격 준비 포지션 유지
  - 스파인/스포어 크롤러 자동 건설

#### P1-6. 퀸 인젝트 최적화
- **파일**: `queen_manager.py`
- **현재**: idle 퀸만 인젝트
- **수정**: 
  - 인젝트 타이머 관리 (25초 주기)
  - 해치 간 퀸 재배치 자동화
  - 3기지 이후 퀸 4마리 이상 유지

#### P1-7. 테크 전환 타이밍
- **파일**: `upgrade_manager.py`, `strategy_manager_v2.py`
- **현재**: 업그레이드 비용 조회 수정됨, 하지만 타이밍 불명확
- **수정**:
  - 레어 타이밍: 4:30~5:00 (66 드론 이전)
  - 하이브 타이밍: 9:00~10:00
  - 공격/방어 업그레이드 1단계: 레어 완성 직후
  - 2단계: 하이브 진입 전

#### P1-8. 유닛 컴포지션 자동 조정
- **파일**: `unit_factory.py`
- **현재**: gas_unit_ratio 고정
- **수정**:
  - 적 공중 유닛 감지 → 히드라/코럽터 전환
  - 적 메카닉 → 바퀴/불로드 전환
  - 적 경장갑 → 바네링 추가

---

### P2 — MEDIUM (안정성 & 효율) [10개]

#### P2-1. BotStepIntegrator 폴백 메커니즘
- **파일**: `wicked_zerg_bot_pro_impl.py` line 476
- **현재**: BotStepIntegrator 실패 시 전체 봇 정지
- **수정**: try/except 래핑 + 핵심 매니저 직접 호출 폴백

#### P2-2. 위협 감지 성능 최적화
- **파일**: `defense_coordinator.py` line 303
- **현재**: 매 프레임 전체 적 유닛 스캔 → 320ms 예산 초과 위험
- **수정**: 5프레임마다 스캔 + 캐시 사용

#### P2-3. 일꾼 재배치 로직 개선
- **파일**: `advanced_worker_optimizer.py`
- **현재**: 포화 초과 일꾼 재배치 지연
- **수정**: surplus_harvesters > 2인 기지에서 < -2인 기지로 즉시 이동

#### P2-4. 오버로드 안전 위치 개선
- **파일**: `overlord_safety_manager.py`
- **현재**: 적 공중 공격에 오버로드 손실 다수
- **수정**: 오버로드를 맵 가장자리/안전 구역으로 분산

#### P2-5. 크립 확장 속도 개선
- **파일**: `creep_expansion_system.py`
- **현재**: 크립 종양 배치 느림
- **수정**: 퀸 크립 분사 우선 → 종양 자동 확장 → 적 방향 우선

#### P2-6. idle 유닛 즉시 할당
- **파일**: `idle_unit_manager.py`
- **현재**: idle 유닛 방치 시간 있음
- **수정**: 매 프레임 idle 체크 → 가장 가까운 집결지/방어선으로 이동

#### P2-7. 스펠 유닛 자동 능력 사용
- **파일**: `spell_unit_manager.py`
- **현재**: 바이퍼, 인페스터 등 스펠 유닛 수동 관리
- **수정**: 자동 능력 사용 (바일 폭탄, 뉴럴, 펑귤 성장)

#### P2-8. 가스 추출기 건설 타이밍
- **파일**: resource_manager.py
- **현재**: 1번째 가스 17드론, 2번째 24드론
- **수정**: 매치업별 조정
  - ZvZ: 1가스 14드론 (빠른 저글링 속도)
  - ZvT: 1가스 17드론 (표준)
  - ZvP: 2가스 20드론 (빠른 레어)

#### P2-9. 건물 파괴 대응
- **파일**: `building_manager.py`
- **현재**: 건물 파괴 시 재건 로직 불명확
- **수정**: 핵심 건물(풀, 레어, 이보챔버) 파괴 시 즉시 재건

#### P2-10. 데이터 캐시 최적화
- **파일**: `data_cache_manager.py`
- **현재**: 매 프레임 계산 반복
- **수정**: 비용 높은 계산 10프레임 캐시

---

### P3 — LOW (품질 향상) [6개]

#### P3-1. 로그 스팸 제거
- **현재**: "CRITICAL THREAT DETECTED!" 초당 수백 번 출력
- **수정**: 동일 메시지 5초 쿨다운

#### P3-2. 게임 결과 상세 로깅
- **현재**: 기본 통계만 기록
- **수정**: 매치업별 상세 (빌드오더, 타임라인, 키 이벤트)

#### P3-3. combat_manager.py 리팩토링
- **현재**: 5,063줄 단일 파일
- **수정**: MicroController, MacroDecisions, ThreatEvaluator로 분리

#### P3-4. 성능 프로파일링 도구
- **현재**: 프레임 타이밍 미측정
- **수정**: 매니저별 on_step 실행 시간 측정 + 320ms 예산 모니터링

#### P3-5. 단위 테스트 확대
- **현재**: 기본 테스트만 존재
- **수정**: 전투 결정, 생산 로직, 확장 타이밍 테스트 추가

#### P3-6. 실시간 대시보드
- **현재**: 로그 파일만 확인 가능
- **수정**: 게임 중 서플라이/자원/위협레벨 실시간 표시

---

## 구현 우선순위 (스프린트 계획)

### Sprint 1 (즉시): P0-1 ~ P0-4 (가스 해결 + EMERGENCY 수정 + 리맥스)
- 예상 승률 변화: 19% → 35%+
- 작업량: ~4시간

### Sprint 2: P0-5 ~ P0-8 (확장 + 서플라이 + 자원관리)
- 예상 승률 변화: 35% → 50%+
- 작업량: ~3시간

### Sprint 3: P1-1 ~ P1-4 (전투력 + 빌드오더)
- 예상 승률 변화: 50% → 65%+
- 작업량: ~5시간

### Sprint 4: P1-5 ~ P1-8 (방어 + 테크)
- 예상 승률 변화: 65% → 75%+
- 작업량: ~4시간

### Sprint 5: P2 전체 (안정성)
- 예상 승률 변화: 75% → 80%+
- 작업량: ~6시간

### Sprint 6: P3 전체 (품질)
- 유지보수성 향상
- 작업량: ~4시간

---

## 매치업별 긴급 수정 사항

### ZvP (현재 8% → 목표 50%)
1. 보이드레이/오라클 러시 대응: 스포어 크롤러 3분 자동 건설
2. 아다 기사단 대응: 히드라 + 코럽터 자동 전환
3. 콜로서스 대응: 바이퍼 자동 생산 + 끌어당기기
4. 프로토스 확장 타이밍 공격: 서플 80에서 바퀴 러시

### ZvT (현재 18% → 목표 50%)
1. 헬리온 러시 대응: 퀸 + 저글링 벽
2. 배틀크루저 대응: 코럽터 자동 전환
3. 메카닉(시즈탱크) 대응: 바퀴 + 불로드 전환
4. 테란 3기지 타이밍: 서플 120에서 공격

### ZvZ (현재 67% → 목표 80%)
1. 12풀 러시 대응 유지
2. 바퀴 전환 속도 개선
3. 가스 관리 강화 (뮤탈 전환 타이밍)

---

## 검증 계획

각 스프린트 완료 후:
1. py_compile 전체 파일 검증
2. pytest 유닛 테스트 통과
3. 20게임 자동 대전 (Easy AI)
   - 매치업별 최소 5게임
   - 승률 계산 + 가스 부유/서플라이 피크 추적
4. 로그 분석으로 개선 효과 정량 측정
