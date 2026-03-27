# Git 히스토리에서 API 키 제거 가이드

**작성일**: 2026-01-15  
**제거할 API 키**: `[API_KEY_REMOVED]` (실제 키는 환경 변수나 설정 파일에서 확인)

---

## ⚠️ 중요 경고

**Git 히스토리를 다시 작성하는 것은 매우 위험한 작업입니다!**

- 이미 푸시된 커밋을 수정하면 **force push**가 필요합니다
- 다른 사람과 공유하는 저장소라면 **심각한 문제**가 발생할 수 있습니다
- 작업 전에 **반드시 백업**을 생성하세요

---

## 📋 발견된 커밋

다음 커밋에서 API 키가 발견되었습니다:

1. `7209080` - Update GOOGLE_API_KEY.txt
2. `415c34f` - Update GEMINI_API_KEY.txt
3. `a26425f` - 3 (NEW_API_KEY_SETUP.md 포함)
4. `a9d0bc5` - 32 (api_keys 파일들 포함)

---

## 🛠️ 제거 방법

### 방법 1: BFG Repo-Cleaner 사용 (권장)

BFG Repo-Cleaner는 Git filter-branch보다 **10-50배 빠르고 안전**합니다.

#### 1단계: BFG 다운로드

```bash
# BFG 다운로드
# https://rtyley.github.io/bfg-repo-cleaner/
# 또는
wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
```

#### 2단계: 제거할 키 목록 파일 생성

`passwords.txt` 파일 생성:
```
[API_KEY]==>[API_KEY_REMOVED]
```

#### 3단계: BFG 실행

```bash
# 클론된 저장소에서 실행
java -jar bfg.jar --replace-text passwords.txt

# 정리
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

#### 4단계: 확인 및 푸시

```bash
# API 키가 제거되었는지 확인
git log --all -S "[API_KEY]"

# 결과가 없어야 함

# Force push (⚠️ 주의!)
git push --force --all
git push --force --tags
```

---

### 방법 2: git filter-branch 사용

#### 1단계: 백업 생성

```bash
# 백업 브랜치 생성
git branch backup-before-api-key-removal-$(date +%Y%m%d-%H%M%S)
```

#### 2단계: filter-branch 실행

```bash
# 모든 브랜치와 태그에서 API 키 제거
git filter-branch --force --index-filter \
    "git ls-files -z | xargs -0 sed -i 's/[API_KEY]/[API_KEY_REMOVED]/g'" \
    --prune-empty --tag-name-filter cat -- --all
```

#### 3단계: 정리

```bash
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

#### 4단계: 확인 및 푸시

```bash
# 확인
git log --all -S "[API_KEY]"

# Force push
git push --force --all
git push --force --tags
```

---

### 방법 3: 제공된 스크립트 사용

#### Windows (PowerShell)

```powershell
cd d:\Swarm-contol-in-sc2bot
.\tools\remove_api_key_from_git_history.ps1 -ApiKey "[YOUR_API_KEY]"
```

**주의**: PowerShell 스크립트는 가이드만 제공합니다. 실제 실행은 Git Bash에서 해야 합니다.

#### Linux/Mac/Git Bash

```bash
cd d:/Swarm-contol-in-sc2bot
chmod +x tools/remove_api_key_from_git_history.sh
./tools/remove_api_key_from_git_history.sh "[YOUR_API_KEY]"
```

---

## ✅ 현재 파일에서 제거 완료

다음 파일에서 API 키를 제거했습니다:

- ✅ `wicked_zerg_challenger/NEW_API_KEY_SETUP.md`

**커밋 필요**:
```bash
git add wicked_zerg_challenger/NEW_API_KEY_SETUP.md
git commit -m "Remove API key from NEW_API_KEY_SETUP.md"
```

---

## 🔍 확인 방법

### 히스토리에서 API 키 검색

```bash
# 모든 커밋에서 검색
git log --all --source --full-history -S "[API_KEY]"

# 특정 파일에서 검색
git log --all --source --full-history -S "[API_KEY]" -- "wicked_zerg_challenger/NEW_API_KEY_SETUP.md"
```

### 현재 파일에서 검색

```bash
# 현재 작업 디렉토리에서 검색
grep -r "[API_KEY]" .
```

---

## 🚨 문제 발생 시 복구

작업 전에 백업 브랜치를 생성했다면:

```bash
# 백업 브랜치로 복구
git reset --hard backup-before-api-key-removal-YYYYMMDD-HHMMSS
```

---

## 📝 참고 사항

1. **API 키는 이미 노출되었을 수 있습니다**
   - GitHub에 푸시된 경우, 히스토리를 제거해도 이미 노출된 상태입니다
   - **새로운 API 키를 발급받는 것을 강력히 권장합니다**

2. **.gitignore 확인**
   - `api_keys/` 폴더가 `.gitignore`에 포함되어 있는지 확인하세요
   - 앞으로 API 키 파일이 커밋되지 않도록 주의하세요

3. **환경 변수 사용**
   - 코드에 하드코딩하지 말고 환경 변수를 사용하세요
   - `secrets/` 폴더를 사용하세요 (이미 `.gitignore`에 포함됨)

---

## 🔗 관련 문서

- `wicked_zerg_challenger/SECURITY_REVIEW.md` - 보안 검토 문서
- `wicked_zerg_challenger/NEW_API_KEY_SETUP.md` - API 키 설정 가이드

---

**작성일**: 2026-01-15  
**상태**: ✅ 현재 파일에서 제거 완료, Git 히스토리 제거는 수동 실행 필요
