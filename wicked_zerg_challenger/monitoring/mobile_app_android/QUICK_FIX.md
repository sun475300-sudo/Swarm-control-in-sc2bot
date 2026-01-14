# Android Studio 프로젝트 열기 - 빠른 해결 가이드

**문제**: Android Studio에서 프로젝트가 열리지 않음

---

## ✅ 즉시 시도할 방법

### 방법 1: 올바른 폴더 열기 (가장 중요!)

**❌ 잘못된 방법**:
```
File > Open > d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring
```

**✅ 올바른 방법**:
```
File > Open > d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
```

**중요**: `mobile_app_android` 폴더를 직접 열어야 합니다!

---

### 방법 2: Gradle Wrapper 파일 확인

프로젝트가 열리지 않는 가장 흔한 원인은 `gradle-wrapper.jar` 파일이 없는 것입니다.

**확인 방법**:
```
gradle/wrapper/gradle-wrapper.jar 파일이 있는지 확인
```

**없다면 해결 방법**:

#### 옵션 A: Android Studio가 자동으로 다운로드하도록
1. Android Studio에서 프로젝트 열기 시도
2. "Gradle sync" 오류가 나면
3. 상단의 "Sync Now" 또는 "Install missing components" 클릭
4. Android Studio가 자동으로 필요한 파일 다운로드

#### 옵션 B: Gradle 명령어로 생성
```powershell
# PowerShell에서 실행
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# Gradle이 설치되어 있다면
gradle wrapper --gradle-version 8.13

# Gradle이 없다면, Android Studio의 내장 Gradle 사용
# Android Studio > File > Settings > Build, Execution, Deployment > Build Tools > Gradle
# "Use Gradle from" 선택 후 "Specified location"에서 경로 확인
```

#### 옵션 C: 수동 다운로드 (최후의 수단)
1. https://services.gradle.org/distributions/gradle-8.13-bin.zip 다운로드
2. 압축 해제
3. `gradle-8.13/lib/gradle-wrapper-8.13.jar` 파일 찾기
4. `gradle/wrapper/gradle-wrapper.jar`로 복사

---

### 방법 3: 프로젝트 구조 확인

프로젝트 루트에 다음 파일들이 있어야 합니다:

```
mobile_app_android/
├── build.gradle.kts          ✅ 있어야 함
├── settings.gradle.kts       ✅ 있어야 함
├── gradle.properties         ✅ 있어야 함
├── gradlew                   ✅ 있어야 함 (방금 생성됨)
├── gradlew.bat               ✅ 있어야 함 (방금 생성됨)
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.properties  ✅ 있어야 함
│       └── gradle-wrapper.jar         ⚠️  없을 수 있음 (자동 다운로드)
└── app/
    └── build.gradle.kts      ✅ 있어야 함
```

---

### 방법 4: Android Studio 캐시 정리

프로젝트가 여전히 열리지 않는다면:

1. **Invalidate Caches / Restart**
   - File > Invalidate Caches...
   - "Invalidate and Restart" 클릭

2. **프로젝트 삭제 후 다시 열기**
   - File > Close Project
   - Welcome 화면에서 프로젝트 제거
   - File > Open으로 다시 열기

---

### 방법 5: Android Studio 버전 확인

**최소 요구사항**:
- Android Studio Hedgehog (2023.1.1) 이상
- 또는 최신 버전 권장

**확인 방법**:
- Help > About
- 버전이 낮다면 업데이트: Help > Check for Updates

---

## 🔍 문제 진단

### 오류 메시지별 해결 방법

#### "SDK location not found"
→ `local.properties` 파일 생성 필요 (BUILD_SETUP.md 참조)

#### "Gradle sync failed"
→ Gradle Wrapper 파일 확인 (위 방법 2 참조)

#### "Project structure is invalid"
→ 올바른 폴더(`mobile_app_android`)를 열었는지 확인

#### "Unsupported Gradle version"
→ `gradle/wrapper/gradle-wrapper.properties`에서 버전 확인
→ `distributionUrl=https\://services.gradle.org/distributions/gradle-8.13-bin.zip`

---

## 📞 여전히 안 되면

1. **Android Studio 로그 확인**
   - Help > Show Log in Explorer
   - `idea.log` 파일에서 오류 메시지 확인

2. **프로젝트 파일 확인**
   ```powershell
   # 필수 파일 존재 확인
   Test-Path "build.gradle.kts"
   Test-Path "settings.gradle.kts"
   Test-Path "app/build.gradle.kts"
   Test-Path "gradle/wrapper/gradle-wrapper.properties"
   ```

3. **새 프로젝트로 테스트**
   - File > New > New Project
   - 프로젝트가 생성되는지 확인
   - 생성되면 Android Studio 자체는 정상

---

**마지막 업데이트**: 2026-01-15
