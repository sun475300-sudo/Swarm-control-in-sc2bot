# ? API 키 교체 가이드 (보안 강화)

**작성일**: 2026-01-14  
**목적**: 노출 가능성이 있는 기존 API 키 삭제 및 새 키 적용

---

## ?? 중요: 즉시 조치 필요

### 현재 확인된 키

**환경 변수에 설정된 키**:
- `AIzaSyC_Ci...MIIo`

**상태**: 이전에 Git에 커밋되었을 가능성이 있으므로 **즉시 삭제 및 재생성 필요**

---

## ? 1단계: 기존 키 삭제 (가장 중요!)

### Google AI Studio에서 키 삭제

1. **Google AI Studio 접속**
   - https://makersuite.google.com/app/apikey
   - 또는 https://aistudio.google.com/app/apikey

2. **기존 키 삭제**
   - 키 목록에서 해당 키 찾기
   - "Delete" 또는 "삭제" 클릭
   - 확인 후 삭제

3. **키 비활성화** (삭제 전 임시 조치)
   - 키를 삭제하기 전에 먼저 비활성화 가능
   - "Disable" 또는 "비활성화" 클릭

---

## ? 2단계: 새 API 키 발급

### 새 키 생성

1. **Google AI Studio 접속**
   - https://makersuite.google.com/app/apikey

2. **새 키 생성**
   - "Create API Key" 클릭
   - 프로젝트 선택 (또는 새 프로젝트 생성)
   - 키 생성 및 복사

3. **키 저장** (안전한 위치)
   - **절대 Git에 커밋하지 마세요!**
   - `secrets/gemini_api.txt` 파일에 저장

---

## ? 3단계: 새 키 적용

### 방법 1: 파일에 저장 (권장)

```powershell
# secrets/ 폴더에 새 키 저장
echo "YOUR_NEW_API_KEY_HERE" > secrets\gemini_api.txt
```

### 방법 2: 환경 변수 설정

```powershell
# Windows PowerShell (현재 세션만)
$env:GEMINI_API_KEY="YOUR_NEW_API_KEY_HERE"

# Windows PowerShell (영구 설정)
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "YOUR_NEW_API_KEY_HERE", "User")

# Windows CMD
setx GEMINI_API_KEY "YOUR_NEW_API_KEY_HERE"
```

### 방법 3: .env 파일 사용

```powershell
# .env 파일 생성 또는 수정
echo "GEMINI_API_KEY=YOUR_NEW_API_KEY_HERE" > .env
echo "GOOGLE_API_KEY=YOUR_NEW_API_KEY_HERE" >> .env
```

---

## ? 4단계: 기존 키 제거

### 환경 변수에서 제거

```powershell
# Windows PowerShell
Remove-Item Env:\GEMINI_API_KEY
Remove-Item Env:\GOOGLE_API_KEY

# Windows CMD
set GEMINI_API_KEY=
set GOOGLE_API_KEY=
```

### 파일에서 제거 (있는 경우)

```powershell
# 기존 키 파일 삭제
if (Test-Path "secrets\gemini_api.txt") { Remove-Item "secrets\gemini_api.txt" }
if (Test-Path "api_keys\GEMINI_API_KEY.txt") { Remove-Item "api_keys\GEMINI_API_KEY.txt" }
if (Test-Path ".env") { 
    # .env 파일에서 키 라인만 제거
    Get-Content ".env" | Where-Object { $_ -notmatch "GEMINI_API_KEY|GOOGLE_API_KEY" } | Set-Content ".env.tmp"
    Move-Item ".env.tmp" ".env" -Force
}
```

---

## ? 5단계: 새 키 확인

### Python 스크립트로 확인

```python
from tools.load_api_key import get_gemini_api_key

new_key = get_gemini_api_key()
if new_key:
    print(f"? 새 키 로드됨: {new_key[:10]}...")
    print(f"  전체 키: {new_key}")
    
    # 기존 키와 다른지 확인
    old_key = "AIzaSyC_Ci...MIIo"
    if new_key != old_key:
        print("? 기존 키와 다름 (교체 완료)")
    else:
        print("?? 기존 키와 동일 (아직 교체 안 됨)")
else:
    print("? 키를 찾을 수 없음")
```

### 간단한 확인

```powershell
# 환경 변수 확인
$env:GEMINI_API_KEY

# 파일 확인
Get-Content secrets\gemini_api.txt
```

---

## ? 6단계: 보안 확인

### Git에서 키 제거 확인

```bash
# Git 히스토리에서 키 검색
git log -p --all -S "AIzaSyC_Ci...MIIo" --source --all

# 현재 추적 중인 파일 확인
git ls-files | grep -E "(gemini_api|GEMINI_API_KEY|\.env)"
```

### .gitignore 확인

다음이 `.gitignore`에 포함되어 있는지 확인:

```gitignore
secrets/
!secrets/.gitkeep
!secrets/README.md
api_keys/*.txt
!api_keys/*.example
.env
.env.*
!.env.example
```

---

## ? 체크리스트

### 기존 키 삭제
- [ ] Google AI Studio에서 기존 키 삭제/비활성화
- [ ] 환경 변수에서 기존 키 제거
- [ ] 파일에서 기존 키 제거 (있는 경우)
- [ ] Git 히스토리 확인 (필요시 정리)

### 새 키 적용
- [ ] 새 API 키 발급
- [ ] `secrets/gemini_api.txt`에 새 키 저장
- [ ] 환경 변수 설정 (선택적)
- [ ] 새 키로 테스트

### 보안 확인
- [ ] `.gitignore` 설정 확인
- [ ] Git에 키가 커밋되지 않았는지 확인
- [ ] 새 키가 정상 작동하는지 확인

---

## ? 문제 해결

### 새 키가 작동하지 않는 경우

1. **키 형식 확인**
   ```python
   # AIzaSy로 시작하는지 확인
   key = get_gemini_api_key()
   if key.startswith("AIzaSy"):
       print("? 올바른 형식")
   ```

2. **키 권한 확인**
   - Google AI Studio에서 키 권한 확인
   - Gemini API가 활성화되어 있는지 확인

3. **로드 우선순위 확인**
   - `tools/load_api_key.py`의 로드 순서 확인
   - 여러 위치에 키가 있으면 우선순위에 따라 로드됨

---

## ? 관련 문서

- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **키 형식 가이드**: `docs/GEMINI_API_KEY_FORMAT.md`
- **비상 대응**: `docs/EMERGENCY_API_KEY_REMOVAL.md`

---

## ?? 중요 주의사항

1. **기존 키는 즉시 삭제하세요**
   - Git에 노출되었을 가능성이 있음
   - 삭제하지 않으면 계속 사용 가능

2. **새 키는 안전하게 보관하세요**
   - Git에 커밋하지 마세요
   - `secrets/` 폴더에 저장 (`.gitignore` 설정됨)

3. **정기적으로 키 교체**
   - 보안을 위해 주기적으로 키 교체 권장
   - 최소 3-6개월마다 교체

---

**마지막 업데이트**: 2026-01-14
