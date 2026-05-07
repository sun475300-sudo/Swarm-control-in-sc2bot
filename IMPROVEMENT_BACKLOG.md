# SC2 Bot — Improvement Backlog (Cycle Tracker)

> Generated: 2026-05-07 · Branch: `claude/stoic-shannon-UAfoL`
> Source: pytest baseline + flake8 critical-error scan
> Cadence: each cycle picks ~5 items, fixes, runs tests, commits, pushes; then repeats.

## Baseline (cycle 0)

| Metric | Value |
|---|---|
| pytest collected | 342 (1 collection error blocked) |
| pytest passed | 365 (after excluding collection error) |
| pytest failed | 7 |
| pytest skipped | 34 |
| flake8 critical (F/E9/W6) | 485 |

### Failures (cycle 0)

1. `tests/test_queen_transfusion.py` — collection error (no `try/except` for `from sc2.ids.unit_typeid`)
2. `tests/test_security.py::TestSecurityImports::test_import_security_module` — `pyo3_runtime.PanicException`
3. `tests/test_security.py::TestSecurityImports::test_trade_safety_exists` — same
4. `tests/test_security.py::TestSecurityImports::test_allowed_ips_defined` — same
5. `tests/test_security.py::TestIPWhitelist::test_localhost_allowed` — same
6. `tests/test_security.py::TestIPWhitelist::test_ipv6_localhost_allowed` — same
7. `tests/test_crypto_trading.py::TestCryptoImports::test_import_config` — same
8. `tests/test_crypto_trading.py::TestCryptoImports::test_import_security` — same

Root cause for #2-#8: `crypto_trading/security.py` imports `cryptography.fernet.Fernet`
inside `try/except ImportError`, but on this system `_cffi_backend` is missing,
which raises `pyo3_runtime.PanicException` (not `ImportError`). The except clause
must be broadened.

## Backlog

### Cycle 1 — Test stability (TARGETED)

- [ ] **B1.1** `tests/test_queen_transfusion.py` — wrap `from sc2.ids.unit_typeid` in `try/except ImportError` + `pytest.skip(allow_module_level=True)`, matching the pattern in `test_harassment_coordinator.py:11-15`.
- [ ] **B1.2** `crypto_trading/security.py:651` (EncryptedTradeLog) — replace `except ImportError` with `except Exception` so cryptography load failures degrade to base64 fallback.
- [ ] **B1.3** `crypto_trading/security.py:1107` (SecretManager._init_fernet) — same broadening.
- [ ] **B1.4** Quick re-run: confirm 0 fail / 0 collection error.

### Cycle 2 — Lint hygiene (F541 batch)

- [ ] **B2.1** `wicked_zerg_challenger/wicked_zerg_bot_pro_impl.py` — 7 F541 f-string placeholder warnings (lines 306, 320, 552, 652, 661, 673, 748).
- [ ] **B2.2** `wicked_zerg_challenger/worker_combat_system.py:133` — 1 F541.
- [ ] **B2.3** Survey remaining F541 (255 total) — group by top 5 files.

### Cycle 3 — Lint hygiene (F841 unused locals)

- [ ] **B3.1** Top file with unused locals — fix top 20 occurrences.
- [ ] **B3.2** Identify whether any are bug-disguising (e.g. assigned but never read despite name suggesting use).

### Cycle 4 — F811 / F401 / F403

- [ ] **B4.1** `_find_harass_target` redefinition (line 2377 area).
- [ ] **B4.2** Single F401 unused import.
- [ ] **B4.3** Visual file `swarm_3d_ursina.py` — replace `from ursina import *` with explicit list (or scope via `# noqa: F403,F405` if intentional).

### Cycle 5 — Test coverage / skip cleanup

- [ ] **B5.1** Audit pytest skip/xfail (38 currently skipped) — categorize: env-dependent vs temporary holdovers.
- [ ] **B5.2** Convert env-dependent skips to `pytest.importorskip` for clearer reasoning.

### Cycle 6+ — Bot logic improvements (deferred until lint base is clean)

- [ ] **B6.1** Review `wicked_zerg_challenger/economy/queen_transfusion_manager.py` — verify recent transfusion fixes hold under cooldown edge cases.
- [ ] **B6.2** Audit `combat_manager` for missing `is_burrowed` / `is_cloaked` checks.
- [ ] **B6.3** `harassment_coordinator` retraction triggers — make threshold configurable.

---

## Cycle log

| Cycle | Date | Items | Tests after | Commit |
|---|---|---|---|---|
| 0 (baseline) | 2026-05-07 | — | 365P / 7F / 34S / 1err | (current HEAD `0ac482b`) |
| 1 | 2026-05-07 | B1.1, B1.2, B1.3 | **372P / 0F / 35S** | `2241e17` |
| 2 | 2026-05-07 | B2.1, B2.2 + 7 more files | **372P / 0F / 35S**, F541 255→159 | (this commit) |

### Cycle 2 detail

Removed dead `f` prefix from 96 f-strings without placeholders across 9 core files:

| File | F541 fixed |
|---|---|
| `run_with_training.py` | 24 |
| `economy_manager.py` | 14 |
| `check_learning_rate.py` | 14 |
| `local_training/production_resilience.py` | 11 |
| `log_analyzer.py` | 10 |
| `local_training/curriculum_manager.py` | 8 |
| `wicked_zerg_bot_pro_impl.py` | 7 |
| `bot_step_integration.py` | 7 |
| `worker_combat_system.py` | 1 |

Each fix is mechanical: `logger.info(f"static text")` → `logger.info("static text")`. No behavior change. Tests unchanged at 372P/0F/35S.

Remaining F541: 159 (mostly in `tools/` and `visuals/` utility scripts — lower priority).


### Cycle 1 detail

- **B1.1** `tests/test_queen_transfusion.py:11` — added `try/except ImportError` around `from sc2.ids.unit_typeid import UnitTypeId` with `pytest.skip(allow_module_level=True)`. Removes 1 collection error.
- **B1.2** `crypto_trading/security.py:665` (EncryptedTradeLog) — broadened `except ImportError` to `except BaseException` (re-raising `KeyboardInterrupt`/`SystemExit`). Catches `pyo3_runtime.PanicException` raised when cryptography native bindings (`_cffi_backend`) are missing.
- **B1.3** `crypto_trading/security.py:1123` (SecretManager._init_fernet) — same broadening with same KI/SE re-raise guard.

Effect: 7 hard failures + 1 collection error gone.

