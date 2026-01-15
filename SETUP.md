# Setup Guide

## 빠른 설치 가이드

### 1. 시스템 요구사항

- **OS**: Windows 10+, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.10 이상
- **메모리**: 최소 8GB RAM (16GB 권장)
- **GPU**: 선택사항 (PyTorch GPU 지원 시 CUDA 11.8+)

### 2. StarCraft II 설치

1. [Battle.net](https://www.battle.net/download/)에서 Battle.net 설치
2. StarCraft II 게임 다운로드 및 설치
3. 게임을 최소 한 번 실행하여 초기화

### 3. 프로젝트 설정

#### 자동 설치 (권장)

**Windows:**
```powershell
.\setup.ps1
```

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

#### 수동 설치

**1단계: 저장소 클론**
```bash
git clone https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git
cd Swarm-control-in-sc2bot
```

**2단계: 가상 환경 생성**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
```

**3단계: 의존성 설치**
```bash
cd wicked_zerg_challenger
pip install --upgrade pip
pip install -r requirements.txt
```

**4단계: 환경 변수 설정**
```bash
# Windows
copy api_keys\.env.example .env

# Linux/macOS
cp api_keys/.env.example .env
```

`.env` 파일을 편집하여 필요한 API 키를 설정하세요:
```
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

**5단계: 설정 확인**
```bash
python -c "import sc2; print('SC2 library OK')"
python -c "import torch; print('PyTorch OK')"
```

### 4. 첫 실행

```bash
# 기본 실행 (로컬 테스트)
python run.py

# 특정 맵에서 실행
python run.py --map "AbyssalReefLE"

# AI Arena 연결
python run.py --LadderServer <address> --GamePort <port> --StartPort <port>
```

## 문제 해결

### ImportError: No module named 'sc2'

```bash
pip install --upgrade burnysc2
```

### numpy 버전 충돌

```bash
pip install "numpy>=1.20.0,<2.0.0"
```

### protobuf 버전 충돌

```bash
pip install "protobuf<=3.20.3"
```

### Windows에서 PowerShell 실행 정책 오류

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 추가 리소스

- [문서 가이드](wicked_zerg_challenger/docs/)
- [아키텍처 설명](README.md#시스템-아키텍처)
- [문제 리포트](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot/issues)
