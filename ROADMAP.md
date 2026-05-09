# WickedZergBotPro Grand Roadmap

> 목표: Medium AI 승률 90%+ 달성 & AI Arena 출전
> 현재 상태: Phase 56 완료, 342/342 테스트 통과, 추정 승률 45~50%
> 봇 프레임워크: python-sc2 (burnysc2>=5.0.0)

---

## 프로젝트 컨텍스트

- 저그 종족 전용 봇 (WickedZergBotPro)
- 핵심 아키텍처: FSM(GamePhase EARLY/MID/LATE) + Manager Registry + Blackboard 패턴
- 하이브리드 구조: 95% 규칙 기반 + 5% RL(PPO/IMPALA)
- `UnitTypeId.LURKER`는 python-sc2에 없음 → 반드시 `UnitTypeId.LURKERMP` 사용
- HP 가중 전투력 계산: `sum(unit.health + unit.shield)` (단순 카운트 금지)
- AI Arena 제한: 프레임당 320ms 이내
- 매니저 파일 위치: `wicked_zerg_challenger/` 하위

---

## Sprint 1: 긴급 수정 (즉시 착수)

### Task 1.1: 인코딩 에러 완전 제거

**파일 목록:**
- `wicked_zerg_challenger/early_defense_system.py`
- `wicked_zerg_challenger/build_order_executor.py`
- 기타 비ASCII 특수문자가 포함된 모든 .py 파일

**구현 지시:**
1. `wicked_zerg_challenger/` 전체에서 비ASCII 특수문자 검색 (예: ⚪, ✓, ✅, 🔴, ❌ 등)
2. 모든 특수문자를 ASCII 대체 문자로 교체:
   - ⚪ → `[O]`, ✓/✅ → `[OK]`, ❌ → `[X]`, 🔴 → `[!]`
3. 한글 로그 메시지는 유지하되, print/logger 호출에 encoding 안전성 확보
4. 검증: `python -m py_compile <파일>` 로 전체 파일 컴파일 확인

---

### Task 1.2: 일꾼 괴롭힘 방어 응답 구현

**파일:** `wicked_zerg_challenger/combat_manager.py`

**현재 문제:** 일꾼 괴롭힘을 감지하지만 응답 로직이 없음

**구현 지시:**
1. `combat_manager.py`에 `async def respond_to_worker_harassment(self)` 메서드 추가
2. 로직:
   - 각 `self.bot.townhalls.ready`를 순회
   - 기지 반경 15 이내 적 공격 유닛 감지: `self.bot.enemy_units.filter(lambda u: u.distance_to(base) < 15 and u.can_attack)`
   - 위협 존재 시:
     - 일꾼 3:1 비율 풀: `min(enemy_threats.amount * 3, local_workers.amount)`
     - 퀸 즉각 투입: `self.bot.units(UnitTypeId.QUEEN).closer_than(20, base)`
   - 위협 소멸 시:
     - 전투 중인 일꾼(`w.is_attacking`)을 가장 가까운 미네랄로 복귀
3. `on_step` 또는 주 루프에서 매 22 iteration(1초)마다 호출
4. 테스트: `tests/` 에 `test_worker_harassment_defense.py` 추가

---

### Task 1.3: 견제 유닛 도달 보장 + 복귀 로직

**파일:**
- `wicked_zerg_challenger/strategy_manager.py` (228-262 라인 부근)
- `wicked_zerg_challenger/combat_manager.py`

**현재 문제:** 견제 신호만 전송하고 유닛이 실제로 적 본진에 도달하는지 확인하지 않음

**구현 지시:**
1. 견제 유닛에 태그 시스템 추가 (unit.tag을 set으로 관리):
   ```python
   self.harass_units: Set[int] = set()
   ```
2. 견제 배정된 유닛이 적 본진 반경 20 이내에 도달했는지 매 프레임 확인
3. 도달 후 행동:
   - 적 일꾼(PROBE/SCV/DRONE) 우선 공격
   - 킬 카운트 추적: `self.harass_kill_count: int = 0`
   - 3킬 이상 또는 아군 HP 50% 이하 시 복귀
4. 복귀 로직: 가장 가까운 아군 기지로 move → 도착 후 harass_units에서 제거
5. 견제 주기: 30초 → 15초로 단축 (strategy_manager.py의 관련 상수 수정)
6. 테스트 추가

---

### Task 1.4: 1분 멀티 타이밍 검증 및 최적화

