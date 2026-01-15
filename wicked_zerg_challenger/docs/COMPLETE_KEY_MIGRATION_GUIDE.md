# ? 프로젝트 전체를 새 키로 교체 가이드

**작성일**: 2026-01-14  
**목적**: 프로젝트 전체를 새 API 키로 완전히 교체

---

## ? 목표

1. ? 프로젝트 전체를 새 키로 교체
2. ? 환경 변수 및 배포 설정에서 옛 키 제거
3. ? 키 제한/보안 강화

---

## ? 빠른 실행

### 1단계: 새 키로 교체

```bash
# 배치 파일 실행
bat\migrate_to_new_key.bat
```

또는

```powershell
# PowerShell 스크립트 직접 실행
.\tools\migrate_to_new_key.ps1 -NewApiKey "AIzaSyD-c6...UZrc"
```

**실행 내용**:
1. 새 키 파일 생성 (`secrets/gemini_api.txt`, `api_keys/*.txt`)
2. 환경 변수 업데이트 (시스템, 사용자, 세션)
3. .env 파일 업데이트
4. 배포 설정 업데이트 (GitHub Actions, GitLab CI, Docker 등)
5. Android local.properties 업데이트
6. 키 검증

---

### 2단계: 보안 강화

```bash
# 보안 강화 스크립트 실행
bat\api_key_security_hardening.bat
```

**실행 내용**:
1. Google Cloud Console 키 제한 설정 가이드
2. 키 사용 모니터링 설정
3. 키 로테이션 스케줄 설정
4. 키 접근 제어 설정
5. 키 사용량 제한 설정

---

## ? 상세 작업 내용

### 1. 새 키 파일 생성

**생성되는 파일**:
- `secrets/gemini_api.txt` (권장)
- `api_keys/GEMINI_API_KEY.txt`
- `api_keys/GOOGLE_API_KEY.txt`

**내용**: 새 키 값

---

### 2. 환경 변수 업데이트

#### 현재 세션
```powershell
$env:GEMINI_API_KEY = "AIzaSyD-c6...UZrc"
$env:GOOGLE_API_KEY = "AIzaSyD-c6...UZrc"
```

#### 사용자 환경 변수
```powershell
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIzaSyD-c6...UZrc", "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "AIzaSyD-c6...UZrc", "User")
```

---

### 3. .env 파일 업데이트

**변경 전**:
```
GEMINI_API_KEY=AIzaSyC_Ci...MIIo
GOOGLE_API_KEY=AIzaSyC_Ci...MIIo
```

**변경 후**:
```
GEMINI_API_KEY=AIzaSyD-c6...UZrc
GOOGLE_API_KEY=AIzaSyD-c6...UZrc
```

---

### 4. 배포 설정 업데이트

#### GitHub Actions

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
4. Value: `AIzaSyD-c6...UZrc`

---

#### GitLab CI

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
4. Value: `AIzaSyD-c6...UZrc`
5. "Mask variable" 체크

---

#### Docker

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
docker run -e GEMINI_API_KEY="AIzaSyD-c6...UZrc" your-image
```

---

### 5. Android local.properties 업데이트

**변경 전**:
```
GEMINI_API_KEY=AIzaSyC_Ci...MIIo
```

**변경 후**:
```
GEMINI_API_KEY=AIzaSyD-c6...UZrc
```

---

## ? 보안 강화

### 1. Google Cloud Console에서 키 제한

1. **API 키 제한**
   - https://console.cloud.google.com/apis/credentials
   - 키 선택 → "API 제한" → "키 제한"
   - "Generative Language API"만 허용

2. **애플리케이션 제한**
   - "애플리케이션 제한" → "IP 주소" 선택
   - 서버 IP 주소 추가

3. **키 이름 변경**
   - 명확한 이름 설정 (예: `SC2-Bot-Production`)

---

### 2. 키 사용 모니터링

```python
from tools.api_key_monitoring import log_api_key_usage

# API 호출 전
log_api_key_usage("gemini", success=True)
```

---

### 3. 키 사용량 제한

```python
from tools.api_key_usage_limiter import ApiKeyUsageLimiter

limiter = ApiKeyUsageLimiter(
    daily_limit=1000,    # 일일 1000회
    hourly_limit=100     # 시간당 100회
)

can_request, message = limiter.can_make_request()
if can_request:
    # API 호출
    limiter.record_request()
```

---

### 4. 접근 제어

**파일**: `config/allowed_ips.txt`

```
192.168.1.100
10.0.0.50
```

**사용**:
```python
from tools.api_key_access_control import ApiKeyAccessControl

access_control = ApiKeyAccessControl()
if not access_control.is_allowed(ip=client_ip):
    raise PermissionError("접근 거부")
```

---

## ? 확인 방법

### 1. 새 키 로드 확인

```bash
python -c "from tools.load_api_key import get_gemini_api_key; print(get_gemini_api_key()[:20] + '...')"
```

**예상 출력**: `AIzaSyD-c6nmOLolncI...`

---

### 2. 환경 변수 확인

```powershell
# 사용자 환경 변수
[System.Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "User")

# 현재 세션
$env:GEMINI_API_KEY
```

**예상 결과**: `AIzaSyD-c6...UZrc`

---

### 3. 배포 파이프라인 확인

```powershell
# GitHub Actions 확인
Select-String -Path ".\.github\workflows\*.yml" -Pattern "secrets.GEMINI_API_KEY"

# Dockerfile 확인
Select-String -Path ".\Dockerfile*" -Pattern "\$GEMINI_API_KEY"
```

**예상 결과**: Secrets 참조로 변경됨

---

## ? 체크리스트

### 키 교체
- [ ] 새 키 파일 생성
- [ ] 환경 변수 업데이트
- [ ] .env 파일 업데이트
- [ ] 배포 설정 업데이트
- [ ] Android local.properties 업데이트
- [ ] 키 검증

### 보안 강화
- [ ] Google Cloud Console에서 API 키 제한
- [ ] 애플리케이션 제한 설정
- [ ] 키 사용 모니터링 활성화
- [ ] 키 사용량 제한 설정
- [ ] 접근 제어 설정 (필요한 경우)
- [ ] 키 로테이션 스케줄 설정

### 배포 파이프라인
- [ ] GitHub Secrets에 새 키 설정
- [ ] GitLab CI/CD Variables에 새 키 설정
- [ ] Azure DevOps Variables에 새 키 설정
- [ ] Docker 환경 변수에 새 키 설정
- [ ] Kubernetes Secrets에 새 키 설정

---

## ? 관련 문서

- **보안 강화**: `docs/API_KEY_SECURITY_HARDENING.md`
- **완전한 제거**: `docs/COMPLETE_KEY_REMOVAL_GUIDE.md`
- **환경 정리**: `docs/COMPLETE_ENVIRONMENT_CLEANUP_GUIDE.md`

---

## ? 요약

### 실행 순서

```bash
# 1. 새 키로 교체
bat\migrate_to_new_key.bat

# 2. 보안 강화
bat\api_key_security_hardening.bat

# 3. 확인
bat\verify_key_removal.bat
```

### 최종 상태

? 프로젝트 전체: 새 키로 교체됨  
? 환경 변수: 새 키 설정됨  
? 배포 설정: Secrets 참조로 변경됨  
? 보안 강화: 키 제한 및 모니터링 설정됨  

**→ 완전히 새 키로 교체 및 보안 강화 완료!**

---

**마지막 업데이트**: 2026-01-14
