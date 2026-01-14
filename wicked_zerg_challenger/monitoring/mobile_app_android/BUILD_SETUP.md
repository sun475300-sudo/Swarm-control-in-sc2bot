# Android Studio 빌드 설정 가이드

**작성일**: 2026-01-15  
**목적**: Android Studio에서 프로젝트를 성공적으로 빌드하기 위한 필수 설정

---

## ⚠️ 프로젝트가 열리지 않는 경우

Android Studio에서 프로젝트가 열리지 않는다면 다음을 확인하세요:

### 문제 1: Gradle Wrapper 파일 누락

**증상**: "Gradle sync failed" 또는 프로젝트가 인식되지 않음

**해결 방법**:
1. **방법 1: Android Studio에서 자동 생성** (권장)
   - Android Studio 실행
   - File > New > New Project
   - Empty Activity 선택
   - 프로젝트 이름: `MobileGCS` (임시)
   - Finish 클릭
   - 생성된 프로젝트의 `gradle/wrapper/gradle-wrapper.jar` 파일을 복사
   - `wicked_zerg_challenger/monitoring/mobile_app_android/gradle/wrapper/` 폴더에 붙여넣기

2. **방법 2: Gradle 명령어로 생성**
   ```bash
   cd wicked_zerg_challenger/monitoring/mobile_app_android
   gradle wrapper --gradle-version 8.13
   ```

3. **방법 3: 수동 다운로드**
   - https://services.gradle.org/distributions/gradle-8.13-bin.zip 다운로드
   - 압축 해제 후 `gradle-8.13/lib/gradle-wrapper-*.jar` 파일을
   - `gradle/wrapper/gradle-wrapper.jar`로 복사

### 문제 2: 프로젝트 루트 디렉토리 확인

**중요**: Android Studio에서 열 때는 **`mobile_app_android` 폴더**를 직접 열어야 합니다.

**올바른 방법**:
1. Android Studio 실행
2. File > Open
3. `d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android` 선택
4. **주의**: 상위 폴더(`monitoring` 또는 `wicked_zerg_challenger`)를 열지 마세요!

### 문제 3: Android Studio 버전 호환성

**필수 요구사항**:
- Android Studio Hedgehog (2023.1.1) 이상
- 또는 Android Studio Iguana (2024.1.1) 이상

**확인 방법**:
- Help > About에서 버전 확인

---

## 필수 설정 단계

### 1. local.properties 파일 생성

Android Studio는 자동으로 `local.properties` 파일을 생성하지만, 수동으로도 생성할 수 있습니다.

**위치**: 프로젝트 루트 (`mobile_app_android/local.properties`)

**내용**:
```properties
# Android SDK 경로 (Windows 예시)
sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk

# Gemini API Key (선택사항, BuildConfig에서 사용)
# 주의: API 키가 만료되면 "API key expired" 오류 발생
# 해결: https://makersuite.google.com/app/apikey 에서 새 키 발급
# 또는 앱에서 사용하지 않는다면 이 줄을 삭제해도 됩니다
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

**⚠️ API 키 만료 오류 발생 시**:
- `API_KEY_FIX.md` 파일 참조
- 또는 `local.properties`에서 `GEMINI_API_KEY` 줄 삭제 (앱에서 사용하지 않는 경우)

**참고**: 
- `local.properties.example` 파일을 복사하여 `local.properties`로 이름 변경
- SDK 경로는 Android Studio의 Settings > Appearance & Behavior > System Settings > Android SDK에서 확인 가능
- `local.properties`는 `.gitignore`에 포함되어 있어 Git에 커밋되지 않습니다

---

### 2. Android SDK 설치 확인

Android Studio에서 다음 SDK 버전이 설치되어 있어야 합니다:

- **Android SDK Platform 34** (compileSdk = 34)
- **Android SDK Build-Tools** (최신 버전)
- **Android SDK Platform-Tools**

**확인 방법**:
1. Android Studio > Settings > Appearance & Behavior > System Settings > Android SDK
2. SDK Platforms 탭에서 "Android 14.0 (API 34)" 체크 확인
3. SDK Tools 탭에서 필요한 도구들 확인

---

### 3. Gradle 동기화

프로젝트를 열면 Android Studio가 자동으로 Gradle 동기화를 시도합니다.

**수동 동기화**:
- File > Sync Project with Gradle Files
- 또는 상단의 "Sync Now" 버튼 클릭

**문제 발생 시**:
```bash
# 터미널에서 수동 동기화
cd wicked_zerg_challenger/monitoring/mobile_app_android
./gradlew --refresh-dependencies
```

---

### 4. 프로젝트 구조 확인

올바른 Android 프로젝트 구조:

```
mobile_app_android/
├── app/
│   ├── src/
│   │   └── main/
│   │       ├── java/          # Kotlin 소스 코드
│   │       ├── res/           # 리소스 파일
│   │       ├── assets/        # assets 파일 (client_secret.json 등)
│   │       └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
├── settings.gradle.kts
├── gradle.properties
├── local.properties          # 로컬 설정 (Git에 커밋 안 됨)
└── gradle/
    └── wrapper/
        └── gradle-wrapper.properties
