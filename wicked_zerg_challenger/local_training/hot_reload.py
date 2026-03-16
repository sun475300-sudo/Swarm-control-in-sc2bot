# -*- coding: utf-8 -*-
"""
Model Hot Reloader - 게임 중 모델 핫 리로드

게임 실행 중 외부 학습 프로세스가 새 모델을 배포하면,
자동으로 감지하여 RLAgent의 PolicyNetwork 가중치를 교체합니다.

동작 방식:
1. deployed_model.npz 파일의 mtime을 주기적으로 확인
2. 변경 감지 시 새 가중치를 로드하여 PolicyNetwork에 적용
3. 게임 중단 없이 seamless하게 교체

사용법:
    reloader = ModelHotReloader(rl_agent, model_path="local_training/models/deployed_model.npz")
    # 게임 루프에서 주기적 호출
    reloader.check_and_reload()
"""

import os
import time
from pathlib import Path
from typing import Optional

import numpy as np


class ModelHotReloader:
    """
    모델 핫 리로더

    - check_and_reload(): 주기적 호출하면 파일 변경 시 자동 리로드
    - PolicyNetwork의 W1,b1,W2,b2,W3,b3 직접 교체
    - 로드 실패 시 기존 가중치 유지 (안전)
    """

    def __init__(
        self,
        rl_agent,
        model_path: Optional[str] = None,
        check_interval: float = 30.0,
    ):
        """
        Args:
            rl_agent: RLAgent 인스턴스 (policy 속성 필요)
            model_path: 감시할 모델 파일 경로 (None이면 기본 경로)
            check_interval: 파일 확인 주기 (초)
        """
        self.rl_agent = rl_agent

        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), "models", "deployed_model.npz"
            )
        self.model_path = Path(model_path)
        self.check_interval = check_interval

        # 상태
        self._last_check_time: float = 0.0
        self._last_mtime: float = 0.0
        self._reload_count: int = 0

        # 초기 mtime 기록
        if self.model_path.exists():
            self._last_mtime = self.model_path.stat().st_mtime

    def check_and_reload(self) -> bool:
        """
        모델 파일 변경 확인 및 리로드.

        Returns:
            True: 새 모델이 로드됨
            False: 변경 없음 또는 아직 확인 시간 아님
        """
        now = time.time()

        # 주기 확인
        if now - self._last_check_time < self.check_interval:
            return False
        self._last_check_time = now

        # 파일 존재 확인
        if not self.model_path.exists():
            return False

        # mtime 비교
        current_mtime = self.model_path.stat().st_mtime
        if current_mtime <= self._last_mtime:
            return False

        # 변경 감지 → 리로드 시도
        return self._reload_weights(current_mtime)

    def _reload_weights(self, new_mtime: float) -> bool:
        """새 가중치 로드 및 적용"""
        try:
            data = np.load(str(self.model_path), allow_pickle=False)

            # 필수 키 확인
            required_keys = {"W1", "b1", "W2", "b2", "W3", "b3"}
            if not required_keys.issubset(set(data.files)):
                print(
                    f"[HOT_RELOAD] Invalid model file: missing keys "
                    f"{required_keys - set(data.files)}"
                )
                return False

            # 차원 검증
            policy = self.rl_agent.policy
            if data["W1"].shape != (policy.input_dim, policy.hidden_dim):
                print(
                    f"[HOT_RELOAD] Shape mismatch W1: "
                    f"expected {(policy.input_dim, policy.hidden_dim)}, "
                    f"got {data['W1'].shape}"
                )
                return False

            # 가중치 교체
            new_weights = {
                "W1": data["W1"],
                "b1": data["b1"],
                "W2": data["W2"],
                "b2": data["b2"],
                "W3": data["W3"],
                "b3": data["b3"],
            }
            policy.set_weights(new_weights)

            # baseline/episode_count도 있으면 반영
            if "baseline" in data.files:
                self.rl_agent.baseline = float(data["baseline"][0])
            if "episode_count" in data.files:
                self.rl_agent.episode_count = int(data["episode_count"][0])

            self._last_mtime = new_mtime
            self._reload_count += 1

            print(
                f"[HOT_RELOAD] ★ Model reloaded (#{self._reload_count}) "
                f"from {self.model_path.name} ★"
            )
            return True

        except Exception as e:
            print(f"[HOT_RELOAD] Reload failed (keeping old weights): {e}")
            return False

    def get_status(self) -> dict:
        """리로더 상태 반환"""
        return {
            "model_path": str(self.model_path),
            "model_exists": self.model_path.exists(),
            "last_mtime": self._last_mtime,
            "reload_count": self._reload_count,
            "check_interval": self.check_interval,
        }
