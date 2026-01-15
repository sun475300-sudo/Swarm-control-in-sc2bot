# 리팩토링 분석 리포트

**생성 일시**: 2026-01-15
**목적**: 대규모 리팩토링 및 코드 품질 개선을 위한 분석

---

## 1. 중복 함수 (리팩토링 우선순위: 높음)

총 72개의 중복 함수 패턴을 발견했습니다.

### main(0 args) (64회)

- `COMPLETE_RUN_SCRIPT.py:287` - `main`
- `run.py:69` - `main`
- `local_training\scripts\learning_logger.py:174` - `main`
- `local_training\scripts\move_completed_replays.py:157` - `main`
- `local_training\scripts\replay_build_order_learner.py:771` - `main`
- `local_training\scripts\replay_learning_manager.py:212` - `main`
- `local_training\scripts\replay_quality_filter.py:330` - `main`
- `local_training\scripts\run_hybrid_supervised.py:94` - `main`
- `local_training\scripts\strategy_database.py:204` - `main`
- `monitoring\compare_server_android_data.py:199` - `main`
- `monitoring\config_server.py:206` - `main`
- `monitoring\get_ngrok_url.py:42` - `main`
- `monitoring\ngrok_tunnel.py:200` - `main`
- `monitoring\start_with_ngrok.py:48` - `main`
- `monitoring\update_android_ngrok_url.py:105` - `main`
- `tools\analyze_and_cleanup.py:231` - `main`
- `tools\analyze_telemetry.py:319` - `main`
- `tools\apply_code_improvements.py:186` - `main`
- `tools\arena_update.py:46` - `main`
- `tools\auto_classify_drive.py:219` - `main`
- `tools\auto_commit_after_training.py:201` - `main`
- `tools\auto_documentation_generator.py:227` - `main`
- `tools\auto_git_push.py:144` - `main`
- `tools\background_parallel_learner.py:478` - `main`
- `tools\check_all_api_keys.py:88` - `main`
- `tools\check_all_sources.py:117` - `main`
- `tools\check_api_key.py:63` - `main`
- `tools\check_learning_progress.py:214` - `main`
- `tools\check_replay_paths.py:19` - `main`
- `tools\check_replay_selection.py:51` - `main`
- `tools\claude_code_executor.py:235` - `main`
- `tools\claude_code_project_analyzer.py:306` - `main`
- `tools\cleanup_artifacts.py:190` - `main`
- `tools\cleanup_deploy.py:15` - `main`
- `tools\clean_duplicates.py:149` - `main`
- `tools\code_diet_analyzer.py:176` - `main`
- `tools\code_quality_improver.py:204` - `main`
- `tools\compare_archive_paths.py:10` - `main`
- `tools\compare_pro_vs_training_replays.py:459` - `main`
- `tools\comprehensive_code_improvement.py:368` - `main`
- `tools\convert_to_euc_kr.py:155` - `main`
- `tools\download_and_train.py:1064` - `main`
- `tools\extract_and_train_from_training.py:380` - `main`
- `tools\fix_all_encoding_issues.py:73` - `main`
- `tools\generate_pwa_icons.py:91` - `main`
- `tools\generate_readme.py:483` - `main`
- `tools\integrated_pipeline.py:39` - `main`
- `tools\large_scale_refactoring.py:168` - `main`
- `tools\merge_training_stats.py:118` - `main`
- `tools\optimize_and_sort_learning_data.py:193` - `main`
- `tools\package_for_aiarena.py:723` - `main`
- `tools\package_for_aiarena_clean.py:396` - `main`
- `tools\package_for_aiarena_clean_fixed.py:388` - `main`
- `tools\pre_training_check.py:343` - `main`
- `tools\prune_updates.py:31` - `main`
- `tools\remove_old_api_keys.py:101` - `main`
- `tools\remove_unused_imports.py:105` - `main`
- `tools\replay_lifecycle_manager.py:450` - `main`
- `tools\runtime_check.py:218` - `main`
- `tools\self_diagnosis.py:12` - `main`
- `tools\setup_verify.py:11` - `main`
- `tools\upload_report.py:33` - `main`
- `tools\upload_to_aiarena.py:191` - `main`
- `tools\validate_arena_deployment.py:298` - `main`

### __init__(2 args) (35회)

