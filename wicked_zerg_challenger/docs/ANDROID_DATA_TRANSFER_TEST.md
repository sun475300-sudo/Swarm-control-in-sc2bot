# ? Android 앱 데이터 전달 테스트 가이드

**작성일**: 2026-01-14  
**목적**: Android 앱과 서버 간 데이터 전달이 정확한지 확인

---

## ? 테스트 목표

1. 서버가 정상적으로 실행 중인지 확인
2. API 엔드포인트가 올바른 데이터를 반환하는지 확인
3. Android 앱이 데이터를 정상적으로 받는지 확인
4. 데이터 형식이 Android 앱과 일치하는지 확인

---

## ? 사전 준비

### 1. 서버 실행 확인

```powershell
# 서버가 실행 중인지 확인
cd wicked_zerg_challenger\monitoring
python dashboard.py
```

또는:

```powershell
# FastAPI 서버 실행
python dashboard_api.py
```

**확인 사항**:
- 서버가 `http://localhost:8000`에서 실행 중이어야 함
- 브라우저에서 `http://localhost:8000/health` 접속 시 응답 확인

---

## ? 테스트 방법

### 방법 1: Python 스크립트로 테스트 (권장)

```powershell
cd wicked_zerg_challenger\monitoring
python test_mobile_app_data.py
```

**확인 사항**:
- ? 서버 상태: 정상
- ? `/api/game-state`: 데이터 반환 확인
- ? 데이터 형식: Android 앱과 일치

---

### 방법 2: 브라우저에서 직접 확인

1. **게임 상태 확인**
   - URL: `http://localhost:8000/api/game-state`
   - 예상 응답:
   ```json
   {
     "minerals": 50,
     "vespene": 0,
     "supply_used": 12,
     "supply_cap": 15,
     "units": {
       "zerglings": 0,
       "roaches": 0
     },
     "win_rate": 0.0
   }
   ```

2. **전투 통계 확인**
   - URL: `http://localhost:8000/api/combat-stats`

3. **학습 진행도 확인**
   - URL: `http://localhost:8000/api/learning-progress`

---

### 방법 3: Android 앱 로그 확인

#### Android Studio에서 로그 확인

1. **Logcat 열기**
   - Android Studio 하단의 "Logcat" 탭 클릭

2. **필터 설정**
   - 필터: `WickedZerg` 또는 `ApiClient`

3. **확인할 로그**
   ```
   ? 성공: "Connected" 메시지
   ? 실패: "Disconnected: [에러 메시지]"
   ```

#### MainActivity.kt에서 로그 추가

```kotlin
private fun startGameStateUpdates() {
    lifecycleScope.launch {
        while (true) {
            try {
                val gameState = apiClient.getGameState()
                Log.d("ApiClient", "Data received: $gameState")
                updateUI(gameState)
                statusText.text = "Connected"
            } catch (e: Exception) {
                Log.e("ApiClient", "Error: ${e.message}", e)
                statusText.text = "Disconnected: ${e.message}"
            }
            delay(1000)
        }
    }
}
```

---

## ? 데이터 형식 확인

### 서버 응답 형식 (snake_case)

```json
{
  "minerals": 50,
  "vespene": 0,
  "supply_used": 12,
  "supply_cap": 15,
  "units": {
    "zerglings": 0,
    "roaches": 0
  },
  "win_rate": 0.0
}
```

### Android 앱에서 필요한 형식 (camelCase)

```kotlin
data class GameState(
    val minerals: Int,
    val vespene: Int,
    val supplyUsed: Int,    // supply_used → supplyUsed
    val supplyCap: Int,     // supply_cap → supplyCap
    val units: Map<String, Int>,
    val winRate: Double     // win_rate → winRate
)
```

### 필드명 매핑 확인

| 서버 (snake_case) | Android (camelCase) | 상태 |
|-------------------|---------------------|------|
| `minerals` | `minerals` | ? 일치 |
| `vespene` | `vespene` | ? 일치 |
| `supply_used` | `supplyUsed` | ?? 변환 필요 |
| `supply_cap` | `supplyCap` | ?? 변환 필요 |
| `units` | `units` | ? 일치 |
| `win_rate` | `winRate` | ?? 변환 필요 |

