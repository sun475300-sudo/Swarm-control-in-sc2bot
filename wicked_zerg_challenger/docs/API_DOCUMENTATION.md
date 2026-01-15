# API Documentation

**자동 생성 일시**: 2026-01-15
**생성 도구**: auto_documentation_generator.py

---

## Module: `COMPLETE_RUN_SCRIPT`

완전한 실행 스크립트 - 전체 시스템을 처음부터 끝까지 실행
Complete Execution Script - Run entire system from start to finish

이 스크립트는 프로젝트의 전체 실행 흐름을 한 곳에 모아서 실행합니다.
This script consolidates the entire execution flow of the project.

### Functions

#### `initialize_system`

시스템 초기화

#### `setup_sc2_path`

SC2 경로 설정

#### `initialize_bot`

봇 초기화

**Parameters**:

- `project_dir`: Path

#### `run_game`

게임 실행

**Parameters**:

- `bot_instance`

#### `start_dashboard_server`

대시보드 서버 시작

**Parameters**:

- `background`

#### `main`

메인 실행 함수

---

## Module: `chat_manager`

Compatibility shim. Use chat_manager_utf8.ChatManager as the canonical implementation.

---

## Module: `combat_manager`

### Classes

#### `CombatManager`

**Methods**:

- `__init__(2 args)`
- `_load_curriculum_level(1 args)`
- `_should_relax_retreat_conditions(1 args)`
- `initialize(1 args)`
- `_determine_combat_mode(1 args)`
- `_update_army_status(1 args)`: Update army status (performance optimized + unit loss detection)...
- `_check_army_gathered(1 args)`: 병력 집결 상태 체크

💡 집결 완료 조건:
    병력의 80% 이상이 집결지 반경 15 내에 있을 때...
- `_should_retreat(1 args)`: 퇴각 여부 판단

💡 퇴각 조건:
    공격 중 병력 손실율이 임계값을 넘으면 퇴각

Curriculum Learning: 난이도가 낮을 때 퇴각 조건 완화
- VeryEasy,...
- `_should_attack(3 args)`: 공격 여부 판단 (Economic-Driven + Serral 스타일)

NOTE: No rush mode - Don't attack in early game (first 4 mi...
- `_find_enemy_clusters(3 args)`: 적 유닛 클러스터 찾기 (간단한 거리 기반 클러스터링)

Args:
    enemy_units: 적 유닛 리스트
    max_clusters: 최대 클러스터 수

Returns...
- `_select_priority_target(3 args)`: IMPROVED: 우선순위 타겟 선택 (Focus Fire 강화)

PERFORMANCE: Optimized using closer_than API to reduce O(n²) d...
- `_calculate_concave_formation(3 args)`: 오목한 진형(Concave) 형성 계산 - 포위 전술

적 위치를 중심으로 반원을 그리며 병력을 분산시킨 후 동시에 덮치는 전술
저그 병력의 핵심은 '포위'입니다.

Args:
 ...
- `_calculate_dynamic_target_priority(3 args)`: 동적 타겟 우선순위 계산 - 내 조합에 따른 상대 우선순위 재계산

내 병력이 히드라 중심이라면 '탱크'를 1순위로,
저글링 중심이라면 '기뢰나 맹독충'을 1순위로 피하거나 점사
...
- `_get_army_units(1 args)`: IMPROVED: 전투 유닛 목록 반환 (일꾼 제외)

