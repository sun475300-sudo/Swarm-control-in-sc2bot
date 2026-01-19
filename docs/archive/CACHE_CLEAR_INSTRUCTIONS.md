# Python 캐시 정리 가이드

**작성일**: 2026-01-15  
**목적**: Python 캐시로 인한 오류 해결

---

## ? 문제

코드를 수정했지만 여전히 오래된 코드가 실행되는 경우, Python 캐시(`__pycache__`, `.pyc` 파일) 문제일 수 있습니다.

---

## ? 해결 방법

### 방법 1: Batch 스크립트 사용 (권장)

```bash
cd wicked_zerg_challenger
.\bat\clear_python_cache.bat
```

### 방법 2: 수동 정리

**Windows (CMD)**:
```cmd
cd wicked_zerg_challenger
for /d /r . %d in (__pycache__) do @if exist "%d" rmdir /s /q "%d"
for /r . %f in (*.pyc) do @if exist "%f" del /q "%f"
for /r . %f in (*.pyo) do @if exist "%f" del /q "%f"
```

**Windows (PowerShell)**:
```powershell
cd wicked_zerg_challenger
Get-ChildItem -Path . -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force
Get-ChildItem -Path . -Recurse -Filter "*.pyo" | Remove-Item -Force
```

---

## ? 확인 사항

캐시 정리 후 다음을 확인하세요:

1. **코드 수정 확인**:
   - `production_manager.py`에서 `vespene_gas`가 모두 `vespene`으로 변경되었는지
   - 모든 `await train()` 호출이 `_safe_train()`으로 변경되었는지

2. **게임 재실행**:
   - 게임을 종료하고 다시 시작
   - 오류 메시지가 사라졌는지 확인

---

**참고**: Python은 실행 시 `.pyc` 파일을 자동으로 생성합니다. 캐시를 정리하면 다음 실행 시 최신 코드가 사용됩니다.
