# ? 완전한 API 키 제거 가이드 - "과거 키가 없음" 상태 만들기

**작성일**: 2026-01-14  
**목적**: 프로젝트를 완전히 "과거 키가 없음" 상태로 만들기

---

## ? 목표

다음 위치에서 **모든** 오래된 API 키를 완전히 제거:

1. ? 환경 변수 (시스템, 사용자, 세션)
2. ? .env 파일
3. ? 문서 파일 (예제 키 마스킹)
4. ? 코드 파일 (하드코딩된 키 제거)
5. ? Git History (완전히 삭제)

---

## ? 빠른 실행

### 완전한 제거 (권장)

```powershell
# PowerShell 스크립트 실행
cd wicked_zerg_challenger
.\tools\complete_key_removal.ps1
```

또는

```bash
# 배치 파일 실행
bat\complete_key_removal.bat
```

### 제거 확인

```powershell
# 확인 스크립트 실행
.\tools\verify_key_removal.ps1
```

또는

```bash
bat\verify_key_removal.bat
```

---

## ? 상세 작업 내용

### 1. 환경 변수에서 키 제거

#### 현재 세션
```powershell
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue
```

#### 사용자 환경 변수
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
```

#### 시스템 환경 변수 (관리자 권한 필요)
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "Machine")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "Machine")
```

---

### 2. .env 파일에서 키 제거

```powershell
$content = Get-Content .env
$newContent = $content | Where-Object { 
    $_ -notmatch "GEMINI_API_KEY" -and 
    $_ -notmatch "GOOGLE_API_KEY" -and
    $_ -notmatch "AIzaSy"
}
$newContent | Set-Content .env
```

---

### 3. 문서 파일에서 예제 키 마스킹

**제거할 키**:
- `AIzaSyC_Ci...MIIo`
- `AIzaSyD-c6...UZrc`

**마스킹 형식**: `AIzaSyC_Ci...MIIo`

모든 `.md`, `.txt` 파일에서 예제 키를 마스킹합니다.

---

### 4. 코드 파일에서 하드코딩된 키 제거

**대상 파일**: `.py`, `.kt`, `.java`, `.js`, `.ts`

**변경 내용**:
- `"AIzaSyC_Ci...MIIo"` → `"YOUR_API_KEY_HERE"`
- 환경 변수나 `load_api_key()` 함수 사용 권장

---

### 5. Git History에서 키 완전히 제거

#### 방법 1: git-filter-repo (권장)

```bash
# 1. 설치
pip install git-filter-repo

# 2. 백업 생성
git branch backup-before-key-removal

# 3. 키 제거
git filter-repo --replace-text <(echo "AIzaSyC_Ci...MIIo==>REDACTED")

# 4. 원격 저장소에 강제 푸시 (주의!)
git push origin --force --all
git push origin --force --tags
```

#### 방법 2: BFG Repo-Cleaner

```bash
# 1. keys.txt 파일 생성
echo "AIzaSyC_Ci...MIIo==>REDACTED" > keys.txt
echo "AIzaSyD-c6...UZrc==>REDACTED" >> keys.txt

# 2. BFG 실행
java -jar bfg.jar --replace-text keys.txt

# 3. 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. 원격 저장소에 강제 푸시
git push origin --force --all
```

---

## ? 확인 방법

### 1. 환경 변수 확인

```powershell
# 사용자 환경 변수
[System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")
[System.Environment]::GetEnvironmentVariable("GOOGLE_API_KEY", "User")

# 현재 세션
$env:GEMINI_API_KEY
$env:GOOGLE_API_KEY
```

**예상 결과**: `$null` 또는 빈 값

---

### 2. 파일 검색

```powershell
# 프로젝트 파일에서 검색
Select-String -Path ".\*" -Pattern "AIzaSyC_Ci...MIIo" -Recurse | 
    Where-Object { $_.Path -notmatch "\.git|node_modules|venv|secrets|api_keys" }
```

**예상 결과**: 검색 결과 없음

---

### 3. Git History 검색

```bash
# Git history에서 검색
git log -p --all -S "AIzaSyC_Ci...MIIo" --source --all
```

**예상 결과**: 검색 결과 없음 (또는 `REDACTED`로 마스킹됨)

---

### 4. 자동 확인 스크립트

```powershell
.\tools\verify_key_removal.ps1
```

**예상 출력**:
```
? 환경 변수에 오래된 키가 없습니다
? .env 파일에 오래된 키가 없습니다
? 프로젝트 파일에 오래된 키가 없습니다
? Git history에 오래된 키가 없습니다

? 완료! 모든 오래된 키가 제거되었습니다.
? '과거 키가 없음' 상태입니다.
```

---

## ?? 주의사항

### Git History 수정 시

1. **백업 필수**: 작업 전 반드시 백업 브랜치 생성
2. **팀원 알림**: 모든 팀원에게 알려야 함
3. **강제 푸시**: `--force` 옵션 사용 시 주의
4. **재클론 필요**: 팀원들은 저장소를 다시 클론해야 함

### 키 보안

1. **절대 Git에 커밋하지 마세요**
2. **.gitignore 확인**: `secrets/`, `api_keys/` 폴더가 제외되어 있는지 확인
3. **환경 변수 사용**: 프로덕션 환경에서는 환경 변수 사용 권장

---

## ? 최종 확인 체크리스트

### 제거 확인
- [ ] 환경 변수에 오래된 키 없음
- [ ] .env 파일에 오래된 키 없음
- [ ] 문서 파일에 예제 키 마스킹됨
- [ ] 코드 파일에 하드코딩된 키 없음
- [ ] Git history에 오래된 키 없음

### 새 키 설정
- [ ] 새 키 파일 생성 (`secrets/gemini_api.txt`)
- [ ] 새 키 로드 확인
- [ ] 코드에서 새 키 사용 확인

### 팀원 알림
- [ ] Git history 변경 사항 알림
- [ ] 저장소 재클론 안내
- [ ] 새 키 설정 방법 안내

---

## ? 관련 문서

- **제거 도구**: `tools/complete_key_removal.ps1`
- **확인 도구**: `tools/verify_key_removal.ps1`
- **제거 가이드**: `docs/API_KEY_CLEANUP_GUIDE.md`

---

## ? 요약

### 완전한 제거 실행

```bash
# 1. 완전한 제거
bat\complete_key_removal.bat

# 2. 제거 확인
bat\verify_key_removal.bat
```

### 최종 상태

? 환경 변수: 오래된 키 없음  
? .env 파일: 오래된 키 없음  
? 문서 파일: 예제 키 마스킹됨  
? 코드 파일: 하드코딩된 키 없음  
? Git History: 오래된 키 없음  

**→ "과거 키가 없음" 상태 완료!**

---

**마지막 업데이트**: 2026-01-14
