# ? 보안 폴더 구조 가이드

**작성일**: 2026-01-14  
**목적**: 파일럿과 엔지니어 관점에서 관리하기 편한 보안 폴더 구조

---

## ? 권장 폴더 구조

### 구조 1: secrets/ 폴더 (권장) ?

```
wicked_zerg_challenger/
├── secrets/                    # 로컬 전용, Git 제외
│   ├── gemini_api.txt         # Gemini API 키
│   ├── ngrok_auth.txt         # Ngrok 인증 토큰 (선택적)
│   ├── .gitkeep               # 폴더 추적용 (Git 포함)
│   └── README.md              # 사용 가이드 (Git 포함)
│
├── .env.example               # Git 공개용 템플릿
├── .env                       # 실제 키 (Git 제외)
└── .gitignore                 # secrets/ 폴더 제외 설정
```

**장점**:
- ? 간단한 파일명 (gemini_api.txt)
- ? 파일럿과 엔지니어 모두 이해하기 쉬움
- ? Git에 올라가지 않음
- ? 코드에서 직접 읽기 쉬움

---

### 구조 2: api_keys/ 폴더 (하위 호환성)

```
wicked_zerg_challenger/
├── api_keys/                  # 로컬 전용, Git 제외
│   ├── GEMINI_API_KEY.txt    # Gemini API 키
│   ├── GOOGLE_API_KEY.txt    # Google API 키
│   └── README.md             # 사용 가이드 (Git 포함)
```

**장점**:
- ? 기존 코드와 호환
- ? 명확한 키 이름

---

## ? 빠른 설정 (secrets/ 폴더)

### 1단계: 파일 생성

```powershell
# Windows
cd secrets
echo. > gemini_api.txt
echo. > ngrok_auth.txt
```

```bash
# Linux/Mac
cd secrets
touch gemini_api.txt
touch ngrok_auth.txt
```

### 2단계: 실제 키 입력

**gemini_api.txt**:
```
AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

**ngrok_auth.txt** (선택적):
```
your_ngrok_auth_token_here
```

### 3단계: .env 파일 생성 (선택적)

```powershell
# Windows
copy .env.example .env
```

```bash
# Linux/Mac
cp .env.example .env
```

그리고 `.env` 파일에 실제 키 입력:
```
GEMINI_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678
GOOGLE_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

---

## ? 코드에서 키 불러오기 (보안 모범 사례)

### 방법 1: 헬퍼 함수 사용 (권장)

```python
from tools.load_api_key import get_gemini_api_key

# 자동으로 secrets/ 폴더에서 읽어옵니다
api_key = get_gemini_api_key()
```

### 방법 2: 직접 파일 읽기

```python
def get_api_key():
    """보안 모범 사례: 파일에서 직접 읽기"""
    try:
        secrets_dir = Path(__file__).parent.parent / "secrets"
        key_file = secrets_dir / "gemini_api.txt"
        
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("에러: secrets/gemini_api.txt 파일을 찾을 수 없습니다.")
        return None

# 사용
api_key = get_api_key()
```

### 방법 3: .env 파일 사용

```python
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 읽기
api_key = os.getenv("GEMINI_API_KEY")
```

---

## ? 우선순위 (자동 처리)

`tools/load_api_key.py`는 다음 순서로 키를 찾습니다:

1. **secrets/ 폴더** (권장)
   - `secrets/gemini_api.txt`
   - `secrets/ngrok_auth.txt`

2. **api_keys/ 폴더** (하위 호환성)
   - `api_keys/GEMINI_API_KEY.txt`
   - `api_keys/GOOGLE_API_KEY.txt`

3. **.env 파일**
   - 프로젝트 루트의 `.env` 파일

4. **환경 변수**
   - `GEMINI_API_KEY`
   - `GOOGLE_API_KEY`

---

## ? 파일명 매핑

| 키 이름 | secrets/ 파일명 | api_keys/ 파일명 |
|---------|----------------|------------------|
| `GEMINI_API_KEY` | `gemini_api.txt` | `GEMINI_API_KEY.txt` |
| `GOOGLE_API_KEY` | `gemini_api.txt` (동일) | `GOOGLE_API_KEY.txt` |
| `NGROK_AUTH_TOKEN` | `ngrok_auth.txt` | `NGROK_AUTH_TOKEN.txt` |

---

## ? 보안 설정

### .gitignore 확인

다음이 `.gitignore`에 포함되어 있습니다:

```gitignore
# secrets/ 폴더 (모든 파일 제외, README와 .gitkeep만 포함)
secrets/
!secrets/.gitkeep
!secrets/README.md

# .env 파일
.env
.env.*
!.env.example
```

### 파일 권한 설정 (Linux/Mac)

```bash
chmod 600 secrets/*.txt
chmod 600 .env
```

---

## ? 마이그레이션 가이드

### api_keys/ → secrets/ 마이그레이션

```powershell
# Windows
cd wicked_zerg_challenger
copy api_keys\GEMINI_API_KEY.txt secrets\gemini_api.txt
```

```bash
# Linux/Mac
cd wicked_zerg_challenger
cp api_keys/GEMINI_API_KEY.txt secrets/gemini_api.txt
```

**참고**: `tools/load_api_key.py`는 두 폴더를 모두 지원하므로 기존 코드는 그대로 작동합니다.

---

## ? 문제 해결

### 키가 로드되지 않을 때

1. **파일 경로 확인**:
   ```python
   from tools.load_api_key import get_secrets_dir
   print(get_secrets_dir())  # 경로 확인
   ```

2. **파일 존재 확인**:
   ```bash
   ls secrets/
   # gemini_api.txt 파일이 있는지 확인
   ```

3. **파일 형식 확인**: 키만 입력되어 있는지 확인 (줄바꿈, 공백 제거)

### Git에 실수로 커밋했을 때

1. **즉시 키 재생성** (가장 중요!)

2. **Git에서 제거**:
   ```bash
   git rm --cached secrets/gemini_api.txt
   git commit -m "Remove API keys from tracking"
   ```

3. **Git 히스토리 정리** (필요한 경우):
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch secrets/*.txt" \
     --prune-empty --tag-name-filter cat -- --all
   ```

---

## ? 관련 문서

- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`
- **secrets/ README**: `secrets/README.md`

---

**마지막 업데이트**: 2026-01-14
