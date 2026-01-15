# ? 완전한 환경 변수 캐시 및 키 제거 가이드

**작성일**: 2026-01-14  
**목적**: IDE 캐시, 터미널/배치 파일, 배포 파이프라인에서 완전히 키 제거

---

## ? 목표

다음 위치에서 **모든** 오래된 API 키를 완전히 제거:

1. ? IDE 환경 변수 캐시
2. ? 터미널/배치 파일
3. ? 환경 변수 (시스템, 사용자, 세션)
4. ? 배포 파이프라인 (GitHub Actions, GitLab CI, Azure DevOps, Docker, Kubernetes)
5. ? .env 파일

---

## ? 빠른 실행

### 완전한 정리 (권장)

```bash
# 배치 파일 실행
bat\complete_environment_cleanup.bat
```

또는

```powershell
# PowerShell 스크립트 직접 실행
.\tools\complete_environment_cleanup.ps1
```

---

## ? 상세 작업 내용

### 1. IDE 환경 변수 캐시 삭제

#### Visual Studio Code
```powershell
# 캐시 디렉토리 삭제
Remove-Item -Path "$env:APPDATA\Code\User\workspaceStorage" -Recurse -Force
Remove-Item -Path "$env:APPDATA\Code\CachedData" -Recurse -Force
Remove-Item -Path "$env:APPDATA\Code\Cache" -Recurse -Force
```

#### Android Studio
```powershell
# Android Studio 캐시 삭제
Get-ChildItem -Path "$env:USERPROFILE\.AndroidStudio*" -Recurse -Filter "caches" | Remove-Item -Recurse -Force

# Gradle 캐시 삭제
Remove-Item -Path "$env:USERPROFILE\.gradle\caches" -Recurse -Force
```

#### IntelliJ IDEA / PyCharm
```powershell
# IntelliJ IDEA 캐시 삭제
Get-ChildItem -Path "$env:USERPROFILE\.IntelliJIdea*" -Recurse -Filter "caches" | Remove-Item -Recurse -Force

# PyCharm 캐시 삭제
Get-ChildItem -Path "$env:USERPROFILE\.PyCharm*" -Recurse -Filter "caches" | Remove-Item -Recurse -Force
```

#### Cursor IDE
```powershell
# Cursor 캐시 삭제
Remove-Item -Path "$env:APPDATA\Cursor\User\workspaceStorage" -Recurse -Force
Remove-Item -Path "$env:APPDATA\Cursor\CachedData" -Recurse -Force
```

---

### 2. 터미널/배치 파일에서 이전 키 제거

**대상 파일**: `.bat`, `.cmd`, `.ps1`, `.sh`

**변경 내용**:
- `set GEMINI_API_KEY=AIzaSy...` → 주석 처리 또는 제거
- `$env:GEMINI_API_KEY="AIzaSy..."` → 주석 처리 또는 제거
- `export GEMINI_API_KEY="AIzaSy..."` → 주석 처리 또는 제거

---

### 3. 환경 변수 완전 제거

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

### 4. 배포 파이프라인에서 옛 키 제거

#### GitHub Actions

**파일**: `.github/workflows/*.yml`

**변경 전**:
```yaml
env:
  GEMINI_API_KEY: AIzaSyC_Ci...MIIo
```

**변경 후**:
```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

**GitHub Secrets 설정**:
1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. Name: `GEMINI_API_KEY`
4. Value: 새 키 입력

---

#### GitLab CI

**파일**: `.gitlab-ci.yml`

**변경 전**:
```yaml
variables:
  GEMINI_API_KEY: AIzaSyC_Ci...MIIo
```

**변경 후**:
```yaml
variables:
  GEMINI_API_KEY: $GEMINI_API_KEY
```

**GitLab CI/CD Variables 설정**:
1. GitLab 프로젝트 → Settings → CI/CD → Variables
2. "Add variable" 클릭
3. Key: `GEMINI_API_KEY`
4. Value: 새 키 입력
5. "Mask variable" 체크

---

#### Azure DevOps

**파일**: `azure-pipelines.yml`

**변경 전**:
```yaml
variables:
  GEMINI_API_KEY: AIzaSyC_Ci...MIIo
```

**변경 후**:
```yaml
variables:
  GEMINI_API_KEY: $(GEMINI_API_KEY)
```

**Azure DevOps Variables 설정**:
1. Azure DevOps 프로젝트 → Pipelines → Library
2. "Variable group" 생성 또는 기존 그룹 선택
3. "Add" → "Variable"
4. Name: `GEMINI_API_KEY`
5. Value: 새 키 입력
6. "Keep this value secret" 체크

---

#### Docker

**파일**: `Dockerfile`, `docker-compose.yml`

**변경 전**:
```dockerfile
ENV GEMINI_API_KEY=AIzaSyC_Ci...MIIo
```

**변경 후**:
```dockerfile
ENV GEMINI_API_KEY=$GEMINI_API_KEY
```

**Docker 실행 시**:
```bash
docker run -e GEMINI_API_KEY="YOUR_NEW_KEY" your-image
```

---

#### Kubernetes

**파일**: `*.yaml` (deployment, service 등)

**변경 전**:
```yaml
env:
  - name: GEMINI_API_KEY
    value: AIzaSyC_Ci...MIIo
