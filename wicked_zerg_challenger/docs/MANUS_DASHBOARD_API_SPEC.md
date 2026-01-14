# ? Manus 대시보드 API 명세서

**작성일**: 2026-01-14  
**목적**: 로컬 SC2 봇과 Manus 대시보드 간 API 통신 명세

---

## ? API 엔드포인트 목록

### 게임 관련

#### 1. `game.createSession` (POST)
게임 종료 시 세션 생성

**요청**:
```json
{
  "mapName": "AbyssalReefLE",
  "enemyRace": "Terran",
  "finalMinerals": 200,
  "finalGas": 100,
  "finalSupply": 150,
  "unitsKilled": 50,
  "unitsLost": 30,
  "duration": 600,
  "result": "Victory",
  "personality": "serral",
  "lossReason": null
}
```

**응답**:
```json
{
  "success": true,
  "id": 123
}
```

---

#### 2. `game.getCurrentState` (GET)
현재 게임 상태 조회

**요청**: 없음

**응답**:
```json
{
  "isRunning": true,
  "gameState": {
    "minerals": 50,
    "vespene": 0,
    "supplyUsed": 12,
    "supplyCap": 15,
    "units": {
      "zerglings": 0,
      "roaches": 0
    },
    "mapName": "AbyssalReefLE",
    "gameTime": 120
  }
}
```

또는 게임이 없을 때:
```json
{
  "isRunning": false,
  "gameState": null
}
```

---

#### 3. `game.updateState` (POST)
실시간 게임 상태 업데이트

**요청**:
```json
{
  "minerals": 50,
  "vespene": 0,
  "supplyUsed": 12,
  "supplyCap": 15,
  "units": {
    "zerglings": 0,
    "roaches": 0
  },
  "mapName": "AbyssalReefLE",
  "gameTime": 120
}
```

**응답**:
```json
{
  "success": true
}
```

---

### 전투 분석 관련

#### 4. `battle.getStats` (GET)
전투 통계 조회

**요청**: 없음

**응답**:
```json
{
  "totalGames": 100,
  "wins": 65,
  "losses": 35,
  "winRate": 0.65
}
```

---

#### 5. `battle.getRecentGames` (GET)
최근 20게임 조회

**요청**: 없음 (또는 `?limit=20`)

**응답**:
```json
{
  "games": [
    {
      "id": 1,
      "result": "Victory",
      "enemyRace": "Terran",
      "mapName": "AbyssalReefLE",
      "duration": 600,
      "finalMinerals": 200,
      "finalGas": 100,
      "unitsKilled": 50,
      "unitsLost": 30,
      "timestamp": "2026-01-14T12:34:56Z"
    }
    // ... 최대 20개
  ]
}
```

---

### 학습 진행 관련

#### 6. `training.getStats` (GET)
학습 통계 조회

**요청**: 없음

**응답**:
```json
{
  "totalEpisodes": 500,
  "averageReward": 150.5,
  "averageWinRate": 0.65,
  "totalGames": 1000
}
```

---

#### 7. `training.createEpisode` (POST)
학습 에피소드 생성

**요청**:
```json
{
  "episode": 100,
  "reward": 150.5,
  "loss": 0.0342,
  "winRate": 0.65,
  "games": 20
}
```

**응답**:
```json
{
  "success": true,
  "id": 100
}
```

---

#### 8. `training.getRecentEpisodes` (GET)
최근 학습 에피소드 조회

**요청**: 없음 (또는 `?limit=20`)

**응답**:
```json
{
  "episodes": [
    {
      "id": 100,
      "episode": 100,
      "reward": 150.5,
      "loss": 0.0342,
      "winRate": 0.65,
      "games": 20,
      "timestamp": "2026-01-14T12:34:56Z"
    }
    // ... 최대 20개
  ]
}
```

---

### 봇 설정 관련

#### 9. `botConfig.getActive` (GET)
활성 설정 조회

**요청**: 없음

