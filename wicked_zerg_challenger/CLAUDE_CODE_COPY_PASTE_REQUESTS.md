# 클로드 코드 복사-붙여넣기 요청 텍스트

**작성 일시**: 2026-01-15  
**목적**: 클로드 코드에게 바로 복사해서 사용할 수 있는 구체적인 요청 텍스트

---

## ? 즉시 사용 가능한 요청 텍스트

### 요청 1: 사용하지 않는 import 제거 (가장 안전, 추천)

```
CODE_DIET_ANALYSIS_REPORT.md를 읽고, 
67개 파일에서 발견된 사용하지 않는 import를 제거해줘.

작업 순서:
1. CODE_DIET_ANALYSIS_REPORT.md 파일 읽기
2. 각 파일에서 사용하지 않는 import 확인
3. 간접 사용 가능한 import는 제거하지 않음 (os, sys, json, pathlib, typing, collections, datetime, logging 등)
4. 사용하지 않는 import 제거
5. 변경된 파일들을 syntax check로 검증
6. 변경 사항을 요약하여 리포트 생성

주의사항:
- 기존 기능이 손상되지 않도록 주의
- 변경 후 테스트 실행 권장
```

---

### 요청 2: 코드 스타일 통일 (안전, 추천)

```
CONTINUOUS_IMPROVEMENT_REPORT.md를 읽고,
발견된 916개의 스타일 이슈를 수정해줘.

수정 항목:
1. 줄 길이 100자 이하로 조정
2. 탭 문자를 공백 4개로 변환
3. 연속된 공백 정리 (문자열 내부 제외)

작업 순서:
1. CONTINUOUS_IMPROVEMENT_REPORT.md 파일 읽기
2. 각 파일의 스타일 이슈 확인
3. PEP 8 준수하도록 수정
4. 변경된 파일들을 syntax check로 검증
5. 변경 사항을 요약하여 리포트 생성

주의사항:
- 로직 변경 없음 (스타일만 수정)
- 문자열 내부의 공백은 변경하지 않음
- 변경 후 테스트 실행 권장
```

---

### 요청 3: 중복 함수 통합 (중간 난이도)

```
REFACTORING_ANALYSIS_REPORT.md를 읽고,
'중복 함수' 섹션의 상위 10개 중복 함수 패턴을 공통 유틸리티로 추출해줘.

작업 순서:
1. REFACTORING_ANALYSIS_REPORT.md 파일 읽기
2. 상위 10개 중복 함수 패턴 분석 (main 함수 제외)
3. 각 패턴의 공통 로직 식별
4. utils/common.py 파일 생성 (없으면)
5. 공통 함수를 utils/common.py에 추가
6. 모든 중복 함수 사용 위치를 공통 함수 호출로 변경
7. Import 문 업데이트
8. 변경된 파일들을 syntax check로 검증
9. 변경 사항을 요약하여 리포트 생성

주의사항:
- main() 함수는 각 파일의 진입점이므로 통합하지 않음
- 기존 기능이 손상되지 않도록 주의
- 각 파일의 컨텍스트를 고려하여 수정
- 변경 후 테스트 실행 필수
```

---

### 요청 4: 긴 함수 분리 (중간 난이도)

```
REFACTORING_ANALYSIS_REPORT.md를 읽고,
'긴 함수' 섹션의 상위 10개 긴 함수를 작은 함수로 분리해줘.

작업 순서:
1. REFACTORING_ANALYSIS_REPORT.md 파일 읽기
2. 상위 10개 긴 함수 분석
3. 각 함수를 논리적 단위로 분리
4. 각 함수를 최대 50줄 이하로 분리
5. 단일 책임 원칙을 준수하도록 함수 이름 명확화
6. 변경된 파일들을 syntax check로 검증
7. 변경 사항을 요약하여 리포트 생성

주의사항:
- 함수 간 의존성을 고려
- 변수 스코프 주의
- 기존 기능 유지
- 변경 후 테스트 실행 필수
```

---

