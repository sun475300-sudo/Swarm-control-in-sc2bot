"""
huggingface_nlp/strategy_classifier.py
HuggingFace Transformers-based classifier for SC2 game situation descriptions.

Loads distilbert-base-uncased, adds a classification head,
and fine-tunes on synthetic SC2 situation → strategy label pairs.

Strategies: expand | attack | defend | tech | macro
"""

from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

# ---------------------------------------------------------------------------
# Label mapping
# ---------------------------------------------------------------------------
STRATEGY_LABELS = ["expand", "attack", "defend", "tech", "macro"]
LABEL2ID = {s: i for i, s in enumerate(STRATEGY_LABELS)}
ID2LABEL = {i: s for i, s in enumerate(STRATEGY_LABELS)}
NUM_LABELS = len(STRATEGY_LABELS)

# ---------------------------------------------------------------------------
# Synthetic SC2 situation → strategy dataset
# ---------------------------------------------------------------------------
SC2_SITUATIONS: list[tuple[str, str]] = [
    # expand
    ("enemy is on two bases and we have three bases already", "expand"),
    ("map control is strong and no enemy pressure detected", "expand"),
    ("our economy is falling behind expand now", "expand"),
    ("creep spread covers the map take a fourth base", "expand"),
    ("enemy expanding with 3 bases and we only have 2", "expand"),
    ("safe to take third hatchery natural is secure", "expand"),
    # attack
    ("our ling bane ball is maxed out attack now", "attack"),
    ("enemy has low army count hit before they rebuild", "attack"),
    ("roach ravager push ready enemy has no static defense", "attack"),
    ("ultralisk broodlord composition complete end the game", "attack"),
    ("enemy third base exposed zergling run-by opportunity", "attack"),
    ("nydus worm ready strike the main base", "attack"),
    # defend
    ("enemy marine marauder push incoming hold at ramp", "defend"),
    ("proxy barracks detected prepare spine crawlers", "defend"),
    ("colossus force coming build queens and spines", "defend"),
    ("cannon rush at natural pull drones defend", "defend"),
    ("bio ball timing attack inbound spine up now", "defend"),
    ("enemy all-in zergling flood pour units to hold", "defend"),
    # tech
    ("upgrade to hive for brood lords and ultras", "tech"),
    ("research carapace and ranged attack upgrades", "tech"),
    ("lair is complete start lurker den research", "tech"),
    ("banelings need speed upgrade immediately", "tech"),
    ("metabolic boost research started pool complete", "tech"),
    ("get hive then research chitinous plating", "tech"),
    # macro
    ("inject all hatcheries and spread creep", "macro"),
    ("drone up to 66 drones before making army", "macro"),
    ("queen injects are behind recover economy first", "macro"),
    ("rally workers mine minerals quickly build drones", "macro"),
    ("saturate all bases before building spire", "macro"),
    ("larva inject timing missed recover drones now", "macro"),
]


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class SC2SituationDataset(Dataset):
    def __init__(self, data: list[tuple[str, str]], tokenizer, max_length: int = 64):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.texts = [d[0] for d in data]
        self.labels = [LABEL2ID[d[1]] for d in data]

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        enc = self.tokenizer(
            self.texts[idx],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.labels[idx], dtype=torch.long),
        }


# ---------------------------------------------------------------------------
# Model loader
# ---------------------------------------------------------------------------
MODEL_NAME = "distilbert-base-uncased"


def load_model_and_tokenizer():
    print(f"[StrategyClassifier] Loading {MODEL_NAME} …")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    return model, tokenizer


# ---------------------------------------------------------------------------
# Fine-tune
# ---------------------------------------------------------------------------
def fine_tune(
    model,
    tokenizer,
    epochs: int = 6,
    lr: float = 2e-5,
    batch_size: int = 8,
):
    # NOTE: 반환 타입을 'None' 으로 명시했었으나 함수 마지막에서 (model, device)
    # 튜플을 반환하고 caller (line 203) 가 'model, device = fine_tune(...)'
    # 로 unpack 한다. 시그니처를 실제 동작과 일치시키기 위해 annotation 제거.
    dataset = SC2SituationDataset(SC2_SITUATIONS, tokenizer)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    total_steps = len(dataloader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 5),
        num_training_steps=total_steps,
    )

    print(
        f"[StrategyClassifier] Fine-tuning on {len(dataset)} SC2 examples  "
        f"| epochs={epochs} | device={device}\n"
    )

    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        correct = 0
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids, attention_mask=attention_mask, labels=labels
            )
            loss = outputs.loss
            logits = outputs.logits

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            preds = logits.argmax(dim=-1)
            correct += (preds == labels).sum().item()

        avg_loss = total_loss / len(dataloader)
        acc = correct / len(dataset)
        print(f"  Epoch {epoch}/{epochs}  loss={avg_loss:.4f}  acc={acc:.2%}")

    return model, device


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def classify_situation(model, tokenizer, text: str, device) -> tuple[str, float]:
    """Return predicted strategy and confidence for a free-text SC2 description."""
    model.eval()
    enc = tokenizer(
        text, truncation=True, padding="max_length", max_length=64, return_tensors="pt"
    )
    input_ids = enc["input_ids"].to(device)
    attention_mask = enc["attention_mask"].to(device)

    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
    probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
    pred_idx = int(np.argmax(probs))
    return ID2LABEL[pred_idx], float(probs[pred_idx])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    model, tokenizer = load_model_and_tokenizer()
    model, device = fine_tune(model, tokenizer)

    print("\n--- Strategy Classification Inference ---")
    test_situations = [
        "enemy expanding with 3 bases attack the third",
        "queen inject timing is off get drones and macro",
        "ling speed done roach warren up hit the enemy",
        "enemy bio push coming build spines at natural",
        "upgrade to hive get broodlord corruptor composition",
        "map control established take fourth and fifth base",
    ]

    for situation in test_situations:
        strategy, confidence = classify_situation(model, tokenizer, situation, device)
        print(f'  [{strategy.upper():7s} {confidence:.1%}]  "{situation}"')
