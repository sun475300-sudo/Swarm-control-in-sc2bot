"""
Phase 358: Model Distillation
Knowledge distillation from large teacher model to compact student model.
Supports KL policy distillation, MSE value distillation, and online self-play distillation.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class DistillConfig:
    teacher_hidden: int = 512
    student_hidden: int = 128
    obs_dim: int = 512
    action_dim: int = 256
    temperature: float = 2.0       # softmax temperature for soft targets
    kl_weight: float = 1.0         # policy KL divergence weight
    value_weight: float = 0.5      # value MSE weight
    ce_weight: float = 0.5         # hard-label cross-entropy weight
    lr: float = 1e-3
    n_epochs: int = 5
    batch_size: int = 256


class TeacherModel(nn.Module):
    """Large capacity policy+value network (teacher)."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.policy = nn.Linear(hidden_dim, action_dim)
        self.value = nn.Linear(hidden_dim, 1)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.net(obs)
        return self.policy(h), self.value(h).squeeze(-1)

    def get_action(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits, value = self.forward(obs)
        dist = Categorical(logits=logits)
        return dist.sample(), value


class StudentModel(nn.Module):
    """Compact policy+value network (student)."""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.policy = nn.Linear(hidden_dim, action_dim)
        self.value = nn.Linear(hidden_dim, 1)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.net(obs)
        return self.policy(h), self.value(h).squeeze(-1)

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())


def distillation_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    student_value: torch.Tensor,
    teacher_value: torch.Tensor,
    hard_actions: torch.Tensor,
    cfg: DistillConfig,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """
    Combined distillation loss:
      - KL divergence on soft policy (temperature-scaled)
      - MSE on value
      - Cross-entropy on hard (argmax) teacher actions
    """
    T = cfg.temperature
    soft_teacher = F.softmax(teacher_logits / T, dim=-1)
    log_soft_student = F.log_softmax(student_logits / T, dim=-1)
    kl_loss = F.kl_div(log_soft_student, soft_teacher.detach(), reduction="batchmean") * (T ** 2)
    value_loss = F.mse_loss(student_value, teacher_value.detach())
    ce_loss = F.cross_entropy(student_logits, hard_actions)
    total = cfg.kl_weight * kl_loss + cfg.value_weight * value_loss + cfg.ce_weight * ce_loss
    return total, {
        "kl_loss": kl_loss.item(),
        "value_loss": value_loss.item(),
        "ce_loss": ce_loss.item(),
        "total_loss": total.item(),
    }


class DistillationTrainer:
    """Trains student model to mimic teacher using knowledge distillation."""

    def __init__(self, teacher: TeacherModel, student: StudentModel,
                 cfg: DistillConfig):
        self.teacher = teacher
        self.student = student
        self.cfg = cfg
        self.teacher.eval()
        self.optimizer = torch.optim.Adam(student.parameters(), lr=cfg.lr)

    def distill_batch(self, obs: torch.Tensor) -> Dict[str, float]:
        with torch.no_grad():
            teacher_logits, teacher_value = self.teacher(obs)
            hard_actions = Categorical(logits=teacher_logits).sample()

        student_logits, student_value = self.student(obs)
        loss, metrics = distillation_loss(
            student_logits, teacher_logits,
            student_value, teacher_value,
            hard_actions, self.cfg)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return metrics

    def distill_dataset(self, obs_data: torch.Tensor) -> Dict[str, float]:
        """Run cfg.n_epochs distillation passes over obs_data."""
        all_metrics: Dict[str, list] = {"kl_loss": [], "value_loss": [],
                                        "ce_loss": [], "total_loss": []}
        for epoch in range(self.cfg.n_epochs):
            idx = torch.randperm(len(obs_data))
            for start in range(0, len(obs_data), self.cfg.batch_size):
                batch = obs_data[idx[start: start + self.cfg.batch_size]]
                m = self.distill_batch(batch)
                for k, v in m.items():
                    all_metrics[k].append(v)
        return {k: sum(v) / len(v) for k, v in all_metrics.items()}

    def online_distill_step(self, obs: torch.Tensor) -> Dict[str, float]:
        """Single-step online distillation during self-play collection."""
        return self.distill_batch(obs)

    def compression_ratio(self) -> float:
        teacher_params = sum(p.numel() for p in self.teacher.parameters())
        student_params = self.student.parameter_count()
        return teacher_params / max(student_params, 1)