- `combat_manager.py:27` - `__init__`
- `config.py:200` - `__init__`
- `economy_manager.py:22` - `__init__`
- `intel_manager.py:163` - `__init__`
- `map_manager.py:71` - `__init__`
- `micro_controller.py:104` - `__init__`
- `micro_controller.py:195` - `__init__`
- `micro_controller.py:25` - `__init__`
- `production_manager.py:74` - `__init__`
- `queen_manager.py:9` - `__init__`
- `rogue_tactics_manager.py:35` - `__init__`
- `scouting_system.py:62` - `__init__`
- `spell_unit_manager.py:33` - `__init__`
- `unit_factory.py:47` - `__init__`
- `local_training\build_order_learner.py:82` - `__init__`
- `local_training\combat_tactics.py:9` - `__init__`
- `local_training\curriculum_manager.py:10` - `__init__`
- `local_training\production_resilience.py:23` - `__init__`
- `local_training\scripts\learning_logger.py:21` - `__init__`
- `local_training\scripts\replay_build_order_learner.py:41` - `__init__`
- `local_training\scripts\replay_quality_filter.py:57` - `__init__`
- `local_training\scripts\strategy_database.py:65` - `__init__`
- `monitoring\bot_api_connector.py:85` - `__init__`
- `monitoring\manus_sync.py:24` - `__init__`
- `sc2_env\mock_env.py:57` - `__init__`
- `services\learning_service_client.py:29` - `__init__`
- `services\service_registry.py:43` - `__init__`
- `services\telemetry_service_client.py:29` - `__init__`
- `tools\apply_code_improvements.py:24` - `__init__`
- `tools\build_order_comparator.py:52` - `__init__`
- `tools\code_diet_analyzer.py:16` - `__init__`
- `tools\download_and_train.py:1047` - `__init__`
- `tools\extract_and_train_from_training.py:36` - `__init__`
- `tools\package_for_aiarena.py:163` - `__init__`
- `tools\training_session_manager.py:63` - `__init__`

### __init__(1 args) (16회)

- `wicked_zerg_bot_pro.py:166` - `__init__`
- `monitoring\config_server.py:36` - `__init__`
- `monitoring\dashboard.py:147` - `__init__`
- `sc2_env\mock_env.py:153` - `__init__`
- `tools\api_key_access_control.py:9` - `__init__`
- `tools\auto_documentation_generator.py:20` - `__init__`
- `tools\background_parallel_learner.py:62` - `__init__`
- `tools\claude_code_executor.py:20` - `__init__`
- `tools\claude_code_project_analyzer.py:23` - `__init__`
- `tools\code_quality_improver.py:26` - `__init__`
- `tools\comprehensive_code_improvement.py:30` - `__init__`
- `tools\download_and_train.py:175` - `__init__`
- `tools\large_scale_refactoring.py:22` - `__init__`
- `tools\refactoring_analyzer.py:21` - `__init__`
- `tools\replay_lifecycle_manager.py:94` - `__init__`
- `tools\upload_to_aiarena.py:18` - `__init__`

### __init__(3 args) (14회)

- `micro_controller.py:334` - `__init__`
- `telemetry_logger.py:26` - `__init__`
- `local_training\build_order_learner.py:270` - `__init__`
- `local_training\personality_manager.py:24` - `__init__`
- `local_training\strategy_audit.py:91` - `__init__`
- `local_training\scripts\learning_status_manager.py:31` - `__init__`
- `local_training\scripts\replay_crash_handler.py:28` - `__init__`
- `local_training\scripts\replay_learning_manager.py:32` - `__init__`
- `local_training\scripts\replay_learning_tracker_sqlite.py:41` - `__init__`
- `monitoring\ngrok_tunnel.py:29` - `__init__`
- `monitoring\telemetry_logger.py:27` - `__init__`
- `tools\analyze_telemetry.py:37` - `__init__`
- `tools\api_key_usage_limiter.py:11` - `__init__`
- `tools\compare_pro_vs_training_replays.py:37` - `__init__`

### __init__(4 args) (5회)

- `zerg_net.py:90` - `__init__`
- `monitoring\manus_dashboard_client.py:22` - `__init__`
- `tools\auto_classify_drive.py:54` - `__init__`
- `tools\package_for_aiarena_clean.py:62` - `__init__`
- `tools\package_for_aiarena_clean_fixed.py:55` - `__init__`

### initialize(1 args) (4회)

- `combat_manager.py:72` - `initialize`
- `scouting_system.py:125` - `initialize`
- `wicked_zerg_bot_pro.py:819` - `initialize`
- `wicked_zerg_bot_pro.py:833` - `initialize`

