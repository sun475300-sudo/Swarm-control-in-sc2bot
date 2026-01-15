# Contributing to Swarm Control in SC2Bot

## 개발 환경 설정

### 필수 요구사항

- Python 3.10 이상
- StarCraft II 게임 (시뮬레이션 환경)
- Git

### 빠른 시작

#### Windows

```powershell
# 1. 저장소 클론
git clone https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git
cd Swarm-control-in-sc2bot

# 2. 가상 환경 생성
python -m venv .venv
.venv\Scripts\activate

# 3. 의존성 설치
cd wicked_zerg_challenger
pip install -r requirements.txt

# 4. 환경 변수 설정
copy api_keys\.env.example .env
# .env 파일을 편집하여 API 키 설정
```

#### Linux/macOS

```bash
# 1. 저장소 클론
git clone https://github.com/sun475300-sudo/Swarm-control-in-sc2bot.git
cd Swarm-control-in-sc2bot

# 2. 가상 환경 생성
python3 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
cd wicked_zerg_challenger
pip install -r requirements.txt

# 4. 환경 변수 설정
cp api_keys/.env.example .env
# .env 파일을 편집하여 API 키 설정
```

## 코드 스타일

- **Python**: PEP 8 준수
- **네이밍**: 
  - 함수/변수: `snake_case`
  - 클래스: `PascalCase`
  - 상수: `UPPER_SNAKE_CASE`

## 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/ -v

# 특정 테스트 파일 실행
python -m pytest tests/test_combat_manager.py -v
```

## Pull Request 가이드

1. Fork 저장소
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 커밋 메시지 규칙

- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 수정
- `test`: 테스트 추가/수정
- `refactor`: 코드 리팩토링
- `style`: 코드 포맷팅
- `chore`: 빌드/설정 관련

예: `feat: Add swarm formation algorithm`
