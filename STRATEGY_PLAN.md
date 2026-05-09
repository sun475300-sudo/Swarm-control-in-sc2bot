# WickedZergBotPro 매치업별 전략 구현 계획서

> ROADMAP.md의 보조 문서 — 매치업별 빌드오더, 유닛 구성, 마이크로 전략에 집중
> 현재 상태: 기본 카운터 로직(strategy_manager.py) 구현됨, 세부 매치업 전략 미완성
> 핵심 파일: strategy_manager.py, build_order_system.py, intel_manager.py, combat/ 디렉토리

---

## 프로젝트 컨텍스트

### 현재 구현된 매치업 로직
- build_order_system.py: 종족별 빌드 선택 (vs P: ROACH_RUSH, vs T: HATCH_FIRST_16, vs Z: SAFE_14POOL)
- strategy_manager.py: `_counter_terran_units()`, `_counter_protoss_units()`, `_counter_zerg_units()` 존재
- upgrade_manager.py: 종족별 업그레이드 우선순위 가중치 존재
- racial_counter_manager.py: 중앙 카운터 디스패치 존재
- strategy_config.json: counter_build 섹션에 JSON 기반 카운터 설정 존재

### 현재 누락된 것
- 매치업별 마이크로 조정 (전투 마이크로가 유닛 타입 기반이고 종족 기반이 아님)
- 종족별 치즈 대응 분기 (일반적인 러시 감지만 있음)
- 매치업별 정찰 우선순위 (스타게이트 vs 팩토리 확인 등)
- 동적 가스 타이밍 조정 (감지된 빌드에 따른 적응)
- 매치업별 빌드오더 다양화 (현재 종족당 1개만)

### 주의사항
- `UnitTypeId.LURKER`는 python-sc2에 없음 → 반드시 `UnitTypeId.LURKERMP` 사용
- HP 가중 전투력 계산 사용 (단순 유닛 수 금지)
- AI Arena 320ms/step 제한 준수
- bot.do() 래핑 필수

---

## Phase 1: ZvT (저그 vs 테란) 전략 완성

### Task 1.1: ZvT 빌드오더 3종 구현

**파일:** `wicked_zerg_challenger/build_order_system.py`

**현재:** vs Terran = HATCH_FIRST_16 (1가지만)

**추가할 빌드오더 3종:**

```python
ZVT_BUILDS = {
    "hatch_first_16": {
        "name": "16 해처리 (기본 매크로)",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),  # 내추럴
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (20, UnitTypeId.QUEEN),      # 본진
            (20, UnitTypeId.QUEEN),      # 내추럴
            (20, UnitTypeId.ZERGLING),   # 2마리 (정찰용)
            (24, "METABOLIC_BOOST"),     # 저글링 스피드
            (30, UnitTypeId.ROACHWARREN),
        ],
        "transition": "roach_hydra_mid",
        "note": "안전한 매크로 오프닝. 배럭 1개 확인 후 사용"
    },
    "aggressive_pool_first": {
        "name": "14 풀 어그로",
        "condition": "enemy_proxy_detected OR enemy_one_base",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (18, UnitTypeId.ZERGLING),   # 6마리 (견제)
            (22, "METABOLIC_BOOST"),
        ],
        "transition": "ling_bane_mid",
        "note": "적이 1베이스 공격 빌드일 때 대응. 저글링 6기로 견제"
    },
    "fast_lair_macro": {
        "name": "빠른 레어 매크로",
        "condition": "enemy_expand_confirmed AND no_aggression",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (21, UnitTypeId.QUEEN),
            (24, "METABOLIC_BOOST"),
            (30, UnitTypeId.LAIR),       # 빠른 레어
            (38, UnitTypeId.HYDRALISKDEN),
            (44, UnitTypeId.HATCHERY),   # 3rd
        ],
        "transition": "hydra_lurker_late",
        "note": "적이 안전하게 확장했을 때 테크 앞서기"
    }
}
```

**빌드 선택 로직:**
```python
def _select_zvt_build(self) -> str:
    if self.blackboard.get("enemy_proxy_detected"):
        return "aggressive_pool_first"
    if self.blackboard.get("enemy_expand_confirmed") and not self.blackboard.get("enemy_aggression"):
        return "fast_lair_macro"
    return "hatch_first_16"
```

---

### Task 1.2: ZvT 유닛 구성 로드맵 구현

**파일:** `wicked_zerg_challenger/strategy_manager.py`

**구현 지시 — 시간대별 목표 유닛 구성:**

