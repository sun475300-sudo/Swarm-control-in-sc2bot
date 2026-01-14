# ? 프로젝트 필수 API 키 목록

**작성일**: 2026-01-14  
**목적**: 프로젝트 실행에 필요한 모든 API 키 정리

---

## ? 필수 API 키 (Required)

### 1. ? GEMINI_API_KEY (필수)

**용도**:
- Gemini Self-Healing 시스템 (자동 에러 수정)
- Build-Order Gap Analyzer (Gemini 피드백 생성)
- Android 모바일 앱 (Gemini AI 기능)

**사용 위치**:
- `genai_self_healing.py` - Self-Healing 시스템
- `local_training/strategy_audit.py` - Gap Analyzer
- `monitoring/mobile_app_android/` - Android 앱

**발급 링크**: https://makersuite.google.com/app/apikey

**파일 위치**: `api_keys/GEMINI_API_KEY.txt`

**환경 변수**: `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`

---

### 2. ? GOOGLE_API_KEY (필수 - GEMINI_API_KEY와 동일 가능)

**용도**:
- Gemini Self-Healing 시스템 (GEMINI_API_KEY와 동일한 키 사용 가능)
- Google API 서비스

**사용 위치**:
- `genai_self_healing.py` - Self-Healing 시스템
- `wicked_zerg_bot_pro.py` - 봇 초기화 시

**발급 링크**: https://makersuite.google.com/app/apikey

**파일 위치**: `api_keys/GOOGLE_API_KEY.txt`

**환경 변수**: `GOOGLE_API_KEY`

**참고**: GEMINI_API_KEY와 동일한 키를 사용해도 됩니다.

---

## ? 선택적 API 키 (Optional)

### 3. ? GCP_PROJECT_ID (선택적)

**용도**:
- Google Cloud Platform 서비스 사용 시
- Vertex AI 사용 시

**사용 위치**:
- Vertex AI 통합 (향후 확장)

**발급 링크**: https://console.cloud.google.com

**파일 위치**: `api_keys/GCP_PROJECT_ID.txt`

**환경 변수**: `GCP_PROJECT_ID`

**필요 여부**: Vertex AI를 사용하지 않으면 불필요

---

### 4. ? GCP_CREDENTIALS.json (선택적)

**용도**:
- Vertex AI 서비스 계정 인증
- Google Cloud Platform 서비스 인증

**사용 위치**:
- Vertex AI 통합 (향후 확장)

**발급 링크**: https://console.cloud.google.com/iam-admin/serviceaccounts

**파일 위치**: `api_keys/GCP_CREDENTIALS.json`

**환경 변수**: `GOOGLE_APPLICATION_CREDENTIALS` (파일 경로)

**필요 여부**: Vertex AI를 사용하지 않으면 불필요

---

## ? 우선순위 요약

| 우선순위 | API 키 이름 | 필수 여부 | 용도 | 발급 링크 |
|---------|------------|----------|------|-----------|
| ? **1순위** | `GEMINI_API_KEY` | **필수** | Gemini Self-Healing, Gap Analyzer | https://makersuite.google.com/app/apikey |
| ? **2순위** | `GOOGLE_API_KEY` | **필수** | Gemini Self-Healing (동일 키 가능) | https://makersuite.google.com/app/apikey |
| ? **3순위** | `GCP_PROJECT_ID` | 선택적 | Vertex AI (향후 확장) | https://console.cloud.google.com |
| ? **4순위** | `GCP_CREDENTIALS.json` | 선택적 | Vertex AI 인증 (향후 확장) | https://console.cloud.google.com/iam-admin/serviceaccounts |

---

## ? 빠른 설정 가이드

### 최소 설정 (필수만)

```powershell
# 1. API 키 파일 생성
cd api_keys
copy GEMINI_API_KEY.txt.example GEMINI_API_KEY.txt
copy GOOGLE_API_KEY.txt.example GOOGLE_API_KEY.txt

# 2. 실제 키 입력
# GEMINI_API_KEY.txt 파일을 열고 실제 키 입력
# GOOGLE_API_KEY.txt 파일을 열고 실제 키 입력 (GEMINI_API_KEY와 동일 가능)
```

