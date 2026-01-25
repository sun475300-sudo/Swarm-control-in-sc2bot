# 추가 발견된 로직 버그 및 잠재적 문제 보고서 (Additional Bugs Report)

기존에 확인된 확장 문제 외에도, 코드베이스 전반에서 안정성과 성능에 영향을 줄 수 있는 잠재적 문제점들을 발견했습니다.

## 1. 묵음 실패 (Silent Failures)

`except: pass`로 예외를 잡고 아무런 처리를 하지 않는 코드가 다수 발견되었습니다. 이는 버그 발생 시 원인 파악을 불가능하게 만듭니다.

### 발견 위치
*   **`economy_manager.py` (Line 651, 662):** 방어 건물 건설 (`build`) 실패 시 예외를 무시합니다. 자원이 소모되었는데 건물이 지어지지 않았는지 알 수 없습니다.
*   **`run_with_training.py` (Line 53):** 레지스트리에서 SC2 경로를 찾는 과정에서 에러가 나면 그냥 넘어갑니다. (이건 의도된 것일 수 있으나 로그는 남기는 것이 좋습니다.)

**권고:** 모든 `except` 블록에 최소한 `print(f"[ERROR] ... {e}")` 로그를 추가해야 합니다.

## 2. 매니저 초기화 순서 문제

`WickedZergBotProImpl.py`에서 `ProductionResilience`가 `EconomyManager`보다 **먼저** 초기화됩니다.

```python
# Line 77
self.production = ProductionResilience(self) 

# Line 88
self.economy = EconomyManager(self)
```

하지만 `BotStepIntegrator.py`의 실행 순서는:
1. `EconomyManager` (Line 313)
2. `ProductionResilience.fix_production_bottleneck` (Line 322)

두 매니저가 서로의 상태(예: `bot.production`)를 참조하는 경우, 초기화 순서와 실행 순서가 중요합니다. 현재 구조에서는 `EconomyManager`가 `self.bot.production`을 참조할 수 있으므로, 초기화 순서는 맞지만 **역할 분담이 모호**합니다. (둘 다 생산/확장에 관여함)

## 3. 포괄적 에러 처리 (Blanket Error Catching)

`BotStepIntegrator.py`의 `_safe_manager_step` 메서드는 모든 `Exception`을 잡아내고 로그만 남깁니다.

```python
        except Exception as e:
            success = False
            if iteration % 200 == 0:  # 200프레임마다만 로그 출력
                print(f"[WARNING] {label} error: {e}")
```

**문제점:**
*   **간헐적 에러 무시:** 200프레임(약 9초) 사이에 발생하는 에러는 로그조차 찍히지 않고 무시됩니다.
*   **중요 로직 누락:** 예를 들어 `EconomyManager`가 199프레임 동안 에러로 멈춰 있어도 사용자는 모를 수 있습니다.

**권고:** 에러 발생 시 **매번** 로그를 남기거나, 에러 카운터를 두어 임계값 초과 시 경고를 보내야 합니다.

## 4. `run_with_training.py`의 프로세스 관리

게임 종료 후 SC2 프로세스를 정리하는 로직이 `psutil`에 의존적입니다.

```python
                try:
                    import psutil
                    # ... 프로세스 확인 로직 ...
                except ImportError:
                    # psutil 없으면 그냥 대기
                    time.sleep(wait_between_games)
```

만약 훈련 환경에 `psutil`이 없거나 권한 문제로 실패하면, SC2 좀비 프로세스가 쌓여 시스템 메모리를 고갈시킬 수 있습니다.

**권고:** `psutil`을 필수 의존성으로 강제하거나, `taskkill` 명령어를 사용하는 폴백(fallback) 로직을 추가해야 합니다.

## 요약 및 우선순위

1.  **[High]** `ProductionResilience`의 자원 소비 로직 수정 (확장 버그 해결 - 이미 리포트됨)
2.  **[Medium]** `economy_manager.py`의 `except: pass` 제거 및 로그 추가.
3.  **[Medium]** `BotStepIntegrator.py`의 에러 로깅 빈도 증가 (모든 에러 기록).
4.  **[Low]** `run_with_training.py`의 리셋 로직 강화.
