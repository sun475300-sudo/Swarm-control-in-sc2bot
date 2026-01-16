# 게임 학습 시작 완료

## 실행 상태
게임 학습이 시작되었습니다.

## 실행 방법

### 배치 파일 사용 (권장)
```batch
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_local_training.bat
```

### Python 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
python run_with_training.py
```

## 학습 설정

### 환경 변수
- `INSTANCE_ID`: 0 (단일 인스턴스)
- `NUM_INSTANCES`: 1 (한 번에 1게임)
- `SHOW_WINDOW`: true (게임 창 표시)
- `MAX_GAMES`: 0 (무한)
- `TORCH_NUM_THREADS`: 12

### 학습 모드
- **단일 게임 모드**: 한 번에 1게임만 실행
- **시각 모드**: 게임 창 표시 (모니터링 가능)
- **신경망 학습**: 활성화됨
- **모니터링 서버**: 자동 시작 (포트 8001)

## 모니터링

### 로컬 모니터링 서버
- URL: http://localhost:8001
- API 문서: http://localhost:8001/docs
- 실시간 게임 상태 확인 가능

### 학습 통계
- 실시간 승률 추적
- 게임별 결과 기록
- 신경망 학습 진행 상황

## 학습 프로세스

1. **게임 시작**
   - StarCraft II 실행
   - 봇 vs AI 대전
   - 실시간 게임 플레이

2. **데이터 수집**
   - 게임 상태 수집
   - 행동-보상 쌍 기록
   - 리플레이 저장

3. **신경망 학습**
   - REINFORCE 알고리즘
   - 정책 네트워크 업데이트
   - 가치 네트워크 업데이트

4. **모델 저장**
   - 주기적으로 모델 저장
   - 최고 성능 모델 유지
   - 학습 통계 기록

## 출력 파일

- `local_training/models/zerg_net_model.pt` - 학습된 모델
- `local_training/data/training_stats.json` - 학습 통계
- `replays/` - 게임 리플레이

## 중지 방법

- `Ctrl+C`로 학습 중지
- 현재 게임 종료 후 중지
- 모델 자동 저장
