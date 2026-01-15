# 대규모 리팩토링 계획

**생성 일시**: 2026-01-15
**목적**: 파일 구조 재구성, 클래스 분리/통합, 의존성 최적화

---

## 1. 클래스 분석

총 140개의 클래스를 발견했습니다.

### 큰 클래스 (메서드 20개 이상) - 분리 권장

- `tools\download_and_train.py:187` - `ReplayDownloader` (25개 메서드)
- `combat_manager.py:26` - `CombatManager` (22개 메서드)

## 2. 의존성 분석

총 11개 파일의 의존성을 분석했습니다.

### 순환 의존성 검사

순환 의존성을 찾아 최적화가 필요합니다.

## 3. 파일 구조 재구성 제안

### 현재 구조

```
wicked_zerg_challenger/
├── bat/
├── tools/
├── monitoring/
├── local_training/
└── 설명서/
```

### 제안 구조

```
wicked_zerg_challenger/
├── core/              # 핵심 봇 로직
│   ├── bot.py
│   ├── managers/      # 매니저 클래스들
│   └── utils/         # 공통 유틸리티
├── training/          # 훈련 관련
├── tools/             # 유틸리티 도구
├── monitoring/        # 모니터링
└── docs/             # 문서
```

## 4. 클래스 분리 및 통합 제안

### 분리 권장 클래스

#### `CombatManager` (combat_manager.py)

- **메서드 수**: 22개
- **제안**: 기능별로 여러 클래스로 분리
  - 예: `CombatManagerCore`, `CombatManagerManager`, `CombatManagerUtils`

#### `ReplayDownloader` (tools\download_and_train.py)

- **메서드 수**: 25개
- **제안**: 기능별로 여러 클래스로 분리
  - 예: `ReplayDownloaderCore`, `ReplayDownloaderManager`, `ReplayDownloaderUtils`

## 5. 의존성 최적화 제안

### 최적화 방안

1. **공통 유틸리티 모듈 생성**
   - `core/utils/common.py`에 공통 함수 통합
   - 중복 import 제거

2. **인터페이스 추상화**
   - 공통 인터페이스 정의
   - 의존성 역전 원칙 적용

3. **모듈 재구성**
   - 관련 기능을 같은 모듈로 그룹화
   - 순환 의존성 제거

