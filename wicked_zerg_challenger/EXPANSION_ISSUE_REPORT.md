# 확장 기지 미확보 원인 분석 보고서 (Expansion Issue Report)

사용자가 제보한 "확장 기지를 안 먹는 현상"에 대해 코드베이스를 분석한 결과, **자원 관리 로직의 치명적인 결함**이 원인임을 확인했습니다.

## 🚨 핵심 원인: "200원 천장" 문제

`ProductionResilience.py`의 `fix_production_bottleneck` 함수에서 **병력 생산 로직이 확장 로직보다 먼저 실행**되며, 미네랄이 **200원을 넘자마자 저글링으로 소모**해버립니다.

### 코드 분석 (`local_training/production_resilience.py`)

```python
    async def fix_production_bottleneck(self):
        # ...
        
        # [문제 1] 미네랄이 200만 넘으면 즉시 소비 로직 실행 (Line 316)
        if b.minerals > 200:
            await self._spend_excess_minerals()

        # [문제 2] 확장은 미네랄 400 이상일 때 시도하지만, 위에서 이미 200까지 씀 (Line 323)
        if time >= 60 and b.minerals > 400:
            await self._try_expand()
```

그리고 `_spend_excess_minerals` 함수 내부:

```python
    async def _spend_excess_minerals(self):
        # ...
        # [문제 3] 미네랄이 200 이상이면 저글링을 찍어서 150~200 수준으로 낮춤
        if b.minerals > 200:
             zerglings_to_make = ...
             await self._safe_train(larva, UnitTypeId.ZERGLING)
```

### 결과 시나리오
1.  봇이 미네랄을 열심히 모아 **250**원이 됩니다.
2.  해처리를 지으려면 **300**원이 필요합니다.
3.  하지만 `_spend_excess_minerals`가 발동되어 저글링 1~2기를 찍어버립니다.
4.  미네랄이 **200원**으로 떨어집니다.
5.  다음 프레임에 다시 **250**원을 모으면 또 저글링을 찍습니다.
6.  결과적으로 **영원히 300원에 도달하지 못해 확장을 할 수 없습니다.**

---

## 🔍 추가 원인: 전략 모듈의 드론 제한

*   `AggressiveStrategy` (12 Pool 등)가 활성화되면 드론 수를 **12~13기로 제한**합니다.
*   하지만 `ProductionResilience`는 이 제한을 무시하고 드론/유닛을 찍어내려 하므로, **전략 모듈과 생산 모듈 간의 부조화**도 존재합니다.

---

## ✅ 해결 방안 권고

1.  **임계값 상향:** `_spend_excess_minerals`의 발동 조건을 **200원에서 600원 이상**으로 높여야 합니다. (해처리 비용 300 + 여유분 확보)
2.  **순서 변경:** `fix_production_bottleneck` 함수 내에서 **확장 체크(`_try_expand`)를 소비 로직(`_spend_excess_minerals`)보다 먼저** 실행해야 합니다.
3.  **예외 처리:** "현재 건설 중인 해처리가 0개일 때"는 소비 로직을 막는 조건문을 추가해야 합니다.