**참고**: Gson이 자동으로 변환하므로 문제 없습니다.

---

## ? 문제 해결

### 문제 1: "Connection refused" 오류

**원인**: 서버가 실행되지 않음

**해결**:
```powershell
# 서버 실행
cd wicked_zerg_challenger\monitoring
python dashboard.py
```

---

### 문제 2: "Timeout" 오류

**원인**: 서버 응답이 느림 또는 네트워크 문제

**해결**:
1. 서버 로그 확인
2. 포트 8000이 다른 프로그램에서 사용 중인지 확인
3. 방화벽 설정 확인

---

### 문제 3: 데이터가 표시되지 않음

**원인**: 데이터 형식 불일치

**해결**:
1. 서버 응답 확인: `http://localhost:8000/api/game-state`
2. Android 앱의 GameState 모델 확인
3. 필드명 매핑 확인

---

### 문제 4: Android 에뮬레이터에서 연결 안 됨

**원인**: IP 주소 설정 오류

**해결**:
- Android 에뮬레이터는 `10.0.2.2`를 사용해야 함
- `ApiClient.kt`의 `BASE_URL` 확인:
  ```kotlin
  private val BASE_URL = "http://10.0.2.2:8000" // 에뮬레이터용
  ```

---

## ? 체크리스트

### 서버 측
- [ ] 서버가 `http://localhost:8000`에서 실행 중
- [ ] `/api/game-state` 엔드포인트 응답 확인
- [ ] 데이터 형식이 올바름 (JSON)
- [ ] CORS 설정 확인 (에뮬레이터 접근 허용)

### Android 앱 측
- [ ] `BASE_URL`이 `http://10.0.2.2:8000`로 설정됨
- [ ] 인터넷 권한이 `AndroidManifest.xml`에 있음
- [ ] `GameState` 모델이 서버 응답과 일치
- [ ] 로그에서 "Connected" 메시지 확인

### 데이터 확인
- [ ] `minerals` 값이 표시됨
- [ ] `vespene` 값이 표시됨
- [ ] `supply` 값이 표시됨
- [ ] `units` 값이 표시됨
- [ ] `winRate` 값이 표시됨

---

## ? 테스트 결과 예시

### 성공적인 테스트

```
? 서버 상태: 정상
? /api/game-state: 데이터 반환
? 데이터 형식 검증: 통과

? Android 앱에서 표시되는 데이터:
   - Minerals: 50
   - Vespene: 0
   - Supply: 12/15
   - Total Units: 2
   - Win Rate: 0.0%
   - Status: Connected
```

### 실패한 테스트

```
? 서버 상태: 연결 실패
   원인: 서버가 실행되지 않음
   해결: python dashboard.py 실행
```

---

## ? 추가 디버깅

### Android 앱에 상세 로그 추가

```kotlin
suspend fun getGameState(): GameState = withContext(Dispatchers.IO) {
    val request = Request.Builder()
        .url("$BASE_URL/api/game-state")
        .get()
        .build()
    
    Log.d("ApiClient", "Request URL: ${request.url}")
    
    val response = client.newCall(request).execute()
    
    Log.d("ApiClient", "Response code: ${response.code}")
    Log.d("ApiClient", "Response body: ${response.body?.string()}")
    
    // ... 나머지 코드
}
```

### 서버에 요청 로그 추가

```python
@app.get("/api/game-state")
async def get_game_state():
    logger.info("Game state requested")
    # ... 기존 코드
    logger.info(f"Returning game state: {state}")
    return state
```

---

## ? 관련 문서

- **모바일 앱 가이드**: `docs/MOBILE_APP_COMPLETE_GUIDE.md`
- **API 엔드포인트**: `monitoring/dashboard_api.py`
- **Android 앱 코드**: `monitoring/mobile_app_android/`

---

**마지막 업데이트**: 2026-01-14
