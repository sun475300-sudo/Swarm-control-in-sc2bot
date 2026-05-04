# -*- coding: utf-8 -*-
"""
현재 학습률 확인 스크립트.

스크립트로 직접 실행될 때만 stdout 인코딩을 변경하고 통계를 출력한다.
다른 모듈에서 import 해도 사이드 이펙트가 없도록 ``main()`` 함수에 모든
로직을 캡슐화한다.
"""

import io
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _print_lr_status(adaptive_lr_path: Path) -> dict:
    """적응형 학습률 상태 출력 후 데이터 반환."""
    if not adaptive_lr_path.exists():
        logger.info("\n[INFO] 적응형 학습률 통계 없음 (아직 게임 실행 안 함)")
        logger.info(f"\n[INIT] 초기 설정값:")
        logger.info(f"  - 초기 학습률: 0.001000")
        logger.info(f"  - 최소 학습률: 0.000100")
        logger.info(f"  - 최대 학습률: 0.010000")
        logger.info(f"  - 조정 배율: 1.2 (±20%)")
        logger.info(f"  - Patience: 10게임")
        return {}

    logger.info("\n[ADAPTIVE_LR] 적응형 학습률 통계 로드됨")
    with open(adaptive_lr_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"\n[OK] 현재 학습률: {data['learning_rate']:.6f}")
    logger.info(f"[OK] 최적 학습률: {data['best_learning_rate']:.6f}")
    logger.info(f"[OK] 최고 승률: {data['best_win_rate']:.2%}")
    logger.info(f"[OK] 총 게임 수: {data['total_games']}")
    logger.info(f"[OK] 총 승리 수: {data['total_wins']}")
    if data["total_games"] > 0:
        logger.info(f"[OK] 전체 승률: {data['total_wins']/data['total_games']:.2%}")
    else:
        logger.info(f"[OK] 전체 승률: 0.00%")
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
    return data


def _print_model_status(model_path: Path) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("RL Agent 모델 상태")
    logger.info("=" * 60)

    if not model_path.exists():
        logger.info(f"\n[INFO] RL Agent 모델 없음 (첫 게임 실행 후 생성됨)")
        logger.info(f"  - 모델 저장 위치: {model_path}")
        return

    import numpy as np

    data = np.load(str(model_path))
    logger.info(f"\n[OK] 모델 파일 존재: {model_path}")
    logger.info(f"[OK] 에피소드 수: {int(data['episode_count'][0])}")
    logger.info(f"[OK] 베이스라인: {float(data['baseline'][0]):.4f}")
    logger.info(f"\n[MODEL] 모델 파라미터:")
    logger.info(f"  - W1 shape: {data['W1'].shape}")
    logger.info(f"  - W2 shape: {data['W2'].shape}")
    logger.info(f"  - W3 shape: {data['W3'].shape}")


def _print_analytics_status(analytics_path: Path) -> None:
    logger.info("\n" + "=" * 60)
    logger.info("게임 분석 통계")
    logger.info("=" * 60)

    if not analytics_path.exists():
        logger.info(f"\n[INFO] 게임 분석 통계 없음 (첫 게임 실행 후 생성됨)")
        return

    with open(analytics_path, "r", encoding="utf-8") as f:
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

    logger.info(f"\n[RACE] 종족별 승률:")
    for race, stats in data["race_stats"].items():
        if stats["games"] > 0:
            race_wr = stats["wins"] / stats["games"] * 100
            logger.info(
                f"  vs {race}: {stats['wins']}/{stats['games']}승 ({race_wr:.1f}%)"
            )


def main() -> int:
    """학습률/모델/분석 통계를 stdout에 출력."""
    # UTF-8 출력 설정 (Windows 콘솔 인코딩 문제 해결) - 스크립트 실행 시에만
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    logger.info("=" * 60)
    logger.info("현재 학습률 상태 확인")
    logger.info("=" * 60)

    adaptive_lr_path = Path("local_training/adaptive_lr_stats.json")
    lr_data = _print_lr_status(adaptive_lr_path)

    _print_model_status(Path("local_training/models/rl_agent_model.npz"))
    _print_analytics_status(Path("local_training/game_analytics.json"))

    logger.info("\n" + "=" * 60)
    logger.info("요약")
    logger.info("=" * 60)

    if lr_data:
        logger.info(f"\n[CURRENT] 현재 학습률: {lr_data['learning_rate']:.6f}")
        logger.info(
            f"[BEST] 최고 성과: {lr_data['best_win_rate']:.2%} (LR: {lr_data['best_learning_rate']:.6f})"
        )
        games_until_adjustment = 10 - lr_data["games_without_improvement"]
        if games_until_adjustment > 0:
            logger.info(f"[NEXT] 다음 조정까지: {games_until_adjustment}게임")
        else:
            logger.warning(f"[WARNING] 다음 게임에서 학습률 조정 가능")
    else:
        logger.info(f"\n[CURRENT] 초기 학습률: 0.001000 (아직 게임 실행 안 함)")
        logger.info(f"[INFO] 첫 게임 실행 후 적응형 학습률 시작")

    logger.info("\n" + "=" * 60)
    logger.info("\n게임 실행: python run_with_training.py")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
