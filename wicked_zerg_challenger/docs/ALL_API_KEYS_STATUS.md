# ? 모든 API 키 상태 확인

**작성일**: 2026-01-14  
**목적**: 프로젝트에서 사용되는 모든 API 키의 현재 상태 확인

---

## ? 프로젝트에서 사용되는 API 키 목록

### ? 필수 키 (Required)

#### 1. GEMINI_API_KEY
**용도**: Gemini Self-Healing, Build-Order Gap Analyzer, Android 앱

**현재 상태**:
- ? **환경 변수에 설정됨**
- 키 값: `AIzaSyC_Ci...MIIo`
- ?? **노출 가능성 있음 - 교체 필요**

**파일 위치**:
- ? `secrets/gemini_api.txt` - 파일 없음
- ? `api_keys/GEMINI_API_KEY.txt` - 파일 없음
- ? `.env` 파일 - 파일 없음

**사용 위치**:
- `genai_self_healing.py`
- `local_training/strategy_audit.py`
- `wicked_zerg_bot_pro.py`

---

#### 2. GOOGLE_API_KEY
**용도**: Gemini Self-Healing (GEMINI_API_KEY와 동일 키 사용 가능)

**현재 상태**:
- ? 환경 변수 없음
- ? 파일 없음
- ?? GEMINI_API_KEY와 동일한 키 사용 가능

**파일 위치**:
- ? `secrets/gemini_api.txt` - 파일 없음 (GEMINI_API_KEY와 공유)
- ? `api_keys/GOOGLE_API_KEY.txt` - 파일 없음

**사용 위치**:
- `genai_self_healing.py`
- `wicked_zerg_bot_pro.py`

---

### ? 선택적 키 (Optional)

#### 3. AIARENA_TOKEN
**용도**: AI Arena 플랫폼에 봇 업로드

**현재 상태**:
- ? 환경 변수 없음
- ? 파일 없음

**파일 위치**:
- ? `secrets/aiarena_token.txt` - 파일 없음
- ? `api_keys/AIARENA_TOKEN.txt` - 파일 없음

**사용 위치**:
- `tools/upload_to_aiarena.py`

**발급 링크**: https://aiarena.net/profile/token/

**필요 여부**: AI Arena에 업로드할 때만 필요

---

#### 4. GCP_PROJECT_ID
**용도**: Google Cloud Platform 프로젝트 ID (Vertex AI 사용 시)

**현재 상태**:
- ? **환경 변수에 설정됨**
- 키 값: `gen-lang-client-0209357933`
- ?? 프로젝트 ID (민감 정보 아님, 공개 가능)

**파일 위치**:
- ? `secrets/gcp_project_id.txt` - 파일 없음
- ? `api_keys/GCP_PROJECT_ID.txt` - 파일 없음

**사용 위치**:
- Vertex AI 통합 (향후 확장)

---

#### 7. GCP_LOCATION
**용도**: Google Cloud Platform 리전 설정

**현재 상태**:
- ? **환경 변수에 설정됨**
- 값: `us-central1`
- ?? 리전 설정 (민감 정보 아님)

**필요 여부**: Vertex AI 사용 시에만 필요

**파일 위치**:
- ? `secrets/gcp_project_id.txt` - 파일 없음
- ? `api_keys/GCP_PROJECT_ID.txt` - 파일 없음

**사용 위치**:
- Vertex AI 통합 (향후 확장)

**발급 링크**: https://console.cloud.google.com

**필요 여부**: Vertex AI 사용 시에만 필요

---

#### 5. GCP_CREDENTIALS.json
**용도**: Google Cloud Platform 서비스 계정 인증

**현재 상태**:
- ? 파일 없음

**파일 위치**:
- ? `secrets/gcp_credentials.json` - 파일 없음
- ? `api_keys/GCP_CREDENTIALS.json` - 파일 없음

**사용 위치**:
- Vertex AI 통합 (향후 확장)

**발급 링크**: https://console.cloud.google.com/iam-admin/serviceaccounts

**필요 여부**: Vertex AI 사용 시에만 필요

---

#### 6. NGROK_AUTH_TOKEN
**용도**: Ngrok 외부 접속 인증 토큰

**현재 상태**:
- ? 환경 변수 없음
- ? 파일 없음

**파일 위치**:
- ? `secrets/ngrok_auth.txt` - 파일 없음
- ? `api_keys/NGROK_AUTH_TOKEN.txt` - 파일 없음

**사용 위치**:
- 외부 접속이 필요한 경우 (선택적)

