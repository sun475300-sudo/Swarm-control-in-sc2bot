# Copilot PR Review - Required Fixes

이 문서는 GitHub Copilot의 PR 검토 의견에 따라 필요한 수정사항을 정리합니다.

## ? 보안 이슈: 하드코딩된 API 키 제거

### 파일별 수정 사항

#### 1. `scan_git_history_for_sensitive_info.ps1` (PR에 포함 예정)
- **문제**: 하드코딩된 실제 API 키 (`AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM`) 포함
- **수정**: 패턴만 사용하도록 변경
```powershell
# 이전 (잘못됨)
$apiKeyPatterns = @(
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM",
)

# 수정 후 (올바름)
$apiKeyPatterns = @(
    "AIzaSy[A-Za-z0-9_-]{35}",  # Google API Key 패턴만 사용
)
```

#### 2. `double_check_before_commit.ps1` (PR에 포함 예정)
- **문제**: 하드코딩된 실제 API 키 포함
- **수정**: 실제 키 라인 제거
```powershell
# 이전 (잘못됨)
$apiKeyPatterns = @(
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM"   # 알려진 API 키
)

# 수정 후 (올바름)
$apiKeyPatterns = @(
    # 실제 키는 포함하지 않음, 패턴만 사용
)
```

#### 3. `remove_sensitive_files_from_git_history.ps1` (PR에 포함 예정)
- **문제**: Git 히스토리 정리 도구인데 하드코딩된 키 포함
- **수정**: 실제 키 라인 제거
```powershell
# 이전 (잘못됨)
$apiKeyPatterns = @(
    "AIzaSy[A-Za-z0-9_-]{35}",
    "AIzaSyBDdPWJyXs56AxeCPmqZpySFOVPjjSt_CM",
)

# 수정 후 (올바름)
$apiKeyPatterns = @(
    "AIzaSy[A-Za-z0-9_-]{35}",  # 패턴만 사용
)
```

#### 4. `pre_commit_security_check.ps1` ? (이미 수정 완료)
- **상태**: 하드코딩된 키 제거 완료
- **확인**: 실제 키 예시는 제외되고 패턴만 사용 중

## ? 코드 품질 개선

### 1. `telemetry_logger.py` - Atomic Write 구현 시 주의사항

#### A. Import 문 위치
- **문제**: `pathlib`, `tempfile`, `shutil` import가 메서드 내부에 있음
- **수정**: 파일 상단으로 이동
```python
# 파일 상단 (권장)
from pathlib import Path
import tempfile
import shutil

# 메서드 내부 (비권장)
async def save_telemetry(self):
    try:
        from pathlib import Path  # ? 매번 실행됨
```

#### B. Cleanup 오류 로깅
- **문제**: 임시 파일 cleanup 실패 시 무시됨
- **수정**: 경고 로깅 추가
```python
# 이전 (잘못됨)
except Exception:
    pass  # 오류가 숨겨짐

# 수정 후 (올바름)
except Exception as cleanup_error:
    print(f"[TELEMETRY] Warning: Failed to clean up temp file {temp_file}: {cleanup_error}")
```

#### C. ImportError Fallback 제거 또는 문서화
- **문제**: `pathlib`은 Python 3.4+ 표준 라이브러리인데 fallback이 있음
- **수정**: Python 버전 요구사항 명시 또는 fallback 제거
```python
# Python 3.4+ 사용 시 (권장)
# fallback 제거

# Python 2.7 지원 시
# requirements.txt 또는 README에 명시
```

### 2. `manus_dashboard_client.py` ? (이미 수정 완료)
- **문제**: ImportError에서 원본 예외 컨텍스트 손실
- **수정**: `raise ... from exc` 사용하여 예외 체이닝 유지
```python
# 이전 (잘못됨)
except ImportError:
    raise ImportError("...")

# 수정 후 (올바름)
except ImportError as exc:
    raise ImportError("...") from exc
```

## ? 체크리스트

PR에 포함될 파일들을 생성할 때 다음을 확인하세요:

- [ ] 하드코딩된 실제 API 키가 없음
- [ ] 패턴만 사용하여 검사
- [ ] Import 문이 파일 상단에 위치
- [ ] Exception 처리 시 적절한 로깅
- [ ] ImportError 시 원본 예외 컨텍스트 보존 (`from exc` 사용)
- [ ] Python 버전 요구사항 명시 (pathlib 등 사용 시)

## ? 참고

- [GitHub Copilot PR Review](https://github.com/sun475300-sudo/Swarm-control-in-sc2bot/pull/1)
- 보안 관련 패턴은 `pre_commit_security_check.ps1` 참조
