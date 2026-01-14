# ? Manus 대시보드 요구사항 명세서

**작성일**: 2026-01-14  
**목적**: SC2 AI Dashboard의 각 페이지별 상세 요구사항 정리

---

## ? 홈 (Home)

**기능**: 메인 대시보드
- 전체 시스템 개요
- 주요 통계 요약
- 빠른 액세스 링크

---

## ? 실시간 모니터링 (Monitor)

### 상태 표시

**게임 진행 중이 아닐 때**:
- 메시지: "현재 진행중인 게임이 없습니다"

**게임 진행 중일 때**:
- 실시간 게임 상태 표시
- 유닛, 자원, 게임 단계 등

### 데이터 요구사항

**API 엔드포인트**: `GET /api/trpc/game.getCurrentState`

**응답 형식**:
```typescript
{
  isRunning: boolean;
  gameState?: {
    minerals: number;
    vespene: number;
    supplyUsed: number;
    supplyCap: number;
    units: Record<string, number>;
    mapName: string;
    gameTime: number;
    // ... 기타 게임 상태
  };
}
```

---

## ?? 전투 분석 (Battles)

### 주요 통계

1. **총 게임수** (Total Games)
2. **승리수** (Wins)
3. **패배수** (Losses)
4. **승률** (Win Rate) - 백분율

### 승률 분석

- 승률 추이 그래프
- 시간대별 승률 변화
- 상대 종족별 승률

### 최근 게임 기록

- **최근 20개 게임**의 상세 기록 표시
- 각 게임의 정보:
  - 게임 결과 (승리/패배)
  - 상대 종족
  - 맵 이름
  - 게임 시간
  - 최종 자원
  - 유닛 처치/손실
  - 날짜/시간

### 데이터 요구사항

**API 엔드포인트**:
- `GET /api/trpc/battle.getStats` - 전체 통계
- `GET /api/trpc/battle.getRecentGames` - 최근 20게임

**응답 형식**:
```typescript
// 전체 통계
{
  totalGames: number;
  wins: number;
  losses: number;
  winRate: number; // 0.0 ~ 1.0
}

// 최근 게임
{
  games: Array<{
    id: number;
    result: "Victory" | "Defeat";
    enemyRace: string;
    mapName: string;
    duration: number; // 초
    finalMinerals: number;
    finalGas: number;
    unitsKilled: number;
    unitsLost: number;
    timestamp: string; // ISO 8601
  }>;
}
```

---

## ? 학습 진행 (Training)

### 강화학습 추적

1. **총 에피소드** (Total Episodes)
2. **평균 보상** (Average Reward)
3. **평균 승률** (Average Win Rate)
4. **총 게임수** (Total Games)

### 성능 개선 추이

- 에피소드별 보상 그래프
- 승률 추이 그래프
- 손실 함수 그래프

### 최근 학습 에피소드

- 최근 학습 에피소드 목록
- 각 에피소드의 정보:
  - 에피소드 번호
  - 보상
  - 손실
  - 승률
  - 게임 수
  - 날짜/시간

### 데이터 요구사항

**API 엔드포인트**:
- `GET /api/trpc/training.getStats` - 전체 통계
- `GET /api/trpc/training.getRecentEpisodes` - 최근 에피소드

**응답 형식**:
```typescript
// 전체 통계
{
  totalEpisodes: number;
  averageReward: number;
  averageWinRate: number;
  totalGames: number;
}

// 최근 에피소드
{
  episodes: Array<{
    id: number;
    episode: number;
    reward: number;
    loss: number;
    winRate: number;
    games: number;
    timestamp: string;
  }>;
}
```

---

## ?? 봇 설정 (Bot Config)

### 활성 설정 표시

**활성화된 설정이 있을 때**:
- 제목: "현재 활성설정"
- 설정 이름
- 빌드오더 설명 (사용자가 작성한 설명)
- 빌드오더 특성

### 설정 관리

**기능**:
1. **생성** - 새 전략/빌드오더 생성
2. **편집** - 기존 설정 수정
3. **삭제** - 설정 삭제

**각 설정 정보**:
- 설정 이름
- 전략
- 빌드오더 (단계별)
- 빌드오더 설명
- 특성 (예: "공격적", "수비적", "빠른 확장" 등)
- 활성화 여부

### 데이터 요구사항

**API 엔드포인트**:
- `GET /api/trpc/botConfig.getActive` - 활성 설정
- `GET /api/trpc/botConfig.getAll` - 모든 설정
- `POST /api/trpc/botConfig.create` - 설정 생성
- `PUT /api/trpc/botConfig.update` - 설정 수정
- `DELETE /api/trpc/botConfig.delete` - 설정 삭제

**응답 형식**:
```typescript
// 활성 설정
{
  activeConfig: {
    id: number;
    name: string;
    strategy: string;
    buildOrder: string[];
    description: string;
    traits: string[];
    isActive: boolean;
  } | null;
}

// 모든 설정
{
  configs: Array<{
    id: number;
    name: string;
    strategy: string;
    buildOrder: string[];
    description: string;
    traits: string[];
    isActive: boolean;
  }>;
}
```

---

## ?? AI Arena

### 경기 통계

1. **총 경기수** (Total Matches)
2. **승리한 게임수** (Wins)
3. **패배한 게임수** (Losses)
4. **현재 ELO 점수** (Current ELO)

### 아레나 승률

