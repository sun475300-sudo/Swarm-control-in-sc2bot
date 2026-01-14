# ? API 키 보안 강화 가이드

**작성일**: 2026-01-14  
**목적**: API 키 보안을 최대한 강화하는 방법

---

## ? 보안 강화 목표

1. ? 키 사용 제한 (API, IP, 도메인)
2. ? 키 사용 모니터링
3. ? 키 사용량 제한
4. ? 키 로테이션
5. ? 접근 제어

---

## 1. Google Cloud Console에서 키 제한 설정

### 1.1 API 키 제한

1. **Google Cloud Console 접속**
   - https://console.cloud.google.com/apis/credentials

2. **API 키 선택**
   - 사용 중인 API 키 클릭

3. **API 제한 설정**
   - "API 제한" → "키 제한" 선택
   - "Generative Language API"만 허용
   - 다른 API는 모두 비활성화

### 1.2 애플리케이션 제한

#### IP 주소 제한 (서버 애플리케이션)

1. **"애플리케이션 제한" → "IP 주소" 선택**
2. **서버 IP 주소 추가**
   ```
   예:
   - 192.168.1.100 (로컬 개발 서버)
   - 10.0.0.50 (프로덕션 서버)
   ```

#### HTTP 리퍼러 제한 (웹 애플리케이션)

1. **"애플리케이션 제한" → "HTTP 리퍼러" 선택**
2. **허용된 도메인 추가**
   ```
   예:
   - https://yourdomain.com/*
   - https://*.yourdomain.com/*
   ```

### 1.3 키 이름 변경

- 키 이름을 명확하게 설정
- 예: `SC2-Bot-Production`, `SC2-Bot-Development`

---

## 2. 키 사용 모니터링

### 2.1 모니터링 스크립트 사용

```python
from tools.api_key_monitoring import log_api_key_usage

# API 호출 전
log_api_key_usage("gemini", success=True)

# 에러 발생 시
log_api_key_usage("gemini", success=False, error=str(e))
```

### 2.2 Google Cloud Console에서 모니터링

1. **API 및 서비스 → 대시보드**
2. **Generative Language API 선택**
3. **사용량 및 할당량 확인**
4. **비정상적인 사용량 감지**

---

## 3. 키 사용량 제한

### 3.1 사용량 제한 스크립트 사용

```python
from tools.api_key_usage_limiter import ApiKeyUsageLimiter

limiter = ApiKeyUsageLimiter(
    daily_limit=1000,    # 일일 1000회
    hourly_limit=100     # 시간당 100회
)

# API 호출 전 확인
can_request, message = limiter.can_make_request()
if not can_request:
    print(f"요청 불가: {message}")
    return

# API 호출
# ...

# 요청 기록
limiter.record_request()
```

### 3.2 Google Cloud Console에서 할당량 설정

1. **API 및 서비스 → 할당량**
2. **Generative Language API 선택**
3. **할당량 제한 설정**
   - 일일 요청 수 제한
   - 시간당 요청 수 제한

---

## 4. 키 로테이션

### 4.1 로테이션 주기

- **프로덕션 키**: 90일마다
- **개발 키**: 180일마다
- **테스트 키**: 필요시

### 4.2 로테이션 프로세스

1. **새 키 생성**
2. **새 키 테스트**
3. **모든 환경에 새 키 배포**
4. **옛 키 비활성화** (삭제하지 않음, 30일 후 삭제)
5. **옛 키 사용 중지 확인**
6. **옛 키 삭제**

### 4.3 자동 로테이션 (선택적)

```python
# tools/auto_rotate_api_key.py
from datetime import datetime, timedelta

def should_rotate_key(key_created_date: datetime) -> bool:
    """90일이 지났는지 확인"""
    return datetime.now() - key_created_date > timedelta(days=90)
```

---

## 5. 접근 제어

### 5.1 IP 주소 제한

**파일**: `config/allowed_ips.txt`

```
# 허용된 IP 주소 목록
192.168.1.100
10.0.0.50
```

