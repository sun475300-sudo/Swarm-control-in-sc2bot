# ? API Keys 관리 가이드

**작성일**: 2026-01-14  
**목표**: API 키를 안전하게 관리하고 Git에 올라가지 않도록 설정

---

## ? 폴더 구조

```
wicked_zerg_challenger/
└── api_keys/                    # API 키 저장 폴더 (Git 제외)
    ├── README.md               # 사용 가이드 (Git 포함)
    ├── .gitkeep                # 폴더 추적용 (Git 포함)
    ├── GEMINI_API_KEY.txt.example    # 예시 파일 (Git 포함)
    ├── GOOGLE_API_KEY.txt.example    # 예시 파일 (Git 포함)
    ├── API_KEYS.md.example           # 통합 예시 파일 (Git 포함)
    │
    ├── GEMINI_API_KEY.txt      # 실제 키 파일 (Git 제외 ??)
    ├── GOOGLE_API_KEY.txt      # 실제 키 파일 (Git 제외 ??)
    └── API_KEYS.md             # 통합 키 파일 (Git 제외 ??)
```

---

## ? 빠른 시작

### 1단계: API 키 파일 생성

예시 파일을 복사하여 실제 키 파일을 만드세요:

```powershell
# Windows
cd api_keys
copy GEMINI_API_KEY.txt.example GEMINI_API_KEY.txt
copy GOOGLE_API_KEY.txt.example GOOGLE_API_KEY.txt

# 또는 통합 파일 사용
copy API_KEYS.md.example API_KEYS.md
```

```bash
# Linux/Mac
cd api_keys
cp GEMINI_API_KEY.txt.example GEMINI_API_KEY.txt
cp GOOGLE_API_KEY.txt.example GOOGLE_API_KEY.txt

# 또는 통합 파일 사용
cp API_KEYS.md.example API_KEYS.md
```

### 2단계: 실제 키 입력

생성한 파일을 열고 `YOUR_API_KEY_HERE`를 실제 API 키로 교체하세요.

**GEMINI_API_KEY.txt**:
```
AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

**API_KEYS.md** (통합 관리):
```markdown
## ? API Keys

### Gemini API Key
```
AIzaSyAbc123def456ghi789jkl012mno345pqr678
```
```

### 3단계: 코드에서 사용

#### 방법 1: 헬퍼 함수 사용 (권장)

```python
from tools.load_api_key import get_gemini_api_key, get_google_api_key

# Gemini API 키 로드
gemini_key = get_gemini_api_key()

# Google API 키 로드
google_key = get_google_api_key()
```

#### 방법 2: 직접 로드

```python
from tools.load_api_key import load_api_key

# 특정 키 로드
api_key = load_api_key("GEMINI_API_KEY")

# 환경 변수 fallback 포함
api_key = load_api_key("GEMINI_API_KEY", fallback_env="GOOGLE_API_KEY")
```

#### 방법 3: 환경 변수로 설정

```python
from tools.load_api_key import set_api_key_to_env

