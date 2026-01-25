# 훈련 시스템 수정 사항

실행 일시: 2026-01-25

---

## 수정된 문제들

### 1. Point2 Import 누락
**파일:** `local_training/hierarchical_rl/improved_hierarchical_rl.py`

**문제:**
- Combat Agent에서 Point2를 사용하는데 import하지 않음
- 에러: `name 'Point2' is not defined`
- 견제와 정찰 기능이 작동하지 않음

**수정:**
```python
# 파일 상단에 추가
try:
    from sc2.position import Point2
except ImportError:
    Point2 = None
```

---

### 2. IntelManager enemy_main_base_location 누락
**파일:** `intel_manager.py`

**문제:**
- ScoutingSystem에서 `enemy_main_base_location` 속성 참조
- IntelManager __init__에서 초기화하지 않음
- 에러: `'IntelManager' object has no attribute 'enemy_main_base_location'`

**수정:**
```python
def __init__(self, bot):
    # ... 기존 코드 ...
    self.enemy_main_base_location = None  # 추가
```

---

### 3. 게임 시간 제한 추가
**파일:** `wicked_zerg_bot_pro_impl.py`

**문제:**
- 봇이 제대로 플레이하지 못하면 게임이 무한히 진행됨
- 자연 확장 실패, 자원 부족 등으로 게임이 끝나지 않음

**수정:**
```python
async def on_step(self, iteration: int):
    # 게임 시간 제한 (10분)
    if self.time > 600:  # 600초 = 10분
        print(f"[AUTO SURRENDER] Game time limit reached ({self.time:.0f}s). Surrendering...")
        await self.client.leave()
        return
    # ... 기존 로직 ...
```

---

## 예상 효과

✅ **견제 및 정찰 작동**
- Point2 에러 해결로 Combat Agent 정상 작동
- 적 확장 견제, 정찰 유닛 이동 가능

✅ **정찰 시스템 정상화**
- enemy_main_base_location 속성 접근 가능
- 적 본진 위치 추적 정상 작동

✅ **게임 정상 종료**
- 10분 시간 제한으로 무한 게임 방지
- 훈련 데이터 정상 수집 가능
- 빠른 학습 사이클

---

## 다음 개선 필요 사항

### 1. 봇 전략 문제
- **자연 확장 실패**: DESPERATE EXPANSION 계속 발생
- **자원 관리**: 미네랄이 극도로 부족한 상황 발생
- **원인**: 일꾼 생산 과다, 건물 배치 실패 등

### 2. 패배 감지 강화
- 일정 시간 동안 유닛/건물이 거의 없으면 조기 항복
- 자원이 지속적으로 부족하면 항복

### 3. 훈련 효율성
- 현재: 게임당 최대 10분 소요
- 개선: 초반 전략 집중 훈련 (5분 제한)

---

## 훈련 재시작 준비

모든 수정 완료. 다음 명령으로 훈련 재시작:

```bash
cd wicked_zerg_challenger
python run_with_training.py
```

**변경 사항:**
- Point2 import 추가
- enemy_main_base_location 속성 추가
- 10분 게임 시간 제한

**기대 결과:**
- 게임 정상 종료
- 견제 및 정찰 작동
- 훈련 데이터 정상 수집
