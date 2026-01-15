# Requirements.txt 확인 리포트

**작성일**: 2026-01-15  
**목적**: AI Arena 배포를 위한 필수 라이브러리 확인

---

## ? 필수 라이브러리 확인

### 1. Core SC2 API 라이브러리

**필수**: `burnysc2` (또는 `sc2` 패키지)

**현재 상태**: ? **포함됨**
```txt
burnysc2>=5.0.12
```

**코드 사용 확인**:
- `wicked_zerg_bot_pro.py`: `from sc2.bot_ai import BotAI`
- `wicked_zerg_bot_pro.py`: `from sc2.data import Race, Result`
- `wicked_zerg_bot_pro.py`: `from sc2.ids.ability_id import AbilityId`
- `wicked_zerg_bot_pro.py`: `from sc2.ids.unit_typeid import UnitTypeId`

**결론**: ? **정확히 명시되어 있음**

---

### 2. PyTorch (Neural Network)

**필수**: `torch` (PyTorch)

**현재 상태**: ? **포함됨**
```txt
torch>=2.0.0
```

**코드 사용 확인**:
- `zerg_net.py`: `import torch`
- `zerg_net.py`: `import torch.nn as nn`
- `zerg_net.py`: `import torch.nn.functional as F`
- `zerg_net.py`: `import torch.optim as optim`
- `wicked_zerg_bot_pro.py`: `import torch` (optional import)

**결론**: ? **정확히 명시되어 있음**

---

### 3. NumPy (Numerical Operations)

**필수**: `numpy`

**현재 상태**: ? **포함됨 (버전 제약 포함)**
```txt
numpy>=1.26.0,<2.0.0; python_version>="3.11"
numpy>=1.23.0,<2.0.0; python_version=="3.10"
```

**코드 사용 확인**:
- `zerg_net.py`: `import numpy as np`
- `wicked_zerg_bot_pro.py`: `import numpy as np`

**결론**: ? **정확히 명시되어 있음 (Python 버전별 제약 포함)**

---

### 4. 기타 필수 라이브러리

#### Loguru (로깅)
**현재 상태**: ? **포함됨**
```txt
loguru>=0.7.0
```

**코드 사용 확인**:
- `wicked_zerg_bot_pro.py`: `from loguru import logger`

#### sc2reader (리플레이 분석)
**현재 상태**: ? **포함됨**
```txt
sc2reader>=1.8.0
```

**코드 사용 확인**:
- `tools/download_and_train.py`: `import sc2reader`

#### requests (HTTP 요청)
**현재 상태**: ? **포함됨**
```txt
requests>=2.31.0
```

**코드 사용 확인**:
- `tools/download_and_train.py`: `import requests`

#### python-dotenv (환경 변수)
**현재 상태**: ? **포함됨**
```txt
python-dotenv>=1.0.0
```

#### google-generativeai (Gemini API)
**현재 상태**: ? **포함됨**
```txt
google-generativeai>=0.3.0
```

**코드 사용 확인**:
- `wicked_zerg_bot_pro.py`: `from genai_self_healing import GenAISelfHealing`

#### protobuf (중요: 버전 제약)
**현재 상태**: ? **포함됨 (버전 제약 포함)**
```txt
protobuf<=3.20.3
```

**설명**: `burnysc2`와 호환성을 위해 버전 제약이 필요합니다.

---

### 5. 선택적 라이브러리 (Optional)

#### psutil (시스템 모니터링)
**현재 상태**: ? **포함되지 않음**

**코드 사용 확인**:
- `wicked_zerg_bot_pro.py`: `import psutil` (optional import)

**권장 사항**: 
- AI Arena 배포 시 필수는 아니지만, 시스템 모니터링이 필요한 경우 추가 권장
- 현재는 `try/except`로 처리되어 있어 없어도 작동함

#### Flask, FastAPI (대시보드)
**현재 상태**: ? **포함됨**
```txt
flask>=3.0.0
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
```

**설명**: 모바일 대시보드 및 API 서버용 (선택적)

---

## ?? 누락된 라이브러리 확인

### 확인 결과: ? **모든 필수 라이브러리 포함됨**

다음 라이브러리들은 코드에서 사용되지만 `try/except`로 처리되어 있어 **선택적**입니다:

1. **psutil**: 시스템 모니터링 (선택적)
2. **Flask/FastAPI**: 대시보드 (선택적)
3. **google-api-python-client**: Google Tasks 연동 (선택적)

---

## ? AI Arena 배포용 최소 요구사항

### 필수 라이브러리 (Core)
1. ? `burnysc2>=5.0.12` - SC2 API
2. ? `torch>=2.0.0` - Neural Network
3. ? `numpy>=1.23.0,<2.0.0` - Numerical operations
4. ? `protobuf<=3.20.3` - Protocol buffers (버전 제약 중요)

### 권장 라이브러리 (Recommended)
5. ? `loguru>=0.7.0` - Enhanced logging
6. ? `python-dotenv>=1.0.0` - Environment variables

### 선택적 라이브러리 (Optional)
7. `sc2reader>=1.8.0` - Replay analysis (학습용, 배포 시 불필요)
8. `requests>=2.31.0` - HTTP requests (API 연동용)
9. `google-generativeai>=0.3.0` - Gemini API (Self-healing용)

---

## ? 결론

### ? Requirements.txt 상태: **완벽**

1. **필수 라이브러리**: 모두 포함됨
   - ? `burnysc2>=5.0.12`
   - ? `torch>=2.0.0`
   - ? `numpy` (버전 제약 포함)
   - ? `protobuf<=3.20.3` (중요: 버전 제약)

2. **버전 제약**: 적절히 설정됨
   - NumPy: Python 버전별 제약 포함
   - Protobuf: `burnysc2` 호환성을 위한 상한선 설정

3. **선택적 라이브러리**: 적절히 분류됨
   - 대시보드/API 관련 라이브러리는 선택적
   - 코드에서 `try/except`로 처리되어 있어 없어도 작동

### ?? 추가 권장 사항

1. **psutil 추가 고려** (선택적):
   ```txt
   psutil>=5.9.0  # 시스템 모니터링 (optional)
   ```

2. **AI Arena 최소 배포용 requirements.txt 생성 고려**:
   - Core 라이브러리만 포함한 `requirements-arena.txt` 생성
   - 학습/대시보드 관련 라이브러리 제외

---

**최종 상태**: ? **모든 필수 라이브러리가 정확히 명시되어 있음**
