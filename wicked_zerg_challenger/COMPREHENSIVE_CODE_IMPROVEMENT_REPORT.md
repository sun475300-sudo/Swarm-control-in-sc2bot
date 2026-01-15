# 종합 코드 품질 개선 리포트

**생성 일시**: 2026-01-15
**목적**: 코드 품질 개선 및 대규모 리팩토링을 위한 종합 분석

---

## 1. 사용하지 않는 Import 정리

총 67개 파일에서 사용하지 않는 import를 발견했습니다.

**총 사용하지 않는 import**: 316개

### `chat_manager.py`

- `chat_manager_utf8.ChatManager`

### `combat_manager.py`

- `traceback`
- `config.TARGET_PRIORITY`
- `config.Config`
- `config.GamePhase`
- `sc2.data.Race`
- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.position.Point2`
- `sc2.unit.Unit`
- `sc2.ids.upgrade_id.UpgradeId`
- `wicked_zerg_bot_pro.WickedZergBotPro`
- `personality_manager.ChatPriority`

### `COMPLETE_RUN_SCRIPT.py`

- `loguru.logger`
- `wicked_zerg_bot_pro.WickedZergBotPro`
- `sc2.data.Race`
- `sc2.data.Difficulty`
- `sc2.main.run_game`
- `sc2.player.Bot`
- `sc2.player.Computer`
- `sc2.maps`

### `config.py`

- `dataclasses.dataclass`
- `enum.Enum`
- `enum.auto`
- `sc2.ids.unit_typeid.UnitTypeId`
- `loguru.logger`

### `economy_manager.py`

- `config.Config`
- `sc2.bot_ai.BotAI`
- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.ids.upgrade_id.UpgradeId`
- `sc2.position.Point2`
- `config.get_learned_parameter`

### `genai_self_healing.py`

- `dataclasses.dataclass`
- `dataclasses.asdict`
- `google.generativeai`
- `loguru.logger`
- `tools.load_api_key.get_gemini_api_key`

### `intel_manager.py`

- `dataclasses.dataclass`
- `dataclasses.field`
- `enum.Enum`
- `enum.IntEnum`
- `enum.auto`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.position.Point2`
- `sc2.unit.Unit`
- `sc2.ids.upgrade_id.UpgradeId`
- `wicked_zerg_bot_pro.WickedZergBotPro`
- `config.TARGET_PRIORITY`

### `micro_controller.py`

- `dataclasses.dataclass`
- `sc2.position.Point2`
- `sc2.position.Point3`
- `sc2.unit.Unit`
- `sc2.units.Units`

### `production_manager.py`

- `config.COUNTER_BUILD`
- `config.Config`
- `config.EnemyRace`
- `config.GamePhase`
- `config.get_learned_parameter`
- `unit_factory.UnitFactory`
- `sc2.data.Race`
- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.ids.upgrade_id.UpgradeId`
- `sc2.position.Point2`
- `wicked_zerg_bot_pro.WickedZergBotPro`
- `personality_manager.ChatPriority`
- `loguru.logger`
- `local_training.personality_manager.ChatPriority`

### `queen_manager.py`

- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.buff_id.BuffId`
- `sc2.ids.unit_typeid.UnitTypeId`

### `rogue_tactics_manager.py`

- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.ids.upgrade_id.UpgradeId`
- `sc2.position.Point2`
- `sc2.unit.Unit`
- `wicked_zerg_bot_pro.WickedZergBotPro`

### `run.py`

- `wicked_zerg_bot_pro.WickedZergBotPro`
- `sc2.data.Race`
- `sc2.data.Difficulty`
- `sc2.main.run_game`
- `sc2.player.Bot`
- `sc2.player.Computer`
- `sc2.maps`
- `sc2.main.run_ladder_game`

### `scouting_system.py`

- `dataclasses.dataclass`
- `sc2.bot_ai.BotAI`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.position.Point2`
- `config.THREAT_BUILDINGS`
- `config.Config`
- `config.EnemyRace`
- `config.GamePhase`

### `spell_unit_manager.py`

- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.position.Point2`
- `sc2.unit.Unit`
- `wicked_zerg_bot_pro.WickedZergBotPro`

### `telemetry_logger.py`

- `sc2.data.Result`
- `sc2.ids.unit_typeid.UnitTypeId`
- `monitoring.manus_dashboard_client.create_client_from_env`

### `unit_factory.py`

- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `config.EnemyRace`
- `config.GamePhase`
- `loguru.logger`

### `wicked_zerg_bot_pro.py`