**파일:** `wicked_zerg_challenger/economy_manager.py` (882-895 라인 부근)

**현재 문제:** 미네랄 300 즉시 확장 로직이 있으나 실제 6분에 첫 멀티

**구현 지시:**
1. 확장 타이밍 로그 추가:
   ```python
   if new_expansion_started:
       logger.info(f"[EXPANSION] First expansion at {self.bot.time:.1f}s")
   ```
2. 초반 빌드 오더 최적화:
   - 13드론 → 오버로드 → 17드론 → 해처리 (내추럴)
   - 해처리 건설 시점: 게임 시간 50~70초 목표
3. 확장 위치 선정: `self.bot.expansion_locations_list`에서 시작 위치에 가장 가까운 곳 우선
4. 미네랄 300 도달 전에도 내추럴이 비어있으면 즉시 확장 시도
5. 검증: `run_single_game.py`로 3판 실행, 확장 시점 로그 확인

---

## Sprint 2: 정찰 & 인텔 강화 (1~2주)

### Task 2.1: 오버로드 정찰 주기 단축

**파일:** `wicked_zerg_challenger/scouting_system.py`

**구현 지시:**
1. 정찰 주기 상수 정의 (기존 30초 → 15초):
   ```python
   OVERLORD_SCOUT_INTERVAL_EARLY = 15   # 초반 (0~5분)
   OVERLORD_SCOUT_INTERVAL_MID = 30     # 중반 (5~10분)
   ```
2. 오버로드 정찰 웨이포인트 시스템:
   - 1순위: 적 본진 입구
   - 2순위: 적 내추럴
   - 3순위: 적 3번째 확장 후보지
3. 오버로드 사망 시 다음 오버로드로 자동 교체
4. Blackboard에 정찰 결과 기록: `self.blackboard.set("enemy_base_scouted", True)`

---

### Task 2.2: 저글링 맵 순찰 루트

**파일:** `wicked_zerg_challenger/scouting_system.py`

**구현 지시:**
1. `self.bot.expansion_locations_list`를 활용한 순찰 웨이포인트 자동 생성
2. 45초마다 저글링 1~2마리를 순찰에 배정
3. 순찰 순서: 적 3rd → 4th → 맵 중앙 → 워치타워 순환
4. 적 건물/유닛 발견 시 Blackboard에 즉시 보고:
   ```python
   self.blackboard.set("enemy_expansion_spotted", position)
   ```
5. 순찰 저글링 사망 시 다음 idle 저글링으로 자동 교체

---

### Task 2.3: 적 빌드 오더 인식 확장 (12 → 25개)

**파일:** `wicked_zerg_challenger/intel_manager.py`

**구현 지시:**
추가할 13개 빌드 패턴 (감지 조건 포함):

```python
BUILD_PATTERNS = {
    # 테란
    "proxy_barracks": {"condition": "Barracks near our base before 3:00", "response": "EMERGENCY"},
    "2_1_1_medivac_drop": {"condition": "2 Barracks + 1 Factory + 1 Starport before 5:00", "response": "base_defense"},
    "battlecruiser_rush": {"condition": "Fusion Core before 8:00", "response": "corruptor_production"},
    "mech_transition": {"condition": "2+ Factory + Armory", "response": "roach_ravager"},
    "widow_mine_drop": {"condition": "Factory + Starport + no Reactor on Starport", "response": "overseer_detection"},
    # 프로토스
    "cannon_rush": {"condition": "Forge + Pylon near our base before 3:00", "response": "EMERGENCY"},
    "dt_rush": {"condition": "Dark Shrine before 6:00", "response": "overseer_spore"},
    "void_ray_rush": {"condition": "Stargate + 2+ VoidRay before 6:00", "response": "hydra_queen"},
    "immortal_allin": {"condition": "Robo + no expansion by 5:00", "response": "EMERGENCY"},
    "archon_transition": {"condition": "Templar Archives + 3+ HighTemplar", "response": "spread_units"},
    # 저그
    "ling_rush": {"condition": "Spawning Pool before 1:30 + no expansion", "response": "EMERGENCY"},
    "muta_rush": {"condition": "Spire before 6:00", "response": "hydra_spore"},
    "nydus_rush": {"condition": "Nydus Network before 5:00", "response": "base_defense"},
}
```

각 패턴에 대해:
1. 감지 함수 구현
2. Blackboard에 감지 결과 기록
3. strategy_manager에서 대응 전략 자동 전환
4. 유닛 테스트 추가