- **전체 경기 승패 비율** 그래프
- 승리와 패배 숫자에 따른 비율
- 그래프 위에 **숫자로 0.0% 단위로 표시**

**예시**:
```
승률: 65.5%
[그래프: 승리 65.5% | 패배 34.5%]
```

### 봇 정보

- 아레나에 참가한 봇의 상태
- 봇 이름
- 종족
- 기타 정보

### 최근 경기 기록

- **최근 20개 경기** 기록
- 각 경기의 정보:
  - 상대 봇 이름
  - 결과 (승리/패배)
  - ELO 변화
  - 날짜/시간

### 데이터 요구사항

**API 엔드포인트**:
- `GET /api/trpc/arena.getStats` - 전체 통계
- `GET /api/trpc/arena.getBotInfo` - 봇 정보
- `GET /api/trpc/arena.getRecentMatches` - 최근 20경기

**응답 형식**:
```typescript
// 전체 통계
{
  totalMatches: number;
  wins: number;
  losses: number;
  currentELO: number;
  winRate: number; // 0.0 ~ 1.0
}

// 봇 정보
{
  bot: {
    name: string;
    race: string;
    status: string;
    // ... 기타 정보
  };
}

// 최근 경기
{
  matches: Array<{
    id: number;
    opponent: string;
    result: "Victory" | "Defeat";
    eloChange: number;
    timestamp: string;
  }>;
}
```

---

## ? 데이터 동기화

### 실시간 업데이트

- **폴링 방식**: 5초마다 업데이트 (현재)
- **WebSocket**: 실시간 업데이트 (향후 개선)

### 데이터 전송 시점

1. **게임 종료 시**: 게임 세션 데이터 전송
2. **학습 완료 시**: 학습 에피소드 데이터 전송
3. **설정 변경 시**: 봇 설정 업데이트
4. **Arena 경기 종료 시**: Arena 경기 데이터 전송

---

## ? 데이터베이스 스키마 요구사항

### 게임 세션 (game_sessions)

```sql
CREATE TABLE game_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  map_name VARCHAR(255),
  enemy_race VARCHAR(50),
  final_minerals INT,
  final_gas INT,
  final_supply INT,
  units_killed INT,
  units_lost INT,
  duration INT,
  result ENUM('Victory', 'Defeat'),
  personality VARCHAR(50),
  loss_reason TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 학습 에피소드 (training_episodes)

```sql
CREATE TABLE training_episodes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  episode INT,
  reward DECIMAL(10, 2),
  loss DECIMAL(10, 4),
  win_rate DECIMAL(5, 2),
  games INT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 봇 설정 (bot_configs)

```sql
CREATE TABLE bot_configs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(255),
  strategy VARCHAR(255),
  build_order JSON,
  description TEXT,
  traits JSON,
  is_active BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Arena 경기 (arena_matches)

```sql
CREATE TABLE arena_matches (
  id INT PRIMARY KEY AUTO_INCREMENT,
  opponent VARCHAR(255),
  result ENUM('Victory', 'Defeat'),
  elo_change INT,
  elo_after INT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## ? 구현 가이드

### 1. 실시간 모니터링

**로컬 봇에서**:
```python
# monitoring/dashboard.py 또는 monitoring/dashboard_api.py
# 게임 상태를 주기적으로 업데이트
# Manus 대시보드가 폴링하여 가져감
```

**Manus 대시보드에서**:
```typescript
// 5초마다 폴링
useEffect(() => {
  const interval = setInterval(() => {
    trpc.game.getCurrentState.query().then((data) => {
      if (data.isRunning) {
        setGameState(data.gameState);
      } else {
        setGameState(null);
      }
    });
  }, 5000);
  return () => clearInterval(interval);
}, []);
```

### 2. 전투 분석

**로컬 봇에서**:
```python
# telemetry_logger.py의 record_game_result()에서
# 게임 종료 시 Manus 대시보드로 전송
manus_client.create_game_session(...)
```

### 3. 학습 진행

**로컬 봇에서**:
```python
# 학습 완료 시
manus_client.create_training_episode(
    episode=current_episode,
    reward=average_reward,
    loss=current_loss,
    win_rate=current_win_rate
)
```

### 4. 봇 설정

**로컬 봇에서**:
```python
# 설정 변경 시
manus_client.update_bot_config(
    config_name="Aggressive Zerg",
    strategy="Roach Rush",
    build_order=["Pool", "Gas", "Roach Warren"],
    description="빠른 로치 러시 전략",
    traits=["aggressive", "fast"]
)
```

### 5. AI Arena

**로컬 봇에서**:
```python
# Arena 경기 종료 시
manus_client.create_arena_match(
    opponent="MonsterBot",
    result="Victory",
    elo_change=+15
)
```

---

## ? 체크리스트

### 백엔드 (Manus 대시보드)
- [ ] tRPC 라우터 구현
- [ ] 데이터베이스 스키마 생성
- [ ] API 엔드포인트 테스트

### 프론트엔드 (Manus 대시보드)
- [ ] 실시간 모니터링 페이지
- [ ] 전투 분석 페이지
- [ ] 학습 진행 페이지
- [ ] 봇 설정 페이지
- [ ] AI Arena 페이지

### 로컬 봇 통합
- [ ] Manus 클라이언트 설정
- [ ] 게임 종료 시 데이터 전송
- [ ] 학습 완료 시 데이터 전송
- [ ] 설정 변경 시 데이터 전송

---

**마지막 업데이트**: 2026-01-14
