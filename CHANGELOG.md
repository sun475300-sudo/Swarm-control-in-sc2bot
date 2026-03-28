# Changelog

All notable changes to WickedZergBotPro are documented here.

## [Phase 42] - 2026-03-28
### 다중 언어 커버 — Python 적 AI 예측 + TypeScript 전투력 위젯
- **Python** `intel_manager.py` supply 추정 수정: `supply_cost` 속성 없음 → 30종 종족별 정확한 룩업 테이블 (ZvT Marine=1, Siege=3, Thor=6 등)
- **Python** `intel_manager.py` 적 공격 타이밍 예측: 테크 건물 + 병력 규모 기반 예상 공격 시점(초) 계산 → Blackboard `enemy_attack_predicted_time` / `enemy_attack_imminent` 전파
- **TypeScript** `Monitor.tsx` 전투력 비율 분석 위젯 추가: KDA 계산, 처치 비율 바, 병력/처치/손실 트리오 카드

## [Phase 41] - 2026-03-28
### 전투 의사결정 고도화 — HP 가중 전투력 + 후퇴 판단 최적화
- `_SUPPLY_TABLE` 정확한 공급 비용 테이블: 13종 저그 유닛 (이전: `supply_cost` 속성 없음 → 모두 1로 계산)
- `_combat_power()` HP 가중 전투력: supply × HP% (이전: 완피 울트라리스크=1 vs 저글링=1)
- `_evaluate_army_retreat` 필터 O(N×M)→O(N+M): 군집 중심 기반으로 교전 유닛 판별 (이전: per-unit `closer_than` 루프)
- `combat_types` 퀸 추가: `QUEEN` 포함하여 방어 퀸도 후퇴 판단에 포함

## [Phase 40] - 2026-03-28
### 통합 검증 + 아레나 패키지 재생성
- Phase 39까지 전체 구문 검증: 8개 핵심 파일 ALL OK
- 테스트 결과: 167 passed / 20 skipped / 15 errors (모두 protobuf 버전 충돌, 봇 코드 무관)
- 아레나 패키지 재생성: WickedZergBotPro_Arena_20260328_2344.zip (491 files, 15.2 MB)

## [Phase 39] - 2026-03-28
### 경제 고도화 — 가스/드론 생산 버그 수정
- `_reduce_gas_workers` 필터 버그 수정: `order_target == extractor.tag` 단독 필터는 익스트랙터 내부 일꾼을 놓침 → `is_carrying_vespene OR order_target` + 거리 12 이내로 확장
- 초반 가스 감소 보호: 게임 시작 3분 이내에는 가스 일꾼 감소 금지 (이전: gas>500/mineral<300 조건 충족 시 즉시 감소 → 초반 테크 건물 건설 중 가스 고갈)
- `_boost_gas_workers` 조기 종료 제거: 첫 번째 익스트랙터 보충 후 `return` 삭제 → 모든 부족한 익스트랙터 동시 채우기 (이전: 익스트랙터 1개만 보충)

## [Phase 38] - 2026-03-28
### 전투 집결 시스템 개선
- 전투 중 유닛 강제 후퇴 방지: 근처에 적 있으면 랠리 이동 명령 생략 (이전: 20타일 밖이면 전투 중에도 후퇴)
- 랠리 포인트 기준 개선: 맵 중앙 최근접 기지 기준 (이전: 항상 본진 — 3+ 베이스 이후에도 본진 앞에 고정)

## [Phase 37] - 2026-03-28
### 후반 유닛 전환 최적화
- GREATERSPIRE 후 뮤탈/코럽터 생산 수정: SPIRE→GREATERSPIRE 변이 후 생산 차단 해제
- VIPER tech 요구사항 추가: HIVE 필요 조건 (이전: 없어서 Hive 없이 생산 시도)

## [Phase 36] - 2026-03-28
### 퀸 매크로 강화
- 방어 탐지 거리 하향: 30/25 → 20/18 타일 (이전: 30타일 밖 적에도 인젝트 포기)
- 퀸 0마리 위기 시 강제 생산: 모든 해처리 busy여도 즉시 생산 (이전: 영구 미생산)
- print 스팸 제거: [QUEEN_DEBUG]/[QUEEN] 매 30초/매 배정 print → logger.debug

## [Phase 35] - 2026-03-28
### 통합 검증 + 아레나 패키지
- Phase 31~34 모든 변경 파일 구문 검증 완료 (syntax OK)
- 매니저 연결 검증: harassment_coordinator, early_scout, overlord_safety, build_order_system, defense_coordinator 모두 bot_step_integration 정상 연결
- 테스트 최종 결과: 321 passed / 1 failed (pre-existing) / 7 skipped
- 아레나 패키지 재생성: WickedZergBotPro_Arena_20260328.zip (491 files, 15.2 MB)

## [Phase 34] - 2026-03-28
### 실전 메타 대응
- ZvZ 저글링 카운터 시간 제한 제거: game_time<300 삭제 → 5분 이후에도 10마리+ 저글링 대응
- ZvT 헬리온 카운터 시간 연장: 4분→5분 (4:30~5분 헬리온 러시 무반응 수정)
- ZvZ/ZvP "hydralisk" 키 오타 수정 → "hydra" (내부 비율 딕셔너리 키 통일, 히드라 전혀 생산 안 되던 버그)
- ZvP 추적자(Stalker) 카운터 추가: 4기+ 시 저글링 포위+바퀴 돌진+담즙 (이전: stalker_count 읽고 미사용)
- 테스트 통과: 321 passed (이전 320 — ZvZ 뮤탈리스크 테스트 자동 해결)

