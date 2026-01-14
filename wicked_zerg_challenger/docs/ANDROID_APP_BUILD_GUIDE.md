# Android 앱 빌드 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **Android 앱 프로젝트 생성 완료**

---

## ? Android 앱 프로젝트 구조

Android 앱 프로젝트가 `monitoring/mobile_app_android/` 폴더에 생성되었습니다.

### 프로젝트 구조

```
mobile_app_android/
├── app/
│   ├── src/main/
│   │   ├── java/com/wickedzerg/mobilegcs/
│   │   │   ├── MainActivity.kt          # 메인 액티비티
│   │   │   ├── api/
│   │   │   │   └── ApiClient.kt        # API 통신 클라이언트
│   │   │   └── models/
│   │   │       └── GameState.kt        # 게임 상태 데이터 모델
│   │   ├── res/
│   │   │   ├── layout/
│   │   │   │   └── activity_main.xml   # 메인 레이아웃
│   │   │   ├── values/
│   │   │   │   ├── strings.xml
│   │   │   │   ├── colors.xml
│   │   │   │   └── themes.xml
│   │   │   └── mipmap/
│   │   │       └── ic_launcher.png     # 앱 아이콘
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

---

## ? 빌드 방법

### 방법 1: Android Studio 사용 (권장)

1. **Android Studio 설치**
   - https://developer.android.com/studio
   - Android Studio 2023.1 이상 권장

2. **프로젝트 열기**
   - Android Studio 실행
   - "Open" 선택
   - `monitoring/mobile_app_android` 폴더 선택
   - Gradle 동기화 대기 (자동으로 시작됨)

3. **빌드 및 실행**
   - 상단 툴바에서 "Run" 버튼 클릭 (▶?)
   - 또는 `Shift + F10` (Windows/Linux) / `Ctrl + R` (Mac)

### 방법 2: 명령줄 사용 (Gradle)

#### Windows (PowerShell/CMD)

```powershell
cd monitoring\mobile_app_android

# Debug APK 빌드
.\gradlew.bat assembleDebug

# 또는 Gradle Wrapper가 없으면
gradle assembleDebug
```

#### Linux/Mac

```bash
cd monitoring/mobile_app_android

# Debug APK 빌드
./gradlew assembleDebug

# 실행 권한 부여 (처음 한 번만)
chmod +x gradlew
```

**생성된 APK 위치**:
```
app/build/outputs/apk/debug/app-debug.apk
```

---

## ?? 필수 설정

### 1. 서버 IP 주소 설정

`app/src/main/java/com/wickedzerg/mobilegcs/api/ApiClient.kt` 파일을 열고:

```kotlin
// TODO: Change this to your PC's IP address
// Find your IP: ipconfig (Windows) or ifconfig (Linux/Mac)
private val BASE_URL = "http://192.168.0.100:8000"  // 여기를 수정하세요
```

**PC의 IP 주소 확인 방법**:
- **Windows**: `ipconfig` 실행 → IPv4 주소 확인
- **Linux/Mac**: `ifconfig` 또는 `ip addr` 실행

### 2. 인터넷 권한

`AndroidManifest.xml`에 이미 포함되어 있습니다:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

### 3. HTTP 연결 허용 (Android 9+)

`AndroidManifest.xml`에 이미 포함되어 있습니다:
```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## ? 의존성

주요 라이브러리 (자동으로 다운로드됨):

- **OkHttp 4.12.0** - HTTP 클라이언트
- **Gson 2.10.1** - JSON 파싱
- **Kotlin Coroutines 1.7.3** - 비동기 처리
- **AndroidX Lifecycle 2.7.0** - Lifecycle 관리
- **Material Components 1.11.0** - UI 컴포넌트

---

## ? 개발 가이드

### 주요 파일 설명

1. **MainActivity.kt**
   - 앱의 메인 화면
   - 1초마다 게임 상태를 업데이트
   - UI 업데이트 로직 포함

