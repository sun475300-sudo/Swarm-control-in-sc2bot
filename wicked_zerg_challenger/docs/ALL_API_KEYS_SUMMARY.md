# ? 모든 API 키 요약

**작성일**: 2026-01-14  
**목적**: 프로젝트에서 사용되는 모든 API 키의 빠른 참조

---

## ? 현재 설정된 키

### 1. GEMINI_API_KEY (필수)
- **위치**: 환경 변수 (`$env:GEMINI_API_KEY`) 또는 `secrets/gemini_api.txt`
- **값**: `YOUR_API_KEY_HERE` (실제 키는 secrets/ 폴더에 저장)
- **상태**: ? 보안 설정 완료

### 2. GCP_PROJECT_ID (선택적)
- **위치**: 환경 변수 (`$env:GCP_PROJECT_ID`)
- **값**: `gen-lang-client-0209357933`
- **상태**: ? 설정됨 (민감 정보 아님)

### 3. GCP_LOCATION (선택적)
- **위치**: 환경 변수 (`$env:GCP_LOCATION`)
- **값**: `us-central1`
- **상태**: ? 설정됨 (민감 정보 아님)

---

## ? 설정되지 않은 키

### 4. GOOGLE_API_KEY (필수)
- **상태**: 없음
- **참고**: GEMINI_API_KEY와 동일한 키 사용 가능

### 5. AIARENA_TOKEN (선택적)
- **상태**: 없음
- **필요 시**: AI Arena 업로드 시에만 필요

### 6. NGROK_AUTH_TOKEN (선택적)
- **상태**: 없음
- **필요 시**: 외부 접속이 필요할 때만 사용

### 7. GCP_CREDENTIALS.json (선택적)
- **상태**: 없음
- **필요 시**: Vertex AI 사용 시에만 필요

---

## ? 즉시 조치 필요

### GEMINI_API_KEY 교체

1. **Google AI Studio에서 기존 키 삭제**
   - 키: `AIzaSyC_Ci...MIIo`
   - https://makersuite.google.com/app/apikey

2. **새 키 발급 및 적용**
   ```powershell
   echo "YOUR_NEW_API_KEY" > secrets\gemini_api.txt
   ```

3. **환경 변수에서 기존 키 제거**
   ```powershell
   Remove-Item Env:\GEMINI_API_KEY
   ```

---

## ? 전체 상태

| 키 이름 | 필수 여부 | 현재 상태 | 교체 필요 |
|---------|----------|----------|----------|
| GEMINI_API_KEY | ? 필수 | ? 설정됨 | ?? **예** |
| GOOGLE_API_KEY | ? 필수 | ? 없음 | - |
| GCP_PROJECT_ID | 선택적 | ? 설정됨 | - |
| GCP_LOCATION | 선택적 | ? 설정됨 | - |
| AIARENA_TOKEN | 선택적 | ? 없음 | - |
| NGROK_AUTH_TOKEN | 선택적 | ? 없음 | - |
| GCP_CREDENTIALS.json | 선택적 | ? 없음 | - |

---

## ? 관련 문서

- **상세 상태**: `docs/ALL_API_KEYS_STATUS.md`
- **키 교체 가이드**: `docs/API_KEY_ROTATION_GUIDE.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`

---

**마지막 업데이트**: 2026-01-14
