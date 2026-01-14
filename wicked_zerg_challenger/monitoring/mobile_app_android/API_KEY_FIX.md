# API 키 만료 오류 해결 가이드

**오류 메시지**: 
```
Please try again later.
Error: Status INVALID_ARGUMENT
API key expired. Please renew the API key.
```

---

## ✅ 즉시 해결 방법

### 방법 1: API 키 갱신 (권장)

1. **새 API 키 발급**
   - https://makersuite.google.com/app/apikey 접속
   - 또는 https://aistudio.google.com/app/apikey
   - "Create API Key" 클릭
   - 새 API 키 복사

2. **local.properties 파일 수정**
   - 파일 위치: `mobile_app_android/local.properties`
   - Android Studio에서 파일 열기
   - 또는 텍스트 에디터로 열기
   
   ```properties
   # Android SDK 경로
   sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
   
   # Gemini API Key (새 키로 교체)
   GEMINI_API_KEY=YOUR_NEW_API_KEY_HERE
   ```

3. **Gradle 동기화**
   - Android Studio에서: `File > Sync Project with Gradle Files`
   - 또는 상단 툴바의 "Sync Now" 클릭

---

### 방법 2: API 키 제거 (임시 해결)

만약 앱에서 Gemini API를 실제로 사용하지 않는다면, API 키를 제거할 수 있습니다.

1. **local.properties에서 API 키 제거**
   ```properties
   # Android SDK 경로만 남기고 API 키 제거
   sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
   
   # GEMINI_API_KEY=... 이 줄을 삭제하거나 주석 처리
   ```

2. **build.gradle.kts 수정** (선택사항)
   - API 키가 없어도 빌드가 되도록 수정
   - 현재 코드는 이미 빈 문자열("")을 기본값으로 사용하므로 문제없음

3. **Gradle 동기화**
   - `File > Sync Project with Gradle Files`

---

## 🔍 문제 원인

이 오류는 다음 중 하나일 수 있습니다:

1. **API 키가 실제로 만료됨**
   - Google AI Studio에서 키가 만료되었거나 삭제됨
   - 해결: 새 키 발급

2. **잘못된 API 키**
   - `local.properties`에 잘못된 키가 입력됨
   - 해결: 키 확인 및 수정

3. **API 키 사용량 초과**
   - 무료 할당량을 초과했을 수 있음
   - 해결: 새 키 발급 또는 할당량 확인

---

## 📝 local.properties 파일 위치 확인

**Windows**:
```
d:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\monitoring\mobile_app_android\local.properties
```

**파일이 없다면**:
1. `local.properties.example` 파일을 복사
2. `local.properties`로 이름 변경
3. API 키 추가

---

## 🚀 빠른 해결 체크리스트

- [ ] `local.properties` 파일 열기
- [ ] `GEMINI_API_KEY` 값 확인
- [ ] 새 API 키 발급 (https://makersuite.google.com/app/apikey)
- [ ] `local.properties`에 새 키 입력
- [ ] Gradle 동기화 (`File > Sync Project with Gradle Files`)
- [ ] 빌드 다시 시도

---

## 💡 참고사항

### API 키가 실제로 필요한가요?

현재 Android 앱 코드를 확인한 결과, **실제로 Gemini API를 사용하는 코드는 없습니다**. 
따라서 API 키가 없어도 앱은 정상적으로 빌드되고 실행될 수 있습니다.

**확인 방법**:
- `app/src/main/java/` 폴더에서 `BuildConfig.GEMINI_API_KEY` 검색
- 사용되지 않는다면 API 키를 제거해도 됩니다

---

## 🔗 관련 문서

- API 키 발급: https://makersuite.google.com/app/apikey
- API 키 보안 가이드: `README_API_KEY.md`
- 빌드 설정 가이드: `BUILD_SETUP.md`

---

**마지막 업데이트**: 2026-01-15
