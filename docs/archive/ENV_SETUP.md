# Environment Variables Setup Guide

## 환경 변수 설정 가이드

이 프로젝트는 API 키와 설정 값을 환경 변수로 관리합니다.

---

## ? 빠른 시작

### 1. 환경 변수 파일 생성

**Windows (PowerShell):**
```powershell
cd wicked_zerg_challenger
Copy-Item .env.example .env
```

**Linux/macOS:**
```bash
cd wicked_zerg_challenger
cp .env.example .env
```

### 2. API 키 설정

`.env` 파일을 편집하여 실제 API 키 값으로 변경하세요:

```bash
# 텍스트 에디터로 열기
# Windows: notepad .env
# Linux/Mac: nano .env
```

---

## ? 필요한 API 키

### 필수 키

#### 1. Google Gemini API Key
- **용도**: Gen-AI Self-Healing 시스템 (자동 오류 수정)
- **발급 위치**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **설정 방법**:
  ```env
  GEMINI_API_KEY=AIzaSy...
  ```

#### 2. Google API Key (선택사항)
- **용도**: Vertex AI 사용 시
- **발급 위치**: [Google Cloud Console](https://console.cloud.google.com/)
- **설정 방법**:
  ```env
  GOOGLE_API_KEY=AIzaSy...
  GCP_PROJECT_ID=your-project-id
  ```

### 선택적 키

#### 3. ngrok Auth Token
- **용도**: Mobile GCS 원격 접속 터널링
- **발급 위치**: [ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken)
- **설정 방법**:
  ```env
  NGROK_AUTH_TOKEN=2abc...
  ```

#### 4. Manus Dashboard API Key (선택사항)
- **용도**: 원격 대시보드 서비스
- **설정 방법**:
  ```env
  MANUS_DASHBOARD_API_KEY=your_key_here
  ```

---

## ? 보안 주의사항

### ? 해야 할 것
- `.env` 파일은 **절대 Git에 커밋하지 마세요**
- `.env.example`은 예시 파일이므로 커밋해도 됩니다
- 실제 API 키는 `.env` 파일에만 저장하세요

### ? 하지 말아야 할 것
- API 키를 코드에 하드코딩하지 마세요
- 공개 저장소에 `.env` 파일을 올리지 마세요
- `.env` 파일을 다른 사람과 공유하지 마세요

---

## ? 환경 변수 우선순위

코드에서 API 키를 로드할 때 다음 순서로 시도합니다:

1. **환경 변수** (최우선)
   ```bash
   export GEMINI_API_KEY=your_key
   ```

2. **.env 파일**
   ```
   GEMINI_API_KEY=your_key
   ```

3. **파일 시스템**
   - `secrets/gemini_api.txt`
   - `api_keys/GEMINI_API_KEY.txt`

4. **기본값** (없으면 빈 문자열)

---

## ? 환경 변수 로드 방법

### Python 코드에서 사용

```python
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수 읽기
gemini_key = os.getenv("GEMINI_API_KEY", "")
```

### 또는 프로젝트 유틸리티 사용

```python
from wicked_zerg_challenger.tools.load_api_key import load_api_key

# 자동으로 여러 위치에서 키를 찾습니다
gemini_key = load_api_key("GEMINI_API_KEY")
```

---

## ? 환경 변수 확인

### 설정 확인 스크립트

```bash
# Python으로 확인
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GEMINI_API_KEY', 'Not set'))"

# 또는 프로젝트 스크립트 사용
python wicked_zerg_challenger/tools/check_api_key.py
```

---

## ? 추가 리소스

- [API Keys Setup Guide](wicked_zerg_challenger/api_keys/SETUP_INSTRUCTIONS.md)
- [Security Best Practices](wicked_zerg_challenger/SECURITY_REVIEW.md)
- [Environment Variables Reference](.env.example)
