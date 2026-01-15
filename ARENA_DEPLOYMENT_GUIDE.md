# AI Arena 배포 가이드

**작성일**: 2026-01-15  
**상태**: ? **배포 패키지 생성 완료**

---

## ? 배포 패키지 생성

### 방법 1: 배치 파일 사용 (가장 쉬운 방법)

```bash
cd wicked_zerg_challenger
bat\create_arena_deployment.bat
```

**결과**: `D:\아레나_배포\deployment\WickedZerg_AIArena_YYYYMMDD_HHMMSS.zip` 파일 생성

### 방법 2: Python 스크립트 직접 실행

```bash
cd wicked_zerg_challenger
python tools\package_for_aiarena_clean.py --output "D:/아레나_배포/deployment"
```

### 방법 3: 환경 변수 사용

```bash
set ARENA_DEPLOY_PATH=D:\아레나_배포\deployment
cd wicked_zerg_challenger
python tools\package_for_aiarena_clean.py
```

---

## ? 패키지 내용

### 포함되는 파일

#### 필수 파일 (Essential)
- `wicked_zerg_bot_pro.py` - 메인 봇 클래스
- `run.py` - AI Arena 진입점
- `config.py` - 설정 파일
- `zerg_net.py` - 신경망 모델
- `combat_manager.py` - 전투 관리
- `economy_manager.py` - 경제 관리
- `production_manager.py` - 생산 관리
- `micro_controller.py` - 군집 제어 알고리즘
- `scouting_system.py` - 정찰 시스템
- `intel_manager.py` - 정보 관리
- `queen_manager.py` - 여왕 관리
- `telemetry_logger.py` - 텔레메트리 로거
- `rogue_tactics_manager.py` - 이병렬 전술 관리
- `requirements.txt` - 의존성 목록

#### 선택적 파일 (Optional - 있으면 포함)
- `combat_tactics.py`
- `production_resilience.py`
- `personality_manager.py`
- `strategy_analyzer.py`
- `spell_unit_manager.py`
- `unit_factory.py`
- `map_manager.py`

#### local_training 디렉토리
- 모든 Python 파일 (테스트 제외)
- 학습된 파라미터 (`learned_build_orders.json`, `strategy_db.json`)

#### 모델 파일
- `models/zerg_net_model.pt` (있는 경우)

---

## ? 출력 위치

**기본 경로**: `D:\아레나_배포\deployment\`

**파일명 형식**: `WickedZerg_AIArena_YYYYMMDD_HHMMSS.zip`

---

## ? 검증

패키지 생성 후 자동으로 검증됩니다:

1. ? 필수 파일 존재 확인
2. ? 불필요한 파일 제외 확인
3. ? 패키지 통계 출력

---

## ? AI Arena 업로드

1. 생성된 ZIP 파일 확인
2. https://aiarena.net 접속
3. Bot 업로드 페이지에서 ZIP 파일 업로드
4. 첫 매치 결과 모니터링

---

## ? 문제 해결

### 문제: "Missing files" 에러

**해결**: 필수 파일이 없는 경우입니다. 다음 파일들이 `wicked_zerg_challenger/` 루트에 있는지 확인:
- `wicked_zerg_bot_pro.py`
- `run.py`
- `config.py`
- `zerg_net.py`

### 문제: 인코딩 에러

**해결**: 배치 파일(`bat\create_arena_deployment.bat`)을 사용하세요. 한글 경로 인코딩이 자동으로 처리됩니다.

### 문제: 모델 파일 없음

**해결**: 모델 파일이 없어도 패키지는 생성됩니다. 학습된 모델이 있으면 `models/` 디렉토리에 `.pt` 파일을 넣으세요.

---

**배포 준비 완료!** ?