```python
ZVT_COMPOSITION_TIMELINE = {
    "early": {  # 0~5분
        "default": {"zergling": 0.60, "queen": 0.30, "roach": 0.10},
        "vs_hellion": {"queen": 0.30, "roach": 0.50, "zergling": 0.20},
        "vs_reaper": {"zergling": 0.70, "queen": 0.30},
    },
    "mid": {  # 5~10분
        "vs_bio": {"baneling": 0.25, "zergling": 0.30, "roach": 0.15, "hydra": 0.20, "ravager": 0.10},
        "vs_mech": {"ravager": 0.30, "roach": 0.25, "hydra": 0.25, "swarmhost": 0.10, "zergling": 0.10},
        "vs_air": {"hydra": 0.35, "corruptor": 0.25, "queen": 0.15, "roach": 0.15, "zergling": 0.10},
    },
    "late": {  # 10분+
        "vs_bio": {"ultralisk": 0.30, "zergling": 0.25, "baneling": 0.20, "hydra": 0.15, "viper": 0.10},
        "vs_mech": {"broodlord": 0.25, "corruptor": 0.20, "viper": 0.15, "ravager": 0.20, "hydra": 0.20},
        "vs_bc": {"corruptor": 0.40, "hydra": 0.25, "viper": 0.15, "queen": 0.10, "infestor": 0.10},
    }
}
```

**적용 방법:**
1. intel_manager에서 적 구성 분류 (bio/mech/air)
2. 게임 시간으로 시간대 결정
3. 해당 유닛 비율을 strategy_manager의 production ratio에 반영

---

### Task 1.3: ZvT 마이크로 조정

**파일:** `wicked_zerg_challenger/combat/micro_combat.py`

**구현 지시:**

```python
class ZvTMicroAdjustments:
    """테란 상대 마이크로 조정"""
    
    # 시즈 탱크 대응: 서라운드 + 바일
    async def handle_siege_tanks(self, own_units, enemy_tanks):
        """탱크가 시즈 모드일 때 양쪽에서 서라운드"""
        for tank in enemy_tanks:
            if tank.type_id == UnitTypeId.SIEGETANKSIEGED:
                # 저글링: 탱크 사각지대(최소 사거리 2 이내)로 돌진
                zerglings = own_units(UnitTypeId.ZERGLING).closer_than(15, tank)
                for ling in zerglings:
                    ling.move(tank.position.towards(ling.position, 1.5))
                
                # 레이저: 바일 조준
                ravagers = own_units(UnitTypeId.RAVAGER).closer_than(9, tank)
                for rav in ravagers:
                    rav(AbilityId.EFFECT_CORROSIVEBILE, tank.position)
    
    # 마린 볼 대응: 베인 폭탄
    async def handle_marine_ball(self, own_units, enemy_marines):
        """마린 6기 이상 뭉쳐있으면 베인 돌진"""
        clumps = self._find_unit_clumps(enemy_marines, radius=3.0, min_count=6)
        for clump_center in clumps:
            banelings = own_units(UnitTypeId.BANELING).closest_n_units(clump_center, 4)
            for bane in banelings:
                bane.attack(clump_center)
    
    # 메디팩 드롭 대응
    async def handle_medivac_drop(self, base, medivacs):
        """메디팩 감지 시 퀸 + 히드라 집중"""
        queens = self.bot.units(UnitTypeId.QUEEN).closer_than(20, base)
        for queen in queens:
            queen.attack(medivacs.closest_to(queen))
        hydras = self.bot.units(UnitTypeId.HYDRALISK).closer_than(25, base)
        for hydra in hydras:
            hydra.attack(medivacs.closest_to(hydra))
    
    # 위도우마인 대응
    async def handle_widow_mines(self, own_units, detected_mines):
        """위도우마인 감지 시 1유닛씩 트리거"""
        if detected_mines:
            # 저글링 1마리를 마인 위로 보내 트리거
            expendable = own_units(UnitTypeId.ZERGLING).closest_to(detected_mines.first)
            if expendable:
                expendable.attack(detected_mines.first.position)
```

---

### Task 1.4: ZvT 정찰 우선순위

**파일:** `wicked_zerg_challenger/scouting_system.py`

**구현 지시:**
```python
ZVT_SCOUT_PRIORITIES = {
    "early": [  # 0~3분
        "enemy_natural",          # 확장 여부 확인
        "enemy_main_ramp",        # 배럭 위치 + 수
        "enemy_gas_count",        # 가스 채취 여부 → 팩토리/테크랩 예측
    ],
    "mid": [  # 3~8분
        "factory_count",          # 팩토리 수 → 메카닉 전환 감지
        "starport_existence",     # 스타포트 → 메디팩/밴시/리버레이터
        "armory_existence",       # 아머리 → 토르/배틀크루저 예측
        "tech_lab_vs_reactor",    # 테크랩(마라우더) vs 리액터(마린)
    ],
    "late": [  # 8분+
        "fusion_core",            # 퓨전코어 → 배틀크루저
        "ghost_academy",          # 고스트 아카데미 → EMP/핵
        "planetary_fortress",     # 행성 요새 → 거북이 전술
    ]
}
```

각 정찰 목표에 대해:
1. 오버로드/저글링을 해당 위치로 이동
2. 건물 발견 시 Blackboard에 기록
3. strategy_manager에서 빌드/유닛 구성 자동 전환

