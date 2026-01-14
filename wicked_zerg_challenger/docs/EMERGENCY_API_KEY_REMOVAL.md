# ? 비상: API 키 노출 대응 가이드

**작성일**: 2026-01-14  
**상황**: API 키가 Git에 커밋되었을 가능성

---

## ?? 즉시 조치사항

### 1단계: 키 재생성 (가장 중요!)

**즉시 다음 키들을 재생성하세요:**

1. **Gemini API Key**
   - https://makersuite.google.com/app/apikey
   - 기존 키 삭제 또는 비활성화
   - 새 키 생성

2. **Google API Key** (Gemini와 동일한 경우)
   - https://makersuite.google.com/app/apikey
   - 기존 키 삭제 또는 비활성화
   - 새 키 생성

3. **GCP Credentials** (사용 중인 경우)
   - https://console.cloud.google.com/iam-admin/serviceaccounts
   - 기존 서비스 계정 키 삭제
   - 새 키 생성

---

## ? 현재 상태 확인

### Git에 추적 중인 파일 확인

```bash
git ls-files wicked_zerg_challenger/api_keys/
```

**현재 추적 중인 파일:**
- ? `.gitkeep` (안전)
- ? `*.example` 파일들 (안전)
- ? `README.md` (안전)
- ? `SETUP_INSTRUCTIONS.md` (안전)

**실제 키 파일은 추적되지 않음** (`.gitignore`가 작동 중)

---

## ?? Git 히스토리에서 제거

### 방법 1: 특정 파일만 제거 (권장)

```bash
# 1. Git 추적에서 제거 (파일은 유지)
git rm --cached wicked_zerg_challenger/api_keys/GEMINI_API_KEY.txt
git rm --cached wicked_zerg_challenger/api_keys/GOOGLE_API_KEY.txt
git rm --cached wicked_zerg_challenger/api_keys/API_KEYS.md

# 2. 커밋
git commit -m "Remove API keys from Git tracking"

# 3. .gitignore 확인 (이미 설정되어 있음)
```

### 방법 2: Git 히스토리에서 완전히 제거

**?? 주의: 이 방법은 히스토리를 재작성하므로 팀과 협의 필요**

```bash
# 1. git-filter-branch 사용 (Git 2.22 이전)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch wicked_zerg_challenger/api_keys/GEMINI_API_KEY.txt wicked_zerg_challenger/api_keys/GOOGLE_API_KEY.txt wicked_zerg_challenger/api_keys/API_KEYS.md" \
  --prune-empty --tag-name-filter cat -- --all

# 2. git-filter-repo 사용 (권장, Git 2.22+)
# 설치: pip install git-filter-repo
git filter-repo --path wicked_zerg_challenger/api_keys/GEMINI_API_KEY.txt --invert-paths
git filter-repo --path wicked_zerg_challenger/api_keys/GOOGLE_API_KEY.txt --invert-paths
git filter-repo --path wicked_zerg_challenger/api_keys/API_KEYS.md --invert-paths

# 3. 강제 푸시 (?? 팀과 협의 후)
git push origin --force --all
git push origin --force --tags
```

---

## ? .gitignore 확인

현재 `.gitignore` 설정:

```gitignore
# API Keys folder - exclude actual key files, keep examples and docs
api_keys/*.txt
!api_keys/*.example
api_keys/API_KEYS.md
!api_keys/API_KEYS.md.example
api_keys/GCP_CREDENTIALS.json
api_keys/*.key
api_keys/*.pem
# Keep documentation files
!api_keys/README.md
!api_keys/SETUP_INSTRUCTIONS.md
!api_keys/.gitkeep
```

**? 올바르게 설정되어 있습니다.**

---

## ? 향후 예방 조치

### 1. pre-commit 훅 설정 (권장)

```bash
# .git/hooks/pre-commit 파일 생성
#!/bin/sh
# API 키 파일 커밋 방지
if git diff --cached --name-only | grep -E "(api_keys/.*\.txt|api_keys/API_KEYS\.md|secrets/.*\.txt)" | grep -v "\.example"; then
    echo "? ERROR: API 키 파일을 커밋할 수 없습니다!"
    echo "실제 키 파일은 .gitignore에 의해 제외됩니다."
    exit 1
fi
```

### 2. Git Secrets 도구 사용

```bash
# 설치
git clone https://github.com/awslabs/git-secrets.git
cd git-secrets
sudo make install

# 설정
git secrets --install
git secrets --register-aws
git secrets --add 'AIza[0-9A-Za-z_-]{35}'  # Google API Key 패턴
```

### 3. 정기적인 감사

```bash
# Git 히스토리에서 API 키 검색
git log -p --all -S "AIza" --source --all
```

---

## ? 체크리스트

- [ ] **즉시**: 모든 API 키 재생성
- [ ] Git 추적에서 실제 키 파일 제거
- [ ] `.gitignore` 확인 (? 완료)
- [ ] Git 히스토리에서 제거 (필요한 경우)
- [ ] 팀원들에게 키 재생성 알림
- [ ] pre-commit 훅 설정 (선택적)
- [ ] 향후 예방 조치 적용

---

## ? 추가 도움말

- **GitHub에서 키 제거**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- **Google Cloud 보안**: https://console.cloud.google.com/iam-admin/serviceaccounts
- **Gemini API 키 관리**: https://makersuite.google.com/app/apikey

---

**마지막 업데이트**: 2026-01-14
