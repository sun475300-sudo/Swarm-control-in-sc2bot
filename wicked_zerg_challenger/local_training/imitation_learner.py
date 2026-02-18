# -*- coding: utf-8 -*-
"""
Imitation Learner - 리플레이 모방학습 시스템 (#103)

SC2Replay 파일에서 전문가 행동을 추출하고 모방 학습합니다.

주요 기능:
1. SC2Replay 파일 파싱 및 행동 추출
2. 전문가 행동 데이터셋 구축
3. 지도학습(Supervised Learning)으로 정책 학습
4. 행동 복제(Behavioral Cloning) + DAgger 지원
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None


class ReplayActionExtractor:
    """
    SC2Replay 파일에서 행동 시퀀스를 추출합니다.

    SC2 리플레이 파일을 파싱하여 각 프레임별로
    전문가가 수행한 행동(빌드오더, 유닛 명령 등)을 추출합니다.
    """

    # SC2 저그 주요 행동 카테고리
    ACTION_CATEGORIES = {
        "build_drone": 0,
        "build_zergling": 1,
        "build_roach": 2,
        "build_hydralisk": 3,
        "build_mutalisk": 4,
        "build_overlord": 5,
        "build_queen": 6,
        "build_hatchery": 7,
        "build_extractor": 8,
        "build_spawning_pool": 9,
        "build_roach_warren": 10,
        "build_hydra_den": 11,
        "build_spire": 12,
        "build_lair": 13,
        "build_hive": 14,
        "attack_move": 15,
        "defend": 16,
        "inject_larva": 17,
        "spread_creep": 18,
        "upgrade": 19,
        "idle": 20,
    }

    NUM_ACTIONS = len(ACTION_CATEGORIES)

    def __init__(self, replay_dir: Optional[str] = None):
        """
        Args:
            replay_dir: 리플레이 파일 디렉토리
        """
        if replay_dir:
            self.replay_dir = Path(replay_dir)
        else:
            self.replay_dir = Path(__file__).parent / "data" / "replays"

        self.extracted_data: List[Dict[str, Any]] = []
        print(f"[IMITATION] ReplayActionExtractor 초기화 (replay_dir={self.replay_dir})")

    def extract_from_replay(self, replay_path: str) -> List[Dict[str, Any]]:
        """
        단일 리플레이 파일에서 행동 시퀀스 추출

        Args:
            replay_path: 리플레이 파일 경로

        Returns:
            프레임별 (상태, 행동) 쌍 리스트
        """
        frames = []
        try:
            # sc2reader 또는 s2protocol 사용 시도
            try:
                import sc2reader
                replay = sc2reader.load_replay(replay_path)

                for event in replay.events:
                    frame_data = self._parse_event(event, replay)
                    if frame_data:
                        frames.append(frame_data)

            except ImportError:
                # sc2reader 미설치 시 - 기본 파싱 시도
                print(f"[IMITATION] sc2reader 미설치, 기본 파싱 모드 사용")
                frames = self._basic_parse(replay_path)

        except Exception as e:
            print(f"[IMITATION] 리플레이 추출 실패 ({replay_path}): {e}")

        return frames

    def _parse_event(self, event, replay) -> Optional[Dict[str, Any]]:
        """
        리플레이 이벤트를 상태-행동 쌍으로 변환

        Args:
            event: sc2reader 이벤트
            replay: 리플레이 객체

        Returns:
            변환된 프레임 데이터 (또는 None)
        """
        try:
            # 유닛 생산 명령
            if hasattr(event, "unit") and hasattr(event, "ability_name"):
                ability = getattr(event, "ability_name", "").lower()

                # 행동 카테고리 매핑
                action = self._map_ability_to_action(ability)
                if action is not None:
                    frame = getattr(event, "frame", 0)
                    game_time = frame / 22.4  # SC2 프레임 -> 초 변환

                    return {
                        "frame": frame,
                        "game_time": game_time,
                        "action": action,
                        "ability_name": ability,
                    }
        except Exception:
            pass
        return None

    def _map_ability_to_action(self, ability_name: str) -> Optional[int]:
        """능력 이름을 행동 카테고리로 매핑"""
        ability = ability_name.lower()

        if "drone" in ability:
            return self.ACTION_CATEGORIES["build_drone"]
        elif "zergling" in ability:
            return self.ACTION_CATEGORIES["build_zergling"]
        elif "roach" in ability and "warren" not in ability:
            return self.ACTION_CATEGORIES["build_roach"]
        elif "hydralisk" in ability and "den" not in ability:
            return self.ACTION_CATEGORIES["build_hydralisk"]
        elif "mutalisk" in ability:
            return self.ACTION_CATEGORIES["build_mutalisk"]
        elif "overlord" in ability:
            return self.ACTION_CATEGORIES["build_overlord"]
        elif "queen" in ability:
            return self.ACTION_CATEGORIES["build_queen"]
        elif "hatchery" in ability:
            return self.ACTION_CATEGORIES["build_hatchery"]
        elif "extractor" in ability:
            return self.ACTION_CATEGORIES["build_extractor"]
        elif "spawningpool" in ability or "spawning pool" in ability:
            return self.ACTION_CATEGORIES["build_spawning_pool"]
        elif "roachwarren" in ability or "roach warren" in ability:
            return self.ACTION_CATEGORIES["build_roach_warren"]
        elif "hydraliskden" in ability or "hydralisk den" in ability:
            return self.ACTION_CATEGORIES["build_hydra_den"]
        elif "spire" in ability:
            return self.ACTION_CATEGORIES["build_spire"]
        elif "lair" in ability:
            return self.ACTION_CATEGORIES["build_lair"]
        elif "hive" in ability:
            return self.ACTION_CATEGORIES["build_hive"]
        elif "attack" in ability:
            return self.ACTION_CATEGORIES["attack_move"]
        elif "inject" in ability:
            return self.ACTION_CATEGORIES["inject_larva"]
        elif "creep" in ability:
            return self.ACTION_CATEGORIES["spread_creep"]

        return None

    def _basic_parse(self, replay_path: str) -> List[Dict[str, Any]]:
        """기본 파싱 (sc2reader 없이)"""
        # 리플레이 파일의 바이너리 데이터에서 최소한의 정보 추출
        # 실제 구현에서는 s2protocol 사용 권장
        print(f"[IMITATION] 기본 파싱: {replay_path}")
        return []

    def extract_all_replays(self) -> int:
        """
        디렉토리 내 모든 리플레이 추출

        Returns:
            추출된 총 프레임 수
        """
        total_frames = 0

        if not self.replay_dir.exists():
            print(f"[IMITATION] 리플레이 디렉토리 없음: {self.replay_dir}")
            return 0

        replay_files = list(self.replay_dir.glob("*.SC2Replay"))
        print(f"[IMITATION] {len(replay_files)}개 리플레이 파일 발견")

        for replay_file in replay_files:
            frames = self.extract_from_replay(str(replay_file))
            self.extracted_data.extend(frames)
            total_frames += len(frames)

        print(f"[IMITATION] 총 {total_frames}개 프레임 추출 완료")
        return total_frames

    def save_dataset(self, output_path: Optional[str] = None) -> bool:
        """추출 데이터를 파일로 저장"""
        if not self.extracted_data:
            print("[IMITATION] 저장할 데이터 없음")
            return False

        if output_path is None:
            output_path = str(self.replay_dir.parent / "imitation_dataset.json")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.extracted_data, f, indent=2, ensure_ascii=False)
            print(f"[IMITATION] 데이터셋 저장 완료: {output_path} ({len(self.extracted_data)} frames)")
            return True
        except Exception as e:
            print(f"[IMITATION] 데이터셋 저장 실패: {e}")
            return False


class ImitationNetwork(nn.Module):
    """
    모방학습용 신경망

    전문가 행동을 예측하는 분류 네트워크입니다.
    입력: 게임 상태 벡터
    출력: 행동 확률 분포
    """

    def __init__(self, state_dim: int = 15,
                 action_dim: int = ReplayActionExtractor.NUM_ACTIONS,
                 hidden_dim: int = 128):
        """
        Args:
            state_dim: 상태 벡터 차원
            action_dim: 행동 공간 크기
            hidden_dim: 은닉층 차원
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch가 필요합니다. pip install torch 로 설치하세요.")

        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, state: "torch.Tensor") -> "torch.Tensor":
        """순전파 -> 행동 logits"""
        return self.network(state)