---

## Phase 2: ZvP (저그 vs 프로토스) 전략 완성

### Task 2.1: ZvP 빌드오더 3종 구현

**파일:** `wicked_zerg_challenger/build_order_system.py`

**현재:** vs Protoss = ROACH_RUSH (1가지만)

**추가할 빌드오더:**

```python
ZVP_BUILDS = {
    "roach_rush": {
        "name": "바퀴 러시 (기본)",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (20, UnitTypeId.QUEEN),
            (22, UnitTypeId.ROACHWARREN),
            (24, "METABOLIC_BOOST"),
            (28, UnitTypeId.ROACH),  # 바퀴 6기 생산 시작
        ],
        "transition": "roach_ravager_push",
        "note": "게이트웨이 확장 상대에게 바퀴 타이밍 푸시"
    },
    "ling_flood_anti_cannon": {
        "name": "저글링 플러드 (캐논 러시 대응)",
        "condition": "enemy_cannon_rush_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),  # 빠른 풀
            (14, UnitTypeId.HATCHERY),
            (16, UnitTypeId.QUEEN),
            (16, UnitTypeId.ZERGLING),  # 즉시 저글링 대량 생산
            (20, "METABOLIC_BOOST"),
        ],
        "transition": "ling_bane_nydus",
        "note": "캐논 러시 감지 시 빠른 풀 + 저글링으로 포지 제거"
    },
    "hydra_lair_macro": {
        "name": "히드라 레어 매크로",
        "condition": "enemy_stargate_detected OR enemy_robo_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (16, UnitTypeId.HATCHERY),
            (18, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.SPAWNINGPOOL),
            (19, UnitTypeId.QUEEN),
            (21, UnitTypeId.QUEEN),
            (24, "METABOLIC_BOOST"),
            (28, UnitTypeId.EXTRACTOR),  # 2가스
            (30, UnitTypeId.LAIR),
            (36, UnitTypeId.HYDRALISKDEN),
            (38, UnitTypeId.HATCHERY),  # 3rd
            (44, UnitTypeId.EXTRACTOR),
            (44, UnitTypeId.EXTRACTOR),
        ],
        "transition": "hydra_lurker_viper",
        "note": "스타게이트/로보 감지 시 빠른 레어 + 히드라"
    }
}
```

---

### Task 2.2: ZvP 핵심 카운터 로직 강화

**파일:** `wicked_zerg_challenger/strategy_manager.py`

**현재 누락된 카운터 추가:**

```python
ZVP_COUNTER_RULES = {
    # 프로토스 주요 위협별 대응
    "disruptor_nova": {
        "detection": "UnitTypeId.DISRUPTOR in enemy_units",
        "response": {
            "composition": {"zergling": 0.30, "mutalisk": 0.30, "roach": 0.20, "ravager": 0.20},
            "micro": "SPREAD_ON_NOVA",  # 디스럽터 노바 감지 시 유닛 분산
            "note": "빠른 유닛으로 디스럽터 우회. 노바 쿨다운 동안 돌진"
        }
    },
    "storm_templar": {
        "detection": "UnitTypeId.HIGHTEMPLAR count >= 2",
        "response": {
            "composition": {"zergling": 0.40, "ravager": 0.30, "roach": 0.15, "viper": 0.15},
            "micro": "SPLIT_ON_STORM",  # 사이오닉 폭풍 감지 시 분산
            "note": "저글링 서라운드로 하이템플러 제거. 바이퍼 어브덕트"
        }
    },
    "warp_prism_harass": {
        "detection": "UnitTypeId.WARPPRISM in enemy_units near our bases",
        "response": {
            "composition": {"queen": 0.25, "hydra": 0.35, "zergling": 0.40},
            "micro": "FOCUS_PRISM",  # 워프프리즘 우선 격추
            "note": "워프프리즘 격추가 최우선. 퀸 + 히드라 집중"
        }
    },
    "blink_stalker_allin": {
        "detection": "Stalker count >= 8 AND no enemy expansion by 5:00",
        "response": {
            "composition": {"roach": 0.40, "ravager": 0.25, "zergling": 0.25, "queen": 0.10},
            "micro": "SURROUND_BLINK",
            "note": "스토커 블링크 진입 시 양쪽 서라운드. 스파인 2개 급조"
        }
    },
    "skytoss_transition": {
        "detection": "Carrier count >= 2 OR Tempest count >= 2",
        "response": {
            "composition": {"corruptor": 0.35, "viper": 0.20, "hydra": 0.25, "queen": 0.10, "infestor": 0.10},
            "micro": "ABDUCT_CARRIERS",
            "note": "바이퍼 어브덕트 → 코럽터 집중. 인페스터 펑갈 고정"
        }
    }
}
```

---

### Task 2.3: ZvP 마이크로 조정

**파일:** `wicked_zerg_challenger/combat/micro_combat.py`