**발급 링크**: https://dashboard.ngrok.com/get-started/your-authtoken

**필요 여부**: 외부 접속이 필요할 때만 사용

---

## ? 전체 키 상태 요약

| 키 이름 | 필수 여부 | 현재 상태 | 위치 | 교체 필요 |
|---------|----------|----------|------|----------|
| **GEMINI_API_KEY** | ? 필수 | ? 환경 변수 | `$env:GEMINI_API_KEY` | ?? **예** (노출 가능성) |
| **GOOGLE_API_KEY** | ? 필수 | ? 없음 | - | ?? GEMINI_API_KEY와 동일 가능 |
| **GCP_PROJECT_ID** | 선택적 | ? 환경 변수 | `$env:GCP_PROJECT_ID` | - |
| **GCP_LOCATION** | 선택적 | ? 환경 변수 | `$env:GCP_LOCATION` | - |
| **AIARENA_TOKEN** | 선택적 | ? 없음 | - | - |
| **GCP_CREDENTIALS.json** | 선택적 | ? 없음 | - | - |
| **NGROK_AUTH_TOKEN** | 선택적 | ? 없음 | - | - |

---

## ? 키 확인 방법

### 환경 변수 확인

```powershell
# 모든 API 관련 환경 변수 확인
Get-ChildItem Env: | Where-Object { $_.Name -match "KEY|TOKEN|CREDENTIAL|API" } | Format-Table Name, Value -AutoSize
```

### 파일 확인

```powershell
# secrets/ 폴더 확인
Get-ChildItem secrets -File

# api_keys/ 폴더 확인
Get-ChildItem api_keys -File | Where-Object { $_.Name -notmatch "\.example|README" }
```

### Python으로 확인

```python
from tools.load_api_key import get_gemini_api_key, get_google_api_key

# GEMINI_API_KEY 확인
gemini_key = get_gemini_api_key()
print(f"GEMINI_API_KEY: {gemini_key[:10]}..." if gemini_key else "GEMINI_API_KEY: Not found")

# GOOGLE_API_KEY 확인
google_key = get_google_api_key()
print(f"GOOGLE_API_KEY: {google_key[:10]}..." if google_key else "GOOGLE_API_KEY: Not found")
```

---

## ?? 즉시 조치 필요

### GEMINI_API_KEY 교체

현재 환경 변수에 설정된 키는 노출 가능성이 있으므로 **즉시 교체**가 필요합니다:

1. **Google AI Studio에서 기존 키 삭제**
   - https://makersuite.google.com/app/apikey
   - 키: `AIzaSyC_Ci...MIIo` 삭제

2. **새 키 발급 및 적용**
   ```powershell
   # 새 키를 secrets/ 폴더에 저장
   echo "YOUR_NEW_API_KEY" > secrets\gemini_api.txt
   ```

3. **환경 변수에서 기존 키 제거**
   ```powershell
   Remove-Item Env:\GEMINI_API_KEY
   ```

---

## ? 키 설정 가이드

### 필수 키 설정

```powershell
# 1. GEMINI_API_KEY 설정
echo "YOUR_GEMINI_API_KEY" > secrets\gemini_api.txt

# 2. GOOGLE_API_KEY 설정 (GEMINI_API_KEY와 동일 가능)
# secrets/gemini_api.txt 파일을 공유하거나 별도 파일 생성
echo "YOUR_GOOGLE_API_KEY" > secrets\google_api.txt
```

### 선택적 키 설정

```powershell
# AIARENA_TOKEN (AI Arena 업로드 시)
echo "YOUR_AIARENA_TOKEN" > secrets\aiarena_token.txt

# NGROK_AUTH_TOKEN (외부 접속 시)
echo "YOUR_NGROK_TOKEN" > secrets\ngrok_auth.txt

# GCP_PROJECT_ID (Vertex AI 사용 시)
echo "YOUR_GCP_PROJECT_ID" > secrets\gcp_project_id.txt
```

---

## ? 보안 확인

### .gitignore 확인

다음이 `.gitignore`에 포함되어 있는지 확인:

```gitignore
secrets/
!secrets/.gitkeep
!secrets/README.md
api_keys/*.txt
!api_keys/*.example
.env
```

### Git에서 키 검색

```bash
# Git 히스토리에서 키 검색
git log -p --all -S "AIzaSy" --source --all
```

---

## ? 관련 문서

- **API 키 교체 가이드**: `docs/API_KEY_ROTATION_GUIDE.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`
- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`

---

**마지막 업데이트**: 2026-01-14
