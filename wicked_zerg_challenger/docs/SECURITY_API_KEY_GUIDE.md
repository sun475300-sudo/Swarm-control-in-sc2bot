# ? API 키 보안 가이드 (GitHub 배포용)

**작성 일시**: 2026-01-14  
**상태**: ? **보안 설정 완료**

---

## ? 중요: API 키 보안

이 프로젝트를 GitHub에 배포할 때, **API 키가 노출되지 않도록** 반드시 확인하세요!

---

## ? 현재 보안 설정 상태

### 1. local.properties 보호

- ? `local.properties`는 `.gitignore`에 포함됨
- ? Git에 커밋되지 않음
- ? 각 개발자가 자신의 키를 사용

### 2. 코드 보안

- ? API 키는 `BuildConfig`를 통해서만 사용
- ? 소스 코드에 하드코딩되지 않음
- ? `local.properties`에서만 읽어옴

---

## ? GitHub 배포 전 확인 사항

### 필수 확인 체크리스트

1. **Git 상태 확인**:
   ```powershell
   cd D:\Swarm-contol-in-sc2bot\Swarm-contol-in-sc2bot\wicked_zerg_challenger
   git status
   ```
   
   **확인 사항**:
   - `local.properties`가 목록에 **없어야** 함
   - `monitoring/mobile_app_android/local.properties`가 **표시되지 않아야** 함

2. **.gitignore 확인**:
   ```powershell
   git check-ignore monitoring/mobile_app_android/local.properties
   ```
   
   **예상 결과**: 파일 경로가 출력되어야 함 (무시되고 있다는 의미)

3. **코드 검색**:
   ```powershell
   # API 키가 코드에 있는지 확인
   git grep "AIzaSy" -- "*.kt" "*.java" "*.py" "*.md"
   ```
   
   **예상 결과**: 아무것도 출력되지 않아야 함

---

## ?? 보안 강화 조치

### 1. .gitignore 강화

프로젝트 루트의 `.gitignore`에 다음이 포함되어 있는지 확인:

```
# Android local.properties (contains API keys and SDK paths)
local.properties
**/local.properties
monitoring/mobile_app_android/local.properties
```

### 2. 예제 파일 사용

- ? `local.properties.example` 파일 제공
- ? 실제 키 없이 템플릿만 제공
- ? 다른 개발자가 자신의 키를 설정할 수 있도록 안내

### 3. 문서에 보안 주의사항 추가

- ? README에 API 키 설정 방법 명시
- ? 보안 주의사항 강조

---

## ? GitHub 배포 전 최종 체크리스트

### 필수 확인

- [ ] `git status`에서 `local.properties`가 표시되지 않음
- [ ] `git check-ignore`로 무시 확인됨
- [ ] 코드에 API 키가 하드코딩되어 있지 않음
- [ ] 문서에 실제 API 키가 포함되어 있지 않음
- [ ] `.gitignore`에 `local.properties` 포함됨

### 권장 확인

- [ ] `local.properties.example` 파일이 제공됨
- [ ] README에 API 키 설정 방법 명시됨
- [ ] 보안 주의사항이 문서화됨

---

## ? 비상 조치: API 키가 이미 커밋된 경우

### 즉시 조치

1. **API 키 재발급** (가장 중요!):
   - https://makersuite.google.com/app/apikey 접속
   - 기존 API 키 삭제
   - 새 API 키 생성

2. **Git 히스토리에서 제거**:
   ```bash
   # 주의: 이 작업은 Git 히스토리를 변경합니다
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch monitoring/mobile_app_android/local.properties" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **강제 푸시** (팀원과 협의 후):
   ```bash
   git push origin --force --all
   ```

---

## ? 다른 개발자를 위한 안내

프로젝트를 클론한 다른 개발자는:

1. **자신의 API 키 발급**:
   - https://makersuite.google.com/app/apikey
   - "Create API Key" 클릭

2. **local.properties 파일 생성**:
   ```properties
   # monitoring/mobile_app_android/local.properties
   sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
   GEMINI_API_KEY=YOUR_OWN_API_KEY_HERE
   ```

3. **Gradle 동기화**:
   - Android Studio: `File > Sync Project with Gradle Files`

---

## ? 보안 설정 완료

현재 설정으로 API 키는 안전하게 보호됩니다:

- ? `local.properties`는 Git에 커밋되지 않음
- ? 코드에 하드코딩되지 않음
- ? `BuildConfig`를 통해서만 사용
- ? 각 개발자가 자신의 키 사용

---

## ? 추가 보안 권장사항

### 1. API 키 제한 설정

Google Cloud Console에서:
- API 키 사용량 제한 설정
- 특정 IP 주소만 허용
- 특정 앱 패키지명만 허용

### 2. 환경 변수 사용 (선택)

프로덕션 환경에서는:
- 환경 변수로 API 키 관리
- CI/CD 파이프라인에서 주입
- 서버 측에서만 API 키 사용

---

**보안이 최우선입니다!** API 키를 안전하게 관리하세요. ?