### __post_init__(1 args) (4회)

- `local_training\build_order_learner.py:66` - `__post_init__`
- `monitoring\bot_api_connector.py:39` - `__post_init__`
- `monitoring\bot_api_connector.py:70` - `__post_init__`
- `services\service_registry.py:30` - `__post_init__`

### generate_report(1 args) (4회)

- `tools\analyze_and_cleanup.py:204` - `generate_report`
- `tools\analyze_telemetry.py:228` - `generate_report`
- `tools\auto_classify_drive.py:190` - `generate_report`
- `tools\code_diet_analyzer.py:132` - `generate_report`

### _cleanup_build_reservations(1 args) (3회)

- `economy_manager.py:78` - `_cleanup_build_reservations`
- `production_manager.py:431` - `_cleanup_build_reservations`
- `local_training\production_resilience.py:57` - `_cleanup_build_reservations`

### __init__(5 args) (3회)

- `genai_self_healing.py:141` - `__init__`
- `zerg_net.py:149` - `__init__`
- `monitoring\remote_client.py:25` - `__init__`

### close(1 args) (3회)

- `wicked_zerg_bot_pro.py:171` - `close`
- `wicked_zerg_bot_pro.py:438` - `close`
- `services\telemetry_service_client.py:198` - `close`

### get_venv_dir(0 args) (3회)

- `local_training\main_integrated.py:19` - `get_venv_dir`
- `local_training\scripts\parallel_train_integrated.py:117` - `get_venv_dir`
- `tools\download_and_train.py:58` - `get_venv_dir`

### get_learning_count(2 args) (3회)

- `local_training\scripts\learning_status_manager.py:104` - `get_learning_count`
- `local_training\scripts\replay_learning_manager.py:139` - `get_learning_count`
- `local_training\scripts\replay_learning_tracker_sqlite.py:124` - `get_learning_count`

### is_completed(2 args) (3회)

- `local_training\scripts\learning_status_manager.py:145` - `is_completed`
- `local_training\scripts\replay_learning_manager.py:169` - `is_completed`
- `local_training\scripts\replay_learning_tracker_sqlite.py:171` - `is_completed`

### find_all_python_files(0 args) (3회)

- `tools\auto_documentation_generator.py:212` - `find_all_python_files`
- `tools\code_quality_improver.py:189` - `find_all_python_files`
- `tools\refactoring_analyzer.py:227` - `find_all_python_files`

### analyze_file(2 args) (3회)

- `tools\auto_documentation_generator.py:25` - `analyze_file`
- `tools\code_diet_analyzer.py:22` - `analyze_file`
- `tools\refactoring_analyzer.py:29` - `analyze_file`

### analyze_dependencies(1 args) (3회)

- `tools\claude_code_project_analyzer.py:73` - `analyze_dependencies`
- `tools\comprehensive_code_improvement.py:217` - `analyze_dependencies`
- `tools\large_scale_refactoring.py:58` - `analyze_dependencies`

### should_exclude(1 args) (3회)

- `tools\package_for_aiarena_clean.py:259` - `should_exclude`
- `tools\package_for_aiarena_clean_fixed.py:251` - `should_exclude`
- `tools\remove_old_api_keys.py:37` - `should_exclude`

### _load_curriculum_level(1 args) (2회)

- `combat_manager.py:56` - `_load_curriculum_level`
- `production_manager.py:220` - `_load_curriculum_level`

### start_dashboard_server(1 args) (2회)

- `COMPLETE_RUN_SCRIPT.py:253` - `start_dashboard_server`
- `monitoring\start_with_ngrok.py:30` - `start_dashboard_server`

## 2. 긴 함수 (100줄 이상, 리팩토링 권장)

총 38개의 긴 함수를 발견했습니다.

