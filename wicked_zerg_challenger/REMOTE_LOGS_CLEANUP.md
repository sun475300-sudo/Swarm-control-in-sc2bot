# 원격 저장소 로그 파일 제거 가이드

**문제**: GitHub에 이미 푸시된 로그 파일 제거

---

## ✅ 현재 상태

### 로컬 확인 결과

- ✅ `.gitignore`에 `logs/` 패턴 포함됨
- ✅ 로컬에서 로그 파일이 Git 추적되지 않음
- ⚠️ 원격 저장소에 이미 푸시된 파일은 별도 제거 필요

---

## 🚀 원격 저장소에서 로그 파일 제거

### 방법 1: Git 명령어로 제거 (권장)

```powershell
cd d:\Swarm-contol-in-sc2bot

# 1. 로컬에서 Git 추적 제거 (파일은 유지)
git rm --cached -r wicked_zerg_challenger/logs/
git rm --cached **/logs/*.txt
git rm --cached **/log_*.txt

# 2. .gitignore 확인 (이미 설정됨)
git add .gitignore

# 3. 변경사항 커밋
git commit -m "chore: Remove log files from Git tracking"

# 4. 원격 저장소에 푸시 (원격에서도 삭제됨)
git push origin main
```

---

### 방법 2: 자동 스크립트 사용

```powershell
cd d:\Swarm-contol-in-sc2bot
.\wicked_zerg_challenger\tools\remove_logs_from_git.ps1

# 스크립트 실행 후
git add .gitignore
git commit -m "chore: Remove log files from Git tracking"
git push origin main
```

---

### 방법 3: 특정 파일만 제거

```powershell
# 특정 로그 파일만 제거
git rm --cached wicked_zerg_challenger/logs/log_20260114_191826.txt
git rm --cached wicked_zerg_challenger/logs/log_20260115_*.txt

# 커밋 및 푸시
git commit -m "chore: Remove specific log files"
git push origin main
```

---

## ⚠️ 주의사항

### 파일은 로컬에 유지됨

`git rm --cached` 명령어는:
- ✅ Git 추적에서만 제거
- ✅ 로컬 파일은 그대로 유지
- ✅ 원격 저장소에 푸시하면 원격에서도 삭제됨

### 히스토리에서 완전히 제거 (선택사항)

Git 히스토리에서도 완전히 제거하려면:

```powershell
# BFG Repo-Cleaner 사용 (권장)
# 1. BFG 다운로드: https://rtyley.github.io/bfg-repo-cleaner/
# 2. 실행:
java -jar bfg.jar --delete-files "log_*.txt" .git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 3. 강제 푸시 (팀원과 협의 후!)
git push origin --force --all
```

**주의**: 히스토리 재작성은 팀원과 반드시 협의하세요!

---

## 🔍 확인 명령어

### 로컬에서 추적되는 로그 파일 확인

```powershell
# Git에 추적되는 로그 파일 확인
git ls-files | Select-String -Pattern "logs/|log_.*\.txt"

# 결과가 비어있어야 함
```

### .gitignore 작동 확인

```powershell
# 특정 파일이 무시되는지 확인
git check-ignore -v wicked_zerg_challenger/logs/log_20260114_191826.txt

# 결과 예시:
# .gitignore:26:logs/	wicked_zerg_challenger/logs/log_20260114_191826.txt
```

---

## 📊 예상 효과

### 제거 전
- 저장소 크기: 수백 MB (로그 파일 포함)
- 다운로드 시간: 느림
- 히스토리: 지저분함

### 제거 후
- 저장소 크기: 소스 코드만 (훨씬 작음)
- 다운로드 시간: 빠름
- 히스토리: 깔끔함

---

## 🔗 관련 문서

- 로그 파일 관리: `LOGS_CLEANUP.md`
- 자동 제거 스크립트: `tools/remove_logs_from_git.ps1`
- `.gitignore` 파일: 프로젝트 루트

---

**마지막 업데이트**: 2026-01-15
