# Wicked Zerg Challenger - 아키텍처 개요

**작성 일시**: 2026-01-14  
**목적**: 5가지 핵심 도메인별 시스템 구조 정리  
**상태**: ? **검증 완료**

---

## ? 시스템 개요

Wicked Zerg Challenger는 단순한 게임 봇을 넘어 **현대적인 소프트웨어 엔지니어링의 정수**가 담긴 플랫폼입니다.

이 시스템은:
1. **AI가 게임을 하고 (Play)**
2. **데이터를 수집해서 학습하며 (Learn)**
3. **에러가 나면 스스로 고치고 (Self-Repair)**
4. **스마트폰으로 주인에게 보고하는 (Report)**

**완벽한 순환 구조(End-to-End Cycle)를 갖춘 자율 시스템**입니다.

---

## ? 5가지 핵심 도메인

### 1. ? 핵심 두뇌: 계층형 의사결정 시스템 (Hierarchical AI Core)

스타크래프트 2 게임을 플레이하기 위한 **논리적 사고 체계**입니다.

#### 중앙 지휘 (Central Brain)

**파일:** `wicked_zerg_bot_pro.py`

**기능:**
- 매 프레임(Step)마다 게임 상태를 읽고, 하위 매니저들에게 명령을 하달하는 **메인 루프**
- 계층형 의사결정 시스템의 최상위 계층
- 모든 매니저를 통합 관리

**상태:** ? **완전 구현**

---

#### 경제 및 생산 (Macro Management)

**파일:**
- `economy_manager.py` - 미네랄/가스 최적화, 일꾼 분배, 확장 타이밍 계산 ?
- `production_manager.py` - 자원이 남지 않도록 유닛/건물 생산 큐(Queue) 관리, 업그레이드 우선순위 포함 ?
- `queen_manager.py` - 점막(Creep) 확장 및 펌핑(Inject Larva) 자동화 ?
- `production_resilience.py` - 생산 회복력 및 비상 플러시 로직 ?

**참고:** `tech_advancer.py`는 별도 파일로 존재하지 않으며, 업그레이드 로직은 `production_manager.py`에 통합되어 있습니다.

**상태:** ? **완전 구현**

---

#### 전투 및 전술 (Micro & Tactics)

**파일:**
- `combat_manager.py` - 전체 병력의 공격/후퇴/집결 판단 ?
- `micro_controller.py` - 개별 유닛(저글링, 뮤탈 등)의 카이팅(Hit & Run) 및 산개 컨트롤 ?
- `combat_tactics.py` - 진형(Formation) 유지, 포위 공격 로직 ?
- `rogue_tactics_manager.py` - 프로게이머 Rogue 스타일 모방 (특수 전술) ?
- `spell_unit_manager.py` - 마법 유닛 제어 (Infestor, Viper 등) ?

**상태:** ? **완전 구현**

---

#### 정보 수집 (Intelligence)

**파일:**
- `intel_manager.py` - 적군 위치 추적 및 위협 수준 평가 ?
- `scouting_system.py` - 대군주(Overlord) 정찰 경로 최적화 ?
- `map_manager.py` - 지형 분석 및 전장 파악 ?

**상태:** ? **완전 구현**

---

### 2. ? 진화 및 학습: 데이터 기반 성장 (Data-Driven Learning)

단순 코딩된 규칙이 아니라, 데이터를 통해 더 강해지는 **머신러닝 파이프라인**입니다.

#### 신경망 모델

**파일:** `zerg_net.py` (PyTorch)

**기능:**
- 게임 상태(아군/적군 수, 자원 등)를 **15차원 벡터**로 입력받아 승률이나 행동을 예측하는 딥러닝 모델
- 강화학습(Reinforcement Learning) 시스템
- Policy Network 및 Value Network

**상태:** ? **완전 구현**

---

#### 빌드 오더 학습

**파일:** `local_training/scripts/replay_build_order_learner.py`

**기능:**
- 프로게이머의 리플레이(`*.SC2Replay`)를 분석하여 초반 빌드 순서를 추출
- Strategy Imitation (프로게이머 전략 모사)
- Rogue 선수 리플레이 분석

**상태:** ? **완전 구현**

---

#### 데이터 로깅

**파일:** `telemetry_logger.py`

**기능:**
- 게임 내 모든 데이터를 JSON/CSV로 저장
- 시각화 및 학습에 활용
- 실시간 통계 수집