- `local_training\main_integrated.py:351` - `run_training` (900줄)
- `wicked_zerg_bot_pro.py:191` - `__init__` (352줄)
- `local_training\scripts\parallel_train_integrated.py:522` - `start_parallel_training` (343줄)
- `local_training\scripts\replay_build_order_learner.py:78` - `extract_build_order` (271줄)
- `combat_manager.py:532` - `_should_attack` (259줄)
- `tools\integrated_pipeline.py:39` - `main` (254줄)
- `wicked_zerg_bot_pro.py:6009` - `_calculate_build_order_reward` (239줄)
- `tools\analyze_and_cleanup.py:12` - `analyze_project` (191줄)
- `local_training\scripts\replay_build_order_learner.py:510` - `learn_from_replays` (182줄)
- `zerg_net.py:282` - `_load_model` (179줄)
- `wicked_zerg_bot_pro.py:4775` - `_collect_state` (178줄)
- `tools\self_diagnosis.py:12` - `main` (173줄)
- `zerg_net.py:767` - `finish_episode` (148줄)
- `production_manager.py:74` - `__init__` (145줄)
- `tools\check_replay_paths.py:19` - `main` (143줄)
- `intel_manager.py:279` - `update` (142줄)
- `tools\replay_lifecycle_manager.py:192` - `cleanup_after_training` (141줄)
- `local_training\scripts\parallel_train_integrated.py:139` - `check_gpu_memory` (136줄)
- `local_training\scripts\parallel_train_integrated.py:340` - `display_dashboard` (132줄)
- `local_training\scripts\move_completed_replays.py:25` - `move_completed_replays` (131줄)

## 3. 복잡한 함수 (순환 복잡도 10 이상, 리팩토링 권장)

총 108개의 복잡한 함수를 발견했습니다.

- `local_training\main_integrated.py:351` - `run_training` (복잡도: 132)
- `local_training\scripts\replay_build_order_learner.py:78` - `extract_build_order` (복잡도: 99)
- `combat_manager.py:532` - `_should_attack` (복잡도: 83)
- `intel_manager.py:820` - `should_attack` (복잡도: 41)
- `tools\integrated_pipeline.py:39` - `main` (복잡도: 41)
- `wicked_zerg_bot_pro.py:191` - `__init__` (복잡도: 36)
- `wicked_zerg_bot_pro.py:6009` - `_calculate_build_order_reward` (복잡도: 34)
- `local_training\scripts\parallel_train_integrated.py:522` - `start_parallel_training` (복잡도: 34)
- `tools\analyze_and_cleanup.py:12` - `analyze_project` (복잡도: 33)
- `local_training\scripts\replay_build_order_learner.py:392` - `_extract_strategies` (복잡도: 28)
- `scouting_system.py:352` - `_detect_enemy` (복잡도: 27)
- `local_training\scripts\replay_build_order_learner.py:510` - `learn_from_replays` (복잡도: 27)
- `tools\self_diagnosis.py:12` - `main` (복잡도: 27)
- `wicked_zerg_bot_pro.py:4775` - `_collect_state` (복잡도: 26)
- `production_manager.py:4331` - `_calculate_tech_priority_score` (복잡도: 25)
- `combat_manager.py:233` - `_update_army_status` (복잡도: 24)
- `zerg_net.py:282` - `_load_model` (복잡도: 23)
- `tools\code_quality_improver.py:31` - `remove_unused_imports` (복잡도: 23)
- `tools\replay_lifecycle_manager.py:192` - `cleanup_after_training` (복잡도: 23)
- `local_training\scripts\move_completed_replays.py:25` - `move_completed_replays` (복잡도: 22)

## 4. 큰 클래스 (메서드 20개 이상, 리팩토링 권장)

총 2개의 큰 클래스를 발견했습니다.

- `tools\download_and_train.py:187` - `ReplayDownloader` (25개 메서드)
- `combat_manager.py:26` - `CombatManager` (22개 메서드)

## 5. 중복 코드 블록 (5줄 이상, 리팩토링 권장)

총 20개의 중복 코드 블록을 발견했습니다.

### 중복 횟수: 11

**코드 미리보기**:
```python
try: with open(file_path, 'r', encoding='utf-8', errors='replace') as f: content = f.read() tree = a...
```

**발견 위치**:
- `tools\claude_code_project_analyzer.py:83`
- `tools\claude_code_project_analyzer.py:185`
- `tools\claude_code_project_analyzer.py:186`
- `tools\code_quality_improver.py:161`
- `tools\comprehensive_code_improvement.py:49`
- `tools\comprehensive_code_improvement.py:191`
- `tools\comprehensive_code_improvement.py:231`
- `tools\large_scale_refactoring.py:37`
- `tools\large_scale_refactoring.py:69`
- `tools\large_scale_refactoring.py:70`
- `tools\remove_unused_imports.py:19`

### 중복 횟수: 9

**코드 미리보기**:
```python
print("=" * 70) if __name__ == "__main__": main()
```

