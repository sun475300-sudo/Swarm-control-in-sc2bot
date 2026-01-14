# ? API 키가 필요한 스크립트 파일 정리

**작성일**: 2026-01-14  
**목적**: 프로젝트에서 API 키를 사용하는 모든 스크립트 파일 정리 및 정렬

---

## ? 필수 API 키: GEMINI_API_KEY / GOOGLE_API_KEY

### 1. ? `genai_self_healing.py` (필수)
**경로**: `wicked_zerg_challenger/genai_self_healing.py`

**사용 API**: 
- `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`

**용도**:
- 자동 오류 분석 및 패치 생성
- Build-Order Gap Analyzer 피드백 분석
- Gemini AI를 통한 코드 자가 수복

**로드 방식**:
```python
from tools.load_api_key import get_gemini_api_key
self.api_key = get_gemini_api_key()
```

**우선순위**: ? **최우선** (Self-Healing 시스템 핵심)

---

### 2. ? `wicked_zerg_bot_pro.py` (필수)
**경로**: `wicked_zerg_challenger/wicked_zerg_bot_pro.py`

**사용 API**: 
- `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` (환경 변수)

**용도**:
- GenAISelfHealing 시스템 초기화
- 게임 실행 중 오류 발생 시 자동 분석

**로드 방식**:
```python
# GenAISelfHealing 초기화 시 자동으로 load_api_key 사용
api_key=None,  # Will use GOOGLE_API_KEY from environment
```

**우선순위**: ? **최우선** (메인 봇 실행 필수)

---

### 3. ? `local_training/strategy_audit.py` (필수)
**경로**: `wicked_zerg_challenger/local_training/strategy_audit.py`

**사용 API**: 
- `GEMINI_API_KEY` (간접 사용)

**용도**:
- Build-Order Gap Analyzer
- 프로 게이머 데이터와 봇 성능 비교 분석
- Gemini 피드백 생성

**로드 방식**:
```python
# GenAISelfHealing을 통해 간접 사용
# generate_gemini_feedback() 메서드에서 사용
```

**우선순위**: ? **중요** (Build-Order 분석 기능)

---

## ?? 유틸리티 스크립트

### 4. `tools/load_api_key.py` (유틸리티)
**경로**: `wicked_zerg_challenger/tools/load_api_key.py`

**사용 API**: 
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- `GCP_PROJECT_ID` (선택적)
- `NGROK_AUTH_TOKEN` (선택적)

**용도**:
- API 키 로드 유틸리티
- 다른 스크립트에서 API 키를 안전하게 로드하는 헬퍼 함수

**로드 방식**:
```python
# 직접 사용하지 않음 (다른 스크립트에서 import하여 사용)
from tools.load_api_key import get_gemini_api_key
```

**우선순위**: ? **유틸리티** (다른 스크립트의 의존성)

---

## ? 모바일 앱 (선택적)

### 5. `monitoring/mobile_app_android/` (선택적)
**경로**: `wicked_zerg_challenger/monitoring/mobile_app_android/`

**사용 API**: 
- `GEMINI_API_KEY` (Android 앱에서 사용)

**용도**:
- Android 모바일 앱에서 Gemini AI 기능 사용

**로드 방식**:
```kotlin
// Android 앱의 local.properties에서 로드
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

**우선순위**: ? **선택적** (모바일 앱 사용 시에만 필요)

---

## ? 정렬된 우선순위 목록

### ? 최우선 (필수)
1. **`genai_self_healing.py`**
   - API: `GEMINI_API_KEY` / `GOOGLE_API_KEY`
   - 용도: Self-Healing 시스템
   - 필수 여부: ? 필수

2. **`wicked_zerg_bot_pro.py`**
   - API: `GEMINI_API_KEY` / `GOOGLE_API_KEY`
   - 용도: 메인 봇 실행 (Self-Healing 초기화)
   - 필수 여부: ? 필수

### ? 중요 (기능 사용 시 필요)
3. **`local_training/strategy_audit.py`**
   - API: `GEMINI_API_KEY` (간접)
   - 용도: Build-Order Gap Analyzer
   - 필수 여부: ?? 기능 사용 시 필요

4. **`monitoring/mobile_app_android/`**
   - API: `GEMINI_API_KEY`
   - 용도: Android 모바일 앱
   - 필수 여부: ?? 모바일 앱 사용 시 필요

### ? 유틸리티 (의존성)
5. **`tools/load_api_key.py`**
   - API: 모든 API 키 (로더)
   - 용도: API 키 로드 유틸리티
   - 필수 여부: ? 다른 스크립트의 의존성

---

## ? API 키 설정 체크리스트

### 필수 설정 (최소)
- [ ] `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` 설정
  - 파일: `secrets/gemini_api.txt` 또는 `api_keys/GEMINI_API_KEY.txt`
  - 환경 변수: `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`

### 선택적 설정
- [ ] `GCP_PROJECT_ID` (Vertex AI 사용 시)
- [ ] `NGROK_AUTH_TOKEN` (외부 접속 필요 시)

---

## ? API 키 사용 흐름도

```
1. wicked_zerg_bot_pro.py
   └─> GenAISelfHealing 초기화
       └─> tools/load_api_key.py
           └─> secrets/gemini_api.txt 또는 환경 변수

2. genai_self_healing.py
   └─> tools/load_api_key.get_gemini_api_key()
       └─> Gemini API 호출

3. local_training/strategy_audit.py
   └─> generate_gemini_feedback()
       └─> GenAISelfHealing.analyze_gap_feedback()
           └─> Gemini API 호출
```

---

## ? 빠른 시작

### 1. API 키 설정
```bash
# secrets/ 폴더에 키 파일 생성
echo "YOUR_API_KEY_HERE" > secrets/gemini_api.txt
```

### 2. 테스트
```python
# Python에서 테스트
from tools.load_api_key import get_gemini_api_key
key = get_gemini_api_key()
print(f"API Key loaded: {key[:10]}..." if key else "API Key not found")
```

### 3. 실행
```bash
# 메인 봇 실행 (자동으로 API 키 로드)
python wicked_zerg_bot_pro.py
```

---

## ? 관련 문서

- **API 키 관리**: `docs/API_KEYS_MANAGEMENT.md`
- **필수 API 키**: `docs/REQUIRED_API_KEYS.md`
- **보안 폴더 구조**: `docs/SECURITY_FOLDER_STRUCTURE.md`

---

**마지막 업데이트**: 2026-01-14
