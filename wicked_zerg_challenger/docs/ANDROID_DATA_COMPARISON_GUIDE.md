# ? Android 앱과 서버 데이터 비교 가이드

**작성일**: 2026-01-14  
**목적**: Android 에뮬레이터 로그의 JSON 데이터와 PC 서버 데이터 일치 여부 확인

---

## ? 목표

Android 앱이 서버로부터 받은 JSON 데이터가 서버가 실제로 보내는 데이터와 일치하는지 확인합니다.

---

## ? 준비 사항

### 1. 서버 실행

```powershell
cd wicked_zerg_challenger\monitoring
python dashboard.py
```

**확인**: `http://localhost:8000/api/game-state` 접속 시 JSON 응답 확인

---

### 2. Android 앱 실행

1. Android Studio에서 앱 실행
2. Logcat 열기 (하단 탭)
3. 필터 설정:
   - 태그: `ApiClient` 또는 `WickedZerg`
   - 레벨: `Debug` 이상

---

## ? 비교 방법

### 방법 1: 자동 비교 스크립트 (권장)

#### 1단계: Android 로그 저장

1. Android Studio Logcat에서 JSON 데이터 복사
2. 텍스트 파일로 저장 (예: `android_log.txt`)

**로그에서 찾을 내용**:
```
=== 서버에서 받은 원본 JSON ===
{
  "minerals": 50,
  "vespene": 0,
  ...
}
=============================
```

또는:

```
=== Android 앱에서 받은 JSON 데이터 ===
{
  "minerals": 50,
  "vespene": 0,
  ...
}
=====================================
```

#### 2단계: 비교 스크립트 실행

```powershell
cd wicked_zerg_challenger\monitoring
python compare_server_android_data.py
```

스크립트가 Android 로그 파일 경로를 요청하면 저장한 파일 경로 입력

---

### 방법 2: 수동 비교

#### 1단계: 서버 데이터 확인

**브라우저에서**:
- URL: `http://localhost:8000/api/game-state`
- 응답 JSON 복사

**또는 PowerShell에서**:
```powershell
cd wicked_zerg_challenger\monitoring
python -c "import requests; import json; print(json.dumps(requests.get('http://localhost:8000/api/game-state').json(), indent=2, ensure_ascii=False))"
```

#### 2단계: Android 로그 확인

Android Studio Logcat에서:
- 필터: `ApiClient` 또는 `WickedZerg`
- JSON 데이터 복사

#### 3단계: 비교

두 JSON을 비교하여 다음을 확인:

1. **필드 존재 여부**
   - 서버: `supply_used`, `supply_cap`, `win_rate`
   - Android: `supplyUsed`, `supplyCap`, `winRate` (camelCase)

2. **값 일치 여부**
   - `minerals`, `vespene` 값이 동일한지
   - `units` 객체의 내용이 동일한지

3. **타입 일치 여부**
   - 숫자는 숫자로, 문자열은 문자열로

---

## ? 예상 결과

### 정상적인 경우

**서버 응답**:
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

**Android 로그 (원본 JSON)**:
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

**Android 로그 (변환된 GameState)**:
```json
{
  "minerals": 50,
  "vespene": 0,
  "supplyUsed": 12,
  "supplyCap": 15,
  "units": {
    "zerglings": 0,
    "roaches": 0
  },
  "winRate": 0.0
}
```

**결과**: ? 완벽하게 일치 (필드명만 camelCase로 변환됨)

---

## ? 문제 해결

### 문제 1: 필드가 다름

**증상**: 서버에는 `supply_used`가 있는데 Android에는 없음

**원인**: Gson 필드명 매핑 문제

**해결**:
1. `GameState.kt`에 `@SerializedName` 어노테이션 추가:
```kotlin
data class GameState(
    val minerals: Int,
    val vespene: Int,
    @SerializedName("supply_used") val supplyUsed: Int,
    @SerializedName("supply_cap") val supplyCap: Int,
    val units: Map<String, Int>,
    @SerializedName("win_rate") val winRate: Double
)
```

---

### 문제 2: 값이 다름

**증상**: 서버는 `minerals: 50`인데 Android는 `minerals: 0`

**원인**: 
1. 서버가 다른 데이터를 보냄
2. Android 앱이 캐시된 데이터 사용

**해결**:
1. 서버 재시작
2. Android 앱 재시작
3. 네트워크 연결 확인

---

### 문제 3: 타입이 다름

**증상**: 서버는 `minerals: 50` (int)인데 Android는 `minerals: "50"` (string)

**원인**: JSON 파싱 오류

**해결**:
1. 서버 응답 형식 확인
2. Android `GameState.kt` 타입 확인

---

## ? 체크리스트

### 서버 측
- [ ] 서버가 `http://localhost:8000`에서 실행 중
- [ ] `/api/game-state` 엔드포인트 응답 확인
- [ ] JSON 형식이 올바름

### Android 앱 측
- [ ] Logcat에서 JSON 로그 확인
- [ ] `ApiClient` 태그로 필터링
- [ ] "=== 서버에서 받은 원본 JSON ===" 로그 확인

### 비교
- [ ] 필드 존재 여부 확인
- [ ] 값 일치 여부 확인
- [ ] 타입 일치 여부 확인

---

## ? 추가 디버깅

### Android 앱에 상세 로그 추가

`MainActivity.kt`에 이미 로그가 추가되어 있습니다:
- `WickedZerg` 태그로 원본 JSON 출력
- `ApiClient` 태그로 서버 응답 로그 출력

### 서버에 요청 로그 추가

`dashboard.py`에 로그 추가:
```python
if self.path == '/api/game-state':
    print(f"[API] Game state requested from {self.client_address}")
    payload = _build_game_state(base_dir)
    print(f"[API] Sending: {json.dumps(payload, ensure_ascii=False)}")
    # ... 기존 코드
```

---

## ? 관련 문서

- **데이터 전달 테스트**: `docs/ANDROID_DATA_TRANSFER_TEST.md`
- **빠른 시작**: `docs/ANDROID_DATA_TEST_QUICK_START.md`
- **모바일 앱 가이드**: `docs/MOBILE_APP_COMPLETE_GUIDE.md`

---

**마지막 업데이트**: 2026-01-14
