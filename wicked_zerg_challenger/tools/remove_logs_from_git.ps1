#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
"""
로그 파일을 Git 추적에서 제거하는 스크립트

사용법:
    .\tools\remove_logs_from_git.ps1
"""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "로그 파일 Git 추적 제거 스크립트" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 프로젝트 루트로 이동
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

Write-Host "[1/3] Git에 추적되는 로그 파일 찾기..." -ForegroundColor Yellow

# Git에 추적되는 로그 파일 찾기
$trackedLogFiles = git ls-files | Select-String -Pattern "logs/|log_.*\.txt|\.log$|\.log\."

if ($trackedLogFiles) {
    Write-Host "다음 로그 파일들이 Git에 추적되고 있습니다:" -ForegroundColor Red
    $trackedLogFiles | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    
    Write-Host "[2/3] Git 추적에서 제거 중..." -ForegroundColor Yellow
    
    # 각 파일을 Git 추적에서 제거 (파일은 로컬에 유지)
    $removedCount = 0
    foreach ($file in $trackedLogFiles) {
        try {
            git rm --cached $file 2>&1 | Out-Null
            Write-Host "  ✓ 제거됨: $file" -ForegroundColor Green
            $removedCount++
        } catch {
            Write-Host "  ✗ 실패: $file - $_" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "[3/3] 결과 요약" -ForegroundColor Yellow
    Write-Host "  총 $removedCount 개의 로그 파일이 Git 추적에서 제거되었습니다." -ForegroundColor Green
    Write-Host ""
    Write-Host "다음 단계:" -ForegroundColor Cyan
    Write-Host "  1. git status 로 변경사항 확인" -ForegroundColor White
    Write-Host "  2. git add .gitignore" -ForegroundColor White
    Write-Host "  3. git commit -m 'chore: Remove log files from Git tracking'" -ForegroundColor White
    Write-Host ""
    
} else {
    Write-Host "✅ Git에 추적되는 로그 파일이 없습니다." -ForegroundColor Green
    Write-Host ""
    Write-Host "확인 사항:" -ForegroundColor Cyan
    Write-Host "  - .gitignore에 logs/ 패턴이 포함되어 있는지 확인" -ForegroundColor White
    Write-Host "  - 원격 저장소에 이미 푸시된 파일은 별도로 제거해야 할 수 있습니다" -ForegroundColor White
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
