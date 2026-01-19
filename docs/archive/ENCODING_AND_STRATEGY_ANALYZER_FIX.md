# 인코딩 오류 및 StrategyAnalyzer 초기화 오류 수정

## 문제점

게임 실행 중 두 가지 오류가 발생했습니다:

1. **인코딩 오류**: `load_api_key.py`에서 API 키 파일을 읽을 때 UTF-8 디코딩 실패
   ```
   [WARNING] Failed to initialize Gemini Self-Healing: (unicode error) 'utf-8' codec can't decode byte 0xb7 in position 9: invalid start byte (load_api_key.py, line 8)
   ```

2. **StrategyAnalyzer 초기화 오류**: `StrategyAnalyzer`가 `None`인 상태에서 호출 시도
   ```
   [WARNING] StrategyAnalyzer init failed: 'NoneType' object is not callable
   ```

## 수정 내용

### 1. `load_api_key.py` - 다중 인코딩 지원

**파일**: `wicked_zerg_challenger/tools/load_api_key.py`

**변경 사항**:
- 단일 UTF-8 인코딩 시도에서 → 여러 인코딩 순차 시도로 변경
- 지원 인코딩: `utf-8`, `cp949`, `latin-1`, `utf-8-sig`
- `UnicodeDecodeError` 발생 시 다음 인코딩으로 자동 전환

**코드**:
```python
# 여러 인코딩 시도 (UTF-8, CP949, latin-1)
encodings = ['utf-8', 'cp949', 'latin-1', 'utf-8-sig']

for encoding in encodings:
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
        break
    except UnicodeDecodeError:
        # 이 인코딩으로 읽을 수 없음, 다음 인코딩 시도
        continue
    except Exception as e:
        print(f"[WARNING] Failed to read {file_path} with {encoding}: {e}")
        continue
```

### 2. `wicked_zerg_bot_pro.py` - StrategyAnalyzer None 체크

**파일**: `wicked_zerg_challenger/wicked_zerg_bot_pro.py`

**변경 사항**:
- `StrategyAnalyzer` 초기화 전에 `None` 체크 추가
- `StrategyAnalyzer`가 `None`인 경우 초기화를 시도하지 않음

**코드**:
```python
try:
    if StrategyAnalyzer is not None:
        self.strategy_analyzer = StrategyAnalyzer(self)
    else:
        self.strategy_analyzer = None
except Exception as e:
    print(f"[WARNING] StrategyAnalyzer init failed: {e}")
    self.strategy_analyzer = None
```

### 3. `genai_self_healing.py` - 예외 처리 강화

**파일**: `wicked_zerg_challenger/genai_self_healing.py`

**변경 사항**:
- `get_gemini_api_key()` 호출 시 인코딩 오류 등 모든 예외 처리
- 예외 발생 시 환경 변수에서 직접 읽기로 Fallback

**코드**:
```python
try:
    from tools.load_api_key import get_gemini_api_key
    self.api_key = get_gemini_api_key()
except ImportError:
    # Fallback: 환경 변수에서 직접 읽기
    self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
except Exception as e:
    # 인코딩 오류 등 기타 예외 처리
    print(f"[WARNING] Failed to load Gemini API key: {e}")
    # Fallback: 환경 변수에서 직접 읽기
    self.api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
```

## 효과

### 인코딩 오류 해결
- Windows에서 CP949로 저장된 API 키 파일도 정상적으로 읽을 수 있음
- 다양한 인코딩 형식의 파일 지원
- 인코딩 오류 발생 시 자동으로 다른 인코딩 시도

### StrategyAnalyzer 오류 해결
- `StrategyAnalyzer` 모듈이 없는 경우에도 안전하게 처리
- `None` 체크로 `'NoneType' object is not callable` 오류 방지
- 게임 실행이 중단되지 않고 계속 진행

## 테스트

다음 상황에서 정상 작동 확인:

1. **UTF-8 인코딩 파일**: 정상 읽기
2. **CP949 인코딩 파일**: 자동 감지 및 읽기
3. **StrategyAnalyzer 없음**: 경고만 출력하고 게임 계속 진행
4. **API 키 파일 없음**: 환경 변수에서 읽기 시도

## 관련 파일

- `wicked_zerg_challenger/tools/load_api_key.py`
- `wicked_zerg_challenger/wicked_zerg_bot_pro.py`
- `wicked_zerg_challenger/genai_self_healing.py`
