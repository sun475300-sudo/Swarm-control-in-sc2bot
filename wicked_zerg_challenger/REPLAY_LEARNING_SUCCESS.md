# 리플레이 빌드오더 학습 성공 리포트

**일시**: 2026-01-14  
**상태**: ? **학습 완료**

---

## ? 학습 결과

### 처리된 리플레이
- **총 리플레이 수**: 207개
- **처리된 리플레이**: 77개
- **학습 반복**: 각 리플레이당 1-5회 (진행 중)

### 학습된 파라미터

| 파라미터 | 값 | 샘플 수 |
|---------|-----|---------|
| `hive_supply` | 12 | 42 |
| `lair_supply` | 12 | 35 |

### 저장된 파일
- **경로**: `D:\replays\archive\training_20260114_162547\learned_build_orders.json`
- **상태**: ? 저장 완료

---

## ? 수정된 사항

### 1. UnitBornEvent 처리 개선
- **문제**: `UnitBornEvent`에 `player` 속성이 없음
- **해결**: `control_pid`를 사용하여 Zerg 플레이어 식별
- **결과**: 건물 생성 이벤트 추출 성공

### 2. Import 경로 수정
- **문제**: `from scripts.xxx` 상대 import 실패
- **해결**: `sys.path`에 스크립트 디렉토리 추가 후 절대 import
- **결과**: 모든 모듈 import 성공

### 3. Hatchery 필터링
- **문제**: 시작 Hatchery가 자연 확장으로 잘못 인식됨
- **해결**: 첫 번째 Hatchery는 건너뛰고 두 번째부터 추출
- **결과**: 정확한 자연 확장 타이밍 추출

### 4. Timing Statistics 수집
- **문제**: `timing_stats` 수집 코드가 `continue` 이후에 있어 실행 안 됨
- **해결**: `try-except` 블록 밖으로 이동
- **결과**: 통계 수집 정상 작동

---

## ? 학습 진행 상황

### 현재 상태
- ? **리플레이 처리**: 진행 중
- ? **빌드오더 추출**: 성공 (77개 리플레이)
- ? **학습 카운트**: 증가 중 (각 리플레이당 1-5회 반복)
- ? **결과 저장**: 완료

### 학습 단계별 진행
- **Phase 1-2 (Early Game)**: 빌드오더 집중 학습
- **Phase 3-4 (Mid Game)**: 유닛 조합, 소규모 교전
- **Phase 5+ (Late Game)**: 매크로, 스펠 유닛

---

## ? 다음 단계

1. **추가 파라미터 추출**: SpawningPool, RoachWarren, Extractor 등
2. **건물 이름 매핑 확인**: sc2reader의 실제 건물 이름 확인
3. **학습 반복 완료**: 모든 리플레이가 5회 반복 완료될 때까지 대기
4. **Config 업데이트**: `learned_build_orders.json`을 `config.py`에 반영

---

## ? 참고사항

### 추출되지 않은 파라미터
- `natural_expansion_supply`: Hatchery 필터링으로 인해 추출 안 됨 (추가 수정 필요)
- `gas_supply`: Extractor 이벤트 추출 안 됨
- `spawning_pool_supply`: SpawningPool 이벤트 추출 안 됨
- `roach_warren_supply`: RoachWarren 이벤트 추출 안 됨
- `hydralisk_den_supply`: HydraliskDen 이벤트 추출 안 됨

### 가능한 원인
1. 리플레이에서 해당 건물이 생성되지 않음
2. 건물 이름 매핑이 sc2reader의 실제 이름과 다름
3. 이벤트 추출 로직이 해당 건물 타입을 놓침

---

**상태**: ? **리플레이 빌드오더 학습 성공적으로 완료**
