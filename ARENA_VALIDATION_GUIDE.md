# AI Arena Validation 가이드

**작성일**: 2026-01-15  
**목적**: AI Arena 서버에서 봇이 정상적으로 시작되는지 검증

---

## ? Validation 과정 개요

AI Arena는 봇을 제출한 후 **Validation** 과정을 거칩니다. 이 과정에서:

1. ? 봇이 서버에서 정상적으로 시작되는지 확인
2. ? 필요한 모든 모듈이 import되는지 확인
3. ? 초기화 과정에서 에러가 없는지 확인
4. ? `run.py`가 올바르게 실행되는지 확인

---

## ? 로컬 Validation 실행

### 자동 검증 스크립트

```bash
cd wicked_zerg_challenger
python tools/validate_arena_deployment.py
```

이 스크립트는 다음을 확인합니다:

1. **Import 검증**: 모든 필수 모듈이 import 가능한지
2. **run.py 검증**: 진입점 파일이 올바른지
3. **Bot 인스턴스화**: 봇이 정상적으로 생성되는지
4. **경로 검증**: 절대 경로 사용 여부 확인
5. **requirements.txt**: 필수 패키지 포함 여부
6. **파일 구조**: 필수 파일 존재 여부
7. **서버 시뮬레이션**: AI Arena 서버 시작 시뮬레이션

---

## ? Validation 체크리스트

### 1. 필수 Import 확인

다음 모듈들이 정상적으로 import되어야 합니다:

- ? `sc2` (burnysc2) - SC2 API
- ? `wicked_zerg_bot_pro` - 봇 메인 클래스
- ? `config` - 설정 파일
- ? `numpy` - 수치 연산
- ?? `torch` - 선택적 (Neural Network 사용 시)
- ?? `zerg_net` - 선택적 (Neural Network 사용 시)

### 2. run.py 검증

- ? `run.py` 파일 존재
- ? `main()` 함수 정의
- ? `if __name__ == "__main__"` 블록
- ? `--LadderServer` 플래그 처리
- ? `run_ladder_game()` 호출

### 3. Bot 인스턴스화

- ? `WickedZergBotPro()` 생성 성공
- ? `Bot(Race.Zerg, WickedZergBotPro())` 래퍼 생성 성공
- ? 초기화 과정에서 에러 없음

### 4. 경로 검증

- ? 절대 Windows 경로 (`D:/`, `C:/`) 사용 안 함
- ? 상대 경로만 사용 (`./models/`, `SCRIPT_DIR / "models"`)
- ?? 로그 파일 경로는 상대 경로 사용

### 5. requirements.txt

- ? `burnysc2>=5.0.12` 포함
- ? `torch>=2.0.0` 포함
- ? `numpy` 포함 (버전 제약 포함)
- ? `protobuf<=3.20.3` 포함

### 6. 파일 구조

- ? `run.py` - 진입점
- ? `wicked_zerg_bot_pro.py` - 봇 메인 클래스
- ? `config.py` - 설정
- ? `zerg_net.py` - Neural Network
- ? `requirements.txt` - 의존성
- ?? `models/zerg_net_model.pt` - 선택적 (학습된 모델)

---

## ? 일반적인 Validation 실패 원인

### 1. Import 에러

**증상**: `ModuleNotFoundError`

**원인**:
- `requirements.txt`에 패키지 누락
- 패키지 이름 오타
- 버전 호환성 문제

**해결**:
```bash
# requirements.txt 확인
cat requirements.txt

# 로컬에서 테스트
pip install -r requirements.txt
python -c "from wicked_zerg_bot_pro import WickedZergBotPro"
```

### 2. 경로 에러

**증상**: `FileNotFoundError` 또는 `PermissionError`

**원인**:
- 절대 Windows 경로 사용 (`D:/replays`)
- 존재하지 않는 디렉토리 참조

**해결**:
- 모든 경로를 상대 경로로 변경
- `Path(__file__).parent` 사용
- `os.path.dirname(os.path.abspath(__file__))` 사용

### 3. 초기화 에러

**증상**: Bot 생성 시 에러

**원인**:
- 필수 파일 누락
- 모델 파일 로드 실패
- 설정 파일 오류

**해결**:
- 모든 필수 파일이 패키지에 포함되었는지 확인
- 모델 파일이 선택적이도록 코드 수정
- 설정값에 기본값 제공

### 4. run.py 실행 에러

**증상**: `run.py` 실행 시 에러

**원인**:
- `--LadderServer` 플래그 처리 누락
- `run_ladder_game()` 호출 누락
- sys.path 설정 오류

**해결**:
- `run.py` 구조 확인
- 로컬에서 `python run.py --LadderServer` 테스트

---

## ? 수동 검증 방법

### 1. Import 테스트

```python
# Python 인터프리터에서 실행
python
>>> from wicked_zerg_bot_pro import WickedZergBotPro
>>> from zerg_net import ZergNet
>>> from config import Config
>>> import torch
>>> import numpy as np
```

### 2. Bot 생성 테스트

```python
python
>>> from wicked_zerg_bot_pro import WickedZergBotPro
>>> from sc2.player import Bot
>>> from sc2.data import Race
>>> bot_ai = WickedZergBotPro(train_mode=False)
>>> bot = Bot(Race.Zerg, bot_ai)
```

### 3. run.py 시뮬레이션

```bash
# --LadderServer 플래그로 실행 (실제 연결 없이)
python run.py --LadderServer
```

---

## ? Validation 결과 해석

### ? 성공

```
? ALL CHECKS PASSED - Ready for AI Arena deployment!
```

**의미**: 모든 검증 통과, AI Arena에 제출 가능

### ?? 경고

```
? ALL CHECKS PASSED (with warnings)
??  Warnings:
   - Absolute Windows paths found in some files
```

**의미**: 기본 검증 통과, 경고 사항 확인 필요

### ? 실패

```
? VALIDATION FAILED
? Errors:
   - ModuleNotFoundError: No module named 'xxx'
```

**의미**: 수정 필요, 에러 해결 후 재검증

---

## ? Validation 통과 후 다음 단계

1. **패키징**: `package_for_aiarena_clean.py` 실행
2. **최종 검증**: 생성된 ZIP 파일 확인
3. **제출**: AI Arena에 ZIP 파일 업로드
4. **서버 Validation 대기**: AI Arena 서버에서 자동 검증

---

## ? 팁

1. **로컬에서 먼저 검증**: 서버에 제출하기 전에 로컬에서 모든 검증 통과
2. **에러 로그 확인**: Validation 실패 시 에러 메시지 자세히 확인
3. **점진적 수정**: 한 번에 하나씩 문제 해결
4. **백업**: 검증 통과한 버전은 백업 보관

---

**Validation 준비 상태**: ? **검증 스크립트 준비 완료**