---

### Task 2.4: 공중 위협 조기 경보

**파일:** `wicked_zerg_challenger/intel_manager.py`

**구현 지시:**
1. 스타포트/스타게이트 탐지 시 Blackboard에 `AIR_THREAT_INCOMING` 플래그 설정
2. strategy_manager에서 플래그 감지 → 코럽터 또는 히드라 생산 전환:
   ```python
   if self.blackboard.get("AIR_THREAT_INCOMING"):
       if self.bot.structures(UnitTypeId.HYDRALISKDEN).ready:
           # 히드라 우선
       else:
           # 스포어 크롤러 + 퀸 방어
   ```
3. 공중 유닛 실제 출현 시 `AIR_THREAT_ACTIVE`로 업그레이드

---

### Task 2.5: 오버시어 은폐 탐지 자동화

**파일:** `wicked_zerg_challenger/scouting_system.py`

**구현 지시:**
1. 은폐 유닛 목록 정의:
   ```python
   CLOAK_UNITS = {UnitTypeId.DARKTEMPLAR, UnitTypeId.BANSHEE, UnitTypeId.LURKERMP, UnitTypeId.WIDOWMINE, UnitTypeId.GHOST}
   ```
2. 은폐 유닛 탐지 또는 은폐 테크 건물 탐지 시:
   - 오버시어 1기를 해당 위치로 이동
   - 오버시어가 없으면 오버로드 변태 예약
3. 각 기지에 오버시어 1기 배치 목표
4. 체인질링 자동 배포: 에너지 50 이상 시 적 기지 방향으로 체인질링 생성

---

## Sprint 3: 경제 & 매크로 최적화 (2주)

### Task 3.1: 드론/병력 밸런스 동적 조절

**파일:** `wicked_zerg_challenger/economy_manager.py`, `wicked_zerg_challenger/local_training/economy_combat_balancer.py`

**구현 지시:**
1. 위협 레벨 enum 정의:
   ```python
   class ThreatLevel(Enum):
       LOW = "low"          # 드론 목표: 66
       MEDIUM = "medium"    # 드론 목표: 55
       HIGH = "high"        # 드론 목표: 44
       CRITICAL = "critical" # 드론 생산 중단
   ```
2. intel_manager의 적 병력 크기 + 접근 거리로 위협 레벨 결정
3. economy_manager에서 위협 레벨에 따라 드론 목표치 동적 조정
4. economy_combat_balancer.py의 밸런싱 로직을 실전 on_step에 연동

---

### Task 3.2: 가스 타이밍 매치업별 최적화

**파일:** `wicked_zerg_challenger/economy_manager.py`

**구현 지시:**
```python
def _get_gas_timing_by_matchup(self) -> int:
    """매치업별 최적 가스 채취 시작 드론 수"""
    enemy_race = self.bot.enemy_race
    if enemy_race == Race.Zerg:
        return 13   # 즉가스 → 저글링 스피드
    elif enemy_race == Race.Terran:
        return 17   # 빠른 가스 → 바퀴
    elif enemy_race == Race.Protoss:
        return 19   # 중간 가스 → 히드라
    return 16       # 랜덤 대응
```
가스 채취 시작 로직에서 이 함수를 호출하도록 수정.

---

### Task 3.3: 라바 우선순위 시스템

**파일:** `wicked_zerg_challenger/economy_manager.py`

**구현 지시:**
```python
async def spend_larva(self):
    """라바 사용 우선순위: 오버로드 > 드론 > 병력"""
    larva = self.bot.larva
    if not larva:
        return
    
    # 1순위: 서플라이 블록 방지
    if self.bot.supply_left < 3 and self.bot.supply_cap < 200:
        if not self.bot.already_pending(UnitTypeId.OVERLORD):
            if self.bot.can_afford(UnitTypeId.OVERLORD):
                larva.random.train(UnitTypeId.OVERLORD)
                return
    
    # 2순위: 드론 (위협 레벨에 따라)
    target_drones = self._get_target_drone_count()
    if self.bot.workers.amount < target_drones:
        if self.bot.can_afford(UnitTypeId.DRONE):
            larva.random.train(UnitTypeId.DRONE)
            return
    
    # 3순위: 병력 생산
    await self._produce_army_units(larva)
```

---

### Task 3.4: 미네랄 플로팅 방지

