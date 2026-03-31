"""
Phase 539: HuggingFace Transformers
SC2 Bot game sequence modeling with transformer (BERT/GPT-style)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from transformers import (
        AutoConfig, AutoModel, AutoModelForSequenceClassification,
        PreTrainedModel, PretrainedConfig,
        Trainer, TrainingArguments,
        DataCollatorWithPadding,
    )
    import torch
    import torch.nn as nn
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


# ─────────────────────────────────────────────
# Custom SC2 config (PretrainedConfig)
# ─────────────────────────────────────────────

if HF_AVAILABLE:
    class SC2TransformerConfig(PretrainedConfig):
        model_type = "sc2_transformer"

        def __init__(
            self,
            obs_dim: int = 16,
            seq_len: int = 64,
            n_heads: int = 4,
            n_layers: int = 4,
            d_model: int = 128,
            d_ff: int = 512,
            dropout: float = 0.1,
            n_actions: int = 7,
            vocab_size: int = 256,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.obs_dim = obs_dim
            self.seq_len = seq_len
            self.n_heads = n_heads
            self.n_layers = n_layers
            self.d_model = d_model
            self.d_ff = d_ff
            self.dropout = dropout
            self.n_actions = n_actions
            self.vocab_size = vocab_size

    # ─────────────────────────────────────────────
    # SC2 Transformer Model
    # ─────────────────────────────────────────────

    class SC2TransformerModel(PreTrainedModel):
        config_class = SC2TransformerConfig

        def __init__(self, config: SC2TransformerConfig):
            super().__init__(config)
            self.obs_embed = nn.Linear(config.obs_dim, config.d_model)
            self.pos_embed = nn.Embedding(config.seq_len, config.d_model)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=config.d_model,
                nhead=config.n_heads,
                dim_feedforward=config.d_ff,
                dropout=config.dropout,
                batch_first=True,
            )
            self.transformer = nn.TransformerEncoder(
                encoder_layer, num_layers=config.n_layers
            )
            self.policy_head = nn.Linear(config.d_model, config.n_actions)
            self.value_head  = nn.Linear(config.d_model, 1)
            self.post_init()

        def forward(
            self,
            obs_seq: "torch.Tensor",
            attention_mask: Optional["torch.Tensor"] = None,
            labels: Optional["torch.Tensor"] = None,
        ):
            B, T, _ = obs_seq.shape
            positions = torch.arange(T, device=obs_seq.device).unsqueeze(0)

            h = self.obs_embed(obs_seq) + self.pos_embed(positions)
            if attention_mask is not None:
                key_padding_mask = (attention_mask == 0)
            else:
                key_padding_mask = None

            h = self.transformer(h, src_key_padding_mask=key_padding_mask)

            # Use last token for prediction (GPT-style)
            last = h[:, -1, :]
            logits = self.policy_head(last)
            value  = self.value_head(last).squeeze(-1)

            loss = None
            if labels is not None:
                loss_fn = nn.CrossEntropyLoss()
                loss = loss_fn(logits, labels)

            return {"logits": logits, "value": value, "loss": loss,
                    "hidden_states": h}


# ─────────────────────────────────────────────
# Game sequence dataset (HF Dataset-compatible)
# ─────────────────────────────────────────────

def generate_game_sequences(
    n_games: int = 200,
    seq_len: int = 64,
    obs_dim: int = 16,
) -> list[dict]:
    """Generate synthetic game observation sequences."""
    from gymnasium_env.sc2_gym_env import SC2ZergEnv

    env = SC2ZergEnv(max_frames=500)
    dataset = []

    for game in range(n_games):
        obs, _ = env.reset(seed=game)
        sequence = [obs]
        actions = []
        done = False

        while not done and len(sequence) < seq_len + 1:
            action = random.randint(0, 6)
            next_obs, _, term, trunc, _ = env.step(action)
            sequence.append(next_obs)
            actions.append(action)
            done = term or trunc
            obs = next_obs

        # Pad or truncate
        while len(sequence) < seq_len + 1:
            sequence.append([0.0] * obs_dim)
            actions.append(0)

        dataset.append({
            "obs_seq": sequence[:seq_len],
            "label": actions[seq_len - 1] if actions else 0,
        })

    return dataset


# ─────────────────────────────────────────────
# Python-native transformer (no HF)
# ─────────────────────────────────────────────

class PythonSelfAttention:
    """Manual self-attention without frameworks."""

    def __init__(self, d_model: int, n_heads: int):
        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads

    def scaled_dot_product(
        self, q: list[list[float]],
        k: list[list[float]],
        v: list[list[float]],
    ) -> list[list[float]]:
        T = len(q)
        scale = math.sqrt(self.head_dim)
        scores = []
        for i in range(T):
            row = []
            for j in range(T):
                dot = sum(q[i][d] * k[j][d] for d in range(len(q[i])))
                row.append(dot / scale)
            scores.append(row)

        # Softmax per row
        attn = []
        for row in scores:
            max_r = max(row)
            exp_r = [math.exp(x - max_r) for x in row]
            sum_r = sum(exp_r)
            attn.append([e / sum_r for e in exp_r])

        # Weighted sum
        out = []
        for i in range(T):
            weighted = [0.0] * len(v[0])
            for j in range(T):
                for d in range(len(v[0])):
                    weighted[d] += attn[i][j] * v[j][d]
            out.append(weighted)
        return out


# ─────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────

def train_hf_model(epochs: int = 3) -> dict:
    if not HF_AVAILABLE:
        print("[HF] Not available — using statistics on generated data")
        data = generate_game_sequences(n_games=50)
        action_counts = [0] * 7
        for sample in data:
            action_counts[sample["label"]] += 1
        return {
            "samples": len(data),
            "action_distribution": action_counts,
        }

    import torch
    from torch.utils.data import Dataset as TorchDataset

    class SC2Dataset(TorchDataset):
        def __init__(self, data, seq_len=64, obs_dim=16):
            self.data = data
            self.seq_len = seq_len
            self.obs_dim = obs_dim

        def __len__(self): return len(self.data)

        def __getitem__(self, idx):
            item = self.data[idx]
            obs_seq = torch.FloatTensor(item["obs_seq"])
            label = torch.LongTensor([item["label"]])[0]
            return {"obs_seq": obs_seq, "labels": label}

    config = SC2TransformerConfig()
    model = SC2TransformerModel(config)

    raw_data = generate_game_sequences(n_games=100)
    split = int(len(raw_data) * 0.8)
    train_ds = SC2Dataset(raw_data[:split])
    eval_ds  = SC2Dataset(raw_data[split:])

    training_args = TrainingArguments(
        output_dir="./sc2_transformer",
        num_train_epochs=epochs,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        evaluation_strategy="epoch",
        save_strategy="no",
        logging_steps=10,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )
    trainer.train()
    return {"epochs": epochs, "samples": len(raw_data)}


if __name__ == "__main__":
    print("Phase 539: HuggingFace Transformers — SC2 Game Sequence Model")
    print(f"HuggingFace available: {HF_AVAILABLE}")
    result = train_hf_model(epochs=2)
    print(f"Result: {result}")
