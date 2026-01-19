# 서버 로그 메시지 가이드

**작성일**: 2026-01-17

---

## ? 서버 시작 로그 해석

### 1. `Started server process [1760]`

**의미**: 서버 프로세스가 시작되었습니다.

**상세 설명**:
- `[1760]`: 운영체제가 할당한 **프로세스 ID (PID)**
- Windows 작업 관리자에서 프로세스 확인 시 이 번호로 찾을 수 있습니다
- 서버 종료 시 이 PID를 사용할 수 있습니다

**예시**:
```powershell
# 프로세스 확인
Get-Process -Id 1760

# 프로세스 종료 (필요시)
Stop-Process -Id 1760
```

---

### 2. `INFO: Waiting for application startup.`

**의미**: FastAPI 애플리케이션이 초기화되는 중입니다.

**이 단계에서 수행되는 작업**:
- CORS 미들웨어 설정
- 데이터베이스 연결 (있는 경우)
- 외부 API 클라이언트 초기화 (Manus 등)
- 캐시 초기화
- 환경 변수 로드

**주의**: 이 단계에서 오류가 발생하면 서버가 시작되지 않습니다.

---

### 3. `INFO: Application startup complete.`

**의미**: 애플리케이션 초기화가 완료되었습니다.

**의미**:
- ? 모든 설정이 완료되었습니다
- ? 이제 HTTP 요청을 처리할 수 있는 상태입니다
- ? 클라이언트가 접속할 수 있습니다

**다음 단계**: 서버는 이제 요청을 기다립니다 (`Uvicorn running...`).

---

### 4. `INFO: Uvicorn running on http://0.0.0.0:8000`

**의미**: Uvicorn 서버가 포트 8000에서 실행 중입니다.

**상세 설명**:
- **`0.0.0.0`**: 모든 네트워크 인터페이스에서 접속 가능
  - `localhost` (127.0.0.1)
  - PC의 로컬 IP (예: 192.168.1.100)
  - Android 에뮬레이터 (10.0.2.2)
  
- **`8000`**: HTTP 요청을 받는 포트 번호

**접속 가능한 URL**:
- `http://localhost:8000`
- `http://127.0.0.1:8000`
- `http://YOUR_PC_IP:8000` (같은 네트워크의 다른 기기)

---

### 5. `INFO: 127.0.0.1:59129 - "GET /docs HTTP/1.1" 200 OK`

**의미**: 클라이언트가 `/docs` 엔드포인트에 요청했고 성공했습니다.

**상세 설명**:
- **`127.0.0.1:59129`**: 클라이언트 정보
  - `127.0.0.1`: 클라이언트 IP 주소 (localhost)
  - `59129`: 클라이언트가 사용한 포트 번호

- **`GET /docs`**: HTTP 요청 정보
  - `GET`: HTTP 메서드 (데이터 조회)
  - `/docs`: 요청한 엔드포인트 (Swagger UI 문서 페이지)

- **`HTTP/1.1`**: 사용된 HTTP 프로토콜 버전

- **`200 OK`**: HTTP 응답 코드
  - `200`: 요청 성공
  - `OK`: 성공 메시지

---

## ? HTTP 응답 코드 의미

| 코드 | 의미 | 설명 |
|------|------|------|
| **200** | OK | 요청 성공 |
| **404** | Not Found | 요청한 리소스를 찾을 수 없음 |
| **500** | Internal Server Error | 서버 내부 오류 |
| **400** | Bad Request | 잘못된 요청 |
| **401** | Unauthorized | 인증 필요 |
| **403** | Forbidden | 권한 없음 |

---

## ? 일반적인 로그 패턴

### 정상적인 시작 로그
```
Started server process [1760]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 요청 처리 로그
```
INFO:     127.0.0.1:59129 - "GET /docs HTTP/1.1" 200 OK
INFO:     127.0.0.1:59130 - "GET /api/game-state HTTP/1.1" 200 OK
INFO:     127.0.0.1:59131 - "GET /health HTTP/1.1" 200 OK
```

### 오류 로그
```
ERROR:    Exception in ASGI application
ERROR:    500 Internal Server Error
WARNING:  ?? Manus dashboard client not available
```

---

## ?? 유용한 명령어

### 프로세스 확인
```powershell
# 특정 PID 확인
Get-Process -Id 1760

# Python 프로세스 확인
Get-Process python | Where-Object { $_.Id -eq 1760 }
```

### 포트 확인
```powershell
# 포트 8000 사용 중인 프로세스 확인
Get-NetTCPConnection -LocalPort 8000

# 특정 PID의 네트워크 연결 확인
Get-NetTCPConnection | Where-Object { $_.OwningProcess -eq 1760 }
```

### 서버 종료
```powershell
# Ctrl+C 또는
Stop-Process -Id 1760
```

---

## ? 요약

| 로그 메시지 | 의미 | 상태 |
|------------|------|------|
| `Started server process [PID]` | 서버 프로세스 시작 | ? 정상 |
| `Waiting for application startup` | 애플리케이션 초기화 중 | ? 정상 |
| `Application startup complete` | 초기화 완료 | ? 정상 |
| `Uvicorn running on http://0.0.0.0:8000` | 서버 실행 중 | ? 정상 |
| `127.0.0.1:PORT - "METHOD /path HTTP/1.1" 200` | 요청 처리 성공 | ? 정상 |
| `... - "... " 404` | 리소스를 찾을 수 없음 | ?? 확인 필요 |
| `... - "... " 500` | 서버 오류 | ? 오류 |

---

## ? 참고

- **Swagger UI**: `http://localhost:8000/docs`
- **API 엔드포인트**: `http://localhost:8000/api/game-state`
- **Health Check**: `http://localhost:8000/health`

---

## ? 팁

1. **서버가 정상적으로 시작되었는지 확인**: 
   - `Application startup complete` 메시지 확인
   - `Uvicorn running on...` 메시지 확인

2. **요청이 성공했는지 확인**:
   - HTTP 응답 코드가 `200`인지 확인
   - `404`는 엔드포인트 오류, `500`은 서버 오류

3. **로그 모니터링**:
   - `WARNING` 메시지는 기능이 비활성화되었거나 주의가 필요함을 의미
   - `ERROR` 메시지는 즉시 확인이 필요함을 의미