**구현 지시:**

```python
class ZvPMicroAdjustments:
    """프로토스 상대 마이크로 조정"""
    
    async def handle_force_fields(self, own_units, enemy_sentries):
        """포스필드 감지 시 우회 또는 너드웜 사용"""
        # 포스필드가 있는 램프/초크 회피
        # 대안 경로로 병력 이동
        # 레이저 바일로 포스필드 위 적 유닛 타겟
        pass
    
    async def handle_psionic_storm(self, own_units):
        """사이오닉 폭풍 범위에서 유닛 분산"""
        for unit in own_units:
            # 폭풍 이펙트 감지 (AbilityId.PSISTORM)
            storm_effects = self.bot.state.effects
            for effect in storm_effects:
                if effect.id == EffectId.PSYCHICSTORM:
                    for pos in effect.positions:
                        if unit.distance_to(pos) < 4:
                            # 폭풍 반대 방향으로 3칸 이동
                            flee_pos = unit.position.towards(pos, -3)
                            unit.move(flee_pos)
    
    async def handle_colossus(self, own_units, enemy_colossi):
        """거신 대응: 코럽터 집중 + 지상군 분산"""
        corruptors = own_units(UnitTypeId.CORRUPTOR)
        for corr in corruptors:
            corr.attack(enemy_colossi.closest_to(corr))
        
        # 거신 공격 범위(9) 밖에서 포지셔닝
        for unit in own_units.filter(lambda u: u.is_ground):
            closest_col = enemy_colossi.closest_to(unit)
            if unit.distance_to(closest_col) < 7:
                # 사이드로 우회
                unit.move(unit.position.towards(closest_col.position, -2))
    
    async def handle_oracle(self, base, oracles):
        """오라클 하라스 대응: 퀸 집중 + 스포어"""
        queens = self.bot.units(UnitTypeId.QUEEN).closer_than(15, base)
        for queen in queens:
            queen.attack(oracles.closest_to(queen))
        # 스포어 크롤러가 없으면 건설 예약
        spores_near = self.bot.structures(UnitTypeId.SPORECRAWLER).closer_than(10, base)
        if not spores_near:
            self.blackboard.set("need_spore_at", base.position)
```

---

### Task 2.4: ZvP 정찰 우선순위

**파일:** `wicked_zerg_challenger/scouting_system.py`

```python
ZVP_SCOUT_PRIORITIES = {
    "early": [  # 0~3분
        "enemy_natural",          # 확장 여부 (넥서스)
        "forge_timing",           # 포지 → 캐논 러시 징후
        "gateway_count",          # 게이트웨이 2+ → 올인 가능
        "cyber_core_timing",      # 사이버네틱스 코어 → 테크 방향
    ],
    "mid": [  # 3~8분
        "twilight_council",       # 황혼의회 → 블링크/차지
        "stargate_existence",     # 스타게이트 → 오라클/공허/캐리어
        "robotics_facility",      # 로보 → 불멸자/거신/관측선
        "dark_shrine",            # 암흑 성소 → DT 러시
        "templar_archives",       # 기사단 기록소 → 하이템플러
    ],
    "late": [  # 8분+
        "fleet_beacon",           # 함대 봉화 → 캐리어/폭풍함
        "disruptor_count",        # 분열기 수
        "archon_count",           # 아콘 수
        "warp_gate_count",        # 워프게이트 총 수 → 병력 규모 추정
    ]
}
```

---

## Phase 3: ZvZ (저그 vs 저그) 전략 완성

### Task 3.1: ZvZ 빌드오더 3종 구현

**파일:** `wicked_zerg_challenger/build_order_system.py`

**현재:** vs Zerg = SAFE_14POOL (1가지만)

```python
ZVZ_BUILDS = {
    "safe_14pool": {
        "name": "14풀 안전 (기본)",
        "condition": "default",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (18, UnitTypeId.ZERGLING),  # 4마리
            (20, "METABOLIC_BOOST"),
            (22, UnitTypeId.QUEEN),     # 내추럴 퀸
            (24, UnitTypeId.BANELINGNEST),
        ],
        "transition": "ling_bane_control",
        "note": "ZvZ 기본. 저글링 스피드 → 베인 전환"
    },
    "12pool_rush": {
        "name": "12풀 러시 (어그로)",
        "condition": "aggressive_opening",
        "order": [
            (12, UnitTypeId.SPAWNINGPOOL),
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.ZERGLING),  # 즉시 6마리
            (17, UnitTypeId.EXTRACTOR),
            (17, UnitTypeId.QUEEN),
            (19, "METABOLIC_BOOST"),
            (20, UnitTypeId.HATCHERY),  # 늦은 확장
        ],
        "transition": "ling_bane_allin_or_macro",
        "note": "12풀로 적 드론 킬 → 이득 보고 확장"
    },
    "roach_warren_macro": {
        "name": "바퀴 매크로 (대 저글링)",
        "condition": "enemy_ling_flood_detected",
        "order": [
            (13, UnitTypeId.OVERLORD),
            (14, UnitTypeId.SPAWNINGPOOL),
            (16, UnitTypeId.HATCHERY),
            (16, UnitTypeId.EXTRACTOR),
            (18, UnitTypeId.QUEEN),
            (20, UnitTypeId.ROACHWARREN),  # 빠른 바퀴
            (22, UnitTypeId.QUEEN),
            (24, UnitTypeId.ROACH),  # 바퀴 4기
        ],
        "transition": "roach_ravager_mid",
        "note": "적이 저글링 올인 시 바퀴로 카운터. 바퀴 4기면 저글링 12기 상대 가능"
    }
}
```

