# SC2 Commander Bot — Improvement Backlog

Generated 2026-05-02 from a fresh test run + TODO.md review.

## Test snapshot (top-level repo)

```
410 tests collected | 382 passed | 13 failed | 15 skipped
```

The 13 failures break down into:
- 5 × `tests/test_security.py` — environment issue (`_cffi_backend` missing in sandbox); not bot bugs
- 3 × `tests/test_crypto_trading.py` — same `_cffi_backend` import chain
- 2 × `tests/test_new_modules.py::TestQMIX` — **real bug** in `qmix_marl/sc2_qmix_agent.py`
- 2 × `tests/test_p606_modules.py::TestMAPPO|TestCommLearning` — **real bug** in `mappo_marl/sc2_mappo_agent.py`
- 1 × `tests/test_phase10_improvements.py::test_gas_overflow_threshold_lowered` — **stale test** (code was further improved 1000→800)

`wicked_zerg_challenger/tests/`: 404/404 pass.

---

## Batch 1 — Test-driven bug fixes (highest signal)

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `qmix_marl/sc2_qmix_agent.py` | `class AgentQNetTorch(nn.Module)` declared at module level even when PyTorch is missing → `NameError: name 'nn' is not defined` on import | Define `_TorchModule` sentinel: `nn.Module` if `HAS_TORCH` else `object` |
| 2 | `qmix_marl/sc2_qmix_agent.py` | Same for `QMIXMixingNetTorch`, `VDNMixerTorch` | Use sentinel base class |
| 3 | `mappo_marl/sc2_mappo_agent.py` | Same bug: `SharedObsEncoderTorch`, `CentralizedCriticTorch`, `DecentralizedActorTorch` reference `nn.Module` unconditionally | Use sentinel base class |
| 4 | `tests/test_phase10_improvements.py:319` | Expects gas threshold == 1000 but code (correctly) lowered to 800 (`★ IMPROVED: 1000→800`) | Update test to assert `<= 1000` so future tightening doesn't regress it |
| 5 | `mappo_marl/__init__.py`, `qmix_marl/__init__.py` | Re-exports trigger same import error | Confirm fixed by 1-3 |

## Batch 2 — TODO.md priority work (defensive, unit-testable)

| # | File | Task |
|---|------|------|
| 6 | `wicked_zerg_challenger/economy_manager.py` | Expose `set_gas_overflow_threshold(value: int)` setter for runtime tuning + a getter. Add bounds check (200..3000). |
| 7 | `wicked_zerg_challenger/economy_manager.py` | Document `gas_overflow_prevention_threshold` invariant (lower = more aggressive macro re-investment) |
| 8 | `wicked_zerg_challenger/tests/` | Add a unit test for the new setter (rejects negatives, clamps to bounds, returns the clamped value) |
| 9 | `tests/test_phase10_improvements.py` | Replace strict 1000 equality with a range assertion (`200 <= t <= 1000`) and add a comment explaining the historical change |

## Batch 3 — Polish / encoding hygiene / regression guards

| # | File | Task |
|---|------|------|
| 10 | `tests/test_new_modules.py`, `tests/test_p606_modules.py` | Add a regression test that simply imports the four MARL modules and checks the module objects (catches re-introduction of the `nn.Module`-at-toplevel bug) |
| 11 | `qmix_marl/__init__.py`, `mappo_marl/__init__.py` | Wrap re-exports in `try/except ImportError` so tests can introspect even on partial installs |
| 12 | `IMPROVEMENT_BACKLOG.md` (this file) | Keep a running log; bump the test snapshot after each batch |

---

## Items deliberately deferred

- TODO.md scout/harassment timing tuning — needs a live SC2 client to validate; can't be checked in CI.
- Combat-manager frame skipping — same constraint; needs profiler data from a real game.
- Strategy-manager role split — large refactor; out of scope for an incremental pass.
- Crypto/security PyO3 panic — environmental, not the bot.
