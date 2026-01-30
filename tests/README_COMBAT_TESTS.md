# Combat Manager Unit Tests

## 📋 개요

이 디렉토리에는 `combat_manager.py` 및 관련 전투 컴포넌트에 대한 유닛 테스트가 포함되어 있습니다.

**목적**: combat_manager.py를 안전하게 리팩토링하기 위한 안전장치

## 🧪 테스트 파일

### 1. `test_combat_manager.py`
**전투 매니저 핵심 기능 테스트**

- ✅ 초기화 및 매니저 컴포넌트
- ✅ 기지 방어 시스템
- ✅ 랠리 포인트 관리
- ✅ 병력 관리 및 임계값
- ✅ 위협 평가
- ✅ 후퇴 조건
- ✅ 멀티태스킹 시스템
- ✅ 전투 통계
- ✅ 통합 테스트 (전체 전투 사이클)
- ✅ 성능 테스트 (대규모 병력)

**테스트 클래스:**
- `TestCombatManagerInitialization`: 초기화
- `TestBaseDefense`: 기지 방어
- `TestRallyPoint`: 랠리 포인트
- `TestArmyManagement`: 병력 관리
- `TestThreatAssessment`: 위협 평가
- `TestRetreatConditions`: 후퇴 조건
- `TestMultitasking`: 멀티태스킹
- `TestCombatStatistics`: 통계
- `TestCombatIntegration`: 통합
- `TestCombatPerformance`: 성능

### 2. `test_combat_components.py`
**전투 컴포넌트 (Targeting, Micro, Boids) 테스트**

- ✅ Targeting System (타겟 우선순위)
- ✅ Micro Combat (키팅, 포위, 후퇴)
- ✅ Boids Swarm Control (분리, 정렬, 응집)
- ✅ 통합 시나리오
- ✅ 엣지 케이스

**테스트 클래스:**
- `TestTargeting`: 타겟팅 시스템
- `TestMicroCombat`: 마이크로 컨트롤
- `TestBoidsSwarmControl`: Boids 군집 제어
- `TestCombatComponentsIntegration`: 컴포넌트 통합
- `TestEdgeCases`: 엣지 케이스

## 🚀 테스트 실행

### 전체 테스트 실행
```bash
pytest tests/test_combat_manager.py tests/test_combat_components.py -v
```

### 특정 테스트 클래스 실행
```bash
pytest tests/test_combat_manager.py::TestBaseDefense -v
```

### 특정 테스트 메서드 실행
```bash
pytest tests/test_combat_manager.py::TestBaseDefense::test_base_under_attack_detection -v
```

### 커버리지 측정
```bash
pytest tests/test_combat_*.py --cov=wicked_zerg_challenger/combat_manager --cov-report=html
```

### 성능 테스트만 실행
```bash
pytest tests/test_combat_manager.py::TestCombatPerformance -v
```

## 📊 현재 테스트 커버리지

| 컴포넌트 | 테스트 수 | 커버리지 | 상태 |
|---------|----------|---------|------|
| CombatManager 초기화 | 2 | ~80% | ✅ |
| 기지 방어 | 2 | ~70% | ✅ |
| 랠리 포인트 | 1 | ~60% | ✅ |
| 병력 관리 | 2 | ~75% | ✅ |
| 위협 평가 | 1 | ~50% | ✅ |
| 후퇴 조건 | 2 | ~80% | ✅ |
| 멀티태스킹 | 2 | ~60% | ✅ |
| 타겟팅 | 5 | ~70% | ✅ |
| 마이크로 | 4 | ~65% | ✅ |
| Boids | 4 | ~60% | ✅ |
| 통합/성능 | 4 | ~50% | ✅ |
| **전체** | **29** | **~65%** | ✅ |

## 🎯 테스트 목표

- [x] 기본 기능 테스트 작성 (29개)
- [ ] 커버리지 70% 이상 달성
- [ ] 모든 엣지 케이스 커버
- [ ] 통합 테스트 강화

## 🔧 Mock 객체

테스트에서 사용되는 Mock 객체:

### `MockUnit`
SC2 유닛을 시뮬레이션하는 Mock 객체
- `tag`: 유닛 태그
- `type_id`: 유닛 타입
- `position`: 위치 (x, y)
- `health`, `health_max`: 체력
- `weapon_cooldown`: 무기 쿨다운
- `distance_to()`: 거리 계산

### `MockUnits`
유닛 컬렉션 Mock
- `closer_than()`: 거리 필터링
- `closest_to()`: 가장 가까운 유닛
- `filter()`: 조건 필터링
- `of_type()`: 타입별 필터링

### `MockBot`
SC2 봇 Mock
- `units`: 아군 유닛
- `enemy_units`: 적 유닛
- `townhalls`: 기지
- `time`: 게임 시간
- `do()`: 명령 실행 (기록용)

## 📝 테스트 작성 가이드

### 1. 새 테스트 추가
```python
class TestNewFeature:
    """새 기능 테스트"""

    def test_feature_name(self):
        """기능 설명"""
        # Arrange
        bot = MockBot()
        combat = CombatManager(bot)

        # Act
        result = combat.some_method()

        # Assert
        assert result is not None
```

### 2. Async 테스트
```python
@pytest.mark.asyncio
async def test_async_feature(self):
    """비동기 기능 테스트"""
    bot = MockBot()
    combat = CombatManager(bot)

    await combat.on_step(0)

    assert combat.some_state is True
```

### 3. 통합 테스트
```python
def test_integration_scenario(self):
    """통합 시나리오 테스트"""
    # 복잡한 시나리오 설정
    bot = MockBot()
    # ... 설정

    # 여러 프레임 시뮬레이션
    for i in range(100):
        await combat.on_step(i)

    # 최종 상태 검증
    assert combat.final_state_check()
```

## 🐛 알려진 이슈

1. **타겟팅 시스템 커버리지 부족**
   - 공중 유닛 타겟팅 로직 미테스트
   - 해결: 추가 테스트 케이스 필요

2. **Boids 알고리즘 엣지 케이스**
   - 단일 유닛 시나리오 미완성
   - 해결: `test_single_unit_boids` 강화 필요

3. **성능 테스트 임계값**
   - 100ms/frame 임계값이 너무 관대할 수 있음
   - 해결: 실제 게임 환경에서 벤치마크 후 조정

## 📈 리팩토링 체크리스트

combat_manager.py 리팩토링 전 확인사항:

- [x] 유닛 테스트 작성 완료 (29개)
- [ ] 모든 테스트 통과 확인
- [ ] 커버리지 70% 이상
- [ ] 성능 테스트 통과
- [ ] CI/CD 파이프라인 통합
- [ ] 리팩토링 후 테스트 재실행

## 🚨 중요 사항

**리팩토링하기 전에 반드시:**

1. ✅ 모든 테스트가 통과하는지 확인
2. ✅ 새로운 기능 추가 시 테스트도 함께 작성
3. ✅ 리팩토링 후 전체 테스트 재실행
4. ✅ 커버리지 감소하지 않도록 주의

## 🔗 관련 문서

- [Python pytest 문서](https://docs.pytest.org/)
- [unittest.mock 가이드](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

## 📞 문의

테스트 관련 문제는 GitHub Issues에 보고해 주세요.
