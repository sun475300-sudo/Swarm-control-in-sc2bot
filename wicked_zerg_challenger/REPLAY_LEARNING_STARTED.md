# 리플레이 학습 시작

## 상태
리플레이 학습 스크립트 실행 준비 중

## 실행 방법

### 배치 파일 사용 (권장)
```batch
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger
bat\start_replay_learning.bat
```

### Python 직접 실행
```bash
cd D:\Swarm-contol-in-sc2bot\wicked_zerg_challenger\local_training\scripts
python replay_build_order_learner.py
```

## 리플레이 디렉토리
- 기본 경로: `D:\replays\replays`
- 파일 형식: `*.SC2Replay`
- Zerg 플레이어 리플레이만 처리

## 학습 프로세스
1. 리플레이 파일 스캔
2. 각 리플레이 분석 (5회 반복)
3. 빌드 오더 추출
4. 학습된 파라미터 저장
5. `learned_build_orders.json` 생성

## 출력 파일
- `local_training/scripts/learned_build_orders.json` - 학습된 파라미터
- `strategy_db.json` - 전략 데이터베이스

## 참고사항
- sc2reader 라이브러리 필요
- 각 리플레이는 5회 분석되어 더 정확한 학습 수행
- 진행 상황이 실시간으로 표시됨