**파일:** `wicked_zerg_challenger/economy_manager.py`

**구현 지시:**
1. 미네랄 > 800 시 매크로 해처리 자동 건설 트리거
2. 미네랄 > 1000 시 즉시 병력 덤프 (라바가 있으면 전부 군사 유닛으로)
3. 라바 부족 감지: `larva.amount == 0 and minerals > 500` → 해처리 추가 건설
4. 로그: `logger.warning(f"[FLOAT] Minerals floating: {self.bot.minerals}")`

---

## Sprint 4: 전투 & 마이크로 고도화 (3~4주)

### Task 4.1: 러커 포지셔닝 마이크로

**파일:** `wicked_zerg_challenger/combat/micro_combat.py`

**구현 지시:**
1. `terrain_analysis.py`에서 초크포인트/램프 위치 가져오기
2. **반드시 `UnitTypeId.LURKERMP` 사용** (LURKER 아님!)
3. 러커 행동 로직:
   ```python
   for lurker in self.bot.units(UnitTypeId.LURKERMP):
       if not lurker.is_burrowed:
           # 가장 가까운 초크포인트로 이동
           choke = self._nearest_choke(lurker.position)
           if lurker.distance_to(choke) < 3:
               lurker(AbilityId.BURROWDOWN_LURKER)
           else:
               lurker.move(choke)
       else:
           # 매설 상태: 적이 사거리 밖으로 우회하면 언버로우
           enemies_nearby = self.bot.enemy_units.closer_than(9, lurker)
           if not enemies_nearby:
               enemies_far = self.bot.enemy_units.closer_than(20, lurker)
               if enemies_far:
                   lurker(AbilityId.BURROWUP_LURKER)
   ```

---

### Task 4.2: 뮤탈리스크 히트앤런

**파일:** `wicked_zerg_challenger/combat/mutalisk_micro.py`

**구현 지시:**
1. 매직박싱: 뮤탈 그룹을 한 점에 스택 → 동시 공격
2. 바운스 공격: 밀집 지역의 유닛 우선 타겟 (바운스 데미지 극대화)
3. 대공 유닛 회피:
   ```python
   ANTI_AIR_THREATS = {UnitTypeId.THOR, UnitTypeId.ARCHON, UnitTypeId.QUEEN, UnitTypeId.MARINE, UnitTypeId.HYDRALISK}
   # 대공 유닛 사거리 + 2 이내 접근 시 반대 방향으로 후퇴
   ```
4. HP 50% 이하 뮤탈 자동 후퇴 → 아군 기지 근처에서 재생

---

### Task 4.3: 바퀴-히드라 연합 포메이션

**파일:** `wicked_zerg_challenger/combat_manager.py`

**구현 지시:**
1. 공격 이동 시 바퀴를 전열(적 방향), 히드라를 후열(바퀴 뒤 사거리 6 이내)에 배치
2. 후퇴 시 히드라 우선 후퇴 → 바퀴가 rear guard
3. 구현: 공격 목표 지점에서 바퀴는 목표를 향해, 히드라는 목표에서 6만큼 뒤에서 a-move

---

### Task 4.4: 다방면 협공 시스템

**파일:** `wicked_zerg_challenger/combat_manager.py`

**구현 지시:**
1. 총 병력 60+ 시 2~3개 그룹으로 분할
2. 각 그룹에 서로 다른 공격 경로 할당 (정면, 좌측, 우측 또는 너드웜 후방)
3. 동시 도착을 위해 거리 역산 → 먼 그룹 먼저 출발
4. 그룹 크기: 메인 60%, 서브1 25%, 서브2 15%

---

### Task 4.5: 전투 프레임 스킵

**파일:** `wicked_zerg_challenger/combat_manager.py`

**구현 지시:**
```python
async def manage_combat(self, iteration):
    # 전투 중이 아니면 5프레임 스킵
    if not self._is_in_active_combat():
        if iteration % 5 != 0:
            return
    # 전투 중이지만 긴급 아니면 2프레임 스킵
    elif not self._is_emergency():
        if iteration % 2 != 0:
            return
    # 긴급 상황: 매 프레임
    await self._execute_combat()
```

---

## Sprint 5: 방어 체계 강화 (2주)

### Task 5.1: 프록시 배럭/캐논 대응

**파일:** `wicked_zerg_challenger/early_defense_system.py`, `wicked_zerg_challenger/strategy_manager.py`

