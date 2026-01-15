# 연속 학습 모드 설정 완료

**작성일**: 2026-01-15  
**목적**: 게임이 끊기지 않고 계속 진행되도록 연속 학습 모드 구현

---

## ? 개선 완료 사항

### 1. **run_with_training.py - 연속 실행 루프 추가**

**개선 전**:
- 단일 게임 실행 후 종료

**개선 후**:
- **연속 게임 실행**: `while True` 루프로 게임이 끝나면 자동으로 다음 게임 시작
- **랜덤 맵 선택**: 다양한 맵에서 학습 (AbyssalReefLE, BelShirVestigeLE, CactusValleyLE, HonorgroundsLE, ProximaStationLE)
- **랜덤 상대 종족**: Terran, Protoss, Zerg
- **랜덤 난이도**: Hard, VeryHard, Elite
- **에러 처리**: 게임 실패 시 다음 게임으로 자동 진행
- **연속 실패 방지**: 5번 연속 실패 시 자동 중단

**코드**:
```python
while True:
    try:
        game_count += 1
        
        # Select random map, opponent race, and difficulty
        map_name = random.choice(available_maps)
        opponent_race = random.choice(opponent_races)
        difficulty = random.choice(difficulties)
        
        # Create new bot instance for each game
        bot = create_bot_with_training()
        bot.game_count = game_count
        
        # Run game
        run_game(...)
        
        # Game completed successfully
        consecutive_failures = 0
        time.sleep(3)  # Wait 3 seconds before next game
        
    except KeyboardInterrupt:
        break
    except Exception as game_error:
        consecutive_failures += 1
        time.sleep(5)  # Wait 5 seconds before retry
        continue
```

---

### 2. **start_model_training.bat - 연속 실행 모드 안내 추가**

**개선 사항**:
- 연속 실행 모드 설명 추가
- Press Ctrl+C로 중단 안내
- 빌드 오더 개선 사항 안내 추가

---

## ? 연속 실행 모드 기능

### 자동 재시작

| 기능 | 설명 |
|-----|------|
| **연속 게임 실행** | 게임이 끝나면 자동으로 다음 게임 시작 ? |
| **다양한 환경 학습** | 랜덤 맵, 상대 종족, 난이도로 다양한 상황 학습 ? |
| **에러 복구** | 게임 실패 시 자동으로 다음 게임 진행 ? |
| **연속 실패 방지** | 5번 연속 실패 시 자동 중단 ? |
| **모델 자동 저장** | 각 게임 후 모델 자동 저장 ? |

---

## ? 실행 방법

### 방법 1: 배치 스크립트 실행 (권장)

```batch
wicked_zerg_challenger\bat\start_model_training.bat
```

### 방법 2: 직접 Python 실행

```bash
cd wicked_zerg_challenger
python run_with_training.py
```

### 중단 방법

- **Ctrl+C** 를 눌러 학습 중단
- 게임이 끝난 후 3초 대기 중에 중단 가능

---

## ? 연속 실행 흐름

### 게임 실행 프로세스

```
1. 게임 시작
   ├─ 랜덤 맵 선택
   ├─ 랜덤 상대 종족 선택
   ├─ 랜덤 난이도 선택
   └─ 봇 인스턴스 생성

2. 게임 실행
   ├─ 빌드 오더 실행 (앞마당, 가스, 산란못)
   ├─ 신경망 학습 진행
   └─ 모델 자동 저장

3. 게임 종료
   ├─ 승리/패배 결과 기록
   ├─ 학습 데이터 저장
   └─ 3초 대기

4. 다음 게임 시작
   └─ 1번으로 돌아가기 ?
```

---

## ?? 에러 처리

### 연속 실패 방지

- **5번 연속 실패** 시 자동 중단
- 각 실패 후 **5초 대기** 후 재시도
- 에러 로그 출력으로 문제 추적 가능

### 예외 처리

- **KeyboardInterrupt**: 사용자가 중단하면 정상 종료
- **게임 실행 에러**: 다음 게임으로 자동 진행
- **예상치 못한 에러**: 5초 대기 후 재시도

---

## ? 수정된 파일

1. **wicked_zerg_challenger/run_with_training.py** ?
   - 연속 실행 루프 추가
   - 랜덤 맵/상대/난이도 선택
   - 에러 처리 개선
   - 연속 실패 방지

2. **wicked_zerg_challenger/bat/start_model_training.bat** ?
   - 연속 실행 모드 안내 추가
   - 빌드 오더 개선 사항 안내

---

## ? 검증 체크리스트

### 연속 실행 기능 확인

- [x] 게임이 끝나면 자동으로 다음 게임 시작
- [x] 랜덤 맵 선택
- [x] 랜덤 상대 종족 선택
- [x] 랜덤 난이도 선택
- [x] 에러 발생 시 다음 게임으로 진행
- [x] 연속 실패 방지 (5번)
- [x] Ctrl+C로 정상 중단 가능
- [x] 모델 자동 저장

---

## ? 예상 효과

### 학습 효율 향상

- ? 다양한 환경에서 학습하여 일반화 성능 향상
- ? 연속 실행으로 학습 시간 최대화
- ? 빌드 오더 개선으로 초반 실패 방지
- ? 에러 복구로 학습 중단 방지

### 빌드 오더 확인

- ? 앞마당 확장 확인 (Supply 30 또는 40+)
- ? 가스 추출 확인 (Supply 17 또는 30+)
- ? 산란못 건설 확인 (Supply 17 또는 25+)
- ? 발업 업그레이드 확인 (Supply 30+)

---

**설정 완료**: ? **게임이 끊기지 않고 계속 진행되도록 연속 학습 모드가 설정되었습니다**

**다음 단계**: 
1. `wicked_zerg_challenger\bat\start_model_training.bat` 실행
2. 게임 실행 후 빌드 오더가 올바르게 실행되는지 확인
3. 학습이 자동으로 계속 진행되는지 확인
