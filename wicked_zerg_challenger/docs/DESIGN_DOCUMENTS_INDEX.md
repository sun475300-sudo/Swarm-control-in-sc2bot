# ? 설계 문서 인덱스

**작성일**: 2026-01-14  
**목적**: 프로젝트의 설계 문서 및 와이어프레임 모음

---

## ? 핵심 설계 문서

### 1. Mobile GCS UI/UX 설계도
**파일**: `docs/MOBILE_GCS_UI_DESIGN.md`

모바일 Ground Control Station의 완전한 UI/UX 설계:
- ? 메인 대시보드 와이어프레임
- ? 상세 통계 화면 설계
- ?? 빌드 오더 분석 화면
- ? 실시간 알림 화면
- ? 컬러 스킴 및 타이포그래피
- ? 반응형 레이아웃
- ? 화면 전환 플로우

**상태**: ? 설계 완료, 구현 준비 완료

---

### 2. Build-Order Gap Analyzer 상세 설계
**파일**: `docs/BUILD_ORDER_GAP_ANALYZER_DETAILED.md`

프로게이머와 봇의 빌드 오더를 프레임 단위로 대조 분석하는 시스템:
- ?? 시스템 아키텍처 다이어그램
- ? 분석 로직 상세 (Time Gap, Sequence Error, Resource Efficiency)
- ? 데이터 플로우
- ? Gemini Self-Healing 연동
- ? 성능 지표
- ? 향후 개선 계획

**상태**: ? 설계 완료, 구현 완료 (`local_training/strategy_audit.py`)

---

## ? 빠른 참조

### Mobile GCS
- **빠른 시작**: `docs/MOBILE_APP_COMPLETE_GUIDE.md`
- **UI 설계**: `docs/MOBILE_GCS_UI_DESIGN.md`
- **빌드 가이드**: `docs/ANDROID_APP_BUILD_GUIDE.md`

### Build-Order Gap Analyzer
- **사용 가이드**: `docs/BUILD_ORDER_GAP_ANALYZER.md`
- **상세 설계**: `docs/BUILD_ORDER_GAP_ANALYZER_DETAILED.md`
- **구현 코드**: `local_training/strategy_audit.py`

---

## ? 설계 원칙

### Mobile GCS
1. **SC2 테마 일관성**: Zerg 종족의 어두운 네이비와 네온 그린
2. **실시간성**: 1초 단위 업데이트
3. **직관성**: 한 눈에 파악 가능한 정보 구조
4. **반응형**: 모바일/태블릿 최적화

### Build-Order Gap Analyzer
1. **정확성**: ±1초 정확도
2. **자동화**: 게임 종료 시 자동 분석
3. **자기 치유**: Gemini를 통한 자동 코드 패치
4. **학습 연동**: CurriculumManager와 통합

---

## ? 구현 상태

### ? 완료
- [x] Mobile GCS UI 설계도
- [x] Build-Order Gap Analyzer 설계
- [x] Build-Order Gap Analyzer 구현
- [x] Gemini Self-Healing 연동
- [x] CurriculumManager 연동

### ? 진행 중
- [ ] Mobile GCS UI 구현 (PWA 기본 구조 완료)
- [ ] 실시간 차트 통합
- [ ] 다중 인스턴스 모니터링

### ? 계획
- [ ] 실시간 빌드 오더 분석
- [ ] 예측 분석 기능
- [ ] 머신러닝 통합

---

## ? 관련 문서

### 아키텍처
- `README.md` - 프로젝트 개요
- `프로젝트_전체_진행_보고서.md` - 전체 진행 상황

### 사용 가이드
- `docs/MOBILE_APP_COMPLETE_GUIDE.md` - 모바일 앱 제작 가이드
- `docs/BUILD_ORDER_GAP_ANALYZER.md` - Gap Analyzer 사용법

### API 문서
- `api_keys/README.md` - API 키 관리
- `docs/API_KEYS_MANAGEMENT.md` - API 키 관리 가이드

---

**마지막 업데이트**: 2026-01-14
