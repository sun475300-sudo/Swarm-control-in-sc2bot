# Gradle Wrapper 파일 생성 가이드

**문제**: `gradle wrapper` 명령어가 작동하지 않음 (Gradle이 설치되지 않음)

---

## ✅ 해결 방법 (3가지)

### 방법 1: Android Studio에서 자동 다운로드 (가장 간단) ⭐ 권장

**Android Studio가 자동으로 처리합니다:**

1. **Android Studio에서 프로젝트 열기**
   - File > Open
   - `d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android` 선택

2. **Gradle 동기화 시도**
   - Android Studio가 자동으로 `gradle-wrapper.jar` 파일을 다운로드합니다
   - 상단에 "Sync Now" 또는 "Install missing components" 버튼이 나타나면 클릭

3. **완료 확인**
   - `gradle/wrapper/gradle-wrapper.jar` 파일이 생성되었는지 확인

---

### 방법 2: 수동 다운로드 (Android Studio 없이)

**Gradle Wrapper JAR 파일을 직접 다운로드:**

1. **다운로드 URL**:
   ```
   https://raw.githubusercontent.com/gradle/gradle/v8.13.0/gradle/wrapper/gradle-wrapper.jar
   ```
   또는
   ```
   https://services.gradle.org/distributions/gradle-8.13-bin.zip
   ```

2. **다운로드 및 배치**:
   ```powershell
   # 방법 A: 직접 JAR 다운로드 (권장)
   # 브라우저에서 위 URL로 접속하여 gradle-wrapper.jar 다운로드
   # 다운로드한 파일을 다음 위치에 복사:
   # d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android\gradle\wrapper\gradle-wrapper.jar
   
   # 방법 B: Gradle 배포판에서 추출
   # 1. https://services.gradle.org/distributions/gradle-8.13-bin.zip 다운로드
   # 2. 압축 해제
   # 3. gradle-8.13/lib/gradle-wrapper-8.13.jar 파일 찾기
   # 4. gradle/wrapper/gradle-wrapper.jar로 복사
   ```

3. **PowerShell로 다운로드** (선택사항):
   ```powershell
   cd d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android
   
   # gradle-wrapper.jar 직접 다운로드
   $url = "https://raw.githubusercontent.com/gradle/gradle/v8.13.0/gradle/wrapper/gradle-wrapper.jar"
   $output = "gradle\wrapper\gradle-wrapper.jar"
   Invoke-WebRequest -Uri $url -OutFile $output
   ```

---

### 방법 3: Android Studio의 내장 Gradle 사용

**Android Studio에 포함된 Gradle을 사용:**

1. **Android Studio 실행**
2. **Settings 확인**:
   - File > Settings (또는 Ctrl+Alt+S)
   - Build, Execution, Deployment > Build Tools > Gradle
   - "Gradle JDK" 확인

3. **프로젝트 열기**:
   - Android Studio가 자동으로 필요한 파일 생성

---

## 🔍 현재 상태 확인

```powershell
# gradle-wrapper.jar 파일 존재 확인
Test-Path "d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android\gradle\wrapper\gradle-wrapper.jar"

# 결과가 True면 파일이 있음, False면 없음
```

---

## 📝 필요한 파일 구조

프로젝트가 정상 작동하려면 다음 파일들이 필요합니다:

```
mobile_app_android/
├── gradlew                    ✅ 생성됨
├── gradlew.bat                ✅ 생성됨
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.properties  ✅ 있음
│       └── gradle-wrapper.jar         ⚠️  없음 (생성 필요)
```

---

## 🚀 빠른 해결 (PowerShell)

다음 명령어를 실행하면 자동으로 다운로드됩니다:

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
} else {
    Write-Host "❌ 다운로드 실패"
}
```

---

## ⚠️ 주의사항

- `gradle-wrapper.jar` 파일은 약 60KB 정도의 작은 파일입니다
- 이 파일이 없으면 Android Studio가 프로젝트를 인식하지 못할 수 있습니다
- Android Studio를 사용한다면 방법 1이 가장 간단합니다

---

## 🔗 참고

- Gradle Wrapper 문서: https://docs.gradle.org/current/userguide/gradle_wrapper.html
- Android Studio 가이드: `BUILD_SETUP.md`

---

**마지막 업데이트**: 2026-01-15
