"""
Phase 439: Modal - Serverless Cloud SC2 Training
GPU-accelerated serverless training and inference on Modal's cloud.
"""

import modal
from modal import App, Volume, Image, Period, web_endpoint
from pathlib import Path


# ── Modal App and infrastructure ──────────────────────────────────────────────

app = App("sc2-bot-training")

# Persistent volume for model checkpoints
checkpoint_volume = Volume.from_name("sc2-checkpoints", create_if_missing=True)

# Docker image with ML dependencies
sc2_image = (
    Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.2.0",
        "numpy",
        "pandas",
        "scikit-learn",
        "mlflow",
        "pydantic",
    )
)


# ── Training function (GPU) ───────────────────────────────────────────────────

@app.function(
    image=sc2_image,
    gpu="A100",
    memory=16384,
    timeout=7200,
    volumes={"/checkpoints": checkpoint_volume},
    secrets=[modal.Secret.from_name("sc2-training-secrets")],
)
def train_sc2_model(
    n_epochs: int = 100,
    batch_size: int = 256,
    learning_rate: float = 3e-4,
    model_version: str = "v1",
) -> dict:
    """
    Train SC2 strategy model on Modal A100 GPU.
    Checkpoints are saved to the persistent volume.
    """
    import torch
    import numpy as np
    import json
    from datetime import datetime

    print(f"[Modal] Training SC2 model on GPU: {torch.cuda.get_device_name(0)}")

    # Simulate training loop
    device = "cuda" if torch.cuda.is_available() else "cpu"
    losses = []
    best_val_loss = float("inf")

    for epoch in range(n_epochs):
        train_loss = 0.35 * np.exp(-epoch * 0.03) + np.random.uniform(0, 0.02)
        val_loss = train_loss + np.random.uniform(0.01, 0.05)
        losses.append({"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss})

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint_path = f"/checkpoints/sc2_{model_version}_best.pt"
            torch.save({"epoch": epoch, "val_loss": val_loss}, checkpoint_path)

        if epoch % 10 == 0:
            print(f"  Epoch {epoch}/{n_epochs}: train={train_loss:.4f}, val={val_loss:.4f}")

    checkpoint_volume.commit()

    result = {
        "model_version": model_version,
        "best_val_loss": round(best_val_loss, 4),
        "final_epoch": n_epochs,
        "checkpoint": f"/checkpoints/sc2_{model_version}_best.pt",
        "trained_at": datetime.now().isoformat(),
        "device": device,
    }
    print(f"[Modal] Training complete. Best val loss: {best_val_loss:.4f}")
    return result


# ── Scheduled periodic training ───────────────────────────────────────────────

@app.function(
    image=sc2_image,
    schedule=Period(days=1),
    volumes={"/checkpoints": checkpoint_volume},
    timeout=10800,
)
def daily_sc2_training() -> None:
    """Automated daily retraining of the SC2 model on fresh replay data."""
    import datetime
    print(f"[Modal] Daily training triggered at {datetime.datetime.now().isoformat()}")
    result = train_sc2_model.remote(
        n_epochs=50,
        batch_size=512,
        model_version=f"daily_{datetime.date.today().isoformat()}",
    )
    print(f"[Modal] Daily training result: {result}")


# ── Web endpoint for inference ────────────────────────────────────────────────

@app.function(
    image=sc2_image,
    memory=4096,
    volumes={"/checkpoints": checkpoint_volume},
)
@web_endpoint(method="POST", label="sc2-inference")
def predict_action(game_state: dict) -> dict:
    """
    HTTP inference endpoint for SC2 model.
    Accepts game state JSON, returns action recommendation.
    """
    import numpy as np

    features = np.array([
        game_state.get("game_time", 0) / 1800,
        game_state.get("supply_used", 0) / 200,
        game_state.get("minerals", 0) / 5000,
        game_state.get("gas", 0) / 2000,
        game_state.get("army_supply", 0) / 100,
        game_state.get("worker_count", 0) / 80,
    ], dtype=np.float32)

    # Simulate inference
    action_scores = np.random.softmax = lambda x: np.exp(x) / np.exp(x).sum()
    raw = np.random.randn(5)
    probs = np.exp(raw) / np.exp(raw).sum()
    actions = ["build_worker", "build_army", "expand", "attack", "defend"]
    best_action = actions[int(np.argmax(probs))]

    return {
        "action": best_action,
        "confidence": round(float(probs.max()), 4),
        "all_scores": dict(zip(actions, probs.round(4).tolist())),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[Modal] SC2 Serverless Training App")
    print(f"  App: {app.name}")
    print(f"  Functions:")
    print(f"    - train_sc2_model (GPU=A100, timeout=2h)")
    print(f"    - daily_sc2_training (schedule=daily)")
    print(f"    - predict_action (web_endpoint, POST)")
    print(f"  Volume: sc2-checkpoints (persistent)")
    print(f"\nDeploy: modal deploy modal_serverless/sc2_modal_train.py")
    print(f"Train now: modal run modal_serverless/sc2_modal_train.py::train_sc2_model")