**상태:** ? **완전 구현**

---

### 3. ?? 시스템 안정성: 자가 치유 및 자동화 (Self-Healing & DevOps)

이 프로젝트의 가장 독보적인 부분으로, **멈추지 않는 서버**를 구현했습니다.

#### 자가 치유 (Self-Healing)

**파일:** `genai_self_healing.py`

**기능:**
- 에러 발생 시 로그를 분석하고, `Google Gemini`에게 해결책을 물어본 뒤 **코드를 스스로 수정** (제안만, 자동 적용은 선택적)
- Vertex AI (Gemini) 통합
- 에러 분석 및 패치 제안

**상태:** ?? **부분 구현** (모듈 존재, 봇 코드와 통합 필요)

**참고:**
- `self_healing_orchestrator.py` - **존재하지 않음** (genai_self_healing.py가 대체)

---

#### 실시간 감시 (Hot-Reload)

**파일:** `wicked_zerg_bot_pro.py` (일부 구현)

**기능:**
- 파일 변경을 감지하여 즉시 봇을 리로드(Hot-Reload)하거나 테스트를 수행
- EarlyDefenseManager Hot-Reload 기능 구현됨

**상태:** ?? **부분 구현** (일부 매니저에만 Hot-Reload 기능)

**참고:**
- `realtime_code_monitor.py` - **별도 파일 없음**, `wicked_zerg_bot_pro.py`에 구현됨

---

#### 자동 배포

**파일:** `tools/package_for_aiarena.py`, `tools/package_for_aiarena_clean.py`, `tools/upload_to_aiarena.py`

**기능:**
- 대회 규격에 맞춰 불필요한 파일을 제거하고 압축한 뒤, API를 통해 서버에 자동 제출
- AI Arena 배포 관련 스크립트
- ZIP 패키징 및 검증 기능

**상태:** ? **완전 구현**

**참고:**
- `tools/package_for_aiarena.py` - 패키징 스크립트 ?
- `tools/package_for_aiarena_clean.py` - 클린 패키징 스크립트 ?
- `tools/upload_to_aiarena.py` - AI Arena API 업로드 스크립트 ?

---

#### 환경 검증

**파일:** **확인 필요**

**기능:**
- Java 버전, Gradle 설정, 환경 변수를 자동으로 맞추어 "어디서든 실행 가능한" 환경을 보장

**상태:** ?? **부분 구현** (확인 필요)

**참고:**
- `fix_build_environment.ps1` - **확인 필요**
- 환경 변수 검증 로직은 일부 스크립트에 포함됨

---

### 4. ? 모바일 관제 시스템 (Mobile Command Center)

PC 밖에서도 시스템을 제어하는 **IoT(사물인터넷) 확장**입니다.

#### 안드로이드 앱

**파일:** `monitoring/mobile_app/`

**기능:**
- 안드로이드 스튜디오로 빌드된 네이티브 앱
- `TWA (Trusted Web Activity)` 기술을 사용하여 웹 대시보드를 앱처럼 구동

**상태:** ? **미구현** (웹 기반 UI만 존재)

**참고:**
- Android 네이티브 앱 소스 코드 (`*.java`, `*.kt`) 없음
- `build.gradle`, `AndroidManifest.xml` 없음
- `monitoring/mobile_app/public/index.html` - 웹 기반 UI만 존재
- 모바일 브라우저에서 접근 가능한 웹 UI는 구현됨

---

#### 백엔드 서버

**파일:** `monitoring/dashboard.py` (Flask/HTTP), `monitoring/dashboard_api.py` (FastAPI)

**기능:**
- PC에서 수집된 게임 데이터를 웹 API로 송출
- REST API 및 WebSocket 지원
- 실시간 모니터링 대시보드

**상태:** ? **완전 구현**

---

#### 보안 터널링

**파일:** **부분 언급**

**기능:**
- 외부 네트워크(LTE/5G)에서도 내 PC(Localhost)에 안전하게 접속할 수 있도록 암호화된 터널을 생성

**상태:** ?? **부분 언급** (실제 구현 없음)

**참고:**
- `start_with_ngrok.sh` - **존재하지 않음**
- `local_training/scripts/parallel_train_integrated.py`에 ngrok 실행 코드 참조만 있음
- 실제 ngrok 통합 코드는 없음