```

---

## 일반적인 빌드 오류 해결

### 오류 1: "SDK location not found"

**원인**: `local.properties` 파일이 없거나 SDK 경로가 잘못됨

**해결**:
1. `local.properties` 파일 생성 (위 1단계 참조)
2. SDK 경로 확인 및 수정

---

### 오류 2: "Failed to resolve: androidx.core:core-ktx"

**원인**: 인터넷 연결 문제 또는 저장소 설정 문제

**해결**:
1. 인터넷 연결 확인
2. `settings.gradle.kts`에서 저장소 설정 확인:
   ```kotlin
   repositories {
       google()
       mavenCentral()
   }
   ```
3. Gradle 캐시 정리:
   ```bash
   ./gradlew clean
   ./gradlew --refresh-dependencies
   ```

---

### 오류 3: "Unresolved reference: R"

**원인**: 리소스 파일 문제 또는 빌드 실패

**해결**:
1. Build > Clean Project
2. Build > Rebuild Project
3. File > Invalidate Caches / Restart

---

### 오류 4: "Kotlin version mismatch"

**원인**: Kotlin 플러그인 버전과 프로젝트 Kotlin 버전 불일치

**해결**:
- `build.gradle.kts`에서 Kotlin 버전 확인:
  ```kotlin
  id("org.jetbrains.kotlin.android") version "1.9.20"
  ```
- Android Studio의 Kotlin 플러그인 업데이트

---

### 오류 5: "Gradle sync failed"

**원인**: 다양한 원인 가능 (의존성, 설정 파일 등)

**해결**:
1. Gradle 로그 확인: View > Tool Windows > Build
2. `gradle.properties` 확인:
   ```properties
   org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
   android.useAndroidX=true
   android.enableJetifier=true
   ```
3. Gradle Wrapper 버전 확인: `gradle/wrapper/gradle-wrapper.properties`
4. 프로젝트 재동기화

---

## 빌드 및 실행

### Debug APK 빌드

```bash
./gradlew assembleDebug
```

생성된 APK 위치:
```
app/build/outputs/apk/debug/app-debug.apk
```

### Android Studio에서 실행

1. 에뮬레이터 실행 또는 실제 기기 연결
2. Run 버튼 클릭 (Shift+F10)
3. 또는 Build > Make Project (Ctrl+F9)

---

## 체크리스트

빌드 전 확인 사항:

- [ ] `local.properties` 파일 존재 및 SDK 경로 설정
- [ ] Android SDK Platform 34 설치됨
- [ ] Gradle 동기화 완료
- [ ] 인터넷 연결 정상
- [ ] 프로젝트 구조 올바름 (`app/src/main/` 구조)
- [ ] `client_secret.json` 파일이 `app/src/main/assets/`에 위치 (필요한 경우)

---

## 추가 리소스

- [Android 개발자 문서](https://developer.android.com/)
- [Gradle 빌드 가이드](https://developer.android.com/studio/build)
- 프로젝트 README: `README.md`, `README_COMPLETE.md`

---

**마지막 업데이트**: 2026-01-15
