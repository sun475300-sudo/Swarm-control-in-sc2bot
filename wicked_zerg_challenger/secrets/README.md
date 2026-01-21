# ? Secrets 폴더

**?? 중요: 이 폴더의 모든 파일은 Git에 올라가지 않습니다!**

## ? 파일 구조

```
secrets/
├── gemini_api.txt          # Gemini API 키
├── ngrok_auth.txt          # Ngrok 인증 토큰 (선택적)
└── .gitkeep                # 폴더 추적용 (Git 포함)
```

## ? 빠른 설정

### 1. 파일 생성

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

### 2. 실제 키 입력

각 파일에 키만 입력하세요 (줄바꿈 없이):

**gemini_api.txt**:
```
AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

**ngrok_auth.txt** (선택적):
```
your_ngrok_auth_token_here
```

## ? 코드에서 사용

```python
from tools.load_api_key import get_gemini_api_key

# 자동으로 secrets/ 폴더에서 읽어옵니다
api_key = get_gemini_api_key()
```

## ? 보안

- 모든 파일은 `.gitignore`에 의해 제외됩니다
- 파일 권한 설정 (Linux/Mac): `chmod 600 secrets/*.txt`
- 절대 Git에 커밋하지 마세요!
