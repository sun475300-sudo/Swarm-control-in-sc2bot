#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plot sensor network CSV/JSON to PNG.

Usage:
  python local_training/scripts/plot_sensor_network.py --csv logs/sensor_network.csv --out logs/sensor_network.png
"""

import argparse
from pathlib import Path

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot sensor network positions")
    parser.add_argument("--csv", default="logs/sensor_network.csv", help="Sensor CSV path")
    parser.add_argument("--out", default="logs/sensor_network.png", help="Output image path")
    args = parser.parse_args()

    if not PLOT_AVAILABLE:
        print("[ERROR] pandas/matplotlib not installed. Install them to use this plotter.")
        return

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("[ERROR] CSV is empty.")
        return

    plt.figure(figsize=(8, 8))
    plt.scatter(df["pos_x"], df["pos_y"], s=10, alpha=0.6, label="sensor_pos")
    plt.scatter(df["target_x"], df["target_y"], s=10, alpha=0.4, label="target_pos")
    plt.title("Sensor Network Positions")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    print(f"[OK] Saved plot -> {out_path}")


if __name__ == "__main__":
    main()