IMPROVED:
    - IntelManager 캐시 우선 사용 (성능 최적화)
    - 더 정확한 병력 추적 (rea...
- `_get_retreat_position(2 args)`: Calculate retreat position...
- `_calculate_army_centroid(1 args)`: 군대 중심점(Centroid) 계산

💡 클러스터링:
    병력의 평균 위치를 계산하여 집결 여부 판단

Returns:
    Point2: 군대 중심점...
- `_calculate_army_spread(1 args)`: 군대 분산도 계산

Returns:
    float: 중심점으로부터의 평균 거리...
- `get_combat_status(1 args)`: Return current combat status...
- `set_attack_target(2 args)`: Set attack target...
- `set_rally_point(2 args)`: Set rally point...
- `_can_attrit_enemy_units(1 args)`: 소모전 판단 로직: 상대방의 병력을 갉아먹을 수 있는가?

저그는 '소모전'에 능해야 함. 단순히 승률이 낮다고 빼는 것이 아니라,
상대방의 병력을 지속적으로 감소시킬 수 있는지 ...
- `_update_win_rate(1 args)`: 현재 승률을 계산하여 업데이트

ProductionManager나 IntelManager에서 계산된 승률을 가져오거나,
직접 계산하여 저장합니다....

---

## Module: `config`

### Classes

#### `GamePhase`

Current game phase - transitions dynamically based on scouting

**Bases**: Enum

#### `EnemyRace`

Opponent race

**Bases**: Enum

#### `Config`

AI behavior configuration values (immutable)

#### `ConfigLoader`

Loads configuration with learned parameter overrides

**Methods**:

- `__init__(2 args)`
- `load_learned_config(1 args)`: Load learned configuration parameters...
- `get_config(1 args)`: Get configuration with learned overrides applied...
- `get_parameter(3 args)`: Get a specific learned parameter value...

### Functions

#### `get_config_loader`

Get global config loader instance

#### `get_learned_parameter`

Get learned parameter from local_training/scripts/learned_build_orders.json
Priority: local_training/scripts/learned_build_orders.json > learned_build_orders.json (same dir)

**Parameters**:

- `parameter_name`: str
- `default_value`: Any

---

## Module: `economy_manager`

### Classes

#### `EconomyManager`

**Methods**:

- `__init__(2 args)`
- `_ensure_build_reservations(1 args)`: Ensure shared reservation map exists and return it....
- `_cleanup_build_reservations(1 args)`: Remove stale reservations (e.g., failed builds) using game time....
- `_reserve_building(2 args)`: Reserve a structure type to block duplicate build commands in the same window....
- `_can_build_safely(4 args)`: 중복 건설을 원천 차단하는 안전한 건설 체크 함수

Args:
    structure_id: 건설할 건물 타입
    check_workers: 일벌레 명령 체크 여부 (기본값:...
- `_is_construction_started(2 args)`: Check if a structure is already being constructed, including when a worker
has an active order to bu...
- `_calculate_location_value(2 args)`: 위치 가치 평가: 일꾼이 스스로 "이 위치가 내가 있어야 할 곳인가?"를 판단

Args:
    position: 평가할 위치

Returns:
    float: 위치의 가치 ...
- `get_economy_status(1 args)`: 현재 경제 상태 반환...

### Functions

#### `get_learned_parameter`

---

## Module: `genai_self_healing`

Gen-AI Self-Healing System

Google Vertex AI (Gemini)¸¦ È°¿ëÇÑ ÀÚµ¿ ¿¡·¯ ºÐ¼® ¹× ÆÐÄ¡ Á¦¾È ½Ã½ºÅÛ



±â´É:

1. ·±Å¸ÀÓ ¿¡·¯ ¹ß»ý ½Ã Traceback ¹× ¼Ò½º ÄÚµå¸¦ Gemini·Î Àü¼Û

2. Gemini°¡ ¿øÀÎ ºÐ¼® ¹× ¼öÁ¤ ÆÐÄ¡ Á¦¾È

3. ÆÐÄ¡ Á¦¾ÈÀ» ·Î±× ÆÄÀÏ¿¡ ÀúÀå (ÀÚµ¿ Àû¿ëÀº ¼±ÅÃÀû)



ÁÖÀÇ»çÇ×:

- ÀÚµ¿ ÆÐÄ¡ Àû¿ëÀº À§ÇèÇÒ ¼ö ÀÖÀ¸¹Ç·Î ±âº»ÀûÀ¸·Î ºñÈ°¼ºÈ­

- ÆÐÄ¡ Á¦¾ÈÀ» ·Î±×·Î ÀúÀåÇÏ¿© °³¹ßÀÚ°¡ °ËÅä ÈÄ Àû¿ëÇÏµµ·Ï ±ÇÀå

### Classes

#### `ErrorContext`

¿¡·¯ ¹ß»ý ÄÁÅØ½ºÆ® Á¤º¸

#### `PatchSuggestion`

Gemini°¡ Á¦¾ÈÇÑ ÆÐÄ¡ Á¤º¸

#### `GenAISelfHealing`

Gen-AI Self-Healing ½Ã½ºÅÛ



Google Gemini API¸¦ »ç¿ëÇÏ¿© ¿¡·¯¸¦ ºÐ¼®ÇÏ°í ÆÐÄ¡¸¦ Á¦¾ÈÇÕ´Ï´Ù.

**Methods**:

- `__init__(5 args)`: Args:

    api_key: Google Gemini API Å° (È¯°æ º¯¼ö GOOGLE_API_KEY¿¡¼­µµ ÀÐÀ½)

    model_name: »ç¿ë...
- `is_available(1 args)`: Gemini API°¡ »ç¿ë °¡´ÉÇÑÁö È®ÀÎ...
- `analyze_error(4 args)`: ¿¡·¯¸¦ ºÐ¼®ÇÏ°í ÆÐÄ¡¸¦ Á¦¾È



Args:

    error: ¹ß»ýÇÑ ¿¹¿Ü °´Ã¼

    context: Ãß°¡ ÄÁÅØ½ºÆ® Á¤º¸ (...
- `analyze_gap_feedback(3 args)`: Build-Order Gap Analyzer 피드백 분석 및 패치 제안

Args:
    gap_feedback: StrategyAudit에서 생성한 피드백 문자열
    sou...
- `_build_gap_analysis_prompt(3 args)`: Gap Analysis 전용 프롬프트 생성...
- `_parse_gemini_gap_response(3 args)`: Gemini의 Gap Analysis 응답 파싱...
- `_collect_error_context(3 args)`: ¿¡·¯ ÄÁÅØ½ºÆ® ¼öÁý...
- `_extract_source_files(2 args)`: ¿¡·¯¿Í °ü·ÃµÈ ¼Ò½º ÆÄÀÏ ÀÐ±â...
- `_build_analysis_prompt(3 args)`: Gemini¿¡ Àü¼ÛÇÒ ÇÁ·ÒÇÁÆ® »ý¼º...
- `_parse_gemini_response(3 args)`: Gemini ÀÀ´ä ÆÄ½Ì...
- `_save_patch_suggestion(3 args)`: ÆÐÄ¡ Á¦¾ÈÀ» ÆÄÀÏ¿¡ ÀúÀå...
- `apply_patch(2 args)`: ÆÐÄ¡ Àû¿ë (ÁÖÀÇ: ÀÚµ¿ ÆÐÄ¡´Â À§ÇèÇÒ ¼ö ÀÖÀ½)



Args:

    patch: Àû¿ëÇÒ ÆÐÄ¡ Á¦¾È



Returns:

    ...

### Functions

#### `get_self_healing`

Àü¿ª Self-Healing ÀÎ½ºÅÏ½º °¡Á®¿À±â

#### `init_self_healing`

Àü¿ª Self-Healing ÀÎ½ºÅÏ½º ÃÊ±âÈ­



Args:

    api_key: Google Gemini API Å°

    enable_auto_patch: ÀÚµ¿ ÆÐÄ¡ Àû¿ë ¿©ºÎ (±âº»°ª: False)



Returns:

    GenAISelfHealing ÀÎ½ºÅÏ½º

**Parameters**:

- `api_key`: Optional[str]
- `enable_auto_patch`: bool

---

## Module: `intel_manager`

### Classes

#### `StrategyMode`

전략 모드

**Bases**: Enum

#### `ThreatLevel`

위협 수준

IntEnum을 사용하여 숫자 비교 연산(>=, <=, >, <)이 가능하도록 함

**Bases**: IntEnum

#### `EnemyIntel`

적 정보 데이터 클래스

#### `CombatIntel`

전투 정보 데이터 클래스

#### `ProductionIntel`

생산 정보 데이터 클래스

#### `EconomyIntel`

경제 정보 데이터 클래스

#### `IntelManager`

인텔 매니저 - 전역 지능 통합 (Blackboard)

💡 설계 철학:
    모든 매니저가 이 클래스를 참조하여 정보를 공유합니다.
    CombatManager가 적의 은폐 유닛을 발견하면,
    ProductionManager가 즉시 감시군주를 생산하는 식의
    유기적인 협력이 가능해집니다.

사용 예시:
    # 메인 봇에서 초기화
    self.intel = IntelManager(self)

    # 매니저에서 정보 읽기
    if self.bot.intel.enemy.has_cloaked:
        self._produce_overseer()

    # 매니저에서 정보 쓰기
    self.bot.intel.enemy.has_cloaked = True

**Methods**:

- `__init__(2 args)`: Args:
    bot: 메인 봇 인스턴스...
- `update(2 args)`: 매 프레임 호출 - 정보 업데이트 및 캐싱

💡 호출 순서:
    1. on_step 시작 시 가장 먼저 호출
    2. 각 매니저가 실행되기 전에 최신 정보 확보

Args:...
- `_update_economy(1 args)`: 경제 정보 업데이트...
- `_update_enemy_tech(1 args)`: 상대 테크 정보 업데이트 (ScoutManager에서 감지한 정보 반영 및 직접 스캔)...
- `_update_enemy_intel(1 args)`: 적 정보 업데이트...
- `_update_combat_intel(1 args)`: 전투 정보 업데이트...
- `_evaluate_threat(1 args)`: 위협 수준 평가...
- `get_pursue_targets(1 args)`: 시야에서 사라진 적 유닛의 마지막 위치 반환 (추격용)

Returns:
    List[Point2]: 추격할 적 유닛의 마지막 위치 리스트...
- `_decide_strategy(1 args)`: 전략 모드 결정...
- `_process_signals(1 args)`: 신호 처리 - 매니저 간 협력...
- `get_status_report(1 args)`: 현재 상태 보고서 반환...
- `should_attack(1 args)`: 공격 시작 여부 판단 (Serral 스타일)

Serral의 공격 트리거 조건:
    1. 인구수 150-160 법칙: 일벌레 66기 이상, 전체 인구수 160 도달
    2....
- `should_defend(1 args)`: 방어 모드 여부 판단...
- `get_priority_unit(1 args)`: 우선 생산 유닛 반환...
- `_update_target_priority_cache(3 args)`: 타겟팅 우선순위 캐시 업데이트

🚀 성능 최적화: 매 프레임 모든 적 유닛의 우선순위를 계산하는 대신,
4프레임마다 한 번만 계산하여 캐싱

Args:
    enemy_units...

---

## Module: `local_training.build_order_learner`

Build Order Learner and Executor

This module provides:
1. BuildOrderLearner: Loads and manages build orders from JSON files
2. BuildOrderExecutor: Executes build orders in-game with adaptive logic

### Classes

#### `BuildOrderStep`

Single build order step

#### `BuildOrder`

Complete build order

**Methods**:

- `__post_init__(1 args)`

#### `BuildOrderLearner`

Loads and manages build orders from JSON files

Features:
- Loads build orders from data directory
- Filters by matchup (ZvT, ZvP, ZvZ)
- Filters by strategy tags (aggressive, economic, standard)
- Provides build order selection based on criteria

**Methods**:

- `__init__(2 args)`: Args:
    data_dir: Directory containing build order JSON files...
- `_load_build_orders(1 args)`: Load all build orders from JSON files...
- `_parse_build_order(2 args)`: Parse build order from dictionary...
- `get_build_orders(4 args)`: Get build orders matching criteria

Args:
    matchup: Matchup filter (e.g., "ZvT", "ZvP", "ZvZ")
  ...
- `get_best_build(3 args)`: Get the best build order for a matchup and strategy

Args:
    matchup: Matchup (e.g., "ZvT", "ZvP",...

#### `BuildOrderExecutor`

Executes build orders in-game with adaptive logic

Features:
- Supply/time-based trigger checking
- Resource availability validation
- Tech requirement checking
- Fallback logic for impossible steps
- Progress tracking

**Methods**:

- `__init__(3 args)`: Args:
    bot: SC2 BotAI instance
    learner: BuildOrderLearner instance...
- `set_build_order(5 args)`: Set the current build order to execute

Args:
    matchup: Matchup (e.g., "ZvT", "ZvP", "ZvZ")
    s...
- `_should_execute_step(2 args)`: Check if step should be executed based on supply/time...
- `_get_unit_type_from_action(2 args)`: Get UnitTypeId from action name...
- `_is_already_built(2 args)`: Check if unit/structure is already built or pending...
- `_has_resources(3 args)`: Check if bot has enough resources...
- `_has_tech_requirements(2 args)`: Check if tech requirements are met...
- `get_progress_status(1 args)`: Get current build order progress status...
- `is_complete(1 args)`: Check if build order is complete...

#### `UnitTypeId`

---

## Module: `local_training.check_encoding`

ÀÎÄÚµù È®ÀÎ ½ºÅ©¸³Æ®

---

## Module: `local_training.combat_tactics`

### Classes

#### `CombatTactics`

**Methods**:

- `__init__(2 args)`

#### `DummyMicroController`

---

## Module: `local_training.curriculum_manager`

### Classes

#### `CurriculumManager`

**Methods**:

- `__init__(2 args)`
- `load_level(1 args)`: Load curriculum level from stats file....
- `save_level(1 args)`: Save current curriculum level to stats file....
- `get_difficulty(1 args)`: Get current difficulty level....
- `get_level_name(1 args)`: Get current level name....
- `check_promotion(3 args)`: Check if AI should be promoted to next difficulty.

IMPROVED: Ensures difficulty increases by exactl...
- `check_demotion(3 args)`: Check if AI should be demoted to previous difficulty.

IMPROVED: Ensures difficulty decreases by exa...
- `record_game(1 args)`: Record game at current level....
- `get_level_name_from_idx(2 args)`: Get level name from index....
- `get_progress_info(1 args)`: Get current progress information....
- `update_priority(3 args)`: Build-Order Gap Analyzer에서 호출: 건물 건설 우선순위 업데이트

Args:
    building_name: 건물 이름 (예: "SpawningPool", "...
- `get_priority(2 args)`: 건물의 현재 우선순위 조회

Args:
    building_name: 건물 이름

Returns:
    우선순위 ("Urgent", "High", "Normal", "Low"...

---

## Module: `local_training.main_integrated`

### Classes

#### `SafeStreamHandler`

StreamHandler that catches ValueError when buffer is detached

**Bases**: logging.StreamHandler

**Methods**:

- `emit(2 args)`

### Functions

#### `get_venv_dir`

Get virtual environment directory from environment variable or use project default

#### `get_sc2_path`

#### `safe_stream_handler_emit`

**Parameters**:

- `self`
- `record`

#### `write_status_file`

Write instance status to a JSON file for dashboard display

IMPROVED: File locking prevention for parallel execution
- Uses temporary file + atomic move to prevent file lock conflicts
- Retries on failure to handle concurrent writes

Args:
    instance_id: Unique instance identifier (0 if not in parallel mode)
    status_data: Dictionary containing status information

**Parameters**:

- `instance_id`
- `status_data`

#### `run_training`

---

## Module: `local_training.personality_manager`

Personality Manager - Bot personality and chat system
Manages bot personality, chat messages, and in-game communication.

Core features:
    1. Persona-based playstyle (Serral, Dark, Reynor)
    2. In-game chat management
    3. GG detection and handling
    4. Bot internal thoughts broadcast

### Classes

#### `PersonalityManager`

Manager for bot personality and chat

**Methods**:

- `__init__(3 args)`: Initialize PersonalityManager

Args:
    bot: WickedZergBotPro instance
    personality: Persona ("s...
- `get_personality_name(1 args)`: Get persona name...
- `get_drone_limit(1 args)`: Get persona drone limit...
- `get_aggression(1 args)`: Get persona aggression...
- `get_macro_focus(1 args)`: Get persona macro focus...
- `should_chat(2 args)`: Determine if bot should chat

Args:
    current_time: Current game time

Returns:
    bool: Whether ...
- `get_greeting_message(1 args)`: Get greeting message...
- `get_win_message(1 args)`: Get victory message...
- `get_taunt_message(1 args)`: Get taunt message...
- `get_personality_description(1 args)`: Get persona description...
- `log_personality_info(1 args)`: Log persona information...

---

## Module: `local_training.production_resilience`

### Classes

#### `ProductionResilience`

**Methods**:

- `__init__(2 args)`
- `_cleanup_build_reservations(1 args)`: Drop stale reservations to avoid permanent blocks....

---

## Module: `local_training.strategy_audit`

Build-Order Gap Analyzer (빌드오더 오차 분석기)

프로게이머의 리플레이 데이터와 봇이 실제로 수행한 데이터를 프레임 단위로 대조하여
'성능 저하의 구간'을 찾아내는 시스템

핵심 기능:
1. Time Gap (시간 오차) 분석
2. Sequence Error (순서 오류) 분석
3. Resource Efficiency (자원 효율) 분석
4. 자동 보완 로직 (CurriculumManager 연동)
5. Gemini Self-Healing 연동

### Classes

#### `BuildEvent`

건물 건설 이벤트

#### `TimeGap`

시간 오차 분석 결과

#### `SequenceError`

순서 오류 분석 결과

#### `ResourceEfficiency`

자원 효율 분석 결과

#### `GapAnalysisResult`

전체 분석 결과

#### `StrategyAudit`

빌드오더 오차 분석기

**Methods**:

- `__init__(3 args)`: Args:
    learned_build_orders_path: 프로게이머 데이터 경로
    telemetry_data_path: 봇 텔레메트리 데이터 경로...
- `load_pro_data(1 args)`: 프로게이머 데이터 로드...
- `extract_bot_build_events(3 args)`: 봇의 빌드 이벤트 추출

Args:
    build_order_timing: production_manager의 build_order_timing 딕셔너리
    telemetr...
- `extract_pro_build_events(1 args)`: 프로게이머의 빌드 이벤트 추출...
- `analyze_time_gaps(3 args)`: 시간 오차 분석...
- `analyze_sequence_errors(3 args)`: 순서 오류 분석...
- `analyze_resource_efficiency(4 args)`: 자원 효율 분석...
- `analyze(4 args)`: 전체 분석 수행

Args:
    build_order_timing: 봇의 빌드 오더 타이밍
    telemetry_data: 봇의 텔레메트리 데이터
    game_id: 게...
- `save_analysis_result(2 args)`: 분석 결과 저장...
- `generate_gemini_feedback(2 args)`: Gemini Self-Healing을 위한 피드백 생성

Returns:
    Gemini에게 전달할 피드백 문자열...

### Functions

#### `update_curriculum_priority`

CurriculumManager의 우선순위 업데이트

Args:
    curriculum_manager: CurriculumManager 인스턴스
    gap_analysis: 분석 결과

**Parameters**:

- `curriculum_manager`
- `gap_analysis`: GapAnalysisResult

#### `analyze_bot_performance`

게임 종료 후 봇 성능 분석

Args:
    bot: WickedZergBotPro 인스턴스
    game_result: 게임 결과 ("victory" or "defeat")

Returns:
    분석 결과 (모든 게임에서 분석, 승리한 경우에도 개선점 확인)

**Parameters**:

- `bot`
- `game_result`: str

#### `analyze_last_game`

게임 종료 후 마지막 게임 분석 (편의 메서드)

Args:
    bot: WickedZergBotPro 인스턴스
    game_result: 게임 결과 ("victory" or "defeat")

Returns:
    분석 결과

**Parameters**:

- `self`
- `bot`
- `game_result`: str

---

## Module: `map_manager`

Map Manager for Training
Manages map rotation, selection, and performance tracking

### Classes

#### `MapManager`

Manages map selection and performance tracking

**Methods**:

- `__init__(2 args)`: Initialize map manager

Args:
    stats_file: Path to map performance statistics file...
- `_load_stats(1 args)`: Load map performance statistics...
- `_save_stats(1 args)`: Save map performance statistics...
- `get_available_maps(1 args)`: Get list of available maps from Maps folder

Returns all .SC2Map files found in the Maps folder,
pri...
- `select_map(2 args)`: Select a map based on mode

Args:
    mode: Selection mode
        - "sequential": Rotate through ma...
- `_select_weighted(2 args)`: Select map based on performance (prefer maps with lower win rate)

Args:
    available: List of avai...
- `record_result(4 args)`: Record game result for a map

Args:
    map_name: Name of the map
    result: "victory" or "defeat"
...
- `get_map_stats(2 args)`: Get statistics for a specific map

Args:
    map_name: Name of the map

Returns:
    Dictionary with...
- `get_performance_report(1 args)`: Generate performance report for all maps

Returns:
    Formatted report string...

### Functions

#### `get_map_manager`

Get global map manager instance

---

## Module: `micro_controller`

Micro Controller - Swarm Control Algorithms for Drone Swarm Applications

This module implements actual swarm control algorithms used in real drone systems:
- Potential Field Method: For obstacle avoidance and formation maintenance
- Boids Algorithm: For natural flocking behavior
- Separation, Alignment, Cohesion: Core swarm behaviors

These algorithms are directly applicable to real-world drone swarm control.

### Classes

#### `SwarmConfig`

Configuration for swarm control algorithms.

#### `PotentialFieldController`

Potential Field Method for Swarm Control

This implements the actual potential field algorithm used in:
- Drone swarm obstacle avoidance
- Formation maintenance
- Path planning

The potential field creates attractive forces toward goals
and repulsive forces away from obstacles and other units.

**Methods**:

- `__init__(2 args)`: Initialize Potential Field Controller....
- `calculate_potential_field(5 args)`: Calculate potential field force at unit position.

Args:
    unit_position: Current position of the ...

#### `BoidsController`

Boids Algorithm for Natural Flocking Behavior

Implements the classic Boids algorithm with three core behaviors:
1. Separation: Steer away from nearby units
2. Alignment: Steer toward average heading of nearby units
3. Cohesion: Steer toward average position of nearby units

This is the same algorithm used in:
- Drone swarm formation flying
- Autonomous vehicle platooning
- Multi-agent coordination systems

**Methods**:

- `__init__(2 args)`: Initialize Boids Controller....
- `calculate_boids_velocity(4 args)`: Calculate desired velocity using Boids algorithm.

Args:
    unit_position: Current position of the ...
- `_calculate_separation(3 args)`: Calculate separation force (steer away from neighbors)....
- `_calculate_alignment(3 args)`: Calculate alignment force (steer toward average neighbor velocity)....
- `_calculate_cohesion(3 args)`: Calculate cohesion force (steer toward average neighbor position)....

#### `MicroController`

Micro Controller - Main interface for swarm control

This class integrates Potential Field and Boids algorithms
to provide comprehensive swarm control for drone applications.

Real-world applications:
- Drone swarm formation flying
- Autonomous vehicle platooning
- Multi-agent coordination
- Obstacle avoidance in cluttered environments

**Methods**:

- `__init__(3 args)`: Initialize Micro Controller.

Args:
    bot: BotAI instance (optional, for SC2 integration)
    conf...
- `calculate_swarm_movement(5 args)`: Calculate optimal movement using combined algorithms.

Args:
    unit_position: Current unit positio...
- `calculate_flocking_behavior(4 args)`: Calculate natural flocking behavior using Boids algorithm.

Args:
    unit_position: Current unit po...
- `execute_formation_control(4 args)`: Execute formation control for a group of units.

Args:
    units: List of units to control
    forma...
- `_get_unit_position(2 args)`: Extract position from unit (handles both SC2 and mock units)....
- `execute_baneling_vs_marines(3 args)`: Specialized micro for banelings vs marines.
Uses potential field to find optimal detonation position...
- `_find_clusters(3 args)`: Find cluster centers using simple k-means-like approach.

Args:
    positions: List of positions
   ...

#### `Point2`

**Methods**:

- `__init__(2 args)`
- `distance_to(2 args)`
- `towards(3 args)`

### Functions

#### `_distance`

Calculate Euclidean distance between two points.

**Parameters**:

- `p1`: Point2
- `p2`: Point2

#### `_magnitude`

Calculate magnitude of a vector.

**Parameters**:

- `p`: Point2

#### `_normalize`

Normalize a vector, optionally limiting to max_magnitude.

**Parameters**:

- `p`: Point2
- `max_magnitude`: float

#### `_zero_point`

Create a zero point.

#### `_average_points`

Calculate average position of a list of points.

**Parameters**:

- `points`: List[Point2]

---

## Module: `monitoring.bot_api_connector`

Bot API Connector - Real-time connection between bot and dashboard API server

This module provides a bridge between the running bot instance and the FastAPI
monitoring server, enabling real-time game state updates.

### Classes

#### `GameState`

Game state data structure

**Methods**:

- `__post_init__(1 args)`

#### `CombatStats`

Combat statistics data structure

#### `LearningProgress`

Learning progress data structure

**Methods**:

- `__post_init__(1 args)`

#### `BotApiConnector`

Connector between bot and dashboard API server.

This class maintains a connection to the FastAPI server and provides
methods to update game state, combat stats, and learning progress.

**Methods**:

- `__init__(2 args)`: Initialize the bot API connector.

Args:
    api_url: Base URL of the FastAPI server (default: http:...
- `update_state(2 args)`: Update game state from bot instance.

Args:
    bot_instance: The bot instance (WickedZergBotPro)
  ...
- `_get_game_status(2 args)`: Extract game status from bot instance...
- `_extract_units(2 args)`: Extract unit counts from bot instance...
- `_get_threat_level(2 args)`: Determine threat level from bot instance...
- `_get_strategy_mode(2 args)`: Extract strategy mode from bot instance...
- `_get_map_name(2 args)`: Extract map name from bot instance...
- `_send_state_update(2 args)`: Send game state update to API server.

Args:
    state: GameState object to send
    
Returns:
    b...
- `get_game_state(1 args)`: Get current game state...
- `get_combat_stats(1 args)`: Get combat statistics...
- `get_learning_progress(1 args)`: Get learning progress...
- `set_strategy_mode(2 args)`: Set strategy mode...
- `resume_game(1 args)`: Resume game...
- `pause_game(1 args)`: Pause game...

### Functions

#### `init_connector`

Initialize the global bot connector instance.

Args:
    api_url: Base URL of the FastAPI server
    
Returns:
    BotApiConnector: The initialized connector instance

**Parameters**:

- `api_url`: str

---

## Module: `monitoring.compare_server_android_data`

서버와 Android 앱 간 데이터 비교 도구

서버가 보내는 JSON 데이터와 Android 앱이 받은 JSON 데이터를 비교합니다.

### Functions

#### `get_server_response`

서버에서 실제로 보내는 JSON 데이터 가져오기

#### `normalize_data`

데이터를 정규화 (필드명 통일, 타입 변환)

**Parameters**:

- `data`: Dict[str, Any]

#### `compare_data`

두 데이터를 비교

**Parameters**:

- `server_data`: Dict[str, Any]
- `android_data`: Dict[str, Any]

#### `print_comparison_result`

비교 결과 출력

**Parameters**:

- `server_data`: Dict[str, Any]
- `comparison`: Dict[str, Any]

#### `parse_android_log`

Android 로그에서 JSON 데이터 추출

**Parameters**:

- `log_text`: str

#### `main`

---

## Module: `monitoring.config_server`

Config Server - Dynamic URL Management System
Ngrok URL을 외부 저장소(Github Gist/Pastebin)에 저장하여
앱을 다시 빌드하지 않고도 URL을 업데이트할 수 있게 합니다.

사용 방법:
1. Github Gist 사용 (권장):
   - https://gist.github.com 에서 새 Gist 생성
   - 파일명: server_url.txt
   - Gist ID를 환경변수에 설정: export GIST_ID="your-gist-id"
   - Personal Access Token 설정: export GITHUB_TOKEN="your-token"

2. Pastebin 사용 (대안):
   - https://pastebin.com 에서 API 키 발급
   - 환경변수 설정: export PASTEBIN_API_KEY="your-api-key"

3. 로컬 파일 사용 (개발용):
   - .config_server_url.txt 파일에 URL 저장

### Classes

#### `ConfigServer`

동적 URL 관리 서버

**Methods**:

- `__init__(1 args)`
- `_get_ngrok_url(1 args)`: Ngrok URL 가져오기...
- `_update_github_gist(2 args)`: Github Gist에 URL 업데이트...
- `_update_pastebin(2 args)`: Pastebin에 URL 업데이트...
- `_update_local_file(2 args)`: 로컬 파일에 URL 저장 (개발용)...
- `update_server_url(1 args)`: 서버 URL 업데이트 (우선순위: Gist > Pastebin > 로컬 파일)...
- `get_server_url(1 args)`: 저장된 서버 URL 가져오기...

### Functions

#### `main`

메인 함수

---

## Module: `monitoring.dashboard`

Mobile Dashboard Server
Real-time monitoring for StarCraft 2 Wicked Zerg AI

### Classes

#### `DashboardHandler`

Dashboard request handler with API endpoints

**Bases**: http.server.SimpleHTTPRequestHandler

**Methods**:

- `__init__(1 args)`
- `end_headers(1 args)`: Override to add UTF-8 charset to all responses...
- `translate_path(2 args)`: Override to serve /static from project root as well as WEB_DIR...
- `guess_type(2 args)`: Override to force UTF-8 charset for text files...
- `do_GET(1 args)`: Handle GET requests with API endpoints...
- `log_message(2 args)`: Format log messages...
- `do_POST(1 args)`: Handle POST endpoints...

#### `ReusableTCPServer`

**Bases**: socketserver.TCPServer

### Functions

#### `_build_game_state`

**Parameters**:

- `base_dir`: Path

#### `_build_combat_stats`

**Parameters**:

- `base_dir`: Path

#### `_build_learning_progress`

**Parameters**:

- `base_dir`: Path

#### `ensure_html_exists`

Create index.html if missing

#### `find_available_server`

Try to bind a server from start_port upward, returning (server, port).

**Parameters**:

- `start_port`: int
- `handler`: http.server.BaseHTTPRequestHandler
- `max_tries`: int

#### `write_port_file`

Write the selected port to a file for other scripts (e.g., ngrok).

**Parameters**:

- `port`: int

#### `broadcast_game_state`

Continuously broadcast game state to WebSocket clients.

**Parameters**:

- `base_dir`: Path

---

## Module: `monitoring.dashboard_api`

Dashboard API Server - sc2AIagent Integration
Real-time game state, combat stats, and AI control API

### Classes

#### `UTF8JSONResponse`

**Bases**: StarletteJSONResponse

**Methods**:

- `render(2 args)`

### Functions

#### `verify_credentials`

Basic Auth 인증 검증

**Parameters**:

- `credentials`: HTTPBasicCredentials

#### `_get_win_rate`

Get win rate from training stats

**Parameters**:

- `base_dir`: Path

---

## Module: `monitoring.get_ngrok_url`

Ngrok 터널 URL 가져오기
터널이 실행 중일 때 현재 URL을 반환합니다.

### Functions

#### `get_ngrok_url_from_api`

Ngrok API에서 현재 터널 URL 가져오기

#### `get_ngrok_url_from_file`

저장된 파일에서 터널 URL 가져오기

#### `main`

메인 함수

---

## Module: `monitoring.manus_dashboard_client`

Manus Dashboard Client

SC2 AI 봇의 데이터를 Manus 웹 호스팅 대시보드(tRPC API)로 전송하는 클라이언트

### Classes

#### `ManusDashboardClient`

Manus 대시보드 tRPC API 클라이언트

**Methods**:

- `__init__(4 args)`: Manus 대시보드 클라이언트 초기화

Args:
    base_url: Manus 대시보드 URL
    api_key: API 인증 키 (선택적, 우선순위: 인자 > 환경 변...
- `_load_api_key(1 args)`: API 키 로드 (환경 변수 우선, 파일 fallback)

Returns:
    API 키 또는 None...
- `_call_trpc(4 args)`: tRPC 프로시저 호출

Args:
    procedure: tRPC 프로시저 이름 (예: "game.createSession")
    input_data: 입력 데이터
   ...
- `create_game_session(12 args)`: 게임 세션 생성 (게임 종료 시 호출)

Args:
    map_name: 맵 이름
    enemy_race: 상대 종족
    final_minerals: 최종 미네랄
   ...
- `create_training_episode(6 args)`: 학습 에피소드 생성

Args:
    episode: 에피소드 번호
    reward: 보상
    loss: 손실
    win_rate: 승률 (0.0 ~ 1.0)
    ...
- `update_bot_config(7 args)`: 봇 설정 업데이트

Args:
    config_name: 설정 이름
    strategy: 전략
    build_order: 빌드 오더 (선택적)
    descriptio...
- `create_arena_match(5 args)`: AI Arena 경기 생성

Args:
    opponent: 상대 봇 이름
    result: 경기 결과 ("Victory" or "Defeat")
    elo_change...
- `update_game_state(8 args)`: 실시간 게임 상태 업데이트

Args:
    minerals: 미네랄
    vespene: 가스
    supply_used: 사용 인구수
    supply_cap: 최대 인...
- `health_check(1 args)`: 대시보드 연결 상태 확인

Returns:
    서버 응답 여부...

### Functions

#### `create_client_from_env`

환경 변수에서 클라이언트 생성

환경 변수:
    MANUS_DASHBOARD_URL: Manus 대시보드 URL
    MANUS_DASHBOARD_API_KEY: API 키 (선택적)
    MANUS_DASHBOARD_ENABLED: 활성화 여부 (1 또는 0)

Returns:
    ManusDashboardClient 인스턴스 또는 None

---

## Module: `monitoring.manus_sync`

Manus Dashboard Sync

로컬 게임 상태를 Manus 대시보드로 주기적으로 동기화하는 모듈

### Classes

#### `ManusSyncService`

Manus 대시보드 동기화 서비스

**Methods**:

- `__init__(2 args)`: 동기화 서비스 초기화

Args:
    sync_interval: 동기화 간격 (초)...
- `_get_game_state(1 args)`: 현재 게임 상태 가져오기

Returns:
    게임 상태 딕셔너리 또는 None...
- `_sync_loop(1 args)`: 동기화 루프...
- `start(1 args)`: 동기화 서비스 시작...
- `stop(1 args)`: 동기화 서비스 중지...

### Functions

#### `start_manus_sync`

Manus 동기화 서비스 시작

Args:
    sync_interval: 동기화 간격 (초)

**Parameters**:

- `sync_interval`: int

#### `stop_manus_sync`

Manus 동기화 서비스 중지

---

## Module: `monitoring.monitoring_utils`

Monitoring utilities for file-based data access.

Centralizes base directory resolution and JSON file loading used by
both dashboard.py (HTTP server) and dashboard_api.py (FastAPI).

### Functions

#### `get_base_dir`

Resolve the base directory for monitoring data.

Precedence:
1) MONITORING_BASE_DIR env var (absolute or relative to CWD)
2) Current working directory (training process location)

#### `load_json`

**Parameters**:

- `path`: Path

#### `find_latest_instance_status`

Find latest instance_*_status.json.

Looks under stats/ first, then falls back to root directory.
Returns parsed JSON dict or None.

**Parameters**:

- `base_dir`: Path

#### `load_training_stats`

Load training_stats.json from data/ or root directory.

**Parameters**:

- `base_dir`: Path

---

## Module: `monitoring.ngrok_tunnel`

Ngrok Tunnel Manager - LTE/5G IoT 연동
외부 네트워크에서 로컬 서버에 안전하게 접속할 수 있도록 ngrok 터널을 관리합니다.

### Classes

#### `NgrokTunnel`

Ngrok 터널 관리 클래스

**Methods**:

- `__init__(3 args)`: Ngrok 터널 초기화

Args:
    local_port: 로컬 서버 포트 (기본: 8000)
    auth_token: Ngrok 인증 토큰 (없으면 환경 변수 또는 파일...
- `_load_auth_token(1 args)`: Ngrok 인증 토큰 로드...
- `is_ngrok_installed(1 args)`: Ngrok이 설치되어 있는지 확인...
- `start_tunnel(1 args)`: Ngrok 터널 시작

Returns:
    성공 여부...
- `get_tunnel_url(1 args)`: Ngrok 터널 URL 가져오기

Returns:
    터널 URL (예: https://xxxx-xx-xx-xx-xx.ngrok.io)...
- `get_tunnel_info(1 args)`: 터널 상세 정보 가져오기

Returns:
    터널 정보 딕셔너리...
- `stop_tunnel(1 args)`: Ngrok 터널 중지...
- `save_tunnel_url(2 args)`: 터널 URL을 파일에 저장

Args:
    file_path: 저장할 파일 경로 (None이면 기본 경로)...

### Functions

#### `main`

메인 함수 - Ngrok 터널 시작

---

## Module: `monitoring.remote_client`

Remote Dashboard Client

로컬 AI 봇의 데이터를 Manus 웹 호스팅 대시보드로 전송하는 클라이언트 모듈

### Classes

#### `RemoteDashboardClient`

원격 대시보드 클라이언트

**Methods**:

- `__init__(5 args)`: 원격 대시보드 클라이언트 초기화

Args:
    base_url: 원격 서버 URL (예: https://sc2aidash-bncleqgg.manus.space)
    api...
- `_make_request(5 args)`: HTTP 요청 실행 (재시도 로직 포함)

Args:
    method: HTTP 메서드 (GET, POST, PUT, DELETE)
    endpoint: API 엔드포인트
...
- `send_game_state(2 args)`: 게임 상태를 원격 서버로 전송

Args:
    game_state: 게임 상태 데이터
    
Returns:
    전송 성공 여부...
- `send_telemetry(2 args)`: 텔레메트리 데이터를 원격 서버로 전송

Args:
    telemetry_data: 텔레메트리 데이터 리스트
    
Returns:
    전송 성공 여부...
- `send_stats(2 args)`: 통계 데이터를 원격 서버로 전송

Args:
    stats: 통계 데이터
    
Returns:
    전송 성공 여부...
- `health_check(1 args)`: 원격 서버 연결 상태 확인

Returns:
    서버 응답 여부...

### Functions

#### `create_client_from_env`

환경 변수에서 클라이언트 생성

환경 변수:
    REMOTE_DASHBOARD_URL: 원격 서버 URL
    REMOTE_DASHBOARD_API_KEY: API 키 (선택적)
    REMOTE_DASHBOARD_ENABLED: 활성화 여부 (1 또는 0)
    REMOTE_SYNC_INTERVAL: 동기화 간격 (초)

Returns:
    RemoteDashboardClient 인스턴스 또는 None

---

## Module: `monitoring.start_with_ngrok`

대시보드 서버 + Ngrok 터널 자동 시작
Dashboard Server + Ngrok Tunnel Auto-Start

로컬 서버와 ngrok 터널을 함께 시작하여 외부 네트워크에서 접속 가능하게 합니다.

### Functions

#### `start_dashboard_server`

대시보드 서버 시작

**Parameters**:

- `port`: int

#### `main`

메인 함수

---

## Module: `monitoring.telemetry_logger`

Telemetry Logger - Training statistics and data recording system
Collects and stores gameplay data for performance analysis and learning improvement.

Core features:
    1. In-game telemetry data collection (every 100 frames)
    2. Final statistics saving at game end
    3. JSON/CSV format data export
    4. Win rate and match history tracking

### Classes

#### `TelemetryLogger`

Logger for training statistics and telemetry data

**Methods**:

- `__init__(3 args)`: Initialize TelemetryLogger

Args:
    bot: WickedZergBotPro instance
    instance_id: Instance ID (f...
- `should_log_telemetry(2 args)`: Determine if telemetry should be logged

Args:
    iteration: Current game frame

Returns:
    bool:...
- `log_game_state(2 args)`: Log current game state to telemetry

Args:
    combat_unit_types: Set of combat unit types...
- `record_game_result(4 args)`: Record game result to training_stats.json

Args:
    game_result: Game result (Victory/Defeat/Tie)
 ...
- `get_win_rate(1 args)`: Calculate current win rate

Returns:
    float: Win rate (0.0 ~ 1.0)...
- `get_statistics_summary(1 args)`: Get statistics summary

Returns:
    Dict: Statistics information...
- `print_statistics(1 args)`: Print statistics information...
- `get_final_stats_dict(1 args)`: Create final statistics dictionary at game end

Returns:
    Dict: Final statistics (None if failed)...
- `clear_telemetry(1 args)`: Clear telemetry data (at new game start)...

---

## Module: `monitoring.telemetry_logger_atomic`

Telemetry Logger with Atomic Write - Thread-safe file writing
Atomic write pattern을 사용하여 파일 쓰기 중 읽기 오류를 방지합니다.

### Functions

#### `atomic_write_json`

Atomic write for JSON files

임시 파일에 쓰고 완료 후 원본 파일로 교체하여
읽기 중 쓰기가 발생해도 데이터 무결성을 보장합니다.

Args:
    filepath: 대상 파일 경로
    data: 저장할 데이터 (JSON 직렬화 가능)

Returns:
    bool: 성공 여부

**Parameters**:

- `filepath`: Path
- `data`: Any

#### `atomic_write_csv`

Atomic write for CSV files

Args:
    filepath: 대상 파일 경로
    data: 저장할 데이터 (리스트의 딕셔너리)

Returns:
    bool: 성공 여부

**Parameters**:

- `filepath`: Path
- `data`: List[Dict[str, Any]]

#### `atomic_append_jsonl`

Atomic append for JSONL files (JSON Lines)

JSONL 파일에 한 줄씩 추가하는 경우에도 원자적 쓰기를 보장합니다.

Args:
    filepath: 대상 파일 경로
    data: 추가할 데이터 (딕셔너리)

Returns:
    bool: 성공 여부

**Parameters**:

- `filepath`: Path
- `data`: Dict[str, Any]

#### `patch_telemetry_logger`

기존 telemetry_logger.py의 save_telemetry 메서드를
atomic write를 사용하도록 패치합니다.

---

## Module: `monitoring.update_android_ngrok_url`

Android 앱의 Ngrok URL 자동 업데이트
Ngrok 터널 URL을 Android 앱 코드에 자동으로 반영합니다.

### Functions

#### `get_ngrok_url`

현재 Ngrok 터널 URL 가져오기

#### `update_android_api_client`

Android ApiClient.kt 파일 업데이트

**Parameters**:

- `ngrok_url`: str

#### `update_manus_api_client`

Android ManusApiClient.kt 파일 업데이트

**Parameters**:

- `ngrok_url`: str

#### `main`

메인 함수

---

## Module: `production_manager`

### Classes

#### `ProductionManager`

**Methods**:

- `__init__(2 args)`
- `_load_curriculum_level(1 args)`: Curriculum Learning 레벨 로드

Returns:
    int: 현재 curriculum 레벨 인덱스 (0=VeryEasy, 5=CheatInsane)...
- `check_duplicate_tech_buildings(1 args)`
- `_should_use_basic_units(1 args)`: 난이도가 낮을 때 기본 물량(저글링/바퀴) 중심으로 생산할지 결정

Returns:
    bool: True면 기본 물량 중심, False면 정상 생산...
- `_should_force_high_tech_production(1 args)`: Force tech production when army is overly zergling-heavy and gas is floating....
- `_select_counter_unit_by_matchup(1 args)`: Select best high-tech unit based on enemy composition (counter-based selection)....
- `_ensure_build_reservations(1 args)`: Ensure shared reservation map exists and return it....
- `_cleanup_build_reservations(1 args)`: Remove stale reservations to avoid blocking rebuilds after failed attempts....
- `_reserve_building(2 args)`: Reserve a structure type so parallel managers don't issue duplicate builds....
- `_can_build_safely(4 args)`: 중복 건설을 원천 차단하는 안전한 건설 체크 함수

Args:
    structure_id: 건설할 건물 타입
    check_workers: 일벌레 명령 체크 여부 (기본값:...
- `_check_duplicate_construction(3 args)`: Enhanced duplicate construction detection

Returns True if construction should be SKIPPED (duplicate...
- `_get_counter_units(2 args)`: 상성 기반 유닛 선택

Args:
    game_phase: 현재 게임 단계

Returns:
    List[UnitTypeId]: 생산할 유닛 목록 (우선순위 순)...
- `_calculate_tech_priority_score(1 args)`: 가치 기반 의사결정: 테크 건물 건설의 가치를 계산

봇이 스스로 "지금 테크를 올리는 것이 유닛을 뽑는 것보다 가치 있는가?"를 판단합니다.

Returns:
    float:...
- `_calculate_production_priority_score(1 args)`: 가치 기반 의사결정: 유닛 생산의 가치를 계산

Returns:
    float: 유닛 생산의 가치 점수 (0.0 ~ 100.0)...
- `_get_required_building(2 args)`: Return building required for unit production...
- `_has_required_building(2 args)`: Check if required building exists (allows sticky flag and progress)...
- `get_production_status(1 args)`: Return current production status...
- `set_enemy_race(2 args)`: Set opponent race...
- `get_build_order_timing(1 args)`: 빌드 오더 타이밍 정보 반환 (신경망 학습용)

Returns:
    dict: 빌드 오더 타이밍 정보 (supply 및 time 값 포함)...

---

## Module: `queen_manager`

### Classes

#### `QueenManager`

**Methods**:

- `__init__(2 args)`

---

## Module: `rogue_tactics_manager`

ÀÌº´·Ä(Rogue) ¼±¼ö Àü¼ú ±¸Çö ¸Å´ÏÀú

ÇÙ½É Àü¼ú:
1. ¸Íµ¶Ãæ µå¶ø (Baneling Drop): Àû º´·ÂÀÌ ÀüÁøÇÏ´Â Å¸ÀÌ¹Ö¿¡ µå¶ø
2. ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿: ÀûÀÇ ½Ã¾ß ¹üÀ§¸¦ ÇÇÇØ µå¶ø ÁöÁ¡±îÁö ÀÌµ¿
3. ¶ó¹Ù ¼¼ÀÌºù: ±³Àü Á÷Àü ¶ó¹Ù¸¦ ¸ð¾ÆµÎ¾ú´Ù°¡ µå¶ø ÈÄ Æø¹ßÀû »ý»ê
4. ÈÄ¹Ý ¿î¿µ: Á¡¸· °¨Áö ±â¹Ý ÀÇ»ç°áÁ¤

### Classes

#### `RogueTacticsManager`

ÀÌº´·Ä(Rogue) ¼±¼ö Àü¼ú ±¸Çö ¸Å´ÏÀú

ÁÖ¿ä ±â´É:
- ¸Íµ¶Ãæ µå¶ø Å¸ÀÌ¹Ö °¨Áö ¹× ½ÇÇà
- ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿ °æ·Î Å½»ö
- ¶ó¹Ù ¼¼ÀÌºù ÆÐÅÏ °ü¸®
- Á¡¸· ±â¹Ý Àû º´·Â °¨Áö

**Methods**:

- `__init__(2 args)`
- `_check_overlord_speed_upgrade(1 args)`: ´ë±ºÁÖ ¼Ó¾÷ »óÅÂ È®ÀÎ...
- `_detect_enemy_on_creep(1 args)`: Àû º´·ÂÀÌ Á¡¸·¿¡ ´ê¾Ò´ÂÁö °¨Áö

Rogue Àü¼ú: Àû º´·ÂÀÌ ³» ±âÁö ¾Õ¸¶´ç Á¡¸· ³¡¿¡ µµ´ÞÇßÀ» ¶§ µå¶ø À¯´Ö...
- `_can_execute_drop(1 args)`: µå¶ø ½ÇÇà °¡´É ¿©ºÎ È®ÀÎ...
- `_find_drop_target(1 args)`: µå¶ø Å¸°Ù °áÁ¤

¿ì¼±¼øÀ§:
1. Àû º»Áø ÀÏ²Û ÁýÁß Áö¿ª
2. Àû È®Àå ±âÁö ÀÏ²Û
3. Àû ÁÖ¿ä °Ç¹° (°ø¼º ÀüÂ÷ ...
- `_calculate_stealth_path(3 args)`: ½Ã¾ß ¹Û ¿ìÈ¸ ±âµ¿ °æ·Î °è»ê

Rogue Àü¼ú: ÀûÀÇ ½Ã¾ß ¹üÀ§¸¦ ÇÇÇØ ¸Ê °¡ÀåÀÚ¸®¸¦ ÀÌ¿ëÇÏ¿© ÀÌµ¿

¾Ë°í¸®Áò...
- `should_save_larva(1 args)`: ¶ó¹Ù ¼¼ÀÌºù ¸ðµå ¿©ºÎ ¹ÝÈ¯...
- `get_enemy_on_creep_status(1 args)`: ÀûÀÌ Á¡¸·¿¡ ÀÖ´ÂÁö, ÀüÁø ÁßÀÎÁö ¹ÝÈ¯...
- `get_drop_readiness(1 args)`: µå¶ø ÁØºñ »óÅÂ ¹ÝÈ¯...

---

## Module: `run`

### Functions

#### `_ensure_sc2_path`

Set SC2PATH environment variable - search via Windows Registry or common paths

#### `create_bot`

AI Arena entry point - Create bot instance.
This function can be called directly by AI Arena if needed.

#### `main`

Main entry point for bot execution.
Supports both AI Arena ladder mode and local testing.

---

## Module: `sc2_env.__init__`

SC2 Environment module.
Provides mock environment for testing without actual SC2 installation.

---

## Module: `sc2_env.mock_env`

Mock SC2 Environment for testing without actual StarCraft II installation.
This module provides a lightweight simulation environment for testing bot logic.

### Classes

#### `Race`

Mock race enum.

**Bases**: Enum

#### `MockUnit`

Mock unit representation.

#### `MockGameState`

Mock game state for testing.

#### `MockSC2Env`

Mock SC2 Environment for testing bot logic without SC2 runtime.

This class simulates basic SC2 game state and allows testing
of bot decision-making logic in isolation.

Example:
    >>> env = MockSC2Env()
    >>> state = env.reset()
    >>> action = "train_drone"
    >>> new_state = env.step(action)

**Methods**:

- `__init__(2 args)`: Initialize mock SC2 environment.

Args:
    initial_minerals: Starting mineral count...
- `reset(1 args)`: Reset environment to initial state.

Returns:
    Dictionary containing game state...
- `step(2 args)`: Execute an action and update game state.

Args:
    action: Action to execute (e.g., "train_drone", ...
- `_state_to_dict(1 args)`: Convert game state to dictionary....
- `can_afford(3 args)`: Check if we can afford a cost.

Args:
    cost_minerals: Mineral cost
    cost_vespene: Vespene gas ...
- `get_supply_left(1 args)`: Get remaining supply capacity....

#### `MockBotAI`

Mock BotAI interface for testing manager logic.

This class provides a minimal interface that mimics sc2.bot_ai.BotAI
for testing purposes without requiring actual SC2 installation.

**Methods**:

- `__init__(1 args)`: Initialize mock bot....
- `minerals(1 args)`: Get current minerals....
- `vespene(1 args)`: Get current vespene gas....
- `supply_used(1 args)`: Get used supply....
- `supply_cap(1 args)`: Get supply capacity....
- `supply_left(1 args)`: Get remaining supply....
- `can_afford(2 args)`: Check if we can afford a unit type.

Args:
    unit_type: Unit type to check (e.g., "drone", "zergli...

---

## Module: `scouting_system`

================================================================================
                    Scouting System (scouting_system.py)
================================================================================
Unified scouting system that manages dynamic build order transitions and
heatmap-based predictive scouting.

Core Features:
    1. Initial scouting (Overlord/Zergling)
    2. Event-based scouting (Idle time/Tech scan)
    3. Heatmap-based predictive scouting (Grid-based area management)
    4. Enemy composition analysis and threat assessment
    5. Dynamic build order transition triggers
================================================================================

### Classes

#### `GridCell`

Grid cell data

#### `ScoutingSystem`

Unified scouting system

Integrated scouting management system combining ScoutManager and HeatmapScout functionality.

**Methods**:

- `__init__(2 args)`: Args:
    bot: Main bot instance...
- `initialize(1 args)`: Initialize - Set scout locations and initialize heatmap...
- `_initialize_heatmap(1 args)`: Initialize heatmap grid...
- `_mark_expansion_locations(1 args)`: Mark expansion locations...
- `_mark_enemy_base_area(1 args)`: Mark enemy base area...
- `_position_to_grid(2 args)`: Convert coordinates to grid key...
- `_update_heatmap(1 args)`: Update heatmap...
- `get_next_scout_target(1 args)`: Return next scout target location based on heatmap

Returns:
    Point2: Scout target location, or N...
- `_detect_enemy(1 args)`: Detect enemy units and buildings (including opponent strategy recording)...
- `_infer_strategy_from_building(2 args)`: Infer opponent strategy from building type...
- `_identify_enemy_race(2 args)`: Identify enemy race...
- `_evaluate_threat(1 args)`: Threat assessment - Enemy composition analysis...
- `_detect_rush(1 args)`: Detect rush...
- `_detect_expansion(1 args)`: Detect enemy expansion...
- `_update_context(2 args)`: Update Blackboard context...
- `_recommend_game_phase(1 args)`: Recommend game phase based on scouting information...
- `get_scout_status(1 args)`: Return current scouting status...
- `get_coverage_percent(1 args)`: Return map exploration percentage...
- `get_stale_cell_count(1 args)`: Return count of stale cells...

---

## Module: `services.__init__`

Hybrid Architecture Services Package

This package provides distributed services for the SC2 bot:
- TelemetryService: Remote telemetry logging service
- LearningService: Distributed learning service
- ServiceRegistry: Service discovery and connection management

---

## Module: `services.hybrid_config`

Hybrid Architecture Configuration

Controls whether services run locally (monolithic) or distributed (hybrid).

### Classes

#### `HybridConfig`

Configuration for hybrid architecture mode.

When enabled, external services (monitoring, learning, telemetry) 
can run as separate processes/servers.

**Methods**:

- `from_env(1 args)`: Load configuration from environment variables.

Environment variables:
- HYBRID_MODE: "local" or "hy...
- `from_file(2 args)`: Load configuration from JSON file.

Args:
    config_path: Path to JSON configuration file...
- `is_hybrid_mode(1 args)`: Check if hybrid mode is enabled....
- `is_local_mode(1 args)`: Check if local (monolithic) mode is enabled....

### Functions

#### `get_config`

Get global hybrid configuration instance.

#### `set_config`

Set global hybrid configuration instance.

**Parameters**:

- `config`: HybridConfig

---

## Module: `services.learning_service_client`

Learning Service Client

Sends learning data to a remote learning service for distributed training.
Falls back to local training if service is unavailable.

### Classes

#### `LearningServiceClient`

Client for sending learning data to a remote learning service.

When hybrid mode is enabled, sends training data to remote service.
When local mode or service unavailable, falls back to local training.

**Methods**:

- `__init__(2 args)`: Initialize LearningServiceClient.

Args:
    service_url: Learning service URL (optional, uses confi...
- `_check_service_availability(1 args)`: Check if learning service is available.

Returns:
    bool: True if service is available...
- `send_training_data(6 args)`: Send training data to remote learning service.

Args:
    game_result: Game result ("Victory" or "De...
- `_send_to_service(2 args)`: Send training data to remote service.

Args:
    data: Training data dictionary
    
Returns:
    bo...
- `get_model_update(2 args)`: Get updated model from remote learning service.

Args:
    model_path: Local model path
    
Returns...

---

## Module: `services.service_registry`

Service Registry

Manages service discovery and connection for hybrid architecture.

### Classes

#### `ServiceInfo`

Information about a registered service.

**Methods**:

- `__post_init__(1 args)`

#### `ServiceRegistry`

Service registry for discovering and managing distributed services.

In hybrid mode, services register themselves and can be discovered by clients.
In local mode, registry is not used.

**Methods**:

- `__init__(2 args)`: Initialize ServiceRegistry.

Args:
    registry_url: Service registry URL (optional, uses config if ...
- `_check_registry_availability(1 args)`: Check if service registry is available.

Returns:
    bool: True if registry is available...
- `register_service(4 args)`: Register a service with the registry.

Args:
    name: Service name (e.g., "telemetry", "learning", ...
- `_register_to_registry(2 args)`: Register service to remote registry.

Args:
    service_info: Service information
    
Returns:
    ...
- `discover_service(2 args)`: Discover a service by name.

Args:
    name: Service name
    
Returns:
    ServiceInfo if found, No...
- `_discover_from_registry(2 args)`: Discover service from remote registry.

Args:
    name: Service name
    
Returns:
    ServiceInfo i...
- `list_services(1 args)`: List all registered services.

Returns:
    List of ServiceInfo...
- `_list_from_registry(1 args)`: List services from remote registry.

Returns:
    List of ServiceInfo...

---

## Module: `services.telemetry_service_client`

Telemetry Service Client

Sends telemetry data to a remote telemetry service via HTTP API.
Falls back to local file logging if service is unavailable.

### Classes

#### `TelemetryServiceClient`

Client for sending telemetry data to a remote service.

When hybrid mode is enabled, sends data to remote service.
When local mode or service unavailable, falls back to local file logging.

**Methods**:

- `__init__(2 args)`: Initialize TelemetryServiceClient.

Args:
    service_url: Telemetry service URL (optional, uses con...
- `_check_service_availability(1 args)`: Check if telemetry service is available.

Returns:
    bool: True if service is available...
- `send_telemetry(2 args)`: Send telemetry data to remote service or save locally.

Args:
    telemetry_data: Telemetry data dic...
- `_flush_buffer(1 args)`: Flush telemetry buffer to service or local file.

Returns:
    bool: True if flushed successfully...
- `_send_to_service(2 args)`: Send telemetry data to remote service.

Args:
    data: List of telemetry data dictionaries
    
Ret...
- `_save_to_local(2 args)`: Save telemetry data to local file (fallback).

Args:
    data: List of telemetry data dictionaries...
- `flush(1 args)`: Force flush remaining buffer.

Returns:
    bool: True if flushed successfully...
- `close(1 args)`: Close client and flush remaining data....

---

## Module: `spell_unit_manager`

Spell Unit Manager - Optimized targeting for spell units (Infestor, Viper)

CRITICAL: Spell units require less frequent targeting updates than regular units
to reduce CPU load and allow proper spell cooldown management.

Features:
- Infestor: Neural Parasite, Fungal Growth
- Viper: Abduct, Parasitic Bomb, Blinding Cloud
- Optimized targeting cycle (16 frames instead of every frame)

### Classes

#### `SpellUnitManager`

Spell Unit Manager - Optimized spell unit control

CRITICAL: Spell units are controlled less frequently (16 frames) than regular units
to reduce CPU load and allow proper spell cooldown management.

**Methods**:

- `__init__(2 args)`
- `_find_best_fungal_target(3 args)`: Find best position for Fungal Growth to hit multiple enemies...
- `_find_best_blinding_cloud_position(3 args)`: Find best position for Blinding Cloud to cover multiple enemies...

---

## Module: `telemetry_logger`

Telemetry Logger - Training statistics and data recording system
Collects and stores gameplay data for performance analysis and learning improvement.

Core features:
    1. In-game telemetry data collection (every 100 frames)
    2. Final statistics saving at game end
    3. JSON/CSV format data export
    4. Win rate and match history tracking

### Classes

#### `TelemetryLogger`

Logger for training statistics and telemetry data

**Methods**:

- `__init__(3 args)`: Initialize TelemetryLogger

Args:
    bot: WickedZergBotPro instance
    instance_id: Instance ID (f...
- `should_log_telemetry(2 args)`: Determine if telemetry should be logged

Args:
    iteration: Current game frame

Returns:
    bool:...
- `log_game_state(2 args)`: Log current game state to telemetry

Args:
    combat_unit_types: Set of combat unit types...
- `_calculate_swarm_metrics(4 args)`: Calculate swarm control algorithm performance metrics.

This provides data to prove whether swarm co...
- `record_game_result(4 args)`: Record game result to training_stats.json

Args:
    game_result: Game result (Victory/Defeat/Tie)
 ...
- `get_win_rate(1 args)`: Calculate current win rate

Returns:
    float: Win rate (0.0 ~ 1.0)...
- `get_statistics_summary(1 args)`: Get statistics summary

Returns:
    Dict: Statistics information...
- `print_statistics(1 args)`: Print statistics information...
- `get_final_stats_dict(1 args)`: Create final statistics dictionary at game end

Returns:
    Dict: Final statistics (None if failed)...
- `_analyze_swarm_performance_from_telemetry(1 args)`: Analyze swarm control performance from collected telemetry data.

This provides evidence of whether ...
- `clear_telemetry(1 args)`: Clear telemetry data (at new game start)...

---

## Module: `tools.analyze_and_cleanup`

Analyze and identify files for cleanup
불필요한 파일 분석 및 제거 대상 식별

### Functions

#### `analyze_project`

Analyze project structure and identify cleanup targets

#### `generate_report`

Generate cleanup report

**Parameters**:

- `cleanup_targets`

#### `main`

Main function

---

## Module: `tools.analyze_tech_unit_production`

Analyze why high tech units are not being produced

### Functions

#### `analyze_tech_unit_issues`

Analyze potential issues with tech unit production

---

## Module: `tools.analyze_telemetry`

Telemetry Analysis Tool

Analyzes telemetry data to answer:
1. "Why did we lose?" - Loss reason analysis
2. "Did swarm control algorithms work as expected?" - Swarm control performance analysis
3. Game performance metrics and trends

Usage:
    python tools/analyze_telemetry.py --telemetry telemetry_0.json
    python tools/analyze_telemetry.py --stats training_stats.json
    python tools/analyze_telemetry.py --all  # Analyze all available data

### Classes

#### `TelemetryAnalyzer`

Analyze telemetry data for performance insights

**Methods**:

- `__init__(3 args)`
- `load_telemetry(2 args)`: Load telemetry JSON file...
- `load_stats(2 args)`: Load training stats JSONL file...
- `analyze_loss_reasons(1 args)`: Analyze why games were lost...
- `analyze_swarm_control_performance(1 args)`: Analyze swarm control algorithm performance...
- `analyze_game_performance(1 args)`: Analyze overall game performance metrics...
- `generate_report(1 args)`: Generate comprehensive analysis report...

### Functions

#### `find_telemetry_files`

Find all telemetry JSON files

**Parameters**:

- `directory`: Path

#### `find_stats_files`

Find all training stats files

**Parameters**:

- `directory`: Path

#### `main`

#### `calculate_trend`

**Parameters**:

- `values`: List[float]

---

## Module: `tools.api_key_access_control`

### Classes

#### `ApiKeyAccessControl`

API 키 접근 제어 클래스

**Methods**:

- `__init__(1 args)`
- `_load_allowed_ips(1 args)`: 허용된 IP 주소 목록 로드...
- `_load_allowed_domains(1 args)`: 허용된 도메인 목록 로드...
- `is_allowed(3 args)`: 접근이 허용되었는지 확인...

---

## Module: `tools.api_key_monitoring`

### Functions

#### `log_api_key_usage`

API 키 사용 로그 기록

**Parameters**:

- `api_name`
- `success`
- `error`

---

## Module: `tools.api_key_usage_limiter`

### Classes

#### `ApiKeyUsageLimiter`

API 키 사용량 제한 클래스

**Methods**:

- `__init__(3 args)`
- `_load_usage(1 args)`: 사용량 로드...
- `_save_usage(1 args)`: 사용량 저장...
- `can_make_request(1 args)`: 요청 가능한지 확인...
- `record_request(1 args)`: 요청 기록...

---

## Module: `tools.apply_code_improvements`

코드 품질 개선 적용 도구

COMPREHENSIVE_CODE_IMPROVEMENT_REPORT.md를 기반으로
실제 개선 작업을 수행합니다.

### Classes

#### `CodeImprovementApplier`

코드 개선 적용기

**Methods**:

- `__init__(2 args)`
- `remove_unused_imports_from_file(3 args)`: 파일에서 사용하지 않는 import 제거...
- `fix_code_style_issues(3 args)`: 코드 스타일 이슈 수정...
- `apply_black_formatting(1 args)`: Black 포맷터 적용...

### Functions

#### `main`

메인 함수

---

## Module: `tools.arena_update`

Arena Update Packager

Creates a timestamped AI Arena update package using existing packager,
then moves the generated ZIP into a dedicated AI_Arena_Updates folder.

Usage:
  python tools/arena_update.py [--keep-submission] [--notes PATH]

Options:
  --keep-submission   Keep the temporary aiarena_submission folder
  --notes PATH        Optional path to a markdown/text file to copy into
                      the update folder with a timestamped filename

### Functions

#### `timestamp`

#### `find_latest_zip`

**Parameters**:

- `root`: Path
- `bot_prefix`: str

#### `copy_notes`

**Parameters**:

- `src`: Path
- `dst_dir`: Path

#### `main`

---

## Module: `tools.auto_classify_drive`

Drive File Auto Classification Script
- Classify files by extension across drives
- Organize by category: coding, documents, games, etc.
- Date-based folder structure

### Classes

#### `DriveClassifier`

**Methods**:

- `__init__(4 args)`
- `log(2 args)`: Logging with timestamp...
- `should_skip(2 args)`: Check if path should be skipped...
- `get_category(2 args)`: Determine file category...
- `classify_file(2 args)`: Classify and move file...
- `scan_and_classify(2 args)`: Scan drives and classify files...
- `generate_report(1 args)`: Generate classification report...

### Functions

#### `main`

---

## Module: `tools.auto_commit_after_training`

Auto Commit After Training - 자동 커밋 스크립트

훈련 종료 후 자동으로 변경사항을 커밋하고 GitHub에 푸시합니다.

### Functions

#### `run_command`

명령어 실행

**Parameters**:

- `cmd`: list
- `cwd`: Path

#### `check_git_repo`

Git 저장소인지 확인

#### `check_remote`

원격 저장소 설정 확인

#### `setup_remote`

원격 저장소 설정

#### `get_changed_files`

변경된 파일 목록 가져오기

#### `create_commit_message`

커밋 메시지 생성

#### `commit_and_push`

변경사항 커밋 및 푸시

#### `main`

메인 함수

---

## Module: `tools.auto_documentation_generator`

자동 문서 생성 도구

클로드 코드와 함께 사용하기 위한 문서 자동 생성 스크립트

### Classes

#### `DocumentationGenerator`

문서 자동 생성기

**Methods**:

- `__init__(1 args)`
- `analyze_file(2 args)`: 파일 분석 및 문서 추출...
- `_extract_module_name(2 args)`: 모듈 이름 추출...
- `_is_method(3 args)`: 함수가 클래스 메서드인지 확인...
- `_extract_class_info(2 args)`: 클래스 정보 추출...
- `_extract_function_info(2 args)`: 함수 정보 추출...
- `generate_api_documentation(1 args)`: API 문서 생성...
- `generate_readme_update(1 args)`: README 업데이트 제안 생성...

### Functions

#### `find_all_python_files`

모든 Python 파일 찾기

#### `main`

메인 함수

---

## Module: `tools.auto_git_push`

### Functions

#### `run_git`

**Parameters**:

- `args`: list[str]

#### `has_changes`

#### `get_branch`

#### `push_with_upstream`

**Parameters**:

- `branch`: str

#### `push`

#### `get_changed_files_summary`

Get a summary of changed files for commit message.

#### `commit_all`

#### `log`

**Parameters**:

- `message`: str

#### `main`

---

## Module: `tools.background_parallel_learner`

Background Parallel Learning System

백그라운드에서 병렬로 리플레이 분석 및 신경망 학습을 수행하는 시스템.
메인 게임 실행을 방해하지 않고 별도 프로세스에서 학습을 진행합니다.

Features:
- Multiprocessing 기반 백그라운드 학습
- 리플레이 분석 병렬 처리
- 신경망 모델 백그라운드 학습
- 리소스 모니터링 및 자동 조절
- 학습 결과 자동 통합

### Classes

#### `LearningTask`

학습 작업 정의

#### `LearningResult`

학습 결과

#### `ResourceMonitor`

시스템 리소스 모니터링

**Methods**:

- `__init__(1 args)`
- `get_system_resources(1 args)`: 현재 시스템 리소스 상태 반환...
- `can_start_learning(3 args)`: 새로운 학습 프로세스를 시작할 수 있는지 확인...

#### `BackgroundParallelLearner`

백그라운드 병렬 학습 매니저

메인 게임 실행 중 백그라운드에서 리플레이 분석 및 모델 학습을 병렬로 수행합니다.

**Methods**:

- `__init__(6 args)`: Args:
    max_workers: 최대 병렬 워커 수
    replay_dir: 리플레이 디렉토리 경로
    model_path: 모델 파일 경로
    enable_r...
- `start(1 args)`: 백그라운드 학습 시작...
- `stop(1 args)`: 백그라운드 학습 중지...
- `_background_loop(1 args)`: 백그라운드 학습 메인 루프...
- `_cleanup_workers(1 args)`: 완료된 워커 프로세스 정리...
- `_start_next_task(1 args)`: 다음 학습 작업 시작...
- `_get_replay_files(1 args)`: 분석할 리플레이 파일 목록 반환...
- `_get_pending_training_data(1 args)`: 대기 중인 학습 데이터 반환...
- `_start_replay_analysis(2 args)`: 리플레이 분석 워커 시작...
- `_start_model_training(2 args)`: 모델 학습 워커 시작...
- `_collect_results(1 args)`: 워커 결과 수집...
- `_process_result(2 args)`: 학습 결과 처리...
- `_integrate_learned_params(2 args)`: 학습된 파라미터 통합...
- `get_stats(1 args)`: 학습 통계 반환...
- `submit_training_data(2 args)`: 게임에서 수집된 학습 데이터 제출...

### Functions

#### `analyze_replay_worker`

리플레이 분석 워커 함수 (별도 프로세스에서 실행)

Args:
    replay_path: 리플레이 파일 경로
    output_queue: 결과를 전달할 큐

Returns:
    분석 결과 딕셔너리

**Parameters**:

- `replay_path`: str
- `output_queue`: Queue

#### `train_model_worker`

모델 학습 워커 함수 (별도 프로세스에서 실행)

Args:
    model_path: 모델 파일 경로
    training_data: 학습 데이터
    output_queue: 결과를 전달할 큐

Returns:
    학습 결과 딕셔너리

**Parameters**:

- `model_path`: str
- `training_data`: Dict
- `output_queue`: Queue

#### `main`

테스트용 메인 함수

---

## Module: `tools.build_order_comparator`

Build Order Comparator - Compare training builds with pro gamer replays

This module compares the build order used during training with pro gamer replay data
and analyzes the differences to improve future performance.

### Classes

#### `BuildOrderComparison`

Result of comparing training build with pro gamer baseline

#### `BuildOrderAnalysis`

Complete analysis of build order comparison

#### `BuildOrderComparator`

Compare training build orders with pro gamer replay data

Features:
- Extract build order from current game
- Load pro gamer baseline from learned_build_orders.json
- Compare timings and identify gaps
- Generate recommendations for improvement
- Update learned parameters for next game

**Methods**:

- `__init__(2 args)`: Initialize BuildOrderComparator

Args:
    learned_data_path: Path to learned_build_orders.json (def...
- `_load_pro_baseline(1 args)`: Load pro gamer baseline from learned_build_orders.json...
- `compare(4 args)`: Compare training build order with pro gamer baseline

Args:
    training_build: Build order timing f...
- `_compare_parameter(5 args)`: Compare a single parameter...
- `_calculate_score(3 args)`: Calculate overall build order score (0.0 - 1.0)...
- `_save_comparison(2 args)`: Save comparison to history file...
- `update_learned_parameters(3 args)`: Update learned parameters based on comparison analysis

Args:
    analysis: BuildOrderAnalysis resul...
- `generate_report(2 args)`: Generate human-readable comparison report...

### Functions

#### `compare_with_pro_baseline`

Convenience function to compare training build with pro baseline

Args:
    training_build: Build order timing from current game
    game_result: "Victory" or "Defeat"
    game_id: Unique game identifier
    
Returns:
    BuildOrderAnalysis result

**Parameters**:

- `training_build`: Dict[str, Optional[float]]
- `game_result`: str
- `game_id`: Optional[str]

---

## Module: `tools.check_all_api_keys`

모든 API 키 상태 확인 스크립트

프로젝트에서 사용되는 모든 API 키의 현재 상태를 확인합니다.

### Functions

#### `check_key`

키 상태 확인

**Parameters**:

- `name`: str
- `value`: str
- `is_sensitive`: bool

#### `main`

---

## Module: `tools.check_all_sources`

ÀüÃ¼ ¼Ò½ºÄÚµå ÆÄÀÏ Á¡°Ë ½ºÅ©¸³Æ®

### Functions

#### `check_syntax`

Python ÆÄÀÏÀÇ syntax Ã¼Å©

**Parameters**:

- `filepath`: Path

#### `find_python_files`

¸ðµç Python ÆÄÀÏ Ã£±â

**Parameters**:

- `root`: Path

#### `check_imports`

ÆÄÀÏÀÇ import ¹® ºÐ¼®

**Parameters**:

- `filepath`: Path
- `root`: Path

#### `main`

---

## Module: `tools.check_api_key`

GEMINI_API_KEY 확인 스크립트

현재 설정된 GEMINI_API_KEY를 확인하고 형식을 검증합니다.

### Functions

#### `validate_gemini_api_key`

GEMINI_API_KEY 형식 검증

Returns:
    (is_valid, message)

**Parameters**:

- `api_key`: str

#### `check_key_from_file`

파일에서 키 확인

**Parameters**:

- `file_path`: Path

#### `main`

---

## Module: `tools.check_crash_log`

Check and clear crash_log.json in_progress entries

---

## Module: `tools.check_learning_progress`

Learning Progress and Build Order Sequence Verification Tool

### Functions

#### `load_json_safe`

Safely load JSON file

**Parameters**:

- `file_path`: Path

#### `check_strategy_db`

Check strategy_db.json

**Parameters**:

- `replay_dir`: Path

#### `check_learned_build_orders`

Check learned_build_orders.json

#### `check_learning_tracking`

Check learning tracking file

**Parameters**:

- `replay_dir`: Path

#### `main`

Main function

---

## Module: `tools.check_replay_paths`

¸®ÇÃ·¹ÀÌ °æ·Î È®ÀÎ ½ºÅ©¸³Æ®

### Functions

#### `main`

---

## Module: `tools.check_replay_selection`

### Functions

#### `load_pro_players`

#### `list_replays`

#### `is_pro_file`

**Parameters**:

- `p`: Path
- `pro_names`: set[str]

#### `select_files`

**Parameters**:

- `files`
- `pro_names`
- `pro_only`: bool
- `max_files`: int | None

#### `main`

---

## Module: `tools.check_training_status`

Check current training status and readiness

### Functions

#### `check_status`

Check training status

---

## Module: `tools.check_win_rate`

Check win rate from training statistics

### Functions

#### `analyze_win_rate`

Analyze win rate from training stats

---

## Module: `tools.claude_code_executor`

클로드 코드를 위한 자동 실행 및 테스트 도구

클로드 코드가 코드 변경 후 자동으로 테스트하고 검증할 수 있도록 도와주는 도구

### Classes

#### `ClaudeCodeExecutor`

클로드 코드 실행기

**Methods**:

- `__init__(1 args)`
- `run_tests(2 args)`: 테스트 실행...
- `_run_syntax_check(1 args)`: 문법 검사...
- `run_refactoring_analysis(1 args)`: 리팩토링 분석 실행...
- `run_documentation_generation(1 args)`: 문서 생성 실행...
- `validate_changes(2 args)`: 변경 사항 검증...
- `generate_execution_report(1 args)`: 실행 리포트 생성...

### Functions

#### `main`

메인 함수

---

## Module: `tools.claude_code_project_analyzer`

클로드 코드를 위한 프로젝트 전체 분석 도구

클로드 코드가 프로젝트를 이해하고 작업할 수 있도록 
프로젝트 구조, 의존성, 실행 방법 등을 종합적으로 분석합니다.

### Classes

#### `ClaudeCodeProjectAnalyzer`

클로드 코드를 위한 프로젝트 분석기

**Methods**:

- `__init__(1 args)`
- `analyze_project_structure(1 args)`: 프로젝트 구조 분석...
- `analyze_dependencies(1 args)`: 의존성 분석...
- `find_entry_points(1 args)`: 진입점 찾기...
- `_extract_batch_description(2 args)`: 배치 파일에서 설명 추출...
- `_extract_file_description(2 args)`: 파일에서 설명 추출...
- `analyze_test_coverage(1 args)`: 테스트 커버리지 분석...
- `generate_claude_code_instructions(1 args)`: 클로드 코드를 위한 지시사항 생성...
- `_get_directory_description(2 args)`: 디렉토리 설명...

### Functions

#### `main`

메인 함수

---

## Module: `tools.clean_duplicates`

Clean Duplicates - Maintenance Script for Project Cleanup

This script removes duplicate files, cleans up temporary files,
and organizes the project structure for better maintainability.

Usage:
    python tools/clean_duplicates.py [--dry-run] [--verbose]

### Functions

#### `calculate_file_hash`

Calculate MD5 hash of a file.

**Parameters**:

- `file_path`: Path
- `chunk_size`: int

#### `find_duplicate_files`

Find duplicate files by content hash.

**Parameters**:

- `directory`: Path
- `verbose`: bool

#### `remove_duplicates`

Remove duplicate files, keeping the first one.

**Parameters**:

- `duplicates`: Dict[str, List[Path]]
- `dry_run`: bool
- `verbose`: bool

#### `clean_temp_files`

Clean temporary files (.tmp, .bak, .log, etc.).

**Parameters**:

- `directory`: Path
- `dry_run`: bool

#### `main`

---

## Module: `tools.cleanup_artifacts`

### Functions

#### `_iter_matches`

**Parameters**:

- `patterns`
- `base`: Path

#### `move_telemetry_to_data`

**Parameters**:

- `dry_run`: bool

#### `move_training_stats_to_data`

**Parameters**:

- `dry_run`: bool

#### `prune_logs`

**Parameters**:

- `keep`: int
- `dry_run`: bool

#### `prune_reports`

**Parameters**:

- `keep`: int
- `dry_run`: bool

#### `cleanup_aiarena_submission_path`

**Parameters**:

- `dry_run`: bool

#### `remove_ai_arena_deploy`

**Parameters**:

- `dry_run`: bool

#### `prune_pycache_and_cursor`

**Parameters**:

- `dry_run`: bool

#### `remove_model_backups`

**Parameters**:

- `dry_run`: bool

#### `main`

---

## Module: `tools.cleanup_deploy`

### Functions

#### `remove_dir`

**Parameters**:

- `path`: Path

#### `main`

---

## Module: `tools.code_diet_analyzer`

Code Diet Analyzer - Find unused imports and dead code
肄붾뱶 ?떎?씠?뼱?듃 遺꾩꽍湲? - ?궗?슜?릺吏? ?븡?뒗 import??? ?뜲?뱶 肄붾뱶 李얘린

### Classes

#### `CodeDietAnalyzer`

Analyze code for unused imports and dead code

**Methods**:

- `__init__(2 args)`
- `analyze_file(2 args)`: Analyze a single Python file...
- `find_unused_imports(1 args)`: Find unused imports...
- `analyze_project(1 args)`: Analyze entire project...
- `generate_report(1 args)`: Generate analysis report...

### Functions

#### `main`

Main function

---

## Module: `tools.code_quality_improver`

코드 품질 개선 자동화 도구

1. 중복 코드 제거
2. 사용하지 않는 import 정리
3. 코드 스타일 통일
4. 타입 힌트 추가

### Classes

#### `CodeQualityImprover`

코드 품질 개선기

**Methods**:

- `__init__(1 args)`
- `remove_unused_imports(2 args)`: 사용하지 않는 import 제거...
- `check_code_style(2 args)`: 코드 스타일 검사...
- `fix_code_style(2 args)`: 코드 스타일 자동 수정...
- `find_duplicate_functions(2 args)`: 중복 함수 찾기 (간단한 버전)...

### Functions

#### `find_all_python_files`

모든 Python 파일 찾기

#### `main`

메인 함수

---

## Module: `tools.compare_archive_paths`

Compare two archive directories to understand their differences

### Functions

#### `main`

---

## Module: `tools.compare_pro_vs_training_replays`

Compare Pro Gamer Replays vs Training Replays

프로게이머 리플레이 학습데이터와 훈련한 리플레이 학습데이터를 비교 분석하는 스크립트입니다.
- 프로게이머 리플레이 데이터 로드 (D:eplayseplays)
- 훈련 리플레이 데이터 로드 (training_stats.json, build_order_comparison_history.json)
- 두 데이터 소스 비교 분석
- 상세 리포트 생성

### Classes

#### `ProVsTrainingComparator`

프로게이머 리플레이 vs 훈련 리플레이 비교 분석 클래스

**Methods**:

- `__init__(3 args)`: Initialize ProVsTrainingComparator

Args:
    pro_replay_dir: Directory containing pro gamer replays...
- `load_pro_replay_data(1 args)`: Load pro gamer replay data...
- `load_training_data(1 args)`: Load training replay data...
- `compare_timings(3 args)`: Compare build order timings between pro and training...
- `analyze_performance(3 args)`: Analyze overall performance comparison...
- `generate_comparison_report(5 args)`: Generate detailed comparison report...
- `save_comparison_data(6 args)`: Save comparison data and report...

### Functions

#### `main`

Main function

---

## Module: `tools.comprehensive_code_improvement`

종합 코드 품질 개선 도구

다음 작업들을 수행:
1. 중복 코드 제거
2. 사용하지 않는 import 정리
3. 코드 스타일 통일
4. 파일 구조 재구성 제안
5. 클래스 분리 및 통합 제안
6. 의존성 최적화

### Classes

#### `ComprehensiveCodeImprover`

종합 코드 개선기

**Methods**:

- `__init__(1 args)`
- `find_unused_imports(1 args)`: 사용하지 않는 import 찾기...
- `find_duplicate_code_blocks(2 args)`: 중복 코드 블록 찾기...
- `check_code_style(1 args)`: 코드 스타일 검사...
- `analyze_class_structure(1 args)`: 클래스 구조 분석 및 리팩토링 제안...
- `analyze_dependencies(1 args)`: 의존성 분석 및 최적화 제안...
- `generate_improvement_report(1 args)`: 개선 리포트 생성...

### Functions

#### `main`

메인 함수

---

## Module: `tools.convert_to_euc_kr`

전체 파일을 EUC-KR 인코딩으로 변환하는 스크립트

?? 주의사항:
1. Python 소스 코드는 일반적으로 UTF-8을 사용합니다
2. EUC-KR로 변환하면 일부 특수문자나 영어가 깨질 수 있습니다
3. 변환 전에 백업을 권장합니다
4. 이미 UTF-8로 잘 작동하는 파일은 변환하지 않는 것이 좋습니다

### Functions

#### `detect_encoding`

파일의 인코딩을 감지

**Parameters**:

- `file_path`: Path

#### `should_convert_file`

파일을 변환해야 하는지 확인

**Parameters**:

- `file_path`: Path

#### `convert_file_to_euc_kr`

파일을 EUC-KR로 변환

**Parameters**:

- `file_path`: Path

#### `find_all_files`

변환할 모든 파일 찾기

**Parameters**:

- `root_dir`: Path

#### `main`

메인 함수

---

## Module: `tools.download_and_train`

Automated replay downloader and trainer.

Downloads pro Zerg replays from Sc2ReplayStats API, validates each file,
and runs supervised learning training on the collected replays.

Features:
- Fetches replays from online Sc2ReplayStats API (Zerg-focused)
- Validates downloadable files via HEAD request
- Skips already-downloaded files
- Updates manifest with new replays
- Runs training after download completion

Usage:
    python download_and_train.py --max-download 50 --epochs 2
    python download_and_train.py --local-only --epochs 1  # Skip online, train local only

### Classes

#### `LinkExtractor`

**Bases**: HTMLParser

**Methods**:

- `__init__(1 args)`
- `handle_starttag(3 args)`

#### `ReplayDownloader`

Download and validate pro Zerg replays from online sources

**Methods**:

- `__init__(7 args)`
- `_scan_existing_hashes(1 args)`: Scan existing replay files and return set of hashes for duplicate detection...
- `_get_file_hash(2 args)`: Calculate MD5 hash of file for duplicate detection...
- `_is_duplicate(2 args)`: Check if file is duplicate by hash...
- `_organize_replay_file(3 args)`: Organize replay file into structured folders (by race, map, player)

Returns:
    Final path where f...
- `_match_pro_name(2 args)`
- `_is_pro_tournament(2 args)`: Check if replay is from major tournament or pro player...
- `_google_search_fallback(2 args)`: Fallback: Search Google for replay pack links when site is blocked

Args:
    search_terms: List of ...
- `_http_head(2 args)`
- `_http_get(2 args)`
- `_extract_archive(2 args)`: Extract archive file (ZIP, RAR, 7Z) and return count of extracted replays

IMPROVED: Validates each ...
- `download_and_extract_from_url(2 args)`: IMPROVED: Download from URL with enhanced validation and duplicate detection...
- `_is_downloadable(2 args)`
- `_normalize_filename(2 args)`
- `_fetch_page_links(2 args)`
- `_liquipedia_search_pages(1 args)`
- `_liquipedia_page_links(2 args)`
- `fetch_replay_pack_links(2 args)`
- `_is_zerg_involved(2 args)`: Check if replay involves Zerg player (ZvT, ZvP, ZvZ)
IMPROVED: Strict Zerg matchup filtering...
- `_validate_replay_metadata(2 args)`: Validate replay using sc2reader metadata with advanced quality filtering

Requirements:
- sc2reader ...
- `_is_downloadable(2 args)`: Validate if URL is downloadable via HEAD request...
- `fetch_replays_from_api(3 args)`: Fetch pro Zerg replays from Sc2ReplayStats API

IMPROVED: Filters for Zerg matchups only, prioritize...
- `download_replay(2 args)`: Download and validate a single replay

IMPROVED: Enhanced validation and duplicate detection...
- `scan_local_replays(1 args)`: Scan local replay directory for new files with enhanced validation

IMPROVED: Validates game time (5...
- `run_download(2 args)`: Execute full download + local scan workflow...

#### `ManifestBuilder`

Build manifest from collected replays

**Methods**:

- `__init__(2 args)`
- `build_manifest(3 args)`: Build manifest JSON from replay list...

### Functions

#### `get_venv_dir`

Get virtual environment directory from environment variable or use project default

#### `get_replay_dir`

Get replay directory - default to D:eplays

#### `main`

---

## Module: `tools.extract_and_train_from_training`

Extract and Train from Training Data

게임 훈련 종료 후 데이터를 추출하고 학습하는 스크립트입니다.
- training_stats.json에서 게임 결과 추출
- build_order_comparison_history.json에서 빌드 오더 추출
- 추출된 데이터를 기반으로 학습 파라미터 업데이트

### Classes

#### `TrainingDataExtractor`

훈련 데이터 추출 및 학습 클래스

**Methods**:

- `__init__(2 args)`: Initialize TrainingDataExtractor

Args:
    base_dir: Base directory for training data (default: aut...
- `extract_training_stats(1 args)`: Extract training statistics from training_stats.json...
- `extract_build_order_comparisons(1 args)`: Extract build order comparisons from comparison history...
- `extract_session_stats(1 args)`: Extract session statistics...
- `analyze_training_data(2 args)`: Analyze extracted training data...
- `extract_build_order_timings(2 args)`: Extract build order timings from comparisons...
- `learn_from_training_data(4 args)`: Learn optimal parameters from training data

Args:
    training_data: Extracted training statistics
...
- `save_extracted_data(5 args)`: Save extracted data to output directory...
- `generate_report(3 args)`: Generate human-readable report...

### Functions

#### `main`

Main function

---

## Module: `tools.fix_all_encoding_issues`

Fix encoding issues in all Python files
모든 Python 파일의 인코딩 문제를 수정하는 스크립트

### Functions

#### `detect_encoding`

Detect file encoding

**Parameters**:

- `file_path`

#### `fix_file_encoding`

Fix encoding of a single file

**Parameters**:

- `file_path`

#### `main`

Main function

---

## Module: `tools.generate_pwa_icons`

Generate PWA icons for Mobile GCS
Creates icon-192.png and icon-512.png

### Functions

#### `create_icon`

Create a PWA icon with SC2 Zerg theme

**Parameters**:

- `size`: int
- `output_path`: str

#### `main`

Generate PWA icons

---

## Module: `tools.generate_readme`

Generate README files (Korean / English) for:
🛸 Swarm Control System in StarCraft II

### Functions

#### `write_file`

파일 쓰기

**Parameters**:

- `path`: Path
- `content`: str

#### `main`

---

## Module: `tools.integrated_pipeline`

### Functions

#### `get_replay_dir`

Get replay directory - default to D:eplays

#### `main`

---

## Module: `tools.large_scale_refactoring`

대규모 리팩토링 계획 및 실행 도구

1. 파일 구조 재구성 계획
2. 클래스 분리 및 통합 계획
3. 의존성 최적화 계획

### Classes

#### `LargeScaleRefactoringPlanner`

대규모 리팩토링 계획자

**Methods**:

- `__init__(1 args)`
- `analyze_classes(1 args)`: 클래스 분석...
- `analyze_dependencies(1 args)`: 의존성 분석...
- `generate_refactoring_plan(1 args)`: 리팩토링 계획 생성...

### Functions

#### `main`

메인 함수

---

## Module: `tools.load_api_key`

API Key 로더 유틸리티

secrets/ 또는 api_keys/ 폴더에서 API 키를 안전하게 로드하는 헬퍼 함수
보안 모범 사례: 파일에서 직접 읽어오기

### Functions

#### `get_project_root`

프로젝트 루트 경로 반환

#### `get_secrets_dir`

secrets 폴더 경로 반환 (권장)

#### `get_api_keys_dir`

api_keys 폴더 경로 반환 (하위 호환성)

#### `load_key_from_file`

파일에서 키를 읽어옵니다 (보안 모범 사례)

Args:
    file_path: 키 파일 경로

Returns:
    키 문자열 (없으면 빈 문자열)

**Parameters**:

- `file_path`: Path

#### `load_api_key`

API 키를 로드합니다 (보안 모범 사례)

우선순위:
1. secrets/ 폴더 (권장)
2. api_keys/ 폴더 (하위 호환성)
3. .env 파일
4. 환경 변수

Args:
    key_name: API 키 이름 (예: "GEMINI_API_KEY")
    fallback_env: 환경 변수 이름 (None이면 key_name 사용)

Returns:
    API 키 문자열 (없으면 빈 문자열)

Examples:
    >>> key = load_api_key("GEMINI_API_KEY")
    >>> key = load_api_key("GOOGLE_API_KEY", fallback_env="GOOGLE_API_KEY")

**Parameters**:

- `key_name`: str
- `fallback_env`: Optional[str]

#### `set_api_key_to_env`

API 키를 환경 변수로 설정합니다.

Args:
    key_name: API 키 이름
    fallback_env: 환경 변수 이름 (None이면 key_name 사용)

Returns:
    성공 여부

**Parameters**:

- `key_name`: str
- `fallback_env`: Optional[str]

#### `get_gemini_api_key`

Gemini API 키 반환

#### `get_google_api_key`

Google API 키 반환

#### `get_gcp_project_id`

GCP 프로젝트 ID 반환

---

## Module: `tools.merge_training_stats`

Merge per-instance training statistics into a single summary.

Usage:
    python tools/merge_training_stats.py --stats-dir stats --output-prefix stats/training_stats_merged

Outputs:
    - <output-prefix>.json: aggregated summary + per-instance breakdown
    - <output-prefix>.csv : tabular per-instance breakdown for quick plotting

### Classes

#### `InstanceStats`

**Bases**: TypedDict

#### `Summary`

**Bases**: TypedDict

#### `MergedStats`

**Bases**: TypedDict

### Functions

#### `_load_instance_stats`

**Parameters**:

- `path`: Path

#### `_weighted_average`

**Parameters**:

- `durations`: Sequence[float]
- `weights`: Sequence[int]

#### `merge_stats`

**Parameters**:

- `stats_dir`: Path

#### `write_outputs`

**Parameters**:

- `merged`: MergedStats
- `output_prefix`: Path

#### `main`

---

## Module: `tools.optimize_and_sort_learning_data`

Optimize and sort learning data
- Sorts strategy_db.json by matchup and extraction time
- Optimizes learned_build_orders.json
- Creates summary report

### Functions

#### `load_json_safe`

Safely load JSON file

**Parameters**:

- `file_path`: Path

#### `save_json_safe`

Safely save JSON file with backup

**Parameters**:

- `file_path`: Path
- `data`: Dict
- `indent`: int

#### `optimize_strategy_db`

Optimize and sort strategy_db.json

**Parameters**:

- `strategy_db_path`: Path

#### `optimize_learned_build_orders`

Optimize learned_build_orders.json

**Parameters**:

- `learned_orders_path`: Path

#### `create_summary_report`

Create summary report of learning data

**Parameters**:

- `strategy_db_path`: Path
- `learned_orders_path`: Path
- `output_path`: Path

#### `main`

Main optimization function

#### `sort_key`

**Parameters**:

- `item`

#### `sort_build_order`

**Parameters**:

- `bo`

---

## Module: `tools.package_for_aiarena`

================================================================================

                AI Arena Á¦Ãâ¿ë ÆÐÅ°Â¡ ÀÚµ¿È­ (package_for_aiarena.py)

================================================================================



·ÎÄÃ¿¡¼­ ÈÆ·ÃµÈ ¸ðµ¨°ú ¼Ò½ºÄÚµå¸¦ AI Arena Á¦Ãâ¿ë ÆÐÅ°Áö·Î ÀÚµ¿ »ý¼ºÇÕ´Ï´Ù.



±â´É:

    1. ÈÆ·ÃµÈ ¸ðµ¨ °¡ÁßÄ¡(.pt) Æ÷ÇÔ

    2. ÇÊ¼ö ¼Ò½ºÄÚµå ÀÚµ¿ ¼öÁý

    3. arena_deploy/ Æú´õ·Î ÀÚµ¿ º¹»ç

    4. Ã¼Å©¼¶ °ËÁõ (¸ðµ¨ ¼Õ»ó ¹æÁö)



»ç¿ë¹ý:

    python package_for_aiarena.py



Ãâ·Â:

    - arena_deploy/bot_package/ (Á¦Ãâ¿ë ¿ÏÀü ÆÐÅ°Áö)

    - arena_deploy/verification_report.txt (°ËÁõ º¸°í¼­)



================================================================================

### Classes

#### `PackageBuilder`

AI Arena Á¦Ãâ¿ë ÆÐÅ°Áö ºô´õ

**Methods**:

- `__init__(2 args)`: Args:

    project_root: ÇÁ·ÎÁ§Æ® ·çÆ® °æ·Î (±âº»°ª: ÇöÀç ÆÄÀÏ µð·ºÅä¸®)...
- `log(3 args)`: ·Î±× ¸Þ½ÃÁö Ãâ·Â ¹× ÀúÀå...
- `verify_file_exists(2 args)`: ÆÄÀÏ Á¸Àç ¿©ºÎ È®ÀÎ...
- `calculate_checksum(2 args)`: ÆÄÀÏ Ã¼Å©¼¶ °è»ê (¹«°á¼º °ËÁõ)...
- `copy_sources(1 args)`: ÇÊ¼ö ¼Ò½ºÄÚµå ÆÄÀÏ º¹»ç...
- `copy_models(1 args)`: ÈÆ·ÃµÈ ¸ðµ¨ °¡ÁßÄ¡ º¹»ç (°¡Àå Áß¿ä!)...
- `copy_data(1 args)`: µ¥ÀÌÅÍ ÆÄÀÏ º¹»ç (Ä¿¸®Å§·³ Åë°è µî)...
- `create_manifest(1 args)`: ÆÐÅ°Áö ¸Å´ÏÆä½ºÆ® ÆÄÀÏ »ý¼º (°ËÁõ¿ë)...
- `create_readme(1 args)`: AI Arena Á¦Ãâ¿ë README »ý¼º...
- `backup_previous_package(1 args)`: ÀÌÀü ÆÐÅ°Áö ¹é¾÷...
- `build(1 args)`: ÀüÃ¼ ÆÐÅ°Â¡ ÇÁ·Î¼¼½º ½ÇÇà...
- `save_report(1 args)`: °ËÁõ º¸°í¼­ ÀúÀå...

### Functions

#### `main`

¸ÞÀÎ ÁøÀÔÁ¡

---

## Module: `tools.package_for_aiarena_clean`

AI Arena Packaging Script for Wicked Zerg Bot
Includes model files and creates clean deployment package

### Classes

#### `AIArenaPackager`

AI Arena deployment packaging system

**Methods**:

- `__init__(4 args)`
- `validate_project(1 args)`: Validate project files...
- `find_latest_model(1 args)`: Find latest model file...
- `create_package_structure(1 args)`: Create package structure - Flat layout for AI Arena...
- `_create_metadata(1 args)`: Create package metadata...
- `create_zip(1 args)`: Create ZIP file with filtering...
- `cleanup(1 args)`: Clean up temporary files...
- `_verify_package(2 args)`: Verify ZIP package contents...
- `package(1 args)`: Complete packaging process...

### Functions

#### `main`

Main execution function

#### `should_exclude`

Check if file should be excluded

**Parameters**:

- `file_path`: Path

---

## Module: `tools.package_for_aiarena_clean_fixed`

AI Arena Packaging Script for Wicked Zerg Bot
Includes model files and creates clean deployment package

### Classes

#### `AIArenaPackager`

AI Arena deployment packaging system

**Methods**:

- `__init__(4 args)`
- `validate_project(1 args)`: Validate project files...
- `find_latest_model(1 args)`: Find latest model file...
- `create_package_structure(1 args)`: Create package structure - Flat layout for AI Arena...
- `_create_metadata(1 args)`: Create package metadata...
- `create_zip(1 args)`: Create ZIP file with filtering...
- `cleanup(1 args)`: Clean up temporary files...
- `_verify_package(2 args)`: Verify ZIP package contents...
- `package(1 args)`: Complete packaging process...

### Functions

#### `main`

Main execution function

#### `should_exclude`

Check if file should be excluded

**Parameters**:

- `file_path`: Path

---

## Module: `tools.pre_training_check`

Pre-training system check script

°ÔÀÓ ½ÇÇà Àü ½Ã½ºÅÛ »óÅÂ È®ÀÎ

### Functions

#### `check_sc2_installation`

Check StarCraft II installation

#### `check_python_packages`

Check required Python packages

#### `check_sc2_process`

Check if SC2 process is running

#### `check_gpu`

Check GPU availability

#### `main`

---

## Module: `tools.prune_updates`

### Functions

#### `list_update_dirs`

#### `prune`

**Parameters**:

- `keep`: int
- `dry_run`: bool

#### `main`

---

## Module: `tools.refactoring_analyzer`

대규모 리팩토링 및 코드 품질 개선 분석 도구

클로드 코드와 함께 사용하기 위한 분석 스크립트

### Classes

#### `RefactoringAnalyzer`

리팩토링 분석기

**Methods**:

- `__init__(1 args)`
- `analyze_file(2 args)`: 파일 분석...
- `_analyze_function(3 args)`: 함수 분석...
- `_analyze_class(3 args)`: 클래스 분석...
- `_analyze_import(2 args)`: Import 분석...
- `find_duplicate_functions(2 args)`: 중복 함수 찾기...
- `find_long_functions(3 args)`: 긴 함수 찾기...
- `find_complex_functions(3 args)`: 복잡한 함수 찾기...
- `find_large_classes(3 args)`: 큰 클래스 찾기...
- `find_duplicate_code_blocks(3 args)`: 중복 코드 블록 찾기 (간단한 버전)...

### Functions

#### `find_all_python_files`

모든 Python 파일 찾기

#### `generate_refactoring_report`

리팩토링 리포트 생성

---

## Module: `tools.remove_cleanup_targets`

Remove cleanup target files

---

## Module: `tools.remove_old_api_keys`

기존 API 키 제거 스크립트
프로젝트에서 하드코딩된 API 키를 찾아서 제거합니다.

### Functions

#### `should_exclude`

파일/디렉토리를 제외해야 하는지 확인

**Parameters**:

- `path`: Path

#### `find_hardcoded_keys`

하드코딩된 키를 찾습니다

**Parameters**:

- `root_dir`: Path

#### `remove_keys_from_file`

파일에서 키를 제거합니다 (예제 키만 마스킹)

**Parameters**:

- `file_path`: Path
- `old_keys`: List[str]

#### `main`

메인 함수

---

## Module: `tools.remove_unused_imports`

사용하지 않는 import 자동 제거 도구

주의: 자동 제거는 위험할 수 있으므로 백업 후 사용하세요.

### Functions

#### `find_unused_imports_in_file`

파일에서 사용하지 않는 import 찾기

**Parameters**:

- `file_path`: Path

#### `remove_unused_imports`

사용하지 않는 import 제거

**Parameters**:

- `file_path`: Path
- `unused_imports`: List
- `dry_run`: bool

#### `main`

메인 함수

---

## Module: `tools.replay_lifecycle_manager`

Zerg Data Pipeline - Step 2: Replay Lifecycle Manager

Purpose: ZIP files -> Zerg filtering -> Training folder batch -> Auto cleanup

Pipeline:
  DOWNLOAD (ZIP)
    |
  EXTRACT & FILTER (Zerg only)
    |
  TRAINING SOURCE
    |
  TRAIN (Learning)
    |
  CLEANUP & ARCHIVE (Organize)

Path Configuration:
  1. DOWNLOAD_DIR: ZIP file location (usually C:\Users\[USER]\Downloads)
  2. TRAINING_SOURCE_DIR: D:\replay_folder\replays (training input)
  3. BOT_OUTPUT_DIR: auto-detected from local_training\replays (training output)

Usage:
  python replay_lifecycle_manager.py --extract    # Extract Zerg replays from ZIP
  python replay_lifecycle_manager.py --cleanup    # Cleanup after training
  python replay_lifecycle_manager.py --full       # Full cycle

### Classes

#### `ReplayLifecycleManager`

Replay lifecycle management

**Methods**:

- `__init__(1 args)`
- `extract_and_filter_zips(2 args)`: ?¢¯??  ZIP  ??  ?¡¤?¢¬ 

Returns:
    (_?¡¤_, ??__?¡¤_)...
- `cleanup_after_training(2 args)`: ¨¡¡¤  ?¡¤ :
1.   ?¡¤  BOT_OUTPUT_DIR ??
2.   ?¡¤  archive ??...
- `validate_replays(1 args)`: ?¡¤  (sc2reader ,  ?¨¬???)...
- `generate_report(2 args)`

### Functions

#### `_find_training_folder`

Auto-detect training folder (local_training or legacy)

#### `main`

---

## Module: `tools.runtime_check`

tools/runtime_check.py
Comprehensive runtime & static-check tool for Wicked Zerg Challenger
- Environment checks (Python, optional packages, nvidia-smi, SC2PATH)
- Static syntax scan across .py files using ast.parse
- Optional dry-run import checks (spawns subprocess to import modules)
- Writes a timestamped log to logs/runtime_check_<timestamp>.log

Usage:
    python tools/runtime_check.py [--no-import] [--modules wicked_zerg_bot_pro,main_integrated]

### Functions

#### `setup_logger`

#### `find_py_files`

**Parameters**:

- `root`: str

#### `check_syntax`

**Parameters**:

- `file_path`: str

#### `run_env_checks`

**Parameters**:

- `logger`: logging.Logger

#### `run_syntax_scan`

**Parameters**:

- `root`: str
- `logger`: logging.Logger

#### `import_check`

Attempt to import a module in a subprocess to detect import-time errors without running in-process.

**Parameters**:

- `module_name`: str
- `timeout`: int

#### `run_dry_imports`

**Parameters**:

- `modules`: List[str]
- `logger`: logging.Logger

#### `parse_args`

#### `main`

---

## Module: `tools.self_diagnosis`

Self-Diagnosis Script for Replay Learning System

### Functions

#### `main`

---

## Module: `tools.setup_verify`

Zerg Data Pipeline - Environment Check

### Functions

#### `main`

---

## Module: `tools.summarize_training_stats`

Summarize training_stats.json
Print: total games, wins, losses, win rate, games per instance, top loss reasons, avg game time.

---

## Module: `tools.training_session_manager`

Training Session Manager - Enhanced training process management

This module provides comprehensive tracking, statistics, and adaptive improvements
for the continuous training loop.

Features:
1. Game statistics tracking (win rate, average time, etc.)
2. Learning data validation and backup
3. Adaptive difficulty adjustment
4. Error recovery and resilience
5. Performance monitoring
6. Learning data quality control

### Classes

#### `GameResult`

Single game result data

#### `TrainingSessionStats`

Overall training session statistics

#### `TrainingSessionManager`

Enhanced training session manager with comprehensive tracking and adaptive improvements

**Methods**:

- `__init__(2 args)`: Initialize TrainingSessionManager

Args:
    stats_file: Path to save training statistics (default: ...
- `_load_stats(1 args)`: Load existing training statistics...
- `_save_stats(1 args)`: Save current training statistics...
- `record_game_result(10 args)`: Record a game result and update statistics

Args:
    game_id: Game number
    map_name: Map name
  ...
- `_print_game_summary(2 args)`: Print game result summary...
- `get_adaptive_difficulty(1 args)`: Get adaptive difficulty based on recent performance

Returns:
    Difficulty level ("Hard" or "VeryH...
- `backup_learning_data(2 args)`: Backup learning data before update

Args:
    learned_data_path: Path to learned_build_orders.json
 ...
- `validate_learning_data(2 args)`: Validate learning data before use

Args:
    learned_data_path: Path to learned_build_orders.json
  ...
- `record_error(3 args)`: Record an error for recovery analysis

Args:
    error_type: Type of error (e.g., "AssertionError", ...
- `reset_error_count(1 args)`: Reset consecutive error count after successful game...
- `get_training_summary(1 args)`: Get comprehensive training summary

Returns:
    Formatted training summary string...

---

## Module: `tools.upload_report`

### Functions

#### `timestamped_name`

**Parameters**:

- `base`: Path

#### `upload_report`

**Parameters**:

- `src_path`: str
- `dst_dir`: str
- `add_header`: bool

#### `main`

---

## Module: `tools.upload_to_aiarena`

AI Arena Auto-Uploader
=======================
Automatically upload bot to AI Arena using their API

### Classes

#### `AIArenaUploader`

Upload bot to AI Arena

**Methods**:

- `__init__(1 args)`
- `check_token(1 args)`: Check if API token is set...
- `get_headers(1 args)`: Get API headers...
- `list_bots(1 args)`: List user's bots...
- `find_bot_by_name(2 args)`: Find bot by name...
- `create_bot(1 args)`: Create new bot...
- `upload_bot_zip(3 args)`: Upload bot ZIP file...
- `upload(2 args)`: Complete upload process...

### Functions

#### `main`

Main entry point

---

## Module: `tools.validate_arena_deployment`

AI Arena Deployment Validation Script

This script simulates the AI Arena validation process to ensure the bot
can start correctly on the server before actual submission.

Usage:
    python tools/validate_arena_deployment.py

### Functions

#### `check_imports`

Check if all required modules can be imported

#### `check_run_py`

Check if run.py can be executed

#### `check_bot_instantiation`

Check if bot can be instantiated

#### `check_paths`

Check if all paths are relative

#### `check_requirements`

Check if requirements.txt exists and has essential packages

#### `check_file_structure`

Check if essential files exist

#### `simulate_arena_start`

Simulate AI Arena server startup

#### `main`

Run all validation checks

---

## Module: `unit_factory`

================================================================================
                    🎖️ Unit Production Management (production_manager.py)
================================================================================
Core loop for producing combat units and managing supply.

Core Features:
    1. Predictive Overlord production (prevent supply block)
    2. Drone production (economy)
    3. Queen production (for larvae injection)
    4. Tech-based military unit production (Zergling → Roach → Hydralisk)
    5. Counter-based unit selection (Counter-Build)
================================================================================

### Classes

#### `UnitFactory`

Unit Production Specialist

**Methods**:

- `__init__(2 args)`

---

## Module: `wicked_zerg_bot_pro`

### Classes

#### `WickedZergBotPro`

**Bases**: BotAI

**Methods**:

- `__init__(6 args)`: Bot initialization

Args:
    train_mode: Enable training mode
    instance_id: Instance ID (0=main ...
- `_setup_race_specific_strategy(1 args)`: 상대 종족에 따른 맞춤 전략 설정

저그 랭킹 1~5위 선수들은 상대 종족에 따라 완전히 다른 빌드를 선택합니다....
- `_check_rush_failure_and_transition(1 args)`: 초반 러쉬 실패 감지 및 중반 강력 빌드 전환 로직

러쉬가 실패했다고 판단되면 중반 강력 빌드로 전환하여 공격을 가합니다.

StrategyHub로 위임...
- `_decide_strategy(1 args)`: Strategy decision - delegated to StrategyHub...
- `get_current_build_phase(1 args)`: 현재 빌드 단계 반환

Returns:
    str: 현재 빌드 단계 설명...
- `get_memory_usage_level(1 args)`: 메모리 사용 수준 반환 (간단한 추정)

Returns:
    str: 메모리 상태 ("OK", "WARNING", "CRITICAL")...
- `write_log(4 args)`
- `write_log_with_traceback(4 args)`: Write log message with full traceback

Args:
    message: Log message
    exception: Exception objec...
- `_print_status(1 args)`
- `save_model_safe(1 args)`: 저장 경로를 확인하고 모델 파일을 물리적으로 저장합니다.
인스턴스별 별도 파일로 저장하여 병렬 실행 시 충돌을 방지합니다....
- `_collect_state(1 args)`: 현재 게임 상태 수집 (신경망 입력용)

IMPROVED: Enhanced state vector with enemy intelligence
- Added enemy unit co...
- `choose_action(2 args)`: 에필론-그리디 전략에 따른 행동 선택

Args:
    state: 게임 상태 (numpy array 또는 list). None이면 자동으로 수집

Returns:
    Act...
- `_calculate_build_order_reward(1 args)`: 빌드 오더 타이밍 보상 계산 (완화된 버전)

Serral 빌드 오더의 정확한 타이밍에 따라 보상을 부여합니다.
신경망이 "16일 때 앞마당을 펴는 게 승률이 높구나!"를 학습하도...
- `_log_training_stats(2 args)`: Record win rate and cumulative training count to log.txt

Args:
    game_result: Game result (Victor...
- `_display_matchup_statistics(2 args)`: Display win/loss statistics and race matchup records at game end

Args:
    game_result: Current gam...
- `_write_status_file_sync(4 args)`: Synchronous file write helper for use with asyncio executor
This prevents blocking the game loop dur...

#### `BuffId`

#### `DebugVisualizer`

**Methods**:

- `__init__(1 args)`
- `update_dashboard(1 args)`
- `record_event(1 args)`
- `generate_debug_chart(1 args)`
- `get_event_summary(1 args)`
- `close(1 args)`

#### `DummyVisualizer`

**Methods**:

- `update_dashboard(2 args)`
- `close(1 args)`
- `record_event(1 args)`

#### `DummyGasManager`

#### `DummyDefenseManager`

**Methods**:

- `is_panic_mode(1 args)`

#### `DummyDefenseManager`

**Methods**:

- `is_panic_mode(1 args)`

#### `DummyIntel`

**Methods**:

- `update(1 args)`
- `should_attack(1 args)`
- `should_defend(1 args)`

#### `DummyEconomy`

#### `DummyProduction`

#### `DummyCombat`

**Methods**:

- `initialize(1 args)`

#### `DummyScout`

**Methods**:

- `initialize(1 args)`

#### `DummyMicro`

**Methods**:

- `execute_spread_attack(1 args)`
- `execute_stutter_step(1 args)`
- `execute_defensive_spread(1 args)`

#### `DummyQueen`

#### `DummyMicroController`

#### `Enemy`

#### `Combat`

#### `Economy`

#### `Production`

### Functions

#### `_retry`

**Parameters**:

- `func`
- `description`: str
- `retries`: int
- `delay`: float

#### `_is_empty`

**Parameters**:

- `collection`

#### `get_total_health`

**Parameters**:

- `enemy`

#### `_save_curriculum`

---

## Module: `zerg_net`

### Classes

#### `Action`

Action type

**Bases**: Enum

#### `ZergNet`

Simple neural network model

IMPROVED: Enhanced input with comprehensive enemy intelligence
Input: [Self(5), Enemy(10)] (15-dimensional):
    Self (5): Minerals, Gas, Supply Used, Drone Count, Army Count
    Enemy (10):
        - Enemy Army Count
        - Enemy Tech Level (0-2)
        - Enemy Threat Level (0-4)
        - Enemy Unit Diversity (0-1)
        - Scout Coverage (0-1)
        - Enemy Main Distance (0-1, normalized)
        - Enemy Expansion Count (0-1, normalized)
        - Enemy Resource Estimate (0-1, normalized)
        - Enemy Upgrade Count (0-1, normalized)
        - Enemy Air/Ground Ratio (0-1)
Output: [Attack Probability, Defense Probability, Economy Probability, Tech Focus] (4-dimensional)

Note: Model structure updated to 15 inputs for context-aware decision making
This allows learning strategies like "Baneling drop timing" based on enemy position, tech, and resources

**Bases**: nn.Module

**Methods**:

- `__init__(4 args)`: Args:
    input_size: Input dimension (default 15: Self(5) + Enemy(10))
        - Self (5): Minerals...
- `forward(2 args)`: Forward pass

Args:
    x: Input tensor [batch_size, input_size]

Returns:
    Output tensor [batch_...

#### `ReinforcementLearner`

Reinforcement Learning Learner

Uses REINFORCE algorithm for policy gradient learning.

**Methods**:

- `__init__(5 args)`: Args:
    model: Neural network model to train
    learning_rate: Learning rate
    model_path: Mode...
- `_get_device(1 args)`: CPU/GPU auto-detection

GPU Priority: Automatically uses CUDA if NVIDIA GPU is available
Falls back ...
- `_load_model(1 args)`: Load model if saved (with file locking handling)
Priority: local_training/models/ > default models/
...
- `save_model(1 args)`: Save model (auto-create directory + file locking handling)

To prevent file conflicts when multiple ...
- `select_action(2 args)`: Select action based on state

Args:
    state: Game state [Minerals, Gas, Supply Used, Drone Count, ...
- `_normalize_state(2 args)`: Normalize state with improved scaling for Self(5) + Enemy(10) balance

CRITICAL IMPROVEMENT: Enhance...
- `record_step(4 args)`: Record one step (episode collection)

Args:
    state: Game state
    action: Selected action
    re...
- `finish_episode(2 args)`: Finish episode and update model (REINFORCE)

Optimized for GPU/CPU load balancing:
- Batch processin...
- `reset_episode(1 args)`: Reset episode records...

### Functions

#### `get_project_root`

Automatically finds the project root directory.
Searches for project root based on current file location.

---