```

**변경 후**:
```yaml
env:
  - name: GEMINI_API_KEY
    valueFrom:
      secretKeyRef:
        name: api-keys
        key: gemini-api-key
```

**Kubernetes Secret 생성**:
```bash
kubectl create secret generic api-keys \
  --from-literal=gemini-api-key="YOUR_NEW_KEY"
```

---

## ? 확인 방법

### 1. IDE 캐시 확인

```powershell
# VS Code 캐시 확인
Test-Path "$env:APPDATA\Code\Cache"

# Android Studio 캐시 확인
Test-Path "$env:USERPROFILE\.AndroidStudio*\config\caches"
```

**예상 결과**: `False` (캐시 없음)

---

### 2. 환경 변수 확인

```powershell
# 사용자 환경 변수
[System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")

# 현재 세션
$env:GEMINI_API_KEY
```

**예상 결과**: `$null` 또는 빈 값

---

### 3. 배치 파일 확인

```powershell
# 배치 파일에서 키 검색
Select-String -Path ".\bat\*.bat" -Pattern "AIzaSyC_Ci...MIIo"
```

**예상 결과**: 검색 결과 없음

---

### 4. 배포 파이프라인 확인

```powershell
# GitHub Actions 확인
Select-String -Path ".\.github\workflows\*.yml" -Pattern "AIzaSyC_Ci...MIIo"

# Dockerfile 확인
Select-String -Path ".\Dockerfile*" -Pattern "AIzaSyC_Ci...MIIo"
```

**예상 결과**: 검색 결과 없음 (또는 `${{ secrets.GEMINI_API_KEY }}` 등으로 변경됨)

---

## ?? 개별 도구 실행

### IDE 캐시만 삭제

```bash
bat\cleanup_ide_cache.bat
```

### 배포 파이프라인만 정리

```bash
bat\cleanup_deployment_pipelines.bat
```

---

## ?? 주의사항

### IDE 캐시 삭제 시

1. **IDE 종료**: 캐시 삭제 전 IDE를 완전히 종료
2. **재시작 필요**: 캐시 삭제 후 IDE 재시작
3. **인덱스 재구성**: IDE가 인덱스를 다시 구축할 수 있음

### 배포 파이프라인 수정 시

1. **Secrets 설정**: 파이프라인 파일 수정 후 실제 Secrets에 새 키 설정 필요
2. **테스트**: 파이프라인 실행 전 테스트
3. **롤백 계획**: 문제 발생 시 롤백 방법 준비

---

## ? 체크리스트

### IDE 캐시
- [ ] VS Code 캐시 삭제
- [ ] Android Studio 캐시 삭제
- [ ] IntelliJ IDEA 캐시 삭제
- [ ] PyCharm 캐시 삭제
- [ ] Cursor IDE 캐시 삭제
- [ ] IDE 재시작

### 터미널/배치 파일
- [ ] .bat 파일에서 키 제거
- [ ] .ps1 파일에서 키 제거
- [ ] .sh 파일에서 키 제거
- [ ] 새 터미널 열기

### 환경 변수
- [ ] 현재 세션 환경 변수 제거
- [ ] 사용자 환경 변수 제거
- [ ] 시스템 환경 변수 제거 (필요한 경우)

### 배포 파이프라인
- [ ] GitHub Actions 정리
- [ ] GitLab CI 정리
- [ ] Azure DevOps 정리
- [ ] Dockerfile 정리
- [ ] Kubernetes 파일 정리
- [ ] 각 플랫폼의 Secrets에 새 키 설정

---

## ? 관련 문서

- **완전한 제거 가이드**: `docs/COMPLETE_KEY_REMOVAL_GUIDE.md`
- **제거 도구**: `tools/complete_key_removal.ps1`
- **확인 도구**: `tools/verify_key_removal.ps1`

---

## ? 요약

### 완전한 정리 실행

```bash
# 1. 완전한 환경 정리
bat\complete_environment_cleanup.bat

# 2. 제거 확인
bat\verify_key_removal.bat
```

### 최종 상태

? IDE 캐시: 삭제됨  
? 터미널/배치 파일: 키 제거됨  
? 환경 변수: 오래된 키 없음  
? 배포 파이프라인: Secrets 참조로 변경됨  
? .env 파일: 오래된 키 없음  

**→ 완전히 "과거 키가 없음" 상태!**

---

**마지막 업데이트**: 2026-01-14
