# ? 실행 빠른 참조 가이드

**작성일**: 2026-01-14  
**목적**: 가장 빠르게 프로젝트를 실행하는 방법

---

## ? 빠른 시작

### 가장 간단한 방법

```bash
# 1. 프로젝트 디렉토리로 이동
cd wicked_zerg_challenger

# 2. 게임 실행
python run.py
```

---

## ? 실행 방법별 가이드

### 방법 1: 간단한 로컬 게임 (가장 빠름)

```bash
python run.py
```

**실행 내용**:
- SC2 경로 자동 탐지
- 봇 인스턴스 생성
- 로컬 게임 시작 (Terran VeryHard vs Zerg Bot)

---

### 방법 2: 완전한 실행 스크립트

```bash
# Python 스크립트 직접 실행
python COMPLETE_RUN_SCRIPT.py

# 또는 배치 파일 실행
bat\complete_run.bat
```

**실행 내용**:
1. 시스템 초기화 (SC2 경로, 로깅, PyTorch)
2. 봇 초기화 (모든 매니저 확인)
3. 게임 실행
4. 대시보드 서버 (선택적)

---

### 방법 3: 통합 학습 실행

```bash
cd local_training
python main_integrated.py
```

**실행 내용**:
- 전체 학습 파이프라인
- Curriculum Manager 통합
- Neural Network 학습

---

### 방법 4: 전체 학습 파이프라인

```bash
bat\start_full_training.bat
```

**실행 내용**:
1. 리플레이 추출
2. 리플레이 학습
3. 게임 학습
4. 정리 및 커밋

---

### 방법 5: Manus 대시보드 통합

```bash
bat\start_with_manus.bat
```

**실행 내용**:
- 환경 변수 설정
- Manus 연결 테스트
- 봇 실행 (자동 데이터 전송)

---

### 방법 6: 대시보드 서버만 실행

```bash
cd monitoring
python dashboard_api.py
```

**접속**:
- 웹: `http://localhost:8000`
- Android: `http://10.0.2.2:8000`

---

## ? 실행 전 확인 사항

### 필수
- [ ] StarCraft II 설치됨
- [ ] Python 3.8+ 설치됨
- [ ] 필요한 패키지 설치됨 (`pip install -r requirements.txt`)

### 선택적
- [ ] PyTorch 설치됨 (Neural Network 사용 시)
- [ ] GPU 드라이버 설치됨 (GPU 사용 시)

---

## ? 실행 흐름 요약

```
시스템 초기화
    ↓
봇 초기화
    ↓
게임 시작 (on_start)
    ↓
게임 실행 (on_step - 매 프레임)
    ↓
게임 종료 (on_end)
```

---

## ? 문제 해결

### SC2 경로 오류
```bash
set SC2PATH=C:\Program Files (x86)\StarCraft II
```

### 모듈 임포트 오류
```bash
# 프로젝트 루트에서 실행
cd wicked_zerg_challenger
python run.py
```

### 대시보드 연결 실패
```bash
# 포트 확인
netstat -ano | findstr :8000

# 다른 포트 사용
python dashboard_api.py --port 8001
```

---

## ? 상세 문서

- **전체 실행 흐름**: `docs/COMPLETE_EXECUTION_FLOW.md`
- **대시보드 아키텍처**: `docs/DASHBOARD_MONITORING_SYSTEM_ARCHITECTURE.md`

---

**마지막 업데이트**: 2026-01-14
