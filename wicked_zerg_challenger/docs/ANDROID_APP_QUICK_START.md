# Android 앱 빠른 시작 가이드

**작성 일시**: 2026-01-14  
**상태**: ? **Android 앱 프로젝트 생성 완료**

---

## ? 3단계로 Android 앱 빌드하기

### 1단계: Android Studio 설치

1. **Android Studio 다운로드**
   - https://developer.android.com/studio
   - Android Studio 2023.1 이상 권장

2. **설치 및 설정**
   - 설치 마법사 따라하기
   - Android SDK 자동 다운로드 (시간 소요)

---

### 2단계: 프로젝트 열기

1. **Android Studio 실행**
2. **"Open" 선택**
3. **프로젝트 폴더 선택**:
   ```
   D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
   ```
4. **Gradle 동기화 대기** (자동으로 시작됨, 몇 분 소요)

---

### 3단계: 서버 IP 설정 및 빌드

#### 서버 IP 주소 설정

1. **파일 열기**:
   ```
   app/src/main/java/com/wickedzerg/mobilegcs/api/ApiClient.kt
   ```

2. **IP 주소 수정**:
   ```kotlin
   // TODO: Change this to your PC's IP address
   private val BASE_URL = "http://192.168.0.100:8000"  // 여기를 수정
   ```

3. **PC의 IP 주소 확인**:
   ```powershell
   ipconfig
   # IPv4 주소 확인 (예: 192.168.0.100)
   ```

#### 빌드 및 실행

1. **USB로 Android 기기 연결**
2. **기기에서 "USB 디버깅" 활성화**
3. **Android Studio에서 "Run" 버튼 클릭** (▶?)
4. **기기 선택 후 설치**

---

## ? APK 파일 직접 빌드

### 방법 1: Android Studio

1. **Build > Build Bundle(s) / APK(s) > Build APK(s)**
2. **APK 위치**: `app/build/outputs/apk/debug/app-debug.apk`

### 방법 2: 명령줄

```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# Gradle Wrapper 초기화 (처음 한 번만)
# Android Studio에서 프로젝트를 열면 자동으로 생성됨

# 빌드
.\gradlew.bat assembleDebug
```

**APK 위치**: `app/build/outputs/apk/debug/app-debug.apk`

---

## ?? 필수 설정

### 1. 서버 IP 주소

`ApiClient.kt`에서 서버 IP를 설정하세요:
```kotlin
private val BASE_URL = "http://YOUR_PC_IP:8000"
```

### 2. 대시보드 서버 실행

앱이 작동하려면 대시보드 서버가 실행 중이어야 합니다:

```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
python dashboard.py
```

### 3. 방화벽 설정

Windows 방화벽에서 포트 8000을 허용하세요:
1. Windows 보안 > 방화벽 및 네트워크 보호
2. 고급 설정 > 인바운드 규칙 > 새 규칙
3. 포트 > TCP > 8000 > 허용

---

## ? 문제 해결

### Gradle 동기화 실패

1. **인터넷 연결 확인**: Gradle이 의존성을 다운로드해야 함
2. **프록시 설정**: 회사 네트워크인 경우 설정 필요
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

---

## ? 앱 기능

### 현재 구현된 기능

- ? 실시간 게임 상태 모니터링 (1초마다 업데이트)
- ? 자원 표시 (미네랄, 가스, 인구수)
- ? 유닛 수 표시
- ? 승률 통계
- ? 연결 상태 표시

### UI 특징

- SC2 테마 색상 (#16213e 배경, #00ff00 텍스트)
- 카드 기반 레이아웃
- 실시간 업데이트
- 연결 상태 표시

---

## ? 상세 가이드

더 자세한 내용은 다음 문서를 참조하세요:
- **빌드 가이드**: `docs/ANDROID_APP_BUILD_GUIDE.md`
- **프로젝트 README**: `monitoring/mobile_app_android/README.md`

---

## ? 완료!

이제 Android 앱이 준비되었습니다. 다음 단계:

1. Android Studio에서 프로젝트 열기
2. `ApiClient.kt`에서 서버 IP 주소 설정
3. 빌드 및 실행
4. 모바일 기기에 설치

---

**참고**: PWA 버전도 사용 가능합니다. `docs/MOBILE_GCS_QUICK_START.md`를 참조하세요.
