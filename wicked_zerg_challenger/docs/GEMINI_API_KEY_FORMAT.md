# ? GEMINI_API_KEY 형식 및 확인 방법

**작성일**: 2026-01-14  
**목적**: GEMINI_API_KEY의 형식과 확인 방법 안내

---

## ? GEMINI_API_KEY 형식

### Google API 키 형식

GEMINI_API_KEY는 **Google API 키** 형식을 따릅니다:

```
AIzaSy[알파벳/숫자/특수문자 35자]
```

**예시** (실제 키 아님):
```
AIzaSyAbc123def456ghi789jkl012mno345pqr678
```

**주의**: 위 예시는 형식 설명용이며, 실제 키가 아닙니다. 실제 키는 `AIzaSy`로 시작하는 39자 길이의 문자열입니다.
**특징**:
- `AIzaSy`로 시작
- 총 약 39자 길이
- 알파벳 대소문자, 숫자, 하이픈(-), 언더스코어(_) 포함 가능

---

## ? 현재 키 확인 방법

### 방법 1: Python 스크립트로 확인

```python
from tools.load_api_key import get_gemini_api_key

# 키 로드
api_key = get_gemini_api_key()

if api_key:
    # 키의 앞부분만 표시 (보안)
    print(f"? GEMINI_API_KEY: {api_key[:10]}... (길이: {len(api_key)})")
    print(f"  형식 확인: {'? 올바른 형식' if api_key.startswith('AIzaSy') else '? 잘못된 형식'}")
else:
    print("? GEMINI_API_KEY: Not found")
```

### 방법 2: 파일에서 직접 확인

```powershell
# secrets/ 폴더 확인
Get-Content secrets\gemini_api.txt

# api_keys/ 폴더 확인
Get-Content api_keys\GEMINI_API_KEY.txt
```

### 방법 3: 환경 변수 확인

```powershell
# Windows PowerShell
$env:GEMINI_API_KEY
$env:GOOGLE_API_KEY

# Windows CMD
echo %GEMINI_API_KEY%
echo %GOOGLE_API_KEY%

# Linux/Mac
echo $GEMINI_API_KEY
echo $GOOGLE_API_KEY
```

### 방법 4: .env 파일 확인

```powershell
# .env 파일 확인
Get-Content .env | Select-String "GEMINI_API_KEY"
Get-Content .env | Select-String "GOOGLE_API_KEY"
```

---

## ? 키가 저장될 수 있는 위치

우선순위 순서:

1. **`secrets/gemini_api.txt`** (권장)
   ```
   AIzaSyAbc123def456ghi789jkl012mno345pqr678
   ```

2. **`api_keys/GEMINI_API_KEY.txt`** (하위 호환성)
   ```
   AIzaSyAbc123def456ghi789jkl012mno345pqr678
   ```

3. **`.env` 파일**
   ```
   GEMINI_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678
   GOOGLE_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678
   ```

4. **환경 변수**
   ```powershell
   $env:GEMINI_API_KEY="AIzaSyAbc123def456ghi789jkl012mno345pqr678"
   $env:GOOGLE_API_KEY="AIzaSyAbc123def456ghi789jkl012mno345pqr678"
   ```

---

## ? 키 유효성 검증

### Python으로 검증

```python
import re

def validate_gemini_api_key(api_key: str) -> bool:
    """GEMINI_API_KEY 형식 검증"""
    if not api_key:
        return False
    
    # Google API 키 형식: AIzaSy로 시작, 약 39자
    pattern = r'^AIzaSy[A-Za-z0-9_-]{35}$'
    return bool(re.match(pattern, api_key))

# 사용 예시
api_key = get_gemini_api_key()
if validate_gemini_api_key(api_key):
    print("? 유효한 GEMINI_API_KEY 형식")
else:
    print("? 잘못된 GEMINI_API_KEY 형식")
```

---

## ? 보안 주의사항

### ? 하지 말아야 할 것

1. **키를 코드에 직접 작성**
   ```python
   # ? 절대 이렇게 하지 마세요!
   api_key = "AIzaSyAbc123def456ghi789jkl012mno345pqr678"
   ```

2. **키를 Git에 커밋**
   - `.gitignore`에 의해 자동 제외되지만 확인 필요

3. **키를 로그에 출력**
   ```python
   # ? 전체 키 출력 금지
   print(f"API Key: {api_key}")
   
   # ? 앞부분만 출력
   print(f"API Key: {api_key[:10]}...")
   ```

### ? 올바른 방법

1. **파일에서 로드** (권장)
   ```python
   from tools.load_api_key import get_gemini_api_key
   api_key = get_gemini_api_key()
   ```

2. **환경 변수 사용**
   ```python
   import os
   api_key = os.environ.get("GEMINI_API_KEY")
   ```

---

## ? 키 발급 방법

### 1. Google AI Studio에서 발급

1. https://makersuite.google.com/app/apikey 접속
2. Google 계정으로 로그인
3. "Create API Key" 클릭
4. 프로젝트 선택 (또는 새 프로젝트 생성)
5. API 키 생성 및 복사

### 2. 키 저장

```powershell
# secrets/ 폴더에 저장 (권장)
echo "AIzaSyAbc123def456ghi789jkl012mno345pqr678" > secrets\gemini_api.txt

# 또는 .env 파일에 저장
echo "GEMINI_API_KEY=AIzaSyAbc123def456ghi789jkl012mno345pqr678" >> .env
```

---

## ? 테스트 스크립트

### 간단한 테스트

```python
#!/usr/bin/env python3
# test_api_key.py

from tools.load_api_key import get_gemini_api_key
import re

def main():
    print("=" * 50)
    print("GEMINI_API_KEY 확인")
    print("=" * 50)
    
    api_key = get_gemini_api_key()
    
    if not api_key:
        print("? GEMINI_API_KEY를 찾을 수 없습니다.")
        print("\n설정 방법:")
        print("  1. secrets/gemini_api.txt 파일 생성")
        print("  2. 또는 환경 변수 설정: $env:GEMINI_API_KEY='YOUR_KEY'")
        return
    
    # 형식 검증
    pattern = r'^AIzaSy[A-Za-z0-9_-]{35}$'
    is_valid = bool(re.match(pattern, api_key))
    
    print(f"? 키 발견: {api_key[:10]}... (길이: {len(api_key)})")
    print(f"  형식: {'? 올바른 형식' if is_valid else '? 잘못된 형식'}")
    
    if is_valid:
        print("\n? GEMINI_API_KEY가 올바르게 설정되었습니다!")
    else:
        print("\n?? 키 형식이 올바르지 않습니다.")
        print("  예상 형식: AIzaSy[35자]")

if __name__ == "__main__":
    main()
```

---

## ? 관련 문서

- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`
- **보안 폴더 구조**: `docs/SECURITY_FOLDER_STRUCTURE.md`

---

**마지막 업데이트**: 2026-01-14