**발견 위치**:
- `tools\apply_code_improvements.py:247`
- `tools\check_all_api_keys.py:187`
- `tools\claude_code_project_analyzer.py:350`
- `tools\code_quality_improver.py:272`
- `tools\compare_pro_vs_training_replays.py:514`
- `tools\comprehensive_code_improvement.py:406`
- `tools\extract_and_train_from_training.py:434`
- `tools\large_scale_refactoring.py:202`
- `tools\remove_unused_imports.py:160`

### 중복 횟수: 8

**코드 미리보기**:
```python
except Exception: pass return None
```

**발견 위치**:
- `local_training\scripts\parallel_train_integrated.py:299`
- `local_training\scripts\parallel_train_integrated.py:300`
- `local_training\scripts\parallel_train_integrated.py:334`
- `local_training\scripts\parallel_train_integrated.py:335`
- `monitoring\config_server.py:67`
- `monitoring\config_server.py:200`
- `monitoring\monitoring_utils.py:41`
- `monitoring\monitoring_utils.py:61`

### 중복 횟수: 8

**코드 미리보기**:
```python
def main(): """메인 함수""" import argparse
```

**발견 위치**:
- `tools\apply_code_improvements.py:184`
- `tools\apply_code_improvements.py:185`
- `tools\claude_code_executor.py:233`
- `tools\claude_code_executor.py:234`
- `tools\code_quality_improver.py:202`
- `tools\code_quality_improver.py:203`
- `tools\remove_unused_imports.py:103`
- `tools\remove_unused_imports.py:104`

### 중복 횟수: 7

**코드 미리보기**:
```python
) return except Exception: pass
```

**발견 위치**:
- `economy_manager.py:2488`
- `scouting_system.py:556`
- `scouting_system.py:577`
- `wicked_zerg_bot_pro.py:3308`
- `wicked_zerg_bot_pro.py:3329`
- `wicked_zerg_bot_pro.py:3350`
- `wicked_zerg_bot_pro.py:3405`

### 중복 횟수: 7

**코드 미리보기**:
```python
except Exception: pass return False
```

**발견 위치**:
- `production_manager.py:2304`
- `production_manager.py:5040`
- `production_manager.py:5191`
- `production_manager.py:6378`
- `monitoring\telemetry_logger_atomic.py:58`
- `monitoring\telemetry_logger_atomic.py:101`
- `monitoring\telemetry_logger_atomic.py:153`

### 중복 횟수: 7

**코드 미리보기**:
```python
for file in files: if file.endswith('.py'): file_path = Path(root) / file try:
```

**발견 위치**:
- `tools\claude_code_executor.py:90`
- `tools\claude_code_project_analyzer.py:79`
- `tools\comprehensive_code_improvement.py:45`
- `tools\comprehensive_code_improvement.py:104`
- `tools\comprehensive_code_improvement.py:187`
- `tools\comprehensive_code_improvement.py:227`
- `tools\large_scale_refactoring.py:33`

### 중복 횟수: 6

**코드 미리보기**:
```python
spawning_pools = list( b.units.filter( lambda u: u.type_id == UnitTypeId.SPAWNINGPOOL and u.is_struc...
```

**발견 위치**:
- `combat_manager.py:677`
- `economy_manager.py:933`
- `production_manager.py:3531`
- `production_manager.py:3545`
- `unit_factory.py:245`
- `unit_factory.py:284`

### 중복 횟수: 6

**코드 미리보기**:
```python
# if hasattr(b, "personality_manager"): # from personality_manager import ChatPriority # await b.per...
```

**발견 위치**:
- `economy_manager.py:792`
- `economy_manager.py:864`
- `economy_manager.py:1081`
- `production_manager.py:4497`
- `production_manager.py:4520`
- `production_manager.py:4762`

### 중복 횟수: 6

**코드 미리보기**:
```python
except Exception: continue except Exception: pass
```

**발견 위치**:
- `economy_manager.py:1372`
- `economy_manager.py:1538`
- `economy_manager.py:1706`
- `production_manager.py:1853`
- `production_manager.py:2849`
- `production_manager.py:2992`

---

## 클로드 코드 활용 제안

다음 작업들은 클로드 코드를 활용하여 효율적으로 수행할 수 있습니다:

1. **중복 함수 통합**: 중복된 함수들을 공통 유틸리티로 추출
2. **긴 함수 분리**: 긴 함수를 작은 함수로 분리
3. **복잡한 함수 단순화**: 복잡한 로직을 더 읽기 쉽게 리팩토링
4. **큰 클래스 분리**: 큰 클래스를 더 작은 클래스로 분리
5. **중복 코드 제거**: 중복 코드 블록을 공통 함수로 추출

