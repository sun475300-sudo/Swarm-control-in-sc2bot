"""
Phase 526: Wasmtime Runtime
SC2 Bot using wasmtime-py with Component Model support
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import struct
import time

try:
    import wasmtime
    from wasmtime import (
        Store,
        Engine,
        Module,
        Linker,
        WasiConfig,
        FuncType,
        ValType,
        Func,
    )

    WASMTIME_AVAILABLE = True
except ImportError:
    WASMTIME_AVAILABLE = False


# ─────────────────────────────────────────────
# WASI Configuration builder
# ─────────────────────────────────────────────


def make_wasi_config(bot_id: int) -> "WasiConfig":
    if not WASMTIME_AVAILABLE:
        return None
    cfg = WasiConfig()
    cfg.argv = ["bot", str(bot_id)]
    cfg.env = [("BOT_ID", str(bot_id)), ("BOT_MODE", "selfplay")]
    cfg.inherit_stdin()
    cfg.inherit_stdout()
    cfg.inherit_stderr()
    return cfg


# ─────────────────────────────────────────────
# Component model interface (WIT-style)
# ─────────────────────────────────────────────


@dataclass
class GameObservation:
    """Mirrors WIT interface: sc2bot:game/observation"""

    minerals: int
    gas: int
    supply: int
    max_supply: int
    frame: int
    worker_count: int
    army_supply: int
    enemy_army_supply: int
    threat_level: float


@dataclass
class GameAction:
    """Mirrors WIT interface: sc2bot:game/action"""

    action_type: str  # "train" | "build" | "move" | "attack" | "expand"
    target: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    priority: int = 0


# ─────────────────────────────────────────────
# Pure-Python bot logic (component implementation)
# ─────────────────────────────────────────────


class SC2BotComponent:
    """Implements sc2bot:game/strategy WIT interface in Python."""

    def __init__(self, strategy: str = "adaptive"):
        self.strategy = strategy
        self._state_history: list[GameObservation] = []
        self._action_count: dict[str, int] = {}

    def on_observation(self, obs: GameObservation) -> GameAction:
        """Main decision function — called each game step."""
        self._state_history.append(obs)
        action = self._decide(obs)
        self._action_count[action.action_type] = (
            self._action_count.get(action.action_type, 0) + 1
        )
        return action

    def _decide(self, obs: GameObservation) -> GameAction:
        # Under attack
        if obs.threat_level > 0.7:
            return GameAction("attack", priority=10)

        # Need supply
        if obs.supply >= obs.max_supply - 2:
            return GameAction("build", target="overlord", priority=8)

        # Saturate workers
        if obs.worker_count < 22:
            if obs.minerals >= 50:
                return GameAction("train", target="drone", priority=7)

        # Expand
        if obs.minerals >= 300 and obs.frame > 2000:
            return GameAction("expand", priority=6)

        # Tech
        if obs.gas >= 100 and obs.minerals >= 150:
            return GameAction("build", target="lair", priority=5)

        # Build army
        if obs.minerals >= 75:
            unit = self._select_army_unit(obs)
            return GameAction("train", target=unit, priority=4)

        return GameAction("train", target="drone", priority=1)

    def _select_army_unit(self, obs: GameObservation) -> str:
        if obs.gas >= 25:
            return "roach"
        return "zergling"

    def get_stats(self) -> dict:
        return {
            "total_steps": len(self._state_history),
            "action_distribution": self._action_count,
            "avg_minerals": (
                sum(o.minerals for o in self._state_history)
                / max(1, len(self._state_history))
            ),
        }


# ─────────────────────────────────────────────
# Wasmtime host wrapper
# ─────────────────────────────────────────────


class WasmtimeHost:
    def __init__(self, wasm_path: str):
        self.wasm_path = wasm_path
        self.engine: Optional[Engine] = None
        self.store: Optional[Store] = None
        self.instance = None

    def setup(self) -> bool:
        if not WASMTIME_AVAILABLE:
            print("[wasmtime] Not available — using Python component")
            return False
        try:
            self.engine = Engine()
            cfg = WasiConfig()
            cfg.inherit_stdout()
            self.store = Store(self.engine)
            self.store.set_wasi(cfg)
            linker = Linker(self.engine)
            linker.define_wasi()
            module = Module.from_file(self.engine, self.wasm_path)
            self.instance = linker.instantiate(self.store, module)
            return True
        except Exception as e:
            print(f"[wasmtime] Setup failed: {e}")
            return False

    def call(self, name: str, *args):
        if self.instance is None:
            return None
        fn = self.instance.exports(self.store).get(name)
        if fn is None:
            return None
        return fn(self.store, *args)


# ─────────────────────────────────────────────
# Simulation runner
# ─────────────────────────────────────────────


def simulate_game(bot: SC2BotComponent, frames: int = 1000) -> dict:
    """Drive the bot component through a simulated game."""
    minerals = 50
    gas = 0
    supply = 12
    max_supply = 14
    workers = 12
    army_supply = 0

    for frame in range(frames):
        # Economy tick
        minerals += workers * 8 // 10
        gas += 0  # no geyser for simplicity

        obs = GameObservation(
            minerals=minerals,
            gas=gas,
            supply=supply,
            max_supply=max_supply,
            frame=frame,
            worker_count=workers,
            army_supply=army_supply,
            enemy_army_supply=max(0, frame // 200 - 5),
            threat_level=min(1.0, frame / 5000),
        )

        action = bot.on_observation(obs)

        # Apply action
        if action.action_type == "train":
            if action.target == "drone" and minerals >= 50:
                minerals -= 50
                workers += 1
                supply += 1
            elif action.target == "zergling" and minerals >= 25:
                minerals -= 25
                army_supply += 1
                supply += 1
            elif action.target == "roach" and minerals >= 75:
                minerals -= 75
                army_supply += 2
                supply += 2
        elif action.action_type == "build":
            if action.target == "overlord" and minerals >= 100:
                minerals -= 100
                max_supply += 8
            elif action.target == "lair" and minerals >= 150 and gas >= 100:
                minerals -= 150
                gas -= 100
        elif action.action_type == "expand" and minerals >= 300:
            minerals -= 300
            workers += 4
            max_supply += 2

    return {
        "final_minerals": minerals,
        "final_army": army_supply,
        "final_workers": workers,
        **bot.get_stats(),
    }


if __name__ == "__main__":
    print("Phase 526: Wasmtime Runtime — Component Model Bot")
    print(f"wasmtime available: {WASMTIME_AVAILABLE}")

    # Python component simulation
    bot = SC2BotComponent(strategy="adaptive")
    result = simulate_game(bot, frames=1000)
    print("\n=== Simulation Result ===")
    for k, v in result.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.1f}")
        else:
            print(f"  {k}: {v}")