---

### Task 3.2: ZvZ 유닛 구성 로드맵

**파일:** `wicked_zerg_challenger/strategy_manager.py`

```python
ZVZ_COMPOSITION_TIMELINE = {
    "early": {  # 0~5분 — 저글링/베인 컨트롤 싸움
        "default": {"zergling": 0.60, "baneling": 0.20, "queen": 0.20},
        "vs_12pool": {"zergling": 0.70, "queen": 0.30},
        "vs_roach": {"roach": 0.50, "zergling": 0.30, "queen": 0.20},
    },
    "mid": {  # 5~10분 — 바퀴/히드라 전환
        "default": {"roach": 0.35, "ravager": 0.20, "hydra": 0.25, "zergling": 0.10, "LURKERMP": 0.10},
        "vs_muta": {"hydra": 0.50, "queen": 0.15, "roach": 0.25, "zergling": 0.10},
        "vs_roach_all_in": {"ravager": 0.30, "roach": 0.40, "hydra": 0.20, "zergling": 0.10},
    },
    "late": {  # 10분+ — 브루드로드/바이퍼 전환
        "default": {"broodlord": 0.25, "corruptor": 0.20, "viper": 0.15, "hydra": 0.20, "LURKERMP": 0.20},
        "vs_broodlord": {"corruptor": 0.40, "viper": 0.20, "hydra": 0.25, "infestor": 0.15},
    }
}
```

**핵심 전환 포인트:**
1. 저글링/베인 → 바퀴: 적이 바퀴를 뽑기 시작하면 즉시 전환
2. 바퀴/히드라 → 러커: 레어 완료 후 러커 전환 (방어적)
3. 러커/히드라 → 브루드로드: 하이브 완료 후 (공격적 마무리)

---

### Task 3.3: ZvZ 마이크로 (가장 중요)

**파일:** `wicked_zerg_challenger/combat/micro_combat.py`

**ZvZ 초반은 마이크로가 승패를 결정:**

```python
class ZvZMicroAdjustments:
    """저그 미러 마이크로 — 초반 저글링/베인 싸움이 핵심"""
    
    async def ling_bane_micro(self, own_lings, own_banes, enemy_lings, enemy_banes):
        """저글링-베인 컨트롤 (ZvZ 핵심)"""
        
        # 1. 적 베인 회피: 적 베인이 접근하면 저글링 분산
        for ling in own_lings:
            closest_enemy_bane = enemy_banes.closest_to(ling) if enemy_banes else None
            if closest_enemy_bane and ling.distance_to(closest_enemy_bane) < 4:
                # 베인 반대 방향으로 도주
                flee_pos = ling.position.towards(closest_enemy_bane.position, -4)
                ling.move(flee_pos)
            else:
                # 적 저글링 공격 (베인 아님!)
                if enemy_lings:
                    ling.attack(enemy_lings.closest_to(ling))
        
        # 2. 아군 베인: 적 저글링 뭉치에 돌진
        for bane in own_banes:
            if enemy_lings.amount >= 4:
                # 가장 밀집된 지점 찾기
                target = self._find_densest_point(enemy_lings, radius=2.0)
                bane.attack(target)
            elif enemy_banes:
                # 적 베인이 있으면 적 베인에 돌진 (상쇄)
                bane.attack(enemy_banes.closest_to(bane))
    
    async def roach_vs_roach_micro(self, own_roaches, enemy_roaches):
        """바퀴 미러: HP 낮은 바퀴 후퇴"""
        for roach in own_roaches:
            if roach.health_percentage < 0.3:
                # HP 30% 이하 바퀴 후퇴 (바퀴는 버로우 후 체력 회복)
                if self.bot.already_pending_upgrade(UpgradeId.BURROW):
                    roach(AbilityId.BURROWDOWN_ROACH)
                else:
                    roach.move(roach.position.towards(self.bot.start_location, 5))
            else:
                if enemy_roaches:
                    # 가장 HP 낮은 적 바퀴 집중
                    weakest = min(enemy_roaches, key=lambda r: r.health)
                    roach.attack(weakest)
    
    def _find_densest_point(self, units, radius=2.0):
        """유닛 밀집도가 가장 높은 지점 반환"""
        best_pos = units.center
        best_count = 0
        for unit in units:
            count = units.closer_than(radius, unit).amount
            if count > best_count:
                best_count = count
                best_pos = unit.position
        return best_pos
```

