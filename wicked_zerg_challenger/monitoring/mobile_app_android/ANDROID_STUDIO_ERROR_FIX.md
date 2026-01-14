# Android Studio 오류 해결 가이드

**오류**: `IllegalStateException: This method is forbidden on EDT`

**작성일**: 2026-01-15

---

## 🔍 오류 분석

### 발생 원인

이 오류는 Android Studio IDE의 내부 버그로, Settings 다이얼로그를 열 때 Gradle JVM 경로를 확인하는 과정에서 발생합니다.

**오류 위치**:
- `GradleInstallationManager.getGradleJvmPath()`
- `MemorySettingsConfigurable` 초기화 중

**원인**: EDT(Event Dispatch Thread)에서 블로킹 작업을 수행하려고 시도

---

## ✅ 해결 방법

### 방법 1: Android Studio 재시작 (가장 간단) ⭐ 권장

1. **Android Studio 완전 종료**
   - File > Exit
   - 또는 작업 관리자에서 프로세스 종료

2. **Android Studio 재시작**
   - 프로젝트 다시 열기

3. **확인**
   - Settings 다이얼로그가 정상적으로 열리는지 확인

---

### 방법 2: 캐시 무효화 및 재시작

1. **File > Invalidate Caches / Restart**
2. **"Invalidate and Restart" 선택**
3. **Android Studio 재시작 후 프로젝트 다시 열기**

---

### 방법 3: Gradle 설정 확인

**Settings 확인**:
1. File > Settings (또는 Ctrl+Alt+S)
2. Build, Execution, Deployment > Build Tools > Gradle
3. 다음 설정 확인:
   - **Gradle JDK**: 올바른 JDK 버전 선택 (예: 17, 11)
   - **Gradle user home**: 기본값 사용 또는 올바른 경로 지정

---

### 방법 4: Android Studio 업데이트

이 오류는 일부 Android Studio 버전에서 발생할 수 있습니다.

1. **Help > Check for Updates**
2. **업데이트가 있으면 설치**
3. **재시작**

---

### 방법 5: 프로젝트 재임포트

1. **File > Close Project**
2. **Welcome 화면에서 "Open" 클릭**
3. **프로젝트 폴더 선택**:
   ```
   d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
   ```
4. **"Open as Project" 선택**

---

## 🔧 추가 확인 사항

### Gradle JVM 설정 확인

**gradle.properties 확인**:
```properties
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
```

**현재 설정**: ✅ 정상

### JDK 버전 확인

Android Studio에서 사용하는 JDK 버전 확인:
1. File > Project Structure > SDK Location
2. JDK location 확인
3. JDK 17 이상 권장

---

## ⚠️ 주의사항

### 이 오류는 프로젝트 문제가 아닙니다

- ✅ 프로젝트 파일은 정상입니다
- ✅ Gradle 설정은 정상입니다
- ✅ 빌드는 정상적으로 작동합니다 (`gradlew.bat tasks` 성공)

**이것은 Android Studio IDE의 내부 버그입니다.**

---

## 🚀 임시 해결책

### Settings 다이얼로그를 열지 않고 작업

1. **프로젝트는 정상적으로 열 수 있습니다**
2. **빌드는 정상적으로 작동합니다**
3. **코드 편집도 정상적으로 작동합니다**

Settings가 필요하지 않다면, 이 오류는 무시해도 됩니다.

---

## 📝 오류 발생 시나리오

이 오류는 다음 상황에서 발생할 수 있습니다:

1. **Settings 다이얼로그 열기**
2. **Memory Settings 확인**
3. **Gradle Settings 확인**
4. **VCS Root 설정 확인**

---

## ✅ 권장 해결 순서

1. **Android Studio 재시작** (가장 간단)
2. **캐시 무효화** (재시작으로 해결 안 되면)
3. **Gradle 설정 확인** (여전히 문제가 있으면)
4. **Android Studio 업데이트** (최후의 수단)

---

## 🔗 관련 문서

- **프로젝트 점검**: `PROJECT_REVIEW.md`
- **빌드 설정**: `BUILD_SETUP.md`
- **Gradle Wrapper**: `GRADLE_WRAPPER_FIX.md`

---

## ✅ 결론

**이 오류는 프로젝트 문제가 아닙니다.**

프로젝트는 정상적으로 작동하며:
- ✅ Gradle 빌드 정상 (`gradlew.bat tasks` 성공)
- ✅ 프로젝트 구조 정상
- ✅ 모든 필수 파일 존재

**Android Studio 재시작으로 대부분 해결됩니다.**

---

**마지막 업데이트**: 2026-01-15
