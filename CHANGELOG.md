# Changelog

All notable changes to WickedZergBotPro are documented here.

## [Phase 22] - 2026-03-28
### Dead Code 일괄 활성화
- 36개 미활성 매니저 발견 (bot_step_integration.py 전수 검사)
- 10대 핵심 매니저 import/init 완료:
  - CreepExpansionSystem, CreepDenialSystem, CreepHighwayManager
  - SpellcasterAutomation, OverlordSafetyManager, IdleUnitManager
  - DynamicCounterSystem, DefeatDetection, BattlePreparationSystem
  - UpgradeCoordinationSystem
- Arena 업로드용 패키지 생성기 (`create_arena_package.py`) 추가

## [Phase 21] - 2026-03-28
### 종족별 특화 대응
- **ZvT 카운터 신규**: 바이오(바네돌진), 메카(레바저담즙), 공중(히드라+코럽터), 헬리온(퀸+바퀴)
- **ZvP 바이퍼 추가**: 캐리어 3+ 시 바이퍼 어둠 집어삼키기 대응
- **ZvZ 럴커 전환**: 6분+ 로치/히드라 미러 시 럴커 20% 포지셔닝 우위

## [Phase 20] - 2026-03-28
### 공격 타이밍 최적화
- 서플라이 기반 점진적 공격 임계값 (4분:12 / 8분:20 / 10분:30 / 후반:40)
- 적 확장/테크 취약 시점 감지 → 임계값 70% 하향 (타이밍 러시)
- 멀티프롱 공격: 80서플+ 시 저글링 6~8마리 견제팀 분리
- IntelManager에 enemy_expanding/teching Blackboard 전파

## [Phase 19] - 2026-03-28
### 후반 전환 시스템
- **HiveTechMaximizer 활성화**: dead code → import/init 완료 (울트라/브루드/바이퍼)
- 후반 유닛 비율에 울트라리스크 20% 추가 (3종족 모두)
- 미네랄 뱅킹 소비: 1500+ 저글링 스팸, 800+ 울트라 우선
- 기지 파괴 시 자동 재확장 (2기지 이하 트리거)
- commander_knowledge.json 후반 비율 전면 개편

## [Phase 18] - 2026-03-28
### 맵 컨트롤 시스템
- 랠리포인트 크립 위 우선 배치 (45%→25% 스캔)
- 전진 스파인 크롤러 (8분+ 3기지+ 크립 위, 최대 4개)
- 공격적 크립 확장 (적진 75%까지 다단계 웨이포인트)
- 종양 릴레이 자동화 (매립 종양 → 적 방향 자동 확산)
- 측면 크립 확장 (8분+ 좌우 15도 오프셋)

## [Phase 17] - 2026-03-28
### 정찰/대응 강화
- 카운터빌드 속도: confidence 0.2→0.1, 폴백 3분→2분30초
- 치즈 즉시 대응: Blackboard 긴급전파, 저글링60% 비상비율
- 오버로드 정찰 개선: 맵센터→적 자연확장 경유
- Hidden Tech 경보: DT/공중위협 → urgent_spore/spine 플래그

## [Phase 16] - 2026-03-28
### 경제 최적화
- 66드론 하드 컷오프 (3기지 포화 시 군대 전환)
- 가스 뱅킹 조기감지: 임계값 500→300
- 매크로 해처리 강화: 미네랄 1500→600

## [Phase 15] - 2026-03-28
### 전투 마이크로 강화
- 저HP(30% 미만) 자동후퇴 (바네링/저글링 제외)
- 3단계 점진적 후퇴 (2.0x 긴급/1.5x 표준/1.3x 재집결)
- 포커스파이어: 극단적 스플래시 위협(거리 4 미만)만 회피
- 약한 적 우선 공격 (체력비율 + 체력/1000 스코어링)

## [Phase 14] - 2026-03-28
### 변이 유닛 활성화
- UnitMorphManager 활성화 (dead code → import/init)
- 4종 변이: 바네링, 레바저, 럴커, 브루드로드
- 동적 비율: Blackboard 연동, 전략 비율 2x 적용
- 테크 건물 자동 보장: 바네링둥지/럴커소굴/바퀴소굴

## [Phase 13] - 2026-03-28
### 자동생산 + MicroV3
- 비율 기반 군대 자동생산 (빌드오더 종료 후)
- AdvancedMicroControllerV3 실제 초기화/활성화
- 테스트 167 passed / 0 failed / 20 skipped

## [Phase 12] - 2026-03-28
### 디컨플릭트 + 하이브 가속
- 방어-공격 유닛태그 추적 + Blackboard 연동
- 공격 집결 시스템 복원 (즉시공격→70% 집결 후)
- 카운터 폴백 전략 (종족별 안전 유닛비율)
- Hive ~8분 완성 (인페핏 5분, 하이브 6분)
- 서플라이 버퍼 MID 3→8, EARLY 4→6