---

### Task 3.4: ZvZ 정찰 우선순위

```python
ZVZ_SCOUT_PRIORITIES = {
    "early": [  # 0~3분 — 풀 타이밍이 전부
        "spawning_pool_timing",   # 12풀/14풀/16풀 판별
        "gas_timing",             # 가스 → 스피드 업 타이밍
        "drone_count",            # 드론 수 → 올인 vs 매크로 판별
        "baneling_nest",          # 베인둥지 → 베인 러시 경고
    ],
    "mid": [  # 3~8분
        "roach_warren",           # 바퀴 워렌 → 바퀴 전환
        "lair_timing",            # 레어 → 뮤탈/러커 예측
        "spire_existence",        # 스파이어 → 뮤탈 경보
        "expansion_count",        # 확장 수 → 경제 규모
    ],
    "late": [  # 8분+
        "hive_timing",            # 하이브 → 울트라/브루드 예측
        "greater_spire",          # 대 스파이어 → 브루드로드
        "infestation_pit",        # 감염 구덩이 → 인페스터/하이브
        "ultralisk_cavern",       # 울트라리스크 동굴
    ]
}
```

---

## Phase 4: 공통 전략 시스템 구현

### Task 4.1: 빌드 오더 동적 전환 시스템

**파일:** `wicked_zerg_challenger/build_order_system.py`

**구현 지시:**
```python
class BuildOrderTransition:
    """빌드 오더 중간 전환 시스템"""
    
    def __init__(self):
        self.current_build = None
        self.transition_triggered = False
    
    async def check_transition(self, game_time, blackboard):
        """정찰 결과에 따라 빌드 오더 중간 전환"""
        if self.transition_triggered:
            return
        
        # 치즈 감지 → 즉시 방어 빌드로 전환
        if blackboard.get("cheese_detected"):
            self._switch_to_defense_build()
            self.transition_triggered = True
            return
        
        # 올인 감지 → 병력 집중 빌드로 전환
        if blackboard.get("enemy_all_in") and game_time < 300:
            self._switch_to_army_build()
            self.transition_triggered = True
            return
        
        # 적 확장 확인 → 매크로 빌드로 전환
        if blackboard.get("enemy_expand_confirmed") and not blackboard.get("enemy_aggression"):
            self._switch_to_greedy_build()
            return
    
    def _switch_to_defense_build(self):
        """방어 빌드: 스파인 + 퀸 + 저글링"""
        self.current_build = "emergency_defense"
        logger.info("[BUILD TRANSITION] Switching to DEFENSE build")
    
    def _switch_to_army_build(self):
        """병력 집중: 드론 중단, 전 라바 군사 유닛"""
        self.current_build = "full_army"
        logger.info("[BUILD TRANSITION] Switching to FULL ARMY build")
    
    def _switch_to_greedy_build(self):
        """그리디 매크로: 3해처리 + 빠른 테크"""
        self.current_build = "greedy_macro"
        logger.info("[BUILD TRANSITION] Switching to GREEDY MACRO build")
```

---

### Task 4.2: 매치업별 업그레이드 우선순위 정밀화

**파일:** `wicked_zerg_challenger/upgrade_manager.py`

**현재:** 종족별 가중치만 있음 (T: armor 1.3x, P: melee 1.2x, Z: melee 1.3x)

**추가 구현:**
```python
MATCHUP_UPGRADE_PRIORITY = {
    "ZvT": {
        "early": [
            UpgradeId.ZERGLINGMOVEMENTSPEED,     # 1순위: 저글링 스피드
        ],
        "mid": [
            UpgradeId.ZERGMELEEWEAPONSLEVEL1,    # 근접 공격 1 (저글링/베인)
            UpgradeId.ZERGGROUNDARMORSLEVEL1,     # 지상 방어 1
            UpgradeId.CENTRIFICALHOOKS,           # 베인 스피드 (vs bio 필수)
        ],
        "late": [
            UpgradeId.ZERGMELEEWEAPONSLEVEL3,
            UpgradeId.CHITINOUSPLATING,           # 울트라 방어 (vs bio 최종)
            UpgradeId.ANABOLICSYNTH,              # 울트라 스피드
        ]
    },
    "ZvP": {
        "early": [
            UpgradeId.ZERGLINGMOVEMENTSPEED,
        ],
        "mid": [
            UpgradeId.ZERGMISSILEWEAPONSLEVEL1,  # 원거리 공격 1 (히드라/바퀴)
            UpgradeId.EVOLVEGROOVEDSPINES,        # 히드라 사거리
            UpgradeId.ZERGGROUNDARMORSLEVEL1,
        ],
        "late": [
            UpgradeId.ZERGMISSILEWEAPONSLEVEL3,
            UpgradeId.ZERGFLYERWEAPONSLEVEL1,     # 공중 공격 (코럽터 vs 캐리어)
            UpgradeId.LURKERRANGE,                # 러커 사거리 (LURKERMP!)
        ]
    },
    "ZvZ": {
        "early": [
            UpgradeId.ZERGLINGMOVEMENTSPEED,     # 필수 1순위
        ],
        "mid": [
            UpgradeId.ZERGMISSILEWEAPONSLEVEL1,  # 바퀴 공격
            UpgradeId.GLIALRECONSTITUTION,        # 바퀴 스피드
            UpgradeId.ZERGGROUNDARMORSLEVEL1,
        ],
        "late": [
            UpgradeId.ZERGFLYERWEAPONSLEVEL1,    # 코럽터/브루드 공격
            UpgradeId.ZERGFLYERARMORSLEVEL1,
            UpgradeId.INFESTORENERGYUPGRADE,      # 인페스터 에너지
        ]
    }
}
```

