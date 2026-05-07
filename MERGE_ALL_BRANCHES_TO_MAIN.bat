@echo off
setlocal EnableExtensions EnableDelayedExpansion
title sc2bot - MERGE ALL BRANCHES TO MAIN

echo ====================================================
echo  sc2bot - MERGE ALL BRANCHES TO MAIN
echo ====================================================
echo Repo: %~dp0
echo.

cd /d "%~dp0"
if exist ".git\index.lock" del /F /Q ".git\index.lock"

echo [1/4] git fetch --prune origin...
git fetch --prune origin
echo.

echo [2/4] Branches MERGED into main (will be deleted):
set MERGED_LIST=claude/ecstatic-hellman-628710 claude/happy-wiles-991755 claude/objective-moser-953a1c claude/review-readme-planning-TJk2f claude/upbeat-murdock-99da7d
for %%B in (%MERGED_LIST%) do (
    git rev-parse --verify --quiet "%%B" >nul 2>&1
    if not errorlevel 1 (
        echo   - deleting %%B
        git branch -d "%%B" 2>nul
    )
)
echo.

echo [3/4] Branches NOT merged into main (kept, manual review):
echo   - claude/black-format-main-2026-04-27
echo   - claude/master-todo-sc2
echo   - claude/stoic-shannon-1YXPl
echo   - claude/stoic-shannon-Dc7yg
echo.

echo [4/4] Final local branch list:
git branch
echo.

echo ----------------------------------------------------
echo  See reports\branch_merge_plan.md for details.
echo  Review remaining branches as PRs on GitHub.
echo ----------------------------------------------------
pause
exit /b 0
