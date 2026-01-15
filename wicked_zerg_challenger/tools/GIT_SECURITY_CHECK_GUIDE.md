# Git 커밋 전 민감한 정보 검사 가이드

**작성일**: 2026-01-15  
**목적**: Git 커밋 전 이중/삼중 검사 시스템 구축  
**상태**: ✅ **구축 완료**

---

## 📋 개요

Git 커밋 전에 민감한 정보(API 키, 비밀번호 등)가 포함되지 않았는지 **자동으로 검사**하는 시스템입니다.

**검사 레벨**:
1. **1차 검사**: Git Pre-commit Hook (자동)
2. **2차 검사**: 수동 검사 스크립트 (커밋 전 실행)
3. **3차 검사**: `.gitignore` 패턴 (파일 자체를 추적하지 않음)

---

## 🚀 빠른 시작

### 1. Git Hooks 설정 (한 번만 실행)

```powershell
# 프로젝트 루트에서 실행
.\tools\setup_git_hooks.ps1
```

이 명령어는 `.git/hooks/pre-commit` 파일을 생성하여 커밋 시 자동으로 검사를 실행합니다.

---

### 2. 수동 검사 (커밋 전 실행 권장)

```powershell
# 커밋 전에 수동으로 검사
.\tools\pre_commit_security_check.ps1
```

---

## 🔍 검사 항목

### 1. API 키 패턴

- Google API Key: `AIzaSy[A-Za-z0-9_-]{35}`
- OpenAI API Key: `sk-[A-Za-z0-9]{32,}`
- Slack Token: `xox[baprs]-[0-9]{10,13}-...`
- 일반 해시: `[0-9a-f]{32}`, `[0-9a-f]{40}`
- 주의: 구체적인 API 키 예시는 보안상의 이유로 스크립트에서 제외됨 (패턴만 사용)

### 2. 비밀번호/토큰 패턴

- `password: "value"`
- `passwd: "value"`
- `secret: "value"`
- `token: "value"`

### 3. 검사 파일 확장자

- Python: `*.py`
- Kotlin/Java: `*.kt`, `*.java`
- JavaScript/TypeScript: `*.js`, `*.ts`
- 문서: `*.md`, `*.txt`
- 설정: `*.json`, `*.yaml`, `*.yml`
- 스크립트: `*.sh`, `*.ps1`, `*.bat`

---

## 🛠️ 사용 방법

### 방법 1: 자동 검사 (Pre-commit Hook)

**설정**:
```powershell
.\tools\setup_git_hooks.ps1
```

**동작**:
- `git commit` 실행 시 자동으로 검사
- 민감한 정보 발견 시 커밋 차단
- 문제 해결 후 다시 커밋

**예시**:
```powershell
git add .
git commit -m "Update code"
# → 자동으로 검사 실행
# → 민감한 정보 발견 시 커밋 차단
```

---

### 방법 2: 수동 검사

**실행**:
```powershell
.\tools\pre_commit_security_check.ps1
```

**결과**:
- ✅ 민감한 정보 없음 → 커밋 가능
- ❌ 민감한 정보 발견 → 파일 목록 표시, 커밋 차단

---

## 📊 검사 프로세스

### 1차 검사: Pre-commit Hook (자동)

```
git commit
  ↓
pre-commit hook 실행
  ↓
pre_commit_security_check.ps1 실행
  ↓
스테이징된 파일 검사
  ↓
민감한 정보 발견?
  ├─ 예 → 커밋 차단 ❌
  └─ 아니오 → 커밋 진행 ✅
```

### 2차 검사: 수동 검사 (권장)

```
커밋 전
  ↓
.\tools\pre_commit_security_check.ps1 실행
  ↓
모든 파일 검사
  ↓
민감한 정보 발견?
  ├─ 예 → 파일 수정 후 재검사
  └─ 아니오 → git commit 실행
```

### 3차 검사: .gitignore (파일 추적 방지)

```
.gitignore 패턴
  ↓
민감한 파일 자동 제외
  ↓
Git에 추적되지 않음 ✅
```

---

## ⚠️ 주의사항

### 1. False Positive (거짓 양성)

일부 패턴이 실제 API 키가 아닌 일반 문자열과 매칭될 수 있습니다.

**예시**:
- `password: "example"` → 검사됨 (의도된 것)
- `token: "test_token_12345"` → 검사됨 (의도된 것)

**해결**:
- 실제 키가 아닌 경우 무시하고 커밋 진행
- 또는 검사 스크립트에서 예외 패턴 추가

### 2. 성능

대용량 파일이 많을 경우 검사 시간이 오래 걸릴 수 있습니다.

**해결**:
- 스테이징된 파일만 검사 (기본 동작)
- 필요시 특정 파일/폴더 제외

---

## 🔧 고급 설정

### 검사 패턴 추가

`tools/pre_commit_security_check.ps1` 파일을 수정:

```powershell
$sensitivePatterns = @(
    # 기존 패턴들...
    
    # 새로운 패턴 추가
    "your_custom_pattern",
)
```

### 검사 파일 확장자 추가

```powershell
$fileExtensions = @(
    # 기존 확장자들...
    
    # 새로운 확장자 추가
    "*.xml",
    "*.properties",
)
```

### 특정 파일/폴더 제외

```powershell
# 검사에서 제외할 경로
$excludePaths = @(
    "node_modules/",
    "venv/",
    "build/",
    # 추가 제외 경로
)
```

---

## 📝 체크리스트

### 커밋 전 필수 확인

- [ ] `.\tools\pre_commit_security_check.ps1` 실행
- [ ] 검사 결과 확인
- [ ] 민감한 정보 발견 시 제거
- [ ] 플레이스홀더로 대체
- [ ] 재검사 후 커밋

### 정기 점검

- [ ] 주 1회: 전체 파일 검사
- [ ] 월 1회: Git 히스토리 검사
- [ ] 분기별: 보안 감사

---

## 🚨 문제 발생 시

### Hook이 작동하지 않음

```powershell
# Hook 재설정
.\tools\setup_git_hooks.ps1

# Hook 수동 실행 테스트
.\tools\pre_commit_security_check.ps1
```

### False Positive로 인한 커밋 차단

```powershell
# 검사 스크립트에서 예외 패턴 추가
# 또는
# --no-verify 플래그 사용 (권장하지 않음)
git commit --no-verify -m "message"
```

---

## 📊 검사 통계

### 검사 항목

- **API 키 패턴**: 5개
- **비밀번호/토큰 패턴**: 4개
- **검사 파일 확장자**: 13개
- **총 검사 패턴**: 9개

### 보호 레벨

- **1차 (Pre-commit Hook)**: 자동 차단
- **2차 (수동 검사)**: 사전 확인
- **3차 (.gitignore)**: 파일 추적 방지

---

## 🔗 관련 문서

- `SENSITIVE_FILES_PROTECTION.md` - 민감한 정보 보호 설정
- `SECURITY_AUDIT_FINAL_VERIFICATION.md` - 보안 감사 최종 확인
- `REMOVE_API_KEY_FROM_GIT_HISTORY.md` - Git 히스토리에서 API 키 제거

---

**작성일**: 2026-01-15  
**상태**: ✅ **이중/삼중 검사 시스템 구축 완료**  
**다음 단계**: Git Hooks 설정 및 테스트
