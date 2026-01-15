# BAT 파일 경로 수정 완료 보고서

**작성 일시**: 2026-01-15  
**상태**: ? **수정 완료**

---

## ? 경로 구조

```
D:\Swarm-contol-in-sc2bot\
└── wicked_zerg_challenger\
    ├── bat\                    ← 배치 파일 위치
    │   ├── extract_and_compare.bat
    │   ├── extract_and_train.bat
    │   ├── compare_pro_vs_training.bat
    │   └── start_model_training.bat
    ├── tools\
    │   ├── extract_and_train_from_training.py
    │   └── compare_pro_vs_training_replays.py
    └── run_with_training.py
```

---

## ? 수정된 파일들

### 1. `extract_and_compare.bat`
**변경 사항**:
- 경로 주석 추가: `%~dp0\..` = `wicked_zerg_challenger` 디렉토리
- 경로 변경: `%~dp0\..\..` → `%~dp0\..` (wicked_zerg_challenger로 이동)

**이유**: 
- `extract_and_train.bat`와 `compare_pro_vs_training.bat`가 `wicked_zerg_challenger` 디렉토리에서 실행되므로 일관성 유지

### 2. `extract_and_train.bat`
**변경 사항**:
- 경로 주석 추가
- 파일 존재 확인 추가: `extract_and_train_from_training.py` 확인
- 에러 처리 강화

### 3. `compare_pro_vs_training.bat`
**변경 사항**:
- 경로 주석 추가
- 파일 존재 확인 추가: `compare_pro_vs_training_replays.py` 확인
- 에러 처리 강화

### 4. `start_model_training.bat`
**변경 사항**:
- 경로 주석 추가
- 경로 변경: `%~dp0..` → `%~dp0\..` (일관성)
- 파일 존재 확인 추가: `run_with_training.py` 확인

---

## ? 경로 설명

### `%~dp0` 의미
- `%0`: 배치 파일의 전체 경로
- `%~dp0`: 배치 파일이 있는 디렉토리 경로 (끝에 `\` 포함)

### 예시
```
배치 파일: D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\extract_and_train.bat
%~dp0     = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\bat\
%~dp0\..  = D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\
```

---

## ? 검증 방법

각 배치 파일 실행 시:
1. 올바른 디렉토리로 이동하는지 확인
2. 필요한 Python 스크립트를 찾을 수 있는지 확인
3. 에러 발생 시 명확한 메시지 출력

---

## ? 참고사항

- 모든 배치 파일은 `wicked_zerg_challenger` 디렉토리에서 실행됩니다
- `PYTHONPATH`가 올바르게 설정되어 Python 모듈을 찾을 수 있습니다
- 파일 존재 확인으로 실행 전 오류를 방지합니다
