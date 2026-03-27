<div align="center">

# 스타크래프트 II 군집 제어 시스템

### 멀티 에이전트 드론 군집 연구를 위한 지능형 통합 관제 시스템

**시뮬레이션에서 현실로: 강화학습 · 자가치유 DevOps · 모바일 GCS**

[![GitHub](https://img.shields.io/badge/GitHub-Swarm--control--in--sc2bot-181717?logo=github)](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![SC2 API](https://img.shields.io/badge/StarCraft%20II-burnysc2-FF6600)](https://github.com/BurnySc2/python-sc2)
[![PyTorch](https://img.shields.io/badge/PyTorch-RL%20Engine-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![파일수](https://img.shields.io/badge/Python%20파일-362-success)]()
[![테스트](https://img.shields.io/badge/테스트-327%20통과-brightgreen)]()
[![버그수정](https://img.shields.io/badge/버그%20수정-87건-critical)]()
[![구문검사](https://img.shields.io/badge/구문%20검사-100%25-brightgreen)]()

</div>

---

## 개요

> 이 프로젝트는 **게임이 아닙니다.**
> **Google DeepMind(AlphaStar)** 와 **미국 공군(USAF VISTA X-62A)** 이 실제로 사용하는 방식 그대로,
> 스타크래프트 II를 **드론 군집 제어(Swarm Control)** 실험 환경으로 활용한 연구입니다.

```
실제 드론 50~200대 실험  →  수천만~수억 원
시뮬레이션 기반 실험       →  안전 · 무비용 · 무한 반복
```

---

## 주요 기능

### 1. 지능형 전략 관리 (Strategy Manager V2)
- **종족별 맞춤 빌드오더**: ZvP 로치 러쉬, ZvT 해처리 퍼스트, ZvZ 14풀
- **위협 감지 및 대응**: 비상/경고/일반 모드 자동 전환
- **실시간 빌드 패턴 분석**: Intel Manager 연동 (terran_bio, protoss_stargate 등)

### 2. 경제 및 생산 최적화
- **동적 가스 일꾼 관리**: 가스 뱅킹 500+ 시 자동 감소 (심각도별 0~2명 유지)
- **강제 확장 시스템**: 타이밍 테이블 기반 자동 확장 (8초~6분)
- **매크로 해처리**: 자원 과잉 시 자동 건설

### 3. 고급 전투 시스템
- **Advanced Micro Controller v3**: 8종 유닛별 전술 (레바저 담즙, 럴커 잠복, 퀸 힐, 살모사 유인)
- **Focus Fire Coordinator**: 오버킬 방지 집중 사격
- **Stutter Step Kiting**: 히드라/바퀴 허리돌리기

### 4. 정찰 시스템 V2
- **동적 정찰 주기**: 초반 25초 → 테크 타이밍 20초 → 중반 40초 → 긴급 15초
- **순찰 경로 시스템**: 다중 웨이포인트 + 젤나가 감시탑 확보
- **변신수 분산 배치**: 오버시어 자동 관리

### 5. 자가치유 DevOps
- **Gemini AI 자동 패치**: 런타임 에러 → AI 분석 → 자동 수정 → 재시작
- **자동 모니터링**: 1시간 주기 버그 탐지 + 커밋

---

## 프로젝트 구조

| 디렉토리 | 설명 | 파일 수 |
|----------|------|---------|
| `wicked_zerg_challenger/` | 메인 봇 엔진 | 362+ |
| `combat/` | 전투 시스템 (12+ 모듈) | 65 |
| `scouting/` | 정찰 시스템 V2 | 20 |
| `local_training/` | 로컬 훈련 (RL/IL) | 45 |
| `config/` | 설정 관리 | 15 |
| `tests/` | 테스트 스위트 | 15 |
| `core/` | 매니저 레지스트리 | 10 |

---

## 품질 대시보드

| 지표 | 수치 | 상태 |
|------|------|------|
| Python 파일 수 | 362 | ✅ 전체 구문 검사 통과 |
| 누적 버그 수정 | 87건 (8 세션) | ✅ CRITICAL 0건 잔존 |
| 테스트 스위트 | 327 passed / 0 failed | ✅ 100% 통과 |
| 빌드오더 | 9개 | ✅ Roach Rush, Hatch First 등 |
| 마이크로 컨트롤러 | 8종 유닛별 전술 | ✅ Ravager, Lurker, Queen, Viper... |
| CI/CD | GitHub Actions | ✅ py_compile + pytest 자동 실행 |
| 자동 모니터링 | 1시간 주기 | ✅ 스케줄 태스크 운영 중 |

---

## 승률 분석 (100게임)

| 매치업 | 승 | 패 | 승률 | 주요 대응 |
|--------|---|---|------|----------|
| **vs Terran** | 6 | 17 | 26% | Hatch First 16 → 링/바네 전환 |
| **vs Zerg** | 5 | 29 | 15% | 14풀 안정 오프닝 |
| **vs Protoss** | 3 | 40 | 7% | Roach Rush 타이밍 전환 적용 |
| **전체** | 14 | 86 | 14% | 가스 뱅킹 + 올인 타이밍 수정 완료 |

### 최근 개선 (2026-03-27)
- 가스 뱅킹 임계값 1500→500 하향 (심각도별 가스 일꾼 0~2명 유지)
- RapidVictorySystem 올인 3분→8분 + 최소 서플 40 조건
- 4개 파괴 시스템 로직 충돌 해결 (UnitAuthority 연동)
- 189개 MD 리포트 → docs/archive/ 정리
- 테스트 327 passed, 0 skipped, 0 failed

---

## 기술 스택

| 카테고리 | 기술 |
|----------|------|
| **언어** | Python 3.10+ |
| **AI/ML** | PyTorch, RL Policy Network, 모방학습, SC2 리플레이 마이닝 |
| **시뮬레이션** | StarCraft II API (burnysc2/python-sc2) |
| **DevOps** | Vertex AI (Gemini) 자가치유 파이프라인 |
| **GCS** | Flask Dashboard + TypeScript/React + Android App |
| **알고리즘** | Potential-Field Navigation, 비동기 동시성 제어 |
| **CI/QA** | GitHub Actions, py_compile, 327+ tests |

---

## 시뮬레이션-현실 매핑

| StarCraft II (가상) | 실제 드론 (물리) |
|---------------------|-----------------|
| 전장의 안개 (Fog of War) | 센서 불확실성 |
| 200기 유닛 제어 | 멀티 UAV 군집 |
| 자원 최적화 | 배터리/우선순위 관리 |
| 빌드 중복 방지 | SSoT 무결성 |
| 동적 전술 전환 | 임무 재할당 |
| 비동기 동시성 | 실시간 C2 |

---

## 커리어 연결

- **UAV/UGV 자율제어 시스템** — 군집 드론 실시간 관제
- **방산 무인체계 군집 알고리즘** — Multi-Agent 전술 의사결정
- **AI/ML Engineer** — 강화학습, 모방학습, 멀티에이전트 AI
- **DevOps/MLOps** — Self-Healing Infrastructure, 자동화 파이프라인
- **로봇/자율주행 C2** — Command & Control 시스템 설계
- **방위산업/항공우주** — ISR 임무 계획, 대군집 방어

---

## 요구 사항

- Python 3.10+
- StarCraft II (설치 필요)
- burnysc2 (`pip install burnysc2`)
- PyTorch (RL 기능 사용 시)

---

<div align="center">

**장선우 (Jang Sun Woo)**

Drone Application Engineering

[![Email](https://img.shields.io/badge/Email-sun475300%40naver.com-03C75A?logo=naver&logoColor=white)](mailto:sun475300@naver.com)
[![GitHub](https://img.shields.io/badge/GitHub-sun475300--sudo-181717?logo=github)](https://github.com/sun475300-sudo)

</div>

---

<div align="center">

<sub>Built with Python · StarCraft II API · PyTorch · Gemini AI</sub>

</div>