2. **ApiClient.kt**
   - REST API 통신 담당
   - `/api/game-state`, `/api/combat-stats`, `/api/learning-progress` 호출
   - Coroutines를 사용한 비동기 처리

3. **GameState.kt**
   - 게임 상태 데이터 모델
   - JSON 파싱을 위한 Gson 어노테이션 포함

4. **activity_main.xml**
   - 메인 화면 레이아웃
   - SC2 테마 색상 적용 (#16213e 배경, #00ff00 텍스트)

### API 엔드포인트

앱이 사용하는 API:
- `GET /api/game-state` - 현재 게임 상태
- `GET /api/combat-stats` - 전투 통계
- `GET /api/learning-progress` - 학습 진행 상황

---

## ? 앱 설치

### 방법 1: Android Studio에서 직접 설치

1. USB로 Android 기기 연결
2. 기기에서 "USB 디버깅" 활성화
3. Android Studio에서 "Run" 버튼 클릭
4. 기기 선택 후 설치

### 방법 2: APK 파일 직접 설치

1. **APK 생성**:
   ```bash
   ./gradlew assembleDebug
   ```

2. **APK 전송**:
   - USB로 기기에 복사
   - 또는 이메일/클라우드로 전송

3. **설치**:
   - 기기에서 APK 파일 열기
   - "알 수 없는 소스" 허용 (필요한 경우)
   - 설치 진행

---

## ? 기능

### 현재 구현된 기능

- ? 실시간 게임 상태 모니터링 (1초마다 업데이트)
- ? 자원 표시 (미네랄, 가스, 인구수)
- ? 유닛 수 표시
- ? 승률 통계
- ? 연결 상태 표시

### 향후 추가 가능한 기능

- [ ] 유닛 구성 상세 표시 (저글링, 로치, 히드라리스크 등)
- [ ] 전투 통계 탭
- [ ] 학습 진행 상황 탭
- [ ] 차트/그래프 (승률 추이 등)
- [ ] 알림 기능 (게임 종료, 승리 등)
- [ ] 다크 모드/라이트 모드 전환

---

## ? 문제 해결

### Gradle 동기화 실패

1. **인터넷 연결 확인**: Gradle이 의존성을 다운로드해야 함
2. **프록시 설정**: 회사 네트워크인 경우 프록시 설정 필요
3. **Gradle 버전 확인**: `gradle/wrapper/gradle-wrapper.properties` 확인

### 빌드 오류

1. **SDK 버전 확인**: `compileSdk = 34` 확인
2. **JDK 버전 확인**: JDK 17 이상 필요
3. **의존성 충돌**: `./gradlew clean` 후 재빌드

### 앱이 서버에 연결되지 않음

1. **IP 주소 확인**: `ApiClient.kt`의 `BASE_URL` 확인
2. **방화벽 확인**: PC의 방화벽에서 포트 8000 허용
3. **같은 네트워크**: PC와 모바일이 같은 Wi-Fi에 연결되어 있는지 확인
4. **서버 실행 확인**: `python monitoring/dashboard.py`가 실행 중인지 확인

### HTTP 연결 오류 (Android 9+)

`AndroidManifest.xml`에 다음이 포함되어 있는지 확인:
```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

---

## ? 참고 자료

- **Android 개발자 문서**: https://developer.android.com
- **Kotlin 문서**: https://kotlinlang.org/docs/home.html
- **OkHttp 문서**: https://square.github.io/okhttp/
- **Gson 문서**: https://github.com/google/gson

---

## ? 완료!

이제 Android 앱이 준비되었습니다. 다음 단계:

1. Android Studio에서 프로젝트 열기
2. `ApiClient.kt`에서 서버 IP 주소 설정
3. 빌드 및 실행
4. 모바일 기기에 설치

---

**참고**: PWA 버전도 사용 가능합니다. `docs/MOBILE_GCS_QUICK_START.md`를 참조하세요.