### 요청 5: 큰 파일 분리 (고난이도)

```
CONTINUOUS_IMPROVEMENT_REPORT.md를 읽고,
다음 큰 파일들을 작은 모듈로 분리해줘:

1. wicked_zerg_bot_pro.py (6575줄)
2. production_manager.py (6537줄)
3. economy_manager.py (2978줄)

작업 순서:
1. 각 파일의 책임 분석
2. 기능별로 여러 모듈로 분리
3. 새로운 디렉토리 구조 생성
4. 파일 이동 및 import 경로 업데이트
5. 변경된 파일들을 syntax check로 검증
6. 변경 사항을 요약하여 리포트 생성

주의사항:
- Git 커밋 필수 (변경 전)
- 단계별로 커밋 권장
- 기존 기능 유지
- 변경 후 테스트 실행 필수
```

---

### 요청 6: 복잡한 함수 단순화 (중간 난이도)

```
REFACTORING_ANALYSIS_REPORT.md를 읽고,
'복잡한 함수' 섹션의 상위 10개 복잡한 함수를 단순화해줘.

작업 순서:
1. REFACTORING_ANALYSIS_REPORT.md 파일 읽기
2. 상위 10개 복잡한 함수 분석
3. 순환 복잡도를 10 이하로 낮추기
4. 조건문을 early return 패턴으로 변경
5. 복잡한 로직을 헬퍼 함수로 분리
6. 중첩된 조건문을 평탄화
7. 변경된 파일들을 syntax check로 검증
8. 변경 사항을 요약하여 리포트 생성

주의사항:
- 로직의 정확성 유지
- 가독성 향상에 중점
- 변경 후 테스트 실행 필수
```

---

### 요청 7: 파일 구조 재구성 (고난이도)

```
LARGE_SCALE_REFACTORING_PLAN.md를 읽고 파일 구조를 재구성해줘.

새로운 구조:
wicked_zerg_challenger/
├── core/              # 핵심 봇 로직
│   ├── bot.py         # 메인 봇 클래스
│   ├── managers/      # 매니저 클래스들
│   │   ├── combat_manager.py
│   │   ├── economy_manager.py
│   │   ├── production_manager.py
│   │   └── ...
│   └── utils/         # 공통 유틸리티
│       └── common.py
├── training/          # 훈련 관련
│   ├── main_integrated.py
│   └── ...
├── tools/             # 유틸리티 도구
├── monitoring/        # 모니터링
└── docs/             # 문서

작업 순서:
1. LARGE_SCALE_REFACTORING_PLAN.md 파일 읽기
2. 새로운 디렉토리 구조 생성
3. 파일 이동
4. 모든 파일의 import 경로 업데이트
5. 변경된 파일들을 syntax check로 검증
6. 변경 사항을 요약하여 리포트 생성

주의사항:
- Git 커밋 필수 (변경 전)
- 단계별로 커밋 권장
- 기존 기능 유지
- 변경 후 테스트 실행 필수
```

---

### 요청 8: 클래스 분리 (고난이도)

```
LARGE_SCALE_REFACTORING_PLAN.md를 읽고,
다음 큰 클래스들을 기능별로 분리해줘:

1. CombatManager (combat_manager.py, 22개 메서드)
2. ReplayDownloader (tools/download_and_train.py, 25개 메서드)

작업 순서:
1. LARGE_SCALE_REFACTORING_PLAN.md 파일 읽기
2. 각 클래스의 책임 분석
3. 기능별로 여러 클래스로 분리
   - CombatManager -> CombatCore, CombatTactics, CombatMicro
   - ReplayDownloader -> ReplayDownloaderCore, ReplayDownloaderManager
4. 의존성 업데이트
5. 변경된 파일들을 syntax check로 검증
6. 변경 사항을 요약하여 리포트 생성

주의사항:
- 단일 책임 원칙 준수
- 기존 기능 유지
- 변경 후 테스트 실행 필수
```

---

### 요청 9: 의존성 최적화 (고난이도)

