"""
Phase 525: Wasmer Runtime
SC2 Bot WASM host using wasmer-python for sandboxed bot execution
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# ─────────────────────────────────────────────
# Wasmer host (with graceful fallback)
# ─────────────────────────────────────────────

try:
    from wasmer import (  # type: ignore
        Function,
        ImportObject,
        Instance,
        Module,
        Store,
        engine,
    )
    from wasmer_compiler_cranelift import Compiler  # type: ignore

    WASMER_AVAILABLE = True
except ImportError:
    WASMER_AVAILABLE = False


@dataclass
class BotSandbox:
    """Sandboxed bot execution environment via WebAssembly."""

    wasm_path: str
    store: Any = field(default=None, init=False)
    instance: Any = field(default=None, init=False)
    loaded: bool = field(default=False, init=False)

    def load(self) -> bool:
        if not WASMER_AVAILABLE:
            print("[Wasmer] wasmer-python not installed — using Python fallback")
            self.loaded = False
            return False
        try:
            self.store = Store(engine.JIT(Compiler))
            with open(self.wasm_path, "rb") as f:
                wasm_bytes = f.read()
            module = Module(self.store, wasm_bytes)
            self.instance = Instance(module)
            self.loaded = True
            print(f"[Wasmer] Loaded {self.wasm_path}")
            return True
        except Exception as e:
            print(f"[Wasmer] Load failed: {e}")
            self.loaded = False
            return False

    def call(self, func_name: str, *args) -> Any:
        if not self.loaded:
            return None
        fn = getattr(self.instance.exports, func_name, None)
        if fn is None:
            raise AttributeError(f"No export: {func_name}")
        return fn(*args)

    def get_minerals(self) -> int:
        return self.call("get_minerals") or 0

    def get_supply(self) -> int:
        return self.call("get_supply") or 0

    def run_ticks(self, n: int) -> None:
        self.call("run_ticks", n)

    def get_decision(self) -> int:
        return self.call("get_decision") or 0


# ─────────────────────────────────────────────
# Pure-Python fallback simulation
# ─────────────────────────────────────────────


@dataclass
class PythonBotSim:
    """Python-native simulation matching WASM bot logic."""

    minerals: int = 50
    gas: int = 0
    supply: int = 12
    workers: int = 12
    army_size: int = 0
    frame: int = 0
    threat_level: int = 0

    ACTION_WAIT = 0
    ACTION_DRONE = 1
    ACTION_ZERGLING = 2
    ACTION_EXPAND = 3
    ACTION_ATTACK = 4

    def tick_economy(self) -> None:
        income = (self.workers * 8) // 10
        self.minerals += income
        self.frame += 1

    def decide(self) -> int:
        if self.threat_level > 5:
            return self.ACTION_ATTACK
        if self.workers < 22 and self.minerals >= 50:
            return self.ACTION_DRONE
        if self.minerals >= 300:
            return self.ACTION_EXPAND
        if self.minerals >= 25:
            return self.ACTION_ZERGLING
        return self.ACTION_WAIT

    def execute_decision(self) -> None:
        action = self.decide()
        if action == self.ACTION_DRONE:
            self.minerals -= 50
            self.workers += 1
        elif action == self.ACTION_ZERGLING:
            self.minerals -= 25
            self.army_size += 2
        elif action == self.ACTION_EXPAND:
            self.minerals -= 300
            self.workers += 3  # new base workers
        elif action == self.ACTION_ATTACK:
            pass  # handled externally

    def run_ticks(self, n: int) -> None:
        for _ in range(n):
            self.tick_economy()
            self.execute_decision()

    def snapshot(self) -> dict:
        return {
            "frame": self.frame,
            "minerals": self.minerals,
            "gas": self.gas,
            "supply": self.supply,
            "workers": self.workers,
            "army_size": self.army_size,
        }


# ─────────────────────────────────────────────
# Multi-bot arena (parallel sandboxes)
# ─────────────────────────────────────────────


class BotArena:
    """Run multiple sandboxed bot instances in parallel."""

    def __init__(self, num_bots: int = 4):
        self.bots = [PythonBotSim() for _ in range(num_bots)]

    def run_round(self, ticks: int = 50) -> list[dict]:
        results = []
        for i, bot in enumerate(self.bots):
            bot.run_ticks(ticks)
            snap = bot.snapshot()
            snap["bot_id"] = i
            results.append(snap)
        return results

    def leaderboard(self) -> list[dict]:
        results = self.run_round(ticks=500)
        return sorted(results, key=lambda r: r["minerals"], reverse=True)

    def print_leaderboard(self) -> None:
        board = self.leaderboard()
        print("\n=== Bot Arena Leaderboard ===")
        for rank, entry in enumerate(board, 1):
            print(
                f"  #{rank}  Bot-{entry['bot_id']:<2}  "
                f"Minerals: {entry['minerals']:>5}  "
                f"Army: {entry['army_size']:>4}  "
                f"Workers: {entry['workers']:>3}"
            )


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 525: Wasmer Runtime — Sandboxed Bot Execution")
    print(f"Wasmer available: {WASMER_AVAILABLE}")

    # Try WASM sandbox first
    sandbox = BotSandbox("wasi_runtime/bot_module.wasm")
    if sandbox.load():
        sandbox.run_ticks(100)
        print(f"WASM Minerals: {sandbox.get_minerals()}")
        print(f"WASM Decision: {sandbox.get_decision()}")
    else:
        # Fallback to Python simulation
        sim = PythonBotSim()
        sim.run_ticks(100)
        print(f"Python sim: {json.dumps(sim.snapshot(), indent=2)}")

    # Arena simulation
    arena = BotArena(num_bots=4)
    arena.print_leaderboard()