---

### Task 4.3: 매치업별 타이밍 어택 시스템

**파일:** `wicked_zerg_challenger/strategy_manager.py`

```python
TIMING_ATTACKS = {
    "ZvT": {
        "ling_speed_timing": {
            "trigger": "metabolic_boost_done AND zergling_count >= 16",
            "time_window": (180, 300),  # 3~5분
            "target": "enemy_natural",
            "retreat_if": "enemy_bunker_count >= 2 OR army_power_ratio < 1.2",
        },
        "roach_ravager_push": {
            "trigger": "roach_count >= 8 AND ravager_count >= 3",
            "time_window": (360, 480),  # 6~8분
            "target": "enemy_third",
            "retreat_if": "siege_tank_count >= 3 OR army_power_ratio < 1.0",
        },
    },
    "ZvP": {
        "roach_timing": {
            "trigger": "roach_count >= 10 AND roach_speed_done",
            "time_window": (300, 420),  # 5~7분
            "target": "enemy_natural",
            "retreat_if": "immortal_count >= 3 OR army_power_ratio < 1.1",
        },
        "ling_nydus_harass": {
            "trigger": "nydus_network_ready AND zergling_count >= 20",
            "time_window": (300, 600),
            "target": "enemy_main_mineral_line",
            "retreat_if": "zergling_count < 8",
        },
    },
    "ZvZ": {
        "ling_bane_allin": {
            "trigger": "metabolic_boost_done AND baneling_count >= 6 AND zergling_count >= 12",
            "time_window": (180, 300),
            "target": "enemy_natural",
            "retreat_if": "roach_count_enemy >= 4 OR army_power_ratio < 0.8",
        },
        "roach_push": {
            "trigger": "roach_count >= 7",
            "time_window": (300, 420),
            "target": "enemy_natural",
            "retreat_if": "ravager_count_enemy >= 4 AND roach_count_enemy >= 5",
        },
    }
}
```

각 타이밍 어택에 대해:
1. 트리거 조건 충족 시 공격 명령 발동
2. 후퇴 조건 충족 시 안전하게 복귀
3. 타이밍 윈도우 밖이면 타이밍 어택 취소 → 일반 전략으로 복귀

---

### Task 4.4: 매치업별 긴급 대응 테이블

**파일:** `wicked_zerg_challenger/strategy_manager.py`

```python
EMERGENCY_RESPONSES = {
    # === ZvT 긴급 ===
    "proxy_barracks": {
        "detection": "Barracks distance_to(our_base) < 40 AND game_time < 180",
        "immediate": ["cancel_expansion", "spine_crawler_x2", "zergling_x6", "queen_defend"],
        "drone_production": "HALT",
    },
    "hellion_runby": {
        "detection": "Hellion count >= 4 AND distance_to(our_mineral_line) < 15",
        "immediate": ["queen_defend", "roach_x4", "wall_off_natural"],
        "drone_production": "REDUCE",
    },
    "bc_rush": {
        "detection": "Battlecruiser count >= 1 AND game_time < 600",
        "immediate": ["corruptor_x5", "queen_transfuse", "spore_x2"],
        "drone_production": "REDUCE",
    },
    
    # === ZvP 긴급 ===
    "cannon_rush": {
        "detection": "Photon Cannon distance_to(our_base) < 40 AND game_time < 180",
        "immediate": ["drone_pull_x4", "spine_crawler_x1", "zergling_x6"],
        "drone_production": "HALT",
    },
    "dt_rush": {
        "detection": "DarkTemplar detected OR DarkShrine scouted",
        "immediate": ["overseer_morph", "spore_x2_each_base", "queen_defend"],
        "drone_production": "NORMAL",
    },
    "void_ray_rush": {
        "detection": "VoidRay count >= 2 AND game_time < 360",
        "immediate": ["queen_x4", "hydra_x6", "spore_x2"],
        "drone_production": "REDUCE",
    },
    
    # === ZvZ 긴급 ===
    "12pool_rush": {
        "detection": "enemy_zergling_count >= 6 AND game_time < 120",
        "immediate": ["drone_pull_x3", "spine_crawler_x1", "zergling_x4"],
        "drone_production": "HALT",
    },
    "baneling_bust": {
        "detection": "enemy_baneling_count >= 8 AND approaching_our_base",
        "immediate": ["split_units", "queen_defend", "roach_x4"],
        "drone_production": "HALT",
    },
}
```