**구현 지시:**
1. 150초 이내 아군 기지 반경 40에 적 건물 탐지 시 EMERGENCY 모드
2. 대응:
   - 스파인 크롤러 1~2개 즉시 건설 (본진 입구 방향)
   - 드론 6마리 풀 → 적 건물 공격
   - 저글링 즉시 생산 (모든 라바 사용)
3. 적 건물 파괴 확인 후 NORMAL 모드 복귀

---

### Task 5.2: 멀티 드롭 대응

**파일:** `wicked_zerg_challenger/combat/base_defense.py`

**구현 지시:**
1. 각 기지에 퀸 1기 + 저글링 4기 상시 수비 배치
2. 드롭 유닛(MEDIVAC, WARPPRISM, OVERLORDTRANSPORT) 감지 시:
   - 해당 기지의 수비대 즉각 공격 명령
   - 가장 가까운 주력 병력에서 소수(8~12기) 분리 파견
3. 공중 하라스 2회 이상 시 스포어 크롤러 자동 건설

---

### Task 5.3: 올인 감지 & 대응

**파일:** `wicked_zerg_challenger/strategy_manager.py`, `wicked_zerg_challenger/intel_manager.py`

**구현 지시:**
1. 올인 감지 조건:
   - 적 확장 없음 (5분 이후 기준)
   - 적 병력이 대규모로 접근 중 (combat power 비율 1.5x 이상)
2. 올인 감지 시:
   - 드론 생산 즉시 중단
   - 스파인 크롤러 3~4개 급조 (본진/내추럴 입구)
   - 모든 라바 → 병력 전환
   - 퀸 전원 방어 투입 (인젝트 중단)

---

## Sprint 6: RL 실전 투입 (3~4주)

### Task 6.1: PPO 에이전트 실전 연동

**파일:** `wicked_zerg_challenger/local_training/rl_agent.py`, `wicked_zerg_challenger/combat_manager.py`

**구현 지시:**
1. combat_manager에 RL 토글 추가:
   ```python
   self.use_rl_micro = False  # 기본 off
   ```
2. 전투 상황(적 5기+ 근접) 감지 시 RL 추론 호출
3. 추론 타임아웃: 50ms 이내 (초과 시 규칙 기반 fallback)
4. 관찰 공간 16D, 행동 공간 7개 이산 행동
5. RL 결과가 규칙 기반보다 나쁘면 자동으로 규칙 기반으로 복귀

---

### Task 6.2: 커리큘럼 학습 Stage 3 완성

**파일:** `wicked_zerg_challenger/local_training/hierarchical_rl/improved_hierarchical_rl.py`

**구현 지시:**
1. Stage 3 = 매크로(Stage 1) + 전투(Stage 2) 통합
2. 보상 함수:
   - 승리: +10, 패배: -10
   - 적 유닛 처치: +0.1 per unit
   - 자원 수집량: +0.01 per 100 minerals
   - 서플라이 블록: -0.5 per occurrence
3. Stage 1/2 가중치를 Stage 3 초기값으로 사용 (transfer learning)

---

### Task 6.3: 셀프 플레이 파이프라인

**파일:** `wicked_zerg_challenger/local_training/training_pipeline.py`

**구현 지시:**
1. 매 50 에피소드마다 현재 모델 체크포인트 저장
2. 상대 풀: 최근 10개 체크포인트 + 규칙 기반 봇
3. ELO 레이팅:
   ```python
   def update_elo(winner_elo, loser_elo, k=32):
       expected = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
       new_winner = winner_elo + k * (1 - expected)
       new_loser = loser_elo + k * (0 - (1 - expected))
       return new_winner, new_loser
   ```
4. 상대 선택: ELO 차이 200 이내에서 랜덤 매칭

---

## Sprint 7: 아키텍처 리팩토링 (2~3주)

### Task 7.1: StrategyManager 역할 분담

**파일:** `wicked_zerg_challenger/strategy_manager.py`

**구현 지시:**
1. 신규 `wicked_zerg_challenger/building_manager.py` 생성:
   - 건물 건설 위치 결정 로직 이동
   - 건물 건설 큐 관리
2. 일꾼 배정 로직 → `economy_manager.py`로 이동
3. strategy_manager.py에는 전략 결정(NORMAL/EMERGENCY/AGGRESSIVE/DEFENSIVE/ALL_IN) 로직만 유지
4. ManagerFactory에 BuildingManager 등록
5. **검증: 기존 342개 테스트 전체 통과 필수**

