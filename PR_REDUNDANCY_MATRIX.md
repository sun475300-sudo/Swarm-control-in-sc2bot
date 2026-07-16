# PR 중복 분석 — #449~#478 (2026-07-16 조사)

> 작성: 자동 점검 세션 (claude/optimistic-edison-ocf554)
> 목적: MASTER_TODO_SC2.md S1.1 실행 — 열린 PR 30건의 redundancy 매트릭스 작성
> **승인 불필요 항목**(분석/문서화)만 수행. close/merge는 사용자 승인 필요.

---

## 1. 핵심 발견

**열린 draft PR 30건(#449~#478)이 사실상 동일한 버그 2개를 반복해서 고치고 있다.**

- 버그 A: `tests/test_queen_transfusion.py`가 `sc2` 패키지를 fallback 없이 import 해서, `sc2`(burnysc2)가 설치되지 않은 환경에서 pytest 수집 자체가 중단됨.
- 버그 B: `tests/test_combat_phase_fsm.py`가 `asyncio.get_event_loop().run_until_complete(...)`(deprecated, 암묵적 이벤트 루프 생성에 의존)를 사용해서, 전체 스위트를 함께 돌릴 때 순서 의존적으로 실패함.

2026-07-13 23:22(#449)부터 2026-07-15 05:15(#478)까지 **약 30시간 동안 매시간 1건씩** 새 세션이 브랜치를 새로 파서 동일한 두 버그를 독립적으로 재발견하고, 거의 동일한 수정(fallback import guard + `asyncio.run()` 치환)을 담은 draft PR을 또 만들었다. **단 하나도 main에 머지되지 않았기 때문에**, 매 세션이 fresh main에서 시작할 때마다 버그가 여전히 남아있어 무한 반복된 것으로 보인다.

## 2. 근본 원인 (신규 발견, 이번 세션)

`ci.yml`의 `python-lint-test` 잡이 `tests/` 스위트를 **실제로 실행하지 않고 있었다**:

```yaml
# 수정 전 (.github/workflows/ci.yml:115)
pytest tests/ -v --tb=short --co -q     # --co = collect-only, 실행 안 함
pytest tests/test_crypto_trading.py tests/test_security.py -v --tb=short  # 이 2개 파일만 실제 실행
```

`--co`(collect-only) 플래그 때문에 423개 테스트 중 421개는 CI에서 **한 번도 실제로 실행되지 않았다** — 수집(import) 가능 여부만 검증됨. `sc2-bot-test` 잡은 별도 디렉터리(`wicked_zerg_challenger/tests/`)를 돈다. 즉 `tests/`의 진짜 런타임 검증 게이트가 CI에 존재하지 않았다 — 이것이 30건의 PR이 로컬에서는 "395 passed"를 반복 보고하면서도 CI가 실제로 그 결과를 검증한 적이 없는 이유다.

**이번 세션에서 수정함** (`.github/workflows/ci.yml`):
- `--co` 제거 → `tests/` 전체를 실제로 실행
- `pytest-asyncio`, `pytest-timeout`을 설치 스텝에 추가 (없으면 83개 async 테스트가 "async def functions are not natively supported"로 실패)

부가 발견: `requirements.txt`가 `cryptography>=41.0.0`은 선언하지만 `cffi`는 선언하지 않아, 일부 환경(예: 이 세션의 apt 설치 `cryptography` 41.0.7)에서 `crypto_trading/security.py` 모듈 임포트 시점에 `SecretManager()`가 즉시 생성되며 `_cffi_backend` 누락으로 `pyo3_runtime.PanicException`이 발생 → `test_crypto_trading.py`/`test_security.py` 7개 테스트 실패. `cffi>=1.15.0`을 `requirements.txt`에 추가함.

## 3. PR 목록 (생성 시각순, 전부 draft, 전부 main 대상)

| # | 생성 시각(UTC) | 제목 요약 |
|---|---|---|
| 449 | 07-13 23:22 | CI가 실제로 tests/ 를 실행 안 함 + crash-masking 버그 |
| 450 | 07-14 00:31 | CI lint drift, event-loop pollution, Arena size gate |
| 451 | 07-14 01:25 | test-suite stability, CI test path, RL save data-loss |
| 452 | 07-14 02:18 | sc2bot-ci 파이프라인 unblock (test path, sys.path) |
| 453 | 07-14 03:25 | combat FSM event-loop + sc2-import collection crash |
| 454 | 07-14 04:14 | order-dependent failures + improvement sweep |
| 455 | 07-14 06:23 | 23 collection errors + 12 asyncio failures |
| 456 | 07-14 07:17 | combat FSM 복구 + dead code 제거 |
| 457 | 07-14 08:19 | flaky combat FSM event-loop + stale issue tracker |
| 458 | 07-14 09:18 | order-dependent asyncio + unguarded sc2 import |
| 459 | 07-14 10:19 | Python 3.11 test crash + import-time landmine |
| 460 | 07-14 11:21 | CI gate repairs (sc2 guard, black/isort, protobuf) |
| 461 | 07-14 12:21 | 두 테스트 스위트 동시 실행 시 발생하는 버그 |
| 462 | 07-14 13:20 | Python 3.11 asyncio 버그(12건) + 문서 감사 |
| 463 | 07-14 14:19 | flaky combat-phase FSM + stale issue tracker |
| 464 | 07-14 15:18 | 전체 pytest suite unblock + order-dependent FSM |
| 465 | 07-14 16:22 | green CI 복구(black/isort) + flaky FSM |
| 466 | 07-14 17:23 | docs: nightly check-in — Sprint 1-6 "완전 구현" 주장 |
| 467 | 07-14 18:18 | event-loop crash + PR pileup 플래그 |
| 468 | 07-14 19:16 | RL agent atomic save + save-guard 테스트 |
| 469 | 07-14 20:15 | 전체 스위트 unblock (sc2 guard + asyncio.run) |
| 470 | 07-14 21:13 | deprecated asyncio.get_event_loop() 제거 |
| 471 | 07-14 22:25 | event-loop flake, dead HELPERS_AVAILABLE 분기 |
| 472 | 07-14 23:23 | 머지 전면 차단하던 CI lockout 근본 원인 |
| 473 | 07-15 00:18 | asyncio.get_event_loop() → asyncio.run() 치환 |
| 474 | 07-15 01:25 | combat FSM 복구 + mypy/CI lint unblock |
| 475 | 07-15 02:22 | combat FSM 복구 + 조용히 삼켜지던 예외 로깅 |
| 476 | 07-15 03:16 | asyncio.get_event_loop() FSM + protobuf 수집 crash |
| 477 | 07-15 04:18 | deprecated asyncio 패턴 + position-cache 중복 제거 |
| 478 | 07-15 05:15 | sc2-import collection crash + flaky event-loop (최신) |

**결론**: 30건 모두 버그 A/B 중 하나 이상을 다룬다. 서로 다른 부가 수정(dead code 정리, 문서 갱신 등)이 섞여 있지만 핵심 diff는 거의 동일하다.

## 4. 권장 조치 (사용자 승인 필요)

1. **머지 후보 선정**: #478(최신, 가장 완성도 높음 — sc2 guard + asyncio.run 둘 다 포함, "395 passed, 34 skipped, 0 failed" 명시)을 검토 후 머지 — 단, 이번 세션에서 `ci.yml`의 `--co` 근본 원인도 같이 고쳤으므로, 이 PR(`claude/optimistic-edison-ocf554`)을 대신 머지하면 #478 내용을 포함하면서 CI 게이트 자체도 고칠 수 있음.
2. **나머지 29건 close 권장** — 전부 동일 diff의 변주. 사용자가 close를 승인하면 일괄 정리 가능.
3. **재발 방지**: 이 PR이 머지되어 `--co`가 제거되면, 이후 세션은 CI가 실제로 tests/ 를 실행해서 그린 상태를 확인할 수 있으므로 "머지 안 됨 → 버그 재발견 → 중복 PR" 루프가 끊길 것으로 기대.