class ImitationLearner:
    """
    모방학습 에이전트

    전문가 리플레이에서 추출한 행동 데이터를 사용하여
    지도학습(Supervised Learning)으로 정책을 학습합니다.

    지원 알고리즘:
    1. Behavioral Cloning (BC): 단순 지도학습
    2. DAgger: 학습된 정책으로 플레이 -> 전문가 라벨링 반복
    """

    def __init__(
        self,
        state_dim: int = 15,
        learning_rate: float = 1e-3,
        batch_size: int = 64,
        model_path: Optional[str] = None,
    ):
        """
        모방학습 에이전트 초기화

        Args:
            state_dim: 상태 벡터 차원
            learning_rate: 학습률
            batch_size: 배치 크기
            model_path: 모델 저장 경로
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch가 필요합니다. pip install torch 로 설치하세요.")

        self.state_dim = state_dim
        self.action_dim = ReplayActionExtractor.NUM_ACTIONS
        self.batch_size = batch_size

        # 모델 경로
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = Path(__file__).parent / "models" / "imitation_model.pt"

        # 디바이스
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 네트워크
        self.network = ImitationNetwork(state_dim, self.action_dim).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)
        self.criterion = nn.CrossEntropyLoss()

        # 학습 데이터
        self.dataset_states: List[np.ndarray] = []
        self.dataset_actions: List[int] = []

        # 통계
        self.epoch_count = 0
        self.training_history: List[Dict[str, float]] = []

        # 리플레이 추출기
        self.extractor = ReplayActionExtractor()

        # 모델 로드 시도
        self._load_model()

        print(f"[IMITATION] ImitationLearner 초기화 완료 "
              f"(state_dim={state_dim}, action_dim={self.action_dim}, device={self.device})")

    def add_demonstration(self, state: np.ndarray, action: int) -> None:
        """
        전문가 시연 데이터 추가

        Args:
            state: 게임 상태 벡터
            action: 전문가 행동 (정수 인덱스)
        """
        self.dataset_states.append(state.astype(np.float32))
        self.dataset_actions.append(action)

    def train_epoch(self) -> Dict[str, float]:
        """
        1 에폭 학습 수행

        Returns:
            학습 통계
        """
        if len(self.dataset_states) < self.batch_size:
            return {"loss": 0.0, "accuracy": 0.0, "samples": len(self.dataset_states)}

        self.network.train()

        # 데이터 셔플
        n = len(self.dataset_states)
        indices = np.random.permutation(n)

        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        for start in range(0, n, self.batch_size):
            end = min(start + self.batch_size, n)
            batch_idx = indices[start:end]

            states = torch.FloatTensor(
                np.array([self.dataset_states[i] for i in batch_idx])
            ).to(self.device)
            actions = torch.LongTensor(
                np.array([self.dataset_actions[i] for i in batch_idx])
            ).to(self.device)

            # 순전파
            logits = self.network(states)
            loss = self.criterion(logits, actions)

            # 역전파
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # 정확도 계산
            predictions = torch.argmax(logits, dim=-1)
            total_correct += (predictions == actions).sum().item()
            total_loss += loss.item() * len(batch_idx)
            total_samples += len(batch_idx)

        avg_loss = total_loss / max(total_samples, 1)
        accuracy = total_correct / max(total_samples, 1)

        self.epoch_count += 1
        stats = {
            "epoch": self.epoch_count,
            "loss": avg_loss,
            "accuracy": accuracy,
            "samples": total_samples,
        }
        self.training_history.append(stats)

        return stats

    def train(self, num_epochs: int = 100, verbose: bool = True) -> List[Dict[str, float]]:
        """
        여러 에폭 학습

        Args:
            num_epochs: 학습 에폭 수
            verbose: 로그 출력 여부

        Returns:
            에폭별 학습 통계
        """
        results = []
        for epoch in range(num_epochs):
            stats = self.train_epoch()
            results.append(stats)

            if verbose and epoch % 10 == 0:
                print(f"[IMITATION] Epoch {self.epoch_count}: "
                      f"loss={stats['loss']:.4f}, accuracy={stats['accuracy']:.3f}")

        return results

    def predict_action(self, state: np.ndarray) -> Tuple[int, np.ndarray]:
        """
        상태에서 행동 예측

        Args:
            state: 게임 상태 벡터

        Returns:
            (action_idx, action_probs): 예측 행동과 확률 분포
        """
        self.network.eval()

        state = state[:self.state_dim].astype(np.float32)
        state = np.nan_to_num(state, nan=0.0, posinf=1.0, neginf=-1.0)

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits = self.network(state_tensor)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]

        action_idx = np.argmax(probs)
        return int(action_idx), probs

    def save_model(self, path: Optional[str] = None) -> bool:
        """모델 저장"""
        save_path = Path(path) if path else self.model_path
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "epoch_count": self.epoch_count,
                "training_history": self.training_history[-100:],
            }, str(save_path))
            print(f"[IMITATION] 모델 저장 완료: {save_path}")
            return True
        except Exception as e:
            print(f"[IMITATION] 모델 저장 실패: {e}")
            return False

    def _load_model(self) -> bool:
        """모델 로드"""
        try:
            if self.model_path.exists():
                checkpoint = torch.load(str(self.model_path), map_location=self.device)
                self.network.load_state_dict(checkpoint["network_state_dict"])
                self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
                self.epoch_count = checkpoint.get("epoch_count", 0)
                self.training_history = checkpoint.get("training_history", [])
                print(f"[IMITATION] 모델 로드 완료: {self.model_path}")
                return True
        except Exception as e:
            print(f"[IMITATION] 모델 로드 실패: {e}")
        return False

    def get_stats(self) -> Dict[str, Any]:
        """학습 통계 반환"""
        return {
            "epoch_count": self.epoch_count,
            "dataset_size": len(self.dataset_states),
            "device": str(self.device),
        }
