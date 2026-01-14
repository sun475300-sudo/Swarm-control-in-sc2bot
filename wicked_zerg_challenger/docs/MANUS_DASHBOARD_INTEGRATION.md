# ? Manus 대시보드 통합 가이드

**작성일**: 2026-01-14  
**목적**: SC2 AI 봇을 Manus 웹 호스팅 대시보드와 연결

---

## ? 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│ 로컬 컴퓨터 (Local)                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ StarCraft II 게임 + AI 봇 (Python)                      ││
│ │ - wicked_zerg_bot_pro.py                                ││
│ │ - telemetry_logger.py                                   ││
│ │ - monitoring/manus_dashboard_client.py                  ││
│ └──────────────────────────────────────────────────────────┘│
│                          ↓ (tRPC API)                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ Manus 웹 호스팅                                              │
│ https://sc2aidash-bncleqgg.manus.space                     │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ React 대시보드 (프론트엔드)                                 ││
│ │ tRPC API + Express 서버 (백엔드)                          ││
│ │ MySQL 데이터베이스                                        ││
│ └──────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## ? 빠른 시작

### 1단계: 환경 변수 설정

```powershell
# PowerShell에서 설정
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_ENABLED = "1"
$env:MANUS_DASHBOARD_API_KEY = "your_api_key_here"  # 선택적
```

**영구 설정**:
```powershell
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_URL", "https://sc2aidash-bncleqgg.manus.space", "User")
[System.Environment]::SetEnvironmentVariable("MANUS_DASHBOARD_ENABLED", "1", "User")
```

### 2단계: 테스트

```powershell
cd wicked_zerg_challenger\monitoring
python manus_dashboard_client.py
```

**예상 출력**:
```
[MANUS] 클라이언트 초기화: https://sc2aidash-bncleqgg.manus.space (활성화: True)
Manus 대시보드 연결 확인 중...
? 서버 연결 성공
테스트 게임 세션 생성 중...
? 게임 세션 생성 성공
```

### 3단계: 봇 실행

이제 봇을 실행하면 게임 종료 시 자동으로 Manus 대시보드에 데이터가 전송됩니다:

```powershell
cd wicked_zerg_challenger
python run.py
```

---

## ? 통합 방법

### 자동 통합 (이미 완료)

`telemetry_logger.py`의 `record_game_result()` 메서드에 Manus 대시보드 전송 기능이 자동으로 통합되어 있습니다.

**게임 종료 시 자동으로**:
1. 로컬 `training_stats.json`에 저장
2. Manus 대시보드로 전송 (환경 변수가 설정된 경우)

### 수동 통합 (선택적)

특정 시점에 수동으로 데이터를 전송하려면:

```python
from monitoring.manus_dashboard_client import create_client_from_env

# 클라이언트 생성
client = create_client_from_env()

# 게임 세션 생성
client.create_game_session(
    map_name="AbyssalReefLE",
    enemy_race="Terran",
    final_minerals=200,
    final_gas=100,
    final_supply=150,
    units_killed=50,
    units_lost=30,
    duration=600,
    result="Victory",
    personality="serral"
)
```

---

## ? API 메서드

### 1. `create_game_session()` - 게임 세션 생성

게임 종료 시 호출됩니다.

```python
client.create_game_session(
    map_name="AbyssalReefLE",
    enemy_race="Terran",
    final_minerals=200,
    final_gas=100,
    final_supply=150,
    units_killed=50,
    units_lost=30,
    duration=600,  # 초 단위
    result="Victory",  # "Victory" or "Defeat"
    personality="serral",  # 선택적
    loss_reason="Army destroyed"  # 선택적 (패배 시)
)
```

### 2. `create_training_episode()` - 학습 에피소드

학습 진행 상황 추적:

```python
client.create_training_episode(
    episode=100,
    reward=150.5,
    loss=0.0342,
    win_rate=0.65
)
```

### 3. `update_bot_config()` - 봇 설정 업데이트

봇 설정 변경 시:

```python
client.update_bot_config(
    config_name="Aggressive Zerg",
    strategy="Roach Rush",
    build_order=["Pool", "Gas", "Roach Warren"]
)
```

### 4. `create_arena_match()` - AI Arena 경기

AI Arena 경기 결과:

```python
client.create_arena_match(
    opponent="MonsterBot",
    result="Victory",
    elo_change=+15
)
```

---

## ? 데이터 매핑

### 봇 데이터 → Manus 대시보드

| 봇 필드 | Manus 필드 | 설명 |
|---------|-----------|------|
| `bot.time` | `duration` | 게임 시간 (초) |
| `bot.minerals` | `finalMinerals` | 최종 미네랄 |
| `bot.vespene` | `finalGas` | 최종 가스 |
| `bot.supply_used` | `finalSupply` | 최종 인구수 |
| `game_result` | `result` | "Victory" or "Defeat" |
| `bot.opponent_race` | `enemyRace` | 상대 종족 |
| `bot.game_info.map_name` | `mapName` | 맵 이름 |
| `bot.personality` | `personality` | 봇 성격 |

---

## ? 문제 해결

### 문제 1: 데이터가 전송되지 않음

**확인 사항**:
1. 환경 변수 설정 확인:
   ```powershell
   $env:MANUS_DASHBOARD_ENABLED
   ```
2. 네트워크 연결 확인
3. 서버 URL 확인

**해결**:
```powershell
# 환경 변수 재설정
$env:MANUS_DASHBOARD_URL = "https://sc2aidash-bncleqgg.manus.space"
$env:MANUS_DASHBOARD_ENABLED = "1"
```

### 문제 2: 연결 실패

**증상**: `Connection timeout` 또는 `Connection refused`

**해결**:
1. Manus 대시보드 URL 확인
2. 방화벽 설정 확인
3. 네트워크 연결 확인

### 문제 3: 인증 오류

**증상**: `401 Unauthorized` 또는 `403 Forbidden`

**해결**:
1. API 키 확인 (필요한 경우)
2. 환경 변수 설정 확인

---

## ? 모니터링

### 로그 확인

Manus 대시보드 전송 로그:

```
[MANUS] 게임 결과를 대시보드에 전송했습니다: Victory
[MANUS] 게임 세션 생성 성공: Victory vs Terran
[MANUS] 요청 실패 (시도 1/3): Connection timeout
[MANUS] 요청 최종 실패: Max retries exceeded
```

### 대시보드 확인

웹 브라우저에서 확인:
- URL: `https://sc2aidash-bncleqgg.manus.space`
- 게임 세션, 학습 진행도, 통계 등 확인

---

## ? 보안 고려사항

### 1. API 키 보호

- 환경 변수에만 저장
- Git에 커밋하지 않음
- `.gitignore`에 `.env` 추가

### 2. HTTPS 사용

- 모든 통신은 HTTPS
- 인증서 검증 활성화

### 3. Rate Limiting

- 서버 측에서 요청 제한
- 클라이언트에서 재시도 로직

---

## ? 관련 문서

- **원격 대시보드 아키텍처**: `docs/REMOTE_DASHBOARD_ARCHITECTURE.md`
- **원격 대시보드 설정**: `docs/REMOTE_DASHBOARD_SETUP.md`
- **로컬 모니터링**: `docs/ANDROID_DATA_TRANSFER_TEST.md`

---

## ? 체크리스트

### 설정
- [ ] 환경 변수 설정 (`MANUS_DASHBOARD_URL`, `MANUS_DASHBOARD_ENABLED`)
- [ ] API 키 설정 (필요한 경우)
- [ ] 클라이언트 테스트 성공

### 통합
- [ ] 봇 실행 시 자동 전송 확인
- [ ] 대시보드에서 데이터 확인
- [ ] 로그 확인

### 검증
- [ ] 게임 세션 데이터 전송 확인
- [ ] 학습 에피소드 데이터 전송 확인 (선택적)
- [ ] 봇 설정 업데이트 확인 (선택적)

---

**마지막 업데이트**: 2026-01-14