**응답**:
```json
{
  "activeConfig": {
    "id": 1,
    "name": "Aggressive Zerg",
    "strategy": "Roach Rush",
    "buildOrder": ["Pool", "Gas", "Roach Warren"],
    "description": "빠른 로치 러시 전략",
    "traits": ["aggressive", "fast"],
    "isActive": true
  }
}
```

또는 활성 설정이 없을 때:
```json
{
  "activeConfig": null
}
```

---

#### 10. `botConfig.getAll` (GET)
모든 설정 조회

**요청**: 없음

**응답**:
```json
{
  "configs": [
    {
      "id": 1,
      "name": "Aggressive Zerg",
      "strategy": "Roach Rush",
      "buildOrder": ["Pool", "Gas", "Roach Warren"],
      "description": "빠른 로치 러시 전략",
      "traits": ["aggressive", "fast"],
      "isActive": true
    }
    // ... 모든 설정
  ]
}
```

---

#### 11. `botConfig.create` (POST)
설정 생성

**요청**:
```json
{
  "name": "Aggressive Zerg",
  "strategy": "Roach Rush",
  "buildOrder": ["Pool", "Gas", "Roach Warren"],
  "description": "빠른 로치 러시 전략",
  "traits": ["aggressive", "fast"],
  "isActive": false
}
```

**응답**:
```json
{
  "success": true,
  "id": 1
}
```

---

#### 12. `botConfig.update` (PUT)
설정 수정

**요청**:
```json
{
  "id": 1,
  "name": "Aggressive Zerg",
  "strategy": "Roach Rush",
  "buildOrder": ["Pool", "Gas", "Roach Warren"],
  "description": "빠른 로치 러시 전략 (수정됨)",
  "traits": ["aggressive", "fast", "early"],
  "isActive": true
}
```

**응답**:
```json
{
  "success": true
}
```

---

#### 13. `botConfig.delete` (DELETE)
설정 삭제

**요청**: `?id=1`

**응답**:
```json
{
  "success": true
}
```

---

### AI Arena 관련

#### 14. `arena.getStats` (GET)
Arena 통계 조회

**요청**: 없음

**응답**:
```json
{
  "totalMatches": 50,
  "wins": 35,
  "losses": 15,
  "currentELO": 1650,
  "winRate": 0.70
}
```

---

#### 15. `arena.getBotInfo` (GET)
봇 정보 조회

**요청**: 없음

**응답**:
```json
{
  "bot": {
    "name": "WickedZerg",
    "race": "Zerg",
    "status": "Active"
  }
}
```

---

#### 16. `arena.createMatch` (POST)
Arena 경기 생성

**요청**:
```json
{
  "opponent": "MonsterBot",
  "result": "Victory",
  "eloChange": 15,
  "eloAfter": 1665
}
```

**응답**:
```json
{
  "success": true,
  "id": 1
}
```

---

#### 17. `arena.getRecentMatches` (GET)
최근 20경기 조회

**요청**: 없음 (또는 `?limit=20`)

**응답**:
```json
{
  "matches": [
    {
      "id": 1,
      "opponent": "MonsterBot",
      "result": "Victory",
      "eloChange": 15,
      "eloAfter": 1665,
      "timestamp": "2026-01-14T12:34:56Z"
    }
    // ... 최대 20개
  ]
}
```

---

## ? 인증

### API 키 사용 (선택적)

요청 헤더:
```
Authorization: Bearer {API_KEY}
```

---

## ? 데이터 형식

### 게임 결과
- `"Victory"` - 승리
- `"Defeat"` - 패배

### 승률
- `0.0` ~ `1.0` (소수점)
- 백분율로 표시 시: `winRate * 100`

### 타임스탬프
- ISO 8601 형식: `"2026-01-14T12:34:56Z"`

---

## ? 에러 응답

### 400 Bad Request
```json
{
  "error": "Invalid input",
  "details": "..."
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid API key"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "..."
}
```

---

## ? 관련 문서

- **요구사항 명세**: `docs/MANUS_DASHBOARD_REQUIREMENTS.md`
- **통합 가이드**: `docs/MANUS_DASHBOARD_INTEGRATION.md`

---

**마지막 업데이트**: 2026-01-14
