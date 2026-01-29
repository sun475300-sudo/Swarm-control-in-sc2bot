# Logic Audit & Improvement Report

이 문서는 Phase 10 완료 후, 코드베이스 전반에 걸쳐 추가적인 개선이 필요한 영역을 분석한 보고서입니다. 다음 단계(Phase 11)에 포함하거나 별도로 진행할 것을 권장합니다.

## 1. Production System (생산 시스템)

### 🚨 Smart Remax (생산 속도 제한 해제)
*   **현재 상태**: `ProductionController._process_production_queue`에서 프레임당 최대 5개의 생산 요청만 처리 (`max_per_frame = 5`).
*   **문제점**: 저그의 가장 큰 장점은 자원이 모였을 때 한 번에 수십 마리의 유닛(예: 저글링 50기)을 동시에 찍어내는 "순간 회전력(Instant Remax)"입니다. 현재 로직은 50기를 뽑으려면 최소 10프레임(약 0.5초) 이상 걸리며, 다른 로직과 겹치면 더 지연될 수 있습니다.
*   **제안**: 자원과 애벌레가 허용하는 한, **한 프레임에 가능한 모든 병력을 즉시 생산**하도록 제한을 해제하거나 대폭 상향해야 합니다.

## 2. Combat & Micro (전투 및 컨트롤)

### ⚔️ Zergling Surround (저글링 포위 공격)
*   **현재 상태**: `MicroCombat.kiting` 및 `focus_fire`는 주로 **거리를 벌리거나(Kiting)**, **점사(Focus Fire)**하는 데 초점이 맞춰져 있습니다.
*   **문제점**: 저글링은 사거리가 짧고 물량이 많으므로, 적을 **감싸서(Surround)** 공격 면적을 최대화하는 것이 필수입니다. 단순히 어택 땅(Attack-Move)이나 카이팅만 하면 뒤쪽 저글링은 놀게 되어 화력 손실이 발생합니다.
*   **제안**: `MicroCombat`에 **Surround Logic** 추가.
    *   적과 붙었을 때 공격 대신 적의 **뒤쪽으로 이동(Move)** 명령을 섞어 자연스럽게 감싸도록 유도.

### 🛑 Active Scout Safety (정찰 유닛 생존 본능)
*   **현재 상태**: `AdvancedScoutingSystemV2`는 정찰 유닛을 목표 지점으로 이동시키지만, **이동 중 공격받을 때의 회피 로직**이 부재합니다. (`OverlordSafetyManager`는 Idle 상태의 대군주만 관리)
*   **문제점**: 적 퀸이나 해병 등 대공 유닛을 만나도 무시하고 가다가 허무하게 잡힐 가능성이 큽니다.
*   **제안**: 정찰 유닛이 공격받거나 체력이 감소하면 즉시 **안전한 곳(본진 방향)으로 후퇴**하는 트리거 추가.

### 🧹 Creep Denial (점막 제거)
*   **현재 상태**: `CreepManager`는 아군 점막 확장에 집중하며, 적 점막을 제거하는 로직은 `CombatManager`에 명시적으로 확인되지 않았습니다.
*   **문제점**: ZvZ 또는 대 테란전에서 적의 점막/종양을 제거하지 않으면 맵 주도권을 뺏깁니다.
*   **제안**: `CombatManager` 또는 `HarassmentCoordinator`에 **적 종양(Creep Tumor) 탐지 및 제거** 태스크 추가. (감시군주 동반 필수)

## 3. Architecture & Reliability (아키텍처 및 신뢰성)

### 🧩 Broad Exception Handling (광범위한 예외 처리)
*   **현재 상태**: `bot_step_integration.py` 및 여러 매니저에서 `try: ... except Exception:` 구문이 자주 사용됩니다.
*   **문제점**: 치명적인 버그(NameError, SyntaxError 등)가 발생해도 로그만 남기고 묻혀버려, 원인을 찾기 어려울 수 있습니다.
*   **제안**: `except Exception` 블록을 최소화하고, 가능한 구체적인 예외(AttributeError, KeyError 등)로 분리하거나, 로그 레벨을 높여 디버깅을 용이하게 해야 합니다.

## 4. Other Suggestions
*   **Overlord Transport**: `HarassmentCoordinator`에 드랍 로직이 추가될 예정이지만, 대군주 "수송 업그레이드(Ventral Sacs)"와 "속업(Pneumatized Carapace)"의 우선순위 조율이 필요합니다.
*   **Burrow Logic**: 바퀴(Roach)의 잠복 회복(Burrow Heal) 마이크로가 강력합니다. 전투 중 체력이 낮은 바퀴를 잠복시키는 로직 추가를 고려해볼 만합니다.