---

### Task 7.2: 거리 계산 캐싱

**파일:** `wicked_zerg_challenger/combat_manager.py`, `wicked_zerg_challenger/economy_manager.py`

**구현 지시:**
```python
# utils/distance_cache.py 신규 생성
class DistanceCache:
    def __init__(self):
        self._cache: Dict[tuple, float] = {}
        self._frame: int = -1
    
    def get(self, pos_a, pos_b, current_frame: int) -> float:
        if current_frame != self._frame:
            self._cache.clear()
            self._frame = current_frame
        key = (round(pos_a.x, 1), round(pos_a.y, 1), round(pos_b.x, 1), round(pos_b.y, 1))
        if key not in self._cache:
            self._cache[key] = pos_a.distance_to(pos_b)
        return self._cache[key]
```
모든 매니저에서 빈번한 distance_to 호출을 이 캐시로 교체.

---

### Task 7.3: 매직넘버 → GameConstants 교체

**파일:** 전체 매니저 파일

**구현 지시:**
1. `utils/game_constants.py`의 기존 상수 클래스 활용
2. 전체 `wicked_zerg_challenger/` 에서 하드코딩된 iteration 주기 숫자(11, 22, 33, 66, 110, 220 등)를 검색
3. `GameFrequencies.EVERY_HALF_SECOND`, `EVERY_SECOND`, `EVERY_3_SECONDS` 등으로 교체
4. 경제 상수(드론 목표 66, 미네랄 300 등)도 `EconomyConstants`로 교체

---

## Sprint 8: QA & AI Arena 배포 (2~3주)

### Task 8.1: Medium AI 30연전 테스트

**실행:**
```bash
cd wicked_zerg_challenger
# ZvT 10판
python run_mass_test.py --opponent Terran --difficulty Medium --games 10
# ZvP 10판
python run_mass_test.py --opponent Protoss --difficulty Medium --games 10
# ZvZ 10판
python run_mass_test.py --opponent Zerg --difficulty Medium --games 10
```
**목표:** 크래시 0회, 전체 승률 90%+

---

### Task 8.2: AI Arena 패키지 최종 검증

**파일:** `create_arena_package.py`

**체크리스트:**
- [ ] `python create_arena_package.py` 실행 성공
- [ ] 생성된 ZIP 파일 10MB 미만
- [ ] 320ms/step 타임아웃 준수 (프로파일링 확인)
- [ ] python-sc2 외 외부 의존성 없음 (또는 번들 포함)
- [ ] ZvT, ZvP, ZvZ 전부 정상 동작
- [ ] 에러 시 graceful degradation (크래시 대신 기본 행동)
- [ ] 3개 이상 맵에서 정상 동작

---

## 장기 비전

1. Elite AI 승률 50%+ 달성
2. AI Arena 래더 등록 및 실전 데이터 수집
3. MCTS/AlphaZero 장기 전략 플래닝 실험
4. TensorRT 추론 가속 (FPS +15%)
5. Rust 가속 모듈 확장 (combat power, pathfinding)
6. 드론 스웜 알고리즘 연구 → 광주 드론 ATC 비전

---

## 파일 맵 요약

```
wicked_zerg_challenger/
├── strategy_manager.py         # Sprint 1.3, 5.1, 5.3, 7.1
├── economy_manager.py          # Sprint 1.4, 3.x
├── combat_manager.py           # Sprint 1.2, 4.x, 6.1
├── intel_manager.py            # Sprint 2.3, 2.4, 5.3
├── scouting_system.py          # Sprint 2.1, 2.2, 2.5
├── early_defense_system.py     # Sprint 1.1, 5.1
├── build_order_executor.py     # Sprint 1.1
├── creep_manager.py            # Sprint 5.4
├── building_manager.py         # Sprint 7.1 (신규 생성)
├── combat/
│   ├── micro_combat.py         # Sprint 4.1, 4.5
│   ├── mutalisk_micro.py       # Sprint 4.2
│   ├── base_defense.py         # Sprint 5.2
│   └── terrain_analysis.py     # Sprint 4.1
├── local_training/
│   ├── rl_agent.py             # Sprint 6.1
│   ├── training_pipeline.py    # Sprint 6.3
│   └── hierarchical_rl/       # Sprint 6.2
└── utils/
    ├── game_constants.py       # Sprint 7.3
    └── distance_cache.py       # Sprint 7.2 (신규 생성)
```
