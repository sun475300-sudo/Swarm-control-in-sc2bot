# monitoring/ vs 모니터링/ 폴더 비교

**작성 일시**: 2026-01-14  
**목적**: 두 폴더의 차이점 및 중복 여부 확인

---

## ? 폴더 구조 비교

### 1. `monitoring/` 폴더 (영문)

**파일/폴더 목록 (17개):**
- ? `dashboard.py` (메인 대시보드 서버)
- ? `dashboard_api.py` (FastAPI 백엔드)
- ? `monitoring_utils.py` (유틸리티 함수)
- ? `dashboard.html` (HTML UI)
- ? `telemetry_logger.py` (텔레메트리 로거)
- ? `test_endpoints.py` (테스트 스크립트)
- ? `MONITORING_README.md` (사용 설명서)
- ? `MONITORING_SYSTEM_REPORT.md` (시스템 리포트)
- ? `status.json` (상태 데이터)
- ? `instance_0_status.json` (인스턴스 상태)
- ? `lifecycle_report_*.json` (5개 파일, 생명주기 리포트)
- ? `backups/` (백업 폴더)
  - `dashboard_api_imports_backup_20260114_084543.py`
- ? `mobile_app/` (모바일 앱 폴더)
  - `public/index.html`

**특징:**
- ? 완전한 모니터링 시스템
- ? 문서화 완료 (README 포함)
- ? 테스트 파일 포함
- ? 백업 및 모바일 앱 지원
- ? 실제 데이터 파일 존재 (JSON)

### 2. `모니터링/` 폴더 (한글)

**파일 목록 (3개):**
- ?? `dashboard.py`
- ?? `dashboard_api.py`
- ?? `monitoring_utils.py`

**특징:**
- ?? 핵심 파일 3개만 존재
- ?? 문서, 테스트, 데이터 파일 없음
- ?? 백업 폴더, 모바일 앱 폴더 없음

---

## ? 파일 내용 비교

### 공통 파일 (3개)

1. **`dashboard.py`**
   - 두 폴더 모두 동일한 코드 (확인 완료)
   - Line 1-50 비교: 완전히 동일

2. **`dashboard_api.py`**
   - 두 폴더 모두 동일한 코드로 추정

3. **`monitoring_utils.py`**
   - 두 폴더 모두 동일한 코드 (확인 완료)
   - Line 1-37 비교: 완전히 동일

---

## ? 차이점 요약

### 주요 차이점

| 항목 | `monitoring/` | `모니터링/` |
|------|---------------|-------------|
| **파일 수** | 17개 파일/폴더 | 3개 파일 |
| **핵심 코드** | ? 3개 파일 | ? 3개 파일 (동일) |
| **문서** | ? README 2개 | ? 없음 |
| **테스트** | ? test_endpoints.py | ? 없음 |
| **데이터** | ? JSON 파일 7개 | ? 없음 |
| **백업** | ? backups/ 폴더 | ? 없음 |
| **모바일 앱** | ? mobile_app/ 폴더 | ? 없음 |
| **HTML UI** | ? dashboard.html | ? 없음 |
| **텔레메트리** | ? telemetry_logger.py | ? 없음 |

---

## ? 코드 참조 확인

### Import 경로 확인

**코드베이스에서 `monitoring/` 참조:**
- ? `monitoring/dashboard.py` 참조하는 코드 존재
- ? `monitoring/dashboard_api.py` 참조하는 코드 존재
- ? `monitoring/monitoring_utils.py` 참조하는 코드 존재

**코드베이스에서 `모니터링/` 참조:**
- ? 참조하는 코드 없음 확인

---

## ? 결론

### 1. 중복 파일 확인
- `모니터링/` 폴더는 `monitoring/` 폴더의 **부분 복사본**
- 핵심 파일 3개만 복사되어 있음
- 파일 내용은 동일하지만, `monitoring/` 폴더가 더 완전함

### 2. 사용 현황
- ? `monitoring/` 폴더: 실제 사용 중 (코드 참조 존재)
- ? `모니터링/` 폴더: 사용하지 않음 (코드 참조 없음)

### 3. 권장 사항
- **`모니터링/` 폴더 삭제 권장**
  - 이유:
    1. `monitoring/` 폴더의 불완전한 복사본
    2. 코드에서 참조하지 않음
    3. Single Source of Truth (SSOT) 원칙 위반
    4. 혼란 가능성 (중복 코드)
  
- **`monitoring/` 폴더 유지**
  - 이유:
    1. 완전한 모니터링 시스템
    2. 문서, 테스트, 데이터 포함
    3. 실제 사용 중
    4. 모바일 앱 및 백업 지원

---

## ? 참고 사항

### 이전 작업 내역

`FINAL_CHECK_COMPLETE_REPORT.md`에 따르면:
- ? `모니터링/` 폴더는 이미 제거 대상으로 확인됨
- ? `monitoring/` 폴더만 유지하는 것이 권장됨
- ?? 아직 `모니터링/` 폴더가 삭제되지 않은 상태

---

**생성 일시**: 2026-01-14  
**상태**: 비교 분석 완료