---

## Phase 5: 종합 테스트 매트릭스

### Task 5.1: 매치업별 시나리오 테스트

**파일:** `tests/test_matchup_strategies.py` (신규 생성)

```python
"""매치업별 전략 시나리오 테스트"""

class TestZvTStrategies:
    def test_build_selection_default(self):
        """기본 상황에서 hatch_first_16 선택"""
    
    def test_build_switch_on_proxy(self):
        """프록시 감지 시 aggressive_pool_first로 전환"""
    
    def test_counter_bio(self):
        """마린/마라우더 상대 베인/저글링 비율 확인"""
    
    def test_counter_mech(self):
        """탱크/토르 상대 레이저/바퀴 비율 확인"""
    
    def test_medivac_drop_response(self):
        """메디팩 드롭 감지 시 방어 유닛 이동 확인"""
    
    def test_siege_tank_surround(self):
        """시즈 탱크 서라운드 마이크로 확인"""

class TestZvPStrategies:
    def test_build_selection_default(self):
        """기본 상황에서 roach_rush 선택"""
    
    def test_build_switch_on_cannon_rush(self):
        """캐논 러시 감지 시 ling_flood 전환"""
    
    def test_counter_skytoss(self):
        """캐리어/폭풍함 상대 코럽터/바이퍼 비율 확인"""
    
    def test_storm_dodge(self):
        """사이오닉 폭풍 회피 마이크로 확인"""
    
    def test_dt_emergency(self):
        """DT 감지 시 오버시어 변태 + 스포어 건설 확인"""

class TestZvZStrategies:
    def test_build_selection_default(self):
        """기본 상황에서 safe_14pool 선택"""
    
    def test_ling_bane_micro(self):
        """저글링-베인 컨트롤: 적 베인 회피 + 적 저글링 공격"""
    
    def test_roach_transition(self):
        """적 바퀴 감지 시 바퀴 전환 확인"""
    
    def test_muta_counter(self):
        """적 뮤탈 감지 시 히드라 + 스포어 전환 확인"""

class TestBuildTransitions:
    def test_cheese_to_defense(self):
        """치즈 감지 시 방어 빌드 전환"""
    
    def test_greedy_on_expand(self):
        """적 확장 확인 시 그리디 매크로 전환"""
    
    def test_timing_attack_trigger(self):
        """타이밍 어택 조건 충족 시 공격 발동"""
    
    def test_timing_attack_retreat(self):
        """후퇴 조건 시 안전 복귀"""
```

---

### Task 5.2: 승률 벤치마크 목표

```
Medium AI 목표 (Sprint 완료 후):
┌──────────┬──────────┬──────────┬──────────┐
│ 매치업    │ 현재     │ 목표     │ 최종 목표 │
├──────────┼──────────┼──────────┼──────────┤
│ ZvT      │ ~45%     │ 85%+     │ 95%+     │
│ ZvP      │ ~45%     │ 85%+     │ 95%+     │
│ ZvZ      │ ~50%     │ 80%+     │ 90%+     │
│ 종합     │ ~47%     │ 83%+     │ 93%+     │
└──────────┴──────────┴──────────┴──────────┘

Hard AI 목표:
┌──────────┬──────────┐
│ 매치업    │ 목표     │
├──────────┼──────────┤
│ ZvT      │ 60%+     │
│ ZvP      │ 60%+     │
│ ZvZ      │ 55%+     │
└──────────┴──────────┘
```

---

## 파일 맵 요약

```
wicked_zerg_challenger/
├── build_order_system.py       # Task 1.1, 2.1, 3.1, 4.1 (빌드오더 확장)
├── strategy_manager.py         # Task 1.2, 2.2, 3.2, 4.3, 4.4 (카운터/타이밍/긴급)
├── intel_manager.py            # Task 1.4, 2.4, 3.4 (정찰 우선순위)
├── scouting_system.py          # Task 1.4, 2.4, 3.4 (정찰 실행)
├── upgrade_manager.py          # Task 4.2 (업그레이드 우선순위)
├── combat/
│   └── micro_combat.py         # Task 1.3, 2.3, 3.3 (매치업별 마이크로)
├── racial_counter_manager.py   # Task 2.2 (카운터 중앙 디스패치)
├── config/
│   └── strategy_config.json    # 카운터 빌드 JSON 설정
└── tests/
    └── test_matchup_strategies.py  # Task 5.1 (신규)
```
