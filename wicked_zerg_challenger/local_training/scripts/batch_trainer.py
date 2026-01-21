# -*- coding: utf-8 -*-
"""
Batch Trainer - ��ġ �н� ���� ����

CRITICAL IMPROVEMENT: ������ ��ġ �����͸� �������� �Ű�� ����ġ ������Ʈ
"""

import json
import torch
import torch.nn as nn
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


class BatchTrainer:
    """
    ��ġ �н� Ʈ���̳�
    
    ������ ���� ��� �����͸� �������� �Ű�� ���� �н���ŵ�ϴ�.
    """
    
    def __init__(self, model_path: Optional[str] = None, learning_rate: float = 0.001):
        """
        Args:
            model_path: �� ���� ��� (������ ���� ����)
            learning_rate: �н���
        """
        self.model_path = Path(model_path) if model_path else Path("local_training/models/zerg_net_model.pt")
        self.learning_rate = learning_rate
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # �� �ʱ�ȭ
        self.model = None
        self.optimizer = None
        self._initialize_model()
    
    def _initialize_model(self):
        """�Ű�� �� �ʱ�ȭ"""
        try:
            # �� ���� ���� (ZergNet �⺻ ����)
            # Input: 15���� (Self 5 + Enemy 10)
            # Output: 4���� (Attack, Defense, Economy, Tech)
            input_size = 15
            hidden_size = 64
            output_size = 4
            
            self.model = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, output_size),
                nn.Softmax(dim=1)
            ).to(self.device)
            
            # ���� ���� ������ �ε�
            if self.model_path.exists():
                try:
                    self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                    print(f"[INFO] Loaded existing model from {self.model_path}")
                except Exception as e:
                    print(f"[WARNING] Failed to load model: {e}, using new model")
            
            # ��Ƽ������ �ʱ�ȭ
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
            
        except Exception as e:
            print(f"[ERROR] Model initialization failed: {e}")
            raise
    
    def train_from_batch_results(self, batch_results: List[Dict[str, Any]], epochs: int = 10) -> Dict[str, float]:
        """
        ��ġ ����κ��� �н� ����
        
        CRITICAL IMPROVEMENT: ������ ��ġ �����͸� �������� �Ű�� ����ġ ������Ʈ
        
        Args:
            batch_results: ���� ��� ����Ʈ
            epochs: �н� ����ũ ��
            
        Returns:
            �н� ��� ��ųʸ�
        """
        if not batch_results:
            print("[WARNING] No batch results to train on")
            return {"loss": 0.0, "accuracy": 0.0}
        
        try:
            # ������ �غ�
            inputs, targets = self._prepare_training_data(batch_results)
            
            if len(inputs) == 0:
                print("[WARNING] No valid training data")
                return {"loss": 0.0, "accuracy": 0.0}
            
            # �н� ����
            total_loss = 0.0
            correct_predictions = 0
            total_samples = 0
            
            self.model.train()
            
            for epoch in range(epochs):
                epoch_loss = 0.0
                
                # ��ġ ó��
                batch_size = min(32, len(inputs))
                for i in range(0, len(inputs), batch_size):
                    batch_inputs = inputs[i:i+batch_size]
                    batch_targets = targets[i:i+batch_size]
                    
                    # Forward pass
                    self.optimizer.zero_grad()
                    outputs = self.model(batch_inputs)
                    
                    # Loss ��� (Cross Entropy)
                    loss_fn = nn.CrossEntropyLoss()
                    loss = loss_fn(outputs, batch_targets.argmax(dim=1))
                    
                    # Backward pass
                    loss.backward()
                    self.optimizer.step()
                    
                    epoch_loss += loss.item()
                    
                    # ��Ȯ�� ���
                    predictions = outputs.argmax(dim=1)
                    correct = (predictions == batch_targets.argmax(dim=1)).sum().item()
                    correct_predictions += correct
                    total_samples += len(batch_inputs)
                
                total_loss += epoch_loss
                
                if (epoch + 1) % 5 == 0:
                    avg_loss = epoch_loss / (len(inputs) // batch_size + 1)
                    accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
                    print(f"[EPOCH {epoch+1}/{epochs}] Loss: {avg_loss:.4f}, Accuracy: {accuracy:.2%}")
            
            # ���� ���
            avg_loss = total_loss / epochs
            final_accuracy = correct_predictions / total_samples if total_samples > 0 else 0.0
            
            # �� ����
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
        ��ġ ����� �н� �����ͷ� ��ȯ
        
        Args:
            batch_results: ���� ��� ����Ʈ
            
        Returns:
            (inputs, targets) Ʃ��
        """
        inputs = []
        targets = []
        
        for result in batch_results:
            try:
                # �Է� ������ ���� (15����)
                input_data = self._extract_input_features(result)
                if input_data is None:
                    continue
                
                # Ÿ�� ������ ���� (4����: Attack, Defense, Economy, Tech)
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
        
        # �ټ��� ��ȯ
        inputs_tensor = torch.tensor(inputs, dtype=torch.float32).to(self.device)
        targets_tensor = torch.tensor(targets, dtype=torch.float32).to(self.device)
        
        return inputs_tensor, targets_tensor
    
    def _extract_input_features(self, result: Dict[str, Any]) -> Optional[List[float]]:
        """���� ������� �Է� Ư¡ ����"""
        try:
            # Self Ư¡ (5����)
            minerals = result.get("minerals", 0) / 2000.0  # ����ȭ
            gas = result.get("gas", 0) / 1000.0
            supply_used = result.get("supply_used", 0) / 200.0
            drone_count = result.get("drone_count", 0) / 100.0
            army_count = result.get("army_count", 0) / 100.0
            
            # Enemy Ư¡ (10����)
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
        """���� ������� Ÿ�� Ư¡ ����"""
        try:
            # �¸� ���ο� ���� ���� ����ġ ����
            victory = result.get("victory", False)
            
            # ���� ���õ� ���� (��� ���)
            attack_prob = result.get("attack_probability", 0.25)
            defense_prob = result.get("defense_probability", 0.25)
            economy_prob = result.get("economy_probability", 0.25)
            tech_prob = result.get("tech_probability", 0.25)
            
            # �¸� �� ���õ� ������ ���ʽ�
            if victory:
                if attack_prob > defense_prob:
                    attack_prob = min(1.0, attack_prob * 1.2)
                elif defense_prob > economy_prob:
                    defense_prob = min(1.0, defense_prob * 1.2)
                elif economy_prob > tech_prob:
                    economy_prob = min(1.0, economy_prob * 1.2)
                else:
                    tech_prob = min(1.0, tech_prob * 1.2)
            
            # ����ȭ
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
        """�� ����"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), self.model_path)
            print(f"[INFO] Model saved to {self.model_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save model: {e}")


def train_from_manifest(manifest_path: Path, model_path: Optional[str] = None, epochs: int = 10) -> Dict[str, float]:
    """
    �Ŵ��佺Ʈ ���Ϸκ��� ��ġ �н� ����
    
    Args:
        manifest_path: �Ŵ��佺Ʈ ���� ���
        model_path: �� ���� ��� (���û���)
        epochs: �н� ����ũ ��
        
    Returns:
        �н� ��� ��ųʸ�
    """
    try:
        # �Ŵ��佺Ʈ ���� �б�
        if not manifest_path.exists():
            print(f"[ERROR] Manifest file not found: {manifest_path}")
            return {"loss": 0.0, "accuracy": 0.0}
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # ��ġ ��� ����
        batch_results = manifest_data.get("results", [])
        if not batch_results:
            # �Ŵ��佺Ʈ ������ �ٸ� �� ����
            batch_results = manifest_data.get("replays", [])
        
        if not batch_results:
            print(f"[WARNING] No results found in manifest: {manifest_path}")
            return {"loss": 0.0, "accuracy": 0.0}
        
        # ��ġ �н� ����
        trainer = BatchTrainer(model_path=model_path)
        stats = trainer.train_from_batch_results(batch_results, epochs=epochs)
        
        return stats
    
    except Exception as e:
        print(f"[ERROR] Training from manifest failed: {e}")
        import traceback
        traceback.print_exc()
        return {"loss": 0.0, "accuracy": 0.0, "error": str(e)}