### 완전 설정 (모든 기능 사용)

```powershell
# 위의 최소 설정 +
copy API_KEYS.md.example API_KEYS.md
# API_KEYS.md 파일에 모든 키 입력
```

---

## ? 체크리스트

### 필수 키
- [ ] `GEMINI_API_KEY.txt` 생성 및 키 입력
- [ ] `GOOGLE_API_KEY.txt` 생성 및 키 입력 (GEMINI_API_KEY와 동일 가능)

### 선택적 키 (Vertex AI 사용 시)
- [ ] `GCP_PROJECT_ID.txt` 생성 및 프로젝트 ID 입력
- [ ] `GCP_CREDENTIALS.json` 생성 및 서비스 계정 키 입력

---

## ? 키 사용 확인

### Python 코드에서 확인

```python
from tools.load_api_key import get_gemini_api_key, get_google_api_key

# 키 로드 확인
gemini_key = get_gemini_api_key()
google_key = get_google_api_key()

if gemini_key:
    print(f"? GEMINI_API_KEY: {gemini_key[:10]}... (loaded)")
else:
    print("? GEMINI_API_KEY: Not found")

if google_key:
    print(f"? GOOGLE_API_KEY: {google_key[:10]}... (loaded)")
else:
    print("? GOOGLE_API_KEY: Not found")
```

### 테스트 스크립트 실행

```bash
python tools/load_api_key.py
```

---

## ? 발급 방법

### Gemini API 키 발급

1. https://makersuite.google.com/app/apikey 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. 프로젝트 선택 (또는 새로 생성)
5. API 키 복사
6. `api_keys/GEMINI_API_KEY.txt` 파일에 저장

**참고**: GEMINI_API_KEY와 GOOGLE_API_KEY는 동일한 키를 사용할 수 있습니다.

### GCP 프로젝트 ID 확인 (선택적)

1. https://console.cloud.google.com 접속
2. 프로젝트 선택
3. 프로젝트 ID 확인 (상단에 표시)
4. `api_keys/GCP_PROJECT_ID.txt` 파일에 저장

### GCP 서비스 계정 키 발급 (선택적)

1. https://console.cloud.google.com/iam-admin/serviceaccounts 접속
2. 서비스 계정 생성 또는 선택
3. "키" 탭 > "키 추가" > "JSON 만들기"
4. 다운로드한 JSON 파일을 `api_keys/GCP_CREDENTIALS.json`으로 저장

---

## ? 보안 주의사항

1. **절대 Git에 커밋하지 마세요!**
   - `.gitignore`에 `api_keys/` 폴더가 이미 추가되어 있습니다
   - 실수로 커밋했다면 즉시 키를 재생성하세요

2. **파일 권한 설정** (Linux/Mac):
   ```bash
   chmod 600 api_keys/*.txt
   chmod 600 api_keys/*.json
   ```

3. **키 공유 금지**:
   - API 키는 개인용으로만 사용하세요
   - 팀 공유가 필요하면 환경 변수나 보안 저장소 사용

---

## ? 문제 해결

### 키가 작동하지 않을 때

1. **파일 경로 확인**: `api_keys/` 폴더에 파일이 있는지 확인
2. **파일 형식 확인**: 키만 입력되어 있는지 확인 (줄바꿈, 공백 제거)
3. **인코딩 확인**: UTF-8로 저장되어 있는지 확인
4. **환경 변수 확인**: 환경 변수로도 설정 가능

### Git에 실수로 커밋했을 때

1. **즉시 키 재생성** (가장 중요!)
2. **Git에서 제거**:
   ```bash
   git rm --cached api_keys/GEMINI_API_KEY.txt
   git commit -m "Remove API keys from tracking"
   ```

---

## ? 관련 문서

- **API 키 관리 가이드**: `api_keys/README.md`
- **상세 관리 가이드**: `docs/API_KEYS_MANAGEMENT.md`
- **빠른 설정**: `api_keys/SETUP_INSTRUCTIONS.md`

---

**마지막 업데이트**: 2026-01-14
