# -*- coding: utf-8 -*-
"""
Batch Trainer - 배치 학습 처리 관리

CRITICAL IMPROVEMENT: 축적된 배치 데이터를 일괄적으로 묶어서 한번에 업데이트
"""

import json
import torch
import torch.nn as nn
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


class BatchTrainer:
    """
    배치 학습 트레이너

    축적된 게임 결과 데이터를 일괄적으로 묶어서 모델을 학습시킵니다.
    """

    def __init__(self, model_path: Optional[str] = None, learning_rate: float = 0.001):
        """
        Args:
            model_path: 모델 파일 경로 (미지정시 기본 경로)
            learning_rate: 학습률
        """
        self.model_path = Path(model_path) if model_path else Path("local_training/models/zerg_net_model.pt")
        self.learning_rate = learning_rate
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 모델 및 옵티마이저 초기화
        self.model = None
        self.optimizer = None
        self._initialize_model()

    def _initialize_model(self):
        """모델 초기화"""
        try:
            # 입력: 15차원 특징 벡터
            # 은닉층: 64 유닛
            # 출력: 5가지 전략 확률 (ECONOMY, AGGRESSIVE, DEFENSIVE, TECH, ALL_IN)
            input_size = 15
            hidden_size = 64
            output_size = 5

            self.model = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, output_size),
                nn.Softmax(dim=1)
            ).to(self.device)

            # 기존 모델 로드 시도
            if self.model_path.exists():
                try:
                    self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                    print(f"[INFO] Loaded existing model from {self.model_path}")
                except Exception as e:
                    print(f"[WARNING] Failed to load model: {e}, using new model")

            # 옵티마이저 설정
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

        except Exception as e:
            print(f"[ERROR] Model initialization failed: {e}")
            raise

    def train_from_batch_results(self, batch_results: List[Dict[str, Any]], epochs: int = 10) -> Dict[str, float]:
        """
        배치 결과로부터 학습 수행

        CRITICAL IMPROVEMENT: 축적된 배치 데이터를 일괄적으로 묶어서 한번에 업데이트

        Args:
            batch_results: 게임 결과 리스트
            epochs: 학습 에포크 수

        Returns:
            학습 결과 딕셔너리
        """
        if not batch_results:
            print("[WARNING] No batch results to train on")
            return {"loss": 0.0, "accuracy": 0.0}

        try:
            # 학습 데이터 준비
            inputs, targets = self._prepare_training_data(batch_results)

            if len(inputs) == 0:
                print("[WARNING] No valid training data")
                return {"loss": 0.0, "accuracy": 0.0}

            # 학습 루프
            total_loss = 0.0
            correct_predictions = 0
            total_samples = 0

            self.model.train()
            loss_fn = nn.CrossEntropyLoss()  # ★ FIX: 루프 외부에서 1회만 생성

            for epoch in range(epochs):
                epoch_loss = 0.0

                # 미니배치 처리
                batch_size = min(32, len(inputs))
                for i in range(0, len(inputs), batch_size):
                    batch_inputs = inputs[i:i+batch_size]
                    batch_targets = targets[i:i+batch_size]

                    # Forward pass
                    self.optimizer.zero_grad()
                    outputs = self.model(batch_inputs)

                    # 손실 계산
                    loss = loss_fn(outputs, batch_targets.argmax(dim=1))

                    # Backward pass
                    loss.backward()
                    # ★ FIX: Gradient clipping (폭발 방지)
                    nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    self.optimizer.step()

                    epoch_loss += loss.item()

                    # 정확도 계산
                    predictions = outputs.argmax(dim=1)
                    correct = (predictions == batch_targets.argmax(dim=1)).sum().item()
                    correct_predictions += correct
                    total_samples += len(batch_inputs)

                total_loss += epoch_loss

                if (epoch + 1) % 5 == 0:
                    avg_loss = epoch_loss / (len(inputs) // batch_size + 1)
                    accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
                    print(f"[EPOCH {epoch+1}/{epochs}] Loss: {avg_loss:.4f}, Accuracy: {accuracy:.2%}")

            # 최종 통계 계산
            avg_loss = total_loss / epochs
            final_accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0

            # 모델 저장
            self._save_model()

            print(f"[SUCCESS] Batch training completed - Avg Loss: {avg_loss:.4f}, Accuracy: {final_accuracy:.2%}")

            return {
                "loss": avg_loss,
                "accuracy": final_accuracy,
                "samples": total_samples
            }

        except Exception as e:
            print(f"[ERROR] Batch training failed: {e}")
            import traceback
            traceback.print_exc()
            return {"loss": 0.0, "accuracy": 0.0, "error": str(e)}

    def _prepare_training_data(self, batch_results: List[Dict[str, Any]]) -> tuple:
        """
        배치 결과를 학습 데이터로 변환

        Args:
            batch_results: 게임 결과 리스트

        Returns:
            (inputs, targets) 튜플
        """
        inputs = []
        targets = []

        for result in batch_results:
            try:
                # 입력 특징 추출
                input_data = self._extract_input_features(result)
                if input_data is None:
                    continue

                # 타겟 레이블 추출
                target_data = self._extract_target_features(result)
                if target_data is None:
                    continue

                inputs.append(input_data)
                targets.append(target_data)

            except Exception as e:
                print(f"[WARNING] Failed to process result: {e}")
                continue

        if not inputs:
            return torch.tensor([]), torch.tensor([])

        # 텐서로 변환
        inputs_tensor = torch.tensor(inputs, dtype=torch.float32).to(self.device)
        targets_tensor = torch.tensor(targets, dtype=torch.float32).to(self.device)

        return inputs_tensor, targets_tensor

    def _extract_input_features(self, result: Dict[str, Any]) -> Optional[List[float]]:
        """입력 특징 벡터 추출 (15차원)"""
        try:
            # 아군 상태 (5개)
            minerals = result.get("minerals", 0) / 2000.0
            gas = result.get("gas", 0) / 1000.0
            supply_used = result.get("supply_used", 0) / 200.0
            drone_count = result.get("drone_count", 0) / 100.0
            army_count = result.get("army_count", 0) / 100.0

            # 적군 상태 (10개)
            enemy_army = result.get("enemy_army_count", 0) / 100.0
            enemy_tech = result.get("enemy_tech_level", 0) / 2.0
            enemy_threat = result.get("enemy_threat_level", 0) / 4.0
            enemy_diversity = result.get("enemy_unit_diversity", 0.0)
            scout_coverage = result.get("scout_coverage", 0.0)
            enemy_distance = result.get("enemy_main_distance", 0.0) / 100.0
            enemy_expansions = result.get("enemy_expansion_count", 0) / 5.0
            enemy_resources = result.get("enemy_resource_estimate", 0) / 5000.0
            enemy_upgrades = result.get("enemy_upgrade_count", 0) / 10.0
            enemy_air_ground = result.get("enemy_air_ground_ratio", 0.5)

            features = [
                minerals, gas, supply_used, drone_count, army_count,
                enemy_army, enemy_tech, enemy_threat, enemy_diversity, scout_coverage,
                enemy_distance, enemy_expansions, enemy_resources, enemy_upgrades, enemy_air_ground
            ]

            return features

        except Exception as e:
            print(f"[WARNING] Feature extraction failed: {e}")
            return None

    def _extract_target_features(self, result: Dict[str, Any]) -> Optional[List[float]]:
        """타겟 레이블 추출 (4차원 전략 확률)"""
        try:
            # 승리 여부 확인
            victory = result.get("victory", False)

            # 전략 확률 가져오기
            attack_prob = result.get("attack_probability", 0.25)
            defense_prob = result.get("defense_probability", 0.25)
            economy_prob = result.get("economy_probability", 0.25)
            tech_prob = result.get("tech_probability", 0.25)

            # 승리 시 해당 전략 강화
            if victory:
                if attack_prob > defense_prob:
                    attack_prob = min(1.0, attack_prob * 1.2)
                elif defense_prob > economy_prob:
                    defense_prob = min(1.0, defense_prob * 1.2)
                elif economy_prob > tech_prob:
                    economy_prob = min(1.0, economy_prob * 1.2)
                else:
                    tech_prob = min(1.0, tech_prob * 1.2)

            # 정규화 (합이 1이 되도록)
            total = attack_prob + defense_prob + economy_prob + tech_prob
            if total > 0:
                attack_prob /= total
                defense_prob /= total
                economy_prob /= total
                tech_prob /= total

            return [attack_prob, defense_prob, economy_prob, tech_prob]

        except Exception as e:
            print(f"[WARNING] Target extraction failed: {e}")
            return None

    def _save_model(self):
        """학습된 모델 저장"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), self.model_path)
            print(f"[INFO] Model saved to {self.model_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save model: {e}")


def train_from_manifest(manifest_path: Path, model_path: Optional[str] = None, epochs: int = 10) -> Dict[str, float]:
    """
    매니페스트 파일로부터 배치 학습 수행

    Args:
        manifest_path: 매니페스트 파일 경로
        model_path: 모델 파일 경로 (선택사항)
        epochs: 학습 에포크 수

    Returns:
        학습 결과 딕셔너리
    """
    try:
        # 매니페스트 파일 확인
        if not manifest_path.exists():
            print(f"[ERROR] Manifest file not found: {manifest_path}")
            return {"loss": 0.0, "accuracy": 0.0}

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)

        # 결과 데이터 추출
        batch_results = manifest_data.get("results", [])
        if not batch_results:
            # 리플레이 데이터 시도
            batch_results = manifest_data.get("replays", [])

        if not batch_results:
            print(f"[WARNING] No results found in manifest: {manifest_path}")
            return {"loss": 0.0, "accuracy": 0.0}

        # 배치 학습 수행
        trainer = BatchTrainer(model_path=model_path)
        stats = trainer.train_from_batch_results(batch_results, epochs=epochs)

        return stats

    except Exception as e:
        print(f"[ERROR] Training from manifest failed: {e}")
        import traceback
        traceback.print_exc()
        return {"loss": 0.0, "accuracy": 0.0, "error": str(e)}
