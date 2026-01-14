# 로그 파일 관리 가이드

**작성일**: 2026-01-15  
**목적**: 로그 파일이 Git에 커밋되지 않도록 설정

---

## ✅ 완료된 작업

### .gitignore에 로그 파일 패턴 추가

다음 패턴들이 `.gitignore`에 추가되었습니다:

```
# Logs
# ----
logs/
*.log
*.log.*
log_*.txt          # log_20260114_191826.txt 형식
log_*.log          # log_20260114_191826.log 형식
training_log*.txt  # training_log_*.txt 형식
training_log*.log  # training_log_*.log 형식
*.log.txt          # *.log.txt 형식
```

---

## 🔍 확인 사항

### 현재 상태 확인

**로컬에서 Git 추적 확인**:
```powershell
# Git에 추적되는 로그 파일 확인
git ls-files | Select-String -Pattern "log.*\.txt|logs/"

# 결과가 비어있어야 함 (로그 파일이 추적되지 않아야 함)
```

**확인 결과**: ✅ 로컬에서는 로그 파일이 Git에 추적되지 않음

### 원격 저장소에 이미 푸시된 로그 파일 제거

만약 원격 저장소(GitHub)에 이미 로그 파일이 푸시되어 있다면:

#### 방법 1: 자동 스크립트 사용 (권장)

```powershell
cd d:\Swarm-contol-in-sc2bot
.\wicked_zerg_challenger\tools\remove_logs_from_git.ps1
```

#### 방법 2: 수동 제거

```powershell
# 1. 모든 logs/ 폴더의 파일을 Git 추적에서 제거
git rm --cached -r wicked_zerg_challenger/logs/
git rm --cached **/logs/*.txt
git rm --cached **/log_*.txt

# 2. 변경사항 커밋
git add .gitignore
git commit -m "chore: Remove log files from Git tracking"

# 3. 원격 저장소에 푸시
git push origin main
```

#### 방법 3: 특정 파일만 제거

```powershell
# 특정 로그 파일만 제거
git rm --cached wicked_zerg_challenger/logs/log_20260114_191826.txt
git rm --cached wicked_zerg_challenger/logs/log_*.txt
```

---

## 📁 로그 파일 위치

프로젝트에서 생성되는 로그 파일들:

1. **훈련 로그**:
   - `logs/training_log.log`
   - `logs/log_YYYYMMDD_HHMMSS.txt`
   - `local_training/logs/*.log`

2. **애플리케이션 로그**:
   - `logs/*.log`
   - `*.log` (프로젝트 루트)

3. **빌드 로그**:
   - `build_output.log`
   - `*.log.txt`

---

## 🚀 다음 단계

### 로컬에서 로그 파일 제거 (이미 추적된 경우)

1. **자동 스크립트 실행** (권장)
   ```powershell
   cd d:\Swarm-contol-in-sc2bot
   .\wicked_zerg_challenger\tools\remove_logs_from_git.ps1
   ```

2. **또는 수동 제거**
   ```powershell
   # 모든 logs/ 폴더의 파일 제거
   git rm --cached -r wicked_zerg_challenger/logs/
   git rm --cached **/logs/*.txt
   git rm --cached **/log_*.txt
   
   # 변경사항 커밋
   git add .gitignore
   git commit -m "chore: Remove log files from Git tracking"
   ```

### 원격 저장소에서 로그 파일 제거

**중요**: 원격 저장소(GitHub)에 이미 푸시된 파일은 별도로 제거해야 합니다.

1. **로컬에서 Git 추적 제거** (위 단계 완료)

2. **원격 저장소에 푸시**
   ```powershell
   git push origin main
   ```
   
   **주의**: 이렇게 하면 원격 저장소에서도 파일이 삭제됩니다.

3. **Git 히스토리에서 완전히 제거** (선택사항, 고급)
   
   히스토리에서도 완전히 제거하려면:
   ```powershell
   # BFG Repo-Cleaner 사용 (권장)
   # 또는 git filter-branch 사용
   ```
   
   **주의**: 히스토리 재작성은 팀원과 협의 후 진행하세요.

---

## 💡 참고사항

### 로그 파일은 왜 Git에 올리지 않나요?

1. **용량 문제**: 로그 파일은 크기가 크고 자주 생성됨
2. **히스토리 오염**: 매번 로그 파일이 변경되면 Git 히스토리가 지저분해짐
3. **불필요한 변경**: 로그는 로컬에서만 분석하면 됨
4. **민감한 정보**: 로그에 API 키나 경로 정보가 포함될 수 있음

### 로그 파일은 어디에 있나요?

- 로컬 파일 시스템에는 그대로 유지됨
- Git에만 커밋되지 않음
- 필요시 로컬에서 분석 가능

---

## 🔗 관련 문서

- `.gitignore` 파일: 프로젝트 루트
- 보안 검토: `SECURITY_REVIEW.md`

---

**마지막 업데이트**: 2026-01-15
