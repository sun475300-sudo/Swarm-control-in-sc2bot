"""
현재 학습률 확인 스크립트
"""

import io
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# UTF-8 출력 설정 (Windows 콘솔 인코딩 문제 해결)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 1. Adaptive Learning Rate 확인
adaptive_lr_path = Path("local_training/adaptive_lr_stats.json")

logger.info("=" * 60)
logger.info("현재 학습률 상태 확인")
logger.info("=" * 60)

if adaptive_lr_path.exists():
    logger.info("\n[ADAPTIVE_LR] 적응형 학습률 통계 로드됨")
    with open(adaptive_lr_path, encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"\n[OK] 현재 학습률: {data['learning_rate']:.6f}")
    logger.info(f"[OK] 최적 학습률: {data['best_learning_rate']:.6f}")
    logger.info(f"[OK] 최고 승률: {data['best_win_rate']:.2%}")
    logger.info(f"[OK] 총 게임 수: {data['total_games']}")
    logger.info(f"[OK] 총 승리 수: {data['total_wins']}")
    if data["total_games"] > 0:
        logger.info(f"[OK] 전체 승률: {data['total_wins']/data['total_games']:.2%}")
    else:
        logger.info("[OK] 전체 승률: 0.00%")
    logger.info(f"[OK] 개선 없음: {data['games_without_improvement']}/10게임")

    if data.get("adjustment_history"):
        logger.info(f"\n[HISTORY] 조정 이력 ({len(data['adjustment_history'])}회):")
        for adj in data["adjustment_history"][-5:]:
            action_mark = (
                "[UP]"
                if adj["action"] == "increase"
                else "[DOWN]" if adj["action"] == "decrease" else "[RESET]"
            )
            logger.info(
                f"  {action_mark} Game {adj['game']}: {adj['old_lr']:.6f} -> {adj['new_lr']:.6f} ({adj['action']})"
            )
else:
    logger.info("\n[INFO] 적응형 학습률 통계 없음 (아직 게임 실행 안 함)")
    logger.info("\n[INIT] 초기 설정값:")
    logger.info("  - 초기 학습률: 0.001000")
    logger.info("  - 최소 학습률: 0.000100")
    logger.info("  - 최대 학습률: 0.010000")
    logger.info("  - 조정 배율: 1.2 (±20%)")
    logger.info("  - Patience: 10게임")

# 2. RL Agent 모델 확인
model_path = Path("local_training/models/rl_agent_model.npz")

logger.info("\n" + "=" * 60)
logger.info("RL Agent 모델 상태")
logger.info("=" * 60)

if model_path.exists():
    import numpy as np

    data = np.load(str(model_path))

    logger.info(f"\n[OK] 모델 파일 존재: {model_path}")
    logger.info(f"[OK] 에피소드 수: {int(data['episode_count'][0])}")
    logger.info(f"[OK] 베이스라인: {float(data['baseline'][0]):.4f}")
    logger.info("\n[MODEL] 모델 파라미터:")
    logger.info(f"  - W1 shape: {data['W1'].shape}")
    logger.info(f"  - W2 shape: {data['W2'].shape}")
    logger.info(f"  - W3 shape: {data['W3'].shape}")
else:
    logger.info("\n[INFO] RL Agent 모델 없음 (첫 게임 실행 후 생성됨)")
    logger.info(f"  - 모델 저장 위치: {model_path}")

# 3. Game Analytics 확인
analytics_path = Path("local_training/game_analytics.json")

logger.info("\n" + "=" * 60)
logger.info("게임 분석 통계")
logger.info("=" * 60)

if analytics_path.exists():
    with open(analytics_path, encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"\n[OK] 총 게임: {data['total_games']}")
    logger.info(f"[OK] 총 승리: {data['total_wins']}")
    win_rate = (
        (data["total_wins"] / data["total_games"] * 100)
        if data["total_games"] > 0
        else 0.0
    )
    logger.info(f"[OK] 승률: {win_rate:.2f}%")
    logger.info(f"[OK] 평균 게임 시간: {int(data['timing_stats']['avg_game_time'])}초")

    logger.info("\n[RACE] 종족별 승률:")
    for race, stats in data["race_stats"].items():
        if stats["games"] > 0:
            race_wr = stats["wins"] / stats["games"] * 100
            logger.info(
                f"  vs {race}: {stats['wins']}/{stats['games']}승 ({race_wr:.1f}%)"
            )
else:
    logger.info("\n[INFO] 게임 분석 통계 없음 (첫 게임 실행 후 생성됨)")

logger.info("\n" + "=" * 60)
logger.info("요약")
logger.info("=" * 60)

if adaptive_lr_path.exists():
    with open(adaptive_lr_path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"\n[CURRENT] 현재 학습률: {data['learning_rate']:.6f}")
    logger.info(
        f"[BEST] 최고 성과: {data['best_win_rate']:.2%} (LR: {data['best_learning_rate']:.6f})"
    )

    # 다음 조정 예측
    games_until_adjustment = 10 - data["games_without_improvement"]
    if games_until_adjustment > 0:
        logger.info(f"[NEXT] 다음 조정까지: {games_until_adjustment}게임")
    else:
        logger.warning("[WARNING] 다음 게임에서 학습률 조정 가능")
else:
    logger.info("\n[CURRENT] 초기 학습률: 0.001000 (아직 게임 실행 안 함)")
    logger.info("[INFO] 첫 게임 실행 후 적응형 학습률 시작")

logger.info("\n" + "=" * 60)
logger.info("\n게임 실행: python run_with_training.py")
logger.info("=" * 60)