**사용**:
```python
from tools.api_key_access_control import ApiKeyAccessControl

access_control = ApiKeyAccessControl()
if not access_control.is_allowed(ip=client_ip):
    raise PermissionError("접근이 거부되었습니다")
```

### 5.2 도메인 제한

**파일**: `config/allowed_domains.txt`

```
# 허용된 도메인 목록
yourdomain.com
*.yourdomain.com
```

---

## 6. 키 저장 보안

### 6.1 파일 권한 설정 (Linux/Mac)

```bash
# secrets 폴더 권한 설정
chmod 700 secrets/
chmod 600 secrets/*.txt

# api_keys 폴더 권한 설정
chmod 700 api_keys/
chmod 600 api_keys/*.txt
```

### 6.2 암호화 저장 (선택적)

```python
# tools/encrypted_key_storage.py
from cryptography.fernet import Fernet

def encrypt_key(key: str, master_key: bytes) -> str:
    """키 암호화"""
    f = Fernet(master_key)
    return f.encrypt(key.encode()).decode()

def decrypt_key(encrypted_key: str, master_key: bytes) -> str:
    """키 복호화"""
    f = Fernet(master_key)
    return f.decrypt(encrypted_key.encode()).decode()
```

---

## 7. 키 노출 대응

### 7.1 즉시 조치

1. **키 즉시 비활성화**
   - Google Cloud Console에서 키 비활성화

2. **새 키 생성**
   - 새 키 생성 및 배포

3. **Git History 정리**
   - `tools/clean_git_history.ps1` 실행

4. **모니터링 강화**
   - 비정상적인 사용량 확인

### 7.2 예방 조치

1. **.gitignore 확인**
   - `secrets/`, `api_keys/` 폴더 제외 확인

2. **코드 리뷰**
   - 하드코딩된 키 검색

3. **자동 검사**
   - CI/CD 파이프라인에서 키 검색

---

## 8. 모니터링 대시보드

### 8.1 사용량 통계

```python
# tools/api_key_stats.py
from tools.api_key_monitoring import load_usage_logs

logs = load_usage_logs()

# 일일 사용량
daily_usage = sum(1 for log in logs if log['timestamp'].startswith(today))

# 에러율
error_rate = sum(1 for log in logs if not log['success']) / len(logs) * 100

print(f"일일 사용량: {daily_usage}")
print(f"에러율: {error_rate:.2f}%")
```

---

## ? 보안 체크리스트

### Google Cloud Console
- [ ] API 키 제한 설정 (Generative Language API만)
- [ ] 애플리케이션 제한 설정 (IP 또는 HTTP 리퍼러)
- [ ] 키 이름 명확하게 설정
- [ ] 할당량 제한 설정

### 프로젝트 설정
- [ ] 키 사용 모니터링 활성화
- [ ] 키 사용량 제한 설정
- [ ] 접근 제어 설정 (필요한 경우)
- [ ] 키 로테이션 스케줄 설정

### 파일 보안
- [ ] 파일 권한 설정 (Linux/Mac)
- [ ] .gitignore 확인
- [ ] 암호화 저장 (선택적)

---

## ? 관련 문서

- **키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **로테이션 가이드**: `docs/API_KEY_ROTATION_GUIDE.md`
- **로테이션 스케줄**: `docs/API_KEY_ROTATION_SCHEDULE.md`

---

## ? 요약

### 보안 강화 실행

```bash
# 보안 강화 스크립트 실행
powershell -ExecutionPolicy Bypass -File tools\api_key_security_hardening.ps1
```

### 최종 보안 상태

? API 키 제한: Generative Language API만  
? 애플리케이션 제한: IP 또는 HTTP 리퍼러  
? 키 사용 모니터링: 활성화  
? 키 사용량 제한: 설정됨  
? 키 로테이션: 스케줄 설정됨  
? 접근 제어: 설정됨 (선택적)  

**→ 최대한 보안 강화 완료!**

---

**마지막 업데이트**: 2026-01-14