# 환경 변수로 설정
set_api_key_to_env("GEMINI_API_KEY")
# 이제 os.environ.get("GEMINI_API_KEY")로 접근 가능
```

---

## ? 필요한 API 키 목록

### 필수 키

| 키 이름 | 용도 | 발급 링크 |
|---------|------|-----------|
| `GEMINI_API_KEY` | Gemini AI 사용 | https://makersuite.google.com/app/apikey |
| `GOOGLE_API_KEY` | Gemini Self-Healing | https://makersuite.google.com/app/apikey |

### 선택적 키

| 키 이름 | 용도 | 발급 링크 |
|---------|------|-----------|
| `GCP_PROJECT_ID` | Google Cloud Platform | https://console.cloud.google.com |
| `GCP_CREDENTIALS.json` | Vertex AI | https://console.cloud.google.com/vertex-ai |

---

## ? 보안 설정

### Git 제외 확인

`.gitignore`에 다음이 포함되어 있습니다:

```gitignore
api_keys/
!api_keys/*.example
!api_keys/README.md
```

**확인 방법**:
```bash
git status api_keys/
# 실제 키 파일은 나타나지 않아야 합니다
```

### 파일 권한 설정 (Linux/Mac)

```bash
chmod 600 api_keys/*.txt
chmod 600 api_keys/API_KEYS.md
```

### 실수로 커밋했을 때

1. **즉시 키 재생성** (가장 중요!)
2. **Git에서 제거**:
   ```bash
   git rm --cached api_keys/GEMINI_API_KEY.txt
   git commit -m "Remove API keys from tracking"
   ```
3. **Git 히스토리 정리** (필요한 경우):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch api_keys/*.txt" \
     --prune-empty --tag-name-filter cat -- --all
   ```

---

## ? 사용 예시

### 예시 1: genai_self_healing.py에서 사용

```python
from tools.load_api_key import get_gemini_api_key

# 기존 코드
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

# 개선된 코드
api_key = get_gemini_api_key() or os.environ.get("GOOGLE_API_KEY")
```

### 예시 2: Android 앱에서 사용

`local.properties` 대신 `api_keys/` 폴더 사용:

```kotlin
// build.gradle.kts에서
val apiKeysDir = rootProject.file("../../api_keys")
val geminiKeyFile = File(apiKeysDir, "GEMINI_API_KEY.txt")
val geminiApiKey = if (geminiKeyFile.exists()) {
    geminiKeyFile.readText().trim()
} else {
    localProperties.getProperty("GEMINI_API_KEY") ?: ""
}
```

### 예시 3: 배치 스크립트에서 사용

```batch
@echo off
REM API 키를 환경 변수로 설정
for /f "delims=" %%i in (api_keys\GEMINI_API_KEY.txt) do set GEMINI_API_KEY=%%i
python your_script.py
```

---

## ? 체크리스트

### 초기 설정

- [ ] `api_keys/` 폴더 생성 확인
- [ ] 예시 파일에서 실제 키 파일 생성
- [ ] 실제 API 키 입력 완료
- [ ] Git에 올라가지 않는지 확인 (`git status`)

### 코드 통합

- [ ] `tools/load_api_key.py` 사용
- [ ] 기존 코드에서 API 키 로드 방식 업데이트
- [ ] 테스트 실행하여 키 로드 확인

### 보안

- [ ] `.gitignore` 설정 확인
- [ ] 파일 권한 설정 (Linux/Mac)
- [ ] 백업 시 암호화 확인
- [ ] 팀원과 키 공유 방법 확인 (환경 변수 등)

---

## ? 문제 해결

### 키가 로드되지 않을 때

1. **파일 경로 확인**:
   ```python
   from tools.load_api_key import get_api_keys_dir
   print(get_api_keys_dir())  # 경로 확인
   ```

2. **파일 인코딩 확인**: UTF-8로 저장되어 있는지 확인

3. **파일 형식 확인**: 주석이나 공백이 없는지 확인

4. **환경 변수 확인**: fallback으로 환경 변수 사용 가능

### Git에 실수로 커밋했을 때

1. **즉시 키 재생성** (가장 중요!)
2. **Git에서 제거** (위의 "실수로 커밋했을 때" 참고)
3. **팀원에게 알림** (키가 노출되었다면)

---

## ? 관련 문서

- **API Keys 폴더 README**: `api_keys/README.md`
- **보안 가이드**: `docs/SECURITY_API_KEY_GUIDE.md`
- **Android 설정**: `docs/ANDROID_GEMINI_API_KEY_SETUP.md`

---

## ? 마이그레이션 가이드

기존에 다른 곳에 저장된 API 키를 `api_keys/` 폴더로 이동:

### 환경 변수에서 이동

```bash
# 현재 환경 변수 확인
echo $GOOGLE_API_KEY

# 파일로 저장
echo $GOOGLE_API_KEY > api_keys/GOOGLE_API_KEY.txt
```

### .env 파일에서 이동

```bash
# .env 파일에서 키 추출
grep GOOGLE_API_KEY .env | cut -d'=' -f2 > api_keys/GOOGLE_API_KEY.txt
```

### local.properties에서 이동

```bash
# Android 프로젝트의 local.properties에서 추출
grep GEMINI_API_KEY monitoring/mobile_app_android/local.properties | cut -d'=' -f2 > api_keys/GEMINI_API_KEY.txt
```

---

**마지막 업데이트**: 2026-01-14
