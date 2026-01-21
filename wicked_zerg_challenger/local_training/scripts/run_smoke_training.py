#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick smoke training setup.

Runs a tiny batch training session with synthetic data to validate
that the training pipeline and model wiring are functional.
"""

import argparse
import json
import random
from pathlib import Path
from typing import List, Dict, Any

from batch_trainer import BatchTrainer


def build_fake_batch_results(samples: int) -> List[Dict[str, Any]]:
    results = []
    for i in range(samples):
        minerals = random.randint(200, 1600)
        gas = random.randint(0, 800)
        supply_used = random.randint(10, 120)
        drone_count = random.randint(8, 80)
        army_count = random.randint(5, 120)

        enemy_army = random.randint(5, 120)
        enemy_tech = random.randint(0, 2)
        enemy_threat = random.uniform(0.0, 4.0)
        enemy_diversity = random.uniform(0.0, 1.0)
        scout_coverage = random.uniform(0.0, 1.0)
        enemy_distance = random.randint(10, 120)
        enemy_expansions = random.randint(1, 4)
        enemy_resources = random.randint(200, 5000)
        enemy_upgrades = random.randint(0, 10)
        enemy_air_ground = random.uniform(0.0, 1.0)

        # Simple heuristic for labels
        attack_prob = 0.25
        defense_prob = 0.25
        economy_prob = 0.25
        tech_prob = 0.25

        if enemy_threat >= 2.5:
            defense_prob = 0.5
        elif minerals > 1200 and drone_count < 50:
            economy_prob = 0.5
        elif enemy_tech >= 2:
            tech_prob = 0.5
        else:
            attack_prob = 0.5

        results.append(
            {
                "minerals": minerals,
                "gas": gas,
                "supply_used": supply_used,
                "drone_count": drone_count,
                "army_count": army_count,
                "enemy_army_count": enemy_army,
                "enemy_tech_level": enemy_tech,
                "enemy_threat_level": enemy_threat,
                "enemy_unit_diversity": enemy_diversity,
                "scout_coverage": scout_coverage,
                "enemy_main_distance": enemy_distance,
                "enemy_expansion_count": enemy_expansions,
                "enemy_resource_estimate": enemy_resources,
                "enemy_upgrade_count": enemy_upgrades,
                "enemy_air_ground_ratio": enemy_air_ground,
                "victory": bool(i % 2 == 0),
                "attack_probability": attack_prob,
                "defense_probability": defense_prob,
                "economy_probability": economy_prob,
                "tech_probability": tech_prob,
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run smoke batch training")
    parser.add_argument("--samples", type=int, default=64, help="Synthetic samples to generate")
    parser.add_argument("--epochs", type=int, default=2, help="Training epochs")
    parser.add_argument("--output-dir", default="local_training/smoke_output", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = build_fake_batch_results(max(8, args.samples))
    trainer = BatchTrainer(model_path=str(output_dir / "zerg_net_model_smoke.pt"))
    stats = trainer.train_from_batch_results(results, epochs=max(1, args.epochs))

    summary_path = output_dir / "smoke_training_summary.json"
    summary_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"[SMOKE] Training complete. Summary -> {summary_path}")


if __name__ == "__main__":
    main()
