# D:\replays 경로 JSON 파일 설명

**작성일**: 2026-01-14

---

## ? JSON 파일 목록 및 용도

### 1. **리플레이 학습 관련 파일** (`D:\replays\replays\`)

#### `.learning_tracking.json`
- **위치**: `D:\replays\replays\.learning_tracking.json`
- **용도**: 리플레이 학습 진행 상황 추적 (내부 추적용)
- **내용**:
  - 각 리플레이 파일의 학습 반복 횟수 (`count`)
  - 마지막 학습 시간 (`last_trained`)
  - 완료 여부 (`completed`)
  - 파일 해시값을 키로 사용
- **사용 모듈**: `ReplayLearningTracker`

#### `learning_status.json`
- **위치**: `D:\replays\replays\learning_status.json`
- **용도**: 리플레이 학습 상태 관리 (하드 요구사항: 최소 5회 반복)
- **내용**:
  - 각 리플레이의 학습 횟수 추적
  - 완료 여부 (`completed: true/false`)
  - 파일 경로 정보
  - 최소 5회 반복 요구사항 강제
- **사용 모듈**: `LearningStatusManager`
- **특징**: 학습 완료 여부를 엄격하게 관리

#### `crash_log.json`
- **위치**: `D:\replays\replays\crash_log.json`
- **용도**: 리플레이 처리 중 크래시 추적 및 방지
- **내용**:
  - `in_progress`: 현재 처리 중인 리플레이 (중복 처리 방지)
  - `crash_count`: 각 리플레이의 크래시 횟수
  - `bad_replays`: 3회 이상 크래시된 리플레이 목록 (자동 스킵)
- **사용 모듈**: `ReplayCrashHandler`
- **기능**: 
  - 중복 처리 방지
  - 크래시된 리플레이 자동 스킵
  - 30분 이상 오래된 세션 자동 복구

#### `strategy_db.json`
- **위치**: `D:\replays\replays\strategy_db.json`
- **용도**: 추출된 전략 데이터베이스
- **내용**:
  - 빌드 오더 전략
  - 드롭 타이밍
  - 마이크로 컨트롤 전략
  - 매치업별 전략 분류
- **사용 모듈**: `StrategyDatabase`

---

### 2. **학습 통계 파일** (`D:\replays\`)

#### `learning_stats.json`
- **위치**: `D:\replays\learning_stats.json`
- **용도**: 전체 학습 통계 (리플레이 학습 + 게임 학습)
- **내용**: 학습 성능 지표, 진행 상황 등

#### `zergops_stats.json`
- **위치**: `D:\replays\zergops_stats.json`
- **용도**: Zerg 운영 통계
- **내용**: Zerg 플레이어 관련 통계 데이터

---

### 3. **아카이브 파일** (`D:\replays\archive\`)

#### `learned_build_orders.json`
- **위치**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\learned_build_orders.json`
- **용도**: 학습된 빌드 오더 파라미터 저장
- **내용**:
  - `learned_parameters`: 학습된 타이밍 파라미터 (supply 기준)
    - `natural_expansion_supply`: 확장 타이밍
    - `gas_supply`: 가스 추출기 타이밍
    - `spawning_pool_supply`: 스포닝 풀 타이밍
    - `roach_warren_supply`: 로치 워런 타이밍
    - `hydralisk_den_supply`: 히드라리스크 덴 타이밍
    - `lair_supply`: 레어 타이밍
    - `hive_supply`: 하이브 타이밍
  - `source_replays`: 학습에 사용된 리플레이 수
  - `build_orders`: 샘플 빌드 오더 (처음 10개)
- **생성 시점**: 리플레이 학습 완료 시
- **사용**: `config.py`의 `get_learned_parameter()` 함수가 이 파일을 읽어 사용

#### `instance_{id}_status.json`
- **위치**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\instance_{id}_status.json`
- **용도**: 병렬 학습 인스턴스별 상태 저장
- **내용**: 각 인스턴스의 학습 진행 상황, 게임 수, 승률 등

#### `supervised_training_stats.json`
- **위치**: `D:\replays\archive\training_YYYYMMDD_HHMMSS\supervised_training_stats.json`
- **용도**: 지도 학습 통계
- **내용**: 지도 학습 성능 지표

---

## ? 파일 간 관계

```
리플레이 학습 프로세스:
1. replay_build_order_learner.py 실행
   ↓
2. .learning_tracking.json 업데이트 (진행 상황)
   ↓
3. learning_status.json 업데이트 (하드 요구사항 체크)
   ↓
4. crash_log.json 체크 (크래시 방지)
   ↓
5. strategy_db.json 업데이트 (전략 저장)
   ↓
6. 학습 완료 시 → learned_build_orders.json 생성 (아카이브)
   ↓
7. 5회 이상 완료 → completed/ 폴더로 이동
```

---

## ? 주요 특징

### 하드 요구사항
- **최소 5회 반복**: 각 리플레이는 최소 5회 학습해야 완료로 간주
- **자동 완료 처리**: 5회 완료된 리플레이는 `completed/` 폴더로 자동 이동

### 크래시 방지
- **중복 처리 방지**: `crash_log.json`의 `in_progress`로 중복 처리 방지
- **Bad Replay 스킵**: 3회 이상 크래시된 리플레이는 자동 스킵
- **세션 복구**: 30분 이상 오래된 세션 자동 복구

### 데이터 일관성
- **파일 해시 기반**: 리플레이 파일의 해시값을 키로 사용하여 중복 방지
- **타임스탬프**: 모든 학습 활동에 타임스탬프 기록

---

## ?? 관리 명령어

### 학습 상태 초기화
```batch
bat\clear_learning_state.bat
```

### 완료된 리플레이 이동
```python
python local_training/scripts/move_completed_replays.py
```

### 학습 상태 확인
```powershell
Get-Content D:\replays\replays\learning_status.json -Encoding UTF8 | ConvertFrom-Json
```

---

**참고**: 모든 JSON 파일은 UTF-8 인코딩으로 저장되며, 한글 파일명도 지원합니다.
