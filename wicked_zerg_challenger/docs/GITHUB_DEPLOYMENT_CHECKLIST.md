# GitHub 배포 전 체크리스트 (API 키 보안)

**작성 일시**: 2026-01-14  
**상태**: ? **보안 체크리스트 완료**

---

## ? GitHub 배포 전 필수 확인 사항

### 1. API 키 보안 확인

#### ? local.properties 확인

```powershell
# Git 상태 확인
git status monitoring/mobile_app_android/local.properties

# 예상 결과: 아무것도 표시되지 않아야 함 (무시되고 있다는 의미)
```

#### ? .gitignore 확인

```powershell
# .gitignore에 포함되어 있는지 확인
git check-ignore monitoring/mobile_app_android/local.properties

# 예상 결과: 파일 경로가 출력되어야 함
```

#### ? 코드 검색

```powershell
# API 키가 코드에 있는지 확인
git grep "AIzaSy" -- "*.kt" "*.java" "*.py"

# 예상 결과: 아무것도 출력되지 않아야 함
```

---

## ? 배포 전 체크리스트

### 필수 확인 항목

- [ ] `local.properties`가 Git에 추가되지 않음 (`git status`에서 표시 안 됨)
- [ ] `.gitignore`에 `local.properties` 포함됨
- [ ] 코드에 API 키가 하드코딩되어 있지 않음
- [ ] 문서에 실제 API 키가 포함되어 있지 않음
- [ ] `local.properties.example` 파일이 제공됨 (실제 키 없이)

### 권장 확인 항목

- [ ] README에 API 키 설정 방법 명시됨
- [ ] 보안 주의사항이 문서화됨
- [ ] 다른 개발자를 위한 가이드 제공됨

---

## ? 비상 조치: API 키가 이미 커밋된 경우

### 즉시 조치

1. **API 키 재발급** (가장 중요!):
   - https://makersuite.google.com/app/apikey 접속
   - 기존 API 키 삭제
   - 새 API 키 생성

2. **Git 히스토리에서 제거**:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch monitoring/mobile_app_android/local.properties" \
     --prune-empty --tag-name-filter cat -- --all
   ```

3. **강제 푸시** (팀원과 협의 후):
   ```bash
   git push origin --force --all
   ```

---

## ? 현재 보안 설정 상태

### 완료된 보안 조치

1. ? `local.properties`에 API 키 저장됨
2. ? `.gitignore`에 `local.properties` 포함됨
3. ? `build.gradle.kts`에서 `local.properties`에서만 읽어옴
4. ? 코드에 하드코딩되지 않음
5. ? `local.properties.example` 파일 제공됨

---

## ? 배포 후 확인

GitHub에 푸시한 후:

1. **GitHub 저장소에서 확인**:
   - `local.properties` 파일이 저장소에 없는지 확인
   - 코드에 API 키가 없는지 확인

2. **다른 개발자 테스트**:
   - 프로젝트를 클론하여 `local.properties`가 없는지 확인
   - 자신의 API 키로 설정 가능한지 확인

---

**보안이 최우선입니다!** ?
