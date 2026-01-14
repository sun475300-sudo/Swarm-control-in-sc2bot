# 설정 가이드

**작성 일시**: 2026-01-14  
**목적**: 시스템 설정 및 실행 가이드  
**상태**: ? **가이드 작성 완료**

---

## ? 빠른 시작 (Quick Start)

### 1. 가상환경 설정 (권장)

의존성 충돌 방지를 위해 가상환경 사용을 **강력히 권장**합니다.

**Windows (PowerShell):**
```powershell
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt
```

**Windows (CMD):**
```cmd
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
venv\Scripts\activate.bat

# 의존성 설치
pip install -r requirements.txt
```

**Linux/Mac:**
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

---

## ? Google Gemini API 인증 설정

### 중요: API Key 방식 사용

이 프로젝트는 **Google Gemini API Key** 방식을 사용합니다.  
서비스 계정 키 파일(`GOOGLE_APPLICATION_CREDENTIALS`)은 **필요하지 않습니다**.

### 해결책: 환경 변수 설정

#### 방법 1: 임시 설정 (현재 터미널 세션만 유효)

**PowerShell:**
```powershell
$env:GOOGLE_API_KEY="your_api_key_here"
```

**CMD:**
```cmd
set GOOGLE_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

**참고:** 터미널을 닫으면 설정이 사라집니다.

---

#### 방법 2: 영구 설정 (시스템 환경 변수)

**Windows:**
1. **Windows 키 + R** → `sysdm.cpl` 입력 → Enter
2. **[고급]** 탭 클릭
3. **[환경 변수]** 버튼 클릭
4. **[사용자 변수]** 섹션에서 **[새로 만들기]** 클릭
5. **변수 이름:** `GOOGLE_API_KEY`
6. **변수 값:** API 키 문자열 (예: `AIzaSy...`)
7. **[확인]** 클릭

**참고:** 설정 후 터미널을 다시 시작해야 적용됩니다.

**Linux/Mac:**
```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export GOOGLE_API_KEY="your_api_key_here"
```

---

#### 방법 3: .env 파일 사용 (권장)

프로젝트 루트에 `.env` 파일을 생성:

```env
GOOGLE_API_KEY=your_api_key_here
```

**참고:** `.env` 파일은 이미 `.gitignore`에 포함되어 있습니다.

---

### API 키 발급 방법

1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. **Create API Key** 클릭
3. API 키 복사 후 환경 변수에 설정

**보안 주의사항:**
- API 키를 Git에 커밋하지 마세요
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- 프로젝트 디렉토리 외부에 저장하는 것을 권장합니다

---

## ? Android 앱 빌드 설정

### 문제 상황

보안을 위해 `android.keystore`를 삭제했지만, Release 빌드는 서명이 필요합니다.

### 해결책: Debug 빌드 사용

테스트 및 시연 용도라면 **Debug 빌드**를 사용하면 자동으로 임시 서명이 적용됩니다.

#### 빌드 명령어

**PowerShell:**
```powershell
cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger\mobile_app

# Debug 빌드 (자동 임시 서명)
.\gradlew assembleDebug
```

**출력 위치:**
- `mobile_app\app\build\outputs\apk\debug\app-debug.apk`

**참고:** Debug 빌드는 개발 및 테스트용이며, Google Play Store에 배포하려면 Release 빌드와 공식 서명이 필요합니다.

---

### Release 빌드 (프로덕션용, 선택 사항)

프로덕션 배포를 위해 Release 빌드가 필요한 경우:

1. **새 keystore 생성:**
   ```bash
   keytool -genkey -v -keystore android.keystore -alias wicked_zerg -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **`mobile_app/app/build.gradle`에 서명 설정 추가:**
   ```gradle
   android {
       signingConfigs {
           release {
               storeFile file('../android.keystore')
               storePassword 'your_password'
               keyAlias 'wicked_zerg'
               keyPassword 'your_password'
           }
       }
       buildTypes {
           release {
               signingConfig signingConfigs.release
           }
       }
   }
   ```

3. **Release 빌드:**
   ```bash
   .\gradlew assembleRelease
   ```

**참고:** keystore 파일과 비밀번호는 안전하게 보관하세요.

---

## ? 실행 체크리스트

### 실행 전 확인 사항

- [ ] **가상환경 설정 완료** (권장)
  - [ ] 가상환경 생성 및 활성화
  - [ ] `pip install -r requirements.txt` 실행 완료
- [ ] **Google Gemini API 인증 설정 완료**
  - [ ] API 키 발급 완료 ([Google AI Studio](https://makersuite.google.com/app/apikey))
  - [ ] 환경 변수 설정됨 (`GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`)
  - [ ] 또는 `.env` 파일 생성 완료
- [ ] **의존성 설치 확인**
  - [ ] `pip list`로 주요 패키지 확인 (burnysc2, numpy, google-generativeai 등)
- [ ] Android 앱 빌드 준비 (선택 사항)
  - [ ] Android 앱 구조 생성 필요 (현재 없음)
  - [ ] Debug 빌드: 추가 설정 불필요
  - [ ] Release 빌드: keystore 생성 및 설정 필요

---

## ? 참고 사항

### 환경 변수 확인

**PowerShell:**
```powershell
# API 키 확인
echo $env:GOOGLE_API_KEY

# 모든 환경 변수에서 GOOGLE 관련 확인
Get-ChildItem Env: | Where-Object { $_.Name -like "*GOOGLE*" }
```

**CMD:**
```cmd
# API 키 확인
echo %GOOGLE_API_KEY%

# 모든 환경 변수에서 GOOGLE 관련 확인
set | findstr /i "GOOGLE"
```

**Linux/Mac:**
```bash
# API 키 확인
echo $GOOGLE_API_KEY

# 모든 환경 변수에서 GOOGLE 관련 확인
env | grep -i GOOGLE
```

### 중요: 인증 방식 구분

- ? **사용하는 방식**: `GOOGLE_API_KEY` (API Key 문자열)
- ? **사용하지 않는 방식**: `GOOGLE_APPLICATION_CREDENTIALS` (서비스 계정 키 파일)

이 프로젝트는 Gemini API를 사용하므로 **API Key만** 필요합니다.  
서비스 계정 키 파일은 Vertex AI나 다른 Google Cloud 서비스를 사용할 때만 필요합니다.

---

## ? 관련 문서

- `genai_self_healing.py` - Gen-AI Self-Healing 모듈 (Google Gemini API 사용)
- `ARCHITECTURE_OVERVIEW.md` - 시스템 아키텍처 개요
- `.gitignore` - Git 무시 규칙 (키 파일 제외)

---

**생성 일시**: 2026-01-14  
**상태**: ? **가이드 작성 완료**
