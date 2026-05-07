@echo off
setlocal EnableExtensions EnableDelayedExpansion
title sc2bot - PUSH FIX TO MAIN

echo ====================================================
echo  Swarm-control-in-sc2bot - PUSH FIX TO MAIN
echo ====================================================
echo Repo: %~dp0
echo.

cd /d "%~dp0"
if errorlevel 1 (
    echo [FAIL] Cannot cd to repo dir.
    pause
    exit /b 1
)

echo [1/7] Removing stale .git locks if any...
if exist ".git\index.lock" del /F /Q ".git\index.lock"
if exist ".git\HEAD.lock" del /F /Q ".git\HEAD.lock"
echo [OK]  Lock cleanup done.
echo.

echo [2/7] Current branch + status...
git rev-parse --abbrev-ref HEAD
git status -s
echo.

echo [3/7] Resolve deferred-stage (D-in-index + ??-in-worktree)...
git add tests/test_combat_phase_fsm.py tests/test_expansion_timing.py tests/test_phase_scout_cadence.py
git add tests/test_queen_transfusion.py
git add wicked_zerg_challenger/scouting/phase_scout_cadence.py
echo.

echo [4/7] Run smoke tests (phase10 + combat + scout + expansion)...
set SKIP_HEAVY_DEPS=1
call python -m pytest tests/test_phase10_improvements.py tests/test_combat_phase_fsm.py tests/test_phase_scout_cadence.py tests/test_expansion_timing.py --tb=line -q
if errorlevel 1 (
    echo.
    echo [FAIL] Smoke tests failed. Aborting push.
    pause
    exit /b 1
)
echo [OK]  Smoke tests passed (84 tests).
echo.

echo [5/7] Stage harassment / scout / queen / mappo / qmix changes...
git add wicked_zerg_challenger/combat/harassment_coordinator.py
git add wicked_zerg_challenger/scouting/advanced_scout_system_v2.py
git add wicked_zerg_challenger/scouting/enhanced_scout_system.py
git add wicked_zerg_challenger/economy/queen_transfusion_manager.py
git add wicked_zerg_challenger/bot_step_integration.py
git add mappo_marl/__init__.py mappo_marl/sc2_mappo_agent.py
git add qmix_marl/sc2_qmix_agent.py
git add comm_learning/__init__.py
git add tests/test_crypto_trading.py tests/test_phase10_improvements.py
git add PLAN-NIGHTLY.md
git add docs/history/ requirements-dev.txt
git add scripts/commit_nightly_2026-05-03.bat
git add README_KO.txt MERGE_ALL_BRANCHES_TO_MAIN.bat PUSH_FIX_TO_MAIN.bat
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "fix(harass+scout): retreat threshold 0.2->0.35 + raid kill counter sync + scout cadence guard" -m "" -m "- harassment_coordinator: HP retreat threshold raised, prevents lings dying at 20pct" -m "- worker kill counter: sync snapshot on rebuild to avoid inflated kill claims" -m "- scout cadence: phase-aware cadence to prevent spam-scouting" -m "- queen transfusion: smarter target priority" -m "- mappo/qmix: stale import cleanup, RL stub guards" -m "- regression: 84/84 smoke pass"
    if errorlevel 1 (
        echo [FAIL] Commit failed.
        pause
        exit /b 1
    )
    echo [OK]  Committed.
) else (
    echo [SKIP] Nothing to commit.
)
echo.

echo [6/7] Switch to main and pull --rebase ...
git checkout main 2>nul
if errorlevel 1 (
    echo [INFO] Already on main or main missing. Continuing on current branch.
)
git pull --rebase origin main
if errorlevel 1 (
    echo.
    echo [FAIL] Rebase failed. Resolve conflicts manually.
    pause
    exit /b 1
)
echo.

echo [7/7] git push origin main...
git push origin main
if errorlevel 1 (
    echo.
    echo [FAIL] Push failed. Check auth and retry.
    pause
    exit /b 1
)
echo.
echo ====================================================
echo  DONE - sc2bot main pushed to origin
echo ====================================================
pause
exit /b 0