- `io`
- `combat_manager.CombatManager`
- `config.Config`
- `config.EnemyRace`
- `config.GamePhase`
- `economy_manager.EconomyManager`
- `intel_manager.IntelManager`
- `rogue_tactics_manager.RogueTacticsManager`
- `production_manager.ProductionManager`
- `production_resilience.ProductionResilience`
- `queen_manager.QueenManager`
- `scouting_system.ScoutingSystem`
- `telemetry_logger.TelemetryLogger`
- `sc2.bot_ai.BotAI`
- `sc2.data.Race`
- `sc2.data.Result`
- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `numpy`
- `combat_tactics.CombatTactics`
- `micro_controller.MicroController`
- `personality_manager.PersonalityManager`
- `strategy_analyzer.StrategyAnalyzer`
- `bot_api_connector.bot_connector`
- `genai_self_healing.GenAISelfHealing`
- `genai_self_healing.init_self_healing`
- `debug_visualizer.DebugVisualizer`
- `zerg_net.Action`
- `zerg_net.ReinforcementLearner`
- `zerg_net.ZergNet`
- `spell_unit_manager.SpellUnitManager`
- `sc2.ids.buff_id.BuffId`
- `loguru.logger`
- `local_training.combat_tactics.CombatTactics`
- `local_training.personality_manager.PersonalityManager`
- `build_order_comparator.BuildOrderComparator`
- `local_training.strategy_audit.analyze_bot_performance`
- `tools.training_session_manager.TrainingSessionManager`
- `tools.training_session_manager.TrainingSessionManager`
- `local_training.strategy_audit.StrategyAudit`

### `zerg_net.py`

- `enum.Enum`
- `numpy`
- `multiprocessing`

### `local_training\build_order_learner.py`

- `dataclasses.dataclass`
- `sc2.ids.unit_typeid.UnitTypeId`
- `sc2.ids.ability_id.AbilityId`

### `local_training\combat_tactics.py`

- `sc2.data.Race`
- `sc2.ids.ability_id.AbilityId`
- `sc2.ids.unit_typeid.UnitTypeId`
- `config.Config`

## 2. 중복 코드 블록

총 30개의 중복 코드 블록을 발견했습니다.

### 중복 횟수: 89

**코드 미리보기**:
```python
except Exception: pass 
```

**발견 위치**:
- `combat_manager.py:1478`
- `combat_manager.py:1532`
- `combat_manager.py:1820`
- `economy_manager.py:231`
- `economy_manager.py:1250`

### 중복 횟수: 68

**코드 미리보기**:
```python
except Exception as e: 
```

**발견 위치**:
- `combat_manager.py:2025`
- `economy_manager.py:1842`
- `economy_manager.py:1888`
- `genai_self_healing.py:185`
- `production_manager.py:752`

### 중복 횟수: 13

**코드 미리보기**:
```python
from pathlib import Path 
```

**발견 위치**:
- `COMPLETE_RUN_SCRIPT.py:14`
- `run.py:3`
- `run_with_training.py:11`
- `local_training\main_integrated.py:11`
- `local_training\scripts\move_completed_replays.py:10`

### 중복 횟수: 13

**코드 미리보기**:
```python
current_iteration = getattr(b, "iteration", 0) 
```

**발견 위치**:
- `economy_manager.py:749`
- `economy_manager.py:822`
- `economy_manager.py:987`
- `economy_manager.py:1784`
- `production_manager.py:2117`

### 중복 횟수: 12

**코드 미리보기**:
```python
from sc2.ids.ability_id import AbilityId 
```

**발견 위치**:
- `combat_manager.py:18`
- `economy_manager.py:15`
- `production_manager.py:28`
- `queen_manager.py:3`
- `rogue_tactics_manager.py:16`

### 중복 횟수: 12

**코드 미리보기**:
```python
from sc2.ids.unit_typeid import UnitTypeId 
```

**발견 위치**:
- `combat_manager.py:19`
- `config.py:8`
- `config.py:9`
- `economy_manager.py:16`
- `production_manager.py:29`

### 중복 횟수: 12

**코드 미리보기**:
```python
traceback.print_exc() 
```

**발견 위치**:
- `economy_manager.py:2011`
- `production_manager.py:3450`
- `production_manager.py:3506`
- `rogue_tactics_manager.py:463`
- `wicked_zerg_bot_pro.py:725`

### 중복 횟수: 11

**코드 미리보기**:
```python
try: with open(file_path, 'r', encoding='utf-8', errors='replace') as f: content = f.read() tree = ast.parse(content, filename=str(file_path))
```

**발견 위치**:
- `tools\claude_code_project_analyzer.py:83`
- `tools\claude_code_project_analyzer.py:185`
- `tools\claude_code_project_analyzer.py:186`
- `tools\code_quality_improver.py:161`
- `tools\comprehensive_code_improvement.py:49`

### 중복 횟수: 10

**코드 미리보기**:
```python
intel = getattr(b, "intel", None) 
```

