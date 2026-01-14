# Gradle 배포판에서 파일 복사 가이드

**작성일**: 2026-01-15  
**목적**: `C:\Users\sun47\Downloads\gradle-8.13-bin` 경로의 Gradle 배포판을 참고하여 필요한 파일 설정

---

## 📁 Gradle 배포판 구조

**다운로드 위치**: `C:\Users\sun47\Downloads\gradle-8.13-bin\gradle-8.13`

### 확인된 파일들

1. **Gradle Wrapper 관련 JAR 파일**:
   - `lib/gradle-wrapper-shared-8.13.jar` (31,950 bytes)
   - `lib/plugins/gradle-wrapper-main-8.13.jar` (42,890 bytes)

2. **주의사항**:
   - Gradle 배포판에는 `gradle-wrapper.jar` 파일이 직접 포함되어 있지 않습니다.
   - `gradle-wrapper.jar`는 별도로 생성하거나 다운로드해야 합니다.

---

## ✅ 현재 Android 프로젝트 상태

**프로젝트 위치**: `d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android`

**확인 결과**:
- ✅ `gradle/wrapper/gradle-wrapper.jar` 파일 존재
- ✅ `gradle/wrapper/gradle-wrapper.properties` 파일 존재
- ✅ `gradlew` 및 `gradlew.bat` 스크립트 존재

---

## 🔍 Gradle Wrapper 파일 생성 방법

### 방법 1: 온라인에서 직접 다운로드 (권장)

Gradle 배포판에는 `gradle-wrapper.jar`가 포함되어 있지 않으므로, 다음 URL에서 직접 다운로드:

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# gradle-wrapper.jar 다운로드
$wrapperUrl = "https://raw.githubusercontent.com/gradle/gradle/v8.13.0/gradle/wrapper/gradle-wrapper.jar"
$wrapperPath = "gradle\wrapper\gradle-wrapper.jar"

# 폴더 생성 (없으면)
New-Item -ItemType Directory -Path "gradle\wrapper" -Force

# 다운로드
Invoke-WebRequest -Uri $wrapperUrl -OutFile $wrapperPath

# 확인
if (Test-Path $wrapperPath) {
    Write-Host "✅ gradle-wrapper.jar 다운로드 완료!"
    $file = Get-Item $wrapperPath
    Write-Host "크기: $($file.Length) bytes"
} else {
    Write-Host "❌ 다운로드 실패"
}
```

### 방법 2: Android Studio에서 자동 생성

1. Android Studio 실행
2. File > Open > `mobile_app_android` 폴더 선택
3. Gradle 동기화 시도
4. Android Studio가 자동으로 `gradle-wrapper.jar` 다운로드

### 방법 3: Gradle 명령어 사용 (Gradle이 설치된 경우)

```powershell
cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android

# Gradle이 설치되어 있다면
gradle wrapper --gradle-version 8.13
```

---

## 📝 Gradle 배포판의 파일 용도

### `gradle-wrapper-shared-8.13.jar`
- Gradle Wrapper의 공유 라이브러리
- Gradle 배포판 내부에서 사용
- 프로젝트에 직접 복사할 필요 없음

### `gradle-wrapper-main-8.13.jar`
- Gradle Wrapper의 메인 라이브러리
- Gradle 배포판 내부에서 사용
- 프로젝트에 직접 복사할 필요 없음

### `gradle-wrapper.jar` (필요한 파일)
- 프로젝트의 `gradle/wrapper/` 폴더에 필요한 파일
- Gradle 배포판에 포함되어 있지 않음
- 별도로 다운로드하거나 생성해야 함

---

## 🔄 Gradle Wrapper 작동 원리

1. **`gradle-wrapper.properties`**: Gradle 버전 및 다운로드 URL 지정
2. **`gradle-wrapper.jar`**: Wrapper 실행 파일
3. **`gradlew` / `gradlew.bat`**: Wrapper 실행 스크립트

프로젝트를 빌드할 때:
- `gradlew` 스크립트 실행
- `gradle-wrapper.jar`가 `gradle-wrapper.properties`를 읽음
- 지정된 Gradle 버전(8.13)을 자동으로 다운로드
- 다운로드한 Gradle로 빌드 실행

---

## ✅ 확인 체크리스트

현재 프로젝트 상태 확인:

- [x] `gradle/wrapper/gradle-wrapper.properties` 존재
- [x] `gradle/wrapper/gradle-wrapper.jar` 존재 (확인 필요)
- [x] `gradlew` 스크립트 존재
- [x] `gradlew.bat` 스크립트 존재

---

## 🚀 다음 단계

1. **`gradle-wrapper.jar` 파일 확인**:
   ```powershell
   Test-Path "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android\gradle\wrapper\gradle-wrapper.jar"
   ```

2. **파일이 없다면**:
   - 방법 1 (온라인 다운로드) 사용
   - 또는 Android Studio에서 자동 생성

3. **Android Studio에서 프로젝트 열기**:
   - File > Open > `mobile_app_android` 폴더
   - Gradle 동기화 확인

---

## 📚 참고 자료

- [Gradle Wrapper 문서](https://docs.gradle.org/current/userguide/gradle_wrapper.html)
- [Gradle Wrapper JAR 다운로드](https://raw.githubusercontent.com/gradle/gradle/v8.13.0/gradle/wrapper/gradle-wrapper.jar)
- Android Studio 가이드: `BUILD_SETUP.md`

---

**마지막 업데이트**: 2026-01-15
