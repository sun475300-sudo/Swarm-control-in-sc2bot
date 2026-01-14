# ? 보안 폴더 구조 설정 완료

**작성일**: 2026-01-14  
**상태**: ? 완료

---

## ? 생성된 폴더 구조

```
wicked_zerg_challenger/
├── secrets/                    # ? 권장 보안 폴더 (Git 제외)
│   ├── gemini_api.txt         # Gemini API 키
│   ├── ngrok_auth.txt         # Ngrok 인증 토큰 (선택적)
│   ├── .gitkeep               # 폴더 추적용 (Git 포함)
│   └── README.md              # 사용 가이드 (Git 포함)
│
├── api_keys/                   # 하위 호환성 폴더 (Git 제외)
│   ├── GEMINI_API_KEY.txt     # Gemini API 키
│   ├── GOOGLE_API_KEY.txt     # Google API 키
│   └── README.md              # 사용 가이드 (Git 포함)
│
├── .env.example                # 환경 변수 템플릿 (Git 포함)
└── .env                        # 실제 환경 변수 (Git 제외)
```

---

## ? 빠른 시작

### 방법 1: secrets/ 폴더 사용 (권장) ?

```powershell
# 1. 파일 생성
cd secrets
echo. > gemini_api.txt

# 2. 실제 키 입력
# gemini_api.txt 파일을 열고 API 키 입력
```

### 방법 2: .env 파일 사용

```powershell
# 1. 템플릿 복사
copy .env.example .env

# 2. 실제 키 입력
# .env 파일을 열고 YOUR_API_KEY_HERE를 실제 키로 교체
```

---

## ? 코드에서 사용

### 자동 로드 (권장)

```python
from tools.load_api_key import get_gemini_api_key

# 자동으로 다음 순서로 찾습니다:
# 1. secrets/gemini_api.txt
# 2. api_keys/GEMINI_API_KEY.txt
# 3. .env 파일
# 4. 환경 변수
api_key = get_gemini_api_key()
```

### 직접 파일 읽기 (보안 모범 사례)

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

api_key = get_api_key()
```

---

## ? 우선순위

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

## ? 완료된 작업

- [x] `secrets/` 폴더 생성
- [x] `.gitignore`에 `secrets/` 폴더 추가
- [x] `.env.example` 템플릿 생성
- [x] `tools/load_api_key.py` 개선 (secrets/ 폴더 지원)
- [x] `genai_self_healing.py` 개선 (자동 키 로드)
- [x] 하위 호환성 유지 (api_keys/ 폴더도 지원)

---

## ? 관련 문서

- **보안 폴더 구조**: `docs/SECURITY_FOLDER_STRUCTURE.md`
- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`

---

**마지막 업데이트**: 2026-01-14