**발견 위치**:
- `combat_manager.py:559`
- `combat_manager.py:635`
- `combat_manager.py:659`
- `combat_manager.py:660`
- `combat_manager.py:710`

### 중복 횟수: 10

**코드 미리보기**:
```python
report_parts.append("") 
```

**발견 위치**:
- `tools\compare_pro_vs_training_replays.py:332`
- `tools\compare_pro_vs_training_replays.py:341`
- `tools\compare_pro_vs_training_replays.py:355`
- `tools\compare_pro_vs_training_replays.py:393`
- `tools\compare_pro_vs_training_replays.py:394`

## 3. 코드 스타일 이슈

총 33개 파일에서 스타일 이슈를 발견했습니다.

**총 스타일 이슈**: 323개

### `combat_manager.py`

- Line 225: Line too long (195 characters)
- Line 256: Line too long (152 characters)
- Line 272: Line too long (156 characters)
- Line 320: Line too long (159 characters)
- Line 621: Line too long (164 characters)

### `economy_manager.py`

- Line 63: Line too long (134 characters)
- Line 452: Line too long (123 characters)
- Line 458: Line too long (159 characters)
- Line 473: Line too long (167 characters)
- Line 515: Line too long (123 characters)

### `genai_self_healing.py`

- Line 401: Line too long (123 characters)
- Line 407: Line too long (124 characters)

### `production_manager.py`

- Line 171: Line too long (151 characters)
- Line 282: Line too long (140 characters)
- Line 326: Line too long (140 characters)
- Line 592: Line too long (142 characters)
- Line 597: Line too long (180 characters)

### `queen_manager.py`

- Line 35: Line too long (131 characters)
- Line 98: Line too long (143 characters)

### `rogue_tactics_manager.py`

- Line 489: Line too long (127 characters)

### `scouting_system.py`

- Line 423: Line too long (134 characters)
- Line 435: Line too long (133 characters)
- Line 451: Line too long (168 characters)
- Line 718: Line too long (180 characters)

### `telemetry_logger.py`

- Line 490: Line too long (124 characters)

### `unit_factory.py`

- Line 140: Line too long (139 characters)
- Line 169: Line too long (176 characters)
- Line 269: Line too long (122 characters)

### `wicked_zerg_bot_pro.py`

- Line 428: Line too long (137 characters)
- Line 564: Line too long (131 characters)
- Line 592: Line too long (134 characters)
- Line 693: Line too long (134 characters)
- Line 698: Line too long (125 characters)

## 4. 클래스 리팩토링 제안

총 2개의 클래스 리팩토링 제안이 있습니다.

### `combat_manager.py:26` - `CombatManager`

- **메서드 수**: 22개
- **제안**: Consider splitting into smaller classes
- **주요 메서드**: __init__, _load_curriculum_level, _should_relax_retreat_conditions, initialize, _determine_combat_mode, _update_army_status, _check_army_gathered, _should_retreat, _should_attack, _find_enemy_clusters

### `tools\download_and_train.py:187` - `ReplayDownloader`

- **메서드 수**: 25개
- **제안**: Consider splitting into smaller classes
- **주요 메서드**: __init__, _scan_existing_hashes, _get_file_hash, _is_duplicate, _organize_replay_file, _match_pro_name, _is_pro_tournament, _google_search_fallback, _http_head, _http_get

## 5. 의존성 최적화 제안

총 2개 파일에서 의존성 이슈를 발견했습니다.

### `wicked_zerg_bot_pro.py`

- **의존성 수**: 27개
- **제안**: Consider splitting into smaller modules
- **주요 의존성**: intel_manager, personality_manager, economy_manager, combat_tactics, rogue_tactics_manager, production_manager, debug_visualizer, build_order_comparator, production_resilience, zerg_net

### `local_training\main_integrated.py`

- **의존성 수**: 16개
- **제안**: Consider splitting into smaller modules
- **주요 의존성**: error_handler, extract_replay_insights, wicked_zerg_bot_pro, loguru, curriculum_manager, learning_accelerator, datetime, scripts, performance_monitor, self_evolution

---

## 개선 작업 제안

### 우선순위 1: 사용하지 않는 Import 제거

```bash
# 자동으로 제거 (주의: 검토 필요)
python tools/remove_unused_imports.py
```

### 우선순위 2: 중복 코드 제거

중복 코드 블록을 공통 함수로 추출하여 제거

### 우선순위 3: 코드 스타일 통일

```bash
# black 또는 autopep8 사용
black wicked_zerg_challenger/
# 또는
autopep8 --in-place --recursive wicked_zerg_challenger/
```

### 우선순위 4: 클래스 리팩토링

큰 클래스를 작은 클래스로 분리

### 우선순위 5: 의존성 최적화

의존성이 많은 파일을 작은 모듈로 분리

