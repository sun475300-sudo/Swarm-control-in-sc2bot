# 클로드 코드 빠른 시작 가이드

**작성 일시**: 2026-01-15  
**목적**: 클로드 코드를 즉시 활용할 수 있는 빠른 시작 가이드

---

## ? 3단계 빠른 시작

### Step 1: 클로드 코드 설치 및 실행

```bash
# Node.js 설치 확인
node --version

# 클로드 코드 설치
npm install -g @anthropic-ai/claude-code

# API 키 설정
export ANTHROPIC_API_KEY="your-api-key-here"

# 클로드 코드 실행
claude
```

### Step 2: 프로젝트 디렉토리로 이동

```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
```

### Step 3: 첫 작업 요청

클로드 코드에게 다음 중 하나를 요청:

---

## ? 즉시 실행 가능한 작업

### 작업 1: 사용하지 않는 import 제거 (가장 안전)

```
CODE_DIET_ANALYSIS_REPORT.md를 읽고,
67개 파일에서 발견된 사용하지 않는 import를 제거해줘.

주의사항:
- 간접 사용 가능한 import는 제거하지 않음
- 변경 후 syntax check 실행
```

### 작업 2: 코드 스타일 통일 (가장 안전)

```
CONTINUOUS_IMPROVEMENT_REPORT.md를 읽고,
발견된 916개의 스타일 이슈를 수정해줘.

수정 항목:
- 줄 길이 100자 이하
- 탭을 공백으로 변환
- 연속된 공백 정리

주의사항:
- 로직 변경 없음
- 스타일만 수정
```

### 작업 3: 중복 함수 통합 (중간 난이도)

```
REFACTORING_ANALYSIS_REPORT.md의 '중복 함수' 섹션에서
상위 10개의 중복 함수를 공통 유틸리티로 추출해줘.

작업 순서:
1. 상위 10개 중복 함수 패턴 분석
2. utils/common.py에 공통 함수 생성
3. 모든 사용 위치 업데이트
4. syntax check 실행
```

### 작업 4: 긴 함수 분리 (중간 난이도)

```
REFACTORING_ANALYSIS_REPORT.md의 '긴 함수' 섹션에서
상위 10개의 긴 함수를 작은 함수로 분리해줘.

각 함수는:
- 최대 50줄 이하
- 단일 책임 원칙 준수
- 명확한 함수 이름
```

### 작업 5: 파일 구조 재구성 (고난이도)

```
LARGE_SCALE_REFACTORING_PLAN.md를 읽고 파일 구조를 재구성해줘.

새로운 구조:
- core/ (핵심 봇 로직)
- core/managers/ (매니저 클래스들)
- core/utils/ (공통 유틸리티)
- training/ (훈련 관련)

주의사항:
- Git 커밋 필수
- 단계별 검증
- 테스트 실행 필수
```

---

## ? 추천 작업 순서

### Phase 1: 안전한 작업 (즉시 실행)
1. ? 사용하지 않는 import 제거
2. ? 코드 스타일 통일

### Phase 2: 중간 난이도 작업
3. ? 중복 함수 통합 (상위 10개)
4. ? 긴 함수 분리 (상위 10개)

### Phase 3: 고난이도 작업
5. ? 파일 구조 재구성
6. ? 클래스 분리
7. ? 의존성 최적화

---

## ? 클로드 코드 명령어 예시

### 예시 1: 간단한 요청
```
사용하지 않는 import를 제거해줘.
```

### 예시 2: 구체적인 요청
```
REFACTORING_ANALYSIS_REPORT.md를 읽고,
'중복 함수' 섹션의 상위 10개를 공통 유틸리티로 추출해줘.
```

### 예시 3: 단계별 요청
```
다음 작업을 순차적으로 수행해줘:
1. CODE_DIET_ANALYSIS_REPORT.md 분석
2. 사용하지 않는 import 제거
3. 변경 사항 검증
4. 리포트 생성
```

---

## ? 작업 전 체크리스트

### 필수 확인 사항
- [ ] Git 커밋 (변경 전 백업)
- [ ] 생성된 리포트 확인
- [ ] 작업 범위 확인

### 작업 중 체크리스트
- [ ] 단계별 검증
- [ ] Syntax check 실행
- [ ] 변경 사항 확인

### 작업 후 체크리스트
- [ ] 테스트 실행
- [ ] 변경 사항 커밋
- [ ] 리포트 확인

---

## ? 문제 해결

### 문제 1: 클로드 코드가 파일을 찾지 못함
```
해결: 절대 경로 사용
예: D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\REFACTORING_ANALYSIS_REPORT.md
```

### 문제 2: 변경 사항이 예상과 다름
```
해결: 단계별로 요청하고 각 단계마다 확인
```

### 문제 3: 에러 발생
```
해결: 
1. 변경 사항 롤백 (Git 사용)
2. 문제 분석
3. 더 구체적인 요청
```

---

## ? 참고 자료

- [작업 템플릿](./CLAUDE_CODE_TASK_TEMPLATES.md) - 상세 작업 템플릿
- [클로드 코드 완전 활용 가이드](./CLAUDE_CODE_COMPLETE_GUIDE.md)
- [리팩토링 분석 리포트](./REFACTORING_ANALYSIS_REPORT.md)
- [대규모 리팩토링 계획](./LARGE_SCALE_REFACTORING_PLAN.md)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-15
