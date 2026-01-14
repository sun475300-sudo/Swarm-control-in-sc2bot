# ? API 키 보안 설정 가이드

**중요**: 이 프로젝트는 GitHub에 공개될 수 있으므로, API 키는 절대 코드에 하드코딩하지 마세요!

---

## ? 안전한 API 키 설정 방법

### 1단계: local.properties 파일 생성/수정

1. **파일 위치**: `monitoring/mobile_app_android/local.properties`
2. **파일 열기** (Android Studio 또는 텍스트 에디터)
3. **API 키 추가**:
   ```properties
   # Gemini API Key (DO NOT COMMIT TO GIT)
   GEMINI_API_KEY=YOUR_API_KEY_HERE
   ```

### 2단계: API 키 발급

1. https://makersuite.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. API 키 복사

### 3단계: Gradle 동기화

Android Studio에서:
- `File > Sync Project with Gradle Files`
- 또는 상단 툴바의 "Sync Now" 클릭

---

## ? 보안 확인 사항

### ? 이미 설정된 보안 기능

1. **`.gitignore`에 포함됨**:
   - `local.properties`는 Git에 커밋되지 않음
   - 프로젝트 루트와 Android 프로젝트 모두 확인됨

2. **BuildConfig 사용**:
   - API 키는 빌드 시점에만 삽입됨
   - 소스 코드에 직접 노출되지 않음

### ? 절대 하지 말아야 할 것

1. **코드에 직접 API 키 작성 금지**:
   ```kotlin
   // ? 절대 이렇게 하지 마세요!
   private val apiKey = "YOUR_API_KEY_HERE"  // 실제 키를 코드에 작성하지 마세요!
   ```

2. **Git에 API 키 커밋 금지**:
   - `local.properties`는 이미 `.gitignore`에 포함됨
   - 다른 개발자는 자신의 키를 사용해야 함

3. **공개 저장소에 API 키 업로드 금지**:
   - GitHub, GitLab 등 공개 저장소에 절대 업로드하지 마세요

---

## ? Git 커밋 전 확인

### API 키가 커밋되지 않았는지 확인

```powershell
# Git에 추가된 파일 확인
git status

# local.properties가 목록에 없는지 확인
# 만약 있다면: git rm --cached monitoring/mobile_app_android/local.properties
```

### 이미 커밋된 경우 (비상 조치)

만약 실수로 API 키를 커밋했다면:

1. **즉시 API 키 재발급**:
   - Google AI Studio에서 기존 키 삭제
   - 새 API 키 생성

2. **Git 히스토리에서 제거**:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch monitoring/mobile_app_android/local.properties" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **강제 푸시** (주의: 팀원과 협의 필요):
   ```bash
   git push origin --force --all
   ```

---

## ? 다른 개발자를 위한 안내

프로젝트를 클론한 다른 개발자는:

1. `local.properties.example` 파일을 참고
2. 자신의 API 키를 발급받아 `local.properties`에 추가
3. 각자 자신의 키를 사용

---

## ? 최종 확인 체크리스트

GitHub에 푸시하기 전:

- [ ] `local.properties`가 `.gitignore`에 포함되어 있음
- [ ] `git status`에서 `local.properties`가 표시되지 않음
- [ ] 코드에 API 키가 하드코딩되어 있지 않음
- [ ] `BuildConfig`를 통해서만 API 키 사용
- [ ] API 키가 문서나 주석에 포함되어 있지 않음

---

**보안이 최우선입니다!** API 키를 안전하게 관리하세요. ?
