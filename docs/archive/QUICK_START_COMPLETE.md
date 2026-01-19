# ? Quick Start Guide - Complete System

**작성일**: 2026-01-15  
**상태**: ? **실행 가능한 완전한 시스템**

---

## ? 사전 요구사항

### 필수
- Python 3.10 이상
- pip (Python 패키지 관리자)

### 선택사항
- StarCraft II (실제 게임 실행용)
- CUDA 지원 GPU (학습 가속용)

---

## ? 빠른 시작 (3단계)

### 1단계: 저장소 클론

```bash
git clone https://github.com/your-username/Swarm-contol-in-sc2bot.git
cd Swarm-contol-in-sc2bot
```

### 2단계: 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv .venv

# 가상환경 활성화
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 의존성 설치
pip install -r wicked_zerg_challenger/requirements.txt
pip install -r requirements_new_structure.txt  # 새 구조용 (있는 경우)
```

### 3단계: 실행

```bash
# 메인 메뉴 실행 (가장 쉬운 방법)
python main.py

# 또는 빠른 시작 (Mock Battle만)
python main.py --quick-start

# 또는 Mock만 (SC2 없이)
python main.py --mock-only
```

---

## ? 실행 옵션

### 옵션 1: SC2 Bot 실행 (실제 게임)

```bash
cd wicked_zerg_challenger
python run.py
```

**요구사항**:
- StarCraft II 설치 필요
- SC2PATH 환경 변수 설정 (또는 자동 감지)

### 옵션 2: Mock Battle (SC2 없이)

```bash
python scripts/run_mock_battle.py
```

**장점**:
- SC2 설치 불필요
- 빠른 테스트 가능
- CI/CD 테스트에 적합

### 옵션 3: 학습 파이프라인

```bash
cd wicked_zerg_challenger
python tools/integrated_pipeline.py --epochs 3
```

**기능**:
- Replay 파일에서 학습
- PyTorch 모델 학습
- 자동 정리 및 아카이브

### 옵션 4: 프로젝트 정리

```bash
python wicked_zerg_challenger/tools/clean_duplicates.py --dry-run  # 미리보기
python wicked_zerg_challenger/tools/clean_duplicates.py  # 실제 실행
```

---

## ? 핵심 기능

### 1. 군집 제어 알고리즘 (드론 전공 연계)

**실제 구현된 알고리즘**:
- **Potential Field Method**: 장애물 회피 및 형성 유지
- **Boids Algorithm**: 자연스러운 무리 행동
- **Separation, Alignment, Cohesion**: 핵심 군집 행동

**위치**: `wicked_zerg_challenger/micro_controller.py`

**실제 드론 군집 제어에 직접 적용 가능**:
```python
from micro_controller import MicroController, SwarmConfig

# 군집 제어 초기화
config = SwarmConfig(
    separation_distance=2.0,  # 최소 거리
    alignment_radius=5.0,      # 정렬 반경
    cohesion_radius=8.0         # 응집 반경
)
controller = MicroController(config=config)

# 형성 제어 실행
target_positions = controller.execute_formation_control(
    units=drone_units,
    formation_center=center_point,
    formation_type="circle"  # 또는 "line", "wedge"
)
```

### 2. 강화학습 엔진

**실제 구현된 모델**:
- **ZergNet**: 15차원 입력 (Self 5 + Enemy 10) → 4차원 출력
- **REINFORCE 알고리즘**: Policy Gradient 학습
- **GPU 자동 감지**: CUDA/MPS/CPU 자동 전환

**위치**: `wicked_zerg_challenger/zerg_net.py`

### 3. 학습 파이프라인

**실제 구현된 기능**:
- Replay 파일 자동 처리
- PyTorch 모델 학습
- 학습 진행 추적
- 자동 정리 및 아카이브

**위치**: `wicked_zerg_challenger/tools/integrated_pipeline.py`

---

## ? 프로젝트 구조

```
Swarm-contol-in-sc2bot/
├── main.py                          # ? 메인 진입점 (git clone 후 바로 실행)
├── src/                             # 새 구조 (모듈화)
│   ├── bot/                        # 봇 로직
│   ├── sc2_env/                    # SC2 환경 (Mock 포함)
│   ├── self_healing/               # 자가 수복 시스템
│   └── utils/                      # 유틸리티
├── wicked_zerg_challenger/          # 기존 구조 (실제 실행 가능)
│   ├── wicked_zerg_bot_pro.py      # 메인 봇 (6,364줄)
│   ├── zerg_net.py                 # 신경망 모델
│   ├── micro_controller.py          # ? 군집 제어 알고리즘
│   ├── run.py                      # 실행 진입점
│   ├── tools/
│   │   ├── integrated_pipeline.py  # 학습 파이프라인
│   │   └── clean_duplicates.py     # 유지보수 스크립트
│   └── local_training/             # 학습 관련
├── scripts/                        # 실행 스크립트
│   └── run_mock_battle.py          # Mock Battle
└── tests/                           # 테스트
```

---

## ? 문제 해결

### 문제: `ModuleNotFoundError: No module named 'src'`

**해결**:
```bash
# 프로젝트 루트에서 실행
cd /path/to/Swarm-contol-in-sc2bot
python main.py
```

### 문제: `ModuleNotFoundError: No module named 'sc2'`

**해결**:
```bash
pip install sc2
```

### 문제: SC2 경로를 찾을 수 없음

**해결**:
```bash
# Windows: 환경 변수 설정
set SC2PATH=C:\Program Files (x86)\StarCraft II

# 또는 run.py가 자동으로 찾습니다
```

---

## ? 추가 문서

- `README.md`: 프로젝트 개요
- `README_NEW_STRUCTURE.md`: 새 구조 설명
- `QUICK_START.md`: 빠른 시작 가이드
- `wicked_zerg_challenger/README.md`: 봇 상세 문서

---

## ? 검증

### 로컬 테스트

```bash
# 1. Mock Battle 테스트
python scripts/run_mock_battle.py

# 2. Import 테스트
python test_import.py

# 3. pytest 테스트
pytest tests/ -v
```

### CI/CD 테스트

GitHub Actions에서 자동으로:
- Black 포맷 체크
- flake8 린트
- mypy 타입 체크
- pytest 실행
- Import 테스트

---

## ? 다음 단계

1. **Mock Battle 실행**: `python main.py --quick-start`
2. **학습 파이프라인 실행**: `python main.py` → 옵션 3
3. **실제 SC2 게임 실행**: `python main.py` → 옵션 1
4. **프로젝트 정리**: `python main.py` → 옵션 4

---

**? 이제 저장소가 완전히 실행 가능한 상태입니다!**