## [Phase 33] - 2026-03-28
### 정찰/오버로드 강화
- 정찰 오버로드 재파견: 사망 시 overlord_scout_sent 리셋 → 즉시 새 오버로드 재파견 (이전: 사망 후 정찰 영구 중단)
- 중반 재정찰 저글링 move→attack: 적 만나도 도망 안 하고 정찰 유지
- 중반 재정찰 최소 수 하향: idle 2마리 (이전: 4 — 발동 조건 너무 엄격)

## [Phase 32] - 2026-03-28
### 견제/하라스 AI 개선
- 하라스 타겟 선택 수정: 방어 가장 약한 적 기지 선택 (이전: 아군 본진 최근접 → 적 주력 공격 역효과)
- 저글링 런바이 최소 수 하향: 8마리 (이전: 12 — 중반 전에 절대 미발동)
- 뮤탈리스크 위험 후퇴 수정: 가장 가까운 아군 기지로 후퇴 (이전: start_location 하드코딩)
- 뮤탈리스크 폴백 attack(): 일꾼 없을 때 move() 대신 attack() — 건물/유닛이라도 교전

## [Phase 31] - 2026-03-28
### 테크 트리 최적화
- 레어 타이밍 현실화: 3분(180초) 또는 미네랄 500+ 시 조기 변이 (이전: 3분30초 고정 — 확장과 충돌)
- Hive 변이 idle 제한 제거: 레어가 라바 생성 중이어도 Hive 변이 가능 (이전: idle만 허용 → 변이 영구 지연)
- Ultralisk Cavern 자동 건설: Hive 완성 즉시 자동 건설 트리거 (미네랄 150 + 가스 200)
- 울트라리스크 최종 테크 달성률 대폭 개선

## [Phase 30] - 2026-03-28
### 공격 판단 고도화
- 사전 전투력 비교: 적 가시 병력의 60% 미만이면 공격 자제 (전멸 방지)
- 열세 시 랠리포인트 재집결 + 로그 출력
- 기존 3단계 후퇴(1.3x/1.5x/2.0x)와 시너지 — 공격 전+전투 중 모두 체크

## [Phase 29] - 2026-03-28
### 매니저 충돌 해소
- defense_coordinator 방어 태그 Blackboard 전파 (이전: 미전파 → combat_manager와 충돌)
- 위협 해제 시 방어 태그 자동 클리어 (공격에 즉시 재투입)
- defense_unit_tags 병합 로직: multi_base + defense_coordinator 태그 통합

## [Phase 28] - 2026-03-28
### 경제/확장 밸런스
- 확장 타이밍 현실화: 3rd 3분30초/4th 5분/5th 7분 (이전: 90초/120초/180초 — 과도하게 빠름)
- 포화 후 확장 원칙: 미네랄 임계값도 상향 (기지당 자원 축적 후 확장)
- 6th/7th 확장도 합리적 타이밍으로 조정

## [Phase 27] - 2026-03-28
### 유닛 컨트롤 튜닝
- 바네링 자폭 최적화: move()→attack() 변경, 경장갑 우선타겟, 클러스터/최근접 폴백
- 유닛 변이 속도 개선: idle 제한 제거 (이전: 대기 유닛만 변이 → 전투 중 변이 가능)
- 저글링→바네링, 로치→레바저, 히드라→럴커 모두 idle 제한 해제

## [Phase 26] - 2026-03-28
### 방어 시스템 강화
- 포자 촉수 2분 선행건설 (이전: 3분) — DT/오라클 사전 대비
- 전투 시 크립 퀸 방어 투입 (이전: 전투 중에도 크립만 확산)
- 초반 러시 감지 임계값 하향: 3유닛/3서플 (이전: 4/4) — 6풀 대응 강화
- 중반 러시 감지 임계값 하향: 6유닛/6서플 (이전: 8/8)

## [Phase 25] - 2026-03-28
### 빌드오더 정밀화
- 스텝 실패 자동 재시도: 50프레임 재시도 후 스킵→백그라운드 재실행
- 연성 종료: 모든 스텝 완료 시 즉시 전환 (이전: 5분 하드컷)
- Blackboard 기반 BO→자동생산 전환 (build_order_complete 플래그)
- 일반 유닛 훈련 지원 추가 (Roach/Hydra 등 — 이전: Ling/Drone/Queen만)
- 초반 유닛 비율 현실화: 빌드 불가 유닛(바네링/레바저) 제거, Queen 추가

## [Phase 24] - 2026-03-28
### 멀티드롭/해커 방어
- 드롭 감지 Blackboard 전파: 수송선 접근 시 drop_detected + drop_position 즉시 공유
- 전투 드롭 대응: 가장 가까운 4~6유닛 즉시 차출 → 드롭 위치 방어
- 방어 후 drop_detected 자동 리셋 + 잔여 병력 원래 임무 복귀

## [Phase 23] - 2026-03-28
### 퀸/서플라이 최적화
- 방어 중에도 인젝트 최우선 실행 (이전: 방어 시 인젝트 완전 건너뜀)
- 오버로드 동적 버퍼 선행생산: 초반4/중반6/후반8/MAX10
- 필요량 기반 다중 오버로드 생산 (이전: 항상 1기만)

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
