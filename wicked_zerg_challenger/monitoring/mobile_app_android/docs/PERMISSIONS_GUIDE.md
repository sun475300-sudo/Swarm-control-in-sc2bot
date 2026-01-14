# ? Android 앱 권한 가이드

**작성일**: 2026-01-14  
**목적**: Android 앱에 필요한 권한 및 런타임 권한 처리 가이드

---

## ? 권한 목록

### 1. 네트워크 권한 (자동 허용)

이 권한들은 설치 시 자동으로 허용됩니다:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
```

**용도**:
- API 호출 (서버와 통신)
- 네트워크 상태 확인
- Wi-Fi 상태 확인

---

### 2. 백그라운드 작업 권한 (자동 허용)

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
```

**용도**:
- 포그라운드 서비스 실행 (향후 확장)
- 화면 꺼짐 방지 (선택적)

---

### 3. 알림 권한 (런타임 요청 필요 - Android 13+)

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

**용도**:
- 푸시 알림 표시
- 게임 상태 변경 알림 (향후 확장)

**런타임 요청**: Android 13 (API 33) 이상에서 사용자에게 권한 요청

---

### 4. 진동 권한 (자동 허용)

```xml
<uses-permission android:name="android.permission.VIBRATE" />
```

**용도**:
- 알림 진동
- 피드백 진동

---

### 5. 위치 권한 (선택적, 향후 기능용)

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" android:maxSdkVersion="32" />
```

**용도**:
- 위치 기반 기능 (향후 확장)
- 현재는 사용하지 않음

---

## ? 런타임 권한 처리

### MainActivity.kt 구현

`MainActivity.kt`에 다음 기능이 구현되어 있습니다:

1. **권한 확인**: 앱 시작 시 필요한 권한 확인
2. **권한 요청**: 권한이 없으면 사용자에게 요청
3. **결과 처리**: 권한 요청 결과 처리
4. **거부 메시지**: 권한이 거부되면 사용자에게 안내

### 코드 구조

```kotlin
class MainActivity : AppCompatActivity() {
    companion object {
        private const val PERMISSION_REQUEST_CODE = 1001
        private val REQUIRED_PERMISSIONS = mutableListOf<String>().apply {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // ...
        checkAndRequestPermissions()
    }
    
    private fun checkAndRequestPermissions() {
        // 권한 확인 및 요청 로직
    }
    
    override fun onRequestPermissionsResult(...) {
        // 권한 요청 결과 처리
    }
}
```

---

## ? 사용자 경험

### 권한 요청 흐름

1. **앱 시작**: `onCreate()`에서 권한 확인
2. **권한 없음**: 사용자에게 권한 요청 다이얼로그 표시
3. **권한 허용**: 정상 작동
4. **권한 거부**: Snackbar로 안내 메시지 표시

### 권한 요청 다이얼로그 예시

```
앱이 알림을 표시하려고 합니다.

[거부] [허용]
```

---

## ?? 개발자 가이드

### 권한 추가 방법

1. **AndroidManifest.xml에 권한 추가**:
   ```xml
   <uses-permission android:name="android.permission.YOUR_PERMISSION" />
   ```

2. **MainActivity.kt에 런타임 권한 추가** (필요한 경우):
   ```kotlin
   private val REQUIRED_PERMISSIONS = mutableListOf<String>().apply {
       add(Manifest.permission.YOUR_PERMISSION)
   }
   ```

3. **권한 사용 코드 추가**:
   ```kotlin
   if (ContextCompat.checkSelfPermission(this, Manifest.permission.YOUR_PERMISSION)
       == PackageManager.PERMISSION_GRANTED) {
       // 권한이 있으면 실행
   } else {
       // 권한 요청
       ActivityCompat.requestPermissions(...)
   }
   ```

---

## ? 권한 확인 체크리스트

### 필수 권한 (자동 허용)
- [x] `INTERNET` - API 호출
- [x] `ACCESS_NETWORK_STATE` - 네트워크 상태 확인
- [x] `ACCESS_WIFI_STATE` - Wi-Fi 상태 확인

### 런타임 권한 (사용자 승인 필요)
- [x] `POST_NOTIFICATIONS` - 알림 (Android 13+)

### 선택적 권한 (향후 확장)
- [ ] `ACCESS_FINE_LOCATION` - 정확한 위치
- [ ] `ACCESS_COARSE_LOCATION` - 대략적인 위치

---

## ? 문제 해결

### 권한이 작동하지 않을 때

1. **AndroidManifest.xml 확인**:
   - 권한이 올바르게 선언되어 있는지 확인
   - `<uses-permission>` 태그가 `<manifest>` 내부에 있는지 확인

2. **런타임 권한 확인**:
   - Android 6.0+ (API 23+)에서 런타임 권한이 필요한지 확인
   - `MainActivity.kt`에 권한 요청 코드가 있는지 확인

3. **권한 상태 확인**:
   ```kotlin
   val hasPermission = ContextCompat.checkSelfPermission(
       this,
       Manifest.permission.POST_NOTIFICATIONS
   ) == PackageManager.PERMISSION_GRANTED
   ```

### 권한 거부 시 처리

1. **사용자 안내**: Snackbar로 메시지 표시
2. **설정 화면 이동**: 사용자가 직접 권한을 허용할 수 있도록 안내
3. **기능 비활성화**: 권한이 없어도 앱이 작동하도록 처리

---

## ? 참고 자료

- **Android 권한 가이드**: https://developer.android.com/training/permissions/requesting
- **런타임 권한**: https://developer.android.com/training/permissions/usage-notes
- **권한 모범 사례**: https://developer.android.com/training/permissions/best-practices

---

## ? 요약

### 현재 구현된 권한

1. ? **네트워크 권한** - 자동 허용
2. ? **알림 권한** - 런타임 요청 (Android 13+)
3. ? **백그라운드 작업 권한** - 자동 허용
4. ? **진동 권한** - 자동 허용

### 향후 확장 가능한 권한

- 위치 권한 (선택적)
- 카메라 권한 (선택적)
- 저장소 권한 (선택적)

---

**마지막 업데이트**: 2026-01-14