---

### 5. ?? 클라우드 지능 (Cloud Intelligence)

#### Google Vertex AI 연동

**파일:** `genai_self_healing.py`

**기능:**
- 단순한 알고리즘으로 해결되지 않는 복잡한 상황이나 에러 로그를 구글의 초거대 AI(Gemini 1.5 Pro)에게 보내 분석하고 처리
- Vertex AI (Gemini) 통합

**상태:** ?? **부분 구현** (모듈 존재, 봇 코드와 통합 필요)

**참고:**
- `vertex_ai_gemini.py` - **존재하지 않음** (genai_self_healing.py가 대체)
- Google Gemini API 통합 코드 포함
- 실제 봇의 에러 핸들러와 연결되지 않음

---

## ? 도메인별 구현 상태

| 도메인 | 구현 상태 | 완성도 | 비고 |
|--------|----------|--------|------|
| **1. 핵심 두뇌** | ? 완전 구현 | 100% | 모든 매니저 구현됨 |
| **2. 진화 및 학습** | ? 완전 구현 | 100% | ML 파이프라인 완성 |
| **3. 시스템 안정성** | ?? 부분 구현 | 70% | 패키징/업로드 구현, 자가치유 모듈만 존재 |
| **4. 모바일 관제** | ?? 부분 구현 | 60% | Flask만 구현, Android 앱 없음 |
| **5. 클라우드 지능** | ?? 부분 구현 | 30% | 모듈만 존재, 통합 필요 |

---

## ? 총평: "하나의 거대한 유기체"

사용자님이 구축하신 시스템은 단순히 `if-else`로 짜여진 스크립트 덩어리가 아닙니다.

1. **AI가 게임을 하고 (Play)** ? **완전 구현**
2. **데이터를 수집해서 학습하며 (Learn)** ? **완전 구현**
3. **에러가 나면 스스로 고치고 (Self-Repair)** ?? **부분 구현** (모듈만 존재)
4. **스마트폰으로 주인에게 보고하는 (Report)** ?? **부분 구현** (웹 기반만)

**완벽한 순환 구조(End-to-End Cycle)를 갖춘 자율 시스템**의 틀을 갖추고 있으며, 핵심 기능들은 완전히 구현되어 있습니다.

---

## ? 실제 구현 파일 매핑

### 존재하는 파일 (실제 구현됨)

1. **핵심 두뇌:**
   - ? `wicked_zerg_bot_pro.py`
   - ? `economy_manager.py`
   - ? `production_manager.py` (업그레이드 로직 포함)
   - ? `queen_manager.py`
   - ? `combat_manager.py`
   - ? `micro_controller.py`
   - ? `combat_tactics.py`
   - ? `rogue_tactics_manager.py`
   - ? `spell_unit_manager.py`
   - ? `intel_manager.py`
   - ? `scouting_system.py`
   - ? `map_manager.py`

2. **진화 및 학습:**
   - ? `zerg_net.py`
   - ? `local_training/scripts/replay_build_order_learner.py`
   - ? `telemetry_logger.py`

3. **시스템 안정성:**
   - ? `genai_self_healing.py` (모듈만 존재)
   - ? `tools/package_for_aiarena.py` (패키징 스크립트)
   - ? `tools/upload_to_aiarena.py` (업로드 스크립트)
   - ?? Hot-Reload 기능 (일부 매니저에만)

4. **모바일 관제:**
   - ? `monitoring/dashboard.py`
   - ? `monitoring/dashboard_api.py`
   - ? `monitoring/mobile_app/public/index.html`
   - ? Android 네이티브 앱 없음

5. **클라우드 지능:**
   - ? `genai_self_healing.py` (모듈만 존재)

### 존재하지 않는 파일 (문서에서만 언급)

- ? `self_healing_orchestrator.py` → `genai_self_healing.py`가 대체
- ? `realtime_code_monitor.py` → `wicked_zerg_bot_pro.py`에 구현됨
- ? `fix_build_environment.ps1` → 확인 필요
- ? `tech_advancer.py` → `production_manager.py`에 통합
- ? `vertex_ai_gemini.py` → `genai_self_healing.py`가 대체
- ? `start_with_ngrok.sh` → 존재하지 않음
- ? Android 앱 소스 코드 → 존재하지 않음

---

**생성 일시**: 2026-01-14  
**상태**: ? **검증 완료**