```
LARGE_SCALE_REFACTORING_PLAN.md를 읽고 의존성을 최적화해줘.

작업 순서:
1. LARGE_SCALE_REFACTORING_PLAN.md 파일 읽기
2. 프로젝트 전체를 분석하여 순환 의존성 식별
3. 공통 유틸리티 모듈 생성 (core/utils/common.py)
4. 중복 import 제거
5. 인터페이스 추상화 (공통 인터페이스 정의)
6. 의존성 역전 원칙 적용
7. 순환 의존성 제거
8. 변경된 파일들을 syntax check로 검증
9. 변경 사항을 요약하여 리포트 생성

주의사항:
- 기존 기능 유지
- 점진적 개선
- 변경 후 테스트 실행 필수
```

---

### 요청 10: 종합 개선 작업 (전체 프로세스)

```
다음 작업들을 순차적으로 수행해줘:

1단계: 분석
- REFACTORING_ANALYSIS_REPORT.md 읽기
- CONTINUOUS_IMPROVEMENT_REPORT.md 읽기
- CODE_DIET_ANALYSIS_REPORT.md 읽기

2단계: 안전한 개선 (우선순위: 높음)
- 사용하지 않는 import 제거 (67개 파일)
- 코드 스타일 통일 (916개 이슈)

3단계: 중복 코드 제거 (우선순위: 중간)
- 중복 함수 통합 (상위 10개)
- 긴 함수 분리 (상위 10개)

4단계: 검증
- 모든 변경된 파일들을 syntax check로 검증
- 변경 사항 요약 리포트 생성

각 단계마다:
- 변경 사항 요약
- 검증 결과
- 다음 단계 제안

주의사항:
- 단계별로 Git 커밋 권장
- 각 단계마다 테스트 실행
- 문제 발생 시 롤백 가능하도록
```

---

## ? 사용 방법

### Step 1: 클로드 코드 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
claude
```

### Step 2: 요청 텍스트 복사
위의 요청 텍스트 중 하나를 선택하여 복사

### Step 3: 클로드 코드에 붙여넣기
클로드 코드 터미널에 붙여넣고 Enter

### Step 4: 결과 확인
```bash
# 변경 사항 확인
git diff

# 검증
python tools\claude_code_executor.py --validate [변경된 파일들]
```

---

## ? 작업 난이도별 추천

### 초보자 (안전한 작업)
- ? 요청 1: 사용하지 않는 import 제거
- ? 요청 2: 코드 스타일 통일

### 중급자 (중간 난이도)
- ? 요청 3: 중복 함수 통합
- ? 요청 4: 긴 함수 분리
- ? 요청 6: 복잡한 함수 단순화

### 고급자 (고난이도)
- ? 요청 5: 큰 파일 분리
- ? 요청 7: 파일 구조 재구성
- ? 요청 8: 클래스 분리
- ? 요청 9: 의존성 최적화

### 전문가 (종합 작업)
- ? 요청 10: 종합 개선 작업

---

## ? 팁

### 효과적인 요청 방법

1. **구체적인 요청**
   - ? "코드를 개선해줘"
   - ? 위의 요청 템플릿 사용

2. **단계별 확인**
   - 큰 작업은 작은 단계로 나누기
   - 각 단계마다 검증하기

3. **리포트 활용**
   - 생성된 리포트를 참조하여 구체적으로 요청
   - 리포트의 파일 경로와 라인 번호 활용

---

## ? 참고 문서

- [작업 템플릿](./CLAUDE_CODE_TASK_TEMPLATES.md) - 상세 작업 템플릿
- [빠른 시작 가이드](./CLAUDE_CODE_QUICK_START.md) - 3단계 빠른 시작
- [완전 활용 가이드](./CLAUDE_CODE_COMPLETE_GUIDE.md) - 상세 가이드
- [리팩토링 분석 리포트](./REFACTORING_ANALYSIS_REPORT.md)
- [대규모 리팩토링 계획](./LARGE_SCALE_REFACTORING_PLAN.md)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-15
