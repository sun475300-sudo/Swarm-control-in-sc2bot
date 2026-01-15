# ? API 키 완전 제거 가이드

**작성일**: 2026-01-14  
**목적**: 프로젝트에서 기존 API 키를 완전히 제거하고 새 키만 사용

---

## ? 작업 목록

### ? 1. .env 파일 확인 및 정리

```bash
# .env 파일이 있다면 확인
cat .env

# API 키 라인 제거
# Windows PowerShell
(Get-Content .env) | Where-Object { $_ -notmatch "GEMINI_API_KEY|GOOGLE_API_KEY" } | Set-Content .env

# Linux/Mac
grep -v "GEMINI_API_KEY\|GOOGLE_API_KEY" .env > .env.tmp && mv .env.tmp .env
```

---

### ? 2. 환경 변수에서 키 제거

#### Windows PowerShell
```powershell
# 현재 세션에서 제거
Remove-Item Env:\GEMINI_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\GOOGLE_API_KEY -ErrorAction SilentlyContinue

# 사용자 환경 변수에서 제거
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $null, "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", $null, "User")
```

#### Windows CMD
```cmd
set GEMINI_API_KEY=
set GOOGLE_API_KEY=
```

#### Linux/Mac
```bash
unset GEMINI_API_KEY
unset GOOGLE_API_KEY

# ~/.bashrc 또는 ~/.zshrc에서도 제거
sed -i '/GEMINI_API_KEY/d' ~/.bashrc
sed -i '/GOOGLE_API_KEY/d' ~/.bashrc
```

---

### ? 3. 코드 내부의 하드코딩된 키 제거

```bash
# Python 스크립트 실행
cd wicked_zerg_challenger
python tools/remove_old_api_keys.py
```

**실행 내용**:
- 하드코딩된 키 검색
- 문서 파일에서 예제 키 마스킹
- 코드 파일에서 키 제거 또는 주석 처리

---

### ? 4. Git History에서 키 완전히 삭제

#### 방법 1: git-filter-repo (권장)

```bash
# 1. git-filter-repo 설치
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
# 1. BFG 다운로드
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 키 제거
java -jar bfg.jar --replace-text keys.txt

# 3. 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**keys.txt 내용**:
```
AIzaSyC_Ci...MIIo==>REDACTED
AIzaSyD-c6...UZrc==>REDACTED
```

#### PowerShell 스크립트 사용

```powershell
cd wicked_zerg_challenger
.\tools\clean_git_history.ps1
```

---

## ? 키 검색 및 확인

### 현재 프로젝트에서 키 검색

```bash
# 모든 파일에서 키 검색
git grep "AIzaSyC_Ci...MIIo" --all

# Git history에서 검색
git log -p --all -S "AIzaSyC_Ci...MIIo"
```

### 키가 제거되었는지 확인

```bash
# 프로젝트 파일에서 검색
grep -r "AIzaSyC_Ci...MIIo" . --exclude-dir=.git

# Git history에서 검색
git log --all --full-history --source -- "**/*" | grep "AIzaSyC_Ci...MIIo"
```

---

## ? 새 키 설정

### 1. 새 키 파일 생성

```powershell
# secrets 폴더에 새 키 저장 (권장)
echo "AIzaSyD-c6...UZrc" > secrets\gemini_api.txt

# 또는 api_keys 폴더에 저장
echo "AIzaSyD-c6...UZrc" > api_keys\GEMINI_API_KEY.txt
echo "AIzaSyD-c6...UZrc" > api_keys\GOOGLE_API_KEY.txt
```

### 2. 새 키 확인

```bash
python -c "from tools.load_api_key import get_gemini_api_key; print(get_gemini_api_key()[:20] + '...')"
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

## ? 관련 문서

- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **보안 설정**: `docs/SECURITY_SETUP_COMPLETE.md`
- **키 로테이션**: `docs/API_KEY_ROTATION_GUIDE.md`

---

## ? 체크리스트

### 제거 작업
- [ ] .env 파일에서 키 제거
- [ ] 환경 변수에서 키 제거
- [ ] 코드 내부의 하드코딩된 키 제거
- [ ] Git history에서 키 제거
- [ ] 키 검색으로 확인

### 새 키 설정
- [ ] 새 키 파일 생성
- [ ] 새 키 확인
- [ ] 코드에서 새 키 로드 확인

### 팀원 알림
- [ ] Git history 변경 사항 알림
- [ ] 저장소 재클론 안내
- [ ] 새 키 설정 방법 안내

---

**마지막 업데이트**: 2026-01-14
