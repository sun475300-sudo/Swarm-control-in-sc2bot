# ? Ngrok 빠른 시작 가이드

**작성일**: 2026-01-14

---

## ? 3단계로 시작하기

### 1단계: Ngrok 설치

```bash
# 다운로드: https://ngrok.com/download
# Windows: ngrok.exe를 PATH에 추가하거나 프로젝트 폴더에 배치
```

**설치 확인**:
```bash
ngrok version
```

---

### 2단계: 인증 토큰 설정 (선택적, 권장)

```powershell
# 1. 토큰 발급: https://dashboard.ngrok.com/get-started/your-authtoken
# 2. 토큰 저장
echo YOUR_TOKEN > secrets\ngrok_auth.txt
```

---

### 3단계: 자동 시작

```bash
# 대시보드 서버 + Ngrok 터널 함께 시작
bat\start_dashboard_with_ngrok.bat
```

**출력 예시**:
```
========================================
대시보드 서버 + Ngrok 터널 자동 시작
========================================

[1/2] 대시보드 서버 시작...
  ? 대시보드 서버 시작됨: http://localhost:8000

[2/2] Ngrok 터널 시작...
  ? Ngrok 터널 시작됨: https://xxxx-xx-xx-xx-xx.ngrok.io

========================================
외부 접속 정보
========================================
터널 URL: https://xxxx-xx-xx-xx-xx.ngrok.io
로컬 URL: http://localhost:8000

Android 앱 설정:
  BASE_URL = "https://xxxx-xx-xx-xx-xx.ngrok.io"
```

---

## ? Android 앱 설정

### 터널 URL 확인

```bash
# 방법 1: 터미널 출력 확인
# 방법 2: 파일에서 읽기
type monitoring\.ngrok_url.txt

# 방법 3: API로 확인
curl http://localhost:8000/api/ngrok-url
```

### Android 앱 코드 수정

```kotlin
// ApiClient.kt
class ApiClient {
    // Ngrok URL 사용
    private val BASE_URL = "https://xxxx-xx-xx-xx-xx.ngrok.io"
    
    // 또는 동적으로 가져오기
    private val BASE_URL = getNgrokUrl() ?: "http://10.0.2.2:8000"
    
    private suspend fun getNgrokUrl(): String? {
        // /api/ngrok-url 엔드포인트 호출
    }
}
```

---

## ? 상태 확인

### Ngrok 웹 UI

터널 실행 중:
```
http://127.0.0.1:4040
```

### Python 스크립트

```bash
python monitoring\get_ngrok_url.py
```

---

## ? 문제 해결

### Ngrok이 시작되지 않을 때

1. 설치 확인: `ngrok version`
2. 포트 확인: `netstat -ano | findstr :8000`
3. 인증 토큰 확인: `python -c "from tools.load_api_key import load_api_key; print(load_api_key('NGROK_AUTH_TOKEN'))"`

### Android 앱 연결 실패

1. HTTPS 사용 확인 (Ngrok은 HTTPS만 제공)
2. CORS 설정 확인 (ngrok 도메인 허용)
3. 네트워크 권한 확인

---

## ? 상세 가이드

- **전체 가이드**: `docs/NGROK_LTE_5G_SETUP.md`
- **대시보드 아키텍처**: `docs/DASHBOARD_MONITORING_SYSTEM_ARCHITECTURE.md`

---

**마지막 업데이트**: 2026-01-14
