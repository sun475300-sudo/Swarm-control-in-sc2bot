# ? API 키 교체 체크리스트

**작성일**: 2026-01-14  
**목적**: 노출된 키 교체를 위한 단계별 체크리스트

---

## ? 즉시 조치 (필수)

### 1. Google AI Studio에서 기존 키 삭제

- [ ] https://makersuite.google.com/app/apikey 접속
- [ ] 기존 키 찾기: `AIzaSyC_Ci...MIIo`
- [ ] 키 삭제 또는 비활성화
- [ ] 삭제 확인

**예상 소요 시간**: 2-3분
l so
---

## ? 새 키 발급 및 적용

### 2. 새 API 키 발급

- [ ] Google AI Studio에서 새 키 생성
- [ ] 키 복사 및 안전한 곳에 임시 저장
- [ ] 키 형식 확인 (`AIzaSy`로 시작)

**예상 소요 시간**: 2-3분

### 3. 새 키 적용

#### 방법 A: 자동 스크립트 사용 (권장)

```powershell
cd wicked_zerg_challenger
.\tools\rotate_api_key.ps1
```

- [ ] 스크립트 실행
- [ ] 새 키 입력
- [ ] 저장 확인

#### 방법 B: 수동 적용

- [ ] `secrets/gemini_api.txt` 파일 생성
- [ ] 새 키 입력
- [ ] 파일 저장 확인

**예상 소요 시간**: 1-2분

---

## ? 기존 키 제거

### 4. 환경 변수에서 제거

```powershell
Remove-Item Env:\GEMINI_API_KEY
Remove-Item Env:\GOOGLE_API_KEY
```

- [ ] 환경 변수에서 기존 키 제거
- [ ] 제거 확인: `$env:GEMINI_API_KEY`

**예상 소요 시간**: 1분

### 5. 파일에서 제거 (있는 경우)

- [ ] `secrets/gemini_api.txt` 확인 및 삭제 (있는 경우)
- [ ] `api_keys/GEMINI_API_KEY.txt` 확인 및 삭제 (있는 경우)
- [ ] `.env` 파일에서 키 라인 제거 (있는 경우)

**예상 소요 시간**: 1-2분

---

## ? 새 키 확인

### 6. 새 키 테스트

```python
from tools.load_api_key import get_gemini_api_key

key = get_gemini_api_key()
print(f"새 키: {key[:10]}...")
```

- [ ] Python 스크립트로 새 키 로드 확인
- [ ] 키가 기존 키와 다른지 확인
- [ ] Gemini API 호출 테스트 (선택적)

**예상 소요 시간**: 2-3분

---

## ? 보안 확인

### 7. Git 보안 확인

```bash
# Git 히스토리에서 키 검색
git log -p --all -S "AIzaSyC_Ci...MIIo"
```

- [ ] Git 히스토리에서 기존 키 검색
- [ ] 새 키가 Git에 커밋되지 않았는지 확인
- [ ] `.gitignore` 설정 확인

**예상 소요 시간**: 3-5분

### 8. 파일 권한 확인 (Linux/Mac)

```bash
chmod 600 secrets/gemini_api.txt
```

- [ ] 파일 권한 설정 (있는 경우)

**예상 소요 시간**: 1분

---

## ? 진행 상황 요약

### 완료 항목
- [ ] 기존 키 삭제
- [ ] 새 키 발급
- [ ] 새 키 적용
- [ ] 기존 키 제거
- [ ] 새 키 테스트
- [ ] 보안 확인

### 총 예상 소요 시간
**약 10-15분**

---

## ? 문제 발생 시

### 새 키가 작동하지 않는 경우

1. **키 형식 확인**
   - `AIzaSy`로 시작하는지 확인
   - 길이가 약 39자인지 확인

2. **로드 우선순위 확인**
   - `tools/load_api_key.py` 확인
   - 여러 위치에 키가 있으면 우선순위 확인

3. **Google AI Studio 확인**
   - 키가 활성화되어 있는지 확인
   - Gemini API 권한이 있는지 확인

---

## ? 관련 문서

- **상세 가이드**: `docs/API_KEY_ROTATION_GUIDE.md`
- **비상 대응**: `docs/EMERGENCY_API_KEY_REMOVAL.md`
- **키 관리**: `docs/API_KEYS_MANAGEMENT.md`

---

**마지막 업데이트**: 2026-01-14
